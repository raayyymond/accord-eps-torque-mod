# V292 REPLAYED THROUGH THE OPERATOR'S OWN RECORDED GRINDING EPISODES

**Agent `replay`, subagent of `main`, 2026-09-13. ANALYSIS ONLY — nothing built, nothing flashed,
nothing sent on any bus, no build script edited, no commit.**
Files: `v292_replay_lib.py` · `v292_replay_s1.py` · `v292_replay_s2.py` · `v292_replay_s3.py`;
outputs `_scratch/v292_replay_s1.txt`, `_scratch/v292_replay_s2.txt`, `_scratch/v292_replay_s3.txt`.

---

## THE ANSWER

**On the operator's own recorded grinding episodes, the byte-exact closed-loop replay predicts V292
delivers ×0.55 of V282's 18–22 Hz ring amplitude (pooled median over 10 episodes × 23 plant fits;
95 % CI [0.54, 0.57]; ×0.71 on the freshest route r6c) and ×0.29–0.36 of its ring-down time (the 20 Hz
mode's free decay half-life falls from 108–197 ms to 39–71 ms), with the 6–9 Hz strong-turn ripple at
×1.03 on r39's loaded high-angle episodes and ×0.94 on r35's, and the delivered torque outside the
ring bands at ×0.999–1.000; the 9–18 Hz band reads ×1.09–1.11, and on r6c's own 12–17 Hz episodes that
band reads ×1.17 — the shoulder is real, it is much smaller on real episodes than the linear ×1.99
worst case, and it is the one thing V292 makes worse.** The positive control passes exactly: the
record's mirror reproduces `COMB-VS-ECHO` §A1 to the digit (T_total 57.21, CMD leg 11.56, FB leg
50.27) and the V282 closed loop reproduces every recorded window with `max|ΔT| = 0`.
🛑 **This is a MODEL PREDICTION, not a drive.** The plant is the fitted `design290b` family, not the
car; the residual disturbance absorbs plant mismatch; and openpilot's outer loop is frozen at the
recorded command, so nothing here says how the car will feel.

---

## 0. Pre-registration — written before anything was run

`v292_replay_s2.py` carries this verbatim in its docstring. **"V292 does not help on real episodes"** if:

| | test | limit | result |
|---|---|---|---|
| **F1** | pooled 18–22 Hz delivered-torque ring ratio | ≥ 0.85 | **0.554** — not tripped |
| **F2** | ring-envelope half-life ratio (the record's half-peak decay metric) | ≥ 1.00 | **1.089 — TRIPPED as written.** The metric is confounded; §4 proves it and gives the matched measurement, which reads **0.29–0.36** |
| **F3** | 9–18 Hz shoulder ≥ 1.50 while the ring gain is < ×2 | ≥ 1.50 | **1.108** — not tripped |
| **F4** | 6–9 Hz strong-turn ripple in situ | > 1.05 | **1.028 pooled** — not tripped; **3 of 15 fits exceed it**, worst 1.103 |
| **F5** | delivered torque outside the ring bands | ±2 % | **×0.999–1.000** — not tripped (a secondary 0.3–3 Hz readout reads −2.4 % on r6c) |
| — | V282 closed loop must reproduce the recording exactly | `max\|ΔT\| = 0` | asserted and held on **every window, every fit** |

**F2 is my own bad metric, not a V292 failure, and I am reporting the trip rather than quietly
swapping the metric.** §4 carries the diagnosis, the control, and the replacement.

---

## 1. METHOD

### 1.1 The chain, and what is byte-exact

```
recorded 0xE4 ──► demand_live ──► assist map ──► sp ─┐
                  (live taper arm)                   │
                                              E = 32·sp − fb          ┌── V292 edits ──┐
   x = −round(wire) ──► FEEDBACK LAG ──► fb ─────────┘                │ 0xC63E8/EA     │
        ▲              (a,b) = 923/1560  →  962/958  ◄────────────────┤ 923/1560→962/958│
        │              two `sar` floors, + V292 cave error feedback   │ cave 0xC4C00   │
        │                                                            └────────────────┘
        │        P = clamp((E·248)>>8, ±15360)   D = clamp((ΔE·128)>>3, ±10240)
        │        S = clamp((m·(P+D))>>8, ±15360) ; m = 254 (fade, live arm)
        │        OUTPUT LAG  s' = (992·s>>10)+(507·S>>10) ;  y = (s+s')>>5
        │        T = clamp((−y·5346)>>15, ±3072)                    ← the 427 tap
        │                                                                  │
        └──── wire[n] = (Ĝ ⊛ (T + ΔT_r24))[n] + d[n] ◄──────────────────────┘
                        └ fitted plant, ZOH + integer-tick delay, CPD = 8
                                       ΔT_r24 : 0xC6446  5244 → 4725
```

**INTEGER, byte for byte:** the feedback lag (two separate `sar 0xa` floors at `0x28F9A`/`0x28FA0`,
then `add r7,r9` at `0x28FA2`; the V292 cave's `andi 0x3ff` error-feedback remainders), the output lag,
the motor gain shift, every clamp. **The forward path (E, P, D, S) keeps the record's own
float-then-floor arithmetic** so that the open-loop run is directly comparable to
`grind_incident_r35.simulate`; §2.3 measures that this choice is worth ≤ 0.1 % at the ring.

**Cells read from the IMAGES, not from any build script** — V282 `0ea98d06…`, V292 `d1128232…`:

| cell | V282 | V292 | what it is |
|---|---|---|---|
| `0xC63E8` / `0xC63EA` | 923 / 1560 | **962 / 958** | feedback-lag pole, 16.52 → **9.94 Hz**, DC held 30.891 → 30.903 |
| `0xC6446` | 5244 | **4725** | r24 damper-lane arm, ×0.9010 |
| `0xC4C00` | `FF…` (erased) | 52-byte cave | first-order error feedback on the two feedback-lag floors |
| `0x28F8E` | `f03f2002` | `890772bc` | the hook (`jr 0xC4C00`) |
| `0xC63EC/EE`, gain, Kp, Kd, every clamp | — | **unchanged** | — |

### 1.2 The disturbance inversion, and why it is well posed everywhere

The plant carries ≥ 1 tick of pure transport delay, so `wire[n]` does not depend on `T[n]`. Run the
electronics **open loop** on the recorded wire → `T_rec`; filter `T_rec` through the plant; the
remainder is everything else:

```
d[n] = wire_rec[n] − (Ĝ ⊛ T_rec)[n]
```

Marching the **closed** loop with this `d` reproduces `wire_rec` and `T_rec` **bit for bit**
(`max|ΔT| = 0`, `max|Δwire| ≈ 1e−11` float roundoff — asserted on every window and every fit).
**It is a causal marching inversion, not a spectral division, so there is no band in which it is
ill posed and no regularisation anywhere.** The price is that `d` is not a physical disturbance: it
absorbs road input, driver input, unmodelled lanes **and plant mismatch**. That is why every number is
reported across the plant family rather than on one fit.

### 1.3 The r24 lane, folded the way the record's own topology requires

🛑 **The `design290b` plants ALREADY contain the r24 lane closed around them** — they are `G_meas`-class
(`TRACE-2026-09-13-r24-lane-transfer` §9.1: *"the tap-identified `G_meas = rate/T` already has r24
CLOSED around it … adding r24 to such a plant double-counts"*; 0 of 304 reproduce the measured pole
with r24 added). **So I fold only the arm's DELTA**, as a parallel branch:

```
ΔT_r24 = −K·((5244 − 4725)·κ / 1024)·D4(f)·B(f)·wire ,   κ = 2353/5244 = 0.4487 ,  K = 5346/32768
```

with `B(f)` the measured `b_of_f_v282` transfer (parametric `Z1P`, `loaded_any`), applied by a
fixed-point outer iteration (converged: max|Δ| 8.12 → 0.18 → 0.008 counts).

**How big is it?** `|ΔH| / |R_servo|` = **0.06 % at 3 Hz, 2.7 % at 10 Hz, 1.4 % at 20.3 Hz.** With the
motor gain included the whole r24 lane is 15.6 % of the servo at 20.3 Hz; **without it, ×6.13 bigger,
i.e. 95 % of the servo.** Both are scored in §3.2 — the answer barely moves either way.

---

## 2. POSITIVE CONTROLS — all of them, before any prediction

### 2.1 The record's baseline, reproduced to the digit [EVIDENCE]

r39, V282, the 10 loudest 3 s engaged windows (`burst_echo_sizing.loud_windows`), f0 19.922 Hz:

| | mine | record (`COMB-VS-ECHO` §A1) | |
|---|---|---|---|
| T_total | **57.21** | 57.21 | MATCH |
| CMD leg | **11.56** | 11.56 | MATCH |
| FB leg | **50.27** | 50.27 | MATCH |

### 2.2 The mirror against the RECORDED 427 torque tap [EVIDENCE — and it is looser than the brief assumed]

| window (t, s) | amp meas | amp sim | sim/meas | corr_band | coh |
|---|---|---|---|---|---|
| 799.8 | 32.04 | 29.65 | 0.925 | 0.93 | 0.97 |
| 146.6 | 103.34 | 113.19 | 1.095 | 0.91 | 0.99 |
| **844.5** | 31.10 | 40.60 | **1.306** | 0.82 | **0.57** |
| **299.7** | 22.16 | 31.94 | **1.442** | **0.06** | **0.42** |
| 145.0 | 93.04 | 111.63 | 1.200 | 0.85 | 0.99 |
| 134.4 | 94.90 | 98.01 | 1.033 | 0.92 | 1.00 |
| 137.6 | 51.09 | 59.04 | 1.155 | 0.81 | 0.98 |
| 609.5 | 62.72 | 63.84 | 1.018 | 0.75 | 0.92 |
| 830.1 | 43.06 | 48.97 | 1.137 | 0.96 | 0.97 |
| 207.1 | 108.99 | 121.86 | 1.118 | 0.83 | 1.00 |
| **median** | | | **1.128** | | |

**The brief's "4–14 %" is tighter than the mirror actually delivers.** Median |error| **12.8 %**, range
1.8–44.2 %. **Two windows fail the control**: t = 299.7 s (band correlation **0.06**, coherence 0.42 —
the mirror does not track it at all) and t = 844.5 s (coherence 0.57). **Dropping both changes nothing:
the pooled ring ratio goes 0.554 → 0.552, wheel rate 0.628 → 0.612.** Every table below is on all ten.

### 2.3 My electronics against the record's mirror, and two defects in the record's mirror

**DEFECT A [EVIDENCE].** `grind_incident_r35.simulate` computes the feedback lag as **one** floor of the
sum, `floor((a·s + b·x)/1024)`. The listing has **two separate** floors. **V292's cave exists precisely
to repair those two floors, so the single-floor form structurally cannot represent the edit.** Mean
output at a steady `x`:

| x | one floor (the record) | two floors (the bytes) | linear |
|---|---|---|---|
| +1 | 12.000 | **2.000** | 30.891 |
| +3 | 74.000 | **62.000** | 92.673 |
| +16 | 474.000 | **468.000** | 494.257 |

My two-floor march reproduces **ADV-V292-B §1's mean-gain table to five decimals by an independent
implementation** (V282 2.000 / V291 0.000 / V292 **30.90320** at x = +1; every other row too) and my
`fb_tick` matches `v292_cave_mirror.FbLag` **tick for tick on 5000 random inputs, all three builds**.

**DEFECT B [EVIDENCE].** The mirror's output lag is a float `lfilter`, not the integer
`(992·s>>10)+(507·S>>10)` with `(s+s')>>5`. Mine is integer.

**Neither moves the ring**: my byte-exact march reproduces the record's mirror to **median ×0.9999**
(worst window ×0.9991) over the same 10 windows. That is the key physical fact for this whole replay —
**the r39 ring is 15.8 RAW COUNTS on the feedback operand**, far above the quantiser, where
ADV-V292-B §5.5's describing function reads V282 0.998 and V292 0.9998. **At the ring the cave is
near-inert; the levers that act are the POLE MOVE and the r24 arm cut.**

### 2.4 The ±102 deadband on `y` cannot reach these episodes [EVIDENCE — closes an open premise]

ADV-V292-B §7.2 flags that if `gp−0x6806` is 0 when engaged, `y` is zeroed unless `|y| > 102`, which
would make the whole `sp = 3` clause vacuous. **At these grinding episodes `|y|` runs p10 2963 / p50
4367 / p90 6099, and 0.3 % of samples sit inside the deadband.** Whatever that branch does, **it cannot
change this answer.**

---

## 3. TASK 2 — r39, the 10 loudest episodes, 23 plant fits

Every column is a **V292 / V282 ratio on the same window, same 0xE4 command, same disturbance.**
Measurement starts 800 ticks in, after the pre-roll. Full per-fit table in `_scratch/v292_replay_s2.txt`.

### 3.1 PRIMARY [EVIDENCE]

| fit | T 18–22 | W 18–22 | T 9–18 | T 5–9 | auth oob | auth LF | auth \|T\| |
|---|---|---|---|---|---|---|---|
| 225 (median) | 0.535 | 0.638 | 1.079 | 1.075 | 1.000 | 1.004 | 1.000 |
| 215 (lo-auth) | 0.534 | 0.652 | 1.021 | 1.038 | 1.000 | 1.007 | 1.000 |
| 38 (hi-auth) | 0.469 | 0.549 | 1.241 | 1.125 | 0.999 | 1.016 | 1.000 |
| 117 (worst B4) | 0.558 | 0.633 | 1.098 | 1.059 | 1.000 | 1.005 | 1.000 |
| **POOLED, 23 fits** | **0.554** | **0.628** | **1.108** | **1.075** | **1.000** | **1.006** | **1.000** |
| 95 % CI | [0.54, 0.57] | [0.61, 0.65] | [1.10, 1.12] | [1.07, 1.08] | [1.00, 1.00] | [1.00, 1.01] | [1.00, 1.00] |
| per-fit range | 0.458–0.680 | 0.531–0.838 | 0.994–1.241 | 1.038–1.125 | 0.999–1.000 | 1.002–1.017 | 1.000 |

### 3.2 CONTROLS on the r24 fold — the answer does not turn on it

| r24 treatment | T 18–22 | W 18–22 | T 9–18 | T 5–9 |
|---|---|---|---|---|
| **folded WITH the motor gain K (primary)** | **0.554** | 0.628 | 1.108 | 1.075 |
| not folded at all (arm held at 5244) | 0.534 | 0.626 | 1.068 | 1.077 |
| folded WITHOUT K (the record's inherited fold, ×6.13 too big) | 0.538 | 0.634 | **1.148** | 1.024 |

**What changes if you leave the motor gain out:** the ring answer moves by 3 % (0.554 → 0.538) and the
**shoulder reads 4 % worse** (1.108 → 1.148). Nothing decision-bearing turns on it. Dropping the r24
delta entirely moves the ring 4 % the other way. **ADV-V292-B §7.1's ×6.13 unit defect is real and it
is immaterial to this question.**

### 3.3 SECOND METHOD on the headline — linear sensitivity, no time-domain march [EVIDENCE]

Predicted from `|1/(1+L)|` and `|R|` weighted by **each window's own disturbance spectrum**:

| fit | T 18–22 linear | T 18–22 **byte-exact** | W 18–22 linear | W 18–22 **byte-exact** |
|---|---|---|---|---|
| 225 | 0.389 | **0.535** | 0.549 | **0.637** |
| 215 | 0.377 | **0.533** | 0.534 | **0.650** |
| 38 | 0.333 | **0.471** | 0.474 | **0.552** |
| 117 | 0.346 | **0.557** | 0.481 | **0.630** |

**The two methods agree in direction and size, and the byte-exact loop delivers CONSISTENTLY LESS of
the benefit than the linear model claims — ×1.35 on torque, ×1.17 on wheel rate.** Same sign as
ADV-V292-B §7.0's own finding (linear ×0.143 at 20.3 Hz against byte-exact ×0.390). **Quote the
byte-exact numbers, not the linear ones.**

---

## 4. RING-DOWN — F2 tripped, and why the pre-registered metric was the wrong one

**The driven metric [pooled ×1.089] says the ring dies SLOWER. The matched free ring-down [×0.286–0.361]
says it dies MUCH FASTER. The second is the right measurement and here is the proof.**

### 4.1 The matched free ring-down [EVIDENCE]

A one-tick wheel-rate kick injected at the burst peak, taken as the **difference of two closed
byte-exact runs sharing `d`, the command, the plant and the operating point** — so the clamps, the fade
and the quantisers are all at their real states. Decay fitted on the analytic envelope of the
12–30 Hz-filtered difference.

| fit | LINEAR pole V282 | LINEAR pole V292 | linear t½ ratio | **byte-exact t½ V282 → V292** | **ratio** | r² |
|---|---|---|---|---|---|---|
| 225 | 19.95 Hz / ζ 0.0248 | 19.86 Hz / ζ **0.0843** | 0.296 | **184 → 57 ms** | **0.286** | 0.80 |
| 215 | 19.81 Hz / ζ 0.0209 | 19.21 Hz / ζ **0.0736** | 0.293 | **197 → 71 ms** | **0.342** | 0.93 |
| 38 | 19.77 Hz / ζ 0.0353 | 20.50 Hz / ζ **0.0830** | 0.410 | **156 → 55 ms** | **0.352** | 0.89 |
| 117 | 20.19 Hz / ζ 0.0412 | 18.49 Hz / ζ **0.1442** | 0.312 | **108 → 39 ms** | **0.361** | 0.90 |

**Two independent methods agree: V292 raises the 20 Hz mode's damping ×2.4–3.5 and cuts its ring-down
half-life to ×0.29–0.41.** Amplitude-independent — kicks of 256 / 512 / 1024 counts give 0.287 / 0.286 /
0.304 on fit 225, so the measurement is in the linear regime.

### 4.2 Why the driven metric is confounded [EVIDENCE — the control]

| | half-life, 18–22 Hz envelope, fit 225 |
|---|---|
| the DISTURBANCE `d`'s own envelope | **276 ms** (p10 66, p90 1293) |
| V282 driven | 344 ms |
| V292 driven | 441 ms |
| V282 **free** ring-down | **184 ms** |
| V292 **free** ring-down | **57 ms** |

V282's driven envelope (344 ms) is dominated by its own resonance (184 ms free). **V292's free
ring-down (57 ms) is five times shorter than the disturbance's envelope, so its driven envelope simply
FOLLOWS the disturbance** and lands inside the disturbance's own spread. The half-peak decay of a
*driven* response measures peak-to-background contrast, not ring-down, and it is not a matched
comparison when the two arms' rings are different sizes. **I pre-registered the wrong metric; F2's trip
is an artifact of my choice, not a V292 result.**

---

## 5. TASK 3 — the strong turn, the 7.3 Hz gate in situ

r35 is **V281 rev 3**, whose LKAS rate-loop cells are **byte-identical to V282's** — fb 923/1560,
lag 992/507, gain 5346, r24 arm 5244, Kp flat [248]×5, read from both images — so replaying its
episodes through "V282 electronics" is exact, not an approximation. **[EVIDENCE]**

Windows: engaged, demand index ≥ 60, speed < 6 m/s, ranked by their own 6–9 Hz driver-torque ripple.
(r35 carries no `marks.json`, so the selection is the ripple's own loudness, not the clock bookmark.)

| route | windows | idx p50 | v (m/s) | **T 6–9** | T 5–9 | T 18–22 | T 9–18 | auth oob | auth \|T\| |
|---|---|---|---|---|---|---|---|---|---|
| **r35** (V281r3) | 3 | 230–240 | 1.4–4.6 | **0.937** | 0.948 | 0.863 | 0.961 | 1.000 | 1.000 |
| | 95 % CI | | | [0.93, 0.95] | | | | | |
| **r39** (V282) | 4 | 240 | 1.7–3.5 | **1.028** | 1.036 | 0.583 | 1.049 | 0.998 | 1.000 |
| | 95 % CI | | | [1.02, 1.04] | | | | | |

**Pooled, the gate holds: ×1.028 on r39 and ×0.937 on r35, both inside ×1.05.**
🛑 **But 3 of 15 fits exceed it on r39** — fit 38 (hi-authority) **1.103**, fit 67 **1.082**, fit 246
**1.076**. **On the high-authority tail of the plant family, the 6–9 Hz torque ripple on a loaded turn
rises up to ×1.10.** That is the honest reading of B5's *"1.0 at only −5.9° of loop phase"* showing up
on real data. Note the ring still falls hard on these same loaded turns (×0.583).

---

## 6. TASK 4 — r6c, the freshest V282 route (3701 s, 62 segments, mostly motorway)

| windows | selected band | **that band** | T 18–22 | W 18–22 | T 9–18 | T 5–9 | auth oob | auth LF | auth \|T\| |
|---|---|---|---|---|---|---|---|---|---|
| 5 loudest | **18–22 Hz** (f0 20.117) | **0.712** | 0.712 | 0.694 | 1.087 | 1.085 | 0.999 | **0.976** | 0.999 |
| | 95 % CI | [0.64, 0.74] | | [0.65, 0.73] | [1.06, 1.11] | [1.07, 1.09] | | | |
| 5 loudest | **12–17 Hz** (f0 13.770) | **1.165** | 0.643 | 0.675 | 1.142 | 1.086 | 0.995 | 0.998 | 0.998 |
| | 95 % CI | [1.13, 1.20] | | | [1.12, 1.18] | [1.08, 1.09] | | | |

Matched free ring-down on r6c: **ring-band windows ×0.316–0.519** (91–165 ms → 26–72 ms);
**12–17 Hz windows ×0.274–0.352** (110–220 ms → 38–69 ms).

**Two things to read off this route.**
1. **The ring falls less on r6c than on r39 (×0.71 vs ×0.55).** r6c's loudest ring windows include
   motorway at 23–30 m/s with demand index 3–9 — a different operating point from r39's low-speed
   loaded episodes, and one where less of the ring is the loop's own regeneration.
2. 🛑 **On r6c's own loudest 12–17 Hz episodes, that band gets 17 % LOUDER (×1.165, CI [1.13, 1.20],
   worst fit 1.357).** This is the 9–18 Hz shoulder, measured on real recorded episodes rather than on
   a linear sensitivity curve. It is far smaller than the ×1.99 linear worst case, and it is real.
3. The 0.3–3 Hz delivered-torque amplitude reads **×0.976** on the ring-band windows — a 2.4 % drop,
   just outside the ±2 % I pre-registered, on a secondary readout. The primary authority measure
   (broadband rms with 5–22 Hz notched) is ×0.999 and mean |T| is ×0.999.

---

## 7. WHAT WOULD HAVE SAID "V292 DOES NOT HELP", AND WHAT ACTUALLY HAPPENED

Nothing in §0's list tripped on a sound metric. The ring falls by 29–46 % on every route and every
plant fit; the mode's free ring-down falls to a third; the strong-turn gate holds pooled; authority is
untouched. **The cost is the 9–18 Hz shoulder, and it shows up on real data at ×1.09–1.17 rather than
the linear model's ×1.99.**

**The honest summary for a decision:** V292's benefit is on the band the operator complains about, it is
large, and it is confirmed by two independent methods. Its cost is a band adjacent to it, it is real,
and it is smaller than the pre-drive analysis feared. The two open risks this replay CANNOT price are
ADV-V292-B §7.3's cold-start ramp-in (V292's feedback delivers 6.1× V282's at 20 ms after engage — an
earlier "grab" on a still wheel, which no gate scores and no replay of steady episodes can see) and
whatever the operator feels that is not in these bands.

---

## 8. WHAT I DID NOT VERIFY

- **The plant is the fitted family, not the car.** `d` absorbs plant mismatch, so where the fit is
  wrong the counterfactual is biased. That is why everything is reported over 15–23 fits; the spread
  is the honest uncertainty and it is wider than any CI printed here.
- **openpilot's outer loop is frozen.** The recorded `0xE4` command is replayed unchanged in both arms,
  so no outer-loop reaction to a changed wheel rate is captured. On r39 the command leg is 20 % of T,
  so this is a second-order omission — but it is an omission.
- **The driver-torque bar is held as recorded in both arms** (it sets the fade and the demand taper).
  I did not close the bar around the rate; the r24 lane's own `B(f)` path is the only place the bar
  responds, and only through the arm DELTA.
- **The r24 lane's ±3 deadband and ±8192 clamp are not modelled.** The record measures that neither
  binds (`TRACE-2026-09-13-r24-lane-transfer` §9.3); I did not re-derive that.
- **I did not re-derive `B(f)` or the plant family** — both are inherited, declared, and named.
- **I did not verify the cave on-car**, only its arithmetic (against `v292_cave_mirror` tick-for-tick
  and against ADV-V292-B §1's table by an independent implementation).
- **The 0x14A b3 telemetry is not modelled** (it is a read-only probe bit).
- **The 427-tap positive control fails on 2 of 10 r39 windows.** Excluding them moves the pooled ring
  ratio by 0.002; I did not investigate why the mirror misses them.
- **Kick-based ring-down needs a large kick** (≥ 256 counts) to clear the 1-count quantiser; at 64
  counts the incremental response is 1–2 counts and the fits are meaningless (r² 0.0–0.4). The reported
  numbers are amplitude-independent over 256–1024, but they are not a measurement at ring amplitude.
- **No r35 clock bookmark was used** — no `marks.json` exists for it, so the strong-turn windows are
  selected by their own 6–9 Hz ripple.
