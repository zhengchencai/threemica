from threemica.core import run


def test_run_scripted_returns_html_paths(fake_micapipe):
    paths = run(
        micapipe_root=fake_micapipe,
        subjects=["sub-001"],
        sessions=["ses-01"],
        maps=["thickness"],
        resolution="fsLR-5k",
        surface_type="template",
        interactive=False,
    )
    assert len(paths) == 1
    assert paths[0].name == "sub-001_ses-01_space-fsLR-5k_desc-template_report-thickness.html"
    assert paths[0].exists()


def test_run_scripted_multiple_subjects_and_maps(fake_micapipe):
    paths = run(
        micapipe_root=fake_micapipe,
        subjects=["sub-001", "sub-002"],
        sessions=None,           # all sessions per subject
        maps=["thickness", "myelin"],   # matched per-subject; missing maps silently skipped
        resolution="fsLR-32k",
        surface_type="template",
        interactive=False,
    )
    # sub-001 has thickness; sub-002 has myelin
    names = sorted(p.name for p in paths)
    assert any("sub-001" in n and "thickness" in n for n in names)
    assert any("sub-002" in n and "myelin" in n for n in names)


def test_run_scripted_requires_subjects_when_non_interactive(fake_micapipe):
    import pytest
    with pytest.raises(ValueError, match="subjects"):
        run(
            micapipe_root=fake_micapipe,
            subjects=None,
            maps=["thickness"],
            resolution="fsLR-5k",
            interactive=False,
        )
