# TRACE 2026-08-11 — hunting the return-to-centre gate (fw-return)

Task: confirm/refute the operator's hypothesis that active-return is suppressed/gated by LKAS command
magnitude, even when LKAS is aligned with the return direction. GhidraMCP only, `gp=0xFEDF8000`,
`tp=0xBF000`, `code.bin` stock unless noted.

## 1. Entry point & goal

Identify the return-to-centre producer, trace every downstream consumer to the motor command, and find
any comparison, gate, or shared limiter that ties its effect to LKAS command magnitude or engagement
state — per team-lead's brief in the 2026-08-11 "Hunt the return-to-centre gate" task.

## 2. Path (ordered hops, addresses computed in code, LE bytes)

```
FUN_000360fe (0x360fe)     5-pt LERP(gp-0x6bda) x gp-0x6abc x cal(0xC63BE) -> gp-0x6b64, clamp +/-0x2800
FUN_00036388 (0x36388)     2 counters (gp-0x6a82 snap-relay, gp-0x6990 ramp) on gp-0x6b64 -> gp-0x6b62
  called from FUN_0002214a (1kHz), state-gated gp-0x67fa in {4,5,11} (mask 0x830)
FUN_0003aa2c (0x3aa2c)     11-lane aggregator: gp-0x6b62 (return) + gp-0x6b4c (LKAS) + 9 others,
                           UNCONDITIONAL ADD, gate gp-0x67ac==1 selects a "reduced" branch (unreachable,
                           see 3.6) -> gp-0x6b94, clamp +/-0x2800(10240)
FUN_0004503c               governor: slew-limits gp-0x6b94 -> gp-0x6ace
FUN_000456a4               + angle/rate-gated comp term -> gp-0x6acc
FUN_00042af8 (0x42af8)     positive-only zero-gate (gp-0x6acc>+8192 -> whole leg = 0, no hysteresis)
                           -> gp-0x6b08 -> integrator/blend -> uVar34
                           + gp-0x6afe (PROVEN ALWAYS 0, see 3.3) -> clamp +/-gp-0x4f64 (RATE-ADAPTIVE,
                           see 3.4) -> hard clamp +/-0x2000(8192) -> gp-0x6b98 -> FOC
```

## 3. Findings — EVIDENCE vs BELIEF labelled

### 3.1 The return-to-centre lane, identified [EVIDENCE]

`FUN_00036388` -> `gp-0x6b62` is the kit's established, only candidate return-to-centre term (per prior
sessions' memory, re-confirmed this session). It is NOT literally an angle-tracking controller: its gate
variable `gp-0x6b64` (from `FUN_000360fe`) is a product of a torque-margin LERP (`gp-0x6bda`, a peak-hold
margin of driver/assist torque) and `gp-0x6abc` (a motor-rate derivative). **No angle term anywhere in
either function.** Full disasm re-confirmed this session (206 + 72 instructions, both functions).

### 3.2 No return term is gated by LKAS command magnitude anywhere upstream [EVIDENCE]

Scoped `search_instructions` on `FUN_00036388` and `FUN_000360fe` for every candidate LKAS-command cell
named in the brief — zero hits, all five:

```
FUN_00036388: 6b3c=0, 6b4c=0, 6afe=0, 6b98=0, 6b4a=0 hits (206 instructions scanned, truncated:false)
FUN_000360fe: 6b3c=0, 6afe=0 hits (72 instructions scanned, truncated:false)
```

Return-centre's producer chain reads driver-torque-margin and motor-rate signals only. There is no
`if (LKAS != 0) suppress return` branch anywhere in these two functions.

### 3.3 🛑🛑 CORRECTION: `gp-0x6afe`/`gp-0x6b4e` — the brief's own candidate signal — is PROVABLY, STRUCTURALLY ALWAYS ZERO

The team-lead's brief named `gp-0x6afe`/`gp-0x6b4e` as "the LKAS overlay [that] reaches the motor" via
`FUN_00042ac6`. Traced its producer fresh this session and found the opposite.

`FUN_00042ac6(param_1)`: writes `gp-0x6afe = param_1` (clamped to `0x7fff` only if wildly out of range).
Sole caller: `FUN_00026c80` (the mixer), called with `r26 = clamp(gp-0x3d8c, +/-0x2800)`.

`gp-0x3d8c` is a straight sum, over all 11 mixer lanes, of a per-lane array `gp-0x62c8[lane]`
(base pointer `r28 = gp-0x62c8`, confirmed by scoped `search_instructions(function=FUN_00026c80,
operand_pattern="r28")`, 15 hits, `truncated:false`). Per-lane role dispatch (`tp+0x5124[lane]`,
`0xC4124`, byte-read this session `[0,0,5,0,5,5,0,0,0,5,0]`):

| role value | `gp-0x62c8[lane]` write |
|---|---|
| 7 | `r10` (real, non-arb, stack-sourced) — **role 7 NEVER appears in `0xC4124` on any build** |
| 6,4,3,2,1,0(default) | explicit `st.h r0,...` — **ZERO** |
| 5 | **not written at all** — retains boot value |

Boot (`.data`) source for `gp-0x62c8[0..10]` (flash offset `0x86260 + (0xFEDF1D38-0xFEDF11B0)` =
`0x86DE8`), fresh `read_memory`: **22 bytes, all zero.**

⇒ **`gp-0x62c8[lane] = 0` for every lane, at boot and forever, on every build** — the same two-method
closure (deterministic re-derivation for the reachable roles + boot initializer for the untouched one)
already used to prove `gp-0x67ac` unreachable in `reference_accord_gp67ac_reduced_branch_unreachable.md`.
**`gp-0x3d8c` ≡ 0 ⇒ `gp-0x6afe` ≡ `gp-0x6b4e` ≡ 0, always.**

**Consequence:** the shaper's final summation `iVar45 = gp-0x6afe + uVar34` (per
`memory/accord/firmware/accord-aggregator-reaches-motor-via-gp6acc-bridge.md`) reduces to `iVar45 = uVar34` — there is
**no second, independent LKAS injection at the final stage.** The entire LKAS contribution to the
delivered command flows through `gp-0x6b4c` inside the 11-lane aggregator (alongside return-centre) and
through `gp-0x6b4a` into `FUN_0003a382`'s PID reference (a *different* aggregator lane, resonance, not
return-centre). This corrects both `memory/accord/firmware/accord-aggregator-reaches-motor-via-gp6acc-bridge.md`'s
"CAN/arbitration term" label for `gp-0x6afe` and the brief's own framing of `gp-0x6b4e`/`gp-0x6afe` as
"the LKAS overlay reaching the motor."

### 3.4 The actual shared limiter: a MOTOR-RATE-ADAPTIVE governor ceiling, not a magnitude relay [EVIDENCE, cross-session]

Re-confirmed via `reference_accord_governor_gp0x184_chain.md` (2026-05-26/07-17, this kit) and
`docs/research/FEASIBILITY-8X-LKAS.md` (2026-08-06), both independently verified and now cross-checked against
this session's fresh trace of 3.1-3.3:

- The shaper's governor clamp (`+/-gp-0x4f64`, applied to `uVar34` — i.e. to the WHOLE base-assist
  aggregate, return-centre included, since `gp-0x6afe` is dead) is **not fixed**. In steady-state LKAS
  mode (`uVar26==1` inside `FUN_0007b022`): `gp-0x4f64 = MIN(gp+0x130, gp+0x128, fVar54) * 1024`, where
  `gp+0x128` is looked up from **motor electrical rate** (`gp-0x6ac0`) against an adaptive table
  (`0xC520C`: `X=[1050,1700,2500,3700,4100]`, `Y=[5325,3584,2406,1587,512]` — falling, byte-confirmed
  stock across builds V37-V74).
- Nominal ceiling (rate below X[0]) = 4762. At rate >= 4100, ceiling falls to **512** — a ~90% reduction.
- `research/FEASIBILITY-8X-LKAS.md` (item 10, independently derived): **"even at TODAY's 4x, moderately fast
  steering already clips here, before the flat 4762 ceiling matters"** — this is already the dominant
  real-world binder on the current car, not a theoretical one.

**Physical reading of the mechanism (BELIEF for the return-to-centre application specifically — the
governor-shrinks-with-rate fact is EVIDENCE; that ordinary return-to-centre reaches the table's lower
breakpoints is not independently confirmed this session):** the governed ceiling applies to the SAME
combined sum that contains both `gp-0x6b4c` (LKAS, inside the aggregator) and `gp-0x6b62` (return-centre,
also inside the aggregator). When LKAS commands ALIGNED with return-to-centre, the wheel returns FASTER
— which raises `gp-0x6ac0` (motor rate) — which SHRINKS `gp-0x4f64` — which caps the delivered total
harder, for BOTH terms, precisely when the combined push is largest. This is a **rate-adaptive,
magnitude-agnostic self-throttle**, not a magnitude relay, but it produces the same felt symptom: pushing
harder together buys less than expected, because going faster shrinks the ceiling. It is **NOT gated on
LKAS specifically** — a fast driver-only return would trip the same table — but the kit's own 4x LKAS
forward-path gain (`0xC6CD0`=3564, current build, see 3.5) makes LKAS's own contribution reach the rate
thresholds that trigger this far more readily than at stock (1x) gain, per the feasibility doc's own
finding that this is *already* the binding limiter at 4x.

**Open, not resolved this session:** the numeric mapping from `gp-0x6ac0` counts to real-world column/
wheel deg/s is NOT independently confirmed for `gp-0x6ac0` itself (a *different*, and possibly
differently-scaled, signal from `gp-0x6abe`, whose 4.7121 ct/(deg/s) scale is settled elsewhere). Whether
an ordinary, comfortable return-to-centre event reaches 1050-4100 counts on `gp-0x6ac0` — i.e. whether
this table's lower breakpoints are reachable in the exact scenario the operator describes, or require a
harder/faster correction than a gentle return — is the single most important open item. **Next step: pull
`gp-0x6ac0` (or `gp-0x6abc`/`gp-0x6abe`) telemetry from an existing rlog during a documented return-to-
centre event, or trace `FUN_00041464`'s scale constant to pin the counts-per-deg/s conversion for
`gp-0x6ac0` specifically.**

### 3.5 Item 6 — OUR OWN non-stock cells, checked [EVIDENCE]

- `0xC6CD0` = 3564 (4x LKAS forward-path gain) is CONFIRMED live on the current build (`builds/v80_v107/build_v90_tva.py`
  line 186: `"private forward LKAS gain = 4.000x, NEVER lower"`), unchanged since the V57 decouple.
- This cal sits in `FUN_00028ea6`'s reader #1 (`0x2a1ee`), feeding `gp-0x6b3c` (arb) -> mixer -> `gp-0x6b4c`
  — i.e. it inflates exactly the term that shares the aggregator's ±0x2800 sum and the rate-adaptive
  governor ceiling with return-centre (3.4). It does NOT touch `gp-0x6b62`'s own producer cals
  (`0xC618A`, `0xC627E`, `0xC63C0`, `0xC6132`, `0xC695C-0xC6970`, `0xC63BE`) — all confirmed untouched by
  any build in `analysis-2020accord/build_v*_tva.py` (grepped, zero write hits, only read/log calls).
- The corridor/boost widen cells (`0xC674F` family, `0xC61B3/5`, `0xC6CD0`'s sibling scales) do not sit
  in `FUN_00036388`/`FUN_000360fe`/`FUN_0003aa2c`'s return-centre lane directly; their relevance here is
  only via the shared-clamp/shared-governor argument above (3.4), not a direct read.
- **Per `research/FEASIBILITY-8X-LKAS.md`'s own prior finding, the aggregator's ±0x2800 total clamp and the
  aggregator's LKAS-lane window do NOT bind at the current 4x gain** ("stays well under 10240... not the
  ceiling either") — so mechanism 3.4 (the rate-adaptive governor) is the better-supported binder, not
  the aggregator's static sum clamp. I initially (mid-session) suspected the static clamp before finding
  this prior work; flagging the correction here rather than silently dropping it.

### 3.6 The two candidate "hard gate" mechanisms in the brief, both closed as NOT the cause [EVIDENCE]

- `gp-0x67ac` (aggregator's alternate "reduced" branch, which explicitly could zero return-centre via
  `0xC74AC`) — **PROVEN structurally unreachable** (`reference_accord_gp67ac_reduced_branch_unreachable.md`,
  re-confirmed this session): `gp-0x617c[i]` can never be nonzero (role 7 never appears in `0xC4124`),
  so `gp-0x67ac` is always 0, and the aggregator always takes the FULL 11-lane branch where return-centre
  and LKAS are simply added.
- `gp-0x67fa` (the state gate on return-centre's very call, mask `0x830` -> states `{4,5,11}`) — **PROVEN
  decoupled from LKAS engagement** (`reference_accord_gp67fa_writer_census_decoupled_from_engagement.md`,
  33-writer exhaustive census): every transition condition traces to `gp-0x6d78` fault/status bits, a
  UDS test-mode byte pair, or one torque-idle-plus-fault check — **zero reference to `gp-0x67fe`
  (LKAS engage-SM), `gp-0x6806`, `gp-0x69ae`, or `gp-0x1426`** across all ~20 guard conditions.

### 3.7 Is it a relay? [EVIDENCE for the mechanism that exists; it is NOT the aggregator sum]

The one genuine **hard, no-hysteresis relay** on this path is the shaper's input zero-gate on `gp-0x6acc`
(`FUN_00042af8`, `0x431d0-0x431d8`): `gp-0x6acc + 0x2000 < 0x4001` — **positive excursions above +8192
get the ENTIRE base-assist leg (return-centre included) hard-zeroed for that cycle**, a single
combinational compare with no dwell counter, i.e. **no hysteresis** — a textbook limit-cycle generator if
the gated signal dithers near the boundary. It is **direction-asymmetric** (negative values always pass
per the corrected reading in `reference-accord-shaper-fun42af8.md`) — so it would restrict return only
on ONE sign of the combined signal, not universally; this asymmetry is a real caveat against reading it
as the operator's whole story, since he describes a general (not one-sided) restriction. The
**rate-adaptive governor (3.4) is symmetric** (applies to `|iVar45|` via `+/-gp-0x4f64`) and matches the
operator's "restricts even when aligned" framing better, without a direction caveat.

### 3.8 Direction / sign [BELIEF, not fully polarity-tested this session]

Not independently re-derived this session; return-centre's own sign convention (`FUN_000360fe`: pure
brake, `sign(gp-0x6b64) = -sign(motor rate)` when its window is open, per prior memory) is unaffected by
either mechanism in 3.4/3.7 — both are magnitude-only ceilings/gates on the SUM, not sign flips. Whatever
direction return-centre computes, the governor/zero-gate can only clip its magnitude, never invert it.

## 4. Findings summary for the operator's specific hypothesis

**No discrete `if (LKAS != 0) suppress return` branch exists anywhere in this firmware** — confirmed by
full disassembly of the return-centre producer chain (3.1-3.2) and by structural closure of both
candidate hard gates named in the brief (3.6). The `gp-0x6afe` signal the brief specifically named as
"the LKAS overlay reaching the motor" is a dead cell, always zero (3.3) — a genuine correction of the
prior mental model.

**What DOES exist, and is the best-supported explanation available:** return-centre and LKAS's own
in-aggregator term (`gp-0x6b4c`) are unconditionally summed into ONE combined command that is then
capped by a **motor-electrical-rate-adaptive governor ceiling** (3.4) — the faster the wheel/motor turns,
the lower the ceiling, symmetric in both directions. Since LKAS aligned with return makes the wheel turn
FASTER, this ceiling shrinks precisely when the combined push is largest, throttling both terms together
— matching "restricts return even when aligned" without needing a magnitude-based LKAS-specific gate.
This mechanism is **not new and not specific to LKAS** (a fast driver-only correction trips the same
table), but the kit's own **4x LKAS forward-path gain (`0xC6CD0`, current build, unchanged since V57)**
makes LKAS reach the rate thresholds that trigger it far more readily than stock — already documented as
the dominant real-world binder on this car even without a return-to-centre scenario in view
(`research/FEASIBILITY-8X-LKAS.md`). **If this reading holds, the fix is closer to a revert (lowering `0xC6CD0`
toward stock) than a new lever — consistent with the brief's item 6 framing** — though this has NOT been
quantitatively confirmed against a real return-to-centre event this session (see 3.4's open item).

A secondary, direction-asymmetric hard relay (3.7, the shaper's `gp-0x6acc` zero-gate) also exists and
has no hysteresis, but its one-sided nature makes it a weaker match to the operator's general complaint;
flagged as a real finding, not the headline.

## 5. Open questions / verification needed

1. **Highest priority**: is `gp-0x6ac0`'s counts-per-deg/s scale established? Trace `FUN_00041464`'s
   scale constant, or pull `gp-0x6ac0`/`gp-0x6abc` from an existing rlog during a known return-to-centre
   event, to determine whether the `0xC520C` table's `X=[1050...4100]` breakpoints are reachable during
   an ordinary (not extreme) return, at both stock and 4x LKAS gain. This is the number that would turn
   3.4 from BELIEF into EVIDENCE for the operator's specific scenario.
2. Quantify how much of the operator's felt restriction (if any) would be removed by reverting `0xC6CD0`
   toward stock, versus a governor-table edit (`0xC520C`, not evaluated for GATE-1/2 safety this session
   — DTC-0x1d lockstep and the hard-DTC monitor both sit near this stage per `research/FEASIBILITY-8X-LKAS.md`
   items 13-14, so any edit here needs a full two-gate review before proposing).
3. `FUN_000456a4`'s comp-add term (gated on `gp-0x6a10`/angle and `gp-0x6ac0`/rate, feeding `gp-0x6acc`
   alongside the governed aggregate) was traced structurally but not fully re-derived this session for
   sign/magnitude in a return-to-centre scenario — see `reference_accord_factord_six_family_map_and_1khz_lane_v84.md`
   for the existing partial trace; not revisited here.
4. The remaining `gp-0x6a10` readers not yet decompiled this session (`FUN_0002c478`, `FUN_00036828`,
   `FUN_000371e0`, `FUN_000389ec`) were NOT checked for a second, independent return-like controller —
   `FUN_0002cc2a` (the lead named in the brief) WAS decompiled and found to be a boost/authority ramp
   state machine (writes `gp-0x699e`, a 0-1024 authority envelope, and `gp-0x6be0`, a filtered/unwrapped
   copy of `gp-0x6a0e`) — not itself a return-torque producer, though its outputs may gate/scale other
   lanes not traced this session.

No cal-only or code-cave lever is proposed this session — per the brief's constraint, this is a
structural finding for the operator/team-lead to weigh, not a build recommendation.
