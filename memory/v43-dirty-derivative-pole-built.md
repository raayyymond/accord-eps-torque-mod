---
name: v43-dirty-derivative-pole-built
description: "V43 BUILT + independently verified, UNFLASHED — V38 + 11 bytes; keeps V42's confirmed ratchet fix, reverts r26, and lowers cal 0xC644A 1024→64 to restore a DISABLED dirty-derivative pole. V44 candidate (governor STEP selector) already safety-reviewed."
metadata: 
  node_type: memory
  type: project
  originSessionId: 1b5347d0-4bca-4b24-acf8-731450f48b64
  modified: 2026-07-20T06:30:34.872Z
---

**V43 = V38 + exactly 11 bytes in 4 runs. BUILT, independently verified, NOT FLASHED.**
`analysis-2020accord/build_v43_tva.py` · `docs/HANDOFF-2026-07-21-v43-dirty-derivative-pole.md`
V43 SHA-256 `6591dde5…0e7eb2ea` · RWD `adacdbfc…721715f6`

| Address | Change |
|---|---|
| `0x454FE` | `bne`→`br` — **KEPT from V42 verbatim, confirmed on-car, NOT under test** |
| `0xC644A` | `1024 → 64` — restore the disabled dirty-derivative pole |
| `0xC4FFC`, `0xC6FFC` | CRC trailers |

**Reverted:** V42's r26 zeroing, asserted back at stock (with a positive check that it *was* zeroed in
V42, so the revert is real). See [[v42-flashed-ratchet-fixed-r26-falsified]].

**The edit.** `0xC644A` is the EMA gain on the lag sitting immediately downstream of a **raw one-sample
difference** in [[reference-accord-fun3a382-unfiltered-residual-lane]] — the classic "dirty derivative"
pole, pinned at Q10 unity i.e. **switched off**. GAIN=64 gives α=0.0625, τ≈15.5 cycles.

**Why band-limit rather than zero the term.** The **sign of Stage C could not be settled from the bytes**
— it resolves only through `gp-0x6752`'s static value *and* a physical wiring convention, the same
irreducible gap already on record for r24/r26. A residual-feedback derivative is classically an *active
damper*, and this kit has already removed derivative feedback twice (V39, V42) while chasing this
vibration. **Band-limiting is sign-agnostic**: damping or anti-damping, it preserves low-frequency action
and removes only the tens-of-Hz content.

**DC claim, stated precisely** (the headline "changes no steady-state value" is too strong): in real
arithmetic the EMA fixed point is `target*32` for any nonzero GAIN, but V850 `sar` floors toward −∞, so
approaching from *below* can stall within `(target − 1024/GAIN, target]`. The residual is real, **one-sided**
(under-reports a sustained *rising* derivative), and bounded by **≈32/GAIN counts** — ≤0.5 at GAIN=64.
Verified two independent ways that agree: integer simulation (15 state-counts) and analytic bound (16).
⚠ **Below roughly GAIN=16–32 the residual stops being negligible — that is the floor on this lever.**
🛑 **GAIN=0 is degenerate** — the state freezes and never converges. Never round down to zero.

**V44 candidate, already safety-reviewed and NOT in V43:** the governor slew-STEP selector `gp-0x67f5` is
driver-torque-gated (vote of `gp-0x6a5e` vs cal `0xC531E`=1062, debounced `0xC64E7`=10 cyc) → STEP 512
hands-off / 205 hands-on. A rate limit is a bandwidth gate whose corner scales as 1/amplitude: ~195 Hz at
stock's 417-count lane, **~46 Hz at V38's 1782** — so V38 is the first build where it binds in the symptom
band. Held back because it touches the *main* command path (the cal V40 mis-set) and attenuates only 2.5×.
A review tried to break `0xC6206` 512→205 and could not; notably `FUN_0004595a`, the only monitor comparing
output against target, explicitly *tolerates* output lagging target.

**Recorded, deliberately NOT shipped:** `0x345fa` reads the SIGNED `gp-0x6ac0` with `ld.hu`, so the
`gp-0x6bd0` damping term is unconditionally **zero for one rotation direction** — a half-wave-rectified
damper. Fixing it would activate a term never active in that direction in *any* build including stock,
violating this kit's rule: **widen an already-live path, do not invent one**.

⚠ **No post-V38 driving telemetry exists.** Route `807a3c21c9f405e8_000000ac` is on disk but segment 0
only (parked). Pulling segments 1+ would give the kit's first V38-era data; CAN 399 is 100 Hz so the
vibration band is observable to 50 Hz. Analysis script ready in the session scratchpad.
