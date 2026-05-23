# Changelog

## 1.0.8
- Fix streaming protocol: send `SynthesizeStopped` (not `AudioStop`) to terminate HA's audio reader
- Ignore legacy `Synthesize` event when streaming session is active

## 1.0.7
- Enable Wyoming streaming TTS (`supports_synthesize_streaming=True`) — audio starts playing before the full response is generated
- Add `SynthesizeStart` / `SynthesizeChunk` / `SynthesizeStop` handlers for sentence-level streaming

## 1.0.6
- Lower default quality to 2 for better performance on constrained hardware
- Add onnxruntime memory options: `enable_mem_pattern=False`, `enable_mem_reuse=True`, `intra_op_num_threads=2`

## 1.0.5
- Fix add-on schema — simplified to basic types (HA Supervisor does not support `list()` syntax)
- Rename TTS entity to "Supertonic TTS" for clarity in HA voice pipelines

## 1.0.4
- Fix Docker base image — switched from `ghcr.io/home-assistant/amd64-base-python:3.12` (not found) to `python:3.12-slim`
- Read config from `/data/options.json` via `jq` (bashio not available outside HA base image)

## 1.0.3
- Fix model download URLs — files are under `onnx/` subdirectory on HuggingFace
- Pin `numpy<2.0` to fix `X86_V2` CPU baseline error on Proxmox kvm64 VMs

## 1.0.2
- Add `icon.png` and `logo.png` from Supertonic project (MIT licensed)
- Remove deprecated `build.yaml`

## 1.0.1
- Fix `startup` and `boot` fields in `config.yaml` (required by HA Supervisor)
- Add `repository.json` at repo root

## 1.0.0
- Initial release: Wyoming TTS server wrapping Supertonic 3 ONNX models
- 10 voices (M1–M5, F1–F5), 31 languages, configurable quality and speed
- Sentence-level audio streaming over Wyoming protocol
