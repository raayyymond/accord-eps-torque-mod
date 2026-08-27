---
name: reference_accord_fun2a93a_dead_code_correction_and_engagement_gate_catalog
description: CORRECTS reference_accord_gp69b0_authority_gate_and_fun42746_table_selector -- FUN_0002a93a is DEAD CODE (0 callers/xrefs, confirmed 2 methods, matches build_v37/v38's own "DEAD" annotation), not a live binary relay gate. The "live" claim mis-cited a correction about a DIFFERENT function (FUN_00028ea6/PATH-A's cal gain). Also: full catalog of confirmed-live engagement-gated mechanisms in the assist forward path (mode-table selector, arb ramp gain). 🛑 2026-08-12: item 3 (authority output-clamp collapse, gp-0x6966/0xC6AF0) STRUCK -- gp-0x6966 is identically 0 on every V31+ build per v54-flashed-authority-measured, so the clamp is permanently wide open and the collapse never occurs.
metadata:
  type: reference
---

# `FUN_0002a93a` is DEAD CODE — corrects a prior memory's misattributed citation (2026-08-12, `lane-weights-6bf`)

Dispatched for team-lead's "enumerate everything that changes on LKAS engagement" task. While assembling
the catalog, checked `reference_accord_gp69b0_authority_gate_and_fun42746_table_selector`'s claim that
`FUN_0002a93a` is "very much live" (a binary all-or-nothing gate: `if (gp-0x69b0==0 && gp-0x6805!=1) {
whole curve computation zeroed }`) before relaying it as a Q2 candidate.

## [EVIDENCE] The "live" claim does not hold up

That memory cited `reference_accord_patha_arb_is_live_not_inert_correction` as its support. Read that
correction fresh: it is about **`FUN_00028ea6`** (the real PATH-A arbitration function) and its cal gain
`0xC646C`, which had been misread as −1/inert in a 2026-05 session. It says nothing about `FUN_0002a93a`
having a caller — the two functions were conflated because `FUN_0002a93a`'s alleged outputs
(`gp-0x6b2e/32/34/36`) were assumed to feed the same downstream chain PATH-A does.

**Fresh check this session**: `get_function_callers(0x2a93a)` and `get_xrefs_to(ram:2a93a)`, both on
`code.bin` — **zero callers, zero xrefs, both methods.** This matches `builds/v18_v49/build_v37_tva.py`/
`builds/v18_v49/build_v38_tva.py`'s own long-standing annotation, present since those builds: `"0x2a97a FUN_0002a93a
(DEAD: 0 callers/xrefs/ptrs)"` and `"NOTE: FUN_0002a30e / FUN_0002a93a are DEAD out-of-line copies; the
LIVE logic..."` — a fact that was already on record in the build scripts and simply never cross-checked
against the newer memory's claim.

**Strike `FUN_0002a93a` as an engagement-gate candidate.** The correction file's actual, valid claim
(PATH-A/`FUN_00028ea6` is live) stands untouched — only the inferential leap to `FUN_0002a93a` was wrong.

## Catalog of CONFIRMED-live engagement-gated mechanisms (synthesis, mostly reusing prior sessions' work)

1. **Mode-table selection, `FUN_00042746`** — two independent axes: `gp-0x67f6` (PHASE) flips on a
   *settled* `gp-0x6806`/`gp-0x69b0` transition, selecting disengaged↔engaged column pairs (24↔26 or
   25↔27 for this vehicle, confirmed TVCA4 per [[reference-accord-car-is-tvca4-mode-24-26]]);
   `gp-0x67e2` (SELECTOR, tracks `gp-0x6733`, producer unidentified) picks column A vs B. Selects which
   FactorB/C/D/E table row every base-assist producer reads. Stock ships 24≡26, 25≡27 byte-identical.
   🛑 Modes 26 AND 27 are BOTH engaged columns (Honda's pairing 24↔26, 25↔27) — an edit to only 26 is a
   silent half-application, per [[accord-mode-27-is-a-second-engaged-column]] (cost V83a a clean result).

2. **Arb ramp gain, inside `FUN_00028ea6`** — `iVar34 = (iVar34 * gp-0x69b0) >> 15`, ALWAYS applied, a
   continuous Q15 multiply by the LKAS engage-ramp authority (0 disengaged → 32768 fully engaged). The
   preceding deadband+sign-relay (cal `0xC61B8`=102, gated `gp-0x6806==0`) is MEASURED bypassed 96.26% of
   engaged driving, 0.011 transitions/s — ruled out as a fast mechanism, per
   [[reference-accord-deadband-signgate-eliminated-on-car]]. What survives is the ramp gain itself: a
   real, live, always-applied engagement-proportional continuous gain (not a relay) on this one arb term.

3. 🛑🛑 **STRUCK 2026-08-12 — Authority output-clamp collapse, `gp-0x6966`/`0xC6AF0` in `FUN_0003a382`.**
   Q15 LERP (X=[0,3277,3604,19661,32768], Y=[32768,32768,0,0,0]) scales the PID's own output bound;
   originally read as a genuine dead-zone/relay that could be muting the PID during sustained engaged
   holding. **Refuted by `memory/builds/v54-flashed-authority-measured.md` (kit `memory/`), from V54's own
   on-car probe (route `1b`, fault-free): `gp-0x6966` (the soft-EME windup magnitude) is identically 0
   on every V31+ build — V31's boost floor makes the windup that would raise it unreachable.** With
   authority pinned at 0 the LERP sits on its `X=0` knot (`Y=32768`) — **the clamp is permanently wide
   open; the collapse this entry describes never occurs on anything this kit flies.** The PID is never
   muted through this mechanism. Lesson: grep the kit's `memory/` for a candidate's OWN cal/variable
   before ranking it, not after — same class of error as the `FUN_0002a93a` correction above, caught by
   team-lead rather than by me this time.

4. **`gp-0x67fe` (LKAS engage-SM state) — mostly NOT a clean discriminator.** 40+ readers, but reads 1
   during ordinary manual power-steering-on driving too — most branches testing `∈{1,2}` don't separate
   engaged from manual. Flag so it isn't mistaken for an engagement flag.

5. **r24/r26 — read ZERO LKAS-domain signals**, confirmed by full fresh decompile of `FUN_0003aa2c`. No
   cal-only LKAS fork possible (`gp-0x4f62`'s sole physical source, the torsion-bar sensor, has no
   upstream tap that separates driver torque from motor-reaction torque). A code-level gate is
   structurally feasible (the flags are fresh by this point in the tick) but not existing — would need a
   new 1kHz-path code-cave insertion.

## Related
[[reference_accord_gp69b0_authority_gate_and_fun42746_table_selector]] — the file corrected here (its
`FUN_00042746` finding stands; its `FUN_0002a93a` claim does not).
[[reference_accord_patha_arb_is_live_not_inert_correction]] — the correction that was mis-cited.
[[reference_accord_mode_selector_fun42746_closed_confined_to_10_11]] — closes the TVAA1 framing (superseded
by TVCA4, see [[reference-accord-car-is-tvca4-mode-24-26]] in the kit's `memory/`).
[[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]] — the r24/r26 exhaustive check reused here.
