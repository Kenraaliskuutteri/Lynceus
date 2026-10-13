from datetime import datetime, timedelta, timezone

import pytest

from app.core import retention
from app.core.retention import floor_bucket, run_retention_pass
from app.models.metric_log import MetricLog
from app.models.metric_rollup import MetricRollup
from helpers import add_metric

NOW = datetime(2026, 10, 13, 12, 0, tzinfo=timezone.utc)


@pytest.fixture(autouse=True)
def retention_settings(monkeypatch):
    monkeypatch.setattr(retention, "RETENTION_DAYS", 7)
    monkeypatch.setattr(retention, "ROLLUP_BUCKET_SECONDS", 300)
    monkeypatch.setattr(retention, "ROLLUP_RETENTION_DAYS", 365)


def seed(db, server_id, start, count, step=timedelta(minutes=1), **values):
    for i in range(count):
        add_metric(db, server_id, start + step * i, **values)
    db.commit()


def test_old_rows_become_rollups(db):
    seed(db, "s1", NOW - timedelta(days=10), 1440)
    seed(db, "s1", NOW - timedelta(hours=1), 60)
    moved = run_retention_pass(db, NOW)
    assert moved == 1440
    assert db.query(MetricLog).count() == 60
    rollups = db.query(MetricRollup).all()
    assert len(rollups) == 288
    assert sum(r.samples for r in rollups) == 1440


def test_rollup_buckets_are_aligned(db):
    seed(db, "s1", NOW - timedelta(days=9), 30)
    run_retention_pass(db, NOW)
    for rollup in db.query(MetricRollup).all():
        assert int(rollup.bucket_start.replace(tzinfo=timezone.utc).timestamp()) % 300 == 0


def test_rollup_computes_average_and_peak(db):
    start = NOW - timedelta(days=8)
    for offset, cpu in enumerate((10.0, 30.0, 20.0)):
        add_metric(db, "s1", start + timedelta(minutes=offset), cpu=cpu, ram=50.0, rx=2.0)
    db.commit()
    run_retention_pass(db, NOW)
    rollup = db.query(MetricRollup).one()
    assert rollup.samples == 3
    assert rollup.cpu_avg == pytest.approx(20.0)
    assert rollup.cpu_max == 30.0
    assert rollup.ram_avg == 50.0
    assert rollup.rx_avg == 2.0


def test_bucket_split_across_chunks_is_merged(db, monkeypatch):
    monkeypatch.setattr(retention, "CHUNK_SIZE", 2)
    start = NOW - timedelta(days=8)
    for offset, cpu in enumerate((10.0, 20.0, 30.0, 40.0, 50.0)):
        add_metric(db, "s1", start + timedelta(seconds=offset * 10), cpu=cpu)
    db.commit()
    run_retention_pass(db, NOW)
    rollup = db.query(MetricRollup).one()
    assert rollup.samples == 5
    assert rollup.cpu_avg == pytest.approx(30.0)
    assert rollup.cpu_max == 50.0


def test_servers_are_rolled_up_separately(db):
    start = NOW - timedelta(days=8)
    add_metric(db, "a", start, cpu=10.0)
    add_metric(db, "b", start, cpu=90.0)
    db.commit()
    run_retention_pass(db, NOW)
    rollups = {r.server_id: r for r in db.query(MetricRollup).all()}
    assert rollups["a"].cpu_avg == 10.0
    assert rollups["b"].cpu_avg == 90.0


def test_second_pass_is_a_noop(db):
    seed(db, "s1", NOW - timedelta(days=9), 100)
    run_retention_pass(db, NOW)
    assert run_retention_pass(db, NOW) == 0
    assert sum(r.samples for r in db.query(MetricRollup).all()) == 100


def test_recent_rows_are_untouched(db):
    seed(db, "s1", NOW - timedelta(days=2), 50)
    assert run_retention_pass(db, NOW) == 0
    assert db.query(MetricLog).count() == 50
    assert db.query(MetricRollup).count() == 0


def test_disabled_when_retention_is_zero(db, monkeypatch):
    monkeypatch.setattr(retention, "RETENTION_DAYS", 0)
    seed(db, "s1", NOW - timedelta(days=30), 20)
    assert run_retention_pass(db, NOW) == 0
    assert db.query(MetricLog).count() == 20


def test_old_rollups_are_pruned(db, monkeypatch):
    monkeypatch.setattr(retention, "ROLLUP_RETENTION_DAYS", 30)
    for days in (40, 5):
        db.add(
            MetricRollup(
                server_id="s1",
                bucket_start=floor_bucket(NOW - timedelta(days=days)),
                samples=1,
                cpu_avg=1, cpu_max=1, ram_avg=1, ram_max=1, disk_avg=1, disk_max=1,
                rx_avg=1, rx_max=1, tx_avg=1, tx_max=1,
            )
        )
    db.commit()
    run_retention_pass(db, NOW)
    remaining = db.query(MetricRollup).all()
    assert len(remaining) == 1
    assert remaining[0].bucket_start.replace(tzinfo=timezone.utc) == floor_bucket(NOW - timedelta(days=5))


def test_zero_rollup_retention_keeps_everything(db, monkeypatch):
    monkeypatch.setattr(retention, "ROLLUP_RETENTION_DAYS", 0)
    seed(db, "s1", NOW - timedelta(days=400), 5)
    run_retention_pass(db, NOW)
    assert db.query(MetricRollup).count() == 1