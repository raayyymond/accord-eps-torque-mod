---
name: accord-mode-27-is-a-second-engaged-column
description: TVCA4 row 11 gives modes [24,25,26,27] and columns 2/3 are BOTH engaged — V83a reverted mode 26 and flew with V81's relay damper still armed on mode 27. Honda's pairing is 24<->26 and 25<->27, so "engaged == mode 24" is a false gate.
metadata:
  type: reference
---

★★★★ **MODE 27 IS A SECOND ENGAGED COLUMN, AND V83a FLEW WITH THE RELAY DAMPER STILL ON IT.**
2026-08-08. [EVIDENCE, byte reads across the shipped images.]

`TVCA4` variant **row 11** yields the four reachable modes **[24, 25, 26, 27]**. **Columns 2 and 3 —
modes 26 and 27 — are the ENGAGED pair.** Every "revert the engaged damper" edit that touches only
mode 26 leaves mode 27 armed.

## What that cost V83a

V83a reverted mode 26 to Honda's surface and **left mode 27 byte-identical to V81's mode 26**:

- the **539 `FactorE` plateau** intact,
- describing-function relay index `N(50)/N(500)` = **1.45×** against Honda's **0.00×**,
- **9.5× mode 26's dose at 200 counts of motor rate.**

⇒ V83a was **not** a clean "damper off" experiment. Read its regressions with that confound attached —
see [[accord-v83a-flew-worst-modern-build]].

## ⊕ Honda's own pairing is 24↔26 and 25↔27 — which breaks the obvious gate

Stock `FactorC` `Y` rows, from Honda's firmware:

| pair | stock FactorC Y |
|---|---|
| `m24` / `m26` | `[0, 234, 429, 908]` |
| `m25` / `m27` | `[0, 233, 426, 875]` |

They are **near-identical but NOT byte-identical**, and the pairing runs **24↔26, 25↔27** — a
manual column and its engaged twin. ⇒ 🛑 **A build gate that asserts "engaged ≡ mode 24" fails on
Honda's own firmware**, because Honda ships two manual columns and two engaged ones.

**Any engaged-column edit must be written and asserted over BOTH pairs**, or it is half applied. This is
the same class of silent-half-application that produced three lost fixes already
([[accord-v81-carries-neither-grind1-fix]]).

Related: [[reference-accord-car-is-tvca4-mode-24-26]] ·
[[accord-stock-mode24-equals-mode26-damper-is-ours]] · [[accord-damper-is-mode-table-selected]] ·
[[accord-v84-built-engaged-equals-manual]] · [[feedback-rule7-mode-proof-or-a-bet]]
