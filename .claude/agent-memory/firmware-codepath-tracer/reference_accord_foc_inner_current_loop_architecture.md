---
name: reference_accord_foc_inner_current_loop_architecture
description: FOC/PWM inner-loop architecture on the A160 (39990-TVA-A160) V850E2Px4 — ISR call chain, TSG20 PWM timer register map (SVD-confirmed), loop-rate evidence, and the negative result that the merged torque command gp-0x6b98 is NOT read by the FOC math core. Load before any inner-current-loop / PI-gain / PWM-carrier investigation.
metadata:
  type: reference
---

# FOC inner current-loop architecture (2026-07-22 session)

Investigated as part of testing the hypothesis that the 10-25 Hz base-assist vibration originates
in the inner FOC current-control loop (not the outer assist lanes). Full session covered ~65
GhidraMCP calls on `code.bin` (stock). Load-bearing facts below; open items at the end.

## ISR call chain (EVIDENCE — decompiled + disassembled)

`FUN_0006404c` = the ADC-complete ISR (per operator brief, EIIC 0x600 — this specific vector
assignment was NOT re-derived this session, carried as given). Decompiled body:
- Clears/configures two peripheral regs (`_DAT_ffffc9c8=0x400`, `_DAT_ffffcc08=0`).
- Gated on a flag byte `gp-0x4e6e`: if 0, runs the main chain; else calls `FUN_00069cfc` (not
  traced this session — believed to be an ADC-offset-calibration/startup branch, unconfirmed).
- Main chain: extracts 4 raw 12-bit-ish ADC fields into `gp-0x4f2a/-0x4f28/-0x4f26/-0x4f2c` (these
  are **RESOLVER SIN/COS ADC channels, NOT phase currents** — confirmed by tracing into
  `FUN_00065afe`, which consumes exactly this quartet as two redundant sin/cos pairs feeding an
  atan2-style helper `FUN_0006adfe`), then calls in order:
  `FUN_0006428e` (extracts 2 more ADC halfwords into `gp-0x4f14/-0x4f12`, unscaled) →
  `FUN_00065afe` (angle-tracking/observer; NOT a bare "sin/cos+atan2" as previously assumed — see
  below) → `FUN_000711f8` (pre-check: sums a 24-byte RAM block at **`gp+0x378..0x38c`** — a
  POSITIVE gp offset, i.e. its own small scratch region above gp — and shadow-compares against
  `gp-0x4f98`, calling `FUN_0006b9ee` on mismatch — the same shadow-mismatch fault handler used by
  the DTC-0x17 shadow pairs elsewhere in this firmware) → **`FUN_00071272`** (the FOC math core,
  see below) → `FUN_000710d4` (post-check: recomputes the same checksum, updates
  `gp-0x4f98`/`gp-0x4498` shadow pair OR calls `FUN_0006b9ee` on mismatch) → sets `gp-0x2abc=1`.
- `FUN_0006adfe` (atan2 helper) is **pure fixed-point** (shl/sar/add/sub/cmp only, CORDIC-style,
  LUT at `tp-0x2c84` = absolute `0xBC37C`) — no FPU instructions at all. Confirms not everything in
  this pipeline is float; angle extraction is fixed-point, the motor-model math (see below) is FPU.
- `FUN_00065afe`'s "else" branch (used when a redundant-sensor mode flag `gp-0x4e3e` is 1) reads
  **`gp-0x6b98` at `0x65c90`** (`ld.h -0x6b98,gp,r15`) purely to check its **SIGN** — selects
  between two near-identical formula branches (an MTPA/advance-angle correction keyed on commanded
  torque polarity, using constants at `tp+0x6000..0x602c`), NOT as a magnitude/Iq reference.

## FUN_00071272 — the FOC math core (EVIDENCE, disasm-verified)

- Address range `0x71272-0x75717` (0x44A5 bytes, 5334 instructions per `search_instructions`
  `instructions_scanned`). **One single function, no further calls out** except:
  `FUN_0006129a` (a fault/output-relay mode selector, sets a 12-entry duty array
  `gp-0x4e1c..gp-0x4dee` to a safe `0xc800` pattern in fault modes 1/2), `FUN_0006b9ee` (shadow-
  mismatch fault handler), and a cluster `FUN_00082524..0x825c8` (small ping-pong/double-buffer
  pointer selectors for a debug/telemetry logger — NOT math helpers).
- **Confirmed HARDWARE FPU present** on this V850E2Px4: real mnemonics are `mulf.s`, `addf.s`,
  `subf.s`, `divf.s`, `maddf.s` (fused multiply-add), `msubf.s`, `nmsubf.s`, `cmpf.s`, `negf.s`,
  `maxf.s`, `cvtf.ws`/`cvtf.uws`, `trncf.suw` — all with a **`.s` suffix**. ⚠ **Tool trap**:
  `search_instructions mnemonic=addf` / `mnemonic=mulf` (no suffix) returns a **misleading zero**
  even though the substring-match tool description implies it should match `addf.s`/`mulf.s`. This
  cost significant time before being caught by cross-checking against a raw disassembly. Always
  search the exact `.s`-suffixed mnemonic on this ISA.
- Instruction census in this one function: 66× `addf.s`, 106× `maddf.s`, 300+ `mulf.s` (search
  truncated at the 300-result limit — true count is higher), 12× `divf.s`, 0× any sqrt mnemonic.
  This is an enormous, fully-inlined floating-point motor-model computation, not a compact PI.
- **`gp-0x6b98` (the merged torque command) has ZERO reads/writes inside `[0x71272,0x75717]`** —
  exhaustively confirmed: the 45-entry program-wide reader/writer list for `-0x6b98` (from
  `search_instructions`) contains no address in that range. This is a **verified negative**, not a
  tool-null artifact (corroborated by manually checking every one of the 45 hits' addresses against
  the function's bounds). **The current loop's Iq/Id reference does NOT enter via a direct read of
  the outer torque command inside this function.** The bridge variable (whatever RAM cell actually
  carries the scaled reference into this function) was **NOT** identified this session — see Open
  Items.
- The true measured phase currents were also not conclusively located inside this function: neither
  the raw ADC quartet (`gp-0x4f2a/28/26/2c`, confirmed to be resolver sin/cos, not phase current) nor
  the `FUN_0006428e` pair (`gp-0x4f14/-0x4f12`) are read here (`search_instructions` returned zero
  for all four offsets scoped to this function). `gp-0x4f0c` (and presumably its sibling `gp-0x4f0a`)
  **is** read here at `0x71354`, alongside a `0.015625` (1/64) scale — but per its use elsewhere
  (`FUN_0007c4f2`, a thermal/power estimator, treats it identically) this looks more like a
  **temperature or DC-bus-voltage** channel than a phase current. Sole producer of both
  `gp-0x4f0a`/`gp-0x4f0c` is `FUN_00063818` (not traced this session).
- **A flash-resident "motor parameter table" was found and is DISTINCT from the compact `0xC6xxx`
  cal block.** `FUN_00071272` reads dozens of `tp+0x60xx..0x6cxx` constants (absolute
  `0xBF000+0x60xx` = **`0xC50D0`..`0xC5D84`ish**) — i.e., inside the flash region CLAUDE.md already
  flags as "the 0xC5000 mystery block" (bootloader-skipped, CRC vestigial, previously believed
  possibly-unused). **It is NOT unused** — the FOC core reads it every ADC-ISR cycle. Content
  strongly resembles motor electrical/thermal characterization constants (Rs, L, flux-linkage-like
  terms, thermal time constants) converted from cal ints to float ONCE per power-up (gated on
  `gp-0x2863`/`gp-0x2862` first-run flags) then cached in a private low-gp scratch block
  (`gp-0x380..gp-0x4b0`-ish, ~154 distinct small offsets used, none overlapping the well-known named
  RAM vars like `gp-0x6b98`/`gp-0x6ac0`). Key anchor: `ep = tp+0x6574` (movea, confirmed at 8
  call-sites) = absolute **`0xC5574`**, a small struct (fields at ep+0/4/8/0x18/0x1c ≈ `0xC5574`,
  `0xC5578`, `0xC557C`, `0xC558C`, `0xC5590`) used in a symmetric ±limit clamp on a **SPEED** value
  (`gp-0x42c = float(gp-0x6abe)`, motor electrical-rate raw) — traced 3× (nearly identical inlined
  blocks at decompiled-C lines ~316-335, ~771-790, ~2115-2134), NOT a current-error/PI-output clamp.
  ⚠ This clamp target was initially mis-hypothesized as a PI anti-windup saturate; disasm-level
  tracing of its SOURCE (line 114 of the extracted decompile) corrected this to a raw speed clamp.
- **No literal, isolated Kp/Ki pair was located.** Given the near-total absence of a helper-function
  decomposition (everything inlined) and the presence of a large motor-parameter table feeding a
  decoupling/feedforward-style computation (quadratic-in-speed impedance terms, `divf.s` denominator
  patterns matching Z(ω)=R²+(ωL)²-style math seen in the sibling function `FUN_0007c4f2`), the
  **BELIEF** (not confirmed) is that this control law is model-based/feedforward-heavy rather than a
  textbook `Kp·e + Ki·∫e` PI — but this was NOT proven; 300+ `mulf.s` sites were far too many to
  hand-trace exhaustively in one session. **Task 2/3 of the PI-gain investigation are UNRESOLVED.**

## Downstream duty path (EVIDENCE)

- `gp-0x4e1c..gp-0x4dee` = a 12-entry `ushort` array, each of the 6 "real" duty values stored
  TWICE into adjacent cells (a lockstep/redundant-copy pattern, matching this firmware's general
  dual-channel safety architecture). Written to a safe `0xc800` pattern by `FUN_0006129a` in fault
  modes; **NOT written by `FUN_00071272` itself** (confirmed: zero `st.h` to `-0x4e1c` inside its
  body) — the actual per-cycle writer of this array during normal running was NOT identified this
  session (open item).
- `FUN_0006166a` (sole writer of `gp-0x2bf0`, confirmed via `search_instructions`) copies this
  12-entry array into a "committed" buffer (`gp-0x2bec..gp-0x2bc2`-ish) applying a **minimum-pulse-
  width / dead-time-style clamp** gated on `gp-0x4e6d`, using cal **`tp+0x59c8`** (absolute
  **`0xC4BC8`**) as the minimum-width threshold. This is a PWM output-shaping clamp, not a current-
  loop voltage saturation per se.
- A separate interrupt, **EIIC 0x970 → `FUN_00061614`**, dispatches an 8-entry function-pointer
  table (`tp-0x2d40`) then calls **`FUN_0006c5ce`** with 4 args pulled from the committed buffer,
  which is what actually writes **TS0CMPU/V/W** (see below). This confirms compute (ADC-ISR,
  `FUN_00071272`) and PWM-register commit (`FUN_00061614`/`FUN_0006c5ce`) are **two separate
  interrupts**, a double-buffering/synchronization scheme common in motor-control firmware.

## TSG20 PWM timer — loop rate (STRONG EVIDENCE, disasm + SVD cross-checked)

`FUN_0006c446` = TSG20 (three-phase HT-PWM timer) power-up init. **Ghidra's decompiled `_DAT_ffffccXX`
labels for this function are UNRELIABLE** — the decompile output itself carries the warning "Globals
starting with '_' overlap smaller symbols at the same address", and hand-verification against the raw
disassembly found at least one label swapped (`_DAT_ffffcc00` shown for a store that raw bytes prove
targets `0xFF82E200`, not `0xFFFFCC00`). **All figures below are from the raw disassembly
(`disassemble_function`), cross-checked address-by-address against
`analysis-2020accord/svd_for_ghidra/UPD70F3508_V850E2Px4.svd`**, not from the decompiled C.

TSG20 peripheral (SVD `<peripheral><name>TSG20</name>`) has TWO address blocks: base
`0xFF82E200` (offsets 0x0-0x12: TS0IOC0/TS0IOC1/TS0CTL0/TS0CTL1/TS0DTPR) and a second block at
`baseAddress + 0x7CEA00` = **`0xFFFFCC00`** (offsets 0x0-0xC6: TS0IOC2, TS0CTL3/4/5, TS0CMPx,
**TS0CMPU/V/W**). This SVD-documented `+0x7CEA00` mirror is what makes `0xFF82E2xx` and `0xFFFFCCxx`
the SAME physical peripheral register set, resolving why the task's known anchors
(`0xFFFFCCB0/B4/B8` = CMPU/V/W) and the init function's `0xFF82E2xx` writes appear side-by-side in
one routine.

Raw-disassembly-confirmed writes in `FUN_0006c446`:
- `st.h r16,-0x3638[r0]` → **`0xFFFFC9C8`** = `0x700` (a DIFFERENT peripheral, not yet identified —
  possibly ADC control; not traced further this session).
- `sst.b r9,0x0[ep]` (ep=`0xFF82E200`) → **TS0IOC0 = 0x7E** (== SVD reset value; explicit re-assert,
  not a functional change).
- `movea 0x1388,r0,r7; st.w r7,-0x33a8[r0]` → **`0xFFFFCC58` = TS0CMP0 = 0x1388 = 5000 decimal.**
  SVD: `TS0CMP0` @ offset `0x7CEA58` = `0xFF82E200+0x7CEA58` = `0xFFFFCC58` — exact match.
  **TS0CMP0 is the TSG2 peak/period-defining compare register** (HT-PWM mode is a triangular/
  up-down carrier per `TS0CTL0.TS0MD=01`, confirmed set to 1 in the same function).
- `movea 0x50,r0,r14` → **`0xFFFFCC6C`=`TS0DTC0W`=80** and **`0xFFFFCC70`=`TS0DTC1W`=80** (dead-time
  setting registers, both phases; 80 ticks).
- `movea 0x1428,r0,r10; st.h ×3` → **`0xFFFFCCB0`=TS0CMPU, `0xFFFFCCB4`=TS0CMPV, `0xFFFFCCB8`=
  TS0CMPW, all = 0x1428 = 5160 decimal.** SVD-confirmed register names (`TS0CMPU`/`V`/`W` @ offsets
  `0x7CEAB0/B4/B8`) match the task brief's own stated anchor addresses exactly. **5160 > the 5000-tick
  period** — this pins all three phase compares outside the valid counting range at power-up, i.e. a
  deliberate **safe "outputs held inactive" startup default** (the real per-cycle duty values,
  written elsewhere at runtime by whatever populates `gp-0x4e1c..gp-0x4dee`, are what actually drive
  the motor once enabled).
- `st.h r13,-0x37e0[r0]` → `0xFFFFC820` = `0x1387` = **4999** (a SEPARATE register outside both TSG20
  blocks — likely a companion ADC-sampling/sync timer's reload value, one less than TSG20's 5000,
  consistent with an N-1 reload convention for the same nominal period). Not identified by name this
  session (SVD lookup not attempted for this address).

**Loop-rate conclusion (belief, built on evidence + one carried assumption):** TSG20 period register
= 5000 ticks, HT-PWM (triangular) mode ⇒ one full carrier period = 2×5000 = 10000 ticks. **IF** the
TSG20 clock source is undivided PCLK **and** PCLK = 80 MHz (this specific 80 MHz figure is an
assumption **carried from the OSTM0/control-task rate analysis elsewhere in this project's memory**,
itself flagged there as "plausibility, not traced" — it was NOT independently re-derived for TSG20 in
this session), carrier frequency ≈ 80 MHz / 10000 = **8 kHz**. The dead-time value (80 ticks ≈ 1 µs at
80 MHz) is a textbook-normal automotive MOSFET/IGBT dead time, which is a *consistency check* in favor
of the 80 MHz assumption, not independent proof of it. The ADC-complete ISR (`FUN_0006404c` →
`FUN_00071272`) is very likely synchronized to this carrier's peak and/or valley match (SVD documents
`TS0CTL5` bits explicitly for "generate ADC trigger at peak/valley timing") — **this specific linkage
(TS0CTL5's actual programmed value) was NOT confirmed this session** — so the FOC/current-loop
execution rate is estimated at **8 kHz (once per carrier period) or possibly 16 kHz (if triggered at
both peak and valley)**, i.e. kHz-class as the task brief assumed, and clearly faster than the
separately-confirmed ~1 kHz outer control task (`w_steer_control_task`/OSTM0, see
[[control-task-tick-confirmed-1khz]]).

## Open items / what would resolve them

1. **Iq/Id reference bridge variable** — what RAM cell, written by the ~1kHz outer task from
   `gp-0x6b98`, is actually read by `FUN_00071272` as the current-loop's setpoint. Next step: trace
   forward from `gp-0x6b98`'s ~45 readers for one in the `0x60000-0x69000` range not yet checked
   (`FUN_00069b8e`, `FUN_0006e09a`/`0140` already ruled out as startup-only), or trace backward from
   one of `FUN_00071272`'s ~154 small gp-offsets to find which one is written by a function OUTSIDE
   the `0x60000-0x83000` FOC-ISR code region.
2. **Literal Kp/Ki isolation** — not achieved. Candidate structures worth a focused follow-up:
   the `ep=tp+0x6574` struct (`0xC5574..0xC5590`ish, currently identified as a speed-clamp source,
   but could have other unexamined fields), and the `tp+0x6760-0x6784` (6 floats) and
   `tp+0x6698-0x6b8` (9 floats) clusters flagged but not traced to their consuming instructions.
   Recommended next step: use `get_function_pcode` on narrower address SLICES (not the whole
   function) once a specific `maddf.s`/`mulf.s` site is chosen, to get SSA-level def-use without the
   full-function token-budget problem.
3. **PI output saturation / anti-windup** — no confirmed instance found; the one saturate pattern
   located was proven (by tracing its source) to be a speed clamp, not a current-error or Vd/Vq
   clamp. No `sqrtf`-class instruction exists in this function (0 hits for `sqrt` mnemonic), so if a
   voltage-magnitude (circular) limit exists it is NOT computed as `sqrt(Vd²+Vq²)` here — it may be a
   per-axis clamp (structurally identical to the speed clamp already found) that was not
   distinguished from it, or it may live in `FUN_0006166a`'s min-pulse-width stage instead.
4. **TS0CTL5 (ADC-trigger-generation) programmed value** — not read this session; would directly
   confirm whether the ADC ISR fires once (peak only) or twice (peak+valley) per carrier period,
   settling 8 kHz vs 16 kHz.
5. **PCLK absolute value for TSG20** — inherited assumption (80 MHz), not re-derived independently
   for this peripheral this session (only cross-checked via a plausible dead-time sanity value).
6. `0xFFFFC820/824/828` (4999/0x7e4/800) — a probable companion ADC-sync timer, register names not
   looked up in the SVD this session.

## Tool-policy notes for future sessions on this function
- `search_instructions mnemonic=addf`/`mulf` (bare, no `.s`) is a **misleading zero** on this ISA —
  always use the exact `addf.s`/`mulf.s`/`maddf.s`/`divf.s`/`subf.s` spelling.
- Decompiled `_DAT_ffffccXX`-style labels in functions flagged with the "Globals starting with '_'
  overlap smaller symbols" warning are NOT reliable — verify against raw `disassemble_function`
  output before citing an absolute peripheral address from decompiled C.
- `decompile_function` on `FUN_00071272` returns ~150K characters and will exceed the tool's token
  cap — must be redirected to a file and processed with `Grep`/Python, or use `disassemble_function`
  scoped queries plus `search_instructions` for the tp/gp offset catalog instead of one bulk
  decompile.
