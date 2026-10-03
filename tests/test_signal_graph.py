from __future__ import annotations

import unittest
from pathlib import Path

from rtl_impact_explorer.signal_graph import SignalGraph
from rtl_impact_explorer.verilator_json import load_design


FIXTURES = Path(__file__).parent / "fixtures"


class SignalGraphTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.graph = SignalGraph(
            load_design(
                FIXTURES / "counter_top.tree.json",
                FIXTURES / "counter_top.tree.meta.json",
            )
        )

    def test_returns_direct_drivers_in_stable_order(self) -> None:
        self.assertEqual(
            self.graph.direct_drivers("counter_top.active_o"),
            ("counter_top.run_i", "counter_top.terminal_count"),
        )

    def test_returns_direct_loads_across_module_ports(self) -> None:
        self.assertEqual(
            self.graph.direct_loads("counter_top.run_i"),
            (
                "counter_top.active_o",
                "counter_top.divider_i.enable_i",
            ),
        )

    def test_traces_a_bounded_driver_cone_without_repeating_the_origin(self) -> None:
        self.assertEqual(
            self.graph.cone("counter_top.active_o", direction="drivers", depth=2),
            (
                "counter_top.run_i",
                "counter_top.terminal_count",
                "counter_top.divider_i.pulse_o",
            ),
        )

    def test_rejects_an_unknown_direction(self) -> None:
        with self.assertRaisesRegex(ValueError, "direction must be"):
            self.graph.cone("counter_top.active_o", direction="sideways")


if __name__ == "__main__":
    unittest.main()
