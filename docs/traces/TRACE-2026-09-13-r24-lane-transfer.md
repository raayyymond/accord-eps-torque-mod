# TRACE — the r24 base-assist rate lane, modelled: `L_r24(f)`, 3–30 Hz

**Subagent `r24lane`, 2026-09-13.** Analysis only — nothing built, flashed, or sent on any bus; no build
script edited; no commit. Every decision-bearing claim is marked **EVIDENCE** (with its method) or **BELIEF**.

**Deliverables**

| file | what |
|---|---|
| `rlog-tools/studies/grind/r24_lane.py` | **the importable arm** — `R_r24(f)`, `R_r24_poly()`, `servo(f)`, `gate73()`, `hp_cave()`, `bp_cave()` |
| `rlog-tools/studies/grind/r24_lane_transfer.py` | the model: the byte-exact chain, the `B(f)` rational fit, the budget, the option table |
| `rlog-tools/studies/grind/r24_plant_refit.py` | the plant family re-fitted **with the r24 arm in the loop** |
| `rlog-tools/studies/grind/b_of_f_v282.py` + `B-OF-F-V282-2026-09-13.md` | `B(f)` measured on r39 + r6c (sibling agent) |
| `_scratch/kappa_scan.py`, `_scratch/dzeta_both.py`, `_scratch/dzeta_stable.py` | the discriminating scans |

---

## 0. Headline

1. **The lane is a 4 ms backward difference of the torsion-bar torque, Q10 gain, with a deadband that is
   already a cal cell.** From the bytes:
   `d[n] = (u[n] − u[n−4])>>1` at 1 kHz → clamp ±5120 → `×gain/1024` (`0xC6446` = 5244 engaged) →
   **deadband 3 (`0xC61F6`)** → **negate** → clamp ±8192 → `gp-0x6b94` with a **unit coefficient**.
   ⇒ `R_r24(f) = −κ·(gain/1024)·D4(f)·B(f)`, `D4(f) = ½(1 − e^{−j2πf·0.004})`. **[EVIDENCE]**
2. **`gp-0x6ada` is NOT the derivative.** It is the lane's post-clamp **output mirror**, written once at
   `0x3ad5a` with **no reader anywhere in the image**. The lane's input is `gp-0x4f62`, shared with r26.
   The record's "4-tap derivative of `gp-0x6ada`" was wrong on both halves. **[EVIDENCE — tracer]**
3. **r24 : LKAS is 1 : 1 at the aggregator, and the aggregator is the motor command.**
   `gp-0x6b94` → governor `FUN_0004503c` → `gp-0x6ace` → `gp-0x6acc` → `gp-0x6b08` → `gp-0x6b98`,
   byte-verified. This is the number the whole model rests on. **[EVIDENCE — two agents, independently]**
   🛑 **CORRECTION, from agent `ghidrafill`'s later and better-resourced trace
   (`TRACE-2026-09-13-lkas-lane-to-aggregator-and-ghidra-gap.md`), which supersedes my own tracer on this
   point:** the LKAS lane reaches the aggregator as **`gp-0x6b4c`**, read at `0x3aa3e` in `FUN_0003aa2c`
   as a **direct summand with UNIT weight** — *not* `gp-0x6ad4`, and `gp-0x6b38`/`gp-0x6b3c` is a stage
   on that path rather than a dead copy (`0x2B41C` is a **dead twin**; the live forward is `0x2a2ea`).
   **The 1 : 1 conclusion is unchanged and now rests on a re-derivation I did not make.**
   ⚠ **One refinement I did NOT model:** the LKAS lane enters the aggregator by a **second, indirect
   route** as well — `gp-0x6b4c` → `FUN_00038148` → `gp-0x6b70` → `gp-0x6ad6` (the reference of a
   *driver-torque tracking* PID) → `gp-0x6ad4`, a second summand. **So my `R_servo` is a LOWER BOUND on
   the LKAS arm, and every r24 share below is correspondingly an UPPER bound** — which pushes in the same
   direction as the small κ of §4.
4. **The transfer reproduces the record at 20 Hz on independent routes**: `R_r24(20.3)` = **3.51 ∠ +5.6°**
   against `GRINDING-DEEP`'s **3.23 ∠ +5°** — 8.8 % in magnitude, **0.6° in phase**. The servo arm comes
   out **1.74 ∠ −72.6°** against its measured **1.90 ∠ −69°**. **[EVIDENCE]**
5. 🛑 **THE MAGNITUDE OF THE r24 ARM IS NOT 1× THE CLOSED FORM, AND THREE LINES SAY SO.** The cave's own
   bit-6 comparator inverts to **κ ≈ 0.45**; **V289's measured relocation of the mode by a servo-side notch
   is IMPOSSIBLE at κ = 1.00** and best at κ = 0.10–0.20; and V281 rev 3's extinction of the 7 Hz cycle is
   only consistent with the small-κ budget. Only the record's own normalised 7.3 Hz split points the other
   way (κ ≈ 1.45). **Default κ = 0.45, bracket [0.10, 1.00].** **The phase is not in dispute.**
6. **THE RECORD'S TRADE STANDS, AND IT IS SHARPER THAN THE RECORD PUT IT.** At every κ the evidence
   actually supports (0.10–0.45), r24 **damps** the 20 Hz mode and cutting `0xC6446` costs damping
   **monotonically**. Taking it to **Honda's own 2048** drives the mode from ζ ≈ 0.030 to **ζ ≈ +0.005 …
   −0.011 — marginal to unstable — and drops its frequency 20.0 → 18.2 Hz**, which is V289's own
   revert signature. **[EVIDENCE for the sign, from a flown two-way ladder; BELIEF for the magnitude.]**
   ⇒ **Do not cut `0xC6446` as a grinding measure.** The record's DO-NOT-FLASH holds.
7. ⚠ **But "Re > 0 = damping" is the wrong tool, and it nearly cost me the right answer.** The real part of
   a lane's phasor is not its damping contribution — the lane acts through the plant, which carries its own
   phase — and on one perfectly defensible plant family (V282's pole alone, κ = 1.00) r24 comes out
   **de-damping** while Re(R_r24) = +3.5. **Use the pole and the flown record, never the sign of Re.** §5.
8. ⭐ **The obvious way to split the trade — a high-pass on r24 — is DOMINATED, and two doses of it FAIL the
   7.3 Hz gate outright.** A one-pole high-pass adds **lead**, and at 7.3 Hz r24 already sits at +171°, so
   the lead rotates it *towards* the critical point faster than the magnitude cut pulls it away. HP 5 Hz
   and HP 8 Hz push `gate73` to **1.124** and **1.064** — they **re-arm the 7 Hz strong-turn cycle**. §7.

---

## 1. The lane, from the bytes

Integer mirror, each line carrying its instruction address. This is the kit's own mirror
(`v282_r24_tap_read.r24_series`) re-derived from the image by the tracer.

```python
# FUN_0003aa2c, the base-assist aggregator, 1 kHz task
u   = bar[n]                       # gp-0x4f62, torsion-bar torque, dual-channel lockstep-mirrored
                                   #   (gp-0x4f60 = -bar is the differentiated channel; SHARED with r26)
d   = (u[n] - u[n-4]) >> 1         # lag-4 BACKWARD DIFFERENCE at 1 kHz  ==  4 ms,  NOT a 4-tap FIR
d   = max(-5120, min(5120, d))     # pre-gain clamp
g   = 1024   if gp-0x671d != 0     # 0x3ABFE  ld.hu 0x7442[tp] -> 0xC6442   the first-strike latch arm
    else 5244 if lp != 0           # 0x3AC08  ld.hu 0x7446[tp] -> 0xC6446   THE ENGAGED ARM (V67+)
    else 2048                      # 0x3AC12  ld.hu 0x7440[tp] -> 0xC6440   Honda's own fixed arm
    else <mode-10 LERP surface>    #          2150-3072 at creep, axis = rectified column rate gp-0x6ac0
s   = (d * g) >> 10                # signed mul + sar 0xa   =>  Q10:  5244/1024 = 5.121 x
s   = 0 if abs(s) <= 3 else s - sign(s)*3     # DEADBAND, cal 0xC61F6 = 3, AFTER the gain
r24 = max(-8192, min(8192, -s))    # 0x3AD5A  st.h -> gp-0x6ada   *** NOTE THE NEGATION ***
agg = ... + iVar21(r26) + iVar16(r24) + <LKAS lane>       # UNIT COEFFICIENTS
agg = max(-0x2800, min(0x2800, agg)) -> gp-0x6b94
```

**Gate.** Byte `0x3AA96` (`fb` since V104) repoints the lane's arm selector to `STEER_CONTROL_ACTIVE`, so
the 5244 arm is **engaged-only and live**. The same one-byte repoint raises r24 **and** cuts r26 6.00×
(`BUILD-LINEAGE-PART1` — every published multiplier in this kit is an r24-only number computed at `a = 0`).

**Tick rate.** 1 kHz. The mirror upsamples the 100 Hz logged bar ×10 and differences at lag 4, which is
what the record has always done; the tracer confirmed the 1 kHz task from the caller chain. **[EVIDENCE]**

**Corrections to the record's premises, all three from the tracer:**

| record said | actually |
|---|---|
| `gp-0x6ada` is the derivative | it is the lane's **post-clamp output mirror**, written once at `0x3ad5a`, **no reader in the image** |
| a **4-tap** derivative | a **lag-4 backward difference**, `(u[n] − u[n−4])>>1` |
| nothing about a deadband | a deadband exists **and is already a cal cell**, `0xC61F6` = 3 |
| — | there is **no** pre-existing low-pass or high-pass on r24: shaping it in frequency **needs a cave** |

---

## 2. `B(f)` — the one piece that is not in the bytes

`B(f)` = torsion-bar counts per raw rate count. Measured fresh on **V282 routes r39 + r6c, 4016 s of
engaged-lateral driving**, by the sibling agent (`B-OF-F-V282-2026-09-13.md`). Its positive control
reproduces the record's own **+114° / coherence 0.94 / |B| 2.78 at 20.31 Hz** on the record's r31–r34
creep pool, to **1°**. **[EVIDENCE]**

Three corrections it returned, each of which changes a number the record uses:

1. The bar-to-rate phase swing is **downward ~130–150°**, not upward 210°. The record's 210° came from
   comparing two strata measured in opposite conventions.
2. `B` has a **zero at the origin**, not an integrator — the "spring" reading fits ~3× worse. `B → 0` at DC.
3. The record's "creep vs loaded" difference at 7 Hz is **mostly a selection artefact**: the instantaneous
   `|bar| < 400` gate truncates the bar signal. A 1 s running median gate moves `∠B(7.3)` by 19° and lifts
   coherence 0.63 → 0.88; de-biased, creep and loaded agree to **3°**. **Use the `*med*` strata.**

🛑 **`10–14 Hz IS BARELY OR NOT IDENTIFIED`** — coherence 0.28–0.50 at 10 and 12 Hz, and that is exactly
where the bar-to-rate phase transitions. **Anything scored in that band is scored on a fit, not on a
measurement.**

---

## 3. `L_r24(f)` — the transfer

**Convention, pinned three ways.** Everything below is *aggregator counts per raw count of*
`x = gp-0x6a56 = −(0x18F wire rate)` — **identical units and sign to `adv_v290_physics.Blocks.Rf()` and
`loopshape20_loop_model.Elec.ret()`** — so the arms add directly and
`L_tot(f) = L_servo(f) + L_r24(f) = (R_servo + R_r24)·CPD·G(f)`, characteristic equation `1 + L_tot = 0`.

- `loopshape20`'s own `ret(20.0)` without the one-tick latency is **1.761 ∠ −64.97°** against
  `LOOPSHAPE-LAGPOLE-KD` §3's model column **1.90 ∠ −65.1°** — **phase to 0.13°**. **[EVIDENCE]**
- `GRINDING-DEEP`'s lane angles are `7HZ-STRONG-TURN`'s **minus 180°** (the mixed-convention correction it
  records as its own headline point 3); mine match `GRINDING-DEEP`.
- The cave's **bit-4 sign channel** confirms `∠R_r24` on the wire: predicted **+5°** at 20.3 Hz creep,
  measured **+1°**; predicted **+166°** at 7 Hz loaded, measured **+176°**; residual −14…+8° in every
  usable cell against an inter-stream timing control of 0…−13°. **[EVIDENCE]**

### 3.1 The table — κ = 1.00, i.e. the closed form at the flown `0xC6446` = 5244

These are `−(5244/1024)·D4(f)·B_measured(f)` — the measurement, not a fit. **Multiply `|R_r24|` by κ for
any other scale.** `R_servo` is V282 (Kp 248 flat, Kd 128), including its one-tick latency.

| f (Hz) | \|R_r24\| creep | ∠ | \|R_r24\| loaded | ∠ | \|R_servo\| | ∠ | coh creep / loaded |
|---|---|---|---|---|---|---|---|
| 3.0 | 0.57 | +145.1° | 0.66 | +176.3° | 4.26 | −24.8° | 0.29 / 0.05 ⚠ |
| 3.9 | 0.74 | +144.5° | 0.86 | +175.7° | 4.00 | −30.4° | 0.42 / 0.35 |
| 5.0 | 1.35 | +157.9° | 1.10 | +174.9° | 3.70 | −36.1° | 0.57 / 0.62 |
| 6.0 | 3.01 | +165.9° | 2.27 | +176.7° | 3.45 | −40.4° | 0.69 / 0.69 |
| **7.3** | **5.10** | **+170.7°** | **4.45** | **+173.7°** | **3.17** | **−45.1°** | 0.88 / 0.91 |
| 8.0 | 6.14 | +169.7° | 5.53 | +173.2° | 3.03 | −47.4° | 0.84 / 0.89 |
| 10.0 | 7.90 | +121.6° | 5.98 | +121.3° | 2.71 | −52.9° | 0.41 / 0.28 |
| 12.0 | 8.74 | +90.8° | 6.22 | +69.4° | 2.45 | −57.6° | 0.45 / 0.50 |
| 14.0 | 5.66 | +49.1° | 4.52 | +32.8° | 2.23 | −61.8° | 0.44 / 0.68 |
| 16.0 | 4.21 | +29.2° | 3.87 | +24.6° | 2.05 | −65.5° | 0.67 / 0.79 |
| 18.0 | 3.66 | +17.1° | 3.41 | +17.6° | 1.90 | −69.0° | 0.85 / 0.94 |
| **20.3** | **3.66** | **+15.5°** | **3.54** | **+13.7°** | **1.74** | **−72.6°** | 0.93 / 0.96 |
| 22.0 | 3.32 | +10.5° | 3.18 | +13.3° | 1.64 | −75.1° | 0.82 / 0.85 |
| 25.0 | 3.38 | +0.3° | 3.04 | +4.2° | 1.49 | −79.2° | 0.53 / 0.55 |
| 30.0 | 4.03 | −3.3° | 3.63 | +0.6° | 1.28 | −85.2° | 0.24 / 0.25 ⚠ |

⚠ = `B` not identified in **either** stratum. 10 and 12 Hz are marginal in both and carry the whole
bar-to-rate phase transition: **treat nothing in 10–14 Hz as measured.**

`L_r24(f) = R_r24(f)·CPD·G(f)`, `CPD = 8`, **with the same `G` the servo arm sees** — that is the content
of the 1 : 1 finding, and it is what makes the two arms summable with no further conversion.

### 3.2 The shape, in one sentence

**r24 is a near-pure PUMP below ~8 Hz (∠ +145…+177°, anti-phase to the servo's sense), swings through
quadrature across the unidentified 10–14 Hz band, and is a near-in-phase term at 16–30 Hz
(∠ +29° → −3°).** That structure is what makes a high-pass on r24 look attractive — §7 shows it is not.

### 3.3 Reconciliation with the record's 7.3 Hz split — it does NOT reproduce, and here is why

`LOOPSHAPE-LAGPOLE-KD` §4's pooled split is **normalised** (`Ls + Lr ≡ 1`), so it carries no scale. What it
asserts is a **ratio and an angle** between the two arms at 7.3 Hz:

| source | build / Kp | \|r24\|/\|T\| at 7.3 Hz | ∠r24 − ∠T |
|---|---|---|---|
| `LOOPSHAPE` §4 pooled (`Ls` 0.55∠+96°, `Lr` 1.19∠−27°) | r36/r38, **Kp 248** | **2.16** | **−123°** |
| `7HZ-STRONG-TURN` §2.2, 18 episodes | r32–r34, Kp ~662 | 1.48 | −125° |
| `GRINDING-DEEP` 7 Hz loaded | r32–r34, Kp ~662 | 1.35 | −132° |
| **this model, κ = 1.00** | **r39/r6c, Kp 248** | **1.41** | **−141°** |
| this model, κ = 0.45 | r39/r6c, Kp 248 | 0.63 | −141° |

**The ANGLE reconciles to within 9–18°** across four independent derivations. **The RATIO does not.** At
Kp 248 the servo arm is *smaller*, so the ratio should be **larger** than the Kp-662 rows; the pooled
split's 2.16 is directionally right and mine is not. Taken at face value it implies **κ ≈ 1.45**.
That is the one line pointing up. Three point down, and two of them are on-car. §4.

---

## 4. The magnitude: κ, and why I do not believe 1.00

### 4.1 The bit-6 comparator — scale-free by construction

V282's cave publishes `bit6 = |r24| ≥ |T|`, **evaluated inside the ECU at full internal precision, before
any quantisation exists.** It is exactly the *compare, don't measure* instrument the kit's own design law
prefers, and V282 was cut to answer this question. Replaying the mirror at each candidate arm and
inverting the measured duty onto that ladder:

| stratum | r39 implied arm | r6c implied arm |
|---|---|---|
| creep 1–3 | 2347 | 2279 |
| creep 1–3 (median gate) | 2325 | 2290 |
| loaded idx ≥ 68 | 2747 | 2692 |
| highway | 2451 | 2268 |
| all engaged | 2438 | 2284 |

**The raw duty moves 7× across strata; the implied arm moves 1.2×** (2268–2747 over 8 strata × 2 routes,
median **2353**). ⇒ **κ ≈ 0.45**, which **replicates the record's own `s = 0.42–0.52`** on two fresh
routes. **[EVIDENCE for the inversion. BELIEF that the gain is where the error lives — the inversion
measures r24 *relative to* `|T|`, so a wrong 427-tap scale would be absorbed into it.]**

⭐ **But the tap scale is independently checked and it is fine:** the byte-exact servo arm gives
**1.76 ∠ −65.0°** at 20 Hz against the 427 tap's measured **1.90 ∠ −69°** — **8 % and 4°**. The tap is not
under-reading `T` by 2×, so the 2.2× cannot hide there. **[EVIDENCE]**

### 4.2 ⭐ V289 bounds κ from above, and it is an ON-CAR bound

V289 relocated the mode **20.1 → 16.5 Hz** with a notch that sits **only in the servo arm**, and that is
measured: the 18–22 Hz band came back empty, **0 of 1414 windows**. A servo-side notch can only relocate
the mode if the servo arm is most of the loop there. So: re-run `design290b`'s own plant grid with the r24
arm in the loop at each κ, and count the plants that reproduce **both** measured poles (V282 19.7–20.4 Hz
ζ 0.012–0.045 **and** V289 15.6–17.3 Hz ζ −0.06…0.12).

| κ | plants fitting V282 | **also fitting V289** | fraction |
|---|---|---|---|
| 0.00 (control) | 5216 | **173** | 0.0332 |
| 0.05 | 5419 | 203 | 0.0375 |
| **0.10** | 5582 | **269** | **0.0482** |
| 0.15 | 5759 | 236 | 0.0410 |
| 0.20 | 5810 | 256 | 0.0441 |
| 0.30 | 5862 | 196 | 0.0334 |
| 0.45 | 5785 | 84 | 0.0145 |
| 0.70 | 5480 | 15 | 0.0027 |
| **1.00** | 5278 | **0** | **0.0000** |

**[EVIDENCE — `_scratch/kappa_scan.py`; the κ = 0 row reproduces the existing family, which is the
positive control.]** ⇒ **κ = 1.00 is excluded outright by an on-car measurement; the data prefer
κ ≈ 0.10–0.20 and tolerate 0.45.**

### 4.3 V281 rev 3 bounds it from the 7 Hz side

Aggregator `Re` budget at 7.3 Hz loaded, V282 (Kp 248 flat):

| κ | servo Re | r24 Re | net |
|---|---|---|---|
| 1.00 | +2.23 | **−4.43** | **−2.20 — still strongly pumping** |
| 0.45 | +2.23 | −1.99 | **+0.24 — roughly neutral** |

On the car, **V281 rev 3 (this Kp) extinguished the self-sustained 7 Hz cycle — F7 0.0 per 100 s on four
routes.** At κ = 1.00 the budget says it should have survived. **[EVIDENCE for the arithmetic; BELIEF for
the inference — the real criterion is `|L_tot| ≥ 1`, not the sign of `Re`, which is §5's whole point.]**

### 4.4 What to carry

**Default κ = 0.45, bracket [0.10, 1.00]**, and report every magnitude-dependent number at both ends.
**The phase is not in dispute** and is confirmed on the wire.

### 4.5 The hidden arm and the latch — currently unarmed, permanently dangerous

`gp-0x671d` ≠ 0 selects `0xC6442` = 1024. The tracer reports it is a **first-strike Schmitt latch**
(SET at 5530, RELEASE at 1024, **cleared only on reset**): one crossing and the lane collapses to ×0.195
of the V280+ arm for the rest of the drive. On r39 and r6c it is **not live and did not fire**
**[EVIDENCE, three ways]**: (a) the duty is 2.0–2.4× the 1024 prediction in every stratum; (b) a
sliding-window scan over 4016 s finds no persistent step-down (r39 p = 0.41, r6c p = 0.98) with a
detection floor of ×0.94 against a hypothesised ×0.195 — **13× the floor**; (c) **no lane quantity ever
reaches the SET threshold 5530** (max |bar| 3949 / 3762; max `|d·5244/1024|` 1899 / 2765; zero frames
≥ 5530). ⇒ **model r24 as bimodal for risk purposes**, but its second mode is not being visited.

---

## 5. 🛑 "Re > 0 = damping" is not a substitute for the pole

The record reads the **real part** of each lane's phasor as its damping contribution, and on that reading
r24 supplies **83 %** of the 20 Hz damping. My arithmetic reproduces that budget:

| lane at 20.3 Hz, creep | \|R\| | ∠ | Re | share of Re |
|---|---|---|---|---|
| LKAS servo (model, Kp 248) | 1.74 | −72.6° | +0.52 | 14 % |
| LKAS servo (measured, 427 tap) | 1.90 | −69.0° | +0.68 | — |
| r24 at 5244, **κ = 1.00** | 3.51 | +5.6° | +3.50 | **87 %** |
| r24 at 5244, **κ = 0.45** | 1.58 | +5.6° | +1.57 | **75 %** |
| record's own closed form | 3.23 | +5.0° | +3.22 | 83 % |

**The share statistic is robust** — plant-free, because both lanes traverse the same aggregator with unit
coefficients, and it survives the whole κ bracket: **r24 carries 75–87 % of the electronic `Re` at the
ring.** **[EVIDENCE]**

🛑 **But `Re` is not `ζ`.** The lane torque acts on the wheel **through the plant**, which carries its own
phase (≈ −72° raw, ≈ −100° stream-corrected at 20.3 Hz). Whether an arm damps or de-damps the closed-loop
mode is set by `1 + L_tot`, not by `Re(R)`. The record flags this itself — `LOOPSHAPE-LAGPOLE-KD` §3 says
*"identifying Re with the operator's grinding is the record's claim, **BELIEF**"* — and the kit's own
central verdict, **that the rate servo DE-damps the 20 Hz plant mode**, is already inconsistent with
reading the servo's `Re = +0.52` as damping. **Do not use the sign of `Re` to decide a lever.** Here it
happens to give the right answer; §6 shows how easily it gives the wrong one.

---

## 6. Δζ at 20 Hz — the counterfactual on `0xC6446`

**Method.** `design290b_family.json` was fitted to reproduce the measured pole with the **servo arm
alone**, i.e. against a loop **missing ~65 % of its own return ratio**. Its `g0`/`ζp` have therefore
absorbed r24, and adding r24 on top double-counts — demonstrably: **0 of 304** of those plants still
reproduce the measured V282 pole once r24 is included. So the family is **re-fitted** over `design290b`'s
own grid and targets (`r24_plant_refit.py`), **with a 2–60 Hz closed-loop stability filter added** — the
unfiltered family admits plants that ring up at 8.6 Hz, which the car demonstrably does not do.

### 6.1 The result, on the stability-filtered family that fits BOTH measured poles

Median over the family; `0xC6446` swept with the servo arm held. **[`_scratch/dzeta_stable.py`]**

| `0xC6446` | κ 0.10 (269 plants) | κ 0.20 (256 plants) | κ 0.45 (12 plants) |
|---|---|---|---|
| | f_cl / ζ | f_cl / ζ | f_cl / ζ |
| **5244 (flown)** | **20.04 Hz / 0.0312** | **20.02 Hz / 0.0297** | **20.09 Hz / 0.0370** |
| 3933 (×0.75) | 19.79 / 0.0217 | 19.52 / 0.0130 | 19.41 / 0.0290 |
| 2622 (×0.50) | 19.57 / 0.0101 | 18.98 / **−0.0031** | 18.60 / 0.0146 |
| **2048 (Honda)** | 19.47 / **0.0066** | 18.76 / **−0.0110** | 18.18 / **0.0054** |
| 1731 (×0.33) | 19.43 / 0.0039 | 18.64 / −0.0158 | 17.95 / −0.0006 |
| 524 (×0.10) | 19.21 / −0.0077 | 18.19 / −0.0364 | 17.13 / −0.0311 |
| 0 | 19.13 / −0.0133 | 18.01 / −0.0474 | 16.83 / −0.0485 |
| **paired Δζ from removing r24, p50** | **−0.0439** | **−0.0748** | **−0.0855** |
| fraction of plants where r24 de-damps | **0.01** | **0.00** | **0.08** |

Two things fall out of this and both matter:

1. **Cutting `0xC6446` lowers ζ monotonically, at every κ the evidence supports.** Honda's own 2048 arm
   lands the mode at **ζ ≈ +0.005 to −0.011 — marginal to unstable.**
2. ⭐ **It also drops the mode's FREQUENCY, 20.0 → 18.2–18.8 Hz at 2048 and → 16.8–17.1 Hz at zero.**
   **That is V289's own revert signature** — the mode moving down into 15–17 Hz and getting louder is
   exactly what the operator felt on r62/r63. A big r24 cut would reproduce it by a different route.

### 6.2 The one family that disagrees, and why it is the one to discard

At **κ = 1.00** — the value **V289 excludes outright** (0 of 5278 plants fit both poles) — the sign flips:
removing r24 *raises* ζ on 99 % of plants (paired Δζ **+0.0144**). **That is the whole source of the
"cutting improves both symptoms" reading, and it lives only at a κ the on-car data rule out.**

### 6.3 The flown ladder agrees with §6.1

`0xC6446` is **not** an untried cell:

| value | build | flown? | measured on-car |
|---|---|---|---|
| **512** (Honda's arm) | pre-V67; **V70** reverted to it | **yes** | **grind #1 BACK AT THE STOCK LEVEL** — median e 18–22 engaged creep 729.1, *excluded from V62/V65 and V67/V68 at P = 0.0000* |
| 1024 | **V149** | **yes** | not separately scored |
| **5244** | V67/V68; restored at V88; on the car continuously since V104 | **yes** | **0.40 [0.27, 0.58] on grind #1**; operator on V88: *"the audible grinding is fixed"*. Its **REMOVAL** is a **~3× win at 6–9 Hz AT CREEP ONLY** (0.45 / 0.26 / 0.58), neutral at 35–65 km/h. **NULL at 22–26 Hz.** |
| 5244 → 6553 | **V160** | **yes** | not separately scored |
| 6553 → 5244 | **V164** | **yes** | not separately scored |
| 5244 → 7866 | V246 | **NO** | protective at the ratchet within fixed gain, p 0.056 |

⇒ **A two-way flown dose-response says r24 DAMPS 18–22 Hz and PUMPS 6–9 Hz.** Same sign as §6.1.
**[EVIDENCE — on-car, both directions]**

⚠ Two honest caveats on that ladder: the V67 and V70 builds each moved **other cells besides `0xC6446`**,
and the 512 ↔ 5244 pair also flips `0x3AA96`, which cuts r26 6.00× at the same time. The record
nonetheless treats the pair as one lever ("Lever B") throughout, and the 0.40 figure is its de-confounded
2×2.

### 6.4 What I therefore report

> **Δζ(20 Hz) contributed by r24 at 5244 is POSITIVE — r24 damps the ring — and it is large: the paired
> median over the two-pole family is +0.044 to +0.086 depending on κ, against a total measured ζ of
> 0.012–0.045.** The ring's damping is **mostly r24's**. **[EVIDENCE for the SIGN, from the flown ladder
> and from every κ the data support. BELIEF for the MAGNITUDE — it rests on a plant family and on a
> `B(w)` rational fit whose stable and best-fitting orders disagree.]**

---

## 7. The design axis, priced

### 7.1 The 7.3 Hz gate, generalised — and it is scale-free

`LOOPSHAPE-LAGPOLE-KD` §4's gate `|Ls·R(7.3) + Lr|` only moves the **servo** arm. Because both arms are
normalised shares of the same ripple phasor, it generalises to

> **`gate73 = |Ls·Rs + Lr·Rr|`**, `Ls = 0.55∠+96°`, `Lr = 1.19∠−27°`, `Rs`/`Rr` = each arm's **new/today
> ratio at 7.3 Hz**. Today = **1.0028**. `≥ 1.000` re-arms the 7 Hz strong-turn cycle.

**It inherits none of the κ dispute** — it is a ratio of ratios, exactly why the original was
interval-invariant. `r24_lane.gate73(Rs, Rr)` implements it. For option (a), scaling `0xC6446` by k, the
lane is **linear in the gain**, so `Rr = k` exactly:

| `0xC6446` | k | **gate73** | vs today | ζ(20 Hz) at κ 0.20 |
|---|---|---|---|---|
| 5244 (flown) | 1.00 | **1.0028** | — | **0.0297** |
| 3933 | 0.75 | 0.7512 | −25 % | 0.0130 |
| 2622 | 0.50 | 0.5478 | −45 % | −0.0031 |
| **2048 (Honda's own arm)** | **0.39** | **0.4900** | **−51 %** | **−0.0110** |
| 1731 | 0.33 | 0.4706 | −53 % | −0.0158 |
| 524 | 0.10 | 0.4953 | −51 % | −0.0364 |
| 0 | 0.00 | 0.5500 | −45 % | −0.0474 |

**The gate is minimised at k = 0.252 (`gate73` = 0.461)**, analytically `k* = −Re(Ls·conj(Lr))/|Lr|²`.
⭐ **The record already priced this move itself** — `STUTTER-7HZ` M5 puts `0xC6446` → 2048 at *"a 38 % ring
reduction"*. I get 0.49 on the pooled split and 0.60 on r36's own shares; the record's 0.62 is r36's, so
the two agree once the route is matched. **[EVIDENCE — reproduces an existing record calculation]**

🛑 **The last column is the whole story: the 7 Hz gate and the 20 Hz damping move in opposite directions
along this axis, monotonically, with no sweet spot.**

### 7.2 The full option table

`Rr` columns are the **r24 arm after the change**, κ = 1.00 (multiply by κ for magnitude; the **ratios**,
and therefore `gate73`, are κ-free). `Δζ20` is the stability-filtered two-pole family, **κ 0.10 / κ 0.20**.

| candidate | gate73 | \|Rr\| 7.3 | ∠ | \|Rr\| 20.3 | ∠ | Δζ20 (κ0.10 / κ0.20) |
|---|---|---|---|---|---|---|
| **(a)** `0xC6446` ×0.75 → 3933 | **0.751** | 1.63 | +163.5° | 2.35 | −9.6° | **−0.0096 / −0.0167** |
| **(a)** ×0.50 → 2622 | **0.548** | 1.09 | +163.5° | 1.57 | −9.6° | **−0.0211 / −0.0327** |
| **(a)** → **2048 (Honda)** | **0.490** | 0.85 | +163.5° | 1.22 | −9.6° | **−0.0246 / −0.0407** |
| **(a)** ×0.33 → 1731 | **0.471** | 0.72 | +163.5° | 1.03 | −9.6° | **−0.0273 / −0.0455** |
| **(a)** ×0.10 → 524 | 0.495 | 0.22 | +163.5° | 0.31 | −9.6° | −0.0389 / −0.0661 |
| **(b)** HP 5 Hz on r24 (cave) | **1.124** ✗ | 1.77 | +197.9° | 3.00 | +4.3° | not priced — fails the gate |
| **(b)** HP 8 Hz on r24 (cave) | **1.064** ✗ | 1.43 | +211.1° | 2.84 | +11.9° | not priced — fails the gate |
| **(b)** HP 12 Hz on r24 (cave) | 0.970 | 1.09 | +222.2° | 2.60 | +21.0° | small; magnitude at 20.3 Hz only −29 % |
| **(b)** BP 8–40 Hz on r24 (cave) | 0.988 | 1.41 | +202.1° | 2.54 | −11.5° | small |
| **(b)** BP 12–60 Hz on r24 (cave) | 0.935 | 1.08 | +216.5° | 2.46 | +5.7° | small |

🛑 **The high-pass options are DOMINATED, and two of them FAIL the 7.3 Hz gate outright.** The reason is in
the phase column: a one-pole high-pass **adds lead**, and at 7.3 Hz r24 already sits at +171°, so the lead
rotates it *towards* the critical point faster than the magnitude cut pulls it away. **HP 5 Hz and HP 8 Hz
push `gate73` above 1.000 — they re-arm the 7 Hz strong-turn cycle.** A high-pass on r24 is **not** the
free frequency separation it looks like on a magnitude plot. **[EVIDENCE — arithmetic on the record's own
normalised split, scale-free]**

⇒ **The r24 axis has no free lunch on it.** Every move that helps 7.3 Hz costs 20 Hz damping, and the
filter that was supposed to separate them either fails the 7 Hz gate (HP 5/8) or barely moves the 7 Hz arm
while keeping most of the 20 Hz arm (HP 12, BP 12–60 — `gate73` 0.94–0.97, a 3–6 % improvement).
**If the session wants both bands, the lever is not on this axis.**

### 7.3 (c) — what else the bytes offer

| lever | address | value | on-car record | verdict |
|---|---|---|---|---|
| the engaged arm | `0xC6446` | 5244 | **flown at 512, 1024, 5244, 6553**; 7866 built unflown (V246) | the axis, and it is live |
| Honda's fixed arm | `0xC6440` | 2048 | the `lp == 0` rung; **never edited** | the natural k = 0.39 target — and §6.1 says it is **marginal to unstable** at 20 Hz |
| the latch arm | `0xC6442` | 1024 | **never edited**; `gp-0x671d` not live, did not fire on r39/r6c | ⚠ a latent ×0.195 hazard, **not a lever** |
| the deadband | `0xC61F6` | 3 | **already a cal cell**, on the lane, after the gain | ⚠ **DISQUALIFIED** — the tracer withdrew it against the kit's explicit operator constraint on adding friction that rate-limits fast steering. It is an amplitude nonlinearity anyway and cannot separate 7 Hz from 20 Hz |
| the pre-gain clamp | ±5120 | — | never reached: max `\|d·5244/1024\|` 1899 / 2765 over 4016 s | **inert; not a lever** |
| the `sar` route | `0x3AB76` / `0x3AC20` | — | **V62/V65 flew it**; the only encoding whose dose is exact independently of `a`, scaling **both** lanes 2.000× | a code edit, and it moves r26 too |
| the r26 sibling arm | `0xC6444` / `0xC643E` | 512 | cut 6× by the same `0x3AA96` repoint; `0xC6444` **FALSIFIED — it flew as V71c** | not on this axis |

**There is no second engaged arm to enable.** The selector is a 4-way if-chain and 5244 already wins it
whenever the lane is engaged and the latch is clear.

---

## 8. What I did NOT verify

1. 🛑 **The κ dispute is NOT closed.** The bit-6 inversion (0.45), the V289 relocation (0.10–0.20) and the
   pooled 7.3 Hz split (1.45) do not reconcile. I argue the two on-car lines should outrank the third, and
   that the 427 tap's scale cannot absorb the gap, but **I have not found the error in the pooled split**.
   Its own source (`STUTTER-7HZ-V283-r36-r38` ADDENDUM 6 §A13.3) already records that composing its
   measured absolutes **self-refutes** (`|L_tot| = 1.76` where the car is stable); that author could not
   repair it either.
2. **`B(f)` is a closed-loop ratio.** The `bof` agent flags this as its own largest open risk: it did not
   run a command-IV version. If the bar ripple carries a road or driver input that is not a function of
   the motor torque, the measured `bar/rate` is a weighted mix and the r24 arm is partly a **feedforward
   of a disturbance**. **That is the most likely way §6 is wrong**, and it is cheap to test: re-estimate
   `B` with the `0xE4` command as the instrument.
3. **10–14 Hz is a fit, in every stratum.** No number in that band is a measurement.
4. **The re-fitted family is not validated against the off-line plant.** `mean ln|G_fit/G_meas|` is −1.74
   (κ 0) to −1.53 (κ 1) — the fitted `|G|` is ~0.2× the directly measured off-line `G` at **every** κ.
   This is a **pre-existing, unexplained discrepancy in the kit's own loop model**, not something this
   trace introduced, but it means the family is anchored on the two measured poles and nothing else.
   ⊕ **A failed control, reported:** I tried a model-light ζ estimate from `|1+L|` and `dL/df` using the
   **measured** off-line `G`, and it fails its own control — servo-only gives `|L| = 0.66` at the minimum
   and ζ = 0.113 against a measured 0.012–0.045. **That method does not apply here, because the 20 Hz mode
   is largely a plant mode, not a loop-crossover resonance.** Discarded, not used anywhere above.
5. **The deadband and both clamps are linearised away** in `R_r24(f)`. The deadband is 3 counts against a
   ring amplitude the model puts at ~10–30; its describing function would cut the fundamental by 0.4–0.8×
   at those amplitudes and is **amplitude-dependent**, so the linear arm over-states r24 at small ring
   amplitudes. **This cuts the same way as a small κ and I have not separated the two** — part of what I
   am calling κ may be the deadband, which would make the lane's effective gain *amplitude-dependent*
   rather than simply smaller.
6. **The `B(f)` rational fit is not unique.** The order used for the pole work (nb 1, nd 3; rms ln|B|
   0.107, rms phase 14.1°) has a pole outside the unit circle — legitimate for a ratio of two plant
   outputs (its poles are `G`'s zeros, which may be non-minimum-phase) but it injects a non-minimum-phase
   pole into the characteristic polynomial. The stable (0, 2) alternative fits far worse (rms ln 0.40, 25°
   phase error at 20 Hz). **Any `unstable` flag in the raw scan outputs is an artefact of that pole and
   must be ignored** — it reads True at every dose including the flown one. §6's stability filter is
   band-limited to 2–60 Hz for exactly this reason.
7. **I did not re-derive the 1 : 1 aggregator finding myself**, and my own tracer got the *identity* of
   the LKAS aggregator term **wrong** (`gp-0x6ad4`; it is `gp-0x6b4c`). Agent `ghidrafill` re-derived the
   whole path instruction by instruction and adjudicated it the other way. **The 1 : 1 weight survives
   that correction**, but I am relying on someone else's derivation for it. Two live consequences I have
   **not** carried into any number above: the LKAS lane's **second, indirect route** into the aggregator
   (§0.3), which makes every r24 share here an upper bound; and the **clamp `0xC61B2`** (512 stock /
   2048 on 4× builds) that sits on the LKAS path at `0x2b42e` — the record scores it INERT (`b6` duty
   0.000000 over 17,614 engaged frames), which is why I left it out, **but I did not re-check that on
   r39/r6c.**
8. ⚠ **`~0x2a30e..0x2b421` was unanalysed in Ghidra for the whole of this work.** `ghidrafill` has since
   analysed and saved it (2086 → 2090 functions) and found it is an **uncalled dead twin** of the live
   LKAS output path, so the census deltas land entirely inside dead code. **My tracer's reports were
   produced against the unanalysed database**, so any null it returned over that address range is
   uncontrolled.
9. **I did not price any change to the SERVO arm.** `gate73(Rs, Rr)` takes both, so the 2-D score is
   available, but every `Rs` in this document is **1.0**.
10. **I did not model r26.** The `0x3AA96` repoint couples the two lanes, so any `sar`-route edit moves
    both, and none of the numbers here cover that.
11. **The κ 0.45 two-pole family is only 12 plants.** Its ζ column is thin; κ 0.10 and 0.20 (269 and 256
    plants) carry the weight, and all three agree in sign.

---

## 9. ADDENDUM — V291 = C10 priced on this model, and the record conflict adjudicated

Added after the orchestrator's decision (V291 = fb pole 9.94 Hz + `0xC6446` 5244 → 4725). Nothing here
was used to make that decision; it is an independent check of it.

### 9.1 TOPOLOGY — the answer `fbdown` needs

**`L_r24` is a PARALLEL FEEDBACK BRANCH around the SAME plant as the servo, never lumped inside `G`.**

```
rate = G0 * u ;  bar = B * rate ;  r24 = R * bar ;  T = C * rate ;  u = T + r24 + d
  =>  L = (C + R*B) * G0
```

That is exactly `grind_loop_shape.py`'s algebra, and it is the same object I built. 🛑 **The consequence
both of us hit independently: the tap-identified `G_meas = rate/T` already has r24 CLOSED around it**, so
`G0 = G_meas/(1 + R·B·G_meas)` — **every margin ever computed against `G_meas` is the margin of a loop that
already contains the r24 pump**, and adding r24 to such a plant double-counts. `design290b_family.json` is
in that class (§6). `TOPO_PARALLEL` is correct.

### 9.2 ⭐ INDEPENDENT REPRODUCTION OF `fbdown`'s k LADDER

Recomputing the fb pole's 7.3 Hz servo ratio from the bytes (DC held at 30.891, `a = 1024·e^{−2πf_p/1000}`,
`b = DC·(1024−a)/2`) and solving `|LS73·R73 + k·LR73| = 1.01` for k:

| fb pole | R73 | ∠ | **k solving gate73 = 1.01** | `0xC6446` | `fbdown` said |
|---|---|---|---|---|---|
| 16.52 Hz (live) | 0.9999 | −0.0° | 1.0067 | 5279 | — |
| 12.0 Hz | 0.9340 | −7.5° | **0.9401** | 4930 | 0.939 ✓ |
| **9.94 Hz (V291)** | **0.8811** | **−12.5°** | **0.9012** | **4726** | 0.901 ✓ |
| 8.0 Hz | 0.8075 | −18.5° | **0.8612** | 4516 | 0.861 ✓ |
| 6.0 Hz | 0.6941 | −26.7° | **0.8215** | 4308 | 0.822 ✓ |

**Agreement to the fourth decimal on all four rows, from a separate implementation.** **[EVIDENCE]**

### 9.3 Is the 7.3 Hz r24 arm LINEAR in `0xC6446`? YES, and the wire says the clamp never binds

**From the bytes:** the only nonlinearities between the gain and the aggregator are the ±3 deadband
(`0xC61F6`) and the ±8192 clamp. Everything else is `(u·g)>>10`, exactly proportional to `g`. So `Rr = k`
holds wherever neither binds. **[EVIDENCE — §1]**

**From the wire, over 4653 s on r39 + r6c:** the pre-gain clamp ±5120 is never approached (max `|d|` 371 /
540), and the post-gain lane value's maximum is `max|d·5244/1024|` = **1899 / 2765 against a ±8192 clamp —
the clamp NEVER BINDS, on either route, at any speed.** The deadband is 3 counts against a lane that
reaches ~2000, i.e. **0.04–0.16 % of the working range at the ring**. **[EVIDENCE]**

⇒ **`Rr = k` exactly, on the wire as well as in the bytes.** The `gate73` column below needs no correction.
⚠ The one caveat, unchanged from §8.5: the deadband is a **subtractive Coulomb tax**, so at *small* ring
amplitudes it is a proportionally larger loss. That is an amplitude effect on `|R_r24|`, not on its
**linearity in k**, which is what this question asked.

### 9.4 The k ladder, priced on both axes (servo held at `Rs` = 1 in the gate column)

| `0xC6446` | k | gate73 | ζ(20 Hz), κ 0.10 | ζ(20 Hz), κ 0.20 |
|---|---|---|---|---|
| 5244 (today) | 1.0000 | 1.0028 | +0.0312 | +0.0297 |
| 4929 | 0.9400 | 0.9400 | +0.0289 | +0.0257 |
| **4725 (V291)** | **0.9010** | **0.8999** | **+0.0274** | **+0.0231** |
| 4720 | 0.9000 | 0.8988 | +0.0274 | +0.0230 |
| 4510 | 0.8600 | 0.8583 | +0.0259 | +0.0203 |
| 4300 | 0.8200 | 0.8186 | +0.0243 | +0.0176 |
| 3933 | 0.7500 | 0.7512 | +0.0217 | +0.0130 |
| 2622 | 0.5000 | 0.5478 | +0.0101 | −0.0031 |
| 2045 | 0.3900 | 0.4897 | +0.0066 | −0.0110 |

**V291's r24 cut costs Δζ(20 Hz) = −0.0038 (κ 0.10) to −0.0066 (κ 0.20)** — roughly **12–22 % of the
mode's damping**, against the fb pole's reported gain of +0.013 → +0.03…+0.06. ⇒ **On my numbers the
pairing is sound: the pole buys an order more damping than the r24 cut spends.** The ×0.86 and ×0.82
doses cost 2–3× as much and are the ones to avoid if the pole's benefit is smaller than modelled.
**[BELIEF — the ζ column carries §6's plant-family and `B(w)`-fit caveats.]**

### 9.5 🛑 THE RECORD CONFLICT ON r24's 20 Hz SIGN — ADJUDICATED

Two entries disagree, and **both methods are unsound; the flown ladder is what decides.**

| entry | claim | method | verdict |
|---|---|---|---|
| `memory/…/accord-r24-pumps-at-7hz-and-damps-at-20hz-…` | r24 **damps** 20 Hz, ~83 % of the aggregator's damping | `Re` of the lane phasor — **the sign heuristic §5 shows is not ζ** | **CONCLUSION RIGHT, REASONING WRONG** |
| `grind_loop_shape.py` §G (2026-09-03) | `0xC6446` 5244 → 512 improves **both** bands (18–22 Hz ×0.81, 7–9 Hz ×0.64) | a genuine closed-loop peak `max|1/(1−L)|` on a **correctly de-embedded** `G0` | **FALSIFIED ON THE CAR** |

**Why §G is the one to retire, despite the better method.** Its topology and its `G0` de-embed are both
right — it is the only prior artefact that got the double-counting trap right — but its prediction is
**contradicted by a flown two-way dose-response**: it says 512 would take the 18–22 Hz peak to ×0.81
(better), and the car says **V70 at 512 put grind #1 BACK AT THE STOCK LEVEL**, excluded from V67/V68 at
**P = 0.0000**, with V88's restore to 5244 measuring **0.40 [0.27, 0.58]** and the operator saying *"the
audible grinding is fixed"*. That is a **2.5× worsening measured where §G predicts a 19 % improvement** —
wrong in sign and in magnitude. §6.1's two-pole family agrees with the car; §G's `G0` does not.
⚠ **What I could NOT do is find §G's error.** Its `G_meas` comes from one stratum's tap identification;
mine is a grid constrained by two measured closed-loop poles. **I am ranking them by which one the car
agrees with, not by finding the bug.** Both plants remain candidates for the real one.
⇒ **Practical instruction: do not cut `0xC6446` below ~×0.75 on the strength of §G.** The small doses in
§9.4 are safe because they are small, not because §G licenses them.

### 9.6 A cal cell that band-shapes r24: **there is none**

The brief asked whether a high-pass above ~12 Hz could keep r24's 20 Hz damping while dropping its 7 Hz
pump — *"that would be the ideal second axis"*. **Two findings kill it as a V291-class option:**

1. **No cal cell shapes r24 in frequency.** The only cells on the path are the gain arms, the ±5120 input
   clamp, the deadband and the ±8192 clamp. **A filter needs a CAVE.** (Hook `0x3ac18`, `mul r10,r8,r0`,
   with 6–8 provably dead scratch registers; nearest verified free flash `0xC5788..0xC5FF0`, 2152 B. GATE 1
   RAM ownership is **not** answered — register liveness is not RAM ownership.)
2. 🛑 **And the high-pass does not work anyway** — §7.2. It adds **lead**, and at 7.3 Hz r24 sits at
   +171°, so the lead rotates the arm *towards* the critical point faster than the magnitude cut pulls it
   away. **HP 5 Hz → gate73 1.124, HP 8 Hz → 1.064: both RE-ARM the 7 Hz cycle.** The doses that pass
   (HP 12 Hz 0.970, BP 12–60 Hz 0.935) buy only **3–6 %** on the gate while keeping most of the 20 Hz arm.

🛑 **The whole §7.2 filter table is a FUTURE-BUILD analysis. None of it is part of V291, and I am not
proposing any of it.** It is recorded so the next session does not spend a build discovering the same
negative.

### 9.7 NAMED OPEN ITEMS — not started, deliberately

1. 🛑 **The plant-absorption test (§8.4's "(b)")** — whether `design290b`'s family absorbed r24 into its
   own `G`, checked against the family's off-line `|G|` residuals. **NOT RUN.** It is the test that would
   say whether §6.1's family or §G's `G0` is the right plant, and therefore the test that would settle
   §9.5 by mechanism rather than by deferring to the car.
2. 🛑 **The 10–14 Hz identification gap.** `B(f)` is not identified at coherence ≥ 0.5 in **any** stratum
   across 10–14 Hz, and that is exactly where the bar-to-rate phase transitions and where `fbdown`'s
   C3(ii) de-embed is reported singular (12.1–12.7 Hz). **Every number either of us quotes in that band is
   a fit.** Closing it needs either more engaged exposure in that band or a different estimator.
3. **`B(f)` as a closed-loop ratio** — the command-IV re-estimate (§8.2). Cheap, and the likeliest way the
   §6 magnitudes are wrong.
4. **The κ dispute** (§8.1), carried by the design as the effective-2353 vs flown-5244 bracket.
