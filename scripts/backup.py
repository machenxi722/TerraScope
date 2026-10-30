"""Consistent whole-instance backup/restore for Compose. Restore is explicit and stops writers."""

import argparse
import subprocess
import tarfile
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(args, **kwargs):
    return subprocess.run(["docker", "compose", *args], cwd=ROOT, check=True, **kwargs)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=["backup", "restore"])
    parser.add_argument("path", type=Path)
    parser.add_argument("--replace-current-data", action="store_true")
    args = parser.parse_args()
    if args.command == "restore" and not args.replace_current_data:
        parser.error(
            "恢复会替换当前数据；必须显式指定 --replace-current-data，先保留独立备份。"
        )
    if args.command == "backup" and args.path.exists():
        parser.error("备份目标已存在；请选择新文件名。")
    run(["stop", "api", "worker"])
    try:
        with tempfile.TemporaryDirectory(prefix="terra-backup-") as directory:
            temp = Path(directory)
            if args.command == "backup":
                with (temp / "database.dump").open("wb") as stream:
                    run(
                        [
                            "exec",
                            "-T",
                            "postgres",
                            "pg_dump",
                            "-U",
                            "terra",
                            "-d",
                            "terrascope",
                            "-Fc",
                        ],
                        stdout=stream,
                    )
                with (temp / "assets.tar").open("wb") as stream:
                    run(
                        [
                            "run",
                            "--rm",
                            "--no-deps",
                            "-T",
                            "--entrypoint",
                            "tar",
                            "api",
                            "-C",
                            "/app/runtime/assets",
                            "-cf",
                            "-",
                            ".",
                        ],
                        stdout=stream,
                    )
                with tarfile.open(args.path, "w:gz") as archive:
                    for name in ["database.dump", "assets.tar"]:
                        archive.add(temp / name, arcname=name)
            else:
                with tarfile.open(args.path, "r:gz") as archive:
                    if sorted(archive.getnames()) != ["assets.tar", "database.dump"]:
                        raise ValueError("不是 TerraScope 备份格式")
                    archive.extractall(temp, filter="data")
                with tarfile.open(temp / "assets.tar") as archive:
                    for member in archive.getmembers():
                        path = Path(member.name)
                        if (
                            path.is_absolute()
                            or ".." in path.parts
                            or not (member.isfile() or member.isdir())
                        ):
                            raise ValueError("资产备份包含不安全的成员路径或链接")
                with (temp / "database.dump").open("rb") as stream:
                    run(
                        [
                            "exec",
                            "-T",
                            "postgres",
                            "pg_restore",
                            "-U",
                            "terra",
                            "-d",
                            "terrascope",
                            "--clean",
                            "--if-exists",
                            "--exit-on-error",
                            "--single-transaction",
                        ],
                        stdin=stream,
                    )
                with (temp / "assets.tar").open("rb") as stream:
                    run(
                        [
                            "run",
                            "--rm",
                            "--no-deps",
                            "-T",
                            "--entrypoint",
                            "tar",
                            "api",
                            "-C",
                            "/app/runtime/assets",
                            "-xf",
                            "-",
                        ],
                        stdin=stream,
                    )
    finally:
        run(["start", "api", "worker"])


if __name__ == "__main__":
    main()
