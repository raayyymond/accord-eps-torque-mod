# HANDOFF 2026-08-06 (late) — V74 ALSO hard-faulted, in MANUAL, with the damper edits byte-stock. The fault class is not a FactorC/E dose problem.

**Session shape:** orchestrator + 13 subagents, then a late operator report that reframed the whole day.
Route `5e` (V75's fault drive) was analysed for the first time — the previous handoff recorded "n = 1, no rlogs."

---

## 1. The two operator reports

**Morning (already on record):** V75 fixed the audible grind #1 and strongly attenuated the micro-ratchet, then
hard-faulted at a stoplight launch — EPS lamp, LKAS fault, total loss of assist, manual effort for the rest of
the drive.

**Late in the session, and it changes everything:**
> "V74 also just threw a fault. It happened when LKAS was **disengaged** and I manually drove **over a bump**…
> It was a hard fault where I lost manual power steering. I had to stop and restart the car to get manual power
> steering back. After driving for 30 s, the dashboard lights turned off."

**EPS lamp on continuously → still on after the restart → off after ~30 s of driving.** That is textbook DTC
maturation: a fault sets with `warningIndicatorRequested` and latches assist off; the power cycle restores
assist but not the lamp; the monitor re-runs clean and, once its test *completes*, the indicator is dropped.
It also matches the `gp-0x3ee8` state-8 force latch — set once, **never cleared anywhere in ROM**.

---

## 2. The load-bearing finding: the damper edits were NOT in force

Disengaged means **mode 24**. Read through the pointer arrays (`FACTOR_C_PTRS=0xC9E9C`, `FACTOR_E_PTRS=0xC9F84`,
stride 4, record `[u16 n][n×int16 X][n×int16 Y]`):

| mode 24 (MANUAL) | address | stock / V74 / V75 |
|---|---|---|
| FactorC | `0xD67E4` | `X=[2240,3840,5120,8960] Y=[0,234,429,908]` — **byte-identical on all three** |
| FactorE | `0xD6820` | `X=[60,400,2500,4000] Y=[0,140,539,927]` — **byte-identical on all three** |
| FactorB / FactorD / Ceiling | `0xD6760` / `0xD67A4` / `0xD60B4` | **byte-identical on all three** |

Independently: of the **54 non-CRC runs** in the V73→V74 diff, **zero** land inside any mode-24 record.

⇒ **[EVIDENCE, two methods] V74 delivers byte-stock damper behaviour in manual. The FactorC/FactorE edits
cannot have caused the bump fault.**

🛑🛑 **CONSEQUENCE: `k* ∈ (0.580, 1.580]` is VOID.** Every gain-margin argument in the previous handoff rested
on "V74 flew 1,011 s clean." It has now hard-faulted with the levers under investigation *inactive*.
**No build in the current lineage has demonstrated safety.**

### What IS live in manual and non-stock — and none of it is new at V74

| cell | stock → V74 | introduced |
|---|---|---|
| **`0xC63A0`** | 1024 → **2048** | **V72** |
| `0xC407E` | 511 → 850 | V73 |
| `0xC61B2/B4` | 512 → 2048 | V38 |
| boost floor `0xC6768/6A/6C` + float mirror `0xC65C4/8/C` | 0/1536/2048 → 5120, 5.0 | V38 |
| `0xC62EA` (low-speed lockout window) | 320 → 0 | V53 |

⚠ V72 and V73 carried the same manual-mode configuration without a manual fault. **n = 1** — the bump may
simply be the first sufficient trigger, or this is not it.

---

## 3. V75's fault, pinned to a single 100 Hz frame

Route `5e`, **t = 284.7947 s, segment 4**. Everything latches in one transmission:

| channel | before | after |
|---|---|---|
| bus STEER_STATUS (`gp-0x6807`) | 0 (28,319 frames) | **7** |
| STEER_CONTROL_ACTIVE | 1 | 0 |
| `gp-0x6880 & 3` | 0 for the whole drive | 1 |
| **`0x1AB` byte0 bit2 — the firmware's own DTC-active flag** | 0 (14,160 frames) | **1** |
| `0x14A` STEER_ANGLE / ANGLE_RATE / WHEEL_ANGLE | live | **all three → `0x7FFF` sentinel** |
| STEER_SENSOR_STATUS | 7 | **4** |

openpilot reacted +5 ms; dash-lamp frames on `0x450`/`0x440` at +0.12 / +0.28 / +0.52 s. Assist never returned:
11,643/11,643 frames at STEER_STATUS 7 over 116.4 s, with median driver effort up **12×**.

**Post-fault the ECU is alive**: the probe cave keeps executing (2,165 `gp-0x6ac2` transitions), `0x14A` and
`0x18F` both hold exactly 100.0 Hz, MOTOR_TORQUE is frozen at a constant payload ⇒ **a motor-off latch, not a
task death or a reset.**

### Three facts that kill every magnitude-based mechanism

1. **The faulting launch was the MILDEST of four engaged stoplight launches.** Launch #2 sat on openpilot's
   ±4096 rail for **76%** of its window and drove the damper to a higher bracket — no fault. Launch #4 had
   **0.00% rail contact** and the lowest driver torque.
2. **The damper never approached its ceiling** — the `≥448` probe rung fired **0 / 39,961 frames**.
3. **300 ms pre-fault there was a 20.0 Hz oscillation** — 1,368 counts p-p in driver torque, 93 counts p-p in
   angle rate, dominant line 20.0 Hz on both — **absent from openpilot's command** (3.3 Hz). The kit's own
   ~21 Hz plant mode. The damper thermometer stepped up one bracket 20 ms before, then froze for 116 s.

⇒ **This is a fast-transient sensitivity, not a dose problem.**

---

## 4. The bit13 fingerprint — orchestrator-verified in Ghidra

`FUN_00040a50` forces the angle sentinel when `FUN_00040906(1)==0xff && FUN_00046ea6(0xd)!=0`.
`FUN_00046ea6(N)` returns **bit N of the OR-aggregate `(gp-0x18d0 | gp-0x18d4)`**, which ORs the first word of
the fault-descriptor record at **`tp-0x72bc = 0xBF000-0x72BC = 0xB7D44`**, stride `0x1c`, fault_id 0–125.
`0xd` = **bit13**.

⇒ **the angle-sensor invalidation is a CONSEQUENCE, not a cause** — no re-pointing to the angle domain — **and
bit13 is a fingerprint of what fired:**

| fault_id | descriptor | bit13 | verdict |
|---|---|---|---|
| 4 (init self-test) | `0x00001C01` | no | **ruled out** |
| 80 = `0xC41668` (ADC timeout) | `0x00000C00` | no | **ruled out** |
| 72 = `0xD48394` | `0x00000C20` | no | **ruled out** |
| **28 — Monitor 1** | `0x00003D01` | **yes** | **live candidate** |
| **29 — Monitor 2 / `FUN_00045a20`** | `0x00003D01` | **yes** | **live candidate** |

Both are **un-debounced single-cycle latches** on the damper's own signal chain. `FUN_00045a20` compares
`comp = (gp-0x6acc − gp-0x6ace)/1024` against **±0.001**, widening to ±5.001 only when `|gp-0x6abe|` crosses a
*separately filtered* threshold. Monitor 1 checks int/float clamp consistency on `gp-0x6bd0` itself at ±5/1024.

**This is the operator's "plausibility window" hypothesis in its true form** — not a stale range check on an
output, but a **consistency corridor between two representations of the same signal**, sized when the creep
damper was structurally zero and never revisited.

---

## 5. The DTC read is structurally blind, and that is now proven

- **`0xF00049` is a catch-all shared by ~42 fault_ids.** Its status byte cannot name a monitor even in principle.
- A multi-member group's UDS status is **not an OR across members**: the display picks a winner from a **live
  RAM** fault-log array (pointer `tp-0x7fcc`) by priority, falling back to the group's first ROM member
  (**fid 4**, a power-on self-test). **The RAM log is cleared by the power cycle** ⇒ a fresh `0x1c`/`0x1d`
  trip is invisible in a `19 02` read taken after a restart.
- **Provenance [EVIDENCE, raw ISO-TP]:** `dtc_script_output_stock_eps_preV21new.txt` shows
  `5902ce 540011 40 c41668 08 d48394 40 f00049 48 f00055 40` on **stock firmware, before this kit's first flash.**
  Today's read differs in exactly two bits — `0xC41668` gained `pendingDTC`, `0xD48394` gained `confirmedDTC`.
  **`0xF00049` is byte-identical to stock.** `dtc_script_output_2.txt` shows `f00049 = 0x0E` when it genuinely
  fires, so the store *is* responsive.
- **`0x23` ReadMemoryByAddress is not implemented on this ECU** — NRC 0x11 in all three captures across three
  firmware eras. Stop proposing it.
- ⚠ **fault_id off-by-one**: the direct map at `tp-0x5AB8 = 0xB9548` (stride 4, DTC = raw bytes[2],[1],[0])
  gives `0xC41668`=**80**, `0xD48394`=**72**, `0x540011`=**16** — one lower than several agent reports claimed.

---

## 6. Path 2 is a closed loop inside the firmware, and `0xC63A0` weights the damper into it

`gp-0x6bd0` reaches the motor by two routes:

- **Path 1 — `FUN_0003aa2c`, the aggregator: unity weight, zero phase.** This is what delivers the damping.
- **Path 2 — `FUN_00038148` stage 1:** six gated terms, **plain ADD, no subtraction**, each `(x*gate*w)>>10`,
  then × polarity `gp-0x6752` × `tp+0x7468 = 0xC6468 = 2639` >>10, then a 1 kHz IIR with
  `tp+0x73ac = 0xC63AC = 102` (**corner 16.70 Hz**) → stage 2 → `gp-0x6b70` → `FUN_00037fe6` → `gp-0x6ad6` →
  `FUN_0003a382` (PID) → aggregator → `gp-0x6b98`.

★★ **`gp-0x6b98` re-enters Path 2 one sample later via `FUN_0003b8f6`** (called at `0x2240e`, before the
governor at `0x229ce`, same 1 kHz tick) ⇒ **Path 2 is a closed feedback loop inside the firmware, not through
the plant.** 🛑 **`0xC63A0` does not touch that re-entry term, and it may dominate. OPEN — highest-value next trace.**

### `0xC63A0` is the odd one out

`tp+0x73a0 = 0xBF000 + 0x73A0`, u16 Q10. It is one of **six sibling weights** at `0xC63A0`..`0xC63AA`, **all
stock 1024**, and it is **the only one any build in this kit's history has ever moved** — V72 set it to 2048
and nothing reverted it until V77.

| weight | signal | gate | stock | V74/V75 | V77 |
|---|---|---|---|---|---|
| `0xC63A8` | `gp-0x6b4e` | ±10240 | 1024 | 1024 | 1024 |
| `0xC63AA` | `gp-0x6b4c` | ±10240 | 1024 | 1024 | 1024 |
| `0xC63A6` | `gp-0x6b26` | ±1024 | 1024 | 1024 | 1024 |
| `0xC63A4` | `gp-0x6b46` | ±1024 | 1024 | 1024 | 1024 |
| **`0xC63A0`** | **`gp-0x6bd0` (damper)** | **±2048** | **1024** | **2048** | **1024** |
| `0xC63A2` | `gp-0x6bbe` | ±2048 | 1024 | 1024 | 1024 |

**Mode-proof bare `tp` scalar ⇒ live in manual AND engaged** — the only property that can explain a manual
fault. 1 reader (`0x381AC`), 0 writers, **no monitor, no float mirror** (two-method null). Reverting is
**−6.02 dB, zero phase, and costs nothing on Path 1.** It was only *functionally* armed at V74, when the
damper it weights first became non-zero at creep.
⚠ Its gate is a **zeroing** gate, not a clamp: `|gp-0x6bd0| > 2048` drops the whole term to 0. Telemetry never
exceeded ~448, so it is always open — but it is a cliff.

---

## 7. The symptom result, quantified for the first time

Dose-response over the four builds that differ **only** in the damper cells (V72 k=0, V73 k=0, V74 k=0.5799,
V75 k=1.5798), episode-bootstrapped:

| band | slope `d ln(y)/dk` | per unit k |
|---|---|---|
| **18–22 Hz (grind #1)** | **−0.599 [−0.856, −0.348]** | **−5.20 dB — CI excludes zero** |
| **6–9 Hz (micro-ratchet)** | −0.089 [−0.350, **+0.163**] | −0.78 dB — **CI includes zero, FLAT** |

V75/V74 grind: **0.349 [0.192, 0.784]** speed-matched, **0.378 [0.201, 0.806]** speed×rate-matched;
**limit-cycle duty 0.034 — the lowest of 13 builds**, ratio **0.067 [0.000, 0.283]**. Negative controls flat
(24–28 Hz 1.071, 40–49 Hz 0.830, 1–4 Hz 0.640). Micro-ratchet: five of six statistics point down, **none clears
its own null**; absolute 6–9 Hz envelope V73 210.1 → V74 209.4 → V75 205.0.

🛑 **k required to fix the ratchet = 4.2–13.5, against the 1.5798 that hard-faulted.**
⇒ **The damper fixes the grind and cannot fix the micro-ratchet. That needs a different lever.**
★ **V75 is the first build in which the two bands decoupled**: paired ratio `(6-9)/(18-22)` = 1.18 (V72) →
1.38 (V73) → 1.40 (V74) → **2.75 [2.09, 3.72]** (V75).
⚠ **V75's dose increase is NOT established on-car at episode level** — engaged-creep bit7 duty ratio 1.347,
CI [0.052, 1.833] against a split-half null of [0.676, 1.413]. The pooled "67.44% → 82.85%" is a window statistic.

---

## 8. Refuted this session

| mechanism | why dead |
|---|---|
| **Cadence watchdog / DTC `0x18`** | It is a **boot-time reset-cause REPORT**, not a live deadline monitor. `FUN_00014b3e` never calls the DTC chain; the `FUN_00016de6(0x18,…)` call lives in `FUN_00014ba0`, gated on **reading back an NVM cause-code**, reached only from state 1 (a boot pass). **Cannot be tripped by a running task.** |
| **The probe cave's 45→68 B growth** | +17 cycles (18 → 35) ≈ **212 ns** at 80 MHz — **4–5 orders of magnitude** below any window. **EXONERATED — keep the probe.** |
| **Soft-EME / boost-floor margin erosion** | SM1/2/3 **cannot latch**: the authority-node recovery branch is a single fixed-step rise with **no bypass condition**. Margin never crosses zero (+215 clamp-sum / +481 realized). Mechanism measured near-inert (V54: authority ≤119 / 5,989 frames vs a 3,073 knee). |
| **Angle-domain plausibility as a *cause*** | The sentinel and `STEER_SENSOR_STATUS 7→4` are hard-coded consequences of a bit13 fault / `gp-0x67fa==8`. |
| **A second consumer of the FactorC/E tables** | `FUN_00034350` is the **sole reader** of all five factor/ceiling tables at all 40 modes — two methods, zero outside hits. |
| **A rate-of-change gate on `gp-0x6bd0` itself** | None exists; the 8-site census is closed. |

---

## 9. Built this session

**V77 — the candidate.** V74 base + **`0xC63A0` 2048 → 1024**, single variable.
`39990-TVA,A160-V77-V74BASE-C63A0.1024-loopgain-revert-0x13000-0x100000.rwd`
rwd `fd8db4e2ed140035782a55b2e6808bcf87a0ea85692cbe547960a13de1cfc8c5` ·
image `_v77_C63A0.1024_v74base_plain_image.bin` `a0f7c09c038931cabc419ccf79d4bb9819e647e88c0fb817ebc23cd44d102782`
**V74→V77 = 2 runs / 5 bytes**: `0xC63A1` `08`→`04` + `0xC6FFC` CRC. 50/50 CRC pass, `.rwd` round-trips
byte-for-byte, cave and all mode-24/26 records byte-identical to V74, mode 24 also identical to **stock**.
⚠ **The edit is ONE byte, not two** — `2048 = 00 08` LE, `1024 = 00 04` LE, low byte `0x00` in both.
*Count cells, not bytes.* The builder's first cut asserted a 2-byte run and correctly failed itself.

**V77B — built, unflashed, NOT recommended.** Same single revert on the V75 base.
rwd `f2c2dc0ba4f5e01bbd95925b8e42c1323a1b6b99bf658b795aa25cb2fa539dd7` ·
image `acbc218751af827d5ddc696e24d6ae44f11ef06dc04e11a3b383d366b4d4fc10`. It carries V75's engaged
configuration, which hard-faulted, and nothing has cleared that.

🛑 **Neither is clearance to fly. V77 is a hypothesis test, not a known-good** — if `0xC63A0` is not the
mechanism, it will fault too. Its weakness: V72/V73 carried the same value without a manual fault.

---

## 10. The shaping questions, answered

**The FactorC dip is ours, not Honda's.** FactorC's X axis is **vehicle speed at 64 counts/km-h** —
`[2240,3840,5120,8960]` = `[35,60,80,140] km/h`. Stock mode-26 `Y = [0,234,429,908]`, **strictly monotone**.
V74 set `Y[0] := Y[2] = 429` (dip −195); V75 raised it to 566 (dip **−332**). It is a descending ramp from
35 to 60 km/h; all builds are identical above 60.
🛑 **Monotone at `C_Y0 = 566` is arithmetically impossible** under the no-clip guard — it needs `Y[2] ≥ Y[1] ≥ 566`,
but at rate ≥ 4000 (`E = 927`) any `C > 566` gives `(C·927)>>10 > 512`, the ceiling floor; first offending speed
**80.5 km/h**. **Reachable alternative: the half-fill `[566,429,429,908]`** — dip −332 → −137, damping at
60 km/h / 21 °/s **56 → 104 counts**, `k` unchanged, passes every guard.

**FactorE `X[0]` 12 → 0 is not a no-op**, and it points the right way on both axes. Below `X[0]` the evaluator
clamps to `Y[0]` (= 0), but moving the breakpoint left raises E across all of `[0,200]` — **196 of 4001 integer
rate points change**. At the measured in-burst rate (99 ct = 21 °/s): dose **137 → 147 (+7%)** while `k` goes
**1.5798 → 1.4850 (−0.53 dB)**. Far too small to be a fault fix. It violates guard `E_X0_MIN_SAFE = 12`, whose
own stated rationale (a steep ramp starting near zero) **argues the wrong way** — `X[0] → 0` *reduces* the slope,
2.867 → 2.695 per count.

⚠ **`M = (C_Y0 · E_Y1) >> 10` is capped at 297** (`C_Y0 ≤ 566` by no-clip, `E_Y1` frozen), so `k = M/(X1−X0)`
and the best reachable at full plateau is **k = 0.7425** — still **+2.15 dB** over V74. On these two tables alone
there is no configuration that keeps V75's grind result cheaply.

---

## 11. Corrections to the record made this session

1. **`BUILD-LINEAGE.md` (~line 259)** — "all weights unity and stock ⇒ no hidden loop gain" is **FALSE** and has
   been since V72. RULE 4 class.
2. **`memory/accord-dtc-0x18-hard-eligible-cadence-watchdog.md`** — DTC `0x18` **requires a prior MCU reset**;
   it is not live-trippable.
3. **The `tp+0x74a4` off-by-`0x1000` trap, THIRD occurrence.** A stale memory still carries `0xC74A4` (= `0xEA`,
   "gated off"). `tp+0x74a4 = 0xBF000 + 0x74A4 = 0xC64A4`, which byte-reads **`0x00` on stock, V74 and V75**
   ⇒ **Monitor 2 is ARMED in every build.**
4. **`reference_accord_soft_eme_bound_arm_gating.md`** — the COMP ceiling **2560 is at `0xC67DC`**, not
   `0xC67D8` (which is 512).
5. **`gp-0x3570` is a pure unattenuated integrator**, not a 1/4-per-cycle tracker — a sustained 100-count excess
   arms SM2 in 153 ms.
6. **RULE 8b's factual claim is wrong** — route 5d contains **5–6 engaged stoplight launches** (two independent
   counts), and V74 flew them without faulting. The rule's useful core survives; the claim does not.
7. **"The new cut keeps ~99% of V75's grind benefit"** — it delivers **48%** at the measured in-burst rate, and
   the dose-response predicts it gives back **1.63× [1.33, 2.01]** of what V75 bought.
8. **`STATE.md` / the golden model's "FactorC damping already flashed and falsified"** — stale, void under
   RULE 7. The approach was never tested until V74.
9. **The `0x1AB` DTC-active flag is not a narrow 3-group test** — `FUN_00046ea6(3)` and `(4)` are structurally
   dead (no fault_id carries those bits); the flag collapses to **bit10, which 75 fault_ids carry**, including
   40 of the 43 EPS-disabling ones. It is a fault-*class* indicator.

---

## 12. Open, in priority order

1. 🛑 **Rlogs from the V74 bump fault.** V74's probe reports `bit7 = (gp-0x6bd0 != 0)` and
   `bits6:3 = gp-0x67fa & 0xF` on `0x14A` byte 4 — it would say directly whether the damper was live and what
   state the ECU entered. Route `5e` gave us V75's fault to the frame; this would do the same.
2. **`FUN_0003b8f6`** — the `gp-0x6b98` re-entry that closes Path 2 inside the firmware. It may be the loop's
   dominant gain term and **`0xC63A0` does not touch it**. Byte-read `tp+0x50d4/0x50d8/0x504c/0x5050/0x50bc/`
   `0x50d0/0x50d2/0x50d6/0x746e` and quantify it.
3. **Discriminate fid 28 vs fid 29** on-car. The lookup primitive `FUN_00047d06(fault_id, 1)` is pure and
   read-only and returns `0xffff` when the id is not in the live log — a 5-bit cave can test 28, 29 and 24
   directly, **with `gp-0x67fa == 5` as the positive control** (this kit has been burned three times by probes
   whose null was on the gate).
4. **A different lever for the micro-ratchet.** The damper is flat on 6–9 Hz and V75 showed the two bands are
   separable.
5. **A DTC re-read** against this morning's baseline, now that a second fault has occurred. `19 02 FF` is proven
   on this ECU; `19 04` / `19 06` freeze-frame and extended-data are untested here and may return NRC 0x12.
   🛑 Operator confirmation of exact payload and bus required; nothing was sent this session.

---

## 13. Artifacts

Scripts: `analysis-2020accord/v75fault_{extract,timeline,analysis,followups,oscillation,final,buschange,flags,lastmile,bitmap}.py`,
`v78_surface_{tables,blastradius,designspace,plots}.py`, `v78_symptom_{cache,lib,census,score,limitcycle,falsifiers,null,matched,dose,perception}.py`,
`build_v77_tva.py`. Caches: `_cache_r5e/`, `_cache_r5e_sym/`. Plots: `analysis-2020accord/plots/v78_*.png`.

⚠ **Two traps for the next session.** `decode_v75_probe.py` / `decode_v74_probe.py` **do not exist** despite
being referenced. And `v75fault_{timeline,analysis,followups,oscillation}.py` split on `t < 284.795`, which
**includes the fault sample itself** (angle/rate = `0x7FFF`) — their `rate_c` numbers carry one sentinel spike.
**`v75fault_final.py` / `v75fault_buschange.py` use a strict index split and supersede them.**

⚠ **Environment:** the anaconda **base** env has a broken numpy and no `capnp`. Everything ran under
`C:\Users\dudei\anaconda3\envs\bin_decompile\python.exe`.
