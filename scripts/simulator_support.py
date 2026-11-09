"""Helpers for disposable, explicitly created CI simulators."""

import json
import os
import signal
import subprocess
import time
from contextlib import contextmanager
from pathlib import Path


def run(*arguments: str) -> str:
    return subprocess.check_output(arguments, text=True).strip()


@contextmanager
def simulator(name: str):
    inventory = json.loads(run("xcrun", "simctl", "list", "-j"))
    artifacts = Path(__file__).resolve().parents[1] / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "startup-simulator-inventory.json").write_text(
        json.dumps(inventory, indent=2), encoding="utf-8"
    )
    runtimes = [
        r
        for r in inventory["runtimes"]
        if r.get("isAvailable")
        and r["identifier"].startswith(
            "com.apple.CoreSimulator.SimRuntime.iOS-"
        )
    ]
    if not runtimes:
        raise RuntimeError("No available iOS simulator runtime")
    # Verified runner inventory: 27.0 is the closest installed runtime to the
    # user's 27.0.1. Avoid the device-specific, dual-display 27.2 runtime.
    matching = [r for r in runtimes if r["version"] == "27.0"]
    if not matching:
        raise RuntimeError(
            "Required iOS 27.0 simulator runtime is unavailable"
        )
    runtime = matching[0]
    # Reuse a supported model, never an existing device or its account data.
    names = {
        d["name"]
        for d in inventory["devices"].get(runtime["identifier"], [])
        if d.get("isAvailable") and d.get("name", "").startswith("iPhone")
    }
    compatible = [d for d in inventory["devicetypes"] if d["name"] in names]
    if not compatible:
        raise RuntimeError("No compatible iPhone model in simulator inventory")
    device_type = next(d for d in compatible if d["name"] == "iPhone 17")
    print("Simulator:", runtime["version"], device_type["name"], flush=True)
    udid = run(
        "xcrun",
        "simctl",
        "create",
        name,
        device_type["identifier"],
        runtime["identifier"],
    )
    try:
        subprocess.run(["xcrun", "simctl", "boot", udid], check=True)
        boot_status = run("xcrun", "simctl", "bootstatus", udid, "-b")
        print(boot_status)
        if "Data Migration Failed" in boot_status:
            raise RuntimeError(
                "Simulator boot reported a data migration failure"
            )
        subprocess.run(
            [
                "xcrun",
                "simctl",
                "io",
                udid,
                "screenshot",
                str(artifacts / "startup-simulator-baseline.png"),
            ],
            check=True,
            timeout=180,
        )
        yield udid, runtime["version"]
    finally:
        # Only this new simulator is touched; no user simulator is selected.
        subprocess.run(["xcrun", "simctl", "shutdown", udid], check=False)
        subprocess.run(["xcrun", "simctl", "delete", udid], check=False)


@contextmanager
def recording(udid: str, output: Path):
    log_path = output.with_suffix(".log")
    with log_path.open("w") as log:
        process = subprocess.Popen(
            [
                "xcrun",
                "simctl",
                "io",
                udid,
                "recordVideo",
                "--codec=h264",
                "--force",
                str(output),
            ],
            stdout=log,
            stderr=log,
        )
        completed = False
        try:
            # Launch while the recorder connects to the headless display.
            # Validate the recording after capture, not just process startup.
            yield
            completed = True
        finally:
            if process.poll() is None:
                process.send_signal(signal.SIGINT)
                process.wait(timeout=20)
        if completed and (
            "Recording started" not in log_path.read_text()
            or not output.exists()
            or output.stat().st_size == 0
        ):
            raise RuntimeError("No simulator recording; inspect recorder log")


def screenshot_text(udid: str, path: Path) -> str:
    subprocess.run(
        ["xcrun", "simctl", "io", udid, "screenshot", str(path)], check=True
    )
    environment = dict(os.environ, OMP_THREAD_LIMIT="1")
    for attempt in range(2):
        try:
            text = subprocess.check_output(
                # Sauvola preserves the faint diagnostic code; a single text
                # block also reads the light-on-dark consent screen reliably.
                [
                    "tesseract", str(path), "stdout", "-l", "eng",
                    "--psm", "6", "-c", "thresholding_method=2",
                ],
                text=True,
                timeout=60,
                env=environment,
            ).strip()
            break
        except subprocess.TimeoutExpired:
            if attempt == 1:
                raise
    path.with_suffix(".txt").write_text(text, encoding="utf-8")
    return text


def wait_stage(udid: str, bundle_id: str, stage: str, output: Path) -> None:
    container = Path(
        run("xcrun", "simctl", "get_app_container", udid, bundle_id, "data")
    )
    report = (
        container / "Library/Application Support/ULTRA-Diagnostics/startup.txt"
    )
    deadline = time.monotonic() + 120
    while time.monotonic() < deadline:
        text = report.read_text(encoding="utf-8") if report.exists() else ""
        output.write_text(text, encoding="utf-8")
        if f"\nstage={stage}\n" in text:
            return
        time.sleep(1)
    raise RuntimeError(f"Startup did not reach {stage}; inspect {output.name}")
