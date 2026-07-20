from fastapi.testclient import TestClient

from main import app

client = TestClient(app)

def test_keep_alive():
    response = client.get("/keep-alive")
    assert response.status_code == 200
    assert response.json() == {"status": "alive"}

def test_chat_rate_limit():
    # Because we don't have a mocked LLM easily, we can just test the 
    # rate limit by hitting it without X-Forwarded-For (uses TestClient IP)
    # The rate limit is 7 requests. Let's make 8 requests.
    for _ in range(7):
        client.post("/api/chat", json={"messages": [{"role": "user", "content": "Hi!"}]})
        
    response = client.post("/api/chat", json={"messages": [{"role": "user", "content": "Hi!"}]})
    assert response.status_code == 429
    assert "Too many requests" in response.json()["detail"]
