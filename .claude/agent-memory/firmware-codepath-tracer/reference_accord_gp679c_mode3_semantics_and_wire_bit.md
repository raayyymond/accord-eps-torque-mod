---
name: reference_accord_gp679c_mode3_semantics_and_wire_bit
description: gp-0x679c IS the state byte of dispatcher FUN_000413ae (0x413ba ld.bu -0x679c; the "gp-0x67DC" claim is wrong). Mode 3 = gp-0x67fe==2 AND absolute baseline gp+0x6470 valid; NOT sticky (->4 when 67fe!=2, ->1 on -0x8000). 0x14A byte4 bit1 (gp-0x679b) is a live wire flag for mode-3 & 67fe==2: 7 in 2,316,807 healthy frames / 91 routes. gp-0x67fe has 5 writers (FUN_0003e760 @0x3e770 too).
metadata:
  type: reference
---

# `gp-0x679c` mode 3, `gp-0x67fe`, and the wire bit that measures both (2026-09-30)

**Setter [EVIDENCE].** `FUN_00040d38` (`0x40d44 st.b r6,-0x679c[gp]`, shadow `gp-0x4c35`) has 17
callers, all in the handlers of `FUN_000413ae`. The dispatcher's own state read at `0x413ba` is
`ld.bu -0x679c[gp]` (raw scan). The older memory's "gp-0x67DC" contradicts its own displacement,
−26524 = −0x679C.

**Mode-3 semantics [EVIDENCE, all 9 handlers decompiled].** State 3 (`FUN_000410da`) holds only while
`gp-0x67fe == 2`. It goes to 4 otherwise, and to 1 if `gp+0x6470 == −0x8000`. Entry: from 0 directly
(`gp-0x67fe == 2` and baseline ∉ {−0x8000, 0x7FFF}), from 2, from 4 (decider(4)), and from 7/8 (latches).
The baseline `gp+0x6470` is set in `FUN_0003c7fc` (|est − `gp-0x6cc4`| ≤ 4825) and appears at `0x8B144`
in a record table. **[BELIEF]** that it is data-flash backed. In FUN_00040a50, mode 3 packs
`−gp-0x6a00` into 0x14A. Otherwise it packs the relative accumulator `gp-0x6ce0`, clamped to ±15120.
The first mode-3 pass only latches `gp-0x35bc`.

**`gp-0x67fe` [EVIDENCE].** 5 writers: 4 in `FUN_0003bd7c` (FOC mode 5 → 2, mode 4 → 1, gate fail →
0 plus a sticky latch `gp-0x6845`) and **`FUN_0003e760` @`0x3e770`**. The latter fires when the
`gp-0x676f` bitmask is nonzero for `0xC62A2` = 100 ticks. Outside {1,2}, `gp-0x6a00` and `gp-0x69ca`
both become 0.

**Wire flag [EVIDENCE].** 0x14A byte 4 bit 1 = `gp-0x679b` = 1 only on the latched mode-3 path with
`gp-0x67fe == 2` and |`gp-0x6a00`| ≤ 10000. Measured: bits[2:0] = 7 in **2,316,807 frames, 395
segments, 91 routes**. The exceptions are the V75 hard fault (route 0x5e) and one cold-start frame
(route 0x75: `b4 0x65, angle 0` → `0x67, angle −93` ten ms later, a full-angle step at mode-3 entry).
⇒ **`gp-0x67fe` is 2 during driving, not 1.** The V31P "==1 in 100 % of frames" claim is refuted.
Method (not committed; rebuild it in about 30 lines): `rlog-tools/lib/rlog_parse.read_messages`, `can`
events, `src == 1` (bus 0 carries none), `address == 0x14A`, then count `dat[4] & 7` and its transitions.

Related: [[reference_accord_gp6a00_angle_is_a_100hz_hold_inputs_fresh_at_1khz]],
[[reference-accord-engage-sm-full-dispatcher-and-trump-exits]] (stale on the state byte),
[[reference_accord_fun456a4_gate_no_hysteresis_and_index_identity]] (says 4 writers; there are 5).
