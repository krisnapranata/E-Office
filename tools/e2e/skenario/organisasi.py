"""Master Organisasi: pohon struktural RSI Yatofa, komite non-struktural, tambah/ubah/nonaktifkan, cegah melingkar."""
from accounts.models import OrganizationUnit, Role
from accounts.organisasi import seed_rsiy
from testutils.factories import user

from . import skenario
from ._bantu import JUDUL_QA, url


@skenario("organisasi", "Master Organisasi: lihat pohon → tambah sub-unit → ubah → hubungan → nonaktif/aktif; cegah melingkar",
          crud=True, role="staf_igd",
          menu=["organisasi:index", "organisasi:create", "organisasi:edit", "organisasi:deactivate",
                "organisasi:activate", "organisasi:relation_add", "organisasi:relation_remove"])
def _(u):
    seed_rsiy()                                       # idempotent; di DB dev biasanya 0 dibuat
    farmasi = OrganizationUnit.objects.get(code="RSIY-FARMASI")
    direktur = OrganizationUnit.objects.get(code="RSIY-DIR")
    r = u.get(url("organisasi:index"), ada=["Direktur RSI Yatofa", "Kepala Bidang Umum &amp; Kepegawaian",
                                            "Instalasi Pusat Sterilisasi", "Pengawasan &amp; komite", "Komite PPRA",
                                            "Pengawasan → Direktur RSI Yatofa"])
    u.harap(url("organisasi:create") not in u.teks(r), "staf melihat tombol tambah unit")
    u.get(url("organisasi:create"), harap=403)
    u.post(url("organisasi:deactivate", farmasi.pk), {"reason": "x"}, harap=403)

    u.w.admin = user(Role.ADMIN, unit=u.w.dir_unit, username="qa_admin")
    u.sebagai("admin")
    u.get(url("organisasi:create") + f"?induk={farmasi.pk}", ada=["Tambah unit organisasi"])
    u.post(url("organisasi:create"), {"code": "QA-DEPO", "name": f"{JUDUL_QA} Depo Farmasi", "kind": "SUBUNIT",
                                      "parent": farmasi.pk, "order": 1}, harap=302)
    depo = OrganizationUnit.objects.get(code="QA-DEPO")
    u.post(url("organisasi:create"), {"code": "QA-DEPO", "name": "duplikat", "kind": "SUBUNIT", "order": 1},
           harap=200, ada=["text-danger"])                       # kode unik (teks galat mengikuti terjemahan Django)
    u.harap(OrganizationUnit.objects.filter(code="QA-DEPO").count() == 1, "kode unit tergandakan")
    u.get(url("organisasi:edit", depo.pk), ada=["Instalasi Farmasi", "Kepala Seksi Pelayanan Penunjang"])  # jalur
    # cegah melingkar: Instalasi Farmasi tidak boleh di bawah sub-unitnya sendiri
    u.post(url("organisasi:edit", farmasi.pk), {"code": "RSIY-FARMASI", "name": "Instalasi Farmasi",
                                                "kind": "INSTALASI", "parent": depo.pk, "order": farmasi.order},
           harap=200)
    farmasi.refresh_from_db()
    u.harap(farmasi.parent.code == "RSIY-SPENUNJANG", "hubungan melingkar tersimpan")
    u.post(url("organisasi:edit", depo.pk), {"code": "QA-DEPO", "name": f"{JUDUL_QA} Depo Farmasi Rawat Inap",
                                             "kind": "SUBUNIT", "parent": farmasi.pk, "order": 2}, harap=302)
    depo.refresh_from_db()
    u.harap(depo.name.endswith("Rawat Inap"), "perubahan nama tidak tersimpan")
    u.post(url("organisasi:relation_add", depo.pk), {"target": direktur.pk, "kind": "KOORDINASI"}, harap=302)
    rel = depo.relations_out.get()
    u.post(url("organisasi:relation_remove", depo.pk, rel.pk), harap=302)
    u.harap(not depo.relations_out.exists(), "hubungan tidak terhapus")
    u.post(url("organisasi:deactivate", farmasi.pk), {"reason": "uji"}, harap=200, follow=True,
           ada=["sub-unit aktif"])                                  # masih punya Depo aktif
    u.post(url("organisasi:deactivate", depo.pk), {"reason": "Digabung ke Instalasi Farmasi"}, harap=302)
    depo.refresh_from_db()
    u.harap(not depo.is_active, "unit tidak nonaktif")
    u.get(url("organisasi:index"), tidak_ada=["Depo Farmasi Rawat Inap"])
    u.get(url("organisasi:index") + "?nonaktif=1", ada=["Depo Farmasi Rawat Inap"])
    u.get(url("workflow:create"), harap=403)                        # admin tetap bukan pemberi tugas
    u.post(url("organisasi:activate", depo.pk), harap=302)
    depo.refresh_from_db()
    u.harap(depo.is_active, "unit tidak aktif kembali")
