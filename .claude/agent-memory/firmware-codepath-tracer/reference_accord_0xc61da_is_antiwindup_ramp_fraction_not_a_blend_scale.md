---
name: reference_accord_0xc61da_is_antiwindup_ramp_fraction_not_a_blend_scale
description: Bounded correction (loop-topology task, low-priority follow-up) -- 0xC61DA does NOT sit as a flat ~1.066x scale directly on the gp-0x6acc-to-gp-0x6b98 hop. Fresh decompile of FUN_00042af8 shows it scales |gp-0x3570>>15| (a slew-rate-limited integrator tracking gp-0x6b08) into gp-0x6966, which is a RAMP-FRACTION index feeding an anti-windup LERP elsewhere (likely inside FUN_0003a382's P/I/D cascade) -- a genuinely state-dependent, non-flat quantity. The d(gp-0x6b98)/d(gp-0x6b4c) blend-gain residual from the 0xC6CD0 DC-cancellation finding remains OPEN, not closed, and is LOW MATERIALITY per team-lead (no DC operating-point effect to fix given the near-exact cancellation already found).
metadata:
  type: reference
---

# `0xC61DA` is an anti-windup ramp-fraction input, not the aggregator-to-motor blend scale

Bounded follow-up, 2026-08-22, same `loop-topology` session. Team-lead flagged closing the
`0xC61DA≈1.066` blend-fraction residual (from
[[reference_accord_0xc6cd0_exogenous_via_masons_formula_but_wired_into_path2_stage1_sign_open]]'s
`d(gp-0x6b98)/d(gp-0x6b4c)≈1` assumption) as optional/low-priority — "do it only if (4) is done, and
its value dropped sharply" given the near-exact DC cancellation already established. Attempted a bounded
pass; did NOT fully close it, and the attempt itself produced a small correction worth recording.

## [EVIDENCE, fresh decompile, `FUN_00042af8` @0x42af8, ~line 625-720 and ~1205-1270 of the pseudocode]

`gp-0x6acc`'s consumer, mode-gated (`0xC64C8`, =0 on every build ⇒ stock takes the pass-through arm):
```c
uVar25 = clamp(gp-0x6acc, +-0x2000);     // mode 0: gp-0x6b08 = clamp(gp-0x6acc, +-8192)  -- unity, unclamped regime
gp-0x6b08 = uVar25;
```
So the FIRST hop (`gp-0x6acc`→`gp-0x6b08`) IS clean unity in the unclamped regime, confirming that much
of the prior belief.

**The `0xC61DA` site, precisely** — a SEPARATE sub-computation, not on this direct hop:
```c
iVar43 = *(gp-0x3570);                                     // OLD integrator state
... slew-rate-limited ramp of iVar43 toward uVar25*0x8000 (gp-0x6b08 scaled Q15),
    bounded by a step derived from OTHER untraced terms (iVar27/iVar38) ...
iVar43 = clamp(new_ramp_value, +-cal(tp+0x71dc)*0x8000);
gp-0x3570[new] = iVar43;                                    // <- the "integrator", genuinely slew-limited
uStack_f0 = gp-0x3570[new] >> 0xf;                          // back to Q0
uVar53 = |uStack_f0|;                                        // = |gp-0x3570>>15|
uVar33 = uVar53 * cal(tp+0x71da=0xC61DA) >> 10;              // <-- 0xC61DA IS HERE
gp-0x6966 = uVar33;                                          // shadow-paired gp-0x4c5a
```
`gp-0x6966` is the SAME cell referenced in `FUN_0003a382`'s decompile (this session, prior message) as
one of "3 MORE LERPs beyond Kp/Ki/Kd (indexed on `gp-0x6bda`, `gp-0x6a5e`, `gp-0x6966`)" feeding an
anti-windup/authority ceiling chain — i.e. **`0xC61DA` scales a slew-limited integrator's magnitude into
a RAMP-FRACTION LERP INDEX for the PID's anti-windup mechanism, not a flat multiplicative gain on the
`gp-0x6acc`→`gp-0x6b98` signal path.** This is a genuinely state-dependent (integrator history + slew
limit) quantity, not reducible to a single scalar without characterizing the slew-limit step size
(`iVar27`/`iVar38`, not traced) and the ramp LERP itself (`0xC6A0C-0xC6A14` per the original memory).

**Downstream, the actual `gp-0x6b98` write** (confirmed fresh, same function, ~line 1213-1264):
```c
uVar34 = (cVar8 == 0) ? iVar45(the blended/ramp candidate) : uVar25(= gp-0x6b08, raw);   // 0xC64C9 mux
iVar45 = gated(gp-0x6afe, +-10240) + uVar34;             // THE SUMMATION POINT: CAN/arb term + uVar34
iVar18 = clamp(gp-0x4f64, 0..10240);                      // governor ceiling
iVar18 = clamp(iVar45, +-iVar18);                          // clamp against the ceiling
iVar45 = clamp(iVar18, +-0x2000);                          // hard clamp +-8192
gp-0x6b98 = (short)iVar45;
```
Matches `accord-aggregator-reaches-motor-via-gp6acc-bridge`'s "THE LAST STRETCH IS CLOSED" section
exactly (same mux, same summation, same clamps) — re-confirmed fresh, not just relayed. **On stock
(`0xC64C9=0`), `uVar34` selects the BLENDED/ramp candidate `iVar45`, not the raw `gp-0x6b08` pass-
through** — so the `d(gp-0x6b98)/d(gp-0x6b4c)` residual genuinely does run through this ramp/integrator
mechanism, not a flat scalar, and I did not close its magnitude this session.

## Verdict — stopping here, bounded by priority

This is consistent with, not a refutation of, the original memory's own caveat ("the full envelope/
ramp/integrator interaction was not collapsed to one number") — my attempt to collapse it to `≈1.066`
in the prior report was an over-simplification; the honest state is "unclosed, state-dependent, low
materiality given the near-exact DC cancellation already established independently of this residual."
**Not chasing further** — team-lead's own assessment ("value dropped sharply" once the two dominant
±2.578 pathways were shown to cancel) applies with more force now that the mechanism is confirmed
genuinely non-trivial rather than a simple missing constant.

## Addendum — found in the same decompile, not chased further (close-out, `loop-topology`)

**Three NEW shadow-lockstep pairs, noticed in `FUN_00042af8` while tracing the above, not independently
verified beyond the decompile text**: `gp-0x6b98`/`gp-0x4ce2` (the final write itself), `gp-0x6b04`/
`gp-0x4cce`, `gp-0x6966`/`gp-0x4c5a` (the anti-windup ramp-fraction cell). Same idiom as the kit's other
~5-6 known pairs (`FUN_0006b9fa` resync on mismatch). Not cross-checked against `tq-lowpass`'s "6th pair
gp-0x4cd0" finding this session — may or may not overlap with their census.

**`gp-0x6bf6`** — a cell written in `FUN_0003b8f6` (`iVar11 = clamp(0xC6468 * fVar18, ±20000)`, BEFORE
friction/inertia subtraction; i.e. `0xC6468 * (cmd_branch + sensor_branch)`, not the final MODEL value)
— noticed, NOT traced forward. Not `gp-0x6bfc` (final MODEL, post-friction/inertia) — a distinct,
uncharacterized intermediate. Readers unknown.

**Possible connection to `leverb-gate`'s `gp-0x4f62` N=4-differentiator finding (today, unconfirmed)**:
`FUN_0003aa2c`'s decompile (this session, prior message) references `gp-0x4f62` in a clamp near its top
(`iVar17 = (int)*(short*)(gp-0x4f62); ... pcVar10 = clamp(iVar17, ±0x1400)`) — noticed only in passing,
NOT traced to confirm whether it's the SAME cell/mechanism `leverb-gate` characterized. Flagging the
address match, not a claim of identity.

## Related
[[reference_accord_0xc6cd0_exogenous_via_masons_formula_but_wired_into_path2_stage1_sign_open]] — the
finding this residual attaches to. [[accord-aggregator-reaches-motor-via-gp6acc-bridge]] — the "LAST
STRETCH" section this file's `gp-0x6b98` write re-confirms.
