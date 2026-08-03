---
name: accord-segs2b-bug-hid-the-kd1-highway-baseline
description: A hardcoded segment list in TWO helper modules excluded route 2b's highway leg, hiding the only Kd=1 highway baseline for three sessions
metadata:
  type: reference
---

🛑 **`_r31_common.SEGS_2B` AND `_r37_ratchet_lib.ROUTES` both enumerate route `2b` as
`[0, 1, 2, 11, 12, 13]`.** Route `2b` (V58) has **14 segments**, and **segments 3–10 are its highway
leg** — **227 s of highway-engaged driving at Kd = 1.00×**, the only stock-rate-lane highway exposure
in the entire corpus.

**Consequence, and it is not hypothetical.** Three sessions concluded *"no Kd = 1 highway baseline
exists"* and built analyses around that. It is what let a confident, arithmetically-correct prediction
(*"V67 delivers 2.44× at highway, its maximum, 22% above the V62 dose that raised 40–49 Hz by 11.7×"*)
stand unrefuted, because the one comparison that could refute it looked impossible. With `r2b`'s full
segment list restored, the three-dose highway comparison is a clean **null** (40–49 Hz **0.970
[0.787, 1.154]** and **0.938 [0.764, 1.184]** against a split-half null of **[0.73, 1.37]**), and the
**corpus-maximum highway envelope sits on `r2b` itself, at Kd = 1.00×** — the stock lane.

## How to use route 2b correctly
- `_grind2_lib.BUILDS` now registers **V58/`r2b` with all 14 segments** (172 highway-engaged windows /
  24 blocks / 5 runs).
- ⚠ It was **deliberately NOT added** to `G.ORDER` / `G.DOSE`, because every `analyze_grind2_*.py`
  iterates those and the creep-focused analyses were validated without it. The highway pools live in
  `_r47_lib.ORDER_HWY` / `DOSE_HWY`. **Promote it deliberately, not by accident.**
- ⚠ `r2b`'s cache is from the older extractor: it has `tq`, `ang`, `cs_v`, `cc_lat`, `rate_c/f` but no
  `cs_gear` / `clk_*` / probe fields. Everything a band analysis needs is there.

## The general lesson
**A hardcoded subset in a helper module is invisible to every analysis that imports it**, and it does
not announce itself the way a missing file would — the code runs, the numbers look reasonable, and the
excluded data simply never appears. Two separate modules carried the same wrong list, so a
cross-check between them would have agreed.

⇒ **Before concluding that a measurement cannot be made, count the exposure across the whole corpus
from the caches themselves**, not through a helper's route table. One cheap loop:
`analysis-2020accord/r47_orchestrator_checks.py exposure`.

Related: [[feedback-check-the-data-exists-before-concluding-it-doesnt]],
[[accord-v67-flew-both-grinds-fixed]].
