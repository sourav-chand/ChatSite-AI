"""Celery application factory."""
from __future__ import annotations

from celery import Celery
from celery.schedules import crontab

from app.core.config import settings

celery_app = Celery(
    "chatsite",
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.crawl_tasks",
        "app.tasks.analytics_tasks",
        "app.tasks.schedule_tasks",
    ],
)

celery_app.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    task_always_eager=False,
)

celery_app.conf.beat_schedule = {
    "analytics-daily-rollup": {
        "task": "app.tasks.analytics_tasks.analytics_daily_rollup_task",
        "schedule": crontab(hour=0, minute=5),
    },
    "scheduled-crawls": {
        "task": "app.tasks.schedule_tasks.scheduled_crawl_dispatch",
        "schedule": crontab(minute="*/15"),
    },
}
