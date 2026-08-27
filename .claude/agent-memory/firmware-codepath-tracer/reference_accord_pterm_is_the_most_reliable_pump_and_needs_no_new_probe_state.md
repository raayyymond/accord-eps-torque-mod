---
name: reference_accord_pterm_is_the_most_reliable_pump_and_needs_no_new_probe_state
description: "🛑🛑 WRONG CONCLUSION, CORRECTED SAME DAY -- see reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal's second correction. P is the DOMINANT DAMPER, not the pump -- I applied the gp-0x6752 correction to GATE2's labels instead of its raw numbers under the canonical convention. D remains the pump (GATE2's original finding, now verified). What SURVIVES from this file: P's own transfer function IS a pure static 0deg-phase gain (that structural fact is convention-independent and correct), and the zero-new-state probe design (gp-0x4f60 vs velocity) is still valid if anyone wants to probe P's DAMPING role specifically -- just not as 'the pump.'"
metadata:
  type: reference
---

# 🛑🛑 CORRECTED, same day: P DAMPS, it does not pump. Read this before anything below.

This file's headline ("P is the dominant pump candidate") is WRONG. The error was applying the
`gp-0x6752=-1` correction to GATE2's own PUMP/DAMP LABELS rather than to its raw numbers read against
the kit's CANONICAL Re(Z) convention (GATE2 uses a different, non-matching convention — see
[[reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal]]'s second correction for the
full re-derivation, numerically verified against `rlog-tools/probe/decode_v90_probe.py`'s actual code).
**Correctly combined: D pumps, P (and I) DAMP at 6-9Hz** — GATE2's original finding, recovered.

**What still holds from the analysis below**: P's own transfer function IS a pure static gain, exactly
0° phase at every frequency, no EMA/dynamics — that structural fact doesn't depend on any sign
convention and is correct. It means P's classification (now: DAMPING) is the most RELIABLE of the three
terms, for the same reason originally stated — it inherits the measured err/v phase directly, no
composed transfer function. **P is now understood as the dominant, most-reliably-classified DAMPER in
the PID, not the pump.** The zero-new-state probe design (`gp-0x4f60` vs `gp-0x6c2c`) is unaffected —
if anyone wants to probe P specifically (e.g. to understand what's currently limiting/countering the
ratchet), it's the same cheap tap, just answering a different question than "find the pump."

---

# ⚠ EVERYTHING BELOW IS THE RETRACTED ARGUMENT — retained for provenance. Read the correction above first.

## P is the most reliable pump call in the PID, and probing it costs nothing new

2026-08-20, immediate follow-up to [[reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal]].

## Why P's classification needs no extra assumption

`FUN_0003a382`'s Stage A: `P_raw = (gainA * ERR) >> 10`, `P_state = P_prev + ((P_raw*32 - P_prev)*cal(0xC6450))>>10`
with `cal(0xC6450)=1024=unity` ⇒ `P_state = P_raw*32` exactly, EVERY cycle, no delay register between
write and read (`0x3a874 add r6,r12` reads P_state the same tick it was written). **This means P's
transfer function relative to ERR is a pure real gain, 0° phase, at every frequency** — confirmed
already in [[reference_accord_pid_dterm_anti_damper_and_v43_lineage_correction]] ("P is a pure static
0°-phase gain at every frequency"). D, by contrast, needed its OWN ~84-90° discrete-derivative lead
COMPOSED with the err/v phase to get a classification — two transfer functions stacked, two places for
error to enter.

**P has none of that.** Its pump/damp call is: `sign(cos(phase(ERR/v) + 180°))` — i.e. it inherits the
GATE2 N1 table's directly-measured `err/v phase` (−125.3° at 6-9Hz) with **zero additional structure**,
only the corrected polarity flip. `cos(−125.3°+180°) = cos(54.7°) = +0.577` (positive) ⇒ **P PUMPS**,
magnitude `0.250 × 0.577 = +0.144` at 6-9Hz — matches the corrected table already sent to `main`.

## Consequence — P outranks D as a candidate on TWO independent grounds

1. **Magnitude**: `|H_P|=0.250` (flat, motor-rate-scheduled 153-256/1024) vs `|H_D|=0.098` at 7.79Hz —
   P is structurally ~2.5× louder.
2. **Reliability**: P's classification rests on ONE measured quantity (err/v phase) with no compounding
   transfer function; D's rests on TWO (its own lead + the same proxy), each with its own uncertainty.

**P is now both the largest AND the most defensible pump candidate in the PID.**

## A P-probe needs no new RAM state — reuse the existing signal

Unlike D (which needed `gp-0x3680`), P has no persistent state to tap — it's recomputed from `ERR` fresh
every cycle. But per `reference/firmware/reference-accord-fun3a382-is-a-real-pid.md`'s own established finding, **for AC
content faster than `gp-0x6ad6`'s own bias crosses its 2-state boundary, `ERR`'s AC content IS
`gp-0x4f60`'s AC content (unity gain, zero phase)** — so a comparator can skip `ERR` entirely and compare
`sign(gp-0x4f60)` (the raw torque sensor — an existing, already-probed signal, not a new cave read)
against a velocity reference (`gp-0x6c2c`, as used for `gp-0x6b26`/r24/r26). **This is cheaper than the
D-term probe in [[reference_accord_pump_hunt_comparator_probe_candidates]] — literally zero new state,
one comparison.** Caveat carried over: near the rare frames where `gp-0x6ad6`'s bias flips its 2-state
selector, `ERR` and `gp-0x4f60` diverge briefly — a small, already-flagged edge case, not a blocker.

## Related
[[reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal]] — the polarity resolution
this extends. [[reference_accord_pump_hunt_comparator_probe_candidates]] — the D-term/r24/r26 probe
design this complements (P can ride the same cave, same hook, same episode).
