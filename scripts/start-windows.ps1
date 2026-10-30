$ErrorActionPreference = 'Stop'
Set-Location (Join-Path $PSScriptRoot '..')
python scripts/configure.py
if ($LASTEXITCODE -ne 0) { throw '初始化配置失败' }
docker compose up --build -d
if ($LASTEXITCODE -ne 0) { throw '容器启动失败，请检查 Docker Desktop 状态' }
docker compose ps
Start-Process 'http://127.0.0.1:8080'
