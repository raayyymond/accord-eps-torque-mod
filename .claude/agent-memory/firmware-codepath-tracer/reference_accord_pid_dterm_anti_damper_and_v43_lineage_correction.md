---
name: reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction
description: FUN_0003a382's D-term (Kd=2.000, unfiltered at stock) is the sole PUMPING (anti-damping) term at 7.79Hz among P/I/D, robust across the measured err/velocity phase uncertainty — P and I are both damping. CORRECTS the kit's V43 lineage record (image value is 32, not 64, a stale print statement) and shows V43's null (scored at 21Hz) does not bound the 7.79Hz question. Resolves gp-0x671a's authority LERP as an exact 1.0 no-op.
metadata:
  type: reference
---

# The PID's anti-damper — traced 2026-08-11, `fw-driver-model` task (GATE-2 pivot)

Team-lead reframed the operator's ratchet as a self-excited limit cycle around the column's own
lightly-damped mode (`Q≈14-29`), driven by whichever term in `error → gp-0x6ad4 → aggregator → motor`
has the WRONG phase relative to column velocity. Traced which term that is.

## The three PID terms' transfer function, `err[n] → combine`, at 7.79 Hz (fs=1000Hz, all cals fresh-read)

| term | \|H\| | phase rel. err | mechanism |
|---|---|---|---|
| P | 0.2500 | 0.00° | instantaneous — `alphaP=cal(0xC6450)=1024/1024`=unity, no lag |
| I | 0.0611 | −88.60° | discrete integrator, ≈ideal −90° |
| D | 0.0979 | +88.60° | discrete backward-diff, ≈ideal +90°, `alphaD=cal(0xC644A)=1024/1024`=unity |

Kp=0.250(rate<4000)/0.1494(≥4000), Ki=0.0957 FLAT, Kd=2.000 FLAT — all `gp-0x6ac0`(motor rate)-indexed
LERPs, but **bare `tp`-relative, NOT `gp+0x63fd` mode-indexed** ⇒ identical in mode 24/26. Each LERP/
alpha confirmed the SOLE real reader image-wide (`search_instructions`, false positives individually
excluded as branch-target substring collisions).

## Folding in err/velocity phase (existing on-car measurement, V89 handoff §1c, 6-9Hz = −129/−143/−139°)

`err ≈ gp-0x4f60`'s own measured phase used as proxy (BELIEF, not re-derived — `gp-0x6ad6`'s own
contribution to `err`'s phase at 7.79Hz not separately quantified):

| err/v | P | I | D |
|---|---|---|---|
| −129° | −0.157 damping | −0.048 damping | **+0.075 PUMPING** |
| −137° | −0.183 damping | −0.043 damping | **+0.065 PUMPING** |
| −143° | −0.200 damping | −0.038 damping | **+0.057 PUMPING** |

**D is the ONLY term with positive `cos(phase rel. velocity)` across the WHOLE measured uncertainty
range — robust, not sensitive to which of the three phase readings is used.** Net P+I+D sum is still
net-damping at every value tested (e.g. −0.161 at −137°) — the loop is marginal, not grossly unstable.
Sign chain confirmed clean: `gp-0x6752` boot-static +1, ADDED into aggregator, no inversion downstream.

## 🛑🛑 V43 lineage correction — the image value is 32, a "64" in some record is stale print text

`builds/v18_v49/build_v43_tva.py` sets `POLE_NEW = 32` in code (asserted against RWD readback) but its OWN closing
print statement says "1024 -> 64" — leftover from an earlier draft before the target band was corrected
from an assumed 30-50Hz to the measured 21.02Hz. **The actual flashed/reverted value was 32, not 64.**

**More important: V43 targeted 21.02Hz (its own comment: "a SHARP, ISOLATED SPECTRAL PEAK AT 21.02
Hz"), not the ~7.8Hz ratchet.** Computed V43's actual filter (`alphaD=32/1024`) at 7.79Hz specifically:
`|H|=0.544, phase=-55.6°` added on top of the raw derivative's own +88.6°, giving combined D-phase
**+33.0°** — enough to flip `cos(phase rel. velocity)` from +0.66 (pumping, stock) to **−0.24 (damping)**
at 7.79Hz, using the same −137° reference. **V43's reported null was scored at 21Hz; no evidence found
that this kit ever re-scored V43's telemetry at 6-9Hz — the record does NOT bound the current
hypothesis, it's an unexamined data point.** Also: V43 added a POLE (filter, adds lag at all
frequencies it touches), a structurally DIFFERENT intervention from a pure Kd GAIN cut (zero added
phase anywhere) — even a fresh 6-9Hz rescore of V43 would not settle the gain-only question.
V49 separately set `0xC644A`→64 (never flashed per the grep of `build_v*_tva.py`, no on-car result).

## `gp-0x671a`'s authority LERP — RESOLVED, exact no-op

Fresh byte-read, `0xC67B2` region (thr=5, X=10, upper=15, Y=1024/1024/1024 at all three points):
**flat 1024/1024=1.0 across its ENTIRE domain.** Closes the "unresolved multiplier" flagged in the
earlier driver-reference trace — the loop-gain figure computed there (≈0.064-0.090 at 6-9Hz) is now
EXACT, not a bound. At 7.79Hz per-term magnitude (to `combine`): P=0.25 (largest), D=0.098, I=0.061.

**This total (≤0.1) is far below unity** — cannot alone supply the loop gain a self-excited limit cycle
needs. Reading: the column's own resonant gain (`Q≈14-29`, `ζ≈0.017-0.036` per existing ring-down
measurement) is the missing element — a small persistent pump from D, against an already-marginal
natural damping margin, is coherent without this PID stage alone needing gain ≥1. Not independently
quantified (plant gain not freshly derived this session).

## The LKAS-vs-driver asymmetry, reframed with firmware precision

Not a differential gain — `err=gp-0x4f60-bias` treats every count of `gp-0x4f60` identically regardless
of physical origin (unfiltered producer, per [[reference_accord_gp4f60_identity_conflict_and_producer_traced]]).
**The asymmetry is a MISSING cancellation term**: the per-channel "declared-disturbance" slot (offset+8,
clamp ±20000, ungated into the observer residual, per the existing §1e finding) exists architecturally
for exactly this purpose, and LKAS writes ZERO into it (`0x2b530: sst.h r0,0x8[ep]`). The CONSEQUENCE
(torque at the sensor) is processed identically by source; the CAUSE (that the assist system created
some of it) is unmarked, and it hits hardest through D since a fast reaction is AC content.

## New, untried lever named (cal-only, not sized)
Lower the flat Y in the Kd LERP (`0xC6AE6/E8/EA/EC`, all 2048 stock) — a PURE gain cut, zero added
phase at any frequency (unlike V43's pole), mode-independent, and zero DC cost (satisfies the
operator's explicit "must not cost steering rate at max LKAS command" constraint by construction, since
a derivative is already zero at steady state). Zero hits in any `build_v*_tva.py` — never tried.

## Related
[[reference_accord_gp6b4a_direct_lkas_term_and_v41_lineage_correction]] — same PID's other input path,
term 0, from the immediately-prior task this session.
`docs/review/GATE2-2026-08-11-cbe74-independent.md` — full writeup, plus the completed (unrelated, positive
clearance) `0xCBE74`/`gp-0x6b26` GATE-2 review kept as an appendix.
