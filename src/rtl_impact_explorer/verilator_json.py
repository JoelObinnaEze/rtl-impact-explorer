from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator

from .model import Design, Edge, ModuleInstance, Signal, SourceLocation


class VerilatorJsonError(ValueError):
    """Raised when Verilator JSON cannot be converted into a design model."""


JsonObject = dict[str, Any]


@dataclass(slots=True)
class _Instance:
    path: str
    name: str
    parent: str | None
    module: JsonObject
    cell: JsonObject | None


def load_design(
    json_path: str | Path,
    meta_path: str | Path | None = None,
) -> Design:
    """Load a Verilator 5 ``--json-only`` artifact into a stable model."""

    input_path = Path(json_path)
    root = _read_json(input_path)
    if root.get("type") != "NETLIST":
        raise VerilatorJsonError(
            f"{input_path.name}: expected a Verilator NETLIST root"
        )

    modules = root.get("modulesp")
    if not isinstance(modules, list) or not modules:
        raise VerilatorJsonError(f"{input_path.name}: NETLIST contains no modules")

    metadata = _load_metadata(input_path, meta_path)
    files = _source_files(metadata)
    module_by_addr = {
        module.get("addr"): module
        for module in modules
        if isinstance(module, dict) and module.get("addr")
    }
    top = next(
        (
            module
            for module in modules
            if isinstance(module, dict) and module.get("level") == 1
        ),
        modules[0],
    )
    if not isinstance(top, dict) or not top.get("name"):
        raise VerilatorJsonError(f"{input_path.name}: top module is malformed")

    instances: list[_Instance] = []
    _collect_instances(
        module=top,
        path=str(top["name"]),
        name=str(top["name"]),
        parent=None,
        cell=None,
        module_by_addr=module_by_addr,
        output=instances,
        active_modules=(),
    )

    dtypes = _dtype_table(root)
    signals: list[Signal] = []
    signal_by_var: dict[tuple[str, str], str] = {}
    module_models: list[ModuleInstance] = []

    for instance in instances:
        instance_signal_ids: list[str] = []
        for node in _statement_nodes(instance.module):
            if node.get("type") != "VAR" or _is_parameter(node):
                continue
            name = str(node.get("name") or "")
            address = str(node.get("addr") or "")
            if not name or not address:
                continue
            signal_id = f"{instance.path}.{name}"
            dtype = _resolve_dtype(node.get("dtypep"), dtypes)
            signal = Signal(
                id=signal_id,
                name=name,
                path=signal_id,
                module_path=instance.path,
                direction=_normalise_direction(node.get("direction")),
                width=_dtype_width(dtype),
                dtype=str(node.get("dtypeName") or dtype.get("name") or "logic"),
                source=_parse_location(node.get("loc"), files),
            )
            signals.append(signal)
            instance_signal_ids.append(signal_id)
            signal_by_var[(instance.path, address)] = signal_id

        module_models.append(
            ModuleInstance(
                id=instance.path,
                name=instance.name,
                path=instance.path,
                definition=str(instance.module.get("name") or instance.name),
                parent=instance.parent,
                source=_parse_location(instance.module.get("loc"), files),
                signal_ids=tuple(instance_signal_ids),
            )
        )

    signal_lookup = {signal.id: signal for signal in signals}
    edges: dict[tuple[str, str, str], Edge] = {}
    for instance in instances:
        _add_process_edges(instance, signal_by_var, files, edges)
        _add_port_edges(instance, signal_by_var, signal_lookup, files, edges)

    return Design(
        name=str(top["name"]),
        source=input_path.name,
        modules=tuple(module_models),
        signals=tuple(signals),
        edges=tuple(edges[key] for key in sorted(edges)),
    )


def _read_json(path: Path) -> JsonObject:
    try:
        value = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as error:
        raise VerilatorJsonError(f"{path}: file not found") from error
    except json.JSONDecodeError as error:
        raise VerilatorJsonError(f"{path.name} is not valid JSON: {error.msg}") from error
    except OSError as error:
        raise VerilatorJsonError(f"cannot read {path}: {error}") from error
    if not isinstance(value, dict):
        raise VerilatorJsonError(f"{path.name}: expected a JSON object")
    return value


def _load_metadata(input_path: Path, meta_path: str | Path | None) -> JsonObject:
    if meta_path is not None:
        return _read_json(Path(meta_path))
    if input_path.name.endswith(".tree.json"):
        candidate = input_path.with_name(
            input_path.name.removesuffix(".tree.json") + ".tree.meta.json"
        )
        if candidate.exists():
            return _read_json(candidate)
    return {}


def _source_files(metadata: JsonObject) -> dict[str, str]:
    result: dict[str, str] = {}
    files = metadata.get("files", {})
    if not isinstance(files, dict):
        return result
    for key, value in files.items():
        if isinstance(value, dict):
            result[str(key)] = str(value.get("filename") or value.get("realpath") or key)
    return result


def _collect_instances(
    *,
    module: JsonObject,
    path: str,
    name: str,
    parent: str | None,
    cell: JsonObject | None,
    module_by_addr: dict[str, JsonObject],
    output: list[_Instance],
    active_modules: tuple[str, ...],
) -> None:
    module_addr = str(module.get("addr") or "")
    if module_addr in active_modules:
        raise VerilatorJsonError(f"recursive module hierarchy detected at {path}")
    output.append(_Instance(path, name, parent, module, cell))
    next_active = active_modules + (module_addr,)
    for statement in _statement_nodes(module):
        if statement.get("type") != "CELL":
            continue
        child = module_by_addr.get(str(statement.get("modp") or ""))
        child_name = str(statement.get("name") or "")
        if child is None or not child_name:
            continue
        _collect_instances(
            module=child,
            path=f"{path}.{child_name}",
            name=child_name,
            parent=path,
            cell=statement,
            module_by_addr=module_by_addr,
            output=output,
            active_modules=next_active,
        )


def _statement_nodes(module: JsonObject) -> list[JsonObject]:
    statements = module.get("stmtsp", [])
    if not isinstance(statements, list):
        return []
    return [statement for statement in statements if isinstance(statement, dict)]


def _is_parameter(node: JsonObject) -> bool:
    return bool(node.get("isParam")) or node.get("varType") in {"GPARAM", "LPARAM"}


def _dtype_table(root: JsonObject) -> dict[str, JsonObject]:
    result: dict[str, JsonObject] = {}
    for node in _walk(root.get("miscsp", [])):
        address = node.get("addr")
        if address and str(node.get("type", "")).endswith("DTYPE"):
            result[str(address)] = node
    return result


def _resolve_dtype(address: Any, dtypes: dict[str, JsonObject]) -> JsonObject:
    current = dtypes.get(str(address), {})
    visited: set[str] = set()
    while current:
        current_address = str(current.get("addr") or "")
        next_address = str(current.get("dtypep") or "")
        if not next_address or next_address == current_address or next_address in visited:
            break
        visited.add(current_address)
        next_dtype = dtypes.get(next_address)
        if next_dtype is None:
            break
        current = next_dtype
    return current


def _dtype_width(dtype: JsonObject) -> int:
    bit_range = dtype.get("range")
    if not isinstance(bit_range, str):
        return 1
    match = re.fullmatch(r"(-?\d+):(-?\d+)", bit_range)
    if match is None:
        return 1
    return abs(int(match.group(1)) - int(match.group(2))) + 1


def _normalise_direction(value: Any) -> str:
    direction = str(value or "NONE").lower()
    return direction if direction in {"input", "output", "inout"} else "internal"


def _parse_location(value: Any, files: dict[str, str]) -> SourceLocation:
    if not isinstance(value, str):
        return SourceLocation()
    match = re.fullmatch(r"([^,]+),(\d+):(\d+),(\d+):(\d+)", value)
    if match is None:
        return SourceLocation()
    file_id, line, column, _, _ = match.groups()
    return SourceLocation(
        file=files.get(file_id, file_id),
        line=int(line),
        column=int(column),
    )


def _add_process_edges(
    instance: _Instance,
    signal_by_var: dict[tuple[str, str], str],
    files: dict[str, str],
    output: dict[tuple[str, str, str], Edge],
) -> None:
    for statement in _statement_nodes(instance.module):
        node_type = str(statement.get("type") or "")
        if node_type in {"VAR", "CELL", "SCOPE"}:
            continue
        reads: set[str] = set()
        writes: set[str] = set()
        for node in _walk(statement):
            if node.get("type") != "VARREF":
                continue
            signal_id = signal_by_var.get(
                (instance.path, str(node.get("varp") or ""))
            )
            if signal_id is None:
                continue
            access = str(node.get("access") or "")
            if access in {"RD", "RW"}:
                reads.add(signal_id)
            if access in {"WR", "RW"}:
                writes.add(signal_id)

        kind = _process_kind(statement)
        location = _parse_location(statement.get("loc"), files)
        for source in reads:
            for target in writes:
                key = (source, target, kind)
                output.setdefault(key, Edge(source, target, kind, location))


def _process_kind(statement: JsonObject) -> str:
    keyword = str(statement.get("keyword") or "").lower()
    if keyword in {"always_ff", "always_latch"}:
        return "sequential"
    if any(node.get("type") == "ASSIGNDLY" for node in _walk(statement)):
        return "sequential"
    return "combinational"


def _add_port_edges(
    instance: _Instance,
    signal_by_var: dict[tuple[str, str], str],
    signals: dict[str, Signal],
    files: dict[str, str],
    output: dict[tuple[str, str, str], Edge],
) -> None:
    if instance.cell is None or instance.parent is None:
        return
    pins = instance.cell.get("pinsp", [])
    if not isinstance(pins, list):
        return
    for pin in pins:
        if not isinstance(pin, dict):
            continue
        child_signal = signal_by_var.get(
            (instance.path, str(pin.get("modVarp") or ""))
        )
        if child_signal is None:
            continue
        parent_signals = {
            signal_by_var[(instance.parent, str(node.get("varp")))]
            for node in _walk(pin.get("exprp", []))
            if node.get("type") == "VARREF"
            and (instance.parent, str(node.get("varp"))) in signal_by_var
        }
        direction = signals[child_signal].direction
        location = _parse_location(pin.get("loc"), files)
        for parent_signal in parent_signals:
            pairs: list[tuple[str, str]] = []
            if direction in {"input", "inout"}:
                pairs.append((parent_signal, child_signal))
            if direction in {"output", "inout"}:
                pairs.append((child_signal, parent_signal))
            for source, target in pairs:
                key = (source, target, "port")
                output.setdefault(key, Edge(source, target, "port", location))


def _walk(value: Any) -> Iterator[JsonObject]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk(child)
