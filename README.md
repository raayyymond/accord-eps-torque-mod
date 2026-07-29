# 2020 Honda Accord EPS Firmware Analysis Kit

A reverse-engineering reference kit for the 2020 Honda Accord's Electric Power Steering (EPS) firmware — `39990-TVA-A160` (Renesas V850E2). Built for working with Claude Code. Gifted from one tinkerer to another.

This is not a "press button, flash car" kit. It's the working environment of someone who's been deep in this firmware for months — the disassembly notes, the CAN→motor gating maps, the failed hypotheses, the small wins, the priming stack that keeps the agent honest, and the `.rwd` build lineage (V9 through V39) at various stages of validation.

If you're here, you probably already know what EPS firmware modification is for: more steering assist for openpilot / sunnypilot, on a car where stock assist tops out before the lateral controller is happy. The interesting work isn't "make number bigger" — it's understanding *why* a gain increase produces an unintended emergency-manual-EPS (EME) cutout, where the arbitration/shaper/debounce state machines live, and which cal values actually move the needle versus which ones are decoys or dead code.

---

## What's inside

```
accord-eps-torque-mod/
├── README.md                  ← this file
├── CLAUDE.md                  ← agent context (auto-loaded by Claude Code)
├── install.sh / install.ps1   ← platform installers (idempotent)
├── .gitignore
│
├── .claude/skills/            ← the priming stack + task-specific skills
│   ├── emotional-affirmations.md
│   ├── thinking-acting-bridge.md
│   ├── platonic-code.md
│   ├── iterative-convergence.md
│   ├── emergent-organization.md
│   ├── high-output-agent.md
│   ├── personality-module.md + personality-module/  ← includes "daru" preset
│   ├── firmware-decompile.md       ← r2 (preferred) / capstone / Ghidra workflow
│   └── gate-feasibility.md         ← Project Sidecar gate-feasibility analysis
├── .claude/agent-memory/firmware-codepath-tracer/  ← the tracer subagent's own
│                                                       persistent memory store
│
├── memory/                    ← the memory constellation
│   ├── MEMORY.md                       ← index, auto-loaded
│   ├── MEMORY_CONSTELLATION.md         ← relational graph of how facts connect
│   ├── feedback_*.md                   ← how the operator wants work done
│   ├── reference_*.md                  ← firmware/protocol facts of record
│   ├── project_*.md                    ← in-flight build state
│   └── dream_*.md                      ← speculative / exploratory threads
│
├── docs/
│   ├── INDEX.md                       ← start here — recommended reading order
│   ├── HONDA-EPS-PID-KNOWLEDGE.md     ← canonical PID reference (26-day Discord synthesis)
│   ├── EPS-FLASH-RUNBOOK.md           ← step-by-step flashing procedure (rig, not car-specific)
│   ├── RED-PANDA-EPS-SETUP.md         ← primary hardware path
│   ├── GHIDRA-CHECKLIST.md            ← human-driven Ghidra interactive verification
│   ├── FIRMWARE-DECOMPILE-GUIDE.md    ← agent-driven r2 (preferred) + capstone + Ghidra
│   ├── GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-2026-07-06.md
│   ├── SPEC-uds-can-ram-telemetry-a160.md
│   ├── HANDOFF-*.md                   ← the V9→V39 session handoff chain (see docs/INDEX.md)
│   ├── review-safety-redteam.md       ← adversarial pre-flash review template
│   └── AGENTS.md
│
├── analysis-2020accord/      ← the active deep work: build_vNN_tva.py per version,
│                                Ghidra/decompile notes, gating-map docs, old_tools/
│                                (superseded early builds)
│
├── flashing-2020accord/      ← eps-update-tva.py (the flasher) + encode_eps.py +
│                                tva_sa_key.py (SecurityAccess)
│
├── rlog-tools/                ← standalone openpilot rlog parser + signal extractor
│                                 (cereal schema, dcam clipper) — feeds the telemetry
│                                 analysis scripts in analysis-2020accord/
│
├── discord-export/            ← raw scrollback from the Honda EPS tuning community
│                                 (source material behind HONDA-EPS-PID-KNOWLEDGE.md)
│
├── tools/
│   ├── comma4_panda_test.py   ← READ-ONLY CAN access verification (safe)
│   ├── test_obd_mux_steering.py
│   ├── bench_uds_telem_read.py
│   └── ...                    ← CAN sniff / UDS telemetry helper scripts
│
└── .beads/                    ← bd (beads) issue tracker
```

---

## External firmware artifacts

Proprietary firmware artifacts are kept outside this repository under the sibling
root `../accord-firmware` by default. The relative layout is preserved:

- `../accord-firmware/analysis-2020accord/stock_fw_dump/` — raw stock dumps
- `../accord-firmware/analysis-2020accord/ghidra_project/` — Ghidra project and imports
- `../accord-firmware/analysis-2020accord/other bins/` and `../accord-firmware/analysis-2020accord/_*_plain_image.bin` — other firmware images
- `../accord-firmware/flashing-2020accord/rwd/` and `../accord-firmware/flashing-2020accord/archive/` — built and historical containers
- `../accord-firmware/iHDS_rwds/CalibFiles/` — genuine HDS header templates

Python tools honor `ACCORD_FIRMWARE_ROOT`; when it is unset, they use
`../accord-firmware` relative to the repository root. Source code and project
documentation remain in this repository's `analysis-2020accord/` and
`flashing-2020accord/` directories.

---

## Quickstart

```bash
# 1. Clone
git clone <repo-url> accord-eps-torque-mod
cd accord-eps-torque-mod

# 2. Open Claude Code IN the kit directory (this matters — see install output)
claude

# 3. First reads inside Claude Code:
#    - memory/MEMORY_CONSTELLATION.md          (how the facts connect)
#    - memory/MEMORY.md                         (the index of what's known)
#    - CLAUDE.md                                (full current-state narrative)
#    - docs/HANDOFF-2026-07-19-v39-direct-torque-rate-guard.md  (latest handoff)
```

After that, anything goes. Ask the agent what's in `analysis-2020accord/`. Ask it to walk you through the arbitration/shaper chain. Ask it to compare two build versions and explain what changed. The kit is built so an agent opens it cold and is productive in minutes.

---

## The memory constellation

`memory/MEMORY.md` is an index of named facts. Each entry links to a per-fact file (`reference_*.md`, `feedback_*.md`, `project_*.md`, `dream_*.md`). The naming is intentional:

- `reference_*` — firmware/protocol facts of record (e.g., "Accord LKAS torque has a hard ±0x3FFF static-edit ceiling", disasm-verified)
- `feedback_*` — how the operator wants work done (e.g., "lived driving experience overrides analyst recs")
- `project_*` — in-flight build state, supersedes itself as work progresses
- `dream_*` — speculative or exploratory threads, lower confidence

`memory/MEMORY_CONSTELLATION.md` is the relational layer — *how the facts connect*. This is the part that's load-bearing in a way a flat list isn't. Pull it up early in any session and the rest of the kit reads as a coherent investigation rather than a pile of files.

There's a second, separate memory store at `.claude/agent-memory/firmware-codepath-tracer/` — the codepath-tracer subagent's own persistent notes from tracing the Accord's SH-2A/V850E2 disassembly (arbitration chain, CAN TX topology, UDS DID dispatch, etc.). It has its own `MEMORY.md` index.

---

## Recent work (state as of 2026-07-19)

**Flashed and fault-free:** `V38` delivers the 4×-stock LKAS build without dashboard/DTC errors. Remaining feedback separates into a several-Hz hard-turn ratchet and a common tens-of-Hz vibration under high LKAS torque while the wheel moves.

**Built and verified, NOT YET FLASHED:** `V39` suppresses the direct Sensor-B torque-rate lane `r24` for both signs at or above the exact V9 full-scale equivalent (`|LKAS lane|>=417`) while preserving stronger driver input, adaptive lane `r26`, and the complete governor. Strong driver torque moves the wheel quickly without either symptom, contradicting an intrinsic moving-motor torque limit. See `docs/HANDOFF-2026-07-19-v39-direct-torque-rate-guard.md`.

The full V9→V39 lineage (cipher solve, SA-key crack, torque-mod ceiling, soft-EME boost-floor, gentle-EME root cause, UDS RAM telemetry, and hard-turn assist feedback) is documented in the `docs/HANDOFF-*.md` chain — see `docs/INDEX.md` for reading order.

---

## Safety

This is real-vehicle work. Please read this section before doing anything beyond reading files.

**The only safe-by-default tool in this kit is `tools/comma4_panda_test.py`.** It is read-only — it opens the panda, dumps CAN traffic, and exits. It does not transmit. Run it any time to verify your hardware path works.

**Everything else that touches the ECU writes.** `flashing-2020accord/eps-update-tva.py` performs a UDS flash sequence that erases and reprograms the EPS ECU. A failed flash with openpilot still running has been observed to light every error indicator on the dash (recoverable — retry after killing openpilot). A failed flash with the wrong firmware for the wrong car/year/revision has not been characterized and could plausibly require ECU replacement.

**Firmware is car/year/revision specific.** Every `.rwd` in `../accord-firmware/flashing-2020accord/rwd/` is built for `39990-TVA-A160` on the operator's specific 2020 Accord. **Do not cross-flash onto a different part number.**

**The operator's iron rule:** never send a CAN write (including UDS reads) without explicit confirmation of *which* file and *which* parameters. The agent context in `CLAUDE.md` codifies this. Hold the line.

**Flash at your own risk.** No part of this kit is warranted for use on any vehicle. The operator flashes their own car after rigorous validation. You should do the same.

---

## Credits

- **Joey** — the original curator of the agent firmware analysis kit.
- Community PID-tuning knowledge distilled into `docs/HONDA-EPS-PID-KNOWLEDGE.md` came out of a private Honda EPS tuning Discord working group (26 days, 4,989 messages); see `discord-export/` for the raw scrollback.

Use of this work in your own builds is welcomed. Attribution where it makes sense.

---

## License / sharing

Private. Gifted to one person for personal use. Not for redistribution. If you want to share a piece of it with someone else, ask first — there's context about how this work fits into a small community that doesn't always translate to a public release.
