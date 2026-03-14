"""Tests for APScheduler integration in main.py."""

from unittest.mock import patch

import pytest

from engine.main import scheduler


class TestSchedulerRegistration:
    @pytest.mark.asyncio
    async def test_metagraph_sync_job_registered(self) -> None:
        """Verify metagraph_sync job is registered after lifespan startup."""
        # The scheduler is a module-level object; we need to test that
        # the lifespan registers the job. We simulate this by running
        # the lifespan context manager.
        from engine.main import lifespan

        mock_app = None  # lifespan ignores the app argument

        with (
            patch("engine.main.run_metagraph_sync_cycle") as _mock_sync,
            patch("engine.main.dispose_subtensor"),
            patch("engine.main.dispose_engine"),
            patch("engine.main.close_redis"),
        ):
            async with lifespan(mock_app):  # type: ignore[arg-type]
                job = scheduler.get_job("metagraph_sync")
                assert job is not None
                assert job.name == "Metagraph Sync Pipeline"
                # Verify interval trigger
                assert hasattr(job.trigger, "interval")

        # After lifespan exit, scheduler is shut down
        # Job may or may not still be queryable after shutdown

    @pytest.mark.asyncio
    async def test_scheduler_uses_configured_interval(self) -> None:
        """Verify scheduler uses settings.metagraph_sync_interval_seconds."""
        from engine.main import lifespan

        with (
            patch("engine.main.settings") as mock_settings,
            patch("engine.main.run_metagraph_sync_cycle"),
            patch("engine.main.dispose_subtensor"),
            patch("engine.main.dispose_engine"),
            patch("engine.main.close_redis"),
        ):
            mock_settings.debug = True
            mock_settings.host = "0.0.0.0"
            mock_settings.port = 8000
            mock_settings.metagraph_sync_interval_seconds = 60

            async with lifespan(None):  # type: ignore[arg-type]
                job = scheduler.get_job("metagraph_sync")
                assert job is not None
                assert job.trigger.interval.total_seconds() == 60
