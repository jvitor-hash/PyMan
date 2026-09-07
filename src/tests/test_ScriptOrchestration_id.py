from __future__ import annotations

from typing import Any

import httpx
import pytest

from textual.widgets import Label, TextArea

from ScriptOrchestration import _ALLOWLIST, _make_sandbox_globals, execute_script, parse_script


class _FakeTextArea:
    def __init__(self, text: str) -> None:
        self.text = text
        self.language = "python"


class _FakeLabel:
    def __init__(self, text: str = "") -> None:
        self.text = text
        self._classes: set[str] = set()

    def update(self, message: str) -> None:
        self.text = message

    def remove_class(self, name: str) -> None:
        self._classes.discard(name)

    def add_class(self, name: str) -> None:
        self._classes.add(name)


class _DummyApp:
    def __init__(self, script_text: str = "", script_status_text: str = "Script Execution Status") -> None:
        self.script_text = script_text
        self._script_status = _FakeLabel(script_status_text)

    def query_one(self, selector: str, expectation: Any = None) -> Any:
        if selector == "#script-input":
            return _FakeTextArea(self.script_text)
        if selector == ".script-status":
            return self._script_status
        raise AssertionError(f"unexpected query selector: {selector}")


def _make_response(status_code: int = 200, json_body: dict[str, Any] | None = None) -> httpx.Response:
    request = httpx.Request("GET", "https://example.com")
    response = httpx.Response(
        status_code,
        request=request,
        content=b"",
        headers={"content-type": "application/json"},
    )
    if json_body is not None:
        response._json = json_body
    return response


def _make_response_non_json(status_code: int = 200) -> httpx.Response:
    request = httpx.Request("GET", "https://example.com")
    return httpx.Response(
        status_code,
        request=request,
        content=b"hello",
        headers={"content-type": "text/plain"},
    )


@pytest.mark.asyncio
async def test_parse_script_reports_syntax_error() -> None:
    app = _DummyApp(script_text="def f(\n")
    await parse_script(app)
    assert app._script_status.text.startswith("Syntax Error:")


@pytest.mark.asyncio
async def test_parse_script_clears_error_on_valid_script() -> None:
    app = _DummyApp(script_text="x = 1\n", script_status_text="Syntax Error: dummy")
    await parse_script(app)
    assert app._script_status.text == "Script Execution Status"


def test_make_sandbox_globals_restricts_builtins() -> None:
    response = _make_response(200, {"ok": True})
    sandbox = _make_sandbox_globals(response)

    assert sandbox["__builtins__"].keys() <= set(_ALLOWLIST)
    assert "__import__" not in sandbox["__builtins__"]
    assert sandbox["response"].status_code == 200
    assert sandbox["json_data"] == {"ok": True}


def test_make_sandbox_globals_handles_none_response() -> None:
    sandbox = _make_sandbox_globals(None)
    assert sandbox["response"] is None
    assert sandbox["status_code"] is None
    assert sandbox["json_data"] is None
    assert sandbox["headers"] == {}
    assert sandbox["cookies"] is None
    assert sandbox["print"] is print


def test_make_sandbox_globals_non_json_sets_cookies_none() -> None:
    response = _make_response_non_json()
    sandbox = _make_sandbox_globals(response)
    assert sandbox["cookies"] is None


@pytest.mark.asyncio
async def test_execute_script_reports_no_script() -> None:
    app = _DummyApp(script_text="")
    await execute_script(app, _make_response())
    assert app._script_status.text == "No script provided"


@pytest.mark.asyncio
async def test_execute_script_reports_success_with_output() -> None:
    app = _DummyApp(script_text="print('hello')\n")
    await execute_script(app, _make_response())
    assert app._script_status.text.startswith("Output: hello")


@pytest.mark.asyncio
async def test_execute_script_reports_success_without_output() -> None:
    app = _DummyApp(script_text="x = 1\n")
    await execute_script(app, _make_response())
    assert app._script_status.text == "✓ Script executed successfully"


@pytest.mark.asyncio
async def test_execute_script_reports_failure() -> None:
    # Use ZeroDivisionError which doesn't require naming the exception class
    app = _DummyApp(script_text="1/0\n")
    await execute_script(app, _make_response())
    assert app._script_status.text.startswith("Failed: ZeroDivisionError: division by zero")
    assert "script-failed" in app._script_status._classes


@pytest.mark.asyncio
async def test_execute_script_allows_response_json_access() -> None:
    app = _DummyApp(script_text="print(json_data['ok'])\n")
    await execute_script(app, _make_response(200, {"ok": True}))
    assert app._script_status.text.startswith("Output: True")


@pytest.mark.asyncio
async def test_execute_script_blocks_import() -> None:
    app = _DummyApp(script_text="import os\n")
    await execute_script(app, _make_response())
    assert app._script_status.text.startswith("Failed:")
