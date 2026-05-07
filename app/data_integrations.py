import csv
from pathlib import Path
from typing import Dict, List
import requests

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
RIDERSHIP_CSV_URL = "https://storage.data.gov.my/transportation/ridership_headline.csv"
WEATHER_WARNING_URL = "https://api.data.gov.my/weather/warning?limit=50"
WEATHER_FORECAST_URL = "https://api.data.gov.my/weather/forecast?limit=3"


def read_csv_dicts(filename: str) -> List[Dict[str, str]]:
    path = DATA_DIR / filename
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def get_stations() -> List[Dict[str, str]]:
    rows = read_csv_dicts("stations.csv")
    return sorted(rows, key=lambda r: (r.get("line", ""), int(r.get("order") or 0)))


def get_line_stations(line: str) -> List[Dict[str, str]]:
    rows = get_stations()
    filtered = [r for r in rows if r.get("line") == line]
    return sorted(filtered, key=lambda r: int(r.get("order") or 0))


def get_interchange_set() -> set:
    return {r["station"] for r in get_stations() if r.get("is_interchange", "").lower() == "yes"}


def get_ridership_baseline(line: str) -> Dict[str, str]:
    rows = read_csv_dicts("ridership_baseline.csv")
    for row in rows:
        if row.get("line") == line:
            return row
    return {"line": line, "demand_level": "Unknown", "impact_score": "8", "source": "Local fallback baseline"}


def attempt_live_ridership_status() -> Dict[str, str]:
    try:
        response = requests.get(RIDERSHIP_CSV_URL, timeout=3)
        if response.status_code == 200 and response.text:
            return {
                "label": "Ridership context",
                "status": "Live connected",
                "detail": "Official open ridership CSV reachable. App keeps cached baseline for stable demo scoring.",
                "source": "data.gov.my ridership_headline.csv"
            }
    except Exception:
        pass
    return {
        "label": "Ridership context",
        "status": "Fallback active",
        "detail": "Using cached official baseline stored in data/ridership_baseline.csv.",
        "source": "Cached official/open-data baseline"
    }


def attempt_weather_status() -> Dict[str, str]:
    warning_ok = False
    forecast_ok = False
    try:
        warning = requests.get(WEATHER_WARNING_URL, timeout=3)
        warning_ok = warning.status_code == 200
    except Exception:
        warning_ok = False
    try:
        forecast = requests.get(WEATHER_FORECAST_URL, timeout=3)
        forecast_ok = forecast.status_code == 200
    except Exception:
        forecast_ok = False

    if warning_ok or forecast_ok:
        return {
            "label": "Weather context",
            "status": "Live connected",
            "detail": "Official weather endpoint reachable. Demo scoring still uses selected weather state for repeatability.",
            "source": "api.data.gov.my / MET Malaysia"
        }
    return {
        "label": "Weather context",
        "status": "Fallback active",
        "detail": "Using selected demo weather context. Live endpoint can be plugged in for production.",
        "source": "Manual fallback / integration-ready"
    }


def get_integration_status() -> List[Dict[str, str]]:
    return [
        attempt_live_ridership_status(),
        attempt_weather_status(),
        {
            "label": "Station network",
            "status": "Reference loaded",
            "detail": "Station and interchange mapping loaded from local CSV reference.",
            "source": "Curated public route reference"
        },
        {
            "label": "Disruption input",
            "status": "Controlled demo",
            "detail": "Incident is controlled for repeatable pitch-day demo. Production can connect to operator incident feeds.",
            "source": "Demo simulator / operator-feed ready"
        }
    ]
