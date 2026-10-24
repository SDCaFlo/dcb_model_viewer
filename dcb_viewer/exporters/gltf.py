"""glTF 2.0 / GLB Binary exporter for Digimon Digital Card Battle (SLUS-01328).

Supports:
- Static world mesh export
- Skinned skeletal mesh export with joint hierarchy and inverse bind matrices
- Skeletal animation tracks (translation, rotation, scale) with linear interpolation
- Embedded PSX TIM texture (converted to PNG) with retro NEAREST sampling
"""

from __future__ import annotations

import io
import json
import math
import struct
from pathlib import Path
from typing import Sequence

import numpy as np
from PIL import Image

from dcb_viewer.formats.animation import AnimationClip
from dcb_viewer.formats.model import DcbModel
from dcb_viewer.formats.tim import TimImage

# glTF Constants
GLTF_MAGIC = 0x46546C67
GLTF_VERSION = 2
CHUNK_TYPE_JSON = 0x4E4F534A
CHUNK_TYPE_BIN = 0x004E4942

# Component Types
COMP_BYTE = 5120
COMP_UNSIGNED_BYTE = 5121
COMP_SHORT = 5122
COMP_UNSIGNED_SHORT = 5123
COMP_UNSIGNED_INT = 5125
COMP_FLOAT = 5126

# BufferView Targets
TARGET_ARRAY_BUFFER = 34962          # VBO (vertices, normals, UVs, joints, weights)
TARGET_ELEMENT_ARRAY_BUFFER = 34963  # IBO (indices)

# Sampler Filters
FILTER_NEAREST = 9728
WRAP_REPEAT = 10497

# PSX to glTF unit scale (0.01 = 1 cm per PSX unit)
DEFAULT_SCALE = 0.01


class GlbBuilder:
    """Helper for assembling glTF 2.0 binary (.glb) files."""

    def __init__(self):
        self.bin_buffer = bytearray()
        self.buffer_views: list[dict] = []
        self.accessors: list[dict] = []
        self.images: list[dict] = []
        self.samplers: list[dict] = []
        self.textures: list[dict] = []
        self.materials: list[dict] = []
        self.meshes: list[dict] = []
        self.nodes: list[dict] = []
        self.skins: list[dict] = []
        self.animations: list[dict] = []

    def _pad_buffer(self, alignment: int = 4) -> None:
        pad = (alignment - (len(self.bin_buffer) % alignment)) % alignment
        if pad > 0:
            self.bin_buffer.extend(b"\x00" * pad)

    def add_buffer_view(self, data: bytes, target: int | None = None) -> int:
        """Appends data to binary buffer aligned to 4 bytes and returns bufferView index."""
        self._pad_buffer(4)
        offset = len(self.bin_buffer)
        self.bin_buffer.extend(data)

        bv_idx = len(self.buffer_views)
        bv_dict: dict = {
            "buffer": 0,
            "byteOffset": offset,
            "byteLength": len(data),
        }
        if target is not None:
            bv_dict["target"] = target

        self.buffer_views.append(bv_dict)
        return bv_idx

    def add_accessor(
        self,
        buffer_view_idx: int,
        component_type: int,
        count: int,
        type_str: str,
        min_val: list[float] | None = None,
        max_val: list[float] | None = None,
        byte_offset: int = 0,
    ) -> int:
        acc_idx = len(self.accessors)
        acc_dict: dict = {
            "bufferView": buffer_view_idx,
            "byteOffset": byte_offset,
            "componentType": component_type,
            "count": count,
            "type": type_str,
        }
        if min_val is not None:
            acc_dict["min"] = min_val
        if max_val is not None:
            acc_dict["max"] = max_val

        self.accessors.append(acc_dict)
        return acc_idx

    def add_texture_png(self, png_bytes: bytes) -> int:
        """Embeds a PNG texture image and returns texture index."""
        bv_idx = self.add_buffer_view(png_bytes)
        img_idx = len(self.images)
        self.images.append({
            "bufferView": bv_idx,
            "mimeType": "image/png",
        })

        sampler_idx = len(self.samplers)
        self.samplers.append({
            "magFilter": FILTER_NEAREST,
            "minFilter": FILTER_NEAREST,
            "wrapS": WRAP_REPEAT,
            "wrapT": WRAP_REPEAT,
        })

        tex_idx = len(self.textures)
        self.textures.append({
            "source": img_idx,
            "sampler": sampler_idx,
        })
        return tex_idx

    def add_material(
        self,
        texture_idx: int | None = None,
        name: str = "Material",
        alpha_mode: str = "MASK",
        alpha_cutoff: float = 0.1,
    ) -> int:
        mat_idx = len(self.materials)
        mat_dict: dict = {
            "name": name,
            "doubleSided": True,
            "alphaMode": alpha_mode,
            "alphaCutoff": alpha_cutoff,
            "pbrMetallicRoughness": {
                "metallicFactor": 0.0,
                "roughnessFactor": 0.8,
            },
        }
        if texture_idx is not None:
            mat_dict["pbrMetallicRoughness"]["baseColorTexture"] = {"index": texture_idx}

        self.materials.append(mat_dict)
        return mat_idx

    def build_glb(self) -> bytes:
        """Assembles and returns final binary GLB byte array."""
        self._pad_buffer(4)

        gltf_dict: dict = {
            "asset": {
                "version": "2.0",
                "generator": "DCB Model Viewer glTF Exporter",
            },
            "scene": 0,
            "scenes": [{"nodes": [0]}],
            "nodes": self.nodes,
            "meshes": self.meshes,
            "buffers": [{"byteLength": len(self.bin_buffer)}],
            "bufferViews": self.buffer_views,
            "accessors": self.accessors,
        }

        if self.materials:
            gltf_dict["materials"] = self.materials
        if self.textures:
            gltf_dict["textures"] = self.textures
        if self.images:
            gltf_dict["images"] = self.images
        if self.samplers:
            gltf_dict["samplers"] = self.samplers
        if self.skins:
            gltf_dict["skins"] = self.skins
        if self.animations:
            gltf_dict["animations"] = self.animations

        # Convert JSON to UTF-8
        json_bytes = json.dumps(gltf_dict, separators=(",", ":")).encode("utf-8")
        json_pad = (4 - (len(json_bytes) % 4)) % 4
        if json_pad > 0:
            json_bytes += b" " * json_pad

        bin_pad = (4 - (len(self.bin_buffer) % 4)) % 4
        if bin_pad > 0:
            self.bin_buffer.extend(b"\x00" * bin_pad)

        total_length = (
            12  # Header
            + 8 + len(json_bytes)  # JSON Chunk
            + 8 + len(self.bin_buffer)  # BIN Chunk
        )

        header = struct.pack("<III", GLTF_MAGIC, GLTF_VERSION, total_length)
        json_chunk_hdr = struct.pack("<II", len(json_bytes), CHUNK_TYPE_JSON)
        bin_chunk_hdr = struct.pack("<II", len(self.bin_buffer), CHUNK_TYPE_BIN)

        return header + json_chunk_hdr + json_bytes + bin_chunk_hdr + bytes(self.bin_buffer)


def export_model_to_glb(
    model: DcbModel,
    texture: TimImage | None = None,
    animations: Sequence[AnimationClip] = (),
    palette_idx: int = 0,
    scale: float = DEFAULT_SCALE,
    output_path: str | Path | None = None,
    skinned: bool = True,
) -> bytes:
    """Exports a DcbModel to a glTF 2.0 binary (.glb) file.
    
    Args:
        model: Parsed DcbModel with skeletal hierarchy.
        texture: Optional decoded PSX TIM image.
        animations: Optional sequence of parsed AnimationClip objects.
        palette_idx: Palette bank index to apply from TIM image.
        scale: Metric scaling multiplier (0.01 converts PSX units to meters).
        output_path: If specified, saves the GLB to this file path.
        skinned: If True, exports as a rigged skeletal mesh with joint nodes.
                 If False, bakes rest-pose vertices into a static mesh.
    """
    builder = GlbBuilder()

    # 2. Geometry Preparation
    # PSX to glTF: x' = x, y' = -y, z' = -z
    all_verts: list[np.ndarray] = []
    all_norms: list[np.ndarray] = []
    all_uvs: list[np.ndarray] = []
    all_indices: list[np.ndarray] = []
    all_joints: list[np.ndarray] = []
    all_weights: list[np.ndarray] = []
    all_cluts: list[np.ndarray] = []

    vert_offset = 0
    model.compute_rest_pose_transforms()

    for bone in model.bones:
        if not bone.mesh or bone.mesh.vertex_count == 0:
            continue

        local_verts = bone.mesh.vertices.copy()
        local_norms = bone.mesh.normals.copy()

        # glTF 2.0 Skinning Specification:
        # Vertex attributes (POSITION, NORMAL) in the buffer MUST be in bind-pose model space!
        # The skin inverseBindMatrices IBM(j) = inv(M_bind(j)) will transform bind-pose vertices
        # into bone-local space before animated joint matrices M_anim(j) transform them to animated model space.
        rot_m = bone.global_transform[:3, :3]
        t_v = bone.global_transform[:3, 3]
        v_world = (local_verts @ rot_m.T) + t_v
        n_world = local_norms @ rot_m.T

        # PSX coordinate inversion: x' = x, y' = -y, z' = -z
        gl_verts = v_world * [scale, -scale, -scale]
        gl_norms = n_world * [1.0, -1.0, -1.0]

        # Normalize normals
        norms_len = np.linalg.norm(gl_norms, axis=1, keepdims=True)
        norms_len[norms_len == 0] = 1.0
        gl_norms = (gl_norms / norms_len).astype(np.float32)

        tris, uvs, cluts = bone.mesh.get_triangulated_data()
        if len(tris) == 0:
            continue

        v_count = len(gl_verts)
        all_verts.append(gl_verts.astype(np.float32))
        all_norms.append(gl_norms)
        # Flatten UVs to (3 * num_tris, 2)
        all_uvs.append(uvs.reshape(-1, 2).astype(np.float32))
        all_cluts.append(cluts)

        # Triangles
        indices = (tris + vert_offset).flatten().astype(np.uint32)
        all_indices.append(indices)

        if skinned:
            # Rigid vertex skinning: 100% attached to this bone
            j_arr = np.zeros((v_count, 4), dtype=np.uint16)
            j_arr[:, 0] = bone.index
            w_arr = np.zeros((v_count, 4), dtype=np.float32)
            w_arr[:, 0] = 1.0

            all_joints.append(j_arr)
            all_weights.append(w_arr)

        vert_offset += v_count

    if not all_verts:
        raise ValueError("Model has no valid geometry to export")

    cat_verts = np.concatenate(all_verts, axis=0)
    cat_norms = np.concatenate(all_norms, axis=0)
    cat_uvs = np.concatenate(all_uvs, axis=0)
    cat_indices = np.concatenate(all_indices, axis=0)
    cat_cluts = np.concatenate(all_cluts, axis=0) if all_cluts else np.empty((0,), dtype=np.uint32)

    # Multi-CLUT / Palette Determination per Triangle
    tri_palette_indices: list[int] = []
    for clut in cat_cluts:
        if texture is not None and texture.palettes and clut != 0:
            p_idx = int(clut >> 6) - int(texture.clut_y)
            if p_idx < 0 or p_idx >= len(texture.palettes):
                p_idx = palette_idx
        else:
            p_idx = palette_idx if texture is not None else -1
        tri_palette_indices.append(p_idx)

    # 1. Texture & Material Setup (per unique palette used)
    pal_mat_map: dict[int, int] = {}
    if texture is not None:
        for p_idx in sorted(set(tri_palette_indices)):
            if p_idx >= 0:
                pil_img = texture.to_rgba_image(palette_idx=p_idx)
                # PSX model UVs are referenced against a 256x256 VRAM texture page.
                # TIM files on disc are cropped to only the rows/columns in use.
                # Placing the TIM pixels onto a 256x256 canvas ensures UVs match 1:1 without squashing.
                if pil_img.size != (256, 256):
                    canvas = Image.new("RGBA", (256, 256), (0, 0, 0, 0))
                    canvas.paste(pil_img, (0, 0))
                    pil_img = canvas

                png_io = io.BytesIO()
                pil_img.save(png_io, format="PNG")
                tex_idx = builder.add_texture_png(png_io.getvalue())
                mat_idx = builder.add_material(tex_idx, name=f"Mat_{model.texture_name}_pal{p_idx}")
                pal_mat_map[p_idx] = mat_idx
            else:
                mat_idx = builder.add_material(name="Mat_Default")
                pal_mat_map[p_idx] = mat_idx
    else:
        mat_idx = builder.add_material(name="Mat_Default")
        pal_mat_map[-1] = mat_idx

    # Note on UV indexing: Since faces were triangulated with per-vertex UVs,
    # we unroll vertices to match face indices so UVs align 1:1 with vertex attributes.
    unrolled_verts = cat_verts[cat_indices]
    unrolled_norms = cat_norms[cat_indices]
    unrolled_uvs = cat_uvs

    if skinned:
        cat_joints = np.concatenate(all_joints, axis=0)
        cat_weights = np.concatenate(all_weights, axis=0)
        unrolled_joints = cat_joints[cat_indices]
        unrolled_weights = cat_weights[cat_indices]

    # 3. Add Mesh Attributes to Buffer (Shared across all primitives)
    # Position
    pos_bytes = unrolled_verts.tobytes()
    pos_bv = builder.add_buffer_view(pos_bytes, target=TARGET_ARRAY_BUFFER)
    pos_min = unrolled_verts.min(axis=0).tolist()
    pos_max = unrolled_verts.max(axis=0).tolist()
    pos_acc = builder.add_accessor(pos_bv, COMP_FLOAT, len(unrolled_verts), "VEC3", pos_min, pos_max)

    # Normal
    norm_bytes = unrolled_norms.tobytes()
    norm_bv = builder.add_buffer_view(norm_bytes, target=TARGET_ARRAY_BUFFER)
    norm_acc = builder.add_accessor(norm_bv, COMP_FLOAT, len(unrolled_norms), "VEC3")

    # UV (TEXCOORD_0)
    uv_bytes = unrolled_uvs.tobytes()
    uv_bv = builder.add_buffer_view(uv_bytes, target=TARGET_ARRAY_BUFFER)
    uv_acc = builder.add_accessor(uv_bv, COMP_FLOAT, len(unrolled_uvs), "VEC2")

    attributes: dict[str, int] = {
        "POSITION": pos_acc,
        "NORMAL": norm_acc,
        "TEXCOORD_0": uv_acc,
    }

    if skinned:
        # Joints
        joint_bytes = unrolled_joints.tobytes()
        joint_bv = builder.add_buffer_view(joint_bytes, target=TARGET_ARRAY_BUFFER)
        joint_acc = builder.add_accessor(joint_bv, COMP_UNSIGNED_SHORT, len(unrolled_joints), "VEC4")

        # Weights
        weight_bytes = unrolled_weights.tobytes()
        weight_bv = builder.add_buffer_view(weight_bytes, target=TARGET_ARRAY_BUFFER)
        weight_acc = builder.add_accessor(weight_bv, COMP_FLOAT, len(unrolled_weights), "VEC4")

        attributes["JOINTS_0"] = joint_acc
        attributes["WEIGHTS_0"] = weight_acc

    # Primitive & Mesh: group triangles by palette index
    mesh_primitives: list[dict] = []
    for p_idx in sorted(set(tri_palette_indices)):
        tri_indices_for_pal: list[int] = []
        for t, p in enumerate(tri_palette_indices):
            if p == p_idx:
                tri_indices_for_pal.extend([3 * t, 3 * t + 1, 3 * t + 2])

        if not tri_indices_for_pal:
            continue

        pal_idx_arr = np.array(tri_indices_for_pal, dtype=np.uint32)
        idx_bytes = pal_idx_arr.tobytes()
        idx_bv = builder.add_buffer_view(idx_bytes, target=TARGET_ELEMENT_ARRAY_BUFFER)
        idx_acc = builder.add_accessor(idx_bv, COMP_UNSIGNED_INT, len(pal_idx_arr), "SCALAR")

        mesh_primitives.append({
            "attributes": attributes,
            "indices": idx_acc,
            "material": pal_mat_map[p_idx],
        })

    builder.meshes.append({
        "name": f"Mesh_{model.model_id}",
        "primitives": mesh_primitives,
    })

    # 4. Skeletal Nodes & Hierarchy
    if skinned:
        # Joint nodes start after Root Node (Node 0 is the character root)
        # Node 0: Root node (holds mesh and skin)
        # Nodes 1..N: Bone joints
        bone_node_offset = 1
        num_bones = model.bone_count

        # Build inverse bind matrices (glTF MAT4 requires column-major order)
        inv_bind_matrices = []
        for bone in model.bones:
            # Transform matrix to glTF space
            m = bone.global_transform.copy()
            # Position scale and inversion
            m[0, 3] *= scale
            m[1, 3] *= -scale
            m[2, 3] *= -scale
            try:
                inv_m = np.linalg.inv(m)
            except np.linalg.LinAlgError:
                inv_m = np.identity(4, dtype=np.float32)
            # Transpose to column-major order for glTF MAT4 accessor
            inv_bind_matrices.append(np.ascontiguousarray(inv_m.T, dtype=np.float32))

        inv_bind_arr = np.stack(inv_bind_matrices, axis=0)
        inv_bv = builder.add_buffer_view(inv_bind_arr.tobytes())
        inv_acc = builder.add_accessor(inv_bv, COMP_FLOAT, num_bones, "MAT4")

        # Create Skin
        joint_node_indices = list(range(bone_node_offset, bone_node_offset + num_bones))
        builder.skins.append({
            "name": f"Armature_{model.model_id}",
            "inverseBindMatrices": inv_acc,
            "joints": joint_node_indices,
        })

        # Find children for each bone
        bone_children: dict[int, list[int]] = {i: [] for i in range(num_bones)}
        root_bones: list[int] = []
        for bone in model.bones:
            if bone.is_root:
                root_bones.append(bone.index)
            else:
                bone_children[bone.parent_index].append(bone.index)

        # Node 0 (Root character node)
        root_children_nodes = [bone_idx + bone_node_offset for bone_idx in root_bones]
        builder.nodes.append({
            "name": f"Digimon_{model.model_id:03d}",
            "mesh": 0,
            "skin": 0,
            "children": root_children_nodes,
        })

        # Add Bone Nodes
        for bone in model.bones:
            # Local translation in glTF coordinates
            bx, by, bz = bone.local_position
            trans = [bx * scale, -by * scale, -bz * scale]
            node_dict: dict = {
                "name": f"Bone_{bone.index:02d}",
                "translation": trans,
                "rotation": [0.0, 0.0, 0.0, 1.0],
                "scale": [1.0, 1.0, 1.0],
            }
            ch = bone_children[bone.index]
            if ch:
                node_dict["children"] = [c_idx + bone_node_offset for c_idx in ch]
            builder.nodes.append(node_dict)

        # 5. Skeletal Animations
        anim_names = {
            0: "Idle",
            1: "Attack_1",
            2: "Attack_2",
            3: "Finisher",
            4: "Take_Damage",
            5: "Defeat",
            6: "Victory",
            7: "Guard",
        }

        for clip in animations:
            if clip.keyframe_count == 0:
                continue

            timestamps = np.array(clip.get_timestamps(), dtype=np.float32)
            time_bv = builder.add_buffer_view(timestamps.tobytes())
            time_acc = builder.add_accessor(
                time_bv,
                COMP_FLOAT,
                len(timestamps),
                "SCALAR",
                [float(timestamps.min())],
                [float(timestamps.max())],
            )

            channels = []
            samplers = []

            for bone_idx in range(num_bones):
                target_node = bone_idx + bone_node_offset
                bone = model.bones[bone_idx]
                bx, by, bz = bone.local_position

                # Translations (export if any frame animates translation)
                has_trans = any(
                    any(abs(v) > 1e-4 for v in kf.bone_transforms[bone_idx].trans)
                    for kf in clip.keyframes
                    if bone_idx < len(kf.bone_transforms)
                )

                if has_trans:
                    trans_list = []
                    for kf in clip.keyframes:
                        if bone_idx < len(kf.bone_transforms):
                            tx, ty, tz = kf.bone_transforms[bone_idx].trans
                            trans_list.append([
                                (bx + tx) * scale,
                                -(by + ty) * scale,
                                -(bz + tz) * scale,
                            ])
                        else:
                            trans_list.append([
                                bx * scale,
                                -by * scale,
                                -bz * scale,
                            ])

                    t_arr = np.array(trans_list, dtype=np.float32)
                    t_bv = builder.add_buffer_view(t_arr.tobytes())
                    t_min = t_arr.min(axis=0).tolist()
                    t_max = t_arr.max(axis=0).tolist()
                    t_acc = builder.add_accessor(t_bv, COMP_FLOAT, len(t_arr), "VEC3", t_min, t_max)

                    t_sampler_idx = len(samplers)
                    samplers.append({
                        "input": time_acc,
                        "output": t_acc,
                        "interpolation": "LINEAR",
                    })
                    channels.append({
                        "sampler": t_sampler_idx,
                        "target": {"node": target_node, "path": "translation"},
                    })

                # Rotations
                quats = []
                for kf in clip.keyframes:
                    if bone_idx < len(kf.bone_transforms):
                        q = kf.bone_transforms[bone_idx].to_quaternion_xyzw()
                        # Rotate to glTF orientation: qx' = qx, qy' = -qy, qz' = -qz, qw' = qw
                        quats.append([q[0], -q[1], -q[2], q[3]])
                    else:
                        quats.append([0.0, 0.0, 0.0, 1.0])

                q_arr = np.array(quats, dtype=np.float32)
                q_bv = builder.add_buffer_view(q_arr.tobytes())
                q_acc = builder.add_accessor(q_bv, COMP_FLOAT, len(q_arr), "VEC4")

                sampler_idx = len(samplers)
                samplers.append({
                    "input": time_acc,
                    "output": q_acc,
                    "interpolation": "LINEAR",
                })
                channels.append({
                    "sampler": sampler_idx,
                    "target": {"node": target_node, "path": "rotation"},
                })

            builder.animations.append({
                "name": anim_names.get(clip.clip_id, f"Animation_{clip.clip_id}"),
                "channels": channels,
                "samplers": samplers,
            })

    else:
        # Static mesh node
        builder.nodes.append({
            "name": f"Digimon_{model.model_id:03d}",
            "mesh": 0,
        })

    glb_bytes = builder.build_glb()

    if output_path is not None:
        target = Path(output_path)
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(glb_bytes)

    return glb_bytes
