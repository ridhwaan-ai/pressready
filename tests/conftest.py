import pytest

from pressready import access


@pytest.fixture(autouse=True)
def _generous_free_tier(monkeypatch):
    """API tests build many books in a row; real servers use the default free tier."""
    monkeypatch.setenv("PRESSREADY_FREE_PER_DAY", "1000")
    access._free_counts.clear()
    access._key_cache.clear()
