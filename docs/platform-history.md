> 仓库整理说明（2026-10-30）：下文保留原部署/验收背景。公开仓库不带数据集与现有账号配置，首次启动请以根目录 README、docs/data.md 和 weights/README.md 为准。历史案例步骤需另行安装本地数据。

# TerraScope 洪灾道路智能解译与调查平台

这是按照 `方案设计/TerraScope_功能设计与总体技术方案_v1.0.docx` 实现的 P0 前后端工程。系统围绕真实影像、不可变预测、版本化复核和固定报告快照组织，支持普通电脑离线运行历史案例。UI 1.2 采用 Copernicus Browser 的深蓝、白色与绿色配色：左侧 40% 集中导航、参数、统计与复核，右侧 60% 为全高影像及工具按钮。字号、表格与表单统一为紧凑的专业工作台样式。

已实现项目与权限管理、影像上传及案例库、异步分析、OpenLayers 判读工作台、人工复核、实验评估和中文报告导出。历史回放严格匹配影像 SHA256、分区、模型和策略；上传的新影像不能套用样例掩膜。已接入 AutoDL A800 上的完整模型与最终微调权重，支持上传 RGB 影像后执行真实单视图或四视图推理。

## 运行入口

### Docker Compose 主部署

需要 Docker Desktop 或 Docker Engine + Compose，以及用于首次生成配置的 Python 3。

```sh
python3 scripts/configure.py
docker compose up --build -d
python3 scripts/healthcheck.py
```

打开 <http://127.0.0.1:8080>。管理员用户名与随机生成的密码在本机 `.env` 文件中。配置脚本不会覆盖已有 `.env`。首次启动创建管理员、完成 Alembic 迁移并导入 10 幅示范影像；不自动伪造分析结果。

macOS 可运行 `scripts/start-macos.command`；Windows PowerShell 可运行 `scripts/start-windows.ps1`，Docker 必须使用 Linux 容器模式。默认只绑定本机地址；数据库、Redis、API 均不对宿主机开放端口。

### 本地开发

使用 Python 3.12、Node.js 22 或更高版本。业务 Python 从方案中的 3.11 升至 3.12，依赖锁定在本机实际通过验证的组合；GPU 环境保持独立。

```sh
python3.12 -m venv .venv
.venv/bin/python -m pip install -r backend/requirements.lock
cd frontend
npm ci
cd ..
.venv/bin/python scripts/dev.py
```

打开 <http://127.0.0.1:5173>。开发模式使用 SQLite 和独立数据库轮询 Worker，方便未安装 Docker 的电脑验证完整流程；主部署使用 PostgreSQL、Redis 与 Celery。开发模式不是生产部署替代方案。按 Ctrl-C 停止开发服务，`runtime/` 中的数据保留。

本机依赖已安装后，也可双击 `scripts/start-local.command` 启动。源码交付包不包含虚拟环境、node_modules 或运行数据，换机器仍需先安装依赖。

前端同时提交 `package-lock.json` 和 `pnpm-lock.yaml`；可用 `pnpm install --frozen-lockfile`。Docker 和当前 CI 使用 `npm ci`。依赖修改后同步锁文件，不能混用两套不一致的版本。

## AutoDL 真实推理

默认已切换至 A800 028 机（`bb5a41b362-ace379d4`），并用 7611 验证两种真实推理与报告导出。039 的连接保留在 `runtime/autodl-039.json`；028 的独立配置为 `runtime/autodl-028.json`。在 AutoDL 启动该实例并设置定时关机后，双击 `scripts/start-autodl.command`，或执行：

```sh
.venv/bin/python scripts/autodl.py start
.venv/bin/python scripts/dev.py
```

首次 SSH 连接按提示输入 AutoDL 实例密码。页面服务状态自动刷新；模型加载完成后，在“分析设置”选择“本次推理”，上传的 RGB 影像即可直接分析。

推理 API 仅监听服务器 `127.0.0.1:8100`，通过 SSH 加密隧道接到本机 `127.0.0.1:18100`，令牌保存在后端 `.env`。实例地址在 `runtime/autodl.json`。运行 `scripts/autodl.py status` 查看状态，`logs` 查看服务日志，`stop` 停止模型服务，`disconnect` 断开隧道。**停止服务后还需在 AutoDL 控制台关机，才能停止 GPU 计费。**

028 验收记录为 `docs/evidence/autodl-028-acceptance.json`：7611 单视图 109,716 像素、四视图 109,239 像素，两份结果与历史掩膜逐像素一致，四视图 IoU 为 82.35%。

此前已用 7301 完成真实推理验收：单视图 147,010 像素、四视图 152,585 像素，两者与对应历史掩膜逐像素一致。结果、统计、报告及证据包已落库，记录在 `docs/evidence/autodl-acceptance.json`。运行 `.venv/bin/python scripts/verify_autodl.py` 可再次执行两次真实 GPU 作业并验证全流程。

## 完整实验资料

服务器的实验 RGB 与标签已只读同步至 `data/library/`，逐文件校验 SHA256 和像素尺寸。共 1,198 幅：训练 300、验证 80、测试 448、留出 370。895 幅含原始 EXIF 拍摄点，898 幅评估影像各有单视图和四视图预测，共 1,796 份掩膜。实验 RGB 尺寸为 1024 × 685 或 1024 × 768，清单另存原始采集尺寸与来源摘要。

案例库支持 ID 检索、分区与 GPS 筛选、缩略图分页和聚合点位地图；项目影像与工作台均可查看 GPS。GPS 为 WGS 84 相机拍摄点，分割结果保留像素坐标。含 GPS 的报告同时导出 `location.geojson`，坐标顺序为经度、纬度。

同步脚本为 `scripts/export_autodl_dataset.py`（在服务器只读流式打包）与 `scripts/install_dataset.py`（本地校验、生成缩略图、安装索引）。验收清单为 `docs/evidence/dataset-connection.json`。不需要 GPU 即可浏览资料、读取历史预测、复核和导出；选择“本次推理”时开启 AutoDL GPU。

## 小组展示

已完成 7598 新项目的真实 GPU 分析、人工复核和报告导出，并用 6480 验证 GPS；另用 7611 完成视频案例预演。截图与三份展示文档位于工程父目录 `展示交付_20261019/`。详细指标与哈希核验见 `docs/evidence/showcase-acceptance.json`。

## 快速验收

1. 登录，进入示范项目，或创建新项目后从案例库导入 `7301`。
2. 打开工作台，在左侧“分析设置”中选择“历史结果 / 四视图 tta4”，提交分析。
3. 查看预测像素 **152,585**、有效像素 **701,440**、覆盖率 **21.7531%**，并检查来源标签。
4. 在左侧“可视化”中筛选结果日期与来源，切换叠加、卷帘、同步对比，并选择右侧视图的结果版本。点击像素查询 RGB、预测及参考类别。
5. 点击地图右侧“区域选择”，圈选区域，双击或回到首顶点完成；填写依据并保存复核。刷新页面后打开“人工复核”，确认版本与圈选仍存在。
6. 点击地图右侧导出按钮生成报告，下载 PDF、CSV、PNG 和 ZIP 证据包。报告锁定提交时选择的复核版本。
7. 在实验评估页分别检查 448 幅测试集和 370 幅留出集，完整实验库已接入，评估明细可直接导入对应影像并分析。

已保存真实浏览器生成的验收证据：`docs/evidence/7301-evidence.zip` 和 `docs/evidence/workbench.png`。这些是本机验收数据，不能替代目标部署机器的验收。

新版界面结构、配色、响应式行为和稳定性边界见 [UI 设计说明](docs/ui-design.md)。

## 技术栈与目录

| 层 | 实现 |
| --- | --- |
| 前端 | Vue 3、TypeScript、Vite、Vue Router、Pinia、Element Plus、TanStack Vue Query |
| 判读与统计展示 | OpenLayers 像素投影与 GPS 点位地图、ECharts；影像判读可离线，位置底图使用 OpenStreetMap |
| 业务 API | FastAPI、Pydantic、SQLAlchemy 2、Alembic，生成 OpenAPI 与前端类型 |
| 持久化 | PostgreSQL；本地开发支持 SQLite；不可变文件存资产卷 |
| 异步处理 | Celery、Redis，数据库任务表作为持久化投递记录，租约与安全检查点 |
| 图像与报告 | NumPy、Pillow、ReportLab、随包开放中文字体 |
| 模型 | 独立 PyTorch CUDA 服务，RGB-only 推理，权重与业务环境隔离 |
| 工程验证 | pytest、Vitest、Playwright、Docker Compose、GitHub Actions 配置 |

```text
backend/app/          路由、契约、数据库模型、服务、Worker
backend/migrations/   版本化数据库迁移
backend/tests/        真实像素、权限、状态机、复核、导出的集成测试
frontend/src/         页面、API、状态、工作台组件
frontend/tests/       浏览器业务闭环
model_service/        可选 GPU 服务与 RGB 推理实现
data/demo/            10 幅基础示例、六组评估记录、SHA256 清单
data/library/         1,198 幅完整实验 RGB/标签、895 GPS、1,796 预测
data/fonts/           离线中文报告字体与 OFL 许可
infra/                Nginx 同源反向代理
scripts/              配置、启动、健康检查、备份恢复与交付打包
docs/                 架构、部署、用户手册、OpenAPI、验收记录
```

## 工程检查

```sh
PYTHONPATH=backend .venv/bin/python -m alembic -c backend/alembic.ini upgrade head
PYTHONPATH=backend .venv/bin/python -m alembic -c backend/alembic.ini check
PYTHONPATH=backend .venv/bin/pytest backend/tests -q
PYTHONPATH=backend .venv/bin/python -m app.cli openapi > docs/openapi.json
cd frontend
npm run api:types
npm test
npm run build
```

启动本地服务后，运行 `npm run test:e2e`。如未安装 Playwright Chromium，执行 `npx playwright install chromium`；macOS 已安装 Chrome 时可设置 `TERRA_CHROME_PATH=/Applications/Google Chrome.app/Contents/MacOS/Google Chrome`。测试会创建独立验收项目并保存证据，不改写示范项目。

PostgreSQL 集成测试使用专用的 `TERRA_TEST_DATABASE_URL`。测试会删除并重建该连接中的业务表，**只能连接隔离的测试库**。CI 已配置 SQLite/PostgreSQL 测试矩阵，实际 CI 结果以代码仓库执行记录为准。

## 交付边界

已验证本机开发部署、AutoDL A800 真实推理、掩膜复现和完整业务闭环。Docker 五容器部署、PostgreSQL 备份恢复与生产容量测试待在目标部署环境验证。AutoDL 隧道方案用于本机开发模式；Docker 部署需提供容器可访问的 HTTPS 模型入口。

P1/P2 的人工掩膜改写、GeoTIFF/PostGIS 地理能力、面积统计、批量报告、跨事件模型验证、路网分析和在线训练未进入本轮 P0。当前实现是可运行且可验收的基础版本，不等同于已经完成生产环境容量测试、运维演练或行业资质认证。

详细说明见 `docs/architecture.md`、`docs/deployment.md`、`docs/user-guide.md`、`docs/acceptance.md`、`model_service/README.md`。
