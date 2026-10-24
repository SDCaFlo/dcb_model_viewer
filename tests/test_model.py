"""Unit tests for 3D model geometry parser."""

import os
import numpy as np
import pytest

from dcb_viewer.formats.archive import PakArchive, CHUNK_ID_MODEL
from dcb_viewer.formats.model import parse_model, DcbModel


@pytest.mark.skipif(
    not os.path.exists("original_iso/extracted/F/003.PAK"),
    reason="Extracted 003.PAK not found",
)
def test_parse_agumon_model():
    """Tests parsing Agumon (003.PAK) 3D model and skeletal rig."""
    pak = PakArchive.from_file("original_iso/extracted/F/003.PAK")
    model_chunk = pak.find_chunk(CHUNK_ID_MODEL, 3)
    assert model_chunk is not None

    model = parse_model(model_chunk.data, model_id=3)
    assert model.model_id == 3
    assert model.texture_name == "003.tim"
    assert model.bone_count == 16
    assert model.total_vertices == 390
    assert model.total_faces == 412  # 134 tris + 278 quads

    # Verify root bone
    root_bone = next(b for b in model.bones if b.is_root)
    assert root_bone.index == 3
    assert root_bone.parent_index == -1

    # Verify world mesh baking
    verts, norms, tris, uvs = model.get_baked_world_mesh()
    assert verts.ndim == 2 and verts.shape[1] == 3
    assert norms.ndim == 2 and norms.shape[1] == 3
    assert tris.ndim == 2 and tris.shape[1] == 3
    assert uvs.ndim == 3 and uvs.shape[1] == 3 and uvs.shape[2] == 2
    assert len(tris) > 0


@pytest.mark.skipif(
    not os.path.exists("original_iso/extracted/F/004.PAK"),
    reason="Extracted 004.PAK not found",
)
def test_parse_another_digimon_model():
    """Tests parsing another Digimon model (004.PAK) to verify format consistency."""
    pak = PakArchive.from_file("original_iso/extracted/F/004.PAK")
    model_chunk = pak.find_chunk(CHUNK_ID_MODEL, 4)
    assert model_chunk is not None

    model = parse_model(model_chunk.data, model_id=4)
    assert model.model_id == 4
    assert model.texture_name.endswith(".tim")
    assert model.bone_count > 0
    assert model.total_vertices > 0

    verts, norms, tris, uvs = model.get_baked_world_mesh()
    assert len(verts) > 0
    assert len(tris) > 0
