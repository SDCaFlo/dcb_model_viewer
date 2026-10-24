"""Digimon Card Battle Card Database parser (CARD2.CDD).

Extracts official Digimon names and maps them to their 3D model IDs.
Reference: external_repository/dcb_decomp/src/main/card/card_db.c
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass
class CardInfo:
    card_id: int
    name: str
    model_id: int
    hp: int = 0
    attr: int = 0


def load_model_name_map(cdd_path: str | Path) -> dict[int, str]:
    """Parses CARD2.CDD and returns a dictionary mapping model_id -> Digimon name."""
    path = Path(cdd_path)
    if not path.is_file():
        return {}

    data = path.read_bytes()
    if len(data) < 8:
        return {}

    digimon_count = struct.unpack_from("<H", data, 4)[0]
    offset = 8
    entry_size = 0x13C  # 316 bytes per DigimonCardData in US/EU

    model_names: dict[int, str] = {}
    for _ in range(digimon_count):
        if offset + entry_size > len(data):
            break
        entry = data[offset : offset + entry_size]
        raw_name = entry[3:25].split(b"\x00")[0]
        name = raw_name.decode("ascii", errors="replace").strip()
        model_id = entry[0xE5]
        if model_id not in model_names:
            model_names[model_id] = name
        offset += entry_size

    return model_names
