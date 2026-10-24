"""Unit tests for glTF 2.0 / GLB exporter."""

import os
import pytest
import pygltflib

from dcb_viewer.formats.archive import (
    PakArchive,
    CHUNK_ID_MODEL,
    CHUNK_ID_TEXTURE,
    CHUNK_ID_ANIMATION,
    decompress_lz_huffman,
)
from dcb_viewer.formats.tim import parse_tim
from dcb_viewer.formats.model import parse_model
from dcb_viewer.formats.animation import parse_animation
from dcb_viewer.exporters.gltf import export_model_to_glb, GLTF_MAGIC


@pytest.mark.skipif(
    not os.path.exists("original_iso/extracted/F/003.PAK"),
    reason="Extracted 003.PAK not found",
)
def test_export_static_glb():
    """Tests exporting a static GLB model."""
    pak = PakArchive.from_file("original_iso/extracted/F/003.PAK")
    model = parse_model(pak.find_chunk(CHUNK_ID_MODEL, 3).data)
    tim, _ = parse_tim(pak.find_chunk(CHUNK_ID_TEXTURE, 3).data)

    glb_bytes = export_model_to_glb(model, tim, skinned=False)
    assert len(glb_bytes) > 10_000
    assert glb_bytes[:4] == b"glTF"

    # Validate with pygltflib
    gltf = pygltflib.GLTF2().load_from_bytes(glb_bytes)
    assert len(gltf.meshes) == 1
    # Multi-CLUT models create one material/texture per palette used
    assert len(gltf.materials) >= 1
    assert len(gltf.textures) >= 1
    assert len(gltf.images) >= 1
    assert len(gltf.skins) == 0


@pytest.mark.skipif(
    not os.path.exists("original_iso/extracted/F/003.PAK"),
    reason="Extracted 003.PAK not found",
)
def test_export_skinned_animated_glb():
    """Tests exporting a fully rigged, skinned, and animated GLB."""
    pak = PakArchive.from_file("original_iso/extracted/F/003.PAK")
    model = parse_model(pak.find_chunk(CHUNK_ID_MODEL, 3).data)
    tim, _ = parse_tim(pak.find_chunk(CHUNK_ID_TEXTURE, 3).data)

    animations = []
    for anim_id in range(8):
        chunk = pak.find_chunk(CHUNK_ID_ANIMATION, anim_id)
        if chunk:
            decomp = decompress_lz_huffman(chunk.data)
            clip = parse_animation(decomp, clip_id=anim_id, bone_count=model.bone_count)
            animations.append(clip)

    assert len(animations) == 8

    glb_bytes = export_model_to_glb(model, tim, animations=animations, skinned=True)
    assert len(glb_bytes) > 50_000
    assert glb_bytes[:4] == b"glTF"

    # Validate with pygltflib
    gltf = pygltflib.GLTF2().load_from_bytes(glb_bytes)
    assert len(gltf.meshes) == 1
    assert len(gltf.skins) == 1
    assert len(gltf.skins[0].joints) == 16
    assert len(gltf.animations) == 8
    anim_names = [a.name for a in gltf.animations]
    assert "Idle" in anim_names
    assert "Attack_1" in anim_names
    assert "Victory" in anim_names
