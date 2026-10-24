from api.app.config import settings


def test_deadline_endpoint_requires_secret(client, seed_data, monkeypatch):
    monkeypatch.setattr(settings, "CRON_SECRET", "test-cron-secret")
    path = "/api/v1/internal/tick"
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"Authorization": "Bearer wrong"}).status_code == 401
    response = client.get(path, headers={"Authorization": "Bearer test-cron-secret"})
    assert response.status_code == 200
