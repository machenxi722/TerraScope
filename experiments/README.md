# 实验方案、设置与复现索引

当前任务为 FloodNet 航拍 RGB 的受淹道路分割。早期问答、水体分割及面积估计记录方案演进，不与最终道路指标混用。

| 阶段 | 代码与原始记录 | 当前用途 |
| --- | --- | --- |
| 选题与技术审查 | `../docs/proposals/`、`technical-review/`、`../archive/early-research/` | 论证与历史来源 |
| 水体微调工具包 | `legacy-water-toolkit/` | Sen1Floods11 独立历史方案 |
| 固定提示基线、投影/解码器微调、LoRA 三种子 | `work/finetune_backups_20261015/formal/` | 初轮基线与对照 |
| 边界、道路辅助、组合及额外模块 | `work/finetune_backups_20261015/{boundary,road_aux,combined,module}/` | 消融，最终未采用 |
| BCE+Dice / BCE+Lovász 各三种子 | `work/night_20261016/backup/` | 最终权重来源 |
| 额外 370 幅 | `work/night_20261016/holdout_backup/` | 同事件留出 |
| 四视图平均 | `work/night_20261016/tta_backup/` | 最终推理策略 |
| 跨种子参数平均 | `work/night_20261016/soup_backup/` | 对照，未采用 |
| 自动空间提示 | `work/sam_prompt_pilot_20261016/backup/` | 开关对照未证明增益 |
| 汇报与结果图 | `work/*talk*`、`work/editorial_v2_20261016/`、`reports/`、`summaries/` | 绘图源码与成品 |

具体实验子目录中的 `protocol.json` 为当时设置，`manifest.json` 为样本划分与摘要，`results/` 为逐检查点结果及预测。`code_sha256.json`、`result_sha256.json` 是原服务器记录，部分指向没有交接到本地的权重，不是本次归档完整性清单。

## 最终设置

见 [configs/final.json](configs/final.json) 和 [原始训练协议](work/night_20261016/backup/protocol.json)。训练 300（162 幅有目标）、验证 80（30）、测试 448（49）、留出 370（23）。818 幅评估 = 448 + 370，不含验证 80。

冻结主干，训练投影层和 SAM2 解码器；每微步一幅，正负样本各 50% 有放回抽样；水平/垂直翻转及亮度/对比度 0.9–1.1 增强；BF16 自动混合精度，可训练参数 FP32。AdamW、累计 4 步、warmup 20 次更新、每 800 微步验证。最终采用种子 20261017、BCE+Lovász、第 4,800 微步单检查点。

全局 IoU 汇总全部有效像元的 TP/FP/FN，不是逐图平均。覆盖率 MAE 单位百分点。448 测试集曾用于探索；额外留出仍来自同一事件。详见 [指标口径与结论边界](summaries/指标口径与结论边界.md)。

## 复现顺序

1. 阅读结果不需要 GPU 或数据：先看 `summaries/01_最终实验/最终方案选择.json` 和 `work/night_20261016/tta_backup/results/`。
2. 最终模型推理按 [权重说明](../weights/README.md) 准备底座与增量，使用维护中的 `model_service/engine.py` 和 HTTP 服务。
3. 重训时复制 `work/night_20261016/backup/` 到新的工作目录，避免覆盖归档 `results/`；准备完整数据为 `data/<id>/RGB.jpg` 与 `labels.png`。保留 `manifest.json` 原字节和 SHA256，不重新随机划分。
4. 原脚本底座路径为 `/root/autodl-tmp/terrascope/models/TerraScope`，按实际环境修改运行副本。协议 `deadline_epoch` 是历史截止时间，需要更新并记录变更，其他设置与 `maximum_run_seconds` 保留。
5. 在配置好的 CUDA 环境中运行 `python train_night.py`。记录新运行的环境、时间、代码摘要及结果，不覆盖旧证据。
6. 原始 `eval_tta.py` 依赖同级 `night_20261016/` 和 `night_holdout_20261016/` 的报告、检查点与单视图预测以逐像素核验。重建完整评估需恢复服务器目录关系；只做业务推理用独立 `model_service`。

这些是实验审计快照，部分绘图脚本、模块导入和命令依赖原目录或额外软件。克隆仓库不能自动补齐原始数据、完整底座及缺失的其他 checkpoint。归档没有重跑训练。
