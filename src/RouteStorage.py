import json
import os

from textual.containers import Horizontal
from textual.widgets import Button, Input, Label, ListItem, ListView, Select, TextArea

ROUTES_FILE = "saved_routes.json"

def save_current_route(self) -> None:
    method = self.query_one("#method-select", Select).value
    url = self.query_one("#url-input", Input).value.strip()
    body = self.query_one("#request-body", TextArea).text
    script = self.query_one("#script-input", TextArea).text
    headers = self.query_one("#input-headers", TextArea).text

    if not url:
        self.query_one("#status-label", Label).update("Status: Cannot save empty URL")
        return

    # Ensure self.route_counter accounts for all existing saved route IDs
    for r_id in self.saved_routes:
        try:
            num = int(r_id.replace("route_", ""))
            self.route_counter = max(self.route_counter, num)
        except ValueError:
            pass

    # Use existing active_route_id only if it is already in saved_routes
    if self.active_route_id in self.saved_routes:
        route_id = self.active_route_id
        is_new_route = False
    else:
        self.route_counter += 1
        route_id = f"route_{self.route_counter}"
        self.active_route_id = route_id
        is_new_route = True

    existing_cookies = self.saved_routes.get(route_id, {}).get("cookies", {})

    self.saved_routes[route_id] = {
        "method": method,
        "url": url,
        "body": body,
        "script": script,
        "headers": headers,
        "cookies": existing_cookies,
    }

    save_routes_to_file(self)

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

def save_routes_to_file(self) -> None:
    """Persists the current saved_routes state to disk."""
    try:
        with open(ROUTES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.saved_routes, f, indent=2)
    except Exception as e:
        self.query_one("#status-label", Label).update(
            f"Status: File write error ({e})"
        )

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
