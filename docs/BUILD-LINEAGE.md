# Build lineage and lever index — CHECK THIS BEFORE PROPOSING ANY CALIBRATION EDIT

**Why this file exists:** on 2026-07-27 two independent agents, in the same session, proposed
`0xC6450` 1024→32 as a "new, never-flashed" vibration lever. **It is V46 verbatim — flashed, null.** A
third nearly repeated it with `0xC644A` (V43, flashed, null). Both had read `CLAUDE.md`; the flashed
result was buried in prose.

> **RULE: before naming any calibration address as a lever, grep `analysis-2020accord/build_v*_tva.py`
> for it and check the table below. State its on-car result in your recommendation.**

---

## Part 1 — Lever index, by address

**FALSIFIED** = flashed and demonstrably changed nothing for its target symptom. It is not "untested".

> **RULE 2, added 2026-07-30:** the table below covers **V9→V58 only**. Levers rejected in the
> **pre-V18 era** live in `memory/project_accord_torque_mod_v0.md`, and their absence here let a
> subagent re-propose `0xC61D6` — a lever an 11-round review had labelled *"highest-risk; last/never"* —
> as a fresh candidate. **The pre-V18 rejections are now folded into the table.** If an address is not
> here, grep `analysis-2020accord/old_tools/build_v*.py` and `memory/project_accord_torque_mod_v0.md`
> before calling it untested.

| address | what it is | build | flashed? | on-car result |
|---|---|---|---|---|
| cave payload @`0xC4B34` → the **boost-index DEPTH probe** | `0x14A` byte4: bit7 liveness, bit6 = `gp-0x6ba6 < 0` (the `0xFFFF` fault sentinel), **bit5/4/3 = a THERMOMETER on `gp-0x6ba6` at 512 / 1024 / 2048** (sense "index < T"; monotone bit5⇒bit4⇒bit3, so a wrong build is detectable rather than plausible) | **V59** | ❌ **BUILT 2026-07-30, UNFLASHED** | **NO calibration change** — 19 bytes off V58, cave + MAIN CRC only, **CAL CRC unchanged** (machine proof). Same base/hook/68-byte extent as V55/V57/V58, all flown clean. **No new encoder and no new condition code** (BGE + BNE only, both pinned to real instances). Answers the one thing V58 could not: **DEPTH.** `gp-0x6ba6 == \|gp-0x6b9a\|` indexes both boost amplitude LERPs, and V58 showed the signed sibling crosses zero at 20.93 Hz only when LKAS applies ⇒ the index is that signal rectified, sweeping the curve at ~2× the mode frequency. But a sign bit carries no amplitude: **if `\|gp-0x6b9a\|` never clears X1 = 512 the coefficient stays pinned at 16384 and NOTHING modulates.** Build asserts both LERPs still resolve at the same mode and `tp+0x7498/0x7499` are still 1. Decoder `rlog-tools/decode_v59_boostindex.py` (hard-stops above 1% non-monotonic). RWD SHA `ce7f6af6d7475a94462505a5f989d282966e00c9717cf6f2bbbc8b43ccdd3fc7`; image SHA `c6020a32780c1c8d952782426deef25ae390afee4606f319b0aa3c3998158d6d` |
| cave payload @`0xC4B34` → the **angle-rate/boost-lane probe** | `0x14A` byte4: bit7 liveness, **bit6 = `gp-0x6bbe < 0` (the damping phase)**, bit5 = `gp-0x6bbe == +512`, bit4 = `gp-0x6b9a < 0`, bit3 = `gp-0x6b9a == 0` | **V58** | ✅ **FLASHED 2026-07-30, route `2b`** | ✅ **FLIGHT-CLEAN** — 14 segments, 83,959 frames, zero `steerUnavailable`/`steerTempUnavailable`/`canError`/`controlsMismatch`/`immediateDisable`; `STEER_STATUS == 0` in 83,959/83,959 and **`ST==4` = 0** (extends V57's 0/37,922). ★★ **bit5 = 0 in all 35,964 frames ⇒ the ceiling `0xD20C0` is ELIMINATED**; `K1` keeps its headroom. 🛑 **bit6 VOID BY CONSTRUCTION** — `gp-0x6bbe` crosses zero 0.00–1.10 /s where 22 Hz needs ~44/s, so the damping sign is **still open**; ⚠ pooling the runs manufactures a splice artifact (5/0/0/1 transitions *within* runs). ★★ **bit4 fired**: 20.93 Hz, per-run coherence 0.649/0.970/0.769/0.881, and **13.69 toggles/s engaged vs 0.61 disengaged** at matched creep. 🛑 **This build's own docstring was WRONG about `gp-0x6b9a`/`0xD28DC`** — corrected in place; see `STATE.md` "Signal-identity corrections" | **NO calibration change** — 59 bytes off V57, cave + MAIN CRC only, and the **CAL CRC is unchanged** (machine proof). Same base/hook/68-byte extent as V55 and V57, both fault-free. Exists because every cal lever for both symptoms is closed and the `gp-0x6bbe` damping sign flipped three times under static analysis. Measures it on-car instead: cross-spectrum phase of bit6 vs `STEER_ANGLE_RATE` (already on the bus). **Method pre-validated** — V57's bit3, also a 1-bit sign channel, gave coherence **0.958 at 21.31 Hz**. bit5 decides whether `K1` is a lever at all: the ±512 ceiling is a SATURATING clamp, so if the lane pins, the damping derivative is ZERO at the peaks and the lever becomes the ceiling `0xD20C0`, not `K1`. Decoder `rlog-tools/decode_v58_boostlane.py`. RWD SHA `7b3cfff05116a22137c1376b78e69d955ac75397b8091e089da4b0379a5948f7` |
| 🛑 **`0xC61D6`** slew step `0` → 14 | `FUN_00042af8` delivered-command slew limiter, accumulator `gp-0x356c` | **V16** (`old_tools/`) | ❌ **REJECTED ON REVIEW, NEVER FLASHED** | 🛑🛑 **DO NOT PROPOSE. "Highest-risk lever; last/never."** An 11-round, 4-analyst, decode-verified Ghidra review found slew=0 **FREEZES** a dormant speed×torque 2D shaping lane (curves `0xC6770`×`0xC69E8`); 0→14 **ACTIVATES an uncalibrated map onto the live command** (mux `0xC64C9`=0). Byte-verified 2026-07-30: **`0xC61D6` = 0 in V31/V38/V42/V53/V55/V57** — stock throughout. ⚠ `.claude/agent-memory/…/reference_accord_slew_limiter.md` still *recommended* this; corrected 2026-07-30 with a header, addresses kept |
| `0xC6424` shaper deadband 29491→20000 | gates only the `gp-0x356c` limiter | **V17** (`old_tools/`) | ❌ rejected | **INERT** — with slew=0 that state is pinned at 0, so the edit is behaviourally null. **Deadband and slew are COUPLED**; neither is independently useful |
| `0xC64DE` re-engage ramp `0x11`→`0x1B` (17→27) | **LENGTHENS** re-engage; targets the **recovery ratchet**, not the initial snap | **V18** | ✅ | ✅ **ROAD-VALIDATED — "drives well."** Byte-verified 2026-07-30: still **27** in V31/V38/V42/V53/V55/V57, carried forward correctly. ⚠ Targets the ~10 s recovery ratchet — **wrong timescale for the ~7.4 Hz ratchet** |
| **`0xC4018`/`1C`/`20`** and **`0xC4048`/`4C`/`50`** | two **3-tap FIR** coefficient triples (32-bit floats), `FUN_0003b66a` / `FUN_0003b8f6` | — | ❌ never in any build | 🛑 **NOT A NOTCH LEVER — closed on arithmetic 2026-07-30.** Both are stock **(1.0, 0.0, 0.0) = identity**, exactly one consumer each, no variant-coding. It is a genuine transversal FIR (`y = b0·x[n]+b1·x[n−1]+b2·x[n−2]`, states `gp-0x365c`/`gp-0x3658`), **not a 2-pole IIR**, so it is unconditionally stable — but at **1 kHz** a 21 Hz notch needs `b = [1, −1.9826, 1]`, which costs **−35.2 dB at DC** (21 Hz is 2.1% of Nyquist, so the zeros sit essentially at DC). Normalising to unity DC needs `b ≈ (57.5, −114.0, 57.5)` with **229× peak gain**. Ill-conditioned; would amplify HF motor-rate noise. ⚠ A third float `1.0` at `0xC4024` is **not** an FIR coefficient — it is an EMA alpha in `FUN_00023850` (an unrelated PID) |
| **`0xD2006`** 102→**43** | ★ **the boost-amplitude BLEND rate** — `0xCA06C[mode 10]`. The slew on the **output** of BOTH amplitude LERPs, applied before they multiply anything. **Was not in the golden model at all until 2026-07-30.** Direction confirmed @`0x34be4` (`cmp r25,r10 / ble` ⇒ instant snap when raw ≤ old): **FALLING instant, RISING slowed** — a fast-attack/slow-release gain reducer | **V60** | ❌ **BUILT 2026-07-30, UNFLASHED** | Attenuates the 42.19 Hz parametric pump **without moving the static gain map** (the blend converges to the same steady state ⇒ DC assist and manual feel untouched). Q10 0.0996→0.0420; 42 Hz transmission ~0.37→~0.17; τ 10.0→23.8 ms @1 kHz. Predicted **eps p99 0.169 → 0.099**. 🛑 **The effect SATURATES** — the falling edge is instant regardless of the coefficient, so it buys ~1.7× then flattens (cal 32 only reaches 0.086); **43 is the knee**. **5 bytes off V59** (1 cal byte + its `[0xD2000,0xD2FFC)` block CRC); ⭐ **MAIN and CAL CRCs both UNCHANGED** = machine proof the cave/probe and every `0xC6xxx` cal stayed put. GATE 1 vacuous. GATE 2: base-assist path, no LKAS-only fork exists — but a pure *dynamics* change on a gain-**scheduling** variable, no added gain, no static-map movement, no steady-state change. Blast radius byte-verified: one pointer (`0xCA094`); the three identical 102s in `0xD2000` are modes 10/11/12's **independent** entries, not an array. ⚠ **Expected to be NULL** given the loop finding — fly it as a **DISCRIMINATOR**. V59's probe rides along unchanged as the CONTROL |
| `0xC63A0`–`0xC63AC`, `0xC64AD`–`0xC64B3`, `0xC6200` | weights/gates on the **second aggregator** chain `FUN_00038148` → `gp-0x6b70` → `FUN_00037fe6` → `gp-0x6ad6` → `FUN_0003a382` → `gp-0x6ad4` | — | ❌ never in any build | ⚠ **Genuinely untouched — and NOT recommended.** All weights are **unity (1024 = 1.0) and stock**, byte-read ⇒ **no hidden loop gain in the aggregation.** ★★ The chain's only output-shaping cal is **`0xC6AF0`, which V56 already zeroed and flashed: NULL on the grinding + cost damping.** Since `gp-0x6ad4` has only 2 accesses image-wide, that mute deleted the whole chain's contribution ⇒ **this path is already tested end-to-end by deletion.** New structural fact worth keeping: boost **and** damper re-enter this second aggregator at unity gain, in parallel with `FUN_0003aa2c` |
| `0xC6372` / `0xC636E` | boost + damping lane input EMAs (both 205) | — | ❌ | 🛑 **DEAD BRANCH — do not analyse or edit.** `tp+0x7498 = tp+0x7499 = 1` (byte-verified, stock and every build) routes **both** boost and damping past the torque-EMA fallback to read `gp-0x6ba6` directly. The EMA still computes into its shadow pair but its result is never consumed. Any GATE-2 phase/dB table for these two cals is analysing a lever with **zero effect** |
| `0x2A1F0` disp `0x746C`→`0x7CD0` + `0xC6CD0`←3564 + `0xC646C`→891 | **the `0xC646C` DECOUPLING** — forward LKAS path gets a private gain word; the four feedback readers revert to stock | **V57** | ❌ **BUILT 2026-07-29, UNFLASHED** | 🛑 **CORRECTNESS FIX — expected NULL for the grinding** (≤0.28 dB at 22 Hz; of the **11** aggregator summands only `FUN_00036682` reads the cal, at −46 to −58 dB). Reader set independently re-enumerated: exactly **6** (1 forward, 1 dead in the `>0x2a30d` dead-copy region, 4 feedback). ✅ **no float mirror** — fresh 32-bit scan of `[0x7440,0x74A0)` → 0 hits ⇒ no V27 desync class. ⚠ **manual feel WILL change** (readers #3-#6 are not engagement-gated). ⚠ Reader #6 is **not** a second additive path — it modulates #5's hysteresis dead-band *width*. **Flash V55 first** | ⊕ **ALSO CARRIES THE DEADBAND-GATE PROBE** (V55's cave payload replaced, same base `0xC4B34` / hook `0x55C0E` / 68-byte extent): `0x14A` byte4 bit7=liveness, **bit6=(gp-0x6806==0) — the EXACT gate test the bus cannot give**, bit5=(gp-0x69b0!=0), bit4=(gp-0x6b30==0), bit3=(gp-0x6b30<0). Closes the parity hole in the deadband elimination (the packer's `andi 0x1` transmits bit0; the gate tests equality). Expected NEGATIVE |
| **`0xC6AFC` + `0xC6AFE`** 32768→0 | `FUN_0003a382` output-bound LERP Y[0]/Y[1] — the **branch-agnostic mute** of the whole `gp-0x6ad4` lane | **V56** | ✅ | 🛑 **FALSIFIED FOR THE VIBRATION *AND* HARMFUL — 2026-07-29, route `24`.** 21 Hz unchanged (**786×** engaged/disengaged speed-matched, vs V55's 877×) and the command's 21 Hz did **not** drop ⇒ **the lane is ELIMINATED as the 21 Hz source, all three branches at once.** ★ It also **cost damping**: operator reports damping removed, and an intermittent **8.69 Hz** line appears (1.18e8, 6.7× its neighbours, 15-20 m/s, engaged+hands-off). **REVERT TO V55.** 🛑 A 50% partial restore (`Y=16384`) is **not** a candidate — 0% and 100% already agree, so intermediate authority is bounded between two agreeing measurements |
| `0xC6450` | `FUN_0003a382` **Stage-A = the P term's own extra smoothing EMA** (1024 = exact unity) | **V46** | ✅ | ⚠ **RE-FRAMED twice.** 1024→32 = −12.6 dB at 21 Hz, one of three branches — *and* 2026-07-29: it was **re-introducing a defeated pole**, not filtering the lane. Moot now: V56 eliminated the lane |
| `0xC644A` | `FUN_0003a382` **Stage-C = the D term's own extra smoothing EMA** (1024 = exact unity) | **V43** | ✅ | ⚠ **RE-FRAMED — same reason.** 1024→64 = −7.1 dB, one branch of three. Moot: lane eliminated by V56 |
| `0xC643E` / `0xC6445` + `0xC6A72/86/9A/AE` | `r26` adaptive torque-rate gain surface | **V42** ch.2 | ✅ | 🛑 **FALSIFIED.** ⚠ **RE-PROPOSED AS "NEVER PREVIOUSLY PROPOSED" BY A SUBAGENT ON 2026-07-29** — r24/r26 are the two *unfiltered, 1 kHz, same-signed* torque-rate summands, so they look irresistible in any fresh lane audit. **They are both already flashed and null.** V42's own builder records why the combined-kill argument is weak: *"r24 carries a ±3 DEADZONE (cal `0xC61F6`) which is why V39's r24 kill was a no-op near zero"* — so V42 already killed the branch that was live near zero. 🛑🛑 **DIRECTION CORRECTION 2026-07-31: the combined kill WAS eventually run (V61) and it made the grinding WORSE, in engaged AND manual driving.** This lane is the mode's **damper**. The nulls above are real but they bracket the **wrong side of the optimum** — every one of V39/V42/V61 tested it DOWNWARD. **Cutting this lane is closed for good; RAISING it is V62.** ⚠ Note this is the *inverse* of the FactorC/V44 trap: there a withdrawn **rationale** was mistaken for a withdrawn **result**; here every result stands and only the **direction** was wrong. Both errors come from the same habit — reading a lever's history as a verdict on the *address* instead of on the *direction tested* |
| `0xC6440/42/46`, `0xC61F6` | `r24` direct Sensor-B rate lane | **V39** | ✅ | 🛑 **FALSIFIED** — and near-inert by construction (±3 deadzone). See the r26 row's re-proposal warning. ⚠ **DIRECTION CORRECTION 2026-07-31 — see the V61/V62 rows below: this lane is the mode's DAMPER and V39 tested it DOWNWARD.** |
| `0x3AB6C` `37E1`→`37E0` + `0x3AC16` `4001`→`4000` | **kill the torsion-bar RATE lane at BOTH taps** of its shared `r1 = clamp(gp-0x4f62, ±5120)`. Two single-bit reg1 `r1`→`r0` changes, no cave | **V61** | ✅ **FLASHED 2026-07-31** | ★★★ **WORSE — the kit's FIRST SIGNED on-car result, and it INVERTS the record.** Operator: grinding *significantly worse* with LKAS on (higher amplitude, louder), **and newly present in MANUAL driving** — unmistakably **in reverse**. ⇒ **r24/r26 are the mode's DAMPER, not its amplifier.** Sign verified from image bytes: polarity `gp-0x6752` is **one load @`0x3AB78` reused by both lanes and by `FUN_0003a382`'s P-term** (so it *cancels*), and the combine chain `0x3ACC8`–`0x3ACDA` is **ten `add`s, no `sub`** ⇒ `+Kd·d(T_bar)/dt` in phase with assist. For the wheel-inertia-on-bar mode that gives `phi'' + (Kd·k/J_c)·phi' + … = …` — **positive damping, linear in Kd; at Kd=0 there is no damping term at all.** 🛑 **A derivative is DC-neutral**, so "V61 removed assist" is ruled out — it changed *only* dynamics, which is what makes this a clean signed measurement. 🛑 **Falsifies `eps_lkas_chain_model.py:1792`'s "r26 = excitation-to-amplifier" framing** (struck and corrected in place). ⇒ **V39, V42 and V61 all tested this lane DOWNWARD**; their results stand but bracket the **wrong side of the optimum**. The gradient points **UP** |
| `0xC6440` 2048→**4096** + `0xC643E` 1536→**3072** | ★★★ **raise ONLY the OSCILLATION-DETECTED gain arms** of both rate lanes. Both lanes' gain priority chains end in `assist_state gp-0x671a >= 5`, and `gp-0x671a` is a **HARD-REVERSAL COUNTER** (`FUN_000428d4`, 1 kHz: the neutral state resets it to 0 **every tick** and only exits when `\|gp-0x6c2c\| > 12800`; a crossing of the *opposite* threshold increments it; 50 quiet ticks clear it). ⇒ it reads **0 during smooth steering**, so `state>=5` = **an oscillation is happening** | **V63** | ❌ **BUILT 2026-07-31, UNFLASHED — THE RECOMMENDED NEXT FLASH** | ★★★ **Built in response to the operator's objection that V62 changes MANUAL feel to fix an LKAS-specific symptom — and it removes that cost by construction.** Raising only the `state>=5` arms adds damping **only while oscillating**; both smooth-steering LERP defaults stay stock. **A smaller edit than V62**: 6 bytes off V59 (2 cal bytes + CAL CRC), ⭐ **MAIN CRC UNCHANGED** = machine proof no code moved; V62's shifts and V61's kill both asserted absent ⇒ independent, not layered. ✅ **No new arithmetic risk — 3072 is already `gain_A`'s own stock maximum**, so worst-case `stage1×gain` stays at 47% of INT32_MAX. GATE 1 vacuous. 🛑 **POLARITY WAS DISPUTED BY TWO SUBAGENTS AND RESOLVED BY THE ORCHESTRATOR IN GHIDRA** — one trace read `0xC643E` as the `state<5` arm, which would have raised the **smooth-steering** gain: all the manual-feel cost, none of the benefit. Verified: `0x3AA7C cmp r14,r12`/`bc` ⇒ `r2=1` iff `state>=5`; `0x3AB66`/`0x3AC10` `be` skip the loads when `r2==0`. 🛑 **Residual — a NULL IS AMBIGUOUS:** whether `gp-0x6c2c` crosses ±12800 in the real vibration is unverified; if not, V63 is **inert**. **Resolve with no probe and no cave: fly V63 first, then V62 if null.** 🛑 `gate_671d` outranks r24's arm and is live ⇒ **expect r26 to carry it**. Image SHA `2f843bce…`; RWD SHA `5e5f83d7…` |
| `0x3AC20` `42AA`→`42A9` + `0x3AB76` `32AA`→`32A9` | **double the rate lane** — `sar 0xa` → `sar 0x9` on each lane's final shift | **V62** | ❌ **BUILT 2026-07-31, UNFLASHED — now the FALLBACK behind V63** | ★★ **The matched inverse of V61**: V61 took `Kd`→0 and the mode diverged, V62 takes `Kd`→2× — the same-sized step back. Stock sustains with **no ring-down at all** ⇒ `zeta_net ≈ 0`, so doubling should move it to `+zeta_lead`. **6 bytes off V59** (2 immediate bytes + MAIN CRC), 8 off V61, 88 off V38; ⭐ **CAL CRC and `0xD2000`-block CRC both unchanged** = machine proof no calibration moved. 🛑 **`sar` immediates chosen OVER the gain cals** for three traced reasons: (1) the gain is a **priority chain** whose live arm can't be pinned statically (`gp-0x671a` is a bounded [0,5] *persistence ramp* that plausibly never saturates during a 21 Hz oscillation; `gp-0x671d` is an event counter possibly self-excited by it); (2) **r24's default arm is MODE-INDEXED** via `gp+0x63fd` through four pointer arrays — `0xD2AEC`←`0xCC154` idx 10, `0xD6AEC`←`0xCC184` **idx 22**, so ⚠ **`0xD6AEC` is a different MODE, not a redundancy twin — the "V27 desync class" reading was wrong**; (3) `gp-0x683c` has **zero writers** ⇒ `0xC6446`/`0xC6444` are dead arms (single-method, wants a raw byte scan). A `sar` edit doubles the lane **under every arm and every mode**. 🛑 **`0x3AB76` not `0x3AB70`**: V850 `mul` discards the high word into `r0`, and doubling before the `×gain_A` multiply pushes the worst case to **94% of INT32_MAX** vs 47% (unchanged) after it. **Headroom is arm-dependent** — ~22×/~11×/**~7.3× worst case**; doubling keeps ≥3.6× margin. GATE 1 **vacuous** (no cave). ⚠ Residual: `avg(gp-0x69a4)` magnitude still unmeasured. ⚠ Manual feel will change. Image SHA `80d9e1f7…`; RWD SHA `1e0806a1…` |
| `0xD27C6` / `0xD27DA` | damper Factor C Y[0] — **variant-coded, entries 10/11**. 🛑 **2026-07-29: the axis is SPEED, not driver torque** — index load in `FUN_00034350` is `gp-0x6a5e` (voted vehicle speed, settled), X=(2240,3840,5120,8960) ≈ **35/60/80/140 km/h**, so `Y[0]=0` means *below ~35 km/h*. **V44 tested a mechanism that does not exist**; its on-car result stands, its rationale is withdrawn. The "2240 counts driver torque" figure is a **number collision** with the unrelated override curve at `0x29a74`. Invalid speed ⇒ factor defaults to **unity**, not zero | **V44** | ✅ | 🛑 **FALSIFIED** (Factor E re-zeroes the product). ✅ **2026-07-28: confirmed it hit the LIVE table.** PN `39990-TVA-A160` → key `TVAA1` → config row 2 → INDEX **10** → `0xD27BC`, exactly what V44 edited. ⚠ one-bit residual: the coded row is in EEPROM, not the flash dump, and the TVA family splits ({TVAA0,2,4}→idx 4). **V55 carries a telemetry bit for it**. 🛑🛑 **RE-PROPOSED 2026-07-30 BY THE ORCHESTRATOR as "V61" (`Y[0]` 0→64 — a *weaker* V44) and caught by the OPERATOR; script written and deleted unexecuted.** The new *mechanism* (an uncompensated positive-feedback loop through the torque sensor) made the old *address* look fresh, and V44's **rationale had been withdrawn** — which is not the same as its result being withdrawn. **A withdrawn rationale does not withdraw an on-car null.** ⚠ And note the arithmetic reason V44 failed: the damper is **four chained Q10 multiplies**, so raising one factor is worthless while any other still zeroes the product — Factor E did. **Before touching one element of a product chain, check every other element.** ✅ Salvage: the damper's int/float lockstep is **ceiling-only** — `FUN_000347b8` *reads* `gp-0x6bd0` and never recomputes the four-factor product (confirmed 4 ways incl. a split-encoding `movhi` check), and the two ceilings are the **same table in two formats** (`INT 0xD209C X=[300,800] Y=[512,1024]` vs `FLOAT 0xC6554 300.0,800.0,0.5,1.0`). Damper authority at creep is firmware-clamped to **±512 of the aggregator's ±10240 (≤5%)** |
| `0xD2802/04/06`, `0xD2816/18/1A` | damper Factor E (motor-rate) deadzone — **variant-coded, entries 10/11** | **V47** | ✅ | 🛑 marginally quieter at 5 mph, **no effect in motion**. ✅ **2026-07-28: confirmed it hit the LIVE table** (same INDEX 10 chain as V44 → `0xD27F8`). ⇒ **the missing-damping hypothesis was genuinely tested and IS falsified** — do not resurrect it on a "wrong variant" theory |
| `0xC4120` + `FUN_0003a382` `uVar27`→256 | type-8 carrier mute | **V48A** | ✅ | ⚠ **RE-FRAMED — one branch of three, like V43/V46** |
| `gp-0x4f60` broad EMA (19 carriers → `gp-0x1300`) | V52C code cave | **V52C** | ✅ | ⚠ **WEAKER THAN IT LOOKS.** `alpha = 74/1024` ⇒ fc ≈ 12 Hz ⇒ only **−6.1 dB at 21 Hz** while *adding* 61° of lag. It halved the mode's content, it did not remove it. **Did change manual feel** (so the cave fired) |
| `0xC6206` (hands-off slew) | governor slew | **V45** | ✅ | 🛑 **FALSIFIED** |
| `0xC6206`/`0xC6208` ← `0xFFFF` | governor slew, both | **V40** | ✅ | ☠ **EPS lamp + no power steering at ignition.** Magnitude, not direction: `0xFFFF` made the guard never fire → snap-to-target → DTC 0x1d → motor off |
| `0xC5030`, `0xC521A`, `0xC5232` | motor-rate cap table | V40/**V41** | ✅ | 🛑 **FALSIFIED** (V41 = clean subtractive test) |
| `0x454FE` `0x65BA`→`0x65B5` | state-4 governor ratchet `bne`→`br` | **V42** ch.1 | ✅ | ✅ **CONFIRMED ROOT CAUSE** — fixed the hard-turn ratchet. Carry forward. ⚠ **NOT present in V38/FOURFRAME** |
| `0xC646C` 891→**1782**→**3564** | the LKAS gain — **shared sensor-scale, 6 readers, 4 on feedback paths** | **V22** (1782), **V38** (3564) | ✅ | 🛑 **CORRECTION 2026-07-29: this was TWO doublings, not one.** Byte-verified across the plain-image archive: stock/V9 = 891, V22-V37 = **1782**, V38+ = **3564**, with clamps `0xC61B2`/`0xC61B4` tracking each step (512→1024→2048). The old "891→3564 at V22" entry was wrong. ★ **The operator has driven all THREE values and reports NO change in manual steering feel** — and when disengaged the forward reader `0x2A1EE` is idle, so manual feel depends only on the four FEEDBACK readers. That is V57's experiment, already run in both directions, null. ⚠ What did NOT track the doublings: the pre-gain deadband `0xC61B8`, still 102 |
| `0xC61B2`/`0xC61B4` 512→**1024**→**2048** | forward-path clamps, doubled with the gain at BOTH steps | **V22**, **V38** | ✅ | correct and intentional. ⚠ `0xC61B8` (the pre-gain deadband, 102) was left behind at both steps — see the deadband box above |
| `0xC62EA` 320→**0** | low-speed steer lockout, 4.995 km/h → 0 | **V53** | ✅ | ✅ **CONFIRMED WORKING** on-car 2026-07-27. Route `1a`: `STEER_STATUS=0` in 5,995/5,995 frames (ST=3 never fires) and **226 frames of `STEER_CONTROL_ACTIVE=1` below 5 km/h** — a cell that is structurally EMPTY on V38. No fault, no dash light |
| `0xC64B8` 112→0xFF | DTC-0x49 fail-counter gate | **V37** | ✅ | ✅ **gentle EME RESOLVED**, no dash-light regression |
| `0xC64B4-B7`, `0xC61C0-C5`, `0xC64E2` | `STEER_STATUS` debounce SM cals | **V36** | ✅ | ⚠ fixed gentle EME but **unmasked DTC 0x49** → superseded by V37 |
| `0xC6312` 320→65535 | gentle-EME decider torque gate | **V33** | ❌ | wrong gate (fires ~10 Hz benign) |
| `0xC65C4/C8/CC` + `0xC6768/6A/6C` | soft-EME boost floor (matched int/float) | **V31** | ✅ | ✅ soft EME resolved. **Do not desync the mirror pair.** ⚠ **V31 set the floor to 4096; V38 RAISED it to 5120** (float 5.0) — byte-verified in `_v54_plain_image.bin` vs stock `0/1536/2048`, and the golden model carries both. The V31 memory's 4096 is correct *for V31*; the car runs V38+, so 5120 is the live value. ★ **On-car proof 2026-07-28:** V54's authority probe read `gp-0x6966` pinned at the bottom bucket for 5,989/5,989 frames *including 17% of requesting frames at openpilot's ±4096 rail* ⇒ the V31 fixpoint is **self-stable and attracting, measured under railed command**, not merely argued |
| `0xC6202` | governor nominal | — | ❌ | **investigated and REJECTED** — buys nothing (4762 > max command), and `gp-0x4f64` is shadowed → fault `0x17`, hard-fault-eligible |
| `0xC6194` | "LKAS-only rate limiter" | — | — | **DEAD calibration** — its gain cal `0xC63CC` = 0 |

### 🛑 `0xC61B8` / `0xC64A3` — the pre-gain deadband + sign relay: ELIMINATED ON-CAR 2026-07-29

`0xC61B8` (=102) is genuinely **un-rescaled** — its siblings `0xC61B2`/`0xC61B4` went 512 → 2048 (×4) with
the gain and it never moved in 30+ builds — and the block **is** on the LKAS forward path (verified:
`r9` → `add r9,r11` @`0x2a1fc` → ×POLARITY×GAIN → clamp → `mov r11,r1` @`0x2a226` →
`cmove 0x0,r1,r16` @`0x2a2c2` → `st.h r16,-0x6b3c` @`0x2a2ea`; the `-0x6b38` store at `0x2a23c` is a
**diagnostic copy**, and a subagent stopped there and wrongly called the whole block diagnostic-only).

**But the gate is inert where the symptom lives, and this is MEASURED, not argued.** `gp-0x6806` — the
enable — is **transmitted**: CAN `0x18F` byte4 bit3 = `STEER_CONTROL_ACTIVE`. Route 24, 18,000 frames,
180 s: **`==1` in 96.26%, TWO transitions, max possible toggle 0.1 Hz** against a 20-25 Hz mode.

⇒ **Do not propose either cal as a vibration lever.** `0xC61B8 → 26` remains a legitimate *engage-ramp*
correctness fix (finishing the lockstep scaling) and needs its own justification. Deliberately excluded
from V57. Full detail: `memory/reference-accord-deadband-signgate-eliminated-on-car.md`.

### Untested levers currently on the table
| address | what | status |
|---|---|---|
| **`gp-0x6bbe` angle-rate tributary** (`FUN_00034a72`, reads `gp-0x6a56` at `0x34AB8`/`0x34E8E`) | the boost lane's **UNFILTERED steering-angle-rate error term**, scaled by two speed-indexed LERPs | ★★ **UNBUILT — and the lever INVERTS.** The mode is **996×** on `STEER_ANGLE_RATE` vs **877×** on torque, and this is that exact variable, unfiltered. First candidate ever outside the torque domain. 🛑🛑 **GATE 2 ANSWERED AGAINST CUTTING IT:** the torque EMA is a *multiplicative amplitude scale*, not an additive branch, and the core term is `rate_error = baseline − angle_rate` (`sub r6,r28` @`0x34e96`) with all-positive downstream multipliers and polarity +1 ⇒ **`gp-0x6bbe` ≈ −(gain)·angle_rate = viscous DAMPING.** **Cutting/muting it would REMOVE damping and likely worsen the grinding — the V56 error one build later.** ⇒ **the direction of interest is RAISING the gain to ADD damping at 22 Hz.** Cleanest single point: **`K1` @`0xD200C` = 43** (Q7; pointer base `0xCA324` = 1 hit image-wide). Others: `clampBound` `0xD2000`=666, speedLERP1 Y `0xD2834+0xE..0x18`, speedLERP2 `0xD20C0+0xC..0x14` — all inside the shared `DAMP_BLOCK` but **not** overlapping V44/V47's bytes (grep-checked). 🛑🛑 **STATUS 2026-07-30: THE SIGN IS UNRESOLVED AND SIMULATION CANNOT SETTLE IT. V58 MEASURES IT INSTEAD.** The reasoning flipped three times in one session — (a) "net damping" off the torque-EMA framing; (b) "unresolved, `baseline` isn't slow"; (c) "damping, `baseline` reads no angle rate"; (d) **unresolved again**, because **`gp-0x6a56` is NOT independently sensed** — `FUN_0003f776` computes it as `clamp(polarity × ((gp-0x6abe × 48 × cal) >> 15), ±12000)`, a scale of MOTOR resolver rate — and `baseline`'s Branch A is **also** `gp-0x6abe`-derived, so the two may partially cancel. The golden model cannot simulate it: `base_driver_assist_lane` is flagged `[SIMPLIFIED]` at exactly this point and the tributary is absent. ⚠ **`K1` may also be moot**: the lane's own ceiling (`0xD20C0`, count=5, X=(0,640,2560,5760,6400), Y=**flat 512**) is a SATURATING clamp at ¼ of the aggregator's ±2048 ZERO-gate, so the gate can never fire — but if the lane pins at ±512 the damping derivative is **zero at the peaks** and the lever becomes the **ceiling**, not `K1`. Full order byte-verified: `term1=(K1×rate_err)>>7` → `×Y3>>10` → clamp ±666 (`0xD2000`) → `×((Y4blend×gp0x6988norm)>>10)>>14` → `×polarity` → clamp ±512 → `gp-0x6bbe`. Two fractional stages sit between the 666 clamp and the ceiling, so raising `K1` is **not** a guaranteed null. **V58's bit6/bit5 answer both questions on-car.** ⚠ speedLERP1 `0xD2834` is the boost curve (count=6, Y=541/639/653/551/439/439), not a monotonic speed rise. 🛑🛑 **STATUS 2026-07-30 AFTER THE V58 DRIVE: the CEILING is ELIMINATED and `K1` is still UNRESOLVED.** bit5 = `gp-0x6bbe == +512` fired in **0 of 35,964 frames** ⇒ the lane never pins, the saturating-clamp failure mode is off the table, **`0xD20C0` is NOT the lever**, and `K1` keeps its headroom. But bit6 was **void by construction** — `gp-0x6bbe` is DC-dominated (crosses zero 0.00–1.10 /s where 22 Hz needs ~44/s), so a sign comparator carries no phase at the mode frequency. **The damping sign question needs a MAGNITUDE probe (thermometer on \|gp-0x6bbe\|), which is V60 — and it only matters once V59 says whether the amplitude path is live.** ⚠ Do not move `K1` on a pooled-run coherence: pooling manufactures a splice artifact |

### Untested levers ADDED 2026-07-30 — the boost-amplitude modulation path
| address | what | status |
|---|---|---|
| **`0xD28DC`** (LERP1, via ptr table `0xca4f4`) and **`0xD2888`** (LERP4, via `0xca23c`) | the two boost **amplitude** curves, both indexed by `gp-0x6ba6`. `0xD28DC`: count=6, X=(0,512,1490,2529,3645,5120), Y=(16384,14657,11672,9365,8244,8187). `0xD2888`: X=(0,307,1024,1741,3072,6144), Y=(16384,14392,10265,8997,8176,8176) | ★★ **UNBUILT, and GATED ON V59.** `gp-0x6ba6 == \|gp-0x6b9a\|` (byte-verified, `subr r0,r13` @`0x3b87a`), and V58 measured the signed sibling crossing zero at 20.93 Hz **only when LKAS applies** (13.69 vs 0.61 toggles/s at matched creep) ⇒ the index is that signal **rectified**, sweeping these curves at **~2× the mode frequency** across a 2:1 range. Flattening the Y rows removes the modulation. 🛑 **But DEPTH is unmeasured** — the delivered swing is set by how far up the curve the index climbs: `<512 ⇒ ≤1.12×`, `1024 ⇒ 1.27×`, `2048 ⇒ 1.58×`, `2529 ⇒ 1.75×`, `≥5120 ⇒ 2.00×`. ⚠ **Not "inert" below 512** — the LERP interpolates from X = 0, so it is pinned at 16384 only at exactly zero; a 12% modulation is weak but real. **V59 measures the regime. Do not build against these until it has flown.** 🛑 GATE 2 outstanding: both sit on the **BASE ASSIST** path, so they change manual feel, not just the LKAS lane. ⚠ `0xD28DC` is reachable ONLY from `0xca4f4` — `build_v58_tva.py` said `0xca23c` and was wrong |
| **`tp+0x73ba`** = `0xC63BA` = 512 | the cascaded-EMA alpha in `FUN_0003b66a` (two poles, α = 512/1024 = 0.5 at 1 kHz ⇒ corner ≈120 Hz for the pair, i.e. **wide open at 21 Hz**) | ★ **UNBUILT — the UPSTREAM candidate.** This is the filter that lets `gp-0x6b9a` carry 21 Hz in the first place; attenuate here and nothing downstream has anything to modulate with. Real filter authority, unlike the two identity FIR triples. 🛑 GATE 2 outstanding and non-trivial: it is on the base assist path and adds phase lag to assist. Gate on V59 |
| ~~`FUN_0003b66a` branch-A "biquad"~~ | `tp+0x5018/501c/5020` = `0xC4018/1C/20` | 🛑 **NOT A NOTCH LEVER — same closure as the FIR row above.** A 2026-07-30 trace claimed "a genuine floating-point 2-pole biquad, IIR by definition". **It is not.** The coefficients read **(1.0, 0.0, 0.0)** and the code is `y = b0·x[n] + b1·x[n−1] + b2·x[n−2]` with two *input* delay states — a delay line, **not feedback**. Stateful ≠ recursive. It is the identity 3-tap FIR already on record. Also: `tp+0x74be = 0` makes `0x3b736–0x3b758` dead code |
| ~~`0xC6AFC` + `0xC6AFE`~~ | moved to the flashed table above — **V56, falsified and harmful 2026-07-29** | 🛑 **DONE. Do not re-propose, at any authority value.** The GATE-2 "damping sign OPEN" caveat resolved *against* the mute on-car |
| ~~`0xC6372` / `0xC636E`~~ | boost-assist + damping lane input EMAs | 🛑 **RETIRED 2026-07-30 — DEAD BRANCH.** `tp+0x7498 = tp+0x7499 = 1` routes both consumers past it. Zero effect on this firmware. See the main table |
| ~~`0x2a1ee` retarget → `0xC6CD0`~~ | decouple 4× forward from the feedback readers | ✅ **BUILT AS V57, 2026-07-29 — moved to the flashed-candidates list below.** Still UNFLASHED |

### 🛑 The `0xC646C` readers are ELIMINATED — the elimination STANDS, on its structural leg

⚠ **Correction of a correction, 2026-07-29.** An earlier pass this session downgraded this elimination to
"not yet tested" on the grounds that the flat-transfer measurement came through a ~1-bit probe. **That
downgrade was wrong and is withdrawn.** Two things were established:

1. **Quantisation is EXONERATED, by construction.** Ground-truth lanes of known shape pushed through the
   exact encoder `clamp((x>>9)+8,1,15)`, Monte Carlo K=30 × 60 trials: the encoder reproduces H1's
   **shape** to within a few percent, including a true 0.93 Hz pole (true H1 ratio @21/@1 = 0.069,
   measured 0.071 ± 0.022). A memoryless nonlinearity applies one describing-function gain at every
   frequency — **it cannot flatten a pole.** H1 bias is −6%/−8% and shape-preserving; **coherence bias is
   DOWNWARD** (0.963-0.976 measured for a true 1.000), so the recorded 0.93 is a **lower bound**.
2. **But the transfer argument is still weak — for a different reason.** With K=3 and ±19.6% error bars,
   a single pole at fc=16.8 Hz (rel-sse 0.215) and flat (0.245) are **statistically indistinguishable**.
   ⇒ "the transfer is flat 1→21 Hz" is **UNCONFIRMED**, not refuted, and the rise 0.192→0.216 is **not
   significant** at ±20%.

⇒ **Rest the elimination on the STRUCTURAL kill, which is a byte fact and untouched by any of this:
`0xC646C` has 0 matches across all 468 instructions of `FUN_0003a382`**, so the carrier cannot read it.
The transfer argument is **corroborating only**. **No candidate cause returns to scope.**

#### The 2026-07-28 arithmetic, retained — still correct *given* a measured 0.221
```python
# FUN_00036682 (readers #5/#6) -- and it is not even a plain EMA: y[n-1] is subtracted twice,
# giving y[n] = y[n-1]*(1-2a) + a*K*x[n], so DC gain is K/2, not K.
alpha = u16le(img, 0xC63D2)        # == 6, NOT 14 -- byte-verified 3 ways, stock and V55 identical
fc    = (6/1024) / (2*pi*1e-3)     # 0.933 Hz
att21 = 1/sqrt(1 + (21/fc)**2)     # 0.0444  = -27.1 dB
(3564/32768) * att21               # 0.0048  contribution at 21 Hz
# MEASURED total sensor->command transfer at 21 Hz = 0.221  =>  reader #5 is 2.2% of it.
# Reverting the gain to stock removes 1.6% of loop gain = 0.14 dB.
```
And the measured transfer is **flat from 1 Hz to 21 Hz** — a lane behind a 0.93 Hz pole cannot do that.

### 🛑 `0xD_xxx`-region LERPs are VARIANT-CODED — resolve the pointer before editing
The damper factor tables (and the output clamp) are reached through **three** stages, and the selector is
an **EEPROM** value absent from every flash dump:

```
5-byte coded ID -> FUN_00057f8e() match vs 16 ASCII PN keys @0xCD000 (stride 0x24) -> ROW  (0-15)
                -> index byte @0xCD012 + ROW*0x24                                   -> INDEX (0-57)
                -> ptr_array[INDEX]                                                 -> the live table
```

**ROW is NOT INDEX.** Conflating them inverts the answer — it happened this session and nearly resurrected
a correctly-falsified hypothesis. Our car: `TVAA1` → row 2 → **INDEX 10**. Arrays: Factor B `0xC9CCC`,
D `0xC9DB4`, C `0xC9E9C`, E `0xC9F84`, clamp ptr `0xC77A0` — 58 entries each, one shared selector at
`gp+0x63fd` (**positive** gp offset). Assume any `0xD_xxx` LERP is variant-coded until proven otherwise.

### 🛑 New-mailbox CAN TX is an UNOBSERVABLE channel — do not build another one
`FOURFRAME` (STRB defect) and `FOURFRAME2`/`V53` (defect fixed) both produced **zero** frames of
`0x6A0`-`0x6A3` at the comma. The V53 null is **uninterpretable**, not negative: six IDs the stock
firmware genuinely broadcasts (`0x19F`, `0x32E`, `0x64D`, `0x660`, `0x722`, `0x723`) are equally absent
from the same rlog while the three openpilot's DBC knows (`0x14A`, `0x18F`, `0x1AB`) run at 97-100 Hz.
Non-DBC IDs *are* logged (`0x669`, `0x750`, `0x674` appear and are in no Honda DBC), so "openpilot didn't
know the ID" is excluded. **Any future firmware telemetry must ride the `0x14A` byte4 bits 7:3 piggyback**
(4 successful flashes, hook at `0x55C0E` before the checksum) until a tap upstream of the gateway exists.

---

## Part 2 — Code caves are the only bricking class

**Three of this kit's code caves bricked the ECU: V24, V27, V48B.** Every success since V29 has been
cal-only or a single in-place branch/displacement edit.

- **V27** — bricked from **ASYMMETRY**, not magnitude (float twin doubled wholesale vs int corridor-only).
- **V48B** — bricked from (a) RAM collision: biquad state `gp-0x14FA` aliased a live monitor status byte,
  and (b) an unmodelled lightly-damped resonator inserted into the always-on base-assist loop.
- **V40** — not a cave, but the same lesson: the defect was the **magnitude** of a cal write, not its
  direction.

⇒ **TWO MANDATORY GATES for any cave / filter / dynamics change** (apply without being asked):
- **GATE 1 — RAM OWNERSHIP.** Every byte of the full multi-byte footprint proven free *including writers*
  and register-indirect / 6-byte-extended-displacement accesses. `gp-0x1401..0x1502` is poison (it is a
  subset of the `0xb7260` I/O-mailbox array). **Static clearance is not sufficient — `gp-0x1500` passed
  both static methods and still failed on-car.** A live probe is the only reliable RAM-ownership test.
- **GATE 2 — CLOSED-LOOP STABILITY.** Magnitude *and* phase of **every loop the touched signal is in**,
  especially the always-on base-assist loop. Never a single-frequency magnitude.

**A 2-byte in-place displacement or branch-condition edit is a different, far lower risk class than a
trampoline + cave.** Do not conflate them.

---

## Part 3 — Machine-generated per-build delta (vs stock `code.bin`, app region only)

Regenerate with a byte diff restricted to `[0x13000, 0x100000)`.
⚠ **A whole-file diff is meaningless** — `build_*.full_image()` writes `0xFF` filler below `0x13000` and a
naive diff reports 51,137 bogus bytes.

`0x13109` and `0x14120` appear in every build: they are the version-string bytes (`-`→`,`, giving
`39990-TVA,A160`). **Every modified build shares that string, so an rlog cannot identify which build is
flashed.**

| build | bytes | code edits (beyond version string) |
|---|---|---|
| v29–v33, v36, v37 | 27–42 | none — cal-only |
| v38 | 126 | none — cal-only (first to touch `0xE4000`/`0xE5000` bootloader blocks) |
| v39 | 174 | `0x3AC78` + cave `0xC4B34-C4B5F` |
| v40 / v41 | 162 | none — cal-only (`0xC5030`, `0xC521A`, `0xC5232`, `0xC6206/08`) |
| v42 | 153 | **`0x454FE`** (the ratchet fix) |
| v43–v48a | 129–145 | `0x454FE` only |
| v48b | 282 | `0x2C482`, `0x354D4`, `0x35AA6`, `0x3A6CC`, … + cave — ☠ **BRICKED** |
| v49 | 130 | `0x3A836`, `0x454FE` |
| v50 / v52 / v52c | 226–254 | multi-site repoints + cave `0xC4B34` |
| v49p / v50probe / v51probe | 183–216 | `0x55C0E` hook + cave (read-only probes) |
| vcantxtest | 340 | `0x55C0E` hook + cave — ⚠ carries the **STRB=0x80 defect** |
| vfourframe | 853 | `0x55C0E` hook + cave — ⚠ **STRB=0x80 defect, never transmitted** |
| **vfourframe2** | 853 | same, **STRB fixed to 0x01**, authority + reference-model signals |
| **v53** | 855 | FOURFRAME2 byte-for-byte **+ `0xC62EA` 320→0** (+ CAL CRC). Exactly 6 bytes off FOURFRAME2 |
| **v54** | 58 | `0x55C0E` hook + **44-byte** cave `0xC4B34` (5-bit `gp-0x6966` authority probe → `0x14A` byte4 bits 7:3) + `0xC62EA` 320→0. **No mailbox cave** |
| **v55** | 82 | `0x55C0E` hook + **68-byte** cave `0xC4B34` (dual probe: damper variant bit + 4-bit `gp-0x6b98`) + `0xC62EA` 320→0 |
| **v56** | 84 | V55 byte-for-byte **+ `0xC6AFC`/`0xC6AFE` 32768→0** (+ CAL CRC). Exactly **6 bytes** off V55 — and only **2** are cal, because `32768` = `00 80` LE so just the high byte of each halfword moves |

---

## Part 4 — Flash status at a glance

**Flashed and currently the on-car baseline lineage:** V38 (fault-free) → V42 (ratchet fixed) → V43, V44,
V45, V46, V47, V48A (all null) → V48B (☠ bricked, recovered by reflash) → V52C (null for vibration,
changed manual feel) → FOURFRAME (telemetry, silent — STRB defect) → V53 (2026-07-27: steer-to-zero
✅ CONFIRMED; four-frame telemetry absent and the null uninterpretable — see the box in Part 1) →
**V54** (2026-07-27: ★ **the probe FIRED** — first working firmware telemetry channel in this kit;
`0xC6AF0` direction measured and the block lifted; fault-free).

→ **V55** (2026-07-28: the dual probe FIRED and partitioned the hypothesis space — ★★ **the ~21 Hz IS in
`gp-0x6b98` and the loop is INTERNAL to the EPS**; openpilot is 8.7× too small even with the LKAS
low-pass deleted, and while RAILED its 21 Hz is exactly 0 yet the command still carries 105.8 counts;
sensor→command transfer is **flat 0.19→0.22 from 1 Hz to 21 Hz**; damper bit7 = 1 ⇒ V44/V47 hit the LIVE
tables). Fault-free.

**⚠ V55 is the image on the car now.** It does **not** carry the V42 ratchet fix (`0x454FE` is stock
`0x65BA`), same as V38/V53/V54/FOURFRAME.

★ **V54's telemetry result — the `0x14A` byte4 bits 7:3 piggyback is PROVEN end to end.** A/B against the
V53 drive is a single bit and it is exactly ours: byte4 = `0x07` ×5,994 (100%) on V53 → `0x0F` ×5,989
(100%) on V54, stock `STEER_SENSOR_STATUS` bits 2:0 preserved, `canValid` true in 5,711/5,713. **Use this
channel for all future firmware telemetry.**

→ **V56** (falsified, reverted) → **V57** (decouple + deadband probe, fault-free) → **V58** (angle-rate/
boost-lane probe, fault-free, 14 segments) → **V59** (2026-07-30, route `2c`: ★★ **the boost-index DEPTH
probe FIRED and answered** — 50,963 frames, 100% live, 100% thermometer-monotonic, fault sentinel 0.000%,
`ST==4` 0/50,963, FLIGHT-CLEAN. The 42.19 Hz pump = **2× the 21.09 Hz mode**, engagement-gated, **absent
disengaged** (bit5 never toggles in 61.2 s) — but **MARGINAL**: eps 0.013–0.169 across every combination
of task rate × series question, against a threshold that cannot be pinned because the passive Q is not
measurable (no ring-down exists: 66 candidates, longest **0.63 cycles**)).

★★ **The turn this drive produced — the OPERATOR's hypothesis, now the leading explanation.** The torque
sensor sits between wheel and road, so LKAS motor torque twists the column and is **read back as driver
input**, then boosted. A positive feedback loop, and **traced: there is NO motor-command feedforward
compensation anywhere in the chain** (`gp-0x6b98` appears only as a sign input to the `gp-0x6ac2`
ceiling detector, and in `FUN_00043e44` whose output has **zero readers**). Measured: the
**command→torsion-bar transfer function peaks at 21.09 Hz — the GLOBAL max over 3–46 Hz** — 15.6×
baseline hands-off (K=5, coh 0.654 vs null 0.527), 25.7× any-hands (K=53). ⇒ **the pump is probably a
passenger; the loop is the driver.**
🛑🛑 **CORRECTION OF RECORD, 2026-07-31 — V52C DID NOT "HALVE THE MODE". THERE WAS NEVER A NUMBER.**
This paragraph used to cite V52C as the loop hypothesis's best supporting evidence. **Struck.**
`−6.1 dB at 21 Hz` and `halved the mode` are **the same statement**: V52C's EMA (α = 74/1024, 1 kHz)
has `|H(20.9 Hz)| = 0.4963`. It is **the filter's designed attenuation, not a measurement.** The phrase
was authored in `HANDOFF-2026-07-28-v55-...md:205` as a **caveat on why V52C's NULL was weak evidence**
and mutated into a positive result two handoffs later. Every contemporaneous record — including the
operator's own words in `HANDOFF-2026-07-26-route13-...md:8` (*"V52C did not fix the vibration; it
clearly changed manual feel"*) — says **NULL**. **No V52C rlog exists** (routes on disk are
`13,1a,1b,1c,24,28,29,2b,2c`; the V52C window `08`–`12` is absent machine-wide and was never in git),
so the "re-derive it first" instruction was unexecutable. ⇒ The loop hypothesis rests **only** on the
21.09 Hz transfer peak and the traced absence of feedforward. ⚠ Not a falsification of the loop — a
2× gain cut carrying +57–61° of lag is a poor stabiliser — but it **is** weak-to-moderate evidence
against the `gp-0x4f60` **VALUE** path specifically.

### 2026-07-31 — V60 FLASHED → NULL, and V61 built

🛑 **V60 (`0xD2006` 102→43) FLASHED and driven 2026-07-31 → NULL on the vibration.** Operator: *"It did
not fix the vibration issue."* No rlogs (V60 carries V59's probe unchanged, so there was no new
telemetry). **This is a result, not a wasted drive** — V60 was built as a **discriminator** and the
record predicted the null in advance. Pump causality was not settleable observationally (the index is
`|x|` of a bar-derived signal, so 2f coupling is arithmetically forced) and `eps_crit = 2/Q` needed a
passive Q that V59 could not measure. ⇒ **the V58/V59/V60 parametric-pump arc is CLOSED.**
★ **It also closes `0xC63BA`** — byte-scanned, the readers of `gp-0x6b9a`/`gp-0x6ba6` are confined to
`FUN_00034350` (damping), `FUN_00034a72` (boost), their producer and V59's probe, so that cal's only
effect is on the same amplitude LERPs V60 just falsified. **Do not propose it as a grinding fix.**
⚠ Two more lanes eliminated, byte-verified: `FUN_00036c12` (`gp-0x6b26`) and `FUN_00036388`
(`gp-0x6b62`, the return-centre lane) read **no torque signal at all** — speed/motor-rate keyed only.

★★ **A structural finding that reframes every damper null: RTOS task 5 runs at 100 Hz.** The rate
divider `FUN_00014be4` is mod-100 on the base tick; boost `FUN_00034a72` and damping `FUN_00034350`
fire once per 10 task-1 invocations (integer arithmetic — clock-independent). ⇒ a ZOH costs
**37.6° average / 75.2° worst-case** transport lag at 20.9 Hz before any plant phase, so the
velocity-proportional damper **structurally cannot damp this mode** and may be anti-damping there.
**That is a second, independent reason V44/V47 were null**, alongside the FactorC speed-axis argument.
⚠ A datasheet audit then refuted the kit's clock chain — **PCLK is 40 MHz, not 80, and OSTM0 is NOT the
RTOS tick** (no arm in the EI trampoline `FUN_0001492a`; the divider's trigger `gp-0x42fc` is written
only by `EIIC 0x340` = TAUJ1I2). The 1 kHz/100 Hz figures **survive on ON-CAR measurement**, which never
used that chain. But **the FOC/TSG20 "~8 kHz" carrier likely halves to ~4 kHz** — treat as OPEN.

| lever | what | build | flashed | result |
|---|---|---|---|---|
| `0x3AB6C` `mul r1,r6,r0`→`mul r0,r6,r0` + `0x3AC16` `mov r1,r8`→`mov r0,r8` | ★★ **kill the torsion-bar RATE lane at BOTH taps of its shared value** `r1 = clamp(gp-0x4f62, ±5120)` | **V61** | ✅ **BUILT, UNFLASHED** | **The one decisive subtractive test never performed.** r24 and r26 are **not independent** — both are gain-scalings of ONE value, same sign, shared polarity load @`0x3AB78`. **V39 killed only r24 and only *conditionally*** (cave @`0x3AC78`, bypasses unless driver max torque < 320 AND \|LKAS\| ≥ 417); **V42 killed only r26** and says so outright. **Byte-checked every flashed image: NO build ever had both dead** ⇒ each recorded null was uninformative about the lane. Two single-**BIT** `reg1` r1→r0 changes, opcode/reg2 byte-identical, **no cave** ⇒ GATE 1 vacuous. 5 bytes off V59; CAL CRC and `0xD2000`-block CRC both unchanged. ⚠ Expect a manual-feel change (phase-lead term in **base** assist, no LKAS-only decoupling point); reversible via V59 |

🛑 **A CORRECTION THAT MATTERS FOR THE FACTOR-C/E RECORD.** V44 raised FactorC alone → null. **V47
raised FactorC AND FactorE together** — byte-verified 2026-07-31 across the images (`v47` has FactorC
`Y[0]` = 235 *and* FactorE = (700,750,800), vs stock 0 and (0,140,539)). **So the multiplicative-chain
concern WAS handled: the simultaneous test exists, was flashed, and gave "marginally quieter at 5 mph,
no effect in motion."** V61 is the *additive dual* of that same trap, and unlike C/E its simultaneous
test has genuinely never been run.

**Built and UNFLASHED:** ★★ **V61** (above), plus ~~V60~~ (now flashed, null — do not re-flash;
null), plus **V55** (dual probe: damper variant bit + 4-bit `gp-0x6b98`
motor command, 82 bytes off V38), plus V49, V50, V51P, V52, VCANTX-TEST, FOURFRAME2. V53 and V54 are both
now flashed and no longer candidates.

★ **V55 is a PARTITION, not a lever.** Every falsified vibration lever in Part 1 — V39, V41, V42 ch.2,
V43, V45, V46, V48A, V52C — sits on the **command path** and assumes the ~20 Hz is *commanded*. V55
samples `gp-0x6b98`, the final merged command and the only path to FOC, to test that assumption directly:
if the mode is absent there, all eight were doomed by construction and the search moves to the plant.
A null BOUNDS the command's 20 Hz content to ~<512 counts (one level) against the sensor's ~550 rms; it
does not prove zero, and a 100 Hz probe still cannot separate 20 Hz from 80 Hz.

🛑 **Flash only on explicit operator instruction naming the file and the bus.**
