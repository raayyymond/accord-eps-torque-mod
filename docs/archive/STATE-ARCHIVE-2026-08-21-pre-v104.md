# STATE ARCHIVE — sections moved out of `docs/STATE.md` on 2026-08-21 (pre-V104 close-out)

**This is a RECORD, not an instruction.** It was moved to keep `STATE.md` under the ~150 KB working
target (hard cap 256 KB — past the `Read` limit a file loads with its tail SILENTLY TRUNCATED).
Nothing here was edited; it is verbatim. **Current state lives in `docs/STATE.md`.**
Contents: archived flight headlines (V88/V91/V92/V94/V96), the standing corpus results from the
2026-08-09 V89 session, the standing instrument corrections, the methodology and signal-identity
corrections, the tyre line, and the superseded on-the-car block.

---

## ⚠ ARCHIVED 2026-08-13 (later still) — V96's flight headline

V96 flew as routes `7e`/`7f`, both fault-free; its instrument under-ranged 34× (S1/S2
void, later closed analytically). V96's calibration (revert-by-construction of V94's
cut) is carried forward byte-for-byte through every build since — see the frozen-count
matrix in `docs/archive/arc-maps/_v100_arc_map.md` §1 and `docs/BUILD-LINEAGE.md`'s V96 row for the full
detail. **Full original section moved verbatim to**
`docs/archive/STATE-ARCHIVE-2026-08-13-v96-to-v99.md`.

---

## ⚠ ARCHIVED 2026-08-13 (later still) — V94's flight headline

V94 flew as route `7d` and was aborted by the operator (*"it vibrated the entire car"*);
it is no longer on the car. **Its durable findings survive in full**, unarchived, at
`memory/accord/builds/accord-v94-flew-and-the-lane-is-a-damper.md` (the damper-removal mechanism,
`Re(Z)` measured +518/+565 ct positive) and
`memory/reference/measurement/reference-accord-steeringpressed-mask-excludes-the-symptom-regime.md` (the
engaged+hands-on+override regime finding, 10/10 routes). **Full original section moved
verbatim to** `docs/archive/STATE-ARCHIVE-2026-08-13-v96-to-v99.md`.

---

## ⚠ ARCHIVED 2026-08-13 (later still) — routes 78/79 (V91/V92) headline

Superseded by the 2026-08-12 V94/V96 block (itself archived above). See
`docs/BUILD-LINEAGE.md`'s V91/V92 rows (corrected 2026-08-13, record-repair pass) for
current flight status. **Full original section moved verbatim to**
`docs/archive/STATE-ARCHIVE-2026-08-13-v96-to-v99.md`.

---

## ★★★★ STANDING CORPUS RESULTS (from the 2026-08-09 V89 analysis session) — still the live evidence base

**Superseded as the headline by the 2026-08-11 block above; the findings below are NOT superseded.**
Narrative: `docs/handoffs/2026-08/HANDOFF-2026-08-09-v89-the-rate-axis.md`.

### 0. ★★★★★ THE NEW INPUT — the operator separated the symptoms, and the separator is STEERING RATE
> *"micro-ratcheting and ratcheting when LKAS is engaged and spinning the wheel **at all**
> (micro-ratcheting) and **quickly** (ratcheting), respectively. Macro-ratcheting is on **large
> steering angle transients**."*

Every ratchet measurement in this kit had been stratified by **vehicle speed**. The operator's axis
is **wheel rate**, and in this corpus the two are strongly anti-correlated (**corr(log rate, log
speed) = −0.640** engaged) — you spin the wheel in a car park, not at 116 km/h. ⇒ **D5's headline
"the ratchet decays 4.8× from creep to highway" is partly a RATE effect read as a SPEED effect**:
the creep stratum's median |rate| is **13 deg/s** against the highway stratum's **1 deg/s**.

### 1. ★★★★★ THE FULL CORPUS — 30 routes, 284 min, 235 episode blocks
🛑 **The 12-route version of this section was WRONG and is replaced.** The operator caught it: the
loader globbed only `_cache_r*/r<NN>.npz` and **skipped every PER-SEGMENT cache**, seeing ~180 min
of ~417 min on disk. `studies/sessions/v89/v89_c1_full_corpus.py` now loads 30 routes (10 Lever-B, 20 not) —
**235 episode blocks against the earlier 93.** Route→build is documented; ambiguity is harmless
because Lever B exists only from V67, so every pre-V67 route is unambiguously Lever-B = no.

`studies/sessions/v89/v89_c2_powered_discriminator.py`, band contrast = 6–9 Hz minus the 32–38 Hz control, same windows:

| term | 6–9 Hz | control | **band contrast** | verdict |
|---|---|---|---|---|
| **`eng`** | **+1.015 [+0.713, +1.302]** | +0.602 [+0.392, +0.810] | **+0.413 [+0.146, +0.667]** | **EXCLUDES 0** |
| `eng × log rate` | +0.133 [−0.005, +0.261] | +0.112 [+0.014, +0.195] | **+0.022 [−0.070, +0.116]** | **NULL — and it REFUTES the 12-route +0.144** |
| `eng × log rate × LeverB` | +0.124 | +0.049 | +0.075 [−0.099, +0.245] | inconclusive |
| `eng × DAMPER` | −0.091 | −0.105 | +0.014 [−0.483, +0.386] | NULL, refutes ±0.413 |
| **`log hands`** | **−0.655 [−0.750, −0.525]** | −0.266 [−0.323, −0.196] | **−0.389 [−0.471, −0.290]** | **EXCLUDES 0** |

⇒ ★★★★★ **[EVIDENCE] ENGAGING LKAS MULTIPLIES THE 6–9 Hz COLUMN MODE BY 2.8×, AND BY 1.5× MORE THAN
IT MULTIPLIES A CONTROL BAND.** A **constant, band-specific, engagement-gated amplification.**
⇒ 🛑🛑 **[EVIDENCE] IT DOES NOT GROW WITH WHEEL RATE.** The rate term is the same in both bands
(+0.133 vs +0.112). **The earlier "+0.144, the operator's axis is band-specific" claim is RETRACTED
— refuted by 2.4× the data.** What *does* grow with rate is the EXCITATION (`log rate` main effect,
present in every band): turn the wheel faster, feed the mode harder. Engagement then multiplies it
by a constant 2.8×. **Both compound, which is exactly why he feels more of it when spinning fast —
but the firmware term itself is NOT rate-dependent.**
⇒ ★★★★★ **THEREFORE: NOTHING HERE ARGUES FOR LIMITING THE LKAS COMMAND'S ANGLE RATE.** The target is
a constant gain, not a rate. **The operator's constraint and the measured target agree.**
⇒ ★★ **[EVIDENCE] The mode is strongly damped by FRICTION AT THE COLUMN** — `log hands` −0.655 vs
the control's −0.266, CIs disjoint. Confirmed independently in §1b.

### 1b. ★★★★★ THE MECHANISM, AND IT INVERTS A STANDING RECOMMENDATION — `0xC40BC`
On V87/V88 **stock modes 24 ≡ 26 are byte-identical in all six factor families**, so engaging
changes **no calibration at all**. The only change is the LKAS command entering the aggregator ⇒ a
constant 2.8× amplification must come from the command's ENTRY moving the loop through a
**nonlinearity**. There is exactly one on record: **`FUN_0003b8f6`, a Coulomb relay PROPORTIONAL TO
THE COMMAND**, whose `ratio` saturates against gate **`0xC40BC`** — pinned across 99.62 % of its
range at the stock gate, i.e. a pure relay. Raising the gate widens the linear region and
**de-relays** it.

```
0xC40BC =  600   stock, V87, V88  -- THE CAR RIGHT NOW
0xC40BC = 6000   V85, V86, V86B only (routes 6e, 6f, 70)
```
`studies/sessions/v89/v89_c3_friction_relay.py`, identified **within-route** (the flag is constant per route, so only the
engaged-vs-manual gap carries it — route fixed effects absorb everything else):

| `0xC40BC` | engaged/manual 6–9 Hz amplification |
|---|---|
| **600 — stock, and on the car** | **2.89× [2.14, 3.92]** |
| **6000 — V85/V86/V86B** | **6.58× [3.19, 13.14]** |

**`eng × FRIC6000` band contrast = +0.682 [+0.213, +1.166] — EXCLUDES 0, and it is POSITIVE.**

⇒ 🛑🛑 **DE-RELAYING THE COULOMB FRICTION TERM MADE THE RATCHET BAND 2.3× WORSE.**
⇒ 🛑🛑 **`STATE.md`'s standing "FREEZE `0xC40BC` at 6000" is CONTRADICTED on the 6–9 Hz band.** It was
set on relay-saturation duty and other bands. **The car is at 600 and that is the better value for
ratcheting. Do not restore 6000.**
⇒ ★★★★★ **TWO INDEPENDENT LINES NOW AGREE: COULOMB FRICTION AT THE COLUMN DAMPS THIS MODE** — the
driver's own grip (−0.655) and the firmware's own friction relay (600 beats 6000 by 2.3×).
**⇒ THE LEVER CLASS IS "MORE COLUMN FRICTION / DAMPING", NOT "LESS COMMAND".**

⚠ **Scope, honestly:** the flag lives on **3 routes**, all from one era, and **V86 also moved
`0xC40D4`** (573→286) while **V86B armed the damper**. The model carries damper and Lever-B
interactions and both come back inconclusive-to-null, but `0xC40BC` **cannot be fully separated from
V86's `0xC40D4`**. The *association* is EVIDENCE; **attributing it specifically to `0xC40BC` is
BELIEF.** ⚠ And the instrument measures **6–9 Hz band energy, not "feels smooth"** — more Coulomb
friction can reduce the oscillation while making the wheel feel notchier. **The operator scores that,
not the instrument.**

### 2. 🛑🛑 TWO OF THIS SESSION'S OWN READINGS RETRACTED BY THEIR OWN CONTROLS
1. **"The rate axis is band-specific to the ratchet"** — `v89_a1` found `e_6-9` slope **+0.490** and
   `e_18-22` **+0.039**, which looked decisive. **It was an ARTEFACT of order-vetoing each band on a
   DIFFERENT window set.** On matched windows (`v89_a2` T2) the slopes are **+0.492 / +0.385 /
   +0.400** and the contrast CI **includes 0**. **Spinning the wheel raises the WHOLE column
   spectrum**, so a rate slope alone can never separate firmware from driver. Only the
   engaged-vs-manual **interaction** in §1 does.
2. **The binned engaged/manual dose curve (2.09× → 21.17×, `v89_a4`)** — **inflated by two
   confounds its own controls caught.** K2: at 8–50 deg/s the MANUAL arm carries **~9× the sustained
   column load** (1724–1878 ct vs 193–201) — slower, heavier parking, and a hard-gripped wheel is
   damped by arm impedance. K4: only 5 routes contribute any cell and they contribute to **different
   bins**, so a build effect can masquerade as a rate trend. 🛑 **Quote §1's model numbers
   (1.16×→3.94×), never the 21×.**

### 3. 🛑 `cmd → column` COHERENCE IS NOT AN ATTRIBUTION INSTRUMENT — dropped, with the reason
`gp-0x6b98` is the **TOTAL motor command, base assist included**, and base assist is a function of
column torque. Its 6–9 Hz coherence with the column is **0.254 engaged but 0.544 MANUAL**, where the
LKAS command is identically absent. **That is loop feedthrough, not attribution.** The road channels
(`imu_vert`/`imu_lat`/wheel-speed roughness) sit **at their shuffled controls in the engaged arm**.
⚠ This also bounds the V88 handoff's own §5 coherence table — the honest carrier there was always
the prominence contrast (52 % vs 13.3 %), as its scoring agent said.

### 4. 🛑🛑 THE BASE-ASSIST DAMPER IS CLOSED AS A MICRO-RATCHETING LEVER — on arithmetic, not on a null
`analysis-2020accord/studies/sessions/v89/v89_b1_damper_surface.py`, read from V88's own image.
`ch₀ = clamp((FactorC(speed) × FactorE(rate)) >> 10, ±ceiling)` has **two MULTIPLICATIVE dead zones**:

```
FactorC  X=[2240,3840,5120,8960] ct = [35,60,80,140] km/h    Y=[0,234,429,908]   <- 0 below 35 km/h
FactorE  X=[  60, 400,2500,4000] ct = [12.7,84.9,530,849] °/s Y=[0,140,539,927]   <- 0 below 12.7 °/s
```
Mode 24 ≡ 26 and 25 ≡ 27, byte-identical on V88. Against route 73's measured engaged distribution:
**the damper contributes exactly ZERO on 95.91 % of engaged frames**, and on **100.0 %** of the
operator's micro-ratcheting regime (229 s at |rate| 1–13 deg/s) and **100.0 %** of his ratcheting
regime at parking-lot speed (131 s).

★ **AND NEITHER PRIOR TEST EVER HAD BOTH ZONES OPEN** — a RULE-5 failure against a *product*:
- the **`FactorE X[0]` lever was withdrawn as "structurally vacuous"** because FactorC was 0 at creep;
- **`FactorC Y[0]` WAS tested, as V86B on route 70**, lifted to the record's own `Y[3]` (908/875) —
  but **FactorE stayed 0 below 12.7 deg/s**, so V86B armed the damper only for *spinning quickly*,
  never for *spinning at all*. Operator on V86B: *"extra dampening on LKAS and in general at slow
  speed"* — the cost was felt; the micro regime was never armed.

🛑 **But sizing kills it anyway.** With FactorC `Y[0]` lifted AND `FactorE X[0]` 60→12, `ch₀` at
creep reads **0 / 3 / 10 / 25** counts at 2 / 5 / 10 / 20 deg/s. Reaching even 25 % authority (256)
at 10 deg/s needs `FactorE(10 °/s) ≥ 288` — **unreachable by moving X; it requires raising `Y[0]`
off zero, which is a STEP AT ZERO RATE = a relay in rate = the V78/V79/V80 move, recorded as
"WORST GRINDING EVER".** ⇒ **Do not propose the damper for micro-ratcheting. Cal-only, it cannot
deliver.**

### 5. ⇒ WHERE V89 STANDS — the lever must be ENGAGEMENT-GATED **and** RATE-DRIVEN
§1 says the firmware's contribution scales with wheel rate. That is a **structural filter on
candidates**, and it is new. Ruled out or already spent:

| candidate | status |
|---|---|
| command-side HF reduction (Lever B class) | 🛑 **measured NON-fix** — V88 halved 15–22 Hz command content, ratchet `e_6-9` V88/V67 = 1.040 [0.759, 1.260] |
| a bigger `0xC6446` dose | 🛑 blocked by the ±8192 rail (2.5× at the rail hot-end, 3× pins) **and** the elasticity failed its out-of-sample dose test |
| base-assist damper (FactorC/FactorE) | 🛑 **closed this session** — §4 |
| FactorD / `gp-0x6a10`, `0xC64C8` m2, `0xC61F6`, a pole on r24, `0xC63B8` | 🛑 all previously killed on structure |
| **the r24 engaged arm ITSELF** | ⏳ **the one untested candidate that fits §1** — Lever B makes r24's gain switch on `gp-0x6806` from 2622 to **5244 when LKAS applies**, i.e. the firmware already contains an *engagement-gated, rate-derivative* gain. **Every build has pushed it UP. §1 says test it DOWN.** |

### 5b. 🛑 THE LEVER-B DISCRIMINATOR, ON THE FULL CORPUS — still inconclusive, but no longer exposure-blocked
`eng × log|rate| × LeverB` band contrast **+0.075 [−0.099, +0.245]** over 235 blocks; `eng × LeverB`
**+0.274 [−0.094, +0.652]**. Both still fail to resolve the effects they are testing.
🛑 **But the reason has changed and it matters:** the earlier "we need 4× the exposure, design a new
drive" recommendation was **based on a loader bug, and is withdrawn.** The corpus is 2.4× what that
glob saw and the answer did not sharpen ⇒ **more of the same driving will not settle Lever B.**
⊕ It also no longer matters much: §1 shows the amplification is **not rate-dependent**, which was the
whole reason r24 (a rate derivative) was the lead candidate. **r24's engaged arm is demoted, and
§1b's friction line replaces it.**

### 6. ⏹ SUPERSEDED — V89 flew (routes `75`/`76`) and V90 (route `77`) carries its K1 unchanged
The "BUILT, VERIFIED, UNFLASHED" block that stood here is superseded by the flight results and moved
verbatim to `docs/archive/STATE-ARCHIVE-pre-V89.md`. **What survives and is still load-bearing:**
`0xC40D2` = **204** is on the car and stays there · `0xC40D2` is **1 reader / 0 writers** (`0x3BAFE`
in `FUN_0003b8f6`), censused twice through the `hw2 = disp|1` trap that returns a **false zero** on a
naive scan · 🛑 **`0xC4080` (K0, the NEVER-RAISE pure-relay hazard) is untouched at 0** — K1 scales
the `|model|` arm alone and is **not** the V80 class.
**On-car verdict: FLAT** (order-clean stratum contrast 0.947 [0.827, 0.979] inside a same-build
placebo band of [0.900, 1.111] = 0.92σ), and V90's data says why **structurally**: above 1 °/s
friction and `|model|` are near-collinear (headline §B). 🛑 **The block-bootstrap CI excluded 1.00 and
would have been reported as a resolvable 5 % fix — the placebo control earned its keep on first use.**

### 6b. ✅ THE POLARITY IS VERIFIED — V89's HOLD IS LIFTED. More modelled friction ⇒ MORE assist
The operator asked *"I thought we didn't want friction… how do we know it's modelling friction?"* and
the second half of that exposed an unverified sign. It is now traced end to end, every link read in
Ghidra on stock `code.bin`.

**THE TERM IS COULOMB FRICTION — five ways, four of them independent of this session:**
1. **Form.** `friction = |model| × sign(polarity × gp-0x6abc) × K1/1024` = `F = μ·N·sign(v)`.
2. **The sign IS a velocity sign.** `FUN_00041464` @`0x4170C`: `gp-0x6abc ← gp-0x4f50`, which
   `STATE.md`'s own signal table calls the **resolver/motor ELECTRICAL RATE**.
3. **Its companion is INERTIA** — a term ∝ `d(rate)/dt` scaled by `0xC646E`, a cal the kit's own
   FROZEN lists already label **"INERTIA gain"**. Applied torque − friction − inertia = a mechanical model.
4. **The record named it first:** V87's `BUILD-LINEAGE.md` row already calls `gp-0x6b70`
   *"the Coulomb friction compensator"* and measured it on-car — **non-zero 99.80 %, negative 67.19 %,
   aggregator optional-term gate OPEN 100 %.**
5. ⊕ **Coulomb friction is rate-INDEPENDENT by definition**, and §1 measured the engagement effect as
   rate-independent (+0.022 [−0.070, +0.116]). **Independent corroboration nobody designed for.**

**THE SIGN CHAIN, link by link:**

| # | where | effect of raising K1 |
|---|---|---|
| 1 | `0x3BBC2` `subf.s r10,r8,r8` — friction is **subtracted** from the model | model out **↓** |
| 2 | `FUN_0003bc20` plausibility ±20000 → `gp-0x6bfe` | ↓ |
| 3 | `FUN_00038148` `residual = MODEL − ACTUAL` | ↓ (already 67 % negative) |
| 4 | `gp-0x6b70 = sign(res) × LERP(\|res\|)` | **more negative** |
| 5 | `FUN_00037fe6`: `gp-0x6ad6 = (… + gp-0x6b70) × LERP >> 10` — lane ENABLE flag `0xC64B0` = 1, unit weight | **↓** |
| 6 | `FUN_0003a382`: `error = gp-0x4f60 (measured driver torque) − clamp(gp-0x6ad6)` | **↑** |
| 7 | PID (P, I, D all positive-coefficient) → `gp-0x6ad4` | **↑** |
| 8 | `0x3ACA8` `ld.h -0x6ad4[gp],r6` → windowed → **`mov`, `add`×8, no negation** → `0x3AD20 st.h r10,-0x6b94[gp]` | **↑** |
| 9 | `gp-0x6b94` → governor → `gp-0x6ace` → comp-add → `gp-0x6acc` → shaper → `gp-0x6b98` → motor | **more assist** |

⇒ ✅ **MORE MODELLED COULOMB FRICTION ⇒ MORE ASSIST ⇒ A LIGHTER WHEEL, NOT A HEAVIER ONE.**
**V89 does not fight the LKAS demand — it assists it.** The operator's constraint is satisfied in the
favourable direction, and the earlier "may feel notchier/heavier" caveat is **withdrawn as stated**.

★ **And the physics is right.** `gp-0x6ad6` is a **torque-tracking REFERENCE**, not a torque added to
the motor. The loop holds the driver's *felt* torque at that target. Telling it the plant has more dry
friction **lowers the target driver effort**, so the PID delivers more motor torque to hold the felt
torque down. And because Coulomb friction **flips sign at every wheel reversal**, an estimate that is
wrong by a constant produces a **step error at every reversal — which is what a ratchet is.**

🛑 **THE ONE HONEST CAVEAT — V56 muted this exact lane and got a null.** `0xC6AFC`/`0xC6AFE`
32768 → 0 killed the whole `FUN_0003a382` → `gp-0x6ad4` output bound, and the memory says the lane is
*"ELIMINATED as the driver… do not re-propose"*. **But that null was scored on `P[15–26 Hz]` — the
20–25 Hz mode — NOT on 6–9 Hz**, and route `24` is **not on disk**, so the ratchet band was never
scored against it. `0xC6AFC`/`0xC6AFE` = 32768 on **all 30 other builds**, so the corpus cannot test
it either. ⇒ **The elimination is BAND-SCOPED and is being carried as if it were general.** That is a
real risk to V89's thesis and it is not resolvable from the data on hand — **it is what the flight tests.**

🛑 **CORRECTION — THE OFF-BY-0x1000 TRAP, FIFTH RECURRENCE.** An earlier draft of this section said
*“lane weight `0xC74B0` = 32, siblings 176/161/14/14”*. **Wrong region.** `tp` = `0xBF000`, so
`tp+0x74B0` is **`0xC64B0`**. The real cells are `0xC64AD..0xC64B3` and they are **0/1 ENABLE FLAGS,
all = 1** — exactly as this file already recorded. Likewise the observer's ACTUAL-side gains are
`0xC63A0..0xC63AE` (all 1024 = unity, EMA α `0xC63AC` = 102 — *the same “Path-2 IIR” the V88 handoff
discusses*), and `gp-0x6b70`'s clamp is `0xC6200` = **8192**, not 41064.
✅ **The sign chain is UNAFFECTED** — the lane still enters with a `+` at unit weight. Only the weight
characterisation was wrong.
🛑 `builds/v80_v107/build_v83a_tva.py` carries an assertion naming this exact trap (*“tp+0x73A0 is 0xC63A0, NOT
0xC73A0 — the off-by-0x1000 trap has recurred four times”*) **and it still happened.** A warning in one
build script does not protect a session that never opens it. ⇒ **compute `tp+off` in code, never by eye.**
⚠ Still unsized: `gp-0x6b70`'s magnitude response to the dose — the LERP it passes through lives in
**RAM** (`gp-0x64b8`/`gp-0x641c`), so the transfer cannot be read from the image.
⊕ Method note: the orchestrator hand-decoded the `add` field split with a Format-VII layout on a
Format-I instruction and got nonsense. **Ghidra's listing is the authority** — `mov`, eight `add`s,
no `sub`/`subr`/`negf` in the accumulator. This is exactly the standing "assembly CONFIRMS, it does
not FORM" rule doing its job.

### 7. ⏹ SUPERSEDED — the V89 pre-registration, and how it scored
Full text moved verbatim to `docs/archive/STATE-ARCHIVE-pre-V89.md`. Outcome: **IDENTITY PASS · H1 (probe
fires) PASS · 🛑 H2 (THE LEVER) FAIL — no band-specific fall survives the order veto · H3 (the
operator's constraint) PASS, no sign-chain inversion · H4 the operator: *"fixed nothing, still only as
good as V88."*** The honest label held: the dose *direction* was measured, "K1 acts like the gate" was
BELIEF, and the null landed on the BELIEF.
⊕ **What the flight added that the pre-registration could not**: V89's own probe showed the friction
term is `sign(motor rate)`-gated and `|friction| ≥ 0.0625` on only **0.9 %** of micro-ratcheting
frames — **arithmetic saying the lever was pointed away from the target**, a fifth independent
confirmation that the term is Coulomb friction, and **not** a falsification of the friction account.
V90 then added the sixth (the rate-gate visible directly in the (b6,b5) 2×2 below 1 °/s).

### 6. ✅ COLLATERAL — `STATE.md` size discipline
See the cap note at the top of this file. `CLAUDE.md` carries the rule now.

---

## ⚠ ARCHIVED 2026-08-13 (later still) — V88's flight headline

V88 flew as route `73`, fault-free — the grinding fix (Lever B restored + the sign-fix
probe), still on the car (carried through every build since, frozen 11 builds per
`docs/archive/arc-maps/_v100_arc_map.md` §1). Operator: grinding fixed; micro-ratcheting and ratcheting
"the main remaining issues." **Full detail — the identity proof, the H1/H2 confirmations,
the raw14 off-by-one instrument defect — is in `docs/BUILD-LINEAGE.md`'s V88 row and**
**`docs/archive/STATE-ARCHIVE-2026-08-13-v96-to-v99.md` (moved verbatim).**

---

## 🛑 STANDING INSTRUMENT CORRECTIONS — they apply to every analysis in this file

### 🛑🛑 NAMED TRAPS ADDED 2026-08-11 (the V90 flight session) — eight, each of which changed or would have changed an answer

**1. 🛑🛑 THE RATE-CHANNEL RULE, AND ITS SCOPE. Getting this wrong INVERTS a build decision.**
- **For PHASE and IMPEDANCE work use the `0x18F`-sourced rate (`rate_f`).** `tq` and `rate_f` are both
  fields of the **same held `0x18F` frame** (`last18[0]`/`last18[1]` in the extractor), so the ~9.15 ms
  staleness is common to numerator and denominator and **cancels exactly** in `Z = S_Tω/S_ωω`.
  **Proved, not asserted:** recomputing `Z` with `rate_c` separates the phase by exactly the skew
  (−11.1° vs −9.9° predicted at 3 Hz; −100.1° vs −93.9° at 28.5 Hz; −116.6° vs −108.7° at 33 Hz).
  > **Had `rate_c` been used, 26–31 Hz would read −30.3° instead of +69.6°, giving `+0.184 PUMPING`
  > instead of `−0.336 DAMPING` — the OPPOSITE BUILD DECISION, from the same data, at the same
  > coherence (0.827 vs 0.834). Same flip at 18–22 Hz (+45.8° ⇒ +0.180 PUMPING).**
- 🛑 **But for ABSOLUTE MAGNITUDE use `rate_c` (`0x14A`).** Regressed on the differentiated angle
  (`0x14A`, 0.1 °/count — a solid LSB anchor) over four routes:

  | channel | slope vs d(angle)/dt | r |
  |---|---|---|
  | **`rate_f` (`0x18F`)** | **0.743 · 0.756 · 0.763 · 0.767** | 0.96–0.98 |
  | **`rate_c` (`0x14A`)** | **0.952 · 0.958 · 0.962 · 0.963** | 0.98–0.99 |

  ⇒ **`rate_f` reads ~24 % LOW.** The kit's old "~25 % low" note is confirmed and **pinned to that
  channel specifically.** ⇒ 🛑 **STATE WHICH CHANNEL YOU USED, EVERY TIME.**

**2. 🛑🛑 A SAME-FIRMWARE PLACEBO PAIR IS MANDATORY FOR ANY CROSS-BUILD CLAIM — and the band contrast
does NOT rescue a thin cut.** V90 changes no calibration cell, so route 77 vs 75/76 is the **same
firmware on different drives**:

| pair (SAME FIRMWARE) | `e_6-9` | `e_18-22` | `e_32-38` (control) |
|---|---|---|---|
| **r77 ÷ r75** | **1.288 [1.017, 1.661]** — CI **excludes 1** | 1.121 [0.870, 1.472] | 0.993 [0.807, 1.189] |
| r77 ÷ r76 | 1.340 [0.925, 2.259] | **1.333 [1.001, 2.307]** — CI **excludes 1** | 1.379 [0.977, 2.164] |

**Two drives on byte-identical firmware return band ratios whose episode-block CIs exclude 1.00, and
one of them excludes 1.00 on the BAND CONTRAST as well.** ⇒ the honest resolution floor is
**±16–22 %** (32–38-contrasted) to **±33 %** (raw ratio). **Any cross-build ratio quoted with a
block-bootstrap CI and no placebo-pair null is over-confident.**

**3. 🛑 A BYTE-DIFF REPORTS THE FIRST DIFFERING BYTE, NOT THE CELL ADDRESS.** If a `u16`'s low byte is
unchanged, the run starts **one byte INTO the cell**. This produced off-by-one addresses for the
corridor/boost walls (`0xC674E/50/5A/5C`, floats `0xC6598/9C/AC/B0`) and the clamps
(`0xC61B2`/`0xC61B4`). **THE TELL IS THE VALUE**: the real cell reads a clean **512 → 2048** or
**1024 → 5120**; the off-by-one reads **2 → 8** and **4 → 20** — nonsense as calibration values.
⇒ **plausibility-check the VALUE, not just the address.**

**4. 🛑 AN ARRAY SWEEP MUST BE BOUNDED BY THE ARRAY'S OWN RECORDED EXTENT.** `range(32)` on a 34-slot
array **hid two modes**; "walk until it stops looking valid" **over-walked into `gain_B` and invented
two** (a prior walk reached "mode 289" and reported phantom differences at "modes 68/126", which are
`gain_B` array 0/1 mode 10). **The friction pointer array is 34 slots, modes 0–33.
`0xCBE74 + 34*4 = 0xCBEFC` is the FIRST SLOT PAST IT** — and it holds `0x000DAA44`, a perfectly
valid-looking pointer to a perfectly valid-looking `n=3` record. **A guessed bound is not a bound, and
neither is an exhaustion walk.**

**5. 🛑 `searchsorted` ON `logMonoTime` SILENTLY MISPAIRS ROWS — AND THE TIMESTAMP CHECK STILL PASSES.**
`evt.can` can carry **two `0x14A` frames in one event**, sharing `logMonoTime` *exactly* — **3,018
duplicate raw14 timestamps on r77** — so `searchsorted` collapses onto the first of each tie and
**mispairs 1,604 rows.** **Only a BYTE check catches it.** ⊕ The correct fix for the kit-wide `raw14`
off-by-one is that the map is a **constant lead** (= 1 on r77), derived and asserted elementwise
against both `raw14_t` and `raw14_b4` and stored as `row2raw14` in the npz
(`rlog-tools/decode/extract_r77.py::_row2raw14`) — **not** a timestamp reconstruction.

**6. 🛑 `_r31_common.runs_of` RETURNS A GENERATOR.** The first consumer exhausts it and **every later
consumer silently sees ZERO windows.** This produced an all-NaN shuffled control on the first D3 pass
— **and a NaN control reads as "no control available", not as a bug.** Materialise with `list()`.
Worth auditing anywhere `runs_of` is passed to more than one estimator.

**7. 🛑 `np.interp` ON `raw14_b4` INTERPOLATES A BITFIELD.** `v88_d1_exposure.grid` does this; the
interpolated values have **meaningless bits**, so any bit test reading `g["b4"]` is suspect. Pair
nearest-within-10 ms instead.

**8. 🛑 A GROUP-DELAY SIGN IS A REQUIRED SCREEN FOR ANY TRANSFER QUOTED FOR SIZING.** Forward causation
*requires* the response to LAG the input, so a **negative group delay is positive proof of
feedthrough.** `|tq/b26|` = **17.76 ct/ct at 6–9 Hz**, coh² 0.289 against a shuffled 0.000 — the best
transfer on the route — **is feedthrough: the column LEADS `gp-0x6b26` by 48.8 ms.** Disqualified for
sizing. The **only** band that survives is **15–22 Hz** (2.64 ct/ct, −42.1°, coh² 0.333 vs shuffled
0.000, group delay **+6.3 ms**) — ⚠ **and even that is a closed-loop correlation that merely failed a
one-sided test, not a proven plant gain.**

⊕ **NINTH, re-measured this session: THE WHEEL-ORDER VETO'S SCREENING ASYMMETRY INVERTS AT HIGHWAY.**
With circumference 2.073–2.088 m and guard 0.8 Hz, order *k* reaches a band over
`v ∈ [(lo−0.8)·2.073/k, (hi+0.8)·2.088/k]`: **6–9 Hz** is clean only above **20.46 m/s** (18.8 is
*not* conservative enough) · **18–22 Hz** — order 2 covers 17.83–23.80 m/s, clean only above 47.6 m/s
(171 km/h) · **32–38 Hz** — order 3 covers 21.60–27.00 m/s, clean only above 81 m/s.
⇒ **No speed stratum is clean for all three bands at once, and above ~21.6 m/s it is the 32–38 Hz
NEGATIVE CONTROL that order 3 contaminates.** Measured on the v ≥ 22.2 arm: **18/205 order hits on
18–22 Hz but 76/205 on the 32–38 control.** ⇒ **use a SYMMETRIC veto** — drop a window if any order
1–6 lands on **any** scored band's own measured line. **Per-band vetoes build different window sets
per band and turn a contrast into a comparison of two different sets.**

**🛑🛑 10. A VERIFIED ARTEFACT FOR A SUPERSEDED DESIGN IS *MORE* DANGEROUS THAN AN UNVERIFIED ONE.**
Everything about it looks correct — **including its assertion log.** And **a hash reported in a
transcript OUTLIVES the artefact it names**: a future session greps the transcript, finds a SHA256 with
every assertion passing, and has no way to tell the artefact is dead.

> ⇒ **WHEN A BUILD IS RE-CUT, THE SUPERSEDED HASHES MUST BE EXPLICITLY NAMED DEAD IN THE RECORD, NOT
> MERELY OMITTED FROM IT.**

**Stripping stale hashes from the docs is NECESSARY AND NOT SUFFICIENT** — omission is invisible, a
DEAD marker is not. **The instance:** a real, fully-verified V92 cut (**182/182 assertions, from-disk
verified**, image `b092bf19…`, rwd `630248a5…`) carried the **old rung map** and was superseded before
flight; **the only tell left in the transcript was a `6ABC` token buried in the old filename**, which
reads as a warning only to someone who already knows a swap happened. See §E for the full DEAD marker.
🛑 **AND WRITE THE DEAD HASH OUT IN FULL.** The search that will actually be run is a **paste of the
full 64-char string out of the transcript** — a truncated or prefix-only entry in the record returns
**nothing**, so the marker fails at exactly the moment it is needed. **Full string, next to the word
DEAD.**
⊕ **The BUILDER caught this itself and pushed back on the orchestrator's own proposed filename, which
had mischaracterised the superseded artefacts as a "dry run". They were a real cut — and that
distinction IS the hazard.** Same pattern as this session's other catches: the correction came from the
agent that owned the artefact, against the orchestrator's description of it.
⊕ **Corollary for the `SUPERSEDED-DO-NOT-FLASH-…` rename this kit already does:** the rename fixes the
**filesystem** and does nothing for the **transcript**. Both need doing.

### 🛑 THE `0x18F`-vs-`0x14A` SKEW — SETTLED AT SOURCE, 2026-08-10, AND THE MAGNITUDE IS NOT 10 ms

The long-standing *"`0x18F` is one frame (~10 ms) stale vs `0x14A`"* is **CONFIRMED**, but it was never
measured until now, it survived one wrong withdrawal and two wrong discriminators, and **its size is
~9.15 ms, not 10.0**.

**Mechanism [EVIDENCE, from the extractor].** `extract66()` appends a row on a **`0x14A`** frame while
holding `last18`, so **the order of messages inside `evt.can` decides everything**. `tm` is
`evt.logMonoTime` — **per-event, not per-message** — so co-logged frames share it exactly.
```python
for m in evt.can:
    if   addr == 0x18F: raw18_t.append(tm); last18 = (...)          # updates the hold
    elif addr == 0x14A: raw14_t.append(tm); rows.append((tm, ..., last18[0], ...))
```
**Measured over 51,691 co-logged events across r73/r75/r76** (`rlog-tools/studies/v91-v94-dose/v89_i1_can_order.py`, one
pass straight from the rlogs): **`0x14A` precedes `0x18F` on 91.28 %** (per route 91.61 / 90.52 /
91.71 — no route is special). ⇒ the row usually carries the **previous** `0x18F`.

🛑 **It is a MIXTURE, not a pure delay**, and nobody was accounting for the amplitude term:
`H(f) = 0.9128·e^{−j2πf·0.01} + 0.0872`

| f | pure 10 ms | **effective** | effective delay | \|H\| |
|---|---|---|---|---|
| 3.00 Hz | −10.80° | **−9.86°** | 9.13 ms | 0.999 |
| **7.79 Hz** | −28.04° | **−25.67°** | **9.15 ms** | 0.991 |
| 21.09 Hz | −75.92° | **−70.75°** | 9.32 ms | 0.938 |
| 23.00 Hz | −82.80° | **−77.45°** | 9.35 ms | **0.928** |

Applying a full 10 ms **over-corrects by +0.9° at 3 Hz, +2.4° at 7.79 Hz, +5.4° at 23 Hz.**

**🛑 HOW TO CORRECT IT — and the honest answer is that the caches CANNOT be fully corrected.**
Co-logged frames **share a `logMonoTime`**, so **no timestamp-based reconstruction can tell which was
processed first.** A `searchsorted(..., side="left") - 1` reconstruction always picks the previous
`0x18F` ⇒ it **reproduces the mixture rather than removing it** (predicted 8.72 % of rows at age ≈ 0;
**measured 0.000 % on all three routes** — the check that falsified it). Ranked:
- **flat 10 ms** — over-corrects by +2.4° at 7.79 Hz, +5.4° at 23 Hz;
- **`H(f)⁻¹`** — correct *on average*, but gains noise **1.078× at 23 Hz**;
- **`payload_time` via `searchsorted`** — exact for **which frame index the row holds** (correct to the
  frame on 91.28 % of rows), no better on the processing-order mixture, but it **does** handle dropouts
  (`payload_age > 20 ms` flags 0.7–0.9 % of rows, better than assuming them away).
  ⚠ **It is NOT a no-op even on r73**: it differs from the naive `raw18_t[i]` on **10.45 % of rows**
  (max 543 ms at a dropout), because r73's own shift census is a *mixture* — `0 ×54,771 · −1 ×6,367 ·
  −2 ×10 · … · −7 ×1`. **"r73 is shift 0" was the modal case, not the route.** Applying it to
  `v89_g1` tightened exposure 147 → 118 engaged windows (~20 % dropped, correctly) and **moved no
  conclusion**: γ² still refuses (0.385/0.465), the engaged lag is still negative (−7.25
  [−15.88, −1.00]), the manual arm still matches `H_A` (+8.50 [+6.00, +11.75]).
  ⚠ Its flat 9.939 ms age is computed *under* the `0x14A`-first assumption, so **it is not independent
  evidence of uniformity** — the flatness is partly built in;
- **only RE-EXTRACTION recording the `0x18F` timestamp per row is complete.**

⇒ **Residual on the existing caches is now BOUNDED rather than guessed: ≤2.4° and ≤1 % at 7.79 Hz;
≤5.4° and ~7 % at 23 Hz.** Below anything load-bearing in the current record.

🛑 **r76 STAYS IN.** Its row↔frame *index* shift really does drift (−1 → −4) and its frame counts
differ by 2 — **but that is bookkeeping, not timing.** Its payload *age* is flat at 9.93 ms and its
tails are the **cleanest of the three** (rows >12 ms: 4.88 / 4.64 / **4.61 %**). `payload_time` is
computed from timestamps, not indices, so it is immune. Excluding r76 would cost **10.95 engaged
minutes at the corpus's highest engaged fraction (86.6 %)** for a defect all three share.

🛑 **THREE DISCRIMINATORS THAT DO NOT WORK** — each was cited as decisive during this dispute:
`sstat` (>99.87 % constant; shifts −3…0 all match at 1.000000) · `raw18_b4 → sca` (only 7–16
transitions, and the row's byte-4 reconstruction ties to 5 decimals at every shift) · **"payload age
vs the most recent `0x18F`"**, which returns 0.000 ms by *assuming the row holds the newest frame* —
the very question at issue. ⊕ `len(raw18_t) − len(raw14_t)` is a valid **tripwire**, never a shift.

### 🛑 NAMED TRAP: **AN ADDRESS IS NOT A MODE.** Three instances, 2026-08-10.
**Never let a raw address stand in for a mode in a spec. Dereference `0xCBE74 + mode*4` and print the
mode number beside it.** Byte-verified map for the friction-comp LERP (`FUN_00036c12`, `gp-0x6b26`):

| mode | record | X array | **Y ARRAY** | V74 dosed ×1.5? | |
|---|---|---|---|---|---|
| 10 | `0xD2A44` | `0xD2A46` | `0xD2A4C` | YES | **DISENGAGED — V73's only edit, inert on this car** |
| 23 | `0xD6A54` | `0xD6A56` | `0xD6A5C` | YES | another variant's engaged column |
| **24** | `0xD6A64` | `0xD6A66` | **`0xD6A6C`** | **no — never touched, ever** | ★ **THIS CAR, MANUAL** |
| 25 | `0xD7A44` | `0xD7A46` | `0xD7A4C` | no | row-11 B branch |
| **26** | `0xD7A54` | `0xD7A56` | **`0xD7A5C`** | YES | ★ **THIS CAR, ENGAGED** |
| 27 | `0xD7A64` | `0xD7A66` | `0xD7A6C` | YES | row-11 B branch |

🛑 **The Y array is at RECORD BASE + 8.** Writing Y values at `base+2` lands them in the **X breakpoint
array**, which the LERP compares **unsigned** — e.g. `−29490` reads as `36046`, every speed falls below
`X[0]`, and the table returns a flat `Y[0]` at all speeds. **A silent, plausible-looking 5× increase at
highway.** Assert the X arrays unchanged in any builder that touches this row.

### 🛑 `0xCBE74` LINEAGE — the friction row has ZERO clean flights on a live column
Three separate overstatements were made about this cell in one session, in both directions. The
byte-verified truth:

| build | ×1.5 on a **live** column (24/26)? | on-car |
|---|---|---|
| V73 | **NO** — mode 10 only (disengaged) | flew clean — **says nothing about this lever** |
| **V74** | **YES** (13 engaged modes) | 🛑 **HARD FAULT, latched loss of assist** |
| **V75** | **YES** | 🛑 **HARD FAULT, latched** |
| V76 *(flown = `_v76_v38base_relu_damper`)* | **NO** — reverted by the V38 rebase | clean |
| V77 / V77B | YES | **never flew** |

⇒ **×1.5 on this car's live columns has flown exactly TWICE and both flights hard-faulted.**
🛑 **And it inverts the standing fault attribution:** the record blames `0xC407E` = 850, but **V73 carried
850 and flew clean.** V73→V74 is 64 differing runs (13 friction sites + 51 others) so the friction row
**cannot be pinned** — but the control meant to exonerate it is the thing that implicates it. ⇒ the row
moves from *exonerated* to *open suspect*, and no dose should fly until a probe measures the lane.
⚠ Two artefacts share the V76 number; **the lineage row's BASE column is the discriminator, and a glob
is not a check.**

⊕ **NAMED TRAP, four instances in one session: a COUNT or an INDEX RELATION is not a PHYSICAL FACT.**
The r76 "drift", the `gp-0x6752` writer census (a 6-byte-encoding blind spot read as "3 stores"), the
V86-vs-V89 rung map, and the payload-age metric. **Measure the physical quantity directly.**

`band_envelope` is **peak-to-peak scale**, not amplitude ·
**a ring-down through a bandpass MUST be quoted against a step control through the identical filter** ·
`rate_f` scale ~25 % low — **now pinned at 0.743–0.767 and scoped, see NAMED TRAP 1 above** ·
for N ≥ 5 only a phase-lock test establishes a harmonic.

---
Update it in place at every close-out; do not append new dated blocks (that is what made `CLAUDE.md`
unreadable). The narrative of how each state was reached lives in `docs/HANDOFF-*.md`.

**Read alongside:** `docs/BUILD-LINEAGE.md` — 🛑 **start with `RULE 3` at the top of that file: a
"CONFIRMED" result is about a LEVER, not about the car you are driving. Byte-check the current image
before reasoning from any recorded result.** 🛑 **Then `RULE 6` — a lever is only in force if the car
reads the TABLE you edited.** 🛑 **Then `RULE 7` — a lever is mode-proof, or it is a bet; this car is
`TVCA4`, modes 24/25 manual and 26/27 ENGAGED.** Then the latest handoff (the 2026-08-08 late one,
V83a's flight and V84), then
**the latest handoff is `docs/handoffs/2026-08/HANDOFF-2026-08-11-v90-flew-and-the-lever-search-closed.md`** (V90's
flight, the six closed levers, and V91/V92), preceded by
`docs/handoffs/2026-08/HANDOFF-2026-08-10-v89-flew-and-the-mechanism-is-friction.md`, then
`docs/handoffs/2026-08/HANDOFF-2026-08-08-v81-flew-and-the-aggregator-reaches-the-motor.md`, then
`docs/handoffs/2026-08/HANDOFF-2026-08-07-v80-flew-the-damper-is-a-relay.md` (V80's flight and V81),
then `docs/handoffs/2026-08/HANDOFF-2026-08-07-v76-flew-and-the-relu-plan-inverts.md`, then
`docs/handoffs/2026-08/HANDOFF-2026-08-07-v76-v38base-and-the-friction-ceiling.md`, then
`docs/handoffs/2026-08/HANDOFF-2026-08-07-v74-fault-rlogs-the-damper-WAS-in-force.md`, then
`docs/handoffs/2026-08/HANDOFF-2026-08-06-v74-also-faulted-and-the-damper-was-not-in-force.md`, then
`docs/handoffs/2026-08/HANDOFF-2026-08-06-v75-faulted-and-the-gate2-gain.md`, then
`docs/handoffs/2026-08/HANDOFF-2026-08-06-v74-flew-the-damper-is-real.md`, then
`docs/handoffs/2026-08/HANDOFF-2026-08-05-v72-flew-the-damper-was-never-in-force.md` (spec: `docs/specs/design/V73-DESIGN.md`),
then `docs/handoffs/2026-08/HANDOFF-2026-08-04-both-confirmed-fixes-were-off-the-car.md`
(predecessors: `handoffs/2026-08/HANDOFF-2026-08-04-v69-flew-grind1-back-at-creep.md`, then
`handoffs/2026-08/HANDOFF-2026-08-04-v69-recut-4x-and-ratchet-probe.md`, then
`handoffs/2026-08/HANDOFF-2026-08-04-v69-built-speed-shaped-rate-lane.md`, then
`handoffs/2026-08/HANDOFF-2026-08-03-v68-flew-the-lane-change-is-28hz.md`, then `handoffs/2026-08/HANDOFF-2026-08-03-the-detector-was-always-there.md`, then
`handoffs/2026-08/HANDOFF-2026-08-02-v67-flew-and-the-highway-grind-is-not-the-rate-lane.md`, then
`handoffs/2026-08/HANDOFF-2026-08-01-grind2-is-v62s-own-fix-at-high-frequency.md`, then
`handoffs/2026-08/HANDOFF-2026-08-01-v62-flew-and-the-grinding-is-fixed.md`, then
`handoffs/2026-07/HANDOFF-2026-07-31-v64-the-null-is-on-the-gate.md`, then
`handoffs/2026-07/HANDOFF-2026-07-31-v61-worse-the-rate-lane-is-the-damper.md`, then
`handoffs/2026-07/HANDOFF-2026-07-31-v60-null-and-the-v52c-fabrication.md`, then
`handoffs/2026-07/HANDOFF-2026-07-30-v59-drive-and-the-loop-hypothesis.md`).

---

★★★★ **SUPERSEDED HEADLINE, 2026-08-07 (night) — superseded by the 2026-08-08 headline above: V80 FLEW. IT DID NOT FAULT, AND IT PRODUCED THE WORST
GRINDING THIS CAR HAS EVER MADE. THE CAUSE IS ITS OWN DAMPER — A FLAT `FactorC` AT `k` = 4.16 TURNS THE
DAMPER INTO A NEAR-BANG-BANG COULOMB RELAY, AND THE BUILD'S NO-CLIP GATES WERE STRUCTURALLY BLIND TO IT.
**V81 — A 126-BYTE REVERT FROM THE FLOWN V75, WITH BOTH LEGS OF THE FAULT MECHANISM REMOVED — IS BUILT,
VERIFIED AND UNFLASHED. THE FLASH DECISION IS THE OPERATOR'S.**

**Route `75604b0a432fdc89|00000066--276b942769`, 15 segments, 901.71 s, 89,997 frames @ 100.0 Hz,
downloaded to `analysis-2020accord/rlogs/`. Engaged (`carControl.latActive`) 30,260 frames = 302.6 s =
33.62%**, 9 engaged episodes ≥ 2 s, speed −0.09 … 31.34 m/s (112.8 km/h).
**Operator's verdict: the WORST grinding the car has ever produced** — loud, strong, felt through the
whole car, ~90% of LKAS-engaged time, at both low and high speed, causing noticeable vehicle instability.
🛑 **V80 DID NOT FAULT. This is a STABILITY failure, not a fault-class failure.** `0x1AB` DTC-active:
**0 transitions, 0.000% duty**, 0 × `0x7FFF` sentinels; `STEER_STATUS` histogram {0: 63,861, 3: 26,136},
same shape as route 65. [EVIDENCE]
⊕ `builds/v80_v107/build_v80_tva.py`'s own header says verbatim *"GATE 2 (magnitude AND phase) is NOT satisfied by
argument. **V80 IS NOT CLEARED TO FLY.**"* It was flown anyway.

### ★★★★★ ROOT CAUSE — V80's damper is a near-bang-bang Coulomb relay

Damper dose vs motor rate at **5 km/h**, recomputed by the orchestrator from the shipped plain images,
records dereferenced through their pointer arrays (`FactorC 0xC9E9C`, `FactorE 0xC9F84`,
`ceiling 0xC77A0`, `friction 0xCBE74`), **mode 26** (this car is `TVCA4`: 26 engaged / 24 manual):

| rate (ct) | 20 | 40 | 99 | **119** | 150 | 255 | 530 | 1000 | 1941 | 4000 |
|---|---|---|---|---|---|---|---|---|---|---|
| ≈ °/s (4.7121 ct per °/s) | 4 | 8 | 21 | **25** | 32 | 54 | 112 | 212 | 412 | 849 |
| **V75** | 12 | 44 | 137 | 169 | 218 | 297 | 297 | 297 | 297 | 512 |
| **V80** | 82 | 166 | 412 | **495** | 495 | 495 | 496 | 498 | 501 | 512 |

⇒ **V80 emits a constant 495 counts — 3.4% variation across a 34× rate range — at 97% of the 512 ceiling,
above only ~25 °/s, at EVERY speed** (FactorC is flat). V75 plateaus at 297 (58% of ceiling) and only
above 54 °/s. [EVIDENCE, orchestrator's own Python LE read of the flashed images]

🛑🛑 **WHY THE BUILD'S OWN GATES WERE BLIND.** Every no-clip guard tests `product > ceiling`. V80's
supremum is `(566*927)>>10 = 512` = the ceiling **exactly**, so it clips **0.00%** and passes. The flat
FactorC did not remove the relay — it **moved** it from the ceiling clamp to **FactorE's own knee**,
**17 counts under the rail** (slope drops ~1200× at `X[1] = 119`). **"Does not clip" and "is not a relay"
are different statements, and only the first was ever checked.** [EVIDENCE]

**Describing function** `N(R)` (fundamental-harmonic gain of `force = −sign(rate)·M(|rate|)`; constant
`N` = viscous = stabilising, `N` rising as amplitude falls = relay = limit-cycle generator):

| R (ct) | 25 | 50 | **99** | 150 | 250 | 500 | 1000 |
|---|---|---|---|---|---|---|---|
| V75 @creep | 0.580 | 1.065 | **1.319** | 1.410 | 1.317 | 0.734 | 0.375 |
| V80 @creep | 4.007 | 4.087 | **4.127** | 3.698 | 2.421 | 1.250 | 0.632 |
| V80/V75 @60 km/h | 17.7× | 9.4× | **7.6×** | 6.4× | 4.5× | 4.1× | — |

Relay-ness index `N(50)/N(500)`: **V75 = 1.45× (creep) / 1.43× (60 km/h); V80 = 3.27× at both.**
Small-signal loop gain `k`: **V75 1.5798 · V76 1.3866 · V74 0.5799 · V80 4.1597** — 2.63× V75, 3.00× V76,
extrapolating 2.6× beyond the last measured point. [EVIDENCE]

★★★★ **THE MEASUREMENT THAT SETTLES IT — both builds' own cave probes.**

| | damper `\|gp-0x6bd0\| ≥ 448 counts`, engaged |
|---|---|
| **V75** (route `5e`, 28,317 pre-fault frames) | **0.000%** — never above 128 counts *at all* above 40 km/h |
| **V80** (route `66`) | **19.4%** overall · 32.7% above 15 m/s · **71% through the worst 29 s event** |

V75's engaged level census: L0 (dead) 56.8% · L1 (1–127) 25.3% · L2 (128–287) 9.3% · L3 (288–447) 8.6% ·
**L4 (≥448) 0.000%.** **V75's damper never entered its saturated regime. V80's lives there.**
[EVIDENCE — the single cleanest statement of the root cause]

★★ **THE DAMPER'S NET SIGN IS RESOLVED, AND IT IS DISSIPATIVE.** `gp-0x6abe` is the **signed twin of
`gp-0x6ac0`** (both filtered from `gp-0x4f50` in `FUN_00041464`; `0x41b56`:
`gp-0x6abe = (short)(uVar16>>10)` signed vs `gp-0x6ac0 = |uVar16|>>10` rectified). Sign applied at
`0x3469E`–`0x346A2` (`cmp r0,r11 / ble / subr r0,r8`) ⇒ `sign(gp-0x6bd0) = −sign(motor rate)`.
**Path 2 through the PID is NON-INVERTING**: the Stage-2 subtraction in `FUN_00038148` and the PID's
`err = setpoint − feedback` cancel, and the two `polarity(gp-0x6752)` multiplications cancel regardless of
value ⇒ `(−P)(+1)(−1)(+P) = P² = +1`. `FUN_00037fe6` is a genuine unity adder (all 7 weights at
`tp+0x74ad..0x74b3` read `01`). Path 1 (bare) and Path 2 both enter `FUN_0003aa2c` with unity weight and
**REINFORCE** ⇒ **dissipative by construction at `gp-0x6b94`, high confidence.** [EVIDENCE]
⚠ **STILL OPEN: the `gp-0x6b94` → motor forward hop.** New node: **`gp-0x6ace`** = the governor-clamped
form of `gp-0x6b94` (written by `FUN_0004503c` via `FUN_00049a90`); its only readers are `FUN_000456a4` /
`FUN_00045a20`, both hard-shutdown monitors. Both of `FUN_00042af8`'s documented external inputs are
RULED OUT: `gp-0x6b08` is self-referential; `gp-0x6afe`'s sole writer `FUN_00042ac6` is fed by
`FUN_00026c80`, an independent Sensor-B lane that runs BEFORE `FUN_0003aa2c` in the same tick.
**A missing link, not a discovered inversion.**

### WHAT ROUTE 66 ACTUALLY SHOWS

★★★ **(a) A broadband HF floor lift — the dominant effect.** Median engaged periodogram, **V80 minus
V76**, matched 10–40 km/h stratum:
```
 Hz    7.8   12.1   18.0   19.9   21.9   23.8   26.2   28.1   30.1   34.0   35.9   39.9   44.2   48.1
dB   -6.03  -0.20  +0.05  -0.72  -0.58  +2.44  +3.75  +5.27  +5.70  +9.22 +10.41  +8.15  +8.49 +11.47
```
**Grind #1's own band is UNCHANGED; the ratchet is 6 dB DOWN; everything above ~24 Hz lifts by a flat,
prominence-neutral offset.** Cell-stratified V80/V76 = **2.09× [1.46, 2.70]** on the 30–49 Hz floor, and a
pre-declared **32–38 Hz negative control fails identically (2.035)** ⇒ the whole HF region moved together.
**This is NOT "grind #2 got worse".** [EVIDENCE]
**Falsifiers, all cell-stratified V80/V76:** torsion bar 30–49 Hz **2.09 [1.40, 2.71]** · steering angle
30–49 Hz (a **different CAN message**, `0x14A`) **1.60 [1.26, 2.03]** · **IMU vertical 20–49 Hz 1.07
[0.92, 1.33] ⇒ NOT a rougher road** · openpilot `0x0E4` command 1.25 [1.12, 1.44] · 1–4 Hz driver-input
exposure check 1.14 [0.88, 1.47].
★ **FFT-FREE CONFIRMATION** — sample-to-sample sign reversals, immune to spectral leakage. Engaged windows
containing ≥1 reversal of `|step| > 300` counts: **V75 3.0% · V74 22.0% · V76 22.0% · V80 73.0%**. At
`|step| > 800`: **V75 0.0% · V74 0.5% · V76 0.6% · V80 23.3%.** Exactly the near-Nyquist chatter a
bang-bang relay injects. [EVIDENCE]

★★★★ **(b) A sustained ~27.4 Hz limit cycle that NO other build produces.** Engaged windows with 26–31 Hz
envelope > 1000 counts: **V74 0/413 · V76 0/328 · V75 0/133 · V80 32/215 (14.9%)**, in segments 8, 12, 13,
at 54–104 km/h.
**THE WORST EVENT — segment 8, route-global t ≈ 500.9–530.3 s, 99–104 km/h, ~30 s unbroken.**
Orchestrator's own Welch spectrum over the window: **27.56 Hz at ×92 over the in-band median**; manual at
the same speed peaks at ×3.1. Torsion bar **6,830 counts p-p**, σ = 1,059. At 10.24 s resolution the line
is **27.344 Hz, prominence 292, Q ≈ 140.** Steering angle p-p **1.92°**, angle rate p-p 234 °/s. Damper
`≥448` duty through the event: **71%**. `sstat`=0, `sca`=1, `cc_lat`=1 throughout — **no fault, no
lockout.** Envelope goes 50 → 3000+ counts within ~1.5 s of engagement and collapses to ~150 the instant
LKAS disengages.
**Relay tests:** amplitude clamped ±15% over 30 s ✅ · crest factor **1.838** (sine 1.414, square 1.000) =
near-sinusoidal limit cycle ✅ · **NOT wheel order 2**: measured `df/dv` = **−0.131 [−0.231, −0.016]** Hz
per m/s where order 2 demands **+0.961**; at 54–62 km/h the line sits at 28.7–30.1 Hz where order 2 would
be 14.4–16.7 Hz ❌.
Speed-tracking check (engaged, 26–30 Hz peak): 1–5 m/s → 30.3 Hz ×2.1 · 10–15 → 26.2 Hz ×1.6 · 15–20 →
29.1 Hz ×10.3 · **24–32 → 27.6 Hz ×94.9.** **Frequency pinned across a 20× speed range** (wheel order 1
would sweep 1.5 → 13.7 Hz), **amplitude exploding with speed.**
⚠ **The mode is NOT new to V80 — it is the kit's ~28 Hz line, amplified.** V74's strongest windows
29.4–29.5 Hz, e = 450–531 ct @106–114 km/h; V76's 28.3–28.9 Hz, e = 815–920 ct; V80's 26.8–28.2 Hz,
**e = 1759–2686 ct**. V80 raised it ~2.7×, dropped f0 by 1–2 Hz, and turned intermittent episodes into a
sustained limit cycle. [BELIEF] the f0 drop with loop gain is what a control-loop mode does and a fixed
mechanical resonance does not.
⚠ **Aliasing (common mode):** fs ≈ 100.0 Hz, so 27.344 Hz is indistinguishable from 72.66/127.34 Hz.
Identical on all four routes ⇒ cannot affect the contrast, only the identification.
⚠ **Command caveat:** openpilot's own `0x0E4` carries 25–30 Hz at rms 45.8 ct, correlated +0.93 at lag 0
with the bar; bar/command ratio at 27 Hz is **15.8×**. [BELIEF] an echo, not a cause — the EPS LKAS lane
is a ~1–5 Hz low-pass on standing EVIDENCE, so a 27 Hz command component cannot reach the motor that way.
**Settling it needs a phase-resolved coherence, not the lag-0 correlation that was run.**

★★ **(c) Damper-saturation dose–response** (engaged 2.56 s windows), 17–30 Hz band power binned by the
fraction of the window the damper spent ≥448 counts:
`0–5% → 1.1e3 · 5–20% → 9.2e3 · 20–40% → 3.0e4 · 40–60% → 2.1e5 · 60–80% → 1.4e6.`
**Three orders of magnitude, monotone.** ⚠ speed and saturation duty are mutually confounded ⇒
**[EVIDENCE] on the association, [BELIEF] on causal direction.**

★★ **(d) "~90% of engaged time" — quantified, scored on the band that MOVED (30–49 Hz).** Thresholds taken
from V76's own engaged distribution (so V76 reads 50/25/10% by construction):

| threshold | V74 | V76 | V75 | **V80** |
|---|---|---|---|---|
| V76 p50 (85.7 ct) | 42.9% | 50.0% | 42.9% | **79.5% [70.3, 87.7]** |
| V76 p75 (128.1 ct) | 21.1% | 25.0% | 11.3% | **75.3% [66.2, 83.9]** |
| V76 p90 (203.5 ct) | 6.8% | 10.1% | 4.5% | **64.7% [52.8, 74.9]** |

Per stratum at V76-p50: creep 37.1% · **10–40 km/h 93.9%** · **40–80 km/h 80.0%** · **>80 km/h 100%.**
Independently, on the 17–30 Hz p-p criterion: **89.1% of engaged windows ≥100 ct p-p**, and **17.1% of
engaged time >1,500 ct p-p — an amplitude reached in ZERO of 432 manual windows.** Engagement test: median
per-edge ratio **×2476** (18–22 Hz) within 4 s of the `latActive` rising edge, 6/7 edges up; falling edges
×0.34. **[EVIDENCE] engagement-conditional, switches on within seconds.**

### 🛑🛑 TWO RETRACTIONS THE RECORD NOW CARRIES

🛑 **(1) GRIND #1 IS INERT TO THE DAMPER DOSE.** Four-point ladder on ONE instrument
(`rlog-tools/studies/grind/compare_v75_v76_v80_grind.py`, NFFT 256/hop 128, p99 analytic band envelope, ~10.2 s
bootstrap blocks nested inside engagement runs), ratio to V76:

| band | V74 k=0.58 | V76 k=1.39 | V75 k=1.58 | V80 k=4.16 |
|---|---|---|---|---|
| **18–22 grind #1** | 1.166 [0.98,1.41] | 1.000 ref | 0.735 [0.50,1.22] | 0.835 [0.64,1.07] |
| 6–9 micro-ratchet | 0.818 [0.70,1.09] | 1.000 ref | 0.821 [0.66,1.09] | **0.418 [0.33,0.61]** |
| 26–31 | 0.823 [0.72,1.02] | 1.000 ref | 0.865 [0.71,1.20] | 1.197 [0.80,1.52] |
| **40–49 grind #2** | 0.810 [0.70,0.97] | 1.000 ref | 0.961 [0.77,1.24] | **2.017 [1.32,2.83]** |
| **30–49 HF floor** | 0.820 [0.73,1.01] | 1.000 ref | 0.953 [0.81,1.26] | **2.091 [1.46,2.70]** |
| **32–38 neg control** | 0.865 [0.76,1.03] | 1.000 ref | 0.959 [0.82,1.22] | **2.035 [1.45,2.57]** |

Split-half nulls (300 halvings, per route): 18–22 Hz ≈ **[0.63, 1.60]**. **Every grind-#1 point sits inside
its own noise floor across k = 0.58 → 4.16.** ⇒ 🛑 **V80 did NOT "overshoot an optimum" on grind #1 —
grind #1 never responded to `k` at all.** On this instrument V75's "no grind #1" vs V76's "still grind #1"
is a **creep-EXPOSURE difference** (V76's creep windows carry 3.4× V75's steering effort), not a dose
difference. **This retracts the "grind #1 is DOSE-LIMITED" verdict in the superseded headline below.**
[EVIDENCE]
★ The operationally useful statement: **something switches on between `k` = 1.58 and 4.16 that costs 2×
broadband HF plus a limit cycle. Where in that gap it switches on is UNMEASURED.**
🛑 **CORRECTED 2026-08-07 by the orchestrator:** an earlier draft of this line read *"`k` ∈ [1.39, 1.58]
buys most of the ratchet benefit at zero HF cost"* — **that clause is withdrawn.** It contradicts the very
next paragraph: 6–9 Hz is FLAT from `k` = 0.58 to 1.58, so that bracket buys **no measurable ratchet
benefit over a LOWER dose**. The only ratchet gain in the corpus is at `k` = 4.16, and it is the point that
also carries the HF penalty. **There is no measured "free ratchet benefit" bracket.**
★ **The micro-ratchet's own reading, stated precisely:** on this ladder (ratio to V76, split-half null
≈ **[0.66, 1.45]**) 6–9 Hz is **FLAT across `k` = 0.58 → 1.58** — V74 0.818 [0.70, 1.09], V75 0.821
[0.66, 1.09], both **inside** the null ⇒ the earlier **"dose-independent" verdict was ACCURATE over the
range then available, and is not refuted — its DOMAIN is bounded above.** It improves significantly **only
at `k` = 4.16**, the first point outside the null: **0.418 [0.33, 0.61]** [EVIDENCE]. ⇒ **V80 bought a real
ratchet gain and paid for it with the HF floor.**
⚠ **Calling the four points MONOTONE is [BELIEF], not EVIDENCE** — three of the four are inside the null,
so only the top point carries it.

🛑 **(2) V80's CREEP NUMBERS ARE AN EXPOSURE ARTEFACT — do not read them.** V80's engaged creep windows
have median sustained effort **173 counts** and median `|angle rate|` **1.3 °/s**, against V74/V76/V75's
685/588/1113 counts and 33/33/48 °/s. **Zero matched cells.** An earlier claim this session that "V80 is
3–30× quieter than V76 at creep" is **RETRACTED — the driver was not turning the wheel.** Also
unresolvable: whether V80's near-zero creep angle rate is itself an *effect* of a 412-count-at-all-speeds
damper making the wheel feel sticky.
⚠ Also not comparable: the **>80 km/h** stratum — V75 never exceeded 65 km/h and V80 has **1 engagement
run / 3 blocks** there (the limit-cycle event itself). **The 10–40 and 40–80 km/h strata are well matched
and carry the load.**

### ★★★★★ THE FAULT MECHANISM — CONFIRMED IN GHIDRA, AND THE `0xC63A0` PREMISE IS REFUTED

**`0xC407E` (= `tp+0x507E`; anchored `0xBF000+0x507E`, the off-by-0x1000 trap avoided) is the whole story.**
- **Monitor `FUN_00036d74`** — orchestrator's own decompile: `fVar3 = gp-0x6b26 * 0.0009765625`; if
  `|fVar3| > *(float*)(tp+0x5004)` → `FUN_000462e6(0x39bc,…)` → `FUN_00016de6(0x1d,…)` = **DTC 0x1d,
  latched total loss of assist**. `0xC4004` bytes `0000003f` = f32 **0.5** ⇒ trip at **512 counts**.
  Symmetric, **no debounce.** Called from the 1 kHz task `FUN_0002214a` @`0x2290A`; the caller's
  `gp-0x67fa ∈ {4,5,11}` gate is the SAME gate that wraps the producer's call ⇒ unconditional *relative to
  the producer* — no path writes `gp-0x6b26` without the monitor checking it that cycle.
- **Sole writer of `gp-0x6b26`**: `st.h r6,-0x6b26[gp]` @`0x36CF0` in `FUN_00036c12` — **exactly one writer
  image-wide**, confirmed by Ghidra + a raw Python LE scan covering disp16, the 6-byte disp23 form, LE32
  address literals and movhi/movea pairs (**0 hits on all three alternatives**). The stored value is
  already clamped to ±`0xC407E` (clamp arms at `0x36CCC`–`0x36CE2`).
- **`0xC407E` itself**: 0 writers, 3 readers, all `ld.h` SIGNED, **all three inside `FUN_00036c12`** ⇒ the
  cell's entire blast radius is one lane's clamp magnitude.
- **Margins**: stock / V38 / V76 / V78 / V79 / V80 **511 → +1, UNTRIPPABLE** · V73 / V74 / V75 **850 →
  −338, TRIPPABLE** · **V81 511 → +1, UNTRIPPABLE.**
⇒ **At 511 the monitor is untrippable BY CONSTRUCTION** — the only value that ever reaches the cell is
already clamped below the trip, whatever the plant, mode or lever set does. [EVIDENCE]

🛑🛑 **THE `0xC63A0` PREMISE IS REFUTED.** The standing operator directive *"do not double `0xC63A0`, that
is what was causing hard faults"* rests on a **false premise**. `0xC63A0` (= `tp+0x73A0`) has **exactly one
reader**, `ld.hu` @`0x381AC`, **0 writers, 0 disp23 hits**. Its only reader `FUN_00038148` writes exactly
two cells — `gp-0x374c` (accumulator) and `gp-0x6b70` (output) — and **never** `gp-0x6b26`, `gp-0x6c2c` or
`gp-0x6a5e`. `gp-0x6c2c`'s two writers are both inside `FUN_00041464` (`0x4184E`, `0x41AC2`).
**There is NO firmware data path from `0xC63A0` to the faulting monitor.** A *physical* path exists
(aggregator → motor → plant → motor rate → `gp-0x6c2c`) and is irrelevant, because **the clamp acts before
the store.** [EVIDENCE]
⊕ `build_v80_tva.assert_c63a0_block` still hard-asserts 1024 with the old rationale — **the comment there
is now known-wrong** and should be corrected. (V80 is a different lineage, so nothing conflicts.)

★ **V75's fault was NOT the damper.** In the last 5 s before the trip the damper was identically **zero for
4.98 s** and reached only level 2 (128–288) **19 ms** before the fault. The car was stationary T−5→T−1 s
then launched (0 → 7.6 km/h). Column rate reversed sign twice in the final 150 ms (+55, +31, −38 °/s);
**peak jerk 7,154 °/s² = 4.3× that route's own p99.9 (1,664)** and the route maximum. Exactly what the
`0xC407E` mechanism predicts. [EVIDENCE]
⚠ **[BELIEF, not EVIDENCE]** "`0xC407E` = 850 caused BOTH faults" — **the DTC number was never confirmed
on-car.** What is EVIDENCE: the mechanism exists, is single-frame, is mode-proof, and the build history
lines up exactly. **V81 closes it whether or not it fired.**

### 🛑 THE V38 REBASE SILENTLY REVERTED ~~THREE~~ **SEVEN** THINGS

🛑 **CORRECTED 2026-08-08 (late): this heading read "THREE LEVERS" and the count has now been walked to
SEVEN.** The record named `0xC63A0`, `0xC407E` and friction ×1.5 (the last two **declared**); `0xC62EA`,
the V57 decouple triplet and `0x454FE` were added later; and a **SEVENTH has never been logged anywhere
until now — `gain_A` rec0/rec1.**

Orchestrator's own byte read across the lineage:

| lever | V62 · V68 · **V74 · V75** | **V76 · V78 · V79 · V80** |
|---|---|---|
| `0x2A1F0` reader disp | `0x7CD0` → **decoupled** `0xC6CD0` = 3564 | `0x746C` → **shared** `0xC646C` = 3564 |
| `0xC646C` shared sensor scale | stock **891** | **3564 (4×)** |
| `0xC62EA` low-speed steer lockout | **0** (removed) | **320** (restored) |
| `0xC63A0` Path-2 damper weight | **2048** | 1024 |
| `0x454FE` V42 macro-ratchet fix | `0xB5` | `0xBA` — 🛑 **the SECOND silent loss of this byte** (V76/V78/V79); **V80 restored it to `0xB5`** |
| 🆕 **`gain_A` rec0** `0xC6A72`–`0xC6A78` | **512** | **Honda's `3072 / 2434 / 2048`** |
| 🆕 **`gain_A` rec1** `0xC6A86`–`0xC6A8C` | **512** | **Honda's `3072 / 2488 / 1536`** |
| `0xC407E` friction-lane clamp *(declared)* | **850** — ⚠ **V73/V74/V75 only**; V62/V68 carry 511 | **511** |
| friction row, 14 sites *(declared)* | **×1.5** — ⚠ **V73/V74/V75 only**; V62/V68 carry Honda's row | **stock** |

🛑 **V80 vs V75 was NEVER a single-variable damper comparison — and the confound count is FIVE, not four.**
The **silent** ones are `0xC63A0`, `0xC62EA`, the V57 decouple triplet, `0x454FE`, and now **`gain_A`
rec0/rec1**; `0xC407E` and the friction row were declared. V76 was cut from V38, which predates V57's
decouple, and nothing in the V76 → V78 → V79 → V80 chain re-applies it.
⇒ **Any conclusion drawn from a V80-vs-V75 (or V76-vs-V75) contrast must name all five.** [EVIDENCE]

**`0xC646C` — full reader map, and why it is NOT the 27 Hz driver.** Exactly **6 static readers, 0 stores,
0 disp23 hits, 0 LE32-pointer hits** (three independent methods: Ghidra `search_instructions`, a fresh raw
Python LE scan of both encodings, fresh decompiles). **Q15 dimensionless multiplicative scale** —
`(x * cal) >> 0xf` at every site; 3564 = 4×891 exactly.

| # | addr | function | role |
|---|---|---|---|
| 1 | `0x2a1ee` | `FUN_00028ea6` | **LKAS arbitration / CAN-setpoint→command — the one V57 decoupled** |
| 2 | `0x2a904` | *(orphan)* | **DEAD** — no function, no xrefs |
| 3 | `0x2b656` | `FUN_0002b62c` | **RECLASSIFIED**: output `gp-0x6af0` reaches only a private 2-function mode-flag debounce loop (`gp-0x677d` has exactly 2 static refs image-wide) + a UDS packer with 0 static callers. **No torque path.** |
| 4 | `0x2c488` | `FUN_0002c478` | output `gp-0x6b10` has **3 refs, all `st.h`, ZERO loads** — proven dead |
| 5 | `0x36686` | `FUN_00036682` | **the only one reaching the motor** — multiplies RAW `gp-0x4f60`, adds into `FUN_0003aa2c` → governor → `gp-0x6b98` |
| 6 | `0x3684a` | `FUN_00036828` | modulates #5's hysteresis half-band via `gp-0x6b44` (2nd-order) |

**Reader #5 cannot drive a 27 Hz limit cycle — a BANDWIDTH argument.** Its output passes an IIR with
`alpha = tp+0x73d2 = 6` ⇒ `6/1024 = 0.00586`, corner **≈0.93 Hz, ≈−26.6 dB at 21 Hz.** [EVIDENCE]
(This also settles the prior "6 vs 14" open discrepancy **in favour of 6**.)
**Reachability screen of reader #5's pre-filter `±0x200` clamp**, whose trigger on `|gp-0x4f60|` drops from
~18,829 counts at stock to **~4,707 at 4×** — never previously run against a V76-lineage log: on route 66,
`|bar|` engaged p50 174 · p90 1,424 · p99 3,346 · p99.9 3,712 · **max 3,849**; `|bar| ≥ 4707` fired
**0 / 89,997 frames**; worst event max 3,437. ⇒ **It did not bind.** ⚠ **Margin only 22%**, and the CAN
sensor's count scale is not proven identical to `gp-0x4f60`'s internal scale ⇒ **"did not fire on this
drive", NOT "cannot fire".** Worth a probe.
⇒ **NET: the shared-cell 4× is a real, uncosted regression in headroom that nobody signed off on, but it is
NOT the 27 Hz driver.** **V81 removes the exposure for free by being cut from the V75 base.**
✅ `0xC6CD0` = `0xFFFF` on V76/V78/V80 is **provably inert** — 0 instructions read `tp+0x7cd0` anywhere.

### 🛑 TOOLING / HYGIENE FINDINGS FROM THIS SESSION

1. 🛑 **`rlog-tools/probe/decode_v76_probe.py` is the WRONG decoder for route 65** and will give a confident wrong
   answer. It documents the **superseded** V74-base V76 (`V76-V74BASE-GATE-FB-ARM5244`), whose bit7 is
   `gp-0x6bd0 != 0` — the damper, not the friction lane. The build that flew route 65 is
   `V76-V38BASE-RELU-C566-damper-frictionCLAMP511-probe-6b26-63fd`; its extractor is
   `analysis-2020accord/studies/sessions/v76/v76flight_extract.py` → `analysis-2020accord/_scratch/data/_cache_r65_records.pkl`
   (**not** `_scratch/cache/r65/`).
2. 🛑 **Two `_v76*plain_image.bin` on disk.** `_v76_gate_fb_arm5244_gateprobe_plain_image.bin` is the
   abandoned V74-base candidate and still carries the V57 decouple; a first `Glob` returns it FIRST. The
   V78/V80 ancestor is `_v76_v38base_relu_damper_plain_image.bin`. The `.rwd` was correctly renamed
   `SUPERSEDED-…`; **the stale plain-image snapshot still reads as current.**
3. **`builds/v50_v79/build_v75_tva.py`'s default lever set does NOT produce the flown V75** — you must pass
   `ACCORD_V75_LEVERS=CY0,EX1`. The default (`CY0` only) writes the never-flown `…CY0.566…` artefacts. No
   overwrite hazard (`lever_token()` is in both filenames), but the comment at line 269 is easy to misread.
   **The flown V75 is the `EX1.200` cut, dose 137, k = 1.5798.**
4. 🛑 **V74's first (clean, symptom-measurement) flight — route `5d`, 17 segments — is MISSING from
   `analysis-2020accord/rlogs/`.** Only the extracted `_scratch/cache/r5d/*.npz` + `.pkl` survive, while
   `analysis-2020accord/extract/extract_r5d_cache.py` (977 lines) is its canonical extractor and
   `docs/BUILD-LINEAGE.md` leans on that cache. **Every downstream V74 conclusion in this file runs
   against the cache, not the raw log — and the cache cannot be re-cut or re-scored.** Re-confirmed
   2026-08-08 (late). ⇒ **Recover or re-download it** (NEXT item 9).
5. **V80's probe cannot distinguish V80 from V78/V79** — byte-identical cave, identical trip rates below
   80 km/h. Build identity rests on the `.rwd` filename plus the absolute exclusion of V76-V38BASE (13,183
   frames set bit6 with bit5 clear, structurally impossible on that cave). Route 66's `0x14A` byte4 took
   only {`0x0F`, `0x1F`, `0x5F`, `0xDF`}; bit5 0/89,997; bit3 positive control **100.000%**.
6. The bash/PowerShell default `python` (anaconda base) has a **broken numpy DLL.** Either prepend
   `C:\Users\dudei\anaconda3\Library\bin` to `PATH` or use
   `C:/Users/dudei/anaconda3/envs/bin_decompile/python.exe` (which also has `capnp`).

### ⇒ ★★★ NEXT

1. **Fly V84.** 🛑 **Flash decision is the operator's; the file and the bus must be named back.** Its
   damper surface is byte-identical to V67/V68, so grind #1 is an interpolation onto a measured point.
   **Fly it with creep, mid-speed and highway engaged exposure** so the highway grind — which V84 does
   **not** claim to fix — is scored rather than assumed.
2. **Read the V84 probe first, then the spectra.** `b3` is the positive control; if `b3` is not ~100%,
   nothing else in the readout is interpretable (the V64/V68 lesson).
3. ~~Bracket the switch-on point in `k` ∈ (1.58, 4.16]~~ — **DEPRIORITISED.** The `k` dose axis is now
   falsified for the 26–31 Hz ring (headline §1) and grind #1 was already inert to `k`. The `k` ladder's
   one surviving claim is the **micro-ratchet gain at `k` = 4.16**, and it comes bundled with the HF floor.
4. **Settle the 27 Hz command-vs-plant question** with a phase-resolved coherence on `sendcan` `0x0E4` vs
   the torsion bar. This is now the *only* live route to the ring, the damper having been falsified.
5. **Probe the friction lane at 320/352/416** if V81 variant B is ever wanted — converts the bet into a
   measurement for ~30 cave bytes.
6. **Correct `build_v80_tva.assert_c63a0_block`'s now-known-wrong rationale comment.**
7. 🛑 **Correct the `0xC61B2`/`0xC61B4` label in the build scripts** — `builds/v80_v107/build_v83a_tva.py:359-360` and
   `builds/v80_v107/build_v84_tva.py:544-545` call them *"pre-gain deadband arm"*. **They are not.** See the correction in
   *Signal-identity corrections of record*. Comment-only; changes no byte.
8. **Re-run reader #5's `±0x200` clamp screen** with a proven `gp-0x4f60` scale — the 22% margin is thin.
9. 🛑 **Recover or re-download route `5d`'s raw rlogs** (V74's clean symptom-measurement flight, 17
   segments) — they are **missing from `analysis-2020accord/rlogs/`** while `extract/extract_r5d_cache.py`
   (977 lines) is its canonical extractor and `BUILD-LINEAGE.md` leans on that cache. Every V74 conclusion
   runs against the cache, not the log.

---

★★★★ **SUPERSEDED HEADLINE, 2026-08-07 (evening): V76 FLEW AND FLEW CLEAN. GRIND #1 IS ~~DOSE-LIMITED~~
AND THE MICRO-RATCHET IS **DOSE-INDEPENDENT** — a resolved split. THE OPERATOR'S "150% OF V75'S 5 mph
DOSE" IS RIGHT AND COSTS **ONE u16 CELL** (**V78**); THE "BOTH FACTORS AS ReLUs + BIGGER TABLES" HALF
**INVERTS** — 4 points was never the obstacle, and a literal ReLU FactorC RE-CREATES THE COULOMB RELAY
AT THE CEILING CLAMP.**

**Route `75604b0a432fdc89_00000065--ae43aa0f27`, segs 0–10, 636.30 s / 63,477 frames, 0–96.7 km/h,
engaged 450.98 s (70.87%). ZERO DTC transitions, zero `0x7FFF` sentinels, no frame-rate collapse.**
Build identity settled **four independent ways** (bits 6/5 structurally unreachable: 0/63,477 · 8-value
legal payload set: 0 violations · V75's thermometer invariant violated on 70.0% ⇒ not V75 · the
superseded V76's structurally-zero bit3 reads 99.926% here).

★★ **THE FRICTION-MARGIN NULL IS REAL, NOT AN UNARMED GATE.** bit7 (`|gp-0x6b26| > 448`) fired
**0 / 63,477** with the positive control (bit3) at 99.93% in the same frames, across every speed band
and both arms. ⚠ **Weakens but does not refute** the V73-interlock story — it bounds `gp-0x6c2c` from
one side only; the physical scale stays OPEN.
★ **Mode lag measured directly: median 994.9 ms [830.0, 1575.0]**, n=6 episodes — **2.5× shorter than
the ~2.5 s in prior handoffs.** Treat this as the better number; n=6 on one route does not prove the
older figure measured the same thing.

★★★★ **THE DOSE-RESPONSE SPLIT** (fit over V72/V73 k=0, V74 0.5799, V75 1.5798, V76 1.3866; creep,
speed-stratified, **episode**-bootstrapped; V76 sits *between* V74 and V75 so the model made a
falsifiable point prediction):
| band | V76 observed | monotone prediction | slope b [95% CI] | verdict |
|---|---|---|---|---|
| ratchet 6–9 Hz | 3.877 [3.098, 5.161] | 3.906 (−0.06 dB) | **−0.094 [−0.291, +0.098]** | **DOSE-INDEPENDENT** |
| grind #1 18–22 Hz | 1.577 [1.380, 1.831] | 1.613 (−0.19 dB) | **−0.614 [−0.810, −0.416]** | ~~DOSE-LIMITED~~ 🛑 **RETRACTED 2026-08-07 (night)** |
🛑🛑 **THE GRIND-#1 "DOSE-LIMITED" VERDICT IS RETRACTED — see the current headline, retraction (1).** On a
four-point ladder run on ONE instrument across `k` = 0.58 → 4.16, **every grind-#1 point sits inside its own
split-half noise floor [0.63, 1.60]**. What this three-point fit read as a dose slope is a **creep-EXPOSURE
difference** between the routes (V76's creep windows carry 3.4× V75's steering effort).
✅ **THE 6–9 Hz DOSE-INDEPENDENT LEG IS *NOT* REFUTED — its DOMAIN is now bounded above.** On the four-build
ladder (ratio to V76, split-half null ≈ **[0.66, 1.45]**) the micro-ratchet is **FLAT across `k` = 0.58 →
1.58** — V74 **0.818 [0.70, 1.09]**, V75 **0.821 [0.66, 1.09]**, both inside the null ⇒ **"dose-independent"
was ACCURATE over the range then available.** It improves significantly **only at `k` = 4.16**, the first
point outside the null: **0.418 [0.33, 0.61]** [EVIDENCE].
⚠ **Reading all four points as a monotone trend is [BELIEF], not EVIDENCE** — three of the four sit inside
the null, so **only the top point carries it.**
🛑 ~~More damper will NOT fix the micro-ratchet.~~ Grind #1 present on V76 at rel. excess
**1.956 [1.214, 4.154]** (worse than V75's 1.572, far better than V74's 9.154); ratchet **5.026
[3.824, 6.592]**, indistinguishable from V74/V75. **Both match the operator's report exactly.**
🛑 **V76's grind-#2 prediction was FALSIFIED** at the one powered rung: predicted 0.57× vs V75 at
42 °/s, **measured 1.394 [1.017, 1.768]** — opposite direction. Discount the arithmetic surface's
ability to predict *delivered* grind #2; the `k` dose axis itself was validated.

★★★★★ **THE EVALUATOR, orchestrator-verified by decompile (`FUN_00034350`, sole caller `FUN_00022ca0`):**
- Records are reached through a **pointer array per factor** (`FactorB 0xC9CCC · FactorC 0xC9E9C ·
  FactorD 0xC9DB4 · FactorE 0xC9F84 · ceiling 0xC77A0 · friction 0xCBE74`), `u32 @ arr + mode*4`,
  **34 distinct records over 34 modes, zero sharing.**
- Layout: `base+0` u16 n · `base+2` n×i16 X · `base+2+2n` n×i16 Y · `base+2+4n` u16 terminator; `4+4n`.
  🛑 **X starts at base+2, NOT base+4** (reading at +4 silently yields `[X1,X2,X3,Y0]`).
- 🛑 **THE COUNT FIELD IS NEVER READ.** The lookup is a real `while (X[i] <= idx) i++` loop, but `n` is
  pinned per factor by three hardcoded immediates — B/C/E `rec+10 / rec+8 / rec+0x10` (n=4), D
  `rec+0xc / rec+10 / rec+0x14` (n=5), ceiling `rec+6 / rec+4 / rec+8` (n=2). **More points = a CODE
  edit to the always-on base-assist damper = the class that bricked V24/V27/V48B.**
- ★★ **THE OUTPUT IS HARD-CLAMPED**: `gp-0x6bd0 = clamp(product, ±ceiling_LERP(gp-0x6ac2))`, ceiling
  record n=2 `X=[300,800] Y=[512,1024]`, fallback `*(u16*)0xC6158 = 512`. **`|gp-0x6bd0|` can never
  exceed 1024, and is 512 at low ceiling index.** This — not the point count — is the binding constraint.
- `gp-0x6bd0` is **lockstep-shadowed at `gp-0x4cf2`**. Two gates zero the chain: FactorC → unity if
  `(gp-0x6a5e > 0x7d00) || (gp-0x67f4 != 1)`; damper → 0 unless
  `(gp-0x6ac0 < 0x32c9) && (gp-0x6abe + 13000 <= 0x6590)`.
  🛑 **`gp-0x67f4` has never been probed** and disables FactorC's speed shaping entirely.

★★★★ **WHY THE ReLU PLAN INVERTS.** A ReLU is 2 DOF; a 4-point table has 8 numbers and spends 3 on
collinearity, so **more points buy EXACTLY ZERO for a pure ReLU** (constructive witness in the handoff).
**The constraint that breaks is parameter-free:** a ReLU FactorC is speed-proportional, so
`dose(v,99)/dose(515,99) = v/515` *whatever values you pick* — pinning 206 at 5 mph forces **3,593 counts
at 140 km/h = 7.02× the 512 ceiling**, railing above **3.2 °/s at 140 km/h, 7.0 at 60, 21 at 20 km/h**.
★★ **A railed damper whose sign comes from a different cell (`gp-0x6abe`) than its index (`gp-0x6ac0`)
IS the Coulomb relay — you would forbid it at `E_Y[0]` and re-create it at the ceiling.** On V76's flat
FactorC the same dose rails no earlier than **563 °/s — 176.7× more usable linear range.**
⚠ **"Which factor isn't a ReLU" has two readings that point at OPPOSITE tables** — literal
`max(0,k(x−x0))` indicts **FactorC** (566 floor); the operator's own recorded gloss in `studies/sessions/v76/v76_surface.py`
(*"FLAT — no taper down, like a rectified linear unit"*, read as a floor clamp) indicts **FactorE**
(three slopes: 2.521 / 0.100 / 0.259 per count). **Neither should be made a literal ReLU.**
📋 **RULE: ask anyone proposing a re-point which FOURTH segment they need. If they can't name it, n=4 is
enough.**

⊕ **Relocation is AVAILABLE though not needed** — it is **cal-only**: one u32 into `0xC9F04` /
`0xC9FEC`. **`0xD7BB8`–`0xD7FEF` = 1,080 B virgin `0xFF`, same page, same CRC block `0xD7FFC` V76
already recomputes**; the same run exists at the same offset in every mode-record page. Confirmed
unreferenced by a byte-granular whole-image u32 scan. **V74's "pointer arrays must stay byte-identical"
was a SELF-IMPOSED BUILD GUARD, not a firmware requirement** (sole reader dereferences without
comparison; the only flash writer `FUN_0000d934` has zero static callers; the CRC verifier
`FUN_0000b006` is UDS-only). 🛑 Leave `0xD7FF0`–`0xD7FFB` alone (`0xD7FF8` is the block self-descriptor).
⊕ **New Ghidra trap: `get_xrefs_to(0xD780C)` returns "No references found"** though the pointer exists at
`0xC9FEC`; the twin `0xD77D0` resolved fine. **Do not trust xref completeness on pointer-array slots.**
⊕ **A free, never-touched lane: FactorD is n=5, flat `Y=1024` (inert) in modes 24 AND 26**, axis
`gp-0x6a10` (angle-tracking error), gated `gp-0x67fe ∈ {1,2}`. UNTESTED, not falsified.

## 🛑 METHODOLOGY — three conventions that were producing wrong answers

These invalidate *reasoning* behind earlier conclusions. None changes a measured on-car outcome, but
every historical amplitude comparison needs rebuilding before it can be trusted.

1. **`carState.cruiseState.enabled` is LONGITUDINAL + LATERAL and is the WRONG engagement proxy.**
   It reads **0.00%** on V55 route `1c`, V56 route `24` seg 0, and V57 route `29` seg 1 — parking-lot
   routes where lateral was demonstrably applying. On route 28 it reads 84.0% while lateral applied 49.9%.
   **Use `carControl.latActive`, corroborated by CAN `0x18F` byte4 bit3 (`STEER_CONTROL_ACTIVE`).** The
   three agree to **99.85–99.94%**. Using cruiseState flipped V57's headline verdict from INERT to
   NOT INERT, and inflates V56's creep baseline **28×** by sweeping in hands-on parking manoeuvres at
   |ang| 89.6°.
2. **Hands-off must be SUSTAINED effort `|lowpass(tq, 3 Hz)| ≤ 200`, never raw `|tq| ≤ 200`.**
   The oscillation is ±1400 counts *on the torsion-bar channel itself*, so it trips the raw test by
   itself: 68.3% of frames scored "hands-on" have the driver doing nothing sustained. On genuinely quiet
   frames the raw test **keeps** 390 frames with oscillation rms 103.5 and **drops** 746 with rms 909.2 —
   **8.79× the amplitude.** It selects *against* the phenomenon. Switching recovers 2.5× more usable
   frames and turns subsets that had no contiguous run into computable numbers.
3. **Mean Welch power is the wrong statistic for a bursty limit cycle — use peak/p99 envelope.**
   V57/V55 grinding: median 0.419 but **p99 0.891, max 0.898**. The "halving" lived entirely in the
   median, which is dominated by quiet time between bursts. Operator called this before the data did.

✅ **A fourth problem, SOLVED 2026-07-30 by route `2b`:** engagement and motion used to be collinear —
no speed bin on any route had ≥3 windows in both arms, so the recorded ratios (877×, 786×, 14,750×,
27.7×) were moving-vs-stopped contrasts wearing an engagement label. **Route `2b` breaks it**: seg 13 is
60 s of *moving but disengaged* at 0.5–4.8 m/s against engaged creep at overlapping speeds, giving 3 of
9 speed bins with windows in both arms (18 v 18 windows, but only ~10 independent episodes per arm —
treat n as episodes, not windows). ⇒ **13.4× amplitude [95% 3.9–19.8], 16.9× speed+effort-matched.**
🛑 The old ratios stay retired; **do not resurrect 877×/786×/14,750×** — they were never engagement
contrasts. Quote the route-`2b` numbers, or absolute engaged powers.

⚠ **A fifth convention, learned the hard way this session: use a STRICT 18–26 Hz band plus a presence
test, never a wider search band.** A 15–30 Hz or 17–28 Hz argmax catches the ratchet's 2nd harmonic
(2×8.0–8.9 Hz = 16–17.8 Hz) at road speed and steps down to ~15 Hz, manufacturing a *negative* frequency
slope out of a mode switch. Two independent analysts produced two contradictory "frequency laws" this way
before the band was tightened.

⚠ **A sixth: prominence, not envelope amplitude, is what separates a mode from broadband.** The
disengaged arm's loudest 18–26 Hz moments are single-digit prominence at |ang| up to 295° — a driver
cranking a wheel. An envelope-ratio headline divides one broadband spike by another; the prominence
contrast (34× grinding vs 6.1× ratchet) and the presence/absence are the defensible statistics.

---

## Signal-identity corrections of record

- 🛑 **`0xC61B2` / `0xC61B4` ARE NOT "the pre-gain deadband arm" — corrected 2026-08-08 (late).** They are
  **output clamps on the forward path**: `0xC61B2` (= `±tp+0x71b2`) is the **arbitration output clamp**
  in `FUN_0002b422`, and `0xC61B4` (= `±tp+0x71b4`) is the **LKAS-gain output clamp**. They were doubled
  **alongside the LKAS gain**, in lockstep, at both steps: stock **512 → 1024 at V22 → 2048 at V38 = 4×
  Honda**, and unchanged since. **The pre-gain deadband is a DIFFERENT cell — `0xC61B8` = 102 — and it
  was never rescaled** (that is the whole point of the deadband box in `BUILD-LINEAGE.md`). [EVIDENCE]
  ⚠ **The wrong label is still live in two build scripts**: `analysis-2020accord/builds/v80_v107/build_v83a_tva.py:359-360`
  and `analysis-2020accord/builds/v80_v107/build_v84_tva.py:544-545` both read `"pre-gain deadband arm."` in their KEEP
  lists. **Comment-only; no byte is affected** — but fix it before the label propagates into a third build
  (NEXT item 7).

- 🛑★★ **`gp-0x6c2c` — the oscillation detector's input — is a MOTOR-RATE DERIVATIVE, not torque and not
  a raw per-tick difference.** Produced in `FUN_00041464` @`0x4184E`; all cals byte-read LE:
  ```python
  K1 = 37     # cal 0xC643C, >>7        K2 = 22   # cal 0xC40DC, >>6
  x      = s16(gp-0x4f50)                            # resolver/motor ELECTRICAL RATE
  if abs(x) > 13000: gp_0x6c2c = 0x7fff; return      # validity ceiling -> fault sentinel
  target = x * 1024
  step   = ((target - old) * K1) >> 7 ; old += step   # EMA #1 increment -- THE DIFFERENCE
  acc    = clamp(step * 0x20, -0xfa0000, 0xfa0000)    # x32, clamp +-16,384,000
  state += ((acc - state) * K2) >> 6                  # EMA #2
  gp_0x6c2c = state >> 9                              # range +-32,000; T = 40.0% of that
  ```
  ⇒ **an ACCELERATION** — differencing kills DC, so a sustained large steering input cannot drive it.
  Sibling `gp-0x6c2e` takes the same `acc` through a slower EMA (cal `0xC40DA` = 3, `>>7`).
  **Sizing:** a 21.3 Hz sinusoid needs `|gp-0x4f50|` ≈ **1683** counts @1 kHz / **1821** @100 Hz to trip
  `T` — inside that signal's own ±13000 validity ceiling, so **the detector is NOT structurally blind to
  the mode; the drive was ~1.7–2× short.** Independently reproduced in the frequency domain
  (`|1-H1|`=0.43041 × `|H2|`=0.95375 ⇒ `gp_0x6c2c = 7.5965·U` ⇒ U = **1685**) — 4 significant figures by
  a different method. The `acc` clamp bites at U ≈ 4017 ⇒ `T` is reached at ~42% of saturation, linear there.
  🛑 **Do NOT size `T` from bus torque.** A pass this session derived "T ≈ 2048–2560" and "LSB ≤3.29×
  finer" from the `0x18F` torque channel; **both are VOID** — `gp-0x6c2c` is not torque-derived and does
  not share that LSB. Also void: a "per-tick rate ⇒ effectively dead" reading that priced the chain at
  unity gain and missed the `×1024` and `×32` pre-scales, which are invisible from the bus.
  ⚠ `gp-0x4f50`'s physical units remain **untraced** (needs the ISR writing `gp-0x29c4`, or a probe), so
  1683 is in raw counts of a signal whose scale is unknown.
- 🛑★ **`gp-0x671a` is NOT private to the rate lanes — 4 external consumers.** Byte-scanned both
  encodings, whole image: 8 real hits, 6 reader functions, sole writer `0x42A12`. External:
  **`FUN_0003a382`** (a **continuous LERP index**, not a gate, shaping the live P/I/D lane `gp-0x6ad4`),
  **`FUN_00036c12`** (friction-comp `gp-0x6b26`, sums into the *same* aggregator; ⚠ its own gate uses cal
  `0xC64FD`, **not** CEIL), **`FUN_000352b4`** (gates a 2nd-order IIR update), **`FUN_00035b20`** (selects
  between two LERP-blend curves). ⇒ **lowering `T` changes five things at once.** By contrast `gp-0x67df`
  is **clean** (2 hits, both inside `FUN_000428d4`) and `T` itself has 4 readers, all inside the detector.
  `CEIL` (`0xC64FA`) is **not** private — 3 external readers.
  ✅ `gp-0x671a` is logged into a diagnostic record array each low-torque tick (`FUN_00045608(2,…)`) but
  the DTC-0x21 dispatch in that tail reads a *different* array (`gp-0x6544[2]`, producer untraced) ⇒
  "touches diagnostic logging, does not appear to gate a fault" — not chased to full closure.
- 🛑 **`0xC64FA` (CEIL) is a BYTE cal = 5, read by `ld.bu` @`0x3AA78`.** A halfword read gives **517** and
  is wrong. Lowering CEIL means writing one byte. (`T` at `0xC620A` *is* a halfword, `ld.h`, = 12800.)
- 🛑 **`gp-0x671d` is NOT "r24's override flag".** It is a **saturating rising-edge counter on a
  torque-residual/observer check** (`FUN_00041d56`, 5-tap filter combination vs `tp+0x71f8`/`0x71fa`),
  feeding DTC dispatch `FUN_00016de6(0x5e,…)`, reset only by `FUN_0003bcb2`'s resync — **not** every tick.
  8 reader functions including the motor-off dispatcher `FUN_0003d4a2`. It read **0** for all of route
  `35`, so r24 *was* covered by V64's arm. Writer/reader set confirmed exhaustive by whole-image raw byte
  scan in **both** encodings (disp16: 16 hits; disp23: 0).

- 🛑★★ **`gp-0x6ba6 == |gp-0x6b9a|`, and `gp-0x6ba6` — not `gp-0x6b9a` — is the boost amplitude index.**
  Byte-verified 2026-07-30; **`builds/v50_v79/build_v58_tva.py`'s docstring was wrong on both counts** and is corrected
  in place. `FUN_0003b66a` writes both from the same r28 (`cmp r0,r28 / mov r28,r13 / bge / subr r0,r13`
  @`0x3b874-87c`, then `st.h` @`0x3b892` and `@0x3b8b0`; byte-scanned for **both** gp-relative encodings:
  exactly one writer each). `gp-0x6b9a`'s only live consumer in `FUN_00034a72` is a **five-input
  plausibility gate** (`|x| ≤ 25600` @`0x34c9c-cb4`, ANDed with `gp-0x6ba6`/`gp-0x4f68`/`gp-0x4f60`/
  `gp-0x6c2e` into r21, which zeroes r24 @`0x34fc8`) — **its sign has no effect on the output**, and two
  of its three reads there (`0x34b5e`, `0x34b68`) are **dead** (`tp+0x7499 = 1` takes the branch
  @`0x34b3c`). **`0xD28DC` hangs off pointer table `0xca4f4`, NOT `0xca23c`** (which resolves to
  `0xD2888`); resolved from image bytes across all 34 modes.
  ⇒ **THE MECHANISM:** V58 measured the *signed* sibling crossing zero at 20.93 Hz only when LKAS
  applies, so the index is that signal **full-wave rectified** — a minimum at every zero crossing,
  sweeping the boost amplitude curve (`0xD28DC` Y = 16384→8187, `0xD2888` Y = 16384→8176) at **~2× the
  mode frequency on the BASE ASSIST path**. ⚠ **INFERENCE, depth unmeasured**: a sign bit carries no
  amplitude, and the delivered swing depends on how far up the curve the index climbs —
  `<512 ⇒ ≤1.12×`, `1024 ⇒ 1.27×`, `2048 ⇒ 1.58×`, `2529 ⇒ 1.75×`, `≥5120 ⇒ 2.00×`. ⚠ **Not "inert"
  below 512** — the LERP interpolates from X = 0, so it is pinned at 16384 only at exactly zero.
  **V59 measures which regime. Do not move `0xD28DC`/`0xD2888` until it has flown.**
- ⚠ **`FUN_0003b66a` branch A is NOT a biquad** — a subagent claimed "a genuine floating-point 2-pole
  biquad, IIR by definition"; it is not. `tp+0x5018/501c/5020` = `0xC4018/1C/20` read **(1.0, 0.0, 0.0)**
  and the code is `y = b0·x[n] + b1·x[n−1] + b2·x[n−2]` with two *input* delay states — a delay line, not
  feedback. **Stateful ≠ recursive.** It is the identity 3-tap FIR already on record, so **"no biquad
  anywhere" survives and there is no new notch candidate.** Also new: `tp+0x74be = 0` (`0xC64BE`) makes
  `0x3b736–0x3b758` (the `divf.s` block) dead code.
- ⚠ **`search_instructions` undercounted again** — 8 access sites for `gp-0x6b9a` where a Python byte
  scan finds **9** (it missed V58's own cave read at `0xC4B4E`, an unanalysed region). The sole-writer
  conclusion held, but only because it was re-derived. **Never let a writer/reader set rest on it alone.**

- 🛑★★ **`gp-0x6a56` is NOT independently sensed.** `FUN_0003f776` (sole producer, 4 `st.h`, all inside it):
  `gp-0x6a56 = clamp(polarity × ((gp-0x6abe × 48 × cal(tp+0x713a)) >> 15), ±12000)` — a fixed Q15 scale of
  the **motor/resolver electrical rate**. The ±12000 is a magnitude clamp recomputed fresh each tick, not a
  rate limit; `gp-0x6a60` merely mirrors its magnitude. ⇒ **`STEER_ANGLE_RATE` is opendbc-named but is not
  an independent angle sensor**, so "996× on rate vs 877× on torque" is two EPS-internal derivations, not
  independent corroboration. And since `gp-0x6bbe`'s `baseline` is **also** `gp-0x6abe`-derived,
  `rate_error = baseline − angle_rate` may partially cancel ⇒ **the damping sign is UNRESOLVED.**
- 🛑 **`FUN_0004613e` is not a rate limiter.** It snapshots params into log cells and calls
  `FUN_00016de6(0x1c,…)`, a fault logger; **`0x3638` (13880) is a diagnostic TAG** (the same callee takes
  `0x38c7` elsewhere). The `gp-0x6bb2/4/6/8` cluster is a cross-tick **integrity watchdog** re-deriving the
  same ±512 ceiling in float, with **no forward path into any control signal**. Golden model corrected.
  ⚠ Its fault path calls `FUN_000462e6(0x39e9,…)` **ungated** — Monitor 2's hard-shutdown chain. Any edit
  to `gp-0x6bbe`'s ceiling math must update `FUN_00035154`/table `0xD2018` to match, or it may trip.
- 🛑 **`0xC6372`/`0xC636E` is a DEAD BRANCH.** `tp+0x7498 = tp+0x7499 = 1` (byte-verified, stock and every
  build) routes **both** boost and damping past the torque-EMA fallback to read `gp-0x6ba6` directly. Any
  GATE-2 analysis of those two cals is analysing a lever with zero effect on this firmware.
- **The FIR slots are real but cannot notch.** `FUN_0003b66a` implements a genuine **3-tap transversal FIR**
  (`y[n] = b0·x[n] + b1·x[n−1] + b2·x[n−2]`, two persisted delay states `gp-0x365c`/`gp-0x3658`) — **not a
  2-pole IIR biquad**, so it is unconditionally stable. Coefficients `0xC4018/1C/20` = floats
  **(1.0, 0.0, 0.0)** = identity; a second instance `0xC4048/4C/50` (`FUN_0003b8f6`) is also identity.
  Exactly **one consumer each**. See "closed levers" for why enabling them fails.
- 🛑 **The ±565/cycle slew in `FUN_0003b66a` is a CODE IMMEDIATE** (`mov 0x440d4000,r6` = 565.0f), not a
  calibration. Editing it is a code-patch-class change. The halfword 565 in the cal region
  (`[0,191,402,565,686,804,878]` at `0xCE43C` etc.) is an unrelated LERP entry — numeric coincidence.
- ⚠ **The two `STEER_ANGLE_RATE` copies disagree by a constant 1.25×** (`0x18F[2:4]×−0.1` reads 0.799–0.800
  of `0x14A[2:4]×−1.0`, corr +0.9997). One DBC scale factor is wrong. Frequencies, Q, prominence and ratios
  are unaffected; **absolute deg/s figures are not.**
- 🛑 **`STEER_STATUS` is `0x18F` byte4 bits 7:4**, not bits 2:0 (which are SPARE — never written anywhere in
  the image, boot-zeroed, read 0 forever). Reading bits 2:0 yields a tautological "always 0". Route 29 shows
  `ST==3` in **120 frames**, all at `vEgo == 0.000` exactly, never with LKAS applying, in two episodes
  (1.08 s at log start, 0.10 s at t=77.8 s). **Not a V57 regression** — `0xC62EA` is byte-identical across
  V55/V56/V57. Amends the record's "ST=3 never fires on V53+".
- 🛑 **The "8.69 Hz line V56 introduced" never existed — it is wheel order 1.** V56's 35 windows sat at
  v ≈ 18 m/s where `0.489·v − 0.186 = 8.69`; its own edge windows move to 7.03 and 9.77 Hz, and V57 tracks
  identically (7.03 → 8.98 → 9.38). **Its absence on V57 is NOT evidence the `0xC6AF0` mute was live** — a
  different liveness proof is needed.
- ⚠ **The recorded V56 baseline `7.66e4` is suspect** — within 5% of route 24 seg 0's *all-frames* power,
  and that segment contains **zero** LKAS-applying frames.

---

## ✅ The tyre line — CONFIRMED, firmware-independent, and actionable

Order tracking (rescale each window's frequency axis by its own wheel frequency before pooling) puts
**both** builds at **order 1.000**:

| build | K | v range | order peak | prom | implied circumference |
|---|---|---|---|---|---|
| **V57 / r28** | 9 | 4.2–20.1 m/s | **1.000** | 11.7 | **2.088 m** |
| V56 / r24 | 59 | 9.5–20.5 m/s | **1.000** | 6.2 | **2.088 m** |

Estimator calibrated on V56 first, where the answer was known. Decoys at order 0.70/1.40/1.80/2.00 all
score far below. Per-window on V57's road episode: 2.056–2.105 m, with a 715× prominence burst at
19.5 m/s. A 235/45R18 is 2.05–2.11 m ⇒ **one line per wheel revolution**.

⇒ 🛑 **Get a wheel balance / road-force check.** Firmware cannot move a road input, and it didn't.

★ Separately, a **fixed ~7.4 Hz resonance** is present on V57 (Q 36.2 at nfft=1024, prominence 40–136×) at
1.2 m/s where wheel order is only 0.59 Hz ⇒ **not the tyre**. It is the ratchet. Route 28's creep misses it
because that creep is |ang| 5.8° — **excitation, not absence** (r29 creep is 26.5°, matching the historical
set's 12.6–42.2°).

---

## Still-standing results worth not re-deriving

- **`gp-0x6966` authority ≡ 0 by design on V31+** — soft-EME wind-up magnitude, pinned by V31's boost
  floor; `0xC6AF0` selects unity in 100% of normal operation. Measured on-car, route `1b`, 5,989/5,989.
- **Steer-to-zero works** — `0xC62EA` = 0, `ST=3` never fires while moving, 226 frames of
  `STEER_CONTROL_ACTIVE=1` below 5 km/h on route `1a`.
- **The `0x14A` byte4 bits 7:3 piggyback is proven across FOUR flashes** (V54, V55, V56, V57). Use it for
  all future firmware telemetry; **do not build another new-mailbox channel** (FOURFRAME2 was never
  transmitted — that null remains uninterpretable).
- **No notch/biquad exists anywhere** on the arb, aggregator, r24/r26, comp-add, boost/damping/friction,
  shaper, or governor paths, nor in the three non-aggregator consumers of `gp-0x6b94`
  (`FUN_0004503c` governor, `FUN_0004595a` redundancy monitor, `FUN_0007ff08` boot interlock). Two regions
  remain unswept: the raw CAN → `gp-0x4f60` producer, and the FOC current loop below `gp-0x6b98`.
- **An rlog cannot identify the flashed build from the version string** — every build reports
  `fw='39990-TVA,A160'`. Behaviourally: `ST=3` never firing while moving ⇒ V53+; probe field semantics
  identify V54/V55/V56/V57/V58 exactly.


---

## ⚠⚠ SUPERSEDED 2026-08-13 — THE BLOCK BELOW IS A RECORD, NOT THE CURRENT STATE
🛑 **It said "ON THE CAR: V94 … Still flashed" and that is FALSE.** V94 was aborted and superseded by
V96 → V97 → **V98**, which is on the car as of route `0x81` (identity single-frame, `0x14A`
byte7[7:6] == 2, duty 1.000000, 17,983 frames). **The head of this file is the authority.**
⇒ This was one of SIX stale flight-status claims found and corrected in one sweep on 2026-08-13
(`STATE.md` ×3, `BUILD-LINEAGE.md` ×3). **Run the gate at EVERY close-out — it fails loudly, memory does not.**

## ON THE CAR RIGHT NOW, AND WHAT IS BUILT — ⚠ SUPERSEDED, SEE ABOVE

🛑🛑 **ON THE CAR: V94 — AND THE OPERATOR STOPPED DRIVING IT.** Flown as route `7d`, 2026-08-12,
**fault-free**. *"It vibrated the entire car, and I decided it was not safe to drive."* **Still flashed.**
image sha256 `cd971c05d483fe9c…` · rwd sha256 `3feccc09d8cbdd05…`
V94 vs stock: **245 differing bytes in 114 runs, zero unattributed** — full table in
`docs/handoffs/2026-08/HANDOFF-2026-08-12-v94-aborted-and-the-override-regime.md` §6b, reader
`analysis-2020accord/studies/ledger/ledger_v94_cells.py`.

**Unflashed candidates on disk:**
- **V92 — the REVERT candidate.** rwd sha256 `388a1974d5702e17…`. The last configuration the operator
  drove and did **not** abort (route `79`, identity proven single-frame). Its cal row is **stock on
  three of five sites and ×1.5 on modes 26/27** — "revert to V92" is *not* "revert to stock".
- **V93** — carries V94's cal without the packer rescale. Valid artefact, measures itself poorly.
- **V96** — the instrument build cut at the 2026-08-12 close-out. **The live candidate.** See §A6.
  🛑 **V95 is a VACATED number** — three artefacts wore it; do not reuse it.

🛑 **Flashing is gated on the operator naming the file and the bus, every time.**

🛑 **Before proposing any calibration edit:** grep `analysis-2020accord/build_v*_tva.py` **and**
`docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md` for the address, and state its on-car result.
`FALSIFIED` ≠ `INERT-BY-MODE` ≠ `never-tried`, and *"the same lever pushed the other way"* is a
different claim from *"a new lever"*.

---

## RECOMMENDED NEXT STEPS, IN ORDER

🛑 **NO openpilot-side modifications.** Standing operator instruction; openpilot is a measurement
instrument only.
🛑 **Score in the regime the operator drives in: ENGAGED + HANDS-ON + OVERRIDE, on BAND POWER.** §A2.
The corpus already holds the exposure — what it does not hold is 5.12 s windows (**only SEVEN**).

1. 🛑🛑 **GET V94 OFF THE CAR.** It is the only build the operator has ever aborted. Whether that is
   V96 or a straight V92 revert is his call and needs him to name the file and the bus.
2. ★★★★★ **Answer the two questions that are waiting on the operator, before cutting another lever:**
   (a) does he feel a **slow lurch or "catch"** during override, distinct from the buzz? (§A3 — a
   quantified ~0.5–1 Hz surge mechanism is sitting there unattached to any complaint);
   (b) does the car feel **different left versus right**? (`0xC63F8` = 33 vs `0xC63FC` = 328 is a
   **10×** asymmetry, virgin on all 85 images, and nobody has ever asked).
3. ★★★★ **Resolve the two live leads in §A6b** — `0xC63A6` (a virgin second multiplier on the lane
   whose direction is now measured) and `0xC64B8` (non-stock for 66 builds, sitting exactly in the
   high-driver-pushback regime). Both have traces in flight; **neither is EVIDENCE yet.**
4. ★★★ **Rebuild the band estimator for override.** Point-process or event-triggered, or 1.28 s
   windows. Every existing band number in this file comes from a 5.12 s window in a regime the
   operator does not produce the symptom in.
5. ⚠ **Audit whether any HISTORICAL result rests on the crossed `raw14` pairing** (the kit-wide
   off-by-one found on route 73). Safe pairings are `(t, probe)` and `(raw14_t, raw14_b4)` — never
   crossed. The defect predates route 73 by at least eight routes and **has not been audited backwards.**
6. ⚠ **`0xC64DE` = 25627 has been non-stock since V22 — 85 builds — with a disputed label and no
   isolation.** The longest-carried unmeasured cell in the image. Not implicated in anything current.
7. 🛑 **`analysis-2020accord/model/eps_lkas_chain_model.py` IS 297 KB AND IS OVER THE `Read` CAP. NOT FIXED.**
   Found at the 2026-08-12 close-out — the **fourth** instance of this defect, and the worst-placed,
   because `CLAUDE.md` makes the golden model **mandatory reading before evaluating any lever**:
   *"a lever is only understood once you can say where it sits in that chain."* At 297 KB an agent
   that reads it whole gets a **silently truncated tail**, and the tail is where the newest chain
   corrections live. ⚠ It was already over before this session; my own edits took it 292.8 → 297.4 KB.
   **NOT fixed deliberately:** it is a live, importable, re-runnable Python module, a builder was
   mid-cut, and module surgery under those conditions is how you break the one artifact everything
   else is checked against. **Fix pattern:** the file is mostly comment blocks — lift the narrative
   commentary into a companion `docs/GOLDEN-MODEL-NOTES.md` and leave the executable model lean, or
   split by chain stage into an importable package. **Assert `import` + a round-trip run before and
   after, exactly as the lossless carves in item 8 were asserted.**
8. ✅ **DONE 2026-08-12 — the `Read`-cap defect is fixed in the other three places.** `memory/MEMORY.md` was
   287 KB (split verbatim to `MEMORY.md` + `MEMORY-PART2.md`, 312 links before and after, none lost);
   `docs/BUILD-LINEAGE.md` was 293.8 KB (Part 1 carved to
   `docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md`, lossless carve asserted in code); this file is back
   under cap. 🛑 **The 170 SUPERSEDED/DEAD/FALSIFIED bullets were deliberately NOT pruned** — they are
   load-bearing, and four candidate levers were killed by them in one session. **The cause is hook
   length (829 B average). Compress hooks; do not delete pointers.**
