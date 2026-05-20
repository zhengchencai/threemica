import json
import nibabel as nib
import numpy as np
import pytest
from pathlib import Path

from threemica._resources import bundle_root
from threemica.builder import build_payload


def _make_func_gii(path: Path, n_vertices: int):
    arr = nib.gifti.GiftiDataArray(
        data=np.random.RandomState(0).rand(n_vertices).astype(np.float32),
        intent="NIFTI_INTENT_NONE",
        datatype="NIFTI_TYPE_FLOAT32",
    )
    nib.save(nib.gifti.GiftiImage(darrays=[arr]), str(path))


@pytest.fixture
def fake_fslr5k_maps(tmp_path):
    surf_lh = bundle_root() / "surfaces" / "fsLR-5k.L.surf.gii"
    surf_rh = bundle_root() / "surfaces" / "fsLR-5k.R.surf.gii"
    n_lh = len(nib.load(str(surf_lh)).agg_data("pointset"))
    n_rh = len(nib.load(str(surf_rh)).agg_data("pointset"))
    map_lh = tmp_path / "lh.func.gii"
    map_rh = tmp_path / "rh.func.gii"
    _make_func_gii(map_lh, n_lh)
    _make_func_gii(map_rh, n_rh)
    return {"surf_lh": surf_lh, "surf_rh": surf_rh, "map_lh": map_lh, "map_rh": map_rh}


def test_build_payload_returns_serializable_dict(fake_fslr5k_maps):
    payload = build_payload(
        surf_lh=fake_fslr5k_maps["surf_lh"],
        surf_rh=fake_fslr5k_maps["surf_rh"],
        map_lhs=[fake_fslr5k_maps["map_lh"]],
        map_rhs=[fake_fslr5k_maps["map_rh"]],
        resolution="fsLR-5k",
        labels=["thickness"],
        sub_labels=[""],
        cb_labels=["mm"],
        colormaps=["plasma"],
        clims=[None],
        surface_type="template",
    )
    # Must be JSON-serializable end-to-end
    s = json.dumps(payload)
    assert len(s) > 1000
    # Sanity checks on structure — payload["mesh"]["lh"] and payload["mesh"]["rh"]
    assert "lh" in payload["mesh"] and "rh" in payload["mesh"]
    assert "maps" in payload
    assert len(payload["maps"]) == 1
    assert payload["maps"][0]["label"] == "thickness"


def test_build_payload_rejects_unsupported_resolution(fake_fslr5k_maps):
    with pytest.raises((KeyError, ValueError, FileNotFoundError)):
        build_payload(
            surf_lh=fake_fslr5k_maps["surf_lh"],
            surf_rh=fake_fslr5k_maps["surf_rh"],
            map_lhs=[fake_fslr5k_maps["map_lh"]],
            map_rhs=[fake_fslr5k_maps["map_rh"]],
            resolution="fsLR-10k",  # dropped in v1
            labels=["x"],
            sub_labels=[""],
            cb_labels=[""],
            colormaps=["plasma"],
            clims=[None],
            surface_type="template",
        )
