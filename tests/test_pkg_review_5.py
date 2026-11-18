"""Offline regressions for package review 5."""

from pathlib import Path

import pytest
from markupsafe import Markup

from test_core_rendering import tree


IMPORT = "{% import 'venom_ui/list.html' as list %}"


@pytest.mark.parametrize('label', ['Действия', 'Действия "ещё" & другое'])
def test_markup_header_label(render, label):
    column = dict(key='actions', label=Markup('<span class="visually-hidden">{}</span>').format(label),
                  width=120, sortable=True)
    html = render(IMPORT + '{{ list.sort_th(column, "actions", "asc", "client") }}', column=column)
    header = tree(html).find('th')[0]
    assert header.attrs == {'scope': 'col', 'aria-label': label,
                            'class': 'data-table__start', 'width': '120',
                            'aria-sort': 'ascending'}
    assert header.find('span', **{'class': 'visually-hidden'})[0].text == label


@pytest.mark.parametrize('count_format', [None, 'shown'])
def test_lazy_card_count_above_limit(page, render, count_format):
    html = render(IMPORT + '''
      {% call list.filter_bar('cards', count_format=count_format, persist='none') %}
        {{ list.search() }}
      {% endcall %}
      {% call list.card_list('cards') %}
        {% for i in range(180) %}
        <li {{ list.row_attrs('match' if i < 120 else 'other') }} style="height:100px">{{ i }}</li>
        {% endfor %}
      {% endcall %}
      {{ list.lazy_sentinel('cards') }}''', count_format=count_format)
    page.set_content(html)
    page.add_script_tag(path=str(Path('src/venomshadows_ui/static/list.js')))
    count = page.locator('[data-list-count]')
    assert page.locator('[data-row]:visible').count() == 50
    assert count.inner_text() == ('показано 50 из 180' if count_format else '180 из 180')
    assert count.get_attribute('data-count-format') == count_format
    page.locator('[data-list-search]').fill('other')
    page.wait_for_function("document.querySelector('[data-row]').hidden")
    assert page.locator('[data-row]:visible').count() == 50
    assert count.inner_text() == ('показано 50 из 180' if count_format else '60 из 180')
