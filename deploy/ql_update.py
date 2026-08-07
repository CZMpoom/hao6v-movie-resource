#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""青龙面板定时任务入口：增量更新影视数据。

特性：
- 幂等、安全：只建表/补分类/增量抓取，不会清空已有数据；
- 流程：动态发现分类（18 专题 + 国剧/日韩剧/欧美剧）→ 每个类型前 20 页列表
        → 新详情页磁力 → 新资源 TMDB 补全；
- 日志写入项目 data/logs/app.log，同时输出到青龙面板日志。

青龙任务命令示例：
  cd /ql/scripts/hao6v_movie && pip3 install -r requirements.txt -q && python3 deploy/ql_update.py
定时规则示例：0 3 * * *（每天凌晨 3 点）
"""
import os
import sys
import time

# 项目根目录 = deploy 的上一级
PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
os.chdir(PROJECT_DIR)
sys.path.insert(0, PROJECT_DIR)

from common.logger import get_logger, setup_logging
from spider import crawler
from tmdb import enrich


def main():
    setup_logging()
    logger = get_logger('qinglong')
    logger.info('========== 青龙定时更新开始 ==========')
    start = time.time()

    crawler.init_db()          # 幂等：动态发现分类 + 建表（不清数据）
    crawler.crawl_lists()      # 每个类型前 20 页，增量写入
    crawler.crawl_details()    # 新资源详情页（磁力链接）
    enrich.enrich_resources()  # 新资源 TMDB 补全（简介/海报/演员/集数/评分等）
    enrich.backfill_ratings()  # 补充缺评分的历史资源
    crawler.summary()

    logger.info('========== 青龙定时更新完成，耗时 %.1f 分钟 ==========',
                (time.time() - start) / 60)


if __name__ == '__main__':
    main()
