"""Unit test aturan bisnis tugas (PRD 18.4 A)."""
from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from audit.models import AuditLog
from notifications.models import Notification
from testutils import factories as f
from workflow import services
from workflow.models import Task, TaskSource, TaskStatus as S


class TaskRulesTests(TestCase):
    def setUp(self):
        self.w = f.World()

    def _running_task(self, **kw):
        task = f.direct_task(self.w.ka_igd, self.w.staf_igd, **kw)
        services.accept_task(task, self.w.staf_igd)
        services.report_progress(task, self.w.staf_igd, progress=10, status=S.BERJALAN)
        return task

    def test_direct_task_requires_reason(self):
        with self.assertRaises(ValidationError):
            services.create_task(created_by=self.w.ka_igd, source_type=TaskSource.LANGSUNG,
                                 title="X", unit=self.w.igd, pic=self.w.staf_igd)

    def test_due_before_start_rejected(self):
        with self.assertRaises(ValidationError):
            f.direct_task(self.w.ka_igd, self.w.staf_igd, start_date=f.today(),
                          due=f.today() - timedelta(days=1))

    def test_issue_notifies_pic_and_awaits_acceptance(self):
        task = f.direct_task(self.w.ka_igd, self.w.staf_igd)
        self.assertEqual(task.status, S.MENUNGGU_PENERIMAAN)
        self.assertTrue(Notification.objects.filter(recipient=self.w.staf_igd,
                                                    kind="task.assigned").exists())

    def test_overdue_computation(self):
        task = f.direct_task(self.w.ka_igd, self.w.staf_igd, due=f.today() - timedelta(days=1))
        self.assertTrue(task.is_overdue())
        self.assertIn(task, Task.objects.overdue())
        services.cancel(task, self.w.ka_igd, "tidak relevan")
        self.assertFalse(task.is_overdue())
        self.assertNotIn(task, Task.objects.overdue())

    def test_due_soon_window(self):
        soon = f.direct_task(self.w.ka_igd, self.w.staf_igd, due=f.today() + timedelta(days=2))
        later = f.direct_task(self.w.ka_igd, self.w.staf_igd, due=f.today() + timedelta(days=3))
        qs = Task.objects.due_soon()
        self.assertIn(soon, qs)
        self.assertNotIn(later, qs)

    def test_invalid_transition_rejected(self):
        task = f.direct_task(self.w.ka_igd, self.w.staf_igd)
        with self.assertRaises(ValidationError):
            services.verify(task, self.w.ka_igd, approved=True)

    def test_progress_100_does_not_close(self):
        task = self._running_task()
        services.report_progress(task, self.w.staf_igd, progress=100, status=S.BERJALAN)
        task.refresh_from_db()
        self.assertEqual(task.status, S.BERJALAN)
        self.assertIsNone(task.closed_at)

    def test_blocked_requires_obstacle(self):
        task = self._running_task()
        with self.assertRaises(ValidationError):
            services.report_progress(task, self.w.staf_igd, progress=20, status=S.TERHAMBAT)

    def test_submit_requires_evidence(self):
        task = self._running_task()
        with self.assertRaises(ValidationError):
            services.submit_result(task, self.w.staf_igd)

    def test_only_pic_can_submit(self):
        task = self._running_task()
        services.add_evidence(task, self.w.staf_igd, f.dummy_file())
        with self.assertRaises(PermissionDenied):
            services.submit_result(task, self.w.ka_igd)

    def test_verification_flow_with_revision(self):
        task = self._running_task()
        services.add_evidence(task, self.w.staf_igd, f.dummy_file())
        services.submit_result(task, self.w.staf_igd)
        self.assertEqual(task.status, S.MENUNGGU_VERIFIKASI)
        with self.assertRaises(ValidationError):
            services.verify(task, self.w.ka_igd, approved=False, note="")
        services.verify(task, self.w.ka_igd, approved=False, note="Bukti kurang lengkap")
        self.assertEqual(task.status, S.PERLU_PERBAIKAN)
        self.assertTrue(Notification.objects.filter(recipient=self.w.staf_igd,
                                                    kind="task.revision").exists())
        services.add_evidence(task, self.w.staf_igd, f.dummy_file("bukti2.pdf"))
        services.submit_result(task, self.w.staf_igd)
        services.verify(task, self.w.ka_igd, approved=True)
        self.assertEqual(task.status, S.SELESAI)
        self.assertIsNotNone(task.closed_at)
        self.assertTrue(task.finished_on_time())

    def test_non_verifier_cannot_verify(self):
        task = self._running_task()
        services.add_evidence(task, self.w.staf_igd, f.dummy_file())
        services.submit_result(task, self.w.staf_igd)
        with self.assertRaises(PermissionDenied):
            services.verify(task, self.w.staf_farmasi, approved=True)

    def test_without_verification_closes_on_submit(self):
        task = self._running_task(requires_verification=False, requires_evidence=False)
        services.submit_result(task, self.w.staf_igd)
        self.assertEqual(task.status, S.SELESAI)

    def test_reassign_requires_reason_and_is_audited(self):
        task = f.direct_task(self.w.ka_igd, self.w.staf_igd)
        new_due = f.today() + timedelta(days=14)
        with self.assertRaises(ValidationError):
            services.reassign(task, self.w.ka_igd, due_date=new_due, reason=" ")
        other = f.user(unit=self.w.igd)
        services.reassign(task, self.w.ka_igd, pic=other, due_date=new_due, reason="Rotasi")
        log = AuditLog.objects.get(action="task.reassign", object_id=str(task.pk))
        self.assertEqual(log.user, self.w.ka_igd)
        self.assertEqual(log.changes["reason"], "Rotasi")
        self.assertIn("pic", log.changes)
        self.assertIn("due_date", log.changes)

    def test_pic_cannot_reassign_own_task(self):
        task = f.direct_task(self.w.ka_igd, self.w.staf_igd)
        with self.assertRaises(PermissionDenied):
            services.reassign(task, self.w.staf_igd, due_date=f.today(), reason="x")

    def test_status_changes_audited(self):
        task = self._running_task()
        actions = list(AuditLog.objects.filter(object_id=str(task.pk), object_type="task")
                       .values_list("action", flat=True))
        self.assertIn("task.create", actions)
        self.assertGreaterEqual(actions.count("task.status"), 3)

    def test_audit_log_immutable(self):
        task = f.direct_task(self.w.ka_igd, self.w.staf_igd)
        log = AuditLog.objects.filter(object_id=str(task.pk)).first()
        log.action = "tamper"
        with self.assertRaises(ValueError):
            log.save()
        with self.assertRaises(ValueError):
            log.delete()

    def test_upload_extension_validated(self):
        task = self._running_task()
        with self.assertRaises(ValidationError):
            services.add_evidence(task, self.w.staf_igd, f.dummy_file("skrip.exe", b"MZ"))


class DueLabelTests(TestCase):
    def test_labels(self):
        w = f.World()
        today = f.today()
        task = f.direct_task(w.ka_igd, w.staf_igd, due=today - timedelta(days=3))
        self.assertEqual(task.due_label(), "terlambat 3 hari")
        task.due_date = today
        self.assertEqual(task.due_label(), "hari ini")
        task.due_date = today + timedelta(days=2)
        self.assertEqual(task.due_label(), "2 hari lagi")
