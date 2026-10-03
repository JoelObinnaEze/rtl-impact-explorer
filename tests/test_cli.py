from __future__ import annotations

import io
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from rtl_impact_explorer.cli import main


FIXTURES = Path(__file__).parent / "fixtures"


class CliTests(unittest.TestCase):
    def test_analyze_json_generates_a_report(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "report"
            stdout = io.StringIO()
            stderr = io.StringIO()

            with redirect_stdout(stdout), redirect_stderr(stderr):
                exit_code = main(
                    [
                        "analyze-json",
                        str(FIXTURES / "counter_top.tree.json"),
                        "--meta",
                        str(FIXTURES / "counter_top.tree.meta.json"),
                        "--output",
                        str(output),
                        "--title",
                        "Counter review",
                    ]
                )

            self.assertEqual(exit_code, 0)
            self.assertEqual(stderr.getvalue(), "")
            self.assertIn("Report ready:", stdout.getvalue())
            self.assertTrue((output / "index.html").exists())

    def test_analyze_json_returns_a_concise_error_without_a_traceback(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            invalid = Path(directory) / "bad.json"
            invalid.write_text("[]", encoding="utf-8")
            stderr = io.StringIO()

            with redirect_stderr(stderr):
                exit_code = main(
                    ["analyze-json", str(invalid), "--output", directory]
                )

            self.assertEqual(exit_code, 1)
            self.assertTrue(stderr.getvalue().startswith("error: "))
            self.assertNotIn("Traceback", stderr.getvalue())

    def test_analyze_rejects_missing_source_files_before_running_a_tool(self) -> None:
        stderr = io.StringIO()

        with redirect_stderr(stderr):
            exit_code = main(
                [
                    "analyze",
                    "missing.sv",
                    "--top",
                    "top",
                    "--output",
                    "report",
                ]
            )

        self.assertEqual(exit_code, 1)
        self.assertIn("source file not found", stderr.getvalue())

    def test_analyze_reports_sources_on_incompatible_filesystem_volumes(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "top.sv"
            source.write_text("module top; endmodule\n", encoding="utf-8")
            stderr = io.StringIO()

            with (
                patch(
                    "rtl_impact_explorer.cli.os.path.commonpath",
                    side_effect=ValueError("Paths do not share a volume"),
                ),
                redirect_stderr(stderr),
            ):
                exit_code = main(
                    [
                        "analyze",
                        str(source),
                        "--top",
                        "top",
                        "--output",
                        str(Path(directory) / "report"),
                    ]
                )

        self.assertEqual(exit_code, 1)
        self.assertIn("same filesystem volume", stderr.getvalue())


if __name__ == "__main__":
    unittest.main()
