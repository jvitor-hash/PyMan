from textual.app import App, ComposeResult
from textual.containers import Vertical
from textual.widgets import (
    Button,
    Header,
    Input,
    Label,
    ListItem,
    ListView,
    Select,
    TabbedContent,
    TabPane,
    TextArea,
)

from APIClient import *
from RouteStorage import *
from ScriptOrchestration import *
from views.RenderCookiesList import render_cookies_list

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

        self.call_after_refresh(lambda: load_routes_from_file(self))

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

    def on_key(self, event) -> None:
        if event.key == "escape":
            self.clear_route_selection()

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        btn_id = event.button.id or ""

        if btn_id == "send-btn":
            await make_request(self)
        elif btn_id == "save-btn":
            save_current_route(self)

        # Handle Edit Button Click
        elif btn_id.startswith("edit_"):
            route_id = btn_id.replace("edit_", "")
            if route_id in self.saved_routes:
                route = self.saved_routes[route_id]

                # Explicitly set active_route_id ONLY when Edit is clicked
                self.active_route_id = route_id

                # Overwrite saved entry with current input fields
                route["method"] = self.query_one("#method-select", Select).value
                route["url"] = self.query_one("#url-input", Input).value.strip()
                route["body"] = self.query_one("#request-body", TextArea).text
                route["script"] = self.query_one("#script-input", TextArea).text
                route["headers"] = self.query_one("#input-headers", TextArea).text

                save_routes_to_file(self)

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

                save_routes_to_file(self)

                # Remove the ListItem component from UI
                list_item = self.query_one(f"#{route_id}", ListItem)
                list_item.remove()

                self.query_one("#status-label", Label).update("Status: Route deleted")

        # Clear all cookies for current route
        elif btn_id == "clear-cookies-btn":
            if self.active_route_id and self.active_route_id in self.saved_routes:
                self.saved_routes[self.active_route_id]["cookies"] = {}
                save_routes_to_file(self)

            cookies_list = self.query_one("#cookies-list", ListView)
            cookies_list.clear()
            self.query_one("#status-label", Label).update("Status: Route cookies cleared")

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "url-input":
            await make_request(self)

    def on_list_view_selected(self, event: ListView.Selected) -> None:
        # Populate the form fields with the selected route's data...
        selected_id = event.item.id
        route_data = self.saved_routes.get(selected_id, {})

        self.query_one("#method-select", Select).value = route_data.get("method", "GET")
        self.query_one("#url-input", Input).value = route_data.get("url", "")
        self.query_one("#request-body", TextArea).text = route_data.get("body", "")
        self.query_one("#script-input", TextArea).text = route_data.get("script", "")
        self.query_one("#input-headers", TextArea).text = route_data.get("headers", "")

        # Render cookies bound to this route
        route_cookies = route_data.get("cookies", {})
        render_cookies_list(self, route_cookies)

        self.query_one("#status-label", Label).update(
            f"Status: Loaded '{route_data['url']}'"
        )

        # Reset active_route_id so saving creates a NEW route instead of overwriting this one
        self.active_route_id = None

    def clear_route_selection(self) -> None:
        """Clears the active route selection and resets input fields."""
        self.active_route_id = None

        # Clear the active selection highlight in the ListView
        list_view = self.query_one("#saved-routes-list", ListView)
        list_view.index = None

        # Reset input fields to default states
        self.query_one("#method-select", Select).value = "GET"
        self.query_one("#url-input", Input).value = ""
        self.query_one("#request-body", TextArea).text = ""
        self.query_one("#script-input", TextArea).text = ""
        self.query_one("#input-headers", TextArea).text = ""

        # Status update about the de-selection
        self.query_one("#status-label", Label).update("Status: Saved route de-selected")

    async def on_text_area_changed(self, event: TextArea.Changed) -> None:
        if event.control.language == "python":
            await parse_script(self)

if __name__ == "__main__":
    app = PyMan()
    app.run()
