# -*- coding: utf-8 -*-
"""解析 6v 电影网（www.hao6v.cc）的页面。

站点为 GB2312/GB18030 编码的静态页：
- 首页：从 #menu 的两个 <p> 元素解析分类（主菜单 + 专题分类）；
- 列表页：每条记录是一个指向详情页的 <a>，URL 形如 /dy/2026-08-05/50144.html；
- 详情页：只取 magnet: 磁力链接（按约定，其余详细信息一律来自 TMDB）。
"""
import re

from bs4 import BeautifulSoup

import config
from common.logger import get_logger

logger = get_logger(__name__)

DETAIL_LINK_RE = re.compile(r'^/(?:[^/]+)/(\d{4}-\d{2}-\d{2})/(\d+)\.html$')


def parse_list_page(html):
    """解析列表页，返回按 URL 去重后的 [{title, url}]。

    只解析正文列表 ul.list（头部导航、侧栏推荐 ul.lt 等不属于当前类型）。
    """
    soup = BeautifulSoup(html, 'html.parser')
    anchors = []
    for ul in soup.select('ul.list'):
        anchors.extend(ul.select('a[href]'))
    if not anchors:
        # 兜底：从 #main 中排除侧栏推荐后再取详情链接
        main = soup.select_one('#main')
        if main:
            for ul in main.select('ul.lt'):
                ul.decompose()
            anchors = main.select('a[href]')

    items, seen = [], set()
    for a in anchors:
        href = (a.get('href') or '').strip()
        if not DETAIL_LINK_RE.match(href):
            continue
        title = a.get_text(' ', strip=True)
        if not title or href in seen:
            continue
        seen.add(href)
        items.append({'title': title, 'url': href})
    logger.debug('列表页解析到 %d 条记录', len(items))
    return items


def parse_menu_categories(html):
    """从首页 #menu 的两个 <p> 元素解析分类链接。

    返回 [{name, slug, url}]，仅含站内分类链接（自动排除首页/新版6V等）。
    """
    soup = BeautifulSoup(html, 'html.parser')
    cats, seen = [], set()
    for node in soup.select(config.MENU_SELECTOR):
        for a in node.select('a[href]'):
            href = (a.get('href') or '').strip()
            if not href.startswith('/') or href == '/' or href.startswith('//'):
                continue
            name = a.get_text(strip=True)
            if not name:
                continue
            slug = href.strip('/').rsplit('/', 1)[-1]
            if not slug or slug in seen:
                continue
            seen.add(slug)
            cats.append({'name': name, 'slug': slug, 'url': href})
    logger.debug('首页菜单解析到 %d 个分类链接', len(cats))
    return cats


def parse_detail_page(html):
    """解析详情页，仅提取磁力链接。

    返回 {'magnets': [{'name': ..., 'url': ...}]}。
    """
    soup = BeautifulSoup(html, 'html.parser')
    magnets = [
        {'name': a.get_text(strip=True) or '磁力链接', 'url': a['href']}
        for a in soup.select('a[href^="magnet:"]')
    ]
    logger.debug('详情页解析到 %d 条磁力链接', len(magnets))
    return {'magnets': magnets}
