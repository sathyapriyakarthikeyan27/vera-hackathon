"""
Celery application for VERA's scheduled work (reminder dispatch + delivery).

Redis is the broker/result backend on separate logical DBs from the LLM cache
(cache = db 0; broker = db 1; results = db 2). Celery Beat periodically dispatches
due reminders; workers deliver them across channels with retry/backoff.
"""

import os

from celery import Celery

BROKER_URL = os.getenv("CELERY_BROKER_URL", "redis://redis:6379/1")
RESULT_BACKEND = os.getenv("CELERY_RESULT_BACKEND", "redis://redis:6379/2")
DISPATCH_INTERVAL = float(os.getenv("REMINDER_DISPATCH_INTERVAL", "60"))

celery = Celery(
    "vera",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["tasks.reminders"],
)

celery.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    timezone="UTC",
    enable_utc=True,
    task_track_started=True,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    result_expires=3600,
    beat_schedule={
        "dispatch-due-reminders": {
            "task": "reminders.dispatch_due",
            "schedule": DISPATCH_INTERVAL,
        },
    },
)
