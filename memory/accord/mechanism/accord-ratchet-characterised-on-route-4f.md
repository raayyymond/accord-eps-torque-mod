---
name: accord-ratchet-characterised-on-route-4f
description: "★★★ First real characterisation of the ratchet — 46 windows/118 s at >=1200 counts p-p, peak 6065, median 7.79 Hz, speed-invariant, 44/46 engaged (p=4.6e-5), and the ~7.5 Hz line is in the BAR but NOT in openpilot's command ⇒ the loop closes inside the EPS + plant. ⚠ Its 'Q is not measurable' correction is SUPERSEDED 2026-08-04 — see accord-ratchet-q-measured-40."
metadata:
  type: reference
---

# ★★★ THE RATCHET, FIRST REAL CHARACTERISATION — route `4f`, 2026-08-04

**Present and large.** **46 windows / 118 s at ≥ 1200 counts p-p, peak 6,065 counts p-p.** Seg 1 carries
a **continuous 20 s event** (t = 20.5–40.9 s); seg 0 one at t = 50.4–60.7 s.
★ **The operator's "mostly segments 0 and 1" is confirmed exactly** — he said it before the data did.

**Frequency:** median **7.79 Hz** by zero-crossing (FFT-free), **7.56 Hz** by the spectral estimator —
consistent with the recorded **7.56 ± 0.36**.
**Order veto:** slope **+0.0358 Hz per m/s** vs wheel order 1's **0.482** ⇒ **speed-invariant, not an
order**; rpm 773–1724 with f0 static ⇒ **not an engine order** either.

## ★ NEW: the loop closes inside the EPS + plant — openpilot is NOT the oscillator
The ~7.5 Hz line is in the **torsion bar** and in the **angle rate**, but **NOT in openpilot's
command**: `e4tq` 6–9 Hz prominence median **2.7** against a presence threshold of **10** — and it holds
when restricted to windows with **command-rail duty ≤ 2%**, so it is not a rail artefact.

## Engagement-conditional
⚠ **SUPERSEDED 2026-08-04 by [[accord-ratchet-is-engagement-required]]** — with the grip confound
removed (both arms hands-off, creep < 4 m/s) and pooled over four routes: **73/88 = 83.0% engaged vs
0/118 = 0.0% manual, p = 3.8e-41**, and the rate is **build-independent (80/81/79/94%) ⇒ no build in
this kit has ever moved the ratchet.** The `4f` numbers below stand as written.

**44 / 46 windows engaged, 0 manual.** Fisher one-sided **p = 4.6 × 10⁻⁵**; matched
**6.65 [2.45, 12.85]** vs null [1.03, 3.96]. Consistent with the pooled 5-build result on record.

## Three corrections to the ratchet's own record
1. ⚠ **Widen "creep only"** — one **4,843-count** episode at **12.7 m/s**.
2. ⚠ ~~**Q is NOT measurable at NFFT 256** — the main lobe caps measurable Q at ~13.3, so the recorded
   **Q ≈ 36** is **neither confirmed nor refuted** here.~~ 🛑 **SUPERSEDED 2026-08-04 —
   [[accord-ratchet-q-measured-40]]: Q ≈ 40 at f0 = 7.793 Hz**, measured on route `50` from a 12.81 s
   provoked episode and confirmed by a **window-cap invariance test** (39.0 at cap 54, 40.0 at cap 111).
   ⚠ **One episode; and f0 drift would DEFLATE it, so 40 is a LOWER BOUND.** The statement above was
   true of `4f`'s windows and is kept for that reason — **do not cite `4f` for Q either way.**
3. ⚠ **The "amplitude-saturated / flat-topped" premise is NOT what `4f` shows** — crest factor
   **2.07–2.45** on a band-pass where a steady sine gives **1.414**, and **no flat-topping on any
   filter**. That premise is what justified V69's rung choice. **BELIEF-level re-framing — flag it for
   re-examination**, do not treat the saturation model as dead
   ([[accord-ratchet-is-a-saturated-resonance]]).

## What the r24 dose ladder says: NULL, and under-powered
0× → 4×: **every CI inside its null**, and the 24–27 Hz negative control itself ranges **0.38–2.47**.
Cross-build V69/V67 = **3.0× raw / 3.6× selectivity**, **both CIs overlapping the split-half null**
⇒ **not established.**
⚠ **Route `4a` cannot speak to the ratchet** — its 149.2 s is engaged-*creep*, but the hands-off cell is
**13.0 s with zero episodes.** Any ratchet claim leaning on `4a` is leaning on nothing.

See [[accord-v69-flew-dose-response-non-monotone]], [[accord-v69-ratchet-probe]],
[[accord-ratchet-and-grinding-are-two-symptoms]].
