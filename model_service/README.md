> 仓库整理说明（2026-10-30）：下文为历史 GPU 部署和验收记录；当前克隆后的权重准备及启动请先看 `../weights/README.md`。本仓库不附现有 SSH/令牌配置。

# 独立 GPU 服务

已在 AutoDL A800 039 机完成实机验收。基础模型约 32.13 GB，30 个文件；最终增量约 72 MB。沿用 `/root/terrascope-env/bin/python`（Python 3.10.8、PyTorch 2.3.1、Transformers 4.42.3），API 依赖单独安装，固定版本见 `requirements.api.lock`。

## 现有部署

| 项目 | 路径或地址 |
| --- | --- |
| 基础模型 | `/root/autodl-tmp/terrascope/models/TerraScope` |
| 最终增量 | `/root/autodl-tmp/terrascope/night_20261016/results/long_bce_lovasz_seed20261017_best_delta.pt` |
| 独立服务 | `/root/terrascope-platform/releases/` |
| 配置、日志、作业与校验清单 | `/root/terrascope-platform/shared/` |
| 服务器 API | `127.0.0.1:8100` |
| 本地 SSH 隧道 | `127.0.0.1:18100` |

部署复用原始权重，不运行训练脚本，不修改既有实验文件。增量 SHA256 为 `7c70b717815a39b66c052748c44256b685d17ef1513ee482084ce6419d93dfa8`；完整底座清单见 `../docs/evidence/autodl-base-manifest.json`。

## 启动与更新

1. 在 AutoDL 控制台启动实例并设置定时关机。
2. 本地执行 `.venv/bin/python scripts/autodl.py start`。该命令复用 SSH 会话、建立本机端口转发并启动单进程模型服务。
3. 执行 `.venv/bin/python scripts/dev.py` 启动前后端，页面自动显示模型加载和就绪状态。
4. 更新代码时执行 `scripts/autodl.py deploy`，再执行 `stop`、`start`。每次部署生成新版本目录，API 依赖与模型环境隔离。
5. 完成后执行 `scripts/autodl.py stop`、`scripts/autodl.py disconnect`，并在 AutoDL 控制台关机。服务停止和断开 SSH 不会停止实例计费。

新电脑安装业务依赖后，将 `scripts/autodl.example.json` 复制为 `runtime/autodl.json`，核对 SSH 地址和端口，再执行 `deploy`。脚本生成后端令牌与服务配置，已有配置中的令牌会继续使用。SSH 密码交互输入，不写入项目配置。

`status` 返回运行状态、GPU 名称与队列长度；`logs` 显示最近 60 行日志；`inventory` 保存模型目录、依赖和增量摘要。实例关机后，历史和已完成的真实推理结果仍可在本机查看、复核和导出。

## 推理协议

指令为 `Segment the flooded roads in this aerial image.`，固定前缀为 `The flooded road regions are [SEG]`。底座冻结，仅加载 SEG 投影和 SAM2 掩膜解码器增量，校验键集合与张量尺寸。

四视图为原图、水平翻转、垂直翻转和双向翻转；logits 逆变换后平均，再双线性恢复原尺寸，以 `logit > 0` 二值化。接口只接收 RGB，不接收标签。

## HTTP 接口

所有请求携带 `Authorization: Bearer <token>`。上传最大 20 MiB、25 MP；默认最多 8 个待执行/执行中作业。

| 接口 | 行为 |
| --- | --- |
| `GET /health` | 就绪状态、模型摘要、设备、队列与执行数；加载期间仍可查询 |
| `POST /inference-jobs` | multipart `image` + JSON `config`，携带 `Idempotency-Key`；同键同配置复用作业，不同配置返回 409 |
| `GET /inference-jobs/{id}` | 状态、排队位置；成功后返回配置、掩膜摘要、底座清单摘要、设备和耗时 |
| `POST /inference-jobs/{id}/cancel` | 排队作业立即取消；运行作业在视图边界取消 |
| `GET /inference-jobs/{id}/mask` | 原尺寸单通道 0/255 PNG，仅成功作业可下载 |

作业状态：`QUEUED → RUNNING → SUCCEEDED / FAILED`；取消进入 `CANCELED`，运行中先标记 `CANCEL_REQUESTED`。SQLite 持久化作业；重启后恢复未完成作业。业务后端自动恢复短暂轮询断线，核验输入、配置和输出摘要后生成不可变结果。

连接方式默认为 HTTPS；本次使用 `TERRA_MODEL_TRANSPORT=ssh_tunnel`，仅允许明确指定端口的 `http://127.0.0.1`。模型凭据不进入前端。Docker 需另配容器可访问的 HTTPS 入口。

## 实机验收

`.venv/bin/python scripts/verify_autodl.py` 经业务 API 上传 7301 RGB，执行单视图与四视图，核对原尺寸掩膜、幂等提交、统计及 PDF/ZIP 导出。两种输出与历史参考逐像素一致；四视图覆盖率 21.7531%。完整作业 ID、耗时和摘要见 `../docs/evidence/autodl-acceptance.json`。该脚本会创建独立验收项目并消耗 GPU 时间。

单元测试使用测试引擎和隔离数据库，不连接真实 GPU。页面验收可运行 `TERRA_VERIFY_LIVE_UI=1 npm run test:e2e`，默认跳过需要在线 GPU 状态的页面检查。
