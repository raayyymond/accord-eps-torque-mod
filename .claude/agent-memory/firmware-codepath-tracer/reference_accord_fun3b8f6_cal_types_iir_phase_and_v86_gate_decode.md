---
name: accord-fun3b8f6-cal-types-iir-phase-and-v86-gate-decode
description: FUN_0003b8f6's cals are 3 floats + 6 u16 Q-format, NOT "8 float coefficients" — its FIR is an identity (taps 1,0,0); the four one-pole IIRs priced at a proof-verified 1 kHz; and V86's own probe decoded, showing its null was NOT a gating null.
metadata:
  type: reference
---

## The "8 float coefficients of `FUN_0003b8f6`" framing is WRONG
It is **three genuine floats + six unsigned HALFWORD Q-format cals**, and the handover list omitted
`0xC4048` — the only nonzero FIR tap. Types read from the **opcode** (`ld.w` + `mulf.s`/`maddf.s`
with no `cvtf` = float; `ld.hu` + `cvtf.uws` = u16), never from the value.

| addr | tp+ | load @ | type | stock | on car | role |
|---|---|---|---|---|---|---|
| `0xC4048` | 0x5048 | `0x3b9d2` | **float** | 1.0f | 1.0f | FIR tap b0 |
| `0xC404C` | 0x504C | `0x3b9de` | **float** | 0.0f | 0.0f | FIR tap b1 (x[n-1] @ `gp-0x363c`) |
| `0xC4050` | 0x5050 | `0x3b9ee` | **float** | 0.0f | 0.0f | FIR tap b2 (x[n-2] @ `gp-0x3638`) |
| `0xC40BC` | 0x50BC | `0x3bab4` | u16 | 600 | 600 | Coulomb relay divisor |
| `0xC40D0` | 0x50D0 | `0x3bb22` | u16 | 408 | 408 | IIR alpha `/4096` |
| `0xC40D2` | 0x50D2 | `0x3bafe` | u16 | 102 | **204** | K1, **Q10** (`x*0.0009765625`) — V89 |
| `0xC40D4` | 0x50D4 | `0x3b94e`,`0x3b96a` | u16 | 573 | 573 | IIR alpha, **x2 cascade** |
| `0xC40D6` | 0x50D6 | `0x3bb60`,`0x3bb8a` | u16 | 246 | 246 | IIR alpha, **x2 cascade** |
| `0xC40D8` | 0x50D8 | `0x3b98e`,`0x3b9a2` | u16 | 3686 | 3686 | IIR alpha, **x2 cascade** |
| `0xC4080` | 0x5080 | `0x3baf6` | u16 | 0 | 0 | constant-Coulomb term — **zero ⇒ dead** |

**The float block is an IDENTITY.** `0x3b9d2..0x3ba04`: `y[n] = 1.0*x[n] + 0.0*x[n-1] + 0.0*x[n-2]`
⇒ **|H| = 1.000, phase 0.000 deg at every frequency.** Confirms
[[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]] from the flash bytes.
Anchors that validate the decode: `0xC40BC`=600 (relay gate), `0xC40D2` 102→204 = V89's K1 at Q10
(0.0996→0.1992), and `ld.hu 0x7468[tp]` ⇒ `0xC6468` = 2639.

## Rate = 1000 Hz — PROVEN two ways, not inherited
**Structural:** `FUN_0003b8f6` (`jarl 0x2240e`) and `FUN_00038148` (`jarl 0x22676`) are both called
in `FUN_0002214a` under the **identical** guard `uVar4 = (1 << (gp-0x67fa & 0xf)) & 0x830` — same
variable, same expression, **no counter/modulo/decimation between them**. (`0x830` = states 4/5/11,
a STATE mask — re-confirms [[reference_accord_fun2214a_is_state_mask_not_phase_divider_loop_all_1khz]].)
**Numerical:** fs=1000 reproduces `0xC63AC`=102's known −18.7/−23.6/−26.8° to **0.07°**;
500/200/100 Hz miss by 17/37/45°. ⊕ `0xC40D0`/4096 = **exactly** 102/1024.

## The four IIRs priced (`y += (x-y)*cal/4096`, from `0x3b956`/`0x3b95e`/`0x3b966`)
| cal | val | x | fc | @6 Hz | @7.79 Hz | @9 Hz |
|---|---|---|---|---|---|---|
| **`0xC40D6` accel/inertia** | 246 | 2 | **9.86 Hz** | 0.730/−60.5° | 0.616/**−73.9°** | 0.546/−81.6° |
| `0xC40D4` torque input | 573 | 2 | 24.0 Hz | 0.941/−26.0° | 0.905/−33.3° | 0.877/−38.0° |
| `0xC40D0` friction | 408 | 1 | 16.7 Hz | 0.941/−18.7° | 0.906/−23.6° | 0.880/−26.7° |
| `0xC40D8` `gp-0x4f60` | 3686 | 2 | 366 Hz | 1.000/−0.5° | 1.000/**−0.6°** | 1.000/−0.7° |

- **`0xC40D6` is the dominant phase element in the whole function** — corner sits on the 7.79 Hz
  ring, 2.2x `0xC40D4`, on the **acceleration** term. **VIRGIN in 92/92 images.**
- 🛑 **`0xC40D8` is a PASS-THROUGH (−0.6°). It is a NO-OP — reject any proposal to move it.**
- Ledger from the images: `0xC40D0` 408 in 92/92 VIRGIN · `0xC40D4` 286 in **exactly one** image
  (`_v86`) · `0xC40D6` 246 in 92/92 VIRGIN · `0xC40D8` 3686 in 92/92 VIRGIN.

## V86's null was NOT a gating null — its own probe says so
`0xC40D4` 573→286 gives **gain x0.759, Δphase −32.1° @7.79 Hz** on `fVar18`, the dominant term of
`iVar6` (`0x3bc1a` → `0x3bc3e` → `0x38218`). Measured **1.001 [0.976, 1.060]** vs pre-registered
[0.797, 0.875]. **So the phase model predicts V86 should have worked and it did not.**
`_v86` carried `PROBE.6B70.SIGN-GATE.67AB`. Decoded with the kit's own `decode_v86_probe.py`
(self-test PASS), route 6f, 23,058 frames / 232 s:
```
FINGERPRINT b3 = 1.0000   GATE b4 = 1.0000  <- gp-0x67ab < 2, ZERO frames with the gate clear
NONZERO     b6 = 0.9975   MAG  b5 = 0.8822  (engaged 0.945 vs manual 0.782)
SIGN        b7 = 0.5461   6-20 km/h window: gate 1.0000, nonzero 0.9988
```
⇒ lane in circuit 100%, live, substantial, engagement-sensitive, cal byte-verified in force.
**A real null on a live lane.** Best reconciliation: **closed-loop suppression** — `FUN_0003b8f6`'s
input `gp-0x6b98` is the **FOC motor command, the loop OUTPUT**, so this filter sits *inside* the
loop where a forward perturbation is suppressed by `1/(1+L)`. Same mechanism the kit invoked for
V91/V92. 🛑 **Applies to the lane weights too**, and a viscous lane proportional to the rate it damps
self-cancels ⇒ **any lane-weight build needs a LARGE dose scored on the ring amplitude, never on the
lane's own value.** ⊕ `gp-0x67ab` is a fault latch (1 writer `0x2775c` in `FUN_00026c80`).

🛑 Route 70 (V86B) carries the same probe with **different bit wiring** (cave bytes `443a` vs
`423a`) — `decode_v86_probe.py` must NOT be pointed at it. A V86B-correct decoder makes r6f-vs-r70
a matched single-variable pair on `0xC40D4` with the sign probe live on both.

⊕ `gp-0x6bfe`/`gp-0x6bfa` are REAL, distinct, live cells, **not** an off-by-2 on `6bfc`/`6bf6`:
`FUN_0003bc20` @`0x3bc3e` writes `gp-0x6bfe` = range-validated `gp-0x6bfc` (health `gp-0x695c`);
`gp-0x6bfa` written 3x in `FUN_00026c80` (`0x273b0`/`0x273c8`/`0x273d6`). Both producers run
*earlier* in the same task pass than `FUN_00038148` ⇒ **no extra tick on either.**

Scripts: `analysis-2020accord/_v97/read_L_coeffs.py`, `_v97/price_the_iirs.py`,
write-up `_v97/close_the_sign.md`. See also [[accord-ram-lerp-is-flash-derived-and-fprime-nonneg]].
