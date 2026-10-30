"""Arsipkan berkas yang sudah ada sebelum E-Arsip aktif (idempotent; aman dijalankan ulang)."""
from django.core.management.base import BaseCommand

from arsip import services as s


class Command(BaseCommand):
    help = "Sinkronkan lampiran surat/instruksi, bahan agenda, bukti tugas, dan notulen disetujui ke E-Arsip."

    def handle(self, *args, **options):
        from agenda.models import AgendaMaterial
        from instructions.models import Instruction
        from letters.models import IncomingLetter, OutgoingLetter
        from notulen.models import MeetingMinutes
        from workflow.models import TaskEvidence

        n = 0
        for x in IncomingLetter.objects.exclude(attachment=""):
            n += bool(s.arsipkan_surat_masuk(x))
        for x in OutgoingLetter.objects.exclude(attachment=""):
            n += bool(s.arsipkan_surat_keluar(x))
        for x in Instruction.objects.exclude(attachment=""):
            n += bool(s.arsipkan_instruksi(x))
        for x in TaskEvidence.objects.select_related("task"):
            n += bool(s.arsipkan_bukti(x))
        for x in AgendaMaterial.objects.select_related("event"):
            n += bool(s.arsipkan_bahan(x))
        for x in MeetingMinutes.objects.filter(status="DISETUJUI").exclude(attachment=""):
            n += bool(s.arsipkan_notulen(x))
        self.stdout.write(self.style.SUCCESS(f"{n} objek diperiksa/diarsipkan."))
