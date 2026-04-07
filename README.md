# Blitzy Platform API Test Suite — percent_complete Field Validation

Automated API response test coverage that verifies the **presence**, **type**, and **value constraints** of the `percent_complete` (or `percentComplete`) field across three Blitzy Platform API endpoints related to code generation run metering and project data.

## Target Endpoints

| Endpoint | Description |
|---|---|
| `GET /runs/metering?projectId={id}` | Retrieves metering data for multiple code generation runs associated with a project |
| `GET /runs/metering/current` | Returns metering data for the currently active (in-progress) code generation run |
| `GET /project?id={id}` | Returns project details with inline metering data embedded |

---

## Requirements Covered

| Requirement | Description | Validated By |
|---|---|---|
| R-001 | **Field Presence Validation** — Verify that `percent_complete` or `percentComplete` is present in the JSON response of all three target endpoints | `test_runs_metering.py`, `test_runs_metering_current.py`, `test_project.py` |
| R-002 | **Data Type Validation** — Confirm the field value is numeric (`float` or `int`) or explicitly `null`; never a string, boolean, or other non-numeric type | `test_runs_metering.py`, `test_runs_metering_current.py`, `test_project.py`, `test_edge_cases.py` |
| R-003 | **Value Range Validation** — Assert that when the value is not `null`, it falls within the inclusive range `0.0` to `100.0` | `test_runs_metering.py`, `test_runs_metering_current.py`, `test_project.py`, `test_edge_cases.py` |
| R-004 | **Cross-API Consistency** — Ensure the field is consistently present across all three APIs for the same project/run context | `test_cross_api_consistency.py` |
| R-005 | **Edge Case Coverage** — Validate negative scenarios including values exceeding 100, values below 0, wrong data types, and field name mismatches | `test_edge_cases.py` |

---

## Project Structure

```
├── README.md
├── requirements.txt
├── pytest.ini
├── .env.example
├── config/
│   └── settings.yaml
├── src/
│   ├── __init__.py
│   ├── config.py
│   ├── api_client.py
│   ├── validators.py
│   └── models.py
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_runs_metering.py
│   ├── test_runs_metering_current.py
│   ├── test_project.py
│   ├── test_cross_api_consistency.py
│   └── test_edge_cases.py
└── docs/
    ├── test_plan.md
    └── api_contracts.md
```

### Module Descriptions

| Module | Purpose |
|---|---|
| `src/config.py` | Configuration management using Pydantic and `python-dotenv` for environment-based settings |
| `src/api_client.py` | HTTP client wrapper with methods for each target endpoint, authentication header injection, and response parsing |
| `src/validators.py` | Validation functions for `percent_complete` field presence, type checking, range enforcement, and null acceptance |
| `src/models.py` | Pydantic response models defining the expected schema for metering and project API responses |
| `tests/conftest.py` | Shared pytest fixtures providing API client instances, authentication tokens, and test identifiers |
| `config/settings.yaml` | Endpoint path definitions, field name variants, and validation parameter defaults |
| `docs/test_plan.md` | Formal test plan mapping each requirement to specific test cases with expected outcomes |
| `docs/api_contracts.md` | API response contract documentation with sample JSON structures for each endpoint |

---

## Prerequisites

- **Python 3.10+** (tested with Python 3.12)
- **pip** package manager
- Access to the **Blitzy Platform API** with valid authentication credentials
- At least one project with **code generation run history** (completed or in-progress runs)

---

## Setup Instructions

### 1. Clone the Repository

```bash
git clone <repository-url>
cd <repository-directory>
```

### 2. Create and Activate a Virtual Environment

```bash
python -m venv venv
source venv/bin/activate
```

On Windows:

```bash
python -m venv venv
venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables

Copy the example environment file and fill in your values:

```bash
cp .env.example .env
```

Edit the `.env` file with your configuration:

| Variable | Description | Example |
|---|---|---|
| `BASE_URL` | Platform API base URL | `https://api.blitzy.com` |
| `API_TOKEN` | Bearer authentication token | *(your token)* |
| `TEST_PROJECT_ID` | Project ID with existing code generation runs | *(your project ID)* |
| `TEST_RUN_ID` | Specific run ID for targeted metering tests | *(your run ID)* |

> **Important:** Never commit your `.env` file to version control. The `.env.example` file serves as a template with placeholder values only.

---

## Running Tests

### Full Test Suite

```bash
pytest
```

### Specific Endpoint Tests

```bash
pytest tests/test_runs_metering.py
pytest tests/test_runs_metering_current.py
pytest tests/test_project.py
```

### Verbose Output

```bash
pytest -v
```

### Generate HTML Report

```bash
pytest --html=report.html --self-contained-html
```

### Skip Tests Requiring an Active Run

Some tests validate the `GET /runs/metering/current` endpoint, which requires a code generation run to be actively in progress. To skip these tests when no active run is available:

```bash
pytest -m "not requires_active_run"
```

### Run with Timeout Enforcement

```bash
pytest --timeout=30
```

---

## Test Categories

### Endpoint-Specific Tests

Each endpoint has a dedicated test module that validates the `percent_complete` field:

| Test Module | Endpoint | Validations |
|---|---|---|
| `test_runs_metering.py` | `GET /runs/metering` | Field presence, numeric type, value range 0–100, null acceptance, field naming convention |
| `test_runs_metering_current.py` | `GET /runs/metering/current` | Field presence, live run value expectations, null for no active run |
| `test_project.py` | `GET /project` | Field presence within nested metering block, type and range validation |

### Cross-API Consistency Tests

The `test_cross_api_consistency.py` module verifies that the `percent_complete` field behaves consistently across all three endpoints for the same project and run context. If the field is present in one endpoint but missing in another, the test flags this as a defect.

### Edge Case and Boundary Tests

The `test_edge_cases.py` module covers:

| Scenario | Expected Result |
|---|---|
| Value is exactly `0.0` | Valid — lower boundary |
| Value is exactly `100.0` | Valid — upper boundary |
| Value is `null` | Valid — represents no data or not applicable |
| Value exceeds `100.0` | Invalid — test fails |
| Value is below `0.0` (negative) | Invalid — test fails |
| Value is a string (e.g., `"50"`) | Invalid — test fails |
| Value is a boolean | Invalid — test fails |
| Field is completely absent | Invalid — test fails (bug detected) |
| Integer value within range (e.g., `50`) | Valid — both int and float are accepted |

---

## Manual QA Verification (DevTools Reference)

For supplementary manual verification alongside the automated test suite, use the browser DevTools Network tab to inspect API responses directly:

### Step-by-Step Procedure

1. **Open DevTools** — Press `F12` or `Ctrl+Shift+I` (Windows/Linux) / `Cmd+Option+I` (macOS)
2. **Navigate to the Network tab**
3. **Enable filters** — Select the **XHR/Fetch** filter and enable **Preserve Log** to capture API calls across page navigations
4. **Filter requests** — Use the search bar to filter by `metering`, `runs`, or `project`
5. **Trigger API calls** — Perform one or more of the following actions in the Blitzy Platform UI:
   - Open a project page
   - Start or view a code generation run
   - Refresh the project dashboard
   - Check the run progress or details page
6. **Inspect the response** — Click a matching request, then open the **Response** or **Preview** tab
7. **Search for the field** — Look for `percent_complete` or `percentComplete` in the response JSON

### Expected Results

| Scenario | Expected Value |
|---|---|
| Completed run | Numeric value between `0` and `100` (typically `100`) |
| In-progress run | Numeric value less than `100` |
| No data available | `null` |
| Field missing entirely | **Bug** — should be reported as a defect |

---

## Configuration

The test suite is configured through three layers:

### Environment Variables (`.env`)

Primary runtime configuration loaded via `python-dotenv`. See the [Setup Instructions](#4-configure-environment-variables) section for the full list of required variables.

### Feature Settings (`config/settings.yaml`)

Defines endpoint paths, accepted field name variants, and validation parameters:

- **Endpoint paths** — URL path segments for each of the three target APIs
- **Field name variants** — Both `percent_complete` and `percentComplete` are configured as accepted field names
- **Validation parameters** — Minimum value (`0.0`), maximum value (`100.0`), accepted types

### Test Framework Settings (`pytest.ini`)

Configures pytest behavior including:

- Test discovery patterns
- Custom markers (e.g., `requires_active_run`)
- Default timeout values
- Output formatting and report generation

---

## Field Naming Convention Note

> **Both `percent_complete` (snake_case) and `percentComplete` (camelCase) are accepted as valid field names.**

Different API endpoints or serialization layers within the Blitzy Platform may use different naming conventions. The test suite accounts for this by checking for both variants:

- If an endpoint returns `percent_complete` — **valid**
- If an endpoint returns `percentComplete` — **valid**
- If one endpoint uses snake_case and another uses camelCase — **valid** (not a bug)
- If the field is **absent under both names** — **invalid** (this is a bug and the test will fail)

The validation logic in `src/validators.py` and the test assertions are designed to accept either naming convention transparently.

---

## License

*License information for this project will be specified here once determined by the project maintainers.*
