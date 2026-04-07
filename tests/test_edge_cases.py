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
from src.config import Settings, get_settings
from src.models import (
    CurrentMeteringResponse,
    MeteringData,
    MeteringResponse,
    ProjectResponse,
)
from src.validators import (
    PERCENT_COMPLETE_FIELD_NAMES,
    get_percent_complete_value,
    validate_field_presence,
    validate_percent_complete,
    validate_response_structure,
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


# ============================================================================
# §4 — Pydantic Model Validation Unit Tests
# ============================================================================
# These tests exercise the Pydantic response models defined in src/models.py
# to verify that they correctly parse, coerce, and validate API response
# structures entirely offline (no API credentials required).
# ============================================================================


@pytest.mark.edge_cases
class TestMeteringDataModel:
    """Unit tests for the :class:`MeteringData` Pydantic model."""

    def test_snake_case_field_accepted(self) -> None:
        """Model accepts ``percent_complete`` (snake_case) key."""
        record = MeteringData.model_validate({"percent_complete": 42.5})
        assert record.percent_complete == 42.5

    def test_camel_case_field_accepted(self) -> None:
        """Model accepts ``percentComplete`` (camelCase) alias key."""
        record = MeteringData.model_validate({"percentComplete": 75.0})
        assert record.percent_complete == 75.0

    def test_null_value_accepted(self) -> None:
        """Model accepts ``None`` (JSON null) for percent_complete."""
        record = MeteringData.model_validate({"percent_complete": None})
        assert record.percent_complete is None

    def test_integer_coerced_to_float(self) -> None:
        """Integer values are coerced to ``float`` by the model."""
        record = MeteringData.model_validate({"percent_complete": 50})
        assert record.percent_complete == 50.0
        assert isinstance(record.percent_complete, float)

    def test_zero_value_accepted(self) -> None:
        """Boundary value 0.0 is valid."""
        record = MeteringData.model_validate({"percent_complete": 0.0})
        assert record.percent_complete == 0.0

    def test_hundred_value_accepted(self) -> None:
        """Boundary value 100.0 is valid."""
        record = MeteringData.model_validate({"percent_complete": 100.0})
        assert record.percent_complete == 100.0

    def test_exceeds_hundred_rejected(self) -> None:
        """Values exceeding 100.0 must be rejected by the model."""
        with pytest.raises(Exception):
            MeteringData.model_validate({"percent_complete": 100.1})

    def test_below_zero_rejected(self) -> None:
        """Negative values must be rejected by the model."""
        with pytest.raises(Exception):
            MeteringData.model_validate({"percent_complete": -0.1})

    def test_extra_fields_preserved(self) -> None:
        """Extra fields in the payload are preserved (``extra='allow'``)."""
        record = MeteringData.model_validate({
            "percent_complete": 10.0,
            "custom_field": "preserved",
        })
        assert record.percent_complete == 10.0
        # Extra fields accessible via model_extra
        assert "custom_field" in record.model_extra

    def test_default_values_when_empty(self) -> None:
        """All fields default to ``None`` when an empty dict is parsed."""
        record = MeteringData.model_validate({})
        assert record.percent_complete is None
        assert record.estimated_hours_saved is None
        assert record.estimated_lines_generated is None

    def test_companion_fields(self) -> None:
        """Model correctly parses companion metering fields."""
        record = MeteringData.model_validate({
            "percent_complete": 80.0,
            "estimated_hours_saved": 12.5,
            "estimated_lines_generated": 1500,
        })
        assert record.percent_complete == 80.0
        assert record.estimated_hours_saved == 12.5
        assert record.estimated_lines_generated == 1500


@pytest.mark.edge_cases
class TestCurrentMeteringResponseModel:
    """Unit tests for the :class:`CurrentMeteringResponse` Pydantic model."""

    def test_snake_case_field_accepted(self) -> None:
        """Model accepts ``percent_complete`` (snake_case) key."""
        resp = CurrentMeteringResponse.model_validate({
            "percent_complete": 55.5,
        })
        assert resp.percent_complete == 55.5

    def test_camel_case_field_accepted(self) -> None:
        """Model accepts ``percentComplete`` (camelCase) alias key."""
        resp = CurrentMeteringResponse.model_validate({
            "percentComplete": 88.0,
        })
        assert resp.percent_complete == 88.0

    def test_null_value_accepted(self) -> None:
        """Model accepts ``None`` for percent_complete."""
        resp = CurrentMeteringResponse.model_validate({
            "percent_complete": None,
        })
        assert resp.percent_complete is None

    def test_empty_payload_defaults(self) -> None:
        """All fields default to ``None`` when payload is empty."""
        resp = CurrentMeteringResponse.model_validate({})
        assert resp.percent_complete is None
        assert resp.estimated_hours_saved is None
        assert resp.estimated_lines_generated is None

    def test_exceeds_hundred_rejected(self) -> None:
        """Values exceeding 100.0 must be rejected."""
        with pytest.raises(Exception):
            CurrentMeteringResponse.model_validate({
                "percent_complete": 101.0,
            })


@pytest.mark.edge_cases
class TestMeteringResponseModel:
    """Unit tests for the :class:`MeteringResponse` list-wrapper model."""

    def test_single_record_data(self) -> None:
        """Parses a ``data`` list with a single metering record."""
        resp = MeteringResponse.model_validate({
            "data": [{"percent_complete": 42.0}],
        })
        assert resp.data is not None
        assert len(resp.data) == 1
        assert resp.data[0].percent_complete == 42.0

    def test_multiple_records(self) -> None:
        """Parses a ``data`` list with multiple metering records."""
        resp = MeteringResponse.model_validate({
            "data": [
                {"percent_complete": 10.0},
                {"percent_complete": 50.0},
                {"percentComplete": 100.0},
            ],
        })
        assert resp.data is not None
        assert len(resp.data) == 3
        assert resp.data[0].percent_complete == 10.0
        assert resp.data[1].percent_complete == 50.0
        assert resp.data[2].percent_complete == 100.0

    def test_empty_data_list(self) -> None:
        """An empty ``data`` list is valid — no records to validate."""
        resp = MeteringResponse.model_validate({"data": []})
        assert resp.data is not None
        assert len(resp.data) == 0

    def test_null_data_field(self) -> None:
        """A ``null`` data field defaults to ``None``."""
        resp = MeteringResponse.model_validate({"data": None})
        assert resp.data is None

    def test_missing_data_field_defaults(self) -> None:
        """Missing ``data`` key defaults to ``None``."""
        resp = MeteringResponse.model_validate({})
        assert resp.data is None


@pytest.mark.edge_cases
class TestProjectResponseModel:
    """Unit tests for :class:`ProjectResponse` and :class:`ProjectMeteringBlock`."""

    def test_full_project_with_metering(self) -> None:
        """Parses a complete project response with nested metering block."""
        proj = ProjectResponse.model_validate({
            "id": "proj-abc-123",
            "name": "Test Project",
            "metering": {"percent_complete": 95.5},
        })
        assert proj.id == "proj-abc-123"
        assert proj.name == "Test Project"
        assert proj.metering is not None
        assert proj.metering.percent_complete == 95.5

    def test_metering_camel_case(self) -> None:
        """Nested metering block accepts camelCase ``percentComplete``."""
        proj = ProjectResponse.model_validate({
            "id": "proj-456",
            "metering": {"percentComplete": 60.0},
        })
        assert proj.metering is not None
        assert proj.metering.percent_complete == 60.0

    def test_metering_null_value(self) -> None:
        """Nested metering ``percent_complete`` can be ``null``."""
        proj = ProjectResponse.model_validate({
            "id": "proj-789",
            "metering": {"percent_complete": None},
        })
        assert proj.metering is not None
        assert proj.metering.percent_complete is None

    def test_no_metering_block(self) -> None:
        """Project response without a metering block defaults to ``None``."""
        proj = ProjectResponse.model_validate({
            "id": "proj-empty",
            "name": "No Metering",
        })
        assert proj.metering is None

    def test_metering_exceeds_range_rejected(self) -> None:
        """Metering block with value > 100.0 must be rejected."""
        with pytest.raises(Exception):
            ProjectResponse.model_validate({
                "id": "proj-bad",
                "metering": {"percent_complete": 150.0},
            })

    def test_project_extra_fields_preserved(self) -> None:
        """Extra fields on the project object are preserved."""
        proj = ProjectResponse.model_validate({
            "id": "proj-extra",
            "name": "Extra Fields",
            "description": "Has extra data",
            "metering": {"percent_complete": 50.0},
        })
        assert proj.id == "proj-extra"
        assert "description" in proj.model_extra

    def test_metering_block_companion_fields(self) -> None:
        """Metering block correctly parses companion fields."""
        proj = ProjectResponse.model_validate({
            "id": "proj-comp",
            "metering": {
                "percent_complete": 85.0,
                "estimated_hours_saved": 8.0,
                "estimated_lines_generated": 2000,
            },
        })
        assert proj.metering is not None
        assert proj.metering.percent_complete == 85.0
        assert proj.metering.estimated_hours_saved == 8.0
        assert proj.metering.estimated_lines_generated == 2000


# ============================================================================
# §5 — Configuration / Settings Unit Tests
# ============================================================================
# These tests exercise the Settings class and configuration logic without
# requiring live API credentials.
# ============================================================================


@pytest.mark.edge_cases
class TestSettingsConfiguration:
    """Unit tests for :class:`Settings` configuration management."""

    def test_default_settings_construction(self) -> None:
        """Settings can be constructed with all defaults (no env vars)."""
        settings = Settings()
        assert settings.base_url == ""
        assert settings.api_token == ""
        assert settings.test_project_id == ""
        assert settings.test_run_id == ""
        assert settings.test_timeout == 30
        assert settings.log_level == "INFO"
        assert settings.retry_count == 3
        assert settings.retry_delay == 1.0

    def test_explicit_construction(self) -> None:
        """Settings can be constructed with explicit values."""
        settings = Settings(
            base_url="https://test.example.com",
            api_token="test-token-123",
            test_project_id="proj-test",
            test_run_id="run-test",
            test_timeout=60,
            log_level="DEBUG",
            retry_count=5,
            retry_delay=2.0,
        )
        assert settings.base_url == "https://test.example.com"
        assert settings.api_token == "test-token-123"
        assert settings.test_project_id == "proj-test"
        assert settings.test_run_id == "run-test"
        assert settings.test_timeout == 60
        assert settings.log_level == "DEBUG"
        assert settings.retry_count == 5
        assert settings.retry_delay == 2.0

    def test_default_endpoint_paths(self) -> None:
        """Default endpoint paths match the three target APIs."""
        settings = Settings()
        assert "runs_metering" in settings.endpoint_paths
        assert "runs_metering_current" in settings.endpoint_paths
        assert "project" in settings.endpoint_paths
        assert settings.endpoint_paths["runs_metering"] == "/runs/metering"
        assert settings.endpoint_paths["runs_metering_current"] == "/runs/metering/current"
        assert settings.endpoint_paths["project"] == "/project"

    def test_default_field_names(self) -> None:
        """Default field names include both snake_case and camelCase."""
        settings = Settings()
        assert "percent_complete" in settings.percent_complete_field_names
        assert "percentComplete" in settings.percent_complete_field_names

    def test_get_endpoint_url_valid(self) -> None:
        """get_endpoint_url constructs the correct full URL."""
        settings = Settings(base_url="https://api.example.com")
        url = settings.get_endpoint_url("runs_metering")
        assert url == "https://api.example.com/runs/metering"

    def test_get_endpoint_url_strips_trailing_slash(self) -> None:
        """Trailing slash on base_url is stripped to avoid double slashes."""
        settings = Settings(base_url="https://api.example.com/")
        url = settings.get_endpoint_url("project")
        assert url == "https://api.example.com/project"
        assert "//" not in url.split("://", 1)[-1]

    def test_get_endpoint_url_invalid_key_raises(self) -> None:
        """Unknown endpoint key raises KeyError with descriptive message."""
        settings = Settings(base_url="https://api.example.com")
        with pytest.raises(KeyError) as exc_info:
            settings.get_endpoint_url("nonexistent_endpoint")
        assert "nonexistent_endpoint" in str(exc_info.value)

    def test_validate_required_settings_missing_all(self) -> None:
        """validate_required_settings raises ValueError when all are empty."""
        settings = Settings()
        with pytest.raises(ValueError) as exc_info:
            settings.validate_required_settings()
        error_msg = str(exc_info.value)
        assert "BASE_URL" in error_msg
        assert "API_TOKEN" in error_msg
        assert "TEST_PROJECT_ID" in error_msg

    def test_validate_required_settings_missing_partial(self) -> None:
        """validate_required_settings lists only missing variables."""
        settings = Settings(
            base_url="https://api.example.com",
            api_token="",
            test_project_id="proj-123",
        )
        with pytest.raises(ValueError) as exc_info:
            settings.validate_required_settings()
        error_msg = str(exc_info.value)
        assert "API_TOKEN" in error_msg
        assert "BASE_URL" not in error_msg
        assert "TEST_PROJECT_ID" not in error_msg

    def test_validate_required_settings_all_present(self) -> None:
        """validate_required_settings succeeds when all are populated."""
        settings = Settings(
            base_url="https://api.example.com",
            api_token="tok-abc",
            test_project_id="proj-123",
        )
        # Should not raise
        settings.validate_required_settings()

    def test_get_settings_returns_settings_instance(self) -> None:
        """get_settings() returns a Settings instance."""
        settings = get_settings()
        assert isinstance(settings, Settings)

    def test_from_env_returns_settings_instance(self) -> None:
        """Settings.from_env() returns a Settings instance."""
        settings = Settings.from_env()
        assert isinstance(settings, Settings)


# ============================================================================
# §6 — API Client Construction Unit Tests
# ============================================================================
# These tests verify APIClient initialisation and header configuration
# without making any HTTP requests.
# ============================================================================


@pytest.mark.edge_cases
class TestAPIClientConstruction:
    """Unit tests for :class:`APIClient` construction and header setup."""

    def test_client_sets_authorization_header(self) -> None:
        """Client sets the Authorization header from the Settings token."""
        settings = Settings(
            base_url="https://api.test.com",
            api_token="my-secret-token",
        )
        client = APIClient(settings)
        assert client.session.headers["Authorization"] == "Bearer my-secret-token"

    def test_client_sets_content_type(self) -> None:
        """Client sets Content-Type to application/json."""
        settings = Settings(
            base_url="https://api.test.com",
            api_token="tok",
        )
        client = APIClient(settings)
        assert client.session.headers["Content-Type"] == "application/json"

    def test_client_sets_accept_header(self) -> None:
        """Client sets Accept to application/json."""
        settings = Settings(
            base_url="https://api.test.com",
            api_token="tok",
        )
        client = APIClient(settings)
        assert client.session.headers["Accept"] == "application/json"

    def test_client_strips_trailing_slash(self) -> None:
        """Client strips trailing slash from base_url."""
        settings = Settings(
            base_url="https://api.test.com/",
            api_token="tok",
        )
        client = APIClient(settings)
        assert client.base_url == "https://api.test.com"
        assert not client.base_url.endswith("/")

    def test_client_stores_settings(self) -> None:
        """Client stores the settings reference for downstream use."""
        settings = Settings(
            base_url="https://api.test.com",
            api_token="tok",
            test_timeout=60,
        )
        client = APIClient(settings)
        assert client.settings is settings
        assert client.settings.test_timeout == 60

    def test_client_session_is_requests_session(self) -> None:
        """Client creates a ``requests.Session`` instance."""
        import requests as req

        settings = Settings(
            base_url="https://api.test.com",
            api_token="tok",
        )
        client = APIClient(settings)
        assert isinstance(client.session, req.Session)


# ============================================================================
# §7 — validate_response_structure Unit Tests
# ============================================================================
# These tests exercise the new structural validation helper that locates
# percent_complete in various response envelope shapes.
# ============================================================================


@pytest.mark.edge_cases
class TestValidateResponseStructure:
    """Unit tests for :func:`validate_response_structure`."""

    def test_flat_dict_snake_case(self) -> None:
        """Locates percent_complete in a flat dict (snake_case)."""
        field_name, value = validate_response_structure(
            {"percent_complete": 42.0, "other": "data"},
            endpoint="test/flat_snake",
        )
        assert field_name == "percent_complete"
        assert value == 42.0

    def test_flat_dict_camel_case(self) -> None:
        """Locates percentComplete in a flat dict (camelCase)."""
        field_name, value = validate_response_structure(
            {"percentComplete": 88.0},
            endpoint="test/flat_camel",
        )
        assert field_name == "percentComplete"
        assert value == 88.0

    def test_nested_metering_block(self) -> None:
        """Locates percent_complete inside a ``metering`` sub-object."""
        field_name, value = validate_response_structure(
            {
                "id": "proj-1",
                "name": "Test",
                "metering": {"percent_complete": 95.0},
            },
            endpoint="test/nested_metering",
        )
        assert field_name == "percent_complete"
        assert value == 95.0

    def test_data_wrapper_list(self) -> None:
        """Locates percent_complete inside a ``data`` list wrapper."""
        field_name, value = validate_response_structure(
            {"data": [{"percent_complete": 60.0}]},
            endpoint="test/data_wrapper",
        )
        assert field_name == "percent_complete"
        assert value == 60.0

    def test_runs_wrapper_list(self) -> None:
        """Locates percent_complete inside a ``runs`` list wrapper."""
        field_name, value = validate_response_structure(
            {"runs": [{"percentComplete": 30.0}]},
            endpoint="test/runs_wrapper",
        )
        assert field_name == "percentComplete"
        assert value == 30.0

    def test_direct_list_response(self) -> None:
        """Locates percent_complete in a direct list response."""
        field_name, value = validate_response_structure(
            [{"percent_complete": 77.0}, {"percent_complete": 88.0}],
            endpoint="test/direct_list",
        )
        assert field_name == "percent_complete"
        assert value == 77.0  # Returns first record's value

    def test_null_value_in_structure(self) -> None:
        """Correctly returns ``None`` for a null percent_complete value."""
        field_name, value = validate_response_structure(
            {"percent_complete": None},
            endpoint="test/null_value",
        )
        assert field_name == "percent_complete"
        assert value is None

    def test_missing_field_raises_assertion(self) -> None:
        """Raises AssertionError when field is missing from all locations."""
        with pytest.raises(AssertionError) as exc_info:
            validate_response_structure(
                {"id": "no-field", "data": "not-a-list"},
                endpoint="test/missing_field",
            )
        assert "not found" in str(exc_info.value)

    def test_empty_list_raises_assertion(self) -> None:
        """Raises AssertionError for an empty list response."""
        with pytest.raises(AssertionError) as exc_info:
            validate_response_structure(
                [],
                endpoint="test/empty_list",
            )
        assert "empty list" in str(exc_info.value).lower()

    def test_non_dict_non_list_raises_assertion(self) -> None:
        """Raises AssertionError when response is not a dict or list."""
        with pytest.raises(AssertionError):
            validate_response_structure(
                "not a dict or list",
                endpoint="test/wrong_type",
            )

    def test_items_wrapper_list(self) -> None:
        """Locates percent_complete inside an ``items`` list wrapper."""
        field_name, value = validate_response_structure(
            {"items": [{"percentComplete": 15.0}]},
            endpoint="test/items_wrapper",
        )
        assert field_name == "percentComplete"
        assert value == 15.0

    def test_results_wrapper_list(self) -> None:
        """Locates percent_complete inside a ``results`` list wrapper."""
        field_name, value = validate_response_structure(
            {"results": [{"percent_complete": 99.9}]},
            endpoint="test/results_wrapper",
        )
        assert field_name == "percent_complete"
        assert value == 99.9


# ============================================================================
# §8 — get_percent_complete_value Additional Edge Cases
# ============================================================================


@pytest.mark.edge_cases
class TestGetPercentCompleteValueEdgeCases:
    """Additional edge cases for :func:`get_percent_complete_value`."""

    def test_returns_none_for_null_field(self) -> None:
        """Returns ``None`` when the field value is null."""
        result = get_percent_complete_value(
            {"percent_complete": None},
            endpoint="test/null_extraction",
        )
        assert result is None

    def test_returns_float_value(self) -> None:
        """Returns the float value when present."""
        result = get_percent_complete_value(
            {"percentComplete": 67.5},
            endpoint="test/float_extraction",
        )
        assert result == 67.5

    def test_returns_int_value(self) -> None:
        """Returns the int value when present."""
        result = get_percent_complete_value(
            {"percent_complete": 50},
            endpoint="test/int_extraction",
        )
        assert result == 50

    def test_prefers_first_field_name_variant(self) -> None:
        """When both variants exist, returns value from the first match."""
        result = get_percent_complete_value(
            {"percent_complete": 10.0, "percentComplete": 20.0},
            endpoint="test/prefer_first",
        )
        # PERCENT_COMPLETE_FIELD_NAMES lists snake_case first
        assert result == 10.0

    def test_custom_field_names(self) -> None:
        """Custom field name list is used when provided."""
        result = get_percent_complete_value(
            {"progress": 85.0},
            field_names=["progress"],
            endpoint="test/custom_field_names",
        )
        assert result == 85.0

    def test_missing_field_raises(self) -> None:
        """Raises AssertionError when field is absent under all names."""
        with pytest.raises(AssertionError):
            get_percent_complete_value(
                {"unrelated": 100},
                endpoint="test/missing",
            )
