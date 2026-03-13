from typing import Sequence

from psycopg import Connection

from data_synthesization.domain.models import BinRecord


def read_bins(conn: Connection) -> list[BinRecord]:
    query = """
            SELECT id, created_at
            FROM bin
            ORDER BY id ASC \
            """
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows: Sequence[tuple[int, object]] = cursor.fetchall()

    return [BinRecord(id=int(row[0]), created_at=row[1]) for row in rows]
