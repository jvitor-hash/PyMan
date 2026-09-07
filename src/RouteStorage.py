import json
import os

from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.widgets import Button, Input, Label, ListItem, ListView, Select, TextArea

ROUTES_FILE = "saved_routes.json"


def _append_route_row(self, route_id: str, method: str, url: str) -> None:
    """Append a new UI row for a saved route to the ListView.

    Kept in RouteStorage so both save_current_route() and APIClient.make_request()
    can use the same row-building logic.
    """
    list_view = self.query_one("#saved-routes-list", ListView)
    item_content = Horizontal(
        Label(f"[{method}] {url}", classes="route-label", markup=False),
        Button("Edit", id=f"edit_{route_id}", variant="warning", classes="action-btn"),
        Button("Delete", id=f"del_{route_id}", variant="error", classes="action-btn"),
        classes="saved-route-row",
    )
    list_view.append(ListItem(item_content, id=route_id))


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

    # Use existing active_route_id only if it is already in saved_routes AND we're in editing mode
    if self.active_route_id and self.active_route_id in self.saved_routes and getattr(self, 'is_editing_route', False):
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

    # Update or create UI row
    list_view = self.query_one("#saved-routes-list", ListView)

    if is_new_route:
        # Append a new UI row for new routes using shared helper
        _append_route_row(self, route_id, method, url)
        self.query_one("#status-label", Label).update(f"Status: Saved '{url}'")
    else:
        # Update the label in the existing UI row for updated routes
        try:
            list_item = list_view.query_one(f"#{route_id}", ListItem)
            label = list_item.query_one(".route-label", Label)
            label.update(f"[{method}] {url}", markup=False)
            self.query_one("#status-label", Label).update(f"Status: Updated '{url}'")
        except NoMatches:
            # If the list item doesn't exist (shouldn't happen), append it
            _append_route_row(self, route_id, method, url)


def save_routes_to_file(self) -> None:
    """Persists the current saved_routes state to disk."""
    try:
        with open(ROUTES_FILE, "w", encoding="utf-8") as f:
            json.dump(self.saved_routes, f, indent=2)
    except Exception as e:
        try:
            self.query_one("#status-label", Label).update(
                f"Status: File write error ({e})", markup=False
            )
        except Exception:
            pass


def load_routes_from_file(self) -> None:
    """Loads pre-saved routes from JSON file on application startup."""
    if os.path.exists(ROUTES_FILE):
        try:
            with open(ROUTES_FILE, "r", encoding="utf-8") as f:
                loaded_routes = json.load(f)

            # Filter out invalid routes that don't have required fields
            self.saved_routes = {}
            for route_id, route in loaded_routes.items():
                if isinstance(route, dict) and "url" in route and "method" in route:
                    self.saved_routes[route_id] = route
                # Skip invalid/corrupted routes silently

            list_view = self.query_one("#saved-routes-list", ListView)
            list_view.clear()  # Clear existing items to prevent duplicate ID crashes

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
                        f"[{route['method']}] {route['url']}",
                        classes="route-label",
                        markup=False,
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
            try:
                self.query_one("#status-label", Label).update(
                    f"Status: Load file error ({e})", markup=False
                )
            except Exception:
                pass
