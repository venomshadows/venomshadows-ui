"""Чистая геометрия дневного графика; выбор дней остаётся у сервиса."""

from datetime import date, datetime
from math import ceil, isfinite
from re import fullmatch


def _day_label(value):
    if isinstance(value, str) and fullmatch(r'\d{4}-\d{2}-\d{2}', value):
        return value[8:10] + '.' + value[5:7]
    return value.strftime("%d.%m") if isinstance(value, (date, datetime)) else str(value)


def _nice_step(top: int, intervals: int = 4) -> int:
    magnitude = 1
    while True:
        for base in (1, 2, 5):
            if top <= base * magnitude * intervals:
                return base * magnitude
        magnitude *= 10


def line_chart(rows, series, *, label_key='label', summary=None, band_title=None) -> dict | None:
    """Ряды идут по времени; значения — конечные неотрицательные числа.

    Даты date/datetime и строки ровно YYYY-MM-DD форматируются как ДД.ММ.
    Остальные строки сохраняются; band_title(row) заменяет подсказку дня.
    Начальные строки со всеми None не наблюдались, но сохраняют ось окна.
    Ноль — наблюдение; None после первого наблюдения недопустим.
    rows в результате — поверхностные копии; label зарезервирован под подпись.
    """
    if not series:
        return None
    for row in rows:
        for key in [label_key, *(key for key, _ in series)]:
            if key not in row:
                raise ValueError(f'Missing chart key: {key}')
    observed = [i for i, row in enumerate(rows)
                if any(row[key] is not None for key, _ in series)]
    first = observed[0] if observed else len(rows)
    for row in rows[first:]:
        for key, _ in series:
            value = row[key]
            if (isinstance(value, bool) or not isinstance(value, (int, float))
                    or not isfinite(value) or value < 0):
                raise ValueError(f'Chart key {key}: expected a finite non-negative number')
    if len(observed) < 2:
        return None
    total = len(rows)
    step_x = 100 / (total - 1)
    top = max(1, max(row[key] for row in rows[first:] for key, _ in series))
    step = _nice_step(top)
    y_top = step * ceil(top / step)

    def x(i):
        return round(i * step_x, 3)

    def y(value):
        return round(100 - value * 100 / y_top, 3)

    plotted, descriptions = [], []
    for index, (key, label) in enumerate(series):
        values = [row[key] for row in rows[first:]]
        line = 'M' + ' L'.join(f'{x(first + i)},{y(v)}' for i, v in enumerate(values))
        plotted.append(dict(key=key, label=label, line=line,
                            area=f'{line} L{x(total - 1)},100 L{x(first)},100 Z',
                            last=values[-1], color=index % 4 + 1))
        descriptions.append(f'{label} — от {min(values)} до {max(values)}, сейчас {values[-1]}')
    bands = []
    for i, row in enumerate(rows[first:], start=first):
        left, right = max(x(i) - step_x / 2, 0), min(x(i) + step_x / 2, 100)
        bands.append(dict(x=round(left, 3), width=round(right - left, 3),
                          title=band_title(row) if band_title is not None else
                          _day_label(row[label_key]) + '. ' + ', '.join(
                              f'{label}: {row[key]}' for key, label in series)))
    # Подпись у самого края прижата к нему, чтобы не выйти за область графика.
    ticks = [dict(label=_day_label(rows[i][label_key]), pos=x(i),
                  edge='start' if x(i) < 8 else ('end' if x(i) > 92 else ''),
                  minor=bool(n % 2))
             for n, i in enumerate(range(total - 1, -1, -7))][::-1]
    return dict(series=plotted, bands=bands, x_ticks=ticks,
                y_ticks=[dict(value=v, pos=y(v)) for v in range(0, y_top + 1, step)],
                rows=[dict(row, label=_day_label(row[label_key])) for row in rows[first:]],
                summary=summary if summary is not None else
                f'По дням за {total} дн.: ' + '; '.join(descriptions) + '.')
