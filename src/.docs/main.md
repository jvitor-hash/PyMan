# PyMan Main Application

#filename
src/main.py
#test file
No dedicated test file (tested indirectly through APIClient, RouteStorage, and ScriptOrchestration tests)

#date of last update of the docs
2026-09-07

#date of creation
2026-09-07

#summary
Main TUI application entry point with UI composition, event handling, and user interaction logic.

#description
The PyMan class extends textual.App and provides the complete user interface:

**UI Composition (compose method):**
- Header widget
- TabbedContent with two main panes:
  - **Request pane**: Contains nested tabs for Body/Response and Headers/Cookies
    - Request bar with method select, URL input, Send and Save buttons
    - Headers/Cookies tab with header editor, cookie switch, and cookies list
    - Main work area with request body and response body TextAreas
    - Scripts section with script input and status label
    - Status label at bottom
  - **Saved routes pane**: Lists saved routes with edit/delete functionality

**Event Handlers:**
- **on_button_pressed** - Handles all button clicks:
  - Send button: Executes make_request
  - Save button: Saves current route
  - Edit buttons (edit_*): Loads route into form, sets editing mode so Save updates the route
  - Delete cookie buttons (del_cookie_*): Uses `event.button.ancestor(ListItem)` to find the containing ListItem directly (instead of nested DOM loops), then removes the cookie from route data
  - Delete buttons (del_*): Removes saved route
  - Clear cookies button: Clears all cookies for active route

**Cookie deletion:** The delete-cookie handler walks up from the clicked button using `button.ancestor(ListItem)` to find the parent ListItem, then reads `cookie_name` from the item. This is more efficient ($O(1)$ traversal) than the previous nested-loop approach ($O(N \times M)$).

- **on_input_submitted** - Triggers request when URL input is submitted (Enter key)

- **on_list_view_selected** - When a saved route is selected:
  - Populates form fields with route data
  - Renders associated cookies
  - Resets active_route_id to create new route on save

- **on_text_area_changed** - Parses script on Python textarea changes

- **clear_route_selection** - Resets form and clears selection

#code
```python
class PyMan(App):
    CSS_PATH = "css/global.tcss"
    TITLE = "PyMan"
    
    def compose(self) -> ComposeResult:
        yield Header()
        with TabbedContent():
            with TabPane("Request"):
                # ... nested tabs and widgets ...
            with TabPane("Saved routes"):
                yield Vertical(
                    Label("Saved Requests", classes="section-title"),
                    ListView(id="saved-routes-list"),
                    classes="pane",
                )
```
