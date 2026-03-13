from collections.abc import Sequence

from psycopg import Connection

from data_synthesization.domain.models import BinActivityRecord


def insert_bin_activity(conn: Connection, records: Sequence[BinActivityRecord]) -> None:
    if not records:
        return

    query = """
            INSERT INTO bin_activity (bin_id, active, activity_timestamp)
            VALUES (%s, %s, %s) \
            """
    payload = [(rec.bin_id, rec.active, rec.activity_timestamp) for rec in records]

    with conn.cursor() as cursor:
        cursor.executemany(query, payload)
