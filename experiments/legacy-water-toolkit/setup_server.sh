#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")"
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install torch==2.3.1 torchvision==0.18.1 --index-url https://download.pytorch.org/whl/cu121
python -m pip install -r requirements-server.txt
python -m pip check
python -m pytest -q tests
python -m pip freeze > installed-environment.txt
python - <<'PY'
import torch
print('Torch:', torch.__version__, 'CUDA:', torch.version.cuda)
print('GPU:', torch.cuda.get_device_name() if torch.cuda.is_available() else 'NO CUDA')
print('BF16:', torch.cuda.is_available() and torch.cuda.is_bf16_supported())
PY
