# Working backwards from "no overshoot" — the Kp-only cut, and why the low-overshoot ZN family is structurally forbidden

> 🛑 **OUTCOME OF THIS FILE, ADDED AT CLOSE (2026-09-04): NO FIRMWARE THIS SESSION.**
> The r24 arm magnitude was measured mid-session (`grind39`, r39) and landed in the branch where the
> **Kd axis inverts** — see **PART IV**. Kd 160/192 give `|L(7.3)| = 0.990–1.044` at the measured arm,
> i.e. dead or marginal. The Kp alternative's r39 deadband cost is ~2× what Part I priced. **Read
> PART IV first, then Part III; Part I's §5 recommendation and Part II's §II.7 recommendation are BOTH
> withdrawn.** Companion note: `docs/research/LOOP-MODEL-CONVENTION-DEFECT-2026-09-04.md`.


Subagent `znback`, 2026-09-04, reporting to `team-lead`/`main`. **ANALYSIS ONLY — nothing was built,
no build script was touched, nothing was sent on any bus.**

**Code:** `analysis-2020accord/studies/pidframe/zn_backwards_no_overshoot.py` (+ `zn_backwards_supp.py`)
and `rlog-tools/studies/osc-highangle/stall_kp_counterfactual.py`. Stdout mirrors:
`_znback_out.txt`, `_znback_supp_out.txt`, `STALL-KP-COUNTERFACTUAL.txt`.

**Image [EVIDENCE]:** V282 `_v282_…TORQUE.TAP_plain_image.bin`, sha256 `0ea98d06b292ca1a…`, hashed by
this script. The filter/clamp/gain cals are byte-read and **asserted equal** to the ones
`studies/pidframe/pid_frame_sizing.py` reads from the V283 image (lag 992/507, fb 923/1560, fwd 5346,
D clamp 10240) — the only difference between the two images on this path is `0xC63E6` (Ki), which is
**0** in V282 and in every candidate below. The controller/filter transfer functions are **imported
from `pid_frame_sizing.py`, not re-implemented.**

**Gate 1, run before anything new was computed:** the script reproduces every published row of
`ZN-ACCEL-FRAME-V285-ADDENDUM` §A5 — ring ratios 1.000 / 0.932 / 0.866 / 1.035, `|L(7.3)|` 0.976 /
0.909 / 0.845 / 1.010, GM 1.77× / 1.48× / 1.27× / 1.96×, `Ku` 227 at Kp 248 and 270 at Kp 0, ZN-PI
(new) 148/122 → ring 0.936 / GM 2.01×. The lower root computes to **116.7** against the published 118
(a 1 % offset from the arms being published to 2 d.p., the same offset `zn285` reported). ⇒ the model
under everything below is the addendum's model, not a new one.

---

## 0. HEADLINE — four answers in one screen

1. ⭐ **Q1: YOUR PREMISE IS CORRECT, and more strongly than you framed it.** `Kp 148 / Kd 128 / Ki 0`
   beats today on both gates (**ring 0.976 → 0.900**, **GM 1.77× → 1.93×**) and beats ZN-PI 148/122 on
   the ring (0.900 vs 0.914). Decomposed: the **Kp cut alone is worth −0.076** on `|L(7.3)|`; the
   **Kd cut alone is worth +0.013 — it HURTS the ring.** ZN-PI's Kd 122 is a net drag on the gate it
   was chosen for. §1
2. 🛑 **AND THE SECOND HOLD-BACK REASON DISSOLVES TOO — "Kd 122 sits 3 % above the ring root of 118"
   IS AN APPLES-TO-ORANGES COMPARISON.** The root is a function of **Kp**: it is 116.7 at Kp 248 but
   **84.9 at Kp 148**. ZN-PI's Kd 122 sits **1.44×** above *its own* root, not 1.03×; the Kp-only
   candidate's Kd 128 sits **1.51×** above it, against today's **1.10×**. **A Kp cut MOVES AWAY from
   the ring root**, and it does so across every arm set and the whole `s` range (margin 1.41–1.93×).
   ⇒ **Neither of the two reasons for holding ZN-PI back survives; and the Kp-only variant is the
   better of the two anyway.** §1.3, §1.4
3. **Q2: the no-overshoot ZN family is STRUCTURALLY FORBIDDEN — confirmed, with a correction to the
   arithmetic.** Your 75 / 45 used `Ku = 227` (measured at Kp 248); ZN-proper hunts with integral
   action off, i.e. at Kp 0, where `Ku(Kd) = 270`, giving **Kd 90 ("some overshoot") and Kd 54 ("no
   overshoot")**. Both figures are below the root **at their own Kp** (94 and 77), and their computed
   `|L(7.3)|` is **1.010 and 1.055 — the ring re-arms**. **There IS a low-gain regime, but it lives in
   Kp, not in Kd**: the floor falls with Kp, so Kd ≈ 128 stays above it at every Kp. §2
4. **Q2b: tuning the inner loop toward ZN barely touches outer-loop path overshoot via LAG — your
   hypothesis is right in direction and negligible in size.** Kd 128 → 160 removes **1.4 ms** of
   inner-loop lag at 1 Hz (13.2 → 11.8 ms), ~0.7 % of openpilot's own 200 ms `SteerDelay`. What DOES
   reach the outer loop is **GAIN**: Kp 248 → 148 cuts the inner loop's closed-loop gain
   `|L/(1+L)|` by **0.76–0.82× at every outer-loop frequency**. ⇒ **Kp is the oversteer lever; Kd is
   not.** [EVIDENCE for both numbers; BELIEF for the causal claim.] §3
5. **Q3: the deadband cost is REAL, MODEST, and NOT disqualifying.** Re-running `v281r3_read_r35.moving_runs`
   — the exact function that produced the published "7 runs / 14.8 s" — with a Kp counterfactual:
   **Kp 148 takes r35 from 7 runs / 14.8 s to 9 runs / 18.9 s (+29 %).** For scale, Ki 50 took the same
   metric 7 → 1. My baseline column **reproduces 7 / 14.8 exactly.** §4
6. **Recommendation: `V287 = V282 + Kp slot 7 flat 248 → 148`. Ki stays 0, Kd stays 128, 5 bytes + CRC.**
   §5 carries the pre-registration, including what a FAIL looks like, written before any build exists.

---

## 1. Q1 — the Kp-only cut, and the whole trade curve

### 1.1 The sweep you asked for: Kp over {248, 200, 176, 148, 128, 100} at **fixed Kd 128, Ki 0**

| Kp | Kd | ring ratio @7.3 | `\|L(7.3)\|` | GM @ blind band | GM dB | `f(−180°)` | **DC tracking** |
|---|---|---|---|---|---|---|---|
| **248 (today)** | 128 | 1.000 | **0.976** | **1.77×** | 5.0 | 28.1 Hz | **53.5 %** |
| 200 | 128 | 0.960 | 0.936 | 1.85× | 5.4 | 28.8 Hz | 48.1 % |
| 176 | 128 | 0.941 | 0.919 | 1.89× | 5.5 | 29.2 Hz | 45.0 % |
| **148** | **128** | **0.922** | **0.900** | **1.93×** | **5.7** | 29.6 Hz | **40.7 %** |
| 128 | 128 | 0.910 | 0.888 | 1.96× | 5.8 | 29.9 Hz | 37.3 % |
| 100 | 128 | 0.895 | 0.873 | 2.00× | 6.0 | 30.3 Hz | 31.7 % |
| 64 | 128 | 0.879 | 0.858 | 2.04× | 6.2 | 30.8 Hz | 22.9 % |
| 0 | 128 | 0.861 | 0.840 | 2.11× | 6.5 | 31.7 Hz | **0.0 %** |

**Both gates improve monotonically as Kp falls, and the only cost is DC authority.** The DC column is
re-derived here from byte-read constants alone — `|T|/E = (Kp/256)·(254/256)·|H_lag(0)|·(5346/32768)`,
`L_dc = 247.1·g·(|T|/E)`, tracking `= L_dc/(1+L_dc)` at the mid-load `g = 0.030 deg/s per count` —
and it reproduces `zn285`'s integer mirror at Kp 248 to the digit (**53.5 %**).

### 1.2 Head to head — the row you asked for, added to §A5's table

| candidate | Kp | Kd | ring ratio | `\|L(7.3)\|` | GM | DC tracking | Kd vs root **@ own Kp** |
|---|---|---|---|---|---|---|---|
| V282/V283 as built | 248 | 128 | 1.000 | 0.976 | 1.77× | 53.5 % | **1.10×** |
| ⭐ **Q1: Kp 148, Kd 128** | **148** | **128** | **0.922** | **0.900** | **1.93×** | **40.7 %** | **1.51×** |
| ZN-PI (new) | 148 | 122 | 0.936 | 0.914 | **2.01×** | 40.7 % | 1.44× |
| F: Kd 160 | 248 | 160 | 0.932 | 0.909 | 1.48× | 53.5 % | 1.37× |
| Kp 148 + Kd 160 | 148 | 160 | **0.847** | **0.827** | 1.58× | 40.7 % | **1.88×** |
| Kp 176, Kd 128 | 176 | 128 | 0.941 | 0.919 | 1.89× | 45.0 % | 1.39× |

**It is not a strict domination and I will not claim one.** `Kp 148 / Kd 128` beats ZN-PI on the ring
(0.900 vs 0.914) and on root margin (1.51× vs 1.44×); ZN-PI beats it on blind-band GM
(**2.01× vs 1.93×**, a 4 % edge). Those are not equally weighted: the **GM is already comfortable in
both** (5.7 vs 6.1 dB against today's 5.0), while the **ring root is the `s`-uncertain gate the whole
V286 ladder exists to bound**. ⇒ **prefer the Kp-only cut**, and note that it needs no Kd
byte at all, so it does not interact with the ladder's purpose.

### 1.3 The decomposition — which cut is doing the work

```
today               248/128 : |L(7.3)| = 0.9760
Kp 248->148 alone   148/128 : |L(7.3)| = 0.9001   (delta -0.0759)   <-- the Kp cut does ALL the work
Kd 128->122 alone   248/122 : |L(7.3)| = 0.9887   (delta +0.0127)   <-- the Kd cut is a NET DRAG
both                148/122 : |L(7.3)| = 0.9139   (delta -0.0621)
GM:  today 1.774x | Kp-only 1.930x | Kd-only 1.840x | both 2.013x
```

⇒ **§A5's sentence "the Kp cut helps the ring more than the small Kd cut hurts it" is exactly right,
and the Kd cut's contribution to the ring gate is negative.** Its only positive contribution is
+0.08× of blind-band GM.

### 1.4 🛑 THE CORRECTION THAT MATTERS — the ring's lower root is a function of **Kp**

The published statement *"its Kd 122 sits only 3 % above the 7.3 Hz ring root of 118"* compares a
candidate that **also cuts Kp** against a root computed at **Kp 248**. Recomputed at each candidate's
own Kp (pooled arms):

| Kp | 248 | 220 | 200 | 176 | **148** | 128 | 100 | 64 | 0 |
|---|---|---|---|---|---|---|---|---|---|
| **lower root (Kd)** | **116.7** | 106.1 | 99.4 | 92.2 | **84.9** | 80.4 | 75.0 | 69.4 | 63.6 |
| **Kd 128 / root** | 1.10× | 1.21× | 1.29× | 1.39× | **1.51×** | 1.59× | 1.71× | 1.84× | 2.01× |

**Mechanism [EVIDENCE, from the byte-exact `C(f)`]:** the root is where `|Ls·R + Lr| = 1`, and lowering
Kp both shrinks `|C|` and rotates it toward the D term's +88.7° at 7.3 Hz. The servo arm therefore
sits *further* from anti-phase with the r24 arm and cancels less of it — the sum shrinks — so the
ring stays sub-unity down to a **lower** Kd. **A Kp cut buys Kd headroom.**

**Robustness — this survives every uncertainty in the framework** (`zn_backwards_supp.py`):

| perturbation | root @ Kp 248 | root @ Kp 148 | Kd 128 margin @ Kp 148 |
|---|---|---|---|
| pooled arms (baseline) | 116.7 | 84.9 | 1.51× |
| r36 arms (largest servo share) | 117.6 | 72.3 | **1.77×** |
| r38 arms (smallest servo share) | 113.1 | 78.7 | 1.63× |
| `\|L_today\|` = 0.944 | 100.9 | 70.5 | 1.82× |
| `\|L_today\|` = 0.990 | 123.3 | 91.0 | 1.41× |
| `s` = 0.24 (low end) | 118.5 | 66.3 | 1.93× |
| `s` = 0.52 (high end) | 112.9 | 90.5 | 1.41× |

⭐ **The `s` sweep is the propagation `STATE.md` records as never having been done.** I did it coarsely
— scale the r24 arm by `s/0.37`, renormalise so `|Ls| + |Lr|` is preserved — and the answer is that
**`s` moves the root at Kp 248 by only ±3 % (113–118.5)**; almost all of the published
`[102–125]` interval is phase variation, as `STATE.md` says. **Under every value of `s`, Kd 128 at
Kp 148 sits ≥ 1.41× above the root.** [BELIEF — the renormalisation is a modelling choice, not a
measurement; the ladder is still the right instrument. But the *sign and rough size* of the
sensitivity are now on record, and they do not threaten this candidate.]

---

## 2. Q2a — the low-overshoot ZN family vs the lower root

### 2.1 Your arithmetic: confirmed in conclusion, corrected in derivation

The classic low-overshoot variants use `Kp' = 0.33·Ku'` and `0.2·Ku'`. Which `Ku`?

- **Your 75 / 45 used `Ku = 227`** — the Ku measured **at today's Kp 248**, i.e. with accel-frame
  integral action still on. `0.33 × 227 = 75`, `0.2 × 227 = 45`. ✔ arithmetic correct for that Ku.
- 🛑 **ZN-proper hunts with integral action OFF.** In this frame our Kp *is* the accel-frame integral,
  so the ZN hunt configuration is `Kp = 0`, where `Ku(Kd) = 270` (§A4's own number). ⇒
  **"some overshoot" = Kd 90 / Kp 183; "no overshoot" = Kd 54 / Kp 110.**

| ZN form | `k_f` | `Ti` | **Kd cell** | **Kp cell** | `Td` | root @ its own Kp | verdict |
|---|---|---|---|---|---|---|---|
| classic PID (Ku@Kp0) | 0.60 | 15.8 ms | 162 | 329 | 3.9 ms → 🛑 no cell | 108 | above |
| classic PI (Ku@Kp0) | 0.45 | 26.3 ms | 122 | 148 | — | 84.9 | above (1.44×) |
| **some overshoot** (Ku@Kp0) | 0.333 | 15.8 ms | **90** | **183** | 10.5 ms → 🛑 no cell | **94.2** | 🛑 **0.95× — BELOW** |
| **no overshoot** (Ku@Kp0) | 0.20 | 15.8 ms | **54** | **110** | 10.5 ms → 🛑 no cell | **76.8** | 🛑 **0.70× — BELOW** |
| some overshoot (Ku@Kp248) | 0.333 | 17.8 ms | **76** | **136** | 11.9 ms | 89 | 🛑 **0.85× — BELOW** |
| no overshoot (Ku@Kp248) | 0.20 | 17.8 ms | **45** | **82** | 11.9 ms | 72.0 | 🛑 **0.63× — BELOW** |

**And the direct test — `|L(7.3)|` computed at each form's own (Kp, Kd):**

| form | Kp | Kd | ring ratio | `\|L(7.3)\|` | GM | DC tracking |
|---|---|---|---|---|---|---|
| some overshoot (Ku@Kp 0) | 183 | 90 | 1.034 | 🛑 **1.010** | 2.49× | 45.9 % |
| no overshoot (Ku@Kp 0) | 110 | 54 | 1.081 | 🛑 **1.055** | 4.15× | 33.8 % |
| some overshoot (Ku@Kp 248) | 136 | 76 | 1.039 | 🛑 **1.014** | 3.04× | 38.7 % |
| no overshoot (Ku@Kp 248) | 82 | 45 | 1.092 | 🛑 **1.066** | 5.11× | 27.6 % |

### 2.2 The structural consequence, stated plainly

🛑 **The entire low-overshoot ZN family is forbidden on this loop — not by gain margin, which it has in
abundance (2.5–5.1×), but by the 7.3 Hz lower root.** Every one of them puts `|L(7.3)| > 1`, i.e.
**re-arms the self-sustained 7 Hz cycle that V281 rev 3 finally killed.**

**Why, mechanically [EVIDENCE from the composition]:** the 7.3 Hz ring is a *sum of two arms*, and only
the servo arm carries Kp and Kd. The r24 arm (`FUN_0003aa2c`, no Kp/Kd reference anywhere in it) is a
**fixed 1.19∠−27°** that the controller cannot shrink. Sub-unity today is achieved by the servo arm
sitting near anti-phase and **cancelling** part of it. Turn the controller down far enough and that
cancellation is withdrawn — the sum grows back toward the bare r24 arm. **This loop has no
"turn everything down and it gets calmer" regime, because a fixed disturbance path does not turn down
with the controller.** That single fact is the answer to "is there any low-gain regime available".

⭐ **But there IS a low-gain direction, and it is Kp, not Kd.** The floor falls with Kp
(116.7 → 63.6), and **Kd = 128 stays above it at every Kp on the table**. So the operator can have a
genuinely lower-gain, lower-authority loop — down to Kp 100 or below — **provided Kd is left where it
is.** Working backwards from "no overshoot" therefore lands on **Kp cuts at fixed Kd**, which is
exactly Q1's candidate. The two questions converge.

---

## 3. Q2b — WHICH loop's overshoot, and does inner-loop lead help?

**The complaint is path overshoot on a curve. That is unambiguously an OUTER-loop (openpilot) property.**
openpilot closes on path/curvature at roughly 0.3–1.5 Hz. It sees the EPS as a plant, and what it sees
is the inner loop's own closed-loop response `T_inner(f) = L(f)/(1+L(f))` **in rate** — a gain and a
phase lag. Both are computed here from the byte-exact `C·H_lag·H_fb` times the measured plant model.

| candidate | Kp | Kd | `\|T_inner\|` @1 Hz | phase @1 Hz | equivalent lag |
|---|---|---|---|---|---|
| today | 248 | 128 | **0.668** | −4.76° | **13.2 ms** |
| Kp 148, Kd 128 | 148 | 128 | **0.545** | −4.67° | 13.0 ms |
| ZN-PI | 148 | 122 | 0.545 | −4.88° | 13.6 ms |
| F | 248 | 160 | 0.667 | −4.26° | **11.8 ms** |
| Kd 192 | 248 | 192 | 0.667 | −3.76° | **10.5 ms** |
| Kp 148, Kd 160 | 148 | 160 | 0.546 | −3.56° | 9.9 ms |

`|T_inner|` is flat to within 1 % across 0.3–2.5 Hz for every candidate, so these rows are the whole
outer-loop-relevant picture.

**Your hypothesis, tested rather than accepted:**

- ✅ **Direction: CORRECT.** More inner-loop lead (Kd up) *does* reduce inner lag: 13.2 → 11.8 ms at
  Kd 160, → 10.5 ms at Kd 192. A Kd cut to 122 *does* add lag: 13.2 → 13.6 ms. [EVIDENCE — computed
  from the byte-exact transfer functions plus the measured plant phase model.]
- 🛑 **Magnitude: NEGLIGIBLE.** The whole Kd 128 → 160 move is worth **1.4 ms**. The operator's own
  StarPilot `SteerDelay` is **0.2 s**, and there is a CAN/actuator chain on top. **1.4 ms is ~0.7 % of
  the outer loop's delay budget.** No path overshoot is measurably attributable to it, in either
  direction. [EVIDENCE for the 1.4 ms; the 200 ms comes from the decoded toggle backup — BELIEF that
  it is the dominant term, though it is 140× larger so the conclusion is insensitive.]
- ⭐ **What actually reaches the outer loop is GAIN.** `Kp 248 → 148` multiplies the outer loop's plant
  gain by **0.545/0.668 = 0.82×** (0.76× at the mid-load DC operating point) **at every frequency
  openpilot closes at**. That is a **first-order 18–24 % reduction in outer-loop gain**, against a
  0.7 % change in delay. **Less outer-loop gain is less path overshoot, directly.**

⇒ **ANSWER.** Tuning the inner loop toward ZN reduces the outer loop's path overshoot — but through
the **authority** channel, not the **lead** channel. **Kp is the oversteer lever. Kd is not, in either
direction.** This puts Q1's Kp-only cut in a *better* light than your hypothesis did, but for a
different reason than you proposed: not because it leaves Kd alone to preserve lead, but because
**the lead channel is irrelevant at this scale and the Kp channel is where all the effect is.**
[EVIDENCE for the two magnitudes; **BELIEF** for the causal attribution of felt oversteer to outer-loop
gain — the record's own reservation about the `Re` → felt-amplitude map applies here too.]

⚠ **Sizing note for the operator, since he just added authority.** He deployed ≈**1.70×** on the
openpilot side (SR 12.5 → 16.0 near centre, ×1.28; `SteerKP` 0.6 → 0.8, ×1.33). `Kp 248 → 148`
returns **0.76–0.82×** of it. Net vs the drive before r39: still **≈1.29–1.39× more** outer-loop
authority than he had. **The Kp cut alone will not return him to the pre-r39 feel** — it claws back
about **45 %** of what he just added. If he wants to land closer to neutral, either take Kp lower
(Kp 128 → 0.70× of the added authority returned; Kp 100 → 0.59×) or back one openpilot toggle off.

---

## 4. Q3 — the deadband / stall cost of the Kp cut. **Real, modest, NOT disqualifying.**

### 4.1 Method — the existing metric, called directly

`rlog-tools/studies/osc-highangle/stall_kp_counterfactual.py` **calls
`v281r3_read_r35.moving_runs(r, R, 40)`** — the same function that produced the published
*"7 stall runs / 14.8 s at idx 54–79"*. Definition, unchanged: segment ENGAGED & `|angle| ≥ 30` &
`idx ≥ 40` into runs ≥ 1.0 s; a run is STALLED if its **median** `rate/ref < 0.5` **and** its median
`|driver torque| < 1000`. **No threshold was moved and no new statistic was invented.**

**The counterfactual map.** With Ki = 0 the DC chain is a pure static gain ∝ Kp (`P = E·Kp>>8` is the
only DC term; the 254/256 taper, the output lag, the 5346 forward gain and the feedback EMA are all
Kp-independent and cancel). A run whose measured median `rate/ref = x` had `L_dc = x/(1−x)` at
Kp 248; at `Kp'`, `L' = L·Kp'/248` and `x' = L'/(1+L')`. The map is monotone, so the run median maps
to the run median, and the stall gate `x' < 0.5` becomes a gate on the **measured** median:

| Kp | 248 | 200 | 176 | **148** | 128 | 100 |
|---|---|---|---|---|---|---|
| equivalent measured-`x` stall gate | 0.500 | 0.554 | 0.585 | **0.626** | 0.660 | 0.713 |

### 4.2 Result — and the baseline reproduces the published number exactly

**r35 (V281 rev 3, Kp flat 248, Ki 0) — the like-for-like Ki-0 baseline, the build that *created* the deadband:**

| Kp | stall runs | stall secs | longest run | idx p50 | DC tracking |
|---|---|---|---|---|---|
| **248 (as flown)** | **7** | **14.8 s** | 3.4 s | 70 | 53.5 % |
| 200 | 8 | 17.3 s | 3.4 s | 72 | 48.1 % |
| 176 | 8 | 17.3 s | 3.4 s | 72 | 45.0 % |
| **148** | **9** | **18.9 s** | **3.4 s** | 74 | 40.7 % |
| 128 | 11 | 22.1 s | 3.4 s | 75 | 37.3 % |
| 100 | 13 | 24.9 s | 3.4 s | 79 | 31.7 % |

✅ **The Kp 248 row is `7 runs / 14.8 s` — the published r35 figure, to the digit.** That is my
validation that the reused metric is the metric.

**Verdict on Q3.** `Kp 248 → 148` costs **+2 stall runs and +4.1 s (+29 %, +28 %)** on the route that
exhibited the symptom. **The longest run does not grow at all (3.4 s at every Kp)** — the cut adds
*more* marginal runs, it does not deepen the worst one. For scale, **Ki 50 took the same metric
7 → 1**, so a Kp cut to 148 undoes roughly **one third of one step** of what Ki 50 was worth. **It is
a real cost and it should be pre-registered as one, but it is not disqualifying**, and it is far
smaller than the gate improvements it buys.

🛑 **Two honest caveats, both cutting against the candidate:**
1. **This is a LOWER bound.** The map holds road load and the openpilot demand index fixed. They would
   not be: a slower wheel raises the path error openpilot sees, so it winds `idx` **up**, which raises
   `ref` and makes the stall gate **harder**. The true worsening is larger than +29 % by an amount I
   cannot size from these routes. [BELIEF, flagged.]
2. **The operator now runs +70 % outer authority**, which pushes `idx` up on its own — so the r39-era
   `idx` distribution is not r35's. The counterfactual is against r35's distribution because that is
   the only Ki-0 route with the symptom.

*(For completeness: on r36/r37/r38 — Ki 50 routes, not the right baseline — Kp 148 adds **zero** stall
runs, because Ki 50 lifts the median `rate/ref` to 0.88–0.97, far above even the Kp-100 gate of 0.713.
That is a measure of how much headroom the integrator bought, not evidence about a Ki-0 candidate.)*

---

## 5. Q4 — pre-registration for `Kp 148 / Kd 128 / Ki 0`

**Written before any build exists. All four endpoints ride channels ALREADY FLYING ON V282:**
`0x18F` `gp-0x6a56` at 100 Hz · the 427 delivered-torque tap `gp-0x6B38` sar0 at 50 Hz (wire ×0.2) ·
`0x14A` byte 4 bits 3–7.

🛑 **Respecting the blind band:** the 27–32 Hz binding mode is above the 427 tap's 25 Hz Nyquist and is
reachable on the 100 Hz stream only through the unresolved 80→20 alias. **No frequency-specific
endpoint is registered there.** Endpoint (C) is an **ENERGY** endpoint over 0–50 Hz, which
`task5rate` established is sound on these channels (no anti-alias filter anywhere in the path, so
folded power is unattenuated) — V286 spec §0b.

### (A) THE PRIMARY ENDPOINT — the 7.3 Hz ring's decay rate. **This is the reason for the build.**

**Statistic:** the per-episode complex-ACF fit already in use — `|ρ(τ)| = exp(−α|τ|)` on the 6–8.5 Hz
band of the `0x18F` wheel rate in hands-light strong-turn episodes, `Q = π·f₀/α`, `|1−L| ≈ 1/Q`.
**Per episode, ≥ 5 episodes**, exactly as the 0.976 [0.944–0.990] figure was obtained.

| | today (measured) | **predicted at Kp 148** |
|---|---|---|
| `\|L(7.3)\|` | 0.976 [0.944–0.990] | **0.900** |
| `Q` | **41.7** | **10.0** |
| ring decay `α` | 0.55 /s | **2.29 /s** |
| ring time constant | **1.82 s** | **0.44 s** |
| cycles to 1/e | 13.3 | **3.2** |

🛑 **PASS:** pooled `Q ≤ 18` (i.e. `|L| ≤ 0.945`) over ≥ 5 episodes — comfortably clear of today's
measured lower bound.
🛑 **FAIL / REFUTED:** pooled `Q ≥ 25` (`|L| ≥ 0.96`), i.e. the ring's decay is statistically
indistinguishable from V282's. **That falsifies the composition rule underneath this entire
framework** — the same rule `zn285` §5.3 flagged as its load-bearing assumption — and the correct
response is to stop sizing candidates from it, not to try another dose.
🛑 **DO-NOT-CONTINUE:** any episode with `|L| > 1.00` (a *growing* 7 Hz cycle) — that would mean the
root is far higher than every arm set predicts, and it invalidates the Kp direction outright.

### (B) THE ATTRIBUTION + AUTHORITY ENDPOINT — DC tracking on the 427 tap

**Statistic:** the existing D2 cell — median `rate/ref` and median `|T|` in hands-light strong turns
(`|angle| ≥ 30`, `40 ≤ idx ≤ 200`, `|tq_raw| < 1216`), `ref` from the map through the on-car chain.

| measured `rate/ref` today | predicted at Kp 148 | predicted `\|T\|` ratio |
|---|---|---|
| 0.42 | **0.30** | 0.72× |
| 0.65 (r35 p50) | **0.53** | 0.81× |
| 0.83 | **0.74** | 0.90× |
| 0.92 (r36–r38 p50) | **0.87** | 0.95× |

🛑 **PASS (the edit is live and acting as modelled):** median `rate/ref` in the idx 40–80 cell falls by
**≥ 0.08 absolute** vs the V282 comparison drive, AND median `|T|` in the *same frames* falls to
**0.78–0.86×**. Both are on the flying 427 tap at 50 Hz.
🛑 **FAIL — the edit did not act:** `rate/ref` unchanged (Δ < 0.03) **or** `|T|` ratio > 0.95. Either
means the tap says Kp is still 248 (mis-flash / wrong slot) or the DC model is wrong; **do not
interpret endpoint (A) at all in that case** — it would be a null from the wrong image.
⚠ **Attribution first, per the standing law:** fit Kp from the 427 tap against the map+chain before
reading anything else. Flat 148 must beat flat 248 and the stock LERP.

### (C) THE BLIND-BAND SAFETY ENDPOINT — total HF energy, 0–50 Hz

**Statistic:** engaged HF energy on the 100 Hz `0x18F` rate stream over **0–50 Hz**, with
**33–49.9 Hz reported as its own sub-band**, speed- and engagement-matched against the V282 drive.
No phase margin is computed and none is cited.

🛑 **PASS:** the 33–49.9 Hz shelf is **≤ 1.0×** V282's (predicted: a small *fall* — the Kp cut reduces
`|C|` at every frequency, ~0.94× at 40 Hz, and GM improves 1.77× → 1.93×).
🛑 **FAIL — STOP FLYING IT:** the 33–49.9 Hz shelf **rises ≥ 1.3×** engagement-matched. That is the
signature of a loop-driven resonance folding down from 68–73 Hz, the specific hazard `task5rate`
identified. A rise this candidate's direction should not produce means the plant model above 25 Hz is
wrong in the dangerous direction.

### (D) THE PRE-REGISTERED **COST** — the deadband, on the existing metric

**Statistic:** `v281r3_read_r35.moving_runs(idx_lo=40)` stall runs, normalised per 100 s of eligible
hands-light strong-turn time (r35 had 36.6 s eligible → 7 runs = **19.1 runs/100 s**).

🛑 **EXPECTED (not a failure):** **≈ 24.6 runs/100 s** (the 9 / 36.6 s counterfactual), longest run
unchanged at ≈ 3.4 s.
🛑 **COST FAIL — the deadband is the wrong price:** **> 38 runs/100 s** (2× the r35 baseline) **or**
any single stall run **> 5 s** **or** the D3 dead fraction (idx 20–40, `|rate| < 1 deg/s`,
speed-matched 8–12 m/s) exceeding r35's **0.336**. Any of those and the candidate is withdrawn in
favour of **Kp 176** (8 runs / 17.3 s counterfactual, ring 0.919, GM 1.89×).
⚠ **The operator's felt symptom is the arbiter of this one, not the number** — he described the r35
deadband before any statistic named it.

### (E) REQUIRED READ, not a gate — the arm split at the new Kp

`0x14A` b4.4 `sign(r24)` plus the 427 `T` phasor, per episode. The root's new location (84.9 predicted)
is `s`-dependent, and this is the drive that would let V286's ladder — if it flies — be interpreted at
Kp 148 rather than Kp 248.

### What this build is, physically

`V287 = V282 + Kp record slot 7 Y → 148`. `248 = 0x00F8`, `148 = 0x0094` — **5 low bytes**
(`0xE5384/86/88/8A/8C`, `f8` → `94`) **plus the `0xE5FFC` CRC**, exactly the shape of V285's 9-byte
edit. **Cal-only, one record, X untouched, Kd untouched, Ki untouched, cave untouched, hook untouched,
427 tap untouched.** Outside the bricking class. **The four-way adversarial pass still applies** — it
carries a lever.

---

## 6. What would falsify this document

1. **The composition rule** (`L_tot = |Ls·R + Lr|` with ripple shares read as loop-gain shares). Every
   ring number here rests on it, and `zn285` §5.3 records that it self-refuted once (`|L_tot| = 1.76`
   against a measured `F7 = 0.00/100 s`). Endpoint (A) is a direct test of it.
2. **The plant's phase above 25 Hz.** Every GM column inherits the −3.75°/Hz extrapolation. Unchanged
   from the addendum, and unchanged in its consequences: the Kp cut *improves* GM under either model.
3. **The Kp-linearity of the DC chain.** [EVIDENCE from the bytes with Ki = 0.] If a build ever carries
   Ki ≠ 0, §4's whole map is void — the integrator makes DC tracking Kp-independent.
4. **The root-moves-with-Kp result** (§1.4). It is the one genuinely new structural claim here. It
   follows from the byte-exact `C(7.3, Kp, Kd)` and the fixed r24 arm, and it holds across every arm
   set and every `s`; but it is a *model* result, and the r24 magnitude `s` has still never been
   directly measured. **If the V286 ladder flies and returns an `s` outside [0.24, 0.52], recompute.**
5. **`g = 0.030 deg/s per count`** for the DC column. `zn285` §1.1 measured `g` spanning **7.4×**
   across four strata. The *ratio* 0.76× is `g`-independent; the *absolute* 53.5 % → 40.7 % is not.

---
---

# PART II — the ACTUATOR / FIDELITY reframing (2026-09-04, second pass)

`team-lead` delivered two reframings after Part I. **Both change the ranking, and the second one
REVERSES my Part I recommendation.** Part I is left standing as written; this part supersedes its
§5 recommendation.

**Code:** `analysis-2020accord/studies/pidframe/zn_fidelity.py` (stdout `_znfid_out.txt`).

---

## II.0 🛑 CONVENTION AUDIT — the record carries TWO loop models and they disagree at 7.3 Hz

Before computing any closed-loop `|T(f)|` I checked that the pieces compose. **They do not.**

| model | at 7.3 Hz | implies |
|---|---|---|
| **(a) Nyquist / GM** (addendum §A3; negative feedback, instability at ∠L = −180°) | `\|L\| = 1.319 ∠−71.5°` | `\|1+L\| = 1.89`, `\|T\| = 0.70` — **no peak at all** |
| **(b) measured ring** (per-episode complex-ACF, 5 episodes; positive feedback, `\|1−L\| ≈ 1/Q`) | `\|L\| = 0.976`, `Q ≈ 42` | a **~42× resonant peak** |

**Model (a) is a smooth delay model fitted at 20 Hz. It contains no plant resonance and no r24 lane
at all** — and the ring is measured to live in the r24 arm (`FUN_0003aa2c`, which carries no Kp and
no Kd). They are not two views of one loop; they are two different loops.

⇒ 🛑 **A SINGLE CLOSED-LOOP `|T(f)|` CURVE IS NOT COMPUTABLE FROM WHAT THIS KIT HAS MEASURED.**
I decline to produce one. §II.8 lists exactly what that costs and what would fix it.

## II.1 ⭐ THE COMMAND BAND, MEASURED — 0–0.75 Hz, not 0–3 Hz

You asked me to check the real spectrum rather than trust the number. Engaged LKAS command,
100 Hz, Welch `nperseg` 2048, cumulative energy fraction:

| route | <0.5 Hz | <1.0 Hz | <2.0 Hz | <3.0 Hz | **95 % band** |
|---|---|---|---|---|---|
| r34 | 0.929 | 0.983 | 0.997 | 0.998 | **0.59 Hz** |
| r35 | 0.920 | 0.975 | 0.994 | 0.996 | **0.71 Hz** |
| r36 | 0.893 | 0.975 | 0.996 | 0.997 | **0.74 Hz** |
| r37 | 0.921 | 0.983 | 0.997 | 0.998 | **0.60 Hz** |
| r38 | 0.897 | 0.978 | 0.996 | 0.997 | **0.71 Hz** |

*(the demand index `gp-0x697a`, which adds the taper and sign, is 95 % below 1.40–2.78 Hz)*

🛑 **97.5–98.3 % of engaged command energy is below 1 Hz.** Every dynamic feature of the loop — the
5.05 Hz output-lag pole, the 7.3 Hz ring, the 9.64 Hz D=P corner, the 16.5 Hz feedback EMA, the
20 Hz creep line — sits **7× to 27× above the command band.**

**Consequences for the four fidelity criteria:**
- **Criterion 1** (`|T|` flat and near 1 across the command band) **collapses to `|T(0)| = 1.0`.**
- **Criterion 3** (minimum phase lag in band) is **MOOT**: across *every* candidate the inner-loop
  lag at 0.75 Hz spans **1.32°** (−2.54° to −3.86°) = **4.9 ms**, against openpilot's own 200 ms
  `SteerDelay`. It cannot discriminate between candidates. [EVIDENCE]
- **Criteria 2 (peaking) and 4 (linearity) carry the whole decision.**

## II.2 THE FIDELITY TABLE

| candidate | Kp | Kd | `\|T(0)\|` | scale err | ring peak | vs today | GM | deadband |
|---|---|---|---|---|---|---|---|---|
| **today (V282)** | 248 | 128 | **0.535** | 1.87× | **41.7** | 1.00× | **1.77×** | 7 runs |
| Kp 200 | 200 | 128 | 0.481 | 2.08× | 15.7 | 0.38× | 1.85× | 8 |
| Kp 176 | 176 | 128 | 0.450 | 2.22× | 12.3 | 0.30× | 1.89× | 8 |
| **Part I: Kp 148** | **148** | **128** | **0.407** | **2.46×** | **10.0** | **0.24×** | **1.93×** | **9** |
| Kp 128 | 128 | 128 | 0.373 | 2.68× | 8.9 | 0.21× | 1.96× | 11 |
| ZN-PI | 148 | 122 | 0.407 | 2.46× | 11.6 | 0.28× | 2.01× | 9 |
| **F: Kd 160** | 248 | **160** | **0.535** | 1.87× | 11.0 | 0.27× | 1.48× | **7 (unchanged)** |
| ⭐ **Kd 192** | 248 | **192** | **0.535** | **1.87×** | **6.5** | **0.16×** | 1.27× | **7 (unchanged)** |
| Kd 216 | 248 | 216 | 0.535 | 1.87× | 5.0 | 0.12× | 1.14× | 7 |

⚠ `ring peak = 1/|1−L_ring|` is a **transfer-function** number. `zn285` §5.3 item 5 explicitly warns
it does **not** map to felt amplitude (`Q ≈ 41` vs the operator's "a damped ring at ~40 %"). **Read
the ratio column, not the value.**

🛑 **THE PAIRWISE COMPARISON THAT DECIDES IT, and it needs no optimiser:**

```
Kp 148, Kd 128 : ring peak 10.0 , |T(0)| 0.407 , GM 1.93x , deadband 7 -> 9 runs
Kp 248, Kd 192 : ring peak  6.5 , |T(0)| 0.535 , GM 1.27x , deadband UNCHANGED
```

**Kd 192 is better on BOTH fidelity criteria and costs no deadband. It pays in blind-band GM alone.**

⇒ 🛑 **ON THE ACTUATOR SPEC, MY PART I RECOMMENDATION (Kp 148) IS DOMINATED.** You asked to be told
if your candidate loses. **It loses.** The currency is blind-band gain margin, not DC authority, and
the ranking inverts relative to the loop-gain framing.

**The Pareto frontier** (best ring at each `|T(0)|`, GM floor 1.48× = candidate F's own margin) —
note the best Kd is ≈160–174 at *every* Kp, i.e. **Kd and Kp are nearly separable**: Kd sets the
ring, Kp sets `|T(0)|`:

| Kp | `\|T(0)\|` | best Kd | `\|L_ring\|` | ring peak |
|---|---|---|---|---|
| 248 | 0.535 | 160 | 0.909 | 11.0 |
| 200 | 0.481 | 166 | 0.854 | 6.8 |
| 176 | 0.450 | 168 | 0.830 | 5.9 |
| 148 | 0.407 | 170 | 0.805 | 5.1 |
| 128 | 0.373 | 172 | 0.786 | 4.7 |

## II.3 🛑 ADJUDICATION — is ZN the wrong recipe? **YES. I agree, and structurally.**

1. **ZN is a regulator recipe.** It targets quarter-amplitude decay ≈ 25 % step overshoot, i.e. it
   *designs in* a closed-loop peak of ≈1.3–1.5. Criterion 2 forbids exactly that. For a follower,
   ZN optimises the wrong functional.
2. **ZN's own reachable form here (`Td` has no cell, so ZN-PI) lands at Kd 122 — a Kd CUT.** The
   fidelity optimum wants Kd *raised* to 160–192. **ZN points the wrong way on the one axis that
   actually sets the peaking.** That is the decisive structural objection, and it is independent of
   any argument about overshoot semantics.
3. **The one thing ZN got right is an accident of arithmetic**: ZN-PID's Kd 162 coincides with
   candidate F's 160. Keep the number, drop the derivation.

⇒ **ZN does not earn its place. Do not tune to a ZN rule. Tune to the peaking/GM frontier in §II.2.**

**BUT — the flat-magnitude target cannot be met either.** `max|T| ≤ 1.05` needs
`|L_ring| ≤ 0.512`. Sweeping the whole feasible box (GM floor, `Kd ≥ 1.10×` its own root, `|T(0)|`
above the outer-integrator floor), **the best ring anywhere is `|L| = 0.640` — a ~2.8× peak — and
only at a GM of 1.15× (thin).** ⇒ **criterion 2 as literally written is UNREACHABLE by any
(Kp, Kd) pair.** The honest design question is *how much* peaking at what GM, not flat vs not.

## II.4 OUTER-INTEGRATOR HEADROOM — the gate that replaces "DC authority is cheap"

Basis: `max|i| = 1.225` against `±2.110` (58.1 % of bound), `saturated` 0.00 %.
Conservative **multiplicative** model, `|i'| = max|i| / k_T` where `k_T = |T(0)|'/|T(0)|`:

| candidate | Kp | `\|T(0)\|` | `k_T` | required mult. | **% of bound** |
|---|---|---|---|---|---|
| today | 248 | 0.535 | 1.000 | 1.000× | 58.1 |
| Kp 200 | 200 | 0.481 | 0.900 | 1.112× | 64.5 |
| Kp 176 | 176 | 0.450 | 0.840 | 1.190× | 69.1 |
| **Kp 148** | 148 | 0.407 | 0.761 | 1.314× | **76.3** |
| Kp 128 | 128 | 0.373 | 0.696 | 1.436× | 83.4 |
| Kp 100 | 100 | 0.317 | 0.592 | 1.688× | **98.0 — thin** |
| **every Kd-only candidate** | 248 | 0.535 | 1.000 | 1.000× | **58.1 — no cost** |

**The floor, as a FUNCTION of `max|i|`** (so it can be re-evaluated when `dec39` reports r39):
saturation when `max|i|/k_T = 2.110`, i.e. `k_T,min = max|i|/2.110`.

| `max\|i\|` | % of bound | `k_T` min | `\|T(0)\|` min | **⇒ Kp FLOOR** |
|---|---|---|---|---|
| 1.000 | 47.4 | 0.474 | 0.254 | **73** |
| **1.225 (prior routes)** | 58.1 | 0.581 | 0.311 | **97** |
| 1.400 | 66.4 | 0.664 | 0.355 | **119** |
| 1.600 | 75.8 | 0.758 | 0.406 | **147** |
| 1.800 | 85.3 | 0.853 | 0.457 | **181** |
| 2.000 | 94.8 | 0.948 | 0.507 | **222** |

🛑 **If r39's `max|i|` comes back at 1.6 or above, Kp 148 is already AT or BELOW the floor.** Given
he just added 1.70× of outer authority on r39, a higher `max|i|` is the likely direction. **Every
Kd-only candidate is exempt from this gate entirely**, because it does not move `|T(0)|`.

⚠ **Why the multiplicative model is probably pessimistic, flagged rather than used silently:** at
steady state `p → 0` and the feedforward is inner-loop-blind, so structurally `i' = u/k_T − f` —
**additive**, not multiplicative. `STATE.md`'s own measured steady-curve decomposition is
`f = +0.800` with `i = −0.392` **opposing** it and net output only `+0.108`. With `f` dominant and
`i` of the opposite sign, demanding more output makes `i` **less** negative — `|i|` would *fall*.
I report the multiplicative bound because it is the one that can disqualify a candidate.
[BELIEF — I do not have `max|i|` paired with `u` on any route.]

## II.5 `Kp = 0` — **I AGREE IT STAYS DEAD**, and the actuator spec adds a third, independent reason

1. `|T(0)| = 0` **exactly** — type-0 plant, `C(s) = Kd_r·s`, `L(0) = 0`. [EVIDENCE]
2. The outer integrator **cannot close a plant with zero DC gain**: it winds up without bound
   against its `±2.110` and rails. The lane is lost, not merely weak.
3. **NEW:** `|T(0)| = 0` is *maximal* infidelity. It is not a low-authority actuator; it is not an
   actuator.

⇒ Confirmed dead — and note this kills `Kp = 0` **even as a Ku-hunt drive**, which Part I had left
open as "flyable on a road where the car not steering itself is acceptable."

## II.6 🛑 CAN THE DEADBAND BE CURED WITHOUT INTEGRAL ACTION? **Essentially NO — one exception**

The deadband is a **stiction** nonlinearity: sustained torque is needed to break away, and only a
term with **DC in the command direction** can supply it. I measured the signed mean of each term
inside the 7 identified r35 stall runs, projected on the command sign, through the byte-exact chain:

| term | mean signed, in stalls | as % of P |
|---|---|---|
| **P** (`E·Kp>>8`) | **+5574** | 100 % |
| **D** (`dE·Kd>>3`) at Kd 128 | **+116** | **2.1 %** |
| D at Kd 192 (extrapolated) | +175 | 3.1 % |
| **I** at Ki 50 | **+4168 … +10240** (railed at the anti-windup ceiling in 3 of 7 runs) | 75–184 % |

🛑 **I RETRACT MY OWN FIRST PREDICTION.** I expected `D ≈ 0` in a stall because `dE ≈ 0`. **Measured,
`|D| = 1616 counts, 29 % of |P|`** — the wheel is not frozen (a "stall" here is `rate/ref < 0.5`,
not zero rate; median rate in these runs is 5.8–17.8 deg/s). **But that D is essentially pure AC**:
DC-to-AC ratio **0.059 median**. It supplies **dither, not breakaway**.

⇒ **A Kd RAISE CANNOT CURE THE DEADBAND — it is ~100× short** (+59 DC counts going 128→192, against
the integrator's +4168–10240). [EVIDENCE — measured on the flown r35 frames.] *(Caveat, honestly:
dither genuinely does break stiction in real mechanisms, and I cannot rule out a second-order
benefit from more AC. But it is not the mechanism that cured it, and I would not size a build on it.)*

**The remaining Ki-0 options, ranked:**
1. **Kp raise (shaped at low idx)** — P *is* the DC term, so this works in principle. **It is V284,
   already built and rejected**: it drives `|L(7.3)|` to 1.106–1.277, above unity, across the ring's
   own index range. **Closed.**
2. ⭐ **THE MAP / REFERENCE** — raising `sp` raises `E` raises `P`, which is real DC. **And with Kp
   FLAT it is loop-gain-neutral**: the small-signal loop gain is `∂T/∂fb = −(Kp/256)·chain`, which
   contains no `sp` at all, and depends on the map only through `idx → Kp` — a dependence a flat Kp
   table removes entirely. [EVIDENCE from the arithmetic.] **This is the only live cal-only, Ki-0
   route to breakaway torque.**
   ⚠ **But it may be invisible to the current metric**: the stall statistic is `rate/ref`, and a map
   raise raises `ref` too. It would cure the symptom while the number barely moves. A map-raise build
   needs a *different* endpoint (absolute rate, or `|T|` at breakaway), pre-registered as such.
   ⚠ And V280 rev 2 already took the map to the ×6 linear top; further headroom runs into the
   `±3072` output clamp.
3. **The dedicated feedforward slot `gp-0x6b2c`** — it exists structurally, immediately before the
   forward gain. It is **doubly dead**: its LERP table at `tp+0x7736..0x7744` is all-zero AND its
   gate `gp-0x6809 == 1` can never be true (no writer anywhere in the image). Reviving it needs
   **both** a table edit **and** a code edit to the gate ⇒ **cave class, the kit's only bricking
   class.** Named for completeness, not recommended.
4. **Forward gain `0xC6CD0`** — multiplies P, D and I identically, so it raises breakaway and loop
   gain **1:1**. Not free; it spends the ring gate at the same rate it buys torque. Closed.

⇒ **PLAIN ANSWER, as requested:** *within Ki = 0 and cal-only, the only lever that reaches stiction
is the MAP, and its benefit would not register on the metric that currently defines the symptom.
Every other route is either already-rejected (the Kp shape), gated behind a code edit (the
feedforward), or self-cancelling (the forward gain). Integral action is the only term in this
firmware that both produces DC and is free to grow against a stalled wheel.* That is the decision to
put to the operator, not a gap in the analysis.

## II.7 REVISED RECOMMENDATION

**Part I recommended `Kp 148 / Kd 128`. Under the actuator spec I withdraw it in favour of a Kd
raise at Kp 248** — `Kd 160` (candidate F, GM 1.48×, ring peak 11.0) or `Kd 192` (GM 1.27×, ring
peak 6.5), with **`Kd 160` the defensible first step** because it keeps GM above 3 dB.

| | Part I basis (loop gain) | Part II basis (actuator fidelity) |
|---|---|---|
| objective | minimise `\|L(7.3)\|`, maximise GM | `\|T(0)\|→1`, no peaking, linearity |
| DC authority | cheap, then a currency | **a fidelity DEFECT — Kp cuts make it worse** |
| winner | Kp 148 / Kd 128 | **Kd 160–192 at Kp 248** |
| currency spent | DC authority + deadband | **blind-band GM only** |

**What does NOT change between the two framings:** `Kp = 0` is dead · the no-overshoot ZN family is
below the ring root and re-arms the cycle · the ring root moves with Kp (§1.4) · a Kd raise moves
*away* from that root · the deadband needs DC, and only P or I supply it.

⚠ **Pre-registration transfer.** Endpoints (A) ring decay, (C) blind-band **energy**, and (E) arm
split from Part I §5 transfer unchanged to a Kd-raise build. **(B) must be REWRITTEN** — a Kd raise
does not move `|T(0)|`, so DC tracking cannot serve as the attribution endpoint; attribute instead
from the 427 tap's `|D|/|P|` ratio in ringing frames, which scales directly and only with Kd
(measured today: 0.294 in stalls, 0.296 in moving runs ⇒ predicted 0.441 at Kd 192, 0.368 at
Kd 160). **(D) becomes a NULL prediction**: the deadband should be **unchanged at 7 runs**, and any
worsening falsifies §II.6's measurement.
🛑 **A Kd raise spends blind-band margin (1.77× → 1.48× at Kd 160, → 1.27× at Kd 192) at a frequency
no instrument on the car can see.** The energy endpoint (C) is the only guard, and note that V286's
ladder was designed to bound the floor a Kd *cut* approaches — **it does not bound the ceiling a
raise approaches.** That asymmetry (V286 spec §0c) still holds and still favours the raise, but it
means the ladder is not the instrument that clears this build; endpoint (C) is.

## II.8 WHAT I COULD NOT COMPUTE, and what would make it computable

**Not computable from measured data, and I decline to manufacture it:**
- **a full closed-loop `|T(f)|` curve** — §II.0: the two models disagree, and the ring lives in a
  lane the Nyquist model's forward path does not contain.
- **`f_-3dB` (closed-loop bandwidth)** — needs the plant **magnitude** above ~5 Hz. The record
  measures the plant's *phase* (−28° @10 Hz, −73° @22 Hz) and its DC gain, never its magnitude in
  between. Any `f_-3dB` I printed would be an artefact of assuming flat.
- **`max|T|` over 0–50 Hz** — the 20 Hz creep line has **no measured `|L|` at all**
  (`CREEP-20HZ` item 7(a): `L_in(line) = −1` by construction at a spectral line), so its peak height
  is unquantified in both directions. **The fidelity spec's "no peaking anywhere" therefore cannot
  be scored at 20 Hz today, in either direction.**

**What would fix all three:** a **plant magnitude identification** — a broadband or swept excitation
with the 427 `T` tap and the `0x18F` rate read simultaneously. That is a *drive design*, not a
build, and it is the single measurement that would turn this whole framework from **composed** to
**identified**. Given that §II.2's entire ranking rests on a composition rule the record has already
seen self-refute once, I would rank that drive above any further sizing work.

---
---

# PART III — the mechanism corrected, the `s` threat priced, and r39. **Net: I now recommend NO cal change yet.**

Subagent `znback`, 2026-09-04, third pass. Code: `analysis-2020accord/studies/pidframe/zn_arm_geometry.py`,
`rlog-tools/studies/osc-highangle/stall_kp_counterfactual_r39.py`.

---

> 🛑 **POINTERS ADDED 2026-09-04 (fourth pass).**
> * The **convention defect** first flagged in Part II §II.0 is now written up standalone and
>   greppable: **`docs/research/LOOP-MODEL-CONVENTION-DEFECT-2026-09-04.md`**. It also carries a
>   second reading trap (`CREEP-20HZ` §1.4's `GM = none` rows are mostly a 2–24 Hz WINDOW artefact,
>   not a null) that bears directly on §III.6's Kd choice.
> * **Part I §1.4's stated mechanism is WRONG and is superseded by §III.1 below.** The number
>   (root 116.7 at Kp 248, 84.9 at Kp 148) survives; the explanation next to it did not.
> * **Part II's recommendation (Kd raise) is conditional on the r24 arm magnitude** — see §III.2.
>   Under a 3–5× smaller r24 arm it INVERTS to a do-not-flash.

## III.1 🛑 THE MECHANISM — my prose was wrong on BOTH clauses. Corrected from the numbers.

`team-lead` is right that *"sits further from anti-phase and cancels less — the sum shrinks"* cannot
be true as written. Here is what the numbers actually say, at 7.3 Hz, Kd held at 128.
`Ls` includes the plant (`= Ls_base × R`, `R = C(f₀,Kp,Kd)/C(f₀,248,128)`; everything else cancels).

| Kp | `Lr` (fixed) | `Ls` (with plant) | angle Ls−Lr | `\|Ls+Lr\|` | **ALONG Lr** | **QUADRATURE** |
|---|---|---|---|---|---|---|
| **248** | 1.190 ∠−27.0° | 0.550 ∠+96.0° | **123.0°** | **1.0028** | **−0.2996** | **0.4613** |
| 200 | 1.190 ∠−27.0° | 0.485 ∠+101.9° | 128.9° | 0.9622 | −0.3049 | 0.3775 |
| 176 | 1.190 ∠−27.0° | 0.455 ∠+105.5° | 132.5° | 0.9441 | −0.3076 | 0.3356 |
| **148** | 1.190 ∠−27.0° | **0.423 ∠+110.3°** | **137.3°** | **0.9249** | **−0.3107** | **0.2868** |
| 100 | 1.190 ∠−27.0° | 0.376 ∠+120.3° | 147.3° | 0.8972 | −0.3161 | 0.2030 |

Identity check: `|Ls+Lr|² = (|Lr| + ALONG)² + QUADRATURE²` — reproduces 1.0028 at Kp 248. And since
`|Lr| = 1.19 > |Ls+Lr| = 1.0028`, **the servo arm is unambiguously doing net cancellation today**, as
`team-lead` deduced.

**WHAT I GOT WRONG:**
- *"further from anti-phase"* — **FALSE.** The angle goes 123.0° → 137.3°, i.e. **CLOSER** to 180°.
- *"cancels less"* — **FALSE.** The along-`Lr` (cancelling) component **grows** slightly,
  −0.2996 → −0.3107 (**+3.7 %**), because the rotation more than compensates the 23 % shrink in `|Ls|`.

**THE CORRECTED MECHANISM, in one sentence:** *lowering Kp rotates the servo arm toward the D term's
+88.7°, which moves it closer to anti-phase with the fixed r24 arm; the cancelling component is
essentially preserved while the **QUADRATURE component collapses (0.461 → 0.287, −38 %)**, and it is
the quadrature — which adds in RMS and cannot be cancelled — that was inflating the sum.*
**The servo arm becomes a PURER canceller, not a weaker one.** [EVIDENCE — byte-exact `C`, and the
identity above closes.]

**And why the root falls with Kp** (same decomposition, sweeping Kd):

| Kp 248 (root Kd 116.7) | Kd 160 | Kd 128 | **Kd 117** | Kd 80 |
|---|---|---|---|---|
| ∠Ls | +102.2° | +96.0° | **+93.6°** | +84.4° |
| ALONG | −0.3814 | −0.2996 | **−0.2714** | −0.1768 |
| `\|Ls+Lr\|` | 0.9345 | 1.0028 | **1.0268** | 1.1088 |

| Kp 148 (root Kd 84.9) | Kd 160 | Kd 128 | **Kd 85** | Kd 60 |
|---|---|---|---|---|
| ∠Ls | +116.2° | +110.3° | **+98.9°** | +89.7° |
| ALONG | −0.3925 | −0.3107 | **−0.2008** | −0.1369 |
| `\|Ls+Lr\|` | 0.8499 | 0.9249 | **1.0273** | 1.0876 |

**Cutting Kd rotates `Ls` back toward P, collapsing the along-`Lr` cancellation until the sum reaches
1.** At a lower Kp the same Kd leaves `C` more D-dominated (`|D|/|P| = 33.03·sin(πfT)/(Kp/256)`), so
the arm stays rotated further out — **you must cut Kd further before the cancellation collapses.**
Both roots sit at `|Ls+Lr| ≈ 1.027`, as they must. **The numeric root-find and the corrected
mechanism now agree**, so the root-find does not need to be distrusted — but the *explanation* in
Part I §1.4 must be replaced with the paragraph above.

## III.2 🛑🛑 THE `s` THREAT, PRICED PROPERLY — and it REVERSES the Kd recommendation

`team-lead` was right that my renormalisation hid the threat. But the naive alternative is also
wrong, and the right test is stronger than either.

**(a) Naive (scale `Lr`, leave `Ls` at 0.55) is REFUTED BY THE MEASUREMENT:** it predicts
`|L_today| = 0.46` at a 3× smaller r24, against a measured **0.976**. Not an admissible sensitivity.

**(b) The correct test — and there is NO free parameter.** A self-sustained ring requires
`Ls + Lr ≈ +1` (magnitude ~1 **and phase ~0**); the published arms give exactly
`Ls + Lr = 1.0028 ∠+0.38°`. **Fix that complex sum, fix `Lr`'s phase at −27°, scale `|Lr|` — then
`Ls = SUM − Lr` is FULLY DETERMINED.** Not renormalised, not chosen: forced.

| `Lr` scale | `\|Lr\|` | **`Ls` = SUM − Lr** | angle Ls−Lr | `\|L\|` **148/128** | `\|L\|` **248/160** | `\|L\|` **248/192** |
|---|---|---|---|---|---|---|
| **1.000 (as modelled)** | 1.190 | **0.550 ∠+96.0°** | 123.0° | **0.900** | **0.909** | **0.845** |
| 0.800 | 0.952 | 0.465 ∠+70.6° | 97.6° | 0.860 | 0.942 | 0.911 |
| 0.600 | 0.714 | 0.494 ∠+42.1° | 69.1° | 0.824 | 0.974 | 0.977 |
| **0.333 (grind39 branch)** | 0.397 | **0.676 ∠+16.1°** | 43.1° | **0.784** | 🛑 **1.017** | 🛑 **1.066** |
| 0.250 | 0.297 | 0.751 ∠+10.9° | 37.9° | 0.774 | 🛑 **1.031** | 🛑 **1.094** |
| **0.200** | 0.238 | 0.799 ∠+8.3° | 35.3° | **0.769** | 🛑 **1.039** | 🛑 **1.111** |

🛑 **THIS IS THE ANSWER TO YOUR QUESTION, AND IT IS NOT A SMALL SHIFT — IT INVERTS THE Kd AXIS.**

- If the r24 arm is **3–5× smaller**, the servo arm's phase is forced from **+96° to +8…+16°**. The
  two arms stop being anti-phased (123° apart) and become **nearly co-phased (35–43°)**. The servo
  arm is then **not a canceller at all** — it is the dominant contributor, exactly as `grind39`'s
  branch says (*"the servo is the 7 Hz pump after all"*).
- ⇒ **A Kd RAISE becomes a DO-NOT-FLASH.** `|L(7.3)|` at Kd 160 goes 0.909 → **1.017–1.039**, and at
  Kd 192 → **1.066–1.111**. **Both re-arm the ring.** Candidate F and my own Part II recommendation
  invert from "best available" to "drives the cycle unstable".
- ⭐ **The Kp CUT is ROBUST across the entire range**: `|L| 148/128` goes 0.900 → 0.769, i.e. it stays
  well below 1 and **gets BETTER as the r24 arm shrinks**, because it attacks the arm that dominates
  in that regime.

⇒ **The `s` uncertainty does not merely widen an interval — it flips the SIGN of the Kd
recommendation while leaving the Kp direction intact.** [EVIDENCE for the arithmetic and the
forcing; the input `Lr` scale is `grind39`'s to settle.] 🛑 **Do not cut a Kd-raise build until
`grind39` reports.**

⚠ Two honest caveats on this test: it holds `Lr`'s **phase** fixed at −27° (only its magnitude is
`grind39`'s finding — if the phase moves too, redo it), and Part I §1.4's *"root falls with Kp"*
claim is stated in the baseline regime; in the inverted regime the `|L|`-vs-Kd curve is no longer
the same V and "the lower root" is not the same object. **The corrected mechanism (III.1) is
`s`-independent — it is controller geometry — but which arm it acts on is not.**

## III.3 THE FIDELITY TABLE YOU ASKED FOR — and **`max|T|` DOES rank differently**

| candidate | Kp | Kd | `\|T(0)\|` | **max\|T\| (smooth)** | at f | `f_-3dB` | ph 1 Hz | ph 2 Hz | ph 3 Hz | **measured ring peak** |
|---|---|---|---|---|---|---|---|---|---|---|
| **today** | 248 | 128 | 0.535 | **1.447** | 25.0 Hz | 41.2 Hz | −4.76° | −8.93° | −13.04° | **41.7 (1.00×)** |
| 200/128 | 200 | 128 | 0.481 | 1.302 | 25.6 Hz | 42.6 Hz | −4.91° | −9.13° | −13.25° | 15.7 (0.38×) |
| 176/128 | 176 | 128 | 0.450 | 1.242 | 26.0 Hz | 43.6 Hz | −4.89° | −9.02° | −13.05° | 12.3 (0.30×) |
| **148/128** | 148 | 128 | 0.407 | **1.181** | 26.4 Hz | 45.2 Hz | −4.67° | −8.54° | −12.34° | 10.0 (0.24×) |
| **ZN-PI** | 148 | 122 | 0.407 | ⭐ **1.090** | 26.0 Hz | 44.2 Hz | −4.88° | −8.95° | −12.93° | 11.6 (0.28×) |
| **F** | 248 | **160** | 0.535 | 🛑 **2.247** | 27.0 Hz | 45.3 Hz | −4.26° | −7.91° | −11.48° | 11.0 (0.27×) |
| **248/192** | 248 | **192** | 0.535 | 🛑 **3.958** | 28.4 Hz | 48.5 Hz | −3.76° | −6.92° | −10.00° | **6.5 (0.16×)** |

🛑 **TWO DIFFERENT OBJECTS, LABELLED.** `max|T|` (smooth) is the byte-exact `C × lag × fb ×` measured
plant phase, closed. It contains **no plant resonance**, so it captures the **broadband peak near the
−180° crossing** and *not* the 7.3 Hz ring. The last column is the separately-anchored measured ring.
**The 20 Hz mode is in neither** — it has no measured `|L|`.

⭐ **YES, `max|T|` RANKS THE CANDIDATES DIFFERENTLY FROM `|L(7.3)|` — and it reverses the Part II
ranking.** The Kd raise removes the 7.3 Hz peak by **creating a new one at 25–28 Hz**: max|T| goes
1.447 → **2.247** at Kd 160 and → **3.958** at Kd 192. That is exactly `1/GM` behaviour (GM 1.77× →
1.48× → 1.27×) showing up in the closed-loop transfer. **Kp cuts do the opposite** — they raise GM,
so max|T| falls to 1.18, and **ZN-PI 148/122 is the flattest candidate on the table at 1.090.**

⇒ **On the operator's criterion 2 taken literally — "no peaking ANYWHERE, max|T| as close to 1.0 as
achievable" — the Kd raise is DISQUALIFIED and the Kp cut wins.** This is the single most useful
column you asked for and it does not agree with Part II.
⚠ The new peak is at **25–28 Hz, in the blind band**. Per V286 §0b an **energy** endpoint can see it;
a frequency one cannot. So it is catchable — but only if pre-registered.
*(`f_-3dB` and `max|T|`'s location both inherit the flat-plant-magnitude assumption above ~5 Hz — see
Part II §II.8. Treat the ORDERING as sound and the absolute frequencies as model-dependent.)*

## III.4 🛑 r39 DEADBAND — the cost is BIGGER than I priced, and **the worst run DOES deepen**

r39's cache is a different schema (91 fields, no `ref`, no demand `idx`), so I used **`dec39`'s own
ref-free window definition** verbatim. Baseline **reproduces 17 windows** at Kp 248. ✅

| Kp | k | rate thr | **windows** | total | **LONGEST** | mean |
|---|---|---|---|---|---|---|
| **248 (as flown)** | 1.000 | 2.00 | **17** | 13.5 s | **1.85 s** | 0.80 s |
| 200 | 0.806 | 2.48 | 21 (1.24×) | 18.5 s | 2.69 s | 0.88 s |
| 176 | 0.710 | 2.82 | 27 (1.59×) | 24.4 s | 2.69 s | 0.90 s |
| **148** | 0.597 | 3.35 | **32 (1.88×)** | **31.2 s** | **2.70 s** | 0.97 s |
| 128 | 0.516 | 3.88 | 35 (2.06×) | 35.9 s | 2.95 s | 1.03 s |
| 100 | 0.403 | 4.96 | 58 (3.41×) | 56.5 s | 3.02 s | 0.97 s |

🛑 **THE r35 FINDING DOES NOT HOLD AT r39's OPERATING POINT.** On r35 the cut added marginal runs and
left the worst at 3.4 s. On r39 the worst run goes **1.85 s → 2.70 s, +46 %**, and the window count
rises **1.88×** (against r35's 1.29×) with total stalled time **2.3×**. **Q3's cost is roughly twice
what I priced it at, and it is now the deeper kind of failure you were worried about.**

⚠ Method note: my Kp-248 baseline reproduces `dec39`'s **17 windows** exactly but gives a longest run
of **1.85 s** against `dec39`'s **2.69 s** — probably a different run-merging or sign-split rule.
**The counterfactual DELTAS are computed self-consistently within my own detector**, so the +46 % is
sound; the absolute longest-run value should be taken from `dec39`.

## III.5 FRAMING CORRECTION — applied

🛑 **STRUCK from Part I §3:** the conclusion *"Kp is the oversteer lever; Kd is not"* and the sizing
note reasoning about clawing back his 1.70×. **Over-steer is the outer loop's, per the operator.**
The 0.82× / 0.76× outer-loop gain numbers stand as **a consequence to be COMPENSATED by `over39` on
the openpilot side, not a reason to make the edit.**

**Re-scored on the ring alone, with DC gain in the COST column** — does Kp 148 still win? **No, and
neither does anything else cleanly.** Against today it buys ring 1.000 → 0.922; it pays 53.5 % →
40.7 % `|T(0)|` (a 1.87× → **2.46×** scale error), **32 vs 17 r39 stall windows with a 46 % deeper
worst run**, and 76.3 % of outer-integrator bound. **Kp 176 is the shallower point** (ring 0.941,
`|T(0)|` 0.450, max|T| 1.242, GM 1.89×, 27 windows) but it is the same trade at 60 % scale, not a
different trade.

## III.6 🛑 REVISED RECOMMENDATION — **NO CAL CHANGE YET. This pass returns "do not cut a build."**

Four axes, and **no candidate wins on all of them**:

| | ring @7.3 (as modelled) | ring if r24 is 3–5× smaller | `max\|T\|` (total peaking) | `\|T(0)\|` | r39 deadband |
|---|---|---|---|---|---|
| **today 248/128** | 41.7 | — | 1.447 | 0.535 | 17 windows |
| **Kp 148 / Kd 128** | ✅ 10.0 | ✅ **0.784 — better still** | ✅ **1.181** | 🛑 0.407 | 🛑 **32, worst +46 %** |
| **Kd 160 (F)** | ✅ 11.0 | 🛑 **1.017 — RE-ARMS** | 🛑 2.247 | ✅ 0.535 | ✅ 17 |
| **Kd 192** | ✅ 6.5 | 🛑 **1.066 — RE-ARMS** | 🛑 **3.958** | ✅ 0.535 | ✅ 17 |

**The Kd raise wins on one axis and fails on three. The Kp cut wins on three and fails on one — but
the one it fails is the deadband, which is a symptom the operator has already felt and named.**

⇒ **My recommendation is to cut NOTHING until `grind39` settles the r24 arm magnitude.** That single
number decides the SIGN of the Kd axis, and it is being measured now. Cutting a Kd-raise build before
it lands risks flashing an image that **re-arms the 7 Hz cycle** — the exact symptom V281 rev 3
finally removed.

**If a build must be cut before `grind39` reports**, the least-regret option is **Kp 176 / Kd 128 /
Ki 0**: it improves the ring under *both* arm hypotheses (0.941 modelled, ~0.83 inverted), improves
total peaking (1.447 → 1.242), improves GM (1.77× → 1.89×), sits at 69 % of outer-integrator bound,
and costs 27 vs 17 r39 windows — **about half the deadband cost of Kp 148 for two-thirds of the ring
benefit.** I would still rather wait.

**What I would do INSTEAD of any cal build, and rank above it:** the **plant-magnitude
identification** drive from Part II §II.8. Three of the four axes above are model-composed rather
than measured, the composition rule has already self-refuted once in this record, and the `s`
sensitivity in III.2 shows the whole Kd axis hanging on one unmeasured magnitude. **Measuring the
plant would retire more risk than any dose.**

---
---

# PART IV — 🛑 THE MEASUREMENT LANDED IN THE INVERTED BRANCH. Outcome: no firmware this session.

Subagent `znback`, 2026-09-04, fourth pass. **This section closes the file's open question: the r24
arm magnitude has been measured, it landed where Part III said the Kd axis inverts, and the
conclusion is "cut nothing", not "choose between Kd 160 and 192."**

---

## IV.1 THE MEASUREMENT — `grind39`'s renormalised ladder on r39's own `|T|`

Engaged / hands-off / creep 1–3 m/s stratum, `n = 5,916`. **[`team-lead`'s direct read of `grind39`'s
output; that agent's formal adjudication was still pending at the time of writing — treat the
attribution accordingly, not the arithmetic below, which is mine.]**

| `0xC6446` arm | predicted bit-6 duty | `\|r24\|` p50 | `\|T\|` p50 |
|---|---|---|---|
| **5244 (flown, engaged)** | 0.1957 | 36 | 160 |
| 2048 (stock) | 0.0784 | 12 | 160 |
| 1024 (fault) | 0.0387 | 4 | 160 |
| | **OBSERVED: 0.0908** | | |

The renormalisation did real work on its own — the flown arm's prediction fell from the
pre-registration's 0.300 to 0.196, so much of the apparent shortfall was `|T|` growing (r39 p50 71 vs
r34/r35's 55 on the tighter stratum). **But 0.0908 is still well below the flown arm's renormalised
0.1957**, putting the effective arm between the 2048 and 5244 rungs.

⚠ **Two defensible readings of "how much smaller", and I report both rather than picking one:**
- **duty ratio** `0.0908 / 0.1957` = **0.464**
- **magnitude interpolation** between the rungs: `(0.0908−0.0784)/(0.1957−0.0784) = 0.106`, so
  `|r24| ≈ 12 + 0.106×(36−12) = 14.5` against the flown 36 ⇒ scale **0.40**

**Duty is a CDF crossing, so it is NOT linear in magnitude** and the true scale is not pinned by
either. **I therefore report the whole band 0.40–0.50, and the conclusion is the same across all of
it.**

## IV.2 THE EXACT FIGURES — `team-lead`'s interpolation CONFIRMED

Forced-geometry model (`Ls + Lr` held at the measured `1.0028 ∠+0.38°`, `Lr` phase fixed, `|Lr|`
scaled, `Ls = SUM − Lr` forced — no free parameter). **`team-lead`'s linear guess of "≈0.99–1.00 at
Kd 160" was right; the exact values:**

| `Lr` scale | `\|Lr\|` | `Ls` forced | angle apart | **Kd 128 (today)** | **Kd 160** | Kd 176 | **Kd 192** | Kp 148/Kd 128 |
|---|---|---|---|---|---|---|---|---|
| 1.000 (as modelled) | 1.190 | 0.550 ∠+96.0° | 123.0° | 0.976 | **0.909** | 0.877 | **0.845** | 0.900 |
| 0.700 | 0.833 | 0.465 ∠+55.9° | 82.9° | 0.976 | 0.958 | 0.950 | 0.944 | 0.841 |
| 0.600 | 0.714 | 0.494 ∠+42.1° | 69.1° | 0.976 | 0.974 | 0.975 | 0.977 | 0.824 |
| **0.500** | 0.595 | 0.548 ∠+30.4° | 57.4° | 0.976 | **0.990** | 1.000 | 🛑 **1.011** | 0.808 |
| **0.460** | 0.547 | 0.575 ∠+26.4° | 53.4° | 0.976 | **0.997** | 🛑 1.010 | 🛑 **1.024** | 0.802 |
| **0.440** | 0.524 | 0.589 ∠+24.5° | 51.5° | 0.976 | 🛑 **1.000** | 🛑 1.014 | 🛑 **1.031** | 0.799 |
| **0.400** | 0.476 | 0.620 ∠+21.1° | 48.1° | 0.976 | 🛑 **1.006** | 🛑 1.024 | 🛑 **1.044** | 0.793 |
| 0.333 | 0.396 | 0.676 ∠+16.0° | 43.0° | 0.976 | 🛑 1.017 | 🛑 1.041 | 🛑 1.066 | 0.784 |

**Across the measured band 0.40–0.50: Kd 160 gives `|L(7.3)| = 0.990 … 1.006` and Kd 192 gives
`1.011 … 1.044`.** Kd 160 buys **at most 2 %** of ring benefit and at scale ≤ 0.44 buys **nothing or
worse**; Kd 192 is **above unity everywhere in the band**. ⇒ **Both are dead or marginal. The Kd-raise
recommendation is withdrawn, and `team-lead`'s decision to treat the Kd axis as closed is correct.**

## IV.3 ⭐ THE LARGER FINDING — at the measured arm scale, **Kd has almost no authority over the ring at all**

Minimising `|L(7.3)|` over the whole usable Kd range at each arm scale:

| `Lr` scale | **best Kd** | `\|L\|` at that Kd | `\|L\|` at today's Kd 128 | **total authority of the Kd axis** |
|---|---|---|---|---|
| 1.000 (as modelled) | **260** | **0.719** | 0.976 | **26 %** |
| 0.600 | 156 | 0.974 | 0.976 | 0.2 % |
| **0.500** | **73** | **0.966** | 0.976 | **1.0 %** |
| **0.460** | **50** | **0.955** | 0.976 | **2.1 %** |
| 0.400 | 40 | 0.933 | 0.976 | 4.4 % |

🛑 **The Kd optimum does not merely move — it COLLAPSES from 260 to 40–73, i.e. from a large RAISE to
a large CUT, and the whole axis flattens.** At the measured arm scale the best Kd anywhere is worth
**1–2 %** on the ring, against **26 %** under the modelled arm. **Kd is not a weak lever at the
measured operating point; it is essentially not a lever.**

*(I am **not** recommending Kd 50–73. It would gut the lead that cancels the 5.05 Hz output-lag pole,
it is far outside anything flown, and the 1–2 % it buys is inside every uncertainty in this
framework. I report it because it is the model's own answer and because it is the cleanest possible
statement that the Kd axis is closed.)*

⭐ **By contrast the Kp axis strengthens as the arm shrinks**: `|L(7.3)|` at Kp 148/Kd 128 goes
**0.900 → 0.802** across the band — because a Kp cut attacks the servo arm, which is precisely the
arm that dominates once r24 is small. **Kp remains the only cell with real authority over the
7.3 Hz ring.** But — see Part III §III.4 — the Kp cut's own cost got worse at the same time
(r39: 17 → 32 stall windows, worst run +46 %), which is why **nothing is being cut this session.**

## IV.4 WHAT THIS FILE NOW CONCLUDES

| axis | verdict |
|---|---|
| **Kd raise (160 / 192)** | 🛑 **DEAD** — `\|L(7.3)\|` = 0.990–1.044 at the measured arm; buys ≤ 2 % or re-arms. Also nearly quadruples `max\|T\|` (Part III §III.3) and spends blind-band margin quoted from the worst estimator family (§III.5 / the convention-defect note). |
| **Kd cut** | not recommended — the model's optimum (50–73) is worth 1–2 %, far outside anything flown, and would remove the lead that cancels the 5.05 Hz lag pole. |
| **Kp cut (148)** | the only lever with real ring authority (0.976 → 0.802), and it *improves* as the arm shrinks — **but** its r39 deadband cost is ~2× what Part I priced (17 → 32 windows, worst run 1.85 → 2.70 s). **Not cut this session.** |
| **Kp = 0** | dead, three independent reasons (Part II §II.5). |
| **ZN as a recipe** | rejected structurally (Part II §II.3) — it is a regulator recipe and it points the wrong way on Kd. |
| **the whole no-overshoot ZN family** | below the ring root, re-arms the cycle (Part I §2). |
| ⭐ **what to do instead** | the **plant-magnitude identification drive** (Part II §II.8). Every axis above is model-composed; this session's own arithmetic has now inverted twice on one unmeasured magnitude. |

**OUTCOME: no firmware this session.** That is the correct output of an analysis whose load-bearing
input was measured mid-session and landed against the candidate.
