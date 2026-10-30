from django.test import TestCase, override_settings
from django.urls import reverse

from accounts.models import Role
from panduan import konten
from testutils import factories as f


class PanduanTests(TestCase):
    def setUp(self):
        self.w = f.World()

    def test_login_required(self):
        r = self.client.get(reverse("panduan:index"))
        self.assertEqual(r.status_code, 302)

    def test_every_role_sees_own_guide_first(self):
        akun = [self.w.direktur, self.w.sekretaris, self.w.wadir, self.w.ka_igd, self.w.staf_igd,
                self.w.auditor, f.user(Role.ARSIP), f.user(Role.ADMIN)]
        for u in akun:
            self.client.force_login(u)
            r = self.client.get(reverse("panduan:index"))
            self.assertEqual(r.status_code, 200, u.role)
            peran = r.context["peran"]
            self.assertEqual(peran[0]["kode"], u.role)
            self.assertTrue(peran[0]["milik_saya"])
            self.assertEqual(sum(p["milik_saya"] for p in peran), 1)
            self.assertEqual(len(peran), len(Role.choices))       # semua peran tetap bisa dibaca

    def test_twelve_modules_documented(self):
        self.assertEqual([m["no"] for m in konten.MODUL], list(range(1, 13)))
        nama = [m["nama"] for m in konten.MODUL]
        for x in ("E-Surat", "E-Disposisi", "E-Instruksi", "E-Task Management", "E-Monitoring", "E-Reminder",
                  "E-Agenda", "E-Notulen & Keputusan", "E-Follow Up", "E-Arsip", "E-Reporting", "Executive Dashboard"):
            self.assertIn(x, nama)
        for m in konten.MODUL:
            reverse(m["url"])
            self.assertTrue(m["tugas"] and m["aturan"], m["nama"])
        self.client.force_login(self.w.staf_igd)
        html = self.client.get(reverse("panduan:index")).content.decode()
        self.assertIn("Panduan per modul (12 modul)", html)
        self.assertIn("12. Executive Dashboard", html)

    def test_every_role_has_guide_and_links_resolve(self):
        self.assertEqual({p["kode"] for p in konten.PERAN}, set(Role.values))
        for p in konten.PERAN:
            for t in p["tugas"]:
                if t["url"]:
                    reverse(t["url"])         # NoReverseMatch = tautan mati

    @override_settings(EOFFICE={"INSTRUCTION_ISSUER_ROLES": ["DIREKTUR"], "REMINDER_DAYS_BEFORE": [2, 1],
                                "ESCALATION_DAYS_OVERDUE": 5, "REMINDER_HOUR": 6})
    def test_configured_values_shown(self):
        self.client.force_login(self.w.staf_igd)
        html = self.client.get(reverse("panduan:index")).content.decode()
        for teks in ("H-2 dan H-1", "pukul 06.00", "≥ 5 hari", "Saat ini: Direktur."):
            self.assertIn(teks, html)
        self.assertNotIn("{", "".join(a for _, a in self.client.get(reverse("panduan:index")).context["faq"]))

    def test_sidebar_has_guide_link(self):
        self.client.force_login(self.w.staf_igd)
        self.assertContains(self.client.get("/"), reverse("panduan:index"))
