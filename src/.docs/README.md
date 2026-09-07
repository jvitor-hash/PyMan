# PyMan - HTTP Client Application

#filename
src/.docs/README.md
#test file
src/tests/conftest.py (pytest configuration shared across all test files)

#date of last update of the docs
2026-09-07

#date of creation
2026-09-07

#summary
PyMan is a terminal-based HTTP client built with Textual framework, featuring request execution, script sandboxing, route storage, and cookie management.

#description
PyMan is a TUI (Terminal User Interface) HTTP client that allows users to make HTTP requests, execute Python scripts in a sandboxed environment, save/load routes, and manage cookies. The application is structured into several modular components:

1. **main.py** - Main application entry point containing the PyMan App class with UI composition and event handlers
2. **APIClient.py** - Handles HTTP request execution, response formatting, and cookie extraction. Delegates UI row creation to RouteStorage to keep network logic separate from DOM manipulation.
3. **ScriptOrchestration.py** - Provides safe Python script execution in a sandboxed environment with restricted builtins
4. **RouteStorage.py** - Manages saving, loading, and persistence of HTTP routes to JSON files. Also provides `_append_route_row()` for shared UI row construction used by both `save_current_route()` and `make_request()`.
5. **views/RenderCookiesList.py** - Renders cookie lists in the UI with proper widget ID sanitization

**Architecture notes:**
- UI row creation is centralized in `RouteStorage._append_route_row()` to avoid duplication between `make_request()` and `save_current_route()`.
- Cookie deletion uses `event.button.ancestor(ListItem)` for efficient DOM traversal instead of nested loops.
- All route labels use `markup=False` to prevent Textual from interpreting `[METHOD]` prefixes as markup.
- Exception handling for ListItem lookups uses `NoMatches` (from `textual.css.query`) instead of broad `except Exception:`.

The application uses Textual widgets for the UI and httpx for async HTTP requests.

#code
```python
# Main application structure
from textual.app import App, ComposeResult

class PyMan(App):
    CSS_PATH = "css/global.tcss"
    TITLE = "PyMan"
    
    def on_mount(self) -> None:
        self.saved_routes = {}
        self.active_route_id = None
        self.route_counter = 0
        self.cookie_counter = 0
        self.call_after_refresh(lambda: load_routes_from_file(self))
    
    def compose(self) -> ComposeResult:
        # UI composition with tabs for Request and Saved routes
        ...
```
