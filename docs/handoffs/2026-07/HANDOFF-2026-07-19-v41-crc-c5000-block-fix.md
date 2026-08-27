> # 🛑 SUPERSEDED — DO NOT USE AS A BUILD REFERENCE
>
> This describes an **earlier, discarded V41** (V40 + a 4-byte CRC repair). That artifact no longer
> exists and was never flashed. **The current V41 is a different build entirely** — see
> `handoffs/2026-07/HANDOFF-2026-07-20-v41-ratecap-flat.md`.
>
> Its central premise is also **refuted**: the stale `0xC5FFC` CRC has no consumer anywhere in the
> firmware. Retained only as the record of that investigation and its retraction. The findings are
> carried forward correctly in `handoffs/2026-07/HANDOFF-2026-07-20-session-v40-fault-investigation.md`.

# HANDOFF - 2026-07-19 - V41: the 0xC5000 block CRC, and a root cause I did NOT establish

**Platform:** 2020 Accord `39990-TVA-A160`, V850E2. **Baseline:** exact on-car V38 plain image.
**Status:** V41 is BUILT and statically VERIFIED, **NOT FLASHED**. No CAN, UDS, or flash operation occurred.
**Relationship to V40:** V41 is V40 plus **exactly four bytes**. Both functional changes preserved
byte-for-byte.

> 🛑 **READ FIRST: V41 IS NOT A DEMONSTRATED FIX.** It repairs a real defect that is worth repairing on
> its own merits, but the causal link between that defect and V40's ignition fault **was investigated
> and does not hold up**. An earlier draft of this document, plus a `CLAUDE.md` edit and a memory,
> claimed a confident root cause. All three are retracted and corrected. Treat flashing V41 as an
> **experiment**, not a repair.

## On-car input

V40 was FLASHED. The car came up with an **immediate EPS warning lamp and power steering completely
disabled**, at ignition, before any steering input.

## What is fact

`[0xC5000, 0xC5FFC)` is a self-describing block — trailer `0xC5FF8`=`0x00C5` (start_page),
`0xC5FFA`=`0x0001` (num_pages) — carrying a CRC32 at `0xC5FFC` that is **correct in stock, V31, V37
and V38**. Something maintains it. V40 wrote 32 bytes into it (cap tables at `0xC5030`, `0xC521A`,
`0xC5232`) and never recomputed:

| Image | `crc32[0xC5000,0xC5FFC)` | stored `@0xC5FFC` | |
|---|---|---|---|
| V38 | `0x09C1200B` | `0x09C1200B` | OK |
| V40 | `0x15207EA4` | `0x09C1200B` | **STALE** |
| V41 | `0x15207EA4` | `0x15207EA4` | OK |

V40 is the only image in this kit's history with a bad CRC there, and the only one that faults at
ignition. **That correlation, on a population of one, is what motivated this build — and it is not a
mechanism.**

## What is NOT fact — the hypothesis that failed

I claimed the kit's `verify_bootloader_crc.walk()` contained a *bogus* "bridge at `0xC6000` → main",
that the real chain was 50 blocks, and that the ECU therefore failed this block at startup. **Wrong.**

A subagent trace of `code.bin` — which I then byte-verified myself — shows `FUN_0000b006` genuinely
contains the bridge:

```c
if (puVar3 == &LAB_000c6000) { puVar3 = &DAT_00013000; puVar2 = &DAT_000b1ffc; }
else { puVar2 = ...(puVar3-6)*0x1000-4; puVar3 = ...(puVar3-8)<<0xc; }
```

```text
0xB070 movea 0x6000 / 0xB072 movhi 0x000C  -> the literal 0xC6000 compared against
0xB07A        0x3000 / 0xB07C        0x0001  -> 0x13000
0xB080        0x1FFC / 0xB082        0x000B  -> 0xB1FFC
```

Consequences, all against my hypothesis:

- The bootloader **really does skip** `[0xC5000,0xC5FFC)`. The kit's Python walker was **faithful**.
- `FUN_0000b006` is reachable **only through a UDS diagnostic session** (`FUN_0000cc4e` →
  `FUN_0000b0ae` → `FUN_0000b006`), and its failure path sets `DAT_fedf20ba = 0x72` — a **UDS negative
  response code**. No `FUN_00016de6` (DTC setter), no `FUN_0001611e`, no `FUN_00045608` (motor-off).
  It **cannot** raise an ignition-time lamp even when it fails.
- V40 therefore passes the bootloader walk **49/49**, and the flasher's dependency check would have
  reported **clean**. (I had predicted a `[warn]` in the V40 flash log. That prediction is also
  retracted — `eps-update-tva.py:541` only warns on non-zero status, but the status would have been
  zero.)

**A stale `0xC5FFC` has no known consumer.**

## Still open

1. **What maintains that CRC, and what checks it?** A block skipped by the bootloader would not
   normally carry a correct, maintained CRC across four independent builds. That asymmetry is
   unexplained and is the strongest remaining thread. A plausible reading: the block holds
   per-vehicle/end-of-line calibration that the bootloader must *not* check at flash time (its content
   legitimately varies per car), but which the **application** validates at startup. Unproven.
2. **What actually caused V40's ignition fault.** Candidates not excluded:
   - An **application-level** integrity or calibration-plausibility check. A flat cap table with
     **zeroed Q13 slopes** is exactly the shape a monotonicity check, or an inverse/reciprocal
     interpolation, would choke on — and a divide-by-zero would produce an immediate hard fault.
   - Anything reached by the `65535` slew cals (`0xC6206`/`0xC6208`).
3. Everything in V40's own "Open / not established" list carries over unchanged.

Two subagents are still running: one searching the application range `[0x13000,0xBF000)` for a startup
integrity/plausibility check, one auditing whether V41 can fault for a reason unrelated to the CRC.
**Fold their results in before flashing.**

## What V41 changes, and why it is still worth having

Four bytes at `0xC5FFC`, restoring the block's internal consistency. Rationale is now hygiene, not
repair: it costs nothing, it is unambiguously correct, and it makes V41 a **cleaner experiment** — if
V41 faults identically, the CRC is definitively cleared and the finger points at the table content
itself, which is exactly the next thing to test.

`lib/verify_bootloader_crc.py` now exposes both walks, with the bridge restored and documented so it is
not "fixed" a third time:

```text
walk()             faithful bootloader replay, 49 blocks, bridge included -> predicts UDS NRC 0x72
walk_all_blocks()  stored linked list, 50 blocks -> HYGIENE check only, not a BL replay
```

```text
image     BL walk (49)      full chain (50)
V31       49 blk 0 fail     50 blk 0 fail
V37       49 blk 0 fail     50 blk 0 fail
V38       49 blk 0 fail     50 blk 0 fail
V40       49 blk 0 fail     50 blk 1 fail   <-- [0x0C5000,0x0C5FFC)
V41       49 blk 0 fail     50 blk 0 fail
```

## Artifact

```text
../accord-firmware/flashing-2020accord/rwd/39990-TVA,A160-V41-LKAS-4x-V38base-slew-off-ratecap-flat5325-crcfixC5FFC-0x13000-0x100000.rwd
```

| Artifact | SHA-256 |
|---|---|
| V41 RWD | `6e771042901c2af0862241fbec5ec28b3785f441d82271258cf041a9a269d7b2` |
| `_v41_plain_image.bin` | `71f58e7b5b5f0fe8c7ade8149e0bcee33b6b449cd3da2485ff3013b85bcf712d` |
| `_v38_plain_image.bin` baseline | `a7391972a9db51d0e7699956755eb1d1e6b1dcc2d7d3aa0f470065fd4b14afa8` |

Builder: `analysis-2020accord/builds/v18_v49/build_v41_tva.py`. **CAL-ONLY — zero code edits, zero caves.**

## Edits — 44 bytes in 6 runs (V40's 40 + 4)

| Address | Stock | V41 | What |
|---|---|---|---|
| `0xC6206` | 512 | 65535 | slew fast step (`tp+0x7206`) — vibration fix, preserved from V40 |
| `0xC6208` | 205 | 65535 | slew slow step (`tp+0x7208`) — ratchet fix, preserved from V40 |
| `0xC5218` | `5325,3584,2406,1587,512` | `5325 × 5` | cap Y row, record copy 1 |
| `0xC5230` | `5325,3584,2406,1587,512` | `5325 × 5` | cap Y row, record copy 2 |
| `0xC5030` | `-21940,-12059,-5593,-22021` | `0,0,0,0` | Q13 slopes copy 1 |
| `0xC5038` | `-21940,-12059,-5593,-22021` | `0,0,0,0` | Q13 slopes copy 2 |
| **`0xC5FFC`** | `0x09C1200B` | `0x15207EA4` | **cap-block CRC — the only V41-vs-V40 change** |
| `0xC6FFC` | `0x2A0A3DB1` | `0xE1D012FE` | cal-block CRC |

Left stock: governor nominal `0xC6202`=4762, cap shift `0xC5160`=13, all X breakpoints, record counts
and terminators, every V38 calibration, banks B/C, and the entire application code range.

## Verification performed

- Bootloader walk 49/49 **and** full chain 50/50 pass on the V38 baseline, the V41 plain image, and
  the decoded V41 RWD readback.
- **V41 vs V40 = exactly 4 bytes, at `0xC5FFC`.** Asserted in the builder and re-checked independently.
- Application code `[0x13000,0xBF000)` byte-identical to V38. Block `[0xF9000,0x100000)` byte-identical.
- Both bank-A record copies and both slope copies identical to each other post-patch.
- RWD round-trips byte-for-byte; x31 checksum valid; part-number headers unchanged (`39990-TVA,A160`).
- Builder asserts every written address is *inside* a CRC-covered block and recomputes every dirtied
  block. V40's `assert_crc_gap_is_real()` is gone — it passed only because it re-derived the "gap"
  from the same walker it was meant to check.

## Process lessons

1. **A verifier and the assertion that checks the verifier must not share an assumption.** That is how
   V40 reached a car with a stale CRC and a green build log.
2. **Correlation on a population of one is not a mechanism.** "Only image with a bad CRC" + "only image
   that faults" + a plausible story was enough to get a confident root cause written into `CLAUDE.md`,
   a handoff, and a memory before any of it was traced. The trace then killed it.
3. **When a subagent's bytes contradict the lead's theory, the bytes win.** The subagent was explicitly
   told not to confirm the framing it was given, and it didn't. That instruction earned its keep.
