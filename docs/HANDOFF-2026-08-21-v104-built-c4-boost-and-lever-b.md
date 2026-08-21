# HANDOFF 2026-08-21 — V104 BUILT: a ×1.85 assist-lane raise + Lever B restored + a dose instrument

**Session type:** investigation → design → **BUILD**. **NOTHING WAS FLASHED. NO CAN OR UDS WAS SENT.**
**On the car: V103, unchanged.** V104 exists as an unflashed artifact.

**Entry question from the operator:** *"Could we be wrong about the inactive Honda notch filter? …I
just want the best possible chance of fixing grinding and ratcheting and highway instability on 6x.
Imagine you only get one chance."*

---

## 0. THE ONE-PARAGRAPH VERSION

We were **not** wrong that a *notch* at 8 Hz is backwards — that refusal survived five independent
attacks. We **were** wrong about the filter in four ways, and the most useful one is that **`c4`
(`0xC60B4`) is a pure flat scalar on the whole lane** — a lever nobody noticed in 99 builds, and
reachable with four cal bytes. V104 raises it ×1.85, restores **Lever B** (off the car for three
builds through three grinding reports), and repoints CAN 427 to `gp-0x6b86` so **the drive measures
its own delivered dose**. The dose was priced from a **flown single-variable pair (V102→V103)** that
nobody had noticed was one, and the assist map was reconstructed from ROM and validated **200/200
against a flown probe**. Two of the session's biggest wins are negative: **no cal-only damper exists
in this firmware** (every rate lane's sign is `pol`-tied or table-unsigned), and **a latent alias in
three cache files** would have silently reproduced the exact error that caused the original notch
refusal.

---

## 1. WHAT IS ON THE CAR — V103, unchanged this session

No flash occurred. `docs/DRIVE-CARD-V103.md` and the V103 cell table in
`HANDOFF-2026-08-21-route9e-and-the-loop-is-the-cause.md` §1 remain current for the vehicle.

---

## 2. V104 — BUILT, NOT FLASHED

| artifact | SHA256 | bytes |
|---|---|---|
| `_v104_V103BASE-BIQUAD.C4x1.85-LEVERB.GATE6806.ARM5244-427.6B86.SAR4_plain_image.bin` | `b556a0b16da5ac2ad850cae036e5533a4de347e84f2c907f37653cc0f7201a03` | 1,048,576 |
| `39990-TVA,A160-V104-…-427.6B86.SAR4-0x13000-0x100000.rwd` | `41e707121cf86d8fc8d8c27f98fa722632858466ebbce952a4adcf7234fd4fa2` | 986,042 |

Script `analysis-2020accord/build_v104_tva.py`, 119/119 assertions, three runs to identical SHA256,
**`EXPECT_IMG_SHA`/`EXPECT_RWD_SHA` hard-asserted** so a future docstring edit that moves a byte trips
immediately. **Exactly one flashable V104 `.rwd` on disk.** All hashes and the byte diff below were
**re-verified by the orchestrator from disk**, not taken from the builder's report.

### The four edits — 16 bytes in 7 runs vs V103 (8 payload + 8 CRC), zero unattributed

| addr | V103 → V104 | what it is | class |
|---|---|---|---|
| `0xC60B4` | `3a3b513f` → **`fc89c13f`** (0.81731 → 1.51202, **ratio 1.8499999927**) | the dormant biquad's **overall gain `c4`** — a flat scalar on the torque-sensor assist lane, **engaged-only** (V103 armed the section) | cal |
| `0x3AA96` | `c5` → **`fb`** | **Lever B** — repoints a `ld.bu` displacement so the r24 arm gates on the engagement flag `gp-0x6806` | 1 in-place byte |
| `0xC6446` | 512 → **5244** | **Lever B** — the r24 arm dose (`m = 2.000` while LKAS applies) | cal |
| `0x55DF2` · `0x55E10` | `b4`→`7a` · `a6`→`a4` | CAN **427 (`0x1AB`) source → `gp-0x6b86`**, shift `sar 6`→`sar 4` | 2 in-place displacement bytes |

CRC: 2 blocks, `[0x013000,0x0C4FFC)` and `[0x0C6000,0x0C6FFC)`. `[0xC5000,0xC5FFC)` byte-identical.
**Cave byte-identical to V103 at 164 B** (verified: no edit lands inside the cave extent, and E5's
`andi 0xfe` appears nowhere in the image). **No new code cave. No hot-path insertion.**

### Re-disassembled from the BUILT image (GhidraMCP)
`0x55DF0` = `24377a94` → **`ld.h -0x6b86, gp, r6`** · `0x55E10` = `a432` → **`sar 0x4, r6`** ·
`0x3AA94` = `847ffb97` → **`ld.bu -0x6806, gp, r15`** · `0xC60A8` reads
`f8c2c4bf 7576223f 0ebef0bf fc89c13f` (poles/zeros frozen, only `c4` moved) · `0xC649B` = `01`.

---

## 3. THE ANSWER TO THE ENTRY QUESTION

### 3.1 The notch refusal SURVIVES — five attacks, five holds
`arg Z`, the `A ≈ 1` approximation, the leave-one-out `|A₀|` swing (0.183/0.440/0.570), the `|κG|` CI
[0.512, 1.001], and the SUM phase (±30°) were all attacked and all held. `gp-0x6b86` carries
`pol = −1` so it sits at **∠180°** while `gp-0x6b4c` sits at **∠+41°**; deleting a cancelling term from
a 4:1 near-cancelling sum grows the sum. ⭐ **And saturation cannot rescue it**: a saturation mixture
**SCALES** a lane and **cannot ROTATE** it, so every phase in the budget survives — the notch's
`Δ(u/T) = +a·H` becomes `(1−d)·a·H`, **magnitude smaller, sign identical.**

### 3.2 But we were wrong about the filter in FOUR ways
1. 🛑 **It is NOT inert where grind #1 lives.** The record wrote it off on `−0.149 dB / −10.6° at
   7.79 Hz`. At **21.73 Hz it is `0.856 ∠ −31.2°`.** And at 6–9 Hz, `a·|H−1| = 0.0174 = **33 % of the
   entire aggregator sum**` — the −0.149 dB figure is **lane-referenced**, exactly the error §3.1's own
   LAW exists to prevent, **made about the kit's own flown build.**
2. ⭐ **`c4` is a pure flat scalar** — exactly one reader image-wide, pcode-confirmed, `mulf.s` before
   the pole recursion, **zero added phase at any frequency**, engagement transient 20.25 ms and
   *constant* across dose (poles untouched). **Never proposed, priced or killed in 99 builds.** Both
   prior biquad refusals moved the **poles**; this moves only the gain.
3. **The reachable space is now mapped.** `|Num(e^{jω})| = |2cos ω + c3|` (closed form). Partial notch:
   **only at DC or Nyquist**, never an interior frequency. **Phase-lead: STRUCTURALLY IMPOSSIBLE** —
   the palindromic ±1 end-taps force numerator phase ≡ −ω. **Band-pass: not reachable cal-only**
   (`b0 ≡ b2 ≡ c4`). A 2-pole low-pass IS reachable (`c3 = +2.0` exactly), and the "shelf" collapses
   into that same family — **no separate design path exists.**
4. **Honda calibrated this stage to sit at its own clamp**: peak `|H|` 1.000031 against an input
   ceiling of exactly 12.0. Clip onset k ≈ 1.0001 — **but never reached in practice, see §4.2.**

### 3.3 The derivative fix — A CLEAN NEGATIVE, and it is a load-bearing result
> 🛑 **NO cal-only site exists with an independently settable sign.** Every rate/derivative lane's sign
> is either tied to global `pol` (`gp-0x6752`) or produced by an **unsigned** (`ld.hu`/`sld.hu`) gain
> table — writing it negative zero-extends into a huge wrong-signed gain and corrupts the
> interpolation. **This is a structural property of the firmware's gain-table convention, not a
> per-lane accident.**

⇒ **You cannot add a damper to this ECU by calibration.** Two consolations, both recorded:
- **`gp-0x6bbe` reversed twice and landed on "already a damper."** A **second `pol` load** nobody had
  found (`FUN_0003f776`, the `gp-0x6a56` producer) cancels the first, so with `pol = −1` the lane is
  `≈ −K1·S1·gp-0x6abe` — **a genuine −K·(column rate) damper at stock**, not pumping. **And `K1` IS
  signed** (`sld.h` @`0x34b16`, `0xD6010` m24 / `0xD700E` m26, both = 43) ⇒ a real two-way lever.
  Bandwidth is the best in the census (**one EMA, `0.989 ∠ −7.0°` at 8 Hz**), and there is **no
  low-rate dead zone.**
  🛑 **DEAD ON HEADROOM ANYWAY:** its bound is a **flat ±512** (`0xD60F0`/`0xD70D8`, Y = [512]×5) and
  V92 measured the lane at p50 76.8 / **max 390.4 — 76 % of rail at k = 1.** Usable dose **≤1.31×** for
  a **3.8 %** cut, and `1/|A|` gets *slightly worse* (2.273 → 2.304). Its own optimum (k = 3.07) needs
  1198 counts against a 512 rail. **The "~6× headroom" figure was a GATE-3 error** — sized against the
  viscous component (20–79 ct) while ignoring a ~74-count DC pedestal.
  ⚠ **And "it's a rate lane and rate lanes worked twice" is a PATTERN-MATCH, not an argument.** V62/V88
  were the **derivative-of-torque** lane, now at a measured optimum with both flanks falsified.
- **`gp-0x6ade` is a permanently-dead aggregator slot** — zero writers by two methods, unit weight,
  already wired into the sum. **The cleanest cave-injection target ever found here.** Needs a live
  write-and-read-back probe before any design commits (static clearance has been wrong before —
  `gp-0x1500`).

---

## 4. HOW THE DOSE WAS PRICED — and the two things that made it possible

### 4.1 ⭐ V102→V103 IS A CLEAN SINGLE-VARIABLE PAIR AND NOBODY NOTICED
Full byte diff: **55 bytes in 13 runs** — the arm-source repoint, `0xC649B` `00`→`01`, the telemetry
cave, two CRC trailers. **Biquad coefficients identical. `0xC6CD0` identical. Levers A and B
identical.** ⇒ **arming the filter is a perturbation of exactly the kind a `c4` edit makes**, so
inverting it measures the quantity that responds to `c4`.

```
a_filt = 0.0457      Im/Re residual = -3.1 %    <-- a free consistency check it could have failed
CI 95 % [-0.0047, +0.0816]    P(a>0) = 0.957    <-- ~2 sigma, AND IT INCLUDES ZERO
```
Every other band returns a 100–980 % residual — the negative control working.
🛑 **THE CLAIM IS NARROWER THAN "WE MEASURED `a`":** `a_filt` is the **as-flown, duty-weighted
sensitivity of the aggregator sum to a change in `H`**. A `c4` edit acts through `H` and **only**
through `H`, under the same duty mixture — so it is **the correct coefficient for pricing `c4` by
construction**, whatever the regime mixture is. **It is NOT the ROM map slope and must never be quoted
as one.**
⚠ **FOUR transport assumptions, all BELIEF:** `c`/`A_dis` identified at 4×/8× and applied at 6×;
**V100 had Lever B ARMED and V102/V103 do not**; cross-route (different drives, days, roads); and a
**4.7× extrapolation** in perturbation size (`|ΔH|` 0.18 arming → 0.85 at k = 1.85).

### 4.2 THE ASSIST MAP, RECONSTRUCTED FROM ROM AND VALIDATED 200/200
`0xC7B40` is a **pointer array indexed by the mode number** (`+24*4` → `0xD6158`, `+26*4` → `0xD7130`
— confirmed by direct read). Record = `[N=9][field A ×9][field B ×9]`.
🛑 **The axis assignment is the opposite of the obvious one**, and it was adjudicated by the car, not
by argument: **`gp-0x373c`/`gp-0x3714` are the map's INPUTS, not the map.** A second transform
(`0x39038`, `0x390b2`) swaps the roles — `gp-0x642e` becomes X and `gp-0x6442` becomes Y.
**V72's flown probe on route `59` settles it: measured `bit6 = 200 / 87,940`. The correct reading
predicts 200 exactly; the swapped reading predicts 10,293 — 51.5× out.** Frame overlap 180/200 (the
±20 is 100 Hz resampling slop on a 1 kHz signal). **This simultaneously validates the mode-record
decode, the speed interpolation, the axis orientation, the `0.388·(A − 0.0912·B)` transform, the
`cal(0xC6178)=5274` ceiling, the map build, the `gp-0x69a0` slope limiter, the breakpoint search, the
slope-vs-value register split and the ×1.024 wire scale.**
⚠ The orchestrator got this wrong first (asserted the swapped reading from one decompile) and was
corrected. **The runtime gains `iVar32`/`iVar33` are exactly 1024 each ⇒ product/2²⁰ = 1.000000**, so
the gains do **not** explain the difference — the axis role does.

**`a` = 0.069 pooled engaged**, speed-scheduled **0.123 at parking → 0.046 at 120 km/h**, capped at
0.350–0.500 by `gp-0x69a0` (never by the map). **The budget's 0.098/0.117 is high by 1.4×/1.7×** — the
closure could not see the speed schedule and its pool was low-speed weighted.
🛑 **`red-team`'s "`a` is 18–38× the assumed value" is a correct read of the RAW ROM PAIR and a wrong
read of the RUNTIME MAP.** The lever survives on the corrected number.

### 4.3 THE CLIP GATE IS CLOSED — structurally and empirically
`|gp-0x6b82| ≤ |gp-0x6b7a| ≤ 12288` proven at instruction level (the friction-hold stage is a pure
attenuator — `0x358ba cmovge` is a `min`, the other branch passes through). And **the biquad cannot
amplify**: zeros on the unit circle, peak `|H| = 1.0000`.
**Engaged clip duty at k = 1.85: 0.000000** — zero frames in **1,704 s across five builds**, zero in
**all 2,000 episode-bootstrap resamples**, rigorous bound clean to **k ≤ 3.40**, exact model first
clipping at **k = 10.76**. Worst single frame 6799 vs 12288 (1.81× clear).
⇒ **The V80 relay failure mode is not reachable by this lever.** Sensitivity: even with the unmeasured
`gp-0x6b4a` pinned at its ±25600 rail on every frame, critical k = 4.7 — still 2.5× above the dose.

### 4.4 The clamp is SYMMETRIC — four independent confirmations
`0x35a54 movhi 0x4140` does **double duty**: it supplies both the comparison constant *and* the
saturated output, so on the ceiling path `maxf.s` is skipped and `r10` already holds `+12.0`.
**A read of `0x35a68`–`80` in isolation, without carrying `r10` in from `0x35a54`, sees only a floor
clamp** — that is the exact shape of the miss that produced a "half-clamp / rectifier" scare.
⇒ **No rectification. The failure mode is odd-symmetric flat-topping**, and §4.3 shows it is never
reached.

---

## 5. WHY k = 1.85, AND WHY UNDER-DOSING IS THE DANGEROUS END

`A(k) = A₀ + (k−1)·c·L` is a **straight line in the complex plane**; its closest approach to the origin
is at **k = 0.83 — a CUT, not a boost.** So every k > 1 walks away from the instability, monotonically.
Exact Möbius `Z(k) = Z(1)·A(1)/A(k)` (the first-order proxy is invalid at this dose — `ΔG` is 93 % of
`|G₀|` at k = 1.5):

| k | amp vs today | `Re Z` @ 6–9 Hz | worst of 204k corners |
|---|---|---|---|
| 1.00 | 1.00× | −3763 | — |
| **1.05** | 0.95× | −2800 | **4.26× WORSE** |
| 1.26 | 0.73× | ≈0 — anti-damping zeroed | +8.8 % |
| 1.35 | 0.63× | +547 | +8.8 % |
| 1.70 | 0.40× | **+1039 (max)** | +3.2 % |
| **1.85** | **0.30×** | +1004 | **none — 0 of 204,000** |

🛑 **The dose-response is INVERTED from the usual shape: a timid boost can land ON the instability.**
This inverts how the kit has sized every lever for sixty builds. ⭐ Three independent arguments select
1.85: the corner sweep, the `Re Z` flat top, and **larger k tolerates more clipping** in the saturation
mixture. On the **measured** `a_filt` the `Re Z` zero-crossing moves to **k = 1.545** — so **k = 1.35
would NOT have cleared it** (`Re Z` = −947, still anti-damped). **The operator chose 1.85 before that
was known.**

⚠ **`a_filt`'s uncertainty is the binding constraint, not (c, A):** P(endpoint passes) = **0.556** with
both live, **0.847** with `a_filt` pinned. That is why 427 carries the **LANE**, not the SUM.

---

## 6. THE PRE-REGISTERED READOUTS

### 6.1 Endpoint 0 — DID THE DOSE REACH THE CAR
```
STATISTIC  6-9 Hz band RMS ratio of the 427 channel, engaged, vs V103 route 0x9e, matched exposure.
PASS       ratio in [1.50, 1.70]  => the c4 edit is IN FORCE.
ARM-FAIL   ratio ~= 1.00          => the arm did not take.
PARTIAL    between                => intermittent gate; cross-check the manual-arm control.
*** DO NOT PRE-REGISTER 1.85. THE CHANNEL IS RECTIFIED AND CANNOT RETURN IT. ***
```
🛑 **The 427 slot carries Honda's own `abs()` (`jarl 0x49a5a` @`0x55DF4`), which folds the spectrum and
reads a true k = 1.85 as 1.603** — flat from LSB 1.19 to 8.0, so no encoding choice fixes it, and
`sar 4` at 3.20 ct/LSB sits inside that range. ⭐ **It is NOT confounded, because `k` is BINARY:** `c4`
is one 4-byte cal inside a CRC block — it is `fc89c13f` or the image does not boot. **No partial-write
path exists, so there is no "half-failed arm" for 1.60 to be confused with.**
**A sign bit is not buildable in-envelope** — suppressing the `abs()` needs the clamp's lower bound at
−512, and V850 Format-II `mov imm5` reaches only −16…+15.

### 6.2 Endpoint 1 — LEVER B, and it is SEPARATELY ATTRIBUTABLE
`c4` is inert at 21.0–22.5 Hz: ratio **0.9726, CI [0.9642, 1.0348], 0 of 3,000 draws exceed a 10 %
effect.** ⚠ **Carry this sentence with that number:** `|A| = 0.990` there means the loop has almost no
leverage, so **the tight interval reflects INSENSITIVITY, not confidence** — it is the model's own
prediction, not a measurement.
🛑 **22–26 Hz is NOT clean** (ratio 0.893, 61 % of draws >10 %). **Pre-register 21.0–22.5 only.**
```
STATISTIC  band RMS of rate_f, 21.0-22.5 Hz, engaged, 4 s Hann / 50 % overlap / detrended.
EXPOSURE   ONE contiguous engaged block >= 15 s, HELD AT STEADY SPEED IN 50-80 km/h.
           THE SPEED BAND IS PART OF THE PRE-REGISTRATION, NOT ADVICE.
REFERENCE  V103 route 0x9e, same speed band, n = 8 blocks: median 1.146 deg/s RMS.
PASS       below that set's p5.  LR 14.1:1.      FAIL  at or above the median (1.146).
```
🛑 Raw over all blocks the base rate spans **59×** — that is exposure, not build — and Lever B's 0.40×
is only **0.73σ, LR 3.3:1: not a readout.** Speed-held it is **2.11σ, LR 14.1:1**.
⚠ The reference set is 8 blocks (soft p5); 12 of V103's 23 blocks are not steady-speed at all.

### 6.3 Endpoint 2 — 6–9 Hz `Re(Z)`, unattributable but DIAGNOSTIC
Reference: V103's 23 engaged 15 s blocks, p50 −3784, p95 −1489, SD 1310.
**PASS `Re Z > −1489`** ⇒ *"at least one lever moved 6–9 Hz"*, LR 12.7:1. **Do not read a pass as
evidence for `c4`.**
⭐ **`Re Z ≤ −3784` (V103's own median) has P ≤ 0.030 under EVERY hypothesis in which either lever
works ⇒ it FALSIFIES the `|κG| = 0.630 / A = 0.440` identification WITHOUT NEEDING ATTRIBUTION.**
That is what a muddy score can still deliver, and it is the strongest case for the bundle.

### 6.4 The free within-drive control
V103 arms the section **engaged-only**, so manual frames run the **literal unity bypass** at `0x35a86`
(`mov r10,r6`, the same tick's `gp-0x6b82`, register-verified). **Bin engaged and manual by `|tq|`;
median `|gp-0x6b86|` per bin should be 1.66–1.85× engaged. Near 1.00 ⇒ the edit is not in force.**
Binning on `|tq|` removes the operating-point confound.
🛑 **Do NOT difference engaged vs manual as a transfer function.** On V100/V101, with the filter
disarmed in **both** arms, manual `tq→u` is **5.5–5.9× engaged and near anti-phase** (0.262∠−145.8°,
0.337∠−173.3°). Engagement changes the transfer enormously for reasons unrelated to `H`, **and nobody
has a mechanism** (open item).

---

## 7. THE OPERATOR'S RULINGS

1. **Dose ceiling: k = 1.85.** Shown the corner table, chose the robustness end, accepting the feel
   change. *(It later proved to be the only listed dose past the `Re Z` crossing on the measured `a`.)*
2. **"Both levers, accept a muddy score"** — shown that `c4` alone PASSES the endpoint while the bundle
   reads FAIL even if both work, and that `|A|` says the bundle is the better car. **He chose the car.**
3. **`gp-0x6bd0` revert** — ruled, then found to have no target (§8).

---

## 8. FINDINGS THAT KILLED THINGS — the negative record

- 🛑 **`gp-0x6bd0`'s V74 amplification is NOT on the car.** All five cells + `0xC63A0` byte-stock on
  V103, **reverted at V84, frozen 20 consecutive builds.** The lineage's "engaged-only amplification we
  added at V74" is **STALE** (true V74–V83a). **Nothing to revert.**
- ⚠ **But its "= 0 at 6–9 Hz" is a DUTY-CYCLE zero, not a bandwidth zero.** `FUN_00034350` is
  **memoryless** — no EMA anywhere — so it passes 6–9 Hz untouched when both dead zones clear. On route
  `0x9e`, **69.7 % of engaged time is above 35 km/h** and the damper is **live on 10.9 % of engaged
  frames, not ~1 %** (the 98.8 % figure came from low-speed routes `6e`/`5e`). It still cannot reach
  the **ratchet** (FactorE's rate dead zone; 24.9 % of engaged frames are highway-speed *and* in the
  micro regime with the damper still zero).
- 🛑🛑 **Path-1 and Path-2 DISAGREE on `gp-0x6bd0`'s sign.** `FUN_00038148` applies its **own extra
  `pol` multiply**; `FUN_0003aa2c` does not. With `pol = −1` the same cell arrives **damping-signed in
  Path-1 and pumping-signed in Path-2.** ⇒ lowering Honda's FactorC moves both at once in opposite
  directions. **A future lever must price this; the sign does not transfer.**
- 🛑 **`gp-0x6bd0` is COLLINEAR with r24/r26** (`sign = −sign(motor rate)` ⇒ ∠−90°), so any amount of it
  is **silently absorbed** into the budget's quadrature bucket. Safe today only because it is off.
- **The 2-pole low-pass is DEAD** — 45 designs, zero feasible; the best makes a high band 2.25× worse.
  It **CUTS** the lane at 15–26 Hz, and on the damping criterion removing lane there **removes
  damping**. Its `ΔG` also lands outside the corrected favourable cone.
- **`f0` IS THE WRONG ENDPOINT for any flat-gain lever, structurally.** `f0` is a **zero crossing** of
  `Re(Z)`; a pure gain change **scales** `Z` and scaling cannot move a zero — only phase can. Predicted
  `|Δf0| < 0.01 Hz at every k` against a ±1.05 Hz floor: **dead by ~100×.** Choosing it would have
  manufactured a guaranteed null (the V97 failure).
- **A `0x9e` falsification test of the saturation model returned the predicted 2.83× and then DIED to
  its own controls** — a placebo predictor (`max|rate|`) gave a **larger** effect, a placebo band
  (22–26 Hz) nearly as large, and the step oscillated in sign under a smooth control. **Recorded
  because it was one message away from being reported as a confirmation.**
- **E5 (a 44 B comparator rung) was designed, priced and DROPPED** — `0x14A` byte4 bits 2:0 are
  **Honda's**, not free (§9). It was also **redundant**.

---

## 9. RETRACTIONS AND RECORD CORRECTIONS

| # | what was wrong | corrected to |
|---|---|---|
| 1 | 🛑 `reference_accord_v103_byte4_free_bits_and_clip_flag_cave_design`: *"byte4 bits {2,1,0} free"* | **THEY ARE HONDA'S** (`gp-0x6799`/`gp-0x679b`/`gp-0x679a`, written in `FUN_00055a98` before the hook; V103's masks `0xbf`/`0xdf`/`0x67` preserve them). `accord-can-tx-100hz-base-tick-and-gateway`'s **"free channel is bits 7:3"** was RIGHT — V103 has SPENT all five. **`0x14A` has ZERO free bits.** **Corrected in place.** *This one caused a real defect.* |
| 2 | `gp-0x69a4` called "the raw LERP-interpolated Y value" in two tracer memories + `TRACE-2026-08-21` §1 | it is the **segment SLOPE**, Q10 (register-proven two ways) |
| 3 | `TRACE-2026-08-21` §2: `cal(0xC6178)=5274` a "snap-up floor" | a **ceiling clamp** |
| 4 | *"V103's filter is inert where the ratchet lives"* | **33 % of the 6–9 Hz loop gain** — a lane-referenced-dB error about our own flown build |
| 5 | *"`gp-0x6bd0` is an engaged-only amplification we added at V74"* | **STALE** — reverted at V84, byte-stock for 20 builds |
| 6 | `0x3AB76`/`0x3AC20` labelled *"Lever A — V62's fix, carried"* | **byte-stock since ~V81** — and the mislabel is in **three** build scripts (`v101`, `v102`, `v103`), not one |
| 7 | `gp-0x6bbe` read as pumping | **it is a `−K·(column rate) DAMPER`** — a second `pol` load cancels the first; **`K1` is signed** |
| 8 | *"He does not mind changed driver feel while engaged"* cited as the operator's words | **a KIT INFERENCE, never a quote.** Also *"16× long-term target"* — the number is nowhere in quotes |
| 9 | `boost-pricing`'s **P(pass) = 0.996** | **0.556** — the 0.996 assumed `a` with no uncertainty. *"The most confident-sounding number I produced all session, and it was wrong by construction."* |
| 10 | *"the rate lane is the model's best cal-only lever"* | **WITHDRAWN** — `ΔG` = 2.4× the whole loop gain, far outside validity. **Lever B's warrant is the road measurement alone.** |
| 11 | orchestrator's *"the closure was inflated 1.6×"* triangulation | **WITHDRAWN** — under a two-regime mixture it could be measuring duty |
| 12 | orchestrator's assist-map axis reading | **WRONG**, refuted 51.5× by the car (§4.2) |
| 13 | orchestrator's `>>3` sizing for the 427 tap | omitted Honda's `mul 0x5` — would have **overflowed 1.57×**. `sar 4` is correct |
| 14 | orchestrator's *"slew limiter on the limit 39.5 % of frames"* applied to `FUN_000352b4` | that is the **LKAS command** slew limiter, a different stage. `bVar3`'s duty is **UNMEASURED** |
| 15 | orchestrator's *"a dosed build measures its own dose within the drive"* (R0d) | **REFUTED** — 0.66 engagement edges per 30 s, and the engaged/manual transfer differs 5.5–5.9× for unrelated reasons |
| 16 | handoff open item #16, *"the L_total/C pricing scripts are in NEITHER repo"* | **WRONG** for the `_g2b_*` family — they are on disk |
| 17 | builder's filter response quoted at **fs = 143 Hz** | **fs = 1000.** Null at **55.23 Hz**, `\|H\|<1` only on **36.8–82.2 Hz**, ratio a **flat 1.8500 everywhere** |

---

## 10. 🛑 A LATENT DATA DEFECT — AUDITED, GUARDED

**`x6b94` is a byte-identical ALIAS of `x6b4c` (the LANE, not the aggregator sum) in `_cache_r96`,
`_cache_r97` and `_cache_r9e`.** CAN 427 carries one cell and **which cell depends on the build**;
only `r85`/`r95` (V100/V101) packed the sum. The extractors write both keys regardless.
⚠ **Three caches, not the two originally reported — the audit found `r97`, the STOCK 1× baseline**, and
therefore the reference most likely to be reused.
🛑 **This is the SAME error class that produced GATE2's original notch verdict** (lane quoted as sum ⇒
dose 4× too large). At 6–9 Hz the aggregator is a 4:1 cancellation, so lane-vs-sum is **a factor of ~4**,
in the unsafe direction. **Now latent in the data files rather than a document.**
✅ **Guard shipped: `analysis-2020accord/check_427_alias.py`** — `assert_is_sum(tag)` raises unless the
route genuinely packed `gp-0x6b94`; running the file re-audits every cache. **Extend `SUM_ROUTES` if a
future build repoints 427.**
⚠ **Sibling trap:** `damp_nz` / `g6ac2` are **stale decodes on V100+ routes** (a V75/V84-era bit that
V102/V103's cave repurposed). On `r9e`, `damp_nz` duty is **0.2390** — plausible-looking, meaningless,
and uncomfortably close to the genuine 12.7 °/s duty of **0.2419**. **Do not use them on V100+.**

---

## 11. OPEN ITEMS — with what closes each

| # | item | what closes it |
|---|---|---|
| 1 | **`a_filt`'s CI includes zero** — the binding constraint (P 0.556 → 0.847 if pinned) | **V104 itself**: `gp-0x6b86` on 427, 7 episodes, one drive |
| 2 | **Two `Re(Z)` estimators disagree 2.6× at 15–22 Hz** (−440 vs −1135); they agree to 3 % at 6–9 Hz | adjudicate power-weighted Welch vs per-bin averaging; both already coded |
| 3 | The **5.5–5.9× manual-vs-engaged `tq→u`** difference, replicated on two builds, **no mechanism** | a build with the SUM on 427 and real manual exposure |
| 4 | `bVar3`'s duty (the `FUN_000352b4` magnitude limiter) is **unmeasured** | a cave rung, or a reconstruction from the second LERP |
| 5 | **`gp-0x6ade`** — permanently-dead unit-weight aggregator slot, the cleanest cave target found | live write-and-read-back probe |
| 6 | The **12.7 °/s dead zone: wheel rate or motor rate?** Inherited, not re-derived | decompile `FUN_00034350`'s input scaling |
| 7 | **`gp-0x6bfe`/`gp-0x6bfa`** (Path-2's nonlinear combiner) untraced ⇒ no ΔG for a FactorC lever | trace their producers |
| 8 | `FactorE m26`'s record parse **inferred by adjacency**, not from a verified layout | one `read_memory` + a record-layout walk |
| 9 | `FUN_00043e44`'s 32-weight bit (`gp-0x6b98` vs a local reference) **not fully resolved** | derive its formula |
| 10 | Endpoint-2 LRs **assume normal block distributions** (23 blocks, untested) | a QQ check |
| 11 | Endpoint-1's reference set is **8 blocks**; grind #1 is strongest at 5–10 km/h where `0x9e` has **2** | more steady-speed 50–80 km/h exposure; a deliberate low-speed run |
| 12 | `gp-0x671a < 5` proven **at the 200 probe frames**, not frame-by-frame elsewhere | one more route with the same rung |
| 13 | `gp-0x6b4a` unmeasured (swept to its rail; verdict survives) | a cave rung |
| 14 | **Register-indirect / computed-pointer access** to `gp-0x3814`/`gp-0x3818`/`gp-0x6b86` | **structurally unclosable by any static method this kit has** — standing limitation |
| 15 | A **Ghidra scratch program is still open** (the superseded E5 image) | close it manually; the shared `code.bin` is untouched |

---

## 12. METHOD FINDINGS

- ⭐ **`gp-0x671a < 5` ON THE CAR ⇒ Honda's own biquad arm gate (`cal(0xC64FA)=5 ≤ gp-0x671a`) is
  FALSE.** Setting `0xC649B` 0→1 **alone is a guaranteed null**; V103's 3-instruction repoint was
  **load-bearing**. Memory: `accord-honda-biquad-arm-gate-is-false-on-this-car.md`. ⊕ It also retires
  V72's `bit6` as a rung that was structurally dead under the other branch.
- ✅ **The CAN checksum runs LAST — now EVIDENCE, not relayed.** `0x55C18 jarl 0x57b24` sits **three
  instructions after the cave hook at `0x55C0E`**, covering the full 8-byte frame. The kit has been
  building on this for six-plus builds without verifying it.
- 🛑 **The cave's `RET` is its ONLY exit.** Appending a pass *after* it leaves the code **unreachable**
  and the rung reads a permanent 0 — which would report *"arm didn't take"* on a perfectly good build.
  Caught pre-flight; `build_v104_tva.py` now asserts RET-is-last and `jmp [lp]`-exactly-once.
- **Ghidra reuses C variable names across unrelated live ranges** — hit three times this session
  (`FUN_00028ea6`'s `uVar37`, `FUN_000352b4`'s `local_44`, `FUN_00034a72`'s `iVar21`). **Use
  `analyze_dataflow` (PCode, seeded at an instruction address), never a name across a long span.**
- **`search_instructions` is blind to ranges Ghidra has not defined as a function** (`0x2a8ac` →
  "No function found" while the decompiler reconstructed the same logic) — a second blind spot stacked
  on the known displacement-text one.
- **The `ld.bu` trap struck live again**: `0x36A22`/`0x36B0A` decode as `0xC64A2`, not `0xC64A3`.
- ⚠ **`close_program` on a scratch import raised a modal dialog and hung GhidraMCP.** Leave scratch
  programs open.
- ⚠ **This environment's bash heredoc does not pass `\n` literally even with a quoted delimiter.**
  Use Write/Edit for Python, not heredocs.
- **Recursive greps from the repo root fail on `ghidra_project/…lock~: Device or resource busy`.**
  Scope greps to subdirectories.

---

## 13. WHAT CLASS OF BUILD THIS IS — against the whole arc since V38

The arc: **V38–V52** authority / filters / poles / caves · **V53–V61** telemetry probes and lane mutes ·
**V62–V73** the rate lane (r24/r26) · **V74–V83a** the base-assist damper · **V84** damper reverted ·
**V85–V99** observer / plant-model probes and comparators · **V100–V103** the LKAS forward-gain ladder
(4×/8×/6×) plus arming Honda's dormant biquad.

**V104 is two things at once, and neither is a repeat:**
1. **A GENUINELY NEW LEVER.** `0xC60A8/AC/B0/B4` are **byte-stock in all 73 built images V38→V103** —
   independently verified by byte diff. `c4` has **never been proposed, priced or killed** anywhere in
   the record. Both prior biquad refusals relocated the **poles**; this moves only the **gain**, which
   is why every objection to them (pole phase, the 12–14 Hz peak, the engagement ring) evaporates.
2. **A REGRESSION REPAIR.** Lever B is **not an experiment** — it is the lever behind the operator's
   *"the audible grinding is fixed"* on V88, measured **0.40 [0.27, 0.58]** on grind #1 with the LKAS
   command band NULL. **V101, V102 and V103 all carry `0x3AA96 = c5` and `0xC6446 = 512` — stock —
   through three grinding reports.** This is the V81/V87 defect recurring unnoticed for three more
   builds.

**Closest prior relatives, and how this differs:** *raising a lane gain that feeds the aggregator* is
the V74–V83a class and the just-refused r24/r26 raise — but both of those moved lanes whose ΔG is
**2.4× the whole loop gain** (outside linear validity), while `c4` at the measured `a_filt` delivers
**ΔG = 0.038 = 72 % of the sum** — large, but inside the regime the model is identified in. It is
**not** V89's plant-model friction (a Coulomb subtraction, different mechanism) and **not** the
`0xC6CD0` gain ladder (upstream and parallel, not this lane).

🛑 **THE FACT THAT OUTRANKS THE PHYSICS.** The operator's stock arm — 688.8 s engaged, the best
baseline in the corpus — was ***"No vibration or grinding. Maybe ever so slightly, barely perceptible
ratcheting."*** Against V102 (6×): ***"Vibration and grinding somewhere between 4× and 8× torque mods.
Ratcheting was bad."*** **The symptoms track `0xC6CD0` monotonically across four operator-scored
doses. They are ours.** And **Lever B fixed grinding on V88 but did NOT move ratcheting**
(1.040 [0.759, 1.260]). **Nothing in sixty builds has moved ratcheting.** One of the operator's three
symptoms has a proven lever; the other two have no proven lever except lowering the gain, which is his
call and which he has ruled against for now.

---

## 14. HOUSEKEEPING

- `docs/BUILD-LINEAGE.md` (~201 KB) and `memory/MEMORY.md` (~179 KB) **split this session** — see the
  pointer tables in each entry file. Both were approaching the 256 KB read cap, past which a file loads
  with its tail **silently truncated**.
- **Two new memories**: `accord-honda-biquad-arm-gate-is-false-on-this-car.md` and
  `accord-427-alias-x6b94-is-the-lane-on-three-routes.md`.
- **Nine agents ran**; all confirmed stopped via the `TaskStop` bogus-id probe (`ListAgents` does not
  enumerate grandchildren — only the probe is ground truth).
