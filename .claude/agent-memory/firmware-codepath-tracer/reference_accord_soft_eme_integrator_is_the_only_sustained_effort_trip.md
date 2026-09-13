---
name: reference-accord-soft-eme-integrator-is-the-only-sustained-effort-trip
description: The ONLY integrate-and-trip on sustained motor effort in this image is the soft-EME command integrator gp-0x3570 (FUN_00042af8, 0x43214-0x4327C), decoded byte-exact -- I += (cmd-bound)<<15 per 1 kHz tick, SM2 arms at |I>>15| >= 15361, i.e. 154 ms at a sustained 100-count excess. The governor, FUN_0004595a and FUN_000456a4 carry NO accumulator, and the energy budget in FUN_0007b022 is unreachable because gp-0x6ba4 <= gp-0x4f64 <= 5325 = the cap table's own maximum.
metadata:
  type: reference
---

# The sustained-effort interlock census — settled 2026-09-13 on the V293 adversarial pass

Asked repeatedly by this kit ("can a lane that holds full torque for seconds trip anything?") and left
open by `docs/traces/TRACE-2026-09-13-lkas-pid-tracked-quantity.md` §7.5. **Answer: exactly one such
structure exists, and it is not where the question kept looking.** `gp = 0xFEDF8000`, `tp = 0xBF000`.

## 1. The integrator — `gp-0x3570`, inside the shaper `FUN_00042af8`

`disassemble_bytes(0x431C4, 188, dry_run:true)` and `(0x430F0, 212)`, decoded instruction by instruction:

```python
# command, 0x431C4-0x43206.  MODE 0 on A160 ([0xC64C8]==0) -> command = cmd, windowed not clamped
cmd = gp_6acc if -8192 <= gp_6acc <= 8192 else 0        # 0x431D0 addi / 0x431D8 cmovc
gp_6b08 = cmd                                           # 0x43206 st.h

# bound, built 0x43136-0x4318A
upper = max(corridor_upper, IIR_upper >> 8, boost)      # r29
lower = min(corridor_lower, -IIR_lower >> 8, -boost)    # r27

# integrator, 0x4320A-0x4327C.  ** (cmd - bound) << 15, NOT << 13 **
if   cmd > upper: I += (cmd - upper) << 15              # 0x4321A sar 0x2 / sub / shl 0x2  == exact <<15
elif cmd < lower: I += (cmd - lower) << 15
else:                                                   # INSIDE the corridor it LEAKS, proportionally
    I += (cmd - (upper if I > 0 else lower)) << 15       # and is snapped to 0 rather than crossing zero
I = clamp(I, +/- ([0xC61DC] << 15))                     # 0x43268, 0xC61DC = 30720
gp_3570 = I                                             # 0x4327C st.w

# authority, 0x432B0-0x432C8
authority = ((abs(I) >> 15) * [0xC61DA]) >> 10          # mulu / shr 0xa / zxh ; 0xC61DA = 1092
gp_6966 = authority
# SM2 arms when authority >= [0xC6422] = 16384   (read 0x436F4 / 0x43746)
```

⇒ **`I >> 15` is literally the running sum, in counts, of the per-tick excess over the bound, at 1 kHz.**
SM2 arms at `|I>>15| >= 15361`. **A sustained 100-count excess arms SM2 in 154 ms.** Confirms the
2026-08-06 correction banner in `memory/.../reference_accord_soft_eme_bound_arm_gating.md` independently,
from bytes. Any dwell argument built on a "1/4 per cycle tracker" is void.

`gp-0x3570` has **exactly 3 accesses image-wide** — `0x43214` read, `0x4327C` write, `0x432DE` read by the
authority writer — on stock, V282, V292 and V293. SM2/SM3 **self-clear**; they cannot latch.

## 2. What is NOT an accumulator — all four checked and cleared

| structure | verdict | evidence |
|---|---|---|
| `FUN_0004595a` plausibility monitor | **instantaneous comparator**, no state | `decompile_function(0x4595a)`: `\|gp-0x6b94\| - \|gp-0x6ace\|` and their product vs `-0.01f` (`0xbc23d70b`) |
| `FUN_0004503c` governor | slew limiter + MIN chain, no integrator | `decompile_function(0x4503c)` |
| `FUN_000456a4` post-governor comp-add | LERP + a per-index **cadence** byte at `gp-0x3E80+i` (task-rate watchdog, not effort) | `decompile_function(0x456a4)` |
| `FUN_0007b022` energy/thermal budget | **structurally unreachable** | §3 |

Census of the three demand cells, raw LE scan, 11/11 controls: `gp-0x6b94` 9 accesses, `gp-0x6ace` 11,
`gp-0x6acc` 6, `gp-0x6ba4` 10 — **no accumulator, timer or integrate-and-trip among any of them.**

## 3. The energy budget is unreachable — by a TIGHTER argument than the old one

`FUN_0007b022` charges only when `gp-0x6ba4 > [0xC509E] = 5325`, **strict**. `gp-0x6ba4` is written at
`0x43C0C` as the magnitude of the post-governor-clamp torque, so `gp-0x6ba4 <= gp-0x4f64`. And
`gp-0x4f64` has **exactly 3 writers image-wide — `0x7C2E2`, `0x7C3B4`, `0x7C47C`, all inside
`FUN_0007b022` (body `0x7B022-0x7C4F1`)** — each a LERP of the cap table `0xC520C`/`0xC5224`, whose Y is
`[5325, 3584, 2406, 1587, 512]`. A LERP cannot leave its knot range and both out-of-range arms return a
knot ⇒ **`gp-0x4f64 <= 5325`, so the strict `>` never fires.**

🛑 The older record (`reference_accord_governor_energy_budget_and_step_selector` §2) bounds this by
`0xC6202 = 4762`. **The cap table's own 5325 maximum is the bound that actually applies**, and it still
closes the case — use it, because it does not depend on identifying `0xC6202`'s role.

## 4. The numbers that decide any future dwell question, read from the images

Byte-identical on stock/V282/V292/V293 unless noted:

| cal | value | role |
|---|---|---|
| `0xC61DC` | 30720 | integrator clamp (`<< 15`) |
| `0xC61DA` | 1092 | authority scale |
| `0xC6422` | 16384 | SM2 arm on authority ⇒ `\|I>>15\| >= 15361` |
| `0xC641E` / `0xC64E3` | 16384 / 20 | boost-zeroing SM threshold / cycles |
| `0xC6156` / `0xC641A` | 9216 / 0 | corridor driver-override gate / authority gate |
| `0xC6768/6A/6C` boost Y | stock 0/1536/2048 → **5120 flat since V31** | the always-live bound arm |
| `0xC674E/50`, `0xC675A/5C` corridor | stock ±1024 → **±5120** | driver-override arm only |
| `0xC509E` / `0xC5164` / `0xC5128` | 5325 / 0 / 1024 | energy budget: threshold / ceiling / gain |
| `0xC520C`,`0xC5224` cap Y | `[5325,3584,2406,1587,512]` | governor cap, **falls with motor rate** |
| `0xC67D8/DA/DC` COMP Y | 512 / 1024 / **2560** | COMP ceiling; sign = `-sign(gp-0x6abe)` |
| `0xC61B4` | stock 512 → **3072** | LKAS lane output clamp |

**⇒ the wind-up condition in one line:** `|gp-0x6acc| > 5120` sustained, where
`gp-0x6acc = gp-0x6ace + COMP`, `|gp-0x6ace| <= gp-0x4f64 <= 5325`, `COMP <= 2560`. The LKAS lane is
clamped at 3072, so **the LKAS lane can never drive wind-up alone** — at least 2048 counts must come from
the other aggregator lanes.

## 5. Why V293 (torque mode) passed on this surface, and the residual

V293 changes none of the cals above, so the **reachable set** of `gp-0x6acc` is identical to V282's; only
**dwell** near the top of it rises, because `fb ≡ 0` stops the lane decaying as the wheel follows. The
largest NEW excess it can create where V282 had none is the **205-count band `5120 < |gp-0x6acc| <= 5325`**
(COMP zero), needing **75 ms** of continuous residency to arm SM2. Two structural anti-correlations damp
it: the governor cap falls with motor rate exactly as the torque-mode advantage grows, and COMP subtracts
in that same regime. Full working: `docs/review/ADV-V293-D-INTERLOCKS-2026-09-13.md` §1.

## Related
[[reference-accord-soft-eme-bound-arm-gating]] — the per-arm gating and V31's self-stable fixpoint; this
entry supplies the byte-exact integrator update that file's banner asserts.
[[reference-accord-corridor-vs-envelope]] — the corridor-vs-IIR-envelope distinction.
[[reference-accord-governor-energy-budget-and-step-selector]] — §3 supersedes its `0xC6202` bound.
[[reference_accord_gp4f64_governor_ceiling_chain_and_v41_force_proof]] — the cap-table chain.
