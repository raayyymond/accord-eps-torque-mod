---
name: reference_accord_return_centre_dual_term_sign_and_dwell_relay_full_characterization
description: FUN_00036388/gp-0x6b62 (return-centre) sums TWO differently-signed terms sharing one peak-hold gate. Term 1's sign source gp-0x6abc is RAW gp-0x4f50 (zero filter lag, CORRECTS an initial mid-session assumption it was EMA'd). Term 2's sign is -sign(gp-0x6bf0) (CORRECTS the sibling constellation memory's "polarity trapezoid" framing). The dwell-relay on term 1's magnitude has NO true hysteresis (single threshold, symmetric-rate counter) and its cal (0xC627E=20) is virgin. gp-0x6bf0's own identity traces one hop short of closure (FUN_0003bd7c <- gp-0x4ee8 <- FUN_00065eda, resolver-shaped but not confirmed same reference frame as gp-0x4f50).
metadata:
  type: reference
---

# Return-centre's two summed terms — full sign/timing re-derivation, 2026-08-11 (`fw-return`, team-lead's A1/A2 pass)

Dispatched after team-lead connected this lane to a measured 6-9Hz anti-damping (`Re(Z)=-3375`) that is
NOT the PID. Explicit instruction: do not inherit prior characterizations, re-derive from raw assembly.

## `gp-0x6b62 = sVar8(sign from gp-0x6b64) + sVar13(sign from gp-0x6b5e)` [EVIDENCE, fresh disasm 0x36432-0x36506]

Both terms share ONE gating signal, `gp-0x6bda`, via each term's own LERP window (term 1:
`FUN_000360fe`, X=[-397,-192,140,294,384] Y=[0,2560,2560,717,0]; term 2: `FUN_000361c8`, freshly
byte-read this session, X=[-384,-128,128,294,384] Y=[0,4762,4762,717,0] — **both Y arrays always >=0,
confirmed by direct read, no sign flip in either table**).

## Term 1 sign source `gp-0x6abc` — CORRECTED mid-session, self-caught [EVIDENCE, `FUN_00041464` re-read]

Initially assumed EMA-filtered. Re-reading the EXACT program order in the decompile: the write
`*(gp-0x6abc) = sVar15` happens BEFORE `sVar15` is reassigned to the EMA'd value (`uVar16>>10`, which
instead goes to `gp-0x6abe`). **`gp-0x6abc = gp-0x4f50` directly — raw, unfiltered, zero phase lag**, in
the normal/valid-reading path. This actually corroborates (not contradicts) prior "gp-0x6abc is raw
motor rate" framing — the EMA'd sibling is `gp-0x6abe`, a separate cell.

## Term 2 sign source `gp-0x6b5e` — CORRECTS prior framing [EVIDENCE, fresh disasm `FUN_000361c8` 0x36240-0x36256]

```
r10 = LERP(gp-0x6bda, table@tp+0x76cc) * cal(tp+0x73c2, fresh-read=1024/Q10-unity) >> 10
r10 = r10 * gp-0x6752(polarity, boot-static +1)   -- scale only, doesn't set sign
if (gp-0x6bf0 > 0): r10 = -r10
gp-0x6b5e = r10
```
Since the LERP's `Y>=0` always: **sign(gp-0x6b5e) = -sign(gp-0x6bf0)**. The sibling-constellation memory
this session inherited from at first ("`gp-0x6b5e = LERP(gp-0x6bda)*polarity`", framing polarity as the
sign source) is **imprecise** — polarity is present in the formula but is boot-static +1 and never flips
sign; the real sign driver is `gp-0x6bf0` ("x"), which the OLD framing didn't even name.

## `gp-0x6bda`'s physical meaning, re-derived [EVIDENCE, `FUN_00036022`]

`gp-0x6bda = margin(x=gp-0x6bf0, UPPER=gp-0x6bd8, LOWER=gp-0x6bd6) - cal(tp+0x714c, or 0 if gp-0x67fe==2)`,
`margin = (x>0) ? x-UPPER : x-LOWER`. UPPER/LOWER are a confirmed non-decaying peak-hold of `gp-0x6bf0`
ITSELF (`FUN_00035d38`). **⇒ the shared activation window opens exactly when `gp-0x6bf0` sits near its
own most recent local extreme** — not near zero, near a PEAK of the rate-like signal that also sets both
terms' sign.

## `gp-0x6bf0`'s identity — ONE HOP SHORT OF CLOSURE [BELIEF for the final link]

`FUN_0003bd7c` (sole non-reset writer): `gp-0x6bf0` = a scaled, wraparound-corrected finite difference of
an unwrap-accumulator `gp-0x6cc4`, itself built from repeated deltas of `gp-0x4ee8`. `gp-0x4ee8`'s sole
writer, `FUN_00065eda`, has the SAME structural shape as the confirmed motor-resolver decode chain that
produces `gp-0x4f50` (bias-corrected differential sin/cos ADC pairs -> atan2-like decode -> wraparound
correction -> commutation-adjacent outputs) — **strongly suggestive it's the same resolver family, NOT
independently confirmed to share a sign convention with `gp-0x6abc`/`gp-0x4f50`.** All of
`FUN_00036022`/`FUN_000361c8`/`FUN_0003bd7c`/`FUN_00041464` are called from `FUN_0002214a`
(confirmed 1kHz) — no cross-task sample delay anywhere in this path, ruling that OUT as a phase source.

## The nonlinear gate is NOT reducible to a clean H(f) — worked the sinusoidal case by hand

For an idealized single-tone oscillation, the shared peak-hold window opens near `gp-0x6bf0`'s own local
extrema, but **sign(each term) continuously tracks its sign source throughout, independent of the
gating** — activation-near-a-peak does not by itself introduce a phase flip into anti-damping. A sign
flip needs either the LERP `Y` going negative (checked, never does, either table) or `gp-0x6bf0` being
OUT OF PHASE with the reference rate `Re(Z)` was measured against. **This reduces the entire anti-damping
question for this lane to the single unresolved link above** (does `gp-0x6bf0` share `gp-0x6abc`'s sign
convention). Recommended to team-lead: a telemetry bit comparing `sign(gp-0x6bf0)` vs `sign(gp-0x6abc)`
live during a 6-9Hz episode is cheaper and more decisive than a further static trace.

## The dwell-relay on term 1's MAGNITUDE — fully characterized, no true hysteresis [EVIDENCE]

```
window_open = |gp-0x6b64| < cal(0xC618A)=1024
counter += 1 if window_open (unless counter already > cal(0xC627E)=20, then holds)
counter -= 1 otherwise, floored at 0
snap_active(this tick) = counter_BEFORE_this_ticks_update > 20
sVar8 = snap_active ? 1024(fixed) : |gp-0x6b64|(tracking)
```
Single threshold, same test both directions, symmetric 1-tick/ms ramp rate both ways — a **rate-limited
sample-and-hold**, not a Schmitt trigger (no separate re-entry band). Snap magnitude: 0 to just under
1024 counts (directly in aggregator counts — this term feeds `gp-0x6b62` with no extra scale before the
aggregator sums it). Minimum round-trip timescale ~40-50ms (20-25Hz) — closer to grind-#1's band than
the 7.79Hz ratchet, though 7.79Hz's 64ms half-period has 3x the margin needed to fully engage/disengage
each half-cycle, so it isn't excluded by timing either.

**`0xC627E`=20 (dwell cap) IS a cal, and is VIRGIN**: `search_instructions("727e")` whole-image = 4 raw
hits, 3 branch-target-address text collisions (excluded, established false-positive class), **exactly 1
real access, `0x36444` inside `FUN_00036388` itself** — sole reader image-wide. `grep -l "C627E"
build_v*_tva.py` (all builds) = zero matches. Same for its window partner `0xC618A` and term 2's whole
table (`0xC66CC`/`0xC63C2`). **This is a cal-only lever on a genuine relay that no build has ever
touched** — NOT priced as a build (no GATE-1/2 review run), existence only.

## Related
[[reference_accord_return_centre_no_lkas_gate_rate_adaptive_governor_is_the_mechanism]] — the earlier
pass this session that closed the LKAS-magnitude-gate question and found the rate-adaptive governor.
[[reference_accord_fun36388_return_centre_traced_and_v69_bit5_inconclusive]] — the prior session's trace
this one corrects on term 2's sign source and firms up on term 1's (`gp-0x6abc` raw, not EMA'd).
[[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]] — source of the imprecise "polarity
trapezoid" framing for `gp-0x6b5e` this session corrects.
