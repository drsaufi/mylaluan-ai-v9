"""LLM-powered communication layer for MyLaluan AI.

The LLM is intentionally NOT used for safety-critical scoring. The rules engine
calculates severity and response pathway first. This module only turns the
verified decision package into clearer passenger, staff, and operations text.
If no API key is available or the LLM request fails, the app falls back to
safe deterministic templates so the demo remains reliable.
"""
from __future__ import annotations

import json
import os
from typing import Dict, List, Any


def _fallback_advisory(line: str, issue_type: str, affected_stations: List[str], severity: str) -> str:
    station_text = ", ".join(affected_stations)
    if severity == "Critical":
        urgency = "Passengers are strongly advised to consider alternative routes and allow significant additional travel time."
    elif severity == "High":
        urgency = "Passengers are advised to consider alternative routes and allow additional travel time."
    elif severity == "Medium":
        urgency = "Passengers are advised to allow extra travel time and follow station staff guidance."
    else:
        urgency = "Passengers may experience minor delays. Please follow station announcements."
    return (
        f"Service on the {line} is currently experiencing {issue_type.lower()} affecting {station_text}. "
        f"{urgency} Further updates will be provided once confirmed by operations."
    )


def _fallback_staff_instruction(severity: str, affected_stations: List[str], affected_interchanges: List[str]) -> str:
    station_text = ", ".join(affected_stations)
    if severity in ["High", "Critical"]:
        instruction = (
            f"Deploy additional staff to {station_text}. Prioritise passenger flow, platform monitoring, "
            "and clear wayfinding support."
        )
    elif severity == "Medium":
        instruction = f"Prepare staff guidance at {station_text}. Monitor crowding and update control centre if queue buildup appears."
    else:
        instruction = f"Monitor {station_text}. Update control centre if delay expands or crowding increases."
    if affected_interchanges:
        instruction += f" Interchange attention: {', '.join(affected_interchanges)}."
    return instruction


def _fallback_operations_brief(decision_package: Dict[str, Any]) -> str:
    return (
        f"{decision_package['severity']} disruption response selected for {decision_package['line']}. "
        f"The agent assessed {len(decision_package['affected_stations'])} affected station(s), "
        f"{len(decision_package['affected_interchanges'])} interchange point(s), "
        f"{decision_package['delay_minutes']}-minute delay, and {decision_package['weather_condition']} weather context. "
        f"Response pathway: {decision_package['response_pathway']}."
    )


def _fallback_response(decision_package: Dict[str, Any], reason: str = "Template fallback active") -> Dict[str, Any]:
    return {
        "passenger_advisory": _fallback_advisory(
            decision_package["line"],
            decision_package["issue_type"],
            decision_package["affected_stations"],
            decision_package["severity"],
        ),
        "staff_instruction": _fallback_staff_instruction(
            decision_package["severity"],
            decision_package["affected_stations"],
            decision_package["affected_interchanges"],
        ),
        "operations_brief": _fallback_operations_brief(decision_package),
        "llm_mode": "Template fallback",
        "llm_status": reason,
        "llm_provider": "None",
        "guardrails": [
            "Severity and escalation are determined by the rules engine, not the LLM.",
            "LLM output is grounded only on verified incident fields.",
            "Public-facing messages remain subject to human review or supervisor approval.",
        ],
    }


def _get_langchain_client():
    """Return a LangChain chat client if an OpenAI API key is available."""
    # Load .env if python-dotenv is installed. Failure is safe.
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except Exception:
        pass

    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None, "OPENAI_API_KEY not found"

    try:
        from langchain_openai import ChatOpenAI
        model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
        client = ChatOpenAI(
            model=model,
            temperature=0.2,
            max_retries=0,
            request_timeout=12,
        )
        return client, f"LangChain + OpenAI connected ({model})"
    except Exception as exc:
        return None, f"LangChain client unavailable: {exc}"



def check_llm_health() -> Dict[str, Any]:
    """Lightweight LLM connectivity check for the UI.

    This is intentionally separated from the operational agent run so the team
    can test API readiness before the demo. It never affects severity scoring
    or task routing.
    """
    client, status = _get_langchain_client()
    configured_model = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")

    if client is None:
        return {
            "llm_ready": False,
            "mode": "Template fallback",
            "provider": "None",
            "model": configured_model,
            "status": status,
            "message": "OPENAI_API_KEY is not available or LangChain client could not be created. Demo will use template fallback.",
        }

    try:
        response = client.invoke(
            "Return only this exact JSON: {\"status\":\"ok\",\"message\":\"LLM health check passed\"}"
        )
        content = getattr(response, "content", str(response)).strip()
        return {
            "llm_ready": True,
            "mode": "LLM active",
            "provider": "LangChain + OpenAI",
            "model": configured_model,
            "status": status,
            "message": f"LLM health check completed. Response preview: {content[:120]}",
        }
    except Exception as exc:
        return {
            "llm_ready": False,
            "mode": "Template fallback",
            "provider": "LangChain + OpenAI",
            "model": configured_model,
            "status": f"LLM test call failed: {exc}",
            "message": "API key was found, but the test call failed. Demo will remain safe using template fallback.",
        }

def generate_llm_outputs(decision_package: Dict[str, Any]) -> Dict[str, Any]:
    """Generate comms outputs using LangChain LLM, with deterministic fallback."""
    client, status = _get_langchain_client()
    if client is None:
        return _fallback_response(decision_package, status)

    compact_actions = [
        {"team": a.get("team"), "action": a.get("action"), "status": a.get("status")}
        for a in decision_package.get("actions", [])
    ]
    prompt = f"""
You are the LLM-powered Comms Agent inside MyLaluan AI, an agentic MRT/LRT disruption response coordinator.

IMPORTANT GUARDRAILS:
- Do not change severity, score, response pathway, affected stations, delay duration, or approval state.
- Do not invent causes, recovery time, official confirmation, safety instructions, or unavailable alternative routes.
- Use only the verified decision package below.
- Keep passenger message concise, clear, and suitable for public review.
- Keep staff instruction operational and concise.
- Return ONLY valid JSON with these keys:
  passenger_advisory, staff_instruction, operations_brief

Verified decision package:
{json.dumps({
    'line': decision_package['line'],
    'issue_type': decision_package['issue_type'],
    'time_period': decision_package['time_period'],
    'delay_minutes': decision_package['delay_minutes'],
    'weather_condition': decision_package['weather_condition'],
    'affected_stations': decision_package['affected_stations'],
    'affected_interchanges': decision_package['affected_interchanges'],
    'severity': decision_package['severity'],
    'score': decision_package['score'],
    'response_pathway': decision_package['response_pathway'],
    'approval_state': decision_package['approval_state'],
    'route_options': decision_package.get('route_options', []),
    'actions': compact_actions,
}, ensure_ascii=False)}
""".strip()

    try:
        response = client.invoke(prompt)
        content = getattr(response, "content", str(response)).strip()
        # Some models wrap JSON in code fences. Strip them safely.
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()
        parsed = json.loads(content)
        return {
            "passenger_advisory": parsed.get("passenger_advisory") or _fallback_advisory(
                decision_package["line"], decision_package["issue_type"], decision_package["affected_stations"], decision_package["severity"]
            ),
            "staff_instruction": parsed.get("staff_instruction") or _fallback_staff_instruction(
                decision_package["severity"], decision_package["affected_stations"], decision_package["affected_interchanges"]
            ),
            "operations_brief": parsed.get("operations_brief") or _fallback_operations_brief(decision_package),
            "llm_mode": "LLM active",
            "llm_status": status,
            "llm_provider": "LangChain + OpenAI",
            "guardrails": [
                "Rules engine controls severity and escalation.",
                "LLM is restricted to grounded communication and briefing outputs.",
                "Human approval remains required for public-facing or safety-sensitive actions.",
            ],
        }
    except Exception as exc:
        return _fallback_response(decision_package, f"LLM failed, fallback used: {exc}")


def _fallback_report_writer(decision_package: Dict[str, Any]) -> Dict[str, Any]:
    actions = decision_package.get("actions", [])
    teams = sorted({a.get("team", "Unknown") for a in actions})
    affected = decision_package.get("affected_stations", [])
    interchanges = decision_package.get("affected_interchanges", [])
    severity = decision_package.get("severity", "Unknown")
    pathway = decision_package.get("response_pathway", "Unknown")
    line = decision_package.get("line", "selected line")
    issue = decision_package.get("issue_type", "disruption").lower()

    summary = (
        f"Post-incident report generated for a {severity.lower()} {issue} on the {line}. "
        f"The incident affected {len(affected)} station(s), including {len(interchanges)} interchange point(s), "
        f"and triggered the {pathway} pathway with {len(actions)} coordination task(s). "
        f"The report is based on verified system outputs and uses passenger-impact proxy inputs rather than exact live passenger counts."
    )

    if severity in ["High", "Critical"]:
        lessons = (
            "Key learning: interchange-heavy and peak-hour disruptions should trigger early crowd-flow separation, "
            "clear passenger guidance, and supervisor review. Future improvement can connect the Impact Agent to live AFC, "
            "tap-in/tap-out, or crowd-sensor feeds for more precise passenger impact estimation."
        )
    else:
        lessons = (
            "Key learning: lower-severity disruptions can be managed through monitoring, targeted passenger guidance, "
            "and readiness to escalate if delay duration or affected station coverage expands."
        )

    return {
        "report_mode": "Template fallback",
        "report_provider": "None",
        "executive_summary": summary,
        "lessons_learned": lessons,
        "verified_metrics": {
            "severity": severity,
            "score": f"{decision_package.get('score', '-')}/100",
            "response_pathway": pathway,
            "affected_stations": str(len(affected)),
            "interchanges": str(len(interchanges)),
            "actions_generated": str(len(actions)),
            "teams_involved": str(len(teams)),
            "approval_state": decision_package.get("approval_state", "Review required"),
            "passenger_impact": decision_package.get("ridership_baseline", {}).get("demand_level", "Baseline proxy"),
        },
        "report_guardrails": [
            "Report metrics are generated from verified system outputs.",
            "LLM/report writer does not change severity, score, escalation, or action routing.",
            "Passenger impact is a proxy in this MVP, not exact live station passenger count.",
        ],
    }


def generate_report_writer_outputs(decision_package: Dict[str, Any]) -> Dict[str, Any]:
    """Generate a post-incident report narrative using LLM, with deterministic fallback.

    The factual report metrics remain deterministic and are not authored by the LLM.
    The LLM only writes executive summary and lessons learned from verified system outputs.
    """
    fallback = _fallback_report_writer(decision_package)
    client, status = _get_langchain_client()
    if client is None:
        fallback["report_provider"] = "None"
        return fallback

    compact_actions = [
        {"team": a.get("team"), "action": a.get("action"), "status": a.get("status")}
        for a in decision_package.get("actions", [])
    ]

    prompt = f"""
You are the Report Writer Agent inside MyLaluan AI.

TASK:
Generate a concise post-incident management report summary and lessons learned.

IMPORTANT GUARDRAILS:
- Do not alter or invent metrics.
- Do not claim exact live passenger counts.
- Say passenger impact is estimated using a proxy when relevant.
- Do not invent recovery times, root cause confirmation, or official statements.
- Return ONLY valid JSON with keys:
  executive_summary, lessons_learned

Verified incident data:
{json.dumps({
    'line': decision_package.get('line'),
    'issue_type': decision_package.get('issue_type'),
    'time_period': decision_package.get('time_period'),
    'delay_minutes': decision_package.get('delay_minutes'),
    'weather_condition': decision_package.get('weather_condition'),
    'affected_stations': decision_package.get('affected_stations'),
    'affected_interchanges': decision_package.get('affected_interchanges'),
    'severity': decision_package.get('severity'),
    'score': decision_package.get('score'),
    'response_pathway': decision_package.get('response_pathway'),
    'approval_state': decision_package.get('approval_state'),
    'ridership_baseline': decision_package.get('ridership_baseline'),
    'actions': compact_actions,
}, ensure_ascii=False)}
""".strip()

    try:
        response = client.invoke(prompt)
        content = getattr(response, "content", str(response)).strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()
        parsed = json.loads(content)
        fallback["executive_summary"] = parsed.get("executive_summary") or fallback["executive_summary"]
        fallback["lessons_learned"] = parsed.get("lessons_learned") or fallback["lessons_learned"]
        fallback["report_mode"] = "LLM active"
        fallback["report_provider"] = "LangChain + OpenAI"
        return fallback
    except Exception as exc:
        fallback["report_mode"] = "Template fallback"
        fallback["report_provider"] = f"LLM failed, fallback used"
        fallback["report_guardrails"].append(f"Fallback reason: {exc}")
        return fallback


def _fallback_hybrid_agent_layer(decision_package: Dict[str, Any]) -> Dict[str, Any]:
    """Deterministic hybrid-role explanation for each agent."""
    severity = decision_package.get("severity", "Unknown")
    score = decision_package.get("score", "-")
    line = decision_package.get("line", "selected line")
    issue = decision_package.get("issue_type", "incident")
    affected = decision_package.get("affected_stations", [])
    interchanges = decision_package.get("affected_interchanges", [])
    actions = decision_package.get("actions", [])
    pathway = decision_package.get("response_pathway", "response pathway")
    approval = decision_package.get("approval_state", "review required")
    demand = decision_package.get("ridership_baseline", {}).get("demand_level", "baseline")

    agents = [
        {
            "agent": "Signal Agent",
            "rules_role": "Validates line, issue type, delay, weather and selected stations.",
            "llm_role": "Can extract incident fields from unstructured operator notes in production.",
            "hybrid_output": f"{issue} captured on {line}. Structured inputs remain the source of truth.",
            "mode": "Rules + LLM extraction-ready",
        },
        {
            "agent": "Impact Agent",
            "rules_role": "Scores impact using ridership baseline, peak/non-peak, affected stations, interchange count, delay and weather.",
            "llm_role": "Explains passenger-impact drivers in operator-friendly language.",
            "hybrid_output": f"{len(affected)} station(s), {len(interchanges)} interchange(s), {demand} demand baseline.",
            "mode": "Rules scoring + LLM explanation",
        },
        {
            "agent": "Decision Agent",
            "rules_role": "Selects severity, score and response pathway deterministically.",
            "llm_role": "Provides a rationale for why the selected pathway is operationally appropriate.",
            "hybrid_output": f"{severity} selected with score {score}/100. Pathway: {pathway}.",
            "mode": "Rules decision + LLM rationale",
        },
        {
            "agent": "Coordination Agent",
            "rules_role": "Routes tasks to relevant teams based on severity, delay and interchange impact.",
            "llm_role": "Refines task wording so each team receives clearer operational instructions.",
            "hybrid_output": f"{len(actions)} team task(s) generated from verified incident fields.",
            "mode": "Rules routing + LLM task wording",
        },
        {
            "agent": "Comms Agent",
            "rules_role": "Uses only verified incident fields and approval state.",
            "llm_role": "Drafts passenger, station staff and operations messages with template fallback.",
            "hybrid_output": "Communication drafted without changing score, severity or escalation.",
            "mode": "LLM drafting + fallback",
        },
        {
            "agent": "Escalation Agent",
            "rules_role": "Determines approval requirement from severity and public-facing action risk.",
            "llm_role": "Summarises escalation rationale for supervisor review.",
            "hybrid_output": approval,
            "mode": "Rules approval + LLM rationale",
        },
        {
            "agent": "Report Writer Agent",
            "rules_role": "Compiles verified metrics from system outputs.",
            "llm_role": "Writes executive summary and lessons learned with deterministic fallback.",
            "hybrid_output": "Post-incident reporting prepared for audit and management review.",
            "mode": "Metrics + LLM summary",
        },
    ]

    return {
        "hybrid_mode": "Template fallback",
        "hybrid_provider": "None",
        "hybrid_summary": "Every agent is hybrid-assisted, but safety-critical outputs remain deterministic. LLM support is limited to extraction, explanation, wording, rationale and reporting.",
        "agents": agents,
        "guardrails": [
            "Rules and verified data remain the source of truth.",
            "LLM cannot change severity, score, affected stations, escalation state or task routing.",
            "Fallback templates keep the demo reliable if no API key is available.",
        ],
    }


def generate_hybrid_agent_layer(decision_package: Dict[str, Any]) -> Dict[str, Any]:
    """Generate hybrid-agent explanations using LLM when available.

    This does not let the LLM control safety-critical logic. It only explains
    each agent's rules role, LLM role, and grounded output.
    """
    fallback = _fallback_hybrid_agent_layer(decision_package)
    client, status = _get_langchain_client()
    if client is None:
        return fallback

    compact_actions = [
        {"team": a.get("team"), "action": a.get("action"), "status": a.get("status")}
        for a in decision_package.get("actions", [])
    ]

    prompt = f"""
You are explaining MyLaluan AI's hybrid multi-agent architecture for hackathon judges.

TASK:
Create concise hybrid role explanations for these agents:
Signal Agent, Impact Agent, Decision Agent, Coordination Agent, Comms Agent, Escalation Agent, Report Writer Agent.

IMPORTANT GUARDRAILS:
- Do not claim exact live passenger counts.
- Do not claim LLM changes severity, score, affected stations, escalation or task routing.
- Make it clear rules/data are source of truth for safety-critical decisions.
- Keep each agent output concise.
- Return ONLY valid JSON with keys:
  hybrid_summary,
  agents
Where agents is a list of objects with:
  agent, rules_role, llm_role, hybrid_output, mode

Verified incident package:
{json.dumps({
    'line': decision_package.get('line'),
    'issue_type': decision_package.get('issue_type'),
    'time_period': decision_package.get('time_period'),
    'delay_minutes': decision_package.get('delay_minutes'),
    'weather_condition': decision_package.get('weather_condition'),
    'affected_stations': decision_package.get('affected_stations'),
    'affected_interchanges': decision_package.get('affected_interchanges'),
    'severity': decision_package.get('severity'),
    'score': decision_package.get('score'),
    'response_pathway': decision_package.get('response_pathway'),
    'approval_state': decision_package.get('approval_state'),
    'ridership_baseline': decision_package.get('ridership_baseline'),
    'actions': compact_actions,
}, ensure_ascii=False)}
""".strip()

    try:
        response = client.invoke(prompt)
        content = getattr(response, "content", str(response)).strip()
        if content.startswith("```"):
            content = content.strip("`")
            if content.lower().startswith("json"):
                content = content[4:].strip()
        parsed = json.loads(content)
        agents = parsed.get("agents")
        if not isinstance(agents, list) or len(agents) < 4:
            raise ValueError("Hybrid agent list missing or incomplete")

        fallback["hybrid_mode"] = "LLM active"
        fallback["hybrid_provider"] = "LangChain + OpenAI"
        fallback["hybrid_summary"] = parsed.get("hybrid_summary") or fallback["hybrid_summary"]
        fallback["agents"] = agents
        return fallback
    except Exception as exc:
        fallback["guardrails"].append(f"Fallback reason: {exc}")
        return fallback
