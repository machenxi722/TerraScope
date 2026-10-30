"""Supervisor for local API + durable CPU worker + Vite. Ctrl-C stops all children."""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from configure import configure

ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / ".venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
NPM = "npm.cmd" if os.name == "nt" else "npm"


def main():
    os.chdir(ROOT)
    configure()
    if not PYTHON.exists() or not (ROOT / "frontend/node_modules").exists():
        sys.exit("请先按 README 安装 Python 与 Node 依赖。")
    env = {**os.environ, "PYTHONPATH": str(ROOT / "backend")}
    for command in [
        [str(PYTHON), "-m", "alembic", "-c", "backend/alembic.ini", "upgrade", "head"],
        [str(PYTHON), "-m", "app.cli", "init", "--demo-if-present"],
    ]:
        subprocess.run(command, env=env, check=True)
    children = []
    try:
        children.append(
            subprocess.Popen(
                [
                    str(PYTHON),
                    "-m",
                    "uvicorn",
                    "app.main:app",
                    "--host",
                    "127.0.0.1",
                    "--port",
                    "8000",
                ],
                env=env,
            )
        )
        children.append(subprocess.Popen([str(PYTHON), "-m", "app.worker"], env=env))
        children.append(
            subprocess.Popen([NPM, "run", "dev"], cwd=ROOT / "frontend", env=env)
        )
        print("TerraScope 本地开发入口：http://127.0.0.1:5173", flush=True)
        while all(p.poll() is None for p in children):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        for p in children:
            if p.poll() is None:
                p.terminate()
        for p in children:
            try:
                p.wait(timeout=8)
            except subprocess.TimeoutExpired:
                p.kill()
        print("开发服务已停止。业务数据仍保存在 runtime/。")


if __name__ == "__main__":
    main()
