from datetime import date

from django.core.management.base import BaseCommand

from notifications.services import run_reminders


class Command(BaseCommand):
    help = "Jalankan pengingat H-n, status terlambat, dan eskalasi (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--date", type=date.fromisoformat,
                            help="Tanggal acuan YYYY-MM-DD (untuk pengujian).")

    def handle(self, *args, **options):
        sent = run_reminders(today=options["date"])
        self.stdout.write(self.style.SUCCESS(f"{sent} pengingat dikirim."))
