"""Tests for APScheduler integration in main.py."""

from unittest.mock import patch

import pytest

from engine.main import scheduler


class TestSchedulerRegistration:
    @pytest.mark.asyncio
    async def test_metagraph_sync_job_registered(self) -> None:
        """Verify metagraph_sync job is registered after lifespan startup."""
        from engine.main import lifespan

        mock_app = None

        with (
            patch("engine.main.run_metagraph_sync_cycle") as _mock_sync,
            patch("engine.main.run_price_sync_cycle") as _mock_price,
            patch("engine.main.dispose_subtensor"),
            patch("engine.main.dispose_engine"),
            patch("engine.main.close_redis"),
        ):
            async with lifespan(mock_app):  # type: ignore[arg-type]
                job = scheduler.get_job("metagraph_sync")
                assert job is not None
                assert job.name == "Metagraph Sync Pipeline"
                assert hasattr(job.trigger, "interval")

    @pytest.mark.asyncio
    async def test_scheduler_uses_configured_interval(self) -> None:
        """Verify scheduler uses settings.metagraph_sync_interval_seconds."""
        from engine.main import lifespan

        with (
            patch("engine.main.settings") as mock_settings,
            patch("engine.main.run_metagraph_sync_cycle"),
            patch("engine.main.run_price_sync_cycle"),
            patch("engine.main.run_taostats_backfill"),
            patch("engine.main.dispose_subtensor"),
            patch("engine.main.dispose_engine"),
            patch("engine.main.close_redis"),
        ):
            mock_settings.debug = True
            mock_settings.host = "0.0.0.0"
            mock_settings.port = 8000
            mock_settings.metagraph_sync_interval_seconds = 60
            mock_settings.price_sync_interval_seconds = 120
            mock_settings.taostats_backfill_hour_utc = 3

            async with lifespan(None):  # type: ignore[arg-type]
                job = scheduler.get_job("metagraph_sync")
                assert job is not None
                assert job.trigger.interval.total_seconds() == 60

    @pytest.mark.asyncio
    async def test_price_sync_job_registered(self) -> None:
        """Verify price_sync job is registered after lifespan startup."""
        from engine.main import lifespan

        mock_app = None

        with (
            patch("engine.main.run_metagraph_sync_cycle"),
            patch("engine.main.run_price_sync_cycle"),
            patch("engine.main.run_taostats_backfill"),
            patch("engine.main.dispose_subtensor"),
            patch("engine.main.dispose_engine"),
            patch("engine.main.close_redis"),
        ):
            async with lifespan(mock_app):  # type: ignore[arg-type]
                job = scheduler.get_job("price_sync")
                assert job is not None
                assert job.name == "Alpha Token Price Tracker"
                assert hasattr(job.trigger, "interval")

    @pytest.mark.asyncio
    async def test_price_sync_uses_configured_interval(self) -> None:
        """Verify price sync scheduler uses settings.price_sync_interval_seconds."""
        from engine.main import lifespan

        with (
            patch("engine.main.settings") as mock_settings,
            patch("engine.main.run_metagraph_sync_cycle"),
            patch("engine.main.run_price_sync_cycle"),
            patch("engine.main.run_taostats_backfill"),
            patch("engine.main.dispose_subtensor"),
            patch("engine.main.dispose_engine"),
            patch("engine.main.close_redis"),
        ):
            mock_settings.debug = True
            mock_settings.host = "0.0.0.0"
            mock_settings.port = 8000
            mock_settings.metagraph_sync_interval_seconds = 120
            mock_settings.price_sync_interval_seconds = 90
            mock_settings.taostats_backfill_hour_utc = 3

            async with lifespan(None):  # type: ignore[arg-type]
                job = scheduler.get_job("price_sync")
                assert job is not None
                assert job.trigger.interval.total_seconds() == 90

    @pytest.mark.asyncio
    async def test_taostats_backfill_job_registered(self) -> None:
        """Verify taostats_backfill job is registered after lifespan startup."""
        from engine.main import lifespan

        with (
            patch("engine.main.run_metagraph_sync_cycle"),
            patch("engine.main.run_price_sync_cycle"),
            patch("engine.main.run_taostats_backfill"),
            patch("engine.main.dispose_subtensor"),
            patch("engine.main.dispose_engine"),
            patch("engine.main.close_redis"),
        ):
            async with lifespan(None):  # type: ignore[arg-type]
                job = scheduler.get_job("taostats_backfill")
                assert job is not None
                assert job.name == "Taostats Historical Backfill"

    @pytest.mark.asyncio
    async def test_taostats_backfill_uses_cron_trigger(self) -> None:
        """Verify backfill uses cron trigger at configured hour."""
        from engine.main import lifespan

        with (
            patch("engine.main.settings") as mock_settings,
            patch("engine.main.run_metagraph_sync_cycle"),
            patch("engine.main.run_price_sync_cycle"),
            patch("engine.main.run_taostats_backfill"),
            patch("engine.main.dispose_subtensor"),
            patch("engine.main.dispose_engine"),
            patch("engine.main.close_redis"),
        ):
            mock_settings.debug = True
            mock_settings.host = "0.0.0.0"
            mock_settings.port = 8000
            mock_settings.metagraph_sync_interval_seconds = 120
            mock_settings.price_sync_interval_seconds = 120
            mock_settings.taostats_backfill_hour_utc = 4

            async with lifespan(None):  # type: ignore[arg-type]
                job = scheduler.get_job("taostats_backfill")
                assert job is not None
                # CronTrigger doesn't have .interval — check it's a cron type
                from apscheduler.triggers.cron import CronTrigger

                assert isinstance(job.trigger, CronTrigger)
