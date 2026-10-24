"""Archive parsers for Digimon Digital Card Battle (SLUS-01328).

Covers:
1. DRV Archives: Virtual disc container systems (A.DRV, B.DRV, etc.).
   Reference: external_repository/dcb_decomp/src/main/system/cd_file.c
2. PAK Archives: Chunked container files containing models, textures, animations.
   Reference: external_repository/dcb_decomp/src/main/system/archive.c
3. ARC Archives: Index-offset container archives.
   Reference: external_repository/dcb_decomp/src/main/system/decompress.c
4. LZSS + Huffman Decompressor:
   Reference: external_repository/dcb_decomp/src/main/system/decompress.c
"""

from __future__ import annotations

import io
import os
import struct
from dataclasses import dataclass
from pathlib import Path
from typing import BinaryIO, Iterator


# -----------------------------------------------------------------------------
# 1. DRV Archive Parser
# -----------------------------------------------------------------------------

SECTOR_SIZE = 2048  # Standard PSX CD-ROM sector size (2KB mode 2 / data sector)
FILE_ENTRY_SIZE = 32
DIR_MARKER = 0x80


@dataclass
class DrvEntry:
    """Represents an entry (file or directory) in a DRV archive."""
    name: str
    ext: str
    is_dir: bool
    sector: int
    size: int
    key: int
    unk_c: bytes
    relative_path: str = ""

    @property
    def full_name(self) -> str:
        if self.is_dir:
            return self.name
        return f"{self.name}.{self.ext}" if self.ext else self.name


class DrvArchive:
    """Reader for PSX .DRV virtual disc drive archives."""

    def __init__(self, file_path_or_buffer: str | Path | BinaryIO):
        if isinstance(file_path_or_buffer, (str, Path)):
            self._file: BinaryIO = open(file_path_or_buffer, "rb")
            self._should_close = True
            self.file_path = str(file_path_or_buffer)
        else:
            self._file = file_path_or_buffer
            self._should_close = False
            self.file_path = getattr(file_path_or_buffer, "name", "<buffer>")

        self.entries: list[DrvEntry] = []
        self._read_all_entries()

    def close(self) -> None:
        if self._should_close and self._file:
            self._file.close()

    def __enter__(self) -> DrvArchive:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()

    def _parse_directory_table(self, sector_offset: int, max_sectors: int = 16) -> list[DrvEntry]:
        """Parses directory entries from a table starting at sector_offset."""
        self._file.seek(sector_offset * SECTOR_SIZE)
        raw_data = self._file.read(max_sectors * SECTOR_SIZE)

        entries: list[DrvEntry] = []
        for offset in range(0, len(raw_data), FILE_ENTRY_SIZE):
            chunk = raw_data[offset : offset + FILE_ENTRY_SIZE]
            if len(chunk) < FILE_ENTRY_SIZE:
                break

            key, sector, size, unk_c = struct.unpack("<III4s", chunk[:16])
            if key == 0:
                # Terminator entry reached
                break

            raw_name = chunk[16:32].split(b"\x00")[0]
            name = raw_name.decode("ascii", errors="replace").strip()

            if key == DIR_MARKER:
                ext = ""
                is_dir = True
            else:
                is_dir = False
                ext_bytes = struct.pack("<I", key)[1:]
                ext = ext_bytes.rstrip(b"\x00").decode("ascii", errors="replace")

            entries.append(
                DrvEntry(
                    name=name,
                    ext=ext,
                    is_dir=is_dir,
                    sector=sector,
                    size=size,
                    key=key,
                    unk_c=unk_c,
                )
            )
        return entries

    def _read_all_entries(self) -> None:
        """Recursively scans and indexes all entries across the DRV archive."""
        root_entries = self._parse_directory_table(0)

        def scan_dir(entries: list[DrvEntry], current_prefix: str) -> None:
            for entry in entries:
                if entry.is_dir:
                    entry.relative_path = f"{current_prefix}{entry.name}"
                    self.entries.append(entry)
                    sub_entries = self._parse_directory_table(entry.sector)
                    scan_dir(sub_entries, f"{current_prefix}{entry.name}/")
                else:
                    entry.relative_path = f"{current_prefix}{entry.full_name}"
                    self.entries.append(entry)

        scan_dir(root_entries, "")

    def get_files(self) -> list[DrvEntry]:
        """Returns all non-directory file entries."""
        return [e for e in self.entries if not e.is_dir]

    def read_file_bytes(self, entry: DrvEntry) -> bytes:
        """Reads the exact binary content of a file entry."""
        if entry.is_dir:
            raise ValueError(f"Cannot read file bytes from directory entry: {entry.relative_path}")
        self._file.seek(entry.sector * SECTOR_SIZE)
        return self._file.read(entry.size)

    def extract_file(self, entry: DrvEntry, output_path: str | Path) -> None:
        """Extracts a single entry to disk."""
        target_path = Path(output_path)
        target_path.parent.mkdir(parents=True, exist_ok=True)
        content = self.read_file_bytes(entry)
        target_path.write_bytes(content)

    def extract_all(self, output_dir: str | Path) -> int:
        """Extracts all files preserving their directory structure."""
        out = Path(output_dir)
        count = 0
        for entry in self.get_files():
            dest = out / entry.relative_path
            self.extract_file(entry, dest)
            count += 1
        return count


# -----------------------------------------------------------------------------
# 2. PAK Archive Parser (Chunk Container)
# -----------------------------------------------------------------------------

CHUNK_HEADER_SIZE = 8

# Well-known chunk IDs from dcb_decomp
CHUNK_ID_MODEL = 0       # 3D Mesh & Skeletal hierarchy
CHUNK_ID_ANIMATION = 1   # Keyframe animation data
CHUNK_ID_SCRIPT_UI = 2   # Script / UI interaction
CHUNK_ID_SUB_SPRITE = 3  # Battle 2D sprites
CHUNK_ID_TEX_ANIM = 4    # Texture animation parameters
CHUNK_ID_TEXTURE = 5     # TIM texture data
CHUNK_ID_SOUND_VAB = 8   # Audio VAB data


@dataclass
class PakChunk:
    """Represents a chunk inside a .PAK package."""
    chunk_id: int
    sub_id: int
    size: int
    data: bytes

    @property
    def is_compressed(self) -> bool:
        """Heuristic check: if animation or mesh chunk, it may start with a 32-bit decompressed size."""
        if len(self.data) >= 4:
            # Check bitstream size header against chunk size
            expected_decomp_size = struct.unpack(">I", self.data[:4])[0]
            # If big-endian 32-bit unpacked is larger than compressed payload
            if 0 < expected_decomp_size < 10_000_000 and expected_decomp_size > self.size:
                return True
        return False


class PakArchive:
    """Reader for .PAK chunk archives containing 3D models, textures, animations."""

    def __init__(self, data: bytes):
        self.data = data
        self.chunks: list[PakChunk] = []
        self._parse()

    @classmethod
    def from_file(cls, file_path: str | Path) -> PakArchive:
        data = Path(file_path).read_bytes()
        return cls(data)

    def _parse(self) -> None:
        cursor = 0
        total_len = len(self.data)

        while cursor + CHUNK_HEADER_SIZE <= total_len:
            chunk_id, sub_id, size = struct.unpack_from("<hhi", self.data, cursor)
            if chunk_id < 0:
                # Negative chunk ID indicates EOF/terminator in dcb_decomp
                break

            cursor += CHUNK_HEADER_SIZE
            chunk_data = self.data[cursor : cursor + size]
            self.chunks.append(
                PakChunk(
                    chunk_id=chunk_id,
                    sub_id=sub_id,
                    size=size,
                    data=chunk_data,
                )
            )
            cursor += size

    def find_chunk(self, chunk_id: int, sub_id: int) -> PakChunk | None:
        """Finds a chunk by chunk_id and sub_id matching dcb_decomp findPakChunk."""
        for c in self.chunks:
            if c.chunk_id == chunk_id and c.sub_id == sub_id:
                return c
        return None

    def find_all_chunks(self, chunk_id: int) -> list[PakChunk]:
        """Returns all chunks matching a given chunk_id."""
        return [c for c in self.chunks if c.chunk_id == chunk_id]


# -----------------------------------------------------------------------------
# 3. LZSS + Huffman Decompressor
# -----------------------------------------------------------------------------

class BitstreamReader:
    """Bit-level reader matching dcb_decomp decompress.c bitstream."""

    def __init__(self, data: bytes):
        self.data = data
        self.pos = 0
        self.bit_buf = 0
        self.bits_left = 0

    def read_bit(self) -> int:
        if self.bits_left <= 0:
            if self.pos >= len(self.data):
                return 0
            self.bit_buf = self.data[self.pos]
            self.pos += 1
            self.bits_left = 8
        self.bits_left -= 1
        return (self.bit_buf >> self.bits_left) & 1

    def read_bits(self, count: int) -> int:
        val = 0
        while self.bits_left < count:
            count -= self.bits_left
            val |= (self.bit_buf & ((1 << self.bits_left) - 1)) << count
            if self.pos >= len(self.data):
                self.bit_buf = 0
            else:
                self.bit_buf = self.data[self.pos]
                self.pos += 1
            self.bits_left = 8

        self.bits_left -= count
        val |= (self.bit_buf >> self.bits_left) & ((1 << count) - 1)
        return val


def decompress_lz_huffman(data: bytes) -> bytes:
    """Decompresses an LZSS + Huffman compressed stream.
    
    Exact port of external_repository/dcb_decomp/src/main/system/decompress.c
    """
    if len(data) < 4:
        return b""

    stream = BitstreamReader(data)
    size_high = stream.read_bits(16)
    size_low = stream.read_bits(16)
    output_size = (size_high << 16) | size_low

    if output_size == 0 or output_size > 50_000_000:
        return b""

    huff_left = [0] * 0x220
    huff_right = [0] * 0x220
    next_node = 0

    def read_huffman_tree() -> int:
        nonlocal next_node
        if stream.read_bit() != 0:
            node = next_node
            next_node += 1
            if node >= 0x21F:
                return -1
            huff_left[node] = read_huffman_tree()
            huff_right[node] = read_huffman_tree()
            return node
        return stream.read_bits(9)

    lz_window = bytearray(0x1000)
    window_pos = 0xFEE
    out = bytearray()

    symbols_decoded = 0x1000
    root = 0

    while len(out) < output_size:
        if symbols_decoded == 0x1000:
            next_node = 0x110
            root = read_huffman_tree()
            symbols_decoded = 0

        symbol = root
        while symbol >= 0x110:
            if stream.read_bit() != 0:
                symbol = huff_right[symbol]
            else:
                symbol = huff_left[symbol]

        symbols_decoded += 1

        if symbol < 0x100:
            byte_val = symbol & 0xFF
            out.append(byte_val)
            lz_window[window_pos] = byte_val
            window_pos = (window_pos + 1) & 0xFFF
        else:
            length = symbol - 0xFD
            offset = stream.read_bits(12)
            for i in range(length):
                if len(out) >= output_size:
                    break
                byte_val = lz_window[(offset + i) & 0xFFF]
                out.append(byte_val)
                lz_window[window_pos] = byte_val
                window_pos = (window_pos + 1) & 0xFFF

    return bytes(out)
