import nibabel as nib
import numpy as np
import pytest
from pathlib import Path

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


@pytest.fixture
def fake_micapipe(tmp_path: Path) -> Path:
    """Build a synthetic MicaPipe derivative tree:

    derivatives/micapipe_v0.2.0/
        sub-001/ses-01/maps/   thickness, curv  @ fsLR-5k + fsLR-32k
                              orphan-L-only @ fsLR-32k
        sub-002/maps/          myelin @ fsLR-32k only
        sub-003/maps/          (empty — no map pairs)
    """
    mp = tmp_path / "derivatives" / "micapipe_v0.2.0"

    s1 = mp / "sub-001" / "ses-01" / "maps"
    s1.mkdir(parents=True)
    for res in ("fsLR-5k", "fsLR-32k"):
        for lab in ("thickness", "curv"):
            _write_pair(s1, "sub-001", "ses-01", res, lab)
    _make_func_gii(
        s1 / "sub-001_ses-01_hemi-L_surf-fsLR-32k_label-orphan.func.gii",
        _RES_VERTS["fsLR-32k"],
    )

    s2 = mp / "sub-002" / "maps"
    s2.mkdir(parents=True)
    _write_pair(s2, "sub-002", None, "fsLR-32k", "myelin")

    (mp / "sub-003" / "maps").mkdir(parents=True)

    return mp
