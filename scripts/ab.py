#!/usr/bin/env python3
"""A/B one line of a script: several annotated variants x several stability values, one clip each.

  ab.py "VARIANT A" "VARIANT B" ... --voice VOICE_ID --out DIR [--stability 0.35 --stability 0.5]
  ab.py --file variants.txt --voice VOICE_ID --out DIR        (one variant per line)
  ab.py ... --dry-run                                         (print the cost, send nothing)

Every clip uses the same --seed, so differences come from the text and settings, not chance.
Each clip is transcribed with ElevenLabs Scribe so you can see, without ears:
  LEAK    a tag was read aloud (its word shows up in the transcript)
  events  non-verbal sounds Scribe heard, e.g. [laughter] / [خنده]: the tag was performed
  speed   spoken characters per second
Then listen and pick by ear. Cost: each variant's length once per stability value (STT is billed separately).

--lexicon FILE (repeatable): a TSV of `written<TAB>spoken<TAB>note` respellings applied before sending (longest
first), e.g. a brand name with vowel marks. For Persian, `LISTEN FOR` names the words whose reading nobody has
confirmed by ear (no ✓ note; see scripts/reading.py): judge those words in the clip.
--prev / --next give the model the neighbouring lines as context.

API key: $ELEVENLABS_API_KEY or ELEVENLABS_API_KEY=... in a .env in the cwd or any parent folder.
Voice: --voice or $ELEVENLABS_VOICE_ID.
"""
from __future__ import annotations

import argparse
import base64
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import reading  # noqa: E402

API = "https://api.elevenlabs.io/v1"
TAG = re.compile(r"\[([^\[\]\n]{1,40})\]")
EVENT = re.compile(r"\[[^\]]+\]|\([^)]+\)")


def env_value(name: str) -> str | None:
    if os.environ.get(name):
        return os.environ[name].strip()
    for d in [Path.cwd().resolve(), *Path.cwd().resolve().parents]:
        env = d / ".env"
        if env.exists():
            for line in env.read_text(encoding="utf-8").splitlines():
                if line.strip().startswith(name + "="):
                    v = line.split("=", 1)[1].strip().strip('"').strip("'")
                    if v:
                        return v
    return None


def request(url: str, key: str, data: bytes, ctype: str) -> dict:
    req = urllib.request.Request(url, data=data, headers={"xi-api-key": key, "Content-Type": ctype})
    try:
        return json.load(urllib.request.urlopen(req, timeout=600))
    except urllib.error.HTTPError as e:
        sys.exit(f"ElevenLabs {e.code}: {e.read()[:400].decode('utf-8', 'replace')}")


def tts(text: str, a, stability: float, key: str) -> bytes:
    body = {"text": text, "model_id": a.model, "seed": a.seed,
            "voice_settings": {"stability": stability, "similarity_boost": a.similarity}}
    if a.lang:
        body["language_code"] = a.lang
    if a.prev:
        body["previous_text"] = a.prev
    if a.next:
        body["next_text"] = a.next
    r = request(f"{API}/text-to-speech/{a.voice}/with-timestamps?output_format=mp3_44100_128", key, json.dumps(body).encode(), "application/json")
    return base64.b64decode(r["audio_base64"])


def stt(path: Path, lang: str, key: str) -> str:
    b = uuid.uuid4().hex
    fields = [("model_id", "scribe_v1"), ("tag_audio_events", "true")] + ([("language_code", lang)] if lang else [])
    parts = [f'--{b}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in fields]
    parts.append(f'--{b}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode() + path.read_bytes() + b"\r\n")
    parts.append(f"--{b}--\r\n".encode())
    return request(f"{API}/speech-to-text", key, b"".join(parts), f"multipart/form-data; boundary={b}").get("text", "")


def seconds(path: Path) -> float:
    if not shutil.which("ffprobe"):
        return 0.0
    out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(path)], capture_output=True, text=True).stdout
    return float(out.strip() or 0)


def load_lexicon(paths) -> list[reading.Entry]:
    if isinstance(paths, str):
        paths = [paths]
    return reading.load_lexicon(paths)


def respell(text: str, lexicon) -> str:
    """Replace whole words only; tags are left alone. LEXICON: Entry objects or (written, spoken) pairs.
    A {written|spoken} override is sent as its spoken part."""
    return reading.respell(reading.OVERRIDE.sub(lambda m: m.group(2), text), lexicon)


def leaks(text: str, heard: str) -> list[str]:
    """Tags whose words were spoken instead of performed (performed events are bracketed by Scribe)."""
    heard_words = EVENT.sub(" ", heard.lower())
    return [t for t in TAG.findall(text) if any(w[:5] in heard_words for w in re.findall(r"[a-z]{4,}", t.lower()))]


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("variants", nargs="*")
    ap.add_argument("--file", help="one variant per line")
    ap.add_argument("--out", required=True)
    ap.add_argument("--voice", default=env_value("ELEVENLABS_VOICE_ID"))
    ap.add_argument("--model", default="eleven_v4")
    ap.add_argument("--lang", default="", help="ISO 639-1 language_code, e.g. fa or en (also used for STT)")
    ap.add_argument("--stability", type=float, action="append", help="repeat for a grid (default 0.5)")
    ap.add_argument("--similarity", type=float, default=0.8)
    ap.add_argument("--seed", type=int, default=1234)
    ap.add_argument("--prev", help="the line before (context, not spoken)")
    ap.add_argument("--next", help="the line after (context, not spoken)")
    ap.add_argument("--lexicon", action="append", help="TSV of written<TAB>spoken<TAB>note respellings; repeatable")
    ap.add_argument("--en-check", action="store_true", help="also transcribe as English (catches tags leaked in a non-English script)")
    ap.add_argument("--dry-run", action="store_true", help="print what would be sent and the character cost")
    a = ap.parse_args()

    variants = list(a.variants)
    if a.file:
        variants += [l.strip() for l in Path(a.file).read_text(encoding="utf-8").splitlines() if l.strip()]
    if not variants:
        ap.error("give at least one variant")
    lex = load_lexicon(a.lexicon)
    if a.lang in ("", "fa"):
        for v in variants:
            for w in reading.reading_checks(v, lex):
                print(f"LISTEN FOR {w}")  # an A/B clip is an ear test: name the words to judge
    grid = [(i, v, respell(v, lex), s) for i, v in enumerate(variants) for s in (a.stability or [0.5])]
    cost = sum(len(sp) for _, _, sp, _ in grid)
    print(f"{len(grid)} clips, {cost} characters")
    if a.dry_run:
        for i, _, sp, s in grid:
            print(f"  ab_{i:02d}_s{round(s * 100):02d}  {sp}")
        return
    if not a.voice:
        ap.error("--voice is required (or set ELEVENLABS_VOICE_ID)")
    key = env_value("ELEVENLABS_API_KEY") or sys.exit("ELEVENLABS_API_KEY is not set (env var or .env).")
    out = Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    rows = []
    for i, v, spoken, s in grid:
        f = out / f"ab_{i:02d}_s{round(s * 100):02d}.mp3"
        f.write_bytes(tts(spoken, a, s, key))
        heard = [stt(f, a.lang, key)] + ([stt(f, "en", key)] if a.en_check and a.lang != "en" else [])
        dur = seconds(f)
        plain = len(re.sub(r"\s", "", TAG.sub("", spoken)))
        leak = leaks(v, " ".join(heard))
        events = sorted(set(EVENT.findall(" ".join(heard))))
        rows.append({"file": f.name, "variant": v, "spoken": spoken, "stability": s, "seed": a.seed, "seconds": round(dur, 2),
                     "chars_per_s": round(plain / dur, 1) if dur else None, "leak": leak, "events": events, "heard": heard})
        print(f"{f.name}  s={s}  {dur:5.2f}s  {rows[-1]['chars_per_s']} ch/s  {'LEAK ' + ','.join(leak) if leak else 'ok'}  {' '.join(events)}")
        print(f"   {v}")
        for h in heard:
            print(f"   heard: {h}")
    (out / "ab.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


if __name__ == "__main__":
    main()
