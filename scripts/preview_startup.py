"""Render the real startup failure view in an isolated iOS simulator."""

import plistlib
import re
import subprocess
import tempfile
import time
from pathlib import Path

from simulator_support import (
    recording,
    run,
    screenshot_text,
    simulator,
    wait_stage,
)


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    source = root / "source"
    artifacts = root / "artifacts"
    artifacts.mkdir(exist_ok=True)
    with simulator("ULTRA Startup Preview") as (udid, runtime):
        with tempfile.TemporaryDirectory(prefix="ultra-startup-") as directory:
            app = Path(directory) / "UltraStartupPreview.app"
            app.mkdir()
            executable = "UltraStartupPreview"
            bundle_id = "app.telegaultra.startup-preview"
            info = {
                "CFBundleIdentifier": bundle_id,
                "CFBundleExecutable": executable,
                "CFBundleName": "ULTRA Preview",
                "CFBundleVersion": "1",
                "CFBundleShortVersionString": "1.0",
                "CFBundlePackageType": "APPL",
                "MinimumOSVersion": "15.0",
                "LSRequiresIPhoneOS": True,
                "UIDeviceFamily": [1],
                "UILaunchScreen": {},
                "UIApplicationSceneManifest": {
                    "UIApplicationSupportsMultipleScenes": False,
                    "UISceneConfigurations": {
                        "UIWindowSceneSessionRoleApplication": [
                            {
                                "UISceneConfigurationName": (
                                    "Default Configuration"
                                ),
                                "UISceneDelegateClassName": (
                                    "UltraPreviewSceneDelegate"
                                ),
                            }
                        ]
                    },
                },
            }
            (app / "Info.plist").write_bytes(plistlib.dumps(info))
            sdk = run("xcrun", "--sdk", "iphonesimulator", "--show-sdk-path")
            ui_source = source / "submodules/TelegramUI/Sources"
            subprocess.run(
                [
                    "xcrun",
                    "--sdk",
                    "iphonesimulator",
                    "swiftc",
                    "-parse-as-library",
                    "-sdk",
                    sdk,
                    "-target",
                    "arm64-apple-ios15.0-simulator",
                    str(ui_source / "UltraStartupFailureViewController.swift"),
                    str(ui_source / "UltraStartupDiagnostics.swift"),
                    str(source / "Tests/UltraStartupPreview/App.swift"),
                    "-o",
                    str(app / executable),
                ],
                check=True,
            )
            subprocess.run(
                ["xcrun", "simctl", "install", udid, str(app)], check=True
            )
            cases = [
                ("startup-preview", "light", [], "APP_GROUP_UNAVAILABLE"),
                (
                    "startup-preview-consent-dark",
                    "dark",
                    [],
                    "APP_GROUP_UNAVAILABLE",
                ),
                (
                    "startup-preview-error-light",
                    "light",
                    ["--preview-no-consent"],
                    "KEYCHAIN_UNAVAILABLE",
                ),
                (
                    "startup-preview-error-dark",
                    "dark",
                    ["--preview-no-consent"],
                    "KEYCHAIN_UNAVAILABLE",
                ),
                (
                    "startup-preview-progress-light",
                    "light",
                    ["--preview-progress"],
                    "PRESENTATION_LOADING",
                ),
                (
                    "startup-preview-progress-dark",
                    "dark",
                    ["--preview-progress"],
                    "PRESENTATION_LOADING",
                ),
            ]
            for prefix, appearance, arguments, stage in cases:
                run("xcrun", "simctl", "ui", udid, "appearance", appearance)
                with recording(udid, artifacts / f"{prefix}.mp4"):
                    subprocess.run(
                        [
                            "xcrun",
                            "simctl",
                            "launch",
                            udid,
                            bundle_id,
                            *arguments,
                        ],
                        check=True,
                    )
                    wait_stage(
                        udid,
                        bundle_id,
                        stage,
                        artifacts / f"{prefix}-report.txt",
                    )
                    time.sleep(3)
                    text = screenshot_text(udid, artifacts / f"{prefix}.png")
                compact = re.sub(r"[^A-Z0-9]", "", text.upper())
                if (
                    stage.replace("_", "") not in compact
                    or "ULTRA" not in compact
                ):
                    raise RuntimeError(
                        f"Diagnostic screen not visible: {prefix}"
                    )
                subprocess.run(
                    ["xcrun", "simctl", "terminate", udid, bundle_id],
                    check=True,
                )
                print(f"Verified {prefix} on iOS {runtime}.", flush=True)


if __name__ == "__main__":
    main()
