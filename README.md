# MyLaluan AI V8 — Product UX Polish

V8 focuses on a champion-level presentation experience, not new backend complexity.

## What improved in V8

- Answer-first incident summary at the top.
- Cleaner product-style layout with reduced text density.
- Focused rail corridor visual using expanded Klang Valley station reference.
- Visual 5-agent orchestration pipeline.
- Team task board with action status cards.
- Execution log to show end-to-end coordination.
- Advisory, staff instruction and Comms Agent outputs separated clearly.
- Explainability, data coverage and integration status moved into collapsible sections.
- Hybrid architecture retained: rules decide, LLM drafts, human approves.

## How to run

```cmd
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open:

```text
http://127.0.0.1:8000
```

## Demo flow

1. Click **Load Final Demo Scenario**.
2. Click **Run MyLaluan Agent**.
3. Show rail corridor, agent flow, task board and outputs.
4. Click **Simulate Situation Worsens**.
5. Show High/Critical escalation and updated coordination actions.

## Safe pitch wording

MyLaluan AI is a hybrid agentic disruption-response coordinator. Rules-based agents handle operational decisions such as impact analysis, severity, escalation and shuttle recommendation. The LLM-powered Comms Agent drafts grounded passenger advisories, staff instructions and operations briefs. If no API key is configured, approved template fallback keeps the demo stable.

## LLM setup

Copy `.env.example` to `.env` and add your key:

```text
OPENAI_API_KEY=your_key_here
OPENAI_MODEL=gpt-4o-mini
```

Without an API key, the system remains functional in Template fallback mode.

## V8.1 Network Visual Upgrade

This version upgrades the rail visual from a straight corridor into a schematic operational network view:

- Main affected line remains readable as the central corridor.
- Interchange branches show alternative/connected services such as MRT Kajang, MRT Putrajaya, Monorail, KTM/ERL, and Ampang/Sri Petaling.
- Affected stations, transfer nodes, and operating segment are highlighted with a clear legend.
- The map is intentionally schematic, not geographically exact. It is designed for disruption response clarity, similar to how transit maps simplify geography for operational understanding.

Recommended pitch wording:

> The map is a focused operational schematic, not a full geographic map. It highlights the affected rail corridor and relevant interchange branches so operators can quickly see where the disruption is, which transfer points are impacted, and which alternative routes may remain available.


## V8.2 Layout Architecture Redesign

This version restructures the interface into paired operational workspaces:

1. Network map + incident insight panel
2. Agent orchestration + team task board
3. Comms output + execution / hybrid AI panels
4. Collapsible explainability and data-source details

The goal is to reduce dead space, lower cognitive load, and make the MVP feel more like a client-ready rail operations product instead of a word-heavy dashboard.

## V8.7 space balance patch
This version moves the Live/Open-Data Readiness panel into the right-hand operational stack under the Hybrid AI Layer. This fills the previous empty right-side area and fixes integration cards that displayed `undefined` labels by mapping the backend fields `label`, `status`, `detail`, and `source` correctly.


## V8.8 Gap Fill Patch
Adds a compact Response Runbook into the left content stack to remove remaining blank canvas while keeping the layout meaningful and demo-focused.


## V8.10 note
Restored the Network Coverage section to a more readable two-column card layout while keeping the V8.9 enlarged rail visual.


## V8.23 Technical Hardening Pack

This version adds automated test coverage so the team can defend the prototype more confidently during technical Q&A.

### What was added

- `tests/` directory
- `pytest.ini`
- Severity scoring tests
- Response action routing tests
- LLM fallback tests
- Report Writer fallback tests
- Hybrid Agent Layer fallback tests
- FastAPI `/run-agent` endpoint test
- `pytest` and `httpx` added to `requirements.txt`

### How to run tests

```cmd
python -m pip install -r requirements.txt
python -m pytest
```

### What the tests prove

- Critical scenarios escalate correctly.
- Low scenarios remain monitor-and-inform.
- Interchange-heavy incidents trigger Interchange Control Team.
- LLM fallback works if no API key is available.
- Report Writer Agent returns verified metrics.
- Hybrid Agent Layer still renders safely in fallback mode.
- `/run-agent` returns a complete payload without relying on live API calls.

### Safe pitch wording

> V8.23 adds automated testing for the safety-critical parts of the prototype. The tests prove that severity scoring, action routing, LLM fallback, reporting fallback, and the API endpoint continue to work even when live LLM or external API calls are unavailable.


## V8.24 Real LLM API Integration

This version adds a real LLM API readiness check while keeping the fallback-safe architecture.

### What changed

- Added `/llm-health` endpoint.
- Added **LLM API readiness check** panel in the UI.
- Default model changed to `gpt-5.4-mini`.
- `.env.example` updated with clear setup instructions.
- The app still works if the API key is missing, invalid, or quota is unavailable.

### How to enable real LLM mode

1. Copy `.env.example`
2. Rename the copy to `.env`
3. Add your API key:

```text
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.4-mini
```

4. Restart the app:

```cmd
python -m uvicorn main:app --reload
```

5. Open the app and click **Check LLM API**.

### Expected result

If the API key works, the UI should show:

```text
LLM active
Provider: LangChain + OpenAI
Model: gpt-5.4-mini
```

If the API key fails, the UI should show:

```text
Template fallback
```

This is safe because severity, scoring, action routing and escalation remain rules-based.

### Demo pitch line

> MyLaluan AI can run with real LLM support for communication, explanation and reporting. If the API fails, the system automatically falls back to deterministic templates, while the rules engine continues to control severity, scoring and escalation.
