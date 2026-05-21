import shutil
import nibabel as nib
import numpy as np
import pytest

from threemica._resources import bundle_root
from threemica._smoothing import smooth_map, write_cortex_mask_gii


_HAS_WB = shutil.which("wb_command") is not None


def _matching_func_gii(target_surf, dst):
    n = len(nib.load(str(target_surf)).agg_data("pointset"))
    arr = nib.gifti.GiftiDataArray(
        data=np.random.RandomState(0).rand(n).astype(np.float32),
        intent="NIFTI_INTENT_NONE",
        datatype="NIFTI_TYPE_FLOAT32",
    )
    nib.save(nib.gifti.GiftiImage(darrays=[arr]), str(dst))
    return dst


def test_write_cortex_mask_gii_inverts_medial_wall(tmp_path):
    out = write_cortex_mask_gii("fsLR-5k", "lh", 4842, tmp_path / "mask.shape.gii")
    data = nib.load(str(out)).darrays[0].data
    assert data.shape == (4842,)
    # Medial-wall indices were zeroed; cortex stays 1.0
    mw = np.load(bundle_root() / "medial_wall" / "medial_wall_fsLR-5k_lh.npy")
    assert (data[mw] == 0.0).all()
    cortex_idx = np.setdiff1d(np.arange(4842), mw)
    assert (data[cortex_idx] == 1.0).all()


@pytest.mark.skipif(not _HAS_WB, reason="wb_command not on PATH")
def test_smooth_map_runs(tmp_path):
    surf = bundle_root() / "surfaces" / "fsLR-5k.L.surf.gii"
    n = len(nib.load(str(surf)).agg_data("pointset"))
    metric = _matching_func_gii(surf, tmp_path / "in.func.gii")
    mask = write_cortex_mask_gii("fsLR-5k", "lh", n, tmp_path / "mask.shape.gii")
    out = smooth_map(surf, metric, tmp_path / "out.func.gii", 5, mask)
    assert out.exists()
    smoothed = nib.load(str(out)).darrays[0].data
    assert smoothed.shape == (n,)
    # Smoothing should reduce variance vs the random input
    raw = nib.load(str(metric)).darrays[0].data
    assert smoothed.var() < raw.var()
