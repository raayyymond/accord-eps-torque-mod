---
name: reference_accord_fun38148_six_lane_identity_and_gp6a10_producer
description: FUN_00038148 Stage-1's six lanes fully identified by address (gp-0x6b4e and gp-0x6b46 were previously unnamed) -- gp-0x6b4e is written by the SAME mixer instruction pair as gp-0x6b4c (LKAS), gp-0x6b46 is a torque-sensor-domain term with its OWN final stage a <1Hz EMA (structurally incapable of 18-24Hz content). Also: FUN_0003fc16 (gp-0x6a10's producer) decompiled fresh -- confirms structurally it contains no reference to any commanded/target/LKAS quantity, only sensor-domain inputs, corroborating the "absolute angle not tracking error" identity from a second, independent method.
metadata:
  type: reference
---

# `FUN_00038148` six-lane identity + `gp-0x6a10` producer structural confirmation (2026-08-09, `lever-hf`)

Dispatched by team-lead to settle whether Path 2's 18-24 Hz content (coherence² = 0.310 with the column,
the tightest band in the whole spectrum per V88's H2 result) comes from friction/damper/boost or from
the diluted LKAS echo — decides whether `0xC63AC` is a clean lever or a disguised gain cut.

## The six Stage-1 lanes, `FUN_00038148` (`0x38148`), fresh decompile

All six weights `tp+0x73a0..0x73aa` (=`0xC63A0`..`0xC63AA`) = **1024 (unity)**, confirmed on record —
no structural up/down-weighting. `get_xrefs_to` on both new addresses returned **zero hits** (a fresh
instance of the gp-relative xref blind spot); `search_instructions operand_pattern=` found the real
sites.

| gp offset | weight cal | writer | physical identity |
|---|---|---|---|
| `gp-0x6b4e` | `0xC63A8` | `0x27466`, inside `FUN_00026c80` (**the mixer**) — 8 bytes from `gp-0x6b4c`'s own write at `0x27458`/`0x27466` in the SAME function | **LKAS-class** [BELIEF: co-located with `gp-0x6b4c` in the mixer, not independently re-traced for its own bandwidth this session — inherits the ~1-5Hz LKAS-lane low-pass ONLY BY INFERENCE] |
| `gp-0x6b4c` | `0xC63AA` | mixer (established prior record) | LKAS (established) |
| `gp-0x6b26` | `0xC63A6` | `FUN_00036c12` | FRICTION (established) |
| `gp-0x6b46` | `0xC63A4` | `FUN_00036682` (`0x36682`, fresh decompile this session) | **NEW, IDENTIFIED**: torque-sensor-domain, structurally <1Hz — see below |
| `gp-0x6bd0` | `0xC63A0` | `FUN_00034350` | DAMPER (established) |
| `gp-0x6bbe` | `0xC63A2` | `FUN_00034a72` | BOOST (established) |

## `gp-0x6b46` fully decoded — structurally incapable of 18-24Hz content

`FUN_00036682` (0x36682-0x3679x), fresh decompile:
```c
sVar15 = gp-0x6b48 + polarity(gp-0x6752) * ((gp-0x4f60[TORQUE SENSOR] * cal(0xC646C)) >> 15) - gp-0x6b46[prior]
// ... a slew-rate-limited state machine (dead-zone counter gp-0x6a80, cals tp+0x719c/0x71a6) ...
iVar14 = ((iVar8*0x400 - iVar14) * cal(0xC63D2)) >> 10 + iVar14   // FINAL stage: 1st-order EMA
gp-0x6b46 = iVar14 >> 10
```
`0xC63D2` matches the record's "final slow IIR with 6/1024 coefficient" (not independently re-read this
session, inherited) ⇒ α≈6/1024≈0.00586, **corner ≈0.93 Hz at 1kHz**. `gp-0x6b46`'s own output stage is a
sub-1Hz low-pass — **structurally cannot carry 18-24Hz energy regardless of what feeds into it upstream.**
Input is `gp-0x4f60` (torque sensor) scaled by `0xC646C` (the shared sensor scale) — driver-torque domain,
not LKAS.

## `gp-0x6a10`'s producer, `FUN_0003fc16`, decompiled fresh — corroborates the absolute-angle identity

```c
if (gp-0x67fe == 1 || gp-0x67fe == 2) {         // assist substate, reads 1 during ordinary manual
                                                  // power-steering-on driving too (established prior)
    uVar7 = 0 if cal(tp+0x74a8)==0 else clamp(cal(tp+0x733a), sign vs gp-0x69e0+RAM(0x641c))
    sVar6 = gp-0x69ca - uVar7            // <<< NO reference anywhere in this function to gp-0x6acc,
                                          //     gp-0x6b98, or any commanded/target quantity
    gp-0x6a10 = MIN/clamp-chain(sVar6)   // FUN_00049a5a/FUN_00049a78, the same voted-sensor MIN/clamp
                                          //     pipeline used for gp-0x69aa elsewhere (per prior record)
} else {
    gp-0x6a10 = 0
}
```
**[EVIDENCE, this decompile]** The function's only inputs are `gp-0x69ca` (a base value, NOT independently
identified this session — producer not traced) and a small bounded correction. **No setpoint, target, or
LKAS-commanded quantity appears anywhere.** Structurally consistent ONLY with "raw/corrected sensor angle,"
not "tracking error" — corroborates `docs/_session_v86_arc_map.md` §D2(b)'s telemetry finding
(`b4 ≡ |angle| ≥ 0.85°` at 99.93-99.94%, route `6d`) via an INDEPENDENT method (structure vs. correlation).
Also computes a second output `gp-0x6a0a` via a different branch involving `gp-0x4f60` (torque) when
`gp-0x67fe`'s substate and `gp-0x4ebc` gate is open — not chased this session, flagged for whoever needs it.

## Route `73` (V88's flight) own angle distribution — read directly from `_cache_r73/r73.npz`

Fields `cs_ang` (steering angle, deg), `cs_v` (speed), `cs_eng` (engagement proxy, fractional — treated
`>0.5` as engaged; NOT independently confirmed to be `latActive` specifically, flag before reusing):
```
engaged & v>50 km/h: 7,504 frames (of 11,588 total engaged; p50 speed 103.3 km/h, max 116.6 km/h)
|angle|: p10=1.5° p25=3.8° p50=4.28° p75=5.30° p90=8.80° p95=10.10° max=15.60°

FactorD segment occupancy (X=[0,5,10,15,70]°), highway-engaged only:
  [0,5°) 72.68%   [5,10°) 21.84%   [10,15°) 4.46%   [15,70°) 1.01%   >=70° 0.00% (never reached)
```
On this route's highway driving, FactorD's index never leaves the first three segments (98.98%); the
top two breakpoints are essentially or entirely unreachable. Moot for the current flat-unity Y (doesn't
matter which segment), but bounds any future edited-FactorD proposal's useful range to 0-10°.

## New candidate this session, ranked ABOVE `0xC63AC` for the 21Hz question

Since the six lane weights are individually addressable and never touched by any build, **lowering
`0xC63A0`/`0xC63A2`/`0xC63A6` (damper/boost/friction — the three lanes structurally capable of carrying
18-24Hz content) is a pure per-lane gain cut with ZERO phase effect anywhere**, doesn't touch the
LKAS-class lanes (`0xC63A8`/`0xC63AA`) or the shared `0xC63AC` pole's phase at 7.79Hz (irrelevant to the
ratchet per H2). More surgical than moving `0xC63AC` itself, which affects all six lanes' phase uniformly.

## Related
[[reference_accord_fun3aa2c_r24_r26_pole_census_no_filter_exists]] — the sibling census this session
that established r24/r26 have no analogous pole, prompting the same fresh-decompile method applied here.
`reference-accord-fun3a382-engagement-gated-residual-loop.md` (repo memory) — established the six-lane
sum's unity weights and overall structure prior to this session; this file names the two previously-open
lane identities and adds the `gp-0x6a10` producer confirmation.
`docs/_session_v86_arc_map.md` §D2(b) — the telemetry-side correlation this decompile corroborates.
