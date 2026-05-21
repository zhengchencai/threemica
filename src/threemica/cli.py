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
        "--surface",
        choices=["individual", "template"],
        default="individual",
        help="Surface to render maps on (default: individual).",
    )
    p.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Override the output directory.",
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
            surface_type=args.surface,
            out_dir=args.out,
            interactive=True,
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
