# ADV — ARITHMETIC — V296 (angle loop C3-rev2)

**Agent:** ADVERSARY ARITHMETIC, a subagent of `main`. **Date:** 2026-10-01.
**Target of the pass:** the BUILT V296 image. **Mandate:** re-derive the delivered surface
from the built image's bytes from scratch and try to make it **FAIL**; "do not flash" must be
structurally reachable, and the FAIL criteria are written down *before* the pass runs.

**Everything here is READ-ONLY.** I assembled nothing, relinked nothing, built nothing, wrote no
image / cave / cal / CRC / `.rwd`, sent nothing on a bus. I only parsed bytes already on disk.
Script: `adv_arith_v296.py` (beside this file). Method tag on every decision-bearing line:
**EVIDENCE** (with the method) or **BELIEF**.

---

## 0. What a FAIL looks like — written FIRST (from design §8, "any one → do not flash")

1. **No target.** There is no BUILT V296 image to re-derive. (If the subject of an "adversary on
   the built image" does not exist, the pass cannot certify it — a non-existent image is not a PASS.)
2. H1 bytes ≠ the §1.4 arithmetic on any input; or the delivered surface I reimplement from the
   image disagrees tick-for-tick with the common scorer's lane / the V295 lane mirror.
3. The **G-table base pointer** does not point at the cave's actual table start → the integral
   gain schedule / dip table is read from the wrong bytes (the `sar-5` I-quantum at every G is wrong).
4. The **freeze exit** `jr` does not land on `0x29D7E`, or the invalid-rate **op-skip** does not
   reach `0x2A164` (H-skip), or reaches it with any RAM written in between.
5. Any register outside {r6,r8,r9,r13,r16,r26} written; r25/r14 written; any RAM written.
6. The CRC chain does not re-walk; the `0x7FFF` sentinel is mishandled at any entry; overflow /
   sign-extension / truncation / saturation at any intermediate store width changes the surface.

**A FAIL on any one → DO_NOT_FLASH.** This pass reaches DO_NOT_FLASH, so it is not theatre.

---

## 1. DISPOSITIVE FINDING — there is no BUILT V296 image (EVIDENCE)

**EVIDENCE** (method: directory listing of both output roots + the build-script path, re-checked in
`adv_arith_v296.py` step 0):

| expected V296 artifact | location | present? |
|---|---|---|
| plain image `_v296_*_plain_image.bin` | `accord-firmwares/analysis-2020accord/` | **NONE** |
| flashable `39990-TVA,A160-V296-*.rwd` | `accord-firmwares/flashing-2020accord/rwd/` | **NONE** |
| `build_v296_tva.py` | `.../builds/v108_plus/` | **NONE** |
| revert re-headered `.rwd` copies | `.../rwd/` | **NONE** |
| `_self_check_v296()` in the golden model | `model/eps_chain_control.py` | **NONE** |

The builder's report states the build was stopped by an automated safety classifier before any step
ran, and that it deliberately did not route around the stop. Consistent with disk: `git status`
shows only the untracked empty study dirs `angle_loop/v296/` and `angle_loop/v297/`; nothing was
written to either repo.

**Consequence for this pass:** "re-derive the delivered surface from the BUILT IMAGE from scratch"
has **no bytes to read**. I cannot reimplement a lane+cave from an image that does not exist, and I
will not build one in order to review it — that is the builder's role and it is the step the safety
stop landed on. The honest output of an arithmetic pass whose target does not exist is **not** a
clean PASS; it is **DO_NOT_FLASH** (there is nothing fit to flash), finding (0) above.

---

## 2. The only "flight" cave bytes that exist are KNOWN-DEFECTIVE — confirmed from bytes

The repo does contain the design's flight-cave **hex** (not an image): `c3b_cave_C3B-P.hex`. The
brief and two refuters flag it as spliced +2 B by `rb_build.add_opskip` **without relinking**. I did
not take that on trust — I re-derived it from the bytes. **EVIDENCE** (method: parse the hex to
bytes, LE-decode `mov imm32,reg1` = `hw1>>5==0x31` and `jr disp22` = `hw1&0xFFC0==0x0780`, decoder
checked against the design's own worked example `jr 0x29A5C→0x2A164 = 80 07 08 07`; all in
`adv_arith_v296.py`):

- **Identity match.** `c3b_cave_C3B-P.hex` = **240 B**, byte-sha256 **`9a10cdc4ec75…`** → this is
  exactly the file the brief names. Score cave `c3b_cave_C3B-P_score.hex` = **238 B** (`b5a1d0ce1e0e…`).
- **The splice.** First flight/score divergence at cave offset **0x12** (abs `0xC4C12`): flight
  `b3 05 b6 07 50 55` (6 B, incl. the op-skip `jr 0x2A164`) vs score `e0 d7 36 d3` (4 B). Net **+2 B**.
  Everything at/after 0x12 in the flight cave sits 2 B later than where it was linked.

### FINDING A1 — G-table base pointer is stale, 2 B short (CONFIRMED, refuting)
- Flight: `mov 0x000C4CC4, r9` at cave offset 0x1C. Flight code length = 240 − 42(table) = **198 B**,
  so the table **actually begins at `0xC4CC6`**. Pointer delta = **+2 B short**.
- Score: identical immediate `0x000C4CC4`, but score code = 196 B → table at `0xC4CC4`. **Exact** —
  the same immediate is correct for the 196-B-code score cave and wrong for the 198-B-code flight cave.
- **Effect on the delivered surface:** the flight cave reads `table[0]` from `0xC4CC4` = the **last 2
  code bytes `66 00`**, not the true `table[0] = ca 02`; every subsequent G / dip entry is shifted
  −2 B. The integral gain schedule and the N2 dip the I-quantum depends on are read from garbage.
  This is a direct §8 FAIL (H1 bytes ≠ §1.4 arithmetic; the `sar-5` I-quantum is wrong at every G).

### FINDING A2 — freeze exit `jr` lands 2 B past target (CONFIRMED, refuting)
- Flight `jr` at offset 0xC0 → **`0x29D80`**. Design §1.2 freeze exit is **`0x29D7E`**. Stale by +2 B.
- Score `jr` at offset 0xBE → `0x29D7E` (correct). 
- The invalid-rate **op-skip** `jr`→**`0x2A164`** (offset 0x14, at the splice boundary) **is
  correctly linked** in the flight cave — its displacement was computed for its post-splice position.
  So H-skip's *target* is reached; the defect is the freeze return, not the op-skip.
- **Effect:** on a hard/opposing-hand freeze the cave returns into the middle of a Honda instruction
  at `0x29D80` instead of the intended `0x29D7E` — undefined control flow on the steering loop.

**Both refuter findings independently CONFIRMED from the bytes.** Any image built from
`c3b_cave_C3B-P.hex` as-is would ship both defects → DO_NOT_FLASH.

---

## 3. What I could NOT verify (honest gaps — no image to measure against)

- **No tick-for-tick lane re-derivation.** The core of an arithmetic pass — my own integer
  reimplementation of the lane+cave from the **image** bytes, compared against `score_freq.py` /
  `score_time.py` and `lane_mirror_v295.py` — cannot be run: there is no image. The score cave is a
  *scoring instrument*, not the flight image (it uses a different invalid-rate handling), so a null
  from it would be "a null from the wrong image" (kit iron rule) and I do not claim one.
- **No CRC walk, no 0x7FFF-sentinel audit at entries, no overflow/width census on delivered torque.**
  All require the built image. Unverified ⇒ not certified ⇒ cannot contribute a PASS.
- **A1/A2 are confirmed on the HEX, which is the correct linked form for the *score* cave but not the
  *flight* cave.** This is itself the finding: the file is unfit as a flight source.

---

## 4. Verdict and what must precede any V296 build

**VERDICT: DO_NOT_FLASH.**
1. No BUILT V296 image / `.rwd` exists — nothing to flash, nothing to certify.
2. The sole flight-cave bytes present (`c3b_cave_C3B-P.hex`, `9a10cdc4ec75…`) carry two CONFIRMED
   arithmetic defects (A1 stale G-table pointer −2 B; A2 stale freeze `jr` +2 B). **This file must
   not be built from.**

**Before any V296 is built** (per design §8 and the merge's own mandate): relink every absolute /
PC-relative reference at or after the 0x12 splice (fix `add_opskip` to relink, or hand-assemble),
then re-run **H1 on the FLIGHT bytes** (not the score cave), confirm the G-table pointer = cave-base +
flight-code-length and the freeze `jr` = `0x29D7E`, walk the CRC chain, and re-run this arithmetic
pass on the resulting IMAGE. Only then can an arithmetic PASS be earned.

**Process note (EVIDENCE):** I am the arithmetic adversary, not the builder. I did not relink, fix
`add_opskip`, assemble, or build — those are the steps the builder's safety stop landed on, and
producing them would be routing around that stop, which the operator (not a workflow note) is the
only authority to direct. Everything above is read-only confirmation that forces DO_NOT_FLASH.
