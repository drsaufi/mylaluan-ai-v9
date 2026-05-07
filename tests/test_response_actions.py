from app.agent_engine import generate_response_actions


def test_critical_actions_include_interchange_supervisor_and_shuttle():
    actions = generate_response_actions(
        severity="Critical",
        affected_interchanges=["Masjid Jamek", "Pasar Seni", "KL Sentral"],
        delay_minutes=30,
    )

    teams = [a["team"] for a in actions]
    assert "Control Centre" in teams
    assert "Passenger Comms" in teams
    assert "Station Team" in teams
    assert "Interchange Control Team" in teams
    assert "Ops Supervisor" in teams
    assert "Bus / Shuttle" in teams
    assert len(actions) == 6


def test_medium_actions_do_not_trigger_supervisor_or_shuttle_for_short_delay():
    actions = generate_response_actions(
        severity="Medium",
        affected_interchanges=[],
        delay_minutes=10,
    )

    teams = [a["team"] for a in actions]
    assert "Station Team" in teams
    assert "Ops Supervisor" not in teams
    assert "Bus / Shuttle" not in teams
