# threemica

Three.js HTML reports for MICA-pipeline–style surface maps.

`threemica` scans a BIDS `derivatives/` folder, finds the files you list in
`threemica_scope.json`, and writes one self-contained HTML report per
subject (and session, and resolution) with the YBA-696 atlas hover overlay
(Parcelquery / Parcelsynth top-term lookups).

## Install

**Recommended — fresh conda env**, so threemica's dependencies (nibabel,
numpy, pandas, questionary, rich) don't touch your existing environments:

```bash
conda create -n threemica python=3.11 -y
conda activate threemica
pip install threemica-0.2.0-py3-none-any.whl
```

Or with `venv`:

```bash
python3.11 -m venv ~/.venvs/threemica
source ~/.venvs/threemica/bin/activate
pip install threemica-0.2.0-py3-none-any.whl
```

Each time you want to use `threemica`, activate the env first.

**Optional but recommended:** install
[Connectome Workbench](https://www.humanconnectome.org/software/connectome-workbench)
(`wb_command`) — required if you want to smooth maps at runtime.

## Quick start

```bash
cd /path/to/BIDS                # any folder that contains derivatives/
threemica
```

On the first run threemica copies `threemica_scope.json` into
`derivatives/`. **Edit that file** to declare which derivative folders,
which subdirectories, and which map tags you want plotted. Then re-run.

The wizard then asks:

```
> ● Subjects               (default: all checked)
> ● Sessions               (only shown when sessions exist)
> ● Resolution             (default: fsLR-32k only)
> ● Maps                   (default: all checked)
> Smoothing FWHM (mm), NA to skip:
```

Output goes to `<BIDS>/derivatives/threemica/sub-XX/[ses-YY]/`, e.g.:

```
sub-HC010_ses-01_space-fsLR-32k_desc-individual_smooth-5mm_report-thickness-curv-midthickness_FA-midthickness_ADC.html
```

## The scope file (`threemica_scope.json`)

This is where you declare what threemica should plot. Three-level structure:

```json
{
  "surface": {
    "derivative": "micapipe_v0.2.0",
    "subdir": "surf",
    "label": "midthickness"
  },

  "micapipe_v0.2.0": {
    "maps": [
      {"tag": "thickness",          "label": "Cortical Thickness", "unit": "mm",          "cmap": "pos-only"},
      {"tag": "curv",               "label": "Curvature",          "unit": "1/mm",        "cmap": "diverging"},
      {"tag": "midthickness_FA",    "label": "FA",                 "unit": "",            "cmap": "pos-only"},
      {"tag": "midthickness_ADC",   "label": "ADC",                "unit": "mm²/s",       "cmap": "pos-only"},
      {"tag": "midthickness_T1map", "label": "Quantitative T1",    "unit": "s",           "cmap": "pos-only", "scale": 0.001},
      {"tag": "midthickness_cbf",   "label": "CBF",                "unit": "mL/100g/min", "cmap": "pos-only"}
    ]
  },

  "MICA-PET_v.alpha.0.5": {
    "surf": [
      {"tag": "midthickness_pvc-IY_ref-cerebellarGM_smooth-10mm_trc-MK6240_pet",
       "label": "Tau-PET (MK6240)", "unit": "SUVR", "cmap": "pos-only"}
    ]
  }
}
```

- **`surface`** — where the midthickness rendering surface lives (one
  declaration, used for all maps). threemica globs
  `*hemi-{H}*surf-{res}*label-{label}.surf.gii` under that path.
- **Top-level keys** other than `surface` are exact derivative folder names
  inside `derivatives/`. Add as many as you have.
- **Second-level keys** are subdirs under `sub-XX/[ses-YY]/` to look in
  (typically `maps` for micapipe, `surf` for micapet).
- **The tag list** — each tag is the *exact* `_label-X` value in the file
  name. A tag entry may be a plain string or a dict with these fields:
  - `tag` (required) — the exact label substring.
  - `label` — friendly title shown top-left in the HTML.
  - `unit` — colorbar unit.
  - `cmap` — `"pos-only"` or `"diverging"`. Pos-only uses min..max of cortex
    values; diverging uses ±max(|x|) symmetric around 0.
  - `scale` — multiply data values before display (e.g. `0.001` to render
    T1map in seconds instead of milliseconds).

Threemica only reads what you put in this file. If you add a new pipeline
or want a new map, add an entry — no code change.

## CLI flags

```
threemica [PATH] [--subjects sub-001 sub-002 …]
                 [--sessions ses-01 …]
                 [--maps thickness curv …]
                 [--resolution fsLR-32k [fsLR-5k]]
                 [--smooth FWHM_MM]
                 [--out OUT_DIR]
                 [--batch]
```

`PATH` defaults to the current working directory; threemica walks up until
it finds a folder containing `derivatives/`.

Any flag you supply replaces the corresponding wizard prompt. `--batch`
disables all prompts; you must then provide subjects + maps + resolution
yourself.

## Python API

```python
import threemica

outputs = threemica.run(
    bids_root="/path/to/BIDS",
    subjects=["sub-001"],
    sessions=["ses-01"],
    maps=["thickness", "midthickness_FA"],
    resolution="fsLR-32k",
    smooth_mm=5,
    interactive=False,
)
for p in outputs:
    print(p)
```

Public API: `threemica.run`, `threemica.scan_subject`, `threemica.build`,
`threemica.resolve_bids_root`, `threemica.list_subjects`,
`threemica.list_sessions`, `threemica.find_surface`, `threemica.FeatureMap`.

## Scope (v0.2)

- Maps stored per the scope file only — no automatic full-tree scanning.
- fsLR-5k and fsLR-32k only — no fsnative, no fsaverage5.
- Renders only midthickness surfaces; surface comes from one derivative
  folder declared in `scope.surface`.
- Three.js viewer derived from the SPACES atlas project.

## License

MIT.
