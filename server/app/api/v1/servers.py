from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.config import ALERT_THRESHOLDS, OFFLINE_THRESHOLD_SECONDS
from app.core.database import get_db
from app.core.security import require_admin, require_user
from app.models.alert import AlertEvent
from app.models.server import Server
from app.models.metric_log import MetricLog
from app.schemas.telemetry import (
    ServerNode,
    SystemMetrics,
    ServerThresholds,
    ServerThresholdsUpdate,
    ServerUptime,
)

router = APIRouter(dependencies=[Depends(require_user)])


def effective_thresholds(server: Server) -> ServerThresholds:
    return ServerThresholds(
        cpuUsage=server.cpu_threshold if server.cpu_threshold is not None else ALERT_THRESHOLDS["cpu_usage"],
        ramUsage=server.ram_threshold if server.ram_threshold is not None else ALERT_THRESHOLDS["ram_usage"],
        diskUsage=server.disk_threshold if server.disk_threshold is not None else ALERT_THRESHOLDS["disk_usage"],
        offlineSeconds=server.offline_threshold_seconds
        if server.offline_threshold_seconds is not None
        else OFFLINE_THRESHOLD_SECONDS,
    )


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
                thresholds=effective_thresholds(server),
            )
        )

    return result


@router.patch("/servers/{server_id}/thresholds", response_model=ServerThresholds, response_model_by_alias=True)
def update_thresholds(
    server_id: str, body: ServerThresholdsUpdate, db: Session = Depends(get_db), _: dict = Depends(require_admin)
):
    server = db.get(Server, server_id)
    if server is None:
        raise HTTPException(status_code=404, detail="server not found")

    if "cpu_usage" in body.clear:
        server.cpu_threshold = None
    elif body.cpu_usage is not None:
        server.cpu_threshold = body.cpu_usage

    if "ram_usage" in body.clear:
        server.ram_threshold = None
    elif body.ram_usage is not None:
        server.ram_threshold = body.ram_usage

    if "disk_usage" in body.clear:
        server.disk_threshold = None
    elif body.disk_usage is not None:
        server.disk_threshold = body.disk_usage

    if "offline_seconds" in body.clear:
        server.offline_threshold_seconds = None
    elif body.offline_seconds is not None:
        server.offline_threshold_seconds = body.offline_seconds

    db.commit()
    db.refresh(server)

    return effective_thresholds(server)


@router.get("/servers/{server_id}/uptime", response_model=ServerUptime, response_model_by_alias=True)
def get_uptime(server_id: str, days: int = 30, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(days=days)

    incidents = (
        db.query(AlertEvent)
        .filter(AlertEvent.server_id == server_id, AlertEvent.metric == "offline")
        .filter((AlertEvent.resolved_at.is_(None)) | (AlertEvent.resolved_at > window_start))
        .filter(AlertEvent.triggered_at < now)
        .all()
    )

    downtime_seconds = 0.0
    for incident in incidents:
        start = incident.triggered_at.replace(tzinfo=timezone.utc)
        end = incident.resolved_at.replace(tzinfo=timezone.utc) if incident.resolved_at else now
        start = max(start, window_start)
        downtime_seconds += max((end - start).total_seconds(), 0)

    window_seconds = (now - window_start).total_seconds()
    uptime_percent = 100.0
    if window_seconds > 0:
        uptime_percent = max(0.0, min(100.0, 100 * (1 - downtime_seconds / window_seconds)))

    return ServerUptime(
        uptimePercent=round(uptime_percent, 2),
        downtimeSeconds=round(downtime_seconds, 0),
        incidentCount=len(incidents),
        windowDays=days,
    )


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