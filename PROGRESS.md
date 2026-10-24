# Project Progress & Backlog: DCB Model Viewer

This document tracks the active progress, roadmap milestones, completed tasks, and upcoming backlog for the **Digimon Digital Card Battle (PSX - SLUS-01328) Model & Animation Viewer/Exporter**.

---

## 📌 Current Status Summary
* **Active Phase**: Completed (Phase 1: Pipeline & glTF Export + Phase 2: Interactive Web 3D Viewer)
* **Current Focus**: Polish, Additional Stages / Arenas, and User Enhancements
* **Status**: 🟢 All Milestones Achieved (Full Extraction, 267 Digimon GLB Models, 8 Animation Tracks, and Web 3D Viewer Live)

---

## 🗺️ Milestone Roadmap

### Phase 1: Model & Animation Extraction (Data Pipeline)

| Task ID | Item | Status | Notes |
| :--- | :--- | :---: | :--- |
| **P1-01** | Python Environment Setup (pyenv + poetry + Python 3.13) | 🟢 Done | Poetry 2.4.1 + Python 3.13.13 in .venv with numpy, pillow, pygltflib, construct |
| **P1-02** | External Repositories Setup (`dcb_decomp`, `mkpsxiso`) | 🟢 Done | Cloned into `external_repository/` (ignored in git) |
| **P1-03** | Project Standards & Guidelines (`AGENTS.md`, `PROGRESS.md`) | 🟢 Done | Operational guides and backlog established |
| **P1-04** | Disc Structure & Archive Analysis | 🟢 Done | Extracted disc via `dumpsxiso`. Identified `.DRV` virtual drive archives (`cd_file.c` struct `FileEntry`) |
| **P1-05** | Decompilation Research (`dcb_decomp`) | 🟢 Done | Reverse-engineered `.DRV` format, `.PAK` chunk structure (`archive.c`), and LZSS+Huffman decompression (`decompress.c`) |
| **P1-06** | Archive Unpacker & Decompressor | 🟢 Done | Implemented `DrvArchive`, `PakArchive`, and `decompress_lz_huffman` in `dcb_viewer/formats/archive.py` and CLI tools |
| **P1-07** | PSX TIM Texture Decoder | 🟢 Done | Implemented `TimImage`, `parse_tim`, `parse_tim_list` in `dcb_viewer/formats/tim.py` with multi-CLUT and PIL/NumPy support |
| **P1-08** | 3D Mesh Geometry Parser | 🟢 Done | Implemented OMD / OMD0 mesh parser in `dcb_viewer/formats/model.py` (SVECTOR vertices, normals, quads/tris, UVs) |
| **P1-09** | Bone Hierarchy & Skeleton Parser | 🟢 Done | Implemented `BoneNode`, parent hierarchy, and local/global rest-pose matrix transformations |
| **P1-10** | Skeletal Animation Parser | 🟢 Done | Implemented `parse_animation` in `dcb_viewer/formats/animation.py` (KeyFrame duration, YXZ Euler to Quaternions, 8 animation slots) |
| **P1-11** | glTF 2.0 / GLB Exporter | 🟢 Done | Implemented binary `.glb` builder in `dcb_viewer/exporters/gltf.py` with embedded PNG textures, bone skinning, and anim tracks |

---

### Phase 2: 3D Visualization (Interactive Tool)

| Task ID | Item | Status | Notes |
| :--- | :--- | :---: | :--- |
| **P2-01** | 3D Viewport Architecture | 🟢 Done | Three.js WebGL viewport with OrbitControls, studio lighting, grid, wireframe, and bone helpers |
| **P2-02** | Shading & Material Pipeline | 🟢 Done | glTF 2.0 PBR material with authentic PSX NEAREST texture filtering |
| **P2-03** | Animation Player UI | 🟢 Done | Timeline scrubber, play/pause, playback speed chips (0.25x - 2x), and clip switcher |
| **P2-04** | Asset Browser & Inspector | 🟢 Done | Digimon card database (`CARD2.CDD`) name resolution, search filter, and mesh stats |
| **P2-05** | Standalone Web Application | 🟢 Done | Multi-threaded Python server (`dcb_viewer/web/server.py`) launched via `dcb-viewer serve` |

---

## 📋 Backlog & Future Considerations

* [ ] **Arena / Battle Stage Exporter**: Digimon Card Battle features 3D battle arenas; parse stage geometry and background textures.
* [ ] **Audio / SFX / Voice extraction**: Low-priority bonus (PSX VAB/SPU sound files).
* [ ] **Batch Conversion CLI**: Command-line tool to dump the entire game disc into modern glTF models in one command (`dcb-viewer extract-all --iso ...`).
* [ ] **Blender Addon Integration**: Evaluate creating a direct Blender import script if custom format features warrant it.

---

## 📝 Activity Log

* **2026-10-24**:
  * Project initialized with Python 3.13, Poetry, `AGENTS.md`, and `PROGRESS.md`.
  * Cloned reference repositories `dcb_decomp` and `mkpsxiso` into `external_repository/`.
  * Built `mkpsxiso` and `dumpsxiso` binaries using CMake and MinGW GCC/Ninja.
  * Extracted game disc (`Digimon Digital Card Battle.bin`) into `original_iso/dump/`.
  * Analyzed disc layout: Found `.DRV` virtual drive containers (`A.DRV`, `B.DRV`, `C.DRV`, `E.DRV`, `F.DRV`, `G.DRV`, `P.DRV`) and `MMM.DAT`.
  * Reverse-engineered the `.DRV` container format from `external_repository/dcb_decomp/src/main/system/cd_file.c`:
    * Each container has a table of 32-byte `FileEntry` records (`key`, `sector`, `size`, `unkC`, `name`).
    * Offsets are sector-based (`sector * 2048`).
    * Keys encode file extension or directory marker (`0x80`).
  * Reverse-engineered `.PAK` chunk structure from `external_repository/dcb_decomp/src/main/system/archive.c` and `include/game.h`:
    * 8-byte chunk headers (`id`, `sub`, `size`).
    * `id == 0`: 3D model geometry and skeleton.
    * `id == 1`: Keyframe animation tracks (0 to 7).
    * `id == 5`: Standard PSX TIM texture.
  * Reverse-engineered compression from `external_repository/dcb_decomp/src/main/system/decompress.c`:
    * Ported `decompressLzHuffman` (LZSS 4KB ring buffer + dynamic Huffman tree) to pure Python.
  * Created `dcb_viewer/formats/archive.py` (`DrvArchive`, `PakArchive`, `decompress_lz_huffman`) and `dcb_viewer/cli.py`.
  * Verified unit & integration tests (`tests/test_archive.py`) passing 100%.
  * Unpacked all 2,401 files across all `.DRV` disc archives to `original_iso/extracted/`.
  * Implemented PSX TIM texture decoder in `dcb_viewer/formats/tim.py` with multi-palette CLUT support, export to PNG via Pillow, and NumPy arrays.
  * Reverse-engineered OMD 3D model format from `model_load.c`, `scene3d.c`, and `tmd_sort.c`:
    * Parsed bone hierarchy (`parent` indices), rest-pose joint vectors.
    * Parsed `OMD0` blocks: `partCount`, `vertCount`, SVECTOR coordinates, normal groups, and `sortModelPrimitives` polygon packets (quads & triangles with UV mapping).
    * Implemented world rest-pose baking with forward hierarchical matrix multiplication.
  * Verified all 7 unit & integration tests passing (`pytest` 7/7).
  * Reverse-engineered Chunk 1 skeletal keyframe animations from `include/dcb/model_anim.h` and `src/main/model/model_anim.c`:
    * Each frame is 772 bytes (`duration`, `sound`, and 32 `KeyBone` structs).
    * Converted PSX 4096-fixed point YXZ Euler angles to glTF-compatible normalized quaternions.
    * Implemented `dcb_viewer/formats/animation.py`.
  * Implemented glTF 2.0 / GLB binary exporter in `dcb_viewer/exporters/gltf.py`:
    * Embedded PNG texture images with retro NEAREST sampling.
    * Rigged skeletal mesh with `JOINTS_0`, `WEIGHTS_0`, and `inverseBindMatrices`.
    * Export of up to 8 animation tracks per model (Idle, Attack 1, Attack 2, Finisher, Hurt, Defeat, Victory, Guard).
  * Added `export-gltf` and `batch-export-gltf` CLI commands.
  * Verified 11/11 unit and integration tests passing (`tests/test_gltf.py`, `tests/test_animation.py`).
  * Batch exported all **267/267 Digimon models** to `original_iso/extracted/models/*.glb` with a 100% success rate!
  * **Phase 1 (Model and Animation Extraction) is 100% complete!**
  * Implemented Digimon card database parser in `dcb_viewer/formats/card_db.py` to map model IDs to canonical names from `CARD2.CDD` (Agumon, Betamon, Greymon, WarGreymon, Omnimon, etc.).
  * Implemented Phase 2 Web 3D Viewer:
    * Created `dcb_viewer/web/server.py` (Multi-threaded HTTP streaming server).
    * Created `dcb_viewer/web/static/index.html` (Modern Three.js WebGL app with OrbitControls, Animation timeline scrubber, Play/Pause, speed adjustment, wireframe, skeleton bone helpers, and instant search).
    * Added `dcb-viewer serve` CLI command.
    * Verified 12/12 unit and integration tests passing (`tests/test_server.py`).
  * **Critical Skinning & Animation Alignment Fix**:
    * Diagnosed spiky mesh stretching and geometric distortion during animation playback:
      1. **glTF Bind-Pose Vertex Space Mismatch**: The glTF 2.0 specification requires the `POSITION` attribute of skinned meshes to be in bind-pose model space, not bone-local space. Using bone-local coordinates caused `M_joint * inv(M_bind)` to apply inverse bind translations to local vertices instead of world vertices, collapsing bones towards the origin and stretching geometry outward during rotation.
      2. **Column-Major Matrix Layout**: glTF `MAT4` accessors mandate column-major order. NumPy C-contiguous matrices were packed row-major, causing translation vectors to be read as the bottom row ($w$-row) and skewing perspective projections. Resolved by storing matrices transposed (`ascontiguousarray(inv_m.T)`).
      3. **Bone Translation Channels**: Added animation channels for bones animating translation (`[(bx + tx) * scale, -(by + ty) * scale, -(bz + tz) * scale]`), enabling character breathing, jumping, and vertical translation offsets.
    * Re-exported all 267 Digimon GLB models with the fixes applied. Tested and verified clean, natural animations across models.
  * **Mesh Topology & Texture Alignment Breakthrough**:
    * Diagnosed and fixed the core reasons models appeared "messy":
      1. **Quad Triangulation Normal Inversion**: Previously, quads $(v_0, v_1, v_2, v_3)$ were split into $(0, 1, 2)$ and $(0, 2, 3)$, which flipped the normal of the second triangle by 180° ($\vec{n}_1 \cdot \vec{n}_2 \approx -1.0$). Fixed to match PSX GPU `POLY_FT4` rasterization: $(0, 1, 2)$ and $(1, 3, 2)$ ($\vec{n}_1 \cdot \vec{n}_2 \approx +1.0$), ensuring uniform outward-facing normals and eliminating black/inverted face shading.
      2. **Decomp-Accurate Strip & Fan Continuation**: Fully implemented `sortModelPrimitives` logic from `external_repository/dcb_decomp/src/main/gfx/tmd_sort.c` for multi-primitive runs (145/400 strips have length > 1), fixing edge-alternation and V0 fan-anchors for all 4 primitive types (textured/untextured quads & tris).
      3. **256×256 VRAM Texture Page Alignment**: Model UV coordinates $(U/256, V/256)$ index into a full 256×256 PSX VRAM page, while TIM files on disc are cropped (e.g. 256×136, 232×112, 56×88). Padded textures onto a standard 256×256 canvas in `gltf.py`, restoring 1:1 sub-pixel UV alignment.
      4. **glTF Alpha Cutout Masking**: Added `"alphaMode": "MASK"` with cutoff 0.1 to cleanly discard transparent VRAM pixels without black fringes or alpha-sorting artifacts.
    * Re-exported all 267 Digimon GLB models with clean topology and aligned textures.
  * **Phase 2 (3D Web Visualization) is 100% complete!**
