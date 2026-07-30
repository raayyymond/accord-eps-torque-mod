---
name: accord-slew-limiter
description: "🛑 THE FIX THIS FILE RECOMMENDS IS REJECTED — do not set 0xC61D6 to 14. Slew/rate limiter in s_motor_torque_rate_shaper (FUN_00042af8) for 39990-TVA-A160; step tp+0x71d6 = ABS 0xC61D6 = 0 (DISABLED in stock; the 0xC71D6/14 reading was an off-by-0x1000 error). accumulator gp-0x356c, SYMMETRIC. Addresses below are good; the 0->14 RECOMMENDATION is falsified."
metadata:
  type: reference
---

# 🛑 CORRECTION 2026-07-30 — THE RECOMMENDATION IN THIS FILE IS REJECTED

**Do NOT propose `0xC61D6` 0→14.** This file's closing advice ("FIX = set 0xC61D6 to 14 (V16)") was
**dismantled by an 11-round, 4-analyst, decode-verified Ghidra review** and V16 was never flashed. From
`memory/project_accord_torque_mod_v0.md` (the V18 block, 2026-05-27):

> **V16 REJECTED:** slew `0xC61D6` 0→14 does not "re-enable a damper" — slew=0 **FREEZES** a dormant
> speed×torque 2D shaping lane (`gp-0x356c`, fed by curves `0xC6770`×`0xC69E8`); 0→14 **ACTIVATES an
> uncalibrated map onto the live command** (mux `0xC64C9`=0). **Highest-risk lever; last/never.**

Also settled by the same review, and contradicting this file's framing:
- **`0xC6424` (V17, deadband-only) is INERT** — it gates only the `gp-0x356c` limiter, and with slew=0
  that state is pinned at 0. Deadband and slew are COUPLED; neither is independently useful.
- **The real EME cut node is the override SM `gp-0x6960`**, NOT the shaper deadband this file describes.
- **`0xC64DE` (re-engage ramp) is the lever that actually targeted the recovery ratchet**, and it
  LENGTHENS re-engage (it was mislabelled "faster"). V18 flashed it 17→27 and the operator
  road-validated it. Byte-verified 2026-07-30: `0xC64DE` = 27 in V31/V38/V42/V53/V55/V57 — carried
  forward correctly, still live.
- **There is NO output rate-limiter available as a calibration.** `gp-0x6b98` has only ±0x2000 plus a
  ±5 change detector; an asymmetric down-rate limiter would need a trampoline code patch
  (`0x43b52`→cave), which was scoped in that review and deliberately never built.

Byte-verified 2026-07-30 across `_v31/_v38/_v42/_v53/_v55/_v57_plain_image.bin`: `0xC61D6` = 0,
`0xC6424` = 29491, `0xC64C9` = 0 in **all** of them — stock throughout the current lineage.

**Why this correction exists:** on 2026-07-30 a subagent hunting a rate-limiter cause for the ~7.4 Hz
ratchet re-surfaced this file's recommendation as a fresh candidate. It is not fresh; it is rejected,
and it is the highest-risk lever in the file. The addresses, encodings and structural notes below remain
accurate and useful — **only the recommendation is wrong.** See `docs/BUILD-LINEAGE.md` (which does not
list `0xC61D6` at all — that gap is what allowed the re-proposal).

---

## Accord TVA-A160 Rate Shaper Slew Limiter

**Function:** s_motor_torque_rate_shaper / FUN_00042af8

**Slew limiter present but DISABLED in stock (step=0).** Classic incremental ramp form: `prev += clamp(target-prev, ±step)` — but with `step = tp+0x71d6 = 0xC61D6 = 0`, it does not ramp; it holds at whatever value (and the deadband can hard-zero it). Re-enabling it (0→14) is the V16 EME fix.

### Key addresses (VERIFIED via search_instructions + decompile)

| What | Address | Bytes |
|------|---------|-------|
| `ld.hu 0x71d6[tp], r16` — load step | 0x43350 | e5 87 d7 71 |
| `ld.w -0x356c[gp], r9` — load state | 0x434ce | 24 4f 95 ca |
| `sub r16, r12` — ramp-down path | 0x434da | b0 61 |
| `add r9, r12` — ramp-up path | 0x434e4 | c9 61 |
| `st.w r12, -0x356c[gp]` — save state | 0x43504 | 64 67 95 ca |
| gp-0x6b98 stores | 0x43b52 and 0x43dfc | (st.h) |

### The step constant

- **tp+0x71d6**, resolved absolute address = tp (0xBF000) + 0x71d6 = **0xC61D6** (**NOT 0xC71D6 — prior memory had an off-by-0x1000 error**)
- **CORRECTED value at 0xC61D6: `00 00` (LE u16) = 0 (slew step is ZERO, NOT 14)**
- The value 0x0E (14) was read from the WRONG address 0xC71D6 (= tp+0x81D6) in the prior session
- Step=0 means the slew limiter has no ramp; it hard-zeroes iVar45 when the deadband fires and holds it there
- Editable calibration constant (NOT a code immediate)

### Symmetry

**SYMMETRIC** — the same single `tp+0x71d6` constant feeds both ramp-up (`add`) and ramp-down (`sub`) paths. In stock that constant is 0; if set to 14 (V16) the rate limit is symmetric.

### Step-to-zero behavior

**STOCK (step=0): does NOT ramp — it holds.** Once the deadband forces the accumulator to 0, with step=0 it stays 0 and the output jumps back only when demand rebuilds elsewhere = the felt hard cut + ratchet. **With the V16 fix (step=14): RAMPS — the integrator steps toward the target at 14 counts/tick**, smoothing both the drop and the recovery. The gp-0x6b98 write always uses the post-slew value.

Exception: if `uVar34 < *(ushort *)(tp+0x7424)` (motor-speed/readiness guard), iVar45 is forced to 0 immediately — hard-kill bypass.

### Internal scaling note

The 32-bit accumulator is shifted right by 15 bits before output (`>> 0xf`). The target `sVar26` entering the slew appears to be in a ×256-scaled representation (decompile L327: `iVar45 = iVar45 << 8` for one branch). Effective rate in int16 output units requires tracing the exact scaling of `sVar26` to interpret what step=14 means physically.

### Nearby tp calibration offsets (VERIFIED read_memory)

| Offset | Abs addr | Value | Notes |
|--------|---------|-------|-------|
| tp+0x71d4 | 0xC61D4 | 0xa05c | Default/fallback demand (fallback when LKAS off) |
| tp+0x71d6 | **0xC61D6** | **0x0000 = 0** | **SLEW STEP (ZERO — slew disabled effectively)** |
| tp+0x71da | 0xC61DA | 0x0444 = 1092 | Scale factor for deadband uVar33 computation |
| tp+0x71dc | 0xC61DC | 0x7800 = 30720 | Demand accumulator clamp |

### Always-on status

INFERRED (not fully traced): slew accumulator appears to run on every tick (no LKAS-gate observed around gp-0x356c accesses). Two lanes converge in this shaper; the slew runs before the lane merge. Confirm by checking callers of FUN_00042af8.

### Related memories

[[accord-shaper-fun42af8]] — full production chain  
[[accord-mixer-lkas-source-chain]] — upstream source to gp-0x6acc
