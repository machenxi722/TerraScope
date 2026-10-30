"""Durable DB outbox, Celery dispatch, and a separate polling worker for local development."""

import argparse
import logging
import time
from celery import Celery
from .config import settings
from .services.tasks import pending_ids, run_task
from .services.reports import pending_report_ids, run_report

celery = Celery("terrascope", broker=settings.redis_url)
celery.conf.update(
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    task_ignore_result=True,
    task_serializer="json",
    accept_content=["json"],
    beat_schedule={"dispatch-durable-outbox": {"task": "dispatch", "schedule": 3.0}},
)


@celery.task(name="analyze")
def analyze(task_id):
    run_task(task_id)


@celery.task(name="report")
def report(report_id):
    run_report(report_id)


@celery.task(name="dispatch")
def dispatch():
    for task_id in pending_ids():
        analyze.delay(task_id)
    for report_id in pending_report_ids():
        report.delay(report_id)


def local_once():
    for task_id in pending_ids():
        run_task(task_id)
    for report_id in pending_report_ids():
        run_report(report_id)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO)
    while True:
        try:
            local_once()
        except Exception:
            logging.exception("Worker poll failed; durable jobs will be retried")
        if args.once:
            break
        time.sleep(1)
