---
name: reference_accord_dterm_grindband_unresolved_and_pid_net_damping
description: "The SIGN TABLE BELOW (P/I damp, D pumps, net -0.122 damping) IS CORRECT AS WRITTEN -- an intermediate same-day correction claimed it was reversed; that intermediate correction was itself wrong and has been retracted (see reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal's SECOND correction for the full re-derivation: GATE2 uses a non-canonical sign convention, and correctly combining that with the true gp-0x6752=-1 value recovers this file's original conclusion). The PROVENANCE-CHASE finding (the 'D damps 16-35Hz' claim traces to docs/review/GATE2-2026-08-11-cbe74-independent.md sec.N1, which explicitly declines to call the grinding bands 18-22/26-31Hz) stands throughout, unaffected by any of this."
metadata:
  type: reference
---

# ✅ CORRECTED BACK, same day: this file's ORIGINAL table (below) is right. Read the note first anyway.

An intermediate same-day edit claimed the sign table below was reversed (citing
[[reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal]]'s first pass). **That
intermediate correction was itself wrong** and has been retracted — see that file's SECOND correction
for the full re-derivation. Short version: GATE2 uses a sign convention OPPOSITE to the kit's canonical
Re(Z) tool (verified numerically against `rlog-tools/probe/decode_v90_probe.py`'s actual code); correctly
combining GATE2's non-canonical convention with the true `gp-0x6752=-1` value requires TWO sign flips,
which cancel — landing back on **this file's original numbers: P/I damp, D pumps, net P+I+D ≈ −0.122
(damping) at 6-9Hz.** No further edit needed to the table below; it was right all along, for reasons
nobody had verified at the time it was written. **The PROVENANCE-CHASE section immediately below (the
"D damps 16-35Hz has no source" finding) was never in question** — independent of any sign convention.

---

# The D-term "damps 16-35Hz" claim has no source, and the PID block nets damping at 6-9Hz anyway

Traced 2026-08-20, task `damphunt round 3` (team-lead brief: "confirm the D pumps 2-12/damps 16-35
curve is real"). Extends and closes an item my own [[reference_accord_kd_pid_dterm_priced_and_manual_gate]]
(2026-08-19) flagged as "I could not find that source file this session."

## Provenance chase — RESOLVED

`reference_accord_vehicle_bus_clearance_and_aggregator_probe_reaim_2026-08-11.md` asserts "D pumps
ONLY 2-12Hz and DAMPS 16-35Hz" citing an unnamed "parallel PID trace," no [[link]]. `docs/STATE.md`
§8.2 (2026-08-13) and `docs/BUILD-LINEAGE.md`'s Kp/Ki/Kd row both repeat this as settled. **The kit's
own most recent handoff, `docs/handoffs/2026-08/HANDOFF-2026-08-20-v102-the-gain-is-the-carrier.md` §9 item 3, already
retracted the "16-35Hz" crossover number** the same day this task started: *"The D-term damping
crossover is 22-26Hz, not ~14-16Hz... Supersedes the 'D damps 16-35Hz' line... whose cited 'parallel
PID trace' could not be located."*

**I located the closest real candidate for that trace: `docs/review/GATE2-2026-08-11-cbe74-independent.md`
§N1** (same day, same session family, does the actual `|H|·cos(err/v phase)` computation for P/I/D).
Its own table [EVIDENCE, cited exactly]:

| band | measured err/v phase | D: \|H\|·cos |
|---|---|---|
| 2-4 Hz | -152.0° | +0.017 PUMP (weak) |
| 4-6 Hz | -136.9° | +0.042 PUMP |
| 6-9 Hz | -125.3° | **+0.076 PUMP** |
| 9-12 Hz | -144.4° | +0.073 PUMP |
| 12-16 Hz | +176.8° | **-0.018 damp — FLIPPED (weak)** |
| 18-22 Hz (grind #1) | **NOT MEASURED** | not computed |
| 26-31 Hz (grind #2) | **NOT MEASURED** | not computed |

**The file's own text**: *"18-22Hz and 26-31Hz (the grinding bands) have NO measured err/velocity
phase anywhere found — CANNOT ESTABLISH whether D pumps or damps there... Blocking gap for a dose
decision, not glossed over."* It also flags the 12-16Hz flip as sitting exactly on the point where the
measured phase crosses near ±180° — plausibly a resonance crossing, not a stable trend — and says
explicitly that extrapolating it into the grinding bands is unsafe ("the sign there is unpredictable
from what's on record").

**⇒ "D damps 16-35Hz" has no computation behind it anywhere in this repo that I could find** (searched
`docs/`, `memory/`, `.claude/agent-memory/`, both literal-string and semantic). The ONE file that tried
to answer this exact question explicitly declined to for the two bands the claim is about. Checked
2026-08-20 against every doc a fresh scan of the repo could find; if a future session finds an actual
computation, this file should be updated, not just re-asserted from STATE.md.

## New synthesis — P+I+D nets to DAMPING at 6-9Hz, in the SAME units

Not previously stated explicitly anywhere I found, though it falls straight out of the GATE2 §N1 table
(which gives P, I, D all as `|H|·cos(phase)` — internally comparable even though their mapping to real
on-car ct is unknown): at 6-9Hz, **P = -0.145 damp, I = -0.053 damp, D = +0.076 pump. Sum = -0.122,
net DAMPING.** This matches (and is the same underlying arithmetic as) my own
[[reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction]]'s "net P+I+D sum is still
net-damping at every value tested (e.g. -0.161 at -137°)."

**Consequence for any D-only lever (cut Kd, or a frequency-selective D filter): it trims the ONE
misbehaving, SMALLEST term inside a PID block whose sum already points the right way** (assuming this
isolated-stage-plus-BELIEF-proxy method is trustworthy at all — see the calibration caveat below). This
is a real argument for LOW PRIORITY on the D-term as "the" 6-9Hz pump, independent of the grinding-band
gap above.

## 🛑 Calibration caveat — do not extend this method to a real-ct Re(Z) magnitude claim

The kit's own closest precedent for this exact method (isolated code-domain phase + a proxy phase,
projected into a closed-loop Re(Z) claim) is `gp-0x6b26`
([[reference_accord_gp6b26_closed_both_directions_v94_aborted]]): its isolated-stage phase (ideal -90°
relative to velocity, since it differentiates velocity) predicted ZERO real part; the MEASURED
closed-loop phase was +137°/+139°, off by ~227°, giving a real +518/+565ct DAMPING contribution instead
of the predicted-zero reactive one. **Do not report a "D carries N ct of the -3375/-3176/-3073 budget"
number from the GATE2 table's normalized `|H|·cos` values — there is no established conversion factor,
and the one directly comparable precedent shows the isolated-stage method can be off by ~227° once the
loop actually closes.** A real magnitude needs an on-car measurement (see
[[reference_accord_pump_hunt_comparator_probe_candidates]] for a concrete, GATE-1-clean way to get one).

## Related
[[reference_accord_kd_pid_dterm_priced_and_manual_gate]] — D's own dual-method-verified transfer
function (83.7°→89.6° lead relative to err, 2-35Hz, no reversal); this file's frequency-response table
is unaffected by anything here, only the pump/damp-vs-VELOCITY classification is in question.
[[reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction]] — the original 7.79Hz pumping
finding this table's 6-9Hz row corroborates.
[[reference_accord_pump_hunt_comparator_probe_candidates]] — the recommended next step.
