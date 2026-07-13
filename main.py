#!/usr/bin/env python

import io
import math
import logging
import asyncio
import argparse
from pathlib import Path
from typing import LiteralString
from html.parser import HTMLParser

import aiofiles
import aiohttp
from aiohttp import TCPConnector


# datalink
REMOTE_STORAGE_URL = 'https://store.steampowered.com/account/remotestorage'

# cookie key names
SESSION_ID = 'sessionId'
STEAM_LOGIN_SECURE = 'steamLoginSecure'

# max rows per page
STEAM_PER_PAGE = 50

DEFAULT_USER_AGENT = (
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/150.0.0.0 Safari/537.36'
)

#
logger = logging.getLogger(__name__)


class ParserException(Exception): ...


class BadSessionException(ParserException): ...


class ZeroAnswerException(ParserException): ...


class DownloadException(ParserException):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path


class CellIO(io.StringIO):
    """override io.StringIO with write blocking"""

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.shadow_close = False

    def write(self, *args, **kwargs) -> int:
        if not self.shadow_close:
            return super().write(*args, **kwargs)
        return -1


class TableParser(HTMLParser):
    """parse steam backend table in py objects"""

    def __init__(self) -> None:
        super().__init__()

        self._in_tr = False
        self._in_td = False

        self.current_row = []
        self.cell_buf = CellIO()

        self.rows = []

    def handle_starttag(self, tag, attrs) -> None:
        tag = tag.lower()

        if tag == 'tr':
            self._in_tr = True
            self.current_row = []
        elif self._in_tr and tag == 'td':
            self._in_td = True
            self.cell_buf = CellIO()
        elif tag == 'a':
            #                   `href=` attr
            self.cell_buf.write(attrs[0][1])
            self.cell_buf.shadow_close = True

    def handle_endtag(self, tag) -> None:
        tag = tag.lower()

        if tag == 'tr':
            if self.current_row:
                self.rows.append(tuple(self.current_row))
            self._in_tr = False
        if self._in_tr and tag == 'td':
            self.cell_buf.seek(0)
            cell = self.cell_buf.read().strip()
            #                       void is not a correct folder name
            self.current_row.append(cell if cell else '_')

            self._in_td = False
            self.cell_buf = CellIO()

    def handle_data(self, data) -> None:
        if self._in_tr and self._in_td:
            self.cell_buf.write(data)

    def feed(self, html: str, *args, **kwargs) -> None:
        super().feed(
            html[html.index('<tbody>') + 7 : html.rindex('</tbody>')].strip(),
            *args,
            **kwargs,
        )


async def parse(
    c_session_id: LiteralString,
    c_steam_login_secure: LiteralString,
    path_to_folder: Path,
    useragent: LiteralString,
    concurrent_connections: int,
    connect_timeout: int,
) -> None:
    async with aiohttp.ClientSession(
        connector=TCPConnector(limit=concurrent_connections, ttl_dns_cache=300),
        timeout=aiohttp.ClientTimeout(total=connect_timeout),
        headers={
            'User-Agent': useragent,
        },
        cookies={
            SESSION_ID: c_session_id,
            STEAM_LOGIN_SECURE: c_steam_login_secure,
        },
        cookie_jar=aiohttp.CookieJar(),
    ) as session:
        text: str
        async with session.get(url=REMOTE_STORAGE_URL) as r:
            r.raise_for_status()
            text = await r.text()

        if 'g_AccountID = 0;' in text:
            raise BadSessionException

        g_parser = TableParser()
        g_parser.feed(text)

        path.mkdir(parents=True, exist_ok=True)

        if not (games_table := g_parser.rows):
            raise ZeroAnswerException
        #                 /size
        for name, rows_c, _, g_url in games_table:
            logger.info(f'iter game: {name}; files count: {rows_c}')

            game_path = path_to_folder / name

            for page in range(math.ceil(int(rows_c) / STEAM_PER_PAGE)):
                params = {'index': page * STEAM_PER_PAGE} if page else None

                first_iter = True
                bad_files: set[Path] = set()
                while first_iter or bad_files:
                    try:
                        async with session.get(url=g_url, params=params) as dr:
                            l_parser = TableParser()
                            l_parser.feed(await dr.text())

                        async with asyncio.TaskGroup() as task_g:
                            #                            / date written
                            for folder, file_name, size, _, l_url in l_parser.rows:
                                file_path = game_path / folder / file_name
                                if first_iter or (
                                    file_path in bad_files
                                    and bad_files.remove(file_path)
                                    is None  # deleting file_name in bad_files if find
                                ):
                                    file_path.parent.mkdir(parents=True, exist_ok=True)
                                    task_g.create_task(
                                        download_file(session, l_url, file_path, size)
                                    )
                    except* DownloadException as errs:
                        for e in errs.exceptions:
                            bad_files.add(e.path)
                    except* Exception:
                        await asyncio.sleep(1)

                    first_iter = False


async def download_file(
    session: aiohttp.ClientSession,
    url: LiteralString,
    path: Path,
    size: str,
    chunk_size: int = 8_192,
) -> None:
    try:
        async with session.get(url=url) as r:
            r.raise_for_status()

            async with aiofiles.open(path, 'wb') as f:
                logger.info(f'download file {path}; size: {size}')
                async for chunk in r.content.iter_chunked(chunk_size):
                    await f.write(chunk)

    except Exception:
        raise DownloadException(path)


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(
        prog='steam-cloud-backup',
        description='micro-script for downloading all save files from steam cloud',
    )

    parser.add_argument('folder')

    parser.add_argument('-i', f'--{SESSION_ID}', type=str)
    parser.add_argument('-l', f'--{STEAM_LOGIN_SECURE}', type=str)

    parser.add_argument('-j', '--max-concurrent-connections', default=16, type=int)
    parser.add_argument('--connect-timeout', default=60, type=int)
    parser.add_argument('--useragent', default=DEFAULT_USER_AGENT, type=str)

    args = parser.parse_args()

    # data
    try:
        for k in (SESSION_ID, STEAM_LOGIN_SECURE):
            attr = getattr(args, k)
            if not attr:
                if not (value := input(f'{k}: ')):
                    raise
                setattr(args, k, value)
    except KeyboardInterrupt:
        parser.exit(1, '\nnot enough data\n')

    path = (
        args.folder
        if (Path(args.folder)).is_absolute()
        else Path().absolute() / args.folder
    )

    # parser
    try:
        asyncio.run(
            parse(
                c_session_id=getattr(args, SESSION_ID),
                c_steam_login_secure=getattr(args, STEAM_LOGIN_SECURE),
                concurrent_connections=args.max_concurrent_connections,
                connect_timeout=args.connect_timeout,
                path_to_folder=path,
                useragent=args.useragent,
            )
        )
    except BadSessionException:
        parser.exit(2, 'bad cookie session\n')
    except ZeroAnswerException:
        parser.exit(3, 'steam return zero page\m')
