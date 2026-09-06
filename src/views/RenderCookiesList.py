from textual.containers import Horizontal
from textual.widgets import (
    Button,
    Label,
    ListItem,
    ListView,
)


def render_cookies_list(self, cookies: dict) -> None:
    """Helper method to clear and redraw the ListView with current route cookies."""
    cookies_list = self.query_one("#cookies-list", ListView)
    cookies_list.clear()

    for name, value in cookies.items():
        self.cookie_counter += 1
        cookie_id = f"ck_{self.cookie_counter}"

        item_content = Horizontal(
            Label(f"{name}={value}", classes="cookie-label"),
            Button(
                "Delete",
                id=f"del_cookie_{cookie_id}",
                variant="error",
                classes="action-btn",
            ),
            classes="cookie-row",
        )

        item = ListItem(item_content, id=f"item_{cookie_id}")
        setattr(item, "cookie_name", name)
        cookies_list.append(item)
