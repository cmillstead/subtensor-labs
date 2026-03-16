"""Tests for user registration, auth, and password reset — real database, no mocks.

Only mock: send_password_reset_email (external Resend API).
Everything else — argon2 hashing, DB sessions, token storage — runs for real.
"""

import hashlib
from unittest.mock import patch

from httpx import AsyncClient
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession


class TestUserRegistration:
    """Tests for POST /engine/users/register."""

    async def test_successful_registration(self, client: AsyncClient) -> None:
        res = await client.post(
            "/engine/users/register",
            json={"email": "new@example.com", "password": "securepass123"},
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert data["email"] == "new@example.com"
        assert data["premium_status"] == "free"
        assert "id" in data
        assert "created_at" in data

    async def test_duplicate_email_returns_409(self, client: AsyncClient) -> None:
        await client.post(
            "/engine/users/register",
            json={"email": "dupe@example.com", "password": "securepass123"},
        )
        res = await client.post(
            "/engine/users/register",
            json={"email": "dupe@example.com", "password": "securepass123"},
        )
        assert res.status_code == 409
        assert res.json()["error"]["type"] == "duplicate_email"

    async def test_invalid_email_format_returns_422(self, client: AsyncClient) -> None:
        res = await client.post(
            "/engine/users/register",
            json={"email": "not-an-email", "password": "securepass123"},
        )
        assert res.status_code == 422

    async def test_short_password_returns_422(self, client: AsyncClient) -> None:
        res = await client.post(
            "/engine/users/register",
            json={"email": "short@example.com", "password": "short"},
        )
        assert res.status_code == 422

    async def test_password_not_in_response(self, client: AsyncClient) -> None:
        res = await client.post(
            "/engine/users/register",
            json={"email": "nopw@example.com", "password": "securepass123"},
        )
        assert res.status_code == 201
        data = res.json()["data"]
        assert "password_hash" not in data
        assert "password" not in data

    async def test_password_stored_as_argon2_hash(
        self,
        client: AsyncClient,
        db_engine,
    ) -> None:
        """Verify password is hashed with argon2, not stored in plaintext."""
        await client.post(
            "/engine/users/register",
            json={"email": "hash@example.com", "password": "securepass123"},
        )
        async with db_engine.connect() as conn:
            row = await conn.execute(
                text("SELECT password_hash FROM users WHERE email = :e"),
                {"e": "hash@example.com"},
            )
            stored_hash = row.scalar_one()
            assert stored_hash.startswith("$argon2id$")
            assert stored_hash != "securepass123"


class TestUserVerification:
    """Tests for POST /engine/users/verify."""

    async def test_successful_verification(self, client: AsyncClient) -> None:
        await client.post(
            "/engine/users/register",
            json={"email": "verify@example.com", "password": "securepass123"},
        )
        res = await client.post(
            "/engine/users/verify",
            json={"email": "verify@example.com", "password": "securepass123"},
        )
        assert res.status_code == 200
        data = res.json()["data"]
        assert data["email"] == "verify@example.com"
        assert data["premium_status"] == "free"

    async def test_wrong_password_returns_401(self, client: AsyncClient) -> None:
        await client.post(
            "/engine/users/register",
            json={"email": "wrong@example.com", "password": "securepass123"},
        )
        res = await client.post(
            "/engine/users/verify",
            json={"email": "wrong@example.com", "password": "wrongpassword"},
        )
        assert res.status_code == 401
        assert res.json()["error"]["type"] == "invalid_credentials"
        assert res.json()["error"]["message"] == "Invalid email or password"

    async def test_nonexistent_email_returns_401_same_message(
        self,
        client: AsyncClient,
    ) -> None:
        res = await client.post(
            "/engine/users/verify",
            json={"email": "nobody@example.com", "password": "securepass123"},
        )
        assert res.status_code == 401
        assert res.json()["error"]["type"] == "invalid_credentials"
        assert res.json()["error"]["message"] == "Invalid email or password"


class TestPasswordResetRequest:
    """Tests for POST /engine/users/reset-password/request."""

    async def test_request_with_valid_email(
        self,
        client: AsyncClient,
        db_engine,
    ) -> None:
        await client.post(
            "/engine/users/register",
            json={"email": "reset@example.com", "password": "securepass123"},
        )
        with patch("engine.api.users.send_password_reset_email") as mock_email:
            res = await client.post(
                "/engine/users/reset-password/request",
                json={"email": "reset@example.com"},
            )
        assert res.status_code == 200
        assert "reset link has been sent" in res.json()["message"]
        mock_email.assert_called_once()

        async with db_engine.connect() as conn:
            row = await conn.execute(
                text("SELECT COUNT(*) FROM password_reset_tokens"),
            )
            assert row.scalar_one() == 1

    async def test_request_with_nonexistent_email_returns_200(
        self,
        client: AsyncClient,
    ) -> None:
        with patch("engine.api.users.send_password_reset_email") as mock_email:
            res = await client.post(
                "/engine/users/reset-password/request",
                json={"email": "nobody@example.com"},
            )
        assert res.status_code == 200
        assert "reset link has been sent" in res.json()["message"]
        mock_email.assert_not_called()

    async def test_request_invalidates_previous_tokens(
        self,
        client: AsyncClient,
        db_engine,
    ) -> None:
        await client.post(
            "/engine/users/register",
            json={"email": "multi@example.com", "password": "securepass123"},
        )
        with patch("engine.api.users.send_password_reset_email"):
            await client.post(
                "/engine/users/reset-password/request",
                json={"email": "multi@example.com"},
            )
            await client.post(
                "/engine/users/reset-password/request",
                json={"email": "multi@example.com"},
            )
        async with db_engine.connect() as conn:
            row = await conn.execute(
                text("SELECT COUNT(*) FROM password_reset_tokens WHERE used_at IS NULL"),
            )
            assert row.scalar_one() == 1


class TestPasswordResetConfirm:
    """Tests for POST /engine/users/reset-password/confirm."""

    async def _create_user_and_get_token(
        self,
        client: AsyncClient,
        db_engine,
    ) -> tuple[str, int]:
        """Register a user, request a reset, and extract the raw token."""
        await client.post(
            "/engine/users/register",
            json={"email": "confirm@example.com", "password": "oldpassword1"},
        )
        captured_token = None

        def capture_email(*, to, reset_url):
            nonlocal captured_token
            captured_token = reset_url.split("token=")[1]

        with patch(
            "engine.api.users.send_password_reset_email",
            side_effect=capture_email,
        ):
            await client.post(
                "/engine/users/reset-password/request",
                json={"email": "confirm@example.com"},
            )

        assert captured_token is not None

        async with AsyncSession(db_engine) as session:
            result = await session.execute(
                text("SELECT id FROM users WHERE email = :e"),
                {"e": "confirm@example.com"},
            )
            user_id = result.scalar_one()

        return captured_token, user_id

    async def test_confirm_with_valid_token(
        self,
        client: AsyncClient,
        db_engine,
    ) -> None:
        token, _ = await self._create_user_and_get_token(client, db_engine)

        res = await client.post(
            "/engine/users/reset-password/confirm",
            json={"token": token, "password": "newpassword123"},
        )
        assert res.status_code == 200
        assert "reset successfully" in res.json()["message"]

        # Verify can login with new password
        verify_res = await client.post(
            "/engine/users/verify",
            json={"email": "confirm@example.com", "password": "newpassword123"},
        )
        assert verify_res.status_code == 200

        # Verify old password no longer works
        old_res = await client.post(
            "/engine/users/verify",
            json={"email": "confirm@example.com", "password": "oldpassword1"},
        )
        assert old_res.status_code == 401

    async def test_confirm_with_expired_token(
        self,
        client: AsyncClient,
        db_engine,
    ) -> None:
        token, _ = await self._create_user_and_get_token(client, db_engine)

        token_hash = hashlib.sha256(token.encode()).hexdigest()
        async with AsyncSession(db_engine) as session:
            await session.execute(
                text(
                    "UPDATE password_reset_tokens "
                    "SET expires_at = NOW() - INTERVAL '1 hour' "
                    "WHERE token_hash = :h"
                ),
                {"h": token_hash},
            )
            await session.commit()

        res = await client.post(
            "/engine/users/reset-password/confirm",
            json={"token": token, "password": "newpassword123"},
        )
        assert res.status_code == 400
        assert res.json()["error"]["type"] == "token_expired"

    async def test_confirm_with_already_used_token(
        self,
        client: AsyncClient,
        db_engine,
    ) -> None:
        token, _ = await self._create_user_and_get_token(client, db_engine)

        await client.post(
            "/engine/users/reset-password/confirm",
            json={"token": token, "password": "newpassword123"},
        )
        res = await client.post(
            "/engine/users/reset-password/confirm",
            json={"token": token, "password": "anotherpassword1"},
        )
        assert res.status_code == 400
        assert res.json()["error"]["type"] == "invalid_token"

    async def test_confirm_with_invalid_token(self, client: AsyncClient) -> None:
        res = await client.post(
            "/engine/users/reset-password/confirm",
            json={"token": "nonexistent-token", "password": "newpassword123"},
        )
        assert res.status_code == 400
        assert res.json()["error"]["type"] == "invalid_token"

    async def test_confirm_with_short_password(self, client: AsyncClient) -> None:
        res = await client.post(
            "/engine/users/reset-password/confirm",
            json={"token": "any-token", "password": "short"},
        )
        assert res.status_code == 422


class TestRoundTrip:
    """Full auth lifecycle: register -> verify -> reset -> verify with new password."""

    async def test_full_auth_lifecycle(
        self,
        client: AsyncClient,
        db_engine,
    ) -> None:
        # 1. Register
        r1 = await client.post(
            "/engine/users/register",
            json={"email": "lifecycle@example.com", "password": "original123"},
        )
        assert r1.status_code == 201

        # 2. Verify with original password
        r2 = await client.post(
            "/engine/users/verify",
            json={"email": "lifecycle@example.com", "password": "original123"},
        )
        assert r2.status_code == 200

        # 3. Request password reset
        captured_token = None

        def capture(*, to, reset_url):
            nonlocal captured_token
            captured_token = reset_url.split("token=")[1]

        with patch(
            "engine.api.users.send_password_reset_email",
            side_effect=capture,
        ):
            r3 = await client.post(
                "/engine/users/reset-password/request",
                json={"email": "lifecycle@example.com"},
            )
        assert r3.status_code == 200

        # 4. Confirm reset
        r4 = await client.post(
            "/engine/users/reset-password/confirm",
            json={"token": captured_token, "password": "changed456"},
        )
        assert r4.status_code == 200

        # 5. Old password fails
        r5 = await client.post(
            "/engine/users/verify",
            json={"email": "lifecycle@example.com", "password": "original123"},
        )
        assert r5.status_code == 401

        # 6. New password works
        r6 = await client.post(
            "/engine/users/verify",
            json={"email": "lifecycle@example.com", "password": "changed456"},
        )
        assert r6.status_code == 200
