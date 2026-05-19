# memoir-voice-input

本地语音回忆录 Web 工具：用浏览器录音，后端通过 sherpa-onnx 中文流式模型实时转写，自动按停顿分段，并导出章节音频、原始 ASR 和整理后文本。

> 隐私默认值：`data/`、`models/`、`exports/`、音频和转写稿都不会提交到 git。这个仓库可以公开，家庭素材仍留在本机。

## 快速启动

```bash
npm install
scripts/setup-python.sh
cp .env.example .env
```

模型下载流量较大，手机热点下先不要运行下面的脚本。等网络合适时再执行：

```bash
scripts/download-model.sh
```

启动后端和前端：

```bash
source .venv/bin/activate
uvicorn backend.app.main:app --reload --host 127.0.0.1 --port 8000
npm run dev
```

打开 `http://127.0.0.1:5173`。

## 运行方式

- 点击 `开始录音` 后，前端将麦克风音频转换成 16 kHz mono Int16 PCM，通过 WebSocket 发给本机后端。
- 后端优先使用 `SHERPA_MODEL_DIR` 下的 sherpa-onnx 中文流式 CTC 模型；模型缺失时仍可启动界面，但 ASR 会提示未加载。
- 自动按静音停顿生成段落；每段都有独立 WAV 和播放按钮。
- 点击 `完成并导出` 会生成 zip，包含 `chapter.mp3`、`raw_asr.txt`、`cleaned_text.md`、`segments.json`。

## 测试

```bash
python -m unittest discover -s backend/tests
npm test
npm run build
```

如果暂时不想下载依赖或模型，可以先运行 Python 单元测试；它们只覆盖文本整理、分段和导出基础逻辑。

当前这台机器默认是 Python 3.14，`scripts/setup-python.sh` 默认寻找 `python3.12`，因为 sherpa-onnx 的预编译 wheel 通常比最新 Python 版本更稳。
