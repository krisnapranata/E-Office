"""E-Surat & E-Disposisi: skenario E2E PRD 18.4 C no. 2."""
from letters.models import Disposition, IncomingLetter, OutgoingLetter
from workflow.models import TaskStatus

from . import skenario
from ._bantu import JUDUL_QA, berkas, hari, url


@skenario("surat", "Surat masuk → disposisi → penerusan → tugas tertaut → selesai", crud=True, role="sekretaris",
          menu=["letters:incoming_list", "letters:incoming_create", "letters:incoming_detail",
                "letters:disposition_create", "letters:disposition_list", "letters:disposition_detail",
                "letters:attachment"])
def _(u):
    w = u.w
    perihal = f"{JUDUL_QA} Permintaan data mutu"
    u.get(url("letters:incoming_create"), ada=["Catat surat masuk"])
    u.post(url("letters:incoming_create"), {
        "letter_number": "QA/001/X/2026", "letter_date": hari(-1), "received_date": hari(), "sender": "Dinas QA",
        "subject": perihal, "summary": "Mohon data indikator mutu.", "classification": "BIASA",
        "attachment": berkas("surat.pdf")}, harap=302)
    surat = IncomingLetter.objects.get(subject=perihal)
    u.harap(surat.agenda_number.startswith("SM/"), f"nomor agenda tidak otomatis: {surat.agenda_number}")
    u.get(url("letters:incoming_list") + "?q=Permintaan+data+mutu", ada=[surat.agenda_number])

    u.sebagai("direktur")
    u.get(url("letters:incoming_detail", surat.pk), ada=["Buat disposisi"])
    u.post(url("letters:disposition_create", surat.pk), {
        "to_user": w.wadir.pk, "to_unit": w.yanmed.pk, "directive": "Koordinasikan dengan IGD",
        "priority": "TINGGI", "due_date": hari(4), "requires_action": "on"}, harap=302)
    d1 = Disposition.objects.get(letter=surat)

    u.sebagai("wadir")
    u.get(url("letters:disposition_list") + "?pending=1", ada=[surat.agenda_number])
    u.get(url("letters:disposition_detail", d1.pk), ada=["Teruskan disposisi"])
    d1.refresh_from_db()
    u.harap(d1.status == Disposition.Status.DIBACA and d1.read_at, f"status dibaca tidak tercatat: {d1.status}")
    u.get(url("letters:disposition_create", surat.pk) + f"?parent={d1.pk}", ada=["Meneruskan disposisi"])
    u.post(url("letters:disposition_create", surat.pk), {
        "parent": d1.pk, "to_user": w.ka_igd.pk, "to_unit": w.igd.pk, "directive": "Siapkan data IGD",
        "priority": "TINGGI", "due_date": hari(3), "requires_action": "on"}, harap=302)
    d2 = Disposition.objects.get(parent=d1)

    u.sebagai("ka_igd")
    u.get(url("letters:attachment", "masuk", surat.pk), harap=200)
    task = d2.tasks.get()
    u.get(url("workflow:detail", task.pk), ada=[f"Disposisi #{d2.pk}"])
    u.post(url("workflow:accept", task.pk), harap=302)
    u.post(url("workflow:progress", task.pk), {"progress": 100, "status": "BERJALAN"}, harap=302)
    u.post(url("workflow:evidence", task.pk), {"file": berkas("data.pdf")}, harap=302)
    u.post(url("workflow:submit", task.pk), harap=302)
    u.sebagai("wadir")
    u.post(url("workflow:verify", task.pk), {"decision": "approve"}, harap=302)
    d2.refresh_from_db()
    task.refresh_from_db()
    u.harap(task.status == TaskStatus.SELESAI, f"tugas disposisi: {task.status}")
    u.harap(d2.status == Disposition.Status.SELESAI, f"status disposisi tidak mengikuti tugas: {d2.status}")

    u.sebagai("staf_farmasi")      # tidak terlibat -> tidak boleh melihat surat/lampiran
    u.get(url("letters:incoming_detail", surat.pk), harap=404)
    u.get(url("letters:attachment", "masuk", surat.pk), harap=404)


@skenario("surat", "Surat keluar: catat dengan lampiran, daftar, unduh", crud=True, role="sekretaris",
          menu=["letters:outgoing_list", "letters:outgoing_create", "letters:attachment"])
def _(u):
    perihal = f"{JUDUL_QA} Balasan permintaan data"
    u.get(url("letters:outgoing_create"), ada=["Catat surat keluar"])
    u.post(url("letters:outgoing_create"), {
        "letter_date": hari(), "recipient": "Dinas QA", "subject": perihal, "summary": "Data terlampir.",
        "classification": "BIASA", "attachment": berkas("balasan.pdf")}, harap=302)
    s = OutgoingLetter.objects.get(subject=perihal)
    u.harap(s.letter_number.startswith("SK/"), f"nomor surat keluar: {s.letter_number}")
    u.get(url("letters:outgoing_list"), ada=[s.letter_number])
    u.get(url("letters:attachment", "keluar", s.pk), harap=200)
