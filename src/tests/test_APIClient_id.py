from __future__ import annotations

from typing import Any

import json
import pytest

from textual.containers import Horizontal
from textual.widgets import Button, Input, Label, ListItem, ListView, Select, Switch, TextArea

# Import after we're ready to patch
import httpx
from APIClient import _run_script_awaitable, extract_and_render_cookies, make_request

import APIClient
import RouteStorage


class _FakeResponseContext:
    def __init__(self, response_factory: Any) -> None:
        self._response_factory = response_factory

    async def __aenter__(self) -> _FakeResponseContext:
        return self

    async def __aexit__(self, *_args: Any) -> None:
        pass

    async def request(self, **kwargs: Any) -> httpx.Response:
        return await self._response_factory(**kwargs)


class _FakeSelect:
    def __init__(self, value: str) -> None:
        self.value = value


class _FakeInput:
    def __init__(self, value: str) -> None:
        self.value = value


class _FakeTextArea:
    def __init__(self, text: str = "", language: str = "json") -> None:
        self.text = text
        self.language = language


class _FakeSwitch:
    def __init__(self, value: bool) -> None:
        self.value = value


class _FakeLabel:
    def __init__(self, value: str = "") -> None:
        self.value = value
        self._classes: set[str] = set()

    def update(self, message: str, markup: bool = True) -> None:
        self.value = message

    def remove_class(self, name: str) -> None:
        self._classes.discard(name)

    def add_class(self, name: str) -> None:
        self._classes.add(name)


class _FakeListView:
    def __init__(self, app: Any) -> None:
        self._app = app
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
        raise AssertionError(f"_FakeListView.query_one: no match for {selector}")

    def query(self, cls: Any) -> Any:
        results = []
        for item in self.items:
            if isinstance(item, cls):
                results.append(item)
            # Also search inside ListItem content (Horizontal)
            if hasattr(item, "content") and hasattr(item.content, "children"):
                for child in item.content.children:
                    if isinstance(child, cls):
                        results.append(child)
        return results


def _make_response(
    status_code: int = 200,
    *,
    json_body: dict[str, Any] | None = None,
    content: bytes = b"",
    headers: dict[str, str] | None = None,
) -> httpx.Response:
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(
        status_code,
        request=request,
        content=content,
        headers=headers or {"content-type": "application/json"},
    )
    if json_body is not None:
        # Set the JSON data so response.json() returns it
        response._json = json_body
        # Also set content to the JSON-encoded bytes
        response._content = json.dumps(json_body).encode()
    return response


class _DummyAppWithRequest:
    def __init__(
        self,
        *,
        method: str = "GET",
        url: str = "https://example.com",
        body_text: str = "",
        headers_text: str = "",
        active_route_id: str | None = None,
        saved_routes: dict[str, Any] | None = None,
        response: httpx.Response | None = None,
        script_text: str = "",
        cookie_switch_value: bool = False,
        cookies_list: Any = None,
    ) -> None:
        self._method = method
        self._url = url
        self._body_text = body_text
        self._headers_text = headers_text
        self.active_route_id = active_route_id
        self.saved_routes = saved_routes or {}
        self._response = response
        self._script_text = script_text
        self._cookie_switch_value = cookie_switch_value
        self.route_counter = 0
        self._script_status = _FakeLabel("Script Execution Status")
        self._status_label = _FakeLabel("Status: Ready")
        self._response_body = _FakeTextArea("")
        self._cookies_list = cookies_list
        self._saved_routes_list = _FakeListView(self)

    def query_one(self, selector: str, expectation: Any = None) -> Any:
        if selector == "#method-select":
            return _FakeSelect(self._method)
        if selector == "#url-input":
            return _FakeInput(self._url)
        if selector == "#request-body":
            return _FakeTextArea(self._body_text)
        if selector == "#input-headers":
            return _FakeTextArea(self._headers_text)
        if selector == "#response-body":
            return self._response_body
        if selector == "#status-label":
            return self._status_label
        if selector == "#switch-save-cookies":
            return _FakeSwitch(self._cookie_switch_value)
        if selector == "#script-input":
            return _FakeTextArea(self._script_text, language="python")
        if selector == ".script-status":
            return self._script_status
        if selector == "#cookies-list":
            if self._cookies_list is not None:
                return self._cookies_list
            return _FakeListView()
        if selector == "#saved-routes-list":
            return self._saved_routes_list
        raise AssertionError(f"unexpected selector: {selector}")


@pytest.mark.asyncio
async def test_make_request_rejects_empty_url(monkeypatch: Any) -> None:
    # Mock httpx.AsyncClient to avoid actual HTTP calls
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def request(self, *args, **kwargs):
            raise Exception("should not be called")
    
    # Patch at the module level where it's used
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    app = _DummyAppWithRequest(url="")
    await make_request(app)
    assert app.query_one("#status-label").value == "Status: Error - URL cannot be empty"


@pytest.mark.asyncio
async def test_make_request_returns_response_text_when_not_json(monkeypatch: Any) -> None:
    resp = _make_response(200, content=b"hello", headers={"content-type": "text/plain"})
    
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def request(self, **kwargs):
            return resp
    
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    app = _DummyAppWithRequest(url="https://example.com")
    await make_request(app)
    assert app.query_one("#status-label").value == "Status: 200 OK"
    assert app.query_one("#response-body").text == "hello"


@pytest.mark.asyncio
async def test_make_request_formats_json_response(monkeypatch: Any) -> None:
    resp = _make_response(200, json_body={"ok": True})
    
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def request(self, **kwargs):
            return resp
    
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    app = _DummyAppWithRequest(url="https://example.com")
    await make_request(app)
    # The response body should contain formatted JSON
    response_text = app.query_one("#response-body").text
    assert response_text == '{\n  "ok": true\n}' or '"ok": true' in response_text


@pytest.mark.asyncio
async def test_make_request_handles_request_exception(monkeypatch: Any) -> None:
    class _FakeAsyncClient:
        def __init__(self, *args, **kwargs):
            pass
        async def __aenter__(self):
            return self
        async def __aexit__(self, *args):
            pass
        async def request(self, *args, **kwargs):
            raise Exception("network error")
    
    monkeypatch.setattr(httpx, "AsyncClient", _FakeAsyncClient)
    app = _DummyAppWithRequest(url="https://example.com")
    await make_request(app)
    assert app.query_one("#status-label").value == "Status: Request Failed"


@pytest.mark.asyncio
async def test_make_request_invalid_json_body() -> None:
    app = _DummyAppWithRequest(method="POST", body_text="{not json")
    await make_request(app)
    assert app.query_one("#status-label").value.startswith("Status: Invalid JSON body")


@pytest.mark.asyncio
async def test_extract_and_render_cookies_saves_cookies_when_switch_on(tmp_path: Any, monkeypatch: Any) -> None:
    resp = _make_response(200, json_body={"ok": True})
    resp.cookies["session"] = "abc"

    route_id = "route_2"
    saved_routes = {route_id: {"cookies": {}}}
    app = _DummyAppWithRequest(
        url="https://example.com",
        active_route_id=route_id,
        saved_routes=saved_routes,
        cookie_switch_value=True,
    )
    app.ROUTES_FILE = str(tmp_path / "saved_routes.json")
    
    # Mock save_routes_to_file and render_cookies_list
    monkeypatch.setattr("APIClient.save_routes_to_file", lambda self: None)
    monkeypatch.setattr("APIClient.render_cookies_list", lambda *args, **kwargs: None)

    await extract_and_render_cookies(app, response=resp)

    assert saved_routes[route_id]["cookies"]["session"] == "abc"


@pytest.mark.asyncio
async def test_extract_and_render_cookies_skips_when_switch_off(tmp_path: Any, monkeypatch: Any) -> None:
    resp = _make_response(200, json_body={"ok": True})
    resp.cookies["session"] = "abc"

    route_id = "route_3"
    saved_routes = {route_id: {"cookies": {}}}
    app = _DummyAppWithRequest(
        url="https://example.com",
        active_route_id=route_id,
        saved_routes=saved_routes,
        cookie_switch_value=False,
    )
    app.ROUTES_FILE = str(tmp_path / "saved_routes.json")
    
    # Mock render_cookies_list to do nothing
    monkeypatch.setattr("views.RenderCookiesList.render_cookies_list", lambda *args, **kwargs: None)

    await extract_and_render_cookies(app, response=resp)

    assert saved_routes[route_id]["cookies"] == {}


@pytest.mark.asyncio
async def test_run_script_awaitable_is_async_wrapper(monkeypatch: Any) -> None:
    app = _DummyAppWithRequest(url="https://example.com", script_text="x = 1")
    app._script_called: bool = False

    async def _fake_execute_script(self_ref: Any, response: Any) -> None:
        app._script_called = True

    # Mock execute_script in APIClient module where it's imported
    monkeypatch.setattr("APIClient.execute_script", _fake_execute_script)
    await _run_script_awaitable(app, None)

    assert app._script_called is True


@pytest.mark.asyncio
async def test_make_request_appends_ui_row_for_new_route() -> None:
    """New routes created during make_request should append a UI row.

    Verifies the refactoring that moved UI row creation into _append_route_row.
    """
    app = _DummyAppWithRequest(url="https://example.com")
    await make_request(app)

    # A new route entry should have been created
    assert app.active_route_id is not None
    assert app.active_route_id in app.saved_routes

    # The UI row should have been appended
    list_view = app.query_one("#saved-routes-list", ListView)
    items = list_view.query(ListItem)
    assert len(items) == 1

    # The ListItem should have a matching ID
    list_item = items[0]
    assert list_item.id == app.active_route_id

    # The ListItem should have the Horizontal as a pending child
    # (the Horizontal was passed to ListItem() but not yet mounted in the DOM)
    pending = list_item._pending_children
    assert len(pending) == 1
    horizontal = pending[0]
    assert isinstance(horizontal, Horizontal)

    # The Horizontal stores children in _pending_children before mounting
    h_children = horizontal._pending_children
    assert len(h_children) == 3

    label = h_children[0]
    assert isinstance(label, Label)
    assert "route-label" in label.classes
    # Label text is only available via render() before mounting; verify the renderable
    rendered = str(label.render())
    assert "[GET] https://example.com" in rendered

    edit_btn = h_children[1]
    assert isinstance(edit_btn, Button)
    assert edit_btn.id == f"edit_{app.active_route_id}"
    assert edit_btn.variant == "warning"

    del_btn = h_children[2]
    assert isinstance(del_btn, Button)
    assert del_btn.id == f"del_{app.active_route_id}"
    assert del_btn.variant == "error"


@pytest.mark.asyncio
async def test_make_request_does_not_create_duplicate_row_for_existing_route() -> None:
    """When active_route_id already exists, no new UI row should be appended."""
    app = _DummyAppWithRequest(
        url="https://example.com",
        active_route_id="route_99",
        saved_routes={"route_99": {"url": "https://example.com", "method": "GET"}},
    )
    initial_count = len(app.query_one("#saved-routes-list", ListView).query(ListItem))

    await make_request(app)

    list_view = app.query_one("#saved-routes-list", ListView)
    final_count = len(list_view.query(ListItem))
    assert final_count == initial_count
