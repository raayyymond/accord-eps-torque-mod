# HANDOFF 2026-08-10 — V89 flew and changed nothing; the mechanism is FRICTION, not inertia; V90 is a probe

**Operator's own verdict on V89: *"fixed nothing, still only as good as V88."*** Every instrument agrees
with him. Nothing in this session is called fixed.

**Operator's opening question, verbatim:** *"the firmware not accounting for such high LKAS-driven
torques which then feed into significant driver torque steering signal (opposite direction than LKAS)
due to steering wheel mass/inertia"* — and a request to research how production EPS cancels the
overlay, keeping firmware changes minimal and avoiding code caves.

**Answer, in one line: the symptom chain is real, the sign is backwards, the inertia mechanism is
refuted, the cancellation he wanted already exists in firmware — and the surviving mechanism is
load-dependent friction, which needs damping rather than cancellation.**

---

## 0. WHAT IS ON THE CAR, AND WHAT WAS BUILT

**On the car: V89**, flown as routes **`75`** and **`76`**, both fault-free.
**Built this session: V90 — PROBE-ONLY, unflashed.** No calibration cell changes. See §7.

**V89's flight, the largest exposure in the corpus:** 20.68 engaged minutes (2.8× route 73),
**695 s engaged ≥50 km/h** against route 73's 119.6 s, 274 s ≥80 km/h, 469 s in the operator's
micro-ratcheting regime. `STEER_STATUS` clean, DTC-active duty 0.000000, zero sentinels, no EPS entry
in 3,749 `onroadEvents`.

| pre-registration | verdict |
|---|---|
| IDENTITY | **PASS** — V89 is on the car |
| H1 probe fires | **PASS** |
| **H2 THE LEVER** | 🛑 **FAIL** — no band-specific fall survives the order veto |
| H3 the constraint | **PASS** — 0.5–3 Hz command did not fall; no sign-chain inversion |
| H4 the operator | *"fixed nothing"* |

**H2 in full.** On the **intrinsically order-clean stratum** (v ≥ 22.2 m/s; 0/59, 0/162, 0/43 vetoed —
no veto needed, so the screening asymmetry is structurally absent): contrast **0.947 [0.827, 0.979]**
against a same-build placebo band of **[0.900, 1.111]** ⇒ **0.92σ, FLAT.**
🛑 **The block-bootstrap CI excludes 1.00 and would have been reported as a resolvable 5 % fix.** It
sits inside its own placebo band. **That is the placebo control earning its keep on the first use.**

**And V89's own probe says why it could never have worked.** The friction term is `sign(motor rate)`-
gated:

| regime | engaged s | `\|friction\| ≥ 0.0625` |
|---|---|---|
| <1 °/s | 297 | **0.000** |
| **micro-ratcheting 1–13 °/s** | **782** | **0.009** |
| ratcheting 13–50 | 112 | 0.235 |

⇒ **The cell K1 doubles is negligible on 99.1 % of the regime where the operator names the symptom.**
Not a falsification of the friction account — arithmetic saying the lever was pointed away from the
target. ⊕ The rate-gating is a **fifth independent confirmation** that the term is Coulomb friction.

---

## 1. ★★★★★ THE OPERATOR'S HYPOTHESIS, ADJUDICATED PIECE BY PIECE

### 1a. The symptom chain is REAL and Honda documented it
**US11685438B2, Honda Motor Co, priority 2020-03-13**: `Tsu = (Tx + Lu) − Ts`, with the verbatim
justification *"if the torque applied by the rack and the torque applied by the steering wheel are
torques in the same direction, the values of these torques have opposite signs."*
🛑 **BELIEF at best about THIS firmware** — the patent names no platform or model year, `Lu` is *"a
mapping … for example"* with no gain, units or filter given, and it does not appear in claims 1–7.
**Do not cite it as documentation of `39990-TVA-A160`.** What survives is narrower and still useful:
**there is no differentiator anywhere in Honda's correction path**, so Honda modelled the
contamination as **memoryless in command magnitude** — not rate-dependent.

### 1b. 🛑 THE INERTIA MECHANISM IS REFUTED
Driving-point impedance `T_bar/ω`, engaged hands-off, coherence² 0.5–0.84, 28–59× the quantisation
floor, polarity anchored first (`phase(T_bar, ω)` = −12.3/−6.3/−13.4° at coh² 0.95–0.98, no flip):
```
predicted:  inertia +90deg  ·  damper 0deg  ·  spring -90deg  ·  negative damping 180deg
measured:   2-4 Hz -152/-168/-174   6-9 Hz -129/-143/-139   12-16 Hz +-175..178
```
**Inertia demands +90°. The column reads −130° to −175° — about 220° away.**
⊕ The *magnitude* is the right order (J = 0.04 kg·m² at 7.5 Hz ⇒ ~2350 ct·s/rad vs 4362–5915 observed),
so an inertial component of the size he imagined is **not excluded — it is just not dominant.**

### 1c. ★★★★ `Re(Z) < 0` ACROSS 2–16 Hz — NEGATIVE DAMPING, MEASURED DIRECTLY
`cos(phase) < 0` right across the band, largest in |Z| at 9–12 Hz, `Re(Z) ≈ −3300 ct·s/rad` at 6–9 Hz.
⚠ **The control that does not exist:** manual + hands-off + moving has **6 / 1 / 0** qualifying windows.
Nobody drives hands-off without LKAS. ⇒ **these logs cannot separate "the EPS loop is anti-damped"
from "the column is anti-damped."** Needs a deliberate hands-off coast.

### 1d. THE SELF-INTERFERENCE FINDING **SPLITS** — and half of it is withdrawn
`cmd` and `tq` each residualised on steering angle, wheel rate, IMU lateral accel and yaw rate:

| band | raw | **partial** | control (5 s shift / manual arm) |
|---|---|---|---|
| **0.2–3 Hz** | 0.73–0.83 | **0.396 – 0.593** | ≈0.00 |
| **6–9 Hz** | 0.43–0.52 | **0.001 – 0.070** | ≈0.00 |

⇒ **Self-interference STANDS at 0.2–3 Hz and is WITHDRAWN at 6–9 Hz.** And "the car is just turning" is
dead at low frequency: the partial is **as large on the straight as in a corner**, larger on both
independent proxies (a de-biased IMU one and a bicycle-model one, correlated only +0.297).
🛑 **The 6–9 Hz collapse does NOT establish the alternative either** — partialling on angle and rate
removes genuine self-interference too, since it is mediated by column motion. **At the ratchet
frequency the test is uninformative between the two.** What it establishes: no command-locked bar
torque at 7.8 Hz beyond what the column's kinematics already account for.
⊕ **This makes §1c the stronger result** — `Re(Z)` is a torque-versus-velocity relation living *inside*
the kinematic channel, so partialling cannot subtract it.

### 1e. 🛑 THE FIRMWARE ALREADY CONTAINS THE CANCELLATION HE WANTED
`FEASIBILITY-SELF-INTERFERENCE-CANCELLATION.md` §2.1 — *"no compensation, decoupling or cancellation
term anywhere"* — is **REFUTED**. [EVIDENCE, orchestrator-verified in Ghidra]
- `FUN_00026c80` (the 11-slot arbitration mixer) computes `sVar38 = clamp(Σ gp-0x62c8[i], ±0x2800)`,
  stores it to **`gp-0x6b4e`**, and tail-calls `FUN_00042ac6(sVar38)` whose whole body writes
  **`gp-0x6afe`** ⇒ **`gp-0x6afe ≡ gp-0x6b4e`, bit for bit.**
- `0x43ae0`–`0x43b52`: `ld.h -0x6afe[gp]` → zero-reject ±0x2800 → **`add r20,r12`** → `clamp(±gp-0x4f64)`
  → `clamp(±0x2000)` → `st.h r8,-0x6b98[gp]`. **That is the overlay entering the motor command.**
- `tp+0x73a8` = **`0xC63A8` = 1024 (unity)** on stock/V38/V81/V84/V87/V88/V89 — the weight `gp-0x6b4e`
  carries in the observer's reconstruction, **with the same zero-reject window as the motor path.**
⊕ **`FUN_0003b8f6`'s model input is `gp-0x6b98`, the TOTAL delivered command** (`0003b8f6: ld.h
-0x6b98[gp],r7`, the function's first instruction). ⇒ **this ECU does not violate the universal
published practice that the actuator's own command is a known plant-model input.**
⊕ ★ **And Honda went further: every assist channel has a per-channel DECLARED-DISTURBANCE slot.**
Field D of the channel struct (offset +8) has clamp **±20000 — bit-for-bit the observer model's own
output clamp**, is the only field summed **ungated**, and its sole destination is the residual
(`gp-0x633c+2i → gp-0x6324+2i → gp-0x3d90 → gp-0x6bfa → res`). **LKAS passes ZERO** (`0002b530:
sst.h r0,0x8[ep]`) — **and zero is CORRECT**, because LKAS is already in the reconstruction at unity
and filling it would double-count. Recorded as the architecturally-correct injection point for any
future observer-bias term; **not recommended.**

⇒ **There is no target for an "add the missing cancellation" cave. The cancellation exists.**

---

## 2. ★★★★★ THE MECHANISM: QUASI-HARMONIC FRICTION-INDUCED VIBRATION

**This overturns the kit's standing "the firmware search is CLOSED" conclusion.**

Friction-induced vibration has **two regimes**, distinguished since 1970 (Brockley & Ko, *ASME J.
Lubrication Technology* **92(4):550–556**):
- **stick-slip / relaxation** — genuinely sticks, sawtooth, rich odd-harmonic comb, phase-locked to
  reversals, **frequency tracks drive velocity**;
- **quasi-harmonic FIV / pure slip** — never sticks, **near-sinusoidal**, low harmonic content, no
  reversals to lock to, **frequency pinned at the structural mode**, and **in ring-down it is
  indistinguishable from a lightly-damped linear resonance.**

**Every one of the kit's four "not a relay" nulls is what the second regime PREDICTS:** odd/even comb
**0.858** [0.739, 1.000] against a positive control reading 1.204 at 15 % injection · 3:1 PLV z ≤ 1.05 ·
switching-surface time-locking **−0.0375** · ring-down ζ **0.017–0.036** passing its own control. So are
two further measurements nobody connected: amplitude **rising** with sliding velocity (1.16× at 2 °/s →
3.94× at 100 °/s) and **speed-invariant 7.79 Hz** (a stick-slip oscillator would not be).

> **The kit did not falsify the friction hypothesis. It falsified the RELAY FORM, and in doing so
> identified WHICH FORM is running.** `ζ_eff = ζ_struct − ζ_friction(load)`, and ζ_friction grows with
> mesh load, which grows with command magnitude. **`Re(Z) < 0` in §1c is that, measured.**

### 2a. 🛑🛑 THE CONSEQUENCE THAT REACHES BACK ACROSS THE WHOLE ARC
**Under FIV the response to added damping is THRESHOLD-LIKE, not proportional.** Below threshold
nothing visible happens; above it — Brockley-Ko — *"the introduction of suitable damping will quench
the vibration entirely."*
⇒ **This kit's core method is dose ladders, and it reads small-dose nulls as falsification. That
inference is valid for a linear mechanism and INVALID here.** How many "FALSIFIED" labels it touches
has **not** been audited. **Size for crossing the threshold, not for a measurable improvement.**

### 2b. ★★★★★ THE LOAD AXIS — an agent tried to destroy it and could not
Same 175 engaged windows / 8 episode blocks, three responses:

| response | log \|cmd\| | log \|rate\| |
|---|---|---|
| **residual `gp-0x6b70`** | **−0.012 [−0.659, +0.472] NULL** | **+0.774 [+0.515, +1.178] ✔** |
| **symptom `e_6-9`** | **+1.074 [+0.812, +1.445] ✔** | +0.100 [+0.021, +0.220] |
| control `e_32-38` | +0.124 [−0.110, +0.431] NULL | +0.369 [+0.186, +0.510] |

Then, one change at a time:

| step | coefficient |
|---|---|
| original (raw rms) | +1.064 [+0.790, +1.418] |
| **DEMEANED — fluctuation only** | **−0.037 [−0.055, +0.119] NULL** |
| **mean \|cmd\| — pure LOAD proxy** | **+0.955 [+0.696, +1.276]** |

⇒ 🛑 **The effect is carried ENTIRELY by how hard LKAS is PUSHING and NOT AT ALL by how much the
command FLUCTUATES.** That kills the best non-friction alternative on its own test: **a resonance is
excited by fluctuation; a DC offset cannot excite 7.8 Hz.** It also refutes the circularity worry —
the shared 6–9 Hz component lives in the AC part, which contributes zero.
**Survives angle, lateral accel and rate as competitors** (the command coefficient *grows* to +0.934
when they are added; they go negative), band contrast **+0.587** with all in, over **6 routes / 39
blocks**. Independently reproduced on a **third** instrument (openpilot's exogenous `0x0E4`, 35× command
range) at **p < 0.002** against a block-permutation null, with `log|rate|` inside the null at p = 0.205.
⚠ **One cut disagrees and is recorded, not buried:** restricted to the order-clean highway stratum
alone (343 windows) it inverts. Power or a real regime difference — not read either way.

---

## 3. LEVERS KILLED THIS SESSION, WITH THE REASON

| lever | verdict |
|---|---|
| **The observer "leak" (`0xC40D4` / `0xC63AC`)** | 🛑 **DEAD ON-CAR, three ways.** The residual `gp-0x6b70` was probed directly (V86/V86B rungs): **no engagement response** (raw +16.3 pp collapses to **+0.6 pp** under the motion screen — manual frames were *parked*; pooled −0.083 [−0.507, +0.513]), **no sign coupling** (inside the shuffled null at every lag; the apparent peak is at **+1.00 s** = manoeuvre-scale co-drift), and **the wrong axis** — rate-driven, command-null, **disjoint from the symptom on both axes.** |
| The observer enable gate | 🛑 **TAUTOLOGICAL.** `\|gp-0x6b98\| ≤ 0x2000` against a producer that clamps to **exactly** ±0x2000 four instructions earlier, inclusive at both rails. **It can never trip.** Same idiom one hop down (`\|gp-0x6bfe\| ≤ 20000` vs a ±20000 clamp). |
| **K1 (`0xC40D2`) at a real dose** | 🛑 **STRUCTURALLY BLOCKED.** Fundamental gain is **1 for every K1** (Fourier: the element is bilinear, not a relay); what K1 controls is **even-harmonic injection** `r·g·4/(3π)`. **Ceiling `K1 ≈ 1024`** — at `g = 1, \|r\| = 1` the positive half of the model is annihilated (half-wave rectifier). But the ceiling binds where the term is **saturated** (\|rate\| ≥ 10.6 °/s, **13 % of frames**) while the effect is wanted where it is **on the ramp** (the other 87 %). **One scalar cannot serve both; conflict 1.4–3.8×.** |
| **`0xCBE74` friction-comp gain ×3** | 🛑 **WITHDRAWN — see §4.** |
| The observer's 3-tap FIR (`0xC404C`/`0xC4050` = 0.0f) | 🛑 **Not a lever.** It multiplies the *sensor* term, which is additive ⇒ **no coefficient can alter the command's transfer function.** And 3 taps span 2 ms against the 11 ms needed. A gain trim with a DC side-effect. |
| Feed-forward cancellation cave | 🛑 Not recommended: the cancellation exists (§1e), Honda's own corrector runs behind a **5 Hz** filter (absent at 18–28 Hz), and `K` is an impedance-divider ratio set by grip and road compliance, not a constant. |

---

## 4. 🛑🛑 THE `0xCBE74` FRICTION ROW — THREE LINEAGE OVERSTATEMENTS ON ONE CELL IN ONE SESSION

The session nearly re-flew a lever with a fault association. The record was wrong; so was the
orchestrator, twice, in **both** directions. Byte-verified truth (dereference `0xCBE74 + mode*4`, Y at
record **+8**, nine images):

| build | ×1.5 on a **live** column (mode 24/26)? | on-car |
|---|---|---|
| V73 | **NO** — mode 10 only, **DISENGAGED**, inert here | flew clean — **says nothing about this lever** |
| **V74** | **YES** (13 engaged modes) | 🛑 **HARD FAULT, latched** |
| **V75** | **YES** | 🛑 **HARD FAULT, latched** |
| V76 *(flown = `_v76_v38base_relu_damper`)* | **NO** — reverted by the V38 rebase | flew route 65 clean |
| V77 / V77B | YES | **NEVER FLEW** |

⇒ **×1.5 on a live column flew exactly TWICE and both flights hard-faulted. ZERO clean flights, ever.**
🛑 **AND IT INVERTS A STANDING ATTRIBUTION.** The faults are attributed to `0xC407E` = 850 — **but V73
carried 850 and flew clean.** V73→V74 is **64 differing runs (13 friction sites + 51 others)** so the
row **cannot be pinned** — but **the control meant to exonerate it is the thing that implicates it.**
⇒ status **EXONERATED → OPEN SUSPECT**; no dose flies until a probe measures the lane.
⚠ **REFINEMENT that halves it:** **V74 faulted in MANUAL** (mode 24), where the ×1.5 was **byte-identical
to Honda** ⇒ by RULE 10 that fault cannot be laid at this row. **V75 faulted ENGAGED** (mode 26), where
it was live. **Flight level 2-for-2; MODE level 1-for-1.** Both true; neither restores exoneration.
⚠ **Two artefacts share the V76 build number and they disagree on BOTH RULE-11 cells, in the same
direction.** A glob does not merely pick the wrong file — **it answers the opposite question.** **The
lineage row's BASE column is the discriminator.**

### 4a. What the safety work established anyway — keep it, it is the basis for any future dose
`DampAxis`, all EVIDENCE: **not a relay** (describing function exactly **1.000 through ×4**, first
departure 0.881 at ×6) · **the ±1024 zero-reject can NEVER fire** because `0xC407E` clamps the lane to
±511 first ⇒ **both failure modes that killed the rate-indexed damper are absent** · **safety ceiling
×3** (clamp binds at 1.50° vs 0.96° measured = 1.56× margin; `|Y|×4` **overflows int16**) · and
★ **the dissipative sign is closed STRUCTURALLY**: phase of `−gp-0x6c2c` vs rate stays in the
dissipative half-plane at **every frequency to Nyquist** (+76° at 7.79, +44° at 28, −25° at 200,
**never reaching −90°**, because two first-order poles asymptote to 180° and the differencer starts at
+90°) ⇒ **raising this gain cannot destabilise by sign at any frequency.** Best GATE-2 position of any
dynamics lever this kit has flown.
🛑 **Corollary, independent of the faults:** raising `0xC407E` **above 1024** would give the lane a
zero-reject dropout it does not have today. One more reason 511 stays.
🛑 **The dose CANNOT be sized.** The ring/Q requirement is in **column-torque counts**; `gp-0x6b26` is in
**aggregator counts**; the conversion needs a plant transfer this session proved unmeasurable (the
engaged `cmd→column` estimator returns a **negative group delay**). **Both sizing inputs were struck.**
⚠ **A strike against it as the CAUSE, recorded:** `gp-0x6c2c` is acceleration-like, so a term driven by
it scales with rate — and the corpus says the amplification is **rate-independent**. **Defensible as a
damper, not as the mechanism.**

---

## 5. INSTRUMENT CORRECTIONS — see `STATE.md` for the full text

1. **The `0x18F`/`0x14A` skew is REAL and now measured at source**: `0x14A` is processed before the
   co-logged `0x18F` on **91.28 % of 51,691 events**, so the row carries the previous frame. **It is a
   MIXTURE, and the correction is ~9.15 ms, not 10.0**, with an **amplitude term of 0.99 at 7.79 Hz
   falling to 0.93 at 23 Hz** that nobody had. Residual on the existing caches is **bounded**: ≤2.4° and
   ≤1 % at 7.79 Hz; ≤5.4° and ~7 % at 23 Hz. **Only re-extraction recording the `0x18F` timestamp per
   row is complete.** **r76 STAYS IN.**
2. **Episode block bootstraps understate CROSS-BUILD uncertainty ~2.8×** (0.37 vs a 213-pair placebo's
   1.03). **Any cross-build ratio quoted with a block-bootstrap CI and no placebo-pair null is
   over-confident.** Not audited backwards. **This is the highest-value outstanding methodological item.**
3. **The wheel-order veto is ASYMMETRIC** — orders 1–6 never fire on the 32–38 Hz control at
   parking-lot speed while orders 3–4 hit 6–9 Hz constantly. Use the **v ≥ 22.2 m/s** stratum, where
   order 1 has climbed to 10.68 Hz and no veto is needed on either band.
4. **`memory/MEMORY.md` is 268.8 KB / 381 lines and a whole-file `Read` HARD-FAILS** (~130,000 tokens,
   5.2× the cap). **Any brief saying "read `memory/MEMORY.md`" is a no-op unless the agent chunks it.**
   Not restructured — the operator's call.
5. **Ring-down is unsupportable on this corpus: 1 usable edge in 99.** All 15 edges on routes 73/75/76
   fail. **8 of 10 end in BRAKING**, and the two longest engagements in the corpus (359.6 s and 596.2 s,
   at 15 and 45 km/h) were lost *purely* on disengage cause. ⇒ **it is a driving-protocol problem, not
   a data problem: cancel button · foot off the brake · hands off · hold 5 s either side · do not
   re-engage.**

---

## 6. 🛑 NAMED TRAPS — four classes, ~20 instances, one session

1. **A COUNT or an INDEX RELATION is not a PHYSICAL FACT.** Four instances: r76's "index drift" read as
   timing drift; a `gp-0x6752` writer census undercounting because a disp16 scan is blind to the 6-byte
   form; V86's rung map applied to V89 (**V86B swapped b5/b6 and V87–V89 inherit V86B's constants**); a
   "payload age vs the most recent `0x18F`" metric that assumed its own conclusion.
2. **AN ADDRESS IS NOT A MODE.** Three instances. **Dereference `0xCBE74 + mode*4` and print the mode
   number beside every address.** `0xD6A5C` is mode **23**, not 24. **Y is at record base + 8** — writing
   Y values at `base+2` lands them in the **X array, compared UNSIGNED** ⇒ every speed below `X[0]` ⇒
   **a flat `Y[0]`: a silent, plausible-looking 5× at highway.**
3. **NEITHER GHIDRA NOR PYTHON ALONE IS COMPLETE.** `search_instructions` returned 73 with
   `truncated:false` against **3 more** real `ld.h` sites in unanalysed regions; a naive Python scan
   misses the 6-byte form; and **operand-text search cannot find register-indirect writes at all** —
   `clr1 0x1,0x6aec[r18]` behind `movhi -0x121,r0,r18` is a live writer of the cave's own target whose
   operand text never contains `1514`. **Both tools, set-differenced, every disagreement adjudicated.**
   ⊕ The 6-byte decoder is **0-indexed**: `hw1`/`hw2` are the **second and third** halfwords. Applying it
   1-indexed returns garbage and produced a confident false null this session.
4. **THREE SIGNAL-IDENTITY RECURRENCES**, and the meta-point is the lesson: **`gp-0x6a5e` is voted
   VEHICLE SPEED** (settled 2026-07-29; the earlier error already cost V44/V47) · **`gp-0x4f50` is a
   RATE, not an angle** (you only wrap-correct the difference of a modular quantity; `0x8000` is an
   INIT sentinel on the stored angle) · **`gp-0x6afe` ≡ `gp-0x6b4e`**.
   ⇒ **All three were caught by a teammate cross-checking an INHERITED claim, not by the agent that made
   it, and two had already been settled weeks earlier.**
5. ⊕ **"A check that produces no output is not a check that passed."** A payload validator printed
   nothing because the bytes it was checking were byte-swapped, so no instruction matched its filter.
   **Assert a boolean.**
6. ⊕ **A rung at duty 1.0000 is not merely wasted — reclaiming it is worth more than whatever you put on
   it, because it MOVES THE ALPHABET.** This is what makes V90's identity test single-frame.
7. 🛑 **THE BOOTLOADER CRC IS NOT UNIFORM 4 KB PAGES — and this was the session's one BRICK-CLASS error,
   made by the orchestrator.** It is a self-describing 50-block list. **One MAIN block spans
   `[0x013000, 0x0C4FFC)` = 0xB1FFC bytes**, trailer `0x0C4FFC`.
   **The per-0x1000 rule generalises ONLY ABOVE `0xC4000`.** The orchestrator inferred it from two
   builds (`V85→V86B`, `V88→V89`) whose edits all sat at or above `0xC4000` — and the "`0xC4000` block"
   *is* the main block, whose trailer merely **coincides** with `0xC4000 + 0xFFC`. **A coincidence was
   generalised into a rule, and the rule said to write four bytes into `0x055FFC`.**
   - **`0x055FFC` is LIVE CODE**: `64 77 b8 f0` = `st.h r14,-0xf48,gp` inside `FUN_00055f2e`.
   - It lies **inside** `[0x13000, 0x0C4FFC)`, so writing there **invalidates the very CRC it was meant
     to help**.
   - 🛑🛑 **AND THE ENCLOSING RECOMPUTE WOULD HAVE HIDDEN IT** — four bytes of executable code
     overwritten inside the CRC'd span, and the chain still walks **50/50 clean**. ⇒ **`walk_all_blocks
     == 0` is a necessary check, NOT a sufficient one. A corrupt build that passes its own verifier is
     the worst failure mode available here.**
   - ★ **The decisive evidence is a FLOWN BUILD, not an inference: `V38 → V87` edited `0x055DF2` — the
     exact cell V90 touches — and changed only `0x0C4FFC`** (plus `0x0C6FFC`, owned by the `0xC6000`
     block). `V87 → V88` likewise emitted no `0x03AFFC` for its `0x03AA96` edit.
   - ⊕ **Cheap independent test: a real trailer has sane link fields at −8/−6.** `0xC4FFC` →
     `start_page = 0x0000` ✓ · `0xD7FFC` → `0x0000` ✓ · **`0x055FFC` → `0x5EC8` ⇒ block start 0x5EC8000
     = 99 MB, past the end of a 1 MB image** ✗.
   ⇒ **ALWAYS derive the trailer set in code from the touched addresses (`V53.owning_block` /
   `verify_bootloader_crc.py`). NEVER from a hard-coded list — including a corrected one.** In this
   session the derivation is what caught the orchestrator: the builder followed the primary rule over
   the explicit instruction, and was right to.

---

## 7. V90 — BUILT, PROBE-ONLY, UNFLASHED

**Base: flown V89. NOT ONE CALIBRATION CELL CHANGES** — `0xC40D2` stays 204, so V89's friction lever
remains on the car and remains observed.

| bit | signal | why |
|---|---|---|
| **b7** | `gp-0x6b26 < 0` (sign) | the **only** channel reaching 18–28 Hz — 427's Nyquist is 24.9 Hz |
| **b6** | `\|gp-0x6bf6\| ≥ 512` = `\|model\|` | with b5, reads the `\|model\|`-vs-`ratio` confound off a 2×2 |
| **b5** | `gp-0x6ae2 ≠ 0` | **measured duty 0.49–0.54**; V89's rung unchanged ⇒ apples-to-apples |
| **b4** | `gp-0x6c00 < 0` | **the observer gate — never once measured** — AND the identity discriminator |
| **b3** | fingerprint | V89's all-zero payload is 50–60 % of frames |

**Plus the 427 repoint**: `0x55DF2` `6894` → `da94` ⇒ CAN 427 `MOTOR_TORQUE` carries **`gp-0x6b26` at
~9 unclipped effective bits**. **That cell has never been telemetered on any build**; its distribution
is the baseline that would let a future dose be **sized** rather than guessed.

**Identity is essentially per-frame:** `b4 == 0` is impossible on V86B/V87/V88/V89 (b4 railed at exactly
1.0000 over **254,085** frames) and is the ~100 % case on V90.

**80 bytes total: 74 cave + 2 repoint + 4 CRC. ONE trailer, `0xC4FFC`.** Five byte sequences are not
already in V89's flown cave; **each is copied from a Ghidra-verified twin, not encoded** —
🛑 **`subr` is `8031`, NOT `3080`; opcode `0x04` is `satsubr`**, which would saturate instead of negating
and corrupt b6 **on negative values only**.

⚠ **b6's threshold (512) is the ONE guessed parameter**, bracketed 0.10–0.50 by inverting V89's measured
duties. **Mitigation: it is one byte at `0xC4B4A`**, and the joint (b6,b5) table says which way to move
it. ⚠ **Two threshold bits give the joint distribution, not the per-frame ratio** — for that, point 427
at `gp-0x6bf6` on a later build.
🛑 **What b4 does NOT catch:** at `(char)gp-0x6752 == 0` the command branch zeroes, so model, friction
and inertia collapse **together** while the observer emits a valid non-sentinel output — and polarity 0
**PASSES** the gate. ⊕ Unreachable in the field: all five `gp-0x6752` stores write literal ±1.

---

## 8. NEXT STEPS, IN ORDER

1. **Fly V90.** Operator's call; flash only on explicit instruction naming the file and the bus.
   Score: the `gp-0x6b26` distribution (the deliverable), the gate duty, and the (b6,b5) joint table.
2. 🛑 **Audit the cross-build claims against a placebo-pair null** (§5.2). It is the highest-value
   methodological item and it reaches back across the corpus.
3. **Re-read every "FALSIFIED" label on a damping-class lever** in light of §2a — threshold-like
   response means a small-dose null is not falsification.
4. **`memory/MEMORY.md`** — operator's call, but it is currently unreadable in one call.
5. **The hands-off coast** (§1c) is the only new *driving* that would buy something: it separates
   "the EPS loop is anti-damped" from "the column is anti-damped", which no log on disk can.
6. ⊕ **Do NOT re-propose:** the observer leak, the enable gate, a K1 dose, the FIR taps, a
   cancellation cave, or a `0xCBE74` dose before V90 flies.

---

## 9. ON HOW THIS SESSION RAN

Ten agents. **Somewhere north of twenty decision-bearing claims were produced and then overturned**,
including at least three of the orchestrator's own — the "virgin cell" lineage claim, the uniform-4 KB
CRC model (**brick-class**, caught by an agent challenging it), and a mode-23 address named as mode 24.

**Nearly all were caught, most within one round, and the catches came overwhelmingly from a DIFFERENT
agent re-deriving an inherited claim** rather than from the agent that made it. That is the adversarial
structure working, and it is the reason the two dangerous errors never reached the car.

**It is also the signal that this many parallel agents on one problem is at the edge of reliable.** The
build was deliberately pushed toward *the smallest thing that answers a real question* rather than the
most capable thing that could be specified. **The measurement is worth more than the lever right now,
and a small measurement is worth more than a clever one.**
