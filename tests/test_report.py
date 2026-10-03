from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from rtl_impact_explorer.report import export_report
from rtl_impact_explorer.verilator_json import load_design


FIXTURES = Path(__file__).parent / "fixtures"


class ReportExportTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.design = load_design(
            FIXTURES / "counter_top.tree.json",
            FIXTURES / "counter_top.tree.meta.json",
        )

    def test_exports_a_fetch_free_report_with_versioned_data(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report"

            result = export_report(self.design, output, title="Counter impact map")

            self.assertEqual(result, output / "index.html")
            self.assertEqual(
                {path.name for path in output.iterdir()},
                {
                    "index.html",
                    "styles.css",
                    "app.js",
                    "graph-view.js",
                    "design-data.js",
                },
            )
            assignment = (output / "design-data.js").read_text(encoding="utf-8")
            prefix = "window.RTL_IMPACT_DATA = "
            self.assertTrue(assignment.startswith(prefix))
            payload = json.loads(assignment.removeprefix(prefix).removesuffix(";\n"))
            self.assertEqual(payload["schemaVersion"], 1)
            self.assertEqual(payload["design"]["name"], "counter_top")
            self.assertEqual(payload["summary"]["modules"], 2)
            self.assertEqual(payload["summary"]["signals"], 11)
            self.assertTrue(
                any(
                    signal["id"] == "counter_top.active_o"
                    for signal in payload["signals"]
                )
            )

    def test_report_markup_is_local_and_accessible(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report"
            export_report(self.design, output)

            markup = (output / "index.html").read_text(encoding="utf-8")
            self.assertIn('<main class="workspace"', markup)
            self.assertIn('aria-label="Search signals"', markup)
            self.assertIn('aria-live="polite"', markup)
            self.assertNotIn("https://", markup)
            self.assertNotIn("fetch(", (output / "app.js").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
