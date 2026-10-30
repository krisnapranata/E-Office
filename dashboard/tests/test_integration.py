"""Integration test: view + database + permission (PRD 18.4 B, 18.8)."""
from datetime import timedelta

from django.test import TestCase
from django.urls import reverse

from audit.models import AuditLog
from instructions.models import Instruction
from testutils import factories as f
from workflow.models import Task, TaskStatus


class PermissionTests(TestCase):
    def setUp(self):
        self.w = f.World()
        self.task = f.direct_task(self.w.ka_igd, self.w.staf_igd, title="Tugas IGD")
        self.secret = f.direct_task(self.w.direktur, self.w.staf_igd, title="Investigasi rahasia",
                                    classification="RAHASIA", unit=self.w.igd)

    def get(self, user, url):
        self.client.force_login(user)
        return self.client.get(url)

    def test_login_required(self):
        r = self.client.get(reverse("workflow:list"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("login"), r["Location"])

    def test_task_detail_allowed_and_denied(self):
        url = reverse("workflow:detail", args=[self.task.pk])
        for allowed in (self.w.staf_igd, self.w.ka_igd, self.w.wadir, self.w.direktur, self.w.auditor):
            self.assertEqual(self.get(allowed, url).status_code, 200, allowed)
        for denied in (self.w.staf_farmasi, self.w.ka_farmasi):
            self.assertEqual(self.get(denied, url).status_code, 404, denied)

    def test_secret_task_hidden_from_unit_managers(self):
        url = reverse("workflow:detail", args=[self.secret.pk])
        self.assertEqual(self.get(self.w.staf_igd, url).status_code, 200)
        self.assertEqual(self.get(self.w.direktur, url).status_code, 200)
        for denied in (self.w.ka_igd, self.w.wadir, self.w.auditor, self.w.staf_farmasi):
            self.assertEqual(self.get(denied, url).status_code, 404, denied)
        r = self.get(self.w.ka_igd, reverse("workflow:list"))
        self.assertNotContains(r, "Investigasi rahasia")

    def test_evidence_download_permission(self):
        self.client.force_login(self.w.staf_igd)
        self.client.post(reverse("workflow:accept", args=[self.task.pk]))
        self.client.post(reverse("workflow:evidence", args=[self.task.pk]),
                         {"file": f.dummy_file(), "description": "foto"})
        ev = self.task.evidences.get()
        url = reverse("workflow:evidence_download", args=[ev.pk])
        self.assertEqual(self.get(self.w.staf_igd, url).status_code, 200)
        self.assertEqual(self.get(self.w.staf_farmasi, url).status_code, 404)
        self.assertTrue(AuditLog.objects.filter(action="task.evidence.download").exists())

    def test_post_actions_denied_for_unrelated_user(self):
        self.client.force_login(self.w.ka_farmasi)
        r = self.client.post(reverse("workflow:cancel", args=[self.task.pk]), {"reason": "x"})
        self.assertEqual(r.status_code, 404)
        self.client.force_login(self.w.auditor)  # auditor hanya baca
        r = self.client.post(reverse("workflow:cancel", args=[self.task.pk]), {"reason": "x"})
        self.assertEqual(r.status_code, 403)
        self.task.refresh_from_db()
        self.assertNotEqual(self.task.status, TaskStatus.DIBATALKAN)

    def test_staff_cannot_open_create_pages(self):
        self.client.force_login(self.w.staf_igd)
        for name in ("workflow:create", "instructions:create", "letters:incoming_create"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 403, name)

    def test_notification_open_only_own(self):
        n = self.w.staf_igd.notifications.first()
        self.client.force_login(self.w.staf_farmasi)
        r = self.client.post(reverse("notifications:open", args=[n.pk]))
        self.assertEqual(r.status_code, 404)


class DashboardTests(TestCase):
    def setUp(self):
        self.w = f.World()
        f.direct_task(self.w.ka_igd, self.w.staf_igd, due=f.today() - timedelta(days=2))
        f.direct_task(self.w.ka_igd, self.w.staf_igd, due=f.today() + timedelta(days=1))
        f.direct_task(self.w.ka_farmasi, self.w.staf_farmasi, due=f.today() - timedelta(days=1))

    def _card(self, ctx, label):
        return next(c for c in ctx["cards"] if c[0] == label)

    def test_dashboard_numbers_match_detail_lists(self):
        for user, expected_overdue in ((self.w.direktur, 2), (self.w.ka_igd, 1)):
            self.client.force_login(user)
            r = self.client.get(reverse("dashboard:home"))
            self.assertEqual(r.status_code, 200)
            for label in ("Terlambat", "Tenggat ≤ H-2"):
                _, n, qs, _ = self._card(r.context, label)
                lst = self.client.get(reverse("workflow:list") + "?" + qs)
                self.assertEqual(lst.context["page"].paginator.count, n, (user, label))
            self.assertEqual(self._card(r.context, "Terlambat")[1], expected_overdue)

    def test_unit_performance(self):
        self.client.force_login(self.w.direktur)
        units = {u["unit__code"]: u for u in self.client.get(reverse("dashboard:home")).context["units"]}
        self.assertEqual(units["IGD"]["total"], 2)
        self.assertEqual(units["IGD"]["overdue"], 1)


class InstructionToClosureFlowTests(TestCase):
    """Skenario E2E no. 1 dijalankan pada level HTTP (tanpa browser)."""

    def setUp(self):
        self.w = f.World()

    def test_full_flow(self):
        c = self.client
        c.force_login(self.w.direktur)
        r = c.post(reverse("instructions:create"), {
            "title": "Audit stok obat high alert", "description": "Lakukan audit.",
            "instruction_date": f.today().isoformat(), "priority": "TINGGI",
            "classification": "BIASA", "due_date": (f.today() + timedelta(days=3)).isoformat(),
            "completion_criteria": "Laporan audit", "requires_evidence": "on",
            "requires_verification": "on"})
        ins = Instruction.objects.get()
        self.assertRedirects(r, reverse("instructions:detail", args=[ins.pk]))
        c.post(reverse("instructions:target_add", args=[ins.pk]),
               {"unit": self.w.farmasi.pk, "pic": self.w.staf_farmasi.pk})
        c.post(reverse("instructions:issue", args=[ins.pk]))
        task = Task.objects.get(instruction=ins)

        c.force_login(self.w.staf_farmasi)
        self.assertContains(c.get(reverse("workflow:list")), "Audit stok obat high alert")
        c.get(reverse("instructions:detail", args=[ins.pk]))
        self.assertIsNotNone(ins.targets.get().read_at)
        c.post(reverse("workflow:accept", args=[task.pk]))
        c.post(reverse("workflow:progress", args=[task.pk]),
               {"progress": 60, "status": "BERJALAN", "note": "Sebagian rak selesai"})
        c.post(reverse("workflow:evidence", args=[task.pk]), {"file": f.dummy_file()})
        c.post(reverse("workflow:submit", args=[task.pk]), {"note": "Selesai"})
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.MENUNGGU_VERIFIKASI)

        c.force_login(self.w.direktur)
        c.post(reverse("workflow:verify", args=[task.pk]), {"decision": "approve", "note": "OK"})
        task.refresh_from_db()
        self.assertEqual(task.status, TaskStatus.SELESAI)
        r = c.get(reverse("dashboard:home"))
        self.assertEqual(next(x for x in r.context["cards"] if x[0] == "Selesai")[1], 1)

    def test_letter_disposition_flow(self):
        c = self.client
        c.force_login(self.w.sekretaris)
        c.post(reverse("letters:incoming_create"), {
            "letter_number": "12/X/2026", "letter_date": f.today().isoformat(),
            "received_date": f.today().isoformat(), "sender": "Kemenkes",
            "subject": "Survei mutu", "classification": "BIASA"})
        from letters.models import IncomingLetter
        letter = IncomingLetter.objects.get()
        c.force_login(self.w.direktur)
        c.post(reverse("letters:disposition_create", args=[letter.pk]), {
            "to_user": self.w.ka_igd.pk, "to_unit": self.w.igd.pk, "directive": "Isi survei",
            "priority": "SEDANG", "due_date": (f.today() + timedelta(days=2)).isoformat(),
            "requires_action": "on"})
        disp = letter.dispositions.get()
        task = disp.tasks.get()
        c.force_login(self.w.ka_igd)
        r = c.get(reverse("workflow:detail", args=[task.pk]))
        self.assertContains(r, f"Disposisi #{disp.pk}")
        self.assertEqual(c.get(reverse("letters:incoming_detail", args=[letter.pk])).status_code, 200)
        c.force_login(self.w.staf_farmasi)
        self.assertEqual(c.get(reverse("letters:incoming_detail", args=[letter.pk])).status_code, 404)

    def test_healthz(self):
        self.assertEqual(self.client.get("/healthz").status_code, 200)
