---
name: reference-accord-governor-gp0x184-chain
description: Verified chain for all 3 uVar26 branches of FUN_0007b022 governor gp-0x4f64; branch-1 (uVar26==1, steady-state LKAS-engaged) uses gp+0x1a4=MIN(gp+0x128,fVar54,gp+0x130)*1024<=4762. CORRECTED 2026-07-17: gp+0x128 is NOT vehicle-speed-adaptive, it is motor-electrical-rate-adaptive.
metadata:
  type: reference
---

# Governor gp-0x4f64 — All Three uVar26 Branches — Accord TVA-A160

Verified in FUN_0007b022 (code.bin, V850:LE, image base 0). Fully traced 2026-05-26.

## ⚠ CORRECTION 2026-07-17 — gp+0x128 is NOT "speed-adaptive"

This file's original framing (below, "gp+0x128 (0xFEDF8128): SPEED-ADAPTIVE RUNTIME VALUE") is **imprecise and was corrected this session**. Full instruction-pinned trace found the gp+0x128 LERP axis (`iVar56`, sourced from `uVar30 = *(ushort*)(gp-0x6ac0)`) is a **motor resolver electrical-angle rate of change**, not vehicle road speed. 7-hop chain, address-pinned:

1. `gp-0x6AC0` sole writer = `FUN_00041464` — slew-limited, IIR-smoothed `|value|>>10`, sign-gated against `*(short*)(gp-0x6b98)` (the delivered torque command itself — a motor-side plausibility check, not something meaningful for road speed).
2. Root source `gp-0x4f50` — raw-cast float, IIR-filtered, **range-clamped to ±13000 with invalid sentinel 65535.0** (clamp-to-invalid, NOT modulo — rules out this being a raw wrapping angle itself).
3. `gp-0x4f50`'s sole writer `FUN_00068fbe` — IRQ-protected (`__disable_irq/__enable_irq`) snapshot of `gp-0x29c4`, the classic pattern for a value an ISR concurrently updates.
4. `gp-0x29c4`'s sole writer `FUN_00068f52` — computes a **wraparound-corrected delta** between consecutive raw position samples (full-scale modulus `0x4000`=16384, the signature of a 14-bit wrapping rotary-position counter), scales it (`*120000>>14`), 2-sample-averages it, clamps to ±13000. **This is where the "mod-wraparound arithmetic" lives — it differentiates a wrapping angle into a RATE, the angle itself is never passed forward.**
5. The wrapping position sample feeding step 4 comes from `FUN_00065afe` (sole caller of `FUN_00068f52`): reads raw sin/cos ADC channel pairs (bias-corrected by `-0x800`=2048, classic differential-ADC bias removal), decodes via `FUN_0006adfe(x,y,0)` (ATAN2/CORDIC-shaped, output masked `&0x3fff` matching the 0x4000 modulus), amid FOC-mode branching (`gp-0x67ad`) and a `+0x4800` phase offset — this is the motor **resolver-to-digital (R2D) angle decoder**.

**Verdict:** branch-1 governor reduction is a function of **how fast the EPS motor is electrically rotating** (a steering-rate proxy), not vehicle speed. Practical implication: governor tapers on fast steering-wheel motion (quick corrections, lock-to-lock), not at highway speed — a materially different drivability caveat than "tapers with road speed."

**Open/unconfirmed:** `fVar48` (a magnitude-ratio scaling factor applied to gp-0x6ac0's value before rounding to `iVar56`) and `fVar40` (a MIN operand alongside gp-0x6ac0) were not traced to their sources — could carry a secondary, unconfirmed modulation. Also: `m_motor_torque_governor`@0x453F0's OWN "speed_scale" variable (`r26`, from `gp-0x6a64`) is a SEPARATE local computation from this gp+0x128 chain and has NOT been verified as speed vs. another rate proxy — do not assume it's correct by association with this correction.

⚠ 2026-07-19 partial resolution — **the BOUND question (can r26 push the clamp above unity?) is now
answered NO** (see [[reference-accord-gp4f64-three-consumers]]: r26/r28 both trace to a literal
`0x8000` seed combined only via `min`/`clamp`, never amplified). **The SEMANTIC question this
paragraph raises (is r26 actually a speed proxy, motor-rate proxy, or something else?) is still
OPEN** — the bound-verification trace did not resolve what r26 physically represents, only that it
cannot exceed unity. Don't conflate the two.

See [[reference-accord-shaper-fun42af8]] for the downstream double-clamp (this governor value + a separate static ±0x2000 clamp, both in FUN_00042af8) and the newer memory on the 3-consumer structure of gp-0x4f64 (to be added).

---

## Original 2026-05-26 trace (branch-1 "speed-adaptive" label superseded above; rest of this file still accurate)

## Common source: tp+0x7202 = 0xC6202 = 4762

```
0x7B06A:  ld.hu  0x7202, tp, r15     ; r15 = *(ushort*)(0xBF000+0x7202) = *(0xC6202) = 0x129A = 4762
```
- tp = 0xBF000; tp+0x7202 = 0xC6202; bytes [9A 12] LE = 4762
- decompile line 85: `fVar39 = 4762 * 0.0009765625 = 4.6504`
- line 125: `gp+0x130 = fVar39` (written once per call)
- lines 587-591: `gp+0x184 = fVar43` where fVar43 = MIN(fVar39, fVar44_LERP); nominal = 4.6504
- lines 606: `gp+0x128 = fVar43` (same value, written at same point)

**All three governor sources trace back to 0xC6202 = 4762 in the nominal (no-LERP-reduction) case.**

## Branch selector: uVar26 = *(byte*)(gp-0x4e5a)

Assembly `0x7C270: ld.bu -0x4e5a[gp],r10`

**Writers in FUN_00071272:**
- `0x712B8: st.b r0,-0x4e5a[gp]` — writes **0**; executed on reset/transition path (early function, mode-mismatch recovery)
- `0x756FE: st.b r6,-0x4e5a[gp]` — writes r6=`*(byte*)(gp-0x2868)`; near END of function after sustained motor computation

**gp-0x2868 writer in FUN_00071272:**
- `0x7530A: mov 0x1,r7` then `0x75310: st.w r7,-0x2868[gp]` — literal immediate 1
- This is at the tail of the sustained motor-on engagement block

**Third writer:** `0x7577E: st.b r24,-0x448a[gp]` from FUN_00075718 (body 0x75718-0x7579B) — separate sub-mode handler, r24 value unconfirmed without decompile

**Mode semantics (assembly-verified):**
- `uVar26==0`: RESET / open-loop / recovery mode. Written as r0 (zero) on mismatch paths.
- `uVar26==1`: STEADY-STATE LKAS-ENGAGED mode. gp-0x2868=1 (literal constant) written after motor validation block, copied to gp-0x4e5a.
- `uVar26==2`: ALT sub-mode from FUN_00075718 (exact conditions TBD — runtime verification needed).

**CORRECTION from prior memory:** The prior entry stated "steady-state LKAS is uVar26==0 or uVar26==2." This is WRONG. Assembly evidence shows uVar26==0 is reset/open-loop (r0 = zero literal), and uVar26==1 is written from the motor-engaged state (literal 1). The else/fallthrough position of branch-1 in the if/elif/else chain is consistent with it being the dominant operative state.

## Branch 0 (uVar26==0): uses gp+0x184

```
decompile lines 1101-1113; assembly 0x7C2AA-0x7C2E6
  0x7C2AA: ld.w 0x184[gp],r10      -- r10 = gp+0x184
  0x7C2B2: movhi 0x4480,r0,r12     -- r12 = 1024.0f
  0x7C2B6: mulf.s r12,r10,r12      -- r12 = gp+0x184 * 1024
  [NaN guard]
  0x7C2E2: st.h r9,-0x4f64[gp]     -- governor = (uint16)(gp+0x184*1024+0.5) = 4762
  0x7C2E6: st.h r9,-0x448a[gp]     -- lockstep shadow
```
Governor = **4762** (fixed cal, gp+0x184 = 4.6504 from 0xC6202).

## Branch 2 (uVar26==2): uses gp+0x184

```
decompile lines 1159-1172; assembly 0x7C37C-0x7C3BC
  0x7C37C: ld.w 0x184[gp],r10
  0x7C384: movhi 0x4480,r0,r12
  0x7C388: mulf.s r12,r10,r12
  [NaN guard]
  0x7C3B4: st.h r7,-0x4f64[gp]     -- governor = (uint16)(gp+0x184*1024+0.5) = 4762
  0x7C3B8: st.h r7,-0x448a[gp]
```
Governor = **4762** (same source, same value).

## Branch 1 (uVar26==1 — the else): uses gp+0x1a4

**THE OPERATIVE STEADY-STATE LKAS GOVERNOR.**

### gp+0x1a4 computation (decompile lines 1060-1073, assembly 0x7C21A-0x7C268)

Pre-selector block (runs for all branches, results used only by branch-1 governor):

```
line 1060: fVar44 = gp+0x128
line 1061: if (fVar54 <= fVar44): fVar44 = max(0, fVar54)
           => fVar44 = MIN(gp+0x128, fVar54)
line 1064: fVar34 = gp+0x300
line 1065: if (fVar45 <= fVar34): fVar34 = max(0, fVar45)
           => fVar34 = MIN(gp+0x300, fVar45) [used for gp+0x1ac, not governor directly]
line 1068: fVar47 = gp+0x130
line 1069: fVar45 = fVar47             -- start with gp+0x130
line 1070: if (fVar44 <= fVar47): fVar45 = max(0, fVar44)
           => fVar45 = MIN(gp+0x130, fVar44)
line 1073: gp+0x1a4 = fVar45
```

**Formula:** `gp+0x1a4 = MIN(gp+0x130, MIN(gp+0x128, fVar54))`

Key assembly: `0x7C256: st.w r11, 0x1a4[gp]` (bytes: 64 5f a5 01) — r11 holds the MIN result.

### Branch-1 governor write (decompile lines 1218-1230, assembly 0x7C454-0x7C480)

```
0x7C454: movhi 0x4480,r0,r9    -- r9 = 0x44800000 = 1024.0f (IEEE 754)
0x7C458: mulf.s r9,r16,r9     -- r9 = 1024.0 * r16 = 1024.0 * gp+0x1a4
         [r16 = r11 from 0x7C25A: mov r11,r16, i.e., = gp+0x1a4]
[NaN/overflow guard: cmp 0x477FFF00, maxf.s r0; addf.s +0.5; trncf.suw]
0x7C476: trncf.suw r6,r16     -- r16 = (uint)(gp+0x1a4 * 1024 + 0.5)
0x7C47A: bne 0x7C486           -- if gp-0x4f64 != shadow: call FUN_0006b9ee
0x7C47C: st.h r16,-0x4f64[gp] -- WRITE governor
0x7C480: st.h r16,-0x448a[gp] -- lockstep shadow
```

**Governor formula:** `gp-0x4f64 = (uint16)(MIN(gp+0x128, fVar54, gp+0x130) * 1024 + 0.5)`

## Producer chains for gp+0x128, gp+0x130, gp+0x300/fVar54

### gp+0x130 (0xFEDF8130): FIXED CAL CONSTANT

- Written at decompile line 125: `*(float*)(gp+0x130) = fVar39`
- fVar39 at that point = 4762 * 0.0009765625 = **4.6504** (from 0xC6202, same source as gp+0x184)
- Written once per FUN_0007b022 call, always = 4.6504 in this firmware
- **Class: CAL CONSTANT — does not vary with speed or operating conditions**

### gp+0x128 (0xFEDF8128): SPEED-ADAPTIVE RUNTIME VALUE

- Written at decompile line 606: `*(float*)(gp+0x128) = fVar43`
- fVar43 = MIN(LERP_output_fVar39, LERP_output_fVar44) after lines 587-590
- LERP inputs (lines 549-563) come from speed-indexed tables at tp+0x6030 (psVar12) and tp+0x620E (psVar13) with tp+0x609E=5.2002 as ceiling
- **Class: RUNTIME, speed-adaptive via LERP tables — CAN vary with vehicle/motor speed**
- Nominal value (no LERP reduction): 4.6504 (same as gp+0x130)
- Can decrease below 4.6504 at some speed conditions

### fVar54 (transient): RUNTIME energy/rate budget

- Computed from gp-0x4e79 (temperature), gp-0x6ba4, angular rate data
- Stored at gp+0x13c (decompile line ~671)
- **Class: RUNTIME — varies with motor load and operating conditions**
- Acts as additional cap on fVar44 before gp+0x1a4 computation (line 1061)

### gp+0x300 (0xFEDF8300): RUNTIME energy integrator

- Written at line 598: `gp+0x300 = fStack_48`
- fStack_48 = integrated energy budget, accumulated per call, capped at tp+0x6164
- Used to compute gp+0x1ac (not directly governor), but fVar45 from this is used in decompile line 1065
- **Class: RUNTIME accumulator**

## Nominal governor values (all branches)

| Branch | uVar26 | Source | Nominal governor | Speed-adaptive? |
|--------|--------|--------|-----------------|----------------|
| 0 | 0 (RESET/open-loop) | gp+0x184 = 4.6504 | **4762** | NO (fixed cal) |
| 2 | 2 (alt sub-mode) | gp+0x184 = 4.6504 | **4762** | NO (fixed cal) |
| 1 | 1 (LKAS-engaged) | gp+0x1a4 = MIN(...) | **<=4762** | YES (can go lower) |

**Branch-1 governor ceiling = 4762** (bounded above by gp+0x130 = 4.6504 via MIN).  
**Branch-1 governor floor = 0** (positive clamp in all paths).  
**Cannot exceed 8192** — static ±0x2000 shaper clamp in FUN_00042af8 remains the absolute ceiling.  
**In nominal steady-state:** branch-1 governor = 4762 (same as branches 0 and 2).  
**Under speed/load reduction:** branch-1 governor < 4762 (adaptive).

## Road-test prediction (updated)

- In steady-state LKAS (uVar26==1): governor = 4762 nominally; can reduce adaptively
- Governor (max 4762) IS below ±8192 shaper ceiling — governor is the real binder at full command
- To raise the governor ceiling: increase tp+0x7202 = 0xC6202 (currently 4762; 0x2000=8192 would remove it as binder)
- Whether branch-2 (FUN_00075718) is ever reached in normal LKAS needs runtime confirmation

## Related

- [[reference-accord-tva-downstream-chain]] — downstream from gp-0x6b98
- [[reference-accord-shaper-fun42af8]] — shaper clamp stack (±gp-0x4f64 before ±0x2000)
