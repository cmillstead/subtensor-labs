"""Tests for coldkey → positions resolver."""

from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

from engine.portfolio.resolver import (
    _query_chain_positions,
    _query_db_positions,
    resolve_coldkey_positions,
)

COLDKEY = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
HOTKEY_1 = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"
HOTKEY_2 = "5DAAnrj7VHTznn2AWBemMuyBwZWs6FNFjdyVXUeYum3PTXFy"


def _mock_metagraph(
    coldkeys: list[str], hotkeys: list[str], stakes: list[float]
) -> SimpleNamespace:
    """Create a mock metagraph with SimpleNamespace (not MagicMock)."""
    n = len(coldkeys)
    return SimpleNamespace(
        n=n,
        coldkeys=coldkeys,
        hotkeys=hotkeys,
        stake=stakes,
        incentive=[0.5] * n,
        trust=[0.9] * n,
        dividends=[0.1] * n,
        active=[True] * n,
    )


class TestQueryDbPositions:
    async def test_returns_entries_for_coldkey(self) -> None:
        """Test that DB query returns entries matching the coldkey."""
        mock_session = AsyncMock()

        mock_entry = SimpleNamespace(
            netuid=1, uid=0, hotkey=HOTKEY_1, coldkey=COLDKEY,
            stake=100.0, incentive=0.5, trust=0.9, dividends=0.1, is_active=True,
        )
        # scalars() returns a sync object, .all() returns a list
        mock_scalars = SimpleNamespace(all=lambda: [mock_entry])
        mock_result = SimpleNamespace(scalars=lambda: mock_scalars)
        mock_session.execute.return_value = mock_result

        entries = await _query_db_positions(COLDKEY, mock_session)
        assert len(entries) == 1
        assert entries[0]["hotkey"] == HOTKEY_1
        assert entries[0]["stake"] == 100.0

    async def test_returns_empty_for_unknown_coldkey(self) -> None:
        """Test that DB query returns empty list for unknown coldkey."""
        mock_session = AsyncMock()
        mock_scalars = SimpleNamespace(all=lambda: [])
        mock_result = SimpleNamespace(scalars=lambda: mock_scalars)
        mock_session.execute.return_value = mock_result

        entries = await _query_db_positions("5Unknown", mock_session)
        assert entries == []

    async def test_multiple_subnets(self) -> None:
        """Test DB query returns entries from multiple subnets."""
        mock_session = AsyncMock()
        entries_data = [
            SimpleNamespace(
                netuid=1, uid=0, hotkey=HOTKEY_1, coldkey=COLDKEY,
                stake=100.0, incentive=0.5, trust=0.9, dividends=0.1, is_active=True,
            ),
            SimpleNamespace(
                netuid=2, uid=5, hotkey=HOTKEY_2, coldkey=COLDKEY,
                stake=200.0, incentive=0.3, trust=0.8, dividends=0.2, is_active=True,
            ),
        ]
        mock_scalars = SimpleNamespace(all=lambda: entries_data)
        mock_result = SimpleNamespace(scalars=lambda: mock_scalars)
        mock_session.execute.return_value = mock_result

        entries = await _query_db_positions(COLDKEY, mock_session)
        assert len(entries) == 2
        assert entries[0]["netuid"] == 1
        assert entries[1]["netuid"] == 2


class TestQueryChainPositions:
    @patch("engine.portfolio.resolver.sync_subnet_metagraph")
    @patch("engine.portfolio.resolver.get_active_subnet_netuids")
    async def test_finds_positions_on_chain(
        self, mock_netuids: AsyncMock, mock_sync: AsyncMock
    ) -> None:
        mock_netuids.return_value = [1]
        mock_sync.return_value = _mock_metagraph(
            coldkeys=[COLDKEY, "5Other"],
            hotkeys=[HOTKEY_1, HOTKEY_2],
            stakes=[100.0, 50.0],
        )

        entries = await _query_chain_positions(COLDKEY)
        assert len(entries) == 1
        assert entries[0]["hotkey"] == HOTKEY_1
        assert entries[0]["stake"] == 100.0

    @patch("engine.portfolio.resolver.sync_subnet_metagraph")
    @patch("engine.portfolio.resolver.get_active_subnet_netuids")
    async def test_returns_empty_when_coldkey_not_found(
        self, mock_netuids: AsyncMock, mock_sync: AsyncMock
    ) -> None:
        mock_netuids.return_value = [1]
        mock_sync.return_value = _mock_metagraph(
            coldkeys=["5Other1", "5Other2"],
            hotkeys=[HOTKEY_1, HOTKEY_2],
            stakes=[100.0, 50.0],
        )

        entries = await _query_chain_positions(COLDKEY)
        assert entries == []

    @patch("engine.portfolio.resolver.sync_subnet_metagraph")
    @patch("engine.portfolio.resolver.get_active_subnet_netuids")
    async def test_handles_subnet_failure_gracefully(
        self, mock_netuids: AsyncMock, mock_sync: AsyncMock
    ) -> None:
        mock_netuids.return_value = [1, 2]
        # Subnet 1 fails, subnet 2 succeeds
        mock_sync.side_effect = [
            Exception("chain error"),
            _mock_metagraph(
                coldkeys=[COLDKEY],
                hotkeys=[HOTKEY_1],
                stakes=[200.0],
            ),
        ]

        entries = await _query_chain_positions(COLDKEY)
        assert len(entries) == 1
        assert entries[0]["netuid"] == 2

    @patch("engine.portfolio.resolver.get_active_subnet_netuids")
    async def test_handles_discovery_failure(self, mock_netuids: AsyncMock) -> None:
        mock_netuids.side_effect = Exception("discovery failed")
        entries = await _query_chain_positions(COLDKEY)
        assert entries == []

    @patch("engine.portfolio.resolver.sync_subnet_metagraph")
    @patch("engine.portfolio.resolver.get_active_subnet_netuids")
    async def test_multiple_subnets_chain(
        self, mock_netuids: AsyncMock, mock_sync: AsyncMock
    ) -> None:
        mock_netuids.return_value = [1, 2]
        mock_sync.side_effect = [
            _mock_metagraph(
                coldkeys=[COLDKEY, "5Other"],
                hotkeys=[HOTKEY_1, HOTKEY_2],
                stakes=[100.0, 50.0],
            ),
            _mock_metagraph(
                coldkeys=["5Other", COLDKEY],
                hotkeys=[HOTKEY_2, HOTKEY_1],
                stakes=[30.0, 200.0],
            ),
        ]

        entries = await _query_chain_positions(COLDKEY)
        assert len(entries) == 2


class TestResolveColdkeyPositions:
    @patch("engine.portfolio.resolver._get_latest_prices")
    @patch("engine.portfolio.resolver._query_db_positions")
    @patch("engine.portfolio.resolver.get_session_factory")
    async def test_db_path(
        self, mock_factory: AsyncMock, mock_db_query: AsyncMock, mock_prices: AsyncMock
    ) -> None:
        """Test resolution via DB path (no chain fallback)."""
        mock_session = AsyncMock()
        mock_factory.return_value.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_db_query.return_value = [
            {
                "netuid": 1, "uid": 0, "hotkey": HOTKEY_1, "coldkey": COLDKEY,
                "stake": 100.0, "incentive": 0.5, "trust": 0.9,
                "dividends": 0.1, "is_active": True, "emission_share": 0.0,
            },
        ]
        mock_prices.return_value = {1: 2.0}

        result = await resolve_coldkey_positions(COLDKEY)
        assert result.coldkey == COLDKEY
        assert len(result.positions) == 1
        assert result.total_staked_tao == 100.0
        assert result.total_alpha_value_tao == 200.0
        assert result.total_value_tao == 300.0
        assert result.subnets_exposed == 1

    @patch("engine.portfolio.resolver._query_chain_positions")
    @patch("engine.portfolio.resolver._get_latest_prices")
    @patch("engine.portfolio.resolver._query_db_positions")
    @patch("engine.portfolio.resolver.get_session_factory")
    async def test_chain_fallback(
        self, mock_factory: AsyncMock, mock_db_query: AsyncMock,
        mock_prices: AsyncMock, mock_chain: AsyncMock
    ) -> None:
        """Test that chain fallback is used when DB returns empty."""
        mock_session = AsyncMock()
        mock_factory.return_value.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_db_query.return_value = []  # No DB data
        mock_chain.return_value = [
            {
                "netuid": 1, "uid": 0, "hotkey": HOTKEY_1, "coldkey": COLDKEY,
                "stake": 50.0, "incentive": 0.0, "trust": 0.0,
                "dividends": 0.0, "is_active": True, "emission_share": 0.0,
            },
        ]
        mock_prices.return_value = {}

        result = await resolve_coldkey_positions(COLDKEY)
        assert len(result.positions) == 1
        mock_chain.assert_called_once_with(COLDKEY)

    @patch("engine.portfolio.resolver._get_latest_prices")
    @patch("engine.portfolio.resolver._query_db_positions")
    @patch("engine.portfolio.resolver.get_session_factory")
    async def test_empty_coldkey_returns_empty_positions(
        self, mock_factory: AsyncMock, mock_db_query: AsyncMock, mock_prices: AsyncMock
    ) -> None:
        """Test that unknown coldkey returns empty positions (not error)."""
        mock_session = AsyncMock()
        mock_factory.return_value.return_value.__aenter__ = AsyncMock(return_value=mock_session)
        mock_factory.return_value.return_value.__aexit__ = AsyncMock(return_value=False)

        mock_db_query.return_value = []
        mock_prices.return_value = {}

        with patch("engine.portfolio.resolver._query_chain_positions", return_value=[]):
            result = await resolve_coldkey_positions(COLDKEY)

        assert result.positions == []
        assert result.total_value_tao == 0.0
        assert result.subnets_exposed == 0
