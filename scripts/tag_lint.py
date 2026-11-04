#!/usr/bin/env python3
"""Check a directed TTS script before any credits are spent. Free, no API call.

  tag_lint.py SCRIPT [--model eleven_v4] [--lang auto] [--tempo 1.0] [--cps N] [--lexicon F] [--ab-budget N]
  tag_lint.py SCRIPT --approve          after the person approved this exact text: write SCRIPT.approved.json
  tag_lint.py SCRIPT --check-approved   exit 0 if the stamp matches the text, 3 if not (gate any TTS call on it)
  tag_lint.py SCRIPT --calibrate AUDIO  measure the voice's real chars/second from one finished take

Prints the beat map (estimated time, role, energy, tags per line), ERROR / WARN / INFO lines and an A/B PLAN
(the lines to test first, in priority order, with their cost). Fix every ERROR. Weigh every WARN: a WARN may be
right for this script, say why if you keep it.

Beat labels: every spoken line ends with « # ROLE ENERGY», e.g. «[excited] Wait, this ends Friday!   # HOOK 5».
ROLE is HOOK SETUP REVEAL ITEM TIP JOKE IRONY WARNING CTA; ENERGY is 1-5. Strip « #...» before sending the text to a
TTS (`strip_beats()` here does it). --no-beats for a script that is not a short-form video.

--lexicon F (repeatable): TSV written<TAB>spoken<TAB>note, the respellings your pipeline applies. A note that starts
with «✓» means the reading was confirmed by ear; the reading checks (scripts/reading.py) warn on the rest.
--tempo: the atempo factor you will apply after generation (1.15 = 15% faster), for the time estimate.
--cps: spoken characters (no spaces, pauses included) per second before atempo. Defaults: fa 9.6
       (measured, one Persian ElevenLabs voice), en 14 (rough estimate). Calibrate your voice once.
--lang: fa or en for the language-specific checks; auto guesses.
Markup understood: [tag] audio tag, {written|spoken} override (counted as spoken), " -- " pause token.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from reading import load_lexicon, reading_checks, respell  # noqa: E402

TAG = re.compile(r"\[([^\[\]\n]{1,40})\]")
OVERRIDE = re.compile(r"\{([^{}|]+)\|([^{}]+)\}")
SENT = re.compile(r"[^.!?؟…]+(?:\.\.\.|[.!?؟…]+|$)")
DIAC = re.compile("[ً-ْٰ]")
BEAT = re.compile(r"[ \t]+#\s*([A-Za-z]+)\s*([0-9])?[^\n]*$")
ROLES = {"HOOK", "SETUP", "REVEAL", "ITEM", "TIP", "JOKE", "IRONY", "WARNING", "CTA"}

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
RISKY = LAUGH | {"whispers", "whispering", "sarcastic", "gasps", "sighs", "shouting", "shouts", "crying", "teasing"}
LOW = {"whispers", "whispering", "sighs", "sad", "calm", "thoughtful", "slowly"}
HIGH = {"excited", "shouting", "shouts", "hyped", "amazed"}

# references/*-delivery.md «Register»: written forms that make the voice sound read
FORMAL = {
    "fa": [(r"می‌?خواهی", "می‌خوای"), (r"نمی‌?شود", "نمیشه"), (r"(?<![\w‌])می‌?شود", "میشه"), (r"\sرا(?=[\s.!؟،]|$)", "رو"),
           (r"(?<![\w‌])است(?=[\s.!؟،]|$)", "ـه / هست"), (r"(?<![\w‌])هستند(?=[\s.!؟،]|$)", "هستن"), (r"می‌?باشد", "ـه"),
           (r"بنابراین", "پس"), (r"لازم است", "باید"), (r"پس از", "بعد از"), (r"نخواهد", "نمی‌"),
           (r"(?<![\w‌])آن(?=[\s.!؟،]|$)", "اون"), (r"کاربران|دوستان عزیز|مخاطبان", "تو")],
    "en": [(r"\b(?:do|does|did|is|are|was|were|have|has|would|should|could) not\b", "a contraction (don't, isn't...)"),
           (r"\bit is\b", "it's"), (r"\byou are\b", "you're"), (r"\bwe are\b", "we're"), (r"\bthat is\b", "that's"),
           (r"\b(?:therefore|furthermore|moreover|hence)\b", "so / and"), (r"\b(?:users|one should)\b", "you")],
}
# references/*-delivery.md «Interjections»: 2-4 per reel, none repeated
INTERJ = {
    "fa": ["وای", "اوه", "باورت نمیشه", "جدی میگم", "ببین", "دقت کن", "گوش کن", "خب", "راستی", "حالا", "آها", "آخه",
           "اِه", "ای بابا", "آره", "عه"],
    "en": ["wait", "okay", "no way", "look", "listen", "here's the thing", "so", "now", "oh", "sure", "honestly", "seriously"],
}


class Report:
    def __init__(self):
        self.rows: list[tuple[str, str]] = []

    def add(self, level: str, msg: str):
        self.rows.append((level, msg))


def split_beat(line: str) -> tuple[str, str | None, int | None]:
    m = BEAT.search(line)
    if not m:
        return line, None, None
    return line[:m.start()], m.group(1).upper(), int(m.group(2)) if m.group(2) else None


def strip_beats(text: str) -> str:
    """The text to send to a TTS: beat labels and whole «#» comment lines removed."""
    return "\n".join(split_beat(l)[0] for l in text.splitlines() if not l.lstrip().startswith("#"))


def stamp_path(script: Path) -> Path:
    return script.with_name(script.name + ".approved.json")


def text_hash(script: Path) -> str:
    return hashlib.sha256(script.read_text(encoding="utf-8").strip().encode("utf-8")).hexdigest()


def approval_problem(script: Path) -> str:
    """'' when the stamp holds the hash of this exact text; otherwise why not. Any TTS pipeline can call this."""
    f = stamp_path(script)
    if not f.exists():
        return f"no approval stamp ({f.name}): the text has not been approved."
    if json.loads(f.read_text(encoding="utf-8")).get("sha256") != text_hash(script):
        return f"{script.name} changed after it was approved ({f.name})."
    return ""


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
    ap.add_argument("--lexicon", action="append", help="TSV written<TAB>spoken<TAB>note (✓ = confirmed by ear); repeatable")
    ap.add_argument("--no-beats", action="store_true", help="do not require « # ROLE ENERGY» labels")
    ap.add_argument("--ab-budget", type=int, default=0, help="characters allowed for A/B tests: mark what fits")
    ap.add_argument("--approve", action="store_true", help="write SCRIPT.approved.json (only after the person's OK)")
    ap.add_argument("--check-approved", action="store_true", help="exit 0 if the approval stamp matches the text, else 3")
    ap.add_argument("--calibrate", metavar="AUDIO", help="print the chars/second of AUDIO for this script, then exit")
    a = ap.parse_args()

    path = Path(a.script)
    if a.check_approved:
        problem = approval_problem(path)
        print(problem or f"approved: {stamp_path(path).name} matches {path.name}")
        sys.exit(3 if problem else 0)

    raw = path.read_text(encoding="utf-8")
    lines = [l.rstrip() for l in raw.splitlines()]
    lex = load_lexicon(a.lexicon)
    text = TAG.sub("", strip_beats(raw))
    lang = a.lang if a.lang != "auto" else ("fa" if len(re.findall(r"[؀-ۿ]", text)) > len(re.findall(r"[A-Za-z]", text)) else "en")
    chars = sum(len(plain(l).replace(" ", "")) for l in strip_beats(raw).splitlines())
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
    beats: list[dict] = []
    n_sent = n_excl = n_ell = 0
    print(f"{'line':>4} {'time':>6}  {'' if a.no_beats else 'beat':<10} tags / marks")
    for i, full in enumerate(lines, 1):
        if not full.strip() or full.lstrip().startswith("#"):
            continue
        line, role, energy = split_beat(full)
        body = plain(line)
        dur = len(body.replace(" ", "")) / cps / a.tempo
        tags = [x.strip().lower() for x in TAG.findall(line)]
        sents = [s for s in SENT.findall(body) if s.strip()]
        n_sent += len(sents)
        n_excl += body.count("!")
        n_ell += body.count("...") + body.count("…")
        marks = [f"[{x}]" for x in tags] + (["..."] if "..." in body else []) + (["--"] if "--" in line else [])
        bl = "" if a.no_beats else f"{role or '?'} {energy or '?'}"
        print(f"{i:>4} {t:6.1f}s  {bl:<10} {' '.join(marks) or '-'}   {body[:56]}")
        beats.append({"line": i, "t": t, "role": role, "e": energy, "tags": tags, "text": line.strip(), "body": body})

        if not a.no_beats:
            if role is None or energy is None:
                r.add("ERROR", f"line {i}: no beat label. End the line with « # ROLE ENERGY» (e.g. « # HOOK 5»): plan the arc before the tags.")
            elif role not in ROLES or not 1 <= energy <= 5:
                r.add("ERROR", f"line {i}: «{role} {energy}» is not a beat. Roles: {' '.join(sorted(ROLES))}; energy 1-5.")
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
            if energy and x in LOW and energy >= 4:
                r.add("WARN", f"line {i}: [{x}] on an energy-{energy} beat. A low tag needs a low beat (1-3), or drop it.")
            if energy and x in HIGH and energy <= 2:
                r.add("WARN", f"line {i}: [{x}] on an energy-{energy} beat. Raise the beat or drop the tag.")
            events.append((t, x, i))
        for rx, fix in FORMAL[lang]:
            m = re.search(rx, body, re.I)
            if m:
                r.add("WARN", f"line {i}: «{m.group(0).strip()}» is written register; say «{fix}» ({lang}-delivery.md, Register).")
        if re.search(r"(?:ها){2,}|ههه|خخخ|قاه|\b(?:ha){2,}\b|\bhehe+\b|\blol\b|\blmao\b", body, re.I):
            r.add("WARN", f"line {i}: written laughter («هاها», haha, lol) is read as letters. Use [laughs] or [chuckles].")
        if re.search(r"([اوی])\1\1|([a-z])\2\2\2", body, re.I):
            r.add("WARN", f"line {i}: stretched letters («وااای», «sooooo») read unpredictably; A/B them or write the word normally.")
        for s in sents:
            if len(s.split()) > 22:
                r.add("WARN", f"line {i}: a {len(s.split())}-word sentence. Split it: a reel voice breathes every 8-14 words.")
        if lang == "fa":
            for w in reading_checks(line, lex):
                r.add("WARN", f"line {i}: reading not confirmed by ear: {w}")
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
    for w in [e for e in events if e[1] in LOW]:
        nxt = next((b for b in beats if b["line"] > w[2]), None)
        if nxt and not ("!" in nxt["body"] or set(nxt["tags"]) & HIGH or (nxt["e"] or 0) >= 4):
            r.add("WARN", f"[{w[1]}] on line {w[2]}: the next line (line {nxt['line']}) does not lift the energy back up "
                          f"(no «!», high tag or energy 4+). Lift it, and A/B the pair.")
    if n_sent and n_excl / n_sent > 0.7:
        r.add("WARN", f"«!» on {n_excl} of {n_sent} sentences. When everything shouts nothing does: keep «!» for the peaks, use «.» between.")
    if n_sent and n_ell / n_sent > 0.34:
        r.add("WARN", f"{n_ell} «...» for {n_sent} sentences. Ellipses are pauses: too many and the reel drags.")
    hook = beats[0]["text"] if beats else ""
    hook_words = {"fa": r"وای|اوه|ببین|باورت|می‌دونستی|میدونستی|نکنه", "en": r"\b(?:wait|no way|okay|ok|look|stop|did you know|imagine|never)\b"}[lang]
    if total > 20 and not (TAG.search(hook) or re.search(hook_words + r"|\?|؟|!", hook, re.I)):
        r.add("INFO", "the first line has no hook energy (no tag, question, «!» or interjection). The first 2 seconds decide the watch.")
    greeting = {"fa": r"\W*سلام", "en": r"\W*(?:hi|hey|hello|welcome back)\b"}[lang]
    if re.match(greeting, plain(hook), re.I):
        r.add("WARN", "the video opens with a greeting. Viewers swipe in the first 2 seconds: open on the hook.")
    alltext = " ".join(b["body"] for b in beats)
    found = {w: len(re.findall(rf"(?<![\w‌]){re.escape(w)}(?![\w‌])", alltext, re.I)) for w in INTERJ[lang]}
    if total > 20 and sum(found.values()) < 2:
        r.add("WARN", f"{sum(found.values())} interjection(s). 2-4 natural ones make the voice human ({lang}-delivery.md, Interjections).")
    for w, n in found.items():
        if n > 1 and w not in ("so", "now", "خب", "حالا"):
            r.add("WARN", f"interjection «{w}» used {n} times. Vary them: a repeated one sounds scripted.")

    # the viral arc (SKILL.md «Viral arc»)
    if not a.no_beats and beats and all(b["role"] and b["e"] for b in beats):
        if beats[0]["role"] != "HOOK" or beats[0]["e"] < 4:
            r.add("ERROR", f"the first line is «{beats[0]['role']} {beats[0]['e']}». A short-form video opens on a HOOK at energy 4-5.")
        if total > 20 and not any(b["role"] == "CTA" for b in beats):
            r.add("INFO", "no CTA beat. Fine for pure content; most short-form videos end with one.")
        for b in beats:
            if b["role"] == "TIP" and b["e"] > 3:
                r.add("WARN", f"line {b['line']}: a TIP at energy {b['e']}. A tip lands as a secret at 2-3, then lifts.")
            if b["role"] == "CTA" and b["e"] not in (3, 4):
                r.add("INFO", f"line {b['line']}: CTA at energy {b['e']}. Warm and clear is 3-4; a shouted CTA sounds like an ad.")
        es = [b["e"] for b in beats]
        if len(es) > 4 and max(es) - min(es) < 2:
            r.add("WARN", f"every beat is energy {min(es)}-{max(es)}. A flat arc loses the viewer: add a low beat (tip, sigh, whisper).")
        changes = [0.0]
        for x, y in zip(beats, beats[1:]):
            if abs(y["e"] - x["e"]) >= 2 or set(y["tags"]) & RISKY or "؟" in y["body"] or "?" in y["body"] or "..." in y["body"]:
                changes.append(y["t"])
        changes.append(total)
        for x, y in zip(changes, changes[1:]):
            if y - x > 14:
                r.add("WARN", f"no change of delivery between ~{x:.0f}s and ~{y:.0f}s. Add a pattern interrupt every 8-12 s.")

    # A/B PLAN (SKILL.md «A/B priority»)
    rows: list[tuple[int, str, dict]] = []
    seen: set[str] = set()
    for b in beats:
        if b["role"] == "HOOK" and not any(p[2]["role"] == "HOOK" for p in rows):
            rows.append((1, "hook", b))
        for x in b["tags"]:
            if x in RISKY and x not in seen:
                seen.add(x)
                rows.append((2, f"first [{x}]", b))
        if lang == "fa" and reading_checks(b["text"], lex):
            rows.append((3, "unconfirmed reading (test the word alone)", b))
    for w in [e for e in events if e[1] in LOW]:
        nxt = next((b for b in beats if b["line"] > w[2]), None)
        if nxt:
            rows.append((4, f"lift after [{w[1]}] (with --prev)", nxt))
    cta = next((b for b in beats if b["role"] == "CTA"), None)
    if cta:
        rows.append((5, "CTA (skip if already approved word for word)", cta))
    if not beats or a.no_beats:
        rows = [p for p in rows if p[0] != 1]
    rows.sort(key=lambda p: (p[0], p[2]["line"]))
    if rows:
        print("\nA/B PLAN (priority order; cost = spoken characters per clip):")
        used, done = 0, set()
        for pri, why, b in rows:
            if b["line"] in done:
                continue
            done.add(b["line"])
            cost = len(respell(spoken_text(b["text"]), lex))
            note = ""
            if a.ab_budget:
                ok = used + cost <= a.ab_budget
                used += cost if ok else 0
                note = "  fits" if ok else "  OVER BUDGET: shorten the clip to the risky words, or skip and say so"
            print(f"  {pri}. line {b['line']:<3} {why:<42} ~{cost} ch{note}")
        if a.ab_budget:
            print(f"  budget {a.ab_budget}: {used} used by the lines that fit (one clip each; a second variant doubles it)")

    print(f"\nlang {lang} | {cps} chars/s | estimated length {total:.1f}s at tempo {a.tempo} | sentences {n_sent} | tags {n_tags} ({ratio:.2f}/sentence) | laughs {len(laughs)}")
    for level, msg in sorted(r.rows, key=lambda x: ("ERROR", "WARN", "INFO").index(x[0])):
        print(f"{level:5} {msg}")
    errors = any(lv == "ERROR" for lv, _ in r.rows)

    if a.approve:
        if errors:
            sys.exit("\nNot approved: fix every ERROR first.")
        stamp_path(path).write_text(json.dumps({
            "sha256": text_hash(path),
            "approved": dt.datetime.now().isoformat(timespec="seconds"),
            "warnings_kept": [m for lv, m in r.rows if lv == "WARN"],
        }, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\napproved: {stamp_path(path).name} (any edit to {path.name} needs a new OK and a new --approve)")
    sys.exit(1 if errors else 0)


if __name__ == "__main__":
    main()
