---
name: accord-averaged-spectrum-needs-matched-speed-distributions
description: "An averaged spectrum compares two routes only if their speed distributions match; otherwise a moving wheel order manufactures an \"only on route X\" line."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 95bceff4-4059-403e-a0cd-c57effc19f41
  modified: 2026-08-04T01:05:13.427Z
---

🛑 **NEW RULE, 2026-08-03 — it nearly cost a session a false mode, and it survives the fix that
killed the withdrawn 42 Hz mode.**

**An averaged periodogram compares two routes ONLY if their SPEED DISTRIBUTIONS MATCH.** A moving
wheel order **concentrates** in a narrow-speed route and **smears** in a wide-speed one, so the
difference between their averaged spectra is the *exposure*, not the car.

**How it bit:** route `4e` (engaged) showed a 28.13 Hz peak at prominence **18.81**, route `4c`
(manual) only **3.33** — which reads as "engaged-only line". It even **passed the band-centre
artefact test** (the peak did not move as the search band swept 24–30 / 20–35 / 18–40 / 15–45 /
23–33 Hz), so it looked like a genuine fixed mode.

**What killed it — a PER-WINDOW prominence census:** 26–30 Hz content appears in **133/177 = 75.1%**
of MANUAL windows at median prominence **7.50**, versus **88/121 = 72.7%** at **6.27** engaged —
*more* on the manual route. `4c`'s version is **wheel order 2**: Theil-Sen **+1.0352 [+1.0012,
+1.0616] Hz per m/s** against order 2's **+0.9616**, per-bin agreement 0.1–0.35 Hz. `4c` simply
swept more speed.

**Why:** So two rules, not one.
1. **The band-centre test is NECESSARY BUT NOT SUFFICIENT.** It catches the "argmax scatters to band
   centre when no line exists" artefact; it does NOT catch a real-but-moving order.
2. **A route-wide LINE is carried by MANY windows. Always follow the averaged spectrum with a
   per-window prominence census** — otherwise one loud episode reads as a route-wide mode.

**How to apply:** before quoting any cross-route averaged spectrum, (a) print both speed
histograms, (b) bin by speed and peak-find *within* bins, (c) run the per-window census, (d) fit
Theil-Sen f0-vs-v and compare against `n × 0.4808 × v` for n = 1, 2, 3 (circumference 2.088 m).
⚠ With a CVT also test f0-vs-**rpm** (engine order 1 = +0.01667 Hz/rpm): rpm is nearly decoupled
from road speed at cruise (measured corr **+0.037** engaged, **+0.184** manual), so a speed sweep
ALONE cannot separate an engine order from a fixed mode.

Companion slip from the same session: coherence computed against `e4req` (the engagement BIT) rather
than `e4tq` (the command) read exactly **0.000** in every band. **An exact 0.000 across every band is
a wiring error, not a result.**

Related: [[accord-v68-lane-change-is-28hz]], [[feedback-episodes-not-windows]].
