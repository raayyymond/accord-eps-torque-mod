---
name: reference_accord_2a30e_2b421_is_an_uncalled_twin_island_and_6b4c_carries_lkas
description: "0x2A30E-0x2B421 (4372 B, 6 functions) is an UNCALLED near-duplicate of the live LKAS output path -- zero callers by three methods, positive-controlled. Its 0x2B41C is a DEAD twin of the real gp-0x6b38->gp-0x6b3c forward, which lives at 0x2A2EA in FUN_00028ea6 (gated by cmove @0x2A2C2). Ghidra gap now analysed and SAVED (2086->2090 functions); the census deltas are gp-0x6b38 3->5, gp-0x6b3c 2->3, 0xC646C 5->6, 0xC61B4 4->8, every new site inside the dead island. ADJUDICATED: gp-0x6b4c carries the LKAS lane; gp-0x6ad4 is a DRIVER-TORQUE tracking PID, not the LKAS rate PID."
metadata:
  type: reference
---

# The 0x2A30E–0x2B421 island is a DEAD TWIN, and gp-0x6b4c carries LKAS — 2026-09-13, agent `ghidrafill`

Program `code.bin` (stock, `list_open_programs` confirmed, 3 programs open — `program:` passed
explicitly on every call). Trace: `docs/traces/TRACE-2026-09-13-lkas-lane-to-aggregator-and-ghidra-gap.md`.

## 1. 🛑 THE ISLAND IS UNCALLED — and its 0x2B41C is a DEAD TWIN [EVIDENCE]

`0x2A30E–0x2B421` = 6 functions, 4,372 bytes, **zero callers**:
`FUN_0002a30e` (pre-existing) · `FUN_0002a508` · `FUN_0002a892` · `FUN_0002a93a` (pre-existing) ·
`FUN_0002b070` · `FUN_0002b35a`. Three methods, each controlled:
- Python Format-V (`jr`/`jarl`, opcode field **0x1E**) over the whole image: 3 raw hits, **all
  rejected — every target is ODD** (`0x2b3e9`, `0x2ac83`, `0x2ac41`), i.e. the `prepare` alias.
  Controls 3/3 PASS (`0x22522→0x28EA6`, `0x23276→0x34350`, `0x2291E→0x3AA2C`).
- `get_function_callers` → 0. **Control PASSES**: `FUN_00028ea6` and `FUN_0002b422` both return
  `FUN_0002214a`.
- `get_xrefs_to` → 0 refs to every entry.

🛑 **`0x2B422` and `0x2B57A` ARE LIVE** (both `jarl` from `FUN_0002214a`) and were **already defined
in Ghidra** — so `reference_accord_undefined_live_code_2b422_and_gp6b2c_orphan_writers` is STALE
where it says Ghidra defines no function there, and it wrongly assumed `FUN_0002a30e` was live.
**The live/dead boundary is exactly `0x2B422`.**

⭐ **THE TRAP THIS SETS:** the island is a *separately compiled duplicate* of the live LKAS output
path, same semantics, different register allocation:
```
DEAD  0x2b414 mov 0x0,r15 / 0x2b416 be 0x2b41c / 0x2b418 ld.h -0x6b38 / 0x2b41c st.h r15,-0x6b3c
LIVE  0x2a2bc cmp r0,r13   / 0x2a2c2 cmove 0x0,r1,r16              / 0x2a2ea st.h r16,-0x6b3c
```
Both are `gp-0x6b3c = gate ? T : 0`. **A brief that names `0x2B41C` as "the forward" is naming dead
code.** Same for `FUN_0002a892` @`0x2a8c0–0x2a938`, a clone of live `0x2a1ee–0x2a23c`.
[BELIEF] unwired second variant. ⚠ **Register-indirect dispatch was NOT excluded** — my `jmp [rN]`
scan returned 1,475 hits vs 756 plain `jmp lp`, so the pattern `0x0060|reg` collides and the scan is
not adjudicable. "No direct caller" is EVIDENCE; "dead" is BELIEF.

## 2. The gap, analysed and SAVED [EVIDENCE]

Real hole was **`0x2A508–0x2B421`** (3,866 B), not `0x2A30E–…`: `0x2A504` is
`dispose 0x0,{r20,r22,r24,r26,r28,lp},[lp]`, a return, so `FUN_0002a30e` genuinely ends at `0x2a507`.
Created `FUN_0002a508` (906 B) · `FUN_0002a892` (168) · `FUN_0002b070` (746) · `FUN_0002b35a` (200);
with pre-existing `FUN_0002a93a` (1,846) they sum to **3,866 = exactly the hole. Zero bytes left
undefined.** Functions **2086 → 2090**; instructions **183,576 → 184,512**. `save_program` OK.

**Census deltas — every new site is inside the dead island, so all four are INERT:**

| cell | pre → post | new sites |
|---|---|---|
| `gp-0x6b38` | 3 → **5** | `0x2a934` st.h (2nd writer), `0x2b418` ld.h |
| `gp-0x6b3c` | 2 → **3** | `0x2b41c` st.h (2nd writer) |
| `tp+0x746C` `0xC646C` | 5 → **6** | `0x2a904` — **the site the `firmware-decompile` skill says `search_instructions` misses. It is real, and it is DEAD ⇒ the LIVE reader count is FIVE.** |
| `tp+0x71B4` `0xC61B4` | 4 → **8** | `0x2a910/91e/924/92e` ⇒ live count stays 4, all in `FUN_00028ea6` |

Unchanged: `gp-0x6b3a`, `gp-0x6b94`, `gp-0x6ad4`, `gp-0x6b4c`, `gp-0x6ada`, `tp+0x73E8`,
`tp+0x73EA`, `tp+0x7446`.
⚠ **`tp+0x7CD0` = 0 readers BOTH before and after, and that is CORRECT for the STOCK program** —
`0x2a1ee` reads `0x746c` on stock; the `0xC6CD0` repoint exists only on V57+/V282 images.
**Not a null result — a wrong-image question.**

## 3. ADJUDICATED: `gp-0x6b4c` carries LKAS; `gp-0x6ad4` is a TORQUE tracker [EVIDENCE]

Full `decompile_function(0x3a382)`: `err = clamp(gp-0x4f60 − clamp(gp-0x6ad6, ±cal 0xC6200=8192),
±0x2800)`. **`gp-0x4f60` is the torsion-bar sensor.** The function reads `gp-0x6ac0`, `-0x671a`,
`-0x6a5e`, `-0x6bda`, `-0x6966`, `-0x6a98`, `-0x6ad6`, `-0x4f60`, `-0x6765`, `-0x67f4`, `-0x67fe`,
`-0x3678/367c/3680/3684/3688`, `-0x6752` — **and NOT `gp-0x6b38`/`6b3c`/`6b3a`, nor the rate PID's
`y`.** ⇒ **`gp-0x6ad4` is NOT the LKAS rate-PID output.**

**The live LKAS route, instruction-anchored:**
`0x2a23c st.h -0x6b38` (T) → `0x2a2c2 cmove` gate → `0x2a2ea st.h -0x6b3c` → `0x2b42e ld.h -0x6b3c`
→ clamp ±`0xC61B2` → **`0x2b52c sst.h r12,0x4[ep]` (bytes `8264`)** → `0x2b53e jarl 0x25c32` →
`gp-0x62f8[1]` → slot 1 is **mode 0** (`0xC4124`) → `gp-0x62b0[1]` → `0x2730c st.w -0x3d88` →
`0x276f0 st.h -0x6b4c` → **`0x3aa3e` aggregator, unit weight** → `gp-0x6b94`.
⊕ `0x2b52a sst.h r0,0x2[ep]` (bytes `8104`) writes a **literal zero** into field +2 ⇒ term 0
(`gp-0x6b4a`) gets nothing from LKAS.
⊕ Second, indirect route: `0x3816c` → `0x382d2 st.h -0x6b70` → `gp-0x6ad6` → the PID → `gp-0x6ad4`.

🛑 **WHY THE PREVIOUS TRACER GOT IT BACKWARDS** (`reference_accord_gp671d_arm_inverts_r24_on_v280plus_and_6ad4_vs_6b4c_conflict` §3):
it scanned `FUN_00026c80` across 49 gp cells for LKAS-domain *names* and found none. **The LKAS
command does not enter by a named gp cell — it enters `ep`-relative.** `FUN_00025c32` sets the base
with `movea -0x62f8,gp,ep` (6 sites: `0x25eaa/25f0c/26490/26792/26a74/26ae2`) and the real stores
are `sst.h 0x0[ep]`, which carry **no `-0x62f8` in operand text at all**. Exactly the false-zero
class recorded in [[reference_accord_two_lkas_routes_gp6b4c_bypasses_auth]].
⇒ [[reference_accord_r24_no_lkas_only_fork_gp671d_resolver_domain]] is **RIGHT** on the LKAS
attribution (its "resonance, eliminated V56" label for `gp-0x6ad4` is a stale aside).
⇒ [[reference_accord_aggregator_11term_loop_census_units_and_fork]] is **right in its math** (§7
already has the torque-tracking error); only its shorthand label "PID P+I+D" invites the LKAS
misreading. **Neither file edited — operator adjudicates.**

## 4. Method note worth reusing
**Reject a Format-V hit whose target is ODD.** V850 instructions are halfword-aligned, so an odd
target cannot be a branch destination. That single filter killed all three false "callers" of the
island and is the cheapest available discriminator against the `prepare`/`jr` opcode collision.

Related: [[reference_accord_undefined_live_code_2b422_and_gp6b2c_orphan_writers]] (stale, §1) ·
[[reference_accord_4x_gain_feeds_6b4c_not_term0_and_the_struct_offset_map]] (independently
reproduced here) · [[reference_accord_gp6ad4_engagement_gate_and_36682_closed_loop_math]] ·
[[reference_accord_gp6ad6_eight_terms_and_the_reachability_budget]]
