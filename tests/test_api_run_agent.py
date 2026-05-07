from fastapi.testclient import TestClient
import app.agent_engine as agent_engine
from main import app


def test_run_agent_endpoint_returns_complete_payload(monkeypatch):
    monkeypatch.setattr(
        agent_engine,
        "get_integration_status",
        lambda: [
            {
                "label": "Ridership context",
                "status": "Fallback active",
                "detail": "Test fallback",
                "source": "test",
            }
        ],
    )
    monkeypatch.setattr(
        agent_engine,
        "generate_llm_outputs",
        lambda package: {
            "passenger_advisory": "Fallback advisory",
            "staff_instruction": "Fallback staff instruction",
            "operations_brief": "Fallback operations brief",
            "llm_mode": "Template fallback",
            "llm_status": "test",
            "llm_provider": "None",
            "guardrails": ["Rules decide"],
        },
    )
    monkeypatch.setattr(
        agent_engine,
        "generate_report_writer_outputs",
        lambda package: {
            "report_mode": "Template fallback",
            "report_provider": "None",
            "executive_summary": "Fallback summary",
            "lessons_learned": "Fallback lesson",
            "verified_metrics": {
                "severity": package["severity"],
                "score": f"{package['score']}/100",
            },
            "report_guardrails": ["Metrics verified"],
        },
    )
    monkeypatch.setattr(
        agent_engine,
        "generate_hybrid_agent_layer",
        lambda package: {
            "hybrid_mode": "Template fallback",
            "hybrid_provider": "None",
            "hybrid_summary": "Fallback hybrid layer",
            "agents": [{"agent": "Signal Agent"}],
            "guardrails": ["Rules are source of truth"],
        },
    )

    client = TestClient(app)
    payload = {
        "line": "Kelana Jaya Line",
        "issue_type": "Signal Disruption",
        "time_period": "Peak Hour",
        "delay_minutes": 30,
        "affected_stations": ["Ampang Park", "Dang Wangi", "Masjid Jamek", "Pasar Seni", "KL Sentral"],
        "weather_condition": "Heavy Rain",
    }

    response = client.post("/run-agent", json=payload)

    assert response.status_code == 200
    data = response.json()
    assert data["severity"] == "Critical"
    assert data["score"] == 100
    assert data["response_pathway"] == "Major Disruption Coordination"
    assert data["report_writer"]["verified_metrics"]["severity"] == "Critical"
    assert "hybrid_agent_layer" in data
    assert any(a["team"] == "Interchange Control Team" for a in data["actions"])
