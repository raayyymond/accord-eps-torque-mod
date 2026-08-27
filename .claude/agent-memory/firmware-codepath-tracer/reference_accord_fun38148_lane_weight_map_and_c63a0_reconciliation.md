---
name: reference_accord_fun38148_lane_weight_map_and_c63a0_reconciliation
description: THE lane<->weight map for FUN_00038148's six Path-2 weights (0xC63A0..0xC63AA), established by fresh decompile -- no prior kit document stated which lane each weight multiplies. Reconciles the standing 0xC63A0-inversion-vs-INERT contradiction (0xC63A0 weights gp-0x6bd0, measured ~0 in 87,940/87,940 frames => the flights were a V64-class null that tested nothing), INVALIDATING the sibling precedent my own c63a6 NO-GO memory leaned on. Also refutes STATE.md A5's gp-0x6b4e V97 candidate as a provably-dead lane, and corrects "gates structurally always open" to zero-reject windows.
metadata:
  type: reference
---

# `FUN_00038148` lane↔weight map — 2026-08-12, `fw-levers` task for team-lead

Fresh `decompile_function(0x38148)` on `code.bin`. **EVIDENCE.** The kit had the six weights indexed
(`studies/ledger/ledger_v94_cells.py`: "lane weight [0]".."[5]") but **no document said which lane each one multiplies.**
That gap was silently load-bearing — it is what let a dead-lane result be imported as a live precedent.

| weight cal | multiplies lane | zero-reject gate | lane identity |
|---|---|---|---|
| `0xC63A0` w[0] | `gp-0x6bd0` | `(x+0x800) < 0x1001` → **±2048** | seed / damper-presence lane |
| `0xC63A2` w[1] | `gp-0x6bbe` | `(x+0x800) < 0x1001` → **±2048** | **VISCOUS** + DC pedestal |
| `0xC63A4` w[2] | `gp-0x6b46` | `(x+0x400) < 0x801` → **±1024** | **unidentified — open item** |
| `0xC63A6` w[3] | `gp-0x6b26` | `(x+0x400) < 0x801` → **±1024** | **INERTIA** (`−K·α`) |
| `0xC63A8` w[4] | `gp-0x6b4e` | `(x+0x2800) < 0x5001` → **±10240** | **PROVABLY ≡ 0 — dead lane** |
| `0xC63AA` w[5] | `gp-0x6b4c` | `(x+0x2800) < 0x5001` → **±10240** | LKAS command lane |

🛑 **The gate is a ZERO-REJECT WINDOW, not a clamp.** `lane = (x * gate * w) >> 10` where
`gate = 1 if (x + halfwidth) < (2*halfwidth+1) else 0`. Outside the window the lane **vanishes**. It
tests the RAW pre-weight value, so raising a weight cannot trip its own gate (magnitude-safe), but
"structurally always open" is a **stronger and unproven** claim absent an upstream clamp.

⭐ `gp-0x6b70` is this function's **return value** (`*(short *)(gp-0x6b70) = (short)iVar9`). On-car data
(V96, routes 7e/7f) shows `gp-0x6b70` carries the engaged 7.8 Hz driver-torque ringing at coherence
0.95–0.97 ⇒ the crux is measured **in Path 2's own output**, making these six the only cal-only levers
directly on it.

## THE RECONCILIATION — `0xC63A0` INERT is a V64-class null, not evidence

Standing contradiction on record: a claimed inversion boundary at `0xC63A0` 1024→2048 should have
produced a large qualitative on-car change, yet it flew and measured INERT. **Resolved:**

1. `0xC63A0` weights **`gp-0x6bd0`** — NOT `gp-0x6b26`. Different signal, different gate.
2. `gp-0x6bd0` was **measured ~zero on-car**: V72's probe `|gp-0x6bd0| >= 64` read **0 / 87,940 frames**
   (0 / 34,275 above 35 km/h) — and **V72 is the very build carrying `0xC63A0 = 2048`**
   (cites [[reference_accord_gp6bd0_seed_ruled_out_and_engagement_gates_found]]).
3. ⇒ `0 × 2048 >> 10 = 0`. **INERT is exactly what the arithmetic predicts.** The experiment never ran.

🛑🛑 **CORRECTS MY OWN [[reference_accord_c63a6_gate_trace_forward_vs_closed_loop_sign_split]]**, which
issued NO-GO leaning on `0xC63A0` as "the structurally identical sibling" whose swept estimate crosses an
inversion boundary. **That import is INVALID** — identical arithmetic *form*, different *signal*, and the
sibling's on-car evidence is void because its lane was dead. **Strike the precedent.**
`0xC63A6` remains NO-GO, but for a *different and weaker-sounding but epistemically worse* reason: the
closed-loop sign is now **simply unknown** rather than "probably inverting". `L` (`FUN_0003b8f6`'s 8 float
coeffs at `tp+0x50d4/0x50d8/0x504c/0x5050/0x50bc/0x50d0/0x50d2/0x50d6` — ⚠ `tp+0x5000` = `0xC4000`, NOT
`0xC5000`) and `f'` (`FUN_000389ec`'s LERP slope) are still unmeasured by any session.

## Refutes `docs/STATE.md` §A5's V97 candidate (`gp-0x6b4c`/`gp-0x6b4e`)

- ✅ CONFIRMED: ±10240 each; "5× and 10× the other two lanes" (10240/2048=5×, 10240/1024=10×);
  `gp-0x6b4c` IS a direct unity-weight summand in Path 1 (`FUN_0003aa2c`: `iVar19 = gp-0x6b4c *
  gate(±10240)`, no cal multiply, no `>>10`) and is the **only term present in BOTH arms** of the
  `gp-0x67ac` branch ⇒ unconditionally live in Path 1.
- 🛑 REFUTED: "disjoint partition sums of the same 11-slot array `gp-0x62f8[]`". The array is
  **`gp-0x62c8`**. `gp-0x6b4e` ← `FUN_00042ac6` ← `FUN_00026c80`'s `gp-0x3d8c` ← `gp-0x62c8[0..10]` ≡ 0
  (per [[reference_accord_gp6afe_gp6b4e_provably_zero_correction]]; role dispatch `0xC4124` re-read fresh
  = `[0,0,5,0,5,5,0,0,0,5,0]`, **third independent census, exact match**; role 7 the only non-zero writer
  and absent).
- 🛑🛑 REFUTED AND INVERTED: "the V64-class null is excluded by arithmetic". For `gp-0x6b4e` it is
  **CERTAIN** — `0 × 0xC63A8 = 0` for any weight. **`0xC63A8` is unfliable.**

## Virginity (89 non-stock images, `sessions/v97/ledger_v97_virginity.py`)
`0xC63A2`/`A4`/`A6`/`A8`/`AA` are **VIRGIN across the entire corpus**. Only `0xC63A0` ever moved (8
images: v72, v72_SUPERSEDED, v73, v74, v75 ×2, **v76_gate_fb**, v81), and it is back at stock 1024 frozen
since V83a. ⚠ `docs/STATE.md` lists the flights as "V72, V73, V76g, V81" — **V74 and V75 are omitted**,
and they are the builds that hard-faulted on `0xC407E`, so part of "measured INERT" rests on aborted drives.

## Related
[[reference_accord_c63a6_gate_trace_forward_vs_closed_loop_sign_split]] — corrected by this file.
[[reference_accord_gp6afe_gp6b4e_provably_zero_correction]] — the `gp-0x6b4e ≡ 0` proof this leans on.
[[reference_accord_gp67ac_resolved_zero_and_path1_always_live]] — why Path 1's full sum always runs.
[[reference_accord_gp6b70_probe_spec_path_separation_and_gate1]] — the probe that would close GATE 2 for
all six weights at once.
