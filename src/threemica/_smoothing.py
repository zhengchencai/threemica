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
    """Smooth a surface metric with wb_command, restricted to a cortex ROI."""
    cmd = [
        _wb_command(), "-metric-smoothing",
        str(surf_path), str(metric_path), str(fwhm), str(out_path),
        "-fwhm", "-roi", str(mask_path),
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"wb_command -metric-smoothing failed:\n{result.stderr}")
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
