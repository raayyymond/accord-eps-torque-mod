# HANDOFF 2026-07-31 — V61 made it WORSE, and that is the best news this kit has had

**Session shape:** operator reported the V61 drive; orchestrator + three subagents (two firmware tracers
and an rlog analyst); **V62 and V63 both built, verified and unflashed at close-out.**

**One-line summary:** V61 removed the torsion-bar rate lane and the grinding got worse *and spread to
manual driving* — which means the lane was the mode's **damper**, and every previous build on it pushed
the wrong way. **V62** doubles it in 6 bytes. Then the operator objected that this changes manual feel to
fix an LKAS-specific symptom, which turned out to be the most productive note of the session: the firmware
has its **own oscillation detector** (`gp-0x671a`), both rate lanes already branch on it, and **V63**
raises only the oscillation-gated arms — same damping, **zero manual-feel cost**, and a smaller edit.
**Fly V63 first; V62 is the fallback that cannot miss.** See §5b.

---

## 1. What happened on the car

V61 zeroed the torsion-bar torque-RATE lane at **both** taps of its shared value
`r1 = clamp(gp-0x4f62, ±5120)` — `0x3AB6C mul r1,r6,r0 → mul r0,r6,r0` (r26) and
`0x3AC16 mov r1,r8 → mov r0,r8` (r24). Two single-bit reg1 changes. No cave. No calibration moved.

Operator, authoritative:

| condition | before (V59-class) | on V61 |
|---|---|---|
| **LKAS ON, forward** | grinding present | **significantly worse** — higher amplitude, louder |
| **LKAS OFF, forward** | clean | **grinding newly present** when turning |
| **LKAS OFF, reverse** | clean | **grinding definitely newly present** |

This is the **first signed on-car result this kit has obtained on any vibration lever.** Everything since
V38 has been a null or a fault. A null tells you an address is not the answer; a *worsening* tells you the
**gradient**, and the gradient is what lets you pick a direction instead of another address.

---

## 2. Why the lane is a damper — the sign, verified from image bytes

The orchestrator verified this personally rather than relaying it, per the standing instruction.

1. **Polarity cancels, so its value doesn't matter.** `gp-0x6752` is **one load @`0x3AB78`, reused
   unmodified by both lanes** — and the *same byte* is read by `FUN_0003a382`'s resonance lane
   @`0x3A71A`, the aggregator's one genuinely torque-**proportional** P-term. Comparing the rate lanes
   against that P-term therefore cancels polarity entirely. (Independently: it is the literal `1`, written
   at boot in `FUN_000490ac` @`0x490b6`–`0x490c0`.)
2. **The combine chain is all `add`.** `0x3ACC8`–`0x3ACDA` decodes as ten Format-I instructions, every
   lane entering with `add`, each add's `reg1` threading the previous add's `reg2` — a textbook
   accumulator chain. Not one `sub`. (⚠ Past `0x3ACDC` a linear halfword walk desyncs on a multi-halfword
   instruction; no claim is made about that region.)
3. ⇒ `r24, r26 = +Kd·d(T_bar)/dt`, **added in phase with assist**. `Kp·x + Kd·dx/dt` — a lead compensator.

### Why "in phase with assist" is damping, not positive feedback

Hands-off, the mode is the **steering-wheel inertia on the torsion bar**. Motor torque is applied to the
**column only**, so with `T_m = K·T_b + Kd·dT_b/dt`, `phi = theta_w − theta_c`, `T_b = k·phi`:

```
J_w·theta_w'' = -T_b                 J_c·theta_c'' = +T_b + T_m - T_road
--------------------------------------------------------------------------
phi'' + (Kd·k/J_c)·phi' + k·(1/J_w + (1+K)/J_c)·phi = T_road/J_c
--------------------------------------------------------------------------
```

The `phi'` coefficient is **`Kd·k/J_c > 0` — positive damping, linear in `Kd`. At `Kd = 0` the mode has
no damping term at all.** That is V61. That is what the car did. And it explains the *manual* symptom,
which nothing else in the record could: base assist runs whether or not LKAS is engaged, so removing base
assist's only fast damper makes the mode reachable by a driver's own input — worst in reverse.

Adding the motor/current-loop lag `tau`, the `K·T_b` term contributes `≈ -K·k·tau/J_c`, so
`zeta_net ~ (Kd − K·tau)·k/(2·J_c·omega)`. **Stock pins the operating point:** the mode sustains with **no
ring-down at all** (66 candidate decays, longest 0.63 cycles) ⇒ `zeta_net ≈ 0` ⇒ `Kd ≈ K·tau`. Hence
V61 (`Kd = 0`) ⇒ `zeta_net < 0` ⇒ diverges. **Observed.**

🛑 **The alternative explanation is ruled out arithmetically.** "V61 just removed assist, so the driver
worked harder" fails because **a derivative term is DC-neutral** — at constant torque the rate is zero and
both lanes contribute nothing. V61 changed *only* dynamics. That is what makes this a clean measurement.

---

## 3. What this falsifies, and the lesson

`eps_lkas_chain_model.py:1792` framed r26 as **"excitation-to-amplifier: faster slew → bigger column-torque
derivative → bigger r26 → more motor torque → more column motion → repeat"** and recommended *"the r26 cal
kill attacks the amplifier."* That predicts killing it helps. **Both passages are struck and corrected in
place.** The framing confused a term in phase with **velocity** (damping) for one in phase with
**displacement** (gain).

⇒ **V39 (killed r24, conditionally), V42 (killed r26), V61 (killed both) all tested this lane DOWNWARD.**
Every result stands. They simply bracket the **wrong side of the optimum**.

★ **The lesson, and it is the inverse of the V44/FactorC trap.** There, a withdrawn **rationale** was
mistaken for a withdrawn **result**, and an already-falsified lever got re-proposed. Here every result
stands and only the **direction** was wrong. Both mistakes come from the same habit: reading a lever's
history as a verdict on the **address** instead of on the **direction tested**. The lineage check should
record *which way* a lever was pushed, not just that it was pushed.

★ **Why this lane and not the dampers already tried.** `FUN_0003aa2c` is **task 1, 1000 Hz** ⇒ ~3.8° of
ZOH lag at 20.9 Hz. The boost and damping lanes are **task 5, 100 Hz** ⇒ **37.6–75.2°** — the structural
reason V44 (FactorC) and V47 (Factor E) were null. **The rate lane is the only damping mechanism in the
whole chain fast enough to act on a 20.9 Hz mode.** That was already on record as a warning; it now reads
as a signpost.

---

## 4. V62 — built, verified, unflashed

```
0x3AC20  42AA -> 42A9   sar 0xa,r8 -> sar 0x9,r8   r24: (dtorque * gain_B) >> 10 -> >> 9
0x3AB76  32AA -> 32A9   sar 0xa,r6 -> sar 0x9,r6   r26: (stage1  * gain_A) >> 10 -> >> 9

image SHA 80d9e1f721b741722a9d4b141a2d328fe8d999705765fedffab1ad23aa9264c7
RWD   SHA 1e0806a1eac69688e6d636fa02c5b1e864da40a65a4d3f8137d444d1ec5bff8e
```

**6 bytes off V59** (2 immediate bytes + MAIN CRC), 8 off V61, 88 off V38. ⭐ **CAL CRC unchanged** and
⭐ **`0xD2000`-block CRC unchanged** = machine proof no calibration moved and V60's falsified blend is
absent. 50/50 CRC blocks pass; RWD round-trips with every gate re-run on the readback; **independently
re-verified from the built image** (taps back at `r1`, both shifts `sar 0x9`, `0x3AB70` still `sar 0xa`,
exactly two code bytes changed, all gain cals untouched).

It is the **matched inverse of V61**: `Kd`→0 diverged, `Kd`→2× is the same-sized step back, and the
damping coefficient is **linear in `Kd`**.

### 🛑 Why `sar` immediates and NOT the gain calibrations — three reasons found by tracing

The obvious lever was the gain cals. It is the **wrong instrument**:

1. ~~**The gain is a priority chain whose live arm cannot be pinned statically.**~~
   🛑🛑 **THIS REASON IS WITHDRAWN — see §5b. It was based on a WRONG reading of `gp-0x671a`.**
   The original text said it was *"a bounded [0,5] persistence ramp tracking consistent sign of a rate
   signal, which during a 21 Hz oscillation plausibly never saturates."* **It is the opposite**: a
   hard-reversal **counter** that reads 0 during smooth steering and rises during an oscillation. So the
   arm *can* be pinned, it *is* the oscillation arm, and editing that cal is not "betting on a branch" —
   it is the **better** instrument, which is V63. Left visible rather than deleted because this is the
   reasoning that produced V62.
   ⚠ Still true and still relevant: `gp-0x671d` is an **event/rising-edge counter** (not "startup dwell",
   as an older memory said), it outranks r24's `state>=5` arm, and it may be self-excited by the
   oscillation — which is why **r26, not r24, is expected to carry V63.**
2. **r24's default arm is MODE-INDEXED, not one location.** `FUN_0003ad74` reads a mode byte at
   `gp+0x63fd` and indexes four ROM pointer arrays (`0xCBF5C`, `0xCC044`, `0xCC12C`, `0xCC214`).
   `0xD2AEC`←`0xCC154` idx 10, `0xD2B28`←`0xCC23C` idx 10, **`0xD6AEC`←`0xCC184` idx 22**.
   ⚠ **Correction made mid-session:** the orchestrator first read `0xD6AEC` as a **redundancy twin** of
   `0xD2AEC` (the blocks are byte-identical, with separate directory entries and separate CRCs) and
   called it the V27 desync class. **That was wrong.** They are **two different modes' records** that
   happen to hold identical data, each reached through its own valid pointer slot.
   (Mode **10** is this car — independently established: PN `39990-TVA-A160` → key `TVAA1` → config row 2
   → INDEX 10, the chain V44/V47 were confirmed on-car to hit. One-bit residual: the coded row lives in
   EEPROM, not the flash dump.)
3. **`gp-0x683c` has zero writers image-wide** ⇒ the 512 arms `0xC6446`/`0xC6444` are dead calibration.
   ⚠ Single-method — wants a raw LE byte scan of **both** gp-relative encodings before anything rests on it.

**`sar 0xa` → `sar 0x9` doubles the lane under every arm and every mode.** Immune to all three. And it is
the same **edit class** as V61 — an immediate-field change on a verified instruction, opcode and reg2
byte-identical, same length, no cave, so **GATE 1 is vacuous**.

### 🛑 Why `0x3AB76` and not `0x3AB70` — an overflow argument, not a coin flip

r26 is two chained multiplies. **V850 `mul r1,r6,r0` discards the HIGH word into `r0`**, so a 32-bit
overflow is silently truncated into a garbage, possibly sign-flipped lane value. Worst case
(`avg = 0xFFFF`, `dtorque = 5120`):

| edit | `stage1 × gain_A(3072)` | vs INT32_MAX |
|---|---|---|
| stock | 1.007e9 | 47% |
| @`0x3AB70` | 2.013e9 | **94% — 6% margin** |
| @`0x3AB76` | **unchanged** 1.007e9 | 47% — **no new risk** |

Doubling the **second** shift leaves every multiply operand at its stock magnitude.

### Headroom — doubling stays linear

A saturating lead term is worse than useless (its describing-function gain falls with amplitude), so this
is the binding constraint. At the measured 1400 counts / 20.9 Hz, `peak dtorque ≈ 367` = **7% of the
shared ±5120 clamp**; r24 sits at ~9% of its own ±8192 clamp on the `state≥5` arm. Headroom is
**arm-dependent** — ~22× (`gate_671d`, 1024), ~11× (`state≥5`, 2048), **~7.3× (natural LERP at stock max
3072, the worst case)**. Doubling keeps **≥3.6× margin under every arm**.
Model: `analysis-2020accord/rate_lane_damping_model.py`.

### Residuals, stated not smoothed

- **`avg(gp-0x69a4)` magnitude is still unmeasured** after three sessions. Its LERP axis `gp-0x6b4a` is a
  `FUN_00026c80` **mixer output**, possibly LKAS-command-adjacent — so r26's own gain may be
  command-driven, a **second-order loop nobody has modelled**. If r26 were already pinned at ±8192,
  doubling would deepen a saturation. **Bounding argument against:** a lane pinned at 8192 would dominate
  the aggregator's own ±10240 sum clamp, and V61 (which zeroed it) would have produced a far more dramatic
  change than reported. Not proof. **r24 is fully bounded and immune to this.**
- **Manual feel will change** — no LKAS-only decoupling point exists in this chain (traced). Risk
  direction is "nervous"/noise-sensitive rather than heavy. This is the lane whose *removal* the operator
  felt immediately, so a feel change is itself confirmation the edit is live.
---

## 4b. The rlog confirms it — and the mode MOVED, which is the stronger evidence

Route `00000031--0441e00d2b`, **22,052 frames / 222 s**, parking lot (v max 1.5–5.4 m/s), segs 0/3 manual,
segs 1/2 engaged. **FLIGHT-CLEAN:** `ST==4` in **0** frames (streak now past 143,000), `ST==0` in
22,042/22,052, zero `steerUnavailable`/`steerTempUnavailable`/`canError`/`immediateDisable`/
`steerSaturated`, one `controlsMismatch`. **2,851 frames ≈ 28 s of reverse.**

**Engaged creep, speed-matched (v ≤ 5.35 m/s), identical method, V59's route `2c` as control:**

| build | n | peak | prominence | abs power |
|---|---|---|---|---|
| V59 route `2c` | 9 | **21.18 Hz** | 227× | 5.26e8 |
| V61 route `31` | 3 | **18.25 Hz** | 486× | **4.15e9** |

**−2.93 Hz and ×7.9 power.**

★★ **The frequency shift is the decisive observable and it is structural.** A pure **gain** change cannot
move a resonance frequency. A **phase** change can — and removing a lead compensator lowers the frequency
at which the loop phase reaches −180°, so the limit cycle settles lower. The direction was predicted from
the arithmetic *before* the spectra were computed. Amplitude alone could be confounded by route or effort
differences; the frequency cannot be.

**The three conditions, in exactly the order the operator reported them:**

| condition | n | peak | prominence | abs power |
|---|---|---|---|---|
| ENGAGED creep | 3 | 18.25 Hz | 486× | **4.15e9** |
| **MANUAL reverse** | 2 | **17.82 Hz** | **1910×** | 5.78e8 |
| MANUAL forward | 5 | 18.54 Hz | **13.1×** | 3.82e6 |

⇒ Manual reverse carries **151× the power of manual forward at the same frequency as the engaged line** —
the *same mode*, unmasked, not a new one.

### 🛑 Refinement — "manual forward is a floor" was wrong, and the error is worth keeping

The 13.1× is an **un-gated average** over all manual-forward driving, diluted by quiet cruising. Gated on
**sustained effort ≥ 1000** it is **146×** (n=2, f0 18.40 Hz). A second analyst reached the same
conclusion from the other side: the loudest manual windows are at **|v| = 0.00–0.6 m/s with the wheel
cranked** (effort 2200–3300), and a `|v| ≥ 0.3 m/s` "moving" gate **drops them entirely** — that arm goes
from *"median prominence 5.3×, mostly floor"* to *"median 317×, envelope p99 median 2495"*, f0 **17.08 Hz,
sd 0.76, n=7**.

**Two different gates each erased the same population**: mine by omitting an effort condition, theirs by
imposing a speed one. The phenomenon *is* present in manual forward — but only while the driver is
actually loading the wheel, which is precisely what the operator said (*"in some scenarios"*).

Manual/reverse sits at **17.0–17.8 Hz**, ~0.5–1.3 Hz *below* the engaged 18.3 Hz — same mode family,
frequency shifting with loading, both far from V59's 21.2 Hz.

⇒ ★ **New standing convention: use a near-stationary, high-effort manual arm.** That is where manual EPS
instability lives, and both a speed gate and a missing effort gate erase it.

### ★ The ratchet stayed LKAS-gated while the grinding did not

Engaged: **10 of 14** windows reach 10× prominence at 6.56 Hz. Manual: **0 of 28**. Reverse: **0 of 10**.
⇒ under V61 the two symptoms **separated further** — the grinding escaped into base assist, the ratchet
did not. Independent support for them being genuinely different phenomena.

This is also the third independent exclusion of the ratchet-2nd-harmonic reading: (i) a harmonic cannot
live in a condition where its fundamental fails a presence test outright; (ii) the arithmetic does not
close — 2 × 6.56 = **13.1 Hz**, not 17.8; (iii) Q is wrong — the reverse line is Q 8.8–14.7 against an
engaged ratchet of Q ≈ 5.3, and a distortion harmonic inherits roughly its fundamental's fractional
bandwidth, so it would be broad.

⚠ **Caveats:** n is small (3 engaged / 2 reverse runs), one route against one control route. The effect
sizes dwarf that, but V62's drive is what confirms them.

### ⚠ A methodology trap caught in-flight — worth adding to the conventions

The first pass pre-restricted the search to the strict **18–26 Hz** band, and the argmax **pinned to the
band edge at 18.04 Hz with sd 0.00** — a truncation artifact, because the mode had moved *below* the band.
**The strict band is for presence-testing a mode whose frequency you already know; it is the wrong tool
for locating one that has shifted.** Locate over 12–30 Hz, then interpret.
(The ratchet-2nd-harmonic trap is separately excluded: in manual reverse the 6–10 Hz fundamental is 9.6×
while the 17.8 Hz line is ~1900× — a "harmonic" 200× stronger than its fundamental is not a harmonic.)

### ⇒ V62 now has TWO independent predicted observables
- **(a) amplitude falls** — engaged power back toward 5e8, manual reverse back toward the forward floor.
- **(b) frequency rises back to ≥ 21.2 Hz**, or the line disappears.
**(b) is the sharper test.** If amplitude falls but the frequency does *not* move, the lane is acting as a
plain gain and the lead interpretation is wrong — that must be reported, not explained away.

---

## 5. ✅ A retracted piece of reasoning worth not re-deriving

Mid-session the orchestrator argued that **`0xC6C42` (the differentiator's delay `D`) is unsafe to edit
because `gp-0x4f62` is lockstep-shadowed to `gp-0x4488`.** **That reasoning is wrong and is retracted.**
`0xC6C42` has **exactly one reader** (`FUN_0007e74a` itself, four `ld.hu` for different steps of the
circular-buffer indexing), and `D` feeds a **single computation whose result is stored to both cells in
sync** — there is no mechanism by which moving `D` desyncs the pair.

The real reason `D` stays stock in V62: it sets the differentiator's **time window**, and its frequency
response at other values is uncharacterised.

⇒ **`D` is therefore a legitimate future lever, and specifically a PHASE lever:** `D` 4→2 halves the
lead's transport lag, **15.1° → 7.6° at 20.9 Hz**. That is the natural **V63** if V62's gain doubling
comes back null — because a null would mean the lane's damping is phase-limited, not gain-limited.

---

## 5b. The operator's objection to V62 — and V63, which removes its cost

**Operator, after V62 was built:** *"we seem to be affecting manual steering feel even though the symptom
is specific to LKAS-engaged only. If the stock values of the doubled dampers is sufficient to remove
vibration on manual steering, how come it's not enough for LKAS-engaged? The V62 edit kind of blindly
ignores this question."* **Correct on both counts.**

### The answer: stock `Kd` isn't sufficient for manual either — manual has `Kd` *plus your hands*
The mode is the **steering wheel's inertia on the torsion bar**, and the driver's arms damp exactly that
mass. Under LKAS hands-off, that damper is gone. Measured 2×2 (⚠ columns use different statistics —
per-frame envelope for manual, window p99 for engaged — so read *within* a column):

| | hands ON (manual) | hands OFF (LKAS) |
|---|---|---|
| `Kd` stock (V59) | clean, 9.2 | **marginal**, 1092 |
| `Kd` = 0 (V61) | mode appears, 163 | **much worse**, 3007 |

Removing `Kd` degraded **both** arms — proportionally *more* in manual (17.8× vs 2.75×), because engaged
was already at the edge. `Kd` was doing real work in manual all along; it just had help. **And LKAS also
injects energy at the mode frequency** (command→bar transfer peaks at **21.09 Hz**, the global max over
3–46 Hz, coherence 0.917). Two differences, both real.

### V62's residual cost is small, and computed rather than hoped
The lane is a **derivative**, so it is inherently frequency-selective — its output scales with `f·A`:

| condition | r24 @2048 | @4096 | added |
|---|---|---|---|
| deliberate steering, 1 Hz | 47 | 97 | **+50** (0.49% of the ±10240 sum clamp) |
| the mode, 18.25 Hz | 729 | 1461 | **+732** |

**14.6:1 selectivity.** Not a blunt global change — but a mitigation, not an answer to the objection.

### ★★★ The real answer: the firmware already has an oscillation detector
Both rate lanes' gain chains end in `assist_state gp-0x671a >= 5`, and `gp-0x671a` is a **hard-reversal
counter** (`FUN_000428d4`, 1 kHz): the neutral state **resets it to 0 every tick** and only exits when
`|gp-0x6c2c| > 12800`; a crossing of the *opposite* threshold increments it; 50 quiet ticks clear it.
⇒ **0 during smooth steering; `state>=5` means an oscillation is happening.** At 18–21 Hz the half-period
is 24–28 ms, inside the 50 ms timeout, so it arms in ~125–150 ms and latches.

```
r24: … | state>=5 -> 0xC6440=2048 <-- OSC ARM | else -> mode-indexed LERP (smooth)
r26: … | state>=5 -> 0xC643E=1536 <-- OSC ARM | else -> gain_A LERP       (smooth)
```

**V63 raises only those two** (→4096 / →3072). Damping only while oscillating; both smooth-steering
defaults stock. **6 bytes off V59, MAIN CRC unchanged, a smaller edit than V62 with the manual-feel cost
removed by construction.** No new arithmetic risk: **3072 is already `gain_A`'s own stock maximum.**

🛑 **The polarity was disputed by two subagents and I resolved it in Ghidra myself.** One trace read
`0xC643E` as the `state<5` arm — which would have raised the *smooth-steering* gain: all of the cost,
none of the benefit. `0x3AA7C cmp r14,r12`/`bc` ⇒ `r2=1` iff `state>=5`; `0x3AB66`/`0x3AC10` `be` skip
the loads when `r2==0`. ★ **A branch polarity that decides a build's direction must be read by the
orchestrator, not relayed.**

🛑 **Residuals:** whether `gp-0x6c2c` crosses ±12800 in the real vibration is **unverified and
load-bearing** — if not, V63 is inert and **a null is ambiguous**. Resolve with **no probe and no cave**:
fly V63 first, and if null fly V62, which cannot miss. And `gate_671d` outranks r24's arm and is live, so
**expect r26 to carry V63**.

## 6. Next steps

0. ★★★ **Flash V63, then V62 only if V63 is null.** V63 gets the same damping increase with zero
   manual-feel cost; V62 cannot miss but does change manual feel. That order also resolves V63's own
   ambiguity for free — V62 working after V63 nulls means the reversal detector was not tripping.
   Repeat the V61 route so the comparison is like-for-like: parking-lot creep,
   deliberate LKAS on/off at matched speed and angle, **plus the same manual-forward and manual-REVERSE
   passes**. 🛑 **Manual reverse is the highest-information single test** — V61 introduced grinding there
   from nothing, with no LKAS in the loop at all.
   **Interpretation fixed in advance so it cannot drift:**
   - **BETTER** ⇒ direction confirmed; next question is *how much more* (V63 = 4×, or the phase lever).
   - **NULL** ⇒ phase-limited, not gain-limited ⇒ go to `0xC6C42` `D` 4→2 (§5).
   - **WORSE** ⇒ past optimum into noise amplification; back off to 1.5×, do not abandon the lane.
1. **Analyse route `00000031--0441e00d2b`.** The decisive question: does the newly-appearing **manual /
   reverse** line sit at the **same ~20.9 Hz and Q** as the engaged grinding (⇒ the same mode, unmasked —
   confirms everything above) or at a different frequency (⇒ a genuinely different finding, and V62's
   rationale needs revisiting *before* it flies)? Also confirm **`ST==4`** stayed at 0. Use the strict
   18–26 Hz band + presence test, `latActive`, sustained-effort hands-off, and peak-frequency **scatter**
   as the mode-vs-floor discriminator.
2. **The operator's fallback — motor-command feedforward compensation** (subtract the expected bar torque
   due to LKAS motor torque) — remains a sound idea and the traced absence of any such compensation still
   stands. **But it is cave-class**, and caves are this kit's only bricking class (V24, V27, V48B). The
   rate lane gives a **cal/immediate-class handle on the same loop**, with a measured gradient. Exhaust
   V62/V63 first.
3. **Close `gp-0x69a4`.** It has been `[OPEN]` for three sessions and it is now the only unquantified term
   in the lever we are actually pulling. A V59-class thermometer probe on `|gp-0x69a4|` would settle both
   its magnitude and whether it is LKAS-command-driven.

---

## 7. Files touched

- `analysis-2020accord/build_v62_tva.py` — new, the build.
- `analysis-2020accord/rate_lane_damping_model.py` — new, the sizing/physics model mirroring the integer
  arithmetic.
- `analysis-2020accord/eps_lkas_chain_model.py` — the "excitation-to-amplifier" framing struck and
  corrected in place (two passages); self-tests still pass.
- `docs/STATE.md`, `docs/BUILD-LINEAGE.md` — V61's result, V62's entry, direction corrections on the
  V39/V42 rows.
- `memory/accord-rate-lane-is-the-damper-not-the-amplifier.md`,
  `memory/accord-v62-doubles-the-rate-lane.md`, `memory/MEMORY.md`.
