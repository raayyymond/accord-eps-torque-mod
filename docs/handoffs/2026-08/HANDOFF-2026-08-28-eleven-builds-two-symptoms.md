# HANDOFF 2026-08-28 — eleven unflown builds, two symptoms, and what each one actually tests

**Status: the analysis side is exhausted. Every remaining question needs an on-car drive.**
Eleven builds are verified and unflown. This file is the single place to act from.

---

## 🛑 THE TWO SYMPTOMS ARE DIFFERENT MECHANISMS — DO NOT ASSUME ONE FIX COVERS BOTH

| | **A — the ~7.8 Hz ratchet** | **B — the audible low-speed GRINDING** |
|---|---|---|
| what it is | a **mechanical resonance**, Q 14–29, ζ 0.017–0.036 | **broadband** acoustic excess |
| where | motor / rack / tyre side | above **every CAN Nyquist** (angle 50 Hz, 427 **24.9 Hz**) |
| instrument | barely CAN-visible (≤ ~2 % of RMS) | **audio only** — 90–110 Hz + adjacent control bands |
| dose-response | none established | **ladders with gain**: 1× −0.04 · 4× 0.84 · 6× 1.13 · 8× 2.24 dB |
| firmware reach | **excitation and loop phase only** — cannot remove a mechanical mode | **NONE** — see below |

**Symptom B is closed as unreachable by calibration.** The engaged forward path has no active
switching nonlinearity (deadband + sign gate are **dormant when engaged**, clamp `0xC61B4` inert);
`cal(0xC6194)`=3 runs in TASK 1 at 1 kHz ⇒ ~2 s full-scale ⇒ already smooth; and the **motor drive
stage carries 0.25 cals/KB against 10–12 in the control stage** — Honda left it uncalibratable on
purpose. Its sole cal, **`0xC4936`, is PWM hardware timing and MUST NOT be touched** (a 2×cal+offset
field in a 3-phase timer block — shortening inverter dead time causes **shoot-through**, which
destroys the power stage; strictly worse than the three brickings this kit has survived).

⇒ **every build below targets SYMPTOM A.**

---

## ✅ THE FLIGHT ORDER

All eleven verified 2026-08-28: **each rebuilds bit-identically, every assertion passes.**
Base is **V122** for all of them. `.rwd` files are in `accord-firmwares/flashing-2020accord/rwd/`.

| # | build | edit | why it is here | B | asserts |
|---|---|---|---|---|---|
| **1** | **V157** | FactorC `Y[0]`→own `Y[1]`, FactorE `Y[0]`→539 | **damper reaches the micro regime, 4× dose.** Product 123 = **24 % of the 512 ceiling** | 6 | 62/62 |
| 2 | V156 | FactorC `Y[0]`→60, FactorE `Y[0]`→539 | same lever, conservative. Product 31 = 6.1 % | 6 | 60/60 |
| 3 | V153 | `0xC40D0` 408→104 **+** `0xC63AC` 102→26 | **matched observer poles**, corner 16.7→4.09 Hz, **1.95× less at 7.8 Hz, zero DC cost** | 3 | 54/54 |
| 4 | V152 | same pair, 408→204 / 102→51 | same lever, /2. 1.26× less | 3 | 54/54 |
| 5 | V149 | `0xC6446` 5244→1024 | removes the **5.12× r24 switch**. ⚠ inert if `gp-0x671d` never increments | 2 | 52/52 |
| 6 | V139 | both pump arms `sar 10→11` | halves both aggregator arms — demonstrated on-car potency | 2 | 49/49 |
| 7 | V155 | `0xC63A6` 1024→256 | inertia lane /4 — cleanest mechanism, **small magnitude** (lane ≤ ~8 % of the sum) | 1 | 58/58 |
| 8 | V154 | `0xC63A6` 1024→512 | same lever, /2 | 1 | 58/58 |
| 9 | V150 | `0xC6136` 0→1 | removes the r26 suppression switch, pump-suppressing direction | 1 | 51/51 |
| 10 | V148 | deadband 96 + probe on `gp-0x671E` | **measures** whether `gp-0x671d` toggles — makes V149 interpretable | 3 | 69/69 |
| 11 | V151 | knee 3000→3600 | **marginal** — the relay is already ~99 % unsaturated; costs 17 % of the term | 2 | 53/53 |

```
V157  65021b6d996ab1107d9dcf7a15667e1b321e2578a33e49572d27e92893785145
V156  bc070cba9e195231337070e57cf228c4ac126f5e09dbc8e2c2e7f68aca37c24d
V153  c25fc1d64a3f0d8c291b37722db29a8847f037f127d11c304d0e956ef4bc50cb
V152  2a5ceef7ba80809593c4b7f6aca4747235dcf30e9c2e442cf7ba3d0b1386e140
V149  6c39034055503e6e2e61576f40096d31102e04493ec248e53f5d0930390f2a9f
V139  6cd7799d63cbd5feb424913761a8f7f387b9f65dc8bfd30e08013bfd9b57121f
V155  0d138c838ea505357ab414cce1685d0d758037823f334718daaba6c93dac1cb6
V154  6fe3eceb410d13ecd56f02da09b1e37081818af9de8f501c306d7484f3015806
V150  d6aae5ee8b79f68bb52c040c82aa0f674e537818f23c1ba5081a9d56bc690ab3
V148  815aec7e04a655ed13ec2f7e0fcd6ed906191b7f6f2a0345faf5079215879071
V151  eb98eb6520f656523ca2db8438de0a3c5c072dbc31f8d35f09fcabebfe427287
```

### 🛑 PAIRS — FLY ONE OF EACH PAIR, NEVER BOTH
`V157 / V156` · `V153 / V152` · `V155 / V154` are **the same lever at two doses.**
`V149`, `V150`, `V151` each assert the others' cells are held ⇒ **do not stack before one flies.**

---

## ⭐ WHY V157 IS FIRST

The ratchet is an **underdamped** resonance, and **adding damping is the textbook fix.** The base
damper is `ch0 = FactorC(speed) × FactorE(rate) >> 10` — a **product of two dead zones**, and below
`X[0]` a LERP returns `Y[0]`, both of which are **0**:

* FactorC `Y[0]`=0 ⇒ zero below 35 km/h — all creep
* FactorE `Y[0]`=0, `X[0]`=60 ↔ the recorded **12.73 °/s** ⇒ the micro regime (1–13 °/s) sits
  **entirely below `X[0]`**, exactly where `Y[0]` applies

⇒ measured **zero on 100 % of the micro regime.** **Neither factor alone can open a product** — V134
raised FactorC and measured **inert**; the FactorE-only variant was **withdrawn as vacuous**. V157 is
the first build to move **both**.

✅ **It respects the standing constraint.** Damping is added **only below 12.73 °/s**; above that
FactorE is **byte-unchanged**, so **max angular velocity and acceleration are untouched.**
🛑 **Bounded by V80's catastrophe** — flat FactorC 566 across *all four* knots passed the ceiling and
made the damper a **bang-bang relay** (worst grinding in the kit's history). V157 flattens **only the
first segment**, leaves `Y[1..3]` byte-identical, and sits at **24 % of the ceiling**.
⚠ **The ceiling itself must not be raised** — it is the `0xC407E` fault interlock; V73 raised it and
V74/V75 faulted.

---

## 🛑 HOW TO JUDGE THE DRIVE

**By ear, and capture audio.** This is a measured conclusion, not a resignation:

* the matched engagement contrast on CAN is **1.12× [1.01, 1.27]** (24 routes, controls null)
* with a **passing positive control** (a Q=20 line at 2 % of RMS reads 1.35×), engagement adds
  **≤ ~2 % of RMS** as a 7.8 Hz line on the column
* ⇒ a build removing **half** the engaged line moves a CAN statistic **≤ 1 %**, against a measured
  between-route floor of **19.9× / 36.2×** for identical cals

⇒ **no CAN statistic can rank these builds.** Audio can — the 11-route ladder separates stock
(fails its null, p=0.890) from 9/10 gain builds (p<0.001) — but only for symptom B.

**Drive shape:** ≥2 min engaged creep, 1–24 km/h, hands off, real steering activity, **audio on.**

---

## 🛑 STANDING ANSWERS — DO NOT RE-DERIVE

* **8× LKAS gain: NO.** Measured — 6× = 1.13 dB, 8× = 2.24 dB engaged acoustic excess ⇒ it
  **doubles** the grinding and fails the operator's own stated condition. Lowering the gain is
  barred separately. **The gain is frozen in both directions.**
* **`0xC4936`: NEVER.** PWM hardware timing; shoot-through risk.
* **The ceiling (512): NEVER.** It is the fault interlock.
* **Ghidra's `code.bin` is STOCK.** Before trusting any decompile for a build, diff that function's
  byte extent stock-vs-target in Python.
* **tp-relative reader counts need the `reg1 == tp` filter** (`hw1 & 0x1F == 5`) — without it ASCII
  matches inflate counts (`0x746E` = `"nt"`).
