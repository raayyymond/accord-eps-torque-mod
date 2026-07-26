---
name: reference-accord-consistency-monitor-hardshutdown
description: Full verified call chain for V850E2 Accord EPS hard shutdown and DTC 0xF00049: two monitors (FUN_00042af8 weight accumulator and FUN_00043e44 float watchdog), their exact trip paths, and the latching kill mechanism. V26 at-rest fault explained.
metadata:
  type: reference
---

> ## ⚠ CORRECTIONS (2026-06-02, V27 session) — read before trusting the details below
> 1. **`.bin` contamination:** parts of this trace (the `FUN_00044666` "separate function", the
>    `FUN_000c4e00`/`FUN_000c4e0c` "cave" chain, the `2·r20 − float(wall)` dir2 arithmetic) were derived on
>    **`_v24_plain_image.bin`, which carries V21–V24 EXPERIMENTAL CODE EDITS** (a real trampoline at
>    `0xC4E00` + `shl` edits). On **STOCK `code.bin`** (the `/master.bin` program), `0xC4E00` is all-`0xFF`,
>    `FUN_00043e44` is ONE function (the "FUN_00044666" entry was created by V24's trampoline), and its
>    dir1/dir2 divergences are computed INLINE: `subf.s r2,lp,r10` @0x4463a (dir1) and `subf.s r9,r20,r12`
>    @0x44662 (dir2), each tested `|·| ≤ 5/1024`. Re-verify any `0xC4Exx`/`FUN_00044666` claim on `code.bin`.
> 2. **Gate address fix:** the float-watchdog fault-SM enable gate is **`0xC64A4` (`tp+0x74A4` = 0xBF000+0x74A4)
>    = `0x00` = ENABLED** — verified directly on stock. A prior pass misread it as `0xC74A4`=`0xEA` (an
>    off-by-`0x1000` tp+disp slip) and wrongly concluded "Monitor 2 gated off." Monitor 2 IS active.
> 3. **The V26 at-rest fault was NOT a `gp-0x6db0`-from-`0xC6664` thing.** `0xC6664` is LERP_B (envelope);
>    doubling it added a +2.0 envelope offset (lerp_a=2.0 at rest). The corrected corridor model + the
>    working V27 fix (code trampoline doubling the real twins lp/r20) is [[reference-accord-corridor-lockstep]].
>
> The HARD-shutdown LATCH CHAIN below (`FUN_00016de6` → `FUN_00018738` → `gp-0x685c`/`gp-0x3ef8` →
> `FUN_00019f7c` → `FUN_0001a16a` → `FUN_00045608` motor-off, power-cycle to recover) is in code far from
> the V24 edits and is sound; the DTC 0xF00049 mapping and "Monitor 2 is NOT report-only" verdict also hold.

## Hard-shutdown trip chain (VERIFIED at instruction level)

### The two monitors

**Monitor 1 — FUN_00042af8 "weight accumulator" (HARD shutdown path)**
- Computes `uStack_ec` from bit-weighted flags
- Weight-1 (uStack_e0): float_twin*1024 − int_wall == −16 (sentinel check)
- Weight-2 (iStack_f8): `int(float_twin*1024) − int_wall >= −16` (i.e. float is NOT much smaller than int) — see asm 0x43172–0x431c0
- Weight-8 (iStack_dc, asm 0x43a48–0x43a68): gp-0x6b04 outside [gp-0x6b00−5, gp-0x6af6+5]
- Weight-16 (uStack_e4): |int_torque_output| vs |float_torque_output| disagree by >5 or sign mismatch >5
- Weight-32 (iVar18): float gp-0x6dbc*1024 vs int gp-0x6b98 diff > 10+5
- Weight-64 (iVar43): float gp-0x6c84*32768 vs uint gp-0x3566 diff > 10+5
- Accumulation: after any non-zero fault cycle → sVar24 (gp-0x3564) += 10; when sVar24 >= 100 → uStack_ec += 0x400 (1024). So 10 fault cycles suffice to trip even with only weight-2.
- **Trip at 0x43d12**: `addi -0x81, r1, r0` / `bnc 0x43d4a` → if uStack_ec >= 128, calls `FUN_0004613e` at 0x43d42
- FUN_0004613e [V] (0x4613e): stores fault params, then calls `FUN_00016de6(0x1c, param_1, 1, 1)` — fault index 0x1c

**Monitor 2 — FUN_00043e44 / FUN_00044666 "float watchdog" (also HARD)**
- Accumulates float fault_word across multiple float-domain checks
- **Trip condition** at 0x44a2e–0x44a4c: if accumulated `r7` >= 128.0 (0x4300_0000 float)
- At 0x44a42: `movea 0x3f1b, r0, r6` / `jarl 0x462e6, lp` → calls `FUN_000462e6`
- FUN_000462e6 [V] (0x462e6): calls `FUN_00016de6(0x1d, 0x3f1b, 1, 1)` — fault index 0x1d
- Also writes fault params to gp-0x691e, gp-0x6922, gp-0x6920 etc. (logging), calls FUN_00046182 (float→fixed), FUN_0004613e (secondary set: `FUN_00016de6(0x1c, ...)`)

### DTC assignment
- DTC code 0x00F00049 = `49 00 F0 00` (little-endian) appears at DTC table 0xB9554 onward
- Indices 5–9, 11–20 map to 0xF00049. Internal fault indices 0x1c, 0x1d both map to DTC 0xF00049 [I — confirmed by table lookup pattern; need FUN_00047d06 trace to verify exact index-to-DTC binding]

### FUN_00016de6 → shutdown path [V]
FUN_00016de6(fault_idx, code, 1, 1) at 0x16de6:
- with param_3=1, param_4=1 enters the fault-latching branch
- Calls `FUN_00016634(param_1)` — DTC history update
- Calls `FUN_00016b66(param_1, param_2)` — DTC status set (sets bits 0x2088 / 0x2098 in fault status array at gp-0x18CE)
- `bVar7 = true` (param_3 != 0)
- Checks `FUN_0001611e(fault_record)` — returns true if fault record has bits 0x41 set (hard fault eligible)
- If true → calls `FUN_00018738(param_1, bVar7=1, param_4=1)`

FUN_00018738(param_1, param_2=1, param_3=1) at 0x18738:
- Increments trip counter in gp-0x40F4 area
- When counter >= trip threshold:
  - `*(undefined1 *)(unaff_gp + -0x685c) = 1` — sets the DTC-latch flag
  - Calls `FUN_00018bc0()` — writes `*(undefined4 *)(unaff_gp + -0x3ef8) = 1`
  - Calls `FUN_00016de6(0x2f, param_1, 1, 1)` — logs secondary DTC

FUN_00018bc0 at 0x18bc0: `mov 0x1,r14; st.w r14,-0x3ef8[gp]; jmp [lp]` — **single-opcode latch write**

### Hard-shutdown execution [V]
FUN_00019f7c at 0x19f7c (called per cycle from main loop):
```
if ((bVar7 != 1) && (iVar4 == 1) &&
    ((iVar2 != 0 ||               // FUN_00046ea6(0) — fault bit 0
      gp-0x685c != 0) ||          // DTC latch set by FUN_00018738
     ((iVar5==1 && steering_input==1) ||
      iVar6==1 ||                  // FUN_000197d0(8) — bit 8 in gp-0x6d78
      (gp-0x6b98 == 0 && iVar3!=0)))) &&
   gp-0x3ee8 == 0)
```
→ sets gp-0x67fa = 8 (shutdown state) [V]
→ calls FUN_0001a16a at 0x1a016 [V]
→ FUN_0001a16a: calls FUN_00018950 (clears DTC records), then `FUN_00045608(3, 0, 0x8000, 0x8000)` (motor off command) [V]
→ sets gp-0x3ee8 = 1 (latches shutdown — prevents re-entry until power cycle) [V]

**gp-0x6b98 is zeroed as part of the motor-off command via FUN_00045608 path, not directly.**

### V26 at-rest fault explanation [I — consistent with all evidence]
V26 change: float twin cal (0xC6664) changed from 1.0 → 2.0, stored at gp-0x6db0.
At rest, zero torque, stock integer corridor walls in gp-0x6af6 (e.g., ±1024):
- Weight-2 check: `int(2.0*1024) - 1024 = 1024 >= -16` → iStack_f8 = 2 (fault flag set)
- Weight-8 check: gp-0x6b04 (computed torque = 0 at rest) vs gp-0x6b00/0x6af6 (stock values): at rest = 0, likely inside corridor → iStack_dc = 0
- But iStack_f8 = 2 non-zero → sVar24 (gp-0x3564) increments by 10 each cycle
- After 10 cycles: sVar24 >= 100 → uStack_ec += 0x400 >> 128 threshold → FUN_0004613e called → FUN_00016de6(0x1c, ...) → FUN_00018738 → gp-0x685c = 1 → FUN_00019f7c shuts EPS off
- At 10ms task rate: ~100ms to fault. At 5ms: ~50ms. Both explain "immediately at rest."

### SOFT path (no DTC, recoverable)
- FUN_00016de6(0x2a, ...) call at 0x43de4 in FUN_00042af8 — manages the direction-corridor integrator gp-0x3570 clamping
- The state machine at gp-0x6786 / gp-0x6785 tracks SM2/SM3 (soft EME states)
- These cause integrator clamp / assist reduction but do NOT set gp-0x685c or trigger FUN_00018bc0
- V18 road behavior: sustained >1× turns → integrator builds up → soft EME → recoverable cutback

### Key addresses summary
| Address | Variable | Role |
|---------|----------|------|
| gp-0x685c | DTC latch byte | Set to 1 by FUN_00018738 when DTC trip counter hits threshold |
| gp-0x3ef8 | Shutdown latch word | Written 1 by FUN_00018bc0; read path → motor off |
| gp-0x3ee8 | Re-entry block | Set 1 when shutdown state entered; prevents repeat calls |
| gp-0x67fa | EPS state byte | Set to 8 for hard shutdown |
| gp-0x6d78 | Fault flag word | Bit 8 set by FUN_000197b8(8) — also trips shutdown |
| gp-0x6b98 | Torque command | Zeroed via FUN_00045608(3,0,0x8000,0x8000) during shutdown |
| gp-0x3564 | Fault cycle counter | Increments by 10 each fault cycle, triggers +0x400 at >=100 |
| gp-0x6db0 | Float twin dir1 | Cal 0xC6664 stock=1.0; V26=2.0 → immediate fault |
| gp-0x6db8 | Float twin dir2 | Companion to gp-0x6db0 |
| gp-0x6af6 | Int wall dir1 | Integer corridor wall; paired with gp-0x6db0 |
| gp-0x6b00 | Int wall dir2 | Paired with gp-0x6db8 |

### ~~Monitor 2 (FUN_00044666) is PERMANENTLY GATED OFF — does NOT fire [V]~~

> # 🛑 THIS ENTIRE SECTION IS WRONG — DO NOT USE. RE-VERIFIED ON STOCK BYTES 2026-07-18.
>
> The address arithmetic below is off by `0x1000`. `ld.bu 0x74a4[tp]` with `tp = 0xBF000` addresses
> **`0xBF000 + 0x74A4 = 0xC64A4`**, not `0xC74A4`. Direct byte read of stock `code.bin`:
>
> | address | byte | meaning |
> |---|---|---|
> | **`0xC64A4`** (correct) | **`0x00`** | gate == 0 → `bne` NOT taken → **SM ADVANCES → trip REACHABLE** |
> | `0xC74A4` (the slip) | `0xEA` | unrelated byte that produced the false "gated off" verdict |
>
> **Monitor 2's trip IS reachable and its fault SM IS active.** This restates correction #2 in the
> header block, which the section below predates and contradicts. The "Monitor 2 never needs to be
> fixed regardless of corridor widening" conclusion is **unsafe** — do not rely on it.
>
> Also note: on stock `code.bin` there is no `FUN_00044666` and no `0xC4Exx` cave chain — those were
> artifacts of tracing `_v24_plain_image.bin`, which carries V21–V24 experimental code edits (header
> correction #1). `FUN_00043e44` is ONE function containing both the setup and the trip evaluator.
>
> Kept only as a record of the misread. Current model: [[reference-accord-watchdog-fault-sm-fun43e44]].

~~Cal byte at `tp+0x74a4 = 0xC74A4 = 0xEA` (= 234, non-zero) permanently disables the Monitor 2
accumulator in FUN_00044666. Verified by read_memory at 0xC74A4 → bytes = [0xEA].~~

**How the gate works (ASM 0x44950–0x44982):**
- `0x44950: ld.bu 0x74a4[tp],r11` → r11 = 0xEA
- `0x44954: cmp r0,r11` → 0xEA ≠ 0
- `0x44956: bne 0x44978` → ALWAYS branches to 0x44978 (gate path)
- At 0x44978: gp-0x3550 (accumulator = 0 in gated state) ≤ r15 (threshold) → `cmovle r0,r7,r7` → r7=0
- `ble 0x449e8` → goes to trip check with r7=0
- `0x44a26: cmp 0x43000000(=128.0),r7` → 0 < 128 → NO TRIP

**Maximum direct flag sum = 126 (weights 2+4+8+16+32+64) + unaff_r23.** Even if r23=2, total=128,
but since r7 gets zeroed by the gate, the trip check sees 0. Monitor 2 trip is unreachable.

**The state machine (gp-0x3540 state 1/2/3) never advances past state 1** because state 1→2
transition requires gate=0, which never happens. States 2 and 3 are unreachable.

**V25 hard fault came entirely from Monitor 1 (FUN_00042af8), NOT Monitor 2.** The V26
Monitor-1-only fix (double int corridor + float twin at 0xC674E/0xC6664) is sufficient.
Monitor 2 never needs to be fixed regardless of corridor widening.

### ~~REPORT-ONLY verdict for FUN_00043e44~~ — 🛑 WRONG, DO NOT USE

> Every premise here is `_v24_plain_image.bin` contamination plus the `0x1000` address slip:
> - the `FUN_000c4e00 → FUN_0004463e → FUN_000c4e0c → FUN_00044666` chain **does not exist on stock**
>   (`0xC4E00` is all-`0xFF`; that chain was V24's trampoline);
> - `FUN_00044666` is not a separate function on stock — `FUN_00043e44` spans `0x43e44`–`0x44a88` and
>   contains the trip evaluator inline (`jarl 0x000462e6` at **`0x44a4c`**);
> - the gate is `0xC64A4` = `0x00` = **ENABLED**, not `0xC74A4` = `0xEA`.
>
> So `FUN_00043e44` **does** reach `FUN_000462e6` → `FUN_00016de6(0x1d, 0x3f1b, 1, 1)` on stock, and the
> trip is live. Separately verified: the monitor's own output word `gp-0x6906` has zero readers, so
> *that word* is report-only — but the DTC call is real and independent of it.
>
> **[UNVERIFIED]** whether index `0x1d` is hard-fault-eligible. Per the latch chain traced above,
> `FUN_00016de6` only escalates to `FUN_00018738` (→ `gp-0x685c`=1 → `FUN_00019f7c` → motor off,
> power-cycle to recover) when `FUN_0001611e(fault_record)` reports bits `0x41` set. Whether the
> record for `0x1d` carries `0x41` is the open question — trace `FUN_00047d06` / the index→DTC binding.

~~FUN_00043e44 ITSELF does not directly call any shutdown function.
It calls FUN_000c4e00 → FUN_0004463e → FUN_000c4e0c → FUN_00044666 (which has the float watchdog).
FUN_00044666 has the trip logic (FUN_000462e6 call) but it is permanently gated by 0xC74A4=0xEA.
FUN_00043e44 is the float watchdog SETUP function (computes corridor tables, IIR state);
FUN_00044666 has the trip evaluator but it is DEAD CODE for all current firmware variants.~~
