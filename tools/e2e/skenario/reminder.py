"""E-Reminder: skenario E2E PRD 18.4 C no. 4 (H-2), no. 5 (terlambat & eskalasi), no. 10 (kegagalan notifikasi).
Waktu dikendalikan lewat parameter `today` / `send_reminders --date` — tidak menunggu tanggal nyata."""
import io
from datetime import timedelta
from unittest import mock

from django.core.management import call_command
from django.utils import timezone

from notifications import services as notif
from notifications.models import Notification, ReminderLog
from workflow import services as alur

from . import skenario
from ._bantu import JUDUL_QA, url

D = timedelta(days=1)


def _tugas(u, judul, n_hari):
    w = u.w
    return alur.create_task(created_by=w.ka_igd, source_type="LANGSUNG", source_note="QA", title=judul,
                            unit=w.igd, pic=w.staf_igd, due_date=timezone.localdate() + n_hari * D)


@skenario("reminder", "H-2: terkirim ke PIC, tercatat, job diulang tidak duplikat", role="staf_igd",
          menu=["notifications:list"])
def _(u):
    hari_ini = timezone.localdate()
    t = _tugas(u, f"{JUDUL_QA} Reminder H-2", 9)
    call_command("send_reminders", "--date", (hari_ini + 6 * D).isoformat(), stdout=io.StringIO())
    u.harap(not ReminderLog.objects.filter(task=t).exists(), "pengingat terkirim sebelum H-2")
    for _ in range(3):                       # job dijalankan berulang (retry/beat ganda)
        call_command("send_reminders", "--date", (hari_ini + 7 * D).isoformat(), stdout=io.StringIO())
    log = ReminderLog.objects.filter(task=t)
    u.harap(log.count() == 1, f"{log.count()} log pengingat (harap 1)")
    log = log.get()
    u.harap((log.kind, log.days_offset, log.recipient_id, log.status) ==
            ("BEFORE_DUE", 2, u.w.staf_igd.pk, "SENT"), f"log salah: {log.__dict__}")
    u.get(url("notifications:list"), ada=["Pengingat H-2"])


@skenario("reminder", "Terlambat → ditandai & eskalasi ke atasan sesuai ambang", role="ka_igd")
def _(u):
    hari_ini = timezone.localdate()
    t = _tugas(u, f"{JUDUL_QA} Reminder terlambat", -1)
    u.get(url("workflow:detail", t.pk), ada=["Terlambat", "terlambat 1 hari"])
    notif.run_reminders(hari_ini)
    u.harap(ReminderLog.objects.filter(task=t, kind="OVERDUE").exists(), "notifikasi terlambat tidak dibuat")
    u.harap(not ReminderLog.objects.filter(task=t, kind="ESCALATION").exists(), "eskalasi sebelum ambang")
    notif.run_reminders(hari_ini + 2 * D)     # terlambat 3 hari = ambang default
    esc = ReminderLog.objects.get(task=t, kind="ESCALATION")
    u.harap(esc.recipient_id == u.w.ka_igd.pk, f"eskalasi ke {esc.recipient} (harap atasan PIC)")
    u.get(url("notifications:list"), ada=["Eskalasi keterlambatan"])


@skenario("reminder", "Kanal gagal → FAILED tercatat, retry run berikutnya tanpa duplikat", role="staf_igd")
def _(u):
    hari_ini = timezone.localdate()
    t = _tugas(u, f"{JUDUL_QA} Reminder gagal", 2)
    asli = notif.send

    def gagal_untuk_qa(penerima, *a, **kw):
        if penerima.pk == u.w.staf_igd.pk and str(a[0]).startswith("reminder."):
            raise RuntimeError("kanal QA mati")
        return asli(penerima, *a, **kw)

    with mock.patch.object(notif, "send", side_effect=gagal_untuk_qa):
        notif.run_reminders(hari_ini)
    log = ReminderLog.objects.get(task=t)
    u.harap(log.status == "FAILED" and "kanal QA mati" in log.error, f"kegagalan tidak tercatat: {log.status}")
    notif.run_reminders(hari_ini)
    log.refresh_from_db()
    u.harap((log.status, log.attempts) == ("SENT", 2), f"retry: {log.status}/{log.attempts}")
    n = Notification.objects.filter(recipient=u.w.staf_igd, kind="reminder.before_due").count()
    u.harap(n == 1 and ReminderLog.objects.filter(task=t).count() == 1, f"duplikat: {n} notifikasi")
