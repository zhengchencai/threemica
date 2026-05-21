"""Command-line entry point. Thin wrapper over threemica.core.run."""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import List, Optional

from rich.console import Console

from threemica import core


_console = Console()


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="threemica",
        description="Three.js HTML reports for MicaPipe surface maps. "
        "Run from inside a MicaPipe derivatives directory.",
    )
    p.add_argument(
        "path",
        nargs="?",
        default=None,
        help="MicaPipe derivatives folder, subject, or session "
        "(default: current working directory).",
    )
    p.add_argument(
        "--subjects",
        nargs="+",
        default=None,
        help="Subjects to process (e.g. sub-001 sub-002). Default: interactive picker.",
    )
    p.add_argument(
        "--sessions",
        nargs="+",
        default=None,
        help="Sessions to include (e.g. ses-01). Default: all sessions found.",
    )
    p.add_argument(
        "--maps",
        nargs="+",
        default=None,
        help="Feature-map labels (e.g. thickness curv). Default: interactive picker.",
    )
    p.add_argument(
        "--resolution",
        nargs="+",
        choices=["fsLR-5k", "fsLR-32k"],
        default=None,
        help="Surface resolution(s); one HTML per resolution. Default: interactive picker.",
    )
    p.add_argument(
        "--surface",
        choices=["individual", "template"],
        default="individual",
        help="Surface to render maps on (default: individual).",
    )
    p.add_argument(
        "--smooth",
        type=int,
        default=None,
        metavar="FWHM_MM",
        help="Surface smoothing FWHM in mm (wb_command -metric-smoothing). "
        "Omit or 0 = no smoothing.",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Override the output directory.",
    )
    p.add_argument(
        "--batch",
        action="store_true",
        help="Non-interactive mode. Requires --subjects, --maps, --resolution.",
    )
    return p


# Indirection point so tests can monkeypatch this without spawning a subprocess
def _run_via_core(**kwargs):
    return core.run(**kwargs)


def main(argv: Optional[List[str]] = None) -> int:
    args = _build_parser().parse_args(argv)
    try:
        outputs = _run_via_core(
            micapipe_root=args.path,
            subjects=args.subjects,
            sessions=args.sessions,
            maps=args.maps,
            resolution=args.resolution,
            surface_type=args.surface,
            out_dir=args.out,
            smooth_mm=(args.smooth if args.smooth and args.smooth > 0 else None),
            interactive=not args.batch,
        )
    except FileNotFoundError as e:
        _console.print(f"[red]✗[/] {e}")
        return 1
    except KeyboardInterrupt:
        _console.print("[yellow]Cancelled[/]")
        return 130

    if not outputs:
        _console.print("[yellow]No reports generated[/]")
        return 0

    _console.print(f"[green]✓[/] {len(outputs)} report(s):")
    for p in outputs:
        _console.print(f"  [cyan]{p}[/]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
