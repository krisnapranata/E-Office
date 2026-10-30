"""Pengguna: input pegawai per unit/bidang dari Master Organisasi (kepala, staf, atasan otomatis, nonaktif)."""
from accounts.models import OrganizationUnit, Role, User
from accounts.organisasi import seed_rsiy
from audit.models import AuditLog
from testutils.factories import user

from . import skenario
from ._bantu import JUDUL_QA, url

SANDI = "QA-Sandi-Kuat-2026!"


@skenario("pengguna", "Pengguna: tambah kepala & staf dari pohon organisasi → atasan otomatis → ubah → nonaktif/aktif",
          crud=True, role="staf_igd",
          menu=["pengguna:index", "pengguna:create", "pengguna:edit", "pengguna:deactivate", "pengguna:activate"])
def _(u):
    seed_rsiy()
    diklat = OrganizationUnit.objects.get(code="RSIY-DIKLAT")
    hrd = OrganizationUnit.objects.get(code="RSIY-SHRD")
    OrganizationUnit.objects.filter(pk=diklat.pk).update(head=None)   # skenario: Diklat tanpa kepala (di-rollback)
    u.get(url("pengguna:index"), harap=403)
    u.get(url("pengguna:create"), harap=403)
    u.post(url("pengguna:deactivate", u.w.ka_igd.pk), harap=403)

    u.w.admin = user(Role.ADMIN, unit=u.w.dir_unit, username="qa_admin")
    u.sebagai("admin")
    r = u.get(url("organisasi:index"))
    u.harap(url("pengguna:create") + f"?unit={hrd.pk}" in u.teks(r), "tombol tambah pengguna tidak ada di pohon")
    u.get(url("pengguna:create") + f"?unit={hrd.pk}", ada=["Tambah pengguna", f'<option value="{hrd.pk}" selected>',
                                                           "saran-unit"])
    u.post(url("pengguna:create"), {"first_name": f"{JUDUL_QA} Kepala HRD", "username": "qa_ka_hrd", "unit": hrd.pk,
                                    "kepala": "on", "role": Role.KEPALA_UNIT, "password1": SANDI, "password2": SANDI},
           harap=302)
    ka = User.objects.get(username="qa_ka_hrd")
    hrd.refresh_from_db()
    u.harap(hrd.head_id == ka.pk and ka.position == "Kepala Seksi HRD", "kepala unit/jabatan tidak terisi dari struktur")
    u.post(url("pengguna:create"), {"first_name": f"{JUDUL_QA} Staf Diklat", "username": "qa_staf_diklat",
                                    "unit": diklat.pk, "role": Role.STAF, "password1": SANDI, "password2": SANDI,
                                    "lagi": "1"}, harap=302)
    staf = User.objects.get(username="qa_staf_diklat")
    # Diklat belum punya kepala -> atasan = kepala unit induk terdekat (Kepala Seksi HRD)
    u.harap(staf.supervisor_id == ka.pk and staf.position == "Staf Diklat", "atasan/jabatan otomatis salah")
    u.harap(staf.check_password(SANDI), "kata sandi tidak tersimpan")
    u.post(url("pengguna:create"), {"first_name": "dup", "username": "qa_staf_diklat", "unit": diklat.pk,
                                    "role": Role.STAF, "password1": SANDI, "password2": SANDI},
           harap=200, ada=["text-danger"])                                      # login unik
    u.post(url("pengguna:create"), {"first_name": "x", "username": "qa_lemah", "unit": diklat.pk,
                                    "role": Role.STAF, "password1": "123", "password2": "123"}, harap=200)
    u.harap(not User.objects.filter(username="qa_lemah").exists(), "sandi lemah diterima")
    u.get(url("pengguna:index") + f"?unit={hrd.pk}", ada=["Kepala Bidang Umum &amp; Kepegawaian",
                                                          f"{JUDUL_QA} Kepala HRD", f"{JUDUL_QA} Staf Diklat"])
    u.get(url("pengguna:edit", staf.pk), ada=["Ubah pengguna", "Riwayat perubahan", "user.create"])
    u.post(url("pengguna:edit", staf.pk), {"first_name": f"{JUDUL_QA} Staf Diklat", "username": "qa_staf_diklat",
                                           "unit": diklat.pk, "role": Role.STAF, "position": "Koordinator Diklat",
                                           "supervisor": ka.pk}, harap=302)
    staf.refresh_from_db()
    u.harap(staf.position == "Koordinator Diklat" and staf.check_password(SANDI), "ubah tanpa sandi gagal")
    u.get(url("pengguna:edit", ka.pk), ada=["Bawahan langsung", f"{JUDUL_QA} Staf Diklat"])
    u.get(url("organisasi:edit", hrd.pk), ada=[f"{JUDUL_QA} Kepala HRD", "Tambah pengguna"])
    u.post(url("pengguna:deactivate", u.w.admin.pk), harap=302)               # tidak bisa diri sendiri
    u.w.admin.refresh_from_db()
    u.harap(u.w.admin.is_active, "admin menonaktifkan diri sendiri")
    u.post(url("pengguna:deactivate", ka.pk), harap=302)
    ka.refresh_from_db()
    hrd.refresh_from_db()
    u.harap(not ka.is_active and hrd.head_id is None, "nonaktif tidak melepas kepala unit")
    baris = f'href="{url("pengguna:edit", ka.pk)}"'                          # baris si kepala (bukan kolom atasan)
    u.get(url("pengguna:index"), tidak_ada=[baris])
    u.get(url("pengguna:index") + "?status=nonaktif", ada=[baris])
    u.post(url("pengguna:activate", ka.pk), harap=302)
    ka.refresh_from_db()
    u.harap(ka.is_active, "pengguna tidak aktif kembali")
    u.harap(AuditLog.objects.filter(object_type="user", object_id=str(ka.pk),
                                    action__in=["user.create", "user.deactivate", "user.activate"]).count() == 3,
            "audit pengguna tidak lengkap")
