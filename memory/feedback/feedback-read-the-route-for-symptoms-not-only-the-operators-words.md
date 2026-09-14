---
name: feedback-read-the-route-for-symptoms-not-only-the-operators-words
description: "Operator instruction 2026-09-14: 'don't just rely on my mentioned symptoms, analyze the route data for symptoms and discrepancies' -- every drive read must census the wire for what he did NOT name (spectra by band and stratum, model residual replay, integrator share, saturations and limiter duty, driver interventions, reference-path phase, measurement checks) and report those beside his words. Also: subagents gather data and execute analyses; the comprehension and the design of the next StarPilot change are the orchestrator's own work, not a subagent's."
metadata:
  type: feedback
---

**Why:** on route 71 the operator's three sentences pointed at loose / jerky / oscillating, but the decision-bearing
findings — the 2.34 Hz limit cycle being the SteerFriction relay's doing, the hold map being ×3–5 too small below
10 m/s, the 20 bursts/min stiction pattern — came from the census (`v293r2_read.py` §S5–S13), not from the words.

**How to apply:** run `v293r2_read.py` (or its successor) on every drive before designing: attribution, torque
shares, plant re-fit, delay/phase, spectra with shoulder prominence, low-speed burst traces, high-speed curve
traces, model-residual replay, tracking, measurement checks, interventions, limiter duty. Put the findings the
operator did not name first if they are larger than the ones he did. Delegate extraction and scorer runs to
subagents (they went idle without reporting this session — read their outputs from disk); keep the reading and
the design in the orchestrator. Related: [[feedback-attribute-the-build-from-the-tap-not-from-the-label]],
[[feedback-subagent-model-policy-no-fable-opus-hard-sonnet-trivial]].
