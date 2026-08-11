from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import importlib.util
from pathlib import Path
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]


def load(name, relative):
    spec = importlib.util.spec_from_file_location(name, ROOT / relative)
    module = importlib.util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


mr11 = load("mr11_cli", "skills/MM/sap-mr11-simulation-export/scripts/mr11_simulation_export.py")
f05 = load("f05_cli", "skills/FI/sap-f05-log-export/scripts/f05_log_export.py")


class SafeReportCliTests(unittest.TestCase):
    def test_mr11_dry_run_requires_policy_and_accepts_explicit_unvalidated_profile(self):
        with tempfile.TemporaryDirectory() as directory:
            output = StringIO()
            with redirect_stdout(output):
                code = mr11.main([
                    "--company-code", "1000", "--key-date", "2026-08-01",
                    "--variant", "Z01", "--output-dir", directory,
                    "--allow-unvalidated-profile", "--dry-run",
                ])
        self.assertEqual(code, 0)
        self.assertIn('"sap_mode": "simulation"', output.getvalue())

    def test_mr11_has_no_posting_mode(self):
        choices = next(action.choices for action in mr11.build_parser()._actions if action.dest == "run_mode")
        self.assertEqual(tuple(choices), ("validate", "full"))

    def test_f05_defaults_existing_log_and_requires_run_id(self):
        with tempfile.TemporaryDirectory() as directory:
            error = StringIO()
            with redirect_stderr(error):
                code = f05.main(["--output-dir", directory, "--allow-unvalidated-profile", "--dry-run"])
        self.assertEqual(code, 2)
        self.assertIn("requires --run-id", error.getvalue())

    def test_f05_test_run_dry_run(self):
        with tempfile.TemporaryDirectory() as directory:
            output = StringIO()
            with redirect_stdout(output):
                code = f05.main([
                    "--mode", "test-run", "--company-code", "1000",
                    "--valuation-key-date", "2026-08-01", "--output-dir", directory,
                    "--allow-unvalidated-profile", "--dry-run",
                ])
        self.assertEqual(code, 0)
        self.assertIn('"mode": "test-run"', output.getvalue())


if __name__ == "__main__":
    unittest.main()
