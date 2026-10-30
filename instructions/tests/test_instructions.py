from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from audit.models import AuditLog
from instructions import services
from instructions.models import Instruction, InstructionTarget
from testutils import factories as f
from workflow.models import Task, TaskStatus


class InstructionTests(TestCase):
    def setUp(self):
        self.w = f.World()

    def _draft(self, user=None, **kw):
        return services.create_instruction(
            user or self.w.direktur, title="Evaluasi waktu tunggu IGD", description="Lakukan evaluasi.",
            instruction_date=f.today(), due_date=f.today() + timedelta(days=7), **kw)

    def test_staff_cannot_create(self):
        with self.assertRaises(PermissionDenied):
            self._draft(self.w.staf_igd)

    def test_code_unique_and_sequential(self):
        a, b = self._draft(), self._draft()
        self.assertNotEqual(a.code, b.code)
        self.assertTrue(a.code.startswith("INS/"))

    def test_issue_requires_targets(self):
        with self.assertRaises(ValidationError):
            services.issue(self._draft(), self.w.direktur)

    def test_issue_creates_one_task_per_target_without_duplicates(self):
        ins = self._draft()
        InstructionTarget.objects.create(instruction=ins, unit=self.w.igd, pic=self.w.ka_igd)
        InstructionTarget.objects.create(instruction=ins, unit=self.w.farmasi, pic=self.w.ka_farmasi)
        services.issue(ins, self.w.direktur)
        self.assertEqual(ins.tasks.count(), 2)
        with self.assertRaises(PermissionDenied):  # sudah terbit, tidak bisa diterbitkan ulang
            services.issue(ins, self.w.direktur)
        self.assertEqual(Task.objects.filter(instruction=ins).count(), 2)
        task = ins.tasks.get(pic=self.w.ka_igd)
        self.assertEqual(task.verifier, self.w.direktur)
        self.assertEqual(task.source_type, "INSTRUKSI")
        self.assertTrue(AuditLog.objects.filter(action="instruction.issue").exists())

    def test_secretary_on_behalf(self):
        ins = self._draft(self.w.sekretaris, on_behalf_of=self.w.direktur)
        InstructionTarget.objects.create(instruction=ins, unit=self.w.igd, pic=self.w.ka_igd)
        services.issue(ins, self.w.sekretaris)
        self.assertEqual(ins.tasks.get().verifier, self.w.direktur)

    def test_cancel_cancels_open_tasks(self):
        ins = self._draft()
        InstructionTarget.objects.create(instruction=ins, unit=self.w.igd, pic=self.w.ka_igd)
        services.issue(ins, self.w.direktur)
        with self.assertRaises(ValidationError):
            services.cancel(ins, self.w.direktur, "")
        services.cancel(ins, self.w.direktur, "Kebijakan berubah")
        self.assertEqual(ins.status, Instruction.Status.DIBATALKAN)
        self.assertEqual(ins.tasks.get().status, TaskStatus.DIBATALKAN)

    def test_mark_read(self):
        ins = self._draft()
        t = InstructionTarget.objects.create(instruction=ins, unit=self.w.igd, pic=self.w.ka_igd)
        services.mark_read(ins, self.w.ka_igd)
        t.refresh_from_db()
        self.assertIsNotNone(t.read_at)
