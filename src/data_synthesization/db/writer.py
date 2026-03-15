from collections.abc import Sequence

from psycopg import Connection

from data_synthesization.domain.models import BinActivityRecord, NfcTagMappingRecord, TourRecord


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


def insert_nfc_tag_mappings(conn: Connection, records: Sequence[NfcTagMappingRecord]) -> None:
    if not records:
        return

    query = """
            INSERT INTO nfc_tag_mapping (uid, bin_id, mapped_at, unmapped_at)
            VALUES (%s, %s, %s, %s) \
            """
    payload = [
        (record.uid, record.bin_id, record.mapped_at, record.unmapped_at)
        for record in records
    ]

    with conn.cursor() as cursor:
        cursor.executemany(query, payload)


def insert_tours(conn: Connection, records: Sequence[TourRecord]) -> None:
    if not records:
        return

    query = """
            INSERT INTO tour (started_at, ended_at, vehicle_id)
            VALUES (%s, %s, %s)
            """
    payload = [(record.started_at, record.ended_at, record.vehicle_id) for record in records]

    with conn.cursor() as cursor:
        cursor.executemany(query, payload)
