"""Skeletal animation track parser for Digimon Digital Card Battle (SLUS-01328).

Parses Chunk 1 of .PAK packages:
- Decompressed via LZSS + Huffman (dcb_viewer.formats.archive.decompress_lz_huffman).
- Structure:
  - 4-byte header: frameCount (number of KeyFrame entries)
  - Array of KeyFrame structs (772 bytes each):
    - duration (s16, in frames halved -> duration * 2 frames)
    - sound (s16, sound effect ID)
    - bone[32] (KeyBone, 24 bytes each: rx, ry, rz, attr, tx, ty, tz, pad, sx, sy, sz, loopKey)

References:
- external_repository/dcb_decomp/include/dcb/model_anim.h (KeyBone, KeyFrame)
- external_repository/dcb_decomp/src/main/model/model_anim.c (loadNextAnimationKeyframe, applyAnimationFirstFrame)
- external_repository/dcb_decomp/src/main/model/anim_control.c (setModelAnimationData, loadModelAnimation)
"""

from __future__ import annotations

import math
import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

# PSX GTE Angle: 4096 units = 360 degrees = 2 * PI radians
ANGLE_TO_RAD = (2.0 * math.pi) / 4096.0
SCALE_DIVISOR = 4096.0  # 0x1000 = 1.0x scale
FPS = 30.0  # PSX standard simulation frame rate


@dataclass
class KeyBoneTransform:
    """Transformation key for a single bone at a given keyframe."""
    # PSX Euler angles in radians (order: YXZ)
    rot_rad: tuple[float, float, float]
    # Translation offset relative to rest-pose position
    trans: tuple[float, float, float]
    # Scale multiplier (1.0 = normal)
    scale: tuple[float, float, float]
    attribute: int = 0

    def to_quaternion_xyzw(self) -> tuple[float, float, float, float]:
        """Converts PSX YXZ Euler angles into a normalized glTF Quaternion (x, y, z, w)."""
        rx, ry, rz = self.rot_rad

        # Half angles
        cx = math.cos(rx * 0.5)
        sx = math.sin(rx * 0.5)
        cy = math.cos(ry * 0.5)
        sy = math.sin(ry * 0.5)
        cz = math.cos(rz * 0.5)
        sz = math.sin(rz * 0.5)

        # Quaternion multiplication order: Q = Qy * Qx * Qz
        # Qy = (0, sy, 0, cy)
        # Qx = (sx, 0, 0, cx)
        # Qz = (0, 0, sz, cz)
        qw = cy * cx * cz + sy * sx * sz
        qx = cy * sx * cz + sy * cx * sz
        qy = sy * cx * cz - cy * sx * sz
        qz = cy * cx * sz - sy * sx * cz

        # Normalize
        length = math.sqrt(qx * qx + qy * qy + qz * qz + qw * qw)
        if length > 0.0:
            return (qx / length, qy / length, qz / length, qw / length)
        return (0.0, 0.0, 0.0, 1.0)


@dataclass
class KeyFrame:
    """Single keyframe in an animation clip."""
    frame_index: int
    duration_frames: int
    duration_seconds: float
    sound_id: int
    bone_transforms: list[KeyBoneTransform] = field(default_factory=list)


@dataclass
class AnimationClip:
    """Full skeletal animation clip (e.g. Idle, Attack, Hurt, Victory)."""
    clip_id: int
    loop_key: int
    keyframes: list[KeyFrame] = field(default_factory=list)

    @property
    def keyframe_count(self) -> int:
        return len(self.keyframes)

    @property
    def total_frames(self) -> int:
        return sum(kf.duration_frames for kf in self.keyframes)

    @property
    def total_duration_seconds(self) -> float:
        return sum(kf.duration_seconds for kf in self.keyframes)

    def get_timestamps(self) -> list[float]:
        """Returns cumulative timestamps (in seconds) for each keyframe."""
        timestamps: list[float] = []
        accum = 0.0
        for kf in self.keyframes:
            timestamps.append(accum)
            accum += kf.duration_seconds
        return timestamps


def parse_animation(decompressed_data: bytes, clip_id: int = 0, bone_count: int = 32) -> AnimationClip:
    """Parses a decompressed Chunk 1 animation payload.
    
    Args:
        decompressed_data: Raw bytes decompressed by decompress_lz_huffman.
        clip_id: Animation slot index (0..7).
        bone_count: Number of active bones in the model (up to 32).
    """
    if len(decompressed_data) < 4:
        raise ValueError("Buffer too small for animation header")

    frame_count = struct.unpack_from("<I", decompressed_data, 0)[0]
    expected_size = 4 + frame_count * 772
    if len(decompressed_data) < expected_size:
        raise ValueError(
            f"Buffer size {len(decompressed_data)} smaller than expected {expected_size} for {frame_count} frames"
        )

    offset = 4
    loop_key = -1
    keyframes: list[KeyFrame] = []

    for f_idx in range(frame_count):
        raw_dur, raw_snd = struct.unpack_from("<hh", decompressed_data, offset)
        duration_frames = raw_dur * 2
        duration_seconds = duration_frames / FPS

        bone_offset = offset + 4
        transforms: list[KeyBoneTransform] = []

        # Read bones (32 bones stored per keyframe in DCB)
        for b_idx in range(min(bone_count, 32)):
            rx, ry, rz, attr, tx, ty, tz, _, sx, sy, sz, pad16 = struct.unpack_from(
                "<12h", decompressed_data, bone_offset + b_idx * 24
            )

            # In bone 0 of the first keyframe, pad16 stores the loopKey
            if f_idx == 0 and b_idx == 0:
                loop_key = pad16

            transforms.append(
                KeyBoneTransform(
                    rot_rad=(rx * ANGLE_TO_RAD, ry * ANGLE_TO_RAD, rz * ANGLE_TO_RAD),
                    trans=(float(tx), float(ty), float(tz)),
                    scale=(sx / SCALE_DIVISOR, sy / SCALE_DIVISOR, sz / SCALE_DIVISOR),
                    attribute=attr,
                )
            )

        keyframes.append(
            KeyFrame(
                frame_index=f_idx,
                duration_frames=duration_frames,
                duration_seconds=duration_seconds,
                sound_id=raw_snd,
                bone_transforms=transforms,
            )
        )
        offset += 772

    return AnimationClip(clip_id=clip_id, loop_key=loop_key, keyframes=keyframes)
