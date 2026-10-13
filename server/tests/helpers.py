from datetime import datetime, timezone

from app.models.alert import AlertEvent
from app.models.metric_log import MetricLog
from app.models.server import Server


def utcnow():
    return datetime.now(timezone.utc)


def add_server(db, server_id="s1", last_seen=None, **fields):
    server = Server(id=server_id, hostname=server_id, ip_address="unknown", last_seen=last_seen, **fields)
    db.add(server)
    db.commit()
    return server


def add_metric(db, server_id, timestamp, cpu=1.0, ram=2.0, disk=3.0, rx=4.0, tx=5.0):
    db.add(
        MetricLog(
            server_id=server_id,
            timestamp=timestamp,
            cpu_usage=cpu,
            ram_usage=ram,
            disk_usage=disk,
            network_rx_kb=rx,
            network_tx_kb=tx,
        )
    )


def add_alert(db, server_id="s1", metric="cpu_usage", status="triggered", triggered_at=None, **fields):
    alert = AlertEvent(
        server_id=server_id,
        metric=metric,
        value=95.0,
        threshold=90.0,
        status=status,
        triggered_at=triggered_at or utcnow(),
        **fields,
    )
    db.add(alert)
    db.commit()
    db.refresh(alert)
    return alert