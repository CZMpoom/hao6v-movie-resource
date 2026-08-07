# -*- coding: utf-8 -*-
"""配置示例：复制为 config.py 后填入真实值，或用环境变量覆盖。

环境变量（优先级高于本文件默认值）：
  HAO6V_DB_HOST / HAO6V_DB_PORT / HAO6V_DB_USER / HAO6V_DB_PASSWORD / HAO6V_DB_NAME
  HAO6V_TMDB_API_KEY / HAO6V_WEB_PORT
"""
import os

# ---------- 数据库 ----------
DB_HOST = os.getenv('HAO6V_DB_HOST', '127.0.0.1')
DB_PORT = int(os.getenv('HAO6V_DB_PORT', '3306'))
DB_USER = os.getenv('HAO6V_DB_USER', 'root')
DB_PASSWORD = os.getenv('HAO6V_DB_PASSWORD', '')
DB_NAME = os.getenv('HAO6V_DB_NAME', 'hao6v')
DB_CHARSET = 'utf8mb4'

# ---------- 目标站点 ----------
SITE_BASE = 'https://www.hao6v.cc'
SITE_HEADERS = {
    'User-Agent': (
        'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 '
        '(KHTML, like Gecko) Chrome/126.0 Safari/537.36'
    ),
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# 每个类型抓取前 N 页（每页约 25 条）
DEFAULT_PAGES_PER_CATEGORY = 20

# ---------- 分类（抓取范围） ----------
ALLOWED_TOPIC_SLUGS = {
    'xiju', 'dongzuo', 'aiqing', 'kehuan', 'qihuan', 'shenmi', 'huanxiang',
    'kongbu', 'zhanzheng', 'maoxian', 'jingsong', 'juqingpian', 'zhuanji',
    'lishi', 'jilu', 'yindudianying', 'guochandianying', 'xijudianying',
}
MAIN_MENU_EXTRA_SLUGS = {'dlz', 'rj', 'mj'}
ALLOWED_CATEGORY_SLUGS = ALLOWED_TOPIC_SLUGS | MAIN_MENU_EXTRA_SLUGS
MENU_SELECTOR = '#menu p'

FALLBACK_CATEGORIES = [
    {'name': '喜剧', 'slug': 'xiju', 'url': '/s/xiju/'},
    {'name': '动作', 'slug': 'dongzuo', 'url': '/s/dongzuo/'},
    {'name': '爱情', 'slug': 'aiqing', 'url': '/s/aiqing/'},
    {'name': '科幻', 'slug': 'kehuan', 'url': '/s/kehuan/'},
    {'name': '奇幻', 'slug': 'qihuan', 'url': '/s/qihuan/'},
    {'name': '神秘', 'slug': 'shenmi', 'url': '/s/shenmi/'},
    {'name': '幻想', 'slug': 'huanxiang', 'url': '/s/huanxiang/'},
    {'name': '恐怖', 'slug': 'kongbu', 'url': '/s/kongbu/'},
    {'name': '战争', 'slug': 'zhanzheng', 'url': '/s/zhanzheng/'},
    {'name': '冒险', 'slug': 'maoxian', 'url': '/s/maoxian/'},
    {'name': '惊悚', 'slug': 'jingsong', 'url': '/s/jingsong/'},
    {'name': '剧情', 'slug': 'juqingpian', 'url': '/s/juqingpian/'},
    {'name': '传记', 'slug': 'zhuanji', 'url': '/s/zhuanji/'},
    {'name': '历史', 'slug': 'lishi', 'url': '/s/lishi/'},
    {'name': '纪录', 'slug': 'jilu', 'url': '/s/jilu/'},
    {'name': '印度电影', 'slug': 'yindudianying', 'url': '/s/yindudianying/'},
    {'name': '国产电影', 'slug': 'guochandianying', 'url': '/s/guochandianying/'},
    {'name': '欧洲电影', 'slug': 'xijudianying', 'url': '/s/xijudianying/'},
    {'name': '国剧', 'slug': 'dlz', 'url': '/dlz/'},
    {'name': '日韩剧', 'slug': 'rj', 'url': '/rj/'},
    {'name': '欧美剧', 'slug': 'mj', 'url': '/mj/'},
]

# ---------- 爬虫并发与限速 ----------
LIST_WORKERS = 6
DETAIL_WORKERS = 10
LIST_DELAY_RANGE = (0.2, 0.6)
DETAIL_DELAY_RANGE = (0.1, 0.4)
REQUEST_TIMEOUT = 30
RETRY_TIMES = 3

# ---------- TMDB ----------
TMDB_API_KEY = os.getenv('HAO6V_TMDB_API_KEY', '')  # 填入你的 TMDB v3 API Key
TMDB_BASE_URL = 'https://api.themoviedb.org/3'
TMDB_IMAGE_BASE = 'https://image.tmdb.org/t/p'
TMDB_LANGUAGE = 'zh-CN'
TMDB_WORKERS = 12
TMDB_DELAY = 0.05
TMDB_RETRY_TIMES = 4
TMDB_CAST_LIMIT = 15

# ---------- 日志 ----------
LOG_DIR = 'data/logs'
LOG_LEVEL = 'INFO'

# ---------- Web ----------
WEB_HOST = '0.0.0.0'
WEB_PORT = int(os.getenv('HAO6V_WEB_PORT', '5000'))
WEB_PAGE_SIZE = 20
