---
name: accord-gp6752-is-negative-one
description: "gp-0x6752 (the PID/r24/r26 polarity multiply) is -1, NOT +1 — verified three ways. Reverses the PID sign classification the kit carried since V38 and makes r24/r26 a confirmed pump at 6-9 Hz."
metadata:
  type: reference
---

🛑🛑 **`gp-0x6752` = **−1**, not +1.** Three memory files asserted *"boot-fixed to +1"*; **all three
inherited an incomplete writer census the record had itself already flagged as a lower bound**
(`feedback-a-count-is-not-a-physical-fact`: *"a disp16 scan is blind to the 6-byte form ⇒ a lower bound,
not a count"*).

## THE MISSED WRITER
`FUN_00048a40`, called once per boot-time config record, overwrites `FUN_000490ac`'s +1 pre-seed:
```
0x48E66  mov 0x1, r10  ; st.b r10,-0x6752,gp   <- record byte+4 = 0x2C (',')  => +1
0x48E86  mov -0x1,r10  ; st.b r10,-0x6752,gp   <- record byte+4 = 0xFA (-6)   => -1
```
**Exactly two type-`0x54` records exist in the flash config table:**
```
0x1180:  6c 55 10 54 2c 08 00 00   -> +1
0x14C0:  a6 71 10 54 fa 08 01 00   -> -1
```
The parser keeps a persistent cursor (`gp-0x350c`) seeded at `0x1000` and **advances it by each record's
own length byte (0x10)** ⇒ **strictly ascending, 16 bytes at a time.** Both records sit on the grid and
pass the length gate ⇒ **`0x14C0` > `0x1180`, last write wins ⇒ −1.**
⚠ Byte +6 is **not** a validity flag — it is copied to `gp-0x6735`, an unrelated cell. That was the best
counter-hypothesis and it is dead.

## VERIFIED THREE INDEPENDENT WAYS [EVIDENCE]
1. **Orchestrator** — the `mov -0x1` store, the table walk, and `FUN_00048a40`'s control flow.
2. **An independent agent**, unprompted, reaching the same two records from its own decompile + raw dump.
3. **On-car** — V98's `b3` rung = `(gp-0x6752 ≥ 0)`, **duty 0.0000 over 17,983 frames / 5 routes.** The
   kit recorded this on 2026-08-12 and then went on asserting +1 anyway.

🛑 **The table lives at flash `0x1000–0x15xx`. Every `.rwd` writes only from `0x13000` up. NO BUILD IN
THIS KIT'S HISTORY COULD HAVE TOUCHED IT. It has been −1 the whole time.**
⚠ **One residual**: a checksum failure on any record between `0x1180` and `0x14C0` latches `gp-0x348c`
and aborts the walk, leaving +1. Nothing suggests it happens, and the on-car measurement independently
confirms −1.

## WHAT IT CHANGES
- The polarity multiplies the **entire** `(P+I+D)` combine before `gp-0x6ad4`.
  ⇒ **D PUMPS · P and I DAMP · net PID DAMPS at 6–9 Hz** — GATE2's *original* headline, now on a verified
  footing. ⚠ **This survived THREE sign reversals in one session; cite
  `.claude/agent-memory/firmware-codepath-tracer/reference_accord_gp6752_resolved_negative_one_and_pid_polarity_reversal.md`
  for the current picture, not any intermediate claim.**
> ## 🛑 CORRECTION 2026-08-30 — THE "r24 PUMPS" INFERENCE BELOW IS WRONG, IN BOTH DIRECTION AND SIZE
>
> **The `gp-0x6752` = −1 finding itself is NOT disputed** — it is verified three ways including
> on-car, and nothing here touches it. What is corrected is the **downstream inference** in the
> next bullet.
>
> r24 was reconstructed from the firmware arithmetic on **flown data, 6 routes / 5 builds**
> (`analysis-2020accord/studies/mixer/r24_reconstructed_magnitude_and_phase.py`). As a transfer,
> `r24(f) = −(cal/1024)·(1 − e^{−j2πf·0.004})·T(f)`, so at 7.79 Hz the difference contributes a
> **fixed** `|H| = 0.19547, arg = +84.39°` and the whole question reduces to the phase of column
> torque vs rate — which is on the wire.
>
> | | claimed here | **measured** |
> |---|---|---|
> | magnitude at the car’s Lever B (5244) | **431–1294 ct** | **187 ct** — overstated **2.3–6.9×** |
> | behaviour at 6–9 Hz | **PUMPING** | **DAMPING** — phase **+143.6°** vs rate, net-work factor **−0.805** |
>
> Column torque **lags rate by ~122°** at 6–9 Hz (tight: only **18.9°** spread across 6 routes), so the
> derivative plus the −1 lands r24 **36° from the anti-rate axis** — opposing the motion.
> ✅ **Two controls with non-trivial expectations pass exactly**, and the `csd` convention is pinned by
> a constructed +90° lead rather than assumed — the specific trap this file itself warns about.
> ✅ **V88 agrees independently**: raising this same gain 512→5244 measured **6–9 Hz at 0.859× on-car**,
> the damping direction.
> ⚠ The verdict is **frame-dependent** (a global flip would make it pumping); it rests on the
> operator-confirmed table in [[accord-steering-sign-convention-confirmed]], under which driver torque
> and steering angle share a frame and assist acts in the driver’s direction.
> ⚠ **Open-loop.** It says what r24 computes, not what the closed loop does with it.
> ⇒ **Raising Lever B is not indicated to pump the ratchet**, and the magnitude that made it look
> alarming was ~4× too large.

- **Parity is ODD for r24 and r26** — each multiplies `gp-0x6752` exactly once, so the `P² = +1`
  cancellation in the Path-1/Path-2 chain **does not apply**. ⇒ ~~**r24 = −431 to −1294 ct at 6–9 Hz,
  PUMPING**~~ — 🛑 **SUPERSEDED, see the correction block above: measured 187 ct and DAMPING**, and the corrected band shape retrodicts the measurement better than +1 did.
- ⚠ **V49 was built, verified and held unflashed with the note "brick if −1."** It was never flashed.
  **That caution was correct and nobody knew why until now.**

## 🛑 THE REUSABLE LESSON
`docs/review/GATE2-2026-08-11-cbe74-independent.md` uses a sign convention **opposite** to the kit's canonical
`Re(Z)` tool (`rlog-tools/probe/decode_v90_probe.py::_band_transfer`). Each is internally consistent; reading
one against the other's assumed convention **produced the wrong answer twice.** It was settled by running
synthetic signals through the **actual code** (`T=+rate → +1.0`, `T=−rate → −1.0`, `T=d(rate)/dt → ≈0`).
⇒ **Verify a convention against a KNOWN test case through the real code. Never assume two labelled tables
share a convention because they use similar language.**

See [[accord-r24r26-is-the-driver-side-lane]], [[feedback-a-count-is-not-a-physical-fact]],
[[accord-check-build-lineage-before-proposing-lever]].
