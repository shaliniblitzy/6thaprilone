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

from typing import Any, Dict, List, Optional, Union


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
