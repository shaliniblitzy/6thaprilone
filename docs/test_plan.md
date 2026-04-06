# Test Plan: `percent_complete` Field Validation

## Document Metadata

| Property              | Value                                                                                              |
|-----------------------|----------------------------------------------------------------------------------------------------|
| **Project**           | Blitzy Platform API Test Suite                                                                     |
| **Feature Under Test**| `percent_complete` / `percentComplete` field across code generation run metering and project APIs   |
| **Version**           | 1.0                                                                                                |
| **Last Updated**      | 2026-04-06                                                                                         |
| **Author**            | Blitzy Platform QA Team                                                                            |

---

## 1. Executive Summary

This test plan defines the verification strategy for the newly introduced `percent_complete` field across three Blitzy Platform API endpoints related to code generation run metering and project data. The purpose of this plan is to ensure that the field is consistently present, correctly typed, and constrained within a valid value range in every API response that exposes code generation progress.

The three target API endpoints under test are:

- **`GET /runs/metering?projectId={id}`** — Retrieves historical run metering data for a given project, returning an array of run metering objects each expected to contain the `percent_complete` field.
- **`GET /runs/metering/current`** — Returns metering data for the currently active (in-progress) code generation run, with `percent_complete` reflecting real-time progress.
- **`GET /project?id={id}`** — Returns comprehensive project details with inline metering data embedded in a nested structure, including the `percent_complete` field.

The `percent_complete` field originates from the code generation pipeline's progress tracking. It is propagated through Pub/Sub `IN_PROGRESS` notifications containing `current_index` and `total_steps` fields, stored by the platform data layer as a computed percentage, and surfaced through the three target REST APIs listed above. This test plan maps each functional requirement (R-001 through R-005) to specific automated test functions, documents preconditions and expected outcomes, and provides a comprehensive execution strategy for both automated CI runs and manual QA verification workflows.

---

## 2. Requirements Traceability Matrix

The following table maps each requirement to its corresponding test coverage, including the test files, specific test functions, and priority level.

| Requirement ID | Requirement Name             | Description                                                                                                                 | Test File(s)                                                                                         | Test Function(s)                                                                                                                                                               | Priority |
|----------------|------------------------------|-----------------------------------------------------------------------------------------------------------------------------|------------------------------------------------------------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------|----------|
| R-001          | Field Presence Validation    | Verify that the `percent_complete` or `percentComplete` field exists in the JSON response payload of all three target endpoints | `test_runs_metering.py`, `test_runs_metering_current.py`, `test_project.py`                          | `test_percent_complete_field_present` (in each file)                                                                                                                           | Critical |
| R-002          | Data Type Validation         | Confirm that the field value is numeric (`float` or `int`) or explicitly `null` — never a string, boolean, or other type     | `test_runs_metering.py`, `test_runs_metering_current.py`, `test_project.py`                          | `test_percent_complete_type_valid` (in each file)                                                                                                                              | Critical |
| R-003          | Value Range Validation       | Assert that when the field value is not `null`, it falls within the inclusive range `0.0` to `100.0`                         | `test_runs_metering.py`, `test_runs_metering_current.py`, `test_project.py`                          | `test_percent_complete_value_range` (in each file)                                                                                                                             | Critical |
| R-004          | Cross-API Consistency        | Ensure the field is consistently present across all three APIs for the same project/run context                               | `test_cross_api_consistency.py`                                                                      | `test_field_present_in_all_endpoints`, `test_field_consistency_across_endpoints`                                                                                                | High     |
| R-005          | Edge Case Coverage           | Validate negative scenarios including values exceeding 100, values below 0, wrong data types, null handling, and field name mismatches | `test_edge_cases.py`                                                                                 | `test_boundary_exactly_zero`, `test_boundary_exactly_hundred`, `test_null_value_accepted`, `test_value_over_hundred_invalid`, `test_negative_value_invalid`, `test_wrong_type_invalid` | High     |

---

## 3. Test Suite Structure

### 3.1 Test Organization Overview

The test suite is organized into five logical groups, each targeting a specific aspect of the `percent_complete` field validation:

1. **Endpoint-Specific Tests** — One test module per target API endpoint, ensuring each endpoint independently meets all field requirements.
   - `tests/test_runs_metering.py` — Tests for `GET /runs/metering`
   - `tests/test_runs_metering_current.py` — Tests for `GET /runs/metering/current`
   - `tests/test_project.py` — Tests for `GET /project`

2. **Cross-API Consistency Tests** — A dedicated module verifying that field behavior is consistent across all three endpoints when queried for the same project and run context.
   - `tests/test_cross_api_consistency.py` — Verifies field presence, value consistency, and naming convention alignment across all three endpoints

3. **Edge Case and Boundary Tests** — A dedicated module for negative scenarios and boundary conditions that exercise the validation logic using simulated and mock data.
   - `tests/test_edge_cases.py` — Covers boundary values (0.0, 100.0), null handling, out-of-range values, wrong types, and missing fields

4. **Shared Infrastructure** — Common pytest fixtures and configuration shared across all test modules.
   - `tests/conftest.py` — Shared pytest fixtures including authenticated API client instance, test project ID, test run ID, and conditional skip markers

5. **Supporting Modules** — Source code modules providing the HTTP client, validation utilities, response models, and configuration management.
   - `src/api_client.py` — HTTP client wrapping `requests` with methods for each target endpoint
   - `src/validators.py` — Validation helper functions for field presence, type checking, and range verification
   - `src/models.py` — Pydantic response models defining expected JSON structures
   - `src/config.py` — Configuration management using environment variables and settings files

### 3.2 Test File Descriptions

#### `tests/test_runs_metering.py`

- **Target Endpoint**: `GET /runs/metering?projectId={id}`
- **Pytest Markers**: `@pytest.mark.runs_metering`
- **Test Functions**:
  - `test_percent_complete_field_present` — Asserts the field key exists in each run record
  - `test_percent_complete_type_valid` — Asserts the field value type is `int`, `float`, or `None`
  - `test_percent_complete_value_range` — Asserts non-null values satisfy `0.0 <= value <= 100.0`
  - `test_response_status_code` — Asserts the endpoint returns HTTP 200 OK
  - `test_field_naming_convention` — Asserts at least one of `percent_complete` or `percentComplete` is present
- **Pass Criteria**: All assertions pass with a valid project ID that has code generation run history
- **Fail Criteria**: Any assertion failure indicates a field contract violation

#### `tests/test_runs_metering_current.py`

- **Target Endpoint**: `GET /runs/metering/current`
- **Pytest Markers**: `@pytest.mark.runs_metering_current`, `@pytest.mark.requires_active_run` (on applicable tests)
- **Test Functions**:
  - `test_percent_complete_field_present` — Asserts the field exists for the current run
  - `test_percent_complete_type_valid` — Asserts the field value type is numeric or null
  - `test_percent_complete_value_range` — Asserts non-null values are within the valid range
  - `test_active_run_less_than_hundred` — Asserts an in-progress run has a value strictly less than 100
  - `test_no_active_run_returns_null` — Asserts null or appropriate response when no run is active
- **Pass Criteria**: All assertions pass; tests marked `requires_active_run` are skipped if no active run exists
- **Fail Criteria**: Field missing, wrong type, or out-of-range value

#### `tests/test_project.py`

- **Target Endpoint**: `GET /project?id={id}`
- **Pytest Markers**: `@pytest.mark.project`
- **Test Functions**:
  - `test_percent_complete_field_present` — Asserts the field exists within the nested metering data block
  - `test_percent_complete_type_valid` — Asserts the nested field value type is numeric or null
  - `test_percent_complete_value_range` — Asserts non-null values are within the valid range
  - `test_metering_block_exists` — Asserts the metering data structure is present in the project response
- **Pass Criteria**: All assertions pass with a valid project ID
- **Fail Criteria**: Missing metering block, missing field, wrong type, or out-of-range value

#### `tests/test_cross_api_consistency.py`

- **Target Endpoints**: All three (`GET /runs/metering`, `GET /runs/metering/current`, `GET /project`)
- **Pytest Markers**: `@pytest.mark.cross_api`
- **Test Functions**:
  - `test_field_present_in_all_endpoints` — Calls all three endpoints for the same project and asserts field presence in all responses
  - `test_field_consistency_across_endpoints` — Compares `percent_complete` values across endpoints for logical consistency
  - `test_field_naming_consistency` — Documents and verifies the naming convention used by each endpoint
- **Pass Criteria**: Field present in all three; values are logically consistent for the same run context
- **Fail Criteria**: Field missing in any endpoint, or values are contradictory across endpoints

#### `tests/test_edge_cases.py`

- **Target**: Validation logic and simulated/mock data scenarios
- **Pytest Markers**: `@pytest.mark.edge_cases`
- **Test Functions**:
  - `test_boundary_exactly_zero` — Validates that 0.0 is accepted
  - `test_boundary_exactly_hundred` — Validates that 100.0 is accepted
  - `test_null_value_accepted` — Validates that `null` is accepted as a valid value
  - `test_value_over_hundred_invalid` — Validates that values greater than 100 are flagged as invalid
  - `test_negative_value_invalid` — Validates that negative values are flagged as invalid
  - `test_wrong_type_string_invalid` — Validates that a string like `"50%"` is flagged as invalid
  - `test_wrong_type_boolean_invalid` — Validates that a boolean like `true` is flagged as invalid
  - `test_field_completely_missing` — Validates that a response missing both field name variants is flagged as a defect
  - `test_integer_value_accepted` — Validates that an integer value like `50` (not `50.0`) is accepted
- **Pass Criteria**: Valid values and null accepted; invalid values, wrong types, and missing fields correctly rejected
- **Fail Criteria**: Validator incorrectly accepts invalid data or rejects valid data

---

## 4. Detailed Test Cases

### 4.1 `tests/test_runs_metering.py` — `GET /runs/metering`

| Test Function                          | Description                            | Preconditions                              | Steps                                                                                          | Expected Result                                                                 |
|----------------------------------------|----------------------------------------|--------------------------------------------|------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| `test_percent_complete_field_present`  | Verify field exists in response        | Valid project ID with run history          | 1. Call `GET /runs/metering?projectId={id}` 2. Parse JSON response 3. Inspect each run record  | `percent_complete` or `percentComplete` key exists in each run metering record   |
| `test_percent_complete_type_valid`     | Verify field is numeric or null        | Valid project ID with run history          | 1. Call endpoint 2. Extract field value from each record 3. Check Python type                  | Value is `int`, `float`, or `None` for every run record                         |
| `test_percent_complete_value_range`    | Verify value is within 0–100 inclusive | Valid project ID with completed runs       | 1. Call endpoint 2. Extract non-null field values 3. Assert bounds                             | `0.0 <= value <= 100.0` for every non-null value                                |
| `test_response_status_code`            | Verify successful API response         | Valid authentication credentials           | 1. Call endpoint with valid auth 2. Check HTTP status code                                     | HTTP 200 OK                                                                     |
| `test_field_naming_convention`         | Verify either snake_case or camelCase  | Valid project ID                           | 1. Call endpoint 2. Check for `percent_complete` key 3. Check for `percentComplete` key        | At least one of the two naming conventions is present in the response            |

### 4.2 `tests/test_runs_metering_current.py` — `GET /runs/metering/current`

| Test Function                          | Description                            | Preconditions                              | Steps                                                                                          | Expected Result                                                                 |
|----------------------------------------|----------------------------------------|--------------------------------------------|------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| `test_percent_complete_field_present`  | Verify field exists for current run    | Active code generation run                 | 1. Call `GET /runs/metering/current` 2. Parse JSON response 3. Inspect response object         | `percent_complete` or `percentComplete` field is present in the response         |
| `test_percent_complete_type_valid`     | Verify field type                      | Active code generation run                 | 1. Call endpoint 2. Extract field value 3. Check Python type                                   | Value is `int`, `float`, or `None`                                              |
| `test_percent_complete_value_range`    | Verify value range                     | Active run with progress data              | 1. Call endpoint 2. Extract non-null field value 3. Assert bounds                              | `0.0 <= value <= 100.0`                                                         |
| `test_active_run_less_than_hundred`    | Verify in-progress value               | Known in-progress run (not yet completed)  | 1. Call endpoint 2. Extract field value 3. Assert value is strictly less than 100               | Value < 100 (in-progress runs should not report 100% completion)                |
| `test_no_active_run_returns_null`      | Verify null when no active run         | No active code generation runs             | 1. Call endpoint 2. Parse response 3. Check field value                                        | Field value is `null` or the response indicates no active run appropriately     |

> **Note**: Tests with the precondition "Active code generation run" are decorated with `@pytest.mark.requires_active_run` and will be automatically skipped if no active run is available, preventing false failures in environments without live runs.

### 4.3 `tests/test_project.py` — `GET /project`

| Test Function                          | Description                                | Preconditions                          | Steps                                                                                                  | Expected Result                                                                 |
|----------------------------------------|--------------------------------------------|----------------------------------------|--------------------------------------------------------------------------------------------------------|---------------------------------------------------------------------------------|
| `test_percent_complete_field_present`  | Verify field in nested metering block      | Valid project ID                       | 1. Call `GET /project?id={id}` 2. Parse JSON 3. Navigate to metering data block 4. Inspect for field   | `percent_complete` or `percentComplete` key present within the nested metering structure |
| `test_percent_complete_type_valid`     | Verify field type in project response      | Valid project ID                       | 1. Call endpoint 2. Navigate to nested metering block 3. Extract field value 4. Check type             | Value is `int`, `float`, or `None`                                              |
| `test_percent_complete_value_range`    | Verify value range                         | Valid project ID with run history      | 1. Call endpoint 2. Navigate to metering block 3. Extract non-null value 4. Assert bounds              | `0.0 <= value <= 100.0` when value is not null                                  |
| `test_metering_block_exists`           | Verify metering data structure is present  | Valid project ID                       | 1. Call endpoint 2. Parse JSON response 3. Check for metering object/block                             | A metering data object or block is present in the project response              |

### 4.4 `tests/test_cross_api_consistency.py`

| Test Function                              | Description                                | Preconditions                                  | Steps                                                                                                                          | Expected Result                                                                                           |
|--------------------------------------------|--------------------------------------------|-------------------------------------------------|--------------------------------------------------------------------------------------------------------------------------------|-----------------------------------------------------------------------------------------------------------|
| `test_field_present_in_all_endpoints`      | Verify field present across all three APIs | Valid project ID with existing run history      | 1. Call `GET /runs/metering?projectId={id}` 2. Call `GET /runs/metering/current` 3. Call `GET /project?id={id}` 4. Check each  | `percent_complete` or `percentComplete` field is present in every response from all three endpoints        |
| `test_field_consistency_across_endpoints`  | Verify logical value consistency           | Valid project ID with a completed run           | 1. Call all three endpoints for the same project 2. Extract `percent_complete` values 3. Compare logically                     | Values are logically consistent (e.g., a completed run shows approximately 100 across all endpoints)       |
| `test_field_naming_consistency`            | Check naming convention across APIs        | Valid project ID                                | 1. Call all three endpoints 2. Record which field name (`percent_complete` vs `percentComplete`) each uses                     | Document which convention each endpoint uses; either convention is valid but absence of both is a defect   |

### 4.5 `tests/test_edge_cases.py`

| Test Function                          | Description                              | Preconditions                          | Steps                                                            | Expected Result                                                                 |
|----------------------------------------|------------------------------------------|----------------------------------------|------------------------------------------------------------------|---------------------------------------------------------------------------------|
| `test_boundary_exactly_zero`           | Boundary: value = 0.0                    | Test data or mock with value 0.0       | 1. Pass value `0.0` to validator 2. Assert acceptance            | Value `0.0` is accepted as valid (lower bound inclusive)                        |
| `test_boundary_exactly_hundred`        | Boundary: value = 100.0                  | Test data or mock with value 100.0     | 1. Pass value `100.0` to validator 2. Assert acceptance          | Value `100.0` is accepted as valid (upper bound inclusive)                      |
| `test_null_value_accepted`             | Null handling                            | No-data scenario or mock               | 1. Pass `None`/`null` to validator 2. Assert acceptance          | `null` is accepted as a valid value (represents "not applicable" or "no data")  |
| `test_value_over_hundred_invalid`      | Negative: value > 100                    | Simulated/mock data with value 150.0   | 1. Pass value `150.0` to validator 2. Assert rejection           | Value flagged as invalid — exceeds maximum allowed range                        |
| `test_negative_value_invalid`          | Negative: value < 0                      | Simulated/mock data with value -10.0   | 1. Pass value `-10.0` to validator 2. Assert rejection           | Value flagged as invalid — below minimum allowed range                          |
| `test_wrong_type_string_invalid`       | Negative: string type                    | Simulated/mock data with value `"50%"` | 1. Pass string `"50%"` to validator 2. Assert rejection          | Value flagged as invalid — string type is not accepted                          |
| `test_wrong_type_boolean_invalid`      | Negative: boolean type                   | Simulated/mock data with value `true`  | 1. Pass boolean `True` to validator 2. Assert rejection          | Value flagged as invalid — boolean type is not accepted                         |
| `test_field_completely_missing`        | Negative: field absent under both names  | Simulated response with no field       | 1. Construct a mock response without either field name variant 2. Check both keys | Flagged as a defect — test failure indicates a bug in the API response          |
| `test_integer_value_accepted`          | Integer within range                     | Value like `50` (not `50.0`)           | 1. Pass integer `50` to validator 2. Assert acceptance           | Value `50` (integer) is accepted — both `int` and `float` types are valid      |

---

## 5. Test Execution Strategy

### 5.1 Test Markers and Selective Execution

The following custom pytest markers are defined in `pytest.ini` and can be used to selectively execute subsets of the test suite:

| Marker                                   | Purpose                                                            |
|------------------------------------------|--------------------------------------------------------------------|
| `@pytest.mark.requires_active_run`       | Skip tests that require a live in-progress code generation run     |
| `@pytest.mark.runs_metering`             | Tests targeting the `GET /runs/metering` endpoint                  |
| `@pytest.mark.runs_metering_current`     | Tests targeting the `GET /runs/metering/current` endpoint          |
| `@pytest.mark.project`                   | Tests targeting the `GET /project` endpoint                        |
| `@pytest.mark.cross_api`                 | Cross-API consistency tests spanning all three endpoints           |
| `@pytest.mark.edge_cases`               | Boundary condition and negative scenario tests                     |

### 5.2 Execution Commands

Standard test execution patterns for different scenarios:

```bash
# Run the full test suite
pytest

# Run tests for a specific endpoint
pytest -m runs_metering
pytest -m runs_metering_current
pytest -m project

# Run edge case and boundary tests only
pytest -m edge_cases

# Run cross-API consistency tests only
pytest -m cross_api

# Skip tests that require an active in-progress run
pytest -m "not requires_active_run"

# Generate an HTML report for QA review
pytest --html=report.html --self-contained-html

# Verbose output with short tracebacks
pytest -v --tb=short

# Run a specific test file
pytest tests/test_runs_metering.py -v

# Combine markers (e.g., edge cases excluding active run tests)
pytest -m "edge_cases and not requires_active_run"
```

### 5.3 Environment Prerequisites

Before executing the test suite, ensure the following prerequisites are satisfied:

1. **Environment Configuration**: A valid `.env` file (based on `.env.example`) must be present with all required variables populated:
   - `BASE_URL` — Blitzy Platform API base URL
   - `API_TOKEN` — Valid bearer authentication token
   - `TEST_PROJECT_ID` — Project ID with existing code generation run history
   - `TEST_RUN_ID` — Specific run ID for targeted metering tests

2. **Network Access**: The test execution environment must have network connectivity to the Blitzy Platform API endpoints.

3. **Authentication**: The `API_TOKEN` must be a valid, non-expired bearer token with sufficient permissions to read project data, run history, and metering metrics.

4. **Test Data**: At least one project with code generation run history must exist. The project should have at least one completed run for range validation tests.

5. **Active Run (Optional)**: An active in-progress code generation run is required only for tests marked with `@pytest.mark.requires_active_run`. If no active run exists, these tests are automatically skipped.

### 5.4 Expected Test Results by Scenario

| Scenario                                       | Expected Outcome                                                                             |
|------------------------------------------------|----------------------------------------------------------------------------------------------|
| All APIs return `percent_complete` correctly   | All tests pass (green)                                                                       |
| One API missing the field                      | Cross-API consistency test fails; the corresponding endpoint-specific presence test fails     |
| Field present but wrong type                   | Type validation tests fail for the affected endpoint(s)                                      |
| Value out of range (>100 or <0)                | Range validation tests fail for the affected endpoint(s)                                     |
| No active code generation run                  | `requires_active_run` tests are skipped (not failed); all other tests execute normally        |
| Missing or expired authentication credentials  | All API-calling tests are skipped with a descriptive message indicating missing configuration |
| Network connectivity failure                   | Tests fail with connection error; descriptive error message identifies the connectivity issue |

---

## 6. Validation Matrix

This matrix is derived from the user-defined validation scenarios and maps each expected platform state to the corresponding test function that verifies it.

| Scenario         | Expected Value            | Validating Test Function                   | Test File                              |
|------------------|---------------------------|--------------------------------------------|----------------------------------------|
| Completed run    | Value between 0–100       | `test_percent_complete_value_range`        | `test_runs_metering.py`, `test_project.py` |
| In-progress run  | Likely less than 100      | `test_active_run_less_than_hundred`        | `test_runs_metering_current.py`        |
| No data          | `null`                    | `test_null_value_accepted`                 | `test_edge_cases.py`                   |
| Field missing    | Bug — test failure        | `test_percent_complete_field_present`      | `test_runs_metering.py`, `test_runs_metering_current.py`, `test_project.py` |

---

## 7. Field Naming Convention Reference

The `percent_complete` field may appear under two naming conventions depending on the API endpoint and its serialization layer:

| Convention    | Field Name          | Context                                          |
|---------------|---------------------|--------------------------------------------------|
| snake_case    | `percent_complete`  | Typical Python/backend API convention             |
| camelCase     | `percentComplete`   | Typical JavaScript/frontend API convention        |

### Naming Convention Rules

- **Both conventions are valid**: Tests accept either `percent_complete` or `percentComplete` as the field name. The validation logic checks for the presence of at least one variant.
- **Absence of both is a defect**: If neither `percent_complete` nor `percentComplete` is found in a response, this is treated as a bug and the corresponding test will fail.
- **Different endpoints may use different conventions**: It is acceptable for `GET /runs/metering` to use snake_case while `GET /project` uses camelCase (or vice versa). This cross-endpoint naming variance is **not** considered a bug.
- **Naming consistency within an endpoint**: Each individual endpoint should consistently use the same naming convention across all responses. Inconsistency within the same endpoint across different calls would be a concern.

### Implementation Reference

The `src/validators.py` module provides a `validate_field_presence` function that checks for both naming conventions:

```
validate_field_presence(response_data, ["percent_complete", "percentComplete"])
```

This function returns the found field name and value, enabling downstream validators to operate on the correct key regardless of the convention used.

---

## 8. Document Validation Checklist

Use this checklist to verify the completeness and accuracy of this test plan before each release cycle:

- [ ] All 5 requirements (R-001 through R-005) are mapped to specific test functions in Section 2
- [ ] All 5 test files are documented with their individual test cases in Sections 3.2 and 4
- [ ] All test functions have clear preconditions, steps, and expected results in Section 4
- [ ] Pytest markers are documented in Section 5.1 and match the `pytest.ini` configuration
- [ ] Execution commands in Section 5.2 are syntactically correct and cover all common scenarios
- [ ] The validation matrix from user requirements is included in Section 6
- [ ] Field naming convention rules from the feature specification are documented in Section 7
- [ ] The document uses consistent Markdown formatting throughout all sections
- [ ] No hardcoded URLs, authentication tokens, or project IDs appear anywhere in this document
- [ ] Cross-references to test files match the actual file names in the project structure

---

## Appendix A: Data Flow Context

The `percent_complete` field follows this data flow path through the Blitzy Platform:

1. **Code Generation Pipeline** — Computes progress as `current_index / total_steps` during document section processing (indices 0–8).
2. **Pub/Sub IN_PROGRESS Notifications** — Publishes progress updates containing `current_index` and `total_steps` fields.
3. **Platform Data Layer** — Receives notifications, computes and stores the `percent_complete` percentage value.
4. **Platform API Layer** — Surfaces the stored value through the three target REST API endpoints.
5. **Test Suite** — Validates field presence, type correctness, and value range constraints via authenticated HTTP GET requests.

## Appendix B: Manual QA Verification Reference

For manual verification complementing the automated test suite, QA engineers can use browser DevTools to inspect API responses directly:

1. **Open DevTools** — Press `F12` or `Ctrl+Shift+I` in the browser.
2. **Navigate to Network Tab** — Select the "Network" tab and enable the "XHR/Fetch" filter.
3. **Enable Preserve Log** — Check "Preserve log" to retain requests across page navigations.
4. **Trigger API Calls** — Perform actions that trigger the target APIs:
   - Open a project page → triggers `GET /project`
   - View run history or metering dashboard → triggers `GET /runs/metering`
   - Start or view an active code generation run → triggers `GET /runs/metering/current`
5. **Inspect Responses** — Click on the relevant request, open the "Response" or "Preview" tab, and search for `percent_complete` or `percentComplete`.
6. **Validate** — Confirm the field is present, the value is numeric (0–100) or null, and the field is consistent across all inspected endpoints.
