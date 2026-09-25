"""Общий интерфейс сервисов venomshadows (brand, index, complaints, rkn, site).

Пакет — Flask-расширение: регистрирует blueprint ``venom_ui`` с шаблонами
(``venom_ui/*.html``) и статикой (``/_ui/...``) и отдаёт шаблонам объект
``venom_ui`` с настройками конкретного сервиса. Всё, что различается между
сервисами (пункты меню, логотип, эндпоинты, CSRF), передаётся здесь, а не
копируется в шаблоны проектов.

Подключение в приложении проекта::

    VenomUI(app, service="brand", home_endpoint="index",
            logout_endpoint="logout", logo="brand/logo.webp",
            nav=[NavItem("brands", "index", "Бренды", match=("index", "brand_")),
                 NavItem("settings", "settings_page", "Настройки")])
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass

from flask import Blueprint, Flask, has_request_context, request, url_for
from markupsafe import Markup

from .icons import icon

__all__ = ["NavItem", "VenomUI", "__version__"]

__version__ = "0.1.2"

EXTENSION_KEY = "venom_ui"


@dataclass(frozen=True)
class NavItem:
    """Пункт верхнего меню.

    ``match`` — эндпоинты, на которых пункт активен: точное имя
    (``"settings_page"``) или префикс с точкой на конце для целого blueprint
    (``"drops."``) либо с подчёркиванием для семейства view (``"brand_"``).
    Пустой ``match`` — активен только на своём ``endpoint``.
    """

    key: str
    endpoint: str
    label: str
    match: tuple[str, ...] = ()

    def is_active(self, endpoint: str | None) -> bool:
        if not endpoint:
            return False
        return any(_endpoint_matches(endpoint, pattern) for pattern in self.match or (self.endpoint,))


def _endpoint_matches(endpoint: str, pattern: str) -> bool:
    if pattern.endswith((".", "_")):
        return endpoint.startswith(pattern)
    return endpoint == pattern


@dataclass(frozen=True)
class UIContext:
    """То, что шаблоны пакета видят как ``venom_ui``."""

    service: str
    nav: tuple[NavItem, ...]
    home_endpoint: str
    logout_endpoint: str
    logo: str
    csrf_field: Callable[[], str] | None
    version: str = __version__

    @property
    def logo_alt(self) -> str:
        return f"venom_shadows {self.service}"

    def static(self, filename: str) -> str:
        """URL статики пакета; версия в запросе сбрасывает кэш браузера при обновлении."""
        return url_for(f"{EXTENSION_KEY}.static", filename=filename, v=self.version)

    def logo_url(self) -> str:
        return url_for("static", filename=self.logo)

    def csrf(self) -> Markup:
        return Markup(self.csrf_field()) if self.csrf_field else Markup("")

    def active_nav(self, override: str | None = None) -> str | None:
        """Ключ активного пункта меню: явный ``nav_active`` страницы или по эндпоинту."""
        if override:
            return override
        endpoint = request.endpoint if has_request_context() else None
        return next((item.key for item in self.nav if item.is_active(endpoint)), None)


class VenomUI:
    def __init__(self, app: Flask | None = None, **options) -> None:
        if app is not None:
            self.init_app(app, **options)

    def init_app(
        self,
        app: Flask,
        *,
        service: str,
        nav: Iterable[NavItem],
        home_endpoint: str,
        logout_endpoint: str,
        logo: str,
        csrf_field: Callable[[], str] | None = None,
    ) -> UIContext:
        context = UIContext(
            service=service,
            nav=tuple(nav),
            home_endpoint=home_endpoint,
            logout_endpoint=logout_endpoint,
            logo=logo,
            csrf_field=csrf_field,
        )
        if not context.nav:
            raise ValueError("VenomUI: пустое меню — нужен хотя бы один NavItem")
        keys = [item.key for item in context.nav]
        if len(set(keys)) != len(keys):
            raise ValueError(f"VenomUI: повторяющиеся ключи меню {keys}")

        app.register_blueprint(
            Blueprint(
                EXTENSION_KEY,
                __name__,
                template_folder="templates",
                static_folder="static",
                static_url_path="/_ui",
            )
        )
        app.extensions[EXTENSION_KEY] = context
        # Глобалы, а не context_processor: макросы пакета импортируются без
        # «with context» и видят только глобалы окружения Jinja.
        app.add_template_global(context, EXTENSION_KEY)
        app.add_template_global(icon, "venom_icon")
        return context
