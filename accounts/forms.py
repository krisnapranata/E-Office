from django import forms

from .models import OrganizationRelation, OrganizationUnit, User


class UnitForm(forms.ModelForm):
    class Meta:
        model = OrganizationUnit
        fields = ["code", "name", "kind", "parent", "order", "head"]
        help_texts = {
            "code": "Identitas unik, mis. RSIY-IGD. Dipakai sebagai kunci data; hindari mengubahnya.",
            "parent": "Garis komando (struktural). Kosongkan untuk unit puncak atau unit non-struktural seperti komite.",
            "head": "Opsional. Kepala unit menerima eskalasi keterlambatan bila PIC tidak punya atasan langsung.",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        induk = OrganizationUnit.objects.filter(is_active=True).order_by("order", "name")
        if self.instance.pk:
            induk = induk.exclude(pk__in=self.instance.descendant_ids())    # cegah hubungan melingkar
        self.fields["parent"].queryset = induk
        self.fields["parent"].required = False
        self.fields["head"].queryset = User.objects.filter(is_active=True).order_by("first_name", "username")
        self.fields["head"].required = False


class RelationForm(forms.Form):
    target = forms.ModelChoiceField(label="Berhubungan dengan",
                                    queryset=OrganizationUnit.objects.filter(is_active=True).order_by("order", "name"))
    kind = forms.ChoiceField(label="Jenis hubungan", choices=OrganizationRelation.Kind.choices)
    note = forms.CharField(label="Keterangan", max_length=255, required=False)


class ReasonForm(forms.Form):
    reason = forms.CharField(label="Alasan penonaktifan", widget=forms.Textarea(attrs={"rows": 2}))


class UnitTreeField(forms.ModelChoiceField):
    """Pilihan unit berlabel bertingkat sesuai pohon Master Organisasi."""

    def __init__(self, pilihan, **kwargs):
        self.kedalaman = {u.pk: d for u, d in pilihan}
        super().__init__(queryset=OrganizationUnit.objects.filter(pk__in=self.kedalaman), **kwargs)
        self.choices = [("", "— pilih unit/bidang —")] + [(u.pk, self.label_from_instance(u)) for u, _ in pilihan]

    def label_from_instance(self, obj):
        return "   " * self.kedalaman.get(obj.pk, 0) + ("· " if self.kedalaman.get(obj.pk) else "") + obj.name


class PenggunaForm(forms.ModelForm):
    kepala = forms.BooleanField(label="Kepala/pimpinan unit ini", required=False,
                                help_text="Menjadi kepala unit: menerima eskalasi keterlambatan unit ini. "
                                          "Kepala lama (bila ada) akan digantikan.")
    password1 = forms.CharField(label="Kata sandi", widget=forms.PasswordInput(render_value=False), required=False,
                                strip=False)
    password2 = forms.CharField(label="Ulangi kata sandi", widget=forms.PasswordInput(render_value=False),
                                required=False, strip=False)

    class Meta:
        model = User
        fields = ["first_name", "username", "email", "unit", "position", "role", "supervisor"]
        labels = {"first_name": "Nama lengkap (dengan gelar)", "username": "Nama pengguna (login)"}
        help_texts = {
            "username": "Huruf kecil tanpa spasi, mis. nip atau nama.panggilan.",
            "position": "Kosongkan untuk diisi otomatis dari unit, mis. \"Staf Instalasi Farmasi\".",
            "supervisor": "Kosongkan untuk diisi otomatis: kepala unit sendiri, atau kepala unit induk bila Anda "
                          "kepala unit.",
        }

    def __init__(self, *args, pilihan, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["first_name"].required = True
        self.fields["unit"] = UnitTreeField(pilihan, label="Unit/bidang", required=True,
                                            help_text="Diambil dari Master Organisasi.")
        self.fields["supervisor"].queryset = (User.objects.filter(is_active=True).exclude(pk=self.instance.pk)
                                              .select_related("unit").order_by("first_name", "username"))
        self.fields["supervisor"].required = False
        baru = self.instance.pk is None
        self.fields["password1"].required = baru
        self.fields["password2"].required = baru
        if not baru:
            self.fields["password1"].label = "Kata sandi baru"
            self.fields["password1"].help_text = "Kosongkan bila tidak diganti."
            self.fields["password2"].label = "Ulangi kata sandi baru"
            self.initial.setdefault("kepala", self.instance.unit_id is not None
                                    and self.instance.headed_units.filter(pk=self.instance.unit_id).exists())
        self.order_fields(["first_name", "unit", "kepala", "position", "role", "supervisor", "username", "email",
                           "password1", "password2"])

    def clean(self):
        data = super().clean()
        if data.get("password1") != data.get("password2"):
            self.add_error("password2", "Kata sandi tidak sama.")
        return data
