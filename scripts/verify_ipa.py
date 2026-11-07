"""Verify the packaged main app identity and diagnostics."""

import argparse
import hashlib
import json
import plistlib
import zipfile
from pathlib import Path


def verify(ipa_path: Path, build_number: str) -> dict:
    root = Path(__file__).resolve().parents[1]
    lock = json.loads((root / "source.lock.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(ipa_path) as ipa:
        main_plists = [
            n
            for n in ipa.namelist()
            if n.startswith("Payload/")
            and n.count("/") == 2
            and n.endswith(".app/Info.plist")
        ]
        if len(main_plists) != 1:
            raise ValueError("Expected exactly one main application")
        info = plistlib.loads(ipa.read(main_plists[0]))
        expected = {
            "CFBundleDisplayName": "ULTRA",
            "CFBundleName": "ULTRA",
            "CFBundleIdentifier": lock["bundle_id"],
            "CFBundleVersion": build_number,
            "CFBundleShortVersionString": lock["app_version"],
            "ULTRAAllowLocalStorage": True,
        }
        for key, value in expected.items():
            if info.get(key) != value:
                raise ValueError(
                    f"Main app {key} does not match required value {value!r}"
                )
        scenes = (
            info.get("UIApplicationSceneManifest", {})
            .get("UISceneConfigurations", {})
            .get("UIWindowSceneSessionRoleApplication", [])
        )
        if not any(
            s.get("UISceneDelegateClassName") == "SceneDelegate"
            for s in scenes
        ):
            raise ValueError("Main app is missing its scene delegate")
        framework = main_plists[0].removesuffix("Info.plist") + (
            "Frameworks/TelegramUIFramework.framework/TelegramUIFramework"
        )
        binary = ipa.read(framework)
        if b"--ultra-ci-" in binary:
            raise ValueError(
                "Simulator-only startup controls leaked into iPhone IPA"
            )
        # Swift can encode <=15-byte strings inline in optimized instructions.
        # Check long, persistent strings here; AUTH_UI_READY is checked at
        # runtime by check_full_startup.py, not by a raw binary substring.
        markers = (
            b"APP_GROUP_UNAVAILABLE",
            b"ULTRA startup diagnostics v1",
            b"ultra.appStorageMode.v1",
        )
        missing = [m.decode("ascii") for m in markers if m not in binary]
        if missing:
            raise ValueError(f"Missing packaged diagnostic markers: {missing}")
        return {
            "ipa_sha256": hashlib.sha256(ipa_path.read_bytes()).hexdigest(),
            "main_app": expected,
            "scene_delegate": "SceneDelegate",
            "diagnostic_markers_present": True,
            "diagnostic_markers": [m.decode("ascii") for m in markers],
            "short_auth_marker_raw_presence": b"AUTH_UI_READY" in binary,
            "device_launch_verified": False,
            "gbox_entitlements_verified": False,
        }


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("ipa", type=Path)
    parser.add_argument("--build-number", required=True)
    parser.add_argument("--report", type=Path, required=True)
    args = parser.parse_args()
    result = verify(args.ipa, args.build_number)
    args.report.write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(
        "Packaged main-app identity, storage and diagnostics verified."
    )
