from typing import Dict, List
from app.data_integrations import get_interchange_set, get_ridership_baseline, get_line_stations, get_integration_status
from app.llm_agent import generate_llm_outputs, generate_report_writer_outputs, generate_hybrid_agent_layer


def calculate_severity_score(line, time_period, delay_minutes, affected_stations, weather_condition):
    score = 0
    reasoning = []

    baseline = get_ridership_baseline(line)
    ridership_score = int(baseline.get("impact_score") or 8)
    score += ridership_score
    reasoning.append({
        "factor": "Official ridership baseline",
        "status": baseline.get("demand_level", "Unknown"),
        "impact": f"+{ridership_score}",
        "explanation": "Line demand baseline increases passenger-impact weighting.",
        "icon": "👥"
    })

    if time_period == "Peak Hour":
        score += 20
        reasoning.append({"factor": "Peak hour", "status": "Yes", "impact": "+20", "explanation": "More commuters are likely to be affected.", "icon": "⏱️"})
    else:
        reasoning.append({"factor": "Peak hour", "status": "No", "impact": "+0", "explanation": "Lower commuter load outside peak periods.", "icon": "⏱️"})

    affected_count = len(affected_stations)
    if affected_count >= 5:
        score += 20
        station_impact = "+20"
        station_explanation = "Wide service disruption across multiple stations."
    elif affected_count >= 3:
        score += 12
        station_impact = "+12"
        station_explanation = "Multiple stations require coordinated response."
    else:
        score += 5
        station_impact = "+5"
        station_explanation = "Limited station spread."
    reasoning.append({"factor": "Affected stations", "status": str(affected_count), "impact": station_impact, "explanation": station_explanation, "icon": "🚉"})

    interchange_set = get_interchange_set()
    affected_interchanges = [s for s in affected_stations if s in interchange_set]
    if len(affected_interchanges) >= 3:
        score += 15
        impact = "+15"
        explanation = "Multiple interchange points can cause network-wide knock-on effects."
    elif affected_interchanges:
        score += 10
        impact = "+10"
        explanation = "Interchange stations increase transfer and crowding risk."
    else:
        impact = "+0"
        explanation = "No interchange impact detected."
    reasoning.append({
        "factor": "Interchange stations among affected",
        "status": f"{len(affected_interchanges)} of {affected_count}" if affected_count else "0",
        "impact": impact,
        "explanation": explanation,
        "icon": "🔁"
    })

    if delay_minutes >= 30:
        score += 20
        delay_impact = "+20"
        delay_explanation = "Delay exceeds escalation threshold."
    elif delay_minutes >= 15:
        score += 15
        delay_impact = "+15"
        delay_explanation = "Delay requires proactive coordination."
    elif delay_minutes >= 5:
        score += 5
        delay_impact = "+5"
        delay_explanation = "Short disruption; continue monitoring."
    else:
        delay_impact = "+0"
        delay_explanation = "Delay remains within low-risk range."
    reasoning.append({"factor": "Delay duration", "status": f"{delay_minutes} minutes", "impact": delay_impact, "explanation": delay_explanation, "icon": "⌛"})

    if weather_condition in ["Heavy Rain", "Thunderstorm"]:
        score += 10
        weather_impact = "+10"
        weather_explanation = "Weather can slow shuttle movement and increase crowding risk."
    elif weather_condition == "Rain":
        score += 5
        weather_impact = "+5"
        weather_explanation = "Rain adds minor operational friction."
    else:
        weather_impact = "+0"
        weather_explanation = "Weather does not significantly increase response risk."
    reasoning.append({"factor": "Weather context", "status": weather_condition, "impact": weather_impact, "explanation": weather_explanation, "icon": "🌦️"})

    score = min(score, 100)
    if score >= 90:
        severity = "Critical"
    elif score >= 70:
        severity = "High"
    elif score >= 40:
        severity = "Medium"
    else:
        severity = "Low"

    return score, severity, reasoning, affected_interchanges, baseline


def get_response_pathway(severity):
    return {
        "Critical": "Major Disruption Coordination",
        "High": "High-Impact Passenger Response",
        "Medium": "Station-Level Coordination",
        "Low": "Monitor and Inform",
    }[severity]


def get_approval_state(severity):
    if severity == "Critical":
        return "Supervisor approval + escalation required"
    if severity == "High":
        return "Supervisor approval required"
    if severity == "Medium":
        return "Comms review required"
    return "Comms review recommended"


def generate_response_actions(severity, affected_interchanges, delay_minutes):
    actions = [
        {"team": "Control Centre", "icon": "🛰️", "action": "Incident created and affected segment placed under monitoring.", "status": "Active"},
        {"team": "Passenger Comms", "icon": "📣", "action": "Passenger advisory draft prepared from verified incident fields.", "status": "Review required" if severity in ["Low", "Medium"] else "Supervisor approval"},
    ]

    if severity in ["Medium", "High", "Critical"]:
        actions.append({"team": "Station Team", "icon": "🧭", "action": "Deploy station guidance support at affected platforms and concourse areas.", "status": "Recommended"})

    if affected_interchanges:
        if severity == "Low":
            wording = f"Monitor passenger movement at interchange station(s): {', '.join(affected_interchanges)}."
        else:
            wording = f"Prioritise passenger flow at interchange station(s): {', '.join(affected_interchanges)}."
        actions.append({"team": "Interchange Control Team", "icon": "🔁", "action": wording, "status": "Recommended"})

    if severity in ["High", "Critical"]:
        actions.append({"team": "Ops Supervisor", "icon": "🛡️", "action": "Review escalation pathway and approve operational response.", "status": "Approval required"})

    if severity == "Critical" or delay_minutes >= 30:
        actions.append({"team": "Bus / Shuttle", "icon": "🚌", "action": "Prepare shuttle support or alternative ground transport coordination.", "status": "Standby / Recommended"})
    return actions


def generate_advisory(line, issue_type, affected_stations, severity):
    station_text = ", ".join(affected_stations)
    if severity == "Critical":
        urgency = "Passengers are strongly advised to consider alternative routes and allow significant additional travel time."
    elif severity == "High":
        urgency = "Passengers are advised to consider alternative routes and allow additional travel time."
    elif severity == "Medium":
        urgency = "Passengers are advised to allow extra travel time and follow station staff guidance."
    else:
        urgency = "Passengers may experience minor delays. Please follow station announcements."
    return f"Service on the {line} is currently experiencing {issue_type.lower()} affecting {station_text}. {urgency} Further updates will be provided once confirmed by operations."


def generate_staff_instruction(severity, affected_stations, affected_interchanges):
    station_text = ", ".join(affected_stations)
    if severity in ["High", "Critical"]:
        instruction = f"Deploy additional staff to {station_text}. Prioritise passenger flow, platform monitoring and clear wayfinding support."
    elif severity == "Medium":
        instruction = f"Prepare staff guidance at {station_text}. Monitor crowding and update control centre if queue buildup appears."
    else:
        instruction = f"Monitor {station_text}. Update control centre if delay expands or crowding increases."
    if affected_interchanges:
        instruction += f" Interchange attention: {', '.join(affected_interchanges)}."
    return instruction


def build_agent_nodes(severity, line, issue_type, affected_stations, affected_interchanges, response_pathway):
    return [
        {"name": "Signal Agent", "icon": "📡", "status": "Complete", "summary": f"{issue_type} captured on {line}"},
        {"name": "Impact Agent", "icon": "🚉", "status": "Complete", "summary": f"{len(affected_stations)} stations · {len(affected_interchanges)} interchanges"},
        {"name": "Decision Agent", "icon": "🧠", "status": severity, "summary": f"{severity} · {response_pathway}"},
        {"name": "Comms Agent", "icon": "📣", "status": "Drafted", "summary": "Passenger message prepared"},
        {"name": "Report Writer Agent", "icon": "📝", "status": "Prepared", "summary": "Post-incident report generated"},
        {"name": "Escalation Agent", "icon": "🛡️", "status": "Active" if severity in ["High", "Critical"] else "Monitor", "summary": get_approval_state(severity)},
    ]


def get_route_options(line, severity, affected_interchanges):
    if line == "Kelana Jaya Line":
        if severity in ["High", "Critical"]:
            return [
                {"label": "Use MRT Kajang / Putrajaya via Pasar Seni or Ampang Park where available", "status": "Alternative available"},
                {"label": "Prepare shuttle standby if disruption exceeds 30 minutes", "status": "Standby" if severity == "High" else "Recommended"},
            ]
    return [{"label": "Follow station guidance and official journey planner", "status": "Monitor"}]


def run_mylaluan_agent(line, issue_type, time_period, delay_minutes, affected_stations, weather_condition):
    score, severity, reasoning, affected_interchanges, baseline = calculate_severity_score(
        line, time_period, delay_minutes, affected_stations, weather_condition
    )
    response_pathway = get_response_pathway(severity)
    actions = generate_response_actions(severity, affected_interchanges, delay_minutes)
    line_stations = get_line_stations(line)
    route_options = get_route_options(line, severity, affected_interchanges)
    approval_state = get_approval_state(severity)
    integration_status = get_integration_status()

    decision_package = {
        "line": line,
        "issue_type": issue_type,
        "time_period": time_period,
        "delay_minutes": delay_minutes,
        "affected_stations": affected_stations,
        "affected_interchanges": affected_interchanges,
        "weather_condition": weather_condition,
        "score": score,
        "severity": severity,
        "response_pathway": response_pathway,
        "approval_state": approval_state,
        "route_options": route_options,
        "actions": actions,
        "ridership_baseline": baseline,
    }

    llm_outputs = generate_llm_outputs(decision_package)
    report_outputs = generate_report_writer_outputs(decision_package)
    hybrid_agent_layer = generate_hybrid_agent_layer(decision_package)
    advisory = llm_outputs["passenger_advisory"]
    staff_instruction = llm_outputs["staff_instruction"]
    operations_brief = llm_outputs["operations_brief"]

    agent_nodes = build_agent_nodes(severity, line, issue_type, affected_stations, affected_interchanges, response_pathway)
    # Make the LLM component visible in the agent workflow.
    for node in agent_nodes:
        if node.get("name") == "Comms Agent":
            node["status"] = "LLM" if llm_outputs.get("llm_mode") == "LLM active" else "Fallback"
            node["summary"] = "LLM-generated comms" if llm_outputs.get("llm_mode") == "LLM active" else "Template fallback comms"
        if node.get("name") == "Report Writer Agent":
            node["status"] = "LLM" if report_outputs.get("report_mode") == "LLM active" else "Fallback"
            node["summary"] = "Executive report generated" if report_outputs.get("report_mode") == "LLM active" else "Template report generated"

    impact_summary = [
        {"label": "Stations affected", "value": len(affected_stations), "hint": "Mapped from selected incident segment"},
        {"label": "Interchanges impacted", "value": f"{len(affected_interchanges)} of {len(affected_stations)}", "hint": "Transfer-risk hotspots"},
        {"label": "Demand level", "value": baseline.get("demand_level", "Unknown"), "hint": "Official/open-data baseline"},
        {"label": "Actions generated", "value": len(actions), "hint": "Coordination tasks created"},
    ]

    decision_timeline = [
        {"step": "Detect", "decision": f"{issue_type} detected on {line}.", "action": "Incident case created."},
        {"step": "Diagnose", "decision": f"{len(affected_stations)} affected station(s), {len(affected_interchanges)} interchange station(s), {delay_minutes}-minute delay.", "action": f"Severity score calculated: {score}/100."},
        {"step": "Decide", "decision": f"Response pathway selected: {response_pathway}.", "action": "Operational tasks generated for relevant teams."},
        {"step": "Act", "decision": "Advisory, staff instruction and escalation route prepared.", "action": approval_state},
        {"step": "Monitor", "decision": "Agent will reassess if delay, weather or affected stations change.", "action": "Use Simulate Situation Worsens to demonstrate adaptation."},
    ]

    return {
        "severity": severity,
        "score": score,
        "response_pathway": response_pathway,
        "reasoning": reasoning,
        "actions": actions,
        "advisory": advisory,
        "staff_instruction": staff_instruction,
        "operations_brief": operations_brief,
        "llm_mode": llm_outputs.get("llm_mode"),
        "llm_status": llm_outputs.get("llm_status"),
        "llm_provider": llm_outputs.get("llm_provider"),
        "llm_guardrails": llm_outputs.get("guardrails", []),
        "decision_timeline": decision_timeline,
        "affected_interchanges": affected_interchanges,
        "affected_stations": affected_stations,
        "ridership_baseline": baseline,
        "approval_state": approval_state,
        "agent_nodes": agent_nodes,
        "line_stations": line_stations,
        "route_options": route_options,
        "impact_summary": impact_summary,
        "integration_status": integration_status,
        "report_writer": report_outputs,
        "hybrid_agent_layer": hybrid_agent_layer,
    }
