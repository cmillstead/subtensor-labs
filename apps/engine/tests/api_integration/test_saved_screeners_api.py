"""Tests for saved screener CRUD endpoints — real database, no mocks."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from engine.models.user import User

SAMPLE_FILTERS = {
    "min_miners": 50,
    "max_miners": None,
    "min_validators": None,
    "max_validators": None,
    "min_registration_cost": None,
    "max_registration_cost": 5.0,
    "min_emission_share": 0.02,
    "max_emission_share": None,
    "min_alpha_price": None,
    "max_alpha_price": None,
    "min_subnet_age_days": None,
    "max_subnet_age_days": None,
    "min_alpha_price_change_24h": None,
    "max_alpha_price_change_24h": None,
    "min_alpha_price_change_7d": None,
    "max_alpha_price_change_7d": None,
    "min_alpha_price_change_30d": None,
    "max_alpha_price_change_30d": None,
    "min_alpha_market_cap": None,
    "max_alpha_market_cap": None,
    "min_net_tao_inflow": None,
    "max_net_tao_inflow": None,
    "min_fill_rate": None,
    "max_fill_rate": None,
    "min_owner_take_rate": None,
    "max_owner_take_rate": None,
    "immunity_active": None,
    "sort_by": "emission_share",
    "sort_direction": "desc",
}

SAMPLE_FILTERS_2 = {**SAMPLE_FILTERS, "min_miners": 100, "sort_by": "alpha_price"}


@pytest.fixture
async def user_id(db_engine) -> int:
    """Create a test user and return its ID."""
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        u = User(email="screener-test@example.com", password_hash="$argon2id$fakehash")
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return u.id


@pytest.fixture
async def other_user_id(db_engine) -> int:
    """Create a second test user for forbidden tests."""
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        u = User(email="other@example.com", password_hash="$argon2id$fakehash")
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return u.id


class TestListSavedScreeners:
    async def test_list_empty(self, client: AsyncClient, user_id: int) -> None:
        res = await client.get(
            f"/engine/users/{user_id}/saved-screeners",
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 200
        assert res.json() == {"data": []}

    async def test_list_returns_screeners_ordered_by_updated_at_desc(
        self, client: AsyncClient, user_id: int
    ) -> None:
        uid = str(user_id)
        base = f"/engine/users/{user_id}/saved-screeners"

        # Create two screeners
        await client.post(
            base,
            json={"name": "First", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": uid},
        )
        r2 = await client.post(
            base,
            json={"name": "Second", "filters_json": SAMPLE_FILTERS_2},
            headers={"x-user-id": uid},
        )
        assert r2.status_code == 201

        res = await client.get(base, headers={"x-user-id": uid})
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 2
        # Most recently created/updated should be first
        assert data[0]["name"] == "Second"
        assert data[1]["name"] == "First"

    async def test_list_forbidden_wrong_user(self, client: AsyncClient, user_id: int) -> None:
        res = await client.get(
            f"/engine/users/{user_id}/saved-screeners",
            headers={"x-user-id": "999999"},
        )
        assert res.status_code == 403


class TestCreateSavedScreener:
    async def test_create_success(self, client: AsyncClient, user_id: int) -> None:
        res = await client.post(
            f"/engine/users/{user_id}/saved-screeners",
            json={"name": "Emerging high-growth", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["name"] == "Emerging high-growth"
        assert data["filters_json"] == SAMPLE_FILTERS
        assert "id" in data
        assert "created_at" in data
        assert "updated_at" in data

    async def test_create_duplicate_name(self, client: AsyncClient, user_id: int) -> None:
        uid = str(user_id)
        base = f"/engine/users/{user_id}/saved-screeners"
        await client.post(
            base,
            json={"name": "My Screener", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": uid},
        )
        res = await client.post(
            base,
            json={"name": "My Screener", "filters_json": SAMPLE_FILTERS_2},
            headers={"x-user-id": uid},
        )
        assert res.status_code == 409
        assert res.json()["error"]["type"] == "duplicate_name"

    async def test_create_exceeds_limit(self, client: AsyncClient, user_id: int) -> None:
        uid = str(user_id)
        base = f"/engine/users/{user_id}/saved-screeners"
        for i in range(20):
            r = await client.post(
                base,
                json={"name": f"Screener {i}", "filters_json": SAMPLE_FILTERS},
                headers={"x-user-id": uid},
            )
            assert r.status_code == 201, f"Failed to create screener {i}: {r.json()}"

        res = await client.post(
            base,
            json={"name": "One Too Many", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": uid},
        )
        assert res.status_code == 400
        assert res.json()["error"]["type"] == "screener_limit_reached"

    async def test_create_forbidden_wrong_user(self, client: AsyncClient, user_id: int) -> None:
        res = await client.post(
            f"/engine/users/{user_id}/saved-screeners",
            json={"name": "Stolen", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": "999999"},
        )
        assert res.status_code == 403

    async def test_create_empty_name_rejected(self, client: AsyncClient, user_id: int) -> None:
        res = await client.post(
            f"/engine/users/{user_id}/saved-screeners",
            json={"name": "", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 422


class TestUpdateSavedScreener:
    async def test_update_name_only(self, client: AsyncClient, user_id: int) -> None:
        uid = str(user_id)
        base = f"/engine/users/{user_id}/saved-screeners"
        create_res = await client.post(
            base,
            json={"name": "Old Name", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": uid},
        )
        screener_id = create_res.json()["data"]["id"]

        res = await client.put(
            f"{base}/{screener_id}",
            json={"name": "New Name"},
            headers={"x-user-id": uid},
        )
        assert res.status_code == 200
        assert res.json()["data"]["name"] == "New Name"
        assert res.json()["data"]["filters_json"] == SAMPLE_FILTERS

    async def test_update_filters_only(self, client: AsyncClient, user_id: int) -> None:
        uid = str(user_id)
        base = f"/engine/users/{user_id}/saved-screeners"
        create_res = await client.post(
            base,
            json={"name": "Keep Name", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": uid},
        )
        screener_id = create_res.json()["data"]["id"]

        res = await client.put(
            f"{base}/{screener_id}",
            json={"filters_json": SAMPLE_FILTERS_2},
            headers={"x-user-id": uid},
        )
        assert res.status_code == 200
        assert res.json()["data"]["name"] == "Keep Name"
        assert res.json()["data"]["filters_json"] == SAMPLE_FILTERS_2

    async def test_update_both(self, client: AsyncClient, user_id: int) -> None:
        uid = str(user_id)
        base = f"/engine/users/{user_id}/saved-screeners"
        create_res = await client.post(
            base,
            json={"name": "Original", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": uid},
        )
        screener_id = create_res.json()["data"]["id"]

        res = await client.put(
            f"{base}/{screener_id}",
            json={"name": "Updated", "filters_json": SAMPLE_FILTERS_2},
            headers={"x-user-id": uid},
        )
        assert res.status_code == 200
        assert res.json()["data"]["name"] == "Updated"
        assert res.json()["data"]["filters_json"] == SAMPLE_FILTERS_2

    async def test_update_duplicate_name(self, client: AsyncClient, user_id: int) -> None:
        uid = str(user_id)
        base = f"/engine/users/{user_id}/saved-screeners"
        await client.post(
            base,
            json={"name": "Existing", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": uid},
        )
        create_res = await client.post(
            base,
            json={"name": "Other", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": uid},
        )
        screener_id = create_res.json()["data"]["id"]

        res = await client.put(
            f"{base}/{screener_id}",
            json={"name": "Existing"},
            headers={"x-user-id": uid},
        )
        assert res.status_code == 409

    async def test_update_nonexistent(self, client: AsyncClient, user_id: int) -> None:
        res = await client.put(
            f"/engine/users/{user_id}/saved-screeners/999999",
            json={"name": "Ghost"},
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 404

    async def test_update_forbidden_wrong_user(
        self, client: AsyncClient, user_id: int, other_user_id: int
    ) -> None:
        uid = str(user_id)
        base = f"/engine/users/{user_id}/saved-screeners"
        create_res = await client.post(
            base,
            json={"name": "Mine", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": uid},
        )
        screener_id = create_res.json()["data"]["id"]

        res = await client.put(
            f"{base}/{screener_id}",
            json={"name": "Stolen"},
            headers={"x-user-id": str(other_user_id)},
        )
        assert res.status_code == 403


class TestDeleteSavedScreener:
    async def test_delete_success(self, client: AsyncClient, user_id: int) -> None:
        uid = str(user_id)
        base = f"/engine/users/{user_id}/saved-screeners"
        create_res = await client.post(
            base,
            json={"name": "To Delete", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": uid},
        )
        screener_id = create_res.json()["data"]["id"]

        res = await client.delete(
            f"{base}/{screener_id}",
            headers={"x-user-id": uid},
        )
        assert res.status_code == 200
        assert res.json()["message"] == "Screener removed."

        list_res = await client.get(base, headers={"x-user-id": uid})
        assert list_res.json() == {"data": []}

    async def test_delete_nonexistent(self, client: AsyncClient, user_id: int) -> None:
        res = await client.delete(
            f"/engine/users/{user_id}/saved-screeners/999999",
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 404

    async def test_delete_forbidden_wrong_user(
        self, client: AsyncClient, user_id: int, other_user_id: int
    ) -> None:
        uid = str(user_id)
        base = f"/engine/users/{user_id}/saved-screeners"
        create_res = await client.post(
            base,
            json={"name": "Protected", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": uid},
        )
        screener_id = create_res.json()["data"]["id"]

        res = await client.delete(
            f"{base}/{screener_id}",
            headers={"x-user-id": str(other_user_id)},
        )
        assert res.status_code == 403


class TestRoundTrip:
    async def test_full_crud_cycle(self, client: AsyncClient, user_id: int) -> None:
        uid = str(user_id)
        base = f"/engine/users/{user_id}/saved-screeners"

        # Create
        r1 = await client.post(
            base,
            json={"name": "Growth Filter", "filters_json": SAMPLE_FILTERS},
            headers={"x-user-id": uid},
        )
        assert r1.status_code == 201
        screener_id = r1.json()["data"]["id"]

        # List
        r2 = await client.get(base, headers={"x-user-id": uid})
        assert len(r2.json()["data"]) == 1

        # Update
        r3 = await client.put(
            f"{base}/{screener_id}",
            json={"name": "Renamed", "filters_json": SAMPLE_FILTERS_2},
            headers={"x-user-id": uid},
        )
        assert r3.json()["data"]["name"] == "Renamed"
        assert r3.json()["data"]["filters_json"] == SAMPLE_FILTERS_2

        # Verify update persisted
        r4 = await client.get(base, headers={"x-user-id": uid})
        assert r4.json()["data"][0]["name"] == "Renamed"

        # Delete
        r5 = await client.delete(f"{base}/{screener_id}", headers={"x-user-id": uid})
        assert r5.status_code == 200

        # Verify deleted
        r6 = await client.get(base, headers={"x-user-id": uid})
        assert r6.json()["data"] == []
