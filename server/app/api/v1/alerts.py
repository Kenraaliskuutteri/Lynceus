from datetime import timezone
from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models.alert import AlertEvent
from app.schemas.alert import AlertEventOut

router = APIRouter()


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
        )
        for row in rows
    ]


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
async def trigger_test_webhook():
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