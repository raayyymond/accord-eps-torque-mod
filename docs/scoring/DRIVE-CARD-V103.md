# DRIVE CARD — V103

**Read the box. The rest is why.**

> ## 🛑 STOP THE MOMENT YOU FEEL IT. That rule beats everything below.
>
> **① FIRST — ordinary driving, HANDS RESTING, NOT GRIPPING.** Engaged, **20–50 mph (30–85 km/h)**,
> let it steer. **Need ≥ 80 s. Aim for ~100 s.** **This is the whole endpoint. If you stop right
> after this, the drive succeeded.**
>
> 🛑 **MOTORWAY DOES NOT COUNT. Above ~53 mph (85 km/h) this measurement stops working entirely.**
> A steady motorway cruise feels like the most data and is the **worst** road for it.
> **An arterial or A-road at 40–50 mph is the ideal.**
>
> ⏱ **Either ~2 minutes deliberately held in that speed band, or ~7 minutes of your usual mixed
> engaged driving.** One drive is enough — you have already done it twice without trying (stock gave
> 268 s, V102 gave 152 s). **But 40 s is NOT enough and would license nothing**, so don't cut it short.
>
> 🛑 **The two things that could cost you the drive are SPEED and HANDS, not time.** Resting hands
> are fine; *gripping* is not. V102 was 5 % gripped and stock 14 % — both fine. V101 was 40 % and
> would have been marginal.
>
> **② THEN — ~100 s on a road that keeps the system WORKING.** Same 20–50 mph, **same hands
> resting.** A long steady curve, a winding A-road, or holding a lane that keeps it correcting —
> **anything but a straight motorway.** ① gave us the *easy* case; this gives us the *hard* one.
> ⚠ **A curve tempts you to hold the wheel. Don't** — gripping voids both ① and ②.
>
> **③ THEN — the grip test, ~20–30 s.** Straight road, **steady speed in the SAME 20–50 mph band,
> no lane changes, no curves.** Alternately **squeeze and release** the wheel — moderate pressure,
> the kind that used to make the buzz go away — **without steering.** Roughly 5 s on, 5 s off, three
> times. **Skip this if the symptom is already bothering you; ① is the one that matters.**
>
> **④ Anything else is a bonus.** Normal driving, any speed.

---

## WHAT V103 IS — read this before you drive it

**V103 = V102 (6× gain, unchanged) + Honda's own dormant filter switched on while engaged
(4 bytes) + a measurement probe.**

🛑 **DO NOT EXPECT A FIX. You are mostly flying an instrument.** The filter is safe and it is
Honda's own, but it is **small — at the most generous estimate it closes about 10 % of the gap we
are trying to close, and at a realistic one, very little.** The probe is the part that unblocks the
next build. **If the grinding feels the same as V102, that is the expected outcome, not a failure.**

**The gain is NOT changing.** V103 is 6×, exactly as V102 was.

### 🛑 OUR PREDICTION, WRITTEN DOWN BEFORE YOU DRIVE

What we measure is **the crossing** — the frequency below which the steering damps itself and above
which it feeds itself. **Lower is better.**

| | 1× stock | 4× | **6× (V102)** |
|---|---|---|---|
| the crossing | **21.9 Hz** | **23.6 Hz** | **24.9 Hz** |

**Every step up in torque pushes the crossing higher, dragging more of the buzz band into the bad
half.** That is why 6× still grinds when 4× mostly did not — **the vibration is not a ramp you can
trade against a bit of torque; it is a threshold, and you are past it.**

> **We predict V103 moves the crossing by 0.06–0.3 Hz. We can only detect about 1 Hz.**
> ⇒ **We are predicting, in advance, that we will NOT be able to see it.** We are writing that down
> so the result cannot be dressed up afterwards. **If it comes back unchanged, that is exactly what
> we expected.**

🛑 **And there is a second problem we only just found — which is what item ② is for.** The crossing
**also moves with how hard the system is working**, by about **1 Hz** across the range you normally
drive — **the same size as the entire effect we are hunting.** So a change we see could just be that
you drove a different road. **② gives us the hard-working case to compare against ①'s easy one, so
we can separate the two.** Without it, one drive cannot tell them apart.

**⇒ The probe is the deliverable. The filter is a long shot and we are telling you so up front.**

---

## WHAT EACH ITEM IS FOR

### ① Hands-off cruise at 20–50 mph — **the pre-registered endpoint**
> **Does the crossing move back down toward stock?**
> Stock sits at **21.9 Hz**, V102 at **24.9 Hz**. Lower is better. V103 asks whether Honda's filter
> pulls it back down.

It has to be **hands-off** because that is the state the measurement is defined in, and it has to be
**20–50 mph** because **that is the only speed range where the measurement works at all.** Above
~53 mph the difference between stock and V102 disappears into the noise — both straddle zero — so
motorway miles contribute nothing no matter how many of them there are.

**This is the one counterintuitive thing on the card**, so it is worth being blunt: of V102's 576 s
of engaged driving, only **152 s (26 %)** was usable, because most of the rest was too fast. You
already drive this way naturally; you just need enough of it *below* motorway speed.

### ② The hard-working road — **the amplitude discriminator**
> **Does the crossing move because of the FIRMWARE, or just because the system was working harder?**

`route-stock` found, **inside route 0x96 alone with the firmware and the gain held fixed**, that the
crossing moves **25.68 Hz at low command → 24.69 Hz at high command — −0.99 Hz over a 2.2× range,
disjoint CIs.** And openpilot commands **harder on the weaker car** (median `|0x0E4|`: stock 465 ·
V100 253 · V102 98), so the between-build march and the within-route effect **have the same sign**.
Pooled, **the gain term goes non-significant (+30 [−99, +159], ΔR² = 0.0009).**

⇒ 🛑 **Most of the 21.9 → 24.9 Hz march we have been attributing to the gain cell may be command
amplitude instead.** ① is the low arm; ② is the high arm. **The firmware is identical across both,
so the contrast is clean by construction** — which is why it costs no extra drive.

### 🛑 INSTRUCTION THAT MUST TRAVEL WITH THE SCORER
**Report median `|0x0E4|` alongside `f0`, and report `f0` adjusted for command.**
**An `f0` shift that sits on the amplitude law's own slope (−1.93 Hz per e-fold of command) is NOT
evidence the lever touched the loop.** From V103 onward, an `f0` quoted without its command
covariate is uninterpretable.

### ③ The grip test — a separate question, and it cannot come from ordinary driving
You have told us twice that **applying torque kills the buzz and letting go brings it back.** That
is the single most specific mechanical claim anyone has made about this problem, and **we still
cannot test it**, because in every drive so far you grip the wheel *when you are steering* — and
steering shakes the car by itself. The two are tangled together in every log we have.

**How tangled: your grip correlates with wheel movement at +0.59 to +0.78 on every build.** And the
clean case — gripping while going *straight* — has:

| build | seconds of it |
|---|---|
| **V102** | **0 s** (out of 566 s engaged) |
| V100 | 1 s |
| V101 | 5 s |
| stock | 24 s |

**Zero seconds on V102.** No amount of ordinary driving produces it. **20–30 s done deliberately
gives us the only clean measurement of your own claim that exists.**

🛑 **And without it we would get a confident WRONG answer.** Analysed the naive way, the logs say
driver torque makes the vibration **2–196× worse** — the opposite of what you report. That number is
an artefact: **stock shows the same trend, and stock has no vibration to make worse.** So the naive
reading is measuring "you were steering", not "you were gripping." **Only the straight-line version
separates them.**

---

## IF YOU CAN ONLY DO ONE THING
**① .** The endpoint is the crossing frequency `f0`, from hands-off cruise at 20–50 mph. Everything
else is optional. **If you can do two, do ① then ②** — without ② we may not be able to tell a real
change from a different road.

## IF THE SYMPTOM SHOWS UP
**Stop.** Note roughly the speed and whether your hands were on the wheel. That is worth more than
another minute of driving, and it is the report that outranks every number in this file.
