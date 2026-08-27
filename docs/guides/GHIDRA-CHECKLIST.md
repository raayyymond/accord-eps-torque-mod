# Ghidra Verification Checklist — 2020 Accord EPS (`39990-TVA-A160`)

Use this checklist once Ghidra is installed (or via GhidraMCP) to rigorously
confirm a disassembly claim before it informs a build. Unlike the kit's
earlier Civic material, there is no single canonical "table map" doc to
check addresses against here — Accord findings live distributed across
`memory/reference_accord_*.md`, `.claude/agent-memory/firmware-codepath-tracer/`,
and the `docs/HANDOFF-*.md` chain. This checklist is the general verification
method; apply it to whichever specific claim you're checking.

## Setup

1. **Install Ghidra** (Windows):
   - Latest release: <https://github.com/NationalSecurityAgency/ghidra/releases/latest>
   - Requires JDK 21+: <https://adoptium.net/temurin/releases/?version=21> (install Temurin first)
   - Unzip Ghidra to `C:\ghidra-11.x\`
   - Run `ghidraRun.bat`

   (If GhidraMCP tool access is already available in this session, you can
   skip local install entirely and use the `mcp__ghidra__*` tools directly
   against the already-open project — check `list_open_programs` first.)

2. **Create/open the project**: File → New Project → Non-Shared Project.
   The kit's existing project is `../accord-firmware/analysis-2020accord/ghidra_project/accord2020_ghidra.gpr`
   — open that rather than starting fresh if it already exists.

3. **Import the stock binary** (skip if `code.bin` is already imported in the existing project):
   - File → Import File → select `../accord-firmware/analysis-2020accord/ghidra_project/code.bin`
   - **Language:** `V850:LE:32:default` — search "V850" in the language picker, select the LE:32:default variant.
   - **Format:** Raw binary.
   - **Base Address:** `0x0` ← unlike the Civic kit, there is no flash-base offset to set here. `code.bin` loads flat at 0x0.
   - Click OK to import, then double-click the file to open in CodeBrowser. Analyze with default analyzers.
   - ⚠ **Known SLEIGH bug:** the base `V850:LE:32:default` module gets `divq reg2==reg3` semantics wrong (computes quotient where the ISA says remainder) — see `memory/reference/tooling/reference_rizin_ghidra_v850_quirks.md`. Don't trust a `divq` result with matching src/dst operands without raw-byte cross-check.

## Verification tasks

### Task 1: Confirm a cal address (`tp+0xNNNN`) is read/written where claimed

For any cal address named in a memory file or handoff (e.g. `0xC64B8`, the
DTC-0x49 fail-counter gate from the V36/V37 lineage):

**Ghidra: `Search → For Scalars → Value: 0xC64B8`** (or use GhidraMCP
`search_functions`/`get_xrefs_to` on the resolved absolute address —
remember `tp+0xNNNN` for the **app** resolves to `0xBF000 + 0xNNNN`, so
`0xC64B8` as a `tp`-relative name is absolute `0xBF000 + 0xC64B8`... — always
state explicitly whether an address you're citing is already absolute or is
a `tp+`/`gp+` offset, and resolve it before searching).

Cross-check the disassembly around each hit looks like the claimed access
pattern (compare-then-branch for a threshold gate, load-then-accumulate for
a counter, etc.) — not just that the immediate value appears somewhere
incidentally (e.g. as part of an unrelated constant).

### Task 2: Confirm a function is LIVE, not dead code

This kit has a documented instance of getting this wrong: `FUN_0002a30e`
and `FUN_0002a93a` both read, at first glance, like the producer of the
`STEER_STATUS` debounce behavior — but a callers/xrefs check found **0
callers on both**. The live logic turned out to be inlined directly in
`m_steer_torque_arbitration`.

- **Ghidra:** right-click the function → **Show References To** (or
  GhidraMCP `get_function_callers`). Zero results = the function is
  unreferenced. Before trusting a function as "the" implementation of some
  behavior, confirm it's actually reachable from the relevant task
  (`w_steer_control_task@0x2214a` for anything steering-related).
- If a function has 0 callers but its logic matches the claimed behavior,
  check whether the SAME logic is inlined elsewhere (diff the candidate
  dead function's decompiled body against the live call site's
  decompilation — near-identical structure is the signature of "this used
  to be a real function, got inlined, and the standalone copy became dead
  code").

### Task 3: Confirm the `gp`/`tp` base resolution at the actual set-site

Before trusting ANY `gp-0xNNNN` or `tp+0xNNNN` address translation, confirm
where the base register is actually set in the binary you're analyzing —
don't assume it matches a prior session's finding without re-checking on
the current program.

- `gp` = `0xFEDF8000` — set once, early boot, both bootloader and app agree.
- `tp` (app) = `0xBF000` — **the bootloader itself sets `tp=0xF8000` at its
  own reset**, but the application overwrites `tp` again early in its own
  init sequence (built via `movhi 0xb` + `movea 0x7000` + a THIRD instruction,
  `add r1(0x8000)`, that's easy to miss if you only look at the movhi/movea
  pair). If you're resolving cal addresses in the app's code region, use
  the app's `tp` value, not the bootloader's — this exact confusion produced
  a wrong "absent partition" conclusion earlier in this project's history
  before being corrected.

### Task 4: Trace the CAN-0xE4 steering handler chain

Walk the chain the way `docs/guides/GENTLE-EME-CAN-TO-MOTOR-GATING-MAP-2026-07-06.md`
already does, and confirm your Ghidra view matches it before extending it:

- Start: find the function receiving CAN ID `0xE4` (Search → For Scalars →
  `0xE4`, or trace forward from the CAN RX ISR).
- Confirm `w_steer_control_task@0x2214a` calls `m_steer_torque_arbitration`.
- Confirm the shaper (`FUN_00042af8`) and float consistency-monitor
  (`FUN_00043e44`) sit downstream, per the existing traces in
  `analysis-2020accord/notes/TORQUE_PATH_AND_TABLE.md` and
  `notes/FUN_00043e44_FLOAT_MONITOR.md`.
- Note any gate/table address referenced in this chain that ISN'T already
  captured in `memory/reference_accord_*.md` or
  `.claude/agent-memory/firmware-codepath-tracer/` — that's a genuine new
  finding, not a re-derivation.

### Task 5: Sanity check on processor/language selection

If Ghidra disassembly looks like nonsense (high `BAD` instruction rate, or
a run of `setf`/`xori` where cal reads are expected):
- Did you select `V850:LE:32:default` and not a generic/wrong variant?
- Did you set the base address to `0x0` (not `0x4000` — that was the OLD
  Civic/SH-2A kit's flash base, not this one)?
- Little-endian — confirm bytes interpret correctly. (V850E2 is LE; the
  Civic's SH-2A was BE — don't carry that assumption over if you've worked
  in the old kit material before.)
- If a function body is a run of `setf`/`xori` where you expect `ld.hu`
  reads, that's the radare2-default-plugin bug (see
  `memory/reference/tooling/reference_rizin_ghidra_v850_quirks.md`), not necessarily a
  Ghidra problem — but check the Ghidra decompile too in case the SLEIGH
  module hit something similar.

## Output artifacts to save

For each verified claim, save:
- The instruction address(es) that reference it (as both the raw absolute
  address AND, if applicable, the `gp-`/`tp-` relative form used in the
  memory files)
- The disassembly or decompiled excerpt of the surrounding context
- A 1-sentence functional description
- Confirmation of caller/xref liveness if a function's behavior is what's
  being claimed (Task 2)

Save findings as a new `.claude/agent-memory/firmware-codepath-tracer/reference_accord_*.md`
memory file (see that agent's memory-saving convention), or propose a
`memory/reference_accord_*.md` file for a fact durable enough to belong in
the main constellation.

## When verification is complete

If the checklist confirms the claim (or surfaces a correction/new finding),
it graduates from "hypothesis" to "disasm-verified" — update the relevant
memory file's confidence language accordingly, and flag the correction to
the operator if it contradicts something already documented as verified
elsewhere (this has happened before in this project's history — corrections
are valuable, not embarrassing, when caught before a flash).
