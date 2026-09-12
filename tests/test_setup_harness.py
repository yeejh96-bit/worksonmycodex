from __future__ import annotations

import hashlib
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "works-on-my-codex" / "scripts" / "setup_harness.py"
START = "<!-- womc:project-harness:start -->"


def run(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(SCRIPT), "--project", str(project), *args],
        capture_output=True,
        text=True,
        check=False,
    )


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


class SetupHarnessTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.project = Path(self.temp.name)
        subprocess.run(["git", "init", "-q", str(self.project)], check=True)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_empty_git_project_is_created_and_idempotent(self) -> None:
        first = run(self.project, "--purpose", "A tiny notes app")
        self.assertEqual(first.returncode, 0, first.stderr)
        agents = self.project / "AGENTS.md"
        content = agents.read_text(encoding="utf-8")
        self.assertIn("Empty starter repository", content)
        self.assertIn("A tiny notes app", content)
        self.assertEqual(content.count(START), 1)
        before = digest(agents)

        second = run(self.project, "--purpose", "A tiny notes app")
        self.assertEqual(second.returncode, 0, second.stderr)
        self.assertIn("unchanged", second.stdout)
        self.assertEqual(digest(agents), before)

    def test_existing_agents_and_source_are_preserved(self) -> None:
        original_agents = "# Team rules\n\nKeep this exact line.\n"
        (self.project / "AGENTS.md").write_text(original_agents, encoding="utf-8")
        source = self.project / "app.js"
        source.write_text("export const value = 1;\n", encoding="utf-8")
        package = self.project / "package.json"
        package.write_text(
            '{"scripts":{"lint":"node --check app.js","test":"node --test",'
            '"dev":"node app.js","test:e2e":"node --test"},'
            '"devDependencies":{"vite":"1.0.0"}}\n',
            encoding="utf-8",
        )
        source_before = digest(source)
        package_before = digest(package)

        result = run(self.project)
        self.assertEqual(result.returncode, 0, result.stderr)
        content = (self.project / "AGENTS.md").read_text(encoding="utf-8")
        self.assertTrue(content.startswith(original_agents))
        self.assertIn("`npm run lint`", content)
        self.assertIn("`npm run test`", content)
        self.assertIn("`npm run test:e2e`", content)
        self.assertIn("start the app with `npm run dev`", content)
        self.assertEqual(digest(source), source_before)
        self.assertEqual(digest(package), package_before)

        before = digest(self.project / "AGENTS.md")
        self.assertEqual(run(self.project).returncode, 0)
        self.assertEqual(digest(self.project / "AGENTS.md"), before)

        if shutil.which("npm"):
            for script in ("lint", "test", "test:e2e", "dev"):
                validation = subprocess.run(
                    ["npm", "run", script], cwd=self.project, capture_output=True, text=True, check=False
                )
                self.assertEqual(validation.returncode, 0, validation.stderr)

    def test_malformed_markers_stop_without_writing(self) -> None:
        agents = self.project / "AGENTS.md"
        agents.write_text(f"User content\n{START}\nbroken\n", encoding="utf-8")
        before = digest(agents)
        result = run(self.project)
        self.assertEqual(result.returncode, 2)
        self.assertIn("marker conflict", result.stderr)
        self.assertEqual(digest(agents), before)

    def test_nonempty_root_override_is_updated_instead_of_ignored_agents(self) -> None:
        override = self.project / "AGENTS.override.md"
        original = "# Temporary root override\n\nKeep this rule.\n"
        override.write_text(original, encoding="utf-8")

        result = run(self.project, "--purpose", "An override-aware project")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((self.project / "AGENTS.md").exists())
        content = override.read_text(encoding="utf-8")
        self.assertTrue(content.startswith(original))
        self.assertEqual(content.count(START), 1)

        before = digest(override)
        self.assertEqual(run(self.project, "--purpose", "An override-aware project").returncode, 0)
        self.assertEqual(digest(override), before)

    def test_check_reports_drift_without_writing(self) -> None:
        result = run(self.project, "--check")
        self.assertEqual(result.returncode, 1)
        self.assertFalse((self.project / "AGENTS.md").exists())


if __name__ == "__main__":
    unittest.main()
