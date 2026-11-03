#!/usr/bin/env python3
"""Check an annotated TTS script for over-tagging, flat delivery and model mistakes. Free, no API call.

  tag_lint.py SCRIPT [--model eleven_v4] [--lang auto] [--tempo 1.0] [--cps N]
  tag_lint.py SCRIPT --calibrate AUDIO     measure the voice's real chars/second from one finished take

Prints a beat map (estimated time, tags, delivery marks per line), then ERROR / WARN / INFO lines.
Fix every ERROR. Weigh every WARN: a WARN may be right for this script, say why if you keep it.

--tempo: the atempo factor you will apply after generation (1.17 = 17% faster), for the time estimate.
--cps: spoken characters (no spaces, pauses included) per second before atempo. Defaults: fa 9.6
       (measured, one Persian ElevenLabs voice), en 14 (rough estimate). Calibrate your voice once.
--lang: fa or en for the language-specific checks (hook, greeting, written laughter); auto guesses.
Markup understood: [tag] audio tag, {written|spoken} override (counted as spoken), " -- " pause token.
"""
from __future__ import annotations

import argparse
import re
import shutil
import subprocess
import sys
from pathlib import Path

TAG = re.compile(r"\[([^\[\]\n]{1,40})\]")
OVERRIDE = re.compile(r"\{([^{}|]+)\|([^{}]+)\}")
SENT = re.compile(r"[^.!?؟…]+(?:\.\.\.|[.!?؟…]+|$)")
DIAC = re.compile("[ً-ْٰ]")

LAUGH = {"laughs", "laughs harder", "starts laughing", "chuckles", "giggles", "wheezing", "snorts", "laughing"}
NONVERBAL = LAUGH | {"sighs", "exhales", "exhales sharply", "inhales deeply", "gasps", "gulps", "swallows", "clears throat",
                     "short pause", "long pause", "pause"}
DELIVERY = {"excited", "whispers", "whispering", "shouting", "shouts", "sarcastic", "curious", "surprised", "happy", "sad",
            "angry", "annoyed", "thoughtful", "mischievously", "dramatic", "calm", "conversational", "warmly", "playfully",
            "confident", "impressed", "amazed", "nervous", "serious", "crying", "frustrated", "relieved", "proud",
            "deadpan", "hyped", "fast", "slowly", "teasing", "matter-of-fact", "awe", "in awe", "rushed"}
SFX = {"applause", "clapping", "explosion", "gunshot"}
STAGING = {"music", "standing", "sitting", "walking", "background music", "intro", "outro"}
KNOWN = NONVERBAL | DELIVERY | SFX


class Report:
    def __init__(self):
        self.rows: list[tuple[str, str]] = []

    def add(self, level: str, msg: str):
        self.rows.append((level, msg))


def spoken_text(s: str) -> str:
    return OVERRIDE.sub(lambda m: m.group(2), s)


def plain(s: str) -> str:
    return re.sub(r"\s+", " ", DIAC.sub("", TAG.sub("", spoken_text(s)).replace("--", " "))).strip()


def main():
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("script")
    ap.add_argument("--model", default="eleven_v4")
    ap.add_argument("--tempo", type=float, default=1.0)
    ap.add_argument("--cps", type=float)
    ap.add_argument("--lang", default="auto", choices=["auto", "fa", "en"])
    ap.add_argument("--calibrate", metavar="AUDIO", help="print the chars/second of AUDIO for this script, then exit")
    a = ap.parse_args()

    lines = [l.rstrip() for l in Path(a.script).read_text(encoding="utf-8").splitlines()]
    text = TAG.sub("", "\n".join(lines))
    lang = a.lang if a.lang != "auto" else ("fa" if len(re.findall(r"[؀-ۿ]", text)) > len(re.findall(r"[A-Za-z]", text)) else "en")
    chars = sum(len(plain(l).replace(" ", "")) for l in lines)
    if a.calibrate:
        if not shutil.which("ffprobe"):
            sys.exit("--calibrate needs ffprobe (ffmpeg) on PATH.")
        out = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", a.calibrate],
                             capture_output=True, text=True).stdout.strip()
        dur = float(out or 0)
        if not dur:
            sys.exit(f"could not read the duration of {a.calibrate}")
        print(f"{chars} chars / {dur:.2f}s = {chars / dur:.2f} chars/s. Use --cps {chars / dur:.1f} for this voice.")
        return
    cps = a.cps or {"fa": 9.6, "en": 14.0}[lang]
    r = Report()
    tags_model = a.model.startswith(("eleven_v3", "eleven_v4"))
    t = 0.0
    events: list[tuple[float, str, int]] = []  # (time, tag, line)
    n_sent = n_excl = n_ell = 0
    print(f"{'line':>4} {'time':>6}  tags / marks")
    for i, line in enumerate(lines, 1):
        if not line.strip():
            continue
        body = plain(line)
        dur = len(body.replace(" ", "")) / cps / a.tempo
        tags = [x.strip().lower() for x in TAG.findall(line)]
        sents = [s for s in SENT.findall(body) if s.strip()]
        n_sent += len(sents)
        n_excl += body.count("!")
        n_ell += body.count("...") + body.count("…")
        marks = [f"[{x}]" for x in tags] + (["..."] if "..." in body else []) + (["--"] if "--" in line else [])
        print(f"{i:>4} {t:6.1f}s  {' '.join(marks) or '-'}   {body[:60]}")

        if not tags_model and tags:
            r.add("ERROR", f"line {i}: {a.model} reads [tags] aloud. Remove them; steer with style/stability or SSML <break>.")
        if tags_model and re.search(r"<break|<phoneme|<speak|<prosody", line):
            r.add("ERROR", f"line {i}: {a.model} has no SSML. Use ... or a [short pause] tag.")
        if re.search(r"(\]\s*\[[^\]]*\]\s*\[)", line):
            r.add("ERROR", f"line {i}: three tags stacked. Use one, two at most.")
        for x in tags:
            if x in STAGING:
                r.add("ERROR", f"line {i}: [{x}] is staging, not voice. The model may play or say it. Remove.")
            elif re.search(r"[؀-ۿ]", x):
                r.add("WARN", f"line {i}: [{x}] is a Persian tag. It is not read aloud, but English tags are what the model was trained on: use one.")
            elif x not in KNOWN and not x.startswith("strong "):
                r.add("WARN", f"line {i}: [{x}] is not in the tested set. Probe it with ab.py before the full run.")
            events.append((t + 0.0, x, i))
        if re.search(r"(?:ها){2,}|ههه|خخخ|قاه|\b(?:ha){2,}\b|\bhehe+\b|\blol\b|\blmao\b", body, re.I):
            r.add("WARN", f"line {i}: written laughter («هاها», haha, lol) is read as letters. Use [laughs] or [chuckles].")
        for s in sents:
            if len(s.split()) > 22:
                r.add("WARN", f"line {i}: a {len(s.split())}-word sentence. Split it: a reel voice breathes every 8-14 words.")
        t += dur

    total = t
    n_tags = len(events)
    ratio = n_tags / max(n_sent, 1)
    laughs = [e for e in events if e[1] in LAUGH]
    if ratio > 0.5:
        r.add("ERROR", f"{n_tags} tags for {n_sent} sentences ({ratio:.2f}/sentence). Over-tagged: keep the beats only (aim <= 0.3).")
    elif ratio > 0.34:
        r.add("WARN", f"{n_tags} tags for {n_sent} sentences ({ratio:.2f}/sentence). Aim <= 0.3; drop tags that do not change the delivery.")
    if total > 20 and n_tags == 0:
        r.add("INFO", "no tags at all. Fine if the text carries the energy; consider one on the hook and one pattern-interrupt.")
    if len(laughs) > 2:
        r.add("WARN", f"{len(laughs)} laughs. More than two in a reel sounds forced: keep the one on the real joke.")
    for x, y in zip(laughs, laughs[1:]):
        if y[0] - x[0] < 20:
            r.add("WARN", f"laughs on lines {x[2]} and {y[2]} are ~{y[0] - x[0]:.0f}s apart. Space them 20s+ or keep one.")
    for x, y in zip(events, events[1:]):
        if x[1] == y[1] and x[1] not in ("short pause",):
            r.add("WARN", f"[{x[1]}] twice in a row (lines {x[2]}, {y[2]}). The second adds nothing: drop it or change the delivery.")
    whispers = [e for e in events if e[1].startswith("whisper")]
    for w in whispers:
        nxt = [e for e in events if e[2] > w[2]]
        if nxt and nxt[0][2] - w[2] > 2:
            r.add("INFO", f"[whispers] on line {w[2]} has no delivery tag in the next lines: check by ear that the voice comes back up.")
    if n_sent and n_excl / n_sent > 0.7:
        r.add("WARN", f"«!» on {n_excl} of {n_sent} sentences. When everything shouts nothing does: keep «!» for the peaks, use «.» between.")
    if n_sent and n_ell / n_sent > 0.34:
        r.add("WARN", f"{n_ell} «...» for {n_sent} sentences. Ellipses are pauses: too many and the reel drags.")
    hook = next((l for l in lines if l.strip()), "")
    hook_words = {"fa": r"وای|اوه|ببین|باورت|می‌دونستی|میدونستی|نکنه", "en": r"\b(?:wait|no way|okay|ok|look|stop|did you know|imagine|never)\b"}[lang]
    if total > 20 and not (TAG.search(hook) or re.search(hook_words + r"|\?|؟|!", hook, re.I)):
        r.add("INFO", "the first line has no hook energy (no tag, question, «!» or interjection). The first 2 seconds decide the watch.")
    greeting = {"fa": r"\W*سلام", "en": r"\W*(?:hi|hey|hello|welcome back)\b"}[lang]
    if re.match(greeting, plain(hook), re.I):
        r.add("WARN", "the video opens with a greeting. Viewers swipe in the first 2 seconds: open on the hook.")

    print(f"\nlang {lang} | {cps} chars/s | estimated length {total:.1f}s at tempo {a.tempo} | sentences {n_sent} | tags {n_tags} ({ratio:.2f}/sentence) | laughs {len(laughs)}")
    for level, msg in sorted(r.rows, key=lambda x: ("ERROR", "WARN", "INFO").index(x[0])):
        print(f"{level:5} {msg}")
    sys.exit(1 if any(lv == "ERROR" for lv, _ in r.rows) else 0)


if __name__ == "__main__":
    main()
