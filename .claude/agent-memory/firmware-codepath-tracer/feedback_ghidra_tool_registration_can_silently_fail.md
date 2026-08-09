---
name: feedback_ghidra_tool_registration_can_silently_fail
description: A GhidraMCP-only session can start with just the static bridge tools (list_instances, connect_instance, check_tools, load_tool_group, debugger_*, import_file) registered — decompile_function/disassemble_function/search_instructions/read_memory etc. never become callable even though the bridge reports them "callable" and load_tool_group("all") reports 195 tools loaded. Check this FIRST, not after planning work around it.
metadata:
  type: feedback
---

**Symptom, observed 2026-08-08/09 (V86-prep session, ghidra-factord)**: `mcp__ghidra__decompile_function`,
`disassemble_function`, `get_xrefs_to`, `search_instructions`, `read_memory`, `list_open_programs`,
`get_current_program_info` all returned harness-level `"No such tool available"` when called directly.
`ToolSearch` for any of these names (individually or via `select:`) returned `"No matching deferred tools
found"` — they are not in the deferred-tool index for the session at all. Yet:
- `mcp__ghidra__check_tools` (itself callable) reported every one of them `"status": "callable"`.
- `mcp__ghidra__load_tool_group("all")` reported `"total_loaded": 195` tools.
- `mcp__ghidra__list_instances` showed an ALREADY-CONNECTED TCP fallback (`connected: true`) with the
  target project (`accord2020_ghidra`) and `code.bin` open — i.e. the underlying Ghidra project state was
  healthy and another agent was plainly using it.
- `mcp__ghidra__connect_instance("accord2020_ghidra")` / `("unknown")` / `(pid)` all failed with
  `"No instance matching 'X' (UDS: 1 found, none matched). Refusing to use any instance's tcp_port"`.

**What DID work, unprompted**: `list_instances`, `connect_instance` (as a call, just not successfully),
`check_tools`, `load_tool_group`, `unload_tool_group`, `list_tool_groups`, `import_file`, and the
unsuffixed `debugger_*` family (`debugger_read_memory`, `debugger_modules`, etc. — NOT the `_2`-suffixed
variants `list_tool_groups` showed under the "debugger" group, which is itself a clue this session's
static manifest predates a bridge update).

**Diagnosis, not confirmed**: this looks like the dynamic Ghidra analysis tools (function/xref/analysis/
program groups beyond the handful of static bridge tools) need a live MCP `tools/list_changed` round-trip
that this particular session's harness connection never received — a per-session registration gap, not a
Ghidra-project or `code.bin`-state problem. The tool doc for `connect_instance` says exactly this should
happen automatically ("After a successful connect the bridge fetches the instance's /mcp/schema and
registers Ghidra analysis tools dynamically... Clients that cache the initial tools/list... must re-list
tools after this call") — but the `connect_instance` call itself never succeeded for me, so I never got
past that step.

**How to apply**: at the START of any Ghidra-heavy session, before planning work around a known-healthy
project, do a cheap round-trip check: `check_tools("decompile_function,read_memory")` (fast, bridge-side)
is NOT sufficient on its own — it can say "callable" while the harness still 404s on the actual call.
**Actually attempt one real call** (e.g. `get_current_program_info` with no args) in the FIRST couple of
turns, not after a lot of planning. If it 404s from the harness itself (not a Ghidra-side error), this is
the same failure mode — report it to whoever briefed you immediately, then fall back to Python byte-level
work (which is unaffected) rather than burning turns retrying `connect_instance` with different arguments;
none of the variants I tried worked and I don't have evidence any would.

**What this session did instead, successfully**: fell back to Python LE byte reads of the plain images
(`stock_fw_dump/code.bin`, `_vNN_..._plain_image.bin`) for every claim that was byte-level (table values,
cal values, pointer-chase censuses), and cited prior-session Ghidra decompiles (from the SAME investigation,
same day) for anything structural, clearly labeling what still needed a fresh decompile to close. This
produced a genuinely useful report, but it is a fallback, not equivalent to having Ghidra — flagged
several items in the close-out as needing `disassemble_function`/`decompile_function` specifically.

Related: [[feedback-ghidra-mcp-only-no-rizin]] (repo memory, the policy this doesn't override — the fix
for a broken connection is to get GhidraMCP working, never to reach for r2 instead).
