"""E-Notulen & Keputusan + E-Follow Up: skenario E2E PRD 18.4 C no. 3 (keputusan rapat → tindak lanjut tanpa duplikasi)."""
from datetime import timedelta

from django.utils import timezone

from agenda.models import AgendaEvent
from agenda.services import create_event
from notulen.models import MeetingMinutes
from workflow.models import Task, TaskStatus

from . import skenario
from ._bantu import JUDUL_QA, berkas, hari, url


@skenario("notulen", "Rapat → notulen + keputusan & PIC → dikembalikan → disetujui → tindak lanjut → selesai",
          crud=True, role="sekretaris",
          menu=["notulen:list", "notulen:create", "notulen:detail", "notulen:edit", "notulen:print",
                "notulen:attachment", "notulen:decision_add", "notulen:decision_remove", "notulen:assignee_add",
                "notulen:assignee_remove", "notulen:submit", "notulen:return", "notulen:approve",
                "tindaklanjut:index", "tindaklanjut:meeting"])
def _(u):
    w = u.w
    judul = f"{JUDUL_QA} Rapat evaluasi mutu"
    ev = create_event(w.direktur, participants=[w.sekretaris, w.ka_igd, w.ka_farmasi], title=judul, kind="RAPAT",
                      start=timezone.now() - timedelta(hours=2), location="Ruang Direksi")
    u.get(url("agenda:detail", ev.pk), ada=["Tulis notulen"])
    u.get(url("notulen:create", ev.pk), ada=["Notulen"])
    u.post(url("notulen:create", ev.pk), {"attendees": [w.direktur.pk, w.ka_igd.pk, w.ka_farmasi.pk],
                                          "discussion": "Evaluasi waktu tunggu IGD dan stok obat.",
                                          "summary": "Perlu perbaikan alur.", "attachment": berkas("notulen.pdf")},
           harap=302)
    m = MeetingMinutes.objects.get(event=ev)
    det = url("notulen:detail", m.pk)
    u.post(url("notulen:decision_add", m.pk), {"text": "Turunkan waktu tunggu IGD < 30 menit", "requires_action": "on",
                                               "priority": "TINGGI", "due_date": ""}, harap=200, follow=True,
           ada=["wajib memiliki tenggat"])
    u.post(url("notulen:decision_add", m.pk), {"text": "Turunkan waktu tunggu IGD < 30 menit", "requires_action": "on",
                                               "priority": "TINGGI", "due_date": hari(14),
                                               "completion_criteria": "Laporan waktu tunggu"}, harap=302)
    u.post(url("notulen:decision_add", m.pk), {"text": "Stok obat dilaporkan mingguan", "requires_action": "on",
                                               "priority": "SEDANG", "due_date": hari(7)}, harap=302)
    u.post(url("notulen:decision_add", m.pk), {"text": "Informasi: akreditasi bulan depan", "priority": "RENDAH"},
           harap=302)
    d1, d2, d3 = m.decisions.order_by("number")
    u.post(url("notulen:submit", m.pk), harap=200, follow=True, ada=["belum memiliki PIC/unit"])
    u.post(url("notulen:assignee_add", m.pk, d1.pk), {"unit": w.igd.pk, "pic": w.ka_igd.pk}, harap=302)
    u.post(url("notulen:assignee_add", m.pk, d1.pk), {"unit": w.igd.pk, "pic": w.staf_igd.pk}, harap=302)
    u.post(url("notulen:assignee_add", m.pk, d2.pk), {"unit": w.farmasi.pk, "pic": w.ka_farmasi.pk}, harap=302)
    salah = d1.assignees.get(pic=w.staf_igd)
    u.post(url("notulen:assignee_remove", m.pk, salah.pk), harap=302)
    u.post(url("notulen:decision_remove", m.pk, d3.pk), harap=302)
    u.post(url("notulen:edit", m.pk), {"attendees": [w.direktur.pk, w.ka_igd.pk, w.ka_farmasi.pk],
                                       "discussion": "Evaluasi waktu tunggu IGD dan stok obat (revisi).",
                                       "summary": "Perlu perbaikan alur."}, harap=302)
    u.get(url("notulen:attachment", m.pk), harap=200)
    u.post(url("notulen:submit", m.pk), harap=302)
    u.post(url("notulen:approve", m.pk), harap=403)             # notulis bukan pimpinan rapat

    u.sebagai("direktur")
    u.post(url("notulen:return", m.pk), {"note": ""}, harap=200, follow=True, ada=["wajib diisi"])
    u.post(url("notulen:return", m.pk), {"note": "Lengkapi daftar hadir"}, harap=302)
    u.sebagai("sekretaris")
    u.get(det, ada=["Lengkapi daftar hadir"])
    u.post(url("notulen:submit", m.pk), harap=302)
    u.sebagai("direktur")
    u.get(url("notulen:list"), ada=[judul])
    u.post(url("notulen:approve", m.pk), harap=302)
    m.refresh_from_db()
    ev.refresh_from_db()
    u.harap(m.status == MeetingMinutes.Status.DISETUJUI and m.revision == 2, f"notulen {m.status} rev {m.revision}")
    u.harap(ev.status == AgendaEvent.Status.SELESAI, "rapat tidak ditandai selesai")
    tl = Task.objects.filter(decision__minutes=m)
    u.harap(tl.count() == 2 and set(tl.values_list("source_type", flat=True)) == {"KEPUTUSAN_RAPAT"},
            f"tindak lanjut {tl.count()} (harap 2)")
    u.harap(all(t.verifier_id == w.direktur.pk for t in tl), "pemeriksa tindak lanjut bukan pimpinan rapat")
    u.post(url("notulen:approve", m.pk), harap=403)              # tidak bisa disetujui ulang
    u.harap(tl.count() == 2, "persetujuan ulang membuat duplikat")
    u.get(url("notulen:print", m.pk), ada=["NOTULEN RAPAT", "Turunkan waktu tunggu"])

    u.sebagai("ka_igd")
    t = tl.get(pic=w.ka_igd)
    u.get(url("tindaklanjut:index") + "?status=terbuka", ada=[f"T-{t.pk}"])
    u.get(url("tindaklanjut:meeting", ev.pk), ada=["Keputusan 1"])
    u.post(url("workflow:accept", t.pk), harap=302)
    u.post(url("workflow:progress", t.pk), {"progress": 100, "status": "BERJALAN"}, harap=302)
    u.post(url("workflow:evidence", t.pk), {"file": berkas("laporan-waktu-tunggu.pdf")}, harap=302)
    u.post(url("workflow:submit", t.pk), harap=302)
    u.sebagai("direktur")
    u.post(url("workflow:verify", t.pk), {"decision": "approve"}, harap=302)
    t.refresh_from_db()
    u.harap(t.status == TaskStatus.SELESAI, f"tindak lanjut {t.status}")
    r = u.get(url("tindaklanjut:meeting", ev.pk) + "?belum=1&cetak=1", ada=["BELUM SELESAI"])
    u.harap(f"{w.ka_farmasi}" in u.teks(r) and f"T-{t.pk}" not in u.teks(r), "daftar belum selesai keliru")

    u.sebagai("staf_farmasi")                                   # tidak diundang
    u.get(det, harap=404)
    u.get(url("tindaklanjut:meeting", ev.pk), harap=404)
