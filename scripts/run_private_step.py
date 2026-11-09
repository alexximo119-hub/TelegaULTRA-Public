"""Run a build with private output and a public, payload-free heartbeat."""

import argparse
import math
import os
import signal
import subprocess
import time
from pathlib import Path


def stop_process(process):
    if process.poll() is not None:
        return
    try:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGTERM)
        else:
            process.terminate()
        process.wait(timeout=10)
    except subprocess.TimeoutExpired:
        if os.name == "posix":
            os.killpg(process.pid, signal.SIGKILL)
        else:
            process.kill()
        process.wait(timeout=10)
    except ProcessLookupError:
        pass


def run(command, log, label, interval):
    started = time.monotonic()
    log.parent.mkdir(parents=True, exist_ok=True)
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(log, flags, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        options = {"start_new_session": True} if os.name == "posix" else {
            "creationflags": subprocess.CREATE_NO_WINDOW
        }
        try:
            process = subprocess.Popen(command, stdout=output,
                                       stderr=subprocess.STDOUT, **options)
        except OSError as error:
            output.write(str(error))
            print(f"ULTRA {label}: could not start; details are in the encrypted log.", flush=True)
            return 1

        def interrupted(_signum, _frame):
            raise KeyboardInterrupt

        previous = signal.signal(signal.SIGTERM, interrupted)
        try:
            print(f"ULTRA {label}: started.", flush=True)
            while True:
                try:
                    code = process.wait(timeout=interval)
                    break
                except subprocess.TimeoutExpired:
                    elapsed = int(time.monotonic() - started)
                    print(f"ULTRA {label}: running, elapsed {elapsed}s.", flush=True)
        except KeyboardInterrupt:
            stop_process(process)
            print(f"ULTRA {label}: cancelled.", flush=True)
            return 130
        finally:
            signal.signal(signal.SIGTERM, previous)
        elapsed = int(time.monotonic() - started)
        status = "completed" if code == 0 else "failed"
        print(f"ULTRA {label}: {status}, elapsed {elapsed}s; details are in the encrypted log.", flush=True)
        return code if code >= 0 else 128 - code


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--label", required=True, choices=["simulator", "device"])
    parser.add_argument("--log", required=True, type=Path)
    parser.add_argument("--heartbeat-seconds", type=float, default=60)
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args()
    command = args.command[1:] if args.command[:1] == ["--"] else args.command
    if not command or not math.isfinite(args.heartbeat_seconds) or not 0.01 <= args.heartbeat_seconds <= 300:
        parser.error("A command and a finite heartbeat interval are required")
    return run(command, args.log, args.label, args.heartbeat_seconds)


if __name__ == "__main__":
    raise SystemExit(main())
