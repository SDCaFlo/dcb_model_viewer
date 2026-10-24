# Agent & Contributor Guide (AGENTS.md)

Welcome to the **DCB Model Viewer** project! This document outlines the core architecture, development standards, operational workflows, and instructions for AI agents and human contributors working on this codebase.

---

## 📌 Project Overview & Goals

* **Target Game**: *Digimon Digital Card Battle* (PlayStation 1 - `SLUS-01328`)
* **Mission**: Create a Python toolchain to extract, parse, export (to glTF 2.0 / GLB), and interactively visualize 3D models, textures, and skeletal animations from the game disc.
* **Core Reference Repositories**:
  * `external_repository/dcb_decomp`: Decompiled C source code of the game (read-only reference).
  * `external_repository/mkpsxiso`: PlayStation ISO extraction toolchain.

---

## 🧭 Progress & Task Tracking

> [!IMPORTANT]
> **Always consult [PROGRESS.md](file:///f:/Projects/digimon/dcb_model_viewer/PROGRESS.md) before starting any task.**
> - Check current milestone status and active backlog items.
> - Whenever a milestone, task, or significant subtask is completed or altered, **update `PROGRESS.md` immediately**.
> - Log notable architectural discoveries or format breakthroughs in the `Activity Log` section of `PROGRESS.md`.

---

## ⚙️ Environment & Tooling Standards

1. **Python Version**: Python 3.13+ managed via `pyenv`.
2. **Dependency Management**: Managed via **Poetry** with in-project virtual environments (`.venv`).
   * Run commands in the environment using `poetry run <command>` or `.venv\Scripts\python.exe`.
   * Add new dependencies with `poetry add <package>` (or `poetry add --group dev <package>`).
3. **External Repositories**:
   * Stored in `external_repository/`.
   * **Strictly read-only**: Never edit, modify, or commit files within `external_repository/`.
   * Ignored by Git via `.gitignore`.
4. **Legal / Clean-Room Policy**:
   * Never commit proprietary game assets (disc ISOs, `.bin`, `.cue`, dumped proprietary textures or models).
   * User must supply their own legitimate dump.

---

## 🏗️ Code Architecture & Standards

### Directory Layout
```text
dcb_model_viewer/
├── AGENTS.md                 # Agent instructions and architectural rules (this file)
├── PROGRESS.md               # Active progress tracker and task backlog
├── README.md                 # Public documentation and setup guide
├── pyproject.toml            # Poetry configuration & project dependencies
├── external_repository/      # [Git ignored] Cloned reference repositories (dcb_decomp, mkpsxiso)
├── docs/                     # Research notes, format specifications, struct diagrams
├── dcb_viewer/               # Main application package
│   ├── formats/              # Binary readers and parsers
│   │   ├── tim.py            # PSX TIM image & CLUT parser
│   │   ├── model.py          # 3D geometry & vertex packet parser
│   │   ├── animation.py      # Skeletal hierarchy & track parser
│   │   └── archive.py        # Container / disc archive unpacker
│   ├── exporters/            # Target format exporters (glTF 2.0 / GLB)
│   ├── gui/                  # Phase 2: 3D viewer & viewport UI
│   └── cli.py                # Command-line interface
└── tests/                    # Pytest test suite for parsers
```

### Coding Guidelines
* **Type Annotations**: Use Python 3.13 type annotations throughout (e.g., `int | None`, `list[str]`).
* **Binary Parsing**:
  * Prefer `struct` or declarative `construct` schemas for clarity.
  * Always document binary field offsets and endianness (PSX is little-endian MIPS).
  * Always cross-reference the corresponding C struct from `external_repository/dcb_decomp` in the docstring.
* **Separation of Concerns**:
  * Parsing logic must remain 100% decoupled from rendering/GUI code.
  * Formats should parse into pure Python/Numpy dataclasses or dictionaries.
* **Math & Geometry**:
  * PlayStation 1 uses fixed-point math (`S.3.12` or `S.11.4`) and integer coordinate systems.
  * Normalize vertices and scale factors cleanly to standard floating-point coordinates in meters/units.

---

## 🔍 Reverse-Engineering Best Practices

1. **Leverage `dcb_decomp` First**:
   * Before guessing file offsets or compression types, search `external_repository/dcb_decomp` for keywords (e.g., file extensions, LBA tables, model structs, GTE rendering functions like `RotTransPers`, `gte_rtps`).
2. **Document Findings**:
   * Whenever you decipher a header, packet layout, or compression algorithm, record it in `docs/formats.md` with clear byte-offset tables.
3. **Verification via glTF**:
   * Export parsed models to `.glb` early and verify geometry, UV mapping, and bone weights in Blender or Three.js before moving to GUI rendering.
