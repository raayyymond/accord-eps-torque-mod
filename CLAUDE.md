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
   🛑 **HARD CAP 256 KB — keep it under ~150 KB.** It hit 506 KB on 2026-08-09, past the `Read` limit,
   so it could not be loaded in one call and **the tail was silently invisible**. **Update it IN PLACE;
   never append a new dated block — supersede the old one.** Superseded sections go to
   `docs/STATE-ARCHIVE-*.md` (a record, not an instruction), per-build history to `BUILD-LINEAGE.md`.
   **Check its size at every close-out.** The same cap applies to any file an agent must read whole,
   `memory/MEMORY.md` included.
2. **`docs/BUILD-LINEAGE.md`** — every lever that has been flashed, and what it did on-car.
   **Mandatory before proposing any calibration edit.**
3. **The latest `docs/HANDOFF-*.md`** — narrative of the most recent session, and the chain behind it.
   `docs/INDEX.md` lists the full reading order. 🛑 **Results, CIs and retractions live in `STATE.md`
   and the handoffs — NOT here.** This file is an index; keep it that way.
4. **`memory/MEMORY.md`** and **`memory/MEMORY_CONSTELLATION.md`** — the flat fact index and the
   relational layer. The constellation carries the *chains* between facts, which the flat list does not.

Default to study/analysis mode unless told otherwise.

🛑 **EVERY investigation or firmware-fix session must be grounded in the WHOLE chain and the WHOLE
recent record — not just the lever in front of you.** Standing operator instruction, 2026-08-03. Before
proposing or evaluating any lever, and before briefing any subagent that will:
- **`analysis-2020accord/eps_lkas_chain_model.py`** — the golden model, the full driver-assist chain
  end to end. A lever is only understood once you can say where it sits in that chain, what feeds it,
  and what it feeds. **Keep it updated when you learn something.**
- **The entire post-V38 record — V38 → present — as one arc**, via `docs/BUILD-LINEAGE.md` and the
  `HANDOFF-*.md` chain. Not just the latest handoff. A dose-response that only makes sense across four
  builds is the kit's most-used form of evidence, and reading one session's slice has repeatedly
  produced levers that were already flashed, already falsified, or pushed the wrong WAY.
**Prime every subagent with both.** The failure mode this prevents is real and recorded: two agents in
one session re-proposed an already-flashed, already-falsified lever.

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

### 🛑🛑 AGENT ROLL-CALL BEFORE CLOSE-OUT — you do not know an agent has stopped
**Recurring failure, and the operator has had to point it out repeatedly (latest 2026-08-07, twice in
one session): the orchestrator writes the handoff, commits, and reports "done" while subagents are
still running and still changing files.** An agent's last message means *it sent a message* — **not**
that it finished, and **not** that it stopped. Agents keep editing after they report.

**Close-out does not begin until every spawned agent is confirmed stopped.** In order:
1. **`TaskList` / roll-call every agent you spawned this session.** Name them. An agent you forgot is
   the one still writing.
2. Before stopping each one, wait for them to send you a message that they are done. Use SendMessage to prompt them to respond. Be very patient.
3. **`TaskStop` each one.** 🛑 **A `SendMessage` "stand down / you're done" does NOT stop an agent.**
   It will acknowledge and keep working.
4. **Then** `git status` on **both** repos and re-hash every reported artifact. **Confirm from the
   filesystem, never from an agent's reply.**
5. Only then: collaterals → commit → push → report.
If `git status` is dirty *after* you thought you were finished, **assume an agent is live** and go
back to step 1.

**This applies to EVERY agent, not just builders** — tracers rewrite their own agent-memory, analysts
overwrite caches and scripts, designers re-issue specs that contradict the one you just shipped. Any
of them can invalidate a conclusion you have already written into `STATE.md` or reported.

**Corollary — once you have REPORTED something, it is FROZEN.** That covers a build's SHA256 and the
script constants behind it (`OUT` / `TAG` / `BIN_OUT`), but equally a cache an analysis quotes, a
memory file, or a spec another agent is building against.
- **Anything you reported, re-verify from disk at close-out** — re-hash the artifact, re-run the
  script and assert it reproduces bit-for-bit, re-read the file. Agent replies are not evidence.
- **Exactly ONE flashable `.rwd` per build number on disk.** Byte-identical duplicates carry zero
  evidence — delete them. Differing ones get `SUPERSEDED-DO-NOT-FLASH-…`.
- Late findings from any agent are **reports, not licence to act**. Put this in every brief:
  *"If you find a defect after I've accepted your work, report it — do not fix it."*

### What "close out the session" means
A four-part deliverable, every time, without being re-asked:
1. **Update the collaterals** — `docs/STATE.md` (in place, not appended), `docs/BUILD-LINEAGE.md` if a
   lever moved, the golden model `analysis-2020accord/eps_lkas_chain_model.py`, and `memory/` +
   `memory/MEMORY.md`.
2. **Commit and push `main` on BOTH repos** — analysis to the kit, firmware artifacts to `accord-firmwares`.
3. **Write `docs/HANDOFF-<date>-<topic>.md`.**
4. 🛑 **EXPLAIN THE NON-STOCK FIRMWARE MODIFICATIONS, IN THE CLOSE-OUT MESSAGE ITSELF.** Standing
   operator instruction, 2026-08-09. Not a pointer to a file — **in the message.**
   - Enumerate **every cell on the current candidate that differs from STOCK** — the *cumulative* delta,
     not just what this session changed. **Read it from the built image, not from the build scripts.**
   - For **each** changed variable: its address, stock value, current value, **what the variable
     physically is**, **what the change does to the car**, and **which build introduced it**.
   - **Use diagrams, graphs and pseudocode wherever they carry the meaning better than prose** — a
     signal-flow diagram of where the cell sits in the chain, the decompiled arithmetic mirrored in
     integer Python, a before/after table or curve of the delivered surface.
   - State plainly which changes are **measured on-car**, which are **inert or unverified**, and which
     are **carried by accident** (the V38 rebase silently reverted seven levers — see `STATE.md`).
   - This exists because the operator drives the car and must be able to say, from one message, exactly
     what is non-stock about the ECU in it and why.
5. 🛑 **RECORD HOW THIS BUILD'S APPROACH DIFFERS FROM THE RECENT ONES — against the WHOLE arc since
   V38.** Standing operator instruction, 2026-08-09. *"We have been at this for a long time, since V38."*
   - A cell table is not enough. Say **what CLASS of intervention this build is**, and **how that class
     differs from what the last several builds tried**. The arc so far: V38–V52 authority / filters /
   poles / caves · V53–V61 telemetry probes and lane mutes · V62–V73 the rate lane (r24/r26) ·
     V74–V83a the base-assist damper · V84 damper reverted to Honda.
   - **Show it as a cross-build matrix read from the IMAGES** — the same handful of cells down every
     build since V38 — so it is visible at a glance which cells have actually moved and which have been
     frozen for dozens of builds. `analysis-2020accord/ledger_v38_to_v84_bytes.py` is the reader.
   - **Name what is genuinely new versus what is a re-run of an earlier lever in a different direction.**
     🛑 FALSIFIED ≠ INERT-BY-MODE ≠ never-tried, and *"the same lever pushed the other way"* is a
     different claim from *"a new lever"*. If a cell has been frozen across N builds, **say N.**
   - If the build is a re-run, say **what is different this time that makes a different result likely** —
     otherwise it is a repeat, and the operator is entitled to be told that before he drives it.

### Calibration and trust
- The operator's **lived experience overrides analyst recommendations** — if they report how the car
  feels, that beats theoretical dwell-time arguments.
- 🛑🛑 **SCORE BANDS; LET THE OPERATOR SCORE SYMPTOMS. NEVER CALL ANYTHING "FIXED" THAT HE HAS NOT
  CALLED FIXED.** Standing instruction, 2026-08-09, after the orchestrator headlined *"V84 fixed the
  highway ring"* off a 26–31 Hz burst-duty drop and had to be corrected twice —
  *"Not even sure what the ring is. We are working on grinding, vibrating, and ratcheting issues"*, then
  *"None of these have been fully fixed in V84."*
  - **"The ring", "grind #1", "grind #2", "S1…S4" are KIT JARGON for frequency bands.** They are not
    symptoms the operator named. **Report in HIS words** — grinding, vibrating, micro-ratcheting,
    ratcheting, excess friction — and cite the band only as the instrument behind it.
  - **An ABSENCE of a complaint is not a report of improvement.** *"I didn't notice anything odd"* is
    weak negative evidence, never a cure.
  - **A band moving is not a symptom being fixed.** Say "band X moved by Y", and say separately what the
    operator reported.
  - **Never let a secondary instrument win over a primary symptom failure.** If the operator's own
    symptoms failed, that is the headline — put it first, before any measured win.
- Full byte diffs over spot diffs; re-disassemble from the built image before declaring victory.

---

## 🛑 Tool policy — GhidraMCP is the ONLY disassembler

**All disassembly and decompilation goes through `mcp__ghidra__*`. Never radare2, rizin, r2pipe,
objdump, or `disasm_v850.py` (retired).** This binds you *and every subagent* — prime each one explicitly,
because the default instinct is to reach for r2.

GET GHIDRA TO ANALYZE THE ENTIRE .BIN FILE FIRST! NO POINT IN DOING SPOT DISASSEMBLY OF SEARCHES BEFORE THIS.

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

Historical handoffs and `reference_accord_*` memories mention r2 because that is how those findings were
obtained. They stay as written — records, not instructions.

**Ghidra/V850 traps — the full list is the `firmware-decompile` skill; load it whenever a session reads
firmware bytes.** Two are quoted here because they have each cost this kit a wrong answer more than once:
- **Off-by-0x1000 on tp-relative cals has recurred four times.** `tp = 0xBF000`, so `tp+0x6000` is
  `0xC5000` (the risky model-coeff block), *not* `0xC6000`. Anchor against a known value first.
- **`search_instructions` silently undercounts** — it scans only already-analysed instructions and still
  reports `truncated:false`. Confirm every load-bearing count or null with a raw Python LE byte scan.

---

## Repo layout — the parts `ls` won't tell you

`ls` covers the tree. Only these two need saying:
- **`analysis-2020accord/eps_lkas_chain_model.py`** is the **golden reference** — keep it updated.
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

## Separate what you BELIEVE from what you have EVIDENCE for

Firmware RE is a **"no false summits"** domain: a hypothesis that looks right can be wrong in a way that
bricks an ECU. **Mark every decision-bearing claim EVIDENCE or BELIEF**, in your own reports and in every
subagent brief — and give the method behind an EVIDENCE claim so the operator can verify the crux.
"I'm not sure, here's what I'd need to verify" is always acceptable and is the preferred output when you
are not sure.

**Skills:** `firmware-decompile` (Ghidra/V850 traps) — load it whenever a session reads firmware bytes.

