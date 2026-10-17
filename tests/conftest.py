import pytest


@pytest.fixture(autouse=True)
def _unset_fred_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """Tests must pass with no API key in the environment."""
    monkeypatch.delenv("FRED_API_KEY", raising=False)
