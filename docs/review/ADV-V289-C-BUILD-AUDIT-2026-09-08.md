# Adversary C — build-script audit of V289 rev 1 — 2026-09-08

**VERDICT: PASS on surface C (build-script audit), with conditions on the TEXT only.** No prereg §C
FAIL condition is met. The image and the .rwd on disk are exactly what the script says they are,
reproduced by an independent rebuild that shares no code with the builder. The conditions (F1–F4
below) are documentation defects in the module docstring and one dead switch; **none changes a byte
and none blocks flashing.** They must be fixed before the artifact page and the handoff are written
from the docstring, because the V288 close-out showed that text propagates.

Prereg: `docs/review/ADVERSARIAL-V289-PREREG-2026-09-08.md` §C. Scripts under
`analysis-2020accord/verify/`: `adv_v289_c_rebuild.py` (rebuild, CRC chain, .rwd decode, diff, tag),
`adv_v289_c_census.py` (assertion census on a captured log), `adv_v289_c_initswitch.py` (the
`INIT_ON_SENTINEL` path). Everything below is EVIDENCE unless marked BELIEF.

---

## 0. Method

The rebuild uses a fresh V850E2 assembler written from the ISA field layout (Formats I, II, III, V,
VI, VII, XI). The cave and tail were transcribed as **mnemonics** from the builder's declared listing
(its semantic claim) and assembled by my code, so an encoder bug in the builder cannot be inherited.
The CRC chain walker was re-implemented from the bootloader description (END−8 / END−6 fields,
backward linked list, the verified 0xC6000 bridge). The .rwd was parsed by my own x31 reader and its
cipher recovered by brute force over the 6 key permutations × 512 op triples, matching the first
128-byte chunk against the image. Nothing was imported from `build_v289_tva.py` for C1/C2/C4.

## 1. Hashes [EVIDENCE]

| artifact | sha256 | claimed |
|---|---|---|
| `_v289_…SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ…_plain_image.bin` | `f0c10c29752d2b9bc4ec510800cd4de58166ebbb87f05613b5ee8e7af339a3ed` | matches |
| `39990-TVA,A160-V289-…-0x13000-0x100000.rwd` | `20fa175721eb9712cd9aada27c6ecc84e43108fcdd0c21d387b80db4a105625c` | matches |
| V282 base | `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe` | matches |
| **my independent rebuild** | `f0c10c29…339a3ed` | **identical** |
| **.rwd decoded by my parser, over [0x13000,0x100000)** | == image and == my rebuild, byte for byte | **identical** |

## 2. C1 — independent rebuild reproduces the hash [EVIDENCE] → not a FAIL

My assembler produced, from the mnemonics alone:

```
hook   jr 0x2A174 -> 0xC4C00      89 07 8c aa   (d = 0x9AA8C -> hw1 0x0789, hw2 0xAA8C)
exit   jr 0xC4BD6 -> 0xC4BDC      80 07 06 00   (d = 6)
cave   140 B at 0xC4C00, 52 instr; penultimate = e5 3f ef 73 (the displaced ld.hu, byte-identical)
return jr 0xC4C88 -> 0x2A178      b6 07 f0 54   (d = -0x9AA10 -> 0x3651F0)
tail   28 B at 0xC4BDC, ending 24 36 e8 ea 7f 00 (Honda's movea -0x1518,gp,r6 ; jmp [lp])
```

All 60 listing lines the script prints match the bytes on disk. Both cal cells applied as halfwords
(923→875, 1560→2301). **CRC cells recomputed by me:** `0xC4FFC = a7 61 1f 82` (crc32[0x13000,0xC4FFC)
= 0x821F61A7) and `0xC6FFC = 77 04 78 fe` (crc32[0xC6000,0xC6FFC) = 0xFE780477). Both equal the cells
in the built image. Resulting sha256 identical to the artifact.

**CRC chain, my own walker:** the linked list from END−8/END−6 yields **50 blocks, 0 mismatches**;
the bootloader replay with the 0xC6000 → [0x13000,0xC4FFC) bridge yields **49 blocks, 0 mismatches**;
the one block the bridge skips is exactly [0xC5000,0xC5FFC). Exactly two blocks own edited bytes,
[0x13000,0xC4FFC) and [0xC6000,0xC6FFC); no edit lands on a trailer; the chain fields at
0xC4FF0–0xC4FFB (`010101010000c6001300b200`) are untouched.

## 3. C2 — full-file diff V282 → V289 [EVIDENCE] → not a FAIL

```
[0x02A174,0x02A178)   4 B  e53fef73 -> 89078caa      hook
[0x0C4BD6,0x0C4BDA)   4 B  7f00ffff -> 80070600      0x14A cave exit
[0x0C4BDC,0x0C4BF8)  28 B  ff..ff   -> tail
[0x0C4C00,0x0C4C0A)  10 B  ff..ff   -> 244fbd93246fc593cd6e   notch cave (run 1)
[0x0C4C0B,0x0C4C20)  21 B  ff..ff   -> ...                    notch cave (run 2)
[0x0C4C21,0x0C4C8C) 107 B  ff..ff   -> ...                    notch cave (run 3)
[0x0C4FFC,0x0C5000)   4 B  446bb04e -> a7611f82      CRC, code block
[0x0C63E8,0x0C63E9)   1 B  9b -> 6b                  fb pole a (high byte 0x03 unchanged)
[0x0C63EA,0x0C63EC)   2 B  1806 -> fd08              fb pole b
[0x0C6FFC,0x0C7000)   4 B  72dfea75 -> 770478fe      CRC, cal block
```

**185 bytes in 10 runs; bytes outside the prereg allowed set: 0.** Of the 188 touched bytes, three
equal their old value: `0xC4C0A` and `0xC4C20` (the `ff` byte of the two `andi 0x3fff` immediates) and
`0xC63E9` (0x03, the high byte of 923 and of 875). Fillers 0xC4BDA–DB and 0xC4BF8–FF are still 0xFF;
0xC4C8C–0xC4FEF is still free; the five flown 0x14A rungs at 0xC4B34–0xC4BD5 are byte-identical.

## 4. C4 — one flashable .rwd, name matches [EVIDENCE] → not a FAIL

Exactly one V289 .rwd and one V289 image exist across both trees; neither carries a SUPERSEDED prefix
and no other V289 file exists anywhere (V288 rev 1 and V287 rev 1 keep their prefixes). The .rwd
filename tag equals the image filename tag character for character. The x31 format embeds **no build
tag** — its headers are the part numbers `39990-TVA-A110` / `39990-TVA,A160`, the security keys, the
cipher key `BF109E` and the CAN byte `30`; that header block is **byte-identical to the V288 rev 2
.rwd's**. Payload: 7,584 contiguous 128-byte chunks 0x13000…0xFFF80; the 4-byte trailer
`38 dd d4 04` is the correct LE sum-32 of the body; the cipher recovered by brute force is
`((i ^ 0x10) ^ 0xBF) - 0x9E`, i.e. the known V9B table.

**Tag honesty.** Read from the image, the coefficients are b0 = 16048, b1 = a1 = −31842, a2 = 15712
(the three `movea` immediates at 0xC4C0E / 0xC4C3C / 0xC4C26). The numerator zero sits at
acos(31842/32096) → **20.036 Hz**; the tag says `20.05HZ`, the design target. The 0.014 Hz gap is
inside the Q14 quantisation grid (±0.05 Hz) and inside the census spread of the line (20.03–20.08).
Honest enough for a filename; **the docs and the artifact page should quote 20.04 Hz realised**, as the
docstring already does at 20.036.

## 5. Reproducibility [EVIDENCE]

Four dry runs (FAST ×2, `--full` ×2, none with a write mode set): every run exits 0; the two FAST logs
are byte-identical, the two `--full` logs are byte-identical, and both print the same image and .rwd
hashes as the artifacts. No wall-clock, path or dict-order dependence: the script imports no time
module, sorts every set it iterates for output, and prints a path only when `ACCORD_V289_SCRATCH` is
set. FAST = 475 assertions, `--full` = 483 (the extra 8 are the long emulator suites).

## 6. C3 — assertion census [EVIDENCE]

Script's own buckets on `--full`: **175 S / 234 E / 46 V / 28 T = 483**. My re-classification of the
same 483 lines:

| bucket | script | mine | note |
|---|---:|---:|---|
| S — about the built bytes or the toolchain | 175 | **92** | |
| D — arithmetic on design constants only, never reads the image | — | **55** | new bucket; falsifiable (a typo in a constant), but not evidence about the image |
| E — entailed by a sibling | 234 | 259 | +25 |
| V — entailed by the base sha256 | 46 | 45 | one moved to T |
| T — readback / constant-vs-constant / identity | 28 | 32 | +4 |

**No assertion has a false predicate. No assertion labelled S is entailed by the base hash or is a
readback of a write** — so the letter of C3's first clause is not met. The 28 moved out of S entirely:

- 10 × `[11] dec :` — the `dec` arm re-runs the decoder/emulator on the .rwd readback, but `[10]`
  already asserts `dec == code` (the same residual the V288 audit recorded).
- 11 × `[9]` — "every differing byte lies in the eight regions" and the ten "diff run … attributable"
  lines are all implied by `[7] stray == 0` (allowed set == attributed set).
- 2 × `[8]` "built image 50/50 / 49/49" — implied by base 50/50 [V] + stray == 0 + the two recomputed
  trailers [T]. 1 × `[10]` readback CRC, implied by `dec == code`.
- 1 × `[6]` "existing 0x14A rungs byte-identical" — region disjoint from every write; implied by `[7]`.
- 3 tautologies labelled S: `[3] tp+0x73e8 == 0xC63E8` (constant arithmetic), `[6] len(jr) == 4`, and
  `[9b]` "V289 vs V281r3 == V282's diff ∪ this build's diff modulo the shared cell" — a set identity
  that holds for **any** three byte strings (F5).

Hunts the brief asked for:

- **(a) circularity in "decoder vs Ghidra".** `GHIDRA_STOCK_LISTING` holds stock addresses only; it
  is not captured from the built cave. Not circular. But the cave uses four forms the listing does not
  contain — `jr`, `or`, `sub`, and register-to-register `mov` — while the check's message claims
  "incl. … jr". Mitigated by my assembler reproducing every byte and by `[5]` decoding the three `jr`
  targets; recorded as F4.
- **(b) emulator on built bytes or in-memory bytes?** The long suites run on `simb`, an in-memory copy
  of the base with the encoder's blobs applied, before CRC. I verified the on-disk image's bytes at
  0xC4BDC–0xC4C8B equal those blobs line for line (60/60), so the suites ran on the shipped cave bytes.
  The FINAL image and the .rwd readback are additionally emulated for 7 ticks each at `[11]`.
- **(c) docstring vs bytes.** Correct as built: TDF-II with error feedback, output clamp from
  0xC61BE, FLAG halfword at gp-0x6c3a, `INIT_ON_SENTINEL` False, cells gp-0x6c44/40/3c/3a, 28-byte tail
  at 0xC4BDC, 140-byte / 52-instruction cave 0xC4C00–0xC4C8B, hook bytes `89 07 8c aa`, 875/2301, two
  CRC trailers, 185 bytes / 10 runs, 50–51 instructions executed per tick, the bit map. **No text
  describes a different revision's bytes.** Three inaccuracies: F1 ("unit-tested"), F3 ("three
  notch-cave bytes"), and the stale census line (F2).
- **(d) the `INIT_ON_SENTINEL=True` path.** Dead switch — F1.

---

# Findings

## F1 — `INIT_ON_SENTINEL` is a dead switch, and "unit-tested" overstates the test [EVIDENCE] · MEDIUM (text only)

The docstring says the prologue "is encoded and unit-tested but NOT emitted". Flipping the constant
to True on a scratch copy makes the script **fail its own assertion at `[4](x)`** and stop with exit 1:
`notch_cave()` takes its default `init` from the switch, so both operands become the 166-byte cave and
`len(pro) == len(notch) + 26` is false. Had it passed, the `[4d]` docstring guard would fail next
(`140 bytes, 52 instructions` vs 166 / 59). The switch therefore cannot produce a build without
editing two assertions and the docstring — a false affordance in the sense the brief named.

The only "unit test" of the prologue in the script is that **length** check. I emulated the init=True
bytes with the builder's own emulator: the prologue assembles (26 B: `ld.w -0x6cf8[gp],r6 ; mov
0x7fffffff,r9 ; cmp r9,r6 ; bne +14 ; st.w r0 ×3`), the `bne` lands exactly on the body, the state is
zeroed **only** when gp-0x6cf8 == 0x7FFFFFFF (kept for 0, 0x7FFFFFFE, 0xFFFFFFFF), live registers and
`r7 == 507` are intact on both arms. So the prologue is sound; the claim that the script tests its
behaviour is not. Fix: either wire `[4](x)`/`[4d]` to the switch and add the behavioural test, or
change the docstring to "encoded and length-checked; not emitted".

## F2 — the census is overstated and the docstring's census line is stale [EVIDENCE] · LOW

Docstring: "Printed at the end (rev 1: 152 S / 234 E / 46 V / 28 T)". The script prints **167 S**
(FAST) / **175 S** (`--full`); the orchestrator's brief quoted 171 S of 479. None of the three agree.
My count is 92 S + 55 D (§6). Quote 92 substantive checks about the image, not 175, in the close-out.

## F3 — "three notch-cave bytes equal the 0xFF they replaced" is wrong by one [EVIDENCE] · LOW

Two cave bytes do (0xC4C0A, 0xC4C20); the third unchanged touched byte is `0xC63E9`, the 0x03 high
byte shared by 923 and 875. The arithmetic (185 of 188) and the run count (10) are right; the
attribution is not, and the same sentence reached the orchestrator's brief.

## F4 — the decoder's Ghidra positive control does not cover `jr`, `or`, `sub`, `mov reg,reg` [EVIDENCE] · LOW

The `[1e]` message claims "every form the caves use, incl. … jr". `GHIDRA_STOCK_LISTING` contains no
`jr`/`jarl` and no `or`/`sub`/register-`mov`. The decoder's reading of those four forms in the built
cave is therefore checked against the encoder's intent only. Independent cover exists (my assembler,
`[5]`'s target decode, the 5,000-site Format-V round trip on the encoder side), and adversary A's A4
is the Ghidra confirmation of the built cave, which this script never performs. Fix the message or
add four stock sites.

## F5 — `[9b]` cross-image identity is a tautology labelled S [EVIDENCE] · NEGLIGIBLE

For any images P, B, C: {C≠P} = ({B≠P} ∪ {C≠B}) − {x ∈ both : C[x] == P[x]}. The check cannot fail.

## Residuals recorded, not findings

- `independent_rebuild()` inside the script is a second encoder but shares the module constants and
  `FF.crc_block_map`; its agreement proves encoder consistency, not displacement correctness. My rebuild
  shares the constants too — whether gp-0x6c44..0x6c39 is the right RAM is GATE 1 (surface D).
- The 28 mirror-only checks (DC, decay, l1 worst cases, lock-in |H|) reach the bytes only through
  `[4a]`'s finite equivalence set (349 + 80 ticks FAST; +23,000 ticks `--full`, both branch arms
  exercised). Exhaustive equivalence is surface A.
- Scratch-path write order (image before .rwd) is unchanged from V288's F6.

## What a FAIL would have looked like, and did not

| §C FAIL condition | result |
|---|---|
| C1 rebuild ≠ hash, or CRC ≠ cell | reproduced exactly; both cells recomputed and equal; 50/50, 49/49 |
| C2 any byte outside the declared runs | 0 outside; 185 B / 10 runs |
| C3 a decisive assertion entailed by base hash or a readback; text of another revision | none; 28 sibling-entailed/tautological overstatements; text inaccuracies F1–F3 |
| C4 >1 flashable rwd, or name ≠ image | exactly one; tags equal; header == V288r2's |
