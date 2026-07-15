__all__ = ('parse',)

import math
import random
import string
import logging
import asyncio
from pathlib import Path

import aiofiles
import aiohttp
from aiohttp import TCPConnector

from steamcb.tools import TableParser
from steamcb.errors import BadSessionException, DownloadException, ZeroAnswerException


# datalink
REMOTE_STORAGE_URL = 'https://store.steampowered.com/account/remotestorage'

# cookie key names
SESSION_ID = 'sessionId'
STEAM_LOGIN_SECURE = 'steamLoginSecure'

# max rows per page
STEAM_PER_PAGE = 50

# logging
logger = logging.getLogger(__name__)


async def parse(
    c_steam_login_secure: str,
    path_to_folder: Path,
    useragent: str,
    concurrent_connections: int,
    connect_timeout: int,
    c_session_id: str | None = None,
) -> None:
    if c_session_id is None:
        # steam default `sessionId` scheme
        c_session_id = ''.join(
            random.choices(string.ascii_lowercase + string.digits, k=24)
        )

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
            logger.debug('%s', str(r))

            if not r.ok:
                raise BadSessionException
            text = await r.text()

        if 'g_AccountID = 0;' in text:
            raise BadSessionException

        g_parser = TableParser()
        g_parser.feed(text)

        path_to_folder.mkdir(parents=True, exist_ok=True)

        if not (games_table := g_parser.rows):
            raise ZeroAnswerException
        #                 / size
        for name, rows_c, _, g_url in games_table:
            logger.info('iter game: %s; files count: %s', name, rows_c)

            game_path = path_to_folder / name

            for page in range(math.ceil(int(rows_c) / STEAM_PER_PAGE)):
                params = {'index': page * STEAM_PER_PAGE} if page else None

                first_iter = True
                bad_files: set[Path] = set()
                while first_iter or bad_files:
                    logger.debug('%s', str(bad_files))
                    try:
                        l_parser: TableParser
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
    
    logger.info('backup success')


async def download_file(
    session: aiohttp.ClientSession,
    url: str,
    path: Path,
    size: str,
    chunk_size: int = 8_192,
) -> None:
    try:
        async with session.get(url=url) as r:
            r.raise_for_status()

            async with aiofiles.open(path, 'wb') as f:
                logger.info('download file %s; size: %s', path, size)
                async for chunk in r.content.iter_chunked(chunk_size):
                    await f.write(chunk)

    except Exception as err:
        logger.debug('%s: %s', type(err), str(err))
        raise DownloadException(path)
