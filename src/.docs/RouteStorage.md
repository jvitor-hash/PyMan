# RouteStorage - Route Persistence

#filename
src/RouteStorage.py
#test file
src/tests/test_RouteStorage_id.py

#date of last update of the docs
2026-09-07

#date of creation
2026-09-07

#summary
Manages saving, loading, and persistence of HTTP routes to JSON files.

#description
RouteStorage handles all route data persistence and UI row management:

- **ROUTES_FILE** - Module constant defining the default JSON file path ("saved_routes.json")

- **_append_route_row(self, route_id, method, url)** - Shared helper that appends a UI row (ListItem with Label + Edit/Delete buttons) to the saved routes ListView. Used by both `save_current_route()` and `APIClient.make_request()` to keep UI construction in one place.

- **save_current_route(self)** - Saves current form data as a route:
  - Validates URL is not empty
  - Updates route_counter to account for existing routes
  - Creates new route or updates existing active route (if `is_editing_route` is set)
  - Persists to file via save_routes_to_file
  - Calls `_append_route_row()` for new routes, or updates the existing label via `ListItem.query_one(".route-label")` for edited routes
  - Uses `NoMatches` (from `textual.css.query`) for specific exception handling when looking up existing ListItems

- **save_routes_to_file(self)** - Writes saved_routes dict to JSON file:
  - Uses json.dump with indent=2 for readability
  - Handles write errors gracefully with status message (defensive try/except around label update)

- **load_routes_from_file(self)** - Loads routes on application startup:
  - Checks if ROUTES_FILE exists
  - Loads JSON and populates saved_routes
  - Rebuilds UI ListView with all saved routes using `Label(markup=False)` to preserve `[METHOD]` prefixes
  - Updates route_counter from loaded data
  - Defensive try/except around label update on error

**Label markup:** All route labels use `markup=False` to prevent Textual from interpreting `[GET]`, `[POST]`, etc. as markup tags.

Route data structure:
```python
{
    "route_1": {
        "method": "GET",
        "url": "https://example.com",
        "body": "",
        "script": "",
        "headers": "",
        "cookies": {}
    }
}
```

#code
```python
ROUTES_FILE = "saved_routes.json"

def save_current_route(self) -> None:
    method = self.query_one("#method-select", Select).value
    url = self.query_one("#url-input", Input).value.strip()
    # ... validation ...
    
    self.saved_routes[route_id] = {
        "method": method, "url": url, "body": body,
        "script": script, "headers": headers, "cookies": existing_cookies,
    }
    save_routes_to_file(self)
```
