---
name: reference-accord-fun3a382-pid-phase-6to9hz-standing-correction
description: STANDING-RECORD CORRECTION -- the existing PID phase figure for FUN_0003a382 (net phase lag -3.3 to -5.4 deg, P:(I+D) ~8-10:1) was measured at 21Hz and does NOT transfer to 6-9Hz. Recomputed from the exact combining arithmetic -- net phase lag is -11 to -27 deg and P:(I+D) collapses to ~2-5:1 at 6-9Hz, because P and D each carry an implicit x32 from their own unity-alpha EMA that the integrator's plain accumulator never gets. Any argument for the 6-9Hz ratchet band that reused the 21Hz figure needs re-checking.
metadata:
  type: reference
---

# 🛑🛑 STANDING-RECORD CORRECTION: the PID's 21Hz phase figure does not transfer to 6-9Hz

**Any closed-loop sign/stability argument about the 6-9 Hz ratchet/micro-ratcheting band that reused the
existing PID phase figure (measured at 21 Hz: net phase lag −3.3° to −5.4°, P-dominance ~8-10:1) was using
the wrong number.** At 6-9 Hz the net phase lag is 3-5x larger and the integrator — negligible at 21Hz —
is a co-equal contributor. This is not a tighter estimate of the same quantity; the two bands are
qualitatively different regimes for this PID.

## The exact combining arithmetic [EVIDENCE, fresh decompile of `FUN_0003a382`]

```c
P_raw   = (err_c * L1) >> 10          // L1 = LERP(gp-0x6ac0 = motor rate), table @0xC6B20, range [153,256]
P_state = P_prev + ((P_raw*32 - P_prev) * cal(0xC6450)) >> 10     // cal=1024=UNITY at stock -> P_state = P_raw*32

I_state = I_prev + (err_c * L2) >> 10  // PLAIN ACCUMULATOR, NO x32 -- L2 flat 98/1024

D_raw   = (err_c[n]-err_c[n-1]) * L3 >> 10   // L3 flat 2.0
D_state = D_prev + ((D_raw*32 - D_prev) * cal(0xC644A)) >> 10     // cal=UNITY at stock -> D_state = D_raw*32

combined = (D_state + I_state + P_state) >> 5   // the >>5 cancels P's/D's x32, but I never had one
```
`err_c` is the PID's clamped error input (`gp-0x4f60 - clamp(gp-0x6ad6, ±8192)`, clamped ±0x2800).

**The architectural asymmetry**: P and D are implicitly **32x louder** than I going into the final sum, by
construction — their own unity-alpha smoothing stage multiplies by 32 before storing state; the
integrator's plain accumulator never does. This is not a tuning choice on any build; it is how the
function is built. It reduces `P_state(f)/err_c(f) = L1/32` exactly (pure real, 0° phase, frequency-
independent).

## Verified against the existing 21Hz figures, then recomputed at 6-9Hz

```
|H_I(f)| = L2 / (2 sin(pi f/fs)),      phase_I(f) = 180 f/fs - 90deg
|H_D(f)| = 2 L3 sin(pi f/fs),          phase_D(f) = 90deg - 180 f/fs
```
Both match the recorded 21Hz values (0.726∠-86.2° for I, 0.264∠+86.2° for D) to 3 significant figures.
`P_state(f)/err_c(f) = L1/32` was verified the same way: back-solving the recorded 21Hz phase-lag bounds
(−3.3° to −5.4° across L1∈[153,256]) against these I/D phasors independently gives effective-P = 4.81 and
7.94 — matching `153/32=4.78` and `256/32=8.0` to <1%.

**Recomputed at fs=1000Hz, target band, same L1 range:**

| f | net phase lag | P:(I+D) magnitude ratio |
|---|---|---|
| 21 Hz (recorded, for comparison) | −3.3° to −5.4° | ~8-10:1 recorded; my own recompute of the same point gives ~8-17:1 — close but not exact, trust the phase match over this ratio |
| 6.0 Hz | **−17.0° to −27.0°** | **1.9:1 to 3.3:1** |
| 7.79 Hz | **−13.0° to −21.0°** | **2.6:1 to 4.3:1** |
| 9.0 Hz | **−11.1° to −18.1°** | **3.0:1 to 5.1:1** |

## Related
[[accord-anti-damping-is-not-the-pid]] — the P/I/D-at-6-9Hz result (net −0.121, damping) this makes the exact arithmetic and the 21Hz-vs-6-9Hz gap explicit for.
[[accord-gp6b26-is-inertia-not-damping]] — a companion standing-record correction on the same 6-9Hz band, same class of error (an assumed mechanism turning out to be structurally wrong).
[[reference-accord-78hz-mode-characterisation]] — the ratchet's own physical characterization (Q≈14, ring-down) at the same frequency this PID correction concerns.
[[accord-plant-model-residual-aggregator-chain]] — the chain this PID sits inside.
