# threemica

Three.js HTML reports for MicaPipe surface maps.

`threemica` scans a MicaPipe derivatives folder, lets you pick which feature
maps to include, and writes one self-contained HTML report per subject (or
subject/session) with the YBA-696 atlas overlay and Parcelquery / Parcelsynth
top-term lookups.

## Install

**Recommended:** create a fresh conda env so threemica's dependencies
(nibabel, numpy, pandas, questionary, rich) don't touch your existing
environments.

```bash
conda create -n threemica python=3.11 -y
conda activate threemica
pip install threemica-0.1.0-py3-none-any.whl
```

Or with `venv` if you don't have conda:

```bash
python3.11 -m venv ~/.venvs/threemica
source ~/.venvs/threemica/bin/activate
pip install threemica-0.1.0-py3-none-any.whl
```

Each time you want to use `threemica`, activate the env first
(`conda activate threemica` or `source ~/.venvs/threemica/bin/activate`).

Optional: install [Connectome Workbench](https://www.humanconnectome.org/software/connectome-workbench)
(`wb_command`) — required for `--smooth` (surface smoothing) and for
cross-resolution resampling.

## Use it (CLI)

```bash
cd /path/to/derivatives/micapipe_v0.2.0
threemica
```

You'll be asked which subjects, sessions, feature maps, resolution, and
smoothing FWHM. Output is written to
`<BIDS>/derivatives/threemica/sub-XX/[ses-YY]/`.

You can also point it at a path or skip prompts via flags:

```bash
threemica /path/to/derivatives/micapipe_v0.2.0/sub-001/ses-01
threemica --subjects sub-001 --maps thickness curv \
          --resolution fsLR-32k --smooth 5 --batch
```

`--smooth N` runs `wb_command -metric-smoothing` on the midthickness surface
with the medial wall masked out. Intermediate smoothed files live in a
`_tmp/` folder under the output dir and are removed on completion.

## Use it (Python API)

```python
import threemica

outputs = threemica.run(
    micapipe_root="/path/to/derivatives/micapipe_v0.2.0",
    subjects=["sub-001"],
    sessions=["ses-01"],
    maps=["thickness", "curv"],
    resolution="fsLR-32k",
    interactive=False,
)
for p in outputs:
    print(p)
```

Public API: `threemica.scan`, `threemica.build`, `threemica.run`,
`threemica.resolve_micapipe_root`, `threemica.FeatureMap`.

## Scope (v1)

- Surface feature maps in `maps/` only — no `parc/`, `func/`, `dwi/`.
- fsLR-5k and fsLR-32k only — no fsnative, no fsaverage5.
- Three.js viewer copied from the SPACES atlas project, unchanged.

## License

MIT.
