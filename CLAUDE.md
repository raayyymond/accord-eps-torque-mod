# 2020 Honda Accord EPS Firmware Analysis Kit — Agent Context

Reverse-engineering kit for the 2020 Honda Accord EPS firmware (`39990-TVA-A160`, Renesas V850E2).

**This file is an INDEX and a statement of KEY BEHAVIOURS. It is deliberately short.** Detail lives
behind the pointers below — read what your task needs, not everything. Operator instruction, 2026-07-27:
*keep it this way.* When you learn something durable, put it in `docs/STATE.md`, a `docs/HANDOFF-*.md`, or
`memory/` — **do not grow this file with narrative or dated status blocks.** That is exactly what made the
previous 704-line version unreadable, and it had a measurable cost: two agents in one session re-proposed
an already-flashed, already-falsified lever because the result was buried in prose.

🛑 **The deep-iteration doctrine moved OUT of this file on 2026-08-21 — it is the `firmware-iteration`
skill.** Orchestration, subagent briefing and roll-call, the build/telemetry design laws, symptom
reporting and the five-part close-out contract all live there. **New standing instructions of that class
go in the SKILL, not here.**

---

## 🛑🛑 LOAD THE `firmware-iteration` SKILL BEFORE DOING ANY OF THIS

**Mandatory, not optional. Load it FIRST if the session will:**
- propose, evaluate or build **any** calibration lever, probe, code cave or firmware image;
- **spawn subagents** for tracing, enumeration or analysis;
- **report on a drive**, score a band, or say anything about how the car behaves;
- **close out** — collaterals, commit/push, handoff, the non-stock delta message;
- or whenever the operator says **"orchestrator"**.

It carries the standing instructions that have each cost this kit a wrong answer or a wasted drive:
grounding a lever in the whole post-V38 arc · *"tell every subagent it IS a subagent"* · the roll-call
before close-out · *every build must be interpretable from ONE short symptomatic drive* · the probe
design law · *score bands, let the OPERATOR score symptoms*.

**Prime every subagent with it too.**

---

## 🛑🛑 EVERY MANDATORY FILE BELOW MUST STAY ≤ 256 KB — SPLIT IT AND REPOINT HERE IF IT GROWS
Standing operator instruction, 2026-08-12. **A file past the `Read` limit loads with its tail SILENTLY
TRUNCATED and no warning** — `STATE.md` hit 506 KB and its tail was invisible; the golden model hit
310 KB and any agent told to "read the golden model" was getting a cut-off file without knowing.
**Check sizes at every close-out.** If a file exceeds the cap, **split it into multiple files and
repoint this index at all of them** — do not leave a pointer to a file that cannot be read whole.

## 🛑 READ FIRST, IN THIS ORDER

1. **`docs/STATE.md`** — the living current state: what is on the car, what is built and unflashed, the
   open workstreams, and the recommended next steps. **Always read this.**
   🛑 **HARD CAP 256 KB — keep it under ~150 KB.** It hit 506 KB on 2026-08-09, past the `Read` limit,
   so it could not be loaded in one call and **the tail was silently invisible**. **Update it IN PLACE;
   never append a new dated block — supersede the old one.** Superseded sections go to
   `docs/archive/STATE-ARCHIVE-*.md` (a record, not an instruction), per-build history to `BUILD-LINEAGE.md`.
   **Check its size at every close-out.** The same cap applies to any file an agent must read whole,
   `memory/MEMORY.md` included.
2. **`docs/BUILD-LINEAGE.md`** — every lever that has been flashed, and what it did on-car.
   **Mandatory before proposing any calibration edit.** 🛑 **THREE FILES:** this entry file (RULES,
   struck levers, Parts 2–4) · `docs/BUILD-LINEAGE-PART1-LEVER-INDEX.md` (the lever index — **grep it
   by address**) · `docs/BUILD-LINEAGE-CATCHUP-V76-V100.md` (the per-build ledger, V76→V100).
   ⚠ *"Part 2"* still means the **code-cave section inside the entry file** — it did not move.
3. **The latest `docs/handoffs/<YYYY-MM>/HANDOFF-*.md`** — narrative of the most recent session, and the chain behind it.
   `docs/INDEX.md` lists the full reading order. 🛑 **Results, CIs and retractions live in `STATE.md`
   and the handoffs — NOT here.** This file is an index; keep it that way.
4. **`memory/MEMORY.md`** — 🛑 **PAGINATED IN SEVEN: read `MEMORY-PART2.md`, `MEMORY-PART3.md`, `MEMORY-PART4.md`, `MEMORY-PART5.md`, `MEMORY-PART6.md` AND `MEMORY-PART7.md` too**
   — the notes themselves are nested one level below (`memory/accord/`, `memory/reference/`, `memory/feedback/` …);
   the indexes carry the full relative path, so follow the link rather than guessing the folder
   — and **`memory/MEMORY_CONSTELLATION.md`**: the flat fact index and the
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

## Git — work directly on `main`, both repos

Work on `main`; no per-task feature branches. **Two repos, both pushed to `main`:**
- **`accord-eps-torque-mod`** (this kit) — analysis, build scripts, docs, memories, golden model.
- **`accord-firmwares`** (`../accord-firmwares`, `git@github.com:raayyymond/accord-firmwares.git`) —
  **push every new firmware artifact here**: built `.rwd` files and `_*_plain_image.bin` snapshots.
  Standing instruction, 2026-07-27. These are gitignored in the kit repo and live only in that repo.

---

## 🛑 Tool policy — GhidraMCP is the ONLY disassembler

**All disassembly and decompilation goes through `mcp__ghidra__*`. Never radare2, rizin, r2pipe,
objdump, or `disasm_v850.py` (retired).** This binds you *and every subagent* — prime each one explicitly,
because the default instinct is to reach for r2.

GET GHIDRA TO ANALYZE THE ENTIRE .BIN FILE FIRST! NO POINT IN DOING SPOT DISASSEMBLY OF SEARCHES BEFORE THIS.

🛑 **`save_program`/`save_all_programs` before closing or switching a Ghidra program** — analysis,
labels and comments made this session live only in memory until saved; close without saving and they
are gone.

🛑 **WORK BACKWARDS: DECOMPILE FIRST, THEN READ THE ASSEMBLY.** Standing operator instruction,
2026-08-04. Start from `decompile_function` / `analyze_function_complete` to get the **structure** —
what the function computes, which branch is which, what feeds what — and only then drop to
`disassemble_function` / `disassemble_bytes` to pin the exact instruction, encoding or byte. **Never
build an understanding upward from raw assembly.** This kit makes materially more mistakes that way,
and they are the expensive kind: a mis-decoded condition nibble or displacement reads as a *fact*, not
as a guess, and it propagates. Recorded instances — a `jarl` Format-V mask bug returning zero hits for
functions Ghidra had just given callers for; `ba05`/`b205` (`bne` vs `be`) inverting a probe rung's
meaning; `hw2 = (disp | 1)` and the odd-displacement `0x3D`-vs-`0x3C` opcode field; and (2026-08-04) an
orchestrator hand-decoding a cave from bytes and nearly declaring a correct build broken, when the
decompile showed the structure — a 5-bit accumulator plus one `shl 0x3` — at a glance.
⇒ **Assembly is for CONFIRMING a specific claim you already framed, and for byte-exact build work.
It is not for forming the claim.**

Byte-level work — diffing builds, CRC checks, dumping a table, checking an extent — is **Python** and is
unaffected. Prefer Python for anything that is just bytes; it is also the required second method whenever
a count or a null result is load-bearing.

🛑 **PYTHON IS THE `bin_decompile` CONDA ENV — `C:/Users/dudei/anaconda3/envs/bin_decompile/python`.**
Invoke it as **`python`** (which resolves there) — **never `python3`**, which hits the WindowsApps stub and
pops the Microsoft Store installer instead of running. If `python` also fails, call the full path above, or
`conda run -n bin_decompile python`. **Prime every subagent with this** — it is where numpy/scipy live.

🛑 **RUN PYTHON AND GHIDRA IN PARALLEL — NEITHER IS COMPLETE ALONE.** Ghidra misses unanalysed regions;
a naive Python scan misses the 6-byte gp-relative form; **operand-text search cannot see register-indirect
writes at all**. Set-difference the two and adjudicate every disagreement — do not take the union on
trust or stop at the first tool that answers.

Historical handoffs and `reference_accord_*` memories mention r2 because that is how those findings were
obtained. They stay as written — records, not instructions.

**Ghidra/V850 traps — the full list is the `firmware-decompile` skill; load it whenever a session reads
firmware bytes.** Two are quoted here because they have each cost this kit a wrong answer more than once:
- **Off-by-0x1000 on tp-relative cals has recurred FIVE times** (latest 2026-08-09: `tp+0x74B0` read as `0xC74B0`, inventing lane “weights” for what are 0/1 enable flags). `tp = 0xBF000`, so `tp+0x6000` is
  `0xC5000` (the risky model-coeff block), *not* `0xC6000`. Anchor against a known value first.
- **`search_instructions` silently undercounts** — it scans only already-analysed instructions and still
  reports `truncated:false`. Confirm every load-bearing count or null with a raw Python LE byte scan.

---

## Repo layout — reorganised 2026-08-26

Every folder was flat and untruncatable before; the tree below is the shape now. `ls` any one level
and it fits on a screen.

```
docs/     STATE.md · BUILD-LINEAGE*.md · INDEX.md · AGENTS.md   (the entry docs stay at the top)
          handoffs/<YYYY-MM>/ · traces/ · specs/{,design/} · scoring/ · review/ · research/
          guides/ · archive/{,arc-maps/}
memory/   MEMORY*.md · MEMORY_CONSTELLATION.md   (indexes stay at the top)
          accord/{builds,mechanism,firmware,instruments,calibration,signals}/
          reference/{firmware,builds,measurement,tooling,can}/ · feedback/{process,measurement,tooling,builds}/
          project/ · builds/ · dream/ · misc/
analysis-2020accord/   model/ · lib/ · builds/ · extract/ · verify/ · studies/<topic|sessions/<tag>>/
          notes/ · reference/ · figures/ · sessions/ · archive/ · ghidra_project/ · _scratch/
rlog-tools/            lib/ · decode/ · score/ · probe/ · studies/<topic>/ · archive/ · cereal/ · _scratch/
tools/ · flashing-2020accord/   unchanged
_scratch/ (repo root and one per kit dir)   cache/<route>/ · out/ · data/ · logs/   — gitignored, regenerable
```

🛑 **The kit dirs are import roots, marked by a `.pkgroot` file.** Scripts that import a sibling by
bare name carry a short `PATH BOOTSTRAP` block at the top that walks up to `.pkgroot` and puts the kit
root and every code subfolder on `sys.path`, so they run from any CWD and from any nesting depth.
**Do not delete `.pkgroot`, and keep the block when you move a script.**

🛑 **`__file__`-relative anchors were re-based when the files moved** (`Path(__file__).resolve().parent`
→ `.parents[N]`, one extra `dirname()` per level). If you move a script again, re-base its anchor too.

Only these other things need saying:

- **The GOLDEN MODEL — the full driver-assist chain end to end — is FOUR modules behind a facade.**
  🛑 **SPLIT 2026-08-12 — it was 310 KB, over the `Read` cap, so every agent told to "read the golden
  model" was silently getting a TRUNCATED TAIL.**

  | file | KB | contents |
  |---|---|---|
  | `analysis-2020accord/model/eps_lkas_chain_model.py` | 31 | **FACADE** — re-exports all 87 symbols; `import eps_lkas_chain_model` still works unchanged |
  | `analysis-2020accord/model/eps_chain_core.py` | 37 | SECTIONS 0–1 — `Calibration`, containers, helpers |
  | `analysis-2020accord/model/eps_chain_lanes.py` | 119 | SECTIONS 2–3 — CAN intake, torque voter, base assist, boost index, the rate lanes |
  | `analysis-2020accord/model/eps_chain_control.py` | 90 | SECTIONS 4–6 — engage SM, arbitration, mixer/gate, aggregator, governor, analyses |
  | `analysis-2020accord/model/eps_chain_delivery.py` | 33 | SECTIONS 7–9 — EME shaper, lockstep monitor, FOC/PWM, `control_task`, `_self_check`, `_demo` |

  Dependency order is strict and acyclic: `core` → `lanes` → `control` → `delivery`. **Keep it updated.**
  🛑 **VERIFICATION CONTRACT — re-run it after ANY edit to these files:** `import eps_lkas_chain_model`
  must expose **exactly 87 symbols**, and `_self_check()` + `_demo()` stdout must hash to
  **`740f4bcd0534212a0c200a9359b0b4318e1419bea33823d66e2e89c12961102d`** (2,512 bytes).

- 🛑 **CITE BY HEADING OR GREP STRING, NEVER BY LINE NUMBER.** The golden model split on 2026-08-12 and
  `docs/BUILD-LINEAGE.md` + `memory/MEMORY.md` split on 2026-08-21, so every line-number citation
  predating those dates is off. Known casualties — old golden-model cites in `studies/sessions/v77/v77_dose_math.py:20,26,193`,
  `lib/_r5d_lib.py:191`, `builds/v50_v79/build_v62_tva.py:17`, `rlog-tools/probe/decode_v70_probe.py:67`; and in
  `.claude/agent-memory/firmware-codepath-tracer/`: `BUILD-LINEAGE.md:929`→`:831`, `:705`→`:607`,
  `:1170-1198`→`:1072-1100`.

- **External artifact root: `../accord-firmwares`** (note the plural). Python tools honour
  **`ACCORD_FIRMWARE_ROOT`** — the default path in `lib/firmware_paths.py` is stale, so set it:
  `ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares`.
  Holds `analysis-2020accord/` (stock dumps, `_*_plain_image.bin`) and `flashing-2020accord/rwd/`.

---

## Memory conventions

`reference_*` facts of record · `feedback_*` how the operator wants work done · `project_*` in-flight
state · `dream_*` speculative.

If a memory looks stale, **ask before updating**. If you generate a durable fact, propose a new memory
file with the right prefix and add a one-line pointer to `memory/MEMORY.md`.

---

## Separate what you BELIEVE from what you have EVIDENCE for

Firmware RE is a **"no false summits"** domain: a hypothesis that looks right can be wrong in a way that
bricks an ECU. **Mark every decision-bearing claim EVIDENCE or BELIEF**, in your own reports and in every
subagent brief — and give the method behind an EVIDENCE claim so the operator can verify the crux.
"I'm not sure, here's what I'd need to verify" is always acceptable and is the preferred output when you
are not sure.

**Skills:**
- **`firmware-iteration`** — orchestration, subagent briefing and roll-call, build & telemetry design
  laws, symptom reporting, the close-out contract. **Load before any build, lever, subagent or close-out.**
- **`firmware-decompile`** — Ghidra/V850 traps. Load whenever a session reads firmware bytes.
