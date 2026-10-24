"""Unit tests for dcb_viewer.formats.archive."""

import io
import os
import struct
import pytest
from pathlib import Path

from dcb_viewer.formats.archive import (
    DrvArchive,
    DrvEntry,
    PakArchive,
    PakChunk,
    decompress_lz_huffman,
    CHUNK_ID_MODEL,
    CHUNK_ID_ANIMATION,
    CHUNK_ID_TEXTURE,
)


def test_drv_synthetic_roundtrip():
    """Tests parsing a synthesized DRV binary buffer."""
    buf = io.BytesIO()
    
    # Sector 0: Root directory table
    # Entry 0: file "TEST.BIN" -> key=(ord('B') | ord('I')<<8 | ord('N')<<16)<<8 | 1
    ext_bin = b"BIN"
    ext_key = ext_bin[0] | (ext_bin[1] << 8) | (ext_bin[2] << 16)
    key_file = (ext_key << 8) | 1
    sector_file = 1
    size_file = 100
    unk_c = b"\x00\x00\x00\x00"
    name_file = b"TEST\x00" + b"\x00" * 11
    
    entry0 = struct.pack("<III4s16s", key_file, sector_file, size_file, unk_c, name_file)
    terminator = b"\x00" * 32
    
    sector0 = entry0 + terminator + b"\x00" * (2048 - 64)
    buf.write(sector0)
    
    # Sector 1: Payload for TEST.BIN (100 bytes of 'A')
    sector1 = b"A" * size_file + b"\x00" * (2048 - size_file)
    buf.write(sector1)
    
    buf.seek(0)
    archive = DrvArchive(buf)
    
    files = archive.get_files()
    assert len(files) == 1
    assert files[0].name == "TEST"
    assert files[0].ext == "BIN"
    assert files[0].full_name == "TEST.BIN"
    assert files[0].size == 100
    assert archive.read_file_bytes(files[0]) == b"A" * 100


def test_pak_chunk_parsing():
    """Tests parsing a synthesized .PAK chunk stream."""
    buf = io.BytesIO()
    
    # Chunk 0: Model (id=0, sub=1, size=4)
    buf.write(struct.pack("<hhi", 0, 1, 4))
    buf.write(b"MDL1")
    
    # Chunk 1: Texture (id=5, sub=1, size=4)
    buf.write(struct.pack("<hhi", 5, 1, 4))
    buf.write(b"TEX1")
    
    # EOF marker: negative id
    buf.write(struct.pack("<hhi", -1, 0, 0))
    
    pak = PakArchive(buf.getvalue())
    assert len(pak.chunks) == 2
    assert pak.find_chunk(0, 1) is not None
    assert pak.find_chunk(0, 1).data == b"MDL1"
    assert pak.find_chunk(5, 1).data == b"TEX1"
    assert pak.find_chunk(1, 0) is None


@pytest.mark.skipif(
    not os.path.exists("original_iso/dump/F.DRV"),
    reason="Original game dump not found in original_iso/dump/",
)
def test_f_drv_digimon_pak():
    """Integration test against actual extracted game data."""
    with DrvArchive("original_iso/dump/F.DRV") as drv:
        files = drv.get_files()
        assert len(files) >= 200
        
        # Test 003.PAK
        pak_entry = next((f for f in files if f.full_name == "003.PAK"), None)
        assert pak_entry is not None
        
        pak_data = drv.read_file_bytes(pak_entry)
        pak = PakArchive(pak_data)
        
        # Check model chunk
        model_chunk = pak.find_chunk(CHUNK_ID_MODEL, 3)
        assert model_chunk is not None
        assert model_chunk.size > 0
        
        # Check texture chunk
        tex_chunk = pak.find_chunk(CHUNK_ID_TEXTURE, 3)
        assert tex_chunk is not None
        # PSX TIM magic: 0x10
        assert tex_chunk.data[:4] == b"\x10\x00\x00\x00"
        
        # Check animation decompression
        anim_chunk = pak.find_chunk(CHUNK_ID_ANIMATION, 0)
        assert anim_chunk is not None
        decompressed_anim = decompress_lz_huffman(anim_chunk.data)
        assert len(decompressed_anim) > len(anim_chunk.data)
