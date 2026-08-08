---
name: accord-v42-ratchet-fix-lost-since-v53
description: "V42's CONFIRMED root-cause ratchet fix (0x454FE bne->br) is byte-stock in every build V53-V70; it was lost at a rebase, and the argument that later retired it as a cause of the current ratchet was voided."
metadata: 
  node_type: memory
  type: project
  originSessionId: cd0a7709-d576-4983-bd00-1d8facc96710
  modified: 2026-08-04T22:14:32.167Z
---

★★★★ **[EVIDENCE — orchestrator byte-read all 60 `_v*_plain_image.bin` in `../accord-firmwares/analysis-2020accord/`, 2026-08-04.]**

`0x454FE` — V42's one-byte kill of the **state-4 governor magnitude substitution** in `FUN_0004503c`,
recorded in `docs/BUILD-LINEAGE.md` as ✅ **CONFIRMED ROOT CAUSE, fixed the hard-turn ratchet, carry
forward** — is:

- `b565` (`0x65B5`, **`br`** = fix applied) in **V42, V43, V44, V45, V46, V47, V48A, V48B, V49, V50,
  V52, V52C — and nowhere else.**
- `ba65` (`0x65BA`, **`bne`** = stock, substitution LIVE) in V22–V41 **and in V53, V54, V55, V56, V57,
  V58, V59, V60, V61, V62, V63, V64, V65, V66, V67, V68, V69, V70.**

**Cause is structural, not a mistake:** the V53+ line descends from V38/FOURFRAME, which branched
*before* V42. `diff_build_vs_stock.py v70` already prints it under *asserted STILL STOCK*.

🛑 **AND THE ARGUMENT THAT RETIRED IT IS VOID.** The elimination was *"`STEER_STATUS == 4` fires in
0 of 37,922 frames ⇒ the state-4 governor substitution is not producing this ratchet."*
`BUILD-LINEAGE.md` now states: *"bus `STEER_STATUS` IS NOT `gp-0x67fa` … any reasoning that equated
them — e.g. 'ST==4 fires 0/37,922' — is **invalid**. State 4 sits inside all three masks."*
⇒ **The V42 mechanism was never actually eliminated as a cause of the current ~7.5–7.8 Hz ratchet.**

★ **The mechanism is a hard nonlinearity, downstream of the aggregator** — which is exactly the shape
the ratchet has, and explains its measured insensitivity to the r24 dose 0×→4×
(see [[accord-ratchet-characterised-on-route-4f]]). Byte-verified in
`analysis-2020accord/.claude/agent-memory/firmware-codepath-tracer/reference_accord_state4_ratchet_and_gp67fa_state_graph.md`:
substitutes when `|fresh| > |held|`, seeded from the old value, with an **unconditional writeback**
`0x455cc st.h r6,-0x138a[gp]` making it **cumulative and self-sustaining**.

✅ **RESTORING IT ON A V70 BASE IS A LITERAL ONE-BYTE CHANGE. [EVIDENCE]** V70's governor region
`[0x453E0, 0x455E0)` is **byte-identical to stock (0 differing bytes)**, and V42 differs from stock
there by **exactly one byte**. So `0xba → 0xb5` (V850 Bcond nibble `0xA` BNE → `0x5` BR, displacement
untouched) reproduces V42's edit on code identical to what V42 was cut from. No cave ⇒ GATE 1 vacuous.
CRC: MAIN block `0xC4FFC`.

⚠ **WHAT THIS DOES NOT ESTABLISH — carry it with the claim.**
- It does **not** show the V42 mechanism *is* the current ratchet. V42's symptom was a **hard-turn**
  ratchet at V38's 4× authority; the current line is **7.79 Hz at creep**.
- The ratchet is present on V55/V59/V61/V62/V69 — all builds lacking the fix — which is **consistent**
  but is **not a controlled test**: no build carrying the fix was ever measured for a 7.5 Hz creep
  ratchet (V42–V52C predate the spectral harness).
- **`gp-0x67fa`'s runtime value has never been read on-car.** V70's bit5 tests `== 10` only.
- **Nobody has ever driven a build carrying both `0x454FE` and the modern rate-lane fix.**
- ⚠ The prior safety case (`FUN_0004595a` → **DTC 0x1d, no debounce** → motor-off) is flagged
  **[INFERRED]** and *"carrying full weight with zero margin for error"*. Re-verify before any flash.

🛑 **THE GENERAL LESSON, and it is the transferable one:** a lever can be marked CONFIRMED and then be
**silently lost at a rebase**, with the record still reading as though it were carried. The lineage
check must record **which builds still carry an edit**, not only that it was once made and confirmed.
See [[accord-check-build-lineage-before-proposing-lever]].
