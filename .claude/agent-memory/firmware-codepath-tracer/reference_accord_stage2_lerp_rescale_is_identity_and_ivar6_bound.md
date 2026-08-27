---
name: accord-stage2-lerp-rescale-is-identity-and-ivar6-bound
description: The FUN_00038148 Stage-2 LERP has NO runtime rescale — K1/K2 (gp-0x6982/gp-0x6984) have zero writers in the whole image and boot to 1024 from .data, so the knots ARE the flash record; plus the creep-regime knots for modes 24/26 and the inversion of route 80's |gp-0x6b70| to |iVar6| <= ~6900.
metadata:
  type: reference
---

# The Stage-2 LERP rescale is the IDENTITY — and the `|iVar6|` bound that falls out

Strengthens [[accord-ram-lerp-is-flash-derived-and-fprime-nonneg]]: that memory said K1/K2 are
"nominally 1024". They are **1024 always** — there is no runtime degree of freedom at all.

## `gp-0x6982` (K1, X divisor) and `gp-0x6984` (K2, Y multiplier) are NEVER written [EVIDENCE]

| method | result for BOTH cells |
|---|---|
| GhidraMCP `search_instructions operand_pattern="0x6982"` / `"0x6984"` | 2 hits each, **all `ld.hu`** — `0x38bec`/`0x394d6` and `0x38bc6`/`0x394e2`, all in `FUN_000389ec` |
| Python raw LE scan, 4-byte disp16 (`hw2 = disp\|1`, reg1==gp) | same 2 each, opcode `0x3F`; **zero `st.h` (opcode `0x3B`)** |
| Python raw LE scan, 6-byte disp23 extended form | 0 |
| exhaustive byte-aligned search for `0xFEDF167E` / `0xFEDF167C` as a 32-bit literal | **0 occurrences in the whole 1 MB image** ⇒ no register-indirect base can be formed |

🛑 **Positive control matters here.** The neighbours `gp-0x6980`/`0x6986`/`0x6988`/`0x698A` DO have
disp16 `st.h` writers (`0x367a0`, `0x27340`, `0x27362`, `0x27384`) — the scan is provably able to
find a writer in this exact block. A null with a working positive control is a *verified* zero.

**Boot values close it** (via [[reference_accord_app_ram_layout_and_boot_init_loops]] — `.data` copy
`0x1475C`, flash `0x86260..0x8AB18` → RAM `0xFEDF11B0`):
```
gp-0x6982 = 0xFEDF167E <- flash 0x8672E = 1024   gp-0x3742 (K1 slew state) <- 0x8996E = 1024
gp-0x6984 = 0xFEDF167C <- flash 0x8672C = 1024   gp-0x3744 (K2 slew state) <- 0x8996C = 1024
```
Target 1024, state 1024, state inside `FUN_0003897a`'s snap window `(0xC639E=717, 0xC6394=1331)`
⇒ returns `clamp(1024,717,1331) = 1024` every call, forever. The `[204,2048]` bounds
(`0xC6390`/`0xC6392` = 2048, `0xC639A`/`0xC639C` = 204) are guard rails on a constant.
⇒ **`X[k] = Xsrc[k]`, `Y[k] = Ysrc[k]`. `f'` swing is 1.000x, not >=10x.**

**Why** [BELIEF]: siblings `gp-0x6986/88/8A` are min-reductions over three 11-element lane-gain
arrays (seeded `0x400`) written by `FUN_00026c80` with lockstep shadows `gp-0x4c60/62/64`.
`0x6982`/`0x6984` are two more slots of that family this part number never populates; the
`(v-204) unsigned < 1845 else 1024` test is the plausibility guard with a unity default.

## The creep knots (mode 26; mode 24 differs only in `Y[8]`, <2 %)
```
 0.0 km/h  X [0, 200, 400, 800,1200,1800,3000,5000,12000,14490]  Y [0,471,880,1408,1689,1953,2376,2844,4114,8192]
 6.6 km/h  X [0, 178, 356, 719,1200,1800,3000,5000,10681,14490]  Y [0,452,839,1382,1838,2131,2546,3043,4245,8192]
```
`f'` near origin **2.36–2.54**, falling ~12x by 5,000 counts. `FUN_00038148` feeds it
`|iVar6| * (0xC63AE = 1024) >> 10` = **`|iVar6|` raw** ⇒ the inversion is direct.
⚠ mode 24 != mode 26 in this family (rec 0/3/4/5 + breakpoints differ) — NOT covered by
[[accord-stock-mode24-equals-mode26-damper-is-ours]], which is scoped to the damper families.

## Inversion of route 80 (|gp-0x6b70| p50 320 / p90 2534 / p99 3059 / max 3187)
```
p50 -> |iVar6| 126-136     p90 -> 2965-3675     p99 -> 5076-6185     max -> 5681-6891
```
⇒ **`|iVar6| <= ~6,900` at creep, p50 ~130** — **2.9x tighter** than the ±20,000 writer clamp.
🛑 This bounds `|iVar6|`, NOT `|gp-0x6bfe|` alone: `iVar6 = gp-0x6bfe - 8*polarity*SUM(w_i*lane_i/1024)
+ gp-0x6bfa`, and the Path-1 term's structural max is 212,992 (all six weights stock 1024).
`gp-0x6bfe`'s own writer `FUN_0003bc20` @`0x3bc3e` clamps ±20,000 with a `0x7FFF` fault sentinel
(and `FUN_00038148` short-circuits to `0x7FFF` if `|gp-0x6bfe| > 20000`).

## Also nailed: the speed-scheduled X-axis CAP
`FUN_000389ec` @`0x389ec..0x38a5c` LERPs speed `gp-0x6a64` through X `0xC669A..` =
`[0,640,1600,3200,5120,7680,12800]` counts (`[0,10,25,50,80,120,200]` km/h), Y `0xC66A8..` =
`[12000,10000,10000,7000,7000,7000,7000]`, and **truncates the X axis there**, replicating knots flat.
At creep it is 10,681–12,000 and only bites at `k=8` ⇒ irrelevant to the creep inversion, but it
drops to **7,000 above 50 km/h** ⇒ **a highway inversion MUST include it; the creep numbers do not travel.**
Conditional Y floors are no-ops on stock: gates `0xC613E` = `0xC6140` = 15000, floors `0xC617A` = `0xC617C` = 0.
`X[9] = max(0xC613C=14490, X[8])`, `Y[9] = 0xC6200 = 8192`.

Doc: `docs/traces/TRACE-2026-08-12-stage2-lerp-knots.md`. Script: `analysis-2020accord/sessions/v97/stage2_lerp_invert.py`.
Related: [[reference_accord_fun38148_lane_weight_map_and_c63a0_reconciliation]],
[[reference_accord_task5_rate_resolved_100hz_and_fun389ec_structure]],
[[reference_accord_6to9hz_loop_is_pid_torque_tracker_phase_budget]].
