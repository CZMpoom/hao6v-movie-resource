# -*- coding: utf-8 -*-
"""启动 Flask Web 服务：python run_web.py [--port 5000]"""
import argparse

import config
from common.logger import get_logger, setup_logging
from web.app import create_app

logger = get_logger(__name__)


def main():
    setup_logging()
    parser = argparse.ArgumentParser(description='启动 6v 影视资源库 Web')
    parser.add_argument('--host', default=config.WEB_HOST)
    parser.add_argument('--port', type=int, default=config.WEB_PORT)
    parser.add_argument('--debug', action='store_true')
    args = parser.parse_args()
    app = create_app()
    logger.info('Web 服务启动: http://%s:%s', args.host, args.port)
    app.run(host=args.host, port=args.port, debug=args.debug,
            threaded=True, use_reloader=False)


if __name__ == '__main__':
    main()
