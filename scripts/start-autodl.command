#!/bin/zsh
set -eu
cd "$(dirname "$0")/.."
echo "请先在 AutoDL 控制台启动 028 机并设置定时关机。"
.venv/bin/python scripts/autodl.py start
exec .venv/bin/python scripts/dev.py
