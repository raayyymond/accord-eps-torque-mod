---
name: feedback-episodes-not-windows
description: "🛑 Bootstrap over EPISODES, never windows, and establish the noise floor with a split-half null BEFORE quoting any ratio — this retracted three of my own claims in one session."
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 9d7a82e7-3e41-4e6c-8c21-5e0df8ff0133
  modified: 2026-08-01T01:42:25.060Z
---

Windows inside one contiguous run are correlated. Bootstrapping over **windows** shrinks every CI by
~`sqrt(windows_per_episode)` (≈√28 on route 37) and **manufactures significance**. Shrinking NFFT does
not help: 256/128/64 gave 266/537/1086 windows but **18/19/19 episodes**.

**Why:** on the V62 drive this cost three claims I had already reported to the operator —
(a) *"V62 amplified the ratchet 2–3×, effort-gated"* (inside a 2.2× noise floor; every CI covered 1),
(b) *"band power tracks driver effort"* (it tracks **motor rate**; partial ρ(effort|rate) is **negative**,
ρ(rate|effort) is **+0.57…+0.70**), and (c) *"f0 shifted 8.18 → 7.71 Hz"* (**Simpson's paradox** — f0
rises with speed on every build).

**How to apply, in order:**
1. **Split-half-by-episode null first** to get the resolution floor. Judge every ratio against *that*,
   not against 1.0.
2. **Negative-band control** — a band where neither effect lives. That is what makes a band-specific
   claim defensible rather than a route/gain offset.
3. **Speed-standardise** every ratio (per speed sub-bin, weighted geometric mean).
4. **Count distinct BURSTS, not crossings** — 43 excursions inside one 0.92 s burst is n = 1, not 43.
5. **Pool a WITHIN-route contrast across routes** when you need power; cross-route exposure weakness
   does not apply. That took the ratchet's LKAS gating from p = 0.10 per route to **p = 1.09e-08**.

★ Prefer `|d(tq)|` (transients) over band power for **cross-route** comparison — true cross-route null
0.87–0.92 vs 0.63–1.23. ⚠ But it is a high-pass of `tq`, so don't double-count it as independent.
⚠ Also: averaging overlapping-window spectra then taking prominence of the average invents lines that
no per-window presence test supports.

Pairs with [[feedback-probe-the-gate-not-just-the-output]].
