# open-data

Public data clients, replications, and tutorials for No Free Lunch.

## Layout

| Path | Contents |
|---|---|
| `golem_sources/` | Python clients for public data sources. |
| `examples/` | Short scripts that call those clients. |
| `replications/` | Reproductions of published studies, with methods and deviations written down. |
| `tutorials/` | Short explainers. |
| `articles/` | Code for a published piece, pinned to a release tag. |

## Setup

Python 3.10 or newer.

```bash
python -m pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and set `FRED_API_KEY`. `.env` is gitignored. A free key is available from the St. Louis Fed: https://fred.stlouisfed.org/docs/api/api_key.html

Tests mock the HTTP calls and run with no key set:

```bash
python -m pytest
```

## FRED

`golem_sources.fred.FredClient` downloads one series from the FRED API. The walkthrough is [How a FRED series is pulled](tutorials/01-pull-a-fred-series.md). The script is `examples/pull_fred_series.py`.

This product uses the FRED® API but is not endorsed or certified by the Federal Reserve Bank of St. Louis.

```bash
python examples/pull_fred_series.py
```

## Licenses

Code is under the [MIT License](LICENSE). Text (tutorials, READMEs, and other prose) is under [CC BY 4.0](LICENSE-TEXT). Data stays under each source's own terms. See [DATA_SOURCES.md](DATA_SOURCES.md). This repository does not store data files it is not allowed to redistribute. Clients download data when you run them.

## Citation

See [CITATION.cff](CITATION.cff). Cite a tagged release.
