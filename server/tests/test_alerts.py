import json
from datetime import datetime, timedelta, timezone

import pytest
from starlette.websockets import WebSocketDisconnect

from app.core.alerts import evaluate_alerts, expire_acknowledgments
from app.models.alert import AlertEvent
from app.models.metric_log import MetricLog
from app.models.server import Server
from helpers import add_alert, add_server, utcnow

NOW = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)


def test_alert_triggers_at_threshold(db):
    changed = evaluate_alerts(db, "s1", {"cpuUsage": 90.0}, NOW)
    assert len(changed) == 1
    assert changed[0].metric == "cpu_usage"
    assert changed[0].status == "triggered"
    assert changed[0].threshold == 90.0


def test_no_alert_below_threshold(db):
    assert evaluate_alerts(db, "s1", {"cpuUsage": 89.9}, NOW) == []


def test_no_duplicate_while_open(db):
    evaluate_alerts(db, "s1", {"cpuUsage": 95.0}, NOW)
    assert evaluate_alerts(db, "s1", {"cpuUsage": 97.0}, NOW) == []
    assert db.query(AlertEvent).count() == 1


def test_hysteresis_keeps_alert_open_inside_band(db):
    evaluate_alerts(db, "s1", {"cpuUsage": 95.0}, NOW)
    assert evaluate_alerts(db, "s1", {"cpuUsage": 88.0}, NOW) == []
    assert db.query(AlertEvent).one().status == "triggered"


def test_alert_resolves_below_band(db):
    evaluate_alerts(db, "s1", {"cpuUsage": 95.0}, NOW)
    later = NOW + timedelta(minutes=1)
    changed = evaluate_alerts(db, "s1", {"cpuUsage": 85.0}, later)
    assert len(changed) == 1
    assert changed[0].status == "resolved"
    assert changed[0].resolved_at is not None


def test_alert_can_retrigger_after_resolve(db):
    evaluate_alerts(db, "s1", {"cpuUsage": 95.0}, NOW)
    evaluate_alerts(db, "s1", {"cpuUsage": 10.0}, NOW + timedelta(minutes=1))
    evaluate_alerts(db, "s1", {"cpuUsage": 95.0}, NOW + timedelta(minutes=2))
    statuses = sorted(a.status for a in db.query(AlertEvent).all())
    assert statuses == ["resolved", "triggered"]


def test_server_override_replaces_global_threshold(db):
    add_server(db, "s1", cpu_threshold=50.0)
    changed = evaluate_alerts(db, "s1", {"cpuUsage": 60.0}, NOW)
    assert len(changed) == 1
    assert changed[0].threshold == 50.0


def test_override_does_not_leak_to_other_servers(db):
    add_server(db, "s1", cpu_threshold=50.0)
    assert evaluate_alerts(db, "s2", {"cpuUsage": 60.0}, NOW) == []


def test_missing_fields_are_ignored(db):
    assert evaluate_alerts(db, "s1", {}, NOW) == []


def test_metrics_alert_independently(db):
    changed = evaluate_alerts(db, "s1", {"cpuUsage": 95.0, "ramUsage": 95.0, "diskUsage": 10.0}, NOW)
    assert sorted(a.metric for a in changed) == ["cpu_usage", "ram_usage"]


def test_acknowledgement_expires(db, monkeypatch):
    monkeypatch.setattr("app.core.alerts.ACK_EXPIRY_HOURS", 1.0)
    alert = add_alert(db, triggered_at=NOW - timedelta(hours=3), acknowledged_at=NOW - timedelta(hours=2))
    expired = expire_acknowledgments(db, NOW)
    assert [a.id for a in expired] == [alert.id]
    assert alert.acknowledged_at is None


def test_recent_acknowledgement_is_kept(db, monkeypatch):
    monkeypatch.setattr("app.core.alerts.ACK_EXPIRY_HOURS", 1.0)
    add_alert(db, triggered_at=NOW - timedelta(hours=1), acknowledged_at=NOW - timedelta(minutes=10))
    assert expire_acknowledgments(db, NOW) == []


def test_acknowledgement_expiry_disabled_by_default(db):
    add_alert(db, triggered_at=NOW - timedelta(days=5), acknowledged_at=NOW - timedelta(days=4))
    assert expire_acknowledgments(db, NOW) == []


def test_list_alerts_filters(client, db, viewer_headers):
    add_alert(db, "s1", status="triggered")
    add_alert(db, "s2", status="resolved", resolved_at=utcnow())
    assert len(client.get("/api/v1/alerts", headers=viewer_headers).json()) == 2
    triggered = client.get("/api/v1/alerts?status=triggered", headers=viewer_headers).json()
    assert [a["serverId"] for a in triggered] == ["s1"]
    by_server = client.get("/api/v1/alerts?server_id=s2", headers=viewer_headers).json()
    assert [a["status"] for a in by_server] == ["resolved"]


def test_acknowledge_and_unacknowledge(client, db, admin_headers):
    alert = add_alert(db)
    response = client.post(f"/api/v1/alerts/{alert.id}/acknowledge", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["acknowledgedAt"]
    response = client.post(f"/api/v1/alerts/{alert.id}/unacknowledge", headers=admin_headers)
    assert response.status_code == 200
    assert response.json()["acknowledgedAt"] is None


def test_acknowledge_missing_alert_returns_404(client, admin_headers):
    assert client.post("/api/v1/alerts/999/acknowledge", headers=admin_headers).status_code == 404


def test_alert_config_exposes_thresholds(client, viewer_headers):
    body = client.get("/api/v1/alerts/config", headers=viewer_headers).json()
    assert body["thresholds"]["cpu_usage"] == 90.0
    assert body["webhook_configured"] is False


def test_ws_rejects_bad_key(client, monkeypatch):
    monkeypatch.setattr("app.core.security.API_KEY", "k" * 20)
    with pytest.raises(WebSocketDisconnect) as excinfo:
        with client.websocket_connect("/api/v1/ws/metrics/s1?key=wrong") as ws:
            ws.receive_text()
    assert excinfo.value.code == 1008


def test_ws_accepts_good_key(client, db, monkeypatch):
    monkeypatch.setattr("app.core.security.API_KEY", "k" * 20)
    frame = {"cpuUsage": 10.0, "ramUsage": 20.0, "diskUsage": 30.0, "networkRxKb": 1.0, "networkTxKb": 2.0}
    with client.websocket_connect(f"/api/v1/ws/metrics/s1?key={'k' * 20}") as ws:
        ws.send_text(json.dumps(frame))
    db.expire_all()
    assert db.query(MetricLog).count() == 1


def test_ws_ingestion_stores_metrics_and_raises_alerts(client, db):
    frame = {"cpuUsage": 95.0, "ramUsage": 40.0, "diskUsage": 50.0, "networkRxKb": 1.0, "networkTxKb": 2.0}
    with client.websocket_connect("/api/v1/ws/metrics/s1") as ws:
        ws.send_text("not json")
        ws.send_text(json.dumps(frame))
    db.expire_all()
    assert db.get(Server, "s1") is not None
    log = db.query(MetricLog).one()
    assert log.cpu_usage == 95.0
    alert = db.query(AlertEvent).one()
    assert alert.metric == "cpu_usage"
    assert alert.status == "triggered"