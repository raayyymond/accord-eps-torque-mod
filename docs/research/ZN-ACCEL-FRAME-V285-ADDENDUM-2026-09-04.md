# ADDENDUM — Ku is 227, not 859: the first instability is a −180° crossing at 27–32 Hz, in the blind band

`zn285`, 2026-09-04, second pass. **Supersedes §3.2/§3.5 of `ZN-ACCEL-FRAME-V285-2026-09-04.md`.**
Triggered by `team-lead`'s retraction and by `CREEP-20HZ-LOOP-ID-2026-09-03.md` item 4, which I had not
been pointed at on the first pass and which I have now verified at source.

Runnable mirror: `analysis-2020accord/studies/zn285/zn_ku_corrected.py` (image sha256 `0ea98d06…`).

---

## A1. 🛑 MY OWN RETRACTION — `Ku = 859` was the wrong quantity

**`Ku = 859` was the Kd at which the 7.3 Hz RING's magnitude reaches unity.** That number stands as
what it is, but it is **not Ku**, because a *different* instability arrives first: a classic Nyquist
−180° crossing at **27–32 Hz**, reached at **Kd ≈ 227**. My first pass searched only at `f0 = 7.3 Hz`,
where the arm split was measured, and therefore could not see it. **`Ku = 227` supersedes `Ku = 859`.**

The two are not in conflict — they are two different modes moving in **opposite** directions in Kd
(§A5). At Kd 227 the 7.3 Hz ring is well damped (`|L|` ≈ 0.79) while the 28 Hz mode is marginal.

**Consequently the ZN constants in §3.5 of the main document are RETRACTED and are UNSTABLE:**
ZN-PI (Kp 108 / Kd 387) has **GM 0.69× (−3.3 dB)**; ZN-PID (Kp 241 / Kd 515) has **GM 0.51× (−5.9 dB)**.
Do not build either.

---

## A2. ✅ Two independent validations of the byte-exact model against item 4 [EVIDENCE]

`CREEP-20HZ-LOOP-ID` item 4's counterfactuals (direct G, Kp 295) are
**Kd 0 → `|L(20)| = 0.37 ∠+157°`** and **Kd 64 → `0.51 ∠−163°`**. Everything in the loop except the
controller is common to both and cancels in the ratio, so this is a direct test of `C(f)`:

| | model (byte-exact `C`) | measured (item 4) | residual |
|---|---|---|---|
| `\|C(20,295,0)\| / \|C(20,295,64)\|` | **0.7314** | 0.37/0.51 = **0.7255** | **+0.8 %** |
| `∠C` change, Kd 64 → 0 | **−39.5°** | +157° vs −163° = **−40.0°** | **0.5°** |

**A second, independent validation — the plant phase.** Decomposing the measured `∠L(20) = +157°`
against the byte-exact `∠C = 0°`, `∠H_lag = −75.8°`, `∠F_b = −50.5°` leaves an implied
**plant phase of −76.7° at 20 Hz**. `CREEP-20HZ` §1.5 **measures** the plant at **−73° at 22 Hz**
(and −28° at 10 Hz) from a completely different route. **Agreement to 3.7°.**

This also settles a convention hazard: **no extra −180° inversion belongs in `L`** — `gp-0x6752 = −1`
is already inside the forward gain. My first pass would have been off by 180° without this check.

The measured plant phase slope 10 → 22 Hz is **−3.75°/Hz**, i.e. a **10.4 ms equivalent transport
delay**. That single number is what carries the loop past −180°.

---

## A3. THE NYQUIST POINT — Ku, properly (`|L| = 1` **and** `∠L = −180°` together)

🛑 **`|L(20 Hz)| = 1` is a CROSSOVER, not Ku.** At Kp = 0 the controller is pure D, so `∠L(20)` is
pinned at **−116.6°** *for every Kd* — a **63° phase margin**. `|L(20)| = 1` occurs at **Kd ≈ 198**
(this is `team-lead`'s 182, recovered exactly), but it happens at 63° of margin and is completely
benign. Ku needs both conditions at once.

| plant model | Kp | Kd | `f(−180°)` | `\|L\|` there | **GAIN MARGIN** | **⇒ Ku (Kd cell)** |
|---|---|---|---|---|---|---|
| **measured slope** | 295 | 128 | **27.4 Hz** | 0.590 | **1.69×** | **217** |
| **measured slope** | **248** | 128 | **28.1 Hz** | 0.564 | **1.77× (5.0 dB)** | **227** |
| **measured slope** | 0 | 128 | **31.7 Hz** | 0.474 | **2.11× (6.5 dB)** | **270** |
| OPTIMISTIC (phase frozen > 20 Hz) | 248 | 128 | 108.3 Hz | 0.148 | 6.76× | 865 |
| OPTIMISTIC (phase frozen > 20 Hz) | 0 | 128 | 125.6 Hz | 0.119 | 8.37× | 1071 |

⭐ **INDEPENDENT CONFIRMATION FROM THE DOC'S OWN MEASURED ROWS.** `CREEP-20HZ` item 4's bar-IV rows
report **`GM 1.75× @ 23.4 Hz` (Kp 295)** and **`GM 1.32× @ 22.4 Hz` (Kp 470)**. My delay-model figure
at Kp 295 is **1.69× @ 27.4 Hz** — the same number, derived from the byte-exact controller plus the
measured plant slope, with no fitting. ⇒ **the gain margin is MEASURED, and Ku = 128 × GM.**

**`Tu` = 1/28.1 Hz = 35.6 ms at Kp 248; 1/31.7 Hz = 31.5 ms at Kp 0.** (The brief's original 49 ms was
much closer than my 137 ms — for the wrong reason, but closer.)

🛑 **The critical frequency, 27–32 Hz, is ABOVE the 427 tap's 25 Hz Nyquist** and at the practical edge
of the 100 Hz streams. **The mode that sets Ku is in the blind band.** That is the single most
important sentence in this addendum.

⚠ **The whole answer bifurcates on the plant above 25 Hz, and nothing on the car can see it.**
Delay model → Ku 227; phase frozen → Ku 865. A **3.8× spread**, and the delay model is both the
physically expected shape and the one that reproduces the doc's own measured GM. I carry **Ku = 227
[217–270] as the working number** and the 865 as an upper bound that requires the plant's phase lag to
simply stop above 20 Hz. [EVIDENCE for the 10–22 Hz slope and the GM at 22–28 Hz; **BELIEF** for the
extrapolation past 25 Hz.]

---

## A4. ZN, re-derived on the correct Ku

`Kd_u = 270` at Kp 0, `f_osc = 31.7 Hz`, `Tu = 31.5 ms`, `Ku' = (270/8)·T = 0.03375 s`:

| form | **`Kd` (`0xE511C`)** | **`Kp` (`0xE5378`)** | `Td` |
|---|---|---|---|
| **ZN classic PID** (0.6Ku, Tu/2, Tu/8) | **162** | **329** | 3.9 ms → 🛑 no cell exists |
| **ZN classic PI** (0.45Ku, Tu/1.2) | **122** | **148** | — |

*(Hunting from Kp 248 instead gives ZN-PID 136/245 and ZN-PI 102/110 — the same neighbourhood.)*

⭐ **ZN-PID's `Kd 162` is candidate F's `Kd 160` to within 1 %.** The loop-shape study's candidate F and
a Ziegler–Nichols tune of the acceleration frame land on the **same Kd**, from completely independent
reasoning. That is the strongest thing in this addendum in F's favour.

**ZN's `Td` still has no home** — §0.2's disassembly is unchanged: one difference operator, one history
cell, three addends. **ZN-PI is the reachable form.** And `0xC63E6` must be 0 in both (double integral).

---

## A5. 🛑 Kd IS BRACKETED FROM BOTH SIDES — this is the whole design space

| candidate | Kp | Kd | ring ratio @7.3 | `\|L(7.3)\|` | `GM` @ blind-band Nyquist | verdict |
|---|---|---|---|---|---|---|
| **V282/V283 as built** | 248 | 128 | 1.000 | 0.976 | **1.77× (5.0 dB)** | both gates pass |
| **F: Kd 160** | 248 | 160 | **0.932** | **0.909** | **1.48× (3.4 dB)** | both gates pass |
| Kd 192 | 248 | 192 | 0.869 | 0.848 | 1.27× (2.1 dB) | thin |
| 🛑 Kd 112 | 248 | 112 | **1.038** | **1.013** | 1.96× | **ring re-arms** |
| **ZN-PID (new) 329/162** | 329 | 162 | **1.013** | **0.989** | 1.39× (2.8 dB) | ring at the edge |
| **ZN-PI (new) 148/122** | 148 | 122 | **0.936** | **0.914** | **2.01× (6.1 dB)** | **both gates pass, both better than today** |
| **Kp 0 only** | 0 | 128 | **0.861** | **0.840** | **2.11× (6.5 dB)** | best on both, **0 % DC authority** |
| Kp 0, Kd 160 | 0 | 160 | 0.780 | 0.761 | 1.69× | " |
| 🛑 ZN-PI (OLD, retracted) | 108 | 387 | 0.347 | 0.339 | **0.69× (−3.3 dB)** | **UNSTABLE** |
| 🛑 ZN-PID (OLD, retracted) | 241 | 515 | 0.544 | 0.531 | **0.51× (−5.9 dB)** | **UNSTABLE** |

**The two modes move in OPPOSITE directions in Kd:**
- **7.3 Hz ring** — more Kd is **better**; the lower root is **Kd ≈ 118**, so a Kd *cut* re-arms the cycle.
- **27–32 Hz Nyquist** — more Kd is **worse**; **Ku ≈ 227**, so a Kd *raise* spends gain margin.

⇒ **Kd is bracketed at `[118, 227]` at Kp 248.** Today's **128 sits near the BOTTOM** of that window
(1.08× above the ring root, 1.77× below Ku). **Candidate F's 160 sits near its middle** (1.36× / 1.42×) —
which is, in gain-margin terms, the **best-centred point in the window**. That is a stronger argument
for F than "it is 5× below Ku", and it replaces that claim.

**The revised verdict on F:** F is **below Ku**, so the loop-shape study is still right and my Q4
adjudication stands in direction — but F **spends 16 % of a gain margin that is already 5.0 dB, taking
it to 3.4 dB**, at a frequency **no instrument on the car can see**. That is a real caution the first
pass did not carry, and it should be in F's pre-registration.

**On `Kp = 0`:** it is the best single move on *both* stability gates (`|L(7.3)|` 0.976 → 0.840; GM
1.77× → 2.11×, +1.5 dB). I confirm `telem285`'s sign result and strengthen its basis — the gain is not
only in the two symptom bands but in the **blind-band gain margin**. §1 of the main document is
unchanged: it still costs **100 % of the DC authority**.

⭐ **`ZN-PI (new) = Kp 148 / Kd 122` is the one candidate that beats today on BOTH gates simultaneously**
(ring 0.976 → 0.914; GM 1.77× → 2.01×) — because the Kp cut helps the ring more than the small Kd cut
hurts it. Its cost is DC authority: Kp 148 vs 248 puts steady-state tracking near **~40 %** against
today's 53.5 %, i.e. **more understeer**, unless `0xC63E6 = 50` is carried (which restores ~97 %).
⚠ And its Kd 122 sits only **3 % above the 7.3 Hz ring root of 118** — too close to fly without the
per-episode arm split first.

---

## A6. Q5, revised — the one-drive Ku estimate is INFEASIBLE for the mode that sets Ku

**Plainly: no.** And this is a useful answer, not a hedge.

1. **The binding mode is at 27–32 Hz.** The 427 tap is 50 Hz sampled (Nyquist 25 Hz) — it cannot see it
   at all. The 100 Hz `gp-0x6a56` stream reaches it in principle, but `CREEP-20HZ` §5 lists as
   *"not resolvable on this instrument"* whether the 20 Hz line is real or the **80 Hz alias folding to
   20** on those same 100 Hz streams. A Ku estimate at 28 Hz on a 100 Hz stream inherits that ambiguity
   directly.
2. **The 7.3 Hz ring CAN be measured this way — 5 episodes / ~8 s already gave [0.944, 0.990]** — but
   §A5 shows that mode is **not** what sets Ku, and it moves the **opposite** way in Kd. Measuring it
   more precisely does not tighten Ku at all.
3. **The 20 Hz mode has `Ms 2–3`, i.e. `|1−L| ≈ 0.33–0.50`** — it is nowhere near marginal, so a
   Q/decay estimator there has **~15× less leverage per episode** than at the 7.3 Hz ring (`|1−L| ≈
   0.024`). Combined with ~5 samples/cycle at 100 Hz and a decay time of ~1 cycle at Q ≈ 2.5, **no
   realistic episode count in a 15–30 s drive closes it.** I would not design a drive around it.
4. ⭐ **But you do not need a drive.** **Ku is already pinned to ±25 % from data in hand**: the gain
   margin is *measured* (1.75× @ 23.4 Hz), and the byte-exact controller reproduces the dose-response to
   0.8 % / 0.5°. The residual uncertainty is **the plant's phase above 25 Hz** (Ku 227 vs 865), and
   **no drive on the flying channels can reduce it** — on the delay model the car would *feel* the
   instability before any of these instruments resolved it.
5. **What WOULD reduce it, if the operator wants Ku tightened:** an on-ECU statistic, not a CAN
   channel. A cave rung counting **sign changes of `dE` per 100 ms** (or a `|dE| ≥ threshold` duty)
   samples at the PID's own **1 kHz** and is therefore immune to both the 25 Hz Nyquist and the 80→20
   alias. `CREEP-20HZ` §5 records the **24–28 Hz control floor as flat**, so such a rung has a clean
   baseline to move off. That is the instrument this question actually needs, and it is a cave design
   question for `telem285`.

---

## A7. What changed, and what is unchanged, from the first pass

| | first pass | **this addendum** |
|---|---|---|
| Ku | 859 (7.3 Hz magnitude root) | **227 [217–270]** (28 Hz Nyquist point) — **retracted and replaced** |
| Tu | 137 ms | **35.6 ms** (Kp 248) / 31.5 ms (Kp 0) |
| ZN-PI | Kd 387 / Kp 108 | **Kd 122 / Kp 148** — the old pair is **UNSTABLE (GM 0.69×)** |
| ZN-PID | Kd 515 / Kp 241 | **Kd 162 / Kp 329** — the old pair is **UNSTABLE (GM 0.51×)** |
| Q4 verdict on F | "5× below Ku, fine" | **below Ku, but spends 5.0 → 3.4 dB of margin in the blind band** |
| Q1 (plant type, Kp=0 has zero DC authority) | — | **UNCHANGED** |
| Q2 (authority loss table) | — | **UNCHANGED** |
| `Td` has no home | — | **UNCHANGED** |
| Kd cuts alone are DO-NOT-FLASH | — | **UNCHANGED** (and now bracketed from above as well) |

**What would falsify this addendum:** the plant's phase slope not continuing above 22 Hz. Everything
here rests on extrapolating a measured −3.75°/Hz from a 12 Hz baseline into a band no instrument
covers. The doc's own measured `GM 1.75× @ 23.4 Hz` is the anchor that makes the extrapolation short
rather than speculative, but it is still an extrapolation, and it is the number I would most want a
second method on.
