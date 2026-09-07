# APIClient - HTTP Request Handler

#filename
src/APIClient.py
#test file
src/tests/test_APIClient_id.py

#date of last update of the docs
2026-09-07

#date of creation
2026-09-07

#summary
Handles HTTP request execution, response formatting, and cookie extraction using httpx.

#description
The APIClient module provides the core HTTP functionality:

- **make_request(self)** - Main async function that:
  - Validates URL input
  - Parses headers and JSON body
  - Creates or retrieves route ID
  - Delegates UI row creation to `RouteStorage._append_route_row()` when a new route is created
  - Executes HTTP request via httpx.AsyncClient
  - Formats JSON responses with indentation
  - Calls script execution and cookie extraction

- **extract_and_render_cookies(self, response)** - Extracts cookies from HTTP response and persists them to the active route if the save-cookies switch is enabled

- **_run_script_awaitable(self, response)** - Thin wrapper to execute user scripts after request completion

The module uses httpx for async HTTP requests and integrates with RouteStorage for persistence and RenderCookiesList for UI updates.

**UI Separation:** `make_request()` no longer directly constructs Textual widgets. UI row creation is delegated to `RouteStorage._append_route_row()` to keep network logic separate from DOM manipulation.

#code
```python
async def make_request(self) -> None:
    method = self.query_one("#method-select", Select).value
    url = self.query_one("#url-input", Input).value.strip()
    # ... validation and parsing ...
    
    async with httpx.AsyncClient() as client:
        response = await client.request(
            method=method, url=url, json=json_data,
            headers=headers_dict, cookies=current_cookies, timeout=10.0
        )
        await _run_script_awaitable(self, response)
        await extract_and_render_cookies(self, response)
```
