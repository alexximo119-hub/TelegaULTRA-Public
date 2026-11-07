"""Check both missing-group paths in the complete simulator client."""

import argparse
import json
import plistlib
import re
import subprocess
import tempfile
import time
import zipfile
from pathlib import Path

from simulator_support import recording, screenshot_text, simulator, wait_stage


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ipa", type=Path)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    artifacts = root / "artifacts"
    with tempfile.TemporaryDirectory(
        prefix="ultra-full-startup-"
    ) as directory:
        with zipfile.ZipFile(args.ipa) as archive:
            archive.extractall(directory)
        apps = list((Path(directory) / "Payload").glob("*.app"))
        if len(apps) != 1:
            raise ValueError("Expected one simulator app")
        app = apps[0]
        for path in app.rglob("*"):
            if path.is_file() and path.suffix == "":
                path.chmod(path.stat().st_mode | 0o111)
        info = plistlib.loads((app / "Info.plist").read_bytes())
        bundle_id = info["CFBundleIdentifier"]
        if info.get("ULTRAAllowLocalStorage") is not True:
            raise ValueError("Simulator main app lacks the local-storage flag")
        framework = app / (
            "Frameworks/TelegramUIFramework.framework/TelegramUIFramework"
        )
        if b"--ultra-ci-no-app-group" not in framework.read_bytes():
            raise ValueError("Simulator app lacks the DEBUG test controls")
        with simulator("ULTRA Full Client Startup") as (udid, runtime):
            subprocess.run(
                ["xcrun", "simctl", "install", udid, str(app)], check=True
            )
            cases = [
                (
                    "consent",
                    ["--ultra-ci-no-app-group"],
                    "APP_GROUP_UNAVAILABLE",
                ),
                (
                    "local",
                    ["--ultra-ci-no-app-group", "--ultra-ci-local-storage"],
                    "AUTH_UI_READY",
                ),
            ]
            for name, launch_args, stage in cases:
                with recording(udid, artifacts / f"startup-full-{name}.mp4"):
                    subprocess.run(
                        [
                            "xcrun",
                            "simctl",
                            "launch",
                            udid,
                            bundle_id,
                            *launch_args,
                        ],
                        check=True,
                    )
                    try:
                        wait_stage(
                            udid,
                            bundle_id,
                            stage,
                            artifacts / f"startup-full-{name}-report.txt",
                        )
                    finally:
                        time.sleep(3)
                        text = screenshot_text(
                            udid, artifacts / f"startup-full-{name}.png"
                        )
                compact = re.sub(r"[^A-Z0-9]", "", text.upper())
                if name == "consent":
                    if (
                        "APPGROUPUNAVAILABLE" not in compact
                        or "ULTRA" not in compact
                    ):
                        raise RuntimeError(
                            "Storage consent screen was not visible"
                        )
                elif "STARTMESSAGING" not in compact:
                    raise RuntimeError("Welcome screen was not visible")
                subprocess.run(
                    ["xcrun", "simctl", "terminate", udid, bundle_id],
                    check=True,
                )
            (artifacts / "startup-full-verification.json").write_text(
                json.dumps(
                    {
                        "runtime": runtime,
                        "missing_app_group_consent_visible": True,
                        "local_storage_auth_screen_visible": True,
                        "real_device_verified": False,
                        "signed_gbox_ipa_verified": False,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )


if __name__ == "__main__":
    main()
