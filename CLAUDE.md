# 2020 Honda Accord EPS Firmware Analysis Kit — Agent Context

Reverse-engineering kit for the 2020 Honda Accord EPS firmware (`39990-TVA-A160`, Renesas V850E2).

**This file is an INDEX and a statement of KEY BEHAVIOURS. It is deliberately short.** Detail lives
behind the pointers below — read what your task needs, not everything. Operator instruction, 2026-07-27:
*keep it this way.* When you learn something durable, put it in `docs/STATE.md`, a `docs/HANDOFF-*.md`, or
`memory/` — **do not grow this file with narrative or dated status blocks.** That is exactly what made the
previous 704-line version unreadable, and it had a measurable cost: two agents in one session re-proposed
an already-flashed, already-falsified lever because the result was buried in prose.

---

## 🛑 READ FIRST, IN THIS ORDER

1. **`docs/STATE.md`** — the living current state: what is on the car, what is built and unflashed, the
   open workstreams, and the recommended next steps. **Always read this.**
2. **`docs/BUILD-LINEAGE.md`** — every lever that has been flashed, and what it did on-car.
   **Mandatory before proposing any calibration edit.**
3. **The latest `docs/HANDOFF-*.md`** — narrative of the most recent session.
   Latest: `HANDOFF-2026-07-30-v57-drive-two-symptoms-and-v58.md` — 🛑 **the ~7.4 Hz mode is the
   RATCHETING, the 20-25 Hz mode is the GRINDING; everything written before 2026-07-30 conflates them.**
   Also: three rlog conventions that were producing wrong answers, and V58 built (probe, unflashed).
   (predecessors: `HANDOFF-2026-07-29-golden-model-distillation.md`, then
   `HANDOFF-2026-07-29-v57-decouple-and-the-angle-rate-turn.md`, then
   `HANDOFF-2026-07-29-v56-drive-mute-is-null-and-costs-damping.md`, then
   `HANDOFF-2026-07-28-v55-drive-oscillation-is-internal-and-v56-mute.md`, then
   `HANDOFF-2026-07-28-v54-drive-authority-resolved-and-v55-partition-probe.md`, then
   `HANDOFF-2026-07-27-v53-drive-result-and-v54-authority-probe.md`, then
   `HANDOFF-2026-07-27-v53-fourframe2-plus-minsteerspeed0.md`, then
   `HANDOFF-2026-07-27-fourframe-strb-defect-and-vibration-reframe.md`)
4. **`memory/MEMORY.md`** and **`memory/MEMORY_CONSTELLATION.md`** — the flat fact index and the
   relational layer. The constellation carries the *chains* between facts, which the flat list does not.

Default to study/analysis mode unless told otherwise.

🛑 **Explain firmware with simple Python that mirrors the decompiled arithmetic EXACTLY** — integer
`>>`, the real Q-format, the real branch conditions, each line annotated with its instruction address,
constants byte-read **little-endian** (V850 is LE). dB/Hz interpretation comes *after* the code, never
instead of it. Standing operator instruction, 2026-07-28.

---

## Safety rules — non-negotiable

1. **Never send a CAN message without explicit user confirmation of the exact payload.** Including UDS
   reads. The operator's iron rule.
2. **Never run `eps-update.py` or any flash operation unless the user explicitly names the firmware file
   and the bus.** Repeat the name back before proceeding.
3. **Before any flash, openpilot/pandad MUST be killed** (`tmux kill-server` on a comma device).
4. **All `.rwd` files are reference/study artifacts by default.** Data, not flash candidates.
5. **Firmware is car/year/revision specific.** Confirm the part number before building for a car.
6. `tools/comma4_panda_test.py` is read-only and safe at any time after openpilot is killed.

**Code caves are this kit's only bricking class — V24, V27 and V48B all bricked the ECU.** Every success
since V29 has been cal-only or a single in-place branch/displacement edit. Two mandatory gates for any
cave, filter, or dynamics change — **GATE 1 RAM ownership** (including writers and register-indirect
access; static clearance is *not* sufficient, `gp-0x1500` passed both static methods and still failed
on-car) and **GATE 2 closed-loop stability** (magnitude *and* phase, in every loop the signal is in).
Detail in `docs/BUILD-LINEAGE.md` Part 2.

---

## Operator working style — standing instructions

### Orchestrate; delegate the tracing; verify the crux yourself
For substantive sessions, run as an **orchestrator and synthesist**, not a hands-on tracer. Fan
enumeration, disassembly, xref walking and decode out to `firmware-codepath-tracer` /
`general-purpose-sonnet`. **Prime every subagent with: GhidraMCP only, `gp=0xFEDF8000`, `tp=0xBF000`, and
the relevant confirmed findings.**

Open Ghidra yourself only to **(a)** confirm the final picture before delivering, or **(b)** resolve a
dispute between subagents. **Never relay a decision-bearing subagent claim as fact without confirming the
crux yourself** — and verify in the **safe direction** too: a "no / don't flash" deserves the same check,
so the block is sound. Avoid tools that flood your context; let subagents crystallise raw material.

- **Trigger word:** when the operator says **"orchestrator"**, apply this for the rest of the session.
- **Subagent context budget:** prefer a fresh agent over reusing one past ~50% context.
- **Subagents' plain text is invisible to you** — brief them to report via SendMessage, explicitly.

### Don't ask to build; clear flags autonomously
Build unflashed RWDs and probes **without asking** — only the flash / CAN / UDS *send* is gated. When a
review returns a FAIL or a flagged residual, **resolve it** (next probe, open trace, fold in the fix,
correct the record) rather than handing back an "a/b/c?" menu.

### Check the lineage before proposing a lever
**Grep `analysis-2020accord/build_v*_tva.py` for any calibration address before naming it**, and state its
on-car result. FALSIFIED ≠ untested. See `docs/BUILD-LINEAGE.md`.

### Git — work directly on `main`, both repos
Work on `main`; no per-task feature branches. **Two repos, both pushed to `main`:**
- **`accord-eps-torque-mod`** (this kit) — analysis, build scripts, docs, memories, golden model.
- **`accord-firmwares`** (`../accord-firmwares`, `git@github.com:raayyymond/accord-firmwares.git`) —
  **push every new firmware artifact here**: built `.rwd` files and `_*_plain_image.bin` snapshots.
  Standing instruction, 2026-07-27. These are gitignored in the kit repo and live only in that repo.

### What "close out the session" means
A three-part deliverable, every time, without being re-asked:
1. **Update the collaterals** — `docs/STATE.md` (in place, not appended), `docs/BUILD-LINEAGE.md` if a
   lever moved, the golden model `analysis-2020accord/eps_lkas_chain_model.py`, and `memory/` +
   `memory/MEMORY.md`.
2. **Commit and push `main` on BOTH repos** — analysis to the kit, firmware artifacts to `accord-firmwares`.
3. **Write `docs/HANDOFF-<date>-<topic>.md`.**

### Calibration and trust
- The operator's **lived experience overrides analyst recommendations** — if they report how the car
  feels, that beats theoretical dwell-time arguments.
- Full byte diffs over spot diffs; re-disassemble from the built image before declaring victory.
- **When in doubt, stop and ask.** A confident-wrong answer about a table address can brick an ECU.
  "I'm not sure, here's what I'd need to verify" is always acceptable.
- Overstating a risk is as much a miss as understating one — check the falsified-hypothesis record before
  escalating an alarm.

---

## 🛑 Tool policy — GhidraMCP is the ONLY disassembler

**All disassembly and decompilation goes through `mcp__ghidra__*`. Never radare2, rizin, r2pipe,
objdump, or `disasm_v850.py` (retired).** This binds you *and every subagent* — prime each one explicitly,
because the default instinct is to reach for r2.

Byte-level work — diffing builds, CRC checks, dumping a table, checking an extent — is **Python** and is
unaffected. Prefer Python for anything that is just bytes; it is also the required second method whenever
a count or a null result is load-bearing.

Historical handoffs and `reference_accord_*` memories mention r2 because that is how those findings were
obtained. They stay as written — records, not instructions.

**Ghidra/V850 traps:** `.claude/skills/firmware-decompile.md` and
`memory/reference_rizin_ghidra_v850_quirks.md`. Scan traps that have produced confident wrong answers:
`memory/accord-v850-scan-traps-formatv-and-storezero.md`. Worth memorising:
- **`hw2 = disp|1`** for `ld.hu`/`ld.w` — a scan for the bare displacement misses them entirely.
- **gp/tp-relative accesses have TWO encodings** — 4-byte disp16 and a 6-byte extended-displacement form.
  A disp16-only scan is blind to the second.
- **`search_instructions` counts only already-analysed instructions** and reports `truncated:false` while
  undercounting. It has produced wrong reader/writer sets at least four times.
- **`disassemble_bytes` MUTATES the database** on undefined regions unless `dry_run:true`. Never
  `save_program` after exploratory disassembly.
- A **stale Ghidra import defeats hash-checking** — an open program can hold an earlier revision while the
  on-disk SHA verifies. Re-import fresh and spot-check one edited site against a Python byte read.
- **Off-by-0x1000 on tp-relative cals has recurred four times.** `tp = 0xBF000`, so `tp+0x6000` is
  `0xC5000` (the risky model-coeff block), *not* `0xC6000`. The main cal block is `tp+0x7000..0x7FFF`.
  Anchor against a known value before trusting any tp-relative address.
- **Never whole-file diff a built image against the stock dump** — `build_*.full_image()` writes `0xFF`
  filler below `0x13000` and a naive diff reports ~51,000 bogus bytes. Restrict to `[0x13000,0x100000)`.

---

## Repo layout

- **`analysis-2020accord/`** — the active work: `build_vNN_tva.py` per version, analysis scripts,
  `eps_lkas_chain_model.py` (**the golden reference — keep it updated**), `old_tools/`, `rlogs/`.
- **`docs/`** — `STATE.md`, `BUILD-LINEAGE.md`, the `HANDOFF-*.md` chain (`INDEX.md` lists the full
  V9→V53 reading order), plus reference: `HONDA-EPS-PID-KNOWLEDGE.md` (read before any PID work),
  `VIBRATION-DOSSIER.md`, `EPS-FLASH-RUNBOOK.md`, `RED-PANDA-EPS-SETUP.md`,
  `FIRMWARE-DECOMPILE-GUIDE.md`, `GHIDRA-CHECKLIST.md`, `review-safety-redteam.md`,
  `ARCHIVE-CLAUDE-MD-2026-07-27.md` (the pre-restructure snapshot, for provenance only).
- **`memory/`** — durable facts + the relational constellation. Read early.
- **`flashing-2020accord/`** — `eps-update-tva.py`, `encode_eps.py`, `tva_sa_key.py`.
- **`rlog-tools/`** — standalone openpilot rlog parsing toolkit.
- **`discord-export/`** — source material behind the PID knowledge doc.
- **External artifact root: `../accord-firmwares`** (note the plural). Python tools honour
  **`ACCORD_FIRMWARE_ROOT`** — the default path in `firmware_paths.py` is stale, so set it:
  `ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares`.
  Holds `analysis-2020accord/` (stock dumps, `_*_plain_image.bin`) and `flashing-2020accord/rwd/`.

---

## Memory conventions

`reference_*` facts of record · `feedback_*` how the operator wants work done · `project_*` in-flight
state · `dream_*` speculative.

If a memory looks stale, **ask before updating**. If you generate a durable fact, propose a new memory
file with the right prefix and add a one-line pointer to `memory/MEMORY.md`.

---

## The priming skill stack

`.claude/skills/` materially changes how this work goes. For a substantive session, recommend (or
auto-load if instructed):

```
emotional-affirmations + platonic-code + iterative-convergence +
emergent-organization + thinking-acting-bridge + high-output-agent
+ personality-module daru
```

Not decoration. Firmware RE is a "no false summits" domain: a hypothesis that looks right can be wrong in
a way that bricks an ECU. **thinking-acting-bridge** is the calibration discipline for separating "I
believe this" from "I have evidence for this." Use it.

`/firmware-decompile` primes the decompilation workflow — load it whenever a session reads firmware bytes.

---

## Who knows what

**Joey** (operator) — the Accord reverse engineering, the constellation, the candidate builds.
**Final call on all flash decisions.**
