---
name: v40-governor-slew-root-cause
description: "SUPERSEDED 2026-07-20. V40 flashed and killed power steering at ignition; V41 flashed and fixed neither symptom. The motor-rate cap is FALSIFIED and the slew-as-vibration story is WRONG."
metadata:
  node_type: memory
  type: project
  originSessionId: 6a579c19-b22f-4385-a786-8205eb6c7a7e
  modified: 2026-07-20T02:41:18.403Z
---

**⚠ THIS MEMORY'S ORIGINAL CONCLUSION IS SUPERSEDED. Read the correction first.**

**2026-07-20 road results.** V40 was flashed → **immediate EPS lamp + power steering fully disabled at ignition**. V41 (V38 + the cap flatten only, `0xC6000` untouched) was flashed → **boots and drives cleanly, and fixed NEITHER symptom.**

**Three corrections of record:**

1. **The motor-rate adaptive cap is FALSIFIED as a root cause.** V41 flattened it exactly as designed and neither the ratchet nor the vibration changed. The arithmetic in the original note (stock's 417 sits below the 512 floor, so stock LKAS can never be rate-capped) is still correct — but its on-car prediction failed. Do not spend another build here.

2. **V40's ignition fault is attributable to `0xC6206`/`0xC6208` ← `0xFFFF`,** because V41 contains V40's entire cap edit and boots fine. But the mechanism is NOT a sign or overflow bug: both cals load **`ld.hu` (unsigned)** at `0x45410`/`0x45416`, the Q15 multiplicand is provably bounded to [0, 32768] (literal `0x8000` seed + MIN-only chain), `65535 × 32768 < 0x80000000`, and the slew guard is self-bounded so nothing can wrap. What `0xFFFF` actually did was make the guard **never fire** → snap-to-target → rate limiting removed entirely. Inferred fault path: unfiltered command → `FUN_0004595a`/`FUN_00045a20` (same `0xd30` state gate as the governor) → `FUN_00016de6(0x1d)` → hard-fault-eligible with **no debounce** → motor off. **The defect was the magnitude, not the direction of the edit.**

3. **The "sign-crossing reset explains the small-command vibration" claim is WRONG.** After a reset the output is capped to ±step from zero, so when |target| < step the target passes through unchanged — small commands are unaffected. The reset cannot produce a small-command vibration. See [[reference-accord-gain-rescaling-invariance-partition]] for why the vibration cannot be downstream of the gain at all.

**What survives:** the step-selector trace (`gp-0x67f5`, pinned slow at 205 during hard turns) and the ramp-time observation are both still valid. But the ratchet's actual root cause is the state-4 governor substitution — see [[reference-accord-state4-governor-ratchet]].

**Also retracted from the original note:** the "16-phase duty cycle" reading of `andi 0xd30,r25`. `r25 = 1 << (gp-0x67fa & 0xf)` and `gp-0x67fa` is the **ECU state-machine byte**, so those masks select *states*, not tick phases. Every Hz figure derived from a 4/16 or 5/16 duty cycle is invalid.

**How to apply:** treat V40 and V41 as two clean subtractive experiments that between them eliminated the cap, the CRC-block theory, and the naive slew fix. Related: [[v39-flashed-no-improvement]], [[reference-crc-chain-is-50-blocks-c5000-not-a-gap]], [[feedback_eps_lkas_chain_model_golden_reference]].
