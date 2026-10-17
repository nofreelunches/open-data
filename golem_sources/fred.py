"""Download a series from the FRED API.

The API key is read from the ``api_key`` argument or from the ``FRED_API_KEY``
environment variable. FRED requires the key as an ``api_key`` query parameter,
so the request on the wire includes it. httpx logs the request URL before the
transport runs; the key is added on a copy of that request inside the
transport, and log records and error messages that contain the key are
rewritten without it.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import date, datetime
from urllib.parse import quote

import httpx

_BASE_URL = "https://api.stlouisfed.org/fred"
_ENV_VAR = "FRED_API_KEY"
_PAGE_SIZE = 100_000
_MAX_PAGES = 100
_SERIES_ID = re.compile(r"^[A-Za-z0-9_-]{1,128}$")
_API_KEY_QUERY = re.compile(r"(?i)(api_key=)[^&\s\"']+")
_REDACTED = "REDACTED"

_keys: set[str] = set()
_logging_installed = False


class FredError(Exception):
    """A FRED request could not be completed.

    The message does not include the API key.
    """


@dataclass(frozen=True, slots=True)
class Observation:
    """One date and its value. ``value`` is ``None`` when FRED sends ``.``."""

    date: date
    value: float | None


@dataclass(frozen=True, slots=True)
class SeriesInfo:
    """Title, units, and frequency for a series."""

    id: str
    title: str
    frequency: str
    units: str
    seasonal_adjustment: str
    observation_start: date
    observation_end: date
    notes: str | None = None


class _ApiKeyTransport(httpx.BaseTransport):
    """Add the API key on a copy of the request, then call the inner transport."""

    def __init__(self, inner: httpx.BaseTransport, api_key: str) -> None:
        self._inner = inner
        self._api_key = api_key

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        params = dict(request.url.params)
        params["api_key"] = self._api_key
        outbound = httpx.Request(
            request.method,
            request.url.copy_with(params=params),
            headers=request.headers,
            content=request.content,
        )
        try:
            return self._inner.handle_request(outbound)
        except Exception as exc:
            raise FredError(_redact(f"FRED request failed. {exc}")) from None

    def close(self) -> None:
        self._inner.close()


class FredClient:
    """Client for the FRED ``series`` and ``series/observations`` endpoints."""

    def __init__(
        self,
        api_key: str | None = None,
        *,
        transport: httpx.BaseTransport | None = None,
        timeout: float = 30.0,
    ) -> None:
        key = _resolve_api_key(api_key)
        _register_key(key)
        inner = transport if transport is not None else httpx.HTTPTransport()
        self._client = httpx.Client(
            transport=_ApiKeyTransport(inner, key),
            timeout=timeout,
        )

    def __enter__(self) -> FredClient:
        return self

    def __exit__(self, *exc: object) -> None:
        self.close()

    def close(self) -> None:
        self._client.close()

    def __repr__(self) -> str:
        return "FredClient()"

    def series_info(self, series_id: str) -> SeriesInfo:
        """Return the title, units, and frequency for ``series_id``."""
        series_id = _check_series_id(series_id)
        payload = self._get("series", {"series_id": series_id, "file_type": "json"})
        rows = payload.get("seriess")
        if not isinstance(rows, list) or not rows:
            raise FredError(f"FRED did not return metadata for series {series_id}.")
        row = rows[0]
        if not isinstance(row, dict):
            raise FredError(f"FRED returned unexpected metadata for series {series_id}.")
        notes = row.get("notes")
        return SeriesInfo(
            id=str(row.get("id") or series_id),
            title=str(row.get("title") or ""),
            frequency=str(row.get("frequency") or ""),
            units=str(row.get("units") or ""),
            seasonal_adjustment=str(row.get("seasonal_adjustment") or ""),
            observation_start=_parse_date(row.get("observation_start"), "observation_start"),
            observation_end=_parse_date(row.get("observation_end"), "observation_end"),
            notes=notes if isinstance(notes, str) and notes else None,
        )

    def get_series(
        self,
        series_id: str,
        *,
        observation_start: date | str | None = None,
        observation_end: date | str | None = None,
    ) -> list[Observation]:
        """Return observations for ``series_id``, oldest first.

        A FRED value of ``.`` is returned as ``None``.
        """
        series_id = _check_series_id(series_id)
        start = _check_date(observation_start, "observation_start")
        end = _check_date(observation_end, "observation_end")
        observations: list[Observation] = []
        offset = 0
        for _page in range(_MAX_PAGES):
            params: dict[str, str] = {
                "series_id": series_id,
                "file_type": "json",
                "limit": str(_PAGE_SIZE),
                "offset": str(offset),
            }
            if start is not None:
                params["observation_start"] = start
            if end is not None:
                params["observation_end"] = end
            payload = self._get("series/observations", params)
            batch = payload.get("observations")
            if not isinstance(batch, list):
                raise FredError(f"FRED did not return observations for series {series_id}.")
            observations.extend(_parse_observation(item) for item in batch)
            if not batch:
                return observations
            offset += len(batch)
            count = payload.get("count")
            if count is None:
                return observations
            try:
                total = int(count)
            except (TypeError, ValueError):
                raise FredError(
                    f"FRED returned an invalid observation count for series {series_id}."
                ) from None
            if offset >= total:
                return observations
        raise FredError("FRED returned too many pages for one series.")

    def _get(self, endpoint: str, params: dict[str, str]) -> dict:
        try:
            response = self._client.get(f"{_BASE_URL}/{endpoint}", params=params)
        except FredError:
            raise
        except Exception as exc:
            raise FredError(_redact(f"FRED request failed. {exc}")) from None
        if response.status_code >= 400:
            raise _error_from_response(response)
        try:
            payload = response.json()
        except ValueError:
            raise FredError("FRED returned a response that was not JSON.") from None
        if not isinstance(payload, dict):
            raise FredError("FRED returned a response that was not a JSON object.")
        if "error_message" in payload and "observations" not in payload and "seriess" not in payload:
            message = payload.get("error_message")
            detail = message.strip() if isinstance(message, str) else ""
            raise FredError(_redact(f"FRED request failed. {detail}".rstrip()))
        return payload


def _resolve_api_key(api_key: str | None) -> str:
    if api_key is None:
        raw = os.environ.get(_ENV_VAR, "")
    else:
        raw = api_key
    key = raw.strip()
    if not key:
        raise FredError(f"Set the {_ENV_VAR} environment variable.")
    return key


def _register_key(api_key: str) -> None:
    _keys.add(api_key)
    _install_log_redaction()


def _install_log_redaction() -> None:
    global _logging_installed
    if _logging_installed:
        return
    previous_factory = logging.getLogRecordFactory()

    def factory(*args: object, **kwargs: object) -> logging.LogRecord:
        record = previous_factory(*args, **kwargs)
        _scrub_log_record(record)
        return record

    logging.setLogRecordFactory(factory)
    redactor = _RedactFilter()
    logging.getLogger().addFilter(redactor)
    logging.getLogger("httpx").addFilter(redactor)
    logging.getLogger("httpcore").addFilter(redactor)
    _logging_installed = True


class _RedactFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        _scrub_log_record(record)
        return True


def _scrub_log_record(record: logging.LogRecord) -> None:
    try:
        rendered = record.getMessage()
    except Exception:
        return
    redacted = _redact(rendered)
    if redacted != rendered:
        record.msg = redacted
        record.args = ()


def _redact(text: str) -> str:
    redacted = text
    for key in sorted(_keys, key=len, reverse=True):
        if not key:
            continue
        redacted = redacted.replace(key, _REDACTED)
        encoded = quote(key, safe="")
        if encoded != key:
            redacted = redacted.replace(encoded, _REDACTED)
    return _API_KEY_QUERY.sub(rf"\1{_REDACTED}", redacted)


def _check_series_id(series_id: str) -> str:
    if not isinstance(series_id, str) or _SERIES_ID.fullmatch(series_id) is None:
        raise FredError(
            "Series id must be 1 to 128 characters: letters, digits, underscore, or hyphen."
        )
    return series_id


def _check_date(value: date | datetime | str | None, name: str) -> str | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        return value.date().isoformat()
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, str):
        text = value.strip()
        try:
            return date.fromisoformat(text).isoformat()
        except ValueError:
            raise FredError(f"{name} must be a date in YYYY-MM-DD form.") from None
    raise FredError(f"{name} must be a date in YYYY-MM-DD form.")


def _parse_date(raw: object, name: str) -> date:
    if not isinstance(raw, str):
        raise FredError(f"FRED returned an invalid {name}.")
    try:
        return date.fromisoformat(raw)
    except ValueError:
        raise FredError(f"FRED returned an invalid {name}.") from None


def _parse_observation(item: object) -> Observation:
    if not isinstance(item, dict):
        raise FredError("FRED returned an observation that was not an object.")
    observed = _parse_date(item.get("date"), "observation date")
    return Observation(date=observed, value=_parse_value(item.get("value")))


def _parse_value(raw: object) -> float | None:
    if raw is None:
        return None
    text = str(raw).strip()
    if text in {"", "."}:
        return None
    try:
        return float(text)
    except ValueError:
        raise FredError(_redact(f"FRED returned a non-numeric value: {text!r}")) from None


def _error_from_response(response: httpx.Response) -> FredError:
    detail = ""
    payload: object
    try:
        payload = response.json()
    except ValueError:
        payload = None
    if isinstance(payload, dict):
        message = payload.get("error_message")
        if isinstance(message, str) and message.strip():
            detail = message.strip()
    if not detail:
        detail = response.text.strip()
    detail = _redact(detail)[:300]
    if detail:
        return FredError(f"FRED request failed ({response.status_code}). {detail}")
    return FredError(f"FRED request failed ({response.status_code}).")
