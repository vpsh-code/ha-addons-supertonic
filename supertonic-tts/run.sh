#!/bin/bash
set -e

# HA writes add-on options to /data/options.json
OPTIONS=/data/options.json
VOICE=$(    jq -r '.voice    // "F1"'   "${OPTIONS}")
LANGUAGE=$( jq -r '.language // "en"'   "${OPTIONS}")
QUALITY=$(  jq -r '.quality  // 2'      "${OPTIONS}")
SPEED=$(    jq -r '.speed    // 1.05'   "${OPTIONS}")

MODEL_DIR=/data/models/onnx
STYLE_DIR=/data/models/voice_styles
BASE_URL="https://huggingface.co/Supertone/supertonic-3/resolve/main"

# ── Download models on first run ──────────────────────────────────────────────
if [ ! -f "${MODEL_DIR}/vocoder.onnx" ]; then
    echo "[supertonic] First run: downloading Supertonic 3 models (~380 MB)..."
    mkdir -p "${MODEL_DIR}" "${STYLE_DIR}"

    for f in duration_predictor.onnx text_encoder.onnx vector_estimator.onnx vocoder.onnx tts.json unicode_indexer.json; do
        echo "[supertonic]   ↓ ${f}"
        curl -fsSL "${BASE_URL}/onnx/${f}" -o "${MODEL_DIR}/${f}"
    done

    for v in M1 M2 M3 M4 M5 F1 F2 F3 F4 F5; do
        echo "[supertonic]   ↓ voice style ${v}"
        curl -fsSL "${BASE_URL}/voice_styles/${v}.json" -o "${STYLE_DIR}/${v}.json"
    done

    echo "[supertonic] Models downloaded successfully."
fi

echo "[supertonic] Starting Wyoming TTS (voice=${VOICE}, lang=${LANGUAGE}, quality=${QUALITY}, speed=${SPEED})"

exec python /app/server.py \
    --onnx-dir  "${MODEL_DIR}" \
    --voice-dir "${STYLE_DIR}" \
    --port      10200 \
    --voice     "${VOICE}" \
    --lang      "${LANGUAGE}" \
    --steps     "${QUALITY}" \
    --speed     "${SPEED}"
