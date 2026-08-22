---
name: feedback-design-the-statistic-inside-a-drive
description: "On this corpus every cross-drive band-power ratio dies to its own within-drive split-half null (route a5's spans 0.26-3.8, so a single drive cannot detect a 2.5x change on any band). Every statistic that survived this session is measured INSIDE one drive. Design the endpoint that way from the start."
metadata:
  type: feedback
---

# 🛑🛑★★★★★ DESIGN THE STATISTIC TO LIVE INSIDE A DRIVE

2026-08-22, route `a5`. **Two independent pipelines each reported a narrow-band "cut" from V105, and both
authors withdrew their own headline** once a within-drive split-half null was run.

## THE NUMBER
```
band          V105/V104              within-drive split-half NULL   verdict
18-22 Hz      1.414 [0.792, 2.723]   [0.311, 3.023]                 INSIDE
20.5-23.0     0.349 [0.159, 0.637]   [0.262, 3.758]                 INSIDE
21-28         0.236 [0.127, 0.432]   [0.344, 2.894]                 INSIDE
18-30         0.410 [0.240, 0.688]   [0.402, 2.479]                 INSIDE
32-45 placebo 1.115 [0.749, 1.845]   [0.492, 2.155]                 INSIDE
```
**The null spans 0.26–3.8. A single drive at this exposure cannot detect a 2.5× change in either
direction, on any band.** "CI excludes 1" is **not** the bar; "clears its own split-half null" is.

## WHY THE NARROW BANDS LOOKED LIKE RESULTS
The mode **moved** (22.73 → 20.48 Hz). So **18–22 Hz went UP 30 % while 20.5–23 went DOWN 65 %** on the
same drive. **A window centred high sees a cut, one centred low sees a rise, and the widest window sees
nothing.** The narrower and more envelope-selective the statistic, the bigger the apparent effect — purely
because more of the relocated mode falls outside it.

## ⭐ WHAT SURVIVED, AND WHAT THEY HAVE IN COMMON
Every survivor is measured **inside one drive**:
- **peak LOCATION and its SHIFT** — a frequency, immune to the level noise that kills ratios;
- **`|H|`-at-each-build's-own-peak** — a lookup on measured frequencies, not a measured ratio;
- **the 427-lane transfer-function shape**, normalised at 3–8 Hz, so the drive-level offset cancels;
- **the fraction of band power inside a stopband**;
- **cave rung duties**, and **engaged-vs-manual contrasts within the same drive**.

## HOW TO APPLY IT
1. **Pre-register the endpoint as a within-drive quantity** — a duty, a ratio normalised inside the drive,
   a peak location, or an engaged/manual contrast. **Not a cross-build band power.**
2. **Run the split-half null FIRST** (`feedback-run-the-control-before-the-measurement`), and bootstrap
   over **EPISODES**, not windows (`feedback-episodes-not-windows`). ⚠ One of the withdrawn results came
   from resampling **75 %-overlapped spectrogram frames** — a window bootstrap wearing an episode's name.
3. **If a cross-build number is unavoidable, mark it NOT-CURRENTLY-DECIDABLE** rather than reporting it.
4. **Build the readout into the firmware** where possible — V106 verifies its own dose from a carried
   comparator rung, needing no cross-build contrast at all. That is the strongest form of this rule.

🛑 **AND THE CHEAPEST FIX NEEDS NO BUILD:** an **alternating drive** — ~30 s engaged / 30 s manual at
5–15 km/h, same road, same session. It removes the between-drive variance that generates this null *and*
the one-stock-route confound the whole corpus rests on. **Open since the V105 handoff; still not done.**

Related: [[feedback-run-the-control-before-the-measurement]] · [[feedback-episodes-not-windows]] ·
[[accord-v105-relocated-the-mode-not-damped]] · [[accord-averaged-spectrum-needs-matched-speed-distributions]]
