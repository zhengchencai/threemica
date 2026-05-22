"""wb_command surface smoothing — port of SPACES spaces_smoothing.smooth_map.

Public:
    smooth_map(surf_path, metric_path, out_path, fwhm, mask_path)
    write_cortex_mask_gii(resolution, hemi, n_verts, out_path)
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import nibabel as nib
import numpy as np

from threemica._resources import bundle_root


def _wb_command() -> str:
    exe = shutil.which("wb_command")
    if not exe:
        raise FileNotFoundError(
            "wb_command not found on PATH. Install Connectome Workbench: "
            "https://www.humanconnectome.org/software/connectome-workbench"
        )
    return exe


def smooth_map(
    surf_path: Path, metric_path: Path, out_path: Path, fwhm: int, mask_path: Path
) -> Path:
    """Gaussian smooth a continuous surface metric via wb_command, restricted
    to a cortex ROI. Not suitable for sparse / categorical data (NaN propagates,
    and averaging IDs is meaningless). For those use ``dilate_map`` instead.
    """
    cmd = [
        _wb_command(), "-metric-smoothing",
        str(surf_path), str(metric_path), str(fwhm), str(out_path),
        "-fwhm", "-roi", str(mask_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"wb_command -metric-smoothing failed:\n{result.stderr}")
    return out_path


def dilate_map(
    surf_path: Path, metric_path: Path, out_path: Path, hops: int,
) -> Path:
    """Nearest-neighbour graph dilation. Each finite vertex value is copied
    outward up to ``hops`` mesh edges; on ties, the closer source wins.
    Original values stay exact (no averaging), so integer / categorical
    data like electrode channel IDs survive intact.
    """
    surf = nib.load(str(surf_path))
    coords = surf.agg_data("pointset")
    faces  = surf.agg_data("triangle")
    n = len(coords)

    # Build mesh adjacency as a list of sets
    adj = [set() for _ in range(n)]
    for a, b, c in faces:
        adj[a].add(b); adj[a].add(c)
        adj[b].add(a); adj[b].add(c)
        adj[c].add(a); adj[c].add(b)

    arr = nib.load(str(metric_path)).darrays[0].data.astype(np.float32)
    src = np.where(np.isfinite(arr))[0]
    out = np.full(n, np.nan, dtype=np.float32)
    if len(src) > 0:
        # Multi-source BFS: each finite vertex propagates its value outward.
        out[src] = arr[src]
        frontier = src.tolist()
        for _ in range(int(hops)):
            nxt = []
            for v in frontier:
                v_val = out[v]
                for u in adj[v]:
                    if np.isnan(out[u]):
                        out[u] = v_val
                        nxt.append(u)
            if not nxt:
                break
            frontier = nxt

    gii = nib.GiftiImage(darrays=[nib.gifti.GiftiDataArray(
        out, intent="NIFTI_INTENT_NONE", datatype="NIFTI_TYPE_FLOAT32",
    )])
    nib.save(gii, str(out_path))
    return out_path


def write_cortex_mask_gii(
    resolution: str, hemi: str, n_verts: int, out_path: Path
) -> Path:
    """Write a 1=cortex/0=medial-wall GIFTI mask to ``out_path``.

    Reads ``medial_wall_{resolution}_{hemi}.npy`` from the bundle (int32
    array of medial-wall vertex indices) and inverts it.
    """
    h = "lh" if hemi.lower().startswith("l") else "rh"
    mw_path = bundle_root() / "medial_wall" / f"medial_wall_{resolution}_{h}.npy"
    mw_idx = np.load(mw_path)
    mask = np.ones(n_verts, dtype=np.float32)
    mask[mw_idx] = 0.0
    gii = nib.GiftiImage(darrays=[
        nib.gifti.GiftiDataArray(
            mask, intent="NIFTI_INTENT_NONE", datatype="NIFTI_TYPE_FLOAT32"
        ),
    ])
    nib.save(gii, str(out_path))
    return out_path
