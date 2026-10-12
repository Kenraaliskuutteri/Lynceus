import csv
import io
import re
from typing import Iterable, Iterator

from fastapi.responses import StreamingResponse

FLUSH_EVERY = 500
FORMULA_PREFIXES = ("=", "+", "-", "@", "\t", "\r")


def safe_cell(value):
    if isinstance(value, str) and value.startswith(FORMULA_PREFIXES):
        return "'" + value
    return value


def safe_filename(name: str) -> str:
    return re.sub(r"[^A-Za-z0-9._-]", "_", name)


def csv_response(filename: str, header: list[str], rows: Iterable[list]) -> StreamingResponse:
    def generate() -> Iterator[str]:
        buffer = io.StringIO()
        writer = csv.writer(buffer)
        writer.writerow(header)
        pending = 0
        for row in rows:
            writer.writerow([safe_cell(cell) for cell in row])
            pending += 1
            if pending >= FLUSH_EVERY:
                yield buffer.getvalue()
                buffer.seek(0)
                buffer.truncate()
                pending = 0
        yield buffer.getvalue()

    return StreamingResponse(
        generate(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="{safe_filename(filename)}"'},
    )