# 2020 Accord TVA-A160 — Torque-Path Variable & Table Inventory (MASTER)

**Built 2026-05-27** by a 4-agent program-wide sweep of `code.bin` (V850:LE:32, 185,116 instructions, 2113 functions). Method: `search_instructions(operand_pattern="-0x<gpoff>")` per variable — scans the entire image, so every reader/writer is captured (validated: `gp-0x6b98` → exactly 45 sites). Bases **VERIFIED this session**: `gp=0xFEDF8000`, `tp=0xBF000`.

Raw per-cluster tables are appended below (cluster1–4). This header is the synthesis.

---

## 1. Pointer-base audit (COMPLETE — every tp/gp register write in the image)

The crucial offset pointer is built in **three** instructions; missing the third (`add r1`) is what produced prior address errors.

| Context | Address | Sequence | Result |
|---|---|---|---|
| Reset stub | 0x1c4 / 0x1c8 / 0x1cc | `movhi 0x0`+`movea 0xd38`+`add r1,tp` | transient (early) |
| **Bootloader** | 0x9152 / 0x9156 | `movhi 0x10`+`movea -0x8000` | **tp = 0xF8000** |
| **Application** (`FUN_00014084`) | 0x140ce / 0x140d2 / **0x140d6** | `movhi 0xb`+`movea 0x7000`+**`add r1(=0x8000),tp`** | **tp = 0xBF000** ✓ |
| gp (boot) | 0x914a / 0x914e | `movhi -0x120`+`movea -0x8000` | gp = 0xFEDF8000 |
| gp (app) | 0x140c4 / 0x140c8 / 0x140cc | `movhi -0x121`+`movea 0x0`+`add r1(=0x8000),gp` | gp = 0xFEDF8000 ✓ |

The three `add …,tp` hits at `0xCBxxx` are in the calibration **data** band (no containing function) — mis-disassembled data, not executable. **Steering/torque code runs under the app ⇒ `tp=0xBF000` ⇒ all `0xC6xxx` cal addresses in this report are correct.**

---

## 2. ROOT CAUSE of the EME (4-agent consensus, disasm-verified end-to-end)

The operator-reported event — *whole power steering momentarily cuts out + ratchets for ~10 s on a sharp low-speed turn while overriding 2× LKAS, no DTC* — is fully explained:

1. Hard driver hand-torque + 2× LKAS pushing the other way ⇒ the **net torque demand swings through zero**, and/or the dual-coil column-torque voter `FUN_00041eec` sees a transient inter-channel divergence.
2. This drives the assist-mode state machine into a **transient re-init (state 3→1→2→3, NOT fault-state 4)** — so **no DTC latches** (the persistent fault bit, `gp-0x6d78` bit 15, is never set).
3. The shaper **deadband** (`tp+0x7424`=`0xC6424`=29491) zeroes the command via the newly-found state node **`gp-0x6960`** → `gp-0x6b98 = 0` (disasm-verified to the final store at 0x43b52/0x43dfc). **This cuts the COMBINED command — base power-steering assist AND LKAS — not just LKAS.**
4. **The slew step `tp+0x71d6`=`0xC61D6` is 0 — the output rate-limiter is DISABLED.** So once zeroed the command **holds at 0 and then jumps back** when demand rebuilds (300-count init-wait `0xC6288` + 17/cycle ramp `0xC64DE`) = the abrupt cut + ~10 s ratchet.
5. **V14's 2× gain did not create the mechanism — it doubled the consequence** of a normally-imperceptible plausibility/zero-crossing event.

**Why the disabled slew is the keystone:** whichever gate momentarily drops the command (deadband zero-crossing [cluster 3, verified], plausibility re-init [cluster 1/4], governor dip [cluster 2], or LKAS ramp-abort `gp-0x6758` [cluster 1]), the reason it is *felt as a violent cut + ratchet* rather than a soft dip is that the **final delivered command has no slew limit**. Re-enabling it smooths **all** of them — it sits on the shared post-merge trunk. This is the "fix robust to all gates" target, now precisely located, and matches aragon's rate-limit cure + vfn's "work at the output stage."

---

## 3. RECOMMENDED FIX (keeps 2× exactly, touches no fault detection)

All edits are in CRC block `0xC6000`; one CRC recompute.

| Rank | Addr | Cur | → | Effect | Safety |
|---|---|---|---|---|---|
| **1 (primary)** | `0xC61D6` slew step | 0 | **14** | Re-enables the delivered-command rate-limiter (other Honda variants ship 14). Smooths the recovery → **kills the ratchet**; smooths any momentary drop. | Rate-of-change only; magnitude (2×) untouched; no fault logic. |
| 2 (optional) | `0xC6424` deadband | 29491 | **~20000** | Net-demand zero-crossing dip no longer trips the full cut → **reduces the momentary outage**. | Keep ≥ ~16384 (50%); it is a low-demand guard, don't gut it. |
| 3 (tune) | `0xC64DE` ramp step | 17 | 25–30 | Faster re-engage after any dropout. | < 50. |

**Easiest = lever 1 alone: `0xC61D6` 0→14 (2 bytes + 1 CRC).** Levers 1+2 together is the robust combination. The 2× gain `0xC646C`=1782 stays untouched.

**OFF-LIMITS:** the plausibility threshold inside `FUN_00041eec` (genuine dual-coil column-torque-sensor fault detector — widening it is a safety regression). Reducing the arb gain `0xC646C` is the fallback only (it sacrifices the 2×).

---

## 4. Variables that can transiently zero/perturb the COMBINED command (no DTC)

| Variable | Abs | Mechanism | Cluster |
|---|---|---|---|
| `gp-0x6960` | 0xFEDF169F | assist-level state node; zeroed on no-active-demand → `gp-0x6b98=0` | 3 (verified to final store) |
| slew accum `gp-0x356c` | 0xFEDF3494 | held at 0 (step=0) once deadband fires → no smooth recovery | 3 |
| governor `gp-0x4f64` | 0xFEDF309C | speed-scaled by `FUN_0007b022`; low-speed mode-transition / hold-accum (`gp-0x138a`, `gp-0x67fa==4`) momentary collapse → clamps trunk to 0 | 2 |
| ramp gain `gp-0x6758` | 0xFEDF18A8 | zeroed by `FUN_0002a30e` on override-abort (`gp-0x6807==7`, `gp-0x67fa==8`, driver-torque `gp-0x682f` vs `tp+0x74b4/b5/b7/b8`) — LKAS-path | 1 |
| plausibility `gp-0x67f4`/`gp-0x67f5` | 0xFEDF180C/0B | voter `FUN_00041eec`: all 5 channels out of range (`ch+0x1900 < 0x9601` ⇒ `ch<0x7701`) → fused torque invalid → assist re-init | 1/4 |

---

## 5. Raw cluster reports

(Full per-variable toucher tables follow, as produced by each agent.)

---

### === cluster1_arb_input ===

# Cluster 1: Arbitration + Input Stage — Variable Inventory
**Program:** code.bin (V850:LE:32, image_base 0x0)
**gp = 0xFEDF8000, tp = 0xBF000**
**Method:** search_instructions(operand_pattern) program-wide (185,116 instructions scanned, complete)
**Date:** 2026-05-27

---

## Variable Table

| Abs RAM Addr | gp-Offset | #R | #W | Writer Function(s) | Reader Function(s) (key) | Role | FLAGS |
|---|---|---|---|---|---|---|---|
| 0xFEDF1652 | -0x69ae | 2 | 4 | `s_lkas_process_steer_cmd` (×4) | `m_steer_torque_arbitration` (×2), `w_lkas_setpoint_consumer2` | LKAS setpoint written by CAN handler; read by arb + secondary consumer | — |
| 0xFEDF14C4 | -0x6b3c | 1 | 1 | `m_steer_torque_arbitration` | `m_steer_torque_limit_and_pack` | Arb output word; single writer (arb), single reader (limit/pack) | — |
| 0xFEDF18AE | -0x6752 | ~50 | 3 | `FUN_000490ac` (init, ×2), `FUN_000497e6` (×2) | ≥30 functions including arb, mixer, shaper, aggregator | **Assist polarity / direction byte.** Written at init by FUN_000490ac (unconditional `=1` on match, else FUN_0006b9fa fault) and by FUN_000497e6. Read by practically every torque-path function. | **FLAG: written outside normal pipeline by init/watchdog functions FUN_000490ac and FUN_000497e6.** Mismatched redundant copy at gp-0x4c2d triggers FUN_0006b9fa (fault handler). |
| 0xFEDF185C | -0x67a4 | 1 | 1 | `m_steer_torque_limit_and_pack` | `m_steer_torque_arbitration` | ENABLE byte; arb reads it, limit/pack writes it (feedback token) | — |
| 0xFEDF1859 | -0x67a7 | 1 | 1 | `m_steer_torque_arbitration` | `m_steer_torque_limit_and_pack` | Arb output status byte; single writer arb, single reader limit/pack | — |
| 0xFEDF185F | -0x67a1 | 5 | 1 | `m_steer_torque_limit_and_pack` | `m_steer_torque_limit_and_pack` (×5 reads, ×1 write, self-RMW) | Internal limit/pack state byte; entirely within limit/pack | — |
| 0xFEDF185D | -0x67a3 | 1 | 1 | `m_steer_torque_arbitration` | `m_steer_torque_limit_and_pack` | Arb output flag byte; single writer, single reader | — |
| 0xFEDF15BC | -0x6a44 | ~13 | 3 | `FUN_000534da` (×3) | arb, FUN_00041eec, FUN_00042376, FUN_0004d8f0, FUN_0004de0c, others | Column-torque channel 1; exclusively written by `FUN_000534da` (CAN torque column unpacker) | — |
| 0xFEDF15C0 | -0x6a40 | ~13 | 3 | `FUN_000534da` (×3) | arb, FUN_00041eec, FUN_00042376, FUN_0004d8f0, FUN_0004de0c | Column-torque channel 2 | — |
| 0xFEDF15C4 | -0x6a3c | ~13 | 3 | `FUN_000534da` (×3) | arb, FUN_00041eec, FUN_00042376, FUN_0004d8f0, FUN_0004de0c | Column-torque channel 3 | — |
| 0xFEDF15C8 | -0x6a38 | ~13 | 3 | `FUN_000534da` (×3) | arb, FUN_00041eec, FUN_00042376, FUN_0004d8f0, FUN_0004de0c | Column-torque channel 4 | — |
| 0xFEDF15BA | -0x6a46 | ~17 | 3 | `FUN_000522fe` (×3) | arb, FUN_00041eec, FUN_00042376, FUN_0004d8f0, FUN_0004de0c, FUN_0002ec52, FUN_0004fbde | Column-torque channel 5 (different writer: `FUN_000522fe`) | **FLAG: different writer from channels 1-4; FUN_000522fe is a separate CAN unpacker** |
| 0xFEDF179E | -0x6a5e | 1 | 1 | `FUN_00041eec` | ≥47 functions including arb (×5), shaper, aggregator, governor, many others | **Fused driver torque** (redundancy-checked; written with dual-copy at gp-0x4caa). Sole writer is the torque fusion function. | **FLAG: extremely wide reader set (47+). The fusion function FUN_00041eec also gates output based on convergence state; zero output possible when no valid torque channels.** |
| 0xFEDF180C | -0x67f4 | ~25 | 2 | `FUN_00041eec` (×2) | arb, FUN_00022016, FUN_00022034, many others | **Plausibility/convergence flag.** Written by FUN_00041eec: set to 1 when |fused - nearest_channel| < 0x41 AND gp-0x4c38 agrees; set to 0 when no valid channels. Read inside FUN_00041eec to gate further processing. | **FLAG: gating. When =0, FUN_00041eec sets gp-0x67f5=0xFF (force-disengaged?) and skips arb curve output computation. This is a zeroing path.** |
| 0xFEDF180B | -0x67f5 | ~8 | 3 | `FUN_00041eec` (×3) | `m_motor_torque_governor` (×1), FUN_00021d72, FUN_00021eee, FUN_00022034, FUN_0007e8d8 | **Convergence/engage flag.** FUN_00041eec writes: 0xFF = not-converged (when gp-0x67f4==0), 1 = converged (timer elapsed + threshold met), 0 = converged-to-zero. Read by governor. | **FLAG: gating. Governor reads this; value 0xFF may gate or zero governor output. Cross-boundary writer (FUN_00041eec is outside arb).** |
| 0xFEDF4269 | -0x3d37 | 1 | 7 | `m_steer_torque_arbitration` (×7) | `m_steer_torque_arbitration` (×1) | Arb state machine byte; entirely internal to arb | — |
| 0xFEDF426A | -0x3d36 | 1 | 6 | `m_steer_torque_arbitration` (×6) | `m_steer_torque_arbitration` (×1) | Arb state machine byte 2; entirely internal to arb | — |
| 0xFEDF4278 | -0x3d28 | 1 | 7 | `m_steer_torque_limit_and_pack` (×7) | `m_steer_torque_limit_and_pack` (×1) | Limit/pack state byte; entirely internal to limit/pack | — |
| 0xFEDF1582 | -0x6a7e | 3 | 11 | `m_steer_torque_arbitration` (×11) | `m_steer_torque_arbitration` (×3) | Re-engage counter (16-bit); entirely internal to arb | — |
| 0xFEDF18AA | -0x6756 | 2 | 10 | `m_steer_torque_arbitration` (×10) | `m_steer_torque_arbitration` (×2) | Re-engage ramp gain byte; entirely within arb | — |
| 0xFEDF18A8 | -0x6758 | 2 | 22 | `m_steer_torque_arbitration` (×12), `FUN_0002a30e` (×10) | `m_steer_torque_arbitration` (×2), `FUN_0002a30e` (×2) | **Re-engage ramp gain accumulator.** `FUN_0002a30e` independently writes this to 0 on multiple exit paths (fault, no-param, etc.). | **FLAG: FUN_0002a30e is the re-engage ramp manager and CAN ZERO this counter under several conditions: iVar7==1 (FUN_00046ea6(9) result), gp-0x67fa==8, gp-0x6807==7, param_3==0, ramp overflow, etc. This is a known zeroing source.** |
| 0xFEDF14D4 | -0x6b2c | 3 | 10 | `m_steer_torque_arbitration` (×10) | `m_steer_torque_arbitration` (×3) | Arb internal accumulator (16-bit, reset to 0 or written to r11); entirely within arb | — |
| 0xFEDF14D0 | -0x6b30 | 1 | 1 | `m_steer_torque_arbitration` | `m_steer_torque_arbitration` | Arb internal word; RMW within arb | — |
| 0xFEDF14CE | -0x6b32 | 0 | 2 | `m_steer_torque_arbitration`, `FUN_0002a93a` | (none observed) | Arb curve output word 1 (written by arb main + arb curve evaluator `FUN_0002a93a`); no observed readers in this scan | **FLAG: second writer FUN_0002a93a.** |
| 0xFEDF14CC | -0x6b34 | 0 | 2 | `m_steer_torque_arbitration`, `FUN_0002a93a` | (none observed) | Arb curve output word 2 | **FLAG: second writer FUN_0002a93a.** |
| 0xFEDF14CA | -0x6b36 | 0 | 2 | `m_steer_torque_arbitration`, `FUN_0002a93a` | (none observed) | Arb curve output word 3 | — |
| 0xFEDF14C8 | -0x6b38 | 2 | 1 | `m_steer_torque_arbitration` | `w_lkas_setpoint_consumer2` (×2) | Arb output word (16-bit); **read by the secondary LKAS consumer** | **FLAG: cross-boundary reader w_lkas_setpoint_consumer2 reads this.** |
| 0xFEDF6BD8 | (abs) | 0 | 0 | — | — | CAN buffer: no direct immediate-operand references found. Access is via base-register + computed offset (not visible to operand pattern search). | **UNRESOLVED: indirect access only.** |

---

## Discovered Variables NOT in Original List

| gp-Offset | Abs Addr | First seen in | Role inferred |
|---|---|---|---|
| -0x6757 | 0xFEDF18A9 | `m_steer_torque_arbitration`, `FUN_0002a30e` | Re-engage ramp direction/sign byte (set to -cVar2 on abort, set to cVar2 on full ramp) |
| -0x6807 | 0xFEDF17F9 | `m_steer_torque_arbitration`, `FUN_0002a30e`, `w_lkas_setpoint_consumer2`, `FUN_00055c42` | **Re-engage state machine byte** (values 3,4,6,7 seen as abort codes in FUN_0002a30e). Cross-boundary: read by w_lkas_setpoint_consumer2 and FUN_00055c42. |
| -0x6802 | 0xFEDF17FE | `s_lkas_process_steer_cmd` (W), arb (R), `FUN_0002a30e` (R), `w_lkas_setpoint_consumer2` (R) | **LKAS engagement mode byte** (values 0/2 visible). Written by LKAS CAN handler; read by arb, re-engage ramp manager, and secondary consumer. |
| -0x6a62 | 0xFEDF179E | `FUN_00041eec` (W ×2), many readers | **Fused driver torque (redundant copy / filtered)**. FUN_00041eec writes both gp-0x6a5e and gp-0x6a62. The difference between these two may be smoothed vs raw. |
| -0x6a64 | 0xFEDF179C | `FUN_00041eec` (W ×1), many readers including `m_motor_torque_governor` | **Speed-adapted torque threshold** (written by torque fuser, read by governor). |
| -0x6a32 | 0xFEDF15CE | `FUN_0002a93a` | Intermediate arb curve signed output |
| -0x697a | 0xFEDF1686 | `FUN_0002a93a` | Arb steer-rate intermediate (speed arg) |
| -0x6cf8 | 0xFEDF1308 | `FUN_0002a93a` (W), arb curve (R) | Arb integrator/history state (int32) |
| -0x6dd0 | 0xFEDF1230 | `FUN_0002a93a` (W) | Arb integrator/history state 2 (int32) |
| -0x674e | 0xFEDF18B2 | `FUN_0002a93a` (R) | Variant/mode index byte (selects arb curve set) |
| -0x674b | 0xFEDF18B5 | `FUN_0002a93a` (W) | Computed steer-rate magnitude (written mid-computation) |
| -0x680a | 0xFEDF17F6 | `FUN_0002a93a` (R) | Arb sub-mode flag (selects alternate curve path when ==1) |
| -0x6805 | 0xFEDF17FB | `FUN_0002a93a` (R) | Arb enable pre-condition byte (must be ==1 or zero-path taken) |
| -0x69b0 | 0xFEDF1650 | `FUN_0002a93a` (R) | Short near gp-0x69ae (setpoint-adjacent); zero check gates arb curve eval |
| -0x6803 | 0xFEDF17FD | `FUN_0002a93a` (R) | Sub-mode byte for arb B/A curve selection (==2 check) |
| -0x682f | 0xFEDF17D1 | `FUN_0002a93a` (R), `FUN_0002a30e` (R) | **Driver torque magnitude byte** (absolute torque, used as axis for arb curve lookup AND re-engage ramp threshold). Cross-used by both arb curve evaluator and re-engage manager. |
| -0x6830 | 0xFEDF17D0 | `FUN_0002a93a` (R) | Secondary driver torque byte (second axis for some arb curves) |
| -0x67fa | 0xFEDF1806 | heavily used (50+ hits, many writers in 0x14xxx-0x19xxx range) | **System mode / fault byte** (very wide — written by low-level CAN/power mgmt functions). Value ==8 in FUN_0002a30e causes re-engage ramp zeroing. |
| -0x4f60 | 0xFEDF3020 | `FUN_0002a93a` (R) | Signed vehicle speed or related signal (sign check gates arb direction) |

---

## Summary: Variables That Can Zero or Hard-Perturb Delivered Torque

### 1. gp-0x6758 (re-engage ramp gain accumulator) — DIRECT ZEROING
**Writer:** `FUN_0002a30e` zeros this unconditionally on ANY of these conditions:
- `FUN_00046ea6(9)` returns 1 (some system-level permission/interlock)
- `gp-0x67fa == 8` (system fault/mode byte = 8)
- `gp-0x6807 == 7` (re-engage state = abort)
- `param_3 == 0` (LKAS command = 0 or not engaged)
- Ramp overflow (counter exceeds tp+0x74e0+tp+0x74e1 threshold)

When zeroed, the re-engage ramp output is zero, meaning LKAS torque can drop to 0 even while the LKAS setpoint is nonzero. This is a **transient zero source with no DTC** — it looks like a clean ramp-to-zero.

### 2. gp-0x67f4 (plausibility flag) — GATE
Written to 0 by `FUN_00041eec` when no valid torque channels are available (all 5 channels failed range check). When 0: FUN_00041eec writes gp-0x67f5 = 0xFF and short-circuits the arb curve output calculation. Downstream effects propagate to gp-0x6a5e/6a62 (fused torque). **If driver torque channels drop (e.g., during hard override transient), this can cause a momentary zeroing of the arb input.**

### 3. gp-0x67f5 (convergence/engage flag) — GATE on governor
Read by `m_motor_torque_governor`. Value 0xFF (set when gp-0x67f4==0) may cause governor to treat LKAS as disengaged. This is the downstream consequence of gp-0x67f4==0.

### 4. gp-0x6752 (assist polarity) — FAULT on mismatch
Has a redundant copy at gp-0x4c2d. If these diverge, `FUN_000490ac` calls `FUN_0006b9fa` (fault handler). During a hard override, if the polarity byte's redundant copy is transiently inconsistent (e.g., due to timing), this fault handler could disrupt torque delivery.

### 5. gp-0x6a5e (fused driver torque) — ZERO RISK from torque fuser
Sole writer is `FUN_00041eec`. If all 5 column-torque channels (gp-0x6a44/40/3c/38/46) fail their range checks simultaneously — which can happen during a hard override with high driver torque — the function takes the "no valid channels" branch and writes zero or 0x7d00 (capped) to gp-0x6a5e. This feeds arb directly and can cause a transient torque output drop.

---

## Unexpected Writers (Outside Expected Pipeline)

| Variable | Unexpected Writer | Why Unexpected |
|---|---|---|
| gp-0x6752 (assist polarity) | `FUN_000490ac`, `FUN_000497e6` | Init/watchdog functions outside the arb/shaper pipeline |
| gp-0x6758 (ramp accumulator) | `FUN_0002a30e` | Separate re-engage ramp manager function, parallel to arb |
| gp-0x6757 (ramp direction) | `FUN_0002a30e` | Same |
| gp-0x6807 (re-engage state) | `FUN_0002a30e` | Cross-writes a byte read by arb and w_lkas_setpoint_consumer2 |
| gp-0x6b32/34/36/38 (arb internals) | `FUN_0002a93a` | Arb sub-function (curve evaluator) — expected sub-call, not truly external |
| gp-0x67f4, gp-0x67f5, gp-0x6a5e, gp-0x6a64 | `FUN_00041eec` | Torque fuser (separate function from arb) but its caller is FUN_00022ca0 |

---

## CAN Buffer (0xFEDF6BD8)
No direct immediate-operand references found anywhere in the 185,116-instruction scan. Access is exclusively via computed base+offset addressing (register load then offset). To trace the CAN buffer, the recommended next step is: decompile `FUN_000534da` (column-torque unpacker for channels 1-4) and `FUN_000522fe` (channel 5 writer) to find the base pointer chain leading to 0xFEDF6BD8.

### === cluster2_mixer_governor ===

# Cluster 2: Mixer / Distribute / Governor — Full Touch Map

**Firmware:** 2020 Accord EPS (V850:LE:32, Ghidra image_base 0x0)
**gp = 0xFEDF8000**, **tp = 0xBF000**
**Method:** `search_instructions(operand_pattern="-0xOFF")`, program-wide, limit 200 per var.
All addresses are file-offset (== Ghidra addr). R/W classified by mnemonic (`ld.*` = READ, `st.*` = WRITE, `movea` = address-of = structural setup, not a direct R/W).

---

## 1. Per-Channel Distribute Buffers (output channels from `m_motor_cmd_distribute_clamp`)

These four are written only by `m_motor_cmd_distribute_clamp` and read by the mixer/accumulator stages.

### gp-0x62e0

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x25e9a | m_motor_cmd_distribute_clamp | movea | base-ptr setup (×6 occurrences) |
| 0x25efc | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26480 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26782 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26a64 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26ad2 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26dd8 | m_motor_cmd_mixer | ld.h | READ — mixer reads channel[i] |
| 0x26e74 | m_motor_cmd_mixer | ld.h | READ — mixer reads channel[i] |
| 0x26fce | m_motor_cmd_mixer | ld.h | READ — mixer reads channel[i] |
| 0x27832 | FUN_00027802 | movea | base-ptr setup (bounds validator) |
| 0x27b98 | FUN_00027b0a | movea | base-ptr setup (accumulator/LERP stage) |
| 0x27bc0 | FUN_00027b0a | movea | base-ptr setup |
| 0x27bda | FUN_00027b0a | movea | base-ptr setup |
| 0x27c62 | FUN_00027b0a | movea | base-ptr setup |
| 0x27c82 | FUN_00027b0a | movea | base-ptr setup |
| 0x27c9c | FUN_00027b0a | movea | base-ptr setup |
| 0x28d38 | FUN_00028d22 | movea | base-ptr setup (integrity checker) |

**Summary:** 6 writers (distribute_clamp), 3 direct reads (mixer), multiple structural setups. No unexpected writers.

---

### gp-0x62f8

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x25eaa | m_motor_cmd_distribute_clamp | movea | base-ptr setup (×6) |
| 0x25f0c | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26490 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26792 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26a74 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26ae2 | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26d12 | m_motor_cmd_mixer | movea | base-ptr setup (mixer reads via offset) |
| 0x278b2 | FUN_00027802 | movea | base-ptr setup |
| 0x27b48 | FUN_00027b0a | movea | base-ptr setup (×6) |
| 0x27b70 | FUN_00027b0a | movea | base-ptr setup |
| 0x27be2 | FUN_00027b0a | movea | base-ptr setup |
| 0x27c12 | FUN_00027b0a | movea | base-ptr setup |
| 0x27c3e | FUN_00027b0a | movea | base-ptr setup |
| 0x27ca4 | FUN_00027b0a | movea | base-ptr setup |
| 0x28d58 | FUN_00028d22 | movea | base-ptr setup (integrity checker) |

**Summary:** All movea (base-pointer), actual r/w via indexed displacement within those functions. No unexpected writers.

---

### gp-0x633c

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x25ec2 | m_motor_cmd_distribute_clamp | movea | base-ptr setup (×6) |
| 0x25f2a | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x264ac | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x267aa | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26a8c | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26afa | m_motor_cmd_distribute_clamp | movea | base-ptr setup |
| 0x26cf4 | m_motor_cmd_mixer | movea | base-ptr setup |
| 0x27928 | FUN_00027802 | movea | base-ptr setup |
| 0x27b78 | FUN_00027b0a | movea | base-ptr setup (×5) |
| 0x27ba0 | FUN_00027b0a | movea | base-ptr setup |
| 0x27bc8 | FUN_00027b0a | movea | base-ptr setup |
| 0x27bec | FUN_00027b0a | movea | base-ptr setup |
| 0x27d60 | FUN_00027b0a | ld.h | DIRECT READ |
| 0x28d76 | FUN_00028d22 | movea | base-ptr setup (integrity checker) |

**Summary:** Written by distribute_clamp only; read directly at 0x27d60 inside FUN_00027b0a.

---

### gp-0x6230

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x25ed2 | m_motor_cmd_distribute_clamp | movea | base-ptr setup (×6) |
| 0x25f3a–0x26b0a | m_motor_cmd_distribute_clamp | movea | base-ptr setup (5 more sites) |
| 0x26d0c | m_motor_cmd_mixer | movea | base-ptr setup |
| 0x279a4 | FUN_00027802 | ld.hu | READ (bounds check) |
| 0x27ad4 | FUN_00027802 | ld.h | READ |
| 0x27b80–0x27cb0 | FUN_00027b0a | movea | base-ptr setup (×6) |
| 0x27d20 | FUN_00027b0a | ld.hu | READ |
| 0x27d42 | FUN_00027b0a | ld.hu | READ |
| 0x27d7e | FUN_00027b0a | ld.hu | READ |
| 0x28d98 | FUN_00028d22 | movea | base-ptr setup |

**Summary:** Written only by distribute_clamp. Multiple reads in FUN_00027802 (bounds validator) and FUN_00027b0a (accumulator). No unexpected writers.

---

## 2. Mixer Lane Slots

### gp-0x62b0  (mixer lane slot B)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x26cd0 | m_motor_cmd_mixer | movea | base-ptr setup |
| 0x2723a | m_motor_cmd_mixer | movea | base-ptr setup |
| 0x27df0 | FUN_00027b0a | ld.h | READ |
| 0x27e96 | FUN_00027b0a | ld.h | READ |
| 0x27f42 | FUN_00027b0a | ld.h | READ |
| 0x280f4 | FUN_00027b0a | ld.h | READ |
| 0x2817a | FUN_00027b0a | ld.h | READ |
| 0x286a4 | FUN_00027b0a | movea | base-ptr setup |
| 0x2870e | FUN_00027b0a | movea | base-ptr setup |
| 0x28de0 | FUN_00028d22 | movea | base-ptr setup |

**Summary:** Written by mixer (WRITE implied via distribute_clamp upstream), read heavily by FUN_00027b0a accumulator stage.

---

### gp-0x62c8  (mixer lane slot A)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x26cc8 | m_motor_cmd_mixer | movea | base-ptr setup |
| 0x2721a | m_motor_cmd_mixer | movea | base-ptr setup |
| 0x27dbc | FUN_00027b0a | ld.h | READ |
| 0x27e64 | FUN_00027b0a | ld.h | READ |
| 0x280d6 | FUN_00027b0a | ld.h | READ |
| 0x28160 | FUN_00027b0a | ld.h | READ |
| 0x281f6 | FUN_00027b0a | movea | base-ptr setup |
| 0x286b0 | FUN_00027b0a | movea | base-ptr setup |
| 0x2871a | FUN_00027b0a | movea | base-ptr setup |
| 0x28794 | FUN_00027b0a | movea | base-ptr setup |
| 0x28dfa | FUN_00028d22 | movea | base-ptr setup |

**Summary:** Same pattern as gp-0x62b0. Written by distribute_clamp/mixer pipeline upstream, multiple reads in FUN_00027b0a.

---

## 3. Mixer Accumulators

### gp-0x3d88  (accumulator A, int32)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x2730c | m_motor_cmd_mixer | st.w | WRITE — stores accumulator |
| 0x276d4 | m_motor_cmd_mixer | ld.w | READ — reads back accumulator |

**Summary:** Written and read exclusively within m_motor_cmd_mixer. Private accumulator. No cross-function zero risk.

---

### gp-0x3d8c  (accumulator B, int32)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x27318 | m_motor_cmd_mixer | st.w | WRITE — stores accumulator |
| 0x2743e | m_motor_cmd_mixer | ld.w | READ — reads back accumulator |

**Summary:** Same as gp-0x3d88. Private to mixer. No cross-function zero risk.

---

## 4. Extended Accumulator Bank

### gp-0x3d70  (int32)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x27310 | m_motor_cmd_mixer | st.w | WRITE only |

**Summary:** Write-only from mixer (write-once per cycle, no same-function read found in range). Likely telemetry/shadow output.

---

### gp-0x3d74  (int32, also movhi target)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x27308 | m_motor_cmd_mixer | st.w | WRITE |
| 0x27352 | m_motor_cmd_mixer | ld.w | READ |
| 0x379b8 | FUN_000378d6 | movhi | address-of (structural) |
| 0x75886 | FUN_000757a2 | movhi | address-of |
| 0x7b2cc | FUN_0007b022 | movhi | address-of (governor writer uses this as base!) |
| 0x7c616 | FUN_0007c4f2 | movhi | address-of |

**FLAG:** FUN_0007b022 (the governor writer) constructs an address based on movhi -0x3d74. This is how it builds the RAM pointer region for its computations. Not a direct R/W of gp-0x3d74, but the governor function uses this region as a base for float math (confirmed: gp+0x184, gp+0x17c, gp+0x128, gp+0x130 are all within this band). The float speed values that determine the governor's output live in this region.

---

### gp-0x3d78  (uint16)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x2733a | m_motor_cmd_mixer | st.w | WRITE |
| 0x2737c | m_motor_cmd_mixer | ld.hu | READ |

**Summary:** Private to mixer. Used as uint16 flag/counter.

---

### gp-0x3d90  (int32)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x27336 | m_motor_cmd_mixer | st.w | WRITE |
| 0x27396 | m_motor_cmd_mixer | ld.w | READ |

**Summary:** Private to mixer.

---

### gp-0x3d94  (byte)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x27328 | m_motor_cmd_mixer | st.w | WRITE |
| 0x27754 | m_motor_cmd_mixer | ld.bu | READ |

**Summary:** Private to mixer. Byte flag, read as unsigned.

---

### gp-0x3d98  (byte)

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x27314 | m_motor_cmd_mixer | st.w | WRITE |
| 0x27732 | m_motor_cmd_mixer | ld.bu | READ |

**Summary:** Private to mixer. Byte flag.

---

## 5. LKAS Upstream Demand: gp-0x6b4c

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x276e2 | m_motor_cmd_mixer | ld.h | READ — reads prior value |
| 0x276f0 | m_motor_cmd_mixer | st.h | WRITE — branch A write |
| 0x27708 | m_motor_cmd_mixer | st.h | WRITE — branch B write |
| 0x27716 | m_motor_cmd_mixer | st.h | WRITE — branch C write (r10) |
| 0x285b4 | FUN_00027b0a | ld.h | READ — accumulator uses it |
| 0x28b16 | FUN_00027b0a | ld.h | READ |
| 0x28b38 | FUN_00027b0a | movea | base-ptr (tolerance check) |
| 0x3816c | FUN_00038148 | ld.h | READ — unknown consumer |
| 0x3aa3e | m_motor_torque_demand_aggregator | ld.h | READ — primary consumer; clamp +-0x2800 applied inline |

**ZEROING RISK:** The decompile of m_motor_torque_demand_aggregator shows:
```c
iVar20 = (int)*(short *)(unaff_gp + -0x6b4c) *
         (uint)((int)*(short *)(unaff_gp + -0x6b4c) + 0x2800U < 0x5001);
```
This is an inline range-clamp: if the value is outside [-0x2800, +0x2800] the multiply by 0 ZEROS the LKAS contribution at the aggregator. The range is ±10240 (±0x2800) which is very wide, so this is a safety floor rather than a normal operating boundary. Under normal conditions gp-0x6b4c stays well inside ±10240.

The three st.h writes in m_motor_cmd_mixer (0x276f0, 0x27708, 0x27716) are the only producers. FUN_00027b0a also reads it for a tolerance/error check (0x3cec diagnostic via FUN_000462e6) — it does NOT write it.

---

## 6. Aggregator Output: gp-0x6b94

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x36bf0 | FUN_00036bec | ld.h | READ — unknown (diagnostic?) |
| 0x3acec | m_motor_torque_demand_aggregator | ld.h | READ — reads prior lockstep check |
| 0x3acfa | m_motor_torque_demand_aggregator | st.h | WRITE — nominal write (clamp ±0x2800 applied) |
| 0x3ad12 | m_motor_torque_demand_aggregator | st.h | WRITE — lower clamp path (-0x2800) |
| 0x3ad20 | m_motor_torque_demand_aggregator | st.h | WRITE — upper clamp path (+0x2800) |
| 0x453e0 | m_motor_torque_governor | ld.h | READ — governor input |
| 0x4595e | FUN_0004595a | ld.h | READ |
| 0x80820 | FUN_0007ff08 | ld.h | READ |

**ZEROING RISK:** The aggregator clamps the sum to ±0x2800 (±10240) before writing gp-0x6b94. The sum includes all demand lanes including the LKAS contribution from gp-0x6b4c. Under a hard driver override, the driver torque term dominates but does NOT itself zero gp-0x6b94 — the sign conventions mean they add, not cancel (the +-0x6752 polarity flag is applied before summation). The ±0x2800 clamp is a hard ceiling, not a zero path. **The aggregator cannot collapse to zero from normal operating conditions.**

Lockstep shadow: gp-0x4ce0. Mismatch triggers FUN_0006b9fa (safety fault). This fault handler is a potential indirect zero path — if triggered, control may be surrendered.

---

## 7. Post-Governor: gp-0x6ace

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x4545a | m_motor_torque_governor | ld.h | READ — reads prior value |
| 0x454d2 | m_motor_torque_governor | st.h | WRITE — main governor output |
| 0x454e0 | m_motor_torque_governor | st.h | WRITE — alternate path |
| 0x454f4 | m_motor_torque_governor | ld.h | READ |
| 0x45528 | m_motor_torque_governor | ld.h | READ |
| 0x4559c | m_motor_torque_governor | st.h | WRITE |
| 0x455ae | m_motor_torque_governor | st.h | WRITE |
| 0x455c0 | m_motor_torque_governor | ld.h | READ |
| 0x458bc | m_post_governor_torque_comp_add | ld.h | READ — comp-add consumes |
| 0x45980 | FUN_0004595a | ld.h | READ |
| 0x45b1e | FUN_00045a20 | ld.h | READ |

**ZEROING RISK:** The governor writes gp-0x6ace as:
```
governed = clamp(gp-0x6b94, ± ((gp-0x4f64 * speed_scale_uVar17) >> 15))
then: gp-0x6ace = rate-limited version of governed
```
If `gp-0x4f64` drops to 0 AND `speed_scale_uVar17` is also small, the governor ceiling collapses to 0 and gp-0x6ace is hard-clamped to 0. This is **the primary zeroing path** for the combined assist. See Section 9 (governor) for the drop conditions.

Lockstep shadow: gp-0x4cca. Mismatch → FUN_0006b9fa.

A second override path exists: when `gp-0x67fa == 4` (mode-4 flag), if the governor's accumulated hold value `gp-0x138a` drops below the governed value in magnitude, the hold value is substituted. This can transiently zero gp-0x6ace if `gp-0x138a` has been driven to 0.

---

## 8. Shaper Input: gp-0x6acc

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x431c4 | s_motor_torque_rate_shaper | ld.h | READ — shaper reads its input |
| 0x4467a | FUN_00043e44 | ld.h | READ |
| 0x458b8 | m_post_governor_torque_comp_add | ld.h | READ |
| 0x45932 | m_post_governor_torque_comp_add | st.h | WRITE — comp_add writes shaper input |
| 0x45942 | m_post_governor_torque_comp_add | st.h | WRITE — alternate |
| 0x45b16 | FUN_00045a20 | ld.h | READ |

**Summary:** gp-0x6acc is downstream of gp-0x6ace. Written by `m_post_governor_torque_comp_add` (which reads gp-0x6ace and adds a speed-LERP correction term). If gp-0x6ace = 0, gp-0x6acc = 0 + correction_term. The correction term is a small trim, so effectively gp-0x6acc ≈ 0 when the governor collapses.

---

## 9. Runtime Governor Limit: gp-0x4f64  **[KEY ZEROING PATH]**

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x43ae4 | s_motor_torque_rate_shaper | ld.hu | READ — shaper also reads the governor limit |
| 0x4486e | FUN_00043e44 | ld.hu | READ |
| 0x453f0 | m_motor_torque_governor | ld.hu | READ — primary consumer |
| 0x6e0f2 | FUN_0006e09a | ld.hu | READ |
| 0x6e1ca | FUN_0006e140 | ld.hu | READ |
| 0x7c2d2 | FUN_0007b022 | ld.hu | READ |
| 0x7c2e2 | FUN_0007b022 | st.h | **WRITE** — update governor |
| 0x7c3a8 | FUN_0007b022 | ld.hu | READ |
| 0x7c3b4 | FUN_0007b022 | st.h | **WRITE** — update governor (second branch) |
| 0x7c470 | FUN_0007b022 | ld.hu | READ |
| 0x7c47c | FUN_0007b022 | st.h | **WRITE** — update governor (third branch) |

**FUN_0007b022 is the SOLE WRITER of gp-0x4f64.**

### How FUN_0007b022 computes the governor value

FUN_0007b022 branches on `uVar26 = gp-0x4e5a` (a mode/state byte, written by FUN_00071272 and FUN_00075718):

**Branch uVar26 == 0 (line 1081):**
```
fVar39 = (gp+0x184) * 1024.0   // speed float * 1024
// saturate to [0, 65535] (unsigned 16-bit range)
// fVar54 = MIN(gp+0x128, fVar54, gp+0x130) * 1024 (from prior calc)
gp-0x4f64 = round(fVar39)   // speed-proportional governor
```
The value written is `round(gp+0x184 * 1024)` subject to the saturation logic. **If vehicle speed (gp+0x184) is near zero, the governor limit drops toward zero.**

**Branch uVar26 == 2 (line 1139):**
Same pattern: `fVar17 = (gp+0x184) * 1024.0`, saturated, written to gp-0x4f64.

**Branch else (uVar26 != 0 and != 2, line 1197):**
Uses `fVar45 * 1024.0` (a related speed-derived float from the MIN/LERP tree at lines 1059-1080), written to gp-0x4f64.

**All three branches compute a speed-scaled value from float data in the gp+0x100–0x1b0 region.** The cal constant at `tp+0x7202 = 0xC6202 = 4762` is the nominal (highway-speed) value. At low speed (near 0 mph) gp-0x4f64 **can drop well below 4762**, and in the limit approaches 0.

### Governor drop conditions (FLAGS)

**(a) Speed → 0:** gp+0x184 is a speed float. As vehicle speed drops to zero, the governor limit computes toward 0. This is a DESIGNED feature (reduces torque authority at standstill) but creates a collapse path.

**(b) uVar26 / mode byte gp-0x4e5a:** Written by FUN_00071272 (0x712aa st.b) and FUN_00075718 (0x7577e st.b). If gp-0x4e5a changes value abruptly (e.g., mode transition during an override), the three branches compute slightly different values. Normally the result is continuous, but if the mode byte changes on the same cycle as a low-speed condition, the branch-3 path may compute a lower intermediate value.

**(c) Lockstep shadow gp-0x448a:** FUN_0007b022 checks `gp-0x4f64 == gp-0x448a` before writing both atomically. Mismatch → calls FUN_0006b9ee (fault handler), **without writing gp-0x4f64**. If a fault fires here, gp-0x4f64 is left stale (not zeroed, but also not updated). Stale at a low-speed value = sustained suppress.

---

## 10. Governor Lockstep Shadow: gp-0x448a

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x7c2da | FUN_0007b022 | ld.hu | READ — lockstep check |
| 0x7c2e6 | FUN_0007b022 | st.h | WRITE — written with gp-0x4f64 atomically |
| 0x7c2ec | FUN_0007b022 | movea | address-of |
| 0x7c3a0 | FUN_0007b022 | ld.hu | READ — branch 2 check |
| 0x7c3b8 | FUN_0007b022 | st.h | WRITE — branch 2 |
| 0x7c3be | FUN_0007b022 | movea | address-of |
| 0x7c468 | FUN_0007b022 | ld.hu | READ — branch 3 check |
| 0x7c480 | FUN_0007b022 | st.h | WRITE — branch 3 |
| 0x7c486 | FUN_0007b022 | movea | address-of |

**Summary:** gp-0x448a is exclusively maintained by FUN_0007b022, in lockstep with gp-0x4f64. No other function touches it. When gp-0x4f64 and gp-0x448a diverge (e.g., via a single-event upset or memory bit error), FUN_0006b9ee is called instead of updating — so the fault itself does NOT zero the governor, it freezes it.

---

## 11. Mode-5 Gate Lane: gp-0x6afe

| Address | Function | Op | Role |
|---------|----------|----|------|
| 0x42ad6 | FUN_00042ac6 | st.h | WRITE — sole writer |
| 0x43ae0 | s_motor_torque_rate_shaper | ld.h | READ — shaper uses as gate input |

**FUN_00042ac6 is a simple clamp wrapper:**
```c
void FUN_00042ac6(int param_1) {
  if (param_1 + 0x2800 > 0x4FFF) param_1 = 0x7fff;  // clamp to 32767
  gp-0x6afe = (short)param_1;
}
```
Called from FUN_00027b0a (the accumulator/LERP stage) as its final output step (`FUN_00042adc(iVar10)` at the end of FUN_00027b0a — this is the same address). gp-0x6afe feeds the rate shaper as a lane-5 demand value. **No zero path here** — the clamp saturates at 32767 at the high end, but the normal input is the accumulator output which can legitimately be 0 when all channels report zero demand.

---

## 12. Summary: Zeroing / Collapse Mechanisms

### MECHANISM A — Governor limit drop (gp-0x4f64 → 0, speed-driven)

**Path:** FUN_0007b022 computes gp-0x4f64 = round(gp+0x184 * 1024). At low / zero vehicle speed, gp+0x184 → 0, so gp-0x4f64 → 0. m_motor_torque_governor then clamps gp-0x6b94 to ±0, writing gp-0x6ace = 0. m_post_governor_torque_comp_add writes gp-0x6acc ≈ 0 (plus small correction). s_motor_torque_rate_shaper sees 0 input. **Full assist suppression.**

**Relevance to hard-override transient:** During a hard override at low speed (or if the speed signal transiently drops — e.g., a CAN dropout or a speed near 0 during initial engagement), the governor can legitimately suppress to near-zero, killing all assist including base power-steering torque delivered through this chain.

**Severity:** HIGH. This is the primary mechanism. The nominal governor at highway speed is 4762; at parking-lot speeds it can be much lower; at very low speed it approaches 0.

### MECHANISM B — Aggregator lockstep fault (gp-0x6b94 shadow mismatch)

**Path:** If gp-0x6b94 ≠ gp-0x4ce0 at entry to m_motor_torque_demand_aggregator (caused by, e.g., a prior FUN_0006b9fa that left the shadow stale), the function calls FUN_0006b9fa without updating gp-0x6b94. The aggregator output is frozen, not zeroed. However, if the fault response itself writes 0 to gp-0x6b94, the downstream chain collapses. **This is not confirmed from available decompile — FUN_0006b9fa behavior is unverified.**

**Severity:** MEDIUM / UNVERIFIED. Need to decompile FUN_0006b9fa to confirm whether it zeros or freezes the output variable.

### MECHANISM C — Governor hold-value collapse (gp-0x138a)

**Path:** Inside m_motor_torque_governor, when `gp-0x67fa == 4`, the hold accumulator `gp-0x138a` is substituted for the governed output if its magnitude is less than the governed value. gp-0x138a initializes to 0 (when `gp-0x5000 == 0`, a first-run flag). On first engage, or after a disengagement, gp-0x138a = 0 and the rate-limiter substitutes 0 for the commanded value, producing a soft ramp from 0 rather than a hard step. **This is the designed ramp-up behavior, not a fault.**

**Severity for "hard override" transient:** The rate-limiter accumulator in the governor means that after an override clears, the output ramps back up from its held value. If the override was sustained long enough for gp-0x138a to decay toward the driver torque direction, disengage causes a momentary near-zero before ramping.

### MECHANISM D — Deadband / slew-limiter in rate shaper (from prior Civic analysis)

**Note:** The Civic firmware has a confirmed deadband/slew mechanism in s_motor_torque_rate_shaper (tp+0x71D6 step size). Whether the Accord firmware has an analogous structure needs verification — the Accord shaper function `s_motor_torque_rate_shaper` IS present and reads gp-0x4f64 and gp-0x6afe — but the specific deadband and slew constants need a separate decompile.

### MECHANISM E — gp-0x6b4c range-zero at aggregator

**Path:** m_motor_torque_demand_aggregator zeros the LKAS contribution if gp-0x6b4c is outside ±0x2800. Under normal LKAS operation gp-0x6b4c stays within ±10240 so this does not fire. However, if the mixer writes an out-of-range value (e.g., due to a stuck distribute-clamp or an upstream saturation), the LKAS lane is silently dropped from the sum without a DTC.

**Severity:** LOW under normal conditions. Would require an upstream fault in distribute_clamp.

---

## 13. Unexpected Writers / Anomalies

| Variable | Unexpected Writer | Notes |
|----------|-------------------|-------|
| gp-0x4f64 | FUN_0007b022 ONLY | This is the expected pattern, but the function is very large (50k+ char decompile) and contains 3 write paths, all speed-derived. No other function touches gp-0x4f64 — confirmed program-wide. |
| gp-0x3d74 | FUN_0007b022 uses movhi base | The governor writer uses the gp+0x184 speed region (near gp+0x3d74 as a base pointer) — not a direct write, but confirms the governor's float inputs come from this memory band. |
| gp-0x448a | FUN_0007b022 ONLY | Lockstep shadow maintained exclusively by governor writer. Clean. |
| gp-0x6b4c | FUN_00038148 reads | FUN_00038148 at 0x3816c reads gp-0x6b4c — unknown role. Not a writer. Needs decompile to classify. |
| gp-0x6b94 | FUN_0007ff08 reads | FUN_0007ff08 at 0x80820 reads aggregator output — unknown role. Likely telemetry/monitoring. Not a writer. |

---

## 14. New gp-offsets Discovered During This Trace

| Variable | Address(es) | Discovered In | Role |
|----------|-------------|---------------|------|
| gp-0x4ce0 | (aggregator shadow) | m_motor_torque_demand_aggregator decompile | Lockstep shadow of gp-0x6b94 |
| gp-0x4cca | (governor shadow) | m_motor_torque_governor decompile | Lockstep shadow of gp-0x6ace |
| gp+0x184 | FUN_0007b022 decompile | Speed float used to compute governor limit | Critical — see Section 9 |
| gp-0x67fa | m_motor_torque_governor decompile | Mode flag: ==4 activates hold/ramp path | Affects ramp-up after override |
| gp-0x5000 | m_motor_torque_governor decompile | First-run flag for gp-0x138a init | |
| gp-0x138a | m_motor_torque_governor decompile | Hold accumulator for rate-limiting | Can be 0 on first engage |
| gp-0x4e5a | FUN_0007b022 / FUN_00071272 | Branch selector for governor computation | Written by FUN_00071272, FUN_00075718 |

---

## 15. Recommended Next Steps

1. **Decompile FUN_0006b9fa** — confirm whether the safety fault handler writes 0 to gp-0x6b94 / gp-0x6ace, or only freezes them. This determines severity of Mechanism B.
2. **Decompile FUN_00038148** — classify unknown reader of gp-0x6b4c.
3. **Decompile s_motor_torque_rate_shaper** — check for Civic-style deadband/slew-limiter and confirm whether gp-0x6afe feeds a separate zeroing path.
4. **Trace gp+0x184** — confirm it is the vehicle speed CAN signal and how it is populated; verify the speed-to-governor-limit mapping.
5. **Decompile FUN_0007b022 branch entrance** — identify what gp-0x4e5a == 0/2/other maps to in the state machine.

### === cluster3_shaper_foc ===

# Cluster 3 — Rate Shaper + Dual-Path Lockstep + FOC Handoff
**Program:** code.bin (V850:LE:32, image_base 0x0, gp=0xFEDF8000, tp=0xBF000)
**Function analyzed:** s_motor_torque_rate_shaper (FUN_00042af8, 0x42af8–0x43e43)
**Date:** 2026-05-27
**Method:** search_instructions (program-wide, -0xOFF operand pattern) + full disasm 0x42af8–0x43e43

---

## 1. gp-offset Inventory Table

| gp offset | Abs address | Role | Writers (addr, fn) | Readers (addr, fn) | Notes |
|-----------|-------------|------|--------------------|--------------------|-------|
| **0x356c** | 0xFEDF4A94 | Slew accumulator (int32) — persists slew state across ticks | 0x43504 st.w r12 (shaper) | 0x434ce ld.w r9 (shaper) | Zeroed by deadband: r12=0 stored at 0x43504; with step=0, stays 0 |
| **0x3570** | 0xFEDF4A90 | Demand accumulator (int32) — integrates combined demand×rate each tick | 0x4327c st.w r10 (shaper) | 0x43214 ld.w r10, 0x432de ld.w r10 (shaper×2) | Scaled demand input to deadband logic; |r10>>15| = uVar53; LKAS+base-assist combined |
| **0x6966** | 0xFEDF169A | Scaled demand magnitude (uVar34 = uVar53×1092>>10) — deadband comparand | 0x432c8 st.h r13 (shaper) | 0x42d86 ld.hu r13 (shaper), 0x432e2 ld.hu r13 (shaper), 0x43df0 ld.hu r16 (shaper), 0x3a632 ld.hu r11 (FUN_0003a382) | Lockstep-shadowed with 0x4c5a |
| **0x4c5a** | 0xFEDF33A6 | Lockstep shadow of 0x6966 (dual-path consistency check) | 0x432cc st.h r9 (shaper) | 0x432b4 ld.hu r14 (shaper) | Fault via FUN_0006b9fa at 0x432d6 if 0x4c5a≠0x6966 |
| **0x6b98** | 0xFEDF1468 | **FINAL delivered motor command → FOC** | **0x43b52 st.h r8 (shaper) — PRIMARY**; **0x43dfc st.h r21 (shaper) — LOCKSTEP 2nd write**; 0x6e104 st.h r12 (FUN_0006e09a); 0x6e1dc st.h r10 (FUN_0006e140) | 45 load sites across 20+ functions (telemetry, FOC, lockstep monitors) | TWO external writers outside shaper — see section 4 |
| **0x4ce2** | 0xFEDF331E | Lockstep shadow of gp-0x6b98 | 0x43b56 st.h r8 (shaper), 0x43e00 st.h r21 (shaper) | 0x43b48 ld.h r7 (shaper), 0x43de8 ld.h r14 (shaper), multiple FOC/monitor fns | Fault via FUN_0006b9fa at 0x43b60 / 0x43e0a if 0x4ce2≠0x6b98 |
| **0x6dbc** | 0xFEDF1244 | Float-path shadow (gp-0x6b98 equivalent in float domain) | 0x44a22 st.w r9 (FUN_00043e44) | 0x43b24 ld.w r12 (shaper) | Used for float-to-int conversion check just before gp-0x6b98 store 1 |
| **0x6db8** | 0xFEDF1248 | Float-path shadow (demand) | — (not in search results) | — | Listed in brief; not found as distinct offset in this search |
| **0x6dc0** | 0xFEDF1240 | Float-path shadow (demand) | — | 0x43288 ld.w r9 (shaper) | Read in shaper near gp-0x6dbc read |
| **0x4cce** | 0xFEDF3332 | Lockstep shadow of gp-0x6b04 | 0x43a88 st.h r14, 0x43e1e st.h r28 (shaper×2) | 0x43a6a ld.h r12 (shaper), 0x43e12 ld.h r10 (shaper) | Fault via FUN_0006b9fa at 0x43a92 / 0x43e28 |
| **0x4ce2** | (see above) | Lockstep of gp-0x6b98 | (see above) | (see above) | Already listed |
| **0x6b00** | 0xFEDF1500 | Shaper neighbor — demand tracking state | 0x43a78 st.h r27 (shaper), 0x43e30 st.h r27 (shaper) | 0x431a0 ld.h r8 (shaper) | Part of demand velocity tracking |
| **0x6b08** | 0xFEDF14F8 | Shaper intermediate — gated shaper input (mode-select output; fed by gp-0x6acc) | 0x43206 st.h r11 (shaper) | 0x43a96 ld.h r11 (shaper), 0x432e6 ld.h r11 (shaper) | The "r11 = gp-0x6b08" at 0x43a96 is what populates r20 fallback when cVar8≠0 |
| **0x6b0a** | 0xFEDF14F6 | Shaper neighbor — demand velocity index | 0x43a72 st.h r24 (shaper), 0x43e34 st.h r24 (shaper) | 0x43294 ld.hu r18 (shaper), 0x432da ld.hu r18 (shaper) | |
| **0x6b02** | 0xFEDF14FE | Shaper neighbor — assist polarity record | 0x43c26 st.h r20 (shaper) | — | Written near end of shaper for downstream telemetry |
| **0x6b04** | 0xFEDF14FC | Parallel internal demand path (dual-path lockstep mirror) | 0x43a84 st.h r14, 0x43e1a st.h r28 (shaper×2) | 0x43a42 ld.h r15 (shaper), 0x43e0e ld.h r8 (shaper) | Lockstep-checked with 0x4cce |
| **0x6bf0** | 0xFEDF1410 | Base driver-assist demand entering shaper | 0x3c0cc st.h r6 (FUN_0003bd7c), 0x3c184 st.h r0 (FUN_0003bd7c), 0x3e7f4 st.h r0 (FUN_0003e760) | 0x43032 ld.h r10 (shaper), 0x43116 ld.h r6 (shaper), 11 other fns | Two shaper reads: 0x43032 (gp-0x67fe gate path) + 0x43116 (assist range check) |
| **0x67fe** | 0xFEDF1802 | Base-assist enable flag — gates gp-0x6bf0 load | 0x3bdb8 st.b r0, 0x3be4e st.b r6, 0x3be5a st.b r15, 0x3be7a st.b r0 (all FUN_0003bd7c) | 0x43016 ld.bu r8 (shaper); many other fns | Value meaning — see section 3 |
| **0x6bb0** | 0xFEDF1450 | FOC consumer 1 — motor current command A | 0x370f4 st.h r10, 0x3712e st.h r6 (FUN_000370b6×2) | 0x370c2 ld.h r7 (FUN_000370b6), 0x374c2 ld.h r12 (FUN_00037494), 0x377f4 ld.h r15 (FUN_000377ba), 0x37ac0 ld.h r23 (FUN_000378d6) | Downstream of gp-0x6b98 via FOC dispatch; writer FUN_000370b6 reads gp-0x6b98 at 0x370be |
| **0x4cee** | (FOC consumer) | Lockstep shadow FOC cmd | Not in brief's search results | — | Listed in brief; search not run |
| **0x6b54** | (FOC consumer) | FOC intermediate | Not in brief's search results | — | Listed in brief; search not run |
| **0x6bf6** | 0xFEDF140A | Mode-5 / gate assist output (feeds shaper via parallel path) | 0x3bac0 st.h r12, 0x3bc0e st.h r7 (FUN_0003b8f6×2) | — not found as reader | Appears to be upstream demand contribution to gp-0x3570 accumulator |
| **0x6c00** | (FOC consumer) | FOC output | Not in brief's search results | — | Listed in brief; search not run |

---

## 2. DECISIVE ANSWER: Does the deadband iVar45=0 reach gp-0x6b98?

**YES — the deadband zero DOES reach the final gp-0x6b98 store. But the decompiler variable reuse makes the path non-obvious. Here is the verified disassembly chain:**

### The deadband check (0x434c2–0x434ee)

```
0x434c2: ld.hu 0x3a[sp], r17          ; r17 = tp+0x7424 = 29491 (deadband threshold)
0x434c6: andi 0xffff, r15, r26         ; r26 = LERP demand result
0x434ca: cmp r17, r13                  ; r13 = uVar34 = uVar53*1092>>10 (scaled demand magnitude)
0x434cc: bc 0x434ee                    ; BRANCH if r13 < r17 (unsigned below = demand < 90% max)
  ; *** DEADBAND BRANCH ***
  0x434ee: mov r0, r12                 ; r12 = 0 (iVar45=0 in decompile)
  ; falls through to 0x434f0
; *** NON-DEADBAND path (demand above threshold): ***
  0x434ce: ld.w -0x356c[gp], r9       ; load slew accumulator
  ; ... slew ramp clamps r12 toward demand target by step tp+0x71D6=0 ...
```

### Critical register trace: deadband r12=0 → two output channels

**Channel A — slew state persistence (gp-0x356c):**
```
0x434ee: r12 = 0
0x434f0: mov r12, r16   → r16 = 0
0x434f2: add r27, r16   → r16 = r27  (r27 = demand component from accumulator sign path)
0x434f4: mov r29, r14
0x434f6: cmovp r0, r16, r8  → r8 = 0 if r27>0, else r8=r27  [PSW positive flag from add]
0x434fa: sub r12, r14   → r14 = r29 - 0 = r29
0x434fe: cmovle r0, r14, r6 → r6 = 0 if r29≤0 else r6=r29
0x43502: cmp r8, r11    ; compare r8 (≈0) vs r11 (gp-0x6b08 = gated input)
0x43504: st.w r12, -0x356c[gp]  → **gp-0x356c = 0 written**  [slew accumulator zeroed]
```

**Channel B — state machine → assist output → LERP → governor → r21 → gp-0x6b98:**
```
0x43524+: state machine reads r8 (≈0), r11 (gp-0x6b08)
   → state machine sets gp-0x6960 = 0 (at 0x4362a: st.h r0,-0x6960[gp])
     when assist-state timeout/zero-crossing condition fires
   → 0x435b2/0x435f6/0x436b2: ld.hu -0x6960[gp], r6  → r6 = 0
0x439c0: cmp r12, r6    ; r12 here = state-machine output r12
0x439c2: cmovnc r12, r6, r8  → r8 = assist output (can be 0)
0x43a10: ld.hu 0x2e[sp], r8  ; r8 reloaded from stack (demand curve output)
0x43a1c: mov r11, r15
0x43a20-0x43a38: LERP(demand curves, r8, r11) → r28
0x43a3a: mul r26, r28, r0; sar 0xf, r28  → r28 = demand × speed_gain  [≈0 when r26≈0]
0x43a9a: ld.bu 0xb[sp], r18  ; r18 = tp+0x74C9 = 0
0x43a9e: cmp r0, r18         ; Z=1
0x43aa0: cmove r28, r11, r20 → r20 = r28 (since Z=1; cVar8=0)
0x43ae0: ld.h -0x6afe[gp], r13   ; feed-forward
0x43ae4: ld.hu -0x4f64[gp], r10  ; governor cap
0x43af0: cmovc 0x0, r13, r12     ; r12 = feed-forward if in range, else 0
0x43af4: add r20, r12            ; r12 = feed-forward + r28 (≈0)  [r12 REASSIGNED here]
0x43afa: cmovc 0x0, r10, r14     ; r14 = governor cap if r10<0x2801 else 0
0x43afe: cmp r14, r12; ...       ; governor clamp
0x43b0e: addi -0x2000, r14, r0; movea 0x2000, r0, r21  ; ±0x2000 hard clamp
0x43b16: bgt 0x43b24; 0x43b1c: movea -0x2000, r0, r6; cmovle r6, r14, r21
  → r21 = clamp(r14, -0x2000, +0x2000)  [= 0 when r14≈0 from deadband chain]
0x43b4e: mov r21, r8
0x43b52: st.h r8, -0x6b98[gp]   *** STORE 1: gp-0x6b98 = r21 ***
```

**Second lockstep write:**
```
0x43de8: ld.h -0x4ce2[gp], r14
0x43dec: ld.h -0x6b98[gp], r12
0x43df4: cmp r14, r12   ; consistency check: 0x4ce2 == 0x6b98?
0x43dfa: bne 0x43e06    ; mismatch → fault handler FUN_0006b9fa
0x43dfc: st.h r21, -0x6b98[gp]  *** STORE 2: redundant write of same r21 ***
0x43e00: st.h r21, -0x4ce2[gp]  ; update shadow too
```

### Verdict: iVar45 IS reassigned before the store, but the zero still propagates

The decompiler reuses `iVar45` for:
- Line ~1253 in decompile: iVar45=0 (deadband) → maps to **r12 at 0x434ee**
- Line ~1255 in decompile: iVar45 = clamp(±0x2000) → maps to **r21 at 0x43b12–0x43b20**

These are DIFFERENT physical registers. The deadband r12=0 does NOT travel directly to the final store's r21. However, the zero DOES reach gp-0x6b98 via Channel B:

1. r12=0 → r8≈0 (cmovp) → state machine triggers zero-assist state → gp-0x6960=0
2. gp-0x6960=0 → r6=0 → assist output → r26≈0 → r28 LERP ≈ 0 → r20≈0
3. r12 (feed-forward + r20) ≈ 0 → governor clamps ≈ 0 → r21 ≈ 0 → gp-0x6b98 = 0

**The decompile-level iVar45=0 correctly predicts gp-0x6b98→0, but the mechanism is through the state machine assist-output path, not a direct register carry. The critical intermediary is gp-0x6960 (zero-assist state) zeroed by the state machine transition when r8≈0 at 0x43502/cmp.**

With step=0 (tp+0x71D6=0), the slew accumulator gp-0x356c stays at 0 once zeroed (next tick also produces r12=0 from slew → repeats the chain). Recovery requires the demand accumulator gp-0x3570 to rebuild above 90% (= uVar34 ≥ 29491 = uVar53 ≥ 27654), which at combined demand 1000 takes ~28ms, at 500 ~55ms.

---

## 3. gp-0x67fe (base-assist enable flag): Values and gating of gp-0x6bf0

### Usage inside s_motor_torque_rate_shaper (verified disassembly)

```
0x43016: ld.bu -0x67fe[gp], r8  ; r8 = gp-0x67fe (byte)
0x4301a: cmp 0x2, r8             ; is r8 == 2?
0x4301c: setfne r6               ; r6 = (r8 ≠ 2)
0x43020: cmp 0x1, r8             ; is r8 == 1?
0x43022: setfne r15              ; r15 = (r8 ≠ 1)
0x43026: cmp r0, r6
0x43028: ld.hu 0x741a[tp], r21  ; r21 = tp+0x741a (speed threshold for base-assist gate)
0x4302c: be 0x43032              ; if r8==2 → branch to load gp-0x6bf0
0x4302e: cmp r0, r15
0x43030: bne 0x43046             ; if r8≠1 → skip gp-0x6bf0 load
0x43032: ld.h -0x6bf0[gp], r10  ; *** load base-assist demand ***
0x43036: ori 0xc801, r0, r16     ; r16 = 0xc801
0x4303a: addi 0x6400, r10, r7   ; r7 = gp-0x6bf0 + 25600
0x4303e: cmp r16, r7             ; check range: gp-0x6bf0 + 25600 < 0xc801 = 51201?
0x43040: setfnc r1               ; r1 = 1 if gp-0x6bf0 < 25601
0x43044: br 0x43048
0x43046: mov 0x1, r1             ; else r1 = 1 (force base-assist enable)
```

**Interpretation:**
- `gp-0x67fe = 1` or `gp-0x67fe = 2`: base-assist enable flag TRUE → gp-0x6bf0 is loaded and range-checked → r1 = base-assist-in-range flag
- `gp-0x67fe = 0` (or any other value): skip gp-0x6bf0 load → r1 = 1 (hardcoded enable) → base assist treated as always-enabled with range check bypassed
- The range check at 0x4303e: gp-0x6bf0 must be < 25601 raw (= ~6.25 Nm if Q8.8 scale) to pass; outside = r1=0 = suppress base-assist contribution

**Writers of gp-0x67fe** (from FUN_0003bd7c):
- 0x3bdb8: `st.b r0, -0x67fe[gp]` — zero (disable)
- 0x3be4e: `st.b r6, -0x67fe[gp]` — variable value
- 0x3be5a: `st.b r15, -0x67fe[gp]` — variable value
- 0x3be7a: `st.b r0, -0x67fe[gp]` — zero (disable)

FUN_0003bd7c is the primary writer. It is the base-assist torque computation function (reads/writes both gp-0x67fe and gp-0x6bf0).

### Does base-assist (gp-0x6bf0) go to 0 TOGETHER with LKAS?

**Structurally YES** when the deadband fires — both converge in gp-0x3570 before the deadband check:

The demand accumulator gp-0x3570 integrates the sum of both LKAS demand and base-assist demand on each tick. The deadband tests the COMBINED magnitude (uVar34 from gp-0x3570). When LKAS is commanding strongly in one direction and the driver overrides in the other, the combined demand passes through zero, causing uVar34 to drop below 90%.

At that point, the deadband fires and zeroes gp-0x356c (slew state), which via the state machine zeroes gp-0x6960 → zeroes the final r21 written to gp-0x6b98. Since gp-0x6b98 is the ONLY path to FOC (base-assist has no separate FOC path — confirmed by gp-0x6b98 being the sole command output to FOC), zeroing gp-0x6b98 kills both LKAS AND base power steering simultaneously.

**Note**: If gp-0x67fe=0 (base-assist disabled) AND gp-0x6bf0=0, the demand accumulator gp-0x3570 carries only LKAS demand. In that case the LKAS component alone must drop below 90% for the deadband to fire. During a strong 2× LKAS command, the component doesn't drop until the driver pushes hard enough to zero the net demand.

---

## 4. gp-0x6b98 Writers Outside the Shaper

Two external writers found:

| Address | Function | Mnemonic | Operand | Context |
|---------|----------|----------|---------|---------|
| 0x6e104 | FUN_0006e09a | st.h r12, -0x6b98[gp] | Writes r12 | Appears to be a fault/reset path or override handler; needs Ghidra decompile to classify |
| 0x6e1dc | FUN_0006e140 | st.h r10, -0x6b98[gp] | Writes r10 | Appears to be second fault/reset variant; same function family |

**Assessment (belief, not fully confirmed):** These functions are likely called in abnormal conditions (EPS fault, torque-sensor plausibility failure, power-on initialization). They would override the shaper output with a safe/zero value. The shaper itself does not call these during normal LKAS operation.

**Verification needed:** Ghidra decompile of FUN_0006e09a (0x6e09a) and FUN_0006e140 (0x6e140) to confirm they are fault/reset handlers and not a parallel torque-injection path.

---

## 5. New gp-Offsets Discovered During This Analysis

| gp offset | Abs address | Role | Discovery context |
|-----------|-------------|------|-------------------|
| 0x6960 | 0xFEDF169F | Assist level output from state machine (zeroed by state machine when zero-crossing/timeout) | Critical intermediary: deadband→r8→state machine→gp-0x6960=0→r6=0→r26=0→r28=0→r20=0→r21≈0→gp-0x6b98=0 |
| 0x6af8 | 0xFEDF1508 | Assist velocity/LERP weight | Read at multiple points inside shaper: 0x43564, 0x43594, 0x437f8, 0x4381c, 0x43678 |
| 0x6a74 | 0xFEDF1D8C | Assist timer counter (zeroed when state machine resets, incremented otherwise) | 0x435b6 st.h r0; 0x43602 st.h r0; 0x4362c st.h r0; etc. |
| 0x6a72 | 0xFEDF1D8E | Assist ramp counter (secondary timer) | 0x4380c / 0x43864 / 0x43886 st.h |
| 0x6785 | 0xFEDF187B | Assist state byte 2 (sub-state for state machine) | Written with 0x1/0x2/0x3 across state machine branches |
| 0x6786 | 0xFEDF187A | Assist state byte 1 | Written with 0x1/0x2/0x3 across state machine branches; read at 0x43d88 |
| 0x6711 | 0xFEDF18EF | Assist step counter (incremented each state machine cycle) | 0x435fe/0x436a0/0x43732 etc. |
| 0x355d | 0xFEDF4AA3 | First-level state byte for base-assist state machine | Multiple writes (1/2/3/4) |
| 0x355e | 0xFEDF4AA2 | Second-level state byte | Multiple writes |
| 0x355f | 0xFEDF4AA1 | Third-level state byte | Multiple writes |
| 0x3560 | 0xFEDF4AA0 | Fourth-level state byte | Multiple writes |
| 0x3561 | 0xFEDF4A9F | Direction state (1=positive, -1=negative) | Written at 0x43722/0x43774 |
| 0x3562 | 0xFEDF4A9E | Outer convergence flag (1=initial, 2=converged) | Written at 0x42ff6/0x43010 |
| 0x355c | 0xFEDF4AA4 | Convergence counter | Written at 0x42fd0/0x42fe8/0x42fee |
| 0x6908 | 0xFEDF16F8 | Assist debug output | 0x43be8 st.h r1 |
| 0x6964 | 0xFEDF169C | Demand output record (stored twice in shaper: 0x43bf8, 0x43e2c) | Locked with r26 |

---

## 6. Summary Table: All gp-0x6b98 Touchers

| Address | Function | Mnemonic | Count | Role |
|---------|----------|----------|-------|------|
| 0x43b52 | s_motor_torque_rate_shaper | st.h r8 | WRITE | **Primary shaper output — r21 (clamped ±0x2000)** |
| 0x43dfc | s_motor_torque_rate_shaper | st.h r21 | WRITE | **Secondary/lockstep shaper output — same r21** |
| 0x6e104 | FUN_0006e09a | st.h r12 | WRITE | External writer — likely fault/reset |
| 0x6e1dc | FUN_0006e140 | st.h r10 | WRITE | External writer — likely fault/reset |
| 0x43b34 | s_motor_torque_rate_shaper | ld.h r15 | READ | Pre-store lockstep read (before 0x43b52) |
| 0x43dec | s_motor_torque_rate_shaper | ld.h r12 | READ | Pre-store lockstep read (before 0x43dfc) |
| 0x19fe2 | FUN_00019f7c | ld.h r10 | READ | Telemetry/monitor |
| 0x1c0c8 | FUN_0001bf88 | ld.h r15 | READ | Telemetry/monitor |
| 0x1c22c | FUN_0001c1ce | ld.h r10 | READ | Telemetry/monitor |
| 0x24448 | FUN_000242a2 | ld.h r24 | READ | Telemetry/monitor |
| 0x2c47c | FUN_0002c478 | ld.h r6 | READ | Reads gp-0x67fe + gp-0x6b98 — combined assist status |
| 0x35ee6 | FUN_00035e00 | ld.h r8 | READ | Base-assist demand consumer |
| 0x370be | FUN_000370b6 | ld.h r14 | READ | **FOC dispatch — primary motor command consumer** |
| 0x3b00a | FUN_0003aff4 | ld.h r12 | READ | FOC downstream |
| 0x3b8f6 | FUN_0003b8f6 | ld.h r7 | READ | FOC downstream |
| 0x41672 | FUN_00041464 | ld.h r16 | READ | FOC downstream |
| 0x41846 | FUN_00041464 | ld.h r9 | READ | FOC downstream (second read same fn) |
| 0x41bd8 | FUN_00041b8e | ld.h r13 | READ | FOC downstream |
| 0x448d6 | FUN_00043e44 | ld.h r12 | READ | Float-path cross-check |
| 0x56420 | FUN_00056420 | ld.h r14 | READ | Supervisory |
| 0x56554+ | FUN_00056518 | ld.h (×3) | READ×3 | Supervisory / CAN TX |
| 0x569c4+ | FUN_000568d0 | ld.h (×2) | READ×2 | CAN TX / telemetry |
| 0x59a44+ | FUN_00059912 | ld.h (×6) | READ×6 | CAN TX broadcast |
| 0x59f7c+ | FUN_00059e7a | ld.h/ld.hu (×4) | READ×4 | CAN TX broadcast |
| 0x65c90 | FUN_00065afe | ld.h r15 | READ | Supervisory |
| 0x69bee+ | FUN_00069b8e | ld.h (×2) | READ×2 | Supervisory |
| 0x70bfc | FUN_00070a98 | ld.h r11 | READ | Safety check |
| 0x7580c | FUN_000757a2 | ld.h ep | READ | Safety check |
| 0x7c52c | FUN_0007c4f2 | ld.h r14 | READ | Safety check |
| 0x7c94e | FUN_0007c94a | ld.h r12 | READ | Safety check |
| 0x81be8 | FUN_00081b24 | ld.h r15 | READ | Supervisory/logging |

**Total: 4 WRITE sites (2 shaper + 2 external), ~41 READ sites across ~20+ functions.**

---

## 7. Calibration Values (Verified via tp=0xBF000)

| Cal offset | Abs addr | Value (LE u16/u8) | Role |
|------------|----------|-------------------|------|
| tp+0x71D6 | 0xC61D6 | 0x0000 = 0 | Slew step — **zero = slew disabled; deadband holds gp-0x6b98=0 indefinitely** |
| tp+0x71DA | 0xC61DA | 0x0444 = 1092 | Scale factor for uVar34 = uVar53×1092>>10 |
| tp+0x71DC | 0xC61DC | 0x7800 = 30720 | Demand accumulator clamp max |
| tp+0x7422 | 0xC6422 | 0x4000 = 16384 | Lane-2 deadband threshold (50% of max) |
| tp+0x7424 | 0xC6424 | 0x7333 = 29491 | **Main deadband threshold (90% of max) — TRIGGER point** |
| tp+0x74C9 | 0xC64C9 | 0x00 | cVar8: 0=use LERP output (r28) for r20; 1=use raw input (gp-0x6b08) |

---

*Generated by firmware-codepath-tracer agent, 2026-05-27. Based on full disassembly of FUN_00042af8 (s_motor_torque_rate_shaper) + program-wide search_instructions for all listed gp-offsets.*

### === cluster4_assist_caltables ===

# 2020 Accord EPS — Base Assist Cluster 4 Cal Tables
## Context
- Ghidra program: `code.bin` (V850:LE:32, image_base=0x0)
- gp = 0xFEDF8000, tp = 0xBF000 → abs addr = tp + offset = 0xBF000 + offset
- READ-ONLY session (no writes). Session date: 2026-05-27.
- Abs addresses given as 0xBF000 + tp_offset. Ghidra address = abs addr (image_base=0).

---

## Part A — RAM Variables (gp-relative, abs = 0xFEDF8000 − offset)

| gp-Offset | Abs RAM Addr | Width | Direction | Functions / Addresses | Semantic |
|---|---|---|---|---|---|
| `-0x4e65` | `0xFEDF319B` | u8 / s8 | **R** FUN_00065af8 @ 0x65AF8; **R** FUN_00065eda @ 0x65F04, 0x65F82, 0x65FE8; **R+W** FUN_0006651e @ 0x665E8,0x66614,0x6669C,0x666BA,0x666E0,0x666F0,0x666FC; **R** FUN_0006964c @ 0x6968E | **Assist-mode state byte.** Values: 0=NORMAL (calls FUN_0006634e), 1=STARTING/RAMP (calls FUN_00068dfe + sets gp-0x4e6c=1; transitions→2 when speed threshold met), 2=ACTIVE, 3=TRANSITION (condition checks for mode-0→1 re-init), 4=FAULT/INHIBIT (set by multi-sensor fault path FUN_0005b2be(4/5/0x2A) returning 3). The final `st.b r28,-0x4e65,gp` write at 0x65F8E (FUN_65eda) and 0x666FC (FUN_6651e) has a lockstep redundancy check against mirror at gp-0x4458 — mismatch calls FUN_0006b9ee. |
| `-0x4fb8` | `0xFEDF0048` | s16 | **W** FUN_0006634e @ 0x663C2, 0x6649C; **R** FUN_000690f8 @ 0x690F8 | Assist demand output channel A (motor current, signed 16). Written by curve-interpolation in the initialization path. Read by FOC/current-control handler. |
| `-0x4fbc` | `0xFEDF0044` | s16 | **W** FUN_0006634e @ 0x66412, 0x664AC; **R** FUN_000690f8 @ 0x6911A | Assist demand output channel B. Parallel to -0x4fb8; separate coil/phase. |
| `-0x4fb6` | `0xFEDF004A` | s16 | **W** FUN_0006634e @ 0x664CC; **R** FUN_000690f8 @ 0x6913A | Assist demand output channel C. |
| `-0x4fba` | `0xFEDF0046` | s16 | **W** FUN_0006634e @ 0x664DE; **R** FUN_000690f8 @ 0x6912C | Assist demand output channel D. |
| `-0x34ec` | `0xFEDFCB14` | ptr (s32) | **W** FUN_00048a40 @ 0x48C90; **R+W** FUN_00049180 @ 0x4929C, 0x492CE; **R** FUN_000498de @ 0x4998A; **R** FUN_0006634e @ 0x66352; **R** FUN_0007dae4 @ 0x7DB04, 0x7DBC6 | Assist-curve **row pointer A** (pointer to lower row struct). FUN_0006634e reads both this and -0x34e8 to perform LERP between two assist-curve table rows. |
| `-0x34e8` | `0xFEDFCB18` | ptr (s32) | **W** FUN_00048a40 @ 0x48CB0; **R+W** FUN_00049180 @ 0x492D2, 0x49304; **R** FUN_000498de @ 0x49992; **R** FUN_0006634e @ 0x66356; **R** FUN_0007dae4 @ 0x7DB00 | Assist-curve **row pointer B** (pointer to upper row struct). Together with -0x34ec forms the two surrounding rows for temperature-interpolated assist demand. |
| `-0x2a40` | `0xFEDFD5C0` | s32 | **W** FUN_00065eda @ 0x661CE (=7), 0x66346 (=0); **W** FUN_0006634e @ 0x66512 (=13); **W** FUN_0006651e @ 0x666DC (=6), 0x666EC (=7), 0x6689C (=0); **R** FUN_0006651e @ 0x6670E | **Assist trigger / demand-ready flag.** Set to 1 by the active assist path to signal that current demand outputs are valid. Cleared to 0 at end of cycle. Used as a guard by FUN_0006651e to decide whether to update the motor current setpoints. |

### Assist-mode dropout path (gp-0x4e65 forced to fault/non-normal state)

`FUN_00065eda` (the outer assist-mode manager) tests two gates before entering the normal assist branch:

1. **Gate 1 — global fault bit 15:** `FUN_000197d0(0xf)` tests bit 15 of a fault-flag word at `gp-0x6d78`. If set → forced to the fault branch.
2. **Gate 2 — `FUN_0006fd42()`:** Returns 1 when a fault condition is active. If it returns 1, also forced to the fault branch.
3. **Gate 3 — `gp-0x4e6a == 1`:** An inhibit flag. Any one of these gates being true bypasses the normal path.

When in the fault/non-normal branch (gates 1/2/3 true), `FUN_00065eda` tests: if `cVar14 == 3` (current assist mode is TRANSITION) AND `gp-0x4e67 == 0`, it sets `gp-0x4e6b = 1` (the re-init flag).

**State 4 (FAULT/INHIBIT) trigger path:** `FUN_0005b2be(param)` is called with params 4, 5, and 0x2A — if any returns 3 (fault active), `cVar14` is set to 4 before the lockstep write. This is the **sensor fault path** that sets mode=4 without a latched DTC.

In `FUN_0006651e`, the assist-mode state machine:
- State 3 (TRANSITION) + flag `gp-0x4e6b == 1` → calls the convergence check (torque-sensor plausibility window via `gp-0x5000`/`gp-0x4ffe` vs. tp+0x5978/0x5970 thresholds). If the channels fail to converge within `tp+0x5x14` counts → state transitions to 1 (STARTING), re-initiating the full ramp sequence. **This is the re-engagement ratchet.** Every failed convergence check fires another state-1 ramp from scratch.

**Core dropout mechanism (confirmed by Era-15 EME constellation note):**
- Driver applies large hand torque on a sharp turn → column torque sensor dual-coil plausibility voter `FUN_00041eec` (5 ADC channels `gp-0x6a44/40/3c/38/46`) fires plausibility inhibit or the inter-channel delta exceeds the threshold → sets `gp-0x4e6b` (re-init flag) or forces state to 3 → re-init ramp cycle.
- With 2× arb gain (`tp+0x746c` 891→1782), the amplified arb output makes the delivered LKAS zero at the same instant (ENABLE byte `0xFEDF195C` written at 0x2b51e clears), and re-ramp through the shaper's deadband (tp+0x7424=29491, ~90% of range) is slow → **whole-assist dropout + ratchet**.
- **The gp-0x4e65 state byte does NOT latch a DTC.** The transition through states 3→1→2→3 is purely runtime and self-recovers when sensor channels reconverge.

---

## Part B — Flash Calibration Constants (tp+offset, abs = 0xBF000+offset)

### Core torque path

| tp-Offset | Abs Addr | Current Value (u16 LE) | Decoded | Code Load Site(s) | Semantic | Editable? |
|---|---|---|---|---|---|---|
| `0x746c` | `0xC646C` | `7b 03` | **891** | `m_steer_torque_arbitration` @ 0x2A1EE (ld.h); FUN_0002b62c @ 0x2B656; FUN_0002c478 @ 0x2C488; FUN_00036682 @ 0x36686; FUN_00036828 @ 0x3684A | **Arb output Q15 gain.** `out = (combined_torque × polarity × GAIN[891]) >> 15`. V14 raised this to 1782 (×2). Primary lever for LKAS magnitude. | YES — V14 doubled this. |
| `0x71b2` | `0xC61B2` | `00 02` | **512** | `m_steer_torque_limit_and_pack` @ 0x2B42A, 0x2B436, 0x2B43C, 0x2B446; FUN_0002b57a @ 0x2B5B6 | **Arb output clamp magnitude** (unsigned half). Used as ±512 symmetric clamp on arb output before limit_and_pack. V14 raised to 1024. | YES — V14 doubled this. |
| `0x71b4` | `0xC61B4` | `00 02` | **512** | `m_steer_torque_arbitration` @ 0x2A1F8, 0x2A20C, 0x2A212, 0x2A21C | **Arb output clamp in the arbitration function itself** (pre-pack). Paired with 0x71b2; both need raising in tandem. V14 raised to 1024. | YES — V14 doubled this. |
| `0x71d6` | `0xC61D6` | `00 00` | **0** | `s_motor_torque_rate_shaper` @ 0x43350 (ld.hu r16) | **Slew step** (incremental ramp step per cycle in the shaper). 0 = no ramp / instantaneous. Non-zero enables a ramp-up that reduces hard cutout severity on re-engage. Verified address and confirmed **0x0000** in current flash. | YES — raising to 14 (0x0E 0x00) proposed in Era 15 memory. |
| `0x71da` | `0xC61DA` | `44 04` | **1092** | `s_motor_torque_rate_shaper` @ 0x432B0; FUN_00043e44 @ 0x448F6 | **Slew scale** (divisor/multiplier in slew computation). Used alongside slew step to set the per-cycle ramp rate. | Caution — paired with slew step; adjust together. |
| `0x71dc` | `0xC61DC` | `00 78` | **30720** | `s_motor_torque_rate_shaper` @ 0x43268; FUN_00043e44 @ 0x4474A | **Accumulator clamp** in the rate shaper (±30720). Defines the maximum integrated value before hard clamp. Well above the 4762 governor; not the operative ceiling. | Low priority. |
| `0x7424` | `0xC6424` | `33 73` | **29491** | `s_motor_torque_rate_shaper` @ 0x43358 (ld.hu r18) | **Shaper deadband / dropout threshold.** ~90% of max. If accumulated shaper value falls below this on a transient zero, the output goes to zero (cold-start behavior). At 2× gain, the ratchet re-engages through this deadband from zero → slow ramp → the dropout feels like a power-steering loss. **Primary dropout severity lever.** | YES — lower to reduce dropout duration (e.g. 14746 = 50%). Safety note: too low and shaper won't zero on true disengage. |
| `0x7288` | `0xC6288` | `2c 01` | **300** | `m_steer_torque_arbitration` @ 0x29752, 0x2998E, 0x29A28 | **Re-engage init-wait** (count threshold; 300 cycles before re-engage ramp starts). | Moderate priority. |
| `0x728a` | `0xC628A` | `98 01` | **408** | `m_steer_torque_arbitration` @ 0x29866, 0x298AC | **Re-engage ramp ceiling** (408 — maximum value during ramp-up phase). | Moderate priority. |
| `0x74de` | `0xC64DE` | `11 64` | ramp_step=0x11=**17**, second byte=0x64=100 | `m_steer_torque_arbitration` @ 0x2976E, 0x2984E, 0x29862, 0x29874, 0x29896, 0x298A8, 0x298B0, 0x299AA (ld.bu — byte loads) | **Ramp step byte** (17 per cycle). Controls per-cycle increment during the arb re-engage ramp sequence. Higher = faster ramp back to full assist after dropout. | YES — can raise to reduce ratchet duration. |
| `0x7202` | `0xC6202` | `9a 12` | **4762** | FUN_0007b022 @ 0x7B06A (governor initializer) | **Governor constant** (max speed-scaled ceiling = 4762). Loaded once at init; runtime copy at gp-0x4f64 and mirror gp-0x448a. Well above the V14 ±1024 arb clamp; not binding for 2× scenario. | LOW priority at 2× — only needed for >9× push. |
| `0x7206` | `0xC6206` | `00 0c` | **3072** (= 0x0C00) | `m_motor_torque_governor` @ 0x45410 | **Governor voter step A.** One of two speed-interpolation step values used inside the governor for the adaptive binder. | Informational; not a short-term lever. |
| `0x7208` | `0xC6208` | `00 02` | **512** | `m_motor_torque_governor` @ 0x45416 | **Governor voter step B** (512). Second interpolation step. | Informational. |

### Shaper cluster

| tp-Offset | Abs Addr | Value | Code Load Site | Semantic |
|---|---|---|---|---|
| `0x71d4` | `0xC61D4` | `00 00` (=0) | `s_motor_torque_rate_shaper` @ 0x431C8; FUN_00043e44 @ 0x446C8, 0x446D6 | Shaper coefficient / init threshold (0 = no offset). |
| `0x71de` | `0xC61DE` | `00 08` (=2048) | `s_motor_torque_rate_shaper` @ 0x43360 | Shaper inner limit A. |
| `0x71e0` | `0xC61E0` | `00 1c` (=7168) | `s_motor_torque_rate_shaper` @ 0x4335C | Shaper inner limit B. |
| `0x71e2` | `0xC61E2` | `00 1c` (=7168) | `s_motor_torque_rate_shaper` @ 0x43388 | Shaper inner limit C. |
| `0x7420` | `0xC7420` | `cc b0 0e 00` — reads as u16 at 0xC7420 = 0xB0CC=45260 | `s_motor_torque_rate_shaper` @ 0x43398 | Shaper auxiliary threshold (used with deadband logic). |
| `0x7298` | `0xC7298` | bytes `74 b0 0e 00` → u16=0xB074=45172 | `s_motor_torque_rate_shaper` @ 0x43392 | Shaper LERP axis reference A. |
| `0x729a` | `0xC729A` | `76 b0 0e 00` → u16=0xB076=45174 | `s_motor_torque_rate_shaper` @ 0x43366 | Shaper LERP axis reference B. |
| `0x729c` | `0xC729C` | `76 b0 0e 00` (shared region) → u16=0xB076 | `s_motor_torque_rate_shaper` @ 0x4337E | Shaper LERP axis reference C. |
| `0x74a4` | `0xC74A4` | `ea b0 0e 00` → byte at 0xC74A4=0xEA=234 (ld.bu) | `s_motor_torque_rate_shaper` @ 0x4334C; FUN_00043e44 @ 0x44950 | Shaper mode selector byte A. |
| `0x74c9` | `0xC74C9` | bytes: `b0 0e 00 f2 b0 0e 00 f4` → byte at 0xC74C9=0xB0=176 | `s_motor_torque_rate_shaper` @ 0x4339E (ld.bu); FUN_00043e44 @ 0x44896 | Shaper mode selector byte B. |
| `0x74cd` | `0xC74CD` | byte at 0xC74CD (`f2 b0 0e 00 f4...`) = 0xF2=242 | `s_motor_torque_rate_shaper` @ 0x43372 (ld.bu) | Shaper mode selector byte C. |
| `0x74fe` | `0xC74FE` | `0e 00 00 b1` → byte at 0xC74FE=0x0E=14 | `s_motor_torque_rate_shaper` @ 0x4336C (ld.bu) | Shaper ramp parameter byte A. |
| `0x74ff` | `0xC74FF` | byte at 0xC74FF=0x00 | `s_motor_torque_rate_shaper` @ 0x43378 (ld.bu) | Shaper ramp parameter byte B. |

### LERP block 0x7a0a..0x7a44 (binary-search axis/value table)

Abs: 0xC7A0A–0xC7A46. 15 entries × 4 bytes (u16 value LE + u16 axis LE). Single code load site: `s_motor_torque_rate_shaper` @ 0x432F0 (`ld.hu 0x7a0a, tp, r8`).

Structure: `[u16 value][u16 axis_breakpoint]` — the shaper performs a binary search on the axis breakpoints to select the interpolated value (motor speed or angle LUT).

| Entry | Value (u16) | Axis breakpoint (u16) | Axis (decimal) |
|---|---|---|---|
| 0 | 13 | 0xB0F0 | 45296 |
| 1 | 13 | 0xC0C0 | 49344 |
| 2 | 13 | 0xC0D8 | 49368 |
| 3 | 13 | 0xC0F0 | 49392 |
| 4 | 13 | 0xD0C0 | 53440 |
| 5 | 13 | 0xD0D8 | 53464 |
| 6 | 13 | 0xD0F0 | 53488 |
| 7 | 13 | 0xE0C0 | 57536 |
| 8 | 13 | 0xE0D8 | 57560 |
| 9 | 13 | 0xE0F0 | 57584 |
| 10 | 13 | 0xF0C0 | 61632 |
| 11 | 13 | 0xF0D8 | 61656 |
| 12 | 13 | 0xF0F0 | 61680 |
| 13 | 13 | 0x00C0 | 192 (wraps u16; = 65536+192 in context) |
| 14 | 14 | 0x00D8 | 216 (wraps; = 65536+216 in context) |

All axis breakpoints have constant value=13 except the last two (value=14). This is a step function with a single transition at the upper end — the shaper uses it as a threshold table, not a continuous interpolation. Axis values appear to be motor electrical angle / speed codes spanning roughly 45296–61680 in the main range.

---

## Ranked Cal Levers — Preventing Transient Dropout/Ratchet While Keeping 2× LKAS

Ranked by expected impact on the dropout symptom, from highest to lowest.

| Rank | Addr | Current | Proposed Direction | Expected Effect | Safety Note |
|---|---|---|---|---|---|
| **1** | `0xC61D6` (tp+0x71d6) slew step | **0** | **Raise to ~14 (0x0E 0x00)** | Enables incremental ramp in the shaper instead of an instantaneous jump to zero. Re-engage after a transient plausibility event ramps up smoothly (14 units/cycle through the 29491 deadband) instead of the hard cutout. Directly addresses the "jerk" part of the EME symptom. | Per Era-15 memory this exact value was verified as the fix in the prior Accord analysis (the slew_limiter memory). At 0, the ramp is absent and any inhibit event causes a hard zero. Raising to 14 is low-risk: it only affects the ramp-up trajectory, not the maximum torque ceiling. Do NOT raise above ~50 — too fast a ramp is indistinguishable from a clamp bypass. |
| **2** | `0xC74DE` (tp+0x74de) ramp step byte | **17** | **Raise to ~25–30** | Faster per-cycle increment during the arb re-engage ramp sequence. Shortens the time spent at zero assist after a sensor plausibility dropout, reducing the "10-second heavy steering" window. | 8-bit byte field (max 255). Raising from 17 to ~25 = ~47% faster ramp. Do not raise above 50 — the ramp exists to validate sensor convergence before full assist resumes. Exceeding that range risks re-engaging before channels have truly re-converged. |
| **3** | `0xC6288` (tp+0x7288) re-engage init-wait | **300** | **Lower to ~150–200** | Reduces the mandatory wait before the re-engage ramp starts. Currently 300 cycles (~15ms @ 50Hz). Cutting to 150 halves the minimum dropout window. | Minimum wait exists to confirm channel stability. Do not lower below 100. Paired change with ramp step for coherent shortening. |
| **4** | `0xC628A` (tp+0x728a) ramp ceiling | **408** | **Raise to ~600–700** | Higher ceiling for the re-engage ramp allows the system to reach full-assist faster without spending cycles near zero. Most effective when combined with lever 2. | Must stay below the arb output clamp (1024 in V14) to avoid a step discontinuity at the top of the ramp. |
| **5** | `0xC6424` (tp+0x7424) shaper deadband | **29491** (~90%) | **Lower to ~20000–22000** (~65–70%) | Reduces the threshold that forces shaper output to zero during a transient. At 90%, any inter-sample dip to 90% of range triggers a full zero. At 65–70% the zero only fires on genuine large transients. Directly shortens the ratchet. | This deadband is a GENUINE FAULT DETECTOR for the shaper, not just a cosmetic clamp. Lowering too far risks missing a real motor fault. Recommended floor: 50% (= ~16384). Do NOT zero this out — it is load-bearing for no-assist-on-fault behavior. Safety: test at 70% first. |
| **6** | `0xC646C` (tp+0x746c) arb gain | **1782** (V14) | **Reduce to ~1300 (×1.46)** | Reduces the amplitude of the arb output that triggers the plausibility voltage ceiling in the torque sensor voter. Directly reduces EME frequency. Trade-off: less LKAS torque at the wheel. Consider as a fallback if levers 1–5 don't suppress the EME to an acceptable level. | This is the V14 value. Reverting all the way to 891 (stock) is the nuclear option / full revert. 1300 is a middle ground (~1.46× over stock). |

### Do NOT touch
- **Torque-sensor plausibility threshold** (`FUN_00041eec` voter, channels gp-0x6a44/40/3c/38/46, threshold ~0x7D00=32000): this is a **genuine column-torque-sensor fault detector**. Widening it risks masking a real dual-coil disagreement and is a safety regression. The Era-15 constellation note explicitly flags this as off-limits.
- **Governor `0xC6202` (4762)**: not binding at 2× (arb output ≤1024 << 4762). Only relevant for >9× scenarios.

### Summary: the dropout trigger
The `gp-0x4e65` assist-mode byte transitions to state 3 (TRANSITION) → state 1 (STARTING/RAMP) — NOT to state 4 (FAULT) — during the EME event. The trigger is NOT a latched DTC. It is the **torque-sensor dual-coil plausibility voter firing a transient inhibit** when driver hand-torque during a sharp low-speed turn pushes one or more ADC channels beyond the inter-channel delta threshold in `FUN_00041eec`. The re-initialization sequence (states 3→1→2 ramp cycle) runs through the shaper deadband (29491) from zero with slew step = 0 (instantaneous), causing the "snapping straight + heavy/jerky" symptom. At 2× arb gain, the pre-existing normally-imperceptible inhibit becomes the violent EME. The gp-0x4e65 state machine self-recovers within ~10s as channels reconverge — exactly matching the reported symptom.
