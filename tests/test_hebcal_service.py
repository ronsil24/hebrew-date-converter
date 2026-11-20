"""Tests for hebcal_service. Hebcal is never called: httpx.MockTransport fakes it."""

import asyncio
from datetime import date

import httpx
import pytest

import hebcal_service

SAMPLE_RESPONSE = {
    "gy": 2011,
    "gm": 6,
    "gd": 2,
    "afterSunset": False,
    "hy": 5771,
    "hm": "Iyyar",
    "hd": 29,
    "hebrew": "כ״ט בְּאִיָיר תשע״א",
    "heDateParts": {"y": "תשע״א", "m": "אייר", "d": "כ״ט"},
    "events": ["Parashat Nasso", "44th day of the Omer"],
}


def run_with_handler(handler, day=date(2011, 6, 2)):
    """Call the service with a fake HTTP layer that uses `handler`."""

    async def go():
        transport = httpx.MockTransport(handler)
        async with httpx.AsyncClient(transport=transport) as client:
            return await hebcal_service.convert_to_hebrew(day, client=client)

    return asyncio.run(go())


def test_successful_conversion_returns_parsed_fields():
    result = run_with_handler(lambda request: httpx.Response(200, json=SAMPLE_RESPONSE))

    assert result == {
        "hebrew": "כ״ט בְּאִיָיר תשע״א",
        "hebrew_year": 5771,
        "hebrew_month": "Iyyar",
        "hebrew_day": 29,
        "events": ["Parashat Nasso", "44th day of the Omer"],
    }


def test_sends_documented_query_parameters():
    seen = {}

    def handler(request):
        seen["url"] = request.url
        return httpx.Response(200, json=SAMPLE_RESPONSE)

    run_with_handler(handler)

    url = seen["url"]
    assert str(url).startswith("https://www.hebcal.com/converter")
    assert url.params["cfg"] == "json"
    assert url.params["g2h"] == "1"
    assert url.params["strict"] == "1"
    assert url.params["gy"] == "2011"
    assert url.params["gm"] == "6"
    assert url.params["gd"] == "2"


def test_timeout_raises_timeout_error():
    def handler(request):
        raise httpx.ReadTimeout("too slow", request=request)

    with pytest.raises(hebcal_service.HebcalTimeoutError):
        run_with_handler(handler)


def test_connection_error_raises_hebcal_error():
    def handler(request):
        raise httpx.ConnectError("no network", request=request)

    with pytest.raises(hebcal_service.HebcalError):
        run_with_handler(handler)


@pytest.mark.parametrize("status", [400, 404, 500, 503])
def test_non_200_status_raises_hebcal_error(status):
    with pytest.raises(hebcal_service.HebcalError):
        run_with_handler(lambda request: httpx.Response(status, json={"error": "x"}))


def test_invalid_json_raises_hebcal_error():
    with pytest.raises(hebcal_service.HebcalError):
        run_with_handler(lambda request: httpx.Response(200, text="<html>oops</html>"))


def test_error_field_in_body_raises_hebcal_error():
    with pytest.raises(hebcal_service.HebcalError):
        run_with_handler(lambda request: httpx.Response(200, json={"error": "bad date"}))


def without(field):
    """SAMPLE_RESPONSE with one field removed."""
    return {k: v for k, v in SAMPLE_RESPONSE.items() if k != field}


@pytest.mark.parametrize(
    "body",
    [
        pytest.param([], id="not-an-object"),
        pytest.param(None, id="null-body"),
        # missing required fields
        pytest.param(without("hebrew"), id="missing-hebrew"),
        pytest.param(without("hm"), id="missing-hm"),
        pytest.param(without("hy"), id="missing-hy"),
        pytest.param(without("hd"), id="missing-hd"),
        # hebrew / hm must be non-empty strings
        pytest.param({**SAMPLE_RESPONSE, "hebrew": ""}, id="hebrew-empty"),
        pytest.param({**SAMPLE_RESPONSE, "hebrew": "   "}, id="hebrew-blank"),
        pytest.param({**SAMPLE_RESPONSE, "hebrew": 123}, id="hebrew-number"),
        pytest.param({**SAMPLE_RESPONSE, "hebrew": None}, id="hebrew-null"),
        pytest.param({**SAMPLE_RESPONSE, "hm": ""}, id="hm-empty"),
        pytest.param({**SAMPLE_RESPONSE, "hm": ["Iyyar"]}, id="hm-list"),
        # hy / hd must be real integers
        pytest.param({**SAMPLE_RESPONSE, "hy": "5771"}, id="hy-numeric-string"),
        pytest.param({**SAMPLE_RESPONSE, "hy": True}, id="hy-bool"),
        pytest.param({**SAMPLE_RESPONSE, "hy": 5771.5}, id="hy-float"),
        pytest.param({**SAMPLE_RESPONSE, "hy": None}, id="hy-null"),
        pytest.param({**SAMPLE_RESPONSE, "hd": "29"}, id="hd-numeric-string"),
        pytest.param({**SAMPLE_RESPONSE, "hd": False}, id="hd-bool"),
        pytest.param({**SAMPLE_RESPONSE, "hd": "not a number"}, id="hd-text"),
        # events, when present, must be a list of strings
        pytest.param({**SAMPLE_RESPONSE, "events": "Parashat Nasso"}, id="events-string"),
        pytest.param({**SAMPLE_RESPONSE, "events": None}, id="events-null"),
        pytest.param({**SAMPLE_RESPONSE, "events": ["ok", 5]}, id="events-non-string-item"),
        pytest.param({**SAMPLE_RESPONSE, "events": {"a": "b"}}, id="events-object"),
    ],
)
def test_malformed_response_raises_hebcal_error(body):
    with pytest.raises(hebcal_service.HebcalError):
        run_with_handler(lambda request: httpx.Response(200, json=body))


def test_missing_events_defaults_to_empty_list():
    result = run_with_handler(lambda request: httpx.Response(200, json=without("events")))
    assert result["events"] == []


def test_empty_events_list_is_valid():
    body = {**SAMPLE_RESPONSE, "events": []}
    result = run_with_handler(lambda request: httpx.Response(200, json=body))
    assert result["events"] == []


def test_valid_response_keeps_exact_types():
    result = run_with_handler(lambda request: httpx.Response(200, json=SAMPLE_RESPONSE))

    assert type(result["hebrew_year"]) is int
    assert type(result["hebrew_day"]) is int
    assert isinstance(result["hebrew"], str)
    assert isinstance(result["hebrew_month"], str)
    assert all(isinstance(e, str) for e in result["events"])
