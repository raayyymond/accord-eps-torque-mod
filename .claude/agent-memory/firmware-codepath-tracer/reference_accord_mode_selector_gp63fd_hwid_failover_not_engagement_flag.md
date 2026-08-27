---
name: reference_accord_mode_selector_gp63fd_hwid_failover_not_engagement_flag
description: 🛑 CORRECTED 2026-08-05 -- do not cite the original "not the large claim" verdict without this correction. Structural chain confirmed (5 real writers in FUN_00042746, all write gp+0x63fd, which is the exact same byte FUN_00034350 reads -- byte-verified, my original "0x63fc/0x63fd are different bytes" claim was WRONG). But team-lead's telemetry (V72 bit4, |gp-0x6bd0|>=64, 0/87940 frames incl. 0/34275 above 35km/h) EXCLUDES mode 10/11 entirely -- their FactorC/E values give a 389-count minimum unconditionally, which would fire on 100% of frames. Mode 0 (the .bss boot default) fits every measured cell; mode 10/11 fits none. My own indirect argument (V38/V44/V47 flashed+drove differently => mode is live) was backwards: V47 is the ONE build that tested the mode-indexed lane specifically, and its near-null on-car result ("marginally quieter at 5mph, no effect in motion") is what mode!=10 predicts, not evidence for mode==10. Settled by a V73 probe rung reading gp+0x63fd directly, not by further static analysis.
metadata:
  type: reference
---

# `gp+0x63fd` mode selector: structural chain confirmed, but telemetry says it isn't reaching 10/11 (2026-08-05)

Team-lead dispatched two agents independently (this one, and sibling `F3-task-rates`, later also `F7`)
across three rounds to determine what value the base-assist damper's mode selector (`gp+0x63fd`,
`FUN_00034350`'s `FactorB/C/D/E` index) holds during ordinary driving. **Net result: the STRUCTURE is
now fully mapped and cross-verified, but the DATA contradicts the structural prediction, and the
question is left to a live probe, not further static work.**

## Round 1 — the structural chain, confirmed correct

`FUN_00042746` (5 real writers, all inside it, all targeting `gp+0x63fd`) is a static HW-ID-keyed
sensor-failover reselector:
```c
cVar8 = gp-0x67e2;              // "fault-role" selector, values 0/1/2
if (gp-0x67f6 == 0) {           // branch A
    if (cVar8==1) { idx=FUN_00057f8e(); gp+0x63fd = e012[idx]; }
    else if (cVar8==2)          { idx=FUN_00057f8e(); gp+0x63fd = e013[idx]; }
} else if (gp-0x67f6 == 1) {    // branch B
    if (cVar8==1)                { idx=FUN_00057f8e(); gp+0x63fd = e014[idx]; }
    else if (cVar8==2)            { idx=FUN_00057f8e(); gp+0x63fd = e015[idx]; }
}
```
`FUN_00057f8e` is a static 5-byte HW-ID match against a ROM table at `0xCD000` (stride `0x24`), fixed
per ECU, not driving-state-dependent. For this car (record 2, "TVAA1"), byte-read fresh:
`e012[2]=10, e013[2]=10, e014[2]=11, e015[2]=11` — **every reachable branch writes 10 or 11, never
anything else.** This matches `builds/v18_v49/build_v44_tva.py`'s own pre-existing documentation (written months
before this session) exactly — three independent sources agree (this session's decompile, this
session's byte read, that build script).

`FUN_00042746`'s sole caller is `FUN_00022ca0`, the live 100Hz decider/torque-fuser/mixer task, not a
boot-only call. `gp+0x63fd` is `.bss` (positive gp offset, outside `.data`) and boots to 0.

## 🛑 CORRECTION — `gp+0x63fc` and `gp+0x63fd` are the SAME byte, not different ones

My original round-1 report claimed `FUN_00034350` reads `0x63fd` while a diagnostic snapshot routine
(`FUN_000508e8`) reads the "different, adjacent" byte `0x63fc`. **Team-lead independently disassembled
both the read and write sites and found they use the identical displacement `0x63fd`** — I re-verified
this myself:
```
0x034470  ld.bu 0x63fd, gp, r15    bytes a47ffd63   -- FUN_00034350's mode read
0x0426ae  st.b  r8, 0x63fd, gp     bytes 4447fd63   -- FUN_00042746's write
```
Byte-for-byte match, independently confirmed by both of us. The damper reads exactly the byte
`FUN_00042746` writes. My "different bytes" claim was wrong (though the reclassification of
`0x050928`/`0x050AD8` as reads, not writes, still stands — team-lead accepted that correction).

## 🛑 THE DECISIVE PART — telemetry excludes mode 10/11 entirely

On V72's own image, modes 10/11 give `FactorC = [430,430,430,877]` (so `C >= 430` at every speed —
below `X[0]=2240` it clamps to `Y[0]=430`, not 0) and `FactorE = [927,927,927,927]` (flat, `E=927` at
every rate). Therefore `|gp-0x6bd0| = 1024 * (430/1024) * (927/1024) = 389` **unconditionally, on every
frame, at every speed and rate.** V72's probe rung `bit4 = |gp-0x6bd0| >= 64` would fire on 100% of
frames if the car were in mode 10 or 11. **It fired on 0 of 87,940 frames, including 0 of 34,275 above
35 km/h** (where the pre-registered rung design expected it to fire regardless of what V72 changed).
**There is no amplitude/speed/rate regime in which mode 10/11 is silent — the car was not in mode 10 or
11 during that route.** Mode 0 (the `.bss` boot default, `FactorC Y[0]=0`, `FactorE Y[0]=0`) is
consistent with every cell of the measurement instead.

## My own indirect argument was backwards — corrected

I had cited "V38/V44/V47 all flashed and drove differently, therefore the runtime mode must be live at
10/11" as tie-breaking evidence. Team-lead's correction, accepted: **V47 is the ONE build that actually
tested the mode-10/11-indexed FactorC/E lane specifically**, and its on-car result was *"marginally
quieter at 5 mph, no effect in motion"* — essentially a null. **That is exactly what mode != 10 would
predict**, not evidence the mode is live. V38's and V44's other on-car differences came from levers that
are NOT mode-indexed (`gain_A`, the rate lanes, the ratchet-fix cave edit) and carry no information about
which mode is active. The lineage evidence is neutral-to-against my original reading, not for it.

## Where this landed — not resolved statically, by design

Neither agent could settle whether `FUN_00042746`'s confirm-sequence (gated on an engagement-transition
edge + settled ramp + low-torque condition, structurally traced, never simulated) actually fires
promptly during real driving. **V73 spends one probe field reading `gp+0x63fd` directly (4 bits, 0-15)**
— settles it on one drive regardless of which reading was right:
- Reads 10/11 ⇒ the structural chain was live, V72's edits took effect, and the `bit4` null needs a
  fifth explanation.
- Reads 0 (or 4/5/12) ⇒ the confirm-sequence is not firing as traced, V72's FactorC/E edits went to
  records the car never read, and the fix is to additionally write the proven values into the LIVE
  mode's own records — an addition, not a re-tune of V72.

**Durable fact worth keeping regardless of the probe result**: `builds/v18_v49/build_v44_tva.py` documented the 10/11
failover pair and patched both tables months ago — the kit *knew* about the failover mechanism and
still nobody had checked the pre-confirm-sequence boot window until this round.

## Related
[[reference_accord_gp6bd0_seed_ruled_out_and_engagement_gates_found]] -- the parallel seed-closure
finding from the same dispatch round, same overall V72/V73 damper-null investigation.
[[reference_accord_tva_hw_id_provenance]] -- the HW-ID provenance chain (`gp+0x6408..640C`), confirms
the ID-string-edit hypothesis for THIS mechanism is separately ruled out (UDS-write-only, not
string-parsed) -- orthogonal to the boot-window question this file resolves.
