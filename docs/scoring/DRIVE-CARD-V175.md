# DRIVE CARD — V175  ·  **FLY THIS ONE FIRST**

> 🛑 **FLIGHT ORDER CHANGED AGAIN 2026-08-29: FLY **V177** FIRST.**
> V177 = this build + **one** more cell: `0xC40D2` K1 **1020 -> 102** (Honda's). K1 is a **sign
> function of motor velocity**, so at 10x Honda it injects a **1.99x|model| STEP at every reversal**
> — ~16 times a second at 8 Hz. That is a **relay**, V80's failure mode in another lane, and it is
> the strongest mechanism-to-symptom match found this session. It also acts in **manual AND engaged**
> (a bare `tp` scalar, RULE 7), which gives the drive a second independent signature.
> Card: `docs/scoring/DRIVE-CARD-V177.md`.


**Supersedes `DRIVE-CARD-V173.md` as fly-first.** V175 *contains* V173 — same poles, same notch, plus
a 12-byte revert. There is no reason to fly V173 by itself.

```
image  a4e0dc4254ad8559e0c7744277cbe609d3c4c7da90284bc145d035a0816ae357
rwd    5bf63d0ea539fd18f3966243fabd257e65c72e711d02af7f1c287fb282a9171f
file   39990-TVA,A160-V175-V173BASE-GP6B26.ENGAGED.Y.REVERT.HONDA-0x13000-0x100000.rwd
```

🛑 **Nothing is flashed without you naming the file and the bus, and me repeating them back.**
🛑 **Kill openpilot/pandad first** (`tmux kill-server` on the comma device).

---

## WHY THIS ONE, IN FOUR LINES

1. The assist section's poles are retuned (V173) — **grind 15–25 Hz −12.6 dB**, ratchet −5.9 dB,
   LKAS magnitude intact, cost +29 ms of group delay at 1 Hz.
2. **New**: the engaged apparent-inertia dose goes back to Honda's row. We had been amplifying a
   **destabilising, ω²-weighted** term by **3.0/3.0/8.14×** — **on the engaged modes only**, which is
   exactly where the ratchet is amplified ~15×.
3. That term is `K × acceleration`, so it is **66.7× stronger at 8.17 Hz than at 1 Hz** with **no
   filter and no added phase** — the first genuinely frequency-selective handle the kit has found.
4. That term is **highly intermittent** — measured on route `77` at Honda's K, p50 ≈ 18 counts but
   **p99 = 408 against its 511 clamp** at the flown 3× — so it is negligible in steady driving and
   large **exactly in the fast transients where the ratchet lives**.
   ⚠ *An earlier draft of this card claimed a ±511 "relay hazard". Measured, it clips only **0.49 %**
   of engaged frames at 3× — rare tail clipping, not V80's relay. That argument is withdrawn.*

---

## THE DRIVE — STAGED, SO YOU NEVER DRIVE MORE THAN THE ANSWER NEEDS

🛑 **Power-checked against the corpus before writing this.** Stage 1 answers the only question
that matters first. **Stage 2 exists solely to attribute a win, so it is only worth driving if there
IS a win** — which is exactly your rule: if the ratcheting is still there, stop instantly.

**STAGE 1 — do this and nothing else.**
1. **TWO passes of engaged creep, 15 s each, 1–24 km/h, real curvature. About 30 s total.**
   **1a — drive it HOW YOU NORMALLY DO** (hands off, or resting). This is the pass that can be
   **scored today**: the whole 27-window historical baseline is hands-off, so this is the only
   pass comparable to it, and the card's thresholds below apply to it.
   **1b — the same again with HANDS ON THE WHEEL.** This answers the confound that `cs_tq` is
   the DRIVER torque sensor, and builds the first hands-on baseline the kit has.
   🛑 **Honest limit on 1b: its detection thresholds are UNKNOWN.** The corpus contains
   **ZERO** continuous 15 s hands-on engaged creep windows, so nothing can be promised about
   what it resolves — it is a baseline-building pass, not a scored one.
   Don't break either pass up — the analysis window is 5.12 s.
2. **Stop.** If the ratcheting is obviously still there, say so and we are done for this build.

✅ **Stage 1 is adequately powered for the primary question.** The ratchet endpoint is
presence/absence, an ~8x move, and a single 15 s engaged window resolves it (11/11 on the corpus).

**STAGE 2 — ONLY if Stage 1 shows the ratcheting gone or clearly reduced.**
3. **Three more short passes, alternating engaged / LKAS-off**, same speeds and same road: roughly
   15 s each, so about 90 s of driving total. This is what tells us **which lever did it**.

⚠ **Why three and not one.** A single engaged + manual pair can only resolve a change larger than
**6.6x** in the engaged/manual ratio (single-pair ratio p50 10.5, 95 % band [1.33, 56.5], log10
sd 0.418). **V175's predicted move is well under that**, so one pair would be uninterpretable for
attribution. Three matched pairs bring the detectable change to **2.97x**; four to 2.57x.
🛑 **This is a limit of our instrument, not of your driving** — it is stated here rather than
discovered afterwards.

```
python rlog-tools/score/score_band_excess.py <route-tag>
python rlog-tools/score/grind_engaged_vs_manual.py <route-tag>
```

---

## 🛑 WHAT ONE STAGE-1 PASS CAN AND CANNOT ANSWER

Power-checked against 27 real 15 s engaged creep windows. **An endpoint marked NOT answerable will
produce a null that means nothing — I will not report one as evidence.**

| endpoint | detectable @ 1 pass | V175 predicts | verdict |
|---|---|---|---|
| **GRIND 15–25 Hz** | 5.96× | **0.058× (a 17× cut)** | ✅ **answerable**, margin 2.9× |
| **lane-change 26–31 Hz** | 2.04× | 0.029× | ✅ **answerable**, margin 17× |
| **ratcheting — is it THERE?** | presence/absence, ~8× | gone or not | ✅ **answerable** (and your report settles it) |
| ratchet 6.5–11 Hz, *how much* it fell | 4.47× | 0.260× | ⚠ margin 0.86× — needs **2** passes |
| LKAS band 0.5–3 Hz | **19.2×** | 0.846× | ❌ needs **54** passes — **not measurable here** |

🛑 **On LKAS authority — a correction to an earlier draft of this card.** I wrote that the drive
would show authority unchanged. **It cannot.** One pass bounds an LKAS-band change only to within
**19×**, so a measured null there is worthless. That authority is intact is an **ANALYTIC** claim
from the section's transfer function (−0.05 to −1.42 dB across 0.5–3 Hz) — **your seat-of-the-pants
report is the better instrument**, and it is the one I will use.

✅ **The upshot is good**: Stage 1's biggest predicted win (the grind, a 17× cut) is comfortably the
best-powered endpoint on the card. If the grinding does not measurably fall on one pass, the
pole-retune account is in trouble — and that is a real, pre-registered way for this build to fail.


## THE DISCRIMINATOR — ENGAGED vs MANUAL

V173's poles and V175's revert **both** attenuate the ratchet, so amplitude alone cannot say which
worked. But **V173's poles act in both modes, and the revert cannot act in manual at all.**

| what you see | what it means |
|---|---|
| ratchet falls **and** the engaged/manual ratio falls | **the inertia dose was carrying it** — our own doing, and V175 is the fix |
| ratchet falls, ratio **unchanged** | V173's poles did it; the inertia account is wrong |
| ratchet **unchanged**, ratio unchanged | both accounts fail together — the lever is outside this loop |
| ratchet **rises** | the polarity chain is inverted somewhere; revert and re-derive before anything else |

---

## WHAT TO EXPECT IN THE SEAT

- ⚠ **Creep will feel LIGHTER.** The revert removes drag we had added. This is intended. If it feels
  *too* light or nervous, say so — that is a real result, not a complaint.
- Steering will feel slightly **laggier at low frequency** than stock (+29 ms at 1 Hz, from V173's
  poles). You may not notice it; if you do, say so, because the next build's size depends on it.
- **LKAS authority should feel unchanged** — the section's magnitude is intact to within
  1.4 dB across 0.5–3 Hz. 🛑 **This drive CANNOT measure that** (see the table above: one
  pass bounds it only to 19×), so **your impression is the instrument here.** If the car
  feels like it is not pulling as hard in a lane, say so — that would be the only signal
  we get.

🛑 **Score bands are mine; symptoms are yours.** I will not call anything fixed that you have not.

---

## IF IT IS BETTER BUT NOT GONE

Two pre-registered next steps, in order:

1. **`0xC63A6` (`w[3]`)** — the weight on the same inertia lane, **virgin, and un-struck on 2026-08-29**
   once its blocking condition (an unknown LERP slope) was met. It multiplies the same quantity the
   revert just cut, so it is the fine adjustment. Cheapest, most targeted, no lag cost.
2. **V174** — the slow pole 0.970 → 0.980: −2.9 dB more ratchet and −3.4 dB more grind for **+14 ms
   more lag**. Built and on the shelf (`c3d6776cc72d4657…`).
   🛑 **Do not cut past `p_slow` = 0.985 without a lag verdict from you.**

## IF IT IS WORSE

Revert to the currently-flying build and tell me which symptom worsened. A *rise* in the ratchet
falsifies the polarity chain and would be the most informative result of the session.
