# Project Progress & Backlog: DCB Model Viewer

This document tracks the active progress, roadmap milestones, completed tasks, and upcoming backlog for the **Digimon Digital Card Battle (PSX - SLUS-01328) Model & Animation Viewer/Exporter**.

---

## 📌 Current Status Summary
* **Active Phase**: Phase 1 - Model and Animation Extraction
* **Current Focus**: Environment Setup & Decompilation Codebase Analysis
* **Status**: 🟢 In Progress

---

## 🗺️ Milestone Roadmap

### Phase 1: Model & Animation Extraction (Data Pipeline)

| Task ID | Item | Status | Notes |
| :--- | :--- | :---: | :--- |
| **P1-01** | Python Environment Setup (pyenv + poetry + Python 3.13) | 🟢 Done | Poetry 2.4.1 + Python 3.13.13 in .venv with numpy, pillow, pygltflib, construct |
| **P1-02** | External Repositories Setup (`dcb_decomp`, `mkpsxiso`) | 🟢 Done | Cloned into `external_repository/` (ignored in git) |
| **P1-03** | Project Standards & Guidelines (`AGENTS.md`, `PROGRESS.md`) | 🟢 Done | Operational guides and backlog established |
| **P1-04** | Disc Structure & Archive Analysis | ⚪ Backlog | Identify files on SLUS-01328 (.BIN, .PAC, LBA tables) |
| **P1-05** | Decompilation Research (`dcb_decomp`) | ⚪ Backlog | Locate model structs, vertex formats, GTE draw calls |
| **P1-06** | PSX TIM Texture Decoder | ⚪ Backlog | Parse 4-bit / 8-bit / 16-bit TIMs and CLUT palettes to PNG |
| **P1-07** | 3D Mesh Geometry Parser | ⚪ Backlog | Parse vertices, normals, UVs, polygon packets (tris/quads) |
| **P1-08** | Bone Hierarchy & Skeleton Parser | ⚪ Backlog | Parse joint transforms and parent-child hierarchy |
| **P1-09** | Skeletal Animation Parser | ⚪ Backlog | Parse rotation, translation, and keyframe tracks |
| **P1-10** | glTF 2.0 / GLB Exporter | ⚪ Backlog | Export rigged, textured models with animations to `.glb` |

---

### Phase 2: 3D Visualization (Interactive Tool)

| Task ID | Item | Status | Notes |
| :--- | :--- | :---: | :--- |
| **P2-01** | 3D Viewport Architecture | ⚪ Backlog | Interactive 3D canvas (orbit, pan, zoom, wireframe) |
| **P2-02** | Shading & Material Pipeline | ⚪ Backlog | Support PSX-style unlit / vertex-lit / textured rendering |
| **P2-03** | Animation Player UI | ⚪ Backlog | Timeline scrubber, playback speed, loop toggle |
| **P2-04** | Asset Browser & Inspector | ⚪ Backlog | File tree for extracted Digimon, models, and textures |
| **P2-05** | Standalone GUI Application | ⚪ Backlog | Unified desktop app (PySide6 / ModernGL) |

---

## 📋 Backlog & Future Considerations

* [ ] **Arena / Battle Stage Exporter**: Digimon Card Battle features 3D battle arenas; parse stage geometry and background textures.
* [ ] **Audio / SFX / Voice extraction**: Low-priority bonus (PSX VAB/SPU sound files).
* [ ] **Batch Conversion CLI**: Command-line tool to dump the entire game disc into modern glTF models in one command (`dcb-viewer extract-all --iso ...`).
* [ ] **Blender Addon Integration**: Evaluate creating a direct Blender import script if custom format features warrant it.

---

## 📝 Activity Log

* **2026-10-24**:
  * Project initialized.
  * Formulated project scope, architecture, and README.md.
  * Configured Python 3.13 with pyenv and Poetry.
  * Created `AGENTS.md` and `PROGRESS.md` tracking system.
