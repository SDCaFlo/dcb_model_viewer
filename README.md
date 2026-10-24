# Digimon Card Battle 3D Model & Animation Viewer (DCB Model Viewer)

A Python-based extraction, conversion, and 3D visualization suite for **Digimon Digital Card Battle** (*PSX / PlayStation 1 - SLUS-01328*).

---

## 🎯 Project Goal

The primary objective is to reverse engineer, extract, and visualize the 3D Digimon models, arenas/stages, textures, and skeletal animations embedded in the original PlayStation 1 release.

### Project Roadmap
* **Phase 1: Extraction & Parsing (Data Pipeline)**
  * [ ] File container unpacking (analyzing archives, compression, LBA indexing).
  * [ ] Texture extraction & conversion (PSX TIM format / indexed CLUTs to PNG).
  * [ ] Mesh geometry parsing (vertices, normals, UVs, quad/triangle faces, materials).
  * [ ] Skeleton and animation parsing (bone hierarchies, keyframes, rotation/translation data).
  * [ ] Modern 3D format export (standard **glTF 2.0 / .glb** for seamless compatibility with Blender, Unity, Godot).
* **Phase 2: Visualization (Interactive 3D Tool)**
  * [ ] Interactive 3D viewport (wireframe, flat, textured, and lighting modes).
  * [ ] Skeletal animation timeline playback (scrubbing, looping, speed controls).
  * [ ] Texture & material inspector.
  * [ ] GUI frontend (desktop application) for browsing game archives and previewing models on the fly.

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
│   └── gui/                  # Phase 2: Interactive 3D visualization
│       ├── __init__.py
│       ├── app.py            # Application window & UI controls
│       └── renderer/         # Shader pipeline & viewport rendering
└── tests/                    # Unit tests for binary decoders
```

---

## 🚀 Getting Started (Preliminary)

### 1. Prerequisites
* Python 3.10 or higher.
* `pip` and virtual environment support.

### 2. Setup Environment
```bash
# Clone the repository
git clone https://github.com/your-username/dcb_model_viewer.git
cd dcb_model_viewer

# Create virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Linux/macOS:
source .venv/bin/activate

# Install dependencies (once requirements.txt is available)
pip install -r requirements.txt
```

---

## 🤝 Contributing & Acknowledgments

* **ReGame-Labs** for the ongoing work on [dcb_decomp](https://github.com/ReGame-Labs/dcb_decomp).
* **Lameguy64** for [MKPSXISO](https://github.com/lameguy64/mkpsxiso).
* The PSX homebrew and reverse engineering communities for documentation on PSX hardware, GTE, and TIM formats.

---

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.
