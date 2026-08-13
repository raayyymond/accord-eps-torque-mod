# REGIME LIVENESS MAP — {6–20 km/h · LKAS engaged · hands-on · returning to centre}

Built 2026-08-12 for the V97 decision. **Every calibration below is byte-read from the image that is
on the car** — `../accord-firmwares/analysis-2020accord/_v96_V92BASE-REVERT.CBE74-PROBE.6B70.374C.674E-427.6B70.SAR6_plain_image.bin`
— not from a build script and not from the record. On-car fractions are computed over the operator's
own elicitation episodes (`_r7e_r7f_elicitations.json`) intersected with engagement.

**Exposure.** `ELICITATION ∩ ENGAGED` = **90.5 s / 9,145 frames** (r7e 50.9 s + r7f 39.6 s).
`+ hands-on (|tq|>300)` = 63.1 s. `+ returning (sign(ang)·sign(rate)<0, |ang|>5°)` = **32.1 s**.
Both drives fault-free. Frame rate 101.1 Hz.

---

## 1. THE TABLE

Legend: **DEAD** = cannot deliver in this regime, structurally. **PARTIAL** = delivers but attenuated
or bounded well below its gate. **LIVE** = delivers at full designed authority.

| # | Lane / block | Cell | State | Binding gate, byte-read | Open on elicitation time |
|---|---|---|---|---|---|
| 1 | Base-assist DAMPER | `gp-0x6bd0` | **DEAD** | FactorC `0xC9E9C[26]`→`0xD77D0` X=[2240,3840,5120,8960] **Y=[0,…]**; X[0]=2240 ct = **34.97 km/h**. Byte-STOCK on V96, modes 24 **and** 26. | **0.00 %** (0 / 9,145 fr) |
| 2 | Return-to-centre | `gp-0x6b62` | **DEAD** | producer `FUN_00036388` *runs* (state 5 clears mask 0x830) but emits 0 — prior probe **0.0000 / 75,227** engaged fr | not on V96's wire |
| 3 | Dwell-snap gate | `gp-0x6bda` | **DEAD** | prior probe 0.0000 engaged | not on V96's wire |
| 4 | FactorD / angle term | `gp-0x6a10` | **DEAD** | FactorC multiplies in *before* FactorD ⇒ product is 0 below ~35 km/h whatever D holds. FactorD byte-read **flat 1024** in both modes. | 0.00 % |
| 5 | (unused lane) | `gp-0x6ade` | **DEAD** | 0 writers image-wide | — |
| 6 | Filtered Sensor-B term | `FUN_00036682` | **PARTIAL, −18.5 dB** | IIR alpha `0xC63D2` = **6** ⇒ corner 0.93 Hz. \|H(7.8 Hz)\| = **0.119**, phase **−81.8°** | live, negligible in band |
| 7 | RESONANCE PID | `gp-0x6ad4` | **LIVE — most reachable authority of any gated lane here** | output ceiling LERP `0xC67C2` X=[128,1280,3200] Y=[0,1024,1024] on **voted speed** | ceiling **p50 395–558, p90 ~830** of 1024 |
| 8 | FRICTION comp | `gp-0x6b26` | **LIVE** | LERP(speed, `0xCBE74`[26]→`0xD7A54`) × `gp-0x6c2c`; **largest at 0 km/h**; self-clamp `0xC407E` = 511 (Honda's) | 100 % |
| 9 | Inline rate lanes | r24 / r26 | **LIVE @ 1 kHz** | Lever B `0xC6446`=5244, `0x3AA96`=`fb97`; gate `gp-0x6806` ≡ latActive | 100 % engaged |
| 10 | Boost | `gp-0x6bbe` | **LIVE, but rate-derived** | measured 2026-08-12: 87–92 ct/(rad/s) flat 2–12 Hz, +18° | 100 % |
| 11 | Magnitude | `gp-0x6b86` | **LIVE** | zeroes only outside the ±25600 Sensor-B window | 100 % |
| 12 | LKAS lane | `gp-0x6b4c` | **LIVE — and SATURATED half the time** | ±0x2800 gate is vacuous; the bound that binds is openpilot's own ±4096 | rail duty **69.9 % / 52.1 %** of the return |
| 13 | Low-speed lockout | `0xC62EA` | **NO GATE — it is 0 on V96** | V53's "min steer speed 0" is carried; stock is 320 ct ≈ 5 km/h | `sstat==3` fires **0.00 %** |
| 14 | Authority-curve mode | `gp-0x674e` | **CONFIRMED < 28** | V96 cave b3 | **100.00 %** |
| 15 | ECU state gate | `gp-0x67fa` | **OPEN** | state 5 ⇒ `1<<5` clears 0x830 / 0x930 / 0xc30 | route 5d, 101,117 / 101,118 |
| 16 | Aggregator range gates (×8) | — | **VACUOUS** | each producer's ceiling sits at or inside its gate window | no reachable hard nonlinearity |

### What the table says in one line
Of the gated lanes, **only four can carry 6–9 Hz into `gp-0x6b70` in this regime**: r24/r26,
`gp-0x6ad4`, `gp-0x6b26`, `gp-0x6bbe`. Everything the kit has spent V74–V86 on — the base-assist
damper and its factor surface — is **exactly zero here, on every one of 9,145 frames**.

---

## 2. ON-CAR CROSS-CHECK — where the operator actually lives

**The band split is not what the kit assumed.** Over `ELICITATION ∩ ENGAGED`:

| \|wheel rate\| | r7e | r7f | in the RETURNING subset |
|---|---|---|---|
| micro 1–13 °/s | 23.0 % | 28.0 % | **15.8 % / 15.9 %** |
| **13–50 °/s** | **49.2 %** | **43.3 %** | **59.6 % / 61.3 %** |
| ≥ 50 °/s | 25.8 % | 24.1 % | 24.5 % / 22.8 % |

Speed: 91.8 % / 95.1 % inside 6–20 km/h — the regime brief is accurate. But the **micro band is a
minority of his elicitation time**, and the return-to-centre phase is dominated by **13–50 °/s**.
A lever tuned for 1–13 °/s addresses ~16 % of the phase that produces the complaint.

**Which dead zone actually binds.** FactorE's gate (`gp-0x6ac0` > 60 ct = 12.73 °/s) is **open on
67–84 %** of elicitation time. FactorC's (speed > 34.97 km/h) is open on **0.00 %**.
⇒ *the damper is a product of two dead zones, but only one of them binds here, and it binds
completely.* Opening FactorE alone buys **nothing**.

**Pricing the only surviving damper rung** — dose = min((C·E)>>10, 512) at 10 km/h, mode 26:

| FactorC Y[0] | 5 °/s | 13 °/s | 20 °/s | 30 °/s | 50 °/s | 80 °/s |
|---|---|---|---|---|---|---|
| stock 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| Y[0]:=Y[1]=234 | 0 | 0 | 3 | 7 | 16 | 29 |
| Y[0]:=Y[2]=429 | 0 | 0 | 5 | 14 | 30 | 54 |
| Y[0]:=Y[3]=908 | 0 | 0 | **12** | **29** | 64 | 115 |

Even the maximum monotone lift of FactorC alone delivers **exactly 0 at ≤13 °/s** — because FactorE's
own X[0]=60 ct = 12.73 °/s dead zone is still in force. This **confirms**
`accord-damper-cannot-reach-micro-regime` and strengthens it from "95.91 % of engaged frames" to
**100.00 % of the operator's elicitation time**.

---

## 3. WHERE THE RETURN-TO-CENTRE AUTHORITY COMES FROM

### 🛑 A polarity correction, made before any conclusion rests on it
`e4tq` is **sign-inverted** relative to `ang` and `rate`. Pinned causally, not assumed:
corr(`cmd`[n], Δ`ang` over the next 50–100 ms), hands-off engaged, = **−0.82 (r7e) / −0.71 (r7f)**,
peaking at the 50–100 ms physical response lag and decaying monotonically to 500 ms. Positive control
on the other convention: manual driving corr(`tq`, `rate`) = **+0.67 / +0.64**.
*My first pass had this backwards and reported the command as opposing the return. It does the
opposite.* Everything below uses the corrected sign.

### The apportionment [EVIDENCE, on-car]

| During the RETURN (engaged, hands-on, 6–20 km/h) | r7e | r7f |
|---|---|---|
| LKAS command acts **toward centre** | **88.7 %** | **91.6 %** |
| …and is **railed at ±4096** | **69.9 %** | **52.1 %** |
| driver torque acts toward centre | 52.6 % | 36.3 % |
| \|driver torque\| p50 | **826** | **811** |

Positive control — the WINDING phase, same masks: driver torque acts **away** from centre
**95.7 % / 85.0 %** at \|tq\| p50 **2,463 / 2,417**, command neutral (48–50 %), rail duty only
11–23 %. The convention and the phase labels are both validated.

**Answer:** openpilot supplies the return-to-centre authority, at the rail, for half to two-thirds of
the return. The driver has **relaxed to about a third of his winding effort** and is roughly neutral.
The firmware's own centring lane (`gp-0x6b62`) contributes **nothing** — it is measured dead engaged.
Mechanical caster is the residual and is not separately observable here. [BELIEF for the caster share
— by elimination, but the three firmware candidates are measured absent, opposing, or DC.]

### 🛑 The structural consequence for V97
For **52–70 % of the return the LKAS lane into the aggregator is a DC constant.** A constant cannot
carry a 7.8 Hz oscillation. And the ringing does not care:

| 6–9 Hz \|tq\| envelope, p50 | r7e | r7f |
|---|---|---|
| return, command **RAILED** (DC) | 121.6 | 378.5 |
| return, command **UNRAILED** | 125.5 | 277.4 |

No consistent difference. ⇒ this **independently confirms** the session's "not the rail, not
command-magnitude dependent", by a different route — and adds the sharper claim:
**the 7.8 Hz energy enters through a SENSOR-FED lane, not the command lane.**
That excludes every command-side lever from V97 and leaves
**{r24/r26, `gp-0x6ad4`, `gp-0x6b26`, `gp-0x6bbe`, the V89 plant-model path}**.

### The operator's own claim, measured
> *"it should be faster than with LKAS disengaged"*

It is not — it is **slower**. Return rate at matched speed and angle, hands relaxed (\|tq\|<1200),
6–20 km/h, stratified into speed×angle cells:

- **r7e: geometric-mean ratio 0.367 [0.247, 0.550]** over 8 matched cells — engaged **2.7× slower**, CI excludes 1.
- **r7f: 0.624 [0.266, 1.176]** over 6 matched cells — directionally slower, **does not clear**.

⚠ Unstratified the ratios read 0.302 / 0.471, which **overstates** the effect — speed and angle were
not matched. Use the stratified numbers.

⚠ **The effect is angle-dependent, and that is the informative part.** At \|ang\| 50–120° the ratio is
**0.164–0.309 in 4 of 4 cells across both routes** (engaged 3–6× slower). Every cell that reverses
(1.308, 1.333, 2.111) is in \|ang\| 10–25°.

**Reading [BELIEF, mechanism]:** under LKAS the wheel does not return *to centre* — it converges to
openpilot's *target* with the closed loop's time constant, and stops there. Free caster-driven return
is faster than a lightly-damped first-order loop settling, which is exactly the asymmetry the operator
describes, and the ringing is that loop's 6–9 Hz mode.

---

## 4. CONTROL — run before quoting the crux

Replicating the session's 6–9 Hz result on an independently-constructed mask (engaged return vs
manual return at matched 6–20 km/h):

| band | engaged p50 | manual p50 | ratio |
|---|---|---|---|
| **6–9 Hz** | 121.6 / 378.5 | 13.3 / 16.9 | **9.1× / 22.4×** |
| 15–22 Hz *(negative control)* | 35.9 / 35.8 | 9.5 / 6.5 | **3.8× / 5.5×** |

The 6–9 Hz contrast replicates. **But the control band moves too.** The effect is band-**preferential**
(2.4× / 4.1× above control), **not band-exclusive.** Engagement lifts the whole spectrum and lifts
6–9 Hz more. Report it that way, not as "engaged-only at 6–9 Hz".

---

## 5. 🛑 DEFECT FOUND — V96's regressor channel is dead

**Reporting, not fixing, per brief.**

V96's stated purpose is to telemeter a **transfer**: the slope
`f' = d(gp-0x6b70)/d(gp-0x374c>>4)`. **That slope is not obtainable from r7e or r7f.**

| V96 cave bit | meaning | duty, whole route (164,094 fr) |
|---|---|---|
| byte4 b7 | sign(`gp-0x6b70`) < 0 | 64.94 % / 68.27 % ✅ |
| byte4 b6 | sign(regressor) < 0 | 44.45 % / 41.29 % ✅ |
| **byte4 b5** | **Mhi bit 1** | **0.00 % — never set** |
| **byte4 b4** | **Mhi bit 0** | **0.00 % — never set** |
| byte4 b3 | `gp-0x674e` < 28 | 100.00 % ✅ (expected 1) |
| **byte7 b7** | **Mlo = bit 11 of \|v\|** | **0.10 % / 0.03 %** |
| byte7 b6 | fingerprint | 100.00 % ✅ (V96 identity) |

`M = 2·Mhi + Mlo` reads **code 0 on 99.90 % / 99.97 % of all frames, and 100.00 % of engaged
highway.** So `|gp-0x374c>>4| < 2048` essentially always — **the entire signal sits inside one LSB of
a 2048-count-per-LSB field.** Saturation duty is 0.00 %, so the build's own saturation guard fired in
the wrong direction: it protected the top of the range while the signal never left the bottom bin.

This is the **gp-0x6b98 "1-bit comparator" failure the V96 header explicitly warned against**, at the
opposite end: the field was sized off a *structural upper bound* of ~68,600 rather than off data,
and the real signal is under 2048.

**What survives:** both SIGN bits (they toggle richly), and the **primary** magnitude on CAN 427 —
`ab_mt` p50 12 → \|`gp-0x6b70`\| ≈ 154 ct, max 275 → ≈ 3,520 ct against its ±8192 clamp
(`0xC6200`, byte-read). The primary channel is healthy and well-ranged.

**What does not survive:** any *slope*, *magnitude* or *shape* of `f'`. A sign-only regressor can
still recover the **sign** of a monotone odd `f'`; it cannot recover its gain or its knots.

---

## 6. TRAPS IN THE r7e / r7f CACHES

1. **`damp_nz`, `thermo_128/288/448`, `g6ac2`, `v84_*` are stale bit-map decodes.** They are the
   V75/V81/V84 interpretations applied to V96's bits by `decode_v84_probe_r6d.py`, which decodes
   *both* legacy maps on every route by design. On V96 those bits mean b7=sign(`gp-0x6b70`),
   b6=sign(regressor), b5/b4=Mhi, b3=mode rung. **`g6ac2` ≡ 1 is the mode rung, not `gp-0x6ac2`;
   `damp_nz` is not the damper.** Anyone scoring the damper off `damp_nz` on these routes gets a
   confident wrong answer — and the damper is independently proven dead here (row 1).
2. **`raw14_b7` needs the same `[1:]` slice as `probe`.** `probe == raw14_b4[1:]`; pairing
   `raw14_b7` raw against `probe`/`t` is off by one frame (≈28° at 7.8 Hz). Asserted in this
   analysis with `np.array_equal(probe, raw14_b4[1:])`.

## 7. LEDGER CONFIRMATION

V96's filename reads `REVERT.CBE74`, but the image **carries V92's ×1.5 friction dose on modes
26/27**: mode 26 `0xD7A54` Y = [−14745, −8601, −2949] vs stock [−9830, −5734, −1966], ratio **1.500
at every knot**; mode 24 `0xD6A64` is byte-stock. This matches the build header
(*"0xCBE74 modes 24/25 STOCK and modes 26/27 at V92's x1.5"*) and contradicts a naive reading of the
filename. **Do not score V96 as friction-stock.**

---

## 8. WHAT THIS MEANS FOR V97

1. **No damper lever.** `gp-0x6bd0` is 0 on 100 % of the elicitation time and the maximum monotone
   FactorC lift still delivers 0 below 13 °/s. Any V97 proposal touching FactorC/FactorE/FactorD in
   this regime is inert by construction.
2. **No command-side lever.** The ringing is at full amplitude while the command is DC.
3. **Target the sensor-fed lanes.** `gp-0x6ad4` is the one with real unused headroom here — its
   ceiling is **395–558 median**, 2–3× the 164–341 the record quotes, because the operator's regime
   (6–20 km/h) is faster than the ratchet episodes (4.9–8.0 km/h) that number was measured at.
4. ⚠ **`gp-0x6ad4`'s elimination is band-scoped and does not cover 6–9 Hz.** V56 muted this lane and
   returned null — **scored at ~21 Hz**. The lane has never been scored at 6–9 Hz. Treat it as open,
   not eliminated. [The V56 null is EVIDENCE about 15–26 Hz and carries no information about 6–9 Hz.]
5. **Size for 13–50 °/s, not 1–13 °/s.** That band is 60 % of the returning phase; micro is 16 %.
6. **Fix the instrument before spending another flight on the transfer.** If V97 is to measure `f'`,
   the regressor needs an LSB near **128–256**, not 2048 — the observed range is under 2048 with the
   sign bits doing all the work.
