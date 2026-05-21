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


# ---------------------------------------------------------------------------
# build()
# ---------------------------------------------------------------------------

import json as _json

from threemica._resources import viewer_template, viewer_js
from threemica.builder import build_payload


_SUB_FROM_DIR_RE = re.compile(r"^sub-[^_/]+$")


def _slug(label: str) -> str:
    """Lowercase, dash-separated, alphanumerics only — for filename map slugs."""
    s = re.sub(r"[^a-zA-Z0-9]+", "-", label).strip("-").lower()
    return s or "map"


def _subject_label(subject_dir: Path) -> str:
    """Return 'sub-XXX' regardless of whether the caller passed sub-XXX or a path ending in it."""
    name = subject_dir.name
    if not _SUB_FROM_DIR_RE.match(name):
        raise ValueError(f"subject_dir must end in 'sub-XXX', got: {subject_dir}")
    return name


def build(
    subject_dir: str | Path,
    session: Optional[str],
    maps: list[FeatureMap],
    *,
    resolution: str = "fsLR-32k",
    surface_type: str = "individual",
    out_dir: Optional[Path] = None,
) -> Path:
    """Write one HTML report for one subject/session. Returns the output path."""
    if not maps:
        raise ValueError("build() requires at least one FeatureMap")
    sub_dir = Path(subject_dir).resolve()
    sub_label = _subject_label(sub_dir)

    # All maps must be at the requested resolution
    bad = [m for m in maps if m.resolution != resolution]
    if bad:
        raise ValueError(
            f"All maps must be at resolution={resolution}, "
            f"but got {[(m.label, m.resolution) for m in bad]}"
        )

    # Choose surface
    if surface_type == "template":
        from threemica._resources import bundle_root
        surf_root = bundle_root() / "surfaces"
        # Some resolutions ship as `.surf.gii`, others as `.midthickness.surf.gii`
        midL = surf_root / f"{resolution}.L.midthickness.surf.gii"
        midR = surf_root / f"{resolution}.R.midthickness.surf.gii"
        if not midL.exists():
            midL = surf_root / f"{resolution}.L.surf.gii"
            midR = surf_root / f"{resolution}.R.surf.gii"
        surf_lh, surf_rh = midL, midR
    else:  # individual
        # Look under <subject>/[<session>/]surf/ for midthickness
        surf_dir = (sub_dir / session / "surf") if session else (sub_dir / "surf")
        candidates_L = sorted(surf_dir.glob(f"*hemi-L*{resolution}*midthickness*.surf.gii"))
        candidates_R = sorted(surf_dir.glob(f"*hemi-R*{resolution}*midthickness*.surf.gii"))
        if not candidates_L or not candidates_R:
            raise FileNotFoundError(
                f"No individual midthickness surface for {resolution} in {surf_dir}"
            )
        surf_lh = candidates_L[0]
        surf_rh = candidates_R[0]

    # Output path
    if out_dir is None:
        out_dir = (sub_dir / session / "report") if session else (sub_dir / "report")
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    map_slug = "-".join(dict.fromkeys(_slug(m.label) for m in maps))
    base = sub_label + (f"_{session}" if session else "")
    fname = f"{base}_space-{resolution}_desc-{surface_type}_report-{map_slug}.html"
    out_html = out_dir / fname

    # Build the payload via the ported builder
    payload = build_payload(
        surf_lh=surf_lh,
        surf_rh=surf_rh,
        map_lhs=[m.lh_path for m in maps],
        map_rhs=[m.rh_path for m in maps],
        resolution=resolution,
        labels=[m.label for m in maps],
        sub_labels=[base] * len(maps),
        cb_labels=["Value"] * len(maps),
        colormaps=["plasma"] * len(maps),
        clims=[None] * len(maps),
        surface_type=surface_type,
    )

    # Assemble HTML from the bundled viewer
    template = viewer_template().read_text(encoding="utf-8")
    js_body = viewer_js().read_text(encoding="utf-8")
    title = f"{maps[0].label} — threemica"
    html = (
        template
        .replace("{{TITLE}}", title)
        .replace("{{THEME_CLASS}}", "")
        .replace("{{PAYLOAD_JSON}}", _json.dumps(payload))
        .replace("{{VIEWER_JS}}", js_body)
    )
    out_html.write_text(html, encoding="utf-8")
    return out_html


__all__ += ["build"]


def _select_maps_for(
    available: List[FeatureMap], labels: List[str], resolution: str
) -> List[FeatureMap]:
    """Pick FeatureMaps whose label is in `labels` AND whose resolution matches."""
    wanted = set(labels)
    return [m for m in available if m.label in wanted and m.resolution == resolution]


def run(
    micapipe_root: "str | Path | None" = None,
    *,
    subjects: Optional[List[str]] = None,
    sessions: Optional[List[str]] = None,
    maps: Optional[List[str]] = None,
    resolution: Optional[str] = None,
    surface_type: str = "individual",
    out_dir: Optional[Path] = None,
    interactive: bool = True,
) -> List[Path]:
    """End-to-end flow: resolve root → scan → (pick) → build.

    interactive=False is the scripted entry point; requires `subjects`,
    `maps`, and `resolution`. interactive=True opens questionary pickers
    for whatever is None (implemented in Task 9).
    """
    resolved = resolve_micapipe_root(micapipe_root)
    mp_root = resolved.root

    if not interactive:
        if not subjects:
            raise ValueError("subjects is required when interactive=False")
        if not maps:
            raise ValueError("maps is required when interactive=False")
        if not resolution:
            raise ValueError("resolution is required when interactive=False")
        return _run_scripted(
            mp_root=mp_root,
            subjects=subjects,
            sessions=sessions,
            map_labels=maps,
            resolution=resolution,
            surface_type=surface_type,
            out_dir=out_dir,
        )

    return _run_interactive(
        resolved=resolved,
        subjects=subjects,
        sessions=sessions,
        map_labels=maps,
        resolution=resolution,
        surface_type=surface_type,
        out_dir=out_dir,
    )


def _run_scripted(
    *,
    mp_root: Path,
    subjects: List[str],
    sessions: Optional[List[str]],
    map_labels: List[str],
    resolution: str,
    surface_type: str,
    out_dir: Optional[Path],
) -> List[Path]:
    outputs: List[Path] = []
    for sub in subjects:
        sub_dir = mp_root / sub
        if not sub_dir.is_dir():
            continue
        per_session = scan(sub_dir)
        for ses, available in per_session.items():
            if sessions is not None and ses not in sessions:
                continue
            picked = _select_maps_for(available, map_labels, resolution)
            if not picked:
                continue
            outputs.append(
                build(
                    subject_dir=sub_dir,
                    session=ses,
                    maps=picked,
                    resolution=resolution,
                    surface_type=surface_type,
                    out_dir=out_dir,
                )
            )
    return outputs


def _run_interactive(**_kwargs) -> List[Path]:
    """Placeholder — implemented in Task 9."""
    raise NotImplementedError("interactive=True is implemented in Task 9")


__all__ += ["run"]
