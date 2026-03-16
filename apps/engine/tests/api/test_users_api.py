"""Tests for user registration, authentication, and password reset endpoints."""

import hashlib
from collections.abc import AsyncGenerator
from datetime import UTC, datetime, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from httpx import AsyncClient

from engine.core.database import get_session
from engine.main import app
from engine.models.password_reset_token import PasswordResetToken
from engine.models.user import User


def _make_user(
    id: int = 1,
    email: str = "test@example.com",
    premium_status: str = "free",
) -> User:
    """Create a User model instance for testing."""
    user = User(
        email=email,
        password_hash="",
        premium_status=premium_status,
    )
    # Set fields that are normally assigned by the DB
    object.__setattr__(user, "id", id)
    object.__setattr__(user, "created_at", datetime(2026, 1, 1, tzinfo=UTC))
    object.__setattr__(user, "updated_at", datetime(2026, 1, 1, tzinfo=UTC))
    return user


@pytest.fixture(autouse=True)
def _override_session() -> None:
    """Provide a no-op session override so tests never hit a real database."""
    mock_session = AsyncMock()
    mock_session.add = MagicMock()  # add() is synchronous in SQLAlchemy

    async def override() -> AsyncGenerator:
        yield mock_session

    app.dependency_overrides[get_session] = override
    yield
    app.dependency_overrides.clear()


class TestUserRegistration:
    """Tests for POST /engine/users/register."""

    async def test_successful_registration(self, client: AsyncClient) -> None:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        user = _make_user(id=1, email="new@example.com")

        async def fake_refresh(obj: User) -> None:
            obj.id = user.id
            obj.email = user.email
            obj.premium_status = user.premium_status
            obj.created_at = user.created_at

        mock_session.refresh = fake_refresh

        async def override() -> AsyncGenerator:
            yield mock_session

        app.dependency_overrides[get_session] = override

        with patch("engine.api.users.ph") as mock_ph:
            mock_ph.hash.return_value = "$argon2id$hashed"
            res = await client.post(
                "/engine/users/register",
                json={"email": "new@example.com", "password": "securepass123"},
            )

        assert res.status_code == 201
        body = res.json()
        assert "data" in body
        assert body["data"]["email"] == "new@example.com"
        assert body["data"]["premium_status"] == "free"
        assert "id" in body["data"]
        assert "created_at" in body["data"]

    async def test_duplicate_email_returns_409(self, client: AsyncClient) -> None:
        mock_session = AsyncMock()
        existing_user = _make_user(email="dupe@example.com")
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = existing_user
        mock_session.execute.return_value = mock_result

        async def override() -> AsyncGenerator:
            yield mock_session

        app.dependency_overrides[get_session] = override

        res = await client.post(
            "/engine/users/register",
            json={"email": "dupe@example.com", "password": "securepass123"},
        )

        assert res.status_code == 409
        body = res.json()
        assert body["error"]["type"] == "duplicate_email"

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
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        user = _make_user(id=2, email="hash@example.com")

        async def fake_refresh(obj: User) -> None:
            obj.id = user.id
            obj.email = user.email
            obj.premium_status = user.premium_status
            obj.created_at = user.created_at

        mock_session.refresh = fake_refresh

        async def override() -> AsyncGenerator:
            yield mock_session

        app.dependency_overrides[get_session] = override

        with patch("engine.api.users.ph") as mock_ph:
            mock_ph.hash.return_value = "$argon2id$hashed"
            res = await client.post(
                "/engine/users/register",
                json={"email": "hash@example.com", "password": "securepass123"},
            )

        assert res.status_code == 201
        body = res.json()
        assert "password_hash" not in body["data"]
        assert "password" not in body["data"]


class TestUserVerification:
    """Tests for POST /engine/users/verify."""

    async def test_successful_verification(self, client: AsyncClient) -> None:
        mock_session = AsyncMock()
        user = _make_user(email="verify@example.com")
        user.password_hash = "$argon2id$valid_hash"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        async def override() -> AsyncGenerator:
            yield mock_session

        app.dependency_overrides[get_session] = override

        with patch("engine.api.users.ph") as mock_ph:
            mock_ph.verify.return_value = True
            mock_ph.check_needs_rehash.return_value = False
            res = await client.post(
                "/engine/users/verify",
                json={"email": "verify@example.com", "password": "securepass123"},
            )

        assert res.status_code == 200
        body = res.json()
        assert body["data"]["email"] == "verify@example.com"
        assert body["data"]["premium_status"] == "free"

    async def test_wrong_password_returns_401(self, client: AsyncClient) -> None:
        from argon2.exceptions import VerifyMismatchError

        mock_session = AsyncMock()
        user = _make_user(email="verify@example.com")
        user.password_hash = "$argon2id$valid_hash"
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = user
        mock_session.execute.return_value = mock_result

        async def override() -> AsyncGenerator:
            yield mock_session

        app.dependency_overrides[get_session] = override

        with patch("engine.api.users.ph") as mock_ph:
            mock_ph.verify.side_effect = VerifyMismatchError()
            res = await client.post(
                "/engine/users/verify",
                json={"email": "verify@example.com", "password": "wrongpassword"},
            )

        assert res.status_code == 401
        body = res.json()
        assert body["error"]["type"] == "invalid_credentials"
        assert body["error"]["message"] == "Invalid email or password"

    async def test_nonexistent_email_returns_401_same_message(self, client: AsyncClient) -> None:
        mock_session = AsyncMock()
        mock_session.add = MagicMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        async def override() -> AsyncGenerator:
            yield mock_session

        app.dependency_overrides[get_session] = override

        res = await client.post(
            "/engine/users/verify",
            json={"email": "nobody@example.com", "password": "securepass123"},
        )

        assert res.status_code == 401
        body = res.json()
        assert body["error"]["type"] == "invalid_credentials"
        # Same error message as wrong password — no email enumeration
        assert body["error"]["message"] == "Invalid email or password"


def _make_token(
    id: int = 1,
    user_id: int = 1,
    token_hash: str = "abc123hash",
    hours_until_expiry: float = 1.0,
    used: bool = False,
) -> PasswordResetToken:
    """Create a PasswordResetToken model instance for testing."""
    now = datetime.now(UTC)
    token = PasswordResetToken(
        user_id=user_id,
        token_hash=token_hash,
        expires_at=now + timedelta(hours=hours_until_expiry),
    )
    object.__setattr__(token, "id", id)
    object.__setattr__(token, "created_at", now)
    if used:
        object.__setattr__(token, "used_at", now)
    return token


class TestPasswordResetRequest:
    """Tests for POST /engine/users/reset-password/request."""

    async def test_request_with_valid_email(self, client: AsyncClient) -> None:
        mock_session = AsyncMock()
        user = _make_user(email="reset@example.com")
        # First call: select user. Second call: update (invalidate old tokens).
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = user
        mock_update_result = MagicMock()
        mock_session.execute.side_effect = [mock_user_result, mock_update_result]
        mock_session.add = MagicMock()

        async def override() -> AsyncGenerator:
            yield mock_session

        app.dependency_overrides[get_session] = override

        with patch("engine.api.users.send_password_reset_email") as mock_email:
            res = await client.post(
                "/engine/users/reset-password/request",
                json={"email": "reset@example.com"},
            )

        assert res.status_code == 200
        assert "reset link has been sent" in res.json()["message"]
        mock_email.assert_called_once()
        # Verify token was added to session
        mock_session.add.assert_called_once()
        added_token = mock_session.add.call_args[0][0]
        assert isinstance(added_token, PasswordResetToken)
        assert added_token.user_id == user.id

    async def test_request_with_nonexistent_email_returns_200(self, client: AsyncClient) -> None:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        async def override() -> AsyncGenerator:
            yield mock_session

        app.dependency_overrides[get_session] = override

        with patch("engine.api.users.send_password_reset_email") as mock_email:
            res = await client.post(
                "/engine/users/reset-password/request",
                json={"email": "nobody@example.com"},
            )

        assert res.status_code == 200
        # Same message as valid email — no enumeration
        assert "reset link has been sent" in res.json()["message"]
        mock_email.assert_not_called()

    async def test_request_invalidates_previous_tokens(self, client: AsyncClient) -> None:
        mock_session = AsyncMock()
        user = _make_user(email="multi@example.com")
        mock_user_result = MagicMock()
        mock_user_result.scalar_one_or_none.return_value = user
        mock_update_result = MagicMock()
        mock_session.execute.side_effect = [mock_user_result, mock_update_result]
        mock_session.add = MagicMock()

        async def override() -> AsyncGenerator:
            yield mock_session

        app.dependency_overrides[get_session] = override

        with patch("engine.api.users.send_password_reset_email"):
            res = await client.post(
                "/engine/users/reset-password/request",
                json={"email": "multi@example.com"},
            )

        assert res.status_code == 200
        # Should have two execute calls: select user + update (invalidate old tokens)
        assert mock_session.execute.call_count == 2


class TestPasswordResetConfirm:
    """Tests for POST /engine/users/reset-password/confirm."""

    async def test_confirm_with_valid_token(self, client: AsyncClient) -> None:
        raw_token = "valid-test-token-abc"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        user = _make_user(email="confirm@example.com")
        user.password_hash = "$argon2id$old_hash"
        token_record = _make_token(user_id=user.id, token_hash=token_hash)

        mock_session = AsyncMock()
        mock_token_result = MagicMock()
        mock_token_result.scalar_one_or_none.return_value = token_record
        mock_user_result = MagicMock()
        mock_user_result.scalar_one.return_value = user
        mock_session.execute.side_effect = [mock_token_result, mock_user_result]

        async def override() -> AsyncGenerator:
            yield mock_session

        app.dependency_overrides[get_session] = override

        with patch("engine.api.users.ph") as mock_ph:
            mock_ph.hash.return_value = "$argon2id$new_hash"
            res = await client.post(
                "/engine/users/reset-password/confirm",
                json={"token": raw_token, "password": "newpassword123"},
            )

        assert res.status_code == 200
        assert "reset successfully" in res.json()["message"]
        # Password should be updated
        assert user.password_hash == "$argon2id$new_hash"
        # Token should be marked as used
        assert token_record.used_at is not None

    async def test_confirm_with_expired_token(self, client: AsyncClient) -> None:
        raw_token = "expired-test-token"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        token_record = _make_token(token_hash=token_hash, hours_until_expiry=-1.0)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = token_record
        mock_session.execute.return_value = mock_result

        async def override() -> AsyncGenerator:
            yield mock_session

        app.dependency_overrides[get_session] = override

        res = await client.post(
            "/engine/users/reset-password/confirm",
            json={"token": raw_token, "password": "newpassword123"},
        )

        assert res.status_code == 400
        body = res.json()
        assert body["error"]["type"] == "token_expired"

    async def test_confirm_with_already_used_token(self, client: AsyncClient) -> None:
        raw_token = "used-test-token"
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        token_record = _make_token(token_hash=token_hash, used=True)

        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = token_record
        mock_session.execute.return_value = mock_result

        async def override() -> AsyncGenerator:
            yield mock_session

        app.dependency_overrides[get_session] = override

        res = await client.post(
            "/engine/users/reset-password/confirm",
            json={"token": raw_token, "password": "newpassword123"},
        )

        assert res.status_code == 400
        body = res.json()
        assert body["error"]["type"] == "invalid_token"

    async def test_confirm_with_invalid_token(self, client: AsyncClient) -> None:
        mock_session = AsyncMock()
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_session.execute.return_value = mock_result

        async def override() -> AsyncGenerator:
            yield mock_session

        app.dependency_overrides[get_session] = override

        res = await client.post(
            "/engine/users/reset-password/confirm",
            json={"token": "nonexistent-token", "password": "newpassword123"},
        )

        assert res.status_code == 400
        body = res.json()
        assert body["error"]["type"] == "invalid_token"

    async def test_confirm_with_short_password(self, client: AsyncClient) -> None:
        res = await client.post(
            "/engine/users/reset-password/confirm",
            json={"token": "any-token", "password": "short"},
        )
        assert res.status_code == 422
