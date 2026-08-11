---
name: accord-placebo-pair-is-mandatory-for-cross-build-claims
description: "A same-firmware placebo pair is MANDATORY for any cross-build band claim, and the band contrast does NOT rescue a thin cut. Route 77 vs route 75 is byte-identical firmware and returned e_6-9 = 1.288 [1.017, 1.661] with the 32-38 Hz band contrast ALSO excluding 1.00. The honest resolution floor is +/-16-22% contrasted, +/-33% raw."
metadata:
  type: reference
---

# A same-firmware placebo pair is MANDATORY — measured 2026-08-11

V90 changes **no calibration cell** (it is probe-only, byte-identical to V89), so **route 77 vs routes
75/76 is the SAME FIRMWARE on different drives**. That makes it a free, exact placebo pair:

| pair (SAME FIRMWARE) | `e_6-9` | `e_18-22` | `e_32-38` (control) |
|---|---|---|---|
| **r77 ÷ r75** | **1.288 [1.017, 1.661]** — CI **excludes 1** | 1.121 [0.870, 1.472] | 0.993 [0.807, 1.189] |
| r77 ÷ r76 | 1.340 [0.925, 2.259] | **1.333 [1.001, 2.307]** — CI **excludes 1** | 1.379 [0.977, 2.164] |

🛑 **Two drives on byte-identical firmware produce band ratios whose episode-block CIs exclude 1.00 —
and one of them excludes 1.00 on the BAND CONTRAST as well.**

⇒ **The band contrast does NOT rescue a thin cut.** Differencing against the 32–38 Hz control removes
some drive-to-drive variance; it does not remove enough to make a 10–15 % band change resolvable.

**The honest floors, derived from this session's own placebo rather than assumed:**
- **32–38-contrasted statistic**: placebo band **[0.845, 1.221]** ⇒ resolvable only if **≥ 15.5 % down
  or ≥ 22.1 % up**.
- **raw ratio**: placebo band **[0.820, 1.261]**, and whole-route same-firmware pairs ran as high as
  **1.333** ⇒ the honest raw-ratio floor is **≈ ±33 %**.

**Consequences, all of them operational:**
1. **Any cross-build ratio quoted with a block-bootstrap CI and no placebo-pair null is
   over-confident.** This is the concrete instance of the standing ~2.8× understatement.
2. On a thin stratum it gets worse, not better: on the loosest populated grind-#2 cut the
   **same-firmware** r77 ÷ r75 pair returns `e_18-22` **1.504 [1.184, 1.732]** with one stratification
   cell, i.e. no matching at all.
3. ⊕ **A no-hypothesis placebo BAND (`e_10-16`) is the cheap tell for a stratum artefact** — if it
   also reads "resolvable", the effect is the stratum, not the band. That is exactly how the one
   apparent V89 grinding regression (1.451 at v ≥ 20.46 m/s) was shown to be an artefact.
4. **If a build produces two routes, its own internal pair is the better placebo and should be used as
   well.**
5. ⊕ **The cheapest real fix is not statistical: fly the next build on the SAME ROUTE.** Same driver,
   same roads, adjacent in time — the best-matched cross-build pair this kit can construct, and the
   only lever on the ±20–33 % floor that does not need new methodology.

Source: `docs/SCORING-2026-08-11-v90-flight.md` §6.1, §10.2, §10.3.
Related: [[feedback-episodes-not-windows]] · [[feedback-run-the-control-before-the-measurement]] ·
[[accord-averaged-spectrum-needs-matched-speed-distributions]]
