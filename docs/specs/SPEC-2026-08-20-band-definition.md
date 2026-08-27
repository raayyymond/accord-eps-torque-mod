# SPEC — 2026-08-20 — THE ANALYSIS BAND. **20–28 Hz becomes primary.**

**Status: PRE-REGISTERED. Approved by the operator, 2026-08-20, before V103 flies.**
Supersedes the bare `21.5–25.5 Hz` of the V102 readout for all forward work.

---

## 1. THE RULE

| band | role | use it for |
|---|---|---|
| **20.0 – 28.0 Hz** | ⭐ **PRIMARY for band-RMS** | every new band-RMS / band-power statistic from V103 onward |
| **`f0` — NOT A BAND** | ⭐⭐ **PRIMARY for `Re(Z)`** | the damping **zero-crossing frequency**. **See §4 — it is a different KIND of endpoint** |
| 22.0 – 26.0 Hz | fixed-band `Re(Z)` sign test | retained as a secondary; monotone in `f0`, does not false-pass |
| 21.5 – 25.5 Hz | **LEGACY, retained** | comparability with the V100 / V101 / V102 record only |
| 32.0 – 38.0 Hz | negative control | unchanged |
| 2.5 – 4.5 Hz | shape denominator | unchanged |

🛑 **THE `Re(Z)` PRIMARY IS NOT A BAND AT ALL.** It is `f0`, the frequency where damping crosses
zero. **That retires the migration problem by construction — a crossing that moves cannot escape an
endpoint that IS the crossing's location.** §4 is the rule; read it before applying anything here.

**Report both.** A V103 number quoted only in the legacy band is not comparable to future builds; a
number quoted only in the primary band is not comparable to the existing record. **Neither alone is
sufficient, and where they disagree the primary band is the one that carries the conclusion.**

---

## 2. WHY — THE MODE MIGRATES IN TWO DIMENSIONS

This is the whole justification. It is forward-looking and it does not depend on any claim about
estimator bias.

**(a) The mode moves with GAIN — ~+1 Hz per doubling.** Per-window local-max peak frequency,
speed-slope removed, evaluated at a common 40 km/h (`rlog-tools/score/score_v102_ancova.py`):

| build | gain | f₀ @ 40 km/h | 95 % CI |
|---|---|---|---|
| V100 | 4× | 21.13 Hz | [20.46, 21.84] |
| V102 | 6× | 22.01 Hz | [21.54, 22.45] |
| V101 | 8× | 23.33 Hz | [22.90, 23.82] |

4×→8× = **+2.21 Hz [+1.35, +3.04]**, separated.

**(b) The mode moves with SPEED — +0.157 Hz/(m/s).** Per-window peak frequency regressed on the
window's own speed, pooled across V100/V102/V101 (they agree within error):
**+0.1594 [+0.1362, +0.1844] Hz/(m/s) on V102.**
🛑 **It is NOT a wheel order** — the order-1 tyre slope +0.4890 is excluded by ~14 σ.

**(c) The two compose, and the model is validated.** It predicts V102's mode at 100 km/h as
`22.01 + 16.7 m/s × 0.157 = 24.63 Hz`. **Measured at 95–115 km/h: 24.71 Hz [24.41, 24.71],
prominence 93.7 over 26 windows. Error 0.08 Hz.**

### ⇒ THE LEGACY BAND IS ALREADY CLIPPING, AND WILL CLIP WORSE

- **V102 at highway speed sits at 24.71 Hz — 0.79 Hz below the 25.5 Hz edge.** Already marginal.
- **8× at highway speed extrapolates to ~25.9 Hz — OUTSIDE 21.5–25.5 Hz entirely.**
  V101 never drove highway, which is the only reason this has not yet bitten.
- 20–28 Hz gives the mode **≥ 3 Hz of headroom** across the whole reachable gain × speed envelope.

🛑 **AND IT PASSES THE 427 NYQUIST.** `0x1AB` samples at **49.81 Hz ⇒ Nyquist 24.9 Hz** on this
route generation. **A mode above 24.9 Hz aliases and INVERTS on that lane.** V102's 24.71 Hz is
0.2 Hz under it. **427 must not be used to read this band on any build at or above 6× at highway
speed** — the bus channels (`0x18F` `tq` / `rate_f` at 100.74 Hz) carry it at full fidelity.
⚠ `v102_xb_lib.CH_NYQ` hard-codes `x6b94: 20.0`, correct for the older 41.7 Hz generation and
**wrong for this one.** Anyone reusing it across generations clips the wrong band.

---

## 3. 🛑 WHAT THIS SPEC IS **NOT** JUSTIFIED BY — a struck argument

An earlier version of this recommendation rested on a claim that the 25.5 Hz edge was clipping
V102's line via **Hann leakage**, producing a 3× discrepancy between two agents' estimators.

**THAT CLAIM IS WITHDRAWN. It was measured and refuted.** Against synthetic signals of known band
power (`rlog-tools/studies/v102-crossbuild/v102_estimator_control.py`), a line 0.8 Hz from the edge — V102's exact case —
costs the Hann estimator **4.9 %**, roughly **60× too little** to explain the discrepancy. The real
cause was **time-smearing in a brick-wall band-pass interacting with V102's extreme burstiness**
(1 s band-power p90/p50 = **59.5**, against V101's 2.74).

**Do not re-cite leakage as a reason for this spec.** The migration argument in §2 stands entirely
on its own and is the only justification.

---

## 4. SCOPE — WHICH STATISTICS THIS BINDS. **Two kinds of endpoint, two rules.**

### BINDS: every absolute band-RMS / band-power statistic, and every shape ratio built on one
**Use 20–28 Hz.** A band-RMS endpoint needs the **line** inside the band, so a mode migrating
+0.157 Hz/(m/s) and ~+1 Hz per gain doubling walks straight out of a 4 Hz window. No protection.

### DOES NOT BIND: `Re(Z)`. **Its primary is `f0`, not a band.** — measured, `route-stock`

`Re(Z)` is different **in kind**: a ratio of cross- to auto-spectrum over the same bins, so it
measures the damping **of the band**, not the amplitude **of a line**, and a bandwidth change scales
numerator and denominator together. Across band choices the **sign is robust** (STOCK/V102:
+300/−147 at 21.5–25.5 · **+398/−128 at 22–26**, best coherence 0.870 · +338/−100 at 20–28) but at
18–30 both CIs touch zero. **The SIGN is robust to band choice; the SIGNIFICANCE is not — widening
dilutes `Re(Z)` with content that is not doing the work.**

### ⭐ AND THE ANTI-DAMPING IS NOT A NOTCH ON THE MODE — it is a REGION with a MOVING EDGE
Sliding a 2 Hz window across 16–36 Hz (`rlog-tools/studies/impedance/rez_band_tracking.py`), the negative region runs
from low frequency up to a **zero crossing**, and **our builds push that crossing UPWARD**:

| arm | gain cal | **`f0`** | 95 % CI | n_win |
|---|---|---|---|---|
| **STOCK 1×** | 891 | **21.90 Hz** | [21.08, 23.03] | 102 |
| V100 4× | 3564 | **23.61 Hz** | [23.22, 23.95] | 22 |
| V102 6× | 5346 | **24.90 Hz** | [24.63, 25.26] | 51 |

**All three CIs mutually disjoint.** Fit: **`f0` ≈ 21.3 + 0.60 × (gain multiple) Hz** — linear in
gain, *not* in log-gain.

> **⇒ `f0` IS THE `Re(Z)` PRIMARY.** Continuous, graded, uses every band, and has a **stock target
> (21.90 Hz)** to aim at. **It retires the migration question by construction.**

ⓘ The fixed-band 22–26 Hz sign test is **retained as a secondary and does not false-pass**: it is
monotone in `f0` (crossing below 22 ⇒ positive ⇒ pass; above 26 ⇒ negative ⇒ fail). `f0` is simply
strictly better. **Report 20–28 Hz alongside as a pre-declared robustness check.**

### 🛑 THE CAVEAT THAT SURVIVES — now conditional on gain, and it STRENGTHENS §2
**Robustness to bandwidth is not the same as being evaluated in the right place.** `route-stock`,
explicitly: *"it is not immune; if the mode migrated entirely past 28 Hz the band would stop
containing it — but at 6× it sits mid-band with headroom on both sides."*

⇒ **At V103's 6× this is SETTLED.** ⇒ 🛑 **LIVE AGAIN at 8×**, where the law predicts
**`f0` ≈ 26.1 Hz — putting the ENTIRE legacy 21.5–25.5 band, and most of 20–28, inside the
anti-damped region.** **Any build at or above 8× must re-open this section before quoting `Re(Z)`
in a fixed band.**

⭐ **This is the stronger form of §2's argument, and it is measured, not extrapolated:** it is not
merely that a *line* walks out of a *window* — **the whole damping structure translates upward with
gain.**
⚠ **[BELIEF, not evidence]** V102's mode (24.61–24.71 Hz at highway) sits almost exactly on V102's
`f0` (24.90 Hz), which would identify the two. **Untestable today** — V101 is the discriminating
case and it has no hands-off windows. **Do not state the identification as established.**

---

## 5. HOW TO APPLY IT

- `rlog-tools/lib/v102_xb_lib.py` `BANDS`: add `"20-28": (20.0, 28.0)`. **Do not remove `"22-26"` or
  `"21.5-25.5"`** — the record depends on them.
- Every new scorer prints **both** bands side by side.
- **State the window length with every number.** The endpoint moves ~25 % between 1 s and 2.56 s
  windows, and it moves most on the burstiest arm. A band figure without its window length is not
  reproducible.
- 🛑 **State the summary statistic too.** On V102 the matched-speed V102/V101 ratio is
  **median 0.381 · mean 0.644 · RMS-total 0.850** — the choice spans most of the decision range.
  **The median over 1 s engaged windows remains the pre-registered statistic.**

---

## 6. THE HONEST LIMIT OF THIS SPEC

Widening the band **cannot rescue a build whose mode leaves the envelope entirely**, and it does not
make any of the existing V100/V101/V102 numbers wrong — those modes (20.2 / 23.0 / 22.0 Hz at
40 km/h) all sit comfortably inside the legacy band. **This spec buys headroom for what comes next;
it corrects nothing already written.**
