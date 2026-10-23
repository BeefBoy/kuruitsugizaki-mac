"""Sends a render to audio models on OpenRouter and keeps what each says it hears: a stand-in ear between renders,
to be checked against what the project actually holds before it is trusted. Each answer goes to
tmp/listen/<stem>/<model>.md, and results.json holds time, tokens, cost and errors per model.

  python scripts/listen.py <audio>... [--models a,b | --models @file] [--env FILE] [--prompt FILE] [--out DIR]

The key is OPENROUTER_API_KEY from the environment, or from the .env file --env names. Several audio files go into one
request as A, B, ... in the order given.
"""
import argparse
import base64
import json
import os
import subprocess
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
URL = "https://openrouter.ai/api/v1/chat/completions"
MODELS = "google/gemini-4-argon,qwen/qwen3.8-omni-flash,xiaomi/mimo-v2.5,xiaomi/mimo-v2.6-pro,google/gemini-3.8-flash"
PROMPT = """Listen to the whole recording. Report only what you can hear, with timestamps as m:ss.

1. Length, tempo in BPM, and key or tonal centre.
2. The instruments and sounds, and when each one plays.
3. Sections: every point where the music changes, and what changes there. Any stops or drops in level.
4. Repetition: which material repeats, how long the repeating unit is, and what changes between repeats (melody, harmony, rhythm, layers), if anything.
5. How many distinct parts play at once at the densest moment.
6. Whether the melody and the harmony develop or loop unchanged.
7. Whether it sounds generic or distinctive, and why, in concrete terms.

When you are unsure of something, say unsure rather than guessing."""


def key(env: str | None) -> str:
    if os.environ.get("OPENROUTER_API_KEY"):
        return os.environ["OPENROUTER_API_KEY"]
    if env:
        for line in Path(env).read_text(encoding="utf-8").splitlines():
            k, _, v = line.partition("=")
            if k.strip() == "OPENROUTER_API_KEY":
                return v.strip().strip('"').strip("'")
    sys.exit("no OPENROUTER_API_KEY in the environment or in --env")


def mp3(src: Path, out: Path) -> Path:
    if src.suffix.lower() == ".mp3":
        return src
    dst = out / f"{src.stem}.mp3"
    if not dst.exists() or dst.stat().st_mtime < src.stat().st_mtime:
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(src), "-ac", "2", "-b:a", "192k", str(dst)], check=True)
    return dst


def ask(model: str, audio: list[Path], prompt: str, api_key: str, max_tokens: int) -> dict:
    parts = [{"type": "text", "text": prompt}]
    for i, a in enumerate(audio):
        if len(audio) > 1:
            parts.append({"type": "text", "text": f"Recording {chr(65 + i)}:"})
        parts.append({"type": "input_audio", "input_audio": {"data": base64.b64encode(a.read_bytes()).decode(), "format": "mp3"}})
    body = {"model": model, "messages": [{"role": "user", "content": parts}], "max_tokens": max_tokens, "usage": {"include": True}}
    if model.startswith("openai/gpt-audio"):
        body["modalities"] = ["text"]
    req = urllib.request.Request(URL, json.dumps(body).encode(), {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"})
    t0 = time.monotonic()
    try:
        for attempt in range(3):
            try:
                r = json.load(urllib.request.urlopen(req, timeout=600))
                break
            except urllib.error.URLError as e:
                if isinstance(e, urllib.error.HTTPError) or attempt == 2:
                    raise
                time.sleep(3)
    except urllib.error.HTTPError as e:
        return {"model": model, "seconds": round(time.monotonic() - t0, 1), "error": f"HTTP {e.code}: {e.read().decode(errors='replace')[:400]}"}
    except Exception as e:
        return {"model": model, "seconds": round(time.monotonic() - t0, 1), "error": f"{type(e).__name__}: {e}"[:400]}
    if "error" in r:
        return {"model": model, "seconds": round(time.monotonic() - t0, 1), "error": json.dumps(r["error"])[:400]}
    msg = (r.get("choices") or [{}])[0].get("message") or {}
    u = r.get("usage") or {}
    return {"model": model, "provider": r.get("provider"), "seconds": round(time.monotonic() - t0, 1),
            "prompt_tokens": u.get("prompt_tokens"), "completion_tokens": u.get("completion_tokens"), "cost": u.get("cost"),
            "answer": msg.get("content") or "", "finish": (r.get("choices") or [{}])[0].get("finish_reason")}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("audio", nargs="+")
    ap.add_argument("--models", default=MODELS)
    ap.add_argument("--env")
    ap.add_argument("--prompt")
    ap.add_argument("--out")
    ap.add_argument("--max-tokens", type=int, default=12000)
    ap.add_argument("--workers", type=int, default=8)
    a = ap.parse_args()
    models = (Path(a.models[1:]).read_text(encoding="utf-8").split() if a.models.startswith("@") else a.models.split(","))
    srcs = [Path(p) for p in a.audio]
    out = Path(a.out) if a.out else ROOT / "tmp" / "listen" / "_vs_".join(p.stem for p in srcs)
    out.mkdir(parents=True, exist_ok=True)
    audio = [mp3(p, out) for p in srcs]
    prompt = Path(a.prompt).read_text(encoding="utf-8") if a.prompt else PROMPT
    api_key = key(a.env)
    results = []
    with ThreadPoolExecutor(a.workers) as pool:
        for r in pool.map(lambda m: ask(m, audio, prompt, api_key, a.max_tokens), models):
            results.append(r)
            name = r["model"].replace("/", "__").replace(":", "_")
            if r.get("answer"):
                (out / f"{name}.md").write_text(f"# {r['model']}\n\n{r['answer']}\n", encoding="utf-8")
            print(f"{r['model']:52s} {r['seconds']:6.1f}s  " + (f"ERROR {r['error']}" if r.get("error") else
                  f"{r.get('prompt_tokens')} in  {r.get('completion_tokens')} out  ${r.get('cost')}  {len(r['answer'])} chars  {r.get('finish')}"), flush=True)
    (out / "results.json").write_text(json.dumps({"audio": [str(p) for p in srcs], "prompt": prompt,
                                                  "results": [{k: v for k, v in r.items() if k != "answer"} for r in results]}, indent=1), encoding="utf-8")
    print(f"total ${sum(r.get('cost') or 0 for r in results):.4f}  answers in {out}")


if __name__ == "__main__":
    main()
