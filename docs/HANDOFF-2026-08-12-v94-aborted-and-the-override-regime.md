# HANDOFF — 2026-08-12: V94 was aborted on-car, and the symptom regime was finally identified

**Predecessor:** `HANDOFF-2026-08-11-routes-78-79-and-the-inertia-reversal.md`
**State:** `docs/STATE.md` §A1–§A7 (rewritten in place at this close-out)
**Lineage:** `docs/BUILD-LINEAGE.md` — the V94 row now carries its on-car result

---

## 0. THE ONE-PARAGRAPH VERSION

V94 flew as route `7d`, fault-free, and **the operator stopped driving it** — *"it vibrated the entire
car, and I decided it was not safe to drive."* **It is still on the car.** V94 cut `gp-0x6b26`'s gain
6× on the premise that the lane is apparent inertia and lowering it is *"strictly safe on both binding
bounds."* Measured afterwards, the delivered lane is a **real 6–9 Hz damper** (+137°/+139° vs wheel
rate), so V94 removed a damper and the car got worse in exactly that band. Separately — and more
valuable — the operator told us **how** he produces the symptom (engage LKAS, then override), which
revealed that **every `Re(Z)` number this kit has ever produced came from a mask that excludes that
regime.** Rescored properly, his claim that *"literally every bad symptom is LKAS engaged only"* is
**confirmed at ~2.2× on 10 of 10 routes.** Two candidate mechanisms died under test in that regime and
a third, unrelated one (a ~0.5–1 Hz surge) was found. **V96 was cut at this close-out — an instrument
build, deliberately not a fix. The number V95 is VACATED.**

---

## 1. WHAT V94 DID, AND WHY IT WAS BACKWARDS

### 1.1 The build
Two changes on a V90 base:

| what | detail |
|---|---|
| `0xCBE74` cut | mode 24 ×0.50, modes 26/27 ×0.25, both non-LERP fallbacks ×0.75 — **6× against V92** |
| `0x55E10` | `sar 0x3,r6` → `sar 0x1,r6`, the CAN-427 packer — instrumentation only |

### 1.2 The on-car result [EVIDENCE]
- **Fault-free.** No DTC, no sentinel, no EPS onroad event.
- **Motor acceleration 3–7× up above 9 Hz** vs the corpus.
- **Column-torque ↔ wheel-rate coherence at 18–31 Hz the highest of any drive in the corpus.**
- Operator: grinding and stuttering *"worse, by a lot"*, whole-car vibration, **aborted**.

### 1.3 The code byte is exonerated [EVIDENCE]
`r6` is consumed only by the `jarl 0x49A90` two instructions later, so the shift has no other reader;
and openpilot's `steeringTorqueEps` dead-ends in `carstate.py`. The packer changes what we *see*, not
what the car *does*. **The regression is the calibration.**

### 1.4 The physics [EVIDENCE — measured, not derived]
`gp-0x6c2c` really is a first difference of filtered motor rate ⇒ an **acceleration**. That much was
right. What does **not** follow is the phase of the *delivered* lane at the wheel:

```
producer identity          ->  acceleration              (correct)
   two EMA poles            (0xC643C = 37>>7, 0xC40DC = 22>>6)
   + the plant
delivered lane at the wheel ->  +137 deg / +139 deg vs WHEEL rate at 6-9 Hz
                            ->  |cos| = 0.73
                            ->  +518 / +565 counts of POSITIVE Re(Z)
```

Two independent drives, ω-partialled against a shuffled control. **It is a damper.** V94 removed
6/6ths of it.

🛑 **Two successive phase stories about this one lane were wrong, four days apart, both
decision-bearing.** The 2026-08-11 story was *"pure inertia, dissipates nothing, cannot damp"*. The
2026-08-12 desk correction was *"+75°, 26 % dissipative, structurally cannot damp 6–9 Hz"* — and that
was **also wrong**, because it phased the *producer's filter* against *motor* rate. The measurement
phases the *delivered lane* against *wheel* rate, with the plant in the loop.

⇒ **The rule is not "do the arithmetic." It is "measure the delivered lane."**
`analysis-2020accord/v94_damping_fraction.py` now carries a SUPERSEDED header; its pole coefficients,
integer mirror and cross-build gain table survive, its central numbers do not.

### 1.5 The process failure — filed in full
`memory/feedback-reducing-a-gain-is-not-a-safety-class.md`. Five compounding failures, of which the
sharpest for future builds:

- **GATE 2 was answered by a sentence that assumes its conclusion** — *"a scalar on an existing term
  adds ZERO phase at any frequency and strictly REDUCES that lane's loop gain"* (`build_v94_tva.py:117`).
  True, and irrelevant: reducing loop gain on a **damper** is what destabilises it.
- **The assertion suite encoded the premise as a PASS condition** —
  `check(y_max_all < y_max_stock, "the largest gain magnitude STRICTLY DECREASES")`. **133/133 green
  measured internal consistency with a wrong premise, not safety.**
- **The motivating null was a measurement artifact.** V91/V92's ×1.5 measured 0.99 because
  `gp-0x6b26 = K·α` and α is *what K damps* — in a stable closed loop **the product is invariant to
  K**. Nobody asked whether the instrument could measure the thing it was pointed at.

**The last line of defence was the operator's hands. That is not acceptable and it is why V96 is an
instrument build.**

---

## 2. THE BIGGER RESULT — THE SYMPTOM REGIME

### 2.1 The operator's two corrections, both of which overturned an orchestrator claim

> *"No you are wrong. Literally every bad symptom is LKAS engaged only."*

> *"Steering override is how I get the steering into such a scenario where grinding and micro
> ratcheting can be observed."*

The first corrected an orchestrator statement that *"~80 % of what you feel isn't gated on LKAS being
on"* — a case of a secondary instrument being allowed to override a primary symptom report. The second
is the more consequential: it names the regime.

### 2.2 Why that breaks every `Re(Z)` number the kit has produced [EVIDENCE]

```python
# opendbc/car/honda/carstate.py:163
ret.steeringPressed = abs(ret.steeringTorque) > STEER_THRESHOLD.get(fingerprint, 1200)
# HONDA_ACCORD (10th gen) is NOT in the override dict  =>  T = 1200
# ret.steeringTorque = STEER_TORQUE_SENSOR   <- THE NUMERATOR OF Z
```

The hands-off mask is a threshold on the **numerator of the very quantity being measured**, and
**override is `steeringPressed == True` by definition**. The instrument was pointed away from the
symptom, and exposure followed it: **7121.6 s engaged hands-off vs 994.9 s engaged hands-on.** The grip
effect was being treated as a confound to exclude; **it is the target.**

Measured verification of the mask's cost: it drops 39 % of engaged and 93 % of manual candidate
windows, and the dropped windows carry **3.91×** the 6–9 Hz torque in the engaged arm vs **1.20×** in
the manual arm — **arm-asymmetric by 3.3×, so it does not cancel in a contrast.** Below 6 Hz the sign
reverses outright (2–4 Hz: −1312 strict vs **+612** band-orthogonal).

### 2.3 The operator is vindicated, quantitatively [EVIDENCE]

6–9 Hz column-torque envelope, override vs manual-hands-on — **both arms hands-on, so grip is matched
out on both sides:**

| route | build | OVR / MAN-ON |
|---|---|---|
| r6e | V85 | **2.90×** |
| r6f | V86 | **2.38×** |
| r73 | V88 | **2.25×** |
| r79 | V92 | **1.93×** |
| r77 | V90 | **1.74×** |
| … | … | 10 of 10 above 1.4 |
| | | **median ≈ 2.2×** |

Ten routes, nine builds. Independently consistent with the standing 2.8× engagement band contrast.
**~55 % of the 6–9 Hz energy he feels is engagement-attributable.**

### 2.4 The two instruments never actually disagreed
`Re(Z)` is **latent** — energy that *would* grow if excited — and hands-off there is almost no
excitation (manual 6–9 Hz coherence **0.040** against a 1/n ≈ 0.014 bias floor). **Band power is the
felt quantity.** 1.24× latent and 2.2× felt are different measurements and both are correct.

### 2.5 🛑 The estimator constraint this creates
Override supports **almost none** of the kit's standard windowing: **5013 contiguous override runs make
up the 994.9 s — median run 0.02 s, p90 0.55 s, and only SEVEN runs corpus-wide reach 5.12 s.** Any
future override scoring must use point-process or event-triggered methods, or 1.28 s windows, **and
must say which, before the drive.**

⇒ `memory/reference-accord-steeringpressed-mask-excludes-the-symptom-regime.md`

---

## 3. WHAT DIED, AND WHAT APPEARED

### 3.1 ☠ Mechanism A — "the LKAS authority collapse curve is the 6–9 Hz exciter"
**Dead, five ways, with perfect exposure.** Median override torque **2235** against a **2240** knot;
33–70 % of override time above 2560 with authority at exactly zero. It had every chance.

1. Knot crossing rate **0.47–1.69 Hz** — about once a second, not eight times.
2. Reconstructed authority spectrum **88.4–94.9 % in 0.5–3 Hz**, peak **0.79 Hz**, every route.
3. Sweeping the unit scale 0.6×–2.0× **never exceeds 1.22 Hz** ⇒ not a mis-scaled-knot artifact.
4. 🛑 The chatter↔energy correlation **inverts against its own negative control**: OVR
   **−0.194 / −0.255** vs MAN-ON **+0.400 / +0.495**. The manual arm shows the stronger,
   opposite-signed effect ⇒ it tracks **how hard the driver is working**, not a firmware mechanism.
5. Not an exciter either: 6–9 Hz energy **falls** after a collapse edge, below the shuffled baseline.

### 3.2 ☠ Mechanism B — "a sign-guard relay chatters when the driver opposes the command"
**Dead.** Request-bit duty **1.0000**, drops/s **0.000**, every route ⇒ the gate never opens.
**openpilot does not back off when overridden — it winds UP 6.7–15×**, so the premise is false.
Direction reversals **0.23–2.66 Hz**, and *lower* during override.

### 3.3 ★ The new one — a real surge, at ~0.5–1 Hz
- The EPS holds LKAS authority at **exactly zero for 17.5–40.5 % of override time**, cycling
  **~0.5–1.7 Hz**.
- **openpilot winds up 6.7–15× during that time** — it does not see the authority kill.

Push, the EPS zeroes the assist, openpilot keeps integrating; ease below the knot and authority returns
with a command an order of magnitude larger. **A genuine surge mechanism, quantified, never previously
described in this kit.**

🛑 **It is ~0.5–1 Hz, NOT 6–9. It is not the grinding and not the micro-ratchet.** It would be felt as a
**slow lurch or a "catch"**. **The operator has not been asked whether he feels it.** Until he answers,
it is a measured behaviour with no symptom attached and must not be reported as a cause of anything.

⇒ `memory/accord-override-surge-and-two-dead-mechanisms.md`

---

## 4. INSTRUMENT RESULTS OF RECORD

- **`Re(Z)` anchored on-car for the first time, parameter-free.** `mean(T·ω)` pooled **+3859**,
  **P(>0) = 0.9238**, n = 20,159, 8 routes / 8 builds. It independently ranks **V80 worst** at
  12–16/18–22 Hz (−8883/−3581) — the build the operator called *"worst grinding ever"*. Detection floor
  **~60 ct at ≥12 episodes; use 150 conservative.**
- **CAN 427 is RECTIFIED.** Aliasing runs on `2f`, and the fold law is `|2f − 50·round(2f/50)|`, **not**
  `f mod 25`. 26/29/31 Hz fold to **2/8/12 Hz** ⇒ the band a 427 magnitude probe exposes is **2–12 Hz,
  not 19–24**, and it **cannot** separate a genuine 2–12 Hz line from a 26–31 Hz image. Both wrong
  versions of this law were used in-session before it was pinned.
- **`gp-0x6bbe` is rate-derived, not the base-assist output** — contradicting the previous headline and
  an existing memory. Dead as a lever.
- **Four more 6–9 Hz stories killed by their own controls**, including **Lever B `0xC6446` CLEARED**
  (⇒ V88's grinding fix need not be traded away) and **0 of 41 varying cells** separating 6–9 Hz.
- 🛑 **RETRACTED: task 5 = 100 Hz.** The derivation rested on an address coincidence. **Task 5's rate is
  OPEN.** Task 1 (`FUN_0002214a`) = 1 kHz survives on two independent methods.
- **`FUN_0002a93a` is dead code** (zero callers); two engagement-gate candidates struck.

---

## 5. COLLATERAL: `memory/MEMORY.md` WAS PAST ITS READ CAP

It had reached **287,321 bytes against a 256 KB `Read` limit** — it could not be loaded in one call and
**its tail was silently invisible**, the same failure `STATE.md` hit at 506 KB. Split verbatim at a
bullet boundary into `MEMORY.md` (149,891 B) and `MEMORY-PART2.md` (129,832 B); verified
`rejoin == original: True`, **312 distinct links before, 312 after, none lost.**

🛑 **The 170 bullets carrying SUPERSEDED / DEAD / FALSIFIED markers (177,891 B) were deliberately NOT
pruned** — they are load-bearing; four candidate levers were killed by them in this session alone.
**The real cause is hook length: 829 bytes average across 405 lines. Compress hooks; do not delete
pointers.**

**`docs/BUILD-LINEAGE.md` had the same problem and it was worse**, because that file is *mandatory
reading before any calibration edit*. It stood at **293.8 KB against the 256 KB cap**. **Part 1 (the
lever index by address, 137 KB) was carved out verbatim to
`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md`** — a lossless carve, asserted in code. The RULES, the
struck-lever lists, and **Part 2 (code caves / GATE 1 / GATE 2)** stay in the main file, now 156 KB.
**Both are under the cap; grep Part 1 by address rather than reading it.**

🛑 **AND A FOURTH, WHICH IS NOT FIXED: `analysis-2020accord/eps_lkas_chain_model.py` is 297 KB.**
This is the worst-placed instance of the four, because `CLAUDE.md` makes the golden model **mandatory
reading before evaluating any lever** — *"a lever is only understood once you can say where it sits in
that chain"* — so an agent that reads it whole gets a **silently truncated tail**, and the tail is
exactly where the newest chain corrections live. It was already over before this session; this
session's edits took it 292.8 → 297.4 KB. **Deliberately not fixed:** it is a live, importable,
re-runnable module, a builder was mid-cut, and module surgery under those conditions risks the one
artifact every other claim is checked against. **Fix pattern:** it is mostly comment blocks — lift the
narrative into a companion `docs/GOLDEN-MODEL-NOTES.md`, or split by chain stage into a package, and
**assert `import` plus a round-trip run before and after**, the way the three carves above were
asserted.

⚠ **OPEN HYGIENE DEFECT, found and NOT fixed:** a link audit over `memory/` reports **105 of 396
distinct `[[wikilink]]` targets unresolved**. **Almost all are a naming-convention artifact, not
missing knowledge** — the older files use `underscore_names` while links to them were written in
`hyphen-case` (`reference_accord_corridor_lockstep.md` exists; links say
`[[reference-accord-corridor-lockstep]]`). A further four resolve only into the *auto-memory*
directory, which is a separate root. **Only two were genuinely absent and both were written at this
close-out** (`accord-v94-flew-and-the-lane-is-a-damper`,
`reference-accord-427-is-rectified-and-folds-26to31-into-2to12hz`). Fixing the rest means touching
100+ files and was out of scope for a close-out; **a canonicalising rename pass is the right fix and
should be its own task.**

---

## 6. WHAT WAS BUILT AT THIS CLOSE-OUT — V96 (and V95 is a burned number)

**V96** — see `docs/STATE.md` §A6 for the spec and `docs/BUILD-LINEAGE.md` for the byte manifest and
hashes.
```
image  876cf2be5800f0f8e315f8b1d63dd103ec11ee7293577808ecff5f19a849cda3
.rwd   7e9a65f11cab4ffc6286f0365ce5196c11dc461468b9ec85022775e35ebdf093
39990-TVA,A160-V96-V92BASE-REVERT.CBE74-PROBE.6B70.374C.674E-427.6B70.SAR6-0x13000-0x100000.rwd
166/166 assertions, reproduces bit-for-bit, 107 B vs V92, ZERO calibration.
```

**Class: an INSTRUMENT build, and deliberately not a fix.** Its two jobs, in order:
1. **Get the car back to a configuration the operator drove and did not abort** — V92's calibration,
   with V94's cut fully reverted. ⚠ **"Revert to V92" is not "revert to stock"**: V92's row is stock on
   `0xC640A` / `0xC640C` / `0xCBE74`[24] and **×1.5** on `0xCBE74`[26]/[27].
2. **Measure the one thing that is blocking every remaining lever** — see below.

### 6a. The fix candidate that appeared and died the same day, and what it taught

The full-image ledger found **`0xC63A6`** — `w[3]` in `FUN_00038148`, **stock 1024**, sitting directly
on the `gp-0x6b26` lane, and **virgin across all 85 images**. With `gp-0x6b26`'s direction now measured
and `0xCBE74` exhausted at ×1.5 (≈94 % of its range), it read as a second independent multiplier on the
one signal whose sign we actually know. It was the first real fix candidate of the session.

**Q1 closed it as a clean single-reader cell** [EVIDENCE, three methods]: one instruction,
`ld.hu 0x73a6,tp,r15 @ 0x381ca`, zero writers, never read by Path 1. 🛑 Note for the trap list:
`get_xrefs_to` returned **"No references found"** — a **false zero** from the Ghidra tp-relative blind
spot, overridden by `search_instructions` plus a raw Python LE scan.

**Q2 killed it — and not on magnitude.** Path 2 is *not* negligible. The problem is that
**`gp-0x6b70` is not an aggregator addend; it is a PID REFERENCE that gets subtracted**
(`error = measured torque − reference`). So the **sign** of the whole path's contribution depends on
the sign of `iVar6` and on the **local slope of a RAM-resident LERP** at the operating point — and
neither is known.

⇒ **A lever whose sign is unresolved is not a lever. That is exactly how V94 reached the car.** The
block is general: **no `FUN_00038148` weight can be moved until that slope is measured.**

⚠ **One contradiction is left open, deliberately.** The claimed inversion boundary at `0xC63A0`
1024→2048 is why the sign risk is taken seriously — but **`0xC63A0` = 2048 flew four times (V72, V73,
V76g, V81) and measured INERT**, V81 fault-free. A model predicting a damping→inverted transition at
that value should not produce four inert flights. Either the model is wrong, or "inert" was measured
hands-off in the wrong regime, or Path 2 is small at the flown operating point — which would contradict
Q2 itself.

### 6b-i. So V96 measures the blocker instead of guessing past it

The original spec put four never-observed lanes on the wire. That would have told us *which* lane
carries the 6–9 Hz energy — useful, but not whether moving a weight **helps or inverts**, which is the
question that just struck the only live candidate. **V96 instead observes `gp-0x374c` (the LERP input)
and `gp-0x6b70` (its output) simultaneously**, yielding the LERP's **local transfer at the real
operating point**. That unblocks the whole weight class rather than ranking six lanes.

✅ **RESOLVED before the cut: the pair IS sufficient.** `d(gp-0x6b70)/d(gp-0x374c>>4) = −f'` holds
**independently of `sign(iVar6)`, `gp-0x6bfe` and `gp-0x6bfa`** — the two sign factors square to +1 and
cancel. No third channel needed.

🛑 **AND THE NUMBER V95 IS VACATED.** Three artefacts wore it inside two hours while the spec moved —
the lane build (`ad8643c1…` / `3a791446…`, deleted), and the pair build briefly numbered V95 (`876cf2be…`
/ `7e9a65f1…`, same bytes, now correctly V96). **Retiring the number is cheaper than disambiguating it
forever.** `build_v95_tva.py` was deleted. ⊕ The orchestrator caused this churn by reporting hashes
while the spec was still moving — the freeze rule exists for exactly that and it was tripped.

**Why not a fix:** no candidate fix lever survived this session's controls. Mechanisms A and B are
dead, `gp-0x6bbe` is dead as a lever, the assist-map operating point is flat, and `0xCBE74` is
exhausted (×1.5 is already ~94 % of its range before int32 wraparound). **The last two builds were both
cut on a mechanism story that measurement refuted after the flash, and V94 is the one the operator had
to stop driving.** Building another lever on another story would be a third go at the same mistake.

**How this differs from the recent arc** — V38–V52 authority/filters/poles/caves · V53–V61 telemetry
probes and lane mutes · V62–V73 the rate lane · V74–V83a the base-assist damper · V84 damper reverted ·
V85–V90 probes on a V38/V89 base · **V91–V94 the `0xCBE74` dose family, ending in an abort.** V96 is the
first build since V90 that **moves no gain at all** and the first ever to instrument the
`FUN_00038148` lane weights, whose six cells have been **frozen at 1024 across every build in the kit**.

---

## 6b. THE CUMULATIVE NON-STOCK DELTA ON V94 — READ FROM THE IMAGE

Reproducible reader: **`analysis-2020accord/ledger_v94_cells.py`** (`diff` · `matrix` · `grid` · `mask`).
Stock `stock_fw_dump/code.bin` sha256 `3f1d55a98aac6e73…`; V94 image sha256 `cd971c05d483fe9c…`.

**Raw diff is 50,529 bytes; 50,284 are `0xFF` in all 85 images** — plain images are reconstructed from
the RWD and leave `0x00000–0x05F31`, `0x07000–0x0EF71` and `0x12FF0–0x12FFF` blank. Packaging, not
levers. 🛑 The 12 bytes that are `0xFF` on V94 but *not* on every image (`0x55C0F`, `0xC61C0–C5`,
`0xC64B4–B8`) are **real edits** and are kept.
**Net: 245 differing bytes in 114 runs, zero unattributed.** Independently reconciled against the V90
audit: 215 + 30 = 245 ✓, 107 + 7 = 114 ✓.

### Calibration cells

| addr | stock | V94 | what it physically is | what it does to the car | from | status |
|---|---|---|---|---|---|---|
| `0xD6A6C` | −9830/−5734/−1966 | **−4915/−2867/−983** | `0xCBE74`[24] — **mode-24 (MANUAL)** friction/inertia LERP Y row | ×0.50 on `gp-0x6b26` in manual | **V93** | 🛑 **HARMFUL** |
| `0xD7A5C` | same | **−2458/−1434/−492** | `0xCBE74`[26] — **mode-26 (ENGAGED)** Y row | ×0.25 — removes ¾ of the term when engaged | V74 / **V93** | 🛑 **HARMFUL** |
| `0xD7A6C` | same | **−2458/−1434/−492** | `0xCBE74`[27] — mode-27 Y row | ×0.25, same | V74 / **V93** | 🛑 **HARMFUL** |
| `0xC640A` | −8192 | **−6144** | `FUN_00036c12` **FALLBACK-2** flat gain | ×0.75 on the same lane | **V93** | 🛑 branch liveness unresolved |
| `0xC640C` | −3277 | **−2458** | `FUN_00036c12` **FALLBACK-1** flat gain | ×0.75, same lane | **V93** | 🛑 same |
| `0xC61B2` / `0xC61B4` | 512 / 512 | **2048** | arbitration + LKAS-gain output clamps | 4× the LKAS authority ceiling | V22 → **V38** | ✅ measured, fault-free 65 builds |
| `0xC6598/9C/AC/B0` | ±1.0f | **±5.0f** | **float** corridor walls | FP twin held in lockstep so the dual-path monitor cannot trip (this is the V27 brick mechanism done right) | V29/V30 → **V38** | ✅ measured |
| `0xC65C4/C8/CC` | 0/1.5/2.0f | **5.0f** | **float** soft-EME boost floor | FP twin of the INT floor | V31 → **V38** | ✅ measured |
| `0xC674E/50/5A/5C` | ±1024 | **±5120** | **int** corridor walls | widens the direction corridor 5× to match the raised authority | V25/V30 → **V38** | ✅ measured |
| `0xC6768/6A/6C` | 0/1536/2048 | **5120** | **int** soft-EME boost floor | the V31 fixpoint; V54 measured it self-stable under a railed command | V31 → **V38** | ✅ measured |
| `0xE4194…`, `0xE5194…` | 15360 | **16384** | **arb setpoint limit**, 72×u16, 8 selector-reachable records | recovers the top 6.25 % of command range openpilot's `torqueBP` was clipping | **V38** | ✅ measured |
| `0xC61C0/C2/C4` | 1600/896/1280 | **0xFFFF** | gentle-EME debounce **rate** thresholds | unsigned `cal < signal` becomes permanently false ⇒ the debounce SM can never fire | **V36** | ✅ resolved gentle EME |
| `0xC64B4/B6` | 24688/16438 | **0xFFFF** | gentle-EME debounce **torque** thresholds | same mechanism | **V36** | ✅ measured |
| `0xC64B8` | `0x70` (112) | **`0xFF`** | **DTC-0x49 fail-counter gate** | makes DTC 0x49 unfirable. ⚠ **side effect: for the compared signal in (112, 255] the live arb no longer takes its high-torque cutoff branch** | **V37** | ✅ measured; ⚠ **see §7.0** |
| `0xC62EA` | 320 | **0** | low-speed steer lockout window (~5 km/h) | "steer to zero" — LKAS keeps authority below 5 km/h instead of `STEER_STATUS = 3` | V53 → **V81** | ✅ measured |
| `0xC6CD0` | −1 | **3564** | V57 **private forward LKAS gain** (Q15, 4×891) | 4× to the forward lane only; the other 5 readers of `0xC646C` stay un-boosted. 🛑 `0xC646C` itself is **stock 891** | V57 → **V81** | ✅ measured |
| `0xC6446` | 512 | **5244** | **r24 engaged arm — "Lever B"**, 2.000× the LERP value 2622 | doubles rate-derivative feedback while engaged ⇒ command 15–22 Hz content **halved at zero LF cost** | V67 → **V88** | ✅ **the kit's only grinding fix** |
| `0xC40D2` | 102 | **204** | **K1**, the \|model\|-proportional modelled Coulomb friction in `FUN_0003b8f6` (1 kHz disturbance observer), 2.000× | more believed friction ⇒ residual ↓ ⇒ reference ↓ ⇒ error ↑ ⇒ PID ↑ ⇒ lighter wheel | **V89** | 🛑 **measured FLAT** (0.947, inside placebo). Left on deliberately |
| `0xC64DE` | 25617 | **25627** | legacy "re-engage ramp / RAMPSTEP" — **label disputed since 2026-07-18** | unknown; road-validated 2026-07 but never isolated | **V22** | ⚠ **longest-carried unmeasured cell — 85 builds** |
| `0x13109`, `0x14120` | `'-'` | `','` | part-number string `39990-TVA-A160` | nothing — lets a flashed ECU be told from stock | V22 | cosmetic |

### Code / cave / probe bytes

| addr | stock | V94 | what it is | from | status |
|---|---|---|---|---|---|
| `0x454FE` | `0xBA` (`bne`) | **`0xB5`** (`br`) | makes a state-4 governor branch unconditional — V42's macro-ratchet fix | V42, present since **V80** | 🛑 **MEASURED INERT** — `gp-0x67fa`'s reachable set excludes the guarded state. Kept because free |
| `0x3AA96` | `0xC5` | **`0xFB`** | rate-lane **gate selector**: dead constant `gp-0x683C` → `latActive` `gp-0x6806` | V67 → **V88** | ✅ **measured** — the gate half of Lever B |
| `0x2A1F0` | `0x6C74` | **`0xD07C`** | reader displacement repointing the forward LKAS gain to `0xC6CD0` | V57 → **V81** | ✅ mechanical half of the V57 decouple |
| `0x55C0E–11` | `24 36 e8 ea` | **`86 ff 26 ef`** | cave **trampoline** — a `movea` replaced by a `jarl` | V31p; current form **V53** | mechanical |
| `0x55DF2–F3` | `gp−0x6C18` | **`gp−0x6B26`** | source displacement of the CAN **427** packer | V87 / **V90** | instrument |
| `0x55E10` | `sar 3` | **`sar 1`** | shift in the same packer | **V94** | ⏳ instrument-only; **exonerated** |
| `0xC4B34–7D` | `0xFF` fill | 74-byte payload | the **telemetry cave**, 100 Hz, 5 bits onto CAN `0x14A` byte4 bits 7:3. Reads nothing into the control path | slot V31p; **this payload is V90's**, byte-identical V90→V94 | read-only |
| 6× `…FFC` | — | recomputed | bootloader **CRC trailer** words, 6 of the 50-block chain | tracks the edits | mechanical |

**The 427 packer, from the decompile then pinned in bytes:**
```
00055df0  ld.h  -0x6c18, gp, r6     2437 e893   # V90/V94: e893 -> da94  =>  gp-0x6b26
00055e06  mul   0x5, r6, r0         e537 4002
00055e0a  movea 0x3ff, r0, r8                   # hi clamp = 1023
00055e10  sar   0x3, r6             a332        # V92 a432 = sar 4 ; V94 a132 = sar 1
00055e12  jarl  0x00049a90                      # clamp(x, 0, 0x3ff)
=>  wire = clamp((abs(src) * 5) >> N, 0, 1023)      N: stock/V90 3 · V92 4 · V94 1
```
⚠ At N = 1 the 1023 ceiling saturates at `|src| ≥ 410` instead of 1638.

**`0xCBE74` verified end to end:** 34 × u32 pointers, 16-byte records `[n:u16][X×n][Y×n]`.
**All 34 stock records are byte-identical** (n = 3, X = 0/1280/5760, Y = −9830/−5734/−1966), **no
aliasing** — 34 distinct addresses, pointer array untouched on all 85 images. V94 changes **exactly 3**.
⊕ V93's ×0.25 used Python floor division on a negative row, so −9830 // 4 = **−2458**, not −2457 —
rounding *away* from zero, i.e. marginally *less* reduction than a true ×0.25.

### Cross-build matrix — what has actually moved, and what is frozen

"frozen N" = consecutive **build images** at the current value, out of 85 (V22→V94), stock not counted.

| cell | stock | V94 | trajectory | frozen |
|---|---|---|---|---|
| `0xCBE74`[24] | −9830/… | **−4915/…** | stock..V92 · **V93..V94 ×0.50** | **2** |
| `0xCBE74`[26]/[27] | −9830/… | **−2458/…** | stock..V73 · V74–V75 ×1.5 · V76 ⟲ · V76g–V77b ×1.5 · **V78–V90 ⟲stock** · V91–V92 ×1.5 · **V93–V94 ×0.25** | **2** |
| `0xC640A` / `0xC640C` | −8192 / −3277 | **−6144 / −2458** | virgin to V92 · **V93..V94** | **2** |
| `0xC407E` | 511 | 511 | V73–V75 **850** (⇒ the V74/V75 faults) · V76 ⟲ · V76g–V77b 850 · **V78..V94 511** | 17 |
| `0xC40D2` | 102 | **204** | **V89..V94** | 6 |
| `0xC40BC` | 600 | 600 | V85–V86b **6000** · **V87..V94 600** | 8 |
| `0xC6446` (Lever B arm) | 512 | **5244** | V67–V68 · **⟲V69–V71b** · V71c · **⟲V72–V76** · V76g · **⟲V77–V83a** · V84–V86b · **⟲V87** · **V88..V94** | **7** |
| `0x3AA96` (Lever B gate) | `0xC5` | **`0xFB`** | exactly the same shape · **V88..V94** | **7** |
| `0x454FE` | `0xBA` | **`0xB5`** | six loss/restore cycles, incl. **V53–V70** (18 builds) · **V80..V94** | 15 |
| `0xC63A0` (`gp-0x6bd0`) | 1024 | 1024 | V72–V75 **2048** · V76 ⟲ · V76g 2048 · V81 **2048** · **V83a..V94 1024** | 13 |
| **`0xC63A2/A4/A6/A8/AA`** | **1024** | **1024** | 🛑 **never moved on any of the 85 images** | **85 — VIRGIN** |
| **`0xC63F8` / `0xC63FC`** | **33 / 328** | **33 / 328** | 🛑 **never moved** — the open **10× left/right asymmetry** lead | **85 — VIRGIN** |
| `0xC61B2` / `0xC61B4` | 512 | **2048** | V22–V37 1024 · **V38..V94 2048** | 65 |
| `0xC646C` | 891 | **891** | V22–V37 1782 · V38–V56 3564 · **⟲V57–V75** · V76 3564 · **V78–V80 3564** · **V81..V94 891** | 14 |
| `0xC6CD0` / `0x2A1F0` / `0xC62EA` | −1 / 29804 / 320 | **3564 / 31952 / 0** | V57–V75 · **⟲V76** · V76g–V77b · **⟲V78–V80** · **V81..V94** | 14 |
| `0x55DF2` (427 source) | `gp−0x6C18` | **`gp−0x6B26`** | V87–V89 `gp−0x6B98` · V90–V91 `gp−0x6B26` · V92 `gp−0x6BBE` · **V93–V94** | 2 |
| `0x55E10` (427 shift) | `sar 3` | **`sar 1`** | stock..V91 `sar 3` · V92 `sar 4` · V93 ⟲`sar 3` · **V94 `sar 1`** | **1** |
| `0x3AB76`/`0x3AC20` (Lever A) | `0xAA` | `0xAA` | V62 · V65 · V71a on · **V71b..V94 OFF** | 27 (off) |
| `0xC6444` (r26 arm) | 512 | 512 | V42 **0** · V71c **3072** · **V72..V94 512** | 25 |
| `0xC644A` (V43 pole) | 1024 | 1024 | V43 **32** · V49 **64** · **V49p..V94 1024** | 52 |
| `0xC61B8`, `0xC63AC`, `0xC6442`, `0xC407C` | — | = | **never moved** | **85 — VIRGIN** |

### 🛑 The unintended-revert record, machine-detected
Every `⟲` above is a build where a cell silently went back to Honda's value. The clustering matches
`STATE.md`'s "seven silent reverts" exactly: **V76/V78/V79/V80** (the V76 cut-from-V38 rebase, which
reverted `0x2A1F0`, `0xC6CD0`, `0xC646C`, `0xC62EA`, `0xC63A0`, `0x454FE` and — V76 only —
`0xC6446` + `0x3AA96`); **V87** (Lever B, both halves, at its V38-base rebase); **V69–V71b** and
**V72–V76** (two further Lever B losses); and **V53–V70** (the 18-build `0x454FE` loss).

✅ **On V94 itself, nothing is carried by accident.** All seven were checked against the images:
`0xC63A0` = 1024 ✓stock · `0xC407E` = 511 ✓stock · `0xC646C` = 891 ✓stock · both `gain_A` records
✓stock · `0xC62EA`/`0x2A1F0`/`0xC6CD0`/`0x454FE` all deliberately restored at V80/V81. FactorB/C/D/E
and the ceiling for modes 24/26/27 are **byte-stock**.

### New versus a re-run
- `0xCBE74` has been touched by **13 builds and every one raised it or restored stock. V93 is the
  first ever REDUCTION** — that part was genuinely new, and it is what made the car undriveable.
- **Mode 24 had never been touched by any build before V93** (frozen 85/85). That is why the manual
  negative control is spent.
- `0xC640A`/`0xC640C` were **virgin across all 85 images** until V93 — a genuinely new lever.
- **The last cell with a measured symptom fix is Lever B (`0xC6446` + `0x3AA96`), frozen 7 builds since
  V88. Nothing since V88 has produced one.**

---

## 7. OPEN QUESTIONS — TWO OF THEM ARE FOR THE OPERATOR

### 7.0 ⭐ THE STRONGEST NEW LEAD — `0xC64B8`, AND IT IS 66 BUILDS OLD

**V37 set `0xC64B8` from `0x70` (112) to `0xFF` to make DTC 0x49 unfirable.** The accepted side effect,
recorded at the time and carried ever since: **for the compared signal in (112, 255] the live
arbitration no longer takes its high-torque cutoff branch.**

🛑 **This session established that the symptom regime is high driver pushback — override.** Nobody has
ever examined this cell in that regime, because until today nobody knew the regime mattered. It is
**non-stock, carried for 66 builds, and sits exactly where the symptom lives.**

⚠ **NOT YET EVIDENCE.** `0xC64B8` is a **u8** and the record calls it a *fail-counter* gate, so the 112
may be a **counter**, not a torque — in which case the "torque in (112,255]" framing is wrong and the
lead dies. Verification is in flight: the exact branch and comparison direction from a decompile, the
**units** of the compared signal, whether the branch was ever reachable on stock, and the full reader
set by both GhidraMCP and a raw Python LE scan. **Do not build on this until those four come back.**

1. 🛑 **Does he feel a slow lurch or a "catch" during an override** — the wheel going slack then
   grabbing — as distinct from the fast buzzing? (§3.3. If yes, a second symptom already has a
   quantified mechanism. If no, it is a real behaviour that happens not to bother him.)
2. 🛑 **Does the car feel different turning left versus right?** `0xC63F8` = 33 vs `0xC63FC` = 328 is a
   **10× ramp-rate asymmetry** and nobody has ever asked.
3. **Task 5's true rate** — retracted, nothing replaces it.
4. **`gp-0x6733` identity** — it drives `gp-0x67e2`, which picks the mode-table column. Both **26 and
   27** are engaged columns.
5. **The `gp-0x67fa == 4` record inconsistency.**
6. **`FUN_0003897a` / `gp-0x6350` / the LERP `X[0]`.**

---

## 8. FILES ADDED OR CHANGED THIS SESSION

**Analysis / tooling**
`rlog-tools/extract_r7d.py` · `v94_r7d_dose.py` · `v94_r7d_symptom.py` · `v94_r7d_fork_version.py` ·
`v95_rez_lib.py` · `v95_rez_polarity_and_mask.py` · `v95_rez_2x2.py` · `v95_lane_decomposition.py` ·
`v95_crossbuild_rez_ledger.py` · `v95_427_aliasing_and_cadence.py` · `v95_override_exposure.py` ·
`v95_override_authority_chatter.py` · `v95_override_onset_ringing.py` ·
`analysis-2020accord/v94_damping_fraction.py` (**SUPERSEDED header**)
⚠ The `v95_*.py` files in `rlog-tools/` are **analysis** scripts, not build scripts.

**Memory (new)**
`accord-v94-flew-and-the-lane-is-a-damper` · `accord-gp6b26-is-a-real-6to9hz-damper` ·
`reference-accord-steeringpressed-mask-excludes-the-symptom-regime` ·
`accord-override-surge-and-two-dead-mechanisms` ·
`reference-accord-427-is-rectified-and-folds-26to31-into-2to12hz` ·
`reference-accord-rez-anchored-on-car-and-its-floor` ·
`reference-accord-gp6bbe-is-rate-derived-not-base-assist` ·
`reference-accord-controls-killed-four-6to9hz-stories` ·
`reference-accord-two-engagement-gate-candidates-struck` ·
`reference-accord-fun3a382-pid-phase-6to9hz-standing-correction` ·
`feedback-reducing-a-gain-is-not-a-safety-class` ·
`reference-accord-task5-100hz-syscall8-rate-divider` (**retracted in place**) · `MEMORY-PART2.md`

**Docs**
`docs/STATE.md` (headline rewritten in place; 154 KB → under cap) ·
`docs/STATE-ARCHIVE-2026-08-11-v90-flight-session.md` (new, 30 KB, verbatim) ·
`docs/BUILD-LINEAGE.md` (V94 row now carries its on-car result) ·
`analysis-2020accord/eps_lkas_chain_model.py` (the `gp-0x6b26` and `gp-0x6bbe` corrections)
