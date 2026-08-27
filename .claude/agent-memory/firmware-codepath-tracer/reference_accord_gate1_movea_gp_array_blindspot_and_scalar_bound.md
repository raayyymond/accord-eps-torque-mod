---
name: reference-accord-gate1-movea-gp-array-blindspot-and-scalar-bound
description: "GATE-1 method correction — `movea disp16,gp,rN` + `add rIdx,rN` materialises a gp-relative ARRAY base that NO disp16/disp23/mov-imm32/movhi scan can see (2,961 sites, 224 provably indexed); the SCALAR-BOUND argument makes it tractable; and an image-wide LE32 literal scan DOES catch gp-0x1500, contradicting the kit's 'passed both static methods' record."
metadata:
  type: reference
---

# GATE-1 RAM ownership: the method that actually reproduces the known failures (2026-08-09)

Stock `code.bin` and `_v86b_..._plain_image.bin` give identical answers for everything below.

## 1. 🛑 THE BLIND SPOT — gp-relative ARRAY bases via `movea`

`[EVIDENCE, Ghidra listing of FUN_0003b66a @0x3b8cc, 1 kHz]`
```
0003b8cc  movea -0x3e80,gp,ep      ; ep = gp-0x3E80
0003b8d0  cmovh 0x7,r6,r6          ; index clamped 0..7
0003b8d4  add   r6,ep
0003b8d6  sld.bu 0x0[ep],r9
0003b8da  sst.b  r9,0x0[ep]        ; WRITES gp-0x3E80..gp-0x3E79 (8 bytes)
```
**None of those 8 bytes appears in any disp16 or disp23 scan** — the store's displacement is 0 off `ep`.
The base comes from `movea disp16,gp,rN`, which is **neither `mov imm32` nor `movhi`**, so the pointer
scans in [[reference_accord_gate1_gp683c_ram_ownership_audit]] (methods 4/5/6) and every kit scanner
before this one were blind to it too.

Encoding: `movea disp16,reg1,reg2` = `hw0 = (reg2<<11) | (0x31<<5) | reg1`, `reg1 = 4` for gp,
**`reg2 != 0`** (`reg2 == 0` is the `mov imm32,reg1` escape — same opcode field, this is why the two get
conflated). Index detection: `add reg1,reg2` = `hw = (reg2<<11) | (0x0E<<5) | reg1`.

**Image-wide census (stock): 2,961 `movea disp16,gp,rN` sites, 796 distinct gp-relative bases, of which
224 are provably indexed by a register `add` ⇒ statically UNBOUNDED extent.** Same mechanism class as the
`0xb7260` registry that killed gp-0x1500, and far more common than it.

## 2. ★ THE SCALAR-BOUND ARGUMENT — what makes §1 tractable

An indexed array base `B` has unbounded extent. **But if some address `S` with `B < S < candidate`
carries a DEDICATED gp-relative scalar access, the compiler allocated a distinct named object at `S`, so
the array based at `B` cannot extend past `S`.** The candidate is out of that array's shadow.

This is exactly what gp-0x1500 lacked: its whole neighbourhood is 8-byte-stride registry literals with
**no dedicated scalar access anywhere in it**. It is also the inverse of the kit's long-standing search
strategy — see §4.

Applied: **gp-0x1300 FAILS** (nearest indexed base `0xFEDF6CFC` is **4 bytes below**, nothing between)
despite its V51P flight clearance. **gp-0x1100 PASSES** (392 B to the nearest base, and that one is not
indexed). ⇒ if a cave reuses a V51P cell, use gp-0x1100, not gp-0x1300.

## 3. 🛑 CORRECTION OF RECORD — gp-0x1500 IS statically catchable

`docs/BUILD-LINEAGE.md:929` and `docs/research/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md:324` both state
gp-0x1500 "passed BOTH static methods". **It does not pass a correct literal scan.** `0xFEDF6B00` is an
LE32 literal in the image **twice** — at `0xb73ac` and `0xbb658` — inside a 13-entry 8-byte-stride
cluster (`0xFEDF6AE0`…`0xFEDF6B40`). Method: plain Python, 4-aligned LE32 over the whole 1 MB, **no range
restriction**. Whatever the 2026-07-23 scan did, it was not that.
This does **not** make static clearance sufficient (see §5) — it makes the pre-flight gate stronger than
the record claims.

## 4. The control harness — reproduces all four known on-car failures

Footprint-aware (an `ld.w` at X marks X..X+3), both encodings, image-wide. Decoder pinned against 4
Ghidra-confirmed fmt-VII sites, the `ld.bu` hw0-bit-5 site @`0x3AA94`, and the disp23 site @`0x4C784`.

| cell | on-car truth | caught by |
|---|---|---|
| gp-0x1500 | FAILED (V50) | (e) LE32 literal @`0xb73ac`/`0xbb658` |
| gp-0x14E0 | unsafe | (e) LE32 literal @`0xb7268` |
| gp-0x1700 | unsafe | (a) **disp23 form only** — `st.w r8,-0x1700,gp` @`0x1e446`; a disp16-only scan is blind |
| gp-0x14FA | BRICKED (V48B) | (a) **footprint-aware only** — 2 `ld.b(ext)` @`0x52052`/`0x53fc8` hit `0xFEDF6B07`, the HIGH byte |
| gp-0x1100, gp-0x683c | flew clean | correctly not flagged |

⚠ **No single method catches everything** — the array-shadow test does NOT catch gp-0x1500, and the
literal scan does NOT catch gp-0x1700. Report the methods separately; never collapse to one verdict.

## 5. What NO static method can see
(i) a base pointer **loaded from RAM at runtime** then indexed — live in this same function:
`ld.w -0x257c[gp],r6 ; ld.bu 0x14[r6],r6` @`0x3b8c2`; (ii) **DMA**; (iii) **a writer that writes ZERO**.
(iii) also defeats a V51P-class read-only probe: "cell stayed 0 for 24,000 frames" cannot distinguish
"no writer" from "a periodic memset". ⇒ the gp-0x1100/gp-0x1300 clearance carries that gap.

**Probe that closes (iii): a CANARY, not a watcher.** Each tick: read the cell, compare against the
expected value, latch a sticky mismatch, then write the next value of a known sequence. Report over the
`0x14A` byte-4 5-bit channel. Safe to fly on a zero-reader cell (§ [[reference-accord-gate1-write-only-diag-taps-are-the-best-cave-ram]])
because a wrong canary cannot reach the motor.

## 6. Scanner geometry notes
- disp16 signed ⇒ gp reach = `0xFEDF0000..0xFEDFFFFF`. App RAM = `0xFEDEC000..0xFEDFFFFF`; the 16 KB
  disp16 cannot reach is exactly the **stack** (`sp=0xFEDEF91C`, grows down). ⇒ **a cave never needs
  disp23 for state.**
- disp23 sub-opcodes confirmed against Ghidra: `0x7`=ld.h, `0x9`=ld.w, **`0xF`=st.w** (an earlier guess of
  `st.h` here UNDER-marks footprints — the unsafe direction). Unconfirmed subops should be forced to
  4 bytes / treated as writes.
- Scanning every byte offset (not just even) OVER-marks. That is the safe direction: it can only reject a
  good candidate, never accept a bad one.
- 🛑🛑 **`get_assembly_context` returned `{}` for EVERY address tried in this session — including
  `0x3b866`, a CONFIRMED real instruction** (`st.w r28,-0x6de8,gp`, found by `search_instructions` and
  present in `disassemble_function`'s listing), and including with `program="code.bin"` passed
  explicitly. **The tool is unreliable here; its `{}` carries NO information.** An earlier revision of
  this memory said an empty return proves a byte-scan alias — **that was WRONG and is retracted.**
  **To test an instruction boundary, use `disassemble_function` on the containing function and read the
  real boundaries**, or `search_instructions` (which reports `instructions_scanned: 183641` when it has
  hit the analysed program — a useful liveness tell in its own right).
- 🛑 **Scan EVEN offsets only when ENUMERATING** (V850 instructions are 2-byte aligned), and all offsets
  only when building a deliberately over-marked occupancy map. Even-offset is still not sufficient — a
  4-byte instruction's second halfword also sits on an even offset. Worked example: `st.b …,-0x3641[gp]`
  "found" at **odd** `0x30a1f` is inside `mulf.s r8,r14,r8` @`0x30a1c` (next real instruction `0x30a20`),
  and would have falsely condemned the 8.131 Hz damper's state block.

Related: [[reference_accord_gate1_gp683c_ram_ownership_audit]] ·
[[reference_accord_app_ram_layout_and_boot_init_loops]] ·
[[reference-accord-gate1-write-only-diag-taps-are-the-best-cave-ram]] ·
[[accord-free-ram-candidates-gp1500-gp14e0]] (that memory's gp-0x1500/gp-0x14E0 recommendations are
FALSIFIED on-car — kept only as a record of the failed method).
