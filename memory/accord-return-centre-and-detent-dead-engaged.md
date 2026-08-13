---
name: accord-return-centre-and-detent-dead-engaged
description: "V92 measured the return-centre lane gp-0x6b62 and the gp-0x6bda outer LERP gate at EXACTLY 0.0000 over 75,227 engaged frames — the detent/dwell hypothesis is structurally dead on the road. UPDATED 2026-08-12: the lane is RE-IDENTIFIED as a rack END-STOP CUSHION (stall-armed), the dwell polarity recorded here was INVERTED (it arms on |gp-0x6b64| > 1024, not <), and the byte7 b6 rung is therefore EXONERATED — its 0.0000 duty is the predicted value, not a null on the gate. Manual duty is 0.0074, so the lane is ~99.3% dead in manual too."
metadata:
  type: reference
---

# 🛑🛑 THE RETURN-CENTRE LANE AND THE DETENT ARE **DEAD ENGAGED** — and it is an END-STOP CUSHION

Route 79 (V92), 2026-08-11, 87,317 `0x14A` frames / 75,227 engaged.
Tool: `rlog-tools/extract_r78_r79.py health 79`.

## THE MEASUREMENT [EVIDENCE]

Route 79's `byte4` takes only **four distinct values** across the whole drive —
`0x0F:18,868 · 0x3F:35 · 0x8F:68,360 · 0xFF:54`:

| rung | meaning | engaged duty | manual duty |
|---|---|---|---|
| b7 | `gp-0x6bbe < 0` (boost sign) | **0.8865** | 0.1435 |
| b6 | `gp-0x6b62 < 0` (return-centre sign) | **0.0000** | 0.0045 |
| b5 | `gp-0x6b62 ≠ 0` (lane LIVE) | **0.0000** | 0.0074 |
| b4 | `gp-0x6bda ∈ (−397, 384)` (OUTER GATE open) | **0.0000** | 0.0074 |
| byte7 b6 | `gp-0x6a82 > 20` (DWELL SNAP) | **0.0000** | **0.0000** |

**`b4 ≡ b5` exactly, on every one of 87,317 frames** — two different cells, one identity. That is
not a coincidence, it is the causal chain: **gate shut ⇒ `gp-0x6b64 ≡ 0` ⇒ return-centre output
≡ 0.** ⊕ The structural check **`(b6, b5) = (1, 0)` = 0 frames** passes, as required (both read
`gp-0x6b62`; it cannot be negative while also zero).

⇒ **The outer LERP gate on `gp-0x6bda` is SHUT for 100 % of engaged driving**, so `gp-0x6b64 ≡ 0`
and the whole dwell/detent lane contributes a **flat −1024 bias, not a relay**. This confirms the
suspicion that motivated the bit: a kit memory put `gp-0x6bda`'s hands-off value at ~9262, **24×
outside the window**. **It is not merely low-duty — it is structurally dead in the regime the
operator drives in.** ⇒ **Do not propose a detent/dwell lever.**

## ✅ RESOLVED IN GHIDRA 2026-08-12 — the rung was RIGHT; the POLARITY in this file was backwards

This section previously indicted `byte7 b6` as a dead rung. **That indictment was wrong, and it was
caused by an inverted comparison recorded above and in `STATE.md` §E.**

🛑 **The dwell counter arms on `|gp-0x6b64| > cal(0xC618A)=1024`, NOT `<`.** Assembly in
`FUN_00036388`:
```
0x36436: cmp r0,r8 / bge / subr r0,r7 / sxh r7   -> r7 = |gp-0x6b64|   (abs idiom; validates operand order)
0x36440: ld.h  0x718a[tp],r16                    -> r16 = cal(0xC618A) = 1024
0x36448: cmp r16,r7                              -> V850 computes r7 - r16
0x3644a: setfgt r16                              -> r16 = 1  <=>  |gp-0x6b64| > 1024
0x3645a: be 0x36464                              -> if NOT greater, take the DECREMENT path
0x36460: add 0x1,r14                             -> else counter++
```
The decompile agrees (`iVar11 - iVar17 < 0 == OV && iVar11 != iVar17` is signed `>`).

**⇒ a shut gate DISARMS the counter, it does not arm it.** Gate shut ⇒ `Y1(gp-0x6bda)=0` ⇒
`gp-0x6b64 ≡ 0` ⇒ `|0| > 1024` is false ⇒ the counter decays to 0 and holds ⇒ **no snap, and the lane
contributes exactly ZERO** (not the "flat −1024 bias" the inverted reading predicted).

| | inverted polarity predicted | correct polarity predicts | MEASURED |
|---|---|---|---|
| `byte7 b6` snap duty | 1.0 (default-armed) | **0.0** | **0.0000** |
| `byte4 b5` (`gp-0x6b62 ≠ 0`) | 1.0 | **0.0** | **0.0000** |

> ✅ **The 855 s sustained `(gate=0, snap=0)` run is a CLEAN CONFIRMATION, not an indictment.**
> `byte7 b6` reads the true value and does **not** need re-flying. All of `b4`/`b5`/`b6` and
> `byte7 b6` are sound and mutually consistent.

⊕ **The lane is also RE-IDENTIFIED**: it is a **rack end-stop cushion**, not a centring lane —
`FUN_00035e00` arms it on `|gp-0x6b98|>4096` AND motor rate `<200` (a **stall**), and its gate needs
`|gp-0x6bf0| > 8878` because the travel envelope is floored by cal `0xC6150` at `18780>>1 = 9390`.
🛑 **Note the manual duty is 0.0074, not ~1** — the lane is ~99.3 % dead in MANUAL too, so its absence
cannot explain any engaged-vs-manual difference. **Still: do not propose a detent/dwell lever.**
See `[[accord-v64-null-is-on-the-gate]]`, `[[feedback-probe-the-gate-not-just-the-output]]`.
