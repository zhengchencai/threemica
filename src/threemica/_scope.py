"""Scope loader. Reads `<BIDS>/derivatives/threemica_scope.json`.

A scope's `subdir → tag-list` entry can hold either:
  - a plain string tag (use defaults from MAP_SETTINGS for display)
  - a dict `{"tag": "...", "label": "...", "unit": "...", "cmap": "pos-only|diverging"}`

`load_or_copy_scope` normalizes both forms into the dict shape.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Any, Dict

from rich.console import Console

from threemica._resources import bundle_root
from threemica.builder import guess_cb_label, guess_map_settings


_FILENAME = "threemica_scope.json"


def _example_path() -> Path:
    return bundle_root().parent / "threemica_scope.example.json"


def scope_path(bids_root: Path) -> Path:
    return bids_root / "derivatives" / _FILENAME


def _normalize_tag(entry) -> Dict[str, Any]:
    """Turn a scope tag entry (str or dict) into a uniform dict with at least
    `tag`, `label`, `unit`, `cmap`. Missing fields fall back to MAP_SETTINGS
    via substring lookup against the tag string itself."""
    if isinstance(entry, str):
        tag = entry
        explicit = {}
    elif isinstance(entry, dict):
        tag = entry["tag"]
        explicit = entry
    else:
        raise ValueError(f"Invalid scope entry: {entry!r}")
    inferred_label, inferred_cmap = guess_map_settings(tag)
    inferred_unit = guess_cb_label(tag)
    return {
        "tag":   tag,
        "label": explicit.get("label", inferred_label),
        "unit":  explicit.get("unit",  inferred_unit if inferred_unit != "Value" else ""),
        "cmap":  explicit.get("cmap",  inferred_cmap),
        "scale": float(explicit.get("scale", 1.0)),
        # smoothing method when --smooth N is given:
        #   "kernel" (default) → wb_command Gaussian (continuous data)
        #   "dilate"           → nearest-neighbour graph dilation (sparse/integer)
        "smooth_method": explicit.get("smooth_method", "kernel"),
    }


def normalize_scope(scope: Dict[str, Any]) -> Dict[str, Any]:
    """Return a copy of ``scope`` with every tag list normalized to dicts."""
    out: Dict[str, Any] = {}
    for k, v in scope.items():
        if k == "surface":
            out[k] = v
            continue
        out[k] = {sub: [_normalize_tag(t) for t in tags] for sub, tags in v.items()}
    return out


def load_or_copy_scope(bids_root: Path, console: Console | None = None) -> Dict[str, Any]:
    """Return the normalized scope dict for ``bids_root``."""
    console = console or Console()
    dst = scope_path(bids_root)
    dst.parent.mkdir(parents=True, exist_ok=True)
    if not dst.exists():
        shutil.copy(_example_path(), dst)
        console.print(
            f"[yellow]threemica_scope.json[/] copied to [cyan]derivatives/[/]. "
            "Edit it to customize what threemica scans — otherwise it will use "
            "the default scope (thickness, curv, midthickness FA/ADC/T1map/cbf)."
        )
    else:
        console.print(
            f"[green]threemica_scope.json[/] found in [cyan]derivatives/[/]. "
            "Edit it if you want to change the scope."
        )
    with dst.open() as f:
        return normalize_scope(json.load(f))
