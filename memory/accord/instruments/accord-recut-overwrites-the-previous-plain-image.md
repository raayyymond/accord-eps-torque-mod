---
name: accord-recut-overwrites-the-previous-plain-image
description: "🛑 OPEN HAZARD — every builder writes a fixed _vNN_plain_image.bin, so a re-cut under the same build number silently destroys its predecessor's snapshot, leaving a flashable .rwd that NO gate in this kit can check. Bit this session on V70. The fix is recommended, NOT applied."
metadata:
  type: reference
---

# 🛑 A RE-CUT UNDER THE SAME BUILD NUMBER DESTROYS ITS PREDECESSOR'S PLAIN IMAGE

**Status: OPEN. The fix below is a recommendation for future builders, not something that has been
done.** Every builder in the tree still writes the fixed `_vNN_plain_image.bin` name.

## What happened, 2026-08-04
Two **V70** cuts were built 19 minutes apart with **opposite control paths** — the first was **rejected
on an operator override**, not an open choice between designs. **Both wrote `_v70_plain_image.bin`**, so
the second silently **overwrote** the first's snapshot. The rejected cut's `.rwd` survived and was
**flashable**.

⇒ **A flashable artefact existed that NO gate in this kit could check:**
- `verify/verify_v70_image.py` asserts the **current** topology (`0x3AA96 == 0xC5`, `0xC6446 == 512`), so it
  **fails on the superseded build by construction**;
- `verify/diff_build_vs_stock.py` has no image to read at all.

⚠ **The only reason the superseded cut's bytes are documented is that they were read inside the
19-minute window before the overwrite.** That is luck, not process.

## What is and is not fixed
✅ The **flash** risk was closed by renaming the artefact `SUPERSEDED-DO-NOT-FLASH-…`
(`accord-firmwares` `9d44efc`; filesystem-verified — exactly one flashable `V70` file remains).
🛑 The **verifiability** hazard is **NOT** closed, and applies to every future re-cut.

## RECOMMENDED FIX — not applied
- Write **`_v<NN><tag>_plain_image.bin`** (tag from the build's own `TAG`), so a re-cut cannot collide;
  **or**
- **Refuse to overwrite** an existing snapshot whose SHA differs from the one about to be written,
  unless explicitly forced.

⚠ **The superseded V70 image cannot be trivially regenerated** — its builder configuration no longer
exists in the tree. In principle it could be recovered by **decoding the surviving `.rwd` back to an
image**. **That was NOT attempted**, and was judged not worth it for a superseded do-not-flash
artefact. Recorded so the gap is explicit rather than ambiguous.

## ★ The companion fact that makes the rename load-bearing
**`bit6 ⇒ bit3` gives build-CLASS identity, never FILE identity.** Two cuts of the same version have
**byte-identical caves**, so no probe can separate them on-car — **the filename is the only pre-drive
discriminator between re-cuts.** See [[accord-v70-built-sign-probe]].

⇒ **Rule: rename a superseded artefact `SUPERSEDED-DO-NOT-FLASH-…` the moment it is superseded**, as
the stale V68 artefact was. It is the only barrier that survives an overwritten image.
