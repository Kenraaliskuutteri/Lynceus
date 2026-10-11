import asyncio
import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.config import (
    RETENTION_DAYS,
    RETENTION_INTERVAL_SECONDS,
    ROLLUP_BUCKET_SECONDS,
    ROLLUP_RETENTION_DAYS,
)
from app.core.database import SessionLocal
from app.models.metric_log import MetricLog
from app.models.metric_rollup import MetricRollup

CHUNK_SIZE = 5000

LOG_ATTRS = {
    "cpu": "cpu_usage",
    "ram": "ram_usage",
    "disk": "disk_usage",
    "rx": "network_rx_kb",
    "tx": "network_tx_kb",
}

log = logging.getLogger(__name__)


def as_utc(ts: datetime) -> datetime:
    if ts.tzinfo is None:
        return ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(timezone.utc)


def floor_bucket(ts: datetime) -> datetime:
    epoch = int(ts.timestamp())
    return datetime.fromtimestamp(epoch - epoch % ROLLUP_BUCKET_SECONDS, tz=timezone.utc)


def rollup_chunk(db: Session, cutoff: datetime) -> int:
    rows = (
        db.query(MetricLog)
        .filter(MetricLog.timestamp < cutoff)
        .order_by(MetricLog.timestamp.asc())
        .limit(CHUNK_SIZE)
        .all()
    )
    if not rows:
        return 0

    groups: dict[tuple[str, datetime], list[MetricLog]] = {}
    for row in rows:
        key = (row.server_id, floor_bucket(as_utc(row.timestamp)))
        groups.setdefault(key, []).append(row)

    first = min(key[1] for key in groups)
    last = max(key[1] for key in groups)
    existing = {
        (r.server_id, as_utc(r.bucket_start)): r
        for r in db.query(MetricRollup).filter(
            MetricRollup.server_id.in_({key[0] for key in groups}),
            MetricRollup.bucket_start >= first,
            MetricRollup.bucket_start <= last,
        )
    }

    for key, chunk in groups.items():
        n = len(chunk)
        stats = {}
        for name, attr in LOG_ATTRS.items():
            values = [getattr(r, attr) for r in chunk]
            stats[name] = (sum(values) / n, max(values))

        rollup = existing.get(key)
        if rollup is None:
            rollup = MetricRollup(server_id=key[0], bucket_start=key[1], samples=n)
            for name, (avg, peak) in stats.items():
                setattr(rollup, f"{name}_avg", avg)
                setattr(rollup, f"{name}_max", peak)
            db.add(rollup)
            continue

        total = rollup.samples + n
        for name, (avg, peak) in stats.items():
            old_avg = getattr(rollup, f"{name}_avg")
            setattr(rollup, f"{name}_avg", (old_avg * rollup.samples + avg * n) / total)
            setattr(rollup, f"{name}_max", max(getattr(rollup, f"{name}_max"), peak))
        rollup.samples = total

    db.query(MetricLog).filter(MetricLog.id.in_([r.id for r in rows])).delete(synchronize_session=False)
    db.commit()
    return len(rows)


def run_retention_pass(db: Session, now: datetime) -> int:
    if RETENTION_DAYS <= 0:
        return 0

    cutoff = floor_bucket(now - timedelta(days=RETENTION_DAYS))
    moved = 0
    while True:
        n = rollup_chunk(db, cutoff)
        moved += n
        if n < CHUNK_SIZE:
            break

    if ROLLUP_RETENTION_DAYS > 0:
        stale = now - timedelta(days=ROLLUP_RETENTION_DAYS)
        db.query(MetricRollup).filter(MetricRollup.bucket_start < stale).delete(synchronize_session=False)
        db.commit()

    return moved


def retention_pass_sync() -> None:
    db = SessionLocal()
    try:
        moved = run_retention_pass(db, datetime.now(timezone.utc))
        if moved:
            log.info("rolled up %d raw metric rows", moved)
    except Exception:
        db.rollback()
        log.exception("retention pass failed")
    finally:
        db.close()


async def run_retention():
    while True:
        await asyncio.to_thread(retention_pass_sync)
        await asyncio.sleep(RETENTION_INTERVAL_SECONDS)