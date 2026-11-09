"""Build output stays private even on failure; progress contains no payload."""

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/run_private_step.py"


class PrivateStepTests(unittest.TestCase):
    def invoke(self, program):
        with tempfile.TemporaryDirectory(prefix="ultra-private-step-") as directory:
            log = Path(directory) / "private.log"
            result = subprocess.run(
                [sys.executable, str(SCRIPT), "--label", "device", "--log", str(log),
                 "--heartbeat-seconds", "0.05", "--", sys.executable, "-c", program],
                capture_output=True, text=True, check=False, timeout=10,
            )
            return result, log.read_text(encoding="utf-8")

    def test_stdout_and_stderr_are_not_forwarded_to_public_progress(self):
        result, private = self.invoke("import sys; print('SYNTHETIC_PRIVATE_PAYLOAD'); print('PRIVATE_STDERR', file=sys.stderr)")
        self.assertEqual(result.returncode, 0)
        self.assertIn("SYNTHETIC_PRIVATE_PAYLOAD", private)
        self.assertIn("PRIVATE_STDERR", private)
        self.assertNotIn("SYNTHETIC_PRIVATE_PAYLOAD", result.stdout + result.stderr)
        self.assertNotIn("PRIVATE_STDERR", result.stdout + result.stderr)
        self.assertIn("completed", result.stdout)

    def test_failed_child_status_is_preserved_without_public_error_payload(self):
        result, private = self.invoke("import sys; print('SYNTHETIC_FAILURE_PAYLOAD'); sys.exit(7)")
        self.assertEqual(result.returncode, 7)
        self.assertIn("SYNTHETIC_FAILURE_PAYLOAD", private)
        self.assertNotIn("SYNTHETIC_FAILURE_PAYLOAD", result.stdout + result.stderr)
        self.assertIn("failed", result.stdout)

    def test_longer_work_emits_payload_free_heartbeat(self):
        result, private = self.invoke("import time; print('SYNTHETIC_WAIT_PAYLOAD', flush=True); time.sleep(0.2)")
        self.assertEqual(result.returncode, 0)
        self.assertIn("running, elapsed", result.stdout)
        self.assertIn("SYNTHETIC_WAIT_PAYLOAD", private)
        self.assertNotIn("SYNTHETIC_WAIT_PAYLOAD", result.stdout + result.stderr)
