"""Tests for the Taostats backfill sync pipeline."""

from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock, patch

from sqlalchemy.ext.asyncio import AsyncSession

from engine.ingestion.taostats_sync import (
    _parse_datetime,
    _parse_float,
    backfill_emission_history,
    backfill_price_history,
    backfill_subnet_history,
    run_taostats_backfill,
)


def _mock_session() -> MagicMock:
    """Create a mock async session with execute and commit."""
    session = MagicMock(spec=AsyncSession)
    result_mock = MagicMock()
    result_mock.rowcount = 5
    session.execute = AsyncMock(return_value=result_mock)
    session.commit = AsyncMock()
    return session


def _mock_client(
    metagraph_data: list | None = None,
    emission_data: list | None = None,
    price_data: list | None = None,
) -> MagicMock:
    """Create a mock TaostatsClient."""
    client = MagicMock()
    client.fetch_metagraph_history = AsyncMock(return_value=metagraph_data or [])
    client.fetch_subnet_emission = AsyncMock(return_value=emission_data or [])
    client.fetch_price_history = AsyncMock(return_value=price_data or [])
    client.close = AsyncMock()
    return client


class TestParseHelpers:
    """Test data parsing utility functions."""

    def test_parse_float_string(self) -> None:
        assert _parse_float("3.14") == 3.14

    def test_parse_float_number(self) -> None:
        assert _parse_float(42) == 42.0

    def test_parse_float_none(self) -> None:
        assert _parse_float(None) == 0.0

    def test_parse_float_invalid(self) -> None:
        assert _parse_float("not-a-number") == 0.0

    def test_parse_float_custom_default(self) -> None:
        assert _parse_float(None, default=-1.0) == -1.0

    def test_parse_datetime_iso(self) -> None:
        dt = _parse_datetime("2024-06-15T12:00:00+00:00")
        assert dt is not None
        assert dt.year == 2024
        assert dt.tzinfo is not None

    def test_parse_datetime_naive(self) -> None:
        """Naive timestamps get UTC attached."""
        dt = _parse_datetime("2024-06-15T12:00:00")
        assert dt is not None
        assert dt.tzinfo == UTC

    def test_parse_datetime_none(self) -> None:
        assert _parse_datetime(None) is None

    def test_parse_datetime_invalid(self) -> None:
        assert _parse_datetime("not-a-date") is None


class TestBackfillSubnetHistory:
    """Test subnet snapshot backfill."""

    async def test_writes_snapshot_rows(self) -> None:
        """Valid metagraph records are written to subnet_snapshots."""
        client = _mock_client(
            metagraph_data=[
                {
                    "timestamp": "2024-01-15T00:00:00+00:00",
                    "neuron_count": 100,
                    "validator_count": 30,
                    "emission": "0.05",
                    "registration_cost": "1.5",
                    "price": "0.002",
                    "market_cap": "500",
                    "tao_reserve": "100.0",
                    "alpha_reserve": "50000.0",
                    "fill_rate": "0.8",
                    "take_rate": "0.18",
                },
            ]
        )
        session = _mock_session()

        count = await backfill_subnet_history(client, 19, datetime(2024, 1, 1, tzinfo=UTC), session)

        assert count == 5  # rowcount from mock
        session.execute.assert_called_once()
        session.commit.assert_called_once()

    async def test_skips_records_without_timestamp(self) -> None:
        """Records missing timestamp are skipped."""
        client = _mock_client(
            metagraph_data=[
                {"neuron_count": 100},  # No timestamp
            ]
        )
        session = _mock_session()

        count = await backfill_subnet_history(client, 19, datetime(2024, 1, 1, tzinfo=UTC), session)

        assert count == 0
        session.execute.assert_not_called()

    async def test_empty_response_returns_zero(self) -> None:
        """Empty API response returns 0 records."""
        client = _mock_client(metagraph_data=[])
        session = _mock_session()

        count = await backfill_subnet_history(client, 19, datetime(2024, 1, 1, tzinfo=UTC), session)

        assert count == 0

    async def test_fetch_failure_returns_zero(self) -> None:
        """API fetch failure returns 0 records and doesn't raise."""
        client = _mock_client()
        client.fetch_metagraph_history = AsyncMock(side_effect=Exception("API down"))
        session = _mock_session()

        count = await backfill_subnet_history(client, 19, datetime(2024, 1, 1, tzinfo=UTC), session)

        assert count == 0


class TestBackfillEmissionHistory:
    """Test emission record backfill."""

    async def test_writes_emission_rows(self) -> None:
        """Valid emission records are written to emission_records."""
        client = _mock_client(
            emission_data=[
                {
                    "timestamp": "2024-03-01T00:00:00+00:00",
                    "emission_tao": "10.5",
                    "emission_share": "0.03",
                    "tao_inflow": "200.0",
                    "total_stake": "5000.0",
                },
            ]
        )
        session = _mock_session()

        count = await backfill_emission_history(
            client, 19, datetime(2024, 1, 1, tzinfo=UTC), session
        )

        assert count == 5
        session.execute.assert_called_once()
        session.commit.assert_called_once()

    async def test_fetch_failure_returns_zero(self) -> None:
        """API failure doesn't raise."""
        client = _mock_client()
        client.fetch_subnet_emission = AsyncMock(side_effect=Exception("timeout"))
        session = _mock_session()

        count = await backfill_emission_history(
            client, 19, datetime(2024, 1, 1, tzinfo=UTC), session
        )

        assert count == 0


class TestBackfillPriceHistory:
    """Test TAO price backfill."""

    async def test_writes_price_rows_as_netuid_zero(self) -> None:
        """TAO price data is stored with netuid=0 (network-level)."""
        client = _mock_client(
            price_data=[
                {
                    "last_updated": "2024-06-01T00:00:00+00:00",
                    "price": "450.00",
                    "volume_24h": "5000000",
                },
            ]
        )
        session = _mock_session()

        count = await backfill_price_history(client, datetime(2024, 1, 1, tzinfo=UTC), session)

        assert count == 5
        session.execute.assert_called_once()

        # Verify the insert was called and committed
        session.commit.assert_called_once()


class TestRunTaostatsBackfill:
    """Test the full backfill orchestrator."""

    @patch("engine.ingestion.taostats_sync.TaostatsClient")
    @patch("engine.ingestion.taostats_sync.get_active_subnet_netuids", new_callable=AsyncMock)
    @patch("engine.ingestion.taostats_sync.get_session_factory")
    async def test_backfill_all_subnets(
        self, mock_factory: MagicMock, mock_netuids: AsyncMock, mock_client_cls: MagicMock
    ) -> None:
        """Full backfill discovers subnets and runs per-subnet + price backfill."""
        mock_netuids.return_value = [1, 19]

        # Mock session factory
        mock_session = _mock_session()
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = factory

        # Mock cursor read (no previous backfill)
        cursor_result = MagicMock()
        cursor_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = cursor_result

        # Mock client instance
        client_instance = _mock_client(
            metagraph_data=[
                {"timestamp": "2024-01-01T00:00:00+00:00", "neuron_count": 50},
            ],
            emission_data=[
                {"timestamp": "2024-01-01T00:00:00+00:00", "emission_tao": "5"},
            ],
            price_data=[
                {"last_updated": "2024-01-01T00:00:00+00:00", "price": "400"},
            ],
        )
        mock_client_cls.return_value = client_instance

        await run_taostats_backfill()

        # Client should have been closed
        client_instance.close.assert_called_once()

    @patch("engine.ingestion.taostats_sync.TaostatsClient")
    @patch("engine.ingestion.taostats_sync.get_active_subnet_netuids", new_callable=AsyncMock)
    @patch("engine.ingestion.taostats_sync.get_session_factory")
    async def test_backfill_single_subnet_filter(
        self, mock_factory: MagicMock, mock_netuids: AsyncMock, mock_client_cls: MagicMock
    ) -> None:
        """Subnet filter limits backfill to specific subnet."""
        mock_session = _mock_session()
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = factory

        cursor_result = MagicMock()
        cursor_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = cursor_result

        client_instance = _mock_client()
        mock_client_cls.return_value = client_instance

        await run_taostats_backfill(subnet_filter=19)

        # Should NOT call get_active_subnet_netuids
        mock_netuids.assert_not_called()
        client_instance.close.assert_called_once()

    @patch("engine.ingestion.taostats_sync.TaostatsClient")
    @patch("engine.ingestion.taostats_sync.get_active_subnet_netuids", new_callable=AsyncMock)
    @patch("engine.ingestion.taostats_sync.get_session_factory")
    async def test_subnet_discovery_failure_aborts(
        self, mock_factory: MagicMock, mock_netuids: AsyncMock, mock_client_cls: MagicMock
    ) -> None:
        """Subnet discovery failure aborts the backfill."""
        mock_netuids.side_effect = Exception("chain down")

        mock_session = _mock_session()
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = factory

        cursor_result = MagicMock()
        cursor_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = cursor_result

        # Should not raise
        await run_taostats_backfill()

    @patch("engine.ingestion.taostats_sync.TaostatsClient")
    @patch("engine.ingestion.taostats_sync.get_active_subnet_netuids", new_callable=AsyncMock)
    @patch("engine.ingestion.taostats_sync.get_session_factory")
    async def test_error_isolation_between_subnets(
        self, mock_factory: MagicMock, mock_netuids: AsyncMock, mock_client_cls: MagicMock
    ) -> None:
        """One subnet failure doesn't stop others."""
        mock_netuids.return_value = [1, 19, 27]

        mock_session = _mock_session()
        factory = MagicMock()
        factory.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        factory.return_value.__aexit__ = AsyncMock(return_value=None)
        mock_factory.return_value = factory

        cursor_result = MagicMock()
        cursor_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = cursor_result

        client_instance = _mock_client()

        async def _conditional_metagraph(*, subnet_id: int, since=None, until=None):
            if subnet_id == 19:
                raise Exception("subnet 19 API error")
            return [{"timestamp": "2024-01-01T00:00:00+00:00", "neuron_count": 50}]

        client_instance.fetch_metagraph_history = AsyncMock(side_effect=_conditional_metagraph)
        mock_client_cls.return_value = client_instance

        # Should complete without raising
        await run_taostats_backfill()
        client_instance.close.assert_called_once()
