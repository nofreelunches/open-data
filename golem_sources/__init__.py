"""Clients for public data sources."""

from golem_sources.fred import FredClient, FredError, Observation, SeriesInfo

__all__ = ["FredClient", "FredError", "Observation", "SeriesInfo"]
