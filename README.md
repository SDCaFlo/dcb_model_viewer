# Digimon Card Battle 3D Model & Animation Viewer (DCB Model Viewer)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![glTF 2.0](https://img.shields.io/badge/glTF-2.0%20%2F%20GLB-green.svg)](https://www.khronos.org/gltf/)

An open-source reverse-engineering toolchain and interactive 3D Web Viewer for **Digimon Digital Card Battle** (*PlayStation 1 - NTSC-U SLUS-01328*).

Extracts, decompresses, converts, and visualizes all **267 Digimon 3D models**, textures, skeletal rigs, and animation tracks from the original PSX game disc into modern, standard **glTF 2.0 / .glb** files.

---

## ✨ Features

* **Complete Archive Extraction**: Unpacks `.DRV` virtual disc archives and decompresses compressed assets using an authentic port of the game's LZSS (4KB circular buffer) + dynamic Huffman tree decompressor (`archive.c` / `decompress.c`).
* **Multi-CLUT Texture Decoding**: Automatically resolves per-polygon palette bank switching from PSX TIM textures (e.g., rendering Magnamon with authentic golden armor and blue skin).
* **Authentic 60 Hz Skeletal Animations**: Decodes 772-byte keyframe skeletal animation tracks with 60 Hz NTSC VBLANK timing, converting PlayStation fixed-point YXZ Euler rotations into normalized quaternions across 8 combat animation tracks (`Idle`, `Attack 1`, `Attack 2`, `Finisher`, `Take Damage`, `Defeat`, `Victory`, `Guard`).
* **Clean Modern glTF 2.0 / GLB Output**: Fully rigged models with joint hierarchies and standard PBR materials ready for **Blender**, **Unity**, **Unreal Engine**, **Godot**, or **Three.js**.
* **Interactive Local Web 3D Viewer**: Browser-based Three.js application featuring:
  * Digimon Card Database (`CARD2.CDD`) integration mapping model IDs to official Digimon names with search filtering.
  * Full orbit, pan, and zoom camera controls with ground grid and studio lighting.
  * Real-time animation timeline scrubber, loop controls, and playback speed multipliers (0.25× to 2.0×).
  * Retro PSX pixelated (`NEAREST`) vs. modern smooth (`LINEAR`) texture filtering toggle.
  * Wireframe overlay and bone skeleton helper visualizers.

---

## 📋 Prerequisites & Requirements

Before starting, ensure you have the following installed on your system:

1. **Python 3.10+** (Python 3.13 recommended): [python.org](https://www.python.org/)
2. **Poetry** (Python dependency and packaging manager):
   ```bash
   pip install poetry
   ```
3. **Your PlayStation 1 Game Disc Image**:
   * A legitimate copy of **Digimon Digital Card Battle** (*SLUS-01328*).
   * Dumped as a standard `.bin` / `.cue` or `.iso` image.
4. **External Tool: MKPSXISO (`dumpsxiso`)**:
   * PlayStation 1 discs use raw 2352-byte sector formatting (Mode 2 / Form 1 / Form 2) with specialized CD-XA sector headers that general-purpose archive extractors (like 7-Zip or WinRAR) cannot parse.
   * We use **`dumpsxiso`** from the open-source **[MKPSXISO toolchain by Lameguy64](https://github.com/lameguy64/mkpsxiso)**.
   * **Download**: Grab the latest pre-compiled binary for your OS from the [MKPSXISO GitHub Releases](https://github.com/lameguy64/mkpsxiso/releases). Make sure `dumpsxiso` (or `dumpsxiso.exe`) is accessible in your system `PATH` or placed into your project directory.

---

## 🚀 Step-by-Step Quickstart Guide

### Step 1: Clone Repository & Install Dependencies

```bash
git clone https://github.com/your-username/dcb_model_viewer.git
cd dcb_model_viewer

# Install Python dependencies into a local virtual environment (.venv)
poetry install
```

---

### Step 2: Place Your Game Disc Dump

Create a folder named `original_iso/` in the project root and place your dumped PlayStation `.bin` and `.cue` files inside:

```text
dcb_model_viewer/
├── original_iso/
│   ├── Digimon Digital Card Battle.bin    <-- Your PSX game disc dump
│   └── Digimon Digital Card Battle.cue
├── dcb_viewer/
├── pyproject.toml
└── README.md
```

> [!NOTE]
> The `original_iso/` folder is explicitly listed in `.gitignore` to prevent any proprietary game files from being committed or uploaded.

---

### Step 3: Extract the Disc Filesystem with `dumpsxiso`

Run `dumpsxiso` from your terminal to extract the raw filesystem sectors into an `original_iso/dump/` directory:

```bash
# Windows / Linux / macOS
dumpsxiso "original_iso/Digimon Digital Card Battle.bin" -s original_iso/dump.xml -x original_iso/dump/
```

This will extract the disc contents into `original_iso/dump/`, producing the game's core virtual drive archives:
* `A.DRV`, `B.DRV`, `C.DRV`, `E.DRV`, `F.DRV`, `G.DRV`, `P.DRV`
* `SLUS_013.28` (Executable)
* `SYSTEM.CNF`

---

### Step 4: Unpack Virtual Drive Archives (`.DRV`)

Use the built-in CLI to unpack all `.DRV` containers into individual assets:

```bash
poetry run dcb-viewer unpack-drv original_iso/dump original_iso/extracted
```

This extracts over 2,400 game assets into `original_iso/extracted/`:
* `original_iso/extracted/F/`: Digimon 3D model packages (`001.PAK` to `267.PAK`).
* `original_iso/extracted/B/CARD2.CDD`: The official card database mapping model IDs to Digimon names and card stats.
* `original_iso/extracted/E/`: Texture packs (`.TIM`), sound archives (`.VAB`), and card illustrations.

---

### Step 5: Convert Digimon Models to glTF 2.0 / GLB

#### Option A: Batch Export All 267 Digimon Models (Recommended)
Convert every Digimon character model, skeleton, texture, and animation track into modern `.glb` files:

```bash
poetry run dcb-viewer batch-export-gltf original_iso/extracted/F original_iso/extracted/models
```

This processes all 267 models and saves them to `original_iso/extracted/models/` (e.g. `001.glb` through `267.glb`).

#### Option B: Export a Single Digimon Model
You can also convert an individual Digimon `.PAK` package directly:

```bash
# Export Magnamon (#189) with its embedded animations and multi-palette textures
poetry run dcb-viewer export-gltf original_iso/extracted/F/189.PAK original_iso/extracted/models/189.glb
```

---

### Step 6: Launch the Interactive 3D Web Viewer

Start the local 3D viewer server:

```bash
poetry run dcb-viewer serve
```

Your default web browser will automatically open:
👉 **`http://127.0.0.1:8080/`**

```text
=================================================================
  DCB MODEL VIEWER - INTERACTIVE 3D WEB VIEWER
=================================================================
  * Serving models from: .../original_iso/extracted/models
  * Total models indexed: 267
  * Viewer URL: http://127.0.0.1:8080/
  Press Ctrl+C to stop the server.
=================================================================
```

#### Viewer Controls:
* **Select Digimon**: Use the left sidebar to search by Digimon name (e.g. "Magnamon", "WarGreymon", "Agumon") or card ID.
* **Camera Orbit**: Left-click + drag to rotate around the Digimon.
* **Camera Pan**: Right-click + drag to pan.
* **Zoom**: Mouse wheel / pinch to zoom in and out.
* **Animations**: Use the bottom player bar to switch between all 8 combat animations, scrub the timeline, or adjust playback speed (`0.25x`, `0.5x`, `1x`, `1.5x`, `2x`).
* **Toolbar Tools**:
  * **Filter**: Toggle between retro pixelated (`NEAREST`) and smooth (`LINEAR`) texture sampling.
  * **Wireframe**: Toggle geometric wireframe overlay.
  * **Skeleton**: View bone joints and skeletal hierarchy.

---

## 🎨 Importing into Blender, Unity, or Unreal Engine

All exported `.glb` files conform strictly to the **glTF 2.0 specification**:
* **Blender**: File → Import → `glTF 2.0 (.glb/.gltf)`. The full skeletal rig and animation actions will appear in the Dope Sheet / Non-Linear Animation editor.
* **Unity**: Drag and drop the `.glb` into your `Assets/` folder. Unity's model importer will automatically detect the avatar rig and animation clips.
* **Unreal Engine**: Import the `.glb` into the Content Browser; skeletal mesh and animation sequences are generated automatically.

---

## 🛠️ CLI Reference

The `dcb-viewer` command provides subcommands for every stage of inspection and extraction:

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `inspect-drv` | `<drv_path>` | Inspect the directory table and sector offsets of a `.DRV` archive. |
| `unpack-drv` | `<input_path> <output_dir>` | Unpack one or all `.DRV` files in a folder into raw files. |
| `inspect-pak` | `<pak_path>` | Inspect chunk IDs, sizes, and decompression status inside a `.PAK` file. |
| `extract-tim` | `<input_path> <output_path>` | Extract PSX TIM textures to PNG with CLUT palette selection. |
| `export-gltf` | `<pak_path> <output_path>` | Convert a single `.PAK` model package to a rigged/animated `.glb`. |
| `batch-export-gltf` | `<input_dir> <output_dir>` | Batch convert an entire directory of `.PAK` models to `.glb`. |
| `serve` | `[--port 8080] [--models-dir ...]` | Start the local HTTP server and open the Three.js 3D Web Viewer. |

---

## 🧪 Running Unit Tests

Run the full pytest test suite (covers TIM decoder, model parser, animation tracks, glTF builder, and web server):

```bash
poetry run pytest tests/
```

---

## ⚖️ Legal & Clean-Room Policy

* **No proprietary or copyrighted game assets are included in this repository.**
* This project is a reverse-engineered clean-room research tool. Users must supply their own legitimate, legally dumped game disc (`SLUS-01328`) to extract assets.
* All trademarks and copyrighted names (e.g. *Digimon*, *Bandai*, *PlayStation*) are property of their respective owners.

---

## 🤝 Acknowledgments & References

* **[dcb_decomp](https://github.com/ReGame-Labs/dcb_decomp)** by ReGame-Labs for the decompilation of *Digimon Digital Card Battle*.
* **[MKPSXISO](https://github.com/lameguy64/mkpsxiso)** by Lameguy64 for the PlayStation disc filesystem extraction toolchain.
* The PlayStation Homebrew and Reverse Engineering communities for PSX hardware and GTE documentation.

---

## 🤖 AI Development Disclaimer

This project, its binary parsing logic, mathematical conversions, and web visualization suite were developed with the assistance of AI (Google DeepMind's Antigravity pair programming assistant).

All reverse-engineering discoveries, binary structures, and mathematical algorithms have been cross-referenced against the decompiled C source code ([`dcb_decomp`](https://github.com/ReGame-Labs/dcb_decomp)) and verified across all 267 game models. However, as with any AI-assisted project, there may be unique stylistic conventions or edge cases. Feedback, bug reports, and pull requests from the community are always welcome!

---

## 📄 License

This project is licensed under the [MIT License](LICENSE).
