---
name: reference_accord_stage2_knot_edit_is_a_hands_on_specific_lever
description: Editing the Stage-2 LERP Y knots 6/7/8 in the mode-24 AND mode-26 creep records is a 24-byte cal-only lever that raises f' at the hands-on operating point 2.56-3.35x with EXACTLY ZERO hands-off effect (AC off 1.0000) -- it strictly dominates 0xC63AE, a step is structurally impossible from a Y-knot edit, the edit is byte-identical at/above 40 km/h, and editing mode 26 alone would introduce a 1755-count engagement STEP where stock has zero; plus the measurement trap that the lane's 6-9 Hz energy is 16.9x larger hands-OFF so a whole-episode AC statistic swamps any hands-on lever.
metadata:
  type: reference
---

# The Stage-2 knot edit — the first HANDS-ON-SPECIFIC lever on this lane

2026-08-13, task `tracer-fprime`. Program `code.bin`. Extends
[[accord-stage2-lerp-rescale-is-identity-and-ivar6-bound]] (geometry) and supersedes
[[reference_accord_c63ae_dose_is_a_level_not_an_ac_change]] *as a candidate* (that trace's NO-GO
reasoning stands; this lever simply beats it on every axis).
Script: `…/scratchpad/fprime_flatten.py` (flash-level knot edits + route-81 scoring).

## Flash geometry, exact [EVIDENCE — `disassemble_bytes` dry_run @`0x382e0` + raw LE reads]
```
0x382e0 ld.bu 0x63fd,gp,r1   MODE BYTE (24 manual / 26 engaged)   0x382ee shl 0x2,r1  -> mode*4
```
- brk ptr `0xCC9FC+mode*4`; record ptr arrays `0xC7B40,0xC7C28,0xC7D10,0xC7DF8,0xC7EE0,0xC7FC8,0xC80B0` (+mode*4), **array stride 0xE8**
- **m24 records `0xD6158 + 0x78*j`; m26 records `0xD7130 + 0x78*j`** (j = speed slot 0..6)
- layout `+0x00` count(9) · `+0x02` X[0..8] 9×s16 · `+0x14` Y[0..8] 9×s16
- **Y[6]/Y[7]/Y[8] target cells** — m26 rec0 `0xD7150/52/54`, rec1 `0xD71C8/CA/CC`; m24 rec0 `0xD6178/7A/7C`, rec1 `0xD61F0/F2/F4`
- 🛑🛑 **CORRECTED 2026-08-21 — THIS CLAIM IS WRONG. Blast radius is NOT the Stage-2 LERP alone.**
  A fresh trace (`docs/traces/TRACE-2026-08-21-assist-map-rom-source.md`) found the shared ROM record family
  (`0xC7B40` pointer array -> m24 `0xD6158` / m26 `0xD7130`, via `FUN_000382d8`) **FORKS inside
  `FUN_000389ec` off one intermediate array `gp-0x373c[]`/`gp-0x3714[]`**:
  **Branch A** -> `gp-0x64b8[]`/`gp-0x641c[]` -> `FUN_00038148` Stage-2 LERP -> `gp-0x6b70` (Path-2,
  the PID-reference-clamp lane) -- what this memory priced; and **Branch B** -> `gp-0x6442`/`gp-0x642e`
  family -> `FUN_000352b4`'s builder -> `gp-0x37fc[]`/`gp-0x37e8[]` -> **`gp-0x6b86`, the
  torque-sensor-driven assist lane.** ⇒ **A mode-26 ROM-record edit moves BOTH lanes.** Any KNOT F / H2
  dose needs its own GATE-2 phase story for Path-1 as well, and must be sized against the aggregator
  SUM (0.053), never a lane -- see [[accord-the-8hz-mode-is-the-loop-not-the-plant]].
  The original claim below was made without knowledge of Branch B; it is retained for its method.
- ~~**Blast radius = the Stage-2 LERP ALONE.**~~ (SUPERSEDED, see above.) Each record address occurs as exactly ONE 32-bit
  literal image-wide (its own pointer cell; Ghidra xref on `0xD7130` = 1 DATA ref from `0xC7BA8`), and
  all five pointer-array literal sites (`0x38356,0x38530,0x3875a,0x38764,0x382ea`) are **inside
  `FUN_000382d8` (body `0x382d8–0x38979`)**.

## 🛑🛑 READ THIS QUALIFICATION BEFORE USING THE "NO STEP" RESULT BELOW
**MONOTONE-IN-Y ≠ MONOTONE-IN-SLOPE, and for a describing function only the second matters.** The
`maxjump` metric below proves there is **no discontinuity in Y**. It says **nothing about a
discontinuity in SLOPE**, and a Y-knot edit *always* changes slope on **both** adjacent segments:
raising one knot **flattens the segment above it**. Confirmed three ways in this kit — `arc-map`'s
`Y[6]`-alone case (`f′` 0.2485 → **0.0780**, a sharp local minimum), my own proposal A (**0.538×**), and
H2 itself (**0.36× above `|iVar6|` = 6,000**). A slope that falls then rises with amplitude is the
V80 relay/limit-cycle setup. **Never read "no step, proven" as "no nonlinearity introduced."**
⊕ The clean way to avoid it is a **LEVEL SHIFT** (move `Y[6]`,`Y[7]`,`Y[8]` by the *same* amount,
`Y[9]` pinned since it IS `0xC6200`), which leaves the interior segments **exactly** unchanged and puts
the whole cost in the final segment.

## 🛑 A STEP IS STRUCTURALLY IMPOSSIBLE FROM A Y-KNOT EDIT [EVIDENCE]
Discontinuity requires `X[i]==X[i-1]`, which no Y edit can cause; **max single-count jump over
0..14600 is 3 for stock AND for the proposal — identical.** Y monotone is enforced in code at three
ungated sites (8 rungs `0x388c4+`, `0x38de2`, `0x38e48`). ⇒ **the V78/V79/V80 relay/step failure mode
cannot be reproduced by this class of edit.** (Contrast `0xC40BC`-style relays, which are a different
structure entirely.)

## The dose and what it buys — route 81, 1.5 s hands-ON windows, bootstrap CI (n=15)
**"F" = rec0 & rec1, `Y[6]+660 Y[7]+1760 Y[8]+1760`, BOTH modes, 24 bytes, pure cal.**
`f'` 1800–3000 **0.352→0.902 (2.56×)**, 3000–5000 **0.234→0.784 (3.35×)**, **byte-identical below 1800**,
`X[8]` corner expansion **falls 9.03×→5.13×**.

| lever | LVL on | **AC 6-9 on** | CI | **AC off** |
|---|---|---|---|---|
| `0xC63AE`=2048 | 1.273 | 1.640 | [1.540,1.683] | **1.395** |
| **KNOT F** | 1.187 | **3.188** | [2.975,3.211] | **1.0000** |
| KNOT A (`Y[6]`+240 only, 8 B) | 1.062 | **0.538** | [0.514,0.993] | **1.0000** |

⭐ **A and F move `f′` BOTH WAYS at felt magnitude with zero off-target exposure ⇒ a SIGN-RESOLVING
instrument**, which matters more than the fix while [[reference_accord_path2_bracket_criterion_closes_openloop_not_closedloop]] is open.
🛑 **Only-`Y[6]` proposals score AC 1.000 or 0.538** — >half the hands-on mass is above 3,000, so
**`Y[7]` must move too.**

## Why it is hands-on-specific — AMPLITUDE, not a gate [EVIDENCE]
`FUN_00038148` has **no conditional on driver torque**; only the `|gp-0x6bfe|>20000` sentinel, the
segment search, and the ±8192 clamp. Hands-OFF `|iVar6|` **max 1,991** sits entirely below the 3,000
knot (p99 = 1,032) while hands-ON p50 = 2,731 ⇒ **disjoint segments.**
- **Byte-identical at ≥40 km/h** (rec0/rec1 leave the blend) ⇒ `0xC669A`/`0xC66A8` truncation irrelevant.
- Clamp headroom: max `|gp-0x6b70|` 3,167→4,661 vs 8,192 = **1.76×**, saturation 0.0000.
- Manual exposure 35% of frames ⇒ ⭐ **a FREE POSITIVE CONTROL** (feel it parking before engaging).

## 🛑 THE MODE FORK — edit BOTH modes
Stock's engagement step is **ZERO** below `|iVar6|`=5,000 (m24≡m26 there). **Mode-26-only would create a
1,755-count step in the PID reference at engagement** — V80 class on the mode axis.

## ⭐ THE SCORING TRAP — 16.9×, and it would have produced an uninterpretable null
Stock 6-9 Hz band RMS of `gp-0x6b70`: hands-ON **7.1** vs hands-OFF **119.4** ⇒ **the lane is 16.9×
quieter in-band when the driver pushes** (`f′` predicts 6.7×; the rest is driver damping). Engaged
frames are **67% hands-off**. **My own first pass scored F at 1.017 whole-episode; hands-ON-windowed it
is 3.188.** 🛑 **Stratify by hands-ON windows or the null is guaranteed.**

## Census (Ghidra ∖ Python EMPTY on all)
`0xC63AE` 1R/0W (`0x38242`) · `0xC669A` 1R (`0x389f8`) · `0xC66A8` 1R (`0x38a10`) ·
**`0xC613C` 2R (`0x38a58`, `0x39ff2` in `FUN_00039702`) — blast-radius flag** · `0xC6200` 15 accesses/4 fns.
⊕ **`Y[9]` and the ±clamp are the same load**: `0x38a94 ld.hu 0x7200,tp,r28` (`e5e70172`) — designed, not coincidence.

## 🛑🛑 HIGHWAY CORRECTION — added same day, after route 0x85 (V100) landed
**The creep dose above ("F", rec0+rec1) is INERT where the symptom actually lives.** Route 0x85 engaged
speed **p50 39.6 km/h, ≥50 km/h for 88.4 s, ≥80 km/h for 45.5 s**; exposure-weighted record usage is
**rec0 0.055 · rec1 0.241 · rec2 0.424 · rec3 0.203 · rec4 0.077** ⇒ rec0+rec1 carry only **0.296**.
The "byte-identical ≥40 km/h" property I reported as a *benefit* is a **defect** on this distribution.

**Corrected lever "H2": scale the Y GAPS of segments 5→6, 6→7, 7→8 by `g`, PER RECORD, all 7 records,
both modes = 21 halfwords/mode, 84 B, pure cal.** Per-record gap scaling **survives the linear speed
blend exactly** ⇒ ratio is **exactly `g` on those three segments and exactly 1.000 below `X[5]`, at
EVERY speed 0–120 km/h**. `maxjump` **identical to stock at every speed** (3/3, 4/4, 5/5, 6/6) ⇒ no step,
proven not asserted; monotone, no degenerate X, corner expansion reduced (2.89× vs stock 9.03× at creep).

🛑 **HARD CAP `g ≤ 1.891`**, set by **rec2** hitting `Y[9]`=8192 — and `Y[9]` IS cal `0xC6200` (same load,
15 accesses/4 functions ⇒ unraisable). Delivered = 1+φ(g−1) ⇒ **1.076–1.495: straddles the felt floor,
clears it only at optimistic φ.** Weaker than at creep **for a structural reason: the curve is ALREADY
less compressed at speed** (min `f′` **0.38–0.43 @80–100 km/h vs 0.181 at creep**).
⚠ **H2 itself reverses to 0.36× above `|iVar6|`=6,000** (raising `Y[8]` flattens 8→9) — the same defect
class I used to kill `0xC63AE`. Variant **H3** (carry `Y[8]` up by `Y[7]`'s absolute delta) gives 1.89× on
1,200–3,000, 1.00× on 3,000–6,000, **0.72×** above — H2-vs-H3 is decided only by the operating point.

## 🛑🛑 THE COVERAGE HOLE — `|iVar6|` HAS NEVER BEEN MEASURED ABOVE ~21 km/h
| route | build | 427 lane | engaged speed p50/max |
|---|---|---|---|
| r80 V97 · r81 V98 · r82 V99 | | **`gp-0x6b70`** (invertible) | 5.1/6.4 · 5.6/17.9 · 6.7/21.4 km/h |
| **r85** | **V100** | **`gp-0x6b94` — REPOINTED** | **39.6/104.5 km/h** |
⇒ **every invertible route is creep-only; the only highway route repointed the lane away.** Cannot say
which LERP segment the highway operating point occupies, and H2 acts only above `X[5]` (**1,200 ct at
≥80 km/h**). **Next build should be the INSTRUMENT — revert 427 to `gp-0x6b70` (V98's flown config) or
spend one rung on a 3-bit `|iVar6|` segment index — NOT the fix.**

## `0xC63AE` at highway — NO-GO stands, NEW reason
The creep-era `X[8]` corner-expansion objection **EVAPORATES** (corner becomes 0.88×/0.84×, a *decrease*).
What kills it is an **amplitude gain REVERSAL in one drive**: at 80 km/h, 2048 gives **0.70× @500 ct,
0.88× @800, 1.20× @1000, 1.76× @3000** — falls then rises = the V80 relay setup, and it lands hardest on
hands-off where H2 is exactly 1.000×. ⊕ PIN moves 14,490→**7,245**; corner moves to **3,000 @80 km/h,
below the only measured ceiling (4,770), margin 0.63×**.

## Open
Closed-loop SIGN (unchanged blocker) · **`|iVar6|` above 21 km/h (the binding gap — see above)** ·
n=15 windows is thin.
✅ **CLOSED by V100 (route 0x85):** whether the dose pushes `gp-0x6ad6` into its ±8192 PID clamp —
**b5/b6 duty 0.000000 over 249.2 s engaged** ⇒ the clamp never binds, the headroom objection is gone,
and `d(gp-0x6b94)/d(gp-0x6b70)=0.2565` is confirmed unsaturated
([[reference_accord_c6200_clamps_gp6ad6_inside_the_pid]]).
⊕ φ sanity [BELIEF, cross-route]: `0.2565 × |gp-0x6b70|` creep p50 538–883 = **138–226 ct** vs
`gp-0x6b94`'s own p50 **102** ⇒ **no extra unexplained attenuation need be posited**; φ is likely high.
Related: [[reference_accord_c63ae_arm_agnostic_residual_gain_and_zxh_wrap]] · [[reference-accord-car-is-tvca4-mode-24-26]] · [[accord-v80-damper-relay-and-grind1-inert]]
