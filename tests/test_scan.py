from threemica.core import FeatureMap, scan


def test_scan_subject_with_session(fake_micapipe):
    result = scan(fake_micapipe / "sub-001")
    assert set(result.keys()) == {"ses-01"}
    labels = {(m.label, m.resolution) for m in result["ses-01"]}
    assert ("thickness", "fsLR-5k") in labels
    assert ("thickness", "fsLR-32k") in labels
    assert ("curv", "fsLR-5k") in labels
    assert ("curv", "fsLR-32k") in labels


def test_scan_drops_orphan_hemi(fake_micapipe):
    result = scan(fake_micapipe / "sub-001")
    labels = {m.label for m in result["ses-01"]}
    assert "orphan" not in labels


def test_scan_subject_without_session(fake_micapipe):
    result = scan(fake_micapipe / "sub-002")
    assert set(result.keys()) == {None}
    assert len(result[None]) == 1
    fm = result[None][0]
    assert fm.label == "myelin"
    assert fm.resolution == "fsLR-32k"
    assert fm.lh_path.exists() and fm.rh_path.exists()


def test_scan_empty_subject(fake_micapipe):
    result = scan(fake_micapipe / "sub-003")
    assert result == {None: []}


def test_featuremap_paths_are_resolved(fake_micapipe):
    result = scan(fake_micapipe / "sub-001")
    for fm in result["ses-01"]:
        assert isinstance(fm, FeatureMap)
        assert "hemi-L" in fm.lh_path.name
        assert "hemi-R" in fm.rh_path.name
        assert fm.lh_path.is_absolute()
