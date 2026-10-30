"""TerraScope AutoDL deployment and SSH tunnel. Instance billing is controlled in AutoDL."""

import argparse
import hashlib
import io
import json
import secrets
import shlex
import subprocess
import tarfile
from pathlib import Path

from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action",
        choices=[
            "connect",
            "disconnect",
            "inventory",
            "deploy",
            "start",
            "stop",
            "status",
            "logs",
        ],
    )
    parser.add_argument("--profile", type=Path, default=ROOT / "runtime/autodl.json")
    args = parser.parse_args()
    profile = json.loads(args.profile.read_text())
    runtime = args.profile.parent
    socket = profile.get(
        "control_socket",
        "/tmp/terrascope-"
        + hashlib.sha256(str(ROOT).encode()).hexdigest()[:12]
        + ".sock",
    )
    target = profile.get("user", "root") + "@" + profile["host"]
    options = [
        "-S",
        socket,
        "-p",
        str(profile["port"]),
        "-o",
        "ConnectTimeout=15",
        "-o",
        "ServerAliveInterval=30",
        "-o",
        "ServerAliveCountMax=3",
        "-o",
        "UserKnownHostsFile=" + str(runtime / "autodl-known-hosts"),
        "-o",
        "StrictHostKeyChecking=accept-new",
    ]
    ssh = ["ssh", *options]

    def remote(command, data=None, capture=False):
        return subprocess.run(
            [*ssh, target, command],
            input=data,
            check=True,
            stdout=subprocess.PIPE if capture else None,
        ).stdout

    if args.action == "disconnect":
        subprocess.run([*ssh, "-O", "exit", target], check=True)
        return
    check = subprocess.run(
        [*ssh, "-O", "check", target], capture_output=True, check=False
    )
    if check.returncode:
        subprocess.run(
            [*ssh, "-M", "-o", "ControlPersist=7200", "-fnNT", target], check=True
        )
    forward = f"127.0.0.1:{profile.get('local_port', 18100)}:127.0.0.1:{profile.get('remote_port', 8100)}"
    # Re-issuing an existing forward is harmless; a new connection must fail if the port is occupied.
    forwarded = subprocess.run(
        [*ssh, "-O", "forward", "-L", forward, target], capture_output=True, check=False
    )
    if forwarded.returncode:
        raise SystemExit("SSH 隧道创建失败，请检查本地端口占用。")
    if args.action == "connect":
        print(f"SSH 隧道已连接：127.0.0.1:{profile.get('local_port', 18100)}")
        return
    if args.action == "inventory":
        data = remote(
            shlex.quote(profile["python"]) + " -",
            (ROOT / "scripts/autodl_inventory.py").read_bytes(),
            True,
        )
        (runtime / "autodl-inventory.json").write_bytes(data)
        print(data.decode())
        return
    base = profile["service_root"]
    q = shlex.quote
    if args.action == "deploy":
        payload = io.BytesIO()
        files = sorted(
            p
            for p in (ROOT / "model_service").rglob("*")
            if p.is_file() and "__pycache__" not in p.parts
        )
        files += [
            ROOT / "scripts/model_manifest.py",
            ROOT / "scripts/autodl_inventory.py",
        ]
        with tarfile.open(fileobj=payload, mode="w:gz") as archive:
            for path in files:
                archive.add(path, arcname=str(path.relative_to(ROOT)))
        content = payload.getvalue()
        revision = hashlib.sha256(content).hexdigest()[:12]
        release = base + "/releases/" + revision
        remote(
            f"mkdir -p {q(release)} {q(base + '/shared')} && tar -xz -C {q(release)}",
            content,
        )
        lock = ROOT / "model_service/requirements.api.lock"
        installed = remote(
            f"{q(profile['python'])} -m pip freeze --path {q(base + '/shared/vendor')}",
            capture=True,
        )
        vendor = base + "/shared/vendor"
        if sorted(installed.decode().splitlines()) != sorted(
            lock.read_text().splitlines()
        ):
            vendor += "-" + hashlib.sha256(lock.read_bytes()).hexdigest()[:12]
            remote(
                f"test -d {q(vendor)} || {q(profile['python'])} -m pip install --index-url https://pypi.org/simple --no-cache-dir --target {q(vendor)} -r {q(release + '/model_service/requirements.api.lock')}"
            )
        manifest = base + "/shared/base-manifest.json"
        remote(
            f"test -s {q(manifest)} || {q(profile['python'])} {q(release + '/scripts/model_manifest.py')} {q(profile['base_path'])} {q(manifest)}"
        )
        env = dotenv_values(ROOT / ".env")
        token = env.get("TERRA_MODEL_SERVICE_TOKEN") or secrets.token_urlsafe(40)
        config = {
            "port": profile.get("remote_port", 8100),
            "vendor_dir": vendor,
            "environment": {
                "MODEL_API_TOKEN": token,
                "MODEL_BASE_PATH": profile["base_path"],
                "MODEL_DELTA_PATH": profile["delta_path"],
                "MODEL_BASE_MANIFEST": manifest,
                "MODEL_JOB_DIR": base + "/shared/jobs",
            },
        }
        remote(
            "umask 077; cat > " + q(base + "/shared/config.json"),
            json.dumps(config).encode(),
        )
        for key, value in {
            "TERRA_MODEL_SERVICE_URL": f"http://127.0.0.1:{profile.get('local_port', 18100)}",
            "TERRA_MODEL_SERVICE_TOKEN": token,
            "TERRA_MODEL_TRANSPORT": "ssh_tunnel",
        }.items():
            set_key(ROOT / ".env", key, value)
        (ROOT / ".env").chmod(0o600)
        profile["release"] = release
        args.profile.write_text(json.dumps(profile, indent=2) + "\n")
        print("已部署独立服务：" + release)
        return
    if args.action == "logs":
        remote("tail -n 60 " + q(base + "/shared/service.log"))
        return
    remote(
        " ".join(
            map(
                q,
                [
                    profile["python"],
                    profile["release"] + "/model_service/control.py",
                    args.action,
                    "--config",
                    base + "/shared/config.json",
                ],
            )
        )
    )


if __name__ == "__main__":
    main()
