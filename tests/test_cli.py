import subprocess
import sys
from pathlib import Path

PKG = Path(__file__).resolve().parents[1] / "src" / "threemica"


def test_cli_help_runs():
    r = subprocess.run(
        ["threemica", "--help"], capture_output=True, text=True, timeout=15
    )
    assert r.returncode == 0
    assert "threemica" in r.stdout.lower()
    assert "path" in r.stdout.lower()


def test_cli_invokes_run(fake_micapipe, monkeypatch):
    """When called from within a MicaPipe root, cli.main calls core.run()."""
    from threemica import cli, core

    captured = {}

    def fake_run(micapipe_root=None, **kwargs):
        captured["micapipe_root"] = Path(micapipe_root) if micapipe_root else None
        captured["interactive"] = kwargs.get("interactive")
        return []

    monkeypatch.setattr(core, "run", fake_run)
    monkeypatch.setattr(cli, "_run_via_core", fake_run)

    # Pass the fake_micapipe explicitly as the positional arg
    cli.main([str(fake_micapipe)])
    assert captured["micapipe_root"] == fake_micapipe
    assert captured["interactive"] is True
