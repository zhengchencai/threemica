from threemica._scope import load_or_copy_scope, scope_path


def test_scope_file_lives_under_threemica_derivative(fake_bids):
    assert scope_path(fake_bids) == (
        fake_bids / "derivatives" / "threemica" / "threemica_scope.json"
    )


def test_scope_file_can_live_under_non_bids_output_root(tmp_path):
    output_root = tmp_path / "report-output"
    assert scope_path(output_root) == (
        output_root / "derivatives" / "threemica" / "threemica_scope.json"
    )


def test_load_or_copy_scope_does_not_write_to_output_root_derivatives(fake_bids):
    root_scope = fake_bids / "derivatives" / "threemica_scope.json"
    threemica_scope = fake_bids / "derivatives" / "threemica" / "threemica_scope.json"

    assert not root_scope.exists()
    assert not threemica_scope.exists()

    load_or_copy_scope(fake_bids)

    assert threemica_scope.exists()
    assert not root_scope.exists()
