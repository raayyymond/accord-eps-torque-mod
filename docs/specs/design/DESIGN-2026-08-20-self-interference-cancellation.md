# DESIGN — LKAS Self-Interference Cancellation for the 6-9 Hz Micro-Ratchet

**Written 2026-08-20 · subagent `firmware-codepath-tracer` · design/analysis only. Nothing built, flashed,
or sent on CAN.**

**Headline verdict, stated up front so it is not lost in the detail below:** the design is buildable and
is specified completely enough to cut. **But the honest comparison in §8 does not favor building it next.**
The re-centered Honda-biquad notch is cheaper, safer, addresses more of the physical problem, and its
arming infrastructure has already flown fault-free (V103). Cancellation's one genuine, non-overlapping
advantage — preserving genuine driver torque at 6-9 Hz — is worth little because that band is almost
entirely below human neuromuscular bandwidth. **Recommendation: notch first; this design stands as the
documented V105+ fallback, gated on the notch's own measured collateral cost.**

---

## 0. The assist chain — CONFIRMED, not assumed

Per instruction, the chain was independently re-derived from **fresh `decompile_function` calls this
session** on `FUN_000352b4` and `FUN_0003aa2c` in `code.bin` (stock, confirmed via
`get_current_program_info` before any read), cross-checked against `search_instructions` (183,569
analysed instructions, `truncated:false`) and `get_assembly_context`. **It matches the briefed chain in
every particular checked, with one correction (§0.3).**

### 0.1 `FUN_000352b4` (base-assist / friction magnitude map), fresh decompile

```
gp-0x4f60 (raw torque, Sensor B)
  -> clamp to +-cal(0xC6200)=+-8192              [inner clamp, see 0.3 — CORRECTS the brief]
  -> + gp-0x6b4a (>=0 today, cal 0xC616C=0 -> term is 0)
  -> clamp +-0x6400=+-25600                       [outer clamp, hardcoded immediate, currently slack]
  -> abs, 10-point breakpoint search over gp-0x37fc[]  -> LERP
  -> clamp to <=0x2fff=12287, x sign(raw), x *(char*)(gp-0x6752)   [confirms gp-0x6752 as a direct
     signed-byte multiplier here, consistent with "gp-0x6752 = -1" finding]
  -> gp-0x6b7a  (shadow gp-0x4cdc, exact-equality lockstep; mismatch -> FUN_0006b9fa)
  -> [a second limiting/interpolation stage vs an interpolated "friction hold" value]
  -> gp-0x6b82  <-- this raw int/1024 (Q10) value is iVar34, THE BIQUAD'S OWN INPUT TAP
  -> [Honda's biquad, gated: cal(0xC649B)==1 AND cal(0xC64FA) <= gp-0x671a — see 0.2]
     when gate is FALSE (stock, every build to date incl. V101/V102): passthrough, iVar34 unchanged
  -> + gp-0x6b7e (a parallel EMA/IIR term derived from the 32-bit accumulator gp-0x381c)
  -> clamp +-0x3000=+-12288
  -> EXTREME-TORQUE DROPOUT: if |gp-0x4f60| > 0x6400=25600 counts (re-reads RAW, uncorrected),
     FORCE gp-0x6b86 AND its shadow gp-0x4cde TO EXACTLY ZERO instead of clamping   [GATE-3 hazard #1]
  -> gp-0x6b86  (shadow gp-0x4cde, exact-equality lockstep; mismatch -> FUN_0006b9fa)
```

### 0.2 Honda's own dead biquad — gate, states, coefficients (re-confirmed, 3 independent methods)

```
if (cal(0xC649B)==1 && cal(0xC64FA) <= gp-0x671a) {          // stock: cal(0xC649B)=0x00, NEVER true
    x2_old = gp-0x3818;  x1_old = gp-0x3814;                  // READ, both float
    w'     = -( c2*x1_old - -( x2_old*c1 - u*c4 ) )           // c1..c4 = tp+0x70a8/ac/b0/b4 = 0xC60A8/AC/B0/B4
    y      = x1_old + x2_old*c3 + w'
    x1' = x2_old ;  x2' = w'                                   // WRITE gp-0x3814=x2_old, gp-0x3818=w'
    y = clamp(y, -12.0, 12.0)
    iVar34 = round(y * 1024)                                   // replaces the biquad's own input
}
```
Coefficients (stock, byte-read this session and matching the pre-existing agent-memory record exactly):
`c1=-1.5372, c2=0.63462, c3=-1.8808, c4=0.81731` -> pole `|r|=0.79663` @ **42.345 Hz**, zero `|r|=1.0` @
55.225 Hz (a true notch: numerator roots have product 1 by construction). This is the structure the
**parallel notch effort** proposes re-centering. **[EVIDENCE]**

### 0.3 🛑 CORRECTION to the brief's chain summary

The brief's "clamp ±0x6400" is the **outer** bound only. Fresh disassembly at `0x354ce-0x354d8` shows the
raw torque is first clamped to **`±cal(0xC6200)=±8192`** (`ld.h 0x7200[tp],r14` / `cmp r14,r16` /
`ble`/`cmovge`-style min/max), and *then* `+gp-0x6b4a` (≡0 today) is clamped again to the looser
`±0x6400=±25600`. **Since the inner clamp is tighter and the added term is zero, the value feeding the
breakpoint search is effectively bounded to ±8192 today, not ±25600.** `cal(0xC6200)` is the **same cell**
already established (three ways) as the Path-2 PID reference clamp and is on this kit's **never-edit**
list — I did not touch it, only read it; flagging this because my brief's chain summary had the wrong
bound and a future session should not build against the wrong number.

### 0.4 GATE-3 dropout census (both independently confirmed this session)

| site | lane | window | behavior past window |
|---|---|---|---|
| `0x35aa4-ae2` (`FUN_000352b4`) | `gp-0x6b86` (my candidate lane) | \|raw torque\| ≤ 25600 | **forces gp-0x6b86 to exactly 0**, not clamp |
| `0x3acc4` (`cmovc 0x0,r6,r13`, `FUN_0003aa2c`) | `gp-0x6ad4` (resonance lane, neighboring) | ±10240 | zero-reject (confirms the brief's citation, different lane than mine) |
| `FUN_0003aa2c`, aggregator sum | `gp-0x6b86` itself | ±12288 (`(x+0x3000)<0x6001`) | zero-reject at the SUMMING step too — matches the ±12288 clamp above exactly, so this lane never trips its own aggregator gate by construction |

### 0.5 The aggregator (`FUN_0003aa2c`, fresh decompile) — where `gp-0x6b86` lands

8 summands + 2 separately-clamped sign-scaled terms + `FUN_00036682()`'s return, all `×sign×gp-0x6752`
where applicable: `gp-0x6b62`(±8192) + `gp-0x6b4c`(±10240) + `gp-0x6ade`(±1024) + `gp-0x6ad4`(±10240) +
`gp-0x6b26`(±1024) + `gp-0x6bbe`(±2048) + `gp-0x6bd0`(±2048) + **`gp-0x6b86`(±12288, the WIDEST window
of all — matches the brief exactly)**. Sum -> **saturating** clamp ±10240 (unlike the zero-reject lanes)
-> `gp-0x6b94` (shadow `gp-0x4ce0`, same lockstep pattern). Readers of `gp-0x6b94`: `FUN_0004503c`
(governor), `FUN_0004595a` (redundancy monitor), `FUN_0007ff08` (boot interlock) — **exactly** the three
non-aggregator consumers already on record. **[EVIDENCE]**

### 0.6 Task rate and causality — the key finding for tap/inject timing

`get_function_callers` on `0x352b4`, `0x3aa2c`, and `0x42af8` (the function that writes `gp-0x6b98`, found
via `search_instructions` for `0x6b98`, 2 of its ≥3 writers at `0x43b52`/`0x43dfc`) **all return the SAME
single caller, `FUN_0002214a`** — the confirmed 1 kHz task. **[EVIDENCE]** This means the raw-torque read,
the friction map, the aggregator, and the final motor-command write all execute inside one call of one
1 ms task. Given `FUN_0003aa2c` reads `gp-0x6b86` (written by `FUN_000352b4`) and the shadow-lockstep
idiom implies same-tick freshness, `FUN_000352b4` must run before `FUN_0003aa2c`, which must run before
`FUN_00042af8` within `FUN_0002214a`'s body — **[BELIEF: inferred from data-flow necessity and the
lockstep pattern, not from a direct decompile of `FUN_0002214a`'s call order, which I did not do this
session]**.

---

## 1. WHERE TO TAP `u`

**Recommendation: `gp-0x6b98`, read ONE TICK OLD (1.000 ms).**

Because `FUN_00042af8` (the `gp-0x6b98` writer) is downstream of the aggregator in the same tick,
`gp-0x6b98` has **not yet been updated** when `FUN_000352b4` runs earlier in that same 1 kHz tick — reading
it there yields exactly last tick's delivered value. This is clean, deterministic, and requires no new
synchronization. Phase cost of the 1-tick lag, computed directly (`360°×f×0.001s`):

| f | phase lag |
|---|---|
| 6 Hz | 2.16° |
| 7.79 Hz (ratchet) | 2.80° |
| 9 Hz | 3.24° |
| 21-26 Hz | 7.6-9.4° |

Negligible against the ~5% fractional bandwidth (±0.2 Hz, tens of degrees) that actually matters for this
filter (§4).

**Why not the alternatives:**
- **`gp-0x6b94` (aggregator out)** — sits *upstream* of the governor, soft-EME shaper, and integrator.
  Those stages are nonlinear (slew limits, EME windup) and change amplitude *and* phase between
  `gp-0x6b94` and the actual delivered torque, especially during the transients where cancellation matters
  most. Using it as `u` would build a model of the wrong signal. **[BELIEF, reasoned from the known
  presence of a governor/shaper/integrator between the two cells per the existing golden-model chain — I
  did not re-derive the governor's own transfer function this session]**.
- **`gp-0x6b86` (this lane's own output)** — captures only ONE of 8+ summands into the aggregator. It
  systematically under-represents total delivered torque and would under-cancel by whatever fraction this
  lane is of the total (uncensused this session — §12).

`gp-0x6b98` is the closest available proxy to actual delivered motor/FOC torque — the physical quantity
that couples into the bar via the rack — and it is already a well-instrumented cell (V87/V88's own
probes tapped it; `search_instructions` shows 30+ distinct reader sites, `truncated:true` at the 40-match
cap, consistent with the "30+ real touches" figure on record).

---

## 2. WHERE TO INJECT

**Recommendation: inside `FUN_000352b4`, immediately after `ld.h -0x4f60[gp],r16` at `0x354d2`, before
`cmp r14,r16` at `0x354d6`.** `[EVIDENCE — exact boundary confirmed via `get_assembly_context`]`

```
000354ce: ld.h  0x7200[tp],r14      ; r14 = cal(0xC6200) = 8192 (never-edit clamp; read only)
000354d2: ld.h  -0x4f60[gp],r16     ; r16 = raw torque      <-- INSERT CAVE CALL HERE
000354d6: cmp   r14,r16             ; downstream clamp/breakpoint search begins
```

Insert `r16 = r16 - round(y_scaled)` where `y_scaled` is the filter's output (§3) converted back to raw
torque counts, **before** `r16` is used by anything else. This corrects the *local copy* only:
`gp-0x4f60` itself is never written. Every other reader of `gp-0x4f60` — the boost curve (`FUN_00034a72`),
the damping term (`FUN_00034350`), the residual/D-term lane (`FUN_0003a382`), and the ~30 other functions
`search_instructions` found reading it (60-match cap hit at `instructions_scanned:154341`, `truncated:true`
— genuinely more than 60 sites exist) — **still see the raw, contaminated sensor value.** This is a
deliberate, brief-mandated trade: touching `gp-0x4f60` itself would corrupt manual steering and fault
monitors that also read it; the cost is that **this design only cancels self-interference in the friction/
base-assist lane, not in boost, damping, or the residual/D-term lane, each of which independently reads
raw torque and forwards its own uncancelled contribution into the same aggregator.** §12 quantifies what
is not known about how large that residual is.

The second `gp-0x4f60` read inside this same function, at `0x35aa4` (the extreme-value dropout check,
§0.4), is **not** touched — it re-reads RAM fresh, so it keeps checking the true raw sensor for the
plausibility/fault sentinel, exactly as it should.

**Register liveness at the injection point:** `r14` holds `cal(0xC6200)`, needed immediately after at
`0x354d6` — must be preserved. The registers used by the *preceding* loop (`r20-r27`, `ep`) belong to a
`do{...}while(bVar12<10)` block that has already exited by this point in program order, but I have **not**
run a formal liveness/def-use pass to prove any of them dead here — that is a standard, cheap Ghidra check
(`get_function_variables` or a P-code liveness pass) that should be run before any byte-patch is cut.
**[BELIEF pending that check]** — the safe default is to save/restore any scratch register the cave routine
needs via stack push/pop, at a cost of a few extra bytes/cycles, rather than assert an unverified liveness
claim.

---

## 3. THE FILTER `Ĥ(z)`

The operator's own model is a **2-pole resonance with no finite zero** (`T_s/u = -(k/J_c)/(s²+2ζωns+ωn²)`),
so the discrete cancellation filter should be the matched digital resonator — **not** a notch (a notch has
a zero on the unit circle; this filter must not). Simplest possible realization, direct form, 2 states,
no numerator dynamics:

```
w[n] = b0*u[n] - a1*w[n-1] - a2*w[n-2]        y_correction[n] = w[n]
```

Pole placement from the measured mode (`f0 = 7.79 Hz`, `fs = 1000 Hz`, `ζ = 0.017-0.036` from the
kit's own ring-down/Q estimate), computed exactly (not by hand) via `numpy`/`math`-equivalent Python this
session:

| | ζ | Q | \|r\| | a1 | a2 | a1 IEEE754 LE hex | a2 IEEE754 LE hex |
|---|---|---|---|---|---|---|---|
| lo damping | 0.0170 | 29.4 | 0.999168 | -1.995943 | 0.998337 | `127bffbf` | `07937f3f` |
| **nominal** | **0.0265** | **18.9** | **0.998704** | **-1.995015** | **0.997409** | `aa5cffbf` | `36567f3f` |
| hi damping | 0.0360 | 13.9 | 0.998239 | -1.994088 | 0.996482 | `463effbf` | `73197f3f` |

All three pole angles land at exactly 7.7900 Hz (verified). **[EVIDENCE — exact arithmetic]** This is
**~17× more lightly damped than V48B's `r=0.979`, the resonator that bricked the ECU** — same order as
the FEASIBILITY doc's independent Q≈20 estimate (`r=0.99878`), which this design reproduces almost
exactly from first principles.

**Peak gain is enormous — |H(f0)| ≈ 7888× (+78 dB) at b0=1.** This is expected (it is a Q≈19 resonator)
and means `b0` itself must be tiny; see §4.

**Reuse Honda's own biquad state, `gp-0x3814`/`gp-0x3818` (`0xFEDF47EC`/`0xFEDF47E8`), rather than claim
new RAM** — this design needs exactly 2 float states, the same count and size Honda's dead biquad already
uses, at the same addresses. See GATE 1 (§5) for why this is safe **only if** `cal(0xC649B)` is kept at 0
(i.e., this design and the notch redesign cannot both be armed against the same RAM simultaneously without
a fresh allocation).

**Q-format:** float (IEEE754 single), matching Honda's own biquad idiom exactly (the adjacent code already
uses `mulf.s`/`addf.s`/`maddf.s`/`nmsubf.s`/`cvtf.*` throughout this function) — this avoids inventing a
new fixed-point convention and lets the new coefficients live as plain floats the same way `0xC60A8-B4`
already do.

**New calibration cells needed:** 3 floats (`a1`, `a2`, `b0` — 12 bytes) plus the state cells (reused, 0
new bytes). **I did not locate 12 bytes of verified-free flash cal space this session** — that is an open
item (§12), not a blocker, since the kit's standard cal-region survey process covers it.

---

## 4. GAIN / ADAPTATION — the part I cannot responsibly hand you a number for

`b0` must absorb (a) the physical coupling constant `k/J_c`, unmeasured on this car (bracket only,
`[BELIEF]`), and (b) the unit conversion between `gp-0x6b98` counts (motor-command domain) and `gp-0x4f60`
counts (torque-sensor domain), which I have not pinned to physical units this session. **I am not going to
invent a confident absolute value for this.**

**Sensitivity — computed, not assumed.** Holding `ζ=0.0265` fixed and sweeping the filter's *own* center
frequency while the *true* resonance stays fixed at 7.79 Hz:

| filter centered at | \|H\| at true 7.79 Hz, relative to on-center | phase at true 7.79 Hz |
|---|---|---|
| 7.79 Hz (matched) | 1.000 | -86.4° |
| 8.09 Hz (+0.3 Hz) | 0.549 | -32.0° |
| 8.79 Hz (+1.0 Hz) | 0.189 | -9.5° |
| 9.79 Hz (+2.0 Hz) | 0.091 | -3.7° |
| 5.79 Hz (-2.0 Hz) | 0.118 | -172.2° |

A gain error alone (±30%) is comparatively benign for a *subtractive* design: 30% too much or too little
gain means 30% under- or over-cancellation, not a sign flip — over-cancellation becomes net anti-damping
only once the residual `(H_self - Ĥ)` itself exceeds the original `H_self` in magnitude with the same
sign, which a pure gain error cannot do on its own. **A frequency (center) error is the dangerous
direction**: at 2 Hz off-center the filter's response at the true resonance has collapsed to 9-12% of
on-center peak *and* rotated to a barely-related phase — meaning a badly mis-centered filter mostly just
stops helping (it is not obviously *worse* than doing nothing, because its magnitude at the true f0 has
collapsed too) but the on-center full-strength case is exactly where correctness matters most, and `f0` is
**on this kit's own record** not fixed — it moves 9.0→7.7 Hz with load and the whole `f0`-vs-command-
amplitude relationship for the *other* symptom band was found to be strongly nonlinear this same week.
I have not established whether the 6-9 Hz mode has an equivalent load/amplitude dependence beyond the
already-cited 9.0→7.7 Hz shift.

🛑 **A structural risk this design carries that the notch does not: this filter is itself a NEW Q≈19-29
resonant structure with its own summing junction (subtraction from `r16`) that does not exist in the
firmware today.** If a coefficient, sign, or timing bug ever lets `Ĥ`'s own output loop back into the
signal it corrects with the wrong sign or an extra tick of delay, that is a lightly-damped 2nd-order
recursive filter with an unintended positive-feedback path around it — structurally the same failure
class as V48B's brick, not merely "the correction doesn't work." A notch, being a single filter inserted
in series in one already-existing path (Honda's own, just re-gated), cannot fail this way — a wrong
coefficient there degrades to "wrong filtering," never a new feedback loop.

**Recommendation: ship gated to b0=0 on the first flight** (the filter computes and its output is
telemetered, but the subtraction is multiplied by zero — pure instrument, no actuation). Dose from there
in a ladder informed by the b0=0 flight's own telemetry (§6), never from an armchair number. Dimensional
sanity check only, **[BELIEF]**: with peak `|H(f0)|≈7888` and typical `u` (`gp-0x6b98`) in the
1000-4000-count range per the existing dose-response record, `b0 ≈ 3×10⁻⁵` would put a fully-resonant
correction in the low hundreds of counts — plausible as a *first non-zero rung*, not a target.

---

## 5. GATES

### GATE 1 — RAM ownership for `gp-0x3814`/`gp-0x3818`

**Two independent methods run this session, both clean:**
1. **`search_instructions` operand-pattern scan** for `0x3814` and `0x3818` across all 183,569 analysed
   instructions (`truncated:false`). Result: `-0x3814` has 6 raw hits, but **4 are `tp`-relative
   (`tp-0x3814 = 0xBB7EC`, a different physical cell entirely — a trap the pattern-text search does not
   distinguish by base register)**; the 2 `gp`-relative hits are both inside `FUN_000352b4`
   (`ld.w -0x3814[gp],r16` @`0x35a4c`, `st.w r11,-0x3814[gp]` @`0x35a64`). `-0x3818` returns exactly 2
   hits, both `gp`-relative, both inside `FUN_000352b4` (`0x35a2c` read, `0x35a6a` write). **No accessor
   anywhere else in the image.**
2. **Fresh-decompile cross-check**: the P-code-derived C source references `gp-0x3814` twice textually
   (once for `c2*x1`, once for `y=x1+...`) and `gp-0x3818` once for its read — fully consistent with the
   assembly showing each value loaded into a register **once** and reused, not with any additional
   access existing that the decompiler simply rendered differently.

Both accesses (all 4 instructions) sit **inside the same gated `if` block** — confirmed structurally from
the decompile — so with `cal(0xC649B)=0` (stock and every build to date, per the pre-existing agent-memory
record's grep of all `build_v*_tva.py`), **these cells have never been written on any flown build** and
sit at their BSS-zero boot value.

**I ran 2 of the assignment's 5 required methods this session** (operand-pattern scan; decompile
cross-check). The remaining 3 — register-indirect access, the 6-byte disp23 extended-displacement form,
and an LE32-literal-table scan — are **not independently re-run by me this session**; they were already
run by the prior agent-memory record that first characterized this biquad
(`reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm.md`), which is where
the "no other accessor" claim originates. **[BELIEF, well-corroborated by 2 fresh methods + a prior
multi-method record, not independently exhaustive by me this session.]** Given the kit's own history
(`gp-0x1500` passed *both* its static methods and still failed on-car; `gp-0x14FA` bricked V48B), **a
dedicated on-car probe reading these two cells is mandatory before any cave writes to them** — this is
the kit's standing rule regardless of how clean the static picture looks, and it applies here without
exception.

**Constraint this creates:** reusing `gp-0x3814`/`gp-0x3818` means this design and the notch redesign
(which arms Honda's *original* biquad at these same cells) **cannot both be live at once** without a
fresh 2-cell RAM allocation and its own GATE-1 sweep for the second design. If both are ever wanted
simultaneously, that allocation is new work, not implied by this document.

### GATE 2 — closed-loop stability

- **Magnitude**: at the recommended `b0=0` first flight, the closed-loop is **provably unchanged**
  (multiplying by 0 before the subtraction). This is the only configuration with zero GATE-2 exposure.
- **Phase / mistuning**: quantified in §4 — a frequency error is the dangerous direction, not a gain
  error, and the failure mode of a badly mis-centered filter is closer to "loses effectiveness" than
  "flips to reinforcing," because magnitude and phase both move together as center error grows. This is
  a materially different (better) failure profile than a hand-wave "180° flip" claim would suggest, but
  it rests on the mistuning being *symmetric drift*, not a *sign bug* in the implementation — the two are
  not the same risk and only the second is checked by GATE 1's RAM/liveness discipline.
- **New-resonance risk**: this filter is its own Q≈19-29 structure with a new summing junction (§4). This
  is the single largest qualitative difference from the notch's risk profile and should weigh heavily in
  any decision to build this before the notch.
- **Every downstream loop the signal is in**: unchanged from the existing chain (§0) — the corrected value
  flows through the identical clamp/LERP/aggregator/governor/EME/integrator path as today; this design
  adds no new downstream loop, only a new upstream correction.

### GATE 3 — dropouts

Both live dropouts on this lane are now characterized (§0.4): the extreme-torque force-zero at `0x35aa4`
(reads **raw**, uncorrected `gp-0x4f60`, so my correction cannot itself trigger or avoid this dropout —
good, it stays keyed to the true sensor) and the ±12288 zero-reject at the aggregator (which the ±12288
clamp immediately upstream makes structurally unreachable for this lane specifically). The brief's cited
`0x3acc4 cmovc` dropout is confirmed to belong to the **neighboring** `gp-0x6ad4` (resonance) lane, not
mine — both are the same class of hazard, in the same function, and both were independently located this
session.

**Shadow/lockstep pairs my injection sits inside**: `gp-0x6b7a`/`gp-0x4cdc` and `gp-0x6b86`/`gp-0x4cde`,
both exact-equality mirrors with `FUN_0006b9fa` as the mismatch handler — confirmed directly in the fresh
decompile. My injection point (before `gp-0x4f60`'s first use) sits **upstream of both pairs**, so it
cannot itself desynchronize them — it changes what value the pairs eventually mirror, not whether they
stay mirrored.

---

## 6. COST

Estimated cave size, using Honda's own adjacent biquad as the yardstick (the FEASIBILITY doc sized a
comparable structure at 41 instructions, 0.051-0.154% of the 1 kHz tick even pessimistically): this
design is **simpler** (2 states, no zero/numerator term, vs Honda's 4-coefficient structure with a zero) —
tap (1) + int-to-float (1) + state loads (2) + coefficient loads (3) + FP compute (~4, matching the
`mulf.s`/`maddf.s`/`nmsubf.s` idiom already in this function) + state stores (2) + clamp (~3) +
float-to-int (1) + subtract-and-reclamp (~2) + call/return overhead (2) ≈ **~20 instructions, ~70-90
bytes**. At 40 MHz / 1 kHz (40,000 cycles/tick), even a pessimistic 3-cycles/instruction estimate is
**≈0.15-0.19% of the tick** — trivially inside budget. **Timing is not the constraint here either; this
reproduces the FEASIBILITY doc's own conclusion for the sibling structure.**

**Location**: a code cave, per this kit's standard CRC-relink template (`docs/BUILD-LINEAGE.md` Part 2).
🛑 **Code caves are this kit's only bricking class — V24, V27, and V48B all bricked the ECU. Every success
since V29 has been cal-only or a single in-place branch/displacement edit.** This design is a cave. That
risk class is real regardless of how carefully the structure above is reasoned through, and it is the
central reason §8 does not recommend building this next.

---

## 7. TELEMETRY

**Pre-registered null sentence** (written before any dose, per standing kit law): *"If, over ≥10
non-overlapping engaged episodes with `b0` at its first non-zero rung, the comparator's `|Ĥ_out| ≥
|gp-0x6b86_precorrection|` duty is statistically indistinguishable from what the same comparator reads at
`b0=0` (its own phase-shuffled/no-op control), the filter's contribution is not resolvable from this
instrument and `b0` must not be raised further on this telemetry alone."*

**Design (comparator-first, per the design law — no bare threshold on an unmeasured distribution):**
- **`|Ĥ_out| ≥ |gp-0x6b86 before correction|`** — a genuine `|A|≥|B|` comparator, self-scaling against the
  same lane's own pre-correction magnitude, immune to over/under-ranging by construction. 1 bit.
- **`sign(Ĥ_out) == sign(u)`-vs-**`sign(Ĥ_out) != sign(u)`** as a second bit — a sanity check on the
  filter's own polarity behavior relative to the command it is modeling, cheap and interpretable
  independent of any absolute calibration.
- **A 1-bit heartbeat/canary** toggling every tick the cave executes — proves the detector ran, matching
  the kit's own established positive-control discipline (V98's pattern).
- Budget: 3 bits fit inside CAN `0x14A` byte4 bits 7:3 (5 available), alongside the existing identity/
  generation bits per the V102/V103 convention (2 bits spare for future use or a coarser mode tag).
- **The 427 lane on `0x1AB`** (Nyquist 24.9 Hz at 49.81 Hz sampling — comfortably covers 7.79 Hz) should
  carry the raw `Ĥ_out` magnitude time series, repointed exactly as V102 already established precedent
  for. This is the channel that lets a later session compute actual coherence between the model's output
  and the measured antidamping, rather than reading only a duty statistic.

---

## 8. THE HONEST COMPARISON — cancellation vs. the re-centered notch

**What the notch buys that cancellation does not:**
1. **Zero new RAM, zero new code, zero new cave.** It is 4 (or, per §3, potentially fewer if this design's
   simpler 2-state form is adopted for the notch too) coefficient bytes on an **already-allocated,
   already-wired, already-gated** structure.
2. **Its arming mechanism has already flown fault-free** — V103 armed `cal(0xC649B)` with Honda's own
   (un-recentered) coefficients for 647.8 s with no faults. Re-centering is a coefficient edit on
   infrastructure whose safety-critical parts (the gate, the state read/write, the clamp) are proven
   on-car. Cancellation's cave infrastructure has flown nowhere.
3. **No physical-constant calibration problem.** A notch's depth is set by its own `Q`, chosen by design —
   it needs no estimate of `k/J_c`. Cancellation's `b0` needs exactly that, and §4 shows I cannot supply
   it with confidence from available evidence.
4. **It addresses every excitation source, not just LKAS-injected ones.** The 6-9 Hz mode is a mechanical
   resonance on the wheel/torsion-bar; per this kit's own record it is present — smaller, but present — in
   *manual* steering too, and gripping the wheel (not disengaging LKAS) is what kills it. That is a
   description of an **underdamped structural mode any torque impulse can ring**, not a description of
   an LKAS-specific artifact. A notch or a damping increase removes loop gain **at the mode**, for every
   excitation path (driver hand movement, a road impulse through the column, LKAS). Cancellation only
   removes the **LKAS-attributable** component and leaves the loop exactly as lightly damped for
   everything else.

**What cancellation buys that the notch does not — and how much that is actually worth:**
Cancellation is source-selective: a notch suppresses *all* content at 7.79 Hz in this lane, including any
genuine driver torque that happens to land there (e.g., a driver actively counter-steering during a
ratchet episode, which by definition produces torque in-band). Cancellation, if correctly tuned, would
leave that driver content untouched.

**How much driver content is actually there?** Human neuromuscular bandwidth for voluntary/reflexive
steering-wheel torque is widely characterized in the low single-digit Hz (roughly 2-5 Hz) — well below
7.79 Hz. Combined with the observation above (the mode is a structural resonance excitable by *any*
torque, not a carrier of driver intent at that specific frequency), the honest answer is: **almost none.**
The 7.79 Hz content on the bar during a ratchet episode is overwhelmingly the ringing wheel-inertia mode
itself, not encoded driver steering commands. **[BELIEF — this is reasoned from general
neuromuscular-bandwidth literature and this kit's own manual-steering-still-shows-the-ratchet finding, not
from an on-car coherence measurement between driver torque and a genuinely LKAS-isolated component during
an active ratchet episode, which has not been run.]**

**⇒ If that belief holds, the notch's collateral cost is close to free, and cancellation's central
advantage over it is worth little in practice** — while cancellation's costs (a new cave, an uncalibrated
physical gain, a new resonant structure with its own summing junction that the notch does not need) are
real and, per this kit's own bricking history, the more dangerous class of change. **This is the "almost
none" case the assignment asked me to call plainly if that is the honest answer, and it is.**

**Ranking against the other shapes named in "ALSO CONSIDER":**

| design | addresses all excitation sources? | needs a new cave/RAM? | needs `k/J_c` calibration? | failure mode of a tuning error |
|---|---|---|---|---|
| **1. Notch (re-centered Honda biquad)** | yes | no | no | wrong depth/width, not a new loop |
| **2. Active damping (`-K·φ'`, `φ'`=torsion-bar rate)** | yes | yes, but smaller (no resonant states — a 1st-difference, not a biquad) | no — sign matters, magnitude is forgiving | wrong `K` under- or over-damps; wrong-signed `K` is the only bad case, and it is a single sign bit to get right |
| **3. Cancellation (this design)** | no — LKAS-attributable component only | yes, full 2-pole resonant cave | yes, exactly the unmeasured `k/J_c` | frequency mistuning degrades toward ineffective (§4), but the design itself is a new resonant summing junction — structurally V48B's risk class |
| **4. Gain-scheduling the assist slope near the operating point** | yes (broadband, not surgical) | no — cal-only | no | lowest build risk, but blunts assist feel across the whole torque range, not just at 7.79 Hz |
| **5. Phase-lead alone** | partially — shifts phase margin but does not reduce peak gain at ωn | yes | not directly, but its gain/corner still need fitting to something | least anchored to a measured quantity of the four cave-requiring options; ranked last on that basis |

**Recommendation: build and fly the notch first** (a separate, parallel effort's task). Use its own
measured collateral cost — specifically, whether a driver's active correction *during* a ratchet episode
is measurably deadened by the notch — as the gate on whether cancellation (this design) or active damping
(#2 above, which shares the "addresses all excitation sources" property with the notch while remaining
source-agnostic rather than needing an unmeasured physical constant) is worth building next. **This design
is complete and buildable as specified; it is not the recommended next cut.**

---

## 9. WHAT I COULD NOT RESOLVE

1. **`b0`'s absolute value.** Needs either a measured `k/J_c` (a bench measurement, per the existing
   record's own flagged open item) or an empirical dose ladder anchored to the `b0=0` telemetry flight.
   Not resolvable from available evidence — see §4.
2. **`FUN_0002214a`'s actual call order.** I inferred `FUN_000352b4` → `FUN_0003aa2c` → `FUN_00042af8`
   from data-flow necessity and the shadow-lockstep same-tick-freshness pattern, not from decompiling
   `FUN_0002214a`'s body directly. Needed to fully close the causality argument in §0.6/§1.
3. **How much of the total self-interference `gp-0x6b86`'s lane represents**, versus boost
   (`FUN_00034a72`), damping (`FUN_00034350`), and the residual/D-term lane (`FUN_0003a382`), each of
   which independently reads raw `gp-0x4f60` and is untouched by this design. Would need a per-lane
   contribution census on real engaged telemetry, similar in kind to the existing "reachability budget"
   analyses elsewhere in this kit's record, to know whether a single-lane fix is a meaningful fraction of
   the whole or a small one.
4. **Whether genuine driver torque exists at 6-9 Hz during an active ratchet episode**, specifically.
   §8's "almost none" is reasoned from general neuromuscular-bandwidth literature plus this kit's
   manual-steering-still-shows-the-ratchet finding, not from an on-car coherence measurement isolating
   driver-sourced from LKAS-sourced content in-band during a live episode. That measurement — driver
   torque vs. a synchronized `Ĥ_out` telemetry stream, coherence at 6-9 Hz, during matched manual and
   engaged ratchet episodes — is the direct way to close this, and it does not need this cave to be armed
   with nonzero `b0` to run (the `b0=0` telemetry-only flight already collects half of what it needs).
5. **3 of the 5 GATE-1 methods** (register-indirect access, the 6-byte disp23 form, an LE32-literal-table
   scan) for `gp-0x3814`/`gp-0x3818` were not independently re-run by me this session; I relied on 2 fresh
   methods plus a prior multi-method agent-memory record. A dedicated re-sweep, or the mandatory pre-flash
   probe build, should close this before any byte is written to these cells.
6. **12 bytes of free flash cal space** for `a1`/`a2`/`b0` — not located this session. A standard cal-region
   survey (or falling back to code immediates, at the cost of losing in-place dose-ladder retunability)
   closes this.

---

## Evidence log — methods used this session

`list_open_programs`/`get_current_program_info` (confirmed `code.bin`, stock, is the active target) ·
`decompile_function` on `0x352b4` and `0x3aa2c` (fresh, this session) · `get_function_callers` on
`0x352b4`, `0x3aa2c`, `0x42af8` · `search_instructions` operand-pattern scans on `0x3814`, `0x3818`,
`0x4f60`, `0x6b98`, `0x6b94`, `0x6b30` (all against the full 183,569-instruction analysed corpus, several
explicitly `truncated:true` — genuinely more hits exist than shown, consistent with "many readers" claims
throughout) · `get_assembly_context` on the biquad state read/write sites and the injection boundary ·
independent Python (not hand) computation of pole placement, coefficients, IEEE754 encodings, frequency
response, and mistuning sensitivity, run this session via `/c/Users/dudei/anaconda3/envs/bin_decompile/python`.
`get_xrefs_to` was attempted on gp-relative absolute addresses and correctly failed (address space
mismatch) — consistent with, and independently reproducing, this kit's documented gp-relative xref
blind spot; `search_instructions` was used instead throughout, per policy.

Cross-referenced against: `docs/research/FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md` (2026-08-06, prior
verdict on this exact question — NO-GO for a 7.79 Hz-targeted cave; this design was produced independently
then checked against it, not derived from it, and the two converge), `docs/STATE.md` (current head),
`docs/handoffs/2026-08/HANDOFF-2026-08-20-v103-f0-is-the-endpoint.md`, and this agent's own persistent memory
(`reference_accord_dead_biquad_fun352b4_pole_characterized_and_reversal_counter_arm.md`,
`reference_accord_biquad_is_a_notch_v103_armed_and_recentering_priced_short.md`).
