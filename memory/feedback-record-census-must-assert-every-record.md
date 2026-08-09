---
name: feedback-record-census-must-assert-every-record
description: "A count-only mode-record census is blind to a write into an already-non-stock record; assert every record byte-identical to the BASE unless declared, over all 340 pointer slots, not 58."
metadata:
  node_type: memory
  type: feedback
---

🛑 **A COUNT-ONLY RECORD CENSUS IS BLIND TO A WRITE INTO AN ALREADY-NON-STOCK RECORD.**

A census that reports *"N records differ from stock"* cannot see a build **modify one of those N**.
The count stays N and the audit passes while the surface changed underneath it. This is the same failure
family as V83a shipping V81's entire damper live in mode 27 for a whole flight — an edit that no
7-mode view could see.

**The correct assertion is against the BASE, not against stock, and it is per-record:**
> **Every mode record must be byte-identical to the BASE image unless the build explicitly declares
> it changed.** A differing record that is not on the declared list is a build failure, whether or not
> it already differed from stock.

**And the space is larger than the kit believed [EVIDENCE, 2026-08-09]:**
- **340 pointer-array slots — 10 arrays × 34 modes — not 58.**
- **34 non-stock records** on the current lineage, **including modes 32 and 33**, which no previous
  sweep enumerated.

**How to apply:** dereference through the pointer arrays inside the image (never a hard-coded record
address), sweep all 340 slots, diff each record against the **base** image, and print the declared-vs-
observed difference as a set operation. Carry a **positive control** — a record you know a past build
wrote — so a silent scan failure is visible.

Related: [[accord-mode-27-is-a-second-engaged-column]], [[reference-accord-car-is-tvca4-mode-24-26]],
[[accord-v85-flew-lever-delivered-bands-are-null]], [[feedback-a-falsifier-only-fires-if-it-could-have-fired]].
