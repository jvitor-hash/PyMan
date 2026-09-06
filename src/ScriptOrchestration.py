import ast
import io
import sys

import httpx
from textual.widgets import Label, TextArea


# Parses the script before execution to verify structural integrity of the script.
# (Note: this does not verify the runtime)
async def parse_script(self) -> None:
    script_text = self.query_one("#script-input", TextArea).text
    script_status = self.query_one(".script-status", Label)

    try:
        ast.parse(script_text)
    except SyntaxError as e:
        script_status.update(f"Syntax Error: {e}")
    else:
        script_status.update("Script Execution Status")

def execute_script(self, response: httpx.Response | None) -> None:
    script_text = self.query_one("#script-input", TextArea).text.strip()
    script_status = self.query_one(".script-status", Label)

    if not script_text:
        script_status.update("No script provided")
        return

    script_status.remove_class("script-success")
    script_status.remove_class("script-failed")

    try:
        json_data = response.json() if response else None
    except Exception:
        json_data = None

    # Sandbox context exposing response & app properties
    sandbox_globals = {
        "response": response,
        "status_code": response.status_code if response else None,
        "json_data": json_data,
        "headers": dict(response.headers) if response else {},
        "cookies": dict(response.cookies) if response else {}
        if response
        and response.headers.get("content-type", "").startswith("application/json")
        else None,
        "print": print,
    }

    # Capture standard output
    stdout_capture = io.StringIO()
    sys.stdout = stdout_capture

    try:
        exec(script_text, sandbox_globals)
        sys.stdout = sys.__stdout__
        output = stdout_capture.getvalue().strip()

        script_status.add_class("script-success")

        if output:
            script_status.update(f"Output: {output}")
        else:
            script_status.update("✓ Script executed successfully")
    except Exception as e:
        sys.stdout = sys.__stdout__
        script_status.add_class("script-failed")
        script_status.update(f"Failed: {type(e).__name__}: {e}")
