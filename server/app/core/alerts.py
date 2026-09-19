from datetime import datetime, timedelta, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.config import ACK_EXPIRY_HOURS, ALERT_THRESHOLDS
from app.models.alert import AlertEvent
from app.models.server import Server

METRIC_FIELDS = {
    "cpu_usage": ("cpuUsage", "cpu_threshold"),
    "ram_usage": ("ramUsage", "ram_threshold"),
    "disk_usage": ("diskUsage", "disk_threshold"),
}


def serialize_alert(alert: AlertEvent) -> dict:
    return {
        "id": alert.id,
        "serverId": alert.server_id,
        "metric": alert.metric,
        "value": alert.value,
        "threshold": alert.threshold,
        "status": alert.status,
        "triggeredAt": alert.triggered_at.replace(tzinfo=timezone.utc).isoformat()
        if alert.triggered_at
        else None,
        "resolvedAt": alert.resolved_at.replace(tzinfo=timezone.utc).isoformat()
        if alert.resolved_at
        else None,
        "acknowledgedAt": alert.acknowledged_at.replace(tzinfo=timezone.utc).isoformat()
        if alert.acknowledged_at
        else None,
    }


def evaluate_alerts(
    db: Session, server_id: str, payload: dict, now: Optional[datetime] = None
) -> list[AlertEvent]:
    now = now or datetime.now(timezone.utc)
    changed_alerts: list[AlertEvent] = []

    server = db.get(Server, server_id)

    for field_name, (alias, override_attr) in METRIC_FIELDS.items():
        value = payload.get(alias)
        if value is None:
            continue

        override = getattr(server, override_attr, None) if server else None
        threshold = override if override is not None else ALERT_THRESHOLDS[field_name]

        open_alert = (
            db.query(AlertEvent)
            .filter(
                AlertEvent.server_id == server_id,
                AlertEvent.metric == field_name,
                AlertEvent.status == "triggered",
            )
            .first()
        )

        if value >= threshold and open_alert is None:
            alert = AlertEvent(
                server_id=server_id,
                metric=field_name,
                value=value,
                threshold=threshold,
                status="triggered",
                triggered_at=now,
            )
            db.add(alert)
            changed_alerts.append(alert)
        elif value < threshold and open_alert is not None:
            open_alert.status = "resolved"
            open_alert.resolved_at = now
            changed_alerts.append(open_alert)

    if changed_alerts:
        db.commit()
        for alert in changed_alerts:
            db.refresh(alert)

    return changed_alerts


def expire_acknowledgments(db: Session, now: datetime) -> list[AlertEvent]:
    if ACK_EXPIRY_HOURS <= 0:
        return []

    cutoff = now - timedelta(hours=ACK_EXPIRY_HOURS)

    expired = (
        db.query(AlertEvent)
        .filter(
            AlertEvent.status == "triggered",
            AlertEvent.acknowledged_at.isnot(None),
            AlertEvent.acknowledged_at < cutoff,
        )
        .all()
    )

    for alert in expired:
        alert.acknowledged_at = None

    if expired:
        db.commit()
        for alert in expired:
            db.refresh(alert)

    return expired