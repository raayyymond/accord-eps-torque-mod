# HANDOFF 2026-10-01: the angle-loop goal set, traced, designed by panel; V298 built and adversarially passed, NOT FLOWN

**Nothing flashed, no CAN sent.** The car runs **V295** (flown by the operator 2026-09-30; rlog not yet read). **V298** is on
disk in `accord-firmwares` with its two re-headered revert files and is waiting for the operator. The fork angle interface is
**implemented on the operator's fork (`raayyymond-StarPilot/StarPilot`, branch `Dom`), three local commits, NOT pushed.**
**No artifact page exists for V298** (see "What is NOT done"). The authority is `docs/STATE.md`'s DESIGN STATUS box. This
file records **how the two days ran** and **where each result lives**. It does not re-derive anything.

Previous: `docs/handoffs/2026-09/HANDOFF-2026-09-30-v294-flew-v295-trim-gain-built.md` (V294 flew; V295 built).

---

## 1. The operator's rulings, in order (each one is binding, and each has a memory)

| date | ruling | where it lives |
|---|---|---|
| 2026-09-30 | **The tuning space is whatever a cave can afford.** Caves are allowed but must be minimised and verified thoroughly. Cal-only is a preference, not a constraint. | `CLAUDE.md`; `firmware-iteration` skill; `memory/feedback/process/feedback-tuning-space-is-whatever-a-cave-can-afford-minimise-and-verify.md` |
| 2026-09-30 | **V294 and V295 FAILED their stated goal.** They were designed to track angular acceleration and do not: \|L\| ≤ 0.63 at any cal value. A build is scored against the goal it was designed for. | STATE evening verdict box; `memory/accord/mechanism/accord-ki-on-acceleration-is-a-dc-rate-term-and-acceleration-feedback-is-virtual-inertia.md` |
| 2026-09-30 | **THE GOAL:** tight, smooth and silent at every speed. The means is a 1 kHz firmware loop closed on **steering angle** (gp-0x6a00), fed an angle setpoint from a minimally modified StarPilot. The cave is the fewest instructions that give that loop, with nothing waived. Success is measured. | STATE 🎯 box (verbatim); `memory/project/project-the-goal-2026-09-30-angle-loop-cave-tight-smooth-silent.md` |
| 2026-10-01 | **Design is a JUDGE PANEL:** several designs, each with several implementations, scored by common scorers and then by independent judges, followed by synthesis and refuters. One agent producing one solution is not a design round. | `memory/feedback/process/feedback-design-is-a-judge-panel-never-one-agent-one-solution.md` |
| 2026-10-01 | **V298 = the primary + the gp-0x6803 == 2 camera interlock is the flight candidate.** The camera-on-relay-close hazard must be structurally impossible, not avoided by procedure. This was conditional on the adversarial pass and on matching the direction-2 hand-fade record to the stock arm as cal. | `memory/feedback/builds/feedback-v298-camera-interlock-is-the-candidate-no-fork-angle-integral-for-drive-1.md` |
| 2026-10-01 | **No fork angle integral for drive 1.** Reconsider it only after the drive, from the measured residual and the breakaway friction per band. Below τ_o ≈ 6 s it rings, and above that it is too slow to matter. | same memory |
| 2026-10-01 | **Fork CODE is authorised for the angle interface**, on his fork's `Dom` branch only, as local commits with no push. The upstream StarPilot checkout stays read-only. | `memory/feedback/process/feedback-angle-interface-fork-code-authorised-on-raayyymond-starpilot-dom.md` |
| 2026-10-01 | **The first flight of V298 is in a CONTROLLED SETTING** (an empty lot or a quiet closed road). It replaces a UDS polarity read beforehand. | `docs/scoring/DRIVE-CARD-V298-controlled-setting-2026-10-01.md` |

## 2. Tracers (2026-09-30; EVIDENCE; the orchestrator re-verified the crux from the TCB table at 0xBB910 and the Ghidra callers)

- `docs/traces/TRACE-2026-09-30-angle-signal-gp6a00.md` covers the angle variable: a signed halfword at 0.1 deg/count, equal to +10 × openpilot's angle. It also identifies the fresh 1 kHz angle gp-0x69ca and the fresh motor-frame rate gp-0x6abe (0x7FFF when invalid).
- `docs/traces/TRACE-2026-09-30-lkas-lane-hook-and-setpoint-path.md` covers the lane FUN_00028ea6 (RTOS task 0, 1 ms), the hook site and the setpoint path. It verifies the zero-cave angle P edit set in V295's bytes.
- `docs/traces/TRACE-2026-09-30-speed-driver-torque-lerp-and-ram-homes.md` covers speed, the driver-torque LERP, and the free cave span and flight-proven RAM homes.
- `docs/traces/TRACE-2026-09-30-sentinel-downstream-and-angle-validity-gates.md` covers the 0x7FFF sentinel and the A2/B2 guards. The 0x7FFF timeout pulse **rails P for 2 s on V293–V295 today**.
- `docs/traces/TRACE-2026-09-30-dominance-preemption-timeout-version-and-6803.md` covers r27 dominance and r8 deadness. The 0xE4 RX callback cannot preempt the lane. The 0xE4 timeout lands at 510 ms. The version string and gp-0x6803's direction arms are also here.
- **The headline:** the lane runs at 1 kHz, but its rate feedback gp-0x6a56 and the angle gp-0x6a00 are written in task 4 at 100 Hz. **Every rate-loop build from V282 to V295 closed on a 10 ms sample-and-hold.** The loop conclusions stand. The attribution was wrong: the record had charged the hold to the plant as a "3.9 ms stream offset". Memory: `memory/accord/firmware/accord-lkas-feedback-is-a-100hz-hold-and-the-zero-cave-angle-loop-edit-set.md`.
- The fork-side interface spec is `docs/specs/design/SPEC-angle-setpoint-interface-2026-09-30.md`.

## 3. Harnesses, single-agent designs, and the refutations (2026-09-30 → 2026-10-01)

- **Harnesses:** `studies/angle_loop/harness_freq.py` and `harness_time.py` are independent of each other, and their reports `studies/angle_loop/reports/HARNESS-{FREQ,TIME}-2026-09-30.md` agree. Neither a flat Kp nor a |θ|-indexed Kp can meet the goal, because the crossover gain must span about 4.5× with speed. **One speed-gain cave is therefore the minimal structure.** See also `reports/HOLD-RECORD-CHECK-2026-09-30.md`.
- **C0** `docs/specs/design/DESIGN-ANGLE-LOOP-C0-2026-09-30.md` was **REFUTED** (`reports/REFUTE-{stability,friction,safety}-2026-09-30.md`; reconciliation in `studies/angle_loop/reconcile_c0/`).
- **C1** `DESIGN-ANGLE-LOOP-C1-2026-09-30.md` and `…C1-rev1-REFUTED-…` were **REFUTED**. Failures: J_hi PM 40.7° at 10.5–12 m/s, combined members PM 17°, sar-5 integer blindness, light-hand wind-up of 1–9°, and b_q × J_hi unstable at 15–19 m/s (`reports/REFUTE-C1-r1-stability-…`; work in `studies/angle_loop/c1/`).
- **Panel round 1** (5 designers, 17 candidates): `docs/specs/design/panel/DESIGN-PANEL-{A,B,C,D}-…`, `studies/angle_loop/panel/` (scorers, `JUDGE-bytes-risk`). Four implementations were fully specified. **C2** = P2/F2 (`DESIGN-ANGLE-LOOP-C2-rev2-A`) and D2a/B0r (`…C2-rev2-B`). C2 was refuted on five open findings, F1–F5 (`reports/REFUTE-C2-r{1,2}-*`): the I clamp is below the curve spring load, the 1.155 D-operand frame ratio un-gates GATE 2, the ms_free × damping corners, an undeclared 8–15 m/s dwell, and the stock camera's 0xE4 being read as an angle on a relay close.
- **Panel round 2** (all roles pinned to `claude-opus-5-5`): `docs/specs/design/panel2/DESIGN-PANEL2-{E1,E2,G,H}-…` and `studies/angle_loop/panel2/` (common `score_freq.py`/`score_time.py`, three judges: goal / bytes-risk / operability). All three judges ranked E2's angle-referenced integral bound first.
- **C3** `DESIGN-ANGLE-LOOP-C3-2026-10-01.md` was **REFUTED** (`reports/REFUTE-C3-r1-*`): GATE 2 collapsed at curve operating points, the A3 bound worked in one direction only, and a G dip below 512 made Honda's I quantum one-sided.
- **C3-rev2** (two revisers + a revision judge) = `DESIGN-ANGLE-LOOP-C3-rev2-2026-10-01.md`, with variants `…-A` (it carries the camera-interlock variant R1-P-cam) and `…-B`. Its **second refutation** (`reports/REFUTE-C3-r2-*`) found three things. (1) The FLIGHT cave hex had been byte-spliced without relinking: the G-table pointer and the freeze-return jr were 2 bytes stale, so **the shipped bytes were never the scored bytes**. (2) "Fork angle integral τ_o ≥ 1 s" is insufficient, which led to the no-integral ruling. (3) The camera hazard is not fail-safe in firmware, which led to the interlock ruling.
- The refutation chain is **C0 → C1 → C2 → C3 → C3-rev2**. Each design died for a reason that its successor designs around. Work dirs: `studies/angle_loop/{c1,c2,c3,refute_*}/`.

## 4. V298, built 2026-10-01, NOT FLOWN

- **What it is:** C3-rev2-P with the gp-0x6803 == 2 camera gate on top, and the flight cave **relinked by a two-pass linker**. The orchestrator re-decoded all four references from the image: table ptr 0xC4CDA, op-skip → 0x2A164, and the freeze and camera returns → 0x29D7E. The direction-2 hand-fade record 0xE54FC (24 B) is set equal to the stock arm 0xE564C as cal. **The cell table is the build script's docstring, section 0** (`analysis-2020accord/builds/v108_plus/build_v298_tva.py`). Do not re-type it.
- **Identity:** image sha256 `177abf043550851789e1063b6625a0e17115a1beb50851571f1b38780bf32066`, rwd sha256 `1a69b92760b8a9538b504b020076e5b025fed7af03b34800ecd05dd687ce960e`. The diff is 325 B vs V295 and 2471 B vs stock. There is one 260 B cave at 0xC4C00 and 0 RAM. F181 becomes `39990-TVA,A16A`.
- **Verification (EVIDENCE, as STATE records it):** CRC chain 50/50 + bootloader 49/49. H1 0/40000 **on the flight bytes**, with two negative controls. The golden contract holds: 94 symbols, hash `740f4bcd…` unchanged, and `_self_check_v298` asserts against the image.
- **Adversarial pass on the built image, four lenses, ALL PASS_WITH_DEFECTS, no flash-blocker** (`analysis-2020accord/studies/angle_loop/v298/adversarial/`; the FAIL criteria were written first and are in the same folder):
  - Arithmetic (`ADV-arithmetic-V298.md`): the bounded sar-5 integrator floor bias is ≤ ~+204 output counts worst case, covered by R6 and the c0 term.
  - Unit/scale (`ADV-unit-scale-V298.md`): every unit on the page agrees with the image. The fresh-D sign rides on pol = −1, which is specific to this car.
  - Build audit (`ADV-build-audit-V298.md`): 27 of 48 "substantive" assertions are base-readbacks. The defect is collateral only.
  - Interlocks/GATE 1/GATE 2 (`ADV-interlocks-gates-V298.md`): 0 RAM. The θ=0 box has 0 fails, worst PM 38.5°. Operating points pass 45120/45120 non-ms_free, worst 32.8°. The ms_free J≈2 family is declared (PM down to 4.6°, ρ < 1, stop band R3* 0.25–0.9 Hz).
- **Revert files:** the V295 and V294 rwd files were re-headered to list A16A (`…-REHEADERED-FOR-REVERT-FROM-V298-…`, sha fb6969fc… / e64f035d…). The originals are untouched.
- **Declared misses (BELIEF on outcome, EVIDENCE on the mechanism):** low-speed stick-slip below 8 m/s (dead zone ≈ Fc/Kp ≈ 1.5°; V282 is not simulated as a baseline, so "≤ V282" is unscored). Also the ms_free ring (R3*), outward-hand lurch up to 14° on b_lo × J_hi, small-signal tracking in the 11–12.5 m/s dip, and 13 Hz anti-damping at 1.33× V295 at some hold ages (R4).
- Lineage: `docs/BUILD-LINEAGE-PART6-V291-ONWARD.md` (V296/V297/V298 pointer entries). Memory: `memory/accord/builds/accord-v298-angle-loop-built-not-flown-four-lenses-pass-with-defects.md`.

## 5. The camera census (EVIDENCE)
`docs/traces/TRACE-2026-10-01-camera-0xE4-byte2-census.md` covers 95 routes and 6,898,004 bus-2 camera frames. **The camera sends byte-2 bits 3:2 = 2 on none of them.** The camera does steer on that bus, with request set on 134,142 frames and |tq| ≤ 2560. openpilot sends 0 in that field today. So the interlock premise is EVIDENCE, and the fork change is required. Keep the car's own LKAS off on drive 1 anyway.

## 6. The fork implementation (operator's fork, `Dom`, local, NOT pushed)
- `51c199f28`, the interface: fwVersion A16A + the `AccordEpsAngleLoop` gate, angle limits and error clip on V298's gains, the carcontroller angle branch, byte-2 field = 2 on every frame, override hysteresis 600/500, the sensor-status fault, the steer-ratio fixed point, the Galaxy toggle and Safe Mode. 46 tests, including a recorded-route replay proving the torque path is byte-identical when the switch is off.
- `38cff0247`: lagd keeps no saved lag across a control-type change.
- `2712e1336`, review fixes: a permanent fault when the switch is on without the A16A EPS, the hold predicate mirrors the panda, the limiter is seeded from the wheel on the first frame and on release, SteerRatio 16.84 is pinned, and docs.
- **Review:** two reviewers + a re-reviewer returned PASS_WITH_DEFECTS. Every code item is EVIDENCE: the torque path is byte-identical over 45 config×scenario cells. There are two LOW doc notes.
- **Configs** in `analysis-2020accord/studies/angle_loop/fork-config/` (README = deploy order and the permanent-fault semantics): `toggle-config_V298_angle_loop.json` (rev 2, SteerRatio 16.84 from route 71b's initData) and `…_REVERT_to_V295_r2.json`. Rev 1 is in `superseded/`; do not restore it. **Check the device's current SteerRatio before deploying.**
- Memory: the ✅ fork-interface pointer at the top of `memory/MEMORY.md`.

## 7. Drive cards and the reader
- `docs/scoring/DRIVE-CARD-V298-controlled-setting-2026-10-01.md` is **drive 1**: low speed, a structural LIVE/INVERTED read, and the engage/override/release/timeout behaviour. A dead zone of about 1.5° below 8 m/s is EXPECTED and is not by itself a failure.
- `docs/scoring/DRIVE-CARD-V296-angle-loop-2026-10-01.md` was written for the primary and applies to V298. It is the **≥ 8 m/s card** where the goal criteria get scored.
- The reader is `rlog-tools/studies/angle_loop/angle_loop_drive_read.py`. On synthetic controls it scores LIVE 4/4 and wrong-image NOT LIVE 4/4.

## 8. What is NOT done
- **No artifact page for V298.** The orchestrator's page write was stopped by an automated safety classifier and was not re-attempted. The close-out contract's artifact clause is therefore **unmet**. The content lives in the design doc, the build docstring, the adversarial reports and the drive card.
- **V296** (the primary without the camera interlock) and **V297** (the held-rate-D fallback C3-rev2-F) were **NOT built**. Their builders were halted by the classifier, and V298 is the ruled candidate. Their adversarial folders (`studies/angle_loop/v29{6,7}/adversarial/`) hold **DO_NOT_FLASH, criterion F0/A0: no artifact exists**. That is not a verdict on the design.
- The V295 rlog (the c1/c2 tap read) is still unread.
- The pol = gp-0x6752 = −1 re-proof on this car is replaced by the controlled-setting drive's INVERTED check, per the operator's choice. This is BELIEF until that drive.
- Nothing is pushed on the fork. The push is the operator's.

## 9. Process facts (each one cost something this session)
- **Model substitution:** the harness substituted Opus 4.8 for the `opus` alias in nine round-1 agents. The operator's rule is that all Opus agents must be 5.5. **Every workflow call now pins `claude-opus-5-5`.**
- **Classifier halts:** an automated safety classifier halted roughly a third of the agents. In round 1, seven of twenty stopped while reading design documents: designer E, the time scorer, two judges, the synthesis, the revision judge and one refuter. STATE counts eight interruptions across the rounds. The V296/V297 builders, the orchestrator's page write and the collateral agent were also stopped. Round-2 briefs told the agents to "continue with the remaining items and list what was withheld", and that worked.
- **The SendMessage trap:** a SendMessage to a *running* workflow subagent resumes a **duplicate** copy, which then edits the same tree concurrently. Never do it; decide everything in the brief. Memory: `memory/feedback/tooling/feedback-never-sendmessage-a-running-workflow-subagent-it-resumes-a-duplicate.md`.
- **A build's scored bytes must be its shipped bytes.** The C3-rev2 splice defect was caught only by a refuter. The fix is a listing-level injection plus a two-pass relink, then H1 run on the flight bytes.

## 10. NEXT, in order (exactly as STATE's V298 paragraph states it)
1. **The operator pushes** the three `Dom` commits.
2. On the device: pull `Dom`, then run **Rebuild Params**.
3. **Flash V298**. This is the operator's step: he names the file and the bus, and openpilot is killed first.
4. **Reboot.**
5. **Restore** `toggle-config_V298_angle_loop.json` while parked, after checking the device's SteerRatio.
6. **Reboot.** Check carParams.steerControlType = angle, EPS `39990-TVA,A16A`, `AccordEpsAngleLoop` = 1, SteerRatio 16.84, and no LKAS fault. The car's own LKAS must be OFF.
7. Fly the **controlled-setting drive** per its card.
8. **Hand over the route.** The reader decides LIVE / NOT LIVE / INVERTED and reports breakaway friction per band.
9. Only after a clean drive 1: fly the **≥ 8 m/s card** (`DRIVE-CARD-V296-angle-loop-2026-10-01.md`).

**Revert:** restore the REVERT config, reflash the re-headered V295 rwd, and reboot after both. Until both are done, openpilot shows a permanent fault, which is safe (fork-config README).
