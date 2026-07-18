#!/usr/bin/env python

__all__ = ()

import logging
import asyncio
import argparse
from pathlib import Path
from typing import Never

from steamcb.errors import BadSessionException, ZeroAnswerException
from steamcb.lib import SESSION_ID, STEAM_LOGIN_SECURE, Parser
from steamcb.tools import AnsiDecor, AnsiExtra


class _ArgumentParser(argparse.ArgumentParser):
    def exit_(self, status: int, message: str) -> Never:
        super().exit(status, f'\n{AnsiDecor.RED}{message}{AnsiDecor.END}\n')


class _LoggingHandler(logging.StreamHandler):
    def filter(self, record) -> bool:
        if not hasattr(record, AnsiExtra.KEY):
            setattr(record, AnsiExtra.KEY, AnsiDecor.PURPLE)
        return True


def _main() -> None:
    parser = _ArgumentParser(
        prog='steam-cloud-backup',
        description='micro-tool for downloading all save files from steam cloud',
    )

    # session group
    group = parser.add_argument_group('session')
    group.add_argument(
        '-i',
        f'--{SESSION_ID}',
        type=str,
    )
    group.add_argument(
        '-s',
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
    group.add_argument('folder', nargs='?', type=Path)
    group.add_argument(
        '-l',
        '--list',
        action='store_true',
        help='just display the list of games',
    )
    group.add_argument(
        '-o',
        '--only',
        help="""download only specific games.
Selection can be by element in the list (#1) (#10-12) (not recommended),
game name (factorio),
appid (427520).
delimeter `;`""",
        type=str,
    )
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

    if not args.list and args.folder is None:
        parser.exit_(2, 'folder positional argument is required')

    # data
    try:
        for k in (STEAM_LOGIN_SECURE,):
            attr = getattr(args, k)
            if not attr:
                if not (value := input(f'{k}: ')):
                    raise
                setattr(args, k, value)
    except Exception, KeyboardInterrupt:
        parser.exit_(103, 'not enough data')

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

    only_games: set[str] = set()
    if args.only is not None:
        for select in args.only.split(';'):
            select = select.strip()
            if select.startswith('#'):
                if select.find('-') != -1:
                    start, end = map(int, select[1:].split('-', 1))
                    only_games |= set(map(lambda a: f'#{a}', range(start, end + 1)))
                    continue
                only_games.add(select)
                continue
            only_games.add(select.lower())

    # parser
    async def work():
        async with Parser(
            c_session_id=getattr(args, SESSION_ID),
            c_steam_login_secure=getattr(args, STEAM_LOGIN_SECURE),
            concurrent_connections=args.max_concurrent_connections,
            connect_timeout=args.connect_timeout,
            useragent=args.useragent,
        ) as p:
            if args.list:
                rows = await p.parse_games()

                row_format = '{:<25}' * len(rows)
                print(AnsiDecor.GRAY, row_format.format('No', 'appid', 'name'))
                for i, (name, *_, url) in enumerate(rows, start=1):
                    app_id = url[url.rindex('?appid=') + 7 :]
                    color = AnsiDecor.GREEN if i % 2 == 0 else AnsiDecor.CYAN
                    print(color, row_format.format(f'#{i}', app_id, name))

                return

            await p.parse(
                only=only_games,
                path_to_folder=args.folder,
            )

    try:
        asyncio.run(work())
    except BadSessionException:
        parser.exit_(100, 'bad cookie session')
    except ZeroAnswerException:
        parser.exit_(101, 'steam return zero table')
    except KeyboardInterrupt:
        parser.exit_(102, 'user kill task')


if __name__ == '__main__':
    _main()
