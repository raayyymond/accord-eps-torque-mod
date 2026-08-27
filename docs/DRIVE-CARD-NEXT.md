# DRIVE CARD — the next drive, whichever build you flash

**One page. Written 2026-08-27 for V108 / V109 / V110.** Six analyses failed on this corpus for lack of
one thing each, and every one of those gaps closes with a manoeuvre that costs under a minute. This card
is those manoeuvres.

🛑 **You do not have to do all of it.** In priority order — if you only do #1, the drive is still worth
flying. If you only do #1 and #2, three separate open questions close.

---

## 0. BEFORE YOU MOVE — 30 seconds, and it unlocks the whole acoustic channel

**Parked, engine ON, LKAS off, HVAC off, windows up. Sit still for 30 seconds.**

Why: the cabin's acoustic gain differs **3–12× between drives** — mic position, HVAC, windows, ambient.
That single fact is why *"no audible band separates stock from 6×"* is **not a real null**: the
between-drive comparison it rests on is **structurally uncomputable**. Thirty parked seconds is a
per-drive reference clip that makes every future acoustic number comparable, retroactively.

---

## 1. ⭐ THE PRIMARY READOUT — your own words, per scenario

**This outranks every measurement on this card.** After the drive, tell me for each of:

| scenario | what I need |
|---|---|
| **~5 mph / creep** | grinding? ratcheting? |
| **15–40 mph** | the higher-pitched grinding — gone, quieter, same, worse? |
| **hard turn at ~50 mph** | does it come back? |
| **highway straight** | anything? |
| **after you disengage** | does anything persist, and for roughly how long? |

Use your own words — grinding, vibrating, micro-ratcheting, ratcheting, excess friction. **Do not try to
map them onto frequencies.** *"I didn't notice anything odd"* is weak evidence and I will report it as
such, so a plain "no change" is genuinely useful.

🛑 **Stop the drive the moment you've answered these.** You said it yourself and you were right: there is
no point continuing a drive once the thing you were testing for has failed. **15–30 seconds of engaged,
symptomatic driving is enough** — every build since V107 has been designed against that budget.

---

## 2. ⭐⭐ THE ALTERNATING SEGMENT — open since V105, and it closes THREE analyses

**On one straight, quiet road at 5–15 mph, alternate: ~30 s engaged, ~30 s manual, repeat 3–4 times.**
Vary your LKAS demand between them — some gentle, some pushing hard into a correction.

What it closes:
- the **~8 Hz ratcheting** null — route `a6` had only 7 engaged episodes, one of them 941 s long, and
  many short runs beat one long one;
- the **pitch-vs-amplitude** cell at <16 mph, which failed on exposure (30 and 46 windows);
- the **engaged-vs-manual** contrast above 15 mph — the last drive had **0.0 s** of manual driving
  between 15 and 37 mph, which is what defeated two separate results.

---

## 3. ⭐ DISENGAGE AT CONSTANT SPEED — the newest requirement, and the cheapest

**Three or four times: while rolling at a steady speed, disengage and then HOLD THE THROTTLE STEADY for
about 15 seconds. Do not slow down, do not speed up, do not steer more than you were.**

Why this is new: last drive you disengaged three times and **changed speed on every one** (−13.6, −6.1,
**+10.7** km/h). That's completely natural driving — and it made the post-disengage measurement
unrecoverable, because the acoustic level just tracks the speed change at ~0.19 dB/km/h. Two of the
three even moved in *opposite* directions.

What it closes: whether the grinding really outlives disengagement, and for how long. Firmware says the
engaged mode records are held **~2.05 s** after you let go — during which V106/V107's dosed damper is
still in force with **no LKAS command at all**. That window is very nearly a controlled experiment on our
own lever, and right now it's the only one available.

---

## 4. IF THE VISIBLE OSCILLATION HAPPENS — mark it

**Press the horn, or say the time out loud, the moment you see the wheel weaving.**

Why: it is **real** — 46 events on the last drive, up to **78 mm at the rim** — but it lives at
**0.4–1.3 Hz**, not the 4–10 Hz everyone had been searching, and its command *leads* your steering,
which points at openpilot's lateral loop rather than the firmware. **One marked instant turns every
future analysis of it from a search into a measurement.**

---

## 5. WHAT I'D LIKE, BUT ONLY IF IT'S SAFE AND CONVENIENT

- **Matched manual at 30–50 mph** on the same road as an engaged stretch. The last drive had **35.8 s
  total** of manual above 15 mph, and that is what caps the confidence on the openpilot-weave finding.
- **Some highway above 45 mph, engaged.** The `≥70 km/h` clamp duty has been asked for twice and answered
  never — it was **unanswerable by construction** until V108's telemetry fix, and V108 fixes it.
- **A couple of deliberate hard turns at 45–55 mph**, since that is where you say the grinding returns.

---

## WHAT NOT TO WORRY ABOUT

- **Don't chase exposure.** Long drives have not helped this project; matched, alternating, short ones
  have. 20 minutes with the manoeuvres above beats an hour without them.
- **Don't try to reproduce a symptom you don't feel.** A clean "it wasn't there" is a result.
- **Don't change anything on the openpilot side.** It is the measurement instrument; if it changes, the
  comparison to previous drives breaks. ⚠ The device was reflashed before the last drive and the route
  counter reset — that was checked and the tuning was unchanged, but it cost real time to verify.

---

## AFTER THE DRIVE

Copy the rlogs off the device and tell me. **Do not delete anything** — routes `1b` and `1e` are still
the only drives that have ever carried the `gp-0x6c2c` telemetry, and the whole rail-duty result rests
on them.
