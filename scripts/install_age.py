"""Install the pinned upstream age binaries on the macOS ARM runner."""

import hashlib
import io
import os
import platform
import subprocess
import tarfile
import urllib.request
from pathlib import Path


def main() -> None:
    if platform.system() != "Darwin" or platform.machine() != "arm64":
        raise RuntimeError("This installer requires the macOS ARM runner")
    url = (
        "https://github.com/FiloSottile/age/releases/download/v1.3.2/"
        "age-v1.3.2-darwin-arm64.tar.gz"
    )
    expected = (
        "e2020b073c44f692685a24d6abc378817"
        "eb81ffaaf49fd0531ef8565f767f2f5"
    )
    with urllib.request.urlopen(url, timeout=90) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError("age release checksum mismatch")
    destination = Path(os.environ["RUNNER_TEMP"]) / "ultra-age"
    destination.mkdir(exist_ok=True)
    with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as archive:
        for name in ("age", "age-keygen"):
            member = archive.getmember(f"age/{name}")
            if not member.isfile():
                raise ValueError("Unexpected age package member")
            source = archive.extractfile(member)
            if source is None:
                raise ValueError("Missing age package data")
            path = destination / name
            path.write_bytes(source.read())
            path.chmod(0o755)
    with Path(os.environ["GITHUB_PATH"]).open("a", encoding="utf-8") as path:
        path.write(str(destination) + "\n")
    subprocess.run([str(destination / "age"), "--version"], check=True)


if __name__ == "__main__":
    main()
