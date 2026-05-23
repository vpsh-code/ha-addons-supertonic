"""
tts_engine.py — Python port of Supertonic 3 ONNX inference (mirrors helper.js).
"""

import json
import math
import random
import struct
from pathlib import Path
from typing import Callable, Generator, Optional

import numpy as np
import onnxruntime as ort


AVAILABLE_LANGS = [
    "en","ko","ja","ar","bg","cs","da","de","el","es","et","fi","fr",
    "hi","hr","hu","id","it","lt","lv","nl","pl","pt","ro","ru","sk",
    "sl","sv","tr","uk","vi","na"
]


# ─── Text processor ───────────────────────────────────────────────────────────
class UnicodeProcessor:
    def __init__(self, indexer: list):
        self.indexer = indexer

    def preprocess(self, text: str, lang: str) -> str:
        import unicodedata, re
        text = unicodedata.normalize("NFKD", text)
        # Strip emojis
        text = re.sub(
            "[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF"
            "\U0001F680-\U0001F6FF\U00002600-\U000027BF"
            "\U0001F1E6-\U0001F1FF]+", "", text)
        # Symbol replacements
        for src, dst in [("–","-"),("‑","-"),("—","-"),("_"," "),
                         ("\u201C",'"'),("\u201D",'"'),("\u2018","'"),("\u2019","'"),
                         ("´","'"),("[", " "),("]"," "),("|"," "),("/"," "),
                         ("#"," "),("→"," "),("←"," ")]:
            text = text.replace(src, dst)
        text = re.sub(r"[♥☆♡©\\]", "", text)
        text = text.replace("@", " at ").replace("e.g.,","for example,").replace("i.e.,","that is,")
        for pat, rep in [(" ,",","),(r" \.","."),(" !","!"),(" [?]","?"),(" ;",";"),(r" :",":")]:
            text = re.sub(pat, rep, text)
        text = re.sub(r'\s+', ' ', text).strip()
        if text and text[-1] not in '.!?;:,")]}':
            text += "."
        text = f"<{lang}>{text}</{lang}>"
        return text

    def encode(self, texts: list[str], langs: list[str]):
        processed = [self.preprocess(t, l) for t, l in zip(texts, langs)]
        lengths = [len(t) for t in processed]
        max_len = max(lengths)

        ids = np.zeros((len(texts), max_len), dtype=np.int64)
        for i, t in enumerate(processed):
            for j, ch in enumerate(t):
                cp = ord(ch)
                ids[i, j] = self.indexer[cp] if cp < len(self.indexer) else -1

        mask = np.zeros((len(texts), 1, max_len), dtype=np.float32)
        for i, l in enumerate(lengths):
            mask[i, 0, :l] = 1.0

        return ids, mask


# ─── Style ────────────────────────────────────────────────────────────────────
class Style:
    def __init__(self, ttl: np.ndarray, dp: np.ndarray):
        self.ttl = ttl
        self.dp  = dp


def load_voice_style(paths: list[str]) -> Style:
    bsz = len(paths)
    first = json.loads(Path(paths[0]).read_text())
    t_dims = first["style_ttl"]["dims"]
    d_dims = first["style_dp"]["dims"]

    ttl = np.zeros((bsz, t_dims[1], t_dims[2]), dtype=np.float32)
    dp  = np.zeros((bsz, d_dims[1], d_dims[2]), dtype=np.float32)

    for i, p in enumerate(paths):
        s = json.loads(Path(p).read_text())
        ttl[i] = np.array(s["style_ttl"]["data"], dtype=np.float32).reshape(t_dims[1], t_dims[2])
        dp[i]  = np.array(s["style_dp"]["data"],  dtype=np.float32).reshape(d_dims[1], d_dims[2])

    return Style(ttl, dp)


# ─── TTS Engine ───────────────────────────────────────────────────────────────
class SupertonicTTS:
    def __init__(self, onnx_dir: str):
        opts = ort.SessionOptions()
        opts.graph_optimization_level = ort.GraphOptimizationLevel.ORT_ENABLE_ALL
        opts.enable_mem_pattern = False       # reduces peak memory
        opts.enable_mem_reuse   = True        # reuse buffers between runs
        opts.intra_op_num_threads = 2         # limit CPU threads → less RAM overhead
        providers = ["CPUExecutionProvider"]

        base = Path(onnx_dir)
        self.dp_sess   = ort.InferenceSession(str(base/"duration_predictor.onnx"), opts, providers=providers)
        self.enc_sess  = ort.InferenceSession(str(base/"text_encoder.onnx"),       opts, providers=providers)
        self.vec_sess  = ort.InferenceSession(str(base/"vector_estimator.onnx"),   opts, providers=providers)
        self.voc_sess  = ort.InferenceSession(str(base/"vocoder.onnx"),            opts, providers=providers)

        cfgs = json.loads((base/"tts.json").read_text())
        self.cfgs = cfgs
        self.sample_rate: int = cfgs["ae"]["sample_rate"]

        indexer = json.loads((base/"unicode_indexer.json").read_text())
        self.processor = UnicodeProcessor(indexer)

    # ── chunk long text ─────────────────────────────────────────────────────
    @staticmethod
    def _chunk(text: str, max_len: int = 300) -> list[str]:
        import re
        paras = [p.strip() for p in re.split(r'\n\s*\n+', text.strip()) if p.strip()]
        chunks = []
        for para in paras:
            sentences = re.split(r'(?<=[.!?])\s+', para)
            current = ""
            for s in sentences:
                if len(current) + len(s) + 1 <= max_len:
                    current = (current + " " + s).strip() if current else s
                else:
                    if current:
                        chunks.append(current)
                    current = s
            if current:
                chunks.append(current)
        return chunks or [text]

    # ── single-batch inference ───────────────────────────────────────────────
    def _infer(self, text: str, lang: str, style: Style,
               total_step: int, speed: float = 1.05,
               progress_cb: Optional[Callable] = None) -> tuple[np.ndarray, float]:

        text_ids, text_mask = self.processor.encode([text], [lang])

        # Duration predictor
        dp_out = self.dp_sess.run(None, {
            "text_ids":  text_ids,
            "style_dp":  style.dp,
            "text_mask": text_mask,
        })
        duration = dp_out[0].flatten().tolist()
        duration = [d / speed for d in duration]

        # Text encoder
        enc_out = self.enc_sess.run(None, {
            "text_ids":  text_ids,
            "style_ttl": style.ttl,
            "text_mask": text_mask,
        })
        text_emb = enc_out[0]

        # Noisy latent
        xt, latent_mask = self._sample_noisy(duration)

        total_arr = np.array([total_step], dtype=np.float32)

        for step in range(total_step):
            if progress_cb:
                progress_cb(step + 1, total_step)

            cur_arr = np.array([step], dtype=np.float32)

            vec_out = self.vec_sess.run(None, {
                "noisy_latent": xt,
                "text_emb":     text_emb,
                "style_ttl":    style.ttl,
                "latent_mask":  latent_mask,
                "text_mask":    text_mask,
                "current_step": cur_arr,
                "total_step":   total_arr,
            })
            xt = vec_out[0]

        # Vocoder
        voc_out = self.voc_sess.run(None, {"latent": xt})
        wav = voc_out[0].flatten()

        dur_total = float(sum(duration))
        wav_len = int(self.sample_rate * dur_total)
        return wav[:wav_len], dur_total

    def _sample_noisy(self, duration: list[float]):
        sr    = self.sample_rate
        cfgs  = self.cfgs
        base_chunk  = cfgs["ae"]["base_chunk_size"]
        compress    = cfgs["ttl"]["chunk_compress_factor"]
        latent_dim  = cfgs["ttl"]["latent_dim"]

        max_dur = max(duration)
        wav_len_max = int(max_dur * sr)
        chunk_size  = base_chunk * compress
        latent_len  = math.ceil(wav_len_max / chunk_size)
        latent_dim_v= latent_dim * compress

        # Box-Muller
        u1 = np.clip(np.random.random((1, latent_dim_v, latent_len)), 1e-4, 1.0)
        u2 = np.random.random((1, latent_dim_v, latent_len))
        xt = (np.sqrt(-2.0 * np.log(u1)) * np.cos(2 * np.pi * u2)).astype(np.float32)

        wav_len = int(duration[0] * sr)
        lat_len_actual = math.ceil(wav_len / chunk_size)
        mask = np.zeros((1, 1, latent_len), dtype=np.float32)
        mask[0, 0, :lat_len_actual] = 1.0
        xt *= mask

        return xt, mask

    # ── public API ─────────────────────────────────────────────────────────
    def synthesize(self, text: str, lang: str, style: Style,
                   total_step: int = 8, speed: float = 1.05,
                   silence_sec: float = 0.3,
                   progress_cb: Optional[Callable] = None) -> np.ndarray:
        max_len = 120 if lang in ("ko", "ja") else 300
        chunks  = self._chunk(text, max_len)
        audio_parts = []

        for chunk in chunks:
            wav, _ = self._infer(chunk, lang, style, total_step, speed, progress_cb)
            if audio_parts:
                silence = np.zeros(int(silence_sec * self.sample_rate), dtype=np.float32)
                audio_parts.append(silence)
            audio_parts.append(wav)

        return np.concatenate(audio_parts) if audio_parts else np.array([], dtype=np.float32)

    def synthesize_streaming(self, text: str, lang: str, style: Style,
                             total_step: int = 8, speed: float = 1.05,
                             silence_sec: float = 0.3,
                             progress_cb: Optional[Callable] = None
                             ) -> Generator[np.ndarray, None, None]:
        """Yield one float32 PCM array per sentence chunk as it is synthesised."""
        max_len = 120 if lang in ("ko", "ja") else 300
        chunks  = self._chunk(text, max_len)
        silence = np.zeros(int(silence_sec * self.sample_rate), dtype=np.float32)
        first   = True

        for chunk in chunks:
            wav, _ = self._infer(chunk, lang, style, total_step, speed, progress_cb)
            if not first:
                yield silence.copy()
            first = False
            yield wav

    @staticmethod
    def to_int16(wav: np.ndarray) -> bytes:
        wav_clipped = np.clip(wav, -1.0, 1.0)
        return (wav_clipped * 32767).astype(np.int16).tobytes()
