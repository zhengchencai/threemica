"""Interactive pickers — isolated for easy mocking in tests."""
from __future__ import annotations

from typing import List, Optional

import questionary


_STYLE = questionary.Style([
    ("selected", "noreverse"),
    ("pointer", ""),
    ("highlighted", "noreverse"),
    ("answer", "fg:green"),
])


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
            questionary.Choice(
                s, value=s, checked=(default is None or s in default)
            )
            for s in candidates
        ],
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
            questionary.Choice(
                s, value=s, checked=(default is not None and s in default)
            )
            for s in candidates
        ],
        style=_STYLE,
    ).ask()
    return answer or []


def pick_resolution(
    candidates: List[str], default: Optional[str] = None
) -> Optional[str]:
    """Single-select resolution. Auto-picks when only one is offered."""
    if not candidates:
        return None
    if len(candidates) == 1:
        return candidates[0]
    return questionary.select(
        "Resolution:",
        choices=candidates,
        default=default,
        pointer=">",
        style=_STYLE,
    ).ask()
