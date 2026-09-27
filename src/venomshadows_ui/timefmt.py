"""Общее русское время; наивные даты сервисов считаются московскими."""

from datetime import datetime, timedelta, timezone
from math import ceil

# В Москве нет сезонного перевода с 2014 года; UTC+3 не требует tzdata на Windows.
DISPLAY_TZ = timezone(timedelta(hours=3))
MONTHS = ('янв.', 'февр.', 'марта', 'апр.', 'мая', 'июня',
          'июля', 'авг.', 'сент.', 'окт.', 'нояб.', 'дек.')


def _moment(value):
    moment = datetime.fromisoformat(value) if isinstance(value, str) else value
    if not isinstance(moment, datetime):
        raise ValueError('Expected ISO datetime or datetime')
    return (moment.replace(tzinfo=DISPLAY_TZ) if moment.tzinfo is None
            else moment.astimezone(DISPLAY_TZ))


def dt_full(value):
    if not value:
        return '—'
    try:
        return _moment(value).strftime('%d.%m.%Y %H:%M')
    except ValueError:
        return str(value)


def rel_time(value, now=None):
    if not value:
        return '—'
    try:
        moment = _moment(value)
    except ValueError:
        return str(value)
    now = _moment(now) if now is not None else datetime.now(DISPLAY_TZ)
    seconds = (moment - now).total_seconds()
    days = (moment.date() - now.date()).days
    clock = moment.strftime('%H:%M')
    if seconds <= 0:
        ago = -seconds
        if ago < 60:
            return 'только что'
        if ago < 3600:
            return f'{int(ago // 60)} мин назад'
        if days == 0:
            return f'{int(ago // 3600)} ч назад'
        if days == -1:
            return f'вчера в {clock}'
    else:
        if seconds < 3600:
            return f'через {max(1, ceil(seconds / 60))} мин'
        if days == 0:
            return f'в {clock}'
        if days == 1:
            return f'завтра в {clock}'
    year = f' {moment.year}' if moment.year != now.year else ''
    return f'{moment.day} {MONTHS[moment.month - 1]}{year}'
