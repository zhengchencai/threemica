import subprocess
from pathlib import Path


def test_cli_help_runs():
    r = subprocess.run(
        ["threemica", "--help"], capture_output=True, text=True, timeout=15
    )
    assert r.returncode == 0
    assert "threemica" in r.stdout.lower()
    assert "path" in r.stdout.lower()


def test_cli_invokes_run(fake_bids, monkeypatch):
    from threemica import cli, core

    captured = {}

    def fake_run(bids_root=None, **kwargs):
        captured["bids_root"] = Path(bids_root) if bids_root else None
        captured["interactive"] = kwargs.get("interactive")
        return []

    monkeypatch.setattr(core, "run", fake_run)
    monkeypatch.setattr(cli, "_run_via_core", fake_run)
    cli.main([str(fake_bids)])
    assert captured["bids_root"] == fake_bids
    assert captured["interactive"] is True
