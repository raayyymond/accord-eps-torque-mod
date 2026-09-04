---
name: feedback-the-odd-even-displacement-parity-trap-decodes-a-neighbouring-cell
description: 2026-09-03/04. A V850 gp-relative displacement whose low bit differs by one decodes to a DIFFERENT CELL, and the tooling will not warn you - three instances in one session. 14 flagged accesses to gp-0x683c ALL decoded to gp-0x683b (so "Lever B is unreachable" stands, now re-verified on the flown image with a positive control); gp-0x674d vs gp-0x674e (the variant selector); and the ld.bu opcode field 0x3c vs 0x3d, where an ODD displacement changes the opcode itself. ALWAYS re-read the byte and check the parity before believing a hit list, and ALWAYS run a POSITIVE CONTROL - a cell you know is accessed - through the same query. Related and equally recurrent: the tp off-by-0x1000 trap (tp = 0xBF000, so tp+0x6000 is 0xC5000 NOT 0xC6000) has now recurred SIX times, and search_instructions silently undercounts unanalysed regions while still reporting truncated:false, so confirm every load-bearing count or null with a raw Python little-endian byte scan.
metadata:
  type: feedback
---

# The odd/even displacement parity trap — a one-bit difference decodes a different cell — 2026-09-03/04

**Three instances in a single session**, each of which nearly shipped a wrong conclusion:

| believed | actually decoded | what it would have cost |
|---|---|---|
| `gp-0x683c` (Lever B), 14 flagged accesses | **all 14 were `gp-0x683b`** | would have re-opened a lever that has never done anything |
| `gp-0x674e` (variant selector) | `gp-0x674d` in the mis-read | wrong selector chain |
| `ld.bu` opcode `0x3c` | `0x3d` for an ODD displacement | the opcode field itself changes with displacement parity |

**Why:** on V850 a gp-relative displacement's low bit is not free — an odd displacement changes both the
cell addressed *and*, for some load forms, the opcode field. Neither Ghidra's operand-text search nor a
naive Python scan flags the difference; the hit list looks clean.

## The rule

🛑 **Re-read the byte and check the parity before believing any displacement-based hit list.**
🛑 **Run a POSITIVE CONTROL through the same query** — a cell you already know is accessed. If the
control does not come back, the query is broken, not the firmware. This is how "Lever B is unreachable"
was re-verified on the *flown* image rather than merely re-asserted; see
[[accord-lever-b-is-unreachable]].

## The two companions it travels with

- 🛑 **The tp off-by-0x1000 trap has now recurred SIX times.** `tp = 0xBF000`, so `tp+0x6000` is
  **`0xC5000`** (the risky model-coefficient block), *not* `0xC6000`. Anchor against a known value first.
- 🛑 **`search_instructions` silently undercounts** — it scans only already-analysed instructions and
  still reports `truncated:false`. It missed `0x2A892` and `0x2A8A2` entirely this session. **Confirm
  every load-bearing count or null with a raw Python little-endian byte scan**, and set-difference the
  two tools rather than taking either on trust. Operand-text search cannot see register-indirect writes
  at all.

Related process note: [[feedback-a-check-that-condemns-the-flown-build-is-broken]],
[[feedback-search-the-kit-before-naming-a-cause]].
