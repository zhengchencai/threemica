import shutil
import pytest

from threemica import resample


def test_module_imports():
    # Just verify the module is importable and exposes the expected names.
    assert hasattr(resample, "resample_metric_to_target")
    assert hasattr(resample, "resample_surface_to_target")


@pytest.mark.skipif(not shutil.which("wb_command"), reason="wb_command not on PATH")
def test_wb_command_available():
    # Sanity: when wb_command IS installed, version check should succeed.
    import subprocess
    out = subprocess.run(["wb_command", "-version"], capture_output=True, text=True)
    assert out.returncode == 0
