"""Offline browser regressions for package review 4."""

from pathlib import Path

import pytest


STATIC = Path('src/venomshadows_ui/static')


def content(markup):
    css = '\n'.join((STATIC / name).read_text(encoding='utf-8')
                    for name in ('tokens.css', 'list.css'))
    return f'<style>{css}</style>{markup}'


@pytest.mark.parametrize('javascript_enabled', [False, True])
def test_server_scroll_before_list_js(browser, render, javascript_enabled):
    html = render('''{% import 'venom_ui/list.html' as list %}
      {% call list.data_table('server', columns, mode='server', fixed=false) %}
      <tbody><tr><td>Wide server table</td></tr></tbody>{% endcall %}''',
                  columns=[dict(key='name', label='Name')])
    with browser.new_context(java_script_enabled=javascript_enabled,
                             viewport={'width': 400, 'height': 900}) as context:
        page = context.new_page()
        page.set_content(content('<style>table {min-width:2400px}</style>' + html))
        wrap = page.locator('.table-scroll')
        assert wrap.evaluate('el => getComputedStyle(el).overflowX') == 'auto'
        assert wrap.evaluate('el => { el.scrollLeft = 500; return el.scrollLeft; }') == 500
        assert 'is-scroll-ready' not in wrap.get_attribute('class')


@pytest.mark.parametrize('replacement', ['table', 'bar'])
def test_scroll_rebind_and_remeasure(page, replacement):
    page.set_content(content('''<div class="table-scroll" style="width:350px">
      <table style="width:200px"><tbody><tr><td>X</td></tr></tbody></table></div>'''))
    page.evaluate('''() => {
      window.observed = [];
      const Native = ResizeObserver;
      window.ResizeObserver = class extends Native {
        constructor(cb) { super(cb); this.nodes = new Set(); observed.push(this); }
        observe(node) { this.nodes.add(node); super.observe(node); }
        disconnect() { this.nodes.clear(); super.disconnect(); }
      };
    }''')
    page.add_script_tag(path=str(STATIC / 'list.js'))
    wrap = page.locator('.table-scroll')
    assert wrap.evaluate('el => getComputedStyle(el).overflowX') == 'clip'
    assert wrap.evaluate('''(wrap, replacement) => {
      window.oldBar = wrap.querySelector('.table-scroll__hbar');
      window.oldObserver = observed[0];
      const old = replacement === 'table' ? wrap.querySelector('table') : oldBar;
      const fresh = old.cloneNode(true);
      old.replaceWith(fresh);
      wrap.querySelector('table').style.width = '2400px';
      VenomList.init(wrap);
      return oldObserver.nodes.size === 0 && observed.length === 2
        && observed[1].nodes.has(wrap.querySelector('table'))
        && wrap.classList.contains('is-overflow')
        && wrap.querySelector('.table-scroll__hbar > div').style.width === '2400px';
    }''', replacement)
    bar = wrap.locator('.table-scroll__hbar')
    bar.evaluate('el => el.scrollLeft = 180')
    page.wait_for_function("document.querySelector('.table-scroll').scrollLeft === 180")
    wrap.evaluate('el => el.scrollLeft = 300')
    page.wait_for_function("document.querySelector('.table-scroll__hbar').scrollLeft === 300")
    if replacement == 'bar':
        page.evaluate("oldBar.dispatchEvent(new Event('scroll'))")
        assert wrap.evaluate('el => el.scrollLeft') == 300
    assert wrap.evaluate('''wrap => {
      wrap.querySelector('table').style.width = '200px';
      VenomList.init(wrap);
      return observed.length === 2 && getComputedStyle(wrap).overflowX === 'clip';
    }''')
    wrap.evaluate('el => el.remove()')
    page.wait_for_function('observed.every(o => o.nodes.size === 0)')


def test_single_stacked_thead_keeps_controls(page, render):
    html = render('''{% import 'venom_ui/list.html' as list %}
      <table id="legacy" data-list class="data-table data-table--stacked">
      <thead><tr><th class="data-table__select"><input type="checkbox" data-select-all></th>
      {{ list.sort_th({'key': 'name', 'label': 'Name', 'sortable': true}, none, 'asc', 'client') }}</tr></thead>
      <tbody><tr data-row><td><input type="checkbox" data-row-select></td>
      <td data-key="name">B</td></tr><tr data-row>
      <td><input type="checkbox" data-row-select></td><td data-key="name">A</td></tr></tbody></table>''')
    page.set_viewport_size({'width': 400, 'height': 900})
    page.set_content(content(html))
    assert page.locator('[data-sort-key]').is_visible()
    assert page.locator('[data-select-all]').is_visible()
    assert page.locator('thead tr').evaluate('el => getComputedStyle(el).flexWrap') == 'wrap'
    page.add_script_tag(path=str(STATIC / 'list.js'))
    page.locator('[data-sort-key]').click()
    assert page.locator('th[aria-sort]').get_attribute('aria-sort') == 'ascending'
    page.locator('[data-select-all]').check()
    assert page.locator('[data-row-select]:checked').count() == 2
