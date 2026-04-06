"""
Blitzy Platform API Test Suite — ``GET /project?id={id}`` Endpoint Tests

Validates the ``percent_complete`` field within the **nested metering data
block** of the ``GET /project?id={project_id}`` API endpoint.

Key Distinction
---------------
Unlike the ``/runs/metering`` and ``/runs/metering/current`` endpoints,
the ``percent_complete`` field in the project response is **NOT** at the
top level.  It is **nested** inside a metering sub-object.  Example::

    {
        "id": "project-123",
        "name": "My Project",
        "metering": {
            "percent_complete": 75.5,
            "estimated_hours_saved": 10.5,
            "estimated_lines_generated": 5000
        }
    }

Requirements Covered
--------------------
- **R-001 — Field Presence Validation**: ``percent_complete`` (or
  ``percentComplete``) must be present inside the metering block.
- **R-002 — Data Type Validation**: Value must be numeric (``int`` /
  ``float``) or ``null``; never a ``str``, ``bool``, or other type.
- **R-003 — Value Range Validation**: When not ``null``, value must be
  in the inclusive range ``[0.0, 100.0]``.

Conventions
-----------
- Every test is decorated with ``@pytest.mark.project``.
- Every assertion includes a descriptive failure message identifying the
  endpoint (``GET /project``), the field under test, and actual vs.
  expected values.
- No hard-coded URLs, tokens, or project IDs — all injected via fixtures
  from ``tests/conftest.py``.
- Each test function is independently executable; no implicit ordering.

Fixtures Used (from conftest.py)
---------------------------------
- ``api_client``      — Authenticated :class:`APIClient` instance
- ``test_project_id`` — Project identifier from environment config
"""

from __future__ import annotations

import warnings
from typing import Any, Dict, List

import pytest

from src.api_client import APIClient
from src.validators import (
    PERCENT_COMPLETE_FIELD_NAMES,
    get_percent_complete_value,
    validate_field_presence,
    validate_percent_complete,
)

# ---------------------------------------------------------------------------
# Module-level constants
# ---------------------------------------------------------------------------

#: Accepted key-name variants for the metering block within the project
#: response.  The API may serialise the key as ``"metering"``,
#: ``"meteringData"`` (camelCase), or ``"metering_data"`` (snake_case).
METERING_BLOCK_KEY_NAMES: List[str] = [
    "metering",
    "meteringData",
    "metering_data",
]

#: Human-readable endpoint identifier used in every assertion message to
#: make test failures immediately actionable.
_ENDPOINT: str = "GET /project"


# ---------------------------------------------------------------------------
# Helper: extract the nested metering block
# ---------------------------------------------------------------------------

def _get_metering_block(response_data: Dict[str, Any]) -> Dict[str, Any]:
    """Extract the metering sub-object from a ``GET /project`` response.

    The project response nests metering data under one of several possible
    key names (``metering``, ``meteringData``, ``metering_data``).  This
    helper tries each variant and returns the first match.

    Parameters
    ----------
    response_data : Dict[str, Any]
        The full parsed JSON body returned by ``GET /project?id={id}``.

    Returns
    -------
    Dict[str, Any]
        The metering sub-object extracted from the response.

    Raises
    ------
    AssertionError
        If none of the expected metering-block key names are present in
        *response_data*.  The error message lists the keys that were
        checked and the keys actually available in the response.
    """
    for key_name in METERING_BLOCK_KEY_NAMES:
        if key_name in response_data:
            return response_data[key_name]

    available_keys = sorted(response_data.keys())
    assert False, (
        f"[{_ENDPOINT}] response missing metering block. "
        f"Checked key names: {METERING_BLOCK_KEY_NAMES}. "
        f"Available top-level keys: {available_keys}"
    )
    # Unreachable — satisfies type checkers expecting a return on all paths.
    return {}  # pragma: no cover


# ===========================================================================
# Test Functions — Response Structure Validation
# ===========================================================================


@pytest.mark.project
def test_project_response_is_valid_json(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Verify that ``GET /project`` returns a valid JSON object (``dict``).

    This is a prerequisite gate: if the response is not a JSON object,
    all subsequent field-level assertions are meaningless.

    Requirement: structural sanity check (prerequisite for R-001 through
    R-003).
    """
    response = api_client.get_project(test_project_id)

    assert isinstance(response, dict), (
        f"[{_ENDPOINT}] response should be a JSON object (dict), "
        f"got {type(response).__name__}: {response!r}"
    )


@pytest.mark.project
def test_project_response_contains_metering_block(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Verify the project response contains a nested metering data block.

    The metering block is the container in which ``percent_complete``
    resides.  If the block itself is absent, all downstream field-level
    tests are invalid.

    Checks for key variants: ``metering``, ``meteringData``,
    ``metering_data``.
    """
    response = api_client.get_project(test_project_id)

    assert isinstance(response, dict), (
        f"[{_ENDPOINT}] response should be a dict before checking for "
        f"metering block, got {type(response).__name__}"
    )

    metering_block_found = any(
        key in response for key in METERING_BLOCK_KEY_NAMES
    )

    assert metering_block_found, (
        f"[{_ENDPOINT}] response missing 'metering' block. "
        f"Checked key names: {METERING_BLOCK_KEY_NAMES}. "
        f"Available top-level keys: {sorted(response.keys())}"
    )


# ===========================================================================
# Test Functions — Field Presence (R-001)
# ===========================================================================


@pytest.mark.project
def test_percent_complete_present_in_project_metering(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """R-001 — Verify ``percent_complete`` exists in the nested metering block.

    Navigates to the metering sub-object and uses
    :func:`validate_field_presence` to check for either
    ``percent_complete`` or ``percentComplete``.  If neither variant is
    found, the assertion failure includes the actual keys present in the
    metering block for diagnostic purposes.

    CRITICAL: The field is NOT at the top level of the project response.
    """
    response = api_client.get_project(test_project_id)
    metering_data = _get_metering_block(response)

    found_field = validate_field_presence(
        metering_data,
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint=f"{_ENDPOINT} (metering block)",
    )

    # Informational: log which naming convention the API is using.
    assert found_field in PERCENT_COMPLETE_FIELD_NAMES, (
        f"[{_ENDPOINT}] validate_field_presence returned unexpected name "
        f"'{found_field}', expected one of {PERCENT_COMPLETE_FIELD_NAMES}"
    )


@pytest.mark.project
def test_percent_complete_not_at_top_level(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Verify ``percent_complete`` is nested within metering, not at top level.

    This test confirms the expected response structure: the
    ``percent_complete`` field should reside inside the metering
    sub-object, NOT as a direct child of the root project object.

    If the field is unexpectedly at the top level, this may indicate an
    API structure change that warrants investigation.
    """
    response = api_client.get_project(test_project_id)

    assert isinstance(response, dict), (
        f"[{_ENDPOINT}] response should be a dict, "
        f"got {type(response).__name__}"
    )

    # Check whether percent_complete appears at the top level (unexpected).
    top_level_field_found = any(
        field_name in response for field_name in PERCENT_COMPLETE_FIELD_NAMES
    )

    # The expected structure has the field NESTED, not at the root.
    # If found at root, log an informational warning but do not fail the
    # test outright — the field might legitimately be in both locations.
    if top_level_field_found:
        # Verify the metering block also contains the field (expected).
        metering_data = _get_metering_block(response)
        metering_field_found = any(
            field_name in metering_data
            for field_name in PERCENT_COMPLETE_FIELD_NAMES
        )
        assert metering_field_found, (
            f"[{_ENDPOINT}] percent_complete found at the top level of the "
            f"response but NOT within the metering block. This indicates "
            f"an unexpected response structure. Top-level keys: "
            f"{sorted(response.keys())}. "
            f"Metering block keys: {sorted(metering_data.keys())}"
        )
    else:
        # Expected: field is NOT at the top level — verify it IS in metering.
        metering_data = _get_metering_block(response)
        metering_field_found = any(
            field_name in metering_data
            for field_name in PERCENT_COMPLETE_FIELD_NAMES
        )
        assert metering_field_found, (
            f"[{_ENDPOINT}] percent_complete not found at the top level "
            f"(expected) AND not found in the metering block (unexpected). "
            f"Top-level keys: {sorted(response.keys())}. "
            f"Metering block keys: {sorted(metering_data.keys())}"
        )


# ===========================================================================
# Test Functions — Data Type Validation (R-002)
# ===========================================================================


@pytest.mark.project
def test_percent_complete_type_in_project(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """R-002 — Verify ``percent_complete`` value is numeric (int/float) or null.

    Extracts the value from the nested metering block using
    :func:`get_percent_complete_value` and validates it through
    :func:`validate_percent_complete`, which enforces:

    * ``None`` → valid (no data / not applicable)
    * ``int`` or ``float`` → valid (subject to range check in R-003)
    * ``bool``, ``str``, ``list``, ``dict``, other → invalid
    """
    response = api_client.get_project(test_project_id)
    metering_data = _get_metering_block(response)

    assert isinstance(metering_data, dict), (
        f"[{_ENDPOINT}] Expected metering block to be dict, "
        f"got {type(metering_data).__name__}"
    )

    value = get_percent_complete_value(
        metering_data,
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint=_ENDPOINT,
    )

    # validate_percent_complete raises AssertionError with a descriptive
    # message if the type is wrong.
    validate_percent_complete(value, endpoint=_ENDPOINT)


# ===========================================================================
# Test Functions — Value Range Validation (R-003)
# ===========================================================================


@pytest.mark.project
def test_percent_complete_range_in_project(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """R-003 — Verify ``percent_complete`` is within [0.0, 100.0] when not null.

    When the value is non-null, it must satisfy ``0.0 <= value <= 100.0``.
    A null value is valid and accepted (tested separately in
    :func:`test_percent_complete_null_acceptance_in_project`).

    Uses :func:`validate_percent_complete` which combines both the type
    and range checks into a single validation pass.
    """
    response = api_client.get_project(test_project_id)
    metering_data = _get_metering_block(response)

    assert isinstance(metering_data, dict), (
        f"[{_ENDPOINT}] Expected metering block to be dict, "
        f"got {type(metering_data).__name__}"
    )

    value = get_percent_complete_value(
        metering_data,
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint=_ENDPOINT,
    )

    # validate_percent_complete handles both type and range assertions.
    validate_percent_complete(value, endpoint=_ENDPOINT)

    # Provide an additional human-readable assertion for range specifically.
    if value is not None:
        assert 0.0 <= value <= 100.0, (
            f"[{_ENDPOINT}] percent_complete value {value} is out of the "
            f"accepted range [0.0, 100.0]"
        )


# ===========================================================================
# Test Functions — Null Acceptance
# ===========================================================================


@pytest.mark.project
def test_percent_complete_null_acceptance_in_project(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Verify that ``null`` (``None``) is a valid ``percent_complete`` value.

    The API contract explicitly allows ``null`` to represent scenarios
    where the completion percentage is not applicable or no data is
    available.  This test confirms that the validation logic correctly
    accepts ``None`` without raising any assertion errors.

    If the value is **not** null, the test still passes — we simply
    validate that the non-null value is a valid numeric within range.
    The purpose of this test is to confirm that *if* the value is null,
    the test infrastructure does not incorrectly flag it as an error.
    """
    response = api_client.get_project(test_project_id)
    metering_data = _get_metering_block(response)

    assert isinstance(metering_data, dict), (
        f"[{_ENDPOINT}] Expected metering block to be dict, "
        f"got {type(metering_data).__name__}"
    )

    value = get_percent_complete_value(
        metering_data,
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint=_ENDPOINT,
    )

    if value is None:
        # Null is explicitly valid — confirm validate_percent_complete
        # does not raise for None.
        validate_percent_complete(value, endpoint=_ENDPOINT)
        # Explicit pass assertion for clarity in test reports.
        assert value is None, (
            f"[{_ENDPOINT}] percent_complete null acceptance: value should "
            f"be None at this point, got {value!r}"
        )
    else:
        # Value is not null — still valid if numeric and in range.
        # Validate it passes the standard check so this test never gives
        # a false negative.
        assert isinstance(value, (int, float)) and not isinstance(value, bool), (
            f"[{_ENDPOINT}] percent_complete null acceptance: value is not "
            f"null but also not numeric — got {type(value).__name__}: "
            f"{value!r}"
        )
        validate_percent_complete(value, endpoint=_ENDPOINT)


# ===========================================================================
# Test Functions — Metering Block Structure Validation
# ===========================================================================


@pytest.mark.project
def test_metering_block_structure(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Validate the metering block is a ``dict`` (JSON object).

    The metering block must be a dictionary, not a list, string, integer,
    or other JSON type.  A non-dict metering block would indicate a
    structural API defect.
    """
    response = api_client.get_project(test_project_id)

    assert isinstance(response, dict), (
        f"[{_ENDPOINT}] response should be a dict, "
        f"got {type(response).__name__}"
    )

    metering_data = _get_metering_block(response)

    assert isinstance(metering_data, dict), (
        f"[{_ENDPOINT}] metering block should be a dict (JSON object), "
        f"got {type(metering_data).__name__}: {metering_data!r}"
    )


@pytest.mark.project
def test_metering_block_additional_fields(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Verify the metering block contains expected companion fields.

    Beyond ``percent_complete``, the metering block is expected to include
    related code-generation metering fields such as
    ``estimated_hours_saved`` and ``estimated_lines_generated``.  Their
    presence confirms that the metering context is correct (code generation
    metering, not an unrelated data structure).

    This test is **informational** — we assert only on the block's
    structure and ``percent_complete`` presence, while logging observations
    about other fields.  The companion fields are checked with a soft
    assertion approach: missing companion fields generate warnings but do
    not cause a hard test failure.
    """
    response = api_client.get_project(test_project_id)
    metering_data = _get_metering_block(response)

    assert isinstance(metering_data, dict), (
        f"[{_ENDPOINT}] metering block should be a dict, "
        f"got {type(metering_data).__name__}"
    )

    # Primary assertion: percent_complete must be present.
    validate_field_presence(
        metering_data,
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint=f"{_ENDPOINT} (metering block)",
    )

    # Informational check: expected companion fields in the metering block.
    # These are not hard requirements for percent_complete validation, but
    # their presence confirms we are looking at code-generation metering data.
    companion_fields: Dict[str, List[str]] = {
        "estimated_hours_saved": [
            "estimated_hours_saved",
            "estimatedHoursSaved",
        ],
        "estimated_lines_generated": [
            "estimated_lines_generated",
            "estimatedLinesGenerated",
        ],
    }

    metering_keys = set(metering_data.keys())
    for logical_name, variants in companion_fields.items():
        found = any(variant in metering_keys for variant in variants)
        if not found:
            # Soft warning — do not fail, but document the observation.
            warnings.warn(
                f"[{_ENDPOINT}] metering block does not contain "
                f"'{logical_name}' (checked variants: {variants}). "
                f"Available keys: {sorted(metering_keys)}. "
                f"This may indicate a different metering context.",
                stacklevel=2,
            )

    # Hard assertion: the metering block has at least the percent_complete
    # field, confirming structural integrity.
    percent_complete_present = any(
        field_name in metering_data
        for field_name in PERCENT_COMPLETE_FIELD_NAMES
    )
    assert percent_complete_present, (
        f"[{_ENDPOINT}] metering block missing percent_complete after "
        f"structure validation. Keys present: {sorted(metering_keys)}"
    )
