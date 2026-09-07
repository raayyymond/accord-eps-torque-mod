# Grind #1 — the loop shape, sized from bytes, and the ONE build

Subagent `shape`, 2026-09-06. Brief from `main` (orchestrator). Analysis only: **nothing built, nothing sent, nothing flashed.**
Script: `rlog-tools/studies/grind/grind1_loop_shape_v287.py` → `_scratch/grind1_loop_shape_v287.txt` (604 lines, reproduces every number here).
Image: `_v282_…_plain_image.bin`, sha256 `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe`. Disassembly by GhidraMCP (`dry_run:true`), constants re-read little-endian in Python.
**EVIDENCE (with the method) or BELIEF on every claim.**

---

## 0. Headline

1. 🛑 **The record's headline loop shape — output-lag pole 5 → 15 Hz, `0xC63EC/EE` = 932/1457 — is a DO-NOT-FLASH.**
   Under model (a), the only loop model the kit licenses for the 27–32 Hz band and the one that reproduces the kit's own
   *measured* gain margins, it takes the gain margin from **1.77× to 0.72×** and moves the −180° crossing from 28.1 to
   31.7 Hz where `|L| = 1.38`. Its **Kp-equivalent margin is Kp ≈ 1003**, which is **1.44× past the top of the stock Kp
   LERP (696)** — i.e. past anything this car has ever been driven at. `GRINDING-DEEP-ANALYSIS` §3 ranked that shape #1
   and #2 and **never ran the Nyquist check on it**; the addendum ran Ku for *Kd* changes only. [EVIDENCE for the
   arithmetic; BELIEF for the plant above 25 Hz, which is the whole bifurcation — see §5.]
2. 🛑 **The output-lag pole is a WATERBED lever, not a damping lever.** Every dose buys 18–22 Hz by growing 26–33 Hz.
   The sensitivity peak is **already at 26.3 Hz today** (`Ms` 2.38) and every pole raise pushes it up and grows it:
   27.2 Hz / 3.06 at a 6 Hz pole, 28.7 Hz / 6.56 at 8 Hz, 30.1 Hz / 102 at 10 Hz. **The band it moves the problem into
   is the band no instrument on this car can resolve in frequency.** [EVIDENCE, model (a) arithmetic]
3. ⭐ **The gate can be calibrated against what has already flown, and that is what makes a dose possible at all.**
   The same model assigns **GM 1.04×** to Kp 696 — the top of the stock LERP, which **every build before V281 rev 3
   flew** — and creep20 *measures* GM 1.32× at Kp 470. So the model's absolute scale is pessimistic by ≥1.7×, and a
   modelled GM of ~1.2× is a margin this car has demonstrably been driven at. [EVIDENCE]
4. ⭐ **THE ONE BUILD: `0xC63EC` = 974, `0xC63EE` = 792.** Output-lag pole 5.05 → **7.97 Hz**, DC held to −0.024 %,
   two halfwords, cal-only, no code byte, base V282. Call it **V287**. It is the unique dose where three windows
   overlap: it is the **smallest** dose whose benefit endpoint clears its own route-to-route noise floor, the
   **smallest** dose that decides the plant question, and it is still **inside the flown gain-margin envelope**
   (GM 1.19×, Kp-equivalent **589** < 696).
5. 🛑 **Frame it as a DISCRIMINATOR, not a cure, and say so to the operator before he drives it.** Its predicted
   benefit is a ×0.76 cut in the 18–22 Hz motion; its predicted cost is a **×2.28 rise in the 26–33 Hz motion**. The two
   plant models predict **×2.28 (delay) vs ×1.03 (frozen)** for that guard band, a **2.21× separation** against a
   measured route-to-route spread of **1.25×**. One drive decides the premise behind `Ku = 227`, behind every
   high-frequency risk verdict in this kit, and behind the V255/V269 post-mortem. That is worth more than the dose.
6. 🛑 **Two of the three statistics the brief asked me to pre-register CANNOT resolve the edit, and I am reporting that
   rather than printing them as if they could.** The T-re-rate phase rotates only **+7.4°** at 20 Hz against a
   route-to-route phase spread of **30°**; the bit-6 duty falls only to **×0.968** because the 20 Hz line is a small
   part of the tap's total power. Neither is an endpoint. The usable endpoints are in §6.
7. **The DC-gain formula is CONFIRMED FROM BYTES** — `2b/(1024−a)/32 = 0.990234` for the output lag, and the `/32` is
   the `sar 0x5, r9` at `0x0002A1AC`. The feedback filter is the *same* structure without that shift, hence its DC gain
   of **30.89**, reproducing the kit's memory independently. **No pole design with DC held can overflow anything**:
   holding DC holds the state magnitude, so int32 headroom is 9.1× at every design and the `sxh` at `0x0002A1EC`
   never wraps (`|v| ≤ 21389 < 32767`). [EVIDENCE]
8. ⭐ **A CORRECTION OF RECORD, and it removes a hypothesis of my own.** The addend `r11` at `0x0002A1FC` is
   `(short)[gp-0x6b2c]`, **identically zero** in stock and V282 on every dominating path. So
   `T = clamp(±3072, (−K6·v) >> 15)` with **no torsion-bar feedthrough at all** — the 427 tap is the LKAS lane and
   nothing else. I had hypothesised a −0.163 bar feedthrough that would have carried a large part of the tap's 20 Hz
   ripple; it does not exist. [EVIDENCE — `firmware-codepath-tracer`, 11 dominating writers enumerated at the
   `0x29A48` join plus a raw LE byte scan; verified against my own read of the same disassembly.]
9. ⚠ **A DISAGREEMENT WITH THE RECORD I could not close.** I measure the 427 tap's phase re the wheel rate at 20.31 Hz
   in engaged hands-off creep as **−115° (r39, coh 0.85), −114° (r3c, 0.87), −112° (r35, 0.87)**. `GRINDING-DEEP-ANALYSIS`
   §2 carries **−69°** for the same lane in the same stratum. That is 46°, not 180°, so it is not a sign convention —
   it is a different estimator. §4 below uses the record's −69° so the ranking stays comparable with the record's; the
   pre-registration in §7 uses **my own** measured number, because a pre-registration must be scored the way it was
   predicted. **Both are stated; the discrepancy is open item 2.**
10. ⚠ **A STRUCTURAL CAVEAT ON THE FEEDBACK FILTER the record's ranking does not carry.** `0xC63E8/EA`'s output is
    rectified (`bp / subr r0, r16` at `0x00028FC4`) and enters as a **multiplier** on the lag output, not as an additive
    feedback term. Its unambiguous effect is a **gain** change; its effect as a *phase* element exists only through a
    term whose sign flips with the sign of the mean wheel rate and which vanishes as that mean goes to zero — i.e.
    exactly in the hands-off creep stratum where grind #1 lives. Shape 4 (the fb pole) is therefore ranked
    optimistically in the record. **I do not pick it, and this is one of the reasons.** [BELIEF, from the byte-exact
    structure; the arithmetic itself is EVIDENCE.]

11. ⭐ **HONDA'S OSCILLATION-REVERSAL DETECTOR PUTS A HARD CEILING JUST ABOVE THE CHOSEN DOSE, AND IT IS
    NOT MONOTONE.** `FUN_000428d4` counts alternate crossings of ±12800 on `gp-0x6c2c` (a filtered rotor-rate
    signal, on the MOTION side), resetting if 50 ms pass between crossings, and after 15 reversals applies a
    **live ×0.600 cut to motor demand**. Replaying the measured creep and bookmark windows through each dose's
    sensitivity ratio: **0 of 19 windows reach 15 reversals at any dose up to 8.0 Hz, at EVERY threshold from 10 %% to 70 %% of the window peak**, and at **10 Hz, 15 of 19 windows FIRE**. The detector is blocked today by PERSISTENCE, not amplitude, so the answer does not depend on where 12800 sits relative to the unknown scale. The 12 and 15 Hz rows read low only because a
    stable-loop `|S|` formula is meaningless once GM < 1 — that is an artefact, not safety. **The detector
    ceiling and the gain-margin ceiling agree, and both sit just above 974/792.** [EVIDENCE for the
    detector arithmetic and the replay; BELIEF for the wheel-rate-as-rotor-rate proxy, whose error direction
    is conservative — see §5b.]
12. 🛑 **A PRE-FLASH GATE I CANNOT CLOSE MYSELF.** The fb cells `0xC63E8/EA` have **one live reader each and
    are private**; the lag cells `0xC63EC/EE` have **TWO readers each**, and the second (`0x2A892`/`0x2A8A2`)
    is in the **orphan/unanalysed `0x2A400-0x2B600` region — which my own tracer proved is NOT all dead**
    (`0x2B422` and `0x2B57A` are `jarl`ed from `0x22530`/`0x22572`). **Do not build V287 until that second
    reader is resolved.** If it is live, the pole cells are not private and the edit touches a second lane
    silently — a GATE 1 ownership failure. Ironically this makes the fb pole the *cleaner* cell by ownership
    and the lag pole the better one by effect; I am not trading that away, I am gating on it.
13. **The 1 kHz tick is EVIDENCE on one method only** (on-car dwell of `0xC64DF` = 100 measured at 100.00 ms).
    The PID and r24 lanes run in the same task pass with zero skew, so every **relative** phase here is safe;
    an absolute-frequency error would rescale the pole labels but not the ranking.
14. ⚠ **`0xC40DC` IS NOT STOCK ON V282** — 14 against stock's 22. It is the detector's own input filter, and
    V282 has already narrowed it from a 67.1 Hz corner to 39.4 Hz. It is only **2.0 dB down at 30 Hz**, so it
    does **not** protect against the 26-33 Hz rise this lever creates. [EVIDENCE, byte-read]

---

## 1. Deliverable A — the arithmetic, byte-exact

`FUN_00028ea6`'s extent `0x28EA6..0x2A400` is **byte-identical between stock `code.bin` and the V282 image except two
bytes** at `0x2A1F0-F1` (`ld.h 0x746c,tp,r7` → `ld.h 0x7cd0,tp,r7`, the ×6 forward-gain repoint). [EVIDENCE — Python
byte diff over the extent.] So the structure below is read on the analysed stock program and is valid for V282.

### 1a. The two filters are the SAME filter

```
H(z) = (b/1024) · (1 + z⁻¹) / (1 − (a/1024) z⁻¹)          fs = 1 kHz
```
A one-pole IIR **on the increment**, with a one-sample **sum** on the output. The pole is `a/1024`; the zero is pinned
at Nyquist. That `(1 + z⁻¹)` is the kit's "two-sample sum" (`add r9,r26` at `0x00028FA4`), and it is why the feedback
filter's DC gain is 30.89 rather than 15.45.

**Feedback filter, `0x00028F86 … 0x00028FC7`** — input `x = gp-0x6a56` (the 16-bit rate operand), state
`*(int32*)(gp-0x3d30)`:

```python
def fb_step(D_prev, x, a, b, clamp):          # a = cal(0xC63E8) = 923 ; b = cal(0xC63EA) = 1560
    D_new = (a * D_prev >> 10) + (x * b >> 10)   # 0x28F92/0x28F8E muls, 0x28FA0/0x28F9A  sar 0xa (ARITHMETIC)
    y     = D_prev + D_new                       # 0x28FA4  add r9,r26   <- the two-sample sum
    y     = max(-clamp, min(clamp, y))           # 0x28FA6..0x28FBC, clamp = cal(0xC62E6) = 46080
    return D_new, abs((y >> 5) << 5)             # 0x28FC0 sar 5 / shl 5 ; 0x28FC4 bp / subr -> ABSOLUTE VALUE
```

**Output lag, `0x0002A180 … 0x0002A1B3`** — input `u` = the PID sum already clamped to ±`cal(0xC61BE)` = 15360, state
`*(int32*)(gp-0x3d3c)`:

```python
def lag_step(D_prev, u, a2, b2):              # a2 = cal(0xC63EC) = 992 ; b2 = cal(0xC63EE) = 507
    D_new = (a2 * D_prev >> 10) + (u * b2 >> 10)  # 0x2A194/0x2A180 muls, 0x2A1A6/0x2A1A0  sar 0xa
    return D_new, (D_prev + D_new) >> 5           # 0x2A1AA add ; 0x2A1AC  sar 0x5   <- THE /32
```

**⇒ DC gains, verified two ways** [EVIDENCE — closed form vs a bit-exact integer step response over 10⁵ ticks]:

| filter | closed form | value | integer step response |
|---|---|---|---|
| output lag | `2·b2/(1024−a2)/32` | `2·507/32/32` = **0.990234** | **0.990000** |
| feedback | `2·b/(1024−a)` | `2·1560/101` = **30.8911** | **30.6200** |

The record's `2b/(1024−a)/32 = 0.990` is confirmed, and the `/32` that distinguishes the two is the single
`sar 0x5, r9` at `0x0002A1AC`. The residual between closed form and step response is integer truncation in the `>>10`s.

### 1b. What the two feed, and the correction of record

```
lag_out ──┐
          ├── if cal(0xC64A3)=1 and gp-0x6806=0 and |sxh(lag_out)| ≤ cal(0xC61B8)=102
          │        and lag_out·prev ≤ 0        →  v := 0          (the P-only deadband, 0x2A1B4..0x2A1E4)
G_fb ─────┤
          └── else  v = sxh( (lag_out · G_fb) >> 15 )              (0x2A1E6-EC)

T = clamp( ±cal(0xC61B4)=3072 ,  (−K6 · v) >> 15 )   K6 = cal(0xC6CD0) = 5346    → st.h gp-0x6b38 @0x2A23C
```

🛑 **There is no addend.** `r11` at `0x2A1FC` is `(short)[gp-0x6b2c]` on all 11 dominating paths, and that cell is
identically zero in both images (its LERP Y table `0xC673E..0xC6744` is `0,0,0,0`, and the `gp-0x6a5e ≥ 32001` gate
forces the above-range branch regardless). **The 427 tap carries the LKAS lane alone.**

### 1c. Cells, read from the image

| addr | tp offset | what | V282 | stock |
|---|---|---|---|---|
| `0xC63E8` | `tp+0x73e8` | fb filter pole `a` | 923 | 923 |
| `0xC63EA` | `tp+0x73ea` | fb filter gain `b` | 1560 | 1560 |
| `0xC63EC` | `tp+0x73ec` | **output lag pole `a2`** | **992** | 992 |
| `0xC63EE` | `tp+0x73ee` | **output lag gain `b2`** | **507** | 507 |
| `0xC62E6` | `tp+0x72e6` | fb output clamp | 46080 | 7680 |
| `0xC61BE` | `tp+0x71be` | PID-sum clamp (the lag's input bound) | 15360 | 15360 |
| `0xC61BC` | `tp+0x71bc` | P clamp | 15360 | 15360 |
| `0xC61B8` | `tp+0x71b8` | P-only deadband | 102 | 102 |
| `0xC61B4` | `tp+0x71b4` | `gp-0x6b38` output clamp | 3072 | 512 |
| `0xC6CD0` | `tp+0x7cd0` | forward gain K6 (V282 reader) | 5346 | 65535 |
| `0xC6446` | `tp+0x7446` | r24 lane gain | 5244 | 512 |

**Reader census** [EVIDENCE — tracer, `docs/traces/TRACE-2026-09-06-lag-and-fb-pole-census-v282.md`]:
`0xC63E8` and `0xC63EA` have **one live reader each** (`0x28F8A` / `0x28F86`) and are **private**.
`0xC63EC` and `0xC63EE` have **two readers each** — `0x2A184` / `0x2A180` in the PID, and a second at
`0x2A892` / `0x2A8A2` in the **orphan, Ghidra-undefined `0x2A400-0x2B600` region**. That region is **not all
dead**: `0x2B422` and `0x2B57A` are `jarl`ed from `0x22530` and `0x22572`, immediately after the `0x22522`
call into `FUN_00028ea6`. **Treat the lag cells as private-in-effect but UNPROVEN, and gate the build on
resolving those two readers** (headline 12).

**Lineage** [EVIDENCE — the r36–r38 read's census over all 285 `_plain_image.bin` snapshots]: `0xC63EC`/`0xC63EE` are
**992/507 in all 285 images** and `0xC63E8`/`0xC63EA` are **923/1560 in all 285**. Both pairs are **NEVER TOUCHED** —
not falsified, not inert-by-mode, never tried. `0xC6446` = 5244 has been on the car since V104.

### 1d. The pole designs the brief asked for

`a = round(1024·exp(−2πf/1000))`; `b` chosen to hold DC (`b/(1024−a)` = `DC·16` = 15.84375).

| target | `0xC63EC` (a2) | `0xC63EE` (b2) | exact pole | DC gain | ΔDC | \|H\|/\|H₀\| @20 Hz | exact Nyquist asymptote |
|---|---|---|---|---|---|---|---|
| as-built | 992 | 507 | 5.05 Hz | 0.990234 | — | 1.000 | 1.000 |
| 8 Hz | **974** | **792** | **7.97 Hz** | 0.990000 | **−0.024 %** | **1.510** | 1.576 |
| 10 Hz | 962 | 982 | 9.94 Hz | 0.989919 | −0.032 % | 1.816 | 1.966 |
| 12 Hz | 950 | 1172 | 11.94 Hz | 0.989865 | −0.037 % | 2.092 | 2.361 |
| 15 Hz | 932 | 1458 | 14.98 Hz | 0.990489 | +0.026 % | 2.448 | 2.964 |
| *record's* | *932* | *1457* | *14.98 Hz* | *0.989810* | *−0.043 %* | *2.447* | *2.962* |
| *record's* | *963* | *986* | *9.78 Hz* | *1.010246* | ***+2.02 %*** | *1.829* | *1.973* |

Two corrections to the record's own numbers: its shape 3 (`963/986`) does **not** hold DC — it is +2.02 % — and the
`×2.88 asymptote` it quotes is the crude `b2` ratio `1457/507`; the exact Nyquist-limit ratio is
`(b2ₙ/b2ₒ)·(1+a2ₒ/1024)/(1+a2ₙ/1024)` = **2.962**. Neither changes a verdict.

**Feedback filter, same treatment.** Target DC 30.8911; `25 Hz → 875/2301`, `33 Hz → 832/2966`. The record's
`842/2814` is labelled "33 Hz" but its exact pole is **31.15 Hz** (DC +0.104 %).

### 1e. Overflow — the answer is no, at every design, for a structural reason

| shape | a2 | \|D_lag\| max | `a2·D_lag` max | `u·b2` max | int32 headroom |
|---|---|---|---|---|---|
| as-built 992/507 | 992 | 243,360 | 2.414e8 | 7.79e6 | **8.9×** |
| 974/792 | 974 | 243,302 | 2.370e8 | 1.22e7 | **9.1×** |
| 962/982 | 962 | 243,283 | 2.340e8 | 1.51e7 | 9.2× |
| 950/1172 | 950 | 243,269 | 2.311e8 | 1.80e7 | 9.3× |
| 932/1458 | 932 | 243,423 | 2.269e8 | 2.24e7 | 9.5× |

**Holding DC holds the state magnitude** — `D_lag,ss = b2·u/(1024−a2) = 15.84375·u` for *every* DC-held design — so the
headroom is invariant, and it is if anything slightly *better* at a higher pole. The recursion is a first-order lowpass
with `0 < a2/1024 < 1` driven by a bounded input, so `|D_lag|` never exceeds that steady state.

**The one place a short truncation could bite** is `sxh r9` at `0x0002A1EC`. Bound: `|lag_out| ≤ DC·|u| = 15210`,
`G_fb ≤ 46080` ⇒ `|v| ≤ 21389 < 32767`. **The same bound at every pole, again because DC is held.** Downstream the
±3072 clamp on `gp-0x6b38` binds at `|v| > 18830`, i.e. 88 % of that bound — but measured 427 saturation on
r39/r3a/r3c is **0.0000 %**, so it is not live. The P clamp (15360), the PID-sum clamp (15360) and the Kd clamp (10240)
are all upstream of the lag and all bounded by the 15360 the table above uses. **No design overflows anything.** [EVIDENCE]

The **fb** filter's input is band-guarded to `|x| ≤ 12000` at the function entry; steady state `15.44554·x` = 185,347,
`a·D` = 1.71e8, headroom 13×. Its output clamp (46080) binds at `|x| ≥ 1492` counts, **the same `|x|` for every DC-held
fb design**, so even the clamp's duty is invariant to the fb pole.

---

## 2. Deliverable B, part 1 — the plant-free damping budget, re-ranked

Method unchanged from the record: every lane enters the 1 kHz aggregator with a unit coefficient, so lane phasors add
directly; `Re` re the wheel rate is damping. A lag-pole shape rotates and scales the LKAS lane **exactly** by
`H_lag,new/H_lag,old` and **does not touch r24 at all** (r24 is `FUN_0003aa2c`, which never reads `0xC63EC/EE`). Measured
inputs are the record's §2 phasors; `s = 0.43`, the median of the V282 cave-bit inversions (0.41–0.52 on r39,
0.42/0.43 on r36–r38).

| shape | cells | Re@7 Hz | Re@20 Hz | ×base@20 | \|C\|@20 | DC auth |
|---|---|---|---|---|---|---|
| **as-built V282** | — | **−0.23** | **+2.06** | 1.00 | 1.90 | 0.9902 |
| lag pole → 8 Hz | **974/792** | **+0.69** | **+2.75** | **1.33** | 2.87 | 0.9900 |
| lag pole → 10 Hz | 962/982 | +1.15 | +3.27 | 1.59 | 3.45 | 0.9899 |
| lag pole → 12 Hz | 950/1172 | +1.49 | +3.81 | 1.85 | 3.97 | 0.9899 |
| lag pole → 15 Hz | 932/1458 | +1.84 | +4.59 | 2.22 | 4.65 | 0.9905 |
| fb pole → 25 Hz (gain-only reading) | 875/2301 | +0.11 | +2.64 | 1.28 | 2.33 | 0.9902 |
| fb pole → 33 Hz (gain-only reading) | 832/2966 | +0.26 | +3.03 | 1.47 | 2.55 | 0.9902 |
| `0xC6446` → 2048 alone | `0xC6446` | +0.62 | +1.22 | **0.59** | 1.90 | 0.9902 |
| 🛑 `0xC6446` → 512 alone | `0xC6446` | +1.04 | +0.82 | **0.40** | 1.90 | 0.9902 |

**DC authority is unchanged at every row** — the whole point of holding `2b/(1024−a)/32`. The 7 Hz column changes
**sign** at every lag-pole dose: the as-built budget is a mild net pump (−0.23) and an 8 Hz pole makes it a net damper
(+0.69). Across the entire measured range of `s` (0.30–0.52) the 8 Hz row stays positive at 7 Hz (+1.12 → +0.40) and
rises at 20 Hz (+2.34 → +3.04), so **the ranking does not turn on `s`.**

---

## 3. Deliverable B, part 2 — 🛑 the Nyquist crossing, and why the record's shape is a DO-NOT-FLASH

`LOOP-MODEL-CONVENTION-DEFECT-2026-09-04` §3 forbids a single closed-loop `|T(f)|` curve and §4 licenses model (a) for
gain-margin and blind-band questions in 20–32 Hz. I use it there and nowhere else. It is `zn_ku_corrected.py`'s model,
re-implemented and **re-anchored on the as-built filters**: `PH_G20` and `KMAG` are plant properties, computed once
from the as-built filters and then held fixed while the filters change. The base row reproduces the addendum exactly
(f(−180°) = 28.1 Hz, `|L|` = 0.564, GM 1.77×, 5.0 dB) and the implied plant phase at 20 Hz (−76.7°) agrees with
creep20's independent −73° at 22 Hz to 3.7°.

| shape | f(−180°) | \|L\| there | **GAIN MARGIN** | GM dB | vs base | Kp-equivalent | flown? |
|---|---|---|---|---|---|---|---|
| **as-built V282** | 28.1 Hz | 0.564 | **1.77×** | 5.0 | 1.00 | Kp 248 | yes |
| lag 6.02 Hz 986/602 | 28.5 Hz | 0.659 | 1.52× | 3.6 | 0.86 | Kp 396 | yes |
| lag 6.50 Hz 983/650 | 28.7 Hz | 0.706 | 1.42× | 3.0 | 0.80 | Kp 453 | yes |
| lag 7.15 Hz 979/713 | 29.0 Hz | 0.769 | 1.30× | 2.3 | 0.74 | Kp 518 | yes |
| **lag 7.97 Hz 974/792** | **29.3 Hz** | **0.841** | **1.19×** | **1.5** | **0.67** | **Kp 589** | **yes** |
| lag 9.94 Hz 962/982 | 30.0 Hz | 1.010 | **0.99×** | −0.1 | 0.56 | Kp 732 | **no** |
| lag 11.94 Hz 950/1172 | 30.7 Hz | 1.167 | **0.86×** | −1.3 | 0.48 | Kp 851 | **no** |
| 🛑 **lag 14.98 Hz 932/1458** | 31.7 Hz | 1.384 | **0.72×** | −2.8 | 0.41 | **Kp 1003** | **no** |
| lag 12 Hz + fb 25 Hz | 32.9 Hz | 1.494 | 0.67× | −3.5 | 0.38 | — | no |
| lag 15 Hz + fb 33 Hz | 35.4 Hz | 2.059 | 0.49× | −6.3 | 0.27 | — | no |
| `0xC6446` → 2048 or 512 | 28.1 Hz | 0.564 | 1.77× | 5.0 | 1.00 | Kp 248 | — |

**The mechanism.** Raising the pole adds phase lead (good) and gain (bad) in the *same* band. The lead pushes the
crossing up in frequency, but with the pole at 10–15 Hz the lane no longer rolls off there, so `|L|` at the *new*
crossing is **higher**, not lower. Gain wins.

**⭐ The Kp-equivalent column is what makes any of this actionable.** The same model gives Kp 696 — the top of the stock
LERP, flown by every build before V281 rev 3 — a gain margin of **1.04×**, and creep20 *measures* GM 1.32× at Kp 470.
So the model's absolute scale is pessimistic by at least 1.7×, and "GM 1.19×" is a margin this car has driven at.
🛑 **Two things keep that from being a licence:** the stock LERP only reaches its top on high-demand-index frames, so
that exposure was brief, whereas a pole change is always-on; and the Kp 470 crossing was at 22.4 Hz where the 0x18F
streams still read, whereas a pole raise puts it at 29–32 Hz where nothing resolves frequency.

**The joint (pole, Kd) frontier is empty.** A Kd cut removes HF gain and could in principle pay for the pole; the 7.3 Hz
ring blocks Kd below ~118, but the pole raise itself cuts the ring and buys that headroom. I ran the full grid with
**both gates held at today's values** (GM ≥ 1.77× and `|L_tot|`(7.3) ≤ 0.980). **The only admissible point is the
as-built one.** At any given `Re@20`, as-built has the best margin. The waterbed is real and the pairing does not beat it.

---

## 4. Deliverable B, part 3 — crossover, phase margin and \|S\|, and the waterbed

Model (a) is anchored at 20 Hz, so the crossover region is the one place it may speak about `|S| = 1/|1+L|`. I report it
there and produce **no** full closed-loop curve.

| shape | f crossover | PM | \|S\|@18 | \|S\|@20 | \|S\|@22 | **Ms (12–50 Hz) @ f** |
|---|---|---|---|---|---|---|
| **as-built V282** | 12.4 Hz | +77.8° | 1.32 | **1.61** | 1.93 | **2.38 @ 26.3 Hz** |
| lag 6.02 Hz | 16.0 Hz | +61.7° | 1.20 | 1.51 | 1.93 | 3.06 @ 27.2 Hz |
| lag 6.50 Hz | 17.8 Hz | +53.4° | 1.13 | 1.43 | 1.88 | 3.55 @ 27.6 Hz |
| lag 7.15 Hz | 20.2 Hz | +42.6° | 1.05 | 1.33 | 1.77 | 4.48 @ 28.1 Hz |
| **lag 7.97 Hz** | **23.3 Hz** | **+29.2°** | **0.96** | **1.21** | **1.60** | **6.56 @ 28.7 Hz** |
| lag 9.94 Hz | 30.4 Hz | −1.8° | 0.78 | 0.96 | 1.24 | **102.6 @ 30.1 Hz** |
| lag 14.98 Hz | 47.7 Hz | −73.9° | 0.54 | 0.63 | 0.76 | 2.73 @ 32.8 Hz |
| `0xC6446` → 2048 or 512 | 12.4 Hz | +77.8° | 1.32 | 1.61 | 1.93 | 2.38 @ 26.3 Hz |

The as-built row lands inside creep20's identified `Ms` 2–2.9, which is the check that the model is being used where it
is anchored. 🛑 **Note where the as-built peak already is: 26.3 Hz, not 20 Hz.** Every dose cuts 18–22 Hz and grows
26–33 Hz. That is the finding, and it is why I will not describe any of these shapes as a cure.

**A note on the two frames.** `GRINDING-DEEP-ANALYSIS` §2 concludes the 20 Hz line is a **driven, lightly damped mode**
(aggregator net-damping at 20 Hz), while the memory `accord-the-creep-grind-is-the-lkas-rate-loop-crossover-resonance`
calls it the loop's own **crossover resonance**. Those are different mechanisms and the record carries both. **They
happen to agree on the direction of this lever** — raise the pole — and disagree on the size and the risk accounting.
I report both (§2 damping budget, §4 sensitivity) and pick the dose on the *risk* side, which is the conservative one.

---

## 5. Deliverable B, part 4 — the blind band, and what the edit would decide

| shape | mean \|L\| 25–50 Hz | × base | \|H\| rise @20 | **blind increment** (rise above 25 Hz) |
|---|---|---|---|---|
| as-built | 0.452 | 1.00× | 1.00× | 1.00× |
| 974/792 | 0.702 | 1.55× | 1.51× | **1.04×** |
| 962/982 | 0.863 | 1.91× | 1.82× | 1.08× |
| 932/1458 | — | 2.46× | 2.45× | 1.14× |

The r36–r38 read's correction stands: **only ×1.04–1.14 of the total gain rise happens above 25 Hz**, not ×2.9. The
danger is not the unobservable *increment*; it is that the sensitivity **peak** relocates into 26–33 Hz, where 0x18F
carries band **energy** but not resolvable frequency (`TASK5`: energy endpoints safe above 25 Hz, frequency endpoints
unsound — adequate for a guard, since a rise is bad whatever its true frequency).

**⭐ And that is exactly what makes the edit worth cutting.** The two plant models make different, measurable
predictions for the 26–33 Hz motion:

| shape | 26–33 Hz × under **DELAY** plant | under **FROZEN** plant | **separation** | 18–22 Hz × (delay / frozen) |
|---|---|---|---|---|
| 986/602 | 1.257 | 1.053 | 1.19× | 0.946 / 0.939 |
| 983/650 | 1.435 | 1.065 | 1.35× | 0.904 / 0.895 |
| 979/713 | 1.739 | 1.062 | 1.64× | 0.842 / 0.832 |
| **974/792** | **2.281** | **1.034** | **2.21×** | 0.764 / 0.755 |
| 962/982 | 6.313 | 0.893 | 7.07× | 0.605 / 0.601 |

Against that band's measured route-to-route spread of **1.25×** on unchanged firmware (§6), a 2.21× separation is a
**decidable experiment**. Deciding it settles the premise behind `Ku = 227`, behind every high-frequency risk verdict
in this kit, and behind the V255/V269 post-mortem.

---

## 5b. 🛑 The oscillation-reversal detector — a second, independent ceiling

Script: `rlog-tools/studies/grind/grind1_detector_margin_v287.py` → `_scratch/grind1_detector_margin_v287.txt`.

**What it is** [EVIDENCE, tracer 2026-09-06]. `FUN_000428d4` watches `gp-0x6c2c`, a doubly-filtered
derivative of motor **rotor angle** — the MOTION side, not the torque path. It counts alternate crossings of
±`cal(0xC620A)` = **12800** (40 % of that signal's own full scale of 32000) and **resets the counter if
`cal(0xC64DD)` = 50 ticks pass between crossings**, so it can only ever count content **faster than 10 Hz**.
After 15 / 20 / 25 reversals (`0xC694C/E/0xC6950`) a LERP at `0xC694A` cuts assist by up to 40 %; the factor
reaches governor slot 2, is MIN-folded into the Q15 motor-demand scale and slew-limited, for a net **×0.600
on motor demand**. It is **live and engaged-relevant**, speed-gated `gp-0x6a5e ≤ 960`.

**Its own input filter is `0xC40DC`, and V282 already moved it** (14 vs stock 22, corner 39.4 vs 67.1 Hz):

| f Hz | 5 | 10 | 20 | 25 | 28 | 30 | 33 | 40 | 50 |
|---|---|---|---|---|---|---|---|---|---|
| V282 a=14 | 0.992 | 0.969 | 0.892 | 0.845 | 0.815 | **0.796** | 0.767 | 0.703 | 0.620 |
| stock a=22 | 0.997 | 0.989 | 0.959 | 0.938 | 0.924 | 0.914 | 0.899 | 0.861 | 0.805 |

Only **2.0 dB down at 30 Hz** — it does **not** protect against the rise this lever creates.

**The replay.** Each dose's closed-loop sensitivity ratio and the detector's input filter are applied to the
measured 0x18F wheel rate over **19 windows** (creep runs on r39/r3a/r3c/r35 plus the two r39 bookmark
episodes), and the detector's counter is mirrored exactly. Because the true threshold sits at an unknown
fraction of the signal, the threshold is fixed at a fraction `q` of each window's own baseline peak and swept.

Mean maximum reversal run, by threshold fraction `q`, and the number of the 19 windows that reach the
firing count of 15:

| dose | peak abs(d) x | q=0.10 | q=0.15 | q=0.20 | q=0.30 | q=0.50 | q=0.70 | **windows reaching 15** |
|---|---|---|---|---|---|---|---|---|
| as-built V282 | 1.000 | 1.9 | 1.5 | 1.3 | 1.3 | 1.0 | 1.0 | **0 of 19 at every q** |
| lag 6.0 Hz 986/602 | 0.984 | 2.1 | 1.5 | 1.4 | 1.3 | 1.0 | 1.0 | 0 of 19 at every q |
| lag 6.5 Hz 983/650 | 0.980 | 2.1 | 1.6 | 1.4 | 1.3 | 1.1 | 1.0 | 0 of 19 at every q |
| lag 7.2 Hz 979/713 | 0.981 | 2.5 | 1.6 | 1.4 | 1.4 | 1.2 | 1.0 | 0 of 19 at every q |
| **lag 8.0 Hz 974/792** | **1.000** | **3.3** | **2.3** | **1.6** | **1.5** | **1.3** | **1.0** | **0 of 19 at every q** |
| 🛑 lag 10 Hz 962/982 | 1.354 | **43.4** | **37.2** | **31.8** | **18.7** | **6.6** | 3.7 | **15 / 14 / 14 / 8 / 4 / 1 of 19** |
| lag 12 Hz 950/1172 | 0.912 | 2.6 | 1.9 | 1.4 | 1.2 | 1.0 | 1.0 | 0 of 19 *(artefact — see below)* |
| lag 15 Hz 932/1458 | 0.831 | 1.4 | 1.2 | 1.1 | 1.0 | 1.0 | 0.9 | 0 of 19 *(artefact)* |

⭐ **THE MARGIN TO 12800 IS NOT THE BINDING QUANTITY, AND THAT IS THE CLEANEST FORM OF THE ANSWER.** Sweeping
the threshold from 10 % to 70 % of each window's own peak changes nothing: every admissible dose reaches
**0 of 19** at *every* threshold, and the 10 Hz dose reaches 15 in **15 of 19** windows at the lowest one. The
detector is blocked today by **persistence, not amplitude** — today's motion simply does not contain 375 ms of
sustained faster-than-10 Hz reversals, and lowering the threshold does not create them. So the answer does not
depend on where 12800 sits relative to the unknown scale, which is exactly the uncertainty I could not
otherwise close. What the 10 Hz pole adds is the *persistence*, by creating a narrow, marginally stable
sensitivity peak at 30 Hz.

**Three readings, and the first is the one that matters.**

1. **The chosen dose does not spend detector margin.** Peak `abs(d)` is unchanged (x1.000) and no window comes
   near 15 reversals. The peak barely moves at any dose because it is carried by low-frequency motion the
   edit does not touch; what the edit changes is the **persistence** of >10 Hz reversals, which is exactly
   what the detector counts.
2. 🛑 **At a 10 Hz pole the detector would FIRE**, in 8 of 19 windows — a live x0.600 authority cut arriving
   375-500 ms into a grind episode, mid-drive. That is a second, independent reason 962/982 and above are
   out, and it agrees with the gain-margin ceiling to within one step.
3. ⚠ **The 12 and 15 Hz rows are an ARTEFACT and must not be read as safety.** `|S| = 1/|1+L|` describes a
   *stable* loop; at GM 0.86x and 0.72x the closed loop has right-half-plane poles and the formula is simply
   not a description of anything. The informative row is 10 Hz, where GM is about 1 and the formula is still
   marginally meaningful — and there the answer is that the detector fires.

**The proxy, stated as BELIEF.** `gp-0x6c2c` is rotor rate; I have column/wheel rate. Between them sit the
worm gear (a scale, harmless to a ratio) and the column's torsional compliance, which at 20-33 Hz lets the
rotor move **more** than the wheel. So a true rotor-rate spectrum carries **more** relative high-frequency
content than my proxy, and every 26-33 Hz number above is an **under-estimate** of the detector's true
exposure. The direction of that error is the conservative one for a risk statistic, and that is what I am
relying on — not the proxy's accuracy. Absolute firing cannot be predicted: no firmware factor links rotor
rate to anything on the wire, so the counts-per-deg/s scale is unknown and **everything above is a ratio**.

---

## 5c. Should the build spend a cave bit on the detector? — NO, and here is the costing

**The only buildable rung** is `bit = (abs(gp-0x6c2c) >= abs(gp-0x6c2e))`, the fast 39.4 Hz EMA against the
slow 3.8 Hz EMA of the same rotor-rate signal — scale-free, evaluated at full precision at 1 kHz inside the
cave, and **not alias-limited the way 0x18F is**. On paper that is exactly the doctrine's "compare, don't
measure" form, aimed at exactly the band this build's risk lives in.

**It is two halfwords, not four, and it costs bit 5 — not a legacy bit.** Read from the image, the cave's
five rungs are:

| offset | instruction | bit | form |
|---|---|---|---|
| `0xC4B34` | `ld.h -0x6ADA, gp, r6` | 6 operand A (r24) | two-operand comparator, 0x2E bytes |
| `0xC4B40` | `ld.h -0x6B38, gp, r6` | 6 operand B (T) | |
| `0xC4B62` | `ld.h -0x6ADA, gp, r6` | 5 operand A (r24) | two-operand comparator |
| `0xC4B6E` | `ld.h -0x6B94, gp, r6` | 5 operand B (aggregator) | |
| `0xC4B92` | `ld.h -0x6B4C, gp, r6` | 7 sign(11-slot assist sum) | **single operand**, ~10 B |
| `0xC4B9C` | `ld.h -0x6ADA, gp, r6` | 4 sign(r24) | **single operand** |
| `0xC4BA8` | `ld.w -0x3680, gp, r6` | 3 sign(gp-0x3680) | **single operand** |

The legacy bits 3 and 7 are **single-operand sign rungs**; converting one into a comparator needs about +0x22
bytes of new instructions, a length change and a relocation — **not the V282 class of edit**, and I do not
propose it. (Note `0xC4BA8`'s hw2 is `C981`: displacement bit 0 is the `ld.h`/`ld.w` opcode select, so it is
a *word* load of `-0x3680`. That is the `hw2 = disp|1` trap, confirmed here, and it is why the record calls
the cell `gp-0x3680` and not `gp-0x367f`.)

**The exact edit, costed so the option is on the table:**

| offset | now | becomes | operand |
|---|---|---|---|
| `0xC4B64-65` | `26 95` (hw2 `9526`, gp-0x6ADA) | `d4 93` (hw2 **`93D4`**, gp-0x6C2C) | bit 5 A |
| `0xC4B70-71` | `6c 94` (hw2 `946C`, gp-0x6B94) | `d2 93` (hw2 **`93D2`**, gp-0x6C2E) | bit 5 B |

`hw1` stays `3724` at both sites; both new displacements are even, so both stay `ld.h`. Four bytes,
read-only, no length change, no relocation. Recompute the page CRC at `0xC4FFC`.

**🛑 MY RECOMMENDATION IS NOT TO DO IT, on four grounds:**

1. **The rung cannot resolve this dose.** Predicted duty on the replay: **0.5604 baseline, then x0.997 /
   0.996 / 0.998 / 1.013** at 6.0 / 6.5 / 7.2 / **8.0** Hz, against a **1.53x baseline spread across the 19
   windows** (0.4757 to 0.7296). It only moves at 10 Hz (x1.26), the dose that is already excluded twice
   over. A rung that is flat over the whole admissible range is not an instrument for this build.
2. **The guard already on the wire is far more sensitive**: 0x18F `26-33 / 2-6` has a **1.25x** spread and a
   **x2.58** prediction at the chosen dose.
3. **Detector firing needs no new instrument at all.** The cut lands on motor demand *downstream* of the
   aggregator, so it shows as a **x0.600 step in motion per unit delivered torque** — the 0x18F rate against
   the existing 427 tap, 375-500 ms after a grind onset. That is registered below as **P9**, and it reads the
   exact event, not a proxy for it.
4. **It changes the build's risk class** from cal-only to cal plus a code-region edit, for no measurement gain.

**The condition under which this flips**, stated so it is not lost: **if the chosen dose is moved to 9 Hz or
above**, the rung's prediction rises past its spread *and* the 0x18F guard becomes unreliable because the
action moves to about 30 Hz where 0x18F cannot resolve frequency. At that dose, spend bit 5. At 974/792, do not.

---

## 6. Endpoint selection — 🛑 which statistics can actually resolve this, measured on the wire

r39, r3a and r3c are all V282, so their spread on any statistic is pure exposure plus measurement noise. Stratum:
engaged lateral (`SCA ∧ STEER_REQUEST`), `vEgo` 1–3 m/s, `|bar| < 400` raw, runs ≥ 2 s. All streams de-jittered onto
their nominal frame counters first.

| endpoint (0x18F wheel rate) | r39 | r3a | r3c | **spread** | pred ×, 6.5 Hz | 7.2 Hz | **8.0 Hz** | 10 Hz |
|---|---|---|---|---|---|---|---|---|
| 18–22 Hz raw | 1.1474 | 0.5399 | 1.3512 | **2.50×** | 0.904 | 0.842 | 0.764 | 0.605 |
| 18–22 / 2–6 | 0.5877 | 0.3729 | 1.0814 | 2.90× | 0.976 | 0.930 | 0.862 | 0.709 |
| 18–22 / rms | 0.3462 | 0.1631 | 0.3148 | 2.12× | 0.904 | 0.842 | 0.764 | 0.605 |
| 18–22 / 6–9 | 2.0512 | 0.5845 | 1.9083 | 3.51× | 1.040 | 1.015 | 0.968 | 0.839 |
| ⭐ **18–22 / 26–33** | 2.7662 | 1.3879 | 3.9834 | 2.87× | 0.630 | 0.484 | **0.335** | 0.096 |
| 26–33 raw (GUARD) | 0.4148 | 0.4841 | 0.3392 | 1.43× | 1.435 | 1.739 | 2.281 | 6.313 |
| ⭐ **26–33 / 2–6 (GUARD)** | 0.2596 | 0.3240 | 0.2814 | **1.25×** | 1.548 | 1.920 | **2.577** | 7.401 |
| 33–40 / 2–6 (SHELF) | 0.2140 | 0.1962 | 0.2298 | 1.17× | 1.226 | 1.331 | 1.468 | 1.802 |

**Read it as: an endpoint is usable only where the predicted change clearly exceeds the spread.** Three consequences,
and they set the dose:

1. **The 18–22 Hz raw amplitude cannot resolve any safe dose.** ×0.76 against a 2.50× spread licenses nothing.
2. **`18–22 / 26–33` can, at 8 Hz and not below**: ×0.335 is a 2.99× change against a 2.87× spread. It works *because*
   of the waterbed — numerator down, denominator up.
3. **The GUARD is the most resolvable statistic on the car**, spread 1.25× against a predicted 2.58×. The cost of this
   build is measurable to much higher confidence than its benefit. That asymmetry is honest and it is the reason to
   frame the build as a discriminator.

**Two statistics the brief asked me to pre-register that DO NOT WORK, reported rather than dressed up:**

- **T-re-rate phase at 20 Hz.** Measured on the V282 wire (Welch, 128-sample windows at 50 Hz, rate on the tap's own
  instants): **r39 −114.8° (coh 0.85, 4 windows), r3c −114.5° (0.87), r3a −85.2° (0.98, 2 windows), r35 −111.9° (0.87)**.
  The route-to-route spread is ~30°. The predicted rotation is **+3.8° at 6.5 Hz, +5.4° at 7.2, +7.4° at 8.0, +22.4° at
  15**. Only the 15 Hz dose would be resolvable, and that one is a do-not-flash. ⚠ These numbers also disagree with the
  record's −69° by 46° — see open item 2.
- **Bit-6 duty (`|r24| ≥ |T|`).** r24 is untouched by a lag-pole edit, so the whole move is on `|T|`; but the 18–22 Hz
  line is a small part of the tap's total power, so the tap's RMS barely moves. Predicted duty (lognormal quantile,
  `sd(ln |r24|/|T|) = 1.68` fitted to the r39 gain-ladder replay, which it reproduces to 0.005): r39 0.0906 →
  **0.0877 at the chosen dose, 0.0822 even at 15 Hz**; r3c 0.0621 → 0.0602 / 0.0571. **A ×0.97 duty change is not an endpoint.**

**Every instrument named above is already on the wire in V282** — 0x18F bar and rate (stock, always on), the 427
delivered-torque tap on `gp-0x6b38`, and 0x14A byte 4 bits 4/5/6 from the V105 cave as repointed by V282. **The build
below is cal-only and needs no new probe.** [EVIDENCE — the V282 cave is byte-identical to V283's and both flew;
route-wide bit-6 duty 0.114/0.154/0.156 on r39/r3a/r3c against exactly 0.0000 on r34/r35's old decode.]

---

## 7. Deliverable C — the ONE build, and its pre-registration

### V287 = V282 + two halfwords

| addr | tp offset | cell | now | **becomes** | effect |
|---|---|---|---|---|---|
| `0xC63EC` | `tp+0x73ec` | output-lag pole `a2` | 992 | **974** | pole 5.05 → 7.97 Hz |
| `0xC63EE` | `tp+0x73ee` | output-lag gain `b2` | 507 | **792** | holds DC at 0.990000 (−0.024 %) |

🛑 **PRE-FLASH GATE, and the build must not be cut until it is closed:** `0xC63EC` and `0xC63EE` each have
a **second reader** at `0x2A892` / `0x2A8A2`, inside the orphan `0x2A400-0x2B600` region that is **not all
dead**. Resolve those two readers first (`create_function` at `0x2A892` in a **scratch** import, never the
shared project, then decompile). If they are live, these cells are not private and the edit silently moves a
second lane — a GATE 1 ownership failure, and the build is off.

✅ **GATE CLOSED, 2026-09-06** [EVIDENCE — `firmware-codepath-tracer`, memory `reference_accord_gate1_pole_cells_unreachable_dispose_is_a_return`]. The second readers at `0x2A892` / `0x2A8A2` are **UNREACHABLE**: `0x2A504`, the target of every `jr` from `FUN_0002a30e`, is a `dispose ..., lp` — a RETURN — so there is no fall-through into the duplicate block at `0x2A508`, zero branches enter it from outside (a 7-of-7-controlled scan, every raw hit adjudicated as a `prepare` prologue) and no immediate can construct its entry. **The lag poles pass GATE 1 and are private in effect.** Proved with dry-run disassembly and raw Python only; no Ghidra mutation and `save_program` not called.


**Base:** V282, on the car and confirmed on the wire. **Cal-only. No code byte. No authority change** — DC gain held to
0.024 %, the P/PID-sum/Kd clamps untouched, the ±3072 output clamp untouched, `0xC6446` untouched, Kp flat 248
untouched, Ki 0 untouched, Kd 128 untouched. **Never-touched cells: 992/507 in all 285 images.**
The build script must recompute the calibration page CRC and re-read both halfwords back from the built image.

### What it does, read from the arithmetic

| quantity | as-built | V287 | note |
|---|---|---|---|
| DC authority | 0.990234 | 0.990000 | −0.024 % |
| lane gain \|H_lag\| @ 7 / 20 / 30 / ∞ Hz | 1.00 | 1.28 / 1.51 / 1.55 / 1.58 | blind increment ×1.04 |
| lane phase lead @ 7 / 20 / 30 Hz | 0° | +12.9° / +7.4° / +5.3° | |
| aggregator Re@7 Hz (loaded) | −0.23 (pump) | **+0.69 (damp)** | sign flips at every `s` in 0.30–0.52 |
| aggregator Re@20 Hz (creep) | +2.06 | **+2.75** | ×1.33 |
| model (a) gain margin | 1.77× @ 28.1 Hz | **1.19× @ 29.3 Hz** | Kp-equivalent 589; stock LERP top is 696 |
| crossover / PM | 12.4 Hz / +77.8° | 23.3 Hz / +29.2° | |
| \|S\| @ 18 / 20 / 22 Hz | 1.32 / 1.61 / 1.93 | 0.96 / 1.21 / 1.60 | |
| detector peak abs(d) | — | **x1.000** | reversal-run replay, 19 windows |
| detector windows reaching 15 reversals | 0 of 19 | **0 of 19** | 8 of 19 at a 10 Hz pole |
| Ms (12–50 Hz) | 2.38 @ 26.3 Hz | **6.56 @ 28.7 Hz** | 🛑 the cost |
| 7.3 Hz ring \|L_tot\| | 0.980 | **0.822** | ratio 0.839 |
| int32 headroom / `sxh` bound | 8.9× / 21389 | 9.1× / 21389 | unchanged by construction |

### 🛑 Risk, stated before the drive

**Authority is unchanged; the risk is a NEW, HIGHER-PITCHED vibration.** The predicted 26–33 Hz motion rises **×2.28**
and the modelled sensitivity peak grows from 2.38 at 26.3 Hz to **6.56 at 28.7 Hz**. Under the optimistic plant that
rise is only ×1.03 and there is no new peak — **the drive is what decides between those two, and the operator should be
told he may feel a buzz roughly half an octave above today's grind.** The gain margin falls to a modelled 1.19×, which
is a margin this car flew for 280 builds at the top of the stock Kp LERP, but always-on rather than on high-index
frames only. **If anything feels worse in any way, stop the drive.**

### Pre-registration — do not move a threshold after the log lands

Stratum for every statistic: **engaged lateral, hands-off (`|bar| < 400` raw), `vEgo` 1–3 m/s**, contiguous runs ≥ 2 s,
all streams de-jittered onto their nominal frame counters. Comparators: **r39, r3a, r3c** (all V282), and r35 (V281 r3).

| # | statistic | today (r39 / r3a / r3c) | **predicted on V287** |
|---|---|---|---|
| **P1** | 0x18F rate **18–22 / 26–33** band ratio | 2.766 / 1.388 / 3.983 | **× 0.335** (median → ~0.93) |
| **P2 (GUARD)** | 0x18F rate **26–33 / 2–6** | 0.2596 / 0.3240 / 0.2814 | **× 2.58** (delay plant) or **× 1.03** (frozen plant) |
| **P3 (SHELF)** | 0x18F rate **33–49.9 / 2–6** | 0.2140 / 0.1962 / 0.2298 | **× 1.47**, and must not exceed ×2.0 |
| **P4 (RING)** | 7.3 Hz episode `\|L_tot\|`, same estimator as the n = 8 pool | 0.980 [0.971–0.983] | **0.822**; **FAIL if ≥ 0.980** |
| **P5** | 0x18F rate 18–22 Hz raw | 1.147 / 0.540 / 1.351 | × 0.76 — **reported, not decisive** (2.50× spread) |
| **P6** | ∠(T/rate) @ 20.31 Hz | −114.8° / −85.2° / −114.5° | **+7.4°** → −107.4 / −77.8 / −107.0 — **not decisive** (30° spread) |
| **P7** | 0x14A b4 bit-6 duty | 0.0906 / 0.0345 / 0.0621 | **× 0.968** → 0.0877 / — / 0.0602 — **not decisive** |
| **P9 (DETECTOR)** | motion per unit torque: 0x18F rate 18–33 Hz over 427 T 18–33 Hz, in the 0.375–0.5 s after each grind onset | no x0.6 step in the record | **unchanged**; a x0.600 step means Honda's reversal detector fired |
| **P8** | 427 tap 18–22 Hz amplitude | 17.1 / 9.3 / 25.1 | rises ~× 1.15 (lane gain ×1.51 × motion 0.76) — **the tap moves the WRONG WAY by design; do not score on it** |

**Decision rule.**
- **P2 ≥ 2.0** ⇒ the **delay plant is confirmed in the blind band for the first time**. `Ku = 227` and every HF risk
  verdict in this kit stand; **no further pole raise is ever flyable**; the loop-shape axis for grind #1 is CLOSED and
  the next lever must be one that lowers loop gain, not one that shifts it.
- **P2 ≤ 1.3** ⇒ the **frozen plant is right above 25 Hz**. `Ku = 227` is superseded by the ~865 bound, the blind band
  is not the hazard the record treats it as, and **932/1457 (the 15 Hz pole) becomes a legitimate candidate** — cut it
  next with the same pre-registration.
- **1.3 < P2 < 2.0** ⇒ licenses nothing about the plant. Report it and gather creep exposure (open item 4).
- **P1 ≤ 0.5 AND P2 ≥ 2.0** ⇒ the waterbed is confirmed end to end: the edit moved the grind, it did not cure it.
- **P1 ≤ 0.5 AND P2 ≤ 1.3** ⇒ the only outcome in which this is a genuine improvement. Then the pole is the lever and
  the dose can be raised.

**FAIL sentence.** *The build fails if, over ≥ 20 s of engaged lateral hands-off creep, the 33–49.9 / 2–6 shelf ratio
(P3) exceeds ×2.0 of the V282 median, or the 7.3 Hz ring `|L_tot|` (P4) reaches 0.980 or above, or the 427 tap
saturation rate rises above 0.0 %, or any DTC appears that V282 did not produce. Any of those and the output-lag pole
is not a safe axis at any dose and the shape family is struck.*

**Cost FAIL — the operator's, and it outranks every number above.** *The build fails on cost if the operator reports a
new vibration, buzz or noise at a higher pitch than today's grind, or any worsening of grinding, vibrating,
micro-ratcheting, ratcheting or excess friction.* **Report symptoms in his words; the bands are only the instrument.**
**An absence of a complaint is not a report of improvement.**

**What a null licenses.** P2 landing between 1.3 and 2.0 with P1 inside its spread licenses **nothing about grinding**
and licenses only *"the 26–33 Hz band did not move enough to separate the two plant models at this dose"* — which
points at the exposure problem (open item 4), not at the lever.

**What refutes this pre-registration.** P2 rising while P1 also rises (both bands up ⇒ the edit is a broadband gain
change and the sensitivity framing is wrong); or P4 rising rather than falling (the ring's servo arm does not scale
with `H_lag` as §6d assumes, which would invalidate the whole two-arm composition).

### The alternatives, and why not

| candidate | why not |
|---|---|
| `0xC63EC/EE` = 932/1457 (15 Hz, the record's shape 2) | modelled GM 0.72×, Kp-equivalent 1003, 1.44× past anything flown. **DO NOT FLASH.** |
| `0xC63EC/EE` = 962/982 (10 Hz) | modelled GM 0.99×, Kp-equivalent 732, just past the stock LERP top. Not flown-equivalent. |
| `0xC63EC/EE` = 979/713 (7.15 Hz) | safest dose whose GM (1.30×) matches creep20's *measured* 1.32× at Kp 470 — but its plant separation is only 1.64× and P1 (×0.484) does not clear its 2.87× spread. **The drive could then only falsify, never confirm.** Name it as the half-step if the operator prefers the margin and accepts that. |
| `0xC63E8/EA` (the fb pole) | its output is rectified and multiplicative, so its phase contribution vanishes in the very stratum grind #1 lives in (headline 10). Ranked optimistically in the record. |
| `0xC6446` → 2048 or 512 | cuts `Re@20` to ×0.59 / ×0.40 and does not move `|S|` or the gain margin at all. The record's own 🛑 stands. |
| lag pole + Kd cut | the joint grid with both gates at today's values is **empty**; as-built dominates at every `Re@20`. |
| Ki | the operator rejects an integrator. Not considered. |

---

## 8. Deliverable D — what I could not close, and the exact measurement that would

| # | open | why it matters | the exact measurement |
|---|---|---|---|
| 1 | **The plant's phase and magnitude above 25 Hz** | the entire verdict bifurcates on it: GM 1.77× vs 6.76× at base, and "unstable" vs "fine" for every dose | **P2 on this build's own drive** — that is what V287 is for. Independently, a broadband-excitation drive logging the 427 tap and 0x18F rate simultaneously (still open from r39). |
| 2 | **∠(T/rate) at 20 Hz: I measure −115°, the record carries −69°** | it is the servo lane's phasor, which sets `Re@20` in §2 and every ranking derived from it. 46°, so not a sign convention | re-run `grind_loop_shape.py`'s estimator and mine on the identical pool and adjudicate; the difference is an estimator, not a stratum. **Until it is closed, §2's absolute `Re` values carry an unquantified phase error; the RATIOS between shapes do not, because the lag ratio is exact.** |
| 3 | **Whether the fb path acts linearly or as a rectified multiplier at the ripple frequency** | it decides whether shape 4 is a phase lever (record) or a pure gain lever (my reading), a ~1.5× difference in its `Re@20` | on existing logs: compare the tap's 20 Hz content, and its coherence with the rate, in creep frames stratified by **mean** wheel rate — high-mean frames should show the linear term, near-zero-mean frames only a 2f term. No build needed. |
| 4 | **Creep exposure: only 5–12 s of qualifying stratum per route** | it is why the 18–22 Hz spread is 2.50× and why the benefit endpoint barely clears it | a deliberate pass of ~5 minutes of engaged hands-off creep at 1–3 m/s **on V282, before flying anything**. It would tighten every spread in §6 and might make the smaller, safer dose decidable. **This is the cheapest thing on this list and I would do it first.** |
| 5 | **Whether the 20.3 Hz line is 20 Hz or an 80/120 Hz alias** | 80 Hz folds to 20 Hz on both a 50 and a 100 Hz sampler, so no CAN instrument separates them; if it is an alias the whole band framing moves | the audio channel at 44.1 kHz over the grind seconds, as `accord-audio-bounds-the-can-alias-risk` did once already. Free. Still open from the record. |
| 6 | **`gp-0x671d` / `gp-0x683c` untraced on the wire** | they select the `0xC6446` arm; `s = 0.43` is compatible with both readings | trace their writers in Ghidra. Unchanged from the r36–r38 read's open item 1. Does **not** affect this build, which does not touch r24. |
| 8 | **The second readers of `0xC63EC`/`0xC63EE` at `0x2A892`/`0x2A8A2`** | if live, the pole cells are not private and the build is off (GATE 1) | `create_function` at `0x2A892` and `0x2A504`/`0x2B422` in a **scratch** Ghidra import, then `decompile_function`. **This is the pre-flash gate.** |
| 9 | **The absolute scale of `gp-0x6c2c` in counts per deg/s of wheel rate** | it converts my detector ratios into an absolute margin to 12800 | nothing on the wire carries rotor rate. The fast-vs-slow cave rung would bound it, at the cost of bit 5 — costed in §5c and not recommended at this dose. |
| 7 | **`gp-0x6b2c` has 24 raw byte-scan touches against `search_instructions`' 13** | the 11 extra live in a Ghidra-undefined region that is not all dead (`0x2B422`/`0x2B57A` are `jarl`ed from `0x22530`/`0x22572`) | reported by the tracer, not acted on. It cannot affect control flow into `0x2A1FC`, so headline 8 stands, but the region should be defined and re-analysed. |

---

## 9. Files

- `rlog-tools/studies/grind/grind1_loop_shape_v287.py` → `_scratch/grind1_loop_shape_v287.txt` (§1–§4, §6)
- `rlog-tools/studies/grind/grind1_detector_margin_v287.py` → `_scratch/grind1_detector_margin_v287.txt` (§5b, §5c)
- `docs/traces/TRACE-2026-09-06-lag-and-fb-pole-census-v282.md` (the reader census and the detector trace)
- `rlog-tools/studies/grind/PREREG-V287-LOOP-SHAPE.md` (§7's pre-registration, standalone, in the `PREREG-V282-READ.md` pattern)
- `.claude/agent-memory/firmware-codepath-tracer/reference_accord_gp6b2c_addend_is_identically_zero.md` (headline 8)
- `.claude/agent-memory/firmware-codepath-tracer/reference_accord_undefined_live_code_2b422_and_gp6b2c_orphan_writers.md` (open item 7)

---

# APPENDIX A (2026-09-06, second pass) — items 2 and 3 closed, and two more lever classes priced

Scripts: `rlog-tools/studies/grind/grind1_phase_and_fb_reconcile.py` and `grind1_dclamp_and_gain_grid.py`,
stdout beside them in `_scratch/`. Analysis only; nothing built, sent or flashed.

## A1. 🛑 ITEM 2 IS CLOSED, AND IT CORRECTS ME, NOT THE RECORD

**The two numbers were never two measurements.** `grind_loop_shape.py:380` reads, verbatim:

```python
Tp = abs(Cm[i]) * np.exp(1j * np.angle(C[i]))   # magnitude MEASURED, phase MODELLED
```

`Cm` is the measured tap transfer and `C` is the modelled controller. The deep analysis's §2 phasor table
carries a **measured magnitude with a modelled phase**, and −69° is `angle(C_lkas(20 Hz))`. My −115° is a raw
measurement with **no inter-stream timing correction**, which the record applies as a hard-coded
`TAU = 3.9 ms`. [EVIDENCE — the line is in the file and its comment says so.]

**The check that settles it is at 7 Hz.** Measured on the identical V282 creep pool (44 windows, 47.7 s,
native 1 kHz resampling onto the tap's own instants):

| f Hz | 5.5 | 7.0 | 8.6 | 15.6 | 18.0 | 19.5 | **20.3** | 21.1 | 22.7 |
|---|---|---|---|---|---|---|---|---|---|
| measured angle(T/rate) | −74 | −73 | −66 | −119 | −116 | −109 | **−114** | −112 | −104 |
| coherence | 0.51 | 0.60 | 0.66 | 0.43 | 0.57 | 0.79 | **0.82** | 0.72 | 0.51 |
| model angle(C·Hlag·Hfb), Kp 248 | −36 | −42 | −46 | −59 | −63 | −64 | **−65** | −66 | −68 |

Apply the record's `TAU = 3.9 ms` (a lead of `360·τ·f` degrees): at **7 Hz** the measurement becomes
**−63.2°** against the record's modelled **−62°** — **agreement to 1.2°**. That is a strong, independent
validation of both the timing correction and the controller model, and it is why I now regard the record's
approach as sound and my raw number as the uncorrected one.

At 20.3 Hz the same correction gives **−85.8°**, leaving a 20° gap to the model. A single τ of 5.5–6.7 ms
closes 20 Hz exactly at the cost of 3–6° at 7 Hz. My own regression of the residual on frequency over
5–23 Hz is **not significant** (slope −0.51 deg/Hz, r = −0.15, **p = 0.38**; coherence-weighted −1.06 deg/Hz),
so this pool cannot pin τ better than "somewhere in 1.4–6.7 ms".

**⭐ CORRECTED CREEP-STRATUM PHASOR TABLE at 20 Hz** (|T| = 1.90 measured, r24 = 3.23·s at +5°, s = 0.43):

| phase estimate | angle | Re(LKAS) | Re(r24) | **SUM Re** |
|---|---|---|---|---|
| record as published (modelled phase) | −69.0° | +0.68 | +1.38 | **+2.06** |
| **measured, TAU 3.9 ms removed — what I now carry** | **−85.8°** | **+0.14** | +1.38 | **+1.52** |
| measured, my fitted τ = 1.41 ms removed | −104.0° | −0.46 | +1.38 | +0.92 |
| raw measured, no correction (my earlier headline 9) | −114.3° | −0.78 | +1.38 | +0.60 |

At 7 Hz the corrected measurement is −63.2° against the record's −62°, so `Re(LKAS)@7` = +1.13 vs +1.17 and
the 7 Hz budget is essentially unchanged.

**What this changes.** The record's §2 statement that the LKAS lane is *"36 % efficient as a damper"* at
20 Hz is **too generous**: on the corrected measurement the servo lane is **near-pure quadrature**
(Re +0.14 of magnitude 1.90, i.e. 7 % efficient), and **essentially all of the aggregator's 20 Hz damping
is r24's**. The sum falls from +2.06 to **+1.52**. Nothing in the §3/§4 *ranking* changes sign, and the
lag pole's benefit at 20 Hz survives (+0.14 → +0.58 at 974/792). ⚠ But it is **not robust to τ**: at
τ = 0 the lane sits past −90° and the lag pole's 20 Hz benefit turns marginally **negative**. I flag that
as the residual, and it is why the build's case now leans on the sensitivity frame and the 7.3 Hz ring
rather than on the damping budget. **I withdraw my headline 9's implication that the record is wrong; the
record is defensible and my raw number was uncorrected.**

## A2. ITEM 3 (the fb filter's form) IS CLOSED — it is a GAIN, not a PHASE

Stratifying the same creep pool on the window-local mean |wheel rate| (the second, linearised term is
proportional to `sign(rate_slow)` and vanishes as the mean goes to zero):

| stratum | windows | s | \|T/rate\|@20 | **angle@20** | coh | angle@7 |
|---|---|---|---|---|---|---|
| near-zero, mean \|rate\| < 2 deg/s | 17 | 17.8 | 12.30 | **−103.9°** | 0.75 | −76.9° |
| low, 2–5 deg/s | 2 | 2.0 | 9.42 | −122.7° | 0.43 | −43.8° |
| mid, 5–12 deg/s | 1 | 1.6 | 15.75 | **−100.6°** | 1.00 | −64.2° |
| high, > 12 deg/s | — | — | no data in this stratum | | | |

The two strata with usable coherence agree to **3.3°**. If the fb path were linear in the loop, the
second term would add `angle(H_fb(20)) = −50.9°` on top of the first term's −76.0° in the high-mean
windows and nothing in the zero-mean ones — **tens of degrees**, and in opposite directions for left and
right turns. It is not there. ⚠ The exposure is thin (1.6 s in the mid stratum) so this is
suggestive rather than conclusive, but it agrees with the byte-level structure.

⇒ **The fb pole is a GAIN lever, not a phase lever, in the stratum grind #1 lives in.** Shape 4 as ranked
in the record (Re@20 4.04, a phase rotation of +17.7°) is **optimistic**; the defensible reading is
×1.34 of lane gain at 20 Hz and no rotation — a pure loop-gain rise with none of the phase benefit.
**Item 3 closed; shape 4 struck as a phase lever.**

## A3. ⭐ ITEM 3b — THE D CLAMP IS THE MOST PROMISING UNTRIED CLASS, AND IT IS NOT CLOSED

A clamp is **invisible to the small-signal loop**: below it the transfer function is unchanged, so there
is **no waterbed, no gain-margin change, no sensitivity-peak relocation and no blind-band rise**. The only
question is whether the D term actually reaches it. Run on the byte-exact 1 kHz chain mirror
(`grind_incident_r35.simulate`, the same code the r35 incident analysis used):

**The D term ALREADY BINDS at today's 10240.** [EVIDENCE]

| window | s | p50 \|D\| | p99 \|D\| | max \|D\| | bind % @10240 | @5120 | @2560 | @1280 |
|---|---|---|---|---|---|---|---|---|
| **r35 t 1010–1025, the 23:48:21 GRIND INCIDENT** | 15.0 | 896 | 15,746 | **35,056** | **3.67** | 9.06 | 17.62 | 39.28 |
| r39 bookmark 1 episode | 20.0 | 496 | 12,336 | 47,408 | 1.47 | 3.54 | 9.08 | 23.22 |
| r39 bookmark 2 episode | 20.0 | 544 | 16,618 | **99,363** | 2.06 | 4.16 | 11.81 | 26.85 |
| r3c loudest creep window | 2.4 | 336 | 4,380 | 13,968 | 0.23 | 0.70 | 2.65 | 8.15 |
| r39 loudest creep window | 2.5 | 400 | 6,993 | 17,120 | 0.72 | 1.63 | 4.38 | 12.48 |

Max |D| reaches **10× the clamp**. So the class is emphatically **NOT** closed by "the D never gets there".

**Open-loop effect on T's 18–22 Hz envelope** (the mirror runs on the measured rate):

| window | D=10240 | D=5120 | D=2560 | D=1280 |
|---|---|---|---|---|
| r35 grind incident | 77.0 | 62.3 (×0.81) | **48.6 (×0.63)** | 40.2 (×0.52) |
| r39 bookmark 1 | 57.0 | 50.1 (×0.88) | 41.0 (×0.72) | 33.2 (×0.58) |
| r39 bookmark 2 | 30.9 | 27.5 (×0.89) | 22.8 (×0.74) | 18.7 (×0.60) |
| creep windows | — | ×0.94–0.95 | ×0.86–0.90 | ×0.77–0.81 |

**⭐ AND IT COSTS ALMOST NO AUTHORITY.** Over 880 s of ordinary engaged driving on r39 (5 runs, 43–340 s):

| run | s | bind % @2560 | **T 0–3 Hz** (command following) | max \|T\| @10240 → @2560 |
|---|---|---|---|---|
| t 29–369 | 340 | 5.74 | 232.6 → 236.4 (**×1.02**) | 1702 → 1518 (−11 %) |
| t 376–602 | 227 | 4.51 | 183.7 → 185.7 (×1.01) | 1677 → 1624 (−3 %) |
| t 605–770 | 164 | 3.63 | 184.8 → 185.9 (×1.01) | 1810 → 1788 (−1 %) |
| t 774–879 | 105 | 3.58 | 135.7 → 135.3 (×1.00) | 874 → 878 (+0 %) |
| t 881–924 | 43 | 9.36 | 368.6 → 371.9 (×1.01) | 1491 → 1399 (−6 %) |

**The command-following band of T is untouched** (×1.00–1.02 at every run and every clamp value down to
1280). The cost is peak |T| — the transient kick — and it is **−11 % at 2560** and up to −17 % at 1280 on
the worst run. That is the whole authority price, and it lands only on transients.

**🛑 WHY I AM NOT PROPOSING IT AS THE BUILD TODAY, and this is the honest half.** As a describing
function, a clamp that binds on a sinusoid of amplitude `A > c` is an equivalent **real gain reduction on
the D path at that amplitude only** — i.e. a **local Kd cut at the grind amplitude**. And A4's grid says a
Kd cut *raises* `|S|@20` slightly (1.61 → 1.71) and pulls the sensitivity peak **down into the grind band**
(26.3 → 24.2 Hz). So the open-loop mirror (×0.63 on T) and the closed-loop sensitivity frame **disagree
about the sign of the benefit**, exactly as they do for the lag pole. Settling it needs the plant magnitude
above 5 Hz — open item 1, the same thing that blocks everything else here.

⚠ Also: I have **not** run a reader census on `0xC61B6`. It is 10240 in both images and matches
`v280_map_profiles.D_CLAMP`, but the record has already been wrong once about which of a clamp pair is
live (the P clamp is `0xC61BC`, not `0xC61BE`, and both hold 15360). **Census it before any build.**

**The P clamp (`0xC61BC` = 15360) is a different story**: it binds 0.00–18.4 % depending on the window, and
in the two r39 bookmark episodes p99 |P| reaches 36,874 and 60,496 — far past the clamp. It is already
heavily rail-limited there. Lowering it would cut command following directly (P carries the DC), so it is
**not** the free lever the D clamp is. Not recommended.

## A4. ITEM 4 — THE (Kd, 0xC6446, Kp) GRID: 50 of 60 points admissible, and almost none of them help

First, **a correction to my own §6d**: I applied the lag ratio to the ring's servo arm and left the r24
arm alone, which made every `0xC6446` row report a ring ratio of exactly 1.000. `Lr` **is** the r24 arm,
so a `0xC6446` cut scales it directly. Corrected here — and the headroom is much larger than §6d showed.

Gates at today's values (GM ≥ 1.77×, ring ≤ 0.980), lag pole held at 992/507, `Re` on the A1-corrected
measured lane phases:

| Kp | Kd | 0xC6446 | GM | \|S\|@20 | Ms @ f | Re@20 | Re@7 | ring | DC auth |
|---|---|---|---|---|---|---|---|---|---|
| **248** | **128** | **5244** *(as built)* | 1.77× | **1.61** | 2.38 @ 26.3 | +1.52 | −0.28 | 0.980 | 1.000 |
| 248 | 128 | 3072 | 1.77× | 1.61 | 2.38 @ 26.3 | +0.95 | +0.30 | **0.595** | 1.000 |
| **248** | **128** | **2048** | 1.77× | **1.61** | 2.38 @ 26.3 | **+0.68** | **+0.58** | **0.479** | 1.000 |
| 248 | 96 | 2048 | 2.18× | 1.71 | 1.93 @ 24.2 | +0.48 | +0.22 | 0.505 | 1.000 |
| 248 | 64 | 2048 | 2.68× | 1.69 | 1.69 @ **20.7** | +0.27 | −0.14 | 0.542 | 1.000 |
| 200 | 128 | 5244 | 1.85× | 1.47 | 2.24 @ 27.0 | +1.65 | −0.22 | 0.940 | 0.806 |
| **160** | **128** | **5244** | **1.91×** | **1.38** | **2.15 @ 27.7** | **+1.76** | **−0.17** | **0.912** | **0.645** |
| 160 | 128 | 2048 | 1.91× | 1.38 | 2.15 @ 27.7 | +0.92 | +0.69 | 0.337 | 0.645 |

**Three readings.**

1. **`0xC6446` is a FREE and LARGE lever — for the 7.3 Hz ring, not for grind #1.** At Kp 248 / Kd 128 a
   cut to 2048 costs **no** authority, **no** gain margin and **no** change to `|S|@20`, and it takes the
   ring from **0.980 to 0.479** and `Re@7` from −0.28 to **+0.58**. But it also **halves the aggregator's
   20 Hz damping** (+1.52 → +0.68), which is the deep analysis's own 🛑 in milder form. It trades the
   stutter against the grind. It is the strongest ring lever in the study and I would put it in front of
   the operator **as a stutter build**, clearly labelled as not-a-grind-build.
2. **Kd is NOT the plain loop-gain lever the hypothesis expected.** Cutting Kd *raises* `|S|@20`
   (1.61 → 1.67 → 1.71) and drags the sensitivity peak **down from 26.3 Hz into 20.7 Hz** at Kd 64 — i.e.
   it moves the peak *into* the grind band instead of out of it. It buys gain margin (1.77× → 2.68×) and
   it does open the ring gate once `0xC6446` is cut, but it does not help grind #1.
3. **Kp is the only cell in the grid that moves `|S|@20`, and it is the one that costs authority.**
   Kp 160 is better than the base on **every margin** — GM 1.91×, Ms 2.15 at 27.7 Hz, ring 0.912,
   Re@20 +1.76 — with `|S|@20` ×0.86. 🛑 **But the outer loop cannot give the authority back.** `SteerKP`
   is **0.800** today (measured on all three routes) against a ceiling of **0.900**, i.e. only ×1.125 of
   headroom, and restoring Kp 160 needs **×1.55**. Even Kp 200 needs ×1.24. So a Kp cut of any useful size
   is an **unrecoverable** authority loss, and the operator's current report is *"amazing authority"*.

**⇒ ANSWER TO THE QUESTION AS ASKED: the admissible set is large but nearly empty of grind-#1 benefit.**
At held authority (Kp 248), **nothing in the (Kd, 0xC6446) plane moves the 18–22 Hz sensitivity at all** —
`|S|@20` is 1.61 at every one of those points. The only mover is Kp, and it does not come free.
**It does not beat 974/792 on 18–22 Hz reduction at held authority; at spent authority Kp 160 beats it on
every margin but delivers less (×0.86 vs ×0.75) and costs 35 % of the inner loop's DC tracking.**

## A5. WHERE THIS LEAVES THE BUILD

The build recommendation is **unchanged but weaker than when I first reported it**, and the reason is A1:
two of the three frames that supported it now disagree about the 20 Hz benefit's sign under a τ the data
cannot pin. What still holds without qualification is the **7.3 Hz ring reduction** (0.980 → 0.822, which
rests on the `|H_lag|` ratio and not on the tap phase) and its value as a **plant discriminator**. If the
orchestrator wants a build whose benefit is not model-contested, the honest ranking is now:

1. **A creep-exposure drive on V282 first** (open item 4) — free, and it is what makes any of these
   measurable.
2. **`0xC6446` → 2048 as a STUTTER build** — free on every gate, large and robust on the ring, explicitly
   not a grind build, and it halves the 20 Hz damping so it must not be sold as one.
3. **V287 = 974/792 as the plant DISCRIMINATOR** — what it decides is worth more than what it delivers.
4. **The D clamp**, once `0xC61B6`'s readers are censused and the plant magnitude question is closed.

---

# APPENDIX B (2026-09-06, third pass) — the D clamp is an EXCITATION LIMITER, and it is the build

Script: `rlog-tools/studies/grind/grind1_dclamp_decompose.py` → `_scratch/grind1_dclamp_decompose.txt`.
Analysis only; nothing built, sent or flashed.

## B0. Headline

1. ⭐ **THE DESCRIBING-FUNCTION OBJECTION IS ANSWERED, AND `team-lead`'s READING IS RIGHT.** `E = 32·sp − fb`
   splits `dE` exactly into a setpoint part and a feedback part, and **at today's 10240 the binding ticks
   are 92.6–100 % SETPOINT-dominated and 93.6–100 % land on a command step.** The clamp is already an
   excitation limiter, not a gain limiter.
2. ⭐ **AT 5120 IT STAYS ONE.** Onset envelopes fall ×0.90 / 0.82 / 0.81 in the three episodes while
   **steady creep is untouched (×1.01 / 1.00 / 1.00)**. That is the excitation signature, measured.
3. ⭐ **AT 2560 IT IS STRONGER AND STILL STEADY-NEUTRAL IN THE EPISODES**: onsets ×0.79 / 0.70 / **0.33**,
   steady ×1.03 / 0.98 / 0.99. In the *loudest creep windows* it does reach steady (×0.89–0.90).
4. ⭐ **IT COSTS NO MAX-RATE AUTHORITY AT ALL.** Over **180 measured hands-light full-demand steps**, the
   delivered |T| median over the first 50 / 100 / 200 ms is **616.8 / 676.8 / 651.2** at 10240 against
   **630.5 / 691.5 / 688.5** at 2560 and **613.2 / 687.5 / 677.5** at 1280 — ±3 %, no monotone trend. The
   D kick is a one-tick impulse; P carries the step. **(b) is answered: it does not fill the first 100 ms.**
5. ⭐ **AND IT GIVES THE FIRST WITHIN-DRIVE EXPERIMENT IN THIS STUDY.** Its positive effect (onsets down)
   and its negative control (steady creep unchanged) are **measured on the same drive, in the same
   stratum, on the same windows**. No cross-route normalisation, so the 2.50× route-to-route spread that
   defeats every endpoint in §6 **does not apply**. That is worth more than the dose.
6. ⚠ **THE BOUNDARY, stated:** at 2560 the *feedback* part's p99 reaches **1.86–3.18× the clamp inside an
   r35-class burst**. So at the peak of a burst the loop **does** see the nonlinearity as a local Kd
   reduction, and A4's caveat applies **there and only there**. In steady creep p99\|D_fb\| is 0.60–0.71 of
   the clamp, so the small-signal loop is untouched where grind #1 lives.

## B1. The decomposition, per tick

`D_sp = floor(32·Δsp·Kd/8)` · `D_fb = floor(−Δfb·Kd/8)`. Exact, no approximation.

| window | s | p50 \|D_sp\| | p99 | max | p50 \|D_fb\| | p99 | max | D_sp 18–22 | **D_fb 18–22** |
|---|---|---|---|---|---|---|---|---|---|
| **r35 23:48:21 GRIND INCIDENT** | 10.7 | 0 | 15,531 | 35,328 | 768 | 8,144 | 12,016 | 635 | **1,730** |
| r39 bookmark 1 episode | 20.6 | 0 | 13,152 | 46,368 | 448 | 4,768 | 11,856 | 531 | 1,201 |
| r39 bookmark 2 episode | 14.9 | 0 | 17,536 | **105,844** | 496 | 5,312 | 8,320 | 456 | 647 |
| loudest creep windows | 2.8–3.1 | 0 | 4.4–6.7 k | 13–18 k | 240–352 | 1.5–1.8 k | 2.2–4.1 k | 171–198 | 371–575 |

`p50 |D_sp|` is **0** in every window — the command is a 100 Hz staircase, so `Δsp` is non-zero on one tick
in ten and `D_sp` is an impulse train. Its p99 is 3–20× the feedback part's. **The magnitude lives in the
setpoint kick; the ripple lives in the feedback part, and the feedback part is small.**

## B2. Which ticks bind, and why — the answer to the question as asked

| clamp | window | bind % | **D_sp-dominated %** | on a sp step % | p99\|D_fb\| / clamp |
|---|---|---|---|---|---|
| **10240** *(today)* | r35 incident | 3.67 | **92.6** | 93.6 | 0.795 |
| | r39 bookmark 1 | 1.47 | **96.7** | 97.7 | 0.466 |
| | r39 bookmark 2 | 2.06 | **100.0** | 100.0 | 0.519 |
| | creep windows | 0.11–0.72 | **100.0** | 100.0 | 0.150–0.176 |
| **5120** | r35 incident | 9.06 | 62.4 | 63.5 | 1.591 |
| | r39 bookmarks | 3.5–4.2 | 71.7–79.9 | 72.9–81.4 | 0.931–1.038 |
| | creep windows | 0.69–1.63 | **100.0** | 100.0 | 0.300–0.353 |
| **2560** | r35 incident | 17.62 | 39.5 | 40.4 | 3.181 |
| | r39 bookmarks | 9.1–11.8 | 31.7–51.4 | 32.3–52.5 | 1.863–2.075 |
| | **creep windows** | 2.1–4.4 | **97.8–100.0** | 97.8–100.0 | **0.600–0.705** |
| **1280** | r35 incident | 39.28 | 20.8 | 21.3 | 6.362 |
| | creep windows | 8.2–12.5 | 57.6–71.6 | 57.6–71.6 | 1.200–1.410 |

**Read it as:** today's clamp binds almost exclusively on command-step ticks. Lowering it to 2560 keeps
that true **in steady creep** (97.8–100 % setpoint-dominated, p99 ratio 0.60–0.71) and makes it
majority-feedback **only inside the bursts**. So the clamp is amplitude-selective by construction: linear
where the loop is quiet, gain-limited where it is ringing hard. **That is the classical way to arrest a
large-amplitude excursion without touching the linear loop, and it is not what A4's Kd row describes** —
A4 changed the *linear* loop everywhere; this changes nothing until the signal is large.

## B3. (a) The discriminating prediction — onsets move, steady does not

Onset = the 0.5 s after a `|Δsp|` in its top 1 % of non-zero steps. Steady = no step above the median
step size within 0.3 s. T's 18–22 Hz envelope on the 1 kHz mirror:

| window | 10240 onset / steady | 5120 | 2560 | 1280 |
|---|---|---|---|---|
| r35 grind incident | 24.9 / 0.7 | **×0.90** / ×1.01 | **×0.79** / ×1.03 | ×0.59 / ×1.02 |
| r39 bookmark 1 | 36.0 / 17.5 | **×0.82** / ×1.00 | **×0.70** / ×0.98 | ×0.58 / ×0.91 |
| r39 bookmark 2 | 17.2 / 16.8 | **×0.81** / ×1.00 | **×0.33** / ×0.99 | ×0.32 / ×0.93 |
| loudest creep #1 | 30.2 / 31.0 | ×0.95 / ×0.96 | ×0.91 / ×0.90 | ×0.84 / ×0.82 |
| loudest creep #2 | 31.3 / 24.0 | ×0.96 / ×0.94 | ×0.89 / ×0.89 | ×0.81 / ×0.79 |
| loudest creep #3 | 18.9 / 18.3 | ×0.90 / ×0.97 | ×0.80 / ×0.90 | ×0.68 / ×0.81 |

**In the three episodes the separation is exactly the excitation signature**: onsets fall 10–67 % while
steady moves 0–2 %. In the loudest *creep* windows the two move together, because those windows are all
onset — the demand is stepping continuously at low speed.

## B4. (b) The max-rate cost — there is none

I do **not** synthesise a step: the forward path multiplies by `|q32(H_fb·rate)|`, which is zero at zero
rate, so a step from rest is not a valid model of this chain. Instead, **180 measured hands-light
full-demand steps** (engaged, `|bar| < 300` raw, demand index jumping into its top 3 %), 24 simulated per
clamp on the byte-exact mirror:

| clamp | \|T\| p50 over 0–50 ms | 0–100 ms | 0–200 ms |
|---|---|---|---|
| 10240 *(today)* | 616.8 | 676.8 | 651.2 |
| 5120 | 626.2 | 708.2 | 679.8 |
| **2560** | **630.5** | **691.5** | **688.5** |
| 1280 | 613.2 | 687.5 | 677.5 |

±3 % and non-monotone — i.e. **no effect**. The D kick is a one-tick impulse; the P term carries the step
and the output lag smears what is left. **The 123–125 deg/s hands-light reference does not come from the
D kick, and a D clamp at 2560 does not touch it.** (A1's separate finding stands: the *peak* |T| over a
whole 340 s run falls 11 % at 2560, because that peak is set by rare large excursions, not by steps.)

## B5. The dose ladder, in one table

| clamp | character in STEADY CREEP | character in a BURST | onset envelope | steady envelope | max-rate | within-drive contrast |
|---|---|---|---|---|---|---|
| 10240 *(today)* | excitation limiter, 0.1–0.7 % bind | excitation limiter, 1.5–3.7 % | — | — | — | — |
| **5120** | **pure excitation limiter** (100 % D_sp, p99 ratio 0.30–0.35) | mostly excitation (62–80 % D_sp) | ×0.81–0.90 | ×1.00–1.01 | none | **weak** (10–19 %) |
| **⭐ 2560** | **excitation limiter** (98–100 % D_sp, p99 ratio 0.60–0.71) | **local Kd cut** (32–51 % D_sp) | **×0.33–0.79** | **×0.98–1.03** | none | **STRONG and unambiguous** |
| 1280 | mixed (58–72 % D_sp, p99 ratio 1.2–1.4) | gain limiter (16–29 % D_sp) | ×0.32–0.59 | ×0.79–0.93 | none | strong but the control is gone |

**⭐ I WOULD FLY 2560 FIRST.** It is the largest dose that keeps the negative control intact: steady creep
in the episode windows stays within ±3 % while onsets fall 21–67 %. 5120's contrast (10–19 %) is inside
the noise; 1280 moves steady creep too and destroys the control that makes the experiment readable.

## B6. 🛑 THE BUILD — V287 = V282 + `0xC61B6` 10240 → 2560, and its pre-registration

**One halfword, cal-only, no code byte.** `0xC61B6` is 10240 in stock and in V282. **This supersedes my
own §7 recommendation of the output-lag pole** for the reasons in B0: the clamp has no waterbed, no
gain-margin change, no sensitivity-peak relocation, no blind-band rise, no detector-margin cost, no
authority cost, and — uniquely in this study — an endpoint that reads out **within one drive**.

✅ **PRE-BUILD GATE — CLOSED 2026-09-06 (see B7.1).** As first written this said the cell had not been
censused, and it also named the WRONG cell (`0xC61BA`). Both are fixed. The D clamp is **`0xC61B6`**,
and it **PASSES GATE 1** [EVIDENCE, tracer]: 4 live readers, all inside `FUN_00028ea6`, all one
symmetric clamp built by `subr` from a single `ld.hu`, so it cannot install a wrong-sign limit at any
value. ⚠ The reason behind the original caution still binds and is why the mix-up happened: `0xC61B6`
and `0xC61BA` both hold 10240, exactly as the P-clamp pair `0xC61BC`/`0xC61BE` both hold 15360. **The
build script must assert on the ADDRESS, not the value.**

### Pre-registration

Stratum: engaged lateral, hands-off, `vEgo` 1–3 m/s for the creep statistics; the episode windows for the
onset statistics. Comparators r39 / r3a / r3c (V282) and r35 (V281 r3). Onset and steady defined exactly
as in B3, computed from the logged 0xE4 command, so both live on the **same drive**.

| # | statistic | today | **predicted on V287** |
|---|---|---|---|
| **Q1 (LIVENESS)** | 427 tap vs the 1 kHz mirror, on the frames the mirror says bind at 2560 | residual matches the 10240 mirror | residual matches the **2560** mirror and not the 10240 one, on 2.1–17.6 % of ticks |
| **Q2 (PRIMARY)** | T 18–22 Hz envelope at transient onsets | 17.2–36.0 (episode windows) | **×0.33–0.79** |
| **Q3 (NEGATIVE CONTROL, same drive)** | T 18–22 Hz envelope in steady creep, episode windows | 0.7–17.5 | **×0.98–1.03 — UNCHANGED** |
| **Q4** | 0x18F rate 18–22 Hz presence in the creep stratum | 46 % / amp 41 raw (r39) | unchanged or slightly lower; **not decisive** (2.50× route spread) |
| **Q5** | 7.3 Hz ring \|L_tot\|, the n = 8 estimator | 0.980 | **unchanged** — the linear loop does not move |
| **Q6 (SHELF)** | 0x18F rate 33–49.9 / 2–6 | 0.196–0.230 | **unchanged**; must not exceed ×1.3 |
| **Q7 (DETECTOR)** | motion per unit torque, 0.375–0.5 s after a grind onset | no ×0.6 step | **unchanged** |
| **Q8 (AUTHORITY)** | \|T\| median over the first 50 / 100 / 200 ms of hands-light full-demand steps | 617 / 677 / 651 | **unchanged within ±5 %** |

**Decision rule.** **Q1 must fire first** — without it nothing else is interpretable. Then:
- **Q2 ≤ 0.80 with Q3 in [0.95, 1.05]** ⇒ the clamp is an excitation limiter on the car, it cuts the
  onset envelope, and it does so without touching the linear loop. **That is the whole hypothesis
  confirmed, on one drive, with its own control.**
- **Q2 ≤ 0.80 but Q3 also ≤ 0.90** ⇒ it is acting as a gain limiter as well; re-read against A4's grid
  before any further dose.
- **Q2 in [0.90, 1.10]** ⇒ the mirror's onset attribution is wrong; the D term is not what excites the
  mode, and **the whole nonlinear class closes**.
- **Q5 rising** ⇒ the linear-loop claim is false and the decomposition is wrong.

**FAIL sentence.** *The build fails if Q1 does not fire over ≥ 20 s of engaged driving (the clamp is not
live at `0xC61B6` and the cell is mis-identified), or if Q5 rises above 0.980, or Q6 exceeds ×1.3, or Q7
shows a ×0.6 step V282 does not show, or Q8 falls more than 5 %.*

**Cost FAIL, and it outranks every number.** *The operator reports weaker or slower response to a lane
change or a curve, any new vibration or noise, or any worsening of grinding, vibrating, micro-ratcheting,
ratcheting or excess friction.* Report symptoms in his words. An absence of a complaint is not a cure.

**Risk before the drive.** No small-signal loop change: `|S|`, Ms, gain margin, the 7.3 Hz ring, the
blind band and Honda's reversal detector are all **exactly as-built** by construction, because the clamp
never binds on the feedback part in steady creep. DC and command-following authority are untouched
(0–3 Hz band ×1.00–1.02 over 880 s). The one real change is a **weaker transient kick at large demand
steps**, measured at **zero** effect on the first 200 ms of a hands-light full-demand step and **−11 %**
on the peak |T| of a long run. ⚠ Inside an r35-class burst the feedback part does reach the clamp
(p99 1.9–3.2×), so during a burst the effective D gain is reduced — which is the intent, but it means
the burst-peak behaviour is the one thing here that is not small-signal-linear.

**What a null licenses.** Q2 inside [0.90, 1.10] with Q1 firing licenses *"the D term's setpoint kick is
not what excites the 18–22 Hz mode"*, which closes the nonlinear class and sends the next build back to
the loop-shape family with the discriminator framing of §7.

## B7. 🛑 CORRECTIONS AND TWO SIZING CAVEATS CLOSED (2026-09-06, fourth pass)

Script: `rlog-tools/studies/grind/grind1_dclamp_effective_c61b6.py` →
`_scratch/grind1_dclamp_effective_c61b6.txt`.

### B7.1 The cell is `0xC61B6`, not `0xC61BA` — my error, corrected throughout

`team-lead`'s tracer census is right and I have re-verified it myself on the decompile of
`FUN_00028ea6` [EVIDENCE]:

| decompile | cal | address | value | what it is |
|---|---|---|---|---|
| lines 1036–1051 | `tp+0x71bc` | `0xC61BC` | 15360 | the **P clamp** |
| lines 1079–1091 | **`tp+0x71b6`** | **`0xC61B6`** | **10240** | **the D clamp — THE CELL** |
| line 992 | `tp+0x71ba` as `((u16) << 10) >> 3` | `0xC61BA` | 10240 | the **integrator anti-windup** ceiling |
| lines 1191–1204 | `tp+0x71be` | `0xC61BE` | 15360 | the **PID-sum clamp** |

`0xC61B6` and `0xC61BA` **both hold 10240**, so a spot check cannot tell them apart — the same trap the
record already carries for the P-clamp pair (`0xC61BC` vs `0xC61BE`, both 15360). **Nothing numeric in
B1–B6 changes**: the mirror clamps at the *value* 10240 through `v280_map_profiles.D_CLAMP`, which is the
D clamp's value. Only the address was wrong. At Ki = 0 the `0xC61BA` anti-windup ceiling is inert, so it
is not a lever in either direction.

**GATE 1 PASSES for `0xC61B6`** [EVIDENCE, tracer]: 4 live readers, all inside `FUN_00028ea6`, all one
symmetric clamp built by `subr` from a single `ld.hu` (`0x29EE8` / `0x29EF2` / `0x29EF8` / `0x29F02`), no
`ld.h`/`ld.hu` mismatch, so it **cannot install a wrong-sign limit at any value** — unlike the latent
defect I flagged at `0xC61B4`. `D = (dE·Kd) >> 3` confirmed; it rails at **|dE| = 640 today, 160 at 2560,
80 at 1280**. **My pre-build gate in B6 is now CLOSED.**

### B7.2 The clamp ORDER in the mirror matches the bytes

```
P       = clip( E*Kp >> 8 , +- 0xC61BC )                          decompile 1036
D       = clip( dE*Kd >> 3 , +- 0xC61B6 )                         decompile 1079
S       = clip( fade * (P + D) >> 8 , +- 0xC61BE )                decompile 1183 (fade), 1191 (clamp)
lag_out = (D_lag_prev + D_lag_new) >> 5                           0x2A1AC
deadband: |sxh(lag_out)| <= 0xC61B8 AND lag_out*prev <= 0  ->  0  0x2A1BE-E4
v = sxh((lag_out * G_fb) >> 15) ;  T = clip(-K6*v >> 15, +- 0xC61B4)
```
`grind_incident_r35.simulate` applies P clamp, D clamp, fade, sum clamp, lag, gain, out cap **in that
order**. It matches. ⚠ It does **not** implement the `0xC61B8` deadband — priced in B7.4.

### B7.3 ⭐ THE EFFECTIVE BIND FRACTION — the dose is NOT wasted

On a tick where the sum clamp also rails, the D value is discarded and a D dose is inert there. Share of
D-binding ticks on which `|fade·(P+D)>>8| ≥ 15360`:

| window | 10240 raw / **wasted** / effective | 5120 | **2560** | 1280 |
|---|---|---|---|---|
| r35 grind incident | 3.67 / **19.2 %** / 2.97 | 9.06 / 0.3 % / 9.03 | **17.62 / 0.0 % / 17.62** | 39.28 / 0.0 % / 39.28 |
| r39 bookmark 1 | 1.47 / 15.6 % / 1.24 | 3.54 / 0.0 % / 3.54 | **9.08 / 0.0 % / 9.08** | 23.22 / 0.0 % / 23.22 |
| r39 bookmark 2 | 2.06 / 0.7 % / 2.05 | 4.16 / 0.0 % / 4.16 | **11.81 / 0.0 % / 11.81** | 26.85 / 0.0 % / 26.85 |
| loudest creep ×3 | 0.11–0.72 / 0.0 % | 0.69–1.63 / 0.0 % | **2.11–4.38 / 0.0 %** | 8.15–12.48 / 0.0 % |
| ordinary engaged ×2 | 0.51–0.82 / 8.8–10.6 % | 1.4–1.9 / ≤0.6 % | **4.5–5.7 / 0.0 %** | 13.7–16.9 / 0.0 % |

**At the candidate doses the waste is zero.** It is only at *today's* 10240 that a fifth of the binding
is inert, because the ticks big enough to hit 10240 are also the ticks that rail the sum. So **the
effective bind fraction equals the raw one at 5120 and below**, and the numbers I quoted in B2–B5 stand
as effective numbers. (The T envelopes in B3 already contained this, since the mirror applies the sum
clamp after the D clamp in byte order; this table is the diagnostic that says none of the dose is lost.)

⚠ **`P` alone rails the sum clamp on 0.00 % of ticks in every window here.** So the concern that P can
fill the sum at low override index does **not** bite in the stratum this build is aimed at. It is not
refuted in general — these windows do not sample high override index — and the right place to check it is
a high-|bar| stratum, which grind #1 does not live in.

### B7.4 ⭐ THE `0xC61B8` = 102 DEADBAND DOES NOT TOUCH THE 20 Hz RIPPLE

The rung zeroes the output when `|sxh(lag_out)| ≤ 102` **and** `lag_out · previous_output ≤ 0` — a
magnitude test **and** a sign change, so it can only chop a small ripple that also crosses zero. Measured
on the mirror's own lag output:

| window | p50 \|lag\| | p90 | max | **lag 18–22 Hz** | P(\|lag\| ≤ 102) | **deadband fires** |
|---|---|---|---|---|---|---|
| r35 grind incident | 1,722 | 5,810 | 8,691 | **472** | 5.8 % | **0.68 %** |
| r39 bookmark 1 | 1,954 | 5,113 | 8,343 | 349 | 3.1 % | 0.33 % |
| r39 bookmark 2 | 1,325 | 4,486 | 7,167 | 190 | 4.6 % | 0.69 % |
| loudest creep ×3 | 568–870 | 1,225–2,273 | 2,017–3,262 | **123–190** | 6.6–11.2 % | 0.44–0.94 % |
| ordinary engaged ×2 | 747–1,062 | 2,725–4,410 | 10,281–10,433 | 155–225 | 5.8–8.6 % | 0.49–0.60 % |

**The ripple's own lag-output amplitude is 123–472 counts, i.e. 1.2× to 4.6× the 102 deadband**, and it
rides on a slow component of 568–1,954 counts, so the magnitude and sign-change conditions are almost
never satisfied together: the rung fires on **0.33–0.94 % of ticks**. ⇒ **The deadband does not gate the
small-signal 20 Hz ripple**, and the mirror's omission of it over-states T by at most that fraction of
ticks — negligible against the effects in B3. 🛑 **The sentence that stood here, attributing r39's *stall* runs to this rung, is STRUCK** — see B8.3: the rung does not execute on the engaged path at all, so it cannot be their cause.

### B7.5 What changes in the build spec

**Nothing except the address.** V287 = V282 + **`0xC61B6`** 10240 → 2560, one halfword, cal-only. GATE 1
passes on that cell by the tracer's census, so **B6's pre-build gate is closed and the build is
specifiable now**. The pre-registration in B6 stands unchanged; add to its FAIL sentence only that Q1's
liveness check must be run against the **`0xC61B6`** value, since `0xC61BA` holds the same 10240 and a
build that edited the wrong one would pass a naive readback.

## B8. PRE-REGISTRATION AMENDMENTS — adversaries A and D (2026-09-06)

Script: `rlog-tools/studies/grind/grind1_v287_prereg_amend.py` → `_scratch/grind1_v287_prereg_amend.txt`.
All three are folded into the B6 pre-registration and into `PREREG-V287-LOOP-SHAPE.md`.

### B8.1 ⭐ Q1 MUST BE CONDITIONED, or masking reads as a falsified lever (adversary A)

With Ki = 0 the PID sum is `P + D`, and the sum clamp is applied to `floor(fade·(P+D)/256)` against
±15360 — so with the fade near 1 it binds at **|P+D| ≥ 15481**. On a tick where **P is already railed at
±15360 and `sign(D) = sign(P)`**, the sum is clamped with or without the edit and **the delivered torque
is bit-identical: V287 ≡ V282 at the output.** Counting such a tick as a Q1 miss would read as a
falsified lever when it is only masking.

⇒ **Q1's binding-tick set is conditioned on `(|P| < 15360) OR (sign(D) ≠ sign(P))`.**

Measured on the mirror, over 2560-binding ticks:

| window | bind % | P railed % | same sign % | **MASKED %** | **OBSERVABLE %** |
|---|---|---|---|---|---|
| r35 23:48:21 grind incident | 17.62 | 0.0 | 49.2 | **0.0** | **100.0** |
| r39 bookmark 1 | 9.08 | 5.6 | 51.3 | 3.1 | 96.9 |
| r39 bookmark 2 | 11.81 | 41.6 | 56.5 | **24.5** | **75.5** |
| r39 ordinary engaged ×2 | 4.51–5.74 | 4.8–10.5 | 51.3–53.2 | 2.9–5.5 | 94.5–97.1 |
| r35 ordinary engaged ×2 | 4.74–5.45 | 2.6–5.4 | 52.3 | 1.2–2.7 | 97.3–98.8 |
| loudest creep ×2 | 2.65–4.38 | 0.0 | 55.7–58.2 | **0.0** | **100.0** |

**Expected surviving fraction: 75.5 – 100 %, median 97.3 %.** Masking is negligible everywhere except
r39 bookmark 2 (24.5 %), and it is **exactly zero in the creep stratum and in the r35 incident**, which
are the windows Q2 and Q3 are scored on. So the conditioning is a correctness fix, not a power problem.

### B8.2 Bit 6 must be scored DIFFERENTIALLY — and the effect is smaller than feared (adversary D)

`bit 6 = (|r24| ≥ |T|)`. r24 is untouched by a D-clamp edit while T's onset kick shrinks, so the duty on
onset ticks **must rise mechanically**. That is arithmetic about the comparator's right-hand side, **not
evidence about r24**, and **V282's absolute 0.22 / 0.10 thresholds DO NOT TRANSFER to this build.**

⇒ **Score bit 6 as ONSET-minus-STEADY on the same drive.** A rise on onset ticks with steady creep
unchanged is the *expected* signature of the edit working.

Predicted shift (lognormal quantile, `sd(ln |r24|/|T|) = 1.68` from §6c's ladder fit), using each
window's own onset-frame mean-|T| ratio:

| window | k (T ratio on onset frames) | duty today | predicted | × |
|---|---|---|---|---|
| r35 incident / r39 bookmarks 1 & 2 | 1.02 / 1.02 / 1.01 | **0.0000** | — | — |
| r39 ordinary engaged ×2 | 1.004 / 1.010 | 0.0114 / 0.0034 | 0.0114 / 0.0033 | 0.98–0.99 |
| r3c loudest creep | 0.982 | 0.2419 | 0.2452 | 1.014 |
| r39 loudest creep | 0.899 | 0.1250 | 0.1386 | **1.109** |

⭐ **The concern is real in direction but small in size, for a structural reason the adversary did not
have**: bit 6 is **identically 0.0000 on the onset ticks that matter**, because those are loaded-turn
frames with |T| ≥ 600 counts and the r39 read already established that bit 6 is exactly zero there. The
mechanical rise is therefore confined to low-|T| frames, where it is ×0.98–1.11 — inside noise. The
differential instruction stands; the number it protects against is not large. Note also that the onset
`k` here (mean |T| over onset frames, ≈ 1.0) is **not** the ×0.33–0.79 of B3, which is the 18–22 Hz
**band** amplitude: the clamp cuts the ripple, not the frame's mean magnitude.

### B8.3 🛑 THE 102 DEADBAND IS GATED OFF ENGAGED — correction of record (adversary D)

The block at `0x2A1BC` executes only when `cal(0xC64A3) == 1` **and** `gp-0x6806 == 0`, and **`gp-0x6806`
is non-zero when engaged** — so the deadband is **skipped entirely on the engaged path**. I had the
branch condition right in §1c but did not know that cell's engaged value.

- **B7.4's conclusion stands *a fortiori*:** the deadband cannot gate the 20 Hz ripple, and now the
  reason is stronger than "it rarely fires" — **it does not run at all engaged.** The 0.33–0.94 %
  fire-rate figures in B7.4 are therefore an upper bound computed on a rung that is not executing; they
  are harmless but redundant.
- 🛑 **STRUCK:** B7.4's closing sentence attributing r39's stall runs to this rung. It cannot be the
  cause, because it does not execute engaged and the stall runs are engaged.
- 🛑 **WITHDRAWN, pending re-derivation:** the record's identification of `0xC61B8` = 102 as *"the
  P-only deadband"*. Whatever produces the stall runs the r39 read measured, **it is not this cell on the
  engaged path.** This should be re-derived before anything is built on it, and no build in this document
  depends on it.

### B8.4 Two notes on `0xC61B6` for the record

- **Reader census: 7 sites in 2 functions** — 4 live in `FUN_00028ea6`, plus **3 in the unreachable
  duplicate `FUN_0002a93a`** (the same block whose unreachability the tracer proved for the lag poles).
  GATE 1 passes.
- ⚠ **D and the PID sum are WRITE-ONLY — they are not on the wire.** `gp-0x6b36` and `gp-0x6b34` are
  stored and never published, so **the clamp's binding can only ever be inferred from T**, through the
  mirror. That is exactly what Q1 does, and it is why Q1's conditioning in B8.1 matters: it is the only
  observation channel this build has.

### Where this leaves 974/792

**Second, not first.** The output-lag pole remains the right *plant discriminator*, and if the D clamp
returns a null it becomes the next build. But it spends gain margin into a blind band to buy an endpoint
that cannot clear its own noise floor, and the D clamp buys a larger endpoint that can, for free. On the
kit's own standard — *every build must be interpretable from ONE short symptomatic drive* — the D clamp
wins and it is not close.

---

# APPENDIX C (2026-09-06, fifth pass) — re-sizing after adversary B's FAIL, and the plain answer

Script: `rlog-tools/studies/grind/grind1_dclamp_resize_allstrata.py` →
`_scratch/grind1_dclamp_resize_allstrata.txt`. Adversary B's stratification and its two admissibility
definitions are adopted **verbatim**; its machinery reproduces Appendix B to three digits on my windows,
so the divergence was stratum coverage and not method. **I accept the FAIL at 2560.**
Also fixed: `grind1_dclamp_decompose.py` line 47 read `u16(0xC61BA)`; it now reads `0xC61B6`.

## C0. 🛑 THE PLAIN ANSWER: NO DOSE DOES BOTH. THE CLASS IS A PARTIAL MITIGANT.

- The **largest ring-safe dose is 7680**, and it is the only dose besides today's that passes.
- **7680's onset effect is ×0.947 (r39) / ×0.930 (r3c)**, which does **not** clear that statistic's own
  within-route noise floor on a normal-length route.
- Every dose big enough to clear the noise floor (**5120 and below**) **fails the ring gate and fails
  admissibility in every stratum**.
- ⇒ **There is no dose that is both safe and measurable on one 15-minute route.** That is the honest
  answer, and it means the D clamp is a **partial mitigant, not the build I claimed in Appendix B**.
- ⭐ **But the noise floor is not fixed.** The onset endpoint is route-wide and its `n` grows with engaged
  time, so — unlike every other endpoint in this study — **it does not need symptomatic exposure at all**.
  7680 becomes resolvable at 2 SE on about **35–40 minutes of ordinary engaged driving** (C3). That is a
  buildable experiment; it is just not a 15-minute one.

## C1. 🛑 A SELF-REFUTING NUMBER IN MY OWN FIRST PASS, CAUGHT AND CORRECTED

My first Part 4 scaled the ring's servo arm from an **unclamped Kd = 128**. That double-counts, because
the registered `|L_tot| = 0.980` was measured **on V282, with the 10240 clamp already acting** — and the
measured in-band multiplier says the effective Kd in the loaded stratum is already **121.7, not 128**.
Run that way, the construction returns **`|L_tot| = 0.993` for the build that is on the car right now**,
which is self-refuting: a check that condemns the flown build is broken. Corrected to a **relative**
scaling against today's effective Kd. Every ring number below is the corrected one.

## C2. ADMISSIBILITY OVER ALL EIGHT STRATA (B's test: D_sp-dominance ≥ 80 % **and** p99\|D_fb\|/clamp < 1)

`dom % / p99 ratio / bind %`, pooled over r39 + r3a + r3c:

| stratum | s | 10240 | **7680** | 6144 | 5120 | 3840 | 2560 |
|---|---|---|---|---|---|---|---|
| CREEP hands-off | 131 | 87.5 / 0.37 / 0.8 | **85.6 / 0.50 / 1.1** | 81.7 / 0.62 / 1.5 | 75.5 / 0.75 / 1.9 | 69.4 / 1.00 / 3.2 | 53.3 / 1.49 / 5.4 |
| LOW-MID 3–8 m/s | 361 | 91.9 / 0.43 / 1.2 | **88.7 / 0.57 / 1.8** | 84.5 / 0.72 / 2.3 | 77.8 / 0.86 / 2.9 | 67.6 / 1.15 / 4.4 | 48.0 / 1.72 / 8.0 |
| SUBURBAN 8–15 m/s | 584 | 84.7 / 0.33 / 0.2 | **79.7 / 0.43 / 0.4** | 75.3 / 0.54 / 0.7 | 69.1 / 0.65 / 1.0 | 63.9 / 0.87 / 1.9 | 51.6 / 1.30 / 3.7 |
| HIGHWAY > 15 m/s | 541 | 90.5 / 0.20 / 0.0 | **82.6 / 0.26 / 0.1** | 83.5 / 0.33 / 0.2 | 79.7 / 0.39 / 0.4 | 82.8 / 0.53 / 0.9 | 74.7 / 0.79 / 1.8 |
| **HANDS-ON \|bar\|>700** | 244 | 94.1 / 0.55 / 2.2 | **89.2 / 0.73 / 3.0** | 81.6 / 0.92 / 4.0 | 72.8 / 1.10 / 4.9 | 58.3 / 1.47 / 7.5 | **38.2 / 2.20 / 13.8** |
| HANDS-ON HARD > 1500 | 147 | 95.1 / 0.48 / 1.9 | **92.2 / 0.64 / 2.6** | 86.2 / 0.80 / 3.3 | 78.3 / 0.96 / 4.0 | 65.7 / 1.28 / 5.9 | 44.4 / 1.93 / 10.4 |
| **LOADED \|ang\|>60** | 172 | 94.7 / 0.59 / 2.9 | **89.4 / 0.79 / 3.8** | 80.8 / 0.99 / 4.9 | 70.4 / 1.18 / 6.2 | 53.2 / 1.58 / 9.5 | **33.4 / 2.37 / 17.3** |
| **FAST WHEEL > 25 deg/s** | 233 | 97.5 / 0.55 / 2.7 | **92.9 / 0.74 / 3.7** | 85.0 / 0.92 / 4.8 | 75.5 / 1.11 / 6.0 | 59.0 / 1.48 / 9.0 | **36.5 / 2.22 / 16.8** |
| **ADMISSIBLE EVERYWHERE?** | | **YES** | **borderline** | no | no | no | **no** |

**7680 fails my strict ≥ 80 % dominance line in exactly one stratum, SUBURBAN, at 79.7 %** — where even
today's 10240 sits at 84.7 %. Adversary B reports 7680 at 82–100 % across its strata; the difference is
segment sampling, and both readings put it **at the boundary**. Its p99 ratio, which is the stronger
criterion, is **≤ 0.79 in every stratum**. I therefore call 7680 **admissible-borderline** and I say so
rather than rounding it either way. **6144 and below are not admissible** and B's FAIL at 2560 is
confirmed in full: dominance falls to 33–38 % and the p99 ratio to 2.2–2.4 in the three strata it named.

## C3. THE ONSET STATISTIC, ROUTE-WIDE, AND ITS OWN NOISE FLOOR

Onset = the 0.5 s after a command step in the top 1 % of non-zero `|Δsp|` **over the whole engaged
route**, so it always exists regardless of whether the drive contains a symptomatic episode.

| clamp | r39 onset × base | r39 steady × base | r3c onset × base | r3c steady × base |
|---|---|---|---|---|
| 10240 | 1.000 | 1.000 | 1.000 | 1.000 |
| **7680** | **0.947** | **1.000** | **0.930** | **1.000** |
| 6144 | 0.915 | 1.000 | 0.897 | 1.000 |
| 5120 | 0.886 | 1.000 | 0.854 | 1.000 |
| 3840 | 0.838 | 1.000 | 0.780 | 1.000 |
| 2560 | 0.764 | 0.997 | 0.675 | 1.000 |

The **steady control is flat to 3 decimal places at every dose** — the excitation-limiter signature holds
route-wide, not only in the episodes. That part of Appendix B survives adversary B intact.

**The noise floor** [the number the brief asked for]:

| route | onset events | p25–p75 | IQR | SE of the median | **resolvable at 2 SE beyond** |
|---|---|---|---|---|---|
| r39 | **435** | 2.31–6.21 | 3.90 | 0.174 = **4.3 %** | **×0.914** |
| r3c | 229 | 3.60–19.56 | 15.96 | 0.980 = **14.9 %** | ×0.701 |

**⇒ 7680's ×0.947 does not clear ×0.914 on r39, and its ×0.930 does not clear ×0.701 on r3c.** The doses
that do clear (5120 and below on r39) are the ones that fail C2 and C4.

⭐ **The one lever on this that is free: `n`.** SE falls as `1/√n`, and onset events accrue on *any*
engaged driving. r39 gave 435 events in 880 s. Resolving ×0.947 at 2 SE needs SE ≤ 2.65 %, i.e.
**n ≈ 1,150 events ≈ 2,320 s ≈ 38 minutes of engaged time** — about 2.6 normal routes, or one longer
commute. **This endpoint does not need the symptom to occur.**

## C4. THE 7.3 Hz RING COST — CORRECTED, RELATIVE TO TODAY

Measured in-band 6–9 Hz multiplier in the **loaded** stratum, converted to an effective Kd there, and the
ring scaled **relative to today's 121.7**. Gate = the CI upper bound **0.983**.

| clamp | m @ 6–9 Hz | Kd_eff | **\|L_tot\| pred** | vs gate 0.983 | Re@7 |
|---|---|---|---|---|---|
| 10240 *(today)* | 0.951 | 121.7 | **0.980** | PASS *(by construction)* | −0.28 |
| **7680** | 0.941 | 120.4 | **0.983** | **PASS — exactly at the bound** | −0.29 |
| 6144 | 0.927 | 118.7 | 0.987 | **FAIL** | −0.31 |
| 5120 | 0.909 | 116.4 | 0.992 | **FAIL** | −0.34 |
| 3840 | 0.860 | 110.1 | 1.006 | **FAIL** | −0.41 |
| 2560 | 0.745 | **95.4** | **1.038** | **FAIL — ring re-armed** | −0.58 |

At 2560 the effective Kd in the loaded stratum is **95.4**, well under the ZN record's ~118 floor, and the
ring crosses unity. **Adversary B's F2 is confirmed quantitatively.** 7680 lands exactly on the gate,
which is a pass but not a margin — and note the whole column rests on the single-frequency ring
composition the convention-defect note permits **only as a ratio between candidates**, which is exactly
how it is used here.

## C5. THE RE-SPECIFIED PRE-REGISTRATION — rev 2, with adversary B's rev-2 conditions

Dose: **`0xC61B6` 10240 → 7680**, one halfword, cal-only.
**Conditions before flashing, per adversary B: (1) the ring gate adjudicated as in Q5/Q10 below;
(2) Q2 scored PAIRED; (3) Q6 raised to ×1.9.**

### C5.1 ⭐ Q2 IS A WITHIN-DRIVE PAIRED STATISTIC — the two-sample version never resolves

Adversary B is right that the between-route form is dead on arrival: its 2·SE floor is 7.8 % against a
5.3 % effect, with a ×1.63 between-route spread. **Q2 is therefore scored PAIRED, like Q1**: on the V287
drive, the **measured** 18–22 Hz onset envelope against the **10240-mirror prediction on the same drive,
the same onset events**, as a per-event ratio.

Measured on r39 and r3c (V282), 1.0 s onset windows:

| term | route | n | median | IQR | **SE of the median** |
|---|---|---|---|---|---|
| **A** — pure dose term (mirror 7680 / mirror 10240) | r39 | 435 | 0.9572 | 0.0458 | **0.21 %** |
| | r3c | 229 | 0.9571 | 0.0570 | 0.37 % |
| **B** — **measured tap / mirror**, the real on-car paired noise | r39 | 435 | 1.2791 | 0.9313 | **3.24 %** |
| | r3c | 229 | 1.1790 | 0.9579 | **4.99 %** |

The dose term alone would resolve trivially (0.21 % SE against a 4.3 % effect). What sets the floor is
the **measured-vs-mirror residual**, whose per-event IQR is 0.93 — and note its median is **1.28 / 1.18**,
i.e. the mirror **under-predicts** the tap's 18–22 Hz content by 18–28 %. That offset cancels in a
ratio-of-ratios provided it is stable, which is exactly why pairing works; its *spread* is the noise.

⇒ **PAIRED SE = 3.24 % (r39) / 4.99 % (r3c). To resolve ×0.957 at 2 SE needs n ≥ 651 (r39 rate) to 811
(r3c rate) onset events ≈ 1,320–1,640 s ≈ 22–27 minutes of engaged driving.** That is better than the
unpaired 38 minutes of C3 but still **about 1.5 normal routes**, not one. I record that difference from
B's "resolves on one normal route" rather than smoothing it.

🛑 **THE WINDOW MUST BE 1.0 s, NOT 0.5 s.** A 0.5 s window is only 25 tap samples at 50 Hz, too few for
an 18–22 Hz band estimate on that stream. At 1.0 s the predicted effect is **×0.957**, not the ×0.947 of
C3's 0.5 s mirror-only table. **Register ×0.957.**

### C5.2 🛑 Q5 IS DOWNGRADED TO A REPORTED STATISTIC — the ring gate is not measurable to gate precision

The gate `|L_tot| ≤ 0.983` rests entirely on the loaded-stratum 6–9 Hz in-band multiplier, and **that
quantity is not reproducible to the precision the gate needs**:

| measurement of the loaded 6–9 Hz multiplier at 7680 | value |
|---|---|
| mine, pooled over r39 + r3a + r3c (Appendix C PART 2) | **0.941** |
| mine as read by `team-lead` from a different pooling | **0.9895** |
| adversary B, per route | **0.9756 / 0.9693 / 0.9832** |

These span 0.941–0.9895 — **wider than the whole margin between 0.980 and the 0.983 gate**, and my own
number is not even stable between poolings. A gate whose input cannot be measured to better than its own
margin is not a gate.

⇒ **Q5 (`|L_tot|`) is REPORTED, not a FAIL criterion.** Predicted 0.983; report it with the multiplier
used. **The ring FAIL criterion becomes Q10 plus the operator's own stutter report**, which are the two
things that can actually be measured. ⚠ **OPEN RECONCILIATION, recorded not resolved:** the three
multiplier measurements above must be reconciled on one pooling before any future build leans on this
gate. Note also the convention-defect standing rule — `|L_tot|` is licensed only as a *ratio between
candidates*, never as an absolute — which this downgrade brings the prereg back into line with.

### C5.3 The statistics, rev 2

| # | statistic | today | predicted | threshold |
|---|---|---|---|---|
| **Q1 (LIVENESS)** | 427 tap vs the mirror on binding ticks, conditioned on `(\|P\| < 15360) OR (sign D ≠ sign P)` | matches the 10240 mirror | matches the **7680** mirror on 0.1–3.8 % of engaged ticks | must fire over ≥ 20 s |
| **Q2 (PRIMARY, PAIRED)** | per-event ratio, **measured** 18–22 Hz onset envelope ÷ **10240-mirror** on the same events, **1.0 s windows**, route-wide command-step onsets | 1.0 by construction | **×0.957** | paired SE 3.24–4.99 %; **needs n ≥ 651–811 events ≈ 22–27 min engaged**; below that, UNDER-POWERED and licenses nothing |
| **Q3 (CONTROL, same drive)** | same, on steady ticks | 1.0 | **×1.000** | must stay in [0.95, 1.05] |
| **Q5 (RING)** | 7.3 Hz `\|L_tot\|` | 0.980 | 0.983 | 🛑 **REPORTED ONLY — no longer a FAIL criterion** (C5.2) |
| **Q6 (SHELF)** | 0x18F rate 33–49.9 / 2–6, **route-wide 2 s tiles, ≥ 20 tiles required** | 0.196–0.230 | unchanged | 🛑 **FAIL if > ×1.9** (B's route-wide spread is ×1.83; was ×1.6, then ×1.3) |
| **Q7 (DETECTOR)** | motion per unit torque 0.375–0.5 s after an onset | no ×0.6 step | unchanged | any ×0.6 step = FAIL |
| **Q8 (AUTHORITY)** | \|T\| over the first 50/100/200 ms of hands-light full-demand steps, paired | 617 / 677 / 651 | unchanged | FAIL if down > 5 % |
| **⭐ Q10 (RING FAIL CRITERION)** | 0x18F rate **6–9 Hz** and **18–22 Hz** at `\|ang\| > 60`, engaged | 6–9: 5.36 / 6.93 / 4.82 · 18–22: 3.70 / 5.46 / 2.93 | unchanged | 🛑 **FAIL above ×1.9 / ×2.3.** B recomputes the route spread at **×1.09 / ×1.30**, so the margins are **×1.75 / ×1.78** |
| **Q11 (RING, OPERATOR)** | his own report of the strong-turn stutter | "a damped ring at ~40 %" | unchanged | 🛑 **any worsening = FAIL**, and it outranks Q10 |

**Decision rule.** Q1 must fire first. Then **Q2 ≤ 0.957 − 2·SE with Q3 in [0.95, 1.05], Q10 flat and Q11
unchanged** confirms the excitation-limiter reading with the ring intact. **Q2 on fewer than 651 events
licenses nothing** and must be reported as under-powered, never as a null.

**FAIL sentence.** *The build fails if Q1 does not fire over ≥ 20 s of engaged driving, or Q6 exceeds
×1.9 on ≥ 20 route-wide 2 s tiles, or Q7 shows a ×0.6 step V282 does not, or Q8 falls more than 5 %, or
Q10's 6–9 Hz band rises above ×1.9 or its 18–22 Hz band above ×2.3, or the operator reports any worsening
of the strong-turn stutter.*

**Cost FAIL, outranking all of it.** *The operator reports weaker or slower response to a lane change or
a curve, any new vibration or noise, or any worsening of grinding, vibrating, micro-ratcheting,
ratcheting or excess friction.*

## C6. WHAT I NOW RECOMMEND

1. **The D clamp is a partial mitigant, not the cure I called it in Appendix B.** I withdraw B0's
   "it is the build" at 2560. Adversary B is right and its FAIL stands.
2. **If a D-clamp build is cut, it should be 7680**, and it should be sold as a **small, ring-neutral,
   all-strata-admissible step whose primary endpoint needs ≈ 38 minutes of ordinary engaged driving** —
   not as a grind cure, and not as a 15-minute experiment.
3. **If the operator cannot give that exposure, do not cut it.** A build whose primary cannot clear its
   own noise floor is the design failure the kit's doctrine names, and at 7680 the effect is 5 %.
4. **The creep/onset exposure drive on V282 remains the cheapest next step** and it now has a second
   purpose: it measures the onset statistic's `n` and SE directly, which is what decides whether any
   D-clamp dose is ever readable.
