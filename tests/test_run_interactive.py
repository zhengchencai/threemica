from threemica import core


def test_interactive_pipes_through_pickers(fake_bids, fake_scope, monkeypatch):
    monkeypatch.setattr(core._wizard, "pick_subjects", lambda c, default=None: ["sub-001"])
    monkeypatch.setattr(core._wizard, "pick_maps",     lambda c, default=None: ["thickness"])
    monkeypatch.setattr(core._wizard, "pick_resolution", lambda c, default=None: ["fsLR-5k"])
    monkeypatch.setattr(core._wizard, "pick_sessions",  lambda c, default=None: c)
    monkeypatch.setattr(core._wizard, "pick_smooth",    lambda default=None: None)
    monkeypatch.setattr(core._wizard, "pick_output",    lambda default: default)

    out = core.run(bids_root=fake_bids, interactive=True, scope=fake_scope)
    assert len(out) == 1
    assert "sub-001_ses-01_space-fsLR-5k" in out[0].name
    assert "thickness" in out[0].name


def test_interactive_cancellation_returns_empty(fake_bids, fake_scope, monkeypatch):
    monkeypatch.setattr(core._wizard, "pick_output", lambda default: default)
    monkeypatch.setattr(core._wizard, "pick_subjects", lambda *a, **k: [])
    out = core.run(bids_root=fake_bids, interactive=True, scope=fake_scope)
    assert out == []


def test_interactive_prompts_for_output_root(fake_bids, fake_scope, tmp_path, monkeypatch):
    selected_output = tmp_path / "reports"
    seen_defaults = []

    monkeypatch.setattr(core._wizard, "pick_subjects", lambda c, default=None: ["sub-001"])
    monkeypatch.setattr(core._wizard, "pick_maps",     lambda c, default=None: ["thickness"])
    monkeypatch.setattr(core._wizard, "pick_resolution", lambda c, default=None: ["fsLR-5k"])
    monkeypatch.setattr(core._wizard, "pick_sessions",  lambda c, default=None: c)
    monkeypatch.setattr(core._wizard, "pick_smooth",    lambda default=None: None)

    def pick_output(default):
        seen_defaults.append(default)
        return selected_output

    monkeypatch.setattr(core._wizard, "pick_output", pick_output)

    out = core.run(bids_root=fake_bids, interactive=True, scope=fake_scope)

    assert seen_defaults == [fake_bids]
    assert len(out) == 1
    assert out[0].is_relative_to(selected_output / "derivatives" / "threemica")
