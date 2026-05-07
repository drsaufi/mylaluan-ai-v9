from app.llm_agent import generate_llm_outputs, generate_report_writer_outputs, generate_hybrid_agent_layer, check_llm_health


def decision_package():
    return {
        "line": "Kelana Jaya Line",
        "issue_type": "Signal Disruption",
        "time_period": "Peak Hour",
        "delay_minutes": 30,
        "weather_condition": "Heavy Rain",
        "affected_stations": ["Ampang Park", "Masjid Jamek", "Pasar Seni", "KL Sentral"],
        "affected_interchanges": ["Ampang Park", "Masjid Jamek", "Pasar Seni", "KL Sentral"],
        "severity": "Critical",
        "score": 100,
        "response_pathway": "Major Disruption Coordination",
        "approval_state": "Supervisor approval + escalation required",
        "route_options": [],
        "actions": [
            {"team": "Control Centre", "action": "Incident created", "status": "Active"},
            {"team": "Passenger Comms", "action": "Draft advisory", "status": "Supervisor approval"},
        ],
        "ridership_baseline": {"demand_level": "High"},
    }


def test_comms_llm_fallback_when_no_client(monkeypatch):
    monkeypatch.setattr("app.llm_agent._get_langchain_client", lambda: (None, "no key"))

    output = generate_llm_outputs(decision_package())

    assert output["llm_mode"] == "Template fallback"
    assert output["llm_provider"] == "None"
    assert "passenger_advisory" in output
    assert "Severity and escalation" in " ".join(output["guardrails"])


def test_report_writer_fallback_returns_verified_metrics(monkeypatch):
    monkeypatch.setattr("app.llm_agent._get_langchain_client", lambda: (None, "no key"))

    output = generate_report_writer_outputs(decision_package())

    assert output["report_mode"] == "Template fallback"
    assert output["verified_metrics"]["severity"] == "Critical"
    assert output["verified_metrics"]["score"] == "100/100"
    assert "proxy" in " ".join(output["report_guardrails"]).lower()


def test_hybrid_agent_layer_fallback_includes_all_agents(monkeypatch):
    monkeypatch.setattr("app.llm_agent._get_langchain_client", lambda: (None, "no key"))

    output = generate_hybrid_agent_layer(decision_package())

    assert output["hybrid_mode"] == "Template fallback"
    agent_names = [a["agent"] for a in output["agents"]]
    assert "Signal Agent" in agent_names
    assert "Impact Agent" in agent_names
    assert "Decision Agent" in agent_names
    assert "Report Writer Agent" in agent_names


def test_llm_health_direct_fallback(monkeypatch):
    monkeypatch.setattr("app.llm_agent._get_langchain_client", lambda: (None, "no key"))

    output = check_llm_health()

    assert output["llm_ready"] is False
    assert output["mode"] == "Template fallback"
    assert output["model"] == "gpt-5.4-mini"
