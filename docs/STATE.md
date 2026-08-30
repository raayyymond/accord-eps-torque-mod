# STATE — living current state of the kit


> 🚩 **FLIGHT ORDER: V222.** = **V221 with four bytes REMOVED from the delta.** Delta from the CAR (**V122**) is **23 payload bytes** — notch 20.50 Hz (grinding) · `0xC63AE` 512 (ratchet) · `0xC6CD0` 6×→8× + clamps (authority) · `0xC6446` 5244→13107 (Lever B) · the 427 probe. Every deliberate lever is byte-identical to V221; what changed is that the friction lane now matches the car at EVERY rate rather than only below its knee. Drive card: `docs/scoring/DRIVE-CARD-V222.md`. **V221 is the fallback** (`DRIVE-CARD-V221.md`), V217 behind it. Shelf: `docs/scoring/SHELF.md`. Pre-registered scoring: `docs/scoring/SCORING-V217-preregistered.md` (applies to all three).

> ⭐ **V227 — THE ONE RATCHET LANE NOBODY HAS SCORED.** The model’s lane census calls `gp-0x6ad4` *"the most reachable authority of any gated lane"* and states that **V56’s mute of it was scored at ~21 Hz, so the lane has NEVER been scored at 6–9 Hz — OPEN, not eliminated."* Its return-to-centre analysis independently narrows the ratchet’s entry to a **sensor-fed** lane, leaving {r24/r26, `gp-0x6ad4`, `gp-0x6b26`, `gp-0x6bbe`, the plant-model path} — and of those, r24 is Lever B (already at 13107), `gp-0x6b26` is the restored damper, `gp-0x6bbe` sits at 76 % of its rail, and the plant-model path is `0xC63AE`. **`gp-0x6ad4` is the one left.** The lever is its ceiling LERP knee: `0xC67C4` **1280→512**, so the ceiling reaches full at **8 km/h instead of 20** — **3.00× at 3 and 6 km/h, 2.25× at 10, and IDENTICAL from 20 km/h up**; Y is asserted unchanged, so it moves the KNEE not the height. **Virgin in 216 of 218 images** — only V162/V163 ever carried it, and that branch was orphaned at the rebase to V164, **the same rebase that orphaned Lever B’s 6553**. Built as **V227 = V222 + one halfword**, 78/78. 🛑 **OPEN lever, NOT a predicted fix**: whether more authority there damps or **pumps** 6–9 Hz depends on a loop phase nobody has measured — that is what "never scored" means — so **it can make the ratchet worse**, and it is cal-only and reversible. ⊕ Gate [19] **correctly fired** on the table-knot move; it is now a **build-scoped** exception naming one cell on one build, with a staleness check, rather than a widened whitelist. **1107 checks, 0 failed.**

> 🛑⭐ **THE "459×" HEADLINE FOR THE ABORTED DRIVE IS RATE-CONFOUNDED — the within-spectrum figures are not.** That number is normalised against a **creep-matched** corpus median, i.e. matched on SPEED only, and at the same speed r7d’s wheel was running **6.6× faster** than its control (|rate| p50 24.00 vs 3.61). Whether that matters is testable without r7d, on the routes that have exposure: over **1,368 engaged windows across 7 routes** (6 of 7 positive), **log 30–35 Hz power vs log RATE corr +0.739 (p<0.0001)** against **vs log SPEED corr −0.182** — weaker *and negative*. By rate quartile the band moves **63×** across the range. ⇒ a speed-matched comparison leaves that 6.6× inside the number, so **459× is an UPPER BOUND, not a measurement.** ⊕ **The same run says how to normalise it away**: `log(30-35 / 12-18) vs log RATE` has **corr −0.041, p=0.13 — no rate dependence at all**, because rate lifts the bands together. So a band-to-control RATIO is rate-robust while raw band power is not. ⇒ **what survives is every r7d figure that is a within-spectrum ratio** — prominence **56×**, **56 %** of 5–49 Hz power sitting in 30–35, and the engaged/manual contrast **54×** (same route, same rates on both arms). 🛑 **r7d is NOT withdrawn** — it is re-based onto statistics it already had. Study: `analysis-2020accord/studies/mixer/the_459x_is_rate_confounded.py`.

> 🛑⭐ **RETRACTION — MY OWN "CUTTING APPARENT INERTIA RAISES LOOP GAIN BROADBAND" DOES NOT SURVIVE.** I measured it **creep-matched, i.e. SPEED-matched**, over 9 routes (corr −0.853 / −0.747 / −0.574 / −0.790, every band together). It was already flagged as carried by one drive (perm p 0.0087 → 0.2486 without `r7d`) and confounded with build order (+0.750). I then established separately that **speed-matching a rate-driven signal manufactures an effect** — and `gp-0x6b26` is `-K*alpha`, acceleration feedback, **rate-driven**. So it was built on the estimator I had just shown to be wrong for this class of signal. Re-run rate-matched: **every correlation flips POSITIVE** (+0.23 to +0.74) and **none is significant** (all p ≥ 0.19); and 🛑 **r7d is absent from every rate bin** — 1,084 engaged frames is too few for a windowed spectrum, so the instrument **cannot test the low-dose end at all**, which is exactly where the effect was claimed. ⇒ **the inference is WITHDRAWN**: one drive, confounded with build order, measured on the wrong axis, sign-unstable when corrected. ⊕ **What stands:** the *description* of r7d (the ≈31 Hz line, in-loop, absent from the command), and the build decision — V214–V217 restored the damper to the car’s own value on *"match the flown image"*, never on a dose-response. Study: `analysis-2020accord/studies/mixer/inertia_dose_broadband_lift_retracted.py`.

> ⭐ **THE RATE-MATCHED INSTRUMENT NOW WORKS — and the knee trend it finds does NOT survive its own checks.** Gating SAMPLES on instantaneous rate fragments the signal below a spectral window (0 usable windows in 3 of 4 bands). Classifying **whole windows by their own median rate**, with a within-window spread cap p90/p50≤3, gives **175/86/148** windows in the slowest bin. The manual side is still empty at low rate on these routes, so each window is normalised **within itself** against the 30–40 Hz control band — alias-contaminated, but identically on every route, so usable as a cross-route normaliser and nothing absolute rests on it. Tool: `rlog-tools/score/rate_matched_band_ratio.py`. **What looks like a finding:** grind 15–22 is monotone decreasing in onset at 3–8 (4.133/3.603/2.580) and 8–20 (5.493/5.449/2.965), with V111-vs-V122 CIs **disjoint in both** — read alone, a sharper relay carries MORE grind energy, so V222’s knee restoration would REDUCE it. **Why it is not claimed:** the largest bin (0–3, n=175/86/148) sorts **nothing**; the ratchet band at 8–20 is **non-monotone** while grind is monotone, which a loop lever should not do; the **middle** onset is highest in mid 9–12, a route signature; onset is confounded with build number; and the arithmetic predicts no effect below 50 counts of rate anyway. ⇒ **[BELIEF, WEAK], not claimed** — and the V222 drive settles it for free, since V222 sits at onset 250 where the whole V196–V217 shelf sat at 50. Study: `analysis-2020accord/studies/mixer/relay_knee_ladder_window_classified.py`.

> ⭐ **A SLOPE-CONTROLLED, THREE-POINT, FLOWN LADDER ON THE RELAY KNEE — AND IT SHOWS NOTHING.** Route `r21`’s cache said **"UNKNOWN-V108-or-V111"**; V108 and V111 differ in only 3 payload cells with a **byte-identical cave**, so the rungs cannot tell them apart. Resolved from the record (`HANDOFF-2026-08-28-v112` tabulates `r21 V111`, written by the session that flew `r22` as V112 whose own base is V111), which unlocks **83,782 engaged frames** and exposes a ladder nobody had noticed: **V111/r21 onset 50 · V112/r22 onset 150 · V122/r24 onset 250**, all with the **same unsaturated slope 0.003984**, and V111→V112 a **true single-variable pair — 2 cells, 4 payload bytes**. That is the controlled experiment the record’s *"de-relaying made the ratchet 2.3× worse"* never had. **Result: non-monotone in every symptom band, and the CONTROL band orders identically to them** (both [0,2,1]) ⇒ route difference, not a lever. ⊕ **It agrees with the arithmetic**: with the slope held the three settings are identical below 50 counts of rate, and the ratchet lives at 1–13 °/s — so V222 restoring the knee 600→3000 should not move the symptom bands, and does not. 🛑 **Method limit: rate-gating and Welch are incompatible** — gating on an INSTANTANEOUS rate fragments the signal below a spectral window and **3 of 4 rate bands returned ZERO usable windows**. This is a WEAK instrument that found nothing, not a strong one that proved nothing. Study: `analysis-2020accord/studies/mixer/relay_knee_flown_ladder_null.py`.

> 🛑⭐ **THE ABORTED DRIVE’S FRICTION RELAY WAS NORMAL FOR ITS RATE — and speed-matching said otherwise.** `r7d` flew V94, which carries V90’s cave **byte-for-byte**, and `r77` flew V90 — so both read **the same rungs** with **identical friction cals** (`0xC40BC` 600, `0xC40D2` 102). That makes `r77` the natural control for the aborted drive and nobody had used it. Speed-matched at creep it looks like a finding: `b5` (*the modelled Coulomb friction is non-zero*) reads **0.746 vs 0.886**, 1.19× more relay activity on the drive that was stopped. A 1 s block bootstrap already refused it, and the reason is one column nobody would print: **at the same SPEED the aborted drive’s wheel was moving 6.6× faster** (|rate| p50 3.61 vs 24.00). Matched on the axis the relay’s own arithmetic uses — `ratio = clamp(rate*12/cal(0xC40BC), ±1)` — the difference **vanishes**: b5 reads 0.466/0.473, 0.997/0.962, 1.000/0.992 across matched rate bands, largest gap **0.035**, and marginally LOWER on the aborted drive; b6 has no consistent direction. ⇒ **[EVIDENCE] the firmware’s own friction state on that drive was normal for its rate**, so **its signature is not in the friction lane**. 🛑 **Method: speed-matching a rate-driven signal manufactures an effect** — the same trap the record already names for the ratchet, on a different quantity. ⊕ The rung values come from `rlog-tools/probe/sweep_cave_rungs.py`, added the same day; it also corrects two defects in its own first version, the important one being that `r97` has **NO CAVE** (probe byte stuck at stock 0x07 across 68,883 engaged frames) rather than five rungs that never fire. Study: `analysis-2020accord/studies/mixer/aborted_drive_friction_relay_is_normal.py`.

> ⭐ **THE DELIVERED COMMAND’S SYMPTOM-BAND CONTENT IS SENSOR-SHARED, NOT COMMAND-SHARED — measured on `gp-0x6b94` ITSELF.** The stated lever class is *"less broadband HF in the delivered command"*, but that had only ever been argued from proxies. Route `r85` flew V100, whose 427 probe telemeters the aggregator output itself with its sign on a cave bit, and that cache had never been used this way. Coherence² over **60 engaged 4 s windows**, both inputs on the SAME windows: **2–4 Hz 0.163 vs 0.041 · 6–9 Hz 0.235 vs 0.085 · 9–12 Hz 0.134 vs 0.049 · 12–18 Hz 0.241 vs 0.051** against a shuffled null of 0.002–0.006 ⇒ **2.9–5.2× more coherent with the COLUMN than with openpilot’s request, in every band including the ratchet’s.** Whatever sits in the delivered command there is **loop content, not commanded content** — the same conclusion V88’s signed-command test reached from the other side, and **independent support for Lever B’s lever class**. 🛑 **The control had to be fixed first**: the initial shuffled-pairs null read **exactly 1.000** because a coherence from ONE segment pair is identically 1 — the null must average over MISMATCHED pairs the way the measurement averages over matched ones. ⚠ Limits, stated: **closed loop so no causal arrow**; absolute coherences 0.13–0.24 so neither input alone explains most of the variance; `r85` is **highway (11.0 m/s), not creep**; and nothing above ~20 Hz, since 427 is a ~50 Hz stream ZOH’d to 100. Study: `analysis-2020accord/studies/mixer/delivered_command_is_sensor_fed_not_commanded.py`.

> 🛑⭐ **THE TWO CLAMPS THAT COULD ZERO THE RATCHET LEVER NEVER SATURATE — MEASURED, WITH A LIVE CONTROL.** The golden model warns that `|gp-0x6ad6| >= cal(0xC6200) = 8192` makes `d(gp-0x6ad4)/d(gp-0x6b70)` **exactly zero through P, I and D at once**, and flagged both clamps as **never measured**. That bears directly on the shelf: the ratchet lever `0xC63AE` acts by scaling the residual into `gp-0x6b70`, so a saturating reference clamp would make it dead on those frames — the V64 failure, *"the null is on the GATE, not the hypothesis"*. **The measurement existed all along: V100 flew as route `r85` and its cave carries exactly these two bits.** Pooled over six cached segments, **49,850 engaged frames: d(b5) = d(b6) = 0.000000**, 95 % upper bound **6.0e-05**. 🛑 **The positive control is what makes it a result rather than a dead probe** — same cave, same route: `b3` is the deliberate constant-1 identity bit (the cave RAN) and `b4`/`b7` toggle **4,343** and **3,153** times. ⇒ **[EVIDENCE] neither clamp saturates engaged**, the `0.2565 @ 7.79 Hz` unsaturated derivative is valid essentially always, and **the ratchet lever is NOT gated off**. ⊕ It transfers to the candidate in the SAFE direction: `gp-0x6b70` IS term 7 of `gp-0x6ad6`, and V222 HALVES `0xC63AE`, shrinking that term — if V100 never reached the clamp, V222 reaches it less. ⚠ Directional for term 7, not a proof for the whole sum. 🛑 `0xC6200` is **four things at once** and has **40 readers** — do not edit it. Study: `analysis-2020accord/studies/mixer/pid_reference_clamp_duty_measured.py`; the model’s stale note is corrected in place, contract re-verified.

> 🛑⭐ **LEVER B’S INPUT HAS A SILENT KILL-SWITCH, AND A FLOWN DRIVE BOUNDS AN OPEN CLOCK QUESTION.** `gp-0x4f62` is produced by `FUN_0007e74a` as a **span-N finite difference over an 8-slot ring**, N = `0xC6C42` = 4, dividing by the MEASURED dt — so the magnitude is right at any rate and **only the PHASE depends on the span**, `lag = 180*f*N*T`. 🛑 **The code’s own guard is `if N < 8 ... else gp-0x4f62 = 0`, so writing 8 or more ZEROES the torque rate and kills r24 AND r26 together** — Lever B would report its full 13107 gain and deliver **nothing**, and every existing check would still pass, because they all check the GAIN and never its input. `0xC6C42` = 4 in **all 218 images**, so it has never bitten; a gate now asserts it and was negative-tested. ⊕ **V88 bounds the producer rate**: the SIGN of an effect at a known frequency is a phase measurement, and V88 measured **15–22 Hz → 0.549×, i.e. DAMPING**. A span-4 difference stops damping at 90°, which at 20.5 Hz needs T ≥ 6.10 ms ⇒ **the producer runs faster than ~164 Hz, and a 100 Hz ring is EXCLUDED** (it would have PUMPED, cos = −0.844). The measured profile corroborates it — damping STRENGTHENS with frequency (0.859 → 0.604 → 0.549), where a lag near 90° would weaken it. ⇒ **at ~1 kHz the lag is 5.6° at 7.79 Hz, so Lever B is already near-pure damping and there is NO lever here — N = 4 left alone.** Study: `analysis-2020accord/studies/mixer/lever_b_input_phase_and_killswitch.py`.

> 🛑⭐ **THE THREE RUNG-2 ARMS WERE STALE — REBASED ONTO V222 AS V224/V225/V226.** V218, V219 and V220 were cut off **V217**, so each LACKED **Lever B at 13107** and the **friction-lane restoration**. Flying one after V222 would have **silently handed back two levers** — the same failure shape as [[V42’s ratchet fix lost at a rebase]] and the damper cut hidden inside V196–V213. Each arm is rebuilt on V222’s base carrying its own lever and nothing else: **V224** `0xC63AE` 512→256 (ratchet) · **V225** `0xC6CD0` 8×→10× **with its clamps** `0xC61B3/B5` 16→18 (authority) · **V226** notch poles 15.50→13.50 (grind). **All five builds — V222, V223, V224, V225, V226 — now share the same 23 payload bytes from the car**, differing only by the one lever each exists to test. ⊕ Registered in all three verifier lists, and a **new gate** makes the 10× arm’s clamp raise mandatory: a gain raise without `0xC61B3/B5` = 18 is not the priced build and now fails. ⇒ **1044 checks, 0 failed** (was 950).

> 🛑⭐ **THE CLOSE-OUT DID NOT COVER THE FLIGHT CANDIDATE.** `PUB` in `closeout_verify_published.py` **stopped at V220** while **V222 was the recommended build**, so the artifact being handed over for flashing had passed **none** of the 835 checks — not gate [17]’s delta manifest, not [14]’s damper pricing, not [16]’s cave anchor, not [21]’s notch arm. Cause: three separate build lists (`PUB`, the shelf rebuild, the 427 decoder) and only two were kept in step. **Adding V221–V223 immediately fired two gates, both correctly:** the staged-gain gate (they carry V217’s 8× step byte-identically — added to the priced set with the reason recorded) and the **Lever B anti-drift gate**, which is the protection that catches silent lever loss. 🛑 **It was NOT widened**: Lever B is now a deliberate ladder, so the gate keeps ONE expected value per build and enumerates it — 13107 for V221/V222, 26214 for V223, **5244 as the default for every other build**, so an unlisted or new build still fails on drift. ⊕ Negative-tested: reverting V222’s Lever B, demoting V223’s rung, and moving one rail byte each made the gate fire; images restored and hash-verified. ⇒ **835 → 950 checks, 0 failed.** ⊕ Same tick: an audit of every checkable numeric claim in the golden-model facade — **4/4 survive**; the pedestal figure was its only error. New do-not-edit fact: `0xC6200` (the assist-map input clamp, 8192) has **40 readers**.

> 🛑⭐ **THE NOTCH’S PEDESTAL BYPASS IS OVERSTATED 4.1× — A CORRECTION TO THE FILE AGENTS READ FIRST.** The golden-model facade warns that `gp-0x6b7e`, added to the biquad output AFTER the filter, *"passes 64.6 % of its input STRAIGHT PAST THE BIQUAD"* at 19.75 Hz. **That figure is the clamp ceiling (K = 204), not the cal.** Read from the image: the direct cal `0xC6382` = **41**, and the 4-point LERP at `0xC6906..0xC690C` has Y = **[20, 20, 20, 20]** — **flat, so not a shaped lever at all**. The reachable set is K ∈ {20, 41}: fc 1.55 / 3.19 Hz, |H(20 Hz)| = **0.078 / 0.159**. ⇒ **max bypass 0.159, not 0.646**, and **the notch is correspondingly LESS diluted than the record has been claiming** — good news for the shelf’s main grinding lever. Both cals are **VIRGIN in all 215 images**; driving K to its floor of 2 takes the bypass to 0.008 but caps out at removing a 15.9 % path, so it is a small lever, not the missing one. ⚠ This bounds the pedestal’s TRANSFER, not how much 20 Hz energy its input carries — only a measurement settles the split. ⊕ Re-confirmed while tracing: `gp-0x6b86` is the **base power-assist** output, not the LKAS command, so **no notch dose can cost LKAS authority or fix command oscillation directly**. Golden-model contract re-verified after the edit: 87 symbols, 2,512 bytes, hash unchanged.

> 🛑⭐ **LEVER B’S REAL CEILING IS ITS DESCRIBING FUNCTION, AND V222 IS NOWHERE NEAR IT.** The lane is a plain saturation (slope k, rail ±8192), so for a sinusoid of amplitude A the effective damping the loop sees is `N(A)/k = (2/pi)[asin(1/rho) + (1/rho)sqrt(1-1/rho^2)]`, `rho = k*A/(L*1024)`, and as k→∞ it tends to `4L*1024/(pi*A)` — **a constant independent of k**. That asymptote is the ceiling, not the cal range and not V160’s non-existent int16 bound. Evaluated at route `r24`’s engaged torque-rate percentiles: the knee (one more doubling buys <20 %) is at **k = 58624 for p90, 14080 for p99 and 5184 for the largest excursion**. ⇒ **at the amplitudes where the roughness lives, V222’s 13107 is far below the knee** — one more doubling buys a full **2×** at p50 and p90 — **while buying essentially nothing at the largest excursion** (1.20×→1.23× even at the cal maximum), so the rung is selective for the small-signal regime by construction. ⊕ **The saturation worry is not new: the car at 5244 is ALREADY past the large-amplitude knee of 5184**, and V88’s measured win came from 512→5244, the very step that carried the largest excursions across it. **V223 = V222 + 13107→26214** is built as rung 2. Study: `analysis-2020accord/studies/mixer/lever_b_describing_function_optimum.py`.

> 🛑⭐ **THE CAL-LEVEL SEARCH SPACE FOR CREEP-REGIME DAMPING IS EXHAUSTED.** Roughness is a small-command phenomenon, so the lever must live at creep. Every cal path there is closed, from the bytes. **The base-assist damper is a PRODUCT of five Q10 LERP gains and two are exactly zero at creep** — FactorC (axis SPEED) is dead below 35 km/h and FactorE (axis RATE) below 60 counts, and since both `Y[0]` are 0, **scaling any record by any k is structurally vacuous**. ⊕ **The edit nobody has ever made:** across **all 214 images on disk** the FactorC X axis is `(2240, 3840, 5120, 8960)` — **exactly one distinct vector, never once moved** — while `Y[0]` has been set **nine** different ways across ~40 builds. Every arming attempt raised `Y[0]` at a FIXED `X[0]`, which puts a **step** at 35 km/h; that is how V80 became a relay and flew as the worst grinding ever measured. So the untried edit is lowering `X[0]` to extend the RAMP down — V80’s own stated lesson — and **it fails too**: even at `X[0]` = 64 (1 km/h) the product reaches only **0.096 % of full gain**, because FactorE contributes just 5.6 % at a 200-count motor rate. The other four candidates are each closed on their own terms: `gp-0x6bbe` (the one measured viscous lane) is already at **76 % of its ±512 rail** so its virgin weight `0xC63A2` would amplify a part-relay signal; `0xC40D2` needs k1 = 25600 to halve the residual at 5 °/s, **25× past the sign-inversion boundary**; ranking the lanes from the 427 probe’s seven historical source cells is not possible from the existing caches (only `r95` carries a decoded 427 magnitude channel); and a notch is already excluded because the ratcheting is not a tone the EPS commands. ⇒ **what remains is to fly what is built, or a code cave** — this kit’s only bricking class. Study: `analysis-2020accord/studies/mixer/creep_damping_search_space_closed.py`.

> 🛑⭐ **V216 RESTORED THE FRICTION LANE’S SLOPE BUT NOT ITS SATURATION — A 216× DIFFERENCE FROM THE CAR ON FAST STEERING.** `FUN_0003b8f6` is the **plant-model observer**: `ratio = clamp(polarity * gp-0x6abc * 12 / cal(0xC40BC), -1, +1)`, `friction = EMA(|model| * ratio * cal(0xC40D2)/1024)`, `model_out = clamp((model - (friction + damping)) * cal(0xC6468), +-20000)` → `gp-0x6b70`. The unsaturated slope is `12*k1/gate/1024` and V216 matched the car **exactly** (0.003984 both: car gate 3000/k1 1020, shelf 600/204) — which is why every check passed. But what each SATURATES AT is `k1/1024` of the whole model: the car models friction at **99.6 %** and the shelf at **19.9 %**, so above 250 counts of rate the car’s observer residual is **annihilated** (model_out 7) while the shelf’s stays fully live (1512) — **216×**. 🛑 **The ratchet regime is 1.0× identical at every rate the ratchet occupies**, so no ratchet expectation changes; this is a FAST-STEERING claim only. **V222 restores both cells** and drops the delta from 27 to 23 payload bytes. ⚠ A close-out entry listing `0xC40D2` = 204 as *"the FLOWN car"* was REMOVED — the car is 1020, and that mislabel is exactly why the gap survived. ⊕ **And the record’s headline for this cell is NOT IDENTIFIED**: *"de-relaying made the ratchet 2.3× worse"* (600 vs 6000, 30 routes) held `k1` at 102 while the gate moved 10×, so the small-signal slope fell 10× too (0.001992 → 0.000199). *"De-relayed"* and *"10× less modelled friction"* fit equally well and are different levers. `0xC40D2` alone separates them — 1 reader (`0x3BAFE`), 0 writers, with a **real** boundary at k1 = 1024 where the residual is identically zero and beyond which the sign inverts. Never tested in isolation.

> 🛑⭐ **BOTH TESTABLE READINGS OF "PEAK COMMAND OSCILLATION" ARE NEGATIVE, AND THE ROUGHNESS IS AT THE OPPOSITE END.** 🛑 Bands are instruments — this does not score the symptom, it says where the roughness sits. **(1) The command reversing after a peak: REFUTED twice.** Integral windup fails its own dose-response (reversal vs time-at-rail corr **+0.099, p=0.188**, n=179; partial **+0.101, p=0.177** with lateral demand removed; per-route corrs +0.189/+0.005/−0.167/−0.263/+0.244, **two negative**). ⚠ **And a first result of mine is RETRACTED**: railed-vs-near-rail gave a 2.86× ratio in 5/5 routes, but the control was broken — a near-rail *run* can end because the command wandered out of the band mid-manoeuvre, so its "exit" is an arbitrary sample rather than a peak. On **true local maxima**, measured identically in both arms: railed p75 **0.155** vs not-railed p75 **0.207** (*the control is higher*), and corr(peak magnitude, reversal) **+0.024, p=0.48, n=858**. **(2) The car oscillating while the command is large: REFUTED, and it reverses.** Over **3,711** two-second engaged windows, the roughness ratio P(6–30 Hz)/P(0.5–3 Hz) by command quartile is **2.49 / 2.85 / 2.43 / 0.66** — the top quartile is **3.7× SMOOTHER** (corr −0.358, p<0.0001). Raw HF power does rise (+0.491) but the manoeuvre rises faster (+0.793). ⇒ **the roughness is a SMALL-COMMAND, small-signal phenomenon, so levers must be sized for the MICRO REGIME, not peak demand** — which independently validates V221’s Lever B dose (onset 640 counts vs the car’s engaged torque-rate p90 of 146). Study: `analysis-2020accord/studies/mixer/peak_command_oscillation_two_readings.py`.

> 🛑⭐ **LKAS AUTHORITY NOW HAS A DIRECT MEASUREMENT, AND THE ONE 8× DRIVE IN THE CORPUS IS CONFOUNDED.** openpilot’s command **pins at ±4096 on 2.7 % of engaged frames on the car’s own drive**, in **sustained 475–732 ms runs** (max 6 s), same-signed between runs, with steer rate 6–21× higher than off-rail ⇒ honest saturation in real manoeuvres, not hunting and not a decode artifact. On `r24` the command’s p90 is 733 but its **p99 is the rail**. When it is pinned openpilot has **no authority left**, so rail duty at matched lateral demand (`|curvature| × speed²`) is a direct authority metric needing no plant model. Among Lever-B-carrying builds it is monotone: **4× → 6× cuts rail duty 8.3× / 5.2× / 4.1× / 2.3× / 1.5×** across rising demand bins. 🛑 **The apparent counter-evidence at 8× is a confound**: the single 8× route (`r95`, **V101**) **removed Lever B in the same build** — byte-checked `0xC6446` = 512 and arm `0x3AA96` = `c5`, both stock, against 5244/`fb` everywhere else. More forward gain with less loop damping needs more command to hold a line. ⇒ **no clean 8× data point exists, and V221 is the first build ever to pair 8× with Lever B RAISED rather than removed.** Readout: `rlog-tools/score/score_authority.py` (self-tests to 1.00× on `r24`, 4.05–7.18× on a 4× route). Study: `analysis-2020accord/studies/mixer/lkas_command_rail_duty_vs_gain.py`.

> 🛑⭐ **V160'S INT16 CEILING ON LEVER B IS FALSE, AND IT FROZE THE KIT'S BEST LEVER FOR 130+ BUILDS.** `0xC6446` — the r24 engaged derivative gain, the only lever that has ever moved both symptom families at once with the LKAS command measurably untouched (V88: 15–22 Hz **0.549×**, 9–12 Hz **0.604×**, 6–9 Hz **0.859×**, 0.5–3 Hz **1.192 = NULL**; operator report *grinding fixed, command intact*) — has been **5244 on every build since V67**. V160 raised it to 6553 and called that *"the EXACT int16 ceiling for this lane"*. There is no int16 anywhere on the path. Decompiled first, then confirmed instruction by instruction: `0x3AC08 ld.hu` (zero-extended ⇒ the cal's own range is 0–65535) → `0x3AC18 mul r10,r8,r0` (**32-bit**, high word discarded) → `0x3AC20 sar 0xa` (still 32-bit) → `0x3AC42/46` the ±8192 output clamp, **the only bound, and an immediate**. Worst case 5120 × 65535 = 3.4e8, an order of magnitude inside int32. ⇒ **real headroom above the car is 12.5×, not 1.25×.** V160/V161/V163 built 6553 three times, never flew, and it was orphaned at a rebase to V164. V221 takes it to **13107**, chosen so the saturation onset (640 counts) stays 4.4× clear of route `r24`'s own engaged p90 torque-rate (146) — the micro regime where ratcheting and grinding live remains fully linear. The ±8192 **rail is asserted byte-identical**, so this structurally cannot cost LKAS authority. 🛑 **Only two dose points exist (512, 5244)** and V62's lesson is *"2× is the OPTIMUM, not a point on a ramp"* — so V221 is a **dose probe as much as a fix**.

> 📘 **SESSION HANDOFF:** `docs/handoffs/2026-08/HANDOFF-2026-08-29-the-damper-the-shelf-was-cutting.md` — the damper finding, the mixer decode, five self-retractions, and the open-items list with what would close each. Prior: `HANDOFF-2026-08-29-the-assist-map-session.md`.
## 🛑🛑⭐⭐⭐ **THE NOTCH SHELF WAS CUTTING A REAL 6–9 Hz DAMPER 7.15× BELOW THE CAR — FOUND 2026-08-29, FIXED IN V214–V217**

Chasing the one route that stood out in a newly-added 30–49 Hz band produced the most important finding of the session, and it was a defect in our own shelf.

**`r7d` is the drive the operator ABORTED** (*"made the stuttering and grinding worse, by a lot … it vibrated the entire car, and I decided it was not safe to drive"*). It carries a measurable signature, and every control passes:

```
  sustained engagement-gated line at ~31 Hz
  459x the CREEP-MATCHED corpus median  <- UPPER BOUND ONLY, see below
  prominence 56x  (next highest 13.3x)   <- rate-robust, quote THIS
  engaged/manual contrast          54x
  survives 0.5 s edge trimming     -> not an engagement transient
  56 % of 5-49 Hz power in 30-35   -> a narrow line, not broadband
  speed-invariant across 3 episodes -> not a wheel order (would be order 75.8)
```

V94 flew it after cutting `gp-0x6b26` 6×. That cell was **measured afterwards to be a REAL 6–9 Hz DAMPER** — +137°/+139° vs wheel rate, |cos| 0.73 ⇒ **+518/+565 counts of positive Re(Z)**.

### 🛑 The defect: every notch build carried a LARGER cut of the same cell

```
  V122 (ON THE CAR)   0xD7A5C = (-29490, -17202, -16000)   3.576x Honda
  V196..V213          0xD7A5C = ( -4915,   -2867,   -983)   0.500x Honda   <- 7.15x CUT
```

Reached in two **never-flown** steps (V175 3.576→1.000, V196 1.000→0.500) and carried silently inside builds whose stated purpose is a grinding fix. **Every previous check compared this row to HONDA**, which made a 7.15× change *from the car* read as a tidy "half dose". That is the whole mechanism of the miss.

### The fix took four builds, because each one exposed the next layer

| build | what it corrected |
|---|---|
| **V214** | mode 26 inertia row → the car |
| **V215** | mode 27 too — RULE 7: "mode 27 is unused" is a *memory*, not evidence |
| **V216** | the friction lane — **I had its polarity backwards**; more modelled friction = MORE assist = LIGHTER wheel, so the shelf’s 0.10× was *removing* authority |
| **V217** | `0xC63A6`, the inertia lane’s **weight** in the model sum — the shelf restored the row then fed it in at half weight, keeping net inertia at 0.5× the car |

⇒ **V217’s delta from the car is 19 payload bytes, all levers.** Close-out gate **[14]** now prices `0xD7A5C` against **both** Honda and the flown car, and all six model-lane weights are asserted together so the set cannot drift again.

⚠ **The generalisable lesson, and it is the valuable part:** *comparing a cell to STOCK hides what it does to the CAR.* Three separate cells (inertia row, friction lane, lane weight) all passed Honda-relative checks while sitting 7×, 10× and 2× from what the operator actually drives. **Diff every candidate against the flown image, not against stock.**

---

## ✅⭐⭐ **THE 8× LKAS GAIN IS RE-OPENED — V208's notch changes the trade that killed it three times**

**LKAS authority was the one symptom with nothing on the shelf.** The enumeration is closed —
`0xC6CD0` is the only firmware lever — and it was abandoned at V101, V124/137 and V142/147 because the
record measures **vibration ∼ m^1.74 against authority ∼ m^0.88**. That trade is set by the
**baseline**, and V208 moves the baseline.

### ✅ **ENERGY-WEIGHTED OVER THE GAIN-DRIVEN BAND (22–26 Hz), 130 EPISODES**
```
   V208 attenuation there      3.70x amplitude   (13.6x energy; sqrt = 3.69x -- consistent)
   a 6x -> 8x step grows vib   1.65x             (m^1.74; and 2^1.74 = 3.34 sits inside the
                                                  measured G = 2.7-3.9x for a 2x step)
   ** net vs the car TODAY     1.65 / 3.70 = 0.45x, i.e. ~2.2x QUIETER **
   authority gained            1.29x
```
⇒ **for the first time the arithmetic puts 8× BELOW where the car sits today, not above it.** V101
flew 8× with only Honda's 55 Hz notch and the operator reported grinding at all speeds — **that was at
1.65× the then-current level. This is at 0.45×.**

### 🛑 **A STATISTICAL TRAP I ALMOST PUBLISHED**
My first pass reported **13.63×** and I nearly called that the attenuation. **13.63× is the ENERGY
ratio; 3.70× is the AMPLITUDE ratio**, and they differ by the square. The record's `m^1.74` law was
fitted to `G`, an amplitude ratio — so comparing 1.65× against 13.63× would have overstated the case
by 3.7×. **Squaring the per-bin amplitude ratios (6.1×…2.4×) gives energy reductions 37×…5.8×, whose
weighted harmonic mean is 13.6×, and √13.6 = 3.69× = the flat amplitude average.** The two agree once
labelled. **Compare like with like or a factor of 3.7 appears from nowhere.**

### ✅ **V211 BUILT — AND DELIBERATELY STAGED**
`70b205589b6f81a9…` · 37/37 · preflight 8/8 · **4 payload bytes across 3 cells** (derived, not assumed:
`3072 → 4096` is `0x0C00 → 0x1000`, so each clamp moves ONE byte).
```
   0xC6CD0  5346 -> 7128   the forward gain, 6x -> 8x
   0xC61B2  3072 -> 4096   tracking clamp A   ] at 8x the lane max is 3341, which EXCEEDS 3072 --
   0xC61B4  3072 -> 4096   tracking clamp B   ] this is why V101 had to raise them too
```
**The gates that killed earlier gain builds are asserted in the builder**: `0xC674E` = 5120 must stay
**above** the tracking clamp (the record's own abort condition, and what caps the lever below 10×);
lane max 3341 < 4096 so the clamps do not bind; `0xC407E` stays Honda 511 (V73 raised it, V74/V75
faulted).

### 🛑 **WHAT IT RESTS ON — AND WHY IT IS STAGED**
⚠ **[BELIEF, not measurement]** that the notch attenuates a **command-excited** line. The notch is on
the base-assist path, not the command path — but it is **inside the loop** (motion → column torque →
sensor → assist map → biquad → aggregator → motor → motion), so it lowers the loop gain that
**sustains** the resonance regardless of what excites it. **That is reasoning, not data.**
🛑 **So V211 must NOT be flown before V208 or V209 confirms the grind fix on-car.** If the notch does
not do what is predicted, 8× simply lands at 1.65× and the operator hears it immediately. **The
sequencing is the safeguard, and it is written into the builder's own docstring.**

## ✅⭐ **THE OUTLIERS DISSOLVE, THE PEAK HISTOGRAM WAS THE WRONG STATISTIC — and V208 stands anyway**

### 🛑 **ONE "OUTLIER ROUTE" HAS NO GRIND AT ALL**
Comparing band powers rather than peak locations:
```
   route   P(15-17)   P(19.5-23)   vs cluster median P(19.5-23)
   r97         0.1        0.0            ** 0.01x **      <- essentially NO signal
   r1e         3.2        1.8               0.56x         <- a REAL 15-17 line
```
⇒ **`r97`'s "peak at 15.82 Hz" is `argmax` on a flat spectrum.** There is no grind on that route to
locate. It is not a second mode; it is an absence being read as a frequency.
⇒ **`r1e` is different and real** — a genuine 15–17 Hz line (3.2, second-highest in the corpus) that
outranks its own 21 Hz content. **One route, not a cluster.**
⊕ A prominence floor does NOT catch `r97` — its line is locally prominent and absolutely tiny. **The
right criterion is absolute energy, not prominence.**

### 🛑🛑 **WHICH MAKES THE PEAK HISTOGRAM THE WRONG STATISTIC — including mine, last tick**
An unweighted median over episode peaks gives an episode with 1 % of the grind **the same vote** as one
with 20 %. Weighting each episode by its band energy:
```
   unweighted       median 20.70   p10 16.37   p90 23.05
   POWER-WEIGHTED   median 21.48   p10 19.53   p90 23.05
   the top 10 episodes carry 53 % of all grind energy in the corpus; their peaks:
     21.5  21.9  24.6  21.5  22.7  23.0  23.0  23.0  21.5  21.5
```
**The energy sits at 21.5–23, not at 20.7.** And the corpus band spectrum confirms it directly — it
peaks at **21.09 Hz** with a broad shoulder to 23.4.

### ✅ **BUT ON THE RIGHT OBJECTIVE, V208 IS ALREADY THERE**
The physically meaningful objective is **total residual band energy**, not a distance to a histogram
median:
```
   V208 as built (20.50, poles 15.50, r 0.9575)   residual 0.0671  ->  ** 14.9x energy reduction **
   best possible  (21.75, poles 18.25, r 0.9300)  residual 0.0562  ->     17.8x
   gain from re-cutting again:                                            ** 1.19x **
```
⇒ **V208's skirt is wide enough that its centre is not critical.** The 19.75→20.50 move was worth
1.66× because it was a whole notch-width off; 20.50→21.75 buys 1.19×, which is inside the sampling
uncertainty of a 20-route corpus. **V208 STANDS — now confirmed on the energy objective, not just on a
peak histogram.**

### ✅ **THE SCORER IS FIXED**
`score_drive.py` now reports the **power-weighted** peak as the figure to trust, prints how many
episodes carry half the drive's band energy, and warns outright when a drive has essentially no band
energy — the `r97` failure mode, which would otherwise hand the operator a confident frequency for a
symptom that was not present.

## ✅ **NOTHING PREDICTS THE GRIND PEAK — but the spread is BIMODAL, and V208 is already near-optimal**

### 🛑 **A CORRELATION I FOUND AND THEN RETRACTED IN THE SAME TICK**
Per engaged episode (130 episodes, 23 routes), the 15–25 Hz peak against each episode's own median
covariates: speed **ρ +0.109 (p 0.22)**, |steering rate| **−0.062 (p 0.48)**, |driver torque|
**−0.109 (p 0.22)** — and **|LKAS command| ρ = −0.351, p < 0.0001.** Only one survived, and it looked
like a real command-dependent frequency shift.
**It does not survive the honest n.** The variance decomposition says **within-route / total = 0.24**,
so episodes inside a route are not independent. At **route level (n = 20): ρ = −0.340, p = 0.14.**
⇒ **The episode-level p was pseudo-replication. RETRACTED.** ⊕ This is the same error the record
already names one level down (*"bootstrap over EPISODES, not windows — window bootstraps manufacture
significance"*); the identical trap exists one level up, **episodes inside a route**, and it is not
written down anywhere. **Now it is.**
⇒ **No covariate predicts the grind peak: not speed, not rate, not driver torque, not command.**

### ✅⭐ **BUT THE SPREAD IS NOT A DISTRIBUTION TAIL — IT IS TWO CLUSTERS**
```
   sorted route medians (Hz):
   15.62 15.82 | 19.53 19.92 19.92 19.92 20.12 20.31 20.31 20.70 20.90 21.09 21.48 21.48 21.48
               | 21.88 22.27 22.66 22.66 23.05
   ** 2 routes below 18 (r1e, r97);  18 routes in 19.53-23.05, median 20.99 **
   ** GAP 3.71 Hz with NOTHING in between **
```
⇒ the "p10 = 16.37, so one biquad cannot cover the spread" worry was driven by **two routes**, not by
a continuum. The other 18 sit inside a **3.5 Hz** window.

### ✅ **RE-SCORED ON THE CLUSTER, V208 IS BETTER THAN ADVERTISED AND NEAR-OPTIMAL**
```
   cluster only (112 episodes, 18 routes, peak median 21.09, p10 19.53)
     V208 as built (20.50)          median 10.4x   p10 3.4x
     best possible on the cluster   median 11.6x   p10 3.5x   (20.75, poles 15.50, r 0.9575)
     gain from moving again:        1.11x
```
⇒ **V208's p10 is 3.4×, not the 2.0× the pooled figure implied** — the pooled p10 was two outlier
routes. ⇒ **and re-centring again buys 11 %, inside sampling noise. DO NOT RE-CUT. V208 stands.**

### ⚠ **WHAT r1e AND r97 ARE IS NOT ESTABLISHED**
They are a distinct regime by frequency, but nothing measured here says why. `r97` is the route that
**carried no cave at all** (probe byte constant `7` across 68,883 engaged frames), so it is anomalous
on an independent axis too. **[BELIEF]** they are a different mode or a different era; **not
investigated**, and the notch is deliberately not tuned toward them.

## ✅⭐⭐ **THE NOTCH WAS 1 Hz LOW — re-centred on the peaks the car ACTUALLY makes, 1.66× for free**

Building a single post-drive scorer (`rlog-tools/score/score_drive.py`, which the kit did not have —
~40 tools and nothing saying which to run) meant surveying the grind peak per engaged episode. That
survey moved the notch.

### 🛑 **THE FITTED CENTRE AND THE MEASURED PEAKS DISAGREE**
V195 fitted 19.75 Hz from a **per-route** distribution it recorded as median 20.12 Hz. Surveying the
cached corpus **per engaged EPISODE** — 20 routes, **125 episodes**, Welch on `cs_rate` over 15–25 Hz:
```
   p10 16.37     median ** 20.70 **     p90 23.05
```
The notch is narrow enough that 1 Hz is expensive. Scoring the **actual episode peaks** through each
candidate, under V202's own two constraints (`max|H| ≤ 1.0`, `|Δphase@5Hz| ≤ 8°`):
```
   design                                      dphase   median atten   p10 atten
   V202  zeros 19.75  poles 15.25  r 0.9600    -7.83        5.7x         2.3x
   V208  zeros 20.50  poles 15.50  r 0.9575    -7.98     ** 9.5x **      2.0x
```
⇒ **1.66× more attenuation at the median for the same gate and the same phase budget.** Measured
against V202 directly, the added lag is **−0.11° at 3 Hz** — it is very nearly free.
⚠ The p10 tail gives up 13 % (2.3× → 2.0×). A point fix earns its keep at the median, and the tail is
where one biquad was never going to help — the minimax settled that.

### ⚠ **HONEST LIMIT: 20 routes here, 67 in V195's fit**
The gap between the two medians (20.12 vs 20.70) could be sampling. **What is not sample-dependent:
at whatever the true median is, the notch should sit on it, and 19.75 is below BOTH estimates.** The
re-centre moves toward both.

### ✅ **V208 = V202 with the notch at 20.50 Hz.** 31/31, `max|H|` 1.000000, depth 0.00000 at 20.50.
`e27b4fcc2dafd872…` · poles stay **below** the zeros (Honda's layout), cave byte-identical, 12 payload
bytes. **V209 = V208 + the `gp-0x6b4e` probe**, 40/40, preflight 8/8, `984dfe5590bb8bfe…`.

### ✅ **AND THE KIT NOW HAS A ONE-COMMAND DRIVE SCORER**
`python rlog-tools/score/score_drive.py <tag>` reports exposure and episode count first, then the free
cave rungs with **degenerate readings flagged as uninterpretable rather than null**, the b3
run-validity gate, b6 against its measured-dead expectation, **b5 against its pre-registered range**,
the 427 channel (pointing at the matching decoder rather than guessing the scale), and the grind peak
**stratified by the drive's own episodes**. 🛑 It **refuses to apply the b5 prediction to a route that
is not a shelf build** — caught on its first run against route `a5`, where it would otherwise have
announced a false "the lever is not reaching the car".

### 🛑 **SHELF CONSOLIDATED TO FOUR**
**V209 (fly this) · V208 (the fix) · V206 (ratchet lever, priced) · V199 (low-phase fallback).**
V202, V204 and V205 renamed `SUPERSEDED-DO-NOT-FLASH-DOMINATED-…`.
⚠ **V206 still carries V202's 19.75 Hz notch.** It is a lever on a different question, so it is left
as built — but if it is ever flown after V208 confirms, **rebuild it on the V208 base first.**

## ✅ **THE SAME METHOD DOES *NOT* RETIRE V204 — and the reason is structural, not a shortfall of effort**

V207 died because its producer had an explicit cap: `min(·, LERP2(angle))` with `max(LERP2 Y) = 2560`.
I applied the identical method to `gp-0x6b4e`, the last unmeasured nonlinearity. **It does not close,
and the contrast is the point.**

### **`gp-0x3d8c` IS AN UNCAPPED ACCUMULATOR**
```asm
   0x271de  movea -0x61b8, gp, ep       ; slot array base, indexed by r14
   0x271e4  sld.hu 0x0, ep, r16         ; running min/max across the slots
   0x271ec  cmovc  r21, r16, r16        ; (repeated for bases -0x61d0, -0x61e8, -0x6324)
   ...
   0x272f6  add    r12, r2              ; the ACCUMULATE
   0x27300  cmp    0xa, r15             ; ~10 slots
   0x27304  jr     0x271de              ; loop
   0x27318  st.w   r6, -0x3d8c, gp      ; ** stored with NO cap, NO clamp, NO min() **
```
⇒ **the saturation to ±10240 is applied DOWNSTREAM, at the reader** (`0x27442`–`0x27454`,
`movea 0x2800` / `cmovle`), **not at the writer.** There is nothing between the accumulate and the
store that bounds it. A sum of ~10 signed halfword terms has no structural ceiling below the
saturation, so **the saturation is genuinely reachable on paper** — exactly unlike the compensation.

### ⭐ **WHICH IS WHY V204 SURVIVES AND V207 DID NOT**
```
   V207's producer   capped by min(., LERP2), max 2560  ->  bound PROVEN, gate cannot fire, RETIRED
   V204's producer   an uncapped 10-slot accumulator    ->  bound NOT PROVABLE, must be MEASURED
```
**That is the honest dividing line between what analysis can settle and what needs a drive**, and it is
worth having explicitly: the analytic route retired one build and confirmed the necessity of the other.

### ⚠ **WEAK CORROBORATION THAT IT MAY STILL BE SMALL — stated as weak**
`gp-0x6b4c`, the *sibling* 11-slot assist sum, is measured at **`|·| ≥ 4096` duty 0.000000 over 17,614
engaged frames.** If `gp-0x3d8c` behaves similarly it would sit far under 10240. **But it is a
different cell with a different slot mask** — `gp-0x6b4c`'s is `0xC4124` = [0,0,5,0,5,5,0,0,0,5,0],
four slots forced zero — so this transfers only as a prior, not as a bound. **[BELIEF]**

### ✅ **NEW STRUCTURE, NOT NAMED IN THIS KIT BEFORE**
The mixer's slot loop carries **four parallel slot arrays** at `gp-0x61b8`, `gp-0x61d0`, `gp-0x61e8`
and `gp-0x6324`, each walked by the same index, with **running min/max** (`cmp` + `cmovc`) alongside
the sum — and it writes **five** separate accumulators (`gp-0x3d74`, `gp-0x3d88`, `gp-0x3d70`,
`gp-0x3d98`, `gp-0x3d8c`) in one pass at `0x27308`–`0x27318`. Only the last is traced anywhere in this
kit; **the other four have never been named.**

## ✅⭐⭐ **THE SATURATION CENSUS IS CLOSED — the last gate CANNOT FIRE, and V207 is retired BEFORE flying**

I built V207 last tick to measure whether the delivery chain zero-rejects the merged command. **The
question is answerable from the image, and the answer is no.** Decompiling `FUN_000456a4` — rather
than reading assembly upward, which is what I had been doing and what `CLAUDE.md` warns against —
gives the whole structure at once:
```c
   uVar6 = gp-0x6a10;                                  // ABSOLUTE STEERING ANGLE
   if ( gp-0x6ac0 (|filtered motor rate|) > LERP1(angle) ) {         // a rate DEADBAND
       v = ((gp-0x6ac0 - LERP1(angle)) * cal(0xC6204)) >> 10;
       v = min(v, LERP2(angle));                       // <-- ** THE CAP **
       gp-0x6ad0 = (gp-0x6abe > 0) ? -v : v;
   } else gp-0x6ad0 = 0;
   gp-0x6acc = gp-0x6ace + gp-0x6ad0;
```
⇒ **the compensation is CAPPED by `min(·, LERP2)`**, so its bound is `max(LERP2's Y table)`:
```
   LERP1 (rate deadband)  X 0xC6832..6836 [3800, 4000, 4150]   Y 0xC6838..683C [5000, 3037, 1000]
   LERP2 (** the cap **)  X 0xC67D2..67D6 [3200, 3800, 4150]   Y 0xC67D8..67DC [ 512, 1024, 2560]
   gain cal 0xC6204 = 3072
```
```
   max compensation          = max(LERP2 Y)   =  2560
   governor gp-0x6ace        <= cal(0xC6202)  =  4762   (gp-0x4f64 is a min() with this)
   worst-case |gp-0x6acc|    = 4762 + 2560    =  7322    vs the gate window 8192
   ** MARGIN 870 COUNTS. THE GATE CANNOT FIRE. **
```
⊕ **The alternate rescaling branch is dead twice over.** `gp-0x6acc = cal(0xC648E) + (sum ×
cal(0xC6134))/1000` is guarded on `cal(0xC64BA) == -0x17`, and that cal reads **0** — disarmed — **and
even if armed it is an identity**: offset `0xC648E` = 0, gain `0xC6134` = 1000/1000 = 1.000.

### ✅ **THIS UPGRADES THE GOLDEN MODEL'S OWN CAVEAT**
`eps_chain_delivery.py` states the envelope *"4762 governor + 2560 compensation = 7322"* but adds
*"this model does not claim every combination is contained."* **It IS contained, provably** — the 2560
is not an observed typical value, it is `max(LERP2 Y)`, and the `min()` makes it a hard ceiling.

### 🛑🛑 **THE CENSUS IS NOW COMPLETE AND CLOSED**
```
   command -> motor path   every clamp: structurally unable to clip, or measured at zero duty
                           (incl. gp-0x6b70 at 1 frame in 72,916 engaged)
                           all six aggregator gates: producer <= window, cannot fire
   delivery chain          the merged-command zero-reject: producer bounded 870 counts under it
```
⇒ **NO clamp saturates and NO gate fires anywhere between the LKAS command and the motor.**
⇒ **The record's "command-gated saturation" model has NO mechanism in the firmware command path.**
⚠ That does not make the *symptom* description wrong — it means the saturating element, if one exists,
is **not in the firmware's command path**: it would have to be in the FOC/PWM inner loop, or mechanical.

### ✅ **V207 IS RETIRED BEFORE FLYING — which is the whole point of doing this analytically**
Its `.rwd` is renamed `SUPERSEDED-DO-NOT-FLASH-ANSWERED-…`. **A drive was saved by reading a
three-knot table.** ⊕ **V204 returns to the top of the shelf** — `gp-0x6b4e`'s writer saturation is
now the only unmeasured nonlinearity left in the path.

### ⭐ **AND THE COMPENSATION IS WORTH RECORDING IN ITS OWN RIGHT**
It is a **motor-rate deadband, scheduled on steering angle**: inert until `|filtered motor rate|`
exceeds LERP1(angle), whose knots **fall** with angle (5000 → 1000), then capped by LERP2(angle),
whose knots **rise** with angle (512 → 2560). **So it arms more easily and permits more at large
steering angles.** Never named anywhere in this kit before.

## ⭐⭐ **THE DELIVERY CHAIN HAS A ZERO-REJECT ON THE MERGED COMMAND — and it is the ONE gate not structurally dead**

The census had cleared the whole command→motor path: no clamp saturates, no aggregator gate can fire.
**The delivery chain was never censused.** It has one, and it is the first with a real margin.

### ✅ **BYTE-CONFIRMED AT `0x431D0`–`0x431D8`**
```asm
   0x431c4  ld.h   -0x6acc, gp, r9      ; the MERGED COMMAND
   0x431d0  addi   0x2000, r9, r6       ; r6 = x + 8192
   0x431d4  addi   -0x4001, r6, r0      ; flags only: carry iff r6 >= 16385
   0x431d8  cmovc  0x0, r9, r11         ; ** carry -> r11 = 0, else r11 = x **
```
⇒ **outside ±8192 the merged command is REPLACED BY ZERO**, not clipped. **A zero-reject on the
command itself is the most violent nonlinearity in the whole chain** — all-or-nothing, and exactly the
"command-gated saturation" shape the record's ratchet model needs.

### ✅ **AND ITS PRODUCER IS NOT STRUCTURALLY BOUNDED BELOW IT**
The comp-add, at `0x458B8`–`0x458CE`:
```asm
   0x458b8  ld.h  -0x6acc, gp, r13      ; previous value (lockstep read)
   0x458bc  ld.h  -0x6ace, gp, r12      ; the GOVERNOR OUTPUT
   0x458c0  ld.h  -0x4cc8, gp, r15      ; its lockstep twin
   0x458c4  st.h  r6,     -0x6ad0, gp   ; the COMPENSATION is stored here
   0x458c8  add   r6, r12               ; ** gp-0x6acc = gp-0x6ace + gp-0x6ad0 **
   0x458cc  sxh   r12                   ; sign-extended to int16 -- WRAPS at +-32768, no clamp
```
```
   gp-0x6ace   <= 4762     the governor output; gp-0x4f64 is pinned at its cal max 99.9%+ of the time
   gp-0x6ad0   ** UNKNOWN **  a LERP output (0x45892-0x458a2), sign-flipped on gp-0x6abe
   the gate    +-8192
```
⇒ **the gate fires iff `|governor + compensation| > 8192`, i.e. iff the compensation exceeds ~3430
while the governor is railed.** 🛑 **Every one of the aggregator's six gates was structurally dead
(producer ≤ window, guaranteed). This one is not — its firing is a genuine question.**
⊕ The golden model's own note concedes the point: the conservative envelope is *"4762 governor + 2560
compensation = 7322"*, **870 counts under the window**, and it says outright *"this model does not
claim every combination is contained."*

### 🛑 **AND NEITHER CELL HAS EVER BEEN MEASURED**
`gp-0x6acc` appears in the record only as a *chain description* — *"the aggregator DOES reach the motor
— the `gp-0x6acc` bridge"* — never as a measurement. `gp-0x6ad0` appears nowhere at all. **No probe in
sixty builds has read either.**

### ⭐ **THIS IS THE NEXT PROBE TARGET, AND IT OUTRANKS V204**
V204 asks whether `gp-0x6b4e` reaches a saturation that merely *clips* a model lane. **This asks
whether the merged command is being ZEROED** — a far larger effect, on the one gate the census could
not rule out, on a cell nothing has ever looked at.
⊕ `gp-0x6ad0` is the better tap of the two: it is the unknown term, `gp-0x6ace` is already bounded,
and their sum is what the gate tests. A tap on `gp-0x6ad0` gives the margin directly.
⚠ **[EVIDENCE]** the gate, the comp-add and the governor bound, all byte-confirmed above.
**[BELIEF]** that it actually fires — unmeasured, and the conservative envelope says it may not.

## 🛑🛑 **NO GATE REJECTS EITHER — the command-gated-saturation model has NO mechanism in this path**

Last tick killed the clamps. The remaining candidate was the aggregator's **zero-REJECT gates**, which
drop a lane to **0** rather than clipping it — a harder nonlinearity than any clamp, and exactly the
shape the record's model needs. Mirroring the compare bit-exactly:
```c
   (int)*(short *)(gp - 0x6b4e) * (uint)( (int)*(short *)(gp - 0x6b4e) + 0x2800U < 0x5001 )
```
an **unsigned** compare of `(x + W)` against `2W+1`, which passes **exactly `|x| ≤ W`** and rejects at
`|x| = W+1`. Against each lane's own producer bound:
```
   lane          window W   producer   can it ever reject?
   gp-0x6b4e       10240      10240    NO  -- writer SATURATES to +-10240 (0x27442..0x27454)
   gp-0x6b4c       10240      10240    NO  -- and |.| >= 4096 measured duty 0.000000 / 17,614 fr
   gp-0x6b26        1024        511    NO  -- producer clamped to 511 by cal 0xC407E
   gp-0x6b46        1024        512    NO  -- FUN_00036682 tail clamps its driver to +-0x200
   gp-0x6bd0        2048       1024    NO  -- <=1024 highway, 0 in 100 % of the micro regime
   gp-0x6bbe        2048        512    NO  -- flat +-512 bound, p50 74
```
⇒ **NOT ONE OF THE SIX CAN EVER FIRE.** `gp-0x6b4e` is the tightest case and it is **exact**: the
writer saturates to ±10240 and the gate passes `|x| ≤ 10240`, so the saturated value passes **by one
count**. That is not luck — **every window is sized at or above its own producer's bound.**

### ⭐ **WHICH REFRAMES THEM: THESE ARE FAULT GUARDS, NOT SHAPING NONLINEARITIES**
Honda sized each window so a healthy lane can never trip it. They exist to drop a **corrupted** lane
(a stuck or wild value), not to shape the control law. **Reading them as shaping elements — which the
"find what clips" hunt invites — is a category error**, and it is why they look promising on paper and
are dead in the code.

### 🛑🛑 **COMBINED: THE MODEL HAS NO MECHANISM ANYWHERE IN THE COMMAND→MOTOR PATH**
```
   clamps   every one either structurally unable to clip, or measured at zero duty --
            including the last survivor gp-0x6b70 at 1 frame in 72,916 engaged
   gates    none can fire, by construction
```
⇒ **If the ratchet is a command-gated saturation, the saturating element is NOT in this path.** The
remaining places it could live are the ones this census never covered: the **delivery chain** — the EME
shaper, the integrator, the FOC/PWM stage — and the **plant** itself.
⚠ **[EVIDENCE]** for the census; **[BELIEF]** that the model is therefore wrong — it may simply be
looking at the wrong stage.

### ✅ **V204 SURVIVES THIS — and it is the one thing here that does**
`gp-0x6b4e` is still **SATURATED BY ITS WRITER** at ±10240. The gate passing is irrelevant to that:
**the clipping already happened upstream**, at `0x27442..0x27454`. Whether `gp-0x3d8c` actually drives
it to the rail is **unmeasured**, and V204 reads exactly that cell. ⇒ **V204 stays the probe to fly**,
and it is now the *only* saturation question left standing in this path.

## 🛑🛑 **`gp-0x6b70` DOES NOT SATURATE — V205's question answered from cache, V206's best argument REFUTED**

V205 was built to ask whether `gp-0x6b70` clips, because the saturation census had eliminated every
other clamp in the command→motor path. **The answer was already on disk.**
`BUILD-LINEAGE-CATCHUP` records V96/V97's probe verbatim:
> *"**PROBE:** CAN 427 ← `gp-0x6b70` (LSB **12.8 ct**, no-clip `8192×5>>6 = 640 ≤ 1023`)"* ·
> *"`b7` = `gp-0x6b70 < 0` … V96's own rungs"*

⇒ 427 carries the **magnitude** at `raw = (|x|×5)>>6` and rung `b7` carries the **sign** — the design
law's own sign-bit-plus-magnitude pattern. The ±8192 writer clamp lands at **raw 640**. V100's
changelog repoints 427 away from `gp-0x6b70`, which bounds the window at **V96–V99: routes 7d / 7e /
7f / 80 / 81 / 82, all cached.** (427 arrives at half the base rate, so engagement is *interpolated
onto the 427 timebase* rather than assumed.)
```
   route  build          n_eng    p50     p95     max    AT CLAMP
   r7d    V94  -- STRUCK, see below  542   1370   4990   8320   0.001845
   r7e    V97            30753    154    1856    3238    0.000000
   r7f    V97            34476    141    1677    3405    0.000000
   r80    V97              860    602    2483    2675    0.000000
   r81    V98             3296    883    2726    3162    0.000000
   r82    V99             2989    538    2624    3008    0.000000
   POOLED  72,374 engaged 427 frames, ZERO at the clamp  ->  duty 0, 95% UB 0.0000414
```

🛑 **CORRECTION 2026-08-29 — the `r7d` row is STRUCK, and it was the only row carrying a clamp hit.**
It was labelled **V96**. **V96 never flew** ("BUILT, VERIFIED, UNFLASHED"), and `r7d` flew **V94** —
agreed by the cache's own `probe_build` field, the lineage (*"V94 … FLEW route `7d` … AND WAS
ABORTED"*), the handoff filename and the study filenames. That matters because **V94's CAN 427 is a
different variable at a 32× different scale**, byte-verified from the images:

```
   V94        0x55DF2 = DA   0x55E10 = A1   ->  gp-0x6b26,  sar 1
   V96..V99   0x55DF2 = 90   0x55E10 = A6   ->  gp-0x6b70,  sar 6
```

So the clamp arithmetic this table rests on (`8192×5>>6 = 640`) **does not apply to `r7d` at all** —
it is `gp-0x6b26` read against `gp-0x6b70`'s ceiling, 32× out. The prose above bounds the window at
"V96–V99: routes 7d/7e/7f/80/81/82"; **`r7d` was never inside it.**

⊕ **CONSEQUENCE 1 SURVIVES AND STRENGTHENS.** `r7d` contributed the pool's single clamp event
(0.001845 × 542 = 1.0). Without it the pool is **72,374 frames with zero events**, so the "nothing
clips" reading is firmer, not weaker, and V206's justification stays dead. Nothing downstream moves.

### 🛑 **CONSEQUENCE 1 — V206's STRONGER JUSTIFICATION IS DEAD**
Two ticks ago I re-justified V206 as *"raises the effective ceiling by exactly 2×"*, matching the
record's instruction to *"find what clips, and either raise its ceiling or soften its corner"* — and
argued it **survived the speed-invariance objection because it was about clip duty, not loop gain.**
**That argument is refuted: the ceiling is reached on 1 frame in 72,916.** ⇒ **V206 raises a ceiling
that is never reached.** What survives is only its **gain** effect (describing function, GATE 2
verified) — **which is the justification that IS in tension with the ratchet being speed-invariant.**
**V206 is demoted, not withdrawn**, and its case is now the weaker of the two.

### 🛑🛑 **CONSEQUENCE 2 — THE SATURATION MODEL HAS NO SURVIVING CLAMP IN THIS PATH**
The census eliminated every other clamp by structure or by measurement, and the sole survivor is now
measured non-saturating. ⇒ **If the ratchet is a command-gated saturation, the saturating element is
NOT a clamp in the command→motor path.** The remaining candidates are of a different kind: the
aggregator's **zero-REJECT gates**, which drop a lane to 0 rather than clipping it — a harder
nonlinearity than any clamp.

### ⭐ **CONSEQUENCE 3 — THIS RE-RANKS THE SHELF. V204 IS NOW THE PROBE TO FLY.**
`gp-0x6b4e` **SATURATES at ±10240 and its zero-reject window is exactly ±10240** — it is the one
element that both saturates and sits in a reject gate, and **its magnitude has never been measured.**
**V204 reads exactly that cell.** ⇒ **V204 → the probe worth a drive. V205 → demoted, its question
answered here.**
⊕ And V205's secondary value is answered too: `gp-0x6b70`'s operating range is now known —
**p50 141–1370, p95 1677–4990, against the 8192 clamp.**

### ✅ **THAT RANGE ALSO SIZES V206 HONESTLY**
The describing-function table was computed over A = 25–12800. The **real** operating range is
p50 ≈ 500, p95 ≈ 2500, where the measured N ratio is **0.47–0.72** ⇒ **V206 delivers a 1.4–2.1× gain
reduction where the signal actually lives**, not the 2× a flat reading would suggest.

## ✅⭐⭐ **AN UNREAD ON-CAR DOSE-RESPONSE FOR THE RATCHET LEVER — and the shelf gets a FREE endpoint**

Decoding the rung specs for the V102–V106 routes turned the sweep's numbers into measurements. The
biggest one had been sitting in two caches for weeks.

### ✅ **`b5` IS THE SAME RUNG ON FIVE CONSECUTIVE BUILDS**
From the lineage: V102's cave defines `b5 = |gp-0x6ae2| ≥ |gp-0x6b26|` — **modelled friction vs the
INERTIA term** — and V103 changes *"exactly ONE rung"* (`b3`), leaving `b5` byte-identical.
```
   route  build   n_eng     b5
   r96    V102    57,629   0.2481
   r9e    V103    40,638   0.2384
   ra4    V104    67,039   0.2305
   ra5    V105    49,021   0.2798
   ra6    V106   123,802   0.1907     <- V106 = V105 + ONE cell: the inertia curve
```
⇒ **inertia exceeds modelled friction ~75 % of engaged time** on every build. That alone is worth
knowing: **V196/V199/V202 halve the term that dominates**, not the minor one.

### ✅✅ **V105 → V106 IS A SINGLE-VARIABLE PAIR, AND IT MEASURES THE LEVER**
Tripling — see the correction below — the inertia term must LOWER `P(friction ≥ inertia)`. Episode
bootstrap, 4,000 resamples, episodes weighted by length, **per the kit's own “episodes not windows” rule**:
```
   rung                                    V105     V106     delta      95% CI
   b5  |friction| >= |INERTIA|   DOSED    0.2798   0.1907   -0.0891  [-0.1328, -0.0200]  EXCLUDES 0
   b7  a sign rung             CONTROL    0.3835   0.3324   -0.0511  [-0.1257, +0.0650]  includes 0
   b4  a sign rung             CONTROL    0.4338   0.4154   -0.0184  [-0.0413, +0.0217]  includes 0
```
⇒ **Direction correct, CI excludes zero, effect 1.7× the largest control.**
✅ **So `0xD7A5C` DEMONSTRABLY REACHES THE CAR, with the expected sign** — which had never been shown
for the ratchet lever now sitting on the shelf.
⚠ **Honest limits: 9 and 7 episodes.** The CI is wide and `b7` moved 57 % as much as `b5`. **This is
corroborating evidence, not proof.**

### 🛑 **CORRECTION TO A BUILD TAG: V106 IS ×2.000, NOT ×3.0**
Its artifact is named `GP6B26.X3.0`, but read from the images the engaged curve moves
**−14745/−8601/−2949 → −29490/−17202/−5898 — exactly ×2.000 on all three knots.**
**The dose in the tag is wrong**, and any dose-response quoted from the tag rather than the image is
off by 1.5×.

### ⭐⭐ **THE CAVE IS BYTE-IDENTICAL FROM V105 TO V202 — so the shelf already has this endpoint**
```
   v105 v106 v107 v108 v122 v202   cave@0xC4B34 sha  d3bb75d8fce08211   ALL IDENTICAL
   (v103/v104 differ: e997c1138528e334)
```
⇒ **V202/V205/V206 carry V105's exact rungs.** `b5` still means friction-vs-inertia and `b6` still
means the governor clip. **Every shelf build already reports the ratchet lever's effect, for zero
extra bytes.** The design law wants each build interpretable from one short drive — **it now is, on a
channel that was already there.**

### ✅ **PRE-REGISTERED, QUANTITATIVE, AND FREE**
Doses read from the images: V105 = 1.000×, V106 = 2.000×, **V202 = 0.333×**. Extrapolating the
measured per-doubling effect (−0.0891, CI [−0.1328, −0.0200]) across −1.585 doublings:
```
   ** b5 on V202 / V205 / V206 should read 0.42, plausible range 0.31 to 0.49 **
   against 0.2798 measured on V105 and 0.1907 on V106.
   b5 <= 0.28 (i.e. no rise at all) => the halving is NOT reaching the car, and the ratchet lever
   on the shelf is inert -- which would be the single most useful null available.
```
⚠ A log-dose extrapolation 1.6 doublings outside the measured range, from ONE pair. Stated as a range,
not a point.

## ✅ **SWEPT ALL 23 CACHED ROUTES FOR UNREAD RUNGS — 72 informative readings, and the REGISTRY STOPS AT r77**

V105's `b6` sat unread because nothing pointed at it. So I swept every cached route's cave rungs
(`0x14A` byte4 bits 7:3) on engaged frames and put each next to what the route registry says it means.
**23 routes, 72 informative readings, 43 degenerate.**

### ✅ **THE METHOD IS VALIDATED AGAINST A RECORDED VALUE — not asserted**
The lineage says V104's `b6` was `|r24| ≥ |r26|` with *"duty **1.0000** engaged ⇒ carried no
information."* My extraction on route `a4` reads **exactly 1.000000**. ⊕ And route `a5` (V105, same
cave with `b6` repointed to the governor comparison) reads **0.000000**. **A positive and a negative
control on the same bit, across two consecutive builds** ⇒ the bit mapping is right.

### ✅ **THREE ANSWERS READ OUT OF CACHES, NO DRIVE**
- **`r85` IS V100 — confirmed by THREE exact matches.** The lineage's V100 row records *"`d(b5)` AND
  `d(b6)` BOTH 0.000000 … with `b4` = 0.6057 on the same cell"*; `r85` reads **b5 0.000000, b6
  0.000000, b4 0.6057.** Attribution by data, not by guess.
- **`r9e` (V103): `b3` = 0.4675 ⇒ VARIES.** The lineage makes this a run-validity gate: *"🛑 IDENTITY:
  `b3` must VARY. A constant `b3` means the build is not V103 or the rung is dead — RUN-INVALIDATING,
  not a finding."* **The gate PASSES.** That had a stated pass/fail criterion and had never been checked.
- **🛑 `r97` CARRIED NO CAVE AT ALL.** The probe byte is **`7` in all 68,883 engaged frames** — a
  single value, and `0x07` is what the registry itself calls *"the stock STEER_SENSOR_STATUS with NO
  probe bits"*. **68,883 engaged frames — one of the largest exposures in the corpus — with zero
  instrument.** Any analysis expecting rungs from `r97` gets nothing, and nothing said so.

### 🛑 **THE STRUCTURAL GAP: THE REGISTRY STOPS AT r77**
`lib/route_build_registry.py` has entries through the V5x–V7x era. **All 13 newer routes — `r77`
through `ra6`, i.e. the entire V90–V106 arc — return "not in registry"**, so their rung meanings live
only in prose in the lineage. **That gap is exactly why V105's `b6` went unread**: the answer was on
disk and nothing connected it to the question.
⚠ **I did NOT extend the registry, because its `tail` field is the rlog hash and those are not in the
caches** — filling them would mean inventing identifiers. **The blocker is named rather than papered
over**: extending it needs the route tails from the rlog paths, not from `_scratch/cache`.
⊕ `analysis-2020accord/verify/unread_rung_sweep.py` is the tool; it re-runs in seconds and prints
every rung with its duty and its registry evidence, flagging degenerate readings separately.

### ⭐ **AND THE DISTINCTION THAT MATTERS: DEGENERATE ≠ NULL**
43 of the 115 readings are **0.000000 or 1.000000**. **A degenerate rung is not a null result — it is
an uninterpretable one**, and this kit's record shows the two being confused repeatedly (V64's *"the
null is on the GATE, not the hypothesis"*; V68's detector that *"has NEVER been non-zero"*; V104's
`b6` at duty 1.0000 *"carried no information"*). The sweep now labels them apart by construction.

## ✅⭐⭐ **THE SATURATION CENSUS CONVERGES ON `gp-0x6b70` — by elimination, from data already on disk**

The record's instruction is *"find what clips"*. I had found **one** saturating element and built a
ceiling raise for it without checking whether it was the only one, or the binding one. So I enumerated
**every clamp between the LKAS command and the motor**, read each ceiling from the image, and put each
next to its own producer's ceiling — because **a clamp only matters if its input can reach it.**

### ✅ **14 OF 18 CLAMPS CANNOT CLIP AT ALL**
Either the ceiling equals or exceeds its own producer (`gp-0x6b86` 12288 = 12288; the biquad's float
±12.0 = 12288; `gp-0x6b26`'s ±1024 window against a producer clamped to 511 by `0xC407E`;
`gp-0x6b46`'s ±1024 window against ±512 by construction), or the record already measured it inert
(the LKAS setpoint clip — V108 E3, pulled on its own null; the forward clamps `0xC61B2`/`0xC61B4`
— lane max 2505 < 3072; `gp-0x6bd0` — zero in 100 % of the micro regime; `gp-0x6bbe` — p50 74
against a ±2048 window; `gp-0x6b4c` — `|·| ≥ 4096` duty 0.000000 over 17,614 engaged frames).

### ✅✅ **AND THE BIGGEST REMAINING CANDIDATE IS MEASURED DEAD — IN A CACHE WE ALREADY HAVE**
`gp-0x4f64` is the **governor ceiling**, and the record measures it **pinned at its cal max 4762 for
99.9 %+ of engaged time** — so it is effectively a **constant 4762 limit** on the aggregator output,
whose own clamp is 10240, i.e. **2.15× higher.** Whether the aggregator ever reaches it had never been
read out. **But V105's cave `b6` is exactly `|gp-0x6b94| ≥ |gp-0x4f64|`, V105 FLEW as route `a5`, and
that cache is on disk.**
```
   route a5, 65,959 frames, 49,021 engaged (74.3 %)
   bit   duty        rung
    7    0.383468    sign                     <- positive control
    6    ** 0.000000 **  |gp-0x6b94| >= |gp-0x4f64|   THE GOVERNOR CLIP
    5    0.279778                             <- positive control
    4    0.433814                             <- positive control
    3    0.487444    identity                 <- positive control
```
⇒ **The aggregator NEVER reaches the governor ceiling. The governor clip is DEAD**, on 49,021 engaged
frames, **with four rungs on the same byte varying normally** — so this is not a stuck field or a dead
cave. ⊕ `gp-0x6ad6` was already measured the same way: **V100's `b5` duty 0.000000, CI [0, 0.0186],
with `b4` = 0.6057 on the same cell.**

### ⭐ **WHAT SURVIVES: `gp-0x6b70`, AND ONLY `gp-0x6b70`**
**Every other clamp in the command→motor path is either structurally unable to clip or measured at
zero duty.** `gp-0x6b70` is **the only one that can clip and has never been measured** — and it is
exactly the cell **V205 reads and V206 doses.**
⇒ **That is independent corroboration, reached by elimination rather than by following the same
thread.** It did not need a drive: the census came from the image and the duties from caches already
on disk.
⚠ One candidate remains genuinely open besides it — **`gp-0x6b84` (the resid mirror, ±0x3000)** —
unmeasured, and worth a rung if a future cave has a spare one.

## 🛑 **A VACUOUS TEST RETIRED, MY OWN AMPLITUDE PREDICTION WEAKENED — AND V206 RE-JUSTIFIED ON BETTER GROUNDS**

### 🛑 **THE FREQUENCY TEST CANNOT DISCRIMINATE — do not spend a drive endpoint on it**
I planned to predict the limit-cycle frequency and test it against the measured 6–9 Hz ratchet. The
ratchet is a **measured** lightly-damped resonance: 7.79 Hz, **Q 14–29**, ζ 0.017–0.036, ring-down,
three drives. A 2nd-order resonance sweeps 180° over roughly `f0/Q`:
```
   Q = 14  ->  the -180 deg crossing is pinned within +-0.28 Hz of 7.79
   Q = 29  ->  ...................................... +-0.13 Hz
```
⇒ **ANY limit cycle in a loop containing this resonance locks to 7.6–8.0 Hz BY CONSTRUCTION**, which
is inside the measured band. **The test is satisfied by every hypothesis that routes through the
resonance at all, so it has ZERO discriminating power.** Retired before it cost a drive endpoint.

### ⚠ **AND MY OWN AMPLITUDE PREDICTION IS IN TENSION WITH THE RECORD**
Last tick I pre-registered the describing-function peak as a limit-cycle amplitude. That peak is
**speed-indexed**, so it predicts the ratchet's amplitude should vary with speed:
```
   speed ct   320    640   1280   2560   5120        (~5, 10, 20, 40, 80 km/h at 64 ct/km/h)
   predicted  460    438    453    619   1224        ** 2.8x rise from 10 to 80 km/h **
```
But the record characterises the ratchet as **SPEED-INVARIANT**, with amplitude scaling on **wheel
rate / command magnitude** ([[accord-ratchet-is-a-lightly-damped-resonance]],
[[accord-ratchet-axis-is-wheel-rate]]). **Those point in opposite directions.**
⇒ **The limit-cycle-amplitude framing is WEAKENED.** ⚠ Not a clean refutation — a compensating speed
dependence in `|G(jω)|` could cancel it — but **the burden now sits on that coincidence**, and I should
not have pre-registered a speed-varying endpoint against a symptom the record calls speed-invariant.

### ⭐⭐ **BUT V206 IS RE-JUSTIFIED, AND ON THE RECORD'S OWN STATED TARGET**
`accord-ratchet-and-grind-are-command-gated-saturation.md` says it plainly:
> *"Sixty builds hunted a **linear** lever — a pole, a damper, a gain — for what is now measured to be
> a **command-triggered nonlinearity**. 🛑 **A linear lever cannot fix a relay.** The target is the
> SATURATING ELEMENT: **find what clips, and either raise its ceiling or soften its corner.**"*

**`0xC63AE` scales the LERP's input, so halving it DOUBLES the residual needed to reach the ceiling:**
```
   LERP ceiling at X[9] = 14490 at every speed
   k = 1024 (Honda)  ->  clips when |resid| >= 14490
   k =  512 (V206)   ->  clips when |resid| >= 28980        ** exactly 2x the ceiling **
   (resid is gated to +-20000 per term, so the Honda ceiling IS reachable and V206's is much less so)
```
⇒ **V206 raises the effective ceiling of a saturating element by exactly 2× — which is verbatim what
the record instructs.** ⊕ **And this justification SURVIVES the speed-invariance objection**, because
it is about **clipping duty**, not loop gain: the ceiling is 14490 at every speed.
⊕ It is also **the "raise its ceiling" branch, not "soften its corner"** — worth naming, because the
two have different side-effects and only one was available as a single virgin cal.

### ✅ **THE ENDPOINT IS NOW SHARPER — CLIP DUTY, NOT AMPLITUDE**
`gp-0x6b70` saturates at ±8192, and **V205 reads `gp-0x6b70` directly.** So the pre-registration
becomes:
```
   clip duty at +-8192 is HIGH   -> the saturation model is confirmed and V206 is aimed correctly
   clip duty is LOW but non-zero -> V206 is a partial fix; a quarter dose (k=256) quadruples the ceiling
   clip duty is IDENTICALLY ZERO -> the element NEVER clips, the saturation model is wrong HERE,
                                    and V206 should come off the shelf rather than be flown
```
**That is a far better endpoint than the amplitude one** — it is a duty, it needs no scale calibration,
it cannot be averaged away, and one of its three branches retires the build.

## ✅ **GATE 2 RUN ON V206 — IT PASSES, AND IT WAS NOT THE TRIVIAL CHECK IT LOOKED LIKE**

I built V206 last tick having run **GATE 1 but not GATE 2**. The kit makes both mandatory for any
dynamics change, and halving a loop gain is one. Running it properly changed a number I had published.

### 🛑 **"HALVING A GAIN HALVES THE LOOP GAIN" IS FALSE HERE**
`0xC63AE` scales the **input** of a **memoryless, CONCAVE** nonlinearity. Scaling the input down moves
the operating point onto a **STEEPER** part of the curve — and the curve's slope ratio between small
and mid signal is **6.7–10.7×**, so the steepening is large. The two effects fight. The correct
instrument for a memoryless nonlinearity inside a loop is the **describing function**:
```
   f(x) = sgn(x) * LERP(|x|)        the stage at unity
   g(x) = f(k*x)                    the stage with the dose
   ** N_g(A) = k * N_f(k*A)   NOT   k * N_f(A) **
```
### ✅ **MEASURED ON THE REAL CURVE — PASS, worst case 0.794**
```
   amplitude A       25     200     800    3200    6400   12800
   N ratio         0.486   0.472   0.619   0.794   0.771   0.658
```
**The ratio is never a flat 0.500 and never reaches 1.0.** Worst case **0.794 at speed 2560, A=3200**.
⇒ **The dose reduces first-harmonic loop gain at EVERY amplitude and EVERY speed tested**, and being
memoryless it **adds no phase at any frequency**. So the Nyquist locus contracts **radially toward the
origin with no rotation**, which cannot create an encirclement of −1 that did not already exist:
**a stable loop stays stable. GATE 2 PASSES.**

### 🛑 **CORRECTION TO MY OWN BUILDER — do not quote "half"**
V206's docstring said the dose halves the gain. **That is the small-signal limit only** (the
describing function confirms 0.486 at A=25). Across the amplitude range the dose buys **1.26× to
2.1×**, not a uniform 2×. The builder now carries the amplitude table.

### ⭐ **AND A FINDING NOBODY ASKED FOR: THE DESCRIBING FUNCTION PEAKS AT A ≈ 200–400**
```
   speed 2560   N(25)=3.64   N(200)=3.75   N(400)=3.55   N(1600)=1.95   N(12800)=0.61
   speed 5120   N(25)=3.31   N(200)=3.61   N(400)=3.80   N(1600)=2.09   N(12800)=0.63
```
**N is NON-MONOTONIC — it rises then falls, peaking near A = 200–400 counts.** A limit cycle sits where
`N(A)·|G(jω)| = 1`, so **a peak in N is a PREFERRED AMPLITUDE.** ⇒ **If the ratchet is a limit cycle
through this stage, its amplitude should sit near 200–400 counts** — a concrete, falsifiable
prediction that V205's probe can test directly, since it reads exactly this signal.
⊕ V206 lowers that peak from ~3.8 to ~1.9, which would either kill such a cycle or move it.
⚠ **[BELIEF]** — the describing function is EVIDENCE (computed from the image); that the ratchet is
this particular limit cycle is the hypothesis.

⊕ **This is the first GATE 2 in the kit run with a describing function rather than a linear Bode
sum.** For a memoryless nonlinearity in a loop it is the right instrument, and a linear sum would have
reported a flat 0.5 and missed that the dose is 1.6× weaker than that at mid amplitude.

## ✅⭐ **THE `0xC63AE` SIGN IS ESTABLISHED WITHOUT A DRIVE — V206 BUILT, AND ITS PRICE IS STATED**

### ✅ **THE RECORD'S OWN NINE-LINK TRACE ALREADY COVERS THIS STAGE**
`accord-friction-polarity-more-friction-is-more-assist.md` traces the polarity end to end, and **its
step 4 IS this stage**:
```
   4  gp-0x6b70 = clamp(sgn(res)*LERP(|res|), +-8192),  f' >= 0  =>  d/d(MODEL) >= 0 EVERYWHERE
   5  FUN_00037fe6:  gp-0x6ad6 += gp-0x6b70 * w         =>  target felt effort
   9  delivered = gp-0x6752 x gp-0x6b94                 =>  torque in the DRIVER'S direction
   measured cross-check:  d(gp-0x6b94)/d(gp-0x6b70) = +0.2529 / +0.2565
```
⇒ **Lowering `0xC63AE` shrinks `|gp-0x6b70|` toward zero.** V87 measured `gp-0x6b70` **negative
67.19 %** of engaged time, and shrinking a negative value *raises* it ⇒ **less assist on ~2/3 of
frames, more on ~1/3. Net: predominantly LESS assist, a slightly heavier wheel.**
✅ **So the sign needed no drive at all** — it was already in the record, one link away from where I
was looking.

### 🛑 **`0xC64B0` IS NOT A WEIGHT — the recorded `tp+0x74B0` trap, in a new form**
Step 5 of that trace reads *"`gp-0x6ad6 += gp-0x6b70 * w(0xC64B0)=1`"*, so I priced `0xC64B0` as a
gain. It reads **257 = `0x0101`** — **two enable BYTES, not a halfword weight.** `CLAUDE.md` names
this exact address as the off-by-0x1000 case that *"invented lane weights for what are 0/1 enable
flags"*. **The trap recurred in a new guise: not a wrong address, but a byte-pair read as a u16.**
⇒ **`0xC64B0` is not a lever.** The clean one is `0xC63AE`.

### ✅ **V206 = V202 + `0xC63AE` 1024 → 512.** ONE u16 cal, 34/34. `71bd8312c324de9c…`
```
   speed    small-signal gain    with the dose
     640        2.67x        ->     1.33x
    1280        3.04x        ->     1.52x
    2560        3.77x        ->     1.89x
    5120        3.43x        ->     1.72x
```
**GATE 1 is the cleanest possible**: `0xC63AE` has **exactly ONE site image-wide** (`0x38242`, the
reader) and **ZERO writers**, byte-stock on every build. Cal-only, **1 payload byte**, cave
byte-identical — **not the bricking class.** ⊕ It scales **this stage only**; the base power-assist
map is fed by the differently-transformed `Xsrc`/`Ysrc` and is untouched.

### ⚖ **THE PRICE, STATED RATHER THAN BURIED**
**The trade is: the soft relay's small-signal gain halves (the ratchet mechanism) and the wheel gets
somewhat heavier (an authority cost).** The operator has been explicit that he wants **low apparent
friction AND no ratcheting**; this buys one with some of the other. 🛑 **So V206 is deliberately NOT
the recommended build — V205 is**, because V205 measures `gp-0x6b70`'s actual range so this dose can
be **sized rather than guessed**. V206 exists so that if V205 says the range is large, the fix is
already cut. **A quarter dose is the obvious follow-up if half reads in the right direction.**

### 🛑 **THE BYTE-COUNT TRAP RECURRED — and is now DERIVED, not assumed**
I asserted "exactly 2 payload bytes" for a u16 cal. **1024 = `0x0400` → 512 = `0x0200` moves only the
HIGH byte — it is ONE byte.** Same shape as the V181 assertion bug and V198's `0x9540`→`0x9526`. The
builder now **computes** the expectation from the two values instead of stating it.

## ✅⭐ **THE RELAY QUESTION IS ANSWERED FROM THE IMAGE — it is a SOFT relay, and it has its own private gain cal**

**This reverses last tick's conclusion, and corrects a second claim I made there.** I said the curve
could not be read statically and that it *"reshapes with steering angle"*. The first is wrong because
the kit already mirrors `FUN_000389ec` integer-exactly; the second is wrong outright.

### ✅ **THE LERP IS THE POWER-ASSIST CURVE, AND THE MIRROR ALREADY COMPUTES IT**
`assist_map_mirror.py` (validated **200/200** against V72's flown probe) computes the very staging
arrays `FUN_00038148`'s LERP copies verbatim:
```
   0x39548  st.h r9,  -0x64b8, gp  <- gp-0x373c  == the mirror's Xi   (torque axis)
   0x39522  st.h r11, -0x641c, gp  <- gp-0x3714  == the mirror's Yi   (assist axis)
```
⇒ **`gp-0x6b70 = sgn(resid) × ASSIST_CURVE(|resid|)`** — the observer re-uses the **power-assist
curve**, applied to the residual instead of to driver torque. One additive side-effect line in the
mirror exposes it; the return value is unchanged.

### 🛑 **CORRECTION — the curve is SPEED-dependent, NOT angle-dependent**
```
   speed  640 / 2560 / 5120 : ** 1 distinct curve across 8 steering angles ** -> INVARIANT
   fixed angle, 6 speeds    : 6 distinct curves                              -> SPEED-DEPENDENT
   mode 24 vs 26            : identical at 2560; ONE knot differs 0.4 % at 640
```
Steering angle enters through `boost` into `SCALE`, which shapes the **downstream** `Xsrc`/`Ysrc` —
the base assist map — **not the `Xi`/`Yi` this LERP copies.** **My "stratify by steering angle"
instruction in `SHELF.md` was wrong and is now "stratify by SPEED".**

### ⭐ **IT IS NOT A HARD RELAY — IT IS A SOFT ONE, AND THAT IS THE INTERESTING PART**
```
   mode 26, speed 640:  X  0   166   333   678  1200  1800  3000  5000 10000 14490
                        Y  0   443   818  1369  1915  2223  2634  3146  4298  8192

   speed    gain near 0    mid-range (X6..X7)    ratio
     640       2.67x            0.256x           10.4x
    1280       3.04x            0.284x           10.7x
    2560       3.77x            0.352x           10.7x
    5120       3.43x            0.516x            6.7x
```
No flat top inside the operating range (the ceiling is only reached at 14490), **so the hard-relay
hypothesis is REFUTED.** But a curve with **2.7–3.8× gain at small input and 0.26–0.52× at mid-range —
a 6.7–10.7× compression ratio — IS a soft relay**, and high small-signal gain around a zero crossing
is exactly the shape that sustains a small-amplitude limit-cycle. **That is a far better-founded
ratchet mechanism than "it is a relay", and it is consistent with the record's own
"command-proportional Coulomb relay".**

### ⭐⭐ **AND THE STAGE HAS A PRIVATE GAIN CAL: `0xC63AE`**
```c
   0x38242   uVar7 = (|resid| * cal(0xC63AE)) >> 10        // cal = 1024 = unity
```
**`0xC63AE` = 1024, EXACTLY ONE site image-wide (`0x38242`), ZERO writers, VIRGIN** (kit's own
`tp_cal_readers.py`). It scales the LERP's **input**, so in the steep small-signal region the
effective gain scales with it **directly** — halving it halves the soft relay's small-signal gain.
⊕ **It scales THIS STAGE ONLY.** The base power-assist map is fed by `Xsrc`/`Ysrc`, a different
transform of the same source, so **the map itself is untouched.** That matters, because the curve's
shape is otherwise welded to the ROM assist records and could not be changed without changing
steering feel — **which is very likely why the ratchet has resisted sixty builds.**
⚠ **BUT `FUN_00038148` is NOT engagement-gated** (caller `FUN_0002214a` = task 0, 1000 Hz), so this
cal changes manual driving too. 🛑 **And its SIGN of effect on delivered assist is NOT established**
— the path runs `gp-0x6b70 → gp-0x6ad6` (a torque-tracking **reference**, not a motor torque), and the
record is emphatic that sign bets on this path have cost builds. **So it is NOT built this tick.**

### ⭐ **THIS MAKES V205 MORE VALUABLE, NOT LESS**
Its purpose is no longer *"is it a relay"* — that is answered. **It is now: measure `gp-0x6b70`'s
operating range and sign so the `0xC63AE` dose can be SIZED and SIGNED.** The probe reads the exact
signal the cal scales. **Sequence: fly V205 → read the range and sign → dose `0xC63AE`.**

## 🛑 **THE RELAY CURVE IS BUILT AT RUNTIME — it cannot be read from the image, so V205's drive is REQUIRED**

I set out to answer the relay question statically and make V205 unnecessary. **The answer is a
definitive no, and the reason is worth more than the original question.**

### THE TWO HOPS END IN LIVE VEHICLE STATE, NOT IN FLASH
`FUN_00038148`'s LERP reads X from `gp-0x64b6..` and Y from `gp-0x641c..`. `FUN_000389ec` fills both:
```
   0x39508   movea -0x3714, gp, ep        <-- ** ep = gp-0x3714, RAM staging, NOT a flash table **
   0x3950C   sld.hu 0x0, ep, r11              Y[0] <- gp-0x3714
   0x39522   st.h   r11, -0x641c, gp          ...
   0x39548   st.h   r9,  -0x64b8, gp          X[0] <- gp-0x373c
   0x39572   st.h   r16, -0x64b6, gp          X[1] <- gp-0x373a
```
and the staging itself is **COMPUTED, not copied**. Immediately before:
```
   ld.hu -0x6982 / -0x6a10 / -0x6a64 / -0x6984, gp     four LIVE cells
   cvtf.uws  x4                                        u16 -> float
   movhi 0x3a80, r0, r6        = 0.0009765625 = 1/1024     (Q10 -> float)
   mov   0x3dcccccd, r12       = 0.1f
   mulf.s ...                                          FLOAT arithmetic
   add 0x1, r14 / cmp 0x9, r14 / bgt / jr 0x39258       TEN iterations, one per knot
```
⇒ **`gp-0x6a10` is ABSOLUTE STEERING ANGLE** (already in the record). **The curve that decides
whether `gp-0x6b70` is a relay is re-derived every pass from steering angle and three other live
cells.** There is no static curve in the image to read. **V205's drive is REQUIRED, not merely
convenient.**

### ⭐ **AND THIS IS ITSELF THE MORE INTERESTING FINDING**
**A LERP that reshapes with steering angle means the stage's CHARACTER is condition-dependent** — it
can be a relay at one steering angle and smooth at another. ⇒ **A single static answer never existed**,
and the right endpoint for V205 is not *"is it a relay"* but **"over what conditions does it become
one"**, stratified by steering angle. That also fits a symptom the operator reports as coming and
going rather than being uniformly present.
⚠ **[BELIEF, not evidence]** — the reshaping is EVIDENCE (it is in the code); that it explains the
ratchet's intermittency is a hypothesis V205 can test.

### 🛑 **PROCESS — I HAND-ROLLED A gp SCAN AND HIT THE RECORDED ODD/EVEN TRAP**
My scan reported **`gp-0x3738`: 0 hits** and **`gp-0x373a`: 1 hit** for cells the disassembly plainly
reads at `0x39556`/`0x3955A`/`0x39560`/`0x39564`. Cause: `ld.hu -0x373a, gp, r16` encodes
**`hw2 = 0xC8C7`, not `0xC8C6`** — the `(disp | 1)` odd-displacement form `CLAUDE.md` names as a
recurring trap. **A raw `find(pack('<H', disp))` is blind to half the sites.**
✅ **The kit ALREADY HAS the correct scanner** — `analysis-2020accord/verify/scan_gp_relative_no_whitelist.py`
— whose own opcode census prints *"op 0x3F ld.hu ← MISSED by the old whitelist"*. **Use it. Do not
hand-roll a displacement scan.** The null it prevents is the expensive kind: *"0 hits"* reads as
*"dead cell"*.

## 🛑 **A SHAPE STATISTIC ON A BIT-FIELD LOOKED LIKE A FINDING — the relay question needs an instrument**

### THE QUESTION, AND WHY IT MATTERS
`FUN_00038148` ends by mapping the residual magnitude through a LERP and re-applying the sign:
```c
   uVar7 = (|resid| * cal(0xC63AE)) >> 10          // cal = 1024, so uVar7 = |resid|
   sVar8 = LERP(uVar7)                             // X at gp-0x64b6.., Y at gp-0x641c..
   gp-0x6b70 = sgn(resid) * sVar8,  clamped to +-cal(0xC6200) = 8192
```
**If that LERP saturates early the stage is a SIGNED CONSTANT — a relay** — and the record blames the
ratchet on exactly that: *"Engagement amplifies 6–9 Hz 2.8× via a COMMAND-PROPORTIONAL COULOMB RELAY."*
`gp-0x6b70` is also the traced route to `gp-0x6ad6`, the torque-tracking reference. **So this is the
ratchet's own named mechanism sitting on a cell we can read for 3 bytes.**
⚠ The LERP's knots are in RAM **two hops from any cal** (X from `gp-0x373c` staging, Y from an
`ep`-pointed table), so reading them statically is not the cheap path. Read the OUTPUT instead.

### 🛑 **AND HERE IS THE ERROR I NEARLY PUBLISHED**
V96–V99 all carried a 427 tap on `gp-0x6b70` (**V100's changelog repoints it AWAY from `gp-0x6b70`,
which dates the earlier target unambiguously**), and routes `r80`/`r81`/`r82` are cached. I computed a
rail-mass statistic on the cached `probe` column against `cs_tq`/`cs_rate` controls, and it looked like
a result — **0.21–0.45 for the probe vs 0.09–0.19 for the controls.**
Then the distinct-value count:
```
   r80  {15, 79, 143, 207}                    4 values, spaced 64
   r81  {23, 71, 87, 135, 199, 215}           6 values, spaced 48/16/48/64/16
   r82  {55, 103, 119, 167, 231, 247}         6 values, same pattern shifted 32
```
⇒ **spacings of 64 and 16 are BIT positions. That column is the cave's packed BOOLEAN RUNG byte, not
a magnitude.** A shape statistic on it is meaningless, and **my rail-mass numbers carry no information
about `gp-0x6b70` whatsoever. Retracted.**
⊕ `field` is the same rung byte; `row2raw14` is a row index. **There is NO magnitude channel for
`gp-0x6b70` anywhere in the corpus** — the earlier taps packed it into the rung byte.
⭐ **The control did not catch this; LOOKING AT THE DATA did.** `cs_tq` behaved perfectly — the
statistic was fine and the *channel* was wrong, which no control on a different channel can detect.
✅ **`rlog-tools/score/observer_relay_shape.py` now REFUSES a channel with fewer than 64 distinct
levels** and prints the levels it saw. **A rule someone must remember became a check that cannot be
forgotten.**

### ✅ **V205 = V202 + the 427 probe on `gp-0x6b70`, sar 6.** 40/40, 3 payload bytes.
`8cf100864be1d603…` · `0x55DF2` → `0x9490`, **sar 6** (±8192 ⇒ raw 0–128 / 896–1023, resolution 64).
**Three live probes now use three different shifts — 5, 5, 6 — because the shift is a property of the
SOURCE, never of the channel.** It answers in one drive: **few levels with mass at the rails ⇒ the
stage IS a relay**, localising the ratchet's named mechanism to one LERP worth the two hops to reach;
**smooth ⇒ the relay lives elsewhere**, worth as much; **railed at ±8192 ⇒ the observer is saturated
and the 41×-corrected `0xC63AA` sensitivity cannot be applied safely at all.**

### 🛑 **V203 RETIRED — `SUPERSEDED-DO-NOT-FLASH-LOWVALUE-…`**
Its question (is the notch bypassed by the pedestal?) **shrank to 7.9 %** once the EMA rate table was
read as flat `K = 20`. **The shelf is V202 (the fix) · V204 · V205 (the two probes worth a slot) · V199
(low-phase fallback).** ⭐ **Of the probes, V205 is the one to fly** — it aims at the ratchet, the one
symptom nothing in sixty builds has moved.

## 🛑🛑 **THE `0xC63AA` SENSITIVITY IS 41× UNDERSTATED IN THE RECORD — and the dilution ratio is nearly closed**

`BUILD-LINEAGE.md` parks `0xC63AA` as *"still the best structural lever, but it needs the **dilution
ratio** first"*, with the sensitivity recorded as `d(iVar6)/d(0xC63AA) = −(1/16)·(gp-0x6b4c/1024)`.
Mirroring `FUN_00038148`'s decompiled arithmetic exactly:
```c
   0x38148   SUM    = sum over SIX lanes of (x_i * gate_i * w_i) >> 10      // ZERO-REJECT gates
             scaled = (SUM * sgn(gp-0x6752) * cal(0xC6468)) >> 10           // cal = 2639
             target = scaled * 0x10                    // <-- the record DROPPED this
             model += ((target - model) * cal(0xC63AC)) >> 10               // alpha = 102/1024
             resid  = gp-0x6bfe - (model >> 4) + gp-0x6bfa                  // <-- it KEPT this
```
🛑 **The `*0x10` and the `>>4` CANCEL** — the model is stored 16× oversampled so the EMA keeps
precision; it is **not** a divide in the signal path. Perturbing the mirror rather than trusting the
algebra: **zeroing the weight moves the residual by 2.577 × `gp-0x6b4c`**, against the recorded 0.0625.
**2.577 / 0.0625 = 41.2×.**
⚠ **This cuts BOTH ways.** It is far more potent than the record believed — and therefore far more
able to destabilise. `gp-0x6b70` is clamped to ±cal(`0xC6200`) = **8192**, and 2.577 × a `gp-0x6b4c`
of 4000 already **exceeds** it. **This is a lever to size carefully, not a free one.**

### ✅ **TWO OF THE THREE UNKNOWNS ARE NOW CLOSED**
```
   the six model lanes, their weights and their ZERO-REJECT windows (V202)
     gp-0x6bd0  w 0xC63A0 = 1024   +-2048    0 in 100 % of the micro regime
     gp-0x6bbe  w 0xC63A2 = 1024   +-2048    p50 74
     gp-0x6b46  w 0xC63A4 = 1024   +-1024    ** <= 512 BY CONSTRUCTION **   <- CLOSED
     gp-0x6b26  w 0xC63A6 =  512   +-1024    <= 511, clamped by 0xC407E     (V181 halved this weight)
     gp-0x6b4e  w 0xC63A8 = 1024   +-10240   ** gp-0x3d8c SATURATED to +-10240 **   <- THE UNKNOWN
     gp-0x6b4c  w 0xC63AA = 1024   +-10240   < 4096 measured (duty 0.000000 for >= 4096 / 17,614 fr)
```
- **`gp-0x6b46` — CLOSED.** `FUN_00036682`'s tail clamps its driver to **±0x200** and EMAs toward it
  (cal `0xC63D2`), so it can never approach its own ±1024 reject window. A lag-compensator error, not
  a large term.
- **`gp-0x6b4e` — THE ONE REMAINING UNKNOWN, and it is BIG.** `0x2743E`–`0x2746A`:
  `ld.w -0x3d8c,gp,r11` · `movea 0x2800,r0,r26` · `bgt` · `movea -0x2800,r0,r9` · `cmovle r9,r11,r26`
  · `st.h r11,-0x6b4e,gp` (+ lockstep twin at `-0x4cd6`). ⇒ **`gp-0x3d8c` SATURATED to ±10240** — the
  same ceiling as `gp-0x6b4c`, and its reject window is exactly ±10240 so it **never drops out.**
```
   dilution = (gp-0x6b4c * w) / SUM, from the mirror with every other lane at its recorded value
     gp-0x6b4c      gp-0x6b4e = 0      gp-0x6b4e = 500
         250            43.2 %              15.8 %
        1000            75.3 %              42.9 %
        4000            92.4 %              75.1 %
```
⇒ **Whether `0xC63AA` is diluted or dominant is now ENTIRELY a question of how big `gp-0x6b4e` runs —
one number, never measured in the whole corpus.**

### ✅ **V204 = V202 + the 427 probe on `gp-0x6b4e`.** 40/40, 3 payload bytes, control cells identical.
`30e7da9f6d20ff13…` · `0x55DF2` → `0x94B2`, sar 5 (±10240 ⇒ raw 0–320 / 704–1023, resolution 32).
**Small ⇒ `0xC63AA` is the strongest cal-only structural lever in the kit, to be sized against the
±8192 clamp. Comparable or larger ⇒ genuinely diluted, and it should be STRUCK rather than left
parked** — which is itself worth knowing after it has sat open since 2026-08-20.

## 🛑 **THE 8 Hz RATCHET NOTCH STAYS REJECTED — and the friction lane is NOT “reverted to Honda”**

### ✅ **V184's 8 Hz NOTCH RE-PRICED UNDER THE CORRECTED UNDERSTANDING — still the wrong trade**
V184 was killed on **−40.5°** of phase, reasoned when the biquad was believed to sit in the **LKAS
command** path. It sits in the **base power-assist** path, so that phase is steering FEEL, not command
tracking — a different currency, and the lever deserved re-pricing. **29,348 candidates, same gate:**
```
   budget   6-9 Hz (ratchet)   16.3-23 Hz (grind)   phase @1/3/5 Hz        zeros poles radius
    5 deg        1.34x               0.91x          -0.3  -1.4  -4.6        9.25  9.12 0.9925
   12 deg        2.56x               0.93x          -1.2  -4.5 -11.8        8.62  8.38 0.9900
   20 deg        3.50x               0.94x          -2.2  -7.8 -19.2        8.25  7.88 0.9875
   40 deg        6.96x               1.03x          -6.3 -20.6 -39.8        8.25  6.88 0.9725
   -------------------------------------------------------------------------------------------
   V202          1.00x            ** 7.3x **              -7.8 at 5 Hz
```
⇒ **2.56× on the ratchet costs MORE phase than 7.3× on the grind**, and 🛑 **the 16.3–23 Hz column
shows it forfeits the grind fix entirely** (0.91–1.03× — at or slightly worse than Honda).
⇒ **There is ONE biquad and ONE zero pair: it serves the grind OR the ratchet, never both.**
**V184's rejection survives on its own terms. The biquad stays on the grind.** ⊕ Why it is so weak:
6–9 Hz is a 3 Hz-wide band at a low centre, and a notch narrow enough to pass the gate (r ≈ 0.99)
nulls only a sliver of it while its phase skirt reaches down into the 1–5 Hz band the driver lives in.
Added group delay at the 12° point is **+3.32 → +15.83 ms** vs V202's +3.80 → +5.52.

### 🛑🛑 **A MISLEADING LABEL IN MY OWN DOCS — the friction lane is at 0.200× HONDA, not Honda**
```
   friction = clamp(motor_rate * 12 / knee, +-1) * (|model| * K1/1024 + K0/1024)

   build   0xC40BC knee   0xC40D2 K1   multiplier vs Honda BELOW saturation   saturates at
   stock        600           102                1.000x                          50
   V122         3000         1020                2.000x                         250     <- FLEW
   V202         3000          102             ** 0.200x **                      250
```
**V177 reverted K1 (1020→102) and the record — mine included — calls that “K1 → Honda”.** But the
**ramp knee was never reverted**, and the knee multiplies the whole expression:
`(600/3000) × (102/102) = 0.200`. ⇒ **The lane is at ONE FIFTH of Honda's friction below saturation,
and saturation now needs 5× the motor rate (250 vs 50).** Above saturation it equals Honda exactly —
but the ratchet lives in the LOW-rate regime, which is entirely the 0.200× regime.
⊕ **A guard now prints this multiplier for every flashable image at close-out**, so “K1 → Honda” can
never again read as “friction is Honda's”.

### ⚖ **WHY IT IS LEFT ALONE — stated, not silently chosen**
The knee cuts **both ways** and the two directions are in genuine tension:
- **For leaving it:** Coulomb friction is *"exactly what makes torque ripple without motion"* — the
  ratchet's own signature (13.5× on `cs_tq`, 1.7× on `cs_rate`). 0.200× means **less ratchet**. It also
  matches the standing operator directive: *low apparent steering mass and friction to LKAS.*
- **Against:** the record's verified polarity is **more modelled friction = MORE assist** (nine links,
  Ghidra-traced). So 0.200× is also **an authority reduction** in that lane — against a stated goal.
🛑 **Reverting the knee to 600 would RAISE friction 5×, which contradicts a standing operator
instruction, so it is NOT built.** It is recorded here as the one remaining unattributed non-stock cell
in the friction lane, with its effect stated in both directions, for the operator to decide.

## ✅ **TWO AUTHORITY LEVERS CHECKED AND CLOSED — and a latent 18.52 Hz injector found silent**

### ✅ **THE SIGN-FLIPPING SQUARE-WAVE INJECTOR IS INERT — checked on the CURRENT build, not inherited**
`BUILD-LINEAGE.md` flags `0xC64DE` as *"a latent, engagement-triggered 18.5 Hz square-wave torque
injector wired into the 6× gain path, four halfwords from being live"*. Read from the images:
```
   0xC64DE (a BYTE, not a halfword)   stock 17 => 29.41 Hz     V202 27 => ** 18.52 Hz **
   0xC6734  n = 4
   0xC6736  X = [0, 31872, 31936, 32000]
   0xC673E  Y = [0, 0, 0, 0]      <-- stock AND V202.  ** SILENT. **
```
⇒ **NOT the grind's source.** Two independent reasons it cannot fire: the amplitude LERP is all zeros,
and the record's *"every other writer of `gp-0x6b2c` is a store-zero"*.
⚠ **But V18's 17→27 moved a latent injector INTO the grind band** (p10 16.33 / median 20.12 / p90
22.15 Hz), and its amplitude table sits **24 bytes from `0xC674E`/`0xC6750`, which this kit edits**
(1024→5120). **A guard is now in `closeout_verify_published.py` — every flashable image is checked.**
⊕ Reverting `0xC64DE` 27→17 is **a functional no-op while the amplitude is zero**, so it is hygiene,
not a fix. **Not built** — it would add a shelf build for no measurable change.

### ✅ **THE SETPOINT CLIP IS CLOSED — already built as V108 E3 and PULLED on its own null**
`0xC61BE` = 15360 was raised to 16384 and killed by its pre-registered endpoint: route `1e`, 93,356
frames / 924 s, achieved `|rate_c|` low-half-vs-top **still rising at all five speed bins** (3.89× /
3.12× / 2.91× / 2.62× / 2.14×, every CI excluding 1.0) where a bound clip would pin it flat.
**The clip is IDLE. Do not re-propose it.**

### ⭐ **SO WHAT DOES LIMIT AUTHORITY? THE ARITHMETIC, READ FROM THE IMAGE**
```
   lane_max = (setpoint_clip * gain) >> 15          clip = 15360

   stock       0xC646C =  891   ->   417 counts =  4.1 % of the aggregator clamp 10240
   V202 (6x)   0xC6CD0 = 5346   ->  2505        = 24.5 %
   8x          0xC6CD0 = 7128   ->  3341        = 32.6 %   ** exceeds the 3072 fwd clamps **
   10x         0xC6CD0 = 8910   ->  4176        = 40.8 %
```
⊕ Anchor reproduces exactly: `(15360 × 891) >> 15 = 417` = the separately recorded stock-V9 maximum.
⇒ **The aggregator has 4× unused headroom; nothing downstream binds at 6×.** The forward clamps
(`0xC61B2`/`0xC61B4` = 3072) are inert at 6× **because 2505 < 3072** — that is the real reason behind
*"0 % of the effect"*, and it also shows **why V101 had to raise them to 4096 for 8×: 3341 > 3072.**
⇒ **Every other candidate is measured non-binding**: the setpoint clip (idle), the `0xC520C` cap table
(`gp-0x4f64` at its max 4762 for 99.9 %+ of engaged time), the low-speed lockout (zeroed since V53).
⇒ 🛑 **`0xC6CD0` IS THE ONLY FIRMWARE AUTHORITY LEVER.** That is why it has been attempted three
times, and the enumeration is now closed rather than open.

### ⭐ **A TESTABLE PREDICTION THAT MAKES THE SEQUENCING CONCRETE**
The record measures **vibration ∝ m^1.74 but authority only ∝ m^0.88** for a gain step m. **A
sublinear authority exponent means something is eating the command — and the obvious candidate is the
vibration itself**: a command oscillating at 23 Hz partially cancels its own steering effect, so net
authority grows slower than the gain that produced it.
⇒ **If that is right, cutting the 23 Hz loop gain should RAISE the exponent toward 1.0**, and V202
cuts it **3.4×** there. **Sequence: fix the grind → re-measure the authority exponent → then raise the
gain.** ⚠ **BELIEF, not evidence** — it needs a gain pair measured on a notched base, which no drive
has ever provided. But it is the first mechanism offered for the sublinearity, which the record has
carried as a bare number since V101.

### 🛑 **TOOLING GOTCHA — `stock_fw_dump/code.bin` reads `0xFFFF` at `0xC6CD0`**
Because **V57 CREATED that cell** (it decoupled the forward reader off the shared `0xC646C`, which is
byte-identical 891 in stock and V202). **Do not use the stock dump as a stock reference for post-V57
migrated cals** — it will hand you 65535 and a 0.08× "stock gain". `0xC646C`, `0xC61BE` and `0xC64DE`
read correctly from it.

## 📁 **EARLIER STATE (V184 → V202) IS ARCHIVED**

Split out 2026-08-30 at **173.6 KB**, past the ~150 KB soft target. Everything from the V202 notch work downward now lives in `docs/archive/STATE-ARCHIVE-2026-08-30-v184-v202.md` — **a record, not an instruction.** All of it is superseded: the candidate is **V222**, the ladder is V223–V226, and that notch was replaced at V208 and again at V217/V222.
