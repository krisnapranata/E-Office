from celery import shared_task

from .services import run_reminders


@shared_task
def run_daily_reminders():
    return run_reminders()
