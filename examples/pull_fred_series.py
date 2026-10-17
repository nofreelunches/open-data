"""Print a FRED series.

Reads FRED_API_KEY from the environment, or from a .env file in the repository
root. The key is not printed.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

from golem_sources import FredClient, FredError, Observation, SeriesInfo

SERIES_ID = "UNRATE"
TAIL = 12


def load_env_file(path: Path) -> None:
    """Load KEY=VALUE lines from ``path`` when the variable is not already set."""
    if not path.is_file():
        return
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[len("export ") :].strip()
        if "=" not in line:
            continue
        name, value = line.split("=", 1)
        name = name.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
            value = value[1:-1]
        if name and name not in os.environ:
            os.environ[name] = value


def format_value(value: float | None) -> str:
    if value is None:
        return "NA"
    text = f"{value:.10f}".rstrip("0").rstrip(".")
    return text or "0"


def render(info: SeriesInfo, observations: list[Observation], tail: int = TAIL) -> str:
    lines = [
        f"{info.id}: {info.title}",
        f"Units: {info.units}",
        f"Frequency: {info.frequency}",
        "",
    ]
    rows = observations[-tail:] if tail > 0 else observations
    if not rows:
        lines.append("(no observations)")
        return "\n".join(lines)
    for row in rows:
        lines.append(f"{row.date.isoformat()}  {format_value(row.value)}")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    series_id = args[0] if args else SERIES_ID
    root = Path(__file__).resolve().parents[1]
    load_env_file(root / ".env")
    try:
        with FredClient() as fred:
            info = fred.series_info(series_id)
            observations = fred.get_series(series_id)
    except FredError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    print(render(info, observations))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
