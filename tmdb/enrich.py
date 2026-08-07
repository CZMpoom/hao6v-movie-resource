# -*- coding: utf-8 -*-
"""使用 TMDB 补全资源信息：简介、海报、年份、演员、总集数、导演、类型等。

按约定，资源的详细信息只从 TMDB 获取；hao6v.cc 只提供名称、磁力链接与详情页链接。
"""
import json
import re
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

import config
from common.db import execute, query
from common.logger import get_logger
from tmdb import client

logger = get_logger(__name__)

_YEAR_HINT_RE = re.compile(r'^(19|20)\d{2}')


def _year_hint(row):
    """从列表页标题开头的年份提取匹配提示（如“2026动作《...》”）。"""
    m = _YEAR_HINT_RE.search((row.get('title') or '').strip())
    return int(m.group()) if m else None


def _candidates(row):
    """构造检索候选标题（清洗片名优先，原始标题兜底），去重。"""
    out, seen = [], set()
    for c in (row.get('clean_title'), row.get('title')):
        c = (c or '').strip()
        if not c or c in seen:
            continue
        seen.add(c)
        out.append(c)
    return out


def _enrich_one(row):
    """对单条资源执行 TMDB 检索并写回数据库。"""
    year = _year_hint(row)
    found = None
    used_title = None
    for title in _candidates(row):
        results = client.search_multi(title, year)
        if results:
            found = results[0]
            used_title = title
            break

    if not found:
        logger.info('TMDB 未匹配: %s（%s）', row['title'], row['detail_url'])
        execute('UPDATE resources SET tmdb_searched = 1 WHERE id = %s', (row['id'],))
        return False

    media_type = found.get('media_type') or 'movie'
    details = client.get_details(media_type, found['id'])
    if not details:
        logger.warning('TMDB 详情获取失败: %s -> id=%s', row['title'], found['id'])
        execute('UPDATE resources SET tmdb_searched = 1 WHERE id = %s', (row['id'],))
        return False

    cast = json.dumps(details['cast'], ensure_ascii=False)
    execute(
        """UPDATE resources SET
             tmdb_id = %s, tmdb_title = %s, overview = %s, poster_path = %s,
             release_date = %s, year = %s, rating = %s, episode_count = %s,
             director = %s, genre = %s, language = %s, country = %s, cast = %s,
             media_type = %s, tmdb_searched = 1
           WHERE id = %s""",
        (
            details['tmdb_id'], details['title'], details['overview'],
            details['poster_path'], details['release_date'],
            int(details['year']) if details['year'] else None,
            round(details['rating'], 1) if details['rating'] is not None else None,
            details['episode_count'], details['director'],
            details['genre'] or None, details['language'] or None,
            details['country'] or None, cast, media_type, row['id'],
        ),
    )
    logger.info(
        'TMDB 匹配成功: %s -> [%s] %s (id=%s, 年份=%s, 集数=%s, 演员=%d, 命中标题="%s")',
        row['title'], media_type, details['title'], details['tmdb_id'],
        details['year'], details['episode_count'], len(details['cast']), used_title,
    )
    return True


def backfill_ratings(workers=None, limit=None):
    """为已有 tmdb_id 但缺评分的资源补拉 TMDB 详情（不重新搜索，按 id 精确获取）。"""
    workers = workers or config.TMDB_WORKERS
    sql = (
        'SELECT id, title, media_type, tmdb_id, detail_url FROM resources '
        'WHERE tmdb_id IS NOT NULL AND rating IS NULL ORDER BY id'
    )
    if limit:
        sql += f' LIMIT {int(limit)}'
    rows = query(sql)
    total = len(rows)
    logger.info('待回填评分 %d 条，并发 %d', total, workers)
    if not total:
        return

    done, ok, fail = 0, 0, 0
    lock = threading.Lock()

    def work(row):
        nonlocal done, ok, fail
        try:
            details = client.get_details(row['media_type'] or 'movie', row['tmdb_id'])
            success = False
            if details:
                rating = round(details['rating'], 1) if details['rating'] is not None else None
                execute('UPDATE resources SET rating = %s WHERE id = %s',
                        (rating, row['id']))
                success = True
            if not success:
                logger.warning('评分回填失败: %s -> id=%s', row['title'], row['tmdb_id'])
        except Exception:
            logger.exception('评分回填异常: %s', row['detail_url'])
            success = False
        with lock:
            done += 1
            if success:
                ok += 1
            else:
                fail += 1
            if done % 50 == 0 or done == total:
                logger.info('评分回填进度 %d/%d（成功 %d / 失败 %d）', done, total, ok, fail)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, r) for r in rows]
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception:
                logger.exception('评分回填任务异常')

    logger.info('评分回填完成：成功 %d / 失败 %d / 共 %d', ok, fail, total)


def enrich_resources(workers=None, limit=None):
    """批量补全：对 tmdb_id 为空且未检索过的资源执行 TMDB 匹配。"""
    workers = workers or config.TMDB_WORKERS
    sql = (
        'SELECT id, title, clean_title, detail_url '
        'FROM resources WHERE tmdb_id IS NULL AND tmdb_searched = 0 ORDER BY id'
    )
    if limit:
        sql += f' LIMIT {int(limit)}'
    rows = query(sql)
    total = len(rows)
    logger.info('待 TMDB 补全 %d 条，并发 %d', total, workers)
    if not total:
        return

    done, ok, fail = 0, 0, 0
    lock = threading.Lock()

    def work(row):
        nonlocal done, ok, fail
        try:
            success = _enrich_one(row)
        except Exception:
            logger.exception('TMDB 补全异常: %s', row['detail_url'])
            success = False
        with lock:
            done += 1
            if success:
                ok += 1
            else:
                fail += 1
            if done % 20 == 0 or done == total:
                logger.info('TMDB 补全进度 %d/%d（成功 %d / 未匹配 %d）', done, total, ok, fail)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, r) for r in rows]
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception:
                logger.exception('TMDB 任务异常')

    logger.info('TMDB 补全完成：成功 %d / 未匹配 %d / 共 %d', ok, fail, total)
