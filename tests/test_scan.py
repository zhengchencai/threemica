from threemica.core import FeatureMap, scan_subject, list_subjects, list_sessions


def test_scan_subject_with_session(fake_bids, fake_scope):
    fms = scan_subject(fake_bids, fake_scope, "sub-001", "ses-01")
    pairs = {(m.label, m.resolution) for m in fms}
    assert ("thickness", "fsLR-5k") in pairs
    assert ("thickness", "fsLR-32k") in pairs
    assert ("curv", "fsLR-5k") in pairs
    assert ("curv", "fsLR-32k") in pairs


def test_scan_drops_unlisted_tags(fake_bids, fake_scope):
    # 'orphan' file exists in maps/ but is not in the scope → skipped
    fms = scan_subject(fake_bids, fake_scope, "sub-001", "ses-01")
    assert all(m.label != "orphan" for m in fms)


def test_scan_subject_without_session(fake_bids, fake_scope):
    fms = scan_subject(fake_bids, fake_scope, "sub-002", None)
    assert len(fms) == 1
    fm = fms[0]
    assert fm.label == "myelin"
    assert fm.resolution == "fsLR-32k"
    assert fm.lh_path.exists() and fm.rh_path.exists()


def test_scan_empty_subject(fake_bids, fake_scope):
    fms = scan_subject(fake_bids, fake_scope, "sub-003", None)
    assert fms == []


def test_list_subjects_union(fake_bids, fake_scope):
    assert list_subjects(fake_bids, fake_scope) == ["sub-001", "sub-002", "sub-003"]


def test_list_sessions(fake_bids, fake_scope):
    assert list_sessions(fake_bids, fake_scope, "sub-001") == ["ses-01"]
    assert list_sessions(fake_bids, fake_scope, "sub-002") == []


def test_featuremap_carries_derivative_and_subdir(fake_bids, fake_scope):
    fms = scan_subject(fake_bids, fake_scope, "sub-001", "ses-01")
    for fm in fms:
        assert isinstance(fm, FeatureMap)
        assert fm.derivative == "micapipe_v0.2.0"
        assert fm.subdir == "maps"
        assert "hemi-L" in fm.lh_path.name
        assert "hemi-R" in fm.rh_path.name
