---
name: accord-c64de-extends-an-arbitration-table-9-to-14-knots
description: "0xC64DE 17->27 is a KNOT COUNT, not a threshold: FUN_00028ea6 computes cal/2 + 1, so our builds make a speed-indexed table in the arbitration core 14 knots long where stock reads 9. The table data at 0xC7734 is byte-identical to stock and continues in a structured pattern past stock's range, so it is not obviously garbage - but whether indices 9-13 are semantically valid is NOT established. Present in every build showing the 7-9 Hz excess; function untraced; OPEN."
metadata:
  node_type: memory
  type: reference
---

# ⭐ `0xC64DE` IS A **KNOT COUNT** — our builds read **14 knots where stock reads 9**

2026-08-28. `0xC64DE` had been sitting in the V112-vs-stock diff as an unexplained single byte
(17 → 27). It is not a threshold.

## THE ARITHMETIC [EVIDENCE] — `FUN_00028ea6` @ `0x2976E`
```
  0x2976E  ld.bu 0x74de,tp,r13    ; r13 = cal(0xC64DE)      17 stock / 27 ours
  0x29774  ld.hu -0x6a5e,gp,r10   ; the index = VEHICLE SPEED
  0x2977A  sar   0x1, r13         ; cal / 2                  8 stock / 13 ours
  0x2977C  addi  0x1, r13, r6     ; cal / 2 + 1              9 stock / 14 ours
  0x29780  ld.hu 0x7736,tp,r13    ; cal(0xC7736) = 14 (unchanged)
  0x29784  movea 0x7734,tp,r7     ; the TABLE BASE, 0xC7734
```
⇒ **`n_knots = cal/2 + 1`.** Stock walks **9**; every build of ours walks **14**.
⊕ **8 readers, all inside `FUN_00028ea6`** (the arbitration core), full 183,671-instruction scan,
not truncated.

## WHAT IS AT THE TABLE — data UNCHANGED, so this is a RANGE change, not a value change
`0xC7734` onward, as u16: `61452, 14, 61454, 14, 61456, 14, 61458, 14, 61460, 14, 61462, 14, 12, 15,
14, 15, 16, 15, 18, 15` — **byte-identical between stock and V112.**
Read as **signed** pairs the first elements are `-4084, -4082, -4080, -4078, -4076, -4074, +12, +14,
+16, +18` — **monotone increasing**, and the pattern continues well past index 13.
⇒ **the extension is not obviously reading garbage.** ⚠ **But that it is SEMANTICALLY valid at
indices 9–13 is NOT established** — the LERP's own walk was not traced, `0xC7736` is read as a
separate cal *and* sits at table index 1, and an earlier unsigned monotonicity test I ran was
misleading because the values are signed.

## STATUS — OPEN, and a live candidate
- Present in **every build showing the 7–9 Hz excess**, absent from stock.
- Sits in the **arbitration core**, indexed by **vehicle speed** — engagement-independent but
  speed-dependent, which fits some of the excess's shape.
- 🛑 **Function untraced.** Do not propose reverting it as a fix, and do not dismiss it either.
✅ **The cheap next step is to read the LERP walk at `0x29784`+ and establish what the table means**,
before any build touches it.

Related: [[accord-the-mod-works-by-deleting-hondas-limiters]]
