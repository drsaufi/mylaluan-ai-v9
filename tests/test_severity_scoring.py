from app.agent_engine import calculate_severity_score, get_response_pathway, get_approval_state


def test_critical_scenario_scores_and_escalates():
    score, severity, reasoning, interchanges, baseline = calculate_severity_score(
        line="Kelana Jaya Line",
        time_period="Peak Hour",
        delay_minutes=30,
        affected_stations=["Ampang Park", "Dang Wangi", "Masjid Jamek", "Pasar Seni", "KL Sentral"],
        weather_condition="Heavy Rain",
    )

    assert score == 100
    assert severity == "Critical"
    assert get_response_pathway(severity) == "Major Disruption Coordination"
    assert get_approval_state(severity) == "Supervisor approval + escalation required"
    assert set(interchanges) == {"Ampang Park", "Masjid Jamek", "Pasar Seni", "KL Sentral"}
    assert baseline["demand_level"] == "High"
    assert len(reasoning) >= 6


def test_low_scenario_remains_monitor_and_inform():
    score, severity, reasoning, interchanges, baseline = calculate_severity_score(
        line="Monorail Line",
        time_period="Non-Peak Hour",
        delay_minutes=2,
        affected_stations=["Bukit Bintang"],
        weather_condition="Clear",
    )

    assert score < 40
    assert severity == "Low"
    assert get_response_pathway(severity) == "Monitor and Inform"
    assert get_approval_state(severity) == "Comms review recommended"
    assert interchanges == ["Bukit Bintang"]
