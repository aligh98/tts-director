# Persian for the ear

TTS reads exactly what it is given. Written Persian («بنابراین لازم است...») comes out sounding like a news anchor. A reel needs the voice of a friend who just found something cool. These rules turn a script into that voice without changing its facts.

## 1. Register: spoken Tehrani, spelled as said

- Write the colloquial forms, so the model has no formal spelling to fall back on:

  | Write | Not |
  | --- | --- |
  | می‌خوای | می‌خواهی |
  | نمیشه | نمی‌شود |
  | اینو | این را |
  | واسه | برای |
  | خونه | خانه |
  | گوشیتو | گوشی‌ات را |

- Add vowel marks (َ ِ ُ ْ) only where a word could be read two ways, and on every loanword or brand name the model might misread: «اَپْ»، «آپْدِیْتْ». A sukun on the final consonant and on «ی» in diphthongs («رِیْج»، «فِیْل») stops the model from stretching vowels. To keep captions clean, give the TTS the marked text and show the unmarked text on screen.
- Use the second person and speak to the viewer directly: «تو»، «گوشیت»، «پولت». Never «کاربران گرامی».

## 2. Sentence shape

- **8–14 words per sentence.** The linter warns above 22. A long sentence makes the voice go flat to get through it.
- **Put the punch word at the end.** «این گوشی نصف قیمته!» hits harder than «نصف قیمت بودن این گوشی».
- **Let a punch stand alone.** «دوم: باتری!» works as a whole line. A short line after a long one is the easiest emphasis there is.
- **Use a rhetorical question for a pattern interrupt.** «می‌دونی چرا؟» or «حالا چی کار کنیم؟» makes the voice rise, then the answer lands.
- **Give lists a rhythm:** a numbered title, one reason, then the next item. Vary the openers: «اول از همه»، «دوم»، «بعدی»، «و آخر از همه».

## 3. Interjections: the most human thing you can add

One natural interjection does more than an `[excited]` tag. Use 2–4 per reel, and never repeat one.

| Want | Use |
| --- | --- |
| Surprise or hype (hook) | «وای!»، «اوه!»، «باورت نمیشه...»، «جدی میگم!» |
| Attention | «ببین!»، «دقت کن!»، «گوش کن!» |
| A casual turn | «خب...»، «راستی...»، «حالا...»، «آها!» |
| Mild complaint | «آخه...»، «اِه!»، «ای بابا» |
| Certainty | «دیگه!» at the end: «اینو که همه می‌دونن دیگه!» |
| Irony | «آره، حتماً...» (pair it with `[sarcastic]` or `[chuckles]`) |

**Never write laughter as letters** («هاها»، «ههه»، «خخخ»). TTS spells it out. Use `[laughs]` or `[chuckles]`.

## 4. Punctuation is the score

| Mark | What the voice does | Rule |
| --- | --- | --- |
| «!» | Lift, energy | Use it at the peaks. On every sentence it flattens; the linter warns above 70%. |
| «؟» | Rising tone | Rhetorical questions are free pattern interrupts. |
| «...» | A pause with weight, a held breath | Put it before a reveal or a twist. Use it at most about once every 3 sentences, or the reel drags. |
| «،» | A short breath | Remove the commas that slow down a hype line. |
| «؛» and «:» | A medium pause | «اول از همه: باتری!» |
| «—» | A clear stop | For a dramatic beat inside a sentence. |

Persian has no capital letters, so emphasis comes from:
- word order, with the key word last;
- a short line on its own;
- repetition: «نصف قیمت، نصف زمان!»;
- an interjection before the word;
- a «...» before it.

Do not stretch letters («وااای»): how TTS reads that varies, so A/B it first if you want it.

## 5. Before and after

Hook:

> فقط تا جمعه فرصت دارید و پس از آن این تخفیف تکرار نخواهد شد.

> [excited] وای! فقط تا جمعه وقت داری... بعدش این تخفیف دیگه تکرار نمیشه!

Tip, lowered for intimacy and then brought back up:

> نکته‌ی مهم این است که شارژ باتری را بین بیست تا هشتاد درصد نگه دارید.

> [whispers] یه نکته‌ی طلایی... باتریتو همیشه بین بیست تا هشتاد نگه دار! خیلی دیرتر خراب میشه.

Light irony with a chuckle:

> نیازی نیست هر شب گوشی را تا صد درصد شارژ کنید.

> [chuckles] لازم نیست هر شب تا صد شارژش کنی که! هشتاد بسه.

CTA, warm and clear, with the keyword said plainly:

> برای دریافت لینک، کلمه‌ی لینک را کامنت کنید.

> واسه گرفتن لینک، فقط بنویس «لینک»... برات می‌فرستیم!

## 6. What not to change

Keep every fact, number, date, name and claim. The rewrite changes how something is said, never what is said. If a sentence cannot sound natural without changing its meaning, keep it and say so.
