"""Create local credentials once; never overwrite an existing configuration."""

import secrets
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def configure():
    target = ROOT / ".env"
    if not target.exists():
        content = (
            (ROOT / ".env.example")
            .read_text()
            .replace("replace-with-at-least-12-characters", secrets.token_urlsafe(24))
            .replace(
                "replace-with-a-long-random-database-password", secrets.token_hex(24)
            )
        )
        with target.open("x") as stream:
            stream.write(content)
        target.chmod(0o600)
    print("配置文件已就绪：.env；管理员用户名和密码请从该文件读取。")


if __name__ == "__main__":
    configure()
