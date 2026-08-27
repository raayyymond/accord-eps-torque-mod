# HANDOFF 2026-08-20 — V103 BUILT · `gp-0x6752` = −1 · **f0 IS THE ENDPOINT**

**Read `docs/STATE.md` first.** This file is the narrative and, per standing operator instruction
(2026-08-20), it carries **every investigation finding — including the negative ones — and every open
item**, so that nothing here is re-derived by a future session. See
`memory/feedback-handoffs-must-carry-all-findings-and-open-items.md`.

**Session shape:** orchestrator + 7 subagents (`route-v102`, `route-stock`, `lkas-input-range`,
`pole-hunt`, `ratchet-inertia`, `cave-engineer`, `pump-hunt`). Two new routes scored, one build cut,
one record-reversing firmware fact established, seven record defects corrected.

---

## 0. TL;DR — WHAT CHANGED

| | |
|---|---|
| **On the car** | **STOCK (V9b)** — he flashed V102, drove route `0x96`, then flashed stock and drove route `0x97`. |
| **Built, NOT flashed** | **V103** — image `df6104bd…f71d`, `.rwd` `a8e68185…4361`. Orchestrator-verified from disk. |
| **Biggest fact** | 🛑 **`gp-0x6752` = −1, not +1.** Reverses the PID sign classification the kit has carried since V38. |
| **Biggest measurement** | **`f0`**, the `Re(Z)` zero-crossing, **marches with gain: 21.90 / 23.61 / 24.90 Hz at 1× / 4× / 6×**, CIs disjoint. |
| **Endpoint change** | The primary endpoint is now **`f0`**, not a band-RMS ratio. It needs **no symptomatic driving**. |
| **Operator decision** | **OPEN** — he will decide what to do with V103 after this close-out. Drive card is written and **HELD**. |

---

## 1. THE TWO NEW ROUTES

**`0x96` = V102 (6×) · `0x97` = V9b STOCK.** Settled by **four independent discriminators**, all at
duty 1.0000, with route `0x95` (V101) as a positive control in the same instrument:

| discriminator | `0x96` | `0x97` | `0x95` |
|---|---|---|---|
| `0x14A` byte7[7:6] | 3 (87,615/87,615) | **0** (107,473/107,473) | 3 |
| `0x14A` byte4 alphabet | 12 values, all EVEN ⇒ b3≡0 | **constant `0x07`** ⇒ field ≡ 0, no cave | all ODD ⇒ b3≡1 |
| LKAS authority 20–65 km/h | \|cmd\| p50 **169**, rail 0.0123, 0 state-4 | \|cmd\| p50 **856**, rail 0.1376, **382 state-4** | p50 214 |
| `carParams.carFw` EPS | `39990-TVA,A160` (COMMA) | `39990-TVA-A160` (HYPHEN) | comma |

⭐ The part-number leg is **orthogonal to every cave bit** — it comes from the UDS version query at
ignition, and every modded build since V18 flips `0x13109`/`0x14120` `-`(0x2D)→`,`(0x2C).
🛑 **`0x1AB` is NOT a discriminator** — full-route, stock and V102 overlap (165 vs 127 distinct codes).
An early claim that it was came from a single parked segment and was **withdrawn**.

**Exposure.** `0x96`: 87,614 frames, **576.3 s engaged in 8 episodes**, v p50 59.5 km/h, hands-light
0.845, fault-free. `0x97`: **688.8 s engaged in 19 episodes**, p50 72 km/h — **2.8× the best prior
exposure in the corpus** and the first substantially highway-weighted stock arm.
⚠ `0x97`'s `STEER_STATUS`=3 on 35,289 frames is **parked-only** (`0xC62EA` low-speed lockout), not a
limited ECU. **The stock arm is valid.**

**Operator's own words:**
> **V102 (6×):** *"Vibration and grinding somewhere between 4× and 8× torque mods. Ratcheting was bad,
> similar to 4× torque mod."*
> **V9b stock:** *"No vibration or grinding. Maybe ever so slightly, barely perceptible ratcheting."*

**Both reports matched the instrument.** 22–26 Hz speed-matched: V102 = **0.460 of V101** where V100 =
0.123 ⇒ **63 % of the way from 4× to 8× on a log scale.** Ratchet band 7.3–9.3 Hz: **V102 / V100 =
1.053 [0.838, 1.705]** — statistically indistinguishable from 4×.
🛑 **Nothing was fixed and he has called nothing fixed.**

---

## 2. 🛑🛑 THE BIGGEST FACT — `gp-0x6752` = −1

**Every prior trace asserted `+1`, "boot-fixed".** Three memory files say so. **All three inherited an
incomplete writer census the record had itself already flagged as a lower bound**
(`feedback-a-count-is-not-a-physical-fact`: *"the `gp-0x6752` writer census — a disp16 scan is blind to
the 6-byte form ⇒ a lower bound, not a count"*).

**The missed writer is `FUN_00048a40`**, called once per boot-time config record. Its type-`0x54`
handler reads the record's byte +4 and branches:

```
0x48E66  mov 0x1, r10  ; st.b r10,-0x6752,gp   <- payload 0x2C (',')  => +1
0x48E86  mov -0x1,r10  ; st.b r10,-0x6752,gp   <- payload 0xFA (-6)   => -1
```

**The flash config table has exactly two type-`0x54` records:**
```
0x1180:  6c 55 10 54 2c 08 00 00    payload 0x2C -> +1
0x14C0:  a6 71 10 54 fa 08 01 00    payload 0xFA -> -1
```
`FUN_00048a40` advances a persistent cursor (`gp-0x350c`) **by each record's own length byte (0x10)**,
seeded at `0x1000` — so the walk is **strictly ascending, 16 bytes at a time**, both records sit on the
grid, both pass the length gate, and **`0x14C0` > `0x1180` ⇒ last write wins ⇒ −1.**

**VERIFIED THREE INDEPENDENT WAYS [EVIDENCE]:**
1. **Orchestrator**, in Ghidra + Python: the `mov -0x1` store, the table walk, and `FUN_00048a40`'s
   control flow including the cursor advance.
2. **`ratchet-inertia`**, independently and unprompted, reaching the same two records.
3. **On-car**: **V98's `b3` rung = `(gp-0x6752 ≥ 0)`, duty 0.0000 over 17,983 frames / 5 routes** ⇒ the
   cell is *never* non-negative. The kit recorded this on 2026-08-12 and then three files went on
   asserting +1 anyway.

🛑 **The table lives at flash `0x1000–0x15xx`. Every `.rwd` this kit has ever built writes only from
`0x13000` upward. No build could ever have touched it. It has been −1 the whole time.**
⚠ **Residual, not closed:** a checksum failure on any record between `0x1180` and `0x14C0` latches
`gp-0x348c` and aborts the walk, leaving +1. Nothing suggests that happens on a production ECU, but it
is the one path that would flip this.

### 2.1 CONSEQUENCE — the PID sign classification inverts
The polarity multiplies the **entire** `(P+I+D)` combine before it reaches `gp-0x6ad4`:
```c
iVar30 = ((D_state + I_state + P_state) >> 5) * gainD_gated >> 10)
         * (int)*(char *)(gp - 0x6752)                       // ±1 on the WHOLE sum
         * (uint)((int)*(char *)(gp - 0x6752) + 1U < 3);      // validity gate, passes for -1/0/1
```
**Corrected classification at 6–9 Hz: D PUMPS · P and I DAMP · net PID DAMPS.**
🛑 **This is GATE2's ORIGINAL headline, recovered — now resting on a verified value instead of an
assumed one.** It survived **two same-day reversals** (documented in §9) before settling, and was
finally confirmed by an **end-to-end numerical simulation through the real `_band_transfer` formula**
(`P +0.144 damp · I +0.051 damp · D −0.079 pump · net +0.116 damp`), matching hand-derivation to 2–3 dp.

### 2.2 CONSEQUENCE — r24/r26 flips to PUMPING at 6–9 Hz
**Parity came back ODD** — r24 and r26 each multiply `gp-0x6752` exactly once, so the `P² = +1`
cancellation that applies in the Path-1/Path-2 chain **does not apply here**; the value is load-bearing.
⇒ **r24 = −431 to −1294 ct at 6–9 Hz, PUMPING** (G = 1–3). And the corrected band shape **retrodicts the
measurement better than +1 did** — pumping at 6–9 and 9–12 Hz (the two worst measured bands), damping at
12–31 Hz (matching the measured recovery toward the 22–26 Hz crossover).

### 2.3 ⚠ A BUILD WAS GATED ON THIS AND WOULD HAVE BRICKED
`memory/MEMORY.md:182` — **V49**, built and verified, held unflashed with the note *"GATED on polarity
`gp-0x6752` = +1 (**brick if −1**; EEPROM-resident → needs live read)."* **It was never flashed. That
caution was correct and nobody knew why until today.**

---

## 3. ⭐⭐ `f0` — THE NEW ENDPOINT

Sliding a 2 Hz band across 16–36 Hz, engaged hands-off, speed-matched 29–86 km/h:

```
Hz        16  17  18  19  20  21  22  23  24  25  26  27  28
STOCK 1x   N   N   N   N   N   .   .   P   P   P   P   P   P
V100  4x   N   N   N   N   N   N   .   .   P   P   P   P   P
V102  6x   N   N   N   N   N   N   N   N   .   P   P   P   P
```
*(N = 95 % CI entirely below zero · P = entirely above · . = straddles)*

🛑 **The anti-damping is not a notch on the mode. It is a REGION running from ≤16 Hz up to a crossing —
present on EVERY arm including stock — and our gain pushes that crossing UPWARD.**

| arm | gain cal | **f0** | 95 % CI | n |
|---|---|---|---|---|
| **STOCK 1×** | 891 | **21.90 Hz** | [21.08, 23.03] | 102 |
| V100 4× | 3564 | **23.61 Hz** | [23.22, 23.95] | 22 |
| V102 6× | 5346 | **24.90 Hz** | [24.63, 25.26] | 51 |

**All three CIs mutually disjoint. Fit: `f0 ≈ 21.3 + 0.60 × (gain multiple)` — LINEAR in gain.**

### 3.1 WHY THIS ENDPOINT BREAKS THE CONSTRAINT WE HAVE BEEN FIGHTING
The standing law is that a build must be readable from ~15–30 s of **symptomatic** frames.
⭐ **A standing loop property needs no symptom at all.** The **burst-tercile test** proves it:

| arm | LOW burst | MID | HIGH | control 26–31 |
|---|---|---|---|---|
| STOCK | +2 [−186,+166] | +180 | **+335** | +544 → +1060 |
| **V102** | **−191 [−308,−21]** | −94 | **−205 [−237,−139]** | +44 → +380 |

**V102 is anti-damped in EVERY tercile with no trend; stock is damped in every tercile and gets MORE
damped as bursts grow.** The control band rises monotonically on all three arms, so the conditioning
works. ⇒ **The negative margin is STANDING. Only the EXCITATION is intermittent.**
⇒ **He drives normally for ~2 minutes. He does not have to reproduce grinding.**

### 3.2 POWER — measured on NON-OVERLAPPING windows, not asserted
The frozen estimator runs 50 % overlap, so a naive bootstrap understates the CI. All figures below use
non-overlapping 5.12 s windows and are therefore conservative.

| engaged hands-off s, 30–85 km/h | CI width on f0 (V102-like) | P(resolve sign) at stock | at V102 |
|---|---|---|---|---|
| 41 s | 1.85 Hz | 0.21 | 0.65 |
| 61 s | 1.42 Hz | 0.82 | 0.97 |
| **81 s** | **1.18 Hz** | **0.94** | 1.00 |
| **101 s** | **1.04 Hz** | **1.00** | 1.00 |

🛑 **REQUIRE ≥80 s, TARGET ~100 s.** 41 s licenses nothing. **Both existing routes already clear it
without trying** (stock 268 s, V102 152 s). **The binding constraint is HANDS-OFF, not duration** —
V102 was 5.4 % hands-on, stock 14.4 %, both fine; **V101 at 39.9 % would have been marginal.**
🛑 **Above ~85 km/h does NOT count** — at 86–115 km/h stock (+104 [−198,+426]) and V102 (+80 [−60,+155])
both straddle zero. **A 60–80 km/h arterial is ideal; a motorway cruise is the worst case despite
feeling like the most data.**

### 3.3 🛑 DOSE FLOOR — and why V103's biquad is predicted below it
**~1.0 Hz of f0 is resolvable in one drive. The V102→stock gap is 3.00 Hz.** Conversion, derived from
the arms' own f0 and band-average `Re(Z)`: **~153 ct·s/rad per Hz of f0** ⇒ **a lever needs ~230
ct·s/rad to clear 1.5 Hz.** On the linear law, **1 Hz of f0 ≈ 1.7× of LKAS gain.**
⇒ **A lever expected to move f0 by 0.3–0.5 Hz is not worth flying on one drive.** This is the *"write
the sentence a null will license"* gate, answered as a **dose floor**, not just an exposure floor.

### 3.4 CONTROLS — pre-declared
🛑 **Use 31–35 Hz as the negative control, NOT 26–31 Hz.** 26–31 tracks the dose (stock +1061 → V100
+790 → V102 +376, a 2.8× march) so it is not invariant. **31–35 barely moves: +1167 / +1159 / +908.**
Carry **6–9 Hz** as a sign-stable control — strongly negative on every arm; a sign flip there means the
run is wrong, not the car.
**Validity gates:** real coh² at 22–26 **≥ 0.10** (measured 0.288–0.870) · shuffled-pair coh² **< 0.02**
(measured 0.0000–0.0126) · ratio **≥ 5** (measured 23 to 18,000).
🛑 **Run `rlog-tools/studies/impedance/rez_control.py` before scoring.** It pins the whole estimator to **0.00 % on all ten
bands** against `_scratch/logs/v92_rez.log`'s published route-77 table, 221/221 windows. **Every Re(Z) number in this
session depends on that estimator staying frozen.**

### 3.5 BAND CHOICE — `Re(Z)` does NOT need widening
| band | STOCK | V102 | verdict |
|---|---|---|---|
| 21.5–25.5 | +300 | −147 | signs differ |
| **22–26** | **+398** | **−128** | **primary — best coherence (V102 0.870)** |
| 20–28 | +338 | −100 | holds — robustness check |
| 18–30 | +157 [−95,+411] | −95 [−148,+3] | **both CIs touch zero** |
**The SIGN is robust to band choice; the SIGNIFICANCE is not.** `Re(Z)` is a ratio of cross- to
auto-spectrum over the same bins, so it measures the damping of the *band*, not the amplitude of a
*line* — a migrating mode still contributes to numerator and denominator together.
⚠ **Not immune**: if the mode migrated entirely past 28 Hz the band would stop containing it. **Settled
at 6× (mode sits mid-band); LIVE AGAIN at 8×**, where the law puts f0 ≈ 26.1 Hz. Spec:
`docs/specs/SPEC-2026-08-20-band-definition.md`, which keeps **20–28 Hz as the band-RMS primary** on the
migration argument and **22–26 Hz as the `Re(Z)` primary**.

### 3.6 🛑🛑 THE CONFOUND THAT ARRIVED LAST — f0 TRACKS COMMAND AMPLITUDE
**Within V102, at FIXED gain, speed-matched halves: f0 = 25.68 [25.31, 26.62] at low command → 24.69
[24.17, 25.16] at high command. −0.99 Hz over a 2.2× command range, CIs disjoint.** Stratified on
`e4tq` (`0x0E4`), deliberately not driver torque, which would have been circular.

🛑 **And the commands run OPPOSITE to the gains** — openpilot winds up harder on the weaker car:

| arm | median \|0x0E4\| in-band | ct/LSB (`4×gain/32768`) | **LKAS contribution to the sum** |
|---|---|---|---|
| STOCK 1× | **465** | 0.109 | ≈ 51 |
| V100 4× | 253 | 0.435 | ≈ 110 |
| V102 6× | **98** | 0.653 | ≈ 64 |

- Pooled `Re(Z) ~ log|cmd| + log v + log(gain)`: **the gain term is n.s. (+30 [−99, +159]), ΔR² = 0.0009.**
- Out-of-sample: fit on STOCK+V102, predict V100 ⇒ predicted **23.07**, observed **23.61**, miss +0.54.
⇒ **[BELIEF] Most of the f0 march may be command amplitude, not the gain cell.** ~0.5 Hz of residual
survives and may be genuine gain.
⚠ **The same amplitude sensitivity is on STOCK at the same magnitude** (+252 [+90,+426] vs V102's
+211 [+63,+356] per e-fold) ⇒ **it is Honda's, not ours** — consistent with the anti-damping being Honda's.
🛑 **MANDATORY COVARIATE from V103 onward: report median `|0x0E4|` alongside f0, and f0 adjusted for
command. An f0 shift sitting on the amplitude law's own slope (−1.93 Hz per e-fold) is NOT evidence a
lever touched the loop.** Without this, a build is at real risk of a confident wrong answer.
⚠ **[NOT ESTABLISHED] causal direction** — command amplitude is itself caused by the plant's response,
and *"command drives f0"* cannot be separated from *"whatever drives f0 also drives command"* inside a
closed loop. **Per-window Re(Z) is noisy (R² = 0.104)** and the 31–35 control band shows the same
command slope, so a generic amplitude→Re(Z) relation is not excluded.

---

## 4. THE STOCK BASELINE — the first instrumented "what does good look like"

### 4.1 🛑 THE ANTI-DAMPING AT 6–9 Hz IS HONDA'S
Speed-matched, engaged & hands-off & moving, frozen estimator, shuffled controls ≈ 0.000, coh² 0.6–0.8:

| speed | **STOCK** | V100 4× | V102 6× | mod/stock |
|---|---|---|---|---|
| 29–58 km/h | **−1297 [−1805,−989]** | −3376 | −3844 | 2.60× / 2.96× |
| 58–86 km/h | **−1709 [−1937,−1451]** | — | −4089 | 2.39× |
| 86–115 km/h | **−1507 [−1746,−1217]** | −1683 | −1034 | 1.12× / **0.69×** |

**Stock is anti-damped 2–22 Hz at every speed, with the same sign flip to damped at 22–26 Hz.**
⇒ **Honda ships the anti-damping. Our builds multiply it ~2.4–3.0× at 29–86 km/h — and NOT at highway.**
⇒ **The ratchet has a stock floor. It is not purely ours.** What is ours is the SIZE.

### 4.2 ⭐ BUT AT 22–26 Hz WE REVERSE THE SIGN
| 22–26 Hz | STOCK | V102 6× |
|---|---|---|
| 29–58 km/h | **+247 [+82,+457]** damped | **−134 [−189,−11]** ANTI-damped |
| 58–86 km/h | **+496 [+97,+833]** damped | **−99 [−188,−18]** ANTI-damped |
| 86–115 km/h | +104 [−198,+426] | +80 [−60,+155] |
**Non-overlapping CIs at both lower speeds. This is the ONLY band where our firmware changes the SIGN of
the damping rather than its size — and it is the vibration band.** That is why stock has **no line at
all**, not a smaller one.

### 4.3 THE RESONANCE — stock has the 7.4 Hz mode but neither LINE
**Ring-down** (estimator = `studies/damping-q/qd_final.py` verbatim; envelope = `scipy.signal.hilbert`, **not** the broken
`band_envelope`): **STOCK f0 = 7.42 Hz, ζ = 0.0275–0.0321, Q = 15.6–18.2**, pre-edge line **29.8–62.0 ct**
· **V102 f0 = 7.81 Hz, ζ = 0.059–0.072, Q = 7.0–8.5**, pre-edge line **905–996 ct — 16–30× stock's.**
**Positive control PASSES**: injected ζ recovered 0.010→0.0110, 0.020→0.0203, 0.040→0.0405; log-log
**r = +0.970, slope +1.107**. Trust it for **Q ≈ 10–50 only** (biased high at ζ = 0.005 and 0.080).
🛑 **n = 1 usable ring-down per arm** — only 8 raw `latActive` falling edges exist on the whole 18-segment
route (4 at standstill, 3 re-engage inside the post window). **Census limit, not estimator failure.**
⇒ **[EVIDENCE]** stock carries a 7.4 Hz mode inside the record's 14–29 Q range.
⇒ **[BELIEF, n=1 per arm]** our builds do not lower its Q; **they drive it 16–30× harder.**

**Spectra, matched speed, tyre orders 1–6 vetoed.** 🛑 **The absolute peak in every stock highway
spectrum is a TYRE ORDER** (9.57 Hz @70–80, 12.30 @90–100, 14.94 @110–120 km/h — it tracks speed exactly).
Per-1-Hz `tq` band-RMS ratio to stock at 100–110 km/h:
`2:2 3:2 4:4 5:4 6:8 7:20 8:16 9:7 10:3 11:1 12:1 … 22:10 23:17 **24:50** 25:23 26:7 … 49:3`
⇒ ⭐ **EXACTLY TWO EXCESSES OVER STOCK — 7–8 Hz and 23–25 Hz — on a flat 2–5× background.** His two
symptoms, and nothing else.
**Negative control passes:** at matched 65–115 km/h stock's 18–28 Hz argmax has **prominence 2.31** with
a CI spanning the whole search band (a wandering noise argmax) against **V102's 75.73 at 24.61 Hz.**
**Two agents, two independent estimators (argmax-prominence and band-RMS-with-order-veto), same conclusion.**

### 4.4 ABSOLUTE LEVELS — "what eliminated means as a number"
`tq` band-RMS, counts, engaged, per speed bin (⚠ pooled over wheel rate; the rate-matched table is the
rigorous one):

| band | v km/h | STOCK | V100 4× | V101 8× | V102 6× |
|---|---|---|---|---|---|
| **6–9** | 50–65 | **22.0** | 208.0 | 743.5 | 25.6 |
| | 85–115 | **8.2** | 13.3 | — | 91.9 |
| **22–26** | 50–65 | **6.2** | 30.5 | 362.3 | 9.0 |
| | 85–115 | **5.3** | 6.1 | — | 112.6 |
| 32–38 (ctrl) | 50–65 | **3.1** | 14.7 | 27.6 | 4.8 |
**Stock's whole 2–50 Hz engaged spectrum sits at 3–15 counts outside the 10–15 Hz road band.**

### 4.5 🛑 HANDS-ON IS A THIRD MATCHING AXIS — and it halved this session's own ratios
Speed × wheel-rate matching does **not** control for hands-on, and the arms differ a lot: **stock 15.3 %,
V100 12.9 %, V101 40.3 %, V102 4.7 %.** Hands-on windows carry **~2.7×** the 6–9 Hz content (stock 30.2 ct
vs 11.1 ct hands-off).

| band | V100: reported → **corrected** | V102: reported → **corrected** |
|---|---|---|
| 6–9 | 1.82× → **1.45× [1.09,1.75]** | 1.75× → **1.20× [0.94,1.69]** ← CI contains 1 |
| 18–22 | 1.76× → **1.12×** n.s. | 2.49× → **1.55× [1.11,2.06]** |
| 22–26 | 1.58× → **1.05×** n.s. | 2.94× → **1.56× [1.01,2.37]** |
| **32–38 (control)** | 1.29× → **1.06×** | 1.30× → **1.04×** |
🛑 **The control collapsing to ~1.05 is the tell** — the old numbers carried a broadband offset, not a
band effect. **V102 keeps a genuine band-selective 18–26 Hz excess of ~1.55×, not ~2.9×. V100 (4×) is
statistically indistinguishable from STOCK in every band except 6–9 Hz.**
✅ **`Re(Z)` is UNAFFECTED** — its frozen mask enforces `~press` at the *frame* level, stricter than any
window-fraction rule. **The three-axis rule binds on band-RMS endpoints, which is where the damage was.**
🛑 **V101 CANNOT be placed on the matched grid at all** — 2 pure hands-off and 3 pure hands-on windows of
103; `press` toggles within nearly every window. **Any V101 arm on a matched comparison is unusable, and
every V101 contrast in this kit's record inherits that unpriced.** V101's engaged `|driver torque|` p50
is **931** against 147–174 on every other route.

**Cell definition, so it cannot be re-inflated by matching on two axes:**
```
speed bin : v_rear*3.6 median -> [5,20) [20,35) [35,50) [50,65) [65,85) [85,115) km/h
rate bin  : median |rate_c|   -> [0,1) [1,13) [13,50) [50,200) deg/s
hands     : press_frac < 0.02 => HANDS-OFF ; > 0.98 => HANDS-ON ; else DISCARD THE WINDOW
cell = speed x rate x hands ; n >= 5 in BOTH arms ; min(n)-weighted geometric mean of per-cell
       log ratios ; bootstrap over EPISODES, never windows
```

---

## 5. V103 — BUILT, VERIFIED, **NOT FLASHED**

```
image  df6104bdf8e4fcb69f3379f5b85fb591e4c64e4c33c16f6f9bf29cc88f48f71d   (1,048,576 B)
.rwd   a8e68185ba2b5bb5d1bf7b0f903a397b9c3961594b5e1054cd9bf5bf098e41ed   (986,042 B)
builder analysis-2020accord/builds/v80_v107/build_v103_tva.py
```
**85/85 assertions · 55 bytes in 13 runs, every one attributed · 41 frozen cells confirmed unmoved ·
`[0xC5000,0xC5FFC)` byte-identical to base · both CRC trailers · bit-for-bit reproducible across two
runs · exactly one `.rwd` on disk.**
**ORCHESTRATOR-VERIFIED FROM DISK** — both hashes re-computed, all four Part A edits re-read, all nine
spot-checked frozen cells re-read, cave contents decoded independently.

### 5.1 PART A — arming Honda's dormant biquad, ENGAGED-ONLY. **4 bytes, all in-place.**
| address | V102 | V103 | instruction before → after |
|---|---|---|---|
| `0xC649B` | `00` | `01` | cal — arms the biquad's gate |
| `0x35A06` | `84 4F E7 98` | `84 4F FB 97` | `ld.bu -0x671a[gp],r9` → `ld.bu -0x6806[gp],r9` |
| `0x35A12` | `EC 49` | `E0 49` | `cmp r12,r9` → `cmp r0,r9` |
| `0x35A18` | `E9 37 00 00` | `EA 37 00 00` | `setfnc r6` → `setfne r6` |
⇒ **the arm source moves from the dead oscillation counter to the LKAS engagement flag** (`gp-0x6806`
≡ `latActive` on 150,302/150,327 = 99.983 %).

**What the filter is.** Coefficients byte-verified from stock: `0xC60A8 = −1.5372`, `0xC60AC = 0.63462`,
`0xC60B0 = −1.8808`, `0xC60B4 = 0.81731`.
> **H(z) = 0.81731 · (z² − 1.8808z + 1) / (z² − 1.5372z + 0.63462)**

🛑 **The numerator's zeros lie EXACTLY on the unit circle (|z| = 1.000000) at 55.23 Hz. It is a NOTCH,
not a low-pass** — an early report labelled it a low-pass with a 42.3 Hz corner; the numbers were right
and the label was wrong, and the difference matters because **above the notch the phase goes POSITIVE
(+82.6° at 60 Hz) and the gain RETURNS (−3.01 dB at 100 Hz)**, which a low-pass would not do.
Poles: |z| = 0.79663, **ζ = 0.6497**, damped 42.35 Hz.

| f (Hz) | 3 | 6 | 7.79 | 15 | 20.3 | 21 | 23 | 30 | 42 | 55.2 | 60 | 100 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| dB | −0.02 | −0.09 | −0.15 | −0.59 | −1.16 | **−1.25** | −1.55 | **−3.01** | −8.09 | **−62.9** | −17.9 | −3.01 |
| ° | −4.1 | −8.1 | −10.6 | −20.9 | −28.9 | **−30.0** | −33.2 | **−45.0** | −66.8 | −90.0 | **+82.6** | **+45.0** |

**DC gain = 1.0000344** ⇒ it passes the LKAS command band untouched (−0.02 dB at 3 Hz), so it
**structurally cannot limit dθ/dt** and adds **no low-frequency drag**. Response is **monotone** from DC
to the notch ⇒ **no new resonance.** Both of the operator's forbidden constraints satisfied *by
construction*, not by argument.

**GATES — ALL PASS.**
- **GATE 1** — `gp-0x3814`/`gp-0x3818` (`0xFEDF47EC`/`0xFEDF47E8`) sit inside the `.data` copy range, so
  the boot value is a **flash initialiser, not a BSS zero**: flash `0x89898..0x8989F` reads
  **`00 00 00 00 00 00 00 00`** in stock *and* V102 ⇒ **both floats boot to exactly `0.0f`. No NaN/Inf
  risk.** Footprint clean on **five methods** (disp16, register-indirect, disp23, LE32-literal, xref),
  both accesses inside `FUN_000352b4` itself, **zero literal-table references anywhere in the 1 MB image.**
  ⭐ **This is not claiming RAM from Honda** — Honda already owns, initialises, reads and writes this
  state whenever the path runs. **We change WHEN it runs, not WHERE its state lives.** That is the
  V62/V67 in-place-edit risk class, **not** the V48B RAM-collision class ⇒ **no canary build needed.**
- **GATE 2** — **|H(f)| ≤ 1.000032 everywhere across 0.1–500 Hz** (fine-scanned at 0.1 Hz, max at DC)
  ⇒ **the filter can only REMOVE loop gain, never add it.** Closed-loop margin improves at **every**
  frequency tested (6–9 / 20–30 / 55–150 Hz) and **every** attribution fraction q ∈ [0.10, 1.00],
  including the deliberately extreme q = 1.00. Representative: 21 Hz margin **1.01 → 2.26 dB** at q=1;
  60 Hz 22.74 → 40.59 dB; 150 Hz 39.45 → 40.46 dB.
  ⭐ **This is the structural reason it cannot backfire the way `0xC63AC` did**: `0xC63AC`'s edit
  *removed* a pole and thereby *added* HF gain to its branch (1.08×@7.79 → 1.75×@42 Hz), which is what
  the full-loop sum found dominant. **This one can only subtract.**
- **GATE 3** — the `gp-0x4f60`-based dropout is computed **after** and **independent of** the filter's
  output; it discards the result on rare occasions and **never feeds back into `gp-0x3814`/`gp-0x3818`**.
  The filter's recursion runs through a dropout event untouched.
- **Encoding** — every byte independently derived two ways, cross-checked against real existing
  instructions in the same binary, then re-read from the image. **Three independent verifications**
  (`pole-hunt`, orchestrator, `cave-engineer`).

🛑🛑 **THE HONEST MAGNITUDE STATEMENT — this is a partial mitigation, not a fix.**
**At q = 1.00 (the extreme stress case) the predicted correction is ~+50 ct·s/rad against the −488
ct·s/rad gap between V102 and stock ⇒ ~10 % of the way back, landing still anti-damped (~−67). At
realistic q = 0.10–0.25 (`gp-0x6b86` is one of ~9–10 aggregator lanes) it is +2 to +13 ct·s/rad —
negligible.** In `f0` terms: **0.06–0.3 Hz against a ~1.0 Hz detection floor.**
⇒ **V103 is PREDICTED, IN ADVANCE, TO READ "NO CHANGE" ON ITS OWN PRIMARY ENDPOINT.** Four gate PASSes
mean **safe**, not **sufficient**.

**Stated assumptions, kept rather than assumed away:** (1) the +90° carrier rotation, cited from
`studies/models/eps_loop_gain_model.py`'s own docstring; (2) gain scaling |L| uniformly with fixed phase shape (the
anchor's premise — **and see §7.2, this is now doubted**); (3) the `Re(L)→Re(Z)` constant assumed
uniform regardless of which branch contributes; (4) 🛑 **the UNARMED branch's own phase above ~30 Hz is
uncharacterised** — if it currently provides net phase-cancellation, shrinking it could remove some.
Nothing in the record suggests this (the lane's unarmed content is an unfiltered torque-derived carrier,
the class the anchor script itself calls destabilising) **but it is not proven absent.**

### 5.2 🛑 WHY THE ONE-BYTE VERSION WOULD HAVE BEEN INERT — and what the record got wrong
`STATE.md` kills `0xC649B` with *"forcing input gated on `gp-0x6b62 ≠ 0`, measured duty 0.0000 over
75,227 engaged frames."*
🛑 **That reason is a MISATTRIBUTION — a decompiler variable-name collision.** In `FUN_000352b4`,
`gp-0x6b62` computes a *different* boolean (the IIR coefficient selector choosing between cal `0xC6382`
= 41 and a LERP output); the biquad's forcing input is gated by an **earlier, different** `bVar3`
(`uVar25 < uVar18`). **Same class as the `0xC6194`/`0xC6196` error already on record.**
🛑 **BUT THE VERDICT WAS ACCIDENTALLY RIGHT.** The biquad's real arm is `cal(0xC649B) == 1 AND
cal(0xC64FA) ≤ gp-0x671a`, and **`gp-0x671a ≥ 5` has NEVER been observed true in this kit — 0 across
255,292 engaged frames on three builds** (V64 0/14,980 · V67 0/186,321 · V68 0/53,991, the last
including a 1,468-count 28 Hz lane-change burst). ⇒ **`0xC649B` 0→1 alone is INERT and would have flown
as another V64-class dead-gate null.**
🛑 **AND THE OBVIOUS FIX IS A TRAP.** Setting `0xC64FA` = 0 makes the unsigned comparison always true —
but that displacement (`ld.bu` enc = `0x74FB`) has **18 in-code readers** including `FUN_000428d4`'s own
latch CEIL and the r24/r26 rate-lane arms. **It is the SHARED oscillation-detector ceiling.** The
in-place `cmp` patch at `0x35A12` is **private to this one site**, which is why the build takes it.
**`0xC64FA` is asserted unchanged at 5 in the FROZEN set, to self-document that choice.**

### 5.3 PART B — the comparator probe. **Exactly ONE rung changes from V102.**
| bit | source | note |
|---|---|---|
| b7 | `gp-0x6b4c < 0` | **byte-identical to V102** — wiring control, expect duty ≈0.27 rising 0.148→0.417 with rate |
| b6 | `\|gp-0x6ada\| ≥ \|gp-0x6adc\|` | **byte-identical** — expect 0.8991, rising 0.836 → 0.981 → 0.992 |
| b5 | `\|gp-0x6ae2\| ≥ \|gp-0x6b26\|` | **byte-identical** — expect 0.2481 |
| b4 | `gp-0x6ada < 0` | **byte-identical** — expect 0.4091 |
| **b3** | **`sign(gp-0x3680) < 0`** | **THE ONLY CHANGE — D_state's delivered sign** |
Cave **154 → 164 B** (+10 B). `ld.w -0x3680[gp],r6` = `24 37 81 c9`, derived from two real Honda examples
and confirmed through Ghidra's decoder **on a throwaway scratch import**, not the shared project.
`add 0x8,r7` = `483a` reused verbatim from PASS 3's own existing pre-shift. PASS 1's mask `0xB7`→`0xBF`
(stops forcing b3). `gp-0x3680` GATE 1: **exactly 2 gp-relative accesses image-wide** (1R/1W inside
`FUN_0003a382`), zero literal-table references.

🛑🛑 **IDENTITY IS MULTI-FRAME, NOT SINGLE-FRAME. V103 is the first build since V85 without a
single-frame witness, and the scorer MUST be told.**
**Both axes are numerically exhausted**: `byte7[7:6]` has all four codes allocated (0 = ≤V91, 1 = V96/97,
2 = V98–V100, 3 = V101/V102), and **`b3`'s two states are spent by V101 (constant 1) and V102 (constant
0).**
⇒ **V103's identity is that `b3` VARIES.** No predecessor's does. **A constant `b3` means either the
build is not V103 or the D rung is dead — that is RUN-INVALIDATING, not a finding.**
⚠ **Two conventions are now dead: "byte4 is always odd" died at V98; "byte7 + constant b3" dies here.**
Either old rule would misroute V103's telemetry.
⚠ **An earlier arrangement putting D's sign in `b5` was considered and rejected** — V102's `b5` has
measured duty **0.2481**, and if D's sign landed near 0.25 the two builds would have been statistically
indistinguishable on the only leg available. **A coin-flip on which firmware is on the car.**

🛑 **VALIDATION GATE ON `b3`, adopted before any direction call is made from it:** the D-sign channel
must pass the **same validation class** applied to r24 — synthetic phase recovery through the full
sign+decimation chain, an internal-consistency cross-check against a known relationship, and null
controls. ⚠ **The hook is 100 Hz ⇒ Nyquist 50 Hz ⇒ ~4 samples/cycle at 22–26 Hz — thin but not
disqualifying** (a harder case survived, see §6.3). **Fine at 6–9 Hz.** **If that validation cannot be
constructed for `gp-0x3680`'s chain, say so and do NOT make a direction call from a bare duty.**

### 5.4 WHAT V103 ACTUALLY BUYS — stated precisely
1. ⭐ **`b3` — D's delivered sign. Genuinely new; nothing else can produce it.** Three independent
   agents refused to derive it because **every desk method feeds the already-closed-loop `Z_measured`
   back into its own estimate.**
2. **`b6`/`b4` at 6–9 Hz — MORE EXPOSURE to an under-powered measurement, not a new quantity.** Route
   `0x96` can already answer 22–26 Hz (§6.3) but **not** 6–9 Hz (§6.4). ⚠ **And V102's data could not
   substitute anyway, because V103's biquad is exactly what might move the 6–9 Hz phase.**
3. **f0 with its command covariate**, and the amplitude discriminator if the curve item is driven.
4. **The biquad rides free** — safe, gate-clean, predicted below detection, stated in advance.

---

## 6. THE INVESTIGATION — every thread, including the ones that came back negative

### 6.1 🛑 THE OPERATOR'S "DRIVER-SIDE INERTIA FEEDBACK" HYPOTHESIS — refuted in one form, CONFIRMED in another
**`gp-0x6b26` — REFUTED as the pump [EVIDENCE].** It is real and live (`−K(speed)·gp-0x6c2c` via the
`0xCBE74` LERP in `FUN_00036c12`; `gp-0x6c2c` is a double-EMA'd first difference of resolver rate in
`FUN_00041464` ⇒ genuine angular ACCELERATION). But:
- **Wrong sign and too small**: measured on-car at **+518/+565 ct — a small net DAMPER**, ~15–18 % of
  the −3375 pump and pointing the opposite way.
- **Closed on-car in BOTH directions**: raised ×1.5 (V91/V92) **measured inert twice**; lowered
  (V93/V94, to 0.167–0.5×) is **the drive the operator ABORTED** — *"made the stuttering and grinding
  worse, by a lot… vibrated the entire car… not safe to drive."*
- 🛑 **It is MOTOR-side.** `gp-0x6c2c` derives from `gp-0x4f50`, the resolver — the motor side of the
  torsion bar. **The operator said *steering wheel*.** That distinction is what redirected the hunt.
- **`0xC646E`** (the `FUN_0003b8f6` Path-2 inertia term, virgin, 1–6 % of clamp) — same conclusion class,
  dissipative-signed, and raising it is literally "add damping", which is forbidden.

⭐ **r24/r26 — the ACTUAL driver-side candidate [EVIDENCE].** Both are built from **`gp-0x4f62`, a
4-sample difference of the RAW TORQUE SENSOR `gp-0x4f60`** — genuinely driver-side. Structurally live
(the gain-selector mux never resolves to zero; `0xC6440`/`0xC6442`/`0xC6446`/`0xC643E`/`0xC6444`/
`0xC61F6`/`0xC6C42` all byte-identical stock/V101/V102, gate byte `0x3AA96` = `c5` = DEAD on all three —
**"Lever B removed" means the boosted-arm branch is unreachable, not that r24/r26 are zero**). Live at
**3.000× (schedule max) at creep** — his regime. **±0x2000 window EACH at the `gp-0x6b94` summing node,
8× `gp-0x6b26`'s ±0x400.**
⇒ **With `gp-0x6752` = −1 and parity ODD: r24 = −431 to −1294 ct at 6–9 Hz, PUMPING.**

### 6.2 THE MICRO-REGIME CENSUS AND THE BUDGET THAT DOES NOT SUM
Only **THREE** things are live in the engaged micro regime (1–13 °/s): `gp-0x6b26`, **the PID D-term**,
and **the r24/r26 lane**. All three scheduled viscous/base-assist dampers are gated to **exactly zero**
there (FactorC's 35 km/h × FactorE's 12.7 °/s product dead-zone).
🛑 **The `Re(Z)` budget does NOT sum.** Against a measured **−3073 to −4890**: `gp-0x6b26` is **+518/+565
(damper)**, r24 reaches **up to ~38 %** at G=3, r26's magnitude is **unresolved**, and D has **no
calibrated ct conversion**. ⇒ either the census is incomplete, or the source is structural/loop rather
than an additive term. **Reported as an unsolved budget rather than forced into a number.**

### 6.3 ⭐ r24/r26's PHASE AT 22–26 Hz — MEASURED from an EXISTING route, no build
**`arg(csd(b4, rate_c))` at 22–26 Hz = +164.4° [+137.4, +172.9]**, hands-light, speed-matched 30–85 km/h,
coh² 0.0763 = **3.0× floor**, 79 windows / 8 blocks. All-hands arm +158.7° [+155.7,+163.6], **6.2× floor**.
**Why it is trustworthy — the method was validated, not assumed:**
- Hard-limiting preserves phase exactly (Bussgang), but Bussgang covers neither of the real hazards, so
  both were tested: **unfiltered 10:1 decimation** (cave at 100 Hz, `gp-0x6ada` updating at 1 kHz) and
  🛑 **3rd-harmonic aliasing landing IN-BAND** (a 24.7 Hz fundamental's 3rd harmonic at 74 Hz folds to
  22–26 Hz, phase-locked at 1/3 amplitude). **Synthetic phase recovery through the whole chain: bias
  −0.0°, scatter 0.2°.**
- ⭐ **Internal consistency**: `rate_c` is the derivative of `cs_ang`, so the two references must differ
  by exactly **−90°**. Measured **−83.5° — agreement to 6.5°**, which independently proves **no pairing
  or timing error** (a 10 ms slip is ~90° here).
- **Three nulls with coherence**: time-reversed 0.0172, rotated 0.0133, phase-randomised 0.0209, all far
  below the signal's 0.0763.
- ⭐ Used **`rate_c`, not `rate_f`** — because `rate_f` carries **~83° of unmodelled filter phase at
  21.5 Hz** (`rate_c − cs_ang` = +84.3°, the expected +90° for a derivative, while `rate_f` sits 83° off).
  🛑 **`rate_f` must not be used as a phase reference at these frequencies.**
- ⚠ **Stated defect**: the synthetic bottomed out at 48.0 flips/s against the real 39.2, so the control
  validated at a **noisier** operating point than reality — **conservative, not permissive**, but not a
  matched control.
- **`b6` bounds the pair**: r24 dominates r26 on **89.9 %** of engaged frames, rising to **0.992 at
  25–50 °/s** ⇒ **at the rates where the resonance lives r26 contributes ≲1 %**, so this phase is
  effectively the pair's.

🛑 **THE CONVERSION — done by COMPARISON against an anchor, not by applying a convention.**
Applying the frame convention once, twice, or never is this kit's recorded failure mode. So instead:
**`gp-0x6b26` is the anchor** — V96 measured it at **+137°/+139° vs wheel rate**, and that same term is
independently established as **+518/+565 ct of POSITIVE (damped) `Re(Z)`. One object, both quantities,
measured on the car.**
⇒ **r24's ENTIRE CI [137.4°, 172.9°] sits in the same (90°, 270°) arc as the anchor [137°, 139°] — no
flip anywhere in the interval, including at the lower bound. ⇒ r24/r26 DAMPS at 22–26 Hz.**
⇒ 🛑 **Therefore r24/r26 CANNOT be what marches `f0` upward** — if its damping grows with amplitude,
that pushes `f0` DOWN. **OUT as the explanation. Retained as a possible lever with a known sign.**
⚠ **Phase only.** `b4` is a sign, so Bussgang gives phase and destroys amplitude. **Direction, never
magnitude. Do not price a lever off it.**

⚠ **A separate code-derived MAGNITUDE estimate exists and is weaker — treat it accordingly.** Using the
`Z_r24 = G·H_diff(f)·Z_measured(f)` piggyback: **r24 alone at 22–26 Hz = +293 to +880 ct·s/rad DAMPING**,
which **exceeds the ~230 ct·s/rad benchmark even at G = 1.** 🛑 **But it is NOT gain-matched** (route 77
is 4×-era only) **and its author flagged that the method may be structurally unable to distinguish
"r24/r26 CAUSES the `f0` shift" from "r24/r26 passively REFLECTS a shift caused elsewhere", because it
uses the already-closed-loop `Z_measured` as an input.** ⇒ **[BELIEF]. Do not treat it as causal.**

⚠ **AND A REJECTED SUGGESTION WORTH PRESERVING**: a proposal to rescale `G` because torque grew 5.35×
was **checked numerically and declined** — **`Re(Z)` is already amplitude-normalised**, and r24/r26's own
clamps are **only 3–10 % used even at the elevated 8×-era amplitude (931 ct p50)**, so there is no
saturation mechanism to justify a rescale. 🛑 **General rule: do not rescale a fixed transfer gain
because a signal got louder. Check for saturation numerically.**

**Lane magnitudes measured for the Path-2 work [EVIDENCE]:** `gp-0x6b26` at 20–23 Hz **0.259 (r77) /
0.273 (r78)** counts/count ZOH-corrected, SNR **79× / 34×** above the quantisation floor; `gp-0x6bbe`
**0.065**. ⭐ **They are 131.9° apart ⇒ VECTOR sum 0.2275, not the scalar 0.3307 — the second lane
CANCELS 31 %.** The third lane `gp-0x6b46` sits behind a **0.94 Hz EMA ⇒ −27 dB at 21.5 Hz**, so **the
3-lane sum IS the 2-lane sum here.** This took `|Q|` from 0.85–0.92 to **0.73–0.79, back under 1**, and
**corrects an earlier error that assumed the lanes ADD.**

**D's own magnitude/phase at 22–26 Hz, relative to its input [EVIDENCE, closed form]:** `|H_D|` =
**0.276–0.326**, phase **+85.3° to +86.0°** — **2.8–3.3× LARGER than at 6–9 Hz (0.098).** ⚠ **Still not
composed with a velocity phase, which is the missing half (O6).**

### 6.4 🛑 WHY 6–9 Hz CANNOT BE READ FROM ROUTE `0x96` — a prior that was measurably wrong
The orchestrator expected 6–9 Hz to be *easier* (~11 samples/cycle, no 3rd-harmonic fold, and the ratchet
line is the strongest feature in the spectrum). **It is the strongest feature of the CAR. It is not a
strong feature of THIS BIT.** `b4`'s own spectrum vs a shuffled-same-bits white null, 421 windows /
13 blocks:

| band | power/white | 95 % CI | verdict |
|---|---|---|---|
| 2–6 Hz | 0.547 | [0.496,0.605] | **below white** |
| **6–9 Hz** | **1.309** | **[1.059,1.658]** | 🛑 **AMBIGUOUS — straddles the 1.15 gate** |
| 9–12 Hz | 1.452 | [1.242,1.692] | structure |
| **12–18 Hz** | **1.737** | [1.452,2.006] | **strongest** |
| 18–22 Hz | 1.299 | [0.924,1.770] | ambiguous |
| **22–26 Hz** | **2.016** | [1.528,2.485] | ✅ clean — where the answer came from |
| 26–31 Hz | 0.848 | [0.723,0.954] | below white |
| 35–45 Hz | 0.537 | [0.511,0.564] | below white |
**CONTROL A passes at 7.6 Hz** (bias +0.1°, scatter 0.2°) ⇒ **it is not the estimator that fails.**
**CONTROL B is ambiguous, not a clean fail** ⇒ per its own pre-registered rule **no number was quoted**,
because *a phase whose sign decides a build must not travel with "the structure control was ambiguous"
attached.* ⇒ **Route `0x96` answers 22–26 Hz and only 22–26 Hz.**
⭐ **Free observation: `b4`'s structure PEAKS at 12–18 Hz — a band nobody in this fleet is looking at.**

### 6.5 THE PID — a sign-convention trap that produced two same-day reversals
🛑 **`docs/review/GATE2-2026-08-11-cbe74-independent.md` uses a DIFFERENT, self-consistent-but-non-matching sign
convention from the kit's canonical `Re(Z)` tool.** GATE2 defines *"in phase with +velocity = energy
adding"* (the textbook `power = F·v` convention). The canonical
`rlog-tools/probe/decode_v90_probe.py::_band_transfer` defines the **opposite**, and its docstring says so:
*"damper 0°, inertia +90°, spring −90°, negative damping 180°."*
**Settled numerically, not by argument** — synthetic signals through the real formula: `T = +rate` →
`Re(Z) = +1.0` · `T = −rate` → `−1.0` · `T = d(rate)/dt` → `≈0`. **Code matches docstring exactly.**
⇒ **Taking GATE2's LABELS and flipping them via `gp-0x6752` double-counts the convention.** That error
produced a headline of *"P pumps, D damps"* which was **wrong and retracted within the hour.**
**Final, triple-verified: D PUMPS · P and I DAMP · net PID DAMPS at 6–9 Hz.**

**Provenance chase on "D damps 16–35 Hz" [EVIDENCE — it is NOT sourced].**
`STATE.md` §8.2 states it as reconciled. Chased: it traces to a 2026-08-11 memory citing *"a parallel
PID trace"* with **no link and no file**, which **no file in this repo computes**. And **the kit's own
handoff from the same day already supersedes it**: *"The D-term damping crossover is 22–26 Hz, not
~14–16 Hz… Supersedes the 'D damps 16–35 Hz' line, whose cited 'parallel PID trace' could not be located."*
The closest real candidate, `GATE2` §N1, **explicitly declines to call the grinding bands** — *"NOT
MEASURED… CANNOT ESTABLISH… a blocking gap for a dose decision, not glossed over."*
⇒ 🛑 **D's phase at 18–22 and 26–31 Hz has never been computed by anyone. The "band-split the D-term"
build is NOT well-posed until it is** — you cannot design a filter to "preserve damping at 16–35 Hz"
when nothing establishes what D does there.

**What IS solid about D [EVIDENCE, dual-method, `0x3a798-0x3a8a0`]:** its phase relative to its OWN input
(`err`) is a robust **~90° LEAD (83.7° → 89.6°) across 2–35 Hz, monotonic, no reversal.** The `Kd` LERP
(`0xC6AE6/E8/EA/EC`) is **flat 2048 at all four knots — N=0/102, fully virgin.**
**P's useful property**: pure static gain, **0° own-phase at every frequency** (unity-alpha EMA, same-tick
read/write, no delay register) ⇒ its pump/damp call inherits the measured phase **directly**, with no
second transfer function stacked on a proxy. **The most reliably classifiable of the three terms.**
⚠ **Magnitude refused, deliberately.** No calibrated ct conversion exists, and **`gp-0x6b26`'s isolated
code-domain phase was wrong by ~227° once the loop closed.** A code-derived magnitude was not
manufactured.

### 6.6 THE OPERATOR'S RESOLUTION IDEA — closed on BOTH sides of the wire
His question: *"maybe we can modify the firmware to accept larger values so that openpilot can order the
demand of torque more finely."*
**The firmware already accepts everything [EVIDENCE, instruction-level].** `FUN_00021724` returns a
16-bit `CONCAT11`; `FUN_00052676` at `0x526cc` does **`sxh r6` — sign-extended full int16, no masking
anywhere.** Then:
```
0x526ce  movea -0x4000,r0,r7   ; clamp lo = -16384   <- CODE LITERAL
0x526d2  shl 0x2,r6            ; x4                   <- CODE LITERAL
0x526d4  subr r0,r6            ; negate  => raw x -4
0x526d6  movea 0x4000,r0,r8    ; clamp hi = +16384   <- CODE LITERAL
0x526da  jarl 0x49a90,lp       ; clamp(raw*-4, ±16384)
0x526f2  st.h r10,-0x69ae,gp   ; gp-0x69ae = lkas_setpoint
```
**`4096 × 4 = 16384` exactly** ⇒ **the firmware's own wall is numerically MATCHED to openpilot's ceiling.**
🛑 **Information-theoretic result, not a guess:** `arb_command` is a **linear, one-to-one** function of
the raw wire code, so **the number of distinct deliverable outputs is capped by the number of distinct
codes openpilot TRANSMITS.** No re-split of the multiply between the code literal and the gain cell can
increase that count. ⇒ **Widening the firmware's acceptance alone is a NULL OPERATION for resolution.**

| gain cal | mult | counts of `arb_command` per wire LSB | build |
|---|---|---|---|
| 891 | 1× | 0.109 | stock |
| 3564 | 4× | 0.435 | V38–V100 |
| 5346 | 6× | 0.653 | V102 |
| 7128 | 8× | 0.871 | V101 |
| 8192 | 9.19× | **1.000 — LSB parity** | not built |
⇒ **No build has crossed 1 output-count per wire LSB. The felt "coarseness" is the RELATIVE slope, not
integer collapse.**

**Where ±4096 comes from [EVIDENCE, primary source]:** **`CarControllerParams.STEER_MAX` =
`CP.lateralParams.torqueBP[-1]`, set in openpilot's `interface.py:114-115`** as
`[[0, 4096], [0, 4096]]`. **NOT the DBC** — `BO_ 228 STEERING_CONTROL` declares `7|16@0-` and the
`[-4096|4096]` is a **metadata annotation of valid range, not a bit-width restriction.** **NOT the
firmware.**
⭐ **Existence proof it is a free choice: `CAR.HONDA_ODYSSEY_TWN`, same codebase, same `_bosch_2018.dbc`,
runs `[[0, 32767], [0, 32767]]`** — and unlike the Accord's entry it carries no *"TODO: determine if
there is a dead zone at the top end"* comment.
⇒ **The quantified both-sides-move fix**: if openpilot used ±32760 and the firmware's scale shrank
`shl 0x2` → `sar 0x1` at `0x526d2`, resolution returns to **0.109 counts/new-wire-LSB — stock-grade —
while still delivering 8× peak authority.** ⚠ **Requires an openpilot change, which the standing rule
forbids. Reported as a FINDING, not proposed as a build. The operator has been asked and has not ruled.**
**Firmware-only fallback**: replace the flat gain multiply with a **LERP-shaped curve keyed on
`|setpoint|`** — gentle near zero, steep only near the top. Does not beat the bound; **reallocates**
where the coarseness falls. `FUN_00028ea6` already contains an inline LERP evaluator as a template.

🛑 **AND THE WIRE IS DENSE — quantisation is closed on the sender side too [EVIDENCE].** Raw `0x0E4`
histogram from `src == 129` (openpilot's own TX), engaged:

| route | build | distinct codes | **GCD of non-zero codes** | occupancy | rail duty ≥4096 |
|---|---|---|---|---|---|
| `0x96` | V102 6× | 4,139 | **1** | 50.5 % | 0.0148 |
| `0x97` | STOCK | **6,464** | **1** | **78.9 %** | 0.0701 |
| `0x95` | V101 8× | 3,883 | **1** | 47.4 % | 0.1197 |
| `0x85` | V100 4× | 5,022 | **1** | 61.3 % | 0.1227 |
**GCD = 1 on all four ⇒ contiguous integers, no coarse lattice, 1-LSB resolution available and used.**
And the **frame-to-frame steps are ~22 LSB at the median** (`|Δ|` p50 = 22 on V102, 9 on stock; **≥4 LSB
on 81 %** of frames; hard max 123 = openpilot's own per-frame rate limit).
⇒ 🛑 **The controller never asks for a step as fine as 1 LSB. A finer wire would change nothing.**
⇒ **The quantisation explanation for his "coarseness" is CLOSED on both sides.** **[BELIEF]** what he
feels as coarse is the ~23 Hz vibration, not resolution.
⚠ **CORRECTION TO THE RECORD**: `STATE.md`'s *"openpilot's ±4096 rail, ~12 % duty on BOTH builds"* is
right for V100 (0.1227) and V101 (0.1197) but **does NOT generalise** — `0x96` rails at **0.0148**, stock
at 0.0701. 🛑 **Do not read rail duty as a gain law** — it is dominated by route content and driver
behaviour (V101 was 39.9 % hands-on with `|driver torque|` p50 931).

### 6.7 THE `gp-0x6b30` / CORRIDOR DISSENT — raised, then RETRACTED by dataflow
A dissent was raised that a **corridor/soft-EME term is added to the wire-derived setpoint BEFORE the
same gain multiply** (`0x2a1fc add r9,r11` then `0x2a1fe mul r13,r11,r0`), so "widening the input" would
leave that term's gain untouched.
🛑 **RETRACTED on its central premise.** Ghidra's PCode dataflow (`analyze_dataflow`, forward, seeded at
the actual wire read `0x29032 ld.h -0x69ae[gp],r13`) traces the value **hop by hop through 15 real
operations** into the exact clamp (`0x2a13e ld.hu 0x71be[tp],r9`, cal `0xC61BE`) that feeds
`gp-0x6b30`'s IIR. **The wire genuinely reaches `gp-0x6b30`'s computation.**
**What survives, minor:** the chain is not a flat pass-through — it runs through a **1-pole IIR (state
`gp-0x3d3c`, coefficients `0xC63EC`/`0xC63EE` — the same pair the record calls the "command low-pass")**
and several mode/LERP blends. **That is shaping, not independence.**
⚠ **The `0xC63EC`/`0xC63EE` IIR's pole has only ever been characterised at 6–9 Hz. Whether it sits
anywhere near 22–26 Hz is UNMEASURED** — see §8.
✅ **And V57 already closed the 22 Hz sign-latch question** it originally rested on:
`docs/HANDOFF-2026-07-30-v57…` — *"bit4 is identically zero across all 1,581 applying frames ⇒ no
chattering relay at any frequency"*, and the parity hole is closed (all 9 bit6-vs-bus disagreements sit
exactly on `STEER_CONTROL_ACTIVE` transitions ⇒ one-frame skew between two 100 Hz mailboxes, not
`gp-0x6806 == 2`; **the flag is strictly {0,1}**).

### 6.8 THE V104 STRUCTURE SEARCH — where a phase filter could live
**Why phase, not magnitude:** `Re(Z) = |Z|·cos(φ)` crosses zero **iff φ = 90°**. **`f0` is a PHASE
boundary.** The biquad is a **magnitude** intervention (|H| ≤ 1 everywhere) and moves `f0` by ~0.1 Hz —
its weakness is not evidence about phase-shaping filters.
**q is a PLACEMENT choice, not a structural limit.** `gp-0x6b86` is one of ~9–10 aggregator lanes ⇒
q ≈ 0.10–0.25. **Downstream of the aggregator sum, q = 1.0 by construction — a 4–10× multiplier before
changing anything about the filter.**
**Measured sensitivity [BELIEF, model uncertain to ~2×]:** a pure allpass on the common path,
`L_new = L_old·e^{jφ}`: **−10° → 0.05 Hz · −30° → 0.20 · −60° → 0.51 · −90° → 0.86 Hz**, in the
**correct** direction (f0 down toward stock). ⚠ **A sign error in the Hz conversion (`d(f0) = −d(ReZ)/S`,
the minus was missing) initially made this read as the wrong direction — found and fixed.** Phase LEAD
gives inconsistent, partly-cancelling sign across the band; **lag is the coherent direction.**
⇒ **−90° at q=1 gets 0.86 Hz of the ~3 Hz needed.** ⭐ **An in-band ALLPASS is not capped at −90°** —
order-N delivers up to **N×180°** at unity magnitude, concentrable in 16–26 Hz and invisible to the
0–3 Hz command band.

🛑🛑 **THE MODEL REFIT FAILED — AND THE FAILURE IS INFORMATIVE [EVIDENCE].** Solving the inverse problem
directly — *what flat phase shift at q=1 would exactly retrodict each measured `f0`, with stock as the
φ=0 baseline?* — using the same forward map, no new assumptions:
> **No φ in the full ±180° range works, at either 4× or 6×.** 4× needs `d(ReZ) = −262`; 6× needs `−460`.
> But the **maximum possible swing from rotating a fixed-magnitude carrier through any angle is bounded
> by `2·|L_total(f)|·C`** — about **216 and 173** respectively. **Smaller than what is needed, at the
> most extreme rotation physically available.**
⇒ 🛑 **It is not that the phase assumption is wrong. The calibrated `|L|` itself is too small to reach
the required swing by ANY phase manipulation.** That is a **second, distinct failure** of this model —
the first was a 5–8× magnitude over-prediction — and **a future session must not assume "retune one
parameter" fixes it.**
⇒ **Recommendation carried forward: stop pricing off this theoretical model.** Use `route-stock`'s
directly measured **`Re(Z)`-vs-log(amplitude) slope (+211 to +252 ct per e-fold)** — real data, not a
theory that has now failed twice.

⭐ **THE ALLPASS IS DESIGNED AND COSTED — but its Hz-of-`f0` is DELIBERATELY WITHHELD.**
Standard 2nd-order allpass (complex pole/zero pair, **`|H| = 1` exactly by construction**, verified
numerically). Design point **`fc = 21 Hz, r = 0.90`**:
- **−128.9° to −174.3° across 20–26 Hz** — real in-band authority.
- **0.3–3 Hz command band moves only −1.6° to −16.1°** — minimal cost where he steers.
- **Group delay in the command band ~10–15 ms.** ⚠ Counter-intuitively, **tighter/higher-`r` designs give
  LOWER low-band delay** — a real trade-off, not obvious ahead of time.
- **Cost: 2 states/section, ~0.06 % of a 1 kHz tick; a 2-section cascade for ~360° roughly doubles it.**
  Cycle-cheap either way. **GATE 1 needs 4 states of verified-free RAM, not yet matched to specific cells.**
🛑 **No Hz number was produced, on purpose**: *"my loop model has now failed twice and doesn't deserve to
price anything yet."* **The filter is real, cheap and well-specified, waiting on a trustworthy way to
size its dose. See O2/O3.**

**Site survey [EVIDENCE, `FUN_0002214a`'s actual jarl sequence, 98 calls, no branches in the region]:**
```
0x2291e  jarl FUN_0003aa2c   aggregator: writes gp-0x6b94, gp-0x6ada, gp-0x6adc
0x22926  jarl FUN_000428d4   oscillation DETECTOR
0x2292e  jarl FUN_00044cf0   unidentified, not traced
0x2293a  jarl FUN_0004503c   GOVERNOR: reads gp-0x6b94, writes gp-0x6ace
0x22978  jarl FUN_0004595a   unidentified, reads gp-0x6ace
0x22984  jarl FUN_000456a4   COMP-ADD: reads gp-0x6ace, writes gp-0x6acc
0x229c2  jarl FUN_00045a20   oscillation monitor: reads gp-0x6ace AND gp-0x6acc
0x229ce  jarl FUN_00042af8   reads gp-0x6acc, writes gp-0x6b08 AND gp-0x6b98 internally
0x22a10  jarl FUN_00043e44   reads gp-0x6acc and gp-0x6b98
```
- 🛑 **`gp-0x6ace` DISQUALIFIED — it is not near V40's edit, it IS V40's function.** `tp+0x7206`/
  `tp+0x7208` (= `0xC6206`/`0xC6208`, V40's exact cells) are read at `0x45410`/`0x45416` **inside
  `FUN_0004503c`**, and `gp-0x6ace` is written 7 times within it before settling.
- 🛑 **`gp-0x6b08` fails the clean-boundary test** — writer `0x43206` and both readers `0x432e6`/`0x43a96`
  are all inside `FUN_00042af8`.
- ⭐⭐ **RECORD DEFECT — there is no separate "integrator."** The chain *"shaper → `gp-0x6b08` →
  integrator → `gp-0x6b98`"* appears in `STATE.md`, in memory and in the golden model and reads as
  separate stages. **It is ONE function** — `FUN_00042af8` (~1769 instructions) owns all of it, with
  `gp-0x6b98`'s live writes at `0x43b52`/`0x43dfc` inside it. The two candidate "integrator" functions
  (`FUN_0006e09a`, `FUN_0006e140`) have **zero callers image-wide.** ⚠ Indirect calls not chased ⇒
  *"not confirmed live"*, **not** *"dead."*
- ✅ **`gp-0x6b94` and `gp-0x6acc` are the only clean-boundary candidates.** Both **always-on** (no
  `gp-0x6806` anywhere in governor/comp-add/monitors) ⇒ both need their own gate if LKAS-only is wanted.
- 🛑🛑 **AND THE DECIDING QUESTION IS UNANSWERED: `gp-0x6acc` IS READ BY `FUN_00045a20`**, established
  earlier as a **same-cycle lockstep VALUE comparator** against a shadow (`gp-0x6acc` vs `gp-0x4cc8`),
  feeding the hard-shutdown path. **A filter inserted between comp-add's write and that read changes
  `gp-0x6acc` but NOT its shadow ⇒ the monitor trips on the first tick.** See §8.

**r24/r26 as an insertion site — envelope traced, and it ranks LAST:**
- **Memoryless confirmed**: both derive from `r1 = clamp(gp-0x4f62, ±0x1400)` at `0x3aaac-0x3aac0`; r26
  through a piecewise-LERP on `gp-0x6ac0` then cal-gain + `sar 0xa`; r24 through cal-gain + `sar 0xa`
  then a fixed-step slew clamp against `tp+0x71f6`. **No IIR, no delay line, no state — matches "no break
  frequency below 125 Hz."** ⇒ **an empty socket: a cave would install the FIRST phase element there.**
- 🛑 **NOT engaged-gated** — zero `gp-0x6806` references in `FUN_0003aa2c`; only internal gate is
  `gp-0x67ac`, a railed-boolean mode selector; caller admits states {4,5,10,11}. **Always-on cluster =
  the V48B exposure class.**
- 🛑 **The free telemetry mirrors are TOO LATE to inject** — `0x3ad4e`/`0x3ad5a` store **after** the
  values are consumed by the sum at `0x3acc8`.
- 🛑 **An intercept must land in a ~112 B / ~35-instruction register-resident window** ⇒ **the first
  mid-function cave in this kit's history**, in a body using nearly every GPR. **V24, V27 and V48B are
  the entire brick history and all three were caves.**
⇒ **Loses on q, on exposure, and on hook risk. Its only advantage is its ±0x2000 window, which is
lane-limited anyway.**

**The GOVERNOR describing-function hypothesis — proposed, tested, and PROBABLY DEAD:**
The governor (`FUN_0004503c`) is a **nonlinear slew-rate limiter** whose *"phase contribution is
amplitude-dependent — lags only when the signal outruns its step."* **A slew limiter's describing
function has phase lag growing with the amplitude-to-slew-step ratio**, which would predict `f0` marching
**linearly** with gain. Attractive, and on the common path at q=1.
**Tested by direct time-domain simulation of the actual discrete limiter:** at the fast step (512/tick,
below ~16.6 km/h) lag stays **under 1° up to ~3000–4000 counts**; at the slow step (205/tick) **onset is
~1500–2000 counts**. `|gp-0x6b94|` peaks at **2,188 on V101** — genuinely at the knee.
⚠ **But the sweep assumed command scaling proportionally with gain, and the measured law is the
opposite** (§3.6). Corrected: **the LKAS contribution is ~51 / 110 / 64 counts at 1× / 4× / 6× — 2–5 % of
a `gp-0x6b94` dominated by base assist — and it is NON-MONOTONE while `f0` marches monotonically.**

🛑 **RE-TESTED AT THE MEASURED AMPLITUDES AND NOW DECISIVELY RULED OUT [EVIDENCE].** Re-running the DF
simulation at the measured `command × gain` products (**465 × 1 = 465 · 253 × 4 = 1012 · 98 × 6 = 588** —
non-monotone, peaking at 4×) gives **phase lag < 0.3° at all three.**
⭐ **And the result is SCALE-INVARIANT: sweeping a hypothetical unit-conversion factor K from 1 to 30,
the ordering `465 < 1012 > 588` is preserved under ANY positive scale, because monotonicity is
scale-invariant.** ⇒ **No unit conversion can rescue it. Under `command × gain` as the input proxy, the
governor slew-limiter mechanism CANNOT explain the monotone `f0` law.** This is stronger than the earlier
"flat at an assumed amplitude" finding and it is **no longer a units question.**
⚠ **The one thing this does NOT close: whether `command × gain` is the right proxy for the governor's
real input.** And 🛑 **the orchestrator's supporting LKAS-share arithmetic (the `4×gain/32768` conversion
and the 2–5 % share) was NOT independently verified before close-out** — see O5.

**Comp-add (`FUN_000456a4`) is a static, memoryless nested LERP — zero dynamics, nothing to retune.**

### 6.9 THREADS THAT WERE CLOSED OR SET ASIDE
- ✅ **The assist-shaping task rate is CLOSED — 1 kHz single-rate, zero inter-stage skew.**
  `FUN_0002214a` drives PID + observer + aggregator + shaper, single-caller agreement across four
  functions. It was listed as UNRESOLVED in the record. **A slower shaping task is NOT the answer.**
- ✅ **REQUEST does not echo the LKAS command** — `FUN_00026c80`/`FUN_00025c32`: same 11-iteration loop
  and same per-slot mode gate (`0xC4118`), but **different raw source arrays** (`param_1[8]`, clamp
  ±20000, vs `param_1[4]`, clamp ±0x2800 matching LKAS's own width).
- ⚠ **The `f′` / Path-2 bracket thread**: `iVar6 = MODEL + REQUEST − ACTUAL`; the Stage-2 LERP's local
  slope `f′` falls ~10× as `|iVar6|` grows (2.539 near 0 → 0.248 at 5000 ct, flash-derived, no runtime
  rescale). `|Q|` hands-off computed at **0.73–0.79**, collapsing to ~1.1× hands-on ⇒ **~1.5×→1.1×
  amplification swing**. ⚠ **Initial numbers assumed the two sensor-fed lanes ADD; measured, they are
  132° apart and partially CANCEL** — corrected. 🛑 **And a counter-observation stands unresolved: V101
  was driven at HIGHER median driver torque than V102 yet has the MORE CONTINUOUS line** — the wrong way
  round for a naive "torque suppresses it" reading. **Do not cite the hands-on/off mechanism as settled.**
- ⚠ **The `gp-0x6c2c` EMA-pole retune** (`0xC643C`/`0xC40DC`, both cal-only, both virgin) was
  **considered and deliberately NOT proposed**: `gp-0x6c2c` has **three consumer domains** (FOC motor-model
  float term, the friction lane, and the oscillation detector `FUN_000428d4`), so retuning its poles is a
  3-consumer blast-radius edit, **and lowering the poles pulls the EMA corners toward the 6–9 Hz band
  itself — a real risk of creating the new resonance the operator forbade.** 🛑 **This reasoning must
  survive so nobody re-proposes it.**
- ⚠ **The "band-split the D-term" build was proposed by the orchestrator and is NOT well-posed** — see
  §6.5. It requires D's phase in the grinding bands, which has never been computed.

---

## 7. SEVEN RECORD DEFECTS CORRECTED

| # | defect | correction |
|---|---|---|
| 1 | `STATE.md` kills the biquad on *"forcing input gated on `gp-0x6b62`"* | **Misattribution** — decompiler variable-name collision. Real arm is `gp-0x671a ≥ 5`. **Verdict accidentally right** (§5.2). |
| 2 | `STATE.md` §8.2 *"D damps 16–35 Hz"* | **Unsourced** — traces to an unlocatable "parallel PID trace"; **superseded by the same day's own handoff** (§6.5). |
| 3 | Golden model + `STATE.md`: *"shaper → `gp-0x6b08` → integrator → `gp-0x6b98`"* | **It is ONE function**, `FUN_00042af8`. The two candidate integrator functions have **zero callers** (§6.8). |
| 4 | Three memories assert `gp-0x6752` = +1 "boot-fixed" | **Measured −1, three ways** (§2). All three inherited a census the record had itself flagged as a lower bound. |
| 5 | `score/score_v102.py`'s `PREREG` key `v101_over_v100 = 5.07` | **Holds an ABSOLUTE, not a ratio.** V101's absolute is 4.2–5.07 depending on window; true V101/V100 is **7.2–8.2×**. **No value is wrong — the key NAME is a misnomer.** |
| 6 | `accord-band-envelope-is-rectified-not-analytic` retraction | **OVER-BROAD.** Measured λ error is only **3.6 %**; envelope **CV** is inflated 22 % (so CV/duty/p50 results ARE corrupted) — **but `studies/damping-q/qd_final.py`/`qd_lib.envelope_stats`, which produced ζ = 0.017–0.036 / Q = 14–29, call `scipy.signal.hilbert`, NOT `band_envelope`.** ⇒ **the ring-down ζ/Q result was NEVER at risk and should be un-retracted.** |
| 7 | `.claude/agent-memory/firmware-codepath-tracer/MEMORY.md:84` advertised *"free RAM `gp-0x1500`/`gp-0x14e0`"* | **POISON — corrected in place.** `gp-0x1500` **FAILED on-car** (V50P: nonzero 99.47 %) after passing BOTH static methods; `gp-0x14FA` in the same `0xb7260` registry **BRICKED V48B**. The project `memory/MEMORY.md` was clean; **the poison was in the index every firmware tracer loads as its own prior.** |

**Also corrected:** `v102_xb_lib.CH_NYQ` hard-codes `x6b94: 20.0` for the older 41.7 Hz route generation;
**`0x1AB` runs at 49.81 Hz on `0x97` (Nyquist 24.9 Hz)**. Reusing that constant across generations clips
the wrong band. And **`STATE.md`'s "~12 % rail duty on BOTH builds" does not generalise** (§6.6).

---

## 8. 🛑🛑 OPEN ITEMS — with what would close each

### 8.1 BLOCKING THE V104 DESIGN
| # | open item | what would close it |
|---|---|---|
| **O1** | 🛑🛑 **Is there ANY boundary on the common path that is not inside a safety mechanism?** `gp-0x6acc` is read by `FUN_00045a20`, a same-cycle lockstep comparator against shadow `gp-0x4cc8`. **A filter there trips the hard-shutdown monitor on the first tick.** | Decompile `FUN_00045a20` and confirm the shadow pair. Check whether a hook **after** `0x229c2` but **before** `0x229ce` works — and whether `FUN_00043e44` at `0x22a10` is **also** a monitor. Run the same check on `gp-0x6b94`. **If both are shadowed with no clean post-monitor boundary, the common path has NO safe site and V104 must be redirected.** |
| **O2** | 🛑🛑 **THE LOOP MODEL HAS FAILED TWICE, IN TWO DIFFERENT WAYS.** (i) magnitude over-prediction 5–8×; (ii) **the refit shows no φ in ±180° can retrodict either point, because `2·\|L\|·C` (216 / 173) is SMALLER than the required swing (262 / 460).** ⇒ **the gap is `\|L\|` MAGNITUDE, not phase.** **Every number in §6.8 is priced off this model.** | **Do NOT retune one parameter — that will not fix it.** Either build a real multi-term `Re(Z)` decomposition, or (**recommended by its own author**) **abandon this model for pricing** and use `route-stock`'s directly measured **`Re(Z)`-vs-log(amplitude) slope, +211 to +252 ct per e-fold.** ⚠ Fitting a new free parameter to match 3 points is **calibration, not confirmation** — it was deliberately not done. |
| **O3** | **The allpass cascade is DESIGNED and COSTED but its Hz-of-`f0` is DELIBERATELY UNPRICED** — blocked on O2. Design point `fc = 21 Hz, r = 0.90`: **−128.9° to −174.3° across 20–26 Hz**, command band only **−1.6° to −16.1°**, group delay ~10–15 ms, 2 states/section, ~0.06 % of a tick. | Unblock O2 first. Then price in **Hz of f0** at fixed 8×, with **GATE 2 on the whole cascade not per section**, and the 0.3–3 Hz phase check. ⚠ **Counter-intuitive trade-off found: tighter/higher-`r` designs give LOWER low-band group delay.** |
| **O4** | **Register liveness at the surviving common-path boundary.** Not verified for `gp-0x6b94` or `gp-0x6acc`. | A liveness census at those specific `jarl` boundaries. Structurally favourable (each callee has its own prepare/dispose; V48B's own 1 kHz hook needed only r10/r11/r12 saved) but **not asserted clean**. |
| **O5** | ⭐ **The governor is now RULED OUT under the `command × gain` proxy [EVIDENCE] — lag < 0.3° at all three measured amplitudes, and the non-monotone ordering `465 < 1012 > 588` is preserved under ANY positive scale K (swept 1–30), so no unit conversion can rescue it.** **Two things remain open, both narrow:** (a) is `command × gain` the right proxy for the governor's *real* input? (b) 🛑 **the orchestrator's supporting LKAS-share arithmetic was NOT independently verified** — the `d(arb_command)/d(wire_LSB) = 4×gain/32768` conversion, the ≈51/110/64 counts, and the 2–5 %-of-2,188 share. | (a) Trace the governor's actual scalar input. (b) Confirm `gp-0x6b94` is really that input and check the conversion arithmetic. **Fast, and would close the governor thread on evidence rather than on shape.** |

### 8.2 MEASUREMENT / EVIDENCE GAPS
| # | open item | what would close it |
|---|---|---|
| **O6** | 🛑 **D's phase at 22–26 Hz — never computed by anyone.** Gates any defensible band-split. | V103's `b3`, **subject to the §5.3 validation gate**. Or a properly-scoped desk computation that does not feed `Z_measured` back into itself. |
| **O7** | **D's magnitude in ct** — no calibrated conversion; deliberately not derived. | An on-car measurement, not a code-domain estimate (`gp-0x6b26`'s isolated phase was wrong by ~227° once the loop closed). |
| **O8** | **Is Path 2's reference low- or high-bandwidth at 6–9 Hz?** Decides whether the `Z`-piggyback shortcut is even available for D. | Trace the reference's own dynamics. |
| **O9** | 🛑 **The `Re(Z)` budget does not sum** — nothing accounts for −3073…−4890. | r26's magnitude (the extra `>>10`, `gp-0x69a4`'s typical value); G's 1–3× range; D in ct. **Or accept the census is incomplete and hunt outside it.** |
| **O10** | 🛑 **Causal direction between command amplitude and `f0`.** [NOT ESTABLISHED] | **The drive-only discriminator**: within one route, fixed firmware and gain, contrast ~100 s sustained high-command against ~100 s low-command, hands-off, 30–85 km/h. **Folds into V103's own drive at zero extra cost.** |
| **O11** | 🛑 **Engaged-vs-manual 6–9 Hz on STOCK is NOT SCOREABLE** — zero manual windows above 20 km/h; the one matched cell gives 2.16× [0.41, 4.69], contrast +0.305, CI spanning 11×. Decides whether the Coulomb relay is Honda's or ours. | **~3–5 minutes driven MANUALLY, LKAS off, at 50–110 km/h** on any stock drive. Cheapest high-value ask on the table. |
| **O12** | **Stock's own `f0` split reads −0.00 Hz** — underpowered, **not a null** (3.3 Hz CI per half). | More stock hands-off exposure in-band. |
| **O13** | **No band-selective control for the amplitude effect** — the 31–35 control band shows the same command slope. | A control that does not move with command, or acceptance that a generic amplitude→Re(Z) relation is not excluded. |
| **O14** | **The unresolved stock Hann/long residual** (0.56 vs 0.912). Bounded, nothing rests on it. | — |
| **O15** | **`arg(L)` at 20–23 Hz** — the sensor-fed-lane phase referred to torque. Measured only at 7.79 Hz (+43°/+45°). | Cross-spectral phase from flown cave telemetry, or a dedicated probe. |
| **O16** | ⭐ **`b4`'s structure PEAKS at 12–18 Hz (1.737) — nobody is looking at that band.** | A rung, if one is ever spare. |
| **O17** | **The `0xC63EC`/`0xC63EE` IIR's pole has only been characterised at 6–9 Hz.** Whether it sits near 22–26 Hz is unmeasured. | Compute its response in-band. |
| **O18** | **The hands-on/off amplification mechanism vs V101's counter-observation** (higher torque, more continuous line). | A within-build torque contrast — see O10; the same manoeuvre serves both. |

### 8.3 STRUCTURAL / VERIFICATION RESIDUALS
| # | open item | what would close it |
|---|---|---|
| **O19** | **`gp-0x6752` = −1 rests on a walk that a checksum failure between `0x1180` and `0x14C0` would abort**, leaving +1. | Nothing suggests it happens; the on-car V98 measurement independently confirms −1. **Flagged, not chased.** |
| **O20** | **The runtime-computed-base-pointer residual** — no static method in this kit closes "a base loaded at runtime and indexed to a data-dependent offset that lands here." Applies to `gp-0x3814`/`gp-0x3818` as it does to `gp-0x683c`. | Only a live probe. **Judged not worth one given the positive evidence.** |
| **O21** | **V48B's 1 kHz hook at `0x7FEAC` is unverified against a current image** — 54 builds later. | Re-verify if a 1 kHz hook is ever needed. |
| **O22** | **The indirect-call possibility for `gp-0x6b98`'s apparently-dead writers** (`FUN_0006e09a`/`FUN_0006e140`, zero static callers). | An indirect-call/jump-table sweep. **"Not confirmed live" ≠ "dead."** |
| **O23** | **`gp-0x6b2c`'s "permanently zero" claim cannot be settled from static code** — its write is gated by a multi-condition runtime state check. | An on-car measurement, exactly as `gp-0x6806` was settled after four subagents got it wrong from static code. |
| **O24** | **`gp-0x633c`** — REQUEST's raw source array, writer untraced. | Not needed for the ACTUAL-arm mechanism; chase only if REQUEST becomes load-bearing. |
| **O25** | **`FUN_00044cf0` and `FUN_0004595a`** in the 1 kHz chain are unidentified. | Decompile if a common-path insertion proceeds. |
| **O26** | **Whether panda mirrors a TX cap** on `STEER_MAX`. | Check panda safety source; not present in the local checkout. |
| **O27** | **`G` (r24's gain, 1–3× range) never pinned.** | Decode `curve-A`'s mode-indexed LERP at the real operating point (rate + `gp-0x671d`/`r2` flag states), not just its 3.0× schedule ceiling. |
| **O28** | **r26's magnitude unresolved** — extra `>>10` vs r24, and `gp-0x69a4`'s typical (boxcar-smoothed) value is not established. It **shares r24's now-resolved sign, so it ADDS**, but the size is unknown. | Decode `gp-0x69a4`'s typical schedule value. |
| **O29** | **`Z_measured` is not gain-matched** — only route 77 (V90, 4×-era) complex cross-spectrum exists. Blocks precision on both the 6–9 Hz and 22–26 Hz r24 estimates. | Repeat the cross-spectral measurement at stock and 8×. |
| **O30** | **Whether r24/r26's delivered phase shifts with LKAS gain is untested.** | ⭐ **Cheap**: `gp-0x6ada`/`gp-0x6adc` are free telemetry (0 new RAM) — an on-car comparator at two gain levels settles it without a proxy model. |
| **O31** | **GATE 1 and GATE 2 have NOT been run for r24/r26 as a compensator target.** It is a legitimate candidate for the authorised cave but is **not build-ready.** | The same discipline that reversed `0xC63AC`'s isolated-stage ranking, applied before anyone cuts code. |
| **O32** | **Path-2's `arg(L)`/`\|L\|` measured at ONE gain level only** (routes 77/78, ~4×-era) — not gain-matched the way `f0` is. | Repeat at stock and 8×. |
| **O33** | **The 12–16 Hz crossover (GATE2's weak −0.018 flip) is itself unsourced beyond one table** — never independently re-derived. | A second method. |
| **O34** | **Is `byte7[7:6]` = 0 or 1 genuinely spent, or reclaimable for a future build's identity?** Taken as settled this session, not re-litigated. | Check whether pre-V91 codes can be safely reused. |
| **O35** | **`b6`'s expected duty (0.8991) was supplied from `route-v102`, not independently re-derived** by the probe designer. | A second check before it is trusted as a hard wiring-validation number. |
| **O36** | **GATE 1 RAM for a 2–4-state allpass cascade** is not matched to specific verified-free cells. | Match the design against the `FUN_0003b66a` write-only tap shortlist; the canary probe becomes relevant again. |

### 8.4 THE OPERATOR'S DECISIONS — both OPEN
| # | decision |
|---|---|
| **D1** | 🛑 **What to do with V103.** He has said he will decide **after** this close-out. Options as put to him: drive as specced (4 items); trim to item ① only (~2 min ordinary 20–50 mph cruising, hands resting — gets f0 and the probe); or hold pending the allpass pricing. **`docs/scoring/DRIVE-CARD-V103.md` is written and HELD, not shipped.** |
| **D2** | **The openpilot `STEER_MAX` change** (§6.6). It is the only route to stock-grade command resolution at 8× authority, and it requires breaking the standing "no openpilot-side modifications" rule. **Put to him; not ruled on.** |

---

## 9. WARNINGS FOR THE NEXT SESSION — retractions, so nobody re-derives them

🛑 **Seven claims were made and withdrawn during this session. They are listed so a successor does not
resurrect them from a transcript.**

1. **"P is the leading pump, D damps"** — WRONG, retracted within the hour. Caused by taking GATE2's
   labels and flipping them via `gp-0x6752`, **double-counting the convention** (§6.5). **Correct: D
   pumps, P and I damp.** The memory `reference_accord_pterm_is_the_most_reliable_pump_and_needs_no_new_probe_state.md`
   was retracted in place — **its probe DESIGN is still valid; its headline is not.**
2. **"Spectral leakage over the 25.5 Hz band edge explains the estimator fork"** — WITHDRAWN by direct
   measurement (edge effect bounded at **4.9 %**, ~60× too small). **Correct cause: a brick-wall
   band-pass inflates the MEDIAN for bursty narrowband content, and V102 is the burstiest arm by ~20×.**
3. **"The Hann estimator loses 45 % on stock"** — WITHDRAWN; it was one run of four (0.837 / **0.457** /
   0.872 / 1.270) and the 422 s run carries 67 % of the weight. **Correct: ≤ ~10 %.**
4. **"Stock's reference is inflated 1.496× by a steep-spectrum bias"** — WITHDRAWN **before it was acted
   on**. The synthetic case was `1/f³` in *amplitude* = **f⁻⁶ in power**, ~2× steeper than the steepest
   real arm (measured PSD slopes 15–35 Hz: STOCK −2.67, V100 −3.77, V102 −4.94, V101 −4.53). At each
   arm's **actual** slope the bias is **0.984–1.017**. **No stock-referenced number needs changing.**
5. **"The estimator fork is a per-Hz density mismatch"** — WITHDRAWN; the un-normalised Parseval ratio
   **rises** monotonically with bandwidth on all four arms, and a density would have made every arm fall.
6. **"The corridor/soft-EME term is independent of the wire"** — RETRACTED by PCode dataflow (§6.7).
   ⚠ Caused by **Ghidra reusing the C variable name `uVar37`** for both the wire read and a later
   driver-torque-derived value — the exact variable-reuse trap this kit's own feedback memory warns about.
7. **"V101 was driven 88 % hands-on"** — MISLABELLED. That was *87.9 % of engaged windows with median
   `|driver torque|` ≥ 400 ct.* **By `steeringPressed` it is 28.3 % (windows) / 39.9 % (frames).** **The
   confound is real and is better stated with torque anyway: V101's engaged `|driver torque|` p50 is 931
   against 147–174 on every other route.**

**Also carry forward:**
- 🛑 **The `1.496×` episode is the transferable lesson: a number labelled BELIEF still moved two headline
  figures before it was checked. Labelling is not a substitute for checking before a number is reported.**
- 🛑 **`rate_f` must not be used as a phase reference at 20–26 Hz** — ~83° of unmodelled filter phase.
  Use `rate_c` or `cs_ang`.
- 🛑 **`raw14` off-by-one**: safe pairs are `(t, probe)` or `(raw14_t, raw14_b4)`, **never** `(t,
  raw14_b4)`. At 22–26 Hz a 10 ms error is ~90° and would invert an answer.
- 🛑 **Contiguous runs ≥20 s, never concatenation**, for any long-FFT reference — splice leakage inflates
  stock's band reference **1.20×** because stock has the least real content in the band.
- 🛑 **`ld.bu` encodes its displacement as `disp | 1`.** A scan for the exact even displacement returns
  **zero** hits and reads as "no readers." `0xC64FA` scans as `0x74FB`. `st.b`/`ld.b` → exact;
  halfword/word → either.
- 🛑 **Do not author instruction bytes as a hex string of the halfword value** — V90 shipped a
  **big-endian** cave that way. Build as `bytes([hw & 0xFF, hw >> 8])` or copy Ghidra's byte field, and
  **make every validator ASSERT, never print.**
- ⚠ **Three agents independently refused to derive D's sign at 22–26 Hz, each catching that every desk
  method feeds the closed-loop `Z_measured` back into its own estimate. That convergence is itself a
  finding: it is not derivable, it must be measured.**

**Late corrections that arrived at close-out — carry these, they supersede earlier text in this session:**
8. 🛑 **The D-term sign reversed a THIRD time.** Sequence: *D pumps* → *P pumps* → **back to D pumps**.
   The final state is §2.1 and it is triple-verified. ⚠ **Cite
   `reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal.md` for the current PID
   picture — NOT any individual agent message about it, several of which are superseded.**
9. 🛑 **"My per-Hz density hypothesis for the estimator fork" — WITHDRAWN** (the Parseval table killed it:
   the band-RMS ratio *rises* monotonically with bandwidth on all four arms; a density would have fallen).
10. 🛑 **"5.07 is a ratio not an absolute" — WITHDRAWN.** 5.07 and 0.62 are both **absolutes**; only the
    key *name* `v101_over_v100` is a misnomer. **No value in the record is wrong.**
11. 🛑 **"`0x1AB` MOTOR_TORQUE is identically 0 on stock" — WRONG**, and it would fail a genuinely stock
    route. Full-route: stock nonzero **20.8 %**, 165 distinct. **Corrected in `decode/extract_r97.py`.**
12. ⚠ **A cache-hygiene claim was over-stated three times**: *"no write to `_scratch/cache/r97` since the single
    17:01 extraction."* **`r97.npz` is untouched since 17:04:04, but `r97_identity.json` was rewritten at
    17:22:41.** No data file moved; a metadata JSON did. **Nothing reported depends on it — but the claim
    as phrased was wrong.**
13. ⚠ **V100's `f0` power rows beyond n = 13 are NOT achievable exposure** (only 13 non-overlapping
    windows exist); those entries resample with reuse and their widths are optimistic.
14. ⚠ **The V101 endpoint arm rests on 2 matched cells.** Treat its 31× as order-of-magnitude, not a
    measurement.
15. ⚠ **Endpoint values move ~25 % between 1 s and 2.56 s windows, most on V102. ALWAYS state window
    length and band with any endpoint number.**
16. 🛑 **The `~153 ct·s/rad per Hz` conversion is a LOCAL linearisation** around the current 22–26 Hz
    operating region. **Do not extrapolate it to a different band or a large Δf0 without re-checking
    local linearity.**
17. 🛑 **The standing-rule slip worth remembering**: a gain-cal lever on r24/r26 was floated **without
    first grepping `build_v*_tva.py`** — a class CLOSED per `STATE.md` §5 (V61 / V71c / V88). **The rule
    has zero exceptions, including under time pressure.**
18. ⭐ **The transferable methodological lesson of the whole session**: *a sign-convention mismatch between
    two documents computing the "same" phase quantity — each internally consistent and individually
    defensible — produced the wrong answer when one was read against the other's assumed convention.*
    **Always verify a convention against a KNOWN test case run through the ACTUAL code, rather than
    trusting that two labelled tables share a convention because they use similar language.**

---

---

## 9.5 ⭐ THE RECOMMENDED NEXT ACTION — three agents converged on it independently

**Spend one drive, not a build.** Two of the three biggest open questions close with **driving alone, no
flash, no firmware change, on whatever ECU is already in the car**:

1. **~3–5 minutes driven MANUALLY, LKAS off, at 50–110 km/h** ⇒ closes **O11**, and decides whether the
   engagement/Coulomb-relay amplification is **Honda's or ours** — a claim the whole ratchet story rests on.
2. **~100 s sustained HIGH command (long steady curve / off-centre hold) vs ~100 s LOW command straight
   cruise**, both hands-off, 30–85 km/h ⇒ closes **O10**, and decides whether the `f0` march is **the gain
   cell or openpilot winding up.** **Same ECU, same gain, same drive ⇒ the confound is absent by
   construction, and there is no unit-matching or model-shape risk.**

**That is one ~15-minute outing and it retires two items outright.** It also has zero flash risk.

🛑 **WHY IT MATTERS MORE THAN THE BUILD.** If `route-stock`'s finding survives — **the gain term goes
non-significant once command amplitude is controlled (+30 [−99, +159], ΔR² = 0.0009)** — then **most of
the 21.9 → 24.9 Hz march this kit has attributed to `0xC6CD0` for two builds may be openpilot commanding
harder on a weaker car.** That would **reframe the entire post-V100 arc**, and it would mean **a V103 that
changes authority will move `f0` for a reason that has nothing to do with damping.**
⇒ **Cut V104 as a NON-GAIN lever, dosed for ≥1.5 Hz of `f0`, reporting median `|0x0E4|` alongside `f0`
so the amplitude confound is readable rather than silent.**

**And the reference for all of it:** stock is anti-damped from ≤16 Hz to **21.90 Hz**, its whole 2–50 Hz
engaged spectrum outside the road band sits at **3–15 counts**, and the operator calls that *"barely
perceptible ratcheting."* **That is what "eliminated" means as a number.**

---

## 10. ARTIFACTS

**Firmware (`../accord-firmwares`):**
`analysis-2020accord/_v103_V102BASE-BIQUAD.ENGAGED-CAVE.CMP.6ADA.6ADC.6AE2.6B26-SIGN.3680.6B4C.6ADA-ID.B3VARIES_plain_image.bin`
· `flashing-2020accord/rwd/39990-TVA,A160-V103-…-0x13000-0x100000.rwd`

**Kit:** `analysis-2020accord/builds/v80_v107/build_v103_tva.py` · `docs/specs/SPEC-2026-08-20-band-definition.md` ·
`docs/scoring/DRIVE-CARD-V103.md` (**HELD**) · caches `_scratch/cache/r96` (owner: `route-v102`), `_scratch/cache/r97` (owner:
`route-stock`).

**New/promoted `rlog-tools/`:** `studies/impedance/rez_control.py` (🛑 **estimator regression — run before scoring
anything**) · `studies/impedance/rez_crossover.py` · `studies/impedance/rez_band_tracking.py` · `studies/impedance/rez_f0_vs_amplitude.py` ·
`studies/v103-r9e/v103_endpoint_power.py` · `studies/impedance/burst_rez.py` · `studies/estimator-qc/bandref.py` · `studies/estimator-qc/splice.py` · `score/v101_press.py` ·
`studies/estimator-qc/bandedge.py` · `studies/identification/ident_r96_r97.py` · `decode/extract_r96_r97.py` · `decode/extract_r97.py` · `score/score_v102_full.py` ·
`score/score_v102_matched.py` · `score/score_v102_peak_cave.py` · `score/score_v102_ancova.py` ·
`studies/v102-crossbuild/v102_endpoint_reconcile.py` · `studies/v102-crossbuild/v102_leak_audit.py` · `studies/v102-crossbuild/v102_estimator_control.py` ·
`studies/v102-crossbuild/v102_wire_and_427.py` · `studies/v102-crossbuild/v102_lane_phase.py` · `studies/v102-crossbuild/v102_b4_phase_feasibility.py` ·
`studies/v102-crossbuild/v102_b4_phase_ci.py` · `studies/v102-crossbuild/v102_b4_phase_band.py` · `studies/v102-crossbuild/v102_torque_intermittency.py` ·
`studies/stock-baseline/stock_r97_baseline.py` · `studies/stock-baseline/stock_r97_resonance.py` · `studies/impedance/stock_r97_rez_matched.py` ·
`studies/stock-baseline/stock_r97_ringdown.py`
