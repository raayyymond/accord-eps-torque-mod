# 🛑 THIS IS NOW THE GATING ITEM FOR THE WHOLE PROGRAMME — and the ask is exact

**ONE more stock-configuration drive** takes the kit's strongest surviving finding from **p = 0.100**
to **p = 0.018**. Nothing else in the corpus can do that, because the limit is arithmetic:

> With **one** stock route, the exact one-sided permutation p-value floor is **1/(n_mod+1) = 0.100**.
> **No amount of further analysis of existing data can reach 0.05.** The limit is the DESIGN.

Matched on small-angle exposure, **stock's large-angle 6-9 Hz p90 (1.551) is below all nine mod
routes (2.909-8.320)** — including **both** V112 drives, by ≥ 1.88x. One more stock drive that lands
anywhere below the mod range settles it.

✅ **No build, no flash, no firmware change.** This is a measurement, not an experiment on the car.
✅ Everything stock-vs-mod in this corpus currently rests on **route 97 alone**.

---

# DRIVE CARD — the one measurement the corpus cannot make

**No firmware change. No flash. Keep V112 on the car.** This is a data-collection drive only.

## WHY

Two independent routes to the remaining mechanism are both blocked by the same gap:

| route to the answer | what it needs | what the corpus has |
|---|---|---|
| compare to STOCK at low speed | stock data below ~35 km/h | **25 s** (route 97 is highway-weighted, p50 72 km/h) |
| compare ENGAGED vs MANUAL at speed | manual data at 35–90 km/h | **174 s total, across 10 routes and 3+ builds** |

A 25-second window swings the `Re(Z)` estimate **1.6–3.8×** (measured by subsampling the rich stock
bins), so neither denominator can carry a ratio claim. **No further re-analysis fixes this** — the
measurement needs new data, and only one of the two gaps is cheap to close.

## WHAT TO DRIVE

**One stretch of road, ~55–80 km/h, driven both ways within the same session.** Interleave rather
than doing all of one then all of the other, so road surface and temperature are shared.

| arm | target | how |
|---|---|---|
| **A — ENGAGED** | ≥ 150 s at 55–80 km/h | openpilot engaged, **hands resting lightly on the wheel** |
| **B — MANUAL** | ≥ 150 s at 55–80 km/h | openpilot **not** engaged, hands on normally, same stretch |
| **C — ENGAGED** | ≥ 100 s at 35–55 km/h | as A |
| **D — MANUAL** | ≥ 100 s at 35–55 km/h | as B |

🛑 **Hands resting lightly on BOTH arms is the point.** Every prior engaged-vs-manual contrast in
this kit compared *engaged hands-off* against *manual hands-on*, which confounds the arm's impedance
with the engagement state. Matching the hands state removes that confound.
⊕ Grip was separately measured to have no reliable effect on the 6–9 Hz **rate** oscillation
(0.79× [0.67, 1.01]), so light hands on both arms should not suppress the thing being measured.

## WHAT IT SETTLES

`gp-0x6b26`'s Y row is the **only live mode-gated cell** (×3.00 on engaged modes 26/27, byte-stock on
mode 24), and its speed LERP knots are **0 / 20 / 90 km/h** with dose **×3.00 / ×3.00 / ×8.14**.
⇒ **If it drives the engaged-minus-manual `Re(Z)` gap, that gap MUST grow ~2.7× between 20 and
90 km/h.** Flat or falling falsifies it and forces the search elsewhere.
That is a pre-registered, falsifiable prediction, and this drive is the only way to test it.

## ⚠ WHAT THIS DRIVE IS NOT
It does not test a fix and it will not change how the car feels. It is the instrument, not the cure.
