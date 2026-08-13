---
name: accord-base-assist-damper-cannot-reach-the-micro-regime
description: REFUTED 2026-08-13 (record-repair) — six builds (V74/75/76/78/79/80) had BOTH FactorC and FactorE dead zones open at once, verified from the images; three flew (V75 route 5e, V76 route 65, V80 route 66). Only the route-73/V88 Honda-stock zero measurement still stands.
metadata:
  type: reference
---

**`ch₀ = clamp( (FactorC(speed) × FactorE(rate)) >> 10 , ±ceiling )`** — `gp-0x6bd0`, the
base-assist damper.

## 🛑🛑 CORRECTED 2026-08-13 — this memory's central claim was WRONG, verified from the images
**"Neither prior test ever had BOTH dead zones open" is REFUTED, and so is "the damper cannot reach
the micro regime, cal-only."** Direct read of `FactorC`/`FactorE` mode-26 records from the
`_v*_plain_image.bin` snapshots (`analysis-2020accord/ledger_v38_to_v99_bytes.py`, `PTRS["FactorC"|
"FactorE"]`, EVIDENCE — method: dereference the pointer array, decode the LERP record, no build
script consulted):

| build | FactorC Y (speed) | FactorE X (rate, ct) / Y | both dead zones open? | flew? |
|---|---|---|---|---|
| STOCK / V84+ / V88 | `[0,234,429,908]` | `[60,400,2500,4000]` / `[0,140,539,927]` | NO (Honda) | — |
| V74 | `[429,234,429,908]` | `[12,400,2500,4000]` / `[0,539,539,927]` | YES | flew, hard-faulted |
| V75 | `[566,234,429,908]` | `[12,200,2500,4000]` / `[0,539,539,927]` | YES | ✅ route `5e`, hard-faulted |
| V76 | `[566,566,566,908]` | `[0,119,2500,4000]` / `[0,300,539,927]` | YES | ✅ route `65`, clean |
| V78 | `[566,566,566,908]` | `[0,119,2500,4000]` / `[0,449,539,927]` | YES | built, never flown |
| V79 | `[566,566,566,908]` | `[0,119,2500,4000]` / `[0,897,912,927]` | YES | built, superseded |
| V80 | `[566,566,566,566]` (flat) | `[0,119,2500,4000]` / `[0,897,912,927]` | YES (fully removed) | ✅ route `66`, worst grinding ever, no fault |

`FactorC Y[0] > 0` removes the speed dead zone (creep is no longer forced to 0). `FactorE X[0] ≤ 12 ct
(≈2.55 °/s)` removes almost all of the rate dead zone against Honda's 60 ct (12.7 °/s) — the LERP
ramps from `X[0]` and is already substantial by the middle of the operator's named 1–13 °/s
micro-ratcheting band. **Six builds carried this combination and three of them — V75, V76, V80 —
actually flew.** V86B, the one prior test this memory credited as "the" open-FactorC test, is not the
exception; it is one of several, and it is the only one of the six that left `FactorE` at Honda's
dead zone (`[60,400,2500,4000]`).

## What survives
- The formula and the pointer arrays (`0xC9E9C` FactorC / `0xC9F84` FactorE / `0xC77A0` ceiling).
- **The route-73 (V88) measurement still stands**: V88 restored Honda's stock FactorC/FactorE, so on
  THAT build the damper genuinely contributes zero on 95.91% of engaged frames, 100% of the
  micro-ratcheting regime.
- The **sizing argument for the Honda-dead-zone starting point** — 25% authority at 10 °/s needs
  `FactorE Y[0]` off zero, i.e. a step at rate zero, the V80 mechanism — is still correct as an
  argument about widening FROM Honda's dead zone. FactorE `X[0]` is 60 counts, not 12.

## What died
- **"Neither prior test ever had BOTH open"** — refuted by the table above.
- **"The base-assist damper cannot be the micro-ratcheting lever, cal-only. Structural, not a
  null."** — V75/V76/V80 are cal-only builds (V80 also carries one code byte, `0x454FE`) that DID
  open both dead zones and DID fly. What is actually unresolved is whether their on-car results
  (V76 clean/no complaint on record, V80 "worst grinding ever") isolate THIS lever — all three also
  move FactorE's ramp height and (V74/V75) the `0xCBE74` friction dose simultaneously, so none of
  them is single-variable against the damper alone. **Open again, not closed.**

⇒ Do not re-cite "cal-only cannot reach the micro regime" without this correction. If a future build
re-tests the damper at creep, V76's config (`[566,566,566,908]` / `[0,119,2500,4000]`) is the mildest
flown one that already reaches the micro regime, and it flew clean.

Related: [[accord-v80-damper-relay-and-grind1-inert]], [[reference-accord-cbe74-friction-row-zero-clean-flights]].
