# HANDOFF 2026-08-11 — V90 flew, and the lever search closed on ARITHMETIC

**Operator's report on V90, verbatim and unedited:**
> *grind #1 still exists · micro-ratcheting still exists · grind #2 can be felt on the highway-speed
> curves or lane changes · parking lot testing · highway and street level testing.*

🛑 **NOTHING IN THIS DOCUMENT IS CALLED FIXED. He reports all three symptoms present.** Every band
number below is an instrument reading, never a symptom result. A band moving is not a symptom being
fixed.

**And V90 could not have fixed anything — it is PROBE-ONLY, byte-identical to V89 in every
calibration cell.** So his report is the **control condition** for the V89 car, not a failed fix. That
is what makes it useful: the same firmware, driven three ways (parking lot, street, highway), still
produces all three complaints.

**The one-line result of the session:** six candidate levers were examined and **all six closed — five
of them on arithmetic rather than on a null** — while the measurement that would decide whether *any*
firmware lever can work (**is the 2–26 Hz anti-damping in the EPS LOOP or in the PLANT?**) still has
**2 qualifying windows / 21.4 s** in the entire corpus.

**Built this session, both UNFLASHED: V91** (`0xCBE74` ×1.5 on the two engaged modes, cal-only, 12
bytes) **and V92** (V91's 12 bytes + a re-specced 8-channel telemetry cave). V91 is flown **against**
the sizing verdict, by the operator's explicit decision — *"we are flying regardless, so the instrument
is free."* §8 states the honest label in full.

---

## 0. WHAT FLEW, AND THE HEALTH OF THE MEASUREMENT

**On the car: V90**, flown as route **`00000077--7411859c54`** — 21 segments, 1245.3 s, cache
`analysis-2020accord/_cache_r77/`. Scoring: `docs/SCORING-2026-08-11-v90-flight.md`.

| | |
|---|---|
| engaged | **1074.6 s = 17.91 min = 86.41 %** — 9 episodes, all ≥ 10 s, longest 276.8 s |
| ≥ 50 km/h / ≥ 80 km/h | 316.4 s / 42.0 s, v_max 90.4 km/h |
| micro-ratcheting regime (1–13 °/s) | 437.6 s · ratcheting (13–50 °/s) 196.0 s · macro (>50) 76.7 s |
| manual | 169.0 s, of which **67.7 % parked** |
| faults | `STEER_STATUS` {0: 124,358, 3: 3} · DTC-active duty **0.000000**, 0 transitions · **0 sentinels** on `0x14A` and `0x18F` · `CONFIG_VALID` 1.0000 · `OUTPUT_DISABLED` 0.00002 · **no EPS entry in 3,489 `onroadEvents`** |
| 427 | 62,180 frames at 49.81 Hz, src 1, DLC 3, COUNTER +1 on 100.00 %, CHECKSUM 16/16 distinct |

**IDENTITY: PASS, parameter-free and single-frame.** `b4 == 0` on **124,362 / 124,362** frames. That
predicate is *impossible* on V86B/V87/V88/V89, where `b4` railed at exactly 1.0000 over 254,085 frames.
The `(byte4>>3)&0x1F` histogram lands entirely in the V90-only alphabet `{1,5,9,13,17,21,25,29}` with
**zero** frames in the pre-V90 alphabet `{3,7,15,23,31}`; every observed value is odd, so `b3 ≡ 1`
holds and the field is being read at the right bit offset. [EVIDENCE]

**Rung health — all four interpretable, and one of them is 0.000 *as an answer*:**

| rung | signal | engaged duty | reading |
|---|---|---|---|
| b7 | `gp-0x6b26 < 0` | 0.5220 | ✔ ~0.50 by construction |
| b6 | `\|gp-0x6bf6\| ≥ 512` | 0.2535 | ✔ the one guessed threshold landed inside its predicted 0.10–0.50 ⇒ **do not move `0xC4B4A`** |
| b5 | `gp-0x6ae2 ≠ 0` | 0.6752 | ✔ V89's rung unchanged ⇒ apples-to-apples |
| b4 | `gp-0x6c00 < 0` | **0.0000** | railed — **and for a gate question 0.000 IS the answer** (§3) |

---

## 1. THE DELIVERABLE — `gp-0x6b26` MEASURED FOR THE FIRST TIME ON ANY BUILD

V90 existed to measure the cell a dose would act on, before dosing it. It did.

Inverting the packer exactly (`wire = clamp(|x|·5>>3, 0, 0x3FF)`, so `|x| ∈ [8w/5, (8w+7)/5]`, a
1.4-count bracket), observed wire range **[0, 199]** with **wire saturation 0.000000** ⇒ every sample
is an honest measurement, not a rail.

| stratum | n | p50 | p90 | p99 | max | **clamp duty at ±511** |
|---|---|---|---|---|---|---|
| **ENGAGED** | 53,630 | 5.5 | 39.1 | 114.3 | **319.1** | **0.000000** |
| engaged, <1 °/s | 18,169 | 2.3 | 7.1 | 25.2 | 128.7 | 0.000000 |
| engaged, micro 1–13 °/s | 21,933 | 7.1 | 35.9 | 96.7 | 303.1 | 0.000000 |
| engaged, ratchet 13–50 °/s | 9,740 | 19.9 | 74.3 | 159.1 | **319.1** | 0.000000 |
| engaged, 5–20 km/h | 12,867 | 13.5 | 66.3 | 155.9 | 319.1 | 0.000000 |
| engaged, ≥80 km/h | 2,101 | 2.3 | 21.5 | 61.5 | 106.3 | 0.000000 |
| MANUAL moving | 2,475 | 5.5 | 23.1 | 56.7 | 104.7 | 0.000000 |

⇒ **the lane is NOT a relay today.** Clipping ladder: largest multiplier never pinning **1.60×** ·
pinning <0.1 % up to **2.75×** · <1 % up to **4.45×**.

🛑 **THIS IS A CLIPPING LADDER, NOT A DOSE BUDGET, AND THE DIFFERENCE KILLED AN ESCALATION PLAN.** A
tighter and structurally independent bound governs the dose: `FUN_00036c12`'s
`mul r13,r6,r0` (×0x111, high half discarded) is **unclamped and UPSTREAM of `0xC407E`**, and int32
wraparound is structurally impossible only for a multiplier **≤ 1.6005**. **A ×2.75 dose would not
pin — it would WRAP, and a wrapped product is a full-scale SIGN INVERSION on the damping lane,
delivered before the clamp meant to contain it.** The scoring agent wrote a "we can escalate to 2.75×
/ 4.45×" paragraph and then **withdrew it in place, as unsafe advice, before the build was cut.**
That withdrawal is preserved verbatim in `SCORING` §10.2.

⚠ The extrapolation is **open-loop** and holds the observed distribution fixed under the dose. In
closed loop more damping *reduces* the motion driving `gp-0x6c2c`, so it **over-states** pinning and is
conservative — but it is still an extrapolation. **The binding stratum is ratchet 13–50 °/s and
5–20 km/h, not highway.**

⊕ **A lineage note with its scope stated:** `0xCBE74` ×1.5 pins **0.000000** of this drive ⇒
saturation is not a candidate mechanism for the V74/V75 hard faults **on route 77's distribution**.
Those builds carried `0xC407E` = 850, and route 77 is not their drive. This **weakens** "the lane
railed"; it does **not** clear the row.

---

## 2. THE SIX LEVERS CLOSED THIS SESSION, EACH WITH ITS REASON

**Five of the six die on arithmetic. Only one dies on a measurement.** That distinction matters: a
lever killed by arithmetic cannot be re-opened by more exposure or a bigger dose.

| lever | verdict | the reason, in one line |
|---|---|---|
| **`0xCBE74`** — friction-comp gain, the standing candidate | 🛑 **CLOSED — no larger dose exists, ever** | int32 wraparound at ≈**1.6005×** ⇒ **×1.5 is 94 % of the lever's ENTIRE range**; and at ×1.5 the delivered damping is **5–69× below the resolvability floor** in every band |
| **`0xC63A6`** — the friction lane's Path-2 weight | 🛑 **CLOSED — inert in the regime, on a PRE-REGISTERED threshold** | micro-regime `\|gp-0x6b26\|` p50 = **7.1 counts** = **0.22 %** of the ±8192 residual clamp, against a stated **≲32 ct do-not-fly** line. It failed a bar written before the number existed |
| **the `Kd` cut** on `FUN_0003a382`'s D term | 🛑 **CLOSED — it is a TRADE, and the cost is 3–4× the benefit** | D **pumps only 2–12 Hz** and **DAMPS 16–35 Hz**. Removing the +0.077 pump at 6–9 Hz costs **−0.217 at 18–22** (2.9×) and **−0.336 at 26–31** (4.4×) — the operator's own two grinding bands |
| **K1 / the friction term** (`0xC40D2`, V89's lever) | 🛑 **CLOSED as a dose question — STRUCTURAL, not a power problem** | above 1 °/s friction and `\|model\|` are **near-collinear**: `P(b5 \| b6=1)` = 0.986 → 1.000; the discriminating cell `(b6=1, b5=0)` is **0.63 %** of engaged frames. You cannot move the term independently of the model in the regime the operator names |
| **term 0 / mixer lane 2** into `gp-0x6ad6` | 🛑 **CLOSED — severed by a single zero constant** | `0xC616C` (`tp+0x716c`) = **0** on stock and on the flown V90, untouched by every build ⇒ `gp-0x6b76` is 0 or a `0x7fff` sentinel on every path ⇒ **lane 2's contribution to `gp-0x6b4a` is unconditionally zero** |
| **the `0xC520C` governor ceiling** as the return-to-centre explanation | 🛑 **CLOSED — it misses by 8.3×** | pooled engaged returns median **127.2 counts** against a first breakpoint at **1050**; at 40–80 km/h the hardest return is **35 °/s = 165 counts** against a **222.8 °/s** onset. Definitively inert in his regime |

### 2a. `0xCBE74` — and why "we cannot resolve it" and "it is too small" are different claims

`fw-dampaxis` ran the delivered-damping arithmetic against V90's real distribution, in the command
domain (the column domain needs the unmeasured `gp-0x6b98 → column` plant, so it was refused):

| band | measured band rms | dissipative fraction | added `gp-0x6b26` at ×1.5 | damping component | at `gp-0x6b98` | % of the 208 ct engaged median | vs the 11 % floor |
|---|---|---|---|---|---|---|---|
| 6–9 Hz | 2.74 ct | 0.226 | 1.37 | 0.31 | 0.33 ct | **0.16 %** | **69× below** |
| 18–22 Hz | 8.42 ct | 0.555 | 4.21 | 2.34 | 2.49 ct | **1.20 %** | **9× below** |
| 26–31 Hz | 11.59 ct *(model-extrapolated)* | 0.722 | 5.80 | 4.19 | 4.46 ct | **2.15 %** | **5× below** |

The 26–31 Hz row is extrapolated via the `|H|` ratio and cross-validated against all four *measured*
bands (model accuracy 0.50×–1.37×); **even at the high end of that error range it reaches only ~2.9 %,
still 4× below the floor.** ⇒ the conclusion is robust to the extrapolation.

⊕ **What survives, and it is worth keeping**: the lane's GATE-2 position is the best of any dynamics
lever in the kit — describing-function gain **exactly 1.000 through ×4** (first departure 0.881 at
×6, reproducing the kit's own recorded figures), the ±1024 zero-reject **can never fire** because
`0xC407E` clamps to ±511 first, and the dissipative sign is closed **structurally** (phase of
`−gp-0x6c2c` vs rate never reaches −90° at any frequency to Nyquist). And `H(0) = 0` **exactly**,
proven three ways including in the fixed-point integer arithmetic itself ⇒ **this lane contributes
nothing at any sustained steering rate, at any multiplier — the operator's own hard constraint is
satisfied STRUCTURALLY, not by argument.**

⚠ **A GATE-2 caution that is specific to the ratchet and was not on record before:** at 7.79 Hz the
term is **97.2 % reactive / 23.5 % dissipative**, and a +90° deviation from the dissipative reference
is `F ∝ −acceleration` — **added apparent inertia**. Adding inertia at fixed physical stiffness and
damping **lowers both `ω0` and `ζ`**. The net sign cannot be signed without the column's `J`/`c`/`k`,
none of which are on file. ⇒ **the lane is a better-supported bet for grind #1/#2 than for the
ratchet.** To match grind #1's dissipative delivery, the ratchet band needs **~6.1×** more gain; to
match grind #2, **~9.2×** — and there is no headroom above 1.60×.

### 2b. The `Kd` cut — killed by extending an existing measurement, not by a new one

`fw-driver-model` found D to be the **sole pumping term** at 7.79 Hz (P −0.145 damping, I −0.053
damping, D **+0.076 PUMPING**), robust across the whole measured phase uncertainty, and identified a
genuinely new, never-tried, cal-only, **zero-added-phase** lever: the flat `Kd` LERP Y values
(`0xC6AE6/E8/EA/EC`, all 2048). It also **corrected the kit's V43 lineage record** (see §5) and
resolved `gp-0x671a`'s authority LERP as an **exact 1.0 no-op**, turning the loop-gain bound
(≈0.064–0.090 at 6–9 Hz) into an exact figure.

Its own write-up flagged the blocking gap honestly: *"18–22 Hz and 26–31 Hz have NO measured
err/velocity phase anywhere found — CANNOT ESTABLISH whether D pumps or damps there. Blocking gap for
a dose decision, not glossed over."*

**`Re(Z)` was then extended to 35 Hz on the frozen estimator and it closed the gap the wrong way for
the lever** (`rlog-tools/v92_rez_extend.py`, pre-declared trust gate coh² ≥ 0.10 **and** ≥ 5×
shuffled; all ten bands pass; §4.1's own bands reproduce bit-for-bit as the positive control):

| band | Re(Z) | phase | coh² | shuffled | D dissipative product |
|---|---|---|---|---|---|
| 6–9 | **−3375** | −125.3° | 0.769 | 0.004 | **+0.077 PUMP** |
| 16–18 | −1610.7 | +146.1° | 0.550 | 0.003 | −0.119 DAMP |
| **18–22** | −652.5 | **+120.2°** | **0.745** | 0.000 | **−0.217 DAMP (2.9×)** |
| 22–26 | −267.8 | +105.7° | 0.739 | 0.000 | −0.290 DAMP |
| **26–31** | **+232.9** | **+69.6°** | **0.834** | 0.002 | **−0.336 DAMP (4.4×)** |
| 31–35 | **+772.9** | +30.9° | 0.497 | 0.000 | −0.213 DAMP |

⇒ **D pumps ONLY 2–12 Hz and DAMPS everything from 16 to 35 Hz. Cutting `Kd` buys +0.077 at the
ratchet and pays −0.217 and −0.336 in the two bands the operator actually complains about.** The
candidate build was killed before it was specified. **[EVIDENCE]**

⊕ **And the sweep produced a second, unlooked-for result: `Re(Z)` flips sign between 22–26 and
26–31 Hz** — the column is **anti-damped 2–26 Hz and positively damped 26–35 Hz**, at the two highest
coherences in the sweep. ⇒ **grind #2's band is not anti-damped at all**, so it is mechanically a
different phenomenon from the stuttering. That is the **same conclusion D6c reached from the
covariates** (§4), from a completely unrelated instrument.

### 2c. The return complaint — the mechanism exists, and it is not the one anybody named

The operator's hypothesis was that active return-to-centre is **suppressed or gated by LKAS command
magnitude, even when LKAS is aligned with the return direction.** `fw-return` disassembled the whole
producer chain and closed both candidate hard gates:

- **No discrete `if (LKAS != 0) suppress return` branch exists anywhere in this firmware.** Scoped
  `search_instructions` over `FUN_00036388` (206 instructions) and `FUN_000360fe` (72), for all five
  candidate LKAS cells: **zero hits, all five, `truncated:false`.**
- `gp-0x67ac` (the aggregator's "reduced" branch, which explicitly *could* zero return-centre) —
  **structurally unreachable**, re-confirmed.
- `gp-0x67fa` (the state gate on return-centre's own call) — **decoupled from LKAS engagement**, on a
  33-writer exhaustive census.

**What does exist:** return-centre (`gp-0x6b62`) and LKAS's own in-aggregator term (`gp-0x6b4c`) are
unconditionally summed into ONE command, capped by a **motor-electrical-rate-adaptive governor
ceiling** (`gp-0x4f64`, table `0xC520C`) — the faster the wheel turns, the lower the ceiling,
symmetric in both directions. Since LKAS aligned with return makes the wheel turn *faster*, the
ceiling shrinks exactly when the combined push is largest. That matches "restricts even when aligned"
without needing an LKAS-specific gate.

🛑 **AND THEN IT WAS MEASURED, AND IT DOES NOT BIND.** `rlog-tools/v93_return_to_centre.py`, four
routes (77/73/75/76), engaged returns defined as `|angle| > 5°`, rate signed **opposite** the angle,
`|rate| > 1 °/s`, sustained ≥ 0.30 s:

- pooled engaged returns (27,914 samples) **median = 127.2 counts** at the on-car-settled scale
  (`gp-0x6ac0` = |column °/s| × 4.7121) ⇒ ceiling **5325 = the FULL value, zero reduction**; the onset
  is **8.3× away**. Duty above X0 = 0.062, above X2 = 0.00018, above X3/X4 = **0.000**.
- **At 40–80 km/h it is definitively inert**: 574 samples, p50 **11.0**, max **35.0** counts
  (= 7.4 °/s) against a **222.8 °/s** onset. Zero samples ≥ 80 km/h.
- Even at the **disfavoured 10.0** scale the median is 270 counts ⇒ still the full 5325 ceiling. To
  make the *median* return reach X0 the scale would have to be **8.25×** the arbitrated value and
  **3.9× beyond** the disfavoured extreme. **The conclusion is not scale-sensitive in any plausible
  range.**
- ★ **And the real binding test is sharper still**: a falling ceiling only *binds* once it drops below
  the command. LKAS alone at 4× (1782) is capped from **3414.3 ct = 724.6 °/s** — **1.3× beyond the
  hardest correction in four routes** and **~28× the ordinary return.**

⇒ 🛑 **`FEASIBILITY-8X-LKAS.md` Part 2 — *"even at TODAY's 4×, moderately fast steering already clips
here"* — is REFUTED.** Part 1 of the same document (the peak `gp-0x6ac0` at highway cruise sits well
below the 1050-count onset) is **CONFIRMED**, and the 40–80 km/h arm is further below still.
⊕ The independent solve reproduces the prior claim's own number to four significant figures
(3414.3 counts), which decodes its notation: `z` is the **count**, and **their own number requires
724.6 °/s.**

⚠ Two caveats pulling opposite ways, so the margin can be judged: `gp-0x6ac0` is rectified and
EMA-filtered, so the p99/max estimates are **upper bounds** (this *strengthens* the null); and the
column→motor conversion is biased low through a torsional mode (this *weakens* the null at the tail).
**The median result's 8.3× margin is robust to both. The p99/max results are not, and no conclusion
rests on them.**

⚠ **This says nothing about whether `0xC6CD0` should move.** A standing ★★★★★ memory freezes the 4×
gain and it is not on the table; §12 supplies only the number.

---

## 3. WHAT V90 SETTLED THAT NOTHING ELSE COULD

1. **THE OBSERVER GATE NEVER FAILS.** `gp-0x6c00 < 0` on **0 of 124,362 frames**, 20.49 minutes,
   engaged and manual, in **every** wheel-rate bin. The observer's success path ran on every frame of
   this drive. Never once measured before. [EVIDENCE]
2. **`Re(Z) < 0` ACROSS 2–16 Hz, REPLICATED at 37× V89's exposure** — 221 windows / 884.5 s (V89 had
   6). **−3375 ct·s/rad at 6–9 Hz** against V89's ≈ −3300 on an independent drive. Predicted phases:
   inertia +90°, damper 0°, spring −90°, negative damping 180°. Measured **−125° to −152°.**
   **The inertia mechanism is refuted again, on new data.**
3. 🛑 **"THE FIRMWARE CANNOT SEE THE 6–9 Hz MODE" IS REFUTED.** The decisive control:
   `R(f) = |B26/W| / |H|` — motor rate per unit wheel rate, normalised at 2–4 Hz where column and
   motor are rigidly coupled, so every scale cancels. **A mode the motor cannot see must show a DIP.**

   | band | R norm | coh² | shuffled |
   |---|---|---|---|
   | 2–4 | 1.000 | 0.271 | 0.005 |
   | **6–9** | **1.016** | **0.438** | 0.001 |
   | 9–12 | 0.730 | 0.206 | 0.000 |
   | 15–22 | 0.996 | 0.765 | 0.000 |

   **R is FLAT. No dip — and 6–9 Hz has the HIGHEST coherence of any low band.** Aliasing cannot
   rescue the hypothesis: shared alias energy is broadband and would *decohere* the channels.
   ⇒ **the damping lane goes back in play for the ratchet** — 2.3× less authority per °/s there than
   at 15–22 Hz (2.99 vs 6.80), **not zero**. What *is* attenuated toward the motor is the narrow
   7.8 Hz **line** (arg-max fraction 0.327 ≈ chance in the motor rate vs 0.482 in the column), **not
   the band.** Neither "invisible" nor "fully visible", and nothing here explains the difference.
4. **The b6 threshold (512), the one guessed parameter in V90's cave, landed inside its predicted
   0.10–0.50 bracket** at 0.2535 ⇒ **do not move `0xC4B4A`.**
5. **NO EVIDENCE THAT V89's K1 = 204 REGRESSED THE GRINDING.** `e_18-22`, V89(+V90) ÷ V88, on three
   strata, all ≤ 1.03 and all **FLAT** against their own constant-build placebo bands. The one stratum
   that read a rise (`v ≥ 20.46 m/s`, 1.451) **is shown to be an artefact**: it shares 205 of 242 V89
   windows with the `v ≥ 22.2` stratum that reads 0.986, so **37 V89 and 2 V88 windows carry the whole
   flip**; both run on 3 V88 episodes and 1–2 cells, and the *no-hypothesis* placebo band `e_10-16`
   also reads "resolvable" there — the signature of a stratum artefact. ⇒ **reverting `0xC40D2` to 102
   is not supported by the grinding measurement, and is also not contraindicated.**
   **Power, stated honestly: this corpus cannot resolve an `e_18-22` change smaller than ≈ ±20 %
   (all-engaged) to ±30 % (order-vetoed).**

---

## 4. 🛑🛑 THE SESSION'S BIGGEST OPEN QUESTION, AND IT GATES EVERYTHING ELSE

**At 6–9 Hz the PID's own terms sum to a NET DAMPER, and the column is anti-damped anyway.**

```
   P  -0.145      I  -0.053      D  +0.077        =>   NET  -0.121   ==  DAMPING
   measured Re(Z) at 6-9 Hz  =  -3375 ct*s/rad    ==   ANTI-DAMPING
   (coherence 0.769 against a shuffled 0.001)
```

🛑 **Two opposite sign conventions are in play and confusing them would invert this. Both are stated:**
per-term dissipative products (the D-sweep's convention) — **negative = damping**; `Re(Z)` (the
impedance convention) — **positive = damping**.

> ⇒ **THE ANTI-DAMPING IS NOT COMING FROM `FUN_0003a382`.** It is another aggregator lane, or the
> plant itself. **[EVIDENCE for both halves; BELIEF as to which alternative.]**

**Every remaining firmware candidate has to answer this**, and it reframes the search: *a lever that
trims a PID term is trimming something that is already on the damping side of the ledger.*

### 🛑 And the measurement that decides whether ANY firmware lever can work still does not exist

Three results converge on one unanswered question:

1. `Re(Z)` is negative across **2–26 Hz** — anti-damping, on 221 windows at coherence up to 0.83
   against a shuffled 0.001.
2. The PID is a **net damper** at 6–9 Hz — so the anti-damping is not in `FUN_0003a382`.
3. The damping levers that could push against it are **spent** — `0xCBE74` capped at ≈1.60× with ×1.5
   already at 94 % of that range, and underpowered by 5–69× even there.

> ### **If the 2–26 Hz anti-damping lives in the PLANT rather than in the firmware loop, NO firmware
> lever can remove it.** Firmware could then only *add damping against* it — and this session has
> shown the available damping levers are far too small to do that.
> ### **The measurement that separates those two cases is the MANUAL HANDS-OFF COAST, and the entire
> corpus contains 2 windows / 21.4 s of it.**

**Cost: ~15–20 minutes of driving.** Measured yield 0.25 qualifying windows per second of continuous
hands-off time ⇒ **~6 runs of 30 s** for a usable-but-wide estimate (≈40 windows), **~14 runs** for
precision comparable to the engaged arm (≈100 windows). Split half at 30–50 km/h and half at
60–80 km/h so it can be compared at matched speed. **It also yields 12–16 clean ring-down edges for
free** (against the 1 the entire corpus has), because a cancel-button disengage held hands-off with no
braking *is* a clean edge.

**The manoeuvre:** reach speed on a straight, empty, level road → **disengage with the CANCEL BUTTON,
not the brake and not by grabbing the wheel** → hands off, foot off the brake, steady throttle →
**coast 25–30 s** → re-take normally. Do not re-engage during the run. Hold ~5 s of steady engaged
driving immediately *before* pressing cancel, so the ring-down edge has a defined pre-state.

🛑 **Safety is the operator's judgement, not the kit's.** This requires hands off the wheel on a moving
car: only on a straight, level, empty road with good surface and no crosswind, in short runs, hands
within a few inches of the rim and ready to take over. **If a run cannot be done safely it should not
be done — a missing control is a far better outcome than an incident.**

⊕ **A hint, flagged as underpowered and not evidence:** `ENGAGED hands-ON moving` (11 windows) reads
`Re(Z)` **+441** at 2–4 Hz and **+1214** at 4–6 Hz, i.e. the driver's grip appears to restore positive
damping — consistent with the corpus's standing grip finding. **coh² 0.023–0.228 against a shuffled
0.006–0.035, so 6–9 Hz in particular is uninterpretable.**

---

## 5. THE DISSOCIATION — the ratchet and grind #2 are not one problem

`fw`-side and log-side agreed independently. **D6c**, 2,032 engaged windows / 286 blocks / four routes,
`|0x0E4|` p5 102 → p95 3,584 ct = a **35.2× load range**, route fixed effects, block bootstrap, every
coefficient reported as a **contrast against the 32–38 Hz negative control**:

| axis | 6–9 Hz (ratchet) | **26–31 Hz (grind #2)** |
|---|---|---|
| `log\|cmd\|`, all engaged | **+0.219 [+0.103, +0.338]** ✔ | **−0.075 [−0.135, −0.012]** ✔ |
| `log\|cmd\|`, highway (v ≥ 13.9 m/s) | +0.082 n.s. | **−0.163 [−0.258, −0.055]** ✔ |
| `log v`, highway | **−1.162 [−1.497, −0.840]** ✔ | **+0.554 [+0.278, +0.825]** ✔ |
| `log\|rate\|`, highway | +0.239 ✔ | **+0.553 [+0.442, +0.651]** ✔ |
| `log\|lat accel\|`, highway | +0.034 n.s. | −0.080 n.s. |

🛑 **The ratchet and grind #2 carry OPPOSITE signs on BOTH the load axis and the speed axis, all four
CIs excluding 0.** The hypothesised replication of the load axis onto grind #2 **fails by reversing,
not by going null.**

⇒ **No evidence that one lever could touch both symptoms.** Anything that reduces command load would,
on these coefficients, be expected to make 26–31 Hz *worse*. **[EVIDENCE for the coefficients; BELIEF
for the mechanistic reading — a regression coefficient is not a lever response.]**

⊕ **Lateral acceleration is NOT the "curve" covariate** — null at 26–31 Hz on the highway cut. The
operator's *"highway-speed curves and lane changes"* is captured by **wheel rate**, not sustained
lateral load: a constant-radius curve has *low* wheel rate once established; a lane change has high
wheel rate. **This corrects the driving protocol** — the earlier advice *"curves beat lane changes for
yield"* was wrong on two counts and is withdrawn. **Deliberate lane changes are the primary
instrument, not a supplement**; target ~60–80 of them spread across many distinct stretches, plus
winding highway, cloverleaf ramps and continuously tightening/opening bends. **Avoid banking exposure
on long steady sweepers** — they inflate the ≥80 km/h seconds while producing almost no qualifying
windows, and the drive will look adequate while yielding nothing.

⚠ **The ratchet's load coefficient replicates in DIRECTION but not MAGNITUDE** — +0.219 here against
the corpus's +0.950. This specification carries `log v` as a competitor, pools four routes with fixed
effects, and includes route 77 (792 of 2,032 windows). **Sign and CI exclusion replicate; size does
not, and no claim is made that it does.**

### 🛑 And grind #2 is essentially UNEXPOSED — a census, not a number

The regime the operator names — engaged, **v ≥ 22.2 m/s with |wheel rate| ≥ 5 °/s** — has
**7 / 33 / 1 / 6 windows** on routes 73 / 75 / 76 / 77. On the loosest populated cut, the
**same-firmware** r77 ÷ r75 comparison returns `e_18-22` **1.504 [1.184, 1.732]** and `e_6-9`
**2.904 [0.862, 5.118]** — on **identical firmware**, with one stratification cell, i.e. no matching
at all. ⇒ **NO grind-#2 claim can be made on this corpus in either direction.**
**What it would take: ~15 minutes of engaged driving above 80 km/h, lane-change-rich, ≥ 20 blocks —
ON EVERY BUILD BEING COMPARED.** A comparison against route 77's 6 windows is not a comparison.

---

## 6. INSTRUMENT CORRECTIONS — eight named traps, all now in `docs/STATE.md`

Each of these was found this session, and each is recorded because it either changed an answer or
would have.

1. 🛑🛑 **THE RATE-CHANNEL RULE, AND ITS SCOPE — this one INVERTS a build decision.**
   For **PHASE and IMPEDANCE** work use the **`0x18F`-sourced rate (`rate_f`)**: `tq` and `rate_f` are
   both fields of the *same held `0x18F` frame*, so the ~9.15 ms staleness is common to numerator and
   denominator and **cancels exactly** in `Z = S_Tω/S_ωω`. Proved, not asserted: recomputing `Z` with
   `rate_c` separates the phase by exactly the skew (−11.1° vs −9.9° predicted at 3 Hz; −100.1° vs
   −93.9° at 28.5 Hz).
   > **Had `rate_c` been used, 26–31 Hz would read −30.3° instead of +69.6°, giving `+0.184 PUMPING`
   > instead of `−0.336 DAMPING` — the opposite build decision, from the same data, at the same
   > coherence (0.827 vs 0.834). Same flip at 18–22 Hz.**
   🛑 **BUT FOR ABSOLUTE MAGNITUDE USE `rate_c` (`0x14A`).** Regressed on the differentiated angle
   (0.1 °/count, a solid LSB anchor) over four routes: `rate_f` slopes **0.743 / 0.756 / 0.763 /
   0.767** (r 0.96–0.98) vs `rate_c` **0.952 / 0.958 / 0.962 / 0.963** (r 0.98–0.99) ⇒ **`rate_f`
   reads ~24 % LOW.** The kit's old "~25 % low" note is confirmed and **pinned to that channel
   specifically.** ⇒ **STATE WHICH CHANNEL YOU USED, EVERY TIME.**

2. 🛑 **A SAME-FIRMWARE PLACEBO PAIR IS MANDATORY FOR ANY CROSS-BUILD CLAIM.** V90 changes no
   calibration cell, so **r77 vs r75/r76 is the same firmware on different drives:**

   | pair (SAME FIRMWARE) | `e_6-9` | `e_18-22` | `e_32-38` (control) |
   |---|---|---|---|
   | r77 ÷ r75 | **1.288 [1.017, 1.661]** — CI excludes 1 | 1.121 [0.870, 1.472] | 0.993 [0.807, 1.189] |
   | r77 ÷ r76 | 1.340 [0.925, 2.259] | **1.333 [1.001, 2.307]** — CI excludes 1 | 1.379 [0.977, 2.164] |

   **Two drives on byte-identical firmware produce band ratios whose episode-block CIs exclude 1.00,
   and one of them excludes 1.00 on the band CONTRAST as well.** ⇒ **the band contrast does NOT rescue
   a thin cut.** This is a fresh, concrete instance of the standing correction that block bootstraps
   understate cross-build uncertainty — it is why every number in §3.5 carries a placebo band, and it
   sets the honest resolution floor at **±16–22 %** (contrasted) to **±33 %** (raw).

3. 🛑 **A BYTE-DIFF REPORTS THE FIRST DIFFERING BYTE, NOT THE CELL ADDRESS.** If a `u16`'s low byte is
   unchanged, the run starts **one byte into the cell**. This produced off-by-one addresses for the
   corridor/boost walls (`0xC674E/50/5A/5C`, floats `0xC6598/9C/AC/B0`) and the clamps
   (`0xC61B2`/`0xC61B4`).
   **THE TELL IS THE VALUE**: the real cell reads a clean **512 → 2048** or **1024 → 5120**; the
   off-by-one reads **2 → 8** and **4 → 20**, which are nonsense as calibration values.
   ⇒ **plausibility-check the value, not just the address.**

4. 🛑 **AN ARRAY SWEEP MUST BE BOUNDED BY THE ARRAY'S OWN RECORDED EXTENT.** `range(32)` on a 34-slot
   array **hid two modes**; "walk until it stops looking valid" **over-walked into `gain_B` and
   invented two** (a previous walk reached "mode 289" and reported phantom differences at "modes
   68/126", which are `gain_B` array 0/1 mode 10).
   **The friction pointer array is 34 slots (modes 0–33). `0xCBE74 + 34*4 = 0xCBEFC` is the FIRST SLOT
   PAST IT** — and it holds `0x000DAA44`, a perfectly valid-looking pointer to a perfectly
   valid-looking `n=3` record. **A guessed bound is not a bound, and neither is an exhaustion walk.**

5. 🛑 **`searchsorted` ON `logMonoTime` SILENTLY MISPAIRS ROWS.** `evt.can` can carry **two `0x14A`
   frames in one event**, sharing `logMonoTime` *exactly* — **3,018 duplicate timestamps on r77** —
   so `searchsorted` collapses onto the first of each tie and **mispairs 1,604 rows while the
   TIMESTAMP CHECK STILL PASSES.** Only a byte check catches it. `extract_r77.py::_row2raw14` derives
   the map and asserts it elementwise against both `raw14_t` and `raw14_b4`.
   ⊕ The *correct* fix for the kit-wide `raw14` off-by-one is that the map is a **constant lead**
   (= 1 on r77), stored as `row2raw14` in the npz — **not** a timestamp reconstruction.

6. 🛑 **`_r31_common.runs_of` RETURNS A GENERATOR.** The first consumer exhausts it and every later
   consumer **silently sees zero windows**. This produced an all-NaN shuffled control on the first D3
   pass — **and a NaN control reads as "no control available", not as a bug.** Materialise with
   `list()`. Worth auditing anywhere `runs_of` is passed to more than one estimator.

7. 🛑 **`np.interp` ON `raw14_b4` INTERPOLATES A BITFIELD.** `v88_d1_exposure.grid` does this; the
   interpolated values have **meaningless bits**, so any bit test reading `g["b4"]` is suspect. D3/D5
   pair nearest-within-10 ms instead.

8. 🛑 **A GROUP-DELAY SIGN IS A REQUIRED SCREEN FOR ANY TRANSFER QUOTED FOR SIZING.** Forward causation
   *requires* the response to lag the input, so a **negative group delay is positive proof of
   feedthrough**. `|tq/b26|` = **17.76 ct/ct at 6–9 Hz** with coh² 0.289 against a shuffled 0.000
   looks like the best transfer on the route — **and it is feedthrough: the column LEADS `gp-0x6b26`
   by 48.8 ms.** Disqualified for sizing. The **only** band that survives the screen is **15–22 Hz**
   (2.64 ct/ct, phase −42.1°, coh² 0.333 vs shuffled 0.000, group delay **+6.3 ms**) —
   ⚠ **and even that is a closed-loop correlation that merely failed to be disproved by a one-sided
   test, not a proven plant gain.**

⊕ **A ninth, carried forward from the standing record and re-measured this session:** the wheel-order
veto's **screening asymmetry INVERTS at highway.** No speed stratum is order-clean for 6–9, 18–22 and
32–38 Hz at once; **above ~21.6 m/s it is the 32–38 Hz NEGATIVE CONTROL that order 3 contaminates**
(18/205 order hits on 18–22 Hz vs **76/205** on the control). ⇒ §5 uses a **symmetric** veto — drop a
window if any order 1–6 lands on **any** scored band's own measured line — because per-band vetoes
build different window sets per band and turn a contrast into a comparison of two different sets.

---

## 7. THE STRUCTURAL FINDINGS — what the firmware turned out to be

These are not levers; they are corrections to the map, and several overturn things the kit had written
down as settled.

- 🛑 **`gp-0x6afe` ≡ `gp-0x6b4e` ≡ 0, ALWAYS, ON EVERY BUILD.** The brief named this cell as "the LKAS
  overlay that reaches the motor". It is a dead cell. `gp-0x3d8c` is a straight sum over all 11 mixer
  lanes of `gp-0x62c8[lane]`; the per-lane role dispatch (`0xC4124` = `[0,0,5,0,5,5,0,0,0,5,0]`)
  either writes an explicit **zero** or does not write at all, **role 7 never appears on any build**,
  and the `.data` boot initialiser for `gp-0x62c8[0..10]` is **22 bytes, all zero**.
  ⇒ the shaper's final `iVar45 = gp-0x6afe + uVar34` reduces to `iVar45 = uVar34` — **there is no
  second, independent LKAS injection at the final stage.** This **corrects a starred memory**
  (`accord-aggregator-reaches-motor-via-gp6acc-bridge.md`'s "CAN/arbitration term" label) and
  `reference-accord-shaper-fun42af8.md`'s "feed-forward addend" label.
- 🛑 **`gp-0x6b4a` is a SECOND, direct, unconditional, unweighted LKAS-descended term into
  `gp-0x6ad6`** — term 0 of `FUN_00037fe6`, negated, **no calibration weight anywhere on its path**,
  and its **gate window (±25600) equals the cell's own final clamp**, so it can drive the reference to
  its full rail alone. Term 7 (the observer residual) is capped at 8192 = **32 %** of that range.
  ⇒ **`gp-0x6ad6` has two LKAS-descended terms, not one**, and the golden model's `[VERIFIED]` block
  at `eps_lkas_chain_model.py:2318-2344` documented only `gp-0x6b4c`, the *sibling*.
  ⊕ **Sign: term 0 is structurally REINFORCING, not cancelling** — the two negations (term 0's, then
  `error = gp-0x4f60 − bias`) cancel exactly, so more LKAS-descended command adds **more** torque in
  the same direction, on top of LKAS's own contribution. Same qualitative shape as the K1 mechanism.
- 🛑 **Term 0's own input lane is nevertheless INERT** — the red-team pass found `FUN_00033d10`'s live
  filter result lands in `gp-0x6b78`, **not** in `gp-0x6b76` which lane 2's caller actually reads;
  `gp-0x6b76` is `sign(gp-0x4f60) × cal(0xC616C)`, and **`0xC616C` = 0** on stock, on the flown V90,
  and in every build script (0 grep hits). ⇒ lane 2 contributes **unconditionally zero**.
  🛑🛑 **`0xC616C` IS A NEVER-RAISE CELL.** A future session will find it at 0, virgin across every
  build, and be tempted to read it as a free never-tried lever. **Raising it turns the idiom into a
  Coulomb relay on driver-torque SIGN, injected straight into the driver-feel reference.** That is the
  V80 class — arguably worse than the standing `0xC4080` hazard, because it relays on driver-torque
  sign specifically, which reverses on every micro-correction at the wheel.
- **`gp-0x6b26` reaches the motor via a Path 1 nobody had documented** — a direct, **unweighted**
  (`weight exactly 1.000`), zero-extra-phase addend in `FUN_0003aa2c`'s aggregator, structurally
  identical to `gp-0x6bd0`'s. The lane is **not** observer-only. Census: **1 writer / 4 readers**,
  closed by Ghidra ∪ Python with every disagreement adjudicated (including one raw-scan hit at
  `0x0614A2` that is the tail of a Format-V `jarl`, and two branch-target text collisions).
- **`0xC407E` = 511 decouples the dose from the DTC-0x1d fault, structurally and at ANY multiplier.**
  `gp-0x6b26 = clamp(raw, ±cal(0xC407E))` and the monitor trips at `|gp-0x6b26| > 512`. At 511 the
  monitor is **untrippable by construction, for any gain M** — the clamp binds first, every time.
  This is stronger than "the fault requires raising `0xC407E`". ⚠ It does **not** clear the row on the
  faults themselves; see §8.
- **`0xC646E` (INERTIA's gain) looks like a second candidate and is NOT one.** It is subtracted from
  the model **inside the same observer, with the same polarity, as FRICTION/K1** ⇒ by the already-
  verified polarity chain, raising it makes the wheel feel **LIGHTER**, the opposite of the intended
  effect. **Do not propose it.** Mechanistic, not merely "untested".
- **`gp-0x4f60` is UNFILTERED, and its producer is now traced** (`FUN_0007f3f8`, a dual-channel
  plausibility/cross-check state machine with a cal-gated scale+offset+clamp; **no EMA/IIR/z⁻¹
  anywhere in the store path**). ⇒ a reaction torque appearing physically at 6–9 Hz reaches
  `gp-0x4f60` with **no firmware-side attenuation.** This closes a region `STATE.md` listed as
  UNSWEPT. 🛑 **An IDENTITY CONFLICT was surfaced and is flagged, not resolved:**
  `reference_accord_gp6af8_fight_trigger.md` labels this same cell *"signed motor/column angular
  velocity"*, citing the identical writer chain; every later and more-corroborated source — including
  the DBC-grounded CAN 399 bridge — calls it **torque**. Working conclusion: **torque (BELIEF)**.
- **Honda's own architecture already contains the cancellation the operator asked for**, and every
  lane of the observer's six-lane sum enters at **identical unity weight** (`0xC63A0`..`0xC63AA` all
  = 1024). The asymmetry that does exist is **gate-window width**, not weight: the LKAS-mirror lane
  gets ±10240, the friction lane ±1024. ⊕ The residual's final clamp is confirmed **at the exact cal
  address** — `cal[0xC6200]` = **±8192** — closing a detail the red-team had flagged as inherited.
- **The dwell relay's polarity is SETTLED: `window_open = |gp-0x6b64| < 1024`** — it opens on a
  **SMALL** signal. Four independent sources converged (a fresh p-code-derived decompile, an
  independent assembly control-flow trace, and three predating sessions). 🛑 **A hand-attempted
  raw-byte CMP-direction decode gave the OPPOSITE answer and was explicitly not trusted.**
  ⊕ The physical reading is a **detent**: arms at near-zero wheel rate, snaps to a fixed 1024-count
  opposing torque after 20 ms of stillness, releases when rate grows.
  ⚠ **And an arithmetic caution carried into that reading:** at 7.79 Hz each zero-crossing gives only
  ~8 ms of near-zero signal against a 20 ms arm requirement, so **the detent likely cannot arm during
  SUSTAINED ratcheting** — better read as an *initiator* of stick-slip than a sustainer, which means a
  low measured duty is **not** automatically a null.
  🛑 **RE-OPENED before close:** the 5-point LERP feeding `gp-0x6b64`
  (`X=[-397,-192,140,294,384]`, `Y=[0,2560,2560,717,0]`) is **zero outside `[-397, 384]`**, so
  `|gp-0x6b64| < 1024` fires for **two physically different reasons** — a genuine low rate (a real
  detent) **or** the outer gate simply being shut. **The snap-state bit alone cannot tell them apart**,
  which is why V92 pairs it with a `gp-0x6bda`-in-window bit.
  🛑 **But the "`(0,0)` should never occur" framing of that pairing is WRONG and is withdrawn — see
  §8b.** A shut gate **ARMS** the dwell counter rather than disarming it, so the counter takes 21 ticks
  (21 ms) to reach its ceiling, and during that climb `b4` is 0 while `b6` is still 0. **`(0,0)` occurs
  for ~2 frames at 100 Hz after every gate-shut edge**; only a *sustained run* indicts the rung map.
  ⊕ The same fact makes `b6 = 1` the **default** state whenever the gate is shut, which is the real
  reason `b4` is required: **without it, `b6` has no baseline.**

---

## 8. V91 AND V92 — BUILT, UNFLASHED, AND THE HONEST LABEL

### 8a. V91 — `0xCBE74` ×1.5 on the two engaged modes. Cal-only. 12 bytes.

```
base   _v90_V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26_plain_image.bin
       sha256 28ac817bc3f76958ad5a33316e420c734949f24b206ddb6d083a5254b3aa70db

0xD7A5C  mode 26 (ENGAGED) friction LERP Y row  (-9830,-5734,-1966) -> (-14745,-8601,-2949)
0xD7A6C  mode 27 (ENGAGED) friction LERP Y row  (-9830,-5734,-1966) -> (-14745,-8601,-2949)

image sha256  0ea15ca9d5f811ddcf915b33237dc3f686461f6b84afb7c476e9f1d2b8a011b1
rwd           39990-TVA,A160-V91-V90BASE-CBE74.M26.M27.X1.5-0x13000-0x100000.rwd
rwd sha256    217f9cef33eaf2544b82bc2c99e8b9e6e5ee3f09bdbe523cfc3014e722b17c0b   (986,042 B)
```

Nothing else moves: V90's cave at `0xC4B34`, the CAN 427 repoint at `0x55DF2`, V89's K1 at `0xC40D2`,
Lever B and the V42 byte are all carried **byte-identical**.

> ### 🛑🛑 THE HONEST LABEL, AS THE BUILD SCRIPT'S OWN HEADER CARRIES IT
> **V91 is the SAME LEVER at the SAME ×1.5 DOSE that flew on V74 and V75. Both of those flights
> HARD-FAULTED with a latched total loss of power steering.** The single difference is `0xC407E`:
> every artefact that ever carried this dose also carried **850**; V91 carries Honda's **511**, one
> count below the DTC-0x1d monitor's 512 trip, so the monitor is structurally untrippable at any
> multiplier. **ZERO flights have ever separated the dose from the 850 interlock — the separation is
> STRUCTURAL, never empirical.** V81 (route 67, fault-free) is a control for the **INTERLOCK ONLY**:
> it is byte-stock on the friction row in all 34 modes, so it says nothing about the dose.
> **Writing only modes 26/27 is a DELIBERATE NARROWING from V74/V75's 14 records, not a reproduction.**

🛑 **AND ×1.5 IS 94 % OF THE LEVER'S ENTIRE RANGE.** Three independent bounds: the clip envelope
(route 77's engaged max 319.1 against the ±511 rail ⇒ ≤ 1.6014); the **int32 wraparound in
`FUN_00036c12`** (≤ **1.6005**, proven against `gp-0x6c2c`'s own hard ±32,000 producer clamp, so it
holds in transients route 77 never sampled — the build script re-derives it at run time and reports
headroom **1.0670×**); and the fact that it is the dose V74/V75 flew, so V91 changes exactly one thing
against them. ⇒ **there is no larger dose. Not "untested at higher dose" — unreachable.**

**Why it is being flown anyway:** the operator's decision, made with the sizing verdict in front of
him — *"we are flying regardless, so the instrument is free."* That is his call and it is recorded as
his, not as a recommendation this session produced. The scoring pre-registration
(`SCORING` §10.1–10.6) is written **before** the build was cut and must be used exactly as written.

**The three pre-declared dose-in-force arms, and they run BEFORE any band scoring:**
1. **ENGAGED, cell-stratified** median `|gp-0x6b26|` ratio V91 ÷ r77 must equal **1.50 ± 15 %**
   ([1.275, 1.725]) with a CI excluding 1.00. A raw route-average percentile comparison is **not
   acceptable** — the statistic runs p50 2.3 at <1 °/s against 19.9 at 13–50 °/s.
2. **MANUAL — the built-in negative control. Must read 1.00.** The dose is on the engaged record only;
   **if the manual arm also scales, the wrong record was edited and the build must be pulled**
   regardless of what the bands say. 8,434 paired manual frames exist.
3. **PER SPEED BIN.** `0xCBE74` is a speed-indexed LERP; a whole-row ×N must give ×N at **every**
   speed. A ratio that varies with speed means only some breakpoints were edited.

🛑 **If the ratio's CI contains 1.00, every band result is UNINTERPRETABLE and must not be reported as
a falsification of the damping hypothesis.** V64's null was on the gate and was read as a result for
weeks.

**Revert triggers, all pre-declared:** clamp duty above ~0 at ±511 (equivalently repeated
`wire == 319`) — **a railed lane is `sign(gp-0x6c2c) × 511`, a Coulomb relay, which is the V80
mechanism itself**; `e_26-31` ratio ≥ 1.50 outside the placebo band; **≥ 3 consecutive order-vetoed
engaged `wrecs` windows with `p_26-31` > 37.12** (threshold fixed from route 77 alone, before V91
existed — **measured false-positive rate on the reference build: ZERO**, 5 windows above it in 5
separate runs, longest run 1); and **the operator, who overrides all of them in both directions.**

⚠ **The predicted effect STRADDLES the detection floor and this is stated in advance.** Upper bound
+50 % (a ×1.5 gain on one damping term, reached only if this lane alone set the band energy); lower
bound zero. **If the true effect is below ~16 %, this corpus returns a null that means nothing and the
operator's own report becomes the primary endpoint.**
⊕ And under friction-induced vibration the response to added damping is **threshold-like, not
proportional** — the two most likely outcomes are *"≈ nothing"* and *"a lot"*; a clean ~18 % is the
**least** likely of the three.
🛑 **But the usual consequence of that argument — "if ×1.5 nulls, try more" — DOES NOT APPLY HERE**,
because there is no more. If ×1.5 nulls, the next step is a **different lever or a different injection
point**, not a larger `0xCBE74`.

⊕ **Costs nothing and buys the most: fly V91 on the SAME ROUTE as 77.** Same driver, same roads,
adjacent in time — the best-matched cross-build pair this kit can construct, and the only lever
available for narrowing the ±20–33 % floor without new methodology.

### 8b. V92 — V91's 12 bytes + a 116-byte cave + the 427 repoint + the 427 scaling fix. PENDING CUT.

```
base   the flown V90.  FIVE edits: 12 cal (IDENTICAL to V91) + 116 cave + 2 repoint + 2 scaling + CRC.
0xC4B34  cave  74 B -> 116 B      SEVEN rungs / 43 instructions, on 0x14A byte4[7:3] AND byte7[7:6]
0x55DF2  da94 -> 4294             CAN 427 MOTOR_TORQUE: gp-0x6b26 -> gp-0x6bbe
0x55E10  a332 -> a432             CAN 427 packer  sar 3 -> sar 4   (the no-clip fix, see below)

artefact token   ...-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4
```

🛑 **PENDING CUT — NO HASHES ARE RECORDED HERE ON PURPOSE.** The payload changed after the artefacts
that existed on disk during this close-out: **`b4` swapped from `sign(gp-0x6abc)` to
`gp-0x6bda`-in-window, the cave grew 110 → 116 B, and the fifth edit was added.**
**Re-hash from disk after the real cut. Do not flash on the strength of this section.**

> ### 🛑🛑 SUPERSEDED V92 ARTEFACTS — NEVER FLOWN, DO NOT FLASH
> An earlier V92 cut **this session** — image **`b092bf19db04f580…`**, rwd **`630248a53393fcc2…`**,
> **182/182 assertions, from-disk verified** — carried the **OLD rung map: `b4 = sign(gp-0x6abc)`, a
> 110 B cave, and no 427 `sar` fix.** It was superseded before flight by the `gp-0x6bda`-in-window swap
> and the `0x55E10` `a332`→`a432` no-clip fix.
> 🛑 **Those two hashes appear in this session's transcript with a complete PASSING assertion log
> behind them. They are DEAD.** The files are renamed on disk to
> `SUPERSEDED-DO-NOT-FLASH-_v92_OLDRUNGMAP-b4.6ABC-NEVER-FLOWN_plain_image.bin` and
> `SUPERSEDED-DO-NOT-FLASH-39990-TVA,A160-V92-OLDRUNGMAP-b4.6ABC-NEVER-FLOWN-0x13000-0x100000.rwd`,
> and will be deleted at the real cut.
>
> **DEAD hashes written out IN FULL, so that grepping the transcript's own string lands on this block:**
> ```
> DEAD - image  b092bf19db04f58047a58eeefeb784f63ff8655c573493e8d2c7f63bf4dfdce2
> DEAD - rwd    630248a53393fcc2470b66b709604e0d43cffc87fdcbf3d7962061947467fb11
> ```
> ⚠ A truncated hash in the record is **not** a working DEAD marker: the search that will actually be
> run is a paste of the **full** 64-char string out of the transcript, and a prefix-only entry returns
> nothing. **Write superseded hashes out in full, next to the word DEAD.**

🛑 **AND THE GENERAL LESSON, WHICH IS THE DURABLE PART:**

> **A VERIFIED ARTEFACT FOR A SUPERSEDED DESIGN IS *MORE* DANGEROUS THAN AN UNVERIFIED ONE, NOT LESS —
> everything about it looks correct, including its assertion log.** A hash reported in a transcript
> **outlives the artefact it names.** ⇒ **When a build is re-cut, the superseded hashes must be
> explicitly named DEAD in the record, not merely omitted from it.**

Stripping the stale hashes from the docs — which is what the previous pass did — is **necessary and
not sufficient.** The only tell left in the transcript was the `6ABC` token buried in the old filename,
and that only reads as a warning to someone who already knows a swap happened. **Omission is invisible;
a DEAD marker is not.**

⊕ **Attribution, because it matters for how this class of catch gets made: the BUILDER caught this
itself and pushed back on the orchestrator's own proposed filename, which had called the superseded
artefacts a "dry run". They were not a dry run — they were a real, fully-verified cut, and the
distinction is the entire hazard.** Another instance of §9's pattern: the correction came from the
agent that owned the artefact, against the orchestrator's characterisation of it.

🛑 **The V91 honest label applies to V92 in full and verbatim — the build script carries it word for
word.** And the script adds the consequence itself: **the dose is 5–69× below the measurable floor**
⇒ **V92 is a MEASUREMENT build with a sub-floor cal edit riding along, NOT a dose build. The
operator's own report is the PRIMARY ENDPOINT and the telemetry is the point of flying it. Do not
expect the 12 calibration bytes to show up in any band statistic; if they do, that is a surprise to be
explained, not a result to be claimed.**

**The payload as BUILT — `0x18F` untouched, ONE hook:**

| channel | signal | why |
|---|---|---|
| 427 (50 Hz) | `clamp(\|gp-0x6bbe\| × 5 >> 4, 0, 0x3FF)` | the **BOOST lane** — of the aggregator's 11 lanes, nine are settled; this is the flagged **best structural match for anti-damping** (same-signed as the raw torque sensor ⇒ REINFORCING), and §4 says the anti-damping is not the PID. **`>> 4`, not `>> 3` — see the no-clip fix below** |
| byte4 b7 | `gp-0x6bbe < 0` | its sign, at 100 Hz — **the only channel reaching 26–31 Hz** |
| byte4 b6 | `gp-0x6b62 < 0` | the **return-centre lane's own net dissipative sign**, never measured |
| byte4 b5 | `gp-0x6b62 ≠ 0` | **lane LIVE** — separates the confirmed disable branches from "tiny" |
| **byte4 b4** | **`gp-0x6bda ∈ (−397, 384)`** | **the outer-gate-OPEN bit. It is not a nice-to-have partner for the detent bit — it is what makes `byte7 b6` interpretable at all.** See the validator note below |
| byte4 b3 | fingerprint ≡ 1 | ⇒ every `byte4[7:3]` value is ODD |
| **byte7 b7** | `\|gp-0x6b26\| ≥ 15` | 🛑 **DOSE-IN-FORCE for the `0xCBE74` ×1.5 edit** — needed because 427 has moved off `gp-0x6b26`. `T=15` from route 77's own percentiles: duty **0.242 stock → 0.339 dosed**, both well off 0/1 |
| **byte7 b6** | `gp-0x6a82 > cal(0xC627E)=20` | **the DWELL-RELAY SNAP STATE — the detent test** |

★ **THE FIRST BUILD EVER TO WRITE CAN `0x14A` BYTE 7.** Every cave from V53 to V90 wrote byte 4 bits
7:3 and nothing else; the telemetry field grows **5 bits → 7**. It is also **the first cave to
instrument the aggregator's OWN unresolved lanes** (`gp-0x6bbe`, `gp-0x6b62`) rather than the
observer/friction family (`gp-0x6bf6`/`gp-0x6ae2`/`gp-0x6c00`) that V86B–V90 all sampled, and **the
first rung anywhere in the kit to test a relay/detent hypothesis** rather than a linear sign
correlation. **The cave rungs are ALL new signals** — none of `gp-0x6bbe`/`gp-0x6b62`/`gp-0x6abc` has
ever been on the wire.

★ **IDENTITY, single-frame and disjoint BY CONSTRUCTION: any frame with `0x14A` byte7[7:6] ≠ 0 proves
V92 is on the car.** No build V53–V91 can produce it — `gp-0x1511`'s only two writers (`0x55C02`
`andi 0xcf,r8,r8`, the redundancy-voted counter at bits 5:4; `0x55C2A` `andi 0xf0,r6,r6`, the checksum
nibble at bits 3:0) **explicitly mask bits 7:6 off** — verified two ways (a decompile of
`FUN_00055a98` and an independent Python byte scan of the whole image for any
`st.b/st.h rX,-0x1511[gp]`, which returns exactly those two hits). **It does not depend on trusting
any prior build's measured duty.** ⊕ The checksum call sits **after** the hook, so it covers the two
new bits automatically — the same mechanism ten-plus flights have used for byte 4.

**🛑🛑 THE `(b4, byte7 b6) = (0,0)` VALIDATOR — "SHOULD NEVER OCCUR" IS WRONG AND IS WITHDRAWN.**
Both the spec and the orchestrator framed `(0,0)` as a free correctness check that *cannot* happen.
It can, and a scorer told *never* **would pull a working build.**

`b4` exists because `|gp-0x6b64| < cal(0xC618A) = 1024` fires for **two physically different reasons**
— a genuine low wheel rate (a real detent) **or the outer LERP gate simply being shut**: the 5-point
LERP feeding `gp-0x6b64` (`X=[-397,-192,140,294,384]`, `Y=[0,2560,2560,717,0]`) is **zero outside
`(−397, 384)`**, so `Y1 = 0` ⇒ `gp-0x6b64 ≡ 0` ⇒ trivially `<1024` ⇒ a flat −1024 bias, **not a relay**.

**But a shut gate SATISFIES the arm condition on every tick, so the dwell counter CLIMBS to its
ceiling of 21 rather than staying down — and that climb takes 21 ticks at 1 kHz = 21 ms. During the
climb `b4` is already 0 while `b6` is still 0.**

⇒ **`(0,0)` occurs for ~21 ms after EVERY gate-shut edge — roughly 2 frames at 100 Hz per event.**

> **CORRECTED PRE-REGISTRATION: `(0,0)` is RARE and ALWAYS ADJACENT TO A `b4` FALLING EDGE. A
> SUSTAINED `(0,0)` RUN is what indicts the rung map — a handful of frames per event is the instrument
> working as designed.**

⊕ **And the correction STRENGTHENS the design rationale, which is why it is worth more than the fix
itself.** Because a shut gate **ARMS** the counter rather than disarming it, **`b6 = 1` is the DEFAULT
state whenever the outer gate is shut.** ⇒ **`b4` is not a nice-to-have partner for `b6`; it is what
makes `b6` interpretable at all — without it, `b6` has no baseline.** The `gp-0x6bda` swap was right
for a **better reason than either argument given for it at the time** (the case made was
"disambiguate a detent from a constant"; the sharper statement is the missing baseline).

⊕ 🛑 **THE GENUINE never-occurs validator is a DIFFERENT cell, and keeping the two straight matters:
`(b6, b5) = (1, 0)` IS structurally unreachable** — both bits read `gp-0x6b62`, so it cannot be
negative while also being zero ⇒ **12 of the 16 odd `byte4` codewords are reachable.** **That one is a
real correctness check; `(0,0)` is not.**

**🛑 Two more things to carry into the scoring:**
1. ⚠ **The detent may not arm during a SUSTAINED ratchet** — at 7.79 Hz the rate signal is near zero
   only ~8 ms per zero crossing against a 20 ms arm time. 🛑 **Read a low duty as "trigger, not
   sustainer", NOT as a null. Both rails are informative, which is what justifies the bit.**
   ⊕ One-tick caveat, recorded so nobody rediscovers it as a defect: `FUN_00036388` evaluates the snap
   on the **pre**-update counter and stores the **post**-update counter, so a 100 Hz read equals the
   condition the 1 kHz task evaluates on its next tick — **≤1 ms, immaterial at 100 Hz.**
2. ✅ **THE 427 SATURATION RESIDUAL IS FIXED IN THE CUT, as the fifth edit.** `gp-0x6b26` was clamped
   to ±511 upstream so V90 could never clip (511×5>>3 = 319), but **`gp-0x6bbe`'s aggregator window is
   ±2048**, so at `sar 3` the field would **saturate at `|gp-0x6bbe| ≥ 1639`** — flat, monotone, never
   wrapping, but **blind over the top ~20 % of the lane's range.** The **SIGN bit was unaffected
   either way and still reaches 26–31 Hz.** `0x55E10` `a332` → `a432` gives `|x|×5>>4`: max
   **640 / 1023, never clips**, at half the resolution.
   📋 **Method note worth keeping: the builder REPORTED the defect and NAMED the one-byte fix rather
   than silently applying it, because the brief scoped the repoint to exactly 2 bytes. The widening
   was then authorised. That is the escalation path working, not a scope violation.**

⚠ **The cost of the swap, in the builder's own wording:** `sign(gp-0x6abc)` — the raw-motor-rate
**convention anchor** — was dropped to make room for `b4`, and that is
***"recoverable at DC, unrecovered in the 6–30 Hz bands where band-resolved phase claims live."***

🛑 **CAVE DISCIPLINE — not one of the 116 bytes is hand-encoded.** All are copied from a
Ghidra-verified twin (V90's own flown cave in this base image, or Honda code elsewhere in it), and the
script asserts **116/116 byte coverage by the twin table before it will build.** That is what defeats
three specific traps: **`subr r0,r6` is `8031` — the hand-derived `3080` is `satsubr`, which SATURATES
instead of negating and would corrupt `b7` on negative values only, a defect that survives a flight**;
`ld.h X[gp],r7` and `ld.w X[gp],r7` share hw1 `243f` with only hw2 bit 0 separating them, so the
counter was deliberately moved to **r6** (hw1 `2437`, already flying); and `ld.bu -0x1511` has op field
**0x3D, not 0x3C** (the displacement's bit 0 lives in hw1 bit 5), so both load and store are copied
**whole, 4 bytes each**, from the `0x14A` builder's own byte-7 accesses.
**GATE 1 verified fresh, not inherited:** every new access is an `ld.h`/`ld.hu` — a load has no side
effect and **no new RAM is claimed anywhere**; scratch is **r6 and r7 only**, asserted mechanically
(every register referenced ∈ {r0, gp, tp, r6, r7, lp}, every register written ∈ {r6, r7}); r6/r7 are
dead at the hook, **r8/r10 are LIVE across it and the cave never touches them**, lp is dead.
**GATE 2** is vacuous for the cave (a straight-line leaf: no loop, no call, no divide, no float, 42
instructions at 100 Hz inside Honda's own `di`/`ei` critical section, V90's hook site unchanged) and
for the cal edit is V91's argument re-run in full. **Two CRC trailers, derived in code from the
image's own 50-block map, never hard-coded.**
🛑 **FROZEN, and V92 moves none of them**: `0xC40D2` (K1) since V89 = 3 builds · `0xC6446` (Lever B)
since V88 = 4 · `0x3AA96` since V88 = 4 · `0x454FE` since V80 · `0xC407E` at Honda's 511 since V81 ·
`0xC6CD0` = 3564 (the 4.000× forward gain) on **every** build.

⊕ **A deliberate decision, argued rather than defaulted:** stay on the **one** `0x14A` hook rather than
take a second on `0x18F`. A second, never-flown hook is a distinct risk class from more bits on
`0x14A`'s ten-flight-proven one — **exactly the "novel cave/hook combination" class this kit's three
bricks (V24/V27/V48B) came from.**
⊕ **`b5`/`b6` were freed by a MEASUREMENT, not a guess** — V90's `(b6,b5)` 2×2 showed friction and
`|model|` are near-collinear above 1 °/s, a **structural** explanation for V89's null rather than a
pending measurement, so those two rungs had nothing left to buy.

⚠ **One cross-agent claim adjudicated rather than deferred, and it found a real nuance:**
`gp-0x6bf0` is **not** referenced anywhere inside `FUN_00036388`/`FUN_000360fe` — it is computed in a
separate function (`FUN_0003bd7c`) and has **15+ readers including the shaper directly**. So the "two
terms of one return-centre lane" framing is imprecise. (`gp-0x6abc` **was** confirmed independently as
raw, unfiltered motor rate.)

---

## 9. ON HOW THIS SESSION RAN — the catches came from re-derivation, again

**~10 agents.** As in the V89 session, **the catches came overwhelmingly from an agent re-deriving an
INHERITED claim, not from the agent that made it.** The five that mattered:

1. **The golden model's `[VERIFIED]` tag was covering an incomplete picture.**
   `eps_lkas_chain_model.py:2318-2344` documents `FUN_00026c80` as `[VERIFIED]` — "~11 LKAS-internal
   distribute sources summed into `gp-0x6b4c`, the LKAS lane into the aggregator." True, and it
   **missed `gp-0x6b4a`**, the wider pre-combine sibling from the same internal aggregate `iVar13`,
   which is a second, direct, unconditional, **unweighted** LKAS term into the driver-torque
   reference. A `[VERIFIED]` tag certifies what was checked, **not that nothing else is there.**
2. **`gp-0x6afe` proven always-zero, against a starred memory.** The brief itself named this cell as
   the LKAS overlay reaching the motor; the agent traced the producer fresh and found the opposite,
   closing it two ways (deterministic re-derivation for the reachable roles + the boot initialiser for
   the one untouched role). **The brief was wrong, and the agent said so rather than working around
   it.**
3. **A mode-count "correction" RETRACTED by its own author.** `arc-sweep` first wrote that the
   record's *"13 engaged modes"* was wrong and the true count was 12. It then re-measured, found its
   own `range(32)` had **truncated a 34-slot pointer array**, and retracted in place:
   *"`BUILD-LINEAGE.md` RULE 11's 14-site address list matches my re-measurement EXACTLY, all 14,
   sorted. The record is right; I was wrong."* ⊕ It also isolated the one clause in the record that
   *is* wrong (RULE 11's *"so it never saw m10"* — m10 **is** written and **is** in the same 14-site
   list beside it), i.e. an internal inconsistency rather than a bad address.
4. **The dwell-relay polarity.** A same-day claim from one agent (`counter ramps while
   |gp-0x6b64| > 1024`) contradicted another's. Settled by a p-code-derived decompile plus three
   predating sessions: **`<`, it opens on a SMALL signal.** 🛑 **The losing input was a hand-attempted
   raw-byte CMP-direction decode** — reconstructing V850's Format-I field layout and CMP convention
   from memory under time pressure is exactly the failure class the kit's own rule warns about. The
   agent that made it **explicitly refused to trust its own decode** over the decompile.
5. **Three wrong hand-decodes, one of them the orchestrator's.** Two are documented in the session's
   own artefacts: `fw-dampaxis`'s first reading of `mulh` as a 16-bit-truncating multiply (**wrong** —
   raw P-code shows two `INT_SEXT`s then a 32×32→32 `INT_MULT`), and the dwell-relay CMP decode above.
   ⚠ **The third — the orchestrator's own — is reported by the orchestrator and I could not find it
   documented in any file on disk; it is recorded here as reported, not as verified.**

⊕ **And the counter-example is worth recording too**: the red-team pass on term 0 **did** hand-decode
condition nibbles at byte level (`0xA2` low nibble `0x2` = `BE`, distinct from `0xA` = `BNE`;
`0x51AF` decoded field-by-field as a genuine `SUB`, not a `subr`/`satsubr`) — **after** framing the
claim from the decompile, and **as confirmation** of a structure already established. That is the
standing rule working as intended: **assembly CONFIRMS a claim you already framed; it does not FORM
it.**

**The shape of the session, honestly:** five of six levers closed on **arithmetic** — a wraparound
bound, a collinearity, a zero constant, a sign flip in an extended sweep, and an 8.3× margin. Only one
closed on a measurement. **That is a better session than a null, and a worse one than a fix.** What it
leaves is a single, cheap, well-specified experiment (§4) that determines whether the remaining search
has a target at all — and it needs 15–20 minutes of driving, not another build.

---

## 10. NEXT STEPS, IN ORDER

1. 🛑 **THE HANDS-OFF COAST (§4).** ~15–20 minutes. It is the only thing on this list that changes what
   is knowable. Everything else is conditional on its answer.
2. **Fly V91 or V92** — the operator's call; flash only on explicit instruction naming the file and the
   bus. **Score with `SCORING` §10.1–10.6 exactly as written**, dose-in-force arms first. **Fly it on
   the same route as 77** if at all possible.
3. **Highway curves and lane changes, ~15 minutes above 80 km/h, on EVERY build being compared** —
   without it, grind #2 stays unscoreable in either direction (§5).
4. **Answer §4's question in the firmware**: where is the 2–26 Hz anti-damping, if not the PID? The
   boost lane `gp-0x6bbe` is the top remaining aggregator candidate and V92 instruments it.
5. ⊕ **Do NOT re-propose:** a larger `0xCBE74` dose (there is none) · the `Kd` cut · `0xC63A6` ·
   a K1 dose · `0xC646E` · raising `0xC616C` · raising `0xC407E` · the `0xC520C` governor table as the
   return-complaint fix · the base-assist damper · the observer FIR taps · a cancellation cave.

---

**Read alongside:** `docs/SCORING-2026-08-11-v90-flight.md` (the flight, and V91's pre-registration) ·
`docs/TRACE-2026-08-10-dampaxis-sizing-and-safety.md` (the `0xCBE74` census, safety and sizing) ·
`docs/GATE2-2026-08-11-cbe74-independent.md` (the PID terms and the `Kd` lever) ·
`docs/TRACE-2026-08-10-driver-reference-vs-lkas.md` (`gp-0x6ad6`'s inputs) ·
`docs/REDTEAM-2026-08-11-term0-verdict.md` (term 0, and `0xC616C`) ·
`docs/TRACE-2026-08-11-return-to-centre-gate.md` (the return complaint) ·
`docs/SPEC-2026-08-11-telemetry-budget.md` (V92's payload) ·
`docs/_v91_arc_brief.md` (the arc V84→V90 and V90's complete non-stock delta, read from the images).
