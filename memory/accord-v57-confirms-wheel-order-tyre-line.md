---
name: accord-v57-confirms-wheel-order-tyre-line
description: "V57 independently reproduces the wheel-order-1 tyre line at circumference 2.073-2.080 m, confirming it is firmware-independent."
metadata: 
  node_type: memory
  type: reference
  originSessionId: a179e27a-7fe7-49ee-b2a8-e84c074404f9
  modified: 2026-07-30T02:43:03.620Z
---

Measured 2026-07-29, route 28 (V57, 300 s stop-and-go) vs route 24 (V56), one identical pipeline.

The circumference estimator was **calibrated on V56 first**, where the answer (2.088 m) is known:
capture band `[0.75, 1.35] * fpred`, nfft=256, prominence >= 3, RATE_fine (`0x18F[2:4] * -0.1`),
linear detrend. At those settings V56 returns **2.090 m (n=46, p10-p90 2.015-2.143)**.
⚠ The wider `[0.60,1.60]` band returns **1.606 m** on the same V56 data — it is contaminated by the
fixed 7-8 Hz resonance sitting inside the search window. Use the tight band.

Applied to V57, three independent settings agree: **2.080 m (n=5)**, 2.073 (n=6), 2.076 (n=3).
Free regression on V57's 5 detections spanning 9.5-20.1 m/s: `f = +0.4230*v + 0.771`, r = +0.9097.

★ **ORDER TRACKING is the better tool and settles it.** Rescale each window's frequency axis by its
own wheel frequency `v/C0` before pooling, so a speed-varying line stops smearing across bins and
every window counts. Pooled order spectrum, LKAS-applying + hands-off, nfft=256:
**peak at order 1.000 on BOTH builds** — V57 K=9 (prominence 11.7), V56 K=59 (6.2) — i.e. C = 2.088 m
on V57 to within the 0.02 grid step. Decoys on V57: order 1.00 → 13.44 vs 1.40 → 1.28, 1.80 → 1.80.
Route 28 episode 5 alone (the road-speed run) tracks it window by window:
v=13.16→6.25 Hz, 18.55→8.98, 19.50→9.38 (prominence **715**, a burst), 20.08→9.77 ⇒ C = 2.056-2.105 m.

**Order-vs-frequency pooling is also the road-input/resonance discriminator**: a road line sharpens
under order pooling and smears under frequency pooling (V57 sharpening 1.71x), a structural resonance
does the reverse. Use it instead of arguing from a single pooled peak.

⇒ A firmware change cannot move a road-input line, and V57 did not. **The tyre diagnosis is
confirmed and firmware-independent.** The wheel balance / road-force check stands as a real action.

⚠ n = 5-6 on V57 (route 28 is 48.4% stopped and has only 16.7 s above 14 m/s). This is agreement,
not a precision match. See [[accord-869hz-line-is-wheel-order-not-v56]].
