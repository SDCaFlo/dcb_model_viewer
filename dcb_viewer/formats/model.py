"""3D Model & Mesh Geometry parser for Digimon Digital Card Battle (SLUS-01328).

Parses Chunk 0 of .PAK packages (OMD format):
- OMD Header: TIM texture name, bone count, parent bone indices, rest-pose positions
- OMD0 Objects: Per-bone geometry, vertices (SVECTOR), normals, UVs, and polygon packets (triangles and quads).

References:
- external_repository/dcb_decomp/src/main/model/model_load.c (loadModel, readModelBonePositions, linkOmdObject)
- external_repository/dcb_decomp/src/main/model/scene3d.c (renderSceneModels)
- external_repository/dcb_decomp/src/main/gfx/tmd_sort.c (sortModelObject, transformAndLightVertices, sortModelPrimitives)
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path
from typing import Sequence

import numpy as np


@dataclass
class PolygonFace:
    """Represents a textured or untextured polygon face (triangle or quad)."""
    vertex_indices: tuple[int, ...]
    uvs: tuple[tuple[float, float], ...] = ()
    colors: tuple[tuple[int, int, int], ...] = ()
    is_quad: bool = False
    clut: int = 0


@dataclass
class BoneMesh:
    """3D geometry attached to a specific bone."""
    bone_index: int
    vertices: np.ndarray  # Shape (N, 3), float32 local bone-space coordinates
    normals: np.ndarray   # Shape (N, 3), float32 local normals
    faces: list[PolygonFace] = field(default_factory=list)

    @property
    def vertex_count(self) -> int:
        return len(self.vertices)

    @property
    def face_count(self) -> int:
        return len(self.faces)

    def get_triangulated_data(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Returns triangulated face indices (M, 3), UVs (M, 3, 2), and CLUT IDs (M,).
        
        Quads (v0, v1, v2, v3) are split into two triangles: (0, 1, 2) and (1, 3, 2).
        """
        tris: list[tuple[int, int, int]] = []
        uv_list: list[tuple[tuple[float, float], tuple[float, float], tuple[float, float]]] = []
        clut_list: list[int] = []

        for f in self.faces:
            if f.is_quad:
                # PSX quad triangulation: (0, 1, 2) and (1, 3, 2)
                # Matches PSX GPU POLY_FT4 / POLY_GT4 rasterizer winding order and normal consistency
                tris.append((f.vertex_indices[0], f.vertex_indices[1], f.vertex_indices[2]))
                if f.uvs and len(f.uvs) >= 4:
                    uv_list.append((f.uvs[0], f.uvs[1], f.uvs[2]))
                else:
                    uv_list.append(((0.0, 0.0), (0.0, 0.0), (0.0, 0.0)))
                clut_list.append(f.clut)

                # Triangle 2: (1, 3, 2)
                tris.append((f.vertex_indices[1], f.vertex_indices[3], f.vertex_indices[2]))
                if f.uvs and len(f.uvs) >= 4:
                    uv_list.append((f.uvs[1], f.uvs[3], f.uvs[2]))
                else:
                    uv_list.append(((0.0, 0.0), (0.0, 0.0), (0.0, 0.0)))
                clut_list.append(f.clut)
            else:
                tris.append((f.vertex_indices[0], f.vertex_indices[1], f.vertex_indices[2]))
                if f.uvs and len(f.uvs) >= 3:
                    uv_list.append((f.uvs[0], f.uvs[1], f.uvs[2]))
                else:
                    uv_list.append(((0.0, 0.0), (0.0, 0.0), (0.0, 0.0)))
                clut_list.append(f.clut)

        return (
            np.array(tris, dtype=np.uint32) if tris else np.empty((0, 3), dtype=np.uint32),
            np.array(uv_list, dtype=np.float32) if uv_list else np.empty((0, 3, 2), dtype=np.float32),
            np.array(clut_list, dtype=np.uint32) if clut_list else np.empty((0,), dtype=np.uint32),
        )

    def get_triangulated_indices_and_uvs(self) -> tuple[np.ndarray, np.ndarray]:
        """Returns triangulated face indices (M, 3) and corresponding UVs (M, 3, 2).
        
        Quads (v0, v1, v2, v3) are split into two triangles: (0, 1, 2) and (1, 3, 2).
        """
        tris, uvs, _ = self.get_triangulated_data()
        return tris, uvs


@dataclass
class BoneNode:
    """Represents a bone in the skeletal hierarchy."""
    index: int
    parent_index: int
    # Relative translation vector to parent joint in rest pose (PSX integer units)
    local_position: tuple[float, float, float]
    # Rest pose 4x4 matrix relative to parent joint
    local_transform: np.ndarray = field(default_factory=lambda: np.identity(4, dtype=np.float32))
    # Rest pose 4x4 matrix relative to model root
    global_transform: np.ndarray = field(default_factory=lambda: np.identity(4, dtype=np.float32))
    mesh: BoneMesh | None = None

    @property
    def is_root(self) -> bool:
        return self.parent_index < 0


@dataclass
class DcbModel:
    """Full 3D Digimon model containing skeleton and mesh attachments."""
    model_id: int
    texture_name: str
    bones: list[BoneNode] = field(default_factory=list)

    @property
    def bone_count(self) -> int:
        return len(self.bones)

    @property
    def total_vertices(self) -> int:
        return sum(b.mesh.vertex_count for b in self.bones if b.mesh)

    @property
    def total_faces(self) -> int:
        return sum(b.mesh.face_count for b in self.bones if b.mesh)

    def compute_rest_pose_transforms(self) -> None:
        """Computes local and global rest-pose matrices down the bone hierarchy."""
        for bone in self.bones:
            # Build local translation matrix
            local_m = np.identity(4, dtype=np.float32)
            local_m[0, 3] = bone.local_position[0]
            local_m[1, 3] = bone.local_position[1]
            local_m[2, 3] = bone.local_position[2]
            bone.local_transform = local_m

            if bone.is_root:
                bone.global_transform = local_m.copy()
            else:
                parent_bone = self.bones[bone.parent_index]
                bone.global_transform = parent_bone.global_transform @ local_m

    def get_baked_world_mesh(self) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Combines all bone meshes transformed into model rest-pose world coordinates.
        
        Returns:
            vertices: (V, 3) float32
            normals: (V, 3) float32
            triangles: (F, 3) uint32
            uvs: (F, 3, 2) float32
        """
        all_verts: list[np.ndarray] = []
        all_norms: list[np.ndarray] = []
        all_tris: list[np.ndarray] = []
        all_uvs: list[np.ndarray] = []
        vert_offset = 0

        self.compute_rest_pose_transforms()

        for bone in self.bones:
            if not bone.mesh or bone.mesh.vertex_count == 0:
                continue

            # Transform vertices by bone global matrix
            rot_trans = bone.global_transform[:3, :3]
            trans = bone.global_transform[:3, 3]

            v_world = (bone.mesh.vertices @ rot_trans.T) + trans
            n_world = bone.mesh.normals @ rot_trans.T
            # Re-normalize
            norms = np.linalg.norm(n_world, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            n_world /= norms

            tris, uvs = bone.mesh.get_triangulated_indices_and_uvs()
            if len(tris) > 0:
                all_verts.append(v_world)
                all_norms.append(n_world)
                all_tris.append(tris + vert_offset)
                all_uvs.append(uvs)
                vert_offset += len(v_world)

        if not all_verts:
            return (
                np.empty((0, 3), dtype=np.float32),
                np.empty((0, 3), dtype=np.float32),
                np.empty((0, 3), dtype=np.uint32),
                np.empty((0, 3, 2), dtype=np.float32),
            )

        return (
            np.concatenate(all_verts, axis=0),
            np.concatenate(all_norms, axis=0),
            np.concatenate(all_tris, axis=0),
            np.concatenate(all_uvs, axis=0),
        )


def parse_model(data: bytes, model_id: int = 0) -> DcbModel:
    """Parses a 3D model from Chunk 0 payload.
    
    Port of dcb_decomp loadModel / sortModelObject.
    """
    if len(data) < 20:
        raise ValueError("Buffer too small for OMD model header")

    # Byte 0..16: TIM filename (null-padded)
    raw_tex_name = data[:16].split(b"\x00")[0]
    tex_name = raw_tex_name.decode("ascii", errors="replace").strip()

    # Offset 16 (0x10): nobj (u16)
    nobj = struct.unpack_from("<H", data, 16)[0]

    # Offset 20 (0x14): parent bone indices (32 bytes signed)
    raw_parents = struct.unpack_from("<32b", data, 20)
    parents = list(raw_parents[:nobj])

    # Offset 52 (0x34): bone positions (nobj * 3 words = 12 bytes each)
    offset = 52
    bones: list[BoneNode] = []

    for i in range(nobj):
        # Bone positions are stored at data + 1 as (s16, s16, s16)
        vx, vy, vz = struct.unpack_from("<hhh", data, offset + 4)
        offset += 12
        bones.append(
            BoneNode(
                index=i,
                parent_index=parents[i],
                local_position=(float(vx), float(vy), float(vz)),
            )
        )

    # Now parse OMD0 blocks for each bone
    omd_offset = offset
    for b_idx in range(nobj):
        bone = bones[b_idx]
        actual_omd = data.find(b"OMD0", omd_offset)
        if actual_omd == -1:
            break

        omd_offset = actual_omd
        mesh = _parse_bone_omd0(data, omd_offset, b_idx)
        bone.mesh = mesh
        omd_offset += 4  # Advance past OMD0 tag for next search

    model = DcbModel(model_id=model_id, texture_name=tex_name, bones=bones)
    model.compute_rest_pose_transforms()
    return model


def _parse_bone_omd0(data: bytes, offset: int, bone_index: int) -> BoneMesh:
    """Parses an OMD0 mesh block for a single bone."""
    magic, flags, nobj_local = struct.unpack_from("<4sII", data, offset)
    if magic != b"OMD0":
        raise ValueError(f"Expected OMD0 at offset 0x{offset:x}, got {magic}")

    # Offset 32 in OMD0 block: unk14 points to primitive data relative to OMD0 start
    unk14 = struct.unpack_from("<I", data, offset + 32)[0]
    data_ptr = offset + unk14

    part_count = struct.unpack_from("<I", data, data_ptr)[0]
    data_ptr += 4

    all_verts: list[tuple[float, float, float]] = []
    all_norms: list[tuple[float, float, float]] = []
    all_faces: list[PolygonFace] = []

    for _ in range(part_count):
        vert_count = struct.unpack_from("<I", data, data_ptr)[0]
        data_ptr += 4

        # Read SVECTOR vertices: (s16 x, s16 y, s16 z, s16 pad)
        part_verts: list[tuple[float, float, float]] = []
        for _ in range(vert_count):
            vx, vy, vz, _ = struct.unpack_from("<hhhh", data, data_ptr)
            part_verts.append((float(vx), float(vy), float(vz)))
            data_ptr += 8

        vert_base_idx = len(all_verts)
        all_verts.extend(part_verts)

        # Read normal groups
        groups = struct.unpack_from("<I", data, data_ptr)[0]
        data_ptr += 4
        part_norms: list[tuple[float, float, float]] = []

        for _ in range(groups):
            word = struct.unpack_from("<I", data, data_ptr)[0]
            count = word & 0xFF
            data_ptr += 4
            if count != 0:
                for _ in range(count):
                    nx, ny, nz, _ = struct.unpack_from("<hhhh", data, data_ptr)
                    part_norms.append((float(nx) / 4096.0, float(ny) / 4096.0, float(nz) / 4096.0))
                    data_ptr += 8

        if not part_norms:
            part_norms = [(0.0, 1.0, 0.0)] * vert_count
        elif len(part_norms) < vert_count:
            # Pad with default/last normal so vert count matches normal count 1:1
            fallback = part_norms[-1] if part_norms else (0.0, 1.0, 0.0)
            part_norms.extend([fallback] * (vert_count - len(part_norms)))
        elif len(part_norms) > vert_count:
            part_norms = part_norms[:vert_count]
        all_norms.extend(part_norms)

        # Read primitive packets (sortModelPrimitives from tmd_sort.c)
        while True:
            header = struct.unpack_from("<I", data, data_ptr)[0]
            data_ptr += 4
            if header == 0:
                break

            count0 = header >> 20
            count1 = (header >> 8) & 0xFFF
            code = (header << 24) & 0xFFFFFFFF
            is_quad = bool(code & 0x08000000)
            textured = bool(code & 0x04000000)

            for pass_idx in range(2):
                run_cnt = count0 if pass_idx == 0 else count1
                for _ in range(run_cnt):
                    run_w = struct.unpack_from("<I", data, data_ptr)[0]
                    data_ptr += 4
                    strip_cnt = run_w & 0xFFFF
                    strip_len = run_w >> 16

                    for _ in range(strip_cnt):
                        if textured and is_quad:
                            w0, w1, w2, w3 = struct.unpack_from("<4I", data, data_ptr)
                            u0, u1, u2, u3 = struct.unpack_from("<4I", data, data_ptr + 16)
                            data_ptr += 32
                            clut = u0 >> 16

                            v0 = ((w0 >> 16) // 8) + vert_base_idx
                            v1 = ((w1 >> 16) // 8) + vert_base_idx
                            v2 = ((w2 >> 16) // 8) + vert_base_idx
                            v3 = ((w3 >> 16) // 8) + vert_base_idx

                            uv0 = ((u0 & 0xFF) / 256.0, ((u0 >> 8) & 0xFF) / 256.0)
                            uv1 = ((u1 & 0xFF) / 256.0, ((u1 >> 8) & 0xFF) / 256.0)
                            uv2 = ((u2 & 0xFF) / 256.0, ((u2 >> 8) & 0xFF) / 256.0)
                            uv3 = ((u3 & 0xFF) / 256.0, ((u3 >> 8) & 0xFF) / 256.0)

                            all_faces.append(
                                PolygonFace(
                                    vertex_indices=(v0, v1, v2, v3),
                                    uvs=(uv0, uv1, uv2, uv3),
                                    is_quad=True,
                                    clut=clut,
                                )
                            )

                            for k in range(1, strip_len):
                                wa, wb, ua, ub = struct.unpack_from("<4I", data, data_ptr)
                                data_ptr += 16
                                va = ((wa >> 16) // 8) + vert_base_idx
                                vb = ((wb >> 16) // 8) + vert_base_idx
                                uva = ((ua & 0xFF) / 256.0, ((ua >> 8) & 0xFF) / 256.0)
                                uvb = ((ub & 0xFF) / 256.0, ((ub >> 8) & 0xFF) / 256.0)

                                if pass_idx != 0:
                                    # Strip: alternating edge replacement
                                    if k % 2 == 1:
                                        v2, v3 = va, vb
                                        uv2, uv3 = uva, uvb
                                    else:
                                        v0, v1 = va, vb
                                        uv0, uv1 = uva, uvb
                                        if (ua >> 16) != 0:
                                            clut = ua >> 16
                                else:
                                    # Fan: V0 anchor stays, V1/V2 alternate with V3
                                    if k % 2 == 1:
                                        v2, v3 = va, vb
                                        uv2, uv3 = uva, uvb
                                    else:
                                        v1, v3 = va, vb
                                        uv1, uv3 = uva, uvb

                                all_faces.append(
                                    PolygonFace(
                                        vertex_indices=(v0, v1, v2, v3),
                                        uvs=(uv0, uv1, uv2, uv3),
                                        is_quad=True,
                                        clut=clut,
                                    )
                                )

                        elif textured and not is_quad:
                            w0, w1, w2 = struct.unpack_from("<3I", data, data_ptr)
                            u0, u1, u2 = struct.unpack_from("<3I", data, data_ptr + 12)
                            data_ptr += 24
                            clut = u0 >> 16

                            v0 = ((w0 >> 16) // 8) + vert_base_idx
                            v1 = ((w1 >> 16) // 8) + vert_base_idx
                            v2 = ((w2 >> 16) // 8) + vert_base_idx

                            uv0 = ((u0 & 0xFF) / 256.0, ((u0 >> 8) & 0xFF) / 256.0)
                            uv1 = ((u1 & 0xFF) / 256.0, ((u1 >> 8) & 0xFF) / 256.0)
                            uv2 = ((u2 & 0xFF) / 256.0, ((u2 >> 8) & 0xFF) / 256.0)

                            all_faces.append(
                                PolygonFace(
                                    vertex_indices=(v0, v1, v2),
                                    uvs=(uv0, uv1, uv2),
                                    is_quad=False,
                                    clut=clut,
                                )
                            )

                            for k in range(1, strip_len):
                                wa, ua = struct.unpack_from("<2I", data, data_ptr)
                                data_ptr += 8
                                va = ((wa >> 16) // 8) + vert_base_idx
                                uva = ((ua & 0xFF) / 256.0, ((ua >> 8) & 0xFF) / 256.0)

                                if k % 2 == 1:
                                    v2 = va
                                    uv2 = uva
                                else:
                                    if pass_idx != 0:
                                        v0 = va
                                        uv0 = uva
                                        if (ua >> 16) != 0:
                                            clut = ua >> 16
                                    else:
                                        v1 = va
                                        uv1 = uva

                                all_faces.append(
                                    PolygonFace(
                                        vertex_indices=(v0, v1, v2),
                                        uvs=(uv0, uv1, uv2),
                                        is_quad=False,
                                        clut=clut,
                                    )
                                )

                        elif not textured and is_quad:
                            w0, w1, w2, w3 = struct.unpack_from("<4I", data, data_ptr)
                            data_ptr += 16

                            v0 = ((w0 >> 16) // 8) + vert_base_idx
                            v1 = ((w1 >> 16) // 8) + vert_base_idx
                            v2 = ((w2 >> 16) // 8) + vert_base_idx
                            v3 = ((w3 >> 16) // 8) + vert_base_idx

                            all_faces.append(PolygonFace(vertex_indices=(v0, v1, v2, v3), is_quad=True, clut=0))

                            for k in range(1, strip_len):
                                wa, wb = struct.unpack_from("<2I", data, data_ptr)
                                data_ptr += 8
                                va = ((wa >> 16) // 8) + vert_base_idx
                                vb = ((wb >> 16) // 8) + vert_base_idx

                                if pass_idx != 0:
                                    if k % 2 == 1:
                                        v2, v3 = va, vb
                                    else:
                                        v0, v1 = va, vb
                                else:
                                    if k % 2 == 1:
                                        v2, v3 = va, vb
                                    else:
                                        v1, v3 = va, vb

                                all_faces.append(PolygonFace(vertex_indices=(v0, v1, v2, v3), is_quad=True, clut=0))

                        else:
                            w0, w1, w2 = struct.unpack_from("<3I", data, data_ptr)
                            data_ptr += 12

                            v0 = ((w0 >> 16) // 8) + vert_base_idx
                            v1 = ((w1 >> 16) // 8) + vert_base_idx
                            v2 = ((w2 >> 16) // 8) + vert_base_idx

                            all_faces.append(PolygonFace(vertex_indices=(v0, v1, v2), is_quad=False, clut=0))

                            for k in range(1, strip_len):
                                wa = struct.unpack_from("<I", data, data_ptr)[0]
                                data_ptr += 4
                                va = ((wa >> 16) // 8) + vert_base_idx

                                if k % 2 == 1:
                                    v2 = va
                                else:
                                    if pass_idx != 0:
                                        v0 = va
                                    else:
                                        v1 = va

                                all_faces.append(PolygonFace(vertex_indices=(v0, v1, v2), is_quad=False, clut=0))

    v_arr = np.array(all_verts, dtype=np.float32) if all_verts else np.empty((0, 3), dtype=np.float32)
    n_arr = np.array(all_norms, dtype=np.float32) if all_norms else np.empty((0, 3), dtype=np.float32)
    return BoneMesh(bone_index=bone_index, vertices=v_arr, normals=n_arr, faces=all_faces)
