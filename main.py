"""FastAPI app: API endpoint, input validation and HTTP error handling."""

import re
from datetime import date, datetime
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

import hebcal_service

STATIC_DIR = Path(__file__).parent / "static"

# Exactly 4 digits, dash, 2 digits, dash, 2 digits. [0-9] instead of \d,
# because \d also matches non-ASCII digits (e.g. Arabic-Indic numerals).
DATE_FORMAT = re.compile(r"[0-9]{4}-[0-9]{2}-[0-9]{2}")

app = FastAPI(title="Gregorian to Hebrew Date Converter")
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


def parse_date(value: str) -> date:
    """Accept only YYYY-MM-DD dates that really exist (e.g. no 2024-02-30)."""
    error = HTTPException(
        status_code=400,
        detail="Invalid date. Please use a real date in YYYY-MM-DD format.",
    )
    value = value.strip()

    # strptime alone also accepts unpadded dates like "2026-1-5",
    # so check the exact format first.
    if not DATE_FORMAT.fullmatch(value):
        raise error

    # Then check that it is a real calendar date (rejects 2023-02-29, 2026-13-01).
    try:
        return datetime.strptime(value, "%Y-%m-%d").date()
    except ValueError:
        raise error


@app.get("/")
def index():
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/convert")
async def convert(date: str = ""):
    if not date.strip():
        raise HTTPException(status_code=400, detail="Please provide a date.")

    gregorian_date = parse_date(date)

    try:
        hebrew = await hebcal_service.convert_to_hebrew(gregorian_date)
    except hebcal_service.HebcalTimeoutError:
        raise HTTPException(
            status_code=504,
            detail="The Hebcal service took too long to respond. Please try again.",
        )
    except hebcal_service.HebcalError:
        raise HTTPException(
            status_code=502,
            detail="The Hebcal service is unavailable right now. Please try again later.",
        )

    return {"gregorian_date": gregorian_date.isoformat(), **hebrew}
