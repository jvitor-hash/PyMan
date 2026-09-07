import ast
import builtins
import io
from contextlib import redirect_stdout

import httpx
from textual.widgets import Label, TextArea

# Allowlisted builtins that are reasonably safe for simple scripting.
_ALLOWLIST = frozenset({
    "abs", "all", "any", "bool", "dict", "enumerate", "filter", "float",
    "format", "getattr", "hasattr", "int", "isinstance", "len", "list",
    "map", "max", "min", "oct", "ord", "pow", "range", "repr", "reversed",
    "round", "set", "slice", "sorted", "str", "sum", "tuple", "zip",
    "True", "False", "None",
})


def _make_sandbox_globals(response: httpx.Response | None) -> dict:
    """Build a restricted execution namespace for user scripts.

    Only allowlisted builtins are exposed, and dangerous modules/attributes
    are blocked by providing a restricted __builtins__ dict.
    """
    if response is not None:
        # Try to get json data from the response
        try:
            json_data = response.json()
        except Exception:
            # Fall back to _json attribute if set by mocks
            json_data = getattr(response, '_json', None)
        headers = dict(response.headers)
        cookies = dict(response.cookies)
    else:
        json_data = None
        headers = {}
        cookies = {}

    # In many client libraries 'cookies' is best represented as a dict.
    # Keep the original RawCookie mapping available separately if needed.
    if response is not None and response.headers.get("content-type", "").startswith(
        "application/json"
    ):
        cookies_payload = cookies
    else:
        cookies_payload = None

    return {
        "response": response,
        "status_code": response.status_code if response is not None else None,
        "json_data": json_data,
        "headers": headers,
        "cookies": cookies_payload,
        "print": print,
        "__builtins__": {name: getattr(builtins, name) for name in _ALLOWLIST},
    }


async def parse_script(self) -> None:
    script_text = self.query_one("#script-input", TextArea).text
    script_status = self.query_one(".script-status", Label)

    try:
        ast.parse(script_text)
    except SyntaxError as e:
        script_status.update(f"Syntax Error: {e}")
    else:
        script_status.update("Script Execution Status")


async def execute_script(self, response: httpx.Response | None) -> None:
    script_text = self.query_one("#script-input", TextArea).text.strip()
    script_status = self.query_one(".script-status", Label)

    if not script_text:
        script_status.update("No script provided")
        return

    script_status.remove_class("script-success")
    script_status.remove_class("script-failed")

    globals_ns = _make_sandbox_globals(response)

    # Capture standard output safely.
    stdout_capture = io.StringIO()

    try:
        # Redirect stdout while executing the user script.
        with redirect_stdout(stdout_capture):
            exec(script_text, globals_ns)
        output = stdout_capture.getvalue().strip()
    except Exception as e:
        script_status.add_class("script-failed")
        script_status.update(f"Failed: {type(e).__name__}: {e}")
        return

    script_status.add_class("script-success")

    if output:
        script_status.update(f"Output: {output}")
    else:
        script_status.update("✓ Script executed successfully")
