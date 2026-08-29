# DRIVE CARD — V175  ·  **FLY THIS ONE FIRST**

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
1. **Engaged creep, ONE continuous pass of 15 seconds, 1–24 km/h**, real curvature, not a straight
   line. Don't break it up — the analysis window is 5.12 s.
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
- **LKAS authority should be unchanged.** Its magnitude is intact to within 1.4 dB. If the car feels
  like it is not pulling as hard in a lane, that is unexpected and worth reporting.

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
