"""Unit tests for PSX TIM decoder."""

import io
import os
import struct
import numpy as np
import pytest
from PIL import Image

from dcb_viewer.formats.tim import TimBpp, TimImage, parse_tim, parse_tim_list
from dcb_viewer.formats.archive import PakArchive, CHUNK_ID_TEXTURE


def test_synthetic_tim_4bit():
    """Tests decoding a synthesized 4-bit TIM with a 16-color CLUT."""
    # CLUT: 16 colors (1 palette) -> 12 bytes header + 32 bytes data = 44 bytes
    clut_colors = [
        0x0000, # Transparent
        0x001F, # Red (R=31, G=0, B=0)
        0x03E0, # Green (R=0, G=31, B=0)
        0x7C00, # Blue (R=0, G=0, B=31)
    ] + [0x7FFF] * 12 # 12 White colors
    
    clut_data = struct.pack(f"<{len(clut_colors)}H", *clut_colors)
    clut_header = struct.pack("<IHHHH", len(clut_data) + 12, 0, 0, 16, 1)
    clut_block = clut_header + clut_data

    # Pixels: 4 pixels wide (pix_w = 1), 2 rows high
    # Row 0: pixel 0=Red(1), pixel 1=Green(2), pixel 2=Blue(3), pixel 3=White(4)
    # Byte 0: (2 << 4) | 1 = 0x21
    # Byte 1: (4 << 4) | 3 = 0x43
    # Row 1: all Transparent (0) -> Byte 0: 0x00, Byte 1: 0x00
    row0 = bytes([0x21, 0x43])
    row1 = bytes([0x00, 0x00])
    pix_data = row0 + row1
    pix_header = struct.pack("<IHHHH", len(pix_data) + 12, 0, 0, 1, 2)
    pix_block = pix_header + pix_data

    tim_raw = struct.pack("<II", 0x10, 0x08) + clut_block + pix_block
    
    img, consumed = parse_tim(tim_raw)
    assert consumed == len(tim_raw)
    assert img.bpp == TimBpp.BPP_4
    assert img.has_clut is True
    assert img.pixel_width == 4
    assert img.pixel_height == 2
    assert img.palette_count == 1

    rgba = img.to_rgba_image(palette_idx=0)
    assert rgba.size == (4, 2)
    
    # Check pixels
    assert rgba.getpixel((0, 0)) == (255, 0, 0, 255)      # Red
    assert rgba.getpixel((1, 0)) == (0, 255, 0, 255)      # Green
    assert rgba.getpixel((2, 0)) == (0, 0, 255, 255)      # Blue
    assert rgba.getpixel((0, 1)) == (0, 0, 0, 0)          # Transparent


@pytest.mark.skipif(
    not os.path.exists("original_iso/extracted/F/003.PAK"),
    reason="Extracted 003.PAK not found",
)
def test_real_digimon_tim_chunk():
    """Tests decoding actual Digimon texture from 003.PAK."""
    pak = PakArchive.from_file("original_iso/extracted/F/003.PAK")
    tex_chunk = pak.find_chunk(CHUNK_ID_TEXTURE, 3)
    assert tex_chunk is not None

    img, consumed = parse_tim(tex_chunk.data)
    assert img.bpp == TimBpp.BPP_4
    assert img.has_clut is True
    assert img.pixel_width == 256
    assert img.pixel_height == 124
    assert img.palette_count == 3  # 3 CLUT banks

    # Verify Pillow conversion
    for p_idx in range(img.palette_count):
        pil_img = img.to_rgba_image(palette_idx=p_idx)
        assert pil_img.size == (256, 124)

    # Verify NumPy conversion
    arr = img.to_numpy(palette_idx=0)
    assert arr.shape == (124, 256, 4)
    assert arr.dtype == np.uint8
