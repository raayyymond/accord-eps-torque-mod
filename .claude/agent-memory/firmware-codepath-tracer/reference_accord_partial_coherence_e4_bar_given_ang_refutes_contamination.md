---
name: reference_accord_partial_coherence_e4_bar_given_ang_refutes_contamination
description: gamma^2(e4,bar|ang) -- the partial coherence between openpilot's command and the torsion bar, conditioning out steer angle -- collapses to 0.0006-0.0165 (at or below its own episode-shuffled null) across FIVE independent routes spanning 1x/6x/6x/6x/8x LKAS gain, with NO dose-response. Ordinary coherence gamma^2(e4,bar) rises clearly with gain (0.08->0.51) over the same routes. This is the direct test of the operator's "LKAS motor torque contaminates the driver-torque sensor" hypothesis and it comes back negative: the command-bar coherence that exists is angle-mediated common-cause, not a residual direct channel, and does not scale with 0xC6CD0.
metadata:
  type: reference
---

# Partial coherence closes the operator's contamination hypothesis (2026-08-22)

Ran for team-lead's explicit request: "the test that has never been run" on the operator's hypothesis
that LKAS motor torque unavoidably contaminates the torsion-bar sensor Honda's loop trusts as driver
intent. `compensator` had already found the architectural reason contamination is PLAUSIBLE (a
torsion bar measures differential twist, so motor torque appears in it by construction) but the
existing "kill" study never ran the actual discriminator and never varied gain.

## Method [EVIDENCE]
Built a 3-channel partial-coherence pipeline (standard Bendat-Piersol formula,
`gamma^2_xy|z = |Sxy - Sxz*conj(Syz)/Szz|^2 / [(Sxx-|Sxz|^2/Szz)(Syy-|Syz|^2/Szz)]`) reusing the
`Sab=conj(A)*B` spectral convention and statistical machinery (episode bootstrap, `g2_crit`,
episode-shuffle null) already established in `rlog-tools/loop_op_lib.py` — but that library's own
`ROUTES`/cache format targets an OLDER, different route set (V80-V84), so I wrote a new pipeline
against the ACTUAL cache schema for `_cache_r97/r96/r9e/ra4/r95` (single concatenated array +
`seg`/`seg_bounds`, not per-segment native-lattice files). Script:
`analysis-2020accord`-adjacent scratchpad `partial_coherence.py` (not committed, self-contained).

Channels (all build-independent per team-lead's instruction, avoiding the documented 427-source
hazard entirely): `e4 = e4tq` (openpilot LKAS command), `bar = tq` (0x18F torsion bar), `ang = ang`
(0x14A steer angle, the variable partialled out). Engaged mask = `cc_lat > 0.5` — **deliberately
dropped `cc_req`** from the mask (matching `loop_op_lib.mask_engaged`'s AND-term) because on `r97`
it measures only 1.8% duty against `cc_lat`'s 64%, inconsistent with a per-frame torque-request flag
that should roughly track it; ANDing it in would have silently discarded ~97% of engaged data on a
flag whose meaning in this cache I don't trust. **[BELIEF, not re-verified]** this choice doesn't bias
the result, but it is a genuine methodological deviation from the library's exact convention, flagged
not hidden.

Episodes: contiguous `cc_lat` runs >=512 samples, never crossing a `seg` boundary or a >50ms gap,
512-sample (~5.1s) Hann-windowed blocks at 50% hop, linearly detrended per block.

**Sanity check before trusting anything**: stock (`r97`) ordinary `gamma^2(e4,bar)` at 6-9Hz = 0.077,
same ballpark as the 0.085 figure already on the kit's record from an earlier study (not a byte
reproduction — different episode/window parameters — a qualitative cross-check only).

## The result [EVIDENCE]
```
     route  gain    K   eng_s          g2_ordinary(e4,bar)        g2_PARTIAL(e4,bar|ang)
    r97_1x     1   18   678.9s   0.0768 [0.0403, 0.1264]      0.0006 [0.0001, 0.0164]
    r96_6x     6   14   569.1s   0.3470 [0.2097, 0.5518]      0.0165 [0.0005, 0.0691]
    r9e_6x     6   11   400.7s   0.2302 [0.0974, 0.4414]      0.0028 [0.0003, 0.0569]
    ra4_6x     6   18   662.9s   0.5142 [0.1914, 0.6762]      0.0027 [0.0003, 0.0328]
    r95_8x     8    4   173.7s   0.3302 [0.2659, 0.4786]      0.0134 [0.0025, 0.0599]
```
95% episode-bootstrap CIs (1000 resamples, resampling episodes not windows). **Ordinary coherence
clearly rises with gain (0.08 -> 0.23-0.51 across the three 6x builds -> 0.33 at 8x). Partial
coherence, conditioning on angle, is small and FLAT across the entire gain ladder — 0.0006 to 0.0165,
NO dose-response, and in every single route the point estimate sits AT OR BELOW its own
episode-shuffled null** (e.g. `r96`: 0.096 vs null 0.115 at the 6-9Hz band level; `ra4`: 0.037 vs
null 0.136). `gamma^2(e4,bar|ang)` does NOT grow with `0xC6CD0`.

**Reading, without over-converting (per an explicit caution relayed from `compensator` — never turn
a coherence into a "% of the bar is motor-originated" figure):** the command-bar coherence that DOES
exist and DOES scale with gain is explainable through the angle-mediated common-cause pathway (both
channels tracking the same physical steering event), not a residual angle-independent contamination
channel. This directly refutes the operator's compensator/contamination hypothesis as a MEASURABLE
effect, closing a gap the original "kill" study left open (it only compared `gamma^2(e4,ANGLE)` vs
`gamma^2(e4,bar)`, which doesn't discriminate the two hypotheses, and never varied gain).

## Caveats, carried forward honestly
- **Manual-arm control is underpowered everywhere** (K=2-3 episodes on 4 of 5 routes, K=0 on `r95`)
  — this corpus is dominated by engaged driving. Reported for completeness, given little weight.
- **`r95`'s own episode-shuffle null is degenerate** (K=4 produces null values exceeding 1.0 in
  several bands — a known small-K artifact). Its partial-coherence *point estimate* (0.013) is still
  small and consistent with the other four routes; don't lean on its null specifically.
- **12.5ms 0x18F staleness**: used the cache's own `tq`/`ang`/`e4tq` columns on their shared ~100Hz
  grid as given — did NOT independently re-verify their relative timing via native-lattice
  reconstruction (the method `loop_op_lib.py` uses for its own, different route set is not available
  here). Coherence magnitude is far less sensitive to a small fixed lag than phase/delay, so this
  likely doesn't threaten the collapse-to-null result, but it is unverified, not verified-clean.
- Did not attempt a full 0.4-49Hz band table write-up beyond what was sent to team-lead; the 6-9Hz
  decisive band and full per-band table (7 bands, all 5 routes) both exist in the sent report/script
  output, not reproduced here.

## Related
Sent to team-lead via SendMessage, 2026-08-22, "Partial coherence collapses to noise at ALL gains".
`rlog-tools/loop_op_lib.py` — the spectral convention and statistical machinery this pipeline reused
without reusing its (incompatible) cache loader.
