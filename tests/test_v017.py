from pathlib import Path

import pytest

from test_list import Tags

STATIC = Path(__file__).parents[1] / 'src/venomshadows_ui/static'
TEMPLATE = '''{% import "venom_ui/list.html" as list %}
{% call list.data_table('auto', columns, stacked=true, mode='server') %}
<tbody><tr data-row id="auto-row">
{{ list.cell(columns[0], 'Alpha') }}
<td data-stack="secondary" data-label="Action"><button id="action">Run</button><input id="value" value="initial"></td>
<td data-stack="secondary" data-label="Note">Note text</td>
{{ list.cell(columns[1], none) }}
<td data-stack="secondary">   </td>
</tr><tr data-row id="manual"><td>Manual</td><td data-stack="secondary">Original</td>
{% call list.secondary_cells(2) %}<button>Custom</button>{% endcall %}
</tr><tr data-row id="empty">{{ list.cell(columns[1], none) }}</tr></tbody>
{% endcall %}'''


def content(render):
    return render(TEMPLATE, columns=[dict(key='name', label='Name', primary=True),
                                    dict(key='extra', label='Extra', stack='secondary')])


def load(page, render):
    page.set_content(content(render))
    for name in ['core.css', 'list.css']:
        if (STATIC / name).exists():
            page.add_style_tag(path=str(STATIC / name))


def test_secondary_resize_identity_and_init(page, render):
    from playwright.sync_api import expect

    page.set_viewport_size(dict(width=700, height=900))
    load(page, render)
    page.evaluate('''() => {
      window.original = document.querySelector('#action');
      original.addEventListener('click', () => window.clicks = (window.clicks || 0) + 1);
      window.manualHTML = document.querySelector('#manual').innerHTML;
    }''')
    page.add_script_tag(path=str(STATIC / 'list.js'))
    page.evaluate('window.manualHTML = document.querySelector("#manual").innerHTML')
    assert page.locator('#auto-row details').count() == 0
    for _ in range(2):
        page.set_viewport_size(dict(width=699, height=900))
        summary = page.locator('#auto-row summary')
        expect(summary).to_be_visible()
        assert summary.locator('svg[aria-hidden="true"]').count() == 1
        page.evaluate('VenomList.init(); VenomList.init(document.querySelector("#auto"))')
        assert page.locator('#auto-row details').count() == 1
        assert page.locator('#auto-row .data-table__secondary-item').count() == 2
        assert page.locator('#empty details').count() == 0
        summary.click()
        page.locator('#action').click()
        page.locator('#value').fill('edited')
        assert page.evaluate('original === document.querySelector("#action")')
        assert page.evaluate('manualHTML === document.querySelector("#manual").innerHTML')
        expect(page.locator('#manual > td[data-stack]')).to_be_hidden()
        page.set_viewport_size(dict(width=700, height=900))
        expect(page.locator('#auto-row details')).to_have_count(0)
        expect(page.locator('#auto-row > td[data-stack] #action')).to_be_visible()
        assert page.locator('#value').input_value() == 'edited'
        assert page.evaluate('original === document.querySelector("#action")')
    assert page.evaluate('window.clicks') == 2


def test_secondary_without_javascript(browser, render):
    from playwright.sync_api import expect

    context = browser.new_context(java_script_enabled=False, viewport=dict(width=390, height=900))
    try:
        page = context.new_page()
        css = (STATIC / 'list.css').read_text(encoding='utf-8')
        page.set_content('<style>' + css + '</style>' + content(render))
        expect(page.locator('#action')).to_be_visible()
        expect(page.locator('#manual > td[data-stack]')).to_be_visible()
        expect(page.get_by_text('Note text', exact=True)).to_be_visible()
    finally:
        context.close()


@pytest.mark.parametrize('mode', ['client', 'server'])
@pytest.mark.parametrize('sortable', [True, False])
@pytest.mark.parametrize('header', [True, False])
def test_short_headers(render, mode, sortable, header):
    html = render('''{% import "venom_ui/list.html" as list %}
        {{ list.sort_th(column, none, 'asc', mode, header=header) }}''',
        column=dict(key='count', label='Полное "имя" <колонки>', short='Кратко', sortable=sortable),
        mode=mode, header=header)
    tags = Tags(html)
    assert 'Кратко' in html
    elements = tags.find('th') + tags.find('button') + tags.find('a')
    for element in elements:
        assert element['title'] == 'Полное "имя"'
        if header:
            assert element['aria-label'] == 'Полное "имя"'


@pytest.mark.parametrize('mode', ['client', 'server'])
def test_short_accessible_headers(page, render, mode):
    from playwright.sync_api import expect

    page.set_content(render('''{% import "venom_ui/list.html" as list %}
      {% call list.data_table('short', columns, mode=mode) %}<tbody></tbody>{% endcall %}''',
      columns=[dict(key='count', label='Количество доменов', short='Домены'),
               dict(key='name', label='Название сервиса', short='Сервис', sortable=False)], mode=mode))
    control = page.get_by_role('button' if mode == 'client' else 'link', name='Количество доменов')
    expect(control).to_have_text('Домены')
    expect(control).to_have_attribute('title', 'Количество доменов')
    header = page.get_by_role('columnheader', name='Название сервиса')
    expect(header).to_have_text('Сервис')
    expect(header).to_have_attribute('title', 'Название сервиса')

@pytest.mark.parametrize('width', [390, 900])
def test_legacy_site_defer(page, width):
    from playwright.sync_api import expect
    page.set_viewport_size(dict(width=width, height=900))
    html = '''<script defer src="/list.js"></script><script defer src="/site.js"></script>
    <table id="domain-table" data-list data-mode="server" class="data-table data-table--stacked">
    <tbody><tr data-row><td class="domain-name">Alpha</td>
    <td data-stack="secondary" data-label="Note">Payload</td></tr></tbody></table>'''
    resources = {'/list.js': (STATIC / 'list.js').read_text(encoding='utf-8'),
                 '/site.js': Path(__file__).with_name('site_secondary_legacy.js').read_text(encoding='utf-8')}
    page.route('**/*', lambda route: route.fulfill(body=resources.get('/' + route.request.url.rsplit('/', 1)[-1], html),
               content_type='application/javascript' if route.request.url.endswith('.js') else 'text/html'))
    page.goto('http://regression.test/')
    for size in [390, 900, 390]:
        page.set_viewport_size(dict(width=size, height=900))
        page.evaluate('VenomList.init()')
        expect(page.locator('details')).to_have_count(1)
        expect(page.locator('[data-secondary-auto]')).to_have_count(0)
        expect(page.locator('details' if size == 390 else 'td[data-stack]')).to_contain_text('Payload')


@pytest.mark.parametrize('marker', ['<details class="data-table__secondary"><summary>Custom</summary></details>',
                                   '<td class="data-table__secondary-cell">Custom</td>'])
@pytest.mark.parametrize('packed', [False, True])
def test_late_service_ownership(page, render, marker, packed):
    from playwright.sync_api import expect
    page.set_viewport_size(dict(width=390 if packed else 900, height=900))
    load(page, render)
    page.add_script_tag(path=str(STATIC / 'list.js'))
    page.locator('#auto-row').evaluate('(row, html) => row.insertAdjacentHTML("beforeend", html)', marker)
    expect(page.locator('#auto-row [data-secondary-auto]')).to_have_count(0)
    for width in [390, 900, 390]:
        page.set_viewport_size(dict(width=width, height=900))
        page.evaluate('VenomList.init(); document.querySelector("#auto").dispatchEvent(new Event("venomlist:refresh"))')
        expect(page.locator('#auto-row [data-secondary-auto]')).to_have_count(0)
        expect(page.locator('#auto-row > td[data-stack] #action')).to_have_count(1)


@pytest.mark.parametrize('late', [False, True])
def test_manual_opt_out(page, render, late):
    from playwright.sync_api import expect
    page.set_viewport_size(dict(width=390, height=900))
    load(page, render)
    if late:
        page.add_script_tag(path=str(STATIC / 'list.js'))
    page.locator('#auto').evaluate('(table) => table.dataset.secondary = "manual"')
    if not late:
        page.add_script_tag(path=str(STATIC / 'list.js'))
    expect(page.locator('[data-secondary-auto]')).to_have_count(0)
    expect(page.locator('#auto-row > td[data-stack] #action')).to_be_visible()


def test_secondary_metadata_refresh_and_indicator(page, render):
    from playwright.sync_api import expect
    page.set_viewport_size(dict(width=390, height=900))
    load(page, render)
    page.locator('#action').evaluate('(el) => { el.parentNode.className="domain-comment"; el.parentNode.title="WHOIS"; }')
    page.add_script_tag(path=str(STATIC / 'list.js'))
    page.add_style_tag(content='.data-table__secondary > summary::after { content: "◇"; display: block; }')
    item = page.locator('#auto-row .data-table__secondary-item.domain-comment')
    expect(item).to_have_attribute('title', 'WHOIS')
    summary = page.locator('#auto-row summary')
    expect(summary).to_have_accessible_name('Ещё : Alpha')
    assert summary.get_attribute('aria-label') is None
    assert summary.evaluate('(el) => getComputedStyle(el,"::after").content') == 'none'
    page.locator('#auto-row').evaluate('''row => {
      const td = document.createElement('td'); td.dataset.stack='secondary'; td.textContent='New payload'; row.append(td);
      row.closest('table').dispatchEvent(new Event('venomlist:refresh'));
    }''')
    expect(page.locator('#auto-row details')).to_have_count(1)
    expect(page.locator('#auto-row details')).to_contain_text('New payload')
    page.set_viewport_size(dict(width=900, height=900))
    expect(page.locator('#auto-row > td.domain-comment')).to_have_attribute('title', 'WHOIS')
    expect(page.locator('#auto-row > td[data-stack]').last).to_have_text('New payload')


@pytest.mark.parametrize('mode', ['client', 'server'])
@pytest.mark.parametrize('direction, label', [('asc', 'по возрастанию'), ('desc', 'по убыванию')])
def test_short_sort_direction_name(page, render, mode, direction, label):
    from playwright.sync_api import expect
    page.set_content(render('''{% import "venom_ui/list.html" as list %}
    {% call list.data_table('sort', columns, stacked=true, mode=mode, sort='date', dir=direction) %}<tbody></tbody>{% endcall %}''',
    columns=[dict(key='date', label='Full date', short='Date')], mode=mode, direction=direction))
    control = page.locator('[data-sort-control] .th-sort')
    expect(control).to_have_accessible_name('Full date , ' + label)
    if mode == 'client':
        page.add_script_tag(path=str(STATIC / 'list.js'))
        control.click()
        expect(control).to_have_accessible_name('Full date , ' + ('по убыванию' if direction == 'asc' else 'по возрастанию'))
