# ADVERSARY B — V288 · surface #2 UNITS / SCALE / LOOP / LAG COST

**Agent**: `advB` (subagent). Adversarial pass, 2026-09-07. Nothing built, flashed, or sent.
**Target**: `../accord-firmwares/analysis-2020accord/_v288_V288-V282BASE-SPFILT.K4-KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`
**sha256 verified by me this session**: `bc8a5b1ac2f796faa5563bb79e221a2f884f55ec040c654114fa2861f2ef5571` (1,048,576 B) — matches the pre-reg.
**Programs**: stock `code.bin` in Ghidra for all disassembly (`dry_run:true` throughout, nothing saved,
program not switched or closed); **every numeric fact below is read from the V288 image with Python**,
never from the build script's constants.
**Pre-registration**: `docs/review/ADVERSARIAL-V288-PREREG-2026-09-07.md`, FAIL definition #2.

---

## VERDICT — **PASS WITH CONDITIONS**, one of which is blocking on the literal text of pre-reg FAIL #2

The scale, range and Q-format assumptions hold with a large margin, and hold for a **stronger structural
reason than the spec gives**. The lag cost is real but bounded and is not provably fatal. **One genuine
defect was found**, and it is the kind the pre-reg was written to catch:

> 🛑 **`gp-0x6a32` is the ONLY piece of this controller's state that the firmware's own disengage-reset
> path does not clear.** The reset at `0x2A164` explicitly zeroes the integrator and four other state
> cells; V288 adds a sixth state cell and does not add it to that reset. On re-engage the setpoint
> resumes from the value it held at the last engaged tick, which can be up to a full-scale command from
> an arbitrary time in the past.

Cost, simulated bit-exactly against the cave's own integer arithmetic: **up to 12 ms of fully railed
P-term in the pre-disengage direction**, and up to **10 ms of setpoint sign opposite to the raw
command**, at the instant of re-engage. That is literally *"engage/disengage transients produce a
setpoint the raw path could not produce (sign flip)"* — pre-reg FAIL #2's last clause. I record it as a
**CONDITION rather than an outright FAIL** because the magnitude is bounded by the same worst case a
single full-range 0xE4 command step already produces while engaged, and because the filter cannot
overshoot. **The call is the orchestrator's, and it should be made explicitly rather than by default.**
The fix is four bytes on a path that already exists (§5.3).

Everything else on this surface: **PASS.**

---

## 1. THE Q-FORMAT AND RANGE OF `sp` AT THE HOOK — re-derived from the image

### 1.1 The chain, re-read from bytes

`disassemble_bytes` (dry-run) over `0x29C70`–`0x29D77`, 71 instructions, `truncated:false`.

```
0x29CB4  mulu  r6, r10, r0     ; speed/torque LERP product
0x29CBC  mul   r22, r7, r0     ; r22 = the raw 0xE4 command
0x29CC0  sar   0x10, r7        ; >>16   \  Q16 de-scale, total >>22
0x29CD6  sar   0x6, r7         ; >>6    /
0x29CD4  mov   0x1, r8         ;  \
0x29CD8  cmovn -0x1, r8, r8    ;  /  r8 = sign(command) ∈ {+1, -1}
0x29CD0  ld.bu 0x74f0,tp,r16   ; cal(0xC64F0) = 240   (tp=0xBF000)
0x29CDC..0x29CFA               ; clamp r7 to ±cal, then |r7|
0x29D10  mov   r7,r22 ; zxb r22; ld.hu ... ; st.b r22,-0x674b,gp
0x29D12  zxb   r22            ; idx = low byte of |cmd|, 0..240
0x29CFC  mov   0xc9a88, r16   ; MAP POINTER TABLE
0x29D06  sld.w 0x0,ep,ep      ; ep = *(u32*)(0xC9A88 + selector*4)  -> X knots
0x29D1A  addi  0x16,r6,r6     ; r6 = same pointer + 0x16            -> Y knots
0x29D26/0x29D3C/0x29D4C..68   ; bracket walk + mul/divq LERP  ->  r13 = Y(idx), UNSIGNED
0x29D6A  mov   r8, r16        ; r16 = ±1
0x29D6C  mulh  r13, r16       ; r16 = sp = (±1) × r13
0x29D6E  ld.hu 0x72e4,tp,r10  ; cal(0xC62E4)=4   LIVE across the hook
0x29D72  <<< HOOK >>>
0x29D76  shl   0x5, r16       ; 32·sp
0x29D78  sub   r26, r16       ; E = 32·sp − fb
```

### 1.2 The map tables, read from the V288 image

Pointer table `0xC9A88`, stride 4; each record is 44 B = 11 X halfwords then 11 Y halfwords.
`X[0]` is a **count (10)**, `X[1..10]` are the knots and `Y[0..9]` the values (`Y[10]` is unused
padding — confirmed by `ld.hu 0x12,r6,r13` at `0x29D3C`, which saturates high onto `Y[9]`, not `Y[10]`).

| selector | record | X knots (`X[1..10]`) | Y values (`Y[0..9]`) | **max Y** |
|---|---|---|---|---|
| 0,1,3,4,6, **7 (live)** | 0xE4000 … 0xE502C | 0,12,20,24,32,64,96,128,160,240 | 0,52,86,103,138,275,413,550,688,1032 | **1032** |
| 2,5 | 0xE4058, 0xE40DC | same | 0,54,90,108,144,288,432,576,720,1080 | 1080 |
| 8,9 | 0xE5058, 0xE5084 | same | 0,56,94,113,150,301,451,602,752,1128 | **1128** |

Byte-identical to V282 for all ten records (checked). `1032/240 = 4.300` and `688/160 = 4.300` — the
linearity claim inherited by the spec is **confirmed from the raw table bytes**, which the spec itself
did not do.

### 1.3 EXACT RANGE — and why the spec's reason is wrong while its answer is right

**`sp` range: ±1032 on the live selector 7; ±1128 on the worst reachable selector (8/9).**
[EVIDENCE — table bytes above, `cal(0xC64F0)=240` read from the image, selector max 9 per
`accord-variant-selector-max-is-nine`.]

🛑 **The spec (§3.1) says `mulh` is a "16×16→16 signed multiply". That is FALSE — V850 `mulh reg1,reg2`
writes a full 32-bit product into `reg2`.** The build script's own docstring gets this right ("a full
32-bit signed `mulh` product"), so the spec and the script contradict each other on the single fact
that decides whether the cave's 16-bit read-back is lossless. **A future build that trusts the spec's
sentence will size a different hook wrong.** Report this as a documentation defect.

The conclusion nevertheless holds, for a **stronger reason than either document gives**:

> Because `r8 ∈ {+1, −1}` at `0x29D6A`, the `mulh` product is **exactly `±signed16(r13)`**. A product of
> ±1 with any 16-bit value always fits in 16 bits, for every possible table content, with the single
> exception `r13 = 0x8000` paired with `r8 = −1`. **`sp` is structurally int16-safe, not merely
> numerically safe.**

I verified `r8` is untouched between `0x29CD8` and `0x29D6A`: over the 32 instructions in that span the
written registers are r7, r16, r6, r22, r10, r9, r13, r2, ep — **r8 appears nowhere**. Both paths into
`0x29CD0` (fall-through from `0x29CCE` and `br` from `0x29CC2`) converge before `mov 0x1,r8`.

**⇒ The FAIL condition "the cave's reload returns a DIFFERENT r16 than the original untruncated path"
is UNREACHABLE.** Margin at the live selector is 32767/1032 = **31.8×**; at the worst selector 29.0×.

Steady state is exact in both directions: an integer sweep of the cave's own arithmetic over
`sp ∈ [−1200, 1200]` from seven starting values found **zero** non-converging pairs — the `+1`
correction closes the positive side and `sar` closes the negative side.

---

## 2. TICK RATE

**Finding: 1 kHz. EVIDENCE for the firmware half; ONE INHERITED LINK for the wall-clock half.**

What I proved myself this session:

1. `FUN_00028ea6` (body `0x28EA6`–`0x2A30D`, contains the hook) has exactly **one** caller,
   `0x22522` inside `FUN_0002214a`. A raw Python Format-V scan, **positive-controlled** against the
   three known call sites in the decompile skill (`0x22522→0x28EA6`, `0x23276→0x34350`,
   `0x2291E→0x3AA2C`, all three found), confirms it.
2. `FUN_0002214a` has **no** `jarl` caller anywhere in the image. It is reached from a dword pointer at
   `0xBB928`, inside an RTOS task/handler table of stride 0x30 (siblings `0x22A88` at `0xBB958`,
   `0x22B20` at `0xBB988`, each with its own stack base and an id/priority word). **The table carries no
   period field I could identify, so the tick rate is NOT derivable from the call graph.**
3. `FUN_0002214a` increments a 32-bit counter at `gp-0x6d28` and a 16-bit counter at `gp-0x3e54` by
   exactly 1 per invocation — it is a *one-shot per period* handler, not a loop with an internal wait.
4. **The debounce anchor is real and it is inside this function.** `cal(0xC64DF) = 100`, read from the
   V288 image, is loaded at `0x29288` (`ld.bu 0x74df,tp,r10`) and stored to `gp-0x6757` as a counter
   **reload**; `gp-0x6757` is incremented by one at `0x29276` (`add 0x1,r12; sxb r12; cmp r0,r12`) on
   each pass through that state. **So 100 passes of `FUN_00028ea6` = one debounce interval.**

What I did **not** re-derive: the CAN-bus measurement that this interval is 100.00 ms. That is inherited
from `TRACE-2026-09-06 §3.2`. Given (4), that measurement divides directly:
**100 calls / 100.00 ms = 1.00 ms per call = 1 kHz.**

⇒ **The build script's `TICK_HZ = 1000.0` is correctly labelled BELIEF, and I now upgrade it to
EVIDENCE-with-one-inherited-link.** I could not refute it and I could not find a second independent
in-image anchor. §4 gives the phase table at 500 Hz and 2 kHz as well, so the conclusions do not rest
on it.

---

## 3. GATE 2 / LOOP STRUCTURE — every consumer of `sp` and of `gp-0x6a32`

### 3.1 `gp-0x6a32` (0xFEDF15CE) — full census from the V288 image

Raw Python LE scan of the 4-byte disp16 gp-relative form over `[0x13000, 0x100000)`, all load/store
opcode fields, **positive-controlled** (the scan finds the known dead writer at `0x2AC68` and the cave's
own four accesses; it correctly no longer finds `0x29D72`, which is now a `jr`):

| address | access | live? |
|---|---|---|
| `0x2AC68` | `st.h r9` | **dead** — inside `[0x2A508, 0x2B422)`, the proven-unreachable duplicate PID |
| `0xC4BDC` | `ld.h → r9` | cave: `y[n−1]`, **sign-extended** |
| `0xC4BF2` | `st.h r16` | cave: publish `y[n]` |
| `0xC4BF6` | `ld.h → r16` | cave: read-back so register and cell cannot diverge |
| `0xC4C02` | `ld.h → r6` | telemetry rung: `sign(y)` → 0x14A byte 4 bit 0 |

**Zero readers outside the two caves. The filter cannot change any feedback return ratio, because no
feedback path passes through this cell.** [EVIDENCE, positive-controlled scan.]
The sign handling is correct: both reloads are `ld.h` (opcode field 0x39, `hw2` bit 0 = 0), **not**
`ld.hu`. A `ld.hu` here would have turned every negative setpoint into ~+64000 — it is not present.

### 3.2 Does the RAW `sp` survive the hook anywhere?

- **`r16`** — the only consumer at `0x29D76` is `shl 0x5` → `sub r26,r16`. No copy of `r16` is taken
  between `0x29D6C` and the hook.
- **`r13`** (the raw map magnitude `|sp|`) — **DEAD after the hook.** On the `ble` path it is rewritten
  at `0x29D8C` (`ld.hu 0x72e4,tp,r13`); on the fall-through path at `0x29DA0`
  (`ld.hu 0x71ba,tp,r13`). Both paths write before any read. So the unfiltered magnitude reaches
  nothing. [EVIDENCE — `disassemble_bytes` `0x29D76`–`0x29DF6`.]
- **`r8`** (the raw sign) — consumed only by `mov r8,r16` at `0x29D6A`; next appearance is a write
  (`mov r16,r8` at `0x29EE0`), and at `0x29EC0` it is already a table base pointer.
- **`gp-0x697a`** — `st.h r7` at `0x29DDA` publishes the *raw clamped* `|cmd|`. Its only other access in
  the image is `0x2ACCE`, inside the unreachable duplicate. **Another dead publish, zero readers.** No
  inconsistency is created because nothing consumes it.

**⇒ After the hook there is exactly one live descendant of the setpoint, and it is the filtered one.**

### 3.3 What the downstream terms actually read — and one carry-forward hazard

Re-read from `0x29D76`–`0x29DF6` and `0x29EC0`–`0x29F06`:

| stage | reads | consistent with the raw command? |
|---|---|---|
| deadband | `E>>5` vs `cal(0xC62E4)=4`, symmetric ±4 | E-derived ✓ |
| I term | `Ki = cal(0xC63E6) = 0` × deadbanded error; accumulator `gp-0x6dd0` | E-derived ✓, and **inert** — `gp-0x6dd0`'s only live write is the reset at `0x2A190`, so the accumulator is permanently 0 |
| anti-windup | `cal(0xC61BA)=10240`, scaled ×128 | E-derived ✓ |
| **Kp / Kd LERP index** | **`r7` = the RAW clamped `\|cmd\|`, published at `0x29DDA`** | ⚠ **raw, NOT filtered** |
| D term | `mov r16,r8; sub r27,r8` → `dE`, × Kd LERP, `sar 0x3`, clamp ±`cal(0xC61B6)=10240` at `0x29EE8`–`0x29F06` | E-derived ✓ |

⚠ **CARRY-FORWARD HAZARD.** The Kp/Kd gain schedule is indexed by the **raw** command, so for ~15 ms
after a command step the loop runs the *new* gain against the *old* (smaller) error. **In V288 this is
harmless only because V282 made the Kp LERP flat at 248 across all five knots** (`LIVE_KP_Y = (248,)*5`,
`Kd = 128`) — with a flat table the index cannot matter. **If any future build restores a sloped Kp or
Kd, this becomes a live gain/error mismatch that V288 introduces and nothing measures.** Not a defect in
this image; a trap for the next one.

**GATE 2 verdict: PASS.** The filter is a textbook 2-DOF **reference pre-filter**. It sits on the
setpoint, upstream of `sub r26,r16`, entirely **outside** the feedback path. It therefore does not
appear in the inner loop transfer `L = C·P` at all and **cannot change the inner loop's gain or phase
margin** (the ~50° at 13–15 Hz in `accord-lanechange-ring-is-the-outer-loop…` is untouched). It changes
only the reference-to-output response, which is the outer loop's problem — priced in §4.

---

## 4. OUTER-LOOP COST OF THE ADDED LAG

Computed from the exact discrete filter `H(z) = (1−a)/(1−a·z⁻¹)`, `a = 1 − 2⁻ᴷ`, at three candidate
tick rates so no conclusion rests on §2.

**Phase lag added, in degrees:**

| tick | K | pole a | f_c (Hz) | τ (ms) | 2 Hz | **3.9 Hz** | 7 Hz | 20 Hz | \|H\| @20 Hz |
|---|---|---|---|---|---|---|---|---|---|
| 1 kHz | 3 | 0.87500 | 21.25 | 7.0 | 5.0 | **9.7** | 17.0 | 39.7 | 0.729 |
| 1 kHz | **4 (flown)** | 0.93750 | 10.27 | 15.0 | 10.7 | **20.1** | 33.0 | 59.3 | **0.457** |
| 1 kHz | 5 | 0.96875 | 5.05 | 31.0 | 21.2 | 37.0 | 52.9 | 72.2 | 0.245 |
| 500 Hz | 4 | 0.93750 | 5.14 | 30.0 | 20.6 | 35.8 | 51.2 | 68.5 | 0.249 |
| 2 kHz | 4 | 0.93750 | 20.54 | 7.5 | 5.4 | 10.4 | 18.2 | 42.5 | 0.717 |

The 1 kHz K=4 row reproduces the build script's own table (10.28 Hz, 0.457 at 20 Hz); its τ = 15.5 ms
vs my 15.0 ms is a definitional half-tick, not a discrepancy.

**Against the delay openpilot already models.** `SteerDelay = 0.2 s` (operator's decoded StarPilot
toggles). K=4 adds 15 ms = **7.5 %** of that; K=3 adds 7 ms = **3.5 %**. The pre-reg FAIL clause
*"exceeds the actuator delay openpilot already models"* is **not met, by a factor of 13**. The defensible
statement is proportional: **the outer loop's delay margin shrinks by 7.5 % at K=4.**

**Against the outer-loop phase margin.** 20.1° at the 3.9 Hz crossover is a **substantial** bite.
🛑 **I cannot evaluate the FAIL clause "provably consumes the outer-loop phase margin below unity-safe",
because the outer loop's phase margin has never been measured in this kit.** The record has the inner
loop's PM (~50° at 13–15 Hz) and the outer crossover frequency (~3.9 Hz), but not the outer PM. **So the
clause is not met — and the premise for asserting a PASS on it is equally unproven.** State it that way
on the artifact rather than implying headroom that was never measured.

**The 20 Hz echo path (angle → openpilot → cmd → sp → torque → angle).** openpilot's friction term is a
steep saturating gain (slope `friction/0.3`), so the echo path has real loop gain at 20 Hz.
🛑 **The SIGN of the added delay's effect there is NOT DECIDABLE from what we have.** The wire study
measured cmd/angle phase at only −3° to −20° at 20 Hz
(`rlog-tools/studies/grind/WIRE-0XE4-20HZ-2026-09-07.md`), but the 0xE4 **receive** latency is unknown,
and at 20 Hz a single 10 ms frame is 72° — larger than the entire measured spread. Any claim about
where the loop sits relative to −180° at 20 Hz is therefore unfounded in both directions.

**What IS decidable, and it is the argument that matters:** at 20 Hz the filter cuts the setpoint path's
gain to **0.457 (−6.8 dB)** *at the same time* as it rotates the phase. A first-order lag cannot
destabilise a loop at a frequency where it also removes 6.8 dB of loop gain **unless that loop was
already within 6.8 dB of instability at that frequency.** Combined with the wire study's measured
×0.446 reduction of command content in the 18–22 Hz band, the 20 Hz echo path is **net-favourable or
neutral, and cannot be made worse by more than the phase rotation can overcome the gain cut.** That is
the bound; the sign within it is undecided.

---

## 5. TRANSIENTS — where the defect is

### 5.1 Paths that skip the hook

Python Format-III/Format-V branch scan over the whole function `[0x28EA6, 0x2A30E)`, **positive-
controlled 6/6** against branches read from the Ghidra listing.

- **No branch anywhere targets `0x29D6A`–`0x29D7A`.** The hook is not a branch target and no path
  re-enters it mid-instruction. [EVIDENCE.]
- The map/PID block is entered from `0x29A8A` (`jr → 0x29CC4`) and `0x29C6C` (`bh → 0x29C74`) only.
- **Three unconditional jumps skip the whole block, hook included:** `0x29A5C jr → 0x2A164`,
  `0x29A64 jr → 0x2A164`, `0x29A70 jr → 0x2A0C6`, guarded at `0x29A48`–`0x29A6E` by a set of
  engage/state flags (`r14≠0`, `r8==1`, `r25≠0`, `gp-0x680a==1`).

### 5.2 🛑 `0x2A164` IS THE PID STATE RESET — and `gp-0x6a32` is missing from it

```
0002a164  mov   0x0, r24 / r29 / r27 / r22
0002a16c  mov   0x7fffffff, r16
0002a17c  st.h  r12(=0),  -0x6b2e, gp     ; state cleared
0002a188  st.h  r29(=0),  -0x6b32, gp     ; state cleared
0002a18c  st.w  r16,      -0x6cf8, gp     ; sentinel 0x7FFFFFFF
0002a190  st.w  r24(=0),  -0x6dd0, gp     ; <<< THE INTEGRATOR, the very cell read at 0x29DA4
0002a19c  st.h  r27(=0),  -0x6b36, gp     ; state cleared   (prev-E companion)
0002a1a2  st.h  r22(=0),  -0x6b34, gp     ; state cleared
```

`gp-0x6dd0` is byte-for-byte the accumulator loaded at `0x29DA4` — **so `0x2A164` is unambiguously the
reset for the very PID whose setpoint V288 filters**, and it is reached exactly on the paths that skip
the hook. The stock design invariant is plain: *every* state cell of this controller is zeroed when the
controller is not running. A census of those five cells confirms it — in the live code region their
**only** writes are the ones at `0x2A164` (all other hits fall inside the unreachable duplicate).

**V288 adds a sixth state cell and does not add it to that reset.** `gp-0x6a32` is written only inside
the hook, which these paths skip. **`y` therefore freezes for the entire disengaged interval and is
reused, unmodified, as the filter's initial condition on the next engage.**

### 5.3 The cost, simulated bit-exactly against the cave's own integer arithmetic

`y += (sp−y)>>4`, with the `+1` correction, `fb = 0` at the instant of re-engage (wheel at rest — the
worst case, and the common one). P rails at `|E| = 15855`, so **any `|y_stale| ≥ 496` rails P on the
first engaged tick**.

| `y_stale` → new `sp` | `E` on tick 0 | railed P attributable to staleness | setpoint sign opposite the raw command |
|---|---|---|---|
| +1032 → 0 (re-engage, no command) | +33 024 | **11 ms** | 0 ms |
| +1128 → 0 (worst selector) | +36 096 | **12 ms** | 0 ms |
| +1032 → −1032 (re-engage, reversed) | +33 024 | — (sp itself is past the rail) | **10 ms** |
| −1032 → +1032 | −33 024 | — | **10 ms** |

Convergence to *exact* equality takes 73–99 ms because of the `+1` crawl, but the error is under 16
counts within ~40 ms.

**Why this is a CONDITION and not a clean FAIL.** The filter is a convex combination of `y_old` and
`sp`, so `|y| ≤ max(|y_old|, |sp|)` always — **it cannot overshoot**, and the transient magnitude is
bounded by the same worst case that a single full-range 0xE4 command step already produces while
engaged. The 10 ms of opposite sign is the designed group delay, not a new phenomenon.
**Why it is a CONDITION and not nothing.** At a normal command step the loop is continuous and the
driver and openpilot are both in it. At re-engage it is a discontinuity: the EPS delivers up to 12 ms of
railed assist in the direction of a command that may be seconds old, while every other piece of PID
state starts from zero. It breaks an invariant the stock firmware maintains deliberately.

**THE FIX, for the orchestrator to weigh — I am not applying it.** One instruction,
`st.h r0, -0x6a32, gp` (4 bytes, `64 07 ce 95`), on the reset path alongside the five stores already
there. It needs 4 bytes of room at `0x2A164`, which is in-place code, so it is a displacement problem,
not a free one — but the cave the build already owns could equally clear the cell when it detects the
`0x7FFFFFFF` sentinel at `gp-0x6cf8`, which is set on exactly the same path and read at `0x29E5E`.
**Either route makes the setpoint filter obey the same invariant as the rest of the controller.**

### 5.4 The other transients

- **Engage (`sp` 0 → command)**: `y` ramps from the stale value; covered above.
- **Disengage**: the hook stops running, `y` freezes. No output consequence *while* disengaged, since
  nothing downstream reads `gp-0x6a32` and the PID itself is reset.
- **Override (driver torque, the `0xCBBC4` post-PID fade)**: the taper acts on the PID *output*, not on
  the setpoint, and is indexed by driver torque, not by `sp`. Unaffected.
- **Command sign reversal through zero, while engaged**: 10 ms of opposite-sign setpoint at a full
  ±1032 reversal. This is the group delay, is symmetric, and is the priced cost of the lever.
- **Power-on**: `y` starts at whatever `gp-0x6a32` holds. If the C runtime zeroes this region the first
  engage is clean; **I did not verify the startup zeroing** and flag it as an open item for the
  interlocks surface (adversary D). It is bounded by the same ±32768 argument and by the fact that the
  controller resets everything else on its first disengaged tick anyway.

---

## 6. THE STRATA THAT FAILED V287 REV 1

**D acts on E — confirmed from bytes.** `0x29EE0 mov r16,r8` / `0x29EE2 sub r27,r8` forms
`dE = E[n] − E[n−1]` (`r27` is the previous-sample state, the companion of `gp-0x6b36`, zeroed by the
same reset), then `mul` by the Kd LERP, `sar 0x3`, and clamp to ±`cal(0xC61B6) = 10240` at
`0x29EE8`–`0x29F06`. [EVIDENCE.]

**The filter provably cannot attenuate the feedback component of `dE`.** `E = 32·y − fb`, so
`dE = 32·(y[n]−y[n−1]) − (fb[n]−fb[n−1])`. The hook is upstream of `sub r26,r16`; `r26` is never touched
by the cave. **The `fb` term of `dE` is bit-identical to stock.** This is structural — it follows from
the hook's position alone and does not depend on where D is computed. ✓ as the brief predicted.

**Interaction with the three failed strata — an honest negative prediction.** In all three
(hands-on bar > 700, loaded |ang| > 60, fast wheel > 25 deg/s) the *feedback* term dominates `E`, so
the setpoint's share of `E` — and therefore the filter's share of `dE` — is proportionally **smallest
exactly where V287 rev 1 failed.** **V288 should not be expected to move those strata**, and a null
there is not evidence against the lever. This is consistent with, and sharpens, the pre-reg's own
statement that a PASS licenses nothing about the resonance's damping: the filter bounds the
**excitation**, and in these strata the excitation is not what is large.

---

## 7. SUMMARY AGAINST PRE-REG FAIL #2

| clause | verdict |
|---|---|
| sp Q-format / range not what the cave assumes | **PASS** — ±1032 live, ±1128 worst; structurally int16-safe because `r8 = ±1`; 31.8× margin. Spec's stated *reason* is wrong (`mulh` is 16×16→**32**), its answer is right. |
| filter changes the feedback return ratio / anything reads `gp-0x6a32` or raw `sp` | **PASS** — 0 readers of the cell (positive-controlled scan); `r13`, `r8`, `gp-0x697a` all dead or unread after the hook; the filter is outside the feedback path. |
| added lag provably consumes outer-loop PM below unity-safe | **NOT PROVEN, EITHER WAY** — 20.1° at 3.9 Hz is substantial; the outer loop's PM has never been measured, so neither the FAIL nor a confident PASS is available. Say so on the artifact. |
| exceeds the actuator delay openpilot models | **PASS** — 15 ms vs 200 ms; delay margin −7.5 %. |
| engage/disengage transient produces a setpoint the raw path could not produce | 🛑 **CONDITION / arguably met.** `gp-0x6a32` is excluded from the controller's own reset at `0x2A164`. Up to 12 ms railed P and 10 ms opposite sign at re-engage. Bounded, non-overshooting, and fixable in 4 bytes. |

**Recommendation: hold the flash until the orchestrator rules explicitly on §5.2/§5.3.** If it flies as
built, the re-engage transient must be written on the artifact as a stated pre-drive risk, and the
operator told that a brief tick at the moment of engage is expected and is the known cause.

---
---

# ADDENDUM — premise for the V288 rev 2 engage-time init

Requested by the orchestrator after V288 rev 1 was ruled DO-NOT-FLASH on §5.2. Same method rules:
Ghidra `dry_run` only on stock `code.bin`, every number re-read from the V288 image with Python,
every scan positive-controlled. **Decompile first, then bytes** — the structural claims below come from
the decompile of the containing function; the assembly confirms them.

## A1. `0x2A164` IS NOT A RESET — IT IS A SHARED EPILOGUE. This changes the picture.

My §5.2 called `0x2A164` "the PID state reset". That was **incomplete, and the correction matters for
the fix.** A positive-controlled branch scan of the whole function shows:

```
entry 0x2A164  <-- 0x29A5C jr , 0x29A64 jr                (skip paths: pre-load zeros + the sentinel)
entry 0x2A174  <-- 0x2A14A br , 0x2A15E br , 0x2A162 br   (ENGAGED path: real values)

  0x2A164..0x2A173 = mov 0x0,r24/r29/r27/r22 ; mov 0x7fffffff,r16 ; mov 0x0,r12
  0x2A174..0x2A1A2 = THE STORES, executed on BOTH routes
```

So the stores at `0x2A17C`/`0x2A188`/`0x2A18C`/`0x2A190`/`0x2A19C`/`0x2A1A2` are the **per-tick state
write-back**. The skip paths reach them with zeros and the sentinel pre-loaded; the engaged path reaches
them with the real computed values. **My §5.2 conclusion is unaffected** — on skip ticks every state
cell is still zeroed and `gp-0x6a32` still is not — but the mechanism is a shared epilogue, not a
separate reset routine. **A rev 2 must not try to "add a store to the reset path" as if that path were
private. It is not:** `0x2A174` onward is shared with every engaged tick, so a store added there would
fire on every tick, not only on resets.

## A2. `gp-0x6cf8` — full census, width, tick order, and what it actually does

**Width: 32-bit, confirmed from the encodings.** `0x29E5E` = `ld.w` (opcode field 0x39, `hw2` = 0x9309,
bit 0 = **1** ⇒ word form) and `0x2A18C` = `st.w` (opcode field 0x3B, `hw2` = 0x9309, bit 0 = 1). Both
`gp`-relative, `reg1 = r4`.

**Census — 4-byte disp16 gp-relative scan, positive-controlled:**

| address | access | live? |
|---|---|---|
| `0x29E5E` | `ld.w → r8` | **the only live reader** |
| `0x2A18C` | `st.w r16` | **the only live writer** |
| `0x2AD4A`, `0x2B058` | ld / st | dead — inside `[0x2A508, 0x2B422)`, the unreachable duplicate |

**Tick order relative to the hook: `0x29D72` (hook) < `0x29E5E` (read) < `0x2A18C` (write).** The cave
and the existing reader both see the value the **previous** tick's epilogue wrote. That is exactly the
ordering a "did the previous tick run?" test needs.

**"Set to 0x7FFFFFFF ONLY on the reset path, then overwritten every tick thereafter?" — YES, confirmed.**
A positive-controlled (5/5) scan for the 6-byte `mov imm32,reg` form (`hw1` bits 15:11 = 0, opcode field
`0x31`, destination in bits **4:0** — the destination is `reg1`, not `reg2`, which is why a naive mask
finds nothing) locates `0x7FFFFFFF` loaded into `r16` at **exactly two sites inside the function:
`0x2A0EA` and `0x2A16C`**, and nowhere else. Both are on hook-skipping paths. **The engaged path can
never write the sentinel**, so the test has no false positives.

**What the sentinel does — it is ALREADY a "first tick after a gap" guard, for the D term.**
Decompiled (lines 1053 and 1076 of 1309) and confirmed in assembly at `0x29E5E`–`0x29E7E`:

```c
bVar4     = 0x177000 < *(int *)(gp - 0x6cf8) + 0xbb800U;  // prev outside [-768000, +768000]
prev_used = bVar4 ? current : prev;                        // 0x29E7E  cmovnc r16, r8, r27
dE        = current - prev_used;                           // 0x29EE2  sub r27,r8  =>  dE = 0
```

It is a **range test on ±768,000**, not an equality test on `0x7FFFFFFF`. Its effect on a sentinel tick
is `dE = 0` — the firmware's own way of saying *"there is no usable history this tick."*

⭐ **This is the strongest argument available for the proposed fix: the firmware ALREADY uses this exact
cell, read at this exact point in the tick, to suppress a stale-history term on the first tick after a
gap. Rev 2 extends the same signal to the one piece of history V288 added.** The two guards then fire on
the same tick and say the same thing.

**Cold boot.** I could not find a bss-zeroing routine and **do not assert one**; the RTOS table pair at
`0xBB900`/`0xBB904` (`0xFEDEC000`, `0xFEE00000`) looks like a RAM region descriptor spanning both cells,
but that is **BELIEF, not EVIDENCE**. **The fix does not need it.** Lateral engagement cannot be true on
the first tick after power-on (it needs the engage flags plus the 100-tick debounce), so **at least one
skip-path tick always runs before the first engaged tick, and that tick writes the sentinel.** Whatever
RAM held at boot is overwritten before the cave can ever act on it. Cold boot is covered by the same
mechanism, with no dependency on the C runtime.

## A3. The third skip, `0x29A70 → 0x2A0C6` — it DOES set the sentinel

**It is not a hold mode. It is a different OUTPUT mode with an identical state reset.**

```
0x2A0C6  mov 0x0,r24                     ; integrator register zeroed
0x2A0CE  mov 0x1,r12 ; cmovlt -0x1,...   ; r12 = a sign
0x2A0D0..0x2A138                         ; a DIFFERENT table walk + LERP (cals 0xC6710..0xC6730)
0x2A0E4  mov 0x0,r27 ; mov 0x0,r29 ; mov 0x0,r22
0x2A0EA  mov 0x7fffffff,r16              ; <<< THE SENTINEL IS SET HERE TOO
0x2A13A  mulh r10,r12 ; subr r0,r12      ; open-loop output from that other curve
0x2A13E..0x2A162                         ; clamp to +/-cal(0xC61BE)=15360
0x2A162  br 0x2A174                      ; ... into the SHARED epilogue
```

- **Does it skip `0x29D72`? YES** — `0x29A70` jumps clean past the whole map/PID block.
- **Does it set the sentinel? YES**, at `0x2A0EA`, and it zeroes `r24`/`r27`/`r29`/`r22` exactly as
  `0x2A164` does. It reaches the same stores at `0x2A174`+.
- **Does it preserve the integrator? NO** — `r24 = 0` reaches `st.w r24,-0x6dd0,gp`.

**So `y` going stale on this path is detected by the same test, and there is no "preserves state but
skips the hook" case to reason about.** On the first tick after this mode ends the raw path recomputes
`sp` from scratch with no history at all — which is precisely what `y := sp` reproduces.

## A4. THE DETECTOR IS COMPLETE — there is no fourth skip

**The function has exactly ONE `return`** (decompiled line 1305 of 1309; the single `dispose ..., lp` at
`0x2A30A`). **There is no early return anywhere in it.** Therefore every tick reaches the shared
epilogue, and the only three ways to bypass the hook are the three `jr`s at `0x29A5C`, `0x29A64` and
`0x29A70` — **all three of which write `0x7FFFFFFF` to `gp-0x6cf8` in the same tick.**

> **⇒ "sentinel present at the hook" ⟺ "the previous tick did not execute `0x29D72`" ⟺ "this is the
> first engaged tick after a gap." The equivalence is exact in both directions.**
> [EVIDENCE — decompile single-return + positive-controlled branch scan + positive-controlled imm32 scan.]

## A5. WHAT `y` SHOULD BE INITIALISED TO — **`y := sp`. I argue FOR, strongly.**

**For `y := sp`:**

1. **Tick 0 becomes byte-identical to V282.** `y = sp` ⇒ `E = 32·sp − fb` exactly as stock. The first
   engaged tick after every gap carries **zero** behavioural delta, so the engage transient that made
   rev 1 a FAIL disappears rather than being merely shrunk.
2. **It is the firmware's own idiom, on the same cell, in the same tick.** The D guard at `0x29E5E`
   handles missing history by substituting the *current* sample for the absent previous one
   (`prev_used = current` ⇒ `dE = 0`). `y := sp` is the exact analogue for the setpoint. Both guards
   then fire together and agree.
3. **It restores the property rev 1 broke** — that `sp[n]` carries no dependence across a gap — rather
   than patching its symptom.
4. The filter then only ever lags *changes*, which is the entire point of the lever.

**Against `y := 0`:**

1. It **creates a new deviation stock never had**: the setpoint would ramp 0 → sp over ~15 ms at *every*
   engage, so the first 15 ms of every engagement delivers **less** assist than V282, at exactly the
   moment openpilot expects the actuator to respond. That trades the transient being removed for a
   fresh, unmeasured one.
2. In the common case (engage with a non-zero command) it makes the engage transient **worse**, not
   better — rev 1 starts too high, `y := 0` starts too low, and only `y := sp` starts right.
3. It has no analogue in the firmware's reset idiom. The firmware zeroes **accumulators and error
   history**; it never zeroes a **reference**, because references are recomputed fresh every tick.

## A6. THE PROPOSED TEST — CONFIRMED CORRECT, with three build notes

`ld.w -0x6cf8[gp],r9 ; sar 0x1c,r9 ; cmp 0x7,r9 ; bne <filter>`

**Confirmed.** `sar 0x1c` yields 7 only for values in `[1879048192, 2147483647]`. The firmware's own
guard band for this cell is `[-768000, +768000]`, and the physical bound from the clamps is tighter
still: `|E| ≤ 32×1128 + cal(0xC62E6 = 46080) = 82,176`.

| value | `sar 0x1c` |
|---|---|
| `0x7FFFFFFF` sentinel | **7** |
| ±768,000 (firmware guard edge) | 0 / −1 |
| ±82,176 (max reachable by the clamps) | 0 / −1 |
| 0 (zeroed bss) | 0 |

**No legitimate value can reach 2²⁸ — margin 3,267× against the clamp bound, 350× against the
firmware's own guard band.** And a signed 32-bit load is what the cell holds: both live accesses are the
word form. ✓

**Build notes, each of which would otherwise have cost a rebuild:**

1. 🛑 **THE CAVE DOES NOT FIT. There are exactly 2 free bytes after it.** `FILT` occupies
   `0xC4BDC..0xC4BFD` (34 B); `0xC4BFE..0xC4BFF` are `FF FF`; `TELE` starts at `0xC4C00`. The
   4-instruction prologue is **10 bytes**. `FILT` or `TELE` must be relocated — `0xC4C20..0xC4FF0` is
   free, and moving `FILT` down to `FREE_LO = 0xC4BD8` buys only 4 of the 10.
2. 🛑 **`ld.w` needs `hw2` bit 0 SET.** Displacement `-0x6CF8` is even, so a halfword encoder emits
   `hw2 = 0x9308`; the word form is `0x9309` — which is exactly what `0x29E5E` and `0x2A18C` carry, and
   what the build script's existing `ld_h`/`st_h` helpers **assert must be clear**. A new `ld_w` encoder
   must set it, or the cave will silently read `gp-0x6cf8`'s neighbouring halfword. This is the skill's
   trap (b), and the existing helpers actively enforce the wrong polarity for this width.
3. **Put the test before the existing `ld.h → r9`**, or use `r6`. Both `r6` and `r9` are dead scratch at
   the hook (next access to each is a write: `mov r16,r6` at `0x29D7A`, `mov 0x0,r9` at `0x29D80`).

⭐ **`y := sp` costs no extra store.** `r16` already holds `sp` at cave entry, so the sentinel branch can
target the cave's **existing** `st.h r16,-0x6a32[gp]` at `0xC4BF2` — which stores `sp`, and the existing
`ld.h` / `jr` tail then reloads and returns it. The whole fix is the 4-instruction prologue plus one
branch, with no new store and no change to the filter arithmetic. A `be` to `0xC4BF2` is well inside
Bcond's ±256 range.

## A7. WHAT THIS ADDENDUM DOES NOT CHANGE

Every §1–§7 finding stands: `sp` range ±1032 live / ±1128 worst, structurally int16-safe because
`r8 = ±1`; zero readers of `gp-0x6a32`; the filter outside the feedback path; D on E with the `fb`
component of `dE` bit-identical to stock; the phase table; the unmeasured outer-loop phase margin; the
undecidable 20 Hz echo-path sign; the flat-Kp dependency; and the negative prediction for the three
strata that failed V287 rev 1. **A rev 2 carrying this init fixes the one FAIL and inherits every one of
those conditions unchanged — including that the outer-loop phase margin at 3.9 Hz is still 20.1° worse
and still unmeasured.**
