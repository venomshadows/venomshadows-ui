import pytest

from demo_app import create_app


@pytest.fixture
def app():
    return create_app()


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
