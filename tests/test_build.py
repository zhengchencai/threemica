from threemica.core import build, scan_subject


def test_build_writes_html_with_expected_filename(fake_bids, fake_scope):
    fms = scan_subject(fake_bids, fake_scope, "sub-001", "ses-01")
    picked = [m for m in fms if m.label == "thickness" and m.resolution == "fsLR-5k"]
    assert picked, "fixture should produce thickness@fsLR-5k"
    out = build(
        bids_root=fake_bids, scope=fake_scope,
        subject="sub-001", session="ses-01",
        maps=picked, resolution="fsLR-5k",
    )
    assert out.exists()
    expected_dir = fake_bids / "derivatives" / "threemica" / "sub-001" / "ses-01"
    assert out.parent == expected_dir
    assert out.name == "sub-001_ses-01_space-fsLR-5k_desc-individual_report-thickness.html"
    text = out.read_text()
    assert "<html" in text.lower()
    assert '"maps"' in text


def test_build_with_session_filename(fake_bids, fake_scope):
    fms = scan_subject(fake_bids, fake_scope, "sub-001", "ses-01")
    picked = [m for m in fms if m.label == "curv" and m.resolution == "fsLR-5k"]
    out = build(
        bids_root=fake_bids, scope=fake_scope,
        subject="sub-001", session="ses-01",
        maps=picked, resolution="fsLR-5k",
    )
    assert out.name == "sub-001_ses-01_space-fsLR-5k_desc-individual_report-curv.html"


def test_build_multi_map_slug(fake_bids, fake_scope):
    fms = scan_subject(fake_bids, fake_scope, "sub-001", "ses-01")
    picked = [m for m in fms if m.resolution == "fsLR-5k" and m.label in ("thickness", "curv")]
    assert len(picked) == 2
    out = build(
        bids_root=fake_bids, scope=fake_scope,
        subject="sub-001", session="ses-01",
        maps=picked, resolution="fsLR-5k",
    )
    assert "report-thickness-curv.html" in out.name or "report-curv-thickness.html" in out.name
