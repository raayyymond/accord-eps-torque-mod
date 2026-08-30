---
name: feedback-never-quote-a-ratio-without-a-ci
description: "Never quote a band ratio without an episode-level CI and a power check. Use rlog-tools/lib/band_contrast.py -- an inline median bypassed a guard written the same hour and produced two findings that had to be withdrawn."
metadata:
  type: feedback
---

🛑 **Never quote a band ratio without an episode-level CI AND a power check.**
Use `rlog-tools/lib/band_contrast.py`. It returns a `Contrast` whose `str()` refuses to print a bare
number — it always carries the CI, the arm sizes, and whether the result is licensed.

## Why this is a memory and not a note

On **2026-08-30** I wrote a `MIN_EPISODES = 8` guard into the pre-registered scorer specifically to
stop under-powered comparisons being read as evidence — and then, **within the hour, bypassed it twice**
by computing `np.median(A) - np.median(B)` inline. Both results were reported as findings and both had
to be withdrawn:

- *"the record’s 8× dose curve is contradicted at 22–26 Hz"* — the CI was **[-0.331, +0.160]**, spanning
  zero, on **7 episodes**. The honest statement was **"I could not reproduce it"**.
- *"CAN agrees with the operator in 2 of 3 bands"* — only **one** band was powered.

**The failure was ERGONOMICS, not carelessness.** An inline median is three characters; calling the
scorer is a subprocess. The unsafe path was the convenient one, so it got taken — by the same agent
that had just built the guard.

## The trap the helper catches that a CI alone does not

A CI can **exclude 1.0 and still license nothing**. The self-test carries the real case: 7 vs 24
episodes gives `1.240 [1.023, 1.690]` — significant-looking, and **refused**, because a 7-episode arm
cannot support it. **Power and significance are different checks and both are required.**

## What to do

```python
from band_contrast import band_contrast, episodes
a = episodes(values_a, fs, mask=engaged_a)     # episodes, NOT windows
r = band_contrast(a, b)
if r.licensed: ...                              # otherwise say so, do not report a direction
```

Related: [[feedback-episodes-not-windows]] · [[feedback-run-the-control-before-the-measurement]]
