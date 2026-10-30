"""E-Task Management & E-Monitoring: penugasan langsung, ubah PIC/tenggat, perlu perbaikan, batal, audit trail.
Skenario E2E PRD 18.4 C no. 6 (perlu perbaikan) dan no. 8 (audit trail)."""
from audit.models import AuditLog
from notifications.models import Notification
from workflow.models import Task, TaskStatus

from . import skenario
from ._bantu import JUDUL_QA, berkas, hari, url


def _langsung(u, judul, **lain):
    w = u.w
    data = {"title": judul, "description": "Uji e2e", "source_note": "Temuan ronde mutu", "unit": w.igd.pk,
            "pic": w.staf_igd.pk, "priority": "SEDANG", "classification": "BIASA", "start_date": hari(),
            "due_date": hari(7), "completion_criteria": "Foto + laporan", "requires_evidence": "on",
            "requires_verification": "on"}
    data.update(lain)
    u.get(url("workflow:create"), ada=["Penugasan langsung"])
    u.post(url("workflow:create"), data, harap=302)
    return Task.objects.get(title=judul)


@skenario("tugas", "Penugasan langsung → perlu perbaikan → kirim ulang → selesai (+ notifikasi PIC)", crud=True,
          role="ka_igd", menu=["workflow:create", "workflow:verify", "notifications:list"])
def _(u):
    judul = f"{JUDUL_QA} Perbaiki alur triase"
    t = _langsung(u, judul)
    u.harap(t.status == TaskStatus.MENUNGGU_PENERIMAAN and t.verifier_id == u.w.ka_igd.pk, "tugas tidak terbit")
    u.sebagai("staf_igd")
    u.get(url("notifications:list"), ada=["Tugas baru"])
    u.post(url("workflow:accept", t.pk), harap=302)
    u.post(url("workflow:progress", t.pk), {"progress": 30, "status": "TERHAMBAT"}, harap=200, follow=True,
           ada=["Jelaskan hambatan"])
    u.post(url("workflow:progress", t.pk), {"progress": 30, "status": "TERHAMBAT", "obstacle": "Menunggu alat",
                                            "decision_needed": "Persetujuan pembelian"}, harap=302)
    u.post(url("workflow:progress", t.pk), {"progress": 90, "status": "BERJALAN"}, harap=302)
    u.post(url("workflow:submit", t.pk), harap=200, follow=True, ada=["Unggah minimal satu bukti"])
    u.post(url("workflow:evidence", t.pk), {"file": berkas("skrip.exe")}, harap=200, follow=True,
           ada=["Jenis berkas tidak diizinkan"])
    u.post(url("workflow:evidence", t.pk), {"file": berkas()}, harap=302)
    u.post(url("workflow:submit", t.pk), harap=302)

    u.sebagai("ka_igd")
    u.post(url("workflow:verify", t.pk), {"decision": "revise", "note": ""}, harap=200, follow=True,
           ada=["Alasan perbaikan wajib diisi"])
    u.post(url("workflow:verify", t.pk), {"decision": "revise", "note": "Foto buram"}, harap=302)
    t.refresh_from_db()
    u.harap(t.status == TaskStatus.PERLU_PERBAIKAN, f"status: {t.status}")

    u.sebagai("staf_igd")
    u.get(url("notifications:list"), ada=["Perlu perbaikan"])
    u.get(url("workflow:detail", t.pk), ada=["Foto buram"])
    u.post(url("workflow:evidence", t.pk), {"file": berkas("foto-ulang.pdf")}, harap=302)
    u.post(url("workflow:submit", t.pk), harap=302)
    u.sebagai("ka_igd")
    u.post(url("workflow:verify", t.pk), {"decision": "approve"}, harap=302)
    t.refresh_from_db()
    u.harap(t.status == TaskStatus.SELESAI and t.verifications.count() == 2, "verifikasi kedua tidak menutup")


@skenario("tugas", "Ubah PIC/tenggat beralasan, minta pembaruan, batal → audit trail tercatat", crud=True,
          role="ka_igd", menu=["workflow:reassign", "workflow:request_update", "workflow:cancel"])
def _(u):
    w = u.w
    t = _langsung(u, f"{JUDUL_QA} Kalibrasi monitor")
    u.post(url("workflow:reassign", t.pk), {"pic": w.ka_igd.pk, "due_date": hari(10), "reason": ""}, harap=200,
           follow=True, ada=["alert-danger"])          # teks galat form mengikuti terjemahan Django
    t.refresh_from_db()
    u.harap(t.pic_id == w.staf_igd.pk, "perubahan tanpa alasan ternyata disimpan")
    baru = u.w.staf_igd.__class__.objects.create_user(username="qa_staf_igd2", role="STAF", unit=w.igd)
    u.post(url("workflow:reassign", t.pk), {"pic": baru.pk, "due_date": hari(10), "reason": "Rotasi jaga"},
           harap=302)
    t.refresh_from_db()
    u.harap(t.pic_id == baru.pk and t.due_date.isoformat() == hari(10), "PIC/tenggat tidak berubah")
    u.harap(Notification.objects.filter(recipient=baru, kind="task.assigned").exists(), "PIC baru tidak dinotifikasi")
    u.post(url("workflow:request_update", t.pk), harap=302)
    u.harap(Notification.objects.filter(recipient=baru, kind="task.update_request").exists(),
            "permintaan pembaruan tidak terkirim")
    u.post(url("workflow:cancel", t.pk), {"reason": "Alat diganti vendor"}, harap=302)
    t.refresh_from_db()
    u.harap(t.status == TaskStatus.DIBATALKAN, f"status: {t.status}")
    aksi = set(AuditLog.objects.filter(object_type="task", object_id=str(t.pk)).values_list("action", flat=True))
    kurang = {"task.create", "task.status", "task.reassign", "task.request_update", "task.cancel"} - aksi
    u.harap(not kurang, f"audit trail kurang: {kurang}")
    u.get(url("workflow:detail", t.pk), ada=["task.reassign", "Rotasi jaga"])
    # tugas tertutup: aksi pengendalian ditolak dengan pesan, bukan error
    u.post(url("workflow:reassign", t.pk), {"due_date": hari(20), "reason": "x"}, harap=200, follow=True,
           ada=["sudah ditutup"])
