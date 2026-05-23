# Changelog

## 1.0.16
- Fix rupee singular: ₹1 → 1 rupee (not "1 rupees")

## 1.0.15
- Add Indian Rupee symbol (₹) expansion: handles crore and lakh suffixes (₹6 crore → 6 crore rupees)

## 1.0.14
- Fix decimal pronunciation: remove spoken "point" expansion — TTS model reads 20.1 natively without pause; Swedish decimal comma now converts to dot (1,5 → 1.5)

## 1.0.13
- Extend text normalization: HA energy units (kWh, W, V, A), air quality (CO2, PM2.5, ppm), distance (mm, cm, km), currency (euro, dollar, pound, SEK, kr)
- Add ISO date expansion (2026-06-07 to 7 June 2026) and time normalization (18:05 to 18 05)
- Add Swedish decimal comma (1,5 to 1 point 5) and thousands separator (1,234 to 1234)
- Fix Roman numeral expansion to only fire after known name or title prefixes
- Add compass direction case-insensitivity for multi-letter abbreviations
- Normalize mathematical minus and em dash to ASCII equivalents

## 1.0.12
- Fix streaming language handling — language from SynthesizeStart now used (was always defaulting to English)
- Fix run.sh quality fallback (8→2) to match config.yaml default
- Pin wyoming>=1.9.0 and onnxruntime>=1.17,<2.0 in requirements.txt

## 1.0.11
- Fix Roman numeral expansion failing when LLM uses Unicode whitespace (non-breaking space, thin space) between name and numeral

## 1.0.10
- Fix Roman numeral regex — now correctly handles sentences ending in `!`, `?`, `:`, `;` (previously only matched before space or period)

## 1.0.9
- Add Roman numeral expansion in text normalization — ordinals like `II`, `XI`, `XIV` are now spoken correctly in name/title context (e.g. "King Henry VIII" → "King Henry the Eighth")

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
