"""E-Arsip: arsip otomatis dari modul lain, arsip manual, versi, metadata, pencarian, retensi & pemusnahan, akses."""
from datetime import date

from arsip.models import ArchiveDocument
from letters.models import IncomingLetter

from . import skenario
from ._bantu import JUDUL_QA, berkas, hari, url


@skenario("arsip", "Arsip otomatis: lampiran surat & bukti tugas masuk arsip; hak akses mengikuti objek asal",
          crud=True, role="sekretaris", menu=["arsip:list", "arsip:detail", "arsip:download"])
def _(u):
    w = u.w
    perihal = f"{JUDUL_QA} Surat arsip otomatis"
    u.post(url("letters:incoming_create"), {"letter_number": "QA/ARS/1", "letter_date": hari(), "received_date": hari(),
                                            "sender": "QA", "subject": perihal, "classification": "BIASA",
                                            "attachment": berkas("surat-arsip.pdf")}, harap=302)
    s = IncomingLetter.objects.get(subject=perihal)
    doc = ArchiveDocument.objects.get(source_id=s.pk, doc_type="SURAT_MASUK")
    u.harap(doc.versions.count() == 1 and doc.number == "QA/ARS/1", "arsip surat tidak lengkap")
    u.get(url("arsip:list") + "?q=ARS%2F1", ada=[perihal])
    u.get(url("arsip:detail", doc.pk), ada=["v1", "Diarsipkan otomatis"])
    u.get(url("arsip:download", doc.latest.pk), harap=200)
    u.sebagai("staf_igd")                       # tidak terlibat surat
    u.get(url("arsip:detail", doc.pk), harap=404)
    u.get(url("arsip:download", doc.latest.pk), harap=404)
    from workflow import services as alur

    t = alur.create_task(created_by=w.ka_igd, source_type="LANGSUNG", source_note="QA", title=f"{JUDUL_QA} Bukti arsip",
                         unit=w.igd, pic=w.staf_igd, due_date=None)
    alur.accept_task(t, w.staf_igd)
    alur.report_progress(t, w.staf_igd, progress=50, status="BERJALAN")
    u.post(url("workflow:evidence", t.pk), {"file": berkas("bukti-arsip.pdf"), "description": "foto"}, harap=302)
    b = ArchiveDocument.objects.get(doc_type="BUKTI", number=f"T-{t.pk}")
    u.get(url("arsip:detail", b.pk), ada=["Bukti pelaksanaan"])   # PIC = pemilik
    u.sebagai("ka_igd")                                               # atasan unit
    u.get(url("arsip:detail", b.pk), harap=200)
    u.sebagai("staf_farmasi")
    u.get(url("arsip:detail", b.pk), harap=404)


@skenario("arsip", "Arsip manual: unggah, versi beralasan, metadata, retensi lewat → usul musnah → Direktur setuju",
          crud=True, role="arsip", menu=["arsip:create", "arsip:version_add", "arsip:metadata", "arsip:propose",
                                         "arsip:decide"])
def _(u):
    w = u.w
    judul = f"{JUDUL_QA} SK lama 2015"
    u.get(url("arsip:create"), ada=["Arsipkan dokumen"])
    u.post(url("arsip:create"), {"doc_type": "LAINNYA", "number": "QA/SK/2015/01", "doc_date": "2015-02-01",
                                 "title": judul, "unit": w.dir_unit.pk, "classification": "BIASA",
                                 "keywords": "sk lama", "file": berkas("sk.pdf")}, harap=302)
    doc = ArchiveDocument.objects.get(title=judul)
    u.harap(doc.retention_until == date(2020, 2, 1), f"retensi {doc.retention_until} (harap 5 tahun)")
    u.post(url("arsip:version_add", doc.pk), {"file": berkas("sk-rev.pdf"), "note": ""}, harap=200, follow=True,
           ada=["alert-danger"])
    u.post(url("arsip:version_add", doc.pk), {"file": berkas("sk-rev.pdf"), "note": "Salinan bertanda tangan"},
           harap=302)
    u.harap(doc.versions.count() == 2, "versi baru tidak tersimpan")
    u.post(url("arsip:metadata", doc.pk), {"number": "QA/SK/2015/01", "doc_date": "2015-02-01", "title": judul,
                                           "unit": w.dir_unit.pk, "classification": "TERBATAS",
                                           "keywords": "sk lama, kepegawaian"}, harap=302)
    doc.refresh_from_db()
    u.harap(doc.classification == "TERBATAS" and "kepegawaian" in doc.keywords, "metadata tidak tersimpan")
    u.get(url("arsip:list") + "?status=RETENSI", ada=[judul])
    u.post(url("arsip:propose", doc.pk), {"note": "Masa retensi habis"}, harap=302)
    u.post(url("arsip:decide", doc.pk), {"decision": "approve", "note": "x"}, harap=403)   # bukan Direktur
    u.sebagai("direktur")
    u.post(url("arsip:decide", doc.pk), {"decision": "approve", "note": ""}, harap=200, follow=True,
           ada=["Berita acara pemusnahan wajib"])
    u.post(url("arsip:decide", doc.pk), {"decision": "approve", "note": "BA-QA-01 disaksikan Komite"}, harap=302)
    doc.refresh_from_db()
    u.harap(doc.status == "DIMUSNAHKAN" and doc.disposal_approved_by_id == w.direktur.pk, f"status {doc.status}")
    u.get(url("arsip:download", doc.latest.pk), harap=404)        # berkas tidak bisa diunduh lagi
    u.get(url("arsip:detail", doc.pk), ada=["BA-QA-01", "(dimusnahkan)"])
    u.sebagai("staf_igd")
    u.get(url("arsip:create"), harap=403)


@skenario("arsip", "Retensi belum habis: usulan pemusnahan ditolak sistem", role="arsip")
def _(u):
    from arsip.services import create_manual

    doc = create_manual(u.w.arsip, berkas(), doc_type="LAINNYA", doc_date=date.today(), title=f"{JUDUL_QA} Baru",
                        classification="BIASA")
    u.post(url("arsip:propose", doc.pk), {"note": "coba"}, harap=200, follow=True, ada=["Masa retensi belum berakhir"])
    doc.refresh_from_db()
    u.harap(doc.status == "AKTIF", "dokumen aktif berubah status")
