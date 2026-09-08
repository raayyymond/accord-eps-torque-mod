# ADVERSARY D — V288, INTERLOCKS / GATE 1 / DOWNSTREAM

**Agent** `advD` (subagent, reports to `main`). **Study/analysis only.** Nothing built, flashed, sent or
modified. No Ghidra function, label or comment created; every Ghidra call was a read-only query or
`disassemble_bytes` with `dry_run: true`. **`save_program` was NOT called.** No repo file other than this
report was written.

**Programs used, stated explicitly**
- **Ghidra**: `code.bin` (stock dump), the only open program (`list_open_programs` = 1, `is_current`,
  2086 functions). All decompile/disassemble below is **stock**.
- **Python byte work**: the V288 target image (sha256 verified `bc8a5b1a…5571`, 1,048,576 bytes), with
  `_v282_…_plain_image.bin` and `stock_fw_dump/code.bin` as comparisons.

**Why stock disassembly is admissible for V288 [EVIDENCE].** A full byte diff V282 → V288 over
`[0x13000, 0x100000)` returns **exactly 78 bytes in 5 runs**, all inside the declared regions:
`0x29D72-75` (4 B) · `0xC4BD6-D9` (4 B) · `0xC4BDC-FD` (34 B) · `0xC4C00-1F` (32 B) · `0xC4FFC-FF` (CRC).
Every other byte of the image, the whole live PID included, is byte-identical to V282, and V282's PID body
is byte-identical to stock apart from the known gain-source repoint. So a stock listing is a valid listing
for every instruction outside those five runs.

---

## 0. VERDICT

**PASS.** No do-not-flash finding on the interlocks / GATE 1 / downstream surface.

Two items go to the orchestrator as **REPORTS, not blocks** (§7). One of them (R2) is a defect in the
build script's own GATE 1 census that happened not to matter for this cell; it will matter for the next
cave that reuses that function.

Against the pre-registered FAIL list for surface D, item by item:

| pre-registered FAIL | result |
|---|---|
| `gp-0x6a32` has any reader | **NO** — zero readers, six independent methods, all positive-controlled |
| …or any register-indirect / table-dispatched writer (`0xb7260` mailbox class) | **NO** — cell is 0x54C0 outside that array; no literal, no `movhi`+low-half pair, no descriptor entry |
| the duplicate PID copy `0x2A508`/`0x2AC68` is reachable | **NO** — 0 external control transfers, 5/5 controls pass |
| `0x29D72`/`0x29D74`/`0x29D76` is a branch target from anywhere | **NO** — the only entry is our own cave's `jr` into `0x29D76` |
| the hook runs on a path where `r16` is not the assist-map output | **NO** — single path, `r16 = mulh` product on every predecessor |
| a plausibility monitor / DTC / oscillation detector / EME provably tripped by ≤16 ms lag or ≤1 command step | **NO** — §5 |

---

## 1. GATE 1 — THE `gp-0x6a32` CENSUS, SIX METHODS [EVIDENCE]

Target cell `gp-0x6a32` = **`0xFEDF15CE`**, 16-bit, so the protected footprint is
`0xFEDF15CE`–`0xFEDF15CF`. Computed in code, not typed (the off-by-0x1000 trap).

I wrote my own scanner rather than reusing the build script's. It scans **every 2-byte offset** in
`[0x13000, 0x100000)` and reports any access whose **accessed byte range overlaps the footprint**, at any
width — so a `ld.w` at `gp-0x6a34` or a `ld.bu` at `gp-0x6a31` would be caught, not just an exact-displacement
match.

**Controls, named before the run** (`firmware-decompile`: an uncontrolled null is a guess with a number
attached):

| control | expected | got | result |
|---|---|---|---|
| `gp-0x4f60`, 4-byte Format VII | 69 (kit record) | **69** | PASS |
| `gp-0x4f60`, 6-byte extended form | 7, at the recorded addresses | **7**, same addresses | PASS |
| `gp-0x6b98`, 6-byte extended form | 12 (kit record) | **12** | PASS |
| `gp-0x1514` `ld.bu`/`st.b` (the flown cave's own byte-4 access, the parity trap) | present | 16 sites incl. `0xC4B54`/`0xC4C0C` | PASS |
| `gp-0x6c2c` split | 8 accesses, 2 W / 6 R (V287 report) | **8, 2 W / 6 R**, same addresses | PASS |

### The census

| # | method | result |
|---|---|---|
| a | 4-byte Format VII, all widths, both `hw2`-bit-0 and `ld.bu` hw1-bit-5 parities, `jr`/`jarl` collision discriminated | **5 sites** (below) |
| b | 6-byte extended-displacement gp form, corrected halfword indices (`disp = (sext16(hw2)<<7) \| ((hw1>>4)&0x7F)`, base in `hw0`) | **0** |
| c | Format VIII bit-manipulation (`set1`/`clr1`/`not1`/`tst1`, opcode field **0x3E**) with `reg1 = gp` | **0** in a ±0x10 window (27 gp bit-ops exist image-wide) |
| d | `tp`-relative accesses resolving to the same absolute address | **0** |
| e | 32-bit LE literal `0xFEDF15CE` anywhere in the image | **0** |
| f | `movhi 0xFEDF/0xFEE0` + low-half pair landing within ±0x100 | **14 pairs, none on the cell** — all are `set1 <bit>,0x156c[r18]` / `0x1688[r18]`, fixed displacements, no index |
| g | `ep`-relative `sld`/`sst` reach: every `movea <disp>,gp,ep` base vs the ±0x1FC short-form reach | **0** — nearest bases are `0xFEDF11F0` (reaches to `0xFEDF13EC`) and `0xFEDF16BC` (above) |

**The five sites, all of them:**

| address | instruction | R/W | status |
|---|---|---|---|
| `0x2AC68` | `st.h r9, -0x6a32, gp` | **W** | inside the unreachable duplicate PID — §2 |
| `0xC4BDC` | `ld.h -0x6a32[gp], r9` | R | **ours** (the cave reads `y[n-1]`) |
| `0xC4BF2` | `st.h r16, -0x6a32[gp]` | **W** | **ours** (publish `y[n]`) |
| `0xC4BF6` | `ld.h -0x6a32[gp], r16` | R | **ours** (read back into `r16`) |
| `0xC4C02` | `ld.h -0x6a32[gp], r6` | R | **ours** (the sign rung) |

The stock writer at `0x29D72` is gone — replaced by the `jr` — and the cave re-issues it. **Outside our own
four cave accesses, the cell has ZERO readers and exactly ONE writer, and that writer is unreachable.**
GATE 1 **PASS**.

⭐ **A zero-reader census also excludes a lockstep twin by construction.** Honda's redundant-copy monitors
in this firmware have a fixed shape — read primary and shadow, `cmp`, `bne` to `jarl 0x6b9fa`, else write
both (e.g. `gp-0x69d2`/`gp-0x4c7a` at `0x3BF58`, `gp-0x6ac0`/`gp-0x4cc4` at `0x41820`). Such a monitor must
**read** the primary. There are no reads. **No lockstep twin exists for this cell** [EVIDENCE].

### The `0xb7260` mailbox class, checked explicitly

`0xFEDF15CE` is **not** in the 40-slot × 8-byte I/O-mailbox array (`0xFEDF6AE0`–`0xFEDF6C18`); it sits
`0x54C0` below its base. The named descriptor tables were dumped and read, not assumed:

- **`0x89C6C`** is a **flat list of individual signal pointers**, not (base, length) ranges — proven by the
  adjacent entries `0xFEDFE420` and `0xFEDFE421`, one byte apart, which cannot be a range pair. Its entries
  near our cell are `0xFEDF1542`, `0xFEDF15A2`, `0xFEDF15FE`, `0xFEDF1602`, `0xFEDF1558`. **None is
  `0xFEDF15CE`**, and the spacing is irregular, so no base + slot×stride lands on it.
- **`0xBBC48`/`0xBBC80`/`0xBBCA0`** are (pointer, descriptor) pairs whose descriptor low byte is a **bit
  length** (`0x0c` = 12, `0x08` = 8, `0x10` = 16, `0x20` = 32) — CAN signal descriptors for single cells,
  not memory ranges.

⚠ **Residual, stated not papered over:** a register-indirect read through a pointer this firmware computes
at run time from a source I did not enumerate cannot be excluded by any static method. What *can* be said is
that no literal, no `movhi` pair, no descriptor entry and no `ep` base anywhere in the image names this
address, and that the cell was **already Honda's own** — `0x29D72` wrote it in stock — so this build is
**not claiming free RAM**. That is the V62/V67 risk class, not the V48B/V50 class: we change the *value* in
a cell Honda already owns and provably never reads, we do not take a cell Honda might own.

---

## 2. THE DUPLICATE PID COPY `[0x2A508, 0x2B422)` IS UNREACHABLE — RE-DERIVED, NOT INHERITED [EVIDENCE]

I re-derived this from the image rather than carrying the trace's conclusion.

**Scan:** every Format V `jr`/`jarl` disp22 (with the `hw2`-bit-0 discriminator against `ld.bu`), every
Format III `Bcond` disp9, and every 48-bit `jr32`/`jarl32`, over `[0x13000, 0x100000)`.

**Controls (5/5 PASS):** the three from the `firmware-decompile` skill — `0x28EA6` ← `0x22522`,
`0x34350` ← `0x23276`, `0x3AA2C` ← `0x2291E` — plus five `Bcond` edges taken from a fresh Ghidra listing
(`0x2A4F4`→`0x2A504`, `0x2A484`→`0x2A49A`, `0x2A52C`→`0x2A5D0`, `0x2A558`→`0x2A590`, `0x2A512`→`0x2A518`).

**Result: ZERO external control transfers into `[0x2A508, 0x2B422)`.** 277 distinct targets land inside the
span; every source is also inside it.

Corroborating, each independently:
- **No fall-through.** `0x2A504` is `dispose 0x0, {r20,r22,r24,r26,r28,lp}, lp` — a **return**, 4 bytes,
  ending exactly at `0x2A508` (fresh Ghidra `dry_run` decode).
- **The span's upper bound is exactly right.** `0x2B422` *is* an external `jarl` target (from `0x22530`), and
  it is a real called function; widening the window to `0x2B600` produces external entries only at
  `0x2B422` and `0x2B57A`, both genuine function heads. The duplicate ends precisely where the record says.
- **No pointer table.** Nine 32-bit LE values in the image fall inside the span; **all nine are adjudicated
  non-pointers** — five point at **odd** addresses (impossible for a V850 entry point: `0x2AE95`, `0x2AE0B`,
  `0x2A609`, `0x2A60D`, `0x2A743`) and six of the nine are not 4-byte aligned. The one 4-aligned even value
  (`0x2B000` at file `0x5A368`) sits inside dense code with no table structure around it, and no `jmp [reg]`
  consumer was found.
- **No `movhi`+`movea` pair** anywhere materialises an address in the span.

⇒ `0x2AC68` never executes. And even if it did it is a **writer**, so it could only reset the filter state,
never feed a wrong value out of it. **Not a FAIL.**

---

## 3. HOOK-SITE INTEGRITY [EVIDENCE]

The stock instruction stream, freshly decoded:

```
0x29D6A  mov   r8,r16              <- r16 = sign (+1/-1)
0x29D6C  mulh  r13,r16             <- r16 = sign * map(idx)   = sp, 16x16 -> 32
0x29D6E  ld.hu 0x72e4[tp],r10      <- r10 = PID deadband cal 0xC62E4
0x29D72  st.h  r16,-0x6a32,gp      <- THE HOOK (V288: jr 0xC4BDC)
0x29D76  shl   0x5,r16             <- E = 32*sp ...
0x29D78  sub   r26,r16             <- ... - feedback
0x29D7A  mov   r16,r6
0x29D7C  sar   0x5,r6
0x29D7E  cmp   r10,r6
```

| question | answer |
|---|---|
| Is `0x29D72` or `0x29D74` a branch target from anywhere? | **No.** Zero `jr`/`jarl`/`Bcond`/`j32` sources. |
| Is `0x29D76` a branch target? | **Only from `0xC4BFA`** — our own cave's return `jr`. No stock path enters it. |
| Any path into `0x29D76` bypassing `0x29D72`? | **No.** `0x29D76` had zero predecessors before this build. |
| Any path executing `0x29D72` with `r16` ≠ the assist-map output? | **No.** `0x29D72` has one predecessor, `0x29D6E`, itself reached only by fall-through from `0x29D6A`/`0x29D6C`. Every incoming branch (`0x29D2A`, `0x29D40`) targets `0x29D6A`, *before* the `mov`/`mulh` pair. `r16` is the product on every path. |
| Does the hook run exactly once per call? | **Yes.** The only back-edge in the function below `0x29D40` is the LERP knot search `0x29D4A → 0x29D42`, which is *upstream* of the hook. |
| Is `FUN_00028ea6` called from more than one site? | **No.** Exactly one `jarl`, at `0x22522`. |

### Register and PSW liveness at the hook

The cave writes **r9, r16, r6** and reads r16.

| reg | live at `0x29D72`? | why |
|---|---|---|
| `r9` | **dead** | next use is a *write*, `mov 0x0,r9` at `0x29D80` |
| `r6` | **dead** | next use is a *write*, `mov r16,r6` at `0x29D7A` |
| `r10` | **LIVE** (loaded `0x29D6E`, read `0x29D7E`) | cave never touches r10 ✓ |
| `r26` | **LIVE** (read `0x29D78`) | cave never touches r26 ✓ |
| `lp` | must survive | cave is entered and left by `jr`, which does not write `lp` ✓ |
| PSW | irrelevant | `0x29D7E` issues its own `cmp` before the branch at `0x29D82` |

### The width question — the one thing that could have been a silent FAIL

Stock's `r16` at `0x29D76` is the **full 32-bit** `mulh` product. The cave's `ld.h` at `0xC4BF6` reloads
`r16` as a **sign-extended 16-bit** value. That is a behaviour change **iff the product can exceed int16**.

Re-derived from the built image, not from the script: multiplicand A is exactly **±1** (`mov r8,r16` where
`r8` is the `(+1|−1)` sign predicate), so `|product| = |map output|`. I read the **whole** setpoint map bank
`0xC9A88` out of the V288 image, all **34 reachable records**:

| | value |
|---|---|
| live slot 7 ceiling | 1032 |
| max Y over all 34 records | 1128 |
| int16 limit | 32767 |

**The store is lossless and the reload is value-identical to stock's 32-bit `r16`.** No sign flip is
possible: no table value reaches `0x8000`. `shl 0x5` on ±1128 gives ±36096, no 32-bit overflow.
[EVIDENCE — bytes read from the built image.]

### Cadence

`FUN_00028ea6` ← `0x22522` in `FUN_0002214a`, which is dispatched **from a task control block at
`0xBB928`** (entry `0x0002214A` beside stack base `0xFEDEC000`; it has no `jarl` caller anywhere, so it is
table-dispatched). Group delay 15.0 ms at K=4 for a 15/16 pole implies a **1 ms tick**, consistent with the
kit's 1 kHz inner loop.

🛑 **The call is CONDITIONAL** — this is the item the brief asked about, and the answer is favourable:

```c
uVar2 = 1 << (*(byte *)(gp - 0x67fa) & 0xf);   // ECU operating mode, one-hot
...
if ((uVar2 & 0x930) != 0) { FUN_00028ea6(0x11); ... }   // modes 4, 5, 8, 11
```

`gp-0x67fa` is the **ECU operating-mode byte**, not an LKAS-engagement flag (the same cell is tested against
6 and 8 by the mode-transition handler `FUN_0003bd7c`; the oscillation detector runs under the adjacent mask
`0x830`). **The PID therefore runs on every tick in the normal driving modes, engaged or not.** Engagement
enters *inside*, through the demand byte `gp-0x682f`: with no LKAS command the demand is 0, the map returns
`Y[0] = 0`, so `sp = 0` and **`y` decays to 0 rather than freezing.** No stale-setpoint transient at engage.
The residual case — a transit through a mode outside the mask — freezes `y` exactly as it already freezes
Honda's own integrator (`gp-0x6dd0`) and `E_prev` (`gp-0x6b36`); no new hazard class, and bounded by §5.

---

## 4. BOOT AND FAULT PATHS [EVIDENCE]

Six candidate bulk operations covering `0xFEDF15CE` were found and **all six adjudicated**:

- **Three were false pairs** — consecutive entries of the `0x89C6C` flat pointer list read by my
  bracketing heuristic as (start, end) ranges. Excluded in §1.
- **`0x587AE`** — `mov 0xFEDF11AC,r12 ; set1 0x0,0x0[r12]`. A single bit-set on one byte. Not a range.
- **`0x191CA` / `0x191E2`** — indexed byte writes `*(u8*)(0xFEDF1008 + idx) = 0x14 / 0`, with `idx`
  auto-incrementing. **The index is byte-wide**: `ld.bu 0x3c7a,r17,r7` loads it and `st.b r9,0x3c7a,r17`
  stores it back, so `idx ∈ [0,255]` and the write range is `0xFEDF1008`–`0xFEDF1107`. Reaching
  `0xFEDF15CE` needs `idx = 0x5C6 = 1478`. **Structurally impossible.**
- **`0x14766`** — the real one, and it is **crt0**. `mov 0xFEDF11B0,ep` then a 16-byte-per-iteration
  ROM→RAM copy, immediately followed by the canonical `0xEBEBEBEB` stack paint over
  `0xFEDEC000`–`0xFEDEF920`. Source `0x86260`, end `0x8AB18`, length `0x48B8`, destination
  `0xFEDF11B0`–`0xFEDF5A68`.

**`0xFEDF15CE` IS covered by that `.data` initialiser**, at destination offset `0x41E`, i.e. ROM `0x8667E`.
I read that ROM word out of the V288 image: **`0000` = 0**.

⇒ **At the first tick, `y = 0`, not garbage.** The "uninitialised RAM" question is closed, and it is closed
in the favourable direction. This runs once, at boot, before any task dispatch — it is the C runtime
startup, not a periodic clear. **Not a FAIL.**

---

## 5. INTERLOCKS AND MONITORS

**Every interlock cal cell re-read from the built image and compared to V282 — 0 changed:**

| cell | role | V282 | V288 |
|---|---|---|---|
| `0xC61B4` | T clamp | 3072 | 3072 |
| `0xC61B6` | D clamp | 10240 | 10240 |
| `0xC61B8` | post-lag deadband | 102 | 102 |
| `0xC61BA` | integrator anti-windup | 10240 | 10240 |
| `0xC61BC` | P clamp | 15360 | 15360 |
| `0xC61BE` | post-gain sum clamp | 15360 | 15360 |
| `0xC6202` | soft-EME bound | 4762 | 4762 |
| `0xC6206`/`0xC6208` | governor slew fast/slow | 512/205 | 512/205 |
| `0xC620A` | oscillation-detector threshold | 12800 | 12800 |
| `0xC62E4` | PID deadband | 4 | 4 |
| `0xC62E6` | feedback clamp | 46080 | 46080 |
| `0xC64DD`/`0xC64FA` | detector timeout / floor | 50/5 | 50/5 |
| `0xC64A3` | deadband ARM | 1 | 1 |

This follows from the 78-byte diff, but was read directly rather than inferred.

### The margin table

The filter has **DC gain exactly 1.0** and **converges exactly** to `sp` from every starting point (verified
by exhaustive simulation of the built encoding over `sp, y ∈ {±1128, ±1032, ±1, 0}` × 4000 ticks: zero
non-converging cases, zero 16-bit overflows on any intermediate). So no monitor's **steady-state** input
moves at all. Only transients change, and they change in the **attenuating** direction:

| monitor | input | does a ≤16 ms setpoint lag move it toward its threshold? |
|---|---|---|
| **Oscillation detector `FUN_000428d4`** | `gp-0x6c2c`, threshold `0xC620A` = 12800, 15/20 reversals | **NO — it moves AWAY.** Census of `gp-0x6c2c`: 8 accesses, **2 writers** (`0x4184E`, `0x41AC2`), 6 readers. `0x41AC2` is a `0x7FFF` fault sentinel; `0x4184E` stores `r26 >> 9` from a **measured motor-side** function (reads `gp-0x6b98`, `tp+0x748e`, writes `gp-0x6ac0`/`gp-0x4cc4`), not from the setpoint. The filter attenuates 20 Hz by **×0.457**, so it can only reduce reversal content. |
| **Governor slew** `0xC6206`/`0xC6208` = 512/205 | per-tick output change | **NO.** Max per-tick *setpoint* step: **raw 1032, filtered 135** (exhaustive, built encoding). The filtered setpoint can never step faster than the raw one — it is `d>>4`. Strictly further from the slew limit. |
| **EME shaper**, soft bound `0xC6202` = 4762 | output amplitude | **NO.** DC gain 1.0 ⇒ steady-state peak unchanged; transient peak strictly reduced. |
| **Lockstep / redundant-copy monitor** | primary vs shadow | **NO — none exists for this cell.** A lockstep comparator must *read* the primary; the reader census is empty (§1). |
| **LKAS plausibility / DTC on delivered torque** | `gp-0x6b38` (T) and the published intermediates | **NO.** The V287 pass established, and my `gp-0x6c2c` control re-validates the same scanner, that the PID's published intermediates have **zero live readers**, and T's three live readers are two CAN frame builders (`0x4E8D2`/`0x4E8E2`, `FUN_0004e82e` — no comparison, no threshold) and the 427 tap (`0x55DF0`). No consumer recomputes an expectation. |
| **`0xE4` message timeout / counter / checksum** | the received CAN frame | **NO — structurally impossible.** The filter sits *downstream* of CAN receive and of the assist map, inside the PID. It cannot touch frame reception, the rolling counter or the checksum. |

**Quantified transient bound.** After the demand goes to zero from the live ceiling, `y` decays
`1032 → below the PID deadband (4)` in **70 ticks = 70 ms**, and to exactly 0 in **74 ticks**. That is the
worst-case tail, it is monotone, and its peak is a value that was *already being commanded* the tick before —
no new authority. Whether any of that tail reaches the motor depends on the downstream engagement gate,
which is byte-unchanged.

---

## 6. THE `0x14A` RELOCATION [EVIDENCE]

All three `jr` displacements decoded independently from the built bytes:

| site | bytes | decodes to |
|---|---|---|
| `0x29D72` | `89076aae` | `jr 0xC4BDC` ✓ |
| `0xC4BD6` | `80072a00` | `jr 0xC4C00` ✓ |
| `0xC4BFA` | `b6077c51` | `jr 0x29D76` ✓ |

- **The relocated epilogue is byte-identical.** V282 `0xC4BD2..0xC4BD8` = `2436e8ea7f00`; V288
  `0xC4C1A..0xC4C20` = `2436e8ea7f00`. Same bytes, same order: `movea -0x1518,gp,r6 ; jmp [lp]`.
- **Caller semantics confirmed from the stock listing.** The cave hook overwrites what was
  `0x55C0E movea -0x1518,gp,r6`, so the cave must reproduce it — and does. On return:
  `0x55C12 mov 0x8,r7` **writes r7 immediately** (so the tele rung's use of r7 is safe), `0x55C14` writes
  r8, and `r6` is consumed by `0x55C18 jarl 0x57b24` — supplied by the relocated `movea`. ✓
- **`lp` is intact at the relocated `jmp [lp]`.** The cave is entered by `jarl …,lp` from `0x55C0E` and the
  relocation uses `jr`, which does not write `lp`. ✓
- **`0xC4BD8`–`0xC4BDB` is executed by no other path.** `0xC4BD8` and `0xC4BDA` are branch targets of
  **nothing** (full `jr`/`jarl`/`Bcond`/`j32` scan), and **no 32-bit literal anywhere in the image** points
  into `0xC4BD0`–`0xC4C20`. Those bytes were `ffffffff` filler in V282 and are now only ever the second
  halfword of the `jr` at `0xC4BD6`. ✓
- **Every internal cave branch resolves as designed:** `0xC4BE8`/`0xC4BEC` → `0xC4BF0`, `0xC4C08` → `0xC4C0C`.
  Both caves decoded instruction by instruction from the built bytes; the tele rung touches **only r6 and
  r7**, both dead across the call.

---

## 7. REPORTS — not blocks

**R1 — the disengage tail, for the scoring card.** The filter leaves a **≤70 ms** monotone decaying setpoint
tail after the demand goes to zero, where stock zeroes instantly. It is bounded, it adds no authority, and
the per-tick step is 7.6× *smaller* than stock's worst case. But if the drive is scored on "how fast does it
let go", **this will read as a real change and it is ours, not noise.** Carry it into the card.

**R2 — a defect in the build script's own GATE 1 census, `gp_census()`.** It happened not to matter for this
cell; it will matter for the next cave that reuses the function.
1. Its final filter is `op in (0x38,0x39,0x3A,0x3B,0x3C,0x3D,0x3F)`, which **excludes opcode field 0x3E** —
   the Format VIII bit-manipulation group (`set1`/`clr1`/`not1`/`tst1`). A `set1` on a candidate cell is a
   **writer** and a `tst1` is a **reader**, and the census would report neither. There are 27 gp-relative
   bit-ops in this image, so the blind spot is real, not theoretical. I scanned for them separately: **0 in
   the target window.**
2. Its docstring claims the scan covers "the 6-byte extended-displacement gp form", but the function body
   reads only `hw1`/`hw2` at each offset and never implements the 6-byte decoder. **The claim is not
   implemented.** I ran a correctly-indexed 6-byte scan separately (controlled at 7/7 and 12/12 against the
   kit's recorded `gp-0x4f60` and `gp-0x6b98` hits): **0 hits on the target.**

Both gaps are closed *by this report's independent scan*, so the GATE 1 conclusion stands. The script text
should not be allowed to keep asserting coverage it does not have.

**Method note, for reproducibility.** My first reachability pass reported 12 external entries into the
duplicate PID span — a **false alarm from my own decoder**. The Format III `Bcond` disp9 field is
`disp[8:4]` in bits 15:11 and `disp[3:1]` in bits 6:4; I had shifted the high field by 4 instead of 3,
doubling every target. It was caught only because I checked one flagged source against a fresh Ghidra
listing and found `br 0x2A504` where my decoder claimed `0x2A514`. **Every `Bcond` count in this report is
from the corrected decoder, positive-controlled on five known edges.** This is the same class of error the
`firmware-decompile` skill warns about, and the control is what caught it.

---

## 8. WHAT THIS PASS DOES NOT LICENSE

Per the pre-registration: a PASS here is **flash-candidate status on surface D only**. It says nothing about
whether the grind is fixed, and nothing about surfaces A, B or C. In particular the **outer-loop phase cost**
of the added 15 ms is explicitly *not* my surface — I confirm only that the **inner** rate loop's return
ratio is byte-identical to V282 (Kp, Kd, feedback clamp, all clamps, the fb pole and the output lag all
verified unchanged), so a reference pre-filter cannot move the inner loop's margins. If the outer loop were
destabilised by the added lag, the oscillation detector is the monitor that would see it — as a backstop,
not as a trip this build makes more likely.

---
---

# ADDENDUM 1 — `gp-0x6cf8`, POWER-ON STATE, AND A RETRACTION IN §3

Added after the rev 1 verdict, on the orchestrator's two additions to my brief (advB's disengage-reset
finding). **The rev 1 body above is left exactly as written**; this addendum corrects it where it is wrong.
Same discipline: stock `code.bin` in Ghidra, all reads or `dry_run`, `save_program` NOT called; byte work on
the same verified V288 image. The census script is parameterised and re-runnable on any image path
(`python census.py <image> <gp_disp> <width>`); it self-checks four controls before it reports.

## 🛑 A1.0 RETRACTION — my §3 claim "y decays to 0 while disengaged" is WRONG

§3 argued that because the PID's call gate `(1 << mode) & 0x930` is an **ECU-mode** gate rather than an
engagement gate, the PID runs while disengaged, the demand byte is 0, and therefore `y` decays to 0.

**The first half is right and the conclusion is wrong.** The function is entered, but *inside* it the
not-engaged path never reaches the hook:

```
0x29A48  cmp r0,r14 ; setfne r20        ; r20 = (r14 != 0)
0x29A4E  cmp 0x1,r8 ; setfe  r8         ; r8  = (r8 == 1)
0x29A54  cmp r0,r20 ; bne 0x29A60
0x29A58  cmp r0,r8  ; bne 0x29A60
0x29A5C  jr  0x0002A164                 ; <-- RESET, skips the hook
0x29A60  cmp r0,r25 ; bne 0x29A68       ; r25 = (r10 == 2), set at 0x29A82
0x29A64  jr  0x0002A164                 ; <-- RESET, skips the hook
0x29A68  ...                            ; only this path reaches 0x29D72
```

Both `jr`s are at **real instruction boundaries** (4-byte Format V, confirmed against a fresh Ghidra
`dry_run` listing) and both are the **only** predecessors of `0x2A164`. **advB's finding is confirmed
independently from the bytes: while disengaged the hook does not execute, so `y` FREEZES at its last
engaged value.** It does not decay.

⚠ Method note: my first attempt at this misread the predecessor addresses because I printed a Python
scan's results in **decimal** and converted them by eye — `170588` is `0x29A5C`, not `0x29A9C`. The wrong
pair landed mid-instruction inside a 6-byte `mov`, which is what exposed the error. Same lesson as the
kit's standing tp-relative rule: **print `hex()` from the script, never convert an address by hand.**

### What that costs, quantified (exhaustive sim of the BUILT encoding)

| frozen `y` | new `sp` | setpoint sign WRONG for | exact convergence | abs error at t=0 |
|---|---|---|---|---|
| −1032 | +1032 | **11 ticks = 11 ms** | 100 ticks | 2064 |
| −1128 | +1128 | **11 ms** | 101 ticks | 2256 |
| −1032 | +516 | **18 ms** | 96 ticks | 1548 |
| −1032 | 0 | 85 ms to reach the deadband | 89 ticks | 1032 |
| +1032 | 0 | 70 ms to reach the deadband | 74 ticks | 1032 |

A wrong-sign setpoint of 1032 puts `32·sp = 33024` into `E`, which **saturates the P clamp (15360)**. So
the worst case is not a small error — it is a **fully-railed assist in the wrong direction for ~11 ms** at
re-engage. That is pre-registered FAIL criterion **B2** ("engage/disengage transients produce a setpoint the
raw path could not produce — sign flip, overshoot"), i.e. **advB's surface, and advB has it.**

**My surface-D verdict does not change: PASS.** GATE 1 is clean, no monitor is tripped, and the per-tick
setpoint step is still bounded at **141 vs stock's 1032**, so nothing slew- or rate-based moves toward a
threshold. But **R1 in §7 is superseded**: the mechanism is not a 70 ms decaying tail, it is a frozen state
and a sign-inverted re-engage transient. Rev 1 should not fly on the strength of my §3 paragraph.

## A1.1 CENSUS OF `gp-0x6cf8` (0xFEDF1308, 4-byte)

Controls first, all PASS: `gp-0x4f60` 4-byte 69/69 · `gp-0x4f60` 6-byte 7/7 · `gp-0x6b98` 6-byte 12/12 ·
gp bit-ops total 27/27.

| method | result |
|---|---|
| (a) 4-byte Format VII, byte-range overlap | **4 sites** |
| (b) 6-byte extended gp form | 0 |
| (c) Format VIII bit-ops, `reg1 = gp`, ±0x10 | 0 |
| (d) tp-relative aliases | 0 |
| (e) absolute 32-bit literal | 0 |
| (f) `movhi`+low-half within ±0x100 | 2 pairs, **neither on the cell** — `clr1 7,0x1289[r18]` and `clr1 0,0x1288[r18]`, fixed displacements, single bytes, 0x80 below |
| (g) ep-relative `sld`/`sst` | **0, and structurally impossible** — see below |

**The four sites:**

| address | instruction | R/W | live? |
|---|---|---|---|
| `0x29E5E` | `ld.w -0x6cf8, gp, r8` | R | **LIVE**, inside `FUN_00028ea6` itself |
| `0x2A18C` | `st.w r16, -0x6cf8, gp` | **W** | **LIVE**, the PID publish block |
| `0x2AD4A` | `ld.w -0x6cf8, gp, r8` | R | orphan — inside `[0x2A508, 0x2B422)` |
| `0x2B058` | `st.w …, -0x6cf8, gp` | **W** | orphan — inside `[0x2A508, 0x2B422)` |

⇒ **In live code the cell is PRIVATE TO THE PID: exactly one reader and one writer, both inside
`FUN_00028ea6`.** No external consumer, no monitor, no lockstep twin (a twin would need a second reader).
This matches the V287 census's "`gp-0x6cf8` — ZERO external, self-read at `0x29E5E`, private".

**(g) closed structurally, not just empirically.** My first `sld`/`sst` decoder silently missed the
`sld.bu`/`sld.hu` forms (they live in the `sld.b`/`sld.h` reserved space: `bits10:4 = 0000110` disp4, and
`0000111` disp5 — *not* the `bits10:7` group the other six use), so its null was uncontrolled and worthless.
Rebuilt and **positive-controlled 10/10 against sites taken from fresh Ghidra listings**
(`sld.hu`/`sld.bu`/`sst.b`/`sst.w` at `0x29D2C`, `0x29D32`, `0x29D42`, `0x29D5A`, `0x224FA`, `0x224FE`,
`0x14770`, `0x1477C`, `0x147C6`, `0x191D6`). Result: 9 static `movea <d>,gp,ep` bases sit within the
0x1FC word-form reach of `0xFEDF1308`, but the **required displacement from each is 0x118–0x148**, and the
maximum displacement of *every* short form is smaller — `sld.bu` 0xF, `sld.hu` 0x1E, `sld.w`/`sst.w` 0xFC,
`sld.b`/`sst.b` 0x7F, `sld.h`/`sst.h` 0xFE. **No ep-relative access can encode a reach to this cell from any
static base.** For `gp-0x6a32` there is no base within reach at all (0 candidates).

## A1.2 CAN A READ-ONLY CAVE ACCESS TO `gp-0x6cf8` DISTURB ANYTHING? — NO, with two design constraints

**No.** `ld.w` has no architectural side effect, and `0xFEDF1308` is **internal RAM**, not peripheral space
(V850E2 peripherals are at `0xFFFF____` / `0xFA______`, where reads *can* have side effects — this address
is not). The only ways a read at the hook could disturb the tick are register clobber and ordering, and both
are constraints on rev 2's cave, not properties of the cell:

1. **Register discipline is unchanged and tight.** At `0x29D72` only **r9, r6 and r16** are free. **r10**
   (loaded `0x29D6E`, read `0x29D7E`) and **r26** (read `0x29D78`) are LIVE and must not be touched; `lp`
   must survive, so the cave must keep using `jr`, not `jarl`. Rev 1's cave already obeys this; rev 2 adds a
   `ld.w` and a compare, and a 32-bit compare against `0x7FFFFFFF` needs a **register to hold the literal**
   (`mov 0x7fffffff,rX` is the 6-byte form). There are only three free registers and rev 1 already uses all
   three. **This is the tightest constraint on rev 2 and it should be designed explicitly, not discovered.**
2. 🛑 **ORDERING — the cave reads the PREVIOUS tick's value.** Within one tick the order is
   **hook `0x29D72` → PID's own reader `0x29E5E` → writer `0x2A18C`**. The sentinel is written *after* the
   hook, so a cave read at `0x29D72` sees the value stored on the **previous** tick. On the re-engage tick
   that is exactly what is wanted (the sentinel was written by the last disengaged tick), but it is a
   one-tick-lagged arm and rev 2 must be designed for it deliberately.

**Sentinel semantics confirmed [EVIDENCE].** `0x2A164` is the reset block: `mov 0x0,r24 ; mov 0x0,r29 ;
mov 0x0,r27 ; mov 0x0,r22 ; mov 0x7fffffff,r16 ; mov 0x0,r12`, falling into the common publish block at
`0x2A174` where `0x2A18C st.w r16,-0x6cf8,gp` stores it. And the PID's own reader treats it as a
range check: `0x29E5E ld.w -0x6cf8,gp,r8 ; mov 0x177001,r13 ; mov 0xfff44800,r10 ; mov r8,r7 ;
sub r10,r7 ; cmp r13,r7` — i.e. "is the state inside `[0xFFF44800, 0xFFF44800+0x177001)` = **[−768000,
+768001)**". `0x7FFFFFFF` is far outside, so it reads as *state invalid*. advB's premise is correct.

## A1.3 🛑 POWER-ON STATE — BOTH CELLS, AND ONE CONSEQUENCE FOR REV 2

Read from the crt0 `.data` initialiser identified in §4 (ROM `[0x86260, 0x8AB18)` → RAM
`[0xFEDF11B0, 0xFEDF5A68)`, len `0x48B8`), taking each cell's destination offset and reading the ROM word
out of the built image:

| cell | dest offset | ROM source | **value at the first tick after power-on** |
|---|---|---|---|
| `y` = `gp-0x6a32` (0xFEDF15CE, 16-bit) | `0x41E` | `0x8667E` = `0000` | **0** |
| `gp-0x6cf8` (0xFEDF1308, 32-bit) | `0x158` | `0x863B8` = `00000000` | **0** |

Both are zero-initialised at boot, once, before any task dispatch. Neither is ever garbage.

🛑 **The consequence rev 2 must be designed around: at power-on `gp-0x6cf8` is `0`, NOT the `0x7FFFFFFF`
sentinel.** And `0` sits **inside** the PID's own valid window `[−768000, +768001)`, so it reads as a
*valid* state, not as "reinitialise". Therefore an engage-time init conditioned on
`gp-0x6cf8 == 0x7FFFFFFF` **will not fire on the first engage after a power-on** — it fires only on an
engage that follows a disengage, because only the disengaged ticks write the sentinel.

That specific case is **benign** — `y` is also 0 at power-on and `sp` starts at 0, so there is nothing stale
to correct — but it means the init is **not** a general "seed y from sp whenever the state is invalid"
guard, and any assertion or docstring claiming it arms on every engage would be **false**. If rev 2 wants
unconditional arming it needs a different predicate; if it accepts the power-on gap, that should be written
down as a deliberate, argued choice.

---
---

# ADDENDUM 2 — RECONCILIATION WITH advB: WHICH SKIP HAPPENS WHEN

The orchestrator asked which picture goes on the drive card. **Both are right, in different windows**, and
the discriminator is the engagement ramp. My Addendum 1 retraction was correct about the *mechanism* and
too pessimistic about the *ordinary case*; §7 R1 is partly reinstated. Decision-bearing for the card, not
for flashing.

## A2.1 First, one correction to the premise

The three skips are not all the same. From fresh `dry_run` listings:

| site | condition | jumps to | reaches the hook? |
|---|---|---|---|
| `0x29A5C` | `!(r14 != 0 \|\| r8 == 1)` | **`0x2A164`** — the state-reset epilogue | no |
| `0x29A64` | `r25 == 0` | **`0x2A164`** — the state-reset epilogue | no |
| `0x29A70` | `gp-0x680a == 1` | **`0x2A0C6`** — *not* the reset epilogue | no (it is past `0x29D72`) |

**`0x29A70` targets `0x2A0C6`, not `0x2A164`.** It is a different lane — an alternative map on the
`tp+0x7714`/`0x7722` knot family selected by `gp-0x680a`, not a state reset. It does skip the hook, but it
does not write the `0x7FFFFFFF` sentinel, so **rev 2's sentinel-armed init will NOT fire after a
`gp-0x680a` excursion.** Only `0x2A164` writes the sentinel, and only the first two skips reach it.
My own predecessor scan independently finds exactly two sources for `0x2A164`, which is the same result.

## A2.2 What r14, r8 and r25 actually are [EVIDENCE — decompile + disassembly]

```c
if (((uVar18 != 0) || (cVar15 == '\x01')) && (bVar3)) {      // 0x29A48-0x29A64
    if (*(char *)(gp - 0x680a) == '\x01') { ...alt map... }   // 0x29A70 -> 0x2A0C6
    else { uVar20 = *(byte *)(gp - 0x682f); ... }             // -> the demand path -> THE HOOK
}                                                             // else -> 0x2A164 reset
```

| reg | is | cell |
|---|---|---|
| `r14` → `uVar18` | the **engagement ramp** | `gp-0x69b0` (0xFEDF1650, `ushort`, 0…0x8000) |
| `r8` → `cVar15` | a received **state byte** | `gp-0x6805` (0xFEDF17FB) — **26 accesses, and every one of its 4 writers is in `0x5269C`–`0x527AC`**, the CAN-receive/decode region. It is an input to the engage state machine, not produced here. |
| `r25` → `bVar3` | an input-validity flag | set `true`/`false` in the intake block; on `false` the code also forces `*(gp-0x682f) = 0`, i.e. it zeroes the demand |

So the hook runs iff **(engagement ramp non-zero OR the received state byte == 1) AND inputs valid AND
`gp-0x680a != 1`.**

## A2.3 The answer: ordinary disengaged driving DOES take the skip — but only after the ramp walks down

The engagement ramp never jumps. **All six writers of `gp-0x69b0` are incremental** — `add` at `0x293AC`,
`0x293FE`, `0x294B4`; `sub` at `0x2942A`, `0x2950C`; and a saturate-to-`0x8000` at `0x29494`. **No writer
stores 0 or any small constant, so there is no snap-to-zero path.** The step cals (all byte-identical
V282 → V288):

| cal | value | site | full 0x8000 walk at 1 kHz |
|---|---|---|---|
| `0xC63F8` up | 33 | `0x294B4` | 0.99 s |
| `0xC63F6` down, slow | 16 | `0x2950C` | **2.05 s** |
| `0xC63F4` down, fast | 328 | `0x2942A` | **0.10 s** |
| `0xC63FC` | 328 | `0x293FE` | 0.10 s |

⇒ **Sequence at an ordinary openpilot disengage.** openpilot stops requesting, so the demand byte goes to
0. The ramp is still non-zero, so the guard still passes and **the hook keeps running with sp = 0** — this
is exactly the R1 tail, and it lasts 70–100 ticks. The ramp then walks to 0 over either 0.10 s or 2.05 s,
both ≥ the filter's convergence. Simulated on the built encoding, the frozen value is **exactly 0 in every
case, on both ramp rates, from every starting y** (±1032, ±1128). Once the ramp reaches 0 and
`gp-0x6805 != 1`, every subsequent disengaged tick takes the `0x29A5C` skip and the hook does not run.

**So, precisely, for the card:**
- **R1's "≤70–100 ms decaying tail" IS real** and it occurs in the ramp-down window — which is
  ramp-non-zero, not fully disengaged. The setpoint *is* consumed on those ticks.
- **Steady disengaged driving skips the hook every tick**, and the setpoint is not consumed at all then.
- **The frozen value in the ordinary case is 0, not stale.** Addendum 1's ±1032 worst case does **not**
  describe a normal disengage.

## A2.4 The narrow case where the worst case IS still reachable

The worst case needs the ramp to reach 0 while the demand is *still large* — i.e. an **EPS-side disengage
while openpilot keeps commanding**: driver override, a plausibility trip, or a fault. Simulated: with the
demand held at full scale through a fast (100-tick) ramp-down, y tracks it and **freezes at +1032**. A later
re-engage with an opposite-sign demand then gives:

| frozen y | new sp | setpoint sign wrong for |
|---|---|---|
| +1032 | −1032 | **11 ticks = 11 ms** |
| +1032 | −516 | 17 ms |

and a wrong-sign setpoint of 1032 still saturates the P clamp. **Driver override mid-curve is exactly this
shape**, so it is not an exotic path — but it is much narrower than Addendum 1 implied, and it cannot arise
from a plain openpilot disengage.

**Surface-D verdict unchanged: PASS.** Rev 2's sentinel-armed `y := sp` covers both pictures, with the two
caveats already recorded: it does not arm after a `gp-0x680a` excursion (§A2.1), and it does not arm on the
first engage after power-on (§A1.3).

## 🛑 A2.5 CORRECTION TO §A2.1 — THE `gp-0x680a` LANE **DOES** WRITE THE SENTINEL

**§A2.1 is wrong where it says the third skip does not arm the sentinel, and I withdraw that claim.** The
orchestrator caught it; I then re-derived it myself from a fresh `dry_run` listing of `0x2A0C6`–`0x2A162`
rather than transcribing the correction. The `gp-0x680a` lane loads **`mov 0x7fffffff, r16` at `0x2A0EA`**,
and from there to each of its three exits to the shared epilogue (`br 0x2A174` at `0x2A14A`, `0x2A15E`,
`0x2A162`) the only registers written are **r22, r10, r13, r9, r7, ep, r6, r8 and r12** — enumerated
instruction by instruction across both halves of the span, and **r16 is never among them**. So
`r16 = 0x7FFFFFFF` survives to the shared store `st.w r16,-0x6cf8[gp]` at `0x2A18C`. ⇒ **All three
hook-skipping paths arm the sentinel**: `0x29A5C` and `0x29A64` via the reset block's own
`mov 0x7fffffff,r16` at `0x2A16C`, and `0x29A70` via `0x2A0EA`. The correct statement is not "only
`0x2A164` writes the sentinel" but "**`0x2A18C` is a shared epilogue store, and every path that skips the
hook reaches it with `r16` already set to the sentinel**." Rev 2's init therefore arms after a `gp-0x680a`
excursion too, and **the only surviving caveat on its arming is the power-on gap in §A1.3.**

---
---

# REV 2 — SURFACE #4 RE-RUN

Target `_v288r2_…SPFILT.K4.EINIT…_plain_image.bin`, **sha256 `94cabdef…bd8c` verified**, 1,048,576 bytes.
(The rev 1 image has been renamed by someone else to `SUPERSEDED-DO-NOT-FLASH_v288_rev1_…`; my rev 1
report files are untouched, but the rev 1 path quoted earlier in this document is now stale.)

## VERDICT — **PASS** on surface #4, with one accounting finding (R3) that must reach the drive card.

## R2.1 Diff, CRC, and one apparent gap that is not one

Diff V282 → rev 2 over `[0x13000, 0x100000)`: **91 bytes in 6 runs** — `0x29D72-75`, `0xC4BD6-D9`,
`0xC4BDC-FD`, `0xC4C00-05`, `0xC4C09-2F`, `0xC4FFC-FF`. Nothing outside the declared regions.

⚠ The diff *appears* to leave `0xC4C06-08` unchanged, in the middle of the cave. **It is not a hole.**
Those three bytes are the middle of the immediate in `mov 0x7fffffff,r9` (`29 06 ff ff ff 7f` at
`0xC4C04-09`), and `ff ff ff` happens to equal the `0xFF` filler they replaced. The cave is contiguous
`0xC4C00-0xC4C2F`, 48 bytes.

**CRC verified.** ⚠ My first attempt reported a mismatch because I assumed the block was
`[0xC4000, 0xC4FFC)`. Calibrating against **two known-good images (V282 and rev 1)** shows the block is
**`[0x13000, 0xC4FFC)`**; on that block V282, rev 1 and rev 2 all verify. Stored trailer `f007c24a`
(= `0x4AC207F0` as an LE u32). This is the second time this pass that an uncalibrated assumption produced
a false negative — the control is what caught it, again.

## R2.2 Displacements, register discipline, isolation — all computed, none typed

| site | bytes | decodes to | expected |
|---|---|---|---|
| `0x29D72` | `89078eae` | `jr 0xC4C00` | 0xC4C00 ✓ |
| `0xC4BD6` | `80070600` | `jr 0xC4BDC` | 0xC4BDC ✓ |
| `0xC4C2C` | `b6074a51` | `jr 0x29D76` | 0x29D76 ✓ |

Internal branches: `0xC4BE4 bge → 0xC4BE8` · `0xC4C0C be → 0xC4C24` · `0xC4C1A bne → 0xC4C22` ·
`0xC4C1E be → 0xC4C22`. All as designed.

**Register discipline holds.** Filter cave writes **r6, r9, r16** only; telemetry rung writes **r6, r7**
only. **r10, r26 and lp are untouched** — the three that are live across the hook. The 48-bit
`mov 0x7fffffff,r9` did not cost a fourth register, which was the constraint I flagged in §A1.2.

**Isolation.** No branch from outside the caves targets `0xC4BDE-0xC4BFD` or `0xC4C02-0xC4C2F`; the only
entries are `0x29D72 → 0xC4C00` and `0xC4BD6 → 0xC4BDC`, plus the four internal branches. **No 32-bit
literal anywhere in the image points into `0xC4B34-0xC4C30`.**

**The einit semantics are right.** `ld.w -0x6cf8[gp],r6 ; mov 0x7fffffff,r9 ; cmp r9,r6 ; be 0xC4C24` —
on a sentinel match it branches *past* the filter body straight to `st.h r16`, where `r16` is still the raw
`sp`. So `y := sp` and the tick's delivered setpoint is `sp` itself, unfiltered. That is exactly the right
seed: no transient on the first engaged tick.

## R2.3 GATE 1 census on rev 2 — both cells clean

Controls PASS first (69/69, 7/7, 12/12, 27/27).

**`gp-0x6a32`, 5 accesses:** `0x2AC68` st.h (the unreachable orphan) · `0xC4BDE` ld.h · `0xC4C0E` ld.h ·
`0xC4C24` st.h · `0xC4C28` ld.h — the last four all ours. **Zero external readers, zero external live
writers.** 6-byte form 0, bit-ops 0, tp aliases 0, literals 0, ep-relative 0 (no base in reach); the 14
`movhi` pairs are the same fixed-displacement `set1`s on `0xFEDF156C/6D/1688` as in rev 1, none on the cell.

**`gp-0x6cf8`, 5 accesses:** `0x29E5E` ld.w and `0x2A18C` st.w (the live PID pair) · `0x2AD4A`, `0x2B058`
(both orphans) · **`0xC4C00` ld.w — ours, read-only.** Exactly the expected set. All other methods 0, and
the ep-relative reach remains structurally impossible (required disp `0x118-0x148` vs a `0xFE` maximum).

## R2.4 Boot picture — unchanged and favourable

crt0 `.data` copy bounds byte-identical (`mov 0x86260,r14` / `mov 0xFEDF11B0,ep`). Re-read from rev 2:

| cell | ROM source | value at first tick after power-on |
|---|---|---|
| `y` = `gp-0x6a32` | `0x8667E` = `0000` | **0** |
| `gp-0x6cf8` | `0x863B8` = `00000000` | **0** |

And per §A2.3 the **first engage is always preceded by skip ticks** — the ramp must walk up from 0, and
while it is 0 the guard fails and the hook is skipped, so the sentinel is written before the first engaged
tick. Combined with §A2.5 (all three skips arm), the einit fires on the first engaged tick in every
case **except** the power-on one, where it is unnecessary because both cells are 0.

## 🛑 R2.5 FINDING R3 — BIT 5 NOW HAS **TWO** WRITERS, AND THE `\|r24\|` COMPARATOR IS LOST

The orchestrator's two stated checks both pass: `andi 0xdf` clears **only bit 5**, preserving bits 0-2
(and 3, 4, 6, 7); and the three stock cave writers are **byte-identical** (`0xC4B34-0xC4BD5` unchanged).
But enumerating *every* rung that writes the `0x14A` byte-4 cell `gp-0x1514` finds **four in rev 2, not
three**:

| rung | mask | bit | quantity |
|---|---|---|---|
| `0xC4B5E` | `0xBF` | 6 | existing |
| `0xC4B8C` | `0xDF` | **5** | existing — the flown `\|r24\|` comparator |
| `0xC4BBC` | `0x67` | 3,4,7 | existing (three-sign rung) |
| **`0xC4BF4`** | **`0xDF`** | **5** | **NEW — `sign(y) < 0`** |

`0xC4BF4` executes *after* `0xC4B8C` in the same call (`0x55C0E → 0xC4B34 → … → 0xC4BD6 jr → 0xC4BDC →
0xC4BF4 → epilogue`), so **the new rung wins and the pre-existing bit-5 comparator is overwritten every
tick.** It is not a safety issue — byte 4 is telemetry and the frame checksum is still computed downstream
in the same critical section — but **anyone scoring the drive on bit 5 expecting the `\|r24\|` comparator
will misread it.** This must be on the card and in the build's own docs.

### 🛑 And it retracts a claim in my rev 1 report

Rev 1 put its bit on **bit 0**, on the build script's assertion — which my rev 1 §3 repeated — that
"bits 2-0 are written by nothing". **That is FALSE.** The stock writers in `FUN_00055a98` are:

```
0x55AC0  andi 0xfb, r8, r8   -> bit 2 = gp-0x6799 & 1
0x55AE8  andi 0xfd, r6, r6   -> bit 1 = gp-0x679b & 1
0x55B06  andi 0xfe, r15, r15 -> bit 0 = gp-0x679a & 1
```

**Bits 0, 1 and 2 are all stock-owned.** They sit at `0x55AAC-0x55B06`, upstream of the cave hook at
`0x55C0E` in the same function, so **rev 1's cave write to bit 0 would have clobbered a Honda-defined
signal on a transmitted CAN frame.** Rev 2's move to bit 5 is therefore not a cosmetic change — it is a
**correct fix to a real rev 1 defect that neither the build script nor my own rev 1 pass caught**, and it
trades a Honda signal for one of our own instruments, which is the right trade and matches the V286
precedent. I record this against my own rev 1 report: §3's "bits 2-0 are written by nothing" is
**RETRACTED**, and the surviving cost is the bit-5 accounting above.
