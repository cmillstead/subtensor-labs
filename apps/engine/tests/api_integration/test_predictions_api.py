"""Integration tests for prediction API endpoints — real database, no mocks."""

from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.fixture
async def seed_emission_data(db_engine):
    """Seed emission_records, metagraph_entries, and subnet_snapshots with
    30 days of data for netuids 1 and 3, plus a user with stake.
    """
    base_time = datetime.now(UTC) - timedelta(days=30)

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        # Emission records — 30 days of increasing emission for SN1
        for i in range(30):
            t = base_time + timedelta(days=i)
            await session.execute(
                text(
                    "INSERT INTO emission_records"
                    " (time, netuid, emission_tao,"
                    " emission_share_pct, net_tao_inflow,"
                    " cumulative_stake)"
                    " VALUES (:t, :netuid, :emission_tao,"
                    " :emission_share_pct, :net_tao_inflow,"
                    " :cumulative_stake)"
                ),
                {
                    "t": t,
                    "netuid": 1,
                    "emission_tao": 10.0 + i * 0.1,
                    "emission_share_pct": 5.0 + i * 0.05,
                    "net_tao_inflow": 50.0 + i,
                    "cumulative_stake": 1000.0 + i * 10,
                },
            )

        # Subnet snapshots — latest for SN1 (owner_take_rate)
        await session.execute(
            text("""
                INSERT INTO subnet_snapshots
                    (time, netuid, miner_count, validator_count, emission_share,
                     registration_cost, alpha_price, alpha_market_cap,
                     tao_reserves, alpha_reserves, fill_rate, owner_take_rate)
                VALUES (NOW(), 1, 100, 50, 0.065, 1.5, 0.12, 1200.0, 500.0, 4000.0, 0.78, 0.10)
            """)
        )

        # Metagraph entries — user's stake on SN1
        await session.execute(
            text(
                "INSERT INTO metagraph_entries"
                " (time, netuid, uid, hotkey, coldkey,"
                " stake, incentive, trust, dividends,"
                " is_active)"
                " VALUES"
                " (NOW(), 1, 0,"
                " '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY',"
                " '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY',"
                " 200.0, 0.5, 0.8, 0.3, true)"
            )
        )

        await session.commit()

    return {
        "address": "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
        "netuid": 1,
        "stake": 200.0,
    }


class TestYieldProjectionEndpoint:
    """Integration tests for POST /engine/predictions/yield."""

    async def test_returns_200_with_projection_data(
        self, client: AsyncClient, seed_emission_data: dict
    ) -> None:
        """Should compute real projections from seeded emission data."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": [seed_emission_data["address"]],
                "horizons": [30],
            },
        )
        assert response.status_code == 200
        body = response.json()

        assert "data" in body
        assert "meta" in body
        assert body["meta"]["compute_ms"] >= 0

        data = body["data"]
        assert data["subnets_analyzed"] == 1
        assert data["total_staked_tao"] == pytest.approx(200.0)
        assert len(data["projections"]) == 1
        assert data["projections"][0]["horizon_days"] == 30
        assert data["projections"][0]["total_projected_yield_tao"] > 0

    async def test_returns_chart_data(self, client: AsyncClient, seed_emission_data: dict) -> None:
        """Should return daily chart data points up to the max horizon."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": [seed_emission_data["address"]],
                "horizons": [30, 60],
            },
        )
        body = response.json()
        chart_data = body["data"]["chart_data"]

        assert len(chart_data) == 60  # max horizon
        assert chart_data[0]["day"] == 1
        assert chart_data[-1]["day"] == 60
        # Confidence bands should exist
        assert "confidence_68_lower" in chart_data[0]
        assert "confidence_95_upper" in chart_data[0]

    async def test_returns_caveat(self, client: AsyncClient, seed_emission_data: dict) -> None:
        """Response always includes the caveat text."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": [seed_emission_data["address"]],
                "horizons": [30],
            },
        )
        body = response.json()
        assert "Not financial advice" in body["data"]["caveat"]

    async def test_envelope_format(self, client: AsyncClient, seed_emission_data: dict) -> None:
        """Response follows {data, meta} envelope format."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": [seed_emission_data["address"]],
                "horizons": [30],
            },
        )
        body = response.json()

        data = body["data"]
        assert "projections" in data
        assert "chart_data" in data
        assert "last_computed" in data
        assert "total_staked_tao" in data
        assert "subnets_analyzed" in data
        assert "subnets_skipped" in data

        meta = body["meta"]
        assert "last_updated" in meta
        assert "compute_ms" in meta
        assert "cache_hit" in meta

    async def test_validates_invalid_addresses(self, client: AsyncClient) -> None:
        """Should reject invalid SS58 addresses."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": ["not-a-valid-address"],
                "horizons": [30],
            },
        )
        assert response.status_code == 422

    async def test_validates_empty_addresses(self, client: AsyncClient) -> None:
        """Should reject empty address list."""
        response = await client.post(
            "/engine/predictions/yield",
            json={"coldkey_addresses": [], "horizons": [30]},
        )
        assert response.status_code == 422

    async def test_validates_invalid_horizons(self, client: AsyncClient) -> None:
        """Should reject invalid horizon values."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": ["5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"],
                "horizons": [15],
            },
        )
        assert response.status_code == 422

    async def test_empty_portfolio_returns_zero(self, client: AsyncClient) -> None:
        """Address with no stake returns zero projections."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": ["5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"],
                "horizons": [30],
            },
        )
        body = response.json()
        assert body["data"]["total_staked_tao"] == 0.0
        assert body["data"]["subnets_analyzed"] == 0

    async def test_default_horizons(self, client: AsyncClient, seed_emission_data: dict) -> None:
        """Should use default horizons [30, 60, 90] if not specified."""
        response = await client.post(
            "/engine/predictions/yield",
            json={"coldkey_addresses": [seed_emission_data["address"]]},
        )
        body = response.json()
        horizons = [p["horizon_days"] for p in body["data"]["projections"]]
        assert horizons == [30, 60, 90]

    async def test_subnet_projection_details(
        self, client: AsyncClient, seed_emission_data: dict
    ) -> None:
        """Subnet projections include all expected fields."""
        response = await client.post(
            "/engine/predictions/yield",
            json={
                "coldkey_addresses": [seed_emission_data["address"]],
                "horizons": [30],
            },
        )
        body = response.json()
        subnet_proj = body["data"]["projections"][0]["subnet_projections"][0]

        assert subnet_proj["netuid"] == 1
        assert subnet_proj["current_stake_tao"] == pytest.approx(200.0)
        assert subnet_proj["projected_yield_tao"] > 0
        assert subnet_proj["r_squared"] > 0
        assert subnet_proj["confidence_68_lower"] < subnet_proj["confidence_68_upper"]
        assert subnet_proj["confidence_95_lower"] < subnet_proj["confidence_95_upper"]
        # 30 days of data → volatility warning (< 60 days)
        assert subnet_proj["has_volatility_warning"] is True

    async def test_cache_hit_on_second_request(
        self, client: AsyncClient, seed_emission_data: dict
    ) -> None:
        """Second identical request should be a cache hit."""
        payload = {
            "coldkey_addresses": [seed_emission_data["address"]],
            "horizons": [30],
        }

        # First request — cache miss
        response1 = await client.post("/engine/predictions/yield", json=payload)
        assert response1.json()["meta"]["cache_hit"] is False

        # Second request — should be cache hit
        response2 = await client.post("/engine/predictions/yield", json=payload)
        assert response2.json()["meta"]["cache_hit"] is True


@pytest.fixture
async def seed_scenario_data(db_engine):
    """Seed data for scenario tests: 2 subnets (SN1, SN3) with emission history + stake."""
    base_time = datetime.now(UTC) - timedelta(days=30)

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        # Emission records for SN1 and SN3 — 30 days
        for i in range(30):
            t = base_time + timedelta(days=i)
            for netuid, base_emission in [(1, 5.0), (3, 3.0)]:
                await session.execute(
                    text(
                        "INSERT INTO emission_records"
                        " (time, netuid, emission_tao,"
                        " emission_share_pct, net_tao_inflow,"
                        " cumulative_stake)"
                        " VALUES (:t, :netuid, :emission_tao,"
                        " :emission_share_pct, :net_tao_inflow,"
                        " :cumulative_stake)"
                    ),
                    {
                        "t": t,
                        "netuid": netuid,
                        "emission_tao": 10.0 + i * 0.1,
                        "emission_share_pct": base_emission + i * 0.05,
                        "net_tao_inflow": 50.0 + i,
                        "cumulative_stake": 1000.0 + i * 10,
                    },
                )

        # Subnet snapshots for SN1 and SN3
        for netuid, alpha_price, take_rate in [(1, 0.12, 0.10), (3, 0.08, 0.05)]:
            await session.execute(
                text("""
                    INSERT INTO subnet_snapshots
                        (time, netuid, miner_count, validator_count, emission_share,
                         registration_cost, alpha_price, alpha_market_cap,
                         tao_reserves, alpha_reserves, fill_rate, owner_take_rate)
                    VALUES (NOW(), :netuid, 100, 50, 0.065, 1.5, :alpha_price, 1200.0,
                            500.0, 4000.0, 0.78, :take_rate)
                """),
                {"netuid": netuid, "alpha_price": alpha_price, "take_rate": take_rate},
            )

        # Metagraph entries — user stakes 300 on SN1, 200 on SN3
        addr = "5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"
        for netuid, uid, stake in [(1, 0, 300.0), (3, 1, 200.0)]:
            await session.execute(
                text(
                    "INSERT INTO metagraph_entries"
                    " (time, netuid, uid, hotkey, coldkey,"
                    " stake, incentive, trust, dividends,"
                    " is_active)"
                    " VALUES"
                    " (NOW(), :netuid, :uid,"
                    " '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY',"
                    " :addr, :stake, 0.5, 0.8, 0.3, true)"
                ),
                {"netuid": netuid, "uid": uid, "addr": addr, "stake": stake},
            )

        await session.commit()

    return {"address": addr}


class TestScenarioEndpoint:
    """Integration tests for POST /engine/predictions/scenario."""

    async def test_returns_200_with_comparison(
        self, client: AsyncClient, seed_scenario_data: dict
    ) -> None:
        """Should compute scenario comparison from seeded data."""
        response = await client.post(
            "/engine/predictions/scenario",
            json={
                "coldkey_addresses": [seed_scenario_data["address"]],
                "scenarios": [
                    {
                        "label": "Move to SN3",
                        "moves": [{"source_netuid": 1, "dest_netuid": 3, "amount_tao": 100}],
                    },
                ],
                "horizon": 30,
            },
        )
        assert response.status_code == 200
        body = response.json()
        assert "data" in body
        assert "meta" in body

        data = body["data"]
        assert data["horizon_days"] == 30
        assert data["baseline"]["label"] == "Current"
        assert len(data["scenarios"]) == 1
        assert data["scenarios"][0]["label"] == "Move to SN3"

    async def test_baseline_reflects_current_stakes(
        self, client: AsyncClient, seed_scenario_data: dict
    ) -> None:
        """Baseline should show current allocation across SN1 and SN3."""
        response = await client.post(
            "/engine/predictions/scenario",
            json={
                "coldkey_addresses": [seed_scenario_data["address"]],
                "scenarios": [
                    {"moves": [{"source_netuid": 1, "dest_netuid": 3, "amount_tao": 50}]},
                ],
                "horizon": 30,
            },
        )
        baseline = response.json()["data"]["baseline"]
        assert baseline["total_staked_tao"] == pytest.approx(500.0)
        netuids = {a["netuid"] for a in baseline["allocations"]}
        assert netuids == {1, 3}

    async def test_yield_delta_computed(
        self, client: AsyncClient, seed_scenario_data: dict
    ) -> None:
        """Scenario outcome should have yield_delta relative to baseline."""
        response = await client.post(
            "/engine/predictions/scenario",
            json={
                "coldkey_addresses": [seed_scenario_data["address"]],
                "scenarios": [
                    {"moves": [{"source_netuid": 1, "dest_netuid": 3, "amount_tao": 100}]},
                ],
                "horizon": 30,
            },
        )
        scenario = response.json()["data"]["scenarios"][0]
        # yield_delta should be non-zero (moving stake changes projected yield)
        assert scenario["yield_delta_tao"] != 0.0

    async def test_multiple_scenarios(self, client: AsyncClient, seed_scenario_data: dict) -> None:
        """Should handle 3 scenarios simultaneously and pick best yield/diversification."""
        response = await client.post(
            "/engine/predictions/scenario",
            json={
                "coldkey_addresses": [seed_scenario_data["address"]],
                "scenarios": [
                    {
                        "label": "Aggressive",
                        "moves": [{"source_netuid": 1, "dest_netuid": 3, "amount_tao": 200}],
                    },
                    {
                        "label": "Moderate",
                        "moves": [{"source_netuid": 1, "dest_netuid": 3, "amount_tao": 100}],
                    },
                    {
                        "label": "Conservative",
                        "moves": [{"source_netuid": 1, "dest_netuid": 3, "amount_tao": 50}],
                    },
                ],
                "horizon": 60,
            },
        )
        data = response.json()["data"]
        assert len(data["scenarios"]) == 3
        assert data["best_yield_index"] in range(3)
        assert data["best_diversification_index"] in range(3)

    async def test_envelope_format(self, client: AsyncClient, seed_scenario_data: dict) -> None:
        """Response follows {data, meta} envelope."""
        response = await client.post(
            "/engine/predictions/scenario",
            json={
                "coldkey_addresses": [seed_scenario_data["address"]],
                "scenarios": [
                    {"moves": [{"source_netuid": 1, "dest_netuid": 3, "amount_tao": 50}]},
                ],
                "horizon": 30,
            },
        )
        body = response.json()
        meta = body["meta"]
        assert "last_updated" in meta
        assert "compute_ms" in meta
        assert "cache_hit" in meta

    async def test_empty_portfolio_returns_empty_baseline(self, client: AsyncClient) -> None:
        """Address with no stake returns empty baseline and no scenarios."""
        response = await client.post(
            "/engine/predictions/scenario",
            json={
                "coldkey_addresses": ["5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"],
                "scenarios": [
                    {"moves": [{"source_netuid": 1, "dest_netuid": 3, "amount_tao": 50}]},
                ],
                "horizon": 30,
            },
        )
        data = response.json()["data"]
        assert data["baseline"]["total_staked_tao"] == 0.0
        assert data["baseline"]["allocations"] == []
        assert data["scenarios"] == []

    async def test_validates_invalid_scenario_request(self, client: AsyncClient) -> None:
        """Should reject invalid scenario requests (empty scenarios)."""
        response = await client.post(
            "/engine/predictions/scenario",
            json={
                "coldkey_addresses": ["5FHneW46xGXgs5mUiveU4sbTyGBzmstUspZC92UhjJM694ty"],
                "scenarios": [],
                "horizon": 30,
            },
        )
        assert response.status_code == 422

    async def test_alpha_exposure_in_allocations(
        self, client: AsyncClient, seed_scenario_data: dict
    ) -> None:
        """Allocations should include alpha price and exposure."""
        response = await client.post(
            "/engine/predictions/scenario",
            json={
                "coldkey_addresses": [seed_scenario_data["address"]],
                "scenarios": [
                    {"moves": [{"source_netuid": 1, "dest_netuid": 3, "amount_tao": 50}]},
                ],
                "horizon": 30,
            },
        )
        baseline = response.json()["data"]["baseline"]
        sn1_alloc = next(a for a in baseline["allocations"] if a["netuid"] == 1)
        assert sn1_alloc["alpha_price"] == pytest.approx(0.12)
        assert sn1_alloc["alpha_exposure_tao"] == pytest.approx(300.0 * 0.12)

    async def test_cache_hit_on_second_request(
        self, client: AsyncClient, seed_scenario_data: dict
    ) -> None:
        """Second identical request should be a cache hit."""
        payload = {
            "coldkey_addresses": [seed_scenario_data["address"]],
            "scenarios": [
                {"moves": [{"source_netuid": 1, "dest_netuid": 3, "amount_tao": 75}]},
            ],
            "horizon": 30,
        }
        response1 = await client.post("/engine/predictions/scenario", json=payload)
        assert response1.json()["meta"]["cache_hit"] is False

        response2 = await client.post("/engine/predictions/scenario", json=payload)
        assert response2.json()["meta"]["cache_hit"] is True


@pytest.fixture
async def seed_emission_forecast_data(db_engine):
    """Seed 30 days of emission records for netuids 1, 3, and 5 with varying
    net_tao_inflow patterns (SN1 positive, SN3 negative, SN5 near-zero),
    plus a subnet snapshot and metagraph entry.
    """
    base_time = datetime.now(UTC) - timedelta(days=30)

    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        # Emission records — 30 days for SN1, SN3, SN5
        for i in range(30):
            t = base_time + timedelta(days=i)
            for netuid, base_emission, inflow_sign in [
                (1, 6.0, 1.0),  # SN1: positive inflow
                (3, 4.0, -1.0),  # SN3: negative inflow (outflow)
                (5, 2.0, 0.01),  # SN5: near-zero inflow
            ]:
                await session.execute(
                    text(
                        "INSERT INTO emission_records"
                        " (time, netuid, emission_tao,"
                        " emission_share_pct, net_tao_inflow,"
                        " cumulative_stake)"
                        " VALUES (:t, :netuid, :emission_tao,"
                        " :emission_share_pct, :net_tao_inflow,"
                        " :cumulative_stake)"
                    ),
                    {
                        "t": t,
                        "netuid": netuid,
                        "emission_tao": 10.0 + i * 0.1,
                        "emission_share_pct": base_emission + i * 0.05,
                        "net_tao_inflow": inflow_sign * (50.0 + i),
                        "cumulative_stake": 1000.0 + i * 10,
                    },
                )

        # Subnet snapshot — latest for SN1
        await session.execute(
            text("""
                INSERT INTO subnet_snapshots
                    (time, netuid, miner_count, validator_count, emission_share,
                     registration_cost, alpha_price, alpha_market_cap,
                     tao_reserves, alpha_reserves, fill_rate, owner_take_rate)
                VALUES (NOW(), 1, 100, 50, 0.065, 1.5, 0.12, 1200.0, 500.0, 4000.0, 0.78, 0.10)
            """)
        )

        # Metagraph entry — user's stake on SN1
        await session.execute(
            text(
                "INSERT INTO metagraph_entries"
                " (time, netuid, uid, hotkey, coldkey,"
                " stake, incentive, trust, dividends,"
                " is_active)"
                " VALUES"
                " (NOW(), 1, 0,"
                " '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY',"
                " '5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY',"
                " 200.0, 0.5, 0.8, 0.3, true)"
            )
        )

        await session.commit()

    return {
        "address": "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY",
        "netuid": 1,
        "stake": 200.0,
    }


class TestEmissionForecastEndpoint:
    """Integration tests for POST /engine/predictions/emission."""

    async def test_returns_200_with_forecast_data(
        self, client: AsyncClient, seed_emission_forecast_data: dict
    ) -> None:
        """Should compute real emission forecast from seeded data."""
        response = await client.post(
            "/engine/predictions/emission",
            json={
                "coldkey_addresses": [seed_emission_forecast_data["address"]],
                "horizons": [30],
            },
        )
        assert response.status_code == 200
        body = response.json()

        data = body["data"]
        assert data["subnets_analyzed"] == 3
        assert data["subnets_skipped"] == 0
        assert len(data["subnet_forecasts"]) == 3
        assert "halving_impact" in data
        assert "staking_migration" in data

    async def test_envelope_format(
        self, client: AsyncClient, seed_emission_forecast_data: dict
    ) -> None:
        """Response follows {data, meta} envelope format."""
        response = await client.post(
            "/engine/predictions/emission",
            json={
                "coldkey_addresses": [seed_emission_forecast_data["address"]],
                "horizons": [30],
            },
        )
        body = response.json()

        assert "data" in body
        assert "meta" in body

        data = body["data"]
        assert "subnet_forecasts" in data
        assert "halving_impact" in data
        assert "staking_migration" in data
        assert "caveat" in data
        assert "last_computed" in data
        assert "subnets_analyzed" in data
        assert "subnets_skipped" in data

        meta = body["meta"]
        assert "last_updated" in meta
        assert "compute_ms" in meta
        assert "cache_hit" in meta

    async def test_validates_invalid_addresses(self, client: AsyncClient) -> None:
        """Should reject invalid SS58 addresses."""
        response = await client.post(
            "/engine/predictions/emission",
            json={
                "coldkey_addresses": ["not-a-valid-address"],
                "horizons": [30],
            },
        )
        assert response.status_code == 422

    async def test_subnet_forecast_fields(
        self, client: AsyncClient, seed_emission_forecast_data: dict
    ) -> None:
        """Each subnet forecast has netuid, ema_trend, momentum, chart_data."""
        response = await client.post(
            "/engine/predictions/emission",
            json={
                "coldkey_addresses": [seed_emission_forecast_data["address"]],
                "horizons": [30],
            },
        )
        body = response.json()
        forecasts = body["data"]["subnet_forecasts"]
        assert len(forecasts) >= 1

        for forecast in forecasts:
            assert "netuid" in forecast
            assert forecast["ema_trend"] in ("rising", "falling", "stable")
            assert isinstance(forecast["momentum"], float)
            assert len(forecast["chart_data"]) == 30
            # Chart data points have expected fields
            point = forecast["chart_data"][0]
            assert point["day"] == 1
            assert "emission_share_pct" in point
            assert "confidence_68_lower" in point
            assert "confidence_95_upper" in point

    async def test_halving_impact_fields(
        self, client: AsyncClient, seed_emission_forecast_data: dict
    ) -> None:
        """halving_impact has blocks_remaining, estimated_days_remaining, emission fields."""
        response = await client.post(
            "/engine/predictions/emission",
            json={
                "coldkey_addresses": [seed_emission_forecast_data["address"]],
                "horizons": [30],
            },
        )
        halving = response.json()["data"]["halving_impact"]

        assert "blocks_remaining" in halving
        assert halving["blocks_remaining"] >= 0
        assert "estimated_days_remaining" in halving
        assert halving["estimated_days_remaining"] >= 0
        assert "current_emission_per_day_tao" in halving
        assert halving["current_emission_per_day_tao"] > 0
        assert "post_halving_emission_per_day_tao" in halving
        assert halving["post_halving_emission_per_day_tao"] == pytest.approx(
            halving["current_emission_per_day_tao"] / 2.0
        )
        assert "estimated_yield_impact_pct" in halving
        assert "estimated_yield_impact_tao" in halving

    async def test_staking_migration_has_directions(
        self, client: AsyncClient, seed_emission_forecast_data: dict
    ) -> None:
        """staking_migration entries have direction (inflow/outflow)."""
        response = await client.post(
            "/engine/predictions/emission",
            json={
                "coldkey_addresses": [seed_emission_forecast_data["address"]],
                "horizons": [30],
            },
        )
        migrations = response.json()["data"]["staking_migration"]
        assert len(migrations) >= 1

        directions_seen = set()
        for entry in migrations:
            assert entry["direction"] in ("inflow", "outflow")
            assert "netuid" in entry
            assert "net_tao_inflow_30d" in entry
            assert "avg_daily_inflow" in entry
            directions_seen.add(entry["direction"])

        # SN1 has positive inflow, SN3 has negative (outflow)
        assert "inflow" in directions_seen
        assert "outflow" in directions_seen

    async def test_cache_hit_on_second_request(
        self, client: AsyncClient, seed_emission_forecast_data: dict
    ) -> None:
        """Second identical request should be a cache hit."""
        payload = {
            "coldkey_addresses": [seed_emission_forecast_data["address"]],
            "horizons": [30],
        }

        # First request — cache miss
        response1 = await client.post("/engine/predictions/emission", json=payload)
        assert response1.json()["meta"]["cache_hit"] is False

        # Second request — should be cache hit
        response2 = await client.post("/engine/predictions/emission", json=payload)
        assert response2.json()["meta"]["cache_hit"] is True
