#!/usr/bin/with-contenv bashio

VOICE=$(bashio::config 'voice')
LANGUAGE=$(bashio::config 'language')
QUALITY=$(bashio::config 'quality')
SPEED=$(bashio::config 'speed')

MODEL_DIR=/data/models/onnx
STYLE_DIR=/data/models/voice_styles
BASE_URL="https://huggingface.co/Supertone/supertonic-3/resolve/main"

# ── Download models on first run ──────────────────────────────────────────────
if [ ! -f "${MODEL_DIR}/vocoder.onnx" ]; then
    bashio::log.info "First run: downloading Supertonic 3 models (~380 MB)..."
    mkdir -p "${MODEL_DIR}" "${STYLE_DIR}"

    for f in duration_predictor.onnx text_encoder.onnx vector_estimator.onnx vocoder.onnx tts.json unicode_indexer.json; do
        bashio::log.info "  ↓ ${f}"
        curl -fsSL "${BASE_URL}/${f}" -o "${MODEL_DIR}/${f}" || {
            bashio::log.error "Failed to download ${f}"
            exit 1
        }
    done

    for v in M1 M2 M3 M4 M5 F1 F2 F3 F4 F5; do
        bashio::log.info "  ↓ voice style ${v}"
        curl -fsSL "${BASE_URL}/voice_styles/${v}.json" -o "${STYLE_DIR}/${v}.json" || {
            bashio::log.error "Failed to download voice style ${v}"
            exit 1
        }
    done

    bashio::log.info "Models downloaded successfully."
fi

bashio::log.info "Starting Wyoming Supertonic TTS (voice=${VOICE}, lang=${LANGUAGE}, quality=${QUALITY}, speed=${SPEED})"

exec python /app/server.py \
    --onnx-dir  "${MODEL_DIR}" \
    --voice-dir "${STYLE_DIR}" \
    --port      10200 \
    --voice     "${VOICE}" \
    --lang      "${LANGUAGE}" \
    --steps     "${QUALITY}" \
    --speed     "${SPEED}"
