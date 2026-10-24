"""PlayStation TIM image format parser and decoder.

References:
- external_repository/dcb_decomp/src/main/psyq/libgpu_p33.c (OpenTIM, ReadTIM)
- external_repository/dcb_decomp/src/main/gfx/vram_upload.c (uploadTim, uploadTimList)
"""

from __future__ import annotations

import io
import struct
from dataclasses import dataclass, field
from enum import IntEnum
from pathlib import Path
from typing import BinaryIO

import numpy as np
from PIL import Image


class TimBpp(IntEnum):
    """PlayStation TIM pixel bits-per-pixel mode."""
    BPP_4 = 0   # 4-bit indexed (16-color CLUT)
    BPP_8 = 1   # 8-bit indexed (256-color CLUT)
    BPP_16 = 2  # 16-bit direct color (RGBA 1555)
    BPP_24 = 3  # 24-bit direct color (RGB 888)
    MIXED = 4


@dataclass
class TimImage:
    """Represents a single decoded PlayStation TIM image."""
    bpp: TimBpp
    has_clut: bool
    vram_x: int
    vram_y: int
    vram_w: int
    vram_h: int
    pixel_width: int
    pixel_height: int
    raw_pixels: bytes
    clut_x: int = 0
    clut_y: int = 0
    clut_w: int = 0
    clut_h: int = 0
    # List of palettes: each palette is a list of (R, G, B, A) tuples
    palettes: list[list[tuple[int, int, int, int]]] = field(default_factory=list)

    @property
    def palette_count(self) -> int:
        return len(self.palettes)

    def to_rgba_image(self, palette_idx: int = 0, transparent_color_zero: bool = True) -> Image.Image:
        """Decodes the TIM into a PIL RGBA Image using the specified CLUT palette.
        
        Args:
            palette_idx: Index of the CLUT palette bank to apply.
            transparent_color_zero: If True, index 0 with STP=0 is fully transparent.
        """
        img = Image.new("RGBA", (self.pixel_width, self.pixel_height))

        if self.bpp in (TimBpp.BPP_4, TimBpp.BPP_8):
            if not self.palettes:
                raise ValueError("Indexed TIM image has no CLUT palette available.")
            if palette_idx >= len(self.palettes):
                raise IndexError(
                    f"Palette index {palette_idx} out of range (image has {len(self.palettes)} palettes)"
                )
            pal = self.palettes[palette_idx]
            pixels = img.load()

            if self.bpp == TimBpp.BPP_4:
                idx = 0
                for y in range(self.pixel_height):
                    for x in range(0, self.pixel_width, 2):
                        byte = self.raw_pixels[idx]
                        idx += 1
                        c0 = byte & 0x0F
                        c1 = (byte >> 4) & 0x0F
                        pixels[x, y] = pal[c0]
                        if x + 1 < self.pixel_width:
                            pixels[x + 1, y] = pal[c1]

            elif self.bpp == TimBpp.BPP_8:
                idx = 0
                for y in range(self.pixel_height):
                    for x in range(self.pixel_width):
                        c = self.raw_pixels[idx]
                        idx += 1
                        pixels[x, y] = pal[c]

        elif self.bpp == TimBpp.BPP_16:
            pixels = img.load()
            idx = 0
            for y in range(self.pixel_height):
                for x in range(self.pixel_width):
                    val = struct.unpack_from("<H", self.raw_pixels, idx)[0]
                    idx += 2
                    r = (val & 0x1F) * 255 // 31
                    g = ((val >> 5) & 0x1F) * 255 // 31
                    b = ((val >> 10) & 0x1F) * 255 // 31
                    a = 0 if (val == 0 and transparent_color_zero) else 255
                    pixels[x, y] = (r, g, b, a)

        elif self.bpp == TimBpp.BPP_24:
            pixels = img.load()
            idx = 0
            for y in range(self.pixel_height):
                for x in range(self.pixel_width):
                    r = self.raw_pixels[idx]
                    g = self.raw_pixels[idx + 1]
                    b = self.raw_pixels[idx + 2]
                    idx += 3
                    pixels[x, y] = (r, g, b, 255)

        return img

    def to_numpy(self, palette_idx: int = 0) -> np.ndarray:
        """Returns the decoded image as a (H, W, 4) uint8 RGBA NumPy array."""
        pil_img = self.to_rgba_image(palette_idx=palette_idx)
        return np.array(pil_img, dtype=np.uint8)

    def save_png(self, output_path: str | Path, palette_idx: int = 0) -> None:
        """Saves decoded image to a PNG file."""
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        img = self.to_rgba_image(palette_idx=palette_idx)
        img.save(target, format="PNG")


def parse_tim(data: bytes, offset: int = 0) -> tuple[TimImage, int]:
    """Parses a single TIM image from a binary buffer starting at offset.
    
    Returns (TimImage, bytes_consumed).
    """
    if len(data) < offset + 8:
        raise ValueError("Buffer too small for TIM header")

    magic, mode = struct.unpack_from("<II", data, offset)
    if magic != 0x10:
        raise ValueError(f"Invalid TIM magic: 0x{magic:08x} (expected 0x00000010)")

    bpp_mode = TimBpp(mode & 7)
    has_clut = bool(mode & 8)

    cursor = offset + 8

    clut_x = clut_y = clut_w = clut_h = 0
    palettes: list[list[tuple[int, int, int, int]]] = []

    if has_clut:
        clut_size, clut_x, clut_y, clut_w, clut_h = struct.unpack_from("<IHHHH", data, cursor)
        clut_data_offset = cursor + 12

        for pal_idx in range(clut_h):
            pal: list[tuple[int, int, int, int]] = []
            for col_idx in range(clut_w):
                c = struct.unpack_from("<H", data, clut_data_offset + (pal_idx * clut_w + col_idx) * 2)[0]
                r = (c & 0x1F) * 255 // 31
                g = ((c >> 5) & 0x1F) * 255 // 31
                b = ((c >> 10) & 0x1F) * 255 // 31
                stp = (c >> 15) & 1
                if c == 0:
                    a = 0
                else:
                    a = 255
                pal.append((r, g, b, a))
            palettes.append(pal)

        cursor += clut_size

    pix_size, pix_x, pix_y, pix_w, pix_h = struct.unpack_from("<IHHHH", data, cursor)
    pix_data_offset = cursor + 12
    raw_pixels_len = pix_size - 12
    raw_pixels = data[pix_data_offset : pix_data_offset + raw_pixels_len]

    if bpp_mode == TimBpp.BPP_4:
        pixel_width = pix_w * 4
    elif bpp_mode == TimBpp.BPP_8:
        pixel_width = pix_w * 2
    elif bpp_mode == TimBpp.BPP_16:
        pixel_width = pix_w
    elif bpp_mode == TimBpp.BPP_24:
        pixel_width = (pix_w * 2) // 3
    else:
        pixel_width = pix_w

    pixel_height = pix_h

    tim_img = TimImage(
        bpp=bpp_mode,
        has_clut=has_clut,
        vram_x=pix_x,
        vram_y=pix_y,
        vram_w=pix_w,
        vram_h=pix_h,
        pixel_width=pixel_width,
        pixel_height=pixel_height,
        raw_pixels=raw_pixels,
        clut_x=clut_x,
        clut_y=clut_y,
        clut_w=clut_w,
        clut_h=clut_h,
        palettes=palettes,
    )

    bytes_consumed = (cursor + pix_size) - offset
    return tim_img, bytes_consumed


def parse_tim_list(data: bytes) -> list[TimImage]:
    """Parses a sequential list of TIM images from a single binary buffer.
    
    Matches `uploadTimList` in dcb_decomp.
    """
    images: list[TimImage] = []
    cursor = 0
    total_len = len(data)

    while cursor + 8 <= total_len:
        magic = struct.unpack_from("<I", data, cursor)[0]
        if magic != 0x10:
            break
        try:
            img, consumed = parse_tim(data, cursor)
            images.append(img)
            cursor += consumed
        except Exception:
            break

    return images
