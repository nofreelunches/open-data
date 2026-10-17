"""FredClient tests. HTTP is mocked; no API key is required."""

from __future__ import annotations

import logging
from datetime import date, datetime

import httpx
import pytest

from golem_sources.fred import FredClient, FredError, _redact

API_KEY = "0123456789abcdef0123456789abcdef"
OTHER_KEY = "fedcba9876543210fedcba9876543210"


def _client(handler, key: str = API_KEY) -> FredClient:
    return FredClient(key, transport=httpx.MockTransport(handler))


def _observations_payload(rows: list[tuple[str, str]], *, count: int | None = None, offset: int = 0):
    return {
        "count": len(rows) if count is None else count,
        "offset": offset,
        "limit": 100000,
        "observations": [
            {"date": observed, "value": value, "realtime_start": "2024-01-01"}
            for observed, value in rows
        ],
    }


def _info_payload():
    return {
        "seriess": [
            {
                "id": "UNRATE",
                "title": "Unemployment Rate",
                "frequency": "Monthly",
                "units": "Percent",
                "seasonal_adjustment": "Seasonally Adjusted",
                "observation_start": "1948-01-01",
                "observation_end": "2024-09-01",
                "notes": "The unemployment rate.",
            }
        ]
    }


def test_missing_api_key_raises_before_http(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("FRED_API_KEY", raising=False)

    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP should not be called")

    with pytest.raises(FredError, match="FRED_API_KEY"):
        FredClient(transport=httpx.MockTransport(handler))


def test_blank_api_key_raises() -> None:
    with pytest.raises(FredError, match="FRED_API_KEY"):
        FredClient("   ")


def test_env_var_is_used(monkeypatch: pytest.MonkeyPatch) -> None:
    seen: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        seen.append(request.url.params["api_key"])
        return httpx.Response(200, json=_info_payload())

    monkeypatch.setenv("FRED_API_KEY", f"  {API_KEY}  ")
    with FredClient(transport=httpx.MockTransport(handler)) as client:
        info = client.series_info("UNRATE")
    assert seen == [API_KEY]
    assert info.title == "Unemployment Rate"


def test_argument_overrides_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("FRED_API_KEY", OTHER_KEY)

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["api_key"] == API_KEY
        return httpx.Response(200, json=_info_payload())

    with _client(handler) as client:
        assert client.series_info("UNRATE").id == "UNRATE"


def test_repr_omits_api_key() -> None:
    with _client(lambda _request: httpx.Response(200, json=_info_payload())) as client:
        assert API_KEY not in repr(client)
        assert repr(client) == "FredClient()"


def test_get_series_parses_values_and_missing() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["series_id"] == "UNRATE"
        assert request.url.params["file_type"] == "json"
        assert request.url.params["observation_start"] == "2020-01-01"
        assert request.url.params["observation_end"] == "2020-03-01"
        assert request.url.params["api_key"] == API_KEY
        assert "/series/observations" in str(request.url)
        return httpx.Response(
            200,
            json=_observations_payload(
                [("2020-01-01", "3.5"), ("2020-02-01", "."), ("2020-03-01", "4")]
            ),
        )

    with _client(handler) as client:
        rows = client.get_series(
            "UNRATE",
            observation_start=date(2020, 1, 1),
            observation_end=datetime(2020, 3, 1, 15, 30),
        )
    assert rows == [
        type(rows[0])(date=date(2020, 1, 1), value=3.5),
        type(rows[0])(date=date(2020, 2, 1), value=None),
        type(rows[0])(date=date(2020, 3, 1), value=4.0),
    ]


def test_logged_url_has_no_api_key(caplog: pytest.LogCaptureFixture) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.params["api_key"] == API_KEY
        return httpx.Response(200, json=_observations_payload([("2020-01-01", "3.5")]))

    caplog.set_level(logging.DEBUG)
    with _client(handler) as client:
        client.get_series("UNRATE")

    assert caplog.text
    assert API_KEY not in caplog.text
    assert "api_key=" not in caplog.text
    assert "series_id=UNRATE" in caplog.text


def test_log_records_that_contain_the_key_are_redacted(caplog: pytest.LogCaptureFixture) -> None:
    _client(lambda _request: httpx.Response(200, json=_info_payload())).close()
    poisoned = f"GET https://api.stlouisfed.org/fred/series?api_key={API_KEY}&series_id=UNRATE"
    caplog.set_level(logging.DEBUG)
    logging.getLogger("httpx").info("HTTP Request: %s", poisoned)
    logging.getLogger("httpcore.http11").debug("request url %s", poisoned)
    logging.getLogger("some.other.logger").warning(poisoned)

    assert API_KEY not in caplog.text
    assert "api_key=REDACTED" in caplog.text


def test_transport_error_redacts_key() -> None:
    url = f"https://api.stlouisfed.org/fred/series/observations?api_key={API_KEY}&series_id=UNRATE"

    def handler(_request: httpx.Request) -> httpx.Response:
        raise RuntimeError(f"connection failed for url '{url}'")

    with _client(handler) as client:
        with pytest.raises(FredError) as caught:
            client.get_series("UNRATE")
    message = str(caught.value)
    assert API_KEY not in message
    assert "api_key=REDACTED" in message
    assert caught.value.__cause__ is None


def test_http_error_redacts_key_in_body() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error_code": 400, "error_message": f"Bad Request. api_key={API_KEY} is invalid."},
        )

    with _client(handler) as client:
        with pytest.raises(FredError) as caught:
            client.series_info("UNRATE")
    message = str(caught.value)
    assert API_KEY not in message
    assert "400" in message
    assert "api_key=REDACTED" in message


def test_non_json_error_body_is_redacted() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(502, text=f"upstream down api_key={API_KEY}")

    with _client(handler) as client:
        with pytest.raises(FredError) as caught:
            client.get_series("UNRATE")
    assert API_KEY not in str(caught.value)
    assert "502" in str(caught.value)


def test_invalid_json_success_body() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="<observations>")

    with _client(handler) as client:
        with pytest.raises(FredError, match="not JSON"):
            client.get_series("UNRATE")


def test_series_info_and_empty_notes() -> None:
    payload = _info_payload()
    payload["seriess"][0]["notes"] = ""

    def handler(request: httpx.Request) -> httpx.Response:
        assert request.url.path.endswith("/series")
        return httpx.Response(200, json=payload)

    with _client(handler) as client:
        info = client.series_info("UNRATE")
    assert info.units == "Percent"
    assert info.frequency == "Monthly"
    assert info.observation_start == date(1948, 1, 1)
    assert info.notes is None


def test_missing_series_uses_fred_message() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            400,
            json={"error_message": "Bad Request.  The series does not exist."},
        )

    with _client(handler) as client:
        with pytest.raises(FredError, match="does not exist"):
            client.get_series("NOT_A_SERIES")


def test_invalid_series_id_skips_http() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        raise AssertionError("HTTP should not be called")

    with _client(handler) as client:
        with pytest.raises(FredError, match="Series id"):
            client.get_series("no spaces")


def test_invalid_date() -> None:
    with _client(lambda _request: httpx.Response(200, json={})) as client:
        with pytest.raises(FredError, match="observation_start"):
            client.get_series("UNRATE", observation_start="01/01/2020")


def test_pagination(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("golem_sources.fred._PAGE_SIZE", 2)
    pages = {
        "0": [("2020-01-01", "1.0"), ("2020-02-01", "2.0")],
        "2": [("2020-03-01", ".")],
    }

    def handler(request: httpx.Request) -> httpx.Response:
        offset = request.url.params["offset"]
        assert request.url.params["limit"] == "2"
        rows = pages[offset]
        return httpx.Response(200, json=_observations_payload(rows, count=3, offset=int(offset)))

    with _client(handler) as client:
        rows = client.get_series("UNRATE")
    assert [row.value for row in rows] == [1.0, 2.0, None]


def test_invalid_observation_count() -> None:
    def handler(_request: httpx.Request) -> httpx.Response:
        payload = _observations_payload([("2020-01-01", "1.0")])
        payload["count"] = "many"
        return httpx.Response(200, json=payload)

    with _client(handler) as client:
        with pytest.raises(FredError, match="observation count"):
            client.get_series("UNRATE")


def test_too_many_pages(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr("golem_sources.fred._PAGE_SIZE", 1)
    monkeypatch.setattr("golem_sources.fred._MAX_PAGES", 2)

    def handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json=_observations_payload([("2020-01-01", "1.0")], count=50),
        )

    with _client(handler) as client:
        with pytest.raises(FredError, match="too many pages"):
            client.get_series("UNRATE")


def test_context_manager_closes_transport() -> None:
    closed = {"value": False}

    class Tracking(httpx.BaseTransport):
        def handle_request(self, request: httpx.Request) -> httpx.Response:
            raise AssertionError(f"unexpected request {request.url}")

        def close(self) -> None:
            closed["value"] = True

    with FredClient(API_KEY, transport=Tracking()):
        pass
    assert closed["value"] is True


def test_redact_encoded_key() -> None:
    key = "abc def/0123456789abcdef012345"
    with FredClient(key, transport=httpx.MockTransport(lambda _request: httpx.Response(200, json={}))):
        pass
    encoded = "abc%20def%2F0123456789abcdef012345"
    text = f"https://example.test/fred?api_key={encoded}&series_id=UNRATE"
    redacted = _redact(text)
    assert key not in redacted
    assert encoded not in redacted
    assert "api_key=REDACTED" in redacted
