# Audio tags (ElevenLabs v3 / v4)

A tag is an English phrase in square brackets, placed right before the words it colours. Only eleven_v3 and eleven_v4 perform tags instead of reading them aloud. A tag's effect lasts to about the end of the sentence. How well a tag works depends on the voice: a calm narrator may ignore `[shouting]`. A/B any new tag with `scripts/ab.py` before relying on it.

If your pipeline also makes captions or word timings, strip the `[tags]` from the caption text. Tags are performed, never shown.

## Catalogue by job

| Job in the video | Tags | Notes |
| --- | --- | --- |
| Hook, big reveal | `[excited]`, `[gasps]`, `[amazed]`, `[surprised]` | One on the hook, one on the biggest reveal. |
| Secret or insider tip | `[whispers]`, `[mischievously]`, `[conspiratorial]` | Bring the energy back up on the next line. |
| Irony, playful jab | `[sarcastic]`, `[teasing]`, `[playfully]`, `[chuckles]` | Use with an ironic sentence. A tag cannot make plain text ironic. |
| Joke landing, self-aware aside | `[chuckles]` (light), `[laughs]` (clear), `[laughs harder]` (once) | 0–2 laughs per reel, at least 20 s apart. |
| Pain point, long wait | `[sighs]`, `[frustrated]`, `[exhales]` | A good pattern interrupt before the solution. |
| Urgency, call to act | `[shouting]` (sparingly), `[hyped]`, `[rushed]` | Shouting tires the listener fast: one line at most. |
| Calm authority, trust | `[confident]`, `[matter-of-fact]`, `[warmly]` | Good before a CTA. |
| Thinking out loud | `[curious]`, `[thoughtful]` | Use before a rhetorical question. |
| Pause | `[short pause]`, `[long pause]` | Prefer «...» or «—». Use these when punctuation is not enough. |
| Sound effects | `[applause]`, `[clapping]`, `[explosion]` | Avoid in voiceovers. Add real SFX in the edit. |

Descriptive tags work too, and are less ambiguous than single words: `[low, excited voice]`, `[smiling]`, `[barely holding back a laugh]`. A one-word tag that could be a sound, such as `[boom]`, may be played as a sound effect.

Write tags in English even when the script is in another language. The models were trained on English tags. A Persian tag such as `[با هیجان]` was not read aloud in testing, but its effect was unclear.

## Tested voices

Speech-to-text only proves two things: that a tag was not read aloud, and that a non-verbal sound happened. Whether a line sounds excited, whispered or sarcastic has to be judged by ear. Add a row for each voice you calibrate.

| Voice (model, language, date) | Performed (STT heard the event) | Not read aloud, effect to judge by ear | Speaking rate |
| --- | --- | --- | --- |
| Persian female library voice "Mitra" `01Hje9fLgarTAqnLKNEK` (eleven_v4, fa, 2026-11-03) | `[laughs]`, `[laughs harder]`, `[chuckles]`, `[gasps]`, `[sighs]` | `[excited]`, `[whispers]`, `[shouting]`, `[sarcastic]`, `[با هیجان]` | 9.6 chars/s including pauses (from a 90 s take) |

## Never

- `[music]`, `[intro]`, staging such as `[standing]`, or sound effects used in place of real SFX.
- Three tags stacked at one spot.
- The same tag on consecutive lines.
- Tags on `multilingual_v2`, flash or turbo. Those models read them aloud.
- SSML (`<break>`) on v3/v4. It is not supported there.
