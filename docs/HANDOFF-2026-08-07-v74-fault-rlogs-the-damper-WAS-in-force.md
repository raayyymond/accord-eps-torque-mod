# HANDOFF 2026-08-07 — The V74 bump-fault rlogs: the damper edits **WERE** in force, and the unifying variable across both hard faults is **angle-rate SLEW**, not dose.

**Session shape:** orchestrator + 7 subagents, driven by the previous session's open item #1
(*"Rlogs from the V74 bump fault"*). They arrived, and they **refute the previous handoff's
load-bearing conclusion.**

**Route: `75604b0a432fdc89_00000061--3b8f2f9278`, segments 0–12.** 75,901 frames on the `0x14A`
lattice, 760.7 s. This is the drive on which **V74** hard-faulted after the operator reflashed it
following V75's stoplight fault.

---

## 1. The fault, pinned to the frame

**t = 732.3872 s, segment 12, index 73073.** Every signature latches in **one 100 Hz transmission**:

| channel | before | after |
|---|---|---|
| **`gp-0x67fa`** (the probe's own state field) | **5** (73,073 frames) | **8** |
| `0x1AB` byte0 bit2 — the firmware's DTC-active flag | 0 | **1** |
| `0x14A` STEER_ANGLE / ANGLE_RATE / WHEEL_ANGLE | live | **all three → `0x7FFF`** |
| STEER_SENSOR_STATUS | 7 | **4** |
| bus STEER_STATUS (`0x18F` b4 7:4) | 0 | **7** |

openpilot reacts +5 ms (`steerUnavailable`, `steerTempUnavailableSilent`). Assist never returns:
**2,828 / 2,828 frames**, 28.28 s, to the end of the log. **Exactly ONE state transition in the
entire 760.7 s route.**

**The ECU stays alive**: `0x14A` holds **99.97 Hz** post-fault and the probe cave keeps executing
⇒ **an authority/motor-off latch, not a reset or a task death.** Identical in class to V75's fault.

★ **Build identity PASSES on the strong test**: `state == 0` in **0** frames and
`state ∈ {2,12,13,14,15}` in **0** frames, against a reachable set of `{1,3,4,5,6,7,8,9,10,11}`.
**The cave fired** — this is not the silent-null failure mode that wrecked V64 and V68.

---

## 2. 🛑🛑 THE HEADLINE — the FactorC/E edits **WERE** in force. The previous handoff is refuted.

The 2026-08-06 (late) handoff recorded, as **[EVIDENCE, verified two ways]**:
> *"THE FACTOR C/E EDITS WERE NOT IN FORCE WHEN V74 FAULTED. Disengaged = mode 24, and all five
> mode-24 damper records are byte-identical to stock"* ⇒ *"`k*` IS VOID."*

**The byte-level half of that is correct and still stands. The inference from it is wrong.**
"Disengaged" was taken from the operator's verbal report and silently equated with "mode 24". The
car's own telemetry says otherwise:

| fact | value | method |
|---|---|---|
| `bit7` = (`gp-0x6bd0` != 0) **at the fault frame** | **1** | direct on-car read of the damper cell |
| `bit7` continuously 1 for | **560 ms** up to and including the fault | 56 consecutive frames |
| vehicle speed at the fault | **33.29 km/h** (`vEgo`) / **33.13** (wheel speeds) | two independent channels |
| stock mode-24 FactorC `X[0]` | **2240 counts = 35.00 km/h**, `Y[0] = 0` | byte read, prior session |
| time since openpilot dropped lateral control | **2.509 s** | `latActive`, corroborated by `0x0E4` b2 b7 at 2.500 s |

The factor-table evaluator **clamps to `Y[0]` below `X[0]`**. So at 2130 counts a mode-24 record
gives FactorC = **0**, and the damper is **identically zero**. It was not zero.
⇒ **[EVIDENCE, by contradiction] the ECU was NOT evaluating the mode-24 column at the fault.**
It was still on the **engaged column**, where V74's `FactorC Y[0] = 429` makes the damper live.

### The arithmetic behind that contradiction, verified in Ghidra this session

| claim | evidence |
|---|---|
| **Below `X[0]` the evaluator hard-clamps to `Y[0]`** — no extrapolation | disasm `0x3451e/0x34520` `cmp r13,r7 ; bh 0x34528` not taken ⇒ falls through to `0x34522 ld.hu 0x0[r10]` = `Y[0]`. All five evaluators (B/C/D/E/ceiling) share the idiom (`0x3448c`, `0x345ae`, `0x3463c`, `0x346d0`) |
| **The factor chain is PURELY MULTIPLICATIVE** ⇒ `FactorC = 0` forces `gp-0x6bd0 = 0` | disasm `0x34684`–`0x3475c`: four back-to-back `mulu` + `shr 0xa` (Q10) at `0x34684/88` (×B), `0x3468a/8e` (×C), `0x34690/96` (×D), `0x34698/9c` (×E) — **zero `add`/`or` instructions in the span.** The sign flip is a conditional negate (`subr r0,r8`), the final clamp a symmetric min/max. **No additive path can rescue a non-zero output.** |
| mode 24 is byte-identical to stock; **mode 26 carries V74's three edits and nothing else** | raw reads of stock + `_v74_engagedcols_x12_plain_image.bin` via `0xC9E9C[26]→0xD77D0`, `0xC9F84[26]→0xD780C`. FactorC `Y[0]` 0→**429**, FactorE `X[0]` 60→**12**, `Y[1]` 140→**539** |

⇒ At 2130 counts: **mode 24 gives a hard 0; mode 26 gives 429.** The prediction holds exactly, and
the old conclusion is dead on this point.

⚠ **HONEST GAP — the ~2.5 s hold is established EMPIRICALLY but its ROM mechanism is NOT pinned.**
The live mode cell is **`gp+0x63fd`** (abs `0xFEDFE3FD`), read by all five factor evaluators
(`0x34470/0x34502/0x34592/0x34616/0x346b4`) and written by `FUN_00042746` from the 100 Hz task-5
dispatcher, gated on `gp-0x67fa ∈ {4,5}` — live all drive, since the state was 5. The only genuine
debounce found is **`0xC624E` = 40 → 40 ms** at 1 kHz (pending flag `gp-0x68ab`, counter snapshot
`gp-0x138c`), which with the ramp-settle requirement tops out near **150 ms — not 2.5 s.**
A deeper freeze exists and is the plausible candidate: `gp-0x6733 = −1` (a "transitioning" sentinel
written by `FUN_000527da`) **blocks the reselect from even arming** — but that function's callers
resolve to null under both `get_function_callers` and `get_xrefs_to` (register-indirect/RTOS-table
dispatch, this kit's documented blind spot), so **what drives it, and for how long, is UNRESOLVED.**
🛑 **This does not weaken the conclusion** — the conclusion follows from the arithmetic above
regardless of *why* the mode was held. But the mechanism is an open item, and the clean way to close
it is a live probe on `gp+0x63fd` across a disengage event. **Bytes alone will not get the number.**

### The negative control, replicated on two routes of the same build

`bit7` in "manual" occurs **only** inside a decaying tail after disengagement, and is **hard zero**
beyond it:

| time since disengage | route 61 (this drive) | route 5d (V74 clean) |
|---|---|---|
| 0–1 s | 28.4% | 44.9% |
| 1–2 s | 18.3% | 41.6% |
| 2–3 s | 20.4% | 12.6% |
| 3–4 s | 3.0% | 6.7% |
| **4–6 s** | **0.000%** | **0.000%** |
| **> 6 s** | **0 of 9,286** | **0 of 39,794** |

**49,080 frames of true-manual driving across two routes, with zero damper activity.** The stock
mode-24 model is *confirmed* — and the fault sits at **2.509 s**, squarely inside the tail.

⊕ **The apparent counter-example dissolves.** Route 61 has three real manual episodes and they look
like they disagree (0.00% / 61.5% / 70.3%). Ordered by time-since-disengage they agree exactly: the
episode reading **0.00%** — and it *crosses* the 35 km/h knee — had **never been engaged at all**, so
its time-since-disengage is infinite. Not a counter-example; the strongest confirmation on the route.
⚠ The 5 km/h bucket table over manual frames must **not** be used: n = 3 episodes, and
`feedback-episodes-not-windows` applies. The fault-frame fact stands alone and does not need it.

🛑 **CONSEQUENCE: `k*` is NOT void — but it is not `(0.580, 1.580]` either.** Both hard faults now
occurred **with the damper live**. V74 faulted at **k = 0.5799**, so no dose bracket derived from
"V74 flew clean" survives. V74 flew 1,012 s clean on route 5d and 732 s on route 61 before faulting
⇒ **not a threshold. A trigger.**

---

## 3. ★★★★ The unifying variable across BOTH hard faults is **angle-rate slew**

One metric, applied to both fault drives, sentinel-free:

| | \|driver torque\| peak, 100 ms pre | its percentile | **\|d(angle rate)/dt\|** | its percentile |
|---|---|---|---|---|
| **V74** (route 61) | 3,676 | 99.999 | **5,400 /s** | **route MAX, n = 1** |
| **V75** (route 5e) | 922 | **86.3** | **6,900 /s** | **route MAX, n = 1** |

**Magnitude does not unify them. Slew does** — each fault fired at its own drive's single largest
`|d(angle rate)/dt|`, n = 1 in both cases.

This **dissolves V75's "mildest of four launches" paradox**: the relevant quantity was never dose,
it was the single-cycle rate of change. And it is corroborated independently on V74:

- **The bump was ORDINARY.** IMU captured at 101.03 Hz (vertical axis is **`ax`**, 0.9884 g). There
  *is* a real bump at the fault — `ax` deviation **−1.494 m/s² at −15 ms**, rebound **+1.559 at +34 ms**
  — so the operator's "over a bump" is correct. But it ranks **#84 of 388** isolated excursions,
  the **78.6th percentile**, and the route maximum is **2.94×** larger.
- **V74 survived 8 earlier damper-live episodes above 3,000 counts** of bar torque, and **502 frames**
  at ≥3,000 counts with the damper live.

⇒ **[EVIDENCE] This is a fast-transient sensitivity in the damper chain, not a dose problem** — the
signature of an **un-debounced, single-cycle consistency latch**. The bit13 fingerprint already ruled
IN exactly two such monitors: **fid 28 (Monitor 1)** and **fid 29 (Monitor 2 / `FUN_00045a20`)**, both
descriptor `0x00003D01`. FactorE is indexed on steering **rate**, so a route-max `d(rate)/dt` drives
the largest single-cycle step `gp-0x6bd0` can take.

⚠ At the fault the rate was 20–78 counts — inside FactorE's **ramp** (`X[0..1]` = 12..400), **not** the
flat relay band. ⇒ **the V74/V75 bang-bang relay is NOT implicated in V74's fault.** Cleanly eliminated.

🛑 **SENTINEL TRAP, and I walked into it before catching it.** At the fault frame the `0x14A` angle
fields latch to `0x7FFF`. A derivative window that *touches* that frame imports a ~16,000-count spike
and inflates `|d(rate)/dt|` **~300×**. Every number above uses a strict `[:F]` prefix with an
assertion that the prefix is sentinel-free. This is the same trap that contaminated
`v75fault_{timeline,analysis,followups,oscillation}.py`.

---

## 4. `gp-0x67fa` — the state machine, confirmed on-car for the first time

The ROM model was traced **before** the telemetry was decoded, and **its prediction matched exactly**:
*"exactly one frame `5→8`, no transit through 6/7/9/10, and 8 should persist."*

**State 5 is the resting state**, in **both** arms — route 5d cross-tabulates 56,743 engaged and
44,358 manual frames all at state 5. ⇒ **the state field cannot read engagement**, and *anything*
other than 5 is abnormal by itself. State 8 never occurs in 1,011 s of clean driving (0/101,102,
three independent methods).

**States 4, 10, 11 never occurred at all** on route 61 (760 s), and route 5d's single state-4 frame is
the final `0x14A` frame at ignition-off. ⇒ V42's `0x454FE` ratchet fix, which keys on
`gp-0x67fa == 4`, is **dead on this car**; V70's bit5 (`== 10`) reading low is corroborated.

### The state-8 trap block (`FUN_00019f7c`, top of function, before dispatch)

```
if (state != 1 && FUN_000197d0(4)==1
    && (  FUN_00046ea6(0) != 0                          // bit0 of the fault aggregate
       || gp-0x685c != 0                                 // DTC latch byte, Monitor-1 chain
       || (FUN_000197d0(0x10)==1 && gp-0x3eec==1)
       || FUN_000197d0(8)==1
       || (gp-0x6b98==0 && FUN_00046ea6(2)!=0) )
    && gp-0x3ee8 == 0 )
{ gp-0x67fa = 8; gp-0x4c39 = 8; FUN_00021e46(); FUN_0001a16a(); gp-0x3ee8 = 1; }
```

⇒ **State 8 is a CONSEQUENCE, not a cause** — a fault is already latched by the time it is written.

### ★★★★ `gp-0x685c` closed — and the "debounce" for fid 28/29 is a structural NO-OP

**4 writers, 1 reader** (the trap block's leg 2), all literal `= 1`, in two functions:
`FUN_00018738` @`0x18848`/`0x1887c` (reached from `FUN_00016de6`, the **4-arg fault-report API that
Monitor 1 and Monitor 2 both use**) and `FUN_000188c0` @`0x18902`/`0x1892e` (a different 2-arg API).

**Both fid 28 and fid 29 are structurally capable of setting it.** Descriptors read fresh:
fid 28 @`0xB8054` and fid 29 @`0xB8070` are **both `013D0000` LE = `0x3D01`** — matching the record
exactly. bit0 = 1 passes the `tp-0x58c0` = 0 test and satisfies `FUN_0001611e`'s `& 0x41`.
⇒ **This closes the `[UNVERIFIED]` flag on the Monitor 1/2 memory, but it does NOT discriminate 28
from 29.** ROM statics cannot; only runtime telemetry of their accumulators can.

★★ **The trip test is `increment + gp-0x42ec[fid] + 1 < threshold`, where `threshold` is the record's
own offset+2 field — and for fid 28 AND fid 29 that field reads `0x0000`.** Any accumulator ≥ 0
already fails `< 0` ⇒ **`FUN_00018738` trips on the FIRST qualifying call for these two IDs.** The
dwell counter is a no-op for them. The only real debounce is the ~10-cycle / **0.1 s** flag
accumulator inside each monitor (`gp-0x3564` in `FUN_00042af8`; `gp-0x3550` in `FUN_00043e44`).
⇒ **A single ~0.1 s stage, not two** — which is exactly the sensitivity a route-max single-cycle
transient would exploit, and is the best structural match yet to the measured slew result in §3.

**Leg ranking against the measured conditions:** `gp-0x685c` is the **strongest** candidate.
The `gp-0x6b98 == 0` leg is the **weakest** and should be set aside — `gp-0x6b98` is a **SUM**
(`FUN_00042af8`: an additive `gp-0x6afe` term, gated only if it falls *outside* ±10240, plus the
SM-shaped LKAS demand, then governor- and ±8192-clamped). At route-max driver torque of −3676,
well inside that window, landing the sum at exactly zero would require an unusual cancellation.
**`gp-0x3ee8` confirmed [EVIDENCE, two methods]: exactly 2 accesses program-wide**, both in this
block — the `==0` guard and the `=1` latch. **Set once, never cleared anywhere in ROM.**
The assist cut is **not** merely the mask gating: `FUN_0001a16a` → `FUN_00045608(0,0,0x8000,0x8000)`
writes **slot 0 of the authority table** (`gp-0x652c`), whose only other reader is the first input to
`FUN_0004503c`, the motor-torque governor's authority-combine ⇒ **a direct authority-zero into the
governor.** None of the five OR'd legs reference LKAS engagement ⇒ **structurally able to fire in
manual**, consistent with V74's fault.

---

## 5. Path 2's re-entry — a correction that bears on V77

`FUN_0003b8f6` traced in full. **The re-entry closes through `gp-0x6bfc` alone**, via one function not
previously in the record — **`FUN_0003bc20`** (`0x3bc20`, called `0x22416`, pure identity passthrough)
→ `gp-0x6bfe` → `FUN_00038148` reads it at `0x38218` as `iVar5 = gp-0x6bfe − (iVar4 >> 4)`.

★★ **It is a SUBTRACTION — a residual/error term, not simple positive feedback.** `0xC63A0` scales
**both** operands, so **to the re-entry residual specifically its revert may be near-cosmetic**. It is
*not* cosmetic to Path 2's forward contribution `iVar4`, which is what actually delivers the damping.
⚠ The cancellation argument rests on the downstream chain having unity DC gain — **an inherited
premise, not re-verified.**

Other corrections: the **"B" input branch (`gp-0x4f60`) is DEAD CODE in every build** — its combine
coefficients `0xC4048 / 0xC404C / 0xC4050` are **all zero** in stock, V74, V77 and V77B.
`gp-0x6bf6`, `gp-0x6c00`, `gp-0x6ae0`, `gp-0x6ae2` have **zero readers anywhere** — write-only telemetry.
The re-entry is **not a bare `z⁻¹`**: the 2-pole LPF (`0xC40D4` = 573/4096) gives **−4.96 dB, −75.3°**
at 21 Hz, plus −7.6° transport = **≈ −83°**. The two operands of the subtraction sit **~27° apart** at
21 Hz and therefore **cannot cancel there.**
### What `0xC63A0` actually reaches — and a correction to the golden model's chain

| link | finding |
|---|---|
| `FUN_00037fe6` (`gp-0x6b70 → gp-0x6ad6`) | **exactly UNITY.** All 7 term weights `tp+0x74ad..0x74b3` read **1** in stock/V74/V77, and the `LERP(gp-0x69aa)` table `0xC6ABA–0xC6AD8` outputs a **constant 1024/1024 = 1.0** across its whole domain in all three. This stage does nothing to the signal. [EVIDENCE, LE byte reads] |
| **`FUN_0003a382` IS a gain-scheduled PID** — the model's original wording was right | It has a hard entry gate (`\|gp-0x6ad6\|`, `\|gp-0x4f60\| ≤ 25600`, plus `gp-0x2588`/`gp-0x2584` bit 27 and `gp-0x6ac0 < 0x32c9`); when it fails, `gp-0x6ad4 = 0` unconditionally. **But `gp-0x6ad6` is ALSO the PID's feedback term** — see the correction below. [EVIDENCE, decompile `0x3a382`, orchestrator-read] |
| ★★ **`gp-0x6ad4` is the ONLY thing this branch feeds** | It appears in `FUN_0003aa2c`'s aggregator sum and nowhere else. ⚠ Whether the gate was open at V74's fault is **not established** — what sets `gp-0x2588`/`gp-0x2584` bit 27 is unresolved, and given the 2.5 s mode lag it plausibly was **open**. |

🛑🛑 **A SUBAGENT ERROR I CAUGHT, AND IT MATTERS.** A tracer reported this round that *"`gp-0x6ad6`
is a GATE input to `FUN_0003a382`, never a DATA input ⇒ reverting `0xC63A0` changes delivered damping
by **0.00 dB**, full stop"*, and reversed its own earlier framing on that basis. **It is false.**
Reading the decompile, `gp-0x6ad6` appears **three** times, not two: the gate, its sign bit, **and
`uVar19 = (uint)*(short *)(gp - 0x6ad6)` — a data read.** `uVar19` is clamped to ±(`tp+0x7200`) into
`uVar24`; then `iVar30 = gp-0x4f60 − uVar24` forms the **error**, clamped to ±0x2800 as `iVar31`,
which drives three gain-scheduled lanes summing into `gp-0x6ad4`:

| lane | expression | state |
|---|---|---|
| **P** | `iVar14 = IIR((iVar31 × LERP_uVar20) >> 10 × 0x20, tp+0x7450)` | `gp-0x367c` |
| **I** | `iVar18 = ((LERP_uVar16 × iVar31) >> 10) + gp-0x3688` | `gp-0x3688` |
| **D** | `iVar29 = ((iVar31 − gp-0x3684) × LERP_uVar12) >> 10` | `gp-0x3684` |

⇒ **`gp-0x6ad6` IS the PID's feedback term, Path 2 DOES reach `gp-0x6ad4` proportionally, and
`0xC63A0`'s effect on the delivered command is REAL — not 0.00 dB.**
★ **This does NOT rescue V77 for the fault question.** §6's conclusion rests on an independent,
separately-verified fact — the monitors read `gp-0x6bd0` *directly*, and `0xC63A0` is downstream of
it — which I confirmed myself from `FUN_000347b8` and `FUN_00038148`. The two results are unrelated:
**`0xC63A0` moves the delivered torque, and still cannot move what the monitors see.**
⚠ The same tracer also reported the aggregator→`gp-0x6b98` gap and the dead "B" branch; those were
not re-checked by the orchestrator and should be treated as **[BELIEF]** pending verification.
| 🛑 **CORRECTION: the aggregator does NOT feed `gp-0x6b98`** | `FUN_0003aa2c`'s sum output is **`gp-0x6b94`** (+shadow `gp-0x4ce0`). `FUN_00042af8` — the governor that actually writes `gp-0x6b98` — **never references `gp-0x6b94` in its 1,424-line body**; it runs on `gp-0x6afe`/`gp-0x6b08`/`gp-0x4f64`. ⇒ **"aggregator → `gp-0x6b98`" has at least one unresolved hop.** 4 unchecked readers of `gp-0x6b94`: `FUN_00036bec`, `FUN_0004503c`, `FUN_0004595a`, `FUN_0007ff08`. **This is in the golden model and is wrong as written.** |

★ **Crucially, `0xC63A0` acts ONLY on Path 2.** Path 1 — `gp-0x6bd0` unity-weighted straight into
`FUN_0003aa2c`'s sum, confirmed unweighted and gate-only — is **untouched** by it.

**Phase, from the actual coefficients** [EVIDENCE]:

| f | re-entry (2-pole + 1-tick delay) | Path 2's own `iVar4` IIR | operand gap |
|---|---|---|---|
| 7.79 Hz | −0.87 dB, −36.06° | −0.85 dB, −23.63° | ~12° |
| 21.09 Hz | −4.96 dB, −82.84° | −4.13 dB, −47.90° | **~35°** |

⇒ the subtraction's two operands cancel best at low frequency and **worst near the resonance.**

⊕ **`gp-0x6abc` identified: `:= gp-0x4f50`** (near-identity passthrough, `FUN_00041464` @`0x41464`),
produced by the same 4-way shadow-lockstep monitor as `gp-0x6ac0`/`gp-0x6ac2`/`gp-0x6abe` — the
resolver/motor-rate family. **Its sign-flip candidate is WEAKENED**: `term1` is LPF'd at
`alpha = 408/4096 ≈ 0.0996`, so a hand-over-hand reversal produces a **filtered multi-tick transient
in `gp-0x6bfc`, not a literal single-sample step.**

---

## 6. 🛑🛑 V77 IS STRUCTURALLY INCAPABLE OF PREVENTING THIS FAULT — **orchestrator-verified in Ghidra**

**There are FOUR monitor trip surfaces feeding fid 28/29, not two, and `0xC63A0` reaches NONE of them.**

| surface | int leg (fid 28) | float leg (fid 29) | reads |
|---|---|---|---|
| **A** — damper ceiling-clamp | `FUN_00034350` top-of-function → `FUN_0004613e(0x4179,…)` | `FUN_000347b8` → `FUN_000462e6(0x417a,…)` | **`gp-0x6bd0` itself**, ±5/1024 |
| **B** — comp-envelope (NEW) | `FUN_000456a4` → `FUN_0004613e(0x3c35,…)` | `FUN_00045a20` → `FUN_000462e6(0x3a09,…)` | `gp-0x6acc` vs `gp-0x6ace` |

**I confirmed the crux myself rather than relaying it** (a "do not flash" deserves the same check as a
"flash"):

- **`FUN_000347b8`** — `fVar5 = (float)(int)*(short *)(gp - 0x6bd0) * 0.0009765625` ⇒ it reads
  **`gp-0x6bd0` directly by value** (1/1024 = Q10), tests the residual against the float constant
  `0x3ba00000` (= 5/1024), and reports via `FUN_000462e6(0x417a,…)`. Exactly the ±5/1024 corridor.
- **`FUN_00038148`** — `gp-0x6bd0` appears **exactly once**, as one of six read-only summands,
  weighted by `*(ushort *)(tp + 0x73a0)` = **`0xC63A0`**, behind a zeroing gate
  `(*(short*)(gp-0x6bd0) + 0x800) < 0x1001` (|x| ≤ 2048). **The function's only store is
  `*(short *)(gp - 0x6b70) = iVar9`. There is NO write to `gp-0x6bd0` anywhere in it.**
  (The re-entry subtraction is visible in the same decompile: `iVar5 = *(short*)(gp-0x6bfe) − (iVar4 >> 4)`.)

⇒ **[EVIDENCE] `0xC63A0` is strictly DOWNSTREAM of the cell Surface A reads. Reverting it changes not
one bit that either monitor sees.** Surface B is a fully parallel pipeline — `FUN_000456a4`'s comp term
is built only from `gp-0x6a10`/`gp-0x6ac0`/`gp-0x6abe`, with **zero references** to `gp-0x6b98`,
`gp-0x6bd0` or `gp-0x6b70`.

⇒ 🛑 **V77 is a NULL EXPERIMENT for this fault class.** It should not be flown expecting a safety
result. If flown, it will very likely fault again — and that outcome would carry **no information**,
because the lever never touched the mechanism.

★ **And the monitors' shape confirms the slew finding independently.** Neither surface computes a
derivative: both are **per-cycle STATIC consistency checks** between int and float representations of
the same quantity, computed by two independent code paths. Combined with the threshold-`0x0000`
finding (§4 — `FUN_00018738` trips on the *first* qualifying call for fid 28/29), a static
un-debounced window is **precisely** what a large single-cycle transient trips. **Two independent
lines of evidence — the on-car slew statistics and the ROM's monitor structure — converge.**

### A THIRD SURFACE was found, briefly looked like it flipped the answer - and does NOT. RESOLVED.

The **original** Monitor 1 / Monitor 2 pair (`gp-0x3564` / `gp-0x3550`) is a *third*, distinct surface,
and it does **not** compare `gp-0x6bd0` at all. It compares **`gp-0x6b98` — the merged command
itself** — against a float envelope `gp-0x6dbc` / `fVar23`, at ±5/1024:

```
fVar12 = -((float)*(short*)(gp-0x6b98) * 0.0009765625 - fVar23)
if (fVar12 outside ±5/1024): fVar12 = 32.0     // the weight-32 "torque arm" flag
```
→ Monitor 2's accumulator `gp-0x3540`/`gp-0x3550` → `FUN_000462e6(0x3f1b,…)` → **fid 29**; the same
comparison recurs one cycle later in `FUN_00042af8` (Monitor 1, `gp-0x3564`, +10/cycle, threshold 100)
→ `FUN_0004613e` @`0x43D42` → **fid 28**. `fVar23` is built from `gp-0x4f64` and corridor tables
`tp+0x71d4`/`tp+0x71d8` with **no Path-2 references**, so only the *left* side could move.

It would be a live lever **if** `0xC63A0` reached `gp-0x6b98`. **It does not.** RESOLVED:
- **`gp-0x6afe` has exactly ONE writer program-wide** - `FUN_00042ac6` @`0x42ad6`
  (`st.h r15,-0x6afe,gp`), six lines: `gp-0x6afe = (param_1 + 0x2800 > 0x5000) ? 0x7fff : param_1`
  [**orchestrator-verified by direct decompile**; it reads nothing else]. Sole caller `FUN_00026c80`
  @`0x277f6`, passing `sVar38 = clamp(iVar14, +/-0x2800)`, accumulated **entirely inside that
  function** from local stack buffers filled from mode-table constants.
- `search_instructions` scoped to `FUN_00026c80`: **989 instructions, ZERO hits** for `6ad4`, `6b94`,
  `6ad6`, `6b70`. Same scan over `FUN_00042af8` (1,769 instructions) for `uVar34`: **zero hits** -
  independently reproducing the second tracer's full decompile, which found `gp-0x6b94` absent from
  all 1,424 lines.

(+) **Real but non-decisive:** `sVar38` is *also* stored to **`gp-0x6b4e`**, one of `FUN_00038148`'s
six weighted inputs and a **sibling** of `gp-0x6bd0`. => they share a common ancestor but run in
**PARALLEL, not series** - `gp-0x6afe` bypasses `FUN_00038148` entirely, so `0xC63A0`'s multiply
(which scales only `gp-0x6bd0`'s contribution to `gp-0x6b70`) never reaches it.

=> `gp-0x6b98 = clamp(clamp(gate(gp-0x6afe) + uVar34))` - **neither term carries anything downstream
of `0x381AC`. ALL THREE SURFACES ARE BLIND; V77 is a null experiment for this fault class.**

WARNING **This answer took the tracer three attempts** (structural NO -> conditional YES -> final NO),
and the YES rested on an unverified directional premise: it cited *"Path 2 closes through
`gp-0x6b98`"*, but `FUN_0003b8f6` **reads** `gp-0x6b98` back **into** Path 2, making it an **input**,
not an output. Recorded because the *pattern* matters: **a subagent reversing its own earlier finding
reads as diligence and is easy to accept unchallenged.**

⚠ **Not exhaustive:** several further `FUN_0004613e`/`FUN_000462e6` callers (`FUN_00027b0a`,
`FUN_00027802`, `FUN_00036388`, `FUN_00036c12`, `FUN_00041464`, `FUN_000365d2`, `FUN_00036d74`,
`FUN_00041b8e`) were not traced.

---

## 6b. The original framing of the V77 question (now answered above)

**V77 = V74 + `0xC63A0` 2048→1024**, one cell, built and unflashed. `0xC63A0` is read at **`0x381AC`**,
which is **downstream** of `gp-0x6bd0`.

**Monitor 1 (fid 28) reportedly checks int/float clamp consistency on `gp-0x6bd0` ITSELF at ±5/1024.**
If it samples the cell **upstream** of that multiply, then **V77 cannot change anything Monitor 1 sees,
and is structurally incapable of preventing this fault.** Monitor 2 (fid 29) compares `gp-0x6acc` vs
`gp-0x6ace`, which are governor-side and therefore downstream — where `0xC63A0` *could* matter.

⇒ **Discriminating fid 28 from fid 29 decides whether V77 is a real lever or a null experiment.**
This was dispatched and is **unresolved at close of session.**

⚠ **What V77 does NOT do under the new evidence:** it leaves the damper live and leaves
`gp-0x6bd0`'s own trajectory untouched. If the mechanism is a single-cycle step in `gp-0x6bd0`
tripping an un-debounced corridor, V77 does not address it. **V77's own recorded weakness also
survives**: V72/V73 carried `0xC63A0` = 2048 without a manual fault — but the damper was structurally
**zero** on those builds, so the weight was inert. `0xC63A0`'s effect is **confounded with damper
liveness** across V72/V73/V74/V75 and cannot be separated by that history.

🛑🛑 **NOTHING HERE IS CLEARANCE TO FLY. V74 is on the car and has hard-faulted. Two hard faults in two
days, both with total loss of power steering. No build in this lineage has demonstrated safety.**

---

## 7. Corrections to the record

1. **`STATE.md` / `HANDOFF-2026-08-06-v74-also-faulted…`** — *"the FactorC/E edits were not in force"*
   and *"`k*` is VOID"` are **REFUTED**. The byte facts stand; the mode inference does not.
2. **The `gp-0x68ad` "field-dead" memory is wrong** — state 5 is the resting state, 96.3% / 99.999%
   of two drives. Flagged by the tracer, confirmed by telemetry.
3. **V42's `0x454FE` fix keys on a state that never occurs** on this car (0 frames at state 4 in 760 s;
   1 frame in 1,011 s, at ignition-off).
4. **`decode_v74_probe.py` still does not exist** despite being referenced by `build_v74_tva.py`.
   Route 61's decode lives in `v74fault_extract.py`, which `exec`s the builder's own `wire_byte4()`
   and verifies the decode inverts it exhaustively.
5. **`pandaStates` capture is broken** in both `v75fault_extract.py` and the r5e cache — `ps_t` is
   populated but `ps_fault`/`ps_safety`/`ps_ign` are empty (the try-block aborts on the first field
   access under this cereal schema). **No panda fault/ignition evidence exists from either cache.**
6. **Route 5d's rlogs are no longer on disk**, and its cache never captured `0x1AB` ⇒ no claim about
   the DTC-active flag on the clean drive is possible without re-downloading.

---

## 8. Open, in priority order

1. 🛑🛑 **Does Monitor 1 or Monitor 2 read anything DOWNSTREAM of `0x381AC`?** `0xC63A0` is read
   there, downstream of `gp-0x6bd0`. If **neither** monitor's compared quantities lie downstream,
   **V77 cannot change what either monitor sees and is structurally incapable of preventing this
   fault.** Dispatched; **unresolved at close of session.** This gates the flash decision.
2. ★ **THE PROBE REDESIGN — the highest-value build action.** ROM statics **cannot** discriminate
   fid 28 from fid 29 (both eligible, both descriptor `0x3D01`). Only runtime can. Add to the cave:
   **`gp-0x42ec[28]`, `gp-0x42ec[29]`** (the per-fid accumulators) and/or **`gp-0x3564`** (Monitor 1)
   and **`gp-0x3550`** (Monitor 2), or the aggregate words **`gp-0x18d0`/`gp-0x18d4`** directly.
   That would name the monitor on the *next* captured fault. 🛑 Keep `gp-0x67fa == 5` as the positive
   control — this kit has been burned three times by probes whose null was on the gate.
3. **A lever that limits `gp-0x6bd0`'s SLEW**, not its magnitude. The evidence now points squarely
   there and **no such lever has ever been proposed in this kit.** Every damper lever tried so far
   (`C_Y0`, `E_X0`, `E_X1`, `E_Y1`, `0xC63A0`) moves gain or shape, not rate of change.
4. **The mode-lag mechanism** — `gp+0x63fd`'s multi-second hold. The 40 ms debounce (`0xC624E`) does
   not explain 2.5 s; the `gp-0x6733 = −1` sentinel from `FUN_000527da` is the candidate but its
   caller is register-indirect and unresolved. **Closeable with a live probe on `gp+0x63fd` across a
   disengage — bytes alone will not get the number.**
5. **`gp-0x6abc`'s producer**, and whether its `sign()` flip (the `ratio` clamp saturates for
   `|gp-0x6abc| > 50`) injects a single-cycle step through a hand-over-hand reversal.
6. **The downstream DC gain** (`FUN_00037fe6` → `FUN_0003a382` → aggregator), byte-verified, to close
   the `0xC63A0` cancellation argument with a number rather than an inherited premise.
7. **A DTC re-read** — `19 02 FF`, bus 1. 🛑 Operator confirmation of exact payload and bus required;
   **nothing was sent this session.**

---

## 9. Artifacts

`analysis-2020accord/v74fault_extract.py` (route 61 + IMU, execs the builder's `wire_byte4()`),
`v74fault_crux.py`, `v74fault_report.py`, `v74fault_orchestrator.py` (the orchestrator's own
verification, sentinel-safe), `v74base_{state,damper,manualdamp,imuaxes,bumps,nearmiss,seg1burst}.py`.
Cache: `_cache_r61/` (`r61.npz`, 71 arrays incl. `state`, `dtc_active`, raw BE angle words, and IMU
under both schemas).

⚠ **Environment:** anaconda **base** has a broken numpy and no `capnp`. Everything ran under
`C:\Users\dudei\anaconda3\envs\bin_decompile\python.exe`.
