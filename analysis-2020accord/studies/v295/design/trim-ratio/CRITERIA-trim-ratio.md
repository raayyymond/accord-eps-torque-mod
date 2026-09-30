# V295 design lens "trim-ratio" — FAIL criteria, written BEFORE any candidate number was computed

Subagent `trim-ratio`, 2026-09-30. Design only. Written after reading the harness report, the census, the V294 lineage
entry and the flight attribution, and before running any sweep. Anything added later is marked ADDED-LATER.

Lens: hold the static feedforward surface byte-identical to V294 and maximise the acceleration trim loop through
b (0xC63EA), the pole a (0xC63E8), the cap C (0xC62E6), and the pair Kp bank (0xCB994) × shl immediate (0x29D76)
with Kp·2^shift held at 3840.

## Candidate-level FAIL (any one = the candidate is rejected)
- **F1 FF identity.** The candidate's delivered surface T(idx) at fb = 0 (golden model `lkas_rate_pid_surface`) must equal
  V294's on all 241 idx at taper 254, and a Lane march at x = 0 must equal V294 tick for tick on a random command. Any
  mismatch means it is outside this lens.
- **F2 HF / grinding guard.**
  - |T/x| anywhere in 10–25 Hz above 3.0× V294 (rule 3), unless evidence is cited.
  - Any stress member (mode13 / mode20 / mode20_lo at 5 / 12 / 25 m/s) with the flexible-mode ζ below
    min(ζ_V294, ζ_open) − 0.005.
  - Any member of family + stress with ρ ≥ 1, or Ms above 1.5 at delay ×1.5.
- **F3 outer loop.** On `light_b` at 17 and 26.9 m/s the outer GM_min (relay on and off) must not fall more than 10 %
  below V294's, nor below 1.5. On the identified members the outer Ms must not rise above 1.4.
- **F4 safety.** All of the following must hold.
  - Rail +2461 / −2463 and sub-rail slope 0.6409 T/wire are unchanged.
  - b ≤ b_max, and every int32 margin is ≥ 2.
  - The zero-command torque (trim cap) is ≤ 616 T, V294's value.
  - The restart-pulse peak is ≤ 615 T at every rate.
  - `problems()` is empty.
- **F5 closed-loop regression.** Mode B, in the same batch as V294, under both `lp` and `full`, on `nominal` AND `light_b`:
  - tracking gain must not drop by more than 0.01 in any band;
  - turn-hold must not drop by more than 0.02;
  - hard-turn 1.6–3 Hz wheel rate must not rise by more than 5 %;
  - the `lp` 1–5 Hz limit-cycle peak on `light_b` must not rise by more than 1 dB;
  - no band of mode-A simulated delivered HF torque (5–9 … 23–30 Hz) may rise by more than ×1.5.
- **F6 attribution.** The candidate is not shippable if either of the following holds.
  - On r71b's own excitation, the byte-exact march of the candidate cells differs from V294's by a trim footprint that the
    existing E3 / SCALE regression cannot separate. The requirement is a predicted SCALE, read against V294's modelled
    trim, at least 5 block-CI half-widths away from 1.0.
  - A changed cell has no wire read at all. In particular, a C whose clamp never binds on r71b-like driving is not
    readable, so it counts as unobservable, and a change to it must be argued as inert-by-construction or dropped.

## Lens-level outcome
- **"No change" is the answer** if no candidate passing F1–F6 improves the hard-turn 1.6–3 Hz wheel rate by ≥ 10 % vs V294
  under `full` on BOTH nominal and light_b (the only complaint band this lens can physically reach). A candidate that only
  moves the literal cmd→α metric without moving the jerk band is not worth a build.
- **What a FAIL of the lens looks like** (written now): the safe region under F2–F3 is so small that the best candidate
  differs from V294 by less than ×1.5 in trim gain. That is inside the drive's own run-to-run scatter for the jerk band, and
  one short drive would return an uninterpretable null.

## Method rules I bind myself to
- Report every candidate as a difference from V294 in the same batch, never as an absolute sim number, except the outer
  metrics under `lp`, which retrodict.
- Show `full` and `lp`, on `nominal` and `light_b`. A ranking that flips between them is not supported.
- Use the stress members for any claim above 8 Hz, and call them stress cases.
- Never quote simulated dwells/min.
- Two methods for every load-bearing number:
  - HF gain: analytic `lane_ctf` against a time-domain sinusoid march through `Lane`.
  - K_α: closed form against a ramp march.
  - FF identity: golden surface against a Lane march.
  - Stress damping: `closed_loop_modes` against `v294_plant.linear_poles`, where supported, or a time-domain ring-down.
