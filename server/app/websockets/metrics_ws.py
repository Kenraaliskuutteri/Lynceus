import asyncio
import json
from datetime import datetime, timezone
from typing import Optional

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.alerts import evaluate_alerts
from app.core.webhooks import dispatch_alert_webhook
from app.models.server import Server
from app.models.metric_log import MetricLog
from app.models.alert import AlertEvent

router = APIRouter()


class ConnectionManager:
    def __init__(self):
        self.rooms: dict[str, set[WebSocket]] = {}

    async def join(self, server_id: str, ws: WebSocket):
        self.rooms.setdefault(server_id, set()).add(ws)

    def leave(self, server_id: str, ws: WebSocket):
        peers = self.rooms.get(server_id)
        if peers and ws in peers:
            peers.remove(ws)
        if peers is not None and not peers:
            self.rooms.pop(server_id, None)

    async def broadcast(self, server_id: str, sender: Optional[WebSocket], message: str):
        peers = list(self.rooms.get(server_id, set()))
        for peer in peers:
            if peer is not sender:
                try:
                    await peer.send_text(message)
                except Exception:
                    pass


manager = ConnectionManager()


def persist_metric(db: Session, server_id: str, payload: dict) -> list[AlertEvent]:
    now = datetime.now(timezone.utc)

    server = db.get(Server, server_id)
    if server is None:
        server = Server(id=server_id, hostname=server_id, ip_address="unknown", last_seen=now)
        db.add(server)
    else:
        server.last_seen = now

    raw_ts = payload.get("timestamp")
    if raw_ts and isinstance(raw_ts, (int, float)) and raw_ts > 0:
        try:
            metric_time = datetime.fromtimestamp(raw_ts / 1000.0, tz=timezone.utc)
        except (ValueError, OverflowError, OSError):
            metric_time = now
    else:
        metric_time = now

    log = MetricLog(
        server_id=server_id,
        timestamp=metric_time,
        cpu_usage=payload.get("cpuUsage", 0.0),
        ram_usage=payload.get("ramUsage", 0.0),
        disk_usage=payload.get("diskUsage", 0.0),
        network_rx_kb=payload.get("networkRxKb", 0.0),
        network_tx_kb=payload.get("networkTxKb", 0.0),
    )
    db.add(log)
    db.commit()
    return evaluate_alerts(db, server_id, payload, metric_time)


@router.websocket("/ws/metrics/{server_id}")
async def metrics_socket(websocket: WebSocket, server_id: str, key: str = Query(default="")):
    await websocket.accept()
    await manager.join(server_id, websocket)

    try:
        while True:
            raw = await websocket.receive_text()

            try:
                payload = json.loads(raw)
            except ValueError:
                continue

            db = SessionLocal()
            try:
                changed_alerts = persist_metric(db, server_id, payload)
            finally:
                db.close()

            await manager.broadcast(server_id, websocket, raw)

            for alert in changed_alerts:
                asyncio.create_task(dispatch_alert_webhook(alert))
                alert_frame = json.dumps({
                    "type": "alert",
                    "event": {
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
                    },
                })
                await manager.broadcast(server_id, None, alert_frame)
    except WebSocketDisconnect:
        pass
    finally:
        manager.leave(server_id, websocket)