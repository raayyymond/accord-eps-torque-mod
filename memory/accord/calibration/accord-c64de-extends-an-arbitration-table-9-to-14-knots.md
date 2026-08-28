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

## 🛑🛑 CORRECTION — **THE TABLE ADDRESS IN THIS NOTE WAS WRONG (off-by-0x1000)**
`tp = 0xBF000`, so **`tp+0x7734` = `0xC6734`, NOT `0xC7734`.** I dumped `0xC7734` — unrelated memory —
and reasoned over it. **Everything in the section above about "the table data" is VOID**: the
`61452, 14, 61454, 14 …` pattern, the "monotone signed pairs −4084…+18", and the conclusion that the
extension "is not obviously reading garbage" were all about the wrong bytes.
⚠ This is the **off-by-0x1000 trap CLAUDE.md records as having recurred five times.** It caught me
even while I was explicitly working tp-relative. **Anchor every tp address against a known value.**

### THE REAL CONTENTS OF `0xC6734`… — and they are NOT a clean speed axis
```
  idx   addr      stock    V112
    0  0xC6734        4       4        10  0xC6748       2       2
    2  0xC6738    31872   31872        11  0xC674A   57344   57344   (= -8192 signed)
    3  0xC673A    31936   31936        12  0xC674C   64512   64512   (= -1024)
    4  0xC673C    32000   32000        13  0xC674E    1024    5120  <<<
    5..9  0xC673E..46    0       0     14  0xC6750    1024    5120  <<<
                                       19  0xC675A   64512   60416  <<<  (-1024 -> -5120)
```
**Not monotone in either stock's range or ours**, so the "9 → 14 knots walks a longer axis" reading is
**not supported**. The walk at `0x297B2` (`sld.hu 0x2,ep` / `add 0x2,ep`) is a real search, but what it
searches is **not established**, and `0xC6736` = 0 / `0xC673C` = 32000 are compared against a *speed*,
which does not parse as a speed axis. 🛑 **`0xC64DE`'s meaning is therefore OPEN AGAIN** — the
`n = cal/2 + 1` arithmetic at `0x2977C` is solid, and it is **stored to `gp-0x6756`** at `0x29788`
before r6 is reused, but what consumes that count is untraced.

## ✅ WHAT THE CORRECTED DUMP DID FIND — the direction corridor is ×5
`0xC674E` / `0xC6750` **1024 → 5120** and `0xC675A` **−1024 → −5120**: these are the **DIRECTION
CORRIDOR** cells of the soft-EME lockstep monitor (the V29/V30/V31 lineage names
`0xC674E/50/5A/5C` exactly), **widened ×5 on this car**. They appear in the V112-vs-stock diff as the
high-byte runs `0xC674F 04→14`, `0xC6751 04→14`, `0xC675B fc→ec`.
⊕ Per [[reference-accord-corridor-lockstep]] the int wall is a **three-way MAX** of
`max(dir_corridor, velocity/cmd-envelope IIR, boost)`, so a ×5 corridor raises that wall only where
the corridor arm is the max. **Not yet sized, and not yet linked to the 7–9 Hz excess** — but it is a
×5 change in a monitor bound, live on this car, and it belongs on the candidate list.
