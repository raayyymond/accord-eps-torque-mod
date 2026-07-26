---
name: accord-free-ram-candidates-gp1500-gp14e0
description: 2020 Accord TVA-A160 (V850E2, master.bin) — two confirmed-zero-reference RAM words near the CAN TX buffer cluster (gp-0x1500 = 0xFEDF6B00, 16-bit; gp-0x14E0 = 0xFEDF6B20, 32-bit), found by exhaustively mapping used/unused bytes in the gp-0x14C0..gp-0x1518 neighborhood. Flags a real register-indirect blind spot in the adjacent mailbox-descriptor array (gp-0x1480..gp-0x14B8).
metadata:
  type: reference
---

# Free RAM word candidates near the CAN TX buffer cluster (session 2026-07-13)

Goal: a 16/32-bit RAM location in the bss-clear range (0xFEDEC000-0xFEDFFFFF) with zero static
references anywhere in `master.bin`, reachable by signed disp16 from gp (0xFEDF8000), for a telemetry
flag word. Method: `search_instructions` operand-substring scans anchored on the displacement text
(`-0x14XX`/`-0x15XX`), cross-checked against the already-known CAN buffer map in
[[reference_accord_can_tx_segmentD_known_frame_provenance]] and [[reference_accord_can_tx_frame_0x14a_bytemap]].

## Known-occupied anchor (confirms the neighborhood)
- gp-0x1518..gp-0x1511 (0xFEDF6AE8-EF): CAN 330 buffer, `FUN_00055a98` (8 bytes, contiguous).
- gp-0x1510..gp-0x1509 (0xFEDF6AF0-F7): CAN 0x660 buffer, `FUN_000561b0` (8 bytes, contiguous,
  immediately adjacent to 330's buffer — confirmed via `-0x151`/`-0x150` operand scans showing every
  suffix 09-10 and 11-18 individually touched by one of the two builders).

## CONFIRMED CANDIDATE 1 (recommended primary): gp-0x1500 = 0xFEDF6B00, 16-bit safe
- Zero hits for `-0x1500` directly, zero hits in the "-0x150" bulk scan (17 matches total in that
  bucket, none touch suffix 00 or 01), zero hits for `-0x14ff` in the exhaustive 269-match "-0x14" dump
  (which is provably exhaustive — `search_instructions` reported `truncated: false` at 269/185116).
- Nearest used neighbor: gp-0x1502 (single isolated flag byte, read by twin functions `FUN_00051fbc`/
  `FUN_00053f32` — see "sparse flag region" note below), 2 bytes away. Nearest buffer: 0x660's end at
  gp-0x1509, 7 bytes away.
- A 16-bit `st.h`/`ld.hu` at gp-0x1500 covers absolute bytes 0xFEDF6B00 (LSB) and 0xFEDF6B01 (MSB, i.e.
  displacement gp-0x14FF) — **both independently confirmed zero-reference**. Do NOT use this address for
  a 32-bit word: gp-0x14FD and gp-0x14FE (which a 32-bit write would also touch) are USED
  (`FUN_00052832`, `ld.bu -0x14fd`/`-0x14fe`).

## CONFIRMED CANDIDATE 2 (32-bit safe): gp-0x14E0 = 0xFEDF6B20
- Zero hits for `-0x14e0` directly and absent from the exhaustive 269-match "-0x14" dump.
- Byte-by-byte mapping of the surrounding hundred-block (gp-0x14DC through gp-0x14E8, all individually
  confirmed via the same dump) shows a clean 4-byte run at suffixes dd,de,df,e0 — bounded below by
  gp-0x14DC (`FUN_00021784`, `st.h`, halfword covers dc+db) and above by gp-0x14E1..E6 (`FUN_000558a6`,
  6 individual byte stores). A 32-bit `st.w`/`ld.w` at gp-0x14E0 covers absolute bytes gp-0x14DD through
  gp-0x14E0 (all 4 confirmed unreferenced) — **safe for a full 32-bit word**, not just 16-bit.

## Third candidate, lower confidence: gp-0x14C0 = 0xFEDF6B40 (byte-only, do not use for 16/32-bit)
- Zero direct hits and absent from the exhaustive dump, BUT sits 1 byte from a used struct
  (`FUN_0001fafa`, 8 contiguous bytes at gp-0x14C1..gp-0x14C8) on one side, and — more importantly — is
  structurally adjacent to an **8-slot, 8-byte-stride mailbox/channel descriptor array** at
  gp-0x1480/-0x1488/-0x1490/-0x1498/-0x14A0/-0x14A8/-0x14B0/-0x14B8 (found via `movea` address-computation
  instructions in `FUN_0001cc9e`/`FUN_0001cd96`, which dispatch on an input 0-4ish selector to pick one of
  these 8-byte record bases — plausibly the FCN0 7-mailbox descriptor table + 1 pad slot). gp-0x14C0 would
  be array-index 8 (one past the highest found slot, gp-0x14B8), consistent with being genuinely
  past-the-end rather than an internal gap — but this was NOT proven byte-by-byte (the individual field
  offsets b9-bf inside each 8-byte record were not disassembled this session). **Do not use for a 16/32-bit
  word without first disassembling what `FUN_0001cc9e`/`FUN_0001cd96`'s callers do with the returned
  pointer** (a caller doing `ld.b N[r1]` for nonzero N would extend into this array via register-indirect
  addressing that no gp-relative literal scan can catch).

## Structural caveat (applies to all 3, flagged per calibration discipline)
Static literal-displacement scanning cannot see a register-indirect access where the base pointer is
computed once (via `movea`/`mov`) and then indexed with a runtime or non-gp-relative offset (`ld.b N[r1]`,
`sld.bu 0[ep]` after `ep = base + computed_index`). This exact idiom is confirmed live in this same
neighborhood (the 8-slot array above, and the 8-way nibble-priority-encoder in
[[reference_accord_can_tx_mailbox_index_map]]). Candidates 1 and 2 were chosen specifically because they
sit OUTSIDE any observed `movea`-computed base's plausible reach; candidate 3 sits closer to one and is
downgraded accordingly. If a live UDS/CCP memory-read primitive exists, a runtime read-before-write
sanity check (confirm the byte is genuinely 0 or otherwise idle) would close this residual risk
empirically — not attempted this session (static study only).

## Sparse flag-region observation (context, not actionable)
`FUN_00051fbc`/`FUN_00053f32` (byte-identical twins) each reference ~14 individual byte offsets scattered
non-contiguously across gp-0x1401 through gp-0x1502 (e.g. -0x1409,-0x1411,-0x1424,-0x142b,-0x1439,-0x1451,
-0x1459,-0x1461,-0x1471,-0x14e9,-0x14f1,-0x14f9,-0x1502). This reads as a sparse named-flag/status region
(compiler-scattered globals, not a dense struct) — consistent with why clean gaps exist between used
bytes without any packing logic. Not further chased this session.
