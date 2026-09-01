---
name: reference-accord-importing-a-built-image-into-ghidra
description: How to verify a built image in Ghidra -- auto-analysis finds ZERO functions on a raw import, create_function is required, and save_all_programs writes every open program
metadata:
  type: reference
---

★★★★ **Importing a built `_plain_image.bin` to check an edit is the only way to turn a hand-decode
into disassembly — but the import gives you NOTHING until you define a function yourself.**

WORKFLOW THAT WORKS (used 2026-09-01 to verify V277's 34-byte packer rewrite):
1. Build into a PRIVATE temp root — run the build script through a harness that monkeypatches
   `plain_image_path`/`RWD_DIR`, so nothing lands in `accord-firmwares`.
2. `import_file` with `language="V850:LE:32:default"`. It reports `auto_analyzed: true` and
   **`function_count: 0`**. `run_analysis` then returns `total_functions: 0` in ~2 ms — a raw binary
   has no entry points, so there is nothing for auto-analysis to seed from. **This is normal, not a
   broken import.**
3. **`create_function` at the address you care about.** It disassembles and walks flow from there.
   Its reported `body_size` is a free integrity check: 430 (0x1AE) for `FUN_00055d80` matches the
   stock extent, which proves the edited bytes did not desynchronise the instruction stream.
4. Then `decompile_function` FIRST, `disassemble_function` second, per the kit's rule.
5. `get_function_jump_targets` cheaply proves no branch lands inside an edited window.

🛑 **FRESH-IMPORT CONTROL — always spot-check `read_memory` at an edited address against a Python
byte read** before trusting anything. A stale program defeats hash-checking (skill: "Tools that lie").

🛑🛑 **`save_all_programs` SAVES EVERY OPEN PROGRAM, not just yours.** If `save_program` on your own
import fails with **"Unable to lock due to active transaction"** (left open by `create_function`),
do NOT reach for `save_all_programs` — it will commit the shared stock/V112/V273 programs to disk,
including any unsaved state another session had. Stop and report the failed save instead; an imported
scratch program is fully reproducible (rebuild, import, `create_function`).

Related: [[reference-accord-clamp-helpers-and-packer-scratch]] ·
[[reference-accord-v850-load-opcode-map-ldhu-0x3e]]
