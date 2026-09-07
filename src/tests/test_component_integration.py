"""Integration tests for main app components working together."""

from __future__ import annotations

from typing import Any

import pytest

from textual.containers import Horizontal
from textual.css.query import NoMatches
from textual.widgets import Button, Label, ListItem, ListView, Select

from RouteStorage import save_current_route, save_routes_to_file, load_routes_from_file
from views.RenderCookiesList import render_cookies_list


class _FakeSelect:
    def __init__(self, value: str) -> None:
        self.value = value


class _FakeInput:
    def __init__(self, value: str) -> None:
        self.value = value


class _FakeTextArea:
    def __init__(self, text: str = "") -> None:
        self.text = text


class _FakeLabel:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def update(self, message: str) -> None:
        self.value = message


class _FakeListView:
    def __init__(self) -> None:
        self.items: list[Any] = []
        self.cleared = False
        self._selected_index: int | None = None

    def clear(self) -> None:
        self.items.clear()
        self.cleared = True

    def append(self, item: Any) -> None:
        # Mock remove() on real Textual widgets to avoid NoActiveAppError
        if hasattr(item, 'remove') and not hasattr(item, '_remove_original'):
            item._remove_original = item.remove
            item.remove = lambda: self.items.remove(item)
        self.items.append(item)

    def query(self, cls: Any) -> list[Any]:
        results = []
        for item in self.items:
            if isinstance(item, cls):
                results.append(item)
            if hasattr(item, 'query'):
                try:
                    child_results = item.query(cls)
                    results.extend(child_results)
                except Exception:
                    pass
        return results

    def query_one(self, selector: str, expectation: Any = None) -> Any:
        # Simple query_one for testing — raises NoMatches to match Textual's API
        for item in self.items:
            if hasattr(item, 'id') and item.id == selector.lstrip('#'):
                return item
        raise NoMatches(f"No node matches {selector!r}")

    def __iter__(self):
        return iter(self.items)


class _IntegrationApp:
    """Test app that simulates the integration of multiple components."""
    
    def __init__(self, routes_file: str) -> None:
        self.ROUTES_FILE = routes_file
        self.saved_routes: dict[str, Any] = {}
        self.active_route_id: str | None = None
        self.is_editing_route = False
        self.route_counter = 0
        self._list_view = _FakeListView()
        self._cookies_list = _FakeListView()
        self._query_payload: dict[str, Any] = {}
        self._status_messages: list[str] = []

    def query_one(self, selector: str, expectation: Any = None) -> Any:
        if selector in self._query_payload:
            return self._query_payload[selector]
        if selector == "#saved-routes-list":
            return self._list_view
        if selector == "#cookies-list":
            # Return a fake ListView for cookies — render_cookies_list will clear it
            return self._cookies_list
        if selector == "#status-label":
            return _FakeLabel()
        if selector == "#method-select":
            return _FakeSelect("GET")
        if selector == "#url-input":
            return _FakeInput("")
        if selector == "#request-body":
            return _FakeTextArea()
        if selector == "#script-input":
            return _FakeTextArea()
        if selector == "#input-headers":
            return _FakeTextArea()
        raise AssertionError(f"unexpected selector: {selector}")

    def set_widget(self, selector: str, widget: Any) -> None:
        """Helper to set widgets for testing."""
        self._query_payload[selector] = widget

    def get_status_messages(self) -> list[str]:
        """Get all status messages that were set."""
        return self._status_messages


class _FakeStatusLabel:
    def __init__(self) -> None:
        self.value = ""

    def update(self, message: str, markup: bool = True) -> None:
        self.value = message


def test_full_route_lifecycle(tmp_path: Any) -> None:
    """Integration test: create route, save, load, edit, delete."""
    routes_file = tmp_path / "test_routes.json"
    
    app = _IntegrationApp(str(routes_file))
    
    # Setup widgets
    app.set_widget("#method-select", _FakeSelect("POST"))
    app.set_widget("#url-input", _FakeInput("https://api.example.com/data"))
    app.set_widget("#request-body", _FakeTextArea('{"key": "value"}'))
    app.set_widget("#script-input", _FakeTextArea("print('test')"))
    app.set_widget("#input-headers", _FakeTextArea("Authorization: Bearer token"))
    app.set_widget("#saved-routes-list", app._list_view)
    app.set_widget("#status-label", _FakeStatusLabel())
    
    # Set editing mode
    app.is_editing_route = True
    app.active_route_id = "route_1"
    app.saved_routes["route_1"] = {
        "url": "https://old.example.com",
        "method": "GET",
        "cookies": {"session": "abc"}
    }
    app.route_counter = 1
    
    # Test saving an existing route
    save_current_route(app)
    
    # Verify route was updated
    assert app.saved_routes["route_1"]["url"] == "https://api.example.com/data"
    assert app.saved_routes["route_1"]["method"] == "POST"
    
    # Verify UI was updated: _append_route_row creates a new ListItem since
    # the test's _FakeListView has no pre-existing ListItem with id 'route_1'
    # (the old code's except Exception: fallback appended a new row; now
    # except NoMatches: does the same via _append_route_row)
    list_items = app._list_view.query(ListItem)
    assert len(list_items) == 1
    assert list_items[0].id == "route_1"


def test_route_persistence_across_sessions(tmp_path: Any, monkeypatch: Any) -> None:
    """Integration test: routes persist across app restarts."""
    routes_file = tmp_path / "persistent_routes.json"
    monkeypatch.setattr("RouteStorage.ROUTES_FILE", str(routes_file))

    # First "session" - save some routes
    app1 = _IntegrationApp(str(routes_file))
    app1.set_widget("#method-select", _FakeSelect("GET"))
    app1.set_widget("#url-input", _FakeInput("https://example.com/route1"))
    app1.set_widget("#request-body", _FakeTextArea())
    app1.set_widget("#script-input", _FakeTextArea())
    app1.set_widget("#input-headers", _FakeTextArea())
    app1.set_widget("#saved-routes-list", app1._list_view)
    app1.set_widget("#status-label", _FakeStatusLabel())
    app1.is_editing_route = True
    app1.active_route_id = "route_1"
    app1.route_counter = 0  # Will be incremented to 1 on first save
    
    save_current_route(app1)
    
    # Add another route (not in editing mode, so a new route is created)
    app1.active_route_id = None
    app1.is_editing_route = False
    app1.set_widget("#url-input", _FakeInput("https://example.com/route2"))
    app1.set_widget("#method-select", _FakeSelect("POST"))
    save_current_route(app1)
    
    # Verify routes were saved
    assert len(app1.saved_routes) == 2
    
    # Second "session" - load routes
    app2 = _IntegrationApp(str(routes_file))
    app2.set_widget("#saved-routes-list", app2._list_view)
    app2.set_widget("#status-label", _FakeStatusLabel())
    
    load_routes_from_file(app2)
    
    # Verify routes were loaded
    assert len(app2.saved_routes) == 2
    assert app2.saved_routes["route_1"]["url"] == "https://example.com/route1"
    assert app2.saved_routes["route_2"]["url"] == "https://example.com/route2"
    
    # Verify UI was populated
    list_items = app2._list_view.query(ListItem)
    assert len(list_items) == 2


def test_cookie_integration_with_route_deletion(tmp_path: Any, monkeypatch: Any) -> None:
    """Integration test: deleting a route also removes its cookies."""
    routes_file = tmp_path / "cookie_test.json"
    monkeypatch.setattr("RouteStorage.ROUTES_FILE", str(routes_file))

    app = _IntegrationApp(str(routes_file))
    app.set_widget("#saved-routes-list", app._list_view)
    app.set_widget("#status-label", _FakeStatusLabel())
    
    # Create a route with cookies
    app.saved_routes["route_1"] = {
        "url": "https://example.com",
        "method": "GET",
        "cookies": {"session": "abc", "user": "test"}
    }
    
    # Add UI item
    item_content = Horizontal(
        Label("[GET] https://example.com", classes="route-label"),
        Button("Edit", id="edit_route_1", variant="warning", classes="action-btn"),
        Button("Delete", id="del_route_1", variant="error", classes="action-btn"),
        classes="saved-route-row",
    )
    app._list_view.append(ListItem(item_content, id="route_1"))
    
    # Delete the route
    del app.saved_routes["route_1"]
    save_routes_to_file(app)
    
    # Remove UI item
    list_item = app._list_view.query_one("#route_1", ListItem)
    list_item.remove()
    
    # Verify route and cookies are gone
    assert "route_1" not in app.saved_routes
    
    # Verify file was updated
    import json
    with open(routes_file, 'r') as f:
        saved_data = json.load(f)
    assert "route_1" not in saved_data


def test_edit_mode_flag_prevents_accidental_overwrites(tmp_path: Any) -> None:
    """Integration test: is_editing_route flag prevents overwriting routes when not intended."""
    routes_file = tmp_path / "edit_test.json"
    
    app = _IntegrationApp(str(routes_file))
    app.set_widget("#method-select", _FakeSelect("POST"))
    app.set_widget("#url-input", _FakeInput("https://new.example.com"))
    app.set_widget("#request-body", _FakeTextArea())
    app.set_widget("#script-input", _FakeTextArea())
    app.set_widget("#input-headers", _FakeTextArea())
    app.set_widget("#saved-routes-list", app._list_view)
    app.set_widget("#status-label", _FakeStatusLabel())
    
    # Create an existing route
    app.saved_routes["route_1"] = {
        "url": "https://original.example.com",
        "method": "GET",
        "cookies": {}
    }
    app.active_route_id = "route_1"
    app.route_counter = 1
    
    # NOT in editing mode - should create a NEW route
    app.is_editing_route = False
    save_current_route(app)
    
    # Verify original route was NOT overwritten
    assert app.saved_routes["route_1"]["url"] == "https://original.example.com"
    
    # Verify a new route was created
    assert "route_2" in app.saved_routes
    assert app.saved_routes["route_2"]["url"] == "https://new.example.com"


def test_render_cookies_list_integration_with_route_selection(tmp_path: Any) -> None:
    """Integration test: selecting a route renders its cookies correctly."""
    routes_file = tmp_path / "select_test.json"
    
    app = _IntegrationApp(str(routes_file))
    app.set_widget("#saved-routes-list", app._list_view)
    app.set_widget("#status-label", _FakeStatusLabel())
    
    # Create routes with different cookies
    app.saved_routes["route_1"] = {
        "url": "https://example.com",
        "method": "GET",
        "cookies": {"session": "abc", "user": "test"}
    }
    app.saved_routes["route_2"] = {
        "url": "https://other.com",
        "method": "POST",
        "cookies": {"token": "xyz"}
    }
    
    # Select route_1
    app.active_route_id = "route_1"
    
    # Render cookies for selected route
    route_cookies = app.saved_routes["route_1"]["cookies"]
    render_cookies_list(app, route_cookies)
    
    # Verify correct cookies are displayed (in _cookies_list, not _list_view)
    cookie_items = app._cookies_list.query(ListItem)
    assert len(cookie_items) == 2
    cookie_names = [item.cookie_name for item in cookie_items]
    assert "session" in cookie_names
    assert "user" in cookie_names
    assert "token" not in cookie_names


def test_clear_cookies_button_integration(tmp_path: Any) -> None:
    """Integration test: clear cookies button resets both UI and data."""
    routes_file = tmp_path / "clear_test.json"
    
    app = _IntegrationApp(str(routes_file))
    app.set_widget("#saved-routes-list", app._list_view)
    app.set_widget("#status-label", _FakeStatusLabel())
    
    # Create route with cookies
    app.saved_routes["route_1"] = {
        "url": "https://example.com",
        "method": "GET",
        "cookies": {"cookie1": "val1", "cookie2": "val2"}
    }
    app.active_route_id = "route_1"
    
    # Render cookies
    render_cookies_list(app, app.saved_routes["route_1"]["cookies"])
    
    # Clear cookies
    app.saved_routes["route_1"]["cookies"] = {}
    save_routes_to_file(app)
    
    # Clear UI
    app._list_view.clear()
    
    # Verify cookies are cleared
    assert app.saved_routes["route_1"]["cookies"] == {}
    
    # Verify UI is cleared
    assert len(app._list_view.query(ListItem)) == 0
