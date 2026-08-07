# -*- coding: utf-8 -*-
"""MySQL 访问工具（pymysql）：线程级连接 + 常用 SQL 辅助。"""
import os
import threading

import pymysql
import pymysql.cursors

import config

_tls = threading.local()
_LOST_CONNECTION_CODES = (2006, 2013)  # MySQL server has gone away / Lost connection


def connect():
    """创建一条新连接。"""
    return pymysql.connect(
        host=config.DB_HOST,
        port=config.DB_PORT,
        user=config.DB_USER,
        password=config.DB_PASSWORD,
        database=config.DB_NAME,
        charset=config.DB_CHARSET,
        cursorclass=pymysql.cursors.DictCursor,
        autocommit=True,
        connect_timeout=10,
    )


def connection():
    """获取当前线程的连接（懒创建，线程内复用）。"""
    conn = getattr(_tls, 'conn', None)
    if conn is None or not conn.open:
        conn = connect()
        _tls.conn = conn
    return conn


def query(sql, args=None):
    def run():
        with connection().cursor() as cur:
            cur.execute(sql, args)
            return cur.fetchall()
    return _retry_on_lost(run)


def query_one(sql, args=None):
    rows = query(sql, args)
    return rows[0] if rows else None


def execute(sql, args=None):
    def run():
        with connection().cursor() as cur:
            return cur.execute(sql, args)
    return _retry_on_lost(run)


def executemany(sql, args_list):
    def run():
        with connection().cursor() as cur:
            return cur.executemany(sql, args_list)
    return _retry_on_lost(run)


def _retry_on_lost(fn):
    """连接丢失（2006/2013）时重建连接重试一次。"""
    try:
        return fn()
    except pymysql.OperationalError as exc:
        if exc.args and exc.args[0] in _LOST_CONNECTION_CODES:
            _tls.conn = None
            return fn()
        raise


def init_schema(schema_file='schema.sql'):
    """执行 schema.sql 建表。"""
    base = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    with open(os.path.join(base, schema_file), encoding='utf-8') as f:
        script = f.read()
    conn = connect()
    try:
        with conn.cursor() as cur:
            for stmt in script.split(';'):
                stmt = stmt.strip()
                if stmt:
                    cur.execute(stmt)
    finally:
        conn.close()


def drop_tables():
    """清空并删除本项目的三张表（数据不可恢复，谨慎使用）。"""
    conn = connect()
    try:
        with conn.cursor() as cur:
            cur.execute('SET FOREIGN_KEY_CHECKS = 0')
            cur.execute('DROP TABLE IF EXISTS resource_categories')
            cur.execute('DROP TABLE IF EXISTS resources')
            cur.execute('DROP TABLE IF EXISTS categories')
            cur.execute('SET FOREIGN_KEY_CHECKS = 1')
    finally:
        conn.close()
