"""Public Python API for threemica."""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class ResolvedRoot:
    """The MicaPipe derivatives root, plus optional preselected subject/session."""

    root: Path
    subject: Optional[str] = None
    session: Optional[str] = None


_MP_DIR_RE = re.compile(r"^micapipe(?:[._-].*)?$")
_SUB_RE = re.compile(r"^sub-")
_SES_RE = re.compile(r"^ses-")


def _is_micapipe_dir(p: Path) -> bool:
    return p.is_dir() and bool(_MP_DIR_RE.match(p.name))


def _find_micapipe_under(parent: Path) -> Optional[Path]:
    """If parent has a derivatives/ subdir containing one or more micapipe* dirs,
    return the lexically last one. Else None."""
    deriv = parent / "derivatives"
    if not deriv.is_dir():
        return None
    candidates = sorted(p for p in deriv.iterdir() if _is_micapipe_dir(p))
    return candidates[-1] if candidates else None


def resolve_micapipe_root(path: "str | Path | None" = None) -> ResolvedRoot:
    """Resolve a user-given path (or cwd) to a MicaPipe derivatives root.

    Rules (first match wins):
      1. path is inside derivatives/micapipe*/sub-XX/ses-YY -> root + sub + ses
      2. path is derivatives/micapipe*/sub-XX -> root + sub
      3. path is a derivatives/micapipe* dir -> root only
      4. path is a BIDS root (has derivatives/) -> pick latest micapipe*
      5. else raise FileNotFoundError
    """
    p = Path(path) if path is not None else Path.cwd()
    p = p.resolve()
    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {p}")

    # Walk up at most 3 levels to find a micapipe-* dir we sit inside
    candidate = p
    subject = None
    session = None
    for _ in range(3):
        if _is_micapipe_dir(candidate):
            return ResolvedRoot(root=candidate, subject=subject, session=session)
        # Record sub-/ses- pieces as we climb so we can preselect them
        if _SES_RE.match(candidate.name) and session is None:
            session = candidate.name
        elif _SUB_RE.match(candidate.name) and subject is None:
            subject = candidate.name
        if candidate.parent == candidate:
            break
        candidate = candidate.parent

    # path may be a BIDS root with derivatives/micapipe*
    mp = _find_micapipe_under(p)
    if mp is not None:
        return ResolvedRoot(root=mp)

    raise FileNotFoundError(
        f"Could not locate a MicaPipe derivatives root from {p}. "
        f"Expected a derivatives/micapipe* directory, a subject inside one, "
        f"or a BIDS root that contains derivatives/micapipe*."
    )


__all__ = ["ResolvedRoot", "resolve_micapipe_root"]


# ---------------------------------------------------------------------------
# FeatureMap dataclass + scan()
# ---------------------------------------------------------------------------

_MAP_FNAME_RE = re.compile(
    r"^sub-[^_]+(?:_ses-[^_]+)?"
    r"_hemi-(?P<hemi>[LR])"
    r"_surf-(?P<res>fsLR-5k|fsLR-32k)"
    r"_label-(?P<label>[^.]+)\.func\.gii$"
)


@dataclass(frozen=True)
class FeatureMap:
    """A LH/RH paired surface map at one resolution."""

    label: str
    resolution: str
    lh_path: Path
    rh_path: Path


def _scan_maps_dir(maps_dir: Path) -> list[FeatureMap]:
    """Return both-hemi FeatureMaps found in a single maps/ directory."""
    if not maps_dir.is_dir():
        return []
    by_key: dict[tuple, dict] = {}
    for f in sorted(maps_dir.iterdir()):
        m = _MAP_FNAME_RE.match(f.name)
        if not m:
            continue
        key = (m.group("label"), m.group("res"))
        by_key.setdefault(key, {})[m.group("hemi")] = f.resolve()
    out: list[FeatureMap] = []
    for (label, res), hemis in sorted(by_key.items()):
        if "L" in hemis and "R" in hemis:
            out.append(
                FeatureMap(
                    label=label,
                    resolution=res,
                    lh_path=hemis["L"],
                    rh_path=hemis["R"],
                )
            )
    return out


def scan(subject_dir: str | Path) -> dict[Optional[str], list[FeatureMap]]:
    """Scan one MicaPipe subject directory. Returns {session_or_None: [FeatureMap]}.

    Detects ses-* subdirectories. If absent, returns {None: [...]} for the
    single-session case.
    """
    sub_dir = Path(subject_dir).resolve()
    if not sub_dir.is_dir():
        raise FileNotFoundError(f"Subject directory does not exist: {sub_dir}")

    sessions = sorted(
        d.name for d in sub_dir.iterdir() if d.is_dir() and _SES_RE.match(d.name)
    )

    if not sessions:
        return {None: _scan_maps_dir(sub_dir / "maps")}
    return {ses: _scan_maps_dir(sub_dir / ses / "maps") for ses in sessions}


__all__ += ["FeatureMap", "scan"]
