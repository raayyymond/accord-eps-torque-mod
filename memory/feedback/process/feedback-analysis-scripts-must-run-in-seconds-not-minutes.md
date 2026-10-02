---
name: feedback-analysis-scripts-must-run-in-seconds-not-minutes
description: "FEEDBACK 2026-10-02: 'Optimize all analysis... python scripts which take minutes to run should be discouraged and avoided' — extract each route ONCE to a cache, run every analysis on the cache in seconds, vectorise, no per-sample Python loops over a 1 kHz replay; brief every subagent with the rule and a runtime budget; the drive read went 713 s -> 11 s with byte-identical output the same day"
metadata:
  type: feedback
---

**Rule (operator, 2026-10-02):** analysis scripts that take minutes to run are discouraged and to be avoided.

**Why:** the V298 drive read (`rlog-tools/studies/angle_loop/angle_loop_drive_read.py`) took 713 s on route 79 —
98 % of it a pure-Python 1 kHz lane replay of six images (the same lane marched twice) and a 2049×2049 nanmedian
per presence window — and a six-analyst panel briefed to read the rlogs themselves would have repeated a
21-segment extraction six times. The panel was stopped and relaunched with one shared extraction.

**How to apply:**
- One extraction per route into `analysis-2020accord/_scratch/cache/v280/` (npz with a README of keys, rates,
  units, signs — see `r79_fork.README.md`); every analysis loads the cache and runs in seconds (the extractor
  itself: multiprocessing over segments, 10 s for 21 segments on 16 CPUs).
- Vectorise (numpy/scipy, `lfilter`, `cumsum`, `searchsorted`); a 1 kHz replay is vectorised for the memoryless
  stages with a plain-integer loop only for the stateful ones (`drive_read_fastlane.py`), cached per route × image
  × version with a source-drift hash guard that falls back to the slow path if the mirrored source changes.
- Every subagent brief carries the rule and a budget ("< 30 s on the cache; state the measured wall time").
- The optimisation is verified by byte-identical output against a saved reference run before it is accepted.
Related: [[feedback-never-sendmessage-a-running-workflow-subagent-it-resumes-a-duplicate]],
[[feedback-subagent-model-policy-opus-55-pinned-one-fable-for-the-design-synthesis]].
