---
name: reference_accord_gp6bd0_path1_path2_sign_inversion_and_signflip_telemetry_method
description: gp-0x6bd0 (FactorC/E damper) enters Path-1 (FUN_0003aa2c) raw but Path-2 (FUN_00038148) applies an EXTRA independent pol multiply -- the two paths receive OPPOSITE effective sign from the same cell. Path-2's chain to gp-0x6ad6 (FUN_00037fe6) and the PID (0xC6200=8192 clamp) traced and cited. Also: motor/column-rate sign-flip rate is directly measurable from ANY rlog via the standard CAN STEER_ANGLE_RATE signal (rate_c), no cave needed -- method + a real measured result (V103/6x vs stock: 1.7x pooled, ~10x at 40-70km/h engaged, two methods agree).
metadata:
  type: reference
---

# gp-0x6bd0 Path-1 vs Path-2 sign, and a no-cave telemetry method — 2026-08-21

Traced for the orchestrator's "price lowering Honda's own FactorC below stock as a highway lever"
follow-up to the damping-injection census. GhidraMCP fresh decompiles + working rlog telemetry, this
session.

## 🛑🛑 gp-0x6bd0 has OPPOSITE effective sign in Path-1 vs Path-2 — do not assume either path's
## characterization transfers to the other

`FUN_0003aa2c` (Path-1, fresh decompile re-read from earlier this session): `gp-0x6bd0` enters the
aggregator **raw**, `+ gp-0x6bd0 * zr(±2048)`, **no `pol` multiply on this specific term** at the point
of summing into `gp-0x6b94`.

`FUN_00038148` (Path-2, fresh decompile this session): `gp-0x6bd0` is one of 6 zero-reject-gated,
weighted lanes (weight `0xC63A0`=1024, unity, byte-confirmed identical stock/V103) summed, and **the
WHOLE 6-lane sum is then multiplied by `pol` again** (`* (int)*(char *)(unaff_gp + -0x6752)`) before
being EMA-filtered (alpha `cal(tp+0x73ac)`) and combined with two more external inputs
(`gp-0x6bfe`/`gp-0x6bfa`, NOT traced) via a nonlinear LERP+sign+clamp into `gp-0x6b70`.

Since `gp-0x6bd0` at its SOURCE is already `−sign(gp-0x6abe)·magnitude` (established, `FUN_00034350`'s
own unconditional `if(gp-0x6abe>0) negate`), and `pol=−1`: **Path-1 receives it as-is (damping-signed);
Path-2 receives it with one extra sign flip (pumping-signed).** Lowering FactorC's Y-knots reduces BOTH
simultaneously, in opposite senses. **General lesson for this kit: a cal cell shared across Path-1 and
Path-2 cannot be assumed to carry the same effective sign in both — check every `pol` multiply on the
SPECIFIC path, not just at the cell's own producer.**

## Path-2's full chain to the PID, addresses cited

```
gp-0x6bd0 --[FUN_00038148: wt 0xC63A0=1024 * pol * cal(tp+0x7462+6) * 16, EMA alpha=cal(tp+0x73ac),
             combined with gp-0x6bfe/gp-0x6bfa via LERP+sign+clamp, NOT further characterized]--> gp-0x6b70
gp-0x6b70 --[FUN_00037fe6 @0x37fe6: one of 7 zero-reject lanes, unit weight 0xC64B0=1 via identity
             speed-LERP [RELAYED], summed with gp-0x6b4a(unconditional base term)+6 others,
             clamp ±25600]--> gp-0x6ad6
gp-0x6ad6 --[FUN_0003a382 @0x3a7a2: clamp ±8192 (cal 0xC6200=8192) BEFORE the PID error subtraction --
             [[reference_accord_c6200_clamps_gp6ad6_inside_the_pid]], re-cited not re-derived this
             session]--> PID error --> established unsaturated d(gp-0x6b94)/d(gp-0x6b70)=0.2565
```
`gp-0x6ad6`'s own term-0 (`gp-0x6b4a`, unrelated to this lever) alone reaches 32% of the 8192 saturation
bound [RELAYED] -- Path-2 is plausibly NOT structurally saturated in ordinary driving, but the actual
operating point of `gp-0x6bd0`→`gp-0x6b70` was not measured this session (the `gp-0x6bfe`/`gp-0x6bfa`
LERP-wrap makes it operating-point-dependent, not a clean linear gain). **What would close it**: trace
`gp-0x6bfe`/`gp-0x6bfa`'s producers, or get a live probe on `gp-0x6bd0`'s actual duty/magnitude at
40-70km/h (see the falsifier design in the session's SendMessage log).

## GATE 1, re-confirmed this session
`0xC9E9C` (FactorC's own pointer table base): **1 hit image-wide** (`FUN_00034350` only) — private,
single-consumer, clean for a Y-knot edit. `0xC63A0`-`0xC63AA` (all 6 Path-2 weight cells, incl. this
lane's `0xC63A0`=1024) confirmed byte-identical stock vs V103 by direct read.

## `0xC407E`/`0xC63A0` exoneration — RE-CONFIRMED FROM THE V103 IMAGE DIRECTLY, not relayed
`0xC407E`=511 on both stock and V103 (byte-read). All six `0xC63A0`-`0xC63AA` = 1024 on both. The
established "V74/V75 fault was `0xC407E`, `0xC63A0`/the damper mechanism is exonerated" record
[[reference_accord_c407e_is_the_fault_interlock_c63a0_exonerated]] holds on the CURRENT V103 base, not
just historically.

## 🛑🛑 NEW METHOD: motor/column-rate sign-flip rate is measurable from ANY rlog, no cave needed

`gp-0x6bbe`'s sign-chain trace this session established `gp-0x6a56 = pol·S1·gp-0x6abe` (a fixed positive
scale `S1`), and CAN `0x14A` bytes[2:3] `STEER_ANGLE_RATE` is a fixed linear function of `gp-0x6a56`
[RELAYED chain, established elsewhere]. **Therefore `sign(gp-0x6abe)` is recoverable from the STANDARD
CAN `STEER_ANGLE_RATE` signal in any log — stock or built, no cave/piggyback required.** The kit's own
`rlog-tools`/`extract_r5d_cache.py` already extracts this as field `rate_c` ("CAN 0x14A x -1.0, column
STEER_ANGLE_RATE, deg/s") into `.npz` caches at `analysis-2020accord/_cache_r97/r97.npz` (stock baseline)
and `_cache_r9e/r9e.npz` (V103/6x) — **a working Python env exists at
`/c/Users/dudei/anaconda3/envs/bin_decompile/python` with numpy/pandas available**, confirmed working
this session (`which python`/`python3` alone fail on this machine — use the anaconda env path directly).

**Measured result** (zero-crossing counting on `rate_c`, two methods — raw and a ≥3-sample/~30ms
debounced run-length version, both agree directionally):

| regime | stock (r97) | V103/6x (r9e) | ratio |
|---|---|---|---|
| ENGAGED all speeds, debounced | 1.37/s (577 flips/421.3s) | 2.33/s (552/237.0s) | **1.7×**, well-powered both sides |
| ENGAGED 40-70km/h, debounced | 0.12/s (4 flips) | 1.29/s (240 flips) | **10.5×**, but stock side is only 4 events — wide uncertainty |

Median `|rate_c|` is SIMILAR (1-2 deg/s) between the two while flip rate differs by 2-10x — signature of
a genuinely FASTER oscillation, not just bigger swings. Did not compute a spectral peak of the flip train
itself (only a mean-rate proxy) — an autocorrelation/FFT of the flip-interval series vs the established
7.79Hz ratchet frequency would be the natural next step if this method gets reused.

Related: [[reference_accord_damping_injection_census_gp6ade_dead_and_gp6ad0_comp_add]],
[[reference_accord_gp6bbe_k1_ratelane_full_retrace_and_sign_disqualification]] (source of the
`gp-0x6a56`/`S1` relation this method depends on).
