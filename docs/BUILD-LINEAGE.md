# Build lineage and lever index — CHECK THIS BEFORE PROPOSING ANY CALIBRATION EDIT

**Why this file exists:** on 2026-07-27 two independent agents, in the same session, proposed
`0xC6450` 1024→32 as a "new, never-flashed" vibration lever. **It is V46 verbatim — flashed, null.** A
third nearly repeated it with `0xC644A` (V43, flashed, null). Both had read `CLAUDE.md`; the flashed
result was buried in prose.

> **RULE: before naming any calibration address as a lever, grep `analysis-2020accord/build_v*_tva.py`
> for it and check the table below. State its on-car result in your recommendation.**

---

## 🛑🛑 RULE 13 — **TRACE A FUNCTION'S OUTPUTS FORWARD. DO NOT ENUMERATE ONE CELL'S READERS AND STOP.**

**Added 2026-08-08, after eleven independent methods returned the same wrong answer.**

For three rounds the kit asked *"who reads `gp-0x6b94`?"* — disp16 and disp23 byte scans, LE32 absolute
literals, movhi/movea pairs, ep-address materialisation, pcode dataflow, and two register-return checks.
**All null.** Against six flashed on-car results (V61, V62, V67/V68, V74, V75, V80) that could only have
worked if that lane reached the motor.

**The lane does reach the motor.** The bridge is two hops past where every check stopped:

```
gp-0x6b94 -> FUN_0004503c (governor) -> gp-0x6ace -> FUN_000456a4 (comp-add) -> gp-0x6acc
          -> FUN_00042af8 reads gp-0x6acc @0x431C4 -> gp-0x6b08 @0x43206 -> ... -> gp-0x6b98
```

**Nobody asked about `gp-0x6acc`.** And `gp-0x6b08` had been dismissed as *"self-referential ramp state,
one writer inside the function itself"* — **individually true, collectively misleading**: that check asked
whether anything *outside* the function reads it and stopped, never asking whether the function's **own
next instructions** consume it. They do.

⊕ The chain was **already documented** in `reference_accord_post_governor_comp_add.md` (May 2026) with
the exact address `0x431c4`, and in `build_v30_tva.py`'s own header. Neither was cross-checked against the
newer "cannot reach" conclusion. **When a new negative contradicts an old positive, diff them explicitly.**

★ **A "monitor-only" output two hops from the motor is a red flag, not a conclusion.** And a governor
whose cals bricked the car (V40) is not on a dead path — **a coherent account of V40 is the acceptance
test for any claim about this chain.**

Full detail: `memory/accord-aggregator-reaches-motor-via-gp6acc-bridge.md` and
`docs/HANDOFF-2026-08-08-v81-flew-and-the-aggregator-reaches-the-motor.md`.

---

## CATCH-UP: V76 → V86  (Part 1 had fallen five builds behind; 2026-08-08, extended 2026-08-08 late and 2026-08-09 late)

| build | base | levers | on-car |
|---|---|---|---|
| **V96** | **V92** | 🛑 **ZERO CALIBRATION BYTES — the first build since V90 that moves no gain at all.** 107 B in 7 runs: `0x55DF2` `42`→`90` (CAN 427 source `gp-0x6bbe` → **`gp-0x6b70`**) · `0x55E10` `A4`→`A6` (`sar 4`→`sar 6`, sized to `gp-0x6b70`'s own ±8192 clamp) · `0xC4B34–0xC4BA7` a **112-byte cave inside V92's proven 116-byte footprint — NO GROWTH**, 4 B back to virgin · one CRC trailer. V94's `0xCBE74` cut reverted **BY CONSTRUCTION** (V92 base, every cal cell asserted equal to V92's *image*) | **BUILT, VERIFIED, UNFLASHED** 2026-08-12. **166/166 assertions, reproduces bit-for-bit.** image `876cf2be5800f0f8…` rwd `7e9a65f11cab4ffc…`. 🛑 **AN INSTRUMENT, EXPLICITLY NOT A FIX** — *"no candidate fix lever survived this session's controls"*, and the two builds before it (V93, V94) were both cut on a mechanism story that measurement refuted **after** the flash. **PROBE:** CAN 427 ← `gp-0x6b70` (LSB **12.8 ct**, no-clip `8192×5>>6=640≤1023`) + `0x14A` ← **`gp-0x374c >> 4`** using **Honda's own shift `@0x38236`**, saturating at 12288 (LSB 2048) — deliberately below the 68,614 structural bound because **neither cell has EVER been on the wire**; saturation duty + 8-code histogram are reported outputs. `b3` = `gp-0x674e < 28` settles **RULE 7** for the authority curve. **WHY THIS PAIR:** `gp-0x6b70` is a **PID REFERENCE THAT GETS SUBTRACTED**, not an aggregator addend ⇒ **no `FUN_00038148` weight can be moved until the LERP's local slope is measured**; the pair yields it because `d(gp-0x6b70)/d(gp-0x374c>>4) = −f'` **independently of `sign(iVar6)`/`gp-0x6bfe`/`gp-0x6bfa`** (the two sign factors square to +1). **PRE-REG: TWO SLOPES, NEVER MERGED** — S1 lag-0/1 = open-loop `f'` (its SIGN is the decisive output), S2 coherence-weighted = closed-loop incl. `L`. 🛑 **S1 CI spanning zero means "NOT RESOLVED", not "zero"**, and the weight class stays blocked. **IDENTITY** `byte7 b6 ≡ 1`; V94 carries the 74-B V90 cave and cannot write byte 7. ⚠ Separation from **V92** is **BELIEF** (V92 also writes byte 7; separator is a measured 0.0000 duty, not an impossibility) — a self-declared regression against the builder's own earlier cut. ⚠ **Freeze exclusion is a WIRE-SIDE HEURISTIC, not a gate read**: `FUN_00038148`'s `gp-0x67fa` gate is **unreadable by a cave** — its boolean is never stored (`r28` written `@0x221D6`, tested `@0x22672`, no store in `[0x2214A,0x22700)` sources it), recomputing needs **Format IX `shl reg,reg,reg`** (the class that bricked V24/V27/V48B), and the affordable `4≤s≤11` superset **would silently read "live" while the pair is frozen — worse than no bit** |
| ~~**V95**~~ | — | 🛑🛑 **VACATED — A BURNED NUMBER. NEVER REUSE IT.** Three artefacts wore it inside two hours while the spec moved; retiring it is cheaper than disambiguating it forever. `build_v95_tva.py` was **deleted**. | **DEAD hashes, written out so a grep finds them:** lane build (`6B4C`/`6B4E`) image `ad8643c1f37ac128c57606c60ad6225420884f3fa250ffd978f9efa6a5fb7faf` / rwd `3a791446c268b2b0660e4035a82c51f93572b662faa6225167f16e331277c9d6` — **deleted from disk**; and the pair build briefly numbered V95, image `876cf2be…` rwd `7e9a65f1…`, **same bytes, now correctly V96**. ⊕ The lane design is **not lost and is V97 material**: `gp-0x6b4c`/`gp-0x6b4e` are the **disjoint partition sums of the same 11-slot request array `gp-0x62f8[]`** (split by the mode bytes at `0xC4124` = `00 00 05 00 05 05 00 00 00 05 00`), **±10240 each — 5× and 10× the other two lanes** — and `gp-0x6b4c` is **also a direct unity-weight aggregator summand** (`0x3AA3E`, both branches) so it reaches the motor by **both** paths. **Both gates are structurally always open** (producer clamps to exactly ±0x2800; the gate passes ±10240 inclusive) ⇒ **the V64-class null is excluded BY ARITHMETIC.** |
| **V94** | flown V90 | **V93's 22 cal bytes, IDENTICAL** + **one code byte**: `0x55E10` `sar 0x3,r6` → `sar 0x1,r6` (`a3`→`a1`), the CAN 427 packer | 🛑🛑 **FLEW route `7d`, 2026-08-12 — AND IS STILL ON THE CAR. THE OPERATOR STOPPED DRIVING IT.** *"Made the stuttering and grinding worse, by a lot. So much so that it vibrated the entire car, and I decided it was not safe to drive."* **No fault of any kind.** Measured: motor acceleration **3–7× up above 9 Hz**; column-torque↔wheel-rate coherence at **18–31 Hz the highest of any drive in the corpus**. 🛑 **THE PREMISE WAS BACKWARDS.** `gp-0x6b26` was cut 6× against V92 on *"it is apparent inertia, nothing is dissipated, lowering is strictly safe on both binding bounds"* (`build_v94_tva.py:106,117`). Measured afterwards on **two independent drives**, ω-partialled with a shuffled control: the **delivered** lane sits at **`+137°/+139°` vs WHEEL rate at 6–9 Hz** ⇒ |cos| = 0.73 ⇒ **`+518/+565` counts of POSITIVE `Re(Z)`. It is a REAL 6–9 Hz DAMPER and V94 removed 6/6ths of it.** ⇒ **the first measured `d(symptom)/dK` this lever has ever had, and the sign says UP.** ⊕ The code byte is **EXONERATED** (instruction-level walk; openpilot's `steeringTorqueEps` dead-ends in `carstate.py`) — the regression is the **calibration**. ⊕ The desk figure *"+75°, 26 % dissipative, structurally cannot damp 6–9 Hz"* is ALSO WRONG and retired: that was the *producer's* filter phase vs *motor* rate. See `memory/accord-v94-flew-and-the-lane-is-a-damper.md` and `memory/feedback-reducing-a-gain-is-not-a-safety-class.md`. **Build record:** 133/133 assertions, reproduces bit-for-bit. image `cd971c05d483fe9c…` rwd `3feccc09d8cbdd05…`. 🛑 **V94 EXISTS BECAUSE V93'S INSTRUMENT IS NOT SIZED FOR V93'S OWN EDIT**: 427 packs `wire = (\|gp-0x6b26\| × 5) >> 3` and V93 divides the cell by 4, so on route 78's measured distribution **87.5 % of engaged frames would land on wire ≤ 1** — the primary endpoint measured at 1–2 LSB. `sar 3 → sar 1` is exactly ×4 and CANCELS the ×0.25: V94's wire distribution reproduces route 78's as-flown one (p75/p90/p95/p99/max **5/10/17/37/137** vs **5/10/17/38/138**), making the ratio test **quantisation-identical**. ⊕ And since `gp-0x6b26 = −K·gp-0x6c2c` with **K known**, full-resolution 427 makes the **EPS-motor ACCELERATION recoverable** — the lever's input, never telemetered on any build — with **no cave change**. ⚠ Clips at `\|gp-0x6b26\| ≥ 409` = 80 % of the rail: an EARLIER alarm, not a lost one. ⊕ `r6` is consumed only by the `jarl 0x49A90` two instructions later, so the byte has no other reader. 🛑 **V93 is NOT superseded and its hashes are NOT dead** — it is a valid artefact that simply measures itself poorly; V94 took a new number precisely to keep V93's published hashes meaningful |
| **V93** | flown V90 | 🛑 **THE FIRST BUILD EVER TO *LOWER* `0xCBE74`.** mode 24 (MANUAL) Y ×0.50 → `(-4915,-2867,-983)` · modes 26/27 (ENGAGED) Y ×0.25 → `(-2458,-1434,-492)` · **both non-LERP fallbacks ×0.75** — `0xC640A` −8192→−6144, `0xC640C` −3277→−2458. 22 cal bytes, 33 differ, 3 CRC trailers. V90 cave + 427=`gp-0x6b26` carried byte-identical | **BUILT, VERIFIED, UNFLASHED** 2026-08-11. 126/126 assertions, reproduces bit-for-bit. image `779180f8aaf88f29…` rwd `9c93dca63e9e404e…`. **Rationale REVERSED**: `FUN_00041464` traced to the instruction — `gp-0x6c2c` is a FIRST DIFFERENCE of filtered motor rate (`sub r7,r9` @`0x41602`) ⇒ **ACCELERATION**, so `gp-0x6b26 = −K·α` **ADDS APPARENT INERTIA and dissipates nothing**. `build_v91_tva.py`'s *"genuinely DISSIPATIVE, it opposes motor rate"* is **WRONG**. Three distinct factors make the flight a **branch discriminator**: engaged `\|gp-0x6b26\|` ratio vs route 78 of **0.25** ⇒ mode 26 live · **0.50** ⇒ the car reads **mode 24 in both states** (the suspected V91/V92 null cause) · **0.75** ⇒ a fallback is live · **1.00** ⇒ stop. ⚠ The MANUAL negative control is **deliberately spent**. ⚠ Does NOT address the 2–26 Hz anti-damping |
| **V76** | V38 | FactorC m26 `[566,566,566,908]`, FactorE `X=[0,119,…] Y=[0,300,539,927]`, `k`=1.3866 | **FLEW route 65, clean.** ⚠ The V38 rebase silently reverted **seven** things, not three — see the note below the table |
| V78 | V76 | FactorE `Y[1]`→449, dose 206 | built, **never flown** |
| V79 | V78 | `Y[1]`→897, `Y[2]`→912, `k`=4.16 | built, superseded |
| **V80** | V79 | + flat FactorC `[566]×4`, `0x454FE`→`B5` | **FLEW route 66. WORST GRINDING EVER**, no fault. 2.09× broadband HF lift + a 30 s 27.4 Hz limit cycle |
| **V81** | flown V75 | `0xC407E` 850→511, friction ×1.5→stock | **FLEW route 67. FAULT-FREE** — the clamp revert worked. Grinding present (no grind-#1 fix was on board) |
| **V83a** | flown V81 | FactorE m26 → Honda's ramp (`k` 1.5798→0.2265) · `gain_A` rec0/rec1 → stock · **`0xC63A0` 2048→1024** | 🛑🛑 **FLEW route 68 — THE WORST BUILD IN THE MODERN LINEAGE FOR BOTH SCORED SYMPTOMS**, and fault-free. **grind #1 2.674× V81 [1.956, 3.885]** (null [0.63, 1.55], 10/10 cells > 1) · **micro-ratchet 1.526× [1.174, 2.019]** (null [0.69, 1.40]) · ring **FLAT 1.021** · 40–49 Hz 1.136, inside. 🛑 **Its own pre-registered falsifier FIRED — ring 1.123 vs V76, indistinguishable ⇒ THE DAMPER-DOSE MODEL OF THE 26–31 Hz RING IS FALSIFIED.** ⚠ It also left **mode 27 carrying V81's whole damper package** (a second ENGAGED column on this car) |
| **V84** | flown V83a | **Lever B** `0x3AA96` `C5`→`FB` + `0xC6446` 512→**5244** · **damper → Honda** in BOTH engaged columns: FactorC `Y[0]` 566→0 at `0xD77DA` (m26) and `0xD77EE` (m27), FactorE m27 `0xD7822`/`0xD7824`/`0xD782C` → **60/400/140** | 🛑 **FLEW AS ROUTE `6d`, 2026-08-09** (this row previously read "BUILT, VERIFIED, UNFLASHED" — the **same record defect V83a's handoff flagged one build earlier**). 68,235 frames, 682.4 s, **79.71% engaged**, 0–113 km/h, **fault-free** (`STEER_STATUS` {0: 68,219, 3: 17}, 0 DTC-active, 0 sentinels). 🛑 **FIXED NOTHING — operator verbatim: "None of these have been fully fixed in V84."** ONE BAND MOVED: 26–31 Hz burst duty **V80 96.6% → V81 25.1% → V84 2.54%**, longest ring 18.29 → 11.25 → **1.34 s**, on **3.4–4.9× the exposure** (151 s engaged >80 km/h vs V81's 44.8). Negative control and IMU falsifier both pass. ⇒ **RETRACTS V83a's "damper-dose model of the ring is FALSIFIED"** — V83a left mode 27 carrying V81's whole damper and had 19.2 s of highway, i.e. it never removed the damper and could not have tested it. **S1** 0.509× V83a [0.396, 0.695] (null [0.60,1.62]) but **1.10× V81 after the negative-control correction** ⇒ Lever B only undid V83a's regression. **S2 1.548× V67, outside null — FAIL. S3 FAIL** (operator). **S4 2.052 [1.089, 3.936] — FAIL and REVERSED.** ⊕ **Orchestrator byte-check: V84 ≡ V67/V68 at EVERY grind-relevant cell** except `0x454FE`, which cannot execute ⇒ **the rate lane is delivering exactly V67's result and that is its ceiling.** 🛑 The §7b grind-#2 protocol got **5.1 s of a 166 s floor (3.1%)** — its "0 events" is uninterpretable, the fourth build in a row to miss it |

| **V85** | flown V84 | **ONE cell**: `0xC40BC` 600 → **6000** (`tp+0x50BC`), the Coulomb-relay normaliser in `FUN_0003b8f6` (1 kHz plant-model estimator) + a 4-rung `0x14A` byte-4 probe on `gp-0x6abc` / `gp-0x6ae2` | ✅ **FLEW AS ROUTE `6e`, 2026-08-09. FAULT-FREE — the cleanest flight in the modern lineage: `STEER_STATUS` = {0: 43,641}, not one non-zero frame**, 0 DTC-active, 0 sentinels. 43,641 frames, 438.2 s, **82.02% engaged**. Identity with no free parameter (`b3` 1.00000, `b7` 0.39481 vs V84's 0/68,236, nesting `b6⇒b7` and `b5⇒b4` 0 violations). ✅ **THE LEVER DELIVERED**: relay saturation **39.5% → 11.1% overall, 33.3% → 4.6% engaged (7.21×)**, both pre-registered duty predictions hit. 🛑 **AND THE BANDS ARE A CLEAN NULL**: 6–9 Hz **1.088 [0.746, 1.451]** · 18–22 Hz **1.347 [0.947, 1.758]** · 40–49 Hz 1.002 · negative control 32–38 Hz **1.007** · 1–4 Hz validity 1.005 · IMU roughness 0.958 (V85's road *smoother*), against split-half nulls **[0.63, 1.50]** wide. **Operator: grinding "a little better", micro-ratcheting "barely, perceptibly better (somewhat unsure)", RATCHETING STILL UNFIXED, no grind #2 reported.** 🛑 **EXPOSURE-LIMITED: 35.6 s engaged ≥50 km/h, 22.4 s ≥80 (V84 had 370.8 / 158.1) ⇒ V83a-class ⇒ NO highway and NO 26–31 Hz verdict may be scored on this route, and its damper abort criterion could not have fired.** 🛑 **`0xC40BC` IS NOW FROZEN AT 6000** — not because `N` is flat there, but because the ring rides on a bias 5–10× its own amplitude so the **biased** describing function is the right instrument, and it reads top-decile pinning **0.0000 (18–22 Hz)** / **0.043 (6–9 Hz)** after a delivered **20.3×** reduction. 🛑 **REFRAME: the pathology was PARAMETRICALLY SWITCHED DAMPING, not harmonic injection** — at cal 600 the damping switched fully off on **87% (6–9 Hz) / 96% (18–22 Hz)** of symptom frames |
| **V86** | flown V85 | **ONE cell**: `0xC40D4` 573 → **286** (`3D 02` → `1E 01`, `tp+0x50D4`) — the **command-branch EMA** in `FUN_0003b8f6`, α 0.1399 → 0.0698 + a 5-rung `0x14A` byte-4 probe on `gp-0x6b70` / `gp-0x67ab` | 🛑 **FLEW AS ROUTE `6f`, 2026-08-09** — this row previously read "BUILT, VERIFIED, UNFLASHED"; **fifth instance of the same record defect** (after V83a, V84, nearly V85, and V86B below), corrected 2026-08-09 late. **FAULT-FREE**: 23,058 frames / 232.3 s, 61.4% engaged, `STEER_STATUS` {0: 23,048, 3: 11 (low-speed lockout)}, 0 DTC-active, 0 sentinels. 🛑 **PARKING-LOT ONLY — v_max 5.38 m/s, 0.0 s engaged ≥50 km/h ⇒ NO highway and NO 26–31 Hz verdict may be scored on this route.** 🛑🛑 **THE PRE-REGISTRATION BELOW IS FALSIFIED, AND WELL-POWERED**: `f(V86)/f(V85)` = **1.001 [0.976, 1.060]** — CI **disjoint** from the pre-registered [0.797, 0.875] and including 1.00; the line stayed at **8.00 Hz**, five independent statistics all null. The falsifier *could* fire: a faithful shift surrogate recovers ×0.797/×0.843/×0.875 with CIs excluding 1.00, smallest resolvable shift **×0.94** against a requested ×0.843 ⇒ **2.6× margin**. Lever in force three ways (`0xC40D4` = 286 byte-verified from the flown image, gate `b4` duty 1.0000, residual non-zero 99.88%). ⊕ **The bound is worth more than the null: the build-to-build floor at constant α is 14× the entire effect.** Operator: grinding and micro-ratcheting *"maybe a smidge better, if at all"*; **ratcheting definitely perceptible**; his second grinding complaint present. ⇒ **the linear-loop hypothesis is dead; the ~8 Hz ratcheting is a lightly-damped RESONANCE (Q ≈ 14–29) and the firmware search on it is CLOSED.** The pre-registration is kept below **as written**, for provenance. — image sha256 **`b8d81ebf9aae4ce27b489687a6d2dc1b222214accc0b128068b31ce41515d2f8`**, rwd `39990-TVA,A160-V86-V85BASE-CMDEMA.C40D4.286-PROBE.6B70.SIGN-GATE.67AB-0x13000-0x100000.rwd` sha256 **`9d237dfc5fbfde27c7843bfa47c6f0e7eb6925819efab94f2aefa4bd4798c370`** (986,042 B). **Orchestrator-verified from disk: 5 runs / 68 bytes vs V85, ZERO unattributed** (2 control + 62 cave + 4 CRC); cave byte-identical to spec; 14 frozen u16 + 4 frozen bytes correct; `[0xC5000,0xC5FFC)` identical to base **and** stock. ⚠ **RE-CUT ONCE** — the first cut shipped `a932` (b5 = 512) after an orchestrator threshold reversal crossed the builder mid-cut; caught from the built image's bytes **before any hash was reported**, both defective files **deleted outright**. 📋 **METHOD RULE: verify a cave against the FINAL spec, not against what the builder was handed.** 🛑 **A DIFFERENT LEVER CLASS FROM EVERYTHING SINCE V38 — phase/lag, not nonlinearity.** It is a **FREQUENCY** experiment: it moves the loop's −180° crossing **7.79 → 6.2–6.9 Hz**, pre-registered as the **RATIO `f(V86)/f(V85) ∈ [0.797, 0.875]`** (median 0.843, min/max over Q ∈ [2,40] × delay ∈ [0,10] ms) = **3.3 FFT bins at NFFT 256 / fs 100 Hz**. **CONFIRMED** if the peak lands in [6.2, 6.9] Hz with the ratio CI excluding 1.00; 🛑 **FALSIFIED — the linear-loop hypothesis dies — if it stays at 7.79 Hz**; ⚠ **AMBIGUOUS, explicitly not a null**, if the ratcheting is too weak to locate a peak. **Why a frequency claim: amplitude ratios have failed four builds running and the split-half null is [0.63, 1.50] wide.** **286 not 1146** (same swing, other direction) because 286 moves *away* from the 12.8 Hz plant mode and **lowers** estimator HF gain to 0.650× @20 Hz / 0.585× @28 Hz where 1146 would raise it 1.216× / 1.355×. 🛑 **It CANNOT limit max LKAS angle rate, proved: an EMA has `\|H(0)\| = α/(1−(1−α)) = 1` exactly for every α** (verified numerically at α ∈ {0.0349…0.9998} → 1.000000000000); only transient tracking changes. **Mode-proof**: 573 appears exactly once in `[0xC4000, 0xC4200)` and no stride S ∈ [2, 0x400) repeats it. **Probe**: `b7` `gp-0x6b70 < 0` · `b6` `gp-0x6b70 != 0` · `b5` `\|gp-0x6b70\| ≥ **64**` (`sar 0x6`) · `b4` `gp-0x67ab < 2` (the aggregator gate) · `b3` fingerprint. ⊕ **64 not 512 because `gp-0x6b70` is MEMORYLESS**: the band `(0,64)` fills only if the LERP *ramps*, so the **`b5/b6` ratio is a second, independent relay-vs-linear discriminator** — ratio → 1 ⇒ a **plateau** (relay-like), ratio ≪ 1 ⇒ it ramps (a relay cannot). 🛑 **`b5 ≈ b6` is a POSITIVE result, not a saturated rung.** At 512 that band fills under any shape and carries nothing. **`b7⇒b6` and `b5⇒b6` are exact DUALS of V85's `b6⇒b7`** ⇒ one `b6 ∧ ¬b7` frame refutes V85, one `b7 ∧ ¬b6` frame refutes V86 ⇒ identity is free. ⊕ `b7`+`b6` is also a free **relay-vs-linear discriminator**. ⚠ **V86B is a SECOND artefact, built alongside — see its own row.** |
| **V86B** | flown V85 | **TWO cells**: `0xD77DA` FactorC **m26** `Y[0]` **0 → 908** and `0xD77EE` FactorC **m27** `Y[0]` **0 → 875** (each := that record's own `Y[3]`), via ptr array `0xC9E9C`. `0xC40D4` stays **573**. Same cave with `b5`/`b6` weight-swapped for identity | 🛑 **FLEW AS ROUTE `70`, 2026-08-09 — AND IT IS THE BUILD ON THE CAR RIGHT NOW.** This row previously read "BUILT, VERIFIED, UNFLASHED"; same record defect as V86 above, corrected 2026-08-09 late. **FAULT-FREE**: 21,428 frames / 216.0 s, 43.0% engaged, `STEER_STATUS` {0: 21,409, 3: 20}, 0 DTC-active, 0 sentinels. 🛑 **PARKING-LOT ONLY — v_max 5.97 m/s, 0.0 s engaged ≥50 km/h**, and only **1.5 engaged minutes** ⇒ underpowered for Q by construction. Operator: *"still present, dampened I think"*, **ratcheting definitely perceptible**, second grinding complaint present, plus *"extra dampening on LKAS and in general at slow speed"* — **the predicted heavier-at-creep cost is CONFIRMED as felt.** 🛑 **The pre-registered ≥50% / <20% recovery test CANNOT be scored** — the route has no highway arm for its own structural negative control. ⚠ **`STATE.md`'s "V86 ↔ V86B are single-variable against each other" is FALSE** — they differ in **two** control cells (`0xC40D4` **and** the FactorC pair); the single-variable pairs are V86-vs-V85 and V86B-vs-V85. — image sha256 **`b2dfe9ffc3fd2c5a786a7adb1d281e2841143756dccf766b84f292b3f9416d8d`**, rwd `39990-TVA,A160-V86B-V85BASE-FACTORC.M26.M27.Y0-PROBE.6B70.SIGN-GATE.67AB-0x13000-0x100000.rwd` sha256 **`350c7d2fe1460a06c4f9efa29e5bc03d50ad391a77d56a2ea2165ed4ba337de5`** (986,042 B). **Orchestrator-verified: 7 runs / 74 bytes, zero unattributed** (4 control + 62 cave + 8 CRC in **two** blocks `0xC4FFC`+`0xD7FFC`); m24/m25 byte-stock ⇒ **engaged-only by construction**; FactorE `X[0]` = **60**, untouched. **V86 ↔ V86B differ by 16 bytes ⇒ single-variable against each other.** **WHY**: two independent lines support the damper-at-creep account — cross-build dose–response **3.2×** separation (ρ = −0.679, control 1.07×, dose crosses build order twice so chronology cannot explain it) and a stratified differential test, wheel-order-clean and speed-bin matched: **V85/V81 below 35 km/h = 3.876 [1.892, 6.740]** vs control 1.470, above 35 km/h 1.529, **control-corrected LOW/HIGH = 2.00**, fine profile **4.51× at 0–9 km/h** → 2.50 → 1.86 → flat above 35. **RING-FREE BY LERP ARITHMETIC, not statistics**: `FactorC Y[0]` affects the curve only below `X[1]` = 3840 ct = **59.9 km/h**; delta at r=99 is **+27.8 ct at 5–35 km/h, +11.1 at 50, EXACTLY 0.00 at 60/80/100/140** — the ring was measured **above 80**. The **relay index is a RATE-axis property**, untouched ⇒ stays at Honda's **0.00** vs V81's 1.50 and V80's 3.27. **GATE 2 easier than V86's**: a memoryless gain ⇒ **every pole in the image bit-identical**; bounded by the ceiling `0xC6158` = 512 ct = **2.00% of the aggregator's ±25600**. 🛑 **KNOWN, DELIBERATE, STRUCTURALLY FORCED: the row becomes NON-MONOTONE** — m26 `[0,234,429,908]` → **`[908,234,429,908]`**, a V-shaped speed surface; Honda ships monotone in all 32 records and `assert_factor_monotone` **fails**. Unavoidable: monotonicity needs `Y[0] ≤ 234` = **2.2% of V81's dose = inert**; `Y[0] = Y[3]` = **10.1%** = the intended test; lifting the upper breakpoints instead restores monotonicity but pushes into the ring regime ⇒ **the non-monotonicity is the PRICE of the ring-free property**. **HONEST LABEL**: a ring-free test of whether the damper's zero point is special — **moderate-to-low probability of fixing the ratcheting, and it WILL make the wheel slightly heavier when engaged at low speed** (≈10% of V81's flown 138 ct, engaged-only). **PRE-REGISTERED**: the line falls toward V81's below 60 km/h and is **bit-identically unchanged above 60** (a *structural* negative control); **≥50% of the V84→V81 3× step recovered ⇒ threshold-at-zero, the damper is worth re-sizing; <20% ⇒ graded, k ≥ 4.2 needed, unreachable without V80's ring ⇒ retire the damper as a ratchet lever permanently.** Abort: any 26–31 Hz burst-duty rise above 2.54%. ⚠ **The FactorE `X[0]` 60 → 12 variant is WITHDRAWN — structurally vacuous at creep** (FactorC `Y[0]` = 0 below 34.97 km/h zeroes the product) and it would land its whole 3.02× effect at highway speed, i.e. the ring regime |

| **V89** | flown **V88** | **`0xC40D2` 102 → 204** — K1, the `|model|`-proportional **modelled Coulomb friction** in `FUN_0003b8f6`, **2.000×** · `0xC4B38` `6894`→`1e95` cave probe → **`gp-0x6ae2` = friction × 1024** · `0xC4B46` `a8`→`a6` rung ±64 | **BUILT, VERIFIED, UNFLASHED 2026-08-09.** image `6eae6826…`, rwd `cdce053e…` (986,042 B). **4 runs / 8 bytes, ZERO unattributed**; 50/50 CRC on image, readback and the shipped file re-read from disk. 🛑 **A DIFFERENT CLASS FROM EVERY BUILD SINCE V38** — V38–V52 authority/filters/poles/caves · V53–V61 telemetry + lane mutes · V62–V73 the rate lane · V74–V83a the damper · V84–V86B damper reverts + phase · V87 subtractive · V88 Lever B. **Every one moved the LKAS COMMAND or a lane that SUMS INTO it. V89 moves neither — it edits the PLANT MODEL that a disturbance observer compares the assist against** (`FUN_0003b8f6` → `FUN_0003bc20` → `FUN_00038148`, `residual = MODEL − ACTUAL`, `gp-0x6b70 = sign(res)×LERP(|res|)`). **WHY:** engagement multiplies 6–9 Hz by 2.8× band-specifically (+0.413 [+0.146, +0.667]) and **does NOT grow with wheel rate** (+0.022 [−0.070, +0.116]) ⇒ the target is a CONSTANT GAIN and **no LKAS rate limiting is involved**; the only friction dose ever flown (`0xC40BC` 600 vs 6000, within-route) gives **2.89× vs 6.58×** engaged/manual ⇒ **less friction, MORE ratchet, contrast +0.682 [+0.213, +1.166]**; and driver GRIP damps the same band (−0.655 vs control −0.266, disjoint). ★ `0xC40D2` = **1 reader / 0 writers**, virgin on all 88 builds. 🛑 `0xC4080` (K0, the NEVER-RAISE pure-relay hazard) **untouched at 0**. 🛑 **HONEST:** the dose DIRECTION is measured; that K1 acts like the gate is **BELIEF** (the gate confounds magnitude with relay-ness). ⚠ **COST: may feel notchier/heavier on-centre — the instrument cannot see that.** |
| **V87** | **V38** (not V86B — a deliberate REBASE) | **6 control edits, 11 bytes, + the V86B cave verbatim.** `0x2A1F0` `6c74`→`d07c` (V57 repoint) · `0xC646C` 3564→**891** · `0xC6CD0` blank→**3564** (V57-style private 4× LKAS; forward gain **unchanged at 4.000×**, four FEEDBACK readers un-boosted) · `0x454FE` `ba`→`b5` (V42 ratchet fix) · `0xC62EA` 320→**0** (steer to zero) · **`0x55DF2` `e893`→`6894` — 427 `MOTOR_TORQUE` source `gp-0x6c18`→`gp-0x6b98`** · `0x55C0E`+`0xC4B34` = the flown V86B 62-byte telemetry cave | ✅ **FLEW AS ROUTE `71`, 2026-08-09** (`75604b0a432fdc89_00000071--ac50da2a6a`, cache `_cache_r71/`). **FAULT-FREE**: 23,765 frames / 239.6 s, 52.4% engaged, 0 sentinels, no EPS event in 1,262 `onroadEvents`. 🛑 **PARKING-LOT ONLY — v_max 5.91 m/s, 0.0 s engaged ≥50 km/h, 2.1 engaged minutes** ⇒ no highway verdict, and underpowered for any cross-build ratio (in-route split-half null on 6–9 Hz power is **[0.18, 5.51]**). **Operator: grinding, micro-ratcheting AND ratcheting all present** — which is the PREDICTED result: V87 is byte-stock at **all four** measured grind-#1 addresses (`0x3AB76`/`0x3AC20` = `aa`, `0x3AA96` = `c5`, `0xC6446` = 512), verified from its own image. ✅ **THE PROBE FIRED, and it is the kit's biggest instrument gain since the cave**: 427 `MOTOR_TORQUE` went **56.5% / 67.0% non-zero and 297 / 240 distinct on routes `6f` / `70`** (V86 / V86B, re-measured this session as controls) to **99.02% non-zero, 946 distinct, range [0,1023], railing 3.23%**. **`\|gp-0x6b98\|` engaged: median 208 counts, p90 966, p99 ≥1637 (railed 2.35%); 6–9 Hz ripple rms 29.0 / p-p 162 counts** ⇒ **the "~120 counts p-p" assumption was low by 1.35×, NOT by the 5× STATE.md feared — that unknown is CLOSED.** 🛑 **THE FORK, and its instrument limit:** on rectification-transparent unclipped engaged windows the ~7.7 Hz line reads **prominence 12.9 in the column torque (50% of windows above the white-noise p95 floor) and 4.0 in the delivered command (7.1% — chance)**; openpilot's command 2.96 / 7.1%. **But the link is real and frequency-selective** — pooled coherence cmd↔column **0.439 at 7.79 Hz vs a shuffled-pairs control of 0.178** (background 0.03–0.16), and per-window corr(column line, command line) = **+0.62**, the command's prominence rising to 12.7 in the top ratchet quartile. ⇒ **a lightly-damped mode driven by BROADBAND command content, not by a commanded tone** ⇒ the lever class is *"less broadband HF in the delivered command"*, **not a notch**. ★ **SPEED-MATCHED (2–4 m/s) engaged/manual band rms of the delivered command: 0.5–3 Hz 0.42× · 3–6 Hz 0.73× · 6–9 Hz 1.73× · 9–12 Hz 1.76× · 12–15 Hz 1.79× · 15–22 Hz 3.37× (CIs DISJOINT)** — engagement REMOVES low-frequency command motion and ADDS high-frequency motion, most of all in grind #1's own band. 🛑 **Two readings from the scoring session were WITHDRAWN by their own controls**: (1) a "differentiator" transfer rising 9× with frequency — at coherence 0.035–0.077 against a 1/n_avg = 0.043 null, `sqrt(Pyy/Pxx)/sqrt(n_avg)` reproduces it in **all seven bands** (ratio 0.89–1.08); (2) the phase-randomised surrogate as a "no line" control — phase randomisation **preserves `\|X(f)\|`**, so it preserves a line's power and the comparison is near-tautological. 🛑 **PROBE DEFECT FOUND, fixed in V88**: 427 carries `\|gp-0x6b98\|`, and rectification was transparent in **0 of 42** 10.28 s windows (14 of 37 at 5.14 s) — at creep the command crosses zero constantly, folding 7.79 Hz to 15.58 Hz. ⚠ **Nyquist: 427 runs at 49.81 Hz, so nothing above 15 Hz is claimable from it** — a 28 Hz object aliases to 21.8 Hz. On the 100 Hz channels the 24–32 Hz content is 6× below 15–22 Hz, so the shelf is *mostly* real, but not separably so. ⊕ `gp-0x6b70` (the Coulomb friction compensator) measured live: non-zero 99.80%, `\|v\|`≥64 in 93.84%, negative 67.19%, aggregator optional-term gate **open 100%** — image sha256 **`27530836dfc121ecf9f62a4dd136abc79484ef2e12af54f55591ac71c334e034`**, rwd `39990-TVA,A160-V87-V38BASE-V57GAIN-RATCHET454FE-STEER0-PROBE.427.6B98-0x13000-0x100000.rwd` sha256 **`997002f01aa7b5bfe0ac32b8f17396a593a3e298ea11919ea2331b718f6e85f6`** (986,042 B). **10 runs / 85 bytes vs the V38 base, ZERO unattributed**; restoring the attributed set reproduces V38 bit-for-bit; CRC 50/50 on the built image, the readback AND the shipped file re-read from disk; probe instruction re-decoded from the BUILT image as `ld.h -0x6B98, gp, r6`. 🛑 **A DIFFERENT CLASS FROM EVERY BUILD SINCE V38 — it is the first SUBTRACTIVE build in the lineage.** V38–V52 authority/filters/poles/caves · V53–V61 telemetry + lane mutes · V62–V73 the rate lane · V74–V83a the damper · V84–V86B damper reverts and phase experiments — **all moved a control variable. V87 moves none.** It strips 49 builds of accumulated levers back to V38 and adds only the operator's two named mods plus 2 bytes that repoint a CAN TRANSMIT packer. 🛑 **HONEST LABEL: it will read as a NULL on the ratcheting, by design** (no damping, no filter, no new authority) — **if it moves the ratchet, the model is wrong, and that is itself information.** ⚠ **Feel change is real and comes from the REBASE**: V85's friction relay (`0xC40BC` 6000→600, a 10× revert), Lever B and V86B's engaged creep damper are all GONE. **WHY A MEASUREMENT BUILD:** every control lever this session examined is dead — `0xC63B8` refuted five ways, a shaper cave blocked by an EPS-disabling float twin (±5 counts / 10 ms → DTC 0xF00049), and `0xC646E`'s sizing figure is an unmeasured estimate. `\|gp-0x6b98\|` at 10 bits / 50 Hz sets the phase budget for ANY future filter (assumed 120 counts; the answer swings **5×**) and discriminates a passive resonance being driven from a closed-loop pole. ⊕ The real `MOTOR_TORQUE` is sacrificed deliberately — it is `\|value\|`, has no sign, and is not a delivered-torque or cut anchor for openpilot |

| **V88** | **flown V87** | **4 sites, 5 changed bytes.** `0x3AA96` `c5`→`fb` + `0xC6446` 512→**5244** = **LEVER B restored** (r24's arm becomes a flat 5244 while LKAS applies = **2.000×** the LERP) · `0xC4B38` `9094`→`6894` = the flown cave's probe source `gp-0x6b70`→**`gp-0x6b98`** (⇒ `b7` = **SIGN of the delivered motor command, at 100 Hz**) · `0xC4B46` `a6`→`a8` = cave `sar 0x6`→`sar 0x8`, magnitude rung 64→**256 counts** | ✅ **FLEW AS ROUTE `73`, 2026-08-09** (`75604b0a432fdc89_00000073--9380c74d52`, 11 segments, cache `_cache_r73/`). **This row is written in the SAME pass that scores the flight** — the method rule that was violated five builds running. **FAULT-FREE**: 61,161 frames / 613.4 s, **72.7 % engaged = 7.41 min**, `STEER_STATUS` {0: 61,147, 3: 15}, DTC-active duty **0.000000**, 0 sentinels, no EPS event in 1,786 `onroadEvents`. ★★ **THE ≥50 km/h DROUGHT IS OVER — 119.6 s engaged ≥50 km/h, 80.2 s ≥80, v_max 116.6 km/h**, against **0.0 s on each of the four prior routes**; highway = segments 4–5, both 100 % engaged. ★ **IDENTITY, parameter-free and triple-measured**: `b6 == (wire ≥ 160)` reads **0.9654** (raw-timebase, `r73-extract`) · 0.9560 (±20.1 ms) · 0.9654 (orchestrator, after correcting an off-by-one) against the V87 control **0.4022**, with **chance = 0.6028** from the marginals ⇒ V87 sits essentially *at* chance. Duty match 0.27330 vs 0.27334; edge-conditioned agreement **0.9901**; lag sweep peaks at lag 0. ★★★ **H1 CONFIRMED, AND THE OPERATOR'S CONSTRAINT IS MET BY MEASUREMENT** — speed-matched 2–4 m/s, engaged, unclipped, episode-bootstrapped: **`0.5–3 Hz` 1.192 [0.780, 1.812] = NULL** (orchestrator's independent crude estimator 1.121) · 3–6 Hz 1.165 · 6–9 Hz 0.859 · **9–12 Hz 0.604 [0.465, 0.943]** · **`15–22 Hz` 0.549 [0.407, 0.844]** (orchestrator 0.625). ⇒ **Lever B HALVED the delivered command's HF content while costing NOTHING in low-frequency steering authority.** **Aliasing excluded on two independent 100 Hz channels** (427's Nyquist is 24.9 Hz): `tq` 15–22 Hz **0.33×** and `rate_c` **0.31×**, while **28–35 Hz is FLAT (1.13× / 0.94×)**; column `tq` 15–22 Hz rms **259.4 → 84.6**. 🛑🛑 **THE ORCHESTRATOR'S PRE-FLIGHT HYPOTHESIS WAS REFUTED**: he predicted 15–22 Hz would **RISE**, reasoning that r24 is a differentiator whose gain Lever B doubles. **r24 is rate FEEDBACK inside the loop and `gp-0x6b98` is the loop's OUTPUT, not its input** ⇒ more derivative feedback = more damping = **less** HF everywhere in the loop. V87's engaged spectrum rising with frequency (29 / 29 / 52 ct rms) against a **flat** manual arm (~9) is the signature of an **under-damped closed loop at stock derivative gain**, not of a feedforward differentiator. ★★★★ **H2 — THE FORK CLOSED, AND IT CLOSED AGAINST THE FIRMWARE.** V88's `b7` sign bit allowed the SIGNED delivered command to be reconstructed and V87's rectification screen **dropped entirely** (75 unclipped engaged windows vs V87's 14 screened). Controls ran first: the sign bit flips at a median `\|cmd\|` of **36.8 ct = the 22.9th percentile** (a noise bit would sit at the 50th), `b5`/`b6` agree with the 427 magnitude in **99.56 % / 96.02 %** of frames, and end-to-end polarity gives corr(0.2–3 Hz signed cmd, column torque) = **−0.671** where the *rectified* magnitude gives **+0.030**. Result, white-noise p95 floor = 10.64 at nw = 512: **column torque prominence 11.17 [7.85, 16.30], above floor in 52.0 % of windows** vs **signed command 5.46 [5.12, 5.94], above floor in 13.3 %** (openpilot's own command 4.43 / 1.3 %). **Signed ≈ rectified (5.46 vs 5.62)** ⇒ **rectification was never hiding a line; V87's null was CORRECT and is now established rather than assumed**, and the specific worry that 7.79 Hz folds to 15.58 Hz is dead. Reproduced at nw = 256 and on the independent **100 Hz cave grid** at two window lengths. ⇒ **THE RATCHETING IS NOT A TONE THE EPS COMMANDS — it is a lightly-damped plant mode excited by broadband command content. No notch, and no phase lever at 7.79 Hz.** ★ **AND THE GATE-2 HAZARD MOVED**: signed-cmd↔column coherence² by band, against a shuffled-pairs control of **0.009 [0.001, 0.061]** — 2–4 Hz 0.038 · 6–9 Hz 0.123 · 9–12 Hz 0.090 · 12–18 Hz 0.133 · **18–24 Hz 0.310, the HIGHEST, above the ratchet's own band.** The command↔column loop is tightest in **grind #1's** band — exactly where Lever B just cut the column by 0.33× — so any future filter's stability cost lands at ~21 Hz, **not** at 7.8 Hz. (At 7.79 Hz specifically, coherence² = 0.343 vs the 0.009 control, `\|tq/cmd\|` = 6.24, phase −30.9°; the **rectified** channel returns 0.009 = *exactly* the control, so V87's 0.439-vs-0.178 was measured through a rectifier destroying most of the link.) 🛑 **WHAT THIS ROUTE CANNOT DO**: **zero manual frames above 20 km/h** ⇒ no engaged-vs-manual contrast is constructible at speed; **58.7 % of manual frames parked** (route 71: 58.9 %) ⇒ raw ratios still worthless; and the **cross-build 6–9 Hz comparison inherits route 71's [0.18, 5.51] split-half null** ⇒ **it CANNOT RESOLVE a ratchet change under ~3–5×. "The ratchet was unchanged" is NOT supported by this route pair — "cannot resolve" is.** ⊕ **Co-movement, not trade-off**: within V88, corr(log 15–22 Hz command rms, log 6–9 Hz column prominence) = **+0.364** (+0.263 speed-partialled, block-permutation **p = 0.016**) — HF command content and the ratchet line rise and fall **together**, refuting the orchestrator's "grind #1 and the ratchet trade off through r24". 🛑 **INSTRUMENT DEFECT FOUND THIS SESSION, kit-wide**: `z["t"] == z["raw14_t"][1:]` and `z["probe"] == z["raw14_b4"][1:]` in **all 13 caches** (`_cache_r5e`…`_cache_r73`) — the extractor appends `raw14_*` on every 0x14A frame but a ROW only after the first 0x18F. Pairing `t` with `raw14_b4` reads the cave byte **one frame (~10 ms) early = 28° at 7.79 Hz**; it cost the orchestrator's identity check 0.9437 instead of 0.9654. **Safe pairings are `(t, probe)` and `(raw14_t, raw14_b4)` — never cross the families.** Audit: `analysis-2020accord/audit_raw14_offbyone.py`. H2's own script was checked and uses the aligned pair ⇒ **H2 is unaffected.** — **artifacts re-hashed from disk at close-out and matching the record exactly** — image sha256 **`96b1e018d2058984ada1ba4add7ce42516d5ed9cab65c7be7db294c3d0ca47b8`**, rwd `39990-TVA,A160-V88-V87BASE-LEVERB.GATE6806.ARM5244-PROBE.427.6B98-CAVE.6B98.SIGN.MAG256-0x13000-0x100000.rwd` sha256 **`4955d80a763a364b30d82ba315e7f1a97873068399de1842f64864478130a2de`** (986,042 B). **6 runs / 15 bytes vs the flown V87, ZERO unattributed** (5 control+instrument + 2 written-but-equal + 8 CRC in two blocks `0xC4FFC`/`0xC6FFC`); restoring the attributed set reproduces V87 bit-for-bit; CRC 50/50 on the built image, the readback **and** the shipped `.rwd` re-read from disk; the build re-runs bit-identically after a docstring edit. 🛑 **NO CAVE IS CREATED, MOVED, GROWN OR SHRUNK** — the two instrument bytes are in-place edits inside the 62-byte payload that has now flown three times (V86, V86B, V87). ★ **THE NEW LOAD IS NOT HAND-ENCODED**: `24376894` is **byte-identical to the 427 packer's own `ld.h -0x6b98[gp],r6` at `0x55DF0`** on this very base — an instruction already proven on-car reading exactly that cell. ★ **THE `TVCA4` HAZARD CHECKED AND CLEARED** — `v66_v67_explained` derives the arm from **mode-10** records and this car reads **24/26**, which has already produced three byte-stock builds. Re-derived from the image's own pointer arrays: **mode 24 ≡ mode 26 byte-identical in all four `gain_B` arrays**, mode 10 differs by ≤2 counts (0.09%), and the LERP at grind #1's operating point is **2622 in all three** ⇒ **5244/2622 = 2.0000× exactly on the car's real records.** ⚠ a SCALAR arm against a CURVE: **1.77×–2.55×** across the LKAS-on regime. 🛑🛑 **RECORD CORRECTION — `0xC6444` (the "decoupler") IS FALSIFIED, NOT UNTESTED.** `accord-rate-lane-builds-were-never-single-variable` calls raising it *"UNTESTED: a candidate"*; the cross-image matrix in this build shows **`0xC6444` = 3072 has flown, as V71c** (= `V67 + 0xC6444 512→3072 + 0x454FE`, nothing else), and `LEDGER-V38-TO-V84.md:236` records the result: grind #1 `e_18-22` **223 vs V67/V68's 109, excluded HIGHER (P = 0.0215)**; **grind #2 came back** (7 bursts, 44.31 Hz, p99 = 12.2× any non-bursting build, vs V67/V68's zero); **ratchet 8,521 ct p-p = the corpus RECORD.** ⇒ **the 6× r26 cut is LOAD-BEARING in Lever B, not a defect in it.** `0xC6444` stays at Honda's 512 and is **not** a V89 candidate. 🛑 **HONEST LABEL — NOT "this fixes the grinding".** Lever B has flown **seven times** (V67, V68, V71c, V84, V85, V86, V86B); the record calls it *"CONFIRMED-FIX, AT ITS CEILING … tops out at V67's level, which the operator still calls grinding"*. V88 does not beat that ceiling. It (1) **puts the car back to the best state the kit has measured**, which V87's V38 rebase deliberately gave up, and (2) **makes Lever B's MECHANISM observable for the first time** — every prior Lever B flight was scored on the column torque, an OUTPUT; V87's probe now exposes the delivered command, so V88-vs-V87 is a single-variable A/B on the thing Lever B actually changes. **It is NOT a ratcheting lever.** ★ **PRE-REGISTERED** (see the handoff): Lever B must **CUT the delivered command's 15–22 Hz band rms**, measured on V87 at **3.37× manual, CIs disjoint**; a null there refutes the "broadband HF in the command drives a lightly-damped plant mode" reading, which is worth more than another attenuation point. ★ **IDENTITY, parameter-free, control already measured**: on V88 the cave and the 427 packer read the SAME cell, so per frame `b6 == (MOTOR_TORQUE ≥ 160)` must hold; on route `71` (V87, cave on `gp-0x6b70`) that predicate agrees **0.402** of the time ⇒ **~1.00 means V88 flew, ~0.40 means V87 did** |

🛑 **RECORD CORRECTION, 2026-08-11 — the V89 row above still reads "BUILT, VERIFIED, UNFLASHED". IT
FLEW.** V89 flew as **routes `75` and `76`**, both fault-free, 20.68 engaged minutes — the largest
exposure in the corpus at the time (695 s engaged ≥50 km/h, 274 s ≥80). **Operator: *"fixed nothing,
still only as good as V88."*** Pre-registration: IDENTITY **PASS** · H1 (probe fires) **PASS** ·
🛑 **H2 (THE LEVER) FAIL** — on the intrinsically order-clean stratum (v ≥ 22.2 m/s, 0 windows vetoed
so the screening asymmetry is structurally absent) the contrast is **0.947 [0.827, 0.979]** against a
same-build placebo band of **[0.900, 1.111]** = **0.92σ, FLAT** · H3 (the operator's constraint)
**PASS**, no sign-chain inversion · H4 the operator, above. 🛑 **The block-bootstrap CI EXCLUDED 1.00
and would have been reported as a resolvable 5 % fix — the placebo control earned its keep on its
first use.** ⊕ **And V89's own probe says why it could never have worked**: the friction term is
`sign(motor rate)`-gated and `|friction| ≥ 0.0625` on **0.000** of frames below 1 °/s and **0.009** of
the operator's micro-ratcheting regime (1–13 °/s, 782 engaged s) ⇒ **the cell K1 doubles is negligible
on 99.1 % of the regime where he names the symptom.** Not a falsification of the friction account —
arithmetic saying the lever was pointed away from the target, and a **fifth** independent confirmation
that the term is Coulomb friction. **This is the SIXTH instance of the "row says UNFLASHED after it
flew" record defect** (V83a, V84, nearly V85, V86, V86B, now V89). **Write the row in the same pass
that scores the flight.**

| **V90** | **flown V89** | 🛑 **PROBE-ONLY — NOT ONE CALIBRATION CELL CHANGES.** `0xC40D2` stays **204**, so V89's friction lever remains on the car and remains observed. **9 runs / 68 bytes vs V89** (80 bytes *written*: 74 cave + 2 repoint + 4 CRC — the two counts differ because one counts bytes changed vs base and the other bytes written). Cave `0xC4B34`–`0xC4B7D` grows 62 → **74 bytes**; `0x55DF2` `6894`→`da94` repoints CAN 427 `MOTOR_TORQUE` to **`gp-0x6b26`** at ~9 unclipped effective bits; ONE CRC trailer, `0xC4FFC`. Rungs: `b7` `gp-0x6b26 < 0` (**the only channel reaching 18–28 Hz** — 427's Nyquist is 24.9 Hz) · `b6` `\|gp-0x6bf6\| ≥ 512` = `\|model\|` · `b5` `gp-0x6ae2 ≠ 0` (V89's rung **unchanged** ⇒ apples-to-apples) · `b4` `gp-0x6c00 < 0` (**the observer gate — never once measured**) · `b3` fingerprint | ✅ **FLEW AS ROUTE `00000077--7411859c54`, 2026-08-11** — 21 segments, 1245.3 s, cache `_cache_r77/`. **FAULT-FREE**: `STEER_STATUS` {0: 124,358, 3: 3}, DTC-active duty **0.000000** with 0 transitions, **0 sentinels** on both `0x14A` and `0x18F`, `CONFIG_VALID` 1.0000, `OUTPUT_DISABLED` 0.00002, **no EPS entry in 3,489 `onroadEvents`**. **Engaged 1074.6 s = 17.91 min = 86.41 %**, 9 episodes all ≥10 s (longest 276.8 s), ≥50 km/h **316.4 s**, ≥80 km/h 42.0 s, v_max 90.4 km/h; micro-ratcheting regime 437.6 s · ratcheting 196.0 s · macro 76.7 s; manual 169.0 s of which **67.7 % parked**. 427: 62,180 frames at 49.81 Hz, COUNTER +1 on 100.00 %. ★ **IDENTITY PASS, parameter-free and SINGLE-FRAME: `b4 == 0` on 124,362 / 124,362** — impossible on V86B/V87/V88/V89 where `b4` railed at exactly 1.0000 over 254,085 frames; the `(byte4>>3)&0x1F` histogram lands entirely in the V90-only alphabet `{1,5,9,13,17,21,25,29}` with **zero** frames in `{3,7,15,23,31}`, and every value odd ⇒ `b3 ≡ 1` and the right bit offset. 🛑 **OPERATOR, VERBATIM: *"grind #1 still exists · micro-ratcheting still exists · grind #2 can be felt on the highway-speed curves or lane changes"*** (parking lot + street + highway). **Because V90 is byte-identical to V89 in every cal cell, this is the CONTROL CONDITION, not a failed fix.** ★★★ **THE DELIVERABLE — `gp-0x6b26` MEASURED FOR THE FIRST TIME ON ANY BUILD**: engaged p50 **5.5** / p90 39.1 / p99 **114.3** / **max 319.1** against the ±511 clamp, **clamp duty EXACTLY 0.000000 in every stratum**, wire saturation 0.000000 ⇒ every sample honest. **The lane is NOT a relay today.** Clipping ladder: never pins to **1.60×** · <0.1 % to 2.75× · <1 % to 4.45× — 🛑 **a CLIPPING ladder, NOT a dose budget: the int32 wraparound in `FUN_00036c12`'s `mul r13,r6,r0` (×0x111, high half discarded, unclamped and UPSTREAM of `0xC407E`) binds first at ≈1.6005×, and ×2.75 would WRAP — a full-scale SIGN INVERSION delivered before the clamp meant to contain it.** ★★ **THE OBSERVER GATE NEVER FAILS** — `gp-0x6c00 < 0` on **0 of 124,362 frames**, 20.49 min, engaged and manual, every wheel-rate bin. ★★ **`Re(Z) < 0` ACROSS 2–16 Hz REPLICATED at 37× V89's exposure** (221 windows / 884.5 s vs 6): **−3375 ct·s/rad at 6–9 Hz** vs V89's ≈−3300 on an independent drive, phase −125° to −152° against inertia's +90° ⇒ **inertia refuted again**. Extended to 35 Hz: **`Re(Z)` FLIPS SIGN at ~26 Hz** — anti-damped 2–26, **positively damped 26–35** ⇒ grind #2's band is not anti-damped at all. 🛑🛑 **AND THE ANTI-DAMPING IS NOT THE PID**: at 6–9 Hz P −0.145, I −0.053, D +0.077 ⇒ **NET −0.121 = DAMPING**, while `Re(Z)` reads −3375 at coherence 0.769 vs shuffled 0.001 ⇒ **it is another aggregator lane, or the plant. The session's biggest open question.** 🛑 **"THE FIRMWARE CANNOT SEE THE 6–9 Hz MODE" IS REFUTED**: `R = \|B26/W\|/\|H\|`, normalised at 2–4 Hz where column and motor are rigidly coupled, reads **1.016 at 6–9 Hz with coh² 0.438 vs shuffled 0.001 — the highest of any low band. R is FLAT, no dip.** ⇒ the damping lane goes back in play for the ratchet (2.99 vs 6.80 authority per °/s = **2.3× less, not zero**); what *is* attenuated toward the motor is the narrow **7.8 Hz LINE**, not the band. **No measurable grinding regression from K1 = 204** — `e_18-22` V89(+V90) ÷ V88 on three strata, all ≤1.03 and FLAT against their own placebo bands; the one stratum reading 1.451 is a **stratum artefact** (37 V89 + 2 V88 windows carry the whole flip, 3 V88 episodes, and the no-hypothesis `e_10-16` placebo also reads "resolvable"). **Power: this corpus cannot resolve an `e_18-22` change below ≈±20 % (all-engaged) to ±30 % (order-vetoed).** 🛑 **AND V90 IS ITS OWN PLACEBO PAIR, which is damning for the method**: r77 ÷ r75 on **byte-identical firmware** returns `e_6-9` **1.288 [1.017, 1.661]** with the **band contrast also excluding 1.00**; r77 ÷ r76 returns `e_18-22` **1.333 [1.001, 2.307]**. ⇒ **the band contrast does NOT rescue a thin cut.** ⊕ b6's guessed 512 threshold landed inside its predicted 0.10–0.50 bracket at 0.2535 ⇒ **do not move `0xC4B4A`** — image sha256 **`28ac817bc3f76958ad5a33316e420c734949f24b206ddb6d083a5254b3aa70db`**, rwd `39990-TVA,A160-V90-V89BASE-PROBE.6B26.6BF6.6AE2.6C00-427.6B26-0x13000-0x100000.rwd` sha256 **`bc04a56f986455d15c02c0ded8aa40c0a290e950bcd7fe9ca50f746a414ecf37`** (986,042 B). 🛑 **CLASS: the seventh consecutive ONE-CELL-OR-ZERO-CELL build (V85→V90), and the only ZERO-cell one — "measure the cell a dose would act on, before dosing it."** Scoring: `docs/SCORING-2026-08-11-v90-flight.md` |

| **V91** | **flown V90** | **TWELVE BYTES. Two int16 triples. Cal-only — no cave change, no code change.** `0xD7A5C` mode **26** (ENGAGED) friction/damping-comp LERP Y row `(-9830,-5734,-1966)` → **`(-14745,-8601,-2949)`** and `0xD7A6C` mode **27** (ENGAGED) the same. Everything else carried byte-identical: V90's cave at `0xC4B34`, the CAN 427 repoint at `0x55DF2`, V89's K1 at `0xC40D2` = 204, Lever B (`0x3AA96` FB / `0xC6446` 5244), `0x454FE` = B5, `0xC62EA` = 0. **`0xC407E` asserted at Honda's 511.** ONE CRC trailer (`0xD7FFC`), **derived in code** from the touched addresses via `V53.owning_block`, never hard-coded | **BUILT, VERIFIED, UNFLASHED 2026-08-11.** image sha256 **`0ea15ca9d5f811ddcf915b33237dc3f686461f6b84afb7c476e9f1d2b8a011b1`**, rwd `39990-TVA,A160-V91-V90BASE-CBE74.M26.M27.X1.5-0x13000-0x100000.rwd` sha256 **`217f9cef33eaf2544b82bc2c99e8b9e6e5ee3f09bdbe523cfc3014e722b17c0b`** (986,042 B). 🛑🛑 **THE HONEST LABEL, AS THE BUILD SCRIPT'S OWN HEADER CARRIES IT: V91 IS THE SAME LEVER AT THE SAME ×1.5 DOSE THAT FLEW ON V74 AND V75, AND BOTH OF THOSE FLIGHTS HARD-FAULTED** with a latched total loss of power steering. **The single difference is `0xC407E`**: every artefact that ever carried this dose also carried **850**; V91 carries Honda's **511**, one count under the DTC-0x1d monitor's 512 trip, so the monitor is structurally untrippable at **any** multiplier (`gp-0x6b26 = clamp(raw, ±cal(0xC407E))` and the clamp binds strictly upstream of the monitor). 🛑 **ZERO FLIGHTS HAVE EVER SEPARATED THE DOSE FROM THE 850 INTERLOCK — THE SEPARATION IS STRUCTURAL, NEVER EMPIRICAL.** **V81 (route 67, fault-free) is a control for the INTERLOCK ONLY** — it is byte-stock on the friction row in all 34 modes, so it says nothing about the dose. **Writing only modes 26/27 is a DELIBERATE NARROWING from V74/V75's 14 records (`{2,3,5,10,11,14,15,17,23,26,27,29,32,33}`, re-verified from those images at build time), not a reproduction** — modes 24/25 stay byte-stock so a manual-vs-engaged contrast exists **inside the same drive**, which V74/V75 could not construct. 🛑🛑 **AND ×1.5 IS 94 % OF THE LEVER'S ENTIRE RANGE — NO LARGER DOSE EXISTS, EVER.** Three bounds: clip envelope (route 77 engaged max 319.1 vs the ±511 rail ⇒ ≤1.6014) · **int32 wraparound in `FUN_00036c12`** (≤ **1.6005**, proven against `gp-0x6c2c`'s own hard ±32,000 producer clamp so it holds in transients route 77 never sampled; the script re-derives it at run time and reports headroom **1.0670×**) · and it is the dose V74/V75 flew. **Not "untested at higher dose" — unreachable.** ⚠ **AND IT IS UNDERPOWERED AT THAT DOSE**: delivered damping is **5–69× below the 11 % resolvability floor** in every band (6–9 Hz 0.16 % of the 208 ct engaged median · 18–22 Hz 1.20 % · 26–31 Hz 2.15 %, the last extrapolated and robust to its own 0.50–1.37× model error). `fw-dampaxis`'s recommendation was **"do not fly `0xCBE74` as a dose"**, on five independent reasons. **It is flying by the operator's explicit decision with that verdict in front of him — *"we are flying regardless, so the instrument is free."*** ⊕ **What is genuinely different this time**, stated so the re-run is not mistaken for a new lever: (1) `0xC407E` = 511, not 850; (2) 2 records instead of 14, with a built-in manual control; (3) it rides V90's instrument — **CAN 427 now carries `gp-0x6b26` directly, so V91 measures its own dose**, where V74/V75 flew blind on this signal; (4) it moves a CALIBRATION, not the plant model, so V89's K1 is not re-litigated. ★ **GATE 2 is the best position of any dynamics lever in the kit**: describing-function gain **exactly 1.000 through ×4** (first departure 0.881 at ×6), the ±1024 zero-reject **can never fire** (`0xC407E` clamps to ±511 first), and the dissipative sign is closed **structurally** — phase of `−gp-0x6c2c` vs rate never reaches −90° at any frequency to Nyquist. ★ **`H(0) = 0` EXACTLY, proven three ways** including in the fixed-point integer arithmetic itself (a constant input makes the differencer's operands identical integers) ⇒ **this lane contributes NOTHING at any sustained steering rate, at any multiplier — the operator's own "do not limit max LKAS steering angle rate" constraint is satisfied STRUCTURALLY, not by argument.** ⚠ **GATE-2 CAUTION specific to the ratchet**: at 7.79 Hz the term is **97.2 % reactive / 23.5 % dissipative**, and a +90° deviation from the dissipative reference is `F ∝ −acceleration` = **added apparent inertia**, which LOWERS both `ω0` and `ζ`. The net sign cannot be signed without the column's `J`/`c`/`k`, none of which are on file. ⇒ **better supported for grind #1/#2 than for the ratchet** — matching grind #1's dissipative delivery needs ~6.1× more gain, grind #2 ~9.2×, and there is no headroom. 🛑 **SCORE IT WITH `docs/SCORING-2026-08-11-v90-flight.md` §10.1–10.6 EXACTLY AS WRITTEN** (pre-registered before the build was cut). **Dose-in-force arms run FIRST**: engaged cell-stratified ratio **1.50 ± 15 %** with CI excluding 1.00 · **manual must read 1.00 — if it scales the WRONG RECORD was edited and the build must be PULLED** · flat across every speed bin. 🛑 **If the ratio's CI contains 1.00, every band result is UNINTERPRETABLE** (V64's null was on the gate and was read as a result for weeks). **REVERT TRIGGERS**: clamp duty above ~0 at ±511 / repeated `wire == 319` — **a railed lane is `sign(gp-0x6c2c) × 511`, a Coulomb relay, the V80 mechanism itself** · `e_26-31` ≥ 1.50 outside the placebo band **[0.831, 1.200]** · **≥3 consecutive order-vetoed engaged `wrecs` windows with `p_26-31` > 37.12** (fixed from route 77 alone before V91 existed, **measured false-positive rate on the reference build: ZERO**) · **the operator, overriding all of them in both directions.** ⚠ **The predicted effect STRADDLES the detection floor** (upper bound +50 %, lower bound 0, floor ±16–22 % contrasted): **a null below ~16 % means nothing** and his report becomes the primary endpoint. ⊕ Under FIV the response is **threshold-like**, so "≈ nothing" and "a lot" are the likely outcomes — 🛑 **but the usual "then dose higher" consequence DOES NOT APPLY, because there is no higher.** ⊕ **Costs nothing and buys the most: fly it on the SAME ROUTE as 77.** Build traps it is armed against: an address is not a mode (every record dereferenced from `0xCBE74 + mode*4` and printed with its mode) · **Y is at record base + 8** (writing at base+2 lands in the X array, compared UNSIGNED ⇒ a silent flat `Y[0]` at all speeds) · mode 25's record sits exactly `0x10` below mode 26's, so a −0x10 slip lands on a disengaged column and looks plausible · **the pointer array is 34 slots, a GIVEN bound — `0xCBEFC` is the first slot past it and holds a valid-looking pointer to a valid-looking n=3 record, so an exhaustion walk runs straight into `gain_B`** |

| **V92** | **flown V90** | **V91's 12 calibration bytes (IDENTICAL) + a 116-byte TELEMETRY CAVE + a 2-byte 427 repoint + a 1-halfword 427 SCALING FIX.** **FIVE edits: 12 cal + 116 cave (43 instructions) + 2 repoint + 2 scaling + CRC.** `0xC4B34` cave 74 B → **116 B**; `0x55DF2` `da94` → **`4294`** (CAN 427 `MOTOR_TORQUE`: `gp-0x6b26` → **`gp-0x6bbe`**); **`0x55E10` `a332` → `a432`** (`sar 3` → `sar 4` — **the no-clip fix, see the residual note below**). 🛑 **THE FIRST BUILD EVER TO WRITE CAN `0x14A` BYTE 7** — every cave from V53 to V90 wrote byte 4 bits 7:3 and nothing else; the field grows **5 bits → 7**. **SEVEN rungs, `0x18F` untouched, ONE hook**: `byte4 b7` `gp-0x6bbe < 0` (**sign of the BOOST lane**) · `b6` `gp-0x6b62 < 0` (**sign of the RETURN-CENTRE lane** — its own net dissipative sign, never measured) · `b5` `gp-0x6b62 ≠ 0` (**lane LIVE** — disambiguates the confirmed disable branches from "tiny") · **`b4` `gp-0x6bda ∈ (−397, 384)`** — **the outer-gate-OPEN bit, and it is what makes `b6` interpretable at all** (see the validator note below) · `b3` fingerprint ≡ 1 (⇒ every `byte4[7:3]` value ODD) · **`byte7 b7` `\|gp-0x6b26\| ≥ 15` = 🛑 DOSE-IN-FORCE for the `0xCBE74` ×1.5 edit** (`T=15` from route 77's own percentiles: duty **0.242 stock → 0.339 dosed**, both well off 0/1 — needed because 427 has moved off `gp-0x6b26`) · **`byte7 b6` `gp-0x6a82 > cal(0xC627E) = 20` = the DWELL-RELAY SNAP STATE**. **427 (50 Hz) = `clamp(\|gp-0x6bbe\| × 5 >> 4, 0, 0x3FF)`** after the scaling fix. ⚠ **`sign(gp-0x6abc)` — the raw-motor-rate CONVENTION ANCHOR — was DROPPED to make room for `b4`.** The builder's own wording for the cost: ***"recoverable at DC, unrecovered in the 6–30 Hz bands where band-resolved phase claims live."*** | ✅ **CUT, VERIFIED, UNFLASHED 2026-08-11. 198/198 assertions** (178 dry-run + 20 that only run on a real write). Reproduces bit-for-bit on a second run. image sha256 **`c8e89fe35ebc445e4c4b19663ba9655dfeb8ba5cada2172aeb033eeb9f9eb939`** rwd   sha256 **`388a1974d5702e17fded074457632092189eb55d806aefd4600e17d58e974245`** `39990-TVA,A160-V92-V90BASE-CBE74.M26.M27.X1.5-CAVE.6BBE.6B62.6BDA.6A82-427.6BBE.SAR4-0x13000-0x100000.rwd` (986,042 B) Diff vs V90: **10 runs / 119 bytes, ZERO unattributed**; 140 attributed (12 cal + 2 repoint + 2 scale + 116 cave span + 8 CRC), 21 cave bytes coincide with V90's and the `sar` halfword moves only its high byte. CRC trailers **derived in code** = `{0xC4FFC, 0xD7FFC}`; chain 50/50 on the image, the readback and the shipped `.rwd`. `[0xD7000,0xD8000)` **byte-identical to V91's image**. V90 and V91 artefacts re-hashed after the cut and unchanged. Ghidra's own disassembler decoded the built cave end-to-end: **43 instructions, 116 bytes, all 7 branch targets on instruction starts, conditions only {bge, bnh}**. 🛑 **SUPERSEDED V92 ARTEFACTS — NEVER FLOWN, DO NOT FLASH.** An earlier V92 cut this session (182/182 assertions, from-disk verified) carried the **OLD rung map — `b4 = sign(gp-0x6abc)`, a 110 B cave, and no 427 `sar` fix.** It was superseded before flight by the `gp-0x6bda`-in-window swap and the `0x55E10` `a332`→`a432` no-clip fix. Its hashes appear in the session transcript with a complete PASSING assertion log — **they are DEAD**, and both files were deleted at the real cut. **DEAD - image `b092bf19db04f58047a58eeefeb784f63ff8655c573493e8d2c7f63bf4dfdce2`** · **DEAD - rwd `630248a53393fcc2470b66b709604e0d43cffc87fdcbf3d7962061947467fb11`**. 🛑 **A verified artefact for a superseded design is MORE dangerous than an unverified one, not less — everything about it looks correct, including its assertion log. Write the dead hash out IN FULL next to the word DEAD; a truncated entry returns nothing for the search that will actually be run.** \|gp-0x6b64\| < cal(0xC618A) = 1024` and forces the output magnitude to a fixed 1024 ceiling once the counter passes 20 — **a fixed resistance that arms after ~20 ms of near-stillness and releases when you push through IS A DETENT**, the first structural match to *"micro-ratcheting when spinning the wheel at all"*. 🛑 **It may NOT arm during a sustained 7.79 Hz ratchet** — the rate signal is near zero only ~8 ms per zero crossing against a 20 ms arm time ⇒ **read a LOW duty as "trigger, not sustainer", NOT as a null. Both rails are informative, which is what justifies the bit.** ⊕ **ONE-TICK CAVEAT ON `byte7 b6`, recorded so nobody rediscovers it as a defect**: `FUN_00036388` evaluates the snap on the PRE-update counter and stores the POST-update counter, so a 100 Hz read equals the condition the 1 kHz task evaluates on its NEXT tick — **≤1 ms offset, immaterial at 100 Hz.** ✅ **THE 427 SATURATION RESIDUAL IS FIXED IN THE CUT — it was found, named, escalated, and then applied as the fifth edit.** Honda's packer is `clamp(\|src\| × 5 >> 3, 0, 0x3FF)`; `gp-0x6b26` was clamped to ±511 upstream so V90 could never clip (511×5>>3 = 319), but **`gp-0x6bbe`'s aggregator window is ±2048**, so at `sar 3` the field **saturates at `\|gp-0x6bbe\| ≥ 1639`** — flat, monotone, never wrapping, but **blind: the top ~20 % of the lane's window would read as one value.** The **SIGN bit (`byte4 b7`) was unaffected either way and still reaches 26–31 Hz.** **`0x55E10` `a332` → `a432` (`sar 3` → `sar 4`) is now IN THE BUILD**: `\|x\|×5>>4`, max **640 of 1023**, **never clips**, at half the resolution. 📋 **Method note worth keeping: the builder reported the defect and named the one-byte fix rather than silently applying it, because the brief scoped the repoint to exactly 2 bytes — the widening was then authorised. That is the escalation path working, not a scope violation.** ★ **IDENTITY, single-frame and disjoint BY CONSTRUCTION: any frame with `0x14A` byte7[7:6] ≠ 0 proves V92 is on the car.** No build V53–V91 can produce it — the only two writers of `gp-0x1511` (`0x55C02` `andi 0xcf`, the redundancy-voted counter at bits 5:4; `0x55C2A` `andi 0xf0`, the checksum nibble at bits 3:0) **explicitly mask bits 7:6 off**, verified two ways (decompile of `FUN_00055a98` + an independent Python byte scan of the whole image for any `st.b/st.h rX,-0x1511[gp]` → **exactly those two hits**). **This does not depend on trusting any prior build's measured duty.** ⊕ Checksum `FUN_00057b24(gp-0x1518, 8, 0x14a)` is called at `0x55C18`, **AFTER** the hook at `0x55C0E`, so it covers the two new bits automatically — the same mechanism 10+ flights have used for byte 4. 🛑 **CAVE DISCIPLINE — NOT ONE BYTE OF THE 110 IS HAND-ENCODED**; all are copied from a Ghidra-verified twin (V90's own flown cave in this base, or Honda code elsewhere in this image) and the script asserts **116/116 byte coverage** by the twin table before it will build. Traps thereby defeated: **`subr r0,r6` is `8031` — the hand-derived `3080` is `satsubr`, which SATURATES instead of negating and corrupts `b7` on negative values only, a defect that survives a flight** · `ld.h X[gp],r7` and `ld.w X[gp],r7` share hw1 `243f` with only hw2 bit 0 separating them, so the counter was deliberately placed in **r6** (hw1 `2437`, already flying) to avoid twinning a halfword against a different instruction class · `ld.bu -0x1511` has op field **0x3D, not 0x3C** (the displacement's bit 0 lives in hw1 bit 5), so both the load and the store are copied **whole, 4 bytes each**, from the `0x14A` builder's own byte-7 accesses 14 and 30 bytes below the hook. **GATE 1 verified this session, not inherited**: every new access is an `ld.h`/`ld.hu` (a load has no side effect, **no new RAM is claimed anywhere**); scratch is **r6 and r7 ONLY**, asserted mechanically (every register referenced by the decoded payload ∈ {r0, gp, tp, r6, r7, lp}, every register written ∈ {r6, r7}); r6 and r7 are **dead at the hook**, r8/r10 are **LIVE across it and the cave never touches them**, lp is dead. **GATE 2** is vacuous for the cave (a straight-line leaf — no loop, no call, no divide, no float, **43 instructions** at 100 Hz inside Honda's own `di`/`ei` critical section, V90's hook site unchanged) and for the cal edit is V91's argument re-run in full (**a uniform ×1.5 on all three Y knots is a REAL SCALAR MULTIPLY — zero phase at any frequency, no sign change, no breakpoint moved — and `H(0) = 0` is proven three ways**). **TWO CRC trailers, DERIVED IN CODE from the image's own 50-block map, never hard-coded.** 🛑 **FROZEN, by count, and V92 moves NONE of them**: `0xC40D2` (K1) unmoved since V89 = 3 builds · `0xC6446` (Lever B) since V88 = 4 · `0x3AA96` since V88 = 4 · `0x454FE` since V80 · `0xC407E` at Honda's 511 since V81 · `0xC6CD0` = 3564 (the 4.000× forward gain) on **every** build. ⊕ **RE-RUN vs NEW, stated plainly by the builder**: the 12 cal bytes are a **RE-RUN** of V74/V75's lever narrowed to modes 26/27; the 427 repoint is the same **CLASS** as V87/V88/V90 (a 2-byte source halfword) pointed at a cell no build has ever telemetered; **the cave rungs are ALL new signals** — none of `gp-0x6bbe`/`gp-0x6b62`/`gp-0x6abc` has ever been on the wire. ⊕ **A deliberate, argued decision: stay on the ONE `0x14A` hook rather than take a second on `0x18F`** — a risk-class argument, not a capacity one: **a second, never-flown hook is exactly the "novel cave/hook combination" class this kit's three bricks (V24/V27/V48B) came from.** ⊕ **`b5`/`b6` were freed by a MEASUREMENT, not a guess**: V90's `(b6,b5)` 2×2 gives `P(b5\|b6=1)` = 0.986 → 1.000 above 1 °/s with a discriminating cell of **0.63 %** of engaged frames ⇒ friction and `\|model\|` are near-collinear exactly where the operator names the symptom — **a STRUCTURAL explanation for V89's null, not a pending measurement** — so those two rungs had nothing left to buy. 🛑🛑 **THE `(b4, byte7 b6) = (0,0)` VALIDATOR — THE "SHOULD NEVER OCCUR" FRAMING IS WRONG AND IS WITHDRAWN. A SCORER TOLD `never` WOULD PULL A WORKING BUILD.** The reason `b4` exists is that the LERP feeding `gp-0x6b64` (`X=[-397,-192,140,294,384]`, `Y=[0,2560,2560,717,0]`) is **zero outside `(−397, 384)`**, so `\|gp-0x6b64\| < cal(0xC618A) = 1024` fires for **two physically different reasons** — a genuine low wheel rate (a real detent) **or the outer gate simply being shut** (`Y1 = 0` ⇒ `gp-0x6b64 ≡ 0` ⇒ trivially `<1024` ⇒ a flat −1024 bias, not a relay). **But a shut gate SATISFIES the arm condition every tick, so the dwell counter CLIMBS to its ceiling of 21 rather than staying down — and that climb takes 21 ticks at 1 kHz = 21 ms, during which `b4` is already 0 while `b6` is still 0.** ⇒ **`(0,0)` occurs for ~21 ms after EVERY gate-shut edge — roughly 2 frames at 100 Hz per event.** > **CORRECTED PRE-REGISTRATION: `(0,0)` is RARE and ALWAYS ADJACENT TO A `b4` FALLING EDGE. A SUSTAINED `(0,0)` RUN is what indicts the rung map — a handful of frames per event is the instrument working as designed.** ⊕ **And the correction STRENGTHENS the design rationale: because a shut gate ARMS the counter rather than disarming it, `b6 = 1` is the DEFAULT STATE whenever the outer gate is shut** ⇒ **`b4` is not a nice-to-have partner for `b6`; it is what makes `b6` interpretable at all. Without `b4`, `b6` has no baseline.** The swap was right for a better reason than the one given for it at the time. ⊕ 🛑 **THE GENUINE never-occurs validator is a DIFFERENT cell and the two must not be confused: `(b6, b5) = (1, 0)` IS structurally unreachable** — both bits read `gp-0x6b62`, so `gp-0x6b62 < 0` cannot be true while `gp-0x6b62 ≠ 0` is false ⇒ **12 of the 16 odd `byte4` codewords are reachable.** That one is a real correctness check; `(0,0)` is not. ⚠ **One cross-agent claim adjudicated rather than deferred, and it found a real nuance**: `gp-0x6bf0` is **NOT** referenced anywhere inside `FUN_00036388`/`FUN_000360fe` — it is computed in `FUN_0003bd7c` and has **15+ readers including the shaper directly** — so the "two terms of one return-centre lane" framing is imprecise. (`gp-0x6abc` **was** independently confirmed as raw, unfiltered motor rate.) Full spec: `docs/SPEC-2026-08-11-telemetry-budget.md` ADDENDUM 2/3 |

**V85 artifacts** — image `_v85_FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2_plain_image.bin`
sha `cc9cdd662ab92049e266d3fef862763bee24dc21e8efa1fe8314ec983ed06e8f`;
rwd `39990-TVA,A160-V85-V84BASE-FRICTION.C40BC.6000-PROBE.RATE.6ABC-FRIC.6AE2-0x13000-0x100000.rwd`
sha `ff0684c2763440c0df9b2ce369ab5b979f7721614e1dd0f95445435079c3c05d` (986,042 B).
Route `6e` = `75604b0a432fdc89_0000006e--649c462a6e`, cache `_cache_r6e/`.
🛑 **`_cache_r6e/r6e.npz` carries `probe_build = ['V80']` — a STALE EXTRACTOR HEURISTIC. It is WRONG.
Never quote it.** Found independently by two agents.
⚠ **Route `6e` segment `--7--` is truncated mid-capnp-message**; stock `read_messages` raises and loses
the whole route. A wrapper recovered 32,695 complete messages.
⊕ **Naming trap:** "CAN 330 / 399 / 427" in this kit are **decimal** = hex **`0x14A` / `0x18F` / `0x1AB`**.

**V83a artifacts** — image sha `bb717ce8322d35c587e95084e697a5ad98ba6564ee9265bb09a88a2a241cd25a`;
rwd `39990-TVA,A160-V83A-V81BASE-FACTORE.STOCK-GAINA.STOCK-C63A0.1024-magprobe-6bd0-thermo-6ac2-0x13000-0x100000.rwd`
sha `0be75e670ebf0c7e57f443eff7ff6976af1d276f54cef61a60e399827ac532aa`.
**Route 68 identity [EVIDENCE, no free parameters]:** the probe thermometer predicted from each candidate
image's own bytes — if V81, bit6 **32.19%** / bit5 **14.60%**; if V83a, **0.515%** / **0.000%**; **observed
0.508% / 0.000%**, and the same code identifies route 67 as V81. 43,606 frames, 437.8 s, `latActive` 69.9%,
`STEER_STATUS` {0: 43,604, 3: 2}, 0 sentinels, 0 DTC-active frames.

**V84 artifacts** — image `_v84_LEVERB.ARM5244-DAMPER.HONDA.M26.M27-PROBE.R24.6ADA-FD.67FE.6A10_plain_image.bin`
sha `344f22f7303f6b5b006b13d329192ce098d118c9ce149834cb3cc05899dc637a`;
rwd `39990-TVA,A160-V84-V83ABASE-LEVERB.ARM5244-DAMPER.HONDA.M26.M27-PROBE.R24.6ADA-FD.67FE.6A10-0x13000-0x100000.rwd`
sha `5e830b2588b22fd6238c4bd376e602d603b5d25871368d08df7986519cda1bca` (986,042 B).
⚠ **V84 WAS RE-CUT.** The earlier **control-path-only** cut (`.rwd` `54985b45…`, image `bdd857c9…`) is
retained renamed **`SUPERSEDED-DO-NOT-FLASH-…`**, bytes intact and verifiable. **Exactly one flashable V84.**
**Rationale:** raise the **DC-neutral** damping (the rate lane, engaged-only by construction — manual is
byte-for-byte Honda, which answers the operator's standing 2026-07-31 objection) and **delete the
DC-opposing** damping (the mode-26/27 Coulomb damper, which is **OURS**, armed at V74).
★ After V84 **all six factor families are identical engaged-vs-manual, exhaustively over speed counts
0 … 14000, for BOTH pairs (24↔26 and 25↔27)** — orchestrator-verified.
★ **V84's damper surface is byte-identical to V67 and V68** ⇒ the grind-#1 prediction is an **interpolation
onto a measured point, not an extrapolation.** ⚠ V67/V68 ran `0x454FE` = `BA` (**no** V42 fix); **V84 carries
it.** **Probe, `0x14A` byte4:** `b7` r24 ≥ +1024 · `b6` r24 ≤ −1025 · `b5` `gp-0x67fe ∈ {1,2}` ·
`b4` `gp-0x6a10 ≥ 8` · `b3` fingerprint = 1.
🛑 **V84 does NOT address** the highway grind (V67/V68 both carried Lever B and it persisted) or the ~28 Hz
lane-change transient (excitation, not gain).

🛑 **THE V38 REBASE REVERTED SEVEN THINGS, NOT THREE** (walked 2026-08-08 late). Named in the record:
`0xC63A0`, `0xC407E`, friction ×1.5 (the last two **declared**), then `0xC62EA`, the V57 decouple triplet
and `0x454FE`. **The seventh had never been logged anywhere: `gain_A` rec0/rec1 — `0xC6A72`–`0xC6A78` and
`0xC6A86`–`0xC6A8C` — went 512 → Honda's `3072/2434/2048` and `3072/2488/1536` on V76/V78/V79/V80.**
⇒ **any V80-vs-V75 (or V76-vs-V75) contrast carries FIVE silent confounds, not four.** [EVIDENCE]

🛑 **`0x454FE` WAS LOST A SECOND TIME.** It is `0xBA` — i.e. **byte-stock, V42's macro-ratchet fix absent**
— on **V76, V78 and V79**, and **V80 restored it to `0xB5`**. V81/V83a/V84 carry `0xB5`. This is the same
byte RULE 3 records as the first silent rebase loss; **it has now been lost twice.** [EVIDENCE]

🛑 **`0xC63A0`: the standing "do not double it" directive was RETIRED EXPLICITLY on 2026-08-08, by
operator decision, on evidence** — one reader, zero writers, no firmware data path to the faulting
monitor; the real fault mechanism was `0xC407E` = 850, reverted in V81. Recorded as a decision, not an
oversight.

🛑 **CORRECTION: `0xC6206`/`0xC6208` are NOT "hands-off/hands-on"** as this file and the build
scripts label them. The selector `gp-0x67f5` flips on **voted vehicle speed crossing 16.6 km/h**
(cal `0xC531E` = 1062, 10-cycle debounce at `0xC64E7`).

★ **Never written by any build, and now named:** `0xC64C8` (aggregator mode selector — **mode 1 deletes
the entire aggregator contribution**; 0 writers, 1 reader), `0xC64C9` (blend mux), `0xC61DA` (1092, Q10
integrator scale), `gain_A` rec2/rec3 `0xC6A90`/`0xC6AA4` (the ≥50 km/h r26 records), mode-26 `gain_B`
`0xD7A88`/`0xD7AC4`, and **FactorD** `0xC9DB4` (n=5, flat-unity in every mode, axis `gp-0x6a10` =
angle-tracking error at 0.1°/count).

---

## 🛑🛑 RULE 12 — **A TABLE'S SHAPE IS BOUNDED BY ITS OUTPUT CLAMP, NOT BY ITS BREAKPOINT COUNT.**

**Added 2026-08-07.** A proposal arrived to make the damper's FactorC and FactorE literal ReLUs and, if
4 breakpoints proved too few, to build larger tables in free memory and repoint every reader. **Both
halves of that mechanism were wrong, and the reasons generalise.**

**(a) Count the DOF before asking for more points.** A ReLU is **2 DOF**. A 4-point record carries 8
numbers and spends 3 of them on collinearity. `n` buys **n−1 slope segments**; n=4 gives **three**, so
ReLU, ReLU+hold and ReLU+hold+rise are all reachable. **More points bought EXACTLY ZERO here**, proven
by explicit construction. 📋 **Ask which FOURTH segment is needed. If nobody can name it, n=4 is enough.**

**(b) The binding constraint was a clamp nobody had written down.** `gp-0x6bd0` is hard-clamped to
±`ceiling_LERP(gp-0x6ac2)` — **≤ 1024, and 512 at low ceiling index**. A ReLU FactorC is
speed-proportional, so `dose(v,99)/dose(515,99) = v/515` **whatever values are chosen**; pinning the
requested dose at 5 mph forces **7.02× the ceiling at 140 km/h** and rails from **3.2 °/s** upward.
★★ **A railed factor whose sign comes from a different cell (`gp-0x6abe`) than its index (`gp-0x6ac0`)
IS the Coulomb relay this kit already forbids at `E_Y[0]` — the "ReLU" re-creates it at the ceiling.**
🛑🛑 **AND THE TEST WRITTEN FOR (b) DOES NOT ACTUALLY DISCRIMINATE (b) — V80 PROVED IT ON-CAR, 2026-08-07.**
A flat `FactorC` sized so the supremum equals the ceiling **exactly** clips 0.00% and passes every no-clip
guard, while delivering a **constant 495 counts across a 34× rate range** — the relay simply moves off the
ceiling clamp onto `FactorE`'s knee, **17 counts under the rail.** See **Part 2 → GATE 2 COROLLARY** for
the shape tests that would have caught it (flatness ratio, describing function `N(50)/N(500)`, distance to
the rail in counts, and a probe rung sized to the saturated regime).

**(c) Check how the operator used the shape word LAST time.** "Which factor isn't a ReLU" had two
readings indicting **opposite tables**: literal `max(0,k(x−x0))` indicts FactorC (nonzero 566 floor);
the operator's own recorded gloss in `v76_surface.py` — *"FLAT — no taper down, like a rectified linear
unit"*, read there as a **floor clamp** — indicts FactorE. **When a shape word is load-bearing for a
flash decision, grep the kit for how it was recorded before designing to it.**

⊕ Recorded for future use: relocating a **same-size** record IS cal-only — one u32 into the factor's
pointer array — and **`0xD7BB8`–`0xD7FEF` is 1,080 B of virgin `0xFF` in the same CRC block the build
path already recomputes. V74's "the six pointer arrays must stay byte-identical to stock" was a
SELF-IMPOSED BUILD GUARD, not a firmware requirement.** But **adding** breakpoints is a code edit to the
always-on base-assist damper — the V24/V27/V48B bricking class.

---

## 🛑🛑🛑 RULE 11 — **A CLAMP MAY BE AN INTERLOCK. NEVER RAISE ONE WITHOUT FINDING ITS MONITOR.**

**Added 2026-08-07, and it is the most expensive lesson in this file: it cost two mid-drive total
losses of power steering.**

**`0xC407E` is a DO-NOT-RAISE CELL.** It clamps the friction lane `gp-0x6b26`. Stock value **511**.
One instruction later, in the same 1 kHz tick, **`FUN_00036d74` — called *unconditionally* from
`FUN_0002214a` @`0x2290a` — tests `|gp-0x6b26| / 1024 > cal(0xC4004)`, where `0xC4004` = float `0.5`
= **512 raw counts**, and faults straight to DTC `0x1d`.**

⇒ **Honda set that clamp to exactly ONE COUNT below the monitor's own trip threshold.** It is an
interlock: a clamped signal cannot trip its own fault check. It looks like an ordinary output limit.
**It is not.**

**V73 raised `0xC407E` 511 → 850 — 338 counts past the ceiling — and removed the interlock without
knowing it was one.** **V74 and V75 both hard-faulted with latched total loss of assist.** The cell is
**mode-proof**, which is why V74 faulted with LKAS *disengaged* — no mode-indexed lever could have.

🛑 **CORRECTION OF RECORD, 2026-08-07 (orchestrator's own byte read across the lineage): the ×1.5 friction
table was introduced by V73, NOT V74.** stock / V70 / V71c / V72 carry Honda's row; **V73 / V74 / V75 carry
×1.5 — and V73 raised `0xC407E` in the SAME build.** ⇒ **the two-step narrative this rule used to carry
("V73 raised the clamp; V74 then multiplied the friction row, dropping the crossing requirement from
`gp-0x6c2c` ≈ 6258 to ≈ 4180") is WRONG.** V73 already carried **both** legs and flew clean anyway (n = 1).
**The mechanism and the rule are unaffected; only the attribution is.**
⊕ **The friction row is 14 sites, not one**: `0xCF6E0 0xCF6F0 0xD0A5C 0xD2A4C 0xD2A5C 0xD3A5C 0xD3A6C
0xD4A5C 0xD6A5C 0xD7A5C 0xD7A6C 0xD8A5C 0xD9A5C 0xD9A6C`, Honda's `9ad99ae952f8` → ×1.5 `67c667de7bf4`.
🛑 **`0xD2A4C` is mode 10 — a DISENGAGED-column record.** V74's derivation only ever wrote the 13 engaged
modes, so it never saw m10; any revert there is a revert TO stock and can only make that column more stock.

⚠ **[BELIEF, not EVIDENCE] "`0xC407E` = 850 caused BOTH faults."** The **DTC number was never confirmed
on-car.** What is EVIDENCE (2026-08-07, orchestrator's own Ghidra decompile + a raw Python LE scan of
disp16, the 6-byte disp23 form, LE32 literals and movhi/movea pairs): the monitor `FUN_00036d74` exists,
is **single-frame and un-debounced**, is **mode-proof**, `gp-0x6b26` has **exactly ONE writer image-wide**
(`st.h r6,-0x6b26[gp]` @`0x36CF0`, clamped at `0x36CCC`–`0x36CE2`), `0xC407E` has **0 writers / 3 signed
readers all inside `FUN_00036c12`**, and the build history lines up exactly. ⇒ **at 511 the monitor is
untrippable BY CONSTRUCTION**, whatever the plant, mode or lever set.
★ **V75's fault was NOT the damper**: the damper was identically **zero for 4.98 s** of the last 5 s and
reached only level 2 (128–288) **19 ms** before the trip; peak column jerk was **7,154 °/s² = 4.3× that
route's own p99.9** and the route maximum — exactly what this mechanism predicts.

**The rule, generally:** before raising any clamp, saturation or output limit, **search for a monitor
that tests the same cell**, and check whether the stock clamp sits just inside that monitor's
threshold. A clamp one count under a fault ceiling is a **design invariant**, not slack to be spent.
Two methods; a null here is load-bearing.

⚠ Corollary: **do not "fix" this by raising `0xC4004` instead.** That loosens the monitor rather than
the signal, and no other consumer of that ceiling has been surveyed.

---

### 🛑🛑 CORRECTION OF RECORD, 2026-08-10 — **THE `0xCBE74` FRICTION ROW HAS ZERO CLEAN FLIGHTS ON A LIVE COLUMN, AND IT IS NO LONGER EXONERATED**

**[EVIDENCE — byte-verified by dereferencing `0xCBE74 + mode*4` on the images themselves and reading the
Y array at `record + 8`, not by reading the build scripts.]** The 2026-08-07 correction above got the
*attribution* right (V73 introduced ×1.5, not V74) but left the record implying that V73's clean flight
tested the friction row. **It did not: V73 wrote mode 10 only, which is a DISENGAGED column on a car that
runs modes 24/26.** [[reference-accord-car-is-tvca4-mode-24-26]] · `docs/STATE.md` "AN ADDRESS IS NOT A MODE".

| build | ×1.5 on a **live** column (24/26)? | m24 (manual) | m26 (engaged) | on-car |
|---|---|---|---|---|
| stock / V70 / V71c / V72 | — | Honda | Honda | baseline |
| V73 | **NO** — mode 10 only, **DISENGAGED**, inert on this car | Honda | Honda | flew clean — **says NOTHING about this lever** |
| **V74** | **YES** — the 13 engaged modes | Honda | **×1.5** | 🛑 **HARD FAULT, latched loss of assist** |
| **V75** | **YES** | Honda | **×1.5** | 🛑 **HARD FAULT, latched** |
| **V76** — flown artefact `_v76_v38base_relu_damper` | **NO** — reverted by the V38 rebase | Honda | Honda | flew route 65 clean |
| ⚠ V76 — *other* artefact `_v76_gate_fb_arm5244_gateprobe` | **YES** | Honda | **×1.5** | **never flew** |
| V77 / V77B | **YES** | Honda | **×1.5** | **NEVER FLEW** |

⇒ **×1.5 on a live column has flown exactly TWICE, and BOTH flights hard-faulted. ZERO clean flights.**

🛑 **AND THIS INVERTS A STANDING ATTRIBUTION.** The record above blames `0xC407E` = 850 for the V74/V75
faults. **That attribution is NOT deleted — the monitor mechanism is EVIDENCE and RULE 11 stands** — but
its control has collapsed: **V73 carried `0xC407E` = 850 and flew clean** (byte-verified: V73/V74/V75/V77/
V77B = 850; V70/V72/V76-flown = 511). The only build that was supposed to show "850 alone is survivable"
is the same build that shows the friction row was never live. **V73→V74 is 64 differing runs (13 friction
sites + 51 others), so the friction row CANNOT be pinned** — but the control meant to exonerate it is the
thing that now implicates it.

> ⇒ **STATUS CHANGE: the `0xCBE74` ×1.5 friction row moves from EXONERATED to 🛑 OPEN SUSPECT.**
> **No dose of this row flies again until a probe measures the lane.** The previous "exonerated" status is
> preserved here as a superseded reading, not erased.

⚠ **REFINEMENT the correction does not cover, and it is RULE 10 applied to this row [EVIDENCE for the
bytes, BELIEF for what it implies about cause]:** the two faults are **not** in the same mode.
- **V74 faulted in MANUAL** (LKAS disengaged, over a bump — see RULE 10). Manual is **mode 24**, and
  m24's friction Y array is **byte-identical to Honda on V74** ⇒ **the friction row was NOT in force in
  the mode V74 faulted in.** By RULE 10 that fault cannot be laid at this row.
- **V75 faulted ENGAGED** (operator verbatim: *"after stopping at a stoplight and then continuing like
  normal, with openpilot engaged"*). Engaged is **mode 26**, where V75 carried **×1.5** ⇒ **the row WAS
  live for that one.**
⇒ **"2-for-2 fault association" is the flight-level fact; at the MODE level it is 1-for-1.** Both
statements are true and both belong in a flight decision. Neither restores exoneration: **zero clean
flights on a live column stands**, and V73 still fails to exonerate `0xC407E`.

⚠ **TWO ARTEFACTS SHARE THE V76 BUILD NUMBER**, and they disagree on both cells in this rule
(`_v76_v38base_relu_damper`: friction Honda, `0xC407E` = 511 · `_v76_gate_fb_arm5244_gateprobe`: friction
×1.5, `0xC407E` = 850). 🛑 **The lineage row's BASE column is the discriminator — `_v76_v38base_*` is the
flown one. A GLOB IS NOT A CHECK.** Any script, diff or ledger that resolves "V76" by wildcard will pick
one of the two arbitrarily and silently answer the opposite question.

🛑 **METHOD, and it is the whole reason this went unnoticed:** every row above was produced by
**dereferencing the pointer table and printing the mode number beside the address.** Reading the build
scripts, or matching addresses against a remembered list, is what produced three separate overstatements
about this cell in one session — in both directions. **An address is not a mode.**

---

Full detail: `memory/accord-friction-lane-ceiling-is-the-hard-fault.md` and
`memory/reference-accord-cbe74-friction-row-zero-clean-flights.md`.

---

---

## 🛑🛑 RULE 7, added 2026-08-05 — **A LEVER IS MODE-PROOF, OR IT IS A BET**

**The car is `TVCA4` — row 11 — running mode 24 disengaged / 26 engaged. It is NOT `TVAA1`, and it was
never modes 10/11.** [EVIDENCE] V73's probe read the mode over 104,061 frames and it **toggles with
engagement** (18 edges, all engagement edges). The 4-bit field drops bit 4, so an observed *v* means
true ∈ {*v*, *v*+16}; observed **8** ⇒ {8, 24}, and **raw 8 appears in no row of `0xCD000`** ⇒ manual =
**24**, forced. Only row 11 contains 24, and all four columns come from one row ⇒ engaged = **26**,
forced. ★ **It is the MANUAL arm that closes it — the engaged reading of 10 alone never would have,**
because rows 2/3/6/7 all carry raw 10.

> **RULE 7: classify every lever before proposing it.**
> - **MODE-PROOF** — code edits, and `tp` scalars reached without an index: `0x3AB76`/`0x3AC20`, the
>   `0x3AA96` gate, `0xC6446`/`0xC6444`, `gain_A` `0xC6A68`/`0xC6A7C`, `0xC407E`.
> - **MODE-INDEXED** — anything reached through a `mode*4` pointer array: `gain_B`
>   (`0xCBF5C`/`0xCC044`/`0xCC12C`/`0xCC214`), FactorC `0xC9E9C`, FactorE `0xC9F84`, the friction
>   records `0xCBE74`, the ceiling `0xC77A0`.
>
> **A mode-indexed edit written at the wrong mode is not a weak lever — it is NO lever, and it looks
> flashed, verified and driven.**

★★ **EVERY MEASURED FIX IN THIS KIT CAME FROM A MODE-PROOF LEVER; EVERY MODE-INDEXED LEVER WAS INERT.**
Inert by table selection: **V44, V47, V72's Levers B/C, BOTH of V73's levers, and the entire r24 dose of
V69/V70/V72/V73.**

⇒ **Write every mode, or probe the selector. There is no third option.** The engaged and disengaged
column sets are **disjoint** — engaged (e014/e015) = `{2,3,5,11,14,15,17,23,26,27,29,32,33}`,
disengaged (e012/e013) = `{0,1,4,10,12,13,16,22,24,25,28,30,31}`, **zero collisions across all 16 rows**
— so dosing the engaged columns of every row delivers whatever row is live **while leaving manual
byte-stock.**

🛑 **COROLLARY, and it is the expensive one: several "symptoms" this kit spent builds chasing were
created by its own earlier fixes.** ~~Grind #2 is V62's `sar`.~~ ⇒ **Before adding a lever for symptom X,
check whether X first appeared in the build that introduced the previous lever. A build that changes
nothing is a real and sometimes correct option.**

🛑 **CORRECTION 2026-08-08 (late): "GRIND #2 IS V62's `sar`" IS REFUTED.** **V71C carries NEITHER `sar`
byte** — `0x3AB76` = `AA` and `0x3AC20` = `AA`, byte-stock — **and it produced a spectrally identical
44.31 Hz event**, p99 **1741.9**, holding **3 of the corpus's 13 merged events in 5.28% of exposure**
(**P(≥3) = 0.028**). A symptom that appears on a build without the byte cannot be attributed to the byte.
[EVIDENCE] **The COROLLARY itself is unaffected — only this instance of it is.** Grind #2's origin is
**OPEN**; do not cite V62's `sar` as its cause.

🛑 **AND "FALSIFIED" MUST NAME THE SYMPTOM.** V42 ch.2 was filed *falsified* — against the **vibration**,
never scored against the ratchet, and it turns out to be V42's actual fix. V47 was filed *null* — against
the **21 Hz vibration**, never against the ratchet. **Both were live levers retired for the wrong
question**, and that is a distinct, recurring failure from the mode problem. A verdict without a named
symptom is not a verdict.

---

## 🛑🛑 RULE 8, added 2026-08-06 — **EVALUATE A NO-CLIP RULE ON THE OBSERVED ENVELOPE, NOT A RECTANGULAR GRID**

**V75's clip check produced two DIFFERENT verdicts from the SAME arithmetic, because two agents (and the
operator) policed two different envelopes.** A rectangular (speed × rate) grid rule checks every combination
the axes can independently reach — including corners the car never visits. On this build, the grid's worst
corner assumes **849°/s** of column rate. **Route 5d's actual measured maximum was ~~330°/s~~ 412°/s
(1,941 counts), and zero of its 101,118 frames exceeded 2000 counts** on the axis that matters. A lever
that clips at the grid's corner but never at the corridor the car actually drives is not unsafe — it is
untested at a speed/rate combination that does not occur.

🛑 **CORRECTION, 2026-08-06 (same day): the "330°/s" above was a UNITS ERROR and it flattered the margin
by 25%.** 330 is `|rate_f|`'s maximum in the extractor's own units — the fine CAN field carries a DBC
factor of 0.1 where the true LSB is 0.125 °/s, so the °/s figure under-states the counts by 1.25×. **The
counts figure — 1,941 — is convention-independent and both CAN channels (0x18F fine and 0x14A coarse)
agree on it exactly.** Quote counts, not °/s, whenever a margin depends on it.

🛑🛑 **AND THE BIGGER PROBLEM WITH THIS RULE, LEARNED THE HARD WAY WHEN V75 HARD-FAULTED:
A MAGNITUDE ENVELOPE IS NOT AN ENVELOPE.**

🛑 **CORRECTION 2026-08-06 (second correction, same day) — THE FACTUAL CLAIM THIS BLOCK USED TO MAKE IS
WITHDRAWN.** It read: *"Route 5d contains ZERO engaged stoplight stops … every check V75 passed ran on
telemetry that STRUCTURALLY COULD NOT CONTAIN THE REGIME THAT FAULTED."* **False.** What is true is
much narrower: 5d holds **0.0 s of `latActive` while STOPPED**. But the regime that faulted is a
**LAUNCH**, and **route 5d contains 5–6 engaged stoplight launches by two independent counts — and V74
flew them without faulting.** The envelope *did* contain the faulting regime. **The CHECK could not see
what was dangerous in it.**

**[EVIDENCE] V75's fault is pinned to ONE 100 Hz frame** — route `5e`, t = 284.7947 s: STEER_STATUS→7,
STEER_CONTROL_ACTIVE→0, `gp-0x6880`→1, `0x1AB`'s DTC-active flag→1, all three `0x14A` angle fields→
`0x7FFF`, STEER_SENSOR_STATUS 7→4, **all latched.** ★★ **The faulting launch was the MILDEST of four:**
an earlier one sat on the ±4096 rail **76%** of its window without faulting, the faulting one had
**0.00% rail contact**, and the damper **never reached the `≥448` probe rung (0/39,961 frames).**
300 ms before the latch there is a **20.0 Hz oscillation absent from openpilot's command.**
⇒ 🛑🛑 **MAGNITUDE-BASED MECHANISMS ARE DEAD FOR THIS FAULT — it is a FAST-TRANSIENT sensitivity**, and
a clip rule, a grid sweep and a peak-hold replay are all structurally blind to it.

> **RULE 8b: before citing an observed-envelope pass, state which regimes the envelope DOES NOT CONTAIN,
> and check that list against what the lever changes.** ⚠ **And state the pass as a BOUND, never a
> proof:** a clip rule tests **magnitude only** — it is structurally blind to **step size, switching rate
> and phase** — so an envelope that **does** contain the regime can still pass a build that faults in it.
> Those are GATE 2 questions, and no amount of telemetry coverage substitutes for them.

> **RULE 8: run BOTH checks, and say which is which.** The grid rule (`new > old AND new > ceiling` swept
> over the full rectangular domain) is the CONSERVATIVE, cheap-to-compute bound — pass it and you are safe
> everywhere the axes can reach, including combinations that may never occur. The observed-envelope check
> (the same rule swept over the ACTUAL (speed, rate) pairs seen in real telemetry) is the CLAIM THAT
> MATTERS for what the car has actually done. **A lever that passes only the second is not proven safe in
> general — say so explicitly** — but a lever that fails only the first, at a corner nobody visits, is not
> thereby dangerous. V75 passed BOTH: 0 new clips on the 98,988-point grid, 0 clips on the 101,118 frames
> actually driven (observed peak 354 = 69% of the 512 ceiling) — report both numbers, not just the
> convenient one. 🛑 **AND IT HARD-FAULTED ANYWAY (2026-08-06).** Passing both clip checks is not a
> safety verdict — see RULE 8b.

★ **The free-lever corollary this rule surfaced**: `FactorE X[1]` (400→200) steepens the low-rate ramp
without raising the plateau that sets the surface maximum, so it is free under EITHER check — neither the
grid rule nor the dose ladder found it by construction; route 5d's own telemetry (`probe-5d`) did, because
the observed envelope showed headroom the grid-only view could not see was usable.

---

## 🛑🛑 RULE 10, added 2026-08-06 — **"SINGLE-VARIABLE" IS RELATIVE TO THE MODE THE CAR IS ACTUALLY IN**

**V74 hard-faulted in MANUAL — LKAS disengaged, over a bump — and its headline lever could not have
caused it.** [EVIDENCE, verified two ways] Disengaged is **mode 24**, and all five mode-24 damper records
are **byte-identical to stock** on V74 and V75 — FactorC `0xD67E4`, FactorE `0xD6820`, FactorB `0xD6760`,
FactorD `0xD67A4`, ceiling `0xD60B4` — and **0 of the 54 non-CRC V73→V74 diff runs lands inside a mode-24
record.**

V74 was engaged-column-only **by design** (RULE 7's disjointness corollary — dose the engaged columns,
leave manual byte-stock). That is exactly what makes it **not single-variable in manual**: in manual, V74
is **V73 plus whatever MODE-PROOF cells it also carries**. That residue is the only place a manual fault
can come from — and on V74 the residue included **`0xC63A0` = 2048**, a bare `tp` scalar V72 doubled and
nobody reverted.

> **RULE 10: classify every cell in a build as MODE-INDEXED or MODE-PROOF before proposing it AND before
> exonerating it. A fault observed in mode X can only be caused by cells the car reads in mode X.**
> - A mode-indexed edit is single-variable **only inside the modes it writes**; in every other mode the
>   build is its parent plus the mode-proof residue. **Enumerate that residue in the build spec.**
> - ⇒ *"the lever was in force"* and *"the lever is exonerated"* are **both mode-scoped claims.** Say
>   which mode, every time.
> - ⇒ **A dose ladder built on mode-indexed cells has NO dose in the other mode**, so any `k` fitted from
>   it is defined only where those records are read.

★ **What not having this rule cost:** V74's fault was attributed to the damper dose for a full session,
**`k* ∈ (0.580, 1.580]` was derived from it as a *safe* bracket**, and V75 was built to k = 1.5798 on that
basis. **Both premises were false, and V75 latched the ECU.** The bracket is **VOID** — see the
`0xC9E9C`/`0xC9F84` row in Part 1.

---

## 🛑 Struck hypotheses, 2026-08-05 — do not re-propose

| hypothesis | why it is dead |
|---|---|
| **Saturation / clamp headroom** (`0xC61B2`/`0xC61B4`, `0xC61AA`/`0xC61AC`) | Falsified on **data** — engaged creep in-burst command sits at **27.7% of rail, 0 of 127 frames at rail**, and where it *does* rail burst duty **falls** 35.5% → 12.5% (the rail is protective) — **and on structure**: no reader of any of the four cells lies inside `FUN_00042af8`, and the four sum to **5120**, not 8192. The four mixer channels are **base assist, not LKAS**. `0xC61AA`/`0xC61AC` are dropped from the candidate pool |
| **A 7.8 Hz firmware divider** | mod-100 scheduler ⇒ only **{1000, 500, 200, 100, 10} Hz** are reachable. 7.8 Hz cannot be generated by the scheduler |
| **Stick-slip** | No harmonic series, no trigger, and f0 **falls** with load |
| **State 8, or any `gp-0x67fa` explanation of the damper null** | 🛑 **`0x830 ⊂ 0xc30` is arithmetic** ({4,5,11} ⊂ {4,5,10,11}) ⇒ **every state that runs the aggregator also runs the damper**, so *"aggregator live, damper inert"* cannot come from this variable at all. State 8 fails the converse way: `8 ∈ 0x930` only, so it runs **neither** ⇒ assist would be absent entirely |
| **`gp-0x67fa` aliasing** | All **33 writers store literal constants**; the complete value set is **{1,3,4,5,6,7,8,9,10,11}**, nothing ≥ 12 ⇒ `& 0xf` is a provable no-op, and V70's rung read the **full unmasked byte**. **State 10 really is excluded** |

---

## 🛑🛑 Struck LEVERS, 2026-08-09 (late) — do not re-propose; each killed on EVIDENCE this session

🛑 `FALSIFIED` ≠ `INERT-BY-MODE` ≠ `NEVER-TRIED`, and *"the same lever pushed the other way"* is a
different claim from *"a new lever"*. Every row below is a **structural or measured kill**, not a null.

| lever | status | why it is dead |
|---|---|---|
| **`gain_A` rec0/rec1 LOWERED** (`0xC6A72`–`78`, `0xC6A86`–`8C`) | 🛑 **ENGAGED-INERT — already run, twice failed** | Lever B's gate repoint (`0x3AA96`=`FB`) makes `lp = latActive`, and the armed path at **`0x3AB5E` OVERWRITES `gain_A` with `[0xC6444]` = 512**. ⇒ **V84 and V85 ALREADY deliver 512 engaged at EVERY speed**, deeper than V72/V73's 512/512/1050/2664/2560. This is V84's own §7a **pre-registered** experiment: **FAIL on V84, FAIL on V85.** ⚠ It remains live in the **manual** arm — but the symptom is engaged-only |
| **Lever A** — `0x3AB76` / `0x3AC20` `sar` `AA`→`A9` | 🛑 **DO NOT RESTORE** | the `sar` is **UNGATED**, so it applies in the **manual** arm too ⇒ it reproduces **V62/V65 verbatim** there, and the operator's V65 report on that exact condition is *"makes the entire car vibrate, almost like I have a subwoofer… happens regardless of LKAS engagement."* Second leg: **`r24 ≥ ~2` is necessary for grind #2 in every build that has ever produced it**, and restoring Lever A on a Lever-B base roughly **doubles past** that. ⚠ **The int16-overflow-ceiling leg is WITHDRAWN** — disassembled: `mul` writes a full 32-bit low word and `sar 0xa` operates on 32 bits, so `5120 × 5244 >> 9 = 52,440` fits with headroom. **The verdict stands on the manual-arm leg alone.** Retained visibly: do not cite an r24 overflow ceiling |
| **the 13-point LERP `0xC6B66` / `0xC6B80`** (in `FUN_0003b8f6`) | 🛑 **DEAD as a shaped lever** | its axis `gp-0x6a10` is **ABSOLUTE STEERING ANGLE**, not a tracking error — `b4` ≡ `\|angle\| ≥ 0.85°` at **99.94%**, the step sits **exactly on the threshold's own numeric value**, and the relation holds in the **MANUAL** arm where a tracking error is not even defined. **88.6% of engaged driving sits in its flat first segment** ⇒ its only honest description is a near-constant **0.878× broadband trim**, the same class as V56's mute (null, cost damping) and the `0xC646C` work (null) |
| **FactorD** (mode-record family, `0xD778C` m26 / `0xD77A4` m27) | 🛑 **STRUCTURALLY INERT where the symptoms live** | FactorC is multiplied in **BEFORE** FactorD and has `X[0]` = 2240 counts = **34.97 km/h** with `Y[0] = 0`, in **all four** of this car's modes. **Zero × anything = 0.** A third `gp-0x6a10` consumer — the boost LERP2 in `FUN_00034a72` — is **also** flat-zero in band0 (0–8 km/h) in all four modes. **Three independent confirmations.** 🛑 This also **REFUTES *"FactorD is the only frequency-selective lever in this firmware"* — THIS FIRMWARE HAS NONE**, which removes the argument that FactorE cannot do what FactorD can |
| **`0xC63A0` 1024 → 2048** | 🛑 **INERT — no mechanism** | `ch₀ = gp-0x6bd0 = clamp((FactorC(speed) × FactorE(rate)) >> 10, ±ceiling)`; Honda's shape has **two zero dead zones** (FactorC below 34.97 km/h, FactorE below 12.73 °/s, both `Y[0] = 0`) and the product truncates ⇒ **`ch₀` is exactly ZERO on 98.8% of engaged frames on route `6e`** (p50 **and** p90 both 0.00 counts, against a ±25600 clamp). ⊕ **V42 flew at 1024 and the operator called the ratchet fixed ⇒ 2048 is not necessary.** ⊕ **V72/V73 also carried Honda's damper**, so `ch₀` was zero on them too ⇒ **the V72/V73 correlation has NO mechanism.** ⊕ ⇒ **V84's own `0xC63A0` revert was itself INERT** and cannot be the cause of the V84 step |
| **`0xC61F6` = 3 → 0** (the rate-lane deadband) | 🛑 **DO NOT — it pushes the destabilising way** | a deadband is the **DUAL of a relay**: `N(A) → 0` as `A → 0` is precisely what *prevents* harmonic balance from closing. **Deleting it ADDS small-signal gain.** It costs **0.4%** at the lane's ~1029-count full scale and **exactly nothing** whenever the total sits >3 counts off zero. ⚠ This **reverses** the E12 framing that opened it as a candidate |
| **`0xC61D6`** (shaper slew step, stock 0) | 🛑 **ALREADY REJECTED — do not revive** | an 11-round review labelled it *"highest-risk; last/never"*: it does **not** re-enable an anti-snap ramp, it **activates a dormant, uncalibrated speed × torque 2D map** onto the live command. `0xC6424` is separately confirmed **inert** (coupled to slew = 0). ⇒ 🛑 **There is NO usable cal-only rate-limiter lever on this path.** (This is the second time a subagent has re-proposed `0xC61D6`; see the Part 1 note) |
| **`FUN_00038148` / `gp-0x6b70` as the ~8 Hz generator** | 🛑 **REFUTED** | odd/even harmonic comb **0.858 [0.739, 1.000]** against a positive control reading **1.204 [1.147, 1.566] at just 15% injection**; 3:1 PLV **z ≤ 1.05**; switching-surface time-locking **−0.0375**; a second method finds no third harmonic ⇒ **<15% of the ~8 Hz bar content can be relay-generated.** The chain stays interesting; **this hypothesis about it does not** |

### 🛑🛑 THREE NEW "FLATTEN-A-CURVE-INTO-A-RELAY" HAZARDS — the V72/V80 error, one address family over
Each of these is a **one-cell edit that converts a shaped nonlinearity into a full-authority relay.**
V80 is the recorded cost of doing exactly this once already: **the worst grinding in this car's history.**

| cell | stock | 🛑 forbidden move | what it produces |
|---|---|---|---|
| **`0xC4080`** | **0** | **NEVER RAISE** | `FRICTION += cal/1024 × ratio` with **no `\|model\|` factor** ⇒ a **latent PURE COULOMB RELAY**: amplitude-independent and unbounded in index |
| **`0xC63AE`** | 1024 | **never → 0** | the LERP index becomes ≡ 0 ⇒ output ≡ `±Y[0]`, a constant ⇒ **a pure relay at full authority** |
| **`0xC6200`** | 8192 | **never < `Y[0]`** | the clamp does the same thing from the other side. ⊕ Separately: `0xC6200` has **15 readers**, and the governor cals `0xC6202/04/06/08` cluster **disjointly** at `0x045410`–`0x0457de` ⇒ **`0xC6200` is NOT governor-shared** (confirmed twice; V40 wrote `0xFFFF` to `0xC6206`/`0xC6208` and left `0xC6200` untouched). **3 of its 15 readers are still unidentified** ⇒ RULE 11 census is **not** complete |

⊕ **RECORDED, VIRGIN, UNTESTED AND NOT PROPOSED** — so it is not "discovered" as new next session:
`FUN_00036388` contains a **relay-with-dwell** — dwell counter `gp-0x6a82`, +1/tick while
`|gp-0x6b64| < 0xC618A` (= 1024), ceiling `0xC627E` = 20; **past 20 ticks the output SNAPS to 1024**,
writing `gp-0x6b62`. Cals `0xC618A` / `0xC627E` / `0xC63C0` were **never edited by any build**
(grep-confirmed). **Disfavoured by the same no-comb evidence that refuted `gp-0x6b70`.**

### 🛑 `gp-0x67fa` — the reachable set is effectively **{11} ALONE**, and that KILLS `0x454FE`
State 5 is **structurally dead**, state 10 measured **0.0000%**, state 4 measured **0/123,277**.
⇒ **V42's `0x454FE` is present on V85 (`0xB5`) and MEASURED INERT.** Keep the byte — it has been silently
lost three times and costs nothing — but **carrying it is NOT addressing ratcheting**, and no build may be
justified on it. ⊕ **`gp-0x671a` is RULED OUT** as a lever axis: stuck at 0 across **1,158 reversals** on V64.

---

## 🛑 Ledger corrections, 2026-08-09 (late) — each from a byte read of the build's OWN image (RULE 4)

| # | correction |
|---|---|
| 1 | **`0xC63A0` was reverted at V83a, NOT at V84.** The lineage row previously implied V84. |
| 2 | **`V76g` ALSO carried `0xC63A0` = 2048.** It was missing from the "who ever moved it" list. |
| 3 | **`V76` and `V80` are `0xC63A0` = 1024**, not 2048. |
| 4 | **The V85 frozen-cell count is 12, not 14** — `build_v85_tva.py` declares 10 `FROZEN_CELLS` + 2 `FROZEN_BYTES`. No 14-item list exists; the "14" in this file refers to the **14 friction sites**, a different set. |
| 5 | **The mode-record pointer space is 340 slots (10 arrays × 34 modes), not 58**, and there are **34 non-stock records**, including modes **32/33**. A count-only census is blind to a write into an **already-non-stock** record ⇒ **assert every record byte-identical to the BASE unless declared.** |

---

## 🛑 Ledger corrections, 2026-08-05 — each from a byte read of the build's OWN image (RULE 4)

| # | correction |
|---|---|
| 1 | 🛑 **V69 AND V70 DID NOTHING.** `sar` stock (`aa32`/`aa42`), gate `c5`, arms 512/512, and the only edit is `gain_B` **mode 10** ⇒ **byte-stock behaviour**. The recorded *"clean single-variable r24 series ×1→×2→×4 = 879/729/746, CIs overlap ⇒ r24 is near-inert"* was **three replications of ONE condition.** ⇒ **r24's dose is UNTESTED, not near-inert** |
| 2 | **V72's two-lane row is `r24 ×1.000 / r26 ×0.250`**, not `3.414 / 0.250` — its r24 half was mode-10 `gain_B`. Its grind-#2 result is therefore **confounded with stock**. 🛑🛑 **THE SECOND HALF OF THIS ROW IS RETRACTED 2026-08-06:** it read *"what governs grind #2 is V62's `sar`, which V72 does not carry"* — **that is hypothesis (A) and it is REFUTED.** `V71C` carries **neither** `sar` byte (`0x3AB76` = `aa32`, `0x3AC20` = `aa42`, byte-read) and produced a spectrally identical grind-#2 event: **44.31 Hz**, p99 **1741.9** = **12.2×** the max of any non-bursting build, against a same-segment non-burst floor of **25.5**. V71C holds **3 of the corpus's 13 merged events in 5.28% of the exposure, P(≥3) = 0.028.** ⇒ **a `sar`-stock build is NOT safe by construction** |
| 2b | **V62/V65's delivered r24 is `×2.000`, not `×3.414`** — `sar 0xa → 0x9` is a **flat doubling of BOTH lanes at every speed and rate** (mode-proof, one instruction each), not the `0xC6446` arm. The 3.414 figure was the *arm* value copied across the whole column. ⇒ **the two-lane rule's "r24 ≳ 3.4×" threshold is WRONG — V62/V65 burst at 2.000×.** The rule's *shape* ("both lanes elevated") survives; its *numbers* do not. Rebuilt table: `docs/STATE.md`; model: `analysis-2020accord/_grind2_delivered_lib.py` |
| 3 | ★★★★ **V42's fix was the r26 KILL, not `0x454FE`.** V42 vs V41: `gain_A` **all four records → `[0,0,0,0]`**, `0xC643E` 1536→0, `0xC6444` 512→0, plus a revert of V41's motor-rate cap. `0x454FE` never executes. **This closes a two-session [OPEN]** — and V42 ch.2 sat in this table marked *FALSIFIED* the whole time (see RULE 7's last paragraph) |
| 4 | **V72/V73's r26 cut is PARTIAL** — `gain_A` `rec0`/`rec1` → flat 512, but **`rec2` `0xC6A90` and `rec3` `0xC6AA4` are byte-stock** ⇒ the cut is **creep-only by record selection**; at and above ~50 km/h r26 is untouched |
| 5 | **`tp+0x71b2` IS load-bearing** — LKAS reaches the motor via the second accumulator `gp-0x62b0[ch]` → `gp-0x3d88` → `gp-0x6b4c`. **No V14 correction is needed** (one was proposed and withdrawn). Lineage byte-verified over 66 images: stock **512** → **1024 by V22** → **2048 at V38**, `0xC61B2`/`0xC61B4` always in lockstep. ⚠ The V14/V15 first step is build-script prose only — no image exists before V22 |

---

## 🛑🛑🛑 RULE 9, added 2026-08-06 — **THE GRIND-#1 FIX AND GRIND #2 HAVE NEVER BEEN SEPARATED**

🛑🛑 **RULE 9's DRIVE PROTOCOL IS RETIRED, 2026-08-09, by operator decision.** The prescribed manoeuvre
(empty lot, openpilot engaged throughout, 4–11 km/h, wheel ≥100° from centre, continuous figure-eights at
100–500 °/s, 6–9 minutes, plus a 60 s LKAS-off control) has been **missed by four consecutive builds** —
route `6d` accumulated **5.1 s against its own 166 s floor (3.1%)**. It is retired rather than re-issued:
it asks for an artificial low-speed manoeuvre under LKAS, and **the 40–49 Hz events the operator actually
reports occur on ordinary roads at 56–62 km/h** (both route-`6d` events), not at engaged creep.
⇒ **Any claim about 40–49 Hz at engaged creep is UNMEASURED and must be labelled so. Do not schedule the
drive; do not quote a zero-count from it as evidence.** The rest of RULE 9 — that the grind-#1 fix and
grind #2 have never been separated — still stands.

**Before proposing any rate-lane lever for grind #1, read this row. It is the reason the trade looks
solved in the record and is not.**

**[EVIDENCE]** Split-half null computed **first** inside the stock-lane pool with the identical estimator
= **[0.663, 1.502]**; grind #1 = p90 of the 18–22 Hz envelope over engaged-creep windows, episodes
resampled. **The builds that measurably moved grind #1 are EXACTLY {V62, V65, V67, V68, V71C}.**

| moved grind #1? | build | grind-#2 events | engaged creep-CORNER s | engaged HIGH-RATE creep s |
|---|---|---|---|---|
| **YES** | V62 · V65 · V71C | **present** | 74.2 · 189.4 · 23.0 | 21.8 · 120.3 · 6.4 |
| **YES** | **V67 · V68** | not observed | **11.5 · 0.0** | **0.0 · 0.0** |
| no | V58·V59·V61·V64·V69·V70·V71B·V72·V73·V74 | none | 3.8 – 56.3 | 0.0 – 21.8 |

⇒ **EVERY BUILD WITH ADEQUATE GRIND-#2 EXPOSURE FAILED TO MOVE GRIND #1, AND EVERY BUILD THAT MOVED
GRIND #1 EITHER SHOWS GRIND #2 OR HAS ESSENTIALLY NO EXPOSURE IN THE BURST REGIME.**
The two are **perfectly collinear.** **No build has ever demonstrated one without the other at usable
power.** 18 of 21 creep burst windows sit at |ang| ≥ 100°, and V67/V68 hold **11.5 s** and **0.0 s** there.

🛑 **A "grind #2 = none" cell for V67/V68 is NOT a measurement — it is 11.5 s at P(0) = 0.80.** The
operator's own V67 report hedged precisely there (*"might still be there somewhat … more so LKAS-engaged
at low-speed … might just be dampened"*) and the hedge was recorded as "none".
✅ **The fix costs no bytes: ~90 s of deliberate ENGAGED hard cornering at creep on the next rate-lane
build** takes P(0) from ~0.61 to < 0.05 in one drive. **Ship that instruction with every such build.**
Scripts: `analysis-2020accord/grind2_collinearity.py`, `grind2_delivered_verdict.py`,
`grind2_delivered_census.py`.

---

## 🛑🛑 RULE 6, added 2026-08-05 — **A LEVER IS ONLY IN FORCE IF THE CAR READS THE TABLE YOU EDITED**

**V72 raised the base-assist damper at creep. The bytes were correct, the arithmetic was correct, the
CRC passed, and the car never read them.**

`FUN_00034350` selects **all five** damping factors — B, C, D, E **and the ceiling** — through pointer
arrays indexed by `mode * 4`, where `mode = *(byte)(gp + 0x63fd)`. **There are 13 mode variants.** V72
edited **modes 10 and 11 only**, because `39990-TVA-A160` *reads as* row 2 `'TVAA1'` in the config table
at `0xCD000` ⇒ modes 10/11.

🛑 **That part-number → key mapping is an ASSUMPTION recorded in this file. It was never a measurement.**
`build_v44_tva.py` has patched modes 10 **and** 11 since V44 *because of it*, and every damping build
since inherited it.

**The probe settled it arithmetically.** On V72, modes 10/11 give `|gp-0x6bd0| = 389` **unconditionally**
(FactorC ≥ 430 at every speed, FactorE = 927 at every rate) ⇒ `bit4` (`|gp-0x6bd0| ≥ 64`) would fire on
**100%** of frames. **It fired on 0 of 87,940, including 0 of 34,275 above 35 km/h.**
⇒ **[EVIDENCE] the car is not in mode 10 or 11; Levers B and C were inert by TABLE SELECTION.**

> **RULE 6: before recording a cal edit as tested, establish that the car reads THAT RECORD — not merely
> that the bytes changed and the CRC passed. For any mode-, variant- or config-indexed table, the
> selector is part of the lever. Probe the selector, or treat the result as a null by construction.**

★ The general form is worse than this instance: **a mode-indexed table makes a lever look flashed,
verified and driven while being structurally unreachable.** Every prior "damping is null" result on this
kit (V44, V47, V72) is now **uninterpretable**, not falsified.
⚠ Still open: **which mode is live.** Modes 4/5 and 12 are fully consistent with the measurement, 0–3
marginally disfavoured, 10/11 excluded. **V73 reads `gp+0x63fd` directly.**

---

## 🛑🛑 RULE 4, added 2026-08-05 — **TWO LEDGER ERRORS FOUND, BOTH RUNNING THE DANGEROUS WAY**

A machine byte-diff of **all 65 built plain images** vs stock over `[0x13000,0x100000)` found two errors
in this file. Both made a lever look *tested* when it was not — the direction that suppresses work.

1. 🛑 **Part 1 attributes four cals to V39 that V39 NEVER WROTE.** The row
   `` `0xC6440/42/46`, `0xC61F6` | V39 | ✅ | FALSIFIED `` is **false**. **V39's entire delta vs V38 is
   `0x3AC78` (4 bytes, a cave hook).**
   - **`0xC6442`** — written by **0 of 65 images**. **UNTESTED**, and separately **unreachable**:
     `gp-0x671d` reads **0 / 402,424 frames** across four routes.
   - **`0xC61F6`** — written by **0 of 65 images**. **UNTESTED.**
   - `0xC6440` — V63/V64 only, null-by-construction. `0xC6446` — V67/V68/V71C only, and only with the gate.
2. 🛑 **V71B and V71C do NOT carry V62's `sar` fix.** `0x3AB76`/`0x3AC20` = `a9` in **exactly three
   images: V62, V65, V71A** — and V71A is unflashed. **The two builds flown 2026-08-04/05 carry NEITHER
   of V62's bytes.** Say this before anyone reads V71B/V71C as "V62 plus something".
✅ **No third silent loss exists** — every carried edit was checked across all 65 images.

> **RULE 4: attribute a lever to a build only from that build's own byte diff, never from this table's
> prose. Two of the entries here were wrong, and both errors ran toward "already tested".**

---

## 🛑🛑 RULE 5, added 2026-08-05 — **A NULL IS ONLY A NULL IF THE LEVER WAS IN FORCE**

**`0x454FE` was recorded mid-session as FALSIFIED for the ratchet because V71B and V71C flew with it
restored and the operator reported no change. That was wrong.** V71's own probe measured
**`gp-0x67fa == 4` at 0 / 123,277 (route 54) and 8 / 92,826 (route 58) — all eight in PARK.**
**State 4 never occurred while driving, so V42's substitution never ran on either drive.**
⇒ **a null by construction**, the same class as `0xC6444` on gateless builds.

> **RULE 5: before recording any lever as FALSIFIED, state HOW you know it was in force on that drive.
> If the answer is "the build carried the byte", that is not sufficient — a byte that never executes is
> not a test. Prefer a probe rung on the lever's own enabling condition.**

★ What survives is stronger than the retracted claim: since state 4 never occurs, the substitution
**never runs on stock either** ⇒ **structurally eliminated** as the 7.79 Hz ratchet's cause.
⚠ **[OPEN]:** V42 was CONFIRMED on-car against the *hard-turn recovery* ratchet. If state 4 never occurs,
that fix could not have acted either. Unresolved.

---

## 🛑🛑 RULE 3, added 2026-08-04 — **"CONFIRMED" DOES NOT MEAN "STILL ON THE CAR"**

**This file records what a lever DID. Until now it did not record whether the current build still
CARRIES it — and that gap cost this kit roughly ten builds.**

> **RULE: for every lever you cite, byte-check whether it is present in the CURRENT build's plain
> image (`../accord-firmwares/analysis-2020accord/_v<NN>_plain_image.bin`) before reasoning from its
> result. A confirmed fix that is no longer carried is not evidence about the car you are driving.**

**The two instances that motivated this rule — both found 2026-08-04, both by byte-reading all 60
built images:**

| lever | what it fixed | confirmed by | carried by | how it was lost |
|---|---|---|---|---|
| **`0x454FE`** `bne`→`br` | the **RATCHET** — state-4 governor magnitude substitution | **V42, "CONFIRMED ROOT CAUSE, carry forward"** | **V42→V52C only** | 🛑 **SILENT REBASE LOSS.** V53+ descends from V38/FOURFRAME, which branched *before* V42. Nobody decided this |
| **`0x3AB76` + `0x3AC20`** `sar 0xa`→`0x9` | **GRIND #1** — 8× at creep, 42× at \|rate\| 16–32; the kit's only measured grind fix | **V62** | **V62, V65 only** | ⚠ removed as **V66's confirmatory control** and **never restored**. The effect was then re-created twice in other encodings that dose **r24 only**, and the ladder still labels those "2×" |

⇒ **From V66 to V70 the car carried NEITHER confirmed fix**, while the record read as though both were
carried. The `0x454FE` case is worse than bookkeeping: the argument that later retired it as a cause of
the *current* ratchet — *"`STEER_STATUS == 4` fires 0/37,922"* — was **voided** when bus `STEER_STATUS`
was shown not to be `gp-0x67fa` (state 4 sits inside all three gate masks). **It was never actually
eliminated.**

★ **And the general form of the second case is the more dangerous one:** a lever removed *on purpose*
as an experimental control is indistinguishable, six builds later, from a lever that was never needed.
**When you remove a confirmed fix to run a control, write the restore into the next build's spec.**

---

## Part 1 — Lever index, by address

🛑 **MOVED, 2026-08-12 — this section now lives in
[`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md`](BUILD-LINEAGE-PART1-LEVER-INDEX.md)** (137 KB), verbatim,
because this file had grown past the 256 KB `Read` cap and its tail was silently invisible.
**Grep that file by address before proposing any calibration edit.** Nothing was deleted.

---

## Part 2 — Code caves are the only bricking class

**Three of this kit's code caves bricked the ECU: V24, V27, V48B.** Every success since V29 has been
cal-only or a single in-place branch/displacement edit.

- **V27** — bricked from **ASYMMETRY**, not magnitude (float twin doubled wholesale vs int corridor-only).
- **V48B** — bricked from (a) RAM collision: biquad state `gp-0x14FA` aliased a live monitor status byte,
  and (b) an unmodelled lightly-damped resonator inserted into the always-on base-assist loop.
- **V40** — not a cave, but the same lesson: the defect was the **magnitude** of a cal write, not its
  direction.

⇒ **TWO MANDATORY GATES for any cave / filter / dynamics change** (apply without being asked):
- **GATE 1 — RAM OWNERSHIP.** Every byte of the full multi-byte footprint proven free *including writers*
  and register-indirect / 6-byte-extended-displacement accesses. `gp-0x1401..0x1502` is poison (it is a
  subset of the `0xb7260` I/O-mailbox array). **Static clearance is not sufficient — `gp-0x1500` passed
  both static methods and still failed on-car.** A live probe is the only reliable RAM-ownership test.
- **GATE 2 — CLOSED-LOOP STABILITY.** Magnitude *and* phase of **every loop the touched signal is in**,
  especially the always-on base-assist loop. Never a single-frequency magnitude.

**A 2-byte in-place displacement or branch-condition edit is a different, far lower risk class than a
trampoline + cave.** Do not conflate them.

### 🛑🛑🛑 GATE 2 COROLLARY, added 2026-08-07 — **"DOES NOT CLIP" AND "IS NOT A RELAY" ARE DIFFERENT STATEMENTS, AND ONLY THE FIRST WAS EVER CHECKED**

**This is the specific defect that let V80 through its own gates and produced the worst grinding this car
has ever made.** [EVIDENCE]

Every no-clip guard in this kit tests **`product > ceiling`**. V80's damper supremum is
`(566*927)>>10 = **512** = the ceiling **exactly**, so it clips **0.00%** — and the guard passed, twice,
on two different envelopes. **A guard of that shape is STRUCTURALLY BLIND to `product = ceiling − 17`.**

V80's flat-`FactorC` edit was adopted *because* it removed the clipping that made V79 a relay. It did not
remove the relay. **It MOVED it** — off the ceiling clamp and onto **`FactorE`'s own knee, 17 counts under
the rail**, where the slope drops ~1200× at `X[1] = 119`. The delivered surface is a **constant 495 counts
across a 34× rate range at every speed**: a near-bang-bang Coulomb law wearing a no-clip certificate.

> **THE RULE: a saturation test is not a linearity test.** Before flying any shaped surface, score the
> **shape**, not just the bound:
> - **Flatness over the operating range.** Quote `max/min` of the delivered output across the rate span
>   the car actually visits. V80's was **1.034 over 34×** and nobody computed it.
> - **The describing function `N(R)`.** Constant `N` = viscous = stabilising; `N` rising as amplitude
>   falls = relay = limit-cycle generator. **Report `N(50)/N(500)`.** V75 = 1.45×; V80 = **3.27×**.
> - **Distance to the rail, in counts.** "0.00% clipped" at `ceiling − 17` is not margin, it is a rail with
>   a rounding error in front of it.
> - **A probe rung sized to the saturated regime, and a flown build to compare it against.** V75 read
>   `|gp-0x6bd0| ≥ 448` at **0.000% of 28,317 engaged frames**; V80 read **19.4%**. That single pair is the
>   cleanest statement of the root cause in this file, and both numbers came from the builds' own caves.

⚠ **The hazard is not new and the kit had already named it** — RULE 12(b): *"a railed factor whose sign
comes from a different cell (`gp-0x6abe`) than its index (`gp-0x6ac0`) IS the Coulomb relay this kit
forbids at `E_Y[0]`."* **The failure was that the test written for that rule only ever policed the
ceiling.** ⇒ **Whenever a rule names a hazard, check that the test actually discriminates it — not merely
one sufficient condition for it.**

### 🛑 A RE-CUT UNDER THE SAME BUILD NUMBER DESTROYS ITS PREDECESSOR'S PLAIN IMAGE — open, 2026-08-04

**The hazard, stated as it actually happened.** Two V70 cuts were built 19 minutes apart. **Both wrote
`_v70_plain_image.bin`**, so the second silently **overwrote** the first's snapshot. The first cut's
`.rwd` survived and was flashable. ⇒ **a flashable artefact existed that NO gate in this kit could
check**: `verify_v70_image.py` asserts the *current* topology (`0x3AA96 == 0xC5`, `0xC6446 == 512`), so
it **fails on the superseded build by construction**, and `diff_build_vs_stock.py` has no image to read.

⚠ **The only reason the superseded cut's bytes are documented at all is that they were read inside the
19-minute window before the overwrite.** That is luck, not process.
✅ The *flash* risk was closed by renaming it `SUPERSEDED-DO-NOT-FLASH-…` (`accord-firmwares` `9d44efc`).
🛑 **The verifiability hazard is NOT closed and applies to every future re-cut.**

**RECOMMENDED FIX FOR THE NEXT BUILDER — NOT DONE, and deliberately not retrofitted this session:**
- write **`_v<NN><tag>_plain_image.bin`** (tag from the build's own `TAG`), so a re-cut cannot collide;
  **or**
- **refuse to overwrite** an existing snapshot whose SHA differs from the one about to be written,
  unless explicitly forced.

**Every builder in the tree still writes the fixed `_vNN_plain_image.bin` name.** This entry is a
recommendation, not a description of a fix that exists — do not read it as done.

⚠ **The superseded V70 image cannot be trivially regenerated** — its builder configuration no longer
exists in the tree. In principle it could be recovered by decoding the surviving `.rwd` back to an
image. **That was NOT attempted**, and was judged not worth it for a superseded do-not-flash artefact;
recorded so the gap is explicit rather than ambiguous.

★ Related and distinct: **`bit6 ⇒ bit3` gives build-CLASS identity, never FILE identity** — a probe
cannot separate two cuts of the same version, because their caves are identical. **The filename is the
only pre-drive discriminator between re-cuts**, which is why the rename is load-bearing rather than
cosmetic.

### 🛑🛑 GATE 4 for PROBES, added 2026-08-04 — **read the GAIN IN FORCE, not a lane OUTPUT**

**Four consecutive probes have now returned an uninterpretable zero by reading a lane output** — V64,
V67, V68 (`gp-0x67df`) and **V70's bit6 (`gp-0x6ada >= +512`, 0/18,010)**.
★ **V70's is the informative one, because it is NOT vacuous:** a replay through the **shipped** surface
driven by **route 50's own data** predicts **311 hits**; **stock predicts 52**; observed **0**. And
`|dtorque|` off a 100 Hz grid is a **lower** bound, so the gap cannot be closed in the safe direction.
⇒ **delivered gain < ~1574 Q10, below stock's 3072**, and **`0xC6442` = 1024 (the `gp-0x671d` mask arm)
is the ONLY arm in the selector predicting exactly 0.**
✅ **The identification was verified and is not at fault** (`0x3AC42`–`0x3AC54` = `r24 = clamp(r6,
±0x2000)`; `0x3AD5A st.h r24,-0x6ada,gp` stores exactly that, r24 unclobbered through the add chain).

⚠⚠ **BUT ARM SELECTION IS THE WEAKER READING — SOFTENED 2026-08-04.** **The same rung read 0/47,990 on
V69's route `4f`, at DOUBLE V70's dose**, where it needed only **49 counts** of `|dtorque|` against a
repo max of **839** — a **much larger** anomaly, and one that **does not fit arm selection**: under (b)
the mask arm is **1024 on every build**, so it cannot produce a **dose-dependent** miss. And **V67 read
`gp-0x671d` 0/150,327 on route 47**, so the mask would have to be set near-continuously on `4f` *and*
`50` but never on `47`. ⇒ **[BELIEF] (a) — an under-ranged or MIS-RECONSTRUCTED rung — is the
better-supported reading** (the `dtorque` figure is a **4-sample 1 kHz difference rebuilt from a 100 Hz
bus copy of a different, filtered torque cell**; polarity is the other candidate). **(b) is possible but
less parsimonious; the corpus cannot settle it**, and grind #1 cannot adjudicate it either (it is blind
to r24 gain — see Part 1). 🛑 **The DURABLE part is the rule below, not the mechanism.**

> **RULE: spend a probe bit on the SELECTOR/MASK that decides which gain is in force, before spending
> one on the lane's output.** A mask bit is one bit and is never ambiguous; an output null cannot
> separate *"the lane is quiet"* from *"the gain you think you shipped is not the gain in force"*.
> V71's **bit6 = `gp-0x671d != 0`** is the first rung in this kit built to that rule — and it carries a
> **two-sided, low-threshold r24 mirror rung** alongside it, so an under-ranged reconstruction cannot
> hide again.

---

### 🛑 GATE 3 for PROBES, added 2026-08-04 — size a rung against the LANE's own reachable output

**A probe cannot brick an ECU, but it can waste the only telemetry budget this kit has, and V69 wasted
all three rungs at once.** The rule that would have caught it:

> **Before choosing a threshold, compute the producing lane's own reachable output range at the
> operating point you care about — its clamp, its LERP ceiling, its index axis — and state that number
> in the build note. A downstream GATE's width is not that number.**

🛑🛑 **SECOND INSTANCE, V84, and it nearly cost a verdict — 2026-08-09.** V84's `b7`/`b6` tested
`|r24| ≥ 1024` on a lane whose input **never exceeded `|r1| = 201`** ⇒ they read **0.0 across 68,235
frames in BOTH arms**, and that was read as *"the lever was out of force."* It was not: **the rung could
not have fired either way.**
📋 **THE RULE IN ITS SHARPEST FORM: a falsifier only fires if it COULD have fired.** Apply it to every
pre-registered falsifier and every abort criterion, **including the ones that come back clear** —
V85's damper abort criterion "passed" on **22.4 s** of engaged ≥80 km/h exposure, which is not a pass.
🛑 **This is RULE 5 (a null is only a null if the lever was in force) applied to the INSTRUMENT rather
than to the lever, and the kit has now made the error at both ends.**

**V69 bit4 — `gp-0x6ad4` ≥ +4096 — was STRUCTURALLY VACUOUS and could never have fired, on any build,
on any drive.** The lane is clamped to **±CEILING = MIN of three LERPs**; the binding one is
`0xC67C2`/`0xC67C8`, indexed on **voted vehicle speed**, **max 1024**, and it **starts at ZERO**. At the
four ratchet episodes' speeds (**4.9 / 6.8 / 7.8 / 8.0 km/h**) CEILING was **164–341** ⇒ the 4096 test
sat **12–25× above the lane's entire reachable range**.
🛑 **ROOT CAUSE: the design read the ERR *input* clamp `±0x2800` as if it were the lane's OUTPUT range.**
★ It also explains, retroactively, **why V56's mute of this same lane changed nothing** — there was
very little there to mute at creep.

Two more, from the same build, both worth carrying forward:
- **bit5 (`gp-0x6b62` ≥ +4096) was INSENSITIVE, not vacuous.** Reachable max **5786**
  (`|gp-0x6b5e| ≤ 4762` from the trapezoid `0xC66CC` X = [−384, −128, 128, 294, 384],
  Y = [0, 4762, 4762, 717, 0] with `0xC63C2` = 1024, plus a latched `|sVar8| ≤ 1024`), so 4096 was
  **71% of full range** and the rung only saw the **top 29%**.
- **bit6 (`gp-0x6ada`) had NO EXPOSURE.** The replay predicts **~1** one-sided hit on route `4f`;
  observed **0**; **p ≈ 0.37.** That is a power problem — **not** the V64 gate failure — but it is also
  **not a positive control**, so bits 5/4 could not be interpreted against it.

⇒ **All three rungs were one-sided, and both middle rungs were sized against a downstream gate width.**
Budget a probe the way you budget a cave: **enable + raw input + a rung whose range you have computed.**

### ★★★ THE RATCHET'S Q IS MEASURED — Q ≈ 40 at f0 = 7.793 Hz (2026-08-04, route `50`)

**[EVIDENCE]** From a **12.81 s provoked episode**. ★ **The invariance test is what makes it real:** Q
reads **39.0 with a window cap of 54** and **40.0 with a cap of 111** — a window-limited estimate would
have **doubled** when the cap doubled. It did not. ⇒ **ζ ≈ 0.0125, ~3× more lightly damped than the
21 Hz mode.**
✅ **Q ≈ 40 CONFIRMS the record's Q ≈ 36.** 🛑 **The only thing SUPERSEDED is *"Q is not measurable at
NFFT 256"* — the claim that it could not be measured, not the value.**
✅ **And it is NOT contaminated by the driver's input** — the episode reconciles exactly with the
transition trace below (envelope-based p-p, 2 × 2,452 = 4,904 ≈ 4,894; speed span matches seg1
`t` ≈ 33–46, the **post-engagement** window, not the cranking).
⚠ **It rests on ONE episode** — a second ≥10 s episode would make it two. ⚠ **f0 drift inside the
window would DEFLATE Q, so 40 is a LOWER BOUND**, not a point estimate.

#### 🛑🛑 ENGAGEMENT-**REQUIRED**, NOT CONDITIONAL — AND NO BUILD HAS EVER MOVED IT

**[EVIDENCE]** Grip confound removed (both arms **hands-off**, `|lowpass(tq,3Hz)| ≤ 300`, creep
< 4 m/s), pooled over four routes and four builds:

| route | engaged hands-off | manual hands-off | Fisher p |
|---|---|---|---|
| V70 `r50` | 4/5 = **80%** | 0/35 = **0%** | 5.5e-05 |
| V69 `r4f` | 22/27 = **81%** | 0/20 = **0%** | 9.4e-09 |
| V62 `r37` | 31/39 = **79%** | 0/39 = **0%** | 2.3e-14 |
| V59 `r2c` | 16/17 = **94%** | 0/24 = **0%** | 1.7e-10 |
| **POOLED** | **73/88 = 83.0%** | **0/118 = 0.0%** | **3.8e-41** |

**ZERO hits in 118 manual hands-off creep windows / 302 s.** ⇒ 🛑🛑 **the rate is BUILD-INDEPENDENT
(80/81/79/94%) — NO BUILD IN THIS KIT HAS EVER MOVED THE RATCHET.** ⚠ **This SUPERSEDES the earlier
"engagement-conditional, 44/46 windows" statement.** ★ Converse: **a hand on the wheel SUPPRESSES it
while engaged** — V59 94% → 14% (p = 3.5e-4), V69 81% → 37% (p = 4.5e-3).
★★ **What that buys: `0x454FE` is a genuinely UNTESTED lever for the ratchet** — it has not been on the
car during a single one of those four measurements (V59/V62/V69/V70 are all post-V53, all stock at
`0x454FE`). ⚠ **A reason to restore it; NOT evidence it will work.**

#### ★★★★ THE TRANSITION TRACE — the mechanism, second by second, at constant speed

**[EVIDENCE — 4th-order Butterworth 6–9 Hz, `sosfiltfilt`, 2.56 s windows, hop 64; mono = seg1 `t` +
100.6; orchestrator-verified from `_cache_r50/r50s1.npz`.]**

| seg1 `t` | mono | `lat` | effort | **RAW p-p** | **6–9 Hz p-p** |
|---|---|---|---|---|---|
| 27.5 | 128.1 | 0.00 | 2646 | **6502** | **190** |
| 33.3 | 133.9 | 0.00 | 942 | 3237 | 136 |
| **33.9** | **134.5** | **0.06** | **320** | 1423 | **134** |
| **34.6** | **135.2** | **0.31** | **441** | 3182 | **1179** |
| 36.5 | 137.1 | 1.00 | 998 | 5070 | **2452** |
| 46.1 | 146.7 | 1.00 | 1548 | 4204 | 910 |
| 46.7 | 147.3 | 1.00 | 2129 | 3019 | **273** |

★★ **THE HEADLINE PAIR:** `t = 33.9` (`lat` 0.06, effort 320) → **134 counts** vs `t = 34.6` (`lat`
0.31, effort 441) → **1,179 counts** — **8.8× in 0.7 s**, with **speed FALLING (1.75 → 1.60 m/s)** and
effort roughly flat, so **speed moves the WRONG way for any confound.** The death is as sharp: effort
**1,548 → 2,129** over 0.6 s collapses the band **910 → 273.**
✅ **THE 6,502-vs-591 INSTRUMENT DISCREPANCY IS SETTLED:** at mono 127.5–128.1 the car is at `lat` 0.00,
effort 2,550–2,646, and the 6–9 Hz content is **190 counts** ⇒ **6,502 is RAW BROADBAND — the operator
cranking, not the ratchet.** ★ **The ratchet proper runs seg1 `t` ≈ 34.6 → 46.1 (mono 135.2 → 146.7),
~11.5 s** ⇒ 🛑 **burst #0's ratchet onset is mono ≈ 135.2, NOT 123.69 — correct any text using the
older figure.**

#### 🛑 A CORRECTION TO THE OPERATOR'S FRAMING — the causal order, not the facts

**His hard MANUAL provocation produced NO ratchet at all** (effort 2,500–2,900; 6–9 Hz p-p only
**422–797**, prominence **1–6**). **The manoeuvres SET UP the condition** — creep, loaded wheel, LKAS
about to take over — **and the ratchet fires when LKAS ENGAGES AND HE LETS GO.** ★ **Both parts of his
account are correct; the causal order is the other way round. His report is corroborated, not
contradicted** — he named the right segments before the data did.

Also from route `50`, all [EVIDENCE]: **10 windows / 25.6 s at ≥1200 counts p-p, max 4,894**;
zero-crossing f0 **7.75 Hz**; **speed-invariant** (Theil-Sen **+0.068 [+0.005, +0.247]** Hz per m/s vs
wheel-order-1's **0.482**); present in the bar (prom **59**), angle-rate (**22**) and angle (**15**) but
**NOT in openpilot's command (1.25)** ⇒ **the loop closes inside the EPS + plant**; and
**per-engaged-window ratchet rate is identical across builds** (V70 **32.1%**, V69 **34.4%**, V62
**32.8%**) ⇒ **V70 did not add ratchet events**, consistent with the build-independence above.

⚠ **A DEFERRED LEVER THIS RE-OPENS, and it is the most under-examined result in the archive.**
**Base-assist damping is EXACTLY ZERO below ~35 km/h** (FactorC `0xD27BC` Y[0] = 0, multiplicative)
while **the ratchet lives at 4.9–8.0 km/h with Q ≈ 40.** **V47 raised FactorC and FactorE TOGETHER and
reported *"marginally quieter at 5 mph"*** — and was filed **null against the 21 Hz vibration**.
🛑 **That positive whisper has never been evaluated against the RATCHET.**
★★ **AND IT IS NOW MATERIALLY MORE COMPELLING:** *engagement-required* + *hands-off-conditional* +
*Q ≈ 40* + *base-assist damping exactly zero below ~35 km/h* fit into one picture — **at creep, the
driver's hand is the only damping in the system.** ⚠ **Still deferred**: it is a two-cal change on a
lane V47 already touched, and it deserves its own single-variable drive. **Do not stack it on V71.**

---

### 🛑 THE STATE-4 CADENCE IS REFUTED AT INSTRUCTION LEVEL (2026-08-04)

**[EVIDENCE — gp-relative *and* absolute encodings both checked.]**
**`gp-0x68ad` can NEVER be set in the field.** Both SET paths need permanently-zero flags: `gp-0x437c`
(a UDS artifact) and — **newly closed** — `gp-0x679d`, whose sole writer `FUN_000567c0` @`0x567e2` reads
`gp-0x67ba`, and **`gp-0x67ba` has exactly ONE access image-wide and ZERO writers.** `FUN_00019970`
opens with `if (gp-0x68ad != 1) return;` ⇒ **4 → 5 NEVER FIRES; state 5 is DEAD CODE on the road.**
**`gp-0x6d78` bit 15 is a ONE-WAY, OR-ONLY latch** — 15 sites, one writer (`FUN_000197b8` @`0x197ca`,
`|= 1<<n`), **no clear anywhere image-wide** ⇒ **4 → 10 is a ONE-SHOT DRIFT; 10 → 4 can never fire
afterwards.**
⇒ 🛑 **State 4 is STICKY once entered, then leaves permanently. There is NO periodic cadence** —
refuted structurally, not merely unconfirmed. With V70's bit5 at **0.0000%**, **the reachable set on a
normal drive is {4, 11}.**
⚠ **Carry the tension:** the V42 substitution is **asymmetric** (clamps increases, passes decreases) so
continuously active it should print a **rectified** waveform — **yet the ratchet measures SYMMETRIC**
(skew −0.16…+0.06, crest 2.07–2.45 vs a sine's 1.414). **Evidence against it shaping the CURRENT
ratchet.**
🛑 **[OPEN]** what sets `gp-0x6d78` bits 15/16 mid-drive — `FUN_000197b8` has **21 callers,
untraced**. That decides whether state 4 is sticky for a whole drive or only briefly.

---

### 🛑 THE AGGREGATOR IS ELIMINATED — all EIGHT zero-type range gates are VACUOUS (2026-08-04)

**[EVIDENCE — every ceiling byte-read.]** Each gate is capped by its own producer's ceiling at or
inside its gate window, **on every drive, every build**:

| lane | producer ceiling | gate window |
|---|---|---|
| boost | 512 | 2048 |
| damping | **exactly 0 at creep** (FactorC `0xD27BC` Y[0] = 0, multiplicative; ≈ 35 km/h onset); ≤ 1024 at highway | 2048 |
| friction | 511 | 1024 |
| magnitude | ±0x3000 | **== window, exactly, inclusive** |
| LKAS | ±0x2800 | **== window, exactly** |
| `gp-0x6ade` | **0 writers** | — |
| resonance | max 1024 (**164–341** at the ratchet's speeds) | 2800 |
| return-centre `gp-0x6b62` | max 5786 | 8192 |

⇒ **the aggregator stage contains NO reachable hard nonlinearity**, joining the aggregator **SUM**
(V65, 120,049 frames). **The relay / limit-cycle framing for the aggregator is REFUTED — do not
re-propose it.**
★ Also [EVIDENCE]: `FUN_00036388`'s own counters give **~20–40 ms or ~1 s** periods — nowhere near
7.8 Hz ⇒ **it INHERITS the ratchet, it does not GENERATE it.**

---

### ★★★★ `gp-0x67fa` STATE-GATES THE WHOLE ASSIST CHAIN, AND STATE 10 SPLITS IT IN HALF — 2026-08-04

✅✅ **SETTLED ON-CAR 2026-08-04 — V70's bit5 (`gp-0x67fa == 10`) read 0.0000% of 18,010 frames**,
encoding independently verified. ⇒ **the aggregator ran** ⇒ **state ∈ {4, 5, 11}** ⇒ **`FUN_00036388`
and `FUN_000428d4` WERE INVOKED** ⇒ 🛑 **the `gp-0x67df` detector nulls on V64/V67/V68 are GENUINE,
and the state-gate explanation for them is REFUTED. Five builds vindicated**, on a **pre-registered**
prediction. ⚠ **It licenses *"the call was made"*, NOT *"the body ran"*:** `FUN_00046ea6(5)` on
`gp-0x18d0` bit 5 — the detector's second, independent entry gate — **remains OPEN.**
⊕ Combined with the state-machine refutation above, **the reachable set on a normal drive is {4, 11}.**
**The structural mapping below stands as written.**

**[EVIDENCE — instruction level, `FUN_0002214a` `0x2214a`–`0x22a84`.]** 🛑 **The guard wraps the `jarl`
IN THE COMMON CALLER, not inside the four functions.** Each has exactly one call site, all in
`FUN_0002214a` (RTOS **task 1**, 1 kHz) ⇒ **in a masked-out state the callee is NEVER INVOKED — no stack
frame, 0% of body.** Index is a plain `1 << (gp-0x67fa & 0xf)`, **no off-by-one** (`0x2214e` `ld.bu` /
`0x22172` `andi 0xf` / `0x2217c` `shl`, recomputed identically @`0x221bc`–`0x221c6`). **THREE masks:**

| site | mask | states | what it gates |
|---|---|---|---|
| `0x221d6` | **`0x830`** | **{4, 5, 11}** | `FUN_00036388` @`0x22882` (return-to-centre) · `FUN_000428d4` @`0x22926` (**the OSCILLATION DETECTOR**) |
| `0x22518` | **`0x930`** | **{4, 5, 8, 11}** | `FUN_00028ea6` / `FUN_0002b422` / `FUN_0002b57a` (**ARBITRATION = `gp-0x6806`'s PRODUCER**) |
| `0x2269a` | **`0xc30`** | **{4, 5, 10, 11}** | `FUN_0003a382` @`0x226a0` (residual lane) · `FUN_0003aa2c` @`0x2291e` (**THE AGGREGATOR**) |

⇒ **IN STATE 10 THE AGGREGATOR AND THE RESIDUAL LANE RUN, WHILE THE DETECTOR, THE RETURN-TO-CENTRE LANE
AND ARBITRATION DO NOT. Assist is delivered from a stale `gp-0x6806`.**

★ **State 10 is REACHABLE IN NORMAL OPERATION** — written twice in `FUN_00019970` (the state-4 handler):
`0x199CC` (diagnostic, `tp+0x74d0 == 0xa`) and **`0x19A72` (the NORMAL path)**, the latter gated on
**bit 15 of `gp-0x6d78`** with bit 16 (→ state 11) taking priority. Writer set over **33 `st.b` sites**
(Ghidra and a raw LE byte scan agree exactly, no undercount): {1,3,4,5,6,7,8,9,10,11}, max 11.
⚠ **[OPEN] what bit 15 of `gp-0x6d78` means** — that decides how *often* state 10 is visited, not
whether it can be.

🛑 **THIS IS A LIVE ALTERNATIVE EXPLANATION FOR THE FIVE-BUILD DETECTOR NULL** (`gp-0x67df` 0/14,980
V64, 0/186,321 V67, 0/53,991 V68): *"`FUN_000428d4` was never CALLED"* has **never been on the table**
and has the **identical signature** to *"it ran and found nothing."* Every *"the detector is exhausted /
the oscillation-gated approach is closed"* verdict in this file inherits the caveat.

⚠ **BUT V67's OWN PROBE ARGUES AGAINST IT, AND THIS MUST BE QUOTED ALONGSIDE — NEVER WRITE THE CLAIM
WITHOUT IT.** State 10 is absent from `0x930` too, so arbitration — `gp-0x6806`'s producer — is **also**
skipped there and the flag would go **STALE**. V67 measured **`gp-0x6806` == `latActive` in
150,302/150,327 = 99.983%** of frames, all **25** disagreements single-frame transition edges. **A stale
flag cannot track transitions that closely** ⇒ **the ECU is predominantly NOT in state 10 while engaged,
and the detector nulls are probably GENUINE.** [BELIEF — indirect.]

✅ **V70's bit5 rung (`gp-0x67fa == 10`) settles it directly, and is NON-VACUOUS IN BOTH DIRECTIONS:**
**bit5 ≈ 0** ⇒ state ∈ {4,5,11} ⇒ **the nulls are genuine and five builds are vindicated**;
**bit5 materially non-zero** ⇒ **the nulls were on the gate** and the detector programme needs
replanning.

⚠ **THE DETECTOR HAS A SECOND, INDEPENDENT ENTRY GATE, AND IT IS STILL OPEN.** `FUN_000428d4` is also
gated on **`FUN_00046ea6(5)`** — bit 5 of `gp-0x18d0`/`gp-0x18d4`, a fault/DTC-style bitmask, falling to
a fixed `0x8000` sentinel if set. 🛑 **This file's earlier closure of that question established only
that the FUNCTION has one caller image-wide — NOT that the BIT is clear in operation. Those are
different claims**, and only the first was ever checked. The other three gated functions have no such
secondary gate.

🛑 **AND bus `STEER_STATUS` IS NOT `gp-0x67fa`.** Route `4f` reads `ST = 0` on 47,990/47,990 frames
*while the car steered*, and **state 0 is in no mask**. **Any reasoning that equated them** — e.g.
*"ST==4 fires 0/37,922"* as evidence about `gp-0x67fa == 4` — **is invalid.** [VERIFIED] **State 4 sits
inside all three masks** and is where the V42 governor ratchet substitution used to fire.

⚠ **PROVENANCE, carry it:** decompiled against **stock `code.bin`**, with the 33 writer sites
cross-checked **byte-identical in `_v68_plain_image.bin`**. The **dispatcher itself was NOT decompiled
from a V68/V69 image** — high confidence it is unchanged (far outside any cave region), but that is
**BELIEF by adjacency, not EVIDENCE.**
⚠ **`mcp__ghidra__get_xrefs_to` returned "No references found" for this RTOS task entry** — a null from
that tool is never load-bearing. A `jarl` Format-V scanner written to cross-check it returned **zero
hits for functions Ghidra had just given callers for**, from a mask bug: bits 15:11 are **reg2, not
opcode**, and `disp = ((hw1 & 0x3F) << 16) | hw2` sign-extended from **22 bits**. **Anchor any such
scanner on a known site and assert it.**

---

## Part 3 — Machine-generated per-build delta (vs stock `code.bin`, app region only)

Regenerate with a byte diff restricted to `[0x13000, 0x100000)`.
⚠ **A whole-file diff is meaningless** — `build_*.full_image()` writes `0xFF` filler below `0x13000` and a
naive diff reports 51,137 bogus bytes.

`0x13109` and `0x14120` appear in every build: they are the version-string bytes (`-`→`,`, giving
`39990-TVA,A160`). **Every modified build shares that string, so an rlog cannot identify which build is
flashed.**

| build | bytes | code edits (beyond version string) |
|---|---|---|
| v29–v33, v36, v37 | 27–42 | none — cal-only |
| v38 | 126 | none — cal-only (first to touch `0xE4000`/`0xE5000` bootloader blocks) |
| v39 | 174 | `0x3AC78` + cave `0xC4B34-C4B5F` |
| v40 / v41 | 162 | none — cal-only (`0xC5030`, `0xC521A`, `0xC5232`, `0xC6206/08`) |
| v42 | 153 | **`0x454FE`** (the ratchet fix) |
| v43–v48a | 129–145 | `0x454FE` only |
| v48b | 282 | `0x2C482`, `0x354D4`, `0x35AA6`, `0x3A6CC`, … + cave — ☠ **BRICKED** |
| v49 | 130 | `0x3A836`, `0x454FE` |
| v50 / v52 / v52c | 226–254 | multi-site repoints + cave `0xC4B34` |
| v49p / v50probe / v51probe | 183–216 | `0x55C0E` hook + cave (read-only probes) |
| vcantxtest | 340 | `0x55C0E` hook + cave — ⚠ carries the **STRB=0x80 defect** |
| vfourframe | 853 | `0x55C0E` hook + cave — ⚠ **STRB=0x80 defect, never transmitted** |
| **vfourframe2** | 853 | same, **STRB fixed to 0x01**, authority + reference-model signals |
| **v53** | 855 | FOURFRAME2 byte-for-byte **+ `0xC62EA` 320→0** (+ CAL CRC). Exactly 6 bytes off FOURFRAME2 |
| **v54** | 58 | `0x55C0E` hook + **44-byte** cave `0xC4B34` (5-bit `gp-0x6966` authority probe → `0x14A` byte4 bits 7:3) + `0xC62EA` 320→0. **No mailbox cave** |
| **v55** | 82 | `0x55C0E` hook + **68-byte** cave `0xC4B34` (dual probe: damper variant bit + 4-bit `gp-0x6b98`) + `0xC62EA` 320→0 |
| **v56** | 84 | V55 byte-for-byte **+ `0xC6AFC`/`0xC6AFE` 32768→0** (+ CAL CRC). Exactly **6 bytes** off V55 — and only **2** are cal, because `32768` = `00 80` LE so just the high byte of each halfword moves |

---

## Part 4 — Flash status at a glance

🛑🛑 **CURRENT, 2026-08-07 (night) — THIS LINE IS THE ONE TO READ; EVERYTHING BELOW IT IS HISTORY.**
Flash order since V70: **V71C → V72 → V73 → V74 → V75 (☠ hard fault, route `5e`) → V74 reflashed (☠ hard
fault, manual, over a bump) → V76 (route `65`, clean) → V80 (route `66`, NO fault — and the worst grinding
this car has ever produced).** **V78 and V79 were built and never flown**; V79 is renamed `SUPERSEDED-…`.
⏳ **V81 IS BUILT, VERIFIED AND UNFLASHED** — image `4ddbd0e2…d65b`, rwd `fc4d4f74…a109`; a **126-byte
cal-only revert from the flown V75** with `0xC407E` back to 511 and the friction table back to Honda's,
`k` = 1.5798 unchanged. **The flash decision is the operator's.**
✅ **V76, V78, V79, V80 and V81 all now have rows in Part 1** (backfilled 2026-08-07 from the build
scripts, the plain images on disk and the 08-06/08-07 handoffs — this file had been five builds behind,
which is precisely the gap it exists to prevent).
🛑 **The `k` ladder, for anyone reaching for a damper dose:** V74 **0.5799** (flown) · V76 **1.3866**
(flown clean) · V75 **1.5798** (flown, fixed the grind, hard-faulted on `0xC407E`) · V78 **2.0840**
(built, never flown) · V79/V80 **4.1597** (V79 never flown; V80 flown — worst grinding ever).
🛑 **`docs/STATE.md` remains the authority for what is on the car.**

🛑🛑 **STALE BELOW THIS LINE — 2026-08-06.** The "CURRENT" line that follows was written at V70 and has
not tracked V71→V76. **`docs/STATE.md` is the authority for what is on the car.** Two things this
section must not be read as saying: **V74 and V75 have BOTH been flashed and BOTH hard-faulted**
(see their row in Part 1 and RULE 8b), and **`k* ∈ (0.580, 1.580]` is VOID** — no build in the current
lineage has demonstrated safety. ⏳ **V77 and V77B are BUILT and UNFLASHED** (`0xC63A0` 2048→1024 on the
V74 and V75 bases respectively); **neither is clearance to fly** — Part 1 carries their SHAs.

🛑 **CURRENT, 2026-08-04: the image on the car is V70** (flashed, driven route `50--50f2e00e8f`;
image `3760d9c0…`, RWD `0bdfb0da…`). Flash order since V55: **V56 → V57 → V58 → V59 → V60 → V61 →
V62 → V64 → V65 → V67 → V68 → V69 → V70.**
⏳ **V71 IS BUILT AND UNFLASHED** — V70 carrier + **`0x454FE` `ba`→`b5`** (restore V42's ratchet fix) +
**`0x3AB76`/`0x3AC20` `aa`→`a9`** (restore V62's ×2 on BOTH lanes) + the mode-10 surface
(`0xD2A7E`/`0xD2A80`/`0xD2ABA`/`0xD2ABC`) reverted to stock + a probe that reads **the gain in force**
(bit6 `gp-0x671d != 0`) rather than a lane output. Its rate lane is **byte-identical to V62/V65**, which
flew twice, both flight-clean. CRC blocks `0xC4FFC` + `0xD2FFC`.

★★ **THREE V71 SIBLINGS WERE BUILT, ALL UNFLASHED, ALL RESTORING `0x454FE`. Orchestrator-verified from
the image bytes.** 🛑 **They are NOT separable on the wire — the filename is the only pre-drive
discriminator** (A and C share a byte-identical cave; B differs by one cave byte that never reaches the
payload).

| | image SHA256 | rate-lane levers | probe |
|---|---|---|---|
| **V71A** | `acc62e0930c9fa8f5176e22d1751f3f9544b1228c90d0b1e09188c67448c78e5` | both `sar` → `0x9`; flat 2.000× at every speed | `gp-0x6ada` (r24) |
| **V71B** ← recommended | `d4543d02b2fa113df7ab394ba0131859e3193a8c75604ddf3165768b6e5dd3f4` | `gain_A` rec0/rec1 Y[0..3] ×2 ⇒ 2.000× ≤10 km/h → **EXACTLY 1.000× ≥50**; r24 stock | `gp-0x6adc` (r26) |
| **V71C** | `30b63fdd59bdf9221fec0942d9ccdbc6f0582d2e8c3acbc4d30b0acd89ff1607` | gate `fb` + `0xC6446`=5244 + **`0xC6444` 512→3072 (r26 CUT REMOVED)**; `sar` stock | `gp-0x6ada` (r24) |

rwd SHAs: A `5c5138d960192d7d0a4e37301a0c82ad29e02ccff0cc116b62d6ac1cb0337e9e` · B
`3bc9347aa54449b2ccfe7896b076f57bf0b932ed1de3d41ae45be838ceaa8157` · C
`4ce568b6fd85ad0ad2a5a6159ede09276f705a1e00d66ac129b8f60679c4e609`.
**V71C is 71 bytes off V67** = **61 differing cave bytes** + `0x454FE` + `0xC6445` + 8 CRC (61+1+1+8 = 71),
in **9 strictly contiguous runs**. ⚠ **The cave is 68 bytes but only 61 of them DIFFER** — V67's cave and
V71C's coincide at 7 positions, so the cave region is **not** one contiguous run. *(Corrected: an earlier
figure of "5 runs / 66-byte cave" came from a diff script using a +3 merge tolerance, and summed to 76.
Re-derive run decompositions with STRICT contiguity.)*

🛑🛑 **A SCALAR GATED ARM CAN NEVER BE HIGHWAY-CLEAN WHILE DOSING AT CREEP** — the arm **replaces** a
LERP that rolls off with speed, so `arm/LERP` **rises** toward highway (V67/V68 and V71C both deliver
**r24 2.438× at 100 km/h** vs V69/V70's 1.000×). No `0xC6446` value fixes it: lowering it enough for
highway puts creep **below** stock. ⇒ **only the ungated speed-shaped surface can be structurally stock
at highway.** ⚠ Consequently **V67/V68 differs from the highway-clean builds in BOTH lanes** (r26 cut
~5× **and** r24 raised 2.438×), so **V71C removes only one of two candidate causes**; if the highway
symptom is r24's, V71C will not fix it. Named follow-up: `0xC6446` 5244 → ~2151–2400.

⚠ **INT32 headroom at `mul r8,r6` @`0x3AB72`:** stock / V71A / V71C = **46.87%**; **V71B = 93.75%** —
the band V62's own build note rejected. **No overflow is reachable** (`ld.hu` bounds `avg` at 65535),
but V71B carries half the margin. `0xC6444` ceiling **6553** = `2³¹ / ((5120 × 65535) >> 10)`.
🛑 **A first V70** (`…LKASGATED-V68CONTROLPATH…`) restored V67/V68's scalar arm and **the operator
overrode it** — it re-introduces the high-speed grind. ✅ **It is renamed
`SUPERSEDED-DO-NOT-FLASH-…`** (`accord-firmwares` `9d44efc`), filesystem-verified: **exactly ONE
flashable `V70` file remains.** ⚠ The rename was load-bearing — its cave is **byte-identical** to the
current one, so the probe could not have told them apart on-car and the filename was the only
discriminator. ⚠ Current SHAs and control path live in `docs/STATE.md` (they change on every re-cut);
V70's probe design is its own row in Part 1. ⚠ **The narrative below was written incrementally and its
"on the car now" sentences are stale as of the build they were written for — this line is the
authority.** V69's and V70's on-car results are in their Part 1 rows.

**Flashed and currently the on-car baseline lineage:** V38 (fault-free) → V42 (ratchet fixed) → V43, V44,
V45, V46, V47, V48A (all null) → V48B (☠ bricked, recovered by reflash) → V52C (null for vibration,
changed manual feel) → FOURFRAME (telemetry, silent — STRB defect) → V53 (2026-07-27: steer-to-zero
✅ CONFIRMED; four-frame telemetry absent and the null uninterpretable — see the box in Part 1) →
**V54** (2026-07-27: ★ **the probe FIRED** — first working firmware telemetry channel in this kit;
`0xC6AF0` direction measured and the block lifted; fault-free).

→ **V55** (2026-07-28: the dual probe FIRED and partitioned the hypothesis space — ★★ **the ~21 Hz IS in
`gp-0x6b98` and the loop is INTERNAL to the EPS**; openpilot is 8.7× too small even with the LKAS
low-pass deleted, and while RAILED its 21 Hz is exactly 0 yet the command still carries 105.8 counts;
sensor→command transfer is **flat 0.19→0.22 from 1 Hz to 21 Hz**; damper bit7 = 1 ⇒ V44/V47 hit the LIVE
tables). Fault-free.

**⚠ V55 is the image on the car now.** It does **not** carry the V42 ratchet fix (`0x454FE` is stock
`0x65BA`), same as V38/V53/V54/FOURFRAME.

★ **V54's telemetry result — the `0x14A` byte4 bits 7:3 piggyback is PROVEN end to end.** A/B against the
V53 drive is a single bit and it is exactly ours: byte4 = `0x07` ×5,994 (100%) on V53 → `0x0F` ×5,989
(100%) on V54, stock `STEER_SENSOR_STATUS` bits 2:0 preserved, `canValid` true in 5,711/5,713. **Use this
channel for all future firmware telemetry.**

→ **V56** (falsified, reverted) → **V57** (decouple + deadband probe, fault-free) → **V58** (angle-rate/
boost-lane probe, fault-free, 14 segments) → **V59** (2026-07-30, route `2c`: ★★ **the boost-index DEPTH
probe FIRED and answered** — 50,963 frames, 100% live, 100% thermometer-monotonic, fault sentinel 0.000%,
`ST==4` 0/50,963, FLIGHT-CLEAN. The 42.19 Hz pump = **2× the 21.09 Hz mode**, engagement-gated, **absent
disengaged** (bit5 never toggles in 61.2 s) — but **MARGINAL**: eps 0.013–0.169 across every combination
of task rate × series question, against a threshold that cannot be pinned because the passive Q is not
measurable (no ring-down exists: 66 candidates, longest **0.63 cycles**)).

★★ **The turn this drive produced — the OPERATOR's hypothesis, now the leading explanation.** The torque
sensor sits between wheel and road, so LKAS motor torque twists the column and is **read back as driver
input**, then boosted. A positive feedback loop, and **traced: there is NO motor-command feedforward
compensation anywhere in the chain** (`gp-0x6b98` appears only as a sign input to the `gp-0x6ac2`
ceiling detector, and in `FUN_00043e44` whose output has **zero readers**). Measured: the
**command→torsion-bar transfer function peaks at 21.09 Hz — the GLOBAL max over 3–46 Hz** — 15.6×
baseline hands-off (K=5, coh 0.654 vs null 0.527), 25.7× any-hands (K=53). ⇒ **the pump is probably a
passenger; the loop is the driver.**
🛑🛑 **CORRECTION OF RECORD, 2026-07-31 — V52C DID NOT "HALVE THE MODE". THERE WAS NEVER A NUMBER.**
This paragraph used to cite V52C as the loop hypothesis's best supporting evidence. **Struck.**
`−6.1 dB at 21 Hz` and `halved the mode` are **the same statement**: V52C's EMA (α = 74/1024, 1 kHz)
has `|H(20.9 Hz)| = 0.4963`. It is **the filter's designed attenuation, not a measurement.** The phrase
was authored in `HANDOFF-2026-07-28-v55-...md:205` as a **caveat on why V52C's NULL was weak evidence**
and mutated into a positive result two handoffs later. Every contemporaneous record — including the
operator's own words in `HANDOFF-2026-07-26-route13-...md:8` (*"V52C did not fix the vibration; it
clearly changed manual feel"*) — says **NULL**. **No V52C rlog exists** (routes on disk are
`13,1a,1b,1c,24,28,29,2b,2c`; the V52C window `08`–`12` is absent machine-wide and was never in git),
so the "re-derive it first" instruction was unexecutable. ⇒ The loop hypothesis rests **only** on the
21.09 Hz transfer peak and the traced absence of feedforward. ⚠ Not a falsification of the loop — a
2× gain cut carrying +57–61° of lag is a poor stabiliser — but it **is** weak-to-moderate evidence
against the `gp-0x4f60` **VALUE** path specifically.

### 2026-07-31 — V60 FLASHED → NULL, and V61 built

🛑 **V60 (`0xD2006` 102→43) FLASHED and driven 2026-07-31 → NULL on the vibration.** Operator: *"It did
not fix the vibration issue."* No rlogs (V60 carries V59's probe unchanged, so there was no new
telemetry). **This is a result, not a wasted drive** — V60 was built as a **discriminator** and the
record predicted the null in advance. Pump causality was not settleable observationally (the index is
`|x|` of a bar-derived signal, so 2f coupling is arithmetically forced) and `eps_crit = 2/Q` needed a
passive Q that V59 could not measure. ⇒ **the V58/V59/V60 parametric-pump arc is CLOSED.**
★ **It also closes `0xC63BA`** — byte-scanned, the readers of `gp-0x6b9a`/`gp-0x6ba6` are confined to
`FUN_00034350` (damping), `FUN_00034a72` (boost), their producer and V59's probe, so that cal's only
effect is on the same amplitude LERPs V60 just falsified. **Do not propose it as a grinding fix.**
⚠ Two more lanes eliminated, byte-verified: `FUN_00036c12` (`gp-0x6b26`) and `FUN_00036388`
(`gp-0x6b62`, the return-centre lane) read **no torque signal at all** — speed/motor-rate keyed only.

★★ **A structural finding that reframes every damper null: RTOS task 5 runs at 100 Hz.** The rate
divider `FUN_00014be4` is mod-100 on the base tick; boost `FUN_00034a72` and damping `FUN_00034350`
fire once per 10 task-1 invocations (integer arithmetic — clock-independent). ⇒ a ZOH costs
**37.6° average / 75.2° worst-case** transport lag at 20.9 Hz before any plant phase, so the
velocity-proportional damper **structurally cannot damp this mode** and may be anti-damping there.
**That is a second, independent reason V44/V47 were null**, alongside the FactorC speed-axis argument.
⚠ A datasheet audit then refuted the kit's clock chain — **PCLK is 40 MHz, not 80, and OSTM0 is NOT the
RTOS tick** (no arm in the EI trampoline `FUN_0001492a`; the divider's trigger `gp-0x42fc` is written
only by `EIIC 0x340` = TAUJ1I2). The 1 kHz/100 Hz figures **survive on ON-CAR measurement**, which never
used that chain. But **the FOC/TSG20 "~8 kHz" carrier likely halves to ~4 kHz** — treat as OPEN.

| lever | what | build | flashed | result |
|---|---|---|---|---|
| `0x3AB6C` `mul r1,r6,r0`→`mul r0,r6,r0` + `0x3AC16` `mov r1,r8`→`mov r0,r8` | ★★ **kill the torsion-bar RATE lane at BOTH taps of its shared value** `r1 = clamp(gp-0x4f62, ±5120)` | **V61** | ✅ **BUILT, UNFLASHED** | **The one decisive subtractive test never performed.** r24 and r26 are **not independent** — both are gain-scalings of ONE value, same sign, shared polarity load @`0x3AB78`. **V39 killed only r24 and only *conditionally*** (cave @`0x3AC78`, bypasses unless driver max torque < 320 AND \|LKAS\| ≥ 417); **V42 killed only r26** and says so outright. **Byte-checked every flashed image: NO build ever had both dead** ⇒ each recorded null was uninformative about the lane. Two single-**BIT** `reg1` r1→r0 changes, opcode/reg2 byte-identical, **no cave** ⇒ GATE 1 vacuous. 5 bytes off V59; CAL CRC and `0xD2000`-block CRC both unchanged. ⚠ Expect a manual-feel change (phase-lead term in **base** assist, no LKAS-only decoupling point); reversible via V59 |

🛑 **A CORRECTION THAT MATTERS FOR THE FACTOR-C/E RECORD.** V44 raised FactorC alone → null. **V47
raised FactorC AND FactorE together** — byte-verified 2026-07-31 across the images (`v47` has FactorC
`Y[0]` = 235 *and* FactorE = (700,750,800), vs stock 0 and (0,140,539)). **So the multiplicative-chain
concern WAS handled: the simultaneous test exists, was flashed, and gave "marginally quieter at 5 mph,
no effect in motion."** V61 is the *additive dual* of that same trap, and unlike C/E its simultaneous
test has genuinely never been run.

**Built and UNFLASHED:** ★★ **V61** (above), plus ~~V60~~ (now flashed, null — do not re-flash;
null), plus **V55** (dual probe: damper variant bit + 4-bit `gp-0x6b98`
motor command, 82 bytes off V38), plus V49, V50, V51P, V52, VCANTX-TEST, FOURFRAME2. V53 and V54 are both
now flashed and no longer candidates.

★ **V55 is a PARTITION, not a lever.** Every falsified vibration lever in Part 1 — V39, V41, V42 ch.2,
V43, V45, V46, V48A, V52C — sits on the **command path** and assumes the ~20 Hz is *commanded*. V55
samples `gp-0x6b98`, the final merged command and the only path to FOC, to test that assumption directly:
if the mode is absent there, all eight were doomed by construction and the search moves to the plant.
A null BOUNDS the command's 20 Hz content to ~<512 counts (one level) against the sensor's ~550 rms; it
does not prove zero, and a 100 Hz probe still cannot separate 20 Hz from 80 Hz.

🛑 **Flash only on explicit operator instruction naming the file and the bus.**
