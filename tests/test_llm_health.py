from fastapi.testclient import TestClient
import main


def test_llm_health_endpoint_fallback(monkeypatch):
    monkeypatch.setattr(
        main,
        "check_llm_health",
        lambda: {
            "llm_ready": False,
            "mode": "Template fallback",
            "provider": "None",
            "model": "gpt-5.4-mini",
            "status": "test fallback",
            "message": "fallback works",
        },
    )

    client = TestClient(main.app)
    response = client.get("/llm-health")

    assert response.status_code == 200
    data = response.json()
    assert data["llm_ready"] is False
    assert data["mode"] == "Template fallback"
    assert data["model"] == "gpt-5.4-mini"
