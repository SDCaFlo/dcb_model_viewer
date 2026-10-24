# Digimon Card Battle 3D Model & Animation Viewer (DCB Model Viewer)

A Python-based extraction, conversion, and 3D visualization suite for **Digimon Digital Card Battle** (*PSX / PlayStation 1 - SLUS-01328*).

---

## 🎯 Project Goal

The primary objective is to reverse engineer, extract, and visualize the 3D Digimon models, arenas/stages, textures, and skeletal animations embedded in the original PlayStation 1 release.

### Project Roadmap
* **Phase 1: Extraction & Parsing (Data Pipeline)** 🟢 **Complete**
  * [x] File container unpacking (`.DRV` virtual disc archives, sector indexing).
  * [x] Compression engine (`LZSS` 4KB circular buffer + dynamic Huffman tree decoder).
  * [x] Texture extraction & conversion (PSX TIM format / 4-bit, 8-bit, 16-bit CLUTs to PNG).
  * [x] Mesh geometry parsing (OMD format, SVECTOR vertices, normals, UVs, quad/triangle packets).
  * [x] Skeleton and animation parsing (bone hierarchies, 772-byte keyframes, YXZ Euler to Quaternion).
  * [x] Modern 3D format export (standard **glTF 2.0 / .glb** with embedded textures and 8 animation tracks).
* **Phase 2: Visualization (Interactive 3D Tool)** 🟢 **Complete**
  * [x] Three.js WebGL interactive 3D viewport (OrbitControls, studio lighting, ground grid).
  * [x] Skeletal animation timeline playback (scrubbing, play/pause, looping, 0.25x - 2x speed controls).
  * [x] Retro pixelated NEAREST texture sampling and wireframe / bone helper overlays.
  * [x] Digimon Card Database (`CARD2.CDD`) integration mapping 190+ model IDs to official Digimon names.
  * [x] Multi-threaded local Web Viewer server (`poetry run dcb-viewer serve`).

---

## 🔍 Foundation & Reverse Engineering

This project builds upon the insights from the community reverse-engineering efforts:
* **[dcb_decomp](https://github.com/ReGame-Labs/dcb_decomp)**: Decompiled C codebase of Digimon Card Battle. We reference its decompiled structs, GTE rendering routines, and file-reading functions to understand how the original PlayStation MIPS hardware processed 3D geometry and animations.
* **Format Research**: PlayStation 1 games often use custom variations of Sony's SDK formats (TMD/TOD/HMD) or proprietary GTE-optimized vertex packets with fixed-point math (`S.3.12` or `S.11.4`). Reference decompilations guide us in faithfully mapping these data structures into clean Python abstractions.

---

## ⚖️ Legal & Prerequisites

> [!IMPORTANT]
> **No copyrighted game assets or ISO files are distributed in this repository.**
> Users must dump their own legally acquired copy of the game.

To extract assets, you will need:
1. A legitimate copy of **Digimon Digital Card Battle** (`SLUS-01328`).
2. A PlayStation ISO extraction tool, such as **[MKPSXISO](https://github.com/lameguy64/mkpsxiso)** (or `dumpsxiso`), to extract the filesystem and sector data from your disc image (`.bin`/`.cue`).

---

## 🛠️ Proposed Tech Stack

* **Language**: Python 3.10+
* **Binary Parsing**: `struct`, `io`, or declarative binary parsers (`construct` / `kaitai-struct`)
* **Math & Geometry**: `numpy`
* **Texture Processing**: `Pillow` (PIL) for TIM/CLUT decoding and PNG exporting
* **3D Export**: `pygltflib` / `trimesh` (for glTF 2.0 / GLB output)
* **Visualization (Phase 2)**: ModernGL / PySide6 (or Pygame/Pyglet) for low-overhead, GPU-accelerated 3D rendering with bone skinning support

---

## 📂 Proposed Project Structure

```text
dcb_model_viewer/
├── README.md
├── requirements.txt
├── docs/                     # Format documentation, memory maps, struct notes
│   ├── formats.md
│   └── notes_decomp.md
├── dcb_viewer/               # Main Python package
│   ├── __init__.py
│   ├── cli.py                # Command-line interface for batch extraction/export
│   ├── formats/              # Binary format readers/decoders
│   │   ├── __init__.py
│   │   ├── tim.py            # PSX TIM texture decoder
│   │   ├── model.py          # 3D mesh & vertex packet parser
│   │   ├── animation.py      # Skeletal animation & bone track parser
│   │   └── archive.py        # Container / disc archive unpacker
│   ├── exporters/            # Exporters to modern formats
│   │   ├── __init__.py
│   │   └── gltf.py           # glTF 2.0 / GLB exporter
│   └── web/                  # Phase 2: Web 3D visualization
│       ├── __init__.py
│       ├── server.py         # Multi-threaded HTTP server & API
│       └── static/           # Three.js SPA (HTML5/CSS3/ES6)
└── tests/                    # Pytest test suite (12/12 passing)
```

---

## 🚀 Getting Started & Usage

### 1. Setup Environment
This project uses **Python 3.13** and **Poetry**:
```bash
# Clone the repository
git clone https://github.com/your-username/dcb_model_viewer.git
cd dcb_model_viewer

# Install dependencies into local virtualenv (.venv)
poetry install
```

### 2. Extract Disc & Assets
Dump your legally owned game disc (`SLUS-01328`) with `dumpsxiso`:
```bash
# Unpack all virtual drive archives (.DRV)
poetry run dcb-viewer unpack-drv original_iso/dump original_iso/extracted
```

### 3. Batch Convert Digimon to glTF 2.0 / GLB
Convert all 267 3D Digimon models, textures, skeletons, and animations:
```bash
poetry run dcb-viewer batch-export-gltf original_iso/extracted/F original_iso/extracted/models
```

### 4. Launch the Interactive Web 3D Viewer
Start the viewer and explore the 3D models and animations in your browser:
```bash
poetry run dcb-viewer serve
```
Open **`http://127.0.0.1:8080/`** to:
* Search and browse all 267 Digimon models.
* Orbit, pan, and zoom around any model with realistic lighting or wireframe mode.
* Play, pause, scrub, and change speed for all 8 animation tracks (`Idle`, `Attack 1`, `Attack 2`, `Finisher`, `Take Damage`, `Defeat`, `Victory`, `Guard`).

---

## 🤝 Contributing & Acknowledgments

* **ReGame-Labs** for the ongoing work on [dcb_decomp](https://github.com/ReGame-Labs/dcb_decomp).
* **Lameguy64** for [MKPSXISO](https://github.com/lameguy64/mkpsxiso).
* The PSX homebrew and reverse engineering communities for documentation on PSX hardware, GTE, and TIM formats.

---

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.
