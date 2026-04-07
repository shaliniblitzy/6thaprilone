"""
Custom Validation Utilities for ``percent_complete`` Field.

This module provides validation functions used by the Blitzy Platform API
test suite to verify the presence, data type, and value range of the
``percent_complete`` (or ``percentComplete``) field across three target API
endpoints:

    - ``GET /runs/metering``         — historical run metering data
    - ``GET /runs/metering/current`` — active (in-progress) run metering
    - ``GET /project``               — project details with inline metering

Validation Rules (from AAP §0.7.1):

    +--------------------------+----------+
    | Scenario                 | Expected |
    +==========================+==========+
    | ``None`` / ``null``      | VALID    |
    | ``int`` in [0, 100]      | VALID    |
    | ``float`` in [0.0, 100.0]| VALID    |
    | Value > 100.0            | INVALID  |
    | Value < 0.0              | INVALID  |
    | ``bool``                 | INVALID  |
    | ``str``                  | INVALID  |
    | ``list`` / ``dict``      | INVALID  |
    +--------------------------+----------+

Field Naming Convention:

    Both ``percent_complete`` (snake_case) and ``percentComplete`` (camelCase)
    are accepted.  If neither variant is present in the response, the field is
    considered missing and an ``AssertionError`` is raised.

Usage Example::

    from src.validators import (
        PERCENT_COMPLETE_FIELD_NAMES,
        get_percent_complete_value,
        validate_field_presence,
        validate_percent_complete,
    )

    # Validate a value directly
    validate_percent_complete(42.5, endpoint="GET /runs/metering")

    # Check field presence in a response dict
    found = validate_field_presence(
        {"percentComplete": 75.0},
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint="GET /runs/metering/current",
    )
    assert found == "percentComplete"

    # Extract value regardless of naming convention
    value = get_percent_complete_value(
        {"percent_complete": 99.9},
        PERCENT_COMPLETE_FIELD_NAMES,
        endpoint="GET /project",
    )
    assert value == 99.9
"""

from typing import Any, Dict, List, Optional, Tuple, Union


# ---------------------------------------------------------------------------
# Module-level constant: accepted field name variants
# ---------------------------------------------------------------------------

PERCENT_COMPLETE_FIELD_NAMES: List[str] = ["percent_complete", "percentComplete"]
"""Both naming conventions the Blitzy Platform API may use for the completion
percentage field.  Test modules import this constant to avoid hard-coding the
list of accepted names in every test function."""


# ---------------------------------------------------------------------------
# validate_percent_complete — type, range, and null validation
# ---------------------------------------------------------------------------

def validate_percent_complete(value: Any, endpoint: str = "") -> None:
    """Validate that a ``percent_complete`` value meets all constraints.

    The function enforces the following rules (AAP §0.7.1 Value Constraint
    Rules):

    * ``None`` is valid — represents "not applicable" or "no data".
    * ``int`` or ``float`` within the inclusive range ``[0.0, 100.0]`` is
      valid.
    * Values greater than ``100.0`` or less than ``0.0`` are invalid.
    * Non-numeric types (``str``, ``bool``, ``list``, ``dict``, etc.) are
      invalid.

    .. important::

       Python's ``bool`` is a subclass of ``int``.  This function explicitly
       rejects boolean values to prevent ``True`` (``== 1``) and ``False``
       (``== 0``) from being silently accepted as valid percentages.

    Parameters
    ----------
    value : Any
        The raw value extracted from the API response JSON.  May be
        ``None``, a numeric type, or any other type (which will cause the
        assertion to fail).
    endpoint : str, optional
        An identifier for the API endpoint being tested (e.g.
        ``"GET /runs/metering"``).  Included in assertion failure messages
        to make test output actionable.

    Raises
    ------
    AssertionError
        If *value* is not ``None`` and fails the type check or range check.
        The error message always includes the endpoint name, the field being
        validated, and the actual value / type that was received.
    """
    # Rule: None / null is always valid — no further checks needed.
    if value is None:
        return

    # Rule: Must be numeric (int or float) but NOT bool.
    # Python's bool is a subclass of int, so isinstance(True, int) is True.
    # We must explicitly exclude bool to prevent True/False from passing.
    _endpoint_tag: str = f"[{endpoint}] " if endpoint else ""
    assert isinstance(value, (int, float)) and not isinstance(value, bool), (
        f"{_endpoint_tag}percent_complete must be numeric (int/float) or null, "
        f"got {type(value).__name__}: {value!r}"
    )

    # Rule: Value must be within the inclusive range [0.0, 100.0].
    assert 0.0 <= value <= 100.0, (
        f"{_endpoint_tag}percent_complete must be between 0.0 and 100.0 inclusive, "
        f"got {value}"
    )


# ---------------------------------------------------------------------------
# validate_field_presence — check for field name in response dict
# ---------------------------------------------------------------------------

def validate_field_presence(
    response_data: Dict[str, Any],
    field_names: Optional[List[str]] = None,
    endpoint: str = "",
) -> str:
    """Assert that at least one ``percent_complete`` field name variant exists
    in *response_data* and return the matched name.

    The Blitzy Platform API may serialise the completion-percentage field as
    either ``percent_complete`` (snake_case) or ``percentComplete``
    (camelCase) depending on the endpoint or API version.  This function
    checks for **any** of the supplied variants and returns the first match.

    Parameters
    ----------
    response_data : Dict[str, Any]
        The parsed JSON body (``dict``) of the API response.
    field_names : Optional[List[str]]
        Ordered list of acceptable field name variants to look for.  When
        ``None`` or empty, falls back to
        :data:`PERCENT_COMPLETE_FIELD_NAMES`.
    endpoint : str, optional
        API endpoint identifier for descriptive error messages.

    Returns
    -------
    str
        The first field name from *field_names* that is present as a key in
        *response_data*.

    Raises
    ------
    AssertionError
        If **none** of the supplied field names exist in *response_data*.
        The error message lists which names were checked and which keys are
        actually present in the response.
    """
    # Default to the module-level constant when no explicit list is provided.
    if not field_names:
        field_names = PERCENT_COMPLETE_FIELD_NAMES

    for field_name in field_names:
        if field_name in response_data:
            return field_name

    # None of the expected field names were found — this is a bug in the API.
    _endpoint_tag: str = f"[{endpoint}] " if endpoint else ""
    raise AssertionError(
        f"{_endpoint_tag}percent_complete field not found in response. "
        f"Checked field names: {field_names}. "
        f"Available keys: {sorted(response_data.keys())}"
    )


# ---------------------------------------------------------------------------
# get_percent_complete_value — extract value regardless of naming convention
# ---------------------------------------------------------------------------

def get_percent_complete_value(
    response_data: Dict[str, Any],
    field_names: Optional[List[str]] = None,
    endpoint: str = "",
) -> Union[int, float, None]:
    """Extract the ``percent_complete`` value from *response_data*, regardless
    of which naming convention the API used.

    This is a convenience wrapper that first locates the field (via
    :func:`validate_field_presence`) and then returns its value.

    Parameters
    ----------
    response_data : Dict[str, Any]
        The parsed JSON body (``dict``) of the API response.
    field_names : Optional[List[str]]
        Ordered list of acceptable field name variants.  When ``None`` or
        empty, falls back to :data:`PERCENT_COMPLETE_FIELD_NAMES`.
    endpoint : str, optional
        API endpoint identifier for descriptive error messages.

    Returns
    -------
    Union[int, float, None]
        The raw value stored under the matched field name.  The caller is
        responsible for further validation (e.g. by passing this value to
        :func:`validate_percent_complete`).

    Raises
    ------
    AssertionError
        Propagated from :func:`validate_field_presence` if the field is not
        found under any of the supplied name variants.
    """
    # Default to the module-level constant when no explicit list is provided.
    if not field_names:
        field_names = PERCENT_COMPLETE_FIELD_NAMES

    found_field_name: str = validate_field_presence(
        response_data,
        field_names=field_names,
        endpoint=endpoint,
    )
    return response_data[found_field_name]


# ---------------------------------------------------------------------------
# validate_response_structure — structural sanity checks on API responses
# ---------------------------------------------------------------------------

def validate_response_structure(
    response_data: Any,
    endpoint: str = "",
) -> Tuple[str, Any]:
    """Validate the top-level structure of an API response and locate the
    ``percent_complete`` field.

    Performs a series of structural sanity checks to ensure the API response
    is well-formed and contains the expected ``percent_complete`` field in a
    discoverable location.  Returns a ``(found_field_name, value)`` tuple
    for downstream validation.

    The function handles multiple response envelope shapes:

    * **Flat dict** — ``percent_complete`` is a direct key
    * **Wrapped list** — the response contains a ``data``, ``runs``,
      ``results``, or ``items`` key holding a list of record dicts
    * **Nested metering block** — a ``metering`` key holds a sub-dict
      containing ``percent_complete`` (typical for ``GET /project``)

    Parameters
    ----------
    response_data : Any
        The raw parsed JSON body from the API.
    endpoint : str, optional
        API endpoint identifier for descriptive error messages.

    Returns
    -------
    Tuple[str, Any]
        A 2-tuple of ``(found_field_name, value)`` where
        *found_field_name* is the key under which the field was discovered
        and *value* is the associated value (may be ``None``).

    Raises
    ------
    AssertionError
        If *response_data* is not a ``dict`` or ``list``, or if the
        ``percent_complete`` field cannot be located in any recognised
        location within the response structure.
    """
    _tag: str = f"[{endpoint}] " if endpoint else ""

    # ------------------------------------------------------------------
    # Step 1: Top-level type check
    # ------------------------------------------------------------------
    assert isinstance(response_data, (dict, list)), (
        f"{_tag}Expected API response to be a dict or list, "
        f"got {type(response_data).__name__}: {response_data!r}"
    )

    # ------------------------------------------------------------------
    # Step 2: Locate percent_complete in the structure
    # ------------------------------------------------------------------

    # Case A: response is a dict — search directly, then nested locations
    if isinstance(response_data, dict):
        # A.1 — Direct key match at the top level
        for field_name in PERCENT_COMPLETE_FIELD_NAMES:
            if field_name in response_data:
                return field_name, response_data[field_name]

        # A.2 — Nested inside a "metering" sub-object
        metering_keys = ("metering", "metering_data", "meteringData")
        for mkey in metering_keys:
            if mkey in response_data and isinstance(response_data[mkey], dict):
                sub = response_data[mkey]
                for field_name in PERCENT_COMPLETE_FIELD_NAMES:
                    if field_name in sub:
                        return field_name, sub[field_name]

        # A.3 — Inside a list wrapper (data, runs, results, items)
        for wrapper_key in ("data", "runs", "results", "items"):
            if wrapper_key in response_data:
                inner = response_data[wrapper_key]
                if isinstance(inner, list) and inner:
                    first = inner[0]
                    if isinstance(first, dict):
                        for field_name in PERCENT_COMPLETE_FIELD_NAMES:
                            if field_name in first:
                                return field_name, first[field_name]

    # Case B: response is a list — check the first element
    if isinstance(response_data, list):
        assert len(response_data) > 0, (
            f"{_tag}Response is an empty list — cannot locate "
            f"percent_complete field."
        )
        first_item = response_data[0]
        assert isinstance(first_item, dict), (
            f"{_tag}First element in response list is not a dict: "
            f"got {type(first_item).__name__}"
        )
        for field_name in PERCENT_COMPLETE_FIELD_NAMES:
            if field_name in first_item:
                return field_name, first_item[field_name]

    # ------------------------------------------------------------------
    # Step 3: Field not found anywhere — assertion failure
    # ------------------------------------------------------------------
    raise AssertionError(
        f"{_tag}percent_complete field not found anywhere in the API "
        f"response structure.  Checked field names: "
        f"{PERCENT_COMPLETE_FIELD_NAMES}.  "
        f"Response type: {type(response_data).__name__}.  "
        f"Top-level keys: {sorted(response_data.keys()) if isinstance(response_data, dict) else 'N/A (list)'}."
    )
