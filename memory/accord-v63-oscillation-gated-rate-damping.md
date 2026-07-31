# ★★ V63 BUILT — oscillation-gated rate damping. Two cal bytes, zero manual-feel cost.

Built 2026-07-31, **UNFLASHED, and it SUPERSEDES V62 as the recommended next flash.**

```
0xC6440  2048 -> 4096   r24's state>=5 arm  (Q10 2.0 -> 4.0)
0xC643E  1536 -> 3072   r26's state>=5 arm  (Q10 1.5 -> 3.0)
image SHA 2f843bce8ff6fcab72cd3fafddcbdea926b40701e1425cabad03791f1a09019c
RWD   SHA 5e5f83d7cd9281000dcfa602a6e70b252037ad782728502d82e82d42c72b9abc
```
**6 bytes off V59** (2 cal bytes + CAL CRC), 88 off V38. ⭐ **MAIN CRC UNCHANGED** = machine proof no
code byte moved. V62's `sar` shifts and V61's tap kill are both **asserted absent**, so V63 is an
independent experiment, not V62 layered underneath. 50/50 CRC blocks; RWD round-trips with every gate
re-run on the readback; re-verified independently from the built image.

## Why it exists — the operator's objection, designed in rather than argued away
V62 doubles the torsion-bar rate lane **unconditionally**, which changes manual steering feel to fix a
problem that is worst with LKAS engaged and hands off. The operator pushed back on exactly that. The
answer is [[accord-state671a-is-an-oscillation-detector]]: both lanes already branch on `gp-0x671a >= 5`,
which is a **hard-reversal counter** reading 0 during smooth steering. Raising only those arms adds
damping only while an oscillation is detected; both smooth-steering LERP defaults stay stock.
⇒ **A smaller edit than V62, with the manual-feel cost removed by construction.**

## Why there is no new arithmetic risk
**3072 is already the gain_A LERP's own stock maximum** (`0xC6A68`/`0xC6A7C` Y[0]=Y[1]=3072), so the
multiply chain runs at that magnitude today in the smooth arm. Worst-case `stage1 * gain` stays at
**1.007e9 = 47% of INT32_MAX, unchanged from stock**. r24 at 4096: `5120 * 4096 = 21.0M`, trivially
inside int32; the ±8192 output clamp is the only ceiling.
⚠ V850 `mul r1,r6,r0` discards the HIGH word into `r0`, so a 32-bit overflow would be **silently
truncated** into a garbage, possibly sign-flipped lane value. Neither edit moves any operand's worst case.

**GATE 1 vacuous** (calibration only — no cave, no code, no new RAM cell; caves are this kit's only
bricking class). **GATE 2** is the damping argument, in the one lane fast enough to act at 20 Hz
(task 1, 1 kHz, ~3.8° lag vs task 5's 37.6–75.2°) — and now gated so it cannot act during smooth steering.

## 🛑 Two residuals
1. **Whether `gp-0x6c2c` crosses ±12800 during the real vibration is UNVERIFIED and load-bearing.**
   If it does not, the detector never fires and V63 is **inert**. ⇒ **a null on V63 is AMBIGUOUS**
   between "detector never trips" and "rise too small". **Resolution needs no probe and no cave: fly V63
   first (zero manual-feel cost); if null, fly V62, which doubles unconditionally and cannot miss.**
   V62 working after V63 nulls tells you the detector was not tripping.
2. **r24's coverage is not guaranteed** — `gate_671d` outranks the `state>=5` arm and is live (2 writers).
   r26's chain is clean (`gate_683c` dead). **Expect r26 to carry this build; r24 is a bonus.**

## Two assertions caught my own bugs mid-build — both fixed in the checker, not the expectation
- `0xC64DD`/`0xC64FA` are **`ld.bu` BYTE loads**; reading `0xC64DD` as u16 gives 6962, not 50.
- `2048→4096` is `0x0800→0x1000` and `1536→3072` is `0x0600→0x0C00`, so in LE **only the high byte of
  each halfword moves — 2 bytes, not 4**. The assertion now checks halfword *containment* rather than a
  hardcoded byte set, which stays correct whatever values a future revision picks.

Related: [[accord-state671a-is-an-oscillation-detector]], [[accord-v62-doubles-the-rate-lane]],
[[accord-rate-lane-is-the-damper-not-the-amplifier]].
