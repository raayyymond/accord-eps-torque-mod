# The 18–22 Hz creep grind — the r24 sign settled ON THE WIRE, the loop shape, and the ONE next build

Deep-analysis subagent, 2026-09-03. Brief: `docs/handoffs/2026-09/HANDOFF-2026-09-03-GRINDING-for-deep-analysis.md`.
Scripts, all standalone and in `rlog-tools/studies/grind/`: `extract_r24sign.py` · `r24_sign_on_the_wire.py` ·
`grind_mode_phase.py` · `grind_loop_shape.py` · `v282_prereg_duty.py` (stdout in `_scratch/` beside them).
Disassembly by three independent GhidraMCP subagents against stock `code.bin` and the flown
`_v280_V280R2-…_plain_image.bin`; byte facts re-read by me in Python. **EVIDENCE (with the method) or BELIEF on every claim.**

---

## 0. Headline

1. 🛑 **The dispute in §4 of the brief is CLOSED, and it was closed without a build: the r24 lane's SIGN IS
   ALREADY ON THE WIRE.** The V280 rev 2 code cave publishes `sign(gp-0x6ada)` — the r24 lane output — into
   **0x14A byte 4 bit 4, at 100 Hz**, and has done on every build since V105. I re-extracted it from the r31–r34
   rlogs. **r24 PUMPS below ~10 Hz and DAMPS from ~13 to ~23 Hz**, on four routes, two builds, two StarPilot
   tunes. At the 20 Hz grind line its phase re the wheel rate is **−6°** (coherence 0.80) — a near-ideal
   damper. At 7 Hz in the loaded high-angle stratum it is **+179°** (coherence 0.76) — a near-ideal pump. [EVIDENCE]
2. 🛑 **Therefore `0xC6446` 5244 → 512, the headline build of the 7 Hz deep analysis, MUST NOT BE FLASHED as
   a grinding measure — it would strip 74–90 % of the aggregator's 20 Hz damping.** The same cut is right for
   7 Hz and wrong for 20 Hz. This is the "do not flash" the adversarial pass exists to produce. [EVIDENCE for
   the damping budget; the 7 Hz half is the sibling analysis's own result and I do not dispute it]
3. **`creep20`'s "bar re rate −70° at 20 Hz, spring-like" is WRONG BY 180°** — a mixed convention, wire-sign
   torque against internal-sign rate. Re-measured on the identical stratum, identical pool (28.0 s, 25 Welch
   windows), it is **+114°, coherence 0.94**. Everything `creep20` built on that number has to be re-read;
   its other findings stand. [EVIDENCE]
4. **`gp-0x6752 = −1` is now MEASURED on this car, not inherited.** Had it been +1 the cave bit would have
   read 180° from where it does. The kit has carried it as a belief since 2026-08. [EVIDENCE]
5. **Which loop carries the 20 Hz line: BOTH, and r24 is the larger half.** At 20 Hz in creep the r24 lane
   delivers **3.23 aggregator counts per rate count at ∠+5°** against the LKAS rate PID's **1.90 at ∠−69°**.
   r24 supplies **83 % of the aggregator's 20 Hz damping**; the LKAS lane supplies 17 % and is mostly
   quadrature. `creep20`'s "the 20 Hz ripple IS the rate PID's own P+D" is right *about the tap* and
   misleading *about the motor*: **the 427 tap reads `gp-0x6b38`, the LKAS lane alone — not the aggregator.**
   [EVIDENCE for the phases and for |T|; BELIEF for |r24|, which is closed-form, and that is the one number
   the next build must measure]
6. **The 7 Hz stutter and the 20 Hz grind are the same cell pulling opposite ways, and Honda's own value sits
   at the 7 Hz neutral point.** Net aggregator damping at 7 Hz in the loaded stratum crosses zero at
   `0xC6446` ≈ **1880**; Honda's own arms are 2048 and a 2150–3072 rate LERP. V280 flies **5244**, i.e. 2.8×
   past neutral. That is a complete, quantitative account of why V280 rev 2 has a 7 Hz stutter and only a
   "very very attenuated" grind, when earlier 6× builds had a loud grind. [EVIDENCE]
7. **The loop shape that serves both bands is the OUTPUT-LAG POLE, a cal never touched in 280 builds.**
   Moving `0xC63EC`/`0xC63EE` from a 5 Hz pole to 15 Hz with the DC gain held rotates the LKAS lane's phase
   from −69° to −46° at 20 Hz and from −62° to −33° at 7 Hz, turning the servo into a real damper in both
   bands: **20 Hz damping ×1.48, 7 Hz pump ×0.01 (neutral), in the loaded stratum, with DC authority
   unchanged.** Paired with `0xC6446` → 2048 it is the only shape I found that is **net-damping at 7 Hz
   (+1.97) while keeping 87 % of the 20 Hz damping.** [BELIEF — the magnitude re-scaling is a model
   extrapolation; the phases are measured]
8. ⭐ **The ONE build to cut next is an INSTRUMENT, and it is eight bytes.** `V282 = V281 rev 3 + four `ld.h`
   displacement halfwords inside the existing flown cave`, repointing two dead-or-low-value comparator bits to
   **`|r24| ≥ |T|`** and **`|r24| ≥ |aggregator|`**. No cal change, no code added, no authority change,
   read-only, and it keeps the 427 torque tap. One drive settles the `gp-0x671d` gain arm, sizes r24 against
   the LKAS lane, and reads V281 rev 3's own Kp test at the same time. Pre-registration in §5.
9. ⚠ **A registered prediction against V281 rev 3, which is built and unflown:** on the damping budget its
   Kp cap makes the 7 Hz net damping slightly *worse* (−2.09 → −2.42 in the loaded stratum) because it cuts
   the servo's damping while leaving r24's pump untouched. I am not asking for it to be pulled — a 2.8× Kp
   swing is a powerful test of everything here — but its FAIL sentence should carry this.

---

## 1. What I did, and the two things I re-derived myself

**The crux I was asked to adjudicate** was a 184° disagreement about `bar/rate` at 20 Hz: `creep20` measured
−70° in the creep stratum, the 7 Hz deep analysis +114° in the loaded high-angle stratum. Both at coherence
0.88–0.94. I did not take either.

**Step 1 — re-measure `bar/rate` myself, in every stratum** (`grind_mode_phase.py`). Torsion bar and wheel
rate ride the **same 0x18F frame**, so this measurement has no inter-stream timing risk at all. I applied no
negation to either signal, so the ratio is convention-free.

| stratum | s | ∠(bar/rate) @7 Hz | coh | ∠(bar/rate) @20 Hz | coh | \|bar/rate\| peak |
|---|---|---|---|---|---|---|
| creep engaged hands-off, v 1–3, \|bar\|<400 | 28.0 | **−139°** | 0.73 | **+114°** | 0.94 | 7.8 Hz |
| creep engaged hands-off, v 1–6 | 63.7 | −140° | 0.61 | +110° | 0.82 | 7.8 Hz |
| loaded high-angle, v 2–9, \|ang\|>30 | 291.3 | −96° | 0.90 | +116° | 0.96 | 8.6 Hz |
| highway, v > 15 | 997.4 | −121° | 0.66 | +114° | 0.46 | 7.8 Hz |

**`creep20`'s number is the error.** My creep pool is byte-for-byte the same stratum and the same size it
reports (28.0 s, 25 Welch windows) and gives +114°. The magnitudes agree once its deg/s axis is converted
(its 20.3 = my 2.81 × 8 counts per deg/s), so only the phase differs, and it differs by 180° — the signature
of mixing the wire-sign bar with the internal-sign rate (`creep20` carries both `g["bar"]` in wire sign and
`g["rate_x"] = −wire/CPD` in internal sign). **There is no stratum-dependent physics here.** There is one
hand-wheel/torsion-bar mode at **7.8–8.6 Hz**, the phase rotates −180° through it, and above ~13 Hz it sits
flat at +109…+118° out to 23 Hz in every stratum. My own "hands change the mode frequency" hypothesis is
**NOT supported** and I am dropping it: hands-on pools show a small, low-coherence `|bar/rate|` with no clean
peak, which is a hand blocking the resonance, not moving it.

**Step 2 — settle r24's sign on the wire, with no build.** The third GhidraMCP subagent decoded the flown
cave completely and found something the kit had not recorded: the cave publishes **five bits into 0x14A byte 4**,
not into 427, and one of them is the r24 lane's sign.

```
0C4B9C  ld.h  -0x6ada[gp],r6      ; the r24 lane output copy (st.h r24,-0x6ada[gp] @0x3AD5A,
0C4BA0  cmp   0x0,r6              ;  the SAME invocation that does `add r24,r6` into the sum @0x3ACCA)
0C4BA2  bge   0x0C4BA6
0C4BA4  add   0x1,r7              ; -> after `shl 0x4`, 0x14A byte 4 bit 4
```
`gp-0x6ada` has exactly two accesses in the whole image — that store and this load (Python LE scan plus
Ghidra, set-differenced, positive-controlled). I re-extracted byte 4 from the r31–r34 rlogs
(`extract_r24sign.py`) and cross-spectrumed it against the wheel rate.

For a sinusoid, `sign(x)` is a square wave with the **same phase** as `x`, so the bit gives the lane's phase
directly. Amplitude is not recoverable from a sign bit; phase is, and phase is what the dispute was about.

| stratum | ∠(r24 re rate) @7 Hz | coh | closed form | ∠ @20 Hz | coh | closed form |
|---|---|---|---|---|---|---|
| creep hands-off v 1–3 | **+129°** | 0.36 | +126° | **−6°** | 0.80 | +10° |
| creep hands-off v 1–6 | +130° | 0.31 | +127° | −6° | 0.62 | +9° |
| loaded high-angle | **+179°** | 0.76 | +169° | **+8°** | 0.58 | +12° |
| highway | +132° | 0.15 | +144° | −6° | 0.15 | +10° |

**Verdict, four routes: r24 PUMPS at 7–9 Hz and DAMPS at 13–23 Hz.** The damping convention is anchored on
Honda's own damper `gp-0x6bd0 = −sign(gp-0x6abe)·M` with `gp-0x6abe ∝ −gp-0x6a56`, which is in phase with
`rate` as defined here; so in these variables **in-phase-with-rate = damping**.

### Two controls, because a null or a sign from one bit is worth nothing without them

- **CONTROL 1 — the `sign()` transform preserves phase.** Applied to `bar`, a signal we *have*, in the *same
  frame* as `rate`, so there is no timing term: `∠(sign(bar)/rate) − ∠(bar/rate)` reads **0 to −20°** across
  4–23 Hz in every stratum. The transform is sound.
- **CONTROL 2 — there is no 0x14A-vs-0x18F stream offset large enough to matter.** A constant offset τ makes
  the residual (measured − closed form) *ramp* with frequency at 360τ deg/Hz; one whole 100 Hz frame is
  3.60 deg/Hz. Regressed over 13–23 Hz the residual slope is **−0.61 to −2.50 deg/Hz**, i.e. an implied
  offset of **1.7–6.9 ms**, and the residual **intercept is +3 to +33°**. The verdicts would need ~80° of
  error to flip. A flat residual across a 3× frequency span is what rules a timing artefact out.
- The control I *designed* and which **FAILED** was bit 7 (`sign(gp-0x6b4c)`) against the 427 tap: coherence
  rate↔T came out 0.00–0.05 because the two npz files carry different `t0`, so the tap was misaligned in
  absolute time. I am reporting that rather than quietly dropping it. Controls 1 and 2 do the job it was
  meant to do, and the tap is used correctly (on its own instants) in `grind_loop_shape.py`.

**A byte-level correction this settles:** `twistloop` §3b states `gp-0x4f60 = −(cache torque) × 1.024`. It is
`+`. The 0x18F builder negates (`subr r0,r6` @0x55C5A) and every kit cache negates back (`i16be(d,0) * −1.0`).
With the correct sign, `r24 = gp-0x6752 · k · d/dt(gp-0x4f60)` and the wire says `gp-0x6752 = −1`, confirming
the kit's memory `accord-gp6752-is-negative-one` by direct measurement for the first time.

---

## 2. Deliverable 1 — which loop carries the 20 Hz line

**Both lanes, and r24 is the larger half.** Every lane enters the 1 kHz aggregator with a **unit coefficient**
(`FUN_0003aa2c`: `iVar19 = … + iVar21 + iVar16`, clamp ±0x2800 → `gp-0x6b94`), so the lanes' phasors add
directly and comparing them needs **no plant, no sign convention and no unit conversion.** `|T|` is measured
on the 427 tap at its own instants; `|r24|` is the closed form `(gain/1024)·|D4(f)|·|bar/rate|` with `|bar/rate|`
measured; phases are as measured above.

**Creep, hands-off, 20 Hz** (aggregator counts per wheel-rate count; Re = the damping component):

| lane | \|·\| | ∠ | **Re (damping)** | Im |
|---|---|---|---|---|
| LKAS rate PID (`gp-0x6b38`, the 427 tap) | 1.90 | −69° | **+0.68** | −1.77 |
| r24 at the flown 5244 | 3.23 | +5° | **+3.22** | +0.29 |
| **sum** | 4.17 | −21° | **+3.90** | −1.48 |

**Loaded high-angle, 7 Hz** — the stutter's own stratum, and the highest coherence in the whole analysis (0.92):

| lane | \|·\| | ∠ | **Re (damping)** | Im |
|---|---|---|---|---|
| LKAS rate PID | 2.50 | −62° | **+1.17** | −2.21 |
| r24 at 5244 | 3.37 | +166° | **−3.26** | +0.84 |
| **sum** | 2.50 | −147° | **−2.09** | −1.37 |

Reading, and it is the whole mechanism in two rows:

- At **20 Hz** the LKAS lane is nearly pure quadrature (Re +0.68 of magnitude 1.90 — 36 % efficient as a
  damper) and **r24 supplies 83 % of the damping**.
- At **7 Hz** r24 pumps 2.8× harder than the servo damps, and **the net aggregator damping is NEGATIVE**.
  That is the strong-turn stutter, and it is r24's, not the servo's.
- The zero crossing at 7 Hz in the loaded stratum is at `0xC6446` ≈ **1880**. Honda's own arms — `0xC6440`
  = 2048 and the rate LERP (2150–3072 at creep; **the LERP axis is the rectified column rate `gp-0x6ac0`,
  not vehicle speed**, a correction from the tracer) — sit essentially *on* that crossing. V280 flies 5244.

**What this does to `creep20`'s conclusions.** Its identification of T's 20 Hz content as the PID's own P+D
response to the rate stands — the chain mirror reproduces the tap to 4–14 % and I have no quarrel with it.
But the tap is `gp-0x6b38`, the LKAS lane alone. It is **a third of what the motor is actually told to do at
20 Hz**, and it is the third that damps least. Its counterfactual ranking (Kd 0 → ×0.63, lag pole 2.5 Hz →
×0.50) scores **the lever's own output**, which is the thing the kit's own standing instruction forbids
(`feedback-score-the-motion-not-the-lever-output`). Scored on the motion instead, the 2.5 Hz lag pole
*reduces* the 20 Hz damping (×0.97) and *increases* the 7 Hz pump (×1.42) — the opposite ranking.

**Limit cycle vs driven resonance (ledger §4 item 5).** `creep20`'s answer — a lightly damped mode rung by
broadband input, not a self-sustained cycle — is **supported and strengthened** here: at 20 Hz the aggregator
sum is at ∠−21° with Re +3.90, i.e. net damping, so nothing is pumping the 20 Hz motion. The 7 Hz case is
the opposite: Re −2.09, net pumping, consistent with a self-sustained cycle. **The two symptoms are different
kinds of thing.** [EVIDENCE for the phasors; BELIEF for the classification]

---

## 3. Deliverable 2 — the loop shapes, ranked

**The objective.** I rank on the **aggregator damping budget `Re(T + r24)`**, which is plant-free: it needs
only the unit-coefficient summing junction, `|T|` measured on the tap, and the measured phases. `|T|` is
re-scaled between shapes by the modelled `|C|` ratio from the decompiled arithmetic and its phase is modelled;
the controller model is validated against the 7 Hz analysis's episode-wise tap demodulation (it predicts
+118° at Kp 664 against their measured +115.6°, a 2.4° agreement).

**Why not a Bode/Ms table as the primary.** I built one (`grind_loop_shape.py` §G): de-embed r24 from the
tap-identified plant, `G0 = G/(1+R·B·G)`, then `L = (C + R·B)·G0`. **It does not reproduce the symptom** —
it returns `|S|` ≈ 1.1 flat across 18–22 Hz where the wire shows ~4× over stock, and its `Ms` is dominated
by a 1–2 Hz artefact of the de-embedding where the tap coherence is 0.2. I am reporting it as BELIEF-grade
and not ranking on it. The de-embedding divides by `1 + R·B·G`, which is near zero in several bins, and it
inherits the closed-form `|r24|` — the very number the next build must measure.

**Ranked shapes.** `Re@7 Hz` is in the **loaded high-angle** stratum (where the stutter lives, coherence
0.92); `Re@20 Hz` in the **creep** stratum (where the grind lives, coherence 0.81). Positive Re = damping.
`|C|@20 Hz` is the LKAS lane's own gain, i.e. the high-frequency risk.

| # | shape | cells | Re@7 Hz | ×base | Re@20 Hz | ×base | \|C\|@20 | authority (DC) |
|---|---|---|---|---|---|---|---|---|
| — | **as-built V280 rev 2** | — | **−2.09** | 1.00 | **3.36** | 1.00 | 1.82 | — |
| **1** | **out-lag pole 5→15 Hz + `0xC6446` → 2048** | `0xC63EC`/`EE` = 932/1457, `0xC6446` = 2048 | **+1.97** | damping | 2.91 | **0.87** | 4.46 | unchanged |
| **2** | **out-lag pole 5→15 Hz alone** | `0xC63EC`/`EE` = 932/1457 | −0.02 | **0.01** | **4.96** | **1.48** | 4.46 | unchanged |
| **3** | **out-lag pole 5→10 Hz** | `0xC63EC`/`EE` = 963/986 | −0.69 | 0.33 | 4.00 | 1.19 | 3.34 | unchanged |
| **4** | **fb pole 16.5→33 Hz** | `0xC63E8`/`EA` = 842/2814 | −1.62 | 0.78 | 4.04 | 1.20 | 2.41 | unchanged |
| 5 | Kd 128 → 192 | the `0xCB7D4` slot-7 table @0x0E511C | −1.77 | 0.85 | 3.75 | 1.12 | 2.21 | unchanged |
| 6 | `0xC6446` → 2048 alone | `0xC6446` | −0.10 | 0.05 | 1.31 | **0.39** | 1.82 | unchanged |
| 7 | V281 rev 3 (Kp flat 248) | the Kp LERP | **−2.42** | **1.16** | 3.84 | 1.14 | 1.23 | max-rate falls |
| 8 | Kd 128 → 64 | `0x0E511C` | −2.41 | 1.15 | 2.97 | 0.88 | 1.53 | unchanged |
| 9 | out-lag pole 5→2.5 Hz (`creep20`'s pick) | `0xC63EC`/`EE` = 1008/253 | −2.97 | 1.42 | 3.25 | 0.97 | 0.92 | slower step |
| 🛑 | **`0xC6446` → 512 (the 7 Hz proposal)** | `0xC6446` | +0.85 | damping | **0.33** | **0.10** | 1.82 | unchanged |

**Reading.**

- **Only shape 1 is net-damping at 7 Hz while keeping most of the 20 Hz damping.** It is the answer to the
  brief's question as asked.
- **Shape 2 is the best single lever**: it takes the 7 Hz pump to neutral and *raises* the 20 Hz damping by
  half again, with `0xC6446` untouched. The mechanism is pure phase: the 5 Hz output-lag pole contributes
  −54° at 7 Hz and −76° at 20 Hz, which is what makes the LKAS lane a quadrature term instead of a damper.
  Move the pole to 15 Hz with the DC gain held (`2b/(1024−a)/32` = 0.990 either way) and the lane rotates to
  −33° and −46°, where it damps.
- **The cost is high-frequency gain.** `|H_lag|` rises ×2.45 at 20 Hz and asymptotes at ×2.87 (1457/507).
  That is bounded and knowable, unlike removing the pole. **But 25–50 Hz is exactly the band no instrument
  on this car can see** — the 427 tap is 50 Hz (Nyquist 25) and the 0x18F streams are 100 Hz. Adding ×2.9 of
  loop gain blind above 25 Hz is the class of change that made V255/V269 undriveable. This is why shape 2 is
  **not** what I am asking to be cut next.
- **Shape 4 is the conservative version of the same idea** — same sign, half the HF gain rise (×1.81
  asymptotic), on two cells with **exactly one live reader each** (`0xC63E8` @0x28F8A, `0xC63EA` @0x28F86 —
  positive-controlled census in both images, so a change to them touches nothing but the LKAS rate PID's
  feedback filter). If the operator wants a dose in the same image as the instrument, this is the one.
- **Shape 7, V281 rev 3, is predicted to make the 7 Hz net damping slightly worse**, for the reason its own
  sibling analysis gives: a Kp cap lowers the servo's contribution and cannot touch r24. Registered as a
  prediction, not a block.
- **The 🛑 row is the finding this whole analysis exists to produce.**

**Highway and the other strata.** The highway stratum (997 s, coherence 0.51 at 7 Hz, 0.39 at 20 Hz) shows the
same signs: r24 pumps at 7 Hz (Re −2.30) and damps at 20 Hz. The full per-stratum tables are in
`_scratch/gls.txt`. The highway outer loop (openpilot's torque controller, now at 0.35–0.45× its old gain)
is a separate loop and none of these shapes moves it.

**Lineage check, done before proposing any of this** (a subagent read the 90 KB ledger and both
`BUILD-LINEAGE` files by address):

| cell | ever flown? |
|---|---|
| `0xC63EC`/`0xC63EE` (output-lag pole) | **NEVER TOUCHED** on any build |
| `0xC63E8`/`0xC63EA` (fb filter pole) | **NEVER TOUCHED**; the address was flagged unverified in the record — the reader census is now done, see §1 |
| Kd (`0xCB7D4` → slot 7 @0x0E511C) | **NEVER TOUCHED**; 128 flat across the whole axis on every image |
| `0xC6446` = 5244 + gate `0x3AA96` = `fb` | on the car since V104; V67 at 4× measured 0.52 vs 1.055 disengaged; V104 at 6× "just as bad as any other 6x" |
| `0xC6446` = 512 | **never flown** — stock never uses 512 either, because the stock gate cell `gp-0x683c` has zero writers, so stock takes Honda's 2048/LERP arm |

---

## 4. Deliverable 3, part 1 — the ONE build: V282, eight bytes, read-only

**Why an instrument and not a dose.** Every row of §3 is proportional to `|r24|`, and `|r24|` is a **closed
form, not a measurement**. Worse, `FUN_0003aa2c` has an arm the kit's record did not carry until today: if
`gp-0x671d` (a saturating fault-debounce counter) is non-zero, the gain is `0xC6442` = **1024**, not 5244.
At 1024 the whole ranking inverts — the servo becomes the dominant lane and r24 stops mattering. The 7 Hz
sibling found the same knife-edge independently. **One number decides between "raise r24" and "cut r24", and
it is not on the wire.** Eight read-only bytes buy it on a drive that is going to happen anyway.

**The edit.** Four `ld.h` displacement halfwords inside the **existing** cave at `0xC4B34` — which has been
byte-identical (`sha256[:8] = d3bb75d8`) on every image from V105 to V281 rev 3. No length change, no new
code, no relocation, no cal change, no authority change. I read every byte below out of the flown image myself.

| offset | now | becomes | effect |
|---|---|---|---|
| `0xC4B36`–`37` | `6c 94` (gp-0x6b94) | `26 95` (gp-0x6ada) | bit 6 operand A |
| `0xC4B42`–`43` | `9c b0` (gp-0x4f64) | `c8 94` (gp-0x6b38) | bit 6 operand B |
| `0xC4B64`–`65` | `1e 95` (gp-0x6ae2) | `26 95` (gp-0x6ada) | bit 5 operand A |
| `0xC4B70`–`71` | `da 94` (gp-0x6b26) | `6c 94` (gp-0x6b94) | bit 5 operand B |

⇒ **0x14A byte 4 bit 6 := `|r24| ≥ |T|`** and **bit 5 := `|r24| ≥ |aggregator sum|`**, at 100 Hz, alongside
the sign bit 4 that already exists. Both replaced bits are cheap to lose: **bit 6's duty on r34 is 0.0000** —
it carries no information at all today — and bit 5's current comparison (`|gp-0x6ae2| ≥ |gp-0x6b26|`) has
never appeared in any analysis.

- **Base:** V281 rev 3 (built, three-attacker PASS, unflown). One drive then tests the Kp cap *and* measures r24.
- **Positive control for the comparator machinery:** bit 5 works today (duty 0.337, 18.9 transitions/s), so a
  dead new bit 6 means my operands are wrong, not that the cave is broken.
- **What still needs doing before it is written:** recompute the 4-byte page CRC at `0xC4FFC` (the build
  scripts already do this) and re-hash the cave. `disassemble_bytes` with `dry_run:true` only; the cave's
  register use (`r6`, `r7`) is unchanged and the hook at `0x55C0E` is untouched.
- ⚠ **One nuance to carry into the decode**, from the cave trace: `gp-0x6ada` is published unconditionally,
  but `r24` only reaches the motor sum on the `r20 == 0` path (`cmp r0,r20; be 0x3AC78`, `r20 = setfe(gp-0x67ac == 1)`).
  The bits report the lane's *computed* value. Gate the decode on `gp-0x67ac` if a discrepancy appears.

**The alternative I rejected.** The 7 Hz analysis proposed re-pointing the 427 tap from `gp-0x6b38` to
`gp-0x6ada` (2 bytes at `0x55DF2`). It is a fine edit, but it **costs the delivered-torque tap** — the signal
every recent analysis, including this one's §2 and §3, is built on — and it reads at 50 Hz. The cave repoint
keeps T, runs at 100 Hz, and answers the same question. 427 has only **three free bits** (byte 0 bits 5–6,
byte 2 bit 7, all inside Honda's checksum, which is computed at `0x55F04`), so a second 10-bit field there is
not available.

---

## 5. Deliverable 3, part 2 — the pre-registration

**Statistic.** The duty of 0x14A byte 4 bit 6 (`|r24| ≥ |T|`) over **engaged, lateral, hands-off creep frames**
(`SCA ∧ STEER_REQUEST`, `vEgo` 1–3 m/s, `|bar| < 400` raw), and the same over the loaded high-angle stratum.
Secondary: bit 5's duty; and bit 4's phase re the wheel rate at the 20 Hz line, re-run as a replication.

**Predicted duties, computed on r32/r33/r34 before the drive** (`v282_prereg_duty.py`; r24 built at 1 kHz from
the measured bar through the decompiled arithmetic, T from the 427 tap):

| `0xC6446` arm actually live | bit 6 duty, creep | bit 6 duty, high-angle | bit 5 duty, creep |
|---|---|---|---|
| **5244** (the engaged arm, what the image says) | **0.300** | **0.199** | 0.213 |
| 3072 (Honda LERP top) | 0.188 | 0.119 | 0.149 |
| 2048 (`0xC6440` stock arm) | 0.132 | 0.076 | 0.109 |
| **1024** (`0xC6442`, the `gp-0x671d` fault arm) | **0.065** | **0.038** | 0.059 |
| 512 | 0.029 | 0.019 | 0.030 |

Bit 5's predicted duty is an **upper bound** — the real aggregator carries lanes I cannot reconstruct, so
`|sum|` is larger than `|T + r24|` and the true duty is at or below the number given.

**Thresholds.**
- **bit 6 duty ≥ 0.22 in engaged creep ⇒ the 5244 arm is live and r24 is the dominant 20 Hz lane.** Then
  `0xC6446` must NOT be cut for grinding, and the next lever is the output-lag or feedback pole (§3 shapes 1–4).
- **bit 6 duty ≤ 0.10 ⇒ the 1024 arm is live**, r24 is a minor lane, the whole r24 reading collapses, and the
  20 Hz line is the LKAS servo's after all — go to `creep20`'s ranking and to Kd/lag-pole levers only.
- **0.10 < duty < 0.22 ⇒ an intermediate arm (2048/3072)**; re-derive before dosing anything.

**FAIL sentence.** *The build fails if, over ≥ 20 s of engaged lateral creep, bit 6's duty is 0.000 or 1.000
(a dead or railed comparator, i.e. my operands or the cave's masks are wrong), or if bit 4's phase re the
wheel rate at 18–22 Hz does not replicate the −6 ± 25° measured on r31–r34 — in which case nothing in §1–§3
is safe to act on and the sign-bit method itself is in question.* Bit 5 remaining live is the positive
control that distinguishes "my operands are wrong" from "the cave stopped firing".

**Cost FAIL.** *The build fails on cost if the delivered-torque tap on 427 stops decoding, if any DTC appears
that V281 rev 3 did not produce, or if the operator reports any change in feel attributable to this edit —
it is read-only and must be invisible.* There is no authority change to fail on: no cal byte moves.

**What a null licenses.** A duty inside 0.10–0.22 licenses **nothing about grinding** and licenses the
statement *"the r24 gain arm is not the flown cell and the `gp-0x671d` path is active in normal driving"*,
which is itself a finding worth the drive and would need `gp-0x671d` traced before any further r24 work.
A clean 0.30 licenses **cutting shape 4 (`0xC63E8`/`0xC63EA` = 842/2814) as V283**, sized on that same drive.

**V281 rev 3's own pre-registration, amended** (legitimate while unflown): add *"on the aggregator damping
budget the Kp cap is predicted to leave the 7 Hz net damping unchanged or slightly worse (−2.09 → −2.42),
because it lowers the servo's damping and cannot touch the engaged-only r24 lane. If the 7 Hz ripple does not
fall, that is the predicted outcome and it indicts `0xC6446`, not Kp."*

---

## 6. Deliverable 4 — what I could NOT close, and the measurement that would

| # | open | why it matters | the exact measurement |
|---|---|---|---|
| 1 | **`\|r24\|`, and which gain arm is live** | every number in §3 scales with it; the ranking inverts at 1024 | V282's bit 6 duty, above. This is the build. |
| 2 | **The aggregator `gp-0x6b94` is not on the wire as a magnitude** | the damping budget uses `T + r24` and omits `gp-0x6bbe`, `gp-0x6b26`, r26 and Honda's damper | V282's bit 5 bounds it; a full answer needs a magnitude tap on `gp-0x6b94`, which would cost the 427 T field |
| 3 | **The plant above 25 Hz** | shapes 1–4 raise the LKAS loop gain ×1.8–2.9 asymptotically into a band no instrument can see; this is the dominant risk in every one of them | nothing on this car can measure it. The 427 tap is 50 Hz and the 0x18F streams 100 Hz. **The honest mitigation is dose size, not measurement** — hence shape 4 before shape 2. |
| 4 | **Whether the 20.3–21.0 Hz line is really 20 Hz or an 80/120 Hz alias** | 80 Hz folds to 20 Hz on *both* a 50 Hz and a 100 Hz sampler, so no CAN instrument can separate them; the chain mirror is circular here | the audio channel at 44.1 kHz (`accord-audio-bounds-the-can-alias-risk` did this once for another band) — a spectral line at 80/120 Hz in the grind seconds settles it, and it is free |
| 5 | **`gp-0x671d`'s identity and duty** | it selects the 1024 arm; the kit's record did not carry this arm at all until today | trace its writers in Ghidra, or infer it from V282's duty falling in the 0.065 band |
| 6 | **The 1 kHz tick** | every phase in this analysis assumes `Ts = 1 ms` for `FUN_0003aa2c` and `FUN_00028ea6`; two tracers declined to assert it (`FUN_0002214a` has no code xrefs, only a task-descriptor entry at `0xBB928`) | decode the task-descriptor record at `0xBB920`–`0xBB93B` and its period field. A wrong `Ts` rescales `D4`'s phase and would move every verdict. |
| 7 | **`gp-0x69a4`'s range, hence r26's true gain** | the `fb` gate cuts r26 6× as an uninstrumented side effect, and r26 shares r24's sign | decompile `FUN_000352b4`'s table fill and the ROM behind `gp-0x37e8`/`gp-0x37fc` |
| 8 | **Which r24 LERP bank is live** (`gp-0x6a5e` against breakpoints `0xC6010` = [0, 640, 3200, 6400]) | it sets Honda's own creep gain at 2150 or 3072, which is the reference for any revert | identify `gp-0x6a5e`'s writer and units, or read it on the wire |

---

## 7. Corrections of record produced by this analysis

1. `creep20` §1.5: `bar` re `rate` at 20 Hz is **+114°, not −70°** (mixed conventions). Its plant `G` and its
   `L_in` margins inherit the same convention and should be re-derived before being cited again.
2. `twistloop` §3b/§3c: `gp-0x4f60 = +(cache torque) × 1.024`, not `−`. The conclusion it drew (r24 pumps at
   7 Hz) survives; the 20 Hz half of its §3b ("in phase with the rate to within ~25°, anti-damping") is
   **wrong in sign** — r24 damps at 20 Hz.
3. `twistloop` §3c: *"The 100 Hz 0x18F torque cannot carry 20 Hz"* is false. 100 Hz resolves 20 Hz at five
   samples per cycle, and `creep20` and I both measure it at coherence 0.9+.
4. The P clamp is **`0xC61BC`**, not `0xC61BE`. Both hold 15360, so a spot check cannot tell them apart and a
   build editing the wrong one would pass every readback assertion.
5. Honda's r24 LERP is indexed on the **rectified column rate `gp-0x6ac0`** (4.71 counts per deg/s), not on
   vehicle speed. At creep it is flat at 2150–3072, so `0xC6446` = 5244 is a **1.7–2.4× raise over stock**,
   not the 10.24× that "512 → 5244" suggests. The ledger's B25 row already says 2.00×; the two 2026-09-03
   handoffs say 10.24×.
6. The `FUN_0007e74a` differencer divides by the **measured elapsed tick delta**, not by `N`; `0.5·Δbar`
   holds only while exactly one tick elapses per call.
7. The cave publishes to **0x14A**, not to 427; the 427 packer is a different function (`FUN_00055d80`).
   The brief and several handoffs conflate them.
8. The ×6 forward gain is a **code repoint** of the `ld.h` at `0x2A1EE` from `tp+0x746c` to `tp+0x7cd0`, not
   a cal edit to a cell that was 891. `0xC646C` is still 891 and still serves five other readers.

---

## 8. Files

`rlog-tools/studies/grind/`: `extract_r24sign.py` (0x14A byte 4 + 0x18F + 0xE4 + carState from the rlogs) ·
`r24_sign_on_the_wire.py` + `_scratch/r24_sign_on_the_wire.txt` · `grind_mode_phase.py` +
`_scratch/grind_mode_phase.txt` · `grind_loop_shape.py` + `_scratch/gls.txt` · `v282_prereg_duty.py` +
`_scratch/v282_prereg_duty.txt` · caches `_scratch/r24sign_r3{1,2,3,4}.npz`.
