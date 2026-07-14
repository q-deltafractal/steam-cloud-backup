#!/usr/bin/env python

__all__ = ()

import logging
import asyncio
import argparse
from pathlib import Path

from steamcb.errors import BadSessionException, ZeroAnswerException
from steamcb.lib import SESSION_ID, STEAM_LOGIN_SECURE, parse


# connection
DEFAULT_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/150.0.0.0 Safari/537.36'
)


class _ArgumentParser(argparse.ArgumentParser):
    def _print_message(self, message: str, file=None) -> None:
        super()._print_message(f'\n{message}\n', file=file)


def main() -> None:
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
        default=DEFAULT_USER_AGENT,
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
        help="""logging type:
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
        parser.exit(1, '\nnot enough data\n')

    logging_level: int | None
    match args.verbose:
        case 0:
            logging_level = None
        case 1:
            logging_level = logging.INFO
        case 2:
            logging_level = logging.DEBUG

    logging.basicConfig(level=logging_level)

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
        parser.exit(2, 'bad cookie session\n')
    except ZeroAnswerException:
        parser.exit(3, 'steam return zero page\n')
    except KeyboardInterrupt:
        parser.exit(4, 'user kill task')


if __name__ == '__main__':
    main()
