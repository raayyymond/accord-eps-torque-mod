# HANDOFF 2026-08-30 — the gain ladder, and what the measurement session found

## The deliverable

The operator's brief, mid-session: *"the safest, highest probability of working firmware with 6x torque
(or higher …) up to 16x torque with no grinding, vibration, or oscillation, best firmware for
autonomous driving."*

**Answer: a three-rung ladder, all on identical grinding work, four bytes per rung. And 16× does not
exist.**

```
  V241   6x   image 2ef7eb8eb2417905…  rwd 57d240d77f568aac…   FLY FIRST -- the car's gain
  V242   8x   image 424249b0c7d89fad…  rwd a94962b4240613c8…   +4 bytes on V241
  V243  10x   image 5fb9ad74f104de46…  rwd 43a32ac352508557…   the ceiling
```

All three re-verified from disk at close-out; exactly one flashable `.rwd` each, 986,042 bytes.
Card: `docs/scoring/DRIVE-CARD-GAIN-LADDER.md`.

## Why the ceiling is real

The forward clamps must stay below the soft-EME floor `0xC674E`, and track the gain as
`gain × 512 // 891`: 6× → 3072, 8× → 4096, 10× → 5120 (= the floor; V219/V225 used 4608),
12× → 6144 FAILS, 16× → 8192 FAILS.

⚠ **`0xC674E` is not Honda's value on the car.** Honda ships **1024**; the car carries **5120**, raised
5× by an earlier build. Reaching 16× would mean raising it again to above 8192. **Left untouched in all
three builds and asserted so.** That is a decision for the operator, not for the kit.

## The risk, and why it is not V101 again

8× flew as V101 and was rejected — *"grinding/vibration at all speeds, only while LKAS commands"*. The
operator reverted to 6× himself. Measured: peak **moved 20.3 → 23.0 Hz**, de-confounded gain
**2.7–3.9× at 22–26 Hz**.

That band is what this lineage's notch attacks, and the notch is aimed by the **comma IMU** —
independent of the EPS. V101 raised the gain with no grinding treatment at all. **Safety is separate
from comfort here: V101 flew fault-free, EME audit passed. 10× has never flown at all.**

## What the measurement session established

**Positive.**
- The ratchet is **real chassis motion**, confirmed off-EPS for the first time (9/10 speed-matched
  routes, p 0.02, median 1.34 over a road control).
- The **grinding metric is valid** — V88, the one measured grinding fix, ranks near-best for grinding
  and near-worst for ratchet on the IMU. Prediction written before the answer was read.
- **22–30 Hz is the largest engagement-created motion band** (2.481, peak 25–26 Hz), and the alias-free
  audio confirms it is real, not folded from 71–79 Hz.
- **V241's notch beats V235's by 28%** on that objective, survives leave-one-route-out on all ten
  routes and five of six weightings, and cuts *less* of the damping band than V235 did.

**Negative, and each one closed an avenue.**
- Every cal in the assist-map path is measured: only `gp-0x69a0` moves the ratchet band without taking
  assist away, and it is broadband. Four cals are completely inert.
- `0xC6384` is **inert** — it only reaches above 2844 torque counts, 1.65% of frames. V236/V239 withdrawn.
- The **loop-delay hypothesis is refuted** by its own control.
- **No build has ever moved the ratchet**, confirmed on an instrument no build could game.
- **Torque and chassis name different bands** (ρ +0.040). The notch acts on torque, where its band is
  nearly the weakest — that is the honest ceiling on V241/V242's grinding claim.

**The one live thread.** The rule forbidding a 6–15 Hz notch — the band torque says matters — may rest
on a **rectified channel**: ra4/ra5/ra6 carry `mag427` without `sgn427`, and the field is a magnitude,
not two's complement. **Neither verifiable nor refutable from existing data.** Settling it needs a build
that puts the lane's sign bit on 427, plus a drive. If the rule falls, a 6–10 Hz notch is the strongest
lever the kit has had.

## Infrastructure fixed along the way

- **The whole `extract/` toolchain was dead** since the 2026-08-26 reorg (`rlog_parse` moved to
  `rlog-tools/lib/`). 51 files fixed. Invisible because the caches were already on disk.
- **`extract_imu_cache.py` had a hardcoded 6-route table** that rejected every route holding the
  speed-matched exposure. Now globs. **225 IMU caches, up from 109.**
- STATE.md archived 176 → 156 KB against the 256 KB cap.

## Corrections made to my own work this session

V237 built backwards and withdrawn · V240 promoted then found to cut a measured damper · "largest
measured ratchet lever" retracted as broadband · an arbitrary 0.97 threshold that rejected stock itself,
replaced by the car's own value · a claimed IMU null reversed when tested rather than eyeballed.

## Next

1. **A drive.** Nothing in this lineage has flown. **V241 first** — it tests the grinding work at the
   gain the car already runs, so a result is interpretable; V242 is then a four-byte gain step with
   that question answered. (An earlier pass in this session recommended V242 first; that answered
   "more torque" rather than the brief's "safest, highest probability", and skipped the operator's
   own "fix at 6x first" ruling.)
2. **The sign probe** — put `gp-0x6b86`'s sign bit on 427 and settle the 6–15 Hz rule.
3. If the rule falls, build the 6–10 Hz notch: it is the only untried lever with a measured case.

---

## 🛑 `gp-0x6b86` carries the most ratchet-band energy of any lane 427 ever flew — and that is NOT "the ratchet's lane"

**Read the correction at the end of this section before using any of it.** I headlined this as *"the
ratchet's lane is identified"* and that was an overclaim: the discriminator was already in `STATE.md`
and it goes against me. The **measurement** below is clean and useful; the **causal reading** is
withdrawn. CAN 427 carried a **different
lane per build**, which makes the corpus a natural experiment. Reading the clamped channel at **2f₀**
(where a rectified 7.8 Hz oscillation lands):

```
  lane         routes   median   per route
  gp-0x6b86         3    3.288   ra4 3.29, ra5 5.36, ra6 2.94
  gp-0x6c2c         1    1.944   r1e 1.94
  gp-0x6b94         2    1.931   r85 2.11, r95 1.75
  gp-0x6b4c         2    1.849   r96 1.82, r9e 1.88
```

**All three `gp-0x6b86` routes sit above all five routes of the other three lanes — complete separation
over 4 lanes and 8 routes.** The split is **bimodal**: the four losing lanes cluster tightly at
**1.75–2.11** (baseline — essentially no local 2f₀ line at all) while `gp-0x6b86` stands apart at
**2.94–5.36**.

**And this survived my own blocker being wrong.** The first pass asserted *"rlogs stop at route a6, so
`gp-0x6c2c` / `gp-0x6abc` / `gp-0x6b4e` cannot be ranked at all."* False: **`r1e` (V107) carries
`mag427` on `gp-0x6c2c` with 989 s engaged — the best-powered route in the entire corpus.** Adding it
did not overturn the result. `gp-0x6abc` (r21/r22/r24) genuinely has no decoded `mag427` column, and
`gp-0x6b4e` (V212–V220) has no cache; those two remain unrankable.

### The first version of this ranking was wrong, and its own control killed it

Scored by the **engaged/manual ratio**, `gp-0x6b4c` came top at **300–377×** — which read as a decisive
answer. The denominator check:

```
  route  lane          eng p50   man p50   man nonzero
  r96    gp-0x6b4c        7.0      0.0      0.354 %
  r9e    gp-0x6b4c        8.0      0.0      0.273 %
  r85    gp-0x6b94        8.0     21.0     98.443 %
```

`gp-0x6b4c` is nonzero on **three tenths of one percent** of manual frames — the lane is simply *dead
when not engaged*, so the ratio was a division by noise measuring **liveness**, not ratchet energy.
(Consistent with the record: an 11-slot *assist sum* has nothing to sum when LKAS is not driving.)
Rescoring as a **local excess within the engaged arm** removes the confound, and `gp-0x6b4c` ranks last.
**Always inspect the denominator behind an implausibly large ratio.**

### 🛑 And the lane's identity had to be corrected — the correction changes the target

First written up as *"the base assist-map lane"*. **Wrong.** The facade's own chain:

```
  ... -> biquad H(z) -> float clamp ±12.0 -> ×1024
      -> + gp-0x6b7e   (UNFILTERED pedestal, NOT scaled by c4)
      -> clamp ±0x3000 -> gp-0x6b86 -> FUN_0003aa2c aggregator
```

`gp-0x6b86` is the **output of the biquad lane** — the lane the entire V172→V241 notch arc has been
shaping. **The notch is in the right lane**; the ratchet is not somewhere the kit's main instrument
cannot reach.

### Three levers in that lane, all checked this tick, all negative

| candidate | test | result |
|---|---|---|
| boost-curve **kink** (seg 0 is 21× steeper than seg 1) | what is the X axis? | **wrong axis** — `0xCA154` is keyed on *speed*, not torque; already refuted on record, and V61 touched it |
| **pedestal** `gp-0x6b7e` bypassing the notch | EMA gain at 7.8 Hz | **weak** — at K=20 it passes **0.196** vs ~0.93 through the biquad path; filtered path dominates ~5×. V238's costing stands |
| the lane's **±0x3000 clamp** (the record's *"nonlinear remains open"*) | does it bind? | **never** — 0.0000 % at ceiling on all three routes (max 850/835/723 of 1023) |

Notching 7.79 Hz directly stays closed for the reason the damping-band floor exists: **there is a real
6–9 Hz damper there**, and cutting it is self-defeating.

**Limits on the ranking, all real:** build and 427-source are perfectly confounded — each lane is seen
only on the builds that probed it, and those builds differ in other ways. 3 vs 1 vs 2 vs 2 routes.
`gp-0x6abc` and `gp-0x6b4e` remain unrankable for want of a decoded channel.

Readers: `rlog-tools/score/rank_lanes_liveness_free.py` (the sound one) and
`rank_lanes_by_ratchet_energy.py` (the confounded one, kept with its confound documented).

### 🛑 The correction: this is a good INSTRUMENT and a bad TARGET

`gp-0x6b86`'s **measured phase at 6–9 Hz is cos −0.918 / −0.989 / −0.629, 3/3 routes** — the lane is
**damping** in the ratchet band, not pumping. A *source* shows cos > 0. So the lane carrying the most
2f₀ energy is the one **responding hardest** to the ratchet, not the one causing it — which is exactly
why cutting it condemned **V238 and V240**. The ranking is therefore *consistent with*, not a correction
to, the standing result that **every tapped lane damps at the ratchet, so no linear lane is the source.**

A third correction, made mid-tick and worth recording because I got it wrong first: the pedestal is
**not** a parallel path carrying its own copy of the signal. It is the term that **undoes the slew
limiter's cut** — `out(f) = table2 + H_k(f)·(table1 − table2)` — so the 0.197 at 7.79 Hz is *the
fraction of the cut undone*, not a path ratio. Its cell is `0xC6906`, i.e. **V238**, already built and
already costed at ~3.8 % of the lane. Right conclusion, wrong reasoning.

**The bind is unchanged, and it is the arc's real wall:** every device in this lane acts at 6–9 Hz by
*cutting* it, and at 6–9 Hz this lane is a damper we need. **The one band worth filtering is the one
band that must not be filtered.** Nothing found this tick moves that.

**The flight recommendation is unchanged: V241 first.**


---

## 🛑 THE LKAS GAIN *IS* THE RATCHET'S ANTI-DAMPING — and it prices this very ladder

**The most useful thing found in the whole arc, and it arrived after the ladder above was written.**

Regressing the coherence-gated 6–9 Hz `Re(Z)` on `0xC6CD0` across every flown build — `tq` against
`cs_rate`, **both non-rectified**, so unlike every 427-derived phase this is actually measured:

```
  4x  (7 builds)   Re(Z)  -46.6 .. -66.8         less negative = less ratchet
  6x  (9 builds)   Re(Z)  -62.3 .. -74.9
  8x  (1 build)    Re(Z)  -84.1
  slope -0.0074/count · R2 0.726 · Spearman rho -0.819 · p 0.0001 · n = 17
```

Gain rises monotonically with build era, so the trend **alone** proves nothing. **What carries it is a
reversal** — three consecutive builds where the gain goes up, then back down:

```
  V100  4x  ->  -66.83
  V101  8x  ->  -84.06     gain UP,   anti-damping DEEPENS  (-17.23)
  V102  6x  ->  -74.91     gain DOWN, anti-damping RECOVERS (+9.15)
```

**Build era is monotone and cannot produce a reversal.** ≈ **−4.4 of `Re(Z)` per 1× of gain.**

### Why this closes the arc's central puzzle

The ratchet was never a lever the kit failed to find. **It tracks the gain the kit itself kept
raising.** That is why every cal, filter, damper, cave and notch measured null on it — and why **no
build from V90 to V122 moved the anti-damping** (median −64.8, sd 9.1, nothing off the pack). None of
them changed the thing that sets it.

### How it was reached — three eliminations from bytes first

Engagement re-indexes the mode table 24 → 26. Of everything that re-index touches:

| lane | mode 24 vs 26 |
|---|---|
| five base-assist damper records (FactorB/C/D/E + ceiling) | **byte-identical** |
| all three boost tables | **byte-identical** |
| **friction** | **3× different** — `Y −9830/−5734/−1966` → `−29490/−17202/−16000` |

Friction was the only candidate left, and its dose spans **1.0×–3.0× across 17 flown builds with no
relation to `Re(Z)`** (rho −0.263, p 0.31). ⇒ no re-indexed calibration explains the anti-damping,
which leaves the applied LKAS torque — and the gain is what sets that.

### Two controls it survives, and one escape that is closed

1. **The clamp is not an independent lever.** It tracks the gain as `gain*512//891`, so `clamp/gain` is
   identically 512 and the command at which it binds is 512 counts on every build. Collinear **by
   construction** — a clamp-only build would be **inert**. No authority-without-ratchet hides there.
2. **Saturation duty controls against "command effort".** If effort drove it, the 4× builds would be
   worst — they saturate **44–45 %** of frames against 6×'s **13 %**. They are the **least**
   anti-damped. Within the 6× builds duty does not predict `Re(Z)` either.

### 🛑 The mechanism is NOT established, and that is recorded deliberately

The LKAS lane is a **~1–5 Hz low-pass**, so the command cannot itself carry 7.8 Hz; and uniform scaling
of both torque and motion would leave the **ratio** `Re(tq/rate)` unchanged. So this is a robust
**empirical** relation with an **open** mechanism. Three mechanisms were written into `STATE.md` and
retracted in this session — see `feedback-compute-the-control-before-writing-the-mechanism`.

### What it means for the ladder

```
  V241   6x   the car's present gain    ->  ratchet as today   <-- FLY THIS
  V242   8x   +2x                       ->  measurably WORSE
  V243  10x   +4x                       ->  worse still
```

**V242 and V243 are not withdrawn** — the operator asked for the ladder, it is built and verified, and
the authority is real. What changed is that **the trade is no longer unknown**. V241 stays the
recommendation, now for a *measured* reason rather than a cautious one.

⚠ One route per build, 75–170 windows each, adjacent builds differ in more than the gain cell. **A
priced trade-off, not a controlled experiment.**

Readers: `gain_vs_antidamping.py` · `friction_dose_vs_antidamping.py` · `gain_vs_clamp_collinearity.py`
· `antidamping_by_build.py` · `rez_dilution_control.py` · `rez_nonrectified_replication.py`.
