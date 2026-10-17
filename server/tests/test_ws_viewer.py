import json

import pytest
from starlette.websockets import WebSocketDisconnect

from app.models.metric_log import MetricLog
from app.websockets.metrics_ws import manager


def token_from(headers):
    return headers["Authorization"].split(" ", 1)[1]


def test_viewer_token_accepted_when_api_key_set(client, viewer_headers, monkeypatch):
    monkeypatch.setattr("app.core.security.API_KEY", "k" * 20)
    joined = []
    original_join = manager.join

    async def spy_join(server_id, ws):
        joined.append(server_id)
        await original_join(server_id, ws)

    monkeypatch.setattr(manager, "join", spy_join)
    token = token_from(viewer_headers)
    with client.websocket_connect(f"/api/v1/ws/metrics/s1?token={token}"):
        pass
    assert joined == ["s1"]


def test_viewer_token_invalid_rejected(client, monkeypatch):
    monkeypatch.setattr("app.core.security.API_KEY", "k" * 20)
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/api/v1/ws/metrics/s1?token=garbage") as ws:
            ws.receive_text()
    assert excinfo.value.code == 1008


def test_viewer_cannot_ingest_metrics(client, db, viewer_headers, monkeypatch):
    monkeypatch.setattr("app.core.security.API_KEY", "k" * 20)
    token = token_from(viewer_headers)
    frame = {"cpuUsage": 10.0, "ramUsage": 20.0, "diskUsage": 30.0, "networkRxKb": 1.0, "networkTxKb": 2.0}
    with client.websocket_connect(f"/api/v1/ws/metrics/s1?token={token}") as ws:
        ws.send_text(json.dumps(frame))
    db.expire_all()
    assert db.query(MetricLog).count() == 0