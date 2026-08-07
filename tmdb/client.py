# -*- coding: utf-8 -*-
"""TMDB v3 API 客户端：全局限速 + 重试，提供搜索与详情获取。

资源的详细信息（简介/海报/年份/演员/集数/导演/类型等）全部来自 TMDB。
"""
import random
import threading
import time

import requests

import config
from common.logger import get_logger

logger = get_logger(__name__)

_lock = threading.Lock()
_last_request_at = 0.0


def _rate_limited_get(url, params, retries=None):
    """带全局间隔与重试的 GET。返回 JSON dict 或 None。"""
    global _last_request_at
    retries = retries or config.TMDB_RETRY_TIMES

    with _lock:
        wait = config.TMDB_DELAY - (time.time() - _last_request_at)
        if wait > 0:
            time.sleep(wait)
        _last_request_at = time.time()

    for attempt in range(1, retries + 1):
        try:
            resp = requests.get(url, params=params, timeout=config.REQUEST_TIMEOUT)
            if resp.status_code == 200:
                return resp.json()
            if resp.status_code == 429:
                logger.warning('TMDB 限流(429)，第 %d/%d 次重试', attempt, retries)
            else:
                logger.error('TMDB 请求失败: %s | HTTP %s | %s', url, resp.status_code, resp.text[:200])
        except requests.RequestException as exc:
            logger.warning('TMDB 请求异常: %s | %s（第 %d/%d 次）', url, exc, attempt, retries)
        if attempt < retries:
            time.sleep(min(1.5 * attempt, 10) + random.random())
    return None


def search_multi(title, year=None):
    """用 /search/multi 同时搜索电影与剧集，按年份匹配度排序。

    year 为列表页标题中的年份提示（仅用于匹配排序，不落库）。
    """
    params = {
        'api_key': config.TMDB_API_KEY,
        'query': title,
        'language': config.TMDB_LANGUAGE,
        'page': 1,
    }
    data = _rate_limited_get(f'{config.TMDB_BASE_URL}/search/multi', params)
    results = [
        r for r in (data or {}).get('results') or []
        if r.get('media_type') in ('movie', 'tv')
    ]

    def score(result):
        s = 0
        ry = (result.get('release_date') or result.get('first_air_date') or '')[:4]
        if year and ry:
            try:
                diff = abs(int(ry) - year)
                s = max(0, 20 - diff * 4)
            except ValueError:
                pass
        return s

    results = sorted(results, key=score, reverse=True)
    logger.debug(
        'TMDB 搜索 "%s" 年=%s -> %d 个结果，首选 [%s] %s',
        title, year, len(results),
        results[0].get('media_type') if results else None,
        (results[0].get('name') or results[0].get('title')) if results else None,
    )
    return results


def get_details(media_type, tmdb_id):
    """获取详情 + 演职员表；中文简介为空时回退英文。"""
    endpoint = 'tv' if media_type == 'tv' else 'movie'
    base = f'{config.TMDB_BASE_URL}/{endpoint}/{tmdb_id}'
    params = {
        'api_key': config.TMDB_API_KEY,
        'language': config.TMDB_LANGUAGE,
        'append_to_response': 'credits',
    }
    data = _rate_limited_get(base, params)
    if not data:
        return None

    if not data.get('overview'):
        logger.debug('中文简介为空，回退英文简介: %s', tmdb_id)
        params['language'] = 'en-US'
        fallback = _rate_limited_get(base, params)
        if fallback:
            data = {**data, **{k: fallback.get(k) for k in ('overview', 'title', 'name')}}

    credits = data.get('credits') or {}
    cast = [c.get('name') for c in (credits.get('cast') or [])[:config.TMDB_CAST_LIMIT]]
    director = None
    for crew in credits.get('crew') or []:
        if crew.get('job') == 'Director':
            director = crew.get('name')
            break
    is_tv = media_type == 'tv'
    return {
        'tmdb_id': data.get('id'),
        'title': (data.get('name') or data.get('title') or '').strip(),
        'media_type': media_type,
        'overview': (data.get('overview') or '').strip(),
        'poster_path': data.get('poster_path'),
        'release_date': (data.get('first_air_date') or data.get('release_date') or None),
        'year': (data.get('first_air_date') or data.get('release_date') or '')[:4] or None,
        'rating': data.get('vote_average'),
        'episode_count': data.get('number_of_episodes') if is_tv else None,
        'director': director,
        'genre': ' / '.join(g.get('name') for g in (data.get('genres') or []) if g.get('name')),
        'language': ' / '.join(
            l.get('english_name') for l in (data.get('spoken_languages') or []) if l.get('english_name')),
        'country': ' / '.join(
            c.get('name') for c in (data.get('production_countries') or []) if c.get('name')),
        'cast': [c for c in cast if c],
    }
