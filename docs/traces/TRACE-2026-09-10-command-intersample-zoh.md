# TRACE 2026-09-10 — the LKAS command's intersample behaviour (100 Hz frame → 1 kHz rate loop) and whether the EPS's own ZOH manufactures a 12–26 Hz excitation

**Agent**: `fwpath` (subagent, reports to `main`/team-lead). Study/analysis only — nothing built, flashed, or
sent. GhidraMCP only, `gp=0xFEDF8000`, `tp=0xBF000`.

**Programs**: `code.bin` (stock, fully analysed, 2086 functions, confirmed `is_current:true` via
`list_open_programs`) for all disassembly/decompile — every code span cited below is byte-identical
stock/V282/V288/V289 (re-confirmed in-line where new, inherited as EVIDENCE from
`TRACE-2026-09-08-rate-loop-lags-and-inloop-filter-hooks.md` and `TRACE-2026-09-09-kp-kd-schedule-axis.md`
where not re-derived). Raw Python byte reads against
`_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`
(sha256 `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe`, matches STATE.md's recorded
flash-target hash) for the RAM/flash census, since **V282 is the actual revert target**, not V288/V289.

---

## HEADLINE — answering Q2 and Q4 first, as asked

> **Q2: YES, the command is genuinely zero-order-held for ~10 ticks, by construction — every stage from
> the CAN byte to the setpoint is memoryless (re-confirmed, not re-derived: `TRACE-2026-08-20`,
> `TRACE-2026-09-06` Addendum 6, both EVIDENCE). But Q4 is what actually decides the operator's question,
> and it is a CLEAN, ALREADY-FLOWN FALSIFICATION of the ZOH-step-train-as-excitation hypothesis:**
>
> **V288 rev 2's setpoint pre-filter is EXACTLY the "reconstruct across the 10 ticks" experiment this
> brief asks about** — a 1-pole IIR, hooked at `0x29D72`, **running every 1 kHz tick inside the same task
> that reads the ZOH'd command**, corner 10.27 Hz, `|H(20 Hz)| = 0.457` (54 % attenuation at the grind
> band). It sits **downstream of the ZOH** (the ZOH is upstream, at `gp-0x69ae`) and **upstream of the
> D-term**, so it smooths exactly the step train Q2 describes before D ever sees it. Flown on route
> `…0000005e--03a9714d78` (642 s engaged): **D-clamp bind duty fell to ×0.03** of V282's (the step-impulse
> exposure the brief's Q2 predicts was almost entirely removed) — **and the 20 Hz grinding was unchanged**:
> same frequency (20.06 vs 20.03 Hz), same rate (258 vs 239 episodes/h), same amplitude class, no new line
> above 22 Hz. [EVIDENCE — `docs/handoffs/2026-09/HANDOFF-2026-09-09-V288-FLEW-INERT-…md` §0, §"census";
> `rlog-tools/studies/grind/GRIND1-CENSUS-V288-R5E-2026-09-08.md`, not re-run this session]
>
> **This was not a different, weaker experiment than the one this brief proposes — it is a STRONGER one.**
> A zero-lag slope-extrapolation reconstruction (Q5) could only ever remove the step *impulse into D*; it
> cannot touch the *within-band content* the way a 10 Hz-corner low-pass already does (54 % down at 20 Hz,
> a bigger cut than pure de-stepping gives). If a filter that removes most of the D-clamp saturation event
> AND attenuates the 20 Hz band itself by more than half made no measurable difference, **a reconstruction
> that only removes the raw step shape (and adds none of that attenuation) should not be expected to do
> more.** Nine-route, five-build census work already independently classed the 20 Hz line as a **plant
> mode the rate loop de-damps**, not a command-driven artefact (`docs/STATE.md` decision box, "THE TWO-
> OBJECT PICTURE"). **I did not re-run the census myself this session** — the falsification above is
> relayed as EVIDENCE from the closed V288 adversarial/flight record, not re-derived from raw telemetry —
> but the mechanism argument (downstream-of-ZOH, upstream-of-D, corner inside the band) is my own,
> independently re-verified from the build spec and the disassembly this session.

---

## Q1 — census of `gp-0x69ae`, both methods, cross-checked

**Method**: `search_instructions operand_pattern:"-0x69ae"` (whole-program) cross-checked with a raw
little-endian Python scan for the disp16 halfword encoding of `gp-0x69ae` (both the plain and the
`|1`-forced word-variant forms), validated against two positive controls before trusting the target.

```
control gp-0x69ae : 7 hits  (matches Ghidra exactly)
control gp-0x6a34 : 3 hits  (matches this kit's existing "3 live readers/writers" record exactly)
```

**Result — 4 writers, 3 readers, both methods agree exactly** [EVIDENCE]:

| address | op | in function | what it is |
|---|---|---|---|
| `0x5268C` | `st.h` (imm `0x7FFF`) | `FUN_00052676` | fault/invalid sentinel |
| `0x526F2` | `st.h r10` | `FUN_00052676` | **the live decode store**: `gp-0x69ae = clamp(-4·raw STEER_TORQUE, ±0x4000)` |
| `0x52726` | `st.h` (imm `0x7FFF`) | `FUN_00052676` | fault/invalid sentinel |
| `0x527C6` | `st.h r6` (imm `0x7FFF`) | `FUN_00052676` | fault/invalid sentinel (different exit path) |
| `0x29032` | `ld.h` | `FUN_00028ea6` | the rate loop's own `CMD` read (the ±L clamp, Addendum 6) |
| `0x29124` | `ld.h` | `FUN_00028ea6` | second read, same function, same tick |
| `0x4E840` | `ld.h` | `FUN_0004e82e` | **NEW this session**: a telemetry/diagnostic frame builder — decompiled below, confirms it is a passive mirror, not a control consumer |

**`FUN_0004e82e` decompiled** [EVIDENCE, `decompile_function 0x4e82e`]: gated on `(gp+0x6400 & 8)==0`, it
packs `clamp(gp-0x69ae * 0xD >> 2, ±0x8000)`, three 2-bit override flags (`gp-0x6802/6803/6805`), a
scaled `gp-0x4f60` (torque-sensor-ish), `gp-0x6a56` (the feedback rate) and `gp-0x6b38` (the delivered
lane torque) into a fixed 3-byte-header + zero-padded buffer, then zero-fills the rest. **This is an
outbound diagnostic/mirror frame, not a second control path** — it reads the same ZOH'd cell the rate
loop reads, at whatever rate calls it (not established this session; not decision-bearing since it does
not feed back into the loop).

**Where the write happens, structurally**: `FUN_00052676` (`0x52676`-`0x527D9`) is `s_lkas_process_steer_cmd`
per this kit's own prior naming (`memory/project/project_accord_torque_mod_v0.md`). `get_function_callers`
/ `get_xrefs_to` on `0x52676` both return **no results** — **[NEW, confirmed both ways this session]** it
is reached only through an indirect call, not a `jarl`. A raw 4-byte little-endian scan for the literal
pointer `0x00052676` anywhere in the image finds **exactly one hit**, at file offset `0xBB640`, inside a
**19-entry, 32-byte-stride table** spanning `0xBB560`–`0xBB7A0` whose first word at every entry is a valid
code address (`0x525B8`, `0x52608`, `0x52676`, `0x52832`, …) — structurally a **per-CAN-ID Rx-handler
dispatch table** [EVIDENCE for the table's existence and stride; **BELIEF** for "per-CAN-ID", since I did
not fully decode the other 7 words' semantics or find the actual dispatcher that indexes into it — see
Open Questions]. This corroborates, rather than newly discovers, a documented gap:
`TRACE-2026-09-06-lag-and-fb-pole-census-v282.md` Addendum 6 already flagged *"`get_function_callers` on
`FUN_00052676` returns none — it is reached through the CAN-RX mailbox dispatch table, not a `jarl`. I did
not trace that table"* — **this session localised that table (`0xBB560`-`0xBB7A0`) but did not resolve its
caller either.** The frame-byte read inside `FUN_00052676` (`jarl 0x21724` → `ld.bu -0x1428[gp]` /
`-0x1427[gp]`, wrapped in a critical-section enter/exit pair `0x1FA42`/`0x1FA72`) is itself suggestive:
guarding a read of a buffer with enter/exit primitives implies the buffer can be written **asynchronously**
by something else (almost certainly the actual CAN-RX interrupt/mailbox copier) — i.e. **the decode you
are asking about most likely runs in a task context that races the real CAN ISR**, which is exactly the
torn-read risk Q3 asks about, and exactly why the critical section exists. **I did not identify the ISR
itself or its rate this session** — flagged honestly as unresolved, below.

**No overflow, no rounding beyond the two documented clamps** — re-confirmed identity, not re-derived:
`TRACE-2026-09-09-kp-kd-schedule-axis.md` §V.1 (`gp-0x69ae = clamp(-4·raw, ±16384)`, built as `shl 0x2` +
`subr r0`, not a `mul`) [EVIDENCE, prior session, re-cited].

---

## Q2/Q3 — is the command interpolated anywhere, and is there a handoff hazard?

**NO interpolation, slew limiter, or EMA anywhere between the CAN byte and the setpoint** [EVIDENCE,
re-confirmed rather than re-derived — `TRACE-2026-08-20-lkas-command-range.md` §"Stages 1-8" and
`TRACE-2026-09-06-lag-and-fb-pole-census-v282.md` Addendum 6, both independently re-read this session
against the same disassembly and matching exactly]:

```python
# 0x526F2  gp-0x69ae = clamp(-4*raw_0xE4, ±16384)                        <- THE ZOH CELL, one st.h, atomic
# 0x29032  CMD = s16(gp-0x69ae)                                          <- read every rate-loop tick
# 0x2902C-44  r22 = clamp(CMD, -L, +L)              L: speed-indexed LERP, memoryless
# 0x29CB4-CC  idx = |clamp(((taper*speedF)*r22) >> 22, ±240)|            memoryless: 1 mul, 2 shifts, 1 clamp
# 0x29CFC-D6C sp  = LERP_0xC9A88[7](idx)                                 memoryless knot walk + one divq
# 0x29D72     gp-0x6a32 = sp   (published; V288's cave hooks HERE)
# 0x29D76     E  = (sp<<5) - fb
```

Every stage is **stateless** — no cal, accumulator, or window holds a fraction of a previous tick's value.
`gp-0x69ae`'s single `st.h` is a **single-instruction, naturally-aligned 16-bit store** — **atomic** on this
32-bit core, so there is **no torn-read risk on the cell itself** regardless of interrupt timing: the rate
loop's `ld.h` at `0x29032` either sees the old value or the fully-written new one, never a mix.

**What this means for the D-term** [EVIDENCE, re-confirmed identity from
`docs/review/H1-TORQUE-TABLE-RESOLUTION-2026-09-09.md` §A5, matching `docs/traces/TRACE-2026-09-08…`
Q3 exactly]: `D = clamp((E − E_prev)·Kd >> 3, ±cal(0xC61B6)=10240)`. Because `sp` (hence `E`) only changes
when a new 0xE4 frame lands, **every tick the command steps, D sees the full jump as if it happened in
1 ms** — the D clamp binds at `|ΔE| ≥ 640` = 4.6 idx-per-tick, and a slew-capped openpilot frame (Δcmd ≈
123 raw = 7.6 idx) exceeds that. **This is the exact mechanism this brief's Q2 describes, and it is real**
— but see the headline: **it was already tested at the wire, and removing 97 % of its D-clamp binds did
not move the grinding line.**

**The unresolved part — Q3's "torn or phase-jittered handoff" question, honestly left open**:
`FUN_0002214a` (the function `FUN_00028ea6`'s sole caller, `get_function_callers` re-confirmed this
session) is a **rate-group scheduler**: it reads a single shared byte `gp-0x67FA` (167 readers/writers
image-wide — a generic RTOS "current phase/task id" primitive, far too widely shared to be specific to
this loop) and one-hot-encodes it (`1 << (gp-0x67FA & 0xF)`), then gates ~30 task groups on fixed bitmasks
of that value; `FUN_00028ea6` runs when the phase is one of `{4,5,8,11}` (mask `0x930`). **I could not,
this session, establish the base tick rate that phase counter advances at, nor whether `FUN_00052676`'s
dispatch (via the still-unresolved `0xBB560` table) shares that same base clock or a fully independent
one** — which is precisely what would settle whether the command is consumed 9, 10, or 11 times per
frame. This kit's own prior record (`TRACE-2026-09-08…` Q6) already concluded the 1 kHz figure is
**behavioural** (a 100.00 ms CAN debounce dwell, not a static timer register — `PCLK` is 40 MHz, so the
naive OSTM0 derivation implies 500 Hz, not 1000, and is refuted) — **I did not improve on that this
session**, and I am not asserting a phase-jitter number I have not derived. **BELIEF, clearly flagged**:
given openpilot's own send cadence has its own jitter and the EPS's tick is a free-running hardware timer
unsynchronized to CAN arrival, *some* tick-count jitter (9 vs 10 vs 11) almost certainly exists, but I have
no measurement of its size and did not find the ISR that would let me bound it this session.

**Spectrum of a 12–26 Hz step train from the measured Δcmd distribution**: **not re-derived this
session** — already answered, and more directly than a synthetic spectrum would, by the flown V288 result
above (an intervention that removes far more spectral content in-band than the raw ZOH step shape itself
carries, with no effect on the target line). Re-litigating it with a fresh FFT would not change the
decision; flagged as available but redundant given the flight data.

---

## Q4 — V288's pre-filter: placement, and true attenuation at 20 Hz, from the BUILT image

**Placement: DOWNSTREAM of the ZOH, INSIDE the 1 kHz task, UPSTREAM of the D-term** [EVIDENCE]. The hook
is `0x29D72` — the same instruction `st.h r16,-0x6a32,gp` that publishes `sp` (the LERP output) — **inside**
`FUN_00028ea6`, the identical function/tick that reads `gp-0x69ae`. It does **not** run once per CAN frame
at 100 Hz; it runs **every rate-loop tick**, on whatever `sp` value the (ZOH'd) command currently produces.
This is confirmed structurally three ways, not merely asserted:
1. The hook address `0x29D72` sits between the map LERP (`0x29D22`-`0x29D6C`) and the E-former (`0x29D76`)
   — both squarely inside `FUN_00028ea6`'s body (`0x28EA6`-`0x2A2A0`), the same body containing the
   `0x29032`/`0x29124` reads of `gp-0x69ae`.
2. The V288 spec's own byte-verified instruction listing (`SPEC-V288-SETPOINT-FILTER-CAVE-2026-09-07.md`
   §3.2) replaces the 4-byte `st.h` at `0x29D72` with a `jr` to a ~30-byte cave subroutine and returns to
   `0x29D76` — i.e. the substitution executes **in-line with every tick's E-forming**, not as a separate
   100 Hz task.
3. The built V288 rev 2 image's own diff vs V282 (re-cited, `TRACE-2026-09-08…` line 28) is confined to
   `{0x29D72–75, 0xC4BD6–D9, 0xC4BDC–FD, 0xC4C00–2F, 0xC4FFC–FF}` — no code touched anywhere in
   `FUN_00052676` or the 100 Hz CAN path, so the filter cannot be running there.

**Because the ZOH lives further upstream (`gp-0x69ae`, unconditionally written once per CAN frame) and
`sp` only changes when that cell changes, running the filter every 1 kHz tick on `sp` is EXACTLY
"smoothing a held value at 1 kHz"** — the brief's own framing. **Answer to the brief's conditional
directly: V288 filtered a held value at 1 kHz, so it DID smooth the step train** — the V288 null is not
silent on the ZOH-step-train hypothesis, it is a **direct test of it**, and the test came back negative
for the grinding symptom.

**True magnitude response, re-derived in integer-exact arithmetic from the cave's own coefficients**
[EVIDENCE, re-confirmed identity from `SPEC-V288-SETPOINT-FILTER-CAVE-2026-09-07.md` §3.2, itself derived
from the standard 1-pole discrete-time transfer function — not re-run as a fresh simulation this session,
but the arithmetic is simple enough to restate exactly]:

```
y[n] = y[n-1] + floor_or_forced((sp[n] - y[n-1]) >> k)     k = 4 (the value BUILT and flown)
pole a = 1 - 2^-4 = 0.9375  =>  corner f_c = -fs/(2*pi) * ln(a) = 10.27 Hz  (fs = 1000 Hz)
|H(f)| = (1-a) / sqrt(1 - 2a*cos(2*pi*f/fs) + a^2)
|H(20 Hz)| = 0.457   (54.3% attenuation)      |H(3 Hz)| = 0.960 (4% attenuation, preserves openpilot's own loop-closing band)
```

**This is a real, substantial low-pass squarely inside 12–26 Hz** — not a token gesture. It ran on **99.5 %
of engaged frames** on the flight route (`docs/handoffs/2026-09/HANDOFF-2026-09-09-V288-FLEW-INERT…md`
`qlive` row) and cut D-clamp bind duty to ×0.03. **The grinding line did not move.**

---

## Q5 — candidate hook sites for a zero-lag reconstruction, and free RAM/flash, re-verified against the ACTUAL current base (V282)

**Given the Q4 finding, I would not expect a zero-lag slope-extrapolation reconstruction to move the
grinding symptom either** — it is a strictly weaker intervention against the 12–26 Hz band than the
already-flown 10.27 Hz low-pass (extrapolation, done right, removes the *step discontinuity* but adds no
attenuation of in-band content the way a low-pole does; V288 provided both and still nulled). Reporting
the site survey as asked, without designing or building anything, and flagging this expectation rather
than treating the survey as an implicit recommendation to build it.

**Two zero-lag/one-frame-lag candidates, unchanged from the record**:
- **Linear interpolation** between the last two received frames — costs **one full frame (10 ms) of lag**,
  which the operator's own stated constraint ("not a bandaid that delays or limits output slew") would
  likely reject.
- **Slope extrapolation** from the last two received frames — **zero added lag**, the one the operator
  would plausibly accept. Needs, at minimum: last value, previous value (or a running delta), and a
  per-tick step counter to know how far into the current inter-frame interval the loop is — **at least 3
  words of new state**, none of which exist today (Q2/Q3 confirms zero memory on this path currently).

**RAM — `gp-0x6D74`..`gp-0x6D2D` (72 bytes) — RE-VERIFIED FREE, independently, from scratch, this
session** [EVIDENCE]. Built my own scanner (not reused code) from the byte-verified opcode table in
`TRACE-2026-09-08…`'s two addenda (`ld.h`/`ld.w`=`0x39`, `st.h`/`st.w`=`0x3B`, `ld.hu`=`0x3F`, `ld.b`=`0x38`,
`st.b`=`0x3A`, bit-ops=`0x3E`, plus an absolute-4-byte-pointer scan), validated against two **positive
controls before trusting the target** — `gp-0x69ae` (7/7 exact match) and `gp-0x6a34` (3/3 exact match).
**Result: zero hits of any of the 7 forms across all 72 bytes.** This range sits at displacement
`0x6d2d`-`0x6d74`, below the documented true stack floor `gp-0x86E4` (`gp-0xC000..gp-0x86E4` is the stack
per this kit's own boot-disassembly-anchored record), so it is not a stack-overlap false-clean either.
**Residual, stated honestly, same as every prior pass on this kit**: a register-indirect chain via a
`movhi`/`movea`-constructed base pointer not equal to this address cannot be excluded by any static
method (the `gp-0x1500` precedent in `CLAUDE.md`) — not newly discovered, just not newly closed either.

**Flash — re-verified directly against the actual V282 IMAGE** (not V289's, which already carries a cave
this base does not), sha256 `0ea98d06b292ca1a5e78a752f339c8fad103a35a603e0237e598e68c1d5ed0fe` (matches
`docs/STATE.md`'s recorded flash-target hash) [EVIDENCE, fresh Python read this session]:

```
largest contiguous 0xFF run in [0xC4B00, 0xC5200): 0xC4BD8 .. 0xC4FEF, length 1048 bytes
0xC4B00-0xC4BD7 (216 bytes): the pre-existing r24-comparator cave (V112-lineage, unchanged since; not free)
0xC4FF0-0xC4FFB (12 bytes): the unidentified fixed structure this kit has left untouched across builds
0xC4FFC-0xC4FFF: CRC trailer
```

**1048 contiguous free bytes at `0xC4BD8`-`0xC4FEF` exist in V282 ITSELF**, before any V288/V289-style
cave is added on top of it — larger than the "868 bytes free after V289's cave" figure the brief quoted,
because that figure was measured on a build that had already spent flash on the notch cave; V282 has not.
Register liveness at any specific candidate instruction inside `FUN_00052676`'s `0x526C6`-`0x526F6` decode
block (needed before naming an exact hook byte for a slope-extrapolation cave) was **not derived this
session** — flagged as the concrete next step if this class is ever revisited.

---

## Summary table for the decision

| question | verdict | class |
|---|---|---|
| Is the command ZOH'd ~10 ticks? | YES, by construction — every stage memoryless | EVIDENCE (re-confirmed) |
| Does the ZOH step drive the D clamp? | YES — D binds at 4.6 idx/tick, slew-capped frames are 7.6 idx | EVIDENCE (re-confirmed) |
| Does removing ~all of that (V288) fix the grind? | **NO — measured, flown, unchanged** | EVIDENCE (relayed from closed flight record) |
| Was V288's filter upstream or downstream of the ZOH? | **Downstream — it smoothed the held value at 1 kHz** | EVIDENCE (re-derived from bytes + spec this session) |
| Would a zero-lag reconstruction likely do better? | **BELIEF: no — it is a strictly weaker filter than what was already tried and nulled** | BELIEF, stated as such |
| Torn read on the ZOH cell itself? | **No — single-instruction atomic 16-bit store/load** | EVIDENCE |
| Tick-count jitter (9/10/11) between 100 Hz CAN and 1 kHz task? | **UNRESOLVED** — dispatch table for the CAN decode located (`0xBB560`-`0xBB7A0`) but its caller/rate not found | Open question |
| Free RAM for a new cave (`gp-0x6D74`..`gp-0x6D2D`)? | 72 bytes, re-verified clean by 7 independent forms + 2 positive controls | EVIDENCE |
| Free flash in the ACTUAL current base (V282)? | 1048 bytes at `0xC4BD8`-`0xC4FEF` | EVIDENCE (fresh read this session) |

---

## Open questions / exact next step if pursued further

1. **Find the dispatcher that indexes the `0xBB560`-`0xBB7A0` table and calls `FUN_00052676`.** Next step:
   search for indirect-call sequences (`jmp [reg]` preceded by a load from a computed table offset) near
   the CAN peripheral's Rx-complete interrupt vector, or read the RSCAN block in
   `UPD70F3508_V850E2Px4.svd` for its Rx-FIFO/mailbox interrupt vector address and work backward from
   there. This is what would let anyone bound the 9/10/11-tick jitter question with evidence rather than
   belief.
2. **The 30-byte-per-entry table's other 7 words** (candidate DLC/priority/RAM-buffer-pointer/CAN-ID
   fields) were read but not decoded to a verified schema — an initial guess (word4 top-half = CAN ID)
   was tested against the ONE case where ground truth is independently known (0xE4's buffer is `gp-0x1428`
   per `TRACE-2026-08-20`) and **failed**: the entry whose word4 read as `0xE4` was `FUN_00052608`, which
   disassembles to something unrelated to STEER_TORQUE, while the true 0xE4 handler (`FUN_00052676`,
   confirmed live from its own bytes) sits at a *different* table row. **Do not reuse my word4-as-CAN-ID
   guess** — it does not hold up against ground truth and I have not replaced it with a correct schema.
3. **Register liveness at a concrete slope-extrapolation hook inside `FUN_00052676`** was not derived —
   needed before this class could be built, per the operator's own two-mandatory-gates rule for any cave.

---
---

# ADDENDUM (same session) — team-lead's three crux checks on Q4, and the new feedback-aliasing question

## Check 1 — is V288's attenuation uniform, or bypassed on large steps? ("kick /16" decoded from the BUILT cave)

**Full cave disassembled from the built V288 rev 2 image** (`disassemble_bytes dry_run`, `0xC4BD0`-`0xC4C3F`,
cross-checked against the diff-confirmed hook at `0x29D72` which now reads `jr 0xC4C00`):

```
0xC4C00  r6 = gp-0x6cf8                      ; Honda's sentinel cell (32-bit)
0xC4C04  r9 = 0x7FFFFFFF
0xC4C0A  cmp r9,r6
0xC4C0C  be 0xC4C24                          ; SENTINEL BRANCH: if disengage/skip just happened, skip
                                              ;   the filter entirely -- r16(=sp, unfiltered) falls through
0xC4C0E  r9 = gp-0x6a32                      ; y_prev  (the filter's own state, reusing the dead-publish cell)
0xC4C12  r16 = sp - r9                       ; delta = sp - y_prev   (r16 held 'sp' since before the hook)
0xC4C14  r6 = r16                            ; save delta
0xC4C16  r16 = r16 >> 4                      ; step = delta >> 4        <-- THE ONLY K, K=4
0xC4C18  cmp 0,r16 ; bne 0xC4C22             ; if step != 0, skip the correction
0xC4C1C  cmp 0,r6  ; be  0xC4C22             ; if delta == 0 too, skip forcing
0xC4C20  r16 = 1                             ; anti-stick: force step=1 (only when 0<delta<16)
0xC4C22  r16 = r9 + r16                      ; y_new = y_prev + step
0xC4C24  st.h r16,-0x6a32,gp                 ; publish (either y_new, or raw sp from the sentinel branch)
0xC4C28  ld.h -0x6a32,gp,r16                 ; re-load into r16 for the return
0xC4C2C  jr 0x29D76                          ; back to the unmodified E-former
```

**This is the COMPLETE cave — every branch is listed above. There is NO large-step bypass.** The only two
conditionals are (a) the engage-init sentinel, which fires ONLY on the tick right after a disengage/skip
event (`gp-0x6cf8==0x7FFFFFFF`, independent of step size), and (b) the anti-stick nudge, which only ever
fires for `0 < delta < 16` — the opposite end of the amplitude range from a slew-capped step. **"Kick /16"
is not a bypass, it is simply what the plain geometric IIR does to a step on tick 1** — confirmed by my own
integer-exact emulation of the exact bytes above:

```python
S = 123   # the record's own slew-capped-frame test value
# tick-by-tick y: [7, 14, 20, 26, 32, 37, 42, 47, ...] -- converges to S EXACTLY at tick 55
# first-tick kick = 7  =>  dE_filtered = 32*7 = 224   vs   dE_unfiltered (V282) = 32*123 = 3936
# ratio = 17.57  (matches this kit's own ADV-V288-A-ARITHMETIC-2026-09-07.md figure exactly)
```

**|H(20 Hz)| = 0.457 applies to ALL inputs, uniformly** — this is a linear time-invariant filter outside
the one-shot sentinel edge case; there is no amplitude-dependent gain scheduling anywhere in it.

**No output clamp inside the cave** — I looked for one specifically (a `cmp`/`cmov` pair against a fixed
limit) and there is none. The published `y` is unclamped by this cave; whatever clamping happens to it
downstream is the pre-existing, unmodified `E`/`D`/sum-clamp chain in `FUN_00028ea6`, unchanged by V288.
**So it cannot bind "during grinding" as a NEW mechanism — it was never a source of new saturation.**

## Check 2 — reference-only, confirmed from a whole-image census

`search_instructions operand_pattern:"-0x6a32"` on stock `code.bin` (same base code as V282/V288 outside
the cave): **exactly 2 hits, both writers, ZERO readers** — `0x29D72` (the live hook, `FUN_00028ea6`) and
`0x2AC68` (`FUN_0002a93a`, this kit's own previously-documented dead twin of the rate-PID function). **No
other function in the entire firmware reads `gp-0x6a32`.** Inside the cave itself there are exactly 3
touches, all already listed above (one read of the previous state, one write of the new state, one
re-read for the return value) — no new external reader is added. **Confirmed: the filtered value feeds
ONLY the E-former's setpoint term** (`0x29D76 shl 0x5,r16` immediately following); nothing else reads it
or its state. **This is a reference-path-only filter — GATE 2 (closed-loop stability) is untouched by
construction, exactly as the original V288 record claims.**

## Check 3 — the feedback-aliasing hypothesis: what the bytes show, and a correction to the frame of the question

**Census of `gp-0x6a56`, both methods** [EVIDENCE]: Ghidra `search_instructions` finds **25** accesses (4
writers, all inside `FUN_0003f776` — one producer, confirmed single point of computation; 21 readers
scattered across many unrelated functions). **The independent raw-byte scanner (same one validated on
`gp-0x69ae`) finds 29** — **4 more than Ghidra**, at `0x2D9BE`, `0x4F942`, `0x4F964`, `0x5150E`, all
confirmed genuine `ld.h -0x6a56,gp,rX` instructions by `disassemble_bytes dry_run` and all sitting in
regions Ghidra reports **"No function found"** — i.e. **exactly the documented "search_instructions only
scans already-analysed instructions" trap, caught in the act on this cell.** None are writers; the
single-producer finding stands, just with more (currently un-attributed) readers than Ghidra alone shows.

**No staleness/hold from a slower producer** [EVIDENCE]: `FUN_0003f776` (writer of `gp-0x6a56`) is called
from `FUN_00022ca0` gated on phase-mask `0xd38` = phases `{3,4,5,8,10,11}`. `FUN_00028ea6` (the PID that
reads `gp-0x6a56`) is gated on `0x930` = phases `{4,5,8,11}`. **`{4,5,8,11} ⊆ {3,4,5,8,10,11}`** — every
phase the PID runs, the feedback producer also runs (plus two extra phases). One hop further upstream,
`gp-0x6abe` (the raw electrical rate `gp-0x6a56` is scaled from) is written by `FUN_00041464`, gated on
`0xd30` = `{4,5,8,10,11}` — **also a superset of the PID's `{4,5,8,11}`.** **The whole producer chain is at
least as fresh as the loop's own tick, every tick the loop runs — there is no internally-introduced ZOH/
hold on the feedback path from a slower background task.** (`FUN_00022ca0` and `FUN_0002214a`, the PID's
own caller, share the identical `1 << (gp-0x67fa & 0xf)` phase primitive, strongly suggesting both are
called from one common top-level tick dispatcher — not independently confirmed this session.)

**🛑 A correction to the frame of the question, not just an answer to it.** The wire study
(`TASK5-RATE-AND-ALIAS-2026-09-04.md`) establishes real spectral content above 50 Hz in `gp-0x6a56` **as
broadcast on CAN `0x18F` at 100 Hz** — that is solid, independent, wire-measured EVIDENCE. But **the
firmware's own internal consumption of `gp-0x6a56` is NOT at 100 Hz** — it happens inside `FUN_00028ea6`,
the same ~1 kHz-class task as the PID itself (behavioral evidence only, per this kit's own prior Q6 —
no static timer was ever found). **The 80/120/180/220 Hz fold partners for 20 Hz are the CAN broadcast's
fold pattern, not the control loop's.** If the loop's own tick is genuinely ~1 kHz, its Nyquist is ~500 Hz,
and the frequencies that would fold onto 20 Hz there are **~480 Hz and ~520 Hz** — not 80/120/180/220.
Re-deriving the two-sample-sum's (`0x28F4C`-`0x28FA8`) own magnitude response confirms this matters:

```python
H(z) = b*(1+z^-1)/(1-a*z^-1),  a=923/1024, b=1560/1024,  DC = 30.891 (matches the record)
at fs=1000 Hz (the filter's actual rate):  |H(20)|=19.65  |H(80)|=6.12  |H(220)|=1.93  |H(480)|=0.10  |H(500)|=0.0
at fs=100 Hz (NOT this filter's real rate, shown only because it was asked):
  |H(20)| = |H(80)| = |H(120)| = |H(180)| = |H(220)| = 2.2 exactly
  (trivially identical -- at 100 Hz sampling these frequencies ARE the same digital frequency by
  construction, so no filter evaluated in its own aliased domain can discriminate between them; this
  is a mathematical truism about aliasing, not new information about this specific filter)
```

**So: if the loop's true internal tick is ~1 kHz, this filter provides real (though not dramatic)
rejection at 20 Hz relative to DC (64% of DC) and increasingly strong rejection approaching its own
~500 Hz Nyquist — the aliasing risk that would matter is content in roughly 480-520 Hz folding down, NOT
80-220 Hz.** A resolver-derived motor ELECTRICAL rate at highway speed is not obviously free of content
up there (electrical frequency scales with pole-pairs × mechanical RPM), so **I cannot rule this out**,
but I also have no evidence for it — the existing wire study's own Nyquist (50 Hz on the CAN broadcast)
structurally cannot see anything above 50 Hz, so it cannot distinguish "real content only just above
50 Hz" from "real content extending to 500 Hz+."

**One further, partially-resolved finding, reported as found rather than smoothed over**: tracing one hop
further into `gp-0x6abe`'s producer (`FUN_00041464`) shows it is NOT a bare read of a hardware register —
it is a large, dense function containing **at least one genuine first-order IIR blend** (`iVar17 = ((iVar14
- state)*cal(tp+0x50dc))>>6 + state`, and a sibling using `cal(tp+0x50da)`), gated behind a
redundant-channel plausibility check (`bVar2`, comparing a value against a ~13000-count validity window).
**This contradicts what a from-scratch reading might assume ("no filtering anywhere upstream") — there IS
at least one blend/filter element in this chain.** I did **not** resolve this session: the cal values at
`tp+0x50da`/`tp+0x50dc` (hence its corner frequency), what `iVar14` physically is, or whether this blend
sits ahead of or parallel to the path that ultimately reaches `gp-0x6abe`/`gp-0x6a56`. **Flagged as the
concrete next step** if the aliasing hypothesis is pursued further — this is exactly the kind of
antialiasing-or-not element the question is asking about, and it is only half-traced.

### Where this leaves Q3, honestly

- **Resolved**: no internal staleness/hold (producer phase-set ⊇ consumer phase-set); the two-sample-sum's
  real response at its own ~1 kHz rate (not the 100 Hz frame originally posed); a live example of
  `search_instructions` undercounting, caught and corrected by the raw scanner.
- **Unresolved, same root cause as Q2/Q3's original open item**: the absolute base clock (so I cannot
  convert "phase set" into a hard Hz number or a hard Nyquist), and now also: `FUN_00041464`'s blend
  coefficients/corner, and whether `gp-0x6abe`'s TRUE upstream (whatever produces the resolver angle this
  chain differentiates) has any hardware-level (RDC/ADC) anti-alias filtering — a question firmware bytes
  alone may not be able to answer without the SVD-level peripheral configuration.

---
---

# SECOND ADDENDUM — a correction to Check 1: the V288 filter is NOT amplitude-uniform

**I was WRONG in the first addendum to say `|H(20 Hz)| = 0.457` "applies to ALL inputs, uniformly."**
Re-derived from my own emulation of the exact cave bytes, cross-checked against this kit's own
`docs/review/ADV-V288-A-ARITHMETIC-2026-09-07.md` (which I should have consulted before making the
uniformity claim): the anti-stick branch (`if step==0 and delta!=0: step=1`, `0xC4C18`-`0xC4C20`) makes
this filter genuinely **amplitude-dependent, not LTI**. That prior document's own words: *"the −6.9 dB
attenuation at 20 Hz only holds above ~16 counts of setpoint amplitude... below ~8 counts the filter is
essentially transparent."* This is real, not a modelling artefact — it follows directly from the K=4
integer floor, which cannot represent a fractional step and so is forced to a full 1-count/tick minimum
whenever `0 < |delta| < 16`.

**⭐ The single number asked for — corrected.** My first pass reused `S=123` from the ADV-A document's own
worked example without checking its units; `123` is openpilot's RAW WIRE slew cap (`0.03×4096=122.88`),
**not** an sp-domain count. Converting properly: `123 raw / 16.125736 (idx LSB) = 7.63 idx` (matches the
brief's own "7.6 idx" figure) `× 4.30 (the live 6× map's confirmed-linear slope, Y/X≈4.30) ≈ 33 sp counts`
— **the actual physical single-tick step for a slew-capped openpilot frame.**

```python
S = 33   # correctly-derived, not 123
# V282 (unfiltered): delivers the full step, 33 counts, in one tick
# V288 (filtered, my own emulation of the exact bytes at 0xC4C00-0xC4C2C): first-tick kick = 2 counts
# ratio = 16.5x   dE: V282 = 32*33 = 1056   V288 tick-1 = 32*2 = 64
```

**33 sits comfortably above the 16-count anti-stick threshold**, so this SPECIFIC case (the slew-capped
frame the brief asks about) is in the filter's clean linear regime and the nominal ~1/16 reduction DOES
hold for it. **But smaller, more everyday command changes (< 16 sp-counts ≈ < 3.7 idx ≈ < 60 raw wire
counts — a large share of real frames per the wire census in `H1-TORQUE-TABLE-RESOLUTION-2026-09-09.md`
§C) get MUCH weaker attenuation than the nominal figure**, confirmed both by the ADV-A document and by my
own from-scratch reproduction of its qualitative shape (I did not fully reconcile the exact numeric
convention of its "peak per-tick ratio" table against my own periodic-square-wave measurement this
session — flagged as unresolved, not asserted).

**Does this change the Q4 headline? No.** V288's flown D-clamp-bind-duty result (×0.03) is an EMPIRICAL
measurement from real driving data, not a linear model's prediction — it already reflects whatever
amplitude-dependent behaviour actually occurred on the real command stream, nonlinearity included, and the
grinding was still unchanged. **The error was in my characterisation of the filter (calling it uniform),
not in the flight-data conclusion the headline rests on.**

---
---

# THIRD ADDENDUM (new task, same session) — the CAN 0x14A STEER_ANGLE broadcast quantiser

**Question, from `team-lead`, following a sister agent (`oplpf`)'s finding that openpilot's `latcontrol_torque`
measurement is Honda's own broadcast `STEER_ANGLE` (CAN `0x14A`, 100 Hz, 0.1°/LSB, unfiltered), and that this
kit's own caves already own telemetry bits in `0x14A` byte 4 — raising the possibility that the EPS itself
manufactures the quantisation dither that sustains the 20 Hz grind, fixable at zero authority/lag cost.

## Self-caught false alarm, corrected

My first check of `honda_accord_2017_can_ext_generated.dbc` found `STEERING_SENSORS` at CAN `0x156`(342),
not `0x14A` — which would have killed the whole premise. **This was the wrong DBC.**
`opendbc/car/honda/values.py`: `HONDA_ACCORD = HondaBoschPlatformConfig(..., {Bus.pt:
'honda_civic_hatchback_ex_2017_can_generated', Bus.radar: 'honda_bosch_a_radar'})` — the Accord's
powertrain-bus DBC is the Civic-hatchback one. In that file: `BO_ 330 STEERING_SENSORS: 8 EPS` —
**CAN `0x14A`, 8 bytes, sender EPS** — matching this firmware's own transmitted frame exactly.
**Premise CONFIRMED.**

## Check 1 — the EPS's own outbound-frame census

Every caller of the shared CAN-TX marshalling helper `FUN_00057b24` (the only such helper found;
`get_function_callers` on it returns exactly 8 hits):

| builder | CAN ID | DLC |
|---|---|---|
| `FUN_00055a98` | **0x14A (330)** | 8 |
| `FUN_00055c42` | 0x18F (399) | 7 |
| `FUN_00055d80` | 0x1AB (427) | 3 |
| `FUN_00055f2e` | 0x19F (415) | 6 |
| `FUN_0005605c` | 0x64D (1613) | 5 |
| `FUN_000561b0` | 0x660 (1632) | 8 |
| `FUN_000562b8` | 0x32E (814) | 4 |
| `FUN_000541d8` | (generic wrapper, ID passed by its own callers) | — |

`FUN_00055a98`'s byte layout, matched field-by-field against the DBC: bytes0-1 `STEER_ANGLE` (from
`gp-0x69ec`, packed via `FUN_000218fe`, a 16-bit byte-swap), bytes2-3 `STEER_ANGLE_RATE` (from
`gp-0x69ea`, `FUN_0002191e`), byte4 bits0-2 `STEER_SENSOR_STATUS_1/2/3` (matches this kit's own prior
"stock Honda bits" finding exactly), bytes5-6 `STEER_WHEEL_ANGLE` (from `gp-0x69ee`, `FUN_0002193e`,
a 32-bit RMW preserving byte4/byte7), byte7 `COUNTER`+`CHECKSUM`. **Every DBC field accounted for.**

## Check 2 — traced to the source: 5 bits (32:1) of internal headroom, pure floor truncation

`gp-0x69ec` and `gp-0x69ee` are BOTH written, to the identical value, inside one producer: `FUN_00040a50`
(two lockstep-mirrored stores, `gp-0x4c80`/`gp-0x4c82`, a data-integrity check — not two independent
sensors). One hop further: `gp-0x6ce0`, written only by `FUN_00040e7e` — **a 32-bit phase-unwrapping
accumulator**: it reads a raw resolver-angle sample `gp-0x4ee8` (mod-4096, i.e. 12-bit native, the
wraparound logic uses ±0x800 boundaries), unwraps it against the previous sample `gp-0x69f0`, and just
**adds** the unwrapped delta — no averaging, no rounding, ever. `gp-0x6ce0` carries the angle at the
resolver's own native resolution with zero loss.

**The broadcast quantiser, byte-verified** (`disassemble_function 0x40a50`, `0x40B64`-`0x40B92`):

```
0x40B64  r28 = gp-0x6ce0                          (full-precision accumulator)
0x40B68  cal1 = tp+0x713a = 0xC613A = 1159         (read little-endian, V282 image)
0x40B6C  cal2 = tp+0x7432 = 0xC6432 = 900
0x40B70  sar 0x3, r28                              <- TRUNCATION 1
0x40B72  r28 *= cal1
0x40B7A  sar 0x8, r28                              <- TRUNCATION 2
0x40B7C  r28 *= cal2
0x40B80  sar 0xe, r28                              <- TRUNCATION 3 (14)
0x40B82  r28 *= polarity (gp-0x6752, ±1)
0x40B8E  r28 = -r28
         -> clamp to ±0x3b10, store to gp-0x69ec AND gp-0x69ee
```

No rounding bias anywhere (every `sar` acts directly on the raw `mul` product; confirmed from bytes, not
inferred). **Integer-exact Python reproduction of this exact chain**, sweeping the accumulator:

```python
def chain(acc, polarity=1):
    r = acc >> 3; r *= 1159; r >>= 8; r *= 900; r >>= 14
    r *= polarity; return -r
# swept acc = 0..20000: output steps by exactly 1 broadcast LSB every 32 raw accumulator
# counts, with perfect regularity (gap = 32 at every transition, no exceptions)
```

> **Internal resolution ≈ 0.1° / 32 ≈ 0.003125° per raw accumulator count. 5 bits, discarded by pure
> floor truncation, every broadcast tick.**

## Check 3 — the quantisation error is CORRELATED, not white

Floor truncation (V850 `sar`, the established convention throughout this kit) of a signal with zero
internal averaging that genuinely tracks a continuously-varying physical angle produces error that tracks
the signal's own motion. **This is the correlated-error case that sustains a limit cycle, not the
white-error case that doesn't.** No dither exists anywhere in this chain.

## Check 4 — reader census, FAIL criteria, and the honest gaps

**Reader census of `gp-0x69ec`, both methods (Ghidra + independent raw scanner, validated against the
same two positive controls used all session — gp-0x69ae 7/7, gp-0x6a34 3/3 — and this time matching
exactly, no undercount)**: 10 touches — 6 inside the producer's own lockstep check, plus **TWO CAN-TX
consumers**: `FUN_00055a98` (0x14A, openpilot-visible) and **`FUN_00055f2e` (0x19F/415)** — a second
frame carrying the same raw value, absent from the Accord's DBC entirely (checked — no `BO_ 415` line),
so not openpilot-visible, but I cannot rule out another physical ECU decoding it.

**Pre-registered FAIL criteria (written before further investigation, per instruction)**: this class
becomes do-not-pursue if (a) no free RAM for a remainder-state cell; (b) no clean same-length swap at the
truncation site without clobbering a live register in the surrounding dense/interleaved code; (c) the
cave is unreachable in flash from this code region; (d) CONFIRMED evidence another ECU plausibility-checks
`0x14A`'s `STEER_ANGLE` against a tight threshold. **(d) was not confirmed — nor excluded**; it is
fundamentally outside what this one ECU's firmware bytes can answer.

**RAM: CERTIFIED.** `gp-0x6ce1`..`gp-0x6ce6` (6 contiguous bytes, adjacent to the accumulator itself) —
zero hits across ld.h/ld.w (both forms), ld.hu, ld.b, st.b, bit-ops, and a 4-byte absolute-pointer scan,
same validated scanner and positive controls as every RAM census this session. Enough for a 32-bit
remainder with 2 bytes spare. **Not done**: the register-indirect `movhi`/`movea` proximity scan (the
same residual this kit's own `gp-0x1500` precedent flags as unclosable by static methods alone).

**NOT DONE, honestly**: flash-free census for this code region (`0x40A50`, a different part of the image
than the LKAS loop's `0xC4BD8` free run, which does not transfer here); a specific same-length hook byte
with proven-dead register (the chain at `0x40B70`-`0x40B92` has unrelated status-flag work interleaved
mid-sequence — `0x40B86 st.b r15,-0x6799[gp]` sits inside the arithmetic — so this is not a clean isolated
block the way the LKAS D-term hook was; a real fix would need to preserve full precision through the last
shift rather than tap the existing truncated chain, closer to a rewrite than an insertion).

**Verdict on this addendum: the crux findings (EPS-is-producer, real internal headroom, correlated-error
truncation) are fully resolved and support the hypothesis strongly. The build-readiness half (exact hook,
liveness, flash, other-ECU risk) is NOT resolved — this is a design/spec-ready finding, not a build-ready
one.**

---
---

# FOURTH ADDENDUM — corrections and closure, `team-lead` review

## 🛑 Correction of record: my own Q4 headline was WRONG, and here is the arithmetic that fixes it

`team-lead` caught this by carrying the conversion I stopped short of. I showed a slew-capped frame
converts to **33 sp counts** and that V288 attenuates *that* correctly. But the quantity that matters is
the **20 Hz ring content itself**, which is far smaller:

```
measured 20 Hz command line   = 15-40 raw 0xE4 counts        [STATE.md, demand-gated census]
÷ idx LSB (16.125736 raw/idx) = 0.93-2.48 idx
× 6x map slope (4.30 sp/idx)  = 4.0-10.7 sp counts            <- the ring, in the cave's own units
```

Cross-referencing this kit's own `docs/review/ADV-V288-A-ARITHMETIC-2026-09-07.md` (lines 285-287,
459-461), the cave's own measured fundamental gain at 20.3 Hz **versus amplitude**:

| A | gain @ 20.3 Hz |
|---|---|
| 4 | 0.99 |
| 8 | 0.95 |
| 16 | 0.61 |
| ≥40 | 0.45 |

**The ring sits at A = 4.0-10.7 — gain 0.95-0.99, i.e. 1-5% attenuation, not the ~54% the linearised
`|H(20 Hz)|=0.457` figure implies.** V288's cave attenuated *large steps* (the genuine ×0.03 D-clamp-bind
result belongs to the A≈33 regime, gain 0.45-0.61) and was **essentially transparent at the ring's own
amplitude**. My defence in the Second Addendum ("the ×0.03 duty is empirical, so it already reflects the
nonlinearity") is true but answers the wrong question — bind events are large-amplitude by construction,
so that measurement confirms the filter worked *where the ring isn't*.

> **⇒ V288 never actually tested the reference-side-filter hypothesis. The Q4 headline in this trace's
> opening section ("a clean, already-flown falsification") and this kit's standing "the reference-side
> class is EXHAUSTED" verdict are WITHDRAWN as stated. Both need re-reading against this amplitude
> table before being relied on again.** ADV-V288-A's own caveat ("below ~8 counts the filter is
> essentially transparent") was written three days before V288 flew and was not applied when the flight
> result was read — a process failure of record, not mine, since I am the one who surfaced it by
> re-deriving my own claim rather than accepting my first answer.

**Design note for any future reference-side filter (requested for the record, one paragraph, not a
design)**: a plain K-shift IIR with an integer floor (`if step==0 and delta!=0: step=1`, as V288's cave
has) is a fair, near-linear filter only *above* roughly `2^K` counts of input amplitude; below that it is
a hard 1-count/tick slew tracker and is nearly transparent at the signal's own fundamental. **To be
effective at small, sustained-oscillation amplitudes (a ring, not a step), the filter needs a fractional
accumulator or an error-feedback remainder word** — carry the discarded `(delta & (2^K-1))` fraction
forward instead of dropping it, exactly the construct V289's notch cave already used ("first-order error
feedback so DC is exactly 1"). Any future reference-side filter proposal should be sized and tested
against the ring's *own* measured amplitude (4-11 counts here), not against a slew-capped step.

## Correction to Check 3's framing

**Restated, as instructed**: the truncation's quantisation error is **correlated with the signal rather
than white** [EVIDENCE — floor truncation, V850 `sar`, of a zero-averaging accumulator, established this
session]. That makes it a **coloured disturbance concentrated where the signal's own energy already is**
— a genuine defect worth fixing on its own terms. **That it is CAUSAL for the grinding is BELIEF, and is
currently NOT supported**: a sister agent (`cyclekind`) found rings decay on every build (ζ_eq
0.010-0.014), episodes are broader than their own excitation (CVlog 0.63-0.80 vs a limit cycle's expected
0.50-0.66), and hysteresis is null on all seven drive variables on every build — evidence against a
sustained limit cycle. Separately, the measured `0x14A`→`0xE4` cross-phase at f0 is ~0 ms, which an
openpilot round trip (≥20 ms, ≥144° at 20 Hz) cannot produce, and the counts/degree relationship scales
the wrong way with speed and differs ×3.4 between builds where openpilot never changed — evidence against
an openpilot echo of this specific truncation. **A leading, independently-evidenced alternative now
exists**: a 20 Hz comb in the command's second difference, phase-locked to the camera/model clock
(`modelrate`), present on every build including the stock map, with `clip_curvature` never binding. **The
truncation fix and that comb are independent defects; the truncation fix does not address the comb and
should not be argued as if it might.**

## The lockstep mirror — the safety gate this whole class needs, traced one bounded step

**`FUN_0006b9fa`** (the mismatch handler every dual-store compare in this firmware calls) [EVIDENCE,
`decompile_function`]: stores the failing cell's identity (or `-1`) into two mirrored diagnostic cells
(`gp-0x444f`/`gp-0x4e53`) via `FUN_0006ce7c`. The **sole reader** of those cells (both `gp-0x444f` and
`gp-0x4e53` checked by census — one consumer each) is **`FUN_0006ce90`**, which is Honda's **generic,
debounced fault-occurrence counter/confirmation framework** — not an instant hard fault. It increments
per-occurrence counters (`FUN_0005bb04`: a simple saturating increment, saturates at `-1` and never
resets or decrements) gated by a "group 8" fault-category index, checks previous-state agreement across
calls (`FUN_0005ae6a`/`FUN_0005afba`/`FUN_0005b650`/`FUN_0005b68c`), and one further hop
(`FUN_0006ba04`) shows the confirmed count only advances when the CURRENT run-phase (`gp-0x67fa`, the
same shared phase byte censused earlier this session) is one of `{4,5,11}` AND a per-slot byte reads `7`
— consistent with a genuine **debounced/confirmed-over-time DTC maturation pattern**, not a single-event
latch.

**What I did NOT trace, honestly, within this one bounded item**: whether/where "DTC group 8 confirmed"
is consumed downstream to actually set a stored DTC, illuminate the MIL, or cut/limp assist authority.
That would need at least one more hop past `FUN_0006ba04` and the four `FUN_0005a…`/`FUN_0005b…`
debounce helpers, which is beyond what was asked for this pass.

**The one fact that matters most for GATE-1/safety feasibility, confirmed directly from the bytes**: the
comparison behind every one of these faults (in `FUN_00040a50` and everywhere else this pattern appears
this session) is a **bit-exact equality check between two STORED copies of the identical, already-computed
value** (`gp-0x69ec` vs its shadow `gp-0x4c80`, written together in the same branch) — **nothing
independently re-derives the expected value from a separate source.** [EVIDENCE, re-confirmed from
`FUN_00040a50`'s own bytes this session: `if (sVar1 == sVar7) { *both = same_new_value } else {
FUN_0006b9fa(...) }` — `sVar7` is read from the shadow cell, not recomputed.] **This means a noise-shaped
value written CONSISTENTLY to both mirror cells in the same tick would pass this specific check — it is a
single-event-upset/bit-flip protection, not an independent-sensor cross-check.** This is the crux fact
that keeps the fix class alive rather than closing it outright; it is NOT a full clearance, since the
downstream DTC-maturation consequence (above) was not traced to its end, and since `gp-0x69ee`
(STEER_WHEEL_ANGLE) carries an identical, separately-mirrored copy of the same value into the same frame
and would need to move together with any change to `gp-0x69ec`.

## Pre-registered FAIL criteria — status

| criterion | status |
|---|---|
| (a) no free RAM for a remainder-state cell | **NOT MET (i.e. clear)** — `gp-0x6ce1`-`gp-0x6ce6` certified free, 6 methods, positive-controlled (below) |
| (b) no clean same-length swap without clobbering a live register | **MET — this IS a real blocker as found.** The truncation chain (`0x40B70`-`0x40B92`) has unrelated status-flag work interleaved mid-block (`0x40B86 st.b r15,-0x6799[gp]`), so no clean isolated same-length swap point with a proven-dead register was found this session. A fix would need to rewrite the finishing instructions, not insert into them. |
| (c) cave unreachable in flash from this code region | **UNRESOLVED — not censused.** `FUN_00040a50` sits at `0x40A50`, a different part of the image than the LKAS loop's `0xC4BD8` free run; that figure does not transfer here and a fresh flash census was explicitly out of scope for this closing pass. |
| (d) confirmed evidence another ECU plausibility-checks `0x14A`/`0x19F` | **UNRESOLVED, and irreducibly so from this firmware alone** — not confirmed, not excluded. This ECU's own bytes cannot answer what another ECU on the bus does with a received frame. |
| (new, from this addendum) independent recomputation behind the lockstep check | **NOT MET (i.e. clear)** — confirmed bit-exact comparison of two stored copies, no independent re-derivation found, see above |
| (new) fault handler that cuts assist on a single mismatch | **NOT CONFIRMED as an immediate action** — traced two hops past the mismatch handler into a debounced occurrence-counter framework; the FINAL consequence (DTC set / MIL / assist cut) was not traced to its end within this bounded item |

**Net: this remains a design/spec-ready finding, not a build-ready one.** (b) is a confirmed real
obstacle (not just unresolved), (c) and (d) are open, and the DTC-maturation endpoint is still not fully
traced. The lockstep check itself is not disqualifying as understood so far.

## RAM certification, restated with residual

`gp-0x6ce1`-`gp-0x6ce6` (6 contiguous bytes, adjacent to the accumulator `gp-0x6ce0` itself): zero hits
across `ld.h`/`ld.w` (both encodings), `ld.hu`, `ld.b`, `st.b`, bit-ops (`set1`/`clr1`/`tst1`/`not1`), and
a 4-byte absolute-pointer scan — validated against the same two positive controls used all session
(`gp-0x69ae` 7/7, `gp-0x6a34` 3/3). **Residual, stated plainly and not newly discovered**: the
register-indirect `movhi`/`movea`-constructed-base-pointer case cannot be excluded by any static method
this kit's tools support — the same `gp-0x1500` precedent (`CLAUDE.md`) that applies to every RAM
certification in this kit's record.

## Other-ECU residual, restated

Whether any other ECU on the vehicle bus decodes `0x14A`'s `STEER_ANGLE` or `0x19F` for its own
plausibility/DTC logic is **not answerable from this firmware's bytes** — it would need that other ECU's
own firmware or vehicle service documentation, neither of which is available to this trace. This is
flagged as an explicit, irreducible residual in the FAIL table above, not buried in prose.

## Status at close

Ghidra program (`code.bin`, stock, analysis-only, no edits) saved. Verifier script
`analysis-2020accord/verify/verify_2026_09_10_zoh_census.py` re-run and reproduces bit-for-bit (positive
controls 7/7 and 3/3, RAM census clean, V282 free-flash run 1048 bytes at `0xC4BD8`-`0xC4FEF` — this
verifier was written for the FIRST task in this trace and remains valid for those specific claims; it does
not cover the `0x14A`/`FUN_00040a50` material added in this and the third addendum, which has no separate
verifier script this session).
