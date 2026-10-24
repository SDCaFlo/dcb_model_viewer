"""Unit tests for Web 3D Viewer server and API."""

import json
import os
import urllib.request
import pytest
from pathlib import Path

from dcb_viewer.web.server import DcbViewerHandler


@pytest.mark.skipif(
    not os.path.exists("original_iso/extracted/models/003.glb"),
    reason="Exported models not found",
)
def test_server_catalog_indexing():
    """Tests indexing of exported GLB models and Digimon names."""
    DcbViewerHandler._cached_catalog = None  # Reset cache
    catalog = DcbViewerHandler.get_catalog()

    assert len(catalog) >= 200

    # Find Agumon (003)
    agumon_entry = next((m for m in catalog if m["id"] == "003"), None)
    assert agumon_entry is not None
    assert "Agumon" in agumon_entry["name"]
    assert agumon_entry["filename"] == "003.glb"
    assert agumon_entry["size"] > 50_000
    assert agumon_entry["anim_count"] == 8

    # Find Greymon (005) or Betamon (004)
    beta_entry = next((m for m in catalog if m["id"] == "004"), None)
    assert beta_entry is not None
    assert "Betamon" in beta_entry["name"]
