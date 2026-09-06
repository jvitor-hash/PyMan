import io
import json
import os
import sys

import httpx
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import (
    Button,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    Switch,
    TabbedContent,
    TabPane,
    TextArea,
)
from typing_extensions import Text

ROUTES_FILE = "saved_routes.json"

DEFAULT_HEADERS = """Accept: */*
Content-Type: application/json
User-Agent: PyMan/1.x
"""

class PyMan(App):
    CSS_PATH = "css/global.tcss"
    TITLE = "PyMan"

    def on_mount(self) -> None:
        # Stores route data indexed by an internal ID key
        self.saved_routes = {}
        self.active_route_id = None
        self.cookies = {}
        self.route_counter = 0
        self.cookie_counter = 0

        # Populate saved routes after DOM widgets are fully mounted
        self.call_after_refresh(self.load_routes_from_file)

    def compose(self) -> ComposeResult:
        yield Header()

        with TabbedContent():
            with TabPane("Request"):
                # Request Address Bar
                with TabbedContent(classes="secondary-tabs"):
                    with TabPane("Body/Response"):
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
                            Input(
                                placeholder="https://api.example.com/data",
                                id="url-input",
                            ),
                            Button("Send", id="send-btn", variant="primary"),
                            Button("Save", id="save-btn", variant="success"),
                            id="request-bar",
                        )
                    with TabPane("Headers/Cookies"):
                        yield Horizontal(
                            Vertical(
                                Label("Headers", classes="section-title"),
                                TextArea(id="input-headers", text=DEFAULT_HEADERS),
                                classes="pane",
                            ),
                            Vertical(
                                Label("Cookies", classes="section-title"),
                                    Horizontal(
                                        Label("Save Cookies?", classes="switch-label"),
                                        Switch(id="switch-save-cookies"),
                                        Button("Clear Cookies", id="clear-cookies-btn", variant="primary"),
                                        classes="cookies-switch"
                                    ),
                                ListView(id="cookies-list"),
                                classes="pane",
                            ),
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
                        TextArea(
                            id="script-input",
                            language="python",
                            placeholder="Type your script here (python)",
                        ),
                        classes="pane",
                    ),
                    id="scripts-container",
                )

                yield Label("Status: Ready", id="status-label")

            with TabPane("Saved routes"):
                yield Vertical(
                    Label("Saved Requests", classes="section-title"),
                    ListView(id="saved-routes-list"),
                    classes="pane",
                )

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""

        if btn_id == "send-btn":
            await self.make_request()
        elif btn_id == "save-btn":
            self.save_current_route()

        # Handle Edit Button Click
        elif btn_id.startswith("edit_"):
            route_id = btn_id.replace("edit_", "")
            if route_id in self.saved_routes:
                route = self.saved_routes[route_id]

                # Overwrite saved entry with current input fields
                route["method"] = self.query_one("#method-select", Select).value
                route["url"] = self.query_one("#url-input", Input).value.strip()
                route["body"] = self.query_one("#request-body", TextArea).text
                route["script"] = self.query_one("#script-input", TextArea).text
                route["headers"] = self.query_one("#input-headers", TextArea).text

                self.save_routes_to_file()

                # Update the displayed text label inside the list item
                label = self.query_one(f"#{route_id}", ListItem).query_one(
                    ".route-label", Label
                )
                label.update(f"[{route['method']}] {route['url']}")

                self.query_one("#status-label", Label).update(
                    f"Status: Updated '{route['url']}'"
                )

        # Handle Delete Button Click
        elif btn_id.startswith("del_"):
            route_id = btn_id.replace("del_", "")
            if route_id in self.saved_routes:
                del self.saved_routes[route_id]

                self.save_routes_to_file()

                # Remove the ListItem component from UI
                list_item = self.query_one(f"#{route_id}", ListItem)
                list_item.remove()

                self.query_one("#status-label", Label).update("Status: Route deleted")

        # Clear all cookies for current route
        elif btn_id == "clear-cookies-btn":
            if self.active_route_id and self.active_route_id in self.saved_routes:
                self.saved_routes[self.active_route_id]["cookies"] = {}
                self.save_routes_to_file()

            cookies_list = self.query_one("#cookies-list", ListView)
            cookies_list.clear()
            self.query_one("#status-label", Label).update("Status: Route cookies cleared")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "url-input":
            await self.make_request()

    async def make_request(self) -> None:
        method = self.query_one("#method-select", Select).value
        url = self.query_one("#url-input", Input).value.strip()
        body_text = self.query_one("#request-body", TextArea).text.strip()
        response_area = self.query_one("#response-body", TextArea)
        status_label = self.query_one("#status-label", Label)
        headers_data = self.query_one("#input-headers", TextArea).text.strip()

        if not url:
            status_label.update("Status: Error - URL cannot be empty")
            return

        status_label.update("Status: Sending...")

        # Parse raw headers string into a dictionary
        headers_dict = {}
        if headers_data:
            for line in headers_data.splitlines():
                if ":" in line:
                    key, val = line.split(":", 1)
                    headers_dict[key.strip()] = val.strip()

        # Parse JSON body if present
        json_data = None
        if body_text and method in ("POST", "PUT", "PATCH"):
            try:
                json_data = json.loads(body_text)
            except json.JSONDecodeError as e:
                status_label.update(f"Status: Invalid JSON body ({e})")
                return

        # Retrieve current active route cookies or use empty dict for unsaved route
        current_cookies = {}
        if not self.active_route_id:
            self.route_counter += 1
            self.active_route_id = f"route_{self.route_counter}"

        if self.active_route_id in self.saved_routes:
            current_cookies = self.saved_routes[self.active_route_id].get("cookies", {})
        else:
            self.saved_routes[self.active_route_id] = {
                "method": method,
                "url": url,
                "body": body_text,
                "script": self.query_one("#script-input", TextArea).text,
                "headers": headers_data,
                "cookies": {},
            }

        # Execute HTTP Request
        try:
            async with httpx.AsyncClient() as client:
                response = await client.request(
                    method=method,
                    url=url,
                    json=json_data,
                    headers=headers_dict,
                    cookies=current_cookies,
                    timeout=10.0,
                )

                self.execute_script(response)
                self.extract_and_render_cookies(response)

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

    def extract_and_render_cookies(self, response: httpx.Response) -> None:
        """Parses cookies from response and persists them to the active route."""
        save_cookies_enabled = self.query_one("#switch-save-cookies", Switch).value
        if not save_cookies_enabled:
            return

        if self.active_route_id:
            if self.active_route_id not in self.saved_routes:
                self.saved_routes[self.active_route_id] = {"cookies": {}}

            route_cookies = self.saved_routes[self.active_route_id].setdefault("cookies", {})

            for name, value in response.cookies.items():
                route_cookies[name] = value

            # Save state and re-render UI list cleanly
            self.save_routes_to_file()
            self.render_cookies_list(route_cookies)

    def save_current_route(self) -> None:
        method = self.query_one("#method-select", Select).value
        url = self.query_one("#url-input", Input).value.strip()
        body = self.query_one("#request-body", TextArea).text
        script = self.query_one("#script-input", TextArea).text
        headers = self.query_one("#input-headers", TextArea).text

        if not url:
            self.query_one("#status-label", Label).update("Status: Cannot save empty URL")
            return

        # Use existing active_route_id or generate a new one
        if not self.active_route_id or self.active_route_id not in self.saved_routes:
            self.route_counter += 1
            route_id = f"route_{self.route_counter}"
            self.active_route_id = route_id
            is_new_route = True
        else:
            route_id = self.active_route_id
            is_new_route = False

        existing_cookies = self.saved_routes.get(route_id, {}).get("cookies", {})

        self.saved_routes[route_id] = {
            "method": method,
            "url": url,
            "body": body,
            "script": script,
            "headers": headers,
            "cookies": existing_cookies,
        }

        self.save_routes_to_file()

        # Only append a new UI row if it's a new route
        if is_new_route:
            list_view = self.query_one("#saved-routes-list", ListView)
            item_content = Horizontal(
                Label(f"[{method}] {url}", classes="route-label"),
                Button("Edit", id=f"edit_{route_id}", variant="warning", classes="action-btn"),
                Button("Delete", id=f"del_{route_id}", variant="error", classes="action-btn"),
                classes="saved-route-row",
            )
            list_view.append(ListItem(item_content, id=route_id))

        self.query_one("#status-label", Label).update(f"Status: Saved '{url}'")

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        route_id = event.item.id
        if route_id in self.saved_routes:
            self.active_route_id = route_id
            route = self.saved_routes[route_id]

            # Populate request fields
            self.query_one("#method-select", Select).value = route["method"]
            self.query_one("#url-input", Input).value = route["url"]
            self.query_one("#request-body", TextArea).text = route["body"]
            self.query_one("#script-input", TextArea).text = route["script"]
            self.query_one("#input-headers", TextArea).text = route["headers"]

            # Render cookies bound to this route
            route_cookies = route.get("cookies", {})
            self.render_cookies_list(route_cookies)

            self.query_one("#status-label", Label).update(
                f"Status: Loaded '{route['url']}'"
            )

    def render_cookies_list(self, cookies: dict) -> None:
        """Helper method to clear and redraw the ListView with current route cookies."""
        cookies_list = self.query_one("#cookies-list", ListView)
        cookies_list.clear()

        for name, value in cookies.items():
            self.cookie_counter += 1
            cookie_id = f"ck_{self.cookie_counter}"

            item_content = Horizontal(
                Label(f"{name}={value}", classes="cookie-label"),
                Button(
                    "Delete",
                    id=f"del_cookie_{cookie_id}",
                    variant="error",
                    classes="action-btn",
                ),
                classes="cookie-row",
            )

            item = ListItem(item_content, id=f"item_{cookie_id}")
            setattr(item, "cookie_name", name)
            cookies_list.append(item)

    def load_routes_from_file(self) -> None:
        """Loads pre-saved routes from JSON file on application startup."""
        if os.path.exists(ROUTES_FILE):
            try:
                with open(ROUTES_FILE, "r", encoding="utf-8") as f:
                    self.saved_routes = json.load(f)

                list_view = self.query_one("#saved-routes-list", ListView)
                for route_id, route in self.saved_routes.items():
                    # Track route counter ID to prevent key collisions
                    try:
                        num = int(route_id.replace("route_", ""))
                        self.route_counter = max(self.route_counter, num)
                    except ValueError:
                        pass

                    # Build ListView UI row
                    item_content = Horizontal(
                        Label(
                            f"[{route['method']}] {route['url']}", classes="route-label"
                        ),
                        Button(
                            "Edit",
                            id=f"edit_{route_id}",
                            variant="warning",
                            classes="action-btn",
                        ),
                        Button(
                            "Delete",
                            id=f"del_{route_id}",
                            variant="error",
                            classes="action-btn",
                        ),
                        classes="saved-route-row",
                    )
                    list_view.append(ListItem(item_content, id=route_id))
            except Exception as e:
                self.query_one("#status-label", Label).update(
                    f"Status: Load file error ({e})"
                )

    def save_routes_to_file(self) -> None:
        """Persists the current saved_routes state to disk."""
        try:
            with open(ROUTES_FILE, "w", encoding="utf-8") as f:
                json.dump(self.saved_routes, f, indent=2)
        except Exception as e:
            self.query_one("#status-label", Label).update(
                f"Status: File write error ({e})"
            )

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
            "headers": response.headers
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
