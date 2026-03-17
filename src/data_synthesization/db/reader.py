from typing import Sequence

from psycopg import Connection

from data_synthesization.domain.models import BinActivityRecord, BinRecord


def read_vehicles(conn: Connection) -> list[int]:
    query = """
            SELECT id
            FROM vehicle
            ORDER BY id ASC
            """
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows: Sequence[tuple[int]] = cursor.fetchall()

    return [int(row[0]) for row in rows]


def read_bins(conn: Connection) -> list[BinRecord]:
    query = """
            SELECT id, volume, coord_x, coord_y, created_at
            FROM bin
            ORDER BY id ASC \
            """
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows: Sequence[tuple[int, int, float, float, object]] = cursor.fetchall()

    return [BinRecord(id=int(row[0]), volume=int(row[1]), coord_x=float(row[2]), coord_y=float(row[3]), created_at=row[4])
            for row in rows
            ]


def read_bin_activities(conn: Connection) -> list[BinActivityRecord]:
    query = """
            SELECT bin_id, active, activity_timestamp
            FROM bin_activity
            ORDER BY bin_id ASC, activity_timestamp ASC
            """
    with conn.cursor() as cursor:
        cursor.execute(query)
        rows: Sequence[tuple[int, bool, object]] = cursor.fetchall()

    return [
        BinActivityRecord(bin_id=int(row[0]), active=bool(row[1]), activity_timestamp=row[2])
        for row in rows
    ]
