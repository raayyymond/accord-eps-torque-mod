---
name: reference-accord-residual-lerp-gp3714-runtime-adaptive
description: SOLVES the golden model's "Y[0] UNRESOLVED" open item — the residual LERP's Y[0] and X[0] are both 0 (store-zero at 0x38d22, loop starts at index 1) so it passes through the origin; but its SLOPE is runtime gain-scheduled by two adaptive factors, so Path 2's loop gain can NEVER be closed statically. Also: 0xC6200 caps the Y table as it is BUILT.
metadata:
  type: reference
---

Traced 2026-08-10, `FUN_000389ec` @0x389ec (builds the RAM LERP that `FUN_00038148` reads to turn
`resid` into `gp-0x6b70`).

## Y[0] = 0 and X[0] = 0 — the LERP passes through the ORIGIN [EVIDENCE]

The golden model records: *"⚠ Y[0] of the RAM LERP is UNRESOLVED … the only ordinary-addressing access
image-wide is a store-zero @0x38D22 — **a lead, not an answer**."* **It IS the answer.**

`0x38d22: st.h r0, -0x3714, gp` (r0 = hardwired zero) sets Y[0] = 0 unconditionally, alongside
`X[0] = 0` at `gp-0x373c`. **The build loop then starts at index 1** (`uVar48 = 1`, offsets
`iVar32 = uVar48*2` ⇒ `gp-0x3712` onward), so index 0 is never rewritten. The other 14 `-0x3714`
references are `movea` base computations or `st.h …,-0x3714,r11` indexed writes at i ≥ 1; the
forward-propagate block copies i → i+1, never back to 0. Copy into the live table:
`0x39508 movea -0x3714,gp,ep` → `0x39522 st.h r11,-0x641c,gp`. `gp-0x641c` has exactly 4 refs
(2 in `FUN_00038148` = the LERP read, 2 here).

⇒ `resid = 0 → gp-0x6b70 = 0`. **No offset and no relay at zero.**

## 🛑 `0xC6200` CAPS THE Y TABLE AS IT IS BUILT — corrects a recorded hazard

`uVar8 = *(u16*)(tp+0x71fe+2)` = `tp+0x7200` = `0xC6200` = 8192, and inside the build loop
`if (uVar51 < uVar57) *(u16*)(Y_stage + 2*i) = uVar8;`. So `0xC6200` is a **table-shaping** cal, not only
the output clamp in `FUN_00038148`. Also lands at `gp-0x3702`.

⇒ The hazard as recorded — *"`0xC6200` = 8192 NEVER BELOW Y[0]"* — is **imprecise and vacuous as
written** (Y[0] is 0; you cannot go below it). **The real mechanism is at the TOP:** lowering `0xC6200`
caps multiple upper Y entries to the same value, **flattening the top of the LERP into a plateau = a
relay** — the V80 failure class, different trigger. ⚠ Flagged to the operator, not edited into the
shared hazard list. See [[accord-v80-damper-relay-and-grind1-inert]].

## 🛑🛑 THE SLOPE IS RUNTIME-ADAPTIVE ⇒ GATE 2 IS NOT STATICALLY CLOSABLE

```
X[i] = (RAM[gp-0x6350 + …] << 10) / iVar32
Y[i] = (RAM[gp-0x630c + …] * iVar33) >> 10
iVar32 = FUN_0003897a(clamp(gp-0x6982, 0xcc..0x800), state gp-0x3742, cals 0xC6394/96/98/9E)
iVar33 = FUN_0003897a(clamp(gp-0x6984, 0xcc..0x800), state gp-0x3744, same cal set)
```
Plus per-entry floors/ceilings scheduled on `0xC613E` / `0xC6140` / `0xC617A` / `0xC617C`, an X-axis
saturation at `LERP(gp-0x6a64)` (table `0xC76A8`), and the `0xC6200` cap.

⇒ **Path 2's loop gain is gain-scheduled at runtime by two independent adaptive factors. There is no
single slope.** Any static GATE-2 loop-gain number for a Path-2 filter edit (e.g. `0xC40D4`) **does not
exist** — a figure produced for it is an invention. **This is a property of the firmware, not a gap in
the analysis.** GATE 2 here can only be closed **empirically**: probe `gp-0x6b70` (1 writer; V87
measured it non-zero 99.80%) together with `resid` to get the realised slope on-car.

## ⊕ THE SLOPE IS PROBEABLE WITHOUT TOUCHING THE SIGNAL — probe the TABLE

Because Y[0] = X[0] = 0, the origin slope is exactly **Y[1]/X[1]**, and both are ordinary RAM cells
written by `FUN_000389ec`'s tail: **`gp-0x641a` = Y[1]** (`*(gp-0x3712)`), **`gp-0x64b6` = X[1]**
(`*(gp-0x373a)`); Y[0]/X[0] at `gp-0x641c`/`gp-0x64b8`. No differencing, no signal reconstruction.
🛑 `resid` itself is an INTERMEDIATE (`iVar6`) and `iVar4` never reaches a RAM cell — **a `resid` probe
is impossible**; this is the only route.
★ **TRY UDS/RAM READ FIRST, NO BUILD NEEDED:** the adaptation inputs `gp-0x6982`/`gp-0x6984` are clamped
into `[0xcc, 0x800]`; if they are static in practice the table is static and one at-rest read settles
the slope. EPS UDS works on bus 1 when comma isn't steering — exactly the at-rest condition.
Rung sizing: Y[1] is bounded by `0xC6200` = 8192 **by construction** (build loop caps every Y entry) ⇒
log-spaced 512/2048/6144 is honest. ⚠ **X[1] has NO static bound** (`(RAM<<10)/iVar32`, runtime) — size
it from the observed read, never guess (the V69 lesson).

## 🛑 THE `0xC63AC` IIR HAS AN ASYMMETRIC INTEGER STALL BAND (not a relay, but a nonlinearity)

`state += ((target*16 − state) * alpha_num) >> 10` @0x381B8. `>>` is SAR (floor), so the step is
**asymmetric — it can always creep DOWN but stalls creeping UP** inside `|err| < 1024/alpha_num`:
`err=+5 → step 0` but `err=−5 → step −1`. ⇒ `iVar4` biased LOW ⇒ `resid` biased HIGH.
Stall band: **alpha 102 (stock) = 0.627 resid counts · 65 = 0.985 (1.57× wider) · 59 = 1.085.**
⇒ Lowering `0xC63AC` widens a systematic offset moving OPPOSITE to the intended leak reduction.

## 🛑 WHICH LOOP `0xC63AC` IS IN — it is the PLANT loop, and that is the GATE-2 problem

- **Loop 1 (internal):** `resid → gp-0x6b70 → PID → aggregator → gp-0x6b98 → Branch A → gp-0x6bfc →
  resid`. **`0xC63AC` is NOT in it** (Branch B is a feed-in, not the return path).
- **Loop 2 (through the PLANT):** Branch B's lanes include `gp-0x6bd0` (damper, motor RATE) and
  `gp-0x6b26` (inertia comp, motor ACCELERATION) ⇒ `resid → … → motor → plant → rate/accel →
  gp-0x6bd0/6b26 → Branch B → iVar4 → resid`. **`0xC63AC` IS in this one.**

`0xC63AC` 102→65 adds **4.0° @2 Hz · 11.7° @7.79 · 13.3° @12.8 (PEAK) · 12.0° @21 · 10.3° @28**, corner
16.70 → 10.44 Hz. **The peak added lag sits ON the measured 12.8 Hz wheel-on-torsion-bar mode**, and
V88's tightest command↔column coherence² (18–24 Hz = 0.310) still eats 12.0°. ⇒ **phase spent in the
least affordable place; GATE 2 does not pass on available evidence.** ⊕ `0xC63AC` = **59 dominates 65**:
same 21/28 Hz leak (0.233/0.232) for less peak lag.

Related: [[reference-accord-observer-gate-tautology-and-term-mismatch]],
[[accord-ratchet-is-a-lightly-damped-resonance]].
