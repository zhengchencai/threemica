from threemica._resources import bundle_root, viewer_template, viewer_js


def test_bundle_root_exists():
    root = bundle_root()
    assert root.is_dir()
    assert (root / "surfaces").is_dir()
    assert (root / "parcellations").is_dir()
    assert (root / "medial_wall").is_dir()
    assert (root / "parcelquery").is_dir()
    assert (root / "parcelsynth").is_dir()


def test_bundle_has_fslr_surfaces():
    root = bundle_root()
    assert (root / "surfaces" / "fsLR-5k.L.surf.gii").is_file()
    assert (root / "surfaces" / "fsLR-5k.R.surf.gii").is_file()


def test_viewer_files_exist():
    assert viewer_template().is_file()
    assert viewer_js().is_file()
    assert viewer_template().stat().st_size > 1000
    assert viewer_js().stat().st_size > 10000
