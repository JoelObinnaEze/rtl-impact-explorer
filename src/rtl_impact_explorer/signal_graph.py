from __future__ import annotations

from collections import defaultdict

from .model import Design


class SignalGraph:
    """Directional graph queries over an analyzed RTL design."""

    def __init__(self, design: Design) -> None:
        self.design = design
        self._signal_ids = {signal.id for signal in design.signals}
        self._loads: dict[str, set[str]] = defaultdict(set)
        self._drivers: dict[str, set[str]] = defaultdict(set)
        for edge in design.edges:
            self._loads[edge.source].add(edge.target)
            self._drivers[edge.target].add(edge.source)

    def direct_drivers(self, signal_id: str) -> tuple[str, ...]:
        self._require_signal(signal_id)
        return tuple(sorted(self._drivers.get(signal_id, ())))

    def direct_loads(self, signal_id: str) -> tuple[str, ...]:
        self._require_signal(signal_id)
        return tuple(sorted(self._loads.get(signal_id, ())))

    def cone(
        self,
        signal_id: str,
        *,
        direction: str,
        depth: int = 3,
    ) -> tuple[str, ...]:
        """Return a breadth-first dependency cone without repeating nodes."""

        self._require_signal(signal_id)
        if direction not in {"drivers", "loads"}:
            raise ValueError("direction must be 'drivers' or 'loads'")
        if depth < 0:
            raise ValueError("depth must be zero or greater")

        adjacency = self._drivers if direction == "drivers" else self._loads
        seen = {signal_id}
        frontier = (signal_id,)
        result: list[str] = []
        for _ in range(depth):
            next_frontier = sorted(
                {
                    neighbor
                    for node in frontier
                    for neighbor in adjacency.get(node, ())
                    if neighbor not in seen
                }
            )
            if not next_frontier:
                break
            result.extend(next_frontier)
            seen.update(next_frontier)
            frontier = tuple(next_frontier)
        return tuple(result)

    def _require_signal(self, signal_id: str) -> None:
        if signal_id not in self._signal_ids:
            raise KeyError(signal_id)
