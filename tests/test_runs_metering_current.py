"""
Blitzy Platform API Test Suite — ``GET /runs/metering/current`` Endpoint Tests

Validates the ``percent_complete`` field in the ``GET /runs/metering/current``
endpoint response.  This endpoint retrieves metering data for the **currently
active** (in-progress) code-generation run, returning a single metering object
reflecting real-time progress.

Endpoint Details (AAP §0.4.2):

    URL            : ``GET /runs/metering/current``
    Query Params   : Contextual — may require project or run identification
    Response       : Single metering object for the active run with
                     ``percent_complete`` reflecting real-time progress
    Trigger Context: Invoked during live run status views and auto-refresh
                     polling intervals
    Data Origin    : Real-time computation from the active run's
                     ``current_index / total_steps`` ratio

Key Distinction:

    This endpoint may return ``None``, an empty dict, or a ``null``
    ``percent_complete`` value when there is **no** active in-progress run.
    Tests must handle this gracefully: tests that require live run data are
    marked with ``@pytest.mark.requires_active_run`` and skipped
    automatically when no run is detected.

Requirement Coverage:

    R-001 — Field Presence Validation     (field must exist when data present)
    R-002 — Data Type Validation          (numeric or null, never str/bool)
    R-003 — Value Range Validation        (0.0 ≤ value ≤ 100.0 when not null)

Design Rules (AAP §0.7.1):

    * Every assertion includes a descriptive message identifying the endpoint,
      the field under test, and the actual-vs-expected value.
    * Generic assertions like ``assert True`` are prohibited.
    * Each test function is independently executable via pytest fixtures.
    * All tests carry the ``@pytest.mark.runs_metering_current`` marker.
    * Tests requiring an active in-progress run additionally carry
      ``@pytest.mark.requires_active_run``.
    * No hardcoded URLs, tokens, project IDs, or credentials.

Fixtures consumed from ``tests/conftest.py``:

    * ``api_client``                  — Authenticated :class:`APIClient` instance
    * ``active_run_check``            — Dict from current metering (skips if no run)
    * ``percent_complete_field_names``— List of accepted field name variants
"""

from __future__ import annotations

from typing import Any, Dict

import pytest

from src.api_client import APIClient
from src.validators import (
    PERCENT_COMPLETE_FIELD_NAMES,
    get_percent_complete_value,
    validate_field_presence,
    validate_percent_complete,
)


# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

_ENDPOINT: str = "GET /runs/metering/current"
"""Endpoint identifier used in all assertion messages for traceability."""


# ============================================================================
# Response Structure Tests
# ============================================================================

@pytest.mark.runs_metering_current
def test_current_metering_response_is_valid(
    api_client: APIClient,
) -> None:
    """Verify ``GET /runs/metering/current`` returns a valid JSON response.

    The HTTP client raises on non-200 status codes and JSON parse errors,
    so a successful call guarantees valid JSON.  This test additionally
    asserts that the top-level type is an acceptable response shape:

    * ``dict``  — metering data is present for an active run
    * ``list``  — alternative response envelope
    * ``None``  — no active run (some APIs return a JSON ``null`` literal)

    This test does **not** require an active run — a ``None`` or empty
    dict response is acceptable, indicating no run is in progress.
    """
    try:
        response = api_client.get_runs_metering_current()
    except Exception as exc:
        pytest.fail(
            f"{_ENDPOINT} raised an unexpected exception instead of "
            f"returning a valid JSON response: {type(exc).__name__}: {exc}"
        )

    # None is acceptable (JSON null → no active run).
    if response is None:
        return

    assert isinstance(response, (dict, list)), (
        f"{_ENDPOINT} should return valid JSON (dict, list, or null), "
        f"got {type(response).__name__}: {response!r}"
    )


# ============================================================================
# Field Presence Tests — R-001
# ============================================================================

@pytest.mark.runs_metering_current
@pytest.mark.requires_active_run
def test_percent_complete_present_in_current_metering(
    active_run_check: Dict[str, Any],
) -> None:
    """R-001 — ``percent_complete`` field exists in current metering response.

    Uses the ``active_run_check`` fixture which calls
    ``GET /runs/metering/current`` and skips the test automatically when
    no active in-progress run is detected.  When data is present, asserts
    that either ``percent_complete`` or ``percentComplete`` exists as a
    key in the response.
    """
    response = active_run_check
    assert isinstance(response, dict), (
        f"{_ENDPOINT} response should be a dict when an active run exists, "
        f"got {type(response).__name__}: {response!r}"
    )
    validate_field_presence(
        response,
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint=_ENDPOINT,
    )


@pytest.mark.runs_metering_current
@pytest.mark.requires_active_run
def test_percent_complete_field_naming_convention(
    active_run_check: Dict[str, Any],
) -> None:
    """Document which naming convention ``GET /runs/metering/current`` uses.

    Both ``percent_complete`` (snake_case) and ``percentComplete``
    (camelCase) are acceptable per AAP §0.7.1.  This test verifies that
    the endpoint uses one of the two conventions and records which variant
    was found for diagnostic purposes.

    The found field name must be one of the recognised variants — any
    other key name (e.g. ``pctComplete``, ``progress``) is a defect.
    """
    response = active_run_check
    assert isinstance(response, dict), (
        f"{_ENDPOINT} response should be a dict when an active run exists, "
        f"got {type(response).__name__}: {response!r}"
    )

    found_name: str = validate_field_presence(
        response,
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint=_ENDPOINT,
    )

    # Confirm the found name is one of the known variants — redundant
    # given validate_field_presence semantics, but explicit for clarity.
    assert found_name in PERCENT_COMPLETE_FIELD_NAMES, (
        f"{_ENDPOINT} returned an unexpected percent_complete field name: "
        f"'{found_name}'. Expected one of {PERCENT_COMPLETE_FIELD_NAMES}."
    )


# ============================================================================
# Data Type Validation Tests — R-002
# ============================================================================

@pytest.mark.runs_metering_current
@pytest.mark.requires_active_run
def test_percent_complete_type_in_current_metering(
    active_run_check: Dict[str, Any],
) -> None:
    """R-002 — ``percent_complete`` is numeric (int/float) or null.

    Extracts the ``percent_complete`` value from the current metering
    response and verifies it is ``None``, ``int``, or ``float`` — never
    a ``str``, ``bool``, ``list``, ``dict``, or any other non-numeric
    type.

    Uses :func:`validate_percent_complete` which explicitly rejects
    ``bool`` (a subclass of ``int`` in Python) to prevent ``True`` /
    ``False`` from silently passing.
    """
    response = active_run_check
    assert isinstance(response, dict), (
        f"{_ENDPOINT} response should be a dict when an active run exists, "
        f"got {type(response).__name__}: {response!r}"
    )

    value: Any = get_percent_complete_value(
        response,
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint=_ENDPOINT,
    )

    try:
        validate_percent_complete(value, endpoint=_ENDPOINT)
    except AssertionError as err:
        raise AssertionError(
            f"{_ENDPOINT} percent_complete has wrong type: expected numeric "
            f"or null, got {type(value).__name__}: {value!r}. "
            f"Original error: {err}"
        ) from err


# ============================================================================
# Value Range Validation Tests — R-003
# ============================================================================

@pytest.mark.runs_metering_current
@pytest.mark.requires_active_run
def test_percent_complete_range_in_current_metering(
    active_run_check: Dict[str, Any],
) -> None:
    """R-003 — ``percent_complete`` is within [0.0, 100.0] when not null.

    Extracts the ``percent_complete`` value and, when it is not ``None``,
    asserts that it falls within the inclusive range 0.0–100.0.  Null
    values are accepted (represent "no data") and do not trigger a range
    failure.

    Uses :func:`validate_percent_complete` for the combined type + range
    check, plus an explicit range assertion for a clearer failure message.
    """
    response = active_run_check
    assert isinstance(response, dict), (
        f"{_ENDPOINT} response should be a dict when an active run exists, "
        f"got {type(response).__name__}: {response!r}"
    )

    value: Any = get_percent_complete_value(
        response,
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint=_ENDPOINT,
    )

    # Full type + range validation via the shared validator
    validate_percent_complete(value, endpoint=_ENDPOINT)

    # Explicit range assertion for a more specific failure message
    if value is not None:
        assert isinstance(value, (int, float)) and not isinstance(value, bool), (
            f"{_ENDPOINT} percent_complete is not numeric: "
            f"got {type(value).__name__}: {value!r}"
        )
        assert 0.0 <= value <= 100.0, (
            f"{_ENDPOINT} percent_complete value {value} out of range "
            f"[0.0, 100.0]"
        )


# ============================================================================
# Live Run-Specific Tests
# ============================================================================

@pytest.mark.runs_metering_current
@pytest.mark.requires_active_run
def test_current_metering_in_progress_value(
    active_run_check: Dict[str, Any],
) -> None:
    """An actively in-progress run should report ``percent_complete < 100``.

    When the ``GET /runs/metering/current`` endpoint returns data for a
    live code-generation run, the ``percent_complete`` value should be
    strictly less than 100.0 — a "current" run that reports 100% is
    suspicious because a completed run should no longer be the "current"
    active run.

    Edge Case Handling:
        If the value is ``None``, the assertion is skipped because null
        represents "no data" and is acceptable even for an active run
        that has not yet reported progress.

    Note:
        A value of exactly 100.0 could theoretically occur during a
        brief window when the run has just finished but the endpoint has
        not yet updated.  This test treats 100.0 as a warning-worthy
        edge case — the assertion uses a soft informational message.
    """
    response = active_run_check
    assert isinstance(response, dict), (
        f"{_ENDPOINT} response should be a dict when an active run exists, "
        f"got {type(response).__name__}: {response!r}"
    )

    value: Any = get_percent_complete_value(
        response,
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint=_ENDPOINT,
    )

    # Null is acceptable — the run may not have reported progress yet
    if value is None:
        return

    # Type guard before numeric comparison
    assert isinstance(value, (int, float)) and not isinstance(value, bool), (
        f"{_ENDPOINT} percent_complete is not numeric for an in-progress run: "
        f"got {type(value).__name__}: {value!r}"
    )

    # Core assertion: an in-progress run should not report 100%
    assert value < 100.0, (
        f"{_ENDPOINT} reports percent_complete={value} for an in-progress "
        f"run — expected less than 100.0. A value of 100.0 suggests the run "
        f"has completed but is still being reported as 'current'."
    )


# ============================================================================
# No Active Run Handling Tests
# ============================================================================

@pytest.mark.runs_metering_current
def test_current_metering_no_active_run(
    api_client: APIClient,
) -> None:
    """When no active run exists the API should return a valid response.

    This test verifies that the ``GET /runs/metering/current`` endpoint
    responds gracefully when no code-generation run is currently in
    progress.  The API is NOT expected to return an error — it should
    return one of:

    * ``None`` / JSON ``null``   — explicitly no data
    * An empty dict ``{}``       — no active run indicator
    * A dict with ``percent_complete`` set to ``null`` — field present
      but no meaningful value

    All three shapes are acceptable.  The test only fails if the
    response is an unexpected type (e.g. a string or integer) that
    would indicate an API serialisation bug.
    """
    try:
        response = api_client.get_runs_metering_current()
    except Exception as exc:
        pytest.fail(
            f"{_ENDPOINT} raised an unexpected exception when no active "
            f"run may exist: {type(exc).__name__}: {exc}"
        )

    # Acceptable shapes: None, dict, list
    if response is None:
        # JSON null — perfectly valid "no active run" indicator
        return

    assert isinstance(response, (dict, list)), (
        f"{_ENDPOINT} returned an unexpected type when no active run "
        f"may exist: got {type(response).__name__}: {response!r}. "
        f"Expected dict, list, or null."
    )

    # If a dict with data, verify that percent_complete (if present) is
    # either null or a valid numeric value — never an error sentinel or
    # garbage data.
    if isinstance(response, dict) and response:
        # Check if any percent_complete field name variant is present
        has_field: bool = any(
            name in response for name in PERCENT_COMPLETE_FIELD_NAMES
        )
        if has_field:
            value: Any = get_percent_complete_value(
                response,
                PERCENT_COMPLETE_FIELD_NAMES,
                endpoint=_ENDPOINT,
            )
            # Value must be null or valid numeric — delegate to validator
            validate_percent_complete(value, endpoint=_ENDPOINT)


# ============================================================================
# Null Acceptance Tests
# ============================================================================

@pytest.mark.runs_metering_current
def test_percent_complete_null_for_no_active_run(
    api_client: APIClient,
) -> None:
    """``null`` is a valid ``percent_complete`` value per the AAP validation
    matrix.

    Verifies that the validation logic correctly accepts ``None`` without
    raising.  This test has two paths:

    1. If the endpoint returns a response containing
       ``percent_complete=null``, the validator must accept it.
    2. If the endpoint returns ``None`` or an empty response (no active
       run), the test still passes — null acceptance is verified via the
       validator's direct invocation as a safety net.

    In either case, this test confirms that ``null`` is never treated as
    an error by the test suite's validation infrastructure.
    """
    try:
        response = api_client.get_runs_metering_current()
    except Exception as exc:
        pytest.fail(
            f"{_ENDPOINT} raised an unexpected exception: "
            f"{type(exc).__name__}: {exc}"
        )

    # Path 1: If response has percent_complete, validate it (null is OK)
    if isinstance(response, dict) and response:
        has_field: bool = any(
            name in response for name in PERCENT_COMPLETE_FIELD_NAMES
        )
        if has_field:
            value: Any = get_percent_complete_value(
                response,
                PERCENT_COMPLETE_FIELD_NAMES,
                endpoint=_ENDPOINT,
            )
            # This should NOT raise even if value is None
            validate_percent_complete(value, endpoint=_ENDPOINT)

    # Path 2: Safety net — explicitly verify the validator accepts None
    # regardless of what the API returned.  This guarantees the null-
    # acceptance contract is honoured even if no null data was returned
    # from the live endpoint.
    validate_percent_complete(
        None,
        endpoint=f"{_ENDPOINT} [null acceptance safety check]",
    )
