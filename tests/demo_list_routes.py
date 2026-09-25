"""Демо списков: запуск `.venv/Scripts/python tests/demo_list_routes.py`."""

from datetime import date, timedelta

from flask import Blueprint, render_template, request

from demo_app import create_app as create_base_app

bp = Blueprint("demo_lists", __name__)
STATUSES = [("", "Все"), ("new", "Новый", "accent"), ("in_use", "В работе", "success"),
            ("used", "Использован", "danger"), ("glued", "Склеен", "warning")]
COLUMNS = [dict(key="domain", label="Домен"), dict(key="status", label="Статус"),
           dict(key="date", label="Дата", type="date"), dict(key="number", label="Число", type="number", align="end")]


def demo_rows():
    return [dict(id=i, domain=f"domain-{i}.example", status=STATUSES[1 + (i % 4)][0],
                 brand=("alpha", "beta", "gamma")[i % 3],
                 date=(date(2026, 1, 1) + timedelta(days=i)).isoformat(), number=i * 7 % 101)
            for i in range(1, 181)]


@bp.get("/demo/list-server")
def server_list():
    rows = demo_rows()
    q = request.args.get("q", "")
    status = request.args.get("status", "")
    if status not in {option[0] for option in STATUSES}:
        status = ""
    brand = request.args.get("brand", "")
    if brand not in ("alpha", "beta", "gamma"):
        brand = ""
    words = q.lower().replace("ё", "е").split()
    scope = [row for row in rows if (not brand or row["brand"] == brand)
             and all(word in f'{row["domain"]} {row["brand"]}'.lower().replace("ё", "е") for word in words)]
    counts = {option[0]: sum(not option[0] or row["status"] == option[0] for row in scope) for option in STATUSES}
    shown = [row for row in scope if not status or row["status"] == status]
    sort = request.args.get("sort", "domain")
    if sort not in {column["key"] for column in COLUMNS}:
        sort = "domain"
    direction = "desc" if request.args.get("dir") == "desc" else "asc"
    shown.sort(key=lambda row: row["id"] if sort == "domain" else row[sort], reverse=direction == "desc")
    return render_template("demo/list-server.html", rows=shown, total=len(rows), q=q, status=status,
                           brand=brand, sort=sort, direction=direction, counts=counts)


@bp.post("/demo/list-selection")
def list_selection():
    return {"ids": request.form.getlist("ids"), "fields": sorted(request.form.keys())}


def create_app():
    app = create_base_app()
    app.register_blueprint(bp)
    return app


if __name__ == "__main__":
    create_app().run(port=5077, debug=True)
