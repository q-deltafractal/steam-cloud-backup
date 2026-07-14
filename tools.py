__all__ = ('TableParser',)

import io
from html.parser import HTMLParser


class _CellIO(io.StringIO):
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

    _current_row: list[str]
    _cell_buf: _CellIO

    def __init__(self) -> None:
        super().__init__()

        self._in_tr = False
        self._in_td = False

        self.rows: list[tuple[str, ...]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()

        if tag == 'tr':
            self._in_tr = True
            self._current_row = []
        elif self._in_tr and tag == 'td':
            self._in_td = True
            self._cell_buf = _CellIO()
        elif tag == 'a':
            #                   `href=` attr
            self._cell_buf.write(attrs[0][1])
            self._cell_buf.shadow_close = True

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()

        if tag == 'tr':
            if self._current_row:
                self.rows.append(tuple(self._current_row))
            self._in_tr = False
        if self._in_tr and tag == 'td':
            self._cell_buf.seek(0)
            cell = self._cell_buf.read().strip()
            #                       void is not a correct folder name
            self._current_row.append(cell if cell else '_')

            self._in_td = False

    def handle_data(self, data: str) -> None:
        if self._in_tr and self._in_td:
            self._cell_buf.write(data)

    def feed(self, html: str, *args, **kwargs) -> None:
        super().feed(
            html[html.index('<tbody>') + 7 : html.rindex('</tbody>')].strip(),
            *args,
            **kwargs,
        )
