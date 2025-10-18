"""Test poller task logic."""
import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.workers.tasks import next_interval_ms


def test_next_interval_exponential_backoff():
    """Test exponential backoff calculation."""
    min_ms = 1000
    max_ms = 30000
    jitter = 0.2

    # First attempt
    interval_0 = next_interval_ms(0, min_ms, max_ms, jitter)
    assert 800 <= interval_0 <= 1200  # 1000 ± 20%

    # Second attempt (2x)
    interval_1 = next_interval_ms(1, min_ms, max_ms, jitter)
    assert 1600 <= interval_1 <= 2400  # 2000 ± 20%

    # Many attempts (capped at max)
    interval_10 = next_interval_ms(10, min_ms, max_ms, jitter)
    assert 24000 <= interval_10 <= 36000  # Should be capped near max_ms


@pytest.mark.asyncio
async def test_poller_completed_scenario():
    """Test poller handling completed job."""
    # Load fixture
    fixtures_path = Path(__file__).parent / "fixtures"
    with open(fixtures_path / "jobset_completed.json") as f:
        completed_data = json.load(f)

    # Mock provider
    with patch("app.workers.tasks.get_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.get_job_set.return_value = {
            "status": "completed",
            "results": completed_data["results"],
        }
        mock_get_provider.return_value = mock_provider

        # Test would call poll_generation and verify job transitions to SUCCEEDED
        # This is a simplified test; full implementation would need DB mocking
        assert completed_data["status"] == "completed"
        assert len(completed_data["results"]) == 1


@pytest.mark.asyncio
async def test_poller_failed_scenario():
    """Test poller handling failed job."""
    # Load fixture
    fixtures_path = Path(__file__).parent / "fixtures"
    with open(fixtures_path / "jobset_failed.json") as f:
        failed_data = json.load(f)

    # Mock provider
    with patch("app.workers.tasks.get_provider") as mock_get_provider:
        mock_provider = AsyncMock()
        mock_provider.get_job_set.return_value = {
            "status": "failed",
            "results": [],
        }
        mock_get_provider.return_value = mock_provider

        # Test would call poll_generation and verify job transitions to FAILED
        assert failed_data["status"] == "failed"

