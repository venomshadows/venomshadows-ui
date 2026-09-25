"""Необязательные проверки реального браузера: pip install playwright; VENOM_UI_BROWSER=chrome."""

import pytest

from demo_list_routes import create_app


@pytest.mark.parametrize(('width', 'height'), [(1600, 36), (360, 44)])
@pytest.mark.parametrize('demo', ['list', 'list-server'])
def test_chip_resting_and_pressed_styles(page, live_url, width, height, demo):
    page.set_viewport_size({'width': width, 'height': 1000})
    page.goto(f'{live_url}/demo/{demo}?status=new')
    pressed = page.locator('[data-chip="new"]')
    resting = page.locator('[data-chip=""]')
    assert pressed.get_attribute('aria-pressed') == 'true'
    assert resting.get_attribute('aria-pressed') == 'false'
    for property in ('color', 'borderColor', 'backgroundColor'):
        read = '(el, property) => getComputedStyle(el)[property]'
        assert pressed.evaluate(read, property) != resting.evaluate(read, property)
    assert resting.bounding_box()['height'] == height
    assert pressed.bounding_box()['height'] == height


def test_row_checkbox_keyboard_focus(page, live_url):
    page.goto(live_url + '/demo/list')
    page.locator('[data-select-all]').focus()
    page.keyboard.press('Tab')
    # Sort buttons precede row controls in the keyboard order.
    for _ in range(10):
        if page.locator('[data-row-select]').first.evaluate('(el) => el === document.activeElement'):
            break
        page.keyboard.press('Tab')
    assert page.locator('[data-row-select]').first.evaluate('''el => {
        const style = getComputedStyle(el);
        const probe = document.createElement('span');
        probe.style.color = 'var(--color-accent)';
        el.parentElement.append(probe);
        const matches = el.matches(':focus-visible') && style.outlineStyle === 'solid'
            && style.outlineWidth === '2px' && style.outlineOffset === '2px'
            && style.outlineColor === getComputedStyle(probe).color && style.boxShadow === 'none';
        probe.remove();
        return matches;
    }''')


def test_numeric_column_width_in_fixed_layout(browser, render):
    html = render('''{% import "venom_ui/list.html" as list %}
        <style>table {table-layout: fixed; width: 600px; border-spacing: 0}
        th, td {padding: 0; border: 0}</style>
        {% call list.data_table("width-test", columns) %}
        <tbody><tr><td>First</td><td>Second</td></tr></tbody>
        {% endcall %}''', columns=[dict(key='first', label='First', width=192),
                                  dict(key='second', label='Second')])
    page = browser.new_page()
    page.set_content(html)
    assert page.locator('th').first.get_attribute('width') == '192'
    assert page.locator('th').first.bounding_box()['width'] == pytest.approx(192)
    assert page.locator('td').first.bounding_box()['width'] == pytest.approx(192)
    page.close()


def test_filter_sort_selection_and_state(browser, live_url):
    page = browser.new_page(viewport={'width': 1600, 'height': 900})
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(live_url + '/demo/list')
    visible = page.locator('[data-row]:visible')
    assert visible.count() == 50
    page.locator('[data-select-all]').check()
    assert page.locator('[data-selection-count]').inner_text() == '50'
    page.locator('[data-row-select]').first.uncheck()
    assert page.locator('[data-select-all]').evaluate('(el) => el.indeterminate')
    page.locator('[data-chip="new"]').click()
    assert visible.count() == 45
    assert page.locator('[data-chip="used"] [data-chip-count]').inner_text() == '45'
    page.locator('select[name="brand"]').select_option('alpha')
    assert visible.count() == 15
    assert page.locator('[data-chip="used"] [data-chip-count]').inner_text() == '15'
    page.locator('[data-sort-key="number"]').click()
    values = visible.evaluate_all('(rows) => rows.map(row => Number(row.dataset.sortNumber))')
    assert values == sorted(values)
    page.locator('[data-sort-key="number"]').click()
    values = visible.evaluate_all('(rows) => rows.map(row => Number(row.dataset.sortNumber))')
    assert values == sorted(values, reverse=True)
    page.reload()
    assert visible.count() == 15
    assert page.locator('[aria-sort="descending"]').count() == 1
    page.locator('[data-list-search]').fill('DOMAIN-12.EXAMPLE ALPHA')
    assert visible.count() == 1
    page.locator('[data-list-search]').fill('missing')
    assert page.locator('[data-empty-row]').is_visible()
    assert page.locator('[data-bulk-bar]').is_hidden()
    page.locator('[data-list-reset]').click()
    assert visible.count() == 50
    assert page.locator('[data-list-reset]').is_disabled()
    page.locator('[data-reveal-more]').click()
    assert visible.count() >= 100
    page.locator('[data-chip="used"]').click()
    page.goto(live_url + '/demo/list')
    assert page.locator('[data-chip="used"]').get_attribute('aria-pressed') == 'true'
    page.goto(live_url + '/demo/list?status=new')
    assert page.locator('[data-chip="new"]').get_attribute('aria-pressed') == 'true'
    assert page.locator('select[name="brand"]').input_value() == ''
    page.goto(live_url + '/demo/list?status=invalid&sort=invalid&dir=invalid')
    assert page.locator('[data-chip=""]').get_attribute('aria-pressed') == 'true'
    assert not errors
    page.close()


@pytest.mark.parametrize('width', [1600, 360])
@pytest.mark.parametrize('path', ['/demo/list', '/demo/list-server'])
def test_responsive_and_server(browser, live_url, width, path):
    page = browser.new_page(viewport={'width': width, 'height': 900})
    page.goto(live_url + path)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    if width == 360:
        page.locator('table').evaluate('(table) => table.classList.remove("data-table--stacked")')
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
        assert page.locator('.table-scroll').evaluate('(el) => el.scrollWidth > el.clientWidth')
    if path.endswith('server'):
        page.locator('[data-chip="new"]').click()
        page.wait_for_url('**/*status=new*')
        assert page.locator('[data-row]').count() == 45
        page.locator('[data-list-search]').fill('domain-12')
        page.wait_for_url('**/*q=domain-12*')
        assert page.locator('[data-row]').count() == 4
    else:
        page.locator('[data-select-all]').check()
        page.locator('[data-demo-delete]').click()
        assert page.locator('[data-list-count]').inner_text() == '130 из 130'
        assert page.locator('[data-bulk-bar]').is_hidden()
    page.close()


def test_stable_sort_and_selection_event(browser, live_url):
    page = browser.new_page()
    page.goto(live_url + '/demo/list')
    page.evaluate('''() => {
      document.querySelectorAll('[data-row]').forEach(row => row.dataset.sortNumber = '1');
      document.querySelector('table').addEventListener('venomlist:selection', event => window.selectedIds = event.detail.ids);
    }''')
    initial = page.locator('[data-row]').evaluate_all('(rows) => rows.map(row => row.dataset.id)')
    page.locator('[data-sort-key="number"]').click()
    page.locator('[data-sort-key="number"]').click()
    assert page.locator('[data-row]').evaluate_all('(rows) => rows.map(row => row.dataset.id)') == initial
    page.locator('[data-row-select]').first.check()
    assert page.evaluate('window.selectedIds') == ['1']
    page.locator('[data-clear-selection]').click()
    assert page.evaluate('window.selectedIds') == []
    page.locator('[data-sort-key="date"]').click()
    dates = page.locator('[data-row]').evaluate_all('(rows) => rows.map(row => row.dataset.sortDate)')
    assert dates == sorted(dates)
    page.close()


def test_no_observer_and_normalization(browser, live_url):
    page = browser.new_page()
    page.add_init_script('delete window.IntersectionObserver;')
    page.goto(live_url + '/demo/list')
    assert page.locator('[data-row]:visible').count() == 180
    page.locator('[data-row]').first.evaluate('(row) => row.dataset.search = "Ёжик зелёный"')
    page.locator('[data-list-search]').fill('ЗЕЛЕНЫЙ ежик')
    assert page.locator('[data-row]:visible').count() == 1
    page.close()


@pytest.mark.parametrize('key', ['number', 'date'])
def test_invalid_sort_values_stay_last(browser, live_url, key):
    page = browser.new_page()
    page.goto(live_url + '/demo/list')
    page.locator('[data-row]').evaluate_all('''(rows, key) => {
      rows[0].setAttribute('data-sort-' + key, '');
      rows[1].setAttribute('data-sort-' + key, 'invalid');
    }''', key)
    for direction in ['ascending', 'descending']:
        page.locator(f'[data-sort-key="{key}"]').click()
        assert page.locator(f'th[aria-sort="{direction}"]').count() == 1
        ids = page.locator('[data-row]').evaluate_all('(rows) => rows.map(row => row.dataset.id)')
        assert ids[-2:] == ['1', '2']
    page.close()


@pytest.mark.parametrize('path', ['/demo/list', '/demo/list-server'])
def test_refresh_labels_and_scoped_selection(browser, live_url, path):
    page = browser.new_page()
    page.goto(live_url + path)
    page.evaluate('''() => {
      const table = document.querySelector('table');
      const row = table.querySelector('[data-row]').cloneNode(true);
      row.dataset.id = 'added';
      row.querySelectorAll('td').forEach(cell => cell.removeAttribute('data-label'));
      row.querySelector('[data-row-select]').remove();
      row.cells[1].insertAdjacentHTML('beforeend', '<input type="checkbox" id="unrelated">');
      table.tBodies[0].prepend(row);
      table.dispatchEvent(new Event('venomlist:refresh'));
      table.addEventListener('venomlist:selection', event => window.ids = event.detail.ids);
    }''')
    assert page.locator('[data-id="added"] td').nth(1).get_attribute('data-label') == 'Домен'
    page.locator('[data-select-all]').check()
    assert not page.locator('#unrelated').is_checked()
    assert 'added' not in page.evaluate('window.ids')
    page.locator('[data-clear-selection]').click()
    assert page.evaluate('window.ids') == []
    page.close()


def test_server_selection_clean_submit_and_sort(browser, live_url):
    from urllib.parse import parse_qs, urlsplit
    page = browser.new_page()
    page.goto(live_url + '/demo/list-server?sort=number&dir=desc')
    page.locator('[data-select-all]').check()
    assert page.locator('[data-selection-count]').inner_text() == '180'
    page.locator('[data-row-select]').first.uncheck()
    assert page.locator('[data-select-all]').evaluate('(box) => box.indeterminate')
    page.locator('[data-chip="new"]').click()
    page.wait_for_url('**/*status=new*')
    assert parse_qs(urlsplit(page.url).query, keep_blank_values=True) == {
        'status': ['new'], 'sort': ['number'], 'dir': ['desc']}
    assert page.locator('[data-bulk-bar]').is_hidden()
    # A persisted pageshow must restore only fields disabled by submit cleanup.
    page.evaluate('''() => {
      const form = document.querySelector('form.filter-bar');
      form.addEventListener('submit', event => event.preventDefault());
      form.requestSubmit();
    }''')
    assert page.locator('[data-list-search]').is_disabled()
    assert page.locator('[data-list-filter]').is_disabled()
    page.evaluate("window.dispatchEvent(new PageTransitionEvent('pageshow', {persisted: true}))")
    assert page.locator('[data-list-search]').is_enabled()
    assert page.locator('[data-list-filter]').is_enabled()
    page.close()


def test_server_without_javascript(browser, live_url):
    page = browser.new_page(java_script_enabled=False)
    page.goto(live_url + '/demo/list-server?sort=number&dir=desc')
    page.locator('[data-list-search]').fill('domain-12')
    page.locator('[data-list-search]').press('Enter')
    page.wait_for_url('**/*q=domain-12*')
    assert 'sort=number' in page.url and 'dir=desc' in page.url
    assert page.locator('[data-row]').count() == 11
    page.goto(live_url + '/demo/list-server?q=missing')
    assert page.locator('[data-empty-row]').is_visible()
    page.close()


@pytest.mark.parametrize('fixed', [True, False])
def test_lazy_keeps_revealing_while_sentinel_intersects(browser, live_url, fixed):
    page = browser.new_page(viewport={'width': 1600, 'height': 900})
    page.add_init_script('''document.addEventListener('DOMContentLoaded', () => {
      // Tiny rows keep the sentinel intersecting across several batches.
      const style = document.createElement('style');
      style.textContent = '.data-table tbody [data-detail-toggle] {height:1px;min-height:0;padding:0;border:0;font-size:0} .data-table tbody tr {height:1px} .data-table tbody td {height:1px;padding:0;font-size:0;border:0} .data-table tbody label {min-height:0;height:1px} .data-table tbody input {height:1px} .data-table tbody .pill {height:1px;min-height:0;padding:0;border:0;font-size:0;line-height:0}';
      document.head.appendChild(style);
    });''')
    if not fixed:
        page.add_init_script('''document.addEventListener('DOMContentLoaded', () => {
          document.querySelector('.table-scroll').classList.remove('table-scroll--fixed');
        });''')
    page.goto(live_url + '/demo/list')
    page.wait_for_function("document.querySelectorAll('[data-row]:not([hidden])').length === 180")
    # Keep >50 matches so the filter reset exercises the same sustained intersection.
    page.locator('[data-list-filter]').select_option('alpha')
    page.wait_for_function("document.querySelectorAll('[data-row]:not([hidden])').length === 60")
    page.close()


@pytest.mark.parametrize('width', [1600, 360])
def test_sticky_header_and_stacked_geometry(browser, live_url, width):
    page = browser.new_page(viewport={'width': width, 'height': 900})
    page.goto(live_url + '/demo/list')
    wrapper = page.locator('.table-scroll--fixed')
    header = page.locator('thead' if width == 360 else 'thead th').first
    before = header.bounding_box()['y']
    wrapper.evaluate('(el) => el.scrollTop = 300')
    page.wait_for_function("document.querySelector('.table-scroll').scrollTop === 300")
    assert abs(header.bounding_box()['y'] - before) < 2
    wrapper.evaluate('(el) => el.scrollTop = 0')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    if width == 360:
        assert abs(page.locator('thead').bounding_box()['width'] - wrapper.bounding_box()['width']) < 2
        cell = page.locator('[data-row]').first.locator('td').last
        assert cell.evaluate("el => getComputedStyle(el, '::before').textAlign") == 'start'
        assert page.locator('thead th').first.evaluate("el => getComputedStyle(el).backgroundColor === getComputedStyle(el.closest('thead')).backgroundColor")
        select = page.locator('[data-row]').first.locator('.data-table__select')
        assert select.evaluate("el => getComputedStyle(el).position") == 'absolute'
        assert select.locator('label').bounding_box()['height'] >= 44
        first_value = page.locator('[data-row]').first.locator('td').nth(1)
        assert abs(first_value.bounding_box()['y'] - select.bounding_box()['y']) < 2
        assert page.locator('.list-chips').evaluate("el => getComputedStyle(el).scrollbarWidth") == 'thin'
    page.close()


@pytest.mark.parametrize('javascript', [True, False])
def test_server_reset_navigation(browser, live_url, javascript):
    page = browser.new_page(java_script_enabled=javascript)
    page.goto(live_url + '/demo/list-server?q=missing&status=new&brand=alpha&page=3&sort=number&dir=desc')
    reset = page.locator('[data-list-reset]')
    assert reset.get_attribute('href') == '/demo/list-server?sort=number&dir=desc'
    reset.click()
    page.wait_for_url('**/list-server?sort=number&dir=desc')
    assert page.locator('[data-row]').count() == 180
    assert reset.get_attribute('aria-disabled') == 'true'
    assert reset.evaluate('(el) => getComputedStyle(el).pointerEvents') == 'none'
    page.close()


def test_lazy_selection_survives_sort_and_matching_filter(browser, live_url):
    page = browser.new_page(viewport={'width': 1600, 'height': 900})
    page.add_init_script('window.IntersectionObserver = class { observe() {} disconnect() {} };')
    page.goto(live_url + '/demo/list')
    page.evaluate('''() => {
      document.querySelector('table').addEventListener('venomlist:selection', event => window.selectedIds = event.detail.ids);
      document.querySelector('[data-reveal-more]').click();
    }''')
    assert page.locator('[data-row]:visible').count() == 100
    box = page.locator('[data-id="60"] [data-row-select]')
    box.evaluate('(el) => { el.checked = true; el.dispatchEvent(new Event("change", {bubbles:true})); }')
    page.locator('[data-sort-key="domain"]').click()
    assert page.locator('[data-row]:visible').count() == 100
    assert box.is_checked()
    assert page.evaluate('window.selectedIds') == ['60']
    # The descending order puts row 60 outside the same 100-row lazy window.
    page.locator('[data-sort-key="domain"]').click()
    assert page.locator('[data-row]:visible').count() == 100
    assert page.locator('[data-id="60"]').is_hidden()
    assert box.is_checked()
    assert page.evaluate('window.selectedIds') == ['60']
    page.locator('[data-list-search]').fill('domain-')
    assert page.locator('[data-row]:visible').count() == 50
    assert box.is_checked()
    page.locator('[data-list-search]').fill('missing')
    assert not box.is_checked()
    assert page.evaluate('window.selectedIds') == []
    page.close()


@pytest.mark.parametrize('query', ['?sort=domain', '?q=&status=invalid&brand=invalid'])
def test_url_clears_prefilled_controls(browser, live_url, query):
    page = browser.new_page()
    def prefill(route):
        html = create_app().test_client().get('/demo/list').text
        html = html.replace('name="q" value=""', 'name="q" value="prefilled"')
        html = html.replace('name="status" value=""', 'name="status" value="new"')
        html = html.replace('<option value="" selected>', '<option value="">')
        html = html.replace('<option value="alpha">', '<option value="alpha" selected>')
        route.fulfill(status=200, content_type='text/html', body=html)
    page.route('**/demo/list?*', prefill)
    page.goto(live_url + '/demo/list' + query)
    for selector in ['[data-list-search]', '[data-chip-value]', '[data-list-filter]']:
        assert page.locator(selector).input_value() == ''
    page.locator('[data-list-search]').fill('domain-12')
    page.locator('[data-list-reset]').click()
    assert page.locator('[data-list-search]').input_value() == ''
    assert page.locator('[data-list-reset]').is_disabled()
    page.close()


def test_chip_hover_and_empty_count(browser, live_url):
    page = browser.new_page(java_script_enabled=False)
    page.goto(live_url + '/demo/list')
    chip = page.locator('[data-chip="new"]')
    assert chip.locator('[data-chip-count]').evaluate('(el) => getComputedStyle(el).display') == 'none'
    chip.hover()
    assert chip.evaluate('''el => {
      const probe = document.createElement('span');
      probe.style.color = 'var(--color-text-primary)';
      probe.style.borderColor = 'var(--border-bright)';
      el.appendChild(probe);
      const matches = getComputedStyle(el).color === getComputedStyle(probe).color && getComputedStyle(el).borderColor === getComputedStyle(probe).borderColor;
      probe.remove();
      return matches;
    }''')
    page.close()


@pytest.mark.parametrize('mode', ['list', 'list-server'])
def test_stacked_roles_on_init_and_refresh(browser, live_url, mode):
    page = browser.new_page(viewport={'width': 360, 'height': 800})
    page.goto(live_url + '/demo/' + mode)
    def assert_roles():
        assert page.locator('table').get_attribute('role') == 'table'
        for selector, role in [('thead, tbody', 'rowgroup'), ('tr', 'row'), ('th', 'columnheader'), ('td', 'cell')]:
            assert page.locator('table ' + selector if ',' not in selector else 'table thead, table tbody').evaluate_all(
                '(els, role) => els.every(el => el.getAttribute("role") === role)', role)
        assert page.locator('[data-empty-row] td').get_attribute('data-label') is None
        assert page.locator('th[aria-sort]').count() == 4
    assert_roles()
    page.evaluate('''() => {
      const table = document.querySelector('table');
      table.querySelector('tbody').insertAdjacentHTML('beforeend', '<tr data-row data-added><td>Added</td></tr>');
      table.dispatchEvent(new Event('venomlist:refresh'));
    }''')
    assert_roles()
    assert page.locator('[data-added] td').get_attribute('data-label') is not None
    page.close()


def test_selection_event_ignores_reordering(browser, live_url):
    page = browser.new_page()
    page.goto(live_url + '/demo/list')
    page.evaluate('''() => {
      window.selections = [];
      document.querySelector('table').addEventListener('venomlist:selection', e => selections.push(e.detail.ids));
    }''')
    page.locator('[data-row-select]').nth(0).check()
    page.locator('[data-row-select]').nth(1).check()
    assert page.evaluate('selections.length') == 2
    page.locator('[data-sort-key="domain"]').click()
    page.locator('[data-sort-key="domain"]').click()
    page.locator('table').evaluate("el => el.dispatchEvent(new Event('venomlist:refresh'))")
    assert page.evaluate('selections.length') == 2
    page.locator('[data-clear-selection]').click()
    assert page.evaluate('selections') == [['1'], ['1', '2'], []]
    page.close()


@pytest.mark.parametrize('width', [360, 860])
def test_chip_focus_ring_inside_scrollport(browser, live_url, width):
    page = browser.new_page(viewport={'width': width, 'height': 800})
    page.goto(live_url + '/demo/list')
    page.keyboard.press('Tab')
    for chip in [page.locator('[data-chip]').first, page.locator('[data-chip]').last]:
        chip.focus()
        assert chip.evaluate('''el => {
          const group = el.closest('.list-chips');
          group.scrollLeft = el === group.querySelector('[data-chip]') ? 0 : group.scrollWidth;
          const rect = el.getBoundingClientRect(), bounds = group.getBoundingClientRect();
          const style = getComputedStyle(el);
          const ring = parseFloat(style.outlineWidth) + parseFloat(style.outlineOffset);
          return el.matches(':focus-visible') && ring === 4 &&
            rect.left - ring >= bounds.left - .1 && rect.right + ring <= bounds.right + .1 &&
            rect.top - ring >= bounds.top - .1 &&
            rect.bottom + ring <= bounds.top + group.clientHeight + .1;
        }''')
    page.close()


def test_stacked_empty_state_centered(browser, live_url):
    page = browser.new_page(viewport={'width': 360, 'height': 800})
    page.goto(live_url + '/demo/list')
    assert page.get_by_role('search', name='Фильтры: Домены').count() == 1
    page.locator('[data-row-select]').first.check()
    assert page.get_by_role('region', name='Массовые действия: Домены').is_visible()
    page.locator('[data-list-search]').fill('missing')
    cell = page.locator('[data-empty-row] td')
    assert cell.is_visible()
    assert cell.evaluate('''el => {
      const range = document.createRange();
      range.selectNodeContents(el);
      const text = range.getBoundingClientRect(), cell = el.getBoundingClientRect();
      return Math.abs((text.left + text.right) / 2 - (cell.left + cell.right) / 2) < 1;
    }''')
    page.close()


def test_session_state_isolated_by_path(browser, live_url):
    page = browser.new_page()
    page.goto(live_url + '/demo/list')
    page.locator('[data-list-search]').fill('domain-12')
    assert page.evaluate("JSON.parse(sessionStorage.getItem('venomlist:/demo/list#domains')).q") == 'domain-12'
    page.route('**/other-list', lambda route: route.fulfill(status=200, content_type='text/html', body=create_app().test_client().get('/demo/list').text))
    page.goto(live_url + '/other-list')
    assert page.locator('[data-list-search]').input_value() == ''
    page.goto(live_url + '/demo/list')
    assert page.locator('[data-list-search]').input_value() == 'domain-12'
    page.close()


@pytest.mark.parametrize('action', ['clear-selection', 'demo-delete'])
def test_bulk_focus_before_hiding(browser, live_url, action):
    page = browser.new_page()
    page.goto(live_url + '/demo/list')
    page.locator('[data-row-select]').first.check()
    page.locator('[data-' + action + ']').focus()
    page.keyboard.press('Enter')
    assert page.locator('[data-select-all]').evaluate('el => el === document.activeElement')
    assert page.locator('[data-bulk-bar]').is_hidden()
    page.close()


@pytest.mark.parametrize('checkboxes', [True, False])
def test_final_reveal_focus(browser, live_url, checkboxes):
    page = browser.new_page()
    page.add_init_script('window.IntersectionObserver = class { observe() {} disconnect() {} };')
    page.goto(live_url + '/demo/list')
    page.evaluate('''checkboxes => {
      if (!checkboxes) document.querySelectorAll('[data-row-select]').forEach(el => el.remove());
      const button = document.querySelector('[data-reveal-more]');
      button.click(); button.click(); button.focus(); button.click();
    }''', checkboxes)
    target = '[data-id="151"] [data-row-select]' if checkboxes else '.table-scroll'
    assert page.locator(target).evaluate('el => el === document.activeElement')
    assert page.locator('[data-lazy-sentinel]').is_hidden()
    assert page.locator('[data-lazy-pending]').count() == 0
    page.close()


@pytest.mark.parametrize('js_class', [True, False])
def test_pending_before_list_script_and_without_js(browser, live_url, js_class):
    page = browser.new_page(java_script_enabled=js_class)
    page.route('**/list.js', lambda route: route.fulfill(status=200, body=''))
    page.goto(live_url + '/demo/list')
    assert page.locator('[data-lazy-pending]').count() == 130
    assert page.locator('[data-row]:visible').count() == (50 if js_class else 180)
    page.close()


@pytest.mark.parametrize(('width', 'touch'), [(690, False), (1600, True)])
def test_touch_sort_header_height_and_colors(browser, live_url, width, touch):
    page = browser.new_page(viewport={'width': width, 'height': 900}, has_touch=touch)
    page.goto(live_url + '/demo/list')
    page.locator('table').evaluate("el => el.classList.remove('data-table--stacked')")
    header = page.locator('th:has(> .th-sort)').first
    assert 44 <= header.bounding_box()['height'] <= 46
    button = header.locator('.th-sort')
    button.hover()
    assert button.evaluate("el => getComputedStyle(el).color === getComputedStyle(document.body).color")
    button.click()
    assert button.evaluate('''el => {
      const probe = document.createElement('span'); probe.style.color = 'var(--color-accent-text)';
      document.body.appendChild(probe);
      const result = getComputedStyle(el).color === getComputedStyle(probe).color;
      probe.remove(); return result;
    }''')
    page.close()


def test_slot_buttons_keep_core_styles(browser, live_url):
    page = browser.new_page()
    page.goto(live_url + '/demo/list')
    page.add_style_tag(content='.btn {background: rgb(1, 2, 3); color: rgb(4, 5, 6); padding: 3px;}')
    page.evaluate('''() => {
      document.querySelector('.filter-bar').insertAdjacentHTML('beforeend', '<button class="btn" id="slot">Action</button>');
    }''')
    page.locator('[data-row-select]').first.check()
    for selector in ['#slot', '[data-demo-delete]']:
        assert page.locator(selector).evaluate('el => getComputedStyle(el).backgroundColor') == 'rgb(1, 2, 3)'
        assert page.locator(selector).evaluate('el => getComputedStyle(el).color') == 'rgb(4, 5, 6)'
    assert page.locator('[data-demo-delete]').get_attribute('class') == 'btn btn--danger'
    page.close()


def test_original_order_uses_weak_keys_and_monotonic_indices(browser, live_url):
    page = browser.new_page()
    page.add_init_script('''window.NativeWeakMap = WeakMap;
      window.orderValues = [];
      window.WeakMap = class extends NativeWeakMap {
        set(key, value) { if (key instanceof HTMLTableRowElement && key.matches('[data-row]')) orderValues.push(value); return super.set(key, value); }
      };''')
    page.goto(live_url + '/demo/list')
    page.evaluate('''() => {
      const table = document.querySelector('table'), body = table.tBodies[0];
      for (let n = 0; n < 2; n++) {
        const row = body.querySelector('[data-row]').cloneNode(true);
        body.querySelector('[data-row]').remove(); body.appendChild(row);
        table.dispatchEvent(new Event('venomlist:refresh'));
      }
    }''')
    assert page.evaluate('orderValues') == list(range(182))
    page.close()


@pytest.mark.parametrize("javascript", [True, False])
def test_selection_plain_post(browser, live_url, javascript):
    page = browser.new_page(java_script_enabled=javascript)
    page.goto(live_url + "/demo/list")
    if javascript:
        page.locator("[data-select-all]").check()
        page.locator("[data-select-all]").uncheck()
    for id in ["2", "4"]:
        page.locator(f'[data-row-select][value="{id}"]').check()
    assert page.locator("[data-select-all]").get_attribute("name") is None
    with page.expect_response("**/demo/list-selection") as response:
        page.locator("[data-submit-selection]").click()
    assert response.value.json() == {"ids": ["2", "4"], "fields": ["csrf_token", "ids"]}
    page.close()


@pytest.mark.parametrize('demo', ['list', 'list-server'])
def test_stacked_header_scroll_and_sort(page, live_url, demo):
    page.set_viewport_size({'width': 360, 'height': 1000})
    page.goto(f'{live_url}/demo/{demo}')
    header = page.locator('.data-table thead tr')
    assert header.bounding_box()['height'] <= 44
    assert header.evaluate("el => getComputedStyle(el).flexWrap") == 'nowrap'
    assert header.evaluate('el => el.scrollWidth > el.clientWidth')
    assert page.locator('.th-sort').evaluate_all("els => els.every(el => getComputedStyle(el).whiteSpace === 'nowrap')")
    for direction in ('ascending', 'descending'):
        page.locator('.th-sort').last.click()
        assert page.locator('th[aria-sort="' + direction + '"]').count() == 1
        values = page.locator('[data-row]:visible').evaluate_all('rows => rows.map(row => Number(row.dataset.sortNumber))')
        assert values == sorted(values, reverse=direction == 'descending')
        assert header.bounding_box()['height'] <= 44
        active = page.locator('th[aria-sort="' + direction + '"]').bounding_box()
        box = header.bounding_box()
        assert active['x'] >= box['x']
        assert active['x'] + active['width'] <= box['x'] + box['width']
        assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    for index in range(page.locator('.th-sort').count()):
        header.evaluate('el => el.scrollLeft = 0')
        page.locator('.th-sort').nth(index).click()
        assert page.locator('th[aria-sort="ascending"], th[aria-sort="descending"]').count() == 1
    # Невидимые подписи остаются в DOM и не увеличивают высоту заголовка.
    hidden = header.locator('th').last
    assert hidden.evaluate("el => getComputedStyle(el).clipPath") == 'inset(50%)'
    assert hidden.evaluate("el => getComputedStyle(el).display") != 'none'
    assert header.bounding_box()['height'] <= 44


@pytest.mark.parametrize('width', [360, 1600])
def test_bulk_checkbox_menu(page, live_url, width, screenshot):
    page.set_viewport_size({'width': width, 'height': 1000})
    page.goto(live_url + '/demo/list')
    page.locator('[data-row-select]').first.check()
    bar = page.locator('[data-bulk-bar]')
    menu = bar.locator('details.checkbox-menu')
    summary = menu.locator('summary')
    summary.scroll_into_view_if_needed()
    height = bar.bounding_box()['height']
    if width == 1600:
        select = bar.locator('select').bounding_box()
        button = bar.locator('[data-demo-delete]').bounding_box()
        assert abs(select['y'] + select['height'] - button['y'] - button['height']) <= 1
        assert height < 100
    summary.click()
    panel = menu.locator('.checkbox-menu__panel')
    box = panel.bounding_box()
    assert box['y'] >= 0
    assert box['y'] + box['height'] <= summary.bounding_box()['y']
    assert box['x'] >= 0 and box['x'] + box['width'] <= width
    assert panel.evaluate('el => el.scrollHeight > el.clientHeight')
    assert bar.bounding_box()['height'] == height
    assert menu.locator('input').count() == 37
    assert menu.locator('[data-checkbox-count]').inner_text() == '2'
    menu.locator('input').first.uncheck()
    assert menu.locator('[data-checkbox-count]').inner_text() == '1'
    screenshot(page, f'list-{width}')
    page.keyboard.press('Escape')
    assert not menu.evaluate('el => el.open')
    assert summary.evaluate('el => el === document.activeElement')
    summary.click()
    # Клик снаружи закрывает меню и не отнимает фокус у выбранного поля.
    search = page.locator('[data-list-search]')
    search.click()
    assert not menu.evaluate('el => el.open')
    assert search.evaluate('el => el === document.activeElement')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')


def test_checkbox_menu_without_js(browser, live_url, render):
    page = browser.new_page(java_script_enabled=False)
    html = render("{% import 'venom_ui/macros.html' as ui %}{{ ui.checkbox_group('brands', 'Brands', [(1, 'One')], collapsible=true) }}")
    page.set_content(html)
    menu = page.locator('details.checkbox-menu')
    menu.locator('summary').click()
    assert menu.evaluate('el => el.open')
    assert menu.locator('input').first.is_visible()
    page.close()
