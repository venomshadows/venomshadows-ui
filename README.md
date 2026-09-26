# venomshadows-ui

Общий интерфейс Flask-сервисов venomshadows: локальный Roboto, дизайн-токены,
SVG-иконки, каркасы Jinja, формы, уведомления и поведение браузера.
Пакет отвечает за отображение; проверка прав, валидация и сохранение данных
остаются в приложении сервиса.

## Установка и подключение

В `pyproject.toml` проекта:

```toml
[project]
dependencies = [
  "venomshadows-ui @ git+https://github.com/venomshadows/venomshadows-ui@v0.1.3",
]
```

```python
from flask import Flask
from markupsafe import Markup, escape
from flask_wtf.csrf import generate_csrf
from venomshadows_ui import NavItem, VenomUI

app = Flask(__name__)
# Маршруты index, settings_page и logout регистрируются самим сервисом.
VenomUI(
    app,
    service="brand",
    home_endpoint="index",
    logout_endpoint="logout",
    logo="brand/logo.webp",
    nav=[
        NavItem("brands", "index", "Бренды", match=("index", "brand_")),
        NavItem("settings", "settings_page", "Настройки"),
    ],
    csrf_field=lambda: Markup(
        '<input type="hidden" name="csrf_token" value="{}">'
    ).format(escape(generate_csrf())),
)
```

Пример CSRF использует Flask-WTF из приложения; пакет не навязывает библиотеку.
Хук `csrf_field` должен возвращать доверенную разметку с экранированным значением.
Без хука `venom_ui.csrf()` возвращает пустую строку. Сам хук не проверяет токен:
проверку POST-запросов, включая выход, настраивает сервис.
Для фабрики приложения доступны `ui = VenomUI()` и `ui.init_app(app, ...)`.
`match` принимает точное имя endpoint, префикс blueprint с точкой или семейство
view с подчёркиванием на конце. В шаблоне `nav_active` переопределяет выбор.

Логотип берётся из `static` приложения. Там же должны находиться
`favicon/favicon-32.png`, `favicon/favicon-16.png`, `favicon/apple-touch-icon.png`.
Статика пакета доступна через `venom_ui.static('ui.css')`, обычно по `/_ui/`.
Порядок стилей: `tokens.css`, `ui.css`, `list.css`, затем блок `head` сервиса.
Скрипты `ui.js` и `list.js` подключены с `defer`; код страницы размещайте
в отдельном скрипте с `defer` через блок `scripts`.

## Страница

```jinja
{% extends "venom_ui/app.html" %}
{% import "venom_ui/macros.html" as ui %}
{% set nav_active = 'settings' %}
{% block title %}Настройки{% endblock %}
{% block content %}
<div class="page">
  {{ ui.page_header('Настройки', lead='Параметры подключения.') }}
  <div class="settings-stack">
    {% call ui.settings_section('telegram', 'Telegram', configured,
        action=url_for('settings_save'), section='telegram') %}
      <div class="field-grid">
        {{ ui.field('token', 'Токен бота', value=token) }}
        {{ ui.field('chat_id', 'Chat ID', value=chat_id) }}
      </div>
      {{ ui.settings_actions() }}
    {% endcall %}
  </div>
</div>
{% endblock %}
```

Блок `sidebar` содержит только содержимое бокового меню: каркас `aside`,
заголовок из `sidebar_title`, бургер и подложку добавляет `app.html`.
Пустой блок не создаёт ни меню, ни бургер. Блок `subnav` расположен перед
уведомлениями, `content` — после. Заголовок и сетка страницы не добавляют
ограничения максимальной ширины.

Для входа расширяйте `venom_ui/auth.html`, задавайте `auth_step`, `auth_total`,
`auth_labels` и блок `auth_content`. Для собственного каркаса используйте
`venom_ui/base.html` и блок `body`.

## Макросы

Импорт: `{% import "venom_ui/macros.html" as ui %}`; `with context` не нужен.
Вызовы с содержимым оформляются через `{% call ui.…(...) %}…{% endcall %}`.

| Макрос | Назначение |
| --- | --- |
| `icon(name, class_='')` | Декоративная SVG-иконка из набора пакета. |
| `logo(context='topbar')` | Логотип сервиса с общей маской. |
| `engine_logo(engine)` | Логотип `yandex` или `google` размером 20px. |
| `topbar(active=None, burger=False)` | Реестр навигации и POST-выход с CSRF. |
| `sidebar(title)` | Каркас бокового меню; содержимое через caller. |
| `subnav(items, active)` | Вкладки из `(key, url, label[, engine])`. |
| `page_header(title, count=None, lead=None)` | Заголовок, счётчик и описание; caller для действий необязателен. |
| `btn(label, variant='primary', type='submit', icon=None, small=False, attrs={})` | Кнопка; варианты `primary`, `secondary`, `danger`, дополнительные атрибуты через словарь. |
| `field(name, label, value='', type='text', hint=None, error=None, placeholder='', required=False, attrs={})` | Поле с подписью и связанными подсказкой/ошибкой; `attrs.id` переопределяет id. |
| `checkbox(name, label, checked=False, hint=None, error=None, required=False, attrs={})` | Флажок с кликабельной строкой и значением `1`. |
| `select(name, label, options, selected=None, hint=None, error=None, required=False, attrs={})` | Выбор из пар `(value, label)`. |
| `textarea(name, label, value='', rows=4, hint=None, error=None, placeholder='', required=False, attrs={})` | Многострочный ввод с нативной проверкой обязательности. |
| `secret_field(name, label, has_value, placeholder_hint='', clearable=False, hint=None, error=None, required=False, attrs={})` | Пустое поле замены SMTP-пароля; флажок очистки называется `<name>__clear`. |
| `icon_button(icon, label, variant=None, compact=False, attrs={})` | Кнопка с иконкой; соседние контролы размещайте во flex-контейнере с `align-items: center; gap: .5rem` минимум, чтобы зона нажатия 44px не перекрывала их. |
| `copy_button(target_id, label='Копировать')` | Копирование поля или текста элемента по id. |
| `api_key_block(key, id='api-key')` | Ключ целиком в `pre` с копированием; пустой ключ не выводится. |
| `file_picker(name, id, label, multiple=False, accept='', required=False, hint=None, error=None, attrs={})` | Настоящий file input с русскими подписями и статусом выбора. |
| `state_marker(on, on_text='Настроено', off_text='Не настроено')` | Точка и текст состояния подключения. |
| `status_pill(tone, label, icon=None)` | Плашка `success`, `danger`, `warning`, `partial`, `accent` или `neutral`. |
| `settings_section(id, title, marker_on, marker_on_text='Настроено', marker_off_text='Не настроено', hint=None, action=None, section=None, form_attrs={})` | Панель с caller; при `action` добавляет POST-форму, CSRF и скрытое поле `section` (по умолчанию id). |
| `settings_actions(save_label='Сохранить', test_label=None, test_action=None)` | Сохранение и дополнительная проверка через `formaction` той же формы. |
| `flash_stack()` | Flash-сообщения Flask; уже вызывается каркасом приложения. |
| `banner(category, text, details=None, actions=None, closable=True, inline=False)` | Уведомление с SVG и необязательными подробностями (строка или список). |
| `empty_state(title, text=None, icon='inbox')` | Пустое состояние; caller для действия необязателен. |
| `modal(id, title)` | Нативный dialog с caller и кнопкой закрытия. |
| `confirm_dialog()` | Общий диалог подтверждения; уже включён один раз в app. |
| `auth_steps(current, total, labels)` | Нумерованные с единицы шаги входа. |

Макросы списков импортируются отдельно: `{% import "venom_ui/list.html" as list %}`.

| Макрос из `list.html` | Назначение |
| --- | --- |
| `filter_bar(target, …)`, `search(…)`, `chips(…)`, `dropdown(…)`, `input(…)` | Панель поиска и фильтров; содержимое панели через caller. |
| `data_table(id, columns, …, select_name=None, reveal_on_filter=False)`, `sort_th(…)` | Таблица с сортировкой; строки через caller. |
| `row_attrs(…)`, `select_cell(id, label, name=None)` | Данные строки и флажок выбора; name включает отправку id формой. |
| `bulk_bar(target, …)`, `lazy_sentinel(target)`, `empty_row(colspan, …)` | Массовые действия, постепенное раскрытие и пустое состояние. |

Категории баннеров: `success`, `info`, `warning`, `error`; `danger` отображается
как `error`, `message` и неизвестные категории — как `info`. Текст и атрибуты
экранирует Jinja. Не передавайте непроверенный `Markup` в макросы.

SMTP-пароль никогда не передавайте в шаблон: `has_value` — только булево значение.
На сервере пустое поле должно сохранять прежний пароль; `<name>__clear=1`
должно удалять его. Telegram-токены и API-ключи всегда видимы: `field(type='text')`
или `api_key_block`. Действия выпуска и отзыва задаёт сервис отдельными кнопками.
Базовое правило полей использует `:where()` и специфичность элемента: `[aria-invalid="true"]` / `:user-invalid` задают рамку ошибки, а `:focus-visible` — рамку фокуса.

Формы нельзя вкладывать в `settings_section` с заполненным `action`.

## Поведение ui.js

| Атрибут | Контракт |
| --- | --- |
| `data-confirm="Текст"` | На форме или кнопке: запрос подтверждения; атрибут кнопки приоритетнее формы, повторная отправка сохраняет submitter и браузерную валидацию. |
| `data-confirm-ok="Удалить"` | Подпись подтверждения (по умолчанию «Продолжить»). |
| `data-confirm-danger` | Присутствие атрибута включает опасный вариант кнопки. |
| `data-busy-label="Сохраняется…"` | На форме или submitter: блокирует повторную отправку, меняет подпись и aria-busy; `pageshow` восстанавливает прежние состояния. |
| `data-copy-target="id"` | На кнопке: копирует value поля или textContent; обратная связь на 1,5 секунды, без Clipboard API использует выделение и execCommand. |
| `data-sidebar-toggle` / `data-sidebar-close` | Открытие и закрытие drawer: aria-expanded, inert, Escape, удержание и возврат фокуса; от 861px закрывается автоматически. |
| `data-banner-close` | Удаляет ближайший `data-banner` и пустой `data-flash-stack`. |
| `data-file-input="status-id"` / `data-file-status` | Связывает file input со статусом; `data-empty-text` задаёт пустой статус; change, reset и pageshow обновляют его. |
| `data-dialog-open="id"` / `data-dialog-close` | Открывает dialog по id или закрывает ближайший dialog. |

Макросы проставляют служебные атрибуты сами. У кнопок только с иконкой обязательно
задайте `aria-label`. Для AJAX код проекта может отменить submit через
`preventDefault()`; автоматический busy тогда не включается. На страницах без
`confirm_dialog()` подтверждение использует нативный `window.confirm`.
Программная отправка, которая должна пройти подтверждение, использует
`form.requestSubmit(button)`, поскольку `form.submit()` обходит события браузера.

Единственный глобальный объект — `window.VenomUI`:
`copyFrom(button)`, `resetBusy(form)`, `setSidebarOpen(open, restoreFocus=true)`,
`updateFileStatus(input)`. Это вспомогательные функции для страниц с динамическим
DOM; обычным страницам достаточно data-атрибутов.

## Правила оформления

- Размеры текста: только `--text-caption`, `--text-sm`, `--text-base`,
  `--text-heading`, `--text-title`; вес — `--weight-regular` или `--weight-medium`.
- Цвета компонентов берите из смысловых `--color-*`, размеры и тени — из токенов.
  `code` и `kbd` допускают `.85em`. Uppercase только у подписей полей и шапки таблицы.
- Иконки — `venom_icon` / `ui.icon`, без эмодзи и текстовых значков.
- Брейкпоинты: 860, 699, 640, 480 и 360px; нижние границы диапазонов — на 1px выше.
  `pointer: fine` разрешает компактным кнопкам 36px, остальные имеют минимум 44px.
- Сайдбар — `--sidebar-w`; поля секции — `.field-grid`; на телефоне одна колонка.
- Шрифт хранится в пакете, внешние Google Fonts не нужны. Уменьшенное движение
  отключает фоновые анимации, переходы и спиннер.

## Демо и проверки

```powershell
python -m venv .venv
.venv\Scripts\pip install -e .[test]
.venv\Scripts\python tests\demo_app.py
```

Страницы: `http://127.0.0.1:5077/demo/settings`, `/demo/components`,
`/demo/sidebar`, `/demo/login`, `/demo/list`, `/demo/list-server`, `/demo/cards`. Формы демонстрируют разметку; обработчиков
сохранения, проверки подключений и авторизации в демо нет.

```powershell
.venv\Scripts\python -m pytest -q
# Необязательные проверки поведения и ширин 1600/860/360 в браузере:
.venv\Scripts\pip install playwright
.venv\Scripts\python -m playwright install chromium
$env:VENOM_UI_BROWSER = 'chromium' # или установленный chrome / msedge
$env:VENOM_UI_SCREENSHOTS = 'C:\Temp\venom-ui-screenshots' # необязательно
.venv\Scripts\python -m pytest -q
```

CSS-проверки охватывают все `static/*.css`, включая слой списков, а проверка
упаковки требует наличия каждого ресурса, на который ссылаются шаблоны.
Числовой `font-weight` внутри `@font-face` — обязательный дескриптор шрифта,
поэтому исключён из проверки весов компонентов.

Секции настроек получают якорь `#settings-<id>` (например, `#settings-telegram`); имя скрытого поля `section` не меняется.

`base.html` добавляет класс `.js` элементу `<html>` до загрузки CSS: `list.css` использует `html.js`, чтобы скрывать строки после первой порции только при включённом JavaScript.

## Списки

Страница со списком наследует `venom_ui/app.html`: каркас подключает общие стили и скрипты.
В режиме `client` поиск, фильтры и сортировка работают по данным `row_attrs`
в браузере. В режиме `server` GET-параметры обрабатывает сервис, который
возвращает строки, счётчики и выбранные фильтры; этот режим работает и без JS.
Режим должен совпадать у `filter_bar` и `data_table`.

В режиме `client` состояние хранится в URL и `sessionStorage` отдельно для пути страницы и id
таблицы; параметры URL имеют приоритет. В режиме `server` состояние хранится только в URL.
`fixed=true` у `data_table` ограничивает
высоту области прокрутки (`--table-max-height`, по умолчанию `70vh`), чтобы
заголовок оставался виден на длинных списках. `stacked=true` включает карточки
на узком экране. Правило `.js [data-lazy-pending]` скрывает строки после первой
порции до запуска списка; без JavaScript все строки доступны.

Для обычной POST-формы передайте имя поля один раз через `select_name`:
`data_table` передаёт его в caller, а `select_cell` добавляет имя и значение id.
Флажок «выбрать все» всегда без имени и не отправляется.

```jinja
<form method="post" action="/bulk">
  {{ venom_ui.csrf() }}
  {% call(select_name) list.data_table('items', columns, selectable=true, select_name='ids') %}
    <tbody>
    {% for row in rows %}
      <tr {{ list.row_attrs(row.title, id=row.id) }}>
        {{ list.select_cell(row.id, row.title, name=select_name) }}
        <td>{{ row.title }}</td>
      </tr>
    {% endfor %}
    </tbody>
  {% endcall %}
  {{ ui.btn('Обработать выбранные') }}
</form>
```

Сервис получает выбранные значения через `request.form.getlist('ids')`.

## Группа флажков

`ui.checkbox_group(name, label, options, checked=(), hint=None, columns_min='14rem', scroll=False, id=None, collapsible=False, error=None, attrs={})`
создаёт fieldset с legend и общей сеткой кликабельных строк.
`options` — пары `(value, label)`, `checked` — выбранные значения;
числовые и строковые ключи сравниваются как строки. Одиночное значение тоже допустимо.
При повторении имени на странице задайте уникальный id: он связывает подсказку с группой.
Все флажки отправляются под одним именем: `request.form.getlist(name)`.

```jinja
{{ ui.checkbox_group('brands', 'Бренды', [(1, 'Alpha'), (2, 'Beta')],
    checked=[2], hint='Выберите бренды для проверки.', columns_min='14rem') }}
```

Ширина колонок задаётся CSP-совместимыми пресетами `10rem`, `14rem`, `18rem`
(модификаторы --narrow и --wide; у стандартного пресета нет модификатора); неизвестное значение использует `14rem`.
На экране до 640px стандартный и узкий пресеты используют минимум 7.5rem: две колонки при 360px, если контейнер не уже 260px, иначе одна. Широкий пресет остаётся одноколоночным.
`scroll=True` добавляет `checkbox-group--scroll`: область вариантов прокручивается
при высоте более `18rem`. Изменить предел можно переменной
`--checkbox-group-max-height` в CSS сервиса.
Обычный fieldset внутри `.bulk-bar` и `.settings-section` также получает сброс
рамки и отступов и оформление legend как `.field__label`.

collapsible=True оборачивает ту же группу в details.checkbox-menu.
Кнопка показывает «Бренды · выбрано N»; ui.js обновляет счётчик, закрывает
меню по Escape и клику снаружи и возвращает фокус на summary.
Без JS работает обычный details. Панель открывается вверх, прокручивается
при высоте более 50vh и подходит для нижней .bulk-bar.
Поля с подписью и кнопки в bulk-bar выравниваются по нижнему краю.

## Заголовок таблицы на телефоне

При `stacked=true` и ширине до 699px заголовок занимает одну строку высотой 44px:
сортируемые колонки и флажок выбора всех строк прокручиваются горизонтально
внутри заголовка, без видимой полосы прокрутки и переноса текста.
Флажок выбора всех и активная сортировка показаны первыми через CSS order; DOM-порядок сохранён.
Остальные заголовки визуально скрыты, но остаются доступны скринридерам.
Сортировка сохраняется в обоих режимах: кнопки в `client`, ссылки в `server`.


## Строки подробностей

В обоих режимах после `<tr data-row>` можно разместить одну или несколько
`list.detail_row(colspan, id=None, hidden=True)` с содержимым через caller.
В режиме `client` они перемещаются вместе с владельцем при сортировке и скрываются вместе с ним
при фильтрации и ленивом показе. Счётчики и выбор учитывают только `data-row`.
Открытое состояние сохраняется при смене фильтров. На телефоне подробности
занимают всю ширину под карточкой владельца.

```jinja
<tr {{ list.row_attrs(row.title, id=row.id) }}>
  <td>{{ row.title }}</td>
  <td><button type="button" data-detail-toggle aria-expanded="false"
              aria-controls="detail-{{ row.id }}">Подробности</button></td>
</tr>
{% call list.detail_row(2, id='detail-' ~ row.id) %}
  {{ ui.textarea('text-' ~ row.id, 'Текст', value=row.text) }}
{% endcall %}
```

`aria-controls` содержит id подробностей (несколько id разделяются пробелами).
У каждого блока должен быть уникальный id; кнопка находится внутри владельца.
Без `aria-controls` кнопка управляет всеми подробностями владельца; пустое или
несовпавшее значение не меняет строки и `aria-expanded`.
Удаляйте владельцев через `VenomList.removeRows(rows)`: функция принимает коллекцию
элементов `data-row`, удаляет каждого вместе со всеми следующими `data-row-detail`
и отправляет один `venomlist:refresh` на каждый затронутый список.
Например: `VenomList.removeRows(document.querySelectorAll('#domains .is-selected'))`.
Прямое удаление только владельца оставит осиротевшие подробности.
Демо `/demo/list` и `/demo/list-server` показывают подробности каждой третьей строки.

## Списки карточек и sort_control

`list.card_list(id, label=None)` создаёт `<ul class="card-list" data-list-body>`;
он также получает `data-list` для инициализации и `tabindex="-1"` для возврата фокуса.
caller содержит `li` с `list.row_attrs`. Поиск, чипы, счётчики, URL/sessionStorage,
сортировка, `lazy_sentinel` (порциями по 50) и `bulk_bar` работают как у таблицы.
`list.select_box(id, label, name=None)` создаёт флажок без табличной ячейки;
`name='ids'` позволяет отправлять выбранные значения обычной POST-формой.

`list.sort_control(columns, sort=None, dir='asc', target=None, selectable=False)`
выводит однострочную прокручиваемую группу заголовков с теми же кнопками,
иконками, что и таблица. Это `<div class="sort-control" role="group" aria-label="Сортировка">`:
активная кнопка имеет `aria-pressed="true"` и скрытую подпись направления
«по возрастанию» / «по убыванию», обновляемую при сортировке; `aria-sort` остаётся
только у табличных заголовков. `columns` имеет тот же формат.
Размещайте группу непосредственно перед списком либо передавайте `target=id`.
`selectable=True` добавляет выбор всех подходящих карточек без имени поля.

```jinja
{% call list.filter_bar('versions') %}
  {{ list.search() }}
  {{ list.chips('status', 'Статус', statuses) }}
{% endcall %}
{{ list.sort_control(columns, sort='date', dir='desc', selectable=true) }}
{% call list.card_list('versions', label='Версии шаблонов') %}
  {% for row in rows %}
  <li {{ list.row_attrs(row.title, {'status': row.status},
                         {'date': row.date, 'title': row.title}, id=row.id) }}>
    {{ list.select_box(row.id, row.title, name='ids') }}
    {{ row.title }}
  </li>
  {% endfor %}
  <li data-empty-row hidden>Ничего не найдено</li>
{% endcall %}
{{ list.lazy_sentinel('versions') }}
{% call list.bulk_bar('versions') %}{{ ui.btn('Применить') }}{% endcall %}
```

Произвольный контейнер отмечайте `data-list` и уникальным `id`, а тело —
`data-list-body` (это может быть тот же элемент). Владельцы `data-row` должны
быть непосредственными детьми тела. Старые таблицы с `tbody` продолжают работать.
После добавления строк отправляйте `venomlist:refresh` на контейнер; для нового
списка вызывайте `VenomList.init(container)`. Демо `/demo/cards` содержит 40 карточек.

Рекомендуемая структура карточки: `.card-list__content` объединяет флажок,
`.card-list__thumbnail` (миниатюра) и `.card-list__text` (заголовок, дата, статус).
Эти классы входят в пакет и подходят для списков brand и complaints.
На `.card-list` можно переопределить локальные переменные `--list-gap` (интервал),
`--list-card-pad` (отступ карточки) и `--list-thumbnail-size` (размер миниатюры).

## Общие параметры полей

`field`, `textarea`, `select`, `checkbox`, `secret_field` и `file_picker` принимают
`required`, `attrs`, `hint`, `error`. Дополнительные атрибуты попадают на сам control;
`attrs.id` меняет также связанные подписи. Подсказка и ошибка связаны через
`aria-describedby`, ошибка добавляет `aria-invalid="true"`. Явные ARIA-атрибуты
в `attrs` имеют приоритет. `textarea` и `field` поддерживают `placeholder`;
у `secret_field` он называется `placeholder_hint`. У select, checkbox и file
нет placeholder: используйте пустую option либо постоянную подпись.
`required=True` у `secret_field` требует новый пароль даже при сохранённом значении.
`checkbox_group` принимает `hint`, `error`, `attrs` для fieldset; `required` к группе
не применяется, поскольку требование к каждому checkbox заставило бы выбрать всё.

```jinja
{{ ui.textarea('domains', 'Добавить домены', required=true,
               placeholder='example.org', attrs={'data-domains': ''},
               hint='Один домен на строку', error=errors.get('domains')) }}
```


## Опции index в 0.1.3

Демо `/demo/list?example=index` включает пересекающиеся фильтры, теги и передачу
состояния; `/demo/list` сохраняет прежние настройки по умолчанию.

| Опция | По умолчанию | Конфигурация index |
| --- | --- | --- |
| `chips(..., none_value='__none__')`, `dropdown(..., none_value='__none__')` | Значение зарезервировано для пустого набора | `('__none__', 'Без тегов')`; пустая строка по-прежнему означает все строки |
| `chips(..., count_scope=None)` | Все активные поля, кроме своей группы | `count_scope=['tag']` учитывает только тег; `[]` считает по всему списку |
| `filter_bar(..., persist='session', persist_ttl=None)` | Сохранение при изменении, без срока | `persist='handoff', persist_ttl=300`; `persist='none'` не читает и не пишет хранилище |
| `search(..., mode='words')` | Все слова запроса в любом порядке | `mode='substring'` ищет весь нормализованный запрос подряд |
| `data_table(..., reveal_on_filter=False)` | Ленивый показ порциями по 50 | `True` раскрывает подходящие строки при фильтрации и сортировке |

`data-filter-NAME` содержит токены через пробел; одиночные значения продолжают
работать. Чипы и dropdown проверяют принадлежность токена, а не равенство всей
строки. `none_value` можно заменить, если значение `__none__` занято данными.
Серверные списки по-прежнему получают готовые результаты и счётчики от сервиса.
Оба режима поиска приводят регистр и заменяют «ё» на «е».

```jinja
{% import 'venom_ui/list.html' as list %}
{% call list.filter_bar('domains', persist='handoff', persist_ttl=300) %}
  {{ list.search(mode='substring') }}
  {{ list.chips('show', 'Показать', [('', 'Все'), ('dropped', 'Выпали'),
      ('errors', 'Ошибки')], count_scope=['tag']) }}
  {{ list.dropdown('tag', 'Тег', [('', 'Все теги'), ('__none__', 'Без тегов'),
      ('1', 'Первый'), ('2', 'Второй')]) }}
{% endcall %}
<form method="post" action="/domains/archive">
  {{ venom_ui.csrf() }}
  {% call(select_name) list.data_table('domains', columns, selectable=true,
      select_name='domain_ids', reveal_on_filter=true) %}
  <tbody>
    <tr {{ list.row_attrs('example.org', {'show': 'dropped errors', 'tag': '1 2'},
        {'domain': 'example.org'}, id=42) }}>
      {{ list.select_cell(42, 'example.org', name=select_name) }}
      <td>example.org</td>
    </tr>
  </tbody>
  {% endcall %}
  {{ ui.btn('В архив') }}
</form>
{{ list.lazy_sentinel('domains') }}
```

Handoff сохраняется в `sessionStorage` при переходе по ссылке в этой вкладке или
отправке формы, но не при каждом изменении и не при обычной перезагрузке.
Ключ `venomlist:<pathname>#<table-id>` изолирует пути и списки. Снимок содержит
`path`, `timestamp` (миллисекунды) и `values`; следующая загрузка того же пути
потребляет его один раз, даже если он просрочен или URL задаёт свои фильтры.
Для handoff `persist_ttl=None` означает 300 секунд. Явные параметры списка в URL
имеют приоритет и не смешиваются с сохранёнными значениями.
Снимок с меткой времени в будущем отбрасывается.

«Выбрать все» теперь всегда выбирает **все подходящие строки**, включая ещё не
показанные. Счётчик, событие `venomlist:selection` и обычная POST-форма получают
полный набор. Отключённые флажки не выбираются; фильтрация сохраняет `checked`
строк, которые перестали подходить, но временно делает их `disabled`: они не
входят в счётчик, событие и POST. Сброс фильтра восстанавливает исходное состояние
`disabled` и сохранённый выбор. Сам выбор не меняет порцию ленивого показа.
Это второе намеренное исключение из обратной совместимости дефолтного поведения
с v0.1.2, наряду с исправлением select-all (пункт 5 спецификации): раньше фильтр
снимал выбор со скрытых строк, теперь временно блокирует их флажки и восстанавливает выбор.

### Дополнения core

`ui.settings_section(..., form_attrs={})` передаёт дополнительные атрибуты форме:
`form_attrs={'autocomplete': 'off'}` удобно для настроек index.
`ui.icon_button(icon, label, variant=None, compact=False, attrs={})` создаёт кнопку
с SVG и доступным именем. Например,
`ui.icon_button('trash', 'Удалить домен', variant='danger', compact=true,
attrs={'data-delete': '42'})`: визуальный размер 28px, область нажатия 44px через
псевдоэлемент, высота строки не увеличивается. По умолчанию размер 44px.
Для соседних compact-кнопок используйте контейнер `.list-row-actions` с gap 8px:
добавочный отступ второй кнопки 8px даёт 16px между видимыми кнопками,
поэтому их области нажатия 44px не пересекаются.
Шапка таблицы и `sort_control` имеют одинаковую яркую нижнюю границу внутри panel.
Drawer игнорирует Escape с `defaultPrevented`: внутренний редактор может вызвать
`event.preventDefault()` и оставить меню открытым.

### Flash с подробностями и отменой

`ui.flash_stack()` принимает строки и словари `text`, `details` (список строк),
`actions` (список действий). Каждое действие содержит `label`, `action` (URL),
`fields` (словарь скаляров или списков) и необязательный `variant='secondary'`
или `'danger'`. Значения списка становятся повторяющимися hidden-полями.
Действия — POST-формы с `venom_ui.csrf()` и стандартной кнопкой пакета.

```python
flash({'text': 'Домены отправлены в архив',
       'details': ['one.example', 'two.example'],
       'actions': [{'label': 'Отменить', 'action': url_for('undo_archive'),
                    'fields': {'domain_ids': [42, 43]}, 'variant': 'secondary'}]},
      'success')
```

`ui.banner(category, text, details=None, actions=None, closable=True, inline=False)`
использует тот же рендерер действий. `{% call ui.banner('info', 'Готово') %}…{% endcall %}`
добавляет произвольную разметку действий; её можно совмещать с `actions`.
Старые позиционные аргументы `details, closable, inline` поддерживаются.
Категории `warn`, `danger`, `message` соответствуют `warning`, `error`, `info`;
неизвестные категории остаются `info`. Строки и поля экранируются автоматически.
В наследнике `venom_ui/app.html` можно переопределить `{% block flash %}`.


### Подтверждение массового действия

`data-confirm="Удалить {n} {noun}?"` и
`data-confirm-forms="домен|домена|доменов"` подставляют число выбранных строк и
русское склонение (1 домен, 2 домена, 5/11 доменов, 21 домен).
`window.VenomUI.pluralRu(n, one, few, many)` экспортирует тот же помощник для сервиса.

```jinja
{% call list.bulk_bar('domains') %}
  {{ ui.btn('Удалить', variant='danger', attrs={
      'form': 'bulk-form', 'data-confirm': 'Удалить {n} {noun}?',
      'data-confirm-forms': 'домен|домена|доменов'}) }}
{% endcall %}
```

Поля подтверждения можно задать форме или кнопке (кнопка имеет приоритет).
Число берётся из `data-confirm-count`, если он указан; иначе из списка,
заданного `data-confirm-target="domains"` / `data-target="domains"`, родительской
bulk bar или списка. Для формы без явной связи учитываются её поля
`data-row-select`, включая внешние поля с `form="..."` и ещё не показанные строки.
Отключённые флажки не учитываются. Обычный текст `data-confirm` остаётся прежним.

`.table-scroll` теперь имеет `position: relative`, чтобы абсолютные
`.visually-hidden` подписи длинной таблицы оставались в её области прокрутки
и не увеличивали высоту страницы.

Статусные `.pill` сохраняют текст в одной строке (`white-space: nowrap`),
в том числе «не проверялся» в узких таблицах.

### Произвольное поле фильтра

`list.input(name, label, value='', type='text', attrs={}, label_visible=False)`
добавляет поле на общую ось поиска, чипов и dropdown. По умолчанию подпись
доступна скринридеру; `label_visible=True` показывает её как подпись dropdown.
`attrs` передаёт HTML-атрибуты, например `min`, `max`, `required` или `id`.

```jinja
{% call list.filter_bar('complaints', mode='server', action='/complaints') %}
  {{ list.search() }}
  {{ list.chips('status', 'Статус', statuses) }}
  {{ list.dropdown('brand', 'Бренд', brands) }}
  {{ list.input('date', 'Дата', value=request.args.get('date', ''), type='date',
      attrs={'min': '2025-01-01'}, label_visible=true) }}
{% endcall %}
```

В client поле фильтрует по `data-filter-<name>` с теми же правилами токенов,
участвует в URL, persistence, count_scope и сбросе. В server изменение (`change`)
автоматически отправляет GET-форму; обработчик сервиса фильтрует данные сам.
Дата в client — точное совпадение токена ISO, не диапазон. Примеры:
`/demo/list?example=input` и `/demo/list-server?example=input`.

Значения `data-filter-*` с пробелами теперь трактуются как несколько токенов:
`data-filter-tag="one two"` совпадает с фильтром `one` или `two`, но не `one two`.
Совместимость прежнего точного сравнения гарантирована только для одного токена.
`count_scope` принимает только список имён полей (не строку).
`filter_bar(..., reset_keep=['example'])` сохраняет нефильтрующие GET-параметры
при отправке и сбросе серверных фильтров. `reset_keep` принимает только список
имён полей (не строку). `card_list(..., reveal_on_filter=True)`
поддерживает раскрытие всех результатов по тем же правилам, что и таблица.
Декоративный разделитель `--border-bright` над `--bg-panel` сохраняет выбранный
контраст около 2.6:1; это не заявление о соответствии границ UI WCAG 1.4.11.
