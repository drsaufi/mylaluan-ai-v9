import logging
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, field_validator
from typing import List
from app.agent_engine import run_mylaluan_agent
from app.llm_agent import check_llm_health

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s — %(message)s")
logger = logging.getLogger("mylaluan")

app = FastAPI(title="MyLaluan AI V8")
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

VALID_LINES = [
    "Kelana Jaya Line",
    "MRT Kajang Line",
    "MRT Putrajaya Line",
    "Ampang Line",
    "Sri Petaling Line",
    "Monorail Line",
]

class DisruptionInput(BaseModel):
    line: str
    issue_type: str
    time_period: str
    delay_minutes: int
    affected_stations: List[str]
    weather_condition: str

    @field_validator("delay_minutes")
    @classmethod
    def validate_delay(cls, v):
        if not (1 <= v <= 480):
            raise ValueError("Delay must be between 1 and 480 minutes")
        return v

    @field_validator("affected_stations")
    @classmethod
    def validate_stations(cls, v):
        if len(v) == 0:
            raise ValueError("At least one affected station is required")
        if len(v) > 50:
            raise ValueError("Too many stations selected (max 50)")
        return v

    @field_validator("line")
    @classmethod
    def validate_line(cls, v):
        if v not in VALID_LINES:
            raise ValueError(f"Unknown line: {v}")
        return v


@app.get("/")
def home(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.post("/run-agent")
def run_agent(data: DisruptionInput):
    try:
        logger.info(
            "Agent run | line=%s | issue=%s | stations=%d | delay=%dmin",
            data.line, data.issue_type, len(data.affected_stations), data.delay_minutes,
        )
        return run_mylaluan_agent(
            line=data.line,
            issue_type=data.issue_type,
            time_period=data.time_period,
            delay_minutes=data.delay_minutes,
            affected_stations=data.affected_stations,
            weather_condition=data.weather_condition,
        )
    except Exception as e:
        logger.error("Agent run failed: %s", e)
        return JSONResponse(
            status_code=500,
            content={"error": "Agent run failed", "detail": str(e)},
        )


@app.get("/llm-health")
def llm_health():
    return check_llm_health()
