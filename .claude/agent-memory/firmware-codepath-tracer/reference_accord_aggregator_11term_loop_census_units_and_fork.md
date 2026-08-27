---
name: reference_accord_aggregator_11term_loop_census_units_and_fork
description: "The 11-term FUN_0003aa2c census re-done as a LOOP, not a sum. Three results that change how every Re(Z) lane number in this kit must be read: (1) the Re(Z) census is DIMENSIONALLY WRONG -- +518/-1294 etc. are aggregator counts per rad/s, not bar-torque counts, and the missing factor is the plant transfer M = d(T_bar)/d(agg count), whose FIRMWARE half (gp-0x6b94->gp-0x6b98) is ~1.0-1.07 at 0 deg same-tick but whose MECHANICAL half is not in the image; (2) gp-0x6b86 (the base assist map, FUN_000352b4) is the LARGEST torque-fed term in the sum -- memoryless, slope capped at 2.000 by cal 0xC6384, i.e. 7.8x the ENTIRE PID at 7.79 Hz -- and it has never appeared in any Re(Z) census; (3) the additive framing is structurally wrong: torque-fed and motor-rate-fed lanes are loop-gain terms in Z=(Z0+P.F)/(1-P.L), so they belong in a DENOMINATOR. With |L|~1.9-2.8 at 7.79 Hz the measured |Z|=5840 needs a numerator of only ~146-408 ct.s/rad, an order below the terms already priced."
metadata:
  type: reference
---

# The aggregator is a LOOP, not a sum — 2026-08-26/27, task `agg-census` (briefed by `ratchet`)

Program `code.bin` (stock, `list_open_programs` confirmed sole program). Fresh
`decompile_function` on `0x3aa2c`/`0x3a382`/`0x4503c`/`0x36682`/`0x361c8`, fresh
`disassemble_function(0x3aa2c)`, plus raw Python LE byte reads and a validating integer sim.

## 1. 🛑🛑 THE UNITS VERDICT — the Re(Z) census is NOT in commensurable units [EVIDENCE]

Every per-lane Re(Z) number in this kit (`gp-0x6b26` +518/+565; r24 −431…−1294) was computed as
`|lane counts| / |Ω_w| · cos(phase)`. That is **aggregator counts per rad/s**. The measured
`Re(Z) = −3073…−4890` is **torsion-bar counts per rad/s**. The conversion factor is
`M(jω) = ∂T_bar/∂(aggregator count)` and it is NOT unity and NOT zero-phase.

**The firmware half of `M` IS traceable and is ≈ unity, zero-phase, same-tick:**
```
gp-0x6b94 -> FUN_0004503c governor  : slew limiter, step cal(0xC6206)=512 (<16.6 km/h) / cal(0xC6208)=205
             @0x4545A-0x455C0         Binds at 7.79 Hz only above amplitude 512/(2*pi*7.79/1000)=10,461 ct
                                      -> PAST the aggregator's own +-10240 clamp => STRUCTURALLY CANNOT BIND
                                      at creep. Above 16.6 km/h step=205 => binds from 4,188 ct (REACHABLE).
                                      Not binding => output = input in the SAME tick (iVar20 = iVar8), gain
                                      = Q15 authority uVar6 (nominally 0x8000 = 1.000). -> gp-0x6ace
  -> FUN_000456a4 comp-add            gp-0x6acc = gp-0x6ace + comp (comp exogenous)  [st.h @0x45932]
  -> FUN_00042af8 shaper              cal(0xC64C8)=0 => pass-through; validity gate |gp-0x6acc|<=0x2000
                                      [RELAYED, not re-verified this session] -> gp-0x6b08 -> blend scaled
                                      ~ cal(0xC61DA)/1024 = 1092/1024 = 1.066 -> + gp-0x6afe -> gp-0x6b98
```
⊕ Both crux encodings re-verified byte-exact this session from a raw dump of `0x431c0..0x43210`:
`0x431C4 = 24 4f 34 95` = `ld.h -0x6acc[gp],r9`; `0x43206 = 64 5f f8 94` = `st.h r11,-0x6b08[gp]`.
`0x431CC = 85 7f c9 74`, `ld.bu` disp rule `(hw2&0xFFFE)|((hw1>>5)&1)` = `0x74c8` = **0xC64C8**, byte 0.
New neighbour cal found: `0xC61D4` (read at `0x431C8` as `ld.h 0x71d4[tp],r7`) = **0**.

⇒ **firmware leg of `M` ≈ 1.00–1.07 ∠0°.** The rest of `M` — `gp-0x6b98` → torque model
`FUN_000757a2` → Iq_ref → FOC (4 kHz) → motor constant → gearbox → column inertia → torsion bar →
`gp-0x4f60` — is **not in the image** (motor Kt, gear ratio, inertias, bar stiffness are physical
parameters). **No firmware trace can supply it.** ⇒ the census cannot be closed by tracing alone.

★ But `M` CAN be bounded from the loop itself: at the resonance `|P·L| ≈ 1`, and `|L|` is byte-derived
below, so `|M| = |P| ≈ 1/|L| ≈ 0.35–0.53 bar-ct per agg-ct`. **Converting the already-priced terms by
that factor makes them SMALLER (+518 → +276; −1294 → −690), i.e. the additive gap gets WORSE, not
better.** [BELIEF — rests on `|P·L|≈1` at the peak.]

## 2. 🛑🛑 THE UNPRICED TERM: `gp-0x6b86` is 7.8x the whole PID [EVIDENCE]

`FUN_000352b4` (caller = `FUN_0002214a` ⇒ **1 kHz**, confirmed `get_function_callers`) is the
**base power-assist map**: a 10-point LERP on `|clamp(gp-0x4f60, ±cal(0xC6200)=8192)|`, per-segment
slope hard-capped at `cal(0xC6384)` = **2048 Q10 = 2.000** (byte-read `tp+0x7384`), `× sign × POL`,
`min(·, 0x3000)`, → `gp-0x6b86`, aggregator window ±0x3000 = **±12288, the widest of all 11**.

* It is **MEMORYLESS** ⇒ transfer at 7.79 Hz is **real, 0°**, magnitude = the local slope `s ≤ 2.000`
  (domain-average bound `12288/8192 = 1.5`).
* The whole PID (`gp-0x6ad4`) is **0.2565 ∠−171.76°** at the same node. **The assist map is 5.8–7.8×
  the entire P+I+D.**
* It has **never appeared in any Re(Z) lane census in this kit.** It is not exotic — it is the
  fundamental power-assist curve — but it is the dominant torque→command term and it was omitted.

## 3. THE TORQUE-FED LOOP GAIN `L(z)` at 7.79 Hz, T_col → gp-0x6b94 counts [EVIDENCE]

| term | \|L_i\| | arg | note |
|---|---|---|---|
| `gp-0x6b86` assist map | **0.5 – 2.000** | +180.00° | memoryless, slope cap `0xC6384`=2048 |
| `gp-0x6ad4` PID P+I+D | 0.2565 | −171.76° | integer sim ≡ closed form to 4 dp |
| — its D-branch alone | 0.0979 | −91.40° | = `−2·(err[n]−err[n−1])` exactly |
| `gp-0x6ada` (reg r24) | 0.049 – 0.293 | −95.61° | `G=gain/1024`, deadband `0xC61F6`=3 |
| `gp-0x6adc` (reg r26) | 0.098 – 1.17 | −95.61° | `G_eff=(a/1024)(gainA/1024)`, **`a`=gp-0x69a4** |
| `FUN_00036682` | 0.0032 | +104.94° | `0xC646C`=891/32768 × EMA `0xC63D2`=6 |
| **NOMINAL SUM** (s=1.5, r24 G=2, r26 G_eff=3) | **1.876** | −163.91° | |
| **CEILING SUM** (s=2.0, r24 G=3, r26 G_eff=12) | **2.825** | −148.10° | |

⭐ **`r26`'s gain is PROPORTIONAL TO THE BASE ASSIST LEVEL.** `0x3ab3a ld.hu -0x69a4[gp]` → 2-tap
boxcar (`gp-0x3672` holds the previous sample) → `(a_avg · clamp(gp-0x4f62,±0x1400)) >> 10` →
`× gainA >> 10`. `gp-0x69a4` is the **assist map's own interpolated Y value** — so this lane's gain
rises with how much assist the map is delivering, i.e. with `|T_col|`, i.e. **maximal exactly in the
loaded-wheel creep regime where the ratchet lives.** No census has ever used a value for `a`.

## 4. THE FORK — the census is not incomplete, it is the WRONG TOPOLOGY [EVIDENCE for structure]

```
T_bar = Z0·Ω_w + P·(agg counts)          agg = F·Ω_w + L·T_bar
 =>  Z = T_bar/Ω_w = (Z0 + P·F) / (1 − P·L)
```
Every lane whose input is `gp-0x4f60` (assist map, PID, r24/r26, `FUN_00036682`) or the motor rate
(`gp-0x6b26` via `gp-0x6c2c`, `gp-0x6bd0` via `gp-0x6abe`) is a **loop-gain term in `L`, not an
additive contribution to `Z`.** A census that sums them is summing denominator terms into a numerator.

Arithmetic: measured `|Z| = 5840.8 ∠−125.3°` at 6–9 Hz; ring-down `Q ≈ 40` at 7.793 Hz engaged vs a
passive column `Q ≤ 2.8`. The numerator `Z0 + P·F` needed to produce 5840.8 is
**5840.8/40 = 146**, or **5840.8/14.3 = 408** ct·s/rad using the Q-ratio. **An order of magnitude
BELOW the terms already priced** — the additive census was never short of magnitude, it was
attributing to a sum what a denominator produces.

⊕ Self-consistency: `Q_eff/Q_passive = 40/2.8 = 14.3` means the loop cancels ~93 % of the mode's
natural damping. That is precisely a `1 − P·L` effect and it cannot be produced by any additive term.

**CONSEQUENCE FOR LEVERS**: a cal that changes any `L_i` moves the DENOMINATOR ⇒ changes the mode's
Q and frequency, which is exactly the observed V105 (relocated) / V106 (extinguished) behaviour.
A cal sized against an ADDITIVE budget will be mis-sized. The largest available `L` lever by far is
`gp-0x6b86`'s slope cap `0xC6384` (2048) — **untouched on every build; NOT a recommendation, it is
the base assist curve and GATE 2 has not been run on it.**

## 5. Lane-by-lane liveness at engaged creep [EVIDENCE unless marked]

| lane | window | producer | rate | live? |
|---|---|---|---|---|
| `gp-0x6ade` | ±0x400 | **none** | — | **DEAD** — 1 access image-wide (the reader `ld.h` @`0x3AA48`); raw scan of BOTH gp encodings (4-byte fmt-VII and 6-byte ext `disp=(sext16(hw2)<<7)\|((hw1>>4)&0x7F)`) = 0 writers |
| `gp-0x6b4c` | ±0x2800 | `FUN_00026c80` | — | LIVE but = openpilot's command, not a sensor lane |
| `gp-0x6ad4` | ±0x2800 | `FUN_0003a382` | 1 kHz | LIVE, ceiling ~395–830 ct at 6–20 km/h |
| `gp-0x6b62` | ±0x2000 | `FUN_00036388` | 1 kHz | **DEAD** — 0.0000 duty / 75,227 engaged frames |
| `gp-0x6b26` | ±0x400 | `FUN_00036c12` | 1 kHz | LIVE, motor-rate-ACCELERATION fed ⇒ in-loop |
| `gp-0x6bbe` | ±0x800 | `FUN_00034a72` | **100 Hz** | LIVE; ZOH into the 1 kHz sum = 0.990 ∠−14.02° |
| `gp-0x6bd0` | ±0x800 | `FUN_00034350` | **100 Hz** | **DEAD at creep** — FactorC X[0]=2240 ct=34.97 km/h, Y[0]=0 |
| `gp-0x6b86` | **±0x3000** | `FUN_000352b4` | 1 kHz | LIVE, **dominant**, see §2 |
| `gp-0x6adc` (r26) | ±0x2000 sat | inline | 1 kHz | LIVE **only while `gp-0x6b5e==0`** — see the sibling gate memory |
| `gp-0x6ada` (r24) | ±0x2000 sat | inline | 1 kHz | LIVE unconditionally (mux always resolves to a positive cal) |
| `FUN_00036682` | none | `0x36682` | 1 kHz | LIVE, self-clamped ±512, **and it feeds `gp-0x6b94` BACK IN** |

⭐ `FUN_00036682` reads `gp-0x6b48` = `IIR(gp-0x6b94·0x40)>>6` — **the aggregator's own previous
output** — and subtracts its own previous output: `sVar15 = (gp-0x6b48 + POL·((T_col·891)>>15)) −
gp-0x6b46`. That is an explicit internal feedback loop inside the aggregator, `|H| = 0.117 ∠−75.06°`
at 7.79 Hz (effective pole `1−2α`, α = `0xC63D2`/1024 = 6/1024). Another denominator, not a summand.

## 6. Add order and windows, re-verified from the disassembly `0x3acc8`–`0x3acda`
`r26 + r24 → +gp-0x6b86 → +gp-0x6bd0 → +gp-0x6bbe → +gp-0x6b26 → +gp-0x6b62 → +gp-0x6ad4 →
+gp-0x6b4c → +gp-0x6ade → +FUN_00036682()` → clamp ±0x2800 → `gp-0x6b94` (+ shadow `gp-0x4ce0`).
All eleven at **literal unity weight**. Range gates are ZERO-REJECT (`cmovc 0x0,...`), not clips;
r24/r26 are SATURATING (`cmovle`).

## 7. The D-term, exactly [EVIDENCE — integer sim ≡ closed form to 4 dp]
```
ref  = clamp(gp-0x6ad6, ±cal(0xC6200)=8192)                     # 0x3a798-0x3a7c8
err  = clamp(gp-0x4f60 − ref, ±10240)                           # 0x3a7ca sub / 0x3a7d0 addi
D    = clamp(((err[n]−err[n−1])·Kd)>>10, ±10240) · 32           # 0x3a836/38/44 ; Kd=cal(0xC6AE6)=2048
       EMA alphaD = cal(0xC644A) = 1024 ⇒ EXACT pass-through    # 0x3a860
out  = ((P+I+D)>>5)·Kout/1024 · POL                             # 0x3a874-0x3a888 ; POL applied ONCE
⇒ D's contribution to gp-0x6ad4 = −2·(err[n] − err[n−1])   (the ±10240 clamp needs |Δerr|>5120/tick: vacuous)
```
`|D| = 0.09788 ∠−91.40°` at 7.79 Hz. **Both the P-branch EMA (`0xC6450`=1024) and the D-branch EMA
(`0xC644A`=1024) are exact pass-throughs**, so `TRACE-2026-08-13`'s `H(f)` is right for stock — but it
omits BOTH EMAs and the D-branch ±10240 clamp from its formula; they matter the moment either cal moves.
🛑 **Marginal authority is EXACTLY ZERO whenever `|gp-0x6ad6| ≥ 8192`** (the reference clamp kills P, I
and D at once) or whenever the output sits on its ±ceiling. **Neither duty has ever been measured.**

## Related
[[reference_accord_kd_pid_dterm_priced_and_manual_gate]] (the D-branch trace this re-verifies) ·
[[reference_accord_r24r26_driver_torque_lane_reZ_estimate]] (the piggyback Re(Z) method this corrects
dimensionally) · [[reference_accord_dc_domain_aggregator_census_and_biquad_numerator_theorem]] ·
[[reference_accord_gp6752_is_the_frame_converter_and_k1_makes_it_lighter]] ·
[[reference_accord_gp6adc_lane_gate_polarity_and_tp_cal_offby1000]] (this session's corrections) ·
`memory/accord/firmware/accord-aggregator-reaches-motor-via-gp6acc-bridge.md`
