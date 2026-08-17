import os

from fastapi.testclient import TestClient

os.environ.setdefault("CHAT_SESSION_SECRET", "test-session-secret-value-32-characters")
os.environ.setdefault("ZERO_ADMIN_API_KEY", "test-admin-key-value-with-32-characters")

from main import app

client = TestClient(app)
ADMIN_HEADERS = {"X-Admin-Key": os.environ["ZERO_ADMIN_API_KEY"]}
SESSION_ID = "123e4567-e89b-42d3-a456-426614174000"


def test_admin_delete_requires_key():
    response = client.request("DELETE", "/api/admin/chats", json={"session_ids": [SESSION_ID]})
    assert response.status_code == 401


def test_admin_deletes_one_chat(monkeypatch):
    async def fake_delete(session_ids):
        return {"scope": "selected", "sessions_requested": len(session_ids), "redis_histories_deleted": 1}

    monkeypatch.setattr("api.admin.delete_selected_chats", fake_delete)
    response = client.delete(f"/api/admin/chats/{SESSION_ID}", headers=ADMIN_HEADERS)
    assert response.status_code == 200
    assert response.json()["sessions_requested"] == 1


def test_admin_deletes_selected_chats(monkeypatch):
    async def fake_delete(session_ids):
        return {"scope": "selected", "sessions_requested": len(session_ids), "redis_histories_deleted": 2}

    monkeypatch.setattr("api.admin.delete_selected_chats", fake_delete)
    second_id = "123e4567-e89b-42d3-a456-426614174001"
    response = client.request(
        "DELETE",
        "/api/admin/chats",
        headers=ADMIN_HEADERS,
        json={"session_ids": [SESSION_ID, second_id]},
    )
    assert response.status_code == 200
    assert response.json()["sessions_requested"] == 2


def test_admin_deletes_all_chats(monkeypatch):
    async def fake_delete_all():
        return {"scope": "all", "sessions_requested": -1, "redis_histories_deleted": 3}

    monkeypatch.setattr("api.admin.delete_all_chats", fake_delete_all)
    response = client.request(
        "DELETE",
        "/api/admin/chats",
        headers=ADMIN_HEADERS,
        json={"delete_all": True, "confirmation": "DELETE_ALL_CHATS"},
    )
    assert response.status_code == 200
    assert response.json()["scope"] == "all"
