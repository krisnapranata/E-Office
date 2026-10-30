"""Permission & kerahasiaan: skenario E2E PRD 18.4 C no. 7 (diizinkan DAN ditolak, termasuk menebak URL)."""
from letters import services as surat
from workflow import services as alur

from . import skenario
from ._bantu import JUDUL_QA, berkas, hari, url


@skenario("akses", "Halaman buat & aksi ditolak untuk peran tanpa hak; auditor hanya baca", role="staf_igd",
          menu=["workflow:create", "instructions:create", "letters:incoming_create", "letters:outgoing_create"])
def _(u):
    for nama in ("workflow:create", "instructions:create", "letters:incoming_create", "letters:outgoing_create"):
        u.get(url(nama), harap=403)
    w = u.w
    t = alur.create_task(created_by=w.ka_igd, source_type="LANGSUNG", source_note="QA", title=f"{JUDUL_QA} Akses",
                         unit=w.igd, pic=w.staf_igd, due_date=None)
    u.post(url("workflow:cancel", t.pk), {"reason": "x"}, harap=403)          # PIC tidak boleh membatalkan
    u.post(url("workflow:verify", t.pk), {"decision": "approve"}, harap=403)   # PIC bukan verifikator
    u.sebagai("auditor")
    u.get(url("workflow:detail", t.pk), ada=[t.title])
    u.post(url("workflow:cancel", t.pk), {"reason": "x"}, harap=403)
    u.post(url("workflow:reassign", t.pk), {"due_date": hari(9), "reason": "x"}, harap=403)
    t.refresh_from_db()
    u.harap(t.status == "MENUNGGU_PENERIMAAN" and t.due_date is None, "aksi terlarang ternyata mengubah tugas")


@skenario("akses", "Unit lain & menebak URL: tugas, bukti, surat → 404", role="staf_farmasi")
def _(u):
    w = u.w
    t = alur.create_task(created_by=w.ka_igd, source_type="LANGSUNG", source_note="QA",
                         title=f"{JUDUL_QA} Tugas IGD", unit=w.igd, pic=w.staf_igd, due_date=None)
    alur.accept_task(t, w.staf_igd)
    alur.report_progress(t, w.staf_igd, progress=10, status="BERJALAN")
    ev = alur.add_evidence(t, w.staf_igd, berkas())
    for x in (url("workflow:detail", t.pk), url("workflow:evidence_download", ev.pk),
              url("workflow:detail", 999999999), url("instructions:detail", 999999999),
              url("letters:disposition_detail", 999999999)):
        u.get(x, harap=404)
    u.post(url("workflow:cancel", t.pk), {"reason": "x"}, harap=404)
    u.get(url("workflow:list") + "?q=Tugas+IGD", tidak_ada=[t.title])


@skenario("akses", "Dokumen Rahasia: hanya pihak terlibat & Direktur; tidak bocor di notifikasi", role="ka_igd")
def _(u):
    w = u.w
    rahasia = f"{JUDUL_QA} Investigasi insiden"
    t = alur.create_task(created_by=w.direktur, source_type="LANGSUNG", source_note="QA", title=rahasia,
                         unit=w.igd, pic=w.staf_igd, due_date=None, classification="RAHASIA")
    s = surat.register_incoming(w.sekretaris, letter_number="QA/R/1", letter_date=hari(), received_date=hari(),
                                sender="QA", subject=f"{JUDUL_QA} Surat rahasia", classification="RAHASIA")
    for peran in ("ka_igd", "wadir", "auditor"):
        u.sebagai(peran)
        u.get(url("workflow:detail", t.pk), harap=404)
        u.get(url("workflow:list"), tidak_ada=[rahasia])
        u.get(url("letters:incoming_detail", s.pk), harap=404)
    for peran in ("staf_igd", "direktur"):
        u.sebagai(peran)
        u.get(url("workflow:detail", t.pk), ada=[rahasia])
    u.sebagai("staf_igd")
    u.get(url("notifications:list"), ada=["(rahasia)"], tidak_ada=["Investigasi insiden"])


@skenario("akses", "Keluar (POST) → tanpa login dialihkan ke halaman login; healthz terbuka",
          menu=["logout", "login", "healthz"])
def _(u):
    u.get("/", ada=["Keluar"])
    u.pengguna = None                    # logout memang mengalihkan ke /login/
    r = u.post(url("logout"), harap=302)
    u.harap("/login/" in r["Location"], f"logout mengarah ke {r['Location']}")
    u.get(url("healthz"), ada=["ok"])
    for x in ("/", url("workflow:list"), url("instructions:list"), url("letters:incoming_list")):
        r = u.get(x, harap=302)
        u.harap("/login/" in r["Location"], f"{x} tidak dialihkan ke login: {r['Location']}")
    u.get(url("login"), ada=["Selamat Datang", 'id="leForm"'])
    r = u.post(url("login"), {"username": u.w.direktur.username, "password": "salah"}, harap=200,
               dari=url("login"))
    u.harap("le-pesan-error" in u.teks(r), "login gagal tanpa pesan galat")
