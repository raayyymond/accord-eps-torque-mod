---
name: accord-v59-parametric-pump-marginal
description: "V59 measured the ~21 Hz grinding's boost-index pump at 2f; it is real, engagement-gated, but MARGINAL vs the Mathieu threshold — and the lever is the previously-unmodelled blend cal 0xD2006"
metadata: 
  node_type: memory
  type: project
  originSessionId: 79c6c288-c714-4c40-a8dc-e5ed6d815de4
  modified: 2026-07-31T00:56:35.656Z
---

V59 flew 2026-07-30 (route `2c`), flight-clean, probe machine-clean (50,963 frames, 100% live,
100% thermometer-monotonic, fault sentinel 0.000%).

**The mechanism:** `gp-0x6ba6` is a *rectified* magnitude, so it sweeps the boost-amplitude LERP at
**2× the mode frequency** — measured at **42.19 Hz vs a 21.09 Hz mode**, prominence 11.10× (K=30,
periodograms averaged across disjoint runs). **Absent disengaged: bit5 never toggles, 0/4 runs,
61.2 s.** A pump at 2f into a mode at f is the principal Mathieu resonance condition.

**But it is MARGINAL.** eps across both open unknowns (task rate × the series dispute), simulating the
literal integer arithmetic with the confirmed blend direction: **0.013–0.020 at median hands-off
amplitude, 0.055–0.104 at p90, 0.070–0.169 at p99**, against `eps_crit ≈ 2/Q = 0.147`. Only the most
generous cell crosses. ⇒ an **amplitude-gated bootstrap** — which explains the burstiness — but
**do not oversell it as "the root cause".**

🛑 **Causality is NOT settleable from observation.** The index is `|x|` of a bar-derived signal, so
2f coupling and index-tracks-mode are arithmetically forced once the ripple exists. Coherence against
the bar is **circular** and is not evidence. Only an intervention separates drive from echo.

**The lever — `0xD2006` = 102 (Q10), the blend coefficient.** Both amplitude-LERP outputs pass through
a previously-unmodelled slew blend before multiplying anything; direction confirmed @`0x34be4`
(`cmp r25,r10 / ble`): **falling instant, rising slowed**. Lowering it attenuates the 42 Hz pump
**without moving the static gain map** (the blend converges to the same steady state). GATE 1 clean:
exactly one pointer (`0xCA094`) references it; the three identical values in `0xD2000` are modes
10/11/12's independent entries, not an array. ⚠ Expected benefit modest — eps is already mostly
sub-threshold, so it bites only on the loudest bursts; the argument is that a bootstrap only needs to
be held below threshold where it currently crosses.

**Closed levers:** FactorC damping `0xD27BC` disfavoured (damping IS zero below 35 km/h, all 34 mode
tables, but the hands-off mode dies below the 9.71 m/s onset — thin data, sampling gap at 6–10 m/s);
`0xC63BA` partial only (filters the torque lane; the index also carries a resolver-rate-derivative
lane); speed-keyed assist concentration refuted (curve is flat).

**Method traps this session:** (1) a byte scan of a STATE CELL cannot prove a register is unused
in-function — that argument was used to call `0xD28DC` dead and it does not hold; (2) `corr(env, lvl)`
flips sign between hands-on and hands-off (Simpson's paradox via driver effort) — always split;
(3) K=1 coherence is identically 1.0, quote K always.

See [[accord-check-build-lineage-before-proposing-lever]] before acting. Related:
[[accord-vibration-requires-lkas-engaged]], [[control-task-tick-confirmed-1khz]].
