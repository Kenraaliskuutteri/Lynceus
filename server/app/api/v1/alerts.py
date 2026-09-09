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