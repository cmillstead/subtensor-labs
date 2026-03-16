"""Tests for user address CRUD endpoints — real database, no mocks."""

import asyncio
import os

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine

# Set debug mode before importing app — but DON'T change ENGINE_DATABASE_URL
# globally, as that would affect other test modules in the same pytest session.
# Instead, we create our own engine pointing at the test DB.
os.environ.setdefault("ENGINE_DEBUG", "true")

import engine.models  # noqa: E402, F401
from engine.core.database import Base, get_session  # noqa: E402
from engine.main import app  # noqa: E402
from engine.models.user import User  # noqa: E402

TEST_DB_URL = "postgresql+asyncpg://tao:tao@localhost:5432/subtensor_labs_test"
VALID_ADDRESS_1 = "5GrwvaEF5zXb26Fz9rcQpDWS57CtERHpNehXCPcNoHGKutQY"


# -- Module-level table setup (sync, runs once) --


def _run(coro):
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


async def _init_tables():
    eng = create_async_engine(TEST_DB_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    await eng.dispose()


async def _drop_tables():
    eng = create_async_engine(TEST_DB_URL)
    async with eng.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await eng.dispose()


_run(_init_tables())


def teardown_module():
    _run(_drop_tables())


# -- Per-test fixtures --


@pytest.fixture
async def db_engine():
    """Fresh engine per test — avoids connection conflicts."""
    eng = create_async_engine(TEST_DB_URL, pool_size=5, max_overflow=0)
    yield eng
    await eng.dispose()


@pytest.fixture(autouse=True)
async def _override_and_clean(db_engine):
    """Override app session, clean tables after test."""

    async def _test_session():
        async with AsyncSession(db_engine, expire_on_commit=False) as session:
            yield session

    app.dependency_overrides[get_session] = _test_session
    yield
    app.dependency_overrides.clear()

    async with db_engine.begin() as conn:
        await conn.execute(text("DELETE FROM user_addresses"))
        await conn.execute(text("DELETE FROM password_reset_tokens"))
        await conn.execute(text("DELETE FROM users"))


@pytest.fixture
async def client():
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        yield ac


@pytest.fixture
async def user_id(db_engine) -> int:
    async with AsyncSession(db_engine, expire_on_commit=False) as session:
        u = User(email="test@example.com", password_hash="$argon2id$fakehash")
        session.add(u)
        await session.commit()
        await session.refresh(u)
        return u.id


class TestListAddresses:
    async def test_list_empty(self, client: AsyncClient, user_id: int) -> None:
        res = await client.get(
            f"/engine/users/{user_id}/addresses",
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 200
        assert res.json() == {"data": []}

    async def test_list_returns_addresses(self, client: AsyncClient, user_id: int) -> None:
        await client.post(
            f"/engine/users/{user_id}/addresses",
            json={"coldkey_address": VALID_ADDRESS_1, "label": "Main Wallet"},
            headers={"x-user-id": str(user_id)},
        )
        res = await client.get(
            f"/engine/users/{user_id}/addresses",
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert len(data) == 1
        assert data[0]["coldkey_address"] == VALID_ADDRESS_1
        assert data[0]["label"] == "Main Wallet"

    async def test_list_forbidden_wrong_user(self, client: AsyncClient, user_id: int) -> None:
        res = await client.get(
            f"/engine/users/{user_id}/addresses",
            headers={"x-user-id": "999999"},
        )
        assert res.status_code == 403


class TestCreateAddress:
    async def test_create_success(self, client: AsyncClient, user_id: int) -> None:
        res = await client.post(
            f"/engine/users/{user_id}/addresses",
            json={"coldkey_address": VALID_ADDRESS_1, "label": "My Wallet"},
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["coldkey_address"] == VALID_ADDRESS_1
        assert data["label"] == "My Wallet"
        assert data["is_watch_only"] is False

    async def test_create_duplicate(self, client: AsyncClient, user_id: int) -> None:
        await client.post(
            f"/engine/users/{user_id}/addresses",
            json={"coldkey_address": VALID_ADDRESS_1},
            headers={"x-user-id": str(user_id)},
        )
        res = await client.post(
            f"/engine/users/{user_id}/addresses",
            json={"coldkey_address": VALID_ADDRESS_1},
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 409
        assert res.json()["error"]["type"] == "duplicate_address"

    async def test_create_exceeds_limit(self, client: AsyncClient, user_id: int) -> None:
        # Generate 20 unique valid SS58 addresses (46 chars each, all base58)
        base58_chars = "123456789ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz"
        for i in range(20):
            c = base58_chars[i + 1]  # vary one char to make unique
            addr = f"5{c}{'a' * 44}"  # 46 chars total: "5" + char + 44 * "a"
            r = await client.post(
                f"/engine/users/{user_id}/addresses",
                json={"coldkey_address": addr},
                headers={"x-user-id": str(user_id)},
            )
            assert r.status_code == 201, f"Failed to create address {i}: {r.json()}"
        res = await client.post(
            f"/engine/users/{user_id}/addresses",
            json={"coldkey_address": VALID_ADDRESS_1},
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 400
        assert res.json()["error"]["type"] == "address_limit_reached"

    async def test_create_invalid_ss58(self, client: AsyncClient, user_id: int) -> None:
        res = await client.post(
            f"/engine/users/{user_id}/addresses",
            json={"coldkey_address": "invalid!address"},
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 422

    async def test_create_forbidden_wrong_user(self, client: AsyncClient, user_id: int) -> None:
        res = await client.post(
            f"/engine/users/{user_id}/addresses",
            json={"coldkey_address": VALID_ADDRESS_1},
            headers={"x-user-id": "999999"},
        )
        assert res.status_code == 403

    async def test_address_stored_encrypted(
        self,
        client: AsyncClient,
        user_id: int,
        db_engine,
    ) -> None:
        """Verify the raw DB column is ciphertext, not plaintext."""
        await client.post(
            f"/engine/users/{user_id}/addresses",
            json={"coldkey_address": VALID_ADDRESS_1},
            headers={"x-user-id": str(user_id)},
        )
        async with db_engine.connect() as conn:
            row = await conn.execute(
                text("SELECT coldkey_address FROM user_addresses WHERE user_id = :uid"),
                {"uid": user_id},
            )
            raw_value = row.scalar_one()
            assert raw_value != VALID_ADDRESS_1
            assert len(raw_value) > len(VALID_ADDRESS_1)


class TestUpdateAddress:
    async def test_update_label(self, client: AsyncClient, user_id: int) -> None:
        create_res = await client.post(
            f"/engine/users/{user_id}/addresses",
            json={"coldkey_address": VALID_ADDRESS_1, "label": "Old Label"},
            headers={"x-user-id": str(user_id)},
        )
        addr_id = create_res.json()["data"]["id"]
        res = await client.patch(
            f"/engine/users/{user_id}/addresses/{addr_id}",
            json={"label": "New Label"},
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 200
        assert res.json()["data"]["label"] == "New Label"

    async def test_update_not_found(self, client: AsyncClient, user_id: int) -> None:
        res = await client.patch(
            f"/engine/users/{user_id}/addresses/999999",
            json={"label": "New Label"},
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 404

    async def test_update_forbidden_wrong_user(self, client: AsyncClient, user_id: int) -> None:
        create_res = await client.post(
            f"/engine/users/{user_id}/addresses",
            json={"coldkey_address": VALID_ADDRESS_1},
            headers={"x-user-id": str(user_id)},
        )
        addr_id = create_res.json()["data"]["id"]
        res = await client.patch(
            f"/engine/users/{user_id}/addresses/{addr_id}",
            json={"label": "Stolen"},
            headers={"x-user-id": "999999"},
        )
        assert res.status_code == 403


class TestDeleteAddress:
    async def test_delete_success(self, client: AsyncClient, user_id: int) -> None:
        create_res = await client.post(
            f"/engine/users/{user_id}/addresses",
            json={"coldkey_address": VALID_ADDRESS_1},
            headers={"x-user-id": str(user_id)},
        )
        addr_id = create_res.json()["data"]["id"]
        res = await client.delete(
            f"/engine/users/{user_id}/addresses/{addr_id}",
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 200
        assert res.json()["message"] == "Address removed."
        list_res = await client.get(
            f"/engine/users/{user_id}/addresses",
            headers={"x-user-id": str(user_id)},
        )
        assert list_res.json() == {"data": []}

    async def test_delete_not_found(self, client: AsyncClient, user_id: int) -> None:
        res = await client.delete(
            f"/engine/users/{user_id}/addresses/999999",
            headers={"x-user-id": str(user_id)},
        )
        assert res.status_code == 404

    async def test_delete_forbidden_wrong_user(self, client: AsyncClient, user_id: int) -> None:
        create_res = await client.post(
            f"/engine/users/{user_id}/addresses",
            json={"coldkey_address": VALID_ADDRESS_1},
            headers={"x-user-id": str(user_id)},
        )
        addr_id = create_res.json()["data"]["id"]
        res = await client.delete(
            f"/engine/users/{user_id}/addresses/{addr_id}",
            headers={"x-user-id": "999999"},
        )
        assert res.status_code == 403


class TestRoundTrip:
    async def test_full_crud_cycle(self, client: AsyncClient, user_id: int) -> None:
        uid = str(user_id)
        base = f"/engine/users/{user_id}/addresses"

        r1 = await client.post(
            base,
            json={"coldkey_address": VALID_ADDRESS_1, "label": "Wallet A"},
            headers={"x-user-id": uid},
        )
        assert r1.status_code == 201
        addr_id = r1.json()["data"]["id"]

        r2 = await client.get(base, headers={"x-user-id": uid})
        assert len(r2.json()["data"]) == 1

        r3 = await client.patch(
            f"{base}/{addr_id}",
            json={"label": "Renamed"},
            headers={"x-user-id": uid},
        )
        assert r3.json()["data"]["label"] == "Renamed"

        r4 = await client.get(base, headers={"x-user-id": uid})
        assert r4.json()["data"][0]["label"] == "Renamed"

        r5 = await client.delete(f"{base}/{addr_id}", headers={"x-user-id": uid})
        assert r5.status_code == 200

        r6 = await client.get(base, headers={"x-user-id": uid})
        assert r6.json()["data"] == []
