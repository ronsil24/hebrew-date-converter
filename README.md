# Hebrew Date Converter

A small web app that converts a Gregorian date to a Hebrew date using the
[Hebcal Hebrew Date Converter REST API](https://www.hebcal.com/home/219/hebrew-date-converter-rest-api).

**Stack:** Python, FastAPI, HTTPX, HTML/CSS/vanilla JavaScript, Pytest.

## Project structure

```text
main.py              FastAPI endpoints, input validation, HTTP error handling
hebcal_service.py    Calls the Hebcal API and parses its response
static/              Frontend (index.html, style.css, app.js)
tests/               Pytest tests (Hebcal is mocked, no network needed)
requirements.txt     Python dependencies
```

## Setup

Requires Python 3.10 or newer.

```bash
python3 -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Run the app

```bash
uvicorn main:app --reload
```

Open http://127.0.0.1:8000, pick a date and click **Convert**.

## Run the tests

```bash
pytest
```

## API

`GET /api/convert?date=YYYY-MM-DD`

Example success response (`date=2011-06-02`):

```json
{
  "gregorian_date": "2011-06-02",
  "hebrew": "כ״ט בְּאִיָיר תשע״א",
  "hebrew_year": 5771,
  "hebrew_month": "Iyyar",
  "hebrew_day": 29,
  "events": ["Parashat Nasso", "44th day of the Omer"]
}
```

Errors return `{"detail": "<message>"}`:

| Status | When |
|--------|------|
| 400 | Date is missing, not in `YYYY-MM-DD` format, or does not exist (e.g. `2023-02-29`) |
| 502 | Hebcal returned an error, a non-200 status, invalid JSON, or an unexpected format, or could not be reached |
| 504 | Hebcal did not respond within 5 seconds |

## How it calls Hebcal

```text
GET https://www.hebcal.com/converter?cfg=json&g2h=1&strict=1&gy=2011&gm=6&gd=2
```

- `cfg=json`: JSON output
- `g2h=1`: convert Gregorian to Hebrew
- `strict=1`: Hebcal returns 400 for invalid dates instead of adjusting them
- `gy`, `gm`, `gd`: Gregorian year, month and day

Hebrew date data is provided by [Hebcal.com](https://www.hebcal.com) under CC BY 4.0.
