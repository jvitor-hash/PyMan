import json
import httpx
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Button, Header, Input, Label, Select, TextArea


class TUIApp(App):
    CSS_PATH="css/global.tcss"

    def compose(self) -> ComposeResult:
        yield Header()

        # Request Address Bar
        yield Horizontal(
            Select(
                [("GET", "GET"), ("POST", "POST"), ("PUT", "PUT"), ("DELETE", "DELETE"), ("PATCH", "PATCH")],
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

        yield Label("Status: Ready", id="status-label")

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "send-btn":
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

            # Format Response
            status_label.update(f"Status: {response.status_code} {response.reason_phrase}")

            try:
                formatted_json = json.dumps(response.json(), indent=2)
                response_area.text = formatted_json
            except Exception:
                response_area.text = response.text

        except Exception as e:
            status_label.update(f"Status: Request Failed")
            response_area.text = str(e)


if __name__ == "__main__":
    app = TUIApp()
    app.run()
