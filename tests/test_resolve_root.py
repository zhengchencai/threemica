import pytest
from pathlib import Path
from threemica.core import resolve_micapipe_root


def _make_mp(tmp_path: Path, name: str = "micapipe_v0.2.0") -> Path:
    """Build a minimal BIDS-ish tree: tmp_path/derivatives/<name>/sub-001/ses-01/maps."""
    mp = tmp_path / "derivatives" / name
    (mp / "sub-001" / "ses-01" / "maps").mkdir(parents=True)
    return mp


def test_path_is_micapipe_root(tmp_path):
    mp = _make_mp(tmp_path)
    result = resolve_micapipe_root(mp)
    assert result.root == mp
    assert result.subject is None and result.session is None


def test_path_is_subject_dir(tmp_path):
    mp = _make_mp(tmp_path)
    result = resolve_micapipe_root(mp / "sub-001")
    assert result.root == mp
    assert result.subject == "sub-001"
    assert result.session is None


def test_path_is_session_dir(tmp_path):
    mp = _make_mp(tmp_path)
    result = resolve_micapipe_root(mp / "sub-001" / "ses-01")
    assert result.root == mp
    assert result.subject == "sub-001"
    assert result.session == "ses-01"


def test_path_is_bids_root_single_micapipe(tmp_path):
    _make_mp(tmp_path)
    result = resolve_micapipe_root(tmp_path)
    assert result.root.name == "micapipe_v0.2.0"


def test_path_is_bids_root_picks_latest_when_multiple(tmp_path):
    _make_mp(tmp_path, "micapipe_v0.2.0")
    _make_mp(tmp_path, "micapipe_v0.2.3")
    result = resolve_micapipe_root(tmp_path)
    # "latest" by lexical sort — v0.2.3 > v0.2.0
    assert result.root.name == "micapipe_v0.2.3"


def test_unrelated_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve_micapipe_root(tmp_path / "nonexistent")


def test_none_uses_cwd(tmp_path, monkeypatch):
    mp = _make_mp(tmp_path)
    monkeypatch.chdir(mp)
    result = resolve_micapipe_root(None)
    assert result.root == mp
