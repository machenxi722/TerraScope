# 模型权重

`long_bce_lovasz_seed20261017_best_delta.pt` 通过 Git LFS 保存，大小 **71,979,524 字节**，SHA256：

```text
7c70b717815a39b66c052748c44256b685d17ef1513ee482084ce6419d93dfa8
```

状态字典包含投影层 `text_hidden_fcs` 和 SAM2 `sam_mask_decoder` 的 17,981,509 个参数。选中 BCE+Lovász、种子 20261017、第 4,800 微步单检查点。四视图是推理策略，不是另一个权重文件。

```sh
git lfs pull --include='weights/*'
python3 scripts/verify_repository.py --weights-only
```

来源为原工程 `runtime/long_bce_lovasz_seed20261017_best_delta.pt`。其他对照 checkpoint 未交接到本地；保存了相应协议、评估和预测，但不包含其参数。

## 完整底座

另行获取上游 [sy1998/TerraScope](https://huggingface.co/sy1998/TerraScope/tree/a2333262586f8a07238d85db85061979198435fc)，锁定 revision：

```text
a2333262586f8a07238d85db85061979198435fc
```

历史实机底座约 32.13 GB、30 个文件，清单见 [autodl-base-manifest.json](../docs/evidence/autodl-base-manifest.json)。本地只有增量和清单，未重新下载、上传完整底座。需要匹配的模型 Python 文件、配置、分词器与所有权重分片。

获取并核对来源后，存放在 `models/TerraScope/`（Git 忽略），对实际文件生成清单：

```sh
mkdir -p runtime
python3 scripts/model_manifest.py models/TerraScope runtime/base-manifest.json
```

生成清单只记录一致性，应先与历史清单逐文件核对。清单必须位于模型目录之外，并覆盖实际模型目录的全部文件；生成后不要修改目录。下载工具额外留下的元数据也需要纳入或在生成前移出。引擎通过 `trust_remote_code=True` 使用本地固定版本代码。

## GPU 服务

历史实机为 Linux / A800 / Python 3.10.8 / PyTorch 2.3.1 / Transformers 4.42.3。GPU 环境与业务 Python 3.12 分离。`requirements.reproduction.txt` 是上游依赖快照，`requirements.api.lock` 是服务 API 依赖；只安装 API 依赖不足以运行模型。

在已配好模型依赖的 CUDA 环境、仓库根目录运行：

```sh
python -m pip install -r model_service/requirements.api.lock
export MODEL_BASE_PATH="$PWD/models/TerraScope"
export MODEL_DELTA_PATH="$PWD/weights/long_bce_lovasz_seed20261017_best_delta.pt"
export MODEL_BASE_MANIFEST="$PWD/runtime/base-manifest.json"
export MODEL_JOB_DIR="$PWD/runtime/model-jobs"
export MODEL_API_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(32))')"
python -m uvicorn model_service.server:app --host 127.0.0.1 --port 8100 --workers 1
```

令牌至少 24 字符，业务后端 `TERRA_MODEL_SERVICE_TOKEN` 使用同一令牌。SSH 隧道方式设置 `TERRA_MODEL_SERVICE_URL=http://127.0.0.1:18100` 和 `TERRA_MODEL_TRANSPORT=ssh_tunnel`。Docker 内 loopback 指向容器自身，需要容器可访问的 HTTPS 模型入口。

AutoDL 脚本需将 `scripts/autodl.example.json` 复制为 `runtime/autodl.json` 并填写自己的 SSH 地址、端口及服务器模型路径。仓库不附现有账号配置。接口及历史验收说明见 [model_service/README.md](../model_service/README.md)。
