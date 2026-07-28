# docs/ — Index

This directory holds the human-readable documentation for the 2020 Honda Accord EPS firmware project (`39990-TVA-A160`, Renesas V850E2): technical references, runbooks, and the session handoff chain. These are real working artifacts written by Joey (and his agents) over the course of the project — not polished public docs. The goal is that you can read them as-is and reconstruct the project's reasoning, history, and current state.

Everything here is **read-only context**. Source tools and code live in this
repository (`analysis-2020accord/`, `flashing-2020accord/`); proprietary
firmware artifacts live under the sibling root `../accord-firmware` by default.
Python tools honor `ACCORD_FIRMWARE_ROOT` when a different artifact root is
needed.

---

## Recommended reading order (cold start)

1. **`../CLAUDE.md`** — the boot context; has the full current-state narrative baked in.
2. **HONDA-EPS-PID-KNOWLEDGE.md** — the canonical Honda EPS PID reference, distilled from a 26-day private Discord working group. Read this BEFORE attempting any PID tune.
3. **`../flashing-2020accord/EPS_UPDATE_TVA_README.md`** — the current Accord flashing workflow.
4. **EPS-FLASH-RUNBOOK.md** + **RED-PANDA-EPS-SETUP.md** — the physical red-panda + comma-harness rig (car-agnostic hardware/procedure, still the setup in use).
5. **Latest handoff:** **`HANDOFF-2026-07-20-v44-handsoff-damping.md`** — the current candidate. Read it before any other build doc. It root-causes the **vibration** as a **measured lightly-damped mechanical resonance** (21.4 Hz, Q≈13.6) whose firmware enabler is that the base-assist **viscous damping** lane (`FUN_00034350` → `gp-0x6bd0`) is multiplied to **exactly zero hands-off** (`Y[0]=0` in the driver-torque LERP at `0xD27BC`/`0xD27D0`) in a command path with **no notch filter anywhere**; V44 raises those `Y[0]` cells. It carries five **corrections of record**: the control-task tick is **confirmed ~1000 Hz** (retires the old "unresolved" item); the "sharp 21.02 Hz clock-locked line" was an **FFT artifact**; `gp-0x6abe` is **live** in normal driving (golden model was backwards); the V43 "half-wave damper" is **wrong**; and `search_instructions` **undercounts** (use byte-pattern scans). The **hard-turn ratchet is SOLVED** (V42 Change 1, `0x454FE`, confirmed on-car) and carried through unchanged. ⚠ **SUPERSEDED — vibration conclusions falsified on-car, read only for disassembly:** `HANDOFF-2026-07-21-v43-dirty-derivative-pole.md` (pole falsified), `HANDOFF-2026-07-20-v42-state4-ratchet.md` (r26 falsified; but its ratchet fix + the gain-rescaling-invariance tool stand), `HANDOFF-2026-07-20-session-v40-fault-investigation.md`, `HANDOFF-2026-07-20-v41-ratecap-flat.md`, `HANDOFF-2026-07-19-v41-crc-c5000-block-fix.md`, `HANDOFF-2026-07-19-v40-governor-slew-and-rate-cap.md`, `HANDOFF-2026-07-19-v39-direct-torque-rate-guard.md`. ⚠ Note the "LKAS lane is a ~1–5 Hz low-pass ⇒ a fast vibration can't be commanded" argument from the V42 handoff is **narrowed**: the resonance is a physical plant mode fed by the raw torque sensor, downstream of that IIR. Then `HANDOFF-2026-07-17-v38.md` (flashed fault-free). Walk backward for the full V9→V44 lineage.
6. **FIRMWARE-DECOMPILE-GUIDE.md** + **GHIDRA-CHECKLIST.md** when you're ready to verify addresses yourself.
7. **AGENTS.md** for the lightweight collaboration conventions (bd / beads issue tracking).

---

## Start here

| Doc | What it is |
|---|---|
| [EPS-FLASH-RUNBOOK.md](./EPS-FLASH-RUNBOOK.md) | The primary flashing workflow — red panda + laptop, end-to-end. Hardware/procedure doc, no car-specific part numbers. |
| [RED-PANDA-EPS-SETUP.md](./RED-PANDA-EPS-SETUP.md) | Hardware setup guide for the red panda + WSL Ubuntu laptop path (through the comma Bosch harness, not OBD-II direct). |

## Technical reference

| Doc | What it is |
|---|---|
| [HONDA-EPS-PID-KNOWLEDGE.md](./HONDA-EPS-PID-KNOWLEDGE.md) | **Canonical Honda EPS PID reference.** Synthesized from a 26-day private Discord working group (4,989 messages, 5 hands). Covers torque-table saturation, controller kf/kP/kI/kD ranges, lateral-accel ceilings, model selection, and the pre-flight checklist. **Read before any PID work.** |
| [GHIDRA-CHECKLIST.md](./GHIDRA-CHECKLIST.md) | Step-by-step disassembly workflow for verifying firmware addresses in Ghidra. Human-driven, interactive. Use before any flash. |
| [FIRMWARE-DECOMPILE-GUIDE.md](./FIRMWARE-DECOMPILE-GUIDE.md) | Agent-driven decompilation reference. 🛑 **Its r2-first prescription is SUPERSEDED — GhidraMCP (`mcp__ghidra__*`) is the only disassembler; never radare2/rizin/objdump.** Read it for the V850 material, not the tool order. Byte-level work (diffs, CRC, table dumps) is Python. Pair with the `.claude/skills/firmware-decompile.md` skill. |
| [GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-2026-07-06.md](./GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-2026-07-06.md) | The full CAN→motor gating map for the gentle-EME investigation (V32–V37 lineage). |
| [SPEC-uds-can-ram-telemetry-a160.md](./SPEC-uds-can-ram-telemetry-a160.md) | Spec for the UDS-over-CAN RAM telemetry insertion point (DID repurposing on the A160 RDBI table) — the basis for V31U/V31T/V31P telemetry builds. |
| [DISCORD-EXPORT-RUNBOOK.md](./DISCORD-EXPORT-RUNBOOK.md) | How to pull scrollback from the community Discord (source for HONDA-EPS-PID-KNOWLEDGE.md). Raw export lives in `../discord-export/`. |
| `EPS System Description 3455.pdf` | Honda EPS system description reference (platform-general engineering doc). |

## Handoff chain (2020 Accord TVA, V9 → V54)

Each handoff supersedes/links its predecessor — read the latest first, walk backward as needed. In rough chronological order:

`HANDOFF-2026-06-02.md` (V24, superseded) → `HANDOFF-2026-06-02-v25-clean.md` → `-v26.md` → `-v27.md` → `HANDOFF-2026-06-03-v28.md` → `-v29.md` → `-v30.md` → `-v31.md` → `HANDOFF-2026-06-29-gentle-eme-v32.md` → `HANDOFF-2026-06-30-sensorA-identity-gate-scale.md` / `-v31t-telemetry.md` → `HANDOFF-2026-07-02-v33.md` → `-07-03-v34.md` → `-07-05-v35.md` → `-07-07-can-tx-swarm-and-visibility.md` / `-gating-map-and-telemetry-plan.md` / `-visibility-resolved-and-ram-telemetry.md` → `-07-08-tier1-telemetry-and-visibility-correction.md` → `-07-10-v31u-uds-telemetry-working.md` → `-07-11-starpilot-eps-telem-rlog-analysis.md` → `-07-12-comma4-uds-live-telemetry-bus-analysis.md` → `-07-13-v31p-gateflags-330-piggyback.md` / `-v31p-v2-gateflags-corrected.md` → `-07-14-v36-debounce-sm-root-cause.md` → `-07-14-v37-dtc0x49-fix.md` → `-07-17-lkas-model-firmware-verification.md` / `-07-17-v38.md` → `-07-18-v39-opposing-torque-rate-guard.md` (superseded draft) → `-07-19-v39-direct-torque-rate-guard.md` → `-07-19-v40-governor-slew-and-rate-cap.md` → `-07-20-session-v40-fault-investigation.md` → `-07-20-v41-ratecap-flat.md` → `-07-20-v42-state4-ratchet.md` (ratchet SOLVED; r26 falsified) → `-07-21-v43-dirty-derivative-pole.md` (pole falsified on-car) → `-07-20-v44-handsoff-damping.md` → `-07-21-v46-v47-vibration.md` → `-07-21-v48-vibration-loopgain-notch.md` → `-07-21-v48b-notch-build.md` → `-07-21-v48b-flashed-catastrophic.md` (☠ bricked, recovered) → `-07-22-v49-stagec-flip-damper.md` → `-07-22-v50-lowpass-ema-cave.md` → `-07-24-v51p-v52-carrier-surface.md` → `-07-24-v52c-complete-broad-lowpass.md` → `-07-24-gate1-fail-newid-fourframe-telemetry.md` → `-07-24-low-speed-steer-lockout.md` (the `0xC62EA` window LOCATED) → `-07-26-route13-vibration-engagement-dependence.md` (the A/B/C split) → `-07-27-fourframe-strb-defect-and-vibration-reframe.md` (FOURFRAME never transmitted; three retractions) → `-07-27-v53-fourframe2-plus-minsteerspeed0.md` (V53 built = FOURFRAME2 + `0xC62EA`→0, and three stale no-speed-gate claims retired from the golden model) → **`-07-27-v53-drive-result-and-v54-authority-probe.md`** (current; V53 FLASHED — steer-to-zero CONFIRMED on-car, four-frame telemetry still silent and the null proven UNINTERPRETABLE; V54 built = the 5-bit `gp-0x6966` authority probe on the `0x14A` piggyback).

⚠ **The single most important thing in this chain is not in the chain.** Read `STATE.md` and
`BUILD-LINEAGE.md` first — the lineage file exists because levers already flashed and falsified were
being re-proposed as new out of these narratives.

See `../CLAUDE.md` for the index and the standing behaviours.

## Adversarial reviews

| Doc | What it is |
|---|---|
| [review-safety-redteam.md](./review-safety-redteam.md) | Safety red-team prompt template — directs the reviewer to critique firmware values, brick risk, and physical safety with no "out of scope" punts. |

## Project conventions

| Doc | What it is |
|---|---|
| [AGENTS.md](./AGENTS.md) | Light agent-collaboration conventions: bd (beads) for issue tracking, the "landing the plane" session-completion workflow. |
- [HANDOFF-2026-07-28-v54-drive-authority-resolved-and-v55-partition-probe.md](HANDOFF-2026-07-28-v54-drive-authority-resolved-and-v55-partition-probe.md) — the V54 drive: the probe fired, authority is ~0 by design (0xC6AF0 unblocked), the vibration at creep moves with speed and dies at the rail, the damper reappraisal withdrawn, and V55 the partition probe.
