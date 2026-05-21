"""Interactive pickers — isolated for easy mocking in tests."""
from __future__ import annotations

from typing import List, Optional

import questionary


_STYLE = questionary.Style([
    ("selected", "noreverse"),
    ("pointer", ""),
    ("highlighted", "noreverse"),
    ("answer", "fg:cyan"),
])


def _checked(s: str, default: Optional[List[str]]) -> bool:
    """Default-check-all when no default given; otherwise only items in default."""
    return s in default if default is not None else True


def pick_subjects(
    candidates: List[str], default: Optional[List[str]] = None
) -> List[str]:
    """Multi-select subjects. Returns [] if user cancels or selects none."""
    if not candidates:
        return []
    if len(candidates) == 1:
        return candidates  # auto-pick the only option
    answer = questionary.checkbox(
        "Subjects:",
        choices=[
            questionary.Choice(s, value=s, checked=_checked(s, default))
            for s in candidates
        ],
        pointer=">",
        style=_STYLE,
    ).ask()
    return answer or []


def pick_sessions(
    candidates: List[str], default: Optional[List[str]] = None
) -> List[str]:
    """Multi-select sessions. Returns [] if user cancels or selects none."""
    if not candidates:
        return []
    if len(candidates) == 1:
        return candidates
    answer = questionary.checkbox(
        "Sessions:",
        choices=[
            questionary.Choice(s, value=s, checked=_checked(s, default))
            for s in candidates
        ],
        pointer=">",
        style=_STYLE,
    ).ask()
    return answer or []


def pick_maps(
    candidates: List[str], default: Optional[List[str]] = None
) -> List[str]:
    """Multi-select feature-map labels."""
    if not candidates:
        return []
    answer = questionary.checkbox(
        "Feature maps:",
        choices=[
            questionary.Choice(s, value=s, checked=_checked(s, default))
            for s in candidates
        ],
        pointer=">",
        style=_STYLE,
    ).ask()
    return answer or []


def pick_smooth(default: Optional[int] = None) -> Optional[int]:
    """Prompt for surface smoothing FWHM in mm. 'NA' / empty → no smoothing."""
    raw = questionary.text(
        "Smoothing FWHM (mm), NA to skip:",
        default=str(default) if default is not None else "NA",
        style=_STYLE,
    ).ask()
    if raw is None:
        return None
    raw = raw.strip()
    if not raw or raw.upper() == "NA":
        return None
    try:
        val = int(raw)
    except ValueError:
        return None
    return val if val > 0 else None


def pick_resolution(
    candidates: List[str], default: Optional[List[str]] = None
) -> List[str]:
    """Multi-select resolution. Default-check-all; auto-picks when only one offered."""
    if not candidates:
        return []
    if len(candidates) == 1:
        return candidates
    answer = questionary.checkbox(
        "Resolution:",
        choices=[
            questionary.Choice(s, value=s, checked=_checked(s, default))
            for s in candidates
        ],
        pointer=">",
        style=_STYLE,
    ).ask()
    return answer or []
