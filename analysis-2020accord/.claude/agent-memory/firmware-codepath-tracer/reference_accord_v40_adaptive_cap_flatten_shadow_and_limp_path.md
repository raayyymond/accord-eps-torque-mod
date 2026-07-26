---
name: reference-accord-v40-adaptive-cap-flatten-shadow-and-limp-path
description: V40's flattened adaptive-cap table (gp-0x4f64=5325 constant, slopes zeroed) does not break the shadow-duplicate check or the LERP math, but pins TWO limp-mode fallback torque paths (0x6e0f2, 0x6e1ca) to the table's max value instead of a tapered one.
metadata:
  type: reference
---

Audited V40's flattened motor-rate adaptive cap table (`0xC521A`/`0xC5232` Y-row → constant
5325, `0xC5030`/`0xC5038` slopes → 0,0,0,0), consumed via `FUN_0007b022` into `gp-0x4f64`.

**Shadow-duplicate check (instruction/decompile-verified, code.bin/stock):** confirmed
`FUN_0007b022` computes the cap 3 times (once per copy/lane) as float, rounds
(`(int)(fVar+0.5)`), then does — verbatim, all 3 sites —
```
if (*(short *)(gp-0x4f64) == *(short *)(gp-0x448a)) {
    uVar7 = round(fVar);
    *(gp-0x4f64) = uVar7;
    *(gp-0x448a) = uVar7;
} else {
    FUN_0006b9ee();   // fault index 0x17, hard-fault-eligible (motor off + power cycle)
}
```
This is a **stored-duplicate consistency check** (old value at both mirrors must already
agree), NOT an independent recomputation compared against the new value. A flat table
produces the same output every cycle regardless of table shape, so **the flatten cannot
trip this fault** — confirmed, not just inferred.

**LERP math (instruction-verified):** the table lookup is `Y[idx] + ((X-Xbreak[idx]) *
slope[idx]) >> shift` (e.g. `0x19515: iVar37 = psVar12[iVar21] + ((iVar56-psVar13[iVar21]) *
slope[iVar21*2+tp]) >> shift`, using `DAT_00006030`/`DAT_00006038` = `tp+0x6030`/`tp+0x6038` =
cal `0xC5030`/`0xC5038`, the exact slopes V40 zeroes). It's a **multiply-then-shift, not a
divide** — zeroing the slope makes the interpolation term identically 0 for every `X`, so the
result is just the flat `Y=5325` regardless of input, clamped to `[-0x7fff,0x7fff]` same as
stock. No div-by-zero, no NaN, no out-of-range store possible from this change alone. The
X-breakpoint array (`DAT_00006228`, the binary-search target) is untouched by V40, so the
index search itself is unaffected and stays in-bounds.

**Second consumer — limp-mode fallback (instruction-verified, NEW for this audit):** found
BOTH sites the operator flagged, in two sibling watchdog/staleness-handler functions:
- `FUN_0006e09a` @ `0x6e0f2-0x6e108`
- `FUN_0006e140` @ `0x6e1ca-0x6e1e0`

Both are gated by the same shape: a staleness counter compared against cal `tp+0x7c22`
(`0xC7C22`); when the delta is still under threshold (`bnc`/fallthrough, the "still fresh"
branch) they execute, byte-identical pattern:
```
r_cap = ld.hu gp-0x4f64            ; the adaptive cap
r_k   = ld.h  tp+0x7c3c            ; cal 0xC7C3C (424, untouched by V40)
r_cmd = r_cap MULH r_k             ; 16x16->16 truncating multiply (V850 MULH, no shift)
st.h  r_cmd -> gp-0x6b98           ; TORQUE COMMAND, written directly
st.h  r_cmd -> gp-0x4ce2           ; shadow copy
```
`0xC7C3C`/`0xC7C22` are outside V40's `TOUCHED_BLOCKS` (only `0xC5xxx`/`0xC6xxx` touched), so
this multiply's mechanics are unchanged from stock — **only the value flowing into `gp-0x4f64`
changes**. Since V40 pins the cap to the table's **maximum** entry (5325, the stock table's
first/peak row) unconditionally, whatever operating condition this watchdog/limp branch
represents will now always see the **peak** cap rather than a context-tapered one (stock could
serve 512/1587/2406/3584/5325 depending on the LERP's resolved index at the time). This is the
same category of concern the operator already recorded for a straight `0xC6202` raise
("raising it raises limp-mode torque") — except here it's not a raise of the nominal cap, it's
a **removal of tapering specifically in an already-degraded/limp code path**, which is a more
targeted version of that same risk.

**Not fully resolved:** I did not trace what real-world condition (motor speed? thermal?)
the LERP's X-axis represents, so I can't say how likely this limp branch is to actually fire,
nor did I decode the MULH result's downstream clamping (this write to `gp-0x6b98` almost
certainly still passes through the shared governor/aggregator, per the golden model's "same
governor and same soft-EME shaper" architecture, but I did not verify that for THIS
specific write site in this session).

See [[reference-accord-v40-governor-slew-step-65535-no-overflow]] for the paired Part-A
finding on the same V40/V42 diff.
