import io
import json
import sys

import httpx
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Header, Input, Label, Select, TextArea


class PyMan(App):
    CSS_PATH = "css/global.tcss"
    TITLE = "PyMan"

    def compose(self) -> ComposeResult:
        yield Header()

        # Request Address Bar
        yield Horizontal(
            Select(
                [
                    ("GET", "GET"),
                    ("POST", "POST"),
                    ("PUT", "PUT"),
                    ("DELETE", "DELETE"),
                    ("PATCH", "PATCH"),
                ],
                value="GET",
                id="method-select",
                allow_blank=False,
            ),
            Input(placeholder="https://api.example.com/data", id="url-input"),
            Button("Send", id="send-btn", variant="primary"),
            id="request-bar",
        )

        # Main Work Area
        yield Horizontal(
            Vertical(
                Label("Request Body (JSON)", classes="section-title"),
                TextArea(id="request-body", language="json"),
                classes="pane",
            ),
            Vertical(
                Label("Response Body", classes="section-title"),
                TextArea(id="response-body", read_only=True, language="json"),
                classes="pane",
            ),
            id="main-container",
        )

        # Scripts Section
        yield Horizontal(
            Vertical(
                Label("Script Execution Status", classes="script-status"),
                TextArea(id="script-input", language="python", placeholder="Type your script here (python)"),
                classes="pane",
            ),
            id="scripts-container",
        )

        yield Label("Status: Ready", id="status-label")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-btn":
            await self.make_request()

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "url-input":
            await self.make_request()

    async def make_request(self) -> None:
        method = self.query_one("#method-select", Select).value
        url = self.query_one("#url-input", Input).value.strip()
        body_text = self.query_one("#request-body", TextArea).text.strip()
        response_area = self.query_one("#response-body", TextArea)
        status_label = self.query_one("#status-label", Label)

        if not url:
            status_label.update("Status: Error - URL cannot be empty")
            return

        status_label.update("Status: Sending...")

        # Parse JSON body if present
        json_data = None
        if body_text and method in ("POST", "PUT", "PATCH"):
            try:
                json_data = json.loads(body_text)
            except json.JSONDecodeError as e:
                status_label.update(f"Status: Invalid JSON body ({e})")
                return

        # Execute HTTP Request
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=json_data,
                    timeout=10.0,
                )

                self.execute_script(response)

            # Format Response
            status_label.update(
                f"Status: {response.status_code} {response.reason_phrase}"
            )

            try:
                formatted_json = json.dumps(response.json(), indent=2)
                response_area.text = formatted_json
            except Exception:
                response_area.text = response.text

        except Exception as e:
            status_label.update(f"Status: Request Failed")
            response_area.text = str(e)

    def execute_script(self, response: httpx.Response | None) -> None:
        script_text = self.query_one("#script-input", TextArea).text.strip()
        script_status = self.query_one(".script-status", Label)

        if not script_text:
            script_status.update("No script provided")
            return

        script_status.remove_class("script-success")
        script_status.remove_class("script-failed")

        # Sandbox context exposing response & app properties
        sandbox_globals = {
            "response": response,
            "status_code": response.status_code if response else None,
            "json_data": response.json()
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


if __name__ == "__main__":
    app = PyMan()
    app.run()
