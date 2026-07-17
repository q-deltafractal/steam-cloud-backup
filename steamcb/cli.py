#!/usr/bin/env python

__all__ = ()

import logging
import asyncio
import argparse
from pathlib import Path
from typing import Never

from steamcb.errors import BadSessionException, ZeroAnswerException
from steamcb.lib import SESSION_ID, STEAM_LOGIN_SECURE, parse
from steamcb.tools import AnsiDecor, AnsiExtra


class _ArgumentParser(argparse.ArgumentParser):
    def exit_(self, status: int, message: str) -> Never:
        super().exit(status, f'test\n{AnsiDecor.RED}{message}{AnsiDecor.END}\n')


class _LoggingHandler(logging.StreamHandler):
    def filter(self, record) -> bool:
        if not hasattr(record, AnsiExtra.KEY):
            setattr(record, AnsiExtra.KEY, AnsiDecor.PURPLE)
        return True


def _main() -> None:
    parser = _ArgumentParser(
        prog='steam-cloud-backup',
        description='micro-script for downloading all save files from steam cloud',
    )

    # session group
    group = parser.add_argument_group('session')
    group.add_argument(
        '-i',
        f'--{SESSION_ID}',
        type=str,
    )
    group.add_argument(
        '-l',
        f'--{STEAM_LOGIN_SECURE}',
        type=str,
    )

    # connection group
    group = parser.add_argument_group('connection')
    group.add_argument(
        '-j',
        '--max-concurrent-connections',
        default=16,
        help='default: 16',
        type=int,
    )
    group.add_argument(
        '--connect-timeout',
        default=60,
        help='default: 60 (s)',
        type=int,
    )
    group.add_argument(
        '--useragent',
        type=str,
    )

    # out group
    group = parser.add_argument_group('out')
    group.add_argument('folder', type=Path)
    group.add_argument(
        '-v',
        '--verbose',
        choices=(0, 1, 2),
        default=1,
        help="""logging level:
0 - off;
1 (default) - info;
2 - debug""",
        type=int,
    )

    args = parser.parse_args()
    del group

    # data
    try:
        for k in (STEAM_LOGIN_SECURE,):
            attr = getattr(args, k)
            if not attr:
                if not (value := input(f'{k}: ')):
                    raise
                setattr(args, k, value)
    except Exception, KeyboardInterrupt:
        parser.exit_(1, 'not enough data')

    logging_level: int | None
    match args.verbose:
        case 0:
            logging_level = None
        case 1:
            logging_level = logging.INFO
        case 2:
            logging_level = logging.DEBUG

    logging.basicConfig(
        level=logging_level,
        format=(
            f'{AnsiDecor.GRAY}{AnsiDecor.ITALIC} %(levelname)s %(asctime)s :: '
            f'{AnsiDecor.END}%({AnsiExtra.KEY})s%(message)s{AnsiDecor.END}'
        ),
        handlers=(_LoggingHandler(),),
    )

    # parser
    try:
        asyncio.run(
            parse(
                c_session_id=getattr(args, SESSION_ID),
                c_steam_login_secure=getattr(args, STEAM_LOGIN_SECURE),
                concurrent_connections=args.max_concurrent_connections,
                connect_timeout=args.connect_timeout,
                path_to_folder=args.folder,
                useragent=args.useragent,
            )
        )
    except BadSessionException:
        parser.exit_(2, 'bad cookie session')
    except ZeroAnswerException:
        parser.exit_(3, 'steam return zero page')
    except KeyboardInterrupt:
        parser.exit_(4, 'user kill task')


if __name__ == '__main__':
    _main()
