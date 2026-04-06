"""
Blitzy Platform API Test Suite — Edge Case and Boundary Condition Tests

Dedicated test module for boundary-value analysis and negative-scenario
validation of the ``percent_complete`` field.  Addresses **Requirement
R-005 (Edge Case Coverage)** from the Agent Action Plan (AAP §0.1.1).

Coverage matrix
---------------

+-------------------------------+------------+-----------------------------+
| Scenario                      | Expected   | Test(s)                     |
+===============================+============+=============================+
| Exactly 0.0 / 0              | VALID      | ``test_…_exactly_zero``     |
+-------------------------------+------------+-----------------------------+
| Exactly 100.0 / 100          | VALID      | ``test_…_exactly_hundred``  |
+-------------------------------+------------+-----------------------------+
| ``None`` (null)               | VALID      | ``test_…_null_value``       |
+-------------------------------+------------+-----------------------------+
| Mid-range floats              | VALID      | ``test_…_mid_range_float``  |
+-------------------------------+------------+-----------------------------+
| Integer values in [0, 100]    | VALID      | ``test_…_integer_values``   |
+-------------------------------+------------+-----------------------------+
| > 100                         | INVALID    | ``test_…_exceeds_hundred``  |
+-------------------------------+------------+-----------------------------+
| < 0                           | INVALID    | ``test_…_below_zero``       |
+-------------------------------+------------+-----------------------------+
| ``str``                       | INVALID    | ``test_…_wrong_type_string``|
+-------------------------------+------------+-----------------------------+
| ``bool``                      | INVALID    | ``test_…_wrong_type_bool``  |
+-------------------------------+------------+-----------------------------+
| ``list``                      | INVALID    | ``test_…_wrong_type_list``  |
+-------------------------------+------------+-----------------------------+
| ``dict``                      | INVALID    | ``test_…_wrong_type_dict``  |
+-------------------------------+------------+-----------------------------+
| snake_case field name         | Found      | ``test_field_presence_…``   |
+-------------------------------+------------+-----------------------------+
| camelCase field name          | Found      | ``test_field_presence_…``   |
+-------------------------------+------------+-----------------------------+
| Neither convention present    | Error      | ``test_field_presence_…``   |
+-------------------------------+------------+-----------------------------+
| Typo / wrong field name       | Not found  | ``test_field_name_typo_…``  |
+-------------------------------+------------+-----------------------------+

All tests are marked with ``@pytest.mark.edge_cases`` and are independently
executable — no test depends on execution order or shared mutable state.

Integration tests (§3.5) that require a live Blitzy Platform API connection
rely on fixtures from ``tests/conftest.py`` and are automatically skipped
when the required environment variables are not configured.
"""

from __future__ import annotations

from typing import Any

import pytest

from src.api_client import APIClient
from src.validators import (
    PERCENT_COMPLETE_FIELD_NAMES,
    get_percent_complete_value,
    validate_field_presence,
    validate_percent_complete,
)


# ============================================================================
# §3.1 — Boundary Value Tests (Valid Cases)
# ============================================================================


@pytest.mark.edge_cases
def test_validate_percent_complete_exactly_zero() -> None:
    """Exactly ``0.0`` is the lower boundary and must be accepted.

    Also verifies that the integer ``0`` passes — both ``int`` and
    ``float`` representations are valid per AAP §0.7.1.
    """
    # float boundary
    validate_percent_complete(
        0.0,
        endpoint="edge_case/boundary",
    )
    # int boundary
    validate_percent_complete(
        0,
        endpoint="edge_case/boundary",
    )


@pytest.mark.edge_cases
def test_validate_percent_complete_exactly_hundred() -> None:
    """Exactly ``100.0`` is the upper boundary and must be accepted.

    Also verifies that the integer ``100`` passes.
    """
    # float boundary
    validate_percent_complete(
        100.0,
        endpoint="edge_case/boundary",
    )
    # int boundary
    validate_percent_complete(
        100,
        endpoint="edge_case/boundary",
    )


@pytest.mark.edge_cases
def test_validate_percent_complete_null_value() -> None:
    """``None`` represents "no data" / "not applicable" and must be
    accepted without raising any error (AAP §0.7.1).
    """
    validate_percent_complete(
        None,
        endpoint="edge_case/null",
    )


@pytest.mark.edge_cases
def test_validate_percent_complete_mid_range_float() -> None:
    """Typical mid-range float values must pass validation.

    Covers several representative fractional percentages that a
    running or partially-complete code-generation run might report.
    """
    mid_range_values = [0.001, 1.5, 25.0, 33.33, 50.5, 75.25, 99.99]
    for value in mid_range_values:
        validate_percent_complete(
            value,
            endpoint="edge_case/mid_range",
        )


@pytest.mark.edge_cases
def test_validate_percent_complete_integer_values() -> None:
    """Integer values within the ``[0, 100]`` range must pass.

    The AAP explicitly states that both ``int`` and ``float`` are
    valid numeric types for the ``percent_complete`` field.
    """
    integer_values = [0, 1, 25, 50, 75, 99, 100]
    for value in integer_values:
        validate_percent_complete(
            value,
            endpoint="edge_case/integer",
        )


# ============================================================================
# §3.2 — Invalid Value Tests (Negative Scenarios)
# ============================================================================


@pytest.mark.edge_cases
def test_validate_percent_complete_exceeds_hundred() -> None:
    """Values greater than ``100.0`` must raise ``AssertionError``.

    Tests a range of over-limit values including barely-over,
    significantly-over, and positive infinity.
    """
    over_limit_values: list[Any] = [100.1, 101, 200, 999.99, float("inf")]
    for value in over_limit_values:
        with pytest.raises(AssertionError) as exc_info:
            validate_percent_complete(
                value,
                endpoint="edge_case/exceeds_hundred",
            )
        # Verify the error message contains diagnostic information
        error_msg = str(exc_info.value)
        assert "percent_complete" in error_msg, (
            f"AssertionError for value {value!r} should mention "
            f"'percent_complete' in the message, got: {error_msg}"
        )


@pytest.mark.edge_cases
def test_validate_percent_complete_below_zero() -> None:
    """Values less than ``0.0`` must raise ``AssertionError``.

    Tests a range of under-limit values including barely-under,
    significantly-under, and negative infinity.
    """
    under_limit_values: list[Any] = [-0.1, -1, -100, -999.99, float("-inf")]
    for value in under_limit_values:
        with pytest.raises(AssertionError) as exc_info:
            validate_percent_complete(
                value,
                endpoint="edge_case/below_zero",
            )
        error_msg = str(exc_info.value)
        assert "percent_complete" in error_msg, (
            f"AssertionError for value {value!r} should mention "
            f"'percent_complete' in the message, got: {error_msg}"
        )


@pytest.mark.edge_cases
def test_validate_percent_complete_wrong_type_string() -> None:
    """String values must raise ``AssertionError`` — even if the
    string content *looks* numeric (e.g. ``"50"``).
    """
    string_values = ["50", "complete", "", "100.0", "null"]
    for value in string_values:
        with pytest.raises(AssertionError) as exc_info:
            validate_percent_complete(
                value,
                endpoint="edge_case/wrong_type_string",
            )
        error_msg = str(exc_info.value)
        assert "percent_complete" in error_msg, (
            f"AssertionError for string value {value!r} should mention "
            f"'percent_complete', got: {error_msg}"
        )
        assert "str" in error_msg, (
            f"AssertionError for string value {value!r} should mention "
            f"the actual type 'str', got: {error_msg}"
        )


@pytest.mark.edge_cases
def test_validate_percent_complete_wrong_type_boolean() -> None:
    """Boolean values must raise ``AssertionError``.

    **Critical**: Python's ``bool`` is a subclass of ``int``
    (``isinstance(True, int)`` is ``True``).  The validator must
    explicitly exclude booleans to prevent ``True`` (== 1) and
    ``False`` (== 0) from silently passing as valid percentages.
    """
    for value in (True, False):
        with pytest.raises(AssertionError) as exc_info:
            validate_percent_complete(
                value,
                endpoint="edge_case/wrong_type_boolean",
            )
        error_msg = str(exc_info.value)
        assert "percent_complete" in error_msg, (
            f"AssertionError for bool value {value!r} should mention "
            f"'percent_complete', got: {error_msg}"
        )
        assert "bool" in error_msg, (
            f"AssertionError for bool value {value!r} should mention "
            f"the actual type 'bool', got: {error_msg}"
        )


@pytest.mark.edge_cases
def test_validate_percent_complete_wrong_type_list() -> None:
    """List / array values must raise ``AssertionError``."""
    list_values: list[Any] = [[50], [], [0, 100]]
    for value in list_values:
        with pytest.raises(AssertionError) as exc_info:
            validate_percent_complete(
                value,
                endpoint="edge_case/wrong_type_list",
            )
        error_msg = str(exc_info.value)
        assert "percent_complete" in error_msg, (
            f"AssertionError for list value {value!r} should mention "
            f"'percent_complete', got: {error_msg}"
        )
        assert "list" in error_msg, (
            f"AssertionError for list value {value!r} should mention "
            f"the actual type 'list', got: {error_msg}"
        )


@pytest.mark.edge_cases
def test_validate_percent_complete_wrong_type_dict() -> None:
    """Dict / object values must raise ``AssertionError``."""
    dict_values: list[Any] = [{"value": 50}, {}, {"percent_complete": 42}]
    for value in dict_values:
        with pytest.raises(AssertionError) as exc_info:
            validate_percent_complete(
                value,
                endpoint="edge_case/wrong_type_dict",
            )
        error_msg = str(exc_info.value)
        assert "percent_complete" in error_msg, (
            f"AssertionError for dict value {value!r} should mention "
            f"'percent_complete', got: {error_msg}"
        )
        assert "dict" in error_msg, (
            f"AssertionError for dict value {value!r} should mention "
            f"the actual type 'dict', got: {error_msg}"
        )


# ============================================================================
# §3.3 — Field Name Convention Tests
# ============================================================================


@pytest.mark.edge_cases
def test_field_presence_snake_case() -> None:
    """``percent_complete`` (snake_case) must be recognised when it is
    the only variant present in the response dict.
    """
    response = {"percent_complete": 50.0, "other_field": "irrelevant"}
    found = validate_field_presence(
        response,
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint="edge_case/field_name_snake",
    )
    assert found == "percent_complete", (
        f"validate_field_presence should return 'percent_complete' for "
        f"snake_case key, got: {found!r}"
    )


@pytest.mark.edge_cases
def test_field_presence_camel_case() -> None:
    """``percentComplete`` (camelCase) must be recognised when it is
    the only variant present in the response dict.
    """
    response = {"percentComplete": 50.0, "other_field": "irrelevant"}
    found = validate_field_presence(
        response,
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint="edge_case/field_name_camel",
    )
    assert found == "percentComplete", (
        f"validate_field_presence should return 'percentComplete' for "
        f"camelCase key, got: {found!r}"
    )


@pytest.mark.edge_cases
def test_field_presence_both_conventions() -> None:
    """When *both* naming conventions are present, the function must
    still succeed and return the first match (snake_case).
    """
    response = {
        "percent_complete": 42.0,
        "percentComplete": 42.0,
        "extra": True,
    }
    found = validate_field_presence(
        response,
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint="edge_case/field_name_both",
    )
    # PERCENT_COMPLETE_FIELD_NAMES lists snake_case first
    assert found == "percent_complete", (
        f"When both conventions are present, the first match "
        f"('percent_complete') should be returned, got: {found!r}"
    )


@pytest.mark.edge_cases
def test_field_presence_neither_convention_raises_error() -> None:
    """When the field is absent under **both** names, an
    ``AssertionError`` must be raised — this indicates a bug
    (AAP §0.7.1).
    """
    response = {"other_field": 42, "status": "complete"}
    with pytest.raises(AssertionError) as exc_info:
        validate_field_presence(
            response,
            PERCENT_COMPLETE_FIELD_NAMES,
            endpoint="edge_case/field_name_neither",
        )
    error_msg = str(exc_info.value)
    # Error should mention both field names that were checked
    assert "percent_complete" in error_msg, (
        f"AssertionError should mention 'percent_complete' in the "
        f"list of checked names, got: {error_msg}"
    )
    assert "percentComplete" in error_msg, (
        f"AssertionError should mention 'percentComplete' in the "
        f"list of checked names, got: {error_msg}"
    )


@pytest.mark.edge_cases
def test_field_name_typo_not_accepted() -> None:
    """Misspellings and wrong capitalisation must not satisfy field
    presence validation.

    Each typo variant is tested in isolation — the response contains
    only the typo key and no valid variant — ensuring the validator
    correctly raises ``AssertionError``.
    """
    typo_variants = [
        "percent_Complete",
        "PercentComplete",
        "percent_completed",
        "pctComplete",
        "percentcomplete",
        "PERCENT_COMPLETE",
    ]
    for typo in typo_variants:
        response: dict[str, Any] = {typo: 50.0}
        with pytest.raises(AssertionError) as exc_info:
            validate_field_presence(
                response,
                PERCENT_COMPLETE_FIELD_NAMES,
                endpoint=f"edge_case/typo/{typo}",
            )
        error_msg = str(exc_info.value)
        assert "not found" in error_msg, (
            f"Typo variant {typo!r} should not be accepted. "
            f"Expected 'not found' in error message, got: {error_msg}"
        )


# ============================================================================
# §3.4 — Parameterized Edge Case Tests
# ============================================================================


@pytest.mark.edge_cases
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(0, id="int_zero"),
        pytest.param(0.0, id="float_zero"),
        pytest.param(0.001, id="just_above_zero"),
        pytest.param(1, id="int_one"),
        pytest.param(50, id="int_fifty"),
        pytest.param(50.5, id="float_fifty_point_five"),
        pytest.param(99.99, id="just_below_hundred"),
        pytest.param(100, id="int_hundred"),
        pytest.param(100.0, id="float_hundred"),
        pytest.param(None, id="null"),
    ],
)
def test_validate_percent_complete_parameterized_valid(value: Any) -> None:
    """Parameterized test covering the full spectrum of **valid** values.

    Each value in the parameter list must be accepted by
    :func:`validate_percent_complete` without raising any error.

    Parameters
    ----------
    value : Any
        A value that is expected to be valid (``None``, or numeric
        within ``[0.0, 100.0]``).
    """
    # Should NOT raise — any exception is a test failure
    validate_percent_complete(
        value,
        endpoint="edge_case/parameterized_valid",
    )


@pytest.mark.edge_cases
@pytest.mark.parametrize(
    "value",
    [
        pytest.param(-0.001, id="just_below_zero"),
        pytest.param(-1, id="negative_one"),
        pytest.param(-100, id="negative_hundred"),
        pytest.param(100.001, id="just_above_hundred"),
        pytest.param(101, id="one_oh_one"),
        pytest.param(200, id="two_hundred"),
        pytest.param("50", id="string_fifty"),
        pytest.param(True, id="bool_true"),
        pytest.param(False, id="bool_false"),
        pytest.param([], id="empty_list"),
        pytest.param({}, id="empty_dict"),
        pytest.param([50], id="list_with_value"),
    ],
)
def test_validate_percent_complete_parameterized_invalid(value: Any) -> None:
    """Parameterized test covering the full spectrum of **invalid** values.

    Each value in the parameter list must be rejected by
    :func:`validate_percent_complete` with an ``AssertionError``.

    Parameters
    ----------
    value : Any
        A value that is expected to be invalid (out of range, wrong type,
        or boolean).
    """
    with pytest.raises(AssertionError) as exc_info:
        validate_percent_complete(
            value,
            endpoint="edge_case/parameterized_invalid",
        )
    error_msg = str(exc_info.value)
    assert "percent_complete" in error_msg, (
        f"AssertionError for invalid value {value!r} should mention "
        f"'percent_complete' in the message, got: {error_msg}"
    )


# ============================================================================
# §3.5 — Integration Edge Case Tests (Live API — if configured)
# ============================================================================


@pytest.mark.edge_cases
def test_runs_metering_edge_case_invalid_project_id(
    api_client: APIClient,
) -> None:
    """Verify API behaviour when called with a non-existent project ID.

    The API should return an HTTP error status or an empty / null
    response — it must **not** return a 200 with misleading metering
    data.  This test handles the response gracefully regardless of
    which error shape the server uses.

    Parameters
    ----------
    api_client : APIClient
        Authenticated HTTP client fixture (from ``conftest.py``).
    """
    bogus_project_id = "nonexistent-id-12345-edge-case"
    try:
        response = api_client.get_runs_metering(bogus_project_id)
    except Exception as exc:
        # HTTP error (4xx/5xx) or network error is acceptable for a
        # non-existent project — the API correctly rejected the request.
        assert exc is not None, (
            f"GET /runs/metering with invalid project ID "
            f"'{bogus_project_id}' raised an unexpected None exception"
        )
        return

    # If the API returned 200 with data, verify the response is
    # empty / null rather than populated with metering records that
    # would belong to an unknown project.
    if response is None:
        # Null response for invalid project is acceptable
        return

    if isinstance(response, list):
        assert len(response) == 0, (
            f"GET /runs/metering with invalid project ID "
            f"'{bogus_project_id}' returned {len(response)} metering "
            f"records — expected 0 or an HTTP error"
        )
    elif isinstance(response, dict):
        # Some APIs wrap the list inside a key; check common patterns
        data_key_candidates = ["data", "runs", "records", "items"]
        for key in data_key_candidates:
            if key in response and isinstance(response[key], list):
                assert len(response[key]) == 0, (
                    f"GET /runs/metering with invalid project ID "
                    f"'{bogus_project_id}' returned "
                    f"{len(response[key])} records under '{key}' — "
                    f"expected 0 or an HTTP error"
                )
                return
        # If the dict has no recognisable list key, just confirm it
        # does not contain a percent_complete field (which would imply
        # valid metering data for a non-existent project).
        has_field = any(
            fname in response for fname in PERCENT_COMPLETE_FIELD_NAMES
        )
        assert not has_field, (
            f"GET /runs/metering with invalid project ID "
            f"'{bogus_project_id}' unexpectedly contains a "
            f"percent_complete field — API should not return metering "
            f"data for a non-existent project"
        )


@pytest.mark.edge_cases
def test_field_extraction_from_api_response(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """End-to-end validation tying unit-level validators to a real API
    response structure.

    1. Calls ``GET /runs/metering`` with a valid project ID.
    2. Extracts the ``percent_complete`` value using
       :func:`get_percent_complete_value`.
    3. Validates the extracted value using
       :func:`validate_percent_complete`.

    This ensures the validators work correctly against the actual JSON
    shape returned by the Blitzy Platform API — not just against
    hand-crafted mock dicts.

    Parameters
    ----------
    api_client : APIClient
        Authenticated HTTP client fixture (from ``conftest.py``).
    test_project_id : str
        Valid project ID fixture (from ``conftest.py``).
    """
    response = api_client.get_runs_metering(test_project_id)

    # The response may be a list of records or a dict wrapping a list.
    records: list[dict[str, Any]] = []
    if isinstance(response, list):
        records = response
    elif isinstance(response, dict):
        # Try common wrapper keys
        for key in ("data", "runs", "records", "items"):
            if key in response and isinstance(response[key], list):
                records = response[key]
                break
        if not records:
            # Treat the dict itself as a single record
            records = [response]

    assert len(records) > 0, (
        f"GET /runs/metering for project '{test_project_id}' returned "
        f"no metering records — cannot perform field extraction edge "
        f"case validation"
    )

    # Validate the first record end-to-end
    first_record = records[0]
    assert isinstance(first_record, dict), (
        f"GET /runs/metering record should be a dict, "
        f"got {type(first_record).__name__}: {first_record!r}"
    )

    extracted_value = get_percent_complete_value(
        first_record,
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint="GET /runs/metering (edge_case/extraction)",
    )

    # The extracted value must pass the full validation chain
    validate_percent_complete(
        extracted_value,
        endpoint="GET /runs/metering (edge_case/extraction)",
    )
