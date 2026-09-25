"""Демо-приложение: каждая страница пакета на тестовых данных.

``/demo/<name>`` рендерит ``demo_templates/demo/<name>.html`` — по одному
шаблону на страницу-витрину (настройки, список, вход...). Им пользуются
тесты и снимки экрана при визуальной проверке:
``python tests/demo_app.py`` → http://127.0.0.1:5077/demo/<name>.
"""

from pathlib import Path

from flask import Flask, abort, redirect, render_template, url_for
from jinja2 import TemplateNotFound
from markupsafe import Markup

from venomshadows_ui import NavItem, VenomUI

HERE = Path(__file__).resolve().parent
CSRF_FIELD = '<input type="hidden" name="csrf_token" value="demo-token">'


def create_app() -> Flask:
    app = Flask(__name__, template_folder=str(HERE / "demo_templates"), static_folder=str(HERE / "demo_static"))
    app.config.update(TESTING=True, SECRET_KEY="demo")

    @app.get("/")
    def index():
        return redirect(url_for("demo", name="list"))

    @app.get("/demo/<name>")
    def demo(name: str):
        try:
            return render_template(f"demo/{name}.html")
        except TemplateNotFound:
            abort(404)

    @app.get("/settings")
    def settings_page():
        return render_template("demo/settings.html")

    @app.post("/logout")
    def logout():
        return redirect(url_for("index"))

    VenomUI(
        app,
        service="demo",
        home_endpoint="index",
        logout_endpoint="logout",
        logo="logo.webp",
        nav=[
            NavItem("list", "index", "Бренды", match=("index", "demo")),
            NavItem("settings", "settings_page", "Настройки"),
        ],
        csrf_field=lambda: Markup(CSRF_FIELD),
    )
    return app


if __name__ == "__main__":
    create_app().run(port=5077, debug=True)
