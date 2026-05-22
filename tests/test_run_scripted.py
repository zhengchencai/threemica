from threemica.core import run


def test_run_scripted_returns_html_paths(fake_bids, fake_scope):
    paths = run(
        bids_root=fake_bids,
        subjects=["sub-001"],
        sessions=["ses-01"],
        maps=["thickness"],
        resolution="fsLR-5k",
        interactive=False,
        scope=fake_scope,
    )
    assert len(paths) == 1
    assert paths[0].name == "sub-001_ses-01_space-fsLR-5k_desc-individual_report-cortical-thickness.html"
    assert paths[0].exists()


def test_run_scripted_multiple_subjects_and_maps(fake_bids, fake_scope):
    paths = run(
        bids_root=fake_bids,
        subjects=["sub-001", "sub-002"],
        sessions=None,
        maps=["thickness", "myelin"],
        resolution="fsLR-32k",
        interactive=False,
        scope=fake_scope,
    )
    names = sorted(p.name for p in paths)
    assert any("sub-001" in n and "thickness" in n for n in names)
    assert any("sub-002" in n and "myelin" in n for n in names)


def test_run_scripted_requires_subjects_when_non_interactive(fake_bids, fake_scope):
    import pytest
    with pytest.raises(ValueError, match="subjects"):
        run(
            bids_root=fake_bids,
            subjects=None,
            maps=["thickness"],
            resolution="fsLR-5k",
            interactive=False,
            scope=fake_scope,
        )
