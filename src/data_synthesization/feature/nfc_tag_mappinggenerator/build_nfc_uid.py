import hashlib


def build_uid(bin_id: int, sequence_index: int) -> str:
    payload = f"bin:{bin_id}|mapping_sequence:{sequence_index}"
    hash = hashlib.sha256(payload.encode("utf-8")).hexdigest().upper()
    return f"0{hash[-13:]}"
