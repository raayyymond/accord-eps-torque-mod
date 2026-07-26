---
name: reference-accord-fun2eda8-lane9-raw-torque-command-path
description: FUN_0002eda8's raw gp-0x4f60 CORDIC/derivative output (gp-0x6b6c) reaches the delivered command via a NEW, previously-undocumented "lane 9" path through the distribute_clamp/mixer framework -- a live, 1kHz, unconditional command-path lane distinct from the 7 carriers any gp-0x4f60 low-pass build (V50/V51) repoints. FUN_0002ec52's parallel diagnostic-cluster output does NOT reach the command path (verdict: leave raw).
metadata:
  type: reference
---

2026-07-23 session, stock `code.bin`, GhidraMCP only (decompile_function + search_instructions +
get_function_callers + one read_memory), program="code.bin" explicit throughout (multiple programs open).
gp=0xFEDF8000, tp=0xBF000. Task: audit two functions reading raw `gp-0x4f60` that the V50/V51 EMA low-pass
build does NOT repoint (see [[reference-accord-v50-lowpass-ema-cave]]) — `FUN_0002ec52` and `FUN_0002eda8`.

## FUN_0002eda8 (gp-0x6b6c/gp-0x69fa outputs) — VERDICT: REPOINT. Confirmed live 1kHz command-path lane.

**Chain (every hop instruction/decompile-verified this session):**
`FUN_0002eda8`@0x2eda8 (raw `ld.h -0x4f60[gp]` ×2, gated by CAN-health `gp+0x6400` bit23, called by
`FUN_0002214a` the 1kHz control task) → produces `gp-0x6b6c` (a CORDIC/debounced-angle-diff derived
magnitude) →
`FUN_000339cc`@0x339cc (caller: `FUN_0002214a`, SAME 1kHz task) reads `gp-0x6b6c`, builds a 26-byte lane
struct with **lane_idx=9** (`local_24=9`), value fields 2/4/6 zeroed, value field 8 (`sVar26`, clamp
±20000) = the `gp-0x6b6c`-derived wrap-corrected delta, gains 0xa/c/e = 0x400 (no-op) → calls
`FUN_00025c32(&local_24)` ("distribute_clamp", the SAME generic 11-lane per-channel validity/clamp
framework documented in [[reference-accord-v48b-repoint-asymmetry-review]] for lane 8/the type-8 mixer;
10 callers total: `FUN_00023ad2/23fe2/2b422/2c246/2caa2/2e52e/339cc/3405a/3a8a8/3aff4`) →
`FUN_00025c32` writes lane 9's clamped value into the shared per-lane arrays at `gp-0x62e0/62f8/6274/
633c/6230/6218/6200`(+2*lane) per a STATIC per-lane mode byte at `tp+0x5124+lane` (read directly:
lane 9's mode = **5**; gate byte `tp+0x5118+lane` = **1** for ALL 11 lanes, confirmed by
`read_memory(0xC4118,24)`) →
`FUN_00026c80`@0x26c80 (caller: `FUN_0002214a`, the REAL 1kHz mixer that PRODUCES `gp-0x6b4a`/`gp-0x6b4c`,
the type-8/corridor-arm cells documented in
[[reference-accord-v48b-monitor1-dtc1c-notch-safety-closed]]) walks all 11 lanes; for mode=5 (lane 9's
mode), the lane's **value-field-8** (position `+8`, i.e. lane 9's `gp-0x6b6c`-derived delta) routes to
`gp-0x6324[lane]`, SUMMED across all mode-5 lanes into `iVar22`, clamped ±20000, and **shadow-committed
(RAM-integrity check, `FUN_0006b9fa` on mismatch — not a raw-vs-filtered compare) to `gp-0x6bfa`.**
Lane 9 does NOT feed `gp-0x6b4a`/`gp-0x6b4c` themselves (those come from OTHER lanes' value fields via
different mode-branches) — **so this new lane creates NO monitor/shadow-lockstep asymmetry risk at the
DTC-0x1c/0x1d monitors**, only a command-path-completeness question (see verdict below).
`gp-0x6bfa`'s only external reader: `FUN_00038148`@0x38148 (caller: `FUN_0002214a`) — a leaky
integrator/EMA (state `gp-0x374c`) that BLENDS `gp-0x6b4c` (mixer, includes the V50-filterable lane 8)
together with `gp-0x6bfa` (raw lane 9) and an LERP-shaped gain, producing **`gp-0x6b70`**.
`gp-0x6b70`'s only real external reader (the other 20 `search_instructions` hits on "6b70" are
`jarl 0x6b700,lp` call-target false positives, unrelated numeric coincidence — confirmed by inspecting
every hit): `FUN_00037fe6`@0x38006 (caller-chain lands in `FUN_0003a382`'s cluster). Decompiled in full:
sums SEVEN cal-weighted, individually-deadbanded terms — `gp-0x6bc2`, `gp-0x6b60`, `gp-0x6b2a`, `gp-0x6bce`,
`gp-0x6b6e`, `gp-0x6bbc`, and **`gp-0x6b70`** (cal weight `tp+0x74b0`) — into a LERP-scaled, ±0x6400-clamped
total stored to **`gp-0x6ad6`**. `gp-0x6ad6` is the EXACT variable
[[reference-accord-fun3a382-unfiltered-residual-lane]] already documents as feeding `FUN_0003a382`, "a raw
derivative on the PHYSICAL torque sensor reaching the aggregator, which IS the governor's slew target" —
i.e. the delivered command path.

**Every hop in this chain (`FUN_0002eda8→339cc→25c32→26c80→38148→37fe6`) is called by `FUN_0002214a`, the
confirmed ~1kHz control task, with no cal-gated mux or dormant-arm found blocking it** (the only gate is
the shared CAN-health `gp+0x6400` bit23 check common to all 7 already-repointed carriers). This is a live,
unconditional path, not a dormant fallback.

**VERDICT: REPOINT `FUN_0002eda8`'s raw `gp-0x4f60` reads in any V51 low-pass build.** Leaving them raw
means the ~21 Hz driver-torque content this signal derives from can re-enter the delivered command via
`gp-0x6b6c→lane9→gp-0x6bfa→gp-0x6b70→gp-0x6ad6→FUN_0003a382→aggregator`, bypassing the 7-carrier filter
entirely. **NOT independently characterized this session: whether `gp-0x6b6c`'s own CORDIC/debounce
processing (multiple internal state machines with ~1000-cycle/~10-cycle hold counters) already
low-passes this specific derived signal well below 21 Hz** — the STRUCTURAL command-path reachability is
proven; the FREQUENCY CONTENT actually carried by this specific derived quantity is not. Flag for the
next efficacy pass, not a blocker for the safety verdict (repointing a slow signal is still safe, just
possibly low-value).

`gp-0x69fa` (`FUN_0002eda8`'s other output): only real external reader is `FUN_0004fbde` (a UDS/freeze-frame
diagnostic snapshot builder, see below) — diagnostic-only, does not need repointing on its own.

## FUN_0002ec52 (gp-0x6e00/6e04/6c8c/6a4a outputs) — VERDICT: LEAVE-RAW. Diagnostic/rate-plausibility cluster, no command-path or monitor connection found.

`FUN_0002ec52`@0x2ec52 (raw `ld.h -0x4f60[gp]` ×1 effective + cached-delta read; same CAN-health bit23
gate; **caller: `FUN_00022ca0`, the ~100Hz assist-shaping task, NOT the 1kHz control task**) computes a
Q16 rate-of-change of raw torque (`gp-0x6e00`), an abs-magnitude peak-hold reset on mode change
(`gp-0x6e04`), a mode-keyed gain factor (`gp-0x6c8c`), and a plausibility-clamped lookback copy of a
different signal `gp-0x6a46` (`gp-0x6a4a`).

Consumers, all decompiled/verified: `FUN_0002f708`@0x2f708 (caller: not checked directly but same cluster;
reads `gp-0x6e00`/`gp-0x6a4a`) is a rate-implausibility DEBOUNCE state machine (10999-cycle escalation
timer) that writes bits 2/4/15 of a status bitfield **`gp-0x6a9a`**. `FUN_0002fab6`@0x2fab6 (caller:
`FUN_0002351e`, the SAME scheduler-dispatch function the a160-SID30 memory names for the diagnostic
supervisor `FUN_0004d0d0` — confirms this is a scheduled DIAGNOSTIC task, not the control task) is an
~110-sample/~70-sample statistical (mean/variance) plausibility checker; reads `gp-0x6e04`/`gp-0x6a4a`;
writes only its own private SM state plus `gp-0x6a9a`, `gp-0x6e08`, `gp-0x6e0c`, `gp-0x68c6` — all
consumed only by `FUN_00030c26` (same diagnostic cluster, address range 0x2ec52-0x33000). **No write to
any named command/aggregator/monitor cell (`gp-0x6b9x`/`gp-0x6acc`/`gp-0x6b94`/`gp-0x6b98`/`gp-0x3564`/
`gp-0x3550`/`gp-0x6af6`/`gp-0x6b00`) was found anywhere in this cluster.**

`gp-0x6a9a` itself is read by `FUN_0002eda8` (bit2, gates ITS OWN plausibility flag — an intra-cluster
feedback, not a monitor), `FUN_0004fbde` (bits 2/3, diagnostic snapshot byte), and by
`FUN_00032234`/`FUN_000308f2`/`FUN_00030c26`/`FUN_000516e4`/`FUN_00051770`/`FUN_000517ce` — the last three
addresses are the EXACT start/stop/results handler addresses of **UDS RID 0x48F1**
(`0x51622(undef)/0x516E4/0x51770`) per [[reference_accord_a160_sid30_proprietary_routinecontrol_and_rid_map]]
— confirming `gp-0x6a9a` is a diagnostic status word surfaced to a UDS routine, not a hard-shutdown trip
condition or command-path variable.

`FUN_0004fbde` (reads raw `gp-0x4f60` a 3rd/4th time, and `gp-0x6b6c`/`gp-0x69fa`) is a UDS/freeze-frame
style min/max/rolling-average SNAPSHOT recorder: accumulates ~10 samples of torque/angle/mode state gated
by a multi-flag "all collected" condition, then shifts them into a small 4-row circular history buffer at
absolute `gp+0x659c`+ — textbook diagnostic freeze-frame, not a live control path.

**VERDICT: `FUN_0002ec52` does not need repointing for command-path or monitor-safety reasons.** Its
entire consumer graph terminates in diagnostic status bits / UDS-readable snapshot buffers, running on the
100Hz assist-shaping/scheduled-diagnostic cadence, not the 1kHz control task. Repointing it would only
matter for diagnostic-value fidelity (e.g. if a UDS tool reads a rate/plausibility PID), not vehicle safety
or the vibration fix.

## Monitor/asymmetry question (task's part (a)) — answered NO for both functions
Neither function's outputs were found feeding a DTC-0x1c (`FUN_00042af8`/`gp-0x3564`) or DTC-0x1d
(`FUN_00043e44`/`gp-0x3550`) shadow-lockstep comparator, nor the type-8 lockstep `FUN_00027b0a`'s
EQUALITY compare (`FUN_00027b0a` DOES read the same lane array `gp-0x6324` that lane 9 populates, per
`search_instructions`, but that's the "independent recompute" side re-reading the SAME already-computed
per-lane array — a matched self-consistency check, not a second raw derivation, so no new asymmetry).
`FUN_00038148`'s blend of `gp-0x6b4c` (filtered-lane-influenced) and `gp-0x6bfa` (raw lane 9) is an
ADDITIVE composition into a single command term, not a comparator — this is a (b)-class command-path
completeness issue, not an (a)-class monitor-asymmetry issue.

## Related
[[reference-accord-v50-lowpass-ema-cave]] · [[reference-accord-v48b-repoint-asymmetry-review]] ·
[[reference-accord-v48b-monitor1-dtc1c-notch-safety-closed]] ·
[[reference-accord-fun3a382-unfiltered-residual-lane]] ·
[[reference_accord_a160_sid30_proprietary_routinecontrol_and_rid_map]]
