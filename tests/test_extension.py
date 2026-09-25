import pytest
from flask import Flask

from venomshadows_ui import NavItem, VenomUI
from venomshadows_ui.icons import icon, icon_names


@pytest.mark.parametrize("endpoint,pattern,expected", [
    ("settings_page", "settings_page", True),
    ("settings_page_x", "settings_page", False),
    ("drops.index", "drops.", True),
    ("dropsx.index", "drops.", False),
    ("brand_texts", "brand_", True),
    (None, "index", False),
])
def test_nav_item_matching(endpoint, pattern, expected):
    assert NavItem("k", "index", "L", match=(pattern,)).is_active(endpoint) is expected


def test_nav_item_defaults_to_own_endpoint():
    item = NavItem("k", "settings_page", "L")
    assert item.is_active("settings_page") and not item.is_active("index")


def test_active_nav_from_endpoint_and_override(app):
    ui = app.extensions["venom_ui"]
    with app.test_request_context("/settings"):
        assert ui.active_nav() == "settings"
        assert ui.active_nav("list") == "list"


@pytest.mark.parametrize("nav", [[], [NavItem("a", "x", "A"), NavItem("a", "y", "B")]])
def test_invalid_nav_rejected(nav):
    with pytest.raises(ValueError):
        VenomUI(Flask(__name__), service="s", nav=nav, home_endpoint="x", logout_endpoint="y", logo="l")


def test_static_is_served_with_version(client, app):
    ui = app.extensions["venom_ui"]
    with app.test_request_context():
        url = ui.static("tokens.css")
    assert url.startswith("/_ui/tokens.css?v=")
    assert client.get(url).status_code == 200


def test_icon_known_and_unknown():
    assert "chevrons-up-down" in icon_names()
    assert icon("x", 'a"b').startswith('<svg class="icon a&#34;b"')
    with pytest.raises(KeyError):
        icon("no-such-icon")


def test_icon_global_available_in_templates(render):
    assert 'class="icon"' in render("{{ venom_icon('check') }}")
