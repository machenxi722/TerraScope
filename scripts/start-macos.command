#!/bin/zsh
set -eu
cd "$(dirname "$0")/.."
python3 scripts/configure.py
docker compose up --build -d
docker compose ps
open "http://127.0.0.1:8080"
