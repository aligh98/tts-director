"""Respelling lexicons and reading checks shared by tag_lint.py and ab.py. Stdlib only.

A lexicon is a TSV file: written<TAB>spoken<TAB>note. The written form is what the viewer reads (captions); the spoken
form is what the TTS gets. A note that starts with «✓» means a human confirmed the reading by ear; every other row
is a guess.

The checks list the readings nobody has confirmed, so they can be tested on the real voice before a full run:
- Persian alef rule: every «ا/آ» is read as a long /ɒː/ and no diacritic shortens it; a short /a/ is a fatha only.
  A respelling or {written|spoken} override that adds or drops an «ا» changes vowel length. Example: «بالاخره»
  respelled «بِلاخَرِه» was read «بِلاخَره»; the intended reading needs «بِلَخَرِه», with no «ا».
- trap words (references/fa-traps.tsv): spelled unlike they sound (the Arabic article «ال», final «ی» said «ا»).
- tanwin «ً»: read badly by current models; write «دقیقا» without «اً».
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
FA_TRAPS = ROOT / "references" / "fa-traps.tsv"
DIAC = re.compile("[ً-ْٰ]")
OVERRIDE = re.compile(r"\{([^{}|]+)\|([^{}]+)\}")
TAG_SPLIT = re.compile(r"(\[[^\]]*\])")
ZWNJ = "‌"
LETTER = r"\w؀-ۿ"
ALEFS = "اآأإ"


@dataclass
class Entry:
    written: str
    spoken: str
    note: str = ""

    @property
    def confirmed(self) -> bool:
        return self.note.lstrip().startswith("✓")


def strip_marks(s: str) -> str:
    return DIAC.sub("", s)


def key(s: str) -> str:
    """Comparison key: no vowel marks, ZWNJ and space treated alike."""
    return re.sub(f"[ {ZWNJ}]+", " ", strip_marks(s)).strip()


def load_lexicon(paths: list[str] | None) -> list[Entry]:
    """Later files win over earlier ones. Longest written form first, so a phrase beats its first word."""
    rows: dict[str, Entry] = {}
    for p in paths or []:
        for line in Path(p).read_text(encoding="utf-8").splitlines():
            if not line.strip() or line.lstrip().startswith("#") or "\t" not in line:
                continue
            cols = [c.strip() for c in line.split("\t")]
            rows[key(cols[0])] = Entry(cols[0], cols[1], cols[2] if len(cols) > 2 else "")
    return sorted(rows.values(), key=lambda e: -len(e.written))


def word_re(w: str) -> re.Pattern:
    body = f"[ {ZWNJ}]?".join(re.escape(x) for x in key(w).split(" "))
    return re.compile(rf"(?<![{LETTER}]){body}(?![{LETTER}])")


def respell(text: str, lexicon) -> str:
    """Replace whole words only; [tags] are left alone. Accepts Entry objects or (written, spoken) pairs."""
    parts = TAG_SPLIT.split(text)
    for e in lexicon:
        w, s = (e.written, e.spoken) if isinstance(e, Entry) else e
        pat = word_re(w)
        parts = [p if p.startswith("[") else pat.sub(s, p) for p in parts]
    return "".join(parts)


def alef_count(s: str) -> int:
    s = strip_marks(s)
    return sum(s.count(c) for c in ALEFS)


def load_traps(path: Path = FA_TRAPS) -> list[tuple[str, str, str]]:
    rows = []
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if line.strip() and not line.lstrip().startswith("#") and "\t" in line:
                cols = [c.strip() for c in line.split("\t")] + ["", ""]
                rows.append((cols[0], cols[1], cols[2]))
    return rows


def reading_checks(text: str, lexicon: list[Entry], traps: list[tuple[str, str, str]] | None = None) -> list[str]:
    """Warnings for spans of TEXT whose reading nobody has confirmed by ear (Persian)."""
    traps = load_traps() if traps is None else traps
    out: list[str] = []
    body = TAG_SPLIT.sub(" ", text)
    for m in OVERRIDE.finditer(body):
        w, s = m.group(1), m.group(2)
        if alef_count(w) != alef_count(s):
            out.append(f"«{w}» -> «{s}»: long «ا/آ» {alef_count(w)} -> {alef_count(s)}. Every «ا» is read «آ»; "
                       "a short /a/ is a fatha only. Test it by ear.")
    body = OVERRIDE.sub(lambda m: m.group(1), body)
    hits: set[str] = set()
    for e in lexicon:
        if word_re(e.written).search(body):
            hits.add(key(e.written))
            if not e.confirmed and alef_count(e.written) != alef_count(e.spoken):
                out.append(f"«{e.written}» -> «{e.spoken}»: long «ا/آ» {alef_count(e.written)} -> {alef_count(e.spoken)}, "
                           "not confirmed by ear (no ✓). Every «ا» is read «آ»; a short /a/ is a fatha only.")
    confirmed = {key(e.written) for e in lexicon if e.confirmed}
    for w, kind, how in traps:
        if key(w) not in confirmed and word_re(w).search(body):
            out.append(f"«{w}» ({kind}): spelled unlike it sounds ({how}). Test it by ear, then add a ✓ row to your lexicon.")
    for m in re.finditer(rf"[{LETTER}]*ً[{LETTER}]*", body):
        out.append(f"«{m.group(0)}»: tanwin «ً» is read badly; write it without «اً» (دقیقا، کاملا).")
    return out
