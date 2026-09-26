"""Контракты карточек и строк подробностей."""

import pytest

from test_list import Tags

IMPORT = '{% import "venom_ui/list.html" as list %}'


def test_detail_and_card_macros(render):
    html = render(IMPORT + '''
      {% call list.detail_row(3, id=identifier, hidden=false) %}Body{% endcall %}
      {{ list.sort_control([{'key': 'title', 'label': 'Title'}], 'title', 'desc', target='cards', selectable=true) }}
      {% call list.card_list('cards', label='Cards') %}
        <li {{ list.row_attrs('Title', id=7) }}>{{ list.select_box(7, 'Title', name='ids') }}</li>
      {% endcall %}''', identifier='detail"<&')
    tags = Tags(html)
    detail = next(row for row in tags.find('tr') if 'data-row-detail' in row)
    assert detail['id'] == 'detail"<&'
    assert 'hidden' not in detail and 'data-row' not in detail
    assert tags.find('td')[0]['colspan'] == '3'
    assert tags.find('ul')[0]['data-list-body'] is None
    box = next(box for box in tags.find('input') if 'data-row-select' in box)
    assert box['name'] == 'ids' and box['value'] == '7'
    assert not tags.find('th') and not tags.find('table')
    assert tags.find('button')[0]['aria-pressed'] == 'true'
    assert any(group.get('role') == 'group' and group.get('aria-label') == 'Сортировка' for group in tags.find('div'))
    assert ', по убыванию' in html and 'aria-sort' not in html
    assert 'hidden' in Tags(render(IMPORT + '{% call list.detail_row(1) %}x{% endcall %}')).find('tr')[0]
    assert 'name' not in Tags(render(IMPORT + '{{ list.select_box(1, "Title") }}')).find('input')[0]


def test_cards_demo(client):
    response = client.get('/demo/cards')
    assert response.status_code == 200
    tags = Tags(response.text)
    assert len([li for li in tags.find('li') if 'data-row' in li]) == 40
    assert len([box for box in tags.find('input') if 'data-row-select' in box]) == 40


def test_detail_pairs_filter_sort_lazy(page, live_url):
    page.goto(live_url + '/demo/list')
    page.locator('[data-id="3"] [data-detail-toggle]').click()
    assert page.locator('#detail-3').is_visible()
    page.evaluate('''() => {
      const extra = document.querySelector('#detail-3').cloneNode(true);
      extra.id = 'detail-3-extra';
      document.querySelector('#detail-3').after(extra);
      document.querySelector('[data-id="3"] [data-detail-toggle]').setAttribute('aria-controls', 'detail-3 detail-3-extra');
      document.querySelector('#domains').dispatchEvent(new Event('venomlist:refresh'));
    }''')
    for key in ['number', 'date', 'domain']:
        page.locator(f'[data-sort-key="{key}"]').click()
        assert page.locator('[data-row-detail]').evaluate_all('''details => details.every(detail => {
          let owner = detail.previousElementSibling;
          while (owner?.matches('[data-row-detail]')) owner = owner.previousElementSibling;
          return owner?.matches('[data-row]') && detail.id.startsWith('detail-' + owner.dataset.id)
            && (!owner.hidden || detail.hidden);
        })''')
    assert page.locator('[data-row]:visible').count() == 50
    assert page.locator('[data-list-count]').inner_text() == '180 из 180'
    page.locator('[data-list-search]').fill('domain-3.example')
    assert page.locator('[data-row]:visible').count() == 1
    assert page.locator('#detail-3-extra').is_visible()
    page.locator('[data-select-all]').check()
    assert page.locator('[data-selection-count]').inner_text() == '1'
    page.locator('[data-list-search]').fill('missing')
    assert page.locator('#detail-3').is_hidden()
    page.locator('[data-list-search]').fill('domain-3.example')
    assert page.locator('#detail-3').is_visible()
    page.locator('[data-id="3"] [data-detail-toggle]').click()
    assert page.locator('#detail-3').is_hidden()
    assert page.locator('#detail-3-extra').is_hidden()
    page.locator('[data-list-reset]').click()
    page.locator('[data-reveal-more]').evaluate('el => el.click()')
    assert page.locator('[data-row]:visible').count() >= 100
    assert page.locator('#detail-3').is_hidden()


def test_cards_filters_sort_selection_state(page, live_url):
    page.goto(live_url + '/demo/cards')
    visible = page.locator('#versions > [data-row]:visible')
    assert visible.count() == 40
    assert page.locator('[data-list-count]').inner_text() == '40 из 40'
    assert page.locator('[data-lazy-sentinel]').is_hidden()
    page.locator('#versions').evaluate("el => el.addEventListener('venomlist:selection', event => window.ids = event.detail.ids)")
    page.locator('[data-select-all]').check()
    assert len(page.evaluate('window.ids')) == 40
    page.locator('[data-chip="new"]').click()
    assert visible.count() == 20
    assert page.locator('[data-selection-count]').inner_text() == '20'
    page.locator('[data-row]:visible [data-row-select]').first.uncheck()
    assert page.locator('[data-select-all]').evaluate('el => el.indeterminate')
    page.locator('[data-clear-selection]').click()
    assert page.locator('[data-bulk-bar]').is_hidden()
    assert page.locator('[data-select-all]').evaluate('el => el === document.activeElement')
    page.locator('[data-sort-key="title"]').click()
    ids = visible.evaluate_all('rows => rows.map(row => Number(row.dataset.id))')
    assert ids == sorted(ids)
    page.locator('[data-sort-key="title"]').click()
    assert visible.evaluate_all('rows => rows.map(row => Number(row.dataset.id))') == sorted(ids, reverse=True)
    page.reload()
    assert visible.count() == 20
    assert page.locator('[data-sort-key="title"][aria-pressed="true"]').count() == 1
    assert page.locator('[data-sort-key="title"] [data-sort-direction]').text_content() == ', по убыванию'
    assert page.locator('[data-sort-key="date"] [data-sort-direction]').text_content() == ''
    assert page.locator('[data-sort-control] [aria-sort], [data-sort-control] table').count() == 0
    page.locator('[data-list-search]').fill('Шаблон 2')
    assert visible.count() == 8
    page.locator('[data-list-search]').fill('missing')
    assert page.locator('[data-empty-row]').is_visible()
    assert page.locator('[data-select-all]').is_disabled()
    page.locator('[data-list-reset]').click()
    assert visible.count() == 40


def test_arbitrary_body_lazy_refresh(page, live_url):
    page.goto(live_url + '/demo/cards')
    page.evaluate('''() => {
      const target = document.querySelector('#versions');
      const wrapper = document.createElement('section');
      wrapper.id = 'custom';
      wrapper.dataset.list = '';
      const body = document.createElement('div');
      body.dataset.listBody = '';
      for (let i = 0; i < 120; i++) {
        const row = target.querySelector('[data-row]').cloneNode(true);
        row.dataset.id = String(i);
        body.append(row);
      }
      wrapper.append(body);
      target.after(wrapper);
      const sentinel = document.querySelector('[data-lazy-sentinel]').cloneNode(true);
      sentinel.dataset.target = 'custom';
      wrapper.after(sentinel);
      VenomList.init(wrapper);
    }''')
    assert page.locator('#custom [data-row]:visible').count() == 50
    # Прокрутка к кнопке сама запускает observer; здесь проверяем ручной показ.
    page.locator('[data-lazy-sentinel][data-target="custom"] [data-reveal-more]').evaluate('el => el.click()')
    assert page.locator('#custom [data-row]:visible').count() >= 100
    page.locator('#custom').evaluate('''el => {
      const row = el.querySelector('[data-row]').cloneNode(true);
      row.dataset.id = 'added';
      el.querySelector('[data-list-body]').append(row);
      el.dispatchEvent(new Event('venomlist:refresh'));
    }''')
    assert page.locator('#custom [data-row]').count() == 121


@pytest.mark.parametrize('width', [1600, 360])
@pytest.mark.parametrize('demo', ['list', 'cards'])
def test_new_list_screenshots(page, live_url, screenshot, width, demo):
    page.set_viewport_size({'width': width, 'height': 1000})
    page.goto(f'{live_url}/demo/{demo}')
    if demo == 'list':
        if width == 360:
            page.locator('[data-sort-key="number"]').click()
        page.locator('[data-id="3"] [data-detail-toggle]').click()
        detail = page.locator('#detail-3')
        assert detail.is_visible()
        if width == 360:
            assert detail.locator('td').evaluate('el => getComputedStyle(el).display') == 'block'
            assert detail.bounding_box()['width'] == pytest.approx(page.locator('[data-id="3"]').bounding_box()['width'], abs=2)
        if width == 360:
            page.locator('[data-id="3"]').evaluate("el => el.closest('.table-scroll').scrollTop += el.getBoundingClientRect().top - el.closest('.table-scroll').getBoundingClientRect().top - 44")
        else:
            page.locator('.table-scroll').evaluate('el => el.scrollTop = 0')
    else:
        card = page.locator('#versions > [data-row]').first
        card.locator('[data-row-select]').check()
        card.hover()
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    screenshot(page, f'{demo}-details-{width}' if demo == 'list' else f'cards-{width}')


@pytest.mark.parametrize('demo', ['list', 'list-server'])
def test_detail_toggle_modes_and_edge_cases(page, live_url, demo):
    page.goto(f'{live_url}/demo/{demo}')
    button = page.locator('[data-detail-toggle]').first
    owner = button.locator('xpath=ancestor::tr')
    detail_id = button.get_attribute('aria-controls')
    detail = page.locator(f'#{detail_id}')
    button.click()
    assert detail.is_visible() and button.get_attribute('aria-expanded') == 'true'
    button.press('Enter')
    assert detail.is_hidden() and button.get_attribute('aria-expanded') == 'false'
    owner.evaluate('''row => {
      const detail = row.nextElementSibling;
      detail.removeAttribute('id');
      const extra = detail.cloneNode(true);
      detail.after(extra);
      row.querySelector('[data-detail-toggle]').removeAttribute('aria-controls');
      row.closest('[data-list]').dispatchEvent(new Event('venomlist:refresh'));
    }''')
    button.press('Space')
    assert owner.evaluate('row => !row.nextElementSibling.hidden && !row.nextElementSibling.nextElementSibling.hidden')
    for controls in ['missing', '   ']:
        button.evaluate('(el, value) => el.setAttribute("aria-controls", value)', controls)
        button.click()
        assert button.get_attribute('aria-expanded') == 'true'
        assert owner.evaluate('row => !row.nextElementSibling.hidden && !row.nextElementSibling.nextElementSibling.hidden')


@pytest.mark.parametrize('demo', ['list', 'list-server'])
def test_remove_rows_never_orphans_details(page, live_url, demo):
    page.goto(f'{live_url}/demo/{demo}')
    page.evaluate('''() => {
      const owner = document.querySelector('[data-id="12"]');
      const detail = owner.nextElementSibling;
      const extra = detail.cloneNode(true);
      extra.id = 'detail-12-extra';
      detail.after(extra);
      window.refreshes = 0;
      document.querySelector('#domains').addEventListener('venomlist:refresh', () => window.refreshes++);
      VenomList.removeRows([owner, document.querySelector('[data-id="9"]')]);
    }''')
    assert page.evaluate('window.refreshes') == 1
    assert page.locator('#detail-12, #detail-12-extra, #detail-9, [data-id="12"], [data-id="9"]').count() == 0
    if demo == 'list':
        assert page.locator('[data-list-count]').inner_text() == '178 из 178'
        page.locator('[data-sort-key="number"]').click()
        assert page.locator('[data-row-detail]').evaluate_all('''details => details.every(detail =>
          detail.previousElementSibling.dataset.id === detail.id.replace('detail-', ''))''')
    page.locator('[data-id="3"] [data-row-select]').check()
    page.locator('[data-demo-delete]').click()
    assert page.locator('[data-id="3"], #detail-3').count() == 0


def test_compact_detail_toggle_and_shared_checkboxes(page, live_url):
    page.set_viewport_size({'width': 1600, 'height': 1000})
    page.goto(live_url + '/demo/list')
    heights = page.locator('[data-row]').evaluate_all('rows => rows.slice(0, 6).map(row => row.getBoundingClientRect().height)')
    assert max(heights) - min(heights) <= 1
    button = page.locator('[data-id="3"] [data-detail-toggle]')
    hit = button.evaluate('''el => {
      const style = getComputedStyle(el, '::before');
      return {height: parseFloat(style.height), top: parseFloat(style.top)};
    }''')
    assert hit['height'] >= 44 and hit['top'] < 0
    bounds = button.bounding_box()
    page.mouse.click(bounds['x'] + bounds['width'] / 2, bounds['y'] - 2)
    assert page.locator('#detail-3').is_visible()
    checkbox_style = '''el => {
      const style = getComputedStyle(el);
      const label = el.closest('label').getBoundingClientRect();
      return {width: style.width, height: style.height, accent: style.accentColor,
        hitWidth: label.width, hitHeight: label.height};
    }'''
    table_style = page.locator('[data-row-select]').first.evaluate(checkbox_style)
    page.goto(live_url + '/demo/cards')
    card = page.locator('#versions > [data-row]').first
    card_style = card.locator('[data-row-select]').evaluate(checkbox_style)
    assert card_style == table_style
    assert card_style['hitWidth'] >= 44 and card_style['hitHeight'] >= 44
    card.locator('[data-row-select]').check()
    page.mouse.move(0, 0)
    selected_color = card.evaluate('el => getComputedStyle(el).backgroundColor')
    card.hover()
    assert card.evaluate('el => getComputedStyle(el).backgroundColor') == selected_color
    page.locator('[data-list-search]').fill('missing')
    assert page.locator('[data-empty-row]').evaluate('el => getComputedStyle(el).textAlign') == 'center'


def test_stacked_header_visible_regions_do_not_overlap(page, live_url):
    page.set_viewport_size({'width': 360, 'height': 1000})
    page.goto(live_url + '/demo/list')
    for key in ['number', 'domain', 'status', 'date', 'number']:
        page.locator(f'[data-sort-key="{key}"]').click()
        assert page.locator(f'[data-sort-key="{key}"]').evaluate('''active => {
          const th = active.closest('th');
          const header = th.closest('tr');
          const select = header.querySelector('.data-table__select');
          const activeBox = active.getBoundingClientRect();
          const clip = header.getBoundingClientRect();
          const selectBox = select.getBoundingClientRect();
          if (Number(getComputedStyle(select).zIndex) <= Number(getComputedStyle(th).zIndex)) return false;
          // Сравниваем видимые области: статические flex-ячейки прокручиваются под липкой.
          for (const sibling of header.querySelectorAll('th[aria-sort]')) {
            if (sibling === th) continue;
            if (Number(getComputedStyle(sibling).zIndex) >= Number(getComputedStyle(th).zIndex)) return false;
            const box = sibling.querySelector('.th-sort').getBoundingClientRect();
            const left = Math.max(box.left, activeBox.left, clip.left, selectBox.right);
            const right = Math.min(box.right, activeBox.right, clip.right);
            for (let x = left + 1; x < right; x += 2) {
              const top = document.elementFromPoint(x, activeBox.top + activeBox.height / 2);
              if (!th.contains(top)) return false;
            }
          }
          return true;
        }''')
    page.locator('[data-id="3"] [data-detail-toggle]').click()
    assert page.locator('#detail-3').evaluate('el => getComputedStyle(el).borderTopWidth') == '0px'
    assert page.locator('[data-id="3"]').evaluate('el => getComputedStyle(el).borderBottomLeftRadius') == '0px'
