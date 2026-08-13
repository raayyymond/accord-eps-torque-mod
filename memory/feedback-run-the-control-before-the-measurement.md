---
name: feedback-run-the-control-before-the-measurement
description: "Four claims died to controls in one session, three retracted by their own authors — always calibrate the estimator against known inputs, and against the RIGHT null, before reporting a number."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: e91b71d0-25c8-4a14-9b74-24c186211918
  modified: 2026-08-09T07:33:54.791Z
---

**Run the control BEFORE the measurement, and test against the RIGHT null.**

**Why:** in the 2026-08-09 V87 session, **four** decision-bearing claims died to controls — three of them
retracted by the agents that produced them, after they had already been reported:

| claim | what the control showed |
|---|---|
| "Q ≥ 68 / a needle / phase-coherent 250–500 cycles" | raw-periodogram FWHM returns **Q = 8,000,000** on a synthetic **Q = 2.4** mode — it measures FFT resolution, not damping |
| "a FOREST of ≥8 coherent peaks at 7.4–8.4 Hz" | a **phase-randomised surrogate** returns 8 peaks at prominence 171/127/105/… — **more** prominent than the real data's 91/79/74/…. Only **white noise** had been tested, which is the wrong null for a coloured, non-stationary background |
| every spectral damping estimator | linewidth returns **38.7 for a Q = 1 mode**; total range over Q = 1 → ∞ is **1.37×** against a single-window spread of **1.79×** — the noise on one window exceeds the estimator's whole dynamic range |
| `C31.q_of` and siblings | **Q = 79.00 on pure white noise**, *above* its own 54.73 window limit — physically impossible. `_grind2_lib.q_of` and `_r47_imu_lib.q_of` identically defective. **25 files call one of them** |

**Only one damping estimator PASSED: ring-down** (log-log r = +0.937 over ζ = 0.005–0.02), and it gave the
session's cleanest number.

**How to apply:**
1. **Before quoting any derived quantity, feed the pipeline synthetic inputs of known value** and publish
   the recovered-vs-true table. If the estimator cannot order the range you care about, **say UNDERPOWERED
   and do not report a ratio.**
2. **Choose the null to match the data's actual character.** White noise is not a null for a coloured,
   bursty, non-stationary signal. A **phase-randomised surrogate** (same power spectrum, destroyed phase)
   is the right null for "is this peak coherent".
3. **A positive control must accompany every null** — an estimator that finds nothing is worthless unless
   you have shown it finds something it should.
4. 🛑 **Beware ratios of two lower bounds.** Q figures from run-limited windows are ratios of *run lengths*;
   an "instrument floor" column belongs beside every value.
5. ⊕ Related and equally load-bearing: **a chain of citations to a summary is not a measurement** — the
   session's keystone was quoted through three documents, and reading its own table showed **1.41×** in the
   band that mattered where the summary said **63.66×**.

See [[accord-ratchet-is-a-lightly-damped-resonance]], [[feedback-episodes-not-windows]].
