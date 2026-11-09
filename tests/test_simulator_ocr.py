"""OCR retries a transient timeout without accepting missing screen evidence."""

import importlib.util
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / "scripts/simulator_support.py"
SPEC = importlib.util.spec_from_file_location("simulator_support", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SimulatorOCRTests(unittest.TestCase):
    def invoke(self, results):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "screen.png"
            with (
                patch.object(MODULE.subprocess, "run") as capture,
                patch.object(MODULE.subprocess, "check_output", side_effect=results) as ocr,
            ):
                result = MODULE.screenshot_text("test-simulator", path)
                self.assertEqual(path.with_suffix(".txt").read_text(), result)
                capture.assert_called_once()
                for call in ocr.call_args_list:
                    self.assertEqual(call.kwargs["env"]["OMP_THREAD_LIMIT"], "1")
                    self.assertEqual(call.kwargs["timeout"], 60)
                    self.assertEqual(call.args[0][-4:],
                                     ["--psm", "6", "-c", "thresholding_method=2"])
                return result, ocr.call_count

    def test_success_keeps_recognized_text(self):
        self.assertEqual(self.invoke(["  ULTRA APP_GROUP_UNAVAILABLE\n"]),
                         ("ULTRA APP_GROUP_UNAVAILABLE", 1))

    def test_transient_timeout_gets_one_retry(self):
        timeout = subprocess.TimeoutExpired("tesseract", 60)
        self.assertEqual(self.invoke([timeout, "ULTRA"]), ("ULTRA", 2))

    def test_persistent_timeout_fails_without_writing_evidence(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "screen.png"
            with (
                patch.object(MODULE.subprocess, "run"),
                patch.object(MODULE.subprocess, "check_output",
                             side_effect=subprocess.TimeoutExpired("tesseract", 60)) as ocr,
            ):
                with self.assertRaises(subprocess.TimeoutExpired):
                    MODULE.screenshot_text("test-simulator", path)
                self.assertEqual(ocr.call_count, 2)
                self.assertFalse(path.with_suffix(".txt").exists())
