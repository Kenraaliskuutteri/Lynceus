import csv
import io
from datetime import timedelta

import pytest

from app.api.v1.servers import TARGET_POINTS, downsample
from app.core import retention
from app.core.retention import run_retention_pass
from app.schemas.telemetry import SystemMetrics
from helpers import add_alert, add_metric, utcnow


@pytest.fixture
def retention_on(monkeypatch):
    monkeypatch.setattr(retention, "RETENTION_DAYS", 7)
    monkeypatch.setattr("app.api.v1.servers.RETENTION_DAYS", 7)


def seed_ten_days(db, server_id="s1"):
    now = utcnow()
    start = now - timedelta(days=9, hours=23)
    count = 0
    moment = start
    while moment < now:
        add_metric(db, server_id, moment, cpu=float(count % 100))
        moment += timedelta(minutes=10)
        count += 1
    db.commit()
    return count


def parse(response):
    return list(csv.DictReader(io.StringIO(response.text)))


def test_downsample_leaves_small_series_alone():
    points = [SystemMetrics(timestamp=i, cpuUsage=1, ramUsage=1, diskUsage=1, networkRxKb=1, networkTxKb=1) for i in range(50)]
    assert downsample(points) == points


def test_downsample_caps_series_length():
    points = [SystemMetrics(timestamp=i, cpuUsage=i, ramUsage=1, diskUsage=1, networkRxKb=1, networkTxKb=1) for i in range(5000)]
    result = downsample(points)
    assert len(result) == TARGET_POINTS
    assert [p.timestamp for p in result] == sorted(p.timestamp for p in result)


def test_history_returns_recent_raw_points(client, db, viewer_headers):
    now = utcnow()
    for i in range(5):
        add_metric(db, "s1", now - timedelta(minutes=i))
    db.commit()
    body = client.get("/api/v1/servers/s1/history?minutes=60", headers=viewer_headers).json()
    assert len(body) == 5
    assert body[0]["timestamp"] < body[-1]["timestamp"]


def test_history_excludes_other_servers(client, db, viewer_headers):
    add_metric(db, "s1", utcnow())
    add_metric(db, "s2", utcnow())
    db.commit()
    assert len(client.get("/api/v1/servers/s1/history", headers=viewer_headers).json()) == 1


def test_history_spans_rollups_and_raw_rows(client, db, viewer_headers, retention_on):
    seed_ten_days(db)
    run_retention_pass(db, utcnow())
    body = client.get("/api/v1/servers/s1/history?minutes=14400", headers=viewer_headers).json()
    timestamps = [p["timestamp"] for p in body]
    assert len(body) <= TARGET_POINTS
    assert timestamps == sorted(timestamps)
    span_days = (timestamps[-1] - timestamps[0]) / 86400000
    assert span_days > 9


def test_history_short_range_ignores_rollups(client, db, viewer_headers, retention_on):
    seed_ten_days(db)
    run_retention_pass(db, utcnow())
    body = client.get("/api/v1/servers/s1/history?minutes=60", headers=viewer_headers).json()
    assert 1 <= len(body) <= 7


def test_history_requires_auth(client):
    assert client.get("/api/v1/servers/s1/history").status_code == 401


def test_history_export_contains_every_sample(client, db, viewer_headers, retention_on):
    total = seed_ten_days(db)
    run_retention_pass(db, utcnow())
    response = client.get("/api/v1/servers/s1/history/export?minutes=14400", headers=viewer_headers)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    rows = parse(response)
    assert sum(int(r["samples"]) for r in rows) == total
    assert {r["resolution"] for r in rows} == {"raw", "rollup"}


def test_history_export_header_and_ordering(client, db, viewer_headers):
    now = utcnow()
    for i in range(3):
        add_metric(db, "s1", now - timedelta(minutes=i), cpu=10.0 * (i + 1))
    db.commit()
    response = client.get("/api/v1/servers/s1/history/export?minutes=60", headers=viewer_headers)
    assert response.text.splitlines()[0] == (
        "timestamp,resolution,samples,cpu_usage,cpu_max,ram_usage,ram_max,disk_usage,disk_max,"
        "network_rx_kb,network_rx_max,network_tx_kb,network_tx_max"
    )
    rows = parse(response)
    assert [r["timestamp"] for r in rows] == sorted(r["timestamp"] for r in rows)
    assert {r["resolution"] for r in rows} == {"raw"}


def test_history_export_filename_is_sanitized(client, viewer_headers):
    response = client.get("/api/v1/servers/a b/history/export?minutes=5", headers=viewer_headers)
    assert 'filename="a_b-history-5m.csv"' in response.headers["content-disposition"]


def test_history_export_rejects_nonpositive_range(client, viewer_headers):
    assert client.get("/api/v1/servers/s1/history/export?minutes=0", headers=viewer_headers).status_code == 422


def test_history_export_requires_auth(client):
    assert client.get("/api/v1/servers/s1/history/export").status_code == 401


def test_alerts_export_filters(client, db, viewer_headers):
    add_alert(db, "s1", status="triggered")
    add_alert(db, "s2", status="resolved", resolved_at=utcnow())
    assert len(parse(client.get("/api/v1/alerts/export", headers=viewer_headers))) == 2
    resolved = parse(client.get("/api/v1/alerts/export?status=resolved", headers=viewer_headers))
    assert [r["server_id"] for r in resolved] == ["s2"]
    assert resolved[0]["resolved_at"]
    only_s1 = parse(client.get("/api/v1/alerts/export?server_id=s1", headers=viewer_headers))
    assert [r["status"] for r in only_s1] == ["triggered"]
    assert only_s1[0]["resolved_at"] == ""


def test_alerts_export_empty_has_header(client, viewer_headers):
    response = client.get("/api/v1/alerts/export", headers=viewer_headers)
    assert response.text.strip() == "id,server_id,metric,value,threshold,status,triggered_at,resolved_at,acknowledged_at"


def test_alerts_export_neutralizes_spreadsheet_formulas(client, db, viewer_headers):
    add_alert(db, "=HYPERLINK(1)")
    rows = parse(client.get("/api/v1/alerts/export", headers=viewer_headers))
    assert rows[0]["server_id"] == "'=HYPERLINK(1)"


def test_alerts_export_requires_auth(client):
    assert client.get("/api/v1/alerts/export").status_code == 401