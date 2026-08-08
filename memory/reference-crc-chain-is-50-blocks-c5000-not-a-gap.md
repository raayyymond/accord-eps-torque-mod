---
name: reference-crc-chain-is-50-blocks-c5000-not-a-gap
description: "The 0xC6000 bridge is REAL (byte-verified). NOTHING in the firmware checks block [0xC5000,0xC5FFC) — bootloader does a blank-check only, app has no CRC32 and zero xrefs to 0xC5FFC. The stale CRC is a RED HERRING for V40's ignition fault."
metadata: 
  node_type: memory
  type: reference
  originSessionId: 2a888703-82cf-4378-8b23-ce6677f440d5
  modified: 2026-07-19T23:13:44.523Z
---

⚠⚠ **THE `0xC6000` BRIDGE IS REAL. DO NOT REMOVE IT FROM `verify_bootloader_crc.walk()` AGAIN.**

On 2026-07-19 the lead removed it, believing it was a radare2 default-`v850` mis-decode. **That claim
was WRONG and is retracted.** `FUN_0000b006` (UDS CheckProgrammingDependencies) genuinely contains:

```c
if (puVar3 == &LAB_000c6000) { puVar3 = &DAT_00013000; puVar2 = &DAT_000b1ffc; }
```

Byte-verified in `code.bin`: `0xB070`/`0xB072` = `movea 0x6000`/`movhi 0x000C` → the literal `0xC6000`
compared against; `0xB07A`/`0xB07C` → `0x13000`; `0xB080`/`0xB082` → `0xB1FFC`. The bootloader really
does jump `0xC6000` → main and never dereferences the link fields pointing at `0xC5000`.

That routine is **UDS-diagnostic-session-only** and its failure path ends in **NRC `0x72`** — no DTC,
no motor-off. It cannot produce an ignition-time lamp.

**NOTHING CHECKS THAT BLOCK — CLOSED 2026-07-19 by three independent traces.** Boot path (`0x8000`→`0x9070`) does a **blank/presence check only**: four addresses (`0x13010`, `0x14000`, `0x9060`, `0xA6000`) compared against `0xFFFFFFFF`, no CRC anywhere, then `jr 0x14010` into the app. App range has **no CRC32 polynomial** (`0xEDB88320`/`0x04C11DB7` both absent) and **zero xrefs to `0xC5FFC`/`0xC5FF8`/`0xC5FFA` in the entire 1 MiB image**. The sole reader `FUN_0007b022` applies **no** plausibility check. ⇒ **The stale CRC at `0xC5FFC` is a RED HERRING for V40's ignition fault, and V41's 4-byte repair cannot fix it.**

**Block provenance.** `[0xC5000, 0xC5FFC)` is self-describing (`0xC5FF8`=`0x00C5`,
`0xC5FFA`=`0x0001`) and its CRC32 at `0xC5FFC` is **correct in stock, V31, V37, V38** — something
maintains it. It is written by bootloader flash routine `FUN_0000d934` during a UDS reprogramming session; the CRC is vestigial build-tool output that nothing reads. Two walkers now exist:

- `walk()` — faithful bootloader replay, **49 blocks**, bridge included. Predicts UDS NRC `0x72`.
- `walk_all_blocks()` — stored linked list, **50 blocks**. **Hygiene only**, not a BL replay.

**V40 status:** wrote the cap tables into that block and left `0xC5FFC` stale — passes `walk()` 49/49
(so the flasher's dependency check reported clean) but fails `walk_all_blocks()` at exactly that block.
V40 also faulted at ignition. **The causal link is NOT established** — a stale `0xC5FFC` has no known
consumer. V41 = V40 + those 4 bytes: correct hygiene, **not a proven fix**. Still-open candidates for
the real cause: an app-level integrity/plausibility check (a flat cap table with **zeroed Q13 slopes**
is exactly what a monotonicity check or an inverse/reciprocal interpolation would choke on), or
something reached by the `65535` slew cals. See [[v40-governor-slew-root-cause]] and
`docs/HANDOFF-2026-07-19-v41-crc-c5000-block-fix.md`.

**Process lessons, worth more than the four bytes:**
1. V40's `assert_crc_gap_is_real()` passed because it re-derived the gap from the same walker it was
   meant to check. **A verifier and the assertion that checks it must not share an assumption.**
2. The lead reached a confident wrong root cause from a suggestive correlation (only image with a bad
   CRC = only image that faults) plus a plausible-sounding mechanism, and wrote it into `CLAUDE.md`,
   a handoff and a memory before a subagent's bytes overturned it. **Correlation on a population of
   one is not a mechanism.** When a subagent contradicts the lead, the bytes win — see
   [[feedback-delegate-firmware-tracing-to-subagents]].
