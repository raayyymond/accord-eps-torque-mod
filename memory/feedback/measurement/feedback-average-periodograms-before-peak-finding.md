---
name: feedback-average-periodograms-before-peak-finding
description: A median-of-per-window-argmax manufactures a spectral line at band centre when no line exists — it won by dBIC 249-460 on an artefact; average the periodograms FIRST, then find the peak
metadata:
  type: feedback
---

🛑 **A median-of-per-window-argmax estimator MANUFACTURES a spectral line at band centre when there is
no line at all.** On a window containing no line, the argmax scatters across the band; the **median**
of that scatter lands near the band centre and is *stable across every stratum*, which reads exactly
like a fixed mode.

**How convincing the artefact looked.** Run over 30–49.5 Hz (centre 39.75 Hz), it reported ~42 Hz in
every speed bin on four independent comma-IMU axes while road speed ran 22→35 m/s — and a model
comparison preferred "constant frequency" over "wheel order 3" by **ΔBIC 249–460**. It matched the
operator's reported fixed pitch. It was published internally as a finding and then withdrawn.

**The fix that exposed it, and the rule.** **Average the periodograms across windows FIRST, then find
the peak of the averaged spectrum.** Averaging suppresses the scatter that biases an argmax; a real
line survives it. Under that estimator the "42 Hz mode" vanished — prominence **1.23–3.83** across
every route, build and channel, against the kit's >4 criterion — while the positive control (wheel
order 1) came back at prominence up to **79**.

## Same class of error: the `order = f0·k/v` tautology
`order = f0·CIRC/v` returns ≈3.00 whenever a band-limited argmax sits near the centre of 30–49.5 Hz at
~28 m/s, **independent of what the spectrum contains**. The kit's recorded *"highway 40–49 Hz is wheel
order 3, per-window order p50 2.994"* was this, not a measurement. See
[[accord-highway-30-49hz-has-no-line]].

🛑 **AND THE TAUTOLOGY IS NOT SPECIFIC TO ORDER 3 — this is the part that generalises.** *Any* band
whose centre divided by the population's typical speed lands near an integer will "confirm" that order.
The same record also carried *"26–32 Hz is order 2 at p50 **1.995**, n > 600"* as if it were independent
corroboration. It is not: 26–32 Hz has band centre **29 Hz**, and at ~28–30 m/s `29 · 2.08 / 29 ≈ 2.0`
**by arithmetic**. Two bands agreeing that they are "their own order" is one tautology counted twice.

⇒ **A ratio built from a band-limited estimate divided by the variable you are testing against is not a
test.** Test with a **slope with a CI**, or a **binned table of the quantity vs the variable**. A
matching order number is evidence **only** when the band is wide relative to the order spacing, or when
the order is tracked across a **speed sweep** so the line has room to move out of the band if it is not
really an order.

## The discipline that caught it, worth repeating
Every band-limited claim needs a **positive control run through the identical pipeline**. Here the
8–30 Hz wheel-order-1 line served: peak 10.94 / 12.61 / 13.66 / 15.40 Hz across speed bins vs
predictions 11.30 / 12.74 / 14.18 / 15.87, free-order fit **1.07**, slope **+0.4836 [+0.4806,
+0.4863]**. An instrument that cannot recover a known line is not to be believed on an unknown one.

## Also chased and killed, so nobody re-runs it
A **fixed pitch does not imply a mode**: the Accord's **CVT holds engine rpm near-constant at cruise**,
so an engine order would also sit still while road speed varies. Tested by extracting `ENGINE_RPM`
(`0x17C` byte 2:3 big-endian, src 1) for 33 highway segments — rpm 1330–2400, `corr(rpm, v)` only
**+0.270** so the hypotheses separate. An aliased engine order 2 requires slope **−0.0333 Hz/rpm**;
measured **−0.00071 [−0.00251, +0.00084]** on `ay`. **Refuted.** Extractor:
`analysis-2020accord/extract/extract_rpm_cache.py`; test: `analysis-2020accord/studies/highway/highway_rpm_test.py`.

⚠ Minor but recurring: `argsort(argsort(x))` is **not** a rank transform when there are ties. On a
binary indicator it gave a Spearman of **+0.393** against a covariate whose own decile table fell
monotonically. Use average ranks.

⇒ Veto file: `analysis-2020accord/studies/highway/highway_meanspec.py`. Related:
[[feedback-episodes-not-windows-and-the-noise-floor]],
[[feedback-mean-and-tail-must-be-reported-together]], [[feedback-verify-subagent-conclusions]],
[[accord-telemetry-conventions-that-produced-wrong-answers]].
