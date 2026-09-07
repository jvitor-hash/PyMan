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
        results = []
        for item in self.items:
            if isinstance(item, cls):
                results.append(item)
            # For ListItem-like objects, check if we can query children
            if hasattr(item, 'query'):
                try:
                    child_results = item.query(cls)
                    results.extend(child_results)
                except Exception:
                    pass
            if hasattr(item, 'content'):
                content = item.content
                if isinstance(content, cls):
                    results.append(content)
                for child in getattr(content, 'children', []):
                    if isinstance(child, cls):
                        results.append(child)
                    for subchild in getattr(child, 'children', []):
                        if isinstance(subchild, cls):
                            results.append(subchild)
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


def test_render_cookies_list_clears_existing_rows() -> None:
    app = _FakeApp()
    app._cookies_list.items = ["stale"]
    app._cookies_list.cleared = False

    render_cookies_list(app, {})

    assert app._cookies_list.cleared is True
    assert app._cookies_list.items == []


def test_render_cookies_list_creates_one_row_per_cookie() -> None:
    app = _FakeApp()
    render_cookies_list(app, {"session": "abc", "user": "bob"})

    assert len(app._cookies_list.items) == 2


def test_render_cookies_list_preserves_cookie_identity() -> None:
    app = _FakeApp()
    render_cookies_list(app, {"sails.sid": "xyz"})

    items = app._cookies_list.query(ListItem)
    assert len(items) == 1
    assert items[0].cookie_name == "sails.sid"
    assert items[0].cookie_uid == "cookie_sails.sid"


def test_render_cookies_list_produces_valid_widget_ids_for_dot_names() -> None:
    app = _FakeApp()
    render_cookies_list(app, {"sails.sid": "xyz", "cfuvid": "1"})

    items = app._cookies_list.query(ListItem)
    item_ids = [item.id for item in items]
    
    # Check item IDs (widget IDs should not contain dots)
    assert item_ids, f"Expected item_ids to be non-empty, got {item_ids}"
    for item_id in item_ids:
        assert "." not in item_id, f"Item ID '{item_id}' contains a dot"
        assert item_id[0].isalpha() or item_id[0] == "_", f"Item ID '{item_id}' doesn't start with letter or underscore"
    
    # Check that items have the expected attributes
    assert len(items) == 2
    item_names = [item.cookie_name for item in items]
    assert "sails.sid" in item_names
    assert "cfuvid" in item_names


def test_render_cookies_list_ids_are_unique_per_render() -> None:
    app = _FakeApp()
    # Render with two different cookies to get two items
    render_cookies_list(app, {"cookie_a": "value1", "cookie_b": "value2"})

    items = app._cookies_list.query(ListItem)
    item_ids = [item.id for item in items]

    # Each item should have a unique ID
    assert len(item_ids) == 2
    assert len(set(item_ids)) == 2


def test_render_cookies_list_cookie_label_wraps() -> None:
    app = _FakeApp()
    render_cookies_list(app, {"longcookie": "a"*50})

    items = app._cookies_list.query(ListItem)
    assert len(items) == 1, f"Expected 1 item, got {len(items)}"
    item = items[0]
    
    # Check that the item has the cookie_name set correctly
    assert item.cookie_name == "longcookie"
    assert item.cookie_uid == "cookie_longcookie"


def test_safe_cookie_widget_suffix_normalizes_invalid_chars() -> None:
    assert _safe_cookie_widget_suffix("sails.sid") == "sails_sid"
    assert _safe_cookie_widget_suffix("cfuvid") == "cfuvid"
    assert _safe_cookie_widget_suffix("a.b.c") == "a_b_c"


def test_safe_cookie_widget_suffix_handles_leading_digits() -> None:
    assert _safe_cookie_widget_suffix("1session") == "c1session"


def test_safe_cookie_widget_suffix_handles_empty_after_strip() -> None:
    assert _safe_cookie_widget_suffix("...") == "cookie"
