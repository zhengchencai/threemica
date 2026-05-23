# threemica

Three.js HTML reports for MICA-pipeline–style surface maps.

Point it at a BIDS `derivatives/` folder, edit one tiny
`derivatives/threemica/threemica_scope.json` to say which maps you care about,
and `threemica` writes a self-contained HTML viewer per subject — with the
YBA-696 atlas overlay, Parcelquery and Parcelsynth top-term lookups, and optional
smoothing.
<p align="center">
  <video autoplay muted loop playsinline disablePictureInPicture controlsList="nodownload" width="100%">
    <source src="https://github.com/user-attachments/assets/7022b7e6-4ef8-4ff4-b10a-fdf92b49757a" type="video/mp4">
  </video>
</p>

## Install

Always in a fresh env so threemica's deps don't touch existing ones:

```bash
conda create -n threemica python=3.11 -y
conda activate threemica
pip install threemica-0.3.0-py3-none-any.whl
```

Optional: install Connectome Workbench (`wb_command`) — needed only if you
want runtime smoothing.

## Use

```bash
cd /path/to/BIDS          # anything containing derivatives/
threemica                 # first run copies threemica_scope.json into derivatives/threemica/
```

Edit `derivatives/threemica/threemica_scope.json` to declare what to scan, then
run again. The wizard asks for output root, subjects, sessions (if any),
resolution and smoothing FWHM. By default, outputs land in
`<BIDS>/derivatives/threemica/sub-XX/[ses-YY]/`. If you choose another output
root, outputs land in `<OUTPUT_ROOT>/derivatives/threemica/sub-XX/[ses-YY]/`.
The scope file is created in that same `derivatives/threemica/` folder.

threemica only writes its own config, temporary smoothing files, and HTML
reports under the selected output root's `derivatives/threemica/`. It reads
source maps/surfaces from micapipe and other derivatives, but does not modify
those derivative folders.

### scope.json — the only thing you'll edit

```jsonc
{
  "surface": {
    "derivative": "micapipe_v0.2.0",
    "subdir":     "surf",
    "label":      "midthickness"
  },

  "micapipe_v0.2.0": {
    "maps": [
      {"tag": "thickness",          "label": "Cortical Thickness", "unit": "mm",          "cmap": "pos-only"},
      {"tag": "midthickness_FA",    "label": "FA",                 "unit": "",            "cmap": "pos-only"},
      {"tag": "midthickness_ADC",   "label": "ADC",                "unit": "mm²/s",       "cmap": "pos-only"},
      {"tag": "midthickness_T1map", "label": "qT1",                "unit": "s",           "cmap": "pos-only", "scale": 0.001},
      {"tag": "midthickness_cbf",   "label": "CBF",                "unit": "mL/100g/min", "cmap": "pos-only"}
    ]
  },

  "MICA-PET_v.alpha.0.5": {
    "surf": [
      {"tag": "midthickness_pvc-IY_ref-cerebellarGM_smooth-10mm_trc-MK6240_pet",
       "label": "Tau-PET (MK6240)", "unit": "SUVR", "cmap": "pos-only"}
    ]
  },

  "electroMICA": {
    "maps": [
      {"tag": "stage-N2_InterictalEventsRates", "label": "IEDRate(N2)", "unit": "events/min", "cmap": "pos-only"},
      {"tag": "stage-N3_InterictalEventsRates", "label": "IEDRate(N3)", "unit": "events/min", "cmap": "pos-only"},
      {"tag": "stage-W_InterictalEventsRates",  "label": "IEDRate(W)",  "unit": "events/min", "cmap": "pos-only"}
    ]
  }
}
```

- Top-level `surface` block — where the rendering surface lives.
- Other top-level keys — exact derivative folder names. Add as many as you
  have.
- Each map dict: `tag` (exact `_label-X` value in the filename) plus optional
  `label` / `unit` / `cmap` (`pos-only` | `diverging` | `auto`) / `scale`.

## CLI

```
threemica [PATH] [--subjects sub-001 …] [--sessions ses-01 …]
                 [--maps thickness …] [--resolution fsLR-32k [fsLR-5k]]
                 [--smooth FWHM_MM] [--output ROOT]
```

`threemica --help` for the full list.

## Embed In Another Python HTML Report

`threemica` can be called from an existing Python report builder and embedded
into the same final HTML file. Generate the threemica viewer, read the generated
HTML, and place it inside an iframe with `srcdoc`.

```python
from pathlib import Path
import html

from threemica import run


def build_report_with_threemica(bids_root, report_root):
    report_root = Path(report_root)

    viewer_paths = run(
        bids_root=bids_root,
        subjects=["sub-001"],
        sessions=["ses-01"],
        maps=["thickness"],
        resolution="fsLR-32k",
        output_root=report_root,
        interactive=False,
    )

    viewer_html = viewer_paths[0]
    viewer_text = viewer_html.read_text(encoding="utf-8")

    threemica_panel = f"""
    <iframe
      srcdoc="{html.escape(viewer_text, quote=True)}"
      style="width:100%; height:900px; border:0;"
      loading="lazy">
    </iframe>
    """

    report_html = f"""
    <!doctype html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>My Report</title>
    </head>
    <body>
      <h1>My Report</h1>

      <section>
        <h2>Surface Viewer</h2>
        {threemica_panel}
      </section>
    </body>
    </html>
    """

    out = report_root / "report.html"
    out.write_text(report_html, encoding="utf-8")
    return out
```

This creates one parent `report.html` containing the threemica viewer. The
intermediate threemica HTML remains under
`<report_root>/derivatives/threemica/`, but the final report does not need to
link to it.

## Viewer controls

`H` help · scroll/`←→` inflate · `↑↓` zoom · `[ ]` switch map · `C` colormap
· `T` theme · `Q` hover query · `O` opacity · `M` mesh · `L` lock · `R` reset.

Right-click a vertex to pin the query with Parcelquery + Parcelsynth tables.
