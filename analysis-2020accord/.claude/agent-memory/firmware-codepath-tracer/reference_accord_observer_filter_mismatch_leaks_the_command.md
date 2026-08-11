---
name: reference-accord-observer-filter-mismatch-leaks-the-command
description: STRUCTURE of the disturbance observer (FUN_0003b8f6/FUN_00038148) with every cal byte-read - still the reference for this lane. But its headline LEAK HYPOTHESIS IS DEAD, measured on-car 2026-08-10; do NOT propose 0xC40D4 or 0xC63AC off this file. Also carries the friction exact-zeros resolution and the 0xC646E damper finding, both of which STAND.
metadata:
  type: reference
---

# 🛑🛑 STATUS, 2026-08-10 (late): THE LEAK HYPOTHESIS IN THIS FILE IS **DEAD**. THE STRUCTURE IS NOT.

`LeakDose` probed **`gp-0x6b70` itself** on-car (V86/V86B cave rungs, routes `6f`/`70`). It died three ways:
1. **No engagement response** — the raw +16 pp collapses to **+0.6 pp** under a motion screen (it was
   parked manual frames). Speed/rate-matched, the two routes **disagree in direction**.
2. 🛑 **Wrong axis, exactly inverted.** Engaged-only, `log|rate|` **+0.947 [+0.805, +1.960]** and
   **+0.573 [+0.333, +1.653]** (both exclude 0), while **`log|cmd| rms` is NULL on both**. The symptom is
   **magnitude-proportional and rate-independent**; the residual is **rate-proportional and
   magnitude-independent**. Opposite signatures.
3. **No sign coupling** — residual-vs-LKAS-command sign agreement is inside the shuffled-pairs null at
   every lag.

⇒ **team-lead has taken `0xC40D4` AND `0xC63AC` off the table.** 🛑 **DO NOT propose "`0xC63AC` 102 -> 65"
or any `0xC40D4` retune from this file** — the arithmetic below is correct and the lever is still dead.
The V86 retrodiction is separately a NULL and underpowered 3.07x
(`docs/ANALYSIS-2026-08-10-v86-leak-retrodiction.md`); an earlier line in this file called it "weak
counter-evidence", which **understated it**.

**What in this file still STANDS as reference:** the full `FUN_0003b8f6` / `FUN_00038148` structure, every
cal value, the friction exact-zeros resolution, the `0xC646E`-is-a-damper finding, and the FIR de-ranking.


Traced 2026-08-10, Ghidra `/code.bin` (stock). All cals byte-read little-endian from
`stock_fw_dump/code.bin`. tp anchor verified (`0xC40D2`=102, `0xC40BC`=600).

## The structure

```
FUN_0003b8f6  MODEL arm : gp-0x6b98 (TOTAL motor command incl. LKAS, ld.h @0x3b8f6)
                          x polarity, then 2-POLE EMA, alpha = 0xC40D4/4096 = 0.13989
              + column arm: gp-0x4f60, 2-pole EMA alpha = 0xC40D8/4096 = 0.89990 (~transparent)
              - friction - inertia   -> gp-0x6bfc -> FUN_0003bc20 -> gp-0x6bfe

FUN_00038148  RECON arm : sum of SIX lanes (gp-0x6b4e, -0x6b4c, -0x6b26, -0x6b46, -0x6bd0, -0x6bbe),
                          gains 0xC63A8/AA/A6/A4/A0/A2 ALL = 1024 = UNITY,
                          x polarity x 0xC6468 (=2639, the SAME scale as the model output)
                          then 1-POLE EMA, alpha = 0xC63AC/1024 = 0.09961, state gp-0x374c (32-bit)
              residual = gp-0x6bfe - (gp-0x374c>>4) + clampv(gp-0x6bfa,20000)
                       -> sign(res)*LERP(|res|*0xC63AE) -> clamp +-0xC6200 (8192) -> gp-0x6b70
```

Matched units are deliberate (same `0xC6468`). **The filters are NOT matched.**

## The mismatch (|H_model - H_recon|, fs = 1 kHz)

| f | 2 | 6 | **7.8** | 15 | **21** | **28** |
|---|---|---|---|---|---|---|
| \|dH\| | 0.041 | 0.120 | **0.152** | 0.249 | **0.285** | **0.293** |
| dphase | -2.4 | -7.3 | -9.6 | -19.5 | -27.2 | -34.8 |

Zero at DC (both EMAs have |H(0)| = 1 exactly). **Peak magnitude 0.293 is task-rate invariant** — at
fs = 500 Hz the same peak simply moves to 9-15 Hz. => up to ~29% of the delivered command reappears as an
unexplained residual, in both complaint bands.

## Dose already flown, unknowingly: V86

`0xC40D4` 573 -> 286 takes peak |dH| **0.293 -> 0.661 = 2.26x WORSE**. Operator's V86 report was
*"maybe a smidge better, if at all; ratcheting definitely perceptible"* => **no clear worsening**, which is
**weak counter-evidence against this mechanism**. Parking-lot-only route. Quote this whenever the finding
is used.

## 🛑 The former "single-cal fix" — RETAINED ONLY AS A DEAD-LEVER RECORD. DO NOT PROPOSE.

Superseded by the on-car `gp-0x6b70` probe above. Kept so a future session recognises it as *tried and
dead* rather than *never considered*:
- `0xC63AC` 102 -> 65 was the arithmetic optimum (peak |dH| 0.293 -> 0.182). **Never flown. Lever dead.**
  It was independently **blocked** anyway: `0xC63AC` is on `build_v83a_tva.py`'s explicit must-not-move
  list (lines 337, 369), a "<=1.32x bound" depends on it.
- `0xC40D4`->4096 with `0xC63AC`->1024 would zero |dH| exactly, at the cost of the actuator-lag model.
  **Dead.** ⚠ Note `0xC40D4` **has flown once** — V86, 573 -> **286**, the *wrong* direction (2.26x worse
  leak), fault-free, and NULL on its frequency pre-registration.

⚠ **Transport tick:** team-lead's and ObserverMatch's leak figures carry a **+1 tick** on Branch A that
mine did not; theirs reproduce the golden model's independently-recorded **-36.06 deg at 7.79 Hz**, which
requires it. **Use the +1 tick** in any future arithmetic on this lane.

## ★★ THE FRICTION TERM'S "EXACT ZEROS" ARE THE PROBE'S QUANTISER, NOT A GATE

Settled 2026-08-10 after `FlightV89` measured `gp-0x6ae2` exactly zero on 46.4-50.5% of engaged frames,
rate-driven (P(zero) 0.865 at <0.05 deg/s -> 0.011 above 25 deg/s). Three candidate causes; the answer is
none of the two proposed.

**1. `ratio` is CONTINUOUS — there is NO three-valued `sign()`.** [EVIDENCE]
`0003bad0: divf.s r14,r12,r14` is a plain float divide (`iVar20/600`), two-sided-saturated by
`0003bad8 cmp/ble` + `0003bae4 maxf.s`. Nothing tests `gp-0x6abc == 0`. `ratio -> 0` linearly.
⊕ Hard number: **`ratio` saturates at |gp-0x6abc| >= 50 counts** (cal `0xC40BC`=600, /12).

**2. `|model|` does NOT collapse at low rate.** [EVIDENCE] `0003ba8a: maddf.s r13,r14,r7,r8` gives
`model = model_cmd + (w*lead)/1024` — the `gp-0x6a10` angle LERP weights **only the additive column term**.
`model_cmd = EMA2(gp-0x6b98*pol/1024)` is a separate summand, untouched by `w`. So the LERP being dead over
88.6% of its domain is NOT the mechanism.

**3. THE CAUSE:** `0003bbec: movhi 0x4480,r0,r11` (=1024.0f) · `0003bbf4: mulf.s r11,r13,r14` ·
`0003bbfc: trncf.sw r14,r12` · `0003bc04: st.h r12,-0x6ae2[gp]`.
⇒ **`gp-0x6ae2` is exactly zero iff `|friction| < 1/1024 = 0.0009766`.** With K0=0,
`friction_ss = |model| * (|gp-0x6abc|/50) * K1/1024`, so **zero <=> `|model|*|gp-0x6abc| < 0.4902`** at
K1=102. A fixed floor on a PRODUCT of two quantities that both shrink at low rate is exactly a monotone
sigmoid in log-rate — which is the observed 80x span.

**4. THE FRICTION EMA EXISTS — settles a direct inter-agent conflict (one agent asserted "no EMA on this
term, it is an algebraic product evaluated per tick"; that is WRONG).** [EVIDENCE]
`0003bb1a: ld.w -0x362c[gp],r16` (load state) · `0003bb22: ld.hu 0x50d0[tp],r14` (cal `0xC40D0`=408) ·
`0003bb2a`/`0003bb2e` (the `+= (in-state)*408/4096` arithmetic) · `0003bb38: st.w r16,-0x362c[gp]` (store).
Census of `gp-0x362c`, both encodings, whole image: **exactly 1 writer and 1 reader**, both inside
`FUN_0003b8f6`. alpha = 0.09961.
⊕ Independent corroboration from the flight data: tau = 1/alpha ~ 10 ticks = **10 ms @1 kHz**, so 2-3 tau =
**20-30 ms** = exactly the observed median zero-run length. An algebraic per-tick product would dither at
the **sample period (~1 ms)**. The run-length statistic is itself evidence the EMA is there.

**DOSE VERDICT: K1 is reachable and a K1 dose is a coherent experiment.** `friction` is exactly linear in
K1 (one `mulf.s` at `0x3bafe`/`0x3bb0e`, no gate/threshold/branch between it and the output), so doubling
K1 **halves the zero threshold** => the `gp-0x6ae2` zero duty must fall in every partially-zero rate bin.
**That is a free positive control that the dose is in force.** ⚠ Reachable != large: at 1-13 deg/s the term
is genuinely small, and doubling it doubles a small number.

✅ **CLOSED 2026-08-10 (late): `gp-0x6abc` ≡ `gp-0x4f50`, IDENTITY — no scaling, no offset, on stock.**
[EVIDENCE, `FUN_00041464` decompiled] The cell has a scaling path
(`gp-0x6abc = cal(0xC648E) + (rate*cal(0xC6134))/1000`, with `0xC6134`=1000, `0xC648E`=0) but it is
**gated off two independent ways**: a **magic word `0x49d6b173`** loaded via `*(gp-0x3490)+4` (a
debug/calibration-mode signature) **AND** a byte cal that must equal `0xE9`. Both must hold; neither does.
The live `else` branch is the bare `gp-0x6abc = s16(gp-0x4f50)`. Writer `0x4170c` (the identity store);
`0x416fc` is the dead scaled store.
⊕ **All four sibling rate cells share the structure and all four gates are uniformly off**: `gp-0x6ac2`,
`gp-0x6ac0`, `gp-0x6abe`, `gp-0x6abc` ← byte cals `0xC40EB`/`EC`/`ED`/`EE`, every one **`0x00`**.

🛑 **ADDRESS TRAP, hit and caught in this very lane:** `tp+0x50EE` is **`0xC40EE`**, NOT `0xC50EE`. An
earlier pass of this analysis reported `0xC50EE`=136 because the address was typed rather than computed —
the off-by-0x1000 trap, sixth recurrence. The conclusion was unchanged (neither value is `0xE9`) but the
address was wrong. **Compute `tp+off` in code, always.**

⇒ **The relay's saturation point is a hard cal-derived number:** `ratio` saturates at
**|gp-0x4f50| >= 50 counts** (`0xC40BC`=600, /12) = **10.61 deg/s at the steering wheel** (at 4.7121
ct/(deg/s); the knee is confirmed on-car by b6 duty steps 0.104->0.312 and 0.042->0.148 straddling it).

🛑 **DO NOT express that as a fraction of the 13000-count validity window.** I did (50/13000 = "0.385% of
full scale") and drew from it that **|r| = 1 essentially everywhere** — a **non sequitur**, corrected by
ObserverMatch. 13000 is where the sensor is declared BROKEN, not the range it occupies; and a range
fraction says nothing about a distribution. **The measured answer is the opposite:** against engaged
wheel-rate exposure, `|rate| >= 10.61 deg/s` on only **13.3% of frames**, median `|r| ~ 0.1-0.25`
⇒ **the bilinear-in-rate region is where the car actually operates and |r| = 1 is the MINORITY case.**
(Consequence: the describing-function even-harmonic ladder `r*g*4/(3pi)` — 4.2% at stock K1=102, 8.5% at
V89's 204, 25.4% at 3x, 42.4% at the K1=1024 half-wave-rectifier ceiling — is computed at |r|=1 and is
therefore an upper bound; at the real median it needs 1.4-3.8x more K1 than the ceiling allows.)
⊕ **`gp-0x6c38` = `|gp-0x4f50|` is written live in the same function** (invalid branch writes `0xffff`)
⇒ the rate magnitude is already in RAM and directly probe-able; `|r|`'s distribution can be a measurement
rather than a substitution.

⊕ Probe resolution, if ever needed (a note, not a proposal): `0x3bbec`'s `movhi 0x4480` is the shared
x1024.0f for **both** `gp-0x6ae0` and `gp-0x6ae2`. `0x4480 -> 0x4500` = x2048.0f doubles resolution and
still fits s16 (both terms clamp +-10.0 => +-20480 < 32767). **x4096 OVERFLOWS.** Both cells are
1 writer / 0 readers in both encodings.

## Other cals byte-read here (stock)

`0xC4048/0xC404C/0xC4050` (f32) = **1.0 / 0.0 / 0.0** — the column-torque 3-tap FIR is a **pass-through,
NOT a derivative**. Never edited in 88 builds (only in KEEP/verify loops). 🛑 **Width trap: all three read
`0x0000` as u16 because `1.0f = 0x3F800000` puts its non-zero bytes in the upper halfword — that is how
they were once wrongly declared dead. Read as f32.**

🛑 **THE FIR TAPS ARE A DEAD LEVER — de-ranked 2026-08-10 after being nominated as the kit's most
promising "disabled-but-present" candidate. Two independent EVIDENCE arguments:**
1. **Wrong branch.** `model = EMA2(cmd) + FIR(EMA2(T_col))·K·w(angle)`. The A-vs-B leak is entirely in the
   FIRST term; the FIR multiplies `T_col`, an *additive* term ⇒ **no coefficient can change the command's
   transfer function.**
2. **No phase authority.** Taps are 1 sample apart, so a 3-tap FIR spans **2 samples**; the −30.9° V88
   measured (command↔column @7.79 Hz) needs **11.0 samples**. Swept: `(1,−0.5,0)` buys **+2.8° at 7.8 Hz**
   and halves DC; a differencer `(1,−1,0)` gives |H| = **0.049** at 7.8 Hz (annihilates the band, since at
   1 ms spacing a first difference is a 1 kHz operator); **any tap sum ≠ 1 rescales the DC driver-torque
   estimate.** ⇒ a gain trim with a DC side-effect, not a filter.

⊕ There are **THREE** identical `[1.0,0.0,0.0]` triples, not two: `0xC4018/1C/20` (sole readers
`0x3b6c0/c4/d4` in **`FUN_0003b66a`** — a *second* column-torque estimator immediately preceding
`FUN_0003b8f6`, also reading `gp-0x4f60` @`0x3b672`), `0xC4024/28/2C` (`FUN_00023xxx`), and the observer's
`0xC4048/4C/50`.
`0xC4080` (K0 pure Coulomb) = **0** — pure Coulomb is OFF in stock; only K1 `0xC40D2`=102 is live.
`0xC40D0`=408 (friction EMA) · `0xC40D6`=246 (inertia EMA) · `0xC613A`=1159 · `0xC646E`=1428 ·
`0xC6468`=2639 · `0xC63CC`=0 · `0xC6200`=8192 · `0xC63AE`=1024.

`0xC646E` = the "INERTIA" gain, ONE reader (`0003bb92`), frozen at **1428 on every image V38->V89**
(51 builds, never written). It multiplies a double-EMA'd derivative of `gp-0x6abc` (<- `gp-0x4f50`) =
motor angular acceleration, never the LKAS command. Subtractive **inside the observer only** —
`FUN_0003b8f6` writes no command anywhere, so it compensates the ESTIMATE, not the PLANT. Hard-clamped
+-10.0 => +-26,390 against a +-20,000 output clamp, i.e. it can saturate the model output alone.

🛑 **IT IS NOT INERTIA COMPENSATION AS DELIVERED — it is a LAGGED VELOCITY DAMPER.** [EVIDENCE, computed
2026-08-10] The `diff`'s +90 deg is eaten by the 2-pole EMA at alpha = `0xC40D6`/4096 = 0.06006
(corner **9.56 Hz** at fs = 1 kHz). Phase of the term vs RATE, with Re/|H|:
1 Hz +78.6 (0.198) · 4 Hz +46.5 (0.688) · **7.79 Hz +14.7 (0.967)** · 12 Hz -9.1 (0.987) ·
**21 Hz -36.0 (0.809)** · **28.5 Hz -46.8 (0.684)**. Real part is positive and large across the whole
7.79-28.5 Hz span (true inertia comp needs Re~0, Im~1); it is inertia-like **only below ~1 Hz**.
**Raising it** => bigger rate-proportional term subtracted from the model => residual down =>
`gp-0x6b70` down => reference `gp-0x6ad6` down => `error = T_col - ref` up => PID commands MORE assist
with rate => **LIGHTER wheel with rate; it un-damps the delivered torque.** [BELIEF on the last step —
rests on [[accord-friction-polarity-more-assist]], not re-walked link by link.]

## The observer's GATE FLAG — three exactly equivalent tests, all single-sourced [EVIDENCE]

`FUN_0003bc20` is a deterministic sentinel relay, whole function:
```c
sVar2 = s16(gp-0x6bfc);
if (sVar2 + 20000U < 0x9c41) { uVar1 = 0x400; } else { uVar1 = 0xffff; sVar2 = 0x7fff; }
gp-0x6bfe = sVar2;   gp-0x695c = uVar1;
```
The success path clamps `gp-0x6bfc` to +-20000 and `20000+20000 = 0x9C40 < 0x9C41` **passes**, so **only
the `0x7fff` sentinel fails.** Therefore:

**`gp-0x6c00 == 0xFFFF`  <=>  `gp-0x695c == 0xFFFF`  <=>  `gp-0x6b70 == 0x7FFF`  <=>  the observer's
input gate failed.**

Census, both encodings, whole image — every cell in the chain is **single-sourced**, so no other writer can
forge the flag: `gp-0x6bfc` 1W(`0x3bc1a`)/1R(`0x3bc20`) · `gp-0x6bfe` 1W(`0x3bc3e`)/1R(`0x38218`) ·
`gp-0x6b70` 1W(`0x382d2`)/1R(`0x38006`) · **`gp-0x6c00` 1W(`0x3bc16`)/0R** · **`gp-0x695c`
1W(`0x3bc42`)/0R**.
⊕ The last two have **zero readers** => pure telemetry mirrors, **zero blast radius** as probe rungs.
⊕ `|gp-0x6b70| >= 8193` is also exact: the success path clamps to +-`0xC6200` = +-8192 *inside* the branch
while `0x7fff` is written outside it.

🛑 **`gp-0x6b70 != 0` is the WRONG test for gate health** — the FAIL path writes a *non-zero* sentinel, so
"non-zero 99.80%" says nothing about how often the gate fails. Use one of the three equalities above.
(Recorded because this exact mis-citation was made and had to be retracted.)

## Coverage gap (separate from the filter mismatch)

The recon covers 6 of the 12 aggregator-plus-direct contributions. Missing: `gp-0x6ade`, `gp-0x6b62`
(`FUN_00036388`), `gp-0x6b86` (`FUN_000352b4`), and **both rate lanes**. `gp-0x6ad4` (the PID) is
deliberately excluded — it is the feedback term.

Related: [[reference-accord-assist-channel-framework-lkas-is-channel1]].
