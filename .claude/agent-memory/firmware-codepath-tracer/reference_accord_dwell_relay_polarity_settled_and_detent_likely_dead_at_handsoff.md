---
name: reference_accord_dwell_relay_polarity_settled_and_detent_likely_dead_at_handsoff
description: Settled a cross-agent polarity contradiction on FUN_00036388's dwell-relay window test via fresh decompile (p-code-derived, not hand-parsed mnemonics) plus 3 corroborating prior sessions -- window_open = |gp-0x6b64| < cal(0xC618A)=1024 (opens on SMALL signal), confirming the DETENT reading, not a saturation-limiter reading. But gp-0x6b64 = Y1(gp-0x6bda) * gp-0x6abc(raw rate), Y1 always >=0 and ZERO when gp-0x6bda is outside [-397,384] -- and a prior memory's hands-off gp-0x6bda figure (~9262) sits far outside that window, which would make the "detent" a FLAT -1024 CONSTANT bias (not a relay at all) during hands-off/light driving specifically. Flagged as the likely clean kill, pending re-verification of the 9262 figure and whether it holds during active steering too.
metadata:
  type: reference
---

# Dwell-relay polarity settled + detent viability question — 2026-08-11, team-lead's B-series pass

## Polarity, settled [EVIDENCE, decompile_function(0x36388), p-code-derived]

```c
sVar3 = *(gp-0x6b64);  iVar11 = |sVar3|;
iVar17 = cal(tp+0x718a=0xC618A) = 1024;
if ( iVar11 < iVar17 ) {              // Ghidra's own overflow-safe signed-LT idiom
    if (counter <= cal(0xC627E)=20) counter++;
} else if (counter != 0) counter--;
...
if ( 20 < counter ) { iVar11 = 1024; }   // SNAP, unambiguous, no flag-mnemonic involved
sVar8 = iVar11;
```
**`window_open = |gp-0x6b64| < 1024` — opens on SMALL |gp-0x6b64|.** This CONTRADICTS a same-day claim
from another agent (`counter ramps while |gp-0x6b64| > 1024`) and CONFIRMS this agent's own original
reading. Corroborated by: (1) an independent assembly-level control-flow trace done earlier the same
session, tracing branch targets directly; (2) THREE PRIOR, INDEPENDENT sessions already on file
(2026-08-04 original trace, 2026-08-05 red-team pass, 2026-08-05 round-2 — see
[[reference_accord_fun36388_return_centre_traced_and_v69_bit5_inconclusive]]) all re-deriving the same
polarity independently, predating today. A hand-attempted raw-byte CMP-direction decode this session gave
the OPPOSITE answer and was explicitly NOT trusted — reconstructing V850's Format-I field layout and CMP
subtraction convention from memory under time pressure is exactly the failure class this kit's own rule
warns about; the decompile is the primary, methodologically-correct source here, not a fallback.

## Consequence: `gp-0x6b64` is a torque-margin-GATED rate, not a pure rate [EVIDENCE]

```
gp-0x6b64 = -clamp( Y1(gp-0x6bda) * gp-0x6abc(RAW motor rate, confirmed unfiltered this session) * 1024 >>10, ±2800 )
Y1 = LERP(gp-0x6bda, X=[-397,-192,140,294,384], Y=[0,2560,2560,717,0])   -- always >=0
```
`|gp-0x6b64| < 1024` (the outer window test) is satisfied via TWO physically distinct routes: (a) genuine
low rate while `gp-0x6bda` is inside `[-397,384]` — the detent story; (b) `gp-0x6bda` simply sitting
OUTSIDE `[-397,384]`, making `Y1=0` and `gp-0x6b64=0` **regardless of rate**.

## The likely clean kill, at hands-off — [BELIEF, resting on a cited-not-reverified prior number]

A prior, unrelated session's memory (`reference_accord_rate_lane_v62_to_v69_gain_arc.md`) recorded
`gp-0x6bda`'s typical HANDS-OFF value as **≈9262** — far outside `[-397,384]` (24x the upper edge). If
still accurate: during hands-off/light driving, `Y1=0` persistently ⇒ `gp-0x6b64=0` persistently ⇒ the
window is ALWAYS open ⇒ the dwell counter climbs to 21 within 21ms and HOLDS there (no decay while the
window stays open) ⇒ `sVar8` snaps to 1024 and STAYS flat. The decompile's own sign step
(`if (gp-0x6b64 < 1) sVar8 = -sVar8;`) then fires (0 < 1 is true) ⇒ **term 1 settles at a flat −1024
CONSTANT bias in this regime — not a relay, not a detent.** This is the exact "clean kill" pattern
team-lead pre-registered as the most likely refutation, and the arithmetic supports it — **but only for
the hands-off case the cited number describes.** NOT resolved: whether `gp-0x6bda` moves inside the
window more often during ACTIVE steering (where torque excursions/returns would put `gp-0x6bf0` near its
own recent peak more often) — that is the regime the operator's micro-ratcheting complaint is actually
about, and the ≈9262 figure doesn't speak to it. Recommended: a telemetry bit on `gp-0x6bda` (or
`gp-0x6bda ∈ [-397,384]`) during an active-steering episode, cheap and decisive.

## Related
[[reference_accord_return_centre_dual_term_sign_and_dwell_relay_full_characterization]] — the fuller
characterization this note narrows (hysteresis shape, snap magnitude, cal virginity — all still stand).
[[reference_accord_fun36388_return_centre_traced_and_v69_bit5_inconclusive]] — source of the three prior
polarity re-derivations and the ≈9262 hands-off figure this note cites but does not re-verify.
