from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from agenda.services import create_event
from notulen import services
from testutils import factories as f
from workflow.models import Task


class NotulenTests(TestCase):
    def setUp(self):
        self.w = f.World()
        self.ev = create_event(self.w.direktur, participants=[self.w.ka_igd], title="Rapat", kind="RAPAT",
                               start=timezone.now())
        self.m = services.create_minutes(self.w.sekretaris, self.ev, discussion="Bahas")

    def _keputusan(self, **kw):
        kw.setdefault("text", "Lakukan X")
        kw.setdefault("requires_action", True)
        kw.setdefault("due_date", timezone.localdate() + timedelta(days=7))
        return services.add_decision(self.m, self.w.sekretaris, **kw)

    def test_only_meetings_have_minutes(self):
        ev = create_event(self.w.direktur, title="Apel", kind="KEGIATAN", start=timezone.now())
        with self.assertRaises(ValidationError):
            services.create_minutes(self.w.sekretaris, ev, discussion="x")

    def test_staff_cannot_write(self):
        self.assertFalse(services.can_write_minutes(self.w.staf_igd, self.ev))

    def test_action_decision_needs_due_and_pic_before_submit(self):
        with self.assertRaises(ValidationError):
            services.add_decision(self.m, self.w.sekretaris, text="x", requires_action=True)
        self._keputusan()
        with self.assertRaises(ValidationError):
            services.submit(self.m, self.w.sekretaris)

    def test_approval_creates_follow_ups_once(self):
        d = self._keputusan()
        services.add_assignee(d, self.w.sekretaris, self.w.igd, self.w.ka_igd)
        services.add_assignee(d, self.w.sekretaris, self.w.farmasi, self.w.ka_farmasi)
        info = self._keputusan(text="Info", requires_action=False, due_date=None)
        services.submit(self.m, self.w.sekretaris)
        with self.assertRaises(PermissionDenied):
            services.approve(self.m, self.w.sekretaris)          # hanya pimpinan rapat
        services.approve(self.m, self.w.direktur)
        tasks = Task.objects.filter(decision__minutes=self.m)
        self.assertEqual(tasks.count(), 2)
        self.assertFalse(Task.objects.filter(decision=info).exists())
        self.assertTrue(all(t.source_type == "KEPUTUSAN_RAPAT" and t.verifier == self.w.direktur for t in tasks))
        with self.assertRaises(PermissionDenied):
            services.approve(self.m, self.w.direktur)
        self.assertEqual(tasks.count(), 2)
        with self.assertRaises(PermissionDenied):                # isi terkunci setelah disetujui
            services.add_decision(self.m, self.w.sekretaris, text="y")

    def test_return_requires_note_and_reopens(self):
        services.submit(self.m, self.w.sekretaris)
        with self.assertRaises(ValidationError):
            services.return_minutes(self.m, self.w.direktur, "")
        services.return_minutes(self.m, self.w.direktur, "Lengkapi")
        self.m.refresh_from_db()
        self.assertEqual((self.m.status, self.m.return_note), ("DRAF", "Lengkapi"))
        services.submit(self.m, self.w.sekretaris)
        self.m.refresh_from_db()
        self.assertEqual(self.m.revision, 2)

    def test_task_from_decision_requires_link(self):
        from workflow import services as alur

        with self.assertRaises(ValidationError):
            alur.create_task(created_by=self.w.direktur, source_type="KEPUTUSAN_RAPAT", title="x", unit=self.w.igd,
                             pic=self.w.ka_igd)
