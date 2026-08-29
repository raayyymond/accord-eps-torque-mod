# DRIVE CARD — V168

**Flash target:** `39990-TVA,A160-V168-V158BASE-ASSIST.SLOPECAP.2048.TO.1536-0x13000-0x100000.rwd`
**.rwd SHA256** `0f0ace3b5bc0a8541227e06c831c555797566374b298ba606614f5a09a1356f1`
**image SHA256** `058dd64ac442ef43c790965c9a5fc011f147f7ff0a5e7cd0c0d1bb8889c7b0ff`

> 🛑 Nothing here authorises a flash. Name the file and the bus yourself; kill openpilot/pandad
> (`tmux kill-server`) before any flash operation.

---

## V168 SUPERSEDES V158 AS THE FLY-FIRST BUILD

V168 **is** V158 plus one byte. Flying it tests both levers at once, and **the two symptoms are
separated by the INSTRUMENT, not by the build** — they live in different bands of the same episode:

| lever | cell | targets | band | channel |
|---|---|---|---|---|
| V158's damper shape | `0xD77DA`/`0xD780E`/`0xD7818` (+mode 27) | **grinding** | 15–25 Hz | `cs_tq` |
| V168's slope cap | `0xC6384` 2048→1536 | **ratcheting** | 5–12 Hz | `cs_tq` |

Fly V158 alone only if you specifically want the grind lever isolated on feel.

---

## THE DRIVE — ONE CONTINUOUS 15-SECOND PASS IS ENOUGH

✅ **The ratchet endpoint is PRESENCE/ABSENCE, not a ratio.** A single continuous 15 s engaged creep
episode detected the ratchet in **11 of 11 episodes (100 %)** on the existing corpus, at excess
**25.5–155.7** against a slope-matched null of **1.9–4.9** — a **5–65× margin**.

1. **Engaged creep, ONE continuous pass of 15 seconds, 1–24 km/h.** A slow unbroken lap of a car park
   is the natural shape. Do not break it up — the analysis window is 5.12 s and a broken pass yields
   too few windows.
2. **Stop as soon as you know.** If the symptom is still there after one pass, the drive has already
   answered its question. Nothing is gained by continuing.
3. **A matched MANUAL creep pass at the same stretch and speed**, if convenient. Not required for the
   primary verdict — it is the control that makes the engaged/manual contrast readable.
4. Audio if easy. More passes only sharpen the *graded* question (how much smaller), which is
   secondary to *is it fixed*.

**Score with:** `python rlog-tools/score/score_band_excess.py <route-tag>`

---

## PRE-REGISTERED OUTCOMES — all three readable from one pass

| ratchet 5–12 Hz reads | verdict |
|---|---|
| **below its slope-matched null** (~4) | **the ratchet is gone in that regime**; the loop-gain account is confirmed |
| **unchanged** (V122 reference ≈33) | a predicted 3.4× damping increase produced nothing ⇒ **falsifies the real-positive `P·L` assumption** ⇒ this loop does not produce the 14.3× cancellation, and the assist map is exonerated the way the Coulomb relay now is |
| **rises** | lowering `\|L\|` sharpened the mode, possible only if `P·L` is not real-positive ⇒ revert and re-derive the phase |

| grind 15–25 Hz reads | verdict |
|---|---|
| below its null | grind gone. ⚠ margin here is only ~3.5× on the flying build, so a **marginal** grind read is **inconclusive, not negative** |
| clearly below 23.2 (V122 reference) | V158's damper shape is working |

**There is no uninterpretable branch.**

---

## 🛑 WHAT WILL FEEL DIFFERENT, AND WHY

Two changes, and they act in **different regimes**, so they are distinguishable by feel:

- **V168's cap — always on, including manual.** Less assist per unit driver torque **near centre**
  ⇒ **heavier steering there**. This cuts against the standing "keep it light" instruction and is a
  real trade.
  ⊕ **Peak authority and max steering rates are UNTOUCHED** — the curve is uncapped above X≈450.
  ⊕ **LKAS effort is UNTOUCHED** — the map is driver-torque fed (`0xC616C`=0 ⇒ `gp-0x6b4a`≡0,
  asserted in the build), so it cannot reach the LKAS lane.
- **V158's damper — ENGAGED modes 26/27 only.** More rate-proportional damping while engaged.

If the car feels heavy **while driving it yourself**, that is V168's cap.
If it feels heavy **only when openpilot is steering**, that is V158's damper.

**Dose:** 1536 is the **smallest** step whose predicted effect (3.4×) clears the one-episode
detection margin. **1280 (4.5×) and 1024 (5.7×) remain available** if V168 reads clean but the
ratchet is only reduced rather than gone.

---

## IF IT FAULTS

No fault is expected — this is a single calibration byte in the `0xC6000` block, no cave, no code
edit, CRC chain verified 50/50 and readback byte-identical. If a DTC does appear, revert to V158 and
report the code; the cell is a pure gain cap with no interlock relationship recorded anywhere in the
lineage.

---

## WHERE THE EFFECT WILL SHOW UP MOST CLEARLY

The ratchet's amplitude is **monotone in command magnitude** (excess 17.0 -> 58.1 across the command
range, a 3.4x rise) and peaks in the **12-25 deg/s wheel-rate band** (excess 143.1 there vs 9.7 at
0-3 deg/s). Its *frequency* barely moves (CV 5.5 % across speed).

=> the pass is most informative if the creep involves **actual steering input** rather than a
straight crawl: a slow continuous lap with real curvature keeps both the command and the wheel rate
in the bands where the ratchet is largest. A dead-straight 15 s crawl at near-zero command sits in
the weakest stratum and will under-read the effect in both directions.
