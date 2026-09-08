from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import OFFLINE_THRESHOLD_SECONDS
from app.core.database import get_db
from app.models.server import Server
from app.models.metric_log import MetricLog
from app.schemas.telemetry import ServerNode, SystemMetrics

router = APIRouter()


@router.get("/servers", response_model=list[ServerNode], response_model_by_alias=True)
def list_servers(db: Session = Depends(get_db)):
    servers = db.query(Server).all()
    now = datetime.now(timezone.utc)
    threshold = timedelta(seconds=OFFLINE_THRESHOLD_SECONDS)

    result = []
    for server in servers:
        last_seen = server.last_seen
        if last_seen and last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)

        is_online = bool(last_seen and now - last_seen < threshold)

        latest = (
            db.query(MetricLog)
            .filter(MetricLog.server_id == server.id)
            .order_by(desc(MetricLog.timestamp))
            .first()
        )

        metrics = None
        if latest:
            metrics = SystemMetrics(
                timestamp=int(latest.timestamp.replace(tzinfo=timezone.utc).timestamp() * 1000),
                cpuUsage=latest.cpu_usage,
                ramUsage=latest.ram_usage,
                diskUsage=latest.disk_usage,
                networkRxKb=latest.network_rx_kb,
                networkTxKb=latest.network_tx_kb,
            )

        result.append(
            ServerNode(
                id=server.id,
                hostname=server.hostname,
                ipAddress=server.ip_address,
                status="online" if is_online else "offline",
                lastSeen=last_seen.isoformat() if last_seen else None,
                metrics=metrics,
            )
        )

    return result


TARGET_POINTS = 200


def downsample(rows: list[MetricLog]) -> list[SystemMetrics]:
    if len(rows) <= TARGET_POINTS:
        return [
            SystemMetrics(
                timestamp=int(row.timestamp.replace(tzinfo=timezone.utc).timestamp() * 1000),
                cpuUsage=row.cpu_usage,
                ramUsage=row.ram_usage,
                diskUsage=row.disk_usage,
                networkRxKb=row.network_rx_kb,
                networkTxKb=row.network_tx_kb,
            )
            for row in rows
        ]

    bucket_size = len(rows) / TARGET_POINTS
    result = []

    for i in range(TARGET_POINTS):
        start = int(i * bucket_size)
        end = int((i + 1) * bucket_size)
        chunk = rows[start:end]
        if not chunk:
            continue

        count = len(chunk)
        avg_ts = int(
            sum(row.timestamp.replace(tzinfo=timezone.utc).timestamp() for row in chunk) / count * 1000
        )

        result.append(
            SystemMetrics(
                timestamp=avg_ts,
                cpuUsage=sum(row.cpu_usage for row in chunk) / count,
                ramUsage=sum(row.ram_usage for row in chunk) / count,
                diskUsage=sum(row.disk_usage for row in chunk) / count,
                networkRxKb=sum(row.network_rx_kb for row in chunk) / count,
                networkTxKb=sum(row.network_tx_kb for row in chunk) / count,
            )
        )

    return result


@router.get("/servers/{server_id}/history", response_model=list[SystemMetrics], response_model_by_alias=True)
def get_history(server_id: str, minutes: int = 60, db: Session = Depends(get_db)):
    cutoff = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    rows = (
        db.query(MetricLog)
        .filter(MetricLog.server_id == server_id, MetricLog.timestamp >= cutoff)
        .order_by(MetricLog.timestamp.asc())
        .limit(20000)
        .all()
    )

    return downsample(rows)