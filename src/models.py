"""
Pydantic Response Models for Blitzy Platform API Endpoints.

This module defines Pydantic v2 response models that enforce the expected JSON
structure at the parsing layer for the three target Blitzy Platform API endpoints:

    - GET /runs/metering         → MeteringResponse (wraps List[MeteringData])
    - GET /runs/metering/current → CurrentMeteringResponse
    - GET /project               → ProjectResponse (contains ProjectMeteringBlock)

All models validate the ``percent_complete`` field with the following constraints:

    - Type: ``Optional[float]`` (nullable; ``int`` values are auto-coerced to ``float``)
    - Range: ``0.0 ≤ value ≤ 100.0`` (inclusive) when not ``None``
    - Naming: Accepts both ``percent_complete`` (snake_case) and ``percentComplete``
      (camelCase) via Pydantic v2 alias + ``populate_by_name=True``
    - Extra fields: All models use ``extra="allow"`` so that additional API response
      fields that are not explicitly modeled are preserved rather than rejected.

Usage Example::

    from src.models import MeteringData, MeteringResponse, ProjectResponse

    # Parse a single metering record (snake_case key)
    record = MeteringData.model_validate({"percent_complete": 42.5})
    assert record.percent_complete == 42.5

    # Parse a single metering record (camelCase key)
    record = MeteringData.model_validate({"percentComplete": 75.0})
    assert record.percent_complete == 75.0

    # Null is valid
    record = MeteringData.model_validate({"percent_complete": None})
    assert record.percent_complete is None

    # Wrap a list of records
    resp = MeteringResponse.model_validate({"data": [{"percent_complete": 10.0}]})
    assert resp.data[0].percent_complete == 10.0

    # Project response with nested metering block
    proj = ProjectResponse.model_validate({
        "id": "proj-1",
        "name": "My Project",
        "metering": {"percent_complete": 99.9}
    })
    assert proj.metering.percent_complete == 99.9
"""

from typing import List, Optional

from pydantic import BaseModel, ConfigDict, Field


# ---------------------------------------------------------------------------
# MeteringData — single metering record for a code generation run
# ---------------------------------------------------------------------------

class MeteringData(BaseModel):
    """Represents a single metering record for a code generation run.

    This model is used as the element type inside ``MeteringResponse.data``.
    It captures the core metering fields that the Blitzy Platform API returns
    for each run, with the ``percent_complete`` field being the primary field
    under test.

    Attributes:
        percent_complete: Completion percentage of the code generation run.
            Accepts both ``percent_complete`` (snake_case) and
            ``percentComplete`` (camelCase) JSON keys.  Value must be
            ``None`` or a float in the inclusive range ``[0.0, 100.0]``.
            Integer values are automatically coerced to ``float`` by Pydantic.
        estimated_hours_saved: Estimated developer hours saved by the code
            generation run.  May be ``None`` when the data is unavailable.
        estimated_lines_generated: Estimated number of source lines produced
            by the code generation run.  May be ``None`` when unavailable.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    percent_complete: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        alias="percentComplete",
        description="Completion percentage of the code generation run (0.0–100.0 inclusive, or null).",
    )
    estimated_hours_saved: Optional[float] = Field(
        default=None,
        description="Estimated developer hours saved by the code generation run.",
    )
    estimated_lines_generated: Optional[int] = Field(
        default=None,
        description="Estimated number of source lines produced by the code generation run.",
    )


# ---------------------------------------------------------------------------
# MeteringResponse — wrapper for GET /runs/metering
# ---------------------------------------------------------------------------

class MeteringResponse(BaseModel):
    """Response model for the ``GET /runs/metering`` endpoint.

    The endpoint returns metering data for multiple code generation runs
    associated with a project.  The exact wrapper structure may vary across
    API versions, so this model uses ``extra="allow"`` to accommodate
    additional top-level keys (e.g. ``meta``, ``pagination``).

    Attributes:
        data: List of :class:`MeteringData` records, one per run.  May be
            ``None`` if the API returns an empty or absent ``data`` key.
    """

    model_config = ConfigDict(extra="allow")

    data: Optional[List[MeteringData]] = Field(
        default=None,
        description="List of run metering records returned by the API.",
    )


# ---------------------------------------------------------------------------
# CurrentMeteringResponse — GET /runs/metering/current
# ---------------------------------------------------------------------------

class CurrentMeteringResponse(BaseModel):
    """Response model for the ``GET /runs/metering/current`` endpoint.

    This endpoint returns metering data for the currently active (in-progress)
    code generation run.  The response is a single metering object rather than
    a list, reflecting real-time progress.

    Attributes:
        percent_complete: Completion percentage of the active run.  Accepts
            both ``percent_complete`` (snake_case) and ``percentComplete``
            (camelCase).  Value must be ``None`` or a float in ``[0.0, 100.0]``.
        estimated_hours_saved: Estimated developer hours saved so far.
        estimated_lines_generated: Estimated lines generated so far.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    percent_complete: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        alias="percentComplete",
        description="Completion percentage of the active code generation run (0.0–100.0 inclusive, or null).",
    )
    estimated_hours_saved: Optional[float] = Field(
        default=None,
        description="Estimated developer hours saved by the active run.",
    )
    estimated_lines_generated: Optional[int] = Field(
        default=None,
        description="Estimated number of source lines produced by the active run.",
    )


# ---------------------------------------------------------------------------
# ProjectMeteringBlock — nested metering block inside ProjectResponse
# ---------------------------------------------------------------------------

class ProjectMeteringBlock(BaseModel):
    """Nested metering data block embedded within the project response.

    When the ``GET /project`` endpoint returns project details, metering
    information is included as an inline object rather than at the top level.
    This model captures that nested structure.

    Attributes:
        percent_complete: Completion percentage from the most recent run.
            Accepts both ``percent_complete`` and ``percentComplete`` keys.
            Must be ``None`` or a float in ``[0.0, 100.0]``.
        estimated_hours_saved: Aggregated developer hours saved.
        estimated_lines_generated: Aggregated lines of code generated.
    """

    model_config = ConfigDict(populate_by_name=True, extra="allow")

    percent_complete: Optional[float] = Field(
        default=None,
        ge=0.0,
        le=100.0,
        alias="percentComplete",
        description="Completion percentage from the most recent code generation run (0.0–100.0 inclusive, or null).",
    )
    estimated_hours_saved: Optional[float] = Field(
        default=None,
        description="Aggregated developer hours saved across runs.",
    )
    estimated_lines_generated: Optional[int] = Field(
        default=None,
        description="Aggregated lines of source code generated across runs.",
    )


# ---------------------------------------------------------------------------
# ProjectResponse — GET /project
# ---------------------------------------------------------------------------

class ProjectResponse(BaseModel):
    """Response model for the ``GET /project`` endpoint.

    Returns comprehensive project details including an inline metering block
    that contains the ``percent_complete`` field.  The metering data is
    accessed via ``response.metering.percent_complete`` — it is **not** at
    the top level of the project response.

    Attributes:
        id: Unique project identifier (UUID string or platform-specific ID).
        name: Human-readable project name.
        metering: Nested :class:`ProjectMeteringBlock` containing metering
            metrics including ``percent_complete``.  May be ``None`` when
            metering data is not yet available for the project.
    """

    model_config = ConfigDict(extra="allow")

    id: Optional[str] = Field(
        default=None,
        description="Unique project identifier.",
    )
    name: Optional[str] = Field(
        default=None,
        description="Human-readable project name.",
    )
    metering: Optional[ProjectMeteringBlock] = Field(
        default=None,
        description="Nested metering block containing percent_complete and related metrics.",
    )
