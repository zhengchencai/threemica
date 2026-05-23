# AGENTS.md

Guidance for Codex sessions in this repo.

## Project

`threemica` is a standalone Python CLI + library that turns MicaPipe surface
maps into self-contained Three.js HTML reports. Point it at a MicaPipe
derivatives folder; it scans, lets the user pick subjects + feature maps, and
writes one HTML per subject(/session) with the YBA-696 atlas hover overlay
(Parcelquery / Parcelsynth top terms).

Extracted from `/Users/django/Projects/SPACES_atlas/YBA_multimodal_data_micapipe/`
plus EpMap-style smart scanner/wizard and proper packaging.

## Architecture

```
src/threemica/
├── __init__.py         # Public re-exports
├── core.py             # Public API: resolve_micapipe_root, scan, build, run, FeatureMap
├── cli.py              # `threemica` console script (thin wrapper over core.run)
├── _wizard.py          # questionary pickers (pick_subjects, pick_maps, pick_resolution)
├── builder.py          # build_payload() — ported from SPACES, edits only for packaging
├── resample.py         # Surface/metric resampling via wb_command (optional)
├── _resources.py       # importlib.resources accessors for bundle
├── viewer/
│   ├── template.html   # Verbatim from SPACES (small CSS tweaks only)
│   └── viewer.js       # Verbatim from SPACES — do not edit
└── data/yba_micapipe/  # ~8 MB atlas bundle (surfaces, parcellations, medial wall,
                          parcelquery, parcelsynth) — shipped in the wheel
```

The CLI is a 5-line wrapper. EpMap (or any third party) calls
`threemica.run(...)` as a library without spawning a subprocess.

## Public API surface

```python
threemica.run                   # end-to-end (interactive=True | False)
threemica.scan                  # one subject dir → {session: [FeatureMap]}
threemica.build                 # one HTML for one subject/session
threemica.resolve_micapipe_root # smart cwd/subject/session → MicaPipe root
threemica.FeatureMap            # dataclass(label, resolution, lh_path, rh_path)
```

`run(interactive=False)` is the scripted entry point — it requires
`subjects`, `maps`, `resolution`.

## CLI

```
threemica [PATH] [--subjects ...] [--sessions ...] [--maps ...]
                 [--resolution fsLR-5k|fsLR-32k]
                 [--surface individual|template]
                 [--out DIR] [--batch]
```

- No args → fully interactive
- Some args → mixed (only missing prompts shown)
- `--batch` → no prompts at all; missing required args is an error

## Tests

```bash
source .venv/bin/activate
pytest -v        # 32 tests, ~2s
```

Synthetic MicaPipe fixture in `tests/conftest.py` (`fake_micapipe`).
No subjects-in-fixtures network/AFNI/wb_command dependency.

## Bundle

`src/threemica/data/yba_micapipe/` is shipped via
`[tool.setuptools.package-data] "threemica" = ["data/**/*", "viewer/*"]`.
Accessed at runtime through `importlib.resources` in `_resources.py` —
never via `Path(__file__).parent`. Do not move the data dir.

## Style rules

- No emojis in code or files unless explicitly requested.
- No `Co-Authored-By` lines in commits.
- Questionary prompts use `pointer=">"` and the style:
  `("answer", "fg:cyan"), ("pointer", ""), ("selected", "noreverse"), ("highlighted", "noreverse")`
  — same as EpMap. Subject picker starts with **nothing checked**.

## Don't touch

- `viewer/viewer.js` — verbatim from SPACES. If upstream changes, re-copy
  wholesale; don't edit inline.
- `viewer/template.html` — also from SPACES. Minor CSS tweaks (e.g.
  `--tooltip-scale`) are OK as long as the `{{TITLE}}`, `{{THEME_CLASS}}`,
  `{{PAYLOAD_JSON}}`, `{{VIEWER_JS}}` placeholders stay intact.
- `builder.py` — port-only. Bundle paths come from `_resources.py`;
  computation logic is upstream SPACES code.

## Scope (v1)

- Surface maps in `maps/` only — no `parc/`, `func/`, `dwi/`.
- fsLR-5k and fsLR-32k only — no fsnative, no fsaverage5.
- Single-subject HTMLs only — no combined multi-subject reports.
- No preset save/load.

## Build / release

```bash
python -m build --wheel              # → dist/threemica-X.Y.Z-py3-none-any.whl (~4.5 MB)
```

Wheel contains everything including the atlas bundle. Recipients run
`pip install threemica-X.Y.Z-py3-none-any.whl` in a fresh conda/venv env.
