#!/usr/bin/env python3
"""
server.py — Wyoming TTS server wrapping Supertonic 3.
Uses the proper wyoming AsyncEventHandler / AsyncServer API.

Usage:
    python server.py --onnx-dir /path/to/assets/onnx \
                     --voice-dir /path/to/assets/voice_styles \
                     --port 10200
"""

import argparse
import asyncio
import logging
from functools import partial
from pathlib import Path
from typing import Optional

import numpy as np
from wyoming.audio import AudioChunk, AudioStart, AudioStop
from wyoming.event import Event
from wyoming.info import Attribution, Info, TtsProgram, TtsVoice
from wyoming.server import AsyncServer, AsyncEventHandler
from wyoming.tts import Synthesize

from tts_engine import AVAILABLE_LANGS, SupertonicTTS, Style, load_voice_style
from text_normalize import normalize

_LOGGER = logging.getLogger(__name__)

VOICES = {
    "M1": "Male 1",  "M2": "Male 2",  "M3": "Male 3",  "M4": "Male 4",  "M5": "Male 5",
    "F1": "Female 1","F2": "Female 2","F3": "Female 3","F4": "Female 4","F5": "Female 5",
}

DEFAULT_VOICE = "M1"
DEFAULT_LANG  = "en"
CHUNK_BYTES   = 4096


class SupertonicHandler(AsyncEventHandler):
    """Per-connection Wyoming event handler."""

    def __init__(self, reader, writer, tts: SupertonicTTS,
                 voice_dir: Path, default_voice: str, default_lang: str,
                 total_step: int, speed: float, style_cache: dict):
        super().__init__(reader, writer)
        self.tts           = tts
        self.voice_dir     = voice_dir
        self.default_voice = default_voice
        self.default_lang  = default_lang
        self.total_step    = total_step
        self.speed         = speed
        self._style_cache  = style_cache   # shared across connections

    def _get_style(self, voice_id: str) -> Style:
        if voice_id not in self._style_cache:
            path = self.voice_dir / f"{voice_id}.json"
            if not path.exists():
                _LOGGER.warning("Voice %s not found, falling back to %s", voice_id, self.default_voice)
                path = self.voice_dir / f"{self.default_voice}.json"
            self._style_cache[voice_id] = load_voice_style([str(path)])
        return self._style_cache[voice_id]

    async def handle_event(self, event: Event) -> bool:
        # ── Describe → send Info ──────────────────────────────────────────────
        if event.type == "describe":
            voices = [
                TtsVoice(
                    name=vid,
                    description=desc,
                    version="3.0",
                    attribution=Attribution(
                        name="Supertone Inc.",
                        url="https://github.com/supertone-inc/supertonic",
                    ),
                    installed=True,
                    languages=AVAILABLE_LANGS,
                )
                for vid, desc in VOICES.items()
            ]
            info = Info(
                tts=[TtsProgram(
                    name="Supertonic TTS",
                    description="Supertonic 3 — On-device Neural TTS (31 languages)",
                    version="3.0",
                    attribution=Attribution(
                        name="Supertone Inc.",
                        url="https://github.com/supertone-inc/supertonic",
                    ),
                    installed=True,
                    voices=voices,
                )]
            )
            await self.write_event(info.event())
            return True

        # ── Synthesize → generate + stream audio ─────────────────────────────
        if Synthesize.is_type(event.type):
            synth = Synthesize.from_event(event)
            await self._synthesize(synth)
            return True

        return True

    async def _synthesize(self, synth: Synthesize):
        text = normalize(synth.text)

        # Language: BCP-47 "en-US" → "en"
        lang = DEFAULT_LANG
        if synth.voice and synth.voice.language:
            lang = synth.voice.language.split("-")[0].lower()
        if lang not in AVAILABLE_LANGS:
            lang = DEFAULT_LANG

        voice_name = self.default_voice
        if synth.voice and synth.voice.name and synth.voice.name in VOICES:
            voice_name = synth.voice.name

        _LOGGER.info("Synthesize | voice=%s lang=%s | %r", voice_name, lang, text[:80])

        style = self._get_style(voice_name)
        sr    = self.tts.sample_rate
        loop  = asyncio.get_event_loop()

        # Split text into sentence chunks up front (fast, no ONNX)
        max_len = 120 if lang in ("ko", "ja") else 300
        chunks  = self.tts._chunk(text, max_len)
        silence = SupertonicTTS.to_int16(
            np.zeros(int(0.3 * sr), dtype=np.float32)
        )

        await self.write_event(AudioStart(rate=sr, width=2, channels=1).event())

        total_samples = 0
        for idx, chunk in enumerate(chunks):
            # Each sentence synthesised in thread pool → streams as it finishes
            wav = await loop.run_in_executor(
                None,
                lambda c=chunk: self.tts._infer(c, lang, style, self.total_step, self.speed)[0]
            )
            if idx > 0:
                # inter-sentence silence
                for i in range(0, len(silence), CHUNK_BYTES):
                    await self.write_event(
                        AudioChunk(rate=sr, width=2, channels=1, audio=silence[i:i+CHUNK_BYTES]).event()
                    )
            pcm = SupertonicTTS.to_int16(wav)
            for i in range(0, len(pcm), CHUNK_BYTES):
                await self.write_event(
                    AudioChunk(rate=sr, width=2, channels=1, audio=pcm[i:i+CHUNK_BYTES]).event()
                )
            total_samples += len(wav)

        await self.write_event(AudioStop().event())
        _LOGGER.info("Done | %.2fs audio in %d chunk(s)", total_samples / sr, len(chunks))


# ─── Main ─────────────────────────────────────────────────────────────────────
async def main():
    parser = argparse.ArgumentParser(description="Wyoming Supertonic TTS server")
    parser.add_argument("--onnx-dir",  required=True)
    parser.add_argument("--voice-dir", required=True)
    parser.add_argument("--host",      default="0.0.0.0")
    parser.add_argument("--port",      type=int, default=10200)
    parser.add_argument("--voice",     default=DEFAULT_VOICE, choices=list(VOICES))
    parser.add_argument("--lang",      default=DEFAULT_LANG)
    parser.add_argument("--steps",     type=int, default=8)
    parser.add_argument("--speed",     type=float, default=1.05)
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()

    logging.basicConfig(level=args.log_level.upper(),
                        format="%(asctime)s %(levelname)s %(message)s")

    _LOGGER.info("Loading Supertonic 3 from %s …", args.onnx_dir)
    tts = SupertonicTTS(args.onnx_dir)
    _LOGGER.info("Ready | sample_rate=%d Hz", tts.sample_rate)

    style_cache: dict = {}

    server = AsyncServer.from_uri(f"tcp://{args.host}:{args.port}")
    _LOGGER.info("Wyoming Supertonic listening on %s:%d", args.host, args.port)

    handler_factory = partial(
        SupertonicHandler,
        tts=tts,
        voice_dir=Path(args.voice_dir),
        default_voice=args.voice,
        default_lang=args.lang,
        total_step=args.steps,
        speed=args.speed,
        style_cache=style_cache,
    )

    await server.run(handler_factory)


if __name__ == "__main__":
    asyncio.run(main())
