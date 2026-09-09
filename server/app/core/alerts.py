from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.orm import Session

from app.config import ALERT_THRESHOLDS
from app.models.alert import AlertEvent

METRIC_FIELDS = {
    "cpu_usage": "cpuUsage",
    "ram_usage": "ramUsage",
    "disk_usage": "diskUsage",
}


def evaluate_alerts(db: Session, server_id: str, payload: dict, now: Optional[datetime] = None):
    now = now or datetime.now(timezone.utc)

    for field_name, alias in METRIC_FIELDS.items():
        value = payload.get(alias)
        if value is None:
            continue

        threshold = ALERT_THRESHOLDS[field_name]

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
            db.add(
                AlertEvent(
                    server_id=server_id,
                    metric=field_name,
                    value=value,
                    threshold=threshold,
                    status="triggered",
                    triggered_at=now,
                )
            )
        elif value < threshold and open_alert is not None:
            open_alert.status = "resolved"
            open_alert.resolved_at = now

    db.commit()