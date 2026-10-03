from __future__ import annotations

import argparse
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Sequence

from .model import Design
from .report import export_report
from .verilator_json import VerilatorJsonError, load_design


class WorkflowError(RuntimeError):
    """Raised for expected command-line workflow failures."""


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="rtl-impact",
        description="Trace signal drivers and loads through an elaborated RTL design.",
    )
    subcommands = parser.add_subparsers(dest="command", required=True)

    analyze_json = subcommands.add_parser(
        "analyze-json",
        help="Generate a report from existing Verilator JSON output.",
    )
    analyze_json.add_argument("input", type=Path, help="Verilator .tree.json file")
    analyze_json.add_argument("--meta", type=Path, help="Optional .tree.meta.json file")
    _add_report_arguments(analyze_json)

    analyze = subcommands.add_parser(
        "analyze",
        help="Run Verilator on SystemVerilog sources and generate a report.",
    )
    analyze.add_argument("sources", nargs="+", type=Path, help="RTL source files")
    analyze.add_argument("--top", required=True, help="Top module name")
    analyze.add_argument(
        "--engine",
        choices=("auto", "local", "docker"),
        default="auto",
        help="Verilator execution mode (default: auto)",
    )
    analyze.add_argument(
        "--verilator",
        default="verilator",
        help="Native Verilator executable (default: verilator)",
    )
    analyze.add_argument(
        "--docker-image",
        default="verilator/verilator:latest",
        help="Docker image used by the docker engine",
    )
    _add_report_arguments(analyze)
    return parser


def _add_report_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--output", required=True, type=Path, help="Report directory")
    parser.add_argument("--title", help="Report title")


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        if args.command == "analyze-json":
            design = load_design(args.input, args.meta)
        else:
            design = _run_verilator(
                args.sources,
                top=args.top,
                engine=args.engine,
                verilator=args.verilator,
                docker_image=args.docker_image,
            )
        entry_point = export_report(design, args.output, title=args.title)
    except (VerilatorJsonError, WorkflowError, OSError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1

    print(f"Report ready: {entry_point.resolve()}")
    print(
        f"Analyzed {len(design.modules)} modules, "
        f"{len(design.signals)} signals, and {len(design.edges)} connections."
    )
    return 0


def entrypoint() -> None:
    raise SystemExit(main())


def _run_verilator(
    sources: Sequence[Path],
    *,
    top: str,
    engine: str,
    verilator: str,
    docker_image: str,
) -> Design:
    resolved_sources = [source.resolve() for source in sources]
    missing = [source for source in resolved_sources if not source.is_file()]
    if missing:
        raise WorkflowError(f"source file not found: {missing[0]}")

    selected_engine = _select_engine(engine, verilator)
    try:
        mount_root = Path(
            os.path.commonpath([str(source.parent) for source in resolved_sources])
        )
    except ValueError as error:
        raise WorkflowError(
            "source files must be on the same filesystem volume"
        ) from error
    safe_top = re.sub(r"[^A-Za-z0-9_.-]", "_", top)
    with tempfile.TemporaryDirectory(prefix=".rtl-impact-", dir=mount_root) as temporary:
        temporary_path = Path(temporary)
        json_path = temporary_path / f"V{safe_top}.tree.json"
        meta_path = temporary_path / f"V{safe_top}.tree.meta.json"
        if selected_engine == "local":
            command = _local_command(
                verilator, resolved_sources, top, json_path, meta_path
            )
        else:
            command = _docker_command(
                docker_image,
                mount_root,
                resolved_sources,
                top,
                json_path,
                meta_path,
            )
        completed = subprocess.run(
            command,
            cwd=mount_root,
            capture_output=True,
            text=True,
            check=False,
        )
        if completed.returncode != 0:
            output = (completed.stderr or completed.stdout).strip()
            last_line = output.splitlines()[-1] if output else "no diagnostic output"
            raise WorkflowError(
                f"Verilator ({selected_engine}) failed with exit code "
                f"{completed.returncode}: {last_line}"
            )
        if not json_path.is_file():
            raise WorkflowError("Verilator completed without producing a JSON AST")
        return load_design(json_path, meta_path if meta_path.is_file() else None)


def _select_engine(engine: str, verilator: str) -> str:
    if engine in {"auto", "local"} and shutil.which(verilator):
        return "local"
    if engine == "local":
        raise WorkflowError(f"Verilator executable not found: {verilator}")
    if engine in {"auto", "docker"} and shutil.which("docker"):
        return "docker"
    if engine == "docker":
        raise WorkflowError("Docker executable not found")
    raise WorkflowError("neither Verilator nor Docker is available")


def _verilator_arguments(top: str, json_output: str, meta_output: str) -> list[str]:
    return [
        "--json-only",
        "--no-json-edit-nums",
        "--json-only-output",
        json_output,
        "--json-only-meta-output",
        meta_output,
        "--top-module",
        top,
    ]


def _local_command(
    executable: str,
    sources: Sequence[Path],
    top: str,
    json_path: Path,
    meta_path: Path,
) -> list[str]:
    return [
        executable,
        *_verilator_arguments(top, str(json_path), str(meta_path)),
        *(str(source) for source in sources),
    ]


def _docker_command(
    image: str,
    mount_root: Path,
    sources: Sequence[Path],
    top: str,
    json_path: Path,
    meta_path: Path,
) -> list[str]:
    def container_path(path: Path) -> str:
        return f"/work/{path.relative_to(mount_root).as_posix()}"

    return [
        "docker",
        "run",
        "--rm",
        "-v",
        f"{mount_root}:/work",
        image,
        *_verilator_arguments(
            top,
            container_path(json_path),
            container_path(meta_path),
        ),
        *(container_path(source) for source in sources),
    ]
