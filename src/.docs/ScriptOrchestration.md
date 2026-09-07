# ScriptOrchestration - Safe Script Execution

#filename
src/ScriptOrchestration.py
#test file
src/tests/test_ScriptOrchestration_id.py

#date of last update of the docs
2026-09-07

#date of creation
2026-09-07

#summary
Provides sandboxed Python script execution with restricted builtins for security.

#description
ScriptOrchestration enables users to execute Python scripts against HTTP responses in a secure sandbox:

- **_ALLOWLIST** - Frozen set of safe builtins (abs, all, any, bool, dict, etc.) - excludes dangerous ones like __import__

- **_make_sandbox_globals(response)** - Creates a restricted execution namespace:
  - Exposes response data (status_code, json_data, headers, cookies)
  - Provides only allowlisted builtins
  - Includes print() function for output capture

- **parse_script(self)** - Validates script syntax using ast.parse, updates status label

- **execute_script(self, response)** - Executes user script:
  - Checks for empty script
  - Runs script in sandbox with stdout capture
  - Reports success/failure with appropriate status messages
  - Handles exceptions safely

Security features:
- No __import__ available (blocks module imports)
- Only whitelisted builtins accessible
- Exceptions caught and reported, not propagated

#code
```python
_ALLOWLIST = frozenset({
    "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float",
    "format", "getattr", "hasattr", "int", "isinstance", "len", "list",
    # ... more safe builtins
})

def _make_sandbox_globals(response: httpx.Response | None) -> dict:
    return {
        "response": response,
        "status_code": response.status_code if response else None,
        "json_data": json_data,
        "headers": headers,
        "cookies": cookies_payload,
        "print": print,
        "__builtins__": {name: getattr(builtins, name) for name in _ALLOWLIST},
    }
```
