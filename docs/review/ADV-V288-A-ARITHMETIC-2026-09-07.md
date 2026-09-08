# Adversary A — ARITHMETIC / ENCODING — V288 (V282 + setpoint pre-filter cave, K=4)

Target image `_v288_…SPFILT.K4…_plain_image.bin`
sha256 `bc8a5b1ac2f796faa5563bb79e221a2f884f55ec040c654114fa2861f2ef5571` — **verified by me before any other work.**
Base `_v282_…_plain_image.bin` sha256 `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe`.

Surface #1 of the prereg (`ADVERSARIAL-V288-PREREG-2026-09-07.md`). Everything below is re-derived from
the IMAGE. The build script was never opened.

---

## VERDICT: **FAIL**

The filter arithmetic and the instruction encoding are **clean** — I could not break either. The build
fails on the **telemetry rung's bit allocation**: the new rung at `0xC4C00` claims **bit 0** of the CAN
0x14A byte at `gp-0x1514`, and **bit 0 already has a STOCK HONDA writer** at `0x55AF4`/`0x55B06`, inside
the same function, executing earlier in the same call. The V288 rung writes last and **overwrites a
stock, transmitted signal at 1 kHz**.

Item 4 of my brief asked me to confirm the `andi 0xfe` "cannot disturb bits 3–7 that the flown rungs
write". It cannot — bits 1–7 are preserved exactly. The brief did not anticipate that **Honda itself owns
bits 0, 1 and 2**, and the defect is there.

---

## D1 — DEFECT (FAIL): bit 0 of `gp-0x1514` is a stock Honda signal, and V288 overwrites it

**EVIDENCE.** Method: control-validated Python little-endian scan for every disp16 gp-relative access to
`0xeaec`/`0xeaed` (`gp-0x1514`) over `[0x13000,0x100000)`, positive-controlled against the known flown
rungs (the scanner found all three before I trusted its census); every hit then disassembled in Ghidra on
the built image, and the mask read from the disassembly, **not** hand-decoded — my first hand-decode of the
`0x55A**` masks was wrong and Ghidra caught it.

Full bit census of the byte `gp-0x1514` (= `0xFEDF6AEC`), CAN 0x14A byte 0:

| bit | writer | source | provenance |
|---|---|---|---|
| 0 | `0x55AF4` ld.bu / `0x55AFC` **andi 0xfe** / `0x55B06` st.b | `gp-0x679a` bit 0 | **STOCK HONDA** |
| 1 | `0x55AD4` / `andi 0xfd` / `0x55AE8` | `gp-0x679b` bit 0 | **STOCK HONDA** |
| 2 | `0x55AAC` / `andi 0xfb` / `0x55AC0` | `gp-0x6799` bit 0 | **STOCK HONDA** |
| 3,4,7 | `0xC4BB2` / `andi 0x67` / `0xC4BBC` | flown cave rung | this kit |
| 5 | `0xC4B82` / `andi 0xdf` / `0xC4B8C` | flown cave rung | this kit |
| 6 | `0xC4B54` / `andi 0xbf` / `0xC4B5E` | flown cave rung | this kit |
| **0** | **`0xC4C0C` / `andi 0xfe` / `0xC4C16`** | **setpoint sign** | **NEW IN V288 — COLLIDES** |

`0x55AAC–0x55B0C` is **byte-identical in stock `code.bin`, V282 and V288** (Python compare). It is not a
probe; it is Honda's own frame builder.

**The byte was already full.** The three flown cave rungs occupy exactly bits 3,4,5,6,7 — the five bits
Honda leaves free. That allocation is not a coincidence; it is the convention V288 broke.

**Order — V288 wins, so a stock signal is destroyed, not our tap.** `0x55AF4` (stock bit 0) and `0x55C0E`
(the flown `jr` into the 0x14A cave) are both inside **`FUN_00055a98`, body `0x55A98–0x55C41`** (Ghidra,
stock program). The cave is entered only from `0x55C0E` — my branch-target scan over the whole image finds
exactly one referrer to `0xC4B34`, and it is `0x55C0E`. The cave tail-calls through
`0xC4BD6 jr 0xC4C00` → rung → `jmp [lp]`. So within one call the stock bit-0 write at `0x55B06` happens
**first** and the V288 rung at `0xC4C16` happens **last**.

⇒ The V288 setpoint-sign tap **will** be readable on the wire. The cost is that **CAN 0x14A byte 0 bit 0
no longer carries the stock flag derived from `gp-0x679a`; it carries our setpoint sign, at 1 kHz.**

The stock write is itself conditional — `0x55AD2 be 0x55B1C` skips `0x55AD4`–`0x55B1A` when `r28 == 8`,
so bits 0 and 1 are written only on the `r28 != 8` path. That narrows nothing: whenever Honda writes it,
we clobber it.

**What I did NOT determine, and who owns it:** the meaning of `gp-0x679a` and whether anything consumes
0x14A bit 0 (openpilot's decode, another ECU, a Honda plausibility monitor). That is surface D's census.
**I am not asserting the consequence is benign — I am asserting the overwrite is real.**

**Constructive note (not a fix, and I did not edit anything):** `gp-0x1511` is the other byte of that word
that the 32-bit RMW at `0x21964` preserves — it masks `0xff0000ff`, keeping bytes 0 and 3 and rewriting
bytes 1 and 2, so `gp-0x1513`/`gp-0x1512` are unusable and have no other accessors. `gp-0x1511` has writers
at `0x55BF2`/`0x55C02`, `0x55C1C`/`0x55C2A` (stock) and the flown rung at `0xC4BC4` (`andi 0x3f`, bits 6–7).
Its free bits need the same census before anything is moved there.

---

## D2 — CONDITIONAL, cross-surface: a second, unhooked writer of the filter state

**EVIDENCE.** The same control-validated scan for `gp-0x6a32` (`0x95ce`):

| image | sites |
|---|---|
| V282 | `0x29D72` st.h (the hooked one), **`0x2AC68` st.h** |
| V288 | **`0x2AC68` st.h**, `0xC4BDC` ld.h, `0xC4BF2` st.h, `0xC4BF6` ld.h, `0xC4C02` ld.h |

`0x2AC68` is the duplicate PID copy the prereg names in FAIL criterion 4. It is **not** hooked. If it is
reachable, it writes the **raw** setpoint straight into the filter's state cell, and the next tick's `d`
is computed against a state the filter never produced — a single-tick step of the full raw value into the
downstream path, i.e. exactly the excitation the filter exists to suppress.

**My arithmetic PASS is conditional on surface D proving `0x2AC68` unreachable.** I did not adjudicate
reachability; it is D's assignment and the kit's record (golden model: `FUN_0002a30e` is the duplicate of
the live `FUN_00028ea6`) says *believed dead*, which is BELIEF, not evidence.

**Favourable side-finding:** in V282 the cell had **two writers and zero readers** (disp16 form). So the
worry that changing the cell's meaning from "raw sp, truncated to 16 bits" to "filtered sp" breaks a
downstream consumer is **void for the disp16 form** — there was no consumer. Register-indirect access is
surface D's.

---

## PASS — the encoding (24/24 instructions, 6/6 targets)

**EVIDENCE, three independent methods that agree exactly:** (a) a V850E2 decoder I wrote from the ISA for
Formats I, II, III, V, VI and VII, (b) Ghidra's disassembler on a **fresh import of the built V288 image**
(new program, base 0, `V850:LE:32:default`), (c) Ghidra's decompiler on the cave.

My decoder was **positive-controlled before I trusted it**: the three known call sites in the kit's skill
file resolve exactly — `0x22522 → 0x28EA6`, `0x23276 → 0x34350`, `0x2291E → 0x3AA2C`.

Two decoder bugs I hit and fixed, recorded because they are the traps the skill file warns about:
- **Format V `jr`/`jarl` collides with `ld.bu`** — both have opcode bits 10..6 = `11110`. Distinguisher is
  hw2 bit 0 (0 for `jr`/`jarl`, 1 for `ld.bu`). Before the fix my decoder called `0xC4C0C` a `jarl` to a
  nonsense address.
- My Format VII handling of opcode `0x3E`/`0x3F` is unreliable (Ghidra reads `divq`/`mul` where I read
  `ld.hu`). **None of the 24 new instructions uses that opcode**, so it does not touch the verdict.

Full-file diff V282 → V288: **78 bytes, every one inside the five declared regions, zero outside.**

| addr | bytes | instruction | target |
|---|---|---|---|
| `0x29D72` | `89076aae` | `jr` | **`0xC4BDC`** ✓ |
| `0xC4BDC` | `244fce95` | `ld.h -0x6a32[gp], r9` | |
| `0xC4BE0` | `a981` | `sub r9, r16` | |
| `0xC4BE2` | `1030` | `mov r16, r6` | |
| `0xC4BE4` | `a482` | `sar 4, r16` | |
| `0xC4BE6` | `6082` | `cmp 0, r16` | |
| `0xC4BE8` | `ca05` | `bne` | **`0xC4BF0`** ✓ |
| `0xC4BEA` | `6032` | `cmp 0, r6` | |
| `0xC4BEC` | `a205` | `be` | **`0xC4BF0`** ✓ |
| `0xC4BEE` | `0182` | `mov 1, r16` | |
| `0xC4BF0` | `c981` | `add r9, r16` | |
| `0xC4BF2` | `6487ce95` | `st.h r16, -0x6a32[gp]` | |
| `0xC4BF6` | `2487ce95` | `ld.h -0x6a32[gp], r16` | |
| `0xC4BFA` | `b6077c51` | `jr` | **`0x29D76`** ✓ |
| `0xC4BD6` | `80072a00` | `jr` | **`0xC4C00`** ✓ |
| `0xC4C00` | `003a` | `mov 0, r7` | |
| `0xC4C02` | `2437ce95` | `ld.h -0x6a32[gp], r6` | |
| `0xC4C06` | `6032` | `cmp 0, r6` | |
| `0xC4C08` | `ae05` | `bge` | **`0xC4C0C`** ✓ |
| `0xC4C0A` | `013a` | `mov 1, r7` | |
| `0xC4C0C` | `8437edea` | `ld.bu -0x1514[gp], r6` | |
| `0xC4C10` | `c636fe00` | `andi 0xfe, r6, r6` | |
| `0xC4C14` | `0731` | `or r7, r6` | |
| `0xC4C16` | `4437ecea` | `st.b r6, -0x1514[gp]` | |
| `0xC4C1A` | `2436e8ea` | `movea -0x1518, gp, r6` | |
| `0xC4C1E` | `7f00` | `jmp [lp]` | |

**Zero divergence from the builder's listing.** Alignment: `gp-0x6a32` = `0xFEDF15CE`, even, so both `ld.h`
and `st.h` are halfword-aligned and the disp16 has bit 0 = 0 (which is what makes them `ld.h`/`st.h` and
not `ld.w`/`st.w`). ✓

The hook is a **4-byte `jr` replacing a 4-byte `st.h`** — no instruction boundary shifts. My whole-image
branch-target scan (positive-controlled: it finds `0x29D72 → 0xC4BDC` and `0xC4BFA → 0x29D76`) shows
**nothing branches to `0x29D72` or `0x29D74`**.

---

## PASS — V850 semantics, confirmed from the image not from memory

- **`sub reg1,reg2` is `reg2 ← reg2 − reg1`.** Confirmed by Ghidra's decompiler on **adjacent stock code**:
  `0x29D76 shl 5,r16` + `0x29D78 sub r26,r16` decompiles to `iVar31 = iVar31 * 0x20 - uVar35`. So
  `sub r9,r16` is `r16 = r16 − r9` = **sp − y = d**, and `add r9,r16` is `r16 = step + y`. Not the reverse.
- **`sar` is arithmetic and floors toward −∞**, and **`ld.h`/`st.h` are signed 16-bit.** Ghidra's decompiler
  on the cave itself renders it, and this is the single strongest confirmation I have:

```c
void advA_v288_spfilt_cave(void) {
  iVar1 = in_r16 - *(short *)(unaff_gp + -0x6a32);       // d = sp - y
  iVar2 = iVar1 >> 4;                                     // step (signed shift)
  if ((iVar2 == 0) && (iVar1 != 0)) { iVar2 = 1; }        // minimum step
  *(short *)(unaff_gp + -0x6a32) = (short)iVar2 + *(short *)(unaff_gp + -0x6a32);
  FUN_00029d76();
}
```

---

## PASS — the filter cannot be broken

Mirrored exactly in integer Python, 16-bit store/reload wrap included, then attacked:

| attack | result |
|---|---|
| steady state `y ≠ sp`, all `sp ∈ [−1200,1200]` × 11 starts incl. `±32768` | **converges to `y = sp` exactly, always** |
| worst-case settle | 144 ticks, at `sp=1176`, `y0=−32768` |
| stuck non-zero LSB / limit cycle at the fixed point | **none** — `tick(sp,sp)` returns `sp` for every `sp` |
| overshoot, sign flip past `sp` | **none** |
| 16-bit overflow of the cell | **none** |
| `st.h`→`ld.h` round-trip ever differs from the value added | **no**, for `|sp| ≤ 32767` |
| failure boundary | first loss at **`|sp| = 32768`** — i.e. exactly where `sp` itself stops being int16 |

**Why no overflow is structural, not just empirical.** If `d > 0` then `1 ≤ step ≤ d`; if `d < 0` then
`d ≤ step ≤ −1`. Either way `y_new` lies strictly between `y` and `sp` inclusive, so
`|y_new| ≤ max(|y|,|sp|)`. The cell can never grow beyond its inputs.

**The `sar` floor makes the filter mildly asymmetric** — for `d<0` the step is up to 1 count larger in
magnitude than for the mirror `d>0` (e.g. `d=−31 → −2`, `d=+31 → +1`). Bounded at 1 count, transient only,
zero at steady state. Not a defect.

**`|sp|` is bounded by 1128, read from the image — 29× headroom to int16.** `0x29D6C mulh` computes
`±1 × (int16)map_output`: the decompile gives `iVar31 = (int)(short)((ushort)!bVar4 - (ushort)bVar4) *
(int)(short)uVar25`, a sign selector times the assist-map output. I dumped the pointer table at `0xC9A88`
from the V288 image and read all 12 reachable map structs: max |y knot| = **1128** (slots 8, 9). So the
one value that could not survive the reload, `+32768`, is unreachable by a factor of 29.

⚠ **This is the real semantic delta beyond "adds a lag", and it is worth stating plainly:** V282's
`st.h` truncated `r16` to 16 bits **for the store only** and fed the **full 32-bit** `r16` to `shl 5`.
V288 reloads `r16` from the 16-bit cell, so the value reaching `shl 5` is now 16-bit-limited. **Inert at
29× headroom** — but it is a change, and it is inert because of a map bound, not because of the cave.

`0x29D60–0x29D72` and `0x29D76–0x29DB0` are **byte-identical to stock `code.bin`**, so the decompile the
±1×int16 argument rests on is of the same bytes that are in V288.

---

## PASS — register and PSW liveness at the hook

Cave writes `r9`, `r16`, `r6`. Reads `r16` (entry), `gp`, `r9`, `r6`.

| reg | verdict |
|---|---|
| `r16` | the intended output ✓ |
| `r9` | **dead-written** at `0x29D80 mov 0,r9`; nothing in `0x29D76…0x29D7E` reads it ✓ |
| `r6` | **dead-written** at `0x29D7A mov r16,r6`; `shl`/`sub` in between do not read it ✓ |
| `r10` | **untouched** by the cave; loaded `0x29D6E`, consumed `0x29D7E cmp r10,r6` ✓ critical, survives |
| `r26` | **untouched**; consumed `0x29D78 sub r26,r16` ✓ |
| `lp` | **untouched** — the cave uses `jr`, not `jarl` ✓ (a `jarl` would have destroyed the return address) |
| `ep`, `r8`, `r13`, `r2`, `sp` | **untouched** ✓ |

**PSW.** The original `st.h` set no flags; the cave's last flag writer is `add r9,r16`. The exposure window
is **zero instructions**: the first instruction after return is `0x29D76 shl 5,r16`, and even under the
most pessimistic assumption that `shl` sets nothing, `0x29D78 sub r26,r16` unambiguously does. **There is
no conditional branch anywhere between `0x29D76` and `0x29D82`**, so no flag the cave leaves can be
consumed.

**`0x29D82 ble` is conditioned only on `0x29D7E cmp r10,r6`.** The only instruction between them is
`0x29D80 mov 0,r9`, and V850 `mov` is flag-neutral — self-evidenced by the **stock** compiler having
scheduled it into that cmp/branch gap in the flown image. That whole span is byte-identical to V282 anyway.

## PASS — the 0x14A epilogue relocation is semantically exact

V282: `0xC4BD2 movea -0x1518,gp,r6` ; `0xC4BD6 jmp [lp]`.
V288: `0xC4BD2 movea` (unchanged) ; `0xC4BD6 jr 0xC4C00` ; rung ; `0xC4C1A movea -0x1518,gp,r6` ; `0xC4C1E jmp [lp]`.

`r6` is clobbered by the rung and then **restored by the re-executed `movea`**, so `r6` on return is
identical. ✓ `r7` is also clobbered, but the **existing V282 rung at `0xC4BC0` already clobbers `r7` on this
exact path before the same `jmp [lp]`** — flown precedent, not new risk. ✓ `ld.bu` at an odd displacement
uses opcode `0x3D`, at an even one `0x3C`; `gp-0x1514` is even and encodes `0x3C`, matching its `st.b`. ✓

---

## Requested numbers — corner, group delay, first-tick kick (K=4, my arithmetic)

Linear regime (`|d| ≥ 16`): `y[n] = (15/16)·y[n−1] + (1/16)·sp`, pole `a = 0.9375`, tick 1 kHz
(`FUN_00028ea6` is the ~1 kHz arbitration).

| quantity | value |
|---|---|
| DC gain | 1.000000 exact |
| −3 dB corner | **10.25 Hz** |
| group delay at DC | **15.0 ticks = 15.0 ms** |
| time constant τ | 15.5 ms |
| at 3.9 Hz | −0.58 dB, −20.1° |
| at 7.0 Hz | −1.66 dB, −33.0° |
| at 20.3 Hz | **−6.90 dB (×0.452)**, −59.6° |

The builder's "15 ms at K=4" is confirmed independently.

**First-tick kick.** For a step `S`: `y[1] = max(1, S>>4)`. So the per-tick excitation is `≈S/16` for
`S ≥ 16`, and **exactly 1 count** for `0 < S < 16` — the integer floor, which cannot be improved on.

**Exact integer response to the real 100 Hz-staircase command**, peak per-tick `|Δsp|` raw vs filtered:

| f | A=4 | A=8 | A=16 | A=40 | A=120 | A=400 |
|---|---|---|---|---|---|---|
| 3.9 Hz | 1.0× | 2.0× | 4.0× | 10.0× | 7.5× | 8.2× |
| 7.0 Hz | 2.0× | 4.0× | 7.0× | 9.0× | 8.7× | 9.2× |
| 20.3 Hz | 5.0× | 10.0× | 9.5× | 16.0× | 15.9× | 15.4× |

**The excitation reduction is real and the filtered per-tick kick is never worse than 1 count.**

⚠ **Efficacy caveat, not a FAIL.** The minimum-step-1 rule makes the filter a ±1 count/tick slew tracker
for small setpoint excursions, so the **−6.9 dB attenuation at 20 Hz only holds above ~16 counts of
setpoint amplitude.** Measured fundamental gain at 20.3 Hz: **0.99 at A=4, 0.95 at A=8**, 0.61 at A=16,
0.45 at A≥40. Below ~8 counts the filter is essentially transparent. The prereg already says a PASS
licenses no claim that the grind is fixed; this **quantifies** that bound, and surface B should note the
amplitude-dependent gain (1.00 → 0.80 at 7 Hz) as a describing-function variation in the outer loop.

---

## What a FAIL would have looked like, and what I actually ran

Written against the prereg's criterion 1. I ran every one; the filter and encoding survived all of them.

- decode divergence under an independent decoder or Ghidra — **ran, none**
- `jr` landing anywhere but `0xC4BDC` / `0x29D76` / `0xC4C00` — **ran, all three exact**
- `y ≠ sp` at steady state — **ran, converges exactly**
- stuck non-zero LSB — **ran, none**
- 16-bit overflow — **ran, structurally impossible**
- `r10`/`r26`/`lp` corruption or PSW-dependent control flow at `0x29D7E` — **ran, none**

The FAIL came from the one item on my list that was not about the filter: the telemetry rung's bit
allocation.

---

## Summary for the orchestrator

**DO NOT FLASH as built.** The setpoint pre-filter itself is, as far as I can break it, correct: the
encoding is exact under three independent methods, the arithmetic converges exactly with no overflow and
no limit cycle, and no register or flag the return path needs is disturbed. The build fails because its
**instrument** collides with a stock Honda signal: `0xC4C00`'s rung takes bit 0 of CAN 0x14A byte 0, which
`0x55B06` (stock, byte-identical since the factory) already writes, and V288's write lands last.

Two things I could not close and hand to other surfaces: whether `0x2AC68` — the second, unhooked writer
of the filter state — is reachable (**D**), and what consumes 0x14A bit 0 (**D**).

*Adversary A, 2026-09-07. Nothing in this pass edited the build script, the image, or any repo doc other
than this file.*

---
---

# REV 2 — `_v288r2_…SPFILT.K4.EINIT…` — re-run of the full surface #1 attack

Image sha256 `94cabdefd39a103ad10ec34b9c64b6ac94d6552b80bfe7cc192a8977cbbdbd8c` — **verified before any
other work.** Rev 1 has been renamed by someone else to
`SUPERSEDED-DO-NOT-FLASH_v288_rev1_V288-V282BASE-SPFILT.K4_plain_image.bin`; I did not move it.

Re-run with a **re-runnable harness** built for this purpose:
`…/scratchpad/advA/advA_v850.py` (decoder + emulator) and `…/scratchpad/advA/advA_attack.py`.
One command re-runs the whole surface on any image:

```
python advA_attack.py <image.bin> --base <base.bin> --sha <expected>
```

The filter's behaviour is obtained by **emulating the cave's own bytes**, not by re-implementing my
reading of them, so a changed cave is picked up automatically. The harness was **validated against rev 1
first** and reproduced my hand analysis exactly, including both rev 1 FAILs.

## REV 2 VERDICT: **FAIL**

Rev 1's defect is **fixed** — the rung no longer touches Honda's bit 0. But it moved to **bit 5, which is
already owned by V282's own flown r24-comparator rung**, and the new rung again writes last.

---

## R1 — DEFECT (FAIL): bit 5 collides with V282's flown r24-comparator tap

**EVIDENCE.** Both rungs decoded from the rev 2 image by my decoder and by Ghidra, and the mask read from
the disassembly rather than by offset arithmetic.

| | flown r24-comparator rung | NEW rev 2 setpoint-sign rung |
|---|---|---|
| select | `0xC4B7A mov 0x2, r7` · `0xC4B80 shl 0x4, r7` | `0xC4BE6 mov 0x2, r7` · `0xC4BE8 shl 0x4, r7` |
| read | `0xC4B82 ld.bu -0x1514[gp], r6` | `0xC4BEA ld.bu -0x1514[gp], r6` |
| mask | `0xC4B86 andi 0xdf` | `0xC4BEE andi 0xdf` |
| write | `0xC4B8C st.b r6, -0x1514[gp]` | `0xC4BF4 st.b r6, -0x1514[gp]` |
| bit | **5** | **5** |

`0xC4B7A–0xC4B90` is **byte-identical in V282 and rev 2** (Python compare), so the r24 rung is untouched
and still live. Both rungs OR in `2<<4 = 0x20` under the identical `andi 0xdf`.

**Order — the new rung wins.** The 0x14A cave runs `…0xC4B8C` (r24 comparator, bit 5) … `0xC4BD2 movea` →
`0xC4BD6 jr 0xC4BDC` → the new rung → `0xC4BF4 st.b` (setpoint sign, bit 5) → `jmp [lp]`. The setpoint
sign is written **last**.

⇒ **CAN 0x14A byte 0 bit 5 stops carrying the r24 comparator and carries the setpoint sign instead.**
The build's own name still asserts `CAVE.R24CMP`, and the kit's record has the operator reading that
comparator on the wire. Either the r24 tap is knowingly being retired — in which case the build name and
the telemetry decoder both need updating — or this is the rev 1 defect repeated one bit over. **I cannot
tell which from the image, and that ambiguity is itself the reason to stop.**

Full bit census of `gp-0x1514` in rev 2:

| bit | writer | provenance |
|---|---|---|
| 0 | `0x55AF4` `andi 0xfe` | STOCK HONDA — **rev 1's collision, now correctly avoided** ✓ |
| 1 | `0x55AD4` `andi 0xfd` | STOCK HONDA |
| 2 | `0x55AAC` `andi 0xfb` | STOCK HONDA |
| 3,4,7 | `0xC4BB2` `andi 0x67` | flown |
| **5** | `0xC4B82` `andi 0xdf` **AND** `0xC4BEA` `andi 0xdf` | **flown r24 cmp + NEW — COLLISION** |
| 6 | `0xC4B54` `andi 0xbf` | flown |

**The byte has no free bit.** Honda owns 0–2; the flown rungs own 3–7. Rev 2 had nowhere to go inside this
byte, which is the underlying problem neither rev solved. `gp-0x1511` is the other byte of the word that
the 32-bit RMW at `0x21964` preserves (mask `0xff0000ff`); it has stock writers at `0x55BF2` and `0x55C1C`
and the flown rung at `0xC4BC4` (bits 6–7), and needs its own census before anything moves there.

---

## R2 — the engage-init gate: PASSES, and it does what it claims

**EVIDENCE, by emulating the rev 2 cave's bytes.**

```
0xC4C00  24370993      ld.w -0x6cf8[gp], r6
0xC4C04  2906ffffff7f  mov 0x7FFFFFFF, r9
0xC4C0A  e931          cmp r9, r6
0xC4C0C  c20d          be 0xC4C24          <- the st.h, skipping the whole filter body
```

- **One tick, exact, no residual lag.** With the gate cell at the sentinel, `state = sp` and `r16 = sp`
  **exactly**, for every `sp` in ±1200 across 7 prior states including `±32768`. Zero mismatches.
- **`r16` still holds raw `sp` on that path.** The prologue writes only `r6` and `r9` — checked by
  decoding, not by reading the listing. ✓
- **The gate does not fire on anything else.** Tested `0`, `1`, `0x7FFFFFFE`, `0x80000000`, `0xFFFFFFFF`
  — all take the filter path. ✓
- **No aliasing with a setpoint.** The gate is a 32-bit `ld.w` at `gp-0x6cf8`, a different cell from the
  16-bit state at `gp-0x6a32`, and `|sp| ≤ 1128` cannot reach the sentinel anyway. The gate cell's
  *meaning* is surface B/D's, not mine.
- **The transient rev 2 exists to fix is fixed.** From stale states `−1128`, `0`, `+1128` with `sp = 300`,
  the init tick snaps the state to `+300` and the next engaged tick already sits at `+300`.

## R3 — the four encoding questions asked, answered

- **6-byte `mov imm32`.** `0x0629` decodes as opcode `0x31` (the `movea` field) with `reg2 = 0`, which is
  the V850E `MOV imm32, reg1` form; `reg1 = 9` → **r9**. **Positive-controlled against Honda's own**:
  `0x2A16C` `3006ffffff7f` = `mov 0x7FFFFFFF, r16` (`0x0630`, `reg1 = 16`) and `0x21954` `2f06ff0000ff`
  = `mov 0xFF0000FF, r15`. Same form, different destination — the encoding is confirmed by code that
  shipped from the factory. ✓
- **`ld.w` word-form bit.** hw2 = `0x9309`, bit 0 = **1** ⇒ `ld.w` (not `ld.h`); disp = `0x9308` =
  **−0x6CF8**. Aligned: `gp−0x6CF8 = 0xFEDF1308`, divisible by 4. ✓
- **`cmp r9, r6` operand order.** Encoding gives `reg1 = r9`, `reg2 = r6`, so it computes `r6 − r9`. The
  branch is `be`, condition nibble `0x2` = **Z**, and equality is symmetric, so the operand order is
  irrelevant here — confirmed, as briefed. ✓
- **The `be` target.** disp decodes to +24 from `0xC4C0C` ⇒ **`0xC4C24`**, which the listing shows is the
  `st.h`. Ghidra independently renders `be 0x000c4c24`. ✓
- **`0xC4C06–0xC4C08` (three `0xFF` bytes that equal the old filler).** They **are** part of the
  immediate. Proof is stream coherence, not assertion: consuming 6 bytes at `0xC4C04` produces a decode
  that lands exactly on the `cmp` at `0xC4C0A`, and **all four** subsequent branch targets
  (`0xC4C24`, `0xC4C22`, `0xC4C22`, `0x29D76`) land on instruction boundaries. Any other framing desyncs
  the stream. The diff shows the gap only because the build had to write 3 of the 6 bytes — the other 3
  were already `0xFF`. ✓

## R4 — everything else re-run, all PASS

| check | rev 2 result |
|---|---|
| diff vs V282 | **91 bytes in 6 runs, all inside the declared regions, zero outside** |
| decoder positive controls | 3 call sites + 2 `mov imm32` sites, all resolve |
| hook | 4-byte `jr 0xC4C00`, replaces a 4-byte `st.h`, no boundary shift |
| all 17 cave + 14 rung instructions | my decoder and **Ghidra agree exactly**, zero divergence |
| all 5 branch targets | exact; every internal branch lands on a decoded boundary |
| convergence | `y → sp` exactly, worst 144 ticks at `sp=1176`, `y0=−32768` |
| stuck LSB / limit cycle | none |
| monotone, no overshoot, no sign flip, no 16-bit overflow | none |
| truncation boundary | first escape at `|sp| = 32768`, i.e. where `sp` stops being int16 — 29× away |
| `r10`, `r26`, `lp`, `r8`, `r13`, `r2`, `ep` | all preserved across the cave |
| `r6`, `r9` | both **dead-written** on the return path before any read (`0x29D7A`, `0x29D80`) — and rev 2's prologue clobbers the same two registers, so the conclusion carries |
| PSW | zero flag-exposure window; no conditional branch before the next flag writer |

**The filter body is byte-identical to rev 1** (`rev1 0xC4BDC..0xC4BF9` == `rev2 0xC4C0E..0xC4C2B`, only
the return `jr` displacement differs for the new origin), so the response numbers are unchanged and I
re-measured them from the emulator to confirm: pole `0.937500`, **−3 dB corner 10.25 Hz, group delay
15.0 ms**, τ 15.5 ms, **−6.90 dB at 20.3 Hz**. Per-tick kick reduction 7.5×–16×, filtered kick never worse
than 1 count. The small-amplitude transparency caveat from rev 1 is unchanged: fundamental gain at 20.3 Hz
is **0.99 at amplitude 4 and 0.95 at amplitude 8**, reaching 0.45 only above ~40 counts.

## R5 — still open, still cross-surface

`0x2AC68` — the second, unhooked `st.h` to `gp-0x6a32` — is **unchanged in rev 2**. My arithmetic PASS
remains conditional on surface D proving it unreachable. Rev 2's engage-init makes this *slightly* less
severe (a stomp is now recovered on the next disengage/engage rather than persisting) but does not remove
it: while engaged, a write from `0x2AC68` still injects the raw setpoint into the state.

*Adversary A rev 2 re-run, 2026-09-07. Harness at `scratchpad/advA/`. I edited nothing but this file, and
imported the rev 2 image into Ghidra as a new program under `/advA` without saving.*
