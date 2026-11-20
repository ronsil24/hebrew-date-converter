"""Communication with the Hebcal Hebrew Date Converter REST API.

Docs: https://www.hebcal.com/home/219/hebrew-date-converter-rest-api
"""

from datetime import date

import httpx

HEBCAL_CONVERTER_URL = "https://www.hebcal.com/converter"
TIMEOUT_SECONDS = 5.0


class HebcalError(Exception):
    """Hebcal returned an error or a response we could not understand."""


class HebcalTimeoutError(HebcalError):
    """Hebcal did not answer in time."""


async def convert_to_hebrew(
    gregorian_date: date, client: httpx.AsyncClient | None = None
) -> dict:
    """Convert a Gregorian date to a Hebrew date using Hebcal.

    `client` is optional so tests can pass a client with a mocked transport.
    """
    params = {
        "cfg": "json",  # ask for JSON output
        "g2h": 1,  # direction: Gregorian -> Hebrew
        "strict": 1,  # Hebcal returns 400 instead of guessing on bad dates
        "gy": gregorian_date.year,
        "gm": gregorian_date.month,
        "gd": gregorian_date.day,
    }

    if client is None:
        async with httpx.AsyncClient(timeout=TIMEOUT_SECONDS) as new_client:
            return await _request(new_client, params)
    return await _request(client, params)


async def _request(client: httpx.AsyncClient, params: dict) -> dict:
    try:
        response = await client.get(HEBCAL_CONVERTER_URL, params=params)
    except httpx.TimeoutException as exc:
        raise HebcalTimeoutError("Hebcal API timed out") from exc
    except httpx.RequestError as exc:
        raise HebcalError(f"Could not reach Hebcal API: {exc}") from exc

    if response.status_code != 200:
        raise HebcalError(f"Hebcal API returned status {response.status_code}")

    try:
        data = response.json()
    except ValueError as exc:
        raise HebcalError("Hebcal API returned invalid JSON") from exc

    return _parse(data)


def _parse(data) -> dict:
    """Keep only the fields we need and check that they look right."""
    if not isinstance(data, dict):
        raise HebcalError("Unexpected response format from Hebcal API")
    if "error" in data:
        raise HebcalError(f"Hebcal API error: {data['error']}")

    hebrew = data.get("hebrew")
    month = data.get("hm")
    year = data.get("hy")
    day = data.get("hd")
    events = data.get("events", [])  # optional: some dates have no events

    # Check types instead of converting them, so bad data is rejected
    # rather than silently turned into something that looks valid.
    if not isinstance(hebrew, str) or not hebrew.strip():
        raise HebcalError("Unexpected response format from Hebcal API")
    if not isinstance(month, str) or not month.strip():
        raise HebcalError("Unexpected response format from Hebcal API")
    # bool is a subclass of int in Python (True == 1), so exclude it explicitly.
    if not isinstance(year, int) or isinstance(year, bool):
        raise HebcalError("Unexpected response format from Hebcal API")
    if not isinstance(day, int) or isinstance(day, bool):
        raise HebcalError("Unexpected response format from Hebcal API")
    if not isinstance(events, list) or not all(isinstance(e, str) for e in events):
        raise HebcalError("Unexpected response format from Hebcal API")

    return {
        "hebrew": hebrew,
        "hebrew_year": year,
        "hebrew_month": month,
        "hebrew_day": day,
        "events": events,
    }
