import pytest
from pathlib import Path
from threemica.core import resolve_bids_root


def _make_bids(tmp_path: Path) -> Path:
    (tmp_path / "derivatives" / "micapipe_v0.2.0" / "sub-001" / "ses-01").mkdir(parents=True)
    return tmp_path


def test_path_is_bids_root(tmp_path):
    bids = _make_bids(tmp_path)
    result = resolve_bids_root(bids)
    assert result.root == bids


def test_path_is_subject_dir(tmp_path):
    bids = _make_bids(tmp_path)
    result = resolve_bids_root(bids / "derivatives" / "micapipe_v0.2.0" / "sub-001")
    assert result.root == bids
    assert result.subject == "sub-001"


def test_path_is_session_dir(tmp_path):
    bids = _make_bids(tmp_path)
    result = resolve_bids_root(
        bids / "derivatives" / "micapipe_v0.2.0" / "sub-001" / "ses-01"
    )
    assert result.root == bids
    assert result.subject == "sub-001"
    assert result.session == "ses-01"


def test_unrelated_path_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        resolve_bids_root(tmp_path / "nonexistent")


def test_none_uses_cwd(tmp_path, monkeypatch):
    bids = _make_bids(tmp_path)
    monkeypatch.chdir(bids)
    result = resolve_bids_root(None)
    assert result.root == bids
