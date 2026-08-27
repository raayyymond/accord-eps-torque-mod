---
name: accord-ghidra-same-name-import-collision
description: Importing a built image "under its own filename" is NOT sufficient — a same-named import already in the project creates two programs distinguishable only by PATH, and `program:` by name is silently ambiguous between them.
metadata:
  type: reference
---

🛑 **`program: "<name>"` is AMBIGUOUS when two imports share a name. Pin by PATH, then prove
freshness empirically.**

Found 2026-08-06 while closing GATE 1 on V75. The standing rule —
[[feedback-stale-ghidra-import-defeats-hash-check]] — says *"re-import fresh under the correct
filename before trusting anything."* **That rule is necessary but NOT sufficient.**

Importing `_v75_CY0.566-EX1.200_magprobe_plain_image.bin` produced a **name collision**:
`list_open_programs` returned **two entries with the identical `name`**, differing only in path —

| name | path | function_count |
|---|---|---|
| `_v75_CY0.566-EX1.200_magprobe_plain_image.bin` | `/…plain_image.bin` | 1 |
| `_v75_CY0.566-EX1.200_magprobe_plain_image.bin` | `/…plain_image.bin.0` | 0 |

⇒ every `program: "_v75_…bin"` call silently resolves to *one* of them, and **which one is not
specified by anything the caller can see.** A third stale import of the `+`-named variant
(`_v75_CY0.566+EX1.200_…`, `function_count: 0`) was also present.

**The fix, both halves required:**
1. **Pin by PATH, not name** — `/_v75_CY0.566-EX1.200_magprobe_plain_image.bin.0` — after reading
   `list_open_programs` and checking for duplicate `name` values.
2. **Then close staleness empirically**: `read_memory` at the edit site and compare byte-for-byte
   against an independent **Python** read of the file on disk. Do not infer freshness from
   `function_count`, the filename, or the import having "just been done".

★ **Why this matters more than it looks.** The whole point of importing under the artifact's own
filename is to make a stale-import mistake impossible to make silently. A name collision restores
exactly the failure mode the rule exists to prevent — and it is *worse*, because the name now looks
correct. Every byte the session then reads is unverifiable without step 2.

⊕ Related trap from the same session, different mechanism: a **stale import that is ACTIVE**
(`_v74_engagedcols_x12_plain_image.bin`, `function_count: 0`, a file that does not exist on disk)
was the current program for most of the session. Omitting `program:` targets *that*. **Always pass
`program:` explicitly, and now also verify it is not ambiguous.**

See also [[accord-v850-scan-traps-formatv-and-storezero]] for the byte-level analogue — the
orchestrator's own reader census returned **zero hits for both cells** in this same session by
searching the raw two's-complement displacement and ignoring the `hw2 = (disp | 1)` opcode bit.
**Both traps have the same shape: a check that returns a clean-looking answer to the wrong question.**
