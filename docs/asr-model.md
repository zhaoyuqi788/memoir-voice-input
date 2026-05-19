# sherpa-onnx 中文模型

首版默认推荐较小的 int8 中文流式 CTC 模型：

`sherpa-onnx-streaming-zipformer-small-ctc-zh-int8-2025-04-01`

官方文档显示该模型目录包含 `model.int8.onnx`、`tokens.txt`、`bbpe.model`，其中 ONNX 模型约 25 MB。下载脚本不会自动运行，避免在手机热点下消耗流量。

模型下载后，在 `.env` 中设置：

```bash
SHERPA_MODEL_DIR=models/sherpa-onnx-streaming-zipformer-small-ctc-zh-int8-2025-04-01
```

后端也会尝试在 `models/` 下自动寻找包含 `tokens.txt` 和 `.onnx` 文件的模型目录。
