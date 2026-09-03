# The 6–8 Hz strong-turn oscillation — deep analysis, r24 settled against the servo, and the ONE next build

Deep-analysis subagent, 2026-09-03. Brief: `docs/handoffs/2026-09/HANDOFF-2026-09-03-7HZ-STRONG-TURN-for-deep-analysis.md`.
Script: `rlog-tools/studies/osc-highangle/r24_deembed.py` (standalone — it re-implements every transfer and re-reads the caches;
it inherits no constant from `twist_taper_loop.py`, `kpflat_sizing.py` or `v280_map_profiles.py`). Full stdout: `R24-DEEMBED.txt`
beside it. Disassembly: GhidraMCP on stock `code.bin`, plus raw little-endian byte scans of
`_v280_V280R2-…_plain_image.bin`. **EVIDENCE (with the method) or BELIEF on every claim.**

---

## 0. Headline

1. **At the oscillation frequency the LKAS rate servo's own return ratio is measured BELOW UNITY on 18 of 18
   episodes (0.58–0.92, median 0.81); the engaged-only r24 twist-derivative lane's is ABOVE unity on 17 of 18
   (0.98–1.29, median 1.17).** The servo lane cannot sustain the 7.3 Hz mode by itself at that frequency,
   whatever its phase. r24 can. [EVIDENCE — §2, a plant-free identity]
2. **The measurement needs no plant model, no aggregator sign convention and no units.** I confirmed in Ghidra
   that the LKAS lane (via `gp-0x6b4c`) and r24 are added with **unit coefficients into the same 1 kHz sum**
   (`FUN_0003aa2c`: `iVar19 = … + iVar21 + iVar16`, clamp ±0x2800 → `gp-0x6b94`). Because the plant from that
   node to the measured rate is common to both lanes, it cancels:
   `L_servo = T/(T+r24)`, `L_r24 = r24/(T+r24)`, and `L_servo + L_r24 = 1` exactly. [EVIDENCE]
3. **r24 pumps at 7 Hz and DAMPS at 15–25 Hz, because the bar-to-rate phase flips through the free-wheel
   torsion-bar mode between 9 and 15 Hz.** Measured in the loaded high-angle stratum: `bar/rate` is
   −95…−108° at 3.9–9.0 Hz (coherence 0.42–0.92) and **+111…+116° at 14.8–25.0 Hz (coherence 0.53–0.94)**.
   With the 4-tap differencer that puts r24 at **−11° from the wheel rate at 7 Hz (pumping)** and at
   **−165…−177° at 15–25 Hz (damping)**. This reconciles twistloop's 7 Hz reading with the on-car history in
   which turning the lane ON reduced the 18–22 Hz band. Both records are right. [EVIDENCE — §5]
4. **`f0` does not track `Kp`.** Over the 18 episodes Kp spans 351→696 (2.0×) and the regression slope is
   +0.00028 Hz/count (se 0.00093, 95 % CI −0.0017…+0.0023). The servo-crossover model's own prediction is
   −0.00605 Hz/count — outside that interval by 4.6 standard errors. [EVIDENCE, with the caveat in §4 that a
   self-regulating limit cycle also predicts a constant f0]
5. **V281 rev 3 (Kp flat 248) is predicted to stop the self-sustained cycle by a thin margin and leave a
   lightly damped 7.3 Hz mode**: the total return ratio at f0 falls 1.00 → **0.91 (N = 1) / 0.88 (N = 0.70)**,
   residual ring gain `1/|1−L|` = **2.1–3.0**. It cannot remove the pump; it removes the phase the pump needs
   at 7.3 Hz and pushes the mode's phase-zero up toward ~10 Hz. [EVIDENCE for the arithmetic; BELIEF for the
   frequency shift, which is an extrapolation]
6. **`0xC6446` 5244 → 512 alone, with Kp untouched, is predicted to damp the mode outright** — L_tot
   0.79∠+74° (N = 1) / 1.12∠+69° (N = 0.70), `|1−L_tot|` = **1.08–1.20, ring gain 0.83–0.93** — at **zero
   authority cost**, cal-only, one u16, one live reader. It is the better lever on every axis I can compute,
   and it is robust to the describing-function assumption that the Kp lever is not. [EVIDENCE on the model]
7. 🛑 **But the verdict inverts on one unmeasured number.** If r24's live gain is 1024 rather than 5244 — which
   is what `gp-0x671d` (a saturating fault-debounce counter, §3) selects whenever it is non-zero — then r24 at
   f0 is ~148 counts, `|L_servo|` becomes **1.14∠+16° and exceeds unity on 18 of 18 episodes**, and **the
   servo is the pump after all**. (At the gate-0 arm `0xC6440` = 2048 it is 1.20∠+35°, likewise 18/18.) The flip
   happens at r24 ≈ **566 counts** (median), i.e. at an effective `0xC6446` of ≈ **3909**; the flown cell is
   5244, a margin of only **×1.34**. r24 is not on the wire. [EVIDENCE for the threshold arithmetic]
8. ⇒ **The ONE next build is the INERT TAP, not a dose: V282 = the 427 delivered-torque tap re-pointed from
   `gp-0x6b38` to `gp-0x6ada` (r24). Two bytes at `0x55DF2`: `c8 94` → `26 95`.** Read-only, no cal change, the
   same single in-place displacement edit that produced the flown V278 rev 3 / V279 taps. One strong-turn drive
   settles the sign, the size, the `gp-0x671d` gate and the differencer's scale factor at once, and sizes every
   candidate dose offline. It also reads r24's 20 Hz phase in the creep windows on the same drive, which is the
   other half of the dispute. Pre-registration in §7. [EVIDENCE for the edit site and the encoding]

---

## 1. What I re-derived myself, and how

Everything below is from the three caches `analysis-2020accord/_scratch/cache/v280/r3{2,3,4}.npz` (V280 rev 2;
r32/r33 old StarPilot tune, r34 new), the 18 F7 episodes named in `HIGHANGLE-r32-r33-2026-09-02.md` and
`HIGHANGLE-r34-2026-09-03.md`, and the images in `../accord-firmwares/analysis-2020accord/`.

**Method.** For each episode I refine `f0` from the wire-rate spectrum (8× zero-padded, 5.5–9.5 Hz) and take a
Hann-tapered complex demodulation of the wire rate, the 0x18F driver torque, the CAN-427 tap `T` and the 0xE4
command at that single frequency. That gives an amplitude and a phase for each signal, with the wheel rate as
the phase reference. r24 is then formed in closed form from the decompiled arithmetic:

```
gp-0x4f60 = -1.024 * bar_wire                      # frame builder FUN_00055C42 sends -(gp4f60*125>>7)
gp-0x4f62 = 0.5 * (gp4f60[n] - gp4f60[n-4])        # 2*(cur-old)/dt, dt = 0xC6C42 = 4    [I disassembled this]
r24       = gp-0x6752 * (gp-0x4f62 * 0xC6446 >> 10), deadband 3, clamp +-8192
          = +5.244 * D4(f) * bar_wire              # gp-0x6752 = -1 cancels the frame builder's -1
D4(f)     = 0.5 * (1 - exp(-j*2*pi*f*0.004))       # |D4| = 0.0879 at 7 Hz, phase +85 deg
```

**Verified by me, this session, not taken on report:**

| claim | how | result |
|---|---|---|
| the 4-tap differencer's factor is **0.5**, not 2 or 1 | disassembled `0x7e828–0x7e864`: `subr` → `shl 0x1` → `divq r12` → `st.h r10,-0x4f62,gp`, i.e. `2·Δvalue/Δt` | **EVIDENCE.** With `0xC6C42 = 4` (read from the image) the operator is `0.5·(bar[n]−bar[n−4])`. A ×2 error here would move r24 across the decision threshold, so it mattered. |
| `Δt = 4` really is 4 milliseconds | the ±0x1400 clamp on `gp-0x4f62` and the ±3 deadband applied after the ×5.12 gain are both scaled for a 0.5·Δ operator, and absurd for a Δ/60 one | **BELIEF, well corroborated.** The tap settles it. |
| r24 and the LKAS lane sum with **unit coefficients** at the same node | decompiled `FUN_0003aa2c`: `iVar19 = iVar9 + gp-0x6b4c + gp-0x6ad4 + gp-0x6b62 + gp-0x6b26 + gp-0x6bbe + gp-0x6bd0 + gp-0x6b86 + iVar21 + iVar16`, then clamp ±0x2800 → `gp-0x6b94`; `iVar16` is the deadbanded gain-`0xC6446` lane and is stored to `gp-0x6ada` | **EVIDENCE** |
| the LKAS lane reaches `gp-0x6b4c` with gain 1 | decompiled `FUN_00026c80` and `FUN_00025c32`. `gp-0x6b4c = gp-0x3d88 + polarity·((iVar13 · 0xC63CC) >> 10)` and **`0xC63CC` reads 0 in the V280 image**, so the second term is dead. `gp-0x3d88` is `Σ gp-0x62b0[i]`; the mixer sets `gp-0x62b0[i] = gp-0x62f8[i]` (gain 1) for the static-mode-0 slots and `0` for the mode-5 slots. The static mode table `0xC4124` reads `[0,0,5,0,5,5,0,0,0,5,0]`, the enable table `0xC4118` is all 1. A mode-5 slot contributes **nothing** to `gp-0x6b4c`; the LKAS lane demonstrably drives the motor; therefore it is one of the seven mode-0 slots and its gain into the sum is **1**. | **EVIDENCE by elimination.** A direct trace of the LKAS slot id would close it outright — §8. |
| the 427 tap source is `gp-0x6b38` at `0x55DF0` | raw LE scan of the V280 image: the halfword at `0x55DF2` is `0x94C8` = −0x6B38, in a `ld.h` (`24 37 c8 94`); stock has `0x93E8` = −0x6C18 there | **EVIDENCE** |
| `gp-0x6ada` is r24's cell and has one writer | LE scan: `st.h` at `0x3AD5A` (`64 c7 26 95`), plus three sites in the 0x75000–0x79000 diagnostic block that read it | **EVIDENCE** |
| the r24 gain arm | `FUN_0003aa2c`: `if (gp-0x671d != 0) gain = 0xC6442 (=1024); else if (gate byte == 0) { gain = 0xC6440 (=2048) or Honda's speed LERP } else gain = 0xC6446 (=5244)`. The gate `ld.bu` at `0x3AA96` reads `fb` on this image (verified: `d[0x3AA96] == 0xFB`), i.e. `gp-0x6806` = STEER_CONTROL_ACTIVE | **EVIDENCE.** Confirms the kit's record and adds the `gp-0x671d` arm, which the record did not carry. |
| the firmware controller phase | my independent `C(f)` (PID → live multiplier 178/256 → output lag 992/507 → ×5346/32768 → fb two-sample sum 923/1560 → ×8 → z⁻¹) predicts `T/rate` at **+114.5°**; the tap measures **+115.6°** (median over 18) | **EVIDENCE — the chain mirror is right in phase to ~1°.** Its magnitude is 1.9× high (measured 2.59 vs 4.96 counts per wire-rate count), which is the P clamp's describing-function gain plus whatever else; see §4. |

---

## 2. §3 of the brief, settled: at 7 Hz r24 is the lane above unity, the servo is not

### 2.1 The identity

Both lanes land in one sum with gain 1, and the transfer `G0` from that sum to the measured wheel rate is
common to both. For any sustained sinusoid the loop's return ratio is exactly 1, so

```
rate = G0 * (T + r24)        =>        L_servo = T/(T+r24)          L_r24 = r24/(T+r24)
                                       L_servo + L_r24 = 1   (exactly, by construction)
```

`G0` cancels. **There is no plant fit, no sign convention, and no unit conversion in this statement.** All it
needs is the two phasors and the unit-coefficient summing junction. `|L_lane| > 1` means that lane's own
return ratio exceeds unity at f0: it could sustain the mode alone if its phase reached the critical point.
`|L_lane| < 1` means it could **not**, at that frequency, whatever its phase.

### 2.2 The measurement (18 episodes, V280 rev 2, r32/r33/r34)

Phases are degrees relative to the wire rate; amplitudes are counts at f0.

| route t0 | f0 | idx | Kp | \|T\| | \|r24\| | ph(T) | ph(r24) | \|T+r24\| | **\|L_servo\|** | **\|L_r24\|** | r24 flip threshold |
|---|---|---|---|---|---|---|---|---|---|---|---|
| r32 620.7 | 7.20 | 121 | 664 | 409 | 681 | +116 | −9 | 556 | 0.74 | 1.22 | 472 |
| r32 692.8 | 7.13 | 110 | 639 | 296 | 586 | +122 | +3 | 511 | 0.58 | 1.15 | 290 |
| r32 726.5 | 6.81 | 184 | 696 | 509 | 660 | +102 | −16 | 614 | 0.83 | 1.08 | 482 |
| r33 100.8 | 7.08 | 26 | 351 | 502 | 636 | +106 | −13 | 588 | 0.85 | 1.08 | 488 |
| r33 212.5 | 7.57 | 140 | 696 | 614 | 990 | +113 | −4 | 904 | 0.68 | 1.10 | 547 |
| r33 224.1 | 7.30 | 106 | 627 | 614 | 872 | +117 | −9 | 713 | 0.86 | 1.22 | 721 |
| r33 833.5 | 7.59 | 118 | 658 | 513 | 752 | +112 | −11 | 635 | 0.81 | 1.18 | 566 |
| r34 35.5 | 7.23 | 133 | 690 | 656 | 831 | +114 | −8 | 733 | 0.89 | 1.13 | 701 |
| r34 77.7 | 7.30 | 238 | 696 | 592 | 741 | +120 | −3 | 643 | 0.92 | 1.15 | 656 |
| r34 133.1 | 7.40 | 80 | 548 | 531 | 917 | +113 | −16 | 710 | 0.75 | 1.29 | 674 |
| r34 182.4 | 7.71 | 128 | 678 | 446 | 720 | +115 | −11 | 577 | 0.77 | 1.25 | 534 |
| r34 188.2 | 7.52 | 238 | 696 | 713 | 1149 | +123 | −2 | 947 | 0.75 | 1.21 | 811 |
| r34 343.7 | 7.47 | 86 | 566 | 594 | 829 | +112 | −9 | 726 | 0.82 | 1.14 | 620 |
| r34 372.9 | 6.81 | 127 | 677 | 550 | 841 | +121 | −6 | 672 | 0.82 | 1.25 | 664 |
| r34 475.7 | 7.37 | 104 | 621 | 510 | 768 | +119 | −8 | 616 | 0.83 | 1.25 | 613 |
| r34 480.9 | 6.59 | 114 | 648 | 435 | 479 | +101 | −14 | 489 | 0.89 | **0.98** | 375 |
| r34 667.7 | 7.06 | 148 | 696 | 441 | 599 | +116 | −2 | 552 | 0.80 | 1.08 | 414 |
| r34 1003.6 | 7.37 | 239 | 696 | 472 | 839 | +127 | 0 | 672 | 0.70 | 1.25 | 566 |
| **median** | **7.30** | 118 | 662 | 512 | 760 | **+116** | **−9** | 620 | **0.81** | **1.17** | **566** |

- **`|L_servo|` is above 1 on 0 of 18 episodes. `|L_r24|` is above 1 on 17 of 18.** [EVIDENCE]
- The lane phases are what twistloop measured, reproduced independently: T leads the rate by 116°, r24 sits
  9° behind it. My r24 median amplitude is 760 counts against twistloop's 767 — a 1 % agreement from a
  different code path.
- **The flip threshold.** `|L_servo| = 1` when `|r24| = −2·|T|·cos(∠r24 − ∠T)`, i.e. **566 counts** (median;
  range 290–811 across episodes). The measured 760 clears it by **×1.34**, equivalent to an effective
  `0xC6446` of **3909**. That is the whole margin the verdict rests on.

### 2.3 How much of the motor's 7 Hz content each term carries

Of the **620 counts** of 7.3 Hz drive arriving at `gp-0x6b94` from these two lanes (median), r24 supplies
760 counts at −9° and the servo 512 counts at +116°; they partly cancel. twistloop's within-T decomposition
is quoted as fractions of the torque **level** |T| p50 (median 860 counts here), not of the T ripple:
P-driven 0.53, D-driven 0.26, `0xCBBC4` multiplier 0.10 — i.e. **456, 224 and 86 counts**. Restated against
the 620-count total drive: **P ≈ 0.74, D ≈ 0.36, multiplier ≈ 0.14, r24 ≈ 1.23** (the components are not
phase-aligned and do not sum to 1; the two lanes sit 125° apart, which is why the 620-count total is smaller
than r24's 760 on its own). The setpoint-stage taper contributes nothing
(twistloop's measured depth 0.00; the live arm's knee at 2560 raw is never reached in these episodes).

### 2.4 What this does NOT say

- It does **not** say the servo is irrelevant. `L_servo` = 0.81∠+82° supplies +0.80 of **imaginary** part,
  which is exactly what rotates r24's 1.17∠−43° onto the positive real axis. **The servo supplies the phase
  the pump needs at this frequency.** That is why cutting Kp helps at all, and why it should move the mode's
  frequency rather than remove it.
- It does **not** rest on an energy argument. I tried one — "T at +116° does negative work on the rate, so the
  servo cannot be the source" — and **discarded it**: `∠T − ∠rate ≡ −∠G` identically, and the tap `T` is
  applied at the motor while the rate is measured at the column, so the product is not power. Any reasoning of
  that shape in this kit should be treated as void. [correction of my own draft]
- It does **not** survive a wrong r24 amplitude. §3.

---

## 3. The two gates that can invert the verdict, and one that can void it

Both are inside `FUN_0003aa2c` and neither is on the wire.

**(a) `gp-0x671d` — a saturating fault-debounce counter.** The gain arm is
`if (gp-0x671d != 0) gain = 0xC6442 = 1024`. I traced its writers: zeroed at `0x3BD2A`, and at
`0x41E8A–0x41EC6` it is incremented while a condition holds, saturated at 0xFF, compared against `0xC6500`,
and drives a DTC setter (`FUN_00016DE6`, id 0x5E) with an int/float lockstep twin at `gp-0x4c24`. So it is 0
in healthy operation [BELIEF, from its structure] — but **any non-zero value drops r24's gain 5.1×**, to
~148 counts at f0, which puts `|L_servo|` at **1.14∠+16°, above unity on 18 of 18 episodes**, and makes the
servo the pump. There is no intermediate reading: the verdict is binary on this byte. The sensitivity, run
over all 18 episodes:

| assumed `0xC6446` | \|L_servo\| median (range) | above 1 on | ∠L_servo | \|L_r24\| median |
|---|---|---|---|---|
| **5244 (flown)** | **0.81 (0.58–0.92)** | **0 of 18** | +81° | **1.17** |
| 2048 (`0xC6440`) | 1.20 (1.09–1.29) | 18 of 18 | +35° | 0.69 |
| 1024 (`0xC6442`) | 1.14 (1.08–1.21) | 18 of 18 | +16° | 0.33 |
| 512 (stock cell) | 1.08 (1.04–1.11) | 18 of 18 | +7° | 0.16 |

🛑 **Do not read that table as a build prediction.** It answers *"if the closed form is wrong by this factor
because a gate I cannot see selects a different cal, which lane is above unity in the cycle I measured?"* —
the measured `T` and rate are the outcome of a loop that already contained that r24, so the two return ratios
must still sum to 1. The effect of **changing** the cal is a perturbation from the measured state and is the
grid in §4.1, which is a different calculation.

**(b) `gp-0x67ac` — mutes the whole lane.** `FUN_0003aa2c` opens with
`if ((gp-0x67ac & (gp-0x67ac < 2)) == 1) { … }` and in that arm **neither `iVar21` (r26) nor `iVar16` (r24) is
added at all** — nor `gp-0x6ad4`, `gp-0x6b26`, `gp-0x6bbe`, `gp-0x6bd0`, `gp-0x6b86`, nor `FUN_00036682`.
`gp-0x67ac` is written by the mixer from `gp-0x3d98`, a flag set when any slot is in dynamic mode 2/3/4 with
its `gp-0x617c` byte non-zero. If that arm is live during the episodes, r24 contributes exactly zero and this
entire analysis is void.

**I can retire this one from the existing record, without a drive.** The same arm also drops `gp-0x6b26`,
`gp-0x6bbe`, `gp-0x6bd0` and `FUN_00036682` from the sum. The kit has on-car measurements that those lanes
*are* summed while engaged: V106's `gp-0x6b26` ×3 produced a measured band change (0.347, the only band result
that cleared its own null — `accord-no-build-has-moved-the-antidamping` and the grinding ledger), and Honda's
`gp-0x6bd0` damper was measured acting (`accord-gate2-damper-phase-passes`). Neither would have been possible
in the `gp-0x67ac == 1` arm. ⇒ **`gp-0x67ac` is 0 in normal engaged driving.** [EVIDENCE from the kit's own
on-car record, applied to a branch I read this session; the crux — that those cells are dropped in that arm —
I verified in the decompile myself.]

🛑 **The tap cannot settle this one.** `gp-0x6ada` is written **unconditionally** at the tail of
`FUN_0003aa2c`, after and outside the `gp-0x67ac` branch, so it carries the value r24 *would* contribute
whether or not the sum took it. The tap settles (a) and (c); (b) rests on the argument above.

**(c) `Δt = 4 ms`** in the differencer (§1). A factor-of-2 error moves r24 from 760 to 380 or 1520 counts,
i.e. across the 566-count threshold in one direction.

**All three are settled by the same one-drive measurement** — see §7.

---

## 4. Deliverable 2: what V281 rev 3 does, with r24 modelled explicitly

### 4.1 The prediction, exact at f0

Linearising about the measured cycle, a build that scales the controller by κ and r24's gain by α gives

```
L_tot = kappa * L_servo + alpha * L_r24 ,     kappa = pid(Kp_new, N=1) / pid(Kp_now, N)
pid(Kp, N) = N*Kp/256 + (Kd/8)*(1 - z^-1)  at f0,   Kd = 128
```

evaluated per episode at that episode's own f0 and Kp, then pooled. `N` is the P clamp's describing-function
gain at the present operating point; `kpflat` measured 0.60–0.83 on these frames, so I report N = 1.00 (no
clamping — the conservative case for the Kp lever) and N = 0.70 (kpflat's median).

`|1 − L_tot|` is the distance from the critical point; `1/|1 − L_tot|` is the closed-loop gain from a
broadband road input to the 7.3 Hz rate, i.e. the residual ring.

| `0xC6446` | Kp | L_tot at f0 (N = 1) | ring gain | L_tot at f0 (N = 0.70) | ring gain | reading |
|---|---|---|---|---|---|---|
| **5244** | 696 (as-is) | **1.009 ∠ +1.5°** | ∞ | **1.237 ∠ +14.3°** | ∞ | **sustains — this is the flown car** |
| 5244 | 645 | 0.992 ∠ −1.5° | ∞ | 1.177 ∠ +11.5° | ∞ | sustains |
| 5244 | 512 | 0.956 ∠ −9.5° | 6.0 | 1.030 ∠ +3.3° | ∞ | sustains at N = 0.70 |
| 5244 | 341 | 0.920 ∠ −21.5° | 2.7 | 0.933 ∠ −10.2° | 5.4 | cycle stops, strong ring |
| 5244 | 295 | 0.912 ∠ −24.4° | 2.4 | 0.904 ∠ −14.5° | 3.9 | cycle stops, strong ring |
| **5244** | **248 (V281 rev 3)** | **0.908 ∠ −27.7°** | **2.1** | **0.884 ∠ −19.3°** | **3.0** | **cycle stops; Q ≈ 2–3 mode remains** |
| **3072** (Honda's LERP arm) | 696 | 0.761 ∠ +28.4° | 2.0 | 1.068 ∠ +37.6° | 1.5 | cycle stops |
| 2048 (`0xC6440`, the gate-0 arm) | 696 | 0.724 ∠ +47.1° | 1.4 | 1.053 ∠ +50.6° | 1.1 | cycle stops |
| 1024 (`0xC6442`) | 696 | 0.753 ∠ +65.9° | 1.0 | 1.084 ∠ +63.2° | 0.9 | fully damped |
| **512 (stock cell)** | **696 (untouched)** | **0.790 ∠ +73.5°** | **0.9** | **1.115 ∠ +68.7°** | **0.8** | **fully damped, no authority cost** |
| 512 | 341 | 0.386 ∠ +82.6° | 1.0 | 0.565 ∠ +79.0° | 1.0 | fully damped |
| **512** | **248** | **0.285 ∠ +88.3°** | **1.0** | 0.428 ∠ +85.9° | 0.9 | fully damped |

**Reading it.**

- **Does Kp 248 kill the cycle if r24 is pumping at 767 counts? Yes, but only just, and it does not remove the
  pump.** `|L_tot|` goes 1.00 → 0.88–0.91: a 9–12 % margin. The residual is a Q ≈ 2–3 mode still sitting at
  ~7.3 Hz, driven by road input rather than self-sustained.
- **Kp 341 and Kp 248 are nearly the same build for this purpose** (0.920 vs 0.908 at N = 1; 0.933 vs 0.884 at
  N = 0.70), because `L_servo` is nearly orthogonal to `L_r24` at f0 — shrinking it mostly rotates the sum
  rather than shortening it. The extra authority the operator pays for 248 over 341 (−29…−48 % stalled push at
  idx 26–80 instead of −13…−28 %) buys **1–5 % of loop margin.** [EVIDENCE on the model]
- **The Kp lever's margin depends on N; the r24 lever's does not.** At N = 0.70 the whole Kp column shifts by a
  full notch — Kp 512 still sustains, Kp 341's ring gain doubles to 5.4. Every `0xC6446` row is stable at both
  N. That asymmetry is the strongest practical argument for the r24 lever.
- **`0xC6446` → 512 alone dominates.** Ring gain 0.83–0.93 with **Kp untouched**: no authority cost at all, no
  change to the stalled push, no change to the highway inner gain, nothing for the r31 stall class to
  reappear from.
- **Combined (512 + Kp 248)** is the most damped cell in the table and also the most expensive. On this model
  it is over-damping: 512 alone already puts the ring below unity.

### 4.2 Predicted ripple and rate, anchored

The road-driven baseline: over 1 s windows at |angle| ≥ 30°, v ≤ 10 m/s, the 6–8.5 Hz wire-rate amplitude is

| regime | r32 | r33 | r34 | median \|bar/rate\| at 7 Hz |
|---|---|---|---|---|
| engaged, hands light | 9.07 | 10.09 | 7.86 deg/s | 10.4–10.9 |
| engaged, hands on (\|tq\| ≥ 1216 raw) | 2.53 | 2.07 | 2.02 deg/s | 5.0–6.2 |
| **manual (disengaged)** | **0.92** | **1.22** | **1.31 deg/s** | 2.2–2.8 |

Taking the manual row (~1.1 deg/s) as the road-excitation floor at ring gain ≈ 1 [BELIEF — the manual arm also
has no 6× map and no servo, so it is an anchor, not a control]:

| build | ring gain | predicted 6–8.5 Hz rate | predicted tap ripple/level | F7 episodes /100 s |
|---|---|---|---|---|
| V280 rev 2 (now) | ∞ (sustained) | 17–29 in-episode; 7.9–10.1 p50 | 0.42–1.42 (median 0.55) | 6.3 pooled |
| **V281 rev 3** | 2.1–3.0 | **2.3–3.3 deg/s** | **0.10–0.25** | **≤ 1** |
| **`0xC6446` → 512** | 0.83–0.93 | **0.9–1.0 deg/s** | **≤ 0.08** | **0** |
| both | 0.9–1.0 | ~1.0 deg/s | ≤ 0.08 | 0 |

[BELIEF for the absolute numbers — one linear extrapolation from a self-sustained state; EVIDENCE for the
ring-gain ratios.] On this reading **V281 rev 3 passes its pre-registered thresholds** ((a) ≤ 2 per 100 s,
(b) ≤ 0.25 median), but near the edge of (b), and it does so by damping a mode it does not remove.

### 4.3 Where the mode goes

`∠L_r24` rises with frequency at ~9.4°/Hz over the measured band (from the per-episode fits: `∠R` +3.5°/Hz,
`∠G0` +5.8°/Hz). At Kp 248 the total return ratio's phase at 7.3 Hz is −28°, so its zero-phase point moves up
to roughly **10 Hz**. That is independent corroboration, by a different method, of `kpflat`'s own warning of
"a NEW lightly damped ~9 Hz ring (Ms 6.3 at 341)" — and it is bounded, because `bar/rate` flips sign between
9 and 15 Hz (§5), so r24 stops pumping there. [BELIEF — extrapolation outside the 6.6–7.8 Hz measured band]

---

## 5. §3's last clause: does the phase flip across the column resonance? Yes.

`bar/rate` in the loaded high-angle stratum (228 s of engaged frames, Welch, 256-point segments):

| f (Hz) | \|B\| ct/ct | ∠B | coherence | r24 phase re rate (= ∠B + ∠D4) | r24 counts per deg/s of rate |
|---|---|---|---|---|---|
| 3.91 | 1.72 | −102° | 0.42 | −15° | 3.5 |
| 5.86 | 4.15 | −99° | 0.71 | −14° | 12.8 |
| **7.03** | **7.62** | **−96°** | **0.91** | **−11° → PUMPING** | 28.2 |
| 7.81 | 10.29 | −95° | 0.92 | −11° | 42.3 |
| 8.98 | 10.72 | −108° | 0.44 | −24° | 50.7 |
| 10.16 | 3.08 | +149° | 0.07 | (transition) | — |
| 12.11 | 4.44 | +122° | 0.39 | −157° | 28.3 |
| **14.84** | **4.14** | **+116°** | **0.90** | **−165° → DAMPING** | 32.2 |
| **19.92** | **2.75** | **+114°** | **0.94** | **−170° → DAMPING** | 28.6 |
| 25.00 | 1.54 | +111° | 0.53 | −177° | 20.0 |

**The bar-to-rate phase swings 210° between 9 and 15 Hz.** A parametric fit over 4.5–9 Hz puts the free-wheel
torsion-bar mode at `fn` ≈ 11.8 Hz, ζ ≈ 0.07 (the phase crossing sits at fn, so the mode is ~10–12 Hz).
A derivative of the twist therefore **pumps below the mode and damps above it** — exactly the reconciliation
the orchestrator proposed in the grinding handoff §4, now measured. It resolves the standing contradiction:

- twistloop's 7 Hz reading (r24 in the pumping half-plane) — **confirmed**, at coherence 0.91–0.92.
- the on-car history (`gate ON reduced the 18–22 Hz band 0.52 vs 1.06`; `V61's rate-lane kill made it 7.9×
  worse`) — **also right**, because at 15–25 Hz the same lane is a near-ideal damper (−165…−177° re rate).

⚠ **This contradicts `creep20`'s creep-stratum number** ("bar re rate −70° at 20 Hz, spring-like"), which would
put r24 at +5.6° and pumping at 20 Hz. My stratum is loaded high-angle at 2–9 m/s; `creep20`'s is 1–3 m/s
hands-off creep. Both cannot describe the same mechanical configuration. **This is for `main` to route to
`deepgrind`, not for me to resolve** — the same statistic in matched windows settles it, and it decides
whether `0xC6446` → 512 helps or hurts the 20 Hz grind.

**Consequence for the recommendation:** if my 20 Hz phase is right, cutting `0xC6446` to 512 removes a real
damper at 20 Hz while removing the pump at 7 Hz. That trade must be read on the drive, and it is why §7's
pre-registration scores the creep band as a cost statistic.

---

## 6. Deliverable 3, part 1: what I can and cannot say about V281 rev 3

**I cannot show that V281 rev 3 cannot work.** My model says it works — it stops the self-sustained cycle by a
9–12 % margin and should clear both of its pre-registered thresholds. So it should fly as planned; it is built,
it passed a three-attacker pass, and a 2.8× swing in Kp is itself a powerful test of everything above.

**Two things about its pre-registration should be amended BEFORE the log lands** (amending after would violate
the kit's own rule; V281 rev 3 is unflown, so this is legitimate now):

1. **The FAIL sentence's list of remaining suspects is incomplete.** It reads: *"…the ripple is NOT the P-gain
   limit cycle … next is the outer loop or a plant-side resonance (V268 damper records), not Kp."* On this
   analysis the third and most likely suspect is **the engaged-only r24 twist-derivative lane**, and the
   outer loop is already excluded by the measured data (the 0xE4 command carries only 3–20 % of the T ripple,
   and the tune change from friction 0.212 → 0.03 did not move the episode rate). Proposed amendment: *"…next
   is the engaged-only r24 lane (`0xC6446` = 5244, gate byte `0x3AA96` = `fb`), which the r24 tap measures
   directly, or a plant-side resonance."*
2. **Add one statistic that discriminates.** Record `f0` per episode and the ratio `|bar ripple| / |rate
   ripple|` at f0 in the surviving frames. Predictions, registered now:
   - **This analysis:** `f0` unchanged or **higher** (toward ~10 Hz), `|bar|/|rate|` unchanged at ~10, ripple
     falls to 0.10–0.25 but does not vanish.
   - **The pure servo-cycle reading (`kpflat`):** `f0` moves **up substantially** (its own `f_180` goes
     8.2 → 12.0 Hz), the ripple goes to the noise floor, and `|bar|/|rate|` falls with it.
   - **If `f0` and `|bar|/|rate|` are both unchanged and the ripple barely falls**, the pump is r24 and its
     gain is at or above 5244 — go straight to the tap and then the dose.

**A correction of record, for the register, not licence to act.** `KPFLAT-SIZING-2026-09-03.md` §0.1 states
*"the 7 Hz line is the crossover limit cycle of a linear inner loop that is UNSTABLE at the as-is Kp"*, and
`PREREG-V281-READ.md` repeats it. On the measurement in §2 the servo lane's own return ratio at f0 is below
unity on every one of the 18 episodes, so that claim does not hold as stated — the loop it describes is
unstable only because the plant `G` it was identified against **already contains r24 closed at 10.2× the
`0xC6446` cell's stock value**. `kpflat` says as much in its own §6 (its margins are BELIEF-grade and descend
from one 175 s stratum); the handoff says it too (*"the tap-identified plant G already CONTAINS r24 closed"*).
Nothing here says do not fly V281 rev 3. It says its predicted benefit is partial, and its null does not
license the conclusion its FAIL sentence currently draws.

---

## 7. Deliverable 3, part 2: the ONE next build — V282, the inert r24 tap

### 7.1 The build

| item | value |
|---|---|
| **base** | V281 rev 3 (`_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.…_plain_image.bin`, sha256 `98a7a514…`) |
| **edit** | **one halfword at `0x55DF2`: `c8 94` → `26 95`** — the 427 tap's `ld.h` source displacement, `gp-0x6b38` (delivered LKAS torque) → `gp-0x6ada` (r24, the deadbanded twist-derivative lane output, post-clamp) |
| **class** | single in-place displacement edit, **read-only / inert**: no cal changes, no code cave, no behaviour change on the car. The same edit class that produced the flown V278 rev 3 and V279 taps (`427 source 0x55DF2`) |
| **cells changed vs V281 rev 3** | none |
| **frame field** | unchanged: `field = ((b0 & 3) << 8) | b1`, value = `±(field & 0x1FF) << 3`, at 50 Hz |
| **range check** | `gp-0x6ada` is clamped ±8192; the field encodes ±4088. r24's whole-route p99 is 784–976 counts and its in-episode amplitude 447–1149, so the field runs at 56–144 of 511. **Well-ranged, no over-range risk** — this is why I am proposing a quantised tap rather than the doctrine's default comparator: the range is known from the cell's own clamp and from the closed form, so the V96 failure mode cannot occur here. Rails only above 4088, which has never been observed. |
| **verified on the target image** | I read `0x55DF0` in the V281 rev 3 image: `24 37 c8 94`, displacement `0x94C8` = −0x6B38. Target displacement `0x9526` = −0x6ADA, bytes `26 95`, halfword-aligned as `ld.h` requires. Its Kp slot 7 record at `0xE5378` reads `X = 0,68,112,136,208 / Y = 248×5` — flat 248, as reported. [EVIDENCE] |
| **builder note** | the edit sits in the code region, so the bootloader CRC block covering `0x55DF0` must be recomputed (`verify_bootloader_crc.walk_all_blocks`); no other block changes. |
| **cost** | `T` is off the wire for this drive. It is reconstructible offline at corr 0.955 / slope 0.86–0.90 from the live-arm chain mirror (`twist_taper_loop.py`), and its 7 Hz behaviour is already characterised over 18 episodes on three routes. |

### 7.2 Pre-registration (write this to `PREREG-V282-READ.md` before the drive)

**Drive:** one strong-turn drive, 2–9 m/s, |angle| ≥ 30°, hands light, ~60–90 s of high-angle engaged time —
the same shape as the V280/V281 reads — plus ~60 s of 3–6 mph engaged creep for the 20 Hz half.

**Primary statistic — the amplitude ratio (settles gates (a) and (c) of §3; (b) is retired there by the
on-car record, and the tap cannot see it because `gp-0x6ada` is written outside that branch).** For each high-angle
engaged episode, compare the tapped r24's 6–8.5 Hz amplitude against the closed form
`5.244 · |D4(f0)| · |bar_wire(f0)|` computed from the same frames' 0x18F torque:

| measured ratio | what it means | licence |
|---|---|---|
| **0.85–1.15** | `0xC6446` = 5244 is live, `gp-0x671d` = 0, `gp-0x67ac` ≠ 1, `Δt` = 4 ms | the §2 verdict stands |
| ≈ 0.39 | the gate-0 arm (`0xC6440` = 2048) is selected — the `fb` byte is not doing what the record says | re-open the gate trace |
| ≈ 0.20 | `gp-0x671d` ≠ 0: the fault-debounce arm (`0xC6442` = 1024) is live | **verdict inverts — the servo is the pump; no `0xC6446` edit is licensed** |
| ≈ 0.00 | the lane is not running at all (a gate arm not in this list) | re-open the whole trace |
| ≈ 0.5 or ≈ 2.0 | the differencer's `Δt` is not 4 ms | rescale everything above and re-decide |

**Secondary statistic — the sign.** r24's phase relative to the 0x18F wire rate at f0.
**PASS (pumping): −40°…+20°, predicted −9°. FAIL (damping): near +171°** — in which case the `gp-0x6752`
polarity or the 0x18F sign chain is inverted, twistloop's §3d verdict retracts, and so does everything in §2.

**Tertiary — the decomposition, read directly.** With r24 measured and `T` reconstructed, compute
`L_servo = T/(T+r24)` and `L_r24 = r24/(T+r24)` per episode. Predicted: `|L_servo|` 0.6–0.95, `|L_r24|`
1.0–1.3 on a route where the cycle persists. If V281 rev 3 has already killed the cycle, these are read on
whatever residual ring remains.

**The 20 Hz half, on the same drive.** r24's 18–22 Hz phase re the wire rate in the creep windows, on the
**nominal frame counter, never on the logged receive times** (the batch-jitter trap from
`CREEP-20HZ-LOOP-ID`). Predicted from §5: **−165…−177°, i.e. damping.** If it reads near 0°, `creep20`'s
creep-stratum phase is right, r24 pumps at 20 Hz too, and `0xC6446` → 512 becomes a clean win on both bands.
⚠ The 427 tap runs at 50 Hz and r24 is a differentiator, so content above 25 Hz folds into this band; treat
the 20 Hz number as indicative and cross-check the coherence against the 0x18F bar.

**Cost FAIL.** None on the car — the build is inert. The build fails as an *experiment* if the field rails
(|value| ≥ 4088) on more than 1 % of engaged frames, or if fewer than three high-angle episodes occur.

**The FAIL sentence.** *"If the tapped r24's 6–8.5 Hz amplitude in the strong-turn episodes is below 0.5× the
closed-form `5.244·|D4|·|bar|` prediction, or its phase relative to the wire rate falls outside −40°…+20°,
then the engaged-only twist-derivative lane is not the pump this analysis names; the servo P-gain reading
stands; no `0xC6446` edit is licensed, and the next lever is the feedback-filter pole (`0xC63E8/EA`
16.5 → 33 Hz, DC held) with its reader census done first."*

**What a PASS licenses — and only this.** `0xC6446` 5244 → 512 (cal-only, one u16 at `0xC6446`, one live
reader at `0x3AC08`), Kp left wherever V281 rev 3 leaves it, with its own pre-registration built on the
per-episode `L_r24` the tap measured. **Not** before the tap: the flown margin is ×1.34 and the two gates in
§3 are unmeasured, so the dose is a coin-flip until this drive happens.

### 7.3 Why the tap and not the dose

The kit's own doctrine settles it — *"if the quantity is already computed and then discarded, a read-only tap
changes nothing on the car and lets every candidate dose be sized offline; that is strictly a better
experiment than picking a dose and flying it."* Here the quantity is computed, stored to `gp-0x6ada`, and
never observed. And the lane has a history in **both** directions (V62's rate-lane ×2 was the one measured
grinding fix; V255/V256's ×2 on the 6× base were undriveable; V246's ×1.5 never flew), which is exactly the
situation a dose cannot resolve and a tap can.

---

## 8. Deliverable 4: what I could not close, and the measurement that would

| open item | why it is not closed | the measurement that closes it |
|---|---|---|
| **r24's live gain** (`gp-0x671d`, `Δt`) | neither is on the wire, and the verdict is binary on the first | **V282, the r24 tap** — the amplitude-ratio table in §7.2 reads both |
| **`gp-0x67ac`, which mutes the whole lane** | not on the wire, and **the tap cannot see it** (`gp-0x6ada` is written outside that branch) | retired for now by the kit's own on-car record (§3b); a direct reading needs a second field or a tap of `gp-0x6b94` |
| **the bare plant `G0` outside 6.6–7.8 Hz** | de-embedding `G0 = G/(1+G·R)` is ill-conditioned: `|G·R| ≈ 1.5` at 7 Hz, so a 20 % error in `R` moves `G0`'s phase by tens of degrees. My Section H attempt produced physically impossible results (`G0` phase +115° at 12 Hz) and **I am not reporting its margin tables**; only the plant-free identity at f0 and the local fits over 6.6–7.8 Hz are load-bearing here. | a drive with a **different** `0xC6446`, re-identifying `G` from the tap; two gains give two equations and pin both `G0` and `R` |
| **the 20 Hz bar-to-rate phase** | my high-angle stratum reads +114° at 19.9 Hz (coherence 0.94); `creep20`'s creep stratum reads −70°. Different strata, opposite verdicts for r24 at 20 Hz. | the same cross-spectrum in matched windows — for `main` to route to `deepgrind`; and V282's creep segment |
| **which of the 11 mixer slots is the LKAS lane** | I established the unit gain **by elimination** (mode-5 slots contribute 0 to `gp-0x6b4c`; the LKAS lane demonstrably drives the motor; therefore it is a mode-0 slot, gain 1). Sound, but indirect. | trace the caller that passes the LKAS struct to `FUN_00025c32` and read its slot id |
| **`N`, the P clamp's describing-function gain** | taken from `kpflat`'s measurement (0.60–0.83), not re-derived by me. It swings the Kp column of §4.1 by a full notch and the r24 column not at all. | re-run the clamp fundamental-gain statistic on r34's episodes, which `kpflat` did not include |
| **whether "a small oscillation on top of a large one" is ripple/level 0.4 or the F7 count** | not mine to score | the operator, on the drive. Score bands; let him score symptoms. |
| **`f0` vs `Kp` as a discriminator** | the null slope (§0.4) is real, but a self-regulating limit cycle also predicts a constant `f0`, so it is supporting evidence rather than a proof. The one episode with `kpflat`'s measured `K_eff` = 225 (r33 100.8) sits at f0 = 7.08 Hz, in the middle of the pack, where the servo model wants ~11.5 Hz — but that is n = 1. | V281 rev 3's own drive: a 2.8× Kp swing with `f0` recorded per episode |

---

## 10. ADDENDUM — a small Ki on the rate PID (operator question, 2026-09-03)

Script: `rlog-tools/studies/osc-highangle/ki_sizing.py`, stdout `KI-SIZING.txt`. Every constant below is
re-derived from the disassembly this session; nothing is taken from the V270/V271 build scripts.

### 10.1 The Ki arithmetic and its units [EVIDENCE — my own disassembly of `FUN_00028ea6`]

```
E        = 32*sp - fb                                          # 0x29d76 shl 0x5 ; 0x29d78 sub r26
excess   = deadband(E >> 5, 0xC62E4 = 4)                       # 0x29d7c..0x29d9a
acc      = clamp(acc + ((excess * Ki) >> 3), +-0xC61BA*128)    # 0x29d9c..0x29dc2   (acc = gp-0x6dd0 >> 3)
I_term   = acc >> 7                                            # 0x29f18 sar 0x7
sum      = clamp(I_term + P + D, +-0xC61BE = 15360)            # 0x29f1e add r9 ; 0x29f24 add r8
gp-0x6dd0 = acc << 3                                           # 0x29de4 shl 0x3,r24 ; 0x2a190 st.w r24
```

- **Per-tick accumulation:** `I_term` gains `excess * Ki / 1024` every 1 ms tick.
- **Clamp:** the accumulator's limit is `0xC61BA << 10 >> 3`, and `I_term = acc >> 7`, so **`|I_term| ≤ 0xC61BA
  = 10240`** — the integral term is limited in exactly the same units as P and D, at two thirds of the sum
  clamp. This is integrator limiting, and it is the only anti-windup present.
- **The `0xC62E4` term is a DEADBAND ON THE ERROR, not an output anti-windup.** It is ±4 in `E>>5`, i.e.
  ±128 counts of E, i.e. **±0.52 deg/s of rate error** (fb DC 30.89 per raw count × 8 raw counts per deg/s
  = 247.1 counts of E per deg/s). At the error magnitudes that matter it costs ~2 %, so the integrator is
  effectively linear.
- **Reset:** `gp-0x6dd0` has exactly **four** accesses in the code region — `ld.w` 0x29DA4 and `st.w` 0x2A190
  in the live function, and the same pair at 0x2AC96/0x2B05C in the dead twin `FUN_0002A93A`. One writer.
  Every reset must therefore flow through r24 before that store, and there are exactly two `mov 0x0, r24`
  sites reaching it: **0x2A164** (the clear-everything path — r24, r29, r27, r22, r16, r12 all zeroed, i.e.
  the loop's not-valid / not-engaged arm) and **0x2A0C6** (the `gp-0x680a` alternate-taper arm, which
  twistloop found has no writer). **There is no driver-override reset and no conditional integration.**
  [EVIDENCE — a complete census, because the single writer bounds it]
- **The accumulator has no external reader**, so its entire effect on the car flows through the PID sum into
  `gp-0x6b38`, which is already tapped. [EVIDENCE — the same four-access census]

**Reader census of the three cells** (raw LE scan of the V280 image, 0x13000–0xC0000):

| cell | value | readers | verdict |
|---|---|---|---|
| **`0xC63E6` Ki** | **0** | 0x29D9C (live PID), 0x2AC8E (dead twin), 0x59B90 | effectively private. The third hit is a bare-halfword match whose decode (`ld.bu …, r0`) discards to r0, so it is far more likely a data coincidence than an instruction — **confirm before building.** |
| `0xC62E4` deadband | 4 | 0x29D6E, 0x29D84, 0x29D8C, 0x29D96 (live) + 3 in the dead twin | **fully private to the rate-PID pair** |
| `0xC61BA` I clamp | 10240 | 0x29DA0 (live), 0x2ACA0 (twin), **0x36ABA, 0x3BCC2, 0x5AAFC** | **NOT private — three outside readers. Do not touch it.** |

### 10.2 The Ki/Kp corner and the phase cost

`|I| = |P|` at **`f_i = 1.2434 · Ki / Kp` Hz**. Cost on the controller transfer, relative to Ki = 0:

| Kp | Ki | f_i (Hz) | 7 Hz | 9 Hz | 20 Hz |
|---|---|---|---|---|---|
| 248 | 5 | 0.025 | ×0.998, −0.14° | ×0.999, −0.09° | −0.02° |
| 248 | 20 | 0.100 | ×0.994, −0.55° | ×0.995, −0.35° | −0.07° |
| **248** | **50** | **0.251** | **×0.984, −1.38°** | **×0.987, −0.88°** | **−0.16°** |
| **248** | **100** | **0.501** | **×0.969, −2.80°** | **×0.974, −1.79°** | **−0.33°** |
| 248 | 200 | 1.003 | ×0.940, −5.79° | ×0.950, −3.68° | −0.66° |
| 248 | 400 | 2.006 | ×0.891, −12.28° | ×0.904, −7.75° | −1.35° |
| 696 | 100 | 0.179 | ×0.995, −1.38° | ×0.995, −1.03° | −0.34° |

**Folded into the measured 7.3 Hz loop share** (the plant-free identity of §2; r24 untouched at 5244):

| Kp | Ki | L_tot at f0 (N = 1) | ring gain | L_tot (N = 0.70) | ring gain |
|---|---|---|---|---|---|
| 248 | 0 | 0.908 ∠ −27.7° | 2.15 | 0.884 ∠ −19.3° | 2.98 |
| 248 | 50 | 0.918 ∠ −27.6° | **2.15** | 0.899 ∠ −19.7° | **2.95** |
| 248 | 100 | 0.928 ∠ −27.5° | **2.15** | 0.914 ∠ −19.8° | **2.95** |
| 248 | 200 | 0.949 ∠ −27.4° | 2.16 | 0.943 ∠ −19.9° | 2.93 |
| 248 | 400 | 0.990 ∠ −27.0° | 2.15 | 0.998 ∠ −20.1° | 2.87 |

**The 7.3 Hz mode does not care.** Up to Ki = 400 the residual ring gain moves by under 1 %: the integral
term shrinks the servo's contribution slightly and rotates it slightly, and the two effects cancel in the
sum with r24. The 20 Hz creep mode is untouched by construction — at 20 Hz the I term is 1.2 % of the D term
at Ki = 100. **Answer to the operator's constraint: a Ki up to ~200 costs nothing at 7–9 Hz and nothing at
20 Hz.** [EVIDENCE on the model — the measured loop share plus the exact firmware transfer]

### 10.3 What it buys and what it costs — closed-loop transients

Plant calibrated to the measured hands-light full-demand point (T 2462 counts → 124 deg/s against a
~690-count load): viscous `b` = 14.3 counts per deg/s, `τ` = 0.199 s (the kit's identified 0.80 Hz pole),
8.4 ms delay, Coulomb break-away `L`. **A MODEL, marked BELIEF** — but every parameter in it is anchored on
a measured point.

**(a) The command deadband — idx 26 (ref 14.5 deg/s), ordinary 690-count road load:**

| Kp | Ki | steady T | steady rate | overshoot |
|---|---|---|---|---|
| 696 (V280 rev 2) | 0 | 792 | 7.2 deg/s | none |
| **248 (V281 rev 3)** | **0** | **555** | **0.0 deg/s — the wheel does not move at all** | none |
| 248 | 20 | 793 | 6.4 | none |
| **248** | **50** | **869** | **12.0** | **none** |
| 248 | 100 | 890 | 13.9 | none |

**V281 rev 3 creates a hard command deadband at low demand that V280 rev 2 does not have**: at idx 26 the
P-only torque (555 counts) sits below the road load (690), so the wheel is dead. Ki = 50 removes it
completely, with no overshoot anywhere in this case. **Pure benefit.**

**(b) The stalled-wheel class — idx 58 (ref 32.3 deg/s), 2000-count break-away released at t = 2 s:**

| Kp | Ki | T in the stall | rate in the stall | time to the I clamp | peak rate after release | overshoot | time above ref |
|---|---|---|---|---|---|---|---|
| 696 | 0 | 2175 | 12.2 | never | 29.9 | −2.4 | 0.00 s |
| **248** | **0** | **1238** | **0.0 (dead)** | never | 11.0 | −21.3 | 0.00 s |
| 248 | 5 | 1568 | 0.0 (still dead) | never | 22.9 | −9.3 | 0.00 s |
| 248 | 20 | 2160 | 8.9 | never | 38.5 | +6.2 | 3.16 s |
| **248** | **50** | **2240** | **16.8** | 0.99 s | 42.7 | **+10.5** | **1.77 s** |
| **248** | **100** | **2240** | **16.8** | 0.47 s | 42.6 | +10.4 | **0.83 s** |
| 248 | 200 | 2240 | 16.8 | 0.22 s | 42.5 | +10.2 | 0.34 s |

**Ki = 5 — V270/V271's dose — is far too small: it does not break the stall at all.** Ki ≥ 20 does. Note the
shape of the cost: **the overshoot MAGNITUDE (~+10 deg/s, a third of the reference) is set by the integrator
clamp and the plant, not by Ki; Ki sets only how long it lasts, and a LARGER Ki gives a SHORTER lurch**
because it unwinds as fast as it wound. That inverts the usual "smaller is safer" instinct.

**(c) A driver holding the wheel — the case I expected to be the problem, and it mostly is not:**

| case | Kp 248, Ki 0 | Kp 248, Ki 100 | Kp 696, Ki 0 (V280 rev 2) |
|---|---|---|---|
| idx 60, held at 2600 ct | T 1281, rate 0 | **T 2462 (railed) within 0.41 s**; on release +10.2 deg/s for 0.80 s | T 2462, rate 0; on release −1.5 |
| idx 120, held at 2600 ct | T 2462 already | T 2462; on release +0.9 deg/s for 0.00 s | T 2462; on release −8.6 |

At idx ≳ 84 the P term alone already rails the output at Kp 248, so **the integrator adds nothing new
against a driver's hand there.** The exposed window is **idx ≈ 40–84**, where Ki takes the delivered torque
from ~1281 counts to the 2462 cap within half a second while the driver holds. That is new relative to
V281 rev 3 — but it is **not new relative to V280 rev 2, which already delivers 2462 there.** Ki restores
the override push that flat 248 removed; it does not exceed what is on the car today.

**(d) r31's real stall episodes, open-loop wind-up replay** (E from the measured rate, so this bounds the
wind-up and cannot show the overshoot): median E is 5509–49509 counts across the ten episodes, and the
integrator reaches its 10240 clamp within the episode at **every Ki ≥ 20**, and in 5 of 10 at Ki = 5.

### 10.4 The deadband cal is not the stall/normal discriminator

The obvious idea is to raise `0xC62E4` so the integrator only wakes on a stall: 4 → 64 moves the deadband
from 0.52 to 8.3 deg/s of rate error. **Do not.** Two reasons:

1. At Kp 248 the loop's *ordinary* steady tracking error in a loaded turn is already 13–25 deg/s
   (`kpflat` §3), which is as large as a stall error. No threshold separates them.
2. **A larger deadband makes the break-free lurch worse, not better.** The wound integrator only unwinds on
   error of the opposite sign, so with a deadband D the wheel must overshoot the reference by more than D
   before unwinding even begins — the wind-up latches. Keep `0xC62E4 = 4`.

The lever is Ki alone: **one u16 at `0xC63E6`.**

### 10.5 Is an accumulator tap needed first?

**No — and this is the one place where the kit's "enabling a disabled term needs a probe" rule does not
bite, for a reason the census makes explicit.** `gp-0x6dd0` has one writer and no external reader, so the
accumulator's entire effect on the car flows through the PID sum into `gp-0x6b38` — **which the CAN-427 tap
already carries.** The integrator is not a quantity that is computed and then discarded; it is in series
with the instrument. Its signature there is large and pre-computable: at idx 58 in a stall, T goes
**1238 → 2240 counts (×1.81)** with a rise time set by Ki (0.99 s at Ki 50, 0.47 s at Ki 100), and the
accumulator is reconstructible offline frame by frame from the logged rate and command using the arithmetic
in §10.1, then validated against the tap.

🛑 **The caveat is scheduling, not observability: V282 (§7) takes that same field for r24.** The two builds
compete for the one tap and must not fly together.

### 10.6 How this folds into the §7 recommendation

The recommendation in §7 does not change — **V282, the inert r24 tap, is still the ONE next build after
V281 rev 3's read.** Ki becomes the *second* build, and which of the two comes second is decided by
V281 rev 3's own drive:

```
V281 rev 3 (built, Kp flat 248)  --- fly it, read PREREG-V281 ---
   |
   +-- 7 Hz FIXED ((a) <= 2, (b) <= 0.25)  AND the stall/deadband cost bites ((e) >= 3, or the
   |   operator reports a dead low-demand command)
   |        => V283 = V281 rev 3 + Ki = 100 at 0xC63E6.  Cal-only, ONE u16, read on the existing
   |           T tap.  This is the companion the Kp cut needs: it gives back the low-frequency
   |           authority (idx 26 rate 0.0 -> 13.9 deg/s; idx 58 stall rate 0.0 -> 16.8 deg/s) and
   |           moves the 7.3 Hz ring gain 2.15 -> 2.15, i.e. not at all.
   |
   +-- 7 Hz NOT fixed ((a) >= 4 with (b) >= 0.4)
            => V282 = the r24 tap (Section 7).  The r24 question is then the live one and Ki is a
               distraction: it cannot touch a mode whose ring gain it does not move.
```

**Dose:** Ki = **100** (f_i 0.50 Hz at Kp 248), with **50** (f_i 0.25 Hz) as the conservative alternative.
Not 200: f_i = 1.0 Hz puts the inner integral corner inside the outer loop's own band (openpilot's command
is a 1–5 Hz low-pass), and the standing constraint is that the highway outer loop must not be pushed back
toward its ring. Not 5: it does not break the stall (table (b)). Between 50 and 100 the trade is lurch
duration (1.77 s vs 0.83 s) against the outer-loop corner (0.25 vs 0.50 Hz); I prefer 100, because the lurch
is what the operator feels and 0.5 Hz is still an octave below the outer loop's crossover.

**Pre-registration for V283, if it is cut.** Primary: at |angle| ≥ 30° stalled frames (rate/ref < 0.3) at
idx 40–80, the tap's |T| p50 — V281 rev 3 will read ~1240–1700, **PASS ≥ 2100**; and the low-demand command
deadband — engaged frames at idx 20–32 with the wheel stopped, **PASS: that class disappears.** Mechanism:
the tap's rise time into a stall, fitted against the predicted `excess·Ki/1024` per ms; if the fitted Ki is
not within ±30 % of 100, the arithmetic in §10.1 is wrong. Cost: peak rate after a stall breaks — **FAIL if
it exceeds the reference by more than 20 deg/s, or if the operator reports a lurch on exit from a stall**;
and statistic (g) of PREREG-V281 — **FAIL if a slow 0.3–1 Hz weave appears**, which is the outer-loop
interaction. **FAIL sentence:** *"If Ki = 100 leaves the stalled-frame |T| p50 below 2100 counts at idx
40–80, the integral path is not live on the car — `gp-0x671d`-class gating, the 0x59B90 reader, or a reset I
did not find — and no larger Ki is licensed until the accumulator is tapped directly."*

**Build gates before cutting V283:** (i) confirm 0x59B90 is data, not a second reader of `0xC63E6`;
(ii) do not touch `0xC61BA` (three outside readers) or `0xC62E4` (§10.4); (iii) for the adversarial pass —
Ki raises no ceiling: the sum clamp, the ±3072 output cap and every downstream clamp are unchanged, so
ADV281R2-B's interlock census carries over — **but the time spent AT the output cap rises**, which is a new
exposure for the soft-EME bound-arm integrator even though its trip condition (peak, not dwell) is unchanged.

---

## 9. Files

- `rlog-tools/studies/osc-highangle/r24_deembed.py` — the script (standalone; sections A/B demodulation and
  de-embedding, C the f0-vs-Kp discriminator, D broadband `B(f)`, E/H the ill-conditioned de-embedded Bode
  **kept for the record and NOT used for any claim**, F ripple predictors, G the regime table, I the loop
  decomposition, J the local fits, K the plant-free identity and the build grid).
- `rlog-tools/studies/osc-highangle/R24-DEEMBED.txt` — full stdout.
- `rlog-tools/studies/osc-highangle/ki_sizing.py` + `KI-SIZING.txt` — the Ki addendum (§10): the PI corner
  and its phase cost, that cost folded into the measured 7.3 Hz share, the calibrated closed-loop stall and
  driver-hold transients, and the open-loop wind-up replay on r31's stall episodes.
- Ghidra work this session: `FUN_0003aa2c`, `FUN_00026c80`, `FUN_00025c32` decompiled; `0x7e820–0x7e864` and
  `0x41e70–0x41ecf` disassembled; raw LE scans of the V280 rev 2 image for `gp-0x4f62`, `gp-0x4f60`,
  `gp-0x6ada`, `gp-0x6adc`, `gp-0x6b38` and for the cals `0xC63CC`, `0xC646A`, `0xC4118`, `0xC4124`,
  `0xC6440/42/44/46`, `0xC61F6`, `0xC6C42`.
- ⚠ `search_instructions` returned `instructions_scanned: 62` and a false zero on `-0x4f62` after a
  `disassemble_bytes` call in the same session. Every count and null above was taken with a raw Python
  little-endian scan of the image instead. The `search_instructions` undercount trap in `CLAUDE.md` should
  gain this second form: **a preceding `disassemble_bytes` can collapse its scan scope silently.**
