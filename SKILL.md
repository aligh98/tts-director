---
name: tts-director
description: Direct a script for text-to-speech so it sounds like a real, engaged human, not a narrator reading. Persian (Farsi) first, English supported. It rewrites the text for the ear, maps the beats of a short-form video (reel, TikTok, Short), and adds ElevenLabs v3/v4 audio tags only where they earn their place ([excited], [whispers], [laughs], [chuckles], [gasps], [sighs], [sarcastic]...). It checks for over-tagging with a free linter and A/B-tests risky lines on the real voice before a full run. It also covers model rules (eleven_v4 ignores speed and style; multilingual_v2, flash and turbo read tags aloud) and converts the result for other TTS engines (OpenAI, Azure, Google). Use for ANY script headed to ElevenLabs or another TTS, and whenever someone wants a voice that is more exciting, emotional, expressive, human or viral, or asks about tone, emotion, laughter, pauses or pacing in TTS: «لحن»، «احساس»، «هیجان»، «خنده»، «تگ»، «انسانی‌تر»، «گوینده»، «صداگذاری».
---

# TTS director: write for the ear, tag the beats, test by ear

A great voiceover is about 80% text and 20% tags. The text sets the rhythm, the register and where the energy goes. Tags only push a delivery the text has already set up. A script with a tag on every line sounds like an over-acted ad and loses the viewer. A script with none often sounds read.

This skill does not replace your TTS pipeline. It prepares the text that goes into it. Scripts are stdlib Python 3.9+; ffmpeg/ffprobe are optional and give durations.

## Workflow

Do the steps in order. The tools check them, so none can be skipped silently:
- `tag_lint.py` gives an ERROR when a line has no beat label;
- `tag_lint.py --check-approved` fails until the person has approved the exact text. Gate your TTS call on it.

Before step 1, read the delivery reference for the script's language (`references/persian-delivery.md` or `references/english-delivery.md`) and `references/audio-tags.md`. The linter checks only part of them.

1. **Beat map, inside the script.** End every spoken line with « # ROLE ENERGY» (energy 1–5):
   ```
   [excited] Wait, this ends Friday... and it's not coming back!   # HOOK 5
   [whispers] Here's the trick...                                  # TIP 2
   ```
   The roles are:
   - HOOK
   - SETUP
   - REVEAL
   - ITEM (a list point)
   - TIP (insider advice)
   - JOKE or IRONY
   - WARNING
   - CTA

   Plan the arc before touching words. See [Viral arc](#viral-arc). Strip the labels before the text goes to the TTS: `tag_lint.strip_beats(text)` does it, or remove everything from « #» to the end of each line. For a script that is not a short-form video, pass `--no-beats`.
2. **Rewrite for the ear.** Keep the meaning and every fact. Rewriting means:
   - shorter sentences;
   - the punch word moved to the end;
   - the interjections a native speaker would actually use;
   - punctuation that marks breaths.

   For Persian, follow the **alef rule** in `persian-delivery.md`: the voice reads every «ا» as a long «آ», and a short /a/ is a fatha only. Some words are spelled unlike they sound («بالاخره»، «حتی»، «فوق‌العاده»; see `references/fa-traps.tsv`). Treat a respelling as a guess until a human confirms it by ear; mark confirmed rows in your lexicon with a note that starts with «✓».
3. **Tag pass.** Tag only the beats the text alone cannot carry, within the [Tag budget](#tag-budget). For tag names and what each one is for, see `references/audio-tags.md`.
4. **Lint (free):**
   ```
   python scripts/tag_lint.py SCRIPT --model eleven_v4 --tempo 1.15 [--lexicon words.tsv] [--ab-budget 160]
   ```
   It prints the beat map with estimated times, then checks:
   - **Beats and arc:**
     - a missing or invalid label (ERROR);
     - a first line that is not a HOOK at energy 4–5 (ERROR);
     - a TIP above energy 3;
     - a flat arc;
     - more than 14 s without a change of delivery;
     - a low tag on a high beat, or a high tag on a low beat;
     - a whisper or sigh not followed by a line that lifts the energy.
   - **Tags:**
     - over-tagging;
     - laughs that are too many or too close together;
     - a repeated tag;
     - staging tags;
     - SSML on v3/v4, and tags on models that read them aloud.
   - **Ear rewrite:**
     - written register («را»، «است»، «می‌شود»; uncontracted English);
     - fewer than 2 interjections, or a repeated one;
     - «!» on every line, and too many ellipses;
     - long sentences;
     - written laughter («هاها», "haha");
     - stretched letters;
     - an opening greeting.
   - **Persian readings:**
     - unconfirmed respellings that change the number of «ا/آ»;
     - `{written|spoken}` overrides that do the same;
     - trap words;
     - tanwin.

   Fix every ERROR. Keep a WARN only when you can say why. The **A/B PLAN** at the end lists the lines to test, in priority order, with their cost; see [A/B priority](#ab-priority).
5. **Approval.** Show the person the full text with its beat map and the A/B plan. Generating audio costs them credits, and the wording is theirs to approve. After their OK:
   ```
   python scripts/tag_lint.py SCRIPT --approve
   ```
   This writes `SCRIPT.approved.json`, the SHA-256 of the stripped file text. `--approve` refuses while there is an ERROR. Before every TTS call, run `tag_lint.py SCRIPT --check-approved`: exit 0 means approved, exit 3 means no stamp or a changed text. Any edit needs a new OK. A pipeline can also compare the hash itself: `sha256(file_text.strip())`. Choosing an A/B take does not approve the whole text.
6. **A/B the risky lines** in the A/B plan's order. Check the cost first; `--dry-run` sends nothing:
   ```
   python scripts/ab.py "VARIANT A" "VARIANT B" --voice VOICE_ID --stability 0.35 --stability 0.5 --prev "line before" --next "line after" --out probe/ab --dry-run
   ```
   Remove `--dry-run` to generate. Every clip uses the same `--seed`, so the differences come from the text and the settings, not from chance. Each clip is transcribed:
   - `LEAK` means a tag was read aloud as a word. Drop or rephrase that tag.
   - An event such as `[laughter]` or `[خنده]` means the sound was performed.
   - `LISTEN FOR` (Persian) names the words whose reading is unconfirmed.

   Speech-to-text cannot judge excitement or vowel length, so let a human ear pick the winner. If the chosen take changes the text, lint and approve again.
7. **Generate the full script** with the chosen variants and settings, after `--check-approved` passes. Then:
   - Set the pacing with `ffmpeg -af atempo=1.1` (1.10–1.20 keeps pitch), not with a speed setting. If you have word timings, divide them by the same factor.
   - To fix one line, regenerate only that chunk with `previous_text`/`next_text` and splice it in.

## Tag budget

**Never over-tag.** Every tag must help retention or make the voice more human. A tag that repeats what the text already says is noise.

- **Density:** about 1 tag per 3–4 sentences, which is 4–8 tags in a 60–90 s reel. The linter errors above 0.5 tags per sentence and warns above 0.34.
- **Baseline energy is not a tag.** The voice, a stability of 0.3–0.4 and punchy text set the overall energy. Do not put `[excited]` on every line. Save it for 2–3 peaks: the hook, the big reveal and the CTA push.
- **Laughs: 0 to 2 per reel, and never forced.** Laugh only where a person would:
  - after a real joke or irony;
  - on a self-aware aside;
  - for relief after a tense point.

  Never laugh on numbers, dates, prices, the offer itself or the CTA keyword. Keep laughs 20 s or more apart. Pick the tag by size: `[chuckles]` is the safe, light one; `[laughs]` is a clear laugh; use `[laughs harder]` for one big moment at most.
- **Contrast beats intensity.** Attention comes from change. Use one change of delivery every 8–12 s; this is the pattern interrupt. For example:
  - a whisper after an energetic line;
  - a pause before a reveal;
  - a sigh before a pain point;
  - a gasp before an unbelievable fact.
- **One or two tags at a spot, never three.** Put the tag right before the words it colours. Its effect runs to about the end of that sentence.
- **Bring the energy back after `[whispers]` or `[sighs]`.** Do it on the next line with the text (a «!», a short punch) or with a delivery tag. Check it by ear.
- **Keep clarity lines clean.** Numbers, dates, prices, product names and the CTA keyword are said plainly. A warm tag may come before the CTA sentence, never inside the keyword.
- **Never tag staging or music** (`[music]`, `[standing]`), and never tag sensitive topics such as grief, illness or tragedy.

## A/B priority

Test credits are often limited. Spend them in this order; the linter's A/B PLAN lists the lines the same way, and `--ab-budget N` marks what fits:
1. **The hook.** It decides the watch. Test two variants: a tag against none, or two wordings.
2. **The first use of each risky tag**: whisper, sigh, laugh, sarcasm, gasp. A tag you have already tested on this voice goes lower.
3. **Unconfirmed readings** (Persian): test the word alone, which costs about 15 characters.
4. **The lift after a low tag**: the line after a whisper or sigh, with `--prev` set to the low line. Does the voice come back up?
5. **The CTA**, unless the person already approved it word for word.

When a line does not fit, shorten the clip to the risky words alone; `--prev`/`--next` give the context and are not spoken. Never skip a level-1 or level-2 item to test a lower one. Tell the person what was not tested.

## Viral arc

For a 60–90 s vertical video:

| Time | Beat | Energy | Typical device |
| --- | --- | --- | --- |
| 0–3 s | HOOK | 5 | Urgency or curiosity in the first words: an interjection, a bold claim, a question, `[gasps]` or `[excited]`. No greeting. |
| 3–10 s | SETUP | 4 | Why it matters now: a deadline, or what they lose if they skip it. Short and fast. |
| every 8–12 s | INTERRUPT | ± | A change of delivery: a whisper, a sigh, a chuckle, a «...» pause, a rhetorical question. |
| list | ITEM | 4 | A punchy numbered title, then one line of reason. Don't tag every item, and vary the openers. |
| ~70% | TIP | 3, intimate | `[whispers]` plus "here's the trick...", then back up. Lower energy here reads as a secret and lifts retention. |
| end | CTA | 4, warm | Clear and friendly, with the keyword said unhurried. A smile in the voice; one light tag at most. |

For long-form narration (an audiobook, an explainer), halve the tag budget and drop the pattern-interrupt rule. Let the text carry it.

## Settings (ElevenLabs)

- **eleven_v4** is ElevenLabs' recommended model. It reads only `stability` and `similarity_boost`; its help page says **Style and Speed are not available**. A test on 2026-11-03 confirmed this: speed 0.8 and 1.2 gave clips of 6.32 s and 6.40 s. Set the pace with short sentences and fewer commas, then `atempo`.
- **Stability:** lower means more expressive delivery and closer tag-following, but takes vary more from one to the next.
  - 0.3–0.4: hype reels.
  - 0.5: neutral narration.
  - Above 0.7: tags are followed weakly.
  - Below about 0.25: takes can wobble, so A/B first.
- **eleven_v3:** the same tags work. The ElevenLabs UI names three stability presets: Creative (low), Natural (0.5) and Robust (high, follows tags weakly). If the API rejects a value, use 0.0, 0.5 or 1.0.
- **No SSML on v3/v4.** `<break>` is not supported. Use «...» or «—» for pauses, «،»/«,» for a breath, and `[short pause]` when punctuation is not enough.
- **multilingual_v2, flash, turbo:** these read `[tags]` aloud, so strip every tag. Steer with `style` (0–1), `speed` (0.7–1.2) and `<break time="0.5s"/>` (3 s at most, and only a few).
- **Chunks:** when you generate part of a script, send `previous_text`/`next_text` so the energy and intonation join up. That context is not spoken.
- **Seed:** `seed` makes sampling close to repeatable, though not guaranteed. Fix it for A/B tests.

## Other TTS engines

Convert the directed script into whatever the engine accepts:
- **OpenAI `gpt-4o-mini-tts`:** no inline tags, so remove them. Put the delivery into the `instructions` field, for example: "energetic young narrator, fast, smiling, one short laugh after the joke".
- **Azure or Google SSML:** use `<break>`, `<prosody rate pitch>` and `<emphasis>`. Use Azure's `<mstts:express-as style>` only on voices that list that style; check the voice's style list first.
- **Prompt-driven engines** (e.g. Gemini TTS): a natural-language style prompt plus the clean text.

Whatever the engine, the step 2 rewrite does most of the work.

## Calibrate for a new voice

Tag behaviour and speaking rate depend on the voice. Once per voice:
- Run `tag_lint.py SCRIPT --calibrate AUDIO.mp3`. It measures the voice's real characters per second from one finished take, for free. Pass that number as `--cps` from then on.
- A/B the tags you plan to use with `ab.py`. Record what works in the tested-voices table in `references/audio-tags.md`.

## Files

| Path | What |
| --- | --- |
| `references/persian-delivery.md` | Persian for the ear: colloquial register, interjections, punctuation as a score, emphasis without capitals, before/after examples |
| `references/english-delivery.md` | The same for English |
| `references/audio-tags.md` | Tag catalogue by job, tested-voices table, what never to tag |
| `references/fa-traps.tsv` | Persian words spelled unlike they sound (Arabic «ال», final «ی» said «ا»); the reading checks warn on them |
| `scripts/tag_lint.py` | Free checker: required beat labels and arc, ear-rewrite rules, tags, model errors, Persian readings, A/B plan, `--approve` / `--check-approved`, `--calibrate` |
| `scripts/ab.py` | Variants × stability on the real voice with a fixed seed, STT leak and event detection, `LISTEN FOR`, `--dry-run`, `--lexicon` |
| `scripts/reading.py` | Shared lexicon loading (✓ = confirmed by ear), respelling and the Persian reading checks |
| `examples/` | A directed Persian and English reel script, with beat labels |
