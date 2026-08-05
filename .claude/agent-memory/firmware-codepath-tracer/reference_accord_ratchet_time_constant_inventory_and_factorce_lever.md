---
name: reference_accord_ratchet_time_constant_inventory_and_factorce_lever
description: Full inventory of firmware time constants/poles with phase computed AT 7.793 Hz (the ratchet's own frequency, not 21 Hz) -- FUN_00036682's Lane D EMA is the single largest lag (-81.8 deg, corner 0.93 Hz), boost-amplitude blend second (-64.1 deg, corner 1.6 Hz). Confirms FactorC/FactorE (V47's damping restore) is STILL STOCK on V70/current lineage by fresh byte read. 0xC63D2 (Lane D coeff) confirmed NEVER edited by any build (assertion-only). No ~128ms/64ms fixed timer found anywhere -- negative result. Flags an address-collision risk in FUN_000360fe's gp-0x6bda LERP (tp+0x7970 collides with the established 0xC7970 mode-indexed pointer array) -- left UNRESOLVED, not guessed.
metadata:
  type: reference
---

**Session: 2026-08-04, dispatched by team-lead to hunt the 7.79 Hz ratchet's loop element(s).** Full
report sent via SendMessage; this memory captures what should outlive that specific message.

## Headline: phase inventory computed AT THE RATCHET'S OWN FREQUENCY (f0=7.793 Hz), not 21 Hz

Every prior session in this kit computed phase at 21 Hz (the older vibration target) or left the ratchet's
own poles unevaluated. This session ran the exact discrete z-domain formula
`phase(f) = -atan2(p*sin(w), 1-p*cos(w))`, `w=2*pi*f/fs`, for every known coefficient at f0=7.793 Hz:

| element | coeff | fs | corner | phase @ f0 |
|---|---|---|---|---|
| **Lane D `FUN_00036682`→`gp-0x6b46`** (11th aggregator summand) | `0xC63D2`=6/1024 | 1000 Hz | 0.93 Hz | **-81.8 deg** (largest found) |
| Boost-amplitude Y1/Y4 blend | `0xCA06C`→`0xD2006`=102/1024 | 100 Hz (task5) | 1.6 Hz | **-64.1 deg** |
| Lane B `FUN_000352b4` output IIR (open state, the operative one) | `0xC6382`=41/2048 | 1000 Hz | 3.2 Hz | -66.2 deg |
| Common-mode rate bus `gp-0x6abe`/`gp-0x6ac0` (`FUN_00041464`) | `0xC643C`=37/128 | 312.5 Hz | 14.4 Hz | -20.4 deg |
| Lane C input EMA `gp-0x6c2c` | `0xC40DC`=22/64 | 312.5 Hz | 17.1 Hz | -16.2 deg |
| `gp-0x6b9a`/`gp-0x6ba6` producer (2-stage cascade) | `0xC63BA`=0.5 x2 | 1000 Hz | 79.6 Hz | -5.6 deg (negligible) |
| `FUN_0003a382` P/I/D lane `gp-0x6ad4` | see below | 1000 Hz | -- | **+8 to +14 deg (LEADING)**, near-flat -- P-dominated at 7.8Hz, NOT the +42..55 deg seen at 21Hz |
| Task-5 100Hz ZOH (boost/damping producers) | -- | 100 Hz | -- | avg 14.0 deg, worst 28.1 deg |
| Task-1 1kHz single-tick staleness | -- | 1000 Hz | -- | 2.8 deg (negligible) |

**Lane D is the standout new finding**: [EVIDENCE, fresh decompile this session of `FUN_00036682` +
`get_xrefs_to` confirming its sole caller is the aggregator `FUN_0003aa2c` (task 1, 1 kHz)] its closure
is a genuine single-real-pole EMA `y[n]=y[n-1]*(1-2a)+a*x[n]`, a=6/1024, DC gain exactly 0.5, confirmed at
the instruction level (the accumulator recurrence `iVar14 += ((iVar8*1024-iVar14)*6)>>10` on a 32-bit
Q10 state at `gp-0x37ac`, output `gp-0x6b46`). This reproduces `build_v56_tva.py`'s own independently-
computed corner (0.933 Hz, from a DIFFERENT investigation ruling this lane out as a flat-21Hz carrier) —
good cross-validation, but nobody had evaluated it at 7.8 Hz before this session.

## `0xC63D2` (Lane D's coefficient) confirmed NEVER edited by any build [EVIDENCE, grep of all build_v*_tva.py]

Appears only inside stock-value ASSERTIONS in `build_v56_tva.py:186`, `build_v62_tva.py:333`, and 6
other build scripts — every one asserts it is UNCHANGED from V55/stock. Genuinely untested as a lever,
not merely unflashed. Candidate: raise it to push the corner above 0.93 Hz and cut the -82 deg/-18.5 dB
lag it contributes at 7.8 Hz. NOT recommended over the FactorC/E lever below — its role is [OPEN]/
[INFERRED] in the golden model, output magnitude is modest (DC gain 0.5 of a +/-512-clamped error), and
unlike FactorC/E it has zero on-car signal in either direction. Blast radius NOT re-swept this session
(GATE 1 work still needed before building).

## FactorC/FactorE (V47's damping-restore lever) — CONFIRMED STILL STOCK on the current lineage

Fresh byte read this session, `_v70_plain_image.bin`: FactorC `0xD27BC`(m10)/`0xD27D0`(m11) Y[0]=0;
FactorE `0xD27F8`(m10)/`0xD280C`(m11) Y[0]=0 — both byte-identical to stock `code.bin`. **V47's damping
restore is NOT carried by any build in the current lineage.** V47 itself (flashed) opened both:
FactorC Y[0] 0->235/234 (mode10/11), FactorE Y-row (0,140,539,927)->(700,750,800,927) both modes.
Operator result on V47: *"marginally quieter at 5 mph, no effect in motion"* — **evaluated only against
the 21 Hz vibration, before the ratchet existed as a characterized target.** Never evaluated against the
ratchet specifically. This is the strongest lever candidate this session surfaced: removes the ONLY two
multiplicative zero-gates on the base-assist damper (§ FactorC keyed on voted SPEED, X0=2240 counts=
34.97 km/h per the corrected `gp-0x6a5e` identity; FactorE keyed on motor rate, X0=60 counts), at exactly
the ratchet's speed/rate window. STATE.md §8 already scopes this as deferred, own single-variable drive —
this session's contribution is (a) confirming it's still off the car, (b) the exact byte-level lever spec,
(c) making explicit that the V47 on-car result speaks to the WRONG symptom, not to "already tested and
null" for the ratchet.

## No ~128ms (7.8Hz) or ~64ms fixed timer anywhere [EVIDENCE, negative result]

Checked every counter/timer/dwell/debounce on record: Lane A debounce (21 ticks=21ms), Lane A ramp
(~993 ticks~1s), STEER_STATUS=4 dwell (100 ticks=100ms, one-shot not periodic), assist-ramp SM
(`tp+0x74d1`=10 -> 100 ticks/state @ 100Hz = 1s/state x4 states, one-way engage ramp). Nothing lands near
128ms or 64ms. Supports: the ratchet frequency is set by loop phase/plant dynamics, not a firmware clock
artifact — consistent with its measured speed- and rpm-invariance.

## Quantiser/relay inventory at creep hands-off — only ONE live relay found, and it's dissipative

Lane A's own relay (`gp-0x6b62 = sgn(S)*1024` once the 21-tick debounce saturates) is the one true
bang-bang element reachable at the ratchet's operating point (21ms << 128ms period, plausible to sustain).
But it always shares S's sign (net-damping by construction, per [[reference-accord-four-unprobed-lanes-abcd-solved]])
so it is an amplitude-limiter, not an energy source. Lane A<->B coupling (2x pole step at
`\|gp-0x6b62\|<=8192`) is NOT reachable — measured max 5786 (V69 probe) never crosses 8192. FactorC/E are
static zeroes during the ratchet (speed doesn't cross 35km/h mid-cycle), not dynamic discontinuities.
r24/r26 kill-window gate not reachable hands-off (margin ~9262, 24x clear). `FUN_00042af8` shaper slew +
deadband (`0xC61D6`=0, `0xC6424`) RULED OUT — slew=0 freezes the lane rather than creating a dynamic cut
(already on record as a rejected lever, re-confirmed stock this session).

## OPEN: `FUN_000360fe`'s LERP over `gp-0x6bda` — address-collision risk, NOT resolved

`FUN_000360fe` (producer of Lane A's `S` term, gate = `-(LERP(gp-0x6bda)*gp-0x6abc)>>10`) was decompiled
fresh this session. Its table appears to span `tp+0x795e..tp+0x7970`, BUT `tp+0x7970 = 0xC7970` is
independently and freshly confirmed (raw byte read, `0xC7950-0xC79B0`, mode10 slot reproduces the
established `0xD20C0` exactly) to be the START of an UNRELATED mode-indexed pointer array (LERP5/
ASSIST_CEILING). This means the naive "table spans to tp+0x7970" reading is very likely wrong about its
upper bound — I stopped rather than guess a load-bearing shape claim. **This is the most promising open
thread for the "gain high near zero driver torque" asymmetry question** (mission item 4) — if resolved
properly (apply the count-based LERP-struct-field convention from
[[reference_accord_gp6bbe_baseline_fsm_and_lerp_struct_solved]]) and the LERP turns out high near
`gp-0x6bda`'s hands-off value, rolling off toward the driver's peak-torque envelope, it would be a SECOND
independent "gain high hands-off, rolls off with grip" mechanism alongside the already-known r24/r26 gate.
**Next step: decompile the LERP-struct walker properly, don't re-attempt a quick address-arithmetic read.**

## Related
[[reference-accord-four-unprobed-lanes-abcd-solved]] — source of Lanes A/B/C/D's base characterization,
reused and extended to 7.8 Hz this session.
[[reference_accord_task5_rate_resolved_and_feedforward_insertion_point]] — task-5 100Hz rate, reused for
the boost-amplitude-blend and ZOH figures.
[[reference_accord_gp68ad_field_dead_and_gp6d78_bit15_one_way_state4_cycle_refuted]] — the FactorC byte
values this session's read reproduces exactly (independent method, same numbers).
