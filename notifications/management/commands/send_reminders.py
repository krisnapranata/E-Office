from datetime import date

from django.core.management.base import BaseCommand

from notifications.services import run_reminders


class Command(BaseCommand):
    help = "Jalankan pengingat tugas H-n, terlambat, eskalasi, dan pengingat agenda (idempotent)."

    def add_arguments(self, parser):
        parser.add_argument("--date", type=date.fromisoformat,
                            help="Tanggal acuan YYYY-MM-DD (untuk pengujian).")

    def handle(self, *args, **options):
        from agenda.services import run_agenda_reminders

        sent = run_reminders(today=options["date"]) + run_agenda_reminders(today=options["date"])
        self.stdout.write(self.style.SUCCESS(f"{sent} pengingat dikirim."))
