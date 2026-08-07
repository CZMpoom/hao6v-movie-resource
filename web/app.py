# -*- coding: utf-8 -*-
"""Flask Web 应用：资源列表/多条件查询 + 详情展示（海报/简介/演员/磁力）。"""
import json

from flask import Flask, abort, render_template, request

import config
from common.db import query, query_one
from common.logger import get_logger

logger = get_logger(__name__)


def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')

    @app.template_filter('poster')
    def poster_url(path, size='w342'):
        if not path:
            return ''
        return f'{config.TMDB_IMAGE_BASE}/{size}{path}'

    @app.template_filter('fromjson')
    def from_json(value):
        try:
            return json.loads(value or '[]')
        except (ValueError, TypeError):
            return []

    @app.template_filter('fmtdate')
    def fmt_date(value):
        return (value or '').strftime('%Y-%m-%d') if value else ''

    def sidebar_data(category_id=None, year=None):
        cats = query(
            """SELECT c.id, c.name, COUNT(rc.resource_id) AS cnt
               FROM categories c
               LEFT JOIN resource_categories rc ON rc.category_id = c.id
               GROUP BY c.id, c.name ORDER BY c.id"""
        )
        years = [r['year'] for r in query(
            'SELECT DISTINCT year FROM resources WHERE year IS NOT NULL ORDER BY year DESC'
        )]
        return cats, years

    @app.route('/')
    def index():
        q = (request.args.get('q') or '').strip()
        actor = (request.args.get('actor') or '').strip()
        category_id = request.args.get('category', type=int)
        year = request.args.get('year', type=int)
        try:
            page = max(1, int(request.args.get('page', 1)))
        except ValueError:
            page = 1
        per_page = config.WEB_PAGE_SIZE

        where, args = [], []
        if q:
            where.append('(r.title LIKE %s OR r.clean_title LIKE %s OR r.tmdb_title LIKE %s)')
            like = f'%{q}%'
            args += [like, like, like]
        if actor:
            where.append('r.cast LIKE %s')
            args.append(f'%{actor}%')
        if category_id:
            where.append('rc.category_id = %s')
            args.append(category_id)
        if year:
            where.append('r.year = %s')
            args.append(year)
        cond = ('WHERE ' + ' AND '.join(where)) if where else ''

        base_sql = (
            'FROM resources r '
            'JOIN resource_categories rc ON rc.resource_id = r.id '
            'JOIN categories c ON c.id = rc.category_id '
            f'{cond} '
        )
        total = query_one(f'SELECT COUNT(DISTINCT r.id) AS c {base_sql}', args)['c']
        pages = max(1, (total + per_page - 1) // per_page)
        page = min(page, pages)

        rows = query(
            f"""SELECT r.*, GROUP_CONCAT(c.name ORDER BY c.id SEPARATOR ' / ') AS category_names
                {base_sql}
                GROUP BY r.id
                ORDER BY COALESCE(r.year, 0) DESC, r.id DESC
                LIMIT %s OFFSET %s""",
            args + [per_page, (page - 1) * per_page],
        )
        cats, years = sidebar_data(category_id, year)
        logger.info('Web 查询: q=%r actor=%r category=%s year=%s -> %d 条', q, actor, category_id, year, total)
        return render_template(
            'index.html',
            rows=rows,
            cats=cats,
            years=years,
            q=q, actor=actor, category_id=category_id, year=year,
            page=page, pages=pages, total=total,
        )

    @app.route('/resource/<int:rid>')
    def detail(rid):
        row = query_one(
            """SELECT r.*, GROUP_CONCAT(c.name ORDER BY c.id SEPARATOR ' / ') AS category_names
               FROM resources r
               JOIN resource_categories rc ON rc.resource_id = r.id
               JOIN categories c ON c.id = rc.category_id
               WHERE r.id = %s GROUP BY r.id""",
            (rid,),
        )
        if not row:
            abort(404)
        row['magnets'] = row.get('magnets') and json.loads(row['magnets']) or []
        row['cast'] = row.get('cast') and json.loads(row['cast']) or []
        logger.info('Web 详情: id=%s %s', rid, row['title'])
        return render_template('detail.html', r=row)

    return app
