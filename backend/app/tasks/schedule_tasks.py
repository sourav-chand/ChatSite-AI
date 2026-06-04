"""Forwarder module for schedule_tasks — Celery autodiscovery expects this name."""
from app.tasks.analytics_tasks import scheduled_crawl_dispatch  # noqa: F401
