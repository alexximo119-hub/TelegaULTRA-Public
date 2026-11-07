"""Encrypt CI artifacts with age; restore only with a matching private key."""

import argparse
import os
import shutil
import stat
import subprocess
import tempfile
import zipfile
from contextlib import contextmanager
from pathlib import Path, PurePosixPath


def run_age(command: list[str]) -> None:
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode:
        # Never echo tool output or secret-bearing file contents into CI logs.
        raise RuntimeError("age operation failed; no plaintext was published")


def seal(includes: list[Path], output: Path, recipient: Path) -> None:
    output = output.resolve()
    recipient = recipient.resolve()
    if not recipient.is_file():
        raise ValueError("Missing public artifact recipient")
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ultra-seal-") as directory:
        directory = Path(directory)
        bundle = directory / "bundle.zip"
        names = set()
        with zipfile.ZipFile(bundle, "w", zipfile.ZIP_STORED) as archive:
            for base in includes:
                base = base.resolve()
                if not base.exists():
                    continue
                if not base.is_dir():
                    raise ValueError("Artifact inputs must be directories")
                for path in sorted(base.rglob("*")):
                    if path.is_symlink():
                        raise ValueError("Symlinks are not artifact inputs")
                    if not path.is_file():
                        continue
                    if not path.resolve().is_relative_to(base):
                        raise ValueError("Artifact escaped input directory")
                    name = str(
                        PurePosixPath(base.name, *path.relative_to(base).parts)
                    )
                    if name in names:
                        raise ValueError("Duplicate archive member")
                    names.add(name)
                    archive.write(path, name)
        if not names:
            raise ValueError("No files to seal")
        encrypted = directory / "bundle.zip.age"
        run_age([
            "age", "--encrypt", "--recipients-file", str(recipient),
            "--output", str(encrypted), str(bundle),
        ])
        # Cross-volume moves are possible on Windows; copy only ciphertext.
        temporary = output.with_name(output.name + ".tmp")
        shutil.copyfile(encrypted, temporary)
        temporary.replace(output)


@contextmanager
def identity_file(path: Path | None, environment: str | None):
    if path is not None:
        if not path.is_file():
            raise ValueError("Missing artifact identity file")
        yield path.resolve()
        return
    value = os.environ.get(environment or "", "")
    if not value.strip():
        raise ValueError("Artifact decryption secret is missing")
    with tempfile.TemporaryDirectory(prefix="ultra-key-") as directory:
        identity = Path(directory) / "identity.txt"
        descriptor = os.open(
            identity, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(value)
        yield identity


def restore(
    encrypted: Path,
    output: Path,
    identity: Path | None,
    environment: str | None,
) -> None:
    output = output.resolve()
    with identity_file(identity, environment) as key:
        with tempfile.TemporaryDirectory(prefix="ultra-open-") as directory:
            bundle = Path(directory) / "bundle.zip"
            run_age([
                "age", "--decrypt", "--identity", str(key),
                "--output", str(bundle), str(encrypted.resolve()),
            ])
            with zipfile.ZipFile(bundle) as archive:
                entries = []
                names = set()
                total = 0
                for member in archive.infolist():
                    name = PurePosixPath(member.filename)
                    mode = member.external_attr >> 16
                    if (
                        "\\" in member.filename
                        or ":" in member.filename
                        or name.is_absolute()
                        or not name.parts
                        or ".." in name.parts
                        or stat.S_ISLNK(mode)
                        or member.filename in names
                    ):
                        raise ValueError("Unsafe encrypted archive member")
                    names.add(member.filename)
                    target = output.joinpath(*name.parts)
                    if not target.resolve().is_relative_to(output):
                        raise ValueError("Archive target escaped output")
                    if target.exists() and not member.is_dir():
                        raise FileExistsError("Restore would overwrite a file")
                    total += member.file_size
                    if total > 4 * 1024**3:
                        raise ValueError("Encrypted archive exceeds size cap")
                    entries.append((member, target))
                # Validate all destinations before writing any payload file.
                for member, target in entries:
                    if member.is_dir():
                        target.mkdir(parents=True, exist_ok=True)
                    else:
                        target.parent.mkdir(parents=True, exist_ok=True)
                        with (
                            archive.open(member) as source,
                            target.open("xb") as dest,
                        ):
                            shutil.copyfileobj(source, dest)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    encrypt = commands.add_parser("seal")
    encrypt.add_argument(
        "--include", action="append", type=Path, required=True
    )
    encrypt.add_argument("--output", type=Path, required=True)
    encrypt.add_argument("--recipient", type=Path, required=True)
    decrypt = commands.add_parser("open")
    decrypt.add_argument("--input", type=Path, required=True)
    decrypt.add_argument("--output", type=Path, required=True)
    key = decrypt.add_mutually_exclusive_group(required=True)
    key.add_argument("--identity", type=Path)
    key.add_argument("--identity-env")
    args = parser.parse_args()
    if args.command == "seal":
        seal(args.include, args.output, args.recipient)
        print("Encrypted artifact ready; plaintext remains outside uploads.")
    else:
        restore(args.input, args.output, args.identity, args.identity_env)
        print("Encrypted artifact restored with the private identity.")


if __name__ == "__main__":
    main()
