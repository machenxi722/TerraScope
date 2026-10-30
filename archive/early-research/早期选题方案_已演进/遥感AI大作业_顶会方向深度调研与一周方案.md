**商用时空信息软件平台：顶会 AI 选题调研与一周实施方案**

调研日期：2026-10-12。已知约束：距离展示一周，3 人，可以租 GPU。本文完成论文收录、作者代码、模型文件与公开数据的核查；尚未运行 GPU 推理，文中的实验结果均为待测目标。方法选择和一周安排是本次调研的判断。

老师最新要求（用户转述）：PPT 包括主题、数据预处理、分析过程、结果分析，成果可以是报告、网页或模型；个人实习报告为实验报告加个人延伸；个人读书报告按感兴趣的领域选择。不要求使用 ArcGIS Pro。学长项目仅用于参考成果的完整度，本项目独立确定问题、数据和实验。

**建议直接采用的题目**

《遥感视觉语言大模型的空间定量推理与证据核验》

主方法选 TerraScope（CVPR 2026 主会），使用作者已发布权重。核心实验研究两个问题：模型的地理空间回答是否准确；它输出的分割区域是否支持这个回答。我们增加确定性的面积与覆盖率计算，对模型答案作独立核验。第一周以单影像定量实验为主，双时相灾害案例作附加展示。

自己的研究主线是：**遥感大模型回答“面积有多大、覆盖率是多少”时，误差来自看错区域，还是算错数值？用明确的像素证据计算，能改善多少？** 基础模型及其分割机制属于原论文；本组完成评测数据协议、同区域的数值核验、错误分解和交互展示。课程项目的独立贡献是这些可复核的实验与分析，不将使用预训练模型表述为原创模型研发。

这个选题同时有前沿 AI 方法、明确遥感应用、可见像素成果和可重复的统计评价。自己的工作落在实验协议、几何核验、错误分析与展示系统上。最终课程成绩仍由老师评价。

**候选方向比较**

下表的适合程度是一周课程项目的判断，不是论文排名。

| 方向 | 核实发表 | 有什么可做的成果 | 一周内的主要风险 | 本次选择 |
| --- | --- | --- | --- | --- |
| TerraScope：像素证据驱动的遥感视觉推理 | [CVPR 2026 主会](https://openaccess.thecvf.com/CVPR2026?day=2026-06-06)，16712–16722 | 自然语言问题、分割区域、面积/覆盖率、空间关系 | 公开评测数据尚不完整，需要自行保存 mask 和增加统计代码 | **主选：AI 展示效果和课程关联同时较强** |
| OpenDPR：生成式视觉原型检索的开放词汇变化检测 | [CVPR 2026 主会](https://openaccess.thecvf.com/content/CVPR2026/html/Guo_OpenDPR_Open-Vocabulary_Change_Detection_via_Vision-Centric_Diffusion-Guided_Prototype_Retrieval_for_CVPR_2026_paper.html) | 前后时相、变化轮廓、类别变化图、IoU/F1 | 多组件安装、类别原型与标签编码需要对齐 | **若优先双时相与标准像素指标，则改选它** |
| KnOTS：LoRA 专家子空间对齐与融合 | [ICLR 2025 主会](https://proceedings.iclr.cc/paper_files/paper/2025/file/0d4f8a5109c5083b5307fcd0bddae7a7-Paper-Conference.pdf) | 遥感专家融合、能力保留率、融合权衡曲线 | 数据划分与分类头适配；视觉成果主要是分类和曲线 | 科研方向备选 |
| AnyChange：免训练变化检测 | [NeurIPS 2024 主会](https://proceedings.neurips.cc/paper_files/paper/2024/hash/9415416201aa201902d1743c7e65787b-Abstract-Conference.html) | 二值变化轮廓、点查询 | 类别语义与变化方向要另加方法 | OpenDPR 的基线或回退 |
| SegEarth-OV：开放词汇遥感分割 | [CVPR 2025 主会](https://openaccess.thecvf.com/content/CVPR2025/html/Li_SegEarth-OV_Towards_Training-Free_Open-Vocabulary_Segmentation_for_Remote_Sensing_Images_CVPR_2025_paper.html) | 文本类别对应的单影像分割图 | 变化分析需另设计双时相流程 | 相关工作或可选分割对照 |

TerraScope 在推理过程中触发分割，并把所选区域的视觉特征回注到后续生成。这个机制提供了可展示的区域证据；是否准确仍需实验检验。[作者项目介绍](https://shuyansy.github.io/terrascope/)

**实际发布状态核查**

| 项目 | 2026-10-12 核查结果 | 对实施的含义 |
| --- | --- | --- |
| 官方模型 | `sy1998/TerraScope`；公开、非 gated；7 个 safetensors 分片合计 32,122,789,552 字节，约 32.12 GB | 先安排下载与磁盘空间；这个数字是文件下载量，不是显存需求 |
| 官方演示 | `demo.py` 读取文字预测和 `prediction_masks`；同时有单图、双图接口 | 可以接入自定义问题与图像，自己保存证据图 |
| 官方 Benchmark | 当前公开 3,549 条、5 种单图任务；字段包括 image、question、candidates、answer、task_type、ground_truth | 足够做覆盖率和面积的课程评测子集 |
| 发布与论文的差异 | 论文介绍 3,837 条、6 任务；当前发布少了建筑变化任务。公开字段未包含逐像素 GT mask | 本项目不声称完整复现六任务；暂不将 mask IoU 列为主指标 |
| 官方推理评测脚本 | 存储文本答案并用于选项评价，未包含 mask 保存和几何真值读取 | 需要增加这两个环节，这是课程扩展的一部分 |

来源：[官方模型](https://huggingface.co/sy1998/TerraScope)、[模型文件 API](https://huggingface.co/api/models/sy1998/TerraScope?blobs=true)、[演示源码](https://github.com/shuyansy/Earth-Observation-VLMs/blob/master/TerraScope/demo.py)、[公开 Benchmark](https://huggingface.co/datasets/sy1998/TerraScope-Bench)、[官方推理脚本](https://raw.githubusercontent.com/shuyansy/Earth-Observation-VLMs/master/TerraScope/projects/terrascope/evaluation/infer_terrascope_bench.py)。模型核查 revision：`a2333262586f8a07238d85db85061979198435fc`；数据 revision：`c00191b737bc01044e3de93fb4f18c5f33b83564`。后续实施应固定版本。

**实验如何设计，才能有自己的分析**

主实验固定 100 道题：50 道覆盖率、50 道绝对面积。另留 20 道开发题用于调试提示词和输出解析。按图像内容哈希划分开发与评测数据，避免同一图像上的不同题分别落入两边。记录实际独立影像数；题数不能等同于独立场景数。

模型输入只含图像、问题、候选答案，以及任务确实需要的分辨率信息；`answer` 和 `ground_truth` 只在评分程序中读取。使用固定随机种子、样本清单和提示模板，提前选定评测子集，不根据结果更换失败样本。

比较三条处理路线：

| 路线 | 输入与处理 | 评价目的 |
| --- | --- | --- |
| A：通用 VLM | InternVL3-8B，回答同一批遥感问题 | 通用模型对地理空间数值问题的表现 |
| B：TerraScope 原始答案 | 作者模型，保存答案和分割区域 | 遥感适配模型的回答能力 |
| C：TerraScope + 几何计算 | 使用 B 的同一批 mask，用确定性程序计算覆盖率/面积并匹配选项 | 数值计算能否减少答案误差；分割错误是否仍然存在 |

InternVL3 是 TerraScope 的基础架构来源，因此它是有意义的对照。但 A/B 差异同时包含遥感训练与架构变化，不能将全部提升单独归因于 mask 回注机制。[论文方法](https://arxiv.org/html/2603.19039v1)

覆盖率计算：`目标像素数 / 有效影像像素数 × 100%`。面积计算：`目标像素数 × resolution_m²`，仅用于分辨率可确认、像元可按该尺度计算的样本。mask 必须对齐原始影像网格，使用明确的二值化和最近邻重采样规则，避免在缩放后沿用原像元面积。

同一次输出若有多个 mask，需要按文字中的区域和 mask 顺序关联，先人工核对 10 个样本。区域缺失、多个区域无法对应、解析失败都应单独计数，不能静默剔除。

核心指标包括：

- **问答准确率**：三条路线在同一评测清单上的正确比例。
- **覆盖率 MAE**：相对公开数值真值的平均绝对误差，以百分点报告。
- **面积误差**：同时报告绝对误差和相对误差；面积为零的真值单独处理。
- **答案与 mask 的数值一致率**：文本结论是否与该 mask 的几何计算一致。它反映内部数值一致性，不能证明整个推理过程正确。
- **运行情况**：有效 mask 返回率、失败样本数、实测显存和推理耗时。

几何计算可以消除一部分计算误差，但不会自动纠正模型分错区域的问题。如果 C 没有提升，仍可通过错误分解解释原因。这个结论也能形成合格的课程分析。

由于当前公开数据没有逐像素真值，分割错误只做人工案例判断，不能报告为完整的像素级误差分解；覆盖率和面积的数值误差则用公开数值真值定量评价。100 道题用于课程规模的受控实验，结论限定在该子集及任务范围内。

**最有展示效果的一屏**

左侧展示原始遥感影像和问题；中间展示彩色分割覆盖；右侧并列显示模型答案、从 mask 计算的数值和公开真值；下方放三路线的误差统计。

可以展示的问题包括：“水体覆盖率是多少？”“建设用地占多少面积？”“水体与农田哪个面积更大？”距离、邻接和面积排序可在核心实验稳定后增加少量样例。现场保存真实推理输出，准备 3 个成功案例和 2 个失败案例，并录制演示视频，以避免现场下载或网络影响展示。

有价值的失败案例包括：回答选项正确但区域明显分错；区域合理但数值回答错误；模型没有输出所需区域；多区域顺序混淆。这些案例应从固定评测集选取，并说明选取理由。

空间统计结果导出 CSV，用 Python 制作统计图，并接入展示网页；报告、网页、模型输出都可以作为老师要求的成果。ArcGIS Pro 可按需要选用。当前公开 Benchmark 的 PNG 没有可确认的 CRS/经纬度，不能将其直接贴到武汉底图上宣称定位。若第 5 天前还有余量，再增加独立 GeoTIFF 迁移案例；保留原影像坐标系与变换参数后，输出带地理参考的分割栅格与面积表。这项不作为首周必要条件。

双时相灾害图可使用官方 demo 的前后图像做附加展示，明确标注为案例推理，不把缺失的变化 Benchmark 说成已完成的定量实验。[官方双图接口](https://github.com/shuyansy/Earth-Observation-VLMs/blob/master/TerraScope/demo.py)

**算力与首日验收**

作者在 A100 80 GB 上报告的推理峰值为 22.4–24.2 GB，随输出 mask 数变化。因此建议租一张 **48 GB NVIDIA GPU** 留出余量；这是实施建议，实际显存和速度要首日测速。模型使用已发布权重推理，无需重做作者训练。[作者效率分析](https://arxiv.org/html/2603.19039v1)

参考官方版本准备推理环境：Torch 2.3.1、CUDA 12.1、Transformers 4.42.3、PEFT 0.11.1 等。完整训练环境与最小推理环境分别处理；HF 推理代码支持 Flash Attention 缺失时回退 eager，回退后的资源用量仍需实测。[模型实现文件](https://huggingface.co/sy1998/TerraScope/tree/main)、[作者代码](https://github.com/shuyansy/Earth-Observation-VLMs/tree/master/TerraScope)

首日必须拿到一张**自己实际运行**的输出图，并确认：模型可加载；返回非空 mask；mask 与原图尺寸、类别对应；数值统计可计算；一批 10 个样本能稳定运行。记录这些样本的耗时和峰值显存后，再估算租赁费用。调研没有核实租赁平台实时价格，因此不提供虚构预算。

若第一天结束仍无法完成加载和非空 mask 输出，第二天转向 OpenDPR；不要把整周花在安装问题上。

**7 天、3 人安排**

| 时间 | 必须完成的成果 |
| --- | --- |
| 第 1 天 | 模型与数据下载、环境、10 样本验收、至少一张真实证据图 |
| 第 2 天 | 固定开发/评测清单，保存 mask、原始答案与元数据 |
| 第 3 天 | 通用模型基线与 TerraScope 的 100 题结果 |
| 第 4 天 | 几何统计、三路线指标、失败原因分类 |
| 第 5 天 | 展示页面、图表、可选双图或 GeoTIFF 案例 |
| 第 6 天 | PPT 和两种个人报告素材，补齐数据与论文引用 |
| 第 7 天 | 答辩排练、录屏、结果和环境备份 |

三人分工：一人负责模型运行和环境；一人负责数据协议、几何计算与指标；一人负责证据图、展示网页和 PPT。每个人的个人实习报告应基于自己实际参与的环节。

**如何对应老师的三项要求**

- **小组 PPT**：依次呈现主题与研究问题、数据来源及预处理、分析方法与处理过程、结果分析及解释，最后演示报告/网页/模型成果。预处理具体展示数据筛选、图像去重与划分、分辨率信息、mask 对齐和异常样本处理。
- **个人读书报告**：每人选择自己感兴趣的领域，可以与小组项目关联，也可以另选时空信息应用方向。若希望复用资料，可阅读 TerraScope 与 EarthDial/GeoChat，讨论遥感 VLM 从识别到空间推理的进展，以及区域证据能验证什么；这只是建议，老师没有要求必须沿用小组题目。
- **个人实习报告**：写清实际实验的数据、预处理、方法、结果和解释，再分别选择几何核验、提示词改写稳健性、分辨率变化影响等一个环节延伸。使用同一数据协议，保存自己增加的处理与结果。

PPT 建议包含约 10–12 页，按老师要求的顺序组织：主题与研究问题、数据来源、数据预处理、论文方法、自己的处理链与评测协议、定量结果、成功案例、失败案例、几何核验分析、网页演示、结论与来源。页数是建议，不是老师规定。

**如果改做 OpenDPR，如何保持同等学术强度**

题目可用《基于生成式视觉原型检索的开放词汇遥感变化解析与空间统计》。采用公开 support set，先复现 OpenDPR 的免训练版本，暂不增加需要弱监督预训练的 OpenDPR-W。[官方代码和运行说明](https://github.com/guoqi2002/OpenDPR)

主数据可用 SECOND。固定公开验证集子集，先核标签色表与类别索引，再比较二值变化和逐类变化。AnyChange 只作为二值对照；多类评价沿用 OpenDPR 协议。新增“从类别 A 变为 B”的转移分析需要另按双时相真值验证，不等同于官方逐类 IoU/F1。[SECOND 来源](https://captain-whu.github.io/SCD/)、[评价实现](https://raw.githubusercontent.com/guoqi2002/OpenDPR/main/eval/evaluate_SECOND.py)

新词汇需要对应的视觉原型，现成六类不代表任意输入“机场”即可识别。SECOND 裁切影像先报告像素数与占比；要做带地理位置的变化案例，可另看 LEVIR-CD 的地理 bbox/GeoJSON，明确这种定位与面积属于近似。[LEVIR-CD](https://justchenhao.github.io/LEVIR/)、[空间信息说明](https://raw.githubusercontent.com/justchenhao/STANet/master/LEVIR_CD_spatial_info/README.md)

**论文与资源入口**

| 用途 | 原始资源 |
| --- | --- |
| 主论文与附录 | [TerraScope 全文](https://arxiv.org/html/2603.19039v1) |
| 正式收录核查 | [CVPR 2026 论文目录](https://openaccess.thecvf.com/CVPR2026?day=2026-06-06) |
| 主项目、模型与数据 | [项目页](https://shuyansy.github.io/terrascope/)、[代码](https://github.com/shuyansy/Earth-Observation-VLMs/tree/master/TerraScope)、[模型](https://huggingface.co/sy1998/TerraScope)、[Benchmark](https://huggingface.co/datasets/sy1998/TerraScope-Bench) |
| 多模态遥感相关工作 | [EarthDial，CVPR 2025](https://openaccess.thecvf.com/content/CVPR2025/html/Soni_EarthDial_Turning_Multi-sensory_Earth_Observations_to_Interactive_Dialogues_CVPR_2025_paper.html) |
| 变化检测备选 | [OpenDPR 代码](https://github.com/guoqi2002/OpenDPR)、[论文](https://arxiv.org/html/2603.27645v2) |
| 模型融合备选 | [KnOTS 代码](https://github.com/gstoica27/KnOTS)、[EuroSAT LoRA](https://huggingface.co/hoffman-lab/KnOTS-ViT-B-32_lora_R16_eurosat)、[RESISC45 LoRA](https://huggingface.co/hoffman-lab/KnOTS-ViT-B-32_lora_R16_resisc45) |

公开 Benchmark 标注 Apache 2.0；作者仓库同时要求遵守所使用数据和权重的原始许可。模型当前没有完整 model card，实施时保留引用和来源记录，不将全部组成部分概括为同一个许可证。自己的课程扩展应与原论文贡献分开署名。[作者仓库声明](https://github.com/shuyansy/Earth-Observation-VLMs)
