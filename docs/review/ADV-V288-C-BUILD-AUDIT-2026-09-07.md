# Adversary C — build-script audit of V288 — 2026-09-07

**VERDICT: PASS on surface #3 (build-script audit).** No prereg FAIL condition is met. The image and
the .rwd on disk are exactly what the script says they are, reproduced by an independent rebuild that
shares no code with the builder.

Six findings follow. **None changes a byte of the image.** Five are documentation/census defects; one
is a partial-write hazard in an optional code path. I recommend flashing is not blocked by any of them.

---

## 0. Method

Everything below is EVIDENCE unless marked otherwise. My rebuild
(`<scratch>/advC_rebuild.py`) re-derives the V850E2 instruction encodings from the field layout
longhand, re-implements the bootloader CRC walk from the documented algorithm in
`analysis-2020accord/lib/verify_bootloader_crc.py`'s docstring, and imports nothing from
`build_v288_tva.py`. The .rwd was decoded with the kit's `parse_x31`, but its cipher was recovered by
brute-forcing the 512 (key, op-triple) combinations against the image rather than by taking the
builder's table.

---

## 1. Hashes — both artifacts match their claims [EVIDENCE]

| artifact | sha256 |
|---|---|
| `_v288_…SPFILT.K4…_plain_image.bin` | `bc8a5b1ac2f796faa5563bb79e221a2f884f55ec040c654114fa2861f2ef5571` |
| `39990-TVA,A160-V288-…rwd` | `862cb52591f6899223053bf5e833f77d148b7ab89c895ac86dab008adfbb6f26` |
| V282 base | `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe` |

Both claimed hashes are correct.

## 2. Independent rebuild — reproduces the hash exactly [EVIDENCE]

I re-derived all four blobs from the V850E2 field layout without reading the builder's encoder. Every
one matched the brief's byte string and the built image:

```
hook jr  @0x29D72   89076aae
cave jr  @0xC4BD6   80072a00
FILT     @0xC4BDC   244fce95 a9811030 a4826082 ca056032 a2050182 c9816487 ce952487 ce95b607 7c51   (34 B)
TELE     @0xC4C00   003a2437 ce956032 ae05013a 8437edea c636fe00 07314437 ecea2436 e8ea7f00        (32 B)
```

Worked check on the two displacements, both ways:

- `jr 0x29D72 → 0xC4BDC`: d = `0x9AE6A`; hw1 = `(0<<11)|(0x1E<<6)|0x09` = `0x0789`; hw2 = `0xAE6A` → `89 07 6a ae`.
- `jr 0xC4BD6 → 0xC4C00`: d = `0x2A`; hw1 = `0x0780`; hw2 = `0x002A` → `80 07 2a 00`.
- FILT return `jr 0xC4BFA → 0x29D76`: d = `-0x9AE84` → `0x36517C`; → `b6 07 7c 51`.

**Independently computed CRC cell for the owning block: `a0 18 5f ad`** (`crc32[0x013000,0x0C4FFC) =
0xAD5F18A0`). This equals the cell in the built image and the value the brief expected.

My rebuilt image sha256 is `bc8a5b1a…f2ef5571` — **identical to the artifact on disk**.

## 3. Full-file diff — 78 bytes, all inside the allowed set [EVIDENCE]

```
[0x029D72,0x029D76)   4 B  hook            V282 6487ce95  →  V288 89076aae
[0x0C4BD6,0x0C4BDA)   4 B  cave exit       V282 7f00ffff  →  V288 80072a00
[0x0C4BDC,0x0C4BFE)  34 B  filter cave     V282 ff…ff     →  V288 244fce95…7c51
[0x0C4C00,0x0C4C20)  32 B  telemetry rung  V282 ff…ff     →  V288 003a2437…7f00
[0x0C4FFC,0x0C5000)   4 B  CRC trailer     V282 446bb04e  →  V288 a0185fad
```

Bytes outside the prereg allowed set: **0**. `0xC4FF0–0xC4FFB` is **untouched** (`010101010000c6001300b200`
in both). The two filler gaps `0xC4BDA–DB` and `0xC4BFE–BFF` remain `ff ff` in both images.

## 4. CRC chain and the .rwd [EVIDENCE]

- Full linked-list walk of the built image: **50 blocks, 0 mismatches** (this includes
  `[0xC5000,0xC5FFC)`, the block the bootloader skips).
- Bootloader replay including the verified `0xC6000` bridge: **49 blocks, 0 mismatches**.
- Exactly one CRC block owns all 74 edited code bytes: `[0x013000,0x0C4FFC)`, trailer at `0xC4FFC`.
  No edit lands on a trailer.
- The .rwd decodes to a single block `0x13000` length `0xED000`, and its plaintext is **byte-for-byte
  equal to the image over `0x13000–0x100000`**.
- The .rwd's 4-byte trailer `5b c6 d4 04` is the little-endian 32-bit sum of the whole body
  (`sum = 0x04D4C65B`). **Correct.** Its header block is identical to the V287 rev 2 .rwd's.

## 5. Re-runnability [EVIDENCE]

Three runs, one dry and two writing to separate scratch directories, all exit 0 and print
`407/407 assertions passed`. The two scratch runs produced byte-identical image and .rwd files, both
matching the on-disk artifacts, and their logs are identical once the scratch path is normalised. The
script is deterministic and re-runnable.

## 6. Disk hygiene [EVIDENCE]

A `find` across both project trees returns exactly one V288 image and exactly one V288 .rwd, both in
the firmware root. No `SPFILT` artifact for K=3 or K=5 exists anywhere. The V287 rev 1 image and .rwd
both still carry their `SUPERSEDED-DO-NOT-FLASH` prefix.

---

# Findings

## F1 — the substantive assertion count is overstated about 3.7× [EVIDENCE] · severity: LOW

The script's own census reports **347 substantive / 31 vacuous / 29 tautological**. My independent
classification of the same 407 lines:

| class | n | basis |
|---|---:|---|
| substantive | 94 | independently informative |
| entailed by the `[7]` stray check | 218 | see below |
| entailed by the `[10]` .rwd readback | 35 | see below |
| vacuous (entailed by the base sha256) | 31 | script agrees |
| tautological (readback of its own write) | 29 | script agrees |

The census taxonomy has three buckets and misses a third vacuity class: **entailed by a sibling
assertion**.

- Section `[7]` opens with `no byte outside the 4 written regions changed (0 stray)`. Once that
  passes, the 196 following `map/Kp/Kd/taper … byte-identical` checks and the 17 `0x… == base == V`
  FROZEN checks **cannot fail** — their regions are disjoint from the four written ranges. 218 of the
  219 assertions in that section are implied by the first one.
- Section `[11]` runs its whole body twice, once over `code` and once over `dec`. But `[10]` already
  asserts `bytes(dec) == bytes(code)`. All 35 `dec :` assertions are implied.

**I found no assertion whose predicate is FALSE.** This is overstatement, not a hidden false claim,
so it does not meet the prereg's FAIL condition. But the headline "347 substantive" should not be
quoted in the close-out or on the artifact page.

## F2 — one assertion's text claims more than its predicate tests [EVIDENCE] · severity: LOW

At `[11]`:

```python
check(u16(im, _andi + 2) | 0xF8 == 0xFE | 0xF8,
      f"{nm}: mask 0xFE preserves every bit (7,6,5,4,3) an existing rung owns", "S")
```

The predicate is `(mask | 0xF8) == 0xFE`, satisfied by **32 of 256 masks** — every mask whose bits
2:1:0 are 1,1,0, with bits 7..3 completely free. The OR mask blanks exactly the bits the text says are
being proved preserved. The claim is nonetheless TRUE, because the preceding line pins
`u16(im,_andi+2) == 0xFE` exactly, which entails it. So this is a census defect (a duplicate labelled
substantive) plus a text/predicate mismatch, not a safety defect.

## F3 — a pure tautology labelled substantive [EVIDENCE] · severity: LOW

At `[0]`:

```python
check(f"SPFILT.K{K_SHIFT}" in TAG, "the output name carries the dose (K…)", "S")
```

`TAG` is constructed from `K_SHIFT` on the line above. The predicate cannot fail for any K. It is
tautological, not substantive.

## F4 — a dead conjunct [EVIDENCE] · severity: NEGLIGIBLE

At `[3]`: `check(t_hi + (STRUCT_LO - t_hi) >= 0 and STRUCT_LO - t_hi >= 0, …)`. The first conjunct
reduces to `STRUCT_LO >= 0`, always true. The second is the real test and it passes.

## F5 — two docstring claims stated as fact that the script does not compute [EVIDENCE] · severity: MEDIUM (labelling only)

The docstring is unusually disciplined: it marks `TICK_HZ` a BELIEF, marks the `0x2AC68`
unreachability a BELIEF, and explicitly flags the wire-study numbers (`0.446`, `0.059`,
`1.81 % → 0.30 %`) as quoted rather than recomputed. Two claims escape that discipline:

1. **"`sp` is in NO loop: nothing downstream of E feeds back into `sp`"** (GATE 2). This is the entire
   basis of the GATE 2 PASS and of the "2-DOF, return ratio untouched" framing. The script computes the
   *zero-readers* half at `[2]`; the *not-in-a-loop* half is inherited from the source trace and is
   printed as fact with no BELIEF marker.
2. **"the whole chain from the 0xE4 CAN byte to `sp` is memoryless, so `sp_raw` is exactly
   reconstructable offline"**. This is the basis of the instrument argument — the reason `sp_raw`
   needs no tap. Also inherited, also unmarked.

Both belong on adversary D's and B's surfaces to verify; my finding is that they are mislabelled
EVIDENCE-grade in a document that otherwise labels carefully.

Two smaller items in the same class: the docstring's "~16 deg of extra phase lag" at 3 Hz is not
computed by the script (it follows from the computed 15 ms, but is not asserted), and the K-ladder
table prints `f_c`, `tau` and group delay in Hz and ms as bare numbers, with the `TICK_HZ = 1000`
BELIEF that all of them rest on recorded only at the variable, not at the table.

**Docstring claims of torque, authority or cure: none found.** The "NO CLAIM MADE" section is accurate.
The claim it does make — "no gain moves, no clamp moves, no authority moves, no cal byte moves" — is
computed at `[7]` and `[9]` and is confirmed by my independent diff.

## F6 — partial-write hazard in the scratch path [EVIDENCE] · severity: LOW

The scratch branch writes the image, then the .rwd:

```python
Path(_scr, IMG_NAME).write_bytes(bytes(code))
Path(_scr, RWD_NAME).write_bytes(rwd)
```

My first attempt used a scratch directory deep enough that the .rwd filename (122 characters) crossed
the Windows 260-character `MAX_PATH` limit. The image was written; the .rwd write raised
`FileNotFoundError`; the script exited non-zero **leaving an orphan image on disk with no .rwd and no
hash echoed**. The same ordering exists in the `WRITE_MODE == "rwd"` branch, where the path is short
enough that this cannot currently trigger. Not a defect in the artifact; a robustness note.

## Non-finding, recorded because it looks like one

The docstring calls `0xC4FF0–0xC4FFB` "12 unidentified non-FF bytes". Four of them are identified:
`u16@0xC4FF8 = 0x0013` and `u16@0xC4FFA = 0x00B2` are the CRC chain's linked-list fields, read by the
kit's own walker, naming the block `[0x13000, 0x13000+0xB1FFC) = [0x13000,0xC4FFC)`. They are
correctly left untouched. Only the description is loose.

---

## What a FAIL would have looked like, and did not

| prereg FAIL condition for surface C | result |
|---|---|
| independent rebuild does not reproduce the hash | reproduced exactly |
| any diff byte outside the allowed set | 0 outside |
| any CRC in the chain wrong | 50/50 and 49/49 correct |
| more than one flashable V288 .rwd | exactly one |
| the census hides a false substantive claim | no false assertion found; overstated count only (F1) |

---
---

# REV 2 — re-run of the full surface #3 audit

**VERDICT: PASS.** No prereg FAIL condition for the build-script surface is met. The image and the
.rwd on disk are exactly what the script says they are, reproduced by an independent rebuild.

**One HIGH finding (R2-F1): the module docstring body is unrevised rev-1 text and contradicts the
emitted bytes about which telemetry bit carries the signal.** The build is correct; the document that
ships with it is not. This must be fixed before the artifact page and the handoff are written from it.

## R2-1. Hashes and rebuild [EVIDENCE]

| artifact | sha256 | claimed |
|---|---|---|
| `_v288r2_…SPFILT.K4.EINIT…_plain_image.bin` | `94cabdefd39a103ad10ec34b9c64b6ac94d6552b80bfe7cc192a8977cbbdbd8c` | matches |
| `39990-TVA,A160-V288R2-…rwd` | `43efd0c98446d331a5b529cbaf93f1173e61e9daa132903cf3467078a7207714` | matches |

Applying the four blobs to V282 and recomputing the owning block's CRC in my own code reproduces the
image hash exactly.

**Independently computed CRC cell: `f0 07 c2 4a`** (`crc32[0x013000,0x0C4FFC) = 0x4AC207F0`). Computed,
not assumed; it equals the cell in the built image and the value the brief expected.

## R2-2. Diff — 91 bytes in six runs, none outside the allowed set [EVIDENCE]

```
[0x029D72,0x029D76)   4 B  hook             6487ce95 -> 89078eae   (jr -> 0xC4C00)
[0x0C4BD6,0x0C4BDA)   4 B  cave exit        7f00ffff -> 80070600   (jr -> 0xC4BDC)
[0x0C4BDC,0x0C4BFE)  34 B  telemetry rung   ff..ff   -> 003a2437...7f00
[0x0C4C00,0x0C4C06)   6 B  filter prologue  ffffffffffff -> 243709932906
[0x0C4C09,0x0C4C30)  39 B  filter body      ff..ff   -> 7fe931c20d...4a51
[0x0C4FFC,0x0C5000)   4 B  CRC trailer      446bb04e -> f007c24a
```

Bytes outside the allowed set: **0**. `0xC4C06-08` is `ff ff ff` in both images, which is why the
48-byte blob splits into two runs, exactly as the brief predicted. `0xC4FF0-0xC4FFB` untouched. The
five existing 0x14A rungs at `0xC4B34-0xC4BD5` are **byte-identical**.

## R2-3. CRC chain, .rwd, determinism, disk [EVIDENCE]

- Full linked-list walk: **50 blocks, 0 mismatches**. Bootloader replay with the 0xC6000 bridge:
  **49 blocks, 0 mismatches**.
- The .rwd decodes (cipher recovered by brute force, not taken from the builder) to a payload
  **byte-for-byte equal to the image over `0x13000-0x100000`**. Its trailer `13 c8 d4 04` is the
  correct little-endian sum-32 of the body (`0x04D4C813`).
- Three runs, one dry and two writing to separate scratch directories, all exit 0 and produce
  byte-identical files matching the on-disk artifacts. Logs identical once the path is normalised.
- **Disk hygiene: clean.** Exactly one flashable V288 .rwd (rev 2). Rev 1's image and .rwd both now
  carry the `SUPERSEDED-DO-NOT-FLASH` prefix, as does V287 rev 1. A content-hash sweep of the whole
  firmware tree finds **zero** files matching the interim sar-prologue hashes `877ba3b9…` / `9e54f2fd…`.

## R2-4. The mirror is EXACT against the emitted bytes [EVIDENCE]

The brief asked for an exact compare. I wrote a small V850E2 interpreter that decodes and executes the
actual bytes at `0xC4C00-0xC4C2F` read out of the built image, with no knowledge of what the cave is
meant to do, and compared its result to the script's `sp_filter_tick` over **107,363 cases**: an
exhaustive sweep of the setpoint band, a dense sweep of the state, every sentinel boundary value, and
40,000 random 32-bit triples.

**0 mismatches.** The mirror's per-line addresses also match my independent disassembly one for one,
`0xC4C00` through `0xC4C2C`. Read straight off the emulator:

| marker | sp | y[n-1] | y[n] | meaning |
|---|---:|---:|---:|---|
| sentinel | 1032 | -1032 | 1032 | engage-init seeds y := sp |
| 0 | 1032 | 0 | 64 | first tick of the lag, 1032/16 |
| 0 | 0 | 1 | 0 | converges from above |
| 0 | 1 | 0 | 1 | rounding fix, no stuck LSB |

The script's `[4c]` assertion pinning the mirror's addresses to the emitted layout is a genuinely new
substantive check and it does what it claims.

## R2-5. Census — much improved, 17 residual [EVIDENCE]

The script now carries the fourth bucket I recommended and applies it honestly:

| bucket | script | mine |
|---|---:|---:|
| substantive | 166 | 149 |
| entailed by a sibling | 243 | 260 |
| vacuous (base sha256) | 41 | 41 |
| tautological | 29 | 29 |
| **total** | **479** | **479** |

The brief quoted 165 substantive; the script prints 166. The 17 I move are the `dec :` arm of section
`[11]`: section `[10]` already asserts `bytes(dec) == bytes(code)`, so re-running the non-readback
checks over `dec` cannot fail independently. This is an 11 % overstatement against rev 1's 270 %.
**No assertion has a false predicate.**

## R2-6. FINDING R2-F1 — the docstring contradicts the bytes on the telemetry bit [EVIDENCE] · severity: HIGH

The rev 2 *header* (lines 1-60) is excellent: it names rev 1's two failures, explains that stock frame
builders at `0x55AC0`/`0x55AE8`/`0x55B06` write byte-4 bits 2, 1 and 0 before the cave runs, and states
that rev 2 therefore moves the signal to bit 5, redefining V282's `|r24| >= |aggregator sum|`
comparator. My disassembly of the built bytes confirms exactly that: `mov 0x2,r7 ; shl 0x4,r7` makes
`0x20`, and `andi 0xdf` clears bit 5 and nothing else. The runtime `[13]` bit map printed at the end of
the run is also correct and complete.

**But the docstring body from `=== THE EDIT ===` onward was never revised.** It still describes rev 1:

1. `(2) FILT the filter cave, 34 bytes` — rev 2's filter cave is **48 bytes at 0xC4C00**. The 34-byte
   blob is now the telemetry rung.
2. `(4) TELE 32 bytes: one new sign rung, sign(gp-0x6a32) -> 0x14A byte 4 bit 0` — the telemetry rung
   is **34 bytes** and writes **bit 5**.
3. The "FOUR changed regions" walkthrough **omits the engage-init prologue entirely**, which is rev 2's
   headline fix.
4. The INSTRUMENT section states: *"bits 2-0 are written by nothing. Bit 0 is the lowest free."* This is
   **verbatim the false claim that the same file's header declares was FAIL A**, repeated as fact about
   160 lines later.
5. The "WHAT A NULL LICENSES" paragraph — the operator's instruction for decoding the drive — names
   **bit 0** three times: the zero-crossing lag "between bit 0 on the wire", and "if it reads 0 ms, or
   bit 0 is stuck, the cave did not execute".

**Why this matters more than a typo.** Point 5 is the build's interpretation contract, written before
the cut precisely so the drive can be scored. Bit 0 on the wire is a stock Honda flag driven by
`gp-0x679a`. An operator or agent following the docstring would decode a signal that has nothing to do
with the filter, and would reach a confident wrong verdict in either direction: a stuck-looking bit 0
read as "the cave did not execute", or a toggling bit 0 read as the filter running. The kit's own
design law makes the instrument, not just the lever, part of the build.

This does not change a byte of the image, so it is not a prereg FAIL. It is a blocking defect for the
close-out, because the artifact page and the handoff are written from this text.

## R2-7. Status of my rev 1 findings

| # | finding | rev 2 |
|---|---|---|
| F1 | census overstated 3.7x | **FIXED** — ENTAILED bucket added; 17 residual (R2-5) |
| F2 | `(mask\|0xF8)` predicate blind to bits 7:3 | **FIXED** — now `mask\|0xF8 == 0xFF and (~mask & 0xFF) == NEW_BIT`, which genuinely tests that stock bits 2:0 are preserved and pins the new bit |
| F3 | `f"SPFILT.K{K}" in TAG` tautology labelled S | **STILL PRESENT** (line 896) |
| F4 | dead conjunct `t_hi + (STRUCT_LO - t_hi) >= 0` | **STILL PRESENT** (line 1160) |
| F5 | GATE 2 "`sp` is in NO loop" stated as fact, unmarked | **STILL PRESENT** — unchanged text, and rev 2 adds no computation for it |
| F6 | scratch path writes image before .rwd | **STILL PRESENT** (line 1572) |

## R2-8. What a FAIL would have looked like, and did not

| prereg FAIL condition for surface C | result |
|---|---|
| independent rebuild does not reproduce the hash | reproduced exactly |
| any diff byte outside the allowed set | 0 outside |
| any CRC in the chain wrong | 50/50 and 49/49 correct |
| more than one flashable V288 .rwd | exactly one |
| the census hides a false substantive claim | no false predicate; 17 residual overstatement |
