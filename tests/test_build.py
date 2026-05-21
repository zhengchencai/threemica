import nibabel as nib
import numpy as np
from pathlib import Path

from threemica._resources import bundle_root
from threemica.core import FeatureMap, build


def _matching_func_gii(target_surf: Path, dst: Path) -> Path:
    n = len(nib.load(str(target_surf)).agg_data("pointset"))
    arr = nib.gifti.GiftiDataArray(
        data=np.random.RandomState(0).rand(n).astype(np.float32),
        intent="NIFTI_INTENT_NONE",
        datatype="NIFTI_TYPE_FLOAT32",
    )
    nib.save(nib.gifti.GiftiImage(darrays=[arr]), str(dst))
    return dst


def test_build_writes_html_with_expected_filename(tmp_path):
    surf_lh = bundle_root() / "surfaces" / "fsLR-5k.L.surf.gii"
    surf_rh = bundle_root() / "surfaces" / "fsLR-5k.R.surf.gii"
    map_lh = _matching_func_gii(surf_lh, tmp_path / "lh.func.gii")
    map_rh = _matching_func_gii(surf_rh, tmp_path / "rh.func.gii")

    sub_dir = tmp_path / "sub-001"
    sub_dir.mkdir()

    out = build(
        subject_dir=sub_dir,
        session=None,
        maps=[FeatureMap("thickness", "fsLR-5k", map_lh, map_rh)],
        resolution="fsLR-5k",
        surface_type="template",
    )
    assert out.exists()
    assert out.parent == sub_dir / "report"
    assert out.name == "sub-001_space-fsLR-5k_desc-template_report-thickness.html"
    text = out.read_text()
    assert "<!doctype html>" in text.lower() or "<html" in text.lower()
    # Payload JSON survived templating
    assert '"maps"' in text


def test_build_with_session_writes_under_session_dir(tmp_path):
    surf_lh = bundle_root() / "surfaces" / "fsLR-5k.L.surf.gii"
    surf_rh = bundle_root() / "surfaces" / "fsLR-5k.R.surf.gii"
    map_lh = _matching_func_gii(surf_lh, tmp_path / "lh.func.gii")
    map_rh = _matching_func_gii(surf_rh, tmp_path / "rh.func.gii")

    sub_dir = tmp_path / "sub-002"
    (sub_dir / "ses-01").mkdir(parents=True)

    out = build(
        subject_dir=sub_dir,
        session="ses-01",
        maps=[FeatureMap("curv", "fsLR-5k", map_lh, map_rh)],
        resolution="fsLR-5k",
        surface_type="template",
    )
    assert out.parent == sub_dir / "ses-01" / "report"
    assert out.name == "sub-002_ses-01_space-fsLR-5k_desc-template_report-curv.html"


def test_build_multi_map_slug_joins_with_dash(tmp_path):
    surf_lh = bundle_root() / "surfaces" / "fsLR-5k.L.surf.gii"
    surf_rh = bundle_root() / "surfaces" / "fsLR-5k.R.surf.gii"
    lh1 = _matching_func_gii(surf_lh, tmp_path / "lh1.func.gii")
    rh1 = _matching_func_gii(surf_rh, tmp_path / "rh1.func.gii")
    lh2 = _matching_func_gii(surf_lh, tmp_path / "lh2.func.gii")
    rh2 = _matching_func_gii(surf_rh, tmp_path / "rh2.func.gii")
    sub_dir = tmp_path / "sub-003"
    sub_dir.mkdir()

    out = build(
        subject_dir=sub_dir,
        session=None,
        maps=[
            FeatureMap("thickness", "fsLR-5k", lh1, rh1),
            FeatureMap("curv", "fsLR-5k", lh2, rh2),
        ],
        resolution="fsLR-5k",
        surface_type="template",
    )
    assert "report-thickness-curv.html" in out.name
