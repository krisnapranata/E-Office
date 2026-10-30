from datetime import date

from django.core.exceptions import PermissionDenied, ValidationError
from django.test import TestCase, override_settings

from arsip import services
from arsip.models import ArchiveDocument
from letters import services as surat
from testutils import factories as f


class ArsipTests(TestCase):
    def setUp(self):
        self.w = f.World()

    def _surat(self, **kw):
        return surat.register_incoming(self.w.sekretaris, letter_number="1/X", letter_date=date(2026, 1, 5),
                                       received_date=date(2026, 1, 6), sender="X", subject="Perihal",
                                       attachment=f.dummy_file("s.pdf"), **kw)

    def test_auto_archive_idempotent(self):
        s = self._surat()
        doc = ArchiveDocument.objects.get(doc_type="SURAT_MASUK", source_id=s.pk)
        self.assertEqual(doc.retention_until, date(2031, 1, 5))
        services.arsipkan_surat_masuk(s)
        self.assertEqual(doc.versions.count(), 1)

    def test_no_attachment_no_archive(self):
        surat.register_incoming(self.w.sekretaris, letter_number="2", letter_date=date.today(),
                                received_date=date.today(), sender="X", subject="tanpa lampiran")
        self.assertFalse(ArchiveDocument.objects.filter(title="tanpa lampiran").exists())

    @override_settings(EOFFICE={"RETENTION_YEARS": {"DEFAULT": 5, "SURAT_MASUK": 10}, "INSTRUCTION_ISSUER_ROLES": [],
                                "REMINDER_DAYS_BEFORE": [2], "ESCALATION_DAYS_OVERDUE": 3})
    def test_retention_per_type(self):
        self.assertEqual(services.retention_date("SURAT_MASUK", date(2026, 1, 5)), date(2036, 1, 5))
        self.assertEqual(services.retention_date("BUKTI", date(2024, 2, 29)), date(2029, 2, 28))

    def test_visibility_and_secret(self):
        s = self._surat(classification="RAHASIA")
        doc = ArchiveDocument.objects.get(source_id=s.pk, doc_type="SURAT_MASUK")
        self.assertTrue(services.can_view_archive(self.w.direktur, doc))
        self.assertTrue(services.can_view_archive(self.w.sekretaris, doc))     # pemilik
        self.assertFalse(services.can_view_archive(self.w.arsip, doc))
        self.assertFalse(services.can_view_archive(self.w.auditor, doc))

    def test_sourced_doc_versions_follow_source(self):
        s = self._surat()
        doc = ArchiveDocument.objects.get(source_id=s.pk, doc_type="SURAT_MASUK")
        with self.assertRaises(PermissionDenied):
            services.add_version(doc, self.w.arsip, f.dummy_file(), "revisi")

    def test_disposal_flow(self):
        doc = services.create_manual(self.w.arsip, f.dummy_file(), doc_type="LAINNYA", doc_date=date(2015, 1, 1),
                                     title="Lama")
        with self.assertRaises(PermissionDenied):
            services.create_manual(self.w.staf_igd, f.dummy_file(), doc_type="LAINNYA", doc_date=date.today(), title="x")
        baru = services.create_manual(self.w.arsip, f.dummy_file(), doc_type="LAINNYA", doc_date=date.today(), title="b")
        with self.assertRaises(ValidationError):
            services.propose_disposal(baru, self.w.arsip, "x")
        with self.assertRaises(PermissionDenied):
            services.propose_disposal(doc, self.w.sekretaris, "x")
        services.propose_disposal(doc, self.w.arsip, "habis")
        with self.assertRaises(PermissionDenied):
            services.decide_disposal(doc, self.w.arsip, approved=True, note="x")
        services.decide_disposal(doc, self.w.direktur, approved=False, note="masih dipakai")
        self.assertEqual(doc.status, "AKTIF")
        services.propose_disposal(doc, self.w.arsip, "habis lagi")
        services.decide_disposal(doc, self.w.direktur, approved=True, note="BA-1")
        self.assertEqual(doc.status, "DIMUSNAHKAN")
