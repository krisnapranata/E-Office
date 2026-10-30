"""Layanan notifikasi dan pengingat. Pesan tidak memuat isi dokumen rahasia (PRD 6.6)."""
import logging
from datetime import timedelta

from django.conf import settings
from django.db import IntegrityError, transaction
from django.urls import reverse
from django.utils import timezone

from accounts.permissions import Classification

from .models import Notification, ReminderLog

logger = logging.getLogger(__name__)


def _task_label(task):
    if task.classification == Classification.RAHASIA:
        return f"T-{task.pk} (rahasia)"
    return f"T-{task.pk} {task.title}"


def _task_url(task):
    return reverse("workflow:detail", args=[task.pk])


def send(recipient, kind, title, message="", url=""):
    if recipient is None:
        return None
    return Notification.objects.create(
        recipient=recipient, kind=kind, title=title[:255], message=message, url=url
    )


def task_assigned(task):
    due = f" Tenggat {task.due_date:%d-%m-%Y}." if task.due_date else ""
    send(task.pic, "task.assigned", f"Tugas baru: {_task_label(task)}",
         f"Anda ditetapkan sebagai PIC.{due}", _task_url(task))


def verification_requested(task):
    send(task.verifier, "task.verification", f"Menunggu verifikasi: {_task_label(task)}",
         "PIC telah mengirim hasil dan bukti.", _task_url(task))


def revision_requested(task, note):
    send(task.pic, "task.revision", f"Perlu perbaikan: {_task_label(task)}",
         "Verifikator mengembalikan hasil. Lihat alasan pada halaman tugas.", _task_url(task))


def task_closed(task):
    for user in {task.pic, task.created_by, task.verifier}:
        send(user, "task.closed", f"Tugas {task.get_status_display().lower()}: {_task_label(task)}",
             "", _task_url(task))


def update_requested(task, requester):
    send(task.pic, "task.update_request", f"Permintaan pembaruan: {_task_label(task)}",
         f"{requester} meminta pembaruan progres.", _task_url(task))


def instruction_issued(instruction, user):
    label = instruction.code if instruction.classification == Classification.RAHASIA else (
        f"{instruction.code} {instruction.title}")
    send(user, "instruction.issued", f"Instruksi baru: {label}", "",
         reverse("instructions:detail", args=[instruction.pk]))


def disposition_received(disposition):
    send(disposition.to_user, "disposition.received",
         f"Disposisi baru: {disposition.letter.agenda_number}", "",
         reverse("letters:disposition_detail", args=[disposition.pk]))


# ---------------------------------------------------------------- pengingat & eskalasi

def escalation_target(task):
    if task.pic.supervisor_id:
        return task.pic.supervisor
    head = task.unit.head
    return head if head and head.pk != task.pic_id else None


def _deliver(log, title, message, url):
    """Kirim satu pengingat. Hanya mengirim bila belum SENT; kegagalan dicatat untuk retry."""
    with transaction.atomic():
        log = ReminderLog.objects.select_for_update().get(pk=log.pk)
        if log.status == ReminderLog.Status.SENT:
            return False
        log.attempts += 1
        try:
            with transaction.atomic():
                send(log.recipient, f"reminder.{log.kind.lower()}", title, message, url)
        except Exception as exc:  # noqa: BLE001 — kegagalan kanal harus tercatat, bukan crash
            logger.exception("Gagal mengirim pengingat %s", log.pk)
            log.status = ReminderLog.Status.FAILED
            log.error = str(exc)[:1000]
            log.save()
            return False
        log.status = ReminderLog.Status.SENT
        log.sent_at = timezone.now()
        log.error = ""
        log.save()
        return True


def _schedule(task, kind, days_offset, recipient, handled):
    try:
        with transaction.atomic():
            log, _ = ReminderLog.objects.get_or_create(
                task=task, kind=kind, days_offset=days_offset, due_date=task.due_date,
                recipient=recipient, channel="internal",
            )
    except IntegrityError:  # job paralel membuat baris yang sama
        log = ReminderLog.objects.get(
            task=task, kind=kind, days_offset=days_offset, due_date=task.due_date,
            recipient=recipient, channel="internal",
        )
    handled.add(log.pk)
    return log


def run_reminders(today=None):
    """Dijalankan harian oleh Celery beat atau `manage.py send_reminders`. Idempotent."""
    from workflow.models import Task

    today = today or timezone.localdate()
    cfg = settings.EOFFICE
    sent = 0
    handled = set()
    tasks = Task.objects.open().exclude(due_date=None).select_related("pic", "unit__head")

    for days in cfg["REMINDER_DAYS_BEFORE"]:
        for task in tasks.filter(due_date=today + timedelta(days=days)):
            log = _schedule(task, ReminderLog.Kind.BEFORE_DUE, days, task.pic, handled)
            sent += _deliver(log, f"Pengingat H-{days}: {_task_label(task)}",
                             f"Tenggat {task.due_date:%d-%m-%Y}.", _task_url(task))

    for task in tasks.filter(due_date__lt=today):
        log = _schedule(task, ReminderLog.Kind.OVERDUE, 0, task.pic, handled)
        sent += _deliver(log, f"Terlambat: {_task_label(task)}",
                         f"Tenggat {task.due_date:%d-%m-%Y} telah terlewati.", _task_url(task))
        late_days = (today - task.due_date).days
        target = escalation_target(task)
        if target and late_days >= cfg["ESCALATION_DAYS_OVERDUE"]:
            log = _schedule(task, ReminderLog.Kind.ESCALATION, cfg["ESCALATION_DAYS_OVERDUE"],
                            target, handled)
            sent += _deliver(log, f"Eskalasi keterlambatan: {_task_label(task)}",
                             f"PIC {task.pic}, terlambat {late_days} hari.", _task_url(task))

    # Retry kegagalan dari run sebelumnya untuk tugas yang masih terbuka.
    failed = ReminderLog.objects.filter(status=ReminderLog.Status.FAILED, task__in=tasks)
    for log in failed.exclude(pk__in=handled).select_related("task"):
        sent += _deliver(log, f"Pengingat: {_task_label(log.task)}", "", _task_url(log.task))
    return sent
