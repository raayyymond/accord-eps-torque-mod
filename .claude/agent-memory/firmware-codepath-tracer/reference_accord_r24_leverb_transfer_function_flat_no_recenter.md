---
name: reference_accord_r24_leverb_transfer_function_flat_no_recenter
description: Lever B (cal 0xC6446, the r24 flat gain arm) is a MEMORYLESS scalar -- zero phase, flat magnitude, no state cells anywhere in r24's own computation (FUN_0003aa2c, 0x3aa9c-0x3ac58). The ONLY frequency shaping in the whole r24 lane comes from its UPSTREAM input gp-0x4f62, an N=4-sample backward-difference (FUN_0007e74a, cal 0xC6C42=4, unchanged by any build). That differentiator is near-flat in magnitude-SHAPE over 7.79-26.8Hz (within 0.16dB of an ideal derivative, nowhere near its sinc rolloff which starts to bite near fs/N=250Hz) and its raw gain RISES monotonically with frequency (24.9Hz is 1.18x 21.0Hz; 26.8Hz is 3.38x 7.79Hz). CONCLUSION: Lever B has no notch, no resonance, no rolloff to re-center -- it cannot be "well-matched to 21-22.5Hz and poorly-matched to 24.9-26.8Hz" because it has no center at all; if anything it is already MORE potent at the higher frequencies the mode has migrated to. Also corrects a naming conflation: FUN_00036682 ("filtered Sensor-B term, final slow IIR 6/1024") is a SIBLING lane called FROM WITHIN FUN_0003aa2c, consuming gp-0x4f60 (raw torque) directly and producing gp-0x6b46 through a separate, heavily-smoothed (~0.93Hz corner) path -- it does NOT touch gp-0x4f62/r24/r26 and is unrelated to Lever B.
metadata:
  type: reference
---

> 🛑 **AMENDED same session, after OPERATOR CORRECTION relayed by team-lead**: the "mode migrated
> 21.9→24.9Hz" framing this file's original title argued against was itself based on a wrong premise
> — the operator confirms grind#1 (18-22Hz, ~21Hz) IS the grinding, established, not open. **The
> conclusion below is UNCHANGED but the framing flips: this file's flat-shape finding means Lever B
> is CONFIRMED well-matched at 21.0-22.5Hz** (96.7-103.5% of its 21.73Hz-reference gain across that
> whole band, phase within 0.5° across it) — **not** "there's nothing to mismatch." Also added:
> **DC/0-3Hz gain is 0-14% of the 21.73Hz value (exactly 0 at DC)** — directly answers the operator's
> new hard constraint (damping/authority must not cost DC/0-3Hz steering-rate response under 6×
> command) — r24 is a bounded ADDITIVE aggregator term, not a gate/multiplier on the command path, so
> it cannot rate-limit driver input even in principle, and its own transfer shape is already near-
> silent at low frequency by construction (differentiator). Separately, note there is an ACTIVE,
> DIFFERENT, self-excited "21-28Hz mode" characterized in `docs/HANDOFF-2026-08-22-v105-the-26hz-mode-
> and-the-notch.md` (f0 = 21.90/23.61/24.90Hz at 1×/4×/6× gain, ~90× stock at 15-40°/s below 16km/h,
> addressed by V105's 25.5Hz notch on a SEPARATE lane, `gp-0x6b86`/biquad, not r24) — do not conflate
> the two; this file is about r24/Lever B specifically, whose shape is flat enough to be well-matched
> to EITHER candidate centre without needing to know which one is the true grind#1 frequency.

# Lever B's transfer function, lane-input to aggregator-contribution: FLAT. No frequency selectivity to re-center.

Traced 2026-08-22, `leverb-gate` session, team-lead's frequency-match brief (item 2). [EVIDENCE: fresh
`decompile_function`/`search_instructions` cross-checked against 3 independent prior sessions'
decompiles of `FUN_0003aa2c` (all agree byte-for-byte per
[[reference_accord_fun3aa2c_r24_r26_pole_census_no_filter_exists]]), plus a fresh PowerShell
computation of the differentiator's H(f).]

## r24's own stage (what Lever B/E3 = cal 0xC6446 actually multiplies) is provably memoryless

```
r1 = clamp(gp-0x4f62, ±5120)                              # the ONLY input with dynamics
gain_q10 = mux(gp-0x671d!=0 -> 1024(0xC6442) | lp!=0 -> 5244(0xC6446, LEVER B'S ARM)
              | assist_state>=5 -> 2048(0xC6440) | else -> mode-10 LERP surface)
x = (r1 * gain_q10) >> 10                                  # sar 0xa -- STOCK on V104/V105 (see below)
shaped = 0 if |x|<=3(0xC61F6) else sign(x)*(|x|-3)          # deadband, amplitude-nonlinear, not freq-shaping
r24 = clamp(polarity(gp-0x6752) * shaped, ±8192)
```
Zero `ld`/`st` to any persistent state cell anywhere in this sequence (`0x3aa9c-0x3ac58`) — confirmed
independently this session, matches the pole census exactly. **Raising `0xC6446` changes ONLY the
scalar `gain_q10` — it contributes exactly 0° of phase shift and a frequency-FLAT multiplier at every
frequency, by construction.** There is nothing in r24's own arithmetic for a frequency to interact with.

## The one place frequency enters at all: `gp-0x4f62`'s N=4 backward-difference producer

`FUN_0007e74a` (cal `0xC6C42`=4, confirmed unchanged stock/V104/V105 by direct byte read), an 8-slot
ring-buffer backward difference at 1kHz — see
[[reference_accord_gp4f62_torque_rate_producer_and_c6c42_window]] for the full derivation:
```
H(f) = (2/(N·T))·(1 − e^{−jNωT})     N=4, T=0.001s (fs=1000Hz, confirmed live task rate)
phase(f) = 90° − 180·N·f·T            magnitude-shape = sinc(N·f·T) = sin(πNfT)/(πNfT)
```

**Computed at the 7 requested frequencies** (fresh this session):

| f (Hz) | phase (deg) | sinc shape (rel. to ideal deriv.) | shape in dB | raw gain (∝ f·sinc) |
|---|---|---|---|---|
| 7.79 | 84.39 | 0.99840 | −0.014 | 7.778 |
| 18.00 | 77.04 | 0.99149 | −0.074 | 17.847 |
| 21.00 | 74.88 | 0.98843 | −0.101 | 20.757 |
| 22.50 | 73.80 | 0.98673 | −0.116 | 22.201 |
| 24.90 | 72.07 | 0.98376 | −0.142 | 24.496 |
| 25.50 | 71.64 | 0.98297 | −0.149 | 25.066 |
| 26.80 | 70.70 | 0.98120 | −0.165 | 26.296 |

**The sinc-shape column is FLAT to within 0.16 dB across the ENTIRE 7.79-26.8Hz span** — nowhere near
this element's actual rolloff (first null at fs/N = 250 Hz). It is NOT a notch, NOT a resonance, and
does not discriminate between "where the mode was" and "where it is now." The RAW gain (last column)
**rises monotonically with frequency** because this is a derivative-type term: **24.9 Hz carries
1.1801× (+1.44 dB) more gain than 21.0 Hz; 26.8 Hz carries 3.3810× (+10.58 dB) more than 7.79 Hz.**

## Verdict on "is Lever B frequency-selective, and can it be re-centered"

**NO to both, and the premise behind "re-centering" does not apply.** [EVIDENCE] Lever B's own edit
(the arm value) is a pure scalar with zero frequency dependence. The one frequency-dependent element
in the whole lane sits UPSTREAM, is untouched by any build to date, and has no center to move — it is
a broadband, near-ideal, monotonically-rising-with-frequency differentiator. If the 21.9→24.9Hz mode
migration (gain-dependent `f0`, see [[accord-f0-crossover-is-the-endpoint]] in kit memory) means the
symptom now sits at 24.9-26.8Hz instead of 21-22.5Hz, **Lever B is, if anything, SLIGHTLY MORE
aggressive there already (1.18-1.35× vs its old operating point), not less.** There is no version of
"raise `0xC6446` further, re-tuned for the new frequency" that differs from "raise `0xC6446` further,
full stop" — the shape is the same at every frequency in this band.

## Correction to the record: `FUN_00036682` is NOT part of r24/r26's chain

[EVIDENCE, fresh `decompile_function(0x36682)`] `FUN_00036682` — the golden model's own architecture
comment tags it "filtered Sensor-B term, final slow IIR (6/1024) [role OPEN]" (`model/eps_chain_lanes.py`
line ~411) — is CALLED FROM `FUN_0003aa2c` (`get_function_callers` confirms sole caller), so it is a
sibling lane inside the SAME aggregator-building function, but it is structurally SEPARATE from r24/r26:
its input is `gp-0x4f60` (raw torque) directly, NOT `gp-0x4f62` (the derivative r24/r26 consume); it
never references `gp-0x6806`/`lp`, so Lever B's gate does not touch it; and its output is a distinct
state cell `gp-0x6b46`, not `gp-0x4f60`/`gp-0x4f62`. Its terminal stage IS a genuine slow EMA —
`iVar14 += ((target*1024 - iVar14) * cal(0xC63D2)) >> 10`, `0xC63D2` byte-read = **6** (confirming the
"6/1024" tag), corner frequency ≈ (6/1024)·1000/(2π) ≈ **0.93 Hz** — but it feeds a different aggregator
slot entirely. `FUN_00036682`'s exact role remains open (not this session's scope); it should NOT be
cited in the same breath as "the r24/r26 lane V62 and V88 touched" — V62's edits are verified inside
`FUN_0003aa2c` directly (`0x3ac20`/`0x3ab76`), never inside `FUN_00036682`.

## Related
[[reference_accord_fun3aa2c_r24_r26_pole_census_no_filter_exists]] — the memoryless-arithmetic proof
this file's r24 excerpt reproduces exactly.
[[reference_accord_gp4f62_torque_rate_producer_and_c6c42_window]] — the differentiator derivation this
file's H(f) table is computed from.
[[reference_accord_rate_lane_v62_to_v69_gain_arc]] — V62's DISTINCT (sar-based) mechanism, see
[[reference_accord_v62_sar_absent_v104_v105_and_r24r26_at_historical_dose_ceiling]] for its current
on-car status.
