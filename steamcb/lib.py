__all__ = ('Parser',)

import math
import random
import string
import logging
import asyncio
from pathlib import Path

import aiofiles
import aiohttp
from aiohttp import TCPConnector

from steamcb.tools import AnsiExtra, TableParser
from steamcb.errors import BadSessionException, DownloadException, ZeroAnswerException


# datalink
REMOTE_STORAGE_URL = 'https://store.steampowered.com/account/remotestorage'

# cookie key names
SESSION_ID = 'sessionId'
STEAM_LOGIN_SECURE = 'steamLoginSecure'

# max rows per page
STEAM_PER_PAGE = 50

# connection
DEFAULT_USER_AGENT = (
    'Mozilla/5.0 (X11; Linux x86_64) '
    'AppleWebKit/537.36 (KHTML, like Gecko) '
    'Chrome/60.0.3112.32 '
    'Safari/537.36'
)

# logging
logger = logging.getLogger(__name__)


class Parser:
    def __init__(
        self,
        c_steam_login_secure: str,
        concurrent_connections: int,
        connect_timeout: int,
        useragent: str | None,
        c_session_id: str | None,
    ):

        c_session_id = Parser.gen_session_id() if c_session_id is None else c_session_id
        useragent = DEFAULT_USER_AGENT if useragent is None else useragent

        self.session = aiohttp.ClientSession(
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
        )

    @staticmethod
    def gen_session_id() -> str:
        return ''.join(
            random.choices(
                string.ascii_lowercase + string.digits,
                k=24,
            )
        )

    async def parse_games(self) -> list[tuple[str, ...]]:
        text: str
        async with self.session.get(url=REMOTE_STORAGE_URL) as r:
            logger.debug('%s', str(r))

            if not r.ok:
                raise BadSessionException
            text = await r.text()
            # print(text)

        if 'g_AccountID = 0;' in text:
            raise BadSessionException

        g_parser = TableParser()
        g_parser.feed(text)

        if not g_parser.rows:
            raise ZeroAnswerException

        return g_parser.rows

    async def parse(self, only: set[str], path_to_folder: Path) -> None:
        path_to_folder.mkdir(parents=True, exist_ok=True)

        #                 / size
        for i, (name, rows_c, _, g_url) in enumerate(await self.parse_games(), start=1):
            if (
                not only
                or g_url[g_url.rindex('?appid=') + 7 :] in only
                or name.lower() in only
                or f'#{i}' in only
            ):
                ...
            else:
                continue

            logger.info(
                'iter game: %s; files count: %s', name, rows_c, extra=AnsiExtra.GREEN
            )

            game_path = path_to_folder / name

            for page in range(math.ceil(int(rows_c) / STEAM_PER_PAGE)):
                params = {'index': page * STEAM_PER_PAGE} if page else None

                first_iter = True
                bad_files: set[Path] = set()
                while first_iter or bad_files:
                    logger.debug('bad files to fix: %s', str(bad_files))
                    try:
                        l_parser: TableParser
                        async with self.session.get(url=g_url, params=params) as dr:
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
                                        self.download_file(l_url, file_path, size)
                                    )
                    except* DownloadException as errs:
                        for e in errs.exceptions:
                            bad_files.add(e.path)
                    except* Exception:
                        await asyncio.sleep(1)

                    first_iter = False

        logger.info('backup success', extra=AnsiExtra.GREEN)

    async def download_file(
        self,
        url: str,
        path: Path,
        size: str,
        chunk_size: int = 8_192,
    ) -> None:
        try:
            async with self.session.get(url=url) as r:
                r.raise_for_status()

                async with aiofiles.open(path, 'wb') as f:
                    logger.info(
                        'download file %s; size: %s', path, size, extra=AnsiExtra.CYAN
                    )
                    async for chunk in r.content.iter_chunked(chunk_size):
                        await f.write(chunk)

        except Exception as err:
            logger.debug('%s: %s', type(err), str(err), extra=AnsiExtra.RED)
            raise DownloadException(path)

    async def __aenter__(self) -> Parser:
        return self

    async def __aexit__(self, *args, **kwargs) -> None:
        await self.session.__aexit__(*args, **kwargs)
