"""Unit tests for skeletal animation parser."""

import math
import os
import pytest

from dcb_viewer.formats.archive import PakArchive, decompress_lz_huffman, CHUNK_ID_ANIMATION
from dcb_viewer.formats.animation import parse_animation, AnimationClip


@pytest.mark.skipif(
    not os.path.exists("original_iso/extracted/F/003.PAK"),
    reason="Extracted 003.PAK not found",
)
def test_parse_agumon_idle_animation():
    """Tests parsing Agumon's Idle animation (003.PAK, anim 0)."""
    pak = PakArchive.from_file("original_iso/extracted/F/003.PAK")
    anim_chunk = pak.find_chunk(CHUNK_ID_ANIMATION, 0)
    assert anim_chunk is not None

    decomp = decompress_lz_huffman(anim_chunk.data)
    clip = parse_animation(decomp, clip_id=0, bone_count=16)

    assert clip.clip_id == 0
    assert clip.keyframe_count == 6
    assert clip.total_frames == 96
    # 96 frames at 60 Hz NTSC simulation rate = 1.60 seconds
    assert pytest.approx(clip.total_duration_seconds, 0.01) == 1.60
    assert clip.loop_key == -1

    # Verify quaternion math
    t0 = clip.keyframes[0].bone_transforms[0]
    qx, qy, qz, qw = t0.to_quaternion_xyzw()
    norm = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
    assert pytest.approx(norm, 0.001) == 1.0


@pytest.mark.skipif(
    not os.path.exists("original_iso/extracted/F/003.PAK"),
    reason="Extracted 003.PAK not found",
)
def test_parse_agumon_victory_animation_with_loop():
    """Tests parsing Agumon's Victory animation (anim 6) which loops to keyframe 1."""
    pak = PakArchive.from_file("original_iso/extracted/F/003.PAK")
    anim_chunk = pak.find_chunk(CHUNK_ID_ANIMATION, 6)
    assert anim_chunk is not None

    decomp = decompress_lz_huffman(anim_chunk.data)
    clip = parse_animation(decomp, clip_id=6, bone_count=16)

    assert clip.clip_id == 6
    assert clip.keyframe_count == 21
    assert clip.loop_key == 1  # Loops back to keyframe 1
    assert clip.total_frames == 336
