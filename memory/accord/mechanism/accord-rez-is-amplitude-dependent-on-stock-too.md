---
name: accord-rez-is-amplitude-dependent-on-stock-too
description: "Re(Z) at 7-12 Hz rises monotonically with the 6-12 Hz rate amplitude on BOTH stock and V112 - a real describing-function nonlinearity that is Honda's, not ours. But at MATCHED amplitude V112 is still ~2.2x more anti-damped than stock, so the nonlinearity does not explain our excess. Records the elimination of six candidate mechanisms."
metadata:
  node_type: memory
  type: reference
---

# `Re(Z)` IS **AMPLITUDE-DEPENDENT ON STOCK TOO** — a real nonlinearity, but not our excess

2026-08-27. 10.24 s blocks classified by their own 6–12 Hz rate amplitude, then pooled per quartile.
```
             6-12 Hz rate amp     Re(Z) 7-9 Hz    Re(Z) 9-12 Hz   coh2
  STOCK  Q1     0.20-0.34             -18.2           -20.6       0.251
         Q4     0.92-2.37             -25.5           -44.8       0.671
  V112   Q1     0.23-0.66             -47.6           -60.0       0.570
         Q4     1.27-2.39             -58.7           -78.4       0.836
```
⭐ **Both arms rise monotonically with amplitude** (stock ×1.40 at 7–9 Hz, ×2.17 at 9–12 Hz;
V112 ×1.23 and ×1.31). ⇒ **the describing-function nonlinearity in this band is HONDA'S**, present
without any of our edits.
🛑 **But it does NOT explain our excess.** At **matched amplitude** — stock Q4 (0.92–2.37) vs V112 Q3
(0.80–1.27, *lower* amplitude) — the values are **−25.5 vs −56.6, still 2.2×.**

## 🛑 CANDIDATE MECHANISMS ELIMINATED FOR THE 7–9 Hz EXCESS (all with their own controls)
| candidate | test | verdict |
|---|---|---|
| the command **rail** | railed vs high-not-railed, matched | 0.76× [0.22, 1.49] |
| **driver grip** | high/low torque, oscillation on RATE | 0.79× [0.67, 1.01] |
| command **magnitude** | Re(Z) vs \|cmd\| | present at \|cmd\| < 512 — command-INDEPENDENT |
| **Coulomb relay switching** as exciter | scale-free shape ratio | 0.14× [0.11, 0.19] — inverted |
| the **armed biquad** (`0xC649B`) | natural experiment, V88- vs V103+ | P = 0.722, not separable; excess already at V90 |
| **linear in LKAS gain** | within- vs between-gain spread | within 41.2 vs between 19.1 — not supported |
| **amplitude dependence** | quartile stratification | real, but Honda's, and gap persists 2.2× at matched amplitude |

## ✅ WHAT IS SETTLED
**Stock's 7–9 Hz `Re(Z)` (−13.1) lies outside the entire modified range (−31.9 … −74.8) over 16
routes spanning V90→V112 and 4×/6×/8×.** The excess is **ours**. The edits common to *every* affected
build reduce to: the **V57 gain repoint** (`0x2A1F0`, arb gain reader 891 → 5346), **V42's ratchet
fix** (`0x454FE`), the **164-byte telemetry cave**, the **LKAS ceiling raise ×1.067**
(`0xE4194`/`0xE51xx` blocks, a 9-knot flat-Y LERP 15360 → 16384), and ~20 cal cells.
⚠ **The gain repoint cannot be separated from "being a modified build at all"** — every modified
route carries it, and stock is the only 1× point. **No existing data can discriminate within that
set.**
⊕ `0x13109`/`0x14120` `2d`→`2c` are **the ASCII part-number string** (`39990-TVA-` → `39990-TVA,`),
not control code — Ghidra mis-decodes that region as instructions.
