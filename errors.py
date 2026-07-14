__all__ = (
    'ParserException',
    'BadSessionException',
    'ZeroAnswerException',
    'DownloadException',
)

from pathlib import Path


class ParserException(Exception): ...


class BadSessionException(ParserException): ...


class ZeroAnswerException(ParserException): ...


class DownloadException(ParserException):
    def __init__(self, path: Path) -> None:
        super().__init__()
        self.path = path
