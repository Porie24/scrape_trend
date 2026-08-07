import os
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ToolkitEntrypointTests(unittest.TestCase):
    """Structural checks for scripts/toolkit.sh, the macOS/Linux port of the
    original toolkit.ps1. These check the same guarantees the Windows tests
    checked (checkpoint ordering, deliberate-stop handling, Tableau output
    naming) against the bash implementation."""

    @classmethod
    def setUpClass(cls):
        cls.toolkit = (ROOT / "scripts" / "toolkit.sh").read_text(encoding="utf-8")
        cls.bootstrap = (ROOT / "scripts" / "bootstrap-mac.sh").read_text(encoding="utf-8")

    def test_scripts_are_executable(self):
        for name in ("toolkit.sh", "bootstrap-mac.sh"):
            path = ROOT / "scripts" / name
            self.assertTrue(path.exists(), f"{name} missing")
            self.assertTrue(os.access(path, os.X_OK), f"{name} is not executable")

    def test_monthly_run_has_one_human_checkpoint_between_prepare_and_finish(self):
        action = self.toolkit.index("monthly-run)")
        prepare = self.toolkit.index("monthly_prepare", action)
        checkpoint = self.toolkit.index("chrome_checkpoint", prepare)
        finish = self.toolkit.index('monthly_finish ""', checkpoint)
        self.assertLess(prepare, checkpoint)
        self.assertLess(checkpoint, finish)

    def test_chrome_checkpoint_requires_typing_finish(self):
        self.assertIn('"$confirmation" == "FINISH"', self.toolkit)

    def test_monthly_finish_names_the_tableau_ready_output(self):
        self.assertIn(
            "Tableau source: derived/sa_pipeline_v3/series.csv",
            self.toolkit,
        )

    def test_setup_delegates_to_bootstrap_mac(self):
        action = self.toolkit.index("setup)")
        self.assertIn("bootstrap-mac.sh", self.toolkit[action:action + 200])

    def test_adding_a_keyword_has_an_entry_point(self):
        action = self.toolkit.index("add-keyword)")
        block = self.toolkit[action:self.toolkit.index("*)", action)]
        self.assertIn("add_keyword.py", block)
        self.assertIn("--interactive", block)
        self.assertIn("--id-file", block)
        self.assertIn("--finalize", block)

    def test_a_deliberate_stop_is_not_dressed_up_as_a_crash(self):
        # A guard that prints a bash stack trace and tells the maintainer to
        # report it teaches people to ignore guards.
        self.assertIn("code -eq 9", self.toolkit)
        self.assertIn("exit 9", self.toolkit)

    def test_bootstrap_checks_the_four_prerequisites(self):
        for tool in ("Python", "Git", "Chrome", "GitHub"):
            self.assertIn(tool, self.bootstrap)

    def test_bootstrap_does_not_auto_download_x13_on_mac(self):
        # Unlike bootstrap-analysis-windows.ps1, there is no official prebuilt
        # macOS X-13 binary to fetch and hash-verify automatically.
        self.assertNotIn("Invoke-WebRequest", self.bootstrap)
        self.assertIn(".tools/x13/1.1-b62/x13as", self.bootstrap)


if __name__ == "__main__":
    unittest.main()
