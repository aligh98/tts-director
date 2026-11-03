---
name: tts-director
description: Direct a script for text-to-speech so it sounds like a real, engaged human, not a narrator reading. Persian (Farsi) first, English supported. It rewrites the text for the ear, maps the beats of a short-form video (reel, TikTok, Short), and adds ElevenLabs v3/v4 audio tags only where they earn their place ([excited], [whispers], [laughs], [chuckles], [gasps], [sighs], [sarcastic]...). It checks for over-tagging with a free linter and A/B-tests risky lines on the real voice before a full run. It also covers model rules (eleven_v4 ignores speed and style; multilingual_v2, flash and turbo read tags aloud) and converts the result for other TTS engines (OpenAI, Azure, Google). Use for ANY script headed to ElevenLabs or another TTS, and whenever someone wants a voice that is more exciting, emotional, expressive, human or viral, or asks about tone, emotion, laughter, pauses or pacing in TTS: «لحن»، «احساس»، «هیجان»، «خنده»، «تگ»، «انسانی‌تر»، «گوینده»، «صداگذاری».
---

# TTS director: write for the ear, tag the beats, test by ear

A great voiceover is about 80% text and 20% tags. The text sets the rhythm, the register and where the energy goes. Tags only push a delivery the text has already set up. A script with a tag on every line sounds like an over-acted ad and loses the viewer. A script with none often sounds read.

This skill does not replace your TTS pipeline. It prepares the text that goes into it. Scripts are stdlib Python 3.9+; ffmpeg/ffprobe are optional and give durations.

## Workflow

1. **Beat map.** Label every line with its role and a target energy from 1 to 5. The roles are:
   - HOOK
   - SETUP
   - REVEAL
   - ITEM (a list point)
   - TIP (insider advice)
   - JOKE or IRONY
   - WARNING
   - CTA

   Plan the arc before touching words. See [Viral arc](#viral-arc).
2. **Rewrite for the ear.** For Persian use `references/persian-delivery.md`; for English, `references/english-delivery.md`. Keep the meaning and every fact. Rewriting means:
   - shorter sentences;
   - the punch word moved to the end;
   - the interjections a native speaker would actually use;
   - punctuation that marks breaths.

   Show the text to the person before generating anything. Generating audio costs them credits, and the wording is theirs to approve.
3. **Tag pass.** Tag only the beats the text alone cannot carry, within the [Tag budget](#tag-budget). For tag names and what each one is for, see `references/audio-tags.md`.
4. **Lint (free):**
   ```
   python scripts/tag_lint.py SCRIPT --model eleven_v4 --tempo 1.15
   ```
   It prints a beat map with estimated times. It flags:
   - over-tagging;
   - laughs that are too many or too close together;
   - a repeated tag;
   - «!» on every line, and too many ellipses;
   - long sentences;
   - written laughter («هاها», "haha");
   - an opening greeting;
   - SSML on v3/v4, and tags on models that read them aloud.

   Fix every ERROR. Keep a WARN only when you can say why.
5. **A/B the risky lines.** These are the hook, every laugh, any whisper or sarcasm, and the CTA. Check the cost first; `--dry-run` sends nothing:
   ```
   python scripts/ab.py "VARIANT A" "VARIANT B" --voice VOICE_ID --stability 0.35 --stability 0.5 --prev "line before" --next "line after" --out probe/ab --dry-run
   ```
   Remove `--dry-run` to generate. Every clip uses the same `--seed`, so the differences come from the text and the settings, not from chance. Each clip is transcribed:
   - `LEAK` means a tag was read aloud as a word. Drop or rephrase that tag.
   - An event such as `[laughter]` or `[خنده]` means the sound was performed.

   Speech-to-text cannot judge excitement, so let a human ear pick the winner.
6. **Generate the full script** with the chosen variants and settings. Then:
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
| `scripts/tag_lint.py` | Free checker: beat map, length estimate, over-tagging and model errors, `--calibrate` |
| `scripts/ab.py` | Variants × stability on the real voice with a fixed seed, STT leak and event detection, `--dry-run`, `--lexicon` |
| `examples/` | A directed Persian and English reel script |
