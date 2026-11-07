"""Check confidentiality and safe artifact restoration."""

import importlib.util
import os
import subprocess
import tempfile
import unittest
import zipfile
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "sealed_artifacts", ROOT / "scripts/sealed_artifacts.py"
)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class SealedArtifactsTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temporary = tempfile.TemporaryDirectory(prefix="ultra-seal-test-")
        self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name)
        self.key = self.root / "identity.txt"
        result = subprocess.run(
            ["age-keygen", "-o", str(self.key)],
            capture_output=True, check=True,
        )
        self.key.chmod(0o600)
        result = subprocess.run(
            ["age-keygen", "-y", str(self.key)],
            capture_output=True, check=True,
        )
        self.recipient = self.root / "recipient.txt"
        self.recipient.write_bytes(result.stdout)
        self.inputs = self.root / "artifacts"
        self.inputs.mkdir()
        self.payload = os.urandom(256) + b"PRIVATE-BUILD-CONTENT"
        (self.inputs / "client.ipa").write_bytes(self.payload)
        self.encrypted = self.root / "release.zip.age"
        self.output = self.root / "restored"

    def seal(self) -> None:
        MODULE.seal([self.inputs], self.encrypted, self.recipient)

    def restore(self, identity=None) -> None:
        MODULE.restore(
            self.encrypted, self.output, identity or self.key, None
        )

    def test_round_trip_hides_payload_and_restores_exact_bytes(self) -> None:
        self.seal()
        self.assertNotIn(self.payload, self.encrypted.read_bytes())
        self.restore()
        self.assertEqual(
            (self.output / "artifacts/client.ipa").read_bytes(), self.payload
        )

    def test_wrong_private_key_creates_no_output(self) -> None:
        self.seal()
        wrong = self.root / "wrong.txt"
        subprocess.run(
            ["age-keygen", "-o", str(wrong)],
            capture_output=True, check=True,
        )
        with self.assertRaises(RuntimeError):
            self.restore(wrong)
        self.assertFalse(self.output.exists())

    def test_ciphertext_tampering_creates_no_output(self) -> None:
        self.seal()
        data = bytearray(self.encrypted.read_bytes())
        data[-20] ^= 1
        self.encrypted.write_bytes(data)
        with self.assertRaises(RuntimeError):
            self.restore()
        self.assertFalse(self.output.exists())

    def test_path_traversal_is_rejected_before_extraction(self) -> None:
        malicious = self.root / "malicious.zip"
        with zipfile.ZipFile(malicious, "w") as archive:
            archive.writestr("artifacts/valid.txt", "first")
            archive.writestr("../escaped.txt", "escape")
        subprocess.run(
            [
                "age", "-R", str(self.recipient), "-o",
                str(self.encrypted), str(malicious),
            ],
            capture_output=True, check=True,
        )
        with self.assertRaises(ValueError):
            self.restore()
        self.assertFalse(self.output.exists())
        self.assertFalse((self.root / "escaped.txt").exists())

    def test_existing_local_files_are_not_overwritten(self) -> None:
        self.seal()
        self.restore()
        target = self.output / "artifacts/client.ipa"
        target.write_bytes(b"KEEP")
        with self.assertRaises(FileExistsError):
            self.restore()
        self.assertEqual(target.read_bytes(), b"KEEP")

    def test_missing_environment_secret_does_not_restore(self) -> None:
        self.seal()
        with patch.dict(os.environ, {}, clear=True):
            with self.assertRaises(ValueError):
                MODULE.restore(
                    self.encrypted, self.output, None,
                    "ULTRA_TEST_ARTIFACT_IDENTITY",
                )
        self.assertFalse(self.output.exists())


if __name__ == "__main__":
    unittest.main()
