# HANDOFF 2026-09-04 — the acceleration frame, the rack map, and three retracted numbers

**Read `docs/STATE.md`'s decision box first.** This narrates *how* the session got there and, more usefully,
**which numbers died on the way** — three headline figures were retracted, two of them mine.

---

## 1. What the operator asked for, in order

1. Read three V283 routes. *"This firmware consistently oversteers. I don't like the idea of the
   integrator anyways — an integrator on steering angle rate is just steering angle, which would NOT be
   used in a PID loop on angular acceleration."*
2. *"We should keep Kp fixed, if not 0… Ziegler–Nichols tuned PID loop for angular acceleration…
   set Kp=0, then increase Kd to get Ku."* **Frontier firmware: V282.**
3. *"Do we really need dE? Don't we have a working view already… in our rlogs?"*
4. *"Implement the variable steer ratio logic and mapping for the Honda Accord… ignore the steer ratio
   setting toggle from galaxy"*, plus suggested friction / lat-accel / KP values.
5. *"Commit and push my fork… then ssh into my comma and switch to my fork."*
6. *"I do not want overshoot, or if we have overshoot, I want it minimized with minimal ringing."*

---

## 2. 🛑 THREE RETRACTIONS — read these before trusting any number from earlier today

| retracted | by whom | what replaced it |
|---|---|---|
| **`Ku ≈ 143–151`** | orchestrator | Built on a **7.3 Hz** figure read as 20 Hz. VOID. |
| **`Ku = 859`** | `zn285`, its own | A *real* quantity — the Kd where the 7.3 Hz ring's **magnitude** hits 1 — but not Ku, because a Nyquist −180° crossing at **27–32 Hz arrives first**. |
| **folded fraction ≤ 22–33 %** | `task5rate`, its own | Its own control killed the monotonic-decay premise. **The folded fraction is NOT bounded by anything measured.** |

**Also corrected:** *"removing P removes ~90° of lag"* is **backwards** — P is phase-**flat**, so removing it
**adds** lead (+52° at 7.3 Hz, +25° at 20 Hz). And `0.976 [0.944–0.990]` is the **7.3 Hz strong-turn ring**,
not the 20 Hz grind; **the 20 Hz ring has no usable measured loop gain at all** (`L_in(line) = −1` by
construction at a spectral line).

---

## 3. The physics that now organises everything

**The frame mapping** (`docs/research/PID-FRAME-SIZING-KP-KD-2026-09-04.md`): in the acceleration frame
openpilot actually commands, **our D is the PROPORTIONAL gain and our P is the INTEGRAL gain**; our I is a
double integral. Corner 9.64 Hz, `|D|/|P| = 64·(Kd/Kp)·sin(πfT)`, `Ti = Kd/(31.25·Kp)`.
🛑 **The raw cell values are not comparable** — `Kd_cell = Kp'·8000`, `Kp_cell = (Kp'/Ti)·256`.

**`Ku ≈ 227` [217–270], `Tu ≈ 36 ms`**, anchored on a **measured** gain margin (`CREEP-20HZ-LOOP-ID` bar-IV
rows, `1.75× @ 23.4 Hz`; ⚠ only that estimator family finds a crossing at all).

⭐ **`Kd ∈ [118, 227]` — bracketed from BOTH sides**, and the asymmetry is what matters:
> The **measured `|L| = 0.976 < 1` at Kd 128 proves we sit BETWEEN the roots**, and that is
> **`s`-INDEPENDENT** — `s` enters the *inferred* root locations, not the *measured* `|L|`.
> ⇒ **A Kd RAISE moves away from the floor; a Kd CUT moves toward it.**

**Every low-overshoot ZN variant is structurally unreachable**: ZN-no-overshoot (Kd 54), ZN-some-overshoot
(Kd 89) and Tyreus–Luyben (Kd 84) all land **below the floor**, where the ring re-arms. This loop has a
*minimum* gain, which textbook recipes do not anticipate.

| tune | Kd / Kp | ring | GM |
|---|---|---|---|
| today | 128 / 248 | 1.000 | 1.77× |
| **Kd 160** (candidate F ≈ ZN-PID's Kd 162) | 160 / 248 | **0.932** | 1.48× |
| classic ZN-PI | 122 / 148 | 0.936 | **2.01×** — costs 25 % of DC authority |
| classic ZN-PID (full pair) | 162 / 329 | **1.013** | 1.39× — at both edges |

---

## 4. The `dE` question — the operator was right, and the answer is an ENDPOINT

`task5rate`: the 0x18F rate channel is **NOT band-limited** (PSD rises monotonically to Nyquist, 1.8–4.8×
on all five routes; frame loss, leakage, an fs/2 producer and a transport artefact each excluded by its own
control). But the risk **splits by endpoint type**:

- **ENERGY endpoint — SAFE.** No anti-alias filter anywhere, so folded power arrives **unattenuated**:
  aliasing destroys the frequency **label**, not the **energy**. A destabilising mode cannot vanish.
- **FREQUENCY endpoint — UNSOUND.** "The mode is at 27–32 Hz so PM there is X" could equally be 68–73 Hz.

⇒ **The 1 kHz `dE` cave is permanently retired.** Score any Kd change on **0–50 Hz energy**, reporting the
**33–49.9 Hz folded shelf** as its own band. ⚠ Engaging LKAS raises true **>50 Hz** content **1.4–3.4×** —
that content is driven by our own loop, and a loop-driven resonance at 68–73 Hz is exactly what a raised Kd
could create. The IMU cannot help (101.01–101.03 Hz ODR, 0.51 Hz headroom — structurally underpowered).

---

## 5. Firmware state

- **V285 BUILT — bench config, DO NOT FLY.** V282 + Kp slot 7 → 0. `7c2cfef7…9605d2` / rwd `83079d43…a652e`,
  444/444, **9 bytes** (248 = `0x00F8`, only the five low bytes change). **Zero steady-state lane keeping** —
  type-0 plant, `dE=0 ⇒ D=0 ⇒ S=0 ⇒ L(0)=0`, verified three ways. Divide-by-zero answered NO exhaustively
  (all 17 divisions divide by an X-segment width; no Y is ever a divisor).
- **V284 SHELVED.** At the correct frequency it drives the 7.3 Hz ring **above unity** (1.106 at idx 68,
  1.277 at its peak) against 2.5 % headroom. The original framing understated it ~10× and named the wrong symptom.
- **V286 SPECCED, NOT BUILT** — V282 + Kd 128→160 + a 2-level `|r24|` ladder on 0x14A bits 3/7 (a *sacrifice*
  of two legacy probe bits). **Needs the full adversarial pass.** Open pre-flash item: place the thresholds
  from the **bit-6 duty against the measured `|T|` distribution**, not the placeholder 16/64.

**Cave findings worth keeping:** 1048 spare `0xFF` bytes at `0xC4BD8`–`0xC4FF0` · `gp-0x683c` dead (0 hits,
positive controls at 14/11) · the PID publishes P/D/sum/output/E_prev at `0x2A17C`–`0x2A1A2` ·
🛑 **`FUN_00028ea6` reuses `lp` as scratch** (`0x28EBC`), so a `jarl` at `0x29EE4` would corrupt a live gate
**every tick** — use `jr`.

🛑 **The 427 spare bits are UNUSABLE from the cave — ordering, not the checksum's existence.** `0x57b24` is a
**pure function** (returns the checksum, no store, no send). On 0x14A the cave writes and the checksum is
computed **three instructions later in the same critical section**; on 427 our 100 Hz write would land
*after* its 50 Hz packer stored the checksum. That is why 177 builds on 0x14A were safe.

---

## 6. openpilot side — DEPLOYED

**The rack is variable-ratio, measured** (operator's own artifact: 427 min / 47 routes, four independent
estimators, speed control passed): flat **≈16:1 to 48°**, quickening to **≈11.1:1** at lock.
⭐ `14.0/16.33 = 0.857` is **exactly** the old constant — i.e. StarPilot shipped *the rack at ~95° applied at
every angle*.

**Pushed to `raayyymond/StarPilot` `Dom` as `5f50a6c01`**; device origin switched, `UpdaterTargetBranch=Dom`,
`AutomaticUpdates=0`. The patch **assigns** `sr` from the map rather than scaling `lp.steerRatio`, which makes
the learner and the toggle inert by construction and kills the 16.33 trap. Operator's six EPS-telemetry
commits preserved under tag **`eps-telemetry-backup-2026-09-04`**.
🛑 **Test suite NOT run** — `pytest selfdrive/controls/tests/test_latcontrol.py -k honda_accord` on the device.
🛑 **Guard after every sync:** `grep -c "sr = get_honda_accord_steer_ratio(" selfdrive/controls/controlsd.py` must be **1**.

**Tune** (`docs/research/TUNE-FOR-V282-2026-09-04.md`): friction **0.03 keep** · LatAccel **2.11 now / 2.53
after the map** · **SteerKP 0.6 → 0.8**. **The double-count trap does not bite** — the integrator never
saturates, so the DC equilibrium is `SR_param/sR_true`, a **gain-free** expression; gain never compensated the
bias, so nothing reverts. **Lowering LAF is a category error** (it scales f/p/i/d *and* the PID limits
together). The 3.9 Hz target no longer exists on this build class (dominant line is 1.95–2.29 Hz).
Expect **~0.85 of the ask, not 1:1** — but 🛑 **that is NOT a pass/fail criterion for the map.**

🛑 **THE SR MAP IS AN UNCONDITIONAL KEEP (operator, 2026-09-04: *"SR is a definite keep for sure"*), and the orchestrator framed this WRONGLY at first.** It is **not a tuning change to be validated on a drive** — it is a **correction to a measurement that was wrong**. The vehicle model was reading curvature through a single ratio that does not exist on this rack (12.5 ≈ the rack near LOCK applied at every angle; the stock 14.0/16.33 ≈ the rack at ~95° applied at every angle — both truthful somewhere the car is not being lane-kept). **Everything downstream — the error, the integrator, every gain anyone would tune — is computed against that measurement**, so the map is correct independently of how the drive feels. Presenting a "0.85 vs 1:1" expectation as an acceptance test set up a criterion under which a correct change could be reverted for feeling wrong. **Do not score the map. Score what REMAINS once the measurement is honest**, and send each residual to its own home: the ~4 % geometric-vs-effective gap → **tyre stiffness in `carParams`** (never by scaling the rack map by 1.04, which launders a tyre-model error into a geometry table); EPS low-demand droop → firmware; convergence speed on the 2 s error runs → `SteerKP`/`KI`.

🛑 **`liveParameters.steerRatio` is published UPSTREAM of the Accord scale** — **r31/r32/r33 all ran an
effective ratio of ~14.05** while the wire reported 16.38–16.51. Anything derived from openpilot's `error` on
those routes carries a 1.21× inflation.

---

## 6a. Deployed and verified ON THE CAR (end of session)

**The Galaxy update was taken and the patch is in the running tree** — verified over SSH:
`origin = github.com/raayyymond/StarPilot.git` · `head = 5f50a6c0` · version `0.11.2 / Dom / 5f50a6c / Sep 03` ·
call-site guard **1** · stale symbols **0** · the knot arrays present in `latcontrol_vehicle_tunes.py:85-86`.
Params unchanged: SteerRatio 12.5 (now inert for the Accord), SteerKP 0.6, SteerLatAccel 2.11, friction 0.03.

**Second commit pushed, `8a28dcef8`: the `SteerLatAccel` ceiling raised 1.5× → 10×** the platform default
(`starpilot/common/starpilot_variables.py`, new `LAT_ACCEL_FACTOR_MAX_MULT`). Accord ceiling **2.534 → 16.890**.
Raising only the MAX is safe by construction — `output_torque = output_lataccel / latAccelFactor`, so a larger
value commands LESS torque; the 0.5× min guard (the dangerous direction) is untouched. **Requires another
device update to take effect.**

🛑 **LAF target — do NOT jump to the measured truth.** `LAF_true ≈ 12–15` vs the live 2.11, so the
feedforward over-commands **6–7×** and the integrator burns **86 %** of its range cancelling it. But LAF divides
the **whole** controller output, so loop gain scales as `LAF_true / LAF_param` — going straight to 13 is
simultaneously a correct FF fix and a **6× loop-gain cut**, and no measured outer-loop margin justifies that in
one step. **Step it: 2.53 → ~4 → 6 → 9 → 13, one per drive.** Stop when `i·sgn(f)` on straights stops shrinking
(today **−0.242**, target ~0). Guard: the **1.9–2.3 Hz** PSD must not rise.

**🛑 THE DRIVE ORDER, as given to the operator:** V283 was last flown (r36/r37/r38); **flash V282 first if it
still is**, because V283's integrator over-delivers in curves and would confound the SR reading — the same
reason `tune282` excluded the V283 routes from its equilibrium analysis. Then **drive V282 + the SR map alone**.
That one drive scores the map, supplies the SteerKP criterion, AND establishes the baseline V286 is measured
against. Only then cut and fly V286.

---

## 7. Next session

1. **Score the SR drive.** Criterion for adding SteerKP 0.8: count one-signed error runs ≥1.0 s with
   `|err| > 0.10` in the straight mask — today 27 runs / 95.5 s / 49 % on r35. Guard: **1.9–2.3 Hz PSD must not rise.**
2. **Place the V286 thresholds** from the bit-6 duty × measured `|T|`.
3. **Adversarial pass on V286**, then cut it.
4. **Then decide ZN-PI (122/148)** — needs the measured floor to clear Kd 122.
5. 🛑 **`STATE.md` is ~201 KB** — under the 256 KB hard cap, over its own ~150 KB target. **Split it.**
6. Open, unclaimed: **what the engagement-gated >50 Hz content actually is**; **`0xC61C0/C2/C4`** (6 bytes
   blanked to `0xFFFF` since V36, 249 images, **12 readers / 0 writers, unexplained**); **Task 5's true rate**
   (OSTM1 excluded; TAUA0/TAUA1 and an INTC mask scan untried).
