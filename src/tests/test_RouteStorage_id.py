from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pytest

from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Button, Label, ListItem, ListView

from RouteStorage import (
    _append_route_row,
    load_routes_from_file,
    save_current_route,
    save_routes_to_file,
)


class _DummyApp:
    def __init__(self, routes_file: Path, saved_routes: dict[str, Any] | None = None) -> None:
        self.ROUTES_FILE = str(routes_file)
        self.saved_routes = saved_routes or {}
        self.active_route_id: str | None = None
        self.route_counter = 0
        self._list_view = ListView(id="saved-routes-list")
        self._query_payload: dict[str, Any] = {}

    def query_one(self, selector: str, expectation: Any = None) -> Any:
        if selector in self._query_payload:
            return self._query_payload[selector]
        if selector == "#saved-routes-list":
            return self._list_view
        if selector == "#status-label":
            return type("S", (), {"update": lambda self, msg: None})()
        raise AssertionError(f"unexpected selector: {selector}")

    def compose(self) -> ComposeResult:
        yield self._list_view


class _FakeWidget:
    def __init__(self, value: str = "") -> None:
        self.value = value

    @property
    def text(self) -> str:
        return self.value

    def update(self, message: str) -> None:
        self.value = message


class _FakeQueryPayload:
    def __init__(self, app: _DummyApp) -> None:
        self.app = app
        self._payload: dict[str, Any] = {}

    def set(self, selector: str, widget: Any) -> None:
        self._payload[selector] = widget
        self.app._query_payload[selector] = widget

    def install(self) -> None:
        # Payload is already installed via set() method
        pass


@pytest.mark.asyncio
async def test_save_current_route_creates_new_route(tmp_routes_file: Path, monkeypatch: Any) -> None:
    # Patch ROUTES_FILE to use our temp file
    monkeypatch.setattr("RouteStorage.ROUTES_FILE", str(tmp_routes_file))
    
    app = _DummyApp(tmp_routes_file)
    app.saved_routes = {}
    app.active_route_id = None
    app.route_counter = 0

    payload = _FakeQueryPayload(app)
    payload.set("#method-select", _FakeWidget("GET"))
    payload.set("#url-input", _FakeWidget("https://example.com"))
    payload.set("#request-body", _FakeWidget(""))
    payload.set("#script-input", _FakeWidget(""))
    payload.set("#input-headers", _FakeWidget(""))
    payload.set("#saved-routes-list", app._list_view)
    payload.set("#status-label", _FakeWidget("Status: Ready"))
    payload.install()

    # Mock the list_view.append to avoid MountError
    original_append = app._list_view.append
    app._list_view.append = lambda item: None
    
    try:
        save_current_route(app)
    finally:
        app._list_view.append = original_append

    assert app.active_route_id is not None
    assert app.active_route_id.startswith("route_")
    assert app.saved_routes[app.active_route_id]["url"] == "https://example.com"
    assert app.saved_routes[app.active_route_id]["method"] == "GET"

    written = json.loads(tmp_routes_file.read_text(encoding="utf-8"))
    assert written[app.active_route_id]["url"] == "https://example.com"


@pytest.mark.asyncio
async def test_save_current_route_rejects_empty_url(tmp_routes_file: Path, monkeypatch: Any) -> None:
    # Patch ROUTES_FILE so the test uses our temp file
    monkeypatch.setattr("RouteStorage.ROUTES_FILE", str(tmp_routes_file))
    
    app = _DummyApp(tmp_routes_file)
    app.saved_routes = {}
    app.active_route_id = None
    app.route_counter = 0

    payload = _FakeQueryPayload(app)
    payload.set("#method-select", _FakeWidget("GET"))
    payload.set("#url-input", _FakeWidget(""))
    payload.set("#request-body", _FakeWidget(""))
    payload.set("#script-input", _FakeWidget(""))
    payload.set("#input-headers", _FakeWidget(""))
    payload.set("#saved-routes-list", app._list_view)
    payload.set("#status-label", _FakeWidget("Status: Ready"))
    payload.install()

    save_current_route(app)

    assert app.saved_routes == {}
    # File should not be created since save_routes_to_file is not called when URL is empty
    assert not tmp_routes_file.exists()


def _set_is_editing_route(app: Any, value: bool) -> None:
    """Helper to set is_editing_route attribute on app."""
    app.is_editing_route = value


class _DummyAppWithEditing:
    """Extension of _DummyApp that supports is_editing_route."""
    def __init__(self, routes_file: Path, saved_routes: dict[str, Any] | None = None) -> None:
        self.ROUTES_FILE = str(routes_file)
        self.saved_routes = saved_routes or {}
        self.active_route_id: str | None = None
        self.route_counter = 0
        self.is_editing_route = False
        self._list_view = ListView(id="saved-routes-list")
        self._query_payload: dict[str, Any] = {}

    def query_one(self, selector: str, expectation: Any = None) -> Any:
        if selector in self._query_payload:
            return self._query_payload[selector]
        if selector == "#saved-routes-list":
            return self._list_view
        if selector == "#status-label":
            return type("S", (), {"update": lambda self, msg: None})()
        raise AssertionError(f"unexpected selector: {selector}")

    def compose(self) -> ComposeResult:
        yield self._list_view


@pytest.mark.asyncio
async def test_save_current_route_updates_existing_active_route(tmp_routes_file: Path, monkeypatch: Any) -> None:
    # Patch ROUTES_FILE to use our temp file
    monkeypatch.setattr("RouteStorage.ROUTES_FILE", str(tmp_routes_file))
    
    app = _DummyAppWithEditing(tmp_routes_file)
    route_id = "route_1"
    app.saved_routes = {route_id: {"url": "https://old.example.com", "cookies": {}}}
    app.active_route_id = route_id
    app.is_editing_route = True  # Set editing mode
    app.route_counter = 1

    payload = _FakeQueryPayload(app)
    payload.set("#method-select", _FakeWidget("POST"))
    payload.set("#url-input", _FakeWidget("https://new.example.com"))
    payload.set("#request-body", _FakeWidget(""))
    payload.set("#script-input", _FakeWidget(""))
    payload.set("#input-headers", _FakeWidget(""))
    payload.set("#saved-routes-list", app._list_view)
    payload.set("#status-label", _FakeWidget("Status: Ready"))
    payload.install()

    # Mock the list_view.append to avoid MountError
    original_append = app._list_view.append
    app._list_view.append = lambda item: None
    
    try:
        save_current_route(app)
    finally:
        app._list_view.append = original_append

    assert app.saved_routes[route_id]["url"] == "https://new.example.com"
    assert app.saved_routes[route_id]["method"] == "POST"


def test_save_routes_to_file_writes_json(tmp_path: Path, monkeypatch: Any) -> None:
    routes_file = tmp_path / "routes.json"
    # Patch the module-level ROUTES_FILE to use our temp file
    monkeypatch.setattr("RouteStorage.ROUTES_FILE", str(routes_file))
    
    app = _DummyApp(routes_file)
    app.saved_routes = {"route_0": {"url": "https://example.com"}}

    save_routes_to_file(app)

    payload = json.loads(routes_file.read_text(encoding="utf-8"))
    assert payload["route_0"]["url"] == "https://example.com"


def test_load_routes_from_file_reads_json(tmp_path: Path, monkeypatch: Any) -> None:
    routes_file = tmp_path / "saved_routes.json"
    routes_file.write_text(
        json.dumps({"route_99": {"url": "https://loaded.example.com", "method": "POST"}}, indent=2),
        encoding="utf-8",
    )

    # Patch the module-level ROUTES_FILE
    monkeypatch.setattr("RouteStorage.ROUTES_FILE", str(routes_file))

    class _LoadApp:
        def __init__(self) -> None:
            self.saved_routes: dict[str, Any] = {}
            self.route_counter = 0
            self._list_view = ListView(id="saved-routes-list")

        def query_one(self, selector: str, expectation: Any = None) -> Any:
            if selector == "#saved-routes-list":
                return self._list_view
            if selector == "#status-label":
                return type("S", (), {"update": lambda self, msg: None})()
            raise AssertionError(f"unexpected selector: {selector}")

    app = _LoadApp()
    # Mock list_view.clear to avoid LookupError (ListView not in app context)
    app._list_view.clear = lambda: None
    load_routes_from_file(app)

    assert app.saved_routes["route_99"]["url"] == "https://loaded.example.com"
    assert app.saved_routes["route_99"]["method"] == "POST"


def test_save_routes_to_file_handles_write_errors_gracefully(tmp_path: Path, monkeypatch: Any) -> None:
    app = _DummyApp(tmp_path / "unwritable.json")
    app.saved_routes = {"route_0": {}}

    def _raise(*_args: Any, **_kwargs: Any) -> None:
        raise OSError("disk full")

    monkeypatch.setattr(Path, "write_text", _raise)

    app.query_one = lambda selector, expectation=None: type("S", (), {"update": lambda self, msg: None})()

    save_routes_to_file(app)

    assert (tmp_path / "unwritable.json").exists() is False


class _FakeListViewById:
    """ListView mock that stores appended items and supports query_one by id."""
    def __init__(self) -> None:
        self.items: list[Any] = []
        self.cleared = False

    def clear(self) -> None:
        self.items.clear()
        self.cleared = True

    def append(self, item: Any) -> None:
        self.items.append(item)

    def query_one(self, selector: str, expectation: Any = None) -> Any:
        if selector.startswith("#"):
            target_id = selector[1:]
            for item in self.items:
                if getattr(item, "id", None) == target_id:
                    return item
        raise AssertionError(f"query_one: no match for {selector}")

    def query(self, cls: Any) -> Any:
        results = []
        for item in self.items:
            if isinstance(item, cls):
                results.append(item)
            # Also search inside ListItem content
            if hasattr(item, "content"):
                content = item.content
                if isinstance(content, cls):
                    results.append(content)
                if hasattr(content, "children"):
                    for child in content.children:
                        if isinstance(child, cls):
                            results.append(child)
        return results


class _FakeLabel:
    def __init__(self, value: str = "") -> None:
        self.value = value

    def update(self, message: str, markup: bool = True) -> None:
        self.value = message


class _FakeHorizontal:
    def __init__(self) -> None:
        self.children: list[Any] = []

    def query_one(self, selector: str, expectation: Any = None) -> Any:
        for child in self.children:
            if getattr(child, "id", None) == selector.lstrip(".").lstrip("#"):
                return child
            if hasattr(child, "classes") and selector.lstrip(".") in getattr(child, "classes", set()):
                return child
        raise AssertionError(f"query_one: no match for {selector}")


@pytest.mark.asyncio
async def test_save_current_route_updates_label_with_no_matches_path(tmp_path: Path, monkeypatch: Any) -> None:
    """When the list item exists, the label must be updated via query_one().

    This test verifies that the code uses the ListItem.query_one(".route-label")
    path and that NoMatches is the expected exception (not bare Exception).
    """
    monkeypatch.setattr("RouteStorage.ROUTES_FILE", str(tmp_path / "routes.json"))

    list_view = _FakeListViewById()

    # Build a pre-existing ListItem with a route-label
    route_label = _FakeLabel("[GET] https://old.example.com")
    route_label.classes = {"route-label"}

    horizontal = _FakeHorizontal()
    horizontal.children = [route_label]

    list_item = type("FakeListItem", (), {
        "id": "route_1",
        "content": horizontal,
        "query_one": lambda self, sel, exp=None: horizontal.query_one(sel, exp),
    })()
    list_item.query_one = lambda sel, exp=None: horizontal.query_one(sel, exp)

    list_view.items = [list_item]

    class _TestApp:
        def __init__(self) -> None:
            self.saved_routes = {
                "route_1": {
                    "method": "GET",
                    "url": "https://old.example.com",
                    "body": "",
                    "script": "",
                    "headers": "",
                    "cookies": {},
                }
            }
            self.active_route_id = "route_1"
            self.is_editing_route = True
            self.route_counter = 1
            self._status_label_value = "Status: Ready"

        def query_one(self, selector: str, expectation: Any = None) -> Any:
            if selector == "#method-select":
                return _FakeWidget("POST")
            if selector == "#url-input":
                return _FakeWidget("https://new.example.com")
            if selector == "#request-body":
                return _FakeWidget("")
            if selector == "#script-input":
                return _FakeWidget("")
            if selector == "#input-headers":
                return _FakeWidget("")
            if selector == "#saved-routes-list":
                return list_view
            if selector == "#status-label":
                return _FakeLabel(self._status_label_value)
            raise AssertionError(f"unexpected selector: {selector}")

    app = _TestApp()
    save_current_route(app)

    # The label should have been updated by query_one(".route-label", Label).update(...)
    assert route_label.value == "[POST] https://new.example.com"


def test_append_route_row_creates_list_item() -> None:
    """_append_route_row should append a ListItem with the correct ID."""
    list_view = _FakeListViewById()

    class _TestApp:
        def query_one(self, selector: str, expectation: Any = None) -> Any:
            if selector == "#saved-routes-list":
                return list_view
            raise AssertionError(f"unexpected selector: {selector}")

    app = _TestApp()
    _append_route_row(app, "route_42", "DELETE", "https://api.example.com/item/7")

    assert len(list_view.items) == 1
    item = list_view.items[0]
    assert item.id == "route_42"
    assert isinstance(item, ListItem)

    # The ListItem stores the Horizontal in _pending_children (not yet mounted)
    pending = item._pending_children
    assert len(pending) == 1
    horizontal = pending[0]
    assert isinstance(horizontal, Horizontal)

    # The Horizontal stores children in _pending_children before mounting
    h_children = horizontal._pending_children
    assert len(h_children) == 3

    label = h_children[0]
    assert isinstance(label, Label)
    assert "route-label" in label.classes
    rendered = str(label.render())
    assert rendered == "[DELETE] https://api.example.com/item/7"

    edit_btn = h_children[1]
    assert isinstance(edit_btn, Button)
    assert edit_btn.id == "edit_route_42"
    assert edit_btn.variant == "warning"

    del_btn = h_children[2]
    assert isinstance(del_btn, Button)
    assert del_btn.id == "del_route_42"
    assert del_btn.variant == "error"
