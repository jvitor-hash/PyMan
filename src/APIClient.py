import json

import httpx
from textual.widgets import Input, Label, Select, Switch, TextArea

from RouteStorage import save_routes_to_file
from ScriptOrchestration import execute_script
from views.RenderCookiesList import render_cookies_list


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

            execute_script(self, response)
            extract_and_render_cookies(self, response)

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
        save_routes_to_file(self)
        render_cookies_list(self, route_cookies)
