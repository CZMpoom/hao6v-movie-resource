# -*- coding: utf-8 -*-
"""6v 电影网爬虫：列表页抓取 → 详情页（仅磁力链接）抓取。

特点：
- 分类从首页 <p class="bg"> 动态发现（白名单 18 个专题分类）；
- 每个类型抓取前 N 页（默认 20 页，每页约 25 条）；
- 从 hao6v.cc 只获取：资源名称、详情页链接、磁力链接；
- 其余详细信息（简介/海报/年份/演员/集数等）由 TMDB 阶段补全；
- 多线程 + 随机延时，日志详细，支持断点续抓（按 detail_url 去重）；
- 结果写入 MySQL（resources / categories / resource_categories）。
"""
import json
import random
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

import config
from common.db import execute, init_schema, query, query_one
from common.logger import get_logger
from spider.parser import parse_detail_page, parse_list_page, parse_menu_categories

logger = get_logger(__name__)

_YEAR_PREFIX_RE = re.compile(r'^\d{4}\s*')
_QUALITY_SUFFIX_RE = re.compile(
    r'[（(]?\d{1,4}[pP][)）]?.*$|'
    r'\.(HD|BD|MKV|MP4|RMVB|TS|WEB|DVD|AVI|MPEG|FLV|国语|粤语|中字|中英双字|双语|无水印|'
    r'内封中字|国粤双语|高清|全集|更新至\d+集?).*$'
)
_SERIES_SUFFIX_RE = re.compile(r'(全集|更新至\d+集?|第[一二三四五六七八九十百\d]+季.*)$')
_FULLWIDTH_BRACKET_RE = re.compile(r'《(.+?)》')


# ---------------------------------------------------------------- 工具

def clean_title(raw):
    """从列表页标题中提取干净的片名（去掉年份前缀、画质字幕后缀、书名号）。"""
    t = _YEAR_PREFIX_RE.sub('', (raw or '').strip())
    t = _QUALITY_SUFFIX_RE.sub('', t)
    t = _SERIES_SUFFIX_RE.sub('', t).strip()
    m = _FULLWIDTH_BRACKET_RE.search(t)
    if m:
        t = m.group(1).strip()
    return t or raw


def build_list_url(category_url, page):
    """类型第 1 页为 /xxx/，第 N 页为 /xxx/index_N.html。"""
    base = category_url.rstrip('/')
    if page <= 1:
        return base + '/'
    return f'{base}/index_{page}.html'


def fetch(url, timeout=None, retries=None, delay_range=None):
    """抓取页面并解码为文本，失败重试；返回 None 表示最终失败。"""
    timeout = timeout or config.REQUEST_TIMEOUT
    retries = retries or config.RETRY_TIMES
    full_url = url if url.startswith('http') else config.SITE_BASE + url
    if delay_range:
        time.sleep(random.uniform(*delay_range))
    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(full_url, headers=config.SITE_HEADERS, timeout=timeout)
            if resp.status_code == 200:
                resp.encoding = 'gb18030'
                return resp.text
            logger.warning('请求失败 %s HTTP %s（第 %d/%d 次）', url, resp.status_code, attempt, retries)
        except requests.RequestException as exc:
            logger.warning('请求异常 %s: %s（第 %d/%d 次）', url, exc, attempt, retries)
        if attempt < retries:
            time.sleep(min(2 ** attempt, 8) + random.random())
    return None


def init_db():
    """建表，并从首页动态发现专题分类写入数据库（按白名单过滤）。"""
    init_schema()
    categories = discover_categories()
    for c in categories:
        execute(
            """INSERT INTO categories (name, slug, url) VALUES (%s, %s, %s)
               AS new ON DUPLICATE KEY UPDATE name = new.name, url = new.url""",
            (c['name'], c['slug'], c['url']),
        )
    logger.info('数据库初始化完成：建表 + 写入 %d 个专题分类', len(categories))
    return categories


def discover_categories():
    """从首页菜单动态发现分类，并按白名单过滤（18 专题 + 国剧/日韩剧/欧美剧）。

    解析失败或白名单内无结果时回退到 config.FALLBACK_CATEGORIES。
    """
    html = fetch(config.SITE_BASE + '/')
    found = parse_menu_categories(html) if html else []
    if not found:
        logger.warning('首页分类获取/解析失败，使用兜底配置')
        return list(config.FALLBACK_CATEGORIES)

    allowed = [c for c in found if c['slug'] in config.ALLOWED_CATEGORY_SLUGS]
    skipped = [c['name'] for c in found if c['slug'] not in config.ALLOWED_CATEGORY_SLUGS]
    logger.info(
        '首页菜单分类：发现 %d 个，保留 %d 个（排除: %s）',
        len(found), len(allowed), ', '.join(skipped) if skipped else '无',
    )
    if not allowed:
        logger.warning('白名单内未发现任何分类，使用兜底配置')
        return list(config.FALLBACK_CATEGORIES)
    return allowed


# ---------------------------------------------------------------- 列表页

def crawl_lists(pages=None, workers=None, category_slug=None):
    """抓取每个类型的前 pages 页列表，写入 resources 并建立类型关联。"""
    pages = pages or config.DEFAULT_PAGES_PER_CATEGORY
    workers = workers or config.LIST_WORKERS

    categories = query('SELECT id, name, slug, url FROM categories ORDER BY id')
    if category_slug:
        category_slug = {s.strip() for s in category_slug.split(',') if s.strip()}
        categories = [c for c in categories if c['slug'] in category_slug]
        if not categories:
            logger.error('未找到类型: %s', ','.join(category_slug))
            return

    tasks = []
    for cat in categories:
        for page in range(1, pages + 1):
            tasks.append((cat, page))
    logger.info('列表页任务共 %d 个（%d 个类型 × %d 页）', len(tasks), len(categories), pages)

    stats = {'ok': 0, 'fail': 0, 'items': 0, 'empty_cats': set()}
    lock = threading.Lock()

    def work(task):
        cat, page = task
        url = build_list_url(cat['url'], page)
        html = fetch(url, delay_range=config.LIST_DELAY_RANGE)
        if html is None:
            with lock:
                stats['fail'] += 1
            logger.error('列表页抓取失败: %s', url)
            return
        items = parse_list_page(html)
        if not items:
            with lock:
                stats['empty_cats'].add(cat['id'])
            logger.warning('列表页无数据: %s（%s）', url, cat['name'])
            return
        n = _upsert_items(items, cat['id'])
        with lock:
            stats['ok'] += 1
            stats['items'] += n
        logger.info('[%s] 第 %d 页 解析 %d 条、入库 %d 条 | %s', cat['name'], page, len(items), n, url)

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, t) for t in tasks]
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception:
                logger.exception('列表页任务异常')

    logger.info(
        '列表页抓取完成：成功 %d / 失败 %d，累计入库 %d 条',
        stats['ok'], stats['fail'], stats['items'],
    )
    return stats


def _upsert_items(items, category_id):
    """写入 resources（按 detail_url 去重）并关联类型。"""
    n = 0
    for it in items:
        url = it['url']
        cleaned = clean_title(it['title'])
        execute(
            """INSERT INTO resources (title, clean_title, detail_url) VALUES (%s, %s, %s)
               AS new ON DUPLICATE KEY UPDATE title = new.title, clean_title = new.clean_title""",
            (it['title'], cleaned, url),
        )
        row = query_one('SELECT id FROM resources WHERE detail_url = %s', (url,))
        execute(
            'INSERT IGNORE INTO resource_categories (resource_id, category_id) VALUES (%s, %s)',
            (row['id'], category_id),
        )
        n += 1
    return n


# ---------------------------------------------------------------- 详情页

def crawl_details(workers=None, limit=None):
    """抓取尚未解析的详情页，仅提取并保存磁力链接。"""
    workers = workers or config.DETAIL_WORKERS
    sql = (
        "SELECT id, detail_url, title FROM resources "
        "WHERE magnets IS NULL ORDER BY id"
    )
    if limit:
        sql += f' LIMIT {int(limit)}'
    rows = query(sql)
    total = len(rows)
    logger.info('待抓取详情页 %d 条，并发 %d', total, workers)
    if not total:
        return

    done, ok, fail = 0, 0, 0
    lock = threading.Lock()

    def work(row):
        nonlocal done, ok, fail
        html = fetch(row['detail_url'], delay_range=config.DETAIL_DELAY_RANGE)
        if html is None:
            with lock:
                done += 1
                fail += 1
            logger.error('[%d/%d] 详情页失败: %s', done, total, row['detail_url'])
            return
        try:
            data = parse_detail_page(html)
            magnets = data['magnets']
            execute('UPDATE resources SET magnets = %s WHERE id = %s',
                    (json.dumps(magnets, ensure_ascii=False), row['id']))
            with lock:
                done += 1
                ok += 1
            logger.info(
                '[%d/%d] 详情页完成: %s | 磁力=%d 条 | %s',
                done, total, row['title'], len(magnets), row['detail_url'],
            )
        except Exception:
            logger.exception('写入数据库失败: %s', row['detail_url'])
            with lock:
                done += 1
                fail += 1

    with ThreadPoolExecutor(max_workers=workers) as pool:
        futures = [pool.submit(work, r) for r in rows]
        for fut in as_completed(futures):
            try:
                fut.result()
            except Exception:
                logger.exception('详情页任务异常')

    logger.info('详情页抓取完成：成功 %d / 失败 %d / 共 %d', ok, fail, total)

# ---------------------------------------------------------------- 汇总

def summary():
    total = query_one('SELECT COUNT(*) AS c FROM resources')['c']
    with_magnet = query_one(
        "SELECT COUNT(*) AS c FROM resources WHERE magnets IS NOT NULL AND magnets <> '[]'"
    )['c']
    with_tmdb = query_one('SELECT COUNT(*) AS c FROM resources WHERE tmdb_id IS NOT NULL')['c']
    tv = query_one("SELECT COUNT(*) AS c FROM resources WHERE media_type = 'tv'")['c']
    logger.info(
        '数据汇总：资源 %d（电影 %d / 剧集 %d），含磁力 %d，含 TMDB 信息 %d',
        total, total - tv, tv, with_magnet, with_tmdb,
    )
    return {'total': total, 'tv': tv, 'with_magnet': with_magnet, 'with_tmdb': with_tmdb}
