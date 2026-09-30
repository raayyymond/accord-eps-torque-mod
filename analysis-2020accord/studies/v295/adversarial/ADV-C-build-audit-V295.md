# ADV-C — V295 build-script audit (adversary C)

Subagent, 2026-09-30. Job: make the V295 build FAIL on the build-script surface.
- Nothing was flashed. No CAN or UDS traffic was sent. Nothing was committed. No Ghidra call mutated the database: only
  `decompile_function` and `read_memory` were used, and nothing was saved.
- Not edited: STATE, CLAUDE.md, memory, BUILD-LINEAGE, the golden model, the build script, any firmware file.
- FAIL criteria F1–F11 were written **before** any computation: `ADV-C-CRITERIA.md`.
- Every decision-bearing claim is marked **[E]** EVIDENCE (with its method) or **[B]** BELIEF.

## 0. Verdict: **PASS_WITH_DEFECTS**. None of F1–F11 fired.

The on-disk V295 image is what the decision says: **V294 plus the u16 at 0xC63EA 567 → 1050, plus the recomputed
trailer of block [0xC6000, 0xC6FFC), and nothing else.**
- My own rebuild reproduces the image, using my own edit, my own CRC-32 and my own chain walker.
- My own decoder turns the `.rwd` back into the image.
- Every decision-bearing number in the docstring re-derives from the image with an integer mirror I wrote from the
  decompile.

The defects (§8) are all about the build's own assertion set and its wording, not the bytes:
- The "16 substantive" census overcounts. About 8 checks are independent tests of this edit.
- The rwd path is never mutation-tested by the script.
- A wrong decision constant at ±1 count is invisible to every one of its 108 assertions.
- A few docstring numbers are cosmetic or unreproducible.

**What this pass cannot say:** this pass covers the build-script surface only. Arithmetic (A), units (B) and
interlocks/downstream (D) are other adversaries' surfaces. Nothing here says how the car will feel.

**Hashes, re-hashed at the start and again at 12:44 [E: `sha256sum`, and hashlib in `advC_1`]:**

| file | sha256 |
|---|---|
| V295 plain image | `5c044d65763140525a2c3651ded72e1e2111cd81ca8b41334366605fb40452ed` (1,048,576 B) |
| V295 rwd | `f42a06bda5a737eb9f678d617603745ec21fb93c4bd229344f33259cfbeaae87` (986,042 B) |
| V294 image (base) | `3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85` |
| V294 rwd (the revert path) | `a2b418f061160f66ffaa8ac541a478d43771fcbd004a92dc3d7a071cfd9f706a` |
| V293 image | `f75e77cf…1db17` |
| stock `code.bin` | `3f1d55a9…fd822` |
| V282 image | `0ea98d06…5d0fe` |

## 1. FAIL criteria, result

| id | FAIL if (abridged; full text in `ADV-C-CRITERIA.md`) | result |
|---|---|---|
| F1 | on-disk V295 / V294 hash ≠ the reported one | silent [E] |
| F2 | my own rebuild ≠ the on-disk V295 | silent: **byte-equal over the whole 1 MiB** [E] |
| F3 | any V295-vs-V294 byte other than 0xC63EA-EB + the owning trailer, or any code byte | silent: exactly 6 bytes [E] |
| F4 | 0xC63EA ≠ 1050 LE, or a neighbour moved | silent [E] |
| F5 | any CRC block fails under my walker | silent: 50/50 full, 49/49 bootloader [E] |
| F6 | my rwd decode ≠ the image, bad checksum, or a header/shape change vs V294 | silent [E] |
| F7 | more than one V295 rwd or image, or the V294 revert rwd missing or changed | silent [E] |
| F8 | a decision-bearing numeric claim is false from the image | silent: all reproduce (§6) [E] |
| F9 | a claimed mutation is not caught, or one of my two mutations passes | silent. My M1 and M2 are caught. Probe M4 missed, as the pre-registered caveat anticipated → DEFECT (§5) [E] |
| F10 | the cumulative non-stock delta omits a cell or states a wrong value | silent: all 2,182 stock→V295 bytes attributed, table values correct (§7) [E] |
| F11 | anything else changed in either repo | silent (§9) [E] |

## 2. My own rebuild [E: `advC_1_rebuild_crc_rwd.py`, no kit import; output `out/advC_1_out.txt`]

**CRC scheme, derived from the bootloader in stock `code.bin`.**
- **The walk: `FUN_0000b006`, Ghidra decompile.**
  - The head descriptor is at END−8 (u16 start page) and END−6 (u16 page count), and len = pages·4K − 4.
  - The trailer is a u32 LE at start+len. The next descriptor is at start−8 / start−6.
  - The walk stops at the region start, and bridges `0xC6000 → [0x13000, +0xB1FFC)`.
- **The primitive: `FUN_0000ae4c`, the hardware CRC unit.**
  - It feeds 32-bit words to 0xFFFFFA00 and reads the result from 0xFFFFFA04. The seed is `local_14 = -1`, and there is no
    software final XOR.
- **The constants, read from the bytes myself.**
  - They are three **6-byte `mov imm32`** at 0xB06E / 0xB078 / 0xB07E, forming 0xC6000, 0x13000 and 0xB1FFC.
  - ⚠ The kit's `lib/verify_bootloader_crc.py` docstring calls these "movea 0x6000 / movhi 0x000C". The halfword `0x0622`
    at 0xB06E is Format VI `mov imm32, r2`. The constants are the same; only the label is wrong. My first decoder made
    the same mistake, and a positive check caught it.
- **The CRC arithmetic.** I wrote my own table-driven reflected CRC-32 (poly 0xEDB88320, init and xorout 0xFFFFFFFF).
  - Check value: `crc32("123456789") = 0xCBF43926`.
  - It reproduces **all 50 stock trailers**. The 50 blocks tile [0x13000, 0x100000) with no gap.
  - The bootloader's bridged main block [0x13000, 0xC4FFC) equals the linked-list main block. The only block outside the
    bootloader walk is [0xC5000, 0xC5FFC).
  - The hardware unit's internal final XOR is inferred from that 50/50 match [B on silicon internals; E on the result].
- **Results.** Stock, V293, V294 and V295 each pass **50/50 full chain + 49/49 bootloader walk**, and the block table is
  identical on all four.

**The edit.**
- **tp from the image's own boot code.** Executing 0x140C0–0x140D6 myself (`ori`, `movhi`, `movea`, `add` ×2) gives
  tp = 0xBF000 and gp = 0xFEDF8000.
- **The address.** Decoding 0x28F86 myself: hw1 `87e5`, hw2 `73eb`, op6 0x3F, reg1 r5, hw2[0] = 1. That is
  `ld.hu 0x73EA[tp], r16`, which reads **0xC63EA**, where V294 holds 567.
- **The write.** I packed 1050 LE there, then recomputed **every** trailer in the chain with my own CRC.
- **Exactly one trailer moved:** [0xC6000, 0xC6FFC), 0xF3441165 → 0x8D982BD9.
- **Result: my rebuild's sha256 is `5c044d65…0452ed`, byte-equal to the on-disk V295 over the whole file.**

## 3. Full diffs, every offset attributed [E: `advC_1`, `advC_4`; full list `out/advC_4_stock_v295_every_offset.txt`]

**V295 vs V294, WHOLE FILE (0 to 1 MiB): 6 bytes.**

| offset | V294 | V295 | what |
|---|---|---|---|
| 0xC63EA | 37 | 1a | gain b, low byte |
| 0xC63EB | 02 | 04 | gain b, high byte (567 → 1050) |
| 0xC6FFC–FF | 65 11 44 f3 | d9 2b 98 8d | trailer of [0xC6000, 0xC6FFC) |

- The neighbours are unchanged: 0xC63E8 (a) = 1011 and 0xC63EC (output-lag a) = 992.
- Nothing below 0x13000 changed, and nothing in [0x13000, 0xC0000).

**V295 vs V293 over [0x13000, 0x100000): 314 bytes, all attributed.**
- V294's code edits: 0x28FA4 (add→subr) and 0x29D76 (shl 5→2), 1 byte each.
- V294's cal edits: C 0xC62E7, 1 byte; a 0xC63E8, 1 byte.
- b 0xC63EA-EB, 2 bytes.
- Kp bank Y on all 28 records: 280 bytes (120 → 960).
- 7 CRC trailers: 0xC4FFC, 0xC6FFC, 0xE4FFC–0xE8FFC, 28 bytes.
- Unattributed: none.

**Stock vs V295 over [0x13000, 0x100000): 2,182 bytes, all attributed. 0 unattributed.**
- 2,139 bytes were last set at or before V282, in V282's rows R1–R28, matched by address.
- 114 were last set by V293: Kd Y (112), D clamp (1), r24 arm (1).
- 307 were last set by V294: Kp Y (280), the two opcodes, C, a, and 23 trailer bytes.
- 6 were last set by V295: b (2) and the trailer (4).
- The stock vs V282 set is exactly the V282 document's census of 1,984 bytes.
- Every stock^V295 byte lies in stock^V282 ∪ V282^V293 ∪ V293^V294 ∪ V294^V295.
- V282→V293 is fully accounted for by V293's five edits plus trailers.
- Two bytes are non-stock on V282 but stock again on V295, both coincidences:
  - 0xC6446 is the r24 low byte, which is 0x00 in both 512 and 2048.
  - 0xE8FFE is a trailer byte.

## 4. .rwd, my own decoder [E: `advC_1` §E]

- **Container.** It starts `1\r\n`, followed by six tag-delimited header fields:
  - `#`: `\x00`
  - `?`: `A1`
  - `/`: `39990-TVA-A110`, `39990-TVA,A160`
  - `!`: `001100121020` ×2
  - `&`: `BF109E`
  - `%`: `30`
- **Layout.** The header is 118 B. After it come 7,584 chunks of 130 B each: address = b0<<12 | b1<<4, then 128 data bytes.
  They are contiguous over **exactly [0x13000, 0x100000)**. The trailer is a u32 LE additive sum of every preceding byte;
  it checks on both V294 and V295.
- **Cipher, not taken from the kit.**
  - I learned the byte substitution from the **flown** V294 rwd/image pair. It has 256 codes, is a bijection, and has
    0 conflicts. V294 flew on r71b, and `studies/v295/flight/V294-FLIGHT-ATTRIBUTION-r71b.md` shows the wire is V294.
  - A brute force over op triples finds that the table **equals the header's own keys applied as
    (xor 0xBF, xor 0x10, sub 0x9E)**, a unique match among the 27 op triples. It also equals the precedent redo's formula.
- **My decode of the V295 rwd equals the V295 image over [0x13000, 0x100000).**
- **Rwd V294 vs V295: 7 bytes differ.**
  - 6 map to image offsets 0xC63EA, 0xC63EB and 0xC6FFC–FF. The 7th is the container checksum.
  - Headers are byte-identical: same part numbers, keys and length. The container V294 flew in is unchanged.

## 5. The assertion census, and mutations

**The script's own dry run** [E: run by me, `out/advC_build_script_dry.txt`] reproduces all of its reported numbers:
- 108/108 pass, census 16 S / 36 C / 52 V / 4 T.
- The zero-edit control reproduces V294's sha.
- **10/10 mutations are caught, with fire counts identical to the builder's report table.**
- The predicted hashes are the on-disk ones.

**My re-census of the 108**, checked assertion by assertion against the printed list. Numbers are assertion ordinals in
print order: #1–43 is [1], #44–51 [2], #52–65 [3], #66 [4], #67–70 [5], #71–74 [6], #75–77 [7], #78–82 [8], #83–86 [9],
#87 [10], #88–90 [11], #91 [12], #92–93 [13], #94–97 [14], #98–108 [15].

| class | builder | mine | the difference |
|---|---|---|---|
| substantive, and independent for THIS edit | 16 | **8** | #68 CRC full chain · #72 diff exactness vs the decision · #84 int32 march audit · #86 settled T = V294 · #87 int32 margin · #90 restart ≤ 288 · #91 \|P/x\| ±1 % + ×3 guard · #95 rwd readback |
| substantive but redundant | — | 4 | #69 bootloader walk: entailed by #68 on this image, since the block tables are equal · #71 stray bytes: entailed by #72 · #88 pre-bail settle: a harness precondition, near-duplicate of #85 · #97 re-splice: same B_CELL/B_NEW constants, only the CRC locator differs, never mutation-exercised |
| mislabelled S | — | 3 | #1 base sha: an input pin that cannot fail on a wrong edit (M3 shows it guards the base) · #93 tag: a readback of b through the reader formatted as a string (T), the other fields V · #96 cipher vs V38: tests the tooling (C) |
| r26 → 0 (#85) | S | S for pole mutations, **vacuous for any b-only edit** | a washout with a stable pole settles for every b |
| constant-check | 36 | 36 (+#88, #96) | agreed |
| vacuous / entailed | 52 | 52 (+#69, #71) | agreed; the 482-cell surface is vacuous by construction, since b is not read at constant r26 |
| tautological | 4 | 5 (+#93); #95 is half-tautological | #95 round-trips through a table and its inverse, so it catches container and chunking errors but not a wrong cipher. #96 covers the cipher |
| stale | 0 | **0 stale values** | Every hard-coded expectation I checked is correct from the images: the FROZEN cells, the adjudicated census sets (scanned on the base; the code region is identical), 44.90, 2461/−2463, the stock rows, 16.125736. Two stale labels: `out/v295_write.txt` shows the pre-fix 17/51 (acknowledged), and `RESTART_CAP = 288 # 2 x V294's 144 T` while the image gives V294 144/145 at zero command by sign, so the cap is 2×min |

**The script's mutation test never runs the rwd path or [15].** It calls `build(do_rwd=False)`, so blocks [14] and [15]
never see a mutated image.

**My mutations** [E: `advC_3_mutations.py` → `out/advC_3_out.txt`; they run through the script's own `build()`]:

| # | mutation | result |
|---|---|---|
| **M1** (mine) | CRC-consistent stray edit in **another block**: the live map knot at 0xE504C 275→276, added to `attributed` so the script re-CRCs block 0xE5000 itself. The CRC walkers cannot see it | **CAUGHT ×5**: owning-block check (C), stray-byte and diff-exactness (S), surface 64 cells and slope 0.6408 (V) |
| **M2** (mine) | **rwd payload corrupted with a valid container checksum**: encoded byte for 0xC63EA flipped before `encode_x31` builds the checksum | **CAUGHT ×1**: only #95 (rwd readback) fires. It is a single guard in the 108. The write path's post-write re-decode is a second, uncounted guard, and my own decoder a third |
| M3 (probe) | base = V294 with one filler byte flipped below 0x13000 | CAUGHT ×1: only #1 (base sha) |
| M4 (probe) | the **decision constant itself** is 1051 (`B_NEW` = 1051, b = 1051) | **MISSED: 0 of 108 fire.** At b 1051 the restart pulse is 288 ≤ 288 (§6), and the \|P/x\| tolerance and the tag both key off `B_NEW`. Pre-registered as a DEFECT, not a FAIL: the on-disk image carries 1050, confirmed by my independent rebuild |

## 6. Every decision-bearing numeric claim, from the image

**Method** [E: `advC_2_numeric_claims.py` → `out/advC_2_out.txt`; no kit import]:
- I wrote my own integer mirror of `FUN_00028ea6` from the decompile (saved at `scratchpad/dec_28ea6.c`).
- Cells are read from each image; b, a and G are resolved through their reader instructions (0x28F86, 0x28F8A and
  0x2A1EE `ld.h 0x7cd0[tp]`).
- **Assumptions carried** [B, the same ones the golden model makes]:
  - the gp-0x6b2c hold term is 0;
  - direction gp-0x6752 = +1;
  - ramp = 0x8000;
  - fade indices at rest (FADE = 254 for **all four** table pairings, read);
  - variant slot 7;
  - bail = sentinel 2 with S = 0, then s_old = 0.

| claim (docstring / report) | re-derived | verdict |
|---|---|---|
| rail +2461 / −2463; V295 surface = V294 at r26 = 0 | +2461 / −2463; 482/482 equal; all 8 printed idx rows equal | ✓ |
| zero-command trim cap 616 | −616 / +615 at r26 = ±C | ✓ |
| sub-rail slope 0.6410 (brief: 0.6409) | **0.64100** | ✓ (0.6409 is a rounding slip in the brief) |
| K_α 0.210 → 0.388 | 0.2097 → 0.3884 | ✓ |
| \|P/x\| 20 Hz 2.079 → 3.850; 2.4 Hz 1.594 → 2.953 | 2.0790 → 3.8500; 1.5944 → 2.9525; ratio 1.8519 < ×3 | ✓ |
| V282 grinder 44.90 | **44.90 recomputed from the V282 image** (a 923, b 1560, add, shl 5, Kp 248, Kd 128); V295 is −21.3 dB below it | ✓ |
| int32 margin 4.058 → 2.191; max \|a·s\| 979,917,816; b_max 1150 | 4.0581 → 2.1915; 979,917,816 exactly; 1150. The guard `0x2ee0+x < 0x5dc1` admits \|x\| = 12000 | ✓ |
| full lane, 2892 lanes: r26 → 0, settled T = V294 | yes and yes | ✓ |
| restart pulse 165 → 287 worst (idx 227), 145 → 269 at zero command, ratio ×1.932, 0 lanes > 288 | all identical; **14 lanes tie at 287**; peak at tick +42 | ✓ |
| "~0.1600 T per P-count" | 0.16029 | cosmetic |
| "~97 % in phase with rate at 2–3 Hz"; "~1.85 → ~3.4 T per deg/s" | 2.4 Hz phase ≈ 15° → cos 0.966; ≈ 1.85 → 3.42 | ✓ (hand arithmetic from the same transfer functions) |
| "trim reaches C at ~1500 deg/s², ~118 deg/s of 2 Hz-band rate" | 1,585 deg/s²; **no frequency gives 118**: 124 deg/s at the HF limit, 150 at 3 Hz, 177 at 2 Hz | DEFECT (non-decision-bearing) |

**Margin sensitivity on the restart cap** [E, same mirror]. This is the "1 T margin" made concrete:

| b | 1040 | 1045 | 1049 | 1050 | 1051 | 1055 | 1060 |
|---|---|---|---|---|---|---|---|
| worst pulse, T | 285 | 286 | 287 | 287 | **288** (passes ≤ 288) | 289 | 290 |

**Scale sensitivity at 100 deg/s:**

| x counts | 760 | 800 | 808 | 816 | 840 |
|---|---|---|---|---|---|
| worst pulse, T | 274 | 287 | 290 | 293 | 301 |

- The 8.00 counts per deg/s scale is inherited EVIDENCE (0x14A field −x>>3; not re-derived here).
- The wire measured 7.1–7.8, so 8.00 is the conservative end. The cap is a fault-path policy bound, not a physical limit.

## 7. The cumulative non-stock delta table [E: `advC_2` §6, stock dump vs V295 image]

**Cells that match, stock → V295:**

| cell | address | stock | V295 |
|---|---|---|---|
| fb clamp C | 0xC62E6 | 7680 | 1024 |
| a | 0xC63E8 | 923 | 1011 |
| b | 0xC63EA | 1560 | 1050 |
| D clamp | 0xC61B6 | 10240 | 0 |
| r24 arm | 0xC6446 | 512 | 2048 |
| Ki | 0xC63E6 | 0 | 0 |
| clamps | 0xC61B2 / B4 | 512 | 3072 |
| lockout | 0xC62EA | 320 | 0 |
| biquad enable | 0xC649B | 0 | 1 |
| DTC-0x49 gate | 0xC64B8 | 112 | 255 |
| square-wave hold (a byte cell) | 0xC64DE | 17 | 27 |
| output lag | 0xC63EC / EE | 992 / 507 | unchanged |
| P and sum clamps | — | 15360 | unchanged |

- **Opcodes:** `add` (d1c9) → `subr` (d189), and `shl 0x5` (82c5) → `shl 0x2` (82c2).
- **Kp:** stock slot 7 [248, 512, 645, 696, 696] → **960 flat on all 28 records**.
- **Kd:** stock [128]×4 → **0 on all 28 records**.
- **Map slot 7:** Y [0, 24, …, 172] → [0, 52, 86, 103, 138, 275, 413, 550, 688, 1032], with X unchanged.
- **Setpoint ceiling:** 15360 → 16384.
- **The stock-dump trap at 0xC6CD0 is handled correctly.**
  - Stock's `ld.h` at 0x2A1EE reads **0xC646C = 891**. The raw stock-dump bytes at 0xC6CD0 are blank 0xFFFF, which reads
    −1; V57 created that cell.
  - V295's `ld.h` reads **0xC6CD0 = 5346**, and 0xC646C is still 891.
  - Neither the docstring nor [15] claims a stock value for 0xC6CD0.
- **Per-build deltas as stated in the docstring, verified V282→V293→V294:**
  - V293: C 46080 → 0; D clamp → 0; r24 5244 → 2048; Kp → 120 on all 28; Kd → 0 on all 28.
  - V294: add → subr; shl 5 → 2; C 0 → 1024; a 923 → 1011; b 1560 → 567; Kp → 960 on all 28.
- **The V282 rows are byte-identical V282 → V295.** I checked 27 windows: version marker, repoint, biquad arm, rate-lane
  gate, 0x454FE, hook, cave body, 427 tap, 0xC6CD0, clamps, EME int and float, relay, debounces, lockout and hold. The
  cave's sha8 is `e9596ad9`, the same as V293/V294.

## 8. Defects (reported, not fixed; none blocks)

1. **The census overstates "substantive": 16 claimed, about 8 independent tests of this edit** (§5).
2. **The rwd path is never mutation-tested.** `mutation_test` passes `do_rwd=False`. M2 shows that #95 is the only one of
   the 108 guarding the rwd payload.
3. **No assertion anchors the dose to anything but the constant `B_NEW`** (M4 missed; (b) 1051 is caught only by
   readbacks).
   - At b = 1051 the H-SAFE-3 gate reads exactly 288 and passes, so the dose sits on the design boundary by construction.
   - The hash pin and my rebuild are what fix it at 1050.
4. `RESTART_CAP = 288` is annotated "2 × V294's 144". The image gives V294's zero-command pulse as 144/145 by sign, so the
   cap is 2×min; 2×max would be 290. Cosmetic.
5. Docstring §0b rounds the forward factor to "0.1600"; it is 0.1603.
6. Docstring §0b says "~118 deg/s of 2 Hz-band rate". This does not reproduce from the image at any frequency (≥ 124).
7. Docstring §3(b) says "~545 T (linear scaling of V294's march)". Linear ×1.852 of 309 is 572; 545 is sub-linear.
   Adversary D's `d4_replay_out.txt` gives V295's engaged max as 554 from a clamped replay, so the label "linear" is
   inaccurate [B: the source of 545 was not traced].
8. The brief's "sub-rail slope 0.6409": the image gives 0.64100.
9. Kit-wide, not V295: the `lib/verify_bootloader_crc.py` docstring labels the 6-byte `mov imm32` at 0xB06E as a
   movea/movhi pair.
10. Stale label: `out/v295_write.txt` carries the pre-fix census 17/51. The builder acknowledged it, and the hashes are
    unaffected.

## 9. Artifacts, naming, revert path, repo state [E: glob, `sha256sum`, `git status --porcelain --ignored`, `find -mtime -1`]

- **Exactly one V295 plain image and one V295 `.rwd`**, searched case-insensitively and with any prefix across the whole
  firmware repo.
- **Names** follow V294's convention.
  - The tag fields re-derive from the image: B1050, SUBR, SHL2, C1024, POLE 2.0 Hz (2.033 Hz), a 1011, b 1050, Kp flat 960
    on all records, Kd 0, r24 2048.
  - The part number `39990-TVA,A160` and the range `0x13000-0x100000` match the header's `/` field and the payload span.
- **The V294 revert rwd** is present, single, and still `a2b418f0…9f706a`.
- **accord-firmwares:** only the two V295 files are untracked; 0 tracked changes. Only `__pycache__` is ignored. These
  two are the only files modified in the last 24 h.
- **Kit:** 0 tracked changes. Untracked files are `build_v295_tva.py` and `studies/v295/`, which includes the other
  adversaries' `advA/`, `advB/` and `advD/`.
- **Ghidra:** the V294 program's bytes at 0x28FA4 (`89d1`), 0x29D76 (`c282`) and 0xC63E8 (`f3033702`) equal the file, so
  it is not stale.

## 10. Files

**Scripts** (all under `analysis-2020accord/studies/v295/adversarial/`):

| script | what it does | output |
|---|---|---|
| `advC_1_rebuild_crc_rwd.py` | hashes, bootloader CRC derivation, my rebuild, diffs, rwd decode | `out/advC_1_out.txt` |
| `advC_2_numeric_claims.py` | my lane mirror, every numeric claim, the delta table | `out/advC_2_out.txt` |
| `advC_3_mutations.py` | M1–M4 through the script's `build()` | `out/advC_3_out.txt` |
| `advC_4_stock_attribution.py` | all 2,182 stock→V295 bytes | `out/advC_4_out.txt`, `out/advC_4_stock_v295_every_offset.txt` |

**Other files:**
- `out/advC_build_script_dry.txt`: the build script's own dry run with its mutation test, run by me. It wrote nothing.
- `ADV-C-CRITERIA.md`: the FAIL criteria, written first.
- The Ghidra decompile of `FUN_00028ea6` I used for the mirror is in the session scratchpad as `dec_28ea6.c`.
  Adversary D keeps an equivalent copy at `advD/ghidra_v294_FUN_00028ea6_decompile.c`.
