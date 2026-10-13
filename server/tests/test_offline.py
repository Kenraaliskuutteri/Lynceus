from datetime import datetime, timedelta, timezone

from app.core.offline_monitor import check_offline_servers
from app.models.alert import AlertEvent
from helpers import add_alert, add_server, utcnow

NOW = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)


def test_stale_server_raises_offline_alert(db):
    add_server(db, "s1", last_seen=NOW - timedelta(seconds=60))
    changed = check_offline_servers(db, NOW)
    assert len(changed) == 1
    assert changed[0].metric == "offline"
    assert changed[0].status == "triggered"
    assert changed[0].threshold == 10.0


def test_fresh_server_stays_online(db):
    add_server(db, "s1", last_seen=NOW - timedelta(seconds=2))
    assert check_offline_servers(db, NOW) == []


def test_offline_alert_not_duplicated(db):
    add_server(db, "s1", last_seen=NOW - timedelta(seconds=60))
    check_offline_servers(db, NOW)
    assert check_offline_servers(db, NOW + timedelta(seconds=5)) == []
    assert db.query(AlertEvent).count() == 1


def test_alert_resolves_when_server_returns(db):
    server = add_server(db, "s1", last_seen=NOW - timedelta(seconds=60))
    check_offline_servers(db, NOW)
    server.last_seen = NOW + timedelta(seconds=4)
    db.commit()
    changed = check_offline_servers(db, NOW + timedelta(seconds=5))
    assert len(changed) == 1
    assert changed[0].status == "resolved"
    assert changed[0].resolved_at is not None


def test_server_override_extends_timeout(db):
    add_server(db, "s1", last_seen=NOW - timedelta(seconds=60), offline_threshold_seconds=300)
    assert check_offline_servers(db, NOW) == []


def test_server_override_shortens_timeout(db):
    add_server(db, "s1", last_seen=NOW - timedelta(seconds=8), offline_threshold_seconds=5)
    assert len(check_offline_servers(db, NOW)) == 1


def test_server_that_never_reported_is_skipped(db):
    add_server(db, "s1", last_seen=None)
    assert check_offline_servers(db, NOW) == []


def test_only_stale_servers_alert(db):
    add_server(db, "old", last_seen=NOW - timedelta(seconds=60))
    add_server(db, "new", last_seen=NOW - timedelta(seconds=1))
    changed = check_offline_servers(db, NOW)
    assert [a.server_id for a in changed] == ["old"]


def test_list_servers_status_uses_per_server_threshold(client, db, viewer_headers):
    stale = utcnow() - timedelta(seconds=100)
    add_server(db, "default", last_seen=stale)
    add_server(db, "patient", last_seen=stale, offline_threshold_seconds=3600)
    servers = {s["id"]: s for s in client.get("/api/v1/servers", headers=viewer_headers).json()}
    assert servers["default"]["status"] == "offline"
    assert servers["patient"]["status"] == "online"


def test_list_servers_reports_effective_thresholds(client, db, viewer_headers):
    add_server(db, "s1", last_seen=utcnow(), cpu_threshold=55.0)
    server = client.get("/api/v1/servers", headers=viewer_headers).json()[0]
    assert server["thresholds"] == {"cpuUsage": 55.0, "ramUsage": 90.0, "diskUsage": 90.0, "offlineSeconds": 10}


def test_uptime_reflects_incident_duration(client, db, viewer_headers):
    now = utcnow()
    add_alert(
        db,
        "s1",
        metric="offline",
        status="resolved",
        triggered_at=now - timedelta(hours=18),
        resolved_at=now - timedelta(hours=6),
    )
    body = client.get("/api/v1/servers/s1/uptime?days=1", headers=viewer_headers).json()
    assert body["incidentCount"] == 1
    assert body["downtimeSeconds"] == 12 * 3600
    assert abs(body["uptimePercent"] - 50.0) < 0.1


def test_uptime_is_full_without_incidents(client, viewer_headers):
    body = client.get("/api/v1/servers/s1/uptime", headers=viewer_headers).json()
    assert body["uptimePercent"] == 100.0
    assert body["incidentCount"] == 0