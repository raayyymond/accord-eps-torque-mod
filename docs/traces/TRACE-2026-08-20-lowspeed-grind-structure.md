# TRACE 2026-08-20 — low-speed grind (#1) structure: 0xC62EA, gp-0x6b30, return-centre, the 25600 dropout

Subagent: `firmware-codepath-tracer`. Tool: GhidraMCP only, program `code.bin` (stock, read-only calls).
`gp=0xFEDF8000`, `tp=0xBF000`. Symptom under trace: grind #1, 15-22 Hz band-RMS, sharply peaked
5-10 km/h (9.88x control vs 4.37/2.23/3.52/2.91 in the neighbouring speed strata), route `0x9e` (V103).

## TASK 1 — `0xC62EA` and what is speed-shaped 5-10 km/h

### Verdict
**[EVIDENCE]** `0xC62EA`=0 (since V53, unchanged through V103 — grepped every `build_v*_tva.py`, all
list it `320→0`, "on the car") removes the ONE conjunct of the STEER_STATUS AND-chain that was directly
keyed to `0xC62EA` itself. It cannot by itself explain a peak AT 5-10 km/h, because with the window's
low bound at 0 the test `0 <= gp-0x6a5e <= 12800` is satisfied almost everywhere — **a disabled
threshold produces a step at 0, not a peak at 5-10.**

**[EVIDENCE]** But `0xC62EA` was only ONE of FIVE conjuncts gating `gp-0x6806` (STEER_CONTROL_ACTIVE),
confirmed by fresh decompile of `FUN_00028ea6` (`m_steer_torque_arbitration`, sole caller
`FUN_0002214a`, the 1 kHz task) plus the pre-existing kit trace of the same function:

```
bVar2 = ALL of:
  1. cal(0xC62EA=0) <= gp-0x6a5e <= cal(0xC62E8=12800)         -- NOW ALWAYS TRUE (this session's find)
  2. bVar1: 5-channel range check AND gp-0x67f4==1 (voter converged) AND gp-0x6a5e<0x7d01
  3. gp-0x67fe == 2                                             -- assist substate
  4. gp-0x69aa == 0x8000 (exact)                                -- "no derate active"
  5. |gp-0x69ae| < 0x4000                                       -- LKAS setpoint magnitude window
if bVar2: STEER_STATUS follows the torque/rate debounce SM (0/4/6/7)
else:     STEER_STATUS = 3  ->  gp-0x6806=0, gp-0x69b0(ramp)=0   (0x2937E/0x29382/0x29384/0x2938E)
```
`gp-0x6806==1` (control-active) additionally requires the debounce SM to land on STEER_STATUS 0.

### What I traced fresh this session on conjunct 4 (`gp-0x69aa`)
**[EVIDENCE]** Sole writer `FUN_0004503c @0x45342` (the governor), full decompile this session:
`gp-0x69aa = (uVar17 * uVar6) >> 15` — a **product of two composite Q15 "derate" factors**, each
itself a chain of 3 MIN/ramp-limited sub-terms (`FUN_00049a90` slew, `FUN_00049a78` combine). Neither
factor is a simple function of `gp-0x6a5e`. **One sub-branch of the `uVar6` chain does compare
`gp-0x6a64` against `cal(tp+0x7316=0xC6316)`** — the same address the kit's `lowspeed_gate_census`
memory catalogues elsewhere as "governor speed, 640=10.00 km/h." [**BELIEF, not closed**] whether
`gp-0x6a64` (identity not re-derived this session — candidates: motor/resolver rate, a second angle
channel) makes this branch produce a genuine **peak** at 5-10 km/h, as opposed to a monotonic function
of something else entirely, is open. This is the single most concrete lead toward "something
speed-shaped 5-10 km/h" that isn't the already-dead `0xC62EA`, and it is NOT closed.

**[EVIDENCE, refines the record]** `gp-0x69b0` (the memory's "authority ramp") is read/written **~40
times**, all but two inside `FUN_00028ea6` itself, tightly interleaved with the `gp-0x6807`
(STEER_STATUS) debounce writers (`0x2928E-0x2972A` vs `0x2936A-0x2972A`). This is not simply "a torque
authority ramp" — it is the **debounce/escalation FSM's own working counter/timer**, used pervasively
through the 0/3/4/6/7 status transitions, reset to 0 on the `else` (status-3) branch. One external live
reader exists: `FUN_00042746 @0x42846` (not traced further this session — open item).

### The strongest structural hypothesis for the 5-10 km/h shape [BELIEF — falsifiable, not confirmed]
`0xC62EA=0` does not remove the OTHER four conjuncts. If any of them is marginal specifically in the
creep-to-walking-pace transition (plausible physically: wheel-speed/voter convergence is least stable
at the lowest nonzero speeds; `gp-0x69ae`'s setpoint window is most likely to be tested near the edge
when the driver is making tight low-speed corrections), `gp-0x6806` could still **toggle** in a band
that structurally sits above dead-stop (where LKAS is less often actively commanding a correction) and
below "fully, stably engaged" (once speed and voter convergence settle) — i.e. exactly 5-10 km/h. Every
toggle to `gp-0x6806=0` (a) zeros `gp-0x69b0`'s debounce timer and (b) — see TASK 2 — **arms and can
latch** the `gp-0x6b30` forward-LKAS-blend term at zero until re-engagement. This unifies Tasks 1 and 2
into one candidate mechanism: repeated soft-restarts of the forward LKAS blend, clustered in the
marginal-engagement band.

**This is NOT confirmed — it is the best-supported hypothesis, and it is directly testable with data
already on the bus, at zero firmware-change risk**: `STEER_STATUS` and (by construction) `gp-0x6806`
are packed onto CAN 399 by `FUN_00055c42` every cycle. **Next step: pull STEER_STATUS from the existing
route `0x9e` rlog, bin transition/toggle rate at 1 km/h resolution across 0-15 km/h, and check whether
the toggle rate peaks in 5-10 km/h coincident with the measured grind band-RMS.** No cave, no cal edit
— this is a re-read of data already collected.

### Other speed gates checked in the 0-15 km/h band [EVIDENCE, from existing lowspeed_gate_census
cross-checked this session]
- `0xC62EE` (CAN-commanded assist-shutdown permissive, ~5 km/h) — real but keyed to CAN `0x17C` byte5
  bits 7/5, normally 0. Not implicated absent a live check that bit is actually 0 on this car.
- Friction lane `gp-0x6b26` (`FUN_00036c12`): 3-pt LERP X=[0,20,90] km/h, **smoothly monotonic** —
  5.00x stronger at 0 km/h than 90 km/h, but nothing shaped specifically at 5-10 vs 0-5 km/h. Does not
  by itself fit a peak at 5-10 (would predict monotonic decay from 0 upward).
- `0xC62E2` (monitor-arm speed floor used in `FUN_00036388`/`FUN_00035e00`, see Task 3) = 0, confirmed
  this session via decompile of `FUN_00035e00` — inert, never blocks.
- FactorC (35 km/h) / FactorE (12.7 °/s) dead zones: both OFF for the entire 0-15 km/h band; not the
  source of a peak inside it.

## TASK 2 — `gp-0x6b30`, fully traced

### Identity and location [EVIDENCE, fresh decompile + search_instructions this session]
Read `0x2a1d4` (`ld.h -0x6b30,gp,r13`), write `0x2a206` (`st.h r9,-0x6b30,gp`) — **both inside
`FUN_00028ea6`**, both confirmed via `search_instructions` (2 hits, `truncated:false`); `get_xrefs_to`
on the same address returned the documented false zero. Sits on the forward LKAS-blend path per the
pre-existing `accord-authority-curve-is-virgin...md` memory's chain: `gp-0x3d3c -> gp-0x6b30 -> 4x
gain -> gp-0x6b4c -> aggregator -> gp-0x6b98 -> motor` (that downstream leg not re-walked this session;
cited as prior evidence).

### The exact mechanism [EVIDENCE — decompiled and hand-verified this session]
```c
// gp-0x3d3c is a 2-term IIR-ish accumulator feeding iVar34 (a rate-like quantity)
if (cal(0xC64A3)=='\x01' && gp-0x6806=='\0') {        // ARMED ONLY WHEN NOT ENGAGED
    // deadband test: is iVar34 inside +/- cal(tp+0x71b8) ?
    //         OR sign-discontinuity test: iVar34 * gp-0x6b30(prev) < 1 ?
    if ( deadband(iVar34) || (iVar34 * gp-0x6b30_prev < 1) ) {
        iVar23 = 0;                                    // LATCH: force this cycle's value to 0
        goto LAB_0002a1ee;
    }
}
iVar23 = (iVar34 * uVar18) >> 15;                       // normal path (engaged, or non-latching disengaged)
...
gp-0x6b30 = (short)iVar23;                              // UNCONDITIONAL write, every cycle, both paths
```
`cal(0xC64A3)` byte-read this session = **1** (stock, gate ARMED, bytes `01 00 01 01` at `0xC64A3`).

### Answers to the brief's specific questions
- **Exact condition:** armed only when `gp-0x6806==0` (NOT engaged). While armed, latches to 0 if
  `iVar34` is inside a small deadband **OR** if `iVar34` and last cycle's stored value have opposite
  sign (product < 1, the "sign-continuity" test the sibling named).
- **Output when latched:** 0, exactly, for that cycle — and see below, **self-perpetuating**.
- **How it clears:** 🛑 Once `gp-0x6b30_prev == 0`, the sign-continuity term is `iVar34*0 = 0 < 1`,
  which is **TRUE regardless of iVar34's sign** — so once zeroed while disengaged, this is a genuine
  **latch that cannot self-clear**; it holds at 0 for as long as `gp-0x6806` stays 0. It clears
  **immediately and only** on the next cycle where `gp-0x6806` becomes 1 (engaged), because the whole
  block is then skipped and `iVar23` is recomputed unconditionally from `iVar34`.
- **Is it engagement-gated?** Yes, definitively — armed only when `gp-0x6806==0`.
- **Is it speed-gated?** No direct reference to `gp-0x6a5e` (or any speed cell) anywhere in this logic.
  Any speed-sensitivity is entirely inherited from whatever makes `gp-0x6806` go to 0 (Task 1).
- **Would its chatter land at 15-22 Hz?** [BELIEF, refined] — **Not directly, by the mechanism's own
  shape.** Because the latch self-perpetuates once triggered, its "release" is paced by `gp-0x6806`
  transitions, not by `iVar34`'s own sign-reversal rate — a debounced engagement flag toggling at
  15-22 Hz (45-67 ms period) would be unusual for a status state-machine. The more defensible reading:
  each `gp-0x6806` toggle injects a **step/transient** into the forward-blend term (hold-at-zero, then
  a fresh value on re-engage), which is **broadband**, not a narrowband 15-22 Hz tone by itself — it
  would only produce a clean 15-22 Hz line if `gp-0x6806` itself toggles at that rate, which is NOT
  established this session (see Task 1's proposed telemetry check).

## TASK 3 — return-to-centre / `gp-0x6bda`, structural side

### Verdict
**[EVIDENCE]** This is a genuine **magnitude threshold not crossed in the measured corpus**, NOT a
hard structural exclusion gated on engagement. No reference to `gp-0x6806` (STEER_CONTROL_ACTIVE)
exists anywhere in either function I decompiled fresh this session (`FUN_00036022`, the `gp-0x6bda`
producer, and `FUN_00035e00`, its primary consumer/arm state machine).

### `gp-0x6bda`'s producer, traced fresh this session [EVIDENCE]
`FUN_00036022`:
```c
sVar1 = (gp-0x6bf0 < 1) ? (gp-0x6bf0 - gp-0x6bd6) : (gp-0x6bd8 - gp-0x6bf0);   // distance to NEAREST rail
sVar5 = (gp-0x67fe != 2) ? cal(tp+0x714c=0xC614C=128) : 0;                     // small offset, engaged-substate only
gp-0x6bda = sVar1 - sVar5;                          // shadow-lockstepped with gp-0x4cf4
```
`gp-0x6bf0` is a rack/steering-travel position (per kit record, 15+ readers, corrected identity); with
`gp-0x6bd6`/`gp-0x6bd8` read as the two end-of-travel rail positions, `sVar1` is a **margin-to-nearest-
rail** that is LARGE for essentially all normal steering and shrinks toward 0 only near full mechanical
lock. `gp-0x67fe==2` (engaged substate) only changes a **128-count offset**, not whether the quantity
is computed or gates to zero — this is the opposite of a hard engagement exclusion.

### The consumer/arm logic, `FUN_00035e00`, decompiled fresh this session [EVIDENCE]
No `gp-0x6806` reference anywhere. The "arm" flag (`bVar3`) instead requires a genuine **stall
condition**: `|gp-0x6b98| (final motor command) > cal(0xC618E=0x1000=4096)` AND
`gp-0x6ac0 (motor rate) < cal(0xC620C=200)` AND a floor/voter-converged/inert-speed-gate conjunct
(`cal(0xC62E2)=0`, confirmed byte-read this session, "never blocks"). Separately, the `gp-0x6bda`
window test compares it against `cal(0xC6154)=13` (byte-read this session) — a tight tolerance,
feeding a DIFFERENT flag than the previously-measured "outer gate" (−397,384) window reported for the
V92 telemetry rung; that (−397,384) figure most likely comes from `FUN_000360fe`'s 5-point LERP
breakpoints (not re-derived byte-for-byte this session — flagged, not re-confirmed).

### Consequence
The prior measurement (`gp-0x6bda` outer gate duty 0.0000 over 75,227 engaged frames, ALSO 0.0074 in
manual — see `accord/firmware/accord-return-centre-and-detent-dead-engaged.md`) is explained structurally: **normal
driving, engaged or manual, essentially never puts the rack near a physical end-stop while stalled.**
This is a threshold that was not crossed, not a mechanism switched off by engagement. **It remains
re-openable specifically for near-full-lock, low-speed, high-effort maneuvering (e.g. parking-lot
U-turns)** — plausible at low speed generally, but there is no structural reason to expect it
specifically inside 5-10 km/h versus, say, 0-5 or 10-15. Whether the operator's grind episodes coincide
with large `|steering angle|` is the empirical question that would re-open or close this for good.

## TASK 4 — the `FUN_000352b4` / `gp-0x4f60` ±25600 dropout, confirmed and placed

### Verdict
**[EVIDENCE, doubly corroborated]** Confirmed exactly as the sibling described, via fresh full decompile
of `FUN_000352b4` this session, AND independently corroborated by a pre-existing kit memory
(`reference/firmware/reference_accord_gp4f60_is_sensor_b_column_torque.md`) that characterized this exact branch in an
earlier session and explicitly calls it a plausibility guard, "active in normal driving."

### Exact location and mechanism [EVIDENCE]
```c
// gp-0x4f60 = Sensor-B (TAS) driver COLUMN TORQUE, signed 16-bit -- decisive ID via CAN399 packer
// FUN_00055c42: STEER_TORQUE_SENSOR = -(gp-0x4f60 * 125/128)  [pre-existing, cross-session evidence]
if (|gp-0x4f60| > 25600) {                              // literal immediate in the instruction stream,
                                                          // NOT a tp-relative cal -- not cal-tunable
    if (gp-0x6b86 == gp-0x4cde) {          // shadow-lockstep consistency check (real == shadow)
        gp-0x6b86 = 0;  gp-0x4cde = 0;     // LITERAL ZERO, both real and shadow, bypassing sVar15 entirely
        goto LAB_00035ae2;
    }
    // mismatch -> falls through to the fault handler below
} else if (gp-0x6b86 == gp-0x4cde) {
    gp-0x6b86 = sVar15;  gp-0x4cde = sVar15;             // NORMAL path: the fully-computed value
    goto LAB_00035ae2;
}
FUN_0006b9fa(unaff_gp + -0x4cde);                        // shadow-lockstep MISMATCH fault handler
LAB_00035ae2: ...
```
Verified the Ghidra pointer-arithmetic idiom (`&DAT_0000c800 < &DAT_00006400 + gp-0x4f60`) resolves to
`|gp-0x4f60| > 25600` by hand-walking both extremes through 32-bit unsigned wraparound arithmetic
(iVar27=+30000 and -30000 cases both checked, both consistent with the ±25600 reading) — cross-checked
against the corroborating memory's independent characterization of the identical idiom recurring at
`FUN_00042af8` (a **different** ±25600 dropout, on `gp-0x6bf0`, the soft-EME corridor arm — same 25600
literal, same "implausible signal" idiom, a second, separate instance).

### Reachability [EVIDENCE + BELIEF]
- **[EVIDENCE]** 25600 is not cal-adjustable — it's baked into the instruction stream as an immediate
  (`ori 51201,...` / `addi 25600,...`-class encoding, matching the corroborating memory's disasm of the
  sibling `FUN_00042af8` instance). Any edit to this specific bound is an in-place instruction patch,
  not a cal edit — a different, higher-risk class.
- **[EVIDENCE, pre-existing session]** The corroborating memory states directly: "normal in-window
  torque stores the computed `gp-0x6b86`/`gp-0x69a4`; only out-of-window torque forces zero. **The lane
  is active in normal driving.**" This closes the sibling's open BELIEF: the dropout is a genuine
  sensor-implausibility interlock, essentially never fired by real steering effort (even hard steering
  effort — 25600 counts is ~78% of the full 16-bit signed range, several times any of the other
  torque-derived clamps in this codebase, e.g. the 8192-count deadband/clamp another consumer of
  `gp-0x4f60` applies for its own purposes).
- Also present: an EARLIER, separate ±25600 **clamp** (not a drop) on a *different* quantity (`iVar33`,
  a `gp-0x6b4a`-gated term combined with a deadbanded/limited derivative of `gp-0x4f60`, NOT raw
  `gp-0x4f60` itself) feeding the 10-point LERP breakpoint search — this is the "clamp ±0x6400" step in
  the golden model's documented chain. **The LATE dropout re-reads the RAW, un-clamped `gp-0x4f60`
  again and, if implausible, discards the entire already-clamped, already-computed pipeline output** —
  i.e. it is redundant for numeric safety (the earlier clamp already bounds the LERP's input) and its
  only function is the plausibility interlock.

### Placement in the record
This is (at least) the **fourth** documented "invisible to no-clip rules" dropout/latch in this
firmware, alongside `gp-0x6b30` (Task 2, engagement-latched, not torque-implausibility), `0x3acc4
cmovc 0x0,r6,r13` (prior finding, drops a lane past ±10240), and `FUN_00042af8`'s `gp-0x6bf0` ±25600
corridor dropout (structurally identical idiom, different variable). **Not grind-relevant** — it does
not fire in normal driving by two independent lines of evidence — but now correctly placed as a
non-issue rather than an open question.

## Ranked candidates for a V104 grind (#1) fix

| # | Edit | Class | 15-22 Hz | 6-9 Hz | 20-28 Hz | Manual steering |
|---|---|---|---|---|---|---|
| 1 | **No firmware change** — pull STEER_STATUS from the existing route `0x9e` rlog, bin `gp-0x6806` toggle rate at 1 km/h resolution 0-15 km/h, compare to the measured grind-band shape | telemetry re-read | tests the hypothesis directly | n/a | n/a | n/a — no change |
| 2 | `0xC64A3` 1→0 (disarms the `gp-0x6b30` disengaged-only latch entirely) | cal | **UNVERIFIED, plausible reduction IF #1 confirms toggle-driven transients; could also be NEUTRAL** | likely neutral — this term is on the forward LKAS-blend path per the authority-curve memory, not evidently coupled to the PID/D-term loop | likely neutral, no evident coupling | **YES — changes disengaged/manual-mode forward-blend behavior; downstream consumer of that path in manual mode not verified this session, must be checked before proposing further** |
| 3 | Return-centre / end-stop cushion (Task 3) | — | not indicated unless grind episodes correlate with near-full-lock angle | not indicated | not indicated | n/a |
| 4 | `FUN_000352b4`/`FUN_00042af8` ±25600 dropouts (Task 4) | — | **not a candidate — confirmed inert in normal driving, closed** | — | — | — |

Both cal-only candidates on this list respect the operator's constraints (#2 does not add friction or
damping — it *removes* a zero-forcing latch; neither introduces a new filter pole/resonance). **Neither
is ready to cut.** #1 costs nothing and should run first; #2 needs its manual-mode downstream
consumption verified (GATE 2 style) before it is even a build candidate, and both are BELIEF-level until
#1's telemetry either confirms or kills the toggle-rate hypothesis.

## What I could not resolve

1. **`gp-0x6a64`'s identity** (the quantity compared against `cal(0xC6316)` inside the `gp-0x69aa`
   governor-derate chain) — not re-derived this session. Needed to close whether conjunct 4 of the
   STEER_STATUS AND-chain is genuinely speed-shaped in a way that peaks at 5-10 km/h, or is unrelated
   to vehicle speed entirely. Next step: `get_xrefs_to`/`search_instructions` on `gp-0x6a64`'s producer.
2. **Whether `gp-0x6806` actually toggles in the 5-10 km/h band post-V53** — the whole Task 1/2
   unification is a structural hypothesis, not a confirmed mechanism. Next step: the telemetry pull
   described in candidate #1 above.
3. **`FUN_00042746`'s use of `gp-0x69b0`** — the one live external reader of the debounce-FSM timer
   outside `FUN_00028ea6` — not traced this session.
4. **The exact (−397, 384) window's source function** — I did not re-derive it byte-for-byte this
   session; I read a different, tighter test (`cal(0xC6154)=13`) in `FUN_00035e00` and flagged rather
   than conflated the two. Next step: decompile `FUN_000360fe`'s 5-point LERP table directly.
5. **Whether `gp-0x6bf0`'s identity ("rack/steering travel position") is fully settled** — relied on
   the kit's existing "CORRECTED (15+ readers)" characterization rather than re-deriving it fresh this
   session.
6. **Physical torque scale for the 25600 bound** — I have the CAN399 conversion factor
   (`STEER_TORQUE_SENSOR = -(gp-0x4f60*125/128)`) but not the DBC's Nm-per-count scale, so I did not
   convert 25600 counts to a physical torque figure.
