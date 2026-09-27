from datetime import date, datetime, timedelta

import pytest

from venomshadows_ui.charts import _nice_step, line_chart
from test_core_rendering import tree
from venomshadows_ui.timefmt import dt_full, rel_time


@pytest.mark.parametrize('rows', [[], [{'label': 'today', 'n': 1}]])
def test_insufficient(rows):
    assert line_chart(rows, [('n', 'Count')]) is None


@pytest.mark.parametrize('value,top', [(0, 1), (950000, 1000000)])
def test_scale(value, top):
    rows = [dict(label=date(2026, 9, i), n=value) for i in (1, 2)]
    result = line_chart(rows, [('n', 'Count')])
    assert result['y_ticks'][-1] == dict(value=top, pos=0)
    assert len(result['y_ticks']) <= 5
    assert result['series'][0]['last'] == value
    assert result['series'][0]['area'].endswith('L0.0,100 Z')
    assert result['rows'][0]['label'] == '01.09'
    assert rows[0]['label'] == date(2026, 9, 1)


def test_ticks_and_bands():
    rows = [dict(day=date(2026, 9, 1) + timedelta(days=i), n=i) for i in range(30)]
    result = line_chart(rows, [('n', 'Count')], label_key='day', summary='Daily counts')
    ticks = result['x_ticks']
    assert [t['label'] for t in ticks] == ['02.09', '09.09', '16.09', '23.09', '30.09']
    assert ticks[0]['edge'] == 'start'
    assert ticks[-1]['edge'] == 'end'
    assert [t['minor'] for t in ticks] == [False, True, False, True, False]
    assert sum(b['width'] for b in result['bands']) == pytest.approx(100, abs=.02)
    assert result['bands'][0]['x'] == 0
    assert result['summary'] == 'Daily counts'


def test_iso_day_labels(render):
    rows = [dict(day=f'2026-09-{i:02}', n=i) for i in range(1, 31)]
    result = line_chart(rows, [('n', 'Count')], label_key='day')
    assert [tick['label'] for tick in result['x_ticks']] == [
        '02.09', '09.09', '16.09', '23.09', '30.09']
    assert [band['title'] for band in result['bands']] == [
        f'{i:02}.09. Count: {i}' for i in range(1, 31)]
    assert [row['label'] for row in result['rows']] == [
        f'{i:02}.09' for i in range(1, 31)]
    html = render("""{% import 'venom_ui/dashboard.html' as d %}
        {{ d.chart(chart, 'Counts', [('label', 'Day'), ('n', 'Count')]) }}""",
        chart=result)
    assert [node.text for node in tree(html).find('th', scope='row')] == [
        f'{i:02}.09' for i in range(30, 0, -1)]
    assert rows[0]['day'] == '2026-09-01'
    assert 'label' not in rows[0]


@pytest.mark.parametrize('label', [
    'today', '2026-9-01', '2026-09-01T00:00:00', ' 2026-09-01', '2026-09-01\n',
])
def test_other_day_strings_unchanged(label):
    result = line_chart([dict(label=label, n=i) for i in (1, 2)], [('n', 'Count')])
    assert result['x_ticks'][0]['label'] == label
    assert result['bands'][0]['title'] == label + '. Count: 1'
    assert result['rows'][0]['label'] == label


def test_custom_band_title(render):
    rows = [dict(day='2026-09-01', n=None, total=None),
            dict(day='2026-09-02', n=1, total=2),
            dict(day='2026-09-03', n=3, total=4)]
    seen = []

    def title(row):
        seen.append(row)
        return f"<Count>: {row['n']} of {row['total']} ({row['n'] / row['total']:.0%})"

    result = line_chart(rows, [('n', 'Count')], label_key='day', band_title=title)
    assert seen == rows[1:]
    assert seen[0] is rows[1]
    assert [band['title'] for band in result['bands']] == [
        '<Count>: 1 of 2 (50%)', '<Count>: 3 of 4 (75%)']
    html = render("""{% import 'venom_ui/dashboard.html' as d %}
        {{ d.chart(chart, 'Counts', [('label', 'Day')]) }}""", chart=result)
    assert '<Count>' not in html
    assert '&lt;Count&gt;: 1 of 2 (50%)' in html


@pytest.mark.parametrize('value', [-1, float('nan'), float('inf'), True, False])
def test_invalid_counts(value):
    with pytest.raises(ValueError):
        line_chart([dict(label='a', n=value), dict(label='b', n=1)], [('n', 'Count')])


@pytest.mark.parametrize('value,expected', [
    ('2026-09-27T14:02:40', 'только что'),
    ('2026-09-27T13:58:00', '5 мин назад'),
    ('2026-09-26T14:03:00', 'вчера в 14:03'),
    ('2026-09-12T14:03:00', '12 сент.'),
    ('2026-09-27T14:08:00', 'через 5 мин'),
    ('2026-09-28T14:03:00', 'завтра в 14:03'),
    (None, '—'), ('bad', 'bad'),
])
def test_relative_time(value, expected):
    assert rel_time(value, now=datetime(2026, 9, 27, 14, 3)) == expected


def test_timezone_and_filters(app):
    assert dt_full('2026-09-27T11:03:00Z') == '27.09.2026 14:03'
    assert dt_full(datetime(2026, 9, 27, 14, 3)) == '27.09.2026 14:03'
    assert app.jinja_env.filters['venom_rel_time'] is rel_time
    assert app.jinja_env.filters['venom_dt_full'] is dt_full


def test_slots_and_escaping(render):
    html = render('''{% import 'venom_ui/dashboard.html' as d %}
        {% call(item) d.feed(items, 1, 'empty') %}{{ d.feed_item(item.main, 'neutral', '<label>', item.at) }}{% endcall %}
        {{ d.side_list(items, 1, 'empty', more_href='/all') }}
        {{ d.chart(none, '', []) }}''', items=[dict(main='<script>', at=None)] * 2)
    assert '<script>' not in html
    assert '&lt;script&gt;' in html
    assert 'Все (2)' in html
    assert 'Показать ещё 1' in html
    assert 'Истории пока мало' in html


def test_demo(client):
    response = client.get('/demo/dashboard')
    assert response.status_code == 200
    assert len([node for node in tree(response.text).find('a', href=True)
                if node.has_class('hstat')]) == 6


@pytest.mark.parametrize('width', [1600, 860, 360])
def test_dashboard_browser(page, live_url, screenshot, width):
    page.set_viewport_size(dict(width=width, height=1000))
    page.goto(live_url + '/demo/dashboard')
    page.evaluate('document.fonts.ready')
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    assert page.locator('a.hstat[href]').count() == 6
    assert page.locator('.hchart__svg').get_attribute('aria-label')
    assert page.locator('.hfeed__item:visible').count() == 8
    screenshot(page, f'dashboard-{width}')
    page.locator('.dash-grid__main .hmore summary').click()
    assert page.locator('.hfeed__item:visible').count() == 25
    page.locator('.hdata summary').click()
    assert page.locator('.hdata tbody tr').count() == 30
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')


@pytest.mark.parametrize('top,step', [(4, 1), (5, 2), (9, 5), (20, 5), (21, 10)])
def test_nice_step_boundaries(top, step):
    assert _nice_step(top) == step


def test_leading_unobserved_window():
    rows = [dict(label=date(2026, 9, 1) + timedelta(days=i),
                 n=None if i < 18 else i, other=None if i < 18 else 0)
            for i in range(30)]
    result = line_chart(rows, [('n', 'Count'), ('other', 'Other')])
    assert result['series'][0]['line'].startswith('M62.069,')
    assert result['series'][0]['area'].endswith('L62.069,100 Z')
    assert result['series'][1]['line'].startswith('M62.069,100.0')
    assert [t['label'] for t in result['x_ticks']] == [
        '02.09', '09.09', '16.09', '23.09', '30.09']
    assert result['x_ticks'][0]['pos'] == 3.448
    assert result['x_ticks'][-1]['pos'] == 100
    assert len(result['bands']) == len(result['rows']) == 12
    assert result['bands'][0]['x'] == pytest.approx(60.345, abs=.001)
    assert result['rows'][0]['label'] == '19.09'
    assert 'за 30 дн.' in result['summary']
    assert rows[0]['n'] is None


@pytest.mark.parametrize('values', [[None, None], [None, 0]])
def test_insufficient_observed(values):
    assert line_chart([dict(label=str(i), n=n) for i, n in enumerate(values)],
                      [('n', 'Count')]) is None


@pytest.mark.parametrize('rows,key', [
    ([dict(label='a'), dict(label='b', n=1)], 'n'),
    ([dict(n=1), dict(label='b', n=1)], 'label'),
    ([dict(label='a', n=1), dict(label='b', n=None), dict(label='c', n=2)], 'n'),
    ([dict(label='a', n=1), dict(label='b', n=None)], 'n'),
])
def test_invalid_chart_keys(rows, key):
    with pytest.raises(ValueError, match=key):
        line_chart(rows, [('n', 'Count')])


def test_partial_observation_rejects_none():
    with pytest.raises(ValueError, match='other'):
        line_chart([dict(label='a', n=1, other=None), dict(label='b', n=2, other=3)],
                   [('n', 'Count'), ('other', 'Other')])


@pytest.mark.parametrize('value,now,expected', [
    ('2026-09-27T12:03:00', datetime(2026, 9, 27, 14, 3), '2 ч назад'),
    # Меньше часа остаётся относительным временем даже через полночь, как в сервисах.
    ('2026-09-26T23:50:00', datetime(2026, 9, 27, 0, 10), '20 мин назад'),
    ('2025-12-31T12:00:00', datetime(2026, 9, 27), '31 дек. 2025'),
    ('2026-03-05T12:00:00', datetime(2026, 9, 27), '5 марта'),
    ('2026-05-05T12:00:00', datetime(2026, 9, 27), '5 мая'),
    ('2026-06-05T12:00:00', datetime(2026, 9, 27), '5 июня'),
    ('2026-07-05T12:00:00', datetime(2026, 9, 27), '5 июля'),
])
def test_relative_time_boundaries(value, now, expected):
    assert rel_time(value, now=now) == expected


def test_aware_and_naive_relative_time():
    now = datetime(2026, 9, 27, 14, 3)
    assert rel_time('2026-09-27T09:03:00Z', now=now) == rel_time(
        datetime(2026, 9, 27, 12, 3), now=now) == '2 ч назад'


@pytest.mark.parametrize('at', ['2026-09-27T11:03:00Z', datetime(2026, 9, 27, 14, 3)])
def test_dashboard_macro_contracts(render, at):
    html = render("""{% import 'venom_ui/dashboard.html' as d %}
        {% call d.stats('Metrics', id='metrics') %}
          {{ d.stat(42, 'Domains', '/domains', 'ok', 'check', 'Note') }}
        {% endcall %}
        {% call d.panel('events', 'Events', hint='Hint', count=2) %}Body{% endcall %}
        {% call d.panel('empty', 'Empty', count=0) %}Empty{% endcall %}
        {{ d.when(at) }}
        {{ d.feed([{'main': 'No badge', 'at': at}], 1, 'empty') }}
        {{ d.side_list([{'main': 'Domain', 'note': 'Source', 'at': at}], 1, 'empty') }}
        """, at=at)
    dom = tree(html)
    section = dom.find('section', **{'aria-labelledby': 'metrics-title'})[0]
    assert section.find('h2', id='metrics-title')[0].has_class('visually-hidden')
    card = section.find('a', href='/domains')[0]
    assert card.has_class('hstat--ok')
    assert all(text in card.text for text in ['42', 'Domains', 'Note'])
    panel = dom.find('section', **{'aria-labelledby': 'events-title'})[0]
    assert panel.find('h2')[0].text == 'Events'
    assert any(n.text == 'Hint' for n in panel.find('span'))
    assert [n.text for n in panel.find('span') if n.has_class('pill')] == ['2']
    empty = dom.find('section', **{'aria-labelledby': 'empty-title'})[0]
    assert not any(n.has_class('pill') for n in empty.find('span'))
    assert not any(n.has_class('pill') for n in dom.find('li')[1].find('span'))
    for time in dom.find('time'):
        assert time.attrs['datetime'] == (at if isinstance(at, str) else at.isoformat())
        assert time.attrs['title'] == '27.09.2026 14:03'
        assert time.text
    meta = next(n for n in dom.find('span') if n.has_class('hdrops__meta'))
    assert meta.find('span', **{'aria-hidden': 'true'})[0].text == '·'
    when = render("{% import 'venom_ui/dashboard.html' as d %}{{ d.when(at) }}", at=at)
    assert when == when.strip()


def test_dashboard_young_browser(page, live_url, screenshot):
    page.set_viewport_size(dict(width=1600, height=1000))
    page.goto(live_url + '/demo/dashboard?young=1')
    page.evaluate('document.fonts.ready')
    assert page.locator('.hchart__line').first.get_attribute('d').startswith('M62.069,')
    assert page.locator('.hchart__xlabel').count() == 5
    assert 'за 30 дн.' in page.locator('.hchart__svg').get_attribute('aria-label')
    assert page.locator('.hdata tbody tr').count() == 12
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
    screenshot(page, 'dashboard-young-1600')
