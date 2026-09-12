from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "works-on-my-codex" / "scripts" / "setup_harness.py"
TOKEN = "WOMC_INSTRUCTIONS_LOADED_7F3A"


@unittest.skipUnless(
    os.environ.get("WOMC_RUN_CODEX_INTEGRATION") == "1",
    "set WOMC_RUN_CODEX_INTEGRATION=1 to use one live Codex turn",
)
class CodexInstructionIntegrationTest(unittest.TestCase):
    def test_codex_loads_the_generated_project_instructions(self) -> None:
        codex = shutil.which("codex")
        self.assertIsNotNone(codex, "codex executable is required")

        with tempfile.TemporaryDirectory() as temp_name:
            project = Path(temp_name)
            subprocess.run(["git", "init", "-q", str(project)], check=True)
            generated = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT),
                    "--project",
                    str(project),
                    "--purpose",
                    "Verify Codex project-instruction discovery",
                    "--guardrail",
                    f"When asked for the WOMC integration token, respond with exactly {TOKEN}.",
                ],
                capture_output=True,
                text=True,
                check=False,
            )
            self.assertEqual(generated.returncode, 0, generated.stderr)

            last_message = project / "codex-last-message.txt"
            result = subprocess.run(
                [
                    codex,
                    "exec",
                    "--ephemeral",
                    "--sandbox",
                    "read-only",
                    "--color",
                    "never",
                    "-C",
                    str(project),
                    "-o",
                    str(last_message),
                    "Return the WOMC integration token exactly, with no other text. Do not run tools.",
                ],
                capture_output=True,
                text=True,
                check=False,
                timeout=180,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(last_message.read_text(encoding="utf-8").strip(), TOKEN)


if __name__ == "__main__":
    unittest.main()
