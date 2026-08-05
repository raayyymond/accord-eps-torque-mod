---
name: reference_accord_gain_a_index_and_leak_v73
description: r26's weight `a` (gp-0x69a4) LERP index resolved to abs(driver column torque gp-0x4f60 + mixer torque gp-0x6b4a); the "a ~ ZERO via cal 0xC6564" belief in eps_lkas_chain_model.py:689 has a BROKEN causal link (0xC6564 feeds a different RAM block, not a's table); gain_A/gain_B per-record rate breakpoints are NOT uniform across speed; V73 plateau-raise interpolation leak quantified and shown structurally incapable of reaching the two-lane-rule danger threshold.
metadata:
  type: reference
---

# `a` (gp-0x69a4) LERP index + gain_A/gain_B per-record axis + V73 interpolation-leak sizing

Resolved 2026-08-05 for team-lead's V73 hypothesis task (raise r26's plateau Y[0]/Y[1] at 0/10 km/h
while leaving Y[2]/Y[3] at V72's proven 512 cut). Full trace via GhidraMCP decompile of
`FUN_0003ad74`, `FUN_0003aa2c`, `FUN_000352b4`, `FUN_000389ec`, `FUN_00039702`; byte dumps via Python
on stock/`_v67_plain_image.bin`/`_v72_plain_image.bin`.

## 1. Per-record rate-axis breakpoints are NOT uniform [EVIDENCE: byte-read]

`v72_lane_model.py`'s docstring assumes a single shared rate axis per surface (X=[0,400,1400,3000]
gain_B / X=[0,400,1600,3000] gain_A). That's an approximation. The REAL per-record X arrays:
```
gain_A (r26):  0km/h [0,400,1600,3000]   10km/h [0,250,1200,3000]   50/100km/h [0,400,1250,3000]
gain_B (r24):  0km/h [0,400,1400,3000]   10km/h [0,400,1500,3000]   50/100km/h [0,400,1500,3000]
```
This matters for any interpolation-leak analysis: the 0km/h and 10km/h gain_A records have DIFFERENT
3rd breakpoints (1600 vs 1200), so a Y[1] raise leaks asymmetrically by speed (below).

## 2. `a`'s LERP index -- resolved [EVIDENCE: disasm 0x354CE-0x35528 in FUN_000352b4]

The store to `gp-0x69a4` (`st.h r10,-0x69a4[gp]` @**0x355C6**) is fed by a 10-segment runtime-built
slope table (breakpoints `gp-0x37fc[0..9]`, built via repeated calls to `FUN_000352a0` -- a trivial
monotonic-enforcement helper, `next = raw<=prev ? prev+1 : raw`) indexed by:
```
index = abs( clamp(gp-0x4f60, +/-cal@tp+0x7200=0xC6200)  +  gp-0x6b4a )
        (gp-0x6b4a passed through raw; only sanity-zeroed above a ~25601-count guard, never in real driving)
        result clamped +/-0x6400
```
- `gp-0x4f60` = **driver column torque, Sensor B, raw physical torque.** Address cross-check:
  `gp-0x4f60` = `0xFEDF8000-0x4F60` = `0xFEDF30A0`, matches `eps_lkas_chain_model.py:608`'s
  `col_torque_sensor_b` exactly. Established independently across ~10 prior memory files.
- `gp-0x6b4a` = **the type-8 MIXER output torque**, written by `FUN_00026c80` (3 `st.h` stores; see
  [[reference_accord_gp6b4c_lane_chain]] and the v61-taps memory). Adjacent slot to `gp-0x6b4c`
  ("LKAS demand"), same mixer, NOT the same signal r24/r26 differentiate directly (that's `gp-0x4f62`).

⇒ **`a`'s index is a TOTAL-TORQUE MAGNITUDE (driver + mixer), not a rate, and not r24/r26's own
dtorque.** Near a centred wheel with light hands, both terms are small -> index sits at the LOW end
of the 10-segment table. The table's own X/Y shape at that low end was NOT resolved this session
(would need `FUN_0003897a` + the two boost-curve LERPs below decompiled).

## 3. 🛑 The golden-model "a ~ ZERO" note (eps_lkas_chain_model.py:689) has a BROKEN causal link

That note cites cal `0xC6564` (=`tp+0x7564`) reading as 40 bytes of exact zero and concludes the
Y-base feeding `a`'s table is ~zero. **`0xC6564` is re-confirmed exact zero in stock AND V72
(byte-read this session)** -- that fact stands. But the CAUSAL CLAIM is wrong: `FUN_00039702`
(the function that reads `0xC6564`) does **not** write back to `gp-0x6444`/the Y-base array
`FUN_000352b4` reads. It reads `gp-0x6444` (as an INPUT, combined with `0xC6564`: `local_5c[i] =
tp+0x7564[i]/1024 + gp-0x6444[i]/1024`) and writes the sum to a DIFFERENT RAM block
(`gp-0x668c`..`gp-0x6674`), never touching `gp-0x6444` itself.

**The real writer of `gp-0x6444`'s range is `FUN_000389ec`** (`search_instructions operand=6444`,
10 raw hits, adjudicated -- 3 are false positives on an unrelated *positive* `tp/gp+0x6444`
displacement in unrelated functions `FUN_0004d8f0`/`FUN_0004de0c`/`FUN_00082e02`):
- `gp-0x6444` itself (slot 0 only): hard-zeroed BOTH at boot (`st.h r0,-0x6444,gp` @0x38FEE) AND
  every call via a shadow-lockstep pair with `gp-0x4bf8` (`FUN_000389ec` body, ~0x390xx).
- **BUT `FUN_000352b4`'s slope-table read loop starts at `gp-0x6442` (offset+2, slot 1), not slot 0.**
  Slots 1-9 (`gp-0x6442` through ~`gp-0x6432`) are LIVE: `FUN_000389ec` writes them from a
  rate-limited slew toward a target sourced from `FUN_00039702`'s OWN output block (`gp-0x668c`
  family, i.e. the sum computed in the paragraph above), which itself depends on two boost-curve
  LERPs at `tp+0x769a-0x76b4` and `tp+0x7b66-0x7b98` (both LIVE, non-zero cal families -- not
  independently confirmed zero) plus `FUN_0003897a` (not decompiled this session).

⇒ **This is a genuine 3-function chain (`FUN_00039702` -> `FUN_000389ec` -> `FUN_000352b4`), not a
single static table, and it is NOT identically zero** -- contra the stale note. The chain terminates
in live calibration data, so `a` is real and non-trivial, but there is **no single ROM cal an
engineer could edit to cleanly raise/lower it** -- the "measure it with the probe, don't argue it"
approach the kit already committed to (V72 bits 6/5) is correct and is the only practical path to a
number. RECOMMEND: soften `eps_lkas_chain_model.py:689` from "~ZERO ON THIS CALIBRATION" to
"BELIEF, broken causal link -- see this file" pending operator confirmation to edit the golden model.

## 4. V73 interpolation-leak sizing -- structurally capped, cannot reach the two-lane-rule threshold

Raising gain_A's Y[0]/Y[1] (rate<=250-400 depending on record) while holding Y[2]/Y[3]=512 leaks into
the interior segment up to each record's own 3rd breakpoint:
- **10km/h record: ZERO leak at rate>=1200** (clamps to Y[2]=512 exactly). Grind-2's stated >=1400
  operating threshold sits entirely inside the flat-512 region on this record.
- **0km/h record: leak extends to rate=1600.** At rate=1400 (the grind-2 threshold), ratio-vs-stock
  for a full "cut removed" candidate (Y0=Y1=3072) = 0.369x; for 2x-stock (6144) = 0.571x.
- **Mathematically capped regardless of candidate magnitude**: at the raw overflow ceiling
  (Y0=Y1=6553, see below), the rate=1400 ratio only reaches 0.597x, because weight=(1400-400)/
  (1600-400)=0.833 already weights 83% toward Y[2]=512 at that point. A plateau-only Y[0]/Y[1] raise
  CANNOT push the rate=1400 leak near 1.5x (the r26 high-rate threshold in
  [[accord-v72-two-lane-rule]] / STATE.md's two-lane rule) -- the interpolation geometry itself is the
  limiter, independent of the chosen Y value.
- At rate=3000 (the two-lane-rule's stated grind-2 corner) the leak is EXACTLY zero for every
  candidate at every speed -- 3000 sits beyond every record's own 3rd breakpoint everywhere.

Overflow ceiling (site `mul r8,r6` @0x3AB72, `stage1_max=(5120*65535)>>10=327675`):
`gain_A <= 6553` exact (`2^31 // 327675`), reproducing the kit's existing recorded figure. Headroom
%: 512->7.81, 1536->23.44, 2048->31.25, 3072->46.87 (matches recorded stock/V71A/V71C figure exactly),
6144->93.75 (matches recorded V71B figure exactly) -- both cross-checks pass.

Reproduce with `v73_dump.py` / `v73_sweep.py` (orchestrator session scratchpad; not yet moved into
`analysis-2020accord/`, ask if you want them promoted).

## Related
[[reference_accord_r24_gainb_table_structure_and_priority_gate]] -- corrected in-place this session
for the same array-index-vs-speed rotation bug this file's section 1 depends on.
[[reference_accord_r26_adaptive_lane_full_trace_and_sign]], [[reference_accord_rate_lane_v62_to_v69_gain_arc]]
-- prior r26/`a` context this session extends rather than replaces.
