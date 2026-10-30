# 系统架构与实现约束

主部署由 web、api、worker、postgres、redis 五个容器组成。Nginx 提供前端并把 `/api/` 转发至 FastAPI，浏览器始终同源访问。CPU Worker 处理真实历史掩膜、外部掩膜、统计、图件和报告；GPU 服务独立接入；服务器部署使用 HTTPS，本机 AutoDL 部署使用 SSH 加密隧道与 Bearer 令牌。

## 数据与代码分层

`routers` 负责请求、项目权限和协议响应；`schemas` 负责输入与输出约束；`services` 负责影像入库、掩膜验证、像素计算、来源适配和报告生成；SQLAlchemy 模型负责事务和唯一约束。耗时任务在独立进程执行，业务 API 不通过内存线程冒充持久化队列。

前端页面通过 TanStack Vue Query 管理服务端状态，Pinia 保存当前会话与项目选择。会话令牌只在 HttpOnly Cookie 中；前端内存保存 CSRF 校验值，不在 localStorage 保存认证令牌。前端接口类型由 `docs/openapi.json` 生成，预测契约和核心统计字段有明确 Pydantic 类型。

`ImageAsset` 引用原始字节、标准化显示图、缩略图与可选标签。原始输入哈希绑定上传字节；EXIF 方向标准化记录在 transforms 中。模型掩膜重新编码为 0/255 PNG 后单独计算结果哈希，同时保留源掩膜摘要。

`Prediction` 对原始预测保持不可变；`Review` 以 `(prediction_id, revision)` 唯一约束追加。`ReportSnapshot` 在创建请求时复制结果与指定复核版本；生成线程只读取固定快照。报告保存原始输入文件、显示图、二值掩膜和统计，避免 JPEG 输入哈希被错误关联到 PNG 显示图。

## 任务状态与恢复

状态流为 QUEUED → VALIDATING → LOADING_ARTIFACT/INFERENCING → POSTPROCESSING → SUCCEEDED。失败进入 FAILED；排队任务可直接 CANCELED，运行中记录 CANCEL_REQUESTED 后在检查点取消，并同步取消远端 GPU 作业；租约转移不会取消新 Worker 正在使用的作业。

任务先提交数据库，Celery beat 每三秒扫描待处理记录并投递，数据库独立于 Redis 保留状态。Worker 用带条件的 UPDATE 获取 120 秒租约，每个阶段和 GPU 轮询更新租约。只有持有当前租约且仍为 POSTPROCESSING 的执行者可以提交结果。结果对 task_id 唯一，重复投递不会生成第二个预测。

Worker 失联后，租约到期的非终态任务会重新从不可变输入执行，不将中间产物当作成功结果。当前 CPU 阶段没有细粒度续算；恢复采用重新验证和重新计算。新资产使用随机 ID，先写临时文件、fsync 和原子改名，再提交数据库引用。失败可能留下不被数据库引用的孤立文件；P0 不自动删除这些文件，避免误删证据。

HTTP 创建任务与报告要求 Idempotency-Key；同键同请求返回已有记录，同键不同请求返回 409。并发首次写入由数据库唯一约束保护，竞争方可能收到 409，使用原键重试可取得已存在记录。手动重试创建新 attempt，保留旧记录，最多三次执行。

## 权限与审计

系统管理员管理用户并访问所有项目。项目管理员管理项目和成员；分析员上传、分析和导出；复核员保存复核和导出；只读成员只能读取和下载。所有资产下载、预测、任务、项目成员和审计查询都检查项目归属。项目归档阻止写入但保留读取和恢复能力。

密码使用带随机盐的 scrypt；数据库只存会话 token 的 SHA256，Cookie 设置 HttpOnly 和 SameSite=Strict。写请求检查 CSRF，登录检查 Origin，登录失败计数落库。错误响应包含 code、message、request_id、field_errors；服务端日志记录请求 ID，不返回堆栈或内部文件路径。

## 空间和指标

业务坐标以左上角为原点，x 向右、y 向下。OpenLayers 显示坐标为 `(x, -y)`，影像 extent 为 `[0, -height, width, 0]`；像素中心为 `(col+0.5, row+0.5)`。双视图共享一个 View，缩略图不参与统计，类别图层禁用插值。

FloodNet 类别 3 为目标，255 为无效区；无标签时以全图为有效区，evaluation 为 null。空有效区拒绝统计，零分母 IoU/Precision/Recall 返回 null。覆盖率为有效影像内目标像素比例，场景阈值为 ≥1%。全局 IoU 累加像素 TP/FP/FN 后计算；MAE 单位为百分点。

目前不输出地理面积、地理 GeoJSON、模型置信度或概率热图。复核圈选是调查注记，不改变原始预测，也不自动形成真值。

## 依据

实现遵循本地设计文档与审核清单，并参照 [OpenLayers 静态影像像素投影](https://openlayers.org/en/latest/examples/static-image.html)、[FastAPI 后台任务边界](https://fastapi.tiangolo.com/tutorial/background-tasks/) 和 [Celery 任务幂等与确认机制](https://docs.celeryq.dev/en/stable/userguide/tasks.html)。GPU 算法从随包 eval_tta.py 提取 RGB-only 路径；未将历史任务文字当作开发指令。
