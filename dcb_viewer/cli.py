"""Command-Line Interface (CLI) for DCB Model Viewer."""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from dcb_viewer.formats.archive import (
    DrvArchive,
    PakArchive,
    decompress_lz_huffman,
    CHUNK_ID_MODEL,
    CHUNK_ID_ANIMATION,
    CHUNK_ID_TEXTURE,
)
from dcb_viewer.formats.tim import parse_tim, parse_tim_list


def cmd_inspect_drv(args: argparse.Namespace) -> None:
    """Inspects the contents of a DRV archive."""
    path = Path(args.drv_path)
    if not path.is_file():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    with DrvArchive(path) as drv:
        print(f"Archive: {path.name} ({len(drv.entries)} total entries)")
        print(f"{'Path':<35} {'Type':<8} {'Sector':<8} {'Size (Bytes)':<12}")
        print("-" * 68)
        for entry in drv.entries:
            t = "<DIR>" if entry.is_dir else entry.ext
            print(f"{entry.relative_path:<35} {t:<8} {entry.sector:<8} {entry.size:<12,}")


def cmd_unpack_drv(args: argparse.Namespace) -> None:
    """Unpacks a DRV file or all DRVs in a directory."""
    input_path = Path(args.input_path)
    output_dir = Path(args.output_dir)

    targets: list[Path] = []
    if input_path.is_file():
        targets.append(input_path)
    elif input_path.is_dir():
        # Case-insensitive deduplication for Windows
        found = {p.resolve(): p for p in input_path.glob("*.[dD][rR][vV]")}
        targets = sorted(found.values(), key=lambda p: p.name.upper())
        if not targets:
            print(f"No .DRV archives found in directory: {input_path}")
            sys.exit(1)
    else:
        print(f"Error: Path does not exist: {input_path}", file=sys.stderr)
        sys.exit(1)

    total_extracted = 0
    for drv_path in targets:
        print(f"Unpacking {drv_path.name}...")
        sub_out = output_dir / drv_path.stem if len(targets) > 1 else output_dir
        with DrvArchive(drv_path) as drv:
            count = drv.extract_all(sub_out)
            total_extracted += count
            print(f"  -> Extracted {count} files to {sub_out}")

    print(f"\nDone! Successfully unpacked {total_extracted} files across {len(targets)} archive(s).")


def cmd_inspect_pak(args: argparse.Namespace) -> None:
    """Inspects chunks inside a .PAK file."""
    path = Path(args.pak_path)
    if not path.is_file():
        print(f"Error: File not found: {path}", file=sys.stderr)
        sys.exit(1)

    pak = PakArchive.from_file(path)
    print(f"PAK Package: {path.name} ({len(pak.chunks)} chunks)")
    print(f"{'Index':<6} {'Chunk ID':<10} {'Sub ID':<8} {'Size':<10} {'Details'}")
    print("-" * 60)

    chunk_names = {
        CHUNK_ID_MODEL: "3D Model / Skeleton",
        CHUNK_ID_ANIMATION: "Animation Track",
        2: "Script / UI",
        3: "Battle Sprite",
        4: "Texture Anim",
        CHUNK_ID_TEXTURE: "TIM Texture",
        8: "VAB Sound",
    }

    for idx, c in enumerate(pak.chunks):
        type_str = chunk_names.get(c.chunk_id, f"Unknown ({c.chunk_id})")
        details = ""
        if c.chunk_id == CHUNK_ID_ANIMATION:
            decomp = decompress_lz_huffman(c.data)
            details = f"Decompresses to {len(decomp):,} bytes"
        elif c.chunk_id == CHUNK_ID_TEXTURE:
            if c.data[:4] == b"\x10\x00\x00\x00":
                details = "PSX TIM Image valid"
        elif c.chunk_id == CHUNK_ID_MODEL:
            # Model chunk has texture name prefix
            tex_name = c.data[:12].split(b"\x00")[0].decode("ascii", errors="replace")
            details = f"Model texture ref: {tex_name}"

        print(f"{idx:<6} {c.chunk_id:<10} {c.sub_id:<8} {c.size:<10,} {type_str} | {details}")


def cmd_extract_tim(args: argparse.Namespace) -> None:
    """Extracts and converts TIM textures (from .TIM or .PAK) to PNG."""
    input_path = Path(args.input_path)
    output_path = Path(args.output_path)

    if not input_path.is_file():
        print(f"Error: File not found: {input_path}", file=sys.stderr)
        sys.exit(1)

    raw_bytes = input_path.read_bytes()
    tim_data_list: list[bytes] = []

    if input_path.suffix.upper() == ".PAK":
        pak = PakArchive(raw_bytes)
        tex_chunks = pak.find_all_chunks(CHUNK_ID_TEXTURE)
        if not tex_chunks:
            print(f"No texture chunks (ID=5) found in {input_path.name}")
            sys.exit(1)
        for c in tex_chunks:
            tim_data_list.append(c.data)
    else:
        tim_data_list.append(raw_bytes)

    total_exported = 0
    for idx, data in enumerate(tim_data_list):
        images = parse_tim_list(data)
        for img_idx, img in enumerate(images):
            # Export all palette variations
            for pal_idx in range(img.palette_count):
                if output_path.suffix.lower() == ".png" and len(images) == 1 and img.palette_count == 1:
                    dest = output_path
                else:
                    stem = input_path.stem
                    suffix = f"_tex{img_idx}_pal{pal_idx}.png" if img.palette_count > 1 else f"_tex{img_idx}.png"
                    dest = output_path / f"{stem}{suffix}" if output_path.is_dir() else output_path.with_name(f"{output_path.stem}{suffix}")
                img.save_png(dest, palette_idx=pal_idx)
                print(f"Exported: {dest} ({img.pixel_width}x{img.pixel_height}, BPP: {img.bpp.name}, Palette: {pal_idx})")
                total_exported += 1

    print(f"\nDone! Successfully exported {total_exported} PNG texture(s).")


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="dcb-viewer",
        description="Digimon Digital Card Battle (PSX - SLUS-01328) Extraction & Viewer CLI",
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    # inspect-drv
    p_ins_drv = subparsers.add_parser("inspect-drv", help="Inspect directory table of a .DRV archive")
    p_ins_drv.add_argument("drv_path", help="Path to .DRV archive file")
    p_ins_drv.set_defaults(func=cmd_inspect_drv)

    # unpack-drv
    p_unp_drv = subparsers.add_parser("unpack-drv", help="Unpack files from .DRV archive(s)")
    p_unp_drv.add_argument("input_path", help="Path to .DRV file or directory containing .DRVs")
    p_unp_drv.add_argument("output_dir", help="Directory where extracted files will be written")
    p_unp_drv.set_defaults(func=cmd_unpack_drv)

    # inspect-pak
    p_ins_pak = subparsers.add_parser("inspect-pak", help="Inspect chunks inside a .PAK file")
    p_ins_pak.add_argument("pak_path", help="Path to .PAK file")
    p_ins_pak.set_defaults(func=cmd_inspect_pak)

    # extract-tim
    p_ext_tim = subparsers.add_parser("extract-tim", help="Extract and convert PSX TIM textures to PNG")
    p_ext_tim.add_argument("input_path", help="Path to .TIM or .PAK file")
    p_ext_tim.add_argument("output_path", help="Target output directory or .png path")
    p_ext_tim.set_defaults(func=cmd_extract_tim)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
