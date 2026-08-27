---
name: firmware-iteration
description: The standing operator doctrine for a deep firmware iteration session on the 2020 Accord EPS kit — how to orchestrate and brief subagents, roll-call before close-out, ground a lever in the whole post-V38 arc, design a build that one short symptomatic drive can interpret, budget the live-telemetry cave bits, report symptoms in the operator's words, and the five-part close-out contract. Load BEFORE proposing or evaluating any calibration lever, cutting or building firmware, designing a probe or code cave, spawning subagents for tracing work, reporting on a drive, or closing out a session — and whenever the operator says "orchestrator".
---

# Deep firmware iteration — orchestration, build design, and close-out

Standing operator instructions for the 2020 Honda Accord EPS kit. **Everything here is binding for the
rest of the session once loaded.** `CLAUDE.md` keeps the index, the non-negotiable safety rules, the
GhidraMCP tool policy, the repo layout and the EVIDENCE/BELIEF rule — read it too; this skill does not
repeat them.

---

## 🛑 Ground the session in the WHOLE chain and the WHOLE recent record

🛑 **EVERY investigation or firmware-fix session must be grounded in the WHOLE chain and the WHOLE
recent record — not just the lever in front of you.** Standing operator instruction, 2026-08-03. Before
proposing or evaluating any lever, and before briefing any subagent that will:
- **The GOLDEN MODEL — the full driver-assist chain end to end.** A lever is only understood once you
  can say where it sits in that chain, what feeds it, and what it feeds. **Keep it updated.** The five
  modules, their dependency order and the 87-symbol / SHA256 verification contract are in `CLAUDE.md`
  under *Repo layout*. **Grep the symbol name, never a line number.**
- **The entire post-V38 record — V38 → present — as one arc**, via `docs/BUILD-LINEAGE.md` and the
  `HANDOFF-*.md` chain. Not just the latest handoff. A dose-response that only makes sense across four
  builds is the kit's most-used form of evidence, and reading one session's slice has repeatedly
  produced levers that were already flashed, already falsified, or pushed the wrong WAY.
**Prime every subagent with both.** The failure mode this prevents is real and recorded: two agents in
one session re-proposed an already-flashed, already-falsified lever.

---

## Orchestrate; delegate the tracing; verify the crux yourself
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

🛑 **BE PATIENT. DO NOT DO THE AGENTS' WORK ALONGSIDE THEM.** As orchestrator you are not the one
working — **let them work for you**, and do not be eager to start work of your own. Wait for each agent
to acknowledge that it expects to be closing out; if it does not answer, **keep waiting** rather than
duplicating its task.

---

## 🛑 TELL EVERY SUBAGENT IT IS A SUBAGENT — and that grandchildren report to the ORCHESTRATOR
Put this in **every** brief, verbatim in substance:
> *"You are a SUBAGENT. I am the orchestrator. Report to me via `SendMessage` — your plain text is
> invisible to me. If you spawn subagents of your own, **brief them to report to the ORCHESTRATOR
> (`main`), not to you**, and tell me you spawned them, with their names."*

**Why — both failure modes were observed on 2026-08-12:**
- An agent's own research subagent **reported to `main`** while its parent sat waiting on it, and a
  second one reported to the parent — so the same findings arrived twice by different routes and the
  parent duplicated work it already had.
- 🛑 **The orchestrator lost the roll-call TWICE**, because it tracked only the agents *it* spawned.
  **Grandchildren are the ones you forget**, and the operator had to point out that agents were still
  running after the orchestrator said two.

**Roll-call mechanics — `TaskList` IS NOT RELIABLE HERE.** It returned *"No tasks found"* while agents
were demonstrably alive. **Use a `TaskStop` on a bogus id (e.g. `__rollcall_probe__`) — its error
message enumerates `Running teammates:` and `Running background agents:`.** That is ground truth.
**Confirm the empty list from the harness, never from an agent's reply**, before close-out.

---

## Check the lineage before proposing a lever
**Grep `analysis-2020accord/build_v*_tva.py` for any calibration address before naming it**, and state its
on-car result. FALSIFIED ≠ untested. See `docs/BUILD-LINEAGE.md`.

## Don't ask to build; clear flags autonomously
Build unflashed RWDs and probes **without asking** — only the flash / CAN / UDS *send* is gated. When a
review returns a FAIL or a flagged residual, **resolve it** (next probe, open trace, fold in the fix,
correct the record) rather than handing back an "a/b/c?" menu.

---

## 🛑🛑 EVERY BUILD MUST BE INTERPRETABLE FROM ONE SHORT SYMPTOMATIC DRIVE
Standing operator instruction, 2026-08-12. **"UNINTERPRETABLE" is not a verdict — it is a DESIGN FAILURE
on our side**, and it is not an acceptable outcome of a drive.

**Exposure is not the operator's job to supply.** In his words: *"the exposure really should not matter.
I can do a couple of tests sure, but if I observe micro-ratcheting or grinding, I am generally going to
stop instantly. No point in continuing that drive if the single thing I'm testing for did not get fixed."*
⇒ **Design for ~15–30 s of engaged, symptomatic frames — one episode.** Route 80 gave 17.2 s; that is
what every future drive will give.

Consequences, binding on every build:
- **A spec whose endpoint needs matched episodes, minutes of exposure, or a cross-build contrast is
  UNBUILDABLE. Do not propose one.** Prefer a **WITHIN-FRAME / within-episode decomposition** that reads
  out during the symptom itself.
- **Diagnose the symptom while it is happening**, rather than scoring a lever across drives. The record
  earns this: **nothing has moved micro-ratcheting or ratcheting in sixty builds**, and only V62 and V88
  ever produced both a measured change and an operator report of improvement.
- The operator reasons from **steering angle, driver-side torque, and LKAS demand** — all already free on
  the wire. **Cave bits must COMPLETE that picture, not duplicate it.**
- 🛑 **Before cutting, write the sentence a null will license.** If the honest answer is *"we would not be
  able to tell,"* **the build is not ready — fix the instrument first.** V97 is the case study: a pole
  with DC gain 1.000000 at every value, so no amplitude statistic could ever see it, and no phase or
  group-delay observable was pre-registered.

---

## 🛑 Live telemetry is part of EVERY build — design it deliberately
Before cutting any firmware, **think first about what every prior build has already observed** — read and
**cite** the real record (`BUILD-LINEAGE.md`, the `HANDOFF-*` chain, `memory/`); **do not hallucinate it,
the history is rich and specific.** Only after that deliberate review, ask: **what data on the live
telemetry would be worth the most right now?** Then budget the cave bits for it. **Live telemetry is a
CRUCIAL aspect of every single build** — a lever with no instrument on it produces an uninterpretable
null (V64, V68, V92).

🛑 **THE DESIGN LAW, from all 45 probe builds V53→V97:**
> **Every probe that DECIDED something was a SIGN BIT PAIRED WITH A MAGNITUDE CHANNEL, or a
> deliberately-designed CONTROL. Every UNINTERPRETABLE null was a SINGLE THRESHOLD RUNG on a quantity
> with no measured distribution and no positive control.**

⇒ Do not spend a rung on a bare threshold against a quantity whose distribution you have never seen.
**Size every field against its OWN lane's reachable output** — not a downstream clamp or a writer's
clamp, which are gates (GATE 3; V96 violated this and under-used its channel ~4×).

⭐ **AND THE WAY OUT OF THE SIZING PROBLEM ENTIRELY — COMPARE, DON'T MEASURE.**
> **When you do not know a signal's scale, do not QUANTISE it — COMPARE it.** A comparator rung
> (`|A| ≥ |B|`) is **immune to UNDER-RANGED and OVER-RANGED by construction**: no LSB, no ceiling, no
> assumed distribution. It compares at full precision **inside the cave, before quantisation exists**,
> and its **duty is the answer.**

V96 lost a whole channel to a 34× over-range *guess*; a comparator could not have failed that way.
Two comparators rank three terms per frame with **no scale assumption at all**. ⚠ Buildability note:
V96's flown cave used `r6`/`r7` only with **single-operand** rungs; a comparator is two-operand, so
either recompute the operand inside each rung (+~20 B, keeps the proven discipline) or prove a third
scratch register dead at the hook (a new liveness claim). **Prefer the first.** And note the kit has
usually *known* at cut time — V86's docstring says outright *"THE PROBE CANNOT SCORE `0xC40D4` IN
FORCE"*, and **V80 flew after its own docstring said it could not discriminate itself from V79 at the
flown speeds.** The knowledge was there; the gate was not. **Make it a gate.**

---

## Calibration and trust
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

## 🛑🛑 AGENT ROLL-CALL BEFORE CLOSE-OUT — you do not know an agent has stopped
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

---

## What "close out the session" means
A four-part deliverable, every time, without being re-asked:
1. **Update the collaterals** — `docs/STATE.md` (in place, not appended), `docs/BUILD-LINEAGE.md` if a
   lever moved, the golden model `analysis-2020accord/model/eps_lkas_chain_model.py`, and `memory/` +
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
     frozen for dozens of builds. `analysis-2020accord/studies/ledger/ledger_v38_to_v84_bytes.py` is the reader.
   - **Name what is genuinely new versus what is a re-run of an earlier lever in a different direction.**
     🛑 FALSIFIED ≠ INERT-BY-MODE ≠ never-tried, and *"the same lever pushed the other way"* is a
     different claim from *"a new lever"*. If a cell has been frozen across N builds, **say N.**
   - If the build is a re-run, say **what is different this time that makes a different result likely** —
     otherwise it is a repeat, and the operator is entitled to be told that before he drives it.
