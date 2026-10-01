# REFUTE C2 r1: bytes and fail-safe (2026-10-01)

**Verdict: REFUTED. DO NOT FLASH. There is no C2 design to clear.**

Lens: BYTES-AND-FAILSAFE. This covers re-decoding every edit and cave byte, branch displacements,
register liveness at hook 0x29D76 (r25 live, r14 = ramp, the free set), GATE 1 for every RAM word,
int32 bounds against the table and the 0x7FFF sentinel, A2/B2 guard semantics, the
timeout, fault and preemption paths, gp-0x67fe != 2, mode != 3, and how the build behaves with a
torque-mode fork, a fork that emits zeros, and the stock camera.

## What was handed to this refuter

The C2 synthesis returned `"HALTED, NO SYNTHESIS PRODUCED"`: a primary and a fallback with id
`none (halted)`, `bytes_total 0`, `cave_count 0`, `edits "none produced"`, `cave "none produced"`, and
`design_doc "not written (halted)"`.

## Checked on disk (EVIDENCE: `ls` / `find` over the repo, 2026-10-01)

| expected artefact | present? |
|---|---|
| `docs/specs/design/DESIGN-ANGLE-LOOP-C2-2026-10-01.md` | **No** (`ls`: no such file) |
| `analysis-2020accord/studies/angle_loop/c2/` | **No** (`ls`: no such directory) |
| any file matching `*C2-2026-10-01*` or `score_time*` anywhere in the repo | **No** (`find`: zero hits) |
| `analysis-2020accord/studies/angle_loop/panel/score_time.py`, which the C2 brief says to re-run | **No** |

The halted output describes itself accurately. None of the files it says were not written exist.

## Why this is a refutation and not a pass

- This lens has no bytes to decode, no cave to trace, no RAM word to GATE-1 and no guard edit to
  check against the real control flow. **Every decision-bearing claim this lens exists to test is
  unverifiable, because none was made.** Under the brief ("if you cannot verify a decision-bearing
  claim yourself, ... return refuted = true for that reason"), the outcome is REFUTED.
- An empty design also cannot satisfy the fail-safe requirement. A build is only clearable if every
  torque path is shown to need a valid, current setpoint and to fail safe otherwise, and no path set
  exists here to show that for. **"No design" must never be read as "no hazard found."**
- In the C2 output, `gate2 "not scored"`, `time_gates "not scored"`, `misses "not produced"` and
  `hazards "not produced"` are **not results.** No pre-declared miss or stop band exists, so a
  pre-declared shortfall cannot excuse anything.

## What this refuter did NOT do, on purpose

- **It did not substitute a panel candidate for C2.** `panel/D-structure/` contains cave hex for
  B0r, D1a–D1c, D2a–D2c and D3a–D3b, and `JUDGE-bytes-risk-2026-10-01.md` ranks D2a 82 and B0r 81.
  None of those is C2, and choosing which one becomes the design is the orchestrator's synthesis
  decision, not a refuter's. Running this lens on D2a or B0r needs its own brief naming the exact
  hex file and its edit list.
- No Ghidra program was opened and no byte was decoded. There was nothing to decode. The FACTS in
  the brief (A2 0x29A56, B2 0x29A50, 0x28F4E, 0x28FA4, 0x29D6A, 0x29EDE/0x29EE0) were neither
  re-verified nor contradicted here. They remain the tracers' EVIDENCE.
- Nothing was built, flashed, sent or written outside this report.

## What a re-run of this lens needs

1. A written C2 design doc that lists the exact in-place edits (address, old bytes, new bytes) and the cave as hex
   with its load address. It also needs the hook displacement, the cave's RAM words and every cal cell it changes.
2. The c2/ build or assembly script, so the cave bytes can be rebuilt independently and compared
   against the doc.
3. The pre-declared misses, each with its stop band and revert signature, so a shortfall can be told apart
   from a refutation.

## Return

`refuted = true`. Reason: **no C2 artefact exists, so no byte, guard, RAM word or fail-safe path can be
verified, and an unverifiable design cannot be offered for flashing.**
