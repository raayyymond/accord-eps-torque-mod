# HANDOFF 2026-09-07 — V288 rev 2: the setpoint pre-filter cave, the first reference-side build since V38

**Read `docs/STATE.md`'s decision box first.** This is the narrative: what the operator asked, what nine agents found, what killed rev 1 twice, and what the flash candidate actually is.

## 0. The one-paragraph version
The operator drove V287 rev 2 (D clamp 7680), *"still felt the grinding"*, went back to V282, and rejected V287's whole class: no build may lower the feedback P/D terms or the V282 authority. He asked for a build on V282 that eliminates the grind and offered a hint from outside: check whether the 20 Hz is in the 0xE4 command itself. The wire says it is, but as an **echo** (9 % of the PID sum's 20 Hz, open-loop) — and the command is **not** a 20 Hz staircase: it changes on 92 % of 100 Hz frames and is **slew-capped at 123 raw/frame by openpilot's own limit**, and about half of every D-clamp bind lands on a capped frame. Grind #1 is a **rung bell** (97.6 % of episodes decay; ζ ≈ 0.026), so cutting the excitation shrinks it. The record already said the setpoint path has no memory anywhere, so the lever is a **code cave that low-passes the setpoint** — outside the rate loop, zero calibration bytes, authority untouched. **V288 rev 1 failed the adversarial pass twice** (filter state froze across disengagement and seeded re-engage; the telemetry rung overwrote a stock Honda CAN bit). **Rev 2** adds an engage-time init from Honda's own first-tick sentinel and moves the instrument to the kit's own bit 5; A/B pass with conditions, C/D pass. It is built and unflown.

## 1. How the session was run
Orchestrator + subagents (all briefed as subagents reporting to `main`, GhidraMCP only, EVIDENCE/BELIEF on every claim); every decision-bearing crux re-verified by the orchestrator from the image or Ghidra: the hook bytes and the zero-reader census of gp-0x6a32, the free flash, the register liveness at 0x29D72 (r6/r9 dead), the stock writers of 0x14A byte 4 (0x55AB0–0x55B0A), the shared epilogue and both sentinel loads (0x2A16C, 0x2A0EA, and that r16 survives to 0x2A18C), the slew cap in the fork's carcontroller, and every artifact hash from disk.

| agent | surface | outcome |
|---|---|---|
| `wire` (Opus) | is the 20 Hz in 0xE4? cadence, slew cap, coherence, doses, growth-vs-decay | staircase premise falsified; cap = excitation; echo 9 %; rung bell ζ≈0.026; mirror is open-loop (corrected its own §4) |
| `op` (Sonnet) | the operator's fork's lateral pipeline | no Accord output LPF; rate_limit ±0.03·4096/frame; clip_curvature + 1.2 Hz jerk filter + 0.10 s rate-plant filter already present |
| `lineage` (Sonnet) | was the reference ever filtered V38→V287? RAM safe to reuse? | never; V50–V52C filtered the SENSOR; 0xC6194/0xC61D6 dead/unsafe; mailbox range is poison |
| `tracer` (Opus) | buildable spec | hook 0x29D72, reuse gp-0x6a32, IIR with the `sar` rounding fix, 1048 B free flash |
| `builder` (Opus) | rev 1 → rev 2 → exact compare → docstring/name | 498/498 assertions, independent rebuild, one flashable rwd |
| `advA`…`advD` (Opus×3, Opus) | arithmetic · units/loop/lag · build audit · interlocks/GATE 1 | rev 1: A FAIL, B FAIL, C PASS, D PASS → rev 2: A/B PASS-cond, C PASS, D PASS |
| `lerps`, `delta`, `golden` (Sonnet, Sonnet, Opus) | LERPs from the images · cumulative non-stock delta · golden model | page data; 33-row delta matching the 2026-09-04 doc; `lkas_setpoint_prefilter` added, contract 88 |

## 2. What changed my mind, in order
1. **I expected the "command staircase" to be the story.** The wire killed it in one table: 94.5 % of gaps between command changes are one frame. What is real is openpilot's slew cap, and the census's "top-1 % step ≥ 122" turned out to be that cap (0.03 × 4096 = 122.88, verified in the fork).
2. **I nearly relayed "a setpoint filter can remove at most 9–13 %".** That came from the kit's 1 kHz mirror, which feeds the LOGGED wheel rate back — open-loop. The 9 %/63 % split is a share of the PID sum, not a closed-loop bound. The growth-vs-decay discriminator settled the direction: a decaying, positively damped mode means the trigger size sets the amplitude.
3. **Rev 1 looked clean and failed twice.** B found that every path skipping the hook resets every PID state cell except ours; D independently retracted its own "decays while disengaged" once it read the guard at 0x29A48. A found the telemetry rung sitting on a stock Honda bit because the builder's free-bit census only read the cave's own masks. Both fixes were ideas the firmware already contained: Honda's own sentinel, and the kit's own bit.
4. **0x2A164 is not a reset routine.** It is the head of a shared epilogue; a "store on the reset path" would have fired every tick. The sentinel test in the cave is the only correct place.

## 3. Corrections of record produced
- The 0xE4 command is a continuously updating 100 Hz signal, slew-capped at 123/frame; there is no 20 Hz staircase. The per-tick impulse into D is the landing of each frame step on one of ten ticks.
- The 1 kHz mirror (`grind_incident_r35.simulate` / `GI.simulate`) is open-loop; every "share of T's 20 Hz" figure is a share.
- 0x14A byte 4 bits 0–2 are stock Honda (gp-0x679a/679b/6799 at 0x55B06/0x55AE8/0x55AC0). "Bits 2–0 are written by nothing" is false.
- The disengage paths skip the hook; the filter state would freeze without the sentinel init. D's rev 1 §3 is retracted; D's "70 ms tail" is real only during the engagement-ramp walk-down.
- The operator is on his own fork (`openpilots/raayyymond-StarPilot/StarPilot` @ Dom); the 2026-09-02 "plain StarPilot" convention is superseded.
- The golden model has never contained the LKAS rate PID stage. Contract is 88 symbols (hash unchanged).

## 4. What is on disk
- Candidate: `../accord-firmwares/flashing-2020accord/rwd/39990-TVA,A160-V288R2-V282BASE-SPFILT.K4.EINIT-KP.FLAT.Y0-CAVE.R24CMP.B6-SPSIGN.B5-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP-0x13000-0x100000.rwd` sha256 `43efd0c98446d331a5b529cbaf93f1173e61e9daa132903cf3467078a7207714`; image `_v288r2_…_plain_image.bin` `94cabdefd39a103ad10ec34b9c64b6ac94d6552b80bfe7cc192a8977cbbdbd8c`. Rev 1 renamed `SUPERSEDED-DO-NOT-FLASH…` (bc8a5b1a… / 862cb525…).
- Script: `analysis-2020accord/builds/v108_plus/build_v288_tva.py` (K_SHIFT one constant; K=3 re-cut verified).
- Spec: `docs/specs/design/SPEC-V288-SETPOINT-FILTER-CAVE-2026-09-07.md`. Prereg + verdicts: `docs/review/ADVERSARIAL-V288-PREREG-2026-09-07.md`, `ADV-V288-{A,B,C,D}-*.md`.
- Studies: `rlog-tools/studies/grind/WIRE-0XE4-20HZ-2026-09-07.md` (+ `wire_0xe4_20hz.py`, `wire_0xe4_slewcap.py`, `wire_0xe4_burst_damping.py`); `docs/research/STARPILOT-FORK-COMMAND-PIPELINE-2026-09-07.md`; `docs/research/LINEAGE-COMMAND-PATH-FILTER-CHECK-2026-09-07.md`; `docs/review/V288-LERPS-FROM-IMAGE-2026-09-07.md`; `docs/review/V288-CUMULATIVE-NONSTOCK-DELTA-2026-09-07.md`.
- Page: https://claude.ai/code/artifact/fb9a34f0-9b1c-4850-b673-187c100ce6fd
- Golden model: `lkas_setpoint_prefilter` (SECTION 5B), `Calibration.spfilt_k`, `EpsState.sp_filter_y` / `pid_prev_err_cell`; 88 symbols, hash `740f4bcd…` unchanged.

## 5. Decoder note (must be applied before the first V288 drive is read)
On V288, **0x14A byte 4 bit 5 = sign(filtered setpoint y)** (1 when y < 0). It was V282's `|r24| ≥ |aggregator sum|` comparator; bit 6 (`|r24| ≥ |T|`) and bits 3/4/7 are unchanged; bits 0–2 are stock. `rlog-tools/studies/grind/extract_14a_b4_r36_r38.py` and any script reading b4.5 as a comparator must branch on the build. Liveness: bit-5 duty of 0.000 or 1.000 over ≥ 20 s engaged means the rung did not execute (a build-identity failure, not a null). The group delay is the zero-crossing lag between bit 5 and sign(sp_raw) reconstructed from the logged 0xE4 through the (memoryless) decode → clamp → map chain; expect ≈ 15 ms.

## 6. Open items
1. Outer-loop phase margin of openpilot's torque controller on this car — never measured; the 15 ms is a stated cost (≈ 20° at 3.9 Hz).
2. Kp/Kd LERP indexed by the raw command, not sp_f — inert while Kp is flat.
3. Golden model: add the LKAS rate PID stage (then the governor MIN-fold and the oscillation detector).
4. openpilot-side echo lever (measurement LPF / SteerFriction) on the fork — not a firmware item.
5. `0xC61C0/C2/C4` blanked since V36 with no recorded intent; the 12 bytes at 0xC4FF0 (partly CRC-chain fields).
6. `docs/STATE.md` is 181 KB (cap 256 KB, target ~150 KB) — archive older blocks at the next close-out.
