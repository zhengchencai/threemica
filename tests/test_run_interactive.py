from threemica import core


def test_interactive_pipes_through_pickers(fake_micapipe, monkeypatch):
    # Stub each picker to return deterministic answers.
    monkeypatch.setattr(
        core._wizard, "pick_subjects",
        lambda candidates, default=None: ["sub-001"],
    )
    monkeypatch.setattr(
        core._wizard, "pick_maps",
        lambda candidates, default=None: ["thickness"],
    )
    monkeypatch.setattr(
        core._wizard, "pick_resolution",
        lambda candidates, default=None: ["fsLR-5k"],
    )
    monkeypatch.setattr(
        core._wizard, "pick_sessions",
        lambda candidates, default=None: candidates,
    )
    monkeypatch.setattr(core._wizard, "pick_smooth", lambda default=None: None)

    out = core.run(
        micapipe_root=fake_micapipe,
        interactive=True,
        surface_type="template",
    )
    assert len(out) == 1
    assert "sub-001_ses-01_space-fsLR-5k" in out[0].name
    assert "thickness" in out[0].name


def test_interactive_cancellation_returns_empty(fake_micapipe, monkeypatch):
    monkeypatch.setattr(core._wizard, "pick_subjects", lambda *a, **k: [])
    out = core.run(
        micapipe_root=fake_micapipe,
        interactive=True,
        surface_type="template",
    )
    assert out == []
