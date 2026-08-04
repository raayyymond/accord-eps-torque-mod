# HANDOFF 2026-08-04 — V69 FLEW. GRIND #1 IS BACK AT CREEP, AND THE DOSE–RESPONSE IS NON-MONOTONE

**Predecessors:** `docs/HANDOFF-2026-08-04-v69-recut-4x-and-ratchet-probe.md` (the ×4 re-cut and the
ratchet probe, same day) → `docs/HANDOFF-2026-08-04-v69-built-speed-shaped-rate-lane.md` (the ×2 cut) →
`docs/HANDOFF-2026-08-03-v68-flew-the-lane-change-is-28hz.md`. Read the ×4 handoff for *why the build
looks the way it does*; this one is what the car said back.

**Route `4f--61171e660d`** — 8 segments, **481.7 s**, 47,990–47,996 frames on the 100 Hz grid.
**FLIGHT-CLEAN, two methods:** `ST == 4` **0** and `ST == 3` **0**, both on the gridded cache *and* on
the raw un-gridded `0x18F` stream. Watchlist absent (`steerUnavailable` / `canError` /
`controlsMismatch` / `immediateDisable` all 0); `steerSaturated` **2** and `steerOverride` **667** are
ordinary. **The zero-EME streak extends.**

**Build identity, confirmed from the probe and not from the filename.** byte4 = `0x87` on **100%** of
frames: bit7 liveness **set**, **bit3 = 0** ⇒ **V68 excluded absolutely** (V68 emits bit3 = 1 in
100.000% of 53,991 frames). V66/V67 are excluded **empirically**, which is stronger than the pre-flight
note allowed: on those builds bit6 is `gp-0x6806` ≈ `latActive` at 99.98%, and route `4f` carries
**345.7 s engaged with bit6 = 0 in every frame** — impossible on V66/V67. V69-×2 is excluded
**structurally** (its `0xC4B54` `61`→`60` makes bit4 constant 1). RWD `e62fcbba…` matches the record.

---

## 1. ★★★★ GRIND #1 IS BACK, AT CREEP — AND THE DOSE–RESPONSE IS NON-MONOTONE

### 1.1 The line is there — EVIDENCE

Engaged, pooled, 18–22 Hz: **f0 20.42 Hz, prominence 13.47** against the kit's **> 4** criterion. f0 is
**identical across all 8 search bands** (the band-centre test that killed the withdrawn "28 Hz mode"),
and the manual arm reads **1.25 = no line**. Present in **6 of 8 segments**; absent on **seg 6**, the
only pure-highway segment.

### 1.2 The order veto is cleared by a contrast a tyre cannot fake — EVIDENCE

A wheel or engine order does not know whether LKAS is on. Engaged-vs-manual, **within route**,
speed-matched:

| contrast | ratio | split-half null |
|---|---|---|
| **18–22 Hz engaged / manual** | **4.726 [1.082, 18.20]** | [0.36, 3.24] |
| 24–28 Hz (negative control) | inside null | — |
| 1–4 Hz (validity) | inside null | — |

### 1.3 Against the other builds

| contrast | ratio | null |
|---|---|---|
| V69 / Kd2 (V62 + V65) | **1.381 [1.026, 1.724]** | [0.83, 1.16] |
| V69 / Kd2-gated (V67 + V68) | **1.654 [1.244, 2.167]** | [0.88, 1.13] |
| **creep < 20 km/h, V69 / V62 (r37) alone — block unit** | **2.244 [1.438, 3.191]** | — |
| **creep < 20 km/h, V69 / V62 (r37) alone — episode unit** | **2.235 [1.533, 3.429]** | — |

⚠ **The all-speeds headline LOSES its CI under the conservative episode unit** — **[0.870, 2.598]**.
**The creep result does not**: it holds under **both** resampling units. Quote the creep number; quote
the all-speeds number only with this caveat attached in the same sentence.

### 1.4 ★ "Lands on stock at ≥ 50 km/h" — CONFIRMED, and one half of it is weak

**1.066 [0.690, 1.677]** vs the Kd1 pool and **0.789 [0.515, 1.252]** vs V59/r2c, both **inside null**,
validity passes. That is the structural prediction of the speed shaping, measured.
⚠ The *other* half — "elevated vs V67/V68 at highway" — is **WEAK**: its 24–28 Hz negative control
moves as much as the subject band. **Do not lean on it.**

### 1.5 ★★ SATURATION IS ELIMINATED — the dose was fully delivered

The pre-flight worry was that peak gain 12288 rails r24 at `|dtorque|` **683** against a
repo-recorded max of **839** (margin 0.81×). Measured on `4f`: transfer-corrected `|dtorque|` max
**633.9**, and **0.0000%** of engaged time above the 683 rail. ⇒ **≥ 99.9% of engaged time received the
full 4.000×.** This is **not** a partially-delivered dose, and the result below cannot be explained away
as clipping.

### 1.6 ★★★ THE DOSE–RESPONSE IS NON-MONOTONE — the session's central result

Median `e_18-22`, engaged creep:

| dose | build | median `e_18-22` |
|---|---|---|
| 0× | V61 | **2501** |
| 1× (stock) | — | **879** |
| 2× | V62 / V65 | **168** |
| 2× gated | V67 / V68 | **109** |
| **4×** | **V69** | **746** |

**The minimum is around 2×.** ⚠ These are **cross-route medians without covariate matching** — read them
beside the matched contrasts in §1.3, not instead of them. But the shape is not subtle and it is
consistent with every matched contrast that has a CI.

### 1.7 ★★ THE EFFECT IS ENGAGEMENT-CONDITIONAL THOUGH THE DOSE IS NOT — EVIDENCE

V69's 4× is applied **identically in both arms** (the gate is reverted; the speed surface does not know
about LKAS). Yet:

- **manual at 4× is indistinguishable from stock** — **1.070 [0.383, 1.396]**, inside null;
- **engaged at 4× is 2.244×** worse than V62.

⇒ **The mechanism lives inside the closed LKAS loop, not in open-loop damping quality.** A pure
"too much derivative feedback makes the ride harsh" story predicts the manual arm moves too. It does not.

### 1.8 🛑 THE MECHANISM IS NOT UNIQUELY DETERMINED — BELIEF, with the dose–response as the EVIDENCE

Two candidates both fit every number above:

**(a) A plain derivative-feedback optimum, overshot.** Kd has a stability optimum; 2× is near it, 4×
is past it. Simple, and requires nothing new.

**(b) A parametric gain collapse.** `gp-0x6ac0` — the rate axis that indexes r24's gain LERP — is
loaded **`ld.hu` (UNSIGNED) @ `0x3AAC4`**. So the gain index sweeps **0 → peak → 0 twice per cycle** of
the oscillation, and V69 turned Honda's **2.0× rate rolloff into 8.0×**, making the damper **weakest at
peak velocity** — exactly where damping does the most work. Modulation depth at `A_rk` 1927:
**1.00×** (V67's flat arm) · **1.49×** (V62) · **5.96×** (V69). Effective-gain crossover at
`A_rk` ≈ **1300** (orchestrator) and **1200–1330** (`RateLaneTrace`, Fourier on the integer chain) —
**two independent methods.**

⚠ Candidate (b) explains §1.7 more naturally (the modulation only bites when the loop is oscillating),
but §1.7 is not a discriminator on its own. **Record both. Do not build as if (b) were settled.**

---

## 2. GRIND #2 — A REPLICATION, AND ONE HYPOTHESIS REFUTED

### 2.1 What `4f` actually says

Creep: **0 bursts**, engaged P(0) = **0.0042**. That reads decisive until you remember **V67 already
gave 0 bursts in 158.7 s at P(0) = 0.0005**. ⇒ **this REPLICATES an already-clean arm.** It is a
non-regression, not a new result.

The **corner cell is under-powered on `4f`**: engaged 26.9 s (P(0) = 0.128), manual 42.2 s
(P(0) = 0.079). `4f` cannot settle a corner question in either direction.

### 2.2 ★ The genuine non-regressions

- **V69's 4× did NOT re-introduce creep grind #2**: engaged max **142.2** vs V62/V65's **1830.7**.
- **V69's manual creep is the first DOSED manual arm since V65** — 0 bursts in 69.1 s, max **50.5**,
  the lowest of any pool, **29× below** V62/V65's 1469.6. P(0) = **0.0512**, just short of the 0.05 line;
  say "just short", not "significant".

### 2.3 🛑 THE ORCHESTRATOR'S "P-A" HYPOTHESIS IS REFUTED — RETRACTION

**P-A said:** V69's rate-axis **under-dose** at grind #2's operating point (1.72× at `gp-0x6ac0` 1206)
is what explains the grind-#2 null — i.e. grind #2 stayed away because r24 was barely dosed where it
lives.

**The premise is CONFIRMED.** All 24 Kd = 2 bursts sit at p90-rate ≥ **400** counts; 19 of 24 at
≥ **1126**; **0 of 96** windows in the lowest stratum. Grind #2 genuinely lives at high motor rate.

**The causal claim is REFUTED.** In the `[1400, ∞)` stratum — which carries **10 of 18** engaged bursts —
**V67 ran 99.8 s at 2.719×, MORE than V62's flat 2.000×, and produced ZERO bursts**, against an expected
**12.00**. **P(0) = 6 × 10⁻⁶.**

⇒ **r24 dose at grind #2's operating point is NOT sufficient to cause grind #2.** The dose story for
grind #2 is incomplete.

⚠ **Not a clean single-variable contrast.** V67 also carries the `0xC646C` decouple, `0xC6CD0` = 3564,
and mss0. The refutation is of *sufficiency*, which does not need the contrast to be clean; a positive
claim from the same comparison would.

---

## 3. ★★ THE LANE-CHANGE TRANSIENT IS DOSE-INDEPENDENT — V69's STATED PURPOSE FAILED

V69 was built to attenuate the ~28 Hz lane-change transient captured on V68. **It did not.**

- The transient **survived and is LARGER in p-p on V69** — **2,599** and **4,094** counts, against
  V68's recorded **1,468**.
- **It runs at full amplitude on the STOCK rate lane.** V58/r2b at dose **1.000×** gives ×floor p90
  **14.93**, max **22.76**, **2,389 counts p-p @ 27.59 Hz**; **V59/r2c at 1.000× carries the corpus's
  largest p-p, 3,283 @ 27.07 Hz.** It is **non-monotone** in dose — V62 at 2.000× is *quieter* than V58
  at 1.000×.

Pooled, speed-matched:

| contrast | ratio | verdict |
|---|---|---|
| 2.000× / 1.000× | **1.176 [0.641, 2.320]** | inside null |
| 2.403× / 1.000× | **2.897 [1.271, 11.439]** | does not clear its null |
| route-level Theil-Sen slope on dose | **+5.736 [−25.432, +34.934]** | **0 inside** |

### ★ Excitation, not gain, is the live candidate

Holding **dose = 1.000× exactly**, ALC vs driver-commanded lane changes = **2.389 [1.453, 4.898]**
against a null of [0.44, 2.26] — **does not clear**, and rests on one manual route. But holding
**excitation** fixed collapsed the 2.403× dose contrast from **2.849 → 2.013** with the CI crossing 1.
⇒ *"an excitation contrast wearing a dose label"* — **the same class of error as the withdrawn 28 Hz
"mode"**, and caught the same way.

⇒ 🛑 **V70 MUST NOT CHASE THE RATE LANE FOR THIS SYMPTOM.**

---

## 4. ★★★ THE RATCHET — FIRST REAL CHARACTERISATION

### 4.1 It is present and it is large — EVIDENCE

**46 windows / 118 s at ≥ 1200 counts p-p, peak 6,065 counts p-p.** Seg 1 carries a **continuous 20 s
event** (t = 20.5–40.9 s); seg 0 carries one at t = 50.4–60.7 s. **The operator's "mostly segments 0 and
1" is confirmed exactly** — his call, before the data.

### 4.2 Frequency and the order veto

**Median 7.79 Hz** by zero-crossing (FFT-free) and **7.56 Hz** by the spectral estimator — consistent
with the recorded **7.56 ± 0.36**. Order veto: slope **+0.0358 Hz per m/s** against wheel order 1's
**0.482** ⇒ **speed-invariant, not an order**; rpm ranges 773–1724 with f0 static ⇒ **not an engine
order** either.

### 4.3 ★ NEW: the loop closes inside the EPS + plant, not through openpilot

The ~7.5 Hz line is **in the torsion bar and in the angle rate, but NOT in openpilot's command**:
`e4tq` 6–9 Hz prominence median **2.7** against a presence threshold of **10**, and it holds when
restricted to windows with command-rail duty ≤ 2%. ⇒ **openpilot is not the oscillator.**

### 4.4 Engagement-conditional

**44 / 46 windows engaged, 0 manual.** Fisher one-sided **p = 4.6 × 10⁻⁵**; matched **6.65
[2.45, 12.85]** vs null [1.03, 3.96].

### 4.5 Three corrections to the ratchet's own record

1. ⚠ **Widen "creep only"** — one **4,843-count** episode at **12.7 m/s**.
2. ⚠ **Q is NOT measurable at NFFT 256** — the main lobe caps the measurable Q at ~13.3. The recorded
   **Q ≈ 36** is **neither confirmed nor refuted** here. Do not cite `4f` either way.
3. ⚠ **The "amplitude-saturated / flat-topped" premise is not what `4f` shows.** Crest factor
   **2.07–2.45** on a band-pass where a steady sine gives **1.414**; **no flat-topping on any filter**.
   That premise is what justified V69's rung choice (probe the lanes' hard nonlinearities).
   **BELIEF-level re-framing — flag it for re-examination, do not treat the saturation model as dead.**

### 4.6 The r24 dose ladder does NOT explain the ratchet — and the test is under-powered

0× → 4× on the ratchet: **NULL, and honestly under-powered** — every CI inside its null, and the
24–27 Hz negative control itself ranges **0.38–2.47**. Cross-build V69/V67 = **3.0× raw / 3.6×
selectivity**, but **both CIs overlap the split-half null** ⇒ **not established**.

⚠ **Route `4a` cannot speak to the ratchet.** Its 149.2 s is engaged-*creep*, but the **hands-off cell
is 13.0 s with zero episodes.** Any future ratchet claim that leans on `4a` is leaning on nothing.

---

## 5. ★★★ THE PROBE POST-MORTEM — THREE DEFECTS, ALL WORTH RECORDING

### 5.1 🛑 bit4 was STRUCTURALLY VACUOUS — it could never have fired, on any build, on any drive

`gp-0x6ad4` is clamped to **±CEILING**, where CEILING = **MIN of three LERPs**. The binding one is
`0xC67C2` / `0xC67C8`, indexed on **voted vehicle speed**, **max 1024**, and it **starts at ZERO**. At
the four ratchet episodes' speeds (**4.9 / 6.8 / 7.8 / 8.0 km/h**) CEILING was **164–341**.

bit4 tested **≥ 4096** — **12–25× above the lane's entire reachable range.**

**ROOT CAUSE: the design read the ERR *input* clamp `±0x2800` as if it were the lane's OUTPUT range.**
🛑 `docs/STATE.md` and `docs/V69-DESIGN.md` both describe bit4 as *"40% of its ±0x2800 ZERO gate"* —
**corrected in both.** This also explains, retroactively and cleanly, **why V56's mute of this lane
changed nothing**: there was very little there to mute at creep.

### 5.2 bit5 was insensitive, not vacuous

`gp-0x6b62`'s reachable max is **5786** — `|gp-0x6b5e| ≤ 4762` from the trapezoid `0xC66CC`
(X = [−384, −128, 128, 294, 384], Y = [0, 4762, 4762, 717, 0], with `0xC63C2` = 1024) plus a latched
`|sVar8| ≤ 1024`. So the 4096 threshold sat at **71% of full range** and the rung only ever saw the
**top 29%**.

### 5.3 bit6 had no exposure — but this is NOT the V64 failure

The replay predicts **~1** one-sided hit on `4f`; observed **0**; **p ≈ 0.37.** That is a
power problem, not a gate problem. **It is also not a positive control**, so bits 5/4 cannot be
interpreted against it.

### 5.4 ⇒ THE TRANSFERABLE LESSON

**Both middle rungs were sized against a DOWNSTREAM GATE WIDTH rather than against the lane's own
reachable output.** A gate's width tells you what the *consumer* will accept; it says nothing about what
the *producer* can emit. Size every threshold against the producing lane's own clamp/LERP ceiling at the
operating point you care about, and state that ceiling in the build note.

### 5.5 ✅ One decoder bug fixed in place — do not regress it

`rlog-tools/decode_v69_ratchet.py`: a **128-sample floor replaces a 256** that made its own null
vacuous — its printed `0/9` was a **tautology**. `analog_line()` and `matched_null()` fixed alongside.

---

## 6. ★★★★ A STATE GATE NOBODY HAD SEEN — CONFIRMED, AND STATE 10 SPLITS THE CHAIN IN HALF

**[EVIDENCE — instruction level, `FUN_0002214a` `0x2214a`–`0x22a84`.]**

```
0002214e  ld.bu -0x67fa[gp],r13   ; 00022172 andi 0xf,r13,r15 ; 0002217c shl r15,r11,r25   (r11 = 1)
000221d6  andi 0x830,r25,r28  -> guards jarl FUN_00036388 @0x22882 , FUN_000428d4 @0x22926
00022518  andi 0x930,r25,r27  -> guards jarl FUN_00028ea6 / FUN_0002b422 / FUN_0002b57a
0002269a  andi 0xc30,r25,r22  -> guards jarl FUN_0003a382  @0x226a0 , FUN_0003aa2c @0x2291e
```

Index is a plain `1 << (gp-0x67fa & 0xf)`, **no off-by-one**, recomputed identically at
`0x221bc`–`0x221c6`.

🛑 **STRUCTURAL POINT: the gate is in the single common CALLER, not inside the four functions.** Each
has exactly one call site, all in `FUN_0002214a`, and **the mask wraps the `jarl` itself** ⇒ in a
masked-out state the function is **never invoked at all** — no stack frame, 0% of body.

| mask | states | what it gates |
|---|---|---|
| **`0x830`** | **{4, 5, 11}** | `FUN_00036388` (return-to-centre) **AND `FUN_000428d4` (the oscillation detector)** |
| **`0x930`** | **{4, 5, 8, 11}** | `FUN_00028ea6` / `FUN_0002b422` / `FUN_0002b57a` — the arbitration/shaper trio, i.e. **`gp-0x6806`'s producer** |
| **`0xc30`** | **{4, 5, 10, 11}** | `FUN_0003a382` **AND `FUN_0003aa2c` (the aggregator)** |

⇒ **IN STATE 10 THE AGGREGATOR AND THE RESIDUAL LANE RUN, WHILE THE DETECTOR, THE RETURN-TO-CENTRE LANE
AND ARBITRATION DO NOT. Assist is delivered from a stale `gp-0x6806`.**

★ **State 10 is REACHABLE in normal operation [EVIDENCE]** — written twice in `FUN_00019970` (the
state-4 handler): `0x199CC` (diagnostic path, `tp+0x74d0 == 0xa`) and **`0x19A72` (the NORMAL path)**,
the latter gated on **bit 15 of `gp-0x6d78`** with bit 16 (→ state 11) taking priority. Writer set over
**33 `st.b` sites** — Ghidra and a raw LE byte scan agree exactly, **no undercount** —
{1,3,4,5,6,7,8,9,10,11}, max 11.
⚠ **[OPEN] what bit 15 of `gp-0x6d78` means.** That decides how *often* state 10 is visited, **not
whether it can be.**

### 🛑 A live alternative for the five-build detector null — and its counter-argument

*"`FUN_000428d4` was never CALLED"* has **never been on the table**, and it has the **identical
signature** to *"it ran and found nothing"*: `gp-0x67df` = 0/14,980 (V64), 0/186,321 (V67),
0/53,991 (V68).

⚠ **BUT V67's OWN PROBE ARGUES AGAINST IT, and it belongs in the same breath.** State 10 is absent from
`0x930` too, so **arbitration — `gp-0x6806`'s producer — is also skipped there and the flag would go
STALE.** V67 measured **`gp-0x6806` == `carControl.latActive` in 150,302/150,327 = 99.983%** of frames,
with all **25** disagreements single-frame transition edges. **A stale flag cannot track engagement
transitions that closely.** ⇒ **the ECU is predominantly NOT in state 10 during engaged driving, which
argues the detector DID run and the `gp-0x67df` nulls are GENUINE.** [BELIEF — indirect, but strong.]

✅ **V70's bit5 rung (`gp-0x67fa == 10`) settles it directly, and both outcomes are decisions:**

| bit5 | verdict |
|---|---|
| **≈ 0** | state ∈ {4,5,11} ⇒ **the nulls are genuine and five builds are vindicated** |
| **materially non-zero** | **the nulls were on the gate** ⇒ the detector programme needs replanning |

🛑 **Do not write "five builds of detector nulls are in play" without the counter-argument attached.**

### ⚠ The detector has a SECOND entry gate, and the record's closure of it was too broad
`FUN_000428d4` is also gated on **`FUN_00046ea6(5)`** — bit 5 of `gp-0x18d0`/`gp-0x18d4`, a
fault/DTC-style bitmask, falling to a fixed **`0x8000` sentinel** if set.
The existing closure — *"bit 5 has exactly ONE caller image-wide, the detector itself"* — established
that the **FUNCTION** has one caller. **It did NOT establish that the BIT is clear in operation.**
**Those are different claims. The second is still [OPEN].** The other three gated functions have no
such secondary gate.

### 🛑 And bus `STEER_STATUS` is NOT `gp-0x67fa`
Route `4f` reads `ST = 0` on 47,990/47,990 frames *while the car steered*, and **state 0 is in no
mask** — so if they were the same variable the car could not have steered at all. **Any earlier
reasoning that equated them is invalid**, e.g. *"ST==4 fires 0/37,922"* read as evidence about
`gp-0x67fa == 4`. [VERIFIED] **State 4 sits inside all three masks** and is where the V42 governor
ratchet substitution used to fire.

⚠ **PROVENANCE CAVEAT, carry it.** This was decompiled against **stock `code.bin`**, with the 33 writer
sites cross-checked **byte-identical in `_v68_plain_image.bin`**. The **dispatcher itself was NOT
decompiled from a V68/V69 image** — high confidence it is unchanged (far outside any cave region), but
that is **BELIEF by adjacency, not EVIDENCE.**

---

## 7. ★★★ THE r26 INERTNESS CLAIM SPLITS — ONE LEG REVERSED, ONE DOWNGRADED

🛑 **Do NOT read this section as a flat reversal of the claim.** It rested on **two independent legs**
and they resolved differently; writing it as a wholesale reversal would be the mirror image of the
original error.

The claim, as it stood in `memory/accord-r26-is-structurally-inert.md`, `memory/MEMORY.md`,
`docs/BUILD-LINEAGE.md` and `docs/V69-DESIGN.md`:

> *"r26 is structurally INERT (`0xC6564` = 40 zero bytes) ⇒ r24 carries the whole lane."*

### 7.1 LEG 1 — THE GATE: **REVERSED. [EVIDENCE]**

- `r26 == 0 ⟺ gp-0x6b5e != 0`. (`0xC6138` = 1 ⇒ `r22 == 1` always, and `gp-0x671a` = 0 over 240k
  frames.)
- `gp-0x6b5e = ((LERP(gp-0x6bda) × 0xC63C2) >> 10) × polarity` — producer `FUN_000361c8` @`0x36256` /
  `0x36264`, shadow pair `gp-0x4cd8`, `0xC63C2` = 1024 = Q10 unity — on the trapezoid `0xC66CC`
  X = [−384, −128, 128, 294, 384], Y = [0, 4762, 4762, 717, 0] ⇒ r26 is killed **only where the LERP is
  ZERO, i.e. `|gp-0x6bda| ≥ 384`**.
- ★ **`gp-0x6bda` is a MARGIN TO A PEAK-HOLD ENVELOPE of driver assist torque `gp-0x6bf0`**
  (`FUN_00036022` @ `0x36068`–`0x3608C`; envelope `gp-0x6bd8` / `gp-0x6bd6` maintained by
  `FUN_00035d38`, **half-width never below 9390**, `0xC614A` = ±10048, margin cal `0xC614C` = 128).
- **Hands-off: `gp-0x6bda` ≈ 9262 = 24× the 384 threshold.**

⇒ **THE GATE DOES NOT KILL r26 IN ORDINARY DRIVING, and least of all hands-off at creep.** The kill
window is a **~512-count sliver at the driver-override end** (≈ the documented override threshold
`0xC6156` = 9216). **This half is settled, and it is a genuine reversal of how the gate was read.**

### 7.2 LEG 2 — THE MAGNITUDE: **STILL BELIEF, unresolved in either direction**

`FUN_00039702` shows the RAM array `gp-0x641E`…`gp-0x6444` is an **adjustment added in Q10 float to a
fixed cal base at `tp+0x7564`**, and **`0xC6564`–`0xC658C` really is 40 bytes of EXACT ZERO** with **no
writer found for the RAM side (10 of 18 cells checked)**. So `stage1 ≈ 0` — **IF that cal base is what
actually feeds `gp-0x69a4`.**

🛑 **THAT LINK WAS NEVER VERIFIED.** `gp-0x69a4`'s real producer is a **live runtime 10-segment LERP at
`0x355C6` in `FUN_000352b4`** — the local *slope* of the curve, gated `|gp-0x4f60| ≤ 25600` —
**1 writer / 3 readers: `0x355A4`, `0x3575A`, `0x3AB3A` (= the aggregator).**

⇒ **"r24 carries the entire lane" is a BELIEF resting on LEG 2 alone**, and the re-attribution of
**V42 / V61 / V62 to a single lane is CONTINGENT ON LEG 2.** It may well still be right. **The
underlying on-car results all stand either way** — only the attribution is in question.

★ **The one indirect argument that LEG 2 holds, and it is the only thing keeping the dose–response
coherent:** at `a = gp-0x69a4 / 1024 ≈ 1`, V67/V68's gate (gain_A **3072 → 512**, a **6.00× cut**) would
put their engaged **TOTAL at ~0.94× stock** — essentially *on* stock — **yet V67/V68 measured the best
grind #1 result in the kit (median `e_18-22` engaged creep 109 vs stock's 879).** ⇒ **the empirical
record argues `a` is small.** [BELIEF — indirect.]

### 7.3 ✅ AND IT IS DIRECTLY MEASURABLE — so this stops being an argument

`gp-0x6adc` is **r26's post-clamp mirror** (`st.h` @ `0x3AD4E`, **0 readers / 1 writer** image-wide),
and r24/r26 share **ONE polarity load** — `ld.b -0x6752[gp],r14` @ `0x3AB78`, reused at `0x3AB7E` (r26)
and `0x3AC3E` (r24) — so **they always carry the same sign** (`gp-0x69a4` is an unsigned magnitude at
both ends). Therefore `sign(gp-0x6adc)` vs `sign(gp-0x6ada)` is a **matched pair**:

| observation | verdict |
|---|---|
| **bit4 pinned at 1 while bit3 toggles** | **r26 is ZERO** ⇒ LEG 2 holds, r24 carries the lane |
| **bit4 TRACKS bit3** | **r26 is LIVE** ⇒ LEG 2 falls, and V42/V61/V62 need re-attributing again |

**V70 flies exactly that pair. Non-vacuous in both directions, resolvable on the next drive.**

### 7.4 What this does to V67/V68 — an open question, not a defect

Repointing `0x3AA96` makes **both** cal arms live under LKAS; `0xC6446` was raised to 5244 but
**`0xC6444` stayed at 512** against r26's LERP value of **3072** at creep. That was recorded as harmless
*because r26 was believed inert* — a justification that no longer stands on its own.

**If r26 is live, V67/V68 is "r24 up 2×, r26 down 6×"**, and total engaged rate-lane damping falls
**below stock** once `a` > **0.848** at 0 km/h, with **`a` unmeasured.**
⚠ **The counter-argument in §7.2 points the other way and is the leading reading** — so V67/V68 is
probably what it says it is. **V70's sign pair confirms or refutes it directly.**

### 7.5 `0xC6444` — a CANDIDATE, not a recommendation

⚠ **Raising it is genuinely UNTESTED.** V42 tested it **downward** (512 → 0, FALSIFIED) — the same
*"tested downward ≠ tested upward"* distinction the **V61 → V62** correction turned on. Blast radius:
**1 reader / 0 writers, no float mirror, same CRC block #48 as `0xC6446`**, overflow ceiling ≤ **6553**.

🛑 **V70 does not take it**, and nothing else should until `a` is bounded: V67/V68's control path is the
measured best in the corpus, and trading it against an unmeasured parameter is the wrong bet.

✅ **V62/V65's `sar` route remains the only edit in this kit that is dose-exact independent of `a`** —
it delivers 2.000× on the total for **every** value of `a`. That is a real and under-appreciated
property of that edit family.

---

## 8. INSTRUMENT AND HARNESS CORRECTIONS

1. 🛑 **`1/median(dt)` is biased by a ROUTE-DEPENDENT amount.** 100.13 Hz (r4f) to **101.42 Hz** (r35)
   against a true grid of **100.000 Hz everywhere**. That is a **1.3% spread = 0.27 Hz at 21 Hz =
   three quarters of a bin — sitting BETWEEN THE ARMS of a cross-build contrast.** Use the **mean rate
   over the longest gap-free stretch plus an index lattice.** ⚠ **`_r31_common.fs_of()` still uses the
   bad estimator.**
2. **The repo's `|dtorque|` figures (123–839) are ALREADY transfer-corrected** —
   `v69_surface_math.measured_dtorque()` applies `|sin(π f · 0.004)|`. A **raw** 10 ms CAN difference
   runs **3.4–5×** larger (analytic ratio 0.202 @ 7.6 Hz → 0.294 @ 50 Hz). A claim that the 0.81× rail
   margin had been overstated tenfold was **raised and withdrawn this session**; recorded so it is not
   re-derived a third time.
3. **`FUN_0003ad74` record selection is 2-point between ADJACENT records only.** Breakpoints
   `0xC6010` = [0, 640, 3200, 6400] counts = **[0, 10, 50, 100] km/h**; **≥ 50.000 km/h reads only
   P2/P3.** ⚠ Boundary detail: at **3199 counts (49.984 km/h)** V69 vs stock is **1.0013×** — a
   **continuous ramp, not a step.** So *"byte-identical at and above 50.000 km/h"* is **true** and
   *"below 50"* is **not**.
4. 🛑 **`0xC618A` is a HALFWORD (= 1024).** A byte read returns 0 and would "disprove" it.
5. **`mcp__ghidra__get_xrefs_to` returned "No references found" for an RTOS task entry.** ⇒ **a null
   from that tool is never load-bearing.**
6. **A `jarl` Format-V scanner mask bug produced ZERO hits for functions Ghidra had just given callers
   for.** Bits 15:11 are **reg2, not opcode**, and `disp = ((hw1 & 0x3F) << 16) | hw2`, sign-extended
   from **22 bits**. **Anchor any such scanner on a known site and assert it** before trusting a count.

---

## 9. WHERE THIS LEAVES V70

**The headline recommendation is to restore V67/V68's control path with a repaired probe.** The reasons,
in order of weight:

1. **The dose–response has a minimum near 2×, and V67/V68 (2× gated) is the best-measured arm in the
   corpus.** V69's 4× is past the optimum at creep. Going back is a measured move, not a retreat.
2. **The probe budget is the scarce resource and all three rungs were wasted or under-exposed.**
   §5 says exactly how to size the next three.
3. **Two probe bits settle two verdict-affecting unknowns, and both are non-vacuous in BOTH
   directions.** **bit5 = `gp-0x67fa == 10`** (§6): ≈ 0 ⇒ the five-build detector null is genuine and
   those builds are vindicated; materially non-zero ⇒ the null was on the gate. **bit4/bit3 = the
   `gp-0x6adc`/`gp-0x6ada` sign pair** (§7.3): bit4 pinned at 1 while bit3 toggles ⇒ r26 is zero and
   *"r24 carries the lane"* holds; bit4 tracking bit3 ⇒ r26 is live.
4. ⚠ **Neither unknown is a reason to expect a different answer.** V67's own gate probe argues the ECU
   is predominantly **not** in state 10 while engaged (§6), and the dose–response argues `a` is
   **small** (§7.2). **The leading reading is that both current claims survive.** V70 measures them
   because they are cheap and verdict-affecting, not because they look wrong.

🛑 **Do NOT aim V70's rate lane at the lane-change transient** (§3). 🛑 **Do NOT read `4f` as evidence
about the ratchet's Q** (§4.5), or **route `4a` as evidence about the ratchet at all** (§4.6).

---

## 10. RETRACTIONS AND CORRECTIONS MADE THIS SESSION

| # | claim | status |
|---|---|---|
| 1 | *"r26 is structurally INERT ⇒ r24 carries the whole lane"* | 🛑 **SPLIT, not flatly reversed.** **LEG 1 (the GATE) REVERSED [EVIDENCE]** — it does not kill r26 in ordinary driving. **LEG 2 (the MAGNITUDE) DOWNGRADED to BELIEF** — `0xC6564` is 40 zero bytes but its link to `gp-0x69a4` was never verified. *"r24 carries the entire lane"* now rests on LEG 2 alone and may still be right; the V42/V61/V62 re-attribution is **contingent** on it (§7) |
| 2 | **P-A**: V69's rate-axis under-dose at grind #2's operating point explains the grind-#2 null | 🛑 **REFUTED.** Premise confirmed, causal claim killed by V67's 99.8 s at 2.719× producing zero bursts, expected 12.00, P(0) = 6e-6 (§2.3) |
| 3 | bit4 tests *"40% of its ±0x2800 ZERO gate"* | 🛑 **CORRECTED.** `±0x2800` is the **ERR input** clamp. The lane's own output CEILING at ratchet speeds is **164–341**; bit4 was **structurally vacuous** (§5.1) |
| 4 | V67 build note: *"`0xC6444` stays stock 512 — r26 is inert"* | ⚠ **JUSTIFICATION WITHDRAWN, conclusion open.** If r26 is live, 512 with the gate repointed is a **6.00× cut** ⇒ V67/V68 is "r24 up 2×, r26 down 6×". The dose–response argues `a` is small, i.e. that the cut is immaterial — an inference, not a measurement (§7.4) |
| 4b | *"bit 5 of `gp-0x18d0`/`gp-0x18d4` is closed as a cause of the V64 null"* | ⚠ **RE-OPENED.** The check established that `FUN_00046ea6` has one caller image-wide — **not** that the **bit** is clear in operation. Different claims; only the first was ever made (§6) |
| 5 | The ratchet is *"amplitude-saturated / flat-topped"* | ⚠ **RE-FRAMED, BELIEF-level.** Crest 2.07–2.45 vs 1.414 for a sine; no flat-topping on any filter (§4.5) |
| 6 | *"the 0.81× rail margin was overstated tenfold"* (raised mid-session) | ⚠ **WITHDRAWN by its author.** The repo's `|dtorque|` figures are already transfer-corrected (§8.2) |
| 7 | *"V69 is byte-identical to stock below 50 km/h"* — never claimed, but implied by the ×2/×4 tables | ⚠ **PRECISION FIX.** At 49.984 km/h V69 is **1.0013×** — a continuous ramp. Only *at and above* 50.000 is it byte-identical (§8.3) |

---

**Reproduce:** `rlog-tools/decode_v69_ratchet.py` (fixed this session — 128-sample floor),
`analysis-2020accord/v69_surface_math.py`, and the route caches for `4f--61171e660d`.
