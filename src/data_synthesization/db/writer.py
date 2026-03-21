from collections.abc import Sequence
from datetime import datetime

from psycopg import Connection

from data_synthesization.domain.models import (
    BinActivityRecord,
    BinVisitRecord,
    NfcTagMappingRecord,
    TourRecord,
    VehicleEmptyingRecord,
)


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


def insert_bin_visits(conn: Connection, records: Sequence[BinVisitRecord]) -> None:
    if not records:
        return

    query = """
            INSERT INTO bin_visit (
                client_event_id,
                event_timestamp,
                received_timestamp,
                connectivity_state,
                fill_level,
                action,
                tour_id,
                nfc_tag_mapping_id
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            """
    payload = [
        (
            record.client_event_id,
            record.event_timestamp,
            record.received_timestamp,
            record.connectivity_state.value,
            record.fill_level.value,
            record.action.value,
            record.tour_id,
            record.nfc_tag_mapping_id,
        )
        for record in records
    ]

    with conn.cursor() as cursor:
        cursor.executemany(query, payload)


def insert_vehicle_emptyings(conn: Connection, records: Sequence[VehicleEmptyingRecord]) -> None:
    if not records:
        return

    query = """
            INSERT INTO vehicle_emptying (
                event_timestamp,
                received_timestamp,
                client_event_id,
                connectivity_state,
                tour_id
            )
            VALUES (%s, %s, %s, %s, %s)
            """
    payload = [
        (
            record.event_timestamp,
            record.received_timestamp,
            record.client_event_id,
            record.connectivity_state.value,
            record.tour_id,
        )
        for record in records
    ]

    with conn.cursor() as cursor:
        cursor.executemany(query, payload)

def update_tours_ended_at(conn: Connection, records: Sequence[
    tuple[int, datetime]
]) -> None:
    if not records:
        return

    query  = """
    UPDATE tour
    SET ended_at = %s
        WHERE id = %s
        AND ended_at IS NULL
        
    """
    payload = [(ended_at, tour_id) for tour_id, ended_at in records]
    with conn.cursor() as cursor:
        cursor.executemany(query, payload)