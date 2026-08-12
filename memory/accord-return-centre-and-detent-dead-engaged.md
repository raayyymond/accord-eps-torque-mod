---
name: accord-return-centre-and-detent-dead-engaged
description: "V92 measured the return-centre lane gp-0x6b62 and the gp-0x6bda outer LERP gate at EXACTLY 0.0000 over 75,227 engaged frames — the detent/dwell hypothesis is structurally dead on the road. The paired dwell-snap rung is DEAD and its map is indicted."
metadata:
  type: reference
---

# 🛑🛑 THE RETURN-CENTRE LANE AND THE DETENT ARE **DEAD ENGAGED** — and one rung is indicted

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

## 🛑 AND ONE RUNG IS INDICTED — read this before trusting `byte7 b6`

The **corrected** pre-registration (`STATE.md` §E) said a shut gate **ARMS** the dwell counter, so it
should climb to its ceiling ⇒ **`snap = 1` should be the DEFAULT whenever the gate is shut**, and
`(gate=0, snap=0)` should occur only as a **~21 ms transient** after each falling edge.

**Observed: `(gate=0, snap=0)` on 99.898 % of frames — 87,228 frames in 3 runs, longest 85,521
frames (855 s), 0.0 % adjacent to a gate falling edge.**

> 🛑 **That is the pre-registered SUSTAINED-RUN condition, and it INDICTS the `byte7 b6` rung map.**
> `byte7 b6` is a **DEAD rung** (duty 0.0000 everywhere ⇒ `0 < duty < 1` fails). **Do not read
> "the detent never snaps" as a physical result** — it is a null on the gate, the V64 class exactly.
> Candidates: the arm-condition model is wrong, `cal(0xC627E) ≠ 20`, or `gp-0x6a82` is not the
> counter. **Resolve in Ghidra before re-flying this bit.**

⊕ **b4/b5/b6 (byte4) are NOT indicted** — they fire (89 and 54 frames), they are self-consistent, and
they pass their own structural check. **The gate result stands on its own.**
See `[[accord-v64-null-is-on-the-gate]]`, `[[feedback-probe-the-gate-not-just-the-output]]`.
