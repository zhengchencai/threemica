import shutil

import nibabel as nib
import numpy as np
import pytest
from pathlib import Path

from threemica._resources import bundle_root

_RES_VERTS = {"fsLR-5k": 4842, "fsLR-32k": 32492}


def _make_func_gii(path: Path, n_vertices: int):
    arr = nib.gifti.GiftiDataArray(
        data=np.random.RandomState(0).rand(n_vertices).astype(np.float32),
        intent="NIFTI_INTENT_NONE",
        datatype="NIFTI_TYPE_FLOAT32",
    )
    nib.save(nib.gifti.GiftiImage(darrays=[arr]), str(path))


def _write_pair(maps_dir: Path, sub: str, ses: str | None, res: str, label: str):
    base = f"{sub}" + (f"_{ses}" if ses else "")
    for hemi in ("L", "R"):
        path = maps_dir / f"{base}_hemi-{hemi}_surf-{res}_label-{label}.func.gii"
        _make_func_gii(path, _RES_VERTS[res])


def _write_midthickness_surfaces(surf_dir: Path, sub: str, ses: str | None):
    """Copy bundled fsLR template midthickness surfaces into surf/ as the
    individual subject surfaces (filename per micapipe convention)."""
    surf_dir.mkdir(parents=True, exist_ok=True)
    bundle_surfs = bundle_root() / "surfaces"
    base = sub + (f"_{ses}" if ses else "")
    for res in ("fsLR-5k", "fsLR-32k"):
        for hemi in ("L", "R"):
            src = bundle_surfs / f"{res}.{hemi}.midthickness.surf.gii"
            if not src.exists():
                src = bundle_surfs / f"{res}.{hemi}.surf.gii"
            dst = surf_dir / (
                f"{base}_hemi-{hemi}_space-nativepro_surf-{res}_label-midthickness.surf.gii"
            )
            shutil.copy(src, dst)


@pytest.fixture
def fake_bids(tmp_path: Path) -> Path:
    """Build a synthetic BIDS tree with one micapipe-style derivative:

    derivatives/micapipe_v0.2.0/
        sub-001/ses-01/maps/   thickness, curv @ fsLR-5k + fsLR-32k + orphan-L-only @ 32k
        sub-001/ses-01/surf/   midthickness surfaces @ fsLR-5k, fsLR-32k (both hemis)
        sub-002/maps/          myelin @ fsLR-32k only
        sub-002/surf/          midthickness surfaces
        sub-003/maps/          (empty)
    """
    mp = tmp_path / "derivatives" / "micapipe_v0.2.0"

    s1_maps = mp / "sub-001" / "ses-01" / "maps"
    s1_maps.mkdir(parents=True)
    for res in ("fsLR-5k", "fsLR-32k"):
        for lab in ("thickness", "curv"):
            _write_pair(s1_maps, "sub-001", "ses-01", res, lab)
    _make_func_gii(
        s1_maps / "sub-001_ses-01_hemi-L_surf-fsLR-32k_label-orphan.func.gii",
        _RES_VERTS["fsLR-32k"],
    )
    _write_midthickness_surfaces(mp / "sub-001" / "ses-01" / "surf", "sub-001", "ses-01")

    s2_maps = mp / "sub-002" / "maps"
    s2_maps.mkdir(parents=True)
    _write_pair(s2_maps, "sub-002", None, "fsLR-32k", "myelin")
    _write_midthickness_surfaces(mp / "sub-002" / "surf", "sub-002", None)

    (mp / "sub-003" / "maps").mkdir(parents=True)

    return tmp_path  # BIDS root


@pytest.fixture
def fake_scope() -> dict:
    """Scope matching `fake_bids`: thickness/curv from micapipe maps; myelin too.

    Returned in NORMALIZED shape — each tag is a dict with tag/label/unit/cmap.
    """
    from threemica._scope import normalize_scope
    return normalize_scope({
        "surface": {
            "derivative": "micapipe_v0.2.0",
            "subdir": "surf",
            "label": "midthickness",
        },
        "micapipe_v0.2.0": {"maps": [
            {"tag": "thickness", "label": "Cortical Thickness", "unit": "mm", "cmap": "pos-only"},
            {"tag": "curv",      "label": "Curvature",          "unit": "1/mm", "cmap": "diverging"},
            {"tag": "myelin",    "label": "Myelin Mapping",     "unit": "T1w/T2w", "cmap": "pos-only"},
        ]},
    })


# Backwards-compat aliases for older tests
@pytest.fixture
def fake_micapipe(fake_bids: Path) -> Path:
    return fake_bids / "derivatives" / "micapipe_v0.2.0"
