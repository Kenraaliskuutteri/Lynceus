from helpers import add_server


def test_admin_sets_thresholds(client, db, admin_headers):
    add_server(db, "s1")
    response = client.patch(
        "/api/v1/servers/s1/thresholds",
        headers=admin_headers,
        json={"cpuUsage": 70, "ramUsage": 75, "diskUsage": 80, "offlineSeconds": 30},
    )
    assert response.status_code == 200
    assert response.json() == {"cpuUsage": 70.0, "ramUsage": 75.0, "diskUsage": 80.0, "offlineSeconds": 30}


def test_partial_update_keeps_other_values(client, db, admin_headers):
    add_server(db, "s1", ram_threshold=60.0)
    response = client.patch("/api/v1/servers/s1/thresholds", headers=admin_headers, json={"cpuUsage": 70})
    assert response.json()["cpuUsage"] == 70.0
    assert response.json()["ramUsage"] == 60.0


def test_clear_restores_global_default(client, db, admin_headers):
    add_server(db, "s1", cpu_threshold=40.0, offline_threshold_seconds=99)
    response = client.patch(
        "/api/v1/servers/s1/thresholds",
        headers=admin_headers,
        json={"clear": ["cpu_usage", "offline_seconds"]},
    )
    assert response.json()["cpuUsage"] == 90.0
    assert response.json()["offlineSeconds"] == 10


def test_unknown_server_returns_404(client, admin_headers):
    response = client.patch("/api/v1/servers/missing/thresholds", headers=admin_headers, json={"cpuUsage": 70})
    assert response.status_code == 404