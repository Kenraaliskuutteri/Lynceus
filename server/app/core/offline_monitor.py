import asyncio
import json
from datetime import datetime, timezone

from sqlalchemy.orm import Session

from app.config import OFFLINE_THRESHOLD_SECONDS
from app.core.alerts import serialize_alert
from app.core.database import SessionLocal
from app.core.webhooks import dispatch_alert_webhook
from app.models.alert import AlertEvent
from app.models.server import Server

POLL_INTERVAL_SECONDS = 5


def check_offline_servers(db: Session, now: datetime) -> list[AlertEvent]:
    changed: list[AlertEvent] = []

    for server in db.query(Server).all():
        last_seen = server.last_seen
        if last_seen is None:
            continue
        if last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)

        threshold_seconds = server.offline_threshold_seconds or OFFLINE_THRESHOLD_SECONDS
        elapsed = (now - last_seen).total_seconds()
        is_online = elapsed < threshold_seconds

        open_alert = (
            db.query(AlertEvent)
            .filter(
                AlertEvent.server_id == server.id,
                AlertEvent.metric == "offline",
                AlertEvent.status == "triggered",
            )
            .first()
        )

        if not is_online and open_alert is None:
            alert = AlertEvent(
                server_id=server.id,
                metric="offline",
                value=elapsed,
                threshold=float(threshold_seconds),
                status="triggered",
                triggered_at=now,
            )
            db.add(alert)
            changed.append(alert)
        elif is_online and open_alert is not None:
            open_alert.status = "resolved"
            open_alert.resolved_at = now
            changed.append(open_alert)

    if changed:
        db.commit()
        for alert in changed:
            db.refresh(alert)

    return changed


async def run_offline_monitor():
    from app.websockets.metrics_ws import manager

    while True:
        db = SessionLocal()
        try:
            changed = check_offline_servers(db, datetime.now(timezone.utc))
        finally:
            db.close()

        for alert in changed:
            asyncio.create_task(dispatch_alert_webhook(alert))
            frame = json.dumps({"type": "alert", "event": serialize_alert(alert)})
            await manager.broadcast(alert.server_id, None, frame)

        await asyncio.sleep(POLL_INTERVAL_SECONDS)