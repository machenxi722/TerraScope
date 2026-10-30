> 仓库整理说明（2026-10-30）：下文保留原部署/验收背景。公开仓库不带数据集与现有账号配置，首次启动请以根目录 README、docs/data.md 和 weights/README.md 为准。历史案例步骤需另行安装本地数据。

# 部署与运维手册

## 配置与启动

首次运行 `python3 scripts/configure.py` 生成随机管理员密码和数据库密码。`.env` 不进入交付包或版本控制。Compose 将业务参数以环境变量传给 API 和 Worker。数据库地址只在容器内构造，不提供给前端。

执行 `docker compose up --build -d`。API 先执行数据库迁移与幂等初始化，健康检查通过后启动 Worker 和 web。用 `docker compose ps`、`docker compose logs --tail=100 api worker` 查看服务状态；用 `python3 scripts/healthcheck.py` 检查 API。管理员初始用户名默认 admin，密码从 `.env` 读取。

首次构建需要网络获取依赖和镜像；运行时案例、前端、字体和报告不依赖外网。首次启动也必须离线时，应先在相同 CPU 架构的联网机器执行构建，再用 `docker image save` 保存 `docker compose config --images` 列出的全部镜像，目标机器 `docker image load` 后执行 `docker compose up --no-build -d`。amd64 与 arm64 必须分别验证，不把另一架构的测试结果当作已验证支持。

软件版本和数据版本在系统设置页显示。当前 CPU 并发配置为 1，避免小内存设备同时展开多个大图。增加并发前先测量图像内存占用和数据库负载。

## 外部访问

默认只提供本机访问。远程访问需要部署者配置可信域名、HTTPS 入口与相应网络访问范围，并把域名加入 `TERRA_ALLOWED_HOSTS`。启用 `TERRA_SECURE_COOKIES=true`。反向代理必须传递正确 Host 与协议，FastAPI 只应信任受控代理的 forwarded headers。当前默认配置没有自动配置公网域名、TLS 证书或外部暴露。

## 数据持久化

`database` 卷保存 PostgreSQL 数据，`assets` 卷保存影像、结果、证据包，`redis` 卷保存队列。`docker compose down` 不删除卷。不要使用 `down -v` 清理正常运行项目。任务以数据库为真源，Redis 丢失后调度器可重新投递未完成任务。

本地开发数据保存在 `runtime/app.db` 与 `runtime/assets`。停止 API 和 Worker 后整体复制 `runtime/` 可备份开发实例；运行中的 SQLite 文件需要使用 SQLite backup API，不能只复制主数据库文件而遗漏 WAL。

## 备份与恢复

```sh
python3 scripts/backup.py backup /absolute/path/terrascope-backup.tar.gz
python3 scripts/backup.py restore /absolute/path/terrascope-backup.tar.gz --replace-current-data
```

备份短暂停止 API 和 Worker，使用 pg_dump 获取数据库快照并打包资产，最后恢复进程。备份不包含 `.env`，由部署负责人单独保管配置。恢复会替换数据库内容，必须使用独立路径保留当前备份，并在隔离环境演练。恢复脚本检查归档成员路径，数据库恢复采用事务；数据库和文件卷之间没有分布式原子恢复，应在停机期间完成并验证资产摘要后再开放访问。

资产下载和分析均执行摘要校验。出现 ASSET_MISSING 或 ASSET_CHECKSUM 时从备份恢复对应文件，不手工改写数据库哈希来掩盖损坏。工作进程中断后等待租约到期，确认任务阶段日志；需要人工重试时使用任务页按钮，旧记录会保留。

## 日志与升级

```sh
docker compose logs --no-color api worker > service-logs.txt
docker compose build
docker compose up -d
```

升级前备份。迁移脚本在 `backend/migrations/versions`，API 启动执行 `upgrade head`。多副本升级时应独立运行迁移作业，避免多个 API 同时迁移；当前 Compose 使用单 API 实例。开发 `.env` 中已存在的管理员不会因重启而重置密码。

## 已知验证范围

当前机器已验证本地开发运行、迁移、核心测试和浏览器流程。Docker/Redis/Celery/PostgreSQL 配置已提供，CI 设有 PostgreSQL 测试矩阵，但本机没有 Docker，未运行容器组合及备份恢复演练。部署验收需记录镜像版本、CPU 架构、内存、系统版本、查询 p95、切图 p95 和报告耗时。


## 本机接入 AutoDL

已完成 039 机 A800 实机验证。先在 AutoDL 控制台启动实例并设置定时关机，再运行 `scripts/start-autodl.command`。模型服务通过 SSH 隧道接入本机后端，前端入口仍为 `http://127.0.0.1:5173`。

实例参数保存在 `runtime/autodl.json`，模型令牌保存在 `.env`。升级用 `.venv/bin/python scripts/autodl.py deploy`；状态、日志、停止分别使用 `status`、`logs`、`stop`。停止服务或 SSH 后仍需在 AutoDL 控制台关机以停止计费。模型路径、HTTP 契约及完整操作见 `model_service/README.md`。

此隧道仅用于本机开发进程。Compose 内的 `127.0.0.1` 属于容器自身，部署容器时使用容器可访问的 HTTPS 模型入口。
