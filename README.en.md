<p align="center"><img src="assets/banner.jpg" alt="tts-director: a microphone, a clapperboard and a waveform tagged [laughs], [whispers], [excited]" width="100%"></p>

# tts-director

**English** · [فارسی](README.md)

**An agent skill that directs scripts for text-to-speech so they sound like a real, engaged human, not a narrator reading.** It is built Persian (Farsi) first and supports English. It targets ElevenLabs v3/v4 audio tags and also covers other TTS engines.

Most TTS scripts fail in one of two ways. They are written as text, so the voice sounds read. Or they are over-tagged, with `[excited]` on every line, so they sound like an over-acted ad. tts-director:

1. Maps the beats of the video: hook, setup, list items, insider tip, joke, CTA.
2. Rewrites the script for the ear, keeping every fact. That means spoken register, short sentences, the punch word last, and real interjections.
3. Adds audio tags only where they earn their place, within a strict budget:
   - about 1 tag per 3–4 sentences;
   - 0–2 natural laughs per reel;
   - a change of delivery every 8–12 s.
4. Lints the result for free, to catch over-tagging, mistakes for the chosen model, written "haha", and openings with a greeting.
5. A/B-tests the risky lines on your real voice before you spend credits on the full script. It uses a fixed seed and a `--dry-run` cost check, and STT shows whether a tag was performed or read aloud.

It works with [Claude Code](https://claude.com/claude-code) and any agent that reads `SKILL.md` skills. The scripts are plain Python 3.9+ with no dependencies; ffmpeg is optional.

## Install

Claude Code (personal skill):

```bash
git clone https://github.com/aligh98/tts-director ~/.claude/skills/tts-director
```

Or clone it into a project's `.claude/skills/`. The skill triggers whenever a script is headed to a TTS engine, or when you ask for a more expressive or human-sounding voice.

## Use the scripts directly

```bash
# Free: beat map, length estimate, over-tagging and model errors
python scripts/tag_lint.py examples/reel-fa.txt --model eleven_v4 --tempo 1.15

# Free: measure your voice's real speaking rate from one finished take
python scripts/tag_lint.py script.txt --calibrate voice.mp3

# Check the cost first (sends nothing)
python scripts/ab.py "[excited] Okay, this ends FRIDAY!" "Okay... this ends Friday!" --stability 0.35 --stability 0.5 --out probe --dry-run

# Generate and transcribe each variant (uses ElevenLabs credits)
export ELEVENLABS_API_KEY=...        # or put it in a .env in this folder or any parent
python scripts/ab.py "[excited] Okay, this ends FRIDAY!" "Okay... this ends Friday!" --voice YOUR_VOICE_ID --lang en --out probe
```

`ab.py` options:
- `--prev` / `--next`: the neighbouring lines, sent as context.
- `--lexicon words.tsv`: respellings in the form `written<TAB>spoken`, for brand names and loanwords.
- `--en-check`: also transcribe as English, to catch an English tag leaking into a non-English script.

Run the offline tests with `python -m unittest discover tests`.

## Key findings baked in

- `eleven_v4` ignores `speed` and `style`; only `stability` and `similarity_boost` apply. Set the pace with `ffmpeg -af atempo=1.1` after generation.
- `multilingual_v2`, flash and turbo read `[tags]` aloud. v3/v4 do not support SSML `<break>`.
- Write tags in English, even in a Persian script.
- STT can prove that a laugh was performed. It cannot prove that a line sounds excited, so the final judge is a human ear.

## Contribute

The most useful contribution is a row in the tested-voices table in `references/audio-tags.md`. Each row covers one voice, model and language: which tags were performed, which were ignored, and the voice's speaking rate. More languages are welcome as `references/<language>-delivery.md`.

## License

MIT. This is not affiliated with ElevenLabs; "ElevenLabs" is a trademark of its owner.
