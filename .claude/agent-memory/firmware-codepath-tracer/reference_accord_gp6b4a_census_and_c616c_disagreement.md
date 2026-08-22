---
name: reference_accord_gp6b4a_census_and_c616c_disagreement
description: Full raw-Python-LE census of gp-0x6b4a (11 sites, 6 functions; producer is FUN_00026c80, the same LKAS-lane rate limiter that writes gp-0x6b4c) and cal(0xC616C) (3 readers, all in FUN_00033d10, stock=0). DISAGREEMENT WITH A CROSS-AGENT CLAIM: cal(0xC616C) is NOT the gate on gp-0x6b4a's addition inside FUN_000352b4 -- fresh disassembly of the actual cited address (0x354f6-0x35504) shows a hardcoded-constant unsigned-range test on gp-0x6b4a's own magnitude (constants 0x6400/0xC801), not a calibration-cell read. The two censuses have zero address overlap.
metadata:
  type: reference
---

# gp-0x6b4a / cal(0xC616C) census, and a disagreement with a relayed cross-agent claim (2026-08-22)

Dispatched as the independent byte-scan half of a dual-method check (Ghidra-decompile half owned by a
sibling agent "compensator"), on the operator's reframe: *"structurally this is all related to LKAS
unexpectedly feeding into the driver torque signal."* Method: raw Python LE scan over the whole 1MB
`code.bin`, both gp-relative encodings, both the plain and the `ld.hu`/`ld.w` `hw2=disp|1`-biased
4-byte forms; every candidate individually adjudicated via `disassemble_bytes(dry_run=true)`, not
hand-decoded or taken from `search_instructions` alone.

## gp-0x6b4a: 11 sites, 6 functions, zero false positives this time
| addr | function | instr |
|---|---|---|
| `0x27776` | `FUN_00026c80` | `ld.h -0x6b4a,gp,r15` |
| `0x27784` | `FUN_00026c80` | `st.h r6,-0x6b4a,gp` **write** |
| `0x2779c` | `FUN_00026c80` | `st.h r6,-0x6b4a,gp` **write** |
| `0x277aa` | `FUN_00026c80` | `st.h r23,-0x6b4a,gp` **write** |
| `0x28548` | `FUN_00027b0a` | `ld.h -0x6b4a,gp,r9` |
| `0x28aba` | `FUN_00027b0a` | `ld.h -0x6b4a,gp,r11` |
| `0x28aee` | `FUN_00027b0a` | `movea -0x6b4a,gp,r7` -- address-of, passed to `FUN_0004613e(id,ptr...)`, the standard shadow/plausibility helper seen throughout this codebase (e.g. inside `FUN_0004503c`'s housekeeping). Reads+writes THROUGH the pointer -- invisible to a displacement scan, flagged not resolved. |
| `0x354f6` | `FUN_000352b4` | `ld.h -0x6b4a,gp,r12` -- the cited injection site |
| `0x37fea` | `FUN_00037fe6` | `ld.h -0x6b4a,gp,r15` |
| `0x42bf6` | `FUN_00042af8` | `ld.h -0x6b4a,gp,r7` |
| `0x43f20` | `FUN_00043e44` | `ld.h -0x6b4a,gp,r6` |

**Producer: `FUN_00026c80` (3 writers, sole writer function).** This is the SAME function already on
this kit's record as the LKAS-lane rate limiter writing `gp-0x6b4c` (`build_v41_tva.py` CHANGE 1: *"the
LKAS-LANE-ONLY per-cycle rate limiter, in FUN_00026c80, which writes gp-0x6b4c -- the LKAS lane the
aggregator reads at 0x3AA3E"*). **`gp-0x6b4a` is written by the identical function that shapes the LKAS
lane** -- structural support (from the producer side, not yet the value/formula) for an LKAS-domain
origin.

**Readers, beyond the cited `FUN_000352b4` site:** `FUN_00042af8` and `FUN_00043e44` both ALSO read
`gp-0x4f64` (see [[reference_accord_gp4f64_governor_ceiling_chain_and_v41_force_proof]]) --
`FUN_00043e44` is the confirmed DTC-0x3f1b composite-anomaly monitor, so `gp-0x6b4a` is one more
additive term feeding that score alongside the governor value.

## The actual gate at 0x354f6, from fresh disassembly -- NOT cal(0xC616C)
```
0x354e0  ld.hu 0x7200,tp,r6         ; cal(0xC6200) -- matches the already-established "raw=clamp(gp_0x4f60,+/-cal(0xC6200))"
0x354e4  subr r0,r6 / sxh r6        ; -cal(0xC6200)
0x354e8-0x354f4  clamps r16 (gp-0x4f60-derived) into r14, floor at -cal(0xC6200)
0x354f6  ld.h  -0x6b4a,gp,r12       ; gp-0x6b4a loaded immediately after the clamp settles
0x354fa  ori   0xc801,r0,r9
0x354fe  addi  0x6400,r12,r11       ; r11 = gp-0x6b4a + 0x6400
0x35502  cmp   r9,r11               ; flags = r11 - 0xC801
0x35504  cmovnc 0x0,r12,r15         ; UNSIGNED range test on gp-0x6b4a's OWN magnitude -> r15 = gated(gp-0x6b4a)
0x35508  add   r14,r15              ; x = gated(gp-0x6b4a) + clamped-raw
0x3550a-0x3551c  symmetric clamp of the sum into [-0x6400,+0x6400]
```
**No calibration cell is read anywhere in this window.** The gate is a hardcoded-constant unsigned-range
test (`+0x6400` then compare against `0xC801`) on `gp-0x6b4a` itself. I have NOT re-verified the exact
`cmovnc` polarity by execution (the way `FUN_00049a90` was settled) -- flagged BELIEF-on-polarity,
EVIDENCE-on-structure (no cal cell present, full stop).

**🛑🛑 DISAGREEMENT, reported per standing instruction:** a relayed cross-agent claim states
`cal(0xC616C)=0` gates this exact addition, "currently DEAD." **My independent, complete census of
`cal(0xC616C)` finds exactly 3 readers, ALL inside a completely different function, `FUN_00033d10`
(`0x33fec`/`0x34000`/`0x34010`), which never touches `gp-0x6b4a` anywhere in its body** (it reads the
cal, sign-matches it against the raw torque sensor `gp-0x4f60`, and writes `gp-0x6b76`/`gp-0x6b78` --
unrelated cells). **Zero address overlap between the two censuses.** Either the cited address/site is
wrong, or there's a different gate elsewhere I haven't found that also involves this cal -- not
resolved this session, reported for reconciliation against the sibling agent's decompile trace.

## cal(0xC616C) -- full independent census
Halfword (`ld.hu`), stock value = **0** (u16 and s16 agree). 3 readers as above. 9 raw candidates from
the scan (both bias forms); the other 6 individually rejected: 2 are bytes inside unrelated 32-bit
immediate loads (`mov 0xb716c,r14` / `mov 0xc716c,ep` -- note the second is `0xC716C`, one hex digit off
from the target `0xC616C`, a coincidental near-miss chased down and confirmed unrelated); 2 are
non-instructions at that byte alignment; 2 decode to `st.h r14,-0x9bea,r0` -- base register **r0**, not
`tp`. **Not part of any mode-indexed table** (no `gp+0x63fd`-style pointer-array lookup near any of the
3 real sites) -- a flat scalar, so there is no mode-24/26-vs-10 ambiguity to have here, unlike the r24/r26
gain tables.

## Related
[[reference_accord_gp4f64_governor_ceiling_chain_and_v41_force_proof]] -- the governor chain this
producer (`FUN_00026c80`) and these two DTC-adjacent readers (`FUN_00042af8`/`FUN_00043e44`) connect to.
