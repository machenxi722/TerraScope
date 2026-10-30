"""Manage only this deployment's inference process; never starts/stops the AutoDL instance."""

import argparse
import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from urllib.request import Request, urlopen


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "stop", "status"])
    parser.add_argument("--config", type=Path, required=True)
    args = parser.parse_args()
    config = json.loads(args.config.read_text())
    shared = args.config.parent
    pidfile = shared / "service.pid"
    release = Path(__file__).resolve().parents[1]
    pid = int(pidfile.read_text()) if pidfile.exists() else None

    def alive():
        if not pid:
            return False
        try:
            command = Path(f"/proc/{pid}/cmdline").read_bytes()
            cwd = Path(f"/proc/{pid}/cwd").resolve()
            return (
                b"model_service.server:app" in command and cwd.parent == release.parent
            )
        except (OSError, ValueError):
            return False

    if args.action == "stop":
        if alive():
            os.kill(pid, signal.SIGTERM)
            for _ in range(40):
                if not alive():
                    break
                time.sleep(0.25)
            if alive():
                raise SystemExit(
                    "Service is finishing a GPU operation; check status before stopping the instance."
                )
        pidfile.unlink(missing_ok=True)
        print(json.dumps({"running": False}))
        return
    if args.action == "start" and not alive():
        env = {
            **os.environ,
            **config["environment"],
            "PYTHONPATH": config.get("vendor_dir", str(shared / "vendor")),
            "HF_HUB_OFFLINE": "1",
            "TRANSFORMERS_OFFLINE": "1",
            "TOKENIZERS_PARALLELISM": "false",
            "PYTHONUNBUFFERED": "1",
        }
        with (shared / "service.log").open("ab") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    "-m",
                    "uvicorn",
                    "model_service.server:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    str(config.get("port", 8100)),
                    "--workers",
                    "1",
                ],
                cwd=release,
                env=env,
                stdin=subprocess.DEVNULL,
                stdout=log,
                stderr=log,
                start_new_session=True,
            )
        pid = process.pid
        pidfile.write_text(str(pid))
        print(json.dumps({"running": True, "pid": pid, "state": "starting"}))
        return
    result = {"running": alive(), "pid": pid}
    if result["running"]:
        try:
            request = Request(
                f"http://127.0.0.1:{config.get('port', 8100)}/health",
                headers={
                    "Authorization": "Bearer "
                    + config["environment"]["MODEL_API_TOKEN"]
                },
            )
            with urlopen(request, timeout=3) as response:
                result.update(json.load(response))
        except OSError:
            result["state"] = "starting"
    print(json.dumps(result))


if __name__ == "__main__":
    main()
