"""Контракты index и обратная совместимость новых опций."""

import pytest
from flask import flash

from demo_list_routes import create_app
from test_list import Tags


def test_options_render(render):
    html = render('''{% import 'venom_ui/list.html' as list %}
      {% call list.filter_bar('rows', persist='handoff', persist_ttl=300) %}
      {{ list.search(mode='substring') }}
      {{ list.chips('show', 'Show', [('empty', 'Empty')], count_scope=['tag'], none_value='empty') }}
      {{ list.dropdown('tag', 'Tag', [('empty', 'Empty')], none_value='empty') }}
      {% endcall %}
      {% call list.data_table('rows', [], reveal_on_filter=true) %}<tbody></tbody>{% endcall %}''')
    for attribute in ['data-persist="handoff"', 'data-persist-ttl="300"', 'data-search-mode="substring"',
                      'data-count-scope="tag"', 'data-none-value="empty"', 'data-reveal-on-filter="true"']:
        assert attribute in html


def test_core_options_and_flash(app, render):
    html = render('''{% import 'venom_ui/macros.html' as ui %}
      {% call ui.settings_section('s', 'Settings', true, action='/save', form_attrs={'autocomplete': 'off'}) %}Content{% endcall %}
      {{ ui.icon_button('trash', 'Delete', variant='danger', compact=true, attrs={'data-delete': 'yes'}) }}''')
    assert Tags(html).find('form')[0]['autocomplete'] == 'off'
    button = Tags(html).find('button')[0]
    assert button['class'] == 'icon-btn icon-btn--danger icon-btn--compact'
    assert button['aria-label'] == 'Delete' and button['data-delete'] == 'yes'
    with app.test_request_context('/'):
        flash({'text': '<removed>', 'details': ['a.example', '<b>'], 'actions': [
            {'label': 'Undo', 'action': '/undo', 'fields': {'domain_ids': [1, 2], 'source': 'list', 'count': 2, 'empty': []}}
        ]}, 'warn')
        flash('Plain message', 'message')
        html = app.jinja_env.from_string("{% import 'venom_ui/macros.html' as ui %}{{ ui.flash_stack() }}").render()
    assert 'banner--warning' in html and 'banner--info' in html
    assert '&lt;removed&gt;' in html and '&lt;b&gt;' in html and 'Plain message' in html
    tags = Tags(html)
    assert tags.find('form')[0] == {'method': 'post', 'action': '/undo'}
    fields = tags.find('input')
    assert any(field['name'] == 'csrf_token' for field in fields)
    assert [field['value'] for field in fields if field['name'] == 'domain_ids'] == ['1', '2']
    assert not any(field['name'] == 'empty' for field in fields)
    assert any(field['name'] == 'count' and field['value'] == '2' for field in fields)


def test_banner_slot_and_legacy_positionals(render):
    html = render('''{% import 'venom_ui/macros.html' as ui %}
      {% call ui.banner('danger', 'Text', None, false, true) %}<a href='/custom'>Custom</a>{% endcall %}''')
    assert 'banner--error banner--inline' in html
    assert 'banner__close' not in html and '/custom' in html
    html = render("{% extends 'venom_ui/app.html' %}{% block flash %}<p>Custom flash</p>{% endblock %}")
    assert 'Custom flash' in html


def index_page(page, live_url):
    page.goto(live_url + '/demo/list?example=index')


def test_index_tokens_counts_search_reveal(page, live_url, screenshot):
    index_page(page, live_url)
    assert page.locator('[data-row]:visible').count() == 50
    page.locator('[data-chip="dropped"]').click()
    assert page.locator('[data-row]:visible').count() == 90
    page.locator('[data-chip="errors"]').click()
    assert page.locator('[data-row]:visible').count() == 90
    page.locator('select[name=tag]').select_option('two')
    assert page.locator('[data-row]:visible').count() == 30
    count = page.locator('[data-chip="errors"] [data-chip-count]')
    assert count.inner_text() == '30'
    page.locator('[data-list-search]').fill('missing')
    assert page.locator('[data-row]:visible').count() == 0
    assert count.inner_text() == '30'
    page.locator('[data-list-reset]').click()
    page.locator('select[name=tag]').select_option('__none__')
    assert page.locator('[data-row]:visible').count() == 60
    page.locator('select[name=tag]').select_option('one')
    assert page.locator('[data-row]:visible').count() == 120
    page.locator('[data-list-reset]').click()
    page.locator('[data-list-search]').fill('ALPHA DOMAIN-12')
    assert page.locator('[data-row]:visible').count() == 0
    page.locator('[data-list-search]').fill('  DOMAIN-12.EXAMPLE ALPHA  ')
    assert page.locator('[data-row]:visible').count() == 1
    page.locator('[data-list-reset]').click()
    screenshot(page, 'index-options')
    index_page(page, live_url)
    page.locator('[data-sort-key=number]').click()
    assert page.locator('[data-row]:visible').count() == 180
    page.reload()
    assert page.locator('[data-row]:visible').count() == 180


@pytest.mark.parametrize('filtered', [False, True])
def test_bulk_post_all_matching_180(page, live_url, filtered):
    page.goto(live_url + '/demo/list')
    if filtered:
        page.locator('select[name=brand]').select_option('alpha')
    expected = [str(i) for i in range(1, 181) if not filtered or i % 3 == 0]
    assert page.locator('[data-row]:visible').count() == 50
    page.locator('[data-select-all]').check()
    assert page.locator('[data-selection-count]').inner_text() == str(len(expected))
    with page.expect_response('**/demo/list-selection') as response:
        page.locator('[data-submit-selection]').click()
    assert response.value.json()['ids'] == expected


def test_handoff_navigation_consumed_once(page, live_url):
    index_page(page, live_url)
    page.locator('[data-list-search]').fill('domain-12')
    assert page.evaluate('sessionStorage.length') == 0
    page.locator('[data-id="12"] [data-detail-toggle]').click()
    page.locator('[data-submit-selection]').click()
    saved = page.evaluate("JSON.parse(sessionStorage.getItem('venomlist:/demo/list#domains'))")
    assert saved['values']['q'] == 'domain-12' and saved['path'] == '/demo/list'
    index_page(page, live_url)
    assert page.locator('[data-list-search]').input_value() == 'domain-12'
    assert page.evaluate('sessionStorage.length') == 0
    assert 'q=domain-12' in page.url
    page.reload()
    assert page.locator('[data-list-search]').input_value() == 'domain-12'
    index_page(page, live_url)
    assert page.locator('[data-list-search]').input_value() == ''
    page.locator('[data-list-search]').fill('domain-1')
    page.locator('a[href="/demo/components"]').first.click()
    index_page(page, live_url)
    assert page.locator('[data-list-search]').input_value() == 'domain-1'


@pytest.mark.parametrize('kind', ['click', 'submit'])
def test_handoff_late_delegated_cancellation(page, live_url, kind):
    index_page(page, live_url)
    page.locator('[data-list-search]').fill('domain-12')
    page.evaluate("document.body.insertAdjacentHTML('beforeend', '<a id=handoff-link href=/demo/components>Navigate</a>')")
    page.evaluate("kind => document.addEventListener(kind, e => e.preventDefault(), {once: true})", kind)
    if kind == 'click':
        page.locator('#handoff-link').click()
    else:
        page.locator('[data-submit-selection]').click()
    page.evaluate('() => new Promise(resolve => setTimeout(resolve, 30))')
    assert page.evaluate('sessionStorage.length') == 0
    assert '/demo/list' in page.url


@pytest.mark.parametrize('immediate', [False, True])
def test_handoff_detached_list_aborts_listeners(page, live_url, immediate):
    page.add_init_script('''
      window.handoffSignals = [];
      const add = document.addEventListener.bind(document);
      document.addEventListener = (type, listener, options) => {
        if (options?.signal) window.handoffSignals.push(options.signal);
        return add(type, listener, options);
      };
    ''')
    index_page(page, live_url)
    page.evaluate('''immediate => {
      document.body.insertAdjacentHTML('beforeend', '<a id=handoff-link href=/demo/components>Navigate</a>');
      document.querySelector('[data-list]').remove();
      if (immediate) document.querySelector('#handoff-link').click();
    }''', immediate)
    if immediate:
        page.wait_for_url('**/demo/components')
    else:
        assert page.evaluate('handoffSignals.length >= 2 && handoffSignals.every(signal => signal.aborted)')
        page.locator('#handoff-link').click()
    assert page.evaluate('sessionStorage.length') == 0


@pytest.mark.parametrize('direction', ['ltr', 'rtl'])
def test_adjacent_compact_hit_targets_do_not_overlap(page, live_url, direction):
    index_page(page, live_url)
    page.locator('.icon-btn--compact').first.evaluate('''(button, direction) => {
      button.parentElement.dir = direction;
      button.after(button.cloneNode(true));
    }''', direction)
    zones = page.locator('.icon-btn--compact').evaluate_all('''buttons => buttons.slice(0, 2).map(button => {
      const box = button.getBoundingClientRect();
      const style = getComputedStyle(button, '::before');
      const left = box.left + button.clientLeft + parseFloat(style.left);
      return {left, right: left + parseFloat(style.width), height: parseFloat(style.height)};
    }).sort((a, b) => a.left - b.left)''')
    assert all(zone['height'] == 44 for zone in zones)
    assert zones[0]['right'] <= zones[1]['left']


@pytest.mark.parametrize('case', ['expired', 'wrong-path', 'url', 'none', 'malformed'])
def test_persistence_guards(page, live_url, case):
    index_page(page, live_url)
    page.evaluate('''kind => {
      const saved = {path: kind === 'wrong-path' ? '/other' : location.pathname,
        timestamp: Date.now() - (kind === 'expired' ? 301000 : 0), values: {q: 'domain-12', tag: 'two'}};
      sessionStorage.setItem('venomlist:/demo/list#domains', kind === 'malformed' ? '{bad' : JSON.stringify(saved));
    }''', case)
    if case == 'none':
        html = create_app().test_client().get('/demo/list?example=index').text.replace('data-persist="handoff"', 'data-persist="none"')
        page.route('**/demo/list?*', lambda route: route.fulfill(status=200, content_type='text/html', body=html))
    page.goto(live_url + '/demo/list?example=index' + ('&q=domain-7' if case == 'url' else ''))
    assert page.locator('[data-list-search]').input_value() == ('domain-7' if case == 'url' else '')
    assert page.locator('select[name=tag]').input_value() == ''
    if case == 'none':
        before = page.evaluate('JSON.stringify(sessionStorage)')
        page.locator('[data-list-search]').fill('changed')
        assert page.evaluate('JSON.stringify(sessionStorage)') == before
    else:
        assert page.evaluate('sessionStorage.length') == 0


def test_none_chip_custom_value_and_empty_scope(page, live_url):
    html = create_app().test_client().get('/demo/list?example=index').text
    html = html.replace('data-chip="stale"', 'data-chip="empty"').replace('data-none-value="__none__"', 'data-none-value="empty"')
    html = html.replace('data-count-scope="tag"', 'data-count-scope=""').replace('data-filter-show="stale"', 'data-filter-show="   "')
    page.route('**/demo/list?*', lambda route: route.fulfill(status=200, content_type='text/html', body=html))
    index_page(page, live_url)
    page.locator('[data-chip="empty"]').click()
    assert page.locator('[data-row]:visible').count() == 90
    page.locator('select[name=tag]').select_option('two')
    assert page.locator('[data-row]:visible').count() == 30
    assert page.locator('[data-chip="empty"] [data-chip-count]').inner_text() == '90'


def test_compact_icon_geometry_and_panel_headers(page, live_url):
    index_page(page, live_url)
    button = page.locator('.icon-btn--compact').first
    assert button.bounding_box()['height'] == 28
    assert button.evaluate("el => parseFloat(getComputedStyle(el, '::before').height)") == 44
    row = page.locator('[data-id="1"]')
    height = row.bounding_box()['height']
    neighbor = row.locator('a').bounding_box()
    bounds = button.bounding_box()
    assert neighbor['x'] >= bounds['x'] + bounds['width'] + 8
    button.evaluate('el => el.remove()')
    assert row.bounding_box()['height'] == height
    page.evaluate('''() => {
      const panel = document.createElement('div'); panel.className = 'panel';
      document.querySelector('.table-scroll').before(panel);
      panel.append(document.querySelector('.table-scroll'));
      panel.insertAdjacentHTML('afterbegin', '<div class="sort-control">Sort</div>');
    }''')
    colors = page.locator('.panel th, .panel .sort-control').evaluate_all('els => els.map(el => getComputedStyle(el).borderBottomColor)')
    assert len(set(colors)) == 1
    ordinary_border = page.locator('.panel').evaluate('''el => {
      const probe = document.createElement('div');
      probe.style.borderBottom = '1px solid var(--border)'; el.append(probe);
      const color = getComputedStyle(probe).borderBottomColor; probe.remove(); return color;
    }''')
    assert colors[0] != ordinary_border


def test_default_sort_and_refresh_keep_lazy_limit(page, live_url):
    html = create_app().test_client().get('/demo/list?example=index').text
    html = html.replace('data-sort=""', 'data-sort="number"')
    page.route('**/demo/list?*', lambda route: route.fulfill(status=200, content_type='text/html', body=html))
    index_page(page, live_url)
    assert page.locator('[data-row]:visible').count() == 50
    page.locator('[data-list]').dispatch_event('venomlist:refresh')
    assert page.locator('[data-row]:visible').count() == 50
    page.locator('[data-sort-key=number]').click()
    assert page.locator('[data-row]:visible').count() == 180
    page.locator('[data-list-search]').fill('domain-12')
    page.locator('[data-sort-key=number]').click()
    page.locator('[data-list-reset]').click()
    assert page.locator('[data-row]:visible').count() == 50


def test_server_input_reset_preserves_example(page, live_url):
    page.goto(live_url + '/demo/list-server?example=input&date=2026-01-02')
    page.locator('[data-list-reset]').click()
    assert 'example=input' in page.url and 'date=' not in page.url
    assert page.locator('input[type=date]').count() == 1
    assert page.locator('[data-list-reset]').get_attribute('aria-disabled') == 'true'


def test_preselected_filter_reset_and_post(page, live_url):
    html = create_app().test_client().get('/demo/list').text
    html = html.replace('data-row-select', 'checked data-row-select')
    page.route('**/demo/list', lambda route: route.fulfill(status=200, content_type='text/html', body=html))
    page.goto(live_url + '/demo/list')
    page.locator('[data-list]').evaluate("el => el.addEventListener('venomlist:selection', e => window.ids = e.detail.ids)")
    page.locator('select[name=brand]').select_option('alpha')
    assert page.locator('[data-row-select]:checked').count() == 180
    assert page.locator('[data-row-select]:checked:disabled').count() == 120
    assert page.locator('[data-selection-count]').inner_text() == '60'
    assert sorted(page.evaluate('window.ids'), key=int) == [str(i) for i in range(3, 181, 3)]
    page.locator('[data-list-reset]').click()
    assert page.locator('[data-row-select]:checked:enabled').count() == 180
    page.locator('select[name=brand]').select_option('alpha')
    with page.expect_response('**/demo/list-selection') as response:
        page.locator('[data-submit-selection]').click()
    assert response.value.json()['ids'] == [str(i) for i in range(3, 181, 3)]


@pytest.mark.parametrize('forms', [None, 'one|two', 'one||many'])
def test_confirmation_invalid_forms(page, live_url, forms):
    page.goto(live_url + '/demo/list')
    page.locator('[data-row-select]').first.check()
    page.locator('[data-demo-delete]').evaluate('''(button, forms) => {
      button.dataset.confirm = 'Delete {n} {noun}?';
      button.dataset.confirmCount = '2';
      if (forms !== null) button.dataset.confirmForms = forms;
    }''', forms)
    page.locator('[data-demo-delete]').click()
    assert page.locator('[data-confirm-text]').inner_text() == 'Delete 2?'


def test_drawer_respects_prevented_escape(page, live_url):
    page.set_viewport_size({'width': 360, 'height': 800})
    page.goto(live_url + '/demo/sidebar')
    toggle = page.locator('[data-sidebar-toggle]')
    toggle.click()
    page.locator('#sidebar').evaluate("el => el.addEventListener('keydown', e => e.preventDefault(), {once:true})")
    page.keyboard.press('Escape')
    assert toggle.get_attribute('aria-expanded') == 'true'
    page.keyboard.press('Escape')
    assert toggle.get_attribute('aria-expanded') == 'false'


@pytest.mark.parametrize('width', [360, 1600])
def test_banner_action_post_and_responsive_index(page, live_url, width, screenshot):
    page.set_viewport_size({'width': width, 'height': 1000})
    index_page(page, live_url)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    banner = page.locator('.banner--warning')
    banner.locator('summary').click()
    assert banner.locator('li').count() == 2
    screenshot(page, f'index-rich-banner-{width}')
    with page.expect_response('**/demo/list-selection') as response:
        banner.locator('button[type=submit]').click()
    assert response.value.json() == {'ids': ['1', '2'], 'fields': ['csrf_token', 'ids']}


def test_banner_actions_positional(render):
    html = render('''{% import 'venom_ui/macros.html' as ui %}
      {{ ui.banner('info', 'Text', None, [{'label': 'Undo', 'action': '/undo', 'fields': {}}], false, true) }}''')
    assert 'banner--inline' in html and 'banner__close' not in html
    assert Tags(html).find('form')[0]['action'] == '/undo'


@pytest.mark.parametrize(('count', 'noun'), [(1, 'домен'), (2, 'домена'), (5, 'доменов'), (11, 'доменов'), (21, 'домен')])
@pytest.mark.parametrize('explicit', [False, True])
def test_confirmation_plural(page, live_url, count, noun, explicit):
    page.goto(live_url + '/demo/list')
    page.evaluate('''({count, explicit}) => {
      const boxes = [...document.querySelectorAll('[data-row-select]')];
      boxes.slice(0, explicit ? 1 : count).forEach(box => box.checked = true);
      boxes[0].dispatchEvent(new Event('change', {bubbles: true}));
      const button = document.querySelector('[data-demo-delete]');
      button.dataset.confirm = 'Удалить {n} {noun}?';
      button.dataset.confirmForms = 'домен|домена|доменов';
      if (explicit) button.dataset.confirmCount = count;
    }''', {'count': count, 'explicit': explicit})
    page.locator('[data-demo-delete]').click()
    assert page.locator('[data-confirm-text]').inner_text() == f'Удалить {count} {noun}?'
    assert page.evaluate("n => VenomUI.pluralRu(n, 'домен', 'домена', 'доменов')", count) == noun
    page.locator('[data-confirm-cancel]').click()
    assert page.locator('[data-row]').count() == 180


def test_confirmation_form_counts_unrevealed_selection(page, live_url):
    page.goto(live_url + '/demo/list')
    page.locator('[data-select-all]').check()
    page.locator('[data-submit-selection]').evaluate('''button => {
      button.form.dataset.confirm = 'Удалить {n} {noun}?';
      button.form.dataset.confirmForms = 'домен|домена|доменов';
    }''')
    page.locator('[data-submit-selection]').click()
    assert page.locator('[data-confirm-text]').inner_text() == 'Удалить 180 доменов?'
    with page.expect_response('**/demo/list-selection') as response:
        page.locator('[data-confirm-accept]').click()
    assert len(response.value.json()['ids']) == 180


def test_long_table_screen_reader_labels_do_not_grow_page(page, live_url):
    page.goto(live_url + '/demo/list')
    page.evaluate('''() => {
      const scroll = document.querySelector('.table-scroll');
      scroll.innerHTML = '<table class="data-table"><tbody>' + Array.from({length:500}, (_, i) =>
        '<tr><td>Row ' + i + '</td></tr>').join('') + '</tbody></table>';
    }''')
    height = page.evaluate('document.documentElement.scrollHeight')
    page.locator('.table-scroll').evaluate('''scroll => {
      scroll.querySelectorAll('td').forEach((cell, i) => {
        cell.insertAdjacentHTML('beforeend', '<label class="visually-hidden">Select row ' + i + '</label>');
      });
      scroll.scrollTop = scroll.scrollHeight;
    }''')
    assert page.locator('.table-scroll .visually-hidden').count() == 500
    assert page.evaluate('document.documentElement.scrollHeight') == height


@pytest.mark.parametrize('width', [360, 860])
def test_status_pill_never_wraps(page, live_url, width):
    page.set_viewport_size({'width': width, 'height': 800})
    page.goto(live_url + '/demo/list')
    pill = page.locator('.pill').first
    pill.evaluate("el => { el.textContent = 'не проверялся'; el.parentElement.style.width = '50px'; }")
    assert pill.evaluate("el => getComputedStyle(el).whiteSpace") == 'nowrap'
    assert pill.evaluate('''el => {
      const range = document.createRange(); range.selectNodeContents(el);
      return range.getClientRects().length === 1;
    }''')


def test_filter_input_render(render):
    html = render('''{% import 'venom_ui/list.html' as list %}
      {{ list.input('date', 'Date', value='2026-01-02', type='date', attrs={'min': '2025-01-01'}) }}
      {{ list.input('other', 'Visible', label_visible=true) }}''')
    fields = Tags(html).find('input')
    assert fields[0] == {'type': 'date', 'name': 'date', 'value': '2026-01-02', 'data-list-filter': None, 'min': '2025-01-01'}
    assert 'class="visually-hidden">Date' in html
    assert 'class="list-dropdown__label">Visible' in html


@pytest.mark.parametrize('width', [360, 1600])
def test_filter_input_alignment_and_client_filter(page, live_url, width, screenshot):
    page.set_viewport_size({'width': width, 'height': 1000})
    page.goto(live_url + '/demo/list?example=input')
    selectors = ['[data-list-search]', '[data-chip="new"]', 'select[name=brand]', 'input[name=date]']
    boxes = [page.locator(selector).bounding_box() for selector in selectors]
    if width == 1600:
        centres = [box['y'] + box['height'] / 2 for box in boxes]
        assert max(centres) - min(centres) <= 1
    heights = [boxes[i]['height'] for i in [0, 2, 3]]
    assert max(heights) - min(heights) <= 1
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    screenshot(page, f'filter-input-{width}')
    date = page.locator('[data-row]').first.get_attribute('data-filter-date')
    page.locator('input[name=date]').fill(date)
    page.locator('input[name=date]').dispatch_event('change')
    assert page.locator('[data-row]:visible').count() == 1
    page.locator('[data-list-reset]').click()
    assert page.locator('input[name=date]').input_value() == ''


def test_date_input_keeps_focus_ring_between_segments(page, live_url):
    page.goto(live_url + '/demo/list?example=input')
    date = page.locator('input[name=date]')
    page.locator('select[name=brand]').focus()
    page.keyboard.press('Tab')

    def assert_focus_ring():
        assert date.evaluate('(el) => document.activeElement === el')
        style = date.evaluate('''(el) => {
            const computed = getComputedStyle(el);
            return {shadow: computed.boxShadow, border: computed.borderColor};
        }''')
        assert style['shadow'] != 'none'
        return style

    initial = assert_focus_ring()
    for key in ['ArrowUp', 'ArrowRight', '2', 'Tab', 'ArrowUp', 'Shift+Tab', 'ArrowLeft']:
        page.keyboard.press(key)
        assert assert_focus_ring() == initial


def test_filter_input_server_change(page, live_url):
    page.goto(live_url + '/demo/list-server?example=input')
    page.locator('input[name=date]').fill('2026-01-02')
    page.wait_for_url('**/*date=2026-01-02*')
    page.wait_for_load_state('load')
    assert page.locator('[data-row]').count() == 1
    assert page.locator('[data-row]').get_attribute('data-id') == '1'
    assert page.locator('input[name=date]').input_value() == '2026-01-02'
