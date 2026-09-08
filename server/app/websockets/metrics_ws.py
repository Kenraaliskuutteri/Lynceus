import json
from datetime import datetime, timezone

from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Query
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.server import Server
from app.models.metric_log import MetricLog

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

    async def broadcast(self, server_id: str, sender: WebSocket, message: str):
        for peer in self.rooms.get(server_id, set()):
            if peer is not sender:
                await peer.send_text(message)


manager = ConnectionManager()


def persist_metric(db: Session, server_id: str, payload: dict):
    now = datetime.now(timezone.utc)

    server = db.get(Server, server_id)
    if server is None:
        server = Server(id=server_id, hostname=server_id, ip_address="unknown", last_seen=now)
        db.add(server)
    else:
        server.last_seen = now

    log = MetricLog(
        server_id=server_id,
        timestamp=now,
        cpu_usage=payload.get("cpuUsage", 0.0),
        ram_usage=payload.get("ramUsage", 0.0),
        disk_usage=payload.get("diskUsage", 0.0),
        network_rx_kb=payload.get("networkRxKb", 0.0),
        network_tx_kb=payload.get("networkTxKb", 0.0),
    )
    db.add(log)
    db.commit()


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
                persist_metric(db, server_id, payload)
            finally:
                db.close()

            await manager.broadcast(server_id, websocket, raw)
    except WebSocketDisconnect:
        pass
    finally:
        manager.leave(server_id, websocket)