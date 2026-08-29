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
4. It also restores the configuration in which the ±511 **relay** hazard is *measured* unexercised
   (V76: 0/63,477 frames). At the flown 3.0× that hazard has **never been measured**.

---

## THE DRIVE — ONE PASS

1. **Engaged creep, ONE continuous pass of 15 seconds, 1–24 km/h.** Don't break it up — the analysis
   window is 5.12 s and a broken pass yields too few of them. Real curvature, not a straight line.
2. **Then the same again with LKAS OFF**, same speeds, same road if you can. **This second pass is
   what makes the build interpretable** — see the discriminator below. 15 s is enough.
3. Stop the moment you have both. If the ratcheting is obviously still there, stop and say so; there
   is no point continuing a drive whose single question is already answered.

```
python rlog-tools/score/score_band_excess.py <route-tag>
python rlog-tools/score/grind_engaged_vs_manual.py <route-tag>
```

---

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
