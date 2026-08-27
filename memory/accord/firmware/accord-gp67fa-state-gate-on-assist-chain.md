---
name: accord-gp67fa-state-gate-on-assist-chain
description: "★★★★ FUN_0002214a state-gates the assist chain on gp-0x67fa via THREE masks, and state 10 splits the chain in half — the aggregator runs while the detector, return-to-centre and arbitration do not. A LIVE ALTERNATIVE explanation for the five-build detector null, but V67's own probe argues against it."
metadata:
  type: reference
---

> 🛑 **AMENDED 2026-08-05 — READ THIS FIRST.** 🛑 **0x830 is a SUBSET of 0xc30** ({4,5,11} within {4,5,10,11}) => every state that runs the aggregator also runs the damper, so **this variable cannot explain "aggregator live, damper inert"**. The state-10 split is struck as an explanation of the damper null. ⊕ All 33 writers store literal constants, value set {1,3,4,5,6,7,8,9,10,11} => **no aliasing**; the 4-bit mask is a provable no-op.

# ★★★★ `gp-0x67fa` STATE-GATES THE ASSIST CHAIN — and state 10 splits it in half

**The guard wraps the `jarl` IN THE CALLER**, not inside the four functions. Each has exactly one call
site, all in `FUN_0002214a` (`w_steer_control_task`, RTOS task 1, 1 kHz) ⇒ **in a masked-out state the
callee is NEVER INVOKED — no stack frame, 0% of body.**

**[EVIDENCE — instruction level, `FUN_0002214a` `0x2214a`–`0x22a84`.]** Index is a plain
`1 << (gp-0x67fa & 0xf)`, **no off-by-one** (`0x2214e` `ld.bu` / `0x22172` `andi 0xf` / `0x2217c` `shl`,
recomputed identically @`0x221bc`–`0x221c6`):

| site | mask | states | gates |
|---|---|---|---|
| `0x221d6` | **`0x830`** | **{4, 5, 11}** | `FUN_00036388` @`0x22882` (return-to-centre) · `FUN_000428d4` @`0x22926` (**the OSC DETECTOR**) |
| `0x22518` | **`0x930`** | **{4, 5, 8, 11}** | `FUN_00028ea6` / `FUN_0002b422` / `FUN_0002b57a` (**ARBITRATION = `gp-0x6806`'s producer**) |
| `0x2269a` | **`0xc30`** | **{4, 5, 10, 11}** | `FUN_0003a382` @`0x226a0` (residual lane) · `FUN_0003aa2c` @`0x2291e` (**THE AGGREGATOR**) |

⇒ **IN STATE 10 THE AGGREGATOR AND THE RESIDUAL LANE RUN, WHILE THE DETECTOR, THE RETURN-TO-CENTRE LANE
AND ARBITRATION DO NOT. Assist is delivered from a stale `gp-0x6806`.** [EVIDENCE]

★ **State 10 is REACHABLE IN NORMAL OPERATION** — written twice in `FUN_00019970` (the state-4
handler): `0x199CC` (diagnostic, `tp+0x74d0 == 0xa`) and **`0x19A72` (the NORMAL path)**, the latter
gated on **bit 15 of `gp-0x6d78`**, with bit 16 (→ state 11) taking priority. Writer set over **33
`st.b` sites** (Ghidra and a raw LE byte scan agree exactly, **no undercount**): {1,3,4,5,6,7,8,9,10,11},
max 11. **[OPEN] what bit 15 of `gp-0x6d78` means — which is what decides how OFTEN state 10 is
visited, not whether it can be.**

## 🛑 A LIVE ALTERNATIVE FOR THE FIVE-BUILD DETECTOR NULL — with its counter-argument attached
*"`FUN_000428d4` was never CALLED"* has **never been on the table**, and it has the **identical
signature** to *"it ran and found nothing"* — `gp-0x67df` = 0/14,980 (V64), 0/186,321 (V67),
0/53,991 (V68).

⚠ **BUT V67's OWN PROBE ARGUES AGAINST IT, and this must be quoted in the same breath.** State 10 is
absent from `0x930` too, so **arbitration — `gp-0x6806`'s producer — is also skipped there and the flag
would go STALE.** V67 measured **`gp-0x6806` == `latActive` in 150,302/150,327 = 99.983%** of frames,
all **25** disagreements single-frame transition edges. **A stale flag cannot track transitions that
closely** ⇒ **the ECU is predominantly NOT in state 10 while engaged, and the detector nulls are
probably GENUINE.** [BELIEF — indirect.]

✅ **V70's bit5 rung (`gp-0x67fa == 10`) settles it directly, and is NON-VACUOUS IN BOTH DIRECTIONS:**

| bit5 | verdict |
|---|---|
| **≈ 0** | state ∈ {4,5,11} ⇒ **the nulls are genuine and five builds are vindicated** |
| **materially non-zero** | **the nulls were on the gate** ⇒ the detector programme needs replanning |

## ⚠ The detector has a SECOND, independent entry gate — and it is still OPEN
`FUN_000428d4` is also gated on **`FUN_00046ea6(5)`** — bit 5 of `gp-0x18d0`/`gp-0x18d4`, a
fault/DTC-style bitmask, falling to a fixed **`0x8000` sentinel** if set.
🛑 **The record's earlier closure established only that that FUNCTION has one caller image-wide — NOT
that the BIT is clear in operation. Those are different claims.** Treat the second as **[OPEN]**.
The other three gated functions have no such secondary gate.

## 🛑 Bus `STEER_STATUS` is NOT `gp-0x67fa`
Route `4f` reads **ST == 0 on 47,990/47,990** frames *while the car steered*, and **state 0 is in no
mask**. **Any reasoning that equated them** — e.g. *"ST==4 fires 0/37,922"* as evidence about
`gp-0x67fa == 4` — **is invalid.**
[VERIFIED] **State 4 sits inside all three masks** and is where the governor's ratchet substitution
(fixed in V42) used to fire — see [[reference-accord-state4-governor-ratchet]].

## ⚠ Provenance caveat, carry it
Decompiled against **stock `code.bin`**, with the 33 writer sites cross-checked **byte-identical in
`_v68_plain_image.bin`**. The **dispatcher itself was NOT decompiled from a V68/V69 image** — high
confidence it is unchanged (far outside any cave region), but that is **BELIEF by adjacency, not
EVIDENCE.**

⚠ Two tool traps hit here: **`mcp__ghidra__get_xrefs_to` returned "No references found" for the RTOS
task entry** ⇒ **a null from that tool is never load-bearing**; and a `jarl` Format-V scanner returned
**zero hits for functions Ghidra had just given callers for** — bits 15:11 are **reg2, not opcode**, and
`disp = ((hw1 & 0x3F) << 16) | hw2` sign-extended from **22 bits**
([[accord-v850-scan-traps-formatv-and-storezero]]).

See [[accord-state671a-is-an-oscillation-detector]],
[[accord-v68-detector-still-zero-no-positive-control]], [[accord-v64-null-is-on-the-gate]],
[[feedback-probe-the-gate-not-just-the-output]].
