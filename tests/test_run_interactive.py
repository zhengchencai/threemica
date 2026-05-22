from threemica import core


def test_interactive_pipes_through_pickers(fake_bids, fake_scope, monkeypatch):
    monkeypatch.setattr(core._wizard, "pick_subjects", lambda c, default=None: ["sub-001"])
    monkeypatch.setattr(core._wizard, "pick_maps",     lambda c, default=None: ["thickness"])
    monkeypatch.setattr(core._wizard, "pick_resolution", lambda c, default=None: ["fsLR-5k"])
    monkeypatch.setattr(core._wizard, "pick_sessions",  lambda c, default=None: c)
    monkeypatch.setattr(core._wizard, "pick_smooth",    lambda default=None: None)

    out = core.run(bids_root=fake_bids, interactive=True, scope=fake_scope)
    assert len(out) == 1
    assert "sub-001_ses-01_space-fsLR-5k" in out[0].name
    assert "thickness" in out[0].name


def test_interactive_cancellation_returns_empty(fake_bids, fake_scope, monkeypatch):
    monkeypatch.setattr(core._wizard, "pick_subjects", lambda *a, **k: [])
    out = core.run(bids_root=fake_bids, interactive=True, scope=fake_scope)
    assert out == []
