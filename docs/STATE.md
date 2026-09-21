# STATE — living current state of the kit

> 🛑 **READ THIS BOX FIRST.** Everything you need to make a decision is in this box. The superseded decision
> boxes and the 84 finding/correction blocks that used to follow it are ARCHIVED under `docs/archive/` (pointers
> at the end of this file). They are a record, not a briefing; nothing was retracted by the moves.

## ✈ THE DECISION, IN ONE PLACE — updated 2026-09-20 (**V294 BUILT, NOT FLOWN — the candidate. V293 stays on the car until the operator decides. V294 = V293's torque map, byte for byte, + a 1 kHz ACCELERATION trim through the stock PID's own P gain (two in-place opcode halfwords `0x28FA4 add→subr`, `0x29D76 shl 5→2`; fb clamp 0→1024, fb-lag pole 923→1011 = 2.0 Hz, b 1560→567, Kp 120→960 ×28). Adversaries A + B PASS. The fork is REVERTED: every torque-mode term defaults off in Dom `54ff1ea39` + `toggle-config_V294_accel-trim_r1.json`. Nothing flashed, no CAN sent.**)

> 🛑 **THE VERDICT (2026-09-20): V294 IS THE CANDIDATE; THE DECISION TO FLASH IS THE OPERATOR'S.** The operator's call: *"the delay kills the idea of a torque mode only control … a PID + feedforward which track acceleration, not rate/velocity … revert all torque mode changes in this next StarPilot update … anticipate grinding and stuttering (relying on feedforward/torque mode as much as possible)."* **What V294 does:** `r26 = clamp(s_new − s_old, ±1024)` — the per-tick change of the lag-filtered wheel rate = the wheel's acceleration through a 2.0 Hz low-pass; `E = 4·sp − r26`; `P = (E·960)>>8 = 15·sp − 3.75·r26`: V293's feedforward EXACTLY (asserted at all 241 demand indices and for every 32-bit sp) minus a trim bounded at 25 % of the rail. Kd 0, D clamp 0, Ki 0, r24 2048, map, tap, cave unchanged. **Why acceleration and why 2 Hz:** with T = −K·H·α and H a lag, every degree of loop lag turns the trim into damping (delayed RATE feedback anti-damps past 90°, V282's 20 Hz crossover resonance); at K_α/J = 1 the wheel mode's ζ goes ×1.02 / 1.16 / 1.49 / 1.82 / 2.05 across 5–26 m/s at a 2 Hz pole (×0.81…1.28 at the stock 16.5 Hz pole — worse at low speed), and the 20 Hz gain sits **−26.7 dB** below the loop V282 ground on. In the 2–3 Hz band the trim is ~97 % damping: **1.85 T counts per deg/s** of wheel rate = a damper comparable to the wheel's own; the 25 % cap binds only above ~230 deg/s. **Image** `3143616d5b79bdb7648d8e4d32e48420c7b481b18325178e89d1853589dbdd85` · **rwd** `a2b418f061160f66…` (exactly one on disk) · script `build_v294_tva.py` (159 assertions, 20/20 mutations caught, zero-edit control reproduces V293) · design `studies/v294/v294_design.py`. **2026-09-21, adversary C (Ghidra):** C1/C2/C4/C5 PASS from the decompiler; its C3 FAIL (x = 1.0–1.7 counts per deg/s) is WITHDRAWN on the wire — three V292 routes with the rate loop live read **x = 7.1–7.8 counts per deg/s** (`studies/v294/x_scale_from_v292_wire.py`), so the design's 8 is EVIDENCE and V294 needs no re-cut. **Adversarial pass:** A (arithmetic/sign/scale: four sign legs, the FF identity for every 32-bit sp, int32 4.06×, the −26.7 dB re-derived) and B (build audit/interlocks: independent rebuild reproduces the hash; every changed cell private and in FLASH; the 0x14A cave reads the delivered torque, not the PID cells; no governor/EME reader; V293's D1 survives) both PASS; six non-blocking defects, four fixed in the script, one a record erratum (`gp-0x6a56` has 29 accesses, not 30). **The one new behaviour to know before the drive:** up to 616 counts of lane torque at ZERO command while engaged, opposing wheel acceleration (V293 delivers 0 there; V282 flew 2463). **Next drive** (V294 + the r1 config, `SteerFriction 0.011` checked in initData first): `residual = T_tap − FF_V293(idx)·taper` regressed on −(0x18F rate, 2 Hz low-pass, differenced): slope ≈ +1.85 T counts per deg/s and the FF identity R² ≥ 0.98 = LIVE, RIGHT SIGN; flat = not live; **positive correlation = SIGN INVERTED → stop, revert to V293** (`…_REVERT_to_V293_r64.json` restores the fork). Outcome the operator scores: hard-turn jerk and the 1.6–3 Hz wheel-rate energy, predicted down; any new line in 5–30 Hz is the revert signature. Handoff: `docs/handoffs/2026-09/HANDOFF-2026-09-20-v294-acceleration-trim-built-fork-reverted.md`. **Page:** https://claude.ai/artifact/BcuAb3dgHP84oasqeadVBs.
>
> *(superseded 2026-09-15 box, kept for the record:)* **V293 stays. REV 4 FLEW (route `00000075--6c8687d5bd`, 803 s engaged, `Dom 08a5a706`): the Ki schedule fixed the tracking GAIN at speed (0.74–0.80 → 0.97–0.98) but the planner error is still 20–30 % of the signal, 50–70 % of it below 0.3 Hz, the integrator carrying a third of the torque; the hard-turn jerk is the lightly damped 2–2.7 Hz closed-loop wheel mode (bursts every 0.53 s, command +6.9 dB at 1.95 Hz). FIX = FORK REV 5 (`Dom e44b6cd31` + `toggle-config_V293_torque_mode_r5.json`): a model-based DISTURBANCE OBSERVER (`AccordDobHz` 0.6) added to the feedforward, Ki 0.3 flat (schedule OFF), Kp 1.0, Kv 1e-3, rate filter 0.03→0.01 s, the observer on the wire. Deployed to the device (pulled, params rebuilt, 22 keys written, rebooted). Nothing flashed, nothing sent.** Previous verdict, 2026-09-14 evening: REV 3 FLEW (routes 72 + 73): route 72 ran rev 3 as written and was "loose" at speed because the LOOP (Ki 0.6 / LAF 14, ~1.4 s) could not absorb a hold feedforward that is wrong by 20–70 % from road to road; route 73 secretly ran `SteerFriction 0.212` — the fork's stock-param sync back-filled the config's explicit 0.0 — a 10×-Kp relay that tracked 2.5× tighter and chattered at 4 Hz ("jerky on hard turns"). FIX = FORK REV 4 (`Dom` `f4e314da6` + `08a5a7064`): speed-scheduled Ki (`AccordTorqueKiHigh` 2.5 from 18 m/s, 0.6 below 8), the relay OFF under the hysteresis FF, the stock-sync fix, the 28 m/s hold knot ×1.2 + `toggle-config_V293_torque_mode_r4.json`. Deployed to the device (pulled, params rebuilt, 21 keys written, rebooted; tests pass on the comma). Nothing flashed, nothing sent.**)

**ON THE CAR: V293** — torque mode (cal-only on V282; **image**
`f75e77cf0ba9d93b5302196877e59c6a41deae4983afc09ade99c5b766e1db17` · **rwd** `ac4723865378ff37…`, exactly one on
disk). **FLEW 2026-09-13, route `75604b0a432fdc89_00000070--717f5a7866`** (18:12–18:31, 19 segments, 858 s
laterally engaged, fork `Dom` `4247cb09e`, rev-1 toggle config confirmed in `initData` **and** by the 100 Hz
`torqueState.p/error` read = **0.3000**). 🛑 **The dongle counter RESET on 2026-09-13 — routes `6c`–`70` are NEWER
than the cached `a6`, and `00000070` was reused from an August route; key everything on the full `counter--hash`.**
The edit-live identity **HOLDS** (|427 tap| vs the image surface **R² 0.986**, resid 22 counts, sign(T) = +sign(cmd)):
the EPS rate loop is dead on the wire.

> 🛑 **THE VERDICT (2026-09-15): V293 STAYS IN THE CAR; THE FORK GOES TO REV 5 — THE DISTURBANCE OBSERVER.** Route 75
> (`75604b0a432fdc89_00000075--6c8687d5bd`, 2026-09-14 22:43–22:57, rev 4 attributed on the wire: `08a5a706`/Dom, Kp 0.8500, LAF 14.0000,
> `AccordTorqueKiHigh 2.5`) — the operator: *"still a little loose; still jerky on hard turns; not as smooth, confident and well-controlled as the
> 1 kHz inner loop; the command has to overshoot to get over friction."* The wire (vs route 72, rev 3): tracking gain 15–22 / >22 m/s **0.80 / 0.74 →
> 0.98 / 0.97**, turn hold >22 m/s 0.75 → 0.99 — rev 4 did its job — but rms error is still 0.19–0.30 of the signal, **49–69 % of it below 0.3 Hz and
> 17–34 % in 0.3–1 Hz**, and the integrator carries **0.29–0.33** of the torque. **The hard-turn jerk is the lightly damped 2–2.7 Hz closed-loop wheel
> mode**: at v<10 the wheel moves in 0.12 s bursts spaced 0.53 s, the torque command has a +6.9 dB line at 1.95 Hz; at 10–20 m/s des→act |H| = 2.28 at 2 Hz
> (coh 0.99). Zero stiction dwells. **Plant damping by speed: the free fit gives b 0.0005–0.0009 torque/(deg/s) below 15 m/s on BOTH drives** (the rev-3/4
> "mode" world) and ~0.004 only above 22; the 09-13 ident's b is BELIEF below 20 m/s. **Why a 100 Hz loop cannot linearise friction here: the ~60 ms round
> trip, not the rate** — static stiffness 1 + Kp_t/k = 1.7; a rate damper's phase −(ωTd + atan ωRC) crosses −90° at ≈2.8 Hz (RC 0.03) so it damps below and
> pumps 3–5 Hz (the +2.6..+4 dB hump on every drive). **Rev 5 (fork `e44b6cd31`, `toggle-config_V293_torque_mode_r5.json`):** `HondaAccordDisturbanceObserver`
> — w = hold(θ) + b(v)θ' + Jθ'' − u(t−0.06) from the measured wheel state and the controller's own delayed output, two poles at `AccordDobHz` **0.6**, clip ±0.3,
> fade 3→6 m/s, held while safety-limited / driver holds, reset on engage, ADDED to the feedforward; the model's b is the fork's 1/G(v) ON PURPOSE (below the
> corner it installs the model's damping whatever the plant has; above it the mismatch de-damps the 2 Hz mode — the reason for 0.6 not 0.8). Ki **0.3 flat**
> (`AccordTorqueKiHigh 0`), Kp **1.0**, Kv **1e-3**, `HONDA_ACCORD_RATE_LOOP_RC` **0.01** s. Sim (five worlds: b ×0.15–8, hold ×1.5, delays ×1.5, J ×1.5), speed-
> averaged: planner-step overshoot 0.51 → 0.20, 0.03-torque disturbance |e|@1 s 0.074 → 0.029, hard-turn hold error 0.219 → 0.086 m/s²; cost +9..+22 % 1.6–3 Hz
> wheel-rate energy in hard turns IF the plant is the lightly damped one; the one loss = hold ×1.5 at 19–26 m/s where rev 4's Ki 2.5 winds faster.
> **Rejected with numbers:** Kp 1.2/DOB 0.8 (+40..+150 % mode energy, rang with delays ×1.5) · observer model b 0.0006 (hold error 0.5–0.8 in the identified
> world) · a model-PREDICTED rate damper (DIVERGENT at 26 m/s under b mismatch, T3 179–462°, and biased in stiction) · notch ×1.35 (unstable) · dither (not
> proposed: sits on the 7 Hz ripple). **Wire instrument:** `starpilotLateralState.accordObserverTorque/.accordObserverFrozen` (@8/@9); the kit's flight read
> decodes and prints them. **Device:** pulled to `e44b6cd31`, params rebuilt (`AccordDobHz` known), 22 keys written and read back, rebooted 00:38; schema and
> observer import on the device. Tests on the comma: 254 pass, 2 pre-existing (Bolt/Palisade). **`SteerFriction` read 0.212 on route 75 after 0.0 on route 74
> 20 min earlier** (both post-fix): the file was rewritten ~30 s into a boot (mtimes of boot-time writes on this device read 2026-07-28 08:05 — the clock is not
> yet set), a Sonnet trace found no writer whose blast radius matches, an offroad reboot tonight did NOT back-fill (0.0 survived) → the remaining suspect needs
> ignition-on; functionally moot (relay off under `AccordFrictionHyst`), the flight read flags it. **Next drive: `v293_flight_read.py <tag> --config …_r5.decoded.json`
> then `v293r5_observer_read.py <tag> r75_v293r4` (pre-registered O1–O5 in its docstring); revert = `_r5_REVERT_to_r4`; if O2/O3 pass and O4 (jerk) fails →
> `AccordDobHz 0.4` / `SteerKP 0.85` by CONFIG.** Handoff: `docs/handoffs/2026-09/HANDOFF-2026-09-15-v293-rev4-flew-r75-rev5-disturbance-observer.md`.
> **Page:** https://claude.ai/artifact/8Bc1Xqt9qeFhsDLbayqK2H (signal flow with the observer drawn, Q(f), Re Q, the damping budget, step/disturbance/hard-turn
> traces before/after, the Ki/Kv LERPs, the robustness table, the risk, the pre-registered read).
>
> *(superseded 2026-09-14 evening box, kept for the record:)* 🛑 **THE VERDICT (2026-09-14 evening): V293 STAYS IN THE CAR; THE FORK GOES TO REV 4.** Routes 72 + 73 (rev 3, `e8e62f0e1`, Kp 0.8500 /
> LAF 14.0000 on the wire) — the operator: *"better than rev 2; still feels a little loose; still jerky on hard turns; still doesn't feel as good
> as the 1 kHz inner loop did."* The wire: **route 72** planner-tracking gain **0.80 / 0.74** at 15–22 / >22 m/s, lag **0.5 s**, |H|(0.2 Hz) 0.66–0.76,
> 79–83 % of the error below 0.3 Hz, the feedforward supplying 68–76 % of the torque and P+I the rest in the SAME direction — the rev-3 map
> under-delivers at speed and the I loop is too slow. The map's level error is ROUTE-DEPENDENT (×1.1–1.25 on its own fitting routes 70/71,
> ×1.3–1.7 on 72/73, left/right ×3 apart on 73): only the integrator can carry it. **Route 73 ran `SteerFriction = 0.2120497` (stock)** because
> `_sync_stock_param` treated the config's explicit 0.0 as UNSET — relay rms 0.095 torque, 239 flips/min, gain 9.9 vs Kp 0.85: rms error 2.5×
> lower but a 3.8–4.7 Hz chatter line, 66 rate reversals/min, 21 % of hard-turn frames at the Honda rate cap. Rev 3 did what it was for (no
> 2.34 Hz cycle, no 2 Hz line, low-speed rate roughness 47 vs 60/86 deg/s). The operator turned live delay learning on himself (0.274 s).
> **Rev 4 (fork `f4e314da6` + `08a5a7064`, `toggle-config_V293_torque_mode_r4.json`):** `AccordTorqueKiHigh` 2.5 (Ki schedule 0.6 below 8 m/s →
> 2.5 from 18; flat 2.5 rings the 1 Hz mode 16–36° at 5 m/s) · the SteerFriction relay dead under `AccordFrictionHyst > 0` · an explicit 0.0 is
> never back-filled · `HOLD_K_V[28 m/s]` 0.0134 → 0.0160. Simulated: 2 s residual of a 0.03-torque bias at 19–26 m/s 0.11–0.12 → 0.005–0.013 m/s²,
> Ms 1.75 unchanged. Rejected with numbers: Kp 1.1/1.6, Ki 2.5 flat, ref 0.08, map ×1.3. **Device carries it** (`/data/params/d` read back;
> `SteerFriction 0.0` survives the start-up sync). Tests on the comma: 72 pass + lateral 193/195 (2 pre-existing). **Next drive: check
> `SteerFriction 0.0` in initData FIRST**, then `v293_flight_read.py … --config …_r4.decoded.json` + `v293r3_read.py <tag> r72_v293r3`; success =
> gain 0.95–1.05, |H|(0.2) ≥ 0.9, lag ≤ 0.3 s at 15–30 m/s; a 0.3–0.8 Hz hunt → `AccordTorqueKiHigh 1.5`; else the `_REVERT_to_r3` file. The
> residual (the first 0.5 s after a disturbance, delay-limited) is the 1 kHz EPS loop's — firmware is the next lever only if rev 4 tracks and he
> still says "not confident". Handoff: `docs/handoffs/2026-09/HANDOFF-2026-09-14-v293-rev3-flew-r72-r73-loose-is-a-slow-loop-rev4-ki-schedule.md`.
> **Page:** https://claude.ai/artifact/MS72a2oMecgGmj4x2yqsGg (signal flow with the edits, Ki / hold-map / relay LERPs before and after, the
> simulated disturbance recovery, the risk).
>
> *(superseded 2026-09-14 morning box, kept for the record:)* 🛑 **THE VERDICT (2026-09-14 morning): V293 STAYS IN THE CAR; THE FORK GOES TO REV 3.** Route 71 (rev 2: `66cf4454a` +
> the rev-2 config, attributed on the wire: Kp 0.8500, LAF 14.0000) — the operator: *"does not feel like StarPilot has
> accurately modeled my EPS + car dynamics"*, *"loose on most straights or slight bends"*, *"on hard curves at low speed
> the steering wheel jerks to correct itself"*, *"at high speed … worse and with more oscillation/resonance"*. The wire:
> a **2.34 Hz, ±6° limit cycle** on every sustained curve above 20 m/s (rate +22.5 dB, cmd ±300 counts, the relay
> flipping every half cycle); **20 rate bursts/min** of 84–442 deg/s in low-speed hard curves (stiction → ramp → snap,
> the honda limiter capped); tracking gain **0.83 / 0.93 / 0.99 / 1.12** by band; the scorer's ratchet REVERT trigger
> fired (dwells 9.1 vs 4.6 /min at 10–20). Re-identified: the steering system has a **mode at √(k(v)/J)/2π = 1.0–2.1 Hz,
> J ≈ 8e-5 torque/(deg/s²), ζ 0.2–0.35**, and the loop delay is ~60 ms (3 + 13 + 30–45 ms measured); the static hold
> torque is a **saturating spring** (0.020 static friction + k(v)·sat(v)·tanh(θ/sat)), ×3–5 the rev-2 tables below
> 10 m/s at 5–35°, ×0.6–0.7 above 17–25 m/s. **Rev 3 (fork `e8e62f0e1` + `toggle-config_V293_torque_mode_r3.json`):**
> `AccordHoldMap` (the measured map) · `AccordFrictionHyst` 0.015 (hysteresis on the desired angle; `SteerFriction` → 0)
> · `AccordRateLoopGain` 0.0006 (the 100 Hz inner loop, tapered above 12 m/s) · `AccordErrorNotchQ` 1.0 (notch at the
> mode) · `AccordRefFilter` 0.12 · `AccordTorqueKi` 0.6. Simulated on the identified plant: no cycle over b / J / delay
> ×1.5 / spring ×0.7–1.4; step overshoot 80–110 % → 30–45 %; Ms 4–30 → 1.9–2.6. **Order: fork, REBUILD PARAMS, config,
> restart** (`docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md` §0). Handoff:
> `docs/handoffs/2026-09/HANDOFF-2026-09-14-v293-rev2-flew-2hz-limit-cycle-rev3-hold-map-rate-loop.md`. **Page:** https://claude.ai/code/artifact/08d2f4e0-44b8-43a0-9fb8-128eedef58e0
> (signal flow, the hold-map and loop LERPs before/after, the simulated consequences, the risk). Tests PASSED on the comma (2026-09-14, /usr/local/venv python + pytest in /data/pytest_site): 14 Accord lateral tests, 25 Galaxy layout tests; the whole lateral file 190/192 — the two Bolt/Palisade failures pre-exist on 66cf4454a. The device already carries e8e62f0e1 + the rev-3 params (read from /data/params/d).**
>
> *(superseded 2026-09-13 night box, kept for the record:)* 🛑 **THE VERDICT (2026-09-13 night): V293 STAYS IN THE CAR. The operator's score, verbatim — *"I did not
> experience any classic grinding or stuttering."* · *"steering felt ratchety, like the wheel did not move smoothly
> but only snapped between angles rather than smoothly moving between them"* · *"Sometimes steering felt loose and
> then sometimes there was oversteer and other times on hard transients, it would overshoot then correct
> slightly"*. The bands are the instrument (18–22 Hz ring present in 1.1 % of windows vs 9.8–20.9 % on every earlier
> build, amplitude ×0.43; F7 0.00; tap ripple ×0.10); NOTHING is "fixed" — he scores the symptom. Every one of the
> four new symptoms traces to the FORK'S MODEL of the plant, not to the firmware: V293 left a SPRING + Coulomb
> friction (torque → angle) and StarPilot modelled one lateral-accel gain at every speed with no friction. The fix
> shipped this session is the fork side ONLY — plant tables re-identified in fork code (`Dom` `66cf4454a`) and a
> rev-2 Galaxy toggle config (`toggle-config_V293_torque_mode_r2.json`: plant FF on, friction 0.011, LAF 14,
> Kp 0.85, Ki 0.30, learned offset off). The next drive is HIS to score; its instrument is `v293_flight_read.py`
> v2 with the four symptom rows pre-registered against route 70 and the V282 references.**

**Page:** https://claude.ai/code/artifact/6751b3ba-2098-4c74-894b-b74741ff4565 (v7 — the drive, the plant, the
ratchet statistics, the rev-2 package, the risk before the next drive). **Scorer for the NEXT drive:**
`python rlog-tools/studies/grind/v293_flight_read.py <route id> --config analysis-2020accord/reference/toggle-config_V293_torque_mode_r2.decoded.json`
(`V293-FLIGHT-READ-HOWTO.md`). **Checklist:** `docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md` (fork
`66cf4454a` on the device FIRST, then restore the rev-2 config, then restart — on the old tables the plant FF
under-holds ×2.1 above 12 m/s). **Authority vs stock, re-verified from the three images at the operator's request:
peak ×6.17 (2461 vs 399 lane counts, stalled wheel), every authority cell exactly ×6.000, the 2.8 % surplus is the
P term against the unchanged stock P clamp, median ×4.35 over the demand range — nothing changed.**

**The PRE-FLIGHT pass, kept as the record of what was checked before the drive:**
**THE PASS, COMPLETE — `advA3` PASS (A1–A4) · `advC3` PASS (C1–C5) · `advD3` PASS (D1–D5) · `advB3`/`advB3b`:
B1, B3, B4, B5, B7 PASS, B8 reported, and 🛑 TWO CLAUSES FAIL AS WRITTEN (B2, B6), BOTH ADJUDICATED.**
Full table and reasoning: `docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md`.

- **A — ARITHMETIC PASS.** Clamp block simulated from its own decoded bytes over **4,023 int32 states: 0
  non-zero operands** (V282 at 46080: **4,012** — the null is capable); **D ≡ 0 by EACH cell alone**; Ki 0;
  `0x2A0C6` unreachable by three methods incl. **zero LE32 hits of `0xFEDF17F6`**; **rail 2461 = 2461** on
  matched cold-start trajectories, **P first rails at idx 239**, linear fit **10.336·idx − 1.89** (2.19-count
  max residual, accounted for by the map lerp plus three floors); all 28 Kp = [120]×5, all 28 Kd = [0]×4;
  **code region `[0x13000, 0xC0000)` byte-identical** ✔ (378 diff bytes, lowest `0xC61B7`).
- 🛑🛑 **A's CARRIED FINDING — NOT GATED, AND IT GOVERNS THE LANGUAGE: V293's sub-rail slope is 10.34
  counts/idx against V282's 21.35 at fb = 0.** Below idx 116 V293 delivers **0.47–0.49 of V282's
  STALLED-WHEEL torque** (idx 58: **598 vs 1236**), meeting it only at idx 239–240 — *"the peak is identical
  and needs twice the demand to reach."* ⇒ 🛑 **NEVER WRITE "AUTHORITY UNCHANGED" ABOUT V293, AND NEVER SHOW
  ONLY THE RAIL.** ⚠ Against a *moving* wheel V282 delivers less and can go negative while V293 holds, so
  the deficit is the **stalled** regime only; openpilot's LAF identification absorbs the slope (actuator
  fraction ~12 % → ~24 %), which is why the first drive identifies before it tunes.
- **B1 PASS at 2048** — unstable fits in torque mode, V282-pole-only family: **5244 → 7/2** (κ 0.45/1.45),
  **4451 → 5/0**, **2048 → 0/0**; both-poles family at κ 0.45 (n = 12, control matches) **0 unstable at every
  arm**, worst-plant ζ **+0.161** vs V282's **−0.005**. ⚠ The literal `ζ < 0.05` clause **condemns flown V282
  on 250/250 and 12/12 — broken**, scored as *"no unstable fit and no worse than V282"*; **the both-poles
  family at κ 1.45 is EMPTY, so the κ dispute is sidestepped at one end, not settled.**
  ⭐ **HAD 4451 BEEN BUILT, B1 WOULD HAVE FAILED.**
- **B3 PASS** — rail **×1.000000**, P rails at idx 239, slope **0.641212** counts per CAN count.
- **B4 PASS, and it is the THINNEST margin in the pass.** Ripple/level on loaded turns **0.028 / 0.034 /
  0.048** against the 0.25 gate (V282 0.019 / 0.013 / 0.099; **stock 0.044 / 0.033 / 0.087 — V293 sits
  between the two**); predicted F7 **≈ 1.24 /100 s** against 2, a margin of only **×1.6** through a
  nonlinear mapping.
- **B5 PASS at 2048** — 5–9 Hz **×1.59 / 1.50 / 1.53 vs V282** and **×1.13 / 1.07 / 1.05 vs STOCK** (the
  stock leg run at **both** readings of its r24 arm); **neither leg trips**, where **4451 trips leg 1 on
  r39 (1.654)**. ⭐ **The rise is BROADBAND — peakiness unchanged**, structurally unlike V292's resonant
  7 Hz re-arm.
- **B7 PASS** — **0 of 250** plants with ζ < 0.10 in 10–18 Hz; 13–17 Hz **×1.058** max vs V282 against a
  ×1.5 gate (V292's rejected number was ×1.9–2.1).
- **B8 reported** — the command-driven 18–22 Hz torque is **×0.055–0.137 of V282's ring and has no pole:
  it cannot ring.**
- 🛑 **B6 FAIL AS WRITTEN AT THE MEASURED τ — and it is a BROKEN CHECK that fires cleanly.** At each speed's
  own measured τ, V293 at the **repaired** preset (friction 0.00) breaks **3 of 10** controller-loop cells
  (worst **PM 33.2°**, k30 1.09, kU 1.80 at 5 m/s / τ 0.25) — and **V282 at the tune it is actually flown
  with breaks 3 of 10 too** (worst **PM 35.6°**, k30 1.12, kU 1.74 at 28.5 m/s / τ 0.22). On the
  path-following channel **both** go unstable inside [0.5×, 2×] (kU 1.31 vs 1.27). The friction repair is
  worth **×1.58 on k30**. ⇒ **Scored on its INTENT — V293's outer loop no worse than the build on the car —
  B6 PASSES.** ⚠ **Residual, named not closed: the creep margin at 5 m/s is only ~10–20 % of plant gain on
  BOTH builds, and the failure mode there is the V276 1–4 Hz signature. That is the FIRST THING TO WATCH,
  at low speed.**
- 🛑 **B2 FAIL AS WRITTEN — ADJUDICATED PASS ON INTENT, AND THE DISSENT STANDS.** Uncalibrated ring
  **×0.285** (r39) / **×0.403** (r6c); the mandated V292 calibration (**×1.90–3.64**) ⇒ **×0.54–1.04 /
  ×0.77–1.47** against the ≤ ×0.50 gate; the open-loop calibration (×1.64) ⇒ 0.47 / 0.66; **the on-car
  anchor, no predictor, re-derived independently: ×0.237 / ×0.285 / ×0.265.**
  **Why it was adjudicated rather than left to the broken-check rule:** B2 does **not** condemn a flown
  build, so that rule does not reach it. The calibration factor was measured on **V292, a build that did
  NOT open the loop** — the fit family's error there is in how a feedback pole reshapes the return ratio at
  20 Hz, **an error that has no channel when the operand is identically zero** (`|S| ≡ 1` is an identity the
  code region's bytes prove, not a fit). Transferred to the one fully-open-loop configuration the car has
  been measured in, **that calibration over-predicts the measured ring by ×1.3–2.0 — the calibrated
  predictor fails a measured case.** On the clause's intent (the ring at least halved) the direct on-car
  measurement reads ×0.24–0.29 and the command-driven residual ×0.06–0.14, **both EVIDENCE rather than
  model.** 🛑 **The V292 precedent is stated, not hidden: V292 was also cleared over one dissent and then
  failed on the wire on clauses the model had passed — which is exactly why this candidate's ring claim
  rests on the car's own open-loop measurement and NOT on the replay.**
- **C — BUILD AUDIT PASS.** Independent rebuild from the V282 image plus the prereg edit list, **hashes
  PREDICTED BEFORE THE WRITE**, reproduced byte for byte; 378 bytes / **0 unattributed / 0 below
  `0xC0000`**; round-trip byte-equal, 50/50 CRCs by two routines; the write guard refuses before touching
  the filesystem. **Five defects in the script's self-verification and prose, NONE in the artifact** — the
  census overstated by 23; **seven single-knot mutations (one Kp knot at 121, one Kd knot at 1) pass all
  241 assertions** because the byte counter cannot see a wrong *level* and the rail check samples only
  Y[−1] (bounded at +9 counts at one idx, closed for V293 by C1's independent knot derivation); the tag
  ignores the D-clamp integer; the "87 % of peak" D-kick sentence is a **×6.13 unit error** (14.5 %); "Kd
  128 on every record" is true on **8 of 28** (64 on 20). `scriptfix` applied the four fixes with the image
  hash held.
- **D — INTERLOCKS PASS (D1–D5), and D1 found the mechanism rather than failing to find one.** The
  integrate-and-trip **exists**: the soft-EME command integrator `gp-0x3570` in the shaper `FUN_00042af8`
  (`0x43214–0x4327C`), `I += (cmd − bound) << 15` at 1 kHz, authority `(|I>>15|·1092)>>10`, **SM2 arms at
  `|I>>15| ≥ 15361`** (a 100-count excess arms in 154 ms), `bound = max(corridor, IIR, boost floor 5120)`.
  ⭐ **The LKAS lane is clamped at 3072 so it cannot drive wind-up alone**; the aggregate ceiling 5325 is
  unchanged; the governor, `FUN_0004595a` and `FUN_000456a4` carry **no accumulator**; the energy budget
  `FUN_0007b022` is **unreachable** (it needs > 5325 strictly, and the cap table's max IS 5325).
  ⚠ **Residual named, not closed:** the 205-count band **`5120 < |cmd| ≤ 5325` needs 75 ms continuous
  residency**, it exists on V282 too, and SM2/SM3 self-clear. **D5 is false as worded** (the island does
  read `0xC61B6`) but **PASS in effect** — 239 island-internal targets, **zero external sources, zero
  `jarl` in**.

---

### 🛑🛑 V292 FLEW — THE VERDICT IN ONE PARAGRAPH

**The operator: grinding still present, stuttering WORSE — "most visible as an oscillation when holding
the wheel at a high angle."** Two of V292's own pre-registered revert signatures **FIRED**: the 6–9 Hz
strong-turn ripple returned (**F7 4.17 /100 s** pooled [1.68, 8.59] against V282's 0.51 and V281 rev 3's
0.00, ×8.1, p = 0.022; tap ripple/level **0.214 / 0.327 / 0.339** against a 0.25 trip and V282's
0.104–0.166), and the 9–18 Hz shoulder landed at **×1.8–2.1** where ×1.3–1.7 was predicted, carrying a new
**14.84 Hz line at +6.3 dB** on r6d where V282 reads +2.8. **The 18–22 Hz ring did NOT fall: by the
drive-controlled measure (engaged ÷ the SAME route's lateral-disengaged amplitude) the loop's own
contribution went UP ×1.20–2.00**, present-window amplitude ×1.07–1.38, the pre-registered creep stratum
×1.10 [0.68, 1.56] — against a predicted ×0.55 pooled / ×0.71 vs r6c. **f0 sat at 19.92–20.02 Hz on every
route and did not move.** The phase moved **+15.5 to +38.4° at 10 Hz** where −14 ± 4° was predicted —
consistently, on three routes against two references, **opposite in sign**. Mechanism: **P is not railed
on any of the seven F7 episodes** (duty ≤ 0.20), so this is not the V278 rev 3 stalled-wheel class; the
seven sit at 6.64–7.47 Hz, exactly the **7.3 Hz gate `DESIGN-V291-FBLP` predicted every dose at a ≥ 927
would pay** (V292 carries a = 962) — the linear 7 Hz mode V281 rev 3 damped out, **re-armed by the fb
pole's phase lag** [EVIDENCE for the numbers, BELIEF for the causal attribution]. Exposure, excitation
(`0xE4` content ≤ ×1.3 while the response moved ×2) and route-normalisation controls all pass; the one
standing confound is the driving model change `tsfdo` → `gyhu3`, which is why controls (2) and (3) exist.
**The wiped `Accord*` params are RESOLVED and NOT a confound** — each code default equals the 2026-09-10
backup value, so the effective outer loop was unchanged, and `AccordCurvatureLead` was absent both sides
⇒ default OFF, the prereg requirement met. Full read: `rlog-tools/studies/grind/V292-FLIGHT-READ-2026-09-13.md`;
lineage entry and verdict in `docs/BUILD-LINEAGE.md`.

### 🛑🛑 V293 FLEW — ROUTE 70 — THE VERDICT IN ONE PARAGRAPH (2026-09-13 night)

**Attribution:** `initData.params` carries the rev-1 config key for key; Kp 0.3000 over 77,863 frames; identity R²
0.986 (V282/V292 references −0.7…−4.8). The scorer's `f/D ≥ 0.75` branch gate was **broken as written** — the fork
logs `f = D_current − roll·g·fade − latAccelOffset·fade` and `desiredLateralAccel = setpoint` (the 0.30 s delayed
reference), so `f/D = 1 − c/|D|` by construction (c ≈ 0.23–0.30 m/s²) — replaced in scorer v2 by `f` vs
`starpilotLateralState.feedforward` (equal ⇒ else-branch; differing ⇒ plant-FF branch live) and the f-slope test.
**Bands:** ring presence 1.1 % (references 9.8–20.9 %), present-window amplitude ×0.43 of r6c (gate ≤ 0.40 — a
marginal miss, NOT a null: the terminal null sentence's antecedent "unchanged" is not met, so the in-loop class is
**not** closed by this drive; the drive-controlled 18–22 Hz reads ×0.55 of r6c and the excess MOVED DOWN to 9–17 Hz,
unexplained); F7 0.00/100 s; 6–8.5 Hz tap ripple ×0.10; 5–9 Hz ×1.6–1.9 broadband (predicted); 13–17 Hz ×1.03; a
10.55 Hz +3.8 dB line not gated. **One REVERT trigger fired — the outer loop:** a genuine 1.2–1.8 Hz peak in
command AND angle (3.55° at 0–5 m/s; 6.5–11.8 dB prominence below 20 m/s where no reference has any; 1–4 Hz rate
content 4.8–11.6× every reference) — assigned by the pre-registration to the FORK tune. **The plant
(`rlog-tools/studies/grind/V293-PLANT-IDENT-2026-09-13.md`):** a SPRING + Coulomb friction, `u = a(v)·θ + b·θ' +
F·sign θ'` in openpilot torque units; IV transfer torque→angle FLAT 0.15–1.2 Hz (an integrator would fall at −1);
hold a = 0.0020/0.0079/0.0113/0.0154 u/deg at 5/12.5/18.5/28.5 m/s (soft below 8; the 4–5 m/s knots are the
study's weakest cell, b's CI crosses zero); b ≈ 0.002–0.005 u per deg/s; **F = 0.010–0.012 u = `SteerFriction`'s
own unit, and the drive ran 0.00**; τ_eq 0.19–0.34 s total, the lag/dead-time split still unidentifiable (a 0.2 s
transport delay is not credible for a rack — accumulated closed-loop phase); LAF measured 3.19/5.32/5.39/6.37 by
band and ×2.8 small→large demand — **the fork's model was wrong twice (no friction, one LAF at all speeds)**; SR and
vehicle model agree with the gyro within 1 % — NOT a cause; the +0.34 m/s² gap between the command and `f` is **mostly ROLL compensation** (+0.41 m/s², a persistent +2.4°
estimated roll — device levelling vs camber undecided) plus a −0.07 m/s² learned `latAccelOffset` (restored cache,
`liveValid` 0 % on this drive) — NOT a 0.30 stale offset (scorer v2's three-term regression, R² 0.99998). **The loop as flown:** crossover
0.034–0.25 Hz, PM 110–136° above 8 m/s, **PM −11° / Ms 12 at 4.5 m/s** (the hard-coded low-speed factor ADDS 6.3 to
Kp; no `SteerKP` removes it; only `SteerLatAccel` divides it — and in the plant-FF branch LAF scales P and I alone).
**The ratchet, measured** (§E/H): dwell-then-jump events **6–39× V282** at th 0.25 deg/s (15.2/7.7/4.6/1.2 per
minute vs 0.39/0.64/0.44/0.20), p90 dwell 1.3–2.6× longer, snap p90 1.5–2.9× at ≥10 m/s, rate-magnitude
concentration 0.468 vs 0.325–0.351 at matched activity — while the 0xE4 command is **3× smoother** than V282's;
three nulls on integrator stick-slip (no zero spike, breakaway = hold, no wind-up ramp). Mechanism: a friction band
(snap ≈ 2F/k(v)) with nothing fast to linearise it — V282 had the EPS 1 kHz rate servo AND the fork's dithering
rate term, both removed on the same drive. **Loose** = outer-loop stiffness only 1.1–1.5× the car's own spring
(wander itself is a null). **Oversteer** = the lat-accel FF over-commanding ×1.9–2.1 above 15 m/s (turn-hold 1.09 at
>20). **Overshoot-then-correct** = a fixed 0.4–0.5 m/s² excursion that does not scale with the step (not a linear
under-damped loop). **Disposition:** the fork — `docs/research/FORK-LATERAL-PATH-V293-2026-09-13.md` maps the path;
`docs/research/DESIGN-NOTE-INNER-LOOP-QUANTITY-2026-09-13.md` records the operator's inner-loop question (angle,
not angular acceleration, if ever; rungs: toggles → 100 Hz fork rate feedback → firmware angle loop).

### 🛑🛑 V293 — WHAT IT IS, WHAT IT COSTS, AND WHAT IT CANNOT PROMISE

**V293 = V282 + cal-only edits, not one code byte:** `0xC62E6` 46080 → **0** (the LKAS rate-PID feedback
saturation clamp; zero forces the feedback operand to exactly 0 on all three branches ⇒ **`E = 32·setpoint`,
the loop is OPEN at every frequency**), the Kd bank `0xCB7D4` → **0** and `0xC61B6` → **0** (**D ≡ 0 twice
over, by two independent cells** — the prereg's A1 clause FAILs unless either alone suffices), the Kp bank
`0xCB994` **all 28 records → 120 flat** (at fb = 0, V282's Kp 248 would rail from idx 116, i.e. peak torque
from 48 % of demand; 120 keeps the surface **linear to full command into V282's own 15360 P-rail**; all 28
because the fb clamp is **one global cell** while Kp is per-slot), and `0xC6446` 5244 → **2048** (the r24
engaged arm). **Class: V279 rev 2's structure (built 2026-09-02, never flown) rebased onto V282** — the
LKAS lane becomes a linear **torque map**, `T = f(cmd)·taper`. Not a new lever; new are the base, the r24
dose and the fork preset. 🛑 **Peak authority is ×1.000: the delivered rail reads 2461 on the V293 image
AND on the V282 image.** Three numbers have been called "the rail" and only one is delivered — **2461**
is the byte-exact steady state through the fade and the output lag (the residue is the output lag's
integer fixed-point interval); **2462** is the same chain's LINEAR DC; **2505** is the structural ceiling
`min((15360·5346)>>15, 3072)`, the `T_ceil` convention the older docstrings print. **Never quote 2505 as
delivered — neither build reaches it at fade 254.** (This supersedes the design doc's ×0.9992 "2461 vs
2463", which compared the two builds by two different methods, and refines correction 3(d) below.)

**🛑 THE PRICE, and it is on the symptom he has just called worse.** V282's loop is a **disturbance-
rejecting servo below ~13 Hz**, and opening it removes that rejection: the predicted **5–9 Hz wheel band
rises ×1.74–1.85 broadband** across the r24 arms, and **×2.10 (r39) / ×1.45 (r35)** on loaded high-angle
windows — consistent with `|1 + L_V282(7.3 Hz)| = 2.04`. That is the same band V292's flight just measured
rising ×1.6–2.2 raw / ×2.9–4.3 route-normalised. **In exchange**, the ring is predicted **×0.285** on r39's
loudest windows and **×0.40** on r6c, with an **on-car anchor** — the reciprocal of V282's own measured
engaged ÷ disengaged ratio — of **×0.24–0.29**. 🛑 **The one out-of-sample test of that predictor FAILED
on V292** (predicted ×0.535, the wire read the loop contribution UP ×1.20–2.00), and the failure is the
**method's**, not an implementation difference. **The r24 cut to 2048** is the orchestrator's ruling
against the design's 4451, taken before any image existed: a criterion-exact arm carries no margin when
the same model under-predicted V292's 5–9 Hz cost three-fold, 2048 is the record's own priced lever, and
**in torque mode the cut is free at 20 Hz** — with the servo gone, removing r24 **raises** ζ (+0.036 /
+0.097 / +0.183 at κ 0.10/0.20/0.45, 96–100 % of plants) where with the servo present it costs it.
**The outer loop is NOT the risk** (Ms 1.09–1.38 vs V282's 1.04–1.35, PM 64° vs 66°; no grid cell
reproduces V276's 2–4 Hz signature that V282 does not also reproduce) — **V276's shape returns as a
feedforward mis-scaling ×3.17 at 5 m/s**, which is what the fork preset exists to prevent.
⭐ **The decomposition the operator is entitled to before he decides:** sweeping `0xC62E6` 46080 → 0 with
Kp 120 / Kd 0 held moves the ring only ×0.299 → ×0.272 — **~90 % of the ring benefit is Kd = 0 and the Kp
re-level; the clamp is what changes the delivered QUANTITY** and is nearly free on the ring. 🛑 **There is
no intermediate dose**: `0xC62E6` is a clamp, not a gain, and any non-zero value is a **Coulomb relay on
sign(rate)** — worse than 0 on every column, and it *adds* 18–22 Hz motion with the command frozen.
**🛑 THE FIRST DRIVE IS AN IDENTIFICATION DRIVE, NOT A SYMPTOM DRIVE:** hands-off, laterally engaged,
≥ 400 frame pairs per |τ| bucket in ≥ 4 buckets to |τ| 0.5, both signs, fitted by instrumental variables
against `modelV2.action.desiredCurvature·v²` — **not** from `torqued`. Then the tune. Then the symptom drive.
Detail: prereg `docs/review/ADVERSARIAL-V293-PREREG-2026-09-13.md` · design
`docs/specs/design/DESIGN-V293-TORQUE-MODE-2026-09-13.md` · lineage entry
`docs/BUILD-LINEAGE-PART6-V291-ONWARD.md` · builder `analysis-2020accord/builds/v108_plus/build_v293_tva.py`.

**READ IT BY:** the within-frame identity `T_tap = f(cmd)·taper` on every engaged frame, with
`sign(T) = −sign(cmd)` ≈ 1.00 proving the feedback is dead (T saturating below the map top means the map
is not the live source); the ring by the **drive-controlled** measure only — engaged 18–22 Hz ÷ the same
route's lateral-disengaged (V282 3.4–3.9, V292 4.1–6.8) plus present-window amplitude vs r6c — **never the
driven half-peak decay**; F7 and tap ripple/level at |angle| ≥ 30°; a 1–4 Hz line in command and angle;
b4–b7 duties as the r24 control. **REVERT IF:** grinding unchanged (his word); the 6–9 Hz ripple returns
(F7 ≥ 2/100 s or ripple/level ≥ 0.25); **a 1–4 Hz oscillation of command and angle — the V276 signature;
the fix is the fork preset, not the firmware, but the drive stops**; a 10–18 Hz line; a darty or loose
feel; a one-sided pull at rest; any EME or DTC.

### 🛑🛑 THE DESIGN LAW, AS OF 2026-09-13 NIGHT — the loop is open, the ring mostly went with it, and the operator's symptoms moved to the FORK

> **V293 opened the LKAS rate loop on every frame (identity R² 0.986) and the 18–22 Hz ring's PRESENCE fell from
> 9.8–20.9 % of windows to 1.1 %, its present-window amplitude to ×0.43 of V282's, with F7 = 0 and the tap ripple
> ×0.10 — and the operator reports no classic grinding or stuttering.** The terminal null sentence (*"if the
> ring is UNCHANGED with the loop open, the 20 Hz object is not the loop's"*) did NOT fire: its antecedent is not
> met. Nor did the pre-registered success clause (≤ ×0.40) pass — ×0.43 is a marginal miss, and the excess moved
> down to 9–17 Hz. **Reading: the 20 Hz object is largely the closed loop's; what remains is small and unexplained;
> the in-loop class is neither closed nor finished — it is PARKED, because the firmware is no longer where the
> operator's symptoms are.** The symptoms he now reports (ratchety snapping, loose, oversteer, overshoot) are the
> spring-plus-friction plant meeting a controller that modelled a lat-accel gain. **The design law for the next
> step: model the plant the firmware left — spring hold, viscous move, Coulomb friction — on the FORK side, and
> instrument each symptom against route 70 and the V282 references; cut no firmware for a fork-side error.**
> V292's own null sentence (decay not below 1.23× while the phase moved) stands as a record of that build.

- **The measurement that set the direction still stands** (`OPENLOOP-RING-DAMPING-2026-09-13.md`, 35
  routes, 4,759 s lateral-disengaged): with the loop OPEN there is **no resonance in 16–26 Hz**; a
  synthetic mode of ζ ≤ 0.03 at the same energy WOULD have been found ⇒ **ζ_open ≥ 0.05 or non-modal**;
  engaged ζ 0.034–0.036, **V282 alone 0.0164** [0.0126, 0.0222] at 20.01 Hz; load-matched amplitude
  OFF/engaged 0.21 (×4.5). Limit: opening the loop also removes the LKAS excitation, so "no object" has
  two readings and both say the same thing for a build.
- **Scoring rules the V292 flight forced, binding on every later build.** (a) **Score the ring by the
  DRIVE-CONTROLLED measure** — engaged ÷ same-route lateral-disengaged, plus present-window amplitude vs
  r6c — **never** by the driven half-peak decay, which is confounded. (b) **Pre-register MARGINS, not
  points**: the operator's revert threshold on the 7 Hz ripple (0.25) and V292's own prediction (0.22)
  were 13 % apart. (c) **A duty read is not an attribution** — design the identity read on the bit's
  *meaning* (a lagged-sign correlation, with a lag profile and reference builds), not on a duty that
  overlaps the reference.
- **The r24 lane** (`TRACE-2026-09-13-r24-lane-transfer.md`): a lag-4 backward difference of torsion-bar
  torque, unit-weight sibling of the LKAS lane at `gp-0x6b94` ⇒ **1 : 1 at the motor**; pure PUMP at
  3–7 Hz, near-pure DAMPER at 18–22 Hz (73–86 % of the electronic 20 Hz damping) — **but that damping is
  a partial cancellation of the servo's de-damping, and it evaporates when the servo goes.** κ dispute
  still open (0.10–0.20 / 0.45 / 1.45); 10–14 Hz unidentified; the `gp-0x671d` fault latch UNARMED.
- **The LKAS lane's true path** (`TRACE-2026-09-13-lkas-lane-to-aggregator-and-ghidra-gap.md`): T @`0x2A23C`
  → gated copy @`0x2A2EA` → `gp-0x6b3c` → clamp ±`0xC61B2` → request array → **`gp-0x6b4c`** (unit weight)
  → aggregator → governor → comp → shaper → `gp-0x6b98`. **`gp-0x6ad4` is a driver-torque tracking PID**,
  not the LKAS output. `0x2A508–0x2B421` is an uncalled TWIN of the LKAS output path, analysed and SAVED.

### THE SESSION'S GOAL AND THE SESSION'S ANSWER

**The operator's goal, in substance:** a new firmware plus StarPilot changes that keep **V282's authority**
(×6 torque, ×6 rate setpoint, no EMEs) with **no grinding and no stutter**; **either** the LKAS PID tracks
**angular acceleration** (≈ torque, which is what openpilot expects) **or** StarPilot outputs a **rate
target**; and the StarPilot tuning updated to match.

| reading of the goal | what it would be | disposition |
|---|---|---|
| **"torque"** | **Torque mode** — V279's structure on V282: fb clamp 0, Kd 0, Kp re-levelled | ⭐ **BUILT as V293 and FLOWN (route 70).** Cal-only, no cave; the loop is open on the wire; no classic grinding or stuttering per the operator; the plant left is a spring + friction |
| **"angular acceleration tracking"** | the PID tracks `d(rate)/dt` instead of rate | 🛑 **DOMINATED — recorded, not built.** It **CONTAINS torque mode** and adds electronic inertia on top, and the inertia term **needs a cave** (the kit's only bricking class). Reasoning: `TRACE-2026-09-13-lkas-pid-tracked-quantity.md` §4 |
| **"StarPilot outputs a rate target"** (fork Design B) | shape the reference on the openpilot side | 🛑 **CANNOT REMOVE THE GRINDING — recorded, not built.** V288 rev 2 flew exactly this class: the cave was live, the D-bind duty fell ×0.03 as designed, **and the grinding was unchanged** (19.99 vs 19.93 Hz, KS p 0.18). Nothing on the fork's reference side reaches the 20 Hz ring |
| **"the tuning updated"** (goal amended 2026-09-13: *and address my route 70 feedback* — ratchety, loose, oversteer, overshoot-then-correct) | the fork's plant model + a toggle config | ⭐ **Rev 1** (`toggle-config_V293_torque_mode.json`: rate-plant FF off, Kp 0.3, Ki 0.15, friction 0.00, LAF 6.0) flew on route 70 and identified the plant. **Rev 2 = the fork's Accord plant tables re-identified in CODE (`Dom` `66cf4454a`, the only place the shape lives: no single `AccordEpsSpringScale` fits both below 8 m/s and above 12) + `toggle-config_V293_torque_mode_r2.json`** (plant FF on, friction 0.011, LAF 14, Kp 0.85, Ki 0.30, learned offset off, delay 0.2). Each symptom has a cause, a fix and an instrument (scorer v2 §7) |

### ⏱ τ, MEASURED — and "τ = 0.20 s" was never a measurement

`rlog-tools/studies/grind/TAU-ACTUATOR-DELAY-2026-09-13.md` [EVIDENCE]. The LKAS lateral delay, measured
`controlsState.desiredCurvature` → steering-angle curvature on **six routes**, zero-lag and 200 ms controls
both passing. ⚠ **The `0xE4` → rate pair is UNUSABLE for this** — the rate-plant feedforward makes the
wheel **LEAD** the command by one round trip.

| speed | correlation-peak lag, current tune (r6c / V282) |
|---|---|
| 3–8 m/s | **258 ms** [251, 264] |
| 8–15 m/s | **232 ms** [219, 247] |
| 15–25 m/s | **211 ms** [197, 231] |
| 25+ m/s | **182 ms** [175, 191] |

⭐ **V292's routes sit INSIDE that scatter — V292 changed nothing here; the TUNE did.** r39's older tune
was **20–55 ms faster**, and the LAF 6.0 tune cut P/I authority.
🛑 **The path is NOT a pure delay, so "τ = 0.20 s" is neither measured nor a single number.** Three
estimators differ by **up to 100 ms on the same data**, and the fitted lag pole is **1.4–4.3 Hz — the
torque controller's own bandwidth plus plant, NOT the EPS servo.** ⇒ **use `tau_eq(f)` at the crossover,
not a scalar.** The **dead-time / servo-lag split is NOT identified** (r39 puts the speed dependence in
dead time, 80 → 180 ms; r6c puts it in the pole) — **quote totals only.** At 3–8 m/s the wheel realises
only **0.57–0.69 of commanded curvature at 1 Hz**, and small-signal is **30–50 ms slower** (friction and
deadband, **not** rate limiting).
⇒ **What this does to B6:** its FAIL was conditional on **τ ≥ 0.18 s**, and the measured totals are
**0.182–0.258 s at every speed band** — met, and met with margin (**258 ms**) at the 5 m/s point where the
FAIL sits. ⚠ **Not a clean substitution**, because the report's own finding is that a total is not
`tau_eq` at the crossover. **B6's condition is satisfied on the best evidence available; the re-score at
the repaired preset is still what settles it.** [EVIDENCE for the totals; this inference is mine.]

**The operator's reading of the speed-dependent lag, recorded 2026-09-13 (τ study §7):** he is skeptical it
is a controls artefact rather than a real, physically variable delay, and may implement a variable lateral
(and longitudinal) delay in StarPilot if one is real. This session does NOT decide it: the dead-time/pole
split is unidentified (r39's fit puts the speed dependence in dead time 80 → 180 ms, r6c's in the pole), the
tune moved the total 20–55 ms, the lag is amplitude-dependent in the friction direction, and the EPS's own
speed-half fade (table D, axis unit OPEN; ×0.42–0.69 delivered at 3–9 m/s on-car) lowers the plant gain at low
speed — three candidate causes (firmware fade, rack friction, outer-loop tune), none excluded. **The V293
identification drive decides it for free:** in torque mode the lane is open-loop and the rate-plant FF is
bypassed, so the 0xE4 → rate pair measures the plant directly per speed band. Longitudinal: not measured.

**V293 (route 70, loop open) — the answer the τ study asked for:** torque→angle τ_eq **0.348/0.262/0.229/0.249/
0.187 s at 0.2/0.3/0.5/0.7/1.0 Hz** (15–22 m/s) and 0.330/0.339/0.285/0.240/0.137 (>22); total 0.19–0.34 s, falling
mildly with speed; the lag/dead-time split is STILL unidentifiable (8–15 puts it in a 0.26 s pole, ≥15 in dead
time; IV controls pass at 0 and 196 ms). A 0.2 s pure transport delay is not credible for a rack — it is the
plant's spring pole plus accumulated closed-loop phase (and the fork's own 0.30 s reference delay above 1.2 Hz).
**Verdict: not a variable transport delay; use τ_eq at the outer loop's crossover as the controls number; do not
implement a variable delay.** `SteerDelay` stays 0.2 (lookahead 0.30 s). [EVIDENCE — `V293-PLANT-IDENT` §B6]

### 🛑🛑 A STANDING FORK DEFECT — LIVE ON THE CAR TODAY, ×6.6, AND IT IS NOT A V293 PROBLEM

> ⚠ **SUPERSEDED 2026-09-13 night by the rev-2 package:** with `SteerKP` 0.85 the LSF inflation at 4.5 m/s is 8.4 (it was
> 22 at Kp 0.3), `SteerFriction` is back at the measured 0.011, and the describing-function check (`V293-PLANT-IDENT`
> §K) finds NO relay limit cycle at 0.011 on either the flown or the rev-2 config (first sustaining value 0.0235 at
> 4.5 m/s). The rule "friction > 0 requires Kp ≤ 1.0" is respected. The mechanism below is still true of the code.


Found by `advB3`'s B6 surface, **crux verified in the fork source by the orchestrator.** StarPilot feeds
**`error_with_lsf`** (= `error·(1 + lsf/kp)`) into **`get_friction`**, where upstream openpilot feeds the
**raw** error. The friction compensator's gain is therefore **`(friction/0.30)·(1 + lsf/kp)`**:

| configuration | friction-compensator gain | outer-loop PM at 5 m/s, κ 1.00, τ 0.20 s |
|---|---|---|
| **the operator's LIVE tune today (Kp 0.9, on V282)** | **×6.6** | — |
| the V293 preset as shipped (Kp 0.3, friction 0.01) | **×17.9** | **22.8°** (Ms 4.32) |
| the repair: preset friction **0.01 → 0.00** | — | **42.2°** (Ms 2.06, GM ×1.40) |

⭐ **A LOWER Kp MAKES IT WORSE, NOT SAFER** — the loop gain is minimised near **Kp ≈ 1.0**, so *"Kp 0.3 is
the conservative third of today's 0.9"* is **backwards as a stability argument.** ⚠ The whole B6 verdict is
conditional on **τ ≥ 0.18 s**, and **τ = 0.20 s is the operator's `SteerDelay` toggle ECHOED BACK, not
identified** (the Honda port's prior is 0.10 s) — being measured from the rlogs now. **This is a fork fact,
not a firmware fact: it is live on V282 today and it does not depend on which image is in the ECU.**

### FORK (`raayyymond-StarPilot` @ `Dom`) — REV 2: the plant tables in CODE (`66cf4454a`) + a toggle config; rev 1 flew and identified the plant

**What the fork computes** is mapped end to end in `docs/research/FORK-LATERAL-PATH-V293-2026-09-13.md` (100 Hz;
`lat_delay` = `SteerDelay` + 0.1 = 0.30 s flat; the setpoint is a complementary filter that is the 0.30 s-delayed
command above 1.2 Hz; `f = D_current − roll·g·fade − latAccelOffset·fade`; `d ≡ 0` structurally; the Honda rate
limiter ±0.03/frame and panda impose no other limit on 0xE4; **the angle-domain P gain is FLAT 33–37 counts/deg from
1 to 20 m/s** because the hard-coded low-speed factor `[12, 10.5, 8, 5]` cancels the v² — so `SteerKP` is nearly
inert below 7 m/s and `SteerLatAccel` is the only uniform lever; **in the `AccordRatePlantFF` branch the output is
`(P + I)/SteerLatAccel + plant_ff_torque + friction_torque`**, so there LAF scales P and I alone). The branch's
feedforward is a SPRING: `hold = k(v)/G(v)·angle_des`, `move = rate_gain·d(angle_des)/dt / G(v)` — the shape V293's
plant has — with tables that were identified on the V280–V292 RATE loop and are the wrong numbers for V293.

**Rev 2, shipped 2026-09-13 night** (`docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md`;
`docs/review/ADV-REV2-FORK-PACKAGE-2026-09-13.md` is the adversarial pass on it):
- **Fork CODE — `Dom` `66cf4454a`** (three commits: `9622aee9f` the tables, `8c4051ce6` the low-speed knots after the adversarial pass, `66cf4454a` the knot placement (measured values at the band centres); `selfdrive/controls/lib/latcontrol_vehicle_tunes.py`): `HONDA_ACCORD_EPS_G_V`
  [120, 95, 85, 70] → **[550, 271, 246, 167]**, `HONDA_ACCORD_EPS_K_V` [0.17, 0.28, 0.35, 0.45, 0.50] →
  **[0.30, 1.00, 2.30, 2.77, 3.91]** (G = 1/b, k = a/b, hold k/G = a = 0.00085/0.0074/0.0116/0.0154 at the band centres 4.9/12.0/18.9/22.8 m/s (0.00055 at ≤ 4, 0.0023 at 8; the 28.5 knot extrapolated so the table lands on the measurement at 22.8 instead of under-holding by 16 % there) u/deg at
  5/12.5/18.5/28.5 m/s; 4–5 m/s BELIEF and conservative; 28.5 extrapolated; old tables kept in the comment;
  `test_latcontrol.py` updated). **Why code and not a scale:** the old tables need ×1.2 at 5 m/s and ×2.1 from
  12.5 m/s up — a single `AccordEpsSpringScale` right at speed over-holds ~2.1× below 8 m/s, the dangerous
  direction. Replay residual vs the torque the plant needed: **0.042/0.042/0.007/0.010** by band (toggle-only best
  0.210/0.037/0.031/0.021; the flown branch 0.080/0.045/0.045/0.049); hold ratio **~0.5/0.97/1.01/1.00** at the band centres (the 1–8 band re-bounded by the adversary: the joint fit's 1.19 rested on a knot 2.4× above route 70's own hands-off bound).
- **Toggle config — `analysis-2020accord/reference/toggle-config_V293_torque_mode_r2.json`** (15 keys, a delta;
  generator `tools/make_galaxy_toggle_config.py`): `AccordRatePlantFF` **1** · `AccordEpsSpringScale` /
  `AccordEpsGainScale` **1.0** · `AccordFFRateGain` **0.5** (1/G is the measured viscous term, but at 1.0 the move term on a planner-limited reference drove the FF past full scale below 8 m/s on route 70's demand — ADV-REV2 finding 2) · `SteerFriction`
  **0.011** (measured F; DF check: no relay cycle < 0.0235) · `SteerLatAccel` **14.0** (the low-speed loop: PM −11°/Ms 12
  → PM 68°/Ms 2.16 at 4.5 m/s) · `SteerKP` **0.85** (hold stiffness at speed ≈ as flown; the Ms ≤ 2 bound at >22 m/s is
  Kp ≤ 0.92 at LAF 14) · `AccordTorqueKi` **0.30** (live integral gain Ki·(1 + lsf/Kp): 3× lower than flown at 4.5 m/s,
  0.6× at speed) · `KeepLearnedLatAccelOffset` **0** (drops the −0.07 m/s² restored, never-revalidated learned offset; ⚠ the +0.41 m/s²
  of the command-vs-`f` gap is ROLL compensation — a persistent +2.4° estimated roll no toggle touches) · `SteerDelay` 0.2 / `UseAutoSteerDelay` 0 · pins as rev 1.
- **Predicted on the identified plant:** Ms 1.78 (15–22) / ≈1.9 (>22); step overshoot 0.48/0.38 (flown 1.41/1.56);
  FF hold ratio 1.01/1.00 (flown 1.90/2.06); **every config still fails the margin bound at 3 m/s** (the low-speed
  factor; direction, not magnitude). What would falsify it on the next drive: tracking gain 0.88/1.02/1.12 → 1.00;
  integrator share 0.38 → ≪; straight-line delivery 80 % → 90–110; dwells/min at th 0.25 → ≤ 3× r6c; concentration
  0.468 → ≤ 0.40; 1–4 Hz prominence < 3 dB. If friction + FF move the ratchet but not the tracking (or the reverse),
  the two causes separate — the one thing route 70 could not do.
- 🛑 **ORDER:** fork `66cf4454a` on the device FIRST, then restore the rev-2 config, then restart openpilot. The
  firmware stays V293. Fork-side revert = restore rev 1 (`toggle-config_V293_torque_mode.json`) + restart. A torque
  config on a **rate-servo** image is over-delivery nothing downstream catches — never; **Safe Mode resets these
  keys** (a route out, never in). **Rev 1 + V293 is the flown state** (loose/ratchety, not unsafe).
- **Still true from rev 1:** `Accord*` keys at their default are ABSENT from `initData` (read absence as the
  default); the 100 Hz Kp read `p/error = SteerKP` is the attribution that survives a mid-route change (must read
  0.85 on rev 2); `torqued` reports `useParams` 1 on this car (Honda IS in `ALLOWED_CARS`) — its LAF/friction are not
  taken under `ForceAutoTuneOff`, its OFFSET was (rev 1) and is not (rev 2); `ModelCurvatureLead` is not in the fork
  (patch preserved); the cereal slot collisions (`@137`, `@116`) still require the scorer's patched schema.
- **Not done, deliberately:** no 100 Hz rate-feedback term in the fork yet (rung 2 of the design note — only if the
  snap statistic does not fall; ✅ the operator's 50 Hz worry was CHECKED: `0x14A`/`0x18F` are 100 Hz with fresh samples
  every frame on route 70, only the `0x1AB` tap is 50 Hz — the design note carries the measurement); no reshape of the low-speed factor (code; only if 3–8 m/s stays marginal on the
  rev-2 drive); no firmware change.

### CORRECTIONS OF RECORD, 2026-09-13 (late)
0. **Two instrument traps from the V293 scorer (`rlog-tools/studies/grind/v293_flight_read.py`, EVIDENCE):**
   (a) the kit's cereal schema declares `epsTelemetry @137` while the fork declares `starpilotLateralState @137`
   — same union slot, same struct id `0xc2243c65e0340384`, different layout — so **any kit decoder reading
   `epsTelemetry` from a fork-logged (2026-09) rlog reads garbage**; the scorer loads a patched schema copy
   (`_scratch/cereal_fork/`), the kit schema is untouched and must be fixed at the next tooling pass — and a
   SECOND collision of the same shape: kit `modelDataV2SP @116` (struct id `0xa1680744031fdb2d`) vs the fork's
   `customReserved9 @116` (the Testing Ground selection heartbeat: slotId/slotName/variant/variantLabel), so
   two slots mis-decode fork rlogs, not one;
   (b) **the 427 tap's wire polarity is sign(T) = +sign(cmd)** — the V293 prereg's "−sign(cmd) ≈ 1.00" read
   was inherited from V279's docstring and is inverted (V282/V292 read 0.145–0.149 on it); the prereg carries
   the erratum and the scorer prints both columns. The scorer's zero-parameter identity FAILS on all six
   non-V293 routes (R² ≤ −0.01) and reads 0.96 on a synthetic V293 tap; V292 fails every V293 revert gate it
   would have been scored on (ring ×1.07–1.38 vs ≤ 0.40; F7 2.2–6.3; absolute 6–8.5 Hz tap ripple ×2.0–2.2).
0b. **Four more from the scorer's validation (`V293-FLIGHT-READ-HOWTO.md`):** DESIGN-V293 §6.2's b7 0.996 → 0.808
   and b4 0.808 are r39's ten loudest one-direction windows, not whole-route (whole-route V282: b7 0.507–0.548,
   b4 0.394–0.404 — the scorer prints and uses these); §6.3's absolute 6–8.5 Hz tap-ripple clause never sized
   V282 (now r6c 73.1 / r39 107.5 / r35 119.2 counts — the ×1.5 gate is 110 vs 161 depending on the reference;
   the scorer takes r6c, on which V292 fails ×2.0–2.2); clause B5's literal window (|angle| ≥ 30°, bar 400–1216)
   has < 3 s of runs on every reference route — the scorer substitutes the 6–8.5 Hz wheel rate on loaded turns;
   r35's tap ripple/level has three values in the record (0.21 / 0.18 / 0.161 by stratum) — pin the stratum. Also:
   1–4 Hz coherence reads 0.88–1.00 on EVERY route (openpilot commands there) — the outer-loop discriminator is
   the 1–4 Hz angle AMPLITUDE vs same-speed references, never coherence; the toggle's only control-path check is
   `torqueState` f/D (torque mode ⇒ 1.000; rate-plant 0.24–0.40; gate 0.75).
1. **The V292 prereg's b3 DUTY read did not discriminate** — V292 0.418–0.453 against V282's 0.467,
   overlapping, and the idle control read backwards (0.035–0.049 vs r6c 0.000). A **design defect in the
   read**, caught only because the flight agent refused to force it. Attribution came from the bit's
   *meaning* instead. Carry (c) of the scoring rules above.
2. **The byte-exact replay's V292 prediction FAILED out of sample** (×0.55 predicted, the loop's
   contribution measured UP ×1.20–2.00). The failure is the **method's** — the V293 design agent
   reproduced the published number with its own implementation. **Every replay-based ring prediction in
   the record now carries that caveat, V293's included.**
3. **Tracer corrections, four, each from the bytes** (`TRACE-2026-09-13-lkas-pid-tracked-quantity.md` §7):
   (a) **`0x29F18 sar 0x7,r2` is the I ACCUMULATOR, not P — the registers were swapped in the record.**
   P is `(E·Kp) >> 8` formed at `0x29E36 mul` / `0x29E3E sar 0x8`, clamped to ±`[0xC61BC]`; `r8` is D.
   (b) **`0x2A0C6` is NOT a reset route ("SKIP 3") — it is a second delivery MODE**, a feedback-only
   viscous damper `−sign(fb)·LERP(|fb>>5|)` over `0xC6710–0xC6730`, gated on `gp-0x680a`, **unreachable**
   (zero writers; `.data` boot value `00`), which is why the mislabel has cost nothing.
   (c) **The cold-boot values of `gp-0x3d30` / `gp-0x3d2c` are now EVIDENCE, not BELIEF: both boot to 0**,
   from the `.data` copy loop `0x1476C–0x14794` (flash `0x89380` / `0x89384`), with `gp-0x6AB0` ← `0x86600`
   = `88 02 88 02` as the non-zero positive control.
   (d) **The delivered rail is NOT 2481 and NOT 2505.** An always-on override taper
   `((255·255)&0xFFFF)>>8 = 254`, i.e. **×254/256**, sits between the sum and the sum clamp; 2481 omits it.
   ▸ **Refined at the V293 build from BOTH built images: the DELIVERED rail is 2461** (the byte-exact
   steady state; the residue is the output lag's integer fixed-point interval), **2462 is the LINEAR DC**
   of the same chain, and **2505 is the structural ceiling.** The tracer's 2462 was the linear reading.
4. **THE TAPER — SPLIT THE CLOSURE. The SELECTOR is CLOSED; the AXIS UNIT is OPEN.**
   ✅ **CLOSED, and the kit memory was right about D:** the taper is **ONE stage, not two** — the bytes at
   `0x2A13x` carry `factor = ((tapAB · tapCD) & 0xFFFF) >> 8; S = (factor · S) >> 8`, at-rest 254/256 only
   because **both halves return 255 at rest**, and **`gp-0x6803` picks B × D (`0xCBBC4`)**. The tracer's
   `bVar1 = true` → A×C reading is **wrong**.
   🛑 **STILL OPEN — what the C/D half's X AXIS IS IN.** Adversary A read it as **speed and assumed km/h**
   (**BELIEF**, and A says so), which would put the rail at **2151 at 10 m/s and 736 at ≥ 20 m/s**. The
   record's own on-car tap numbers point the other way — V278 rev 3's `T_meas/T_sim` **0.42–0.51 at
   3–9 m/s**, and the tap's 310 rail on faster routes. **Do not treat the derated rails as established.**
   ⭐ **What is safe either way: the table is IDENTICAL on both builds, so the V282 : V293 ratio holds at
   every speed** — the trade does not depend on resolving the axis. But **2461 is an AT-REST number**, so
   condition every on-car rail read on speed rather than quoting it flat.
5. 🛑🛑 **THE B ADVERSARY'S DEFECT LIST (its §9) — SIX ITEMS, ALL IN MACHINERY OTHER RESULTS REST ON, NONE
   IN THE ARTIFACT.** Every one is a tool or a document, not the image.
   (a) **The module-default `B(f)` fit is BAD.** At `nb = 1, nd = 4` it returns rms `ln|B|` **0.54**,
   phase error **38°**, and **a spurious UNSTABLE 4.5 Hz root**. **Use the design's `nb = 1, nd = 3`**, and
   re-check anything fitted with the module default.
   (b) 🛑 **`r24_plant_refit.py` CANNOT REGENERATE `r24_plant_refit.json`** — its `fit_B(nb=4, nd=2)`
   now raises on the properness guard. **The pre-registration names that family as B1's reference and it
   is not reproducible from its own script.** The JSON on disk is an artifact with **no working producer**.
   (c) **`v293_s3_gate7`'s unbanded `unst` column is MEANINGLESS** — do not quote it.
   (d) **The design scripts modelled Kp 119; the image carries 120.** Every design-script number that
   depends on Kp is off by that one count until re-run.
   (e) **`v293_s4` never ran the stock leg or F7** — its stock comparison and its F7 figure do not exist.
   (f) **`v293_s2` TASK 2C's V293 command leg reads ×2.5 BELOW the second method** — unreconciled.
   (g) **The pre-registration's own anchor caveat (1) is VOID**, and **the r26 sibling arm was omitted**
   from it.
6. 🛑🛑 **r24 ARM CORRECTION — `0xC6440` = 2048 IS THE DISENGAGED ARM, and it reads 2048 on EVERY image
   INCLUDING STOCK.** Honda's stock **engaged** arm is `0xC6446` = **512**. ⇒ **V293's 2048 sets the
   ENGAGED arm equal to the DISENGAGED one**, which is a different and much more interpretable statement
   than "a number between 512 and 5244".
   ✅ **RESOLVED by `advB3b`: the lane is SWITCHED, not gated off.** The selector rungs read
   `g = 1024 if gp-0x671d else 0xC6446 if lateral else 0xC6440` (`0x3ABFE` / `0x3AC08` / `0x3AC12`).
   ⇒ **on V293 the r24 lane is BIT-IDENTICAL engaged and disengaged**, and the on-car anchor's reciprocal
   (**×0.24–0.29**) is therefore **an ESTIMATE of V293's ring, not a lower bound.** ⚠ **Three residuals
   keep it an estimate:** V293 still injects `f(cmd)` (the replay sizes the forced ring at **3.49** against
   V282's **10.30** counts); the disengaged reference is **mostly stationary**; and **the r26 base-assist
   arm `0xC6444` also moves with the `0x3AA96` gate** — unresolved.
7. **Refinement to `TRACE-2026-09-13-fb-lag-filter-bytes`, from `goldenmodel`'s independent march:**
   with **`b = 0` the filter state's absorbing set is `[−10, −1]`, not `{0}`**, so the two-sample feedback
   operand would rest in **`[−20, −2]`** rather than at zero. It does not touch V293 (whose clamp forces
   the *operand* to 0 regardless of the state) and it does not touch V292 (whose cave releases the
   absorbing state at its own `b`), but **any future argument that "the state rests at exactly 0" must
   name its `b`.**
8. 🛑🛑 **NOTHING IN THE FORK MEASURES τ — three separate fields look like identifications and none is.**
   (a) **`liveDelay.lateralDelay = 0.2` is the operator's `SteerDelay` toggle ECHOED BACK.**
   (b) **`lateralDelayEstimate` (0.2479) is ~99 % SEED from previous routes** — 50 blocks, all seeded;
   r39 sat **frozen at 0.2272 for 948 s**. It is gated to **≥ 15 m/s** and reads **livePose yaw, which
   lags the gyro by 73–90 ms.** **Not an identification.**
   (c) ⚠ **A FORK DEFECT, reported not fixed:** `full_lateral_delay(x) = x + 0.2`, and **the toggle branch
   in `lagd` SKIPS that wrapper**, so the field **mixes two conventions** depending on which branch wrote it.
   (d) **The operator's `SteerDelay` 0.2 is a FULL delay**, implying a **vehicle part of 0.0** against
   stock Honda's **0.1 / 0.3**. ⇒ **Quote the measured totals (182–258 ms by speed) and `tau_eq(f)` at the
   crossover. Never quote 0.20 s as measured.**
9. Still standing from earlier today: `DESIGN-V290B` §A.2's per-build free-decay ζ are **not**
   measurements; the ring is **~16 LSB on the 0x18F RATE channel** (0.17–0.28 LSB was the ANGLE channel);
   r24 is a **lag-4 backward difference on `gp-0x4f62`**, not a 4-tap FIR on `gp-0x6ada`; the record's
   "×33–72 engagement gating" is a presence RATE and the amplitude ratio is ×4.5.

### ✈ NEXT — in order
0. ⭐ **THE OPERATOR FLIES REV 5 (2026-09-15):** the device already carries `e44b6cd31` + the r5 config (rebooted). Score with
   `v293_flight_read.py <tag> --config toggle-config_V293_torque_mode_r5.decoded.json` (attribution: commit `e44b6cd31`, `AccordDobHz 0.6`,
   Kp 1.0000 on the wire, the OBSERVER line non-zero, `SteerFriction 0.0`) then `v293r5_observer_read.py <tag> r75_v293r4` (O1 on the wire ·
   O2 loose · O3 confident · O4 jerky · O5 sensible; revert triggers in its docstring). **He scores loose / jerky / confident in his words.**
   If O2/O3 pass and O4 fails: `AccordDobHz 0.4` and/or `SteerKP 0.85` by config. If the observer pins at ±0.3 or a 0.6–1.5 Hz oscillation
   appears: `toggle-config_V293_torque_mode_r5_REVERT_to_r4.json`. The next lever after a good rev 5 is the identification of b(v) per speed
   (it decides whether the model-predicted damper can ever be safe) — not firmware.
1. *(superseded by 0)* ⭐ **THE OPERATOR FLIES REV 2 (his call):** device fork → `66cf4454a`, restore `toggle-config_V293_torque_mode_r2.json`,
   restart; drive the same kind of route as route 70 (low-speed manoeuvres, a motorway stretch, a few hard
   transients); score with `v293_flight_read.py <route> --config …_r2.decoded.json`; **he scores the four symptoms in
   his words.** Revert triggers unchanged (darty/loose, one-sided pull, oscillation, grinding) plus "ratchet worse
   than route 70" from the scorer. Watch the FIRST 30 s at low speed (the least-known band).
2. **If the ratchet statistic does not fall toward the V282 references:** rung 2 of
   `DESIGN-NOTE-INNER-LOOP-QUANTITY` — a 100 Hz rate-feedback term in the fork (code), never an
   angular-acceleration loop, never a half-open fb clamp. **If 3–8 m/s stays marginal:** reshape the low-speed
   factor for the Accord (code). **If the tracking gain does not flatten:** re-identify the tables on the rev-2
   drive (the plant FF now carries the identification, so the next fit is cleaner).
3. **The EME / governor dwell residual is NAMED, not closed:** the 205-count band
   **`5120 < |cmd| ≤ 5325` needs 75 ms continuous residency** to arm SM2. It exists on V282 too and
   SM2/SM3 self-clear, but nothing has ever measured the dwell on the wire.
5. **The IMU stays the top missing instrument** (road vs rack vs motor). No drive so far separates them.
6. **Two open premises other builds have already leaned on:** `gp-0x6806`'s engaged state, and **the
   taper's X-AXIS UNIT** (the selector is closed — D — but whether the axis is km/h is BELIEF, and it
   decides whether the rail derates to 2151/736 or not; see correction 4). Because the taper is one
   speed-derated stage, **condition any on-car rail read on speed** rather than quoting 2461 flat.
7. Standing: golden model **94 symbols** — 🛑 **90 → 94 this close-out, when the LKAS RATE PID ITSELF was
   added** (`lkas_rate_pid_tick`, `lkas_rate_pid_surface`, `lkas_rate_lerp`, `lkas_output_lag`, SECTION 5D
   of `eps_chain_control.py`), closing the gap that had left V288's and V289's mirrors with no caller;
   a fifth new def, `_self_check_v293`, is deliberately NOT re-exported. `_self_check()`+`_demo()` sha256
   `740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d` (2,512 B) — **unchanged**, because
   every `_self_check_v2xx()` asserts and prints nothing. **Contract re-verified independently at close-out:
   94 / 2,512 B / `740f4bcd…`, and `_golden_contract_syms.json` carries the four new names.**
   `CLAUDE.md`'s contract line is already at 94;
   🛑 **the lineage SPLIT happened this close-out** — `docs/BUILD-LINEAGE.md` is the entry point,
   **new per-build entries from V293 onward go in `docs/BUILD-LINEAGE-PART6-V291-ONWARD.md`** (⚠ PART**6**;
   `PART5-V122-ONWARD-MEASURED` already exists and is a different thing). `BUILD-LINEAGE-PART1-LEVER-INDEX.md`
   is over the 150 KB soft target — split it at the next close-out; `0xC61C0/C2/C4` still has no lineage entry.

**Session reports (2026-09-13 night — the flight):** `rlog-tools/studies/grind/V293-FLIGHT-READ-r70-2026-09-13.txt` ·
`V293-PLANT-IDENT-2026-09-13.md` (+ `v293_ident_*.py`) · `docs/research/FORK-LATERAL-PATH-V293-2026-09-13.md` ·
`DESIGN-NOTE-INNER-LOOP-QUANTITY-2026-09-13.md` · `docs/review/ADV-REV2-FORK-PACKAGE-2026-09-13.md` ·
`docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md` · `tools/make_galaxy_toggle_config.py` · handoff
`docs/handoffs/2026-09/HANDOFF-2026-09-13-v293-flew-plant-is-a-spring.md`.
**Earlier 2026-09-13 reports:** `rlog-tools/studies/grind/V292-FLIGHT-READ-2026-09-13.md` (+ `v292_flight_*.py`,
`extract_v292_routes.py`) · `docs/review/ADVERSARIAL-V292-PREREG-2026-09-13.md`,
`ADVERSARIAL-V293-PREREG-2026-09-13.md` · `docs/specs/design/DESIGN-V293-TORQUE-MODE-2026-09-13.md`
(+ `v293_s1`…`s10`, `v293_lib.py`) · `docs/traces/TRACE-2026-09-13-lkas-pid-tracked-quantity.md` ·
`docs/research/ARC-GROUNDING-TORQUE-MODE-AND-ACCEL-TRACKING-2026-09-13.md` and
`FORK-LATERAL-DESIGN-FOR-TORQUE-MODE-AND-RATE-TARGET-2026-09-13.md` (each now carries a **Reconciliation**
note pointing at the other and at the prereg's dispositions) · `docs/guides/TORQUE-MODE-TOGGLE-CHECKLIST-2026-09-13.md` ·
`analysis-2020accord/builds/v108_plus/build_v293_tva.py` · handoff
`docs/handoffs/2026-09/HANDOFF-2026-09-13-V292-FLEW-REVERT-V293-TORQUE-MODE-BUILT.md`.
**The superseded 2026-09-13 V292 decision box is archived in
`docs/archive/STATE-ARCHIVE-2026-09-13-v292-decision-box.md`**, and the 09-09/09-10 boxes in
`docs/archive/STATE-ARCHIVE-2026-09-13-decision-boxes-0909-0910.md` — records, not instructions. Nothing
was retracted by either move; every still-decision-bearing correction is in the paragraphs above.

---


## 📁 **THE V279-ERA REFERENCE AND 84 FINDING BLOCKS (2026-08-30 → 2026-09-11) ARCHIVED 2026-09-13**

Moved to `docs/archive/STATE-ARCHIVE-2026-09-13-v279-to-v290-blocks.md` at the V291 close-out to keep this file
under its working target. **A record, not an instruction.** Nothing was retracted by the move; the decision box
above carries every correction that was still decision-bearing.

## 📁 **EARLIER BLOCKS (24) ARCHIVED 2026-08-30**

Moved to `docs/archive/STATE-ARCHIVE-2026-08-30-probe-audit-era.md` to keep this file under its
working target. **A record of what was believed then, not an instruction.** Nothing was retracted
by the move.

## 🗂 INDEX TO THE BLOCKS BELOW

| what you want | look for the block titled |
|---|---|
| the flight order | *FLIGHT ORDER — A CHOICE, NOT A SINGLE BUILD* |
| why V222’s ratchet is a risk | *THE 8× IS COVERED WHERE THE OPERATOR FELT IT — BUT NOT AT THE RATCHET* |
| what V228 is | *V228 BUILT — V222 WITHOUT THE 8×* |
| the audible side effect | *"V228 CANNOT MAKE ANYTHING WORSE" IS FALSE* · *THE 40–49 Hz LIFT IS UNAVOIDABLE* |
| **my own withdrawn claims** | *SELF-CORRECTION: THE ABSOLUTE "r24 DAMPS" LABEL IS DOWNGRADED* · *CORRECTION TO THE BLOCK BELOW — AND TO MY OWN r24 ANCHOR* · *CORRECTION: "V62’s lever CREATED grind #2" is NOT settled* |
| what measurement can and cannot do | *THE RATCHET BAND CANNOT BE SCORED BY BAND POWER* · *RING-DOWN COMPUTED* · *CROSS-BUILD EVIDENCE HAS NEVER BEEN PRICED AGAINST ROUTE VARIATION* |
| what is closed and will not be re-proposed | *THE CAL-LEVEL SEARCH IS COMPLETE IN EVERY DIRECTION* · *THE NOTCH IS NOW CLOSED* · *EXACTLY ONE BIQUAD* · *FOC CURRENT LOOP IS TRANSPARENT* · *LEVER A r26-HALF ONLY* · *r24 IS AT 94 % OF A STRUCTURAL PHASE CEILING* |
| what is still open | *THE TWO REMAINING QUESTIONS BOTH NEED A CAVE* · *OPEN OBSERVATION — an 11.4× residual* · *THE FRAME TEST IS INCONCLUSIVE* |
| the session narrative | *SESSION HANDOFF* (last block) |

---



## 📁 **EARLIER BLOCKS (22) ARCHIVED 2026-08-30**

Moved to `docs/archive/STATE-ARCHIVE-2026-08-30-probe-audit-era.md` to keep this file under its
working target. **A record of what was believed then, not an instruction.** Nothing was retracted
by the move.

## 📁 **EARLIER STATE (V204 → V208) IS ARCHIVED — with its closures kept here**

Split out 2026-08-30 at **138.6 KB**, against the ~150 KB soft target. The narrative, the numbers
and the retractions now live in `docs/archive/STATE-ARCHIVE-2026-08-30-v204-v208.md` — **a record,
not an instruction.** What that era CLOSED is kept below, because a closure is what stops a lever
being re-proposed:

| closed | verdict |
|---|---|
| the notch shelf | was cutting a **real 6–9 Hz damper 7.15× below the car**; fixed V214–V217 |
| the saturation census | **closed** — the last gate cannot fire; V207 retired **before** flight |
| `gp-0x6b70` saturation | **does not saturate**; V206’s best argument retracted |
| the command-gated-saturation model | **no mechanism exists** in this path — no gate rejects either |
| the 8 Hz ratchet notch | **stays rejected**; the friction lane is NOT "reverted to Honda" |
| two authority levers | **checked and closed**; a latent 18.52 Hz injector found silent |
| `0xC63AA` sensitivity | **41× understated** in the old record |
| the relay | a **SOFT** relay, curve **built at runtime** — unreadable from the image |
| `0xC63AE` sign | established **without a drive**; V206 built and priced |

🛑 **Tooling gotcha kept live, because it still bites:** `stock_fw_dump/code.bin` reads `0xFFFF`
at `0xC6CD0` because **V57 created that cell**. Do not use the stock dump as a stock reference for
post-V57 migrated cals — it hands you 65535 and a 0.08× "stock gain". `0xC646C`, `0xC61BE` and
`0xC64DE` read correctly from it.

## 📁 **EARLIER STATE (V184 → V202) IS ARCHIVED**

Split out 2026-08-30 at **173.6 KB**, past the ~150 KB soft target. Everything from the V202 notch work downward now lives in `docs/archive/STATE-ARCHIVE-2026-08-30-v184-v202.md` — **a record, not an instruction.** All of it is superseded: the candidate is **V222**, the ladder is V223–V226, and that notch was replaced at V208 and again at V217/V222.
