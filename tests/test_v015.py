"""v0.1.5 API, compatibility and real browser regressions (offline)."""
import json
from pathlib import Path

import pytest
from markupsafe import Markup

from test_core_rendering import tree

SNAPSHOTS = Path(__file__).parent / 'snapshots' / 'v014.json'


@pytest.mark.parametrize('case', json.loads(SNAPSHOTS.read_text(encoding='utf-8')) if SNAPSHOTS.exists() else [])
def test_legacy_html_byte_for_byte(render, case):
    expected = json.loads(SNAPSHOTS.read_text(encoding='utf-8'))[case]
    assert render(case) == expected


def macro(render, expression, **kwargs):
    return render("{% import 'venom_ui/macros.html' as ui %}{% import 'venom_ui/list.html' as list %}" + expression, **kwargs)


def test_secret_options(render):
    html = macro(render, "{{ ui.secret_field('smtp', 'SMTP', false, reveal=true, required=true, placeholder_unset='Новый пароль', attrs={'id': 'custom'}) }}")
    dom = tree(html)
    control = dom.find('input')[0]
    assert control.attrs['placeholder'] == 'Новый пароль'
    assert control.attrs['value'] == '' and 'required' in control.attrs
    button = dom.find('button')[0]
    assert button.attrs['aria-controls'] == 'custom'
    assert button.attrs['aria-pressed'] == 'false'
    html = macro(render, "{{ ui.secret_field('smtp', 'SMTP', true, clearable=true, clear_label='Удалить пароль') }}")
    assert 'smtp__clear' in html and 'Удалить пароль' in html


def test_new_core_macros(render):
    html = macro(render, """{{ ui.settings_toc([('smtp', 'Почта'), {'id': 'api', 'title': 'API'}]) }}
      {{ ui.empty_state('Выберите', 'Слева', sidebar=true, text_mobile='В меню') }}
      {{ ui.status_dot('ok', 'Работает') }}{{ ui.external_link('/target', '<Label>') }}
      {{ ui.kv_list([('Ключ', value)]) }}
      {% call ui.kv_list() %}{% call ui.kv_item('Нагрузка') %}<progress value="1" max="2"></progress>{% endcall %}{% endcall %}
      {% call ui.settings_section('plain', 'Сведения', none, no_marker=true) %}text{% endcall %}
      {% call ui.settings_section('off', 'Почта', false) %}text{% endcall %}""", value=Markup('<b>value</b>'))
    dom = tree(html)
    assert dom.find('a', href='#settings-smtp') and dom.find('a', href='#settings-api')
    assert dom.find('button', **{'data-sidebar-toggle': True})
    assert dom.find('span', role='img', **{'aria-label': 'Работает'})
    assert dom.find('a', target='_blank', rel='noopener')
    assert '&lt;Label&gt;' in html and '<b>value</b>' in html
    assert 'state-marker' not in html.split('id="settings-plain"')[1].split('</section>')[0]
    assert 'Не настроено' in html


def test_list_options(render):
    html = macro(render, """{% call list.filter_bar('test', count='auto') %}{{ list.chips('s', 'Статус', [('', 'Все')], label_visible=true) }}{{ list.input('date', 'Дата', nav=true) }}{% endcall %}
      {% call list.data_table('test', columns, stacked='auto', attrs={'class': 'data-table--stacked-scroll'}) %}<tbody><tr>{{ list.cell(columns[0], none) }}{% call list.secondary_cells(2) %}detail{% endcall %}</tr>{{ list.empty_row(2) }}</tbody>{% endcall %}
      {% call list.card_list('cards', grid=true) %}{% endcall %}""", columns=[dict(key='a', label='A', stack='hide', primary=True)])
    assert 'data-count="auto"' in html and 'data-list-nav' in html
    assert 'list-chips__label--visible' in html and 'card-list--grid' in html
    assert 'data-stack="hide"' in html and 'data-empty' in html and 'data-table__primary' in html
    assert 'data-table__secondary' in html and 'data-table__empty-inner' in html
    assert 'table-scroll__hbar' in html and 'data-table--stacked-scroll' in html


@pytest.mark.parametrize('count,hidden', [('always', False), ('auto', True), ('none', True)])
def test_count_policy(render, count, hidden):
    dom = tree(macro(render, "{% call list.filter_bar('items', count=policy, total=10, shown=10) %}{% endcall %}", policy=count))
    assert ('hidden' in dom.find('span', **{'data-list-count': True})[0].attrs) == hidden


def test_disabled_token_and_contrast():
    css = Path('src/venomshadows_ui/static/tokens.css').read_text(encoding='utf-8')
    assert '--color-text-disabled: var(--muted)' not in css
    def luminance(rgb):
        values = [v / 255 for v in rgb]
        return sum((v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4) * w
                   for v, w in zip(values, [.2126, .7152, .0722]))
    for background in [(12, 22, 38), (26, 42, 68)]:
        foreground = [a * .65 + b * .35 for a, b in zip((154, 173, 203), background)]
        assert (luminance(foreground) + .05) / (luminance(background) + .05) >= 3


def test_reveal_browser(page, live_url):
    page.goto(live_url + '/demo/settings')
    button = page.locator('[data-secret-reveal]')
    control = page.locator('#smtp_password')
    button.click()
    assert control.get_attribute('type') == 'text'
    assert button.get_attribute('aria-pressed') == 'true'
    assert button.get_attribute('aria-label') == 'Скрыть'
    button.click()
    assert control.get_attribute('type') == 'password'
    button.click()
    control.evaluate('el => el.form.addEventListener("submit", e => e.preventDefault())')
    control.evaluate('el => el.form.dispatchEvent(new Event("submit", {bubbles: true, cancelable: true}))')
    assert control.get_attribute('type') == 'password'
    assert button.get_attribute('aria-pressed') == 'false'
    button.evaluate('el => el.querySelectorAll("[data-secret-eye], [data-secret-eye-off]").forEach(n => n.remove())')
    button.click()
    assert control.get_attribute('type') == 'text'
    page.evaluate('document.dispatchEvent(new MouseEvent("click", {bubbles: true}))')


@pytest.mark.parametrize('width', [1600, 1280, 400])
def test_v015_demos(page, live_url, width):
    page.set_viewport_size({'width': width, 'height': 900})
    for demo in ['settings', 'cards?grid=1', 'list?example=stacked', 'dashboard']:
        page.goto(live_url + '/demo/' + demo)
        page.evaluate('document.fonts.ready')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    page.goto(live_url + '/demo/list?example=stacked')
    if width == 400:
        table = page.locator('#stack-flags')
        assert not table.locator('td[data-empty]').is_visible()
        assert not table.locator('td[data-stack="hide"]').is_visible()
        assert not table.locator('td[data-stack="secondary"]').is_visible()
        assert table.locator('.data-table__secondary summary').is_visible()
        assert table.locator('.data-table__primary').evaluate("el => getComputedStyle(el, '::before').content") == 'none'
        assert page.locator('.list-chips').first.evaluate('el => el.scrollWidth === el.clientWidth')
        assert table.locator('.sort-control').evaluate('el => el.scrollWidth === el.clientWidth')
    wrap = page.locator('.table-scroll:has(#wide-table)')
    page.wait_for_function("document.querySelector('#wide-table').parentElement.classList.contains('is-overflow')")
    bar = wrap.locator('.table-scroll__hbar')
    bar.evaluate('el => el.scrollLeft = 180')
    page.wait_for_function("document.querySelector('#wide-table').parentElement.scrollLeft >= 179")
    wrap.evaluate('el => el.scrollLeft = 300')
    page.wait_for_function("document.querySelector('#wide-table').parentElement.querySelector('.table-scroll__hbar').scrollLeft >= 299")
    empty = wrap.locator('.data-table__empty-inner')
    wrap.locator('[data-empty-row]').evaluate('el => el.hidden = false')
    assert empty.bounding_box()['x'] >= 0


def test_count_chips_and_nav(page, live_url):
    page.goto(live_url + '/demo/list')
    assert page.locator('[data-list-count]').inner_text() == 'показано 50 из 180'
    page.locator('[name="brand"]').select_option('alpha')
    assert page.locator('[data-chip=""]').get_attribute('aria-pressed') == 'false'
    page.locator('[data-list-reset]').click()
    assert page.locator('[data-chip=""]').get_attribute('aria-pressed') == 'true'
    page.locator('[data-filter-bar]').evaluate("el => el.dataset.count = 'auto'")
    page.locator('[data-list-search]').fill('nothing-matches')
    assert page.locator('[data-list-count]').is_visible()


def test_sticky_page_header_and_code(page, live_url):
    page.goto(live_url + '/demo/list-server')
    wrap = page.locator('.table-scroll')
    assert 'is-overflow' not in (wrap.get_attribute('class') or '')
    page.evaluate('window.scrollTo(0, 900)')
    assert page.locator('thead th').first.bounding_box()['y'] == pytest.approx(0, abs=1)
    page.goto(live_url + '/demo/settings')
    assert page.locator('.field__hint').first.evaluate('''el => {
      const code = document.createElement('code'); code.textContent = 'test'; el.append(code);
      return parseFloat(getComputedStyle(code).fontSize) >= 13;
    }''')


def test_overflow_edges_and_subnav(page, live_url):
    page.set_viewport_size({'width': 400, 'height': 900})
    page.goto(live_url + '/demo/settings')
    page.locator('.topbar__nav').evaluate('''el => {
      for (let i = 0; i < 12; i++) {
        const tab = el.firstElementChild.cloneNode(true); tab.classList.remove('topbar__tab--active');
        tab.removeAttribute('aria-current'); tab.textContent = 'Раздел ' + i; el.append(tab);
      }
      el.scrollLeft = 0; VenomUI.overflowEdges(el);
      const sub = el.cloneNode(true); sub.className = 'subnav';
      document.querySelector('.page').prepend(sub); VenomUI.overflowEdges(sub);
    }''')
    assert 'is-overflow-end' in page.locator('.topbar__nav').get_attribute('class')
    assert page.locator('.subnav').evaluate('el => el.scrollWidth === el.clientWidth && el.clientHeight > 44')
    page.locator('.topbar__nav').evaluate('el => el.scrollLeft = el.scrollWidth')
    page.wait_for_function("document.querySelector('.topbar__nav').classList.contains('is-overflow-start')")
    assert page.locator('.topbar__nav').evaluate('''old => {
      const nav = old.cloneNode(true); nav.classList.remove('is-overflow-start', 'is-overflow-end');
      nav.querySelectorAll('.topbar__tab--active').forEach(el => el.classList.remove('topbar__tab--active'));
      nav.lastElementChild.classList.add('topbar__tab--active'); old.replaceWith(nav);
      VenomUI.overflowEdges(nav);
      const box = nav.lastElementChild.getBoundingClientRect(), parent = nav.getBoundingClientRect();
      return box.left >= parent.left && box.right <= parent.right + 1;
    }''')


@pytest.mark.parametrize('mode', ['client', 'server'])
def test_navigation_input(page, live_url, mode):
    page.goto(live_url + '/demo/' + ('list-server' if mode == 'server' else 'list'))
    page.locator('[data-filter-bar]').evaluate('''form => {
      const field = document.createElement('input'); field.name = 'period';
      field.setAttribute('data-list-nav', ''); form.append(field);
    }''')
    with page.expect_navigation():
        page.locator('[data-list-nav]').fill('2026-11')
        page.locator('[data-list-nav]').dispatch_event('change')
    assert 'period=2026-11' in page.url


def test_disabled_and_buttons(page, live_url):
    page.set_viewport_size({'width': 400, 'height': 900})
    page.goto(live_url + '/demo/list')
    assert page.locator('[data-list-reset]').evaluate("el => getComputedStyle(el).backgroundColor") == 'rgba(0, 0, 0, 0)'
    assert page.locator('.page-header').evaluate('''header => {
      const actions = document.createElement('div'); actions.className = 'page-header__actions';
      const button = document.createElement('button'); button.className = 'btn'; button.textContent = 'Перепроверить';
      actions.append(button); header.append(actions);
      const range = document.createRange(); range.selectNodeContents(button);
      return range.getClientRects().length === 1;
    }''')


def test_stacked_scroll_edges(page, live_url):
    page.set_viewport_size({'width': 400, 'height': 900})
    page.goto(live_url + '/demo/list?example=stacked&scroll=1')
    group = page.locator('#stack-flags .sort-control')
    assert group.evaluate("el => getComputedStyle(el).scrollbarWidth") == 'thin'
    assert 'is-overflow-end' in group.get_attribute('class')


def test_mobile_clear_selection_focus(page, live_url):
    page.set_viewport_size({'width': 400, 'height': 900})
    page.goto(live_url + '/demo/list')
    page.locator('[data-select-all]:visible').check()
    clear = page.locator('[data-clear-selection]')
    clear.focus()
    clear.click()
    assert page.locator('[data-select-all]:visible').evaluate('el => el === document.activeElement')


def test_chart_summary_target(page, live_url):
    page.goto(live_url + '/demo/dashboard')
    summary = page.locator('.hdata summary').first
    assert summary.bounding_box()['height'] >= 44
    assert summary.locator('.icon').count() == 1


@pytest.mark.parametrize('value', [None, False, 0, '', True])
def test_settings_marker_legacy_values(render, value):
    import sqlite3
    with sqlite3.connect(':memory:') as db:
        stored = db.execute('select ?', (value,)).fetchone()[0]
    html = macro(render, "{% call ui.settings_section('x', 'X', value) %}{% endcall %}", value=stored)
    assert 'state-marker' in html
    assert ('Настроено' if stored else 'Не настроено') in html
    assert html == macro(render, "{% call ui.settings_section('x', 'X', value) %}{% endcall %}", value=bool(stored))
    assert 'state-marker' not in macro(render, "{% call ui.settings_section('x', 'X', value, no_marker=true) %}{% endcall %}", value=stored)


@pytest.mark.parametrize('url,expected', [('/path', '/path'), ('https://example.test', 'https://example.test'),
    ('../path', '../path'), ('javascript:alert(1)', '#'), ('JaVa\nScRiPt:alert(1)', '#'), ('data:text/html,x', '#')])
def test_external_url_policy(render, url, expected):
    dom = tree(macro(render, "{{ ui.external_link(url, 'Link') }}", url=url))
    assert dom.find('a')[0].attrs['href'] == expected


def test_kv_null_and_falsy(render):
    html = macro(render, "{{ ui.kv_list([('Null', none), ('Zero', 0), ('Empty', '')]) }}")
    assert '<dd>—</dd>' in html and '<dd>0</dd>' in html and '<dd></dd>' in html


@pytest.mark.parametrize('width', [400, 1600])
def test_empty_alignment_and_grid(page, live_url, width):
    page.set_viewport_size({'width': width, 'height': 900})
    page.goto(live_url + '/demo/list?example=stacked')
    wrap = page.locator('.table-scroll:has(#wide-table)')
    wrap.locator('[data-empty-row]').evaluate('el => el.hidden = false')
    for scroll in [0, 300]:
        wrap.evaluate('(el, x) => el.scrollLeft = x', scroll)
        center = wrap.locator('.data-table__empty-inner').evaluate('''el => {
          const range = document.createRange(); range.selectNodeContents(el);
          const text = range.getBoundingClientRect(); const wrap = el.closest('.table-scroll').getBoundingClientRect();
          return (text.left + text.right - wrap.left - wrap.right) / 2;
        }''')
        assert center == pytest.approx(0, abs=3)
    page.goto(live_url + '/demo/cards?grid=1')
    page.locator('[data-list-search]').fill('missing')
    empty = page.locator('[data-empty-row]')
    assert empty.evaluate('el => getComputedStyle(el).gridColumn') == '1 / -1'
    assert empty.bounding_box()['width'] == pytest.approx(page.locator('.card-list--grid').bounding_box()['width'], abs=2)


def test_legacy_lazy_count(page, live_url):
    page.goto(live_url + '/demo/cards')
    assert page.locator('[data-list-count]').inner_text() == '40 из 40'
    assert page.locator('[data-list-count]').get_attribute('data-count-format') is None


def test_dynamic_observers_are_released(page, live_url):
    page.add_init_script('''
      window.observed = new Set();
      const NativeObserver = ResizeObserver;
      window.ResizeObserver = class extends NativeObserver {
        constructor(callback) { super(callback); this.nodes = new Set(); observed.add(this); }
        observe(node, options) { this.nodes.add(node); super.observe(node, options); }
        disconnect() { this.nodes.clear(); super.disconnect(); }
      };
      window.scrollListeners = 0;
      const add = window.addEventListener;
      window.addEventListener = function(type, ...args) {
        if (type === 'scroll') scrollListeners++;
        return add.call(this, type, ...args);
      };
    ''')
    page.goto(live_url + '/demo/list')
    before = page.evaluate('scrollListeners')
    page.evaluate('''() => {
      for (let i = 0; i < 4; i++) {
        const root = document.createElement('section');
        root.innerHTML = '<div class="table-scroll"><table><tbody><tr><td>X</td></tr></tbody></table></div><nav><span>X</span></nav>';
        document.body.append(root); VenomList.init(root); VenomUI.overflowEdges(root.querySelector('nav'));
        root.remove();
      }
    }''')
    page.wait_for_function('Array.from(observed).every(o => Array.from(o.nodes).every(n => n.isConnected))')
    assert page.evaluate('scrollListeners') == before
