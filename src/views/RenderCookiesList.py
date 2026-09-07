import re

from textual.containers import Horizontal
from textual.widgets import (
    Button,
    Label,
    ListItem,
    ListView,
)

# Textual widget ids are stricter than normal string keys. Cookie names like
# "sails.sid" are valid dict keys but invalid widget ids, so we normalize them
# into a safe suffix for widget id generation while still preserving cookie
# identity through the original name-based cookie_uid.
_COOKIE_ID_RE = re.compile(r"[^A-Za-z0-9_\-]")


def _safe_cookie_widget_suffix(name: str) -> str:
    """Return a widget-id-safe suffix derived from a cookie name.

    Invalid characters are replaced with underscores, and a leading digit is
    avoided by prefixing with "c" when needed.
    """
    suffix = _COOKIE_ID_RE.sub("_", name).strip("_")
    if not suffix:
        suffix = "cookie"
    if suffix[0].isdigit():
        suffix = f"c{suffix}"
    return suffix


def render_cookies_list(self, cookies: dict) -> None:
    """Helper method to clear and redraw the ListView with current route cookies.

    Each cookie row gets a stable identifier (`cookie_uid`) based on the cookie
    name so that repeated renders do not leak stale IDs or require a global
    counter. Widget ids use a sanitized suffix plus a per-render sequence so
    repeated renders cannot insert duplicate widget ids.
    """
    cookies_list = self.query_one("#cookies-list", ListView)
    cookies_list.clear()

    for index, (name, value) in enumerate(cookies.items()):
        cookie_uid = f"cookie_{name}"
        cookie_widget_suffix = _safe_cookie_widget_suffix(name)
        render_seq = index

        item_id = f"item_{cookie_widget_suffix}_{render_seq}"
        button_id = f"del_cookie_{cookie_widget_suffix}_{render_seq}"

        cookie_label = Label(f"{name}={value}", classes="cookie-label")
        cookie_label.can_wrap = True
        cookie_label.overflow = "fold"

        item_content = Horizontal(
            cookie_label,
            Button(
                "Delete",
                id=button_id,
                variant="error",
                classes="action-btn",
            ),
            classes="cookie-row",
        )

        item = ListItem(item_content, id=item_id)
        item.cookie_name = name
        item.cookie_uid = cookie_uid
        cookies_list.append(item)
