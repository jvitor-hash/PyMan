# Testing Documentation

#filename
src/.docs/TESTING.md

#date of last update of the docs
2026-09-07

#date of creation
2026-09-07

#summary
Overview of the test suite structure and how to run tests.

#description
The project uses pytest with pytest-asyncio for testing async components.

**Test Structure:**
- Tests located in `src/tests/`
- Uses conftest.py for pytest configuration (asyncio_mode = "auto")
- Mock objects simulate Textual widgets and httpx responses

**Test Files:**

1. **test_APIClient_id.py** (8 tests)
   - Tests for make_request (URL validation, response handling, error cases)
   - Tests for extract_and_render_cookies (cookie saving/skipping)
   - Test for _run_script_awaitable wrapper

2. **test_ScriptOrchestration_id.py** (11 tests)
   - Script parsing (syntax errors, valid scripts)
   - Sandbox globals (builtins restriction, response data)
   - Script execution (output, errors, import blocking)

3. **test_RouteStorage_id.py** (6 tests)
   - Route creation, updates, and validation
   - File persistence (save/load)
   - Error handling

4. **test_RenderCookiesList_id.py** (9 tests)
   - Cookie list rendering
   - Widget ID sanitization
   - Cookie identity preservation

**Running Tests:**
```bash
./.venv/bin/python -m pytest src/tests/ -v
```

**Configuration (pyproject.toml):**
```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
testpaths = ["src/tests"]
pythonpath = ["src"]
```

**Current Status:** 54 tests passing, 0 failing

**Test files (7 total):**

1. **test_APIClient_id.py** (10 tests) - Includes 2 new tests for UI row creation via `_append_route_row`
2. **test_ScriptOrchestration_id.py** (11 tests)
3. **test_RouteStorage_id.py** (8 tests) - Includes 2 new tests for `_append_route_row` and NoMatches handling
4. **test_RenderCookiesList_id.py** (9 tests)
5. **test_component_integration.py** (6 tests) - Integration tests for full lifecycle, persistence, cookie deletion
6. **test_cookie_integration.py** (10 tests) - Cookie rendering and deletion tests including ancestor traversal verification

**New tests added:**
- `test_make_request_appends_ui_row_for_new_route` - Verifies UI row is appended for new routes
- `test_make_request_does_not_create_duplicate_row_for_existing_route` - Verifies no duplicate rows
- `test_save_current_route_updates_label_with_no_matches_path` - Verifies NoMatches exception handling
- `test_append_route_row_creates_list_item` - Verifies shared UI row helper
- `test_cookie_deletion_uses_ancestor_traversal` - Verifies ancestor-based cookie deletion
