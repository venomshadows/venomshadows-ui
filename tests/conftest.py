import os
from pathlib import Path
from threading import Thread

import pytest
from werkzeug.serving import make_server

import demo_list_routes


@pytest.fixture
def app():
    return demo_list_routes.create_app()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def render(app):
    """Отрендерить строку-шаблон в контексте запроса (для проверки макросов)."""

    def _render(source: str, path: str = "/", **context) -> str:
        with app.test_request_context(path):
            return app.jinja_env.from_string(source).render(**context)

    return _render


@pytest.fixture(scope="session")
def browser():
    channel = os.environ.get("VENOM_UI_BROWSER")
    if not channel:
        pytest.skip("Set VENOM_UI_BROWSER to run browser checks")
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch(channel=None if channel == "chromium" else channel)
        yield browser
        browser.close()


@pytest.fixture(scope="session")
def live_url(browser):
    server = make_server("127.0.0.1", 0, demo_list_routes.create_app(), threaded=True)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}"
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()


@pytest.fixture
def page(browser):
    context = browser.new_context(reduced_motion="reduce")
    page = context.new_page()
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    yield page
    context.close()
    assert not errors


@pytest.fixture
def screenshot():
    def save(page, name):
        if folder := os.environ.get("VENOM_UI_SCREENSHOTS"):
            path = Path(folder)
            path.mkdir(parents=True, exist_ok=True)
            page.screenshot(path=str(path / f"{name}.png"), full_page=True)
    return save
