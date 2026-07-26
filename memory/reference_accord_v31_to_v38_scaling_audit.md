---
name: reference-accord-v31-to-v38-scaling-audit
description: "V31's matched boost floor fixed the observed 2x soft EME and V38 is fault-free on-car. Correction: 3584/4608 were LKAS-source-clamp+comp bounds, not whole aggregator maxima; assist joins before the governor and conservative gp-0x6acc envelope is 7322. The old absolute-margin proof is therefore not universal."
metadata:
  node_type: memory
  type: reference
---

Audit done 2026-07-18 at the operator's direction: *"The changes in V31 should show us what was needed to resolve the hard and soft faults from the 2× mod. Make sure we are learning from V31 specifically for V38 4×."* All cal values read from the actual plain images (`../accord-firmware/analysis-2020accord/_v37_plain_image.bin` carries the V31 cal set; `../accord-firmware/analysis-2020accord/_v38_plain_image.bin`).

> **V39-session correction:** the original audit treated `LKAS source clamp + max compensation` as the complete `gp-0x6acc` envelope. That omitted assist lanes summed into `gp-0x6b94` before the first governor. Conservative `abs(gp-0x6acc) <= 4762 + 2560 = 7322`, so the 4096/5120 floor does not statically dominate every assist-inclusive combination. V31's on-car fix and V38's fault-free result remain facts; the universal "integrator cannot wind" proof is retracted.

## What V31 actually did — and what it deliberately did NOT do

V31's fix was **not** to raise any state-machine threshold. Raising SM arms was **V19's approach and was not taken**. V31 instead **floored the soft-EME bound above the max command** so the integrator `gp-0x3570` can never wind on `(command − bound)`.

The reason boost is the arm that matters: hands-off, **all three bound arms collapse** — the corridor is the driver-override arm (gated off when `|gp-0x6bf0| ≤ 0xC6156`=9216), the IIR decays when the column is held, and **boost is the only arm still ON at authority ≈ 0**. Flooring boost therefore makes a **self-stable fixpoint**: bound > command → integrator can't wind → authority stays ≈0 → boost never latches off (`0xC641E`=16384) and the SMs never arm.

V30 widened only the *corridor* — the one arm gated off in exactly that regime — which is why V30 still threw a residual soft EME on a sustained hands-off turn.

## V38 inherits the mechanism correctly

The integrator is **additive**, so the correct invariant is **absolute** margin, not ratio. V38 preserves it exactly:

| | V31/V37 (2×) | V38 (4×) |
|---|---:|---:|
| max merged (clamp-sum) | 3584 | 4608 |
| corridor / boost wall | 4096 | 5120 |
| **margin (invariant)** | **+512** | **+512** |
| int/float mirrors exact at 1/1024 | ✓ | ✓ |
| all four tables flat (lockstep exact by construction) | ✓ | ✓ |

Walls scaled ×1.25 while max command scaled ×1.286 — the walls grew *slightly less*, but since the term is additive that is irrelevant; only the sign of `(command − bound)` matters, and it stays negative.

Byte-verified unchanged from stock in **both** V31 and V38: every SM threshold (`0xC6422`, `0xC641E`, `0xC61DE`, `0xC61DC`, `0xC61DA`), the corridor gate `0xC6156`, the governor `0xC6202`, the LERP_B envelope `0xC6664` (the V26 brick cal), and the fault-SM enable gate `0xC64A4`.

## 🛑 RETRACTED: the "V38 spent all its SM margin" alarm was a DOMAIN ERROR

An intermediate version of this audit compared the LKAS source clamp against SM1's threshold and the setpoint clamp against SM2's threshold, concluded both margins went `+1024 → 0`, and flagged V38 not-flash-ready. **Both comparisons were between different domains. Both alarms are FALSE and are retracted.** The traces (2026-07-18):

### SM2's operand is AUTHORITY, not the setpoint — `r13` traced

```
000432de: ld.w  -0x3570[gp],r10   ; the soft-EME INTEGRATOR
000432ee: sar   0xf,r10           ; >>15 signed
00043286: subr  r0,r24            ; |.|
000432b0: ld.hu 0x71da[tp],r16    ; cal 0xC61DA = 1092
000432ba: mulu  r16,r9,r0         ; x1092
000432be: shr   0xa,r9            ; >>10
000432c8: st.h  r13,-0x6966[gp]   ; = AUTHORITY
000432e2: ld.hu -0x6966[gp],r13   ; <- the r13 later compared at 0x436f8
```

So `r13` = **authority** = `(|gp-0x3570>>15| × 1092) >> 10`, confirming the long-standing model. SM2's `0xC6422`=16384 is a threshold **in the authority domain**. V38's setpoint clamp of 16384 is in the **setpoint** domain. **They are unrelated numbers that happen to be equal.**

**The `~15360` coincidence is fully explained:** authority ≥ 16384 requires `|gp-0x3570>>15| ≥ 16384×1024/1092 = 15363.8`. *That* is the "~15360" in [[reference-accord-override-snap-state-machines]] — the **integrator-domain** equivalent of the threshold, **not** the setpoint clamp. That memory conflated two numerically-similar values from different domains, and this audit initially inherited the confusion.

Arming SM2 requires the integrator to reach `|gp-0x3570| ≳ 503,000,000` — reachable only by sustained winding, which the bound floor prevents.

### SM1's 2048 is a qualifier inside a driver-opposition AND, not a headroom budget

Cal `0xC61DE` has exactly **one** real reader (`0x43360`; the other `71de` hits are branch-target substring false positives). Its arm chain at `0x43670`–`0x4368c` is a 4-way AND:

```
00043670: cmp r2,r15  / bnh -> NO ARM     ; velocity arm
00043674: cmp r1,r14  / bnh -> NO ARM     ; r1 = 0xC61DE = 2048 magnitude qualifier
00043678: ld.h -0x6af8[gp],r10            ; driver torque reference
00043680: mul r10,r6,r0 / 00043686: bp -> NO ARM   ; arm ONLY if cmd x dir x driver_torque < 0
0004368a: ble -> NO ARM                   ; polarity
0004368c: mov 0x3,r8                      ; ARM
```

The decisive term is the **product test**: SM1 arms only when the command **opposes the driver's hand torque**. It is a driver-override snap detector; 2048 is a magnitude qualifier *within* it, not clearance V38 consumed. Independent check: V31's merged command (3395) **already exceeds** 2048, so V31 never held "1024 of margin" to SM1 — the original table was comparing the wrong quantity.

### What actually survives the audit

Only **one** margin comparison in the original table was same-domain and therefore valid:

| | V31/V37 (2×) | V38 (4×) |
|---|---:|---:|
| bound floor − max cmd (**the invariant**) | +512 | **+512** ✓ preserved |
| governor `0xC6202`=4762 − max cmd (clamp-sum) | +1178 | **+154** ⚠ **real** |
| governor 4762 − max cmd (actual 1782+2560) | +1367 | +420 ⚠ real |

**The governor headroom collapse (7.6× clamp-sum / 3.3× actual) is the single genuine regression from V31 to V38.** Everything else scales correctly.

## Adding governor margin — the CAL-ONLY path (analysis, nothing built)

Cal `0xC6202` = 4762 has **exactly one reader**: `0x7b06a` in `FUN_0007b022`, which also writes **`gp-0x4f64`** (at `0x7c2e2`, `0x7c3b4`, `0x7c47c`). `gp-0x4f64` is then read by:

| site | function | role |
|---|---|---|
| `0x453f0` | `m_motor_torque_governor` | the actual binder |
| `0x43ae4` | `s_motor_torque_rate_shaper` | Monitor 1 |
| `0x4486e` | `FUN_00043e44` | Monitor 2 float re-derivation |
| `0x6e0f2`, `0x6e1ca` | `FUN_0006e09a`/`FUN_0006e140` | **[UNVERIFIED]** purpose |

**Structurally safer than the corridor:** `gp-0x4f64` is a **single RAM value** consumed by both the int and float sides, so raising it moves both together — there is **no separate float mirror to desync**, which is the failure mode that bricked V25/V26/V27.

⚠ **There is a hard ceiling at 10240.** In Monitor 2 at `0x4487e`–`0x44884`:

```
0004486e: ld.hu -0x4f64[gp],r12
00044876: mulf.s r8,r1,r14        ; r14 = gp-0x4f64 / 1024
0004487e: movhi 0x4120,r0,r9      ; 10.0
00044884: cmovgt r0,r14,r14       ; r14 > 10.0  ->  r14 = 0
```

If `gp-0x4f64` exceeds **10240**, the monitor's re-derivation is zeroed → divergence vs the int side → flag 6 (weight 32) → trip. **Any raise must stay well below 10240.**

Sizing (nothing built, not validated):

| goal | value | vs ceiling 10240 |
|---|---:|---|
| restore V31's **absolute** margin (+1178 over 4608) | ~5786 | safe |
| restore V31's **ratio** (4762/3584 = 1.329) | ~6124 | safe |

### 🛑 The governor raise was investigated and REJECTED (2026-07-18). Do not build it.

The open items were closed and every one came back against the change.

**1. It buys nothing where it matters.** Governor nominal **4762 > max command 4608** (4342 actual) — **the governor does not bind at nominal.** Raising it changes nothing in normal operation. It only takes effect in the **tapered** regime, i.e. `MIN(nominal, motor-rate LERP, energy budget)` when the motor is moving fast or the energy budget is stressed — *which is the thermal/mechanical protection doing its job.* Raising the cap buys torque only there.

⚠ This also **corrects this audit's own framing**: "governor headroom collapsed 7.6×" is a true observation with a **wrong implication**. It is not a fault risk. It is the pre-existing drivability caveat (*"not guaranteed 4× delivered torque at every speed; adaptive taper keyed to motor angular rate"*), restated.

**2. `gp-0x4f64` is a SHADOWED redundant variable with a HARD-FAULT-ELIGIBLE mismatch handler.** Each write site checks the live value against a shadow at **`gp-0x448a`** before storing, and on mismatch calls `FUN_0006b9ee`:

```
0007c2d2: ld.hu -0x4f64[gp],r16   ; live
0007c2da: ld.hu -0x448a[gp],r7    ; shadow
0007c2de: cmp r7,r16 / bne -> 0x7c2ec -> jarl 0x0006b9ee

FUN_0006b9ee: st.w r6,-0x4d6c[gp] ; record offender
              movea 0x17,r0,r6    ; fault index 0x17
              jr 0x0006ce7c
```

Fault **`0x17`** has `record[+8]` = `0x2D01`, `& 0x41` = **1** → **HARD-FAULT-ELIGIBLE**, the same class as the lockstep monitors (motor-off, power-cycle to recover). Same pattern at `0x7c3a8`/`0x7c470`.

**3. It feeds a limp/fallback path that writes the torque command directly.** `FUN_0006e09a` @`0x6e0f2` and `FUN_0006e140` @`0x6e1ca`:

```
0006e0f2: ld.hu -0x4f64[gp],r10
0006e100: mulh r9,r12            ; x cal 0xC7C3C = 424
0006e104: st.h r12,-0x6b98[gp]   ; WRITES the merged torque command
0006e108: st.h r10,-0x4ce2[gp]   ; its own shadow
```

Raising `gp-0x4f64` therefore raises **limp-mode torque**, not just the governor ceiling.

**4. The cal→variable chain is UNVERIFIED.** `0xC6202` is read at `0x7b06a`; `gp-0x4f64` is written at `0x7c2e2`/`0x7c3b4`/`0x7c47c` — **~4.7 KB apart**, through float math inside one very large function. That `0xC6202` *determines* `gp-0x4f64` came from a subagent claim and **could not be confirmed**. Patching a cal whose effect on the target is unproven, when the target is shadowed and hard-fault-eligible, is exactly the V25/V26 mistake shape.

**Verdict: leave `0xC6202` stock.** If it is ever revisited, all four items above must be closed first, the value kept well under the 10240 monitor ceiling, and it must be **its own build with its own road validation** — never bundled with a reach change.

## Why NOT to disable SM1 / SM2 / the governor with a code cave

- **SM1/SM2: nothing to fix.** Both "margin" problems were domain errors (above). Disabling them removes the **driver-override snap** — the mechanism that lets the driver win when fighting the wheel. On a steering system that is a primary safety function, not a nuisance fault.
- **The governor is the motor's thermal/energy protection.** It is `MIN(nominal, motor-rate LERP, energy budget)`; the dynamic terms are what prevent overheating. Disabling it risks **hardware damage**, a different and worse class than a recoverable fault. Raising the nominal cap keeps the dynamic protection intact; removing the governor does not.
- **Code caves are this kit's highest-risk change class, empirically.** V24 and V27 both used trampolines at `0xC4E00`; both faulted. **Every build that has succeeded since V29 has been cal-only.** The lockstep monitors exist precisely to catch code-path divergence, so injected code is the most likely thing to trip them — see [[reference-accord-corridor-lockstep]].

**Recommendation: pursue the cal-only `0xC6202` raise; do not cave.** If a cave later proves unavoidable, it should be its own build with its own road validation, never bundled with a 4× reach change.

Related: [[reference-accord-override-snap-state-machines]], [[reference-accord-corridor-lockstep]], [[reference-accord-watchdog-fault-sm-fun43e44]], [[reference-accord-setpoint-limit-15360-lerp]], [[reference-accord-lkas-delivery-and-governor]]
