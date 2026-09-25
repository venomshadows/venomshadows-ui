"""SVG-иконки интерфейса.

Файлы ``icons/<имя>.svg`` — иконки Lucide (ISC, см. ``icons/LICENSE``).
Из файла берётся только содержимое ``<svg>``: размер, толщина линии и цвет
одинаковы для всех иконок и задаются здесь, поэтому иконка подстраивается под
шрифт и цвет кнопки (1.25em, ``currentColor``). Иконка декоративная —
действие называет подпись или ``aria-label`` кнопки.
"""

from __future__ import annotations

import re
from functools import cache
from importlib.resources import files

from markupsafe import Markup, escape

_INNER = re.compile(r"<svg\b[^>]*>(.*)</svg>", re.S)
_ATTRS = (
    'viewBox="0 0 24 24" width="1.25em" height="1.25em" fill="none" '
    'stroke="currentColor" stroke-width="1.75" stroke-linecap="round" '
    'stroke-linejoin="round" aria-hidden="true" focusable="false"'
)


def _icons_dir():
    return files(__package__) / "icons"


@cache
def icon_names() -> frozenset[str]:
    return frozenset(p.name.removesuffix(".svg") for p in _icons_dir().iterdir() if p.name.endswith(".svg"))


@cache
def _body(name: str) -> str:
    if name not in icon_names():
        raise KeyError(f"Неизвестная иконка {name!r}; есть: {', '.join(sorted(icon_names()))}")
    match = _INNER.search((_icons_dir() / f"{name}.svg").read_text(encoding="utf-8"))
    return re.sub(r">\s+<", "><", match.group(1).strip())


def icon(name: str, class_: str = "") -> Markup:
    """``<svg class="icon ...">`` по имени файла; неизвестное имя — ошибка, а не пустое место."""
    classes = f"icon {escape(class_)}".strip()
    return Markup(f'<svg class="{classes}" {_ATTRS}>{_body(name)}</svg>')
