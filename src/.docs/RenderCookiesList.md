# RenderCookiesList - Cookie UI Rendering

#filename
src/views/RenderCookiesList.py
#test file
src/tests/test_RenderCookiesList_id.py

#date of last update of the docs
2026-09-07

#date of creation
2026-09-07

#summary
Renders cookie lists in the UI with proper widget ID sanitization for cookie names.

#description
RenderCookiesList provides UI rendering for cookies with special handling for invalid widget IDs:

- **_COOKIE_ID_RE** - Regex pattern to match invalid characters in widget IDs (`[^A-Za-z0-9_\-]`)

- **_safe_cookie_widget_suffix(name)** - Converts cookie names to valid widget ID suffixes:
  - Replaces invalid characters with underscores
  - Strips leading/trailing underscores
  - Defaults to "cookie" if result is empty
  - Prefixes with "c" if starts with digit

- **render_cookies_list(self, cookies)** - Renders cookies in ListView:
  - Clears existing items
  - Creates ListItem for each cookie with unique IDs
  - Uses render_index to ensure unique IDs across renders
  - Sets cookie_name and cookie_uid attributes for deletion handling
  - Configures Label with can_wrap=True and overflow="fold" for long cookie values

Widget ID structure:
- Item ID: `item_{suffix}_{render_seq}` (e.g., "item_sails_sid_0")
- Button ID: `del_cookie_{suffix}_{render_seq}` (e.g., "del_cookie_sails_sid_0")
- cookie_uid preserves original name: "cookie_sails.sid"

#code
```python
_COOKIE_ID_RE = re.compile(r"[^A-Za-z0-9_\-]")

def _safe_cookie_widget_suffix(name: str) -> str:
    suffix = _COOKIE_ID_RE.sub("_", name).strip("_")
    if not suffix:
        suffix = "cookie"
    if suffix[0].isdigit():
        suffix = f"c{suffix}"
    return suffix

def render_cookies_list(self, cookies: dict) -> None:
    cookies_list = self.query_one("#cookies-list", ListView)
    cookies_list.clear()
    
    for name, value in cookies.items():
        cookie_uid = f"cookie_{name}"
        item_id = f"item_{cookie_widget_suffix}_{render_seq}"
        # ... create ListItem with Label and Delete Button ...
```
