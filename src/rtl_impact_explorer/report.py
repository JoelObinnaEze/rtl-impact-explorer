from __future__ import annotations

import html
import json
import shutil
from pathlib import Path

from .model import Design, SourceLocation


_WEB_ASSETS = ("styles.css", "graph-view.js", "app.js")


def export_report(
    design: Design,
    output_dir: str | Path,
    *,
    title: str | None = None,
) -> Path:
    """Export a fetch-free browser report and return its entry point."""

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    report_title = title or f"{design.name} · RTL Impact Explorer"
    web_dir = Path(__file__).parent / "web"

    template = (web_dir / "index.html").read_text(encoding="utf-8")
    (output / "index.html").write_text(
        template.replace("{{TITLE}}", html.escape(report_title)),
        encoding="utf-8",
    )
    for asset in _WEB_ASSETS:
        shutil.copyfile(web_dir / asset, output / asset)

    payload = _design_payload(design, report_title)
    data = json.dumps(payload, ensure_ascii=True, separators=(",", ":"), sort_keys=True)
    (output / "design-data.js").write_text(
        f"window.RTL_IMPACT_DATA = {data};\n",
        encoding="utf-8",
    )
    return output / "index.html"


def _design_payload(design: Design, title: str) -> dict[str, object]:
    return {
        "schemaVersion": 1,
        "design": {
            "name": design.name,
            "source": design.source,
            "title": title,
        },
        "summary": {
            "modules": len(design.modules),
            "signals": len(design.signals),
            "connections": len(design.edges),
        },
        "modules": [
            {
                "id": module.id,
                "name": module.name,
                "path": module.path,
                "definition": module.definition,
                "parent": module.parent,
                "source": _location_payload(module.source),
                "signalIds": list(module.signal_ids),
            }
            for module in design.modules
        ],
        "signals": [
            {
                "id": signal.id,
                "name": signal.name,
                "path": signal.path,
                "modulePath": signal.module_path,
                "direction": signal.direction,
                "width": signal.width,
                "dtype": signal.dtype,
                "source": _location_payload(signal.source),
            }
            for signal in design.signals
        ],
        "edges": [
            {
                "id": f"edge-{index}",
                "source": edge.source,
                "target": edge.target,
                "kind": edge.kind,
                "sourceLocation": _location_payload(edge.source_location),
            }
            for index, edge in enumerate(design.edges, start=1)
        ],
    }


def _location_payload(location: SourceLocation) -> dict[str, object]:
    return {
        "file": location.file,
        "line": location.line,
        "column": location.column,
    }

