"""Детерминированные значения графика и реалистичные события витрины."""
from datetime import datetime, timedelta, timezone

from flask import render_template, request
from venomshadows_ui.charts import line_chart


def register_dashboard(app):
    @app.get('/demo/dashboard')
    def dashboard():
        now = datetime.now(timezone.utc)
        rows = [dict(day=(now - timedelta(days=29-i)).date(),
                     yandex=180 + i * 3 + i % 4 * 2,
                     google=150 + i * 4 - i % 5 * 3,
                     clean=110 + i * 2 + i % 3 * 4) for i in range(30)]
        if request.args.get('young') == '1':
            for row in rows[:18]:
                row.update(yandex=None, google=None, clean=None)
        events = [dict(main=f'project-{i + 1}.example', pill_tone='success' if i % 3 else 'danger',
                       pill_label='В индексе' if i % 3 else 'Не в индексе',
                       at=now - timedelta(minutes=5 + i * 97)) for i in range(25)]
        blocks = [dict(main=f'archive-{i + 1}.example', href='/demo/list', note='ЕАИС',
                       at=now - timedelta(hours=i + 1)) for i in range(7)]
        return render_template('demo/dashboard.html',
                               chart=line_chart(rows, [('yandex', 'Яндекс'), ('google', 'Google'),
                                                       ('clean', 'Без блокировок')], label_key='day'),
                               events=events, blocks=blocks)
