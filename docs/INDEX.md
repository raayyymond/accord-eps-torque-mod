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

## 🛑 THIS INDEX IS PARTIAL — the authoritative reading order lives elsewhere

**48 handoffs on disk are not listed here**, a drift that predates 2026-08-02. Do not treat absence
from this file as evidence a handoff does not exist — `ls docs/HANDOFF-*.md` is the ground truth.
🛑 **AUTHORITY CHANGED 2026-08-03.** This section used to defer to *"`CLAUDE.md` item 3"*, but that
chain has been removed: `CLAUDE.md` is an index and was carrying 57 lines of dated results and handoff
narrative, against its own stated rule. **The authoritative chain is now THIS section plus
`docs/STATE.md`'s header** — keep both current at every close-out. It lists the current investigative
arc only — the V57→V68 grinding thread — because that is what a next session actually needs.

### The current arc, newest first

- [HANDOFF-2026-08-04-v69-built-speed-shaped-rate-lane.md](HANDOFF-2026-08-04-v69-built-speed-shaped-rate-lane.md) — ★★★ **V69 BUILT, UNFLASHED — the highway lane-change fix.** Deletes the mechanism rather than trimming it: V67/V68's **flat** rate-lane arm delivers its MAXIMUM (**2.4383×**) at highway because a scalar replaces a surface Honda rolls off (3072→2151). V69 reverts the gate (`0x3AA96` `fb`→`c5`) and doubles the low-speed end of the surface itself (`0xD2A7E`/`0xD2A80` 3072→6144, `0xD2ABA`/`0xD2ABC` 2561→5122) ⇒ **2.000× to 10 km/h → exactly 1.000× at and above 50 km/h**, both arms. ★ That 1.000× is **STRUCTURAL** (≥50 km/h reads only rec2/rec3; 12,221-point sweep) and the design is **scale-invariant** on the [OPEN] rate axis. **Max anywhere = exactly 2.000×**, inside the `[stock, V62/V65]` flown-clean bracket. 🛑 The design is **FORCED** — the gate branch is 10 bytes with zero slack and REPLACES the LERP, so *gated AND speed-shaped* needs a 1 kHz cave. 🛑 **~~Design A~~ rejected** on three counts (hump **2.753×** not ~2.45×; swings 2.00×→1.22× across axis scales; only **1.1–1.5×** at |rate| 16–32 deg/s where V62's fix measured LARGEST). ⚠ Costs stated: manual <50 km/h gains the damping; **saturation margin 1.91×→1.63×**, the one metric worse than V68. 🛑 Mechanism **suggestive, not established** (3.334 [1.201, 6.492] inside a [0.33, 3.36] null) — 6 pre-registered predictions, 2 negative controls. Two build traps recorded: a jointly-safe/individually-worse-than-stock edit pair, and three mode variants sharing byte-identical records within 40 bytes.

- [HANDOFF-2026-08-03-v68-flew-the-lane-change-is-28hz.md](HANDOFF-2026-08-03-v68-flew-the-lane-change-is-28hz.md) — ★★★★ **V68 flew, and the lane-change vibration is CAPTURED: a ~28 Hz transient, not grind #2.** Route `4e` seg 33 t = 51.3 s, an openpilot ALC right lane change at 25.93 m/s — bar **1468 counts p-p**, 26–30 Hz envelope **614** (20× route median), lines at 27.73/**28.12**/**28.51** Hz at prominence **100–107**, while **40–49 Hz reads 69 in the same window**. Not wheel order 2 (24.93) or 3 (37.40), not engine order 1 (26.10) or 2 (52.20); ✅ the 37.10/37.49 Hz lines in that same window *are* order 3, so the estimator finds orders when present. ★★★ **The corpus's missing arm is closed** — route `4c` gives **234.8 s disengaged above 20 m/s** against a prior 0.0 s at every cut — and **"only when engaged" is REFUTED at 40–49 Hz** (maneuver/control **2.516 [1.561, 3.701]** engaged vs **2.558 [1.469, 3.747]** manual, each against its own null); the engagement-conditional part is at **18–28 Hz**. 🛑 **Honda's detector stayed at ZERO** (bit5 0/53,991 frames, including through the burst) — but the cell has **never been observed non-zero in this kit**, so there is **no positive control** and `gp-0x67df`'s writer is now verdict-affecting. ⚠ The rate-lane suggestion at 26–30 Hz (**3.334 [1.201, 6.492]**) does **not** clear its own split-half null **[0.33, 3.36]**. 🛑 Three corrections of mine, incl. a withdrawn "engaged-only 28 Hz mode" — **an averaged spectrum compares two routes only if their SPEED DISTRIBUTIONS MATCH**, and the band-centre test is necessary but not sufficient.

- [HANDOFF-2026-08-03-the-detector-was-always-there.md](HANDOFF-2026-08-03-the-detector-was-always-there.md) — ★★★★ **The >50 Hz blindness was OURS, not the car's.** Honda runs a 1 kHz oscillation detector (`FUN_000428d4`) whose input `gp-0x6c2c` is a **band-pass peaking at ~61 Hz** — V67 had been reading it all along, at threshold **5**, where it read 0.000%. **V68 revised** (8 bytes from V67, control path byte-identical) reads it at **1**, plus `gp-0x67df` one rung lower. ★★★ **The microphone's two weightings are a two-point filter bank** and independently place grind #2's acoustic excess at a centroid of **63.5 Hz [54.2, 79.6]** — the first data-based evidence above the ceiling, landing on the detector's own peak with no shared assumption. ★★ Route `4a` **resolved the engaged-creep grind #2** (0 bursts / 158.7 s, P(0) = 0.0005) and grind #1 holds at **0.40 [0.27, 0.58]**. 🛑 **Grind #1 is a torsional column mode that never reaches the chassis** (coherence 0.82–0.88 for grind #2 vs no contrast across 48 grind #1 events) — which is why the IMU never showed its fix. 🛑 The highway symptom is a **well-powered null** below 50 Hz (min detectable 1.61×, both positive controls firing); a pre-registered hypothesis was refuted, and a published 95.5 Hz centroid was retracted (power-vs-amplitude weight error). **Wheel order 3 at highway is RETIRED as an estimator tautology.**

- [HANDOFF-2026-08-02-v67-flew-and-the-highway-grind-is-not-the-rate-lane.md](HANDOFF-2026-08-02-v67-flew-and-the-highway-grind-is-not-the-rate-lane.md) — ★★★★ **V67 flew and is the best build measured.** Grind #1 fixed by a *within-route* gate A/B (engaged 0.524, disengaged 1.055 — suppression in one arm only); creep grind #2 eliminated (0 bursts vs 24 at Kd=2×), though the engaged-creep arm is only 22 s and stays UNRESOLVED. 🛑 The new highway symptom is **not** the rate lane — three-dose null (0.970 / 0.938 vs a [0.73, 1.37] null) with a working 18–22 Hz positive control, and four instruments agree including a **microphone validated at 4.14× on grind #2**. **An arithmetically-correct prediction of mine (2.44× at highway) was refuted and withdrawn**, along with six other claims. Traps recorded: ~~highway 40–49 Hz is **wheel order 3**~~ — 🛑 **RETIRED 2026-08-03, it is an estimator tautology** (`order = f0·CIRC/v` returns ≈3.00 by arithmetic at band centre near 28 m/s; order 2's 1.995 has the same defect, so the two were one tautology counted twice — see the 2026-08-03 handoff) — and a hardcoded `SEGS_2B` hid the only Kd=1 highway baseline for three sessions.
- [HANDOFF-2026-08-01-grind2-is-v62s-own-fix-at-high-frequency.md](HANDOFF-2026-08-01-grind2-is-v62s-own-fix-at-high-frequency.md) — ★★★★ Grind #2 is V62's own fix seen at high frequency: a monotone band response with a crossover at 22–24 Hz (40–49 Hz **11.71×**, p = 0.0003), because `gp-0x4f62` is a 4-sample finite difference whose gain rises with frequency. A filter cannot fix it. The lever is the dead `gp-0x683c` gate — a **one-byte** repoint. ⚠ Its ">8× driver torque" separator is withdrawn (real figure 1.70×).
- [HANDOFF-2026-08-01-v62-flew-and-the-grinding-is-fixed.md](HANDOFF-2026-08-01-v62-flew-and-the-grinding-is-fixed.md) — ★★★★ The kit's first measured fix: 18–22 Hz down 8× at creep, 42× at |rate| 16–32 deg/s. 🛑🛑 r26 is **structurally inert**, so r24 carries the whole rate lane — re-attributing V42/V61/V62.
- [HANDOFF-2026-07-31-v64-the-null-is-on-the-gate.md](HANDOFF-2026-07-31-v64-the-null-is-on-the-gate.md) — the detector never armed: a null on the **gate**, not the hypothesis. The origin of *"decode the probe before reading the result."*
- [HANDOFF-2026-07-31-v61-worse-the-rate-lane-is-the-damper.md](HANDOFF-2026-07-31-v61-worse-the-rate-lane-is-the-damper.md) — V61 made it **worse**, inverting the record: the rate lane is the mode's damper. 🛑 Check which **way** a lever was pushed, not just that it was pushed.
- [HANDOFF-2026-07-31-v60-null-and-the-v52c-fabrication.md](HANDOFF-2026-07-31-v60-null-and-the-v52c-fabrication.md) — V60 null closes the parametric-pump mechanism; and a caveat that had mutated into a result.
- [HANDOFF-2026-07-30-v59-drive-and-the-loop-hypothesis.md](HANDOFF-2026-07-30-v59-drive-and-the-loop-hypothesis.md) · [HANDOFF-2026-07-30-v58-drive-and-the-boost-index-mechanism.md](HANDOFF-2026-07-30-v58-drive-and-the-boost-index-mechanism.md) · [HANDOFF-2026-07-30-v57-drive-two-symptoms-and-v58.md](HANDOFF-2026-07-30-v57-drive-two-symptoms-and-v58.md) — the boost-index/pump arc, and the drive that **separated the two symptoms** (ratchet vs grinding).
- [HANDOFF-2026-07-29-golden-model-distillation.md](HANDOFF-2026-07-29-golden-model-distillation.md) · [HANDOFF-2026-07-29-v57-decouple-and-the-angle-rate-turn.md](HANDOFF-2026-07-29-v57-decouple-and-the-angle-rate-turn.md) · [HANDOFF-2026-07-29-v56-drive-mute-is-null-and-costs-damping.md](HANDOFF-2026-07-29-v56-drive-mute-is-null-and-costs-damping.md) — V56's mute is null **and harmful**; `0xC646C` is a shared sensor scale, not the LKAS gain.
