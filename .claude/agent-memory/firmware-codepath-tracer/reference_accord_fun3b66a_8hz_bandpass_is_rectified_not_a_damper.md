---
name: reference_accord_fun3b66a_8hz_bandpass_is_rectified_not_a_damper
description: FUN_0003b66a really does contain a band-pass peaking at 8.13 Hz with +1.44 deg phase (cals 0xC63B4=51, 0xC63B8=41) — but its output is rectified to gp-0x6ba6=|gp-0x6b9a| and consumed ONLY as a table index and a ±25600 plausibility window, never summed into the assist demand. abs() destroys the phase, so "in phase with rate ⇒ viscous damping" does NOT hold; this is amplitude-triggered BOOST gain reduction, not a damper
metadata:
  type: reference
---

Traced 2026-08-09 (`EXCITATION-TRACER`) to answer the team-lead's "**what is the SIGN of `gp-0x6b9a`?**"
question, which was framed on the belief that `FUN_0003b66a` is a band-pass **damper** aimed at the
operator's 8 Hz ratchet. **The frequency analysis is confirmed; the CLASS is refuted.**

## The band-pass is REAL and correctly centred [EVIDENCE, decompile + numeric]

Cals byte-read, **stock and V86B identical, never touched by any build**:
`0xC63B4` = **51** (both EMA stages) · `0xC63B6` = **1** (output scale) · `0xC63B8` = **41** (gain)
· `0xC63BA` = **512** (Branch B's EMA).

```
gp-0x6abc (motor rate) → clamp ±2000 → slew ±565/tick → d/dt ×17.453293 (=π/180×1000, deg→rad @1kHz)
   → EMA(α=51/1024) → EMA(α=51/1024) → ×41/1024 → clamp ±10.0 → ×1024 → Branch A
```
| f (Hz) | \|diff\| | \|EMA²\| | **\|TOTAL\|** | **∠TOTAL** |
|---|---|---|---|---|
| 7.00 | 0.0440 | 0.5744 | 0.02526 | **+9.79°** |
| 8.13 | 0.0511 | 0.5002 | **0.02555** | **+1.44°** ← peak |
| 10.00 | 0.0628 | 0.3981 | 0.02501 | −10.00° |
| 20.00 | 0.1256 | 0.1420 | 0.01784 | −42.21° |

## 🛑 But Branch A is the MINORITY term, and the output is RECTIFIED

`0x3b86a add r14,r28` sums Branch A with **Branch B** = 2-pole EMA α=**512/1024=0.5** on
`gp-0x4f60 × 4` then `sar 0x2` (net ×1) ⇒ at 8 Hz **\|H\|=0.9950, −5.75° = raw torque pass-through,
full scale**. Branch A is clamped to **±10240** counts. So:
```
gp-0x6b9a ≈ raw_torque + (small clamped 8 Hz bump)      gp-0x6ba6 = |gp-0x6b9a|
```
⇒ this is the **boost amplitude index** already on record, with an 8 Hz ring-detector bump added.

⚠ `gp-0x6de8` (`0x3b866`) and `gp-0x6de4` (`0x3b846`) are **write-only telemetry, 0 readers** — but the
QUANTITIES are live via **register reuse** (`st.w r28,-0x6de8,gp` then `add r14,r28`). Exact same trap
class as `gp-0x6ad0` in `FUN_000456a4`. Patching those cells does nothing.

## 🛑🛑 THE SIGN QUESTION IS MALFORMED — no summing junction exists

`gp-0x6b9a`: **1 writer, 7 readers** [full-opcode Python census {0x38..0x3F}, both disp forms]:
`0x3B8B0` write · `0x3B8A4` shadow self-compare vs `gp-0x4ce4` ·
`0x34414`/`0x3441E`/`0x34428` (`FUN_00034350` damper) · `0x34B5E`/`0x34B68`/`0x34B72` (`FUN_00034a72` boost).
**ZERO readers in the aggregator, governor, comp-add or shaper.**

The signed value **dies in a register after one comparison** — the symmetric `|x| ≤ 25600` window:
```
0x34414  ld.h  -0x6b9a, gp, r13      ; 246f6694
0x3442E  addi  0x6400, r13, r12      ; +25600
0x34432  ori   0xc801, r0, r8        ; 51201
0x34436  cmp   r8, r12 / 0x3443C bnc 0x3446A     ; fail -> BAIL
0x34448  ld.hu -0x4f68, gp, r13      ; r13 OVERWRITTEN => gp-0x6b9a DEAD
```
Same idiom in boost (`0x34c9c` addi, `0x34ca4` `ori 0xc801,r0,r15` overwrites r15).

The value path is the **unsigned** twin: `0x34424 ld.hu -0x6ba6,gp,r10` → `0x34438 st.h r10,-0x6bcc,gp`
= **FactorB's index** in the damper; and `0x34B6E ld.hu -0x6ba6,gp,r9` = the shared **LERP1/LERP4 index**
in boost.

⇒ **`abs()` destroys the phase.** "+1.44° ⇒ in phase with rate ⇒ viscous damping" **does not hold**,
because the signed quantity whose phase was measured is not what propagates. This is **amplitude-triggered
gain scheduling**, not a damping torque. LERP1 `0xD28DC` Y=`[16384,14657,11672,9365,8244,8187]` is
**monotonically decreasing** ⇒ bigger index ⇒ **less boost**.

## Dose ceiling on `0xC63B8` — raising it too far switches the lane OFF
- The **±10.0 clamp binds** once the 2nd EMA exceeds **249.8**; doubling 41→82 halves that to 124.9.
  Past the clamp, raising the cal buys **nothing**.
- If the sum exceeds **25600**, the plausibility window **fails** ⇒ in boost `r21=0` forces the LERP4
  blend state `gp-0x69ba` to **0**.

## At CREEP only the boost half is live
`gp-0x6ba6` → `gp-0x6bcc` → FactorB, but `FUN_00034350`'s output is a **PRODUCT** and FactorC `Y[0]=0`
below 20/35 km/h ⇒ the damper term is **exactly zero at creep regardless of FactorB**.
⇒ at the operator's speed the **only** live effect of `0xC63B8` is **boost attenuation**.

## What this lane CANNOT see
**r24/r26** enter `FUN_0003aa2c` directly from `gp-0x4f62` with **no dependence on `gp-0x6b9a`/`gp-0x6ba6`**
— +84° lead, **3.000× at creep**. The largest 8 Hz-active element is outside this mechanism entirely,
which **caps the benefit**.

⚠ Residual: **6-byte extended-disp23 form not checked** for either cell. Corroborated two ways, not certified.

## Related
[[reference_accord_gp6b9a_r21_gate_and_fault_sentinel_mechanism]] — prior trace; its "gate input, not
index" core is **re-confirmed** here at instruction level. Its "float biquad" claim was retracted by the
team lead (coeffs `(1.0,0.0,0.0)` = pass-through FIR) and that retraction stands.
[[reference_accord_creep_damping_dead_rate_gain_max]] — why the damper half is inert at creep.
[[reference-accord-fun456a4-gp6ad0-resolved-live-damping-no-step]] — the same write-only-cell/live-register trap.
