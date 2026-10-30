from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.urls import reverse

from accounts import organisasi as org
from accounts import pengguna as svc
from accounts.models import OrganizationUnit, Role, User
from testutils import factories as f

U = OrganizationUnit
SANDI = "Sandi-Kuat-2026!"


class SaranStrukturTests(TestCase):
    def setUp(self):
        org.seed_rsiy()
        self.g = lambda kode: U.objects.get(code=kode)  # noqa: E731

    def test_jabatan_dan_peran_dari_unit(self):
        self.assertEqual(svc.jabatan_saran(self.g("RSIY-SHRD"), True), "Kepala Seksi HRD")
        self.assertEqual(svc.jabatan_saran(self.g("RSIY-IGD"), True), "Kepala Instalasi Gawat Darurat")
        self.assertEqual(svc.jabatan_saran(self.g("RSIY-KMEDIK"), True), "Ketua Komite Medik")
        self.assertEqual(svc.jabatan_saran(self.g("RSIY-FARMASI"), False), "Staf Instalasi Farmasi")
        self.assertEqual(svc.peran_saran(self.g("RSIY-DIR"), True), Role.DIREKTUR)
        self.assertEqual(svc.peran_saran(self.g("RSIY-BKEU"), True), Role.WADIR)
        self.assertEqual(svc.peran_saran(self.g("RSIY-IGD"), True), Role.KEPALA_UNIT)
        self.assertEqual(svc.peran_saran(self.g("RSIY-IGD"), False), Role.STAF)

    def test_atasan_kepala_terdekat_di_garis_struktural(self):
        dir_ = f.user(Role.DIREKTUR, unit=self.g("RSIY-DIR"))
        U.objects.filter(code="RSIY-DIR").update(head=dir_)
        seksi = f.user(Role.KEPALA_UNIT, unit=self.g("RSIY-SMEDIK"))
        U.objects.filter(code="RSIY-SMEDIK").update(head=seksi)
        # IGD belum punya kepala -> staf IGD ke Kepala Seksi Pelayanan Medik
        self.assertEqual(svc.atasan_saran(self.g("RSIY-IGD"), False), seksi)
        # kepala seksi -> lompati Manager & Kabid yang kosong -> Direktur
        self.assertEqual(svc.atasan_saran(self.g("RSIY-SMEDIK"), True, seksi), dir_)

    def test_pilihan_unit_mengikuti_pohon(self):
        pilihan = svc.pilihan_unit()
        nama = [u.name for u, _ in pilihan]
        self.assertLess(nama.index("Kepala Bidang Pelayanan"), nama.index("Instalasi Gawat Darurat"))
        self.assertEqual(dict((u.code, d) for u, d in pilihan)["RSIY-IGD"], 4)


class LayananPenggunaTests(TestCase):
    def setUp(self):
        org.seed_rsiy()
        self.admin = f.user(Role.ADMIN, username="adm")
        self.farmasi = U.objects.get(code="RSIY-FARMASI")

    def data(self, **kw):
        d = {"first_name": "apt. Siti", "username": "siti", "email": "", "unit": self.farmasi,
             "position": "", "role": Role.STAF, "supervisor": None}
        d.update(kw)
        return d

    def test_kepala_lalu_staf_otomatis_ke_kepala(self):
        ka, _ = svc.create_user(self.admin, self.data(role=Role.KEPALA_UNIT), SANDI, kepala=True)
        self.farmasi.refresh_from_db()
        self.assertEqual(self.farmasi.head, ka)
        self.assertEqual(ka.position, "Kepala Instalasi Farmasi")
        staf, _ = svc.create_user(self.admin, self.data(first_name="Budi", username="budi"), SANDI)
        self.assertEqual((staf.supervisor, staf.position), (ka, "Staf Instalasi Farmasi"))
        self.assertTrue(staf.check_password(SANDI))
        # ganti kepala -> kepala lama dilaporkan
        _, diganti = svc.update_user(self.admin, staf, self.data(first_name="Budi", username="budi",
                                                                 supervisor=ka), kepala=True)
        self.farmasi.refresh_from_db()
        self.assertEqual((self.farmasi.head, diganti), (staf, str(ka)))

    def test_pindah_unit_melepas_jabatan_kepala_lama(self):
        ka, _ = svc.create_user(self.admin, self.data(), SANDI, kepala=True)
        gizi = U.objects.get(code="RSIY-GIZI")
        svc.update_user(self.admin, ka, self.data(unit=gizi, position="Staf Gizi"))
        self.farmasi.refresh_from_db()
        self.assertIsNone(self.farmasi.head)

    def test_hak_akses_dan_validasi(self):
        staf = f.user(Role.STAF)
        with self.assertRaises(PermissionDenied):
            svc.create_user(staf, self.data(), SANDI)
        with self.assertRaises(ValidationError):
            svc.create_user(self.admin, self.data(), "123")               # sandi lemah
        su = User.objects.create_superuser("root", password=SANDI)
        with self.assertRaises(PermissionDenied):
            svc.update_user(self.admin, su, self.data(username="root"))
        with self.assertRaises(ValidationError):
            svc.deactivate(self.admin, self.admin)

    def test_nonaktif_melepas_kepala(self):
        ka, _ = svc.create_user(self.admin, self.data(), SANDI, kepala=True)
        self.assertEqual(svc.deactivate(self.admin, ka), ["Instalasi Farmasi"])
        self.farmasi.refresh_from_db()
        self.assertIsNone(self.farmasi.head)
        ka.refresh_from_db()
        self.assertFalse(ka.is_active)


class HalamanPenggunaTests(TestCase):
    def setUp(self):
        org.seed_rsiy()
        self.admin = f.user(Role.ADMIN)
        self.igd = U.objects.get(code="RSIY-IGD")

    def test_staf_ditolak(self):
        self.client.force_login(f.user(Role.STAF))
        self.assertEqual(self.client.get(reverse("pengguna:index")).status_code, 403)
        self.assertEqual(self.client.get(reverse("pengguna:create")).status_code, 403)

    def test_tambah_dari_pohon(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("organisasi:index"))
        self.assertContains(r, reverse("pengguna:create") + f"?unit={self.igd.pk}")
        r = self.client.get(reverse("pengguna:create") + f"?unit={self.igd.pk}")
        self.assertContains(r, f'<option value="{self.igd.pk}" selected>')
        r = self.client.post(reverse("pengguna:create"), {
            "first_name": "dr. Andi", "username": "andi", "unit": self.igd.pk, "kepala": "on",
            "role": Role.KEPALA_UNIT, "password1": SANDI, "password2": SANDI, "lagi": "1"})
        self.assertRedirects(r, reverse("pengguna:create") + f"?unit={self.igd.pk}")
        andi = User.objects.get(username="andi")
        self.igd.refresh_from_db()
        self.assertEqual((andi.unit, self.igd.head, andi.position), (self.igd, andi, "Kepala Instalasi Gawat Darurat"))
        r = self.client.get(reverse("pengguna:index"))
        self.assertContains(r, "Kepala Bidang Pelayanan")                 # dikelompokkan per bidang
        self.assertContains(r, "dr. Andi")

    def test_sandi_tidak_sama(self):
        self.client.force_login(self.admin)
        r = self.client.post(reverse("pengguna:create"), {
            "first_name": "X", "username": "x", "unit": self.igd.pk, "role": Role.STAF,
            "password1": SANDI, "password2": SANDI + "x"})
        self.assertContains(r, "Kata sandi tidak sama.")
        self.assertFalse(User.objects.filter(username="x").exists())
