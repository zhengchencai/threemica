"""Public Python API for threemica."""
from __future__ import annotations

import json as _json
import re
import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

from threemica import _wizard
from threemica._resources import viewer_template, viewer_js
from threemica._scope import load_or_copy_scope
from threemica.builder import build_payload


_SUB_RE = re.compile(r"^sub-")
_SES_RE = re.compile(r"^ses-")


# ---------------------------------------------------------------------------
# BIDS root resolution
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class ResolvedRoot:
    """A BIDS root (parent of `derivatives/`), plus optional preselected sub/ses."""

    root: Path
    subject: Optional[str] = None
    session: Optional[str] = None


def resolve_bids_root(path: "str | Path | None" = None) -> ResolvedRoot:
    """Walk up from ``path`` (or cwd) until we find a folder with a `derivatives/`
    child. Record any `sub-XX` / `ses-YY` segments seen on the way up so the
    wizard can pre-select them.
    """
    p = (Path(path) if path is not None else Path.cwd()).resolve()
    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {p}")

    candidate = p
    subject: Optional[str] = None
    session: Optional[str] = None
    for _ in range(8):  # up to 8 levels up is plenty for any BIDS tree
        if (candidate / "derivatives").is_dir():
            return ResolvedRoot(root=candidate, subject=subject, session=session)
        if _SES_RE.match(candidate.name) and session is None:
            session = candidate.name
        elif _SUB_RE.match(candidate.name) and subject is None:
            subject = candidate.name
        if candidate.parent == candidate:
            break
        candidate = candidate.parent

    raise FileNotFoundError(
        f"Could not locate a BIDS root from {p}. "
        f"Expected a folder containing 'derivatives/'."
    )


__all__ = ["ResolvedRoot", "resolve_bids_root"]


# ---------------------------------------------------------------------------
# FeatureMap + scope-driven scan
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FeatureMap:
    """A LH/RH paired surface map at one resolution, from one scope entry."""

    label: str          # exact `_label-X.func.gii` value, == the scope tag
    resolution: str     # fsLR-5k or fsLR-32k
    derivative: str     # the derivative folder this came from
    subdir: str         # the subdir under <sub>/[ses]/
    lh_path: Path
    rh_path: Path
    display_label: str = ""  # what the report shows top-left (e.g. "Cortical Thickness")
    unit: str = ""           # colorbar unit (e.g. "mm")
    cmap: str = "pos-only"   # "pos-only" or "diverging"
    scale: float = 1.0       # multiply raw data by this before display (e.g. 0.001 for ms→s)
    smooth_method: str = "kernel"  # "kernel" or "dilate"


def _resolutions_supported() -> tuple:
    return ("fsLR-5k", "fsLR-32k")


def _file_matches(name: str, tag: str, hemi: str, resolution: str) -> bool:
    """Match either:
      A) micapipe-style ``_hemi-{H}_surf-{res}_label-{tag}.(func.)?gii``
      B) electroMICA-style ``_{tag}_hemi-{H}_..._surf-{res}_....gii``
    Both ``.gii`` and ``.func.gii`` are accepted as the file extension.
    """
    if not (name.endswith(".gii") or name.endswith(".func.gii")):
        return False
    if (f"_hemi-{hemi}_surf-{resolution}_label-{tag}.func.gii" in name
            or f"_hemi-{hemi}_surf-{resolution}_label-{tag}.gii" in name):
        return True
    if (f"_{tag}_hemi-{hemi}_" in name
            and f"_surf-{resolution}_" in name):
        return True
    return False


def _find_paired(
    maps_dir: Path, tag: str, resolution: str
) -> Optional[tuple[Path, Path]]:
    """Find LH+RH paired files in ``maps_dir`` for ``tag`` at ``resolution``.
    Raises if more than one match per hemisphere."""
    if not maps_dir.is_dir():
        return None
    lhs = [p for p in maps_dir.iterdir() if _file_matches(p.name, tag, "L", resolution)]
    rhs = [p for p in maps_dir.iterdir() if _file_matches(p.name, tag, "R", resolution)]
    if not lhs or not rhs:
        return None
    if len(lhs) > 1 or len(rhs) > 1:
        raise ValueError(
            f"Tag '{tag}' at {resolution} matches multiple files in {maps_dir}: "
            f"LH={[p.name for p in lhs]} RH={[p.name for p in rhs]}. "
            "Tighten the tag in threemica_scope.json."
        )
    return lhs[0].resolve(), rhs[0].resolve()


def list_sessions(bids_root: Path, scope: dict, subject: str) -> list[str]:
    """Return the union of `ses-*` folders found under any scope derivative
    for ``subject``."""
    found: set[str] = set()
    for deriv in scope:
        if deriv == "surface":
            continue
        sub_path = bids_root / "derivatives" / deriv / subject
        if not sub_path.is_dir():
            continue
        for d in sub_path.iterdir():
            if d.is_dir() and _SES_RE.match(d.name):
                found.add(d.name)
    return sorted(found)


def list_subjects(bids_root: Path, scope: dict) -> list[str]:
    """Return the union of `sub-*` folders across all scope derivatives."""
    found: set[str] = set()
    for deriv in scope:
        if deriv == "surface":
            continue
        deriv_path = bids_root / "derivatives" / deriv
        if not deriv_path.is_dir():
            continue
        for d in deriv_path.iterdir():
            if d.is_dir() and _SUB_RE.match(d.name):
                found.add(d.name)
    return sorted(found)


def scan_subject(
    bids_root: Path, scope: dict, subject: str, session: Optional[str]
) -> list[FeatureMap]:
    """Return every FeatureMap found for ``subject``/``session`` under scope.

    Expects a normalized scope (tags are dicts with `tag/label/unit/cmap`).
    """
    out: list[FeatureMap] = []
    for deriv, spec in scope.items():
        if deriv == "surface":
            continue
        base = bids_root / "derivatives" / deriv / subject
        if session:
            base = base / session
        if not base.is_dir():
            continue
        for subdir, tags in spec.items():
            maps_dir = base / subdir
            for entry in tags:
                tag = entry["tag"]
                for res in _resolutions_supported():
                    paired = _find_paired(maps_dir, tag, res)
                    if paired is None:
                        continue
                    out.append(FeatureMap(
                        label=tag, resolution=res,
                        derivative=deriv, subdir=subdir,
                        lh_path=paired[0], rh_path=paired[1],
                        display_label=entry.get("label", tag),
                        unit=entry.get("unit", ""),
                        cmap=entry.get("cmap", "pos-only"),
                        scale=float(entry.get("scale", 1.0)),
                        smooth_method=entry.get("smooth_method", "kernel"),
                    ))
    return out


def find_surface(
    bids_root: Path, scope: dict, subject: str, session: Optional[str],
    resolution: str, hemi: str,
) -> Path:
    """Locate the midthickness surface per the scope's `surface` block."""
    if "surface" not in scope:
        raise KeyError("threemica_scope.json missing 'surface' block")
    spec = scope["surface"]
    base = bids_root / "derivatives" / spec["derivative"] / subject
    if session:
        base = base / session
    surf_dir = base / spec["subdir"]
    label = spec.get("label", "midthickness")
    H = hemi.upper()
    pattern = f"*hemi-{H}*surf-{resolution}*label-{label}.surf.gii"
    candidates = sorted(surf_dir.glob(pattern))
    if not candidates:
        raise FileNotFoundError(
            f"No midthickness surface for {subject} {session or ''} {resolution} {H} "
            f"under {surf_dir} (pattern {pattern})"
        )
    if len(candidates) > 1:
        raise ValueError(
            f"Multiple midthickness surfaces match in {surf_dir}: "
            f"{[p.name for p in candidates]}"
        )
    return candidates[0]


__all__ += ["FeatureMap", "scan_subject", "list_subjects", "list_sessions", "find_surface"]


# ---------------------------------------------------------------------------
# build()
# ---------------------------------------------------------------------------

def _slug(label: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "-", label).strip("-").lower()
    return s or "map"


def build(
    bids_root: Path,
    scope: dict,
    subject: str,
    session: Optional[str],
    maps: list[FeatureMap],
    *,
    resolution: str = "fsLR-32k",
    out_dir: Optional[Path] = None,
    smooth_mm: Optional[int] = None,
) -> Path:
    """Write one HTML report for one subject/session/resolution."""
    if not maps:
        raise ValueError("build() requires at least one FeatureMap")
    bad = [m for m in maps if m.resolution != resolution]
    if bad:
        raise ValueError(
            f"All maps must be at resolution={resolution}, "
            f"got {[(m.label, m.resolution) for m in bad]}"
        )

    surf_lh = find_surface(bids_root, scope, subject, session, resolution, "L")
    surf_rh = find_surface(bids_root, scope, subject, session, resolution, "R")

    if out_dir is None:
        out_dir = bids_root / "derivatives" / "threemica" / subject
        if session:
            out_dir = out_dir / session
    out_dir = Path(out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    base = subject + (f"_{session}" if session else "")

    # Optional smoothing
    map_lhs = [m.lh_path for m in maps]
    map_rhs = [m.rh_path for m in maps]
    tmp_dir: Optional[Path] = None
    if smooth_mm:
        import nibabel as nib
        from threemica._smoothing import smooth_map, dilate_map, write_cortex_mask_gii
        # Approximate average mesh edge length per resolution (mm).
        _EDGE_MM = {"fsLR-32k": 3.0, "fsLR-5k": 7.0}
        edge_mm = _EDGE_MM.get(resolution, 3.0)
        hops = max(1, round(smooth_mm / edge_mm))

        tmp_dir = out_dir / "_tmp"
        tmp_dir.mkdir(exist_ok=True)
        n_lh = len(nib.load(str(surf_lh)).agg_data("pointset"))
        n_rh = len(nib.load(str(surf_rh)).agg_data("pointset"))
        mask_lh = write_cortex_mask_gii(resolution, "lh", n_lh, tmp_dir / f"cortex_mask_{resolution}_lh.shape.gii")
        mask_rh = write_cortex_mask_gii(resolution, "rh", n_rh, tmp_dir / f"cortex_mask_{resolution}_rh.shape.gii")
        smoothed_lhs, smoothed_rhs = [], []
        print(f"[threemica] Smoothing {len(maps)} map(s) at FWHM={smooth_mm}mm "
              f"(dilate hops={hops}) on {resolution} for {base} …", flush=True)
        for m in maps:
            out_lh = tmp_dir / f"{m.lh_path.stem}_smooth-{smooth_mm}mm.func.gii"
            out_rh = tmp_dir / f"{m.rh_path.stem}_smooth-{smooth_mm}mm.func.gii"
            method = m.smooth_method
            print(f"  · {m.label} L/R ({method}) …", flush=True)
            if method == "dilate":
                dilate_map(surf_lh, m.lh_path, out_lh, hops)
                dilate_map(surf_rh, m.rh_path, out_rh, hops)
            else:  # kernel (default)
                smooth_map(surf_lh, m.lh_path, out_lh, smooth_mm, mask_lh)
                smooth_map(surf_rh, m.rh_path, out_rh, smooth_mm, mask_rh)
            smoothed_lhs.append(out_lh)
            smoothed_rhs.append(out_rh)
        map_lhs, map_rhs = smoothed_lhs, smoothed_rhs

    # Sub-label under top-left title
    sub_parts = [subject]
    if session:
        sub_parts.append(session)
    sub_parts.append(f"smooth {smooth_mm}mm" if smooth_mm else "smooth NA")
    sub_label_str = " · ".join(sub_parts)

    nice_labels = [m.display_label or m.label for m in maps]
    cb_labels = [m.unit for m in maps]
    cmap_types = [m.cmap for m in maps]
    scales = [m.scale for m in maps]

    # Use the scope's friendly label for the filename, not the raw file tag.
    map_slug = "-".join(dict.fromkeys(
        _slug(m.display_label or m.label) for m in maps
    ))
    smooth_tag = f"_smooth-{smooth_mm}mm" if smooth_mm else ""
    fname = (
        f"{base}_space-{resolution}_desc-individual{smooth_tag}"
        f"_report-{map_slug}.html"
    )
    out_html = out_dir / fname

    payload = build_payload(
        surf_lh=surf_lh, surf_rh=surf_rh,
        map_lhs=map_lhs, map_rhs=map_rhs,
        resolution=resolution,
        labels=nice_labels,
        sub_labels=[sub_label_str] * len(maps),
        cb_labels=cb_labels,
        colormaps=cmap_types,
        clims=[None] * len(maps),
        surface_type="individual",
        cmap_types=cmap_types,
        scales=scales,
    )

    template = viewer_template().read_text(encoding="utf-8")
    js_body = viewer_js().read_text(encoding="utf-8")
    title = f"{nice_labels[0]} — threemica"
    html = (
        template
        .replace("{{TITLE}}", title)
        .replace("{{THEME_CLASS}}", "")
        .replace("{{PAYLOAD_JSON}}", _json.dumps(payload))
        .replace("{{VIEWER_JS}}", js_body)
    )
    out_html.write_text(html, encoding="utf-8")

    if tmp_dir is not None:
        shutil.rmtree(tmp_dir, ignore_errors=True)

    return out_html


__all__ += ["build"]


# ---------------------------------------------------------------------------
# run()
# ---------------------------------------------------------------------------

def _as_resolutions(value) -> Optional[List[str]]:
    if value is None:
        return None
    if isinstance(value, str):
        return [value]
    return list(value)


def run(
    bids_root: "str | Path | None" = None,
    *,
    subjects: Optional[List[str]] = None,
    sessions: Optional[List[str]] = None,
    maps: Optional[List[str]] = None,
    resolution: "Optional[str | List[str]]" = None,
    output_root: Optional[Path] = None,
    smooth_mm: Optional[int] = None,
    interactive: bool = True,
    scope: Optional[Dict[str, Any]] = None,
) -> List[Path]:
    """End-to-end. ``bids_root`` defaults to cwd; resolved by walking up
    to find a `derivatives/` child.

    ``output_root`` is the parent directory under which reports land at
    ``<output_root>/threemica/sub-XX/[ses-YY]/<file>.html``. Default is
    ``<BIDS>/derivatives``.
    """
    resolved = resolve_bids_root(bids_root)
    root = resolved.root
    if scope is None:
        scope = load_or_copy_scope(root)
    resolutions = _as_resolutions(resolution)
    eff_root = Path(output_root) if output_root is not None else (root / "derivatives")
    print(f"[threemica] Output: {eff_root}/threemica/sub-XX/[ses-YY]/", flush=True)

    if not interactive:
        if not subjects:
            raise ValueError("subjects is required when interactive=False")
        if not maps:
            raise ValueError("maps is required when interactive=False")
        if not resolutions:
            raise ValueError("resolution is required when interactive=False")
        return _run_scripted(
            bids_root=root, scope=scope,
            subjects=subjects, sessions=sessions,
            map_labels=maps, resolutions=resolutions,
            output_root=eff_root, smooth_mm=smooth_mm,
        )

    return _run_interactive(
        bids_root=root, scope=scope, resolved=resolved,
        subjects=subjects, sessions=sessions,
        map_labels=maps, resolutions=resolutions,
        output_root=eff_root, smooth_mm=smooth_mm,
    )


def _run_scripted(
    *,
    bids_root: Path, scope: dict,
    subjects: List[str], sessions: Optional[List[str]],
    map_labels: List[str], resolutions: List[str],
    output_root: Path, smooth_mm: Optional[int],
) -> List[Path]:
    outputs: List[Path] = []
    wanted_labels = set(map_labels)
    for sub in subjects:
        ses_list = list_sessions(bids_root, scope, sub) or [None]
        for ses in ses_list:
            if sessions is not None and ses not in sessions:
                continue
            available = scan_subject(bids_root, scope, sub, ses)
            for res in resolutions:
                picked = [m for m in available
                          if m.resolution == res and m.label in wanted_labels]
                if not picked:
                    continue
                this_out = output_root / "threemica" / sub
                if ses:
                    this_out = this_out / ses
                outputs.append(build(
                    bids_root=bids_root, scope=scope,
                    subject=sub, session=ses, maps=picked,
                    resolution=res, out_dir=this_out, smooth_mm=smooth_mm,
                ))
    return outputs


def _run_interactive(
    *,
    bids_root: Path, scope: dict, resolved: ResolvedRoot,
    subjects: Optional[List[str]], sessions: Optional[List[str]],
    map_labels: Optional[List[str]], resolutions: Optional[List[str]],
    output_root: Path, smooth_mm: Optional[int],
) -> List[Path]:
    all_subjects = list_subjects(bids_root, scope)
    if subjects is None:
        # Default: nothing pre-checked (user picks intentionally). If the
        # caller cd'd into a specific subject, that one stays pre-selected.
        default = [resolved.subject] if resolved.subject else []
        subjects = _wizard.pick_subjects(all_subjects, default=default)
    if not subjects:
        return []

    # Scan all selected subjects so we can offer the union of sessions / labels / res
    per_subject: Dict[str, Dict[Optional[str], list[FeatureMap]]] = {}
    for sub in subjects:
        ses_list = list_sessions(bids_root, scope, sub) or [None]
        per_subject[sub] = {ses: scan_subject(bids_root, scope, sub, ses) for ses in ses_list}

    session_candidates = sorted({
        ses for per_ses in per_subject.values() for ses in per_ses.keys() if ses is not None
    })
    if sessions is None and session_candidates:
        default = [resolved.session] if resolved.session else None
        sessions = _wizard.pick_sessions(session_candidates, default=default)
        if not sessions:
            return []

    # Available (label, resolution) across what was scanned
    all_pairs: set[tuple[str, str]] = set()
    for per_ses in per_subject.values():
        for ses, fms in per_ses.items():
            if sessions is not None and ses not in sessions:
                continue
            for fm in fms:
                all_pairs.add((fm.label, fm.resolution))
    if not all_pairs:
        return []

    if resolutions is None:
        res_candidates = sorted({r for _, r in all_pairs})
        # Default to fsLR-32k only (the visualization standard) when available
        default = ["fsLR-32k"] if "fsLR-32k" in res_candidates else None
        resolutions = _wizard.pick_resolution(res_candidates, default=default)
    if not resolutions:
        return []

    label_candidates = sorted({lab for lab, r in all_pairs if r in resolutions})
    if map_labels is None:
        map_labels = _wizard.pick_maps(label_candidates)
    if not map_labels:
        return []

    if smooth_mm is None:
        smooth_mm = _wizard.pick_smooth()

    return _run_scripted(
        bids_root=bids_root, scope=scope,
        subjects=subjects, sessions=sessions,
        map_labels=map_labels, resolutions=resolutions,
        output_root=output_root, smooth_mm=smooth_mm,
    )


__all__ += ["run"]
