#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
MODEL_NAME="${MODEL_NAME:-sherpa-onnx-streaming-zipformer-small-ctc-zh-int8-2025-04-01}"
MODEL_ARCHIVE="${MODEL_NAME}.tar.bz2"
MODEL_URL="https://github.com/k2-fsa/sherpa-onnx/releases/download/asr-models/${MODEL_ARCHIVE}"

mkdir -p "${ROOT_DIR}/models"
cd "${ROOT_DIR}/models"

if [[ -d "${MODEL_NAME}" ]]; then
  echo "Model already exists: models/${MODEL_NAME}"
  exit 0
fi

echo "About to download ${MODEL_ARCHIVE}"
echo "Default small int8 model is about 25 MB before extraction. Stop now if you are on limited data."
read -r -p "Continue? [y/N] " answer
if [[ "${answer}" != "y" && "${answer}" != "Y" ]]; then
  echo "Cancelled."
  exit 1
fi

curl -L --fail -o "${MODEL_ARCHIVE}" "${MODEL_URL}"
tar xvf "${MODEL_ARCHIVE}"
rm "${MODEL_ARCHIVE}"

echo "Downloaded to models/${MODEL_NAME}"
echo "Set SHERPA_MODEL_DIR=models/${MODEL_NAME} in .env"
