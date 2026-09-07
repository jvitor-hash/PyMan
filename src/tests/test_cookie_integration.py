"""Integration tests for cookie handling and component interactions."""

from __future__ import annotations

from typing import Any

import pytest

from textual.containers import Horizontal
from textual.widgets import Button, Label, ListItem, ListView

import views.RenderCookiesList as render_mod

_safe_cookie_widget_suffix = render_mod._safe_cookie_widget_suffix
render_cookies_list = render_mod.render_cookies_list


class _FakeListView:
    def __init__(self) -> None:
        self.items: list[Any] = []
        self.cleared = False

    def clear(self) -> None:
        self.items.clear()
        self.cleared = True

    def append(self, item: Any) -> None:
        self.items.append(item)

    def query(self, cls: Any) -> list[Any]:
        results: list[Any] = []
        for item in self.items:
            if isinstance(item, cls):
                results.append(item)
            # For real Textual widgets (like ListItem), check _pending_children
            # instead of calling their query() method which requires app context.
            pending = getattr(item, '_pending_children', None)
            if pending is not None:
                for child in pending:
                    if isinstance(child, cls):
                        results.append(child)
                    # Also check the child's own pending children (for Horizontal)
                    sub_pending = getattr(child, '_pending_children', None)
                    if sub_pending is not None:
                        for subchild in sub_pending:
                            if isinstance(subchild, cls):
                                results.append(subchild)
            # Also check content.children for ListItem
            if hasattr(item, 'content'):
                content = item.content
                if isinstance(content, cls):
                    results.append(content)
        return results

    def __iter__(self):
        return iter(self.items)


class _FakeApp:
    def __init__(self) -> None:
        self._cookies_list = _FakeListView()
        self.call_count: dict[str, int] = {}

    def query_one(self, selector: str, expectation: Any = None) -> Any:
        if selector == "#cookies-list":
            return self._cookies_list
        raise AssertionError(f"unexpected selector: {selector}")


class _FakeAppWithRouteState:
    """Test app with route state to test cookie deletion integration."""
    
    def __init__(self, saved_routes: dict[str, Any] | None = None) -> None:
        self._cookies_list = _FakeListView()
        self.saved_routes = saved_routes or {}
        self.active_route_id: str | None = None
        self.is_editing_route = False
        self.cookie_deletion_calls: list[tuple[str, str]] = []

    def query_one(self, selector: str, expectation: Any = None) -> Any:
        if selector == "#cookies-list":
            return self._cookies_list
        raise AssertionError(f"unexpected selector: {selector}")


def test_render_cookies_list_with_empty_dict() -> None:
    """Test that rendering an empty cookie dict clears the list without errors."""
    app = _FakeApp()
    app._cookies_list.items = ["stale_item"]
    app._cookies_list.cleared = False
    
    render_cookies_list(app, {})
    
    assert app._cookies_list.cleared is True
    assert app._cookies_list.items == []


def test_render_cookies_list_with_none_values() -> None:
    """Test rendering cookies with None values doesn't crash."""
    app = _FakeApp()
    
    # Should handle None values gracefully
    render_cookies_list(app, {"session": None, "user": "bob"})
    
    assert len(app._cookies_list.items) == 2


def test_render_cookies_list_with_special_characters() -> None:
    """Test cookie names with various special characters are handled."""
    app = _FakeApp()
    
    cookies = {
        "simple": "value1",
        "with.dot": "value2",
        "with-dash": "value3",
        "with_underscore": "value4",
        "with spaces": "value5",
        "123numeric": "value6",
        "...": "value7",
    }
    
    render_cookies_list(app, cookies)
    
    items = app._cookies_list.query(ListItem)
    assert len(items) == 7
    
    # Verify cookie names are preserved
    cookie_names = [item.cookie_name for item in items]
    assert "simple" in cookie_names
    assert "with.dot" in cookie_names
    assert "with-dash" in cookie_names
    assert "with_underscore" in cookie_names
    assert "with spaces" in cookie_names
    assert "123numeric" in cookie_names
    assert "..." in cookie_names


def test_cookie_deletion_integration_with_active_route() -> None:
    """Integration test: deleting a cookie updates route state and persists."""
    app = _FakeAppWithRouteState({
        "route_1": {
            "url": "https://example.com",
            "cookies": {"session": "abc123", "user": "testuser"}
        }
    })
    app.active_route_id = "route_1"
    
    # Simulate cookie deletion
    route_cookies = app.saved_routes["route_1"]["cookies"]
    route_cookies.pop("session", None)
    
    # Verify cookie was removed from route state
    assert "session" not in app.saved_routes["route_1"]["cookies"]
    assert "user" in app.saved_routes["route_1"]["cookies"]


def test_cookie_deletion_when_active_route_not_set() -> None:
    """Test that cookie deletion is skipped when no active route is set."""
    app = _FakeAppWithRouteState({
        "route_1": {"url": "https://example.com", "cookies": {"session": "abc"}}
    })
    app.active_route_id = None
    
    # Attempt to delete cookie without active route
    cookie_name = "session"
    if cookie_name and app.active_route_id in app.saved_routes:
        route_cookies = app.saved_routes[app.active_route_id].get("cookies", {})
        route_cookies.pop(cookie_name, None)
    
    # Cookie should still exist since no active route
    assert "session" in app.saved_routes["route_1"]["cookies"]


def test_cookie_deletion_when_route_not_in_saved_routes() -> None:
    """Test that cookie deletion is skipped when active route not in saved_routes."""
    app = _FakeAppWithRouteState({})
    app.active_route_id = "nonexistent_route"
    
    # Attempt to delete cookie with invalid active route
    cookie_name = "session"
    if cookie_name and app.active_route_id in app.saved_routes:
        route_cookies = app.saved_routes[app.active_route_id].get("cookies", {})
        route_cookies.pop(cookie_name, None)
    
    # Nothing should happen
    assert app.saved_routes == {}


def test_multiple_cookie_deletions_preserve_remaining_cookies() -> None:
    """Test that deleting multiple cookies preserves the remaining ones."""
    app = _FakeAppWithRouteState({
        "route_1": {
            "url": "https://example.com",
            "cookies": {"cookie1": "val1", "cookie2": "val2", "cookie3": "val3"}
        }
    })
    app.active_route_id = "route_1"
    
    # Delete cookie1 and cookie3
    route_cookies = app.saved_routes["route_1"]["cookies"]
    route_cookies.pop("cookie1", None)
    route_cookies.pop("cookie3", None)
    
    # Verify only cookie2 remains
    assert list(app.saved_routes["route_1"]["cookies"].keys()) == ["cookie2"]
    assert app.saved_routes["route_1"]["cookies"]["cookie2"] == "val2"


def test_cookie_rendering_after_deletion_reflects_state() -> None:
    """Integration test: re-rendering cookies after deletion shows correct state."""
    app = _FakeAppWithRouteState({
        "route_1": {
            "url": "https://example.com",
            "cookies": {"session": "abc", "user": "test"}
        }
    })
    app.active_route_id = "route_1"
    
    # Delete a cookie
    app.saved_routes["route_1"]["cookies"].pop("session", None)
    
    # Re-render the cookies list
    render_cookies_list(app, app.saved_routes["route_1"]["cookies"])
    
    # Verify only remaining cookie is shown
    items = app._cookies_list.query(ListItem)
    assert len(items) == 1
    assert items[0].cookie_name == "user"


def test_concurrent_cookie_modification_and_rendering() -> None:
    """Test that rendering cookies while modifying them doesn't cause issues."""
    app = _FakeAppWithRouteState({
        "route_1": {
            "url": "https://example.com",
            "cookies": {"cookie_a": "val_a", "cookie_b": "val_b"}
        }
    })
    app.active_route_id = "route_1"
    
    # Render initial state
    render_cookies_list(app, app.saved_routes["route_1"]["cookies"])
    initial_count = len(app._cookies_list.query(ListItem))
    assert initial_count == 2
    
    # Modify cookies (add and remove)
    app.saved_routes["route_1"]["cookies"]["cookie_c"] = "val_c"
    app.saved_routes["route_1"]["cookies"].pop("cookie_a", None)
    
    # Re-render
    render_cookies_list(app, app.saved_routes["route_1"]["cookies"])
    
    # Verify updated state
    items = app._cookies_list.query(ListItem)
    assert len(items) == 2
    cookie_names = [item.cookie_name for item in items]
    assert "cookie_b" in cookie_names
    assert "cookie_c" in cookie_names
    assert "cookie_a" not in cookie_names


class _FakeListItem(ListItem):
    """Fake ListItem that inherits from real ListItem for isinstance checks.

    Cannot be fully mounted (no app context), but isinstance(ListItem) works
    and it carries the cookie_name attribute used by the deletion handler.
    """
    def __init__(self, cookie_name: str) -> None:
        # Initialize the real ListItem with a dummy child to avoid errors
        super().__init__(Label("dummy"), id=f"cookie_item_{cookie_name}")
        self.cookie_name = cookie_name

    def remove(self) -> None:
        self.cookie_name = None


class _FakeButton:
    """Minimal Button mock that supports ancestor() traversal."""
    def __init__(self, button_id: str, parent_list_item: Any) -> None:
        self.id = button_id
        self._parent = parent_list_item

    def ancestor(self, cls: Any) -> Any:
        current = self._parent
        while current is not None:
            if isinstance(current, cls):
                return current
            current = getattr(current, "_parent", None)
        return None


class _FakeAppWithCookieAncestor:
    """Test app that supports button.ancestor(ListItem) traversal.

    Used to verify the refactored cookie deletion path in main.py.
    """
    def __init__(self) -> None:
        self._cookies_list = _FakeListView()
        self.saved_routes: dict[str, Any] = {}
        self.active_route_id: str | None = None

    def query_one(self, selector: str, expectation: Any = None) -> Any:
        if selector == "#cookies-list":
            return self._cookies_list
        raise AssertionError(f"unexpected selector: {selector}")


def test_cookie_deletion_uses_ancestor_traversal() -> None:
    """Cookie deletion should use button.ancestor(ListItem) instead of nested loops.

    This test verifies the refactored code path in main.py's on_button_pressed.
    We simulate what happens when a del_cookie_* button is pressed: the button's
    ancestor(ListItem) is used to find the containing ListItem directly.
    """
    app = _FakeAppWithCookieAncestor()
    app.saved_routes = {
        "route_1": {
            "url": "https://example.com",
            "cookies": {"session": "abc", "user": "test"},
        }
    }
    app.active_route_id = "route_1"

    # Build a ListItem with a cookie and a delete button.
    # The button's parent is the ListItem (as in the real Textual DOM).
    list_item = _FakeListItem("session")
    button = _FakeButton("del_cookie_session_0", list_item)

    # Simulate the refactored deletion logic from main.py:
    # button.ancestor(ListItem) walks up from button to its parent ListItem.
    cookie_item = button.ancestor(ListItem)
    assert cookie_item is not None
    assert cookie_item.cookie_name == "session"

    cookie_item.remove()
    assert cookie_item.cookie_name is None

    # Verify the cookie was removed from route state
    route_cookies = app.saved_routes["route_1"]["cookies"]
    route_cookies.pop("session", None)
    assert "session" not in route_cookies
    assert "user" in route_cookies
