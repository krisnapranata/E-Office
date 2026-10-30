from datetime import timedelta

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase
from django.utils import timezone

from agenda import services
from agenda.models import AgendaEvent
from notifications.models import Notification
from testutils import factories as f


class AgendaTests(TestCase):
    def setUp(self):
        self.w = f.World()
        self.mulai = timezone.now() + timedelta(days=2)

    def _ev(self, **kw):
        kw.setdefault("title", "Rapat")
        return services.create_event(self.w.sekretaris, participants=kw.pop("participants", [self.w.wadir]),
                                     organizer=kw.pop("organizer", self.w.direktur), start=self.mulai, **kw)

    def test_staff_cannot_create(self):
        with self.assertRaises(PermissionDenied):
            services.create_event(self.w.staf_igd, title="x", start=self.mulai)

    def test_end_after_start(self):
        with self.assertRaises(ValidationError):
            self._ev(end=self.mulai - timedelta(hours=1))

    def test_invitations_and_visibility(self):
        ev = self._ev()
        self.assertTrue(Notification.objects.filter(recipient=self.w.wadir, kind="agenda.invite").exists())
        self.assertTrue(services.can_view_event(self.w.wadir, ev))
        self.assertFalse(services.can_view_event(self.w.staf_igd, ev))
        self.assertTrue(services.can_view_event(self.w.auditor, ev))
        rahasia = self._ev(classification="RAHASIA")
        self.assertFalse(services.can_view_event(self.w.auditor, rahasia))

    def test_reschedule_notifies_and_participant_cannot_edit(self):
        ev = self._ev()
        with self.assertRaises(PermissionDenied):
            services.update_event(ev, self.w.wadir, start=self.mulai + timedelta(days=1))
        services.update_event(ev, self.w.sekretaris, start=self.mulai + timedelta(days=1))
        self.assertTrue(Notification.objects.filter(recipient=self.w.wadir, kind="agenda.reschedule").exists())

    def test_cancel_requires_reason_and_blocks_edit(self):
        ev = self._ev()
        with self.assertRaises(ValidationError):
            services.cancel_event(ev, self.w.sekretaris, " ")
        services.cancel_event(ev, self.w.sekretaris, "Batal")
        with self.assertRaises(ValidationError):
            services.update_event(ev, self.w.sekretaris, title="y")

    def test_reminders_idempotent_and_skip_cancelled(self):
        ev = self._ev()
        hari = timezone.localtime(ev.start).date()
        n1 = services.run_agenda_reminders(hari - timedelta(days=1))
        n2 = services.run_agenda_reminders(hari - timedelta(days=1))
        self.assertEqual((n1, n2), (2, 0))      # penyelenggara (direktur) + peserta (wadir); pembuat tidak
        services.cancel_event(ev, self.w.sekretaris, "Batal")
        self.assertEqual(services.run_agenda_reminders(hari), 0)
        self.assertEqual(AgendaEvent.objects.get(pk=ev.pk).status, "DIBATALKAN")
