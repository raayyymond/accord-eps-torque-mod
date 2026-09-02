---
name: reference-accord-second-driver-torque-gate-cbae4-cbbc4
description: FUN_00028ea6 has a SECOND driver-torque-indexed gain gate (0xCBAE4/0xCBBC4, PID-output stage) besides the known setpoint-stage taper (0xCBA04/0xCBA74) -- but a cmovne on gp-0x6803==2 means the operator's actual override case (opposing torque, mode==2) selects the GRAB-RATE-indexed curves instead (0xCBB54/0xCBC34), which are flat-to-near-flat, so this second gate is functionally INERT in the scenario that matters. V277's TAPER_PTRS correctly omits it.
metadata:
  type: reference
---

# A second gp-0x682f-indexed gate exists -- and it is inert in the operator's actual override case

Traced fresh 2026-09-01 (GhidraMCP, stock `code.bin`, `0x29d9c-0x2a0c4`), while adjudicating the
operator's driver-torque-feedback-loop hypothesis for V276/V277
([[reference-accord-gp4f60-no-producer-filter-raw-sensor]]). This corrects my own first-pass report
on this same task, which flagged gate (B) as a live, untouched compounding factor -- a follow-up trace
resolved it as inert in the relevant mode.

## The two gates

**(A) Setpoint-stage taper** (already known, `0xCBA04`/`0xCBA74` for the mode==2/opposing-torque
pair): X=(70,72,78,80) → Y=(254,234,12,0), a true 99%→0% cliff over 320 raw driver-torque counts,
applied BEFORE the (now ×6, V276/277) assist-map lookup.

**(B) PID-OUTPUT-stage gate** (`0x29fe2-0x2a0c2`) -- `LERP[0xCBAE4+4*variant]` and
`LERP[0xCBBC4+4*variant]`, indexed by the SAME instantaneous `gp-0x682f` (confirmed: index register
`r1`, loaded once at `0x29A7C`, unmodified through this whole span), applied to the clamped PID mixer
sum (`gp-0x6b2e`) rather than to the setpoint.

## The cmovne resolves WHICH curve actually gates, per mode

Both gate-(B) LERP results are combined with a SIBLING pair keyed on `gp-0x6830` (the "grab-rate"
index, `|d/dt(lagged gp-0x4f60)|>>6`) via `LERP[0xCBB54+4*variant]` / `LERP[0xCBC34+4*variant]`, then
selected with:

```
0029fde  cmp    r0, r25
0029fe8  cmovne r26, r9, r23     ; r23 = (r25 != 0) ? r26(grab-rate/cbb54) : r9(driver-torque/cbae4)
...
002a0ac  zxh    r13
002a0b0  cmovne r9,  r13, r9     ; r9  = (r25 != 0) ? r9(grab-rate/cbc34) : r13(driver-torque/cbbc4)
```

`r25` is set once, at `0x29a82`: `cmp 0x2, r10; setfe r25` where `r10 = ld.bu -0x6803,gp` -- **`r25 =
(gp-0x6803 == 2)`**, the SAME mode flag that selects the mode==2 bank pair for gate (A). V277's own
docstring identifies mode==2 as "the OPPOSING-torque case, which is the actual driver-override case."

**So in the operator's real override scenario (mode==2), `r25=1` (NE true) and BOTH cmovne's select
the GRAB-RATE-indexed curves (`0xCBB54`/`0xCBC34`), NOT the driver-torque fade
(`0xCBAE4`/`0xCBBC4`).** The driver-torque fade only becomes live in the OTHER mode (agreeing-sign
torque -- LKAS and driver pushing the same direction), which is not the "driver fights LKAS" case.

## The grab-rate curves are flat-to-near-flat -- for BOTH slot 0 and the car's live slot 1

Dumped fresh, both slots (⚠ CORRECTED 2026-09-01: the live slot is 7, record 11 `TVCA4` — V73 probe 2026-08-05 + V276 wire 35=7x5; slot 1 was a stale V38 belief. Slot-7 curves NOT yet dumped. Slot 1 was believed live for this car, part number
39990-TVA-A160 → `0xCD000` record 2 → selector 1, per a sibling agent's variant-matcher trace):

```
0xCBB54[0] (0xE4588 unread) / 0xCBB54[1]=0xE45A4: n=6  X=[0,3,6,8,10,20]   Y=[255,255,255,255,255,205]
0xCBC34[1]=0xE46F4:                                n=6  X=[0,3,6,8,10,20]   Y=[255,255,255,255,255,205]
```

Both slot-1 records are **identical**: flat at 255 (100% authority) across the entire normal
grab-rate range (X=0..10), dropping only to 205 (80.4%) at the single extreme top knot (X=20). So for
this car's actual coded part number, gate (B) in the operator's override scenario is **functionally
inert across normal driving** -- the only time it would attenuate at all is a grab-rate magnitude at
the very top of its range, and even then only to 80%, not a cliff.

For comparison, the driver-torque fade this gate WOULD apply in the other (agreeing-torque) mode:
```
0xCBAE4[0]=[1]=0xE44E0/0xE44FC: n=6  X=[24,45,64,80,96,112]  Y=[255,205,164,125,90,51]
0xCBBC4[0]=[1]=0xE4630/0xE464C: n=6  X=[16,26,38,48,64,96]   Y=[255,243,218,179,77,77]
```
Gentle, non-zero-floor fades (worst-case slope ≈-0.19 Y-unit/raw-count, vs gate (A)'s ≈-1.16 at its
steepest) -- not cliffs even where they ARE live.

## Consequence for V277

**V277's `TAPER_PTRS = (0xCBA04, 0xCBA74, 0xCB8B4, 0xCB924)` correctly omits `0xCBAE4`/`0xCBBC4`** --
not an oversight. Gate (B) is inert in the mode that matters for driver override, so leaving it
untouched is the right call, not an incompleteness. (V277 also leaves the grab-rate curves
`0xCBB54`/`0xCBC34` untouched, which is likewise correct -- they gate override authority downward at
most to 80%, and only at extreme grab rates.)

## FUN_0002a30e -- resolved: real, distinct, and unreachable by static call analysis

Prior kit memory flagged `FUN_0002a30e`'s liveness as unresolved and speculated it might duplicate
this PID/taper block. **Resolved this session: it does NOT** -- freshly decompiled, it implements only
the debounce/DTC-0x49 plausibility state machine (writes `gp-0x6807`/`gp-0x6758`/`gp-0x6757`, calls
`FUN_00016de6(0x49,...)`), reading `gp-0x682f` only as a threshold compare, not through either LERP
gate. So even if live, it does not add a third instance of gates (A)/(B).

**Reachability: three independent null checks, no positive hit.** `get_function_callers` → null;
`get_xrefs_to(0x2a30e)` → null; a raw Python LE scan for `jarl disp22` targeting `0x2a30e` over the
whole image (`0x13000`-`0x100000`) → zero hits; a raw scan for the literal 32-bit word `0x0002A30E`
(dispatch-table style) → zero hits. `search_instructions(mnemonic=jarl)` over the whole program
returned 500 (truncated) hits, all length 4 -- no 6-byte jarl form was seen, and none should be
expected here: `jarl disp22` covers ±~2 MB, comfortably spanning this whole ~0xED000-byte image, so a
6-byte extended form has no structural reason to appear. **Residual gap**: a register-indirect call
via a runtime-loaded function pointer cannot be excluded by static scanning, but there is no positive
evidence for one. Best current call: **`FUN_0002a30e` is unreachable**, upgraded from "unresolved."

## Related
[[reference-accord-gp4f60-no-producer-filter-raw-sensor]]
[[reference-accord-pid-output-5hz-lag-dc-gain-trap]]
