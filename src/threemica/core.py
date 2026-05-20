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
