---
name: reference-accord-v50-ram-audit-gp1500-gp14e0-and-status-table
description: V50 EMA-filter RAM audit — full-footprint re-verification of gp-0x1500 and gp-0x14E0, discovery of two literal RAM-address tables referencing both cells with an unresolved consumer, and a reusable V850E2 byte0-opcode-family table for exhaustive gp-based ld/st/addi/movea scans.
metadata:
  type: reference
---

## Context
Extends (does not contradict) [[reference-accord-v48b-freeram-and-v850-encoding-formulas]]. That memory
checked gp-0x1500 only as a **halfword** (bytes 0-1) and gp-0x14E0 as a single cell before correcting it
to a 4-byte run. This session (2026-07-22) re-verified **both as full 4-byte footprints** using an
exhaustive masked byte-pattern method (not text-based `search_instructions`, which this session again
proved gives misleading zeros — see below), and separately discovered a **structural risk neither prior
audit checked: literal RAM-address tables**.

## Method: exhaustive byte0-family sweep (reusable for future RAM audits)
V850E2's format-V/VI (4-byte, reg1+disp16) instructions all live in the 6-bit opcode range 0x30-0x3F.
With reg1 fixed (e.g. `gp`=r4), `byte0 = ((opcode&7)<<5)|reg1` — i.e. byte0 depends only on the opcode's
**low 3 bits**, so opcodes 0x30-0x37 and 0x38-0x3F pair up into exactly **8 byte0 values** when byte1
(which carries reg2 + the opcode's top 3 bits) is wildcarded. With reg1=gp=4, the 8 byte0 values are
`04,24,44,64,84,A4,C4,E4`. Confirmed opcode identities (bit-derived from real bytes, ≥2 examples each):
`0x30`=ADDI, `0x31`=MOVEA, `0x38`=LD.B, `0x39`=LD.H/LD.W(shared, bit0 of disp selects), `0x3A`=ST.B,
`0x3B`=ST.H/ST.W(shared), `0x3C`=LD.BU, `0x3D`=**also decodes as LD.BU** in Ghidra's output (confirmed via
`disassemble_function` at `0x5285c`, byte0=0xA4) — V850E2 apparently has two hardware encodings that both
render as `ld.bu`; `0x3F`=LD.HU. `0x32-0x36,0x3E` uncharacterized but included defensively (over-inclusive
is safe). **Unsigned ops (LD.BU/LD.HU, and whatever 0x3D is) force bit0=1 in the raw disp16 field
regardless of natural alignment** — Ghidra's decompiled/disassembled mnemonic text shows the TRUE
(masked) displacement, but a raw byte scan for e.g. "-0x14FD" will also catch a masked/forced-bit access
whose true target is the adjacent EVEN address "-0x14FE". Always cross-check odd-disp byte-pattern hits
against Ghidra's actual disassembly before attributing them to a specific byte.

Search pattern per target byte: `search_byte_patterns(pattern="XX??LLHH")` where XX=byte0 (one of the 8
values), LL/HH = little-endian disp16 for that displacement, `??` wildcards byte1 (nibble-wildcard syntax
confirmed working on this MCP build — no separate `mask` parameter needed; the documented `mask` param
did not behave as expected in several tested conventions and was abandoned in favor of `?` nibbles).
Running all 8 byte0 values × N target displacements exhaustively covers **every possible gp-based
load/store/addi/movea** touching those addresses, image-wide (not just Ghidra-analyzed instructions).

## Finding 1 — gp-0x1500 (abs 0xFEDF6B00) 4-byte footprint: bytes 2-3 are LIVE, previously unknown
- Bytes 0-1 (gp-0x1500/gp-0x14FF, abs 0xFEDF6B00/01): zero hits, all 8 opcodes, both direct gp-relative
  and movea/addi-with-gp-base forms. Matches prior "Cell A" halfword finding exactly.
- **Byte 2 (gp-0x14FE, abs 0xFEDF6B02): LIVE.** `ld.bu -0x14fe[gp],r14` @ `0x5286a`, inside
  `FUN_00052832` (`0x52832-0x528b7`). Confirmed via `disassemble_function` — raw bytes `84 77 03 eb`
  (byte0=0x84=LD.BU family; disp16 raw=0xEB03 with bit0 forced, true target -0x14FE).
- **Byte 3 (gp-0x14FD, abs 0xFEDF6B03): LIVE.** `ld.bu -0x14fd[gp],r12` @ `0x5285c`, same function.
  Raw bytes `a4 67 03 eb` (byte0=0xA4, the "also LD.BU" opcode 0x3D).
- **`search_instructions(operand_pattern="-0x14fd[gp]")` and `"-0x14fe[gp]"` both returned ZERO** despite
  Ghidra's own `disassemble_function` on the SAME address printing exactly that text. This is a
  **directly reproduced instance of the documented "misleading zero" bug**, not a corroborated absence —
  do not trust bare `search_instructions` operand-text nulls on this program without a byte-level
  cross-check, even when `truncated:false` and `instructions_scanned` looks complete.
- Zero writers found (ST.B/ST.H/ST.W family) across all 4 bytes, all 8 opcodes — this cell is read-only
  as far as direct instructions go.
- `FUN_00052832` decompiles to a param_1-gated (values 0,1,4,5,6,7) unpacker: it reads the byte at
  gp-0x14fd, extracts individual bits via shift chains, and writes flags to `gp-0x67b2`, `gp-0x67f7`,
  `gp-0x67f8`, `gp-0x67f9`, `gp-0x6817`; also reads bit1 of gp-0x14fe when param_1==0. It ends by calling
  `FUN_0005462c(8, param_1)`.
- **`get_function_callers`/`get_xrefs_to` on `FUN_00052832`'s entry (0x52832) both report zero** — but a
  raw 4-byte LE search for its own address (`32280500`) found it as a **function-pointer table entry at
  `0xbb660`**, 8 bytes past the well-known CAN-0xE4 fault-code dispatch table base `0xbb640` (see
  [[reference_accord_can_e4_intake_gates]]). **The function is LIVE, reached only via the same
  function-pointer-table mechanism already documented for that table's other entries — a THIRD
  reproduction this session of "zero xref ≠ dead code" on this program.**

## Finding 2 — a NEW, unresolved literal RAM-address table references BOTH gp-0x1500 and gp-0x14E0
Two data structures, found by raw 32-bit-LE literal search for the exact absolute addresses:
1. **`0xbb640`-based "record" table** (immediately adjacent to/interleaved with the CAN-0xE4 dispatch
   table): 32-byte (8-word) records of the shape `[function_ptr, 8, 6, 1, (0x0001,varies16), 1,
   RAM_address, 8]`. Record 1 = `{FUN_00052676 (the documented CAN-0xE4 intake handler), ...,
   addr=0xFEDF6B00 (=gp-0x1500 exactly)}`. Record 2 = `{FUN_00052832 (Finding 1 above), ...,
   addr=0xFEDF6C18 (a different cell, gp-0x13E8)}`.
2. **A flatter address-list table at `0xb7260`/`0xb7398`** (header word `0x800007FF` then a straight
   array of ~25 RAM addresses in the `0xFEDF6Axx`-`0xFEDF6Cxx` range, spaced non-uniformly). This list
   **includes both `0xFEDF6B00` (gp-0x1500) and `0xFEDF6B20` (gp-0x14E0) as literal entries**, alongside
   ~23 other cells (gp-0x1520,1518,1510,1508,14E8,14D8,14D0,14C8,1490,14B8,14B0,1488,14A0,1478,1468,1460,
   1438,1420,13F8,13F0,13E8,13D0,13CC — full addr list preserved in session transcript, not reproduced
   here to keep this memory compact).
- **Could not find a consumer of either table this session** despite: raw literal search for
  `FUN_00052676`'s own address (found only at the one known `0xbb640` slot, no second reference);
  `search_instructions`/`get_xrefs_to` on the table base addresses (both zero, and by now expected to be
  unreliable regardless); a `mov 0xTABLEADDR,rX`-style 32-bit-immediate text search (also zero). **This
  matches and reconfirms a documented open item from [[reference_accord_can_e4_intake_gates]]:
  "Caller of the fault-code dispatch table... UNRESOLVED — owns checksum/counter logic, not found this
  session" — now independently reproduced by a second session with a different method.**
- **Safety implication (BELIEF, not proven):** if this table is walked by a generic dispatcher that
  performs a register-indirect store (`ld.w`/`st.w [rX]` where rX is loaded from the table's address
  field, e.g. to write incoming CAN-0xE4 payload or DTC/freeze-frame data), that write would be
  **completely invisible to any gp-relative or absolute-bitop instruction scan**, including the
  exhaustive one in this memory and the one in [[reference_accord_v48b_freeram_and_v850_encoding_formulas]].
  This is exactly the class of blind spot that caused the V48B brick (an aliased byte stomped by an
  unrelated writer). Until this table's consumer is found and characterized, **neither gp-0x1500 nor
  gp-0x14E0 should be treated as fully proven-free**, even where direct-instruction evidence is clean.

## Finding 3 — gp-0x14E0 (abs 0xFEDF6B20) 4-byte footprint: CONFIRMED clean of direct/absolute access, twice
All 8 byte0 opcode families × all 4 bytes (disp `0x14DD`/`0x14DE`/`0x14DF`/`0x14E0`) returned **zero**
hits this session — full independent reconfirmation, via a different method, of
[[reference_accord_v48b_freeram_and_v850_encoding_formulas]]'s "corrected free run... 4 contiguous bytes"
finding for the exact same footprint. The bounding live neighbor (`0x14E1`/`FUN_000558a6`, a CAN-status
packer) was reconfirmed present (found writers at `0x5590c`/`0x558e8` while probing an adjacent candidate
window, landing in `FUN_000558a6` as expected). **This is the stronger of the two original candidates on
direct-instruction evidence alone** — its only open caveat is the Finding-2 table reference, shared with
gp-0x1500.

## Finding 4 — Task B (alternate clean window) in gp-0x14C0..gp-0x1520: NOT productive
Two candidate 4-byte windows tested inside the operator-requested scan range, both FAILED:
- gp-0x14F4 (abs `0xFEDF6B0C`-0F): byte1 (gp-0x14F3, abs `0xFEDF6B0D`) is heavily used — 8 raw hits
  across ADDI/LD.B, ST.B, ST.H/W-family, LD.BU opcode buckets (addresses `0x3a251`, `0x57989`,
  `0x72861`, `0x72c0f`, `0x72ccb`, `0x73d4b`, `0x7455b`, `0x52474` — not individually adjudicated, but
  the density alone disqualifies this window).
- gp-0x151C (abs `0xFEDF6AE4`-E7): bytes 1-2 (gp-0x151B/gp-0x151A) are writers, both `st.b` in
  `FUN_000558a6` (`0x5590c`, `0x558e8`) — the same CAN-status packer bounding gp-0x14E0's live neighbor.
- **The requested gp-0x14C0..gp-0x1520 window is densely populated** — both by direct-instruction
  accessors (this session) and by the Finding-2 address table (8 of ~25 known table entries fall inside
  this exact range: gp-0x14E8/14E0/14D8/14D0/14C8/1510/1518/1520). **Do not keep hunting in this
  neighborhood.** [[reference_accord_v48b_freeram_and_v850_encoding_formulas]] already identifies a far
  better-vetted alternative: **Cell C, gp-0x7F00ish through gp-0x7FFFish (abs ~`0xFEDF0000`-`0xFEDF00FF`,
  a clean 256-byte run)**, exhaustively checked by a different method (search_instructions prefix sweep +
  set1/clr1/tst1 absolute-bitop scan) and structurally far from this entire CAN/DTC status-byte cluster.
  This session did a light spot-check confirming the `movhi -0x121,r0,rX` hits near there are the
  already-documented absolute-addressing idiom, not a second literal-address table of the Finding-2 kind.

## Bottom line for V50
- **gp-0x1500, 4-byte: UNSAFE.** Bytes 2-3 have confirmed live readers (FUN_00052832, itself live via a
  dispatch table); byte0's address also appears in two unresolved literal-address tables.
- **gp-0x1500, 2-byte (bytes 0-1 only): provisionally clean of direct access (2 independent sessions,
  2 methods) but carries the unresolved Finding-2 table flag** — downgrade from "SAFE" to "clean of
  everything checkable, with one open structural risk."
- **gp-0x14E0, 4-byte: clean of direct/absolute access (2 independent sessions, 2 methods)** — the
  stronger of the two original candidates, but shares the same Finding-2 table flag.
- ~~Recommended path: use Cell C (gp-0x7F00ish, abs ~0xFEDF0000-00FF) instead of either original
  candidate.~~ **RETRACTED same session, see below — Cell C is NOT free RAM.**
- **Before ANY of these cells is used in a flashed build:** find and characterize the Finding-2 table's
  consumer. This is now a twice-reproduced open item (this session + [[reference_accord_can_e4_intake_gates]])
  and should probably get a dedicated session rather than more ad hoc byte-search attempts.

## Finding 5 (same session, follow-up) — Cell C is DEBUNKED: it's a ~600+ byte boot-shadow-copied control block, not free RAM
The coordinator asked for full Cell-C vetting for a 4-byte STATE + 2-byte OUTPUT window near abs
`0xFEDF0000` (gp-0x8000, the extreme edge of gp's negative reach). This uncovered a THIRD accessor
category beyond gp-relative disp16 and literal address-tables: **a boot-time flash-to-RAM copy loop**.

- `FUN_00008446` (`0x8446-0x851b`), called from `FUN_000089fe`@`0x8a14` (itself called from `0x8be6`),
  deep in a chain of flash-config-validity checks (`cmp -1,rX` against multiple `0xa7074/a7078/a7088/
  a708c` flash words) run early/low in the address space — architecturally consistent with power-on init,
  though not traced all the way back to the reset vector this session. It does TWO word-copy loops:
  (1) 4096 bytes, flash `0xac000` → RAM `0xFEDFA400` (unrelated, different region);
  (2) **~592 bytes, flash `[0x8bf0,0x8e3e)` → RAM starting exactly at `0xFEDF0000`**, incrementing the
  destination pointer by 4 every iteration (`mov 0xfedf0000,r12` then a loop: `sld.w 0[ep],r10; add
  4,ep; st.w r10,0[r12]; add 4,r12`). Destination span: abs `0xFEDF0000`-`~0xFEDF024F` (gp-0x8000 to
  gp-0x7DB1).
- At least 14 small "table lookup" helper functions (`FUN_000022f4, FUN_00004c8c, FUN_00005130,
  FUN_00005498, FUN_00005514, FUN_0000559c, FUN_0000571e, FUN_0000580c, FUN_000058fa, FUN_00005932,
  FUN_00005968, FUN_000059f0, FUN_00005a24, FUN_00008446`) reference this base via the SAME
  `mov 0xfedf0000,reg` (or `mov 0xfedf0070,reg`, a second hardcoded entry point INTO the same copied
  blob at relative offset 0x70) absolute-literal idiom, then use FIXED offsets (`0x4,0x8,0xc,0x10,0x14,
  0x1c,0x24,0x28,0x2c,0x30,0x34,0x38,0x3c,0x40` from the `0x0` base; up to `0x234` from the `0x70` base,
  i.e. abs `0xFEDF02A4`) to read/write real fields — confirmed READS (`ld.w 0x10[r27]`) and WRITES
  (`sst.w r0,0x10[ep]` / `sst.w r14,0x14[ep]`) on offsets squarely inside my originally-proposed window.
- **This single mechanism invalidates the "Cell C" recommendation in
  [[reference_accord_v48b_freeram_and_v850_encoding_formulas]] outright** — that memory's own residual-risk
  caveat ("regular ld/st absolute forms via the -0x121 register family were not individually audited...
  architecturally this residual risk is low") was WRONG for this specific region; the boot-copy loop
  alone proves ~600 bytes of "Cell C" are a live, actively-populated, actively-read-and-written control
  block, not free RAM.
- A follow-up scan found gp-0x7D88..gp-0x7D79 (abs `0xFEDF0278-027F`, i.e. 12 bytes through `0xFEDF0283`)
  clean of BOTH the gp-relative 8-opcode scan AND literal full-address references (confirmed via an
  exhaustive `"??02dffe"` wildcard covering the entire `0xFEDF0200-02FF` sub-range in one query — the
  only two literal hits in that whole 256-byte range were `0xFEDF0284` and `0xFEDF02A4`/`0x2D0`/etc.,
  none inside `0x278-0283`). However `0xFEDF0284` (immediately adjacent) is the confirmed base of a
  **dynamically-indexed packed 2-bit array** (`FUN_0000235e`, 13 callers found via `get_xrefs_to` — for
  once a real positive result — feeding CAN-signal/index-driven lookups), whose upper extent from those
  13 callers was NOT individually bounded this session — treat `0x284` onward as live/unknown-extent, not
  just the one byte. **This candidate window was superseded by the coordinator's pivot to gp-0x1500
  before a second-register (non-gp base, e.g. r28=`0xFEDF0070`) offset-collision check could be
  completed** — see the in-session interruption; do not treat `0xFEDF0278-0283` as fully cleared, only
  as "cleared on the two methods checked so far, with the r28-base-offset risk category still open."

## Follow-up session (2026-07-22, continued): the walker search — decisively unresolved, twice over
The coordinator asked for the ONE load-bearing question: does anything WRITE gp-0x1500 bytes 0-1 at
runtime? This required finding the walker/consumer of the `0xbb640` dispatch table (Finding 2 above).

**Table geometry, fully mapped this pass.** The table is 32-byte records starting at abs `0xbb560`
(NOT `0xbb640` — that's just where FUN_00052676's record happens to sit), preceded by a header/strings
block at `0xbb500-0xbb55F` containing null-terminated ASCII `"Failed"`, `"OK"`×4, `"UERBuerbSPE"`, then a
`4,8,16,32,64,128,0,0` byte sequence (a bit-mask lookup table, i.e. `2^2..2^7`) — strongly suggestive of
a **boot-time self-test / diagnostic-report framework**, not a per-frame real-time validator. 10 records
confirmed (fn_ptr field found at `0xbb560,580,5a0,5c0,5e0,600,620,640,660,680`, each exactly 32 bytes
apart — verified by exact string-offset arithmetic, not eyeballing). Record layout (LE, 32 bytes):
`+0x00 fn_ptr(u32) / +0x04 index(u32, 1..10) / +0x08 const_A(u32, mostly 3) / +0x0C const_B(u32, =1) /
+0x10 u16,u16 (varies per record — plausibly size/offset fields) / +0x14 const_E(u32,=1) /
+0x18 DATA_PTR(u32, RAM address) / +0x1C LEN(u32, 8 or 15)`. FUN_00052676's record (index=8, at `0xbb640`)
has DATA_PTR=`0xFEDF6B00`(=gp-0x1500), LEN=8. FUN_00052832's record (index=9, at `0xbb660`) has
DATA_PTR=`0xFEDF6C18`, LEN=8.

**Exhaustive search for the walker — three independent methods, all negative:**
1. Literal full-address search for the table/header base, wildcarding every possible low-byte in both
   the `0xbb500-0xbb5FF` and `0xbb600-0xbb6FF` windows (`search_byte_patterns` `"??b50b00"` /
   `"??b60b00"`, i.e. every address in each 256-byte range as a raw 32-bit LE literal, image-wide):
   **zero genuine hits.** The one raw hit in the `0xbb600` bucket (`0x4b6c8`, value `0x000BB60D`) was
   individually verified via `disassemble_function` to be a coincidental byte-collision — the real
   instruction there is `addi 0xb,r13,r22` inside an unrelated loop (`FUN_0004b664`, a diagnostic-report
   printer using `movea -0x1304,gp,r6` / `jarl 0x49b2c` repeatedly), not an absolute-pointer load. This
   matches a documented pattern in [[reference_accord_v48b_freeram_and_v850_encoding_formulas]] ("a
   coincidental hex collision at an unrelated cell, correctly excluded").
2. `movhi`+`movea` SPLIT construction (the two-instruction form, as opposed to the single "mov IMM32,reg"
   pseudo-op used elsewhere in this binary — see the boot-shadow-copy discovery above): computed the
   correct sign-extended `movea` immediates for both plausible bases (`movhi 0xC,r0,rX` +
   `movea -0x4aa0,rX,rX` = `0xbb560`; same `movhi 0xC` + `movea -0x4b00,rX,rX` = `0xbb500`) and searched
   `search_instructions(operand_pattern="-0x4aa0")` / `"-0x4b00"`: **zero** (text-based, so weaker
   evidence than method 1, but consistent).
3. Caller graph: `get_function_callers`/`get_xrefs_to` on `FUN_00052676` and `FUN_00052832` both zero
   (already known); this pass additionally confirmed **zero non-`lp` `jmp rX` instructions anywhere near
   the `0x4Bxxx-0x53xxx` code cluster** where all these small CAN-validator-family functions live — the
   357 `jmp lp` (plain returns) and ~140 `jmp rX` (r20-r29, r6, r12, r0, r2) hits found image-wide are all
   in structurally unrelated functions elsewhere in the binary (spot-checked several; none touch this
   table or its fn_ptr family).

This **exactly reproduces** the prior dedicated investigation's conclusion in
[[reference_accord_can_e4_intake_gates]] ("a full linear disassembly of `0x0-0xc4000`, zero hits... NOT
called by a literal jarl anywhere") — now independently reconfirmed by a SECOND session using a
DIFFERENT toolchain (GhidraMCP vs that session's r2), across the FULL 1MB image (not just `0x0-0xc4000`),
and by three separate methods. **The walker is either genuinely absent from statically-discoverable code
(e.g. invoked via a mechanism this class of tooling structurally cannot see — DMA descriptor, hardware
sequencer, or a pointer cached in RAM at boot from a source outside the flash image) or is diagnostic/
UDS-service code invoked rarely enough that its dispatch doesn't look like a typical hot-path loop.**

**Verdict on the actual safety question (gp-0x1500 bytes 0-1, i.e. `0xFEDF6B00/01`):**
- **Direct pathway: CONCLUSIVELY zero writes.** The exhaustive 8-opcode-family byte scan earlier in this
  file covers every gp-relative `st.b/st.h/st.w` (and, via the shared-opcode-family byte0 values,
  arithmetic/`addi`/`movea`-with-gp forms) touching any of the 4 bytes `0xFEDF6B00-03` — zero writer hits,
  full stop. FUN_00052676 (the record's handler) is independently confirmed via `decompile_function` to
  never read or write `0xFEDF6B00` — its CAN payload comes from `gp-0x1424/1426` (≈`0xFEDF6BD8`, the
  separately-documented "routed buffer" for CAN-0xE4, per [[reference_accord_can_e4_intake_gates]]).
- **Indirect (table-walker) pathway: UNRESOLVED, not "proven clean."** I could not find a store
  instruction to prove or disprove a write via the generic dispatcher, despite three independent search
  methods across the whole image. This is a genuine gap, not a disguised "no" — **do not round this to
  SAFE without the operator explicitly accepting the residual risk.**
- **If a different record's buffer were considered instead:** no better off — every record in this table
  (all 10) is consumed by the SAME unresolved walker, so moving to e.g. `0xFEDF6C18`
  (FUN_00052832's DATA_PTR) inherits an identical unresolved-writer risk, not a fresh one.
- **The "Failed"/"OK" diagnostic strings + bit-mask table preceding the record array** are circumstantial
  evidence (BELIEF, not proof) that this whole framework may be a boot-time self-test/diagnostic-report
  system rather than a hot 100 Hz path — if true, DATA_PTR usage would plausibly be init-time-only. This
  is a plausible mitigating hypothesis, not a verified one.

## Cross-reference
[[reference_accord_v48b_freeram_and_v850_encoding_formulas]] (Cell A/B/C definitions, V850E2 encoding
formulas this session's method builds on), [[reference_accord_can_e4_intake_gates]] (the CAN-0xE4 intake
chain and its own unresolved dispatch-table-caller open item, now independently reconfirmed by a second
session/toolchain over the full image).
