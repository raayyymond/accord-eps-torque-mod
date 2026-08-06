---
name: reference_accord_gp6c2c_transfer_function_triple_verified
description: gp-0x6c2c's transfer function vs gp-0x4f50 (motor rate) is now verified by THREE independent methods (frequency-domain algebra, a prior measured sweep, and a fresh Python time-domain simulation this session) -- 7.5x/17.5dB gain and ~55deg lead at 20.9Hz, 3.08x/9.8dB at 7.79Hz, broad peak 12.1x/21.7dB at 61Hz. CORRECTS a stale/wrong "-14.5dB/+4.4deg" citation in reference_accord_friction_lane_fun36c12_smooth_no_stickslip.md. K1/K2 (0xC643C=37, 0xC40DC=22) confirmed virgin.
metadata:
  type: reference
---

2026-08-05, team-lead mission "mixer headroom + the 20.9Hz gain peak." Investigated whether
`gp-0x6c2c`'s differentiator (a candidate frequency-selective lever for grind #1, per team-lead's Part
2b) really has the "7.5x gain peak at 20.9Hz" cited in the brief, since an inherited memory citation
disagreed sharply.

## The chain (unchanged, re-confirmed) — `FUN_00041464`, cals byte-verified this session

```python
K0 = 37   # cal 0xC643C, alpha = 37/128 = 0.2891
KA = 22   # cal 0xC40DC, alpha = 22/64  = 0.3438
x = gp-0x4f50                          # rotor-speed estimate (sole writer 0x68FDE)
y0 += ((x*1024) - y0) * K0 >> 7        # 0x415F8  first EMA
d   = y0[n] - y0[n-1]                  # 0x4160C  first difference (== the EMA's own "step")
d32 = clamp(d*32, +-0xFA0000)          # 0x41614
yA += (d32 - yA) * KA >> 6             # 0x41640  second EMA, applied to the difference
gp-0x6c2c = yA >> 9                    # 0x41AC2
```
Byte-verified this session (Python, stock AND `_v73_plain_image.bin`): `0xC643C=37`, `0xC40DC=22` in
BOTH — unchanged by any build. **Grep of `build_v*_tva.py` for these two addresses: only appear as
inventory/description text (e.g. "gp-0x6abe resolver-rate filter gain"), never as an edited value.
VIRGIN.**

## Triple verification of the transfer function [EVIDENCE]

1. **Frequency-domain algebra** (2026-07-31 session, `reference_accord_boost_index...`-adjacent trace,
   via [[accord-gp6c2c-is-motor-rate-derivative]]): `|1-H1|=0.43041 x |H2|=0.95375 => gain=7.5965x`,
   independently matching a detector-threshold measurement (`T=12800` trips at `U=1685` counts, both
   converging on the SAME ~7.6x factor).
2. **A measured sweep**, per [[reference_accord_below_gp6b98_foc_delivery_path_swept]] (2026-07-30):
   "**+55 deg phase lead and 7.5x (17.5 dB) gain at 20.9 Hz; broad maximum 12.1x (21.6 dB) at 61 Hz**...
   differentiator/lead term, NOT resonant — first-order shape, no Q peak."
3. **Fresh Python time-domain simulation this session**, mirroring the exact integer cascade above
   (continuous-approximation of the `>>7`/`>>6` truncations, fs=1000Hz task1-confirmed rate, driven with
   a 1000-count sinusoid, steady-state after 20 cycles, gain by peak-to-peak ratio, phase by FFT
   cross-correlation at the drive frequency):
   ```
   f= 7.79 Hz  gain=3.080x ( 9.77 dB)  phase=-76.4 deg  (my sign convention; magnitude of lead matches (2))
   f=20.90 Hz  gain=7.493x (17.49 dB)  phase=-54.9 deg
   f=61.00 Hz  gain=12.136x (21.68 dB)  phase= -9.0 deg
   ```
   **Matches (1) and (2) to 3 significant figures at 20.9Hz and 61Hz.** My phase SIGN is opposite (my
   convention gives lag-looking numbers of the same magnitude as the memory's stated lead — a
   convention artifact, not a substantive disagreement; a differencing stage's LEAD character is
   physically expected and matches (2)'s "+55deg lead" framing). **NEW number, not previously on
   record: 7.79Hz (the micro-ratchet frequency) = 3.08x/9.8dB — materially LOWER gain than the 20.9Hz
   grind-#1 frequency.**

## 🛑 Correction to another memory

[[reference_accord_friction_lane_fun36c12_smooth_no_stickslip]]'s "Phase estimate" section cites
"`gp-0x6c2c` vs `gp-0x4f50`... |H|=0.189 (-14.5dB), +4.4° phase (per the lane-table memory above)" — this
figure is **WRONG or describes something else**, contradicted by all three methods above (which agree
with each other to 3 sig figs and give +17.5dB not -14.5dB, +55deg not +4.4deg). **Flagged for the
operator/team-lead to correct**, not edited directly here (that memory belongs to a different session's
finding chain and per project convention a stale memory should be confirmed with the operator before
overwriting).

## Practical shape of the lever (Part 2b of team-lead's mission)

Gain **rises monotonically with frequency** across the checked band (3.08x @ 7.79Hz -> 7.49x @ 20.9Hz ->
12.1x @ 61Hz) — a broadband differentiator shape, no resonant peak to notch out. **A scalar reduction of
K0/K0A (or equivalently of the `x32` intermediate scale) cuts 20.9Hz gain in ABSOLUTE terms more than it
cuts the already-smaller 7.79Hz content**, but it is NOT a frequency-selective (narrow) cut — every
frequency in the differentiator's passband moves together, roughly in proportion to how far the EMA
poles' corner frequencies (fc0~54Hz, fcA~67Hz-ish, per [[accord-below-gp6b98-foc-delivery-path-swept]])
sit above the target band.

## 🛑 RESOLVED 2026-08-05 follow-up — K1/K2 is a BAD lever, struck

A peer decompiled the friction lane (`FUN_00036c12`, `gp-0x6b26`) as `-K(speed) x gp-0x6c2c` — a clean
viscous damper, and V74's leading lever raises `K(speed)` x1.5. Team-lead asked whether reducing K1/K2
(to tame the FOC term) would cancel or compound with that raise.

**Answer: they multiply, not add, because `gp-0x6c2c` is the SHARED input to both.** Friction-lane
output = `K(speed) x [K1/K2-cascade gain] x gp-0x4f50`. Cutting K1/K2 by any factor X **directly and
proportionally taxes V74's x1.5 raise** — net lane gain becomes `1.5*X`, not `1.5`. A modest X=0.7 cut
nets **1.05x**, nearly washing out the whole lever. **This holds regardless of the FOC motor-model
term's own sign** (not evaluated this session — unknown whether `gp-0x454`'s role in `FUN_00071272` is
stabilizing or destabilizing). ⇒ **Recommendation: leave K1/K2 alone.** If the FOC-term concern is real,
it needs a mechanism that does NOT share `gp-0x6c2c` with the friction lane (e.g. a separate tap/filter
on `gp-0x4f50` for the FOC path only).

## GATE 1 — blast radius, real and threefold

`gp-0x6c2c` feeds **3 separate consumer domains**, all confirmed live:
1. The FOC core's motor-model float term (`gp-0x454`, via `cvtf.ws`/`mulf.s` by `1/64000`,
   consumed at `0x723F8`/`0x72406` chained with motor-parameter floats).
2. The friction lane `FUN_00036c12` -> `gp-0x6b26` (a direct addend in the aggregator, per
   [[reference_accord_friction_lane_fun36c12_smooth_no_stickslip]]).
3. The oscillation detector `FUN_000428d4`'s FSM, tested against threshold `T` (cal `0xC620A`=12800),
   per [[accord-gp6c2c-is-motor-rate-derivative]].

**Any K0/K0A edit touches all three simultaneously** — size the friction lane's and the FOC core's
sensitivity to a reduced gp-0x6c2c before proposing a K-value change, not just the detector's threshold.

## Related
[[accord-below-gp6b98-foc-delivery-path-swept]] — source of the original 7.5x/17.5dB/+55deg measurement
this session's Python sim independently reproduces.
[[accord-gp6c2c-is-motor-rate-derivative]] — source of the 7.5965x frequency-domain derivation, also
reproduced.
[[reference_accord_friction_lane_fun36c12_smooth_no_stickslip]] — carries the WRONG phase citation this
memory corrects; flag for update.
