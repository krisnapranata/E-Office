from django.core.exceptions import PermissionDenied, ValidationError
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from accounts import organisasi as org
from accounts.models import OrganizationRelation, OrganizationUnit, Role
from accounts.permissions import managed_unit_ids
from testutils import factories as f

U = OrganizationUnit


class SeedRsiyTests(TestCase):
    def test_seed_complete_and_idempotent(self):
        self.assertEqual(org.seed_rsiy(), (50, 0, 11))
        self.assertEqual(org.seed_rsiy(), (0, 0, 0))
        call_command("seed_organisasi_rsiy", stdout=__import__("io").StringIO())
        self.assertEqual(U.objects.filter(code__startswith="RSIY-").count(), 50)
        self.assertEqual(OrganizationRelation.objects.count(), 11)

    def test_structure_matches_chart(self):
        org.seed_rsiy()
        g = lambda kode: U.objects.get(code=kode)  # noqa: E731
        self.assertIsNone(g("RSIY-DIR").parent)
        jalur, u = [], g("RSIY-IGD")
        while u:
            jalur.append(u.name)
            u = u.parent
        self.assertEqual(jalur, ["Instalasi Gawat Darurat", "Kepala Seksi Pelayanan Medik", "Manager Pelayanan Pasien",
                                 "Kepala Bidang Pelayanan", "Direktur RSI Yatofa"])
        self.assertEqual(g("RSIY-ANGGOTA").parent.name, "Kepala Seksi Keamanan")
        self.assertEqual(sorted(c.name for c in g("RSIY-BKEU").children.all()),
                         ["Akuntansi & Pelaporan", "Bendahara", "Kasir", "Perencanaan Anggaran"])
        self.assertEqual(g("RSIY-DIR").children.count(), 3)
        # SPI & komite: bukan bawahan struktural siapa pun, hanya hubungan koordinasi/pengawasan ke Direktur
        for kode in ("RSIY-SPI", "RSIY-KMEDIK", "RSIY-KPPRA", "RSIY-CASEMIX"):
            self.assertIsNone(g(kode).parent, kode)
            self.assertTrue(g(kode).relations_out.filter(target__code="RSIY-DIR").exists(), kode)
        self.assertEqual(g("RSIY-SPI").relations_out.get().kind, "PENGAWASAN")
        self.assertFalse(U.objects.filter(name__icontains="PT YSW").exists())

    def test_structural_scope_used_by_workflow(self):
        org.seed_rsiy()
        kabid = f.user(Role.KEPALA_UNIT, unit=U.objects.get(code="RSIY-BYAN"))
        lingkup = managed_unit_ids(kabid)
        self.assertIn(U.objects.get(code="RSIY-IGD").pk, lingkup)
        self.assertNotIn(U.objects.get(code="RSIY-KASIR").pk, lingkup)
        self.assertNotIn(U.objects.get(code="RSIY-KMEDIK").pk, lingkup)     # komite bukan bawahan bidang

    def test_seed_respects_admin_edits_unless_forced(self):
        org.seed_rsiy()
        U.objects.filter(code="RSIY-KASIR").update(name="Kasir Rawat Jalan")
        org.seed_rsiy()
        self.assertEqual(U.objects.get(code="RSIY-KASIR").name, "Kasir Rawat Jalan")
        self.assertEqual(org.seed_rsiy(paksa=True)[1], 1)
        self.assertEqual(U.objects.get(code="RSIY-KASIR").name, "Kasir")


class ManageUnitTests(TestCase):
    def setUp(self):
        org.seed_rsiy()
        self.admin = f.user(Role.ADMIN)
        self.staf = f.user(Role.STAF)
        self.byan = U.objects.get(code="RSIY-BYAN")
        self.igd = U.objects.get(code="RSIY-IGD")

    def test_only_admin_manages(self):
        with self.assertRaises(PermissionDenied):
            org.create_unit(self.staf, code="X", name="X")
        u = org.create_unit(self.admin, code="RSIY-X", name="Unit X", kind="SUBUNIT", parent=self.igd)
        self.assertEqual(u.parent, self.igd)

    def test_cycle_prevented(self):
        with self.assertRaises(ValidationError):
            org.update_unit(self.byan, self.admin, parent=self.igd)          # induk = cucu
        with self.assertRaises(ValidationError):
            org.update_unit(self.byan, self.admin, parent=self.byan)         # induk = diri sendiri
        self.byan.refresh_from_db()
        self.assertEqual(self.byan.parent.code, "RSIY-DIR")
        self.byan.parent = self.igd
        with self.assertRaises(ValidationError):
            self.byan.full_clean()                                             # juga dijaga di model

    def test_deactivate_rules(self):
        with self.assertRaises(ValidationError):
            org.deactivate(self.byan, self.admin, "x")                         # masih punya sub-unit aktif
        with self.assertRaises(ValidationError):
            org.deactivate(self.igd, self.admin, "")
        org.deactivate(self.igd, self.admin, "Digabung")
        self.assertFalse(U.objects.get(pk=self.igd.pk).is_active)
        self.assertTrue(U.objects.filter(pk=self.igd.pk).exists())             # tidak dihapus
        org.activate(self.igd, self.admin)
        self.assertTrue(U.objects.get(pk=self.igd.pk).is_active)

    def test_relation_not_self_and_no_duplicate(self):
        with self.assertRaises(ValidationError):
            org.add_relation(self.admin, self.igd, self.igd, "KOORDINASI")
        org.add_relation(self.admin, self.igd, self.byan, "KOORDINASI")
        org.add_relation(self.admin, self.igd, self.byan, "KOORDINASI")
        self.assertEqual(self.igd.relations_out.count(), 1)

    def test_pages(self):
        self.client.force_login(self.staf)
        r = self.client.get(reverse("organisasi:index"))
        self.assertContains(r, "Direktur RSI Yatofa")
        self.assertContains(r, "Komite Medik")
        self.assertNotContains(r, reverse("organisasi:create"))
        self.assertEqual(self.client.get(reverse("organisasi:create")).status_code, 403)
        self.assertEqual(self.client.post(reverse("organisasi:edit", args=[self.igd.pk]), {"name": "x"}).status_code, 403)
        self.client.force_login(self.admin)
        self.assertContains(self.client.get(reverse("organisasi:index")), reverse("organisasi:create"))
        r = self.client.post(reverse("organisasi:edit", args=[self.byan.pk]), {
            "code": "RSIY-BYAN", "name": "Kepala Bidang Pelayanan", "kind": "BIDANG", "parent": self.igd.pk, "order": 13})
        self.assertEqual(r.status_code, 200)                                    # form ditolak, tidak melingkar
        self.byan.refresh_from_db()
        self.assertEqual(self.byan.parent.code, "RSIY-DIR")
