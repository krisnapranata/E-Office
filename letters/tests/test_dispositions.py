from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase

from letters import services
from letters.models import Disposition
from testutils import factories as f
from workflow import services as workflow
from workflow.models import TaskStatus


class DispositionTests(TestCase):
    def setUp(self):
        self.w = f.World()
        self.letter = services.register_incoming(
            self.w.sekretaris, letter_number="001/DINKES/2026", letter_date=f.today(),
            received_date=f.today(), sender="Dinas Kesehatan", subject="Permintaan data")

    def _dispose(self, **kw):
        kw.setdefault("due_date", f.today() + timedelta(days=5))
        return services.create_disposition(
            self.w.direktur, self.letter, to_user=self.w.wadir, to_unit=self.w.yanmed,
            directive="Siapkan data", **kw)

    def test_staff_cannot_register_letter(self):
        with self.assertRaises(PermissionDenied):
            services.register_incoming(self.w.staf_igd, letter_number="x", letter_date=f.today(),
                                       received_date=f.today(), sender="x", subject="x")

    def test_disposition_creates_linked_task(self):
        disp = self._dispose()
        task = disp.tasks.get()
        self.assertEqual((task.source_type, task.pic, task.verifier),
                         ("DISPOSISI", self.w.wadir, self.w.direktur))

    def test_action_disposition_requires_due_date(self):
        with self.assertRaises(ValidationError):
            self._dispose(due_date=None)

    def test_info_disposition_creates_no_task(self):
        disp = self._dispose(requires_action=False, due_date=None)
        self.assertFalse(disp.tasks.exists())

    def test_forward_only_by_recipient(self):
        disp = self._dispose()
        with self.assertRaises(PermissionDenied):
            services.create_disposition(self.w.ka_farmasi, self.letter, parent=disp,
                                        to_user=self.w.staf_farmasi, to_unit=self.w.farmasi,
                                        directive="x", due_date=f.today())
        # penerima disposisi dapat melihat surat dan meneruskannya
        fwd = services.create_disposition(self.w.wadir, self.letter, parent=disp,
                                          to_user=self.w.ka_igd, to_unit=self.w.igd,
                                          directive="Tindak lanjuti", due_date=f.today())
        self.assertEqual(fwd.parent, disp)

    def test_status_follows_task(self):
        disp = self._dispose()
        task = disp.tasks.get()
        services.mark_read(disp, self.w.wadir)
        self.assertEqual(disp.status, Disposition.Status.DIBACA)
        workflow.accept_task(task, self.w.wadir)
        workflow.report_progress(task, self.w.wadir, progress=50, status=TaskStatus.BERJALAN)
        services.sync_disposition_status(disp)
        self.assertEqual(disp.status, Disposition.Status.DITINDAKLANJUTI)
        workflow.add_evidence(task, self.w.wadir, f.dummy_file())
        workflow.submit_result(task, self.w.wadir)
        workflow.verify(task, self.w.direktur, approved=True)
        disp.refresh_from_db()
        self.assertEqual(disp.status, Disposition.Status.SELESAI)

    def test_secret_letter_visibility(self):
        secret = services.register_incoming(
            self.w.sekretaris, letter_number="R/1", letter_date=f.today(), received_date=f.today(),
            sender="X", subject="Rahasia", classification="RAHASIA")
        self.assertTrue(services.can_view_letter(self.w.direktur, secret))
        self.assertTrue(services.can_view_letter(self.w.sekretaris, secret))  # pencatat
        self.assertFalse(services.can_view_letter(self.w.auditor, secret))
        self.assertFalse(services.can_view_letter(self.w.wadir, secret))
