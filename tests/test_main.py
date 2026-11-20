"""Tests for the FastAPI endpoints. The Hebcal service is replaced with fakes."""

import pytest
from fastapi.testclient import TestClient

import hebcal_service
import main

client = TestClient(main.app)

FAKE_RESULT = {
    "hebrew": "כ״ט בְּאִיָיר תשע״א",
    "hebrew_year": 5771,
    "hebrew_month": "Iyyar",
    "hebrew_day": 29,
    "events": ["Parashat Nasso"],
}


@pytest.fixture
def fake_service(monkeypatch):
    """Replace the real Hebcal call; record which date it received."""
    calls = []

    async def fake_convert(gregorian_date):
        calls.append(gregorian_date)
        return FAKE_RESULT

    monkeypatch.setattr(hebcal_service, "convert_to_hebrew", fake_convert)
    return calls


def fail_with(monkeypatch, error):
    async def fake_convert(gregorian_date):
        raise error

    monkeypatch.setattr(hebcal_service, "convert_to_hebrew", fake_convert)


def test_index_serves_html():
    response = client.get("/")
    assert response.status_code == 200
    assert "Hebrew Date Converter" in response.text


def test_convert_success(fake_service):
    response = client.get("/api/convert", params={"date": "2011-06-02"})

    assert response.status_code == 200
    assert response.json() == {"gregorian_date": "2011-06-02", **FAKE_RESULT}
    assert str(fake_service[0]) == "2011-06-02"


@pytest.mark.parametrize(
    "bad_date",
    ["", "   ", "hello", "02/06/2011", "2011-13-01", "2023-02-29", "2011-6-2x"],
)
def test_invalid_dates_return_400(fake_service, bad_date):
    response = client.get("/api/convert", params={"date": bad_date})

    assert response.status_code == 400
    assert "detail" in response.json()
    assert fake_service == []  # Hebcal is never called for bad input


@pytest.mark.parametrize(
    "badly_formatted",
    [
        "2026-1-5",  # month and day not zero-padded
        "2026-01-5",  # day not zero-padded
        "2026-1-05",  # month not zero-padded
        "26-01-05",  # two-digit year
        "02026-01-05",  # five-digit year
        "2026/01/05",  # wrong separator
        "20260105",  # no separators
        "2026-01-05T00:00",  # extra time part
        "2026-01-05x",  # trailing characters
        "2026-٠١-٠٥",  # non-ASCII (Arabic-Indic) digits
    ],
)
def test_badly_formatted_dates_return_400(fake_service, badly_formatted):
    response = client.get("/api/convert", params={"date": badly_formatted})

    assert response.status_code == 400
    assert "YYYY-MM-DD" in response.json()["detail"]
    assert fake_service == []


def test_correctly_padded_date_is_accepted(fake_service):
    response = client.get("/api/convert", params={"date": "2026-01-05"})

    assert response.status_code == 200
    assert str(fake_service[0]) == "2026-01-05"


def test_missing_date_returns_400(fake_service):
    response = client.get("/api/convert")
    assert response.status_code == 400


def test_leap_day_is_valid(fake_service):
    response = client.get("/api/convert", params={"date": "2024-02-29"})
    assert response.status_code == 200


def test_hebcal_timeout_returns_504(monkeypatch):
    fail_with(monkeypatch, hebcal_service.HebcalTimeoutError("timeout"))
    response = client.get("/api/convert", params={"date": "2011-06-02"})

    assert response.status_code == 504
    assert "too long" in response.json()["detail"]


def test_hebcal_failure_returns_502(monkeypatch):
    fail_with(monkeypatch, hebcal_service.HebcalError("broken"))
    response = client.get("/api/convert", params={"date": "2011-06-02"})

    assert response.status_code == 502
    assert "unavailable" in response.json()["detail"]
