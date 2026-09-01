# PRE-REGISTRATION — how to read V276's log at 2–4 Hz

Written **2026-09-01, BEFORE the V276 rlog exists.** Operator report: *a large self-exciting
2–4 Hz oscillation, LKAS-engaged only, at all speeds, on straight roads, stoppable only by
gripping the wheel firmly.*

Standing kit law: *a build whose null is uninterpretable is a design failure on our side.*
This file fixes the statistic, the threshold and the refutation **before** the data lands, so
the read cannot be steered by the result. **Do not edit the thresholds after the log arrives** —
if one turns out wrong, say so in the report and leave the original standing.

Scripts that produce every number below (all under `rlog-tools/studies/osc-2to4/`):

| script | what it gives |
|---|---|
| `rescore_2to4hz_all_routes.py` | raw 2–4 Hz levels, engaged vs manual, all channels (**confounded — see below**) |
| `band_excess_2to4_speed_matched.py` | **the primary instrument** — speed-stratified `excess24`, `coh24`, `gain24` |
| `v101_recheck_and_noise_floor.py` | the V101 re-check, the within-route noise floor, the r66/V80 precedent check |

---

## 0. The instrument, and why the obvious statistic is useless

**Do NOT read V276 on raw 2–4 Hz power.** EVIDENCE: raw engaged 2–4 Hz steering-rate power
spans **500×** across the flown corpus and its ranking is ordered by *route regime*, not by
build — the top six are the short parking-lot routes (r80, r82, r6f, r70, r81, r71), the bottom
are the long highway routes. 2–4 Hz power is the tail of the 1/f steering spectrum, so any
route with more low-frequency wheel motion scores higher. A cross-build claim off that number
is an artefact.

The three statistics that ARE regime-robust, each computed inside a speed stratum
(LOW 1–8, MID 8–18, HIGH ≥18 m/s) on contiguous engaged runs ≥ 5.12 s:

- **`excess24`** — mean PSD over 2–4 Hz ÷ the power-law baseline interpolated through the
  1.0–1.6 Hz and 5–6 Hz shoulders. A pure 1/fⁿ tail gives ≈1.0 whatever the regime.
  **> 1 means real energy is parked in 2–4 Hz.** Computed on `rate_f` (0x18F steering rate),
  `ang`, `tq`, and on the command `e4tq` / `co_req`.
- **`coh24`** — coherence² between the wire command `e4tq` and `rate_f` over 2–4 Hz.
- **`gain24`** — `sqrt(mean P_rate / mean P_cmd)` over 2–4 Hz: deg/s of column rate delivered
  per count of commanded torque. **This is the loop gain the operator can feel.**

⚠ Deliberate deviation from the house scorer, and it matters at this band: the house scorers
mask by **zeroing** (`np.where(m, x, 0)`) and welch the whole route. Every mask edge is a step,
and step energy goes as 1/f² — i.e. straight into 2–4 Hz. These scripts extract **contiguous
runs** instead. FS, `nperseg=512`, `noverlap=256` and the mean-removal are the house values.

---

## 1. The baseline V276 is to be placed against

EVIDENCE. 35 cached routes, **V74 → V122 plus a stock control**, mapped to builds by the npz's
own `probe_build` field (four resolved from `BUILD-LINEAGE-CATCHUP-V76-V100.md`). Engaged
cells with ≥ 60 s, MID+HIGH strata, n = 48:

| statistic | p05 | p25 | **p50** | p75 | p95 | max |
|---|---|---|---|---|---|---|
| `excess24` `rate_f` | 0.50 | 0.66 | **0.83** | 1.05 | 1.40 | 1.82 |
| `excess24` `ang` | 0.46 | 0.53 | **0.66** | 0.95 | 1.24 | 1.47 |
| `excess24` `e4tq` (command) | 0.71 | 0.82 | **0.91** | 1.05 | 1.27 | 1.63 |
| `excess24` `co_req` (op command) | 0.72 | 0.83 | **0.90** | 1.03 | 1.36 | 1.57 |
| `coh24` (e4tq → rate_f) | 0.21 | 0.28 | **0.44** | 0.56 | 0.74 | 0.84 |
| `gain24` | 0.009 | 0.013 | **0.018** | 0.027 | 0.048 | 0.059 |

🛑 **The headline: `excess24` sits at or BELOW 1.0 in the median. There is NO 2–4 Hz resonance
anywhere in the flown corpus.** The band carries less energy than its own shoulders predict.
Whatever V276 is doing is **new**, not the end of a trend. (BELIEF, one inference deep: this
also means the year of "no effect" nulls computed on 6 Hz-and-up band sets were not hiding a
2–4 Hz effect — there was nothing there to hide.)

**Within-route noise floor** (bootstrap, contiguous engaged run = the resampling unit, per
`accord-cluster-bootstrap-route-is-the-unit`): the 95 % interval on `excess24` spans a factor
of **2.15×** (p50; max 7.78×), on `coh24` 2.14×, on `gain24` 2.24×. **A V276 reading inside
±2.2× of the corpus median is NOT a detection.**

**The corpus contains no sustained 2–4 Hz oscillation precedent.** The single cell that
resembles the V276 report — r66 / V80, engaged, ≥18 m/s, `excess24` 6.48 on the rate and 9.44
on the command, `coh24` 0.973 — is **one 32.6 s run** (t = 499–532 s), the only qualifying run
in that cell. A single transient, not a precedent. EVIDENCE.

---

## 2. 🛑 THE DISCRIMINATOR — the one number that decides whether V278 should exist

Compute, on V276's engaged runs, in each speed stratum:

```
rate_excess24   = excess24(rate_f)      the RESPONSE
cmd_excess24    = excess24(e4tq)        the DELIVERED command  (cross-check on co_req)
coh24, gain24   as defined above
```

| what you see | mechanism | where the fix is |
|---|---|---|
| **`cmd_excess24` ≥ 2.5 AND `coh24` ≥ 0.8**, rate follows | **openpilot's OUTER loop is ringing** — it is reacting to a plant V276 made more responsive | **comma side.** Retune openpilot's lateral controller (or back V276's dose out). **A firmware V278 aimed at 2–4 Hz would be the wrong lever.** |
| **`cmd_excess24` ≤ 1.3 (inside the corpus p75) while `rate_excess24` ≥ 2.5** | **EPS INNER loop is ringing** — the ECU is oscillating on a smooth command | **firmware.** V278 exists, and it targets whatever V276 raised. |
| **both ≥ 2.5 with `coh24` ≤ 0.5** | common external drive, or two separate effects | neither yet — instrument further before building |

**Supporting number in every case: `gain24`.** Corpus p50 **0.018**, p95 **0.048**. If V276
reads `gain24` ≥ 0.10 — above every cell in 48 and ~5× the median — the plant genuinely became
more responsive at 2–4 Hz, and that is true whichever loop is ringing. If `gain24` is inside
[0.009, 0.048] the "more responsive plant" story is **refuted** and the oscillation is
something else.

---

## 3. Every pre-registered threshold, in one table

| # | claim under test | CONFIRMS if | REFUTES if |
|---|---|---|---|
| 1 | there is a real 2–4 Hz oscillation at all | `excess24(rate_f)` **≥ 2.5** engaged, in ≥ 2 speed strata, ≥ 120 s each | `excess24` **≤ 1.4** (corpus p95) — then the symptom is not in this band and the whole read is void; **re-scan 0.5–10 Hz before anything else** |
| 2 | it is a PEAK, not broadband | strict interior local max of the excess curve in 1.6–5.0 Hz with **peak excess ≥ 3** and **Q ≥ 3**, at the **same centre frequency (±0.4 Hz) in every stratum** | no interior max, or centre frequency moving > 1 Hz between strata ⇒ broadband tilt, not a mode |
| 3 | it is ENGAGED-ONLY (his words) | engaged `excess24` ÷ manual `excess24` **≥ 3** in a matched speed stratum with ≥ 60 s in both arms | ratio ≤ 1.5 ⇒ it is present manually too and is not LKAS-driven. ⚠ this test needs manual frames at speed — **most routes in the corpus have zero**, so if V276's log has none either, this test is *unavailable*, NOT negative |
| 4 | 🛑 **command vs response** (§2) | see §2 table | — |
| 5 | it is SELF-EXCITING (growing), not driven | the 2–4 Hz analytic envelope of `rate_f` shows episodes rising **≥ 3×** over ≥ 3 s with no matching rise in the road/curvature input (`ct_dcurv`) | envelope tracks `ct_dcurv` ⇒ it is a response to road input, not self-excitation |
| 6 | gripping the wheel kills it (his words) | `excess24` computed on hands-ON frames (5 s median `\|tq\|` **≥ 1200**, the house threshold) is **≤ 1/3** of the hands-OFF value | no hands-on/off difference ⇒ his "stoppable by gripping" is damping the *symptom* he feels, not the *measured* mode, and the mechanism story needs re-examining |
| 7 | the plant got more responsive | `gain24` **≥ 0.10** | `gain24` inside the corpus [0.009, 0.048] |
| 8 | it is at ALL speeds (his words) | `excess24` ≥ 2.5 in **all three** strata | present in one stratum only ⇒ speed-dependent, and the report's "all speeds" is the feel, not the measurement |

**What a "do not build V278" verdict looks like** — write it down now so it is possible:
test 1 refutes (`excess24` ≤ 1.4), **or** test 4 lands in the OUTER-loop row, **or** test 7
refutes while test 4 is ambiguous. Any of those and the correct next action is a comma-side
change or a V276 back-out, **not** a firmware build.

---

## 4. The V101 re-check (asked, and answered here rather than in the V276 read)

**EVIDENCE: V101's rejection was NOT a misfiled 2–4 Hz event.** V101 (route r95) flew 8× LKAS
gain and was rejected for *"grinding/vibration at all speeds, only while LKAS commands"* — the
same grammatical shape as the V276 report. Engaged, v ≥ 8 m/s, each band as a fraction of the
route's own 1–40 Hz total, z-scored against the corpus:

```
band     1-2    2-3    3-4    4-6    6-9   9-12  12-16  16-22  22-30  30-40
V101 z  -0.58  -0.57  -0.60  -0.63  -0.02  -1.05  -0.97  -0.79  +1.08  -0.82
```

V101 is **below** the corpus median in every band except 22–30 Hz, and puts **83.2 %** of its
engaged 1–40 Hz steering-rate energy into 22–30 Hz. Its 2–4 Hz fraction (0.0045) is among the
lowest in the corpus. The original 22–30 Hz filing was right.

⊕ One V101 observation worth carrying into the V276 read, marked **BELIEF**: V101 has the
corpus's tightest command↔rate coupling in the MID stratum (`coh24` 0.764, `coh69` 0.815, vs
MID medians ~0.28 / ~0.33) with an entirely ordinary `excess24` of 1.12. So **8× gain raised
the coupling without creating a 2–4 Hz mode.** If V276 shows high `coh24` *and* high
`excess24`, that combination is new and is not simply "more gain".

---

## 5. Coverage — read this before trusting any cross-build statement

🛑 **The cached corpus stops at V122.** 35 whole-route caches: V74, V75, V76, V80, V84?, V85,
V86, V86B, V87, V88, V89 (×2), V90, V91, V92, V94, V96? (×2), V97?, V98, V99, V100, V101,
V102, V103, V104, V105, V106, V107 (×2), V108-or-V111, V112 (×2), V122, and a stock control
(r97). **Nothing between V123 and V276 has a cached rlog.** So the "was 2–4 Hz already rising?"
question is answered only up to V122 — after which **154 build revisions are unobserved**.
State the gap explicitly in any claim about a trend.

Per-route engaged exposure and the qualifying cells are printed by
`band_excess_2to4_speed_matched.py`; routes with < 60 s in a stratum are excluded from every
baseline above. Four routes (r7d/V94, r80/V97?, r81/V98, r82/V99) have too little engaged time
at speed to contribute to the MID/HIGH baseline at all.
