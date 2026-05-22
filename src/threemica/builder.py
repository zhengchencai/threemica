"""Build the JSON/base64 payload for the report viewer HTML.

Reads:
  - subject surface (midthickness + inflated from the bundle at the given resolution)
  - subject map (.func.gii, LH + RH)
  - Yale-696 label GIFTI (from bundle parcellations/)
  - ParcelQuery / Parcelsynth CSVs (from bundle)

Returns a payload dict ready for json.dumps(), to be injected into report_template.html.
"""
from __future__ import annotations

import base64
import json
from pathlib import Path
from typing import List, Optional

import nibabel as nib
import numpy as np
import pandas as pd

from threemica._resources import bundle_root as _bundle_root

_BUNDLE = _bundle_root()
_SURF_TMPL = _BUNDLE / "surfaces"
_PARC = _BUNDLE / "parcellations"
_MW = _BUNDLE / "medial_wall"
_PQ = _BUNDLE / "parcelquery" / "parcelquery_activations_functionalterms.csv"
_PS = _BUNDLE / "parcelsynth" / "parcelsynth_activations_functionalterms.csv"

TOP_N = 20

# Resolution → tag used in the template parcellation filenames
_PARC_TAG = {"fsLR-5k": "fsLR-5k", "fsLR-32k": "conte69"}
# Resolution → inflated template surface filename stem
_INFL_STEM = {
    "fsLR-5k":  "fsLR-5k.{H}.inflated.surf.gii",
    "fsLR-32k": "fsLR-32k.{H}.inflated.surf.gii",
}
_SPHERE_STEM = {
    "fsLR-5k":  "fsLR-5k.{H}.sphere.surf.gii",
    "fsLR-32k": "fsLR-32k.{H}.sphere.surf.gii",
}

# UI map settings dictionary: maps a substring match in the filename to a UI label and colormap type
# Type can be "pos-only" (e.g. plasma) or "diverging" (e.g. coolwarm)
MAP_SETTINGS = {
    # Structural
    "thickness": {"label": "Cortical Thickness", "cmap_type": "pos-only", "cb_label": "mm"},
    "curvature": {"label": "Curvature", "cmap_type": "diverging", "cb_label": "1/mm"},
    "curv":      {"label": "Curvature", "cmap_type": "diverging", "cb_label": "1/mm"},
    "myelin":    {"label": "Myelin Mapping", "cmap_type": "pos-only", "cb_label": "T1w/T2w"},
    "sulc":      {"label": "Sulcal Depth", "cmap_type": "diverging", "cb_label": "mm"},
    "flair":     {"label": "FLAIR", "cmap_type": "pos-only", "cb_label": "AU"},
    "t1map":     {"label": "T1 (qMRI)", "cmap_type": "pos-only", "cb_label": "ms"},
    "adc":       {"label": "ADC", "cmap_type": "pos-only", "cb_label": "mm²/s"},
    "fa":        {"label": "FA", "cmap_type": "pos-only", "cb_label": "FA"},

    # Functional
    "bold":      {"label": "fMRI (BOLD)", "cmap_type": "diverging", "cb_label": "AU"},
    "reho":      {"label": "Regional Homogeneity (ReHo)", "cmap_type": "pos-only", "cb_label": "ReHo"},
    "alff":      {"label": "ALFF", "cmap_type": "pos-only", "cb_label": "ALFF"},
    "fc":        {"label": "Functional Connectivity", "cmap_type": "diverging", "cb_label": "r"},

    # PET Tracers
    "mk6240":    {"label": "Tau-PET", "cmap_type": "pos-only", "cb_label": "SUVR"},
    "av1451":    {"label": "Tau-PET", "cmap_type": "pos-only", "cb_label": "SUVR"},
    "flortaucipir": {"label": "Tau-PET", "cmap_type": "pos-only", "cb_label": "SUVR"},
    "fdg":       {"label": "FDG-PET", "cmap_type": "pos-only", "cb_label": "SUVR"},
    "pib":       {"label": "Amyloid-PET", "cmap_type": "pos-only", "cb_label": "SUVR"},
    "ucbj":      {"label": "SV2A-PET", "cmap_type": "pos-only", "cb_label": "SUVR"},

    # Statistical Maps
    "zstat":     {"label": "Z-map", "cmap_type": "diverging", "cb_label": "z"},
    "tstat":     {"label": "T-map", "cmap_type": "diverging", "cb_label": "t"},
}

def guess_map_settings(filename: str) -> tuple[str, str]:
    """Fallback logic to infer label and colormap from filename."""
    fn_lower = filename.lower().replace("midthickness", "")
    for key, settings in MAP_SETTINGS.items():
        if key in fn_lower:
            return settings["label"], settings["cmap_type"]
    return "Map", "pos-only"


def guess_cb_label(filename: str) -> str:
    """Look up the colorbar unit label for a map filename (defaults to 'Value')."""
    fn_lower = filename.lower().replace("midthickness", "")
    for key, settings in MAP_SETTINGS.items():
        if key in fn_lower:
            return settings.get("cb_label", "Value")
    return "Value"


def guess_label(filename: str) -> str:
    """Look up the friendly map label (defaults to 'Map')."""
    return guess_map_settings(filename)[0]


def _b64(arr: np.ndarray, dtype) -> str:
    return base64.b64encode(arr.astype(dtype).ravel(order="C").tobytes()).decode()


def _vertex_normals(coords: np.ndarray, faces: np.ndarray) -> np.ndarray:
    v0, v1, v2 = coords[faces[:, 0]], coords[faces[:, 1]], coords[faces[:, 2]]
    fn = np.cross(v1 - v0, v2 - v0)
    norms = np.linalg.norm(fn, axis=1, keepdims=True)
    fn /= norms + 1e-12
    n = np.zeros_like(coords)
    for i in range(3):
        np.add.at(n, faces[:, i], fn)
    n /= np.linalg.norm(n, axis=1, keepdims=True) + 1e-12
    return n.astype(np.float32)


def _load_surf(path: Path):
    gii = nib.load(path)
    coords = gii.agg_data("pointset").astype(np.float32)
    faces  = gii.agg_data("triangle").astype(np.uint32)
    return coords, faces


def _rigid_align(source: np.ndarray, target: np.ndarray) -> np.ndarray:
    """Procrustes rigid alignment of source point cloud to target point cloud."""
    c_s = source.mean(axis=0)
    c_t = target.mean(axis=0)
    S = source - c_s
    T = target - c_t
    H = S.T @ T
    U, _, Vt = np.linalg.svd(H)
    R = Vt.T @ U.T
    if np.linalg.det(R) < 0:
        Vt[2, :] *= -1
        R = Vt.T @ U.T
    return (S @ R.T) + c_t


def _per_roi_top_n(csv_path: Path, n_rois: int, top_n: int) -> List[List[List]]:
    df = pd.read_csv(csv_path)
    df = df.iloc[:n_rois]
    terms  = np.asarray(df.columns)
    values = df.to_numpy()
    out: List[List[List]] = []
    for row in values:
        pos = np.where(row > 0)[0]
        if len(pos) == 0:
            out.append([])
            continue
        idx = pos[np.argsort(-row[pos])][:top_n]
        out.append([[str(terms[i]), round(float(row[i]), 2)] for i in idx])
    return out


def build_payload(
    surf_lh: Path,
    surf_rh: Path,
    map_lhs: list,
    map_rhs: list,
    resolution: str,
    labels: list,
    sub_labels: list,
    cb_labels: list,
    colormaps: list,
    clims: list,
    surface_type: str,
    cmap_types: list | None = None,
    scales: list | None = None,
) -> dict:
    """Assemble the full JSON payload dict for the viewer.
    """
    print(f"[report_builder] Loading surfaces …")
    lh_mid_coords, lh_faces = _load_surf(surf_lh)
    rh_mid_coords, rh_faces = _load_surf(surf_rh)
    n_lh = len(lh_mid_coords)
    n_rh = len(rh_mid_coords)

    # Rigidly align the individual's mid surfaces to the template's mid surfaces
    # so that morphing to template inflated/sphere doesn't cause rotational "nodding".
    if resolution == "fsLR-5k":
        t_lh = nib.load(_SURF_TMPL / "fsLR-5k.L.surf.gii").agg_data("pointset").astype(np.float32)
        t_rh = nib.load(_SURF_TMPL / "fsLR-5k.R.surf.gii").agg_data("pointset").astype(np.float32)
    else:
        t_lh = nib.load(_SURF_TMPL / f"{resolution}.L.midthickness.surf.gii").agg_data("pointset").astype(np.float32)
        t_rh = nib.load(_SURF_TMPL / f"{resolution}.R.midthickness.surf.gii").agg_data("pointset").astype(np.float32)

    source_all = np.vstack([lh_mid_coords, rh_mid_coords])
    target_all = np.vstack([t_lh, t_rh])
    aligned_all = _rigid_align(source_all, target_all)
    lh_mid_coords = aligned_all[:n_lh].astype(np.float32)
    rh_mid_coords = aligned_all[n_lh:].astype(np.float32)

    # Template inflated + sphere surfaces for morphing
    infl_lh_coords = nib.load(
        _SURF_TMPL / _INFL_STEM[resolution].format(H="L")
    ).agg_data("pointset").astype(np.float32)
    infl_rh_coords = nib.load(
        _SURF_TMPL / _INFL_STEM[resolution].format(H="R")
    ).agg_data("pointset").astype(np.float32)

    sphere_lh_coords = nib.load(
        _SURF_TMPL / _SPHERE_STEM[resolution].format(H="L")
    ).agg_data("pointset").astype(np.float32)
    sphere_rh_coords = nib.load(
        _SURF_TMPL / _SPHERE_STEM[resolution].format(H="R")
    ).agg_data("pointset").astype(np.float32)

    print(f"[report_builder] Loading maps …")
    # Cortex mask (True = cortex, False = medial wall). Used to compute robust
    # vmin/vmax that aren't dragged by medial-wall zeros.
    mw_lh = np.load(_MW / f"medial_wall_{resolution}_lh.npy")
    mw_rh = np.load(_MW / f"medial_wall_{resolution}_rh.npy")
    cortex_lh = np.ones(n_lh, dtype=bool); cortex_lh[mw_lh] = False
    cortex_rh = np.ones(n_rh, dtype=bool); cortex_rh[mw_rh] = False

    maps_data = []
    for i in range(len(map_lhs)):
        map_lh_vals = nib.load(map_lhs[i]).darrays[0].data.astype(np.float32)
        map_rh_vals = nib.load(map_rhs[i]).darrays[0].data.astype(np.float32)

        if len(map_lh_vals) != n_lh or len(map_rh_vals) != n_rh:
            raise RuntimeError(f"Map vertex count mismatch in map {i}")

        scale = float(scales[i]) if (scales and i < len(scales)) else 1.0
        if scale != 1.0:
            map_lh_vals = map_lh_vals * scale
            map_rh_vals = map_rh_vals * scale

        # Cortex-only values for robust range; ignore NaN + medial wall.
        cortex_vals = np.concatenate([map_lh_vals[cortex_lh], map_rh_vals[cortex_rh]])
        cortex_vals = cortex_vals[np.isfinite(cortex_vals)]

        inferred_label, inferred_cmap_type = guess_map_settings(map_lhs[i].name)

        final_label = labels[i] if (labels and i < len(labels) and labels[i]) else inferred_label
        final_cmap = (
            cmap_types[i] if (cmap_types and i < len(cmap_types) and cmap_types[i])
            else inferred_cmap_type
        )

        if clims[i]:
            vmin = float(clims[i][0])
            vmax = float(clims[i][1])
        elif final_cmap == "diverging":
            # Symmetric around 0 at max(|cortex values|).
            m = max(abs(float(np.nanmin(cortex_vals))),
                    abs(float(np.nanmax(cortex_vals)))) if cortex_vals.size else 1.0
            vmin, vmax = -m, m
        else:  # pos-only — full data range of cortex values
            if cortex_vals.size:
                vmin = float(np.nanmin(cortex_vals))
                vmax = float(np.nanmax(cortex_vals))
            else:
                vmin, vmax = 0.0, 1.0

        maps_data.append({
            "label":      final_label,
            "sub_label":  sub_labels[i] if (sub_labels and i < len(sub_labels)) else "",
            "cb_label":   cb_labels[i] if (cb_labels and i < len(cb_labels)) else "val",
            "cmap_type":  final_cmap,
            "vmin":       float(vmin),
            "vmax":       float(vmax),
            "lh": [float(v) for v in map_lh_vals.tolist()],
            "rh": [float(v) for v in map_rh_vals.tolist()],
        })
    print(f"[report_builder] Loading Yale-696 parcellation ({resolution}) …")
    tag = _PARC_TAG[resolution]
    dict_df = pd.read_csv(_PARC / "yale-696_dict.csv")
    n_rois = len(dict_df)

    lh_label_ids = nib.load(
        _PARC / f"yale-696_{tag}_lh.label.gii"
    ).darrays[0].data.astype(np.int32)
    rh_label_ids = nib.load(
        _PARC / f"yale-696_{tag}_rh.label.gii"
    ).darrays[0].data.astype(np.int32)

    # Hard-coded medial wall mask (derived from brainspace conte69 mask)
    mw_lh = np.load(_MW / f"medial_wall_{resolution}_lh.npy")
    mw_rh = np.load(_MW / f"medial_wall_{resolution}_rh.npy")

    def _to_roi_idx(ids: np.ndarray, mw_indices: np.ndarray) -> np.ndarray:
        """Map 1-based label IDs to 0-based ROI indices; medial wall → -1."""
        out = np.where(ids > 0, ids - 1, -1).astype(np.int16)
        out[mw_indices] = -1
        return out

    vtx2roi = np.concatenate([_to_roi_idx(lh_label_ids, mw_lh),
                              _to_roi_idx(rh_label_ids, mw_rh)])
    roi_rgb = dict_df[["YBA_R_color", "YBA_G_color", "YBA_B_color"]].to_numpy().astype(np.uint8)

    print(f"[report_builder] Building functional term lists …")
    top_query = _per_roi_top_n(_PQ, n_rois, TOP_N)
    top_synth = _per_roi_top_n(_PS, n_rois, TOP_N)

    def _hemi_mesh(mid_coords, infl_coords, sphere_coords, faces):
        return {
            "faces":    _b64(faces.ravel(), np.uint32),
            "n_verts":  int(len(mid_coords)),
            "surfaces": {
                "mid": {
                    "positions": _b64(mid_coords,  np.float32),
                    "normals":   _b64(_vertex_normals(mid_coords, faces), np.float32),
                },
                "inflated": {
                    "positions": _b64(infl_coords, np.float32),
                    "normals":   _b64(_vertex_normals(infl_coords, faces), np.float32),
                },
                "sphere": {
                    "positions": _b64(sphere_coords, np.float32),
                    "normals":   _b64(_vertex_normals(sphere_coords, faces), np.float32),
                },
            },
        }

    payload = {
        "resolution": resolution,
        "mesh": {
            "lh": _hemi_mesh(lh_mid_coords, infl_lh_coords, sphere_lh_coords, lh_faces),
            "rh": _hemi_mesh(rh_mid_coords, infl_rh_coords, sphere_rh_coords, rh_faces),
        },
        "maps": maps_data,
        "atlas": {
            "vertex_to_roi_lh": _b64(vtx2roi[:n_lh], np.int16),
            "vertex_to_roi_rh": _b64(vtx2roi[n_lh:], np.int16),
            "roi_rgb":          _b64(roi_rgb, np.uint8),
            "roi_names":        dict_df["Name"].tolist(),
            "roi_long_names":   dict_df["Long_name"].tolist(),
            "top_terms_query":  top_query,
            "top_terms_synth":  top_synth,
        },
    }
    return payload
