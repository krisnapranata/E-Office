"""Reminder H-2, terlambat, eskalasi, idempotensi, dan kegagalan (PRD 18.4 A/B)."""
from datetime import timedelta
from io import StringIO
from unittest import mock

from django.core.management import call_command
from django.test import TestCase, override_settings

from notifications import services as notify
from notifications.models import Notification, ReminderLog
from notifications.tasks import run_daily_reminders
from testutils import factories as f
from workflow import services as workflow

D = timedelta(days=1)


class ReminderTests(TestCase):
    def setUp(self):
        self.w = f.World()
        self.today = f.today()

    def test_h2_reminder_sent_once(self):
        task = f.direct_task(self.w.ka_igd, self.w.staf_igd, due=self.today + 2 * D)
        self.assertEqual(notify.run_reminders(self.today), 1)
        self.assertEqual(notify.run_reminders(self.today), 0)  # job diulang
        log = ReminderLog.objects.get(task=task)
        self.assertEqual((log.kind, log.days_offset, log.recipient), ("BEFORE_DUE", 2, self.w.staf_igd))
        self.assertEqual(log.status, ReminderLog.Status.SENT)
        self.assertEqual(Notification.objects.filter(kind="reminder.before_due").count(), 1)

    def test_clock_controlled_h2(self):
        f.direct_task(self.w.ka_igd, self.w.staf_igd, due=self.today + 10 * D)
        self.assertEqual(notify.run_reminders(self.today), 0)
        self.assertEqual(notify.run_reminders(self.today + 8 * D), 1)

    def test_no_reminder_for_closed_tasks(self):
        task = f.direct_task(self.w.ka_igd, self.w.staf_igd, due=self.today + 2 * D)
        workflow.cancel(task, self.w.ka_igd, "batal")
        self.assertEqual(notify.run_reminders(self.today), 0)
        self.assertEqual(notify.run_reminders(self.today + 5 * D), 0)

    def test_overdue_and_escalation(self):
        task = f.direct_task(self.w.ka_igd, self.w.staf_igd, due=self.today - D)
        notify.run_reminders(self.today)
        self.assertTrue(ReminderLog.objects.filter(task=task, kind="OVERDUE").exists())
        self.assertFalse(ReminderLog.objects.filter(task=task, kind="ESCALATION").exists())
        notify.run_reminders(self.today + 2 * D)  # terlambat 3 hari = ambang default
        esc = ReminderLog.objects.get(task=task, kind="ESCALATION")
        self.assertEqual(esc.recipient, self.w.ka_igd)  # atasan langsung PIC
        notify.run_reminders(self.today + 3 * D)
        self.assertEqual(ReminderLog.objects.filter(task=task).count(), 2)

    @override_settings(EOFFICE={"INSTRUCTION_ISSUER_ROLES": [], "REMINDER_DAYS_BEFORE": [2, 1],
                                "ESCALATION_DAYS_OVERDUE": 1})
    def test_configurable_schedule(self):
        task = f.direct_task(self.w.ka_igd, self.w.staf_igd, due=self.today + D)
        notify.run_reminders(self.today - D)
        notify.run_reminders(self.today)
        self.assertEqual(sorted(ReminderLog.objects.filter(task=task)
                                .values_list("days_offset", flat=True)), [1, 2])

    def test_due_date_change_creates_new_reminder(self):
        task = f.direct_task(self.w.ka_igd, self.w.staf_igd, due=self.today + 2 * D)
        notify.run_reminders(self.today)
        workflow.reassign(task, self.w.ka_igd, due_date=self.today + 5 * D, reason="Diperpanjang")
        notify.run_reminders(self.today + 3 * D)
        self.assertEqual(ReminderLog.objects.filter(task=task, kind="BEFORE_DUE").count(), 2)

    def test_failure_logged_and_retried_without_duplicates(self):
        f.direct_task(self.w.ka_igd, self.w.staf_igd, due=self.today + 2 * D)
        with mock.patch.object(notify, "send", side_effect=RuntimeError("kanal mati")), \
                self.assertLogs("notifications.services", "ERROR"):
            self.assertEqual(notify.run_reminders(self.today), 0)
        log = ReminderLog.objects.get()
        self.assertEqual(log.status, ReminderLog.Status.FAILED)
        self.assertIn("kanal mati", log.error)
        self.assertEqual(notify.run_reminders(self.today), 1)
        log.refresh_from_db()
        self.assertEqual((log.status, log.attempts), (ReminderLog.Status.SENT, 2))
        self.assertEqual(ReminderLog.objects.count(), 1)
        self.assertEqual(Notification.objects.filter(kind="reminder.before_due").count(), 1)

    def test_secret_task_title_not_leaked(self):
        f.direct_task(self.w.ka_igd, self.w.staf_igd, due=self.today + 2 * D,
                      title="Investigasi insiden X", classification="RAHASIA")
        notify.run_reminders(self.today)
        for n in Notification.objects.all():
            self.assertNotIn("Investigasi", n.title + n.message)

    def test_celery_task_and_command(self):
        f.direct_task(self.w.ka_igd, self.w.staf_igd, due=self.today + 2 * D)
        self.assertEqual(run_daily_reminders.delay().get(), 1)
        call_command("send_reminders", "--date", (self.today + 2 * D).isoformat(), stdout=StringIO())
        self.assertEqual(ReminderLog.objects.count(), 1)
