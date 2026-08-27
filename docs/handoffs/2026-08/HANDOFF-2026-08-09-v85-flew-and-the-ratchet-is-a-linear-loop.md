# HANDOFF 2026-08-09 (late) — V85 flew route `6e`, the lever delivered and the bands are a null, and the ~7.79 Hz ratcheting is a LINEAR LOOP OSCILLATION

**Predecessor:** `handoffs/2026-08/HANDOFF-2026-08-09-v84-flew-and-the-command-scaled-relay.md`.
**Current state:** `docs/STATE.md` (rewritten in place this session). **Lever ledger:** `docs/BUILD-LINEAGE.md`.
**Arc map for this session:** `docs/archive/arc-maps/_session_v86_arc_map.md`. **Cumulative non-stock delta:**
`docs/archive/arc-maps/_session_v86_nonstock_delta.md`.

---

## 0. 🛑 THE OPERATOR'S VERDICT COMES FIRST

His words on V85, verbatim:

| symptom, HIS word | V85 |
|---|---|
| **grinding** | *"grind #1 is still barely perceptible"*, *"got a little bit better"* — **still present** |
| **micro-ratcheting** | *"seems like it got barely, perceptibly better (somewhat unsure)"* — **still present** |
| **ratcheting** | 🛑 **"was still unfixed"** |
| grind #2 | *"I did not experience any grind #2 from my hard turning or on the highway"* — 🛑 **an absence of complaint is NOT a cure** |

🛑 **RATCHETING IS UNFIXED, AND THAT IS THE HEADLINE.** Everything measured below is instrument, not
symptom. **"Grind #1/#2", "the ring" and "S1…S4" are KIT JARGON for frequency bands** — they are not
symptoms the operator named. A band moving is not a symptom being fixed, and nothing here may be called
fixed that he has not called fixed.

---

## 1. V85 FLEW AS ROUTE `6e`, FAULT-FREE — the cleanest flight in the modern lineage

`75604b0a432fdc89_0000006e--649c462a6e`, cache `_scratch/cache/r6e/`.
**43,641 frames · 438.2 s · 82.02% engaged.**
**`STEER_STATUS` = {0: 43,641} — not one non-zero frame**, 0 DTC-active frames, 0 sentinels. [EVIDENCE]

**Identity, with no free parameter** [EVIDENCE]: `b3` fingerprint **1.00000**; `b7` duty **0.39481**
where V84 read **0 / 68,236**; nesting `b6⇒b7` and `b5⇒b4` both **0 violations**.

### 🛑 The exposure limit, stated before any result
| | V85 (route `6e`) | V84 (route `6d`) |
|---|---|---|
| engaged ≥50 km/h | **35.6 s** | 370.8 s |
| engaged ≥80 km/h | **22.4 s** | 158.1 s |
| creep windows / blocks | **68 / 15 — best in the ladder** | — |

⇒ This is **V83a-class exposure at speed**. 🛑 **No highway verdict and no 26–31 Hz verdict may be
scored on route `6e`.** Creep is the regime this route can carry, and it carries it well.

### Three traps recorded from the extraction work
1. 🛑 **`_scratch/cache/r6e/r6e.npz` carries `probe_build = ['V80']`.** That field is a **stale extractor
   heuristic and is WRONG.** **Never quote it.** Found independently by two agents.
2. ⊕ **"CAN 330 / 399 / 427" are DECIMAL** in this kit = hex **`0x14A` / `0x18F` / `0x1AB`**.
3. ⊕ **Route `6e` segment `--7--` is truncated mid-capnp-message.** Stock `read_messages` raises and
   loses the **whole route**. A wrapper recovered **32,695** complete messages.

---

## 2. THE `0xC40BC` LEVER DELIVERED — AND IS NOW SPENT. FREEZE AT 6000.

**Delivered [EVIDENCE]:** relay saturation **39.5% → 11.1% overall, 33.3% → 4.6% engaged (7.21×)**.
**Both pre-registered duty predictions hit.**

### 🛑 Why FREEZE — and why the pre-registration's own reason was the wrong route to it
The pre-registration read *"if S2 does not improve, revert `0xC40BC` — `N` is already flat at 6000, there
is no larger dose."* That reached the right disposition by the wrong argument, and the correction matters
because the wrong argument would generalise badly.

**The single-input describing function cannot settle this at all**, because **the ring rides on a bias
5–10× its own amplitude**:

| quantity | p50 | p90 |
|---|---|---|
| bias `\|B\|` | **35 counts** | **228 counts** |
| ring amplitude `A` | **4–7 counts** | — |

The correct instrument is the **BIASED** describing function. It reads **top-decile pinning at cal 6000
of 0.0000 for 18–22 Hz and 0.043 for 6–9 Hz**, after an already-delivered **20.3×** reduction.
⇒ **There is nothing left to buy. Do not raise it further, and do not revert it — the lever is spent,
not wrong.**

### 🛑 The golden-model reframe
**This lane's pathology was NOT "harmonic injection". It was PARAMETRICALLY SWITCHED DAMPING.**
At cal 600 the damping switched **fully off** on **87% (6–9 Hz)** and **96% (18–22 Hz)** of symptom
frames. That is a different mechanism with different implications: a switched damper does not need a
harmonic comb to destabilise a loop, which is consistent with §4's no-comb result.

⊕ **Scale confirmed independently, two ways:** **4.923** and **4.697** ct/(°/s) bracket the inherited
**4.7121**. Reachable envelope **±1,930 counts**.

---

## 3. 🛑 V85 vs V84 IS A CLEAN NULL IN EVERY BAND

| band | V85 / V84 | verdict |
|---|---|---|
| 6–9 Hz | **1.088 [0.746, 1.451]** | null |
| 18–22 Hz | **1.347 [0.947, 1.758]** | null |
| 40–49 Hz | 1.002 | null |
| **32–38 Hz — negative control** | **1.007** | control holds |
| 1–4 Hz — validity | 1.005 | holds |
| IMU roughness | **0.958** | V85's road was *smoother*, i.e. moving **for** V85 |

**Split-half nulls are [0.63, 1.50] wide — a ratio must clear ~1.5 to mean anything.**

🛑 **The instrument does NOT corroborate the operator's two "a little better" reports, and does NOT
refute them either.** Both statements are true simultaneously; neither overrides the other. **Score
bands; let the operator score symptoms.**

⚠ **Self-correction of record.** The 6–9 Hz figure *"V85 worse than V81"* = **1.625 was a WHEEL-ORDER
ARTEFACT**. Order-cleaned it falls to **1.273 [0.853, 2.507]**, inside the null. The 18–22 Hz result
**survives** order-cleaning (1.957 → **1.928**).

---

## 4. ★★★ THE ~7.79 Hz RATCHETING IS A LINEAR LOOP OSCILLATION

**This is the session's real finding, and it changes what CLASS of lever can touch the one symptom the
operator says is unfixed.**

### It is NOT a relay [EVIDENCE]
| test | result | control |
|---|---|---|
| odd/even harmonic comb | **0.858 [0.739, 1.000]** | positive control **1.204 [1.147, 1.566]** at just **15%** injection |
| 3:1 phase-locking PLV | **z ≤ 1.05** | — |
| switching-surface time-locking | **−0.0375** | — |
| third harmonic, second method | **absent** | — |

⇒ **<15% of the ~8 Hz bar content can be relay-generated.** This refutes the friction-compensator relay
`FUN_00038148`/`gp-0x6b70` as the generator, which is where the session had been aiming.

### It is NOT a plant resonance [EVIDENCE]
The wheel-on-torsion-bar mode is **12.8 Hz [12.1, 13.6]** — **above** the ratchet — and **7.79 Hz is
unreachable through the plant alone** (12.65 Hz floor).

### ⇒ A LINEAR loop oscillation whose frequency is set by accumulated estimator lag `[BELIEF]`
It is the only surviving hypothesis, and it fits **every** recorded property:

| recorded property | consistent with a linear loop mode? |
|---|---|
| sinusoidal, no comb | ✅ |
| **speed-invariant** (+0.074 / +0.049 / −0.004 Hz per m/s) | ✅ — wheel order 2 predicts **+0.961** |
| engaged-only | ✅ (the loop only closes engaged) |
| in the bar and in angle rate, **not** in openpilot's command | ✅ (the loop closes inside the EPS + plant) |

🛑 **The lever CLASS this implies — PHASE / LAG — is new since V38.** The whole arc has moved
magnitudes: authority, gains, clamps, filter poles as attenuators, damper surfaces, nonlinearity shape.
**Nothing has ever been aimed at *when* rather than *how much*.**

### Two supporting observations, both bounded
- ⊕ **The line grew ~3× at V84 and V85 kept it** — speed-matched V85/V81 = **2.742**, V85/V84 = **0.850**.
  ⚠ The reading *"V85's line is 3.2× more prominent"* is a **FLOOR EFFECT**, not an amplitude increase.
- ⊕ **NEW: a discrete engaged-only ~20.90 Hz line at creep on V85 and V84, absent on V81** (prominence
  **8.08×**), within noise of the recorded **21.09 Hz** engaged-only closed-loop mode. **The 18–22 Hz
  V85-vs-V81 elevation is THAT LINE, not a floor shift.** ⚠ V84's arm is **n = 6 windows** —
  suggestive, **not measured**.
- ⊕ **Micro- vs macro-ratcheting could NOT be separated.** The split is dominated by speed, and kurtosis
  is consistent with **one population**. Do not treat them as two objects on this evidence.

---

## 5. A PREVIOUSLY UNDOCUMENTED CHAIN, TRACED END TO END

Now folded into `analysis-2020accord/model/eps_lkas_chain_model.py`.

```
FUN_0003b8f6 @0x3b8f6   (1 kHz plant-model estimator; sole caller FUN_0002214a, guard andi 0x830 => states {4,5,11})
  model  = EMA2(gp-0x6b98 x polarity/1024, a=0xC40D4=573/4096)
         + clamp(FIR(EMA2(gp-0x4f60/1024, a=0xC40D8=3686/4096)) x 0xC613A/32768, +-15)
           x LERP13(gp-0x6a10, X@0xC6B66, Y@0xC6B80)/1024
  FRICTION = clamp(EMA(|model| x 102/1024 + 0/1024, a=0xC40D0=408/4096) x ratio, +-10)   -> gp-0x6ae2
      ratio = clamp(polarity(gp-0x6752) x gp-0x6abc x 12 / cal(0xC40BC), +-1)   [saturates at cal/12]
  INERTIA  = EMA^2[d/dt(polarity x gp-0x6abc x 12) x 17.453293] x 0xC646E        -> gp-0x6ae0
  gp-0x6bfc = clamp(0xC6468(=2639) x (model - FRICTION - INERTIA), +-20000)      @st 0x3BC1A

FUN_0003bc20 @0x3bc20 : plausibility |x| < 20000 -> gp-0x6bfe, status gp-0x695c (0x400 ok / 0xFFFF bad)

FUN_00038148 @0x38148 : resid = gp-0x6bfe
                              - (EMA(SUM six channels x weights 0xC63A0..0xC63AA, coeff 0xC63AC=102) >> 4)
                              + gp-0x6bfa
                        gp-0x6b70 = clamp(SIGN(resid) x LERP_RAM(|resid| x 0xC63AE >> 10),
                                          +-0xC6200=8192)                        @st 0x382D2

FUN_00037fe6 @0x37fe6 : ASSIST AGGREGATOR
                        sum = -gp-0x6b4a + SUM(term x BYTE enable 0xC64AD..0xC64B3, all 0x01)
                        gate: the six optional terms are summed whenever gp-0x67ab != 1
                        gp-0x6ad6 = clamp(sum x speedLERP(gp-0x69aa)/1024, +-25600)   @st 0x38142

-> FUN_0003a382 (PID; gp-0x6ad6 is its feedback/bias term) -> gp-0x6ad4 -> aggregator -> governor -> gp-0x6b98
```

**Censuses (dual-encoding scan) [EVIDENCE]:** `gp-0x6bfc` 2 hits · `gp-0x6bfe` 2 · `gp-0x6b70` 2 ·
`gp-0x6ad6` 3 · `gp-0x67ab` 3 (the `0x37FE6` hit is a genuine `ld.bu` — the aggregator's entry read).

- **`0xC64AD`..`0xC64B3` are 0/1 ENABLE FLAGS, not gains.** **`0xC64B0` gates `gp-0x6b70`.** The
  aggregator's speed LERP is **flat 1024**.
- **`0xC6200` has 15 readers**, and the governor cals `0xC6202/04/06/08` cluster **disjointly** at
  `0x045410`–`0x0457de` ⇒ **`0xC6200` is NOT governor-shared** — confirmed twice, and consistent with
  V40 having written `0xFFFF` into `0xC6206`/`0xC6208` while leaving `0xC6200` untouched.
  ⚠ **3 of its 15 readers remain unidentified ⇒ the RULE 11 census on it is NOT complete.**
- ⚠ **`Y[0]` of the RAM LERP is UNRESOLVED.** `Y[0] = *(u16*)(gp-0x3714)` via `movea -0x3714,gp,ep`
  @`0x39508` + `sld.hu 0x0,ep,r11` @`0x3950C` → `st.h r11,-0x641c,gp` @`0x39522`, inside `FUN_000389ec`.
  The only ordinary-addressing access image-wide is a **store-zero** at `0x38D22` — **a lead, not an
  answer**; the block is `ep`-relative and invisible to a displacement scan.

### 🛑🛑 Three new "flatten a curve into a relay" hazards in this chain
This is the **V72/V80 error, one address family over**, and V80 is the recorded cost of making it once:
the worst grinding in this car's history.

| cell | stock | forbidden move | what it produces |
|---|---|---|---|
| **`0xC4080`** | **0** | 🛑 **NEVER RAISE** | `FRICTION += cal/1024 × ratio` has **no `\|model\|` factor** ⇒ a **latent PURE COULOMB RELAY**: amplitude-independent, unbounded in index |
| **`0xC63AE`** | 1024 | 🛑 **never → 0** | LERP index ≡ 0 ⇒ output ≡ `±Y[0]`, a constant ⇒ **a pure relay at full authority** |
| **`0xC6200`** | 8192 | 🛑 **never < `Y[0]`** | the clamp produces the same relay from the other side |

### 🛑 `gp-0x67fa`'s reachable set is effectively {11} alone
State 5 **structurally dead**, state 10 measured **0.0000%**, state 4 measured **0/123,277**.
⇒ **V42's `0x454FE` is present on V85 (`0xB5`) and MEASURED INERT.** Keep the byte — it has been silently
lost three times and costs nothing — but **carrying it is not addressing ratcheting**, and no build may
be justified on it.
⊕ **`gp-0x671a` is RULED OUT** as a lever axis: stuck at 0 across **1,158 reversals** on V64.

---

## 6. LEVERS KILLED ON EVIDENCE THIS SESSION

Full table with reasons is in `docs/BUILD-LINEAGE.md` → *"Struck LEVERS, 2026-08-09 (late)"*. In brief:

| lever | verdict |
|---|---|
| **`gain_A` rec0/rec1 lowered** | **ENGAGED-INERT.** Lever B's gate repoint makes `lp = latActive`, and `0x3AB5E` **overwrites** `gain_A` with `[0xC6444]`=512 ⇒ **V84/V85 already deliver 512 engaged at every speed.** Already-run, **twice-failed** pre-registered experiment (FAIL on V84, FAIL on V85) |
| **Lever A** (`0x3AB76`/`0x3AC20`) | **DO NOT RESTORE** — the `sar` is **ungated** ⇒ reproduces V62/V65 **manual** behaviour verbatim, and `r24 ≥ ~2` is necessary for grind #2 in every build that produced it. ⚠ Its int16-overflow leg is **WITHDRAWN** (the intermediate is 32-bit: `5120 × 5244 >> 9 = 52,440` fits); the verdict rests on the manual-arm leg alone |
| **13-point LERP `0xC6B66`/`0xC6B80`** | **DEAD.** `gp-0x6a10` is **absolute steering angle**, not a tracking error (99.94%, step on the threshold's own value, holds in the MANUAL arm). 88.6% of engaged driving is in its flat first segment ⇒ a **0.878× broadband trim** |
| **FactorD** | **STRUCTURALLY INERT where the symptoms live** — FactorC multiplies in first with `X[0]` = 34.97 km/h, `Y[0]` = 0, in all four modes. Three independent confirmations |
| **`0xC63A0` 1024 → 2048** | **INERT** — `ch₀` is exactly zero on **98.8%** of engaged frames on route `6e` |
| **`0xC61F6` 3 → 0** | **DO NOT** — a deadband is the **dual of a relay**; deleting it **adds** small-signal gain, the destabilising direction |
| **`0xC61D6`** | **already rejected** — activates a dormant uncalibrated 2D map. **There is no usable cal-only rate-limiter lever on this path** |
| **`FUN_00038148`/`gp-0x6b70` as the ~8 Hz generator** | **REFUTED** (§4) |

🛑 **This REFUTES *"FactorD is the only frequency-selective lever in this firmware"* — THIS FIRMWARE HAS
NONE**, which also removes the standing argument that FactorE cannot do what FactorD can.

🛑 **`0xC63A0` ledger corrections:** reverted at **V83a** not V84; **V76g also carried 2048**; **V76 and
V80 are 1024**. Consequences: **V42 flew at 1024 with the ratchet called fixed ⇒ 2048 is not necessary**;
**V72/V73 also carried Honda's damper**, so `ch₀` was zero on them too ⇒ the **V72/V73 correlation has no
mechanism**; and **V84's own `0xC63A0` revert was itself inert** and cannot explain the V84 step.

⊕ **Recorded, virgin, untested and NOT proposed:** `FUN_00036388`'s **relay-with-dwell** — dwell counter
`gp-0x6a82`, +1/tick while `|gp-0x6b64| < 0xC618A` (=1024), ceiling `0xC627E` = 20; **past 20 ticks the
output SNAPS to 1024**, writing `gp-0x6b62`. Cals `0xC618A`/`0xC627E`/`0xC63C0` never edited by any build.
Disfavoured by the same no-comb evidence.

---

## 7. V86 — BUILT, UNFLASHED

**V86 = the flown V85 + ONE cell: `0xC40D4` 573 → 286** (`3D 02` → `1E 01`, `tp+0x50D4`), the
**command-branch EMA** in `FUN_0003b8f6` (**α 0.1399 → 0.0698**), plus a probe cave.
Builder `analysis-2020accord/builds/v80_v107/build_v86_tva.py`; gate checker `analysis-2020accord/verify/verify_v86_gates.py`.
🛑 **Artefact names and SHA256s are pending the builder's cut — take them from disk, never from a
report.**

### It is a FREQUENCY experiment, pre-registered as a RATIO
It moves the loop's **−180° crossing from 7.79 Hz to 6.2–6.9 Hz**.
**Pre-registered: `f(V86)/f(V85) ∈ [0.797, 0.875]`** (median 0.843; min/max over Q ∈ [2, 40] ×
delay ∈ [0, 10] ms) = **3.3 FFT bins at NFFT 256 / fs 100 Hz**.

- ✅ **CONFIRMED** if the peak lands in **[6.2, 6.9] Hz** with the ratio CI excluding 1.00.
- 🛑 **FALSIFIED — the linear-loop hypothesis DIES — if it stays at 7.79 Hz.**
- ⚠ **AMBIGUOUS, and explicitly NOT a null**, if the ratcheting is too weak to locate a peak.

**Why a frequency claim at all:** **amplitude ratios have failed four builds running**, and the
split-half null is **[0.63, 1.50]** wide. A frequency shift is the one prediction this instrument can
actually resolve.

**Why 286 and not 1146** (the same swing, other direction): 286 moves *away* from the 12.8 Hz plant mode
— conservative on the **unpinned** Q — and it **LOWERS** estimator HF gain to **0.650× @20 Hz / 0.585×
@28 Hz**, where 1146 would **raise** it 1.216× / 1.355×.

### 🛑 It cannot limit max LKAS angle rate, and this is proved
An EMA has **`|H(0)| = α / (1 − (1 − α)) = 1` exactly, for every α** — verified numerically at
α ∈ {0.0349 … 0.9998} → **1.000000000000**. **Only transient tracking changes.** The operator's standing
hard constraint is therefore satisfied **by construction**, not by argument.

### Mode proof (RULE 7)
573 appears **exactly once** in `[0xC4000, 0xC4200)`, and **no stride S ∈ [2, 0x400) repeats it**
(contrast FactorC's stride `0x14`). It is a bare `tp` scalar.

### The probe — `0x14A` byte 4
| bit | rung |
|---|---|
| `b7` | `gp-0x6b70 < 0` |
| `b6` | `gp-0x6b70 != 0` |
| `b5` | `\|gp-0x6b70\| ≥ 512` |
| `b4` | `gp-0x67ab < 2` — **the aggregator gate** |
| `b3` | 1, fingerprint |

**`b7⇒b6` and `b5⇒b6` are EXACT — the DUALS of V85's `b6⇒b7`** ⇒ **one `b6 ∧ ¬b7` frame refutes V85 and
one `b7 ∧ ¬b6` frame refutes V86.** Build identity is free, with no free parameter.
⊕ **`b7` + `b6` is also a free RELAY-vs-LINEAR discriminator:** a linear term must pass through zero at
every sign change (`b6` clears near `b7` transitions); a relay jumps (`b6` stays set).

### ⚠ V86B was designed and is ON HOLD
A damper creep re-open (**FactorE `X[0]` 60 → 12**). The cross-build dose-response is **3.2× with
rho = −0.679** and the dose crosses build order twice — **but** the within-route engaged/manual test
shows **no separation**, **V83a is a counterexample**, and the test **cannot run on V84 at all**.
`[BELIEF]`, not established.
📋 **What settles it costs ZERO BYTES: a creep protocol alternating engaged and manual over the same
stretch at 2–9 m/s.** Run that before spending a build.

### What class of build V86 is, against the whole arc since V38
| era | builds | class |
|---|---|---|
| the cause | V38 | LKAS **authority** ×2.13 |
| authority / filters / poles / caves | V39–V52c | rate guards, slew caps, EMA poles as **attenuators**, notch biquads (**V40, V48B bricked**) |
| telemetry and lane mutes | V53–V61 | measure, then mute |
| the rate lane | V62–V73 | `sar` ×2 (Lever A), then the `latActive`-gated r24 arm (Lever B) |
| the base-assist damper | V74–V83a | arm and dose an engaged-only Coulomb damper (**ours**, armed at V74) |
| damper reverted to Honda | V84 | delete the damper in both engaged columns + re-arm Lever B |
| **nonlinearity SHAPE** | **V85** | relay → viscous on a virgin 1 kHz term (`0xC40BC`) |
| **PHASE / LAG** | **V86** | **move a loop mode's FREQUENCY. Nothing in the arc has ever done this** |

🛑 **V86 is not a re-run of anything.** `0xC40D4` has **never been written by any build**, and the
*dimension* — when, not how much — has never been an arm. The one honest caveat is that its target,
ratcheting, has **no instrumented history** and the claim rests on a frequency shift that a weak ring
may not resolve — which is exactly why **AMBIGUOUS** is pre-declared as its own outcome and not folded
into "null".

---

## 8. METHOD RULES EARNED THIS SESSION

1. 🛑 **A RUNG MUST BE SIZED AGAINST ITS OWN LANE'S REACHABLE OUTPUT — and a falsifier only fires if it
   COULD have fired.** V84's `b7`/`b6` tested `|r24| ≥ 1024` on a lane whose input never exceeded
   `|r1| = 201` ⇒ **0.0 across 68,235 frames in BOTH arms**, misread as *"the lever was out of force."*
   The same error runs the other way: **V85's damper abort criterion "passed" on 22.4 s of engaged
   ≥80 km/h exposure — that is not a pass.** Folded into `BUILD-LINEAGE.md` GATE 3.
2. 🛑 **A COUNT-ONLY RECORD CENSUS IS BLIND TO A WRITE INTO AN ALREADY-NON-STOCK RECORD.** Assert
   **every** record byte-identical to the BASE unless declared. It is **340 pointer-array slots
   (10 arrays × 34 modes), not 58**; **34 non-stock records**, including modes **32/33**.
3. 🛑 **DYNAMIC GHIDRA TOOL REGISTRATION IS SCOPED TO THE AGENT SESSION AT SPAWN TIME.** Three tracers
   were **silently blind all session** — `check_tools` reported "callable" while direct calls errored.
   **Every future session must smoke-test `get_current_program_info` as its FIRST call.**
4. 🛑 **A prediction that comes true for a reason that is not yours is a COINCIDENCE until the real
   reason is found.** This session's own case: `0xC40BC` was frozen for the right disposition and the
   wrong reason until the biased describing function was computed.

---

## 9. WHAT IS HONESTLY UNRESOLVED

- **Ratcheting is unfixed and still has no instrumented history** beyond the frequency line itself.
  V86's test is the first probe aimed at it since V72.
- **`Y[0]` of the `FUN_00038148` RAM LERP** — `ep`-relative, one store-zero lead, otherwise unknown.
  Anything that clamps or scales that LERP is un-sizable until this is closed.
- **3 of `0xC6200`'s 15 readers are unidentified** ⇒ RULE 11 is not satisfied on it.
- **The ~20.90 Hz creep line** is `n = 6` windows on V84 — suggestive, not measured.
- **Micro- vs macro-ratcheting are not separated**, and this session could not separate them.
- **V86B's damper creep hypothesis** is `[BELIEF]` and is settled by a drive protocol, not a build.
- **The 26–31 Hz band and the highway regime have no V85 measurement at all** — route `6e` did not have
  the exposure, and no verdict on them may be carried forward from this flight in either direction.
