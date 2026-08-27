# V97 CANDIDATE CELL LEDGER — `fw-levers`, 2026-08-12

Scope: calibration cells that can shape the **engaged, low-speed, hands-on** torque path, against the
operator's crux (ringing in driver torque + wiggle in steering angle on return to centre, engaged only).

All structural work done in GhidraMCP on `code.bin` (2086 functions). All corpus work in Python over the
**89 non-stock plain images** on disk. `gp = 0xFEDF8000`, `tp = 0xBF000`.

---

## 0. THE DECISIVE STRUCTURAL RESULT — `FUN_00038148`'s lane↔weight map

Fresh `decompile_function(0x38148)`. **No prior kit document states which lane each weight multiplies.**
`studies/ledger/ledger_v94_cells.py` labels them only by index ("lane weight [0]"…"[5]"). The mapping is load-bearing
and it overturns two standing conclusions.

| weight cal | multiplies lane | zero-reject gate | lane identity (source) | virgin? |
|---|---|---|---|---|
| `0xC63A0` w[0] | `gp-0x6bd0` | `(x+0x800) < 0x1001` → **±2048** | seed/damper-presence lane — **measured `\|x\|<64` in 87,940/87,940 frames** | 7/89 moved |
| `0xC63A2` w[1] | `gp-0x6bbe` | `(x+0x800) < 0x1001` → **±2048** | **VISCOUS + DC pedestal**, ≈90 ct/(rad/s), phase ~0° | **VIRGIN** |
| `0xC63A4` w[2] | `gp-0x6b46` | `(x+0x400) < 0x801` → **±1024** | **unidentified** | **VIRGIN** |
| `0xC63A6` w[3] | `gp-0x6b26` | `(x+0x400) < 0x801` → **±1024** | **INERTIA** term (`−K·α`) | **VIRGIN** |
| `0xC63A8` w[4] | `gp-0x6b4e` | `(x+0x2800) < 0x5001` → **±10240** | **PROVABLY ≡ 0 — dead lane** | **VIRGIN** |
| `0xC63AA` w[5] | `gp-0x6b4c` | `(x+0x2800) < 0x5001` → **±10240** | the LKAS command lane | **VIRGIN** |

Exact arithmetic per lane, mirroring the decompile:

```python
# FUN_00038148, all six lanes share this form.  V850 is LE; >> is an integer shift.
def lane(x, w, halfwidth):          # halfwidth = 1024 / 2048 / 10240
    gate = 1 if (x + halfwidth) < (2*halfwidth + 1) else 0   # ZERO-REJECT, not a clamp
    return (x * gate * w) >> 10                              # w is Q10; stock w = 1024 => unity

sum6   = sum(lane(...) for the six lanes)
target = ((sum6 * polarity(gp-0x6752) * 2639) >> 10) * 16    # 0xC6468 = 2639
gp-0x374c += ((target - gp-0x374c) * 102) >> 10              # 0xC63AC = 102, IIR fc ~16 Hz @1 kHz
iVar6  = gp-0x6bfe + gated(gp-0x6bfa, ±20000) - (gp-0x374c >> 4)
gp-0x6b70 = sign(iVar6) * RAM_LERP(|iVar6| * 1024 >> 10)     # clamped ±8192 (0xC6200)
```

🛑 **The gate is a ZERO-REJECT window, not a clamp.** Outside ±halfwidth the multiplier evaluates to
**0** and the lane vanishes entirely. This matters for GATE 2 and it refutes "structurally always open"
(§2 below).

⭐ **`gp-0x6b70` is this function's return value** (`*(short *)(gp - 0x6b70) = (short)iVar9`). The
session's on-car measurement says `gp-0x6b70` carries the crux at **coherence 0.95–0.97**. So the crux is
measured *in Path 2's own output*, and these six weights are the only cal-only levers directly on it.
That is the strongest available argument that this family is the right neighbourhood.

---

## 1. VIRGINITY CENSUS (EVIDENCE — `sessions/v97/ledger_v97_virginity.py`, 89 images)

**Five of the six lane weights are VIRGIN across the entire corpus.** Only `0xC63A0` was ever moved.

`0xC63A0` exact provenance (filenames, not tags):

| value | images |
|---|---|
| 2048 | `_v72`, `_v72_SUPERSEDED_plateauonly`, `_v73`, `_v74_engagedcols…`, `_v75_CY0.566-EX1.200_magprobe`, `_v75_CY0.566_magprobe`, **`_v76_gate_fb_arm5244_gateprobe`**, `_v81_C407E.511-FRICTION.STOCK` |
| 1024 | all other 83, including **V96** — frozen at stock since V83a |

⚠ **Correction to `docs/STATE.md` §A5 / the V97 brief**, which lists the flights as "V72, V73, V76g, V81":
**V74 and V75 also carried 2048** (three images between them). V76g is correct; `_v76_v38base_relu_damper`
is *not*. That matters because **V74/V75 are the builds that hard-faulted on `0xC407E`** — so part of the
"measured INERT" evidence rests on drives aborted for an unrelated reason.

---

## 2. ITEM (a) — THE STANDING V97 CANDIDATE, CLAUSE BY CLAUSE

`docs/STATE.md` §A5 declares `gp-0x6b4c`/`gp-0x6b4e` to be V97. **Half of it is a dead lane.**

| clause | verdict |
|---|---|
| "±10240 each" | ✅ **CONFIRMED** — `(x+0x2800U) < 0x5001` on both, in both `FUN_00038148` and `FUN_0003aa2c` |
| "5× and 10× the other two lanes" | ✅ **CONFIRMED** — 10240/2048 = 5× (`6bd0`,`6bbe`); 10240/1024 = 10× (`6b26`,`6b46`) |
| "`gp-0x6b4c` is also a direct unity-weight aggregator summand (`0x3AA3E`), reaches the motor by both paths" | ✅ **CONFIRMED** — `FUN_0003aa2c`: `iVar19 = gp-0x6b4c * gate(±10240)`, no cal multiply, no `>>10`. It is the **one term present in BOTH arms** of the `gp-0x67ac` branch ⇒ unconditionally live in Path 1 |
| "disjoint partition sums of the same 11-slot array `gp-0x62f8[]`, split by mode bytes at `0xC4124`" | 🛑 **REFUTED AS WRITTEN.** The array is **`gp-0x62c8`**, not `gp-0x62f8`. And they are not two partitions of one live array: `gp-0x6b4e` ← `FUN_00042ac6` ← `FUN_00026c80`'s accumulator `gp-0x3d8c` ← `gp-0x62c8[0..10]`, which is **identically zero** |
| "Both gates structurally always open, so the V64-class null is excluded by arithmetic" | 🛑🛑 **REFUTED, and inverted for `gp-0x6b4e`.** The gate is a zero-reject window that kills the lane when `\|x\|>10240` — "always open" is unproven absent an upstream clamp. For `gp-0x6b4e` the V64-class null is not merely possible, it is **CERTAIN**: the lane is identically 0, so `0 × 0xC63A8 = 0` for any weight |

**`gp-0x6b4e ≡ 0` — the proof (EVIDENCE, my own `fw-return` trace, re-confirmed this session).**
`gp-0x62c8[lane]` is written only inside `FUN_00026c80`'s role-dispatch switch, selected by
`tp+0x5124[lane]` = `0xC4124`. Fresh `read_memory` of `0xC4120-0xC4140` this session:
`01 01 01 00 | 00 00 05 00 05 05 00 00 00 05 00 | 01 …` ⇒ roles = **`[0,0,5,0,5,5,0,0,0,5,0]`** — the
third independent census to return exactly this. **Role 7 is the only branch that writes a non-zero
value, and role 7 appears nowhere.** Roles 0/1/2/3/4/6 execute `st.h r0,0x0[r28]` (explicit zero); role 5
never writes the cell. Boot `.data` source `0x86DE8` reads all-zero. ⇒ `gp-0x3d8c ≡ 0 ⇒ gp-0x6b4e ≡ 0`.

**Is it the right lever for the return-to-centre crux? — NO, and this is the instrument/mechanism split
you asked for.**
`gp-0x6b4c` is a genuinely excellent **instrument**: unconditionally live, widest gate in the function,
reaches the motor by two independent paths. But the crux was measured to be **NOT command-magnitude
dependent and to survive a full command sign reversal.** `gp-0x6b4c` *is* the LKAS command lane. Scaling
`0xC63AA` scales exactly the variable that was measured not to matter. ⇒ **instrument, not mechanism.**

---

## 3. ITEM (b) — `0xC63A6`, AND THE `0xC63A0` CONTRADICTION: **RECONCILED, NOT UNRECONCILED**

The brief asks why an inversion boundary claimed at `0xC63A0` 1024→2048 produced no qualitative on-car
change. The lane map answers it.

1. `0xC63A0` weights **`gp-0x6bd0`** — *not* `gp-0x6b26`. They are different signals with different gates.
2. `gp-0x6bd0` was **measured essentially zero on-car**: V72's damper-presence probe `|gp-0x6bd0| >= 64`
   read **0 / 87,940 frames**, including 0 / 34,275 above 35 km/h — and **V72 is the very build that
   carried `0xC63A0 = 2048`.**
3. ⇒ The doubling was applied to a signal measured at ~0. `0 × 2048 >> 10 = 0`. **INERT on-car is exactly
   what the arithmetic predicts.**

**⇒ The `0xC63A0` flights are a V64-class null — a null on the LANE, not on the mechanism.** They tested
nothing. The contradiction dissolves: INERT is *consistent* with the inversion hypothesis and also with
its negation, because the experiment never ran.

🛑 **Consequence — a correction to my own prior memory.**
`reference_accord_c63a6_gate_trace_forward_vs_closed_loop_sign_split` issued NO-GO on `0xC63A6` and leaned
on `0xC63A0` as "the structurally identical sibling" whose swept estimate "crosses an inversion boundary".
**That import is invalid.** The two weights are structurally identical in *arithmetic form* only; their
*signals* differ, and the sibling's evidence is void because its lane was dead. The precedent should be
struck.

**But `0xC63A6` does NOT become GO.** The reason for NO-GO changes, it does not disappear:
- Q1/Q5 remain **CLOSED clean** — sole reader `ld.hu 0x73a6,tp,r15 @0x381ca`, flat non-mode-indexed
  scalar, zero writers (three methods; `get_xrefs_to` returned a false zero — the tp-relative blind spot).
- The open-loop sign is analytically determinate (**`+sign(gp-0x6b26)`**, reinforcing) under two stated
  assumptions.
- The **closed-loop** sign still depends on two never-measured quantities: `L` (`FUN_0003b8f6`'s float EMA
  cascade, 8 coefficients at `tp+0x50d4/0x50d8/0x504c/0x5050/0x50bc/0x50d0/0x50d2/0x50d6`, never byte-read
  by any session) and `f'` (the RAM LERP's local slope; `FUN_000389ec` has resisted a single-pass
  decompile in **three** independent sessions now). **V96's attempt to measure the slope FAILED** — its
  regressor code M is pinned at 0.

Previously the sign was "probably inverting, per precedent". It is now **simply unknown**. That is a
worse epistemic position for shipping, not a better one.

---

## 4. ITEM (c) — `0xC64DE`: **IDENTIFIED. It is a BYTE; "25627" is a type error.**

The longest-carried unmeasured cell, non-stock on **all 89 images** (present even in `_vfourframe2`).

**It is not a halfword.** Stock `0xC64DE..DF` = `11 64`; V96 = `1B 64`. Only the low byte moved:
**0x11 = 17 → 0x1B = 27.** The high byte `0x64` = 100 never moved and is a *separate* cal. Three methods:
- Ghidra decompile renders it verbatim as **`*(byte *)(unaff_tp + 0x74de)`**, and loads `tp+0x74df`
  independently at another site ⇒ two distinct byte cals.
- Raw LE scan: **16** `ld.bu` sites resolve to `0xC64DE`, **2** to `0xC64DF`. This is the documented
  `ld.bu` parity trap — `hw2 = 0x74df` in *both* cases; the real disp bit 0 is in **hw1 bit 5**
  (opfield `0x3C` → `0xC64DE`, `0x3D` → `0xC64DF`). A scan keying on hw2 alone merges the two cells.
- `builds/v18_v49/build_v18_tva.py` already wrote "(byte)" in its comment — the halfword framing entered later, via the
  ledger's `MATRIX_SCALARS` entry `(0xC64DE, 2, False, …)`, which is simply the wrong width.

**What it is (and the record is incomplete, not merely "disputed").**
`memory/reference/firmware/reference_accord_eme_lever_semantics.md` calls it "the count ceiling of the re-engage/debounce SM
… increments by 1/cycle until it hits the ceiling". The increment half is right. **What the record misses
is what happens AT the ceiling** — `FUN_00028ea6` (`m_steer_torque_arbitration`), decompile lines 676-693:

```c
bVar6  = *(byte  *)(tp + 0x74de);                 // N = 17 stock / 27 ours
bVar22 = *(byte  *)(gp - 0x6756);                 // counter
if (bVar22 < bVar6) {
    *(byte  *)(gp - 0x6756) = bVar22 + 1;
    iVar28  =  (int)*(short *)(gp - 0x6b2c);      // output = +A
} else {
    cVar29 = 1;
    if (*(ushort *)(tp + 0x728a) <= (ushort)(*(byte *)(tp + 0x74de) + sVar27))
        cVar29 = (char)((uint)*(byte *)(tp + 0x74de) >> 1) + 1;   // re-arm at (N>>1)+1
    *(byte  *)(gp - 0x3d36) = 2;                  // state 1 -> 2
    *(char  *)(gp - 0x6756) = cVar29;             // counter RE-ARMS (does not latch)
    iVar28  = (int)-*(short *)(gp - 0x6b2c);      // output = -A
    *(short *)(gp - 0x6b2c) = -*(short *)(gp - 0x6b2c);   // AMPLITUDE NEGATED
}
```

`gp-0x6b2c` is **sign-flipped** each time the counter reaches `N`, and the counter **re-arms** rather than
latching. That is a **relaxation oscillator / square-wave dither**, not a one-shot ramp. `N` is its
**half-period in ticks**. At 1 kHz:

| | N | half-period | frequency |
|---|---|---|---|
| stock | 17 | 17 ms | **29.4 Hz** |
| every build since V18 | 27 | 27 ms | **18.5 Hz** |

**Liveness — BELIEF that it is dead; the null is NOT yet clean.**
The branch above sits under `if (*(char *)(gp - 0x6809) == 1)`, and
`memory/misc/eps-deliver-cut-gp6809-broken.md` establishes `gp-0x6809` has **zero writers — dead code** — and
explicitly calls it "a dead gate protecting a permanently-zero term (`gp-0x6b2c`)". If that holds the
oscillator never runs and `0xC64DE` is inert, which would *explain* 85 builds of no measurable effect.

🛑 **But 8 of the 16 read sites — `0x2B0AA, 0x2B17E, 0x2B192, 0x2B1A4, 0x2B1C4, 0x2B1D6, 0x2B1DE,
0x2B2BE` — lie OUTSIDE `FUN_00028ea6`** (body `0x28EA6`–`0x2A30D`). `get_function_by_address(0x2B0AA)`
returns **"No function found"**: Ghidra has never analyzed that region, so `search_instructions` is
structurally blind to it and every prior census that said "read 8×" counted only the arbitration copy.
It **is** code — `read_memory(0x2B0AA)` = `85 7f df 74` = `ld.bu 0x74de[tp], r15`, inside a dense
instruction stream. **Those 8 sites are unadjudicated by any session.** Until they are decompiled,
"`0xC64DE` is dead" is a **tool zero, not a verified zero.**

---

## 5. GATE 1 / GATE 2

**GATE 1 (RAM ownership) is VACUOUS for every candidate here** — all are flash calibration cells, read-only
at runtime, claiming no RAM. GATE 1 binds only if V97 adds a cave or probe; if it does, the existing
`gp-0x6b70` probe spec already carries a GATE-1 analysis. Cleared: `0xC63A2`, `0xC63A4`, `0xC63A6`,
`0xC63A8`, `0xC63AA`, `0xC64DE`.

**GATE 2 (closed-loop stability, magnitude AND phase) — I CANNOT CLEAR ANY OF THEM, and I will not pretend
otherwise.** All six weights sit in the *same* loop and are blocked on the *same* two unmeasured
quantities (`L` and `f'`, §3). Path 2 is a genuine 1 kHz closed digital loop: `gp-0x6bfe` ←
`FUN_0003bc20` ← `gp-0x6bfc` ← `FUN_0003b8f6`, whose first input is `gp-0x6b98[n-1]` — the aggregator's
own previous-cycle output.

What I *can* certify:
- **Magnitude / overflow: SAFE.** The ±1024/±2048/±10240 gates test the **RAW pre-weight** value, so
  raising a weight cannot push its own gate into rejection. `gp-0x6b70` clamps ±8192 (`0xC6200`).
- **The linear sub-path's phase, exactly** (`a = 102/1024`, `fs = 1 kHz`, discrete one-pole):
  `|H|` = 0.94 / 0.91 / 0.88 and phase = **−18.7° / −23.6° / −26.8°** at 6 / 7.79 / 9 Hz.
  This describes the IIR alone and does **not** resolve the loop-gain crossing.

---

## 6. RANKED CANDIDATES, with "what would make this the wrong lever"

🛑 **A lever whose SIGN is unresolved is not a lever.** By that rule — which is the rule that should have
stopped V94 — **none of 1-3 below is shippable today.** They are ranked for what to *measure*, not to fly.

| # | cell | lane | why it fits the crux | what would make it WRONG |
|---|---|---|---|---|
| 1 | **`0xC63A2`** | `gp-0x6bbe` — **VISCOUS**, ≈90 ct/(rad/s), phase ~0° | Viscous = dissipative. Raising its weight is the only cal-only way to add **damping** directly into the signal measured to carry the ringing. Virgin. Signal measured LIVE (p50 73.6 ct, `P(<0)` 0.887 engaged vs 0.499 manual) | It also carries a **DC pedestal** — raising the weight raises a static engaged bias as well as the damping, and the pedestal is the larger part at low rate. If the closed-loop sign inverts, this ADDS anti-damping at 7.8 Hz |
| 2 | **`0xC63A6`** | `gp-0x6b26` — **INERTIA** (`−K·α`) | Raising apparent inertia lowers a torsion-bar resonance and raises its Q; *lowering* it should do the reverse. Second, independent lever on the signal V93/V94 tried to move via `0xCBE74` — which was **measured INERT**, so the lane itself is unfalsified | The kit already pushed inertia and got a null then an abort. Same sign risk. And `gp-0x6b26` is upstream-clamped to ±511 by `0xC407E`, so its authority is small next to the ±10240 lanes |
| 3 | `0xC63A4` | `gp-0x6b46` — **unidentified** | Virgin, ±1024 gate, same neighbourhood | **Unknown identity.** Cannot be ranked or gated until traced. This is the cheapest open item on the board |
| 4 | `0xC63AA` | `gp-0x6b4c` — LKAS command | Widest gate; unconditionally live; reaches motor by two paths | The crux is **command-magnitude independent and survives a command sign reversal**. This scales exactly the variable measured not to matter ⇒ **instrument, not mechanism** |
| — | `0xC63A0` | `gp-0x6bd0` | — | 🛑 **NON-CANDIDATE.** Lane measured `\|x\|<64` in 87,940/87,940 frames |
| — | `0xC63A8` | `gp-0x6b4e` | — | 🛑 **NON-CANDIDATE.** Lane **provably ≡ 0**. Any edit is a guaranteed V64-class null |
| — | `0xC64DE` | oscillator half-period | Would set an 18.5 Hz square-wave dither if live | Almost certainly gated dead by `gp-0x6809`. **Do not fly it as a lever** — fly it only if the 8 unanalyzed sites turn out live |

### Recommendation
**V97 should be an INSTRUMENT, not a lever.** Every candidate on the engaged low-speed torque path is
blocked on the *same* two quantities, so measuring them once unblocks the whole family rather than one
cell. Two routes, either of which closes GATE 2 for all six weights:

1. **Fly the `gp-0x6b70` probe** already specified in
   `reference_accord_gp6b70_probe_spec_path_separation_and_gate1` — and note `gp-0x6b70` is precisely the
   cell the on-car data already shows carries the crux at coherence 0.95–0.97, so the probe is aimed at a
   confirmed-hot signal.
2. **Or close it analytically without a flight**: byte-read `FUN_0003b8f6`'s 8 float coefficients
   (`tp+0x50d4`, `0x50d8`, `0x504c`, `0x5050`, `0x50bc`, `0x50d0`, `0x50d2`, `0x50d6` — ⚠ `tp+0x5000` =
   `0xC4000`, the model-coeff block, **not** `0xC5000`) and give `FUN_000389ec` a dedicated session.

---

# ADDENDUM — RE-RANKED ON PHASE MARGIN **AND** RETURN SPEED

Team-lead's constraint: the operator's crux has two clauses that pull opposite ways — the engaged return
must be (1) as SMOOTH as manual *and* (2) FASTER than manual. A **PURE DISSIPATION** lever buys 1 and
costs 2. Only a **PURE LEAD / LAG-REMOVAL** lever buys both. 🛑 **Unknown sign = DISQUALIFIED outright.**

Under that rule my previous top three are **disqualified, not demoted**: `0xC63A2`, `0xC63A6`, `0xC63A4`
are all GAIN-class levers whose closed-loop sign rests on the unmeasured `L` and `f'`. That is the V94
failure mode exactly.

## THE SURVIVOR: `0xC63AC` = 102 — the Path-2 accumulator pole

`gp-0x374c += ((target - gp-0x374c) * A) >> 10`, `A = 0xC63AC`. Priced in
`sessions/v97/ledger_v97_poles.py`, mirroring the integer arithmetic.

**It is a POLE, not a GAIN — the decisive property.** DC gain = `a/(1-(1-a))` = **1.000000 at every
value** (verified numerically at A = 102/205/410). Moving it cannot change how hard the car pulls; it
changes only *when*.

| A | α | −3 dB corner | phase @6/7.79/9 Hz | phase @0.5/1/2 Hz | step to 90 % |
|---|---|---|---|---|---|
| **102 (stock, VIRGIN)** | 0.0996 | 16.71 Hz | **−18.7 / −23.6 / −26.7°** | −1.6 / −3.3 / −6.5° | 21.9 ms |
| 154 | 0.1504 | 26.00 Hz | −12.0 / −15.4 / −17.6° | −1.0 / −2.0 / −4.1° | 14.1 ms |
| **205** | 0.2002 | 35.70 Hz | **−8.5 / −11.0 / −12.6°** | −0.7 / −1.4 / −2.9° | **10.3 ms (2.13× faster)** |
| 256 | 0.2500 | 46.11 Hz | −6.4 / −8.3 / −9.6° | −0.5 / −1.1 / −2.2° | 8.0 ms |

**102 → 205 recovers +12.6° of phase margin at 7.79 Hz AND returns 2.13× faster.** Both clauses.

⊕ **A nonlinearity a linear analysis misses.** `>>` on V850 is an *arithmetic* shift (floors toward −∞),
so a POSITIVE error below `ceil(1024/A)` floors to 0 and the accumulator **stalls**, while a NEGATIVE
error of the same size still creeps at −1. The filter is **asymmetric at small error** — a rectifying
stiction, plausibly relevant to a micro-regime ratchet. Stock stalls up to **11 counts**; A=205 → 5;
A=410 → 3. Raising A shrinks it.

**Blast radius — the smallest of any candidate.** `search_instructions(operand="73ac")` returns
**exactly one** real reference — `0x00038202 ld.hu 0x73ac, tp, r13` in `FUN_00038148` — with the other
five hits excluded as `bne`/`jr` branch-target coincidences. A whole-image raw LE scan (both parities)
found 5 hits total: that one reader, two in a stride-4 **data table** at `0xBD682`/`0xBE9C2`
(`40 3f d6 9e | 40 3f ac 73 | 40 3f 64 48` — `3f40` is a constant field), and two mid-instruction byte
coincidences at `0x64642`/`0x6E73E` inside functions Ghidra *has* analysed and where
`search_instructions` reports no such operand. **Two-method agreement: 1 reader, 0 writers.** It touches
Path 2's accumulator only — not Path 1, not the PID, not the aggregator.

🛑 **THE COST, stated plainly — this is NOT a free lever.** Raising α widens the passband, so Path 2
transmits *more* high frequency:

| | 7.79 Hz | 21 Hz | 28 Hz | 42 Hz |
|---|---|---|---|---|
| A=205 vs stock | 1.08× | **1.38×** | **1.53×** | 1.75× |

⚠ **This collides with a MEASURED win.** V62 fixed the grinding by taking 18–22 Hz down 8–42×, the kit's
first measured fix. A=205 puts 1.38× back at 21 Hz. **Raising `0xC63AC` may partially undo V62.** That is
the single strongest argument against this lever and it should be priced before flying, not after.

**On the "must-not-move list" — and why that is weaker than it sounds.** `builds/v80_v107/build_v83a_tva.py:159` says
"`0xC63AC` = 102 is on the must-not-move list precisely because the bound above depends on it." Reading
the surrounding lines, the bound in question is V83a's **≤1.32× maximum-effect estimate for a *different*
cell (`0xC63A0`)**. It is an **analysis-comparability** freeze, not a stability veto. Worth surfacing
because "must-not-move list" reads like a safety finding and is not one.

## `0xC644A` — NON-CANDIDATE, and the brief's value is wrong

**Correction:** the brief says "V43 (1024→64)". The images say **V43 → 32**, V44 revert, **V49 → 64**,
V49p revert. Moved on 2 of 89 images.

**Stock 1024 = α = 1.000 = a pass-through with a pole at z=0 and ZERO lag. It is already at maximum —
there is no raise available.** V43 and V49 both *lowered* it, adding **55.6°** and **35.8°** of lag at
7.79 Hz respectively — the wrong direction for phase margin. So V43's null is not primarily a
band-scoping question: V43 pushed a large, wrong-way change and still measured nothing, which is
evidence about the D-path's **authority**, not its band.

## `0xC6AE6` (Kd) — known sign, but internally conflicted

**VIRGIN across all 89 images.** ⚠ It is **not a scalar** — `builds/v18_v49/build_v43_tva.py:240` documents it as a
4-entry Y row `(2048, 2048, 2048, 2048)`, currently flat, so it *acts* scalar but a change means four
cells. Class: **conflicted**, per the kit's own two records — the D-term is the *sole pumping* term at
7.79 Hz, yet D *damps* 16–35 Hz, which is why the kit already killed a Kd cut. Cutting Kd helps the
target band and hurts the band V62 fixed — **structurally the same trade as `0xC63AC`, in the opposite
direction.** `fw-loop` should price these two against one shared phase budget rather than separately.

## RE-RANKED TABLE

| # | cell | class | 7.8 Hz phase margin | 0.5–2 Hz return speed | verdict |
|---|---|---|---|---|---|
| **1** | **`0xC63AC`** 102→~205 | **PURE LEAD / LAG-REMOVAL** | **+12.6°** | **2.13× FASTER** | **only candidate that buys BOTH.** Virgin, 1 reader, 0 writers, DC gain invariant. ⚠ costs 1.38× at 21 Hz |
| 2 | `0xC6AE6` (Kd) ↓ | dissipation-removal, conflicted | helps (D pumps at 7.8 Hz) | faster | virgin, but 4 cells and it fights 16–35 Hz |
| — | `0xC63A2` | GAIN | unknown | unknown | 🛑 **DISQUALIFIED — unknown sign** |
| — | `0xC63A6` | GAIN | unknown | unknown | 🛑 **DISQUALIFIED — unknown sign** |
| — | `0xC63A4` | GAIN | unknown | unknown | 🛑 **DISQUALIFIED — unknown sign + unknown identity** |
| — | `0xC63AA` (`gp-0x6b4c`) | **AUTHORITY** | ~none | ~none | 🛑 **RETIRE for this crux** (below) |
| — | `0xC644A` | — | already optimal | — | no headroom; stock is the max |
| — | `0xC63A0`, `0xC63A8` | — | — | — | dead/near-zero lanes |

## §A5's V97 — RETIRE IT FOR TODAY'S CRUX. Plainly.

You asked me to say so plainly even though it is the declared plan. **`gp-0x6b4c`/`gp-0x6b4e` is the
wrong CLASS of lever for a ringy, slow return.** It is an **authority** lane: scaling it changes how hard
the car pulls, not the damping or the phase of the mode that rings while it pulls. Three independent
reasons, none of which depend on the others:
1. **Class mismatch.** A summand's weight is a gain. The crux is a dynamics problem.
2. **Measured dose-independence.** The ring is not command-magnitude dependent and survives a full
   command sign reversal — it is invariant to exactly the quantity this lever moves.
3. **Half of it is arithmetically dead.** `gp-0x6b4e ≡ 0`, so `0xC63A8` is unfliable.
Hold it for an authority question. It is a fine instrument; it is not this build.

⊕ **And §A5's author saw something real — it is mis-stated, not imagined.** There are **two parallel
accumulators**, `gp-0x62b0[] → gp-0x3d88 → gp-0x6b4c` (live, your row-5 citation) and
`gp-0x62c8[] → gp-0x3d8c → gp-0x6b4e` (**proven ≡ 0**). Two partition sums of **two different arrays
0x18 apart**, not one array split by mode bytes. That is the likely origin of the §A5 wording.

## LEDGER DEFECT — surfaced, not fixed, as instructed

`docs/BUILD-LINEAGE.md` carries two rows I cannot reconcile:
- **Row 5 (Ledger corrections 2026-08-05):** "`tp+0x71b2` IS load-bearing — LKAS reaches the motor via
  `gp-0x62b0[ch] → gp-0x3d88 → gp-0x6b4c`… `0xC61B2`/`0xC61B4` always in lockstep", byte-verified over
  66 images.
- **Struck-hypotheses table:** the same cells are "saturation / clamp headroom", **falsified on data and
  structure** — "no reader of any of the four cells lies inside `FUN_00042af8`… the four mixer channels
  are **base assist, not LKAS**."

One says these cells sit on the LKAS path; the other says the channels they clamp are base assist and
not LKAS. **They may be about different "four cells"** — the struck row is scoped to readers inside the
shaper `FUN_00042af8`, row 5 is about the accumulator upstream — but as written a reader cannot tell.
What would settle it: enumerate the readers of `0xC61B2`/`0xC61B4` and state, per reader, which function
and which of the two paths it clamps. I did not trace that. Corpus fact for context: both cells are
**512 stock → 1024 at V22 → 2048 at V38**, non-stock on **all 89** images, in exact lockstep — consistent
with row 5's 66-image claim and extending it to the full corpus.

### Open items I could not close
- **`gp-0x6b46`'s identity** (`0xC63A4`'s lane) — untraced. Cheapest next step: `analyze_dataflow` /
  writer search on `gp-0x6b46`.
- **The 8 `0xC64DE` sites at `0x2B0AA`–`0x2B2BE`** — need Ghidra to analyze that region first
  (`0x2A30D`–`0x2B2BE` is undefined), then decompile. Until then the "`0xC64DE` is dead" null is a tool
  zero.
- **`gp-0x6b4c`'s producer** — I confirmed it is live and unconditionally summed, but did not trace where
  it is written, so the "partition of `gp-0x62c8[]`" clause is refuted rather than replaced.
