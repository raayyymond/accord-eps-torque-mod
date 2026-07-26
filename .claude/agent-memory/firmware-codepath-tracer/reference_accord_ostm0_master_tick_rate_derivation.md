---
name: reference-accord-ostm0-master-tick-rate-derivation
description: Independent derivation attempt for the master RTOS tick rate via OSTM0's reload/compare register. VERIFIED reload value (0x1387F=79487, interval-timer mode) at two boot sites. INFERRED target rate ~1kHz via a plausibility match against 80MHz (a documented valid CPU clock for this chip) -- NOT independently verified against the actual configured clock tree, which could not be traced from the available SVD, and the OSTM0-ISR-to-task-dispatch linkage was not confirmed via static call graph either. Reports exactly what would close both gaps.
metadata:
  type: reference
---

Traced 2026-07-21, tasked by team-lead to independently derive the master RTOS tick rate (the open
100Hz-vs-1kHz question underlying [[reference-accord-gp6a5e-voter-bandwidth-insufficient-for-21hz]] and
[[reference-accord-fun41464-sign-filter-phase-response]]), deliberately without coordinating with a
parallel tracer working the same question via a different route.

## Route taken: OSTM0 (OS Timer 0) reload register

Per the SVD (`analysis-2020accord/svd_for_ghidra/UPD70F3508_V850E2Px4.svd`): `OSTM0` base
`0xFF800020` (`OSTM0CTL` at offset 0), register cluster at `0xFF800020+0x7FBFE0 = 0xFFFFC000`
(`OSTM0CMP`, the down-counter start/compare value, 32-bit).

## VERIFIED: reload value and mode, two independent write sites

**Site 1 — earliest boot code, `FUN_000003b4` (executed essentially at reset):**
```
0x3d8: mov 0x13880, r1          ; literal 79488
0x3de: st.w r1, -0x4000, r0     ; -0x4000[r0] = 0xFFFFC000 = OSTM0CMP
```

**Site 2 — main scheduler's one-time init block, `FUN_00014c5c` (the SAME function that runs the
top-level `do{...}while(true)` RTOS dispatch loop on `gp-0x67fa`):**
```
0x14c86: movhi -0x80,r0,r17      ; r17 = 0xFF800000
0x14c8a: st.b  r28,0x20,r17      ; OSTM0CTL = r28 (=1, per the decompile: "DAT_ff800020 = 1")
0x14c8e: mov   0x1387f,r13       ; literal 79487  (ONE LESS than site 1's value)
0x14c94: st.w  r13,-0x4000,r0    ; OSTM0CMP = 79487
```
`OSTM0CTL=1` sets `OSTMnMD0=1` (start-of-counting interrupt enabled) with `OSTMnMD1=0` (interval timer
mode — auto-reloading periodic interrupt, per the SVD's register description). **This is a genuine
periodic hardware timer, reload ≈79,487-79,488 counts** (the 1-count discrepancy between the two sites
is negligible for a rate computation — both taken as strong corroboration of the same target, one being
an earlier/bootstrap config and the other the final application value).

## INFERRED, moderate-high confidence: target rate is ~1 kHz, via clock-plausibility, NOT a traced clock tree

I could not trace OSTM0's actual counting clock from the SVD (no PLL/clock-generator peripheral is
modeled in it under any name I searched — `CKC`, `CSC`, `PLL`, `MOSC` all came up empty except unrelated
protection-register and baud-rate-generator hits) or from the datasheet (`UPD70F3508GJA2-GBG-AX-1.pdf` —
the `Read` tool's PDF page rendering is unavailable in this environment, `pdftoppm`/poppler-utils not
installed; I could not open it at all).

**Plausibility check against the one clock fact the SVD DOES give**: `DFLASH.DCLKWAIT`'s field
description documents four valid CPU/system-clock options for this chip family — **48/64/80/160 MHz**.
Computing the OSTM0 tick frequency for the verified reload (79487) at each:

| candidate clock | resulting OSTM0 tick |
|---|---|
| 48 MHz | 603.9 Hz |
| 64 MHz | 805.2 Hz |
| **80 MHz** | **1006.4 Hz** |
| 160 MHz | 2012.9 Hz |

**80 MHz gives, by a wide margin, the closest match to a clean engineering target (1 kHz)** — 0.6% off,
the kind of small residual you'd expect from picking the nearest integer reload count to a 1ms target
against a real (non-power-of-2-friendly) clock, not a coincidence. None of the other three candidates
land near any similarly clean number. **I did NOT verify that OSTM0's counting clock is actually 80MHz
CPU clock** (vs. a divided PCLK, which is common on this family and could shift the answer) — this is an
inference from a strong numerical coincidence plus one documented valid clock option, not a traced
configuration.

**My independent conclusion: the master tick is very likely TARGETED at 1 kHz (≈1006 Hz as actually
configured, if the 80MHz inference holds), not 100Hz.** I'd put this at moderate-high confidence — high
enough that I would not budget for the 100Hz hypothesis being correct, but not "verified" in the sense
this kit uses the word.

## Two gaps I could not close — exactly what would settle them

1. **The actual OSTM0 counting clock.** Found candidate PLL/clock-generator writes in the SAME earliest
   boot function (`FUN_000003b4`, `0x3be-0x3ca`: `st.h 0x40,-0x7cec[r0]` then `st.h 0x1c6,-0x7bec[r0]`,
   i.e. writes to `0xFFFF8314`/`0xFFFF8414`) that are very plausibly clock-generator setup (sequential,
   early, protected-register-shaped) but **I could not map these addresses to the SVD** (no peripheral
   is defined at that range under any name I tried) or interpret `0x40`/`0x1C6` as multiplier/divider
   bit-fields without the datasheet's clock-generator register map. **Reading the datasheet's clock
   generator chapter (need `poppler-utils` installed, or an alternate PDF-to-text path) against these two
   register writes would directly settle this** — that's a very short, targeted read once the tool
   works, not a broad investigation.
2. **Whether OSTM0's interrupt is what actually paces `FUN_00022ca0`/`FUN_0002214a`** (the two task
   bodies whose `gp-0x67fa`-state-gated calls this whole investigation depends on). `get_function_callers`
   on both returns zero static callers — same function-pointer-dispatch blind spot this kit has already
   hit elsewhere (the CAN TX builders). I did not find or trace OSTM0's interrupt vector/ISR to confirm
   it's the thing that invokes these task bodies (directly, or via a flag a background loop polls) rather
   than some OTHER periodic source. **Finding OSTM0's specific entry in the interrupt vector table**
   (confirmed present at low addresses, `0x0-0x244`ish, standard V850E2 EIINTn 16-byte-spaced vectors —
   I did not have OSTM0's specific vector NUMBER to jump to it directly) **and reading forward from there
   would close this gap.**

## What I did NOT attempt this session
Did not pursue the CAN-399-measured-100.01Hz corroboration route — team-lead flagged it as possibly
cleanest, but tracing the CAN TX scheduler's periodic-dispatch counter back to a divisor of the master
tick independently (without leaning on this kit's existing scheduler-table memory, per the
don't-coordinate instruction) looked like comparable effort to what's above, and I judged the OSTM0
route already in progress a better use of remaining budget. Flagging as the natural next avenue if this
thread continues — a firmware-side counter that increments once per OSTM0 fire and is checked against a
literal divisor before the CAN-399 packer runs would pin the ratio directly, independent of the clock
question entirely.

## Related
[[reference-accord-gp6a5e-voter-bandwidth-insufficient-for-21hz]] — depends on this rate
[[reference-accord-fun41464-sign-filter-phase-response]] — depends on this rate, corrected version
