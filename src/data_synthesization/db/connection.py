from contextlib import contextmanager
from typing import Iterator

from psycopg import Connection


@contextmanager
def connect(database_source_name: str) -> Iterator[Connection]:
    try:
        import psycopg

        with psycopg.connect(database_source_name) as connection:
            yield connection
        return
    except ModuleNotFoundError as e:
        raise RuntimeError("psycopg is not installed") from e
