"""
Blitzy Platform API Test Suite — Cross-API Consistency Tests

Verifies that the ``percent_complete`` field behaves consistently across ALL
THREE Blitzy Platform API endpoints for the same project / run context.

This module addresses **Requirement R-004 (Cross-API Consistency)** from
the Agent Action Plan (AAP):

    "Ensure the field is consistently present across all three APIs — if
    present in one API but missing in another, flag this as a defect."

Target Endpoints
----------------
- ``GET /runs/metering``         — historical run metering data
- ``GET /runs/metering/current`` — active (in-progress) run metering
- ``GET /project``               — project details with inline metering

AAP §0.7.1 Cross-API Consistency Rule
--------------------------------------
When testing the same project / run across multiple endpoints, the
``percent_complete`` value should be logically consistent.  A completed run
must not show ``percent_complete < 100`` in one endpoint and ``100`` in
another (accounting for timing differences in eventual consistency).

Test Functions
--------------
test_percent_complete_present_in_all_endpoints
    Core R-004 — field present in all three endpoints.
test_percent_complete_field_name_consistency
    Naming convention check (snake_case vs camelCase).
test_percent_complete_type_consistency
    Data-type consistency across endpoints.
test_percent_complete_value_logical_consistency
    Logical value comparison with eventual-consistency tolerance.
test_percent_complete_null_consistency
    Null-vs-non-null distribution consistency.
test_all_endpoints_accessible
    HTTP accessibility and valid-JSON verification.
test_endpoints_return_structured_data
    Response top-level structure validation.

Markers
-------
All tests carry ``@pytest.mark.cross_api`` for selective execution.

Fixtures (from conftest.py)
---------------------------
- ``api_client`` — authenticated :class:`APIClient` instance
- ``test_project_id`` — project identifier from environment
- ``settings`` — full :class:`Settings` configuration object
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

import pytest

if TYPE_CHECKING:
    from src.config import Settings

from src.api_client import APIClient
from src.validators import (
    PERCENT_COMPLETE_FIELD_NAMES,
    get_percent_complete_value,
    validate_field_presence,
    validate_percent_complete,
)


# ---------------------------------------------------------------------------
# Constants — endpoint labels for descriptive assertion messages
# ---------------------------------------------------------------------------

_EP_RUNS_METERING: str = "GET /runs/metering"
"""Label for the historical-run metering endpoint."""

_EP_RUNS_METERING_CURRENT: str = "GET /runs/metering/current"
"""Label for the active-run metering endpoint."""

_EP_PROJECT: str = "GET /project"
"""Label for the project-details endpoint (nested metering block)."""

_ALL_ENDPOINTS: List[str] = [
    _EP_RUNS_METERING,
    _EP_RUNS_METERING_CURRENT,
    _EP_PROJECT,
]
"""Ordered list of all three endpoint labels."""

_VALUE_CONSISTENCY_TOLERANCE: float = 5.0
"""Maximum allowed difference between non-null ``percent_complete`` values
returned by different endpoints for the same project.  A generous tolerance
accounts for eventual-consistency timing differences in the data layer."""


# ---------------------------------------------------------------------------
# Private helper — extract the first metering record from runs/metering
# ---------------------------------------------------------------------------

def _extract_first_metering_record(
    response_data: Any,
) -> Optional[Dict[str, Any]]:
    """Return the first metering-record dict from a ``runs/metering`` response.

    The ``GET /runs/metering`` endpoint may return:

    * A plain JSON array of records: ``[{...}, ...]``
    * A wrapper dict containing a nested array under a well-known key
      such as ``"data"``, ``"runs"``, ``"records"``, ``"results"``, or
      ``"items"``.
    * A single dict representing one metering record.

    This helper normalises all three shapes into the first record dict,
    or ``None`` if no usable record can be found.

    Parameters
    ----------
    response_data : Any
        The parsed JSON body returned by :meth:`APIClient.get_runs_metering`.

    Returns
    -------
    Optional[Dict[str, Any]]
        The first metering record, or ``None``.
    """
    # Shape 1: top-level list
    if isinstance(response_data, list) and response_data:
        first = response_data[0]
        return first if isinstance(first, dict) else None

    # Shape 2: wrapper dict with a nested list
    if isinstance(response_data, dict):
        for key in ("data", "runs", "records", "results", "items"):
            wrapped = response_data.get(key)
            if isinstance(wrapped, list) and wrapped:
                first = wrapped[0]
                return first if isinstance(first, dict) else None
        # Shape 3: single dict record (no nested list found)
        return response_data

    return None


# ---------------------------------------------------------------------------
# Private helper — extract percent_complete from nested project response
# ---------------------------------------------------------------------------

def _extract_percent_complete_from_project_response(
    response_data: Dict[str, Any],
) -> Tuple[Optional[str], Any]:
    """Navigate the nested ``GET /project`` response to find ``percent_complete``.

    The project endpoint returns ``percent_complete`` inside a **nested
    metering block** rather than at the top level.  This helper checks
    several possible nesting keys (``metering``, ``metering_data``,
    ``meteringData``) and falls back to the top level if no nested block
    is found.

    Parameters
    ----------
    response_data : Dict[str, Any]
        The parsed JSON body returned by :meth:`APIClient.get_project`.

    Returns
    -------
    Tuple[Optional[str], Any]
        A two-tuple of ``(field_name_found, value)``.  If the field is
        absent under all accepted name variants, returns ``(None, None)``.
    """
    if not isinstance(response_data, dict):
        return None, None

    # Primary: look inside nested metering blocks
    for metering_key in ("metering", "metering_data", "meteringData"):
        metering_block = response_data.get(metering_key)
        if isinstance(metering_block, dict):
            for field_name in PERCENT_COMPLETE_FIELD_NAMES:
                if field_name in metering_block:
                    return field_name, metering_block[field_name]

    # Fallback: check at top level (some API versions may flatten)
    for field_name in PERCENT_COMPLETE_FIELD_NAMES:
        if field_name in response_data:
            return field_name, response_data[field_name]

    return None, None


# ---------------------------------------------------------------------------
# Private helper — DRY collector for all three endpoints
# ---------------------------------------------------------------------------

def _collect_percent_complete_from_all_endpoints(
    api_client: APIClient,
    project_id: str,
) -> Dict[str, Dict[str, Any]]:
    """Call all three endpoints and extract ``percent_complete`` from each.

    Returns a dict mapping each endpoint label to an information dict::

        {
            "GET /runs/metering": {
                "field_name": "percent_complete" | "percentComplete" | None,
                "value": <extracted value or None>,
                "error": <error message string or None>,
                "response": <raw parsed JSON or None>,
                "field_present": True | False,
            },
            ...
        }

    Each endpoint call is wrapped in a ``try / except`` so that a failure
    in one endpoint does not prevent the other two from being tested.

    Parameters
    ----------
    api_client : APIClient
        Authenticated HTTP client instance (from the ``api_client`` fixture).
    project_id : str
        Project identifier (from the ``test_project_id`` fixture).

    Returns
    -------
    Dict[str, Dict[str, Any]]
        Per-endpoint extraction results.
    """
    results: Dict[str, Dict[str, Any]] = {}

    # ---- Endpoint 1: GET /runs/metering ----
    try:
        response = api_client.get_runs_metering(project_id)
        record = _extract_first_metering_record(response)
        if record is not None:
            found_name: Optional[str] = None
            for fname in PERCENT_COMPLETE_FIELD_NAMES:
                if fname in record:
                    found_name = fname
                    break
            results[_EP_RUNS_METERING] = {
                "field_name": found_name,
                "value": record.get(found_name) if found_name else None,
                "error": None,
                "response": response,
                "field_present": found_name is not None,
            }
        else:
            results[_EP_RUNS_METERING] = {
                "field_name": None,
                "value": None,
                "error": "No metering records found in response",
                "response": response,
                "field_present": False,
            }
    except Exception as exc:
        results[_EP_RUNS_METERING] = {
            "field_name": None,
            "value": None,
            "error": str(exc),
            "response": None,
            "field_present": False,
        }

    # ---- Endpoint 2: GET /runs/metering/current ----
    try:
        response = api_client.get_runs_metering_current()
        if isinstance(response, dict) and response:
            found_name = None
            for fname in PERCENT_COMPLETE_FIELD_NAMES:
                if fname in response:
                    found_name = fname
                    break
            results[_EP_RUNS_METERING_CURRENT] = {
                "field_name": found_name,
                "value": response.get(found_name) if found_name else None,
                "error": None,
                "response": response,
                "field_present": found_name is not None,
            }
        else:
            results[_EP_RUNS_METERING_CURRENT] = {
                "field_name": None,
                "value": None,
                "error": (
                    "Empty or non-dict response from current metering endpoint"
                ),
                "response": response,
                "field_present": False,
            }
    except Exception as exc:
        results[_EP_RUNS_METERING_CURRENT] = {
            "field_name": None,
            "value": None,
            "error": str(exc),
            "response": None,
            "field_present": False,
        }

    # ---- Endpoint 3: GET /project ----
    try:
        response = api_client.get_project(project_id)
        found_name, value = _extract_percent_complete_from_project_response(
            response,
        )
        results[_EP_PROJECT] = {
            "field_name": found_name,
            "value": value,
            "error": None,
            "response": response,
            "field_present": found_name is not None,
        }
    except Exception as exc:
        results[_EP_PROJECT] = {
            "field_name": None,
            "value": None,
            "error": str(exc),
            "response": None,
            "field_present": False,
        }

    return results


# =========================================================================
# Test Functions — Field Presence Consistency (core R-004)
# =========================================================================


@pytest.mark.cross_api
def test_percent_complete_present_in_all_endpoints(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """R-004 core test: ``percent_complete`` must be present in ALL THREE endpoints.

    Calls every endpoint for the same project and asserts that the field
    exists in every response.  If the field is present in some endpoints
    but missing from others, the test fails with a detailed inconsistency
    report identifying exactly which endpoints have the field and which
    do not.

    Endpoints that are entirely unreachable (network / auth errors) are
    reported separately from endpoints that return data without the field.
    If *all* endpoints error out, the test is skipped rather than
    producing a misleading pass / fail.
    """
    results = _collect_percent_complete_from_all_endpoints(
        api_client, test_project_id,
    )

    present_in: List[str] = []
    missing_from: List[str] = []
    errored: List[str] = []

    for endpoint in _ALL_ENDPOINTS:
        info = results.get(endpoint, {})
        if info.get("error"):
            errored.append(f"{endpoint} (error: {info['error']})")
        elif info.get("field_present"):
            present_in.append(endpoint)
        else:
            missing_from.append(endpoint)

    # If every endpoint errored, this is a config / network issue — skip.
    if len(errored) == len(_ALL_ENDPOINTS):
        pytest.skip(
            "All endpoints returned errors — likely a configuration or "
            f"network issue.  Errors: {errored}"
        )

    assert not missing_from, (
        f"percent_complete field inconsistency: present in "
        f"{present_in or ['(none)']} but MISSING from {missing_from} "
        f"for project {test_project_id}.  "
        f"Errored endpoints: {errored or ['(none)']}"
    )


@pytest.mark.cross_api
def test_percent_complete_field_name_consistency(
    api_client: APIClient,
    test_project_id: str,
    settings: Settings,
) -> None:
    """Document the naming convention each endpoint uses for ``percent_complete``.

    Per AAP §0.7.1, both ``percent_complete`` (snake_case) and
    ``percentComplete`` (camelCase) are acceptable.  Different naming
    across endpoints is **not** a bug.  The test only fails if the field
    is completely absent under **both** names in any endpoint.

    The ``settings`` fixture is used to log the configured field-name
    variants for traceability.
    """
    configured_names = getattr(settings, "percent_complete_field_names", None)
    field_names_to_check: List[str] = (
        list(configured_names)
        if configured_names
        else list(PERCENT_COMPLETE_FIELD_NAMES)
    )

    results = _collect_percent_complete_from_all_endpoints(
        api_client, test_project_id,
    )

    naming_report: Dict[str, Optional[str]] = {}
    absent_endpoints: List[str] = []

    for endpoint in _ALL_ENDPOINTS:
        info = results.get(endpoint, {})
        if info.get("error"):
            naming_report[endpoint] = f"ERROR: {info['error']}"
            continue
        if info.get("field_present"):
            naming_report[endpoint] = info["field_name"]
        else:
            naming_report[endpoint] = None
            absent_endpoints.append(endpoint)

    # Only fail when the field is completely absent under ALL accepted names.
    assert not absent_endpoints, (
        f"percent_complete field completely absent (not found under "
        f"{field_names_to_check}) in endpoints: {absent_endpoints}.  "
        f"Naming conventions per endpoint: {naming_report}"
    )


# =========================================================================
# Test Functions — Value Consistency
# =========================================================================


@pytest.mark.cross_api
def test_percent_complete_type_consistency(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Verify the data type of ``percent_complete`` is consistent across endpoints.

    All non-null values must be numeric (``int`` or ``float``).  A string,
    boolean, or other non-numeric type from any endpoint constitutes a
    failure.  Additionally, each non-null value is passed through
    :func:`validate_percent_complete` for authoritative type and range
    checking.

    Mixed ``int`` vs ``float`` across endpoints is logged but not treated
    as a failure — both are valid numeric types.
    """
    results = _collect_percent_complete_from_all_endpoints(
        api_client, test_project_id,
    )

    type_report: Dict[str, str] = {}
    invalid_types: List[str] = []

    for endpoint in _ALL_ENDPOINTS:
        info = results.get(endpoint, {})
        if info.get("error"):
            type_report[endpoint] = f"ERROR: {info['error']}"
            continue
        if not info.get("field_present"):
            type_report[endpoint] = "FIELD_ABSENT"
            continue

        value = info["value"]

        if value is None:
            type_report[endpoint] = "null"
            continue

        # Explicit bool rejection (bool is a subclass of int in Python)
        if isinstance(value, bool):
            type_report[endpoint] = f"bool({value})"
            invalid_types.append(
                f"{endpoint}: received bool({value}) instead of numeric"
            )
            continue

        if isinstance(value, (int, float)):
            type_report[endpoint] = type(value).__name__
            # Run authoritative validator for type + range check
            validate_percent_complete(value, endpoint=endpoint)
        else:
            type_report[endpoint] = type(value).__name__
            invalid_types.append(
                f"{endpoint}: received {type(value).__name__}({value!r}) "
                f"instead of numeric"
            )

    assert not invalid_types, (
        f"percent_complete type inconsistency — non-numeric values "
        f"detected: {invalid_types}.  Full type report: {type_report}"
    )


@pytest.mark.cross_api
def test_percent_complete_value_logical_consistency(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """For the same project, ``percent_complete`` values should be close.

    A completed run must not show ``100`` in one endpoint and ``50`` in
    another.  Non-null numeric values are compared pair-wise; any pair
    differing by more than :data:`_VALUE_CONSISTENCY_TOLERANCE` (5.0)
    is reported as a logical inconsistency.

    If fewer than two non-null numeric values are available (e.g. all
    endpoints return ``null`` or have errors), the test is skipped.
    """
    results = _collect_percent_complete_from_all_endpoints(
        api_client, test_project_id,
    )

    numeric_values: List[Tuple[str, float]] = []

    for endpoint in _ALL_ENDPOINTS:
        info = results.get(endpoint, {})
        if info.get("error") or not info.get("field_present"):
            continue
        value = info["value"]
        if (
            value is not None
            and isinstance(value, (int, float))
            and not isinstance(value, bool)
        ):
            numeric_values.append((endpoint, float(value)))

    if len(numeric_values) < 2:
        pytest.skip(
            "Not enough non-null numeric values to compare across "
            f"endpoints.  Found {len(numeric_values)} value(s); "
            "at least 2 are needed for cross-API comparison."
        )

    # Pair-wise comparison
    inconsistencies: List[str] = []
    for i in range(len(numeric_values)):
        for j in range(i + 1, len(numeric_values)):
            ep_a, val_a = numeric_values[i]
            ep_b, val_b = numeric_values[j]
            diff = abs(val_a - val_b)
            if diff > _VALUE_CONSISTENCY_TOLERANCE:
                inconsistencies.append(
                    f"Logical inconsistency: {ep_a} shows "
                    f"percent_complete={val_a}, but {ep_b} shows "
                    f"percent_complete={val_b} for the same project "
                    f"{test_project_id} (difference={diff:.1f}, "
                    f"tolerance={_VALUE_CONSISTENCY_TOLERANCE})"
                )

    assert not inconsistencies, (
        "Cross-API value inconsistencies detected: "
        + "; ".join(inconsistencies)
    )


# =========================================================================
# Test Functions — Null Consistency
# =========================================================================


@pytest.mark.cross_api
def test_percent_complete_null_consistency(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Check null-vs-non-null distribution of ``percent_complete`` across endpoints.

    If ``GET /project`` returns a non-null value but ``GET /runs/metering``
    returns ``null`` for the **same** project, this is flagged as a
    potential data-layer inconsistency because ``runs/metering`` is the
    primary data source.

    A mix of ``null`` and non-null values across endpoints is not always
    a bug (depends on data state and endpoint semantics), but the
    specific combination above is suspicious and warrants investigation.
    """
    results = _collect_percent_complete_from_all_endpoints(
        api_client, test_project_id,
    )

    null_report: Dict[str, str] = {}
    null_endpoints: List[str] = []
    non_null_endpoints: List[str] = []

    for endpoint in _ALL_ENDPOINTS:
        info = results.get(endpoint, {})
        if info.get("error"):
            null_report[endpoint] = f"ERROR: {info['error']}"
            continue
        if not info.get("field_present"):
            null_report[endpoint] = "FIELD_ABSENT"
            continue

        value = info["value"]
        if value is None:
            null_report[endpoint] = "null"
            null_endpoints.append(endpoint)
        else:
            null_report[endpoint] = f"value={value}"
            non_null_endpoints.append(endpoint)

    # Specific suspicious pattern: project has data but runs_metering is null.
    if non_null_endpoints and null_endpoints:
        runs_metering_is_null = _EP_RUNS_METERING in null_endpoints
        project_has_value = _EP_PROJECT in non_null_endpoints

        if project_has_value and runs_metering_is_null:
            assert False, (
                f"Null inconsistency: {_EP_PROJECT} has a non-null "
                f"percent_complete value but {_EP_RUNS_METERING} returns "
                f"null for project {test_project_id}.  The primary data "
                f"source (runs/metering) should have data if the project "
                f"endpoint does.  Full report: {null_report}"
            )


# =========================================================================
# Test Functions — Error Handling / Accessibility
# =========================================================================


@pytest.mark.cross_api
def test_all_endpoints_accessible(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Verify that all three endpoints are accessible and return valid JSON.

    Each endpoint is called individually; the test collects accessibility
    results for all three before asserting.  A descriptive failure message
    lists every inaccessible endpoint alongside its error.
    """
    endpoint_results: Dict[str, Dict[str, Any]] = {}

    # ---- Endpoint 1: GET /runs/metering ----
    try:
        response = api_client.get_runs_metering(test_project_id)
        endpoint_results[_EP_RUNS_METERING] = {
            "accessible": True,
            "valid_json": response is not None,
            "error": None,
        }
    except Exception as exc:
        endpoint_results[_EP_RUNS_METERING] = {
            "accessible": False,
            "valid_json": False,
            "error": str(exc),
        }

    # ---- Endpoint 2: GET /runs/metering/current ----
    try:
        response = api_client.get_runs_metering_current()
        endpoint_results[_EP_RUNS_METERING_CURRENT] = {
            "accessible": True,
            "valid_json": response is not None,
            "error": None,
        }
    except Exception as exc:
        endpoint_results[_EP_RUNS_METERING_CURRENT] = {
            "accessible": False,
            "valid_json": False,
            "error": str(exc),
        }

    # ---- Endpoint 3: GET /project ----
    try:
        response = api_client.get_project(test_project_id)
        endpoint_results[_EP_PROJECT] = {
            "accessible": True,
            "valid_json": response is not None,
            "error": None,
        }
    except Exception as exc:
        endpoint_results[_EP_PROJECT] = {
            "accessible": False,
            "valid_json": False,
            "error": str(exc),
        }

    # Collect failures
    inaccessible: List[str] = [
        f"{ep} (error: {info['error']})"
        for ep, info in endpoint_results.items()
        if not info["accessible"]
    ]

    assert not inaccessible, (
        f"The following endpoints are NOT accessible: {inaccessible}.  "
        f"Full accessibility report: {endpoint_results}"
    )


@pytest.mark.cross_api
def test_endpoints_return_structured_data(
    api_client: APIClient,
    test_project_id: str,
) -> None:
    """Verify response structures are consistent with expected shapes.

    Expected shapes per endpoint:

    - ``GET /runs/metering``         → ``dict`` or ``list`` of metering records
    - ``GET /runs/metering/current`` → ``dict`` with metering data
    - ``GET /project``               → ``dict`` with nested metering block

    Each endpoint is validated for its expected top-level structure.
    The ``validate_field_presence`` utility is used to confirm that
    the metering data contains the ``percent_complete`` field in
    the correct location within the structure.
    """
    structure_issues: List[str] = []

    # ---- Endpoint 1: GET /runs/metering ----
    try:
        response = api_client.get_runs_metering(test_project_id)
        if not isinstance(response, (dict, list)):
            structure_issues.append(
                f"{_EP_RUNS_METERING}: expected dict or list, "
                f"got {type(response).__name__}"
            )
        else:
            # Validate that a metering record contains the field
            record = _extract_first_metering_record(response)
            if record is not None and isinstance(record, dict):
                validate_field_presence(
                    record,
                    field_names=list(PERCENT_COMPLETE_FIELD_NAMES),
                    endpoint=_EP_RUNS_METERING,
                )
    except AssertionError:
        # validate_field_presence raises AssertionError when field missing —
        # re-raise so pytest captures it with its descriptive message.
        raise
    except Exception as exc:
        structure_issues.append(
            f"{_EP_RUNS_METERING}: request failed — {exc}"
        )

    # ---- Endpoint 2: GET /runs/metering/current ----
    try:
        response = api_client.get_runs_metering_current()
        if response is None:
            # None is a legitimate response when no active run exists.
            # This is not a structural defect — skip validation for this
            # endpoint rather than flagging a false failure.
            pass
        elif not isinstance(response, dict):
            structure_issues.append(
                f"{_EP_RUNS_METERING_CURRENT}: expected dict or None, "
                f"got {type(response).__name__}"
            )
        else:
            # Use get_percent_complete_value to both validate presence and
            # extract the value in a single call, then run authoritative
            # type / range validation on the extracted value.
            current_value = get_percent_complete_value(
                response,
                field_names=list(PERCENT_COMPLETE_FIELD_NAMES),
                endpoint=_EP_RUNS_METERING_CURRENT,
            )
            validate_percent_complete(
                current_value, endpoint=_EP_RUNS_METERING_CURRENT,
            )
    except AssertionError:
        raise
    except Exception as exc:
        structure_issues.append(
            f"{_EP_RUNS_METERING_CURRENT}: request failed — {exc}"
        )

    # ---- Endpoint 3: GET /project ----
    try:
        response = api_client.get_project(test_project_id)
        if not isinstance(response, dict):
            structure_issues.append(
                f"{_EP_PROJECT}: expected dict, "
                f"got {type(response).__name__}"
            )
        else:
            # Use the nested extraction helper; run get_percent_complete_value
            # against the metering sub-block to exercise the validator import.
            found_name, value = _extract_percent_complete_from_project_response(
                response,
            )
            if found_name is None:
                structure_issues.append(
                    f"{_EP_PROJECT}: percent_complete field not found in "
                    f"nested metering block or top level.  "
                    f"Checked names: {list(PERCENT_COMPLETE_FIELD_NAMES)}"
                )
            else:
                # Validate extracted value with authoritative validator
                validate_percent_complete(value, endpoint=_EP_PROJECT)
    except AssertionError:
        raise
    except Exception as exc:
        structure_issues.append(
            f"{_EP_PROJECT}: request failed — {exc}"
        )

    assert not structure_issues, (
        f"Response structure issues detected: {structure_issues}"
    )
