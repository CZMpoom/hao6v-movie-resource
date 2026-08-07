# -*- coding: utf-8 -*-
"""爬虫一键入口：建表 → 抓列表 → 抓详情（含磁力）→ TMDB 补全。

用法示例：
  python run_crawler.py                          # 全流程
  python run_crawler.py --steps lists details    # 只跑指定步骤
  python run_crawler.py --reset                  # 清空全部数据后重抓
  python run_crawler.py --category dongzuo --pages 1 --limit 5   # 小规模调试
"""
import argparse
import time

import config
from common import db
from common.logger import get_logger, setup_logging
from spider import crawler
from tmdb import enrich

logger = get_logger(__name__)


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description='6v 电影网爬虫 + TMDB 补全')
    parser.add_argument(
        '--steps', nargs='+',
        choices=['schema', 'lists', 'details', 'tmdb', 'ratings'],
        default=['schema', 'lists', 'details', 'tmdb'],
        help='要执行的步骤（默认全部）',
    )
    parser.add_argument('--pages', type=int, default=config.DEFAULT_PAGES_PER_CATEGORY,
                        help='每个类型抓取前 N 页（默认 20）')
    parser.add_argument('--reset', action='store_true',
                        help='清空数据库全部数据后重新抓取')
    parser.add_argument('--category', type=str, default=None,
                        help='只抓指定类型 slug，逗号分隔（如 dongzuo 或 dlz,rj,mj），调试用')
    parser.add_argument('--list-workers', type=int, default=config.LIST_WORKERS)
    parser.add_argument('--detail-workers', type=int, default=config.DETAIL_WORKERS)
    parser.add_argument('--tmdb-workers', type=int, default=config.TMDB_WORKERS)
    parser.add_argument('--limit', type=int, default=None,
                        help='详情/TMDB 处理条数上限（调试用）')
    args = parser.parse_args()

    logger.info('========== 任务开始 ==========')
    start = time.time()

    if 'schema' in args.steps:
        if args.reset:
            db.drop_tables()
            logger.warning('已清空全部数据（categories/resources/resource_categories）')
        crawler.init_db()

    if 'lists' in args.steps:
        crawler.crawl_lists(pages=args.pages, workers=args.list_workers,
                            category_slug=args.category)

    if 'details' in args.steps:
        crawler.crawl_details(workers=args.detail_workers, limit=args.limit)

    if 'tmdb' in args.steps:
        enrich.enrich_resources(workers=args.tmdb_workers, limit=args.limit)

    if 'ratings' in args.steps:
        enrich.backfill_ratings(workers=args.tmdb_workers, limit=args.limit)

    crawler.summary()
    logger.info('========== 任务结束，耗时 %.1f 分钟 ==========', (time.time() - start) / 60)


if __name__ == '__main__':
    main()
