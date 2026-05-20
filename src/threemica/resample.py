"""wb_command wrappers for resampling subject surfaces and maps to fsLR-10k.

Called by build_report.py when --resolution fsLR-10k is requested and
the subject only has fsLR-32k outputs (standard micapipe).
"""
from __future__ import annotations

import subprocess
from pathlib import Path

from threemica._resources import bundle_root as _bundle_root

WB_CMD = "/Applications/workbench/bin_macosxub/wb_command"

# Template sphere files in the bundle (32k → 10k)
_SURF_TMPL = _bundle_root() / "surfaces"

_SPHERE_32k = {
    "L": _SURF_TMPL / "fsLR-32k.L.sphere.surf.gii",
    "R": _SURF_TMPL / "fsLR-32k.R.sphere.surf.gii",
}
_SPHERE_TARGET = {
    "fsLR-10k": {"L": _SURF_TMPL / "fsLR-10k.L.sphere.surf.gii", "R": _SURF_TMPL / "fsLR-10k.R.sphere.surf.gii"},
    "fsLR-5k":  {"L": _SURF_TMPL / "fsLR-5k.L.sphere.surf.gii",  "R": _SURF_TMPL / "fsLR-5k.R.sphere.surf.gii"},
}
_MID_32k_TMPL = {
    "L": _SURF_TMPL / "fsLR-32k.L.midthickness.surf.gii",
    "R": _SURF_TMPL / "fsLR-32k.R.midthickness.surf.gii",
}
_MID_TARGET = {
    "fsLR-10k": {"L": _SURF_TMPL / "fsLR-10k.L.midthickness.surf.gii", "R": _SURF_TMPL / "fsLR-10k.R.midthickness.surf.gii"},
    "fsLR-5k":  {"L": _SURF_TMPL / "fsLR-5k.L.surf.gii",               "R": _SURF_TMPL / "fsLR-5k.R.surf.gii"},
}


def _wb(*args: str) -> None:
    result = subprocess.run([WB_CMD, *args], capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f"wb_command failed:\n{result.stderr}")


def resample_surface_to_target(
    surf_32k: Path,
    hemi: str,          # "L" or "R"
    resolution: str,    # "fsLR-10k" or "fsLR-5k"
    out_path: Path,
) -> Path:
    """Resample a subject 32k midthickness surface to target resolution via BARYCENTRIC."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        print(f"  [resample] cached: {out_path.name}")
        return out_path
    print(f"  [resample] surface {hemi}: 32k → {resolution} …")
    _wb(
        "-surface-resample",
        str(surf_32k),
        str(_SPHERE_32k[hemi]),
        str(_SPHERE_TARGET[resolution][hemi]),
        "BARYCENTRIC",
        str(out_path),
    )
    return out_path


def resample_metric_to_target(
    metric_32k: Path,
    surf_32k: Path,
    hemi: str,          # "L" or "R"
    resolution: str,    # "fsLR-10k" or "fsLR-5k"
    out_path: Path,
) -> Path:
    """Resample a scalar .func.gii from fsLR-32k to target resolution via ADAP_BARY_AREA."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if out_path.exists():
        print(f"  [resample] cached: {out_path.name}")
        return out_path
    print(f"  [resample] metric  {hemi}: 32k → {resolution} …")
    _wb(
        "-metric-resample",
        str(metric_32k),
        str(_SPHERE_32k[hemi]),
        str(_SPHERE_TARGET[resolution][hemi]),
        "ADAP_BARY_AREA",
        str(out_path),
        "-area-surfs",
        str(surf_32k),                  # source area (individual 32k)
        str(_MID_TARGET[resolution][hemi]), # target area
    )
    return out_path
