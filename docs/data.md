# 数据准备与排除规则

不附 FloodNet / Sen1Floods11 原图、标签、独立 RGB/GT 图块、缩略图库、数据压缩包和运行数据库。实验表格、划分 ID、哈希、预测掩膜和成品图件保留。PPT、PDF、UI 截图及视频已有展示图属于汇报成品，不提供可直接训练的数据集。

## 无数据集运行

`data/demo/manifest.json` 是空索引，`data/demo/experiments/` 保存统计。启动使用 `init --demo-if-present`，没有案例时只初始化管理员。可创建项目、上传自己的 RGB 和浏览统计；实时分析需 GPU，历史回放需匹配的影像与预测索引。

## 恢复本地案例

已有经过校验的原工程资料时，可将完整 `data/demo/` 放到同一路径，或设置 `TERRA_DEMO_DIR` 指向外部目录。必须包含 `manifest.json`、`checksums.json` 及索引引用的 RGB、标签和预测。保持原字节，重存 JPEG 会改变 SHA256。

完整 1,198 幅实验库安装入口：

```sh
.venv/bin/python scripts/install_dataset.py /absolute/path/to/autodl-dataset.tar
```

这是读取已经取得的本地导出包，不自动下载数据，也不要求 GPU。脚本校验哈希与尺寸，安装到 `data/library/` 并生成缩略图。服务器导出为 `scripts/export_autodl_dataset.py`，旧服务器路径需按实际环境检查。

`scripts/prepare_demo.py` 依赖原交接包结构及未上传数据，不能从 Git 自动补齐。安装数据后重启服务以清空索引缓存。

## 划分与坐标

训练 300、验证 80、测试 448、同事件留出 370。各实验 `manifest.json` 与 `experiments/datasets/library-index.json` 保存分区和哈希；后者没有原始 GPS 目录。受淹道路类别 3，255 无效。GPS 是 WGS84 相机点，不能作为整幅影像地理变换。

## 提交边界

`.gitignore` 排除 `data/library/`、`data/demo/images/`、`datasets/`、`models/`、实验 `data/`、`.env`、运行数据库与依赖缓存。安装资料可能更新已跟踪的 demo 索引与校验清单，这些更改只用于本机，提交前应检查。依赖真实案例的测试缺数据时明确跳过。
