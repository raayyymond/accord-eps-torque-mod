---
name: reference-accord-demand-aggregator-pipeline
description: "Accord TVA torque/assist DEMAND AGGREGATOR, Ghidra-traced 2026-05-25: 10 producers (slots 0-9) each gate+clamp their demand-vector entry (RAM 0xFEDF1468..15A2) and write one slot via shared distributor FUN_00025c32 -> per-slot banks -> mixer FUN_00026c80 (state-route + cross-slot MAX/SUM + clamp) -> 0xFEDF1502 -> shaper FUN_00042af8 (±0x2000) -> demand struct 0xFEDF16E0 -> serializer FUN_000564ce -> CSIG0. Sharpened GAP 2: principal cmd routes to a SERIAL FRAME, no st to gp-0x2bf0/-0x2be0 q-ref found, so on-chip FOC handoff is NOT proven."
metadata:
  node_type: memory
  type: reference
---

> **⚠⚠ UPDATE 2026-05-26 (late) — GAP 2 resolved + the post-shaper governor chain mapped.** (1) The shaper output `0xFEDF1468` (`gp-0x6b98`) IS read by the on-chip FOC functions (FUN_000370b6/0x3b8f6/0x56420/0x7c4f2, 45 readers total) — so the mixer→shaper→FOC handoff IS corroborated; GAP 2's "not corroborated" is closed in the affirmative. (2) There is a SECOND mixer lane that reconverges at the shaper: mode-0 sources (incl. the LKAS slot-1 arb torque) route `gp-0x62b0`→`gp-0x3d88`→`gp-0x6b4c`→FUN_0003aa2c→`gp-0x6b94`→FUN_0004503c→`gp-0x6ace`→FUN_000456a4→`gp-0x6acc`, and the shaper FUN_00042af8 reads BOTH `gp-0x6acc` (0x431c4) and `gp-0x6afe` (0x43ae0). (3) The delivered high-end binder is the runtime governor `gp-0x4f64` = cal `tp+0x7202`=`0xC6202`=4762 (applied in FUN_0004503c + the shaper), NOT the ±0x2000 static. Full record: [[reference-accord-lkas-delivery-and-governor]].
>
> **⚠ tp CORRECTION 2026-05-26:** every `tp+0xNNNN` here resolves at **`tp = 0xBF000`** (application base, set @`0x140ce`), NOT `0xF8000` — e.g. the mixer state-4 gain `tp+0x746a` = `0xC646A` (programmed), and the slot-1 LKAS arbitration applies output gain `tp+0x746c`=`0xC646C`=**891** + clamp `tp+0x71b4`=`0xC61B4`=**512** before this aggregator. See [[reference-accord-databin-tp-base]] (corrected) — there is no absent partition. The pipeline topology below (10 producers → distributor `0x25c32` → mixer `0x26c80` → shaper `0x42af8` ±0x2000 → serializer) is UNAFFECTED and correct.

The 2020 Accord EPS (`39990-TVA-A160`, V850, code.bin port 8193) turns LKAS steering torque into a motor command through a **multi-producer demand aggregator**, not a single passthrough. Traced 2026-05-25; every hop instruction- or decompile-verified. Builds on [[reference-accord-lkas-torque-path]] (the LKAS slot is one of ten) and [[reference-accord-gp-base-fedf8000]] (gp=0xFEDF8000 used for every abs address below). CALL xrefs resolve in this project now (auto-analysis re-run since the doc's §0.1 "CALL xrefs return 0").

**The 10 producers (slot index = struct +0). Each: read own demand-vector entry → identical per-slot enable/transition/fault state machine (state 0-5 into +1) → clamp → `FUN_00025c32`.**

| slot | producer | source var | lane written |
|---|---|---|---|
| 0 | FUN_0002e52e | 0xFEDF14E6 | +4 |
| **1** | **FUN_0002b422 (LKAS / STEER_TORQUE)** | **0xFEDF14C4** (arbitration out, `FUN_00028ea6`) | **+4** |
| 2 | FUN_0003405a | 0xFEDF148A & 0xFEDF1488 (dual) | +2 AND +4 |
| 3 | FUN_0002c246 | interp tbl 0xC7090[idx] | +4 |
| 4 | FUN_00023ad2 | 0xFEDF1498 | +4 |
| 5 | FUN_00023fe2 | 0xFEDF1470 | +4 |
| 6 | FUN_0003aff4 | float-interp computed term | +8 |
| 7 | FUN_0003a8a8 | (idle/clear — all lanes 0) | none |
| 8 | FUN_0002caa2 | 0xFEDF14EE | +4 |
| 9 | FUN_000339cc | 0xFEDF1494 + accumulator 0xFEDF44B0 | +4 |

Two scheduler task contexts (both dispatched via fn-ptr table, no direct callers): **`0x2214a`** runs slots 1,6,7,8,9 + arbitration `0x28ea6` + pack `0x2b422` + mixer `0x26c80`; **`FUN_00022ca0`** runs slots 0,2,3,4,5.

**DISTRIBUTOR `FUN_00025c32` (shared, 10 callers) [V instr].** Clamps 4 independent command lanes — **+2:±0x4000, +4:±0x2800, +6:±0x384, +8:±0x4e20** — plus 3 blend gains +a/+c/+e (≤`0x400`=unity, Q10). Index byte +0 (≤0xa) selects the slot; fans each clamped lane into per-slot banks: **primary `gp-0x62xx`** (+2=`gp-0x62e0`=0xFEDF1D20, +4=`gp-0x62f8`, +6=`gp-0x6274`, +8=`gp-0x633c`) **+ ASIL mirror `gp-0x4bxx`**. Lane usage across all 10: **+4 = shared by 7 slots** (the torque-demand lane), **+2 only slot 2**, **+8 only slot 6**, **+6 never used (dead)**, slot 7 all-zero.

**MIXER `FUN_00026c80` [V disasm; fails to decompile — TAUJ0 type bug].** Loops slots 0-10: per-slot state-routed staging (state 1-7; state 4 applies gain `mul tp+0x746a; sar 0xe; clamp ±0x2800`) → cross-slot running **MAX** on some lanes, **SUM** on others → accumulators `gp-0x3d70..3d98` → final clamps **±0x4e20 / ±0xe10 / ±0x2800 / ±0x6400**, each ASIL-mirrored via `FUN_0006b9fa`. Principal output: `mov r26,r6; sxh; jarl FUN_00042ac6`.

**Forward spine [V]:**
`FUN_00042ac6` (range-check ±0x2800 else sentinel 0x7fff) → **`0xFEDF1502`** (gp-0x6afe; the mixed torque cmd). `0xFEDF1502` has exactly **1 writer (0x42ac6) + 1 reader (0x42af8)** — verified by `search_instructions -0x6afe`.
→ **SHAPER `FUN_00042af8`**: blends 0xFEDF1502 with companion terms (e.g. 0xFEDF309C), sign-consistency checks, **clamp ±0x2000**, ASIL state (writes feedback 0xFEDF1468 read by slot 6); emits via `FUN_0004613e`.
→ `FUN_0004613e`: packs **demand struct 0xFEDF16E0/16E4/16E6/16E8/16EA** (tag id `0x38c7`), then `FUN_00016de6(0x1c,...)`.
→ **SERIALIZER `FUN_000564ce`** (caller `FUN_00056654` ← `FUN_00047f28`): big-endian byte-packs the struct into a TX frame at `param+0xA..+0x13`.
→ **dispatch `FUN_00016de6`** (ids 0x2a/0x1c): fails to decompile on a **`CSIG0` clocked-serial register type** → a serial/message path.

**SHARPENED GAP 2 — flag, do NOT flatten.** The principal mixer output flows into a **serialized message frame**, NOT a direct write to the on-chip FOC q/d setpoints. Whole-image search found **no `st` to `gp-0x2bf0`/`-0x2be0`** (the q/d setpoint slots named in [[reference-accord-lkas-torque-path]] GAP 2). So the assumption "mixer output → on-chip FOC q-reference" is **not corroborated**. Three unresolved possibilities: (a) current loop / power stage partly off-die over the CSIG0 link (frame = command); (b) real q-ref written via a computed base register, invisible to a gp-offset search; (c) the `gp-0x2bf0` offsets are approximate. The on-chip FOC `FUN_00071272`→TSG20 PWM (`FUN_0006c5ce`, CMPU/V/W 0xFFFFCCB0/B4/B8) IS verified as the motor drive ([[reference-accord-lkas-torque-path]] ⑤); reconciling that with this serial-frame path is the open question. Per operator 2026-05-25: not closing this now.

**The arbitration stage that feeds slot 1 is detailed in [[reference-accord-arbitration-limit-family]]** (2026-05-25): its setpoint limit is a mode/gear-indexed FAMILY of LERP curves at 0xE4xxx (cb844 hard limit is gear-invariant; c9a88 shaping curve varies by gear), and the full x=4096 clamp waterfall ends at the shaper's ±0x2000=8192.

Figures: `analysis-2020accord/demand_aggregator_pipeline.png` + the v2 `accord_demand_pipeline_v2.png` (adds per-slot state machine, cross-slot MAX/SUM, final clamps, companion terms); `torque_transform_x4096.png` (x=4096 stage-by-stage; NOTE its panel C used 0xC6534 which arbitration does NOT read — superseded by `accord_bottleneck_and_limit_family.png` and `accord_plotC_by_mode.png`). Method per [[feedback-rigorous-validation]] (verified vs inferred kept distinct).
