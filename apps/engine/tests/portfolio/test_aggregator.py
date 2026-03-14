"""Tests for multi-address portfolio aggregation."""

from unittest.mock import AsyncMock, patch

from engine.portfolio.aggregator import (
    _deserialize_coldkey_portfolio,
    _merge_positions,
    _serialize_coldkey_portfolio,
    aggregate_portfolio,
)
from engine.schemas.portfolio import (
    ColdkeyPortfolioSchema,
    SubnetPositionSchema,
)

COLDKEY_1 = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
COLDKEY_2 = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
HOTKEY_1 = "5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum3PTXFy"
HOTKEY_2 = "5HGjWAeFDfFCWPsjFQdVV2Msvz2XtMktvgocEZcCj68kUMaw"


def _pos(
    netuid: int = 1,
    hotkey: str = HOTKEY_1,
    staked: float = 100.0,
    alpha: float = 50.0,
) -> SubnetPositionSchema:
    return SubnetPositionSchema(
        netuid=netuid,
        hotkey=hotkey,
        staked_tao=staked,
        alpha_value_tao=alpha,
        emission_share=0.05,
        incentive=0.0,
        trust=0.9,
        dividends=0.1,
        is_active=True,
        is_miner=False,
    )


def _coldkey_portfolio(
    coldkey: str = COLDKEY_1,
    positions: list[SubnetPositionSchema] | None = None,
) -> ColdkeyPortfolioSchema:
    if positions is None:
        positions = [_pos()]
    staked = sum(p.staked_tao for p in positions)
    alpha = sum(p.alpha_value_tao for p in positions)
    netuids = {p.netuid for p in positions}
    return ColdkeyPortfolioSchema(
        coldkey=coldkey,
        total_value_tao=staked + alpha,
        total_staked_tao=staked,
        total_alpha_value_tao=alpha,
        positions=positions,
        subnets_exposed=len(netuids),
    )


class TestSerializationRoundtrip:
    def test_serialize_deserialize(self) -> None:
        original = _coldkey_portfolio()
        serialized = _serialize_coldkey_portfolio(original)
        restored = _deserialize_coldkey_portfolio(serialized)
        assert restored.coldkey == original.coldkey
        assert restored.total_value_tao == original.total_value_tao
        assert len(restored.positions) == len(original.positions)

    def test_empty_positions(self) -> None:
        original = _coldkey_portfolio(positions=[])
        serialized = _serialize_coldkey_portfolio(original)
        restored = _deserialize_coldkey_portfolio(serialized)
        assert restored.positions == []


class TestMergePositions:
    def test_single_coldkey_no_dedup(self) -> None:
        result = _coldkey_portfolio(positions=[_pos(netuid=1), _pos(netuid=2, hotkey=HOTKEY_2)])
        merged = _merge_positions([result])
        assert len(merged) == 2

    def test_deduplication_same_hotkey(self) -> None:
        """Same hotkey in same subnet across two coldkeys should be deduplicated."""
        result1 = _coldkey_portfolio(
            coldkey=COLDKEY_1,
            positions=[_pos(netuid=1, hotkey=HOTKEY_1, staked=100.0)],
        )
        result2 = _coldkey_portfolio(
            coldkey=COLDKEY_2,
            positions=[_pos(netuid=1, hotkey=HOTKEY_1, staked=100.0)],  # Same hotkey+netuid
        )
        merged = _merge_positions([result1, result2])
        assert len(merged) == 1  # Deduplicated

    def test_different_hotkeys_kept(self) -> None:
        """Different hotkeys should not be deduplicated."""
        result1 = _coldkey_portfolio(
            coldkey=COLDKEY_1,
            positions=[_pos(netuid=1, hotkey=HOTKEY_1)],
        )
        result2 = _coldkey_portfolio(
            coldkey=COLDKEY_2,
            positions=[_pos(netuid=1, hotkey=HOTKEY_2)],
        )
        merged = _merge_positions([result1, result2])
        assert len(merged) == 2

    def test_same_hotkey_different_subnets_kept(self) -> None:
        """Same hotkey in different subnets should both be kept."""
        result = _coldkey_portfolio(
            positions=[
                _pos(netuid=1, hotkey=HOTKEY_1),
                _pos(netuid=2, hotkey=HOTKEY_1),
            ],
        )
        merged = _merge_positions([result])
        assert len(merged) == 2

    def test_empty_results(self) -> None:
        merged = _merge_positions([])
        assert merged == []


class TestAggregatePortfolio:
    @patch("engine.portfolio.aggregator.cache_set", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.resolve_coldkey_positions", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.cache_get", new_callable=AsyncMock)
    async def test_cache_miss_resolves_and_caches(
        self, mock_cache_get: AsyncMock, mock_resolve: AsyncMock, mock_cache_set: AsyncMock
    ) -> None:
        mock_cache_get.return_value = None  # Cache miss
        mock_resolve.return_value = _coldkey_portfolio()

        response, cache_hit = await aggregate_portfolio([COLDKEY_1])
        assert cache_hit is False
        assert response.total_value_tao == 150.0
        mock_resolve.assert_called_once_with(COLDKEY_1)
        mock_cache_set.assert_called_once()

    @patch("engine.portfolio.aggregator.resolve_coldkey_positions", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.cache_get", new_callable=AsyncMock)
    async def test_cache_hit_skips_resolution(
        self, mock_cache_get: AsyncMock, mock_resolve: AsyncMock
    ) -> None:
        portfolio = _coldkey_portfolio()
        mock_cache_get.return_value = _serialize_coldkey_portfolio(portfolio)

        response, cache_hit = await aggregate_portfolio([COLDKEY_1])
        assert cache_hit is True
        mock_resolve.assert_not_called()

    @patch("engine.portfolio.aggregator.cache_set", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.resolve_coldkey_positions", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.cache_get", new_callable=AsyncMock)
    async def test_multi_address_merge(
        self, mock_cache_get: AsyncMock, mock_resolve: AsyncMock, mock_cache_set: AsyncMock
    ) -> None:
        mock_cache_get.return_value = None
        mock_resolve.side_effect = [
            _coldkey_portfolio(coldkey=COLDKEY_1, positions=[_pos(netuid=1, hotkey=HOTKEY_1)]),
            _coldkey_portfolio(coldkey=COLDKEY_2, positions=[_pos(netuid=2, hotkey=HOTKEY_2)]),
        ]

        response, _ = await aggregate_portfolio([COLDKEY_1, COLDKEY_2])
        assert response.coldkeys_resolved == 2
        assert len(response.positions) == 2
        assert response.subnets_exposed == 2

    @patch("engine.portfolio.aggregator.cache_set", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.resolve_coldkey_positions", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.cache_get", new_callable=AsyncMock)
    async def test_multi_address_deduplication(
        self, mock_cache_get: AsyncMock, mock_resolve: AsyncMock, mock_cache_set: AsyncMock
    ) -> None:
        mock_cache_get.return_value = None
        # Both coldkeys have the same hotkey in the same subnet
        mock_resolve.side_effect = [
            _coldkey_portfolio(coldkey=COLDKEY_1, positions=[_pos(netuid=1, hotkey=HOTKEY_1)]),
            _coldkey_portfolio(coldkey=COLDKEY_2, positions=[_pos(netuid=1, hotkey=HOTKEY_1)]),
        ]

        response, _ = await aggregate_portfolio([COLDKEY_1, COLDKEY_2])
        assert len(response.positions) == 1  # Deduplicated

    @patch("engine.portfolio.aggregator.cache_set", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.resolve_coldkey_positions", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.cache_get", new_callable=AsyncMock)
    async def test_cache_read_failure_falls_through(
        self, mock_cache_get: AsyncMock, mock_resolve: AsyncMock, mock_cache_set: AsyncMock
    ) -> None:
        mock_cache_get.side_effect = Exception("Redis down")
        mock_resolve.return_value = _coldkey_portfolio()

        response, cache_hit = await aggregate_portfolio([COLDKEY_1])
        assert cache_hit is False
        assert response.total_value_tao == 150.0

    @patch("engine.portfolio.aggregator.cache_set", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.resolve_coldkey_positions", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.cache_get", new_callable=AsyncMock)
    async def test_cache_write_failure_non_fatal(
        self, mock_cache_get: AsyncMock, mock_resolve: AsyncMock, mock_cache_set: AsyncMock
    ) -> None:
        mock_cache_get.return_value = None
        mock_resolve.return_value = _coldkey_portfolio()
        mock_cache_set.side_effect = Exception("Redis down")

        response, cache_hit = await aggregate_portfolio([COLDKEY_1])
        assert response.total_value_tao == 150.0  # Still works

    @patch("engine.portfolio.aggregator.cache_set", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.resolve_coldkey_positions", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.cache_get", new_callable=AsyncMock)
    async def test_empty_positions_response(
        self, mock_cache_get: AsyncMock, mock_resolve: AsyncMock, mock_cache_set: AsyncMock
    ) -> None:
        mock_cache_get.return_value = None
        mock_resolve.return_value = _coldkey_portfolio(positions=[])

        response, _ = await aggregate_portfolio([COLDKEY_1])
        assert response.positions == []
        assert response.total_value_tao == 0.0
        assert response.subnets_exposed == 0

    @patch("engine.portfolio.aggregator.resolve_coldkey_positions", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.cache_get", new_callable=AsyncMock)
    async def test_partial_cache_hit(
        self, mock_cache_get: AsyncMock, mock_resolve: AsyncMock
    ) -> None:
        """One coldkey cached, one not — cache_hit should be False."""
        portfolio1 = _coldkey_portfolio(coldkey=COLDKEY_1, positions=[_pos(netuid=1)])
        mock_cache_get.side_effect = [
            _serialize_coldkey_portfolio(portfolio1),  # Cache hit for coldkey 1
            None,  # Cache miss for coldkey 2
        ]
        mock_resolve.return_value = _coldkey_portfolio(
            coldkey=COLDKEY_2, positions=[_pos(netuid=2, hotkey=HOTKEY_2)]
        )

        response, cache_hit = await aggregate_portfolio([COLDKEY_1, COLDKEY_2])
        assert cache_hit is False
        assert response.coldkeys_resolved == 2

    @patch("engine.portfolio.aggregator.resolve_coldkey_positions", new_callable=AsyncMock)
    @patch("engine.portfolio.aggregator.cache_get", new_callable=AsyncMock)
    async def test_response_has_last_updated(
        self, mock_cache_get: AsyncMock, mock_resolve: AsyncMock
    ) -> None:
        mock_cache_get.return_value = None
        mock_resolve.return_value = _coldkey_portfolio(positions=[])

        response, _ = await aggregate_portfolio([COLDKEY_1])
        assert response.last_updated  # Non-empty ISO timestamp
