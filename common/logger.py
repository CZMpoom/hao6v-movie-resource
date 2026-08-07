# -*- coding: utf-8 -*-
"""日志配置：同时输出到控制台与 data/logs/app.log（按大小轮转）。"""
import logging
import os
import sys
from logging.handlers import RotatingFileHandler

import config

_FORMAT = '%(asctime)s | %(levelname)-7s | %(name)s | %(message)s'
_DATE_FMT = '%Y-%m-%d %H:%M:%S'
_configured = False


def setup_logging(level=None):
    """初始化根日志器：控制台 + 文件。可重复调用，仅生效一次。"""
    global _configured
    if _configured:
        return
    _configured = True

    # 避免 Windows 控制台（GBK）遇到非常用字符时抛 UnicodeEncodeError
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(errors='replace')
        except Exception:
            pass

    os.makedirs(config.LOG_DIR, exist_ok=True)
    level = level or getattr(logging, config.LOG_LEVEL.upper(), logging.INFO)
    root = logging.getLogger()
    root.setLevel(level)
    fmt = logging.Formatter(_FORMAT, _DATE_FMT)

    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(fmt)
    root.addHandler(console)

    file_handler = RotatingFileHandler(
        os.path.join(config.LOG_DIR, 'app.log'),
        maxBytes=20 * 1024 * 1024,
        backupCount=10,
        encoding='utf-8',
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)
    root.addHandler(file_handler)


def get_logger(name):
    setup_logging()
    return logging.getLogger(name)
