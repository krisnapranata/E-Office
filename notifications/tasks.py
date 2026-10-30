from celery import shared_task

from .services import run_reminders


@shared_task
def run_daily_reminders():
    from agenda.services import run_agenda_reminders

    return run_reminders() + run_agenda_reminders()
