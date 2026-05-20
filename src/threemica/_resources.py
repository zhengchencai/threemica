"""Locate bundled data (atlas + viewer) via importlib.resources."""
from __future__ import annotations

from importlib.resources import files
from pathlib import Path


def bundle_root() -> Path:
    """Return the path to the YBA atlas bundle directory."""
    return Path(str(files("threemica").joinpath("data/yba_micapipe")))


def viewer_template() -> Path:
    """Return the path to the HTML template file."""
    return Path(str(files("threemica").joinpath("viewer/template.html")))


def viewer_js() -> Path:
    """Return the path to the Three.js viewer script."""
    return Path(str(files("threemica").joinpath("viewer/viewer.js")))
