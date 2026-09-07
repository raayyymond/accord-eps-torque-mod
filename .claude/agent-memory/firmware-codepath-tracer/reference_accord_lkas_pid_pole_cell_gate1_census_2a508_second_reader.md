---
name: reference_accord_lkas_pid_pole_cell_gate1_census_2a508_second_reader
description: GATE-1 reader/writer census for the four LKAS-rate-PID filter poles (0xC63E8/EA/EC/EE), the Kd LERP record 0xE511C and its table base 0xCB7D4, on the V282 image. The EMA poles are private to FUN_00028ea6; the OUTPUT-LAG poles 0xC63EC/0xC63EE have a second reader at 0x2A892/0x2A8A2 sharing RAM state gp-0x3d3c -- but that region (0x2A30E-0x2B421) is a DUPLICATE COMPILED COPY with no entry path, so the pole is applied ONCE per tick, not twice. RESOLVED 2026-09-06: GATE 1 now PASSES outright - 0x2A504 is `dispose ..., lp`, a RETURN, so FUN_0002a30e never falls into the block; see reference_accord_gate1_pole_cells_unreachable_dispose_is_a_return. Also: the cal-block CRC, and why 'it writes a cell live code reads' does NOT prove liveness.
metadata:
  type: reference
---

# GATE-1 census: the four LKAS rate-PID poles, the Kd record, and the second reader at 0x2A8xx

Measured 2026-09-03 on `_v282_..._plain_image.bin` (V282), cross-checked against stock `code.bin`.
Method: GhidraMCP for structure (decompile first), raw little-endian Python byte scan as the required
second method, every null paired with a positive control.

## Anchor (the off-by-0x1000 trap did NOT fire)
`tp = 0xBF000`, so `tp+0x73ec = 0xC63EC`. Verified by value: 0xC63E8=923, 0xC63EA=1560, 0xC63EC=992,
0xC63EE=507, 0xC63E6=0 (Ki), 0xC61BC=15360. All four pole cells are **byte-STOCK in V282**
(`9b031806e003fb01`), as are 0xE511C and the whole 0xCB7D4 table.

## Verdict table

| cell | read sites | writes | verdict |
|---|---|---|---|
| `0xC63E8` feedback-EMA a | `0x28F8A` `ld.h 0x73e8,tp,r9` | none | **PRIVATE** to FUN_00028ea6 |
| `0xC63EA` feedback-EMA b | `0x28F86` `ld.hu 0x73ea,tp,r16` | none | **PRIVATE** to FUN_00028ea6 |
| `0xC63EC` output-lag a | `0x2A184` (FUN_00028ea6) **+ `0x2A8A2`** | none | **SHARED** |
| `0xC63EE` output-lag b | `0x2A174` (FUN_00028ea6) **+ `0x2A892`** | none | **SHARED** |
| `0xE511C` Kd record slot 7 | only via the 0xCB7D4 evaluator (register-indirect) | none | shared by design |
| `0xCB7D4` ptr-table base | `0x29E76` (FUN_00028ea6), `0x2AD64` (FUN_0002a93a) | none | **SHARED** |

Full raw census, hw2 in 0x73e8-0x73ef with hw1&0x1f==5, ALL opcodes — exactly six sites, no stores:
`0x28F86 op3f r16` · `0x28F8A op39 r9` · `0x2A174 op3f r7` · `0x2A184 op39 r7` ·
`0x2A892 op3f r10` · `0x2A8A2 op39 r10`. (`ld.h`=op 0x39 encodes hw2=disp; `ld.hu`=op 0x3f encodes
hw2 = disp|1.) A 7th unfiltered halfword hit at `0x7FD5E` adjudicated OUT: preceding hw1=0x7241,
low-5 = 1, not tp.

## 🛑 The second reader, and why every Ghidra scan missed it

`search_instructions operand_pattern="73e"` returned 58 matches, `truncated:false`, 171,746 instructions
scanned — and **did not contain 0x2A892 or 0x2A8A2**. `get_function_by_address 0x2a892` returns
"No function found" in **both** the V282 program and the more-analysed stock `code.bin` (2086 funcs vs
1682). The region is UNANALYSED, so the analysed-instruction scanner cannot see it. Only the raw byte
scan found it. This is a fresh instance of the documented undercount trap and here it **flipped two
verdicts from PRIVATE to SHARED** — see [[reference_accord_tp_relative_xref_blindspot_and_parity_trap_2026-08-12]].

⊕ `get_xrefs_to 0xC63E8` returns "No references found" — the known tp-displacement xref failure.
That null is worthless; discard it, never report it.

## 🛑 RAM ownership: the output-lag STATE is shared too, the EMA state is not

Raw gp-relative scan (`gp = 0xFEDF8000`; scanner controlled on gp-0x6b38 → 7 accesses incl. the cave
read `0xC4B40` and the tap source `0x55DF0`, where search_instructions had found only 3):

- **EMA state `gp-0x3d30`** (0xFEDF42D0): 2 accesses — `ld.h 0x28F7C` / `st.h 0x28FA8`, both in
  FUN_00028ea6. **PRIVATE.**
- **Output-lag state `gp-0x3d3c`** (0xFEDF42C4): **4 accesses** — `ld.h 0x2A178` / `st.h 0x2A1B0`
  (FUN_00028ea6) **and `ld.h 0x2A89A` / `st.h 0x2A8BA`** (the 0x2A8xx function). The second function
  runs the same output-lag filter, on the same RAM state, with the same two cal poles.
- The same function also writes the delivered lane torque cell: `st.h` to `gp-0x6b38` at `0x2A934`
  (`ld.h` at `0x2B418`) — see [[accord-gp6b38-is-the-delivered-lane-torque-and-forwards-to-gp6b3c]].

## 🛑🛑 RESOLVED (same session, follow-up): the 0x2A30E-0x2B421 region is a DUPLICATE COMPILED COPY

The output-lag pole is applied **ONCE per tick, not twice** — the two lag blocks are mutually exclusive
and an edit to 0xC63EC/0xC63EE changes ONE path. There is no `H^2`. Evidence, in order of strength:

1. **Byte-level proof of duplication.** The two dispatch heads are the same instruction sequence, and
   the encodings differ **only in the register field**:
   `0x29322 ld.bu -0x3d38,gp,r10 = 8457c9c2` vs `0x2A508 ld.bu -0x3d38,gp,r6 = 8437c9c2`;
   `cmp 0x5,r10 = 6552` vs `cmp 0x5,r6 = 6532`; `6152`/`6132`; `6352`/`6332`. One source compiled twice
   with a different register allocation. The dispatch is a compare-and-branch ladder ending in direct
   `jr` — **no jump table, so no function-pointer array in either copy.**
2. **The 1 kHz task's complete call list.** `FUN_0002214a` gates on `1 << (gp-0x67fa & 0xf)` and under
   `(uVar2 & 0x930)` calls exactly `FUN_00028ea6(0x11)`, `FUN_0002b422(0x12)`, `FUN_0002b57a(0x13)`.
   All ~60 calls in that task are direct; **not one indirect call**, and none into 0x2A30E-0x2B421.
3. **No address materialisation.** 6-byte `mov imm32,reg` with an immediate in the region: one hit,
   `0x5A366 mov 0x2b000,r8`, adjudicated OUT — it is immediately `st.w r8,0x1044,r17`, a DATA field in a
   config struct, and 0x2B000 is mid-body, not an entry. `movhi 0x0002/0x0003` + low-half pairs: none.
   ⭐ **The halfword `0xA892` (low half of 0x2A892) does not occur ANYWHERE in the image** — no
   `movea`/`mov` immediate can build that address. No absolute dword to 0x2A30E/0x2A508/0x2A93A.
4. The lag is a **convergent tail** in the orphan just as in FUN_00028ea6 — `jr 0x2A890` arrives from
   all nine handler ranges — so the state byte does not select it; the only question was invocation.

🛑 **Do NOT trust a `jmp [reg]` census built by scanning every 2-byte offset.** Mine returned 540 non-lp
"hits" including 46 `jmp [gp]` and 18 `jmp [tp]` — it is dominated by data misread as code. The `jmp lp`
control (735 sites, finds the known 0x5965C) proves the *pattern* and not the *census*. I reported it as
unusable rather than quoting a number.

## 🛑 The "producer of a cell live code reads" inference is UNSOUND — it failed here

I initially accepted, and `loopshape` argued, that the 0x2A508 function must be live because it writes
`gp-0x69b0`, the engagement ramp `FUN_00028ea6` reads at `0x2A1E6`. **False.** Raw census of `gp-0x69b0`
(disp16 0x9650, addr 0xFEDF1650; scanner controlled on gp-0x3d3c → exactly the 4 expected sites):
**FUN_00028ea6 writes it TWELVE times itself** — `st.h` at `0x293AC, 0x293FE, 0x2942A, 0x29494, 0x294B4,
0x2950C, 0x29594, 0x295AC, 0x29656, 0x2969C, 0x29714, 0x2972A` (plus 29 `ld.hu` reads). The PID produces
its own ramp and consumes it within one call.
⇒ **A cell having a writer in suspect code proves nothing if live code also writes it. Census the live
side before arguing liveness from a data dependency.**

Same shape for `gp-0x3d38`: read at `0x29322` (inside FUN_00028ea6) and `0x2A508`; written by st.b at
`0x293A2, 0x293F8, 0x2949A, 0x2957E, 0x2968A, 0x296C8, 0x29702, 0x29720` — all eight inside
FUN_00028ea6. It is the PID's **private internal sub-state byte**, NOT the `gp-0x67fa` one-hot EPS state
the control task gates on.
⚠ Neighbour trap: the `hw2=0xc2c9` `st.b` sites (0x29798, 0x297F6, 0x29822, 0x298CA, 0x2997E, 0x2999E,
0x29A32, 0x2B0B0, 0x2B132, 0x2B150, 0x2B200, 0x2B2A6, 0x2B2DE, 0x2B348) are **gp-0x3d37, a different
cell**. `st.b` uses the full hw2; `ld.bu` carries disp bit 0 in hw1 bit 5. Do not merge them.

## The lag runs UNCONDITIONALLY in FUN_00028ea6 (PID-mirror premise confirmed)
The disengaged/reset `else` branch sets `iVar23 = 0`, `iVar31 = 0x7FFFFFFF`, `iVar34 = 0` and **joins the
engaged path at 0x2A174** with `r12 = S`. So `iVar23 = (0xC63EC * gp-0x3d3c >> 10) + (S * 0xC63EE >> 10)`
executes every tick, S = 0 when disengaged. Output is `state_old + increment`, and `gp-0x3d3c` is then
overwritten with the **increment**, not the output — flagged for the arithmetic owner, not verified here.

## ✅ RESOLVED 2026-09-06 — the residual caveat is CLOSED, GATE 1 PASSES

~~Residual caveat: `FUN_0002a30e` is a live-with-no-discoverable-caller case, so if its entry path is
ever found it may enter the duplicate block too and this conclusion needs revisiting.~~
**STRUCK.** The concern was misplaced and is now disproved, not merely unresolved.

**`0x2A504` — the target of every `jr`/`br` in `FUN_0002a30e` that looked like it "lands next to the
duplicate" — is `dispose 0x0, { r20,r22,r24,r26,r28,lp }, lp`: a function RETURN.** `dispose` with `lp`
as its destination pops the frame and jumps to the link register, so control **never falls through**
from 0x2A507 into the dispatch head at 0x2A508. Ghidra's function bound is correct here.
⇒ **`FUN_0002a30e`'s liveness is irrelevant to the duplicate block.** The two are unconnected.

A 7/7-positive-controlled branch scan (45,821 branches) then found **zero** real entries into
`[0x2A508, 0x2B422)` from outside — the three raw hits were all `prepare` prologues, one of them the
entry of the 100 Hz task — and no immediate, pointer or `movhi`/`movea` pair anywhere in the image can
construct `0x2A508` or `0x2A890`.

⇒ **GATE 1 PASSES for `0xC63EC` and `0xC63EE`: an edit changes exactly ONE lag filter, the live one at
`0x2A174`/`0x2A184`. No `H^2`.** Full proof, and the one route left bounded rather than closed
(Format-XI `jarl [reg]` dispatch), in
**[[reference_accord_gate1_pole_cells_unreachable_dispose_is_a_return]]** — read that file, not this
paragraph, for the current verdict.
⚠ The scan trap that nearly inverted this verdict is
[[reference_accord_v850_prepare_collides_with_jr_jarl_in_format_v_scans]].

The `gp-0x3d3c` (0xFEDF42C4) wire tap — 4 accesses, 2 live and 2 in the orphan, written once per tick
if the orphan is dead and twice if it runs — is **no longer needed to decide GATE 1**. It survives only
as the cheapest way to close the Format-XI residual empirically, should anyone want that.

## Historical note — the original (now superseded) liveness paragraph

A raw `jarl` disp22 scan (opcode field 0x1E in hw1 bits 6-10; 11,317 decoded; **3/3 positive controls
PASS** — 0x28EA6←0x22522, 0x34350←0x23276, 0x3AA2C←0x2291E, exact callers, no extras) finds **zero**
callers into 0x2A30E-0x2B400. Ghidra's own caller/xref engine on stock agrees for the two functions it
does define there (FUN_0002a30e, FUN_0002a93a).

**That is NOT evidence of dead code in this neighbourhood.** `FUN_0002a30e` (0x2a30e-0x2a507) produced
the identical null on 2026-07-13 by both methods, and it is demonstrably LIVE — it is the STEER_STATUS=4
debounce/hold machine whose output is observed on CAN 399 with ~99 ms durations. It must be reached by
an indirect call, and that link is still open. See
[[reference_accord_fun2a30e_steerstatus_debounce_statemachine]].
⇒ **In the 0x2A3xx-0x2B4xx range, a zero-jarl-caller result is a known false negative.** I made exactly
this over-reach and had to retract it the same session.

Untested and still open: `jarl [reg]` / `jmp [reg]` Format-XI dispatch (no encoding control available).
A disp32 caller test and a function-pointer-dword test were both run and **DISCARDED as uncontrolled** —
the known-live control 0x28EA6 returned NONE for each, so neither can distinguish live from dead.

## The Kd LERP family — 0xCB7D4 / 0xE511C

Table at `0xCB7D4` is dword pointers, stride 0x14 within groups of 6, +0x1000 between groups:
0xE4108, 0xE411C, 0xE4130, 0xE4144, 0xE4158, 0xE416C, 0xE5108, **0xE511C**, 0xE5130, …
Slot 7 = 0xCB7D4+0x1C = 0xCB7F0 → 0xE511C; `get_xrefs_to 0xE511C` returns exactly one referent,
`000cb7f0 [DATA]`.

Record 0xE511C (20 bytes, `040000000b001600200080008000800080000000`) decodes under the evaluator as
**count 4, x knots {0, 11, 22, 32}, y {128, 128, 128, 128}**. Evaluator layout, read from the
FUN_0002a93a decompile: `rec+2` = x0, `rec+4..` = x knots, `rec+8` = x_last, `rec+10` = y0,
`rec+0x10` = y_last; linear interpolation between bracketing knots, clamped to y0 below and y_last above.

Exactly **two** base loads exist image-wide (raw dword scan for `0x000CB7D4` → immediates at 0x29E78 and
0x2AD66, inside the 6-byte `mov` at `0x29E76` and `0x2AD64`). Both index it as
`*(int*)(&PTR_LAB_000cb7d4 + selector*4)` off the same variant selector `gp-0x674e` — so only the live
slot is ever reached, and with the measured selector 7 that is 0xE511C and no other record. See
[[accord-one-selector-indexes-all-five-banks]] and [[accord-the-live-variant-selector-is-7-tvca4-measured-on-the-wire]].

⇒ **GATE-1 verdict for `0xE511C`: SHARED-IN-CODE, PRIVATE-IN-EFFECT.** Both indexers compute the same
slot, but the second one (`FUN_0002a93a`, 0x2A93A) is inside the unreachable duplicate block below, so an
edit changes the live rate PID's Kd and nothing else. Publish both halves.

⚠ **The two loads at `0x29E82`/`0x29E88` (and `0x2AD6E`/`0x2AD74`) fetch the SAME record twice, not two
records** — the compiler failed to CSE `*(&PTR_LAB_000cb7d4 + iVar)`. Byte proof: `0x29E6E mov r12,ep`
and `0x29E7C mov r12,r10` load the identical index, then `add r7,ep` / `add r7,r10` with `r7 = 0xCB7D4`.
One record from the family per pass, in both copies. (A reader mistook this for a two-record fetch.)

⚠ Ghidra variable-reuse check, done explicitly: `iVar23` reaching the Kd LERP at decompile line 1059 is
assigned at lines 804/810/861 (`gp-0x674e << 2` / `* 4`) and **not reassigned in between** — so it really
is selector×4, in both the override and non-override branches.

**Knot index (distinct from the slot):** `uVar30 = uVar33 & 0xff` — **ceiling 255**. `gp-0x674b` gets
`(char)uVar33` (byte, same clip); `gp-0x697a` gets `(short)uVar33` (halfword, **NOT clipped**). They
diverge above 255, so `gp-0x697a` is not a valid proxy for the Kd knot index. Moot for slot 7 today:
record 0xE511C is FLAT (y = 128 at every knot), so the knot index cannot change Kd in the live variant.

**`gp-0x674e` census** (disp16 0x98B2; scanner controlled on gp-0x3d3c → exactly 4): readers
`0x28FC8, 0x29AA0, 0x29B7C, 0x29CC4` (live copy) and `0x2A9A6, 0x2ABBA` (orphan); writers `st.b` at
`0x4272A, 0x4273E` (the UDS variant-coding path).
⚠ **Parity trap:** `0x2DBD0` and `0x4E646` are op **0x3d** (odd disp) = **`gp-0x674d`, a different cell**.
A census that does not split `ld.bu` on op 0x3c (even) vs 0x3d (odd) over-counts `gp-0x674e` by two.

**What `FUN_0002a93a` is:** the same LKAS assist/rate computation recompiled — not a different lane and
not a monitor. Same cal set, same nine pointer banks, and its tail `LAB_0002b054` writes the identical
six cells FUN_00028ea6's tail writes (`gp-0x6b32/-0x6b34/-0x6b36/-0x6b2e/-0x6cf8/-0x6dd0`) plus
`gp-0x674b` and `gp-0x697a`. Those ARE motor-path cells; the live writes all come from FUN_00028ea6.

## Register-indirect consumers of the whole cal block (invisible to operand-text search)

Raw scan for `mov imm32,reg` (hw1>>5 == 0x31) with the immediate in the cal windows:
- **`0x146DC`** `mov 0xc6000,r11` → `movhi -0x580,r0,ep` (ep = 0xFA800000) → `st.w 1,[0xfa0012c4]` →
  `addi 0x1000,r11,r9` → a 16-byte-per-iteration `ld.w`/`sst.w` loop. **Copies the entire
  0xC6000-0xC6FFF block, all four pole cells included, to 0xFA800000.** Undefined in Ghidra.
- **`FUN_00059560`**: `if (p < 0xC6000 || p > 0xC7FFF) return 0; else return p - 0x58C6000;` —
  0xC6000 - 0x058C6000 = 0xFA800000, so this maps a cal address into the 0xFA800000 window.
- **`0x5963E`**: bounds guard — r6 ≥ 0xC6000, size ≤ 0x2000, r6+r7 ≤ 0xC8000 → 0/1. Reads as the
  reprogramming/UDS write-range validator. `0x59862` is a fourth site in the same module.

BELIEF (callers not traced): these are the reprogramming/diagnostic path, not live control-loop readers.
The point that matters for GATE 1 is that the block **is** addressed wholesale through a base register,
so "no other operand-text reader" was never a sufficient census.

## Cross-cell notes worth carrying
- The P clamp `0xC61BC` is **not** private either: `0x29E3A/0x29E44/0x29E4A/0x29E58` in FUN_00028ea6
  **and** `0x2AD2C/0x2AD34/0x2AD44` in FUN_0002a93a.
- The Ki cell `0xC63E6` has two readers: `0x29D9C` and `0x2AC8E`. Relevant when pinning a Ki dose.
- 0xC63DA/DC/DE/E0 and 0xC63F4/F6/F8/FA/FC are all likewise read from both FUN_00028ea6 and the
  0x2A5xx-0x2B3xx region.

## Related
[[reference_accord_crc_block_lookup_and_cave_hook_template]] — which CRC block covers these cells, and
why "one CRC per 0x1000 page" is the wrong model.
[[reference_accord_fun2a30e_steerstatus_debounce_statemachine]] — the live-with-no-callers precedent.
[[reference_accord_tp_relative_xref_blindspot_and_parity_trap_2026-08-12]] — the scanner blind spots.
[[feedback_check_kit_memory_before_calling_a_function_dead]] — the retraction this session produced.
