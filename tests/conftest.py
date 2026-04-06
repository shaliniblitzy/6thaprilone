"""
Blitzy Platform API Test Suite — Shared Pytest Fixtures

Provides all test modules with common infrastructure including:

* Authenticated :class:`APIClient` instances for API endpoint interaction
* Environment-based :class:`Settings` configuration loaded from ``.env``
  files and ``config/settings.yaml``
* Test data identifiers (project ID, run ID) sourced from environment
  variables
* Conditional skip markers for tests that require an active in-progress
  code-generation run
* Accepted ``percent_complete`` field-name variants for cross-convention
  validation

**Consumed by every test module in the suite:**

- ``tests/test_runs_metering.py``
- ``tests/test_runs_metering_current.py``
- ``tests/test_project.py``
- ``tests/test_cross_api_consistency.py``
- ``tests/test_edge_cases.py``

Design Rules (AAP §0.7.1)
--------------------------
- **Environment Configuration Rule** — all environment-specific values are
  read from environment variables or ``.env`` files; nothing is hard-coded.
- **Test Isolation Rule** — shared state flows exclusively through pytest
  fixtures; no module-level globals are used.
- **Graceful Failure** — missing configuration triggers ``pytest.skip()``
  with a descriptive message referencing ``.env.example``, rather than an
  unhandled exception.
"""

from __future__ import annotations

import os

import pytest

from src.api_client import APIClient
from src.config import Settings


# ---------------------------------------------------------------------------
# Pytest hook — custom marker registration
# ---------------------------------------------------------------------------

def pytest_configure(config: pytest.Config) -> None:
    """Register custom markers used by the test suite.

    Registers the ``requires_active_run`` marker so that tests depending
    on a live, in-progress code-generation run can be selectively skipped
    or filtered via ``pytest -m "not requires_active_run"``.

    This registration is redundant with declarations in ``pytest.ini`` but
    ensures IDE auto-complete and linting tools recognise the marker even
    when only ``conftest.py`` is analysed.

    Parameters
    ----------
    config : pytest.Config
        The pytest configuration object provided by the framework.
    """
    config.addinivalue_line(
        "markers",
        "requires_active_run: Test requires an active in-progress "
        "code generation run",
    )


# ---------------------------------------------------------------------------
# Session-scoped fixtures — expensive / shared objects
# ---------------------------------------------------------------------------

@pytest.fixture(scope="session")
def settings() -> Settings:
    """Load test configuration from environment variables and settings.yaml.

    Creates a single :class:`Settings` instance per test session by calling
    :meth:`Settings.from_env`.  The instance reads ``BASE_URL``,
    ``API_TOKEN``, ``TEST_PROJECT_ID``, ``TEST_RUN_ID``, and other knobs
    from the process environment (or a ``.env`` file) and merges in any
    overrides defined in ``config/settings.yaml``.

    Returns
    -------
    Settings
        Fully populated configuration instance.

    Notes
    -----
    This fixture does **not** call ``validate_required_settings()`` —
    downstream fixtures that depend on specific fields perform their own
    validation and skip gracefully when the required values are absent.
    """
    return Settings.from_env()


@pytest.fixture(scope="session")
def base_url(settings: Settings) -> str:
    """Provide the Blitzy Platform API base URL from configuration.

    Reads ``settings.base_url`` and skips the requesting test with a
    descriptive message when the value is empty (i.e. the ``BASE_URL``
    environment variable was not set).

    Parameters
    ----------
    settings : Settings
        Session-scoped configuration fixture.

    Returns
    -------
    str
        The configured API base URL (e.g. ``https://api.blitzy.com``).
    """
    if not settings.base_url:
        pytest.skip(
            "BASE_URL environment variable not set. "
            "See .env.example for setup instructions."
        )
    return settings.base_url


@pytest.fixture(scope="session")
def api_client(settings: Settings) -> APIClient:
    """Create an authenticated :class:`APIClient` ready to call all endpoints.

    Validates that the critical configuration values (``BASE_URL``,
    ``API_TOKEN``, ``TEST_PROJECT_ID``) are present by calling
    :meth:`Settings.validate_required_settings`.  If any are missing the
    test is skipped with a descriptive message rather than raising an
    unhandled error.

    Parameters
    ----------
    settings : Settings
        Session-scoped configuration fixture providing connection details.

    Returns
    -------
    APIClient
        A session-scoped HTTP client instance with ``Authorization``,
        ``Content-Type``, and ``Accept`` headers pre-configured.
    """
    try:
        settings.validate_required_settings()
    except ValueError as exc:
        pytest.skip(
            f"Missing required configuration: {exc}"
        )

    return APIClient(settings)


@pytest.fixture(scope="session")
def test_project_id(settings: Settings) -> str:
    """Provide the project ID used for endpoint-specific tests.

    The value is sourced from the ``TEST_PROJECT_ID`` environment variable
    (via :class:`Settings`).  Tests that require a project with existing
    code-generation runs depend on this fixture.

    Parameters
    ----------
    settings : Settings
        Session-scoped configuration fixture.

    Returns
    -------
    str
        The project identifier configured for testing.
    """
    if not settings.test_project_id:
        pytest.skip(
            "TEST_PROJECT_ID environment variable not set. "
            "A project with existing code generation runs is required. "
            "See .env.example for setup instructions."
        )
    return settings.test_project_id


@pytest.fixture(scope="session")
def test_run_id(settings: Settings) -> str:
    """Provide a specific run ID for targeted metering tests.

    The value is sourced from the ``TEST_RUN_ID`` environment variable
    (via :class:`Settings`).  Tests that validate metering data for a
    particular code-generation run depend on this fixture.

    Parameters
    ----------
    settings : Settings
        Session-scoped configuration fixture.

    Returns
    -------
    str
        The run identifier configured for testing.
    """
    if not settings.test_run_id:
        pytest.skip(
            "TEST_RUN_ID environment variable not set. "
            "A specific run ID is required for targeted metering tests. "
            "See .env.example for setup instructions."
        )
    return settings.test_run_id


@pytest.fixture(scope="session")
def percent_complete_field_names(settings: Settings) -> list:
    """Provide the list of accepted ``percent_complete`` field-name variants.

    Returns the configured field-name variants from :class:`Settings`,
    falling back to the default ``["percent_complete", "percentComplete"]``
    if the YAML configuration does not override them.  Using this fixture
    prevents individual test files from hard-coding field names.

    Parameters
    ----------
    settings : Settings
        Session-scoped configuration fixture.

    Returns
    -------
    list of str
        Accepted JSON field-name variants (e.g.
        ``["percent_complete", "percentComplete"]``).
    """
    field_names = settings.percent_complete_field_names
    if not field_names:
        # Defensive fallback — should never be needed given Settings defaults
        return ["percent_complete", "percentComplete"]
    return list(field_names)


# ---------------------------------------------------------------------------
# Function-scoped fixtures — per-test checks
# ---------------------------------------------------------------------------

@pytest.fixture
def active_run_check(api_client: APIClient) -> dict:
    """Verify that an active in-progress run exists and return its data.

    Calls ``GET /runs/metering/current`` via the :class:`APIClient`.  If
    the endpoint returns empty or null data (indicating no active run),
    the requesting test is skipped with a descriptive message.

    This fixture is intended for tests marked with
    ``@pytest.mark.requires_active_run`` that cannot produce meaningful
    assertions without a live code-generation run.

    Parameters
    ----------
    api_client : APIClient
        Session-scoped authenticated HTTP client.

    Returns
    -------
    dict
        The parsed JSON body from ``GET /runs/metering/current``
        representing the active run's metering data.
    """
    try:
        response = api_client.get_runs_metering_current()
    except Exception as exc:
        pytest.skip(
            f"Could not verify active run status: {exc}"
        )
        # The line below is unreachable but satisfies type checkers that
        # expect a return value on all code paths.
        return {}  # pragma: no cover

    # Handle various "no active run" response shapes
    if response is None:
        pytest.skip(
            "No active in-progress run detected (response is None). "
            "Skipping test that requires an active run."
        )
    if isinstance(response, dict) and not response:
        pytest.skip(
            "No active in-progress run detected (empty response). "
            "Skipping test that requires an active run."
        )

    return response
