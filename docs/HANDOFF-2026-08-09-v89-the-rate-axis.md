# HANDOFF 2026-08-09 — V89 analysis session: the operator gave the symptoms an axis, and it is WHEEL RATE

**Session shape:** orchestrator working hands-on (no subagents spawned this session).
🛑 **§§3 and 7 were WRITTEN, THEN OVERTURNED WITHIN THE SESSION** by the operator catching a loader bug. **Read §12 FIRST** — it supersedes them.
**Deliverables:** the operator's symptom axis tested on existing logs · two of this session's own
readings retracted by their own controls · the base-assist damper closed as a micro-ratcheting lever
on arithmetic · the Lever-B discriminator run and found underpowered · **no build cut, deliberately**
· `STATE.md` cut 494.7 KB → 88.1 KB with a size cap written into `CLAUDE.md`.

---

## 1. What the operator asked

> *"Let's work towards a firmware which enables 4x LKAS torque without all the current bad
> side-effects. We just need to eliminate micro-ratcheting and ratcheting when LKAS is engaged and
> spinning the wheel at all (micro-ratcheting) and quickly (ratcheting), respectively. Note about
> macro-ratcheting is it's on large steering angle transients."*
>
> *"Also shrink the STATE file so it's readable in its entirety (and up-to-date) before the end of
> this session… less than 256 kB. Make sure to note this in CLAUDE.md so this doesn't happen again."*

Both addressed. The second is done and verified. The first produced a **measurement and three
kills, not a build** — and the reason is in §6.

---

## 2. ★★★★★ The new input is an AXIS, and the corpus had never used it

Every ratchet measurement in this kit has been stratified by **vehicle speed**. The operator's own
separator is **steering-wheel rate**: *at all* vs *quickly*, with macro on *large angle transients*.

In this corpus those two axes are strongly anti-correlated — **corr(log |rate|, log speed) = −0.640**
on engaged windows. You spin the wheel in a car park, not at 116 km/h.

⇒ **The V88 handoff's D5 headline — "the ratchet's amplitude decays 4.8× from creep to highway" —
is partly a RATE effect read as a SPEED effect.** Its creep stratum has a median |rate| of
**13 deg/s**; its highway stratum, **1 deg/s**. On the same route, with an order veto and a purity
screen, the creep→highway ratio falls to **2.27×**, and most of what remains sits between the
40–80 and >80 km/h strata.

🛑 This does **not** overturn D5's *frequency* result. `f0 = +0.0102·v + 7.998 Hz` against wheel
order 1's 0.4807 stands — **speed-invariance of the frequency is untouched.** What is re-attributed
is the **amplitude** trend.

---

## 3. ★★★★ What survived every control: the engagement × rate interaction

`analysis-2020accord/v89_a5_engagement_model.py`. 400 windows, 12 routes, 93 episode blocks.

```
log e_band  ~  route + eng + eng x log|rate| + log|rate| + log v + log hands
```

| term | 6–9 Hz (ratchet) | 32–38 Hz (control) | contrast |
|---|---|---|---|
| `eng` | +0.869 [+0.295, +1.369] | +0.523 [+0.246, +0.750] | +0.346 [−0.050, +0.695] — includes 0 |
| **`eng × log rate`** | **+0.313 [+0.103, +0.490]** | +0.168 [+0.064, +0.260] | **+0.144 [−0.004, +0.267] — includes 0 by a hair** |
| **`log hands`** | **−0.720 [−0.918, −0.500]** | −0.216 [−0.326, −0.104] | **DISJOINT — band-specific** |

**[EVIDENCE] Engagement's amplification of the 6–9 Hz column mode grows with wheel rate.**
Engaged/manual runs **1.16× at 2 deg/s → 1.92× at 10 → 3.94× [2.19, 6.70] at 100 deg/s**.
🛑 **[BELIEF] That it is RATCHET-SPECIFIC.** The control band does the same at ~half the rate and the
contrast's lower bound is **−0.004** — suggestive, **not** established.
🛑 **This number changed mid-session.** With `_cache_r66`/`_cache_r66x` double-counting route `66` it
read +0.172 [+0.038, +0.288] and excluded 0. **Deduped (§10.1), it does not.** The duplicate was found
while writing §7's discriminator, and the headline was corrected rather than shipped.

**That is the operator's micro → ratcheting progression, measured for the first time.** It is the
first instrument in this kit that responds to his distinction at all.

★ **And a second result, which is the session's most solid:** `d(log e_6-9)/d(log sustained column
torque)` = **−0.720 [−0.918, −0.500]** against the control band's **−0.216 [−0.326, −0.104]** —
**CIs DISJOINT.** **The mode is strongly damped by driver grip, band-specifically.** A firmware lever that
adds damping at the column at 6–9 Hz is emulating what the operator's own hands already do — which
is both an encouragement and the reason §5's sizing matters.

⚠ **Honest scope.** The effect is real but **modest**, and weakest at the *micro* end (1.16× at
2 deg/s). n = 400 after screening and deduping; the engaged and manual arms overlap only partially in `hands`
(p50 193 vs 2005) and in `|rate|` (p50 16 vs 53). **The interaction is EVIDENCE; any mechanism
attached to it is BELIEF.**

---

## 4. 🛑🛑 Two of this session's own readings, retracted by their own controls

Recorded as retractions because both were persuasive and both would have shipped.

**(a) "The rate axis is band-specific to the ratchet."** `v89_a1` returned `e_6-9` slope **+0.490**
against `e_18-22` **+0.039** — a clean, headline-shaped separation matching the phenomenology
(grinding is fixed; ratcheting is not). **It was an artefact of order-vetoing each band on a
DIFFERENT window set.** On matched windows (`v89_a2` T2) the three slopes are **+0.492 / +0.385 /
+0.400** and the contrast CI **includes 0**.
⇒ **Spinning the wheel raises the WHOLE column spectrum.** A rate slope can never, by itself,
separate firmware from driver. Only the engaged-vs-manual **interaction** in §3 does.

**(b) The binned engaged/manual dose curve, 2.09× → 21.17×** (`v89_a4`). Inflated by two confounds
its own controls caught:
- **K2 (load).** At 8–50 deg/s the MANUAL arm carries **~9× the sustained column load** (1724–1878
  counts vs 193–201) — it is slower, heavier parking. A hard-gripped wheel is damped by arm
  impedance, and §3's −0.720 says exactly how much. **The one rate bin where the arms *are*
  load-matched (50+ deg/s) is the bin where the effect collapses, to 1.76×.**
- **K4 (route).** Only 5 routes contribute any cell and they contribute to **different bins**, so a
  build effect masquerades as a rate trend.

🛑 **Quote §3's model numbers (1.16× → 3.94×). Never the 21×.**

---

## 5. 🛑 `cmd → column` coherence is not an attribution instrument

Attempted as `v89_a3` (STATE's recommended analysis #1/#3) and **dropped, with the reason recorded.**

`gp-0x6b98` is the **total motor command, base assist included**, and base assist is a function of
column torque. Its 6–9 Hz coherence with the column is **0.254 engaged** but **0.544 MANUAL**, where
the LKAS command is identically absent. That is **loop feedthrough, not attribution.**

The road channels — `imu_vert`, `imu_lat`, wheel-speed roughness — sit **at their shuffled-pairs
controls in the engaged arm** (0.079 / 0.066 / 0.088 against p95 controls of 0.144 / 0.144 / 0.183),
so the road-excitation hypothesis gets no support here either, but the instrument is too weak to
carry a negative.

⚠ This also bounds the V88 handoff's §5 coherence table. Its scoring agent already said the honest
carrier was the prominence contrast (52 % vs 13.3 %), not the coherence — **that caveat is now the
main statement.**

⊕ `v89_a3`'s E3/E4 (Q from peak shape, envelope cross-correlation) starved on window screens and
returned nothing usable. Recorded so the next session does not re-run them unchanged.

---

## 6. 🛑🛑 The base-assist damper is CLOSED as a micro-ratcheting lever — on arithmetic, not on a null

`analysis-2020accord/v89_b1_damper_surface.py`, read from V88's own image.

```
ch0 = clamp( (FactorC(speed) * FactorE(rate)) >> 10 , +/- ceiling )        [gp-0x6bd0]

FactorC  X=[2240,3840,5120,8960] ct = [35, 60, 80, 140] km/h   Y=[0,234,429,908]
FactorE  X=[  60, 400,2500,4000] ct = [12.7,84.9,530,849] deg/s Y=[0,140,539,927]
```
Mode 24 ≡ 26 and 25 ≡ 27, byte-identical on V88. **Two MULTIPLICATIVE dead zones**, and against
route 73's measured engaged distribution the damper contributes **exactly zero on 95.91 % of engaged
frames** — including **100.0 %** of the operator's micro-ratcheting regime (229 s at |rate|
1–13 deg/s) and **100.0 %** of his ratcheting regime at parking-lot speed (131 s).

### ★ Neither prior test ever had both zones open — a RULE-5 failure against a *product*
- The **`FactorE X[0]` lever was withdrawn as *"structurally vacuous"*** — correct, but only
  *because FactorC was 0 at creep.*
- **`FactorC Y[0]` WAS tested**, as **V86B on route 70**, lifted to the record's own `Y[3]`
  (908 / 875) — but **FactorE stayed 0 below 12.7 deg/s.** So V86B armed the damper only for
  *spinning quickly*, **never for spinning at all.** Operator on V86B: *"extra dampening on LKAS and
  in general at slow speed"* — the **cost** was felt while the **micro regime was never armed.**

### 🛑 But sizing kills it anyway, and that is why no build was cut
With FactorC `Y[0]` lifted **and** `FactorE X[0]` 60→12, `ch₀` at creep reads:

| |rate| deg/s | 2 | 5 | 10 | 20 | 40 | 80 |
|---|---|---|---|---|---|---|---|
| V88 (Honda) | 0 | 0 | 0 | 0 | 0 | 0 |
| V86B (FactorC `Y[0]`=908) | 0 | 0 | 0 | 12 | 46 | 115 |
| **+ FactorE `X[0]`→12** | 0 | 3 | **10** | 25 | 55 | 116 |

Reaching even 25 % authority (256) at 10 deg/s needs `FactorE(10 °/s) ≥ 288`. **Unreachable by
moving X.** It requires raising `Y[0]` off zero — **a step at zero rate = a relay in rate = the
V78/V79/V80 move, recorded as "WORST GRINDING EVER".**

⇒ **Do not propose the base-assist damper for micro-ratcheting. Cal-only, it structurally cannot
deliver.** This kill saves a build that the §3 result would otherwise have strongly motivated —
and the orchestrator was on his way to proposing it before running the sizing.

---

## 7. 🛑 The Lever-B discriminator: run, and UNDERPOWERED

§3 filters candidates structurally: the culprit must be **engagement-gated AND rate-driven**. Exactly
one known thing is both — **Lever B**, which repoints r24's gain gate to `gp-0x6806` ("LKAS
applying") and swaps the gain 2622 → **5244** while it holds. r24 is a 4-sample backward difference
of column torque, i.e. a rate derivative. **Every build has pushed it UP; §3 says test it DOWN.**

`analysis-2020accord/v89_a6_leverb_discriminator.py`. Both flags **byte-derived from each build's own
image**: Lever B = (`0x3AA96`==`FB` ∧ `0xC6446`==5244); damper = (FactorC m26 `Y[0]`≠0), carried as
its own interaction because the two co-occur (**corr = −0.499**). 400 windows / 12 routes / 93 blocks,
a clean 6-vs-6 route split.

`eng × log|rate| × LeverB`, band contrast vs the 32–38 Hz control: **−0.101 [−0.381, +0.298]**.

🛑 **The CI half-width (0.340) is 2.4× the effect it tests (§3's +0.144).** It cannot distinguish
*"no modulation"* from *"modulation as large as the entire effect"*.
⇒ **INCONCLUSIVE. r24's engaged arm is NOT exonerated**, and no V89 may be justified on this either
way. The script's own verdict logic now refuses to print "exonerated" unless the CI is narrower than
the effect — the `feedback-a-falsifier-only-fires-if-it-could-have-fired` trap, caught before write-up.

⊕ Closing it needs roughly **4× the episode blocks (93 → ~370)**: matched **engaged AND manual**
exposure at matched **wheel rate**, on both a Lever-B and a non-Lever-B build. **That is an exposure
problem, not an analysis one** — and it is the first thing a future drive should be designed around.

---

## 8. Why no build was cut

Four candidate levers, and every one is either spent or structurally blocked:

| candidate | status |
|---|---|
| command-side HF reduction (Lever B class) | 🛑 **measured NON-fix** — V88 halved 15–22 Hz command content; `e_6-9` V88/V67 = 1.040 [0.759, 1.260] |
| a bigger `0xC6446` dose | 🛑 blocked by the ±8192 rail (2.5× at the rail hot-end, 3× pins) **and** the elasticity failed its out-of-sample dose test |
| base-assist damper (FactorC / FactorE) | 🛑 **closed this session on arithmetic** — §6 |
| lowering r24's engaged arm | ⏳ **the one live candidate**, and §7 could not size or justify it |

Cutting a `.rwd` on any of these today would be a bet dressed as a build, and the kit's own record
(V80, V74, V75) is what that costs. **The binding constraint is exposure, and it is now named.**

---

## 9. Collaterals

- **`docs/STATE.md` — 494.7 KB → 88.1 KB**, and it is now current. 47 superseded sections were split
  out **verbatim** to `docs/STATE-ARCHIVE-pre-V89.md` (432.8 KB) by the reproducible
  `analysis-2020accord/shrink_state_md.py`. **Nothing was deleted:** 506,564 B in → 90,231 + 443,142.
  It had been past the 256 KB `Read` limit, so **no agent could load it in one call and the tail was
  silently invisible** — a live instrument defect, not just untidiness.
- **`CLAUDE.md`** carries the cap as a rule under READ FIRST item 1: hard 256 KB, target ~150 KB,
  update in place, never append a dated block, check the size at every close-out. Kept to six lines.
- New scripts, all under `analysis-2020accord/`: `v89_a1_rate_axis.py` · `v89_a2_rate_mechanism.py` ·
  `v89_a3_excitation.py` · `v89_a4_rate_x_engagement.py` · `v89_a5_engagement_model.py` ·
  `v89_a6_leverb_discriminator.py` · `v89_b1_damper_surface.py` · `shrink_state_md.py`.
  JSON outputs in `_cache_r73/`.

## 10. Two instrument defects found, both recorded

1. **`_cache_r66` and `_cache_r66x` hold the SAME route** (`r66`, V80, n = 89,997 both). A naive
   `_cache_r*/r*.npz` glob **double-counts it**. 🛑 **This was NOT cosmetic:** it moved §3's headline
   contrast from **+0.172 [+0.038, +0.288]** (excludes 0) to **+0.144 [−0.004, +0.267]** (does not).
   `v89_a5` is fixed and re-run; `v89_a4`'s binned output was already retracted for other reasons.
   **Glob by ROUTE, not by cache dir** — and re-run the headline after ANY loader change.
2. **`v89_a1`'s per-band order veto** built a different window set per band, manufacturing a
   band-specific result out of nothing (§4a). **Veto once, on a common band, then compare bands on
   identical windows.**


---

## 12. 🛑🛑 SUPERSEDES §3 AND §7 — the loader was skipping most of the corpus

**The operator caught it:** *"We have plenty of routes in our work history. Look at all handoffs and
rlogs since V38. Lever B is in multiple (stock and non-stock)."* He was right.

`v89_a5`/`a6` globbed `_cache_r*/r<NN>.npz` and **silently skipped every PER-SEGMENT cache**
(`r<NN>s<K>.npz`) — ~180 min of the ~417 min on disk. `v89_c1_full_corpus.py` loads **30 routes,
284 min, 10 Lever-B against 20 not, 235 episode blocks** (vs 93). A second bug in the same family:
image lookup used `_{tag}_*_plain_image.bin`, which **misses the `_v67_plain_image.bin` form** and
dropped 18 of 32 routes on the first run.

### What changed with 2.4× the data (`v89_c2_powered_discriminator.py`)

| term | band contrast | verdict |
|---|---|---|
| **`eng`** | **+0.413 [+0.146, +0.667]** | **EXCLUDES 0** — engagement multiplies 6–9 Hz by **2.8×**, 1.5× more than the control band |
| `eng × log rate` | **+0.022 [−0.070, +0.116]** | **NULL, and REFUTES §3's +0.144** |
| `log hands` | **−0.389 [−0.471, −0.290]** | EXCLUDES 0, tighter than before |

🛑 **§3's headline is RETRACTED.** The engagement effect is **band-specific but NOT rate-dependent**.
The rate dependence the operator feels is in the **EXCITATION** (turning the wheel feeds every band),
not in a rate-dependent firmware term. ⇒ **Nothing argues for limiting the LKAS command's angle
rate — the target is a constant gain.**

🛑 **§7's "needs ~4× the exposure, design a new drive" is WITHDRAWN.** It rested on the bug. The
corpus already had 2.4× and the Lever-B answer did **not** sharpen (+0.075 [−0.099, +0.245]) ⇒ more
of the same driving will not settle it, and §13 makes it less interesting anyway.

## 13. ★★★★★ THE MECHANISM — and it inverts a standing recommendation

On V87/V88 **stock modes 24 ≡ 26 are byte-identical in all six factor families**, so engaging changes
**no calibration**. A constant 2.8× amplification must come from the command's ENTRY moving the loop
through a **nonlinearity** — and there is exactly one on record: **`FUN_0003b8f6`, a Coulomb relay
proportional to the COMMAND**, `ratio` saturating against gate **`0xC40BC`** (pinned across 99.62 %
of its range at stock = a pure relay; raising the gate de-relays it).

`v89_c3_friction_relay.py`, identified **within-route**:

| `0xC40BC` | builds | engaged/manual 6–9 Hz amplification |
|---|---|---|
| **600** | stock, V87, **V88 — the car now** | **2.89× [2.14, 3.92]** |
| **6000** | V85, V86, V86B | **6.58× [3.19, 13.14]** |

**`eng × FRIC6000` band contrast +0.682 [+0.213, +1.166] — EXCLUDES 0, POSITIVE.**

⇒ 🛑🛑 **De-relaying the Coulomb friction made the ratchet band 2.3× WORSE**, and
**`STATE.md`'s standing "FREEZE `0xC40BC` at 6000" is contradicted on this band.** The car sits at
600, which is the better value. **Do not restore 6000.**
⇒ ★★★★★ **Two independent lines now agree that COLUMN FRICTION DAMPS THIS MODE:** the driver's grip
(−0.655 vs control −0.266) and the firmware's own relay (600 beats 6000 by 2.3×).
**The lever class is "more column friction/damping", not "less command".**

⚠ **Scope:** 3 routes carry the flag, all one era; **V86 also moved `0xC40D4`** and **V86B armed the
damper**. Both are carried as interactions and come back inconclusive-to-null, but `0xC40BC` cannot
be fully separated from V86's `0xC40D4`. **Association = EVIDENCE; the specific cell = BELIEF.**
⚠ The instrument measures **6–9 Hz band energy, not "feels smooth"**. More Coulomb friction can damp
the oscillation and make the wheel notchier. **The operator scores that.**
