# V290 ROW S — IS THE WITHIN-DRIVE CONTROL READABLE FROM ONE SHORT DRIVE?

**Agent**: `powerS` (SUBAGENT, orchestrator `main`). **Analysis only — nothing built, flashed or sent.**
Date 2026-09-09.

**Scripts (everything below reproduces from these two)**
- `rlog-tools/studies/grind/powerS_row_readability.py` → `_scratch/powerS_row_readability.{txt,json}`
  — strata, confound floor, power, minutes, P(usable), parametric exposure, duty-class comparison.
- `rlog-tools/studies/grind/powerS_sizing_dbit.py` → `_scratch/powerS_sizing_dbit.{txt,json}`
  — sizing the minimum cave bit, unpaired and paired.

**Inputs read, not re-derived**: the census episode cache
`rlog-tools/studies/grind/_scratch/grind1_census_v289_r62_r63_cache.pkl` (176 base + 27 V289 episodes,
`census62`'s pipeline, reproduction-asserted against the stored V282 census), the route caches under
`analysis-2020accord/_scratch/cache/`, `_scratch/scalecheck_x4_r62_r63.txt`, and
`docs/review/V290-DECISION-TABLE-2026-09-09.md` §5 for the candidate and its predicted effect.

---

## 0. THE HEADLINE

**Row S as specified is NOT readable from one short drive, and the within-drive control is not the reason
— the DECAY-RATE ESTIMATOR is.** The two answers the brief asked for, first:

- **THE CONFOUND FLOOR (item 3).** On the base builds, where Kd is flat 128 everywhere so any stratum
  difference is confound, the low-demand and high-demand grinding episodes differ **enormously in
  amplitude and duration and negligibly in frequency**, and **the decay rate cannot be pinned at all**:

  | metric, base pool (V282pool + V288, n = 44 low vs 56 high) | idx ≤ 22 ÷ idx ≥ 32 | 95 % CI | verdict |
  |---|---|---|---|
  | line frequency f0 | **0.988** | [0.966, 0.998] | resolved confound, small (−1.2 %, ≈ 0.24 Hz) |
  | envelope peak | **0.585** | [0.507, 0.713] | **RESOLVED CONFOUND — low-demand rings are 41 % quieter** |
  | duration | **0.500** | [0.204, 0.664] | **RESOLVED CONFOUND — low-demand rings are half as long** |
  | decay rate \|gd\| | 0.940 | **[0.340, 2.006]** | **not resolved on 98 episodes; CI spans ×5.9** |
  | ζ | 0.968 | [0.336, 2.328] | not resolved; CI spans ×6.9 |

  ⇒ **The confound floor on the metric row S targets is a factor of ×5.9 of unresolved uncertainty, and
  the effect row S predicts is ×2.29.** Correcting the target for the measured confound gives a band of
  **×0.78 to ×4.60** — the base's own stratum uncertainty *alone* straddles the effect. And the two
  operator-facing proxies (how loud, how long) are **not usable at all**: they are confounded by 2× in
  the direction that would masquerade as a cure.

- **THE VERDICT (item 4).** **NOT readable without a cave** — and the cheap cave bit named in the brief
  (a comparator on which Kd knot interval is live) **does not fix it**, because the stratification is
  already reconstructed to 99.65–99.85 % exact-integer agreement. **The minimum instrument that works is
  a MAGNITUDE comparator on |D|, read as a duty and adjudicated against a per-episode mirror
  prediction — and even that measures LIVENESS AND DOSE, not the 582 → 254 ms claim.** A *sign*
  comparator on D would be structurally blind: scaling Kd does not change sign(D).

**What a null licenses is therefore very little, and §5 writes the sentence.**

---

## 1. IS IT POWERED? (item 1)

### 1.1 The estimator's dispersion

The census's per-episode decay estimator is `growth_fit`'s log-envelope fall slope `gd` (/s), with
ζ = |gd| / (2π f0). It is **extremely heavy-tailed**:

| arm | n | p50 \|gd\| | geo mean | **sd(ln\|gd\|)** | p25 | p75 | p75/p25 |
|---|---|---|---|---|---|---|---|
| r39 (V282) | 79 | 3.224 | 2.637 | 1.304 | 0.968 | 8.833 | **9.1×** |
| V282pool | 130 | 3.218 | 2.420 | 1.400 | 0.964 | 8.663 | **9.0×** |
| r5e_v288 (V288) | 44 | 1.542 | 1.611 | 1.235 | 0.539 | 4.392 | **8.1×** |
| V289pool | 24 | 3.285 | 2.820 | 1.168 | 1.180 | 7.679 | **6.5×** |

**Base pool (V282pool + V288, n = 174): sd(ln|gd|) = 1.368, i.e. a ×3.9 one-sigma spread per episode.**
[EVIDENCE: the per-episode values are the census's own, unchanged.]

The physical reason is in the census itself: §7d found only **7 command-quiet stretches in all of
V282pool and 1 in all of V289pool**. These are not free rings — the envelope slope is a mixture of
damping and excitation, and the excitation varies episode to episode far more than the damping does.

### 1.2 Episodes needed

Bootstrap-by-episode (the kit convention), resampling ln|gd| from the base pool and multiplying the
treated arm by the hypothesised ratio. **The false-positive column is quoted first, because for n ≤ 3
the bootstrap CI on a median of 1–3 values has near-zero width and the test is invalid.**

| n/arm | FPR at ×1.00 | ×1.50 | **×2.29** | ×3.00 | ×5.00 |
|---|---|---|---|---|---|
| 1 | **0.99** | 1.00 | 1.00 | 1.00 | 1.00 ← invalid |
| 2 | **0.33** | 0.37 | 0.41 | 0.44 | 0.53 ← invalid |
| 3 | **0.10** | 0.12 | 0.16 | 0.22 | 0.32 ← invalid |
| 5 | 0.02 | 0.05 | 0.09 | 0.14 | 0.24 |
| 12 | 0.03 | 0.07 | 0.19 | 0.29 | 0.52 |
| 30 | 0.04 | 0.12 | 0.32 | 0.57 | 0.88 |
| 50 | 0.05 | 0.14 | 0.53 | 0.79 | 0.97 |
| 80 | 0.05 | 0.23 | 0.71 | 0.93 | 1.00 |
| **120** | 0.04 | 0.31 | **0.89** | 0.99 | 1.00 |

⇒ **120 episodes per arm for 80 % power at ×2.29 with a valid test.**
The difference-in-differences (four arms — the estimator the within-drive control actually implies)
needs **200 per arm**.

### 1.3 The n = 1 case, which is the operator's actual budget

He stops the drive at the first symptom, so the realistic sample is **one episode per stratum**. Stated
without a test, because no interval estimator exists at n = 1:

- ln|gd| per-episode sd = **1.368** ⇒ the log ratio of two single episodes has sd = **1.935**.
- The target is ln(2.29) = 0.829 ⇒ **the effect is 0.43 σ of a single-episode contrast.**
- **P(the observed contrast even has the right SIGN) = 0.67.**
- The 95 % interval on a one-vs-one ratio spans **×44 in either direction.**

**That is the whole answer to item 1.** One episode per stratum cannot distinguish a build that halves
the ring from one that does nothing, or from one that doubles it.

### 1.4 In minutes

Measured episode rates, and the treated-stratum rate (episodes whose body sits ≥ 70 % at idx ≤ 22):

| arm | engaged s | n ep | ep / engaged h | **TREATED ep/h** | min for 1 treated ep |
|---|---|---|---|---|---|
| r39 (V282) | 880 | 79 | 323 | 102 | 0.6 |
| V282pool | 1957 | 130 | 239 | 63 | 1.0 |
| r5e_v288 (V288) | 642 | 46 | 258 | 56 | 1.1 |
| r62_v289 | 619 | 12 | 70 | 52 | 1.1 |
| r63_v289 | 588 | 15 | 92 | 18 | 3.3 |
| **V289pool** | 1207 | 27 | 81 | **36** | **1.7** |

At the V289 pooled treated rate, **120 treated episodes = 200 minutes of engaged driving**, and the
untreated arm accrues alongside it, so **one drive of ≳ 3.3 h engaged** — against a stated budget of
**15–30 s of symptomatic driving**. **The shortfall is roughly four orders of magnitude in exposure.**

> ⚠ Even on the *loudest* base build (r39, 102 treated ep/h) 120 episodes is 71 min engaged. There is no
> arm in the corpus where this read is affordable.

---

## 2. THE STRATIFICATION RISK (item 2)

### 2.1 How the split actually lands

Episodes classified from the **body** (median idx and the fraction of body frames per zone), not from
the onset frame:

| arm | n ep | TREATED (body ≥ 70 % at idx ≤ 22) | UNTREATED (≥ 70 % at idx ≥ 32) | MIXED |
|---|---|---|---|---|
| r39 (V282) | 79 | 25 (32 %) | 16 (20 %) | 38 (48 %) |
| V282pool | 130 | 34 (26 %) | 41 (32 %) | 55 (42 %) |
| r5e_v288 (V288) | 46 | 10 (22 %) | 15 (33 %) | 21 (46 %) |
| **r62_v289** | 12 | **9 (75 %)** | **3 (25 %)** | 0 |
| **r63_v289** | 15 | **3 (20 %)** | **9 (60 %)** | 3 (20 %) |
| V289pool | 27 | 12 (44 %) | 12 (44 %) | 3 (11 %) |

**The 31 %/67 % split the census flagged is confirmed and is worse than it looked**: on r62 three
quarters of episodes are treated and only 3 are controls; on r63 it is the reverse. **A one-drive read
would be a 9-vs-3 or a 3-vs-9 comparison, and which one you get is a coin flip.** [EVIDENCE:
`powerS_row_readability.py` §2, from the census episodes and the wire-reconstructed idx.]

**Between 42 % and 48 % of base-build episodes are MIXED** — the body straddles the knot — so on the
yardsticks nearly half the data is unusable for a stratum contrast at all.

### 2.2 By seconds, which is the dose that matters

| arm | episode s | idx ≤ 22 | 22–32 | idx ≥ 32 | mean delivered Kd under row S |
|---|---|---|---|---|---|
| V282pool | 293.0 | 93.1 (32 %) | 33.8 (12 %) | 166.1 (57 %) | 115.9 (×0.906) |
| r5e_v288 | 97.5 | 32.9 (34 %) | 10.2 (11 %) | 54.3 (56 %) | 115.5 (×0.902) |
| r62_v289 | 12.5 | 8.2 (66 %) | 0.4 (3 %) | 3.9 (31 %) | 106.5 (×0.832) |
| r63_v289 | 13.0 | 3.2 (24 %) | 1.1 (9 %) | 8.7 (67 %) | 118.9 (×0.929) |
| V289pool | 25.5 | 11.4 (45 %) | 1.5 (6 %) | 12.6 (49 %) | **112.8 (×0.882)** |

⚠ **The delivered dose is not the nominal dose.** Row S nominally cuts Kd to 0.75×, but averaged over
grinding-episode seconds the *delivered* Kd is **×0.88** on the V289 routes and **×0.91** on the base
builds — because more than half of grinding time is already above the knot. **A design memo that scores
row S at Kd 96 is scoring an operating point the car spends 24–45 % of its grinding time in.**

### 2.3 Minimum episodes for a usable read, and P(getting them)

From §1.2 the minimum for a *valid* test is **n ≥ 5 per stratum** (FPR ≤ 0.10) and for a *powered* one
**n ≥ 120**. Poisson at the measured per-arm rates, requiring k in **both** strata of the same drive:

| V289pool, drive length | k ≥ 1 | k ≥ 2 | k ≥ 3 | k ≥ 5 | k ≥ 8 |
|---|---|---|---|---|---|
| 5 min engaged | 0.90 | 0.64 | 0.33 | 0.03 | 0.00 |
| 10 min | 0.99 | 0.96 | 0.88 | 0.50 | 0.06 |
| 15 min | 1.00 | 1.00 | 0.99 | 0.89 | 0.45 |
| 30 min | 1.00 | 1.00 | 1.00 | 1.00 | 0.99 |

⇒ **Does the comparison collapse when the treated stratum is thin? Yes, but that is the lesser
problem.** Populating both strata at k ≥ 5 takes ~15 min engaged and is ~89 % likely; **populating them
at the k = 120 the estimator needs is not achievable in any single drive.** The stratification risk is
real and asymmetric across drives, but **it is not the binding constraint — the estimator variance is.**

---

## 3. CONFOUNDS (item 3) — THE CONFOUND FLOOR

**Method**: on the routes where **Kd is flat 128 at every index**, split the census episodes by the same
body-stratum rule and compare. Any difference found is confound by construction. Bootstrap by episode,
4000 draws.

**r39 (V282), n = 25 low vs 16 high**

| metric | p50 idx ≤ 22 | p50 idx ≥ 32 | ratio | 95 % CI | |
|---|---|---|---|---|---|
| f0 Hz | 19.910 | 20.124 | 0.989 | [0.976, 1.002] | not resolved |
| env peak | 97.5 | 187.2 | **0.521** | [0.404, 0.687] | **CONFOUND** |
| dur s | 1.000 | 2.245 | **0.445** | [0.213, 0.745] | **CONFOUND** |
| \|gd\| /s | 2.456 | 2.922 | 0.841 | [0.197, 2.631] | not resolved |
| ζ | 0.020 | 0.024 | 0.825 | [0.244, 2.684] | not resolved |

**V282pool, n = 34 vs 41** — env 0.582 [0.458, 0.739] **CONFOUND**; dur 0.500 [0.299, 0.745]
**CONFOUND**; f0 0.989 [0.971, 1.001]; |gd| 0.753 [0.288, 1.906]; ζ 0.640 [0.316, 2.019].

**r5e_v288 (V288), n = 10 vs 15** — dur 0.201 [0.142, 0.980] **CONFOUND**; env 0.542 [0.443, 1.685];
f0 0.952 [0.775, 1.055]; |gd| 1.309 [0.139, 4.666]; ζ 1.290 [0.158, 5.405].

**BASE POOL (V282pool + V288, n = 44 vs 56) — THE FLOOR**

| metric | p50 idx ≤ 22 | p50 idx ≥ 32 | ratio | 95 % CI | verdict |
|---|---|---|---|---|---|
| f0 Hz | 19.892 | 20.124 | **0.988** | [0.966, 0.998] | **CONFOUND** (small) |
| env peak | 97.5 | 166.5 | **0.585** | [0.507, 0.713] | **CONFOUND** |
| dur s | 1.000 | 2.000 | **0.500** | [0.204, 0.664] | **CONFOUND** |
| \|gd\| /s | 2.392 | 2.544 | 0.940 | **[0.340, 2.006]** | not resolved |
| ζ | 0.020 | 0.021 | 0.968 | [0.336, 2.328] | not resolved |

**Reading it honestly, because two different things are true at once:**

1. **The decay-rate confound's POINT ESTIMATE is benign — 0.940, essentially 1.** On the base builds, low-
   and high-demand rings decay at the same rate. That is the one piece of good news for the design: the
   within-drive control is not *systematically* biased on the metric row S targets.
2. **But it cannot be pinned.** Even with 98 base episodes the CI spans ×5.9. Correcting the ×2.29 target
   by that interval gives **×0.78 to ×4.60**. **The correction factor's own uncertainty is 2.6× wider
   than the effect.** So the control is unbiased but useless at the precision required.
3. **The amplitude and duration channels are catastrophically confounded, in the flattering direction.**
   Low-demand grinding episodes are 41 % quieter and half as long on builds that treat them identically.
   **Any V290 report that says "the low-demand grinding was quieter and shorter, so row S worked" is
   reporting the confound.** This is the single most likely way row S produces a false positive.
4. **The frequency channel is nearly clean** (−1.2 %, ≈0.24 Hz) and is the only within-drive channel
   whose confound is small relative to what a real loop-shape change would do.

⭐ **Answer to the brief's framing**: the untreated stratum is a *fair* control in expectation for the
decay rate, and an *unfair* one for loudness and length. Either way the within-drive control is not
worthless — it is **unbiased and 2.6× too imprecise**. That distinction matters: the fix is not a better
control, it is a better estimator.

### 3.1 The parametric hazard, quantified

Reconcile flagged that a gain switching inside the ring cycle is a parametric modulation. It is not
hypothetical:

| arm | n ep | knot-32 crossings/s p50 | p90 | max | share of episodes with ≥ 1 crossing |
|---|---|---|---|---|---|
| V282pool | 130 | 1.1 | 4.3 | 10.0 | **0.68** |
| r5e_v288 | 46 | 2.0 | 6.5 | 16.0 | **0.70** |
| V289pool | 27 | 0.7 | 6.0 | 8.0 | **0.52** |

**Between half and 70 % of grinding episodes cross the knot at idx 32 during the episode body**, at a
median 0.7–2.0 crossings/s and up to 16/s. [EVIDENCE: `powerS_row_readability.py` §4, from the
wire-reconstructed idx over census episode bodies.] The mitigation reconcile named (widen the 22 → 32
ramp) is therefore **not optional** — and note that widening it also widens the MIXED class, which
further thins both strata.

---

## 4. THE VERDICT, AND THE FIX (item 4)

### 4.1 Verdict

> **NOT READABLE WITHOUT A CAVE — on the decay-rate claim, at any drive length the operator would
> accept. And the specific cheap cave bit proposed (which Kd knot interval is live) DOES NOT FIX IT.**

Three separate failures, only one of which a knot-interval bit touches:

| failure | severity | does a Kd-interval bit fix it? |
|---|---|---|
| Estimator variance: sd(ln\|gd\|) = 1.37 ⇒ 120 ep/arm | **fatal** | **no** |
| Stratum thinness on a given drive (9-vs-3 or 3-vs-9) | serious | **no** |
| Stratum labelling from the wire | **already solved** | yes, but worth ~0.3 % |

**The stratification is not a reconstruction problem.** `scalecheck_x4_r62_r63.py` re-derived idx
bit-exactly from the image and compared it to `GI.demand_live` frame by frame: **r62_v289 0.9985,
r63_v289 0.9965, r5e_v288 0.9920 exact-integer agreement, max |diff| = 1 LSB.** A comparator bit would
replace a 99.7 %-accurate reconstruction with a 100 % measurement. **It buys 0.3 % of frames and none
of the variance.** [EVIDENCE: `_scratch/scalecheck_x4_r62_r63.txt`.]

### 4.2 The minimum cave that would actually change the answer

**A MAGNITUDE comparator on the D term, reported as one bit on 0x14A byte 4, adjudicated per episode
against the mirror.** `rlog-tools/studies/grind/powerS_sizing_dbit.py` sizes it.

🛑 **First, the trap.** D = clip(floor(dE·Kd / 8), ±10240). Below the clamp, **D is exactly proportional
to Kd**, so **sign(D) is invariant under row S**. A *sign* comparator — the class the r24 and notch-sign
taps already ship, and the obvious thing to reach for — is **structurally blind to this edit** and would
produce exactly the uninterpretable null the doctrine forbids. [EVIDENCE: the decompiled arithmetic.]

Sizing, base |D| taken from the 1 kHz mirror over the measured V289 grinding episodes
(|D| p25/p50/p75/p90 = 448/1248/2480/4368 on r62, 464/1312/2928/5650 on r63; D-clamp bind duty 0.025/0.028):

| threshold T | duty at Kd 128 | duty at Kd 96 | shift | unpaired 1-ep z | **paired 1-ep z** | episodes for z = 2 (paired) |
|---|---|---|---|---|---|---|
| 896 (base p40) | 0.604 | 0.523 | −0.081 | 0.39 | 0.91 | 5 |
| 1280 (base p50) | 0.503 | 0.403 | −0.100 | 0.49 | 0.91 | 5 |
| **1712 (base p60)** | 0.403 | 0.300 | −0.103 | 0.54 | **1.89** | **2** |
| 2672 (base p75) | 0.251 | 0.171 | −0.081 | 0.51 | 1.48 | 2 |

- **Unpaired** (compare the flown duty to a pooled expectation) gives z ≈ 0.5/episode — no better than
  the decay estimator, because between-episode operating-point spread dominates.
- **Paired** (run the mirror twice on the *same* wire data for that episode, Kd 128 and Kd 96, and ask
  which prediction the measured duty matches) gives **z ≈ 1.9/episode at T = 1712 ⇒ 2 episodes for
  z = 2.** [BELIEF for the numbers — they are mirror-grade and ignore mirror model error, so the true z
  is lower; EVIDENCE for the mechanism.]

⭐ **But be exact about what that buys.** The paired duty bit answers **"is the edit live, and at what
dose"** from 2–5 episodes, i.e. from one short drive. **It does NOT measure the 582 → 254 ms claim.** No
instrument in this kit's reach measures that from one drive, because the wire almost never contains a
free ring (§7d: 7 quiet stretches in all of V282pool). **The honest design is to demote the ring-length
claim from a measurement to a model prediction, and ship the bit that verifies the model's input.**

### 4.3 What I would put to the orchestrator

1. **Do not ship row S with "the within-drive control is the instrument".** It is unbiased on decay rate
   and 2.6× too imprecise, and it is a 2× confound on loudness and duration in the flattering direction.
2. **If row S ships, it ships with the |D| ≥ T magnitude bit** (T ≈ 1712 raw, base p60 — sized so both
   the base and the treated duty sit off the 0/1 rails), and the read is the **paired mirror
   adjudication**, pre-registered as a liveness/dose check.
3. **Widen the 22 → 32 knot ramp** before flying, per §3.1 — 52–70 % of episodes cross it.
4. **The alternative that avoids all of this** is to prefer a candidate whose effect is *not* confined to
   a stratum, so the whole drive is the treated arm and the comparison is against the 176-episode base
   corpus rather than against 3–9 same-drive controls. The decision table's cave candidate (notch on the
   feedback operand + fb pole 40 Hz) has that property. **That is a design trade for the orchestrator,
   not a finding of mine.**

---

## 5. THE SENTENCE A NULL LICENSES, AND THE PRE-REGISTERED SIGNATURES

### 5.1 What a null licenses — row S, as specified (no cave)

> **"On one drive of *N* minutes engaged, *k_T* treated and *k_U* untreated grinding episodes were
> observed. The measured decay-rate ratio between strata was *r* [CI]. Because the estimator's
> per-episode dispersion is sd(ln|gd|) = 1.37 and the base-build confound on the same contrast is
> 0.940 [0.340, 2.006], this drive was powered to detect a ×2.29 change only if k_T ≥ 120; it was not.
> **Row S's effect on ring length is therefore UNMEASURED, not absent.** The drive licenses no statement
> about whether the Kd schedule shortened the ring, and it licenses no statement about grinding
> loudness or duration by stratum, because those channels carry a measured ×0.59 and ×0.50 confound in
> the direction that mimics a cure. What the drive DOES license: the operator's symptom report, and the
> authority checks (7 Hz gate, capped-step peak rate), which are protected by construction above idx 32
> and are not stratum-confounded."**

### 5.2 What a null licenses — row S + the |D| ≥ 1712 magnitude bit

> **"The bit's duty over *k* grinding episodes was *d*, against paired mirror predictions of *d128* and
> *d96* for those same episodes. [If d matches d96] the Kd schedule is LIVE and delivering ×0.75 in the
> treated stratum; the edit acted and the ring did not shorten enough to be felt ⇒ the DOSE is the
> lever, not the mechanism. [If d matches d128] the schedule did NOT act in the episodes that ground —
> either the demand index sat above the knot throughout (check the reconstructed idx) or the edit is not
> live; **in that case the build is uninterpretable on its own claim and must be re-cut, not re-flown.**"**

### 5.3 Pre-registered FAIL / REVERT signatures for row S

**FAIL (the build did not do its job):**
- **F1** — the operator reports the grinding unchanged **and** the |D| bit's duty matches the *base*
  prediction ⇒ the edit did not reach the episodes that ground. **Re-cut, do not re-fly.**
- **F2** — treated-stratum episode rate, envelope and duration all within the base-pool confound band
  (env ×0.51–0.71, dur ×0.20–0.66, |gd| ×0.34–2.01) ⇒ no signal distinguishable from the confound.
- **F3** — the delivered-dose check fails: mean delivered Kd over grinding-episode seconds ≥ 120
  (i.e. > ×0.94 of base) ⇒ the schedule is nominally right and operationally inert, as §2.2 warns.

**REVERT (the build made something worse):**
- **R1** — a new or louder line **anywhere in 10–30 Hz on straight-road engaged frames**
  (|angle| < 5°), by the V288/V289 segment-PSD normalisation. This is the parametric-modulation
  signature: 52–70 % of episodes cross the knot, so a knot-rate sideband would appear at
  f0 ± (crossing rate), i.e. **±0.7–6 Hz around the 15–17 Hz line**. ⭐ Score the *sidebands*
  explicitly — a pure line-height test will miss them.
- **R2** — the 7 Hz strong-turn gate rises above **1.01**, or capped-step peak rate falls below
  **0.95**. Both are protected by construction above idx 32, so a breach means the protection
  assumption is wrong, not that the dose was too big.
- **R3** — episode duration or envelope rises in the **untreated** stratum, where nothing changed. That
  can only be a whole-loop effect and falsifies the "byte-identical above idx 32" reasoning.
- **R4** — the operator reports any new symptom at low demand (creep, parking, lane-keep on straight
  road) that he did not have on V289.

**A NULL FROM A DRIVE WITH k_T < 5 TREATED EPISODES IS NOT A NULL** — it is a drive that did not sample
the treatment. Record it as exposure, not as a result.

---

## 6. RESIDUAL UNCERTAINTY — what I did not establish

- **BELIEF**: the |D| duty numbers and the paired z are mirror-grade (`GI.simulate`), not measured on a
  flown build. Mirror model error is not in the SE, so the paired z of 1.89 is an **upper bound**.
- **BELIEF**: the cave cost of a magnitude comparator. I did not price the cave; a tracer must.
  §5 of `powerS_sizing_dbit.py` names the obvious economy (reuse `0xC61B6` shifted rather than a new
  constant) but that is untraced.
- **NOT ESTABLISHED**: whether the closed-loop response to Kd 128 → 96 preserves the open-loop |D|
  scaling in the presence of the D clamp (bind duty 0.025–0.028 in episodes). The sizing assumes it
  below the clamp, which is exact for 97 % of frames.
- **NOT ESTABLISHED**: whether `growth_fit`'s dispersion could be reduced by a better estimator (e.g.
  fitting only the post-peak quiet sub-stretch). §7d suggests not — the quiet stretches are too rare —
  but I did not attempt an alternative estimator.
- The MIXED class (42–48 % of base episodes) was excluded from every stratum contrast. A dose-response
  regression on delivered Kd would use them and would be somewhat better powered; I did not run it, and
  it would not close a 120-episode gap.
