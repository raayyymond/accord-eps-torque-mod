---
name: reference-accord-rate-limits-c6194-partition-and-c520c-ceiling-scale
description: "Every rate limit on the LKAS->motor path, enumerated from code.bin. 0xC6194 IS a real 3-count/ms slew limiter on the LKAS request -- dead only because its partition (mode bytes 0xC4118, all 1) is EMPTY, NOT because 'output x0' as the kit memory records. 0xC520C's rate-adaptive ceiling knots convert to 222.8-870.1 column deg/s at 4.7121 ct per deg/s, and the table values independently settle the kit's old 8x scale ambiguity. Governor slew 0xC6206=512/tick at 1 kHz cannot bind."
metadata:
  type: reference
---

# Rate limits on the LKAS→motor path — 2026-08-12 (`fw-loop`)

Triggered by the operator's own words: *"It feels like effectively a steer angle rate limit for
LKAS engaged."* Model: `analysis-2020accord/_v97/loop_phase_model.py`.

## 1. 🛑🛑 `0xC6194` — A REAL SLEW LIMITER, DEAD FOR A DIFFERENT REASON THAN RECORDED

`memory/reference-accord-lkas-only-rate-limiter-c6194.md` says *"0xC6194 is DEAD calibration;
output ×0; no live LKAS-specific slew limit exists."* **The verdict "dead" is right. The reason is
wrong** — "output ×0" is `0xC6196` = 0, a **different cell**, on the residual path.

One reader: `ld.hu 0x7194,tp,r7 @0x27622` in **`FUN_00026c80`**, the LKAS request arbitrator
(1 kHz, `jarl @0x225f6`), producer of `gp-0x6b4a`:
```
uVar30   = clamp(gp-0x3d84, ±(0xC6192=2048 settled | 0xC6198=3072 settling))
iVar11   = gp-0x3d6c                                        # slew state
if (uVar30 >= iVar11): iVar11 = min(iVar11 + cal_0xC6194, uVar30)
else:                  iVar11 = max(iVar11 - cal_0xC6194, uVar30)
gp-0x3d6c = iVar11
residual = clamp(uVar30 - iVar11, ±LERP_{gp-0x6a62}(0xC66FE))   # Y = [256,256,256,256]
gp-0x6b4a = clamp(gp-0x3d80 + iVar11 + residual, ±25600)
```
`0xC6194` = **3 counts per 1 ms tick = 3000 counts/s**; 0 → 4096 would take **1.37 s**.

🛑 **It is fed a constant zero.** The 11-slot request array is split by the mode bytes at
`tp+0x5118` = **`0xC4118`**: `!= 0` → `gp-0x3d80` (**bypasses** the limiter), `== 0` → `gp-0x3d84`
(**through** it). **Byte-read of `0xC4118`, all 11 slots = `[1,1,1,1,1,1,1,1,1,1,1]`** ⇒
`gp-0x3d84` ≡ 0 ⇒ slew state parks at 0, residual 0, `gp-0x6b4a = gp-0x3d80`. **100 % bypasses.**

⇒ **Honda built, wired and calibrated an LKAS rate limiter and switched it off with eleven bytes.**

## 🛑🛑🛑 SAFETY — ADDED 2026-08-13 (`tracer-fprime`): **ARMING `0xC4118` DELETES THE LKAS COMMAND**
The earlier line *"arming it makes the car SLOWER — wrong direction"* **understated this badly.** Full
`decompile_function(0x26c80)` shows **the partition byte does DOUBLE DUTY**: it routes `gp-0x6298[]`
*and* **gates `gp-0x62b0[]`**, which is the live 4× LKAS command.
```c
if (*(char*)(tp+0x5118+i) != 0) iVar11 += gp-0x62b0[i];   // -> gp-0x3d88  ** LIVE COMMAND **
if (*(char*)(tp+0x5118+i) != 0) iVar47 += gp-0x6298[i];   // -> gp-0x3d80  (bypass)
if (*(char*)(tp+0x5118+i) == 0) iVar13 += gp-0x6298[i];   // -> gp-0x3d84  (through limiter)
```
**Zeroing the partition to "arm" the limiter makes `gp-0x3d88` = 0 ⇒ `gp-0x6b4c` = 0 ⇒ LKAS steering is
silently dead while openpilot believes it is steering.** ⇒ **ARMING THE LIMITER AND DELETING THE
COMMAND ARE THE SAME EDIT. NEVER PROPOSE IT.** [EVIDENCE]

**And it is dead a SECOND, independent way.** `gp-0x6b4c = clamp(gp-0x3d88 + pol*((iVar13*cal(0xC63CC))>>10), ±10240)`
with **`0xC63CC` = 0** ⇒ the rate-limited `iVar13` never reaches `gp-0x6b4c`; it reaches only
`gp-0x6b4a`, which is **≡ 0**. ⇒ **input zero AND output nowhere.**

⭐ **The useful residue: `d(LKAS demand)/dt` is UNLIMITED on the live path.** `gp-0x62b0 → gp-0x3d88 →
gp-0x6b4c → FUN_00038148` has **no slew limiter, no partition gate**, only the ±10240 clamp. Honda
rate-limited the *other* arm. Attacking the operator's `dx/dt` axis in firmware would require
**creating** a limiter = a cave = the only bricking class.
⚠ Tooling trap: the partition is reached by `movea 0x5118,tp,rX` at **ten** sites then indexed at
runtime ⇒ a per-slot displacement scan (`tp+0x5119`, `tp+0x511A`…) returns **zero hits and is false**.
⊕ Same read: **`0xC63CC` = 0** ⇒ `gp-0x6b4c = clamp(gp-0x3d88, ±10240)`.

🛑 **CORRECTED 2026-08-13 (`tracer-4x-to-term0`) — the second half of that sentence was WRONG.** The
original read on ⊕ said this means `gp-0x6b4c` "does **not** carry the LKAS command." **It does.**
`0xC63CC` = 0 kills only the `iVar13 → gp-0x6b4c` **cross-term**; it says nothing about `gp-0x3d88`,
which is `Σ_ON gp-0x62b0[]` — and `gp-0x62b0[1] = gp-0x62f8[1]` **is** the 4×-gained LKAS command,
registered by `FUN_0002b422` @`0x2b52c` (`sst.h r12,0x4[ep]`) into slot 1, which is **mode 0**.
⇒ **`gp-0x6b4c` is the 4× LKAS command's sole route**, read at `0x3816c` in `FUN_00038148`.
Conversely `gp-0x6b4a` ≡ 0 (all ten registrants write zero to field +2). See
[[accord-4x-gain-feeds-6b4c-not-term0-and-the-struct-offset-map]]. **Any lane census that assumed
`gp-0x6b4c` is LKAS-free is void.**

## 2. `gp-0x6ac0`'s SCALE, and the `0xC520C` ceiling [EVIDENCE]

`FUN_00041464` @0x41464 (1 kHz, `jarl @0x22200`):
`gp-0x359c` = one-pole LPF of `gp-0x4f50 × 0x400`, coefficient `0xC643C` = 37, **shift 7**
(a = 0.2891, fc ≈ 46 Hz). Then `gp-0x6abc` = raw, `gp-0x6abe` = filtered signed (`>>10`),
**`gp-0x6ac0` = |filtered| (`>>10`)**.
🛑 **The `×0x400` and `>>10` cancel ⇒ `gp-0x6ac0` is in the SAME UNITS as `gp-0x4f50`/`gp-0x6abe`**
⇒ **4.7121 counts per column °/s** ([[reference_accord_gp6abe_column_degps_scale_settled]]).

⭐ **The knot values are a third, independent vote for 4.7121 over the retracted 0.58901:** 0.58901
would put knot 1 at **1783 °/s** (five wheel-rev/s, impossible); 4.7121 puts it at **222.8 °/s**.

Table byte-verified: count header 5 @`0xC520C`, X @`0xC520E`, Y @`0xC5218`.

| ct | column °/s | ceiling |
|---|---|---|
| 1050 | **222.8** | 5325 |
| 1700 | **360.8** | 3584 |
| 2500 | 530.5 | 2406 |
| 3700 | 785.2 | 1587 |
| 4100 | 870.1 | 512 |

⇒ **Dead below ~223 °/s** — so inactive for the 60–61 % of the return at 13–50 °/s; **−25 % at
330 °/s, −33 % at 360 °/s.** Flat top 5325 is already below the ±10240 aggregator clamp ⇒ binding
at all rates.

**Applied to the SUM, instruction-level** (`FUN_0004503c`):
```
000453e0 ld.h -0x6b94[gp],r6   ; the AGGREGATOR SUM
000453f0 ld.hu -0x4f64[gp],r8  ; ceiling
000453f4 mul r26,r8,r0 ; 000453f8 sar 0xf,r8   ; +L
000453fa mov r8,r7   ; 000453fc subr r0,r7     ; -L
000453fe jarl 0x00049a90,lp    ; FUN_00049a90 = 3-arg ordered CLAMP
```
⇒ caps LKAS, PID, damper, boost, friction **equally**. Not LKAS-specific; the engaged-only
asymmetry is an **operating-point** difference (manual return is caster-driven and puts little
through `gp-0x6b94`).

⚠ **It produces the PLATEAU, not the RIPPLE** [BELIEF]: rate↑→ceiling↓→torque↓→rate↓ is NEGATIVE
feedback (terminal velocity). Harmonic balance: local slope −12.6 ceiling-ct per °/s, filter −6.8°
at 7.79 Hz, plant ≤−90° ⇒ ≈−97°, far from the −180° a limit cycle needs.

## 3. GOVERNOR SLEW — CANNOT BIND [EVIDENCE]
`FUN_0004503c` is `jarl @0x2293a` inside `FUN_0002214a` ⇒ **1 kHz confirmed**. Step `0xC6206` = 512
ct/tick = **512,000 ct/s**; a full ±10240 excursion slews in **20 ms** against a ~1 s return.
`0xC6208` = 205 above 16.6 km/h ⇒ 50 ms full-scale. **Not a rate limit at any observed rate.**

## 4. ZERO-COST VALIDATION
`gp-0x6ac0` ≈ **4.7121 × |CAN STEER_ANGLE_RATE °/s|** — computable from existing rlogs, no build.
Fraction of the return above 1050 ct decides whether the ceiling matters.

## 5. ⚠ OPEN — the claim that gates everything downstream
**I did NOT sweep every route from the LKAS request arrays (`gp-0x6298[]`, `gp-0x62b0[]`) to the
motor.** The AUTH-limits-the-return story in
[[reference_accord_6to9hz_loop_is_pid_torque_tracker_phase_budget]] assumes the PID lane is the
**sole** actuation route. Next step: `get_bulk_xrefs` on both arrays + a raw Python LE corroboration.

Links: [[reference_accord_6to9hz_loop_is_pid_torque_tracker_phase_budget]] ·
[[reference_accord_gp6abe_column_degps_scale_settled]] ·
[[reference_accord_c520c_cap_table_axis_provenance]]
