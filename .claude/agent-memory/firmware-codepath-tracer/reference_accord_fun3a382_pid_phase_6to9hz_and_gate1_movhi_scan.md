---
name: reference_accord_fun3a382_pid_phase_6to9hz_and_gate1_movhi_scan
description: "🛑 RETRACTED 2026-08-14 — the PID-phase half of this file is an ARITHMETIC BUG (P and I quoted in x32 units, D in x1, understating D by exactly 32x). The PID is in LEAD at 6-9Hz (-0.9 / +8.2 / +13.3 deg), NOT a -11..-27 deg lag. Use reference-accord-fun3a382-is-a-real-pid instead. The movhi/0xfedf GATE-1 scan half is UNAFFECTED and still valid."
metadata:
  type: reference
---

# 🛑🛑 RETRACTED — THE PID-PHASE HALF OF THIS FILE IS WRONG. READ THIS BEFORE ANYTHING BELOW.

**Retracted 2026-08-14 by `gate2-pid`, verified by the orchestrator from the image.**

> **THE BUG: this file quotes P and I in ×32 units and D in ×1 units, understating D by EXACTLY 32×.**

```
at 21 Hz     |H_P| x1 = 0.2500   x32 = 8.0000        |H_D| x1 = 0.2637   x32 = 8.4385
this file's own row:   P_eff = 8.0   I = 0.726   D = 0.264
   P 8.0   == Kp x32   -> the x32 form
   D 0.264 == |H_D| x1 -> the x1 form          => D understated by exactly 32x
```
**Proof it is the bug and not a different convention: feeding the mixed units back in reproduces this
file's own output table to 0.1° at ALL FOUR frequencies** (−17.0 / −13.0 / −11.1 / −3.3).

**THE CORRECT VALUES — the PID is in LEAD at 6–9 Hz, not in lag:**
```
              6.0 Hz   7.79 Hz   9.0 Hz    21 Hz
this file      -17.0     -13.0     -11.1     -3.3     <- WRONG
CORRECT         -0.9      +8.2     +13.3    +41.8     <- a LEAD
```
And **P does NOT dominate I+D by 2–5:1** — by 21 Hz **|D| ≈ |P|**. The PID's lead/lag crossover is
**5.5 Hz**; there is **no −180° crossing** in this band to have a phase margin against.

**Authoritative figures: `reference-accord-fun3a382-is-a-real-pid`** (cross-validated two ways there,
and a third time by an independent integer time-domain sim of `pid_step` agreeing to 4 dp at
3/5/8/21 Hz). The **V87 handoff is also right** (*"PID is in LEAD at 8.21 Hz, +10.08°"*); this file was
the outlier.

✅ **Provenance chased: NO BUILD was sized on the bad figure.** Every `build_v*.py` was grepped for the
four lag values; the three hits (v43, v44, v99) are coincidental numeric matches — v43's is a frequency
band, not a phase. **No image carries a decision made on it.**

⚠ **A sibling file, `reference_accord_fun3a382_engagement_gated_residual_loop.md:162`, carries the
superseded −3.3°/−5.4° figure — that is the *21 Hz* value quoted WITHOUT ITS BAND**, the same
band-scoping defect that made the Kd pair look contradictory.

✅ **THE SECOND HALF OF THIS FILE — the whole-image `movhi`/`0xfedf` GATE-1 scan — IS UNAFFECTED AND
STILL VALID.** Only the PID-phase argument is retracted.

---

## ⚠ EVERYTHING BELOW IS THE RETRACTED ARGUMENT — retained for provenance only. DO NOT QUOTE IT.

## ~~🛑🛑 STANDING-RECORD CORRECTION, not a refinement (team-lead's framing, 2026-08-11)~~

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
