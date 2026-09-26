"""Контракт макросов и ограничений общей библиотеки списков."""

from html.parser import HTMLParser
from pathlib import Path
import re
import shutil
import subprocess
from urllib.parse import parse_qs, urlsplit

import pytest

from demo_list_routes import create_app

ROOT = Path(__file__).resolve().parents[1]
STATIC = ROOT / "src/venomshadows_ui/static"
IMPORT = '{% import "venom_ui/list.html" as list %}'


class Tags(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.tags = []
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))

    def find(self, tag):
        return [attrs for name, attrs in self.tags if name == tag]


@pytest.mark.parametrize(('sort', 'direction', 'expected'), [(None, 'asc', 'none'), ('domain', 'asc', 'ascending'), ('domain', 'desc', 'descending')])
def test_header_sort(render, sort, direction, expected):
    html = render(IMPORT + '{{ list.sort_th(column, sort, direction, "client") }}',
                  column=dict(key='domain', label='Домен'), sort=sort, direction=direction)
    tags = Tags(html)
    assert tags.find('th')[0]['aria-sort'] == expected
    assert tags.find('button')[0]['data-sort-key'] == 'domain'
    assert len(tags.find('svg')) == 3


def test_server_links(render):
    html = render(IMPORT + '{{ list.sort_th(column, "domain", "asc", "server") }}',
                  '/demo/list-server?q=a%26b&tag=1&tag=2&page=8&sort=domain&dir=asc', column=dict(key='domain', label='Домен'))
    query = parse_qs(urlsplit(Tags(html).find('a')[0]['href']).query)
    assert query == {'q': ['a&b'], 'tag': ['1', '2'], 'sort': ['domain'], 'dir': ['desc']}


def test_chips_and_row_escaping(render):
    html = render(IMPORT + '{{ list.chips("status", "Статус", [("", "Все"), ("new", "Новый", "accent")], "new", {"new": 3}) }}'
                  '<table><tr {{ list.row_attrs(search, {"status": "new"}, {"number": 7}, "a") }}></tr></table>', search='ЁЖ "<script>')
    tags = Tags(html)
    assert [tag['aria-pressed'] for tag in tags.find('button')] == ['false', 'true']
    assert tags.find('input')[0]['value'] == 'new'
    assert tags.find('tr')[0] == {'data-row': None, 'data-search': 'ёж "<script>', 'data-filter-status': 'new', 'data-sort-number': '7', 'data-id': 'a'}
    assert '<script>' not in html


def test_table_contract(render):
    html = render(IMPORT + '{% call list.data_table("rows", columns, selectable=true, compact=true, stacked=true) %}<tbody><tr {{ list.row_attrs("a") }}><td data-label="Выбор"></td><td data-label="Домен">a</td></tr>{{ list.empty_row(2) }}</tbody>{% endcall %}', columns=[dict(key='domain', label='Домен')])
    tags = Tags(html)
    assert tags.find('input')[0]['aria-label'] == 'Выбрать все подходящие строки'
    assert 'data-table--stacked' in tags.find('table')[0]['class']
    assert 'data-table--compact' in tags.find('table')[0]['class']
    assert tags.find('td')[1]['data-label'] == 'Домен'
    assert 'hidden' in tags.find('tr')[-1]


@pytest.fixture
def list_app():
    return create_app()


def test_demos(list_app):
    client = list_app.test_client()
    page = client.get('/demo/list')
    assert page.status_code == 200
    rows = [row for row in Tags(page.text).find('tr') if 'data-row' in row]
    assert len(rows) == 180
    assert sum('data-lazy-pending' in row for row in rows) == 130
    page = client.get('/demo/list-server?status=new&brand=alpha&sort=number&dir=desc')
    assert page.status_code == 200
    rows = [tag for tag in Tags(page.text).find('tr') if 'data-row' in tag]
    assert len(rows) == 15
    assert all(row['data-filter-status'] == 'new' and row['data-filter-brand'] == 'alpha' for row in rows)
    values = [int(row['data-sort-number']) for row in rows]
    assert values == sorted(values, reverse=True)
    assert '15 из 180' in page.text
    empty = client.get('/demo/list-server?q=missing')
    assert 'Ничего не найдено' in empty.text
    assert client.get('/demo/list-server?sort=invalid&dir=invalid&status=invalid').status_code == 200


def test_css_guard():
    css = (STATIC / 'list.css').read_text(encoding='utf-8')
    for size in re.findall(r'font-size\s*:\s*([^;}]+)', css):
        assert re.fullmatch(r'var\(--text-(caption|sm|base|heading|title)\)', size.strip())
    for weight in re.findall(r'font-weight\s*:\s*([^;}]+)', css):
        assert re.fullmatch(r'var\(--weight-(regular|medium)\)', weight.strip())
    assert set(re.findall(r'(?:min|max)-width:\s*(\d+)px', '\n'.join(re.findall(r'@media[^\{]+', css)))) <= {'860', '861', '699', '700', '640', '641', '480', '481', '360', '361'}
    tokens = (STATIC / 'tokens.css').read_text(encoding='utf-8') + css
    defined = set(re.findall(r'(--[\w-]+)\s*:', tokens))
    # Публичный параметр высоты имеет fallback и не добавляет токен палитры.
    assert set(re.findall(r'var\((--[\w-]+)', css)) <= defined | {'--table-max-height'}
    assert 'data:' not in css
    assert '.pill' not in css


def test_no_glyph_icons():
    for path in [STATIC / 'list.css', ROOT / 'src/venomshadows_ui/templates/venom_ui/list.html']:
        assert not re.search('[⇅▲▼↑↓×✕✓🗄]', path.read_text(encoding='utf-8'))


def test_javascript_syntax():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node.js не установлен')
    subprocess.run([node, '--check', str(STATIC / 'list.js')], check=True, capture_output=True)


@pytest.mark.parametrize('mode', ['client', 'server'])
def test_filter_form_contract(render, mode):
    html = render(IMPORT + '{% call list.filter_bar("rows", mode=mode, action="/rows") %}'
                  '{{ list.search() }}{% endcall %}', '/?sort=number&dir=desc', mode=mode)
    tags = Tags(html)
    form = tags.find('form')[0]
    hidden = {tag['name']: tag['value'] for tag in tags.find('input') if tag.get('type') == 'hidden'}
    if mode == 'server':
        assert form['method'] == 'get' and form['action'] == '/rows'
        assert hidden == {'sort': 'number', 'dir': 'desc'}
    else:
        assert 'method' not in form and 'action' not in form
        assert not hidden
    plain = Tags(render(IMPORT + '{% call list.filter_bar("rows", mode="server") %}{% endcall %}'))
    assert not plain.find('input')


def test_new_table_macros(render):
    html = render(IMPORT + '{% call list.data_table("rows", [], label="Домены", fixed=true) %}'
                  '<tbody><tr>{{ list.select_cell("a&b", "<домен>") }}</tr>'
                  '{{ list.empty_row(1, hidden=false) }}</tbody>{% endcall %}')
    tags = Tags(html)
    assert tags.find('div')[0]['aria-label'] == 'Домены'
    assert 'table-scroll--fixed' in tags.find('div')[0]['class']
    box = tags.find('input')[0]
    assert box['value'] == 'a&b' and box['aria-label'] == 'Выбрать <домен>'
    assert 'data-row-select' in box
    assert 'hidden' not in tags.find('tr')[-1]
    assert '<домен>' not in html


@pytest.mark.parametrize('query,active', [('', False), ('?other=x', True), ('?sort=x&dir=desc&page=2', False), ('?query=&query=x', True), ('?query=', False), ('?query=x', True), ('?state=new', True), ('?category=a', True)])
def test_server_reset_uses_nonempty_query_values(render, query, active):
    html = render(IMPORT + '''{% call list.filter_bar("rows", mode="server", action="/elsewhere") %}
        {{ list.search(name="query") }}
        {{ list.chips("state", "State", [("", "All"), ("new", "New")]) }}
        {{ list.dropdown("category", "Category", [("", "All"), ("a", "A")]) }}
        {% endcall %}''', '/rows' + query)
    reset = Tags(html).find('a')[0]
    assert urlsplit(reset['href']).path == '/rows'
    assert (reset.get('aria-disabled') != 'true') == active


def test_server_reset_preserves_only_sort_and_direction(render):
    html = render(IMPORT + '''{% call list.filter_bar("rows", mode="server") %}
        {{ list.search() }}{% endcall %}''', '/rows?q=x&page=3&other=a&sort=a%26b&dir=desc')
    reset = Tags(html).find('a')[0]
    assert parse_qs(urlsplit(reset['href']).query) == {'sort': ['a&b'], 'dir': ['desc']}
    assert 'aria-disabled' not in reset


def test_multiple_bars_use_same_request_reset_state(render):
    html = render(IMPORT + '''{% call list.filter_bar("one", mode="server") %}
        {{ list.search(name="one") }}{% endcall %}
        {% call list.filter_bar("two", mode="server") %}
        {{ list.search(name="two") }}{% endcall %}''', '/?one=x')
    first, second = Tags(html).find('a')
    assert 'aria-disabled' not in first
    assert 'aria-disabled' not in second


def test_client_reset_is_not_native_reset(render):
    html = render(IMPORT + '{% call list.filter_bar("rows") %}{{ list.search(value="prefilled") }}{% endcall %}')
    reset = next(tag for tag in Tags(html).find('button') if 'data-list-reset' in tag)
    assert reset['type'] == 'button'
    assert 'disabled' in reset


def test_list_files_have_no_bom():
    paths = [STATIC / 'list.css', STATIC / 'list.js', ROOT / 'src/venomshadows_ui/templates/venom_ui/list.html', ROOT / 'tests/demo_list_routes.py']
    paths += list((ROOT / 'tests').glob('test_list*.py'))
    paths += list((ROOT / 'tests/demo_templates/demo').glob('list*.html'))
    for path in paths:
        assert not path.read_bytes().startswith(b'\xef\xbb\xbf'), path


@pytest.mark.parametrize('label', [None, 'Домены', '<Архив>'])
def test_landmark_labels(render, label):
    html = render(IMPORT + '''{% call list.filter_bar("rows", label=label) %}{% endcall %}
        {% call list.bulk_bar("rows", label=label) %}{% endcall %}''', label=label)
    tags = Tags(html)
    suffix = ': ' + label if label else ''
    assert tags.find('form')[0]['aria-label'] == 'Фильтры' + suffix
    bar = next(tag for tag in tags.find('div') if 'data-bulk-bar' in tag)
    assert bar['role'] == 'region'
    assert bar['aria-label'] == 'Массовые действия' + suffix
    assert len([tag for tag in tags.find('span') if tag.get('role') == 'status']) == 2


def test_nullable_pending_rows(render):
    html = render(IMPORT + '<tr {{ list.row_attrs(none, {"brand": none}, {"date": none}, pending=true) }}></tr>')
    row = Tags(html).find('tr')[0]
    assert all(row[key] == '' for key in ['data-search', 'data-filter-brand', 'data-sort-date', 'data-id'])
    assert 'data-lazy-pending' in row and 'hidden' not in row
    plain = Tags(render(IMPORT + '<tr {{ list.row_attrs("x") }}></tr>')).find('tr')[0]
    assert 'data-lazy-pending' not in plain


def test_dropdown_tones_and_column_width(render):
    html = render(IMPORT + '{{ list.dropdown("status", "Status", [("", "All"), ("new", "New", "accent")], "new") }}'
                  '{{ list.sort_th(column, none, "asc", "client") }}', column=dict(key='x', label='X', width='120'))
    tags = Tags(html)
    assert tags.find('option')[1] == {'value': 'new', 'selected': None}
    assert tags.find('th')[0]['width'] == '120'
    assert 'style' not in tags.find('th')[0]


@pytest.mark.parametrize(('width', 'expected'), [
    (120, '120'), ('120', '120'), ('25%', '25%'), (0, '0'),
    ('12rem', None), ('120px', None), ('25%%', None), ('', None),
    (' 120', None), ('12.5', None), ('１２', None), (None, None),
    (True, None), (['120'], None),
])
def test_column_width_contract(render, width, expected):
    html = render(IMPORT + '{% call list.data_table("rows", columns) %}<tbody></tbody>{% endcall %}',
                  columns=[dict(key='x', label='X', width=width)])
    header = Tags(html).find('th')[0]
    assert header.get('width') == expected
    assert 'style' not in header


def test_column_classes_preserve_alignment_and_escape(render):
    extra = 'service-width service-column "<test>'
    html = render(IMPORT + '{% call list.data_table("rows", columns) %}<tbody></tbody>{% endcall %}',
                  columns=[{'key': 'x', 'label': 'X', 'align': 'end', 'class': extra}])
    header = Tags(html).find('th')[0]
    assert header['class'] == 'data-table__end ' + extra
    assert 'style' not in header
    assert '<test>' not in html


def test_shared_query_policy_preserves_repeated_sort_args(render):
    html = render(IMPORT + '{% call list.filter_bar("rows", mode="server") %}{% endcall %}',
                  '/demo/list-server?sort=a&sort=b&dir=desc&q=x&page=4')
    tags = Tags(html)
    assert [(x['name'], x['value']) for x in tags.find('input')] == [('sort', 'a'), ('sort', 'b'), ('dir', 'desc')]
    assert parse_qs(urlsplit(tags.find('a')[0]['href']).query) == {'sort': ['a', 'b'], 'dir': ['desc']}


@pytest.mark.parametrize("checked", [[], ["1"], ["2", "4"]])
def test_selection_plain_post(checked):
    from werkzeug.datastructures import MultiDict
    client = create_app().test_client()
    html = client.get("/demo/list").text
    inputs = Tags(html).find("input")
    rows = [item for item in inputs if "data-row-select" in item]
    assert len(rows) == 180
    assert all(item["name"] == "ids" for item in rows)
    assert all("name" not in item for item in inputs if "data-select-all" in item)
    payload = MultiDict((item["name"], item["value"]) for item in rows if item["value"] in checked)
    response = client.post("/demo/list-selection", data=payload)
    assert response.json == {"ids": checked, "fields": ["ids"] if checked else []}


def test_selection_name_escaping_and_default(render):
    html = render(IMPORT + '{{ list.select_cell(id, "Row", name=name) }}',
                  id='a"<&', name='ids"<&')
    checkbox = Tags(html).find("input")[0]
    assert checkbox["name"] == 'ids"<&'
    assert checkbox["value"] == 'a"<&'
    assert "name" not in Tags(render(IMPORT + '{{ list.select_cell(1, "Row") }}')).find("input")[0]
    assert "name" not in Tags(render(IMPORT + '{{ list.select_cell(1, "Row", name="") }}')).find("input")[0]
    html = render(IMPORT + '''{% call(select_name) list.data_table("rows", [], selectable=true) %}
        <tbody><tr>{{ list.select_cell(7, "Row", name=select_name) }}</tr></tbody>
        {% endcall %}''')
    assert all('name' not in checkbox for checkbox in Tags(html).find('input'))
