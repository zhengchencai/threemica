# threemica

Three.js HTML reports for MICA-pipeline–style surface maps.

Point it at a BIDS `derivatives/` folder, edit one tiny `threemica_scope.json`
to say which maps you care about, and `threemica` writes a self-contained
HTML viewer per subject — with the YBA-696 atlas overlay, Parcelquery and
Parcelsynth top-term lookups, optional smoothing, and a hidden demo.

<p align="center">
  <video src="https://github.com/user-attachments/assets/4c173394-041d-451b-9dcf-8dab67a4aa4a"
         controls autoplay muted loop playsinline width="720">
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
threemica                 # first run copies threemica_scope.json into derivatives/
```

Edit `derivatives/threemica_scope.json` to declare what to scan, then run
again. The wizard asks for subjects, sessions (if any), resolution and
smoothing FWHM. Outputs land in
`<BIDS>/derivatives/threemica/sub-XX/[ses-YY]/`.

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
                 [--smooth FWHM_MM] [--output PARENT_DIR]
```

`threemica --help` for the full list.

## Viewer controls

`H` help · scroll/`←→` inflate · `↑↓` zoom · `[ ]` switch map · `C` colormap
· `T` theme · `Q` hover query · `O` opacity · `M` mesh · `L` lock · `R` reset.

Right-click a vertex to pin the query with Parcelquery + Parcelsynth tables.

There's also a hidden demo: `Enter`, type `poweroverwhelming`, `Enter`.

