# API Response Contracts: `percent_complete` Field Specification

> **Project**: Blitzy Platform API Test Suite
> **Feature**: `percent_complete` / `percentComplete` field in code generation run metering APIs
> **Version**: 1.0
> **Last Updated**: 2026-04-06
> **Author**: Blitzy Platform QA Team

---

## 1. Overview

This document defines the expected JSON response contracts for three Blitzy Platform API endpoints that expose the `percent_complete` field. It serves as the authoritative reference for the automated test suite and manual QA verification workflows within this project.

The `percent_complete` field represents the **progress percentage of a code generation run**, expressed as a value from `0.0` (not started) to `100.0` (fully complete). The field originates from the code generation pipeline's progress tracking, computed as the `current_index / total_steps` ratio, where `total_steps` corresponds to the document section count (indices 0–8, yielding up to 9 steps).

**Data Flow**:

```
Code Gen Pipeline  →  Pub/Sub IN_PROGRESS notifications  →  Platform Data Layer  →  REST API responses
```

Specifically, the pipeline emits `IN_PROGRESS` Pub/Sub notifications containing `current_index` and `total_steps` fields. The platform's data layer computes these into a `percent_complete` value, which is then surfaced through the three REST API endpoints documented below.

The automated tests in this project validate the contracts defined in this document by asserting field presence, data type, value range, and cross-API consistency.

**Target Endpoints**:

| # | Endpoint | Purpose |
|---|----------|---------|
| 1 | `GET /runs/metering` | Historical metering data for multiple runs |
| 2 | `GET /runs/metering/current` | Real-time metering for the active run |
| 3 | `GET /project` | Project details with inline metering data |

---

## 2. The `percent_complete` Field Specification

This section defines the `percent_complete` field contract independently of any specific endpoint. All three target endpoints must conform to this specification.

### 2.1 Field Definition

| Property | Value |
|---|---|
| **Field Name** | `percent_complete` (snake_case) OR `percentComplete` (camelCase) |
| **Type** | `number` (JSON) / `float` or `int` (Python) / `null` |
| **Nullable** | Yes — `null` represents "not applicable" or "no data" |
| **Minimum Value** | `0.0` (inclusive) |
| **Maximum Value** | `100.0` (inclusive) |
| **Integer Acceptable** | Yes — e.g., `50` is valid (not only `50.0`) |
| **Context** | Code generation project runs only |
| **Data Origin** | Computed from `current_index / total_steps` in the code generation pipeline |

### 2.2 Naming Convention Rules

The following naming convention rules govern how the field is identified across API responses:

- Both `percent_complete` (snake_case) and `percentComplete` (camelCase) are **accepted as valid** field names.
- Different endpoints may use different conventions — this is **NOT** a defect.
- The field must be present under **at least ONE** of these names in every applicable response object.
- If the field is completely **absent under BOTH names**, that **IS** a defect (bug) and should cause a test failure.

**Rationale**: The Blitzy Platform API layer may apply different serialization strategies (e.g., Python-native snake_case vs. JavaScript-friendly camelCase) depending on the endpoint or response transformer. The test suite accommodates this by checking for either naming variant.

### 2.3 Valid and Invalid Value Examples

| Value | Type | Valid? | Notes |
|---|---|---|---|
| `75.5` | float | ✅ Yes | Standard in-progress value |
| `100.0` | float | ✅ Yes | Completed run |
| `0.0` | float | ✅ Yes | Just started / no progress |
| `50` | int | ✅ Yes | Integer within range accepted |
| `0` | int | ✅ Yes | Zero as integer is valid |
| `100` | int | ✅ Yes | Maximum as integer is valid |
| `null` | null | ✅ Yes | No data / not applicable |
| `100.1` | float | ❌ No | Exceeds maximum of 100.0 |
| `-1.0` | float | ❌ No | Below minimum of 0.0 |
| `-0.001` | float | ❌ No | Any negative value is invalid |
| `"75"` | string | ❌ No | Wrong type — must be numeric or null |
| `"100.0"` | string | ❌ No | String representation of number is invalid |
| `true` | boolean | ❌ No | Wrong type |
| `false` | boolean | ❌ No | Wrong type |
| `{}` | object | ❌ No | Wrong type |
| `[]` | array | ❌ No | Wrong type |
| *(key missing)* | — | ❌ No | Field absence is a bug |

### 2.4 Validation Logic Summary

The following pseudo-code describes the validation logic applied by the test suite:

```python
def validate_percent_complete(response_obj, field_names=("percent_complete", "percentComplete")):
    # Step 1: Field presence — at least one name must exist
    field_found = any(name in response_obj for name in field_names)
    assert field_found, "percent_complete field missing under all known names"

    # Step 2: Extract value (prefer snake_case, fall back to camelCase)
    value = response_obj.get("percent_complete", response_obj.get("percentComplete"))

    # Step 3: Null acceptance
    if value is None:
        return  # null is a valid value

    # Step 4: Type check — must be numeric (int or float), but NOT bool
    # (Python's bool is a subclass of int, so explicit exclusion is required)
    assert isinstance(value, (int, float)) and not isinstance(value, bool), \
        f"Expected numeric type, got {type(value).__name__}"

    # Step 5: Range check — 0.0 <= value <= 100.0
    assert 0.0 <= value <= 100.0, f"Value {value} outside valid range [0.0, 100.0]"
```

---

## 3. Endpoint 1 — `GET /runs/metering`

### 3.1 Endpoint Details

| Property | Value |
|---|---|
| **Method** | `GET` |
| **Path** | `/runs/metering` |
| **Query Parameters** | `projectId` (required) — identifies the target project |
| **Authentication** | Bearer token in `Authorization` header |
| **Purpose** | Retrieves metering data for multiple code generation runs associated with a project |
| **Trigger Context** | Called when viewing run history or fetching metering data for a project dashboard |
| **Response Type** | Array of run metering objects |

### 3.2 Expected Response Structure

The response contains an array of run metering objects, each representing one code generation run. The `percent_complete` field appears at the run-record level within each array element.

**Sample Response — Multiple Runs (Completed and Pending)**:

```json
{
  "status": "success",
  "data": [
    {
      "run_id": "run_abc123",
      "project_id": "proj_xyz789",
      "percent_complete": 85.5,
      "estimated_hours_saved": 12.3,
      "estimated_lines_generated": 4500,
      "status": "completed",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T11:45:00Z"
    },
    {
      "run_id": "run_def456",
      "project_id": "proj_xyz789",
      "percent_complete": null,
      "estimated_hours_saved": null,
      "estimated_lines_generated": null,
      "status": "pending",
      "created_at": "2025-01-16T09:00:00Z",
      "updated_at": "2025-01-16T09:00:00Z"
    }
  ]
}
```

**Key observations about the sample**:

- The first record (`run_abc123`) shows a completed run with `percent_complete` set to the numeric value `85.5`, demonstrating a valid in-range float value.
- The second record (`run_def456`) shows a pending run with `percent_complete` set to `null`, demonstrating the valid null-value scenario for runs that have no progress data.
- Additional metering fields (`estimated_hours_saved`, `estimated_lines_generated`) are included for context but are not the focus of the `percent_complete` validation.
- The exact top-level response wrapper structure (`status`, `data`) may vary between API versions. Tests focus on the metering objects within the data payload, not the wrapper.

### 3.3 Field Location

The path to `percent_complete` within the response depends on the response structure:

| Response Structure | Field Path |
|---|---|
| Wrapped response (with `data` key) | `response.data[i].percent_complete` or `response.data[i].percentComplete` |
| Direct array response | `response[i].percent_complete` or `response[i].percentComplete` |

Tests should handle both structures by first navigating to the array of metering records, then validating the field within each record. The validation must iterate over **every** record in the array and assert field presence, type, and range for each one individually.

---

## 4. Endpoint 2 — `GET /runs/metering/current`

### 4.1 Endpoint Details

| Property | Value |
|---|---|
| **Method** | `GET` |
| **Path** | `/runs/metering/current` |
| **Query Parameters** | Contextual — may require project or run identification |
| **Authentication** | Bearer token in `Authorization` header |
| **Purpose** | Returns metering data for the currently active (in-progress) code generation run |
| **Trigger Context** | Invoked during live run status views and auto-refresh polling intervals |
| **Response Type** | Single metering object (or null when no active run) |

### 4.2 Expected Response Structure — Active Run

When an active code generation run is in progress, the endpoint returns a single metering object with real-time progress data:

```json
{
  "status": "success",
  "data": {
    "run_id": "run_ghi789",
    "project_id": "proj_xyz789",
    "percent_complete": 42.0,
    "estimated_hours_saved": 5.1,
    "estimated_lines_generated": 1800,
    "status": "in_progress",
    "current_index": 4,
    "total_steps": 9,
    "started_at": "2025-01-17T14:00:00Z"
  }
}
```

**Key observations**:

- The `percent_complete` value (`42.0`) reflects the real-time progress computed from `current_index / total_steps`.
- Calculation example: `current_index = 4`, `total_steps = 9` → `percent_complete ≈ 44.4` (the sample uses `42.0` to illustrate that the exact computation method may vary).
- The `current_index` and `total_steps` fields provide raw progress data that the platform computes into the percentage. These fields may or may not be present in the response — tests focus on `percent_complete`.
- For an active run, `percent_complete` is expected to be a numeric value **less than 100** (since the run has not yet completed). However, edge cases near completion may briefly show `100.0`.

### 4.3 Expected Response Structure — No Active Run

When no code generation run is currently active, the endpoint may return one of the following structures:

**Variant A — Null data payload**:

```json
{
  "status": "success",
  "data": null
}
```

**Variant B — Metering object with null values**:

```json
{
  "status": "success",
  "data": {
    "percent_complete": null,
    "status": "no_active_run"
  }
}
```

**Test handling for no-active-run scenarios**:

- If `data` is `null` (Variant A), the test should accept this as valid — there is no metering object to validate.
- If `data` contains a metering object with `percent_complete: null` (Variant B), the test should validate that the null value is accepted per the field specification.
- Tests requiring an active run should be marked with `@pytest.mark.requires_active_run` and skipped gracefully when no active run is available.

### 4.4 Field Location

| Scenario | Field Path |
|---|---|
| Active run (data is an object) | `response.data.percent_complete` or `response.data.percentComplete` |
| No active run (data is null) | Field is absent — entire `data` payload is `null` |
| No active run (data has null fields) | `response.data.percent_complete` is `null` |

---

## 5. Endpoint 3 — `GET /project`

### 5.1 Endpoint Details

| Property | Value |
|---|---|
| **Method** | `GET` |
| **Path** | `/project` |
| **Query Parameters** | `id` (required) — identifies the target project |
| **Authentication** | Bearer token in `Authorization` header |
| **Purpose** | Returns comprehensive project details with inline metering data embedded |
| **Trigger Context** | Called on project page load and dashboard refresh |
| **Response Type** | Single project object with nested metering block |

### 5.2 Expected Response Structure

The `percent_complete` field is **nested** within a `metering` object inside the project data, which is structurally different from Endpoints 1 and 2:

```json
{
  "status": "success",
  "data": {
    "id": "proj_xyz789",
    "name": "My Code Generation Project",
    "description": "Project description",
    "created_at": "2025-01-10T08:00:00Z",
    "metering": {
      "percent_complete": 100.0,
      "estimated_hours_saved": 24.7,
      "estimated_lines_generated": 9200,
      "total_runs": 5,
      "last_run_status": "completed",
      "last_run_at": "2025-01-17T16:30:00Z"
    }
  }
}
```

**Key observations**:

- The `percent_complete` field is located inside `data.metering`, not directly on the `data` object. This requires tests to navigate one additional nesting level compared to the other two endpoints.
- The `metering` block aggregates data from the **most recent run** — the `percent_complete` value reflects the latest run's progress, not an average or cumulative value across all runs.
- Additional metering fields (`estimated_hours_saved`, `estimated_lines_generated`, `total_runs`, `last_run_status`, `last_run_at`) provide project-level metering context.
- If the `metering` block itself is missing from the project response, this may indicate a separate API issue distinct from the `percent_complete` field presence check. Tests should flag missing metering blocks as a precondition failure.

### 5.3 Field Location

| Response Structure | Field Path |
|---|---|
| Standard nested response | `response.data.metering.percent_complete` or `response.data.metering.percentComplete` |
| Metering block missing | Test precondition failure — metering block expected but absent |
| Metering block present, field missing | Bug — `percent_complete` field should be present |
| Metering block present, field is null | Valid — null represents no metering data |

---

## 6. Cross-API Contract Comparison

The following table summarizes how the `percent_complete` field manifests across all three target endpoints, highlighting the structural differences that tests must account for:

| Aspect | `GET /runs/metering` | `GET /runs/metering/current` | `GET /project` |
|---|---|---|---|
| **Field Location** | `data[i].percent_complete` | `data.percent_complete` | `data.metering.percent_complete` |
| **Nesting Level** | Array item property | Direct property on data object | Nested in metering block |
| **Multiple Records** | Yes (array of runs) | No (single active run) | No (single project) |
| **Null Scenario** | Individual run has no data | No active run exists | Project has no metering data |
| **Naming Convention** | May use either snake_case or camelCase | May use either | May use either |
| **Data Freshness** | Historical (completed and past runs) | Real-time (currently active run) | Aggregated (most recent run) |
| **Value Expectation** | 0–100 for completed; null for pending | < 100 for active; null for none | Reflects latest run state |

### 6.1 Cross-API Consistency Expectations

When querying all three endpoints for the **same project** with the **same run context**, the `percent_complete` values should be logically consistent:

- A **completed run** should show `percent_complete` between `0.0` and `100.0` (typically `100.0`) across all endpoints where it appears.
- An **in-progress run** should show a value less than `100.0` in `GET /runs/metering/current`, and the corresponding record in `GET /runs/metering` should show the same or a slightly different value (accounting for eventual consistency and timing differences).
- The `GET /project` endpoint reflects the **most recent run**, so its `percent_complete` value should match the latest entry from `GET /runs/metering`.
- Minor discrepancies due to **eventual consistency** (e.g., a few percentage points difference between endpoints queried seconds apart) are acceptable and should not cause test failures. Tests should use tolerance-based comparisons rather than exact equality when checking cross-API consistency.

---

## 7. Authentication Contract

All three target endpoints require authentication. This section documents the common authentication requirements.

### 7.1 Required Request Headers

Every API request must include the following headers:

```
Authorization: Bearer {API_TOKEN}
Content-Type: application/json
Accept: application/json
```

| Header | Required | Description |
|---|---|---|
| `Authorization` | Yes | Bearer token for API authentication. Value format: `Bearer <token>` |
| `Content-Type` | Recommended | Set to `application/json` for consistency |
| `Accept` | Recommended | Set to `application/json` to request JSON responses |

The `API_TOKEN` value must be provided via the `API_TOKEN` environment variable. It should never be hardcoded in test files, source modules, or configuration files.

### 7.2 HTTP Status Codes and Error Responses

| HTTP Status | Meaning | Test Handling |
|---|---|---|
| `200 OK` | Success — response body contains valid data | Primary test path — validate response body per this contract |
| `401 Unauthorized` | Invalid or missing authentication token | Fail fast with descriptive error: "Authentication failed — check API_TOKEN" |
| `403 Forbidden` | Insufficient permissions for the requested resource | Fail fast with descriptive error: "Authorization denied — check token permissions" |
| `404 Not Found` | Invalid project ID or run ID in query parameters | Test precondition failure — verify TEST_PROJECT_ID and TEST_RUN_ID |
| `429 Too Many Requests` | Rate limit exceeded | Retry with exponential backoff or skip with warning |
| `500 Internal Server Error` | Server-side error | Retry once or fail with full error details for debugging |
| `502 Bad Gateway` | Upstream service unavailable | Retry or fail with connectivity warning |
| `503 Service Unavailable` | Service temporarily unavailable | Retry with backoff or skip with warning |

### 7.3 Error Response Body Structure

When an error occurs, the API may return a JSON error body:

```json
{
  "status": "error",
  "message": "Unauthorized: Invalid or expired token",
  "code": 401
}
```

Tests should capture and report the error `message` field in assertion failure messages to aid debugging.

---

## 8. Relationship to Pydantic Response Models

The contracts defined in this document are enforced programmatically through Pydantic models defined in `src/models.py`. These models serve as a **secondary validation layer** — the primary validation is performed through explicit assertions in test functions.

### 8.1 Model Mapping

| Endpoint | Pydantic Model | `percent_complete` Definition |
|---|---|---|
| `GET /runs/metering` | `MeteringResponse` | `percent_complete: Optional[float] = Field(None, ge=0.0, le=100.0)` |
| `GET /runs/metering/current` | `CurrentMeteringResponse` | `percent_complete: Optional[float] = Field(None, ge=0.0, le=100.0)` |
| `GET /project` | `ProjectResponse` → `ProjectMeteringBlock` | `percent_complete: Optional[float] = Field(None, ge=0.0, le=100.0)` |

### 8.2 Model Hierarchy for `GET /project`

The `GET /project` response requires a nested model structure due to the metering block:

```
ProjectResponse
├── id: str
├── name: str
├── description: Optional[str]
├── created_at: str
└── metering: ProjectMeteringBlock
    ├── percent_complete: Optional[float]  (ge=0.0, le=100.0)
    ├── estimated_hours_saved: Optional[float]
    ├── estimated_lines_generated: Optional[int]
    ├── total_runs: Optional[int]
    ├── last_run_status: Optional[str]
    └── last_run_at: Optional[str]
```

### 8.3 Validation Layer Strategy

The test suite uses a **dual validation approach**:

1. **Primary Layer — Explicit Test Assertions**: Each test function directly inspects the JSON response using the `validate_percent_complete()` helper from `src/validators.py`. This provides clear, readable test output with descriptive failure messages identifying exactly which endpoint, field, and value failed validation.

2. **Secondary Layer — Pydantic Model Parsing**: Response JSON is optionally parsed through Pydantic models from `src/models.py`. This enforces structural contracts (field presence, types, constraints) at the parsing level and catches schema violations that might be missed by individual assertions.

Both layers enforce the same constraints defined in Section 2 of this document. If either layer detects a violation, the test fails.

---

## 9. Validation Checklist

Use this checklist to verify the completeness and accuracy of this contract document:

- [ ] All three endpoints are documented with complete details (method, path, params, auth, purpose)
- [ ] Sample JSON payloads are valid JSON (parseable by any standard JSON parser)
- [ ] The `percent_complete` field appears in each sample response
- [ ] Field location paths are documented for each endpoint
- [ ] The cross-API comparison table is accurate and covers all relevant aspects
- [ ] Authentication contract (headers, error codes) is documented
- [ ] Naming convention rules (snake_case and camelCase acceptance) are included
- [ ] The valid/invalid value examples table is complete and covers all edge cases
- [ ] The relationship to Pydantic models in `src/models.py` is described
- [ ] No hardcoded actual API tokens, real URLs, or real project IDs appear in this document
- [ ] Markdown formatting is consistent throughout the document
- [ ] The data flow explanation matches the pipeline architecture (Pipeline → Pub/Sub → Data Layer → API)

---

## Appendix A: Quick Reference Card

For rapid lookup during test development and manual QA verification:

```
┌────────────────────────────────────────────────────────────────────┐
│  percent_complete / percentComplete — Quick Reference              │
├────────────────────────────────────────────────────────────────────┤
│  Type:     number | null                                          │
│  Range:    0.0 ≤ value ≤ 100.0 (inclusive)                        │
│  Null OK:  Yes                                                    │
│  Int OK:   Yes (50 is valid, not just 50.0)                       │
│  Names:    percent_complete OR percentComplete (both valid)        │
│  Missing:  BUG — field must be present under at least one name    │
├────────────────────────────────────────────────────────────────────┤
│  Endpoint 1:  GET /runs/metering?projectId=xxx                    │
│    Location:  data[i].percent_complete                            │
│                                                                    │
│  Endpoint 2:  GET /runs/metering/current                          │
│    Location:  data.percent_complete                               │
│                                                                    │
│  Endpoint 3:  GET /project?id=xxx                                 │
│    Location:  data.metering.percent_complete                      │
└────────────────────────────────────────────────────────────────────┘
```

---

## Appendix B: Manual QA Verification via Browser DevTools

For QA team members performing manual verification alongside the automated test suite:

1. **Open DevTools**: Press `F12` or `Ctrl+Shift+I` (Windows/Linux) / `Cmd+Option+I` (macOS).
2. **Navigate to Network tab**: Click the "Network" tab in DevTools.
3. **Enable filters**: Select "Fetch/XHR" filter to isolate API calls. Enable "Preserve log" to retain requests across page navigations.
4. **Trigger API calls**: Perform one of the following actions in the Blitzy Platform UI:
   - Open a project page (triggers `GET /project`)
   - View run history or metering dashboard (triggers `GET /runs/metering`)
   - Start or view an active code generation run (triggers `GET /runs/metering/current`)
5. **Locate the request**: Filter by keywords such as `metering`, `runs`, or `project` in the Network tab search bar.
6. **Inspect the response**: Click the request → go to "Response" or "Preview" tab → search for `percent_complete` or `percentComplete`.
7. **Validate**: Confirm the field is present, its value is numeric (or null), and the value falls within `0.0`–`100.0`.

| Scenario | Expected Value |
|---|---|
| Completed run | Numeric value between 0 and 100 (typically 100.0) |
| In-progress run | Numeric value less than 100 |
| No data available | `null` |
| Field missing entirely | **Bug** — report as defect |
