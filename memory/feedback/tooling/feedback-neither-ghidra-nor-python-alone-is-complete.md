---
name: feedback-neither-ghidra-nor-python-alone-is-complete
description: "For ENUMERATION, Ghidra and a Python byte scan each have a blind spot the other covers, and operand-text search cannot see register-indirect writes at all. Run both, set-difference the results, adjudicate every disagreement."
metadata:
  type: feedback
---

🛑 **Standing rule, 2026-08-10: no single tool can enumerate a cell's accessors on this image. Run both,
set-difference them, and adjudicate every disagreement — a silent agreement is not a confirmation if the
two methods share a blind spot.**

## The three blind spots, each demonstrated

**1. Ghidra undercounts, and reports `truncated: false` while doing it.** [EVIDENCE]
`search_instructions` scans only **already-analysed** instructions. One census returned **73 `ld.h` hits
with `truncated: false`** against **3 more real sites** living in regions Ghidra had not analysed. The
flag is about the *result buffer*, not about coverage — it is not a completeness claim and must never be
quoted as one.

**2. A naive Python scan undercounts the other way — the 6-byte extended-displacement form.** [EVIDENCE]
gp-relative accesses have **two encodings**, and a disp16-only scan is blind to the long one:

```python
# the 6-byte form's displacement is NOT a plain 16-bit field:
disp = (sext16(hw2) << 7) | ((hw1 >> 4) & 0x7F)
```

Every disp16-only census in this kit's history is therefore a **lower bound**, not a count
([[accord-gp4f60-two-encodings-enumeration-trap]], [[accord-v850-scan-traps-formatv-and-storezero]]).

**3. 🛑 Operand-TEXT search cannot find register-indirect writes AT ALL.** [EVIDENCE] A live writer of
`gp-0x1514` exists whose operand text never contains the string `1514`:

```
movhi -0x121, r0, r18      # r18 = base; the address is FORMED, never spelled
clr1  0x1, 0x6aec[r18]     # <-- writes gp-0x1514. Grep for "1514" returns nothing.
```

⇒ **"zero writers" from a text search is not a null.** Any register-indirect path — `movhi`/`movea` pairs,
a base register loaded from a table, a pointer chased through `0xCBE74` — is invisible to it. This is the
blind spot both other methods share, and it is the one that has produced confident wrong "0 writers"
answers.

## How to apply

1. **Ghidra first, for STRUCTURE** — `decompile_function` / `analyze_function_complete`, then
   `get_xrefs_to` / `search_instructions` ([[feedback-decompile-first-then-assembly]]).
2. **Python second, for COVERAGE** — a raw little-endian byte scan over the whole image implementing
   **both** gp encodings, plus LE32 literals and `movhi`/`movea` pairs.
3. **Set-difference the two.** Ghidra-only hits are usually operand-literal collisions
   ([[reference_accord_search_instructions_overcounts_address_literals]]); Python-only hits are usually
   real sites in unanalysed regions. **Adjudicate each one by hand — do not average.**
4. **For a NULL, add the register-indirect sweep explicitly**: enumerate `movhi`/`movea` base loads whose
   resulting base ± the instruction's displacement lands on the cell. A null without this step is a
   BELIEF, not EVIDENCE — and GATE 1 RAM-ownership decisions rest on exactly this null
   (`gp-0x1500` passed both static methods and still failed on-car).
5. **Report which method produced which hit**, so the crux is checkable.

⊕ This is the ENUMERATION twin of [[feedback-verify-with-ghidra-and-bytes-both]] (which covers *build
verification*), and it is why [[feedback-a-count-is-not-a-physical-fact]] insists a count get a second
independent method. See also [[feedback-displacement-grep-misses-reused-ghidra-variable]] and
[[feedback-ghidra-mcp-only-no-rizin]].
