# THE V99 ARC MAP — the record V99 must be designed against

**Built 2026-08-12 for the V99 design session.** Purpose: make it impossible for V99 to be a lever that
was already flashed and already falsified, and make the close-out able to state honestly how V99's class
differs from the last sixty builds.

> 🛑 **This file is a MAP, not an instruction.** Every claim is marked **[EVIDENCE]** (read from the
> record or the images, with the method) or **[BELIEF]** (inferred). Where the record contradicts itself
> the contradiction is printed rather than resolved.

**Read in full to build this:** `docs/STATE.md` (all 2,129 lines) · `docs/BUILD-LINEAGE.md` (RULES 3–13,
the V76→V98 catch-up rows, Part 2's cave/probe gates) · `docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md`
(rows V85→V98) · `docs/_v87_symptom_ladder.md` (the 2026-08-08 ladder — **extended here, not
re-derived**) · `memory/MEMORY.md` + `memory/MEMORY-PART2.md`.

---

# ⚡ THE V99 CHECKLIST — the whole file in one screen

**Nine hard NOs, from the partition (D3):**
1. ❌ **Not another command-HF-reduction build.** Measured fix for grinding, measured NON-fix for the
   ratchet, with a **disjoint** out-of-sample prediction (predicted 0.523 [0.451, 0.614], measured
   1.040 [0.759, 1.260]).
2. ❌ **Do not re-dose `0xC63AC`** — V97's null is on the INSTRUMENT (DC gain 1.000000; no phase
   observable was pre-registered). **NOT falsified. Do not record it as falsified either.**
3. ❌ **Do not re-dose `0xCBE74`** in either direction. UP is exhausted at 94 % of range and measured
   inert; DOWN is measured catastrophic **with a sign**.
4. ❌ **Do not raise `0xC40BC` to 6000** — measured 2.3× WORSE on the ratchet band.
5. ❌ **Do not restore Lever A** (`0x3AB76`/`0x3AC20`) — it is **UNGATED** and reproduces V65's
   *"subwoofer… regardless of LKAS engagement"* in the manual arm.
6. ❌ **Do not raise `0xC6446`** above 5244 — the ±8192 rail; 3.0× **pins** = relay class.
7. ❌ **Never raise `0xC4080`** (latent pure Coulomb relay) · **never `0xC63AE`→0** · **never
   `0xC6200` < `Y[0]`** — each is a one-cell edit that converts a shaped nonlinearity into a
   **full-authority relay**.
8. ❌ **Do not touch `0xC61F6`, `0xC61D6`, `0xC6194`, `0xC64B8`, `0xC6B12`, FactorD, `0xC63A0`,
   `0xC6372`/`0xC636E`, the return-to-centre lane** — all INERT IN FORCE on structure (D3.B3).
9. ❌ **Do not build another new CAN mailbox.** The gateway is a WHITELIST; only `0x14A`/`0x18F`/`0x1AB`
   cross. Use `0x14A` byte4 bits 7:3 + byte7.

**Five hard MUSTs, from the design law (D5) and the exposure (D6):**
1. ✅ **Every rung arrives with a PRE-REGISTERED DUTY.** *If you cannot say, before the flash, what
   fraction of frames it reads TRUE and why, it is not a rung.* Eight rungs have been lost to this.
2. ✅ **A POSITIVE CONTROL IN THE SAME BYTE**, whose duty you also predicted.
3. ✅ **A WITHIN-DRIVE MANUAL ARM** — make V98's *"optional and free"* LKAS-off seconds **MANDATORY**.
   It is the only control 17 s of one episode permits.
4. ✅ **The endpoint must be a WITHIN-FRAME DUTY or RANK on cave bits.** Every episode-based statistic
   the kit owns is unbuildable at 1 episode, and the column spectrum is unusable at ~5 km/h.
5. ✅ **Write the sentence a null will license, BEFORE cutting.** V97 is the case study, and its fault
   was written into the build script *before the flash* and flown anyway.

**The partition has FOUR categories, not three** (D3): **FALSIFIED** · **INERT** (by mode / by gate / in
force) · ⏳ **TRIED-BUT-UNSCOREABLE** — *flew, lever LIVE, INSTRUMENT failed* · **NEVER-TRIED** (virgin /
same-lever-other-way). ⭐ **The fourth is where the recoverable value is; filing it as "falsified" throws
away good levers, and this kit has done that before.**

**Four things the record leaves genuinely open** (threads, not recommendations):
- ⭐⭐ **`0xC63AC` — a LIVE lever on a LOAD-BEARING arm that has NEVER been scored.** V98's comparator
  (`b6` = 0.4235) proves ACTUAL is comparable to MODEL, removing the last structural excuse for V97's
  null. 🛑 **Recoverable ONLY with a pre-registered PHASE or GROUP-DELAY observable** — DC gain is
  1.000000 at every value, so re-dosing it blind is V97 again.
- ⭐ **`0xC40BC` BELOW 600** — census-confirmed untried; two independent measured lines behind the
  direction; ⚠ but it makes the term **more** relay-like, which is where V78/V79/V80 came from.
- ⭐ **The base-assist damper's SHAPE, not its dose** — §D1.3c: a standing memory saying this was never
  tried is **REFUTED from the images**; three builds flew it, and the variable separating the one good
  operator report from the disaster is `FactorE X[1]`, never isolated. ⚠ but it is **UNGATED** (acts in
  manual) and >4 points is a **CODE edit**.
- ⭐ **The `0xC63F8` = 33 vs `0xC63FC` = 328 ten-fold left/right asymmetry** — virgin on all images and
  **nobody has ever asked him whether the car feels different left versus right.** Costs one sentence.

---
---

# D1 — THE SYMPTOM LADDER, IN THE OPERATOR'S OWN WORDS

## D1.0 A vocabulary point that governs this session's brief

🛑 **"Stuttering" is the operator's own synonym for MICRO-RATCHETING. It is not a fourth symptom.**
[EVIDENCE — his own parenthetical, twice]

- **V97:** *"I did not feel any difference in grinding or **stuttering (micro-ratcheting)** behavior at
  all on V97, so I stopped the drive."*
- **V94:** *"Made the **stuttering and grinding** worse, by a lot. So much so that it vibrated the entire
  car, and I decided it was not safe to drive."*

⇒ the session brief — *"solve all grinding and stuttering/ratcheting issues"* — maps exactly onto the
three symptoms the kit has been failing on since V38: **GRINDING · MICRO-RATCHETING · RATCHETING.**

**His full vocabulary:** grinding · vibrating · micro-ratcheting · macro-ratcheting · ratcheting ·
stuttering (≡ micro-ratcheting) · excess friction / heaviness.

🛑 ***"grind #1" / "grind #2" / "the ring" / "S1–S4" are KIT JARGON for frequency bands.*** On record
2026-08-09: *"Not even sure what the ring is. We are working on grinding, vibrating, and ratcheting
issues."* Report in HIS words; cite the band only as the instrument behind it.

🛑 **MACRO-RATCHETING HAS NEVER BEEN GIVEN A BAND.** V42 was called *"FIXED THE HARD-TURN RATCHET"* on
feel alone and that attribution is **VOID** (`gp-0x67fa == 4` fires **0/123,277** while driving).
**There is no instrument to place a V99 number into for macro-ratcheting.** [EVIDENCE]

## D1.1 The symptom ↔ band mapping and how strong each link actually is

| band | kit jargon | operator's word | link | what it rests on |
|---|---|---|---|---|
| **6–9 Hz** (line 7.79–8.2 Hz) | micro-ratchet | **micro-ratcheting / stuttering** — *"not audible, only felt in the column"* | ★★★★ **the only band he himself named against a number** | **V57 verbatim: *"grinding is not 7.4 Hz, that is the ratcheting."*** He was shown the line and assigned it. **V72:** he settled the naming — TWO ratchets, MACRO and MICRO ≡ the 7.79 Hz line. ⚠ both are **single comments**; there has never been a blind A/B |
| **18–22 Hz** | grind #1 | **grinding** (creep, 2–5 mph, wheel near centre) | ★★★★ via a fix that moved with the symptom | **V62:** 18–22 Hz creep **0.124 [0.036, 0.387]**, 30–40 Hz control ≈1.0, + *"Original grinding at 2–5 mph is gone!"* Replicated by V67/V68 (**0.40 [0.27, 0.58]**). ⚠ the reverse direction has FAILED: **V84 was byte-identical to V67/V68 at every grind cell and he still reported grinding** |
| **26–31 Hz** | **"the ring"** | 🛑 **NONE — explicitly disclaimed** | ☆ | Real as an *instrument* (V81: an 11.25 s sustained 27.75 Hz limit cycle). **No operator symptom has ever been attached to it**, and the one time a band move was headlined as a fix he corrected it twice. **A stability instrument, never a symptom** |
| **32–38 Hz** | **PRE-DECLARED NEGATIVE CONTROL** | — | n/a | 🛑 it has FAILED at least once, load-bearing: on V80 the 30–49 Hz lift was 2.091 and the control moved **2.035** ⇒ the whole HF region moved |
| **40–49 Hz** | grind #2 | **vibrating** — *"makes the entire car vibrate, almost like I have a subwoofer"* | ★★★ for the OBJECT, ☆ for the BAND | Acoustic inversion puts the real centroid at **63.5 Hz [54.2, 79.6]** — **above both instruments' Nyquist** (CAN 50.00, IMU 50.51) ⇒ **40–49 Hz is the visible SKIRT of an out-of-band object.** A 40–49 Hz null is weak evidence |
| **~28 Hz lane-change** | (inside 26–31) | *"Definitely felt the grind-#2-like vibration when changing lanes"* | ★★★ | 🛑 **EXCITATION, NOT GAIN — dose-independent** (2×/1× = 1.176 [0.641, 2.320]). **Do not chase the rate lane for it** |
| **macro-ratcheting** | (no band) | **ratcheting** (≤30 mph under strong command) | ☆ **NO INSTRUMENT** | see D1.0 |

🛑 **MICRO vs MACRO COULD NOT BE SEPARATED AS TWO OBJECTS.** Splitting each build's engaged ~8 Hz
envelope at its own median gives **ONE population** on V85 and V81 (kurtosis ≈3 = a single log-normal),
and the split is **dominated by SPEED, not kind** — the HIGH half is simply the slower half on every
build. **That is a statement about the instrument, not about the car: he names two symptoms and he is
the one feeling them.** [EVIDENCE]

## D1.2 ⭐⭐ THE MOST DECISION-RELEVANT PATTERN IN THE RECORD — what V62 and V88 did

**Only two builds in sixty produced BOTH a measured band change AND an operator report of improvement.
They are the SAME LEVER CLASS.** [EVIDENCE]

| | **V62** — route `37`, 2026-07-31 | **V88** — route `73`, 2026-08-09 |
|---|---|---|
| bytes | `0x3AB76` + `0x3AC20` `sar 0xa`→`0x9` | `0x3AA96` `c5`→`fb` + `0xC6446` 512→**5244** |
| what it physically is | **×2 on the rate-DERIVATIVE lanes r24 AND r26, UNGATED** | **×2 on r24's arm, GATED on `gp-0x6806` = latActive** |
| measured | 18–22 Hz creep **0.124 [0.036, 0.387]** vs V59; control ≈1.0 | delivered command **15–22 Hz 0.549 [0.407, 0.844]** · 9–12 Hz 0.604 · **0.5–3 Hz 1.192 = NULL** |
| **HIS WORDS** | ★ ***"Original grinding at 2–5 mph is gone!"*** | ★ **grinding — HE SAYS FIXED**; *"micro-ratcheting and ratcheting … these are the main remaining issues"* |
| what it did **NOT** do | ratchet **amplified 2–3×**, gated on driver effort | `e_6-9` V88/V67 = **1.040 [0.759, 1.260]** — the tightest null in the session |
| its cost | 🛑 **UNGATED ⇒ acts in MANUAL.** V65: *"makes the entire car vibrate, almost like I have a subwoofer… happens regardless of LKAS engagement."* **Lever A is now DO-NOT-RESTORE for exactly this** | none measured — LF authority untouched |

### ⇒ THE PATTERN, as sharply as the record supports it

> 🛑🛑 **Both successes were the SAME PHYSICAL ACT — ADDING DERIVATIVE (RATE) FEEDBACK DAMPING INSIDE
> THE LOOP, which reduces HIGH-FREQUENCY content in the DELIVERED COMMAND. Both fixed GRINDING. NEITHER
> touched micro-ratcheting or ratcheting, and the record now says structurally why.** [EVIDENCE]

```
 driver / LKAS                                      the two successes act HERE
      │                                                        │
      ▼                                                        ▼
  torque sensor ──► dtorque (backward difference) ──► r24 ─── ×gain ──┐
                                                                      ├──► 11-slot aggregator
  motor rate ─────► d/dt ──────────────────────────► r26 ─── ×gain ──┘        │
                                                                              ▼
   ⭐ r24/r26 are RATE FEEDBACK *INSIDE* the loop; gp-0x6b98 is the loop's OUTPUT
   ⇒ MORE derivative feedback = MORE damping = LESS HF everywhere in the loop
      (this REFUTED the orchestrator's pre-flight prediction that V88 would RAISE 15-22 Hz)
```

**And V88 supplied the out-of-sample test that closes the class:**
- observational elasticity `d(log ratchet)/d(log 15–22 Hz cmd)` = **+1.082 [+0.814, +1.329]**
- ⇒ predicted ratchet ratio from V88's 0.549× cut: **0.523 [0.451, 0.614]** — plainly visible if real
- ⇒ **measured: 1.040 [0.759, 1.260]. THE INTERVALS DO NOT OVERLAP.** [EVIDENCE]
- inverted causal elasticity **−0.065 [−0.385, +0.460]** = consistent with **ZERO**, upper bound below
  the observational lower bound.
- ⊕ the **32–38 Hz negative control also responds** (+0.664 [+0.441, +0.827]) ⇒ the correlation was
  operating-point covariation, not a lever.

**Operator's own summary sentence, on record:** ***"Cutting high-frequency content out of the delivered
steering command is now a measured fix for the grinding and a measured NON-fix for the ratcheting."***

🛑 **⇒ V99 MUST NOT BE ANOTHER COMMAND-HF-REDUCTION BUILD.** That class is banked for grinding (V88's
Lever B is on the car) and measured-dead for the two symptoms he now names. On the most optimistic
elasticity still consistent with V88, halving the ratchet needs the 15–22 Hz command at **0.22× of V87 —
a further 2.5× cut on top of V88** — which reaches into the range where 0.5–3 Hz authority is at risk.
**On the central estimate, no achievable cut moves it at all.**

⊕ **And the rail closes it independently:** `0xC6446` at V88's 5244 already sits at **1.50× hot-end
margin** against the ±8192 clamp; 2.5× is *at* the rail, 3.0× **pins** (relay class). ⭐ **That is the
MECHANISM behind the recorded *"2× ≈ OPTIMUM, not a point on a ramp"* — the RAIL, not the tuning.**

## D1.3 THE FULL LADDER, V38 → V98, HIS WORDS

🛑 **THREE INCOMPATIBLE NUMBER FAMILIES EXIST. Never rank across them.** [EVIDENCE]

| family | what | builds | comparable to |
|---|---|---|---|
| **A — the modern ladder** | NFFT 256 / hop 128, p99 analytic band envelope, `blk` (~10.2 s) episode units, creep **< 10 km/h** | V67, V68, V76, V80, V81, V83a, V84, V85 | ✅ each other only |
| **B — the `e_18-22` yardstick** | same estimator, creep **< 20 km/h**, different route pool | V58–V72 | ⚠ each other only |
| **C — pre-statistical** | mean-Welch engaged/disengaged ratios, **no CI, no null**, engagement/motion collinear | V38 → V57 | 🛑 **nothing** |

**The size of the error:** at a matched cut V67 reads **110.7** (family B) vs **654.3** (family A). The
famous *"V67/V68 is the best grind #1 in the kit, `e_18-22` = 109"* is a `<20 km/h` figure; against the
modern creep stratum V67 reads **654.3 — worse than V81's 69.4.**

| build | route | HIS WORDS (verbatim) |
|---|---|---|
| V38 | — | *"hard turns appear authority-limited by a feedback loop"* — 🛑 **the cause** |
| V39 | — | *"fixed neither symptom"* |
| V40 | — | ☠ **BRICK** — EPS lamp, no power steering |
| V41 | — | *"boots and drives cleanly, fixed neither"* |
| V42 | — | *"FIXED THE HARD-TURN RATCHET"* ⚠ **attribution VOID** |
| V43 / V45 / V46 / V48A | — | *"fixed neither symptom"* / *"no noticeable change"* |
| V48B | — | ☠ **BRICK** — wheel spun full-authority at startup |
| V52C | — | *"did not fix the vibration; clearly changed manual feel"* 🛑 **no rlog exists** |
| V53 | `1a` | *"the steer-to-zero feature worked"* |
| V54 | `1b` | *"this drive exhibits the vibration issue"* |
| V55 | `1c` | *"demonstrated the vibration in a parking lot"* |
| V56 | `24` | *"damping removed and a new few-Hz resonance"* 🛑 the *"new 8.69 Hz"* is **wheel order 1, a tyre** |
| **V57** | `28`,`29` | ★★★★ ***"grinding is not 7.4 Hz, that is the ratcheting."*** — **the mapping's only anchor** |
| V60 | — | *"It did not fix the vibration issue."* |
| V61 | `31` | *"significantly worse"*; LKAS **off**: *"grinding newly present"* |
| **V62** | `37` | ★ ***"Original grinding at 2–5 mph is gone!"*** |
| V64 | `35` | *"The vibration/grinding at low speeds is not fixed."* |
| V65 | `3a`,`3b` | *"makes the entire car vibrate, almost like I have a subwoofer… happens regardless of LKAS engagement"* |
| V67 | `47` | *"Grind #2 seems mostly gone… but a higher-speed grind #2 on lane changes/turns, only LKAS-engaged"* |
| V68 | `4e` | *"Definitely felt the grind-#2-like vibration when changing lanes"* |
| V69 | `4f` | — |
| V70 | `50` | *"stiffer"* (mechanism REFUTED bus-side) |
| V71b | `54` | *"I definitely experienced grind #1."* |
| V71c | `58` | *"attenuated but still present"*; ranked V71c > V71b |
| V72 | `59` | 🛑 **settled the naming: MACRO vs MICRO ≡ the 7.79 Hz line**, *"not audible, only felt in the column"* |
| V73 | `5a` | *"grind #1 audible, micro-ratchet not"* |
| V74 | `5d`,`61` | ☠ **HARD FAULT**, latched loss of assist |
| V75 | `5e` | ⭐ *"got rid of the audible grind #1 and **strongly attenuated the micro-ratcheting**… **then a hard fault**, lost power steering"* ☠ |
| V76 | `65` | *"There is still grind #1 and micro-ratcheting at creep."* |
| **V80** | `66` | 🛑 *"loud, strong, felt through the whole car, ~90% of LKAS-engaged time, **noticeable vehicle instability**"* — **WORST GRINDING EVER, and NO FAULT** ⇒ a *stability* failure |
| V81 | `67` | *"all grinding stopped the instant LKAS disengaged; hand mass did not damp it; **highway was worst**; manual steering much heavier when engaged, even turning WITH the command"* |
| **V83a** | `68` | 🛑 ***"Feels just like V38, like we have made no progress since then."*** — and it was a **byte fact** |
| V84 | `6d` | *"grind #1 barely got better, might just be placebo… 2 instances of grind #2… **Both microratcheting and ratcheting were very obviously present**"* → 🛑 ***"None of these have been fully fixed in V84."*** |
| V85 | `6e` | grinding *"a little better"* · micro-ratcheting *"barely, perceptibly better (somewhat unsure)"* · 🛑 **ratcheting STILL UNFIXED** · *"I did not experience any grind #2"* — 🛑 **an absence of complaint is NOT a cure** |
| V86 | `6f` | *"maybe a smidge better, if at all"*; **ratcheting definitely perceptible** |
| V86B | `70` | *"still present, dampened I think"*; **ratcheting definitely perceptible**; + *"extra dampening on LKAS and in general at slow speed"* — **the predicted heaviness cost CONFIRMED AS FELT** |
| V87 | `71` | grinding, micro-ratcheting AND ratcheting **all present** — the **PREDICTED** result (deliberate rebase to V38) |
| **V88** | `73` | ★ **grinding FIXED**; *"micro-ratcheting and ratcheting … the main remaining issues"* |
| V89 | `75`,`76` | 🛑 ***"fixed nothing, still only as good as V88."*** |
| V90 | `77` | *"grind #1 still exists · micro-ratcheting still exists · grind #2 can be felt on the highway-speed curves or lane changes"* — **the CONTROL condition** (byte-identical to V89) |
| V91 / V92 | `78`,`79` | ⚠ **NO OPERATOR SYMPTOM REPORT IS ON RECORD FOR EITHER.** Both fault-free, both scored as instruments. **A gap — flagged, not invented** |
| **V94** | `7d` | ☠ ***"Made the stuttering and grinding worse, by a lot. So much so that it vibrated the entire car, and I decided it was not safe to drive."*** — **the only build he has ever aborted** |
| V96 | `7e`,`7f` | ⚠ **NO OPERATOR SYMPTOM REPORT ON RECORD.** Instrument build, both fault-free |
| **V97** | `80` | 🛑 ***"I did not feel any difference in grinding or stuttering (micro-ratcheting) behavior at all on V97, so I stopped the drive."*** |
| **V98** | **`81`** | ✅ **FLEW, fault-free.** Identity proven single-frame: `0x14A` byte7[7:6] == 2, duty **1.000000 over 17,983 frames.** **65.9 s engaged in 3 EPISODES**, 3 segments; **seg1/seg2 are a clean engaged / LKAS-off MATCHED PAIR.** ⚠ **A ZERO-CAL INSTRUMENT BUILD — it changed no calibration byte, so no symptom verdict is expected or claimable from it.** Its deliverable is the comparator (see D3.A-bis) |

### 🛑🛑 The one-line reading of the ladder
**SIXTY BUILDS. Micro-ratcheting/ratcheting have moved in the improving direction EXACTLY ONCE — V75,
which then HARD-FAULTED, and whose lever (`0xCBE74` ×1.5 + `0xC407E` = 850) has since been measured
INERT at that dose (0.99 [0.91, 1.26] vs a pre-registered 1.50).** Everything else is *"still present"*,
*"fixed nothing"*, or worse. [EVIDENCE]

⭐ **V75 is therefore the single most under-exploited data point in the arc** — the only operator report
of micro-ratcheting attenuation in the whole record. Its confound is total (V74/V75 changed 64 runs;
`0xC407E` = 850 was the fault, the friction row cannot be pinned), and the ×1.5 dose has since flown
clean-and-inert on V91/V92 with `0xC407E` = 511. ⚠ **Do NOT read this as "re-fly V75"** — the dose IS
falsified at ×1.5 and ×1.5 is 94 % of the lever's entire range. Read it as: *the one time he felt the
micro-ratchet improve, something in a 64-run delta did it, and the record has never isolated which.*

## D1.3b ⭐⭐ THE ONE THING THE PARTITION LEAVES STANDING — and it is NOT what "the damper is closed" sounds like

**Two independent positives point at the SAME lever, and they are the only two the micro-ratchet has
ever had.** [EVIDENCE for both; **BELIEF** that they are the same effect]

| | what happened |
|---|---|
| **V75** (route `5e`, `k` = 1.5798) | ⭐ ***"got rid of the audible grind #1 and STRONGLY ATTENUATED THE MICRO-RATCHETING… then a hard fault."*** **The ONLY operator report of micro-ratcheting improving in sixty builds.** Its own cave measured the damper live: engaged level census **L0 (dead) 56.8 % · L1 25.3 % · L2 9.3 % · L3 8.6 % · L4 (≥448) 0.000 %** ⇒ **the damper was ACTIVE on 43.2 % of engaged frames and never saturated** |
| **V80** (route `66`, `k` = 4.16) | ⭐ **6–9 Hz = 0.418 [0.33, 0.61]** vs V76 — 🛑 **the ONLY point on the four-build `k` ladder that falls OUTSIDE its own split-half null of [0.66, 1.45].** V74 (`k`=0.58) 0.818 and V75 (`k`=1.58) 0.821 are both inside. *"V80 bought a real ratchet gain and paid for it with the HF floor"* |

**Why this is not contradicted by "the base-assist damper is CLOSED":** that closure is computed on
**V88's STOCK damper surface**, where `ch₀` is exactly zero on **95.91 %** of engaged frames. **V75's
damper was not stock** — it opened **BOTH** dead zones (FactorC `Y[0]` 0→566 and FactorE `X[0]` 60→12),
which is why its own probe reads **43.2 % active**. ⇒ 🛑 **the closure is a statement about HONDA'S
SURFACE — which is what V98 carries — not about the mechanism.** Byte proof in **§D1.3c** below.

### 🛑 The precise, defensible form of the closure
> **The damper is closed as a lever ON HONDA'S STOCK SURFACE, which is what the car currently carries.
> It has been ARMED in the micro regime on three FLOWN builds (V75, V76, V80) with three different
> outcomes, and the shape variable that separates them — `FactorE X[1]`, where the ramp saturates — has
> never been isolated.** And 🛑 **the count field is never read** — going beyond 4 points is a **CODE
> edit to the always-on base-assist damper**, the class that bricked V24/V27/V48B.

### ⚠ And the honest caveats, which are serious
- 🛑 **V75's report is TOTALLY CONFOUNDED.** V73→V74 alone is **64 differing runs** (13 friction sites +
  51 others); V75 adds FactorC `Y[0]`=566 and FactorE `X[1]`=200 on top; `0xC407E` = 850 was on board and
  is the fault mechanism. **The record has never isolated which run produced the attenuation.**
- 🛑 **V80's route has an exposure warning on EVERY band** in the ladder's own gate table (engaged
  fraction **32.9 %**), and *"V80's creep numbers are an EXPOSURE ARTEFACT — the driver was not turning
  the wheel"* is an explicit retraction in `STATE.md`. ⚠ Also unresolved: **whether V80's near-zero creep
  angle rate is itself an EFFECT of a 412-count-at-all-speeds damper making the wheel feel sticky** — in
  which case the 0.418 is partly the driver, not the firmware.
- ⊕ The record's own note: *"something switches on between `k` = 1.58 and 4.16 that costs 2× broadband HF
  plus a limit cycle. **Where in that gap it switches on is UNMEASURED**"* — and bracketing it was
  **DEPRIORITISED**, on grounds (the ring's `k` axis falsified, grind #1 inert to `k`) that **do not
  touch the 6–9 Hz result.**

### 🛑🛑 D1.3c — A STANDING MEMORY IS REFUTED BY THE IMAGES. READ THIS BEFORE CITING "THE DAMPER IS CLOSED".

`memory/accord-base-assist-damper-cannot-reach-the-micro-regime.md` (★★ in `MEMORY.md`) asserts
*"Neither prior test ever had BOTH dead zones open (V86B armed FactorC only). FactorE `X[0]` is **60
counts**, not 12."* **Four of its claims are FALSE.**

**Method [EVIDENCE]:** raw Python LE read of the plain images, records dereferenced through their own
pointer arrays (`FactorC 0xC9E9C`, `FactorE 0xC9F84`, `ceiling 0xC77A0`), **mode 26 = ENGAGED**, `Y` at
`base + 2 + 2n`, rate scale **4.7121 ct/(°/s)** (= 1/0.21217, the memory's own figure).
✅ **POSITIVE CONTROL — the reconstruction reproduces the RECORDED surfaces exactly:** V75 at rate 20 ct
→ **12** (record 12) · V80 at 20 ct → **82.9** (record 82) · V75 plateau **297** (record 297) · V80
plateau **495** (record 495).

**FactorE mode 26, read from every image:**
```
STOCK  X=[60, 400,2500,4000]  Y=[  0,140,539,927]   ramp saturates  84.9 deg/s
V75    X=[12, 200,2500,4000]  Y=[  0,539,539,927]   ramp saturates  42.4 deg/s   X[0]=12  FLOWN (r5e)
V76    X=[ 0, 119,2500,4000]  Y=[  0,300,539,927]   ramp saturates  25.3 deg/s   X[0]=0   FLOWN (r65)
V78    X=[ 0, 119,2500,4000]  Y=[  0,449,539,927]   ramp saturates  25.3 deg/s   built, never flown
V79    X=[ 0, 119,2500,4000]  Y=[  0,897,912,927]   ramp saturates  25.3 deg/s   built, never flown
V80    X=[ 0, 119,2500,4000]  Y=[  0,897,912,927]   ramp saturates  25.3 deg/s   X[0]=0   FLOWN (r66)
V86b   X=[60, 400,2500,4000]  Y=[  0,140,539,927]   (stock)                      FactorC only
V98    X=[60, 400,2500,4000]  Y=[  0,140,539,927]   (stock)  = ON THE CAR
```
**FactorC m26 `Y[0]`** = **566** on V75/V76/V78/V79/V80 · 908 on V86b · **0** on STOCK/V88/V98.

**The delivered surface `ch₀ = (FactorC(creep) × FactorE(rate)) >> 10`, mode 26, counts:**
```
rate deg/s :     1      2      3      5      8     10     13  |    20     30     42
STOCK      :     0      0      0      0      0      0      0  |     0      0      0
V98 (car)  :     0      0      0      0      0      0      0  |     0      0      0
V86b       :     0      0      0      0      0      0      0  |    12     29     49
V75        :     0      0      2     18     40     55     77  |   129    203    294
V76        :     6     12     19     33     52     65     84  |   130    166    169
V78        :     9     18     28     49     79     97    127  |   195    248    249
V79 / V80  :    20     37     58     99    158    195    253  |   391    495    495
                <------- the operator's MICRO regime, 1-13 deg/s ------->
```

| the memory's claim | verdict |
|---|---|
| *"Neither prior test ever had BOTH dead zones open"* | ❌ **FALSE — FIVE builds had both open; THREE FLEW: V75, V76, V80** |
| *"FactorE `X[0]` is 60 counts, not 12; 12 was a WITHDRAWN variant"* | ❌ **FALSE — V75 FLEW with `X[0]` = 12; V76/V78/V79/V80 carry `X[0]` = 0** |
| *"Reaching 25 % authority at 10 °/s is UNREACHABLE by moving X"* | ❌ **FALSE — V79/V80 deliver 195 ct at 10 °/s = 38 % of the 512 ceiling**, via `X[1]`→119 and `Y[1]`→897 |
| *"It requires raising `Y[0]` off zero = a step at zero rate"* | ❌ **FALSE — NO flown build ever raised FactorE `Y[0]` off zero.** It is 0 on every one. V80's relay came from a **STEEP RAMP SATURATING AT 25.3 °/s** |

**What IS still true and matters:** `ch₀` really is exactly zero on **95.91 %** of engaged frames and
**100 %** of the micro regime — **on the STOCK surface, which is what V98 carries.** V86B really did arm
FactorC only. The V80 move really is *"worst grinding ever."* ⇒ **the memory's OBSERVATION is right; its
GENERALISATION to "never tried / cannot be done" is wrong.**

### ⭐⭐ THE CORRECTED MECHANISM — the relay-ness is set by `X[1]`, NOT by `Y[0]`

| build | `X[1]` | ramp saturates | relay index `N(50)/N(500)` | operator |
|---|---|---|---|---|
| **V75** | 200 ct | **42.4 °/s** | **1.45** | ⭐ *"strongly attenuated the micro-ratcheting"* (then an unrelated `0xC407E`=850 fault) |
| V76 | 119 ct | 25.3 °/s | (`k` 1.39) | *"still grind #1 and micro-ratcheting at creep"* |
| **V80** | 119 ct | 25.3 °/s | **3.27** | ☠ *"worst grinding ever"* — **and 6–9 Hz 0.418 [0.33, 0.61], the only `k`-ladder point outside its null** |

🛑 **Note the NON-MONOTONICITY, which is the real finding: V76 delivered MORE damping below 3 °/s than
V75 (6/12/19 vs 0/0/2) and the operator said micro-ratcheting was still there; V75 delivered LESS at the
bottom and he said it was strongly attenuated.** The variable that separates them is **not the amount** —
it is the **SHAPE**: V75 alone has a **small rate DEADBAND at the bottom (`X[0]` = 12 ct = 2.55 °/s)
followed by a LONG LINEAR RAMP to 42 °/s** — **the most viscous, least relay-like damper ever flown on
this car**, and the only one with a positive operator report on the target symptom.

⇒ **[BELIEF] This is the strongest thread the partition leaves standing, and it is stated as a thread,
NOT a recommendation.** It carries two positives (V75's operator report, V80's 0.418) and two serious
negatives (V80's grinding, V75's fault), **all four confounded**, and going beyond 4 points is a
**CODE edit to the always-on base-assist damper** (the count field is never read) — the class that
bricked V24/V27/V48B.

📋 **ACTION FOR CLOSE-OUT: `memory/accord-base-assist-damper-cannot-reach-the-micro-regime.md` must be
corrected.** It is a `reference_*` fact of record and it currently forecloses a lever class with three
flights behind it.

## D1.4 The regime statement that reframes every measurement in the file

Operator, 2026-08-12: ***"Steering override is how I get the steering into such a scenario where
grinding and micro ratcheting can be observed."*** and ***"literally every bad symptom is LKAS engaged
only."***

Scored in **his** regime (override vs manual-hands-on, grip matched on BOTH arms), 6–9 Hz column-torque
envelope:
```
OVR / MAN-ON  =  1.43  1.65  1.74  1.93  2.22  2.25  2.35  2.38  2.55  2.90
                 10 of 10 routes, 9 builds, every one above 1.4,  median ~2.2x
```
⇒ **his report is CONFIRMED by the amplitude instrument in his own regime**; ~55 % of the 6–9 Hz energy
he feels is engagement-attributable. An orchestrator claim that *"~80 % of what you feel isn't gated on
LKAS"* was **RETRACTED**. **An LKAS-gated lever — the V62/V88 class — is fully back on the table.**
[EVIDENCE]

🛑 **BUT THE KIT'S INSTRUMENT WAS POINTED AWAY FROM THE SYMPTOM FOR THE WHOLE ARC.** The hands-off mask
is `steeringPressed` = `|STEER_TORQUE_SENSOR| > 1200` — a threshold on the **numerator of `Re(Z)`** — and
**override is `steeringPressed == True` by definition.** Exposure followed: **7121.6 s engaged hands-off
against 994.9 s engaged hands-on.** ⇒ **every `Re(Z)` number ever produced excluded the symptom regime.**

### ⚠ AN OPEN CONTRADICTION V99'S SCORING MUST NOT PAPER OVER
Two well-powered results point in opposite directions about the driver's hand:

| result | statement |
|---|---|
| 2026-08-04, pooled 4 routes / 4 builds, both arms hands-off | ratchet events **73/88 = 83.0 % engaged hands-off vs 0/118 manual hands-off**, Fisher **p = 3.8e-41**; rate **BUILD-INDEPENDENT** (80/81/79/94 %) ⇒ 🛑 **NO BUILD IN THIS KIT HAS EVER MOVED THE RATCHET.** ★ **a hand on the wheel SUPPRESSES it while engaged** — V59 94 %→14 %, V69 81 %→37 % |
| 2026-08-12, 10 routes / 9 builds, both arms hands-on | **override / manual-hands-on = 2.2× median** at 6–9 Hz |
| 235-block corpus | **driver GRIP damps the mode**: `log hands` −0.655 vs the control's −0.266, **CIs disjoint** |

**Both are true and they are not in conflict arithmetically** — grip damps in absolute terms, while
engagement multiplies by ~2.2–2.8× *within* whatever grip state you are in. **But they ARE in conflict
operationally:** the instrument's largest absolute 6–9 Hz signal is in **engaged hands-off**, and the
operator says he provokes the symptom in **engaged hands-ON override.** [EVIDENCE for both]
⇒ 🛑 **V99's readout must work in the OVERRIDE regime, and V99 must not be scored on an
engaged-hands-off statistic just because that is where the corpus is deepest.**
⇒ 🛑 **Override does not support the 5.12 s band estimator at all**: 5,013 contiguous override runs make
up the 994.9 s — median run **0.02 s**, p90 **0.55 s**, and **only SEVEN runs corpus-wide reach 5.12 s.**

---
---

# D3 — THE FALSIFIED / INERT / UNTRIED PARTITION

> 🛑 **`FALSIFIED` ≠ `INERT-BY-MODE` ≠ `INERT-IN-FORCE` ≠ `UNINTERPRETABLE` ≠ `NEVER-TRIED`, and
> *"the same lever pushed the other way"* is a DIFFERENT CLAIM from *"a new lever."***

## D3.A ☠ FALSIFIED — flashed, proven in force, and demonstrably did not fix its target (or moved it the wrong way)

| lever | build / route | the statistic that killed it |
|---|---|---|
| `0xC644A` 1024→64 (dirty-derivative pole) | V43 | null; lane later **ELIMINATED** by V56 |
| `0xC6450` 1024→32 | V46 | null. 🛑 **re-proposed as "new" by two agents in one session — the founding incident of `BUILD-LINEAGE.md`** |
| **`0xC6444` 512→3072** (r26 engaged arm) | **V71c**, route `58` | grind #1 `e_18-22` **223 vs V67/V68's 109 — excluded HIGHER (P = 0.0215)**; grind #2 returned (7 bursts @44.31 Hz, p99 = 12.2× any non-bursting build); **ratchet 8,521 ct p-p = the corpus RECORD.** 🛑 the memory calling it *"UNTESTED: a candidate"* is **CORRECTED — FALSIFIED AND REVERSED.** The 6× r26 cut is **LOAD-BEARING** in Lever B |
| **`0xC40D4` 573→286** (command-branch EMA) | **V86**, route `6f` | pre-registered [0.797, 0.875]; **measured `f(V86)/f(V85)` = 1.001 [0.976, 1.060] — DISJOINT and well-powered** (a faithful surrogate resolves ×0.94 against a requested ×0.843 = **2.6× margin**). ⇒ 🛑 **the LINEAR-LOOP hypothesis is DEAD**; the ~8 Hz ratcheting is a lightly-damped **RESONANCE, Q ≈ 14–29** |
| **`0xC40BC` 600→6000** (Coulomb-relay normaliser) | **V85**, route `6e` | the lever **DELIVERED** (relay saturation 39.5 %→11.1 %, engaged 7.21×) — but engaged/manual 6–9 Hz went **2.89× [2.14, 3.92] → 6.58× [3.19, 13.14]**, band contrast **+0.682 [+0.213, +1.166]** ⇒ 🛑 **RAISING IT MADE THE RATCHET 2.3× WORSE.** The standing *"FREEZE at 6000"* is **CONTRADICTED**; the car has been back at 600 since V87 and that is the better value |
| **`0xC40D2` 102→204** (K1, modelled Coulomb friction) | **V89**, routes `75`/`76` | **0.947 [0.827, 0.979]** inside the same-build placebo band **[0.900, 1.111]** = 0.92σ, **FLAT.** Operator *"fixed nothing."* 🛑 the naive block-bootstrap CI **EXCLUDED 1.00** and would have shipped as a 5 % fix — the placebo control earned its keep on first use. ⚠ **8 bytes still on the car, still doing nothing measured.** ⭐ **SHARPENED BY V98'S COMPARATOR — see D3.A-bis below** |

### ⭐ D3.A-bis — V98'S COMPARATOR SHARPENS THE `0xC40D2` KILL, AND REFUTES A STANDING `STATE.md` BELIEF

**V98's flown comparator (orchestrator-verified from the raw wire bits):**
`b5` = `|gp-0x6bfa| ≥ |gp-0x374c>>4|` duty **0.0000 over 6,591 engaged frames** ⇒ **REQUEST is the
smallest arm.** `b6` = `|gp-0x6bfe| ≥ |gp-0x374c>>4|` duty **0.4235** ⇒ **MODEL and ACTUAL are
COMPARABLE.**

🛑🛑 **THIS REFUTES `STATE.md`'s standing structural BELIEF** — *"the arms may be wildly unequal, so
whichever you move, the residual barely notices … the first account explaining two nulls with one
mechanism."* **That account is DEAD for the MODEL/ACTUAL pair** (it survives only for REQUEST, which
really is tiny). ⇒ **V89's and V97's nulls no longer have a common structural excuse and must each be
explained on their own terms.**

**⚠ BUT THE INFERENCE MUST BE TAKEN AT THE RIGHT LEVEL OF THE TREE, and I am flagging a disagreement
with the phrasing *"K1 was correctly aimed"* rather than adopting it:**

| level | claim | evidence |
|---|---|---|
| **ARM** — is MODEL load-bearing? | ✅ **YES** — MODEL ≈ ACTUAL | **NEW: V98's `b6` = 0.4235** |
| **SUB-TERM** — is K1's friction term inside MODEL live *in the micro regime*? | 🛑 **NO** — the term is `sign(motor rate)`-gated and `\|friction\| ≥ 0.0625` on **0.000** of frames below 1 °/s and **0.009** of the 1–13 °/s micro regime (782 engaged s) | **OLD: V89's own probe** |

⇒ **The precise kill is: K1 was aimed at a LIVE ARM but at a NEGLIGIBLE SUB-TERM WITHIN IT, in the very
regime the operator names.** That is a **strong, specific kill on K1** — stronger than an ambiguous one,
exactly as the orchestrator argued — **but it does NOT generalise to "the MODEL arm is a dead lever
class."** A *different* term inside MODEL, one that is not rate-sign-gated, would sit on a
**demonstrably load-bearing arm.** [EVIDENCE at both levels; the two-level reading is mine]

⭐ **AND THE SAME RESULT UPGRADES `0xC63AC`:** V97's pole acts on **ACTUAL**, and `b6` = 0.4235 proves
ACTUAL is **comparable to MODEL, i.e. load-bearing.** ⇒ **V97's null cannot be blamed on a small arm
either. It sits on a load-bearing arm and has NEVER been scored** — which is precisely why it belongs in
the TRIED-BUT-UNSCOREABLE bucket and not in this table.
| **`0xCBE74` ×1.5 ENGAGED** (m26/m27) | **V91/V92**, routes `78`/`79` | engaged stratified ratio **0.99 [0.91, 1.26]** vs pre-registered **1.50**; **MANUAL control holds at 1.009**; duty flat 0.167/0.161/0.165 vs a needed 0.204. **A null on the LEVER, not the flash** (identity proven single-frame; the image carries the row). ⚠ **RULE 7 STILL OPEN** — Y is nonzero at all 3 knots ⇒ *the record READ may not be the record WRITTEN.* 🛑 **×1.5 is 94 % of the lever's entire range — int32 wraparound at ×1.6005. NO LARGER DOSE EXISTS** |
| **`0xCBE74` ×0.25 ENGAGED** — *the same lever pushed DOWN* | **V94**, route `7d` | ☠ **THE ONLY BUILD THE OPERATOR HAS EVER ABORTED.** Measured afterwards on two independent drives, ω-partialled vs a shuffled control: the **delivered** lane sits at **+137°/+139° vs WHEEL rate at 6–9 Hz**, `\|cos\|` = 0.73 ⇒ **+518/+565 counts of POSITIVE `Re(Z)` — a REAL 6–9 Hz DAMPER, and V94 removed 6/6ths of it.** Motor acceleration **3–7× up above 9 Hz**; 18–31 Hz coherence the highest in the corpus. ⇒ **DOWN is falsified WITH A MEASURED SIGN** |
| the **base-assist damper dose `k`** (FactorC/FactorE) | V74/V75/V76/V78/V79/**V80**/V83a | **V80 at `k` = 4.16 = "worst grinding ever"** — 2.09× broadband HF lift + a **30 s sustained 27.4 Hz limit cycle**, and **no fault** ⇒ a *stability* failure. Grind #1 is **INERT to `k` across 0.58 → 4.16** (every point inside its own [0.63, 1.60] null). 6–9 Hz improves **only** at `k` = 4.16 (0.418 [0.33, 0.61]) — the same point that carries the HF penalty. **There is NO free-benefit bracket** |
| `0xC6AF0` mute of `gp-0x6ad4` | V56, route `24` | null **and cost damping**. 🛑 ⚠ **BAND-SCOPED: scored on P[15–26 Hz], NEVER on 6–9 Hz**, and route `24` is not on disk. **The record carries the elimination as if it were general. It is not.** `0xC6AFC`/`0xC6AFE` = 32768 on all 30 other builds ⇒ the corpus cannot test it either |
| `0xD2006` 102→43 | V60 | *"It did not fix the vibration issue."* |
| 12 Hz EMA on 19 carriers | V52C | *"did not fix the vibration; clearly changed manual feel"* 🛑 **no rlog exists** |
| `0xC6194` **as a slew limiter, if armed** | (never flown) | 🛑 **arming it goes the WRONG way** — see D3.B |

## D3.B ⏸ INERT — the byte was on the car but the lever NEVER ACTED. 🛑 These are NOT falsified.

### B1 — INERT BY MODE (the table you edited is not the table the car reads). RULE 6 / RULE 7.
- **V44 / V47 / V72** damping builds wrote **modes 10/11**; the car is **TVCA4** — modes **24/25 manual,
  26/27 ENGAGED.** V72's own probe: a rung that should have fired **100 %** fired **0 of 87,940**
  (including 0 of 34,275 above 35 km/h). ⇒ *"damping is null"* on all three is **UNINTERPRETABLE, not
  falsified.** [EVIDENCE]
  🛑 **This retires the standing "V47 reported *marginally quieter at 5 mph* and was never scored against
  the RATCHET" note as a lead** — V47's lever was inert by table selection, so the whisper cannot be
  attributed to the damper. (And the damper has since been closed on arithmetic — see B3.)
- **V69 / V70's r24 dose ladder wrote mode-10 `gain_B` ⇒ byte-stock ⇒ THE LADDER NEVER EXISTED.** After
  RULE 7 the family-B ladder collapses to **three** real points: 0× (V61, much worse) → 1× (stock) →
  2× (V62/V65). [EVIDENCE]
- **V73's `0xCBE74` ×1.5 was mode 10 only** — a *disengaged* column ⇒ its clean flight says **nothing**
  about that lever, and the "V73 flew clean at `0xC407E` = 850" control that was meant to exonerate the
  clamp instead **implicates the friction row.**

### B2 — INERT BY GATE / BY STATE (the enable never armed)
- **V64** — the null is **on the GATE**, not the hypothesis. It was read as a result for weeks.
- **V67 / V68 (`gp-0x67df`)** — the cell has **NEVER been non-zero on ANY build**: 0/186,321 (V67),
  0/53,991 (V68) ⇒ its writer *and* its enable are open questions, not a result.
- **`0x454FE`** (V42's macro-ratchet fix) — `gp-0x67fa`'s reachable set is effectively **{11} alone**;
  state 5 is structurally dead, state 10 measured 0.0000 %, state 4 measured **0/123,277** while driving.
  ⇒ **MEASURED INERT.** Keep the byte (silently lost three times, costs nothing) but 🛑 **no build may be
  justified on it.** ⚠ **This SUPERSEDES the 2026-08-04 note calling it *"a genuinely UNTESTED lever for
  the ratchet."***

### B3 — INERT IN FORCE (it executed; its output is arithmetically zero or negligible where the symptom lives)
**These are the strongest kills in the file — structure, not nulls.**

| lever | why it cannot act |
|---|---|
| **base-assist damper — ⚠ ON THE STOCK SURFACE ONLY, see §D1.3c** | `ch₀ = clamp((FactorC(speed) × FactorE(rate)) >> 10, ±ceiling)` — a **PRODUCT of two dead zones** (FactorC `Y[0]`=0 below **34.97 km/h**, FactorE `Y[0]`=0 below **12.7 °/s**) ⇒ **exactly ZERO on 95.91 % of engaged frames, 100 % of the micro-ratcheting regime, 100 % of the ratcheting regime at parking-lot speed** — **on V88/V98's stock surface, which is what is on the car.** 🛑🛑 **BUT THE FURTHER CLAIM *"and it cannot be opened / neither test ever had both zones open"* IS REFUTED FROM THE IMAGES — V75, V76 and V80 all FLEW with both zones open. See §D1.3c. Do not cite the sizing argument; it is wrong on three counts.** |
| **`0xC63A0` 1024→2048** | INERT with **no mechanism** — `ch₀` is zero on 98.8 % of engaged frames. Flew **four times** (V72/V73/V76g/V81) and measured inert. ⊕ **V84's own revert of it was therefore also inert** |
| **FactorD** | FactorC multiplies in **FIRST** with `Y[0]` = 0 below 34.97 km/h, in **all four** of this car's modes. **Zero × anything = 0.** Confirmed three independent ways. 🛑 **This also REFUTES *"FactorD is the only frequency-selective lever"* — THIS FIRMWARE HAS NONE** |
| **`0xC6194`** (LKAS slew limiter) | **REAL and calibrated** — 3 ct/tick = 1.37 s full scale, *exactly the shape the operator described* — but its input partition `0xC4118` is **all-1 ⇒ 100 % of the request bypasses it.** 🛑 The record's *"output ×0"* reason is **WRONG** (that is `0xC6196`). **Arming it goes the wrong way** |
| **`0xC64B8`** | at this car's mode **both arms deliver 0 everywhere the branch could fire** (all four curve records clamp to `Y[last]` = 0 above X = 80/112, below the gate's 113). **Stock and V37 are BIT-IDENTICAL here. V37 removed nothing.** ⇒ do not re-propose |
| **`0xC6B12`** (PID Ki) | at 6–10 km/h the P term alone (16,000 at e = 2000) exceeds the anti-windup bound (7,264) ⇒ **the integrator is pinned** |
| **`0xC6372` / `0xC636E`** | a **DEAD BRANCH** — `tp+0x7498 = tp+0x7499 = 1`, byte-verified on stock and every build |
| **return-to-centre + detent** | `gp-0x6b62 ≠ 0` and the `gp-0x6bda` gate both **0.0000 over 75,227 engaged frames**, with an **855 s sustained (0,0) run.** 🛑 Re-identified 2026-08-12: it is a **RACK END-STOP CUSHION** — arms on `\|gp-0x6b98\| > 4096` **AND** motor rate `< 200` (a STALL detector), splits by sign into left/right stop enums, **no angle term anywhere**, gate needs `\|gp-0x6bf0\| > 8878`. **~99.3 % dead in MANUAL too** ⇒ its absence **cannot** explain the engaged/manual difference |
| **`0xC6B66` / `0xC6B80`** (13-point LERP) | axis is **ABSOLUTE steering angle**, not a tracking error (the relation holds in the MANUAL arm, where a tracking error is not even defined), and **88.6 % of engaged driving sits in its flat first segment** ⇒ a near-constant **0.878× broadband trim** |
| **`gp-0x6b4e`** | provably **≡ 0** |
| **`0xC520C`** (governor ceiling) | `gp-0x6ac0` scale = 4.7121 ct per °/s ⇒ first knot **222.8 °/s**; measured returns max **528 ct against a 1050 knot — 0.00 %** reach it |
| **`gp-0x6afe` / `gp-0x6b4e`, `FUN_0002a93a`** | always-zero cells / **DEAD CODE, zero callers** |

---

## ⏳ THE FOURTH CATEGORY — **TRIED-BUT-UNSCOREABLE**
*(indexed as D3.B4 for cross-references; it is NOT a sub-class of "inert" and must not be filed as one)*

🛑 **NOT falsified. NOT inert. NOT never-tried. The build flew, the lever was LIVE, and the INSTRUMENT
failed. "UNINTERPRETABLE" is not a verdict — it is a DESIGN FAILURE ON OUR SIDE.**

⭐ **This is where the kit's recoverable value is hiding.** Collapsing these into "falsified" throws away
good levers, and the record shows the kit has done exactly that before (V64's gate null *"was read as a
result for weeks"*; `0x454FE` was *"recorded mid-session as FALSIFIED"* and had to be retracted under
RULE 5).

- 🛑🛑 **`0xC63AC` 102→150 — V97, route `80`. DO NOT RE-DOSE, AND DO NOT RECORD IT AS FALSIFIED.**
  **The lever is proven LIVE and both of the operator's own hypotheses are REFUTED:**
  - *"a mistaken cal address"* — **excluded 3 ways.** `0x38202` bytes `e5 6f ad 73` = `ld.hu 0x73ac[tp]`;
    `tp+0x73AC = 0xC63AC` reads 102 / 102 / 150 (stock / V96 / V97); off-by-0x1000 excluded
    (`0xC53AC` = 683, identical in all three); six neighbour cals `0xC63A0..AE` all 1024 unchanged;
    census **1 reader / 0 writers** by five methods, Ghidra∖Python set-difference **EMPTY**.
  - *"the logic isn't used"* — **REFUTED statically AND dynamically.** `FUN_00038148`'s sole caller
    guards it with a mask **byte-identical to the guard on the assist-channel mixer** ⇒ **a shut gate
    would mean NO POWER ASSIST AT ALL.** And `sign(gp-0x374c)` **toggled 181× in 109 s** on this route.
    **No speed gate, no rate gate, no engagement gate anywhere on the path.**

  **Why it could not be scored — three reasons, none of them the lever:**
  1. **NO INSTRUMENT.** V96's cave carried unchanged; its regressor is **34× over-range** — `M ≡ 0` on
     **10,749/10,749** frames, `Mlo` duty **0.0000**. S1/S2 **VOID** — *conceded in
     `build_v97_tva.py:99-100` **before the flash.***
  2. **EXPOSURE.** **1** engaged hands-off episode ≥2 s, **1** decaying-angle return.
  3. **THE OBSERVABLE.** 🛑 **DC gain is 1.000000 at any `A` — a POLE, not a GAIN** ⇒ **no amplitude
     statistic can see it, and none was pre-registered.**
  ⊕ **V97 NEVER CLAIMED a grinding or ratcheting fix** — its header prices only a **21 Hz cost**.
  *"No difference in grinding"* **is consistent with the build working exactly as specified.**
  ⭐ **AND V98's COMPARATOR REMOVES THE LAST STRUCTURAL EXCUSE FOR ITS NULL:** the pole acts on the
  **ACTUAL** arm, and `b6` = **0.4235** proves ACTUAL is **comparable to MODEL** — a load-bearing arm,
  not a small one. ⇒ **`0xC63AC` is a live lever on a load-bearing arm that has never once been scored.
  It is the single clearest recoverable item in this category.** 🛑 **But it is only recoverable WITH AN
  INSTRUMENT** — DC gain is 1.000000 at every value, so any re-cut must pre-register a **phase or
  group-delay observable**, not an amplitude one. Re-dosing it blind would be V97 again.
- **V96's S1/S2** (`f′`, the LERP local slope) — **VOID** by the same 34× over-range. (Later closed
  *analytically* instead: the Stage-2 rescale is the **IDENTITY**, swing 1.000×.)
- **V53's FOURFRAME2** — **never transmitted**: our own STRB/SSAM cave defect wrote STRB = 0x80 leaving
  SSAM = 0. Not the gateway. Null uninterpretable.
- **`0xC6446` as a ratchet lever** — 🛑 the V88 handoff itself: *"the cross-build 6–9 Hz comparison
  inherits route 71's [0.18, 5.51] split-half null ⇒ it CANNOT RESOLVE a ratchet change under ~3–5×.
  'The ratchet was unchanged' is NOT supported by this route pair — 'cannot resolve' is."*

## D3.C ⭕ UNTRIED — and the two sub-classes must never be merged

### C1 — VIRGIN CELLS (no build has ever written them)

**✅ CENSUS RUN BY ME, from all 93 `_v*_plain_image.bin` + stock `code.bin` (94 images), raw Python LE
read [EVIDENCE]:**
```
0xC4080  (K0, the NEVER-RAISE relay hazard) :  0 on 94/94  ->  VIRGIN
0xC63A6  (the virgin Path-2 multiplier)     : 1024 on 94/94 -> VIRGIN
0xC40BC  (Coulomb relay normaliser)         :  600 on 91  ·  6000 on 3 (V85, V86, V86B ONLY)
                                              -> 🛑 BELOW 600 HAS NEVER BEEN TRIED  [confirms C2 below]
0xC40D2  (K1, modelled friction)            :  102 on 85  ·   204 on 9 (V89..V98)  -> ON THE CAR
0xC40D4  (command-branch EMA)               :  573 on 93  ·   286 on 1 (V86 ONLY)
0xC63AC  (the Path-2 IIR pole)              :  102 on 92  ·   150 on 2 (V97, V98)
0xC63A0  (Path-2 damper weight)             : 1024 on 86  ·  2048 on 8 (V72, V72sup, V73, V74,
                                              V75 x2, V76g, V81)  -> matches the record's own correction
```
⚠ The rest of C1 is being re-verified by the byte-ledger subagent; where its verdict differs from this
table, **ITS verdict wins** (RULE 4: attribute from the byte diff, never from prose).

| cell | status and the reason it is not a free lever |
|---|---|
| `0xE547C` / `0xE5404` / `0xE52FC` / `0xE5284` — the **AUTHORITY-COLLAPSE CURVE** | **VIRGIN on all 90 images**, and **he drives on its knee**: curve `X[0]` = 2240 vs **measured median override torque 2235 — one count below.** Authority goes **254 → 0 between raw 2240 and 2560**, nearly a step. 🛑 **NOT A 6–9 Hz LEVER — refuted five ways.** It targets the measured **~0.5–1 Hz SURGE**, which **NO OPERATOR COMPLAINT IS ATTACHED TO.** 🛑🛑 **SAFETY IS ASYMMETRIC** — Honda collapses authority when the driver pushes hard; widening it makes the car **fight the driver harder and for longer.** Only a **MONOTONE-NON-INCREASING** reshape is defensible |
| **`0xC4080` (K0)** | **VIRGIN. 🛑🛑 NEVER RAISE** — `FRICTION += cal/1024 × ratio` with **no `\|model\|` factor** ⇒ a **latent PURE COULOMB RELAY**, amplitude-independent and unbounded in index |
| `0xC63A2 / A4 / A6 / A8 / AA` | VIRGIN. **`0xC63A6` was TRACED AND STRUCK the same day**: it weights **only** `gp-0x6b26`, one instruction, zero writers — but `gp-0x6b70` is a **PID REFERENCE THAT GETS SUBTRACTED**, so Path 2's sign depends on `sign(iVar6)` **and** on the local slope of a RAM-resident LERP. 🛑 ***"A lever whose SIGN is unresolved is not a lever. That is exactly how V94 reached the car."*** `0xC63A4`'s lane carries **~1.1 ct of a 342 ct signal** |
| `0xC40D0` / `0xC40D6` / `0xC40D8` | the other three `FUN_0003b8f6` EMAs — VIRGIN, untraced as levers |
| **`0xC63F8` = 33 vs `0xC63FC` = 328** | ⭐ **a 10× LEFT/RIGHT RAMP-RATE ASYMMETRY, VIRGIN on all 85 images, and NOBODY HAS EVER ASKED HIM whether the car feels different turning left versus right.** The cheapest open question in the kit — it costs one sentence |
| `0xC63AE` = 1024 | VIRGIN. 🛑 **NEVER → 0** — the LERP index becomes ≡0 ⇒ output ≡ ±`Y[0]` = **a pure relay at full authority** |
| `0xC6200` = 8192 | 🛑 **NEVER < `Y[0]`** — the clamp does the same thing from the other side. ⚠ **15 readers, 3 still unidentified** ⇒ its RULE-11 census is **NOT complete** |
| `0xC618A` / `0xC627E` / `0xC63C0` | the **relay-with-dwell** in `FUN_00036388` — never edited by any build (grep-confirmed). 🛑 **Do not arm it**: the snap flattens the one shaped curve in the lane into a constant = the FLATTEN-INTO-A-RELAY class, and the lane is **dead engaged** (B3) |
| `0xC64DE` = 25627 | 🛑 **NON-STOCK SINCE V22 — 85 builds — with a disputed label and never once isolated.** The longest-carried unmeasured cell in the image. Not implicated in anything current, but it is *carried by accident* |

### C2 — "THE SAME LEVER PUSHED THE OTHER WAY" — a DIFFERENT claim from a new lever

| direction | status |
|---|---|
| ⭐ **`0xC40BC` BELOW 600** — *more* relay, not less | ✅ **NEVER TRIED — CONFIRMED BY CENSUS [EVIDENCE]: 600 on 91 images, 6000 on exactly 3 (V85/V86/V86B). No image has ever carried any other value.** Two independent measured lines support the direction: (a) less friction relay ⇒ **MORE ratchet** (2.89× at 600 vs **6.58×** at 6000, contrast +0.682 [+0.213, +1.166]); (b) **driver GRIP damps the same band** (−0.655 vs a control's −0.266, CIs disjoint). ⇒ *"THE LEVER CLASS IS MORE COLUMN FRICTION / DAMPING, NOT LESS COMMAND."* ⚠ **BELIEF that below-600 is in range and safe** — GATE 2 unrun, and the association **cannot be fully separated from V86's `0xC40D4`** (V86 moved it in the same 3-route flag). ⚠ **The instrument measures 6–9 Hz band energy, not "feels smooth"** — more Coulomb friction can reduce the oscillation while making the wheel feel **notchier**, which is exactly what V86B's *"extra dampening… at slow speed"* cost was |
| `0xC63AC` **BELOW** 102 (lag, not lead) | untried — but it **inherits V97's observability problem entirely** (DC gain 1.000000). 🛑 **Do not re-cut this cell without a phase or group-delay observable pre-registered** |
| `0xC6446` **DOWN** (Lever B lower) | every build has pushed it UP. ⚠ the §5 argument for testing it DOWN rested on **rate-dependence**, which the 235-block corpus **REFUTED** (`eng × log rate` band contrast **+0.022 [−0.070, +0.116]**) ⇒ **r24 is DEMOTED, not promoted** |
| `0xC6446` **UP** beyond 5244 | 🛑 **BLOCKED BY THE RAIL.** 2.000× (V88) = 1.50× hot-end margin · 2.5× = at the rail · **3.0× PINS = relay class.** The usable window above V88 is **narrow to non-existent** |
| `0xC61F6` 3 → 0 (rate-lane deadband) | 🛑 **DO NOT.** A deadband is the **DUAL of a relay** — `N(A) → 0` as `A → 0` is precisely what *prevents* harmonic balance closing. **Deleting it ADDS small-signal gain**, i.e. pushes the destabilising way. This **REVERSES** the framing that opened it as a candidate |
| `0xC61D6` (shaper slew step) | 🛑 **ALREADY REJECTED TWICE.** It does not re-enable an anti-snap ramp — it **activates a dormant, uncalibrated speed × torque 2-D map onto the live command.** ⇒ **there is NO usable cal-only rate-limiter lever on this path** |
| **Lever A** `0x3AB76`/`0x3AC20` `sar` restore | 🛑 **DO NOT RESTORE.** The `sar` is **UNGATED** ⇒ it reproduces V62/V65 **in the MANUAL arm**, and his V65 report on exactly that condition is *"makes the entire car vibrate, almost like I have a subwoofer… happens regardless of LKAS engagement."* ⚠ the int16-overflow leg of this argument is **WITHDRAWN**; the verdict stands on the manual-arm leg alone |
| `gain_A` rec0/rec1 LOWERED | 🛑 **ENGAGED-INERT — already run, twice failed.** Lever B's gate repoint makes `lp = latActive`, and the armed path at `0x3AB5E` **OVERWRITES `gain_A` with `[0xC6444]` = 512** ⇒ **V84 and V85 ALREADY deliver 512 engaged at every speed.** FAIL on both |

## D3.D ☠ The seven that died at the desk in the V97 session — recorded so nobody re-raises them

| lever | how it died |
|---|---|
| **pre-declared V97** (`gp-0x6b4c`/`gp-0x6b4e`) | `gp-0x6b4e` **provably ≡ 0**; the array is `gp-0x62c8[]`, **not** `gp-0x62f8[]`, and they are **two different arrays 0x18 apart** |
| return-to-centre lane | 🛑 **a RACK END-STOP CUSHION**, not a centring lane (see B3) |
| `0xC520C` governor ceiling | first knot **222.8 °/s**; measured returns reach **0.00 %** of it |
| `0xC6194` LKAS slew limiter | **100 % bypasses it** (`0xC4118` all-1) |
| **AUTH / `0xC67C8`** | β(log AUTH) = **−0.013 [−0.344, +0.319]** — CI **excludes the predicted +1** — *and* `gp-0x6b4c` is a second LKAS route that **never sees AUTH.** ⚠ the table header is `0xC67BE`; `0xC67C8` is its `Y[0]` |
| PID Ki `0xC6B12` | **INERT** — the integrator is pinned by anti-windup |
| `0xC63A6` / `0xC63A4` | **a cliff edge, not a lever** (V91/V92 ×1.5 null + V94 ×0.25 catastrophe fit closed-loop invariance, not a dose-response) |

---
---

# D5 — THE DESIGN LAW AUDIT

**The law under test** (`CLAUDE.md`, claimed from all 45 probe builds V53→V97):
> *Every probe that DECIDED something was a **SIGN BIT PAIRED WITH A MAGNITUDE CHANNEL**, or a
> **deliberately-designed CONTROL**. Every UNINTERPRETABLE null was a **SINGLE THRESHOLD RUNG** on a
> quantity with no measured distribution and no positive control.*

## D5.1 The audit, probe by probe

⚠ **SCOPE, stated honestly.** `CLAUDE.md` says *"all 45 probe builds V53→V97."* **This audit covers the
~24 probes whose RUNG DESIGN AND OUTCOME are both recorded** in `STATE.md`, `BUILD-LINEAGE.md`,
`BUILD-LINEAGE-PART1-LEVER-INDEX.md` and `memory/`. Builds that merely *carried* a predecessor's cave
unchanged (V63, V65, V66, V71a/b, V74, V77–V79, V81, V83a, V91, V93, V97) are counted in the 45 but have
no rung of their own to audit — **and V97 is precisely the case where "carried unchanged" was the
failure** (D5.1, last row). **I have not audited a rung I could not find a written design and a written
outcome for**; where the record is silent I say so rather than infer.

### ✅ PROBES THAT DECIDED SOMETHING
| build | instrument | what it decided | law-consistent? |
|---|---|---|---|
| **V54** | 5-bit `gp-0x6966` = a **MAGNITUDE** channel | authority ≡ **0 by design** on every V31+ build, 5,989/5,989 | ✅ magnitude |
| **V55** | 4-bit `gp-0x6b98` **magnitude** + a variant/identity bit | the oscillation is **internal** | ✅ magnitude + identity control |
| **V58** | the **SIGNED** boost sibling | it crosses zero at **20.93 Hz only when LKAS applies** ⇒ the index is that signal **full-wave rectified** | ✅ SIGN |
| **V70** | **4-bit SIGN probe**: b4 = r26 sign, b3 = r24 sign, b5 = state gate `== 10`, b6 = `\|r24\| ≥ 512` | **state 10 is 0.0000 %** ⇒ the five-build detector null is GENUINE; **r26 is LIVE** (`gp-0x6adc` strictly negative 1,644/18,010) ⇒ the "r26 is inert" LEG 2 **REFUTED** | ✅ **SIGN bits decided; ⭐ b6 — the ONE threshold rung — returned an uninterpretable 0/18,010 against a replay predicting 311. A PERFECT WITHIN-BUILD CONFIRMATION OF THE LAW** |
| **V72** | b4 = `\|gp-0x6bd0\| ≥ 64`, a **single threshold rung** | **RULE 6: the car is NOT in mode 10/11.** Fired **0 of 87,940** against an **arithmetically PRE-REGISTERED 100 %** | ⚠ **EXCEPTION on form, CONSISTENT on substance — see D5.2 R1** |
| **V73** | reads the mode byte `gp+0x63fd` **directly** = a value channel on the SELECTOR | which record the car reads | ✅ magnitude, and **GATE 4's rule** (probe the selector, not the output) |
| **V75** | magprobe + a **THERMOMETER** on `gp-0x6bd0` (L0…L4 census) | **V75's damper NEVER entered its saturated regime** — L4 (≥448) = **0.000 %** of 28,317 engaged frames | ✅ **a thermometer IS a magnitude channel** |
| **V76** | b7 = `\|gp-0x6b26\| > 448`, a **single threshold rung** | fired **0/63,477** — and it is a **REAL NULL, not an unarmed gate**, because **b3 (positive control) read 99.93 % in the same frames** | ✅ **the law's escape clause, used correctly** |
| **V80** | the identical b7 rung, flown against **V75 as a control build** | duty **19.4 % overall / 71 % through the worst 29 s event** vs V75's **0.000 %** — *"the single cleanest statement of the root cause in this file, and both numbers came from the builds' own caves"* | ✅ **a deliberately-designed CONTROL (a flown comparator build)** |
| **V85** | 4-rung, + a **nesting identity** (`b6⇒b7`, `b5⇒b4`, 0 violations) | relay saturation **39.5 %→11.1 % overall, 33.3 %→4.6 % engaged (7.21×)** — both pre-registered duty predictions **HIT** | ✅ duty (magnitude) + designed control |
| **V86** | ⭐ b7 = SIGN · b6 = `≠0` · b5 = `≥64` · b4 = gate · b3 = fingerprint, **with the b5/b6 RATIO deliberately designed as a relay-vs-linear discriminator** | the pre-registration **FALSIFIED and WELL-POWERED** (2.6× margin) ⇒ **the linear-loop hypothesis is dead** | ✅ **TEXTBOOK — sign + magnitude + a designed discriminator** |
| **V87** | CAN 427 ← `gp-0x6b98` = a full **10-bit MAGNITUDE channel** | *"the kit's biggest instrument gain since the cave"* — 99.02 % non-zero, 946 distinct codes; **the ~120 ct p-p assumption was low by 1.35×, not 5×** | ✅ magnitude |
| **V88** | ⭐⭐ **cave b7 = SIGN of `gp-0x6b98` at 100 Hz, PAIRED WITH the 427 MAGNITUDE channel on the same cell** | **H2 — the fork closed.** Signed ≈ rectified ⇒ rectification was never hiding a line; **the ratcheting is NOT a tone the EPS commands** | ✅ **THE ARCHETYPE OF THE LAW** |
| **V89** | cave `gp-0x6ae2` **SIGN + magnitude (±64)** | arithmetic: the friction term is `sign(motor rate)`-gated and `\|friction\| ≥ 0.0625` on **0.9 %** of the micro-ratcheting regime ⇒ **the lever was pointed away from the target** | ✅ |
| **V90** | ⭐ b7 = `gp-0x6b26 < 0` (SIGN) **+ 427 ← `gp-0x6b26` (MAGNITUDE)** + b4 = observer-gate SIGN + b3 fingerprint; b6's 512 threshold carried a **pre-registered 0.10–0.50 bracket** | `gp-0x6b26` **measured for the first time on any build** (p50 5.5 / max 319.1, **clamp duty EXACTLY 0.000000**); **the observer gate NEVER fails** (0/124,362); the **same-firmware placebo pair** | ✅ **sign + magnitude + a pre-registered bracket (landed at 0.2535)** |
| **V92** | cave on 4 cells + 427 ← `gp-0x6bbe` (magnitude), **with a MANUAL arm as the designed control** | `gp-0x6bbe` is **VISCOUS + a DC pedestal** — p50 **73.6 ct flat across 0–6 °/s**, and **`P(<0)` 0.887 engaged vs 0.499 manual = the DC LKAS bias, instrumented** | ⚠ **MIXED** — the magnitude channel decided; its two threshold rungs (`gp-0x6b62 ≠ 0`, `gp-0x6bda` gate) returned **0.0000 duty = a V64-class null on the gate** |

### ☠ PROBES THAT RETURNED AN UNINTERPRETABLE NULL
| build | the rung | why it failed |
|---|---|---|
| **V53** | FOURFRAME2, a **new mailbox** | ⚠ **NOT a rung failure — a TRANSMIT-PATH failure.** Our own cave wrote STRB = 0x80 leaving SSAM = 0 ⇒ never transmitted. Closed by *"use `0x14A` byte4 bits 7:3, proven across four flashes; do not build another new-mailbox channel"* |
| **V64** | a single rung on the oscillation detector | **the detector never armed** — the null is on the GATE. Read as a result for weeks |
| **V67 / V68** | `gp-0x67df`, a single rung on a **lane OUTPUT** | the cell has **NEVER been non-zero on any build** (0/186,321, 0/53,991) |
| **V69** | 🛑 **ALL THREE RUNGS** | **b4 STRUCTURALLY VACUOUS** — sized against the **ERR *input* clamp ±0x2800** when the lane's OUTPUT is clamped to a speed-indexed CEILING that was **164–341** at the ratchet's speeds ⇒ **the test sat 12–25× above the lane's entire reachable range.** **b5 INSENSITIVE** — 4096 = 71 % of a 5786 reachable max ⇒ it saw only the top 29 %. **b6 NO EXPOSURE** — replay predicts ~1 hit, observed 0, p ≈ 0.37 — *and it was therefore not a positive control either, so b5/b4 could not be interpreted against it.* ⭐ **THE CANONICAL CASE** |
| **V70** | b6 `\|r24\| ≥ 512` | 0/18,010 against a replay predicting **311** (stock predicts 52) |
| **V84** | b7/b6 `\|r24\| ≥ 1024` | on a lane whose input **never exceeded 201** ⇒ **0.0 across 68,235 frames in BOTH arms**, and it was read as *"the lever was out of force."* **It was not — the rung could not have fired either way** |
| **V96** | `gp-0x374c >> 4`, LSB **2048**, saturating at 12288 | 🛑 **34× OVER-RANGE.** `M ≡ 0` on 99.90 % / 99.97 % / **100 %** of three routes; `Mlo` duty 0.0000 ⇒ **S1 AND S2 BOTH VOID.** The build note says outright it was sized *"deliberately below the 68,614 structural bound because NO BUILD HAS EVER PUT EITHER CELL ON THE WIRE"* — i.e. **the distribution had never been seen.** ⭐ **THE POSTER CHILD** |
| **V97** | 🛑 **none — it carried V96's cave unchanged** | ⚠ **A DIFFERENT FAILURE CLASS: not a bad rung, but NO RUNG AT ALL.** A lever flown on the previous build's already-broken instrument, with the fault **conceded in the build script before the flash** |

## D5.2 ⇒ VERDICT: **THE LAW HOLDS — with three named refinements V99 must build to**

### R1 — ⭐ THE OPERATIVE VARIABLE IS NOT "THRESHOLD vs SIGN". IT IS **WHETHER THE DUTY WAS PREDICTED BEFORE THE FLASH.**
A single threshold rung **has decided, three times**, and in every case its duty was pre-registered:
- **V72** — the shipped surface's own arithmetic predicted **100 %**; observed **0 of 87,940** ⇒ RULE 6.
- **V76** — a **positive control in the same byte** read **99.93 %** in the same frames ⇒ *"a REAL null,
  not an unarmed gate."*
- **V80 vs V75** — the **identical rung** on a **flown comparator build**: 0.000 % vs 19.4 %.

And every failed rung failed the same test: **V69** (no reachable-range computation), **V70 b6**
(replay-predicted 311, observed 0 — a *prediction that was made and violated*, which is why it was
informative about the lane rather than about the rung), **V84** (input max 201 vs a 1024 test),
**V96** (a guess against a never-observed distribution).

> **⇒ THE RULE V99 MUST BE BUILT TO: every rung arrives with a PRE-REGISTERED DUTY. If you cannot state,
> before the flash, what fraction of frames the rung will read TRUE and why, it is not a rung — it is a
> guess, and this kit has lost EIGHT rungs to that.**
> This is **GATE 3's sharpest form**, already in the record: ***"a falsifier only fires if it COULD have
> fired"*** — and it must be applied to abort criteria and pre-registered falsifiers **including the
> ones that come back clear.**

### R2 — TWO FAILURES ARE **NOT COVERED** BY THE LAW AND NEED SEPARATE GUARDS
- **(a) TRANSMIT-PATH (V53).** A perfectly-designed rung on a channel that never reaches the wire.
  Guard: **`0x14A` byte4 bits 7:3 + byte7, proven across V54/V55/V56/V57 and every build since. Never
  build another new mailbox** — the CAN gateway is a **WHITELIST** (only `0x14A`/`0x18F`/`0x1AB` cross)
  so a new ID can **never** reach openpilot.
- **(b) NO INSTRUMENT AT ALL (V97).** The law is about rung *design*; V97's failure was **not designing
  one.** Guard: **`CLAUDE.md`'s own gate — *"before cutting, write the sentence a null will license. If
  the honest answer is 'we would not be able to tell,' the build is not ready."*** V97 is the case study,
  and the fault was **written into the build script before the flash and flown anyway.**

### R3 — A THRESHOLD ON A **STATIC / CONFIGURATION** QUANTITY IS SAFE
**V96's `b3` = `gp-0x674e < 28`** is a single threshold rung with no magnitude channel and no positive
control — **and it DECIDED**, settling **RULE 7 for the authority curve** (the `Y[last]=0` records are
live; modes 28–39 excluded). Its quantity is a **boot-parsed configuration byte with a point-mass
distribution.** ⇒ **the law binds on DYNAMIC signals.** A config/selector/mode rung is cheap and safe —
and it is exactly what **GATE 4** already asks for (*"spend a bit on the SELECTOR/MASK that decides which
gain is in force, before spending one on the lane's output"*).

### R4 — ⭐ THE COMPARATOR IS STRICTLY STRONGER THAN EVERYTHING ABOVE, AND V98 IS THE FIRST ONE
A comparator rung (`|A| ≥ |B|`) is **immune to UNDER-RANGED and OVER-RANGED BY CONSTRUCTION**: no LSB, no
ceiling, no assumed distribution. It compares at full precision **inside the cave, before quantisation
exists**, and **its duty IS the answer** — so R1's pre-registration requirement is satisfied
*automatically*, because there is no threshold to pre-register.
🛑 **Buildability cost, from V98's own record — do not under-price it as §R8 did:** a comparator needs
**three live values in two registers**; **recomputation alone cannot fix it**; V98's byte 4 is
read-modify-written twice with two masks (`0xDF`/`0x27`) **proven to partition the byte**; and
**Path 2 was never available** — `r6`/`r7` are the only registers the record can defend. Cave grew
**112 → 154 B (+37.5 %), 43 → 59 instructions, 12.7 % of the 1,212 B extent.**

---
---

# D6 — THE ONE-EPISODE CONSTRAINT: WHAT SURVIVES, AND WHAT IS NOW UNBUILDABLE

## D6.0 The budget, stated exactly

Operator, verbatim: *"the exposure really should not matter. I can do a couple of tests sure, but if I
observe micro-ratcheting or grinding, I am generally going to stop instantly. No point in continuing
that drive if the single thing I'm testing for did not get fixed."*

**TWO reference drives now exist. Calibrate between them, and design for the WORSE one.**

| | **route 80** (V97) | **route 81** (V98) |
|---|---|---|
| total | 109.2 s | 3 segments |
| **engaged** | **17.2 s in ONE episode** | **65.9 s in THREE episodes** |
| speed | p50 **5.13 km/h**, v_max 6.6 | parking-lot creep |
| arms | 19.5 % override / 80.5 % hands-off | ⭐ **seg1/seg2 = a clean engaged / LKAS-off MATCHED PAIR** |
| faults | none | none |

⇒ **plan for 15–65 s engaged across 1–3 episodes, at creep, with 0 s above ~10 km/h.**
🛑 **The binding rule does not move with the better number: a V99 whose endpoint needs matched episodes,
minutes of exposure, or a CROSS-BUILD contrast is UNBUILDABLE.** Three episodes is still below
`min_ep`-style requirements once a cell stratification is applied, and one drive can never supply the
mandatory same-firmware placebo pair.
⭐ **What route 81 DID buy, and it is the most important exposure fact in this section: a WITHIN-DRIVE
ENGAGED/LKAS-OFF MATCHED PAIR.** That is the control D6.2 row 6 asks for, demonstrated to be
obtainable. **V99's drive protocol must require it, not treat it as optional.**

**Derived window counts — the arithmetic that kills most of the kit's machinery:**

| unit | from 17.2 s (r80) | from 65.9 s (r81) | usable? |
|---|---|---|---|
| **episodes** (the bootstrap unit) | **1** | **3** | ☠ still far too few |
| `blk` ≈10.2 s block (the estimator's own unit) | **1–2** | **~6** | ☠ |
| 5.12 s window, hop 2.56 s | ~3 independent | ~12 independent | ☠ / ⚠ |
| 2.56 s window (NFFT 256 @ 100 Hz) | ~6 independent | ~25 independent | ⚠ |
| 1.28 s window, hop 0.64 s | ~13 independent | ~51 independent | ⚠ |
| **frames (100 Hz)** | **≈1,720** | **≈6,590** | ✅ |

⊕ **The frame count is the one that matters, and V98 proved it:** its comparator rungs were scored on
**6,591 engaged frames** and returned a duty of **0.0000** and **0.4235** — decisive readings from
exactly the class of statistic this section says survives.

## D6.1 ☠ STRUCTURALLY UNBUILDABLE ON THIS EXPOSURE — **do not propose a V99 whose endpoint needs any of these**

| method | why it is dead at 1 episode |
|---|---|
| **Any CROSS-BUILD band ratio** | `boot_cellwise` needs `min_ep` episodes and `min_win` windows in a cell **on BOTH sides**, and a same-firmware **PLACEBO PAIR** is mandatory (V90 supplied one: byte-identical firmware returned `e_6-9` **1.288 [1.017, 1.661]** — a CI **excluding 1.00** on **no change at all**). Honest resolution floor with FULL exposure is **±16–22 % contrasted / ±33 % raw.** At one episode there is no floor at all |
| **Any EPISODE BOOTSTRAP or SPLIT-HALF NULL** | `min_ep = 2`. ⇒ **every CI this kit knows how to compute is unavailable.** And *"a ratio must clear ~1.5 (or fall below ~0.67) to mean anything"* even at full exposure |
| **Ring-down ζ / Q** | needs **10–35 clean edges at 35–45 km/h**, hold ≥5 s engaged, stay hands-off ≥5 s after, disengage with the cancel button. Route 73 produced **1 usable edge from 5 disengagements** on 613 s |
| **Any ≥50 km/h or highway claim** | 0 s available. V85 (34.6 s ≥50) and V83a (37.1 s) were both declared **UNSCOREABLE** at more exposure than this drive has in total |
| **Any 26–31 Hz "ring" claim** | same, and 🛑 **no operator symptom is attached to that band anyway** |
| **Any grind #2 claim** | the interpretability floor is **166 s**; V88 got **47.4 s = 29 %** and its zero was **formally uninterpretable.** Four builds in a row missed it |
| **Any dose–response ladder** | needs ≥3 builds |
| **Any 5.12 s-window OVERRIDE statistic** | override runs: **median 0.02 s, p90 0.55 s, and only SEVEN runs corpus-wide reach 5.12 s** |
| **Any wheel-order-vetoed 6–9 Hz ratio** | the veto drops **~50 %** of windows (V85 134/266, V81 317/495). From ~13 independent windows there is nothing left |
| ⚠ **Any 6–9 Hz SPECTRAL claim from a ~5 km/h creep** — and **the kit's veto cannot tell you either way** | 🛑 **A LIVE INCONSISTENCY IN THE RECORD, flagged rather than resolved.** The record's own order-clean windows for 6–9 Hz are **1.8–3.6 · 33.8–44.6 · 67.7+ km/h**, which puts route 80's engaged p50 of **5.13 km/h in a CONTAMINATED window.** But the **implemented veto sweeps orders 1–6 only**, and at 1.425 m/s (C = 2.0805 m) orders 1–6 span **0.68–4.11 Hz — entirely BELOW the band**, so **the veto passes every window and reports "clean."** The orders that reach 6–9 Hz there are **k ≈ 9–13** (k × 0.685 Hz). ⇒ **either the clean-window table assumes orders the veto does not sweep, or the table is wrong.** [EVIDENCE for both halves; **BELIEF** as to which is right — I could not resolve it from the record] ⚠ **Consequence for V99 either way: a 6–9 Hz spectral verdict from a parking-lot creep carries an unquantified contamination risk that the kit's own tool CANNOT screen. Prefer cave bits, which are internal firmware signals and immune to wheel order entirely.** |

## D6.2 ✅ WHAT SURVIVES — and it is a short list

**All of it is WITHIN-FRAME or single-frame. None of it needs an episode.**

| method | why it survives | precedent |
|---|---|---|
| **1. Single-frame identity / liveness / fault screens** | one frame is enough | V90's `b4 == 0` on 124,362/124,362; V92's identity; V98's byte7 = 2 |
| **2. ⭐ DUTY of a cave bit over the engaged frames** | n ≈ 1,720; even at an effective n of ~100 after autocorrelation, **0.00 vs 0.50 is decisive** | V76 (0/63,477 with a 99.93 % control), V80 vs V75 (19.4 % vs 0.000 %), V85 (39.5→11.1 %) |
| **3. ⭐⭐ COMPARATOR RANK DUTY** | **immune to over/under-range by construction; its DUTY IS THE ANSWER** | **V98** — the first in the kit |
| **4. JOINT DUTY / a contingency table of two or more bits in the SAME frame** | a 2×2 or 2×2×2 needs no episode structure and separates confounded hypotheses that a single bit cannot | V90's `(b6,b5)` 2×2; V86's `b5/b6` ratio as a relay-vs-linear discriminator |
| **5. CONDITIONAL duty** — bit X given bit Y, or given a bus quantity | 🛑 **the operator reasons from steering angle, driver torque and LKAS demand — ALL ALREADY FREE ON THE WIRE.** Cave bits must **COMPLETE** that picture, not duplicate it | V92's `P(<0)` 0.887 engaged vs 0.499 manual |
| **6. ⭐ A WITHIN-DRIVE MANUAL ARM** | the only control the exposure permits | ✅ **DEMONSTRATED ON ROUTE 81 — seg1/seg2 are a clean engaged / LKAS-off matched pair.** V98's protocol called it *"optional and free"*; it is neither optional nor a nicety. 🛑 **MAKE IT A REQUIRED STEP OF THE V99 DRIVE.** Without it V99 has no control at all |
| **7. Event-triggered ONSET windows at the single `latActive` rising edge** | n = 1, so only a **large** effect is visible — but the record shows the effect IS large: the transition trace goes **134 → 1,179 counts in 0.7 s (8.8×)** with speed moving the *wrong* way for a confound | route `50`'s transition trace |
| **8. Sign-crossing / zero-crossing RATE within the episode** | ⚠ **as a WITHIN-BUILD contrast only** (engaged vs the manual seconds). 🛑 V97 used it **cross-build** and it sat inside its own split-half noise **with the control bit moving too** | V97's failure mode |
| **9. ⭐ THE OPERATOR'S OWN REPORT** | **the primary endpoint, and the only instrument that scores the SYMPTOM.** *"None of these have been fully fixed"* outranks any band | every build |

## D6.3 ⇒ THE BINDING CONCLUSION FOR V99'S INSTRUMENT

> 🛑🛑 **On the exposure the operator will actually give, the ONLY interpretable readout is a
> WITHIN-FRAME DUTY or RANK on cave bits, with a positive control in the same byte and a manual arm in
> the same drive.** The column-torque SPECTRUM is unusable at that episode count on exposure grounds
> alone (D6.1), and carries an **unscreenable** wheel-order risk at ~5 km/h on top (D6.1, last row).
> **Cave bits are internal firmware signals sampled per frame — immune to wheel order by construction.**

⇒ **V99's endpoint must be a sentence of the form:**
*"Bit X reads TRUE on p₁ of engaged frames and p₀ of manual frames; we predicted p₁ ≈ … and p₀ ≈ …; the
positive control in the same byte reads ≈1.0; therefore ‹mechanism› is / is not what is happening while
he feels it."*
**Write that sentence BEFORE cutting. If you cannot fill in the predicted duties, the build is not
ready.** (`CLAUDE.md`'s own gate, plus D5.2 R1.)

---
---

# D2 / D4 — CROSS-BUILD CELL MATRIX AND THE V98 NON-STOCK DELTA

✅ **DONE — read from the IMAGES, not from prose (RULE 4).** Reader:
`analysis-2020accord/ledger_v38_to_v98_bytes.py`; output `ledger_v38_to_v98_out.txt`;
machine-readable `v98_vs_stock_delta.json`.
**Anchors held:** `0xC646C` = 891 on stock · `code.bin[0x454FE]` = `0xBA` · `len` = `0x100000` ·
**89 images on disk, 0 missing.**

> **V98 vs STOCK: 312 differing bytes in 113 runs = 139 control-law + 153 cave + 20 CRC.
> 🛑 UNATTRIBUTED: NONE.**
> V97 vs STOCK: 270 bytes, the same 113 runs, **the same 139 control-law bytes** + 111 cave.
> ⇒ **the V97→V98 delta really is cave-only, confirmed from the images.**

## 🛑🛑 D4.0 — THE HEADLINE: A MEASURED-INERT NON-STOCK CELL IS ON THE CAR AND V99 WILL INHERIT IT

```
0xD7A5C/5E/60  mode 26 (ENGAGED) friction/inertia Y = -14745 / -8601 / -2949   (stock -9830/-5734/-1966)
0xD7A6C/6E/70  mode 27 (ENGAGED) friction/inertia Y = -14745 / -8601 / -2949   (stock -9830/-5734/-1966)
0xD6A6C/6E/70  mode 24 (MANUAL)  friction/inertia Y =  -9830 / -5734 / -1966   = STOCK
```
⇒ **THE `0xCBE74` ×1.5 ENGAGED DOSE IS ON THE CAR.** First written at **V74**; carried
V91 → V92 → **V96 → V97 → V98**. This is the lever filed **MEASURED INERT** (engaged stratified ratio
**0.99 [0.91, 1.26]** against a pre-registered 1.50; manual control 1.009).
🛑 **It is on the car BY BASE CHOICE, NOT BY DECISION** — V96 was cut from V92 *"with V94's cut reverted
by construction"*, which silently carried V91's ×1.5 forward. ✅ Mode 24 is stock, so the **built-in
manual control still exists.** ⇒ **V99 inherits it unless deliberately reverted, and the close-out
message must say so.**

## D4.1 — THE COMPLETE CONTROL-LAW DELTA, V98 vs STOCK

| addr | stock → V98 | first | what it physically is / does to the car |
|---|---|---|---|
| **— THE LKAS 4× AUTHORITY PACKAGE —** | | | |
| `0x2A1F0` | 29804 → **31952** | V57 | displacement: repoints the **FORWARD** LKAS path off the shared cell onto a private one |
| `0xC6CD0` | −1 → **3564** | V57 | **the private 4.000× forward LKAS gain** |
| `0xC646C` | **891 = STOCK** | — | ✅ the SHARED sensor scale is back at Honda ⇒ the 4× no longer leaks into 5 other readers (V87's rebase fix, carried) |
| `0xC61B2` / `0xC61B4` | 512 → **2048** | V22 | **arbitration** and **LKAS-gain OUTPUT CLAMPS**, 4× Honda. ⚠ these are NOT "the pre-gain deadband" — that is `0xC61B8` = 102 and it was never rescaled |
| `0xC674E/50/5A/5C` | ±1024 → **±5120** | V25 | corridor walls (INT), 5× |
| `0xC6598/9C/AC/B0` | ±1f → **±5f** | V29 | corridor walls (FLOAT) |
| `0xC6768/6A/6C` | 0 / 1536 / 2048 → **5120** | V31 | boost floor (INT) |
| `0xC65C4/C8/CC` | 0f / 1.5f / 2f → **5f** | V31 | boost floor (FLOAT) |
| `0xE4194 … 0xE521C` | 15360 → **16384** | V38 | **ARB SETPOINT LIMIT — 81 cells (9 selectors × 9 knots)**, the ± clamp on the LKAS setpoint `gp-0x69ae`. **+6.7 %.** `sel1` is the LIVE selector for A160 |
| **— THE GUARD DISABLES —** | | | |
| `0xC61C0/C2/C4` | 1600/896/1280 → **65535** | V36 | gentle-EME debounce **RATE** thresholds — **OFF** |
| `0xC64B4/B6` | 24688/16438 → **65535** | V36 | gentle-EME debounce **TORQUE** thresholds — **OFF** |
| `0xC64B8` | 0x70 → **0xFF** | V37 | DTC-0x49 fail-counter gate. ⚠ **measured to remove NOTHING on this car** — both arms deliver 0 everywhere the branch could fire |
| `0xC62EA` | 320 → **0** | V53 | 🛑 **LOW-SPEED STEER LOCKOUT DISABLED.** ⇒ **creep at 5 km/h sits in a regime stock Honda would have locked out.** Material context for anything felt at parking-lot speed |
| **— THE ONE MEASURED FIX —** | | | |
| `0x3AA96` | 0xC5 → **0xFB** | V67 | Lever B **GATE** byte → `gp-0x6806` = `latActive` |
| `0xC6446` | 512 → **5244** | V67 | ⭐ **LEVER B ARM — r24's engaged rate-feedback gain, 2.000×.** The only measured fix on the car (grinding) |
| **— MEASURED INERT / UNVERIFIED, STILL CARRIED —** | | | |
| `0xC40D2` | 102 → **204** | V89 | K1, modelled Coulomb friction (the MODEL arm of the observer). **Measured FLAT** (0.947, inside a [0.900, 1.111] placebo band). **8 bytes, 9 builds, doing nothing measured** |
| `0xD7A5C…0xD7A70` | ×1.5 | V74 | **the ENGAGED friction/inertia dose — MEASURED INERT.** See D4.0 |
| `0x454FE` | 0xBA → **0xB5** | V42 | V42's macro-ratchet substitution — **MEASURED INERT** (state 4 = 0/123,277 while driving). Kept because it costs nothing and has been silently lost three times |
| `0xC64DE` | 25617 → **25627** | V22 | 🛑 **non-stock for 76 builds, label DISPUTED, never once isolated.** The longest-carried unmeasured cell in the image |
| **— THE LEVER UNDER TEST —** | | | |
| `0xC63AC` | 102 → **150** | V97 | the Path-2 Stage-1 IIR pole on the ACTUAL arm. **UNINTERPRETABLE, not falsified** |
| **— INSTRUMENT ONLY, no control effect —** | | | |
| `0x55C0E` | 4-byte `jarl` | V31p | the `0x14A` cave HOOK (**proven from the image to be the 100 Hz CAN-TX builder, NOT the 1 kHz task**) |
| `0x55DF2` / `0x55E10` | | V87 / V92 | CAN-427 packer SOURCE displacement + SHIFT byte |
| `0x13109`, `0x14120` | 0x2D → 0x2C | V22 | part-number ASCII (cosmetic) |
| cave `0xC4B34–0xC4BCD` | 153 B | V31p→V98 | the telemetry cave |

✅ **`0xC407E` = 511 = HONDA** — the hard-fault interlock is at its safe value (one count under its own
512 trip), **frozen 20 builds.** Not in the delta.
✅ **`0xC4080` (K0) = 0 = stock** — the NEVER-RAISE pure-relay hazard is untouched.

### ✅ D4.1b — INDEPENDENT RECONCILIATION OF THE 17 OBSERVER CELLS: **ZERO DISAGREEMENTS**
The orchestrator independently asserted that across all 17 observer cells **exactly TWO are non-stock.**
I re-read all 17 from the **V98 image** (and V97, and stock) with my own raw Python LE reader, anchors
re-checked (`0xC646C` = 891, `code.bin[0x454FE]` = `0xBA`, len `0x100000`):

```
0xC63AC   102 -> 150   V97   NON-STOCK   (the Path-2 IIR pole, on the ACTUAL arm)
0xC40D2   102 -> 204   V89   NON-STOCK   (K1, modelled Coulomb friction, inside the MODEL arm)
0xC4080 =    0 · 0xC40BC =  600 · 0xC40D0 =  408 · 0xC40D4 =  573 · 0xC40D6 = 246 · 0xC40D8 = 3686
0xC63A0 = 1024 · 0xC63A2 = 1024 · 0xC63A4 = 1024 · 0xC63A6 = 1024 · 0xC63A8 = 1024 · 0xC63AA = 1024
0xC63AE = 1024 · 0xC6468 = 2639 · 0xC6200 = 8192              <- all BYTE-STOCK on V97 and V98
```
**DISAGREEMENTS: 0.** ⊕ **And an independent WINDOW SWEEP confirms it is exhaustive, not just a
spot-check** — scanning every halfword of `[0xC4040, 0xC40E0)` (the `FUN_0003b8f6` plant-model block),
`[0xC63A0, 0xC63B0)` (the `FUN_00038148` weights + pole), `[0xC6460, 0xC6470)` and `[0xC61FC, 0xC6204)`
against stock returns **`0xC40D2` and `0xC63AC` and NOTHING ELSE.** [EVIDENCE]

⇒ 🛑 **The whole observer / plant-model chain is Honda-stock apart from those two cells** — which is what
makes D3.A-bis's two-level reading load-bearing rather than academic.

## D4.2 — THE THREE CLASSES THE CLOSE-OUT MESSAGE MUST SEPARATE
| class | cells |
|---|---|
| **DELIBERATE and MEASURED** | Lever B (`0x3AA96` + `0xC6446`) — grinding, operator-confirmed |
| **DELIBERATE and INERT / UNVERIFIED** | `0xC40D2`=204 (measured FLAT, 9 builds) · `0x454FE`=0xB5 (measured inert) · `0xC64B8`=0xFF (removes nothing on this car) · `0xC63AC`=150 (uninterpretable) |
| 🛑 **CARRIED BY ACCIDENT** | **`0xD7A5C…70` — the ×1.5 ENGAGED dose, inherited by base choice at V96 and never re-decided** · **`0xC40BC` = 600, back at Honda BY ACCIDENT OF V87's REBASE — and 600 is the BETTER value for ratcheting** · `0xC64DE`=25627, non-stock 76 builds with a disputed label |

## D2 — THE CROSS-BUILD MATRIX: FROZEN COUNTS, read from the images
```
0xC6450  V46's lever                    STOCK 1024   frozen 59 builds
0xC644A  V43's dirty-derivative pole    STOCK 1024   frozen 55
0xC61C0..C4, 0xC64B4/B6  V36 guards     NON-STOCK    frozen 70
0xC64B8  DTC-0x49 gate                  NON-STOCK    frozen 69
the whole V38 authority package         NON-STOCK    frozen 68
0xC6208  (V40 brick cal)                STOCK        frozen 65
0xC6A9A / 0xC6AAE  gain_A rec2/rec3     STOCK        frozen 63
0xC6206  (V40 brick cal)                STOCK        frozen 60
0x3AB76 / 0x3AC20   LEVER A             STOCK 0xAA   frozen 30
0xC6444  r26 engaged arm                STOCK 512    frozen 28   <- FALSIFIED at 3072 (V71c)
0xC407E  hard-fault interlock           HONDA 511    frozen 20
0x454FE                                 0xB5         frozen 18
0x2A1F0 / 0xC62EA / 0xC646C / 0xC6CD0   mixed        frozen 17
0xC63A0  Path-2 damper weight           STOCK 1024   frozen 16
0xC6A72 / 0xC6A74  gain_A rec0          STOCK 3072   frozen 16
0xC40D4  command-branch EMA             STOCK 573    frozen 12
0xC40BC  Coulomb relay normaliser       STOCK 600    frozen 11
0x3AA96 / 0xC6446   LEVER B             NON-STOCK    frozen 10
0xC40D2  K1                             204          frozen 9
0xD7A5C..70  the x1.5 ENGAGED dose      NON-STOCK    frozen 3 (since V96)
0x55DF2 / 0x55E10   427 packer          NON-STOCK    frozen 3
0xC63AC  the Path-2 pole                150          frozen 2 (since V97)
```

## D2 — VIRGIN VERDICTS across all 89 images [EVIDENCE]
✅ **VIRGIN — never written by any build:**
`0xC4080` · `0xC4048` · `0xC40D0` · `0xC40D6` · `0xC40D8` · `0xC63A2` · `0xC63A4` · **`0xC63A6`** ·
`0xC63A8` · `0xC63AA` · `0xC6372` · `0xC636E` · `0xC63B8` · `0xC61D6` · `0xC616C` · `0xC6158` ·
`0xC61DA` · `0xC6316` · **`0xC63F8` (33)** · **`0xC63FC` (328)** · `0xC6B12` · `0xC520C` · `0xC6194` ·
**and ALL FOUR authority-collapse curve records `0xE547C` / `0xE5404` / `0xE52FC` / `0xE5284`.**

🛑 **ONE CORRECTION TO THE RECORD'S VIRGIN LIST:**
`0xC6206` **MOVED at V40 (the brick) and V45** · `0xC6208` **MOVED at V40.** Both are back at stock on
V98, but **they are NOT virgin — anyone citing them as untried is wrong.**

⇒ **Every other virgin claim in D3.C1 is CONFIRMED from the images.** In particular the **10×
left/right ramp-rate asymmetry (`0xC63F8` = 33 vs `0xC63FC` = 328) is VIRGIN on all 89 images**, and the
operator has still never been asked whether the car feels different turning left versus right.

## 🛑 D4.3 — WHY "CARRIED BY ACCIDENT" IS ITS OWN CLASS (the precedent behind D4.2's third row)

- 🛑 **The V38 rebase silently reverted ~~THREE~~ SEVEN levers** — `0x2A1F0` · `0xC646C` · `0xC62EA` ·
  `0xC63A0` · `0x454FE` · `gain_A` rec0 · `gain_A` rec1. **V80-vs-V75 was therefore NEVER a
  single-variable damper comparison, and the confound count is FIVE, not four.**
- 🛑 **V42's ratchet fix was OFF THE CAR from V53 to V79** while the record read as though it were
  carried — *"nobody decided this."*
- 🛑 **V62's grind fix (`0x3AB76`/`0x3AC20`) is carried by V62 and V65 ONLY** — removed as V66's
  confirmatory control and never restored. ⇒ **from V66 to V70 the car carried NEITHER confirmed fix.**
  ★ *"When you remove a confirmed fix to run a control, write the restore into the next build's spec."*
- ⭐ **And the two CURRENT ones, both confirmed from the images this session:** the **`0xCBE74` ×1.5
  engaged dose** (D4.0), and **`0xC40BC` back at 600 by accident of V87's rebase — where 600 is the
  BETTER value for ratcheting**, so the accident happened to run in the right direction.

---
---

# THE ARC IN ONE TABLE — what class each era was, so V99 can be placed

| era | class | outcome |
|---|---|---|
| **V38–V52** | authority · filters · poles · code caves | 3 BRICKS (V24/V27/V48B era + V40); nothing fixed |
| **V53–V61** | telemetry probes + lane mutes | instruments built; `0x14A` byte4 channel proven; mutes null |
| **V62–V73** | **the RATE LANE (r24/r26)** | ⭐ **V62 = the kit's FIRST measured fix, and grinding.** Ceiling reached at V67/V88 |
| **V74–V83a** | **the base-assist DAMPER** | 2 HARD FAULTS (V74/V75) + **V80 = worst grinding ever**. ⚠ **closed on arithmetic ONLY for Honda's stock surface — V75/V76/V80 all flew with both dead zones OPEN (§D1.3c)** |
| **V84–V86B** | damper reverts + a PHASE experiment | V86's pre-registration falsified ⇒ **the linear-loop hypothesis dies** |
| **V87** | ⭐ the first **SUBTRACTIVE** build — strips 49 builds back to V38 | the probe fired; the instrument era begins |
| **V88** | Lever B restored, LKAS-gated | ⭐ **grinding FIXED, command untouched.** The second and last matched success |
| **V89–V90** | the **PLANT MODEL** (a disturbance observer) | V89 FLAT; V90 = the first zero-cell placebo pair |
| **V91–V94** | the `0xCBE74` friction/damping row, UP then DOWN | ×1.5 INERT; **×0.25 ABORTED with a measured sign** |
| **V96–V97** | instrument, then **the arc's first LOOP-POLE lever** | V96's regressor 34× over-range; **V97 UNINTERPRETABLE — no instrument, one episode, DC gain 1.000000** |
| **V98** | ⭐ the first **COMPARATOR** probe — zero cal bytes | flown as route `81`; scoring in progress |

🛑 **What has NEVER been tried as a class — stated after the §D1.3c correction:**
a lever that is **(a) ENGAGEMENT-GATED by construction** (the V62/V88 class, and what §A2's override
result independently supports), **(b) acting in the MICRO regime, 1–13 °/s at <10 km/h, WITHOUT being a
relay in rate** — every build that reached that regime (V75, V76, V80) did so on the **always-on
base-assist path**, i.e. **UNGATED, acting in manual too**, which is exactly the cost the operator felt
on V86B (*"extra dampening on LKAS and in general at slow speed"*) and V81 (*"much heavier when
engaged, even turning WITH the command"*) — **and (c) carrying a comparator or a pre-registered-duty
instrument on its OWN mechanism, readable inside ONE 17 s episode.**

**Every candidate the record leaves standing fails at least one of those three.** That is the honest
statement of where V99 starts.
[**BELIEF** — this is my reading of the partition, not a recorded claim. The three sub-clauses are each
[EVIDENCE]; their conjunction being empty is my inference.]

---

## 🛑 A RECORD DEFECT THAT IS LIVE RIGHT NOW — the EIGHTH instance, and there are TWO STALE LAYERS
`docs/STATE.md:33` reads **"⭐ BUILT AND UNFLASHED: V98"** and `docs/BUILD-LINEAGE.md:51` reads
**"🛑 BUILT, VERIFIED, UNFLASHED 2026-08-12"** — **but V98 FLEW as route `0x81`**, identity proven
single-frame (byte7[7:6] == 2, duty **1.000000 over 17,983 frames**), fault-free.
🛑🛑 **AND THERE IS A SECOND, OLDER STALE LAYER: `STATE.md:400-401` still claims V97 UNFLASHED and V96
ON THE CAR — which contradicts the SAME FILE'S OWN HEAD at line 6.** ⇒ **Trust neither block's flight
status. The V98 image is the authority for D4.**

That is the **eighth** instance of the *"row says UNFLASHED after it flew"* defect (V83a, V84, nearly
V85, V86, V86B, V89, the V94→V96 case, now V98). The V94→V96 instance **cost real work**: it sent the
session's strongest analyst to close a verdict with *"fly V96, S2 answers it"* when V96 had already flown
and its regressor was 34× over-range, so **S1 and S2 were BOTH VOID.**

⇒ **Run `STATE.md`'s own mechanical gate at close-out:**
`grep -n "ON THE CAR\|UNFLASHED\|never flashed" docs/STATE.md docs/BUILD-LINEAGE.md`, reconciled against
the identity bit from the most recent route. **Write the flight row in the SAME pass that scores the
flight.**

## 🛑 COLLATERALS THIS FILE OBLIGES AT CLOSE-OUT
1. **Correct `memory/accord-base-assist-damper-cannot-reach-the-micro-regime.md`** — four of its claims
   are refuted from the images (§D1.3c). It is ★★ in `MEMORY.md` and currently forecloses a lever class
   with **three flights** behind it.
2. **Correct the `0xC6444` entry in `accord-rate-lane-builds-were-never-single-variable`** — it calls the
   cell *"UNTESTED: a candidate"*; it is **FALSIFIED AND REVERSED** (flew as V71c).
3. **Record that `0x454FE` is MEASURED INERT**, superseding the 2026-08-04 note calling it *"a genuinely
   UNTESTED lever for the ratchet."*
4. **Record that V47's *"marginally quieter at 5 mph"* whisper is INERT-BY-MODE** (V47 wrote modes 10/11)
   and cannot be revived as a damper lead.
5. **Resolve or flag the wheel-order clean-window inconsistency** (D6.1, last row).
6. **V91/V92 (routes `78`/`79`) and V96 (routes `7e`/`7f`) have NO operator symptom report on record.**
   Either recover them or mark the gap explicitly — four flights with no symptom column.
