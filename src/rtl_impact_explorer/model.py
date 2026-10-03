from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SourceLocation:
    file: str = ""
    line: int | None = None
    column: int | None = None


@dataclass(frozen=True, slots=True)
class Signal:
    id: str
    name: str
    path: str
    module_path: str
    direction: str
    width: int
    dtype: str
    source: SourceLocation


@dataclass(frozen=True, slots=True)
class ModuleInstance:
    id: str
    name: str
    path: str
    definition: str
    parent: str | None
    source: SourceLocation
    signal_ids: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Edge:
    source: str
    target: str
    kind: str
    source_location: SourceLocation


@dataclass(frozen=True, slots=True)
class Design:
    name: str
    source: str
    modules: tuple[ModuleInstance, ...]
    signals: tuple[Signal, ...]
    edges: tuple[Edge, ...]

    def signal(self, signal_id: str) -> Signal:
        for signal in self.signals:
            if signal.id == signal_id:
                return signal
        raise KeyError(signal_id)

