from __future__ import annotations

import re
import unittest
from pathlib import Path


EXAMPLES = Path(__file__).parents[1] / "examples"
RICH_EXAMPLES = {
    "uart_tx.sv": "uart_tx",
    "traffic_light_controller.sv": "traffic_light_controller",
}


class ExampleDesignTests(unittest.TestCase):
    def test_richer_examples_exist_with_matching_top_modules(self) -> None:
        for filename, top_module in RICH_EXAMPLES.items():
            with self.subTest(filename=filename):
                source_path = EXAMPLES / filename
                self.assertTrue(source_path.is_file(), f"missing example: {filename}")
                if not source_path.is_file():
                    continue

                source = source_path.read_text(encoding="utf-8")
                module_names = re.findall(r"\bmodule\s+([A-Za-z_][A-Za-z0-9_]*)", source)
                self.assertIn(top_module, module_names)
                self.assertGreaterEqual(
                    len(module_names),
                    2,
                    f"{filename} should demonstrate cross-module tracing",
                )


if __name__ == "__main__":
    unittest.main()
