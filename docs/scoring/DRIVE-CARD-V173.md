# DRIVE CARD — V173  ·  **FLY THIS**

**Flash target:** `39990-TVA,A160-V173-V158BASE-ASSIST.SECTION.POLES.NOTCH.KEPT-0x13000-0x100000.rwd`
**.rwd SHA256** `5d213cf8604df90f2df2eaa2a8e40ccedde89f1d66055cb2a22c81edb7245396`
**image SHA256** `a9877aeecfbbbf2436c63fbc81041e1dfbfde787f5a1bf8ea58404b8f86ab1f7`

> 🛑 Nothing here authorises a flash. Name the file and the bus yourself; kill openpilot/pandad
> (`tmux kill-server`) before any flash operation.

---

## THE DRIVE — ONE CONTINUOUS 15-SECOND PASS

A single continuous 15 s engaged creep episode detected the ratchet in **11 of 11 episodes (100 %)**
on the existing corpus, at a **5–65× margin**. One pass answers it.

1. **Engaged creep, ONE continuous pass of 15 seconds, 1–24 km/h.** Don't break it up — the analysis
   window is 5.12 s and a broken pass yields too few of them.
2. **Include real curvature.** The ratchet's amplitude is monotone in command (excess 17.0 → 58.1
   across the command range) and peaks in the **12–25 deg/s** wheel-rate band. A dead-straight crawl
   sits in the weakest stratum and will under-read the effect **in both directions**. A slow
   continuous lap of a car park is the right shape.
3. **Stop as soon as you know.** If the symptom is still there after one pass, the drive has answered
   its question.
4. A matched manual creep pass at the same stretch and speed, if convenient. Not required — both
   symptoms are engaged-only, so the manual arm is a control rather than a comparison.

**Score with:** `python rlog-tools/score/score_band_excess.py <route-tag>`

That one command now prints the verdict, both attribution discriminators, and the reference values.

---

## WHAT V173 CHANGES

Three float32 cells on the V158 base — the poles of the assist map's own second-order section.
`C_B0` is left **byte-identical to stock**, which is what preserves Honda's 55.23 Hz notch.

```
freq        FLYING      V173        what it means
0.5 Hz      0.999965    0.994633    steering weight at rest: UNCHANGED
3   Hz      0.997530    0.847560    driver band, 15 % down
5   Hz      0.993052    0.689768    driver band, 31 % down
8.64 Hz     0.978950    0.476076    THE RATCHET -- 2.1x attenuated
21  Hz      0.865930    0.189446    the grind -- 4.6x
55.23 Hz    0.000128    0.000013    Honda's notch KEPT, and deeper
```

Loop effect: **5.8–6.9× more damped**, insensitive to the largest remaining uncertainty in the model.
Poles are **real** at [0.97, 0.475] ⇒ no ringing, 0.0 % step overshoot. Max gain over the full band
to Nyquist is **0.9946** ⇒ it never amplifies anything.

---

## PRE-REGISTERED OUTCOMES

| ratchet 5–12 Hz | verdict |
|---|---|
| **below its slope-matched null** (~4) | **gone in that regime**; the loop-gain account holds |
| **unchanged** (V122 reference **33.2×**) | the predicted damping produced nothing ⇒ **falsifies the real-positive `P·L` assumption for the slope-cap builds TOO** — they share it, so this null closes both lever classes at once |
| **rises** | `P·L` is not real-positive; revert and re-derive the phase |

| grind 15–25 Hz | verdict |
|---|---|
| falls, and **20–25 falls more than 15–20** | V173's filter did it — its attenuation is sloped (2.2× more at the top) |
| falls, and **both sub-bands fall equally** | V158's damper did it — rate-proportional, dose-set, flat |
| ratchet moves but grind does not | the shared-loop account is wrong somewhere, and **that gap names where** |

Reference on the flying build (V122, route r24, `cs_tq`): **ratchet 33.2×, grind 14.0×**; grind
sub-bands **15–20 = 5.8×, 20–25 = 14.0×**.

**No uninterpretable branch.**

---

## 🛑 WHAT WILL FEEL DIFFERENT

- **Steering weight at rest: unchanged.** DC gain 0.9947.
- **Fast inputs: assist arrives ~30 ms later**, and 3–5 Hz content is 15–31 % down. If anything feels
  off it will be on quick turn-in — the assist "catching up" rather than heaviness.
- **V158's damper is also on this build** (engaged modes 26/27 only). Heaviness *only* while
  openpilot is steering is that, not this.

**If the lag is the problem**, V168 and its four-dose ladder are built and ready — their cost is
static weight rather than response speed. See `docs/scoring/BUILD-INVENTORY.md`.

**If it works but not enough**, the trade is priced: poles 0.980/0.60 give 0.338 at 8.64 Hz for
+46.6 ms of lag, and 0.975/0.95 give 0.283 for +54.6 ms. One coefficient triple away.

---

## IF IT FAULTS

Three float32 cells the kit has already changed on-car without fault (V106/V107 moved these). The
enable was already on. No cave, no code edit. Poles real and inside the unit circle with margin.
GATE 1 is cleared: `gp-0x6b86` has exactly **one** consumer outside its producer (the aggregator at
`0x3AC7C`) and no monitor watches it, so heavy filtering cannot trip a fault path. CRC chain 50/50 and
readback byte-identical.

If a DTC appears, revert to V158 and report the code.
