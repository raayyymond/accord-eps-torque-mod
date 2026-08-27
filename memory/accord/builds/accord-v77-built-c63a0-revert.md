---
name: accord-v77-built-c63a0-revert
description: V77 = V74 base + 0xC63A0 2048->1024, single variable, ONE cell (not two bytes). V77B = the same revert on the V75 base, BUILT/UNFLASHED/NOT RECOMMENDED. Neither is clearance to fly — V77 is a hypothesis test, not a known-good.
metadata:
  type: project
---

# ★ V77 BUILT — the `0xC63A0` loop-gain revert, single variable

**V77 = V74 base + `0xC63A0` 2048 → 1024.** One lever, nothing else.

| artifact | sha256 |
|---|---|
| `39990-TVA,A160-V77-V74BASE-C63A0.1024-loopgain-revert-0x13000-0x100000.rwd` | `fd8db4e2ed140035782a55b2e6808bcf87a0ea85692cbe547960a13de1cfc8c5` |
| `_v77_C63A0.1024_v74base_plain_image.bin` | `a0f7c09c038931cabc419ccf79d4bb9819e647e88c0fb817ebc23cd44d102782` |

## The diff
**V74 → V77 = 2 runs / 5 bytes: `0xC63A1` `08` → `04`, plus the `0xC6FFC` CRC. Nothing else.**

⚠ **It is ONE CELL, not two bytes.** `2048 = 00 08` LE and `1024 = 00 04` LE — the **low byte is `0x00`
in both**, so only the high byte moves. ★ **Count CELLS, not bytes**, when sizing an edit; a byte count
here understates the lever and a naive "2-byte halfword" verifier assertion fails.

## Gates
- **50/50 CRC pass**
- `.rwd` **round-trips byte-for-byte**
- cave and **all mode-24/26 records byte-identical to V74**
- **mode-24 also identical to STOCK** (the [[accord-v74-hard-faulted-in-manual-over-a-bump]] invariant
  holds — but note that invariant is exactly what makes V74's manual fault *unexplained* by the damper)

## V77B — the V75-base sibling
`…-V77B-V75BASE-C63A0.1024-NOT-RECOMMENDED-UNFLASHED-…rwd`
sha `f2c2dc0ba4f5e01bbd95925b8e42c1323a1b6b99bf658b795aa25cb2fa539dd7`;
image sha `acbc218751af827d5ddc696e24d6ae44f11ef06dc04e11a3b383d366b4d4fc10`.

🛑 **BUILT, UNFLASHED, NOT RECOMMENDED** — it carries V75's engaged configuration, which **hard-faulted**.

## 🛑 Neither is clearance to fly
**V77 is a hypothesis test, not a known-good.** The hypothesis is that V72's `0xC63A0` ×2 raised Path-2
loop gain ([[accord-path2-is-a-closed-firmware-loop-and-c63a0-weights-it]]) and that reverting it takes
−6.02 dB out of the loop at zero phase cost. It does **not** address the `gp-0x6b98` re-entry term,
which is untraced and may dominate — so a V77 null does **not** exonerate the loop.

⚠ And per [[accord-v74-hard-faulted-in-manual-over-a-bump]], **no build in the current lineage has
demonstrated safety**, V74 included. Flash decisions remain the operator's, on an explicitly named file
and bus.

Related: [[accord-damper-fixes-the-grind-but-is-flat-on-the-ratchet]] ·
[[accord-recut-overwrites-the-previous-plain-image]] · [[feedback-verify-with-ghidra-and-bytes-both]]
