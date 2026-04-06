"""
Blitzy Platform API Test Suite — ``GET /runs/metering`` Endpoint Tests

Validates the ``percent_complete`` field in the ``GET /runs/metering``
endpoint response.  This endpoint retrieves metering data for **multiple**
code-generation runs associated with a specific project, returning an array
(or wrapper object) of run-metering records.

Endpoint Details (AAP §0.4.2):

    URL            : ``GET /runs/metering?projectId={project_id}``
    Query Param    : ``projectId`` (required)
    Response       : Array of run-metering objects; each record is expected
                     to contain either ``percent_complete`` (snake_case) or
                     ``percentComplete`` (camelCase).
    Trigger Context: Called when viewing run history or fetching metering
                     data for a project dashboard.

Requirement Coverage:

    R-001 — Field Presence Validation     (every record must have the field)
    R-002 — Data Type Validation          (numeric or null, never str/bool)
    R-003 — Value Range Validation        (0.0 ≤ value ≤ 100.0 when not null)

Design Rules (AAP §0.7.1):

    * Every assertion includes a descriptive message identifying the endpoint,
      the field under test, and the actual-vs-expected value.
    * Generic assertions like ``assert True`` are prohibited.
    * Each test function is independently executable via pytest fixtures.
    * All tests carry the ``@pytest.mark.runs_metering`` marker.
    * No hardcoded URLs, tokens, project IDs, or credentials.

Fixtures consumed from ``tests/conftest.py``:

    * ``api_client``      — Authenticated :class:`APIClient` instance
    * ``test_project_id`` — Project ID with existing code-generation runs
"""

from __future__ import annotations

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
# Helper — extract metering records from various response envelopes
# ---------------------------------------------------------------------------

def _extract_metering_records(response_data: Any) -> List[Dict[str, Any]]:
    """Extract a flat list of metering-record dicts from the API response.

    The ``GET /runs/metering`` endpoint may return the records in several
    envelope shapes depending on the API version or backend serialisation
    layer:

    * **Direct list** — ``[{record_1}, {record_2}, ...]``
    * **"data" wrapper** — ``{"data": [{record_1}, ...]}``
    * **"runs" wrapper** — ``{"runs": [{record_1}, ...]}``
    * **"results" wrapper** — ``{"results": [{record_1}, ...]}``
    * **"items" wrapper** — ``{"items": [{record_1}, ...]}``
    * **Single-record dict** — ``{record}`` (treated as a one-element list)

    Parameters
    ----------
    response_data : Any
        The parsed JSON body returned by
        :meth:`APIClient.get_runs_metering`.

    Returns
    -------
    List[Dict[str, Any]]
        A flat list of run-metering record dictionaries.  Never ``None``
        — returns an empty list when the response shape is unrecognisable.
    """
    # Case 1: response is already a list of records
    if isinstance(response_data, list):
        return response_data

    # Case 2: response is a dict wrapper — try common envelope keys
    if isinstance(response_data, dict):
        for envelope_key in ("data", "runs", "results", "items"):
            if envelope_key in response_data:
                inner = response_data[envelope_key]
                if isinstance(inner, list):
                    return inner

        # Case 3: the dict itself appears to be a single metering record
        # (i.e. it contains domain-specific keys rather than just an
        # envelope key).  Wrap it in a list for uniform iteration.
        if response_data:
            return [response_data]

    # Fallback: unrecognised shape — return empty list so callers can
    # produce a clear assertion failure rather than a confusing TypeError.
    return []


# ============================================================================
# Response Structure Tests
# ============================================================================

@pytest.mark.runs_metering
def test_runs_metering_response_is_valid_json(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Verify ``GET /runs/metering`` returns a valid parsed JSON payload.

    The HTTP client raises on non-200 status codes and JSON parse errors,
    so a successful call guarantees valid JSON.  This test additionally
    asserts that the top-level type is either ``dict`` or ``list``.
    """
    response = api_client.get_runs_metering(test_project_id)
    assert isinstance(response, (dict, list)), (
        f"GET /runs/metering should return valid JSON (dict or list), "
        f"got {type(response).__name__}: {response!r}"
    )


@pytest.mark.runs_metering
def test_runs_metering_returns_data(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Verify the response contains at least one metering data record.

    A project used for testing must have at least one historical code-
    generation run.  An empty response indicates a test-data setup issue
    rather than a field-level defect.
    """
    response = api_client.get_runs_metering(test_project_id)
    records = _extract_metering_records(response)
    assert len(records) >= 1, (
        f"GET /runs/metering should return at least one metering record "
        f"for project {test_project_id}, but received {len(records)} records. "
        f"Raw response type: {type(response).__name__}"
    )


# ============================================================================
# Field Presence Tests — R-001
# ============================================================================

@pytest.mark.runs_metering
def test_percent_complete_present_in_runs_metering(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """R-001 — ``percent_complete`` field exists in every metering record.

    Iterates over ALL records returned by ``GET /runs/metering`` and
    asserts that each contains either ``percent_complete`` or
    ``percentComplete``.  A missing field in **any** record is a bug.
    """
    response = api_client.get_runs_metering(test_project_id)
    records = _extract_metering_records(response)
    assert len(records) >= 1, (
        f"GET /runs/metering returned no metering records for project "
        f"{test_project_id}. Cannot validate field presence without data."
    )

    for idx, record in enumerate(records):
        assert isinstance(record, dict), (
            f"GET /runs/metering record at index {idx} is not a dict: "
            f"got {type(record).__name__}"
        )
        validate_field_presence(
            record,
            PERCENT_COMPLETE_FIELD_NAMES,
            endpoint=f"GET /runs/metering [record {idx}]",
        )


@pytest.mark.runs_metering
def test_percent_complete_field_naming_in_metering(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Document which naming convention ``GET /runs/metering`` uses.

    Both ``percent_complete`` (snake_case) and ``percentComplete``
    (camelCase) are acceptable per AAP §0.7.1.  This test verifies that
    every record uses one of the two conventions and logs which variant
    was found for diagnostic purposes.
    """
    response = api_client.get_runs_metering(test_project_id)
    records = _extract_metering_records(response)
    assert len(records) >= 1, (
        f"GET /runs/metering returned no metering records for project "
        f"{test_project_id}. Cannot validate field naming without data."
    )

    observed_names: set = set()
    for idx, record in enumerate(records):
        assert isinstance(record, dict), (
            f"GET /runs/metering record at index {idx} is not a dict: "
            f"got {type(record).__name__}"
        )
        found_name = validate_field_presence(
            record,
            PERCENT_COMPLETE_FIELD_NAMES,
            endpoint=f"GET /runs/metering [record {idx}]",
        )
        observed_names.add(found_name)

    # Informational: record which naming convention(s) were found.
    # Both are acceptable — this assertion just confirms we got at least one.
    assert len(observed_names) >= 1, (
        f"GET /runs/metering: no percent_complete field name variant found "
        f"across {len(records)} records. "
        f"Expected one of {PERCENT_COMPLETE_FIELD_NAMES}."
    )


# ============================================================================
# Data Type Validation Tests — R-002
# ============================================================================

@pytest.mark.runs_metering
def test_percent_complete_type_in_runs_metering(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """R-002 — ``percent_complete`` is numeric (int/float) or null.

    For every metering record, extracts the ``percent_complete`` value and
    verifies it is ``None``, ``int``, or ``float`` — never a ``str``,
    ``bool``, ``list``, ``dict``, or any other non-numeric type.
    """
    response = api_client.get_runs_metering(test_project_id)
    records = _extract_metering_records(response)
    assert len(records) >= 1, (
        f"GET /runs/metering returned no metering records for project "
        f"{test_project_id}. Cannot validate field type without data."
    )

    for idx, record in enumerate(records):
        assert isinstance(record, dict), (
            f"GET /runs/metering record at index {idx} is not a dict: "
            f"got {type(record).__name__}"
        )
        value = get_percent_complete_value(
            record,
            PERCENT_COMPLETE_FIELD_NAMES,
            endpoint=f"GET /runs/metering [record {idx}]",
        )
        # validate_percent_complete raises AssertionError with descriptive
        # message if value is wrong type or out of range.  We add an
        # additional context layer referencing the record index.
        try:
            validate_percent_complete(
                value,
                endpoint=f"GET /runs/metering [record {idx}]",
            )
        except AssertionError as err:
            raise AssertionError(
                f"GET /runs/metering record at index {idx} "
                f"percent_complete has wrong type: expected numeric or null, "
                f"got {type(value).__name__}: {value!r}. "
                f"Original error: {err}"
            ) from err


# ============================================================================
# Value Range Validation Tests — R-003
# ============================================================================

@pytest.mark.runs_metering
def test_percent_complete_range_in_runs_metering(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """R-003 — ``percent_complete`` is within [0.0, 100.0] when not null.

    For every metering record where ``percent_complete`` is not ``None``,
    asserts that the value falls within the inclusive range 0.0–100.0.
    Null values are accepted (represent "no data") and skipped.
    """
    response = api_client.get_runs_metering(test_project_id)
    records = _extract_metering_records(response)
    assert len(records) >= 1, (
        f"GET /runs/metering returned no metering records for project "
        f"{test_project_id}. Cannot validate value range without data."
    )

    for idx, record in enumerate(records):
        assert isinstance(record, dict), (
            f"GET /runs/metering record at index {idx} is not a dict: "
            f"got {type(record).__name__}"
        )
        value = get_percent_complete_value(
            record,
            PERCENT_COMPLETE_FIELD_NAMES,
            endpoint=f"GET /runs/metering [record {idx}]",
        )
        if value is not None:
            # Verify numeric type first to prevent comparison errors
            assert isinstance(value, (int, float)) and not isinstance(value, bool), (
                f"GET /runs/metering record at index {idx} "
                f"percent_complete is not numeric: "
                f"got {type(value).__name__}: {value!r}"
            )
            assert 0.0 <= value <= 100.0, (
                f"GET /runs/metering record at index {idx} "
                f"percent_complete value {value} out of range [0.0, 100.0]"
            )


# ============================================================================
# Null Acceptance Tests
# ============================================================================

@pytest.mark.runs_metering
def test_percent_complete_null_acceptance_in_metering(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Null/None is a valid value for ``percent_complete``.

    Verifies that the validation logic correctly accepts ``None`` without
    raising.  If any record in the response has ``percent_complete=null``,
    the test confirms the null is accepted gracefully.  If no records have
    null values, the test still passes — null acceptance is verified via
    the validator's behaviour rather than requiring null data to exist.
    """
    response = api_client.get_runs_metering(test_project_id)
    records = _extract_metering_records(response)
    assert len(records) >= 1, (
        f"GET /runs/metering returned no metering records for project "
        f"{test_project_id}. Cannot validate null acceptance without data."
    )

    null_found = False
    for idx, record in enumerate(records):
        assert isinstance(record, dict), (
            f"GET /runs/metering record at index {idx} is not a dict: "
            f"got {type(record).__name__}"
        )
        value = get_percent_complete_value(
            record,
            PERCENT_COMPLETE_FIELD_NAMES,
            endpoint=f"GET /runs/metering [record {idx}]",
        )
        if value is None:
            null_found = True
        # Regardless of whether value is null or numeric, validate it —
        # validate_percent_complete explicitly accepts None.
        validate_percent_complete(
            value,
            endpoint=f"GET /runs/metering [record {idx}]",
        )

    # Informational note: we do not require null values to be present.
    # The purpose of this test is to ensure the validator does NOT reject
    # None when it appears.  If all values are numeric, that is also fine.
    # Explicitly validate that None passes the validator as a safety net.
    validate_percent_complete(
        None,
        endpoint="GET /runs/metering [null acceptance safety check]",
    )


# ============================================================================
# Multiple Record Validation
# ============================================================================

@pytest.mark.runs_metering
def test_all_records_have_percent_complete(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Every metering record must contain ``percent_complete`` — not just
    the first one.

    Iterates through ALL records, counts those with and without the field,
    and asserts that zero records are missing it.  Per R-001, a missing
    field in any record is a defect.
    """
    response = api_client.get_runs_metering(test_project_id)
    records = _extract_metering_records(response)
    total_count = len(records)
    assert total_count >= 1, (
        f"GET /runs/metering returned no metering records for project "
        f"{test_project_id}. Cannot validate field coverage without data."
    )

    missing_indices: List[int] = []
    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            missing_indices.append(idx)
            continue
        # Check if any accepted field name variant is present
        has_field = any(
            field_name in record for field_name in PERCENT_COMPLETE_FIELD_NAMES
        )
        if not has_field:
            missing_indices.append(idx)

    missing_count = len(missing_indices)
    assert missing_count == 0, (
        f"GET /runs/metering: {missing_count}/{total_count} records missing "
        f"percent_complete field. Missing at record indices: {missing_indices}. "
        f"Checked field name variants: {PERCENT_COMPLETE_FIELD_NAMES}"
    )


@pytest.mark.runs_metering
def test_completed_run_percent_complete(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Completed runs should have ``percent_complete`` between 0 and 100.

    Per the AAP validation matrix, a completed run is expected to have a
    numeric ``percent_complete`` value within the [0, 100] range (not null).
    If a record is identifiable as "completed" (via a ``status`` field or
    similar indicator), its ``percent_complete`` must be non-null and
    within range.

    If no completed runs are identifiable in the response, the test still
    passes by verifying that all non-null values meet the range constraint.
    """
    response = api_client.get_runs_metering(test_project_id)
    records = _extract_metering_records(response)
    assert len(records) >= 1, (
        f"GET /runs/metering returned no metering records for project "
        f"{test_project_id}. Cannot validate completed run data without records."
    )

    # Attempt to identify completed runs via common status field patterns
    completed_status_values = {
        "completed", "complete", "done", "finished", "success", "succeeded",
        "COMPLETED", "COMPLETE", "DONE", "FINISHED", "SUCCESS", "SUCCEEDED",
    }
    status_field_names = ["status", "run_status", "runStatus", "state"]

    completed_records_found = False
    for idx, record in enumerate(records):
        if not isinstance(record, dict):
            continue

        # Determine if this record represents a completed run
        is_completed = False
        for status_key in status_field_names:
            if status_key in record:
                status_val = record[status_key]
                if isinstance(status_val, str) and status_val in completed_status_values:
                    is_completed = True
                    break

        if is_completed:
            completed_records_found = True
            value = get_percent_complete_value(
                record,
                PERCENT_COMPLETE_FIELD_NAMES,
                endpoint=f"GET /runs/metering [completed record {idx}]",
            )
            assert value is not None, (
                f"GET /runs/metering completed run record at index {idx} "
                f"has percent_complete=null. Completed runs should have a "
                f"numeric value between 0 and 100."
            )
            assert isinstance(value, (int, float)) and not isinstance(value, bool), (
                f"GET /runs/metering completed run record at index {idx} "
                f"has non-numeric percent_complete: "
                f"got {type(value).__name__}: {value!r}"
            )
            assert 0.0 <= value <= 100.0, (
                f"GET /runs/metering completed run record at index {idx} "
                f"has unexpected percent_complete: {value}. "
                f"Expected a value between 0.0 and 100.0 for a completed run."
            )

    # If no explicitly completed runs were found, fall back to verifying
    # that all non-null percent_complete values are within range (which
    # still provides meaningful coverage for the endpoint).
    if not completed_records_found:
        for idx, record in enumerate(records):
            if not isinstance(record, dict):
                continue
            value = get_percent_complete_value(
                record,
                PERCENT_COMPLETE_FIELD_NAMES,
                endpoint=f"GET /runs/metering [record {idx}]",
            )
            if value is not None:
                assert isinstance(value, (int, float)) and not isinstance(value, bool), (
                    f"GET /runs/metering record at index {idx} "
                    f"has non-numeric percent_complete: "
                    f"got {type(value).__name__}: {value!r}"
                )
                assert 0.0 <= value <= 100.0, (
                    f"GET /runs/metering record at index {idx} "
                    f"has unexpected percent_complete: {value}. "
                    f"Expected a value between 0.0 and 100.0."
                )
