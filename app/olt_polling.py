"""Helpers for scheduling OLT polling."""
from __future__ import annotations

import os
from datetime import datetime, timedelta
from typing import Callable

from apscheduler.schedulers.background import BackgroundScheduler

from modules.olt import cli, snmp
from modules.olt import ONURecord

from . import db
from .models import OLT, ONU

Poller = Callable[[OLT], list[ONURecord] | tuple[ONURecord, ...] | set[ONURecord] | dict]


def _select_provider(model: str) -> Callable[[OLT], object]:
    """Choose polling provider based on OLT model."""
    normalized = (model or "").lower()
    if "cli" in normalized or "ssh" in normalized:
        return cli.poll
    return snmp.poll


def _upsert_onu(olt_id: int, record: ONURecord) -> None:
    """Create or update ONU record based on polling result."""
    onu = ONU.query.filter_by(
        olt_id=olt_id,
        interface=record.interface,
        serial_number=record.serial_number,
    ).first()
    if not onu:
        onu = ONU(
            olt_id=olt_id,
            interface=record.interface,
            serial_number=record.serial_number,
        )
        db.session.add(onu)
    onu.status = record.status
    onu.last_seen = datetime.utcnow()


def poll_single_olt(olt: OLT) -> None:
    """Poll a single OLT and persist ONU records."""
    provider = _select_provider(olt.model)
    for record in provider(olt):
        if isinstance(record, ONURecord):
            _upsert_onu(olt.id, record)
    olt.last_polled_at = datetime.utcnow()
    db.session.commit()


def poll_olts(limit: int = 200) -> None:
    """Poll available OLT devices respecting their intervals."""
    now = datetime.utcnow()
    olts = OLT.query.limit(limit).all()
    for olt in olts:
        if olt.polling_interval <= 0:
            continue
        if olt.last_polled_at and now - olt.last_polled_at < timedelta(seconds=olt.polling_interval):
            continue
        poll_single_olt(olt)


def _run_polling(app) -> None:
    """Invoke polling inside application context."""
    with app.app_context():
        poll_olts()


def schedule_polling_jobs(app) -> None:
    """Start background scheduler to poll OLTs periodically."""
    if getattr(app, "polling_scheduler", None) is not None:
        return

    if app.debug and os.environ.get("WERKZEUG_RUN_MAIN") != "true":
        return

    tick_seconds = int(os.getenv("POLLING_TICK_SECONDS", "60"))
    scheduler = BackgroundScheduler()
    scheduler.add_job(
        lambda: _run_polling(app),
        "interval",
        seconds=tick_seconds,
        id="olt-polling",
        replace_existing=True,
        max_instances=1,
    )
    scheduler.start()
    app.polling_scheduler = scheduler
