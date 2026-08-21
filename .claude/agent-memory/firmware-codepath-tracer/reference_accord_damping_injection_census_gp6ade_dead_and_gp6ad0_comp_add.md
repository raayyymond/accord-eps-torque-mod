---
name: reference_accord_damping_injection_census_gp6ade_dead_and_gp6ad0_comp_add
description: Full census of every gp-0x6b94 aggregator addend for rate-proportional damping injection sites. gp-0x6ade is a permanently-dead unit-gain aggregator slot (zero writers, two methods). NEW comp-add-stage term gp-0x6ad0/FUN_000456a4 found downstream of the aggregator, likely dead in the micro regime. Standing structural fact: no cal gain table anywhere in this census carries an independently-settable sign -- every LERP Y-array read is ld.hu (unsigned); sign always comes from global pol or the natural sign of a physical difference.
metadata:
  type: reference
---

# Damping-injection-census session, 2026-08-21 (orchestrator mission, siblings biquad-structure/boost-pricing)

Full census of `FUN_0003aa2c`'s (the aggregator) 10 addends plus the governor->comp-add->shaper chain,
for the orchestrator's "where could a cal-only -K*rate damper be injected" question. GhidraMCP, stock
`code.bin`, this session unless [RELAYED]. Companion to
[[reference_accord_gp6bbe_k1_ratelane_full_retrace_and_sign_disqualification]] which covers gp-0x6bbe in
depth.

## The aggregator formula, re-confirmed fresh (matches the orchestrator's brief exactly)

Fresh `decompile_function(0x3aa2c)` confirms byte-for-byte:
```
gp-0x6b94 = clamp( FUN_00036682()
      + gp-0x6ade*zr(1024)  + gp-0x6b4c*zr(10240) + gp-0x6ad4*zr(10240)
      + gp-0x6b62*zr(8192)  + gp-0x6b26*zr(1024)   + gp-0x6bbe*zr(2048)
      + gp-0x6bd0*zr(2048)  + gp-0x6b86*zr(12288)
      + clamp(pol*X_r26,±0x2000)   # -> gp-0x6adc (r26)
      + clamp(pol*X_r24,±0x2000)   # -> gp-0x6ada (r24)
      , ±0x2800 )
```
`gp-0x67ac` gate (which branch: the "else" full-sum path vs. a suppressed variant) confirmed reads 0 in
practice per [[reference_accord_gp67ac_resolved_zero_and_path1_always_live]] [RELAYED] -- the full-sum
path above is the live one.

## 🛑🛑 NEW: `gp-0x6ade` is a permanently-dead unit-gain aggregator slot

Zero writers, confirmed **TWO independent methods**: `search_instructions operand_pattern="-0x6ade"` (and
the broader `"-0x6ad"` sweep covering the whole 6ad0-6ade family) returns only the ONE read at `0x3aa48`
inside `FUN_0003aa2c` itself; a raw Python LE16 disp16 byte scan over the full 1 MB image found one
apparent second hit at `0x793D8`, **proven a false positive** via `disassemble_bytes` dry-run — it is two
unrelated 2-byte `sld.w` short-form instructions (`sld.w 0x70,ep,r11` then `sld.w 0x44,ep,r18`) whose
concatenated trailing bytes coincidentally match the `-0x6ade` disp16 pattern (the
[[reference_v850_ep_relative_short_format_aliasing_trap]] class, confirmed recurring).

**Every neighboring cell has exactly one confirmed writer** — `search_instructions operand_pattern="-0x6ad"`
gives one hit each for `6ad0`(`FUN_000456a4`), `6ad2`(`FUN_00045a20`), `6ad4`(`FUN_0003a382`),
`6ad6`(`FUN_00037fe6`), `6ad8`(`FUN_00041d56`), `6ada`/`6adc`(`FUN_0003aa2c` itself, r24/r26). **`6ade` is
the one gap in an otherwise fully-populated, densely-packed cluster of legitimate SW state cells.**

**BELIEF (not provable from a ROM-only image — RAM content isn't in `code.bin`):** if this region is
boot-zeroed `.bss` like the rest of this state cluster (plausible, given the density of legitimate,
well-characterized neighbors — this is NOT the `gp-0x1500` I/O-mailbox region, which is a completely
different low address range), `gp-0x6ade` reads 0 forever, meaning the aggregator's
`+gp-0x6ade*zr(±1024)` term contributes exactly 0 in every build including stock, always.

**If confirmed live: this is the cleanest cave-injection target found in the whole census** — a
pre-mapped, unit-gain (weight=1, no rescale needed), zero-current-consumer RAM cell already wired directly
into the torque-command sum, inside a window (±1024) that comfortably covers the orchestrator's stated
target dose (~8-20 counts). **Per doctrine this is NOT GATE-1-clear yet** — static clearance alone has
failed before in this kit (`gp-0x1500` passed both static methods and still failed on-car). **What would
close it: a live probe that writes a sentinel value to `gp-0x6ade` and confirms (a) it holds across
multiple ticks without being overwritten, (b) no DTC/fault fires, (c) telemetry shows it actually reaching
`gp-0x6b94` at the expected ±1 weight** before any cave design commits to it.

## 🛑 NEW: `gp-0x6ad0`/`FUN_000456a4` — a second velocity-opposing term, downstream (comp-add stage)

Not in the orchestrator's original 10-addend list — found while tracing the confirmed
`gp-0x6b94 -> governor -> gp-0x6ace -> comp-add -> gp-0x6acc -> shaper` chain [RELAYED chain, established].
`FUN_0004503c` = the governor (writer of `gp-0x6ace`, [RELAYED]). `FUN_000456a4` = comp-add: fresh
decompile shows
```
gp-0x6ad0 = [gate: uVar13(angle-scheduled threshold, table tp+0x7834 family = 0xC6832-3C) < gp-0x6ac0
             (electrical rate)] ? -sign(gp-0x6abe)*[(gp-0x6ac0-threshold)*cal(tp+0x7204=0xC6204=3072)>>10,
             clamped by a SECOND angle-LERP (tp+0x77d4 family = 0xC66D2-DE)] : 0
sVar10 = gp-0x6ace[governor out] + gp-0x6ad0
gp-0x6acc = sVar10   (feeds the shaper) — guarded by a shadow-lockstep AND an unrelated CRC-magic
             anti-tamper branch (`cmp ...==0x49d6b173 && tp+0x74ba==-0x17`) that applies a DIFFERENT
             /1000 rescale on match — not chased further, flagged for GATE-1 caution near this address.
```
Same "negate if motor-rate(`gp-0x6abe`)>0" idiom as the established `FactorC/E` damper (`FUN_00034350`) —
structurally a genuine damper shape (rate-threshold-gated, velocity-opposing).

**BELIEF, activation likely unreachable in the stated regime, NOT fully re-verified this session:** byte-
read the first angle-LERP's breakpoints at `0xC6832` = 3800/4000/4150/5000/3037/1000 (ushorts). At the
established `gp-0x6a10` scale of **0.1°/count** [RELAYED, `memory/accord-measured-rack-ratio-and-two-
instrument-traps.md`, "X (0.1 deg/ct): 0 340 640 850 1000 1200 ... 4776"], these breakpoints are
**380-500°** of column angle — deep full-lock territory. The OUTER gate compares this angle-scheduled
value (1000-5000 raw counts) directly against `gp-0x6ac0` (electrical rate, established scale
**~4.7121 ct/(deg/s)** [RELAYED, not re-derived this session]) — implying an activation threshold of
**roughly 212-1061°/s**, far above the orchestrator's stated 13-50°/s regime. If this reading holds,
`gp-0x6ad0` is dead in the regime that matters, same disqualifying class as `gp-0x6bd0`/`FactorD`.
**What would close it:** re-verify `gp-0x6ac0`'s current scale directly (not relayed), and disassemble the
actual comparison branch (I did not confirm the "small angle needs bigger rate" direction from the branch
condition itself, only inferred it from the Y-value ordering in the table).

The SECOND angle-LERP (`0xC66D2` family, breakpoints 128/294/384 raw counts = **12.8°/29.4°/38.4°**,
saturating at Y=4762) sets the SHAPE/ceiling once activated — much closer to your regime, but gated behind
the outer rate check above.

## Reconciles gp-0x6ba6/gp-0x6b9a with existing record (nothing new, confirms and connects forward)

Independently re-traced `FUN_0003b66a` (fresh decompile) before finding `memory/accord-gp6ba6-is-the-
boost-amplitude-index.md` and `accord-c63b8-8hz-bandpass-is-a-rectified-boost-index.md` already fully
solved this: input = raw motor rate `gp-0x6abc`, FIR stage confirmed identity (`0xC4018/1C/20` =
1.0/0.0/0.0, re-verified this session — byte read matches exactly), torque-derivative correction
confirmed DISABLED stock (`cal(0xC64BE)=0`, **new byte-read confirmation this session**), cascaded 2-stage
EMA (`0xC63B4=51`->8.13Hz, `0xC63B8=41`, both re-verified unchanged this session) is a real ~8Hz band-pass-
shaped element, then FULL-WAVE RECTIFIED (`gp-0x6ba6=|gp-0x6b9a|`) before use as a LERP index into
boost-amplitude tables. **Already REFUTED FIVE WAYS as a damper site by the existing record — nothing new
to add.** New contribution: confirmed this feeds `gp-0x6bbe` only as an AMPLITUDE SCALE (`blendedMagnitude`
in the K1 chain, see the companion memory), not as the phase-carrying value — so the "rectification kills
phase" refutation does NOT transfer to `gp-0x6bbe` itself, only to the boost-index's own direct consumers.

## 🛑🛑 Standing structural fact — no local sign control found ANYWHERE in this census

Every rate/derivative-flavored LERP or gain table read in this entire census uses `ld.hu`/`sld.hu`
(unsigned halfword): `gp-0x6bbe`'s K1 (`0xD200C`), r24/r26's mode24/26 tables (`0xD6A9C.../0xD7A88...`,
Y-values all positive on read [RELAYED]), `gp-0x6ad4`'s D-term gains inside `FUN_0003a382`. **Sign is
carried EITHER by global `gp-0x6752` (pol, forbidden to touch — global) OR by the natural sign of a
computed physical difference** (`rate_error = baseline-angle_rate` for `gp-0x6bbe`; the torque-tracking
error for `gp-0x6ad4`'s D-term). **Writing any of these gain tables negative does not flip the term's
sign — it zero-extends into a huge wrong-magnitude positive gain and corrupts the interpolation.** This
appears to be a firmware-wide convention, not a per-lane accident — record it as a standing expectation
for any future cal-only sign-flip proposal on a gain table in this image: check the load mnemonic
(`ld.h` vs `ld.hu`) before assuming a negative write will do what you want.

The only UNCONDITIONAL (always-on) sign flips found in the whole census are `gp-0x6bd0`'s and
`gp-0x6ad0`'s `if (motor_rate>0) negate` idiom — genuine dampers structurally, but **not cal-settable
(the flip is baked into the arithmetic, not behind a cal byte) and both are dead in the regime that
matters** (established for `gp-0x6bd0`; BELIEF, pending re-verification, for `gp-0x6ad0`).

## Part C answer this session reached

**No site passes all four of: (i) independently-settable sign, (ii) reachable dose, (iii) no dead zone in
the micro regime, (iv) ≤2 readers.** `gp-0x6bbe`/K1 passes (ii) and (iii), comes close on (iv) (4 readers,
well-characterized), and is the best-instrumented rate lane found (genuinely unfiltered on
`gp-0x6a56`/steering-column angle rate) — but fails (i) for the structural reason above. r24/r26 remains
the only LIVE rate lane and is already at V88's measured optimum, still pumping, with the 229° phase
discrepancy [RELAYED] still open. `gp-0x6ade` is a promising CAVE site (not a cal-only lever) pending a
live-write probe.

See [[reference_accord_gp6bbe_k1_ratelane_full_retrace_and_sign_disqualification]] for the gp-0x6bbe deep
dive, [[reference_accord_r24r26_live_gain_is_default_lerp_and_phase_discrepancy]] for the r24/r26 state,
[[reference_accord_gp6b26_closed_both_directions_v94_aborted]] and
[[reference_accord_driver_side_inertia_hypothesis_refuted_synthesis]] for why `gp-0x6b26` is closed.
