# Supertonic TTS — Home Assistant Add-on

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Wyoming Streaming](https://img.shields.io/badge/Wyoming-Streaming%20TTS-brightgreen)](https://www.home-assistant.io/integrations/wyoming/)
[![Version](https://img.shields.io/badge/version-1.0.8-blue)](https://github.com/vpsh-code/ha-addons-supertonic/blob/main/supertonic-tts/CHANGELOG.md)

On-device neural Text-to-Speech for Home Assistant via the [Wyoming protocol](https://www.home-assistant.io/integrations/wyoming/), powered by [Supertonic 3](https://github.com/supertone-inc/supertonic) from Supertone Inc.

- **🔴 Streaming TTS** — audio starts playing sentence-by-sentence as synthesis happens, no waiting for the full response (`stream_response: true`)
- **31 languages** — English, Korean, Japanese, German, French, Spanish, and 25 more
- **10 voices** — M1–M5 (male), F1–F5 (female)
- **100% on-device** — no cloud, no API key, no data leaves your home
- **Wyoming protocol** — native HA integration, works in Assist pipelines

![Supertonic 3](https://raw.githubusercontent.com/supertone-inc/supertonic/main/img/Supertonic3_HeroImage.png)

---

## Requirements

| | Minimum | Recommended |
|---|---|---|
| **RAM** | 4 GB (tight) | **8 GB** |
| **CPU** | x86-64 / aarch64 | x86-64 with AVX2 |
| **Storage** | 500 MB free | 1 GB free |
| **HA Install** | HAOS or Supervised | HAOS |

> ⚠️ **armv7 (32-bit ARM, Raspberry Pi 2/3) is not supported** — `onnxruntime` has no 32-bit ARM wheels.

---

## Installation

### Step 1 — Add this repository to HA

1. Go to **Settings → Add-ons → Add-on Store**
2. Click **⋮** (top right) → **Repositories**
3. Add: `https://github.com/vpsh-code/ha-addons-supertonic`
4. Click **Add** → close the dialog
5. Find **Supertonic TTS** in the store and click **Install**

### Step 2 — Configure

In the add-on **Configuration** tab:

| Option | Default | Description |
|---|---|---|
| `voice` | `F1` | Voice ID: M1–M5 (male), F1–F5 (female) |
| `language` | `en` | Language code (en, de, fr, es, ko, ja…) |
| `quality` | `2` | Denoising steps — 1=fastest, 8=best quality |
| `speed` | `1.05` | Speech rate multiplier (0.5–2.0) |

> Use a **dot** for decimals in `speed` (e.g. `1.05` not `1,05`).

### Step 3 — Start the add-on

Click **Start**. On first launch it downloads ~380 MB of models from HuggingFace — watch the **Log** tab. This is a one-time download; models are stored in `/data/models/`.

### Step 4 — Connect to HA

Go to **Settings → Devices & Services → Add Integration → Wyoming Protocol**:
- **Host:** `172.16.2.xxx` *(your HAOS machine's IP — not `localhost`)*
- **Port:** `10200`

Then set it as your TTS engine: **Settings → Voice Assistants → your pipeline → Text-to-speech → Supertonic TTS**.

---

## Platform-specific setup

### 🖥️ Proxmox VM (HAOS)

This is the most common self-hosted setup. Two important Proxmox settings that dramatically affect performance:

**1. Set CPU type to `host`** *(critical for speed)*

In Proxmox web UI → select your HAOS VM → **Hardware** → **Processors** → **CPU Type: `host`**

This exposes your real CPU's AVX2/FMA instructions to the VM. onnxruntime uses these heavily — without them inference is 5–10× slower.

**2. Allocate at least 8 GiB RAM**

In Proxmox → VM → **Hardware** → **Memory** → set to **8192 MiB**.

Why 8 GiB? Breakdown at runtime:
| Component | RAM |
|---|---|
| HAOS + HA core | ~1.2 GB |
| Other add-ons (Nginx, InfluxDB, etc.) | ~0.5–1.5 GB |
| Supertonic peak inference | ~1.5 GB |
| Safe headroom | ~2 GB |
| **Total recommended** | **~6–8 GB** |

With only 4 GB the Linux OOM killer will terminate the Python process mid-synthesis.

**3. Restart the VM after both changes.**

---

### 🐧 Ubuntu + Home Assistant Supervised

The add-on runs identically. Ubuntu already exposes your real CPU features so no CPU type change is needed. Ensure the machine has **≥ 6 GB RAM** free for HA + the add-on.

```bash
# Check available RAM
free -h
```

---

### 🍎 macOS (running HA in a VM)

If you run HAOS inside Parallels, UTM, or VirtualBox on a Mac:

- **Apple Silicon (M1/M2/M3):** The VM is aarch64 — the add-on supports this. Allocate ≥ 6 GB to the VM.
- **Intel Mac:** Same as Proxmox — expose host CPU in VM settings for best performance.

**Alternatively**, run the standalone Wyoming server directly on macOS and point HA at it — see [`wyoming-supertonic`](https://github.com/vpsh-code/wyoming-supertonic).

---

### 🍓 Raspberry Pi 4 / 5

| Pi model | Supported | Notes |
|---|---|---|
| Pi 5 (8 GB) | ✅ | Slow (~15–30 s/sentence). Set quality=1. |
| Pi 4 (4–8 GB) | ⚠️ | Very slow. Marginal on 4 GB. |
| Pi 3 or older | ❌ | No onnxruntime armv7 wheel |

For Pi users, set `quality: 1` in add-on options to minimise synthesis time.

---

## Quality vs. speed guide

The `quality` setting controls how many denoising passes the neural model runs. Lower = faster, higher = better audio:

| Quality | Approx. time (modern x86) | Approx. time (Pi 4) | Audio |
|---|---|---|---|
| 1 | ~1 s | ~15 s | Good |
| 2 | ~2 s | ~30 s | Better |
| 4 | ~4 s | ~60 s | Very good |
| 8 | ~8 s | ~120 s | Best |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| OOM / Python killed | Not enough RAM | Increase VM RAM to 8 GiB |
| Very slow synthesis | kvm64 CPU type | Change Proxmox CPU to `host` |
| `Failed to connect` | Wrong host | Use machine IP, not `localhost` |
| `Failed to save` options | Decimal comma | Use dot: `1.05` not `1,05` |
| `Provider not found` | Old entity cached | Update pipeline to use `Supertonic TTS` |
| Model download fails | HuggingFace 404 | Restart the add-on |
| `X86_V2` numpy error | Old numpy + no AVX | Already fixed in v1.0.1+ |

---

## Not using HAOS? (Container / Core installs)

If you run **HA Container** (plain Docker) or **HA Core** (Python venv), add-ons are not supported. Use the standalone Wyoming server instead:

👉 **[wyoming-supertonic](https://github.com/vpsh-code/wyoming-supertonic)** — Docker Compose or plain Python, runs anywhere.

---

## Credits

- **[Supertone Inc.](https://github.com/supertone-inc/supertonic)** — Supertonic 3 ONNX models and inference code (MIT License)
- Wyoming protocol — [Home Assistant](https://www.home-assistant.io/integrations/wyoming/)
