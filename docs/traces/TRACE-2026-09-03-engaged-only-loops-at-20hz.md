# Census of engaged-gated loops and gains at ~20 Hz — for the creep "grind #1" symptom

2026-09-03, subagent `fwloops20` (firmware-codepath-tracer), for `team-lead`. Symptom under study:
`rlog-tools/studies/osc-highangle/HIGHANGLE-r34-2026-09-03.md` §8-9 — a 18-22 Hz line on the torsion
bar, wheel rate and delivered LKAS-lane torque (`gp-0x6b38` tap), coherent (1.00/0.98), engaged-only,
3-6 mph, hands-light, no clamp active, ~4x stock, unchanged V278/V280/StarPilot tunes.

**Method**: built on this kit's large existing address-verified record (cited throughout,
`.claude/agent-memory/firmware-codepath-tracer/*.md`), corroborated this session by a **fresh Python
LE byte read of the actual flown image**,
`../accord-firmwares/analysis-2020accord/_v280_V280R2-V268BASE-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin`,
against `stock_fw_dump/code.bin`, for every cal cell this census depends on — not relayed from memory
without a current check. Structural/topology claims (function bodies, xref counts, gate conditions)
are inherited from prior sessions' address-level traces and cited by memory file name; none of that
structure differs between stock and V280 (only cal bytes do), so a fresh full re-decompile of each
function was not repeated here. GhidraMCP was not separately invoked this session — every claim below
already carries an instruction-level citation from a prior GhidraMCP trace, and the delta-vs-stock
numbers are a direct file byte read (Python), which is the kit's own prescribed second method for
byte-level facts. EVIDENCE unless marked BELIEF.

`gp = 0xFEDF8000`, `tp = 0xBF000`. All addresses below are as found in the cited memory files.

---

## 1. THE ENGAGED SWITCH — every table/gain/clamp gated by engagement

The kit's engagement state lives in two flags that this census found gating every engaged-only
mechanism below:

| cell | identity | source |
|---|---|---|
| `gp-0x6806` | **STEER_CONTROL_ACTIVE** — the live LKAS-engaged flag, 16 writers / 13 readers in `FUN_00028ea6`+`FUN_0002a30e` | [[reference_accord_v36_gentle_eme_debounce_full_mechanism]], [[reference_accord_gp6807_gates_gp69b0_engagement_ramp]] |
| `gp-0x69b0` | **engagement-ramp Q15 multiplier** (0→32768), the ramp that scales the LKAS PID's own output; ALSO gated (advance blocked) by a `STEER_STATUS` dispatcher tail-appended to `FUN_0002a30e` that Ghidra mis-bounds and neither `get_function_by_address` nor `search_instructions` sees | [[reference_accord_gp6807_gates_gp69b0_engagement_ramp]], [[reference_accord_fun28ea6_ramp_statemachine_gp6806_gp69b0_decoded]] |
| `gp-0x674e` | **static, UDS-coded variant index**, NOT a runtime engagement signal — `byte(0xCD012+0x24*hwid+8)`, measured live = **7** (record `TVCA4`); indexes 11 per-variant table banks (map, Kp, Kd, both driver-override tapers) simultaneously | top-index [[accord-the-live-variant-selector-is-7-tvca4-measured-on-the-wire]], [[accord-one-selector-indexes-all-five-banks]] |
| `gp+0x63fd` | mode/HW-ID failover selector, **closed as confined to states 10/11**, NOT a runtime engagement flag either — do not conflate with `gp-0x674e` | [[reference_accord_mode_selector_gp63fd_hwid_failover_not_engagement_flag]], [[reference_accord_mode_selector_fun42746_closed_confined_to_10_11]] |

**Consumers gated ON engagement (`gp-0x6806 != 0`), byte-verified V280 vs stock this session:**

| lane | engaged-gate mechanism | stock value | **V280 value** | effect |
|---|---|---|---|---|
| **Rate lane r24** (`FUN_0003aa2c` @`0x3aa96`) | gate opcode byte at `0x3AA96`; when `0xFB`, engaged (`gp-0x6806!=0`) selects the **FLAT** cal `0xC6446` and discards the speed/rate LERP entirely | gate `0xC5`(off) / `0xC6446`=**512** | **gate `0xFB`(on)** / `0xC6446`=**5244** — a **10.24x raise, engaged-only** | [[reference_accord_rate_lane_v62_to_v69_gain_arc]] §8 |
| **Honda's 55 Hz biquad** (`FUN_000352b4`, notch) | V103's 3-instruction repoint at `0x35A06/12/18` swapped the dead `gp-0x671a<5` gate for **`gp-0x6806 != 0`**; arm byte `0xC649B` | repoint bytes `844fe798a77a`/`ec49`/`e937`; arm=**0** (Honda's own gate is FALSE on this car — never fires stock) | repoint bytes `844ffb97a77a`/`e049`/`ea37` (**present**); arm=**1** | notch goes from permanently dormant to **live, engaged-only** |
| **LKAS rate PID itself** (`FUN_00028ea6`) | the whole cascade's output is gated by `gp-0x6807` (debounce/latch → `STEER_STATUS`), the driver-override Y taper, and finally `* gp-0x69b0 >> 15` (the engagement ramp) at `0x2a1e6` | debounce cals `0xC64B4..B8`=112/96/54/64/112, `0xC61C0/2/4`=1600/896/1280 (satisfiable) | debounce cals **255/255/255/255/255**, `0xC61C0/2/4`=**0xFFFF/0xFFFF/0xFFFF** (all unsatisfiable → the debounce mechanism is DISARMED, the multiplicative Y taper is the sole surviving override) | [[reference_accord_fun28ea6_lkas_rate_pid_full_decode]] |
| **LKAS forward gain / clamp** (`FUN_00028ea6` @`0x2a1ee`) | private cal `tp+0x7CD0`=`0xC6CD0`, sole reader is the arbitration function; feeds `gp-0x6b38`→`gp-0x6b3c`, gated `* enable_flag` at the same site | `0xC6CD0`=**0xFFFF** (unwritten on virgin stock — the repointed slot did not exist pre-V57), `0xC61B4/0xC61B2` clamp=**512** | `0xC6CD0`=**5346** (= 6.00x of `0xC646C`'s 891), `0xC61B4/0xC61B2`=**3072** (6x, tracks 1:1) | [[reference_accord_0xc6cd0_exogenous_via_masons_formula_but_wired_into_path2_stage1_sign_open]], top-index [[accord-the-8x-gain-is-the-carrier]] |
| **crossover threshold `0xC62E6`** | (`E<0` requires `feedback_lag_out > K*setpoint`) | 7680 | **46080** (K=6, matches the filename's `FEEDBACK46080`) | [[reference_accord_v276_crossover_threshold_and_packer_rectifies_sign]] |
| **Pole `0xC40DC`** (α2, `gp-0x6c2c` friction/inertia EMA-A) | not itself engagement-gated, but sits inside the Path-1/Path-2-reinforcing inertia lane | 22 | **14** (α2 band-limit) — this is **V109's documented lever**, `docs/BUILD-LINEAGE.md:277,284`, correctly carried forward — NOT a new/undocumented edit | [[reference_accord_gp6b26_two_paths_reinforce_and_pole_fork_dead]] flagged this cal "virgin on all 102 images" as of 2026-08-22; `BUILD-LINEAGE.md` (checked this session) shows it was already moved by V109/V122-138, so that "virgin" note is stale for the current build — flag for whoever owns that memory file |

`0xC646C` (the shared 4x sensor-to-command Q15 scale, 6 static readers spanning arbitration + 3
feedback/diagnostic sites) is **unchanged**, 891 stock = 891 V280 — it did not move; the V57+ arb-only
repoint to the private `0xC6CD0` cell (above) is what's carrying the authority increase now, not this
shared cell. `0xC63E6` (LKAS PID's Ki) is **0 on both** — the integrator remains inert. `0xC61BE`
(post-gain PID-sum clamp, the cell identified as starving D per the V276 finding) is **15360 on both** —
**unchanged by V280**, i.e. the D-starvation mechanism from the V276 census is still present today.

---

## 2. THE LOOPS AROUND THE MOTOR

| # | loop | sample rate | engaged-gated? | gain/phase near 20 Hz | flown-edited on V280? |
|---|---|---|---|---|---|
| (a) | **LKAS rate PID** `FUN_00028ea6` — setpoint = CAN-0xE4 mapped via variant table, feedback = a **two-sample-summed** first-order lag of `gp-0x6a56` (column rate) | **1 kHz** (task 0, unconditional every tick) — [[reference_accord_task5_100hz_live_verified_full_producer_census]] | YES — gated by `gp-0x6807`/Y-taper AND `*gp-0x69b0>>15` | Feedback path: `y[n]+y[n-1]` where `y` is EMA(a=923/1024,b=1560/1024). DC gain **30.9** (per top-index memory); at **20 Hz computed this session**: `|H|≈19.7` (64% of DC), phase **≈-50°**. D term (`(32·err − prior)·Kp_D>>3`, Kp_D 205–696 by driver-override index) is a raw per-tick difference — gain rises with f (no filtering at all on the error signal itself). | Ki=0 both, unchanged. Debounce/cutout cals disarmed on V280 (table above) — engaged authority is now gated *only* by the Y taper. `0xC61BE` sum clamp unchanged at 15360 (still the D-starving constraint per the V276 finding). |
| (b) | **Base-assist rate lane r24/r26** (`FUN_0003aa2c` inline; gain tables refreshed by `FUN_0003ad74`) — `dtorque` = a **4-tap backward difference, N=4** (`FUN_0007e74a`), an unfiltered near-ideal differentiator | dtorque: **1 kHz** (inline in the 1kHz aggregator); gain-table refresh: **100 Hz** (task 5, [[reference_accord_task5_100hz_live_verified_full_producer_census]]) | **YES, r24** — flat engaged gain `0xC6446` (table §1); manual uses a speed-shaped LERP instead. r26 uses the same `dtorque`, its 2-tap boxcar averages only the *gain schedule*, not the signal (|H(20.9Hz)|=0.9978, functionally unity) | `|H_diff(f)|` scales ~linearly with f for an ideal differencer: computed ratio `\|H(18.5Hz)\|/\|H(1.5Hz)\|=12.33x` (memory, N=4 window) — **the differentiator itself AMPLIFIES 20 Hz content ~12x relative to 1.5 Hz**, before the engaged gain is even applied. r24 has **zero state cells / no filter anywhere** on its own path (exhaustively confirmed) — nothing between the raw difference and the aggregator sum attenuates 20 Hz. | **YES — `0xC6446` 512→5244, a 10.24x raise, engaged-only, present on V280 (byte-confirmed this session).** |
| (c) | **Inertia term `gp-0x6b26`** (`FUN_00036c12` + Path-2 through `FUN_00038148`/`FUN_0003a382`) — 4 negations, net POSITIVE, immune to `gp-0x6752` | **1 kHz** | Path-2 passes through the PID's own engagement gating indirectly (via `gp-0x6ad4`→aggregator); not a separate gate | Two EMA poles: α1=37/128 (`0xC643C`, unchanged), α2=22/64→**14/64** (`0xC40DC`, V109 lever, present on V280). Prior sweep: the differencer alone gives **+86.09° at 21.73 Hz**; the two poles currently subtract only **−32.44°** net (`phase(H)=+53.64°` at 21.7Hz) — **this lane still delivers substantial ADDED INERTIA, not damping, at ~21-22 Hz**, per the closed pole-fork analysis. | α2 lever is V109's, carried forward — not new to V280. |
| (d) | **Viscous/DC term `gp-0x6bbe`** (`FUN_00034a72`, "boost") — dominant signal is an **UNFILTERED angle-rate error** (`baseline − gp-0x6a56`), no EMA/IIR on the phase-carrying signal at all | **100 Hz** (task 5) | Not directly engagement-gated (runs always); its `gp-0x682e` baseline has its own override gate reading torque-domain cells | Net **DAMPING** on angle rate (opposes it) — `rate_error = baseline − raw`, all downstream gains non-negative, polarity +1. At 100 Hz sampling a 20 Hz signal is only 5 samples/cycle — **aliasing risk not evaluated this session**, flagged open. | `K1` (`0xD200C`=43), `clampBound` (`0xD2000`=666), speedLERP1/2 Y-values — not checked against V280 this session; recommend a byte diff (all 4 are un-cited in any `build_v*_tva.py` per the source memory, i.e. **historically never touched** — worth a fresh V280 diff to confirm still true). |
| (e) | **Carrier gain `0xC6CD0`** (LKAS forward gain, `FUN_00028ea6` sole reader) | 1 kHz (arbitration) | YES, output gated `*enable_flag` | **Structurally EXOGENOUS by Mason's-gain-formula** — the ~1874-instruction `search_instructions` null on `gp-0x6b98` inside `FUN_00028ea6` (re-confirmed, both sessions independently) means this gain cannot move the poles of a *fixed-operating-point linearization*. **BUT** its output `gp-0x6b4c` is a unity-weighted term feeding BOTH the aggregator AND Path-2's own error-forming Stage-1 composite — so it sets the **operating point** of a real gain-scheduled nonlinearity (Stage-2's "f′" LERP, which varies >10x across its range). This is a describing-function mechanism, not a linear pole-mover. Prior on-car measurement: **raising this cal from 4x→8x MOVED a resonance pole from 20.3 Hz to 23.0 Hz** and produced vibration scaling `m^1.74` against authority `m^0.88` — the strongest single measured mechanism this kit has for a self-sustained line near 20-23 Hz, though that evidence is from the ~22-26 Hz "carrier" band at speed, not confirmed at 3-6 mph creep specifically. | **YES — 891(equiv, unwritten)→5346 (6.00x of `0xC646C`), engaged-only, present on V280.** `0xC61B4/B2` clamp raised in lockstep (512→3072). |
| (f) | **Biquad/notch** `FUN_000352b4` — Honda's own coefficients (`0xC60A8/AC/B0/B4`, **byte-identical stock=V280**, pole \|r\|=0.7966@42.345Hz, zero \|r\|=1.0@55.225Hz) | 1 kHz | **YES, confirmed dormant-on-stock, live-on-V280 this session (byte read).** Honda's own arm condition (`gp-0x671a<5`) is **measured FALSE on this car** ([[accord-honda-biquad-arm-gate-is-false-on-this-car]]) — stock never fires it. V103's repoint substitutes `gp-0x6806!=0` (engaged) for the dead condition. | As-flown (Honda's coefficients): **20 Hz: −1.12 dB / −28.5° phase.** Not a strong resonance generator by itself at 20 Hz specifically (its zero sits at 55 Hz) — but it now contributes real, engaged-only phase lag inside whatever loop reads its output, previously absent on every stock/pre-V103 build. | **YES — arm byte 0→1, gate repoint present, engaged-only, live on V280 (byte-confirmed this session, first time this census has checked it against the current flown image).** |
| (g) | **Relay/coulomb (dwell relay, `FUN_00036388`, return-centre end-stop cushion)** | 1 kHz | Not engagement-gated in the classic sense — it's a rate-of-change dwell/snap counter on `gp-0x6b64`, arms on **LARGE** \|value\| > `0xC618A`=1024 (corrected polarity, [[reference_accord_dwell_relay_polarity_is_arm_on_LARGE_correcting_the_kit_record]]) | `0xC618A` unchanged 1024 stock=V280. Gate `Y1(gp-0x6bda)` (the peak-hold-margin arm) is 0 in the documented hands-off case → `gp-0x6b64≡0` → snap counter never arms → **contributes exactly zero** in the operator's steady hands-light creep condition per the corrected polarity. | This lane is **NOT** the "relay/coulomb knee" the census asked about — that is a different mechanism (`0xC40BC`, see [[reference_accord_c40bc_is_a_rate_knee_not_a_relay_hardness]], "a rate knee not a relay hardness" — i.e. NOT a coulomb relay at all, a prior name for this was corrected). No dwell-relay lever appears on the flown-edit ledger. |
| (h) | **FOC current loop + PWM** | Current loop / ADC ISR: **4.000 kHz** (corrected from an earlier ~8kHz belief — PCLK=40MHz not 80MHz). PWM carrier: **4.000 kHz** (`TS0CMP0`=5000, HT-PWM, undivided PCLK). | Always-on, not engagement-gated (runs whenever the motor is powered) | `gp-0x6b98` (merged torque command) has **ZERO reads inside `FUN_00071272`** (the FOC math core, exhaustively confirmed, both static disp-scan methods) — the current loop does not read the delivered torque command directly; the bridge variable carrying the scaled reference into it was **not identified**. No isolated Kp/Ki found — heavily inlined float motor-model math (100+ `maddf.s`), BELIEF: model-based/feedforward, not textbook PI. At 4 kHz, a 20 Hz line is 200 samples/cycle — this loop is not itself frequency-limited near 20 Hz; if it participates, it is via an unidentified reference bridge, not via bandwidth. | No cal-level edit identified in this loop by this census — the whole path is code structure, not a cal cell, so a byte diff cannot directly answer "flown-edited"; recommend a targeted trace if this loop stays a live candidate. |
| (i) | **Lockstep monitor / EME shaper** — `gp-0x6bfa` (REQUEST arm) shadow-locked at `gp-0x4cfa`, mismatch → `FUN_0006b9fa`; `FUN_00043e44` (Monitor2, weighted fault accumulator, bit32 = 32.0 weight on a float `cmd_final` vs `gp-0x6b98/1024` mismatch >5 counts) | 1 kHz-class dwell SM (per the "~10ms to threshold" figure in the EME memory, consistent with a 1kHz weighted accumulator) | Runs continuously, not itself engagement-gated — it is a SAFETY monitor, watching whatever the loop above produces | `cmd_final` (the float side) reads `tp+0x746c` **NOT AT ALL** (confirmed absent by a full disasm scan) — it is built from `gp-0x4f64`(governor), `gp-0x6dac`(an independent 5-channel plausibility score, unrelated to command path), a mode byte, and hard ±8.0 clips. **The EME monitor is therefore blind to the V280 gain raises (`0xC6CD0`, `0xC6446`) entirely** — it compares the DELIVERED command (`gp-0x6b98`) against its own independently-derived estimate, not against a gain-aware reconstruction, so a 20 Hz oscillation riding on the delivered torque is exactly what this monitor is built to catch **if it exceeds ±5 counts of "expected"** — the 20 Hz creep line's magnitude vs this threshold was not evaluated this session (needs a telemetry cross-check, not a static one). | No cal edits identified in this monitor's own path this session. |
| (j) | **100 Hz command intake / gain-table refresh** (task 5, `FUN_00022ca0`) — hosts `FUN_00034350` (damping/FactorC/E), `FUN_00034a72` (boost/viscous, item d), `FUN_0003ad74` (r24/r26 gain-table rebuild, item b) | **100 Hz**, confirmed via TCB byte-read + decompile of the scheduler dispatch, this kit's third independent confirmation of this specific rate | These three functions are NOT engagement-gated as a group — r24/r26's ENGAGED gain (item b) IS gated, but the 100Hz refresh cadence itself runs regardless | A 100 Hz refresh of a table that a 1kHz signal (dtorque) then multiplies against introduces up to **10 ms of staleness** on the *shape* of the gain surface relative to vehicle speed — **not** a bandwidth cut on the 1kHz-sampled signal itself (memory is explicit on this distinction). Not itself a plausible 20 Hz generator (100 Hz Nyquist is 50 Hz, so 20 Hz aliasing is possible in principle but the refreshed quantity is a slowly-varying speed-indexed gain, not oscillatory content) — **LOW priority as a direct 20 Hz source**, but it is the timing context for items (b)/(d). | No table-refresh-rate edits found. |
| (k) | **Two-sample feedback sum** (part of item (a)'s own feedback path — folded in above; not a separate loop) | 1 kHz | gated as part of (a) | see (a) | see (a) |

---

## 3. RANKING — most to least likely to produce a self-sustained, engaged-only, coherent 20 Hz line at creep

**(1) ⭐⭐⭐ Rate lane r24 (item b) — HIGHEST-CONFIDENCE STRUCTURAL CANDIDATE.**
It is the only lane in this census that combines all four required properties in one place: (i)
**engaged-only** by construction (flat gain selected iff `gp-0x6806!=0`), (ii) an **unfiltered
near-ideal differentiator** immediately upstream whose own gain rises ~linearly with frequency (12.33x
more gain at 18.5 Hz than at 1.5 Hz, by the memory's own N=4 computation — no cal or code has ever put
a pole on this specific path, confirmed exhaustively: "no ld/st to any persistent state cell appears
anywhere in this sequence"), (iii) a **measured, engaged-only 10.24x gain raise carried on the current
V280 image** (`0xC6446` 512→5244, byte-confirmed this session), and (iv) it feeds directly into the
1kHz aggregator sum that becomes the delivered torque — no downstream filtering between it and
`gp-0x6b94`. **What discriminates it**: r24's contribution is a pure function of `dtorque` (the 4-tap
difference of driver/column torque, `gp-0x4f62`) with NO state — so if the 20 Hz line is this lane, its
per-frame magnitude should be **linearly reconstructible offline from `gp-0x4f62`'s own 20 Hz content**
against the aggregator sum, using ONLY the flown gain (5244) and the known 4-tap phase response — a
pure Python replay against telemetry already on the wire (`gp-0x6b38`/`gp-0x6b3c` via the CAN-427 tap),
**no new build needed.**

**(2) ⭐⭐ Inertia term `gp-0x6b26` (item c).** Structurally still delivers net ADDED inertia (not
damping) at ~21-22 Hz per the closed pole-fork analysis (+53.64° phase, well short of the −180°···0°
"damping" sector), 1 kHz, reinforcing through two paths. Its poles were already moved once (V109), and
the census this session found nothing changed further on V280 — so this is a **standing, unmodified
contributor**, not something V280 made worse or better. Weaker than (1) because it was never found to
be the *dominant* term in any prior amplitude decomposition this kit ran — it adds inertia, it hasn't
been shown to be the largest term.

**(3) ⭐⭐ LKAS rate PID D-term + feedback lag (item a/k).** A genuine 1kHz closed loop tracking rate
error with a raw (unfiltered) D term and a feedback path whose gain at 20 Hz (≈19.7, computed this
session) is still 64% of its DC value with ≈50° of added lag — i.e. real phase margin erosion right in
the band of interest. But the V276 census already found this loop's peak torque is bound by a **sum
clamp (`0xC61BE`=15360, unchanged on V280)** that starves the D term specifically — so whether D can
actually reach enough amplitude to sustain 20 Hz on its own, versus being clipped away by P, is an
**open quantitative question**, not yet closed either way for THIS symptom (the V276 census closed it
for the 2-4 Hz complaint, not for 20 Hz).

**(4) ⭐ Carrier gain `0xC6CD0` (item e).** Strong PRIOR measured mechanism (pole moved 20.3→23.0 Hz
on a direct on-car dose-response) but that evidence is from a **different band (22-26 Hz) at speed**,
not confirmed at the 18-22 Hz creep band this symptom lives in. Structurally exogenous by Mason's
formula (cannot move poles of a fixed linearization) — its only route to affecting the SYMPTOM band is
via the describing-function/operating-point mechanism into Path-2's nonlinearity, which was never
re-run at 3-6 mph creep specifically. **Ranked below (1)-(3) for THIS symptom only because of the band
mismatch**, not because the mechanism is weak — it remains the kit's best-evidenced 20-ish-Hz vibration
cause overall.

**(5) ⭐ Biquad/notch (item f).** Newly confirmed live+engaged-gated on V280 this session (was dormant
on every pre-V103 build and the kit had not previously checked whether V280 still carries the repoint —
it does). As-flown its own response at 20 Hz is mild (−1.1 dB / −28.5°), so it is unlikely to be a
*generator* on its own, but it changes phase margin in whatever loop it sits inside, engaged-only —
worth checking as a CONTRIBUTING factor to (1)-(3), not a standalone cause.

**(6) Low priority for a direct 20 Hz mechanism**: viscous term (d, 100Hz-refreshed but unfiltered
signal, aliasing risk unevaluated), FOC/PWM (h, 4kHz, no direct command read found), lockstep/EME (i,
a monitor not a generator, and explicitly blind to the V280 gain raises), dwell relay (g, proven zero
contribution in the hands-light steady case by its own corrected polarity), 100Hz task cadence (j, a
timing context not a generator).

---

## 4. Discriminating tests, ranked by cost

1. **(Zero-build) Offline replay of item (1), r24, against existing telemetry.** `dtorque` = clamp of
   the N=4 backward difference of `gp-0x4f62`; the aggregator's r24 contribution =
   `polarity(gp-0x6752) * deadband(dtorque_scaled>>10, D=0xC61F6) * gain(5244 engaged / speed-LERP
   manual)`, clamped ±0x2000. The tap on `gp-0x6b38`/`gp-0x6b3c` already carries the aggregate result;
   `gp-0x4f60`(driver/column torque, already on the wire) is r24's ultimate input upstream of the
   4-tap window. A Python replay of this exact chain against an existing high-angle or creep route
   with the tap live would show whether r24's PREDICTED 20 Hz content matches the MEASURED delivered
   torque's 20 Hz content in amplitude and phase — the same method that closed the V280-rev-2-line
   attribution in `HIGHANGLE-r34-2026-09-03.md` §1 (corr 0.913-0.937).
2. **(Zero-build) Same replay for item (2), the inertia lane**, using the already-decoded pole/gain
   chain in [[reference_accord_gp6b26_two_paths_reinforce_and_pole_fork_dead]] and
   [[reference_accord_gp6b26_alpha0_shared_alpha2_isolated_bandlimit_sweep]] (α2=14 confirmed on V280
   this session).
3. **(One inert tap, if the replays are ambiguous) `gp-0x6bd0` or the D-term's own gp cell** — per
   [[reference_accord_fun28ea6_publishes_its_pid_internals_to_gp_cells]], the PID already publishes 9
   internal terms to gp cells nothing reads; tapping the raw D-term output specifically (not the
   summed `gp-0x6b38`) would isolate item (3) from items (1)/(2)/(5) on the SAME drive, at zero
   authority change and a 3-byte 427-packer edit, per that memory's own stated method.
4. **(Needs a fresh trace, not this session)** Whether `gp-0x6bbe` (item d, 100Hz) can alias a 20 Hz
   signal into its own band was flagged open and not evaluated — if items (1)-(3) don't close it, this
   is the next thing to trace.

## Open questions / verification needed

- Item (d)'s aliasing risk at 100 Hz sampling of nominally-20-Hz-adjacent content — not computed this
  session; would need `FUN_00034a72`'s exact sample-and-hold behavior confirmed (is it a true 100Hz
  sample of a continuously-updated `gp-0x6a56`, or does it read a value that itself only changes at
  100Hz? Not determined here).
- Item (h)'s "bridge variable" carrying the scaled torque reference into the FOC math core
  (`FUN_00071272`) was never identified in the cited prior session — if this loop stays a candidate,
  that identification is the concrete next step (a fresh `analyze_dataflow` backward from the core's
  Iq/Id reference registers).
- Item (i)'s EME threshold (±5 counts) was not cross-checked against the MEASURED 20 Hz amplitude on
  `gp-0x6b38` from the HIGHANGLE-r34 creep windows (per-second bar 18-22Hz amp up to 281 raw at the
  operator's own timestamps) — worth a direct check: does this monitor actually see the creep-band
  line, or does its own blindness to gain raises (item i, `cmd_final` not reading `tp+0x746c`) also
  make it blind to whatever generates the 20 Hz content specifically?
- I did NOT re-open Ghidra this session — every structural claim above traces to a prior GhidraMCP
  session cited by memory file; the only fresh work this session is the Python byte-level V280-vs-stock
  comparison. If any ranked candidate becomes the lead for a build, re-confirm its structural claim
  with a fresh `decompile_function`/`disassemble_function` call before cutting, per this kit's own
  adversarial-pass standing instruction.
