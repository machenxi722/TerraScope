# 2026-10-30 归档验证

验证对象为整理后的仓库副本，原工作目录保持不变。

| 检查 | 结果 |
| --- | --- |
| 无数据集后端测试 | 10 passed，13 skipped；跳过项均需真实示例影像 |
| 指向原本地 demo 的完整后端测试 | 23 passed；数据只从外部读取，未复制进 Git |
| 前端 Vitest | 3 个文件、9 项测试通过 |
| TypeScript 与 Vite production build | 通过；有大于 500 kB 的分块体积提示 |
| SQLite Alembic upgrade / check | 通过，无待补迁移 |
| 最终权重 | 71,979,524 字节，SHA256 与原模型服务硬编码及实验记录一致 |
| 数据与敏感文件 | 排除原图、标签、数据 ZIP、运行数据库、SSH 配置、`.env`；扫描文本及 Office XML 未发现现有密码/令牌或私钥格式 |

测试使用原工程已安装的 Python 3.12 / Node 依赖，前端检查基于其 node_modules；依赖与构建输出不提交。FastAPI 测试客户端有上游 httpx 弃用提示，未影响断言。

此次未重新启动 GPU、重新训练、执行付费推理；未在 Docker 或 PostgreSQL 上实机验收，也未重新运行需要案例库与在线 GPU 的浏览器回放。历史记录保存在 `docs/evidence/`，不要把历史结果当作此次重跑结果。

当前发布文件的逐项 SHA256 由 `file-manifest.json` 保存（清单本身不自校验），下载 LFS 文件后用 `scripts/verify_repository.py` 检查。安装本地数据或修改源码后，清单出现差异是预期行为。
