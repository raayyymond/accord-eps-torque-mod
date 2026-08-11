# The anti-damper hunt in `FUN_0003a382`'s PID — 2026-08-11

Renamed per team-lead's pivot (2026-08-11): the operator's DC-limit-cycle loop is `assist → motor →
wheel-mass reaction torque (gp-0x4f60) → error → assist`, self-excited around a lightly-damped column
mode (`Q≈14-29`). The `0xCBE74` GATE-2 review (§ below) was superseded before a verdict was reached —
its Q1-Q5 answers stand as a completed, positive independent discharge and are kept for the record, but
the live question is now: **which PID term pumps energy into the mode, at 7.79Hz.**

## Q2 (sent first) — the D-term is the sole pumping term, robustly

Full z-domain phase computation, `err[n] → combine`, at 7.79Hz, fs=1000Hz, stock cal:

| term | \|H\| | phase rel. err |
|---|---|---|
| P | 0.2500 | 0.00° (instantaneous — `alphaP=cal(0xC6450)=1024/1024`, unity) |
| I | 0.0611 | −88.60° (discrete integrator) |
| D | 0.0979 | +88.60° (discrete derivative — `alphaD=cal(0xC644A)=1024/1024`, unity) |

Folded in `err`'s phase relative to column velocity from the existing on-car measurement (V89 handoff
§1c, `phase(T_bar,ω)` 6-9Hz = −129/−143/−139°, using `err ≈ gp-0x4f60` as the dominant component):

| err/v phase | P \|H\|·cos | I \|H\|·cos | D \|H\|·cos |
|---|---|---|---|
| −129° | −0.157 damping | −0.048 damping | **+0.075 PUMPING** |
| −137° | −0.183 damping | −0.043 damping | **+0.065 PUMPING** |
| −143° | −0.200 damping | −0.038 damping | **+0.057 PUMPING** |

**D is the only term with positive `cos(phase rel. velocity)` across the entire measured uncertainty
range — robust, not knife-edge.** Net P+I+D sum is still damping overall at every value (e.g. −0.161 net
at −137°), so the loop is not grossly unstable by this metric, but D is actively opposing P+I.

**Sign chain, no hidden flip**: `gp-0x6752` boot-static +1, `out = combined × authorityLERP(≥0) ×
polarity(+1)`, ADDED into the aggregator, no further inversion downstream (established this session's
earlier PID trace). "In phase with +velocity" genuinely means energy-adding.

**BELIEF flagged**: used `gp-0x4f60`'s own measured torque/velocity phase as a proxy for `err`'s phase,
rather than re-deriving `err = gp-0x4f60 − clamp(gp-0x6ad6)`'s phase specifically — reasonable since
`gp-0x6ad6` is comparatively slow/small at 7.79Hz, but not independently re-verified this session.

## Q1 — cal census, mode liveness, build-script lineage

All three gains are LERPs indexed on `gp-0x6ac0` (motor rate) — **bare `tp`-relative reads, no
`gp+0x63fd` mode-array indirection anywhere in `FUN_0003a382`** ⇒ **mode-INDEPENDENT: identical values
and identical code path in mode 24 (manual) and mode 26 (engaged).** `tp+off` computed in code
throughout (`tp=0xBF000`).

| | cal address | value (Q10, /1024) | breakpoints | reader census |
|---|---|---|---|---|
| Kp | `0xC6B1E`(thr=0)/`0xC6B20,22`(X:300,2000)/`0xC6B24`(upper=4000)/`0xC6B26,28`(Y:256,256)/`0xC6B2C`(Y-hi=153) | **0.250** (rate<4000) / **0.1494** (≥4000) | | 1 real reader (`0x3a386`, `FUN_0003a382`) — confirmed via `search_instructions`, other hits are branch-target substring collisions in unrelated functions |
| Ki | `0xC6B0A`(thr=0)/`0xC6B0C,0E`(X:400,1500)/`0xC6B10`(upper=3000)/`0xC6B12,14,16,18`(Y: all 98) | **0.0957 FLAT** | | 1 real reader (`0x3a3e6`) |
| Kd | `0xC6ADE`(thr=50)/`0xC6AE0,E2`(X:400,1500)/`0xC6AE4`(upper=3000)/`0xC6AE6,8,EA,EC`(Y: all 2048) | **2.000 FLAT** | | 1 real reader (`0x3a446`) |
| alphaP | `0xC6450` (`tp+0x7450`) | **1024/1024 = 1.0** | scalar | 1 real reader (`0x3a7f0`, matches `build_v46_tva.py`'s own independent note) |
| alphaD | `0xC644A` (`tp+0x744a`) | **1024/1024 = 1.0** (stock) | scalar | 1 real reader (`0x3a860`) |
| authorityLERP (`gp-0x671a`-indexed) | `0xC67B2`(thr=5)/`0xC67B4`(X=10)/`0xC67B6`(upper=15)/`0xC67B8,BA,BC`(Y: all 1024) | **1024/1024 = 1.0, FLAT across the entire domain** | | 1 real reader (`0x3a4ae`), other 8 hits are branch targets in an unrelated function |

All five LERP/scalar readers verified as SOLE consumers, all inside `FUN_0003a382` — no shared/duplicate
computation elsewhere touches any of these cals.

**Build-script lineage, grepped `build_v*_tva.py` for every address above:**
- **`0xC644A`**: touched by V43 and V49. 🛑 **Resolved the discrepancy you flagged.** Read
  `build_v43_tva.py` directly (not just its print statements, which disagree with each other): the
  code sets `POLE_NEW = 32`, asserted against the RWD readback (`assert ... == POLE_NEW`). **The
  build's OWN print statement at the bottom says "1024 -> 64" — that text is STALE**, left over from
  "an earlier draft of this builder [that] used 64, chosen when the symptom band was ASSUMED to be
  30-50 Hz... now corrected" to 32, per the build script's own comment. **The image value is 32, not
  64 — your instinct was right, the "64" in some memory is inherited stale print-statement text, not
  the actual edit.** V49 separately set it to 64 (`"EDIT 3: StageC pole 0xC644A 1024->64 (band-limit)"`)
  — a DIFFERENT build, never flashed per the record (no on-car result cited for V49 in the grep hits).
  V43 was flashed and reported NULL, reverted at V44, and has stayed stock (1024) through V45-V84.
  🛑 **V43 targeted a DIFFERENT symptom: its own comment says "a SHARP, ISOLATED SPECTRAL PEAK AT
  21.02 Hz", not the ~7.8Hz ratchet.** Computed V43's actual filter (alphaD=32/1024) at **7.79Hz**
  specifically: `|H|=0.544, phase=-55.6°` ADDED on top of the raw derivative's own +88.6°, giving a
  combined D-phase of **+33.0°** (vs stock's +88.6°) — **enough to flip D's `cos(phase rel. velocity)`
  from +0.66 (pumping) to −0.24 (damping) AT 7.79Hz**, using the same −137° err/v reference as Q2.
  **⇒ if V43's on-car data was ever scored at 6-9Hz specifically, that would be a direct, on-car test
  of "does damping D at this exact frequency help" — but the record only cites a 21Hz null, and I found
  no evidence this kit ever re-scored V43's route at 6-9Hz. The record does NOT bound the current
  hypothesis; it's an unexamined data point, not a confirmed null on it.** ⚠ Team-lead: this is a real
  finding — a **filter** (V43's actual mechanism) both attenuates AND re-phases D differently at 21Hz
  vs 7.79Hz, so even IF someone re-checked V43's telemetry at 6-9Hz, a null there would only refute
  "adding THIS SPECIFIC POLE helps" — a pure GAIN reduction on Kd is a structurally different
  intervention (no added phase at any frequency, per your own framing) and V43 cannot bound it either
  way.
- **`0xC6450`**: touched by V46 (`1024→32`, flashed, reported NULL, reverted V47, stock since). This is
  the P-term's own pole, not the D-term's — same "filter vs gain" caveat applies if it's ever revisited,
  though P is not the pumping term per Q2 so this is lower priority.
- **Kp/Ki/Kd LERP tables themselves, the authority LERP, and `0xC67B2` region**: **zero hits** in any
  `build_v*_tva.py` — never touched by any build in this kit's history. **A direct Kd-magnitude cut
  (as opposed to V43's pole) has never been tried.**

## Q3 — loop gain at 7.79Hz, per term, and `gp-0x671a` RESOLVED

`authorityLERP(gp-0x671a)` — the one previously-unresolved multiplier — is **CONFIRMED flat 1024/1024 =
1.0 exactly across its entire domain** (table above). ⇒ **The earlier loop-gain bound (this session's
driver-reference trace, ≈0.064-0.090 at 6-9Hz, I-term dominant) is now EXACT, not a bound with an
unverified factor.** At 7.79Hz specifically, per-term contribution to `combine` (magnitude only,
ignoring sign): P=0.25, D=0.098, I=0.061 — **P is the largest by raw magnitude, D second, I smallest**
at this frequency (I dominates only at lower frequencies, per the earlier 2-4Hz table).

**This total loop gain (≤0.1) is far below unity, and per your own framing that a self-excited limit
cycle needs loop gain ≥1 somewhere in the cycle, this PID stage's OWN gain cannot be the sole gain
element closing the loop.** The two consistent readings: (a) the loop also includes the aggregator's
own unity-summing, the governor, the FOC/motor gain, and mechanical transmission — none characterized
by gain here; (b) more importantly, **the column itself is the missing gain** — a `Q≈14-29` resonance
has very little inherent damping margin (`ζ ≈ 1/(2Q) ≈ 0.017-0.036`, matching the ring-down measurement
already on record), so it does not take a large ADDED destabilizing term to push the SYSTEM's total
damping negative — a small persistent pump (D's +0.057 to +0.075 here) working against an
already-marginal natural damping margin is a coherent, evidence-consistent picture without requiring
this PID stage alone to supply loop gain ≥1. **I read the second explanation as the more likely one,
per your own note that it's "more valuable" — but I have NOT quantified the plant's own resonant gain
independently this session to close this numerically; it rests on the existing ring-down `Q` measurement,
not a fresh derivation.**

## Q4 — the LKAS-vs-driver asymmetry, quantified structurally

**The asymmetry is NOT in how the PID processes the two sources — `err = gp-0x4f60 − bias` treats every
count of `gp-0x4f60` identically regardless of physical origin, and `gp-0x4f60` is unfiltered (this
session's earlier producer trace: no EMA/IIR anywhere in `FUN_0007f3f8`).** A reaction torque from wheel
inertia and a torque from the driver's hand are PHYSICALLY INDISTINGUISHABLE once they reach the sensor,
and the PID responds to both with the exact same transfer function.

**The asymmetry is in what's MISSING: there is no cancellation of the portion of `gp-0x4f60` that the
assist system itself just caused.** Per the already-established §1e finding (prior session, re-cited
here): Honda's own architecture HAS a slot for exactly this — a per-channel "declared-disturbance" field
(offset +8 of the channel struct), summed UNGATED directly into the observer residual, with clamp
±20000 (bit-for-bit the observer model's own output clamp) — **and LKAS explicitly writes ZERO into it**
(`0x2b530: sst.h r0,0x8[ep]`). That slot is a mechanism DESIGNED to tell the observer "this much of what
you're about to see was caused by MY OWN command, don't treat it as new information" — and it exists,
architecturally, but is unused by LKAS.

**Quantified**: for a torque `T` appearing at the column from EITHER source, `err` gains `T` identically
(unity, no filtering, no source-tagging) — the asymmetry is not a differential GAIN, it is a **missing
feed-forward cancellation term specific to the assist system's OWN recent output.** Reframing the
operator's words in firmware terms: *"openpilot is commanding an assist that is handled differently
than driver torque"* is precisely true one level up — **the CAUSE of a reaction is handled differently
(LKAS commands, and its own physical consequence loops back utterly unmarked), even though its
CONSEQUENCE (the resulting torque at the sensor) is handled identically once it lands.** This is
consistent with, and gives firmware-level precision to, the operator's original framing — and it
operates most strongly through the D-term (Q2), since a reaction to a fast column motion is fast/AC
content, exactly what D (not P or I) responds to.

**I have NOT quantified "how much of `gp-0x4f60`'s AC content at 7.79Hz is actually LKAS-caused vs
driver-caused" in absolute counts** — that is a measurement question (needs matched engaged/hands-off
data), not a structural one, and is outside what I can establish from the image alone.

## Recommendation, cal-only per your instruction

**No cal exists that scales `Kd` alone without adding a filter pole** (V43/V49 both added a pole, never
a pure gain cut). **A direct edit exists and has never been tried**: lower the flat `Y` values in the
Kd LERP table (`0xC6AE6/E8/EA/EC`, all currently 2048) — this is a PURE GAIN cut with **zero added
phase at any frequency** (unlike V43's pole), is **mode-independent** (affects manual and engaged
identically, satisfying no special mode-gating is needed or possible here), and is **exactly zero cost
at DC** (a derivative term is already zero at steady state, so cutting its gain cannot cost steering
rate at maximum sustained LKAS command — satisfies the operator's stated constraint by construction,
independent of dose size). This is a genuinely new, untried, cal-only lever consistent with every
constraint you and the operator have stated. **I am not sizing a specific multiplier — that needs your
judgement on how much of D's now-quantified pumping margin (+0.057 to +0.075 at 7.79Hz) you want to
remove, weighed against the loss of legitimate rate-derivative response elsewhere in the P/I/D's
intended operating envelope (a real cost I have not characterized).**

---

## APPENDIX — the original `0xCBE74` GATE-2 review (Q1-Q5), completed before the pivot, kept for record

Independent discharge, no coordination with `fw-dampaxis`, verdict: **positive clearance recommended**
for `0xCBE74` modes 26/27 ×2-2.5 as originally specified. Full detail was sent to team-lead in two
messages; condensed here:
- **Q3 (clamp/monitor ordering)**: CLEARED. `0xC407E=511`, `0xC4004=0.5f`, both fresh-read. The clamp is
  baked into the local register value before any store — `gp-0x6b26` structurally cannot hold an
  unclamped value.
- **Q1 (26-31Hz phase margin)**: `gp-0x6c2c` cascade (`α1=37/128`, `α3=22/64`) is DISSIPATIVE (relative
  to velocity) at every frequency 2-35Hz tested, STRONGEST at 26-31Hz.
- **Q2 (Path-1 sign)**: unweighted `add`, confirmed via raw disasm; the `0xCBE74` dose Y-values are
  negative, so `gp-0x6b26` (post-multiply) is genuinely anti-phase with velocity — a real damper.
- **Q4 (GATE 1)**: no unaccounted lockstep pair, no register-indirect access to `gp-0x6b26`/`gp-0x6c2c`.
- **Q5 (modes)**: mode 27 never observed reached in 104k frames of telemetry; moot since its record is
  byte-identical to mode 26's. Engagement-boundary step is real but small/conditional on `gp-0x6c2c`'s
  instantaneous value, and the disjoint-mode-column pattern is not new to this build.

This is a SEPARATE lever from the D-term question above — `0xCBE74` is velocity-derivative-based too
(`gp-0x6c2c`) but enters through a DIFFERENT path (`FUN_00036c12` → Path 1/2 → aggregator directly, not
through the PID's error term), and per the appendix's Q1/Q2 it was found DISSIPATIVE, not pumping. The
two findings do not contradict: this firmware has (at least) two mechanisms sensitive to column
motion/rate — one measured dissipative (`0xCBE74`/`gp-0x6b26`), one measured pumping (`Kd` in
`FUN_0003a382`) — consistent with a system that is close to marginal, not grossly wrong everywhere.

## N1 — the frequency sweep (2026-08-11, using `docs/SCORING-2026-08-11-v90-flight.md` §4.1)

| band | measured err/v phase | P: \|H\|·cos | I: \|H\|·cos | D: \|H\|·cos |
|---|---|---|---|---|
| 2–4 Hz | −152.0° | −0.221 damp | −0.076 damp | +0.017 PUMP (weak) |
| 4–6 Hz | −136.9° | −0.183 damp | −0.066 damp | +0.042 PUMP |
| 6–9 Hz | −125.3° | −0.145 damp | −0.053 damp | +0.076 PUMP |
| 9–12 Hz | −144.4° | −0.203 damp | −0.028 damp | +0.073 PUMP |
| **12–16 Hz** | **+176.8°** | −0.250 damp | +0.0004 ≈0 | **−0.018 damp — FLIPPED** |
| 18–22 Hz | NOT MEASURED | \|H\|=0.250, 0° rel err | \|H\|=0.024, −86.4° rel err | \|H\|=0.251, +86.4° rel err |
| 26–31 Hz | NOT MEASURED | \|H\|=0.250, 0° rel err | \|H\|=0.017, −84.9° rel err | \|H\|=0.358, +84.9° rel err |

**D pumps 2–12 Hz, then FLIPS TO DAMPING at 12–16 Hz** — right where the measured phase crosses through
+176.8° (near the ±180° boundary). P is a reliable damper at every measured band (phase fixed at 0° rel.
err, so it just inherits `Re(Z)`'s own sign). D's raw magnitude keeps GROWING with frequency (0.094 at
7.5Hz → 0.176 at 14Hz → 0.251/0.358 extrapolated at 20/28.5Hz).
**18–22Hz and 26–31Hz (the grinding bands) have NO measured err/velocity phase anywhere found — CANNOT
ESTABLISH whether D pumps or damps there.** Two readings, neither resolved: if the phase trend keeps
rotating past 12–16Hz's near-180° crossing, D would likely be damping (and growing) in the grinding
bands too — cutting Kd would then cost real, larger-magnitude damping exactly where the operator's
grinding lives, a genuine trade against the 2–12Hz pumping fix. If a second physical regime intervenes
past 16Hz (plausible — the 12–16Hz jump itself looks like a resonance crossing, not a smooth trend), the
sign there is unpredictable from what's on record. **Blocking gap for a dose decision, not glossed over.**

## N2 — closing the flagged BELIEF (only partially closeable)

Corrected the SUM_6ch EMA alpha to `102/1024` (not `/4096` — the decompile's `>>10` shift is the tell).
Computed the two linear filter stages between `gp-0x6b98` (delivered command) and the pre-LERP residual
that becomes `gp-0x6b70`, at 7.79Hz: command-branch EMA (`α=573/4096`) `|H|=0.951, phase=−16.6°`;
SUM_6ch EMA (`α=102/1024`) `|H|=0.906, phase=−23.6°` — **this second figure exactly reproduces an
already-established golden-model number ("Path 2's own iVar4 IIR: −0.85 dB/−23.63 deg" at 7.79Hz)**,
strong cross-validation of both the corrected alpha and the method. **Combined: `|H|=0.862` (86%
magnitude survival), `phase=−40.3°` — NOT a slow/DC-dominated filter.**

**⇒ Term 7 (`gp-0x6b70`) is plausibly the DOMINANT source of `gp-0x6ad6`'s 7.79Hz content, not term 0**
(term 0/`gp-0x6b4a` confirmed low-content per team-lead's own established LKAS-low-pass reasoning, not
re-derived here). **Cannot fully close the belief**: term 7's phase relative to velocity depends on the
plant-model-vs-actual MISMATCH's own phase (an internal, closed-loop quantity — `gp-0x6b98` and the
aggregator lanes feeding "actual" are themselves part of the ringing loop), not an externally measurable
input like `gp-0x4f60` was on-car. **CANNOT ESTABLISH** whether `err≈gp-0x4f60` over- or under-states the
true `err` phase at 7.79Hz — the assumption is weaker than first flagged, direction unknown. A live probe
of `gp-0x6ad6`/`gp-0x6b70` alongside velocity (same instrumentation class as V87's existing 427 probe on
`gp-0x6b98`) would settle it directly; not proposed as a build here, named as the concrete next step.

## N3 — `Kd` cal, lineage, structural cost (no dose recommended, per team-lead instruction)

`Kd` LERP: `0xC6ADE` region (thr=50/X=400,1500/upper=3000/Y=2048×4, FLAT), mode-independent, sole reader
`0x3a446`. Never touched by any `build_v*_tva.py`. `0xC644A` (V43, actual value 32 not 64) is the FILTER
α downstream of D's raw output, NOT the same intervention — lowering it ADDS LAG, which at 7.79Hz
computably pushes the anti-damping the wrong way (see prior section). **The `Kd` LERP itself has never
been edited by any build.** A cut here is a pure gain change, zero added phase at any frequency — that
structural property, not a claimed dose, is the finding.

## N4 — GATE 1 / blast radius for a `Kd` cut

`gp-0x6ad4` (D's combined output with P/I): fresh `search_instructions` + LE32 scan — **exactly 1 writer
(`0x3a8a0`) and exactly 1 reader (`0x3aca8`, `FUN_0003aa2c`'s unweighted `add` chain, the same one
established in the `0xCBE74` GATE-2 work)** — narrowest blast radius found in this kit. 0 LE32 hits, no
register-indirect access. (`set1`/`clr1` hits on operand text "6ad4" excluded — different base register
`r18`, a coincidental displacement match, not a `gp`-relative access.)

**Where a cut costs phase margin**: D is the loop's only source of phase LEAD (P=0°/I=−90°/D=+90°
relative to err, always — these never move; only the measured err/velocity phase per band moves). A
`Kd` cut reduces the lead's MAGNITUDE uniformly at every frequency without shifting where it sits. Per
N1's own table: D is net-destabilizing (pumping) at 2–12Hz and net-stabilizing (damping) at 12–16Hz —
cutting `Kd` trades margin from 12–16Hz into 2–12Hz, the SAME numbers as N1 read as a margin question.
Separately, not quantifiable from the image: D provides the PID's fast response to sudden torque changes
in ordinary driving — a real feel cost outside what static analysis can size.

## N5 — telemetry probe spec (SPEC ONLY — no cave payload, no bytes)

1. **Telemeter `gp-0x6ad6`, not `gp-0x6b70`.** `gp-0x6ad6` is literally the quantity `err` is built from
   (`err=gp-0x4f60−clamp(gp-0x6ad6,±8192)`) — answers N1's question directly with no assumption about
   which of the 8 internal terms dominates. `gp-0x6b70` is only one of those terms; reading it alone
   reopens the composition question N2 couldn't close.
2. **GATE 1**: re-cites `reference_accord_fun3a382_gp6ad6_model_closure_and_bias_clamp_correction.md` —
   `gp-0x6ad6` has exactly 3 static references (1 write, 2 reads, both inside `FUN_0003a382`). A
   telemetry read is a 4th, READ-ONLY reference — blast-radius-zero by construction, same class as
   V87's existing 427 repoint.
3. **CAN 427 scaling**: the existing `(|x|*5)>>3` clamp(0,0x3FF) packer CLIPS immediately at `gp-0x6ad6`'s
   own ±25600 ceiling (computed: 25600 maps to 1023, already railed — tuned for `gp-0x6b98`'s narrower
   ±8192, not this cell). **Recommend `|x|>>5`**: ceiling maps to 800/1023, never clips, ~9.64 effective
   bits. `>>6` (400/1023, ~8.64 bits) as a more conservative fallback. **427 Nyquist=24.91Hz: 2-12, 12-16,
   and 18-22Hz all comfortably below Nyquist, faithfully represented. 26-31Hz is entirely ABOVE Nyquist
   and ALIASES (28.5Hz folds to ≈21.3Hz) — 427 cannot see this band and would contaminate an 18-22Hz
   reading if 26-31Hz content is real.** Hard limit of this approach for that specific band.
4. **100Hz sign bit**: agree with team-lead's allocation (`0x14A` byte4 b4, measured dead by team-lead,
   not independently re-verified this session) pairing sign at 100Hz with `>>5`-scaled magnitude at 50Hz
   — same reconstruction class V88 already proved.
5. **Identity discriminator**: `b4 == (gp-0x6ad6 < 0)` at the same hook feeding the 427 packer — holds
   exactly every frame on the new build by construction, uncorrelated (near-chance) on the old build
   (b4 there reflects `gp-0x6c00`'s unrelated sign) — same test class as V88's `MOTOR_TORQUE≥160`≈b6
   check. Exact expected identity rate not computed — needs the hook's bit-packing detail, cave-design
   territory, not spec.
