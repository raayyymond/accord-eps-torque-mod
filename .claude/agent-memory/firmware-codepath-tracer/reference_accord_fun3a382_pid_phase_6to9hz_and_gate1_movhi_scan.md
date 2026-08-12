---
name: reference_accord_fun3a382_pid_phase_6to9hz_and_gate1_movhi_scan
description: FUN_0003a382's PID phase RECOMPUTED at 6-9Hz from a fresh full decompile (not extrapolated from the existing 21Hz figure) -- P is 3-5x less dominant and net phase lag is 3-5x larger than at 21Hz, because P/D carry an implicit x32 the plain accumulator I never gets. Also: whole-image movhi/0xfedf scan is CLEAN (0 hits) -- GATE-1 for gp-0x6b70 (and generally, absolute-address register-indirect RAM access) closed.
metadata:
  type: reference
---

# PID phase at 6-9Hz [EVIDENCE, fresh decompile] + GATE-1 movhi/fedf scan [EVIDENCE, clean]

## 🛑🛑 STANDING-RECORD CORRECTION, not a refinement (team-lead's framing, 2026-08-11)

**Every closed-loop argument this kit has made about the ratchet/micro-ratcheting band (6-9Hz) that reused
the existing 21Hz PID phase figure (`-3.3° to -5.4°`, `~8-10:1` P-dominance) was using the WRONG number.**
At 6-9Hz the net phase lag is **3-5x larger** (`-11° to -27°`, see table below) and the integrator — a
negligible contributor at 21Hz — is a **co-equal term**, not a rounding error, in this band. This is not a
tighter estimate of the same quantity; the two bands are qualitatively different regimes for this PID. Any
prior or future sign/stability claim for a Path-2 weight (`0xC63A2` included) or any other 6-9Hz mechanism
that leaned on the 21Hz PID characterization needs to be re-checked against the numbers below, not assumed
to still hold.

2026-08-11, `lane-weights-6bf`, for team-lead's `gp-0x6b70` probe. Both requested as "cheap, do it now"
items on top of [[reference_accord_gp6b70_probe_spec_path_separation_and_gate1]].

## GATE-1: whole-image `movhi`/`0xfedf` scan — 0 hits

`gp=0xFEDF8000`; any absolute-address construction into the RAM region holding every gp-relative variable
needs a `movhi` loading the upper halfword `0xFEDF` first. `search_instructions(mnemonic="movhi",
operand_pattern="fedf")`: **0 hits, whole image, 183,570 instructions scanned.** Combined with the earlier
`search_instructions("6b70")` census (2 real hits: sole write `FUN_00038148`@`0x382d2`, sole read
`FUN_00037fe6`@`0x38006`; 19 of 21 raw hits are `jarl 0x0006b700,lp` text collisions with an unrelated
call target), this closes the register-indirect/absolute-address concern for `gp-0x6b70` specifically, and
more generally shows NO code anywhere constructs an absolute RAM pointer via `movhi` — a broader clean
result than just this one cell. Residual, theoretical only: an array-base register could coincidentally
index onto `gp-0x6b70` without ever spelling `0xFEDF` — no evidence this happens, not exhaustively provable.

## PID phase at 6-9Hz — recomputed from the exact combining arithmetic, not extrapolated

Fresh full decompile of `FUN_0003a382` (`0x3a382`) exposed the exact P/I/D combine, which the existing
21Hz-only record (`reference-accord-fun3a382-engagement-gated-residual-loop.md`,
`reference-accord-fun3a382-pid-structure-aggregator-addsign-and-freqresponse.md`) didn't spell out at the
arithmetic level:
```c
P_raw   = (err_c * L1) >> 10                         // L1 = LERP(gp-0x6ac0=motor rate), table @0xC6B20, range [153,256]
P_state = P_prev + ((P_raw*32 - P_prev) * cal(0xC6450)) >> 10     // cal=1024=UNITY at stock -> P_state = P_raw*32

I_state = I_prev + (err_c * L2) >> 10                 // PLAIN ACCUMULATOR, NO x32 -- L2 flat 98/1024 (established)

D_raw   = (err_c[n]-err_c[n-1]) * L3 >> 10             // L3 flat 2.0 (established)
D_state = D_prev + ((D_raw*32 - D_prev) * cal(0xC644A)) >> 10     // cal=UNITY at stock (established) -> D_state = D_raw*32

combined = (D_state + I_state + P_state) >> 5          // the >>5 cancels P's/D's x32 but I never had it
```
**The asymmetry that matters**: P and D are implicitly **32x "louder"** than I going into the sum, purely
structurally (their own unity-alpha EMA multiplies by 32 before storing state; I's plain accumulator
never does). This reduces `P_state(f)/err_c(f) = L1/32` exactly (pure real, 0° phase) — verified against
the EXISTING 21Hz phase-lag bounds (−3.3° to −5.4° across L1∈[153,256]): back-solving those two numbers
independently against my own I/D phasors gives effective-P = 4.81 and 7.94, matching `153/32=4.78` and
`256/32=8.0` to <1%. I(f) and D(f) formulas (verified to 3 sig figs against the recorded 0.726∠−86.2° and
0.264∠+86.2° at 21Hz):
```
|H_I(f)| = L2 / (2 sin(pi f/fs)),      phase_I(f) = 180 f/fs - 90deg
|H_D(f)| = 2 L3 sin(pi f/fs),          phase_D(f) = 90deg - 180 f/fs
```

**Recomputed at fs=1000Hz, target band, L1 range [153,256] unchanged**:

| f | net phase lag | P:(I+D) magnitude ratio |
|---|---|---|
| 21 Hz (recorded, for comparison) | −3.3° to −5.4° | ~8-17:1 (my own recompute; source text's "8-10:1" is close but not exact — the phase match is far tighter, trust phase over this ratio) |
| 6.0 Hz | **−17.0° to −27.0°** | **1.9:1 to 3.3:1** |
| 7.79 Hz | **−13.0° to −21.0°** | **2.6:1 to 4.3:1** |
| 9.0 Hz | **−11.1° to −18.1°** | **3.0:1 to 5.1:1** |

**Finding**: the PID is 3-5x less proportional-dominated at 6-9Hz than at 21Hz, with net phase lag 3-5x
larger. The integrator (negligible contributor at 21Hz) is a genuine co-equal term at 6-9Hz. **Any
closed-loop sign/stability argument for `0xC63A2` that reuses the 21Hz PID phase figure is using the wrong
number** — the two bands are not close enough to treat as interchangeable.

## Related
[[reference_accord_gp6b70_probe_spec_path_separation_and_gate1]] — the probe spec this closes two open
items for. `reference-accord-fun3a382-engagement-gated-residual-loop.md` (repo memory) — source of the
21Hz figures this recompute extends and the L1/L2/L3 table identities (0xC6B20/L2 flat 98/L3 flat 2.0)
reused here without re-deriving.
