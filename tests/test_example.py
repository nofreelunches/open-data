"""The example script runs without a key and does not print one."""

from __future__ import annotations

import importlib.util
import os
from datetime import date
from pathlib import Path

import pytest

from golem_sources import Observation, SeriesInfo

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "examples" / "pull_fred_series.py"


def _load():
    spec = importlib.util.spec_from_file_location("pull_fred_series", EXAMPLE)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_render_tail_and_missing_value() -> None:
    example = _load()
    info = SeriesInfo(
        id="UNRATE",
        title="Unemployment Rate",
        frequency="Monthly",
        units="Percent",
        seasonal_adjustment="Seasonally Adjusted",
        observation_start=date(1948, 1, 1),
        observation_end=date(2024, 9, 1),
    )
    rows = [
        Observation(date=date(2023, i, 1), value=float(i))
        for i in range(1, 13)
    ]
    rows.append(Observation(date=date(2024, 1, 1), value=None))
    text = example.render(info, rows, tail=2)
    assert text == "\n".join(
        [
            "UNRATE: Unemployment Rate",
            "Units: Percent",
            "Frequency: Monthly",
            "",
            "2023-12-01  12",
            "2024-01-01  NA",
        ]
    )


def test_render_empty() -> None:
    example = _load()
    info = SeriesInfo(
        id="UNRATE",
        title="Unemployment Rate",
        frequency="Monthly",
        units="Percent",
        seasonal_adjustment="Seasonally Adjusted",
        observation_start=date(1948, 1, 1),
        observation_end=date(2024, 9, 1),
    )
    assert example.render(info, []).endswith("(no observations)")


def test_load_env_file_does_not_override_or_print(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    example = _load()
    env_file = tmp_path / ".env"
    env_file.write_text(
        '\n'.join(
            [
                "# comment",
                "export FRED_API_KEY='from-file'",
                "OTHER=1",
                "",
            ]
        ),
        encoding="utf-8",
    )
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    monkeypatch.delenv("OTHER", raising=False)
    example.load_env_file(env_file)
    assert os.environ["FRED_API_KEY"] == "from-file"
    monkeypatch.setenv("FRED_API_KEY", "already-set")
    example.load_env_file(env_file)
    assert os.environ["FRED_API_KEY"] == "already-set"
    captured = capsys.readouterr()
    assert captured.out == ""
    assert captured.err == ""
    assert "from-file" not in captured.out


def test_main_prints_series(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    example = _load()
    monkeypatch.setattr(example, "load_env_file", lambda _path: None)

    class FakeClient:
        def __enter__(self) -> FakeClient:
            return self

        def __exit__(self, *args: object) -> bool:
            return False

        def series_info(self, series_id: str) -> SeriesInfo:
            assert series_id == "GDP"
            return SeriesInfo(
                id="GDP",
                title="Gross Domestic Product",
                frequency="Quarterly",
                units="Billions of Dollars",
                seasonal_adjustment="Seasonally Adjusted Annual Rate",
                observation_start=date(1947, 1, 1),
                observation_end=date(2024, 1, 1),
            )

        def get_series(self, series_id: str) -> list[Observation]:
            assert series_id == "GDP"
            return [Observation(date=date(2024, 1, 1), value=1.5)]

    monkeypatch.setattr(example, "FredClient", lambda: FakeClient())
    assert example.main(["GDP"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert "GDP: Gross Domestic Product" in captured.out
    assert "2024-01-01  1.5" in captured.out


def test_main_missing_key_exits(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    example = _load()
    monkeypatch.setattr(example, "load_env_file", lambda _path: None)
    monkeypatch.delenv("FRED_API_KEY", raising=False)
    assert example.main([]) == 1
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "FRED_API_KEY" in captured.err
    assert "0123456789abcdef" not in captured.err
