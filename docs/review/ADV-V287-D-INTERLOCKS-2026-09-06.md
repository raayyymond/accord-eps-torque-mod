# ADVERSARY D — V287, INTERLOCKS AND DOWNSTREAM CONSUMERS

**Agent**: `advD` (subagent, reports to `main`). **Study/analysis only** — nothing built, flashed, sent
or modified. No Ghidra function, label or comment was created; every Ghidra call was a read-only query
or `disassemble_bytes` with `dry_run: true`. **`save_program` was NOT called.**

**Programs used, stated explicitly:**
- **Ghidra**: `code.bin` (stock dump), the only open program (`list_open_programs` = 1, `is_current`,
  2086 functions). All decompile/disassemble below is from **stock**.
- **Python byte work**: `_v287_…DCLAMP.2560…_plain_image.bin` (V287, 0x100000 bytes), with
  `_v282_…_plain_image.bin` and `stock_fw_dump/code.bin` as comparisons.

**Why stock disassembly is admissible for V287 [EVIDENCE]:** a full byte diff of the live PID body
`[0x28EA6, 0x2A2A0)` between **V287 and stock** returns **exactly 2 differing bytes, `0x2A1F0`/`0x2A1F1`**
— the V282 gain-source repoint `ld.h 0x746c,tp,r7` to `ld.h 0x7cd0,tp,r7`. Every other instruction in the
PID, including all four D-clamp loads, the deadband block, the T clamp and the publish block, is
**byte-identical to stock**.

---

## 0. WHAT A FAIL LOOKS LIKE — written before the attack

I would return **DO NOT FLASH** on any one of:

- **F1** — a live consumer of the D result, the PID sum, or T that recomputes an expectation from a
  hard-coded `10240`, or from a *different* cell holding 10240 (`0xC61BA`, or the `0xC61C0/C2/C4`
  blanked cells), so that the delivered value and the monitor's expectation diverge under V287.
- **F2** — any DTC, lockstep or plausibility path whose *input* moves in the direction of its threshold
  when the D transient shrinks.
- **F3** — a rate-limited or dwell-based window (governor slew, oscillation-detector timeout, STEER_STATUS
  debounce, soft-EME persistence) that a **slower** demand rise **lengthens** into a trip.
- **F4** — a loop in which the D kick is what prevents a slower mode from winding up, i.e. the D clamp is
  a **stabilising** nonlinearity, such that a smaller kick **increases** the P-only stall dwell at the
  `0xC61B8 = 102` deadband.
- **F5** — an engage/disengage or fault path that seeds E_prev or a D state from a cal assuming 10240.
- **F6** — a hidden second delta, or a CRC that does not recompute.

**VERDICT: PASS on all six.** Two items go to the orchestrator as **REPORTS**, not blocks — one of them
(R1) will corrupt the reading of the drive if it is not carried into the scoring, and one (R2) corrects
a premise the session's own r39 read rests on.

---

## 1. THE DELTA IS FIVE BYTES, AND FOUR OF THEM ARE THE CRC [EVIDENCE]

Full-image byte diff **V287 vs V282**: **exactly 5 differing bytes.**

| offset | V282 | V287 | what |
|---|---|---|---|
| `0xC61B7` | `0x28` | `0x0A` | the D clamp `0xC61B6`, 10240 to 2560 (low byte `0x00` both ways) |
| `0xC6FFC`-`0xC6FFF` | `75eadf72` | `acf36eac` | CRC trailer of the `[0xC6000, 0xC6FFC)` cal page |

`zlib.crc32(img[0xC6000:0xC6FFC])` = **`0xACF36EAC`**, and the stored trailer is **`0xACF36EAC`**.
**Recomputed independently of the build script. MATCH.** **F6 clear** — no hidden second delta, no code
byte, and the whole region `[0x00000, 0xC0000)` is byte-identical between V287 and V282.

Frozen cells re-read from the **built image**, not from the script's constants:

| cell | role | stock | V282 | V287 |
|---|---|---|---|---|
| `0xC61B6` | **D clamp** | 10240 | 10240 | **2560** |
| `0xC61B8` | post-lag deadband | 102 | 102 | 102 |
| `0xC61BA` | integrator anti-windup | 10240 | 10240 | 10240 |
| `0xC61BC` | P clamp | 15360 | 15360 | 15360 |
| `0xC61BE` | post-gain sum clamp | 15360 | 15360 | 15360 |
| `0xC61B4` | T clamp | 512 | 3072 | 3072 |
| `0xC6206`/`0xC6208` | governor slew fast/slow | 512/205 | 512/205 | 512/205 |
| `0xC620A` | oscillation-detector threshold | 12800 | 12800 | 12800 |
| `0xC64DD`/`0xC64FA` | detector timeout / floor | 50/5 | 50/5 | 50/5 |
| `0xC6202` | soft-EME bound | 4762 | 4762 | 4762 |
| `0xC64A3` | **deadband ARM byte** | 1 | 1 | 1 |

---

## 2. THE SCANNER, AND ITS FOUR POSITIVE CONTROLS

An opcode-aware raw-Python gp/tp scanner over the whole image, with the V850E2 load/store opcode field
recovered **empirically from eleven known sites** rather than assumed:
`0x38 ld.b · 0x39 ld.h|ld.w · 0x3A st.b · 0x3B st.h|st.w · 0x3C/0x3D ld.bu · 0x3F ld.hu`, with the
`ld.h/ld.w` and `st.h/st.w` width taken from `hw2` bit 0, `ld.hu` displacement as `hw2 & 0xFFFE`, and the
`ld.bu` displacement bit 0 carried in the opcode field.

⚠ **My first pass had `0x3A`/`0x3B` wrong and returned 2 accesses for `gp-0x3d3c` where the record says
4 — i.e. it was silently blind to every store.** It was caught only because a control failed. Recorded
because it is the exact class of error a store-blind census produces: a cell that looks read-only.

**Controls, named before each run:**

| control | expected | got | result |
|---|---|---|---|
| `0xC646C` (tp) | 5 sites | 5 — `0x2A904`, `0x2B656`, `0x2C488`, `0x36686`, `0x3684A` | **PASS** |
| `gp-0x3d3c` | 4 accesses, 2 live 2 orphan | 4 — `0x2A178` ld.w, `0x2A1B0` st.w, `0x2A89A`, `0x2A8BA` | **PASS** |
| `gp-0x6c2c` | 8 accesses, 2 w / 6 r | 8, exactly the record's addresses | **PASS** |
| `mov imm32 == 0xC6000` | the 4 known UDS sites | `0x146DC`, `0x59560`, `0x5963E`, `0x59862` | **PASS** |

⊕ Incidental correction to the census trace: its first control address is printed as `0x2A944` in
Addendum 1 and `0x2A904` in Addendum 4. **The byte-correct value is `0x2A904`** (`ld.h 0x746c,tp,r6`).
The other four agree. Not load-bearing — that site is inside the unreachable duplicate block.

---

## 3. F1 — THE PUBLISHED-INTERMEDIATE CENSUS. NO MONITOR EXISTS. [EVIDENCE]

I first re-derived **what** the PID publishes, rather than taking the brief's `0x2A17C`-`0x2A1A2` on trust.
Every gp-relative **store** inside the live PID, resolved and grouped, gives the publish block:

| site | cell | address | quantity |
|---|---|---|---|
| `0x2A17C` | `gp-0x6b2e` | 0xFEDF14D2 | the PID **sum** entering the output lag (`st.h r12`) |
| `0x2A188` | `gp-0x6b32` | 0xFEDF14CE | `r29` |
| `0x2A18C` | `gp-0x6cf8` | 0xFEDF1308 | P-path 32-bit state (`0x7FFFFFFF` on reset) |
| `0x2A190` | `gp-0x6dd0` | 0xFEDF1230 | **integrator** 32-bit state |
| `0x2A19C` | `gp-0x6b36` | 0xFEDF14CA | **E_prev** (`r27`, the operand of `sub r27,r8` at `0x29EE2`) |
| `0x2A1A2` | `gp-0x6b34` | 0xFEDF14CC | `r22` |
| `0x2A206` | `gp-0x6b30` | 0xFEDF14D0 | previous post-taper output |
| `0x2A23C` | `gp-0x6b38` | 0xFEDF14C8 | **T**, the delivered lane torque / 427 tap source |

**Full-image reader census of each, split live / orphan `[0x2A508, 0x2B422)`:**

| cell | LIVE readers outside the PID | verdict |
|---|---|---|
| `gp-0x6b2e` sum | **ZERO** (1 orphan ld.h at `0x2A896`) | **write-only in live code** |
| `gp-0x6b32` | **ZERO** | write-only |
| `gp-0x6b34` | **ZERO** | write-only |
| `gp-0x6b36` E_prev | **ZERO** | write-only |
| `gp-0x6b30` | **ZERO** (self-read at `0x2A1D4`) | private to the PID |
| `gp-0x6cf8` | **ZERO** (self-read at `0x29E5E`) | private |
| `gp-0x6dd0` | **ZERO** (self-read at `0x29DA4`) | private |
| `gp-0x6b38` **T** | **THREE** — `0x4E8D2`, `0x4E8E2`, `0x55DF0` | adjudicated below |

⭐ **The PID's D, P, sum and E_prev are published to cells that NOTHING in live code reads.** They are a
diagnostic mirror. **There is no monitor to mismatch**, so F1 cannot be constructed from them.

**The three live readers of T, each adjudicated:**

1. **`0x4E8D2` / `0x4E8E2`** — the paired read that looks most like a range check. It is **not**.
   `FUN_0004e82e` decompiles to a **CAN frame builder**: it writes `T >> 8` and `T & 0xFF` into bytes 7
   and 8 of the buffer at `*(param_1+8)`, alongside `gp-0x6a56`, `gp-0x4f60`, `gp-0x6807` and a
   packed flag byte, then zero-fills the remainder and sets the length to `0x38`. **No comparison, no
   threshold, no DTC on T.** Its only fault call, `FUN_00020436(0x31)`, sits on the `else` of a
   *pre-existing* fault-mask test `(*(uint *)(&DAT_00006400 + gp) & 8)` that never touches T.
2. **`0x55DF0`** — inside `FUN_00055d80`, the **427 torque tap** the kit already owns (the record's
   "427 source `0x55DF2`"). Telemetry, not an interlock.
3. `0x2B418` is in the unreachable block.

**Register-indirect blind spot, closed with its own control.** The published cells occupy the contiguous
span `0xFEDF14C8`-`0xFEDF14D4`, exactly the shape a walking pointer would address. Scanned for
(a) `mov imm32` and (b) `movhi`+`movea` pairs materialising any base in `0xFEDF14C0`-`0xFEDF14E0`, and
(c) 4-byte-aligned absolute dwords into that window. **ZERO hits on all three**, with the `0xC6000`
control passing on the same scanner. ⚠ **Residual I will not paper over:** I did not bound the copy
lengths of the 324 `mov imm32` RAM bases the census trace records, so a long block copy reaching this
window is bounded, not excluded. It would also have to be a *reader*, and no consumer of such a copy was
found.

**The other 10240-holding cells, re-checked as the brief asked:**
- **`0xC61BA`** (integrator anti-windup, also 10240) has **1 live reader**, `0x29DA0`, inside the PID's
  own anti-windup arithmetic. It is not a monitor, it is not fed by D, and V287 leaves it at 10240.
- **`0xC61C0/C2/C4`** (12 live readers) are the **engage-permission entry ladder** at `0x2924A`,
  `0x2925E`, `0x2926E` and their `FUN_0002a30e` twins. Freshly disassembled: each is `ld.hu` followed by
  `cmp rN, r28` and an **unsigned** `bh`/`bnh`. **All three cells are `65535` in V282 and V287**, so
  `r28 > 65535` is impossible for a ushort and **every one of those branches is structurally dead** — the
  ladder falls through regardless of anything V287 changes. Inert before the edit, inert after.
- **No hard-coded 10240 exists inside the live PID.** An image-wide scan for `0x2800` as an imm16
  operand returns 52 sites; the 12 that are real `movea 10240, r0, rN` constant loads are at `0x25CA2`,
  `0x26EA6`, `0x26ECA`, `0x27446`, `0x276EC`, `0x2C4BE`, `0x36176`, `0x3A7D4`, `0x3A84A`, `0x3ACF6`,
  `0x3B62E`, `0x5EFA0` — **none inside `FUN_00028ea6`, and none reads any published intermediate**
  (the reader census above is empty for all of them). The rest are `addi`-form unsigned compares and
  data.

⇒ **F1: CLEAR.** No consumer anywhere recomputes D, and the four `ld.hu 0x71b6[tp]` readers are the one
symmetric clamp.

---

## 4. F4 — THE GATE-2 CRUX, AND IT INVERTS A PREMISE THIS SESSION IS USING 🛑

The brief's sharpest question: could a smaller D kick **increase** the P-only stall dwell at the
`0xC61B8 = 102` deadband that the r39 read found? The mechanism is real — D is the fast component that
lifts the lag output past the deadband — so this was the likeliest FAIL.

**It cannot happen ENGAGED, because the deadband is gated OFF when engaged.** Disassembled at
`0x2A1AC`-`0x2A1E6`, byte-identical to stock in V287:

```
0002a1ac  sar   0x5, r9                  ; y = lag output
0002a1ae  cmp   0x1, r16                 ; r16 = cal(0xC64A3) byte = 1   <-- the ARM
0002a1b0  st.w  r7, -0x3d3c, gp
0002a1b4  bne   0x0002a1e6               ; arm != 1  -> SKIP the whole block
0002a1b6  ld.bu -0x6806, gp, r12         ; the LKAS-active state byte
0002a1ba  cmp   r0, r12
0002a1bc  bne   0x0002a1e6               ; gp-0x6806 != 0  -> SKIP the whole block   <<<<
0002a1be  ld.h  0x71b8, tp, r6           ; +102
   ... |y| <= 102            -> y = 0    ; the DEADBAND
0002a1d4  ld.h  -0x6b30, gp, r13         ; previous output
0002a1da  mul   r13, r6, r0              ; y * y_prev
0002a1e0  bgt   0x0002a1e6               ; product > 0 -> keep
0002a1e2  mov   0x0, r9                  ; SIGN CHANGE -> y = 0
```

`cmp r0, r12` sets Z iff `r12 == 0`; `bne` is taken iff `r12 != 0`. **So the deadband AND the
sign-change zeroing both execute only when `gp-0x6806 == 0`.**

**`gp-0x6806 != 0` is the LKAS-active state [EVIDENCE, two independent sites]:**
- Freshly disassembled in the PID's own mode dispatch: at `0x29588` the handler writes **`4`** to the
  STEER_STATUS byte `gp-0x679f` and immediately `st.b r6, -0x6806` (non-zero); at `0x29690` the handler
  writes **`6`** and `st.b r0, -0x6806` (zero). Four handlers write non-zero, four write `r0`.
- The census trace's Addendum 2 independently reads `0x3AA94 ld.bu -0x6806,gp,r15` … `setfne lp` as
  `lp = (gate != 0) = ENGAGED`, the V104 repoint. Same cell, same polarity, different function.

⇒ **F4: CLEAR. V287 cannot lengthen an engaged stall dwell through `0xC61B8`, because that deadband
never runs engaged.** GATE 2 discharged on this path.

🛑 **REPORT R2, and it is a correction, not a caveat.** The kit memory
`accord-v281r3-flew-the-7hz-cycle-is-gone-the-p-only-deadband-arrived…` attributes r39's **7 engaged
stall runs at idx 54-79** to *"the P-only DEADBAND"*. If `0xC61B8` is the cell meant, **that attribution
cannot be right** — the cell is unreachable in engaged frames. The engaged stalls are something else:
the `0xC61B4 = 3072` T clamp, the `0xC61BE = 15360` sum clamp, or the plant. **This does not block
V287** (V287 leaves all three frozen), but it does mean the stall-dwell prediction in the pre-registration
should not be scored against `0xC61B8`. I did not re-derive what *does* cause the engaged stalls; that is
the next question, not mine. **[EVIDENCE for the gating; BELIEF that the memory's "deadband" refers to
`0xC61B8` — I inferred that from the cell the r39 read names, and did not read the r39 working.]**

**F5, and why D has no state to seed [EVIDENCE].** `D = ((E − E_prev) · Kd) >> 3`, clamped. It is
**memoryless**: the only persistence is `E_prev` (`r27`), which is the *error*, not D, and the clamp is
applied *after* the subtraction. The reset branch at `0x2A164`-`0x2A172` seeds `r27 = 0`, `r24 = 0`,
`r29 = 0`, `r22 = 0`, `r16 = 0x7FFFFFFF`, `r12 = 0` — **by immediates, from no cal at all**. So at the
engage transition ΔE = E − 0, a full-size first-tick kick, and that is precisely the tick where the clamp
binds hardest. **Lowering it to 2560 shrinks the engage-transition kick about 4x, which is the safe
direction.** ⇒ **F5: CLEAR.**

---

## 5. F2 / F3 — EVERY FREQUENCY- OR DWELL-SENSITIVE MONITOR MOVES AWAY FROM ITS THRESHOLD

Each of these is a **high-pass or large-signal** acceptance test. A smaller D transient is *less*
excitation on every one of their inputs. None has a "too slow" arm that a blunted rise could trip.

| monitor | input | gate | direction under V287 |
|---|---|---|---|
| **Oscillation detector `FUN_000428d4`** | `gp-0x6c2c`, rotor-rate derivative | needs **15 alternating crossings of ±12800**, each within **50 ticks** of the last, else `st.b r0, -0x357c` **wipes the count to zero** | Away. It needs oscillation *faster than 10 Hz and at least 80 % of full scale*; less D means less 18-22 Hz excitation into the plant. A **slower** rise cannot help it — a longer gap **times the FSM out**. |
| **Governor slew `FUN_0004503c`** | demand rate | asymmetric ±205/tick (±512 below 16.6 km/h); motion toward zero and sign crossings immediate | Away. Less D means the demand rises **slower**, so it is rate-limited **less**, not more. A shaper, not a cut; `FUN_0004595a` checks only magnitude-vs-target with matching sign, guaranteed in every branch. |
| **Soft-EME `FUN_00042af8`** | `gp-0x6acc`, ±8192 zero-reject | amplitude + persistence, not frequency | Cannot fire either way: bounded by `0xC6202 = 4762` + compensation ≤ 2560 = **7322 against 8192**, margin 870, and both terms sit downstream of the governor clamp. V287 changes neither cal. |
| **Lockstep DTC `FUN_00043e44`** | recomputed shaper **bounds** (`0xC6598` corridor, `0xC65C4` boost), ±5 LSB | not frequency-dependent | Untouched. V287 edits neither arm, so the integer-vs-float delta stays 0. It cross-checks the *bound*, never the signal. |
| **STEER_STATUS debounce `0xC64DF = 100`** | tick count | dwell | Untouched cal; D does not gate the state machine. |

⇒ **F2 and F3: CLEAR.** The build's own pre-registration Q7 ("a x0.6 detector step V282 does not show")
is the right instrument for the one monitor that could plausibly matter, and it is aimed the correct way.

---

## 6. 🛑 REPORT R1 — THE CAVE BITS ARE UNCHANGED, BUT BIT 6's MEANING SHIFTS. STATE THE DIRECTION.

V287 touches **no** cave byte: `[0x00000, 0xC0000)` is byte-identical to V282, so the cave at `0xC4B34`,
the hook at `0x55C0E` and the 427 tap at `0x55DF0` are all intact. **The bits still compute what they
computed. What changes is the quantity one of them is comparing against.**

From `build_v282_tva.py` (lines 53-54), the live rungs are:
- **bit 6** (`0x14A` byte 4, `0x40`) = **`|gp-0x6ada (r24)| >= |gp-0x6b38 (T)|`**
- **bit 5** (`0x20`) = `|r24| >= |gp-0x6b94 (aggregator sum)|`

**T is on the far side of the D clamp.** V287's own replay predicts T's 18-22 Hz onset envelope at
**x0.33-0.79**, steady creep **x0.98-1.03**. Bit 6 fires when `|T|` is *small* relative to `|r24|`, so:

⭐ **PREDICTED DIRECTION: bit-6 duty RISES under V287, concentrated on command-step / onset ticks, with
steady-creep duty roughly unchanged.** Bit 5 shifts in the same direction only insofar as the aggregator
carries T, so its move should be smaller.

**Why this is a misattribution risk and not a curiosity.** `build_v282_tva.py` ships a **decision table
keyed on absolute bit-6 duty**: *"bit 6 duty >= 0.22 in engaged creep => 5244 arm live, r24 dominant, do
NOT cut"* and *"bit 6 duty <= 0.10 => go to the output-lag/feedback-pole levers instead."* Those thresholds
were calibrated against **V282's T**. `build_v287_tva.py` **never mentions bit 6 at all**, so a V287 drive
scored against the inherited table would read a mechanically-induced duty rise as evidence that *"the
r24 arm is live and dominant"* — biasing the next lever exactly the wrong way, and away from the pole
levers that a low duty would have pointed to.

**Recommendation (a report, not a block): score bit-6 duty on V287 only DIFFERENTIALLY — onset ticks
against same-drive steady creep — and do not carry V282's 0.22 / 0.10 absolute thresholds across.**
This is the kit's own standing rule, *attribute the build from the tap, not from the label*, applied to a
threshold instead of a build number.

---

## 7. THE NULL RISK, RESTATED WITH ITS ARITHMETIC

Not an interlock finding, but it bounds what the drive can conclude, and the build script raises it
honestly, so I checked the numbers rather than repeating the sentence.

`P = (E · Kp) >> 8` clamped to ±`0xC61BC` = 15360; `D = ΔE · 16` clamped to ±`0xC61B6`; the **sum** is
clamped to ±`0xC61BE` = **15360**. With Kp flat 248, `P ≈ 0.969·E`. D's contribution survives only while
`|P| < 15360 − |D|`. So the edit can bite only when **`|P| < 12800` AND `|ΔE| > 160`**; whenever P alone
already fills the sum clamp, 10240 and 2560 deliver **the identical sum** and V287 is byte-for-byte
inert on that tick.

That region is wide enough that the build is **not** structurally inert — this is a real null *risk*,
not a null *prediction*. But it is the reason Q3 (the same-drive steady-creep negative control) is the
load-bearing half of the pre-registration, not Q2. **A Q2 move without a Q3 control is uninterpretable.**

---

## 8. VERDICT

**PASS — no interlock, no DTC, no lockstep, no plausibility check and no downstream consumer is
disturbed by `0xC61B6` 10240 to 2560.** The specific reasons, each re-derived from the image:

1. The PID's published D / P / sum / E_prev cells have **zero live readers**, by an operand-text census
   with four passing controls, **plus** a negative register-indirect scan with its own control.
2. T's only three live readers are a **CAN frame builder** and the kit's **427 tap**. Neither compares,
   thresholds, or faults on it.
3. Nothing recomputes D. `0xC61BA` has one live reader on a different term; `0xC61C0/C2/C4` are
   structurally dead at 65535; no hard-coded 10240 exists in the live PID.
4. Every frequency- or dwell-sensitive monitor is a **high-pass, large-signal** acceptance test, and a
   smaller D transient moves **away** from all of them. No monitor has an arm that a slower rise trips.
5. The D term is **memoryless**; the engage transition seeds `E_prev = 0` from an immediate, not a cal,
   and the lower clamp shrinks the transition kick.
6. Five bytes changed, four of them the CRC, and the CRC recomputes correctly from the image.

**Two things must travel with the build:**

- 🛑 **R1** — **bit-6 duty will rise for a mechanical reason.** Score it differentially; do not apply
  V282's absolute 0.22 / 0.10 thresholds to a V287 drive. Unaddressed in `build_v287_tva.py`.
- 🛑 **R2** — **the `0xC61B8 = 102` deadband is gated OFF whenever engaged** (`gp-0x6806 != 0` at
  `0x2A1BC`). This *clears* V287's GATE-2 stall-dwell concern, and it also means r39's engaged stall runs
  cannot be attributed to that deadband. That premise should be re-derived before it carries any further.

**What I did NOT close**, stated plainly: block-copy reach of the 324 `mov imm32` RAM bases into
`0xFEDF14C0`-`0xFEDF14E0` is bounded by the absence of any reader, not excluded by a length analysis;
and `ep`-relative (`sld`/`sst`, and `ld` with `ep` as base) is a **third addressing mode my census does
not cover** — the PID uses it at `0x29EC8`/`0x29ECE` for the Kd LERP table. Neither affects the D clamp,
whose four readers are all direct `ld.hu 0x71b6[tp]`, but I am not quoting either as a census.
