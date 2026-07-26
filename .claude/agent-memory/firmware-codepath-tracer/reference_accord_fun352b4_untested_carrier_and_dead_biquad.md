---
name: reference-accord-fun352b4-untested-carrier-and-dead-biquad
description: FUN_000352b4 produces TWO outputs -- gp-0x69a4 (already-falsified r24/r26 input) and gp-0x6b86 (a DIRECT, UNTESTED aggregator lane with the widest clamp gate of any base-assist lane, ±12288). Also contains a genuine 2nd-order recursive (biquad-shaped) filter that is calibration-DEAD (gate byte cal 0xC649B=0).
metadata:
  type: reference
---

# FUN_000352b4 -- Accord TVA-A160, traced 2026-07-20 for team-lead's whole-system 21Hz feedback audit

Decompiled fresh on stock `code.bin`. Dispatched as part of "(2) untested proportional Sensor-B
carriers" -- the earlier `FUN_0003a382` unfiltered-lane finding
([[reference-accord-fun3a382-unfiltered-residual-lane]]) prompted a scan of the OTHER,
not-yet-characterized aggregator inputs. This function was not in my memory index before this session.

## Two outputs, two very different fates

`FUN_000352b4` computes **both** `gp-0x69a4` and `gp-0x6b86` in the same call.

- **`gp-0x69a4`** is the confirmed direct input to the r24/r26 adaptive torque-rate gain lane
  ([[reference-accord-r26-adaptive-lane-full-trace-and-sign]]) -- **that consumption path is
  ALREADY FALSIFIED** (V39 zeroed r24 output, V42 zeroed the r26 gain tables; neither symptom moved).
- **`gp-0x6b86`** feeds `FUN_0003aa2c` (the demand aggregator) **directly**, independent of r24/r26.
  **No V39/V41/V42/V43/V44 build touches `FUN_000352b4`, `gp-0x6b86`, or any of its calibration
  tables.** This is a genuinely untested path carrying the same upstream Sensor-B content.

## `gp-0x6b86`'s aggregator gate is the widest of any base-assist lane [VERIFIED, byte-exact]

From fresh decompile of `FUN_0003aa2c` (the aggregator), the per-lane zero-type clamp gates before
summation into `gp-0x6b94`:

| Lane | gp offset | Gate (±counts) |
|---|---|---|
| Friction (`FUN_00036c12`) | `gp-0x6b26` | 1024 |
| Unidentified small lane | `gp-0x6ade` | 1024 |
| Boost (`FUN_00034a72`) | `gp-0x6bbe` | 2048 |
| Damping (`FUN_00034350`) | `gp-0x6bd0` | 2048 |
| Return-centre | `gp-0x6b62` | 8192 |
| Filtered Sensor-B (`FUN_00036682`, r10) | (inline, iVar16) | 8192 |
| `FUN_0003a382` residual | `gp-0x6ad4` | 10240 |
| **LKAS command itself** | `gp-0x6b4c` | 10240 |
| **`FUN_000352b4` (`gp-0x6b86`)** | `gp-0x6b86` | **12288 -- widest of ALL, incl. LKAS's own gate** |

`gp-0x6b86`'s own internal clamp (`sVar15` computed near the end of `FUN_000352b4`, `if (0x3000 <
uVar16) sVar15=0x3000` / floor `-0x3000`) matches the aggregator's external gate exactly
(self-consistent, both ±0x3000=12288).

## Live structure feeding `gp-0x6b86` [VERIFIED, structure; NOT fully quantified]

Reads `gp-0x4f60` (raw Sensor-B/TAS column torque) directly -- both as a sign source and, after a
deadband/clamp (bound = cal `tp+0x7200` = `0xC6200` = 8192, the same constant reused elsewhere in this
codebase), as the primary magnitude input. Pipeline: a **10-point piecewise-linear LERP** (a static
lookup, keyed on the magnitude of a `gp-0x6b4a`-gated/summed version of the deadbanded Sensor-B signal)
feeds a **friction-style hold/hysteresis combinator** (freezes the output at its prior value when the
LERP result is inside a threshold band, updates when it exceeds it) before the final ±12288 clamp.

**This live path is largely unfiltered in the time domain** -- the LERP is a static nonlinear shape,
not an integrator/EMA, and the hold-combinator only introduces filtering in the sense of a hysteresis
dead-band, not a slow time-constant low-pass. Structurally closer to `FUN_0003a382`'s near-unfiltered
residual than to `FUN_00036682`'s genuine τ~170-cycle IIR. **NOT fully quantified**: the 10-point LERP
table's actual breakpoint/value data (cal region around `tp+0x6444`) and the hysteresis threshold were
NOT byte-dumped this session -- open follow-up if this lane needs to be ranked precisely.

## A genuine 2nd-order recursive (biquad-shaped) filter exists here -- and is CALIBRATION-DEAD [VERIFIED]

Inside the same function, gated behind `cVar4 == '\x01' && bVar12 <= gp-0x671a` (`cVar4` = cal
`tp+0x749b` = `0xC649B`, `bVar12` = cal `tp+0x74fa` = `0xC64FA`), there is a real 2-state recursive
filter:
```c
fVar29 = gp-0x3818 (x2_prev);
fVar37 = -(cal[0x70ac]*gp-0x3814(x1_prev) - -(fVar29*cal[0x70a8] - iVar34_scaled*cal[0x70b4]));
fVar38 = gp-0x3814 + fVar29*cal[0x70b0] + fVar37;   // new output before clamp
gp-0x3814 = fVar29;      // shift register: x1_new = x2_old
gp-0x3818 = fVar37;      // x2_new = newly computed state
// fVar38 clamped to +/-12.0, *1024 -> iVar34
```
Coefficients byte-read at `0xC60A8/AC/B0/B4` (floats): **-1.537, 0.634, -1.880, 0.818**. This is a
textbook shift-register biquad structure with non-trivial (non-unity, non-zero) coefficients -- the
first such structure found anywhere in this firmware's torque path.

**Byte-read the gate: `cal 0xC649B = 0x00`.** The branch requires `cVar4=='\x01'`; since this is a
calibration/ROM constant (not RAM), it is **fixed at 0 in stock firmware and can never be true**. The
biquad branch is **structurally present but permanently dead under current calibration** -- `iVar34`
in practice always takes the OTHER branch (the friction-hold combinator described above), never the
recursive filter.

**Correction of record**: [[reference-accord-notch-biquad-search-negative-result]] documented "no
biquad found... not exhaustive." That conclusion (no LIVE biquad) still stands, but the premise that
none EXISTS in the binary was incomplete -- one does, here, just disabled. Worth noting if anyone later
audits `0xC649B` for an unrelated reason: flipping it to 1 would activate a previously-inert 2nd-order
filter with unknown frequency response, not a no-op.

## Related
[[reference-accord-fun3a382-unfiltered-residual-lane]] -- sibling untested carrier, same investigation.
[[reference-accord-r26-adaptive-lane-full-trace-and-sign]] -- the ALREADY-falsified consumer of this
function's other output (`gp-0x69a4`).
[[reference-accord-governor-energy-budget-and-step-selector]] -- the governor slew mechanism this
session's primary investigation covered; `gp-0x6b86`'s untested contribution to `gp-0x6b94` is one
candidate source of amplitude feeding that limiter.
