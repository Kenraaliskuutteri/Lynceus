from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.alerts import serialize_alert
from app.core.database import get_db
from app.core.security import require_admin, require_user
from app.models.alert import AlertEvent
from app.schemas.alert import AlertEventOut

router = APIRouter(dependencies=[Depends(require_user)])


@router.get("/alerts", response_model=list[AlertEventOut], response_model_by_alias=True)
def list_alerts(
    server_id: Optional[str] = Query(default=None),
    status: Optional[str] = Query(default=None),
    limit: int = Query(default=100, le=500),
    db: Session = Depends(get_db),
):
    query = db.query(AlertEvent)
    if server_id:
        query = query.filter(AlertEvent.server_id == server_id)
    if status:
        query = query.filter(AlertEvent.status == status)

    rows = query.order_by(desc(AlertEvent.triggered_at)).limit(limit).all()

    return [
        AlertEventOut(
            id=row.id,
            serverId=row.server_id,
            metric=row.metric,
            value=row.value,
            threshold=row.threshold,
            status=row.status,
            triggeredAt=row.triggered_at.replace(tzinfo=timezone.utc).isoformat(),
            resolvedAt=row.resolved_at.replace(tzinfo=timezone.utc).isoformat() if row.resolved_at else None,
            acknowledgedAt=row.acknowledged_at.replace(tzinfo=timezone.utc).isoformat()
            if row.acknowledged_at
            else None,
        )
        for row in rows
    ]


async def _set_acknowledged(alert_id: int, value: Optional[datetime], db: Session) -> AlertEventOut:
    alert = db.get(AlertEvent, alert_id)
    if alert is None:
        raise HTTPException(status_code=404, detail="alert not found")

    alert.acknowledged_at = value
    db.commit()
    db.refresh(alert)

    from app.websockets.metrics_ws import manager
    import json

    frame = json.dumps({"type": "alert", "event": serialize_alert(alert)})
    await manager.broadcast(alert.server_id, None, frame)

    return AlertEventOut(
        id=alert.id,
        serverId=alert.server_id,
        metric=alert.metric,
        value=alert.value,
        threshold=alert.threshold,
        status=alert.status,
        triggeredAt=alert.triggered_at.replace(tzinfo=timezone.utc).isoformat(),
        resolvedAt=alert.resolved_at.replace(tzinfo=timezone.utc).isoformat() if alert.resolved_at else None,
        acknowledgedAt=alert.acknowledged_at.replace(tzinfo=timezone.utc).isoformat()
        if alert.acknowledged_at
        else None,
    )


@router.post("/alerts/{alert_id}/acknowledge", response_model=AlertEventOut, response_model_by_alias=True)
async def acknowledge_alert(alert_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return await _set_acknowledged(alert_id, datetime.now(timezone.utc), db)


@router.post("/alerts/{alert_id}/unacknowledge", response_model=AlertEventOut, response_model_by_alias=True)
async def unacknowledge_alert(alert_id: int, db: Session = Depends(get_db), _: dict = Depends(require_admin)):
    return await _set_acknowledged(alert_id, None, db)


from app import config
from app.core.webhooks import send_test_webhook, _detect_format
from pydantic import BaseModel


class WebhookTestResponse(BaseModel):
    success: bool
    message: str
    target_format: str
    configured: bool


class AlertConfigResponse(BaseModel):
    thresholds: dict[str, float]
    webhook_configured: bool
    webhook_format: str


@router.get("/alerts/config", response_model=AlertConfigResponse)
def get_alert_config():
    return AlertConfigResponse(
        thresholds=config.ALERT_THRESHOLDS,
        webhook_configured=bool(config.WEBHOOK_URL),
        webhook_format=_detect_format(config.WEBHOOK_URL, config.WEBHOOK_FORMAT)
        if config.WEBHOOK_URL
        else "none",
    )


@router.post("/alerts/test-webhook", response_model=WebhookTestResponse)
async def trigger_test_webhook(_: dict = Depends(require_admin)):
    if not config.WEBHOOK_URL:
        return WebhookTestResponse(
            success=False,
            message="No webhook URL configured. Set environment variable LYNCEUS_WEBHOOK_URL.",
            target_format="none",
            configured=False,
        )
    target_format = _detect_format(config.WEBHOOK_URL, config.WEBHOOK_FORMAT)
    success, msg = await send_test_webhook()
    return WebhookTestResponse(
        success=success,
        message=f"Webhook test result: {msg}",
        target_format=target_format,
        configured=True,
    )