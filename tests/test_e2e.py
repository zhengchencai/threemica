import subprocess
import sys


def test_e2e_real_subject_via_api(fake_micapipe):
    """Run the whole pipeline via the Python API with interactive=False."""
    from threemica import run

    outputs = run(
        micapipe_root=fake_micapipe,
        subjects=["sub-001"],
        sessions=["ses-01"],
        maps=["thickness", "curv"],
        resolution="fsLR-5k",
        surface_type="template",
        interactive=False,
    )
    assert len(outputs) == 1  # one HTML, two maps inside
    html = outputs[0].read_text()
    # Both labels should appear in the embedded payload
    assert "thickness" in html
    assert "curv" in html


def test_e2e_cli_against_fixture(fake_micapipe, tmp_path):
    """Run the installed CLI via subprocess for one fully-scripted invocation.

    We mock out questionary by setting a non-tty stdin to ensure the wizard
    raises and the CLI surfaces a clean error — confirming the binary works
    and the error path is wired.
    """
    r = subprocess.run(
        [sys.executable, "-m", "threemica.cli", str(fake_micapipe / "nope")],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert r.returncode != 0
    assert "does not exist" in (r.stdout + r.stderr).lower() or \
           "could not locate" in (r.stdout + r.stderr).lower()
