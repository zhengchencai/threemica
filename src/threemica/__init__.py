"""threemica — Three.js HTML reports for MicaPipe surface maps."""

__version__ = "0.3.0"

from threemica.core import (
    FeatureMap,
    ResolvedRoot,
    build,
    find_surface,
    list_sessions,
    list_subjects,
    resolve_bids_root,
    run,
    scan_subject,
)

__all__ = [
    "__version__",
    "FeatureMap",
    "ResolvedRoot",
    "build",
    "find_surface",
    "list_sessions",
    "list_subjects",
    "resolve_bids_root",
    "run",
    "scan_subject",
]
