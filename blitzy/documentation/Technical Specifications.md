# Technical Specification

# 0. Agent Action Plan

## 0.1 Executive Summary

Based on the bug description, the Blitzy platform understands that the bug is a **missing type-safety guard in the `_get_metering_block()` helper function** within `tests/test_project.py` of the Blitzy Platform API Test Suite. This function extracts the nested metering data object from `GET /project` API responses but returns the raw value at the metering key without validating that it is a `dict`. When the Blitzy Platform API returns a response where the metering key exists but its value is `None` (JSON `null`) or a non-dict type (e.g., a string), the function returns that non-dict value to its callers, causing downstream test functions to crash with unhelpful `TypeError` or `AttributeError` exceptions instead of clean, descriptive `AssertionError` messages.

The user's requirement specifies verifying that three existing Blitzy Platform API endpoints — `GET /runs/metering`, `GET /runs/metering/current`, and `GET /project` — include a `percent_complete` (or `percentComplete`) field with a numeric value between `0.0` and `100.0`, or `null`. The test suite at `tests/test_project.py` is the validation layer for the `GET /project` endpoint, and the `_get_metering_block()` function is the critical extraction point where the nested metering block is located before field-level validation proceeds. The bug manifests when the API returns a structurally unexpected metering block (specifically `null`), causing two of seven `GET /project` tests to produce undiagnosable `TypeError` crashes rather than actionable test failure messages.

### 0.1.1 Technical Failure Classification

- **Error Type**: Missing input validation / type-safety guard in test helper function
- **Failure Mode**: `TypeError: argument of type 'NoneType' is not iterable` and `AttributeError: 'str' object has no attribute 'keys'`
- **Affected Component**: `tests/test_project.py`, function `_get_metering_block()` at lines 85–118
- **Affected Tests**: `test_percent_complete_present_in_project_metering` (line 185) and `test_percent_complete_not_at_top_level` (line 216)
- **Severity**: Medium — causes confusing test output that obscures real API defects, violating the suite's design principle of descriptive failure messages

### 0.1.2 Reproduction Summary

The bug can be reproduced by passing a response dictionary where the metering key exists but its value is not a `dict`:

- `_get_metering_block({"metering": None})` returns `None` instead of raising an `AssertionError`
- `_get_metering_block({"metering": "loading"})` returns `"loading"` instead of raising an `AssertionError`
- Subsequent calls to `validate_field_presence(None, ...)` crash with `TypeError`
- Subsequent calls to `any(field in None for field in ...)` crash with `TypeError`

## 0.2 Root Cause Identification

Based on exhaustive repository analysis, THE root cause is: **the `_get_metering_block()` helper function in `tests/test_project.py` (lines 85–118) returns the raw value at a metering key without asserting that the value is a `dict`**, allowing `None`, strings, lists, and other non-dict types to propagate unchecked to downstream test assertions that assume dict-like behavior.

### 0.2.1 Primary Root Cause — Missing Type Guard

- **Located in**: `tests/test_project.py`, lines 109–111
- **Triggered by**: `GET /project` API responses where a recognized metering key (`metering`, `meteringData`, or `metering_data`) exists but maps to a value that is not a `dict` — most critically, `null` (`None` in Python)
- **Evidence**: Direct code examination of the function's `for` loop at lines 109–111:

```python
for key_name in METERING_BLOCK_KEY_NAMES:
    if key_name in response_data:
        return response_data[key_name]
```

The `if key_name in response_data` check confirms the key exists, but performs zero validation on the value at `response_data[key_name]` before returning it. The function's docstring (line 99) declares the return type as `Dict[str, Any]`, but the implementation does not enforce this contract.

- **This conclusion is definitive because**: The function has exactly one `return` statement (line 111) and one `raise` path (lines 114–118). The `raise` path only fires when no metering key is found at all. When a metering key IS found but maps to `None`, the `return` at line 111 returns `None` unconditionally. There is no type check anywhere between the key-existence check and the return statement.

### 0.2.2 Downstream Impact — Vulnerable Call Sites

Two test functions call `_get_metering_block()` and use the returned value without an `isinstance(metering_data, dict)` guard:

**Vulnerable Call Site 1** — `test_percent_complete_present_in_project_metering` (line 200):

```python
metering_data = _get_metering_block(response)
found_field = validate_field_presence(metering_data, ...)
```

When `metering_data` is `None`, `validate_field_presence()` in `src/validators.py` executes `any(field in data for field in names)`, which raises `TypeError: argument of type 'NoneType' is not iterable`.

**Vulnerable Call Site 2** — `test_percent_complete_not_at_top_level` (lines 246–248 and 260–262):

```python
metering_data = _get_metering_block(response)
metering_field_found = any(
    field_name in metering_data
    for field_name in PERCENT_COMPLETE_FIELD_NAMES
)
```

When `metering_data` is `None`, the `in` operator raises the same `TypeError`. When `metering_data` is a string (e.g., `"loading"`), `in` performs substring matching instead of key lookup, producing incorrect boolean results rather than a crash.

### 0.2.3 Contrast with Safe Call Sites

Five other test functions in the same file ARE protected because they include an explicit `isinstance` guard immediately after calling `_get_metering_block()`:

- `test_percent_complete_type_in_project` — line 296: `assert isinstance(metering_data, dict)`
- `test_percent_complete_range_in_project` — line 334: `assert isinstance(metering_data, dict)`
- `test_percent_complete_null_acceptance_in_project` — has a similar guard after the call
- `test_metering_block_structure` — validates type before accessing keys
- `test_metering_block_additional_fields` — validates type before accessing keys

This inconsistency confirms that the type guard was intended but was omitted from the two vulnerable call sites. The correct fix is to centralize the guard inside `_get_metering_block()` itself so all callers are automatically protected.

### 0.2.4 Root Cause Classification

| Attribute | Value |
|-----------|-------|
| Category | Missing input validation |
| Defect type | Type-safety gap in test helper |
| Trigger condition | `GET /project` returns `{"metering": null}` |
| Failure mode | Unhandled `TypeError` / `AttributeError` |
| Crash location | Caller-side — lines 202, 248, 262 |
| Defect origin | `_get_metering_block()` — line 111 |
| Number of affected tests | 2 out of 7 `GET /project` tests |
| Severity | Medium — confuses debugging, masks real API defects |

## 0.3 Diagnostic Execution

### 0.3.1 Code Examination Results

- **File analyzed**: `tests/test_project.py`
- **Problematic code block**: Lines 109–111 (`_get_metering_block` return path)
- **Specific failure point**: Line 111, the `return response_data[key_name]` statement
- **Execution flow leading to bug**:
  - Step 1: A `GET /project` test function calls `api_client.get_project(test_project_id)`, receiving a JSON response parsed as a Python `dict`
  - Step 2: The test function calls `_get_metering_block(response)` to extract the nested metering sub-object
  - Step 3: `_get_metering_block` iterates over `METERING_BLOCK_KEY_NAMES` (`["metering", "meteringData", "metering_data"]`) at line 109
  - Step 4: The key `"metering"` is found in `response_data` (line 110 evaluates to `True`)
  - Step 5: Line 111 returns `response_data["metering"]` which is `None` — no type check occurs
  - Step 6: The caller receives `None` where it expects a `dict`
  - Step 7: The caller passes `None` to `validate_field_presence()` or uses `None` directly in an `any(field_name in None ...)` expression
  - Step 8: Python raises `TypeError: argument of type 'NoneType' is not iterable`

### 0.3.2 Repository File Analysis Findings

| Tool Used | Command/Action Executed | Finding | File:Line |
|-----------|------------------------|---------|-----------|
| read_file | `tests/test_project.py` lines 85–118 | `_get_metering_block()` has no type validation on return value | `tests/test_project.py:111` |
| read_file | `tests/test_project.py` lines 185–212 | `test_percent_complete_present_in_project_metering` passes raw return to `validate_field_presence` without `isinstance` guard | `tests/test_project.py:200-202` |
| read_file | `tests/test_project.py` lines 216–270 | `test_percent_complete_not_at_top_level` uses `in` operator on raw return at two sites without `isinstance` guard | `tests/test_project.py:246-248, 260-262` |
| read_file | `tests/test_project.py` lines 279–299 | `test_percent_complete_type_in_project` has `isinstance` guard at line 296 — SAFE | `tests/test_project.py:296` |
| read_file | `tests/test_project.py` lines 318–346 | `test_percent_complete_range_in_project` has `isinstance` guard at line 334 — SAFE | `tests/test_project.py:334` |
| read_file | `src/validators.py` lines 70–130 | `validate_field_presence` uses `any(field in data ...)` which crashes on `None` input | `src/validators.py:~155` |
| bash | `python3 -c "from tests.test_project import _get_metering_block; r = _get_metering_block({'metering': None}); print(type(r))"` | Returns `NoneType` — confirms no type guard | `tests/test_project.py:111` |
| bash | `python3 -c "from src.validators import validate_field_presence, PERCENT_COMPLETE_FIELD_NAMES; validate_field_presence(None, PERCENT_COMPLETE_FIELD_NAMES, 'test')"` | Raises `TypeError: argument of type 'NoneType' is not iterable` | `src/validators.py` |
| bash | `python3 -c "from tests.test_project import _get_metering_block; r = _get_metering_block({'metering': 'loading'}); print(type(r), repr(r))"` | Returns `str 'loading'` — non-dict accepted silently | `tests/test_project.py:111` |
| bash | `cd /tmp/blitzy/6thaprilone/main_0d6e40 && python3 -m pytest -v --tb=short --timeout=30 --no-header` | 102 passed, 35 skipped — all unit tests pass, integration tests skip due to missing env vars | Full suite |
| grep (via bash) | `grep -n "isinstance.*metering_data.*dict" tests/test_project.py` | Found guards at lines 296, 334, and in later tests — confirms inconsistent protection pattern | `tests/test_project.py:296,334` |
| grep (via bash) | `grep -n "_get_metering_block" tests/test_project.py` | 7 call sites total: lines 200, 246, 260, 294, 332, 379, and others | `tests/test_project.py` |

### 0.3.3 Fix Verification Analysis

- **Steps followed to reproduce bug**:
  - Imported `_get_metering_block` from `tests.test_project` in an interactive Python session
  - Called `_get_metering_block({"metering": None})` — returned `None` (confirmed bug)
  - Called `_get_metering_block({"metering": "loading"})` — returned `"loading"` (confirmed bug)
  - Passed `None` result to `validate_field_presence()` — `TypeError` raised (confirmed crash)
  - Passed `None` result to `any(field in None for field in ...)` — `TypeError` raised (confirmed crash)

- **Confirmation tests to ensure the fix works**:
  - After applying the fix, `_get_metering_block({"metering": None})` must raise `AssertionError` with a message describing that the metering block is not a `dict`
  - After applying the fix, `_get_metering_block({"metering": "loading"})` must raise `AssertionError`
  - After applying the fix, `_get_metering_block({"metering": {"percent_complete": 50.0}})` must still return the `dict` successfully (no regression)
  - The full test suite (`python3 -m pytest -v --tb=short --timeout=30`) must continue showing 102 passed, 35 skipped

- **Boundary conditions and edge cases covered**:
  - `None` value at metering key (primary trigger)
  - String value at metering key
  - List value at metering key (e.g., `{"metering": [1, 2]}`)
  - Boolean value at metering key (e.g., `{"metering": True}`)
  - Integer value at metering key (e.g., `{"metering": 42}`)
  - Empty dict at metering key (valid — should return `{}`)
  - Normal dict at metering key (valid — should return the dict)

- **Verification confidence level**: **95%** — The bug is deterministically reproducible and the fix is a straightforward type assertion. The 5% uncertainty accounts for potential edge cases in integration test scenarios where the API might return entirely unexpected structures not covered by the current test data.

## 0.4 Bug Fix Specification

### 0.4.1 The Definitive Fix

- **File to modify**: `tests/test_project.py`
- **Current implementation at lines 109–111**:

```python
for key_name in METERING_BLOCK_KEY_NAMES:
    if key_name in response_data:
        return response_data[key_name]
```

- **Required change at lines 109–111** — replace the 3-line block with a 9-line block that adds an `isinstance` type guard before returning the value:

```python
for key_name in METERING_BLOCK_KEY_NAMES:
    if key_name in response_data:
        value = response_data[key_name]
        assert isinstance(value, dict), (
            f"[{_ENDPOINT}] metering block under key "
            f"'{key_name}' must be a dict, "
            f"got {type(value).__name__}: {value!r}"
        )
        return value
```

- **This fixes the root cause by**: Intercepting non-dict values at the extraction point before they propagate to callers. When the API returns `{"metering": null}`, the function now raises a descriptive `AssertionError` stating that the metering block under key `'metering'` must be a `dict` but got `NoneType: None`, instead of allowing `None` to flow through and cause a confusing `TypeError` at a downstream call site. The assertion message follows the existing convention used throughout the file: `[GET /project]` prefix, field identification, and actual-vs-expected value reporting.

### 0.4.2 Change Instructions

- **MODIFY** `tests/test_project.py` lines 109–111:
  - **FROM** (3 lines):
    ```python
        for key_name in METERING_BLOCK_KEY_NAMES:
            if key_name in response_data:
                return response_data[key_name]
    ```
  - **TO** (9 lines):
    ```python
        for key_name in METERING_BLOCK_KEY_NAMES:
            if key_name in response_data:
                # Guard: ensure the value under the metering key is a dict.
                # Without this check, None or non-dict values propagate to
                # callers, causing TypeError/AttributeError instead of
                # descriptive AssertionError messages.
                value = response_data[key_name]
                assert isinstance(value, dict), (
                    f"[{_ENDPOINT}] metering block under key "
                    f"'{key_name}' must be a dict, "
                    f"got {type(value).__name__}: {value!r}"
                )
                return value
    ```

- **No other lines in this file require modification**. The existing `isinstance` guards in the 5 safe callers (lines 296, 334, etc.) become redundant but are harmless and should be left in place as defense-in-depth.
- **No other files require modification**. The bug is entirely contained within `_get_metering_block()` in `tests/test_project.py`.

### 0.4.3 Fix Validation

- **Test command to verify fix**:
  ```
  cd /tmp/blitzy/6thaprilone/main_0d6e40 && CI=true python3 -m pytest -v --tb=short --timeout=30 --no-header
  ```
- **Expected output after fix**: `102 passed, 35 skipped` — identical to the current baseline (the fix only changes the error path, not the success path, so no existing passing test is affected)
- **Confirmation method**:
  - Run the interactive reproduction scenario post-fix:
    ```python
    from tests.test_project import _get_metering_block
    try:
        _get_metering_block({"metering": None})
    except AssertionError as e:
        print("PASS:", e)
    ```
  - Expected: `AssertionError` with message containing `must be a dict, got NoneType`
  - Run with string value:
    ```python
    try:
        _get_metering_block({"metering": "loading"})
    except AssertionError as e:
        print("PASS:", e)
    ```
  - Expected: `AssertionError` with message containing `must be a dict, got str`
  - Run with valid dict (regression check):
    ```python
    result = _get_metering_block({"metering": {"percent_complete": 50.0}})
    assert result == {"percent_complete": 50.0}
    print("PASS: valid dict returned correctly")
    ```
  - Expected: Returns the dict without error

### 0.4.4 Design Rationale

The fix is placed inside `_get_metering_block()` rather than at each call site for the following reasons:

- **Centralization**: All 7 callers are protected by a single code change, eliminating the need to patch each test function individually
- **Contract enforcement**: The function's docstring declares `Returns Dict[str, Any]` — the assertion makes the implementation honor this contract
- **Consistency**: The assertion message follows the `[GET /project]` prefix convention already used in every other assertion in the file (per the module docstring at line 35)
- **Minimality**: The fix adds 6 net new lines (9 replacement lines minus 3 original lines), all within a single function, with zero changes to any other file

## 0.5 Scope Boundaries

### 0.5.1 Changes Required (Exhaustive List)

| Action | File Path | Lines | Specific Change |
|--------|-----------|-------|-----------------|
| MODIFIED | `tests/test_project.py` | 109–111 | Replace 3-line unconditional return with 9-line guarded return including `isinstance(value, dict)` assertion |

**Total files affected**: 1
**Total lines changed**: 3 lines removed, 9 lines added (net +6 lines)
**No files are CREATED or DELETED.**

### 0.5.2 Explicitly Excluded

The following files and components are explicitly OUT OF SCOPE for this fix:

- **Do not modify**: `src/validators.py` — The `validate_field_presence()` function is not at fault; it correctly assumes dict-like input per its contract. The bug is in the caller that passes non-dict values.
- **Do not modify**: `src/api_client.py` — The API client correctly returns whatever the API sends; the test infrastructure must handle unexpected shapes.
- **Do not modify**: `src/models.py` — The Pydantic models are declarative validation for well-formed data; they are not involved in the test helper's extraction logic.
- **Do not modify**: `src/config.py` — Configuration loading has no bearing on this bug.
- **Do not modify**: `tests/conftest.py` — Shared fixtures are not involved in the metering block extraction.
- **Do not modify**: `tests/test_runs_metering.py` — The `_extract_metering_records()` helper in this file handles its own envelope shapes and is not affected.
- **Do not modify**: `tests/test_runs_metering_current.py` — This endpoint's response is a flat object; no nested extraction is involved.
- **Do not modify**: `tests/test_cross_api_consistency.py` — Cross-API tests have their own extraction helpers with appropriate guards.
- **Do not modify**: `tests/test_edge_cases.py` — Unit tests are self-contained with mock data; the bug is only in the integration test helper.
- **Do not modify**: `config/settings.yaml` — Configuration values are unrelated.
- **Do not modify**: `pytest.ini` — Test runner configuration is unrelated.
- **Do not modify**: `requirements.txt` — No dependency changes are needed.
- **Do not remove**: Existing `isinstance(metering_data, dict)` guards in the 5 safe test functions (lines 296, 334, etc.) — These become redundant after the fix but should be retained as defense-in-depth.
- **Do not add**: New test files, new source modules, or new configuration entries — The fix is a minimal correction to existing code.
- **Do not refactor**: The overall structure of `_get_metering_block()` or the `METERING_BLOCK_KEY_NAMES` iteration pattern — These are sound and should not be restructured as part of a bug fix.

## 0.6 Verification Protocol

### 0.6.1 Bug Elimination Confirmation

- **Execute the full test suite**:
  ```
  cd /tmp/blitzy/6thaprilone/main_0d6e40 && CI=true python3 -m pytest -v --tb=short --timeout=30 --no-header
  ```
- **Verify output matches**: `102 passed, 35 skipped` — identical to the pre-fix baseline. No test that currently passes should fail after the fix. No test that currently skips should change status.
- **Confirm the error path now produces an `AssertionError`**: Execute the following interactive reproduction after applying the fix:
  ```
  cd /tmp/blitzy/6thaprilone/main_0d6e40 && python3 -c "
  from tests.test_project import _get_metering_block
  # Test 1: None value should raise AssertionError
  try:
      _get_metering_block({'metering': None})
      print('FAIL: No exception raised for None')
  except AssertionError as e:
      assert 'must be a dict' in str(e)
      print('PASS: None value raises AssertionError')
  except TypeError:
      print('FAIL: TypeError still raised — fix not applied')
  # Test 2: String value should raise AssertionError
  try:
      _get_metering_block({'metering': 'loading'})
      print('FAIL: No exception raised for string')
  except AssertionError as e:
      assert 'must be a dict' in str(e)
      print('PASS: String value raises AssertionError')
  # Test 3: Valid dict should still work
  result = _get_metering_block({'metering': {'percent_complete': 50.0}})
  assert result == {'percent_complete': 50.0}
  print('PASS: Valid dict returned correctly')
  "
  ```
- **Expected output**: Three `PASS` lines confirming all three scenarios behave correctly.
- **Validate no unhandled exceptions remain**: Run a broader edge case sweep after applying the fix:
  ```
  cd /tmp/blitzy/6thaprilone/main_0d6e40 && python3 -c "
  from tests.test_project import _get_metering_block
  bad_values = [None, 'loading', 42, True, False, [1,2], 3.14]
  for val in bad_values:
      try:
          _get_metering_block({'metering': val})
          print(f'FAIL: {type(val).__name__} not caught')
      except AssertionError:
          print(f'PASS: {type(val).__name__} correctly rejected')
  # Valid cases
  for val in [{}, {'percent_complete': 0.0}, {'percentComplete': 100.0}]:
      result = _get_metering_block({'metering': val})
      assert isinstance(result, dict)
      print(f'PASS: valid dict {val} accepted')
  "
  ```

### 0.6.2 Regression Check

- **Run the existing test suite** (same command as above) to confirm all 102 unit tests continue passing. The 35 integration tests will continue to skip due to missing environment variables — this is expected and correct.
- **Verify unchanged behavior in the following features**:
  - `tests/test_runs_metering.py` — All 7 tests must maintain their current pass/skip status
  - `tests/test_runs_metering_current.py` — All 7 tests must maintain their current pass/skip status
  - `tests/test_cross_api_consistency.py` — All 7 tests must maintain their current pass/skip status
  - `tests/test_edge_cases.py` — All 109 tests must continue passing (these are pure unit tests unaffected by the change)
- **Confirm test execution time**: The fix adds a single `isinstance` check per invocation of `_get_metering_block()` — execution time delta should be imperceptible (sub-microsecond). Total suite time should remain under 1 second.
- **Verify no import or syntax errors**: Run a static compile check on the modified file:
  ```
  python3 -m py_compile tests/test_project.py && echo "Syntax OK"
  ```

## 0.7 Rules

### 0.7.1 Coding and Development Standards

The following rules are derived from the existing codebase conventions observed across all 21 files in the repository and must be strictly followed when implementing the fix:

- **Assertion message convention**: Every assertion in the test suite includes a descriptive message formatted as `f"[{_ENDPOINT}] <description> ... got {type(value).__name__}: {value!r}"`. The fix must follow this exact pattern, using the module-level `_ENDPOINT` constant (`"GET /project"`) as the prefix.
- **Docstring convention**: The codebase uses NumPy-style docstrings with `Parameters`, `Returns`, and `Raises` sections. If the docstring for `_get_metering_block()` is updated, it must follow this format. The existing `Raises` section at lines 102–107 already documents `AssertionError` for missing keys; the new type-check assertion should be noted there.
- **Type hint convention**: All functions in the codebase use PEP 484 type annotations. The return type of `_get_metering_block()` is already declared as `Dict[str, Any]` — the fix enforces this contract without changing the signature.
- **Import convention**: No new imports are required for this fix. The `isinstance` built-in is used extensively throughout the existing codebase.
- **Comment convention**: Inline comments in the codebase explain the "why" behind non-obvious logic. The fix should include a brief comment explaining why the type guard exists (to prevent `TypeError`/`AttributeError` at downstream call sites).

### 0.7.2 Bug Fix Discipline

- Make the exact specified change only — modify lines 109–111 of `tests/test_project.py` to add the `isinstance` guard
- Zero modifications outside the bug fix — no refactoring, no feature additions, no test restructuring
- Preserve all existing test behavior — 102 passed, 35 skipped must remain the outcome
- Do not alter the public API of `_get_metering_block()` — it must still accept `Dict[str, Any]` and return `Dict[str, Any]`
- Do not remove the redundant `isinstance` guards in the 5 safe caller functions — defense-in-depth is an explicit design choice in this codebase

### 0.7.3 Version Compatibility

- **Python**: The fix uses `isinstance()` and f-strings, both available since Python 3.6. The project targets Python 3.10+ (tested on 3.12.3). No compatibility concerns.
- **pytest**: The fix uses `assert` statements (not `pytest.raises`), consistent with the existing codebase pattern. Compatible with pytest ≥ 8.3.0 as specified in `requirements.txt`.
- **No new dependencies**: The fix requires no new packages, no version bumps, and no changes to `requirements.txt`.

### 0.7.4 Testing Standards

- Extensive testing must confirm the fix prevents regressions across all 137 test cases (102 unit + 35 integration)
- The fix must be validated against both the `None` trigger condition and at least 5 additional non-dict types (string, int, float, bool, list) to ensure comprehensive coverage
- All verification commands must use non-interactive flags (`--timeout=30`, `--no-header`, `CI=true`) to prevent hanging

## 0.8 References

### 0.8.1 Repository Files and Folders Searched

The following files and folders were exhaustively examined to derive the conclusions in this Agent Action Plan:

**Source Code (`src/`)**

| File Path | Purpose | Relevance to Bug |
|-----------|---------|-------------------|
| `src/config.py` | Settings management with Pydantic BaseModel | Reviewed — not involved in the bug |
| `src/api_client.py` | HTTP client with retry logic for 3 endpoints | Reviewed — returns raw API response; not at fault |
| `src/validators.py` | Imperative validation functions for `percent_complete` | Reviewed — `validate_field_presence()` is a downstream crash site but not the root cause |
| `src/models.py` | Pydantic v2 declarative models for response validation | Reviewed — not involved in the bug |

**Test Code (`tests/`)**

| File Path | Purpose | Relevance to Bug |
|-----------|---------|-------------------|
| `tests/conftest.py` | Shared pytest fixtures (session + function scope) | Reviewed — fixtures not involved |
| `tests/test_project.py` | Tests for `GET /project` endpoint — **contains the bug** | **Primary file** — `_get_metering_block()` at lines 85–118 |
| `tests/test_runs_metering.py` | Tests for `GET /runs/metering` endpoint | Reviewed — has its own `_extract_metering_records()` helper, not affected |
| `tests/test_runs_metering_current.py` | Tests for `GET /runs/metering/current` endpoint | Reviewed — flat response structure, no nested extraction |
| `tests/test_cross_api_consistency.py` | Cross-API consistency tests (R-004) | Reviewed — has its own extraction helpers with appropriate guards |
| `tests/test_edge_cases.py` | 109 unit tests for edge cases (R-005) | Reviewed — pure unit tests with mock data, not affected |

**Configuration and Documentation**

| File Path | Purpose | Relevance to Bug |
|-----------|---------|-------------------|
| `config/settings.yaml` | Endpoint paths, field names, validation constraints | Reviewed — configuration values confirmed correct |
| `pytest.ini` | Test runner configuration with custom markers | Reviewed — marker definitions confirmed correct |
| `requirements.txt` | PyPI dependency manifest (8 packages) | Reviewed — dependency versions confirmed compatible |
| `.env.example` | Environment variable template | Reviewed — integration test skip behavior confirmed |
| `README.md` | Project documentation and QA procedures | Reviewed — Python 3.10+ requirement confirmed |
| `docs/test_plan.md` | Detailed test plan covering 5 requirements | Reviewed — requirement mapping confirmed |
| `docs/api_reference.md` | API endpoint reference documentation | Reviewed — response structure expectations confirmed |

**Root-Level and Build Files**

| File Path | Purpose |
|-----------|---------|
| `.env.example` | Environment variable template |
| `blitzy/` | Blitzy platform metadata directory |

### 0.8.2 Technical Specification Sections Consulted

| Section | Key Insight |
|---------|-------------|
| 1.1 Executive Summary | Confirmed 137 total test cases (102 unit + 35 integration), Python 3.10+ target, dual-layer validation architecture |
| 3.1 Technology Stack Overview | Confirmed 8 PyPI dependencies, minimal footprint design, configuration-driven flexibility |
| 6.6 Testing Strategy | Confirmed comprehensive testing strategy with unit testing (109 tests in `test_edge_cases.py`), integration testing (35 tests across 4 modules), edge case coverage matrix |

### 0.8.3 Commands Executed for Diagnosis

| Command | Purpose | Key Result |
|---------|---------|------------|
| `find / -maxdepth 4 -name ".blitzyignore"` | Search for ignore files | None found |
| `pip install --break-system-packages -r requirements.txt` | Install project dependencies | All 8 packages installed successfully |
| `python3 -m pytest -v --tb=short --timeout=30 --no-header` | Run full test suite | 102 passed, 35 skipped, 0 failed |
| `python3 -c "from tests.test_project import _get_metering_block; ..."` | Reproduce bug with `None` value | Confirmed: returns `None`, causes `TypeError` downstream |
| `python3 -c "from tests.test_project import _get_metering_block; ..."` | Reproduce bug with string value | Confirmed: returns `"loading"`, causes `AttributeError` downstream |
| `grep -n "isinstance.*metering_data.*dict" tests/test_project.py` | Identify existing type guards | Found guards at lines 296, 334 — confirms inconsistent protection |
| `grep -n "_get_metering_block" tests/test_project.py` | Count all call sites | 7 call sites identified — 2 vulnerable, 5 safe |

### 0.8.4 Attachments

No attachments were provided for this project. No Figma URLs were specified.

