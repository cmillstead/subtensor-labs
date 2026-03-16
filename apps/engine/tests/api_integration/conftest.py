"""Override parent conftest — these tests use a real database, not mocks."""

import pytest


@pytest.fixture(autouse=True)
def _override_session():
    """Override the parent conftest's _override_session (no-op).

    The parent conftest installs a mock session via app.dependency_overrides.
    This fixture takes precedence (same name, closer conftest) and does nothing,
    allowing each test file to set up its own real-DB session override.
    """
    yield
