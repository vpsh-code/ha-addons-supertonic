# Supertonic TTS — Home Assistant Add-on Repository

Custom add-on repository for [Supertonic TTS](https://github.com/vpsh-code/wyoming-supertonic) — on-device neural TTS via Wyoming protocol.

## Installation

1. In Home Assistant go to **Settings → Add-ons → Add-on Store**
2. Click ⋮ (top right) → **Repositories**
3. Add: `https://github.com/vpsh-code/ha-addons-supertonic`
4. Find **Supertonic TTS** in the store and install it
5. Configure voice, language, quality in the add-on options
6. Start the add-on (first start downloads models — ~380 MB, takes a few minutes)
7. In **Settings → Devices & Services → Add Integration → Wyoming Protocol**:
   - Host: `localhost`
   - Port: `10200`

## Add-ons

### Supertonic TTS

On-device neural TTS (31 languages, 10 voices) using the [Supertonic 3](https://github.com/supertone-inc/supertonic) ONNX models. Exposes a Wyoming protocol server on port 10200.

| Option | Default | Description |
|---|---|---|
| voice | F1 | Voice ID (M1–M5, F1–F5) |
| language | en | Language code |
| quality | 8 | Denoising steps (1=fast, 20=best) |
| speed | 1.05 | Speech rate multiplier |
