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