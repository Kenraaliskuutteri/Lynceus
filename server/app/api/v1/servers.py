from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import desc, func
from sqlalchemy.orm import Session

from app.config import ALERT_THRESHOLDS, OFFLINE_THRESHOLD_SECONDS, RETENTION_DAYS, ROLLUP_BUCKET_SECONDS
from app.core.csv_export import csv_response
from app.core.database import SessionLocal, get_db
from app.core.retention import as_utc
from app.core.security import require_admin, require_user
from app.models.alert import AlertEvent
from app.models.server import Server
from app.models.metric_log import MetricLog
from app.models.metric_rollup import MetricRollup
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

    result = []
    for server in servers:
        last_seen = server.last_seen
        if last_seen and last_seen.tzinfo is None:
            last_seen = last_seen.replace(tzinfo=timezone.utc)

        threshold_seconds = server.offline_threshold_seconds or OFFLINE_THRESHOLD_SECONDS
        is_online = bool(last_seen and (now - last_seen).total_seconds() < threshold_seconds)

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


def log_to_metric(row: MetricLog) -> SystemMetrics:
    return SystemMetrics(
        timestamp=int(as_utc(row.timestamp).timestamp() * 1000),
        cpuUsage=row.cpu_usage,
        ramUsage=row.ram_usage,
        diskUsage=row.disk_usage,
        networkRxKb=row.network_rx_kb,
        networkTxKb=row.network_tx_kb,
    )


def rollup_to_metric(row: MetricRollup) -> SystemMetrics:
    mid = as_utc(row.bucket_start).timestamp() + ROLLUP_BUCKET_SECONDS / 2
    return SystemMetrics(
        timestamp=int(mid * 1000),
        cpuUsage=row.cpu_avg,
        ramUsage=row.ram_avg,
        diskUsage=row.disk_avg,
        networkRxKb=row.rx_avg,
        networkTxKb=row.tx_avg,
    )


def downsample(points: list[SystemMetrics]) -> list[SystemMetrics]:
    if len(points) <= TARGET_POINTS:
        return points

    bucket_size = len(points) / TARGET_POINTS
    result = []

    for i in range(TARGET_POINTS):
        chunk = points[int(i * bucket_size):int((i + 1) * bucket_size)]
        if not chunk:
            continue

        count = len(chunk)
        result.append(
            SystemMetrics(
                timestamp=int(sum(p.timestamp for p in chunk) / count),
                cpuUsage=sum(p.cpu_usage for p in chunk) / count,
                ramUsage=sum(p.ram_usage for p in chunk) / count,
                diskUsage=sum(p.disk_usage for p in chunk) / count,
                networkRxKb=sum(p.network_rx_kb for p in chunk) / count,
                networkTxKb=sum(p.network_tx_kb for p in chunk) / count,
            )
        )

    return result


@router.get("/servers/{server_id}/history", response_model=list[SystemMetrics], response_model_by_alias=True)
def get_history(server_id: str, minutes: int = 60, db: Session = Depends(get_db)):
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(minutes=minutes)

    rows = (
        db.query(MetricLog)
        .filter(MetricLog.server_id == server_id, MetricLog.timestamp >= window_start)
        .order_by(MetricLog.timestamp.desc())
        .limit(20000)
        .all()
    )
    rows.reverse()
    points = [log_to_metric(row) for row in rows]

    if RETENTION_DAYS > 0:
        boundary = as_utc(rows[0].timestamp) if rows else now
        rollups = (
            db.query(MetricRollup)
            .filter(
                MetricRollup.server_id == server_id,
                MetricRollup.bucket_start >= window_start,
                MetricRollup.bucket_start <= boundary - timedelta(seconds=ROLLUP_BUCKET_SECONDS),
            )
            .order_by(MetricRollup.bucket_start.asc())
            .all()
        )
        points = [rollup_to_metric(r) for r in rollups] + points

    return downsample(points)


HISTORY_CSV_HEADER = [
    "timestamp",
    "resolution",
    "samples",
    "cpu_usage",
    "cpu_max",
    "ram_usage",
    "ram_max",
    "disk_usage",
    "disk_max",
    "network_rx_kb",
    "network_rx_max",
    "network_tx_kb",
    "network_tx_max",
]


@router.get("/servers/{server_id}/history/export")
def export_history(server_id: str, minutes: int = Query(default=60, ge=1)):
    window_start = datetime.now(timezone.utc) - timedelta(minutes=minutes)

    def rows():
        db = SessionLocal()
        try:
            first_raw = (
                db.query(func.min(MetricLog.timestamp))
                .filter(MetricLog.server_id == server_id, MetricLog.timestamp >= window_start)
                .scalar()
            )

            if RETENTION_DAYS > 0:
                boundary = as_utc(first_raw) if first_raw else datetime.now(timezone.utc)
                rollups = (
                    db.query(MetricRollup)
                    .filter(
                        MetricRollup.server_id == server_id,
                        MetricRollup.bucket_start >= window_start,
                        MetricRollup.bucket_start <= boundary - timedelta(seconds=ROLLUP_BUCKET_SECONDS),
                    )
                    .order_by(MetricRollup.bucket_start.asc())
                    .yield_per(1000)
                )
                for r in rollups:
                    yield [
                        as_utc(r.bucket_start).isoformat(),
                        "rollup",
                        r.samples,
                        r.cpu_avg,
                        r.cpu_max,
                        r.ram_avg,
                        r.ram_max,
                        r.disk_avg,
                        r.disk_max,
                        r.rx_avg,
                        r.rx_max,
                        r.tx_avg,
                        r.tx_max,
                    ]

            raw = (
                db.query(MetricLog)
                .filter(MetricLog.server_id == server_id, MetricLog.timestamp >= window_start)
                .order_by(MetricLog.timestamp.asc())
                .yield_per(1000)
            )
            for r in raw:
                yield [
                    as_utc(r.timestamp).isoformat(),
                    "raw",
                    1,
                    r.cpu_usage,
                    r.cpu_usage,
                    r.ram_usage,
                    r.ram_usage,
                    r.disk_usage,
                    r.disk_usage,
                    r.network_rx_kb,
                    r.network_rx_kb,
                    r.network_tx_kb,
                    r.network_tx_kb,
                ]
        finally:
            db.close()

    return csv_response(f"{server_id}-history-{minutes}m.csv", HISTORY_CSV_HEADER, rows())