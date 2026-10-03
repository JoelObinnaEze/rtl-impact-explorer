from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rtl_impact_explorer.verilator_json import VerilatorJsonError, load_design


FIXTURES = Path(__file__).parent / "fixtures"


class VerilatorJsonTests(unittest.TestCase):
    def test_loads_modules_signals_and_cross_hierarchy_connections(self) -> None:
        design = load_design(
            FIXTURES / "counter_top.tree.json",
            FIXTURES / "counter_top.tree.meta.json",
        )

        self.assertEqual(design.name, "counter_top")
        self.assertEqual(
            [module.path for module in design.modules],
            ["counter_top", "counter_top.divider_i"],
        )
        self.assertEqual(len(design.signals), 11)

        count = design.signal("counter_top.count_o")
        self.assertEqual(count.width, 4)
        self.assertEqual(count.direction, "output")
        self.assertTrue(count.source.file.endswith("examples/counter_top.sv"))
        self.assertEqual(count.source.line, 25)

        connections = {
            (edge.source, edge.target, edge.kind) for edge in design.edges
        }
        self.assertIn(
            (
                "counter_top.run_i",
                "counter_top.divider_i.enable_i",
                "port",
            ),
            connections,
        )
        self.assertIn(
            (
                "counter_top.divider_i.pulse_o",
                "counter_top.terminal_count",
                "port",
            ),
            connections,
        )
        self.assertIn(
            (
                "counter_top.divider_i.count_o",
                "counter_top.count_o",
                "port",
            ),
            connections,
        )
        self.assertIn(
            ("counter_top.run_i", "counter_top.active_o", "combinational"),
            connections,
        )

    def test_rejects_json_that_is_not_a_verilator_netlist(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "invalid.json"
            invalid.write_text(json.dumps({"type": "OTHER"}), encoding="utf-8")

            with self.assertRaisesRegex(
                VerilatorJsonError, "expected a Verilator NETLIST root"
            ):
                load_design(invalid)

    def test_reports_invalid_json_with_the_input_filename(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "broken.tree.json"
            invalid.write_text("{not-json", encoding="utf-8")

            with self.assertRaisesRegex(
                VerilatorJsonError, "broken.tree.json is not valid JSON"
            ):
                load_design(invalid)


if __name__ == "__main__":
    unittest.main()
