import subprocess
import sys

from threemica import run


def test_e2e_real_subject_via_api(fake_bids, fake_scope):
    outputs = run(
        bids_root=fake_bids,
        subjects=["sub-001"],
        sessions=["ses-01"],
        maps=["thickness", "curv"],
        resolution="fsLR-5k",
        interactive=False,
        scope=fake_scope,
    )
    assert len(outputs) == 1
    html = outputs[0].read_text()
    assert "Cortical Thickness" in html
    assert "Curvature" in html


def test_e2e_cli_against_fixture(fake_bids):
    r = subprocess.run(
        [sys.executable, "-m", "threemica.cli", str(fake_bids / "nope")],
        capture_output=True, text=True, timeout=15,
    )
    assert r.returncode != 0
    msg = (r.stdout + r.stderr).lower()
    assert "does not exist" in msg or "could not locate" in msg
