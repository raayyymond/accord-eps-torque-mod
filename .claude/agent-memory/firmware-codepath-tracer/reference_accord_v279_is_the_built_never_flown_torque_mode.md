---
name: accord-v279-is-the-built-never-flown-torque-mode
description: Torque mode (fb = 0) is a ONE-HALFWORD cal edit, 0xC62E6 := 0 (the fb filter's OUTPUT clamp, not the input gain) — exact on every path; it was already built as V279 and NEVER FLOWN; it does not change the steady-state delivered surface at all, only the response to wheel motion
metadata:
  type: reference
---

## 1. The exact mute is the CLAMP, not the input gain

`0xC62E6` is the feedback lag filter's **output clamp**, read `ld.hu` at `0x28F96`, `0x28F9C`,
`0x28FB8`. It is what the V282/V292 build tag calls **`FEEDBACK46080`** (stock 7680, V276+ 46080).

Hand-tracing `0x28FA6..0x28FBC` with `C = 0`, all three arms yield 0:
`r26 > 0` → `mov r14,r26` = 0 · `r26 < 0` → `ld.hu` + `subr` = −0 = 0 · `r26 == 0` → unchanged.
`ld.hu` means 0 reads as 0 with no sign trap. ⇒ **`fb ≡ 0` for every state value, on every path.**

🛑 **Do NOT mute via `0xC63EA := 0` (the input gain `b`) on a pre-V292 base.** `floor(−a/1024) = −1`
for every `a < 1024`, so `s = −1` is an **absorbing state** and the filter would rest at `out = −2`
forever, not 0. V292's residue-carrying cave removes that absorbing state, so `b = 0` is exact *there* —
but the clamp route is exact everywhere and costs the same one halfword.

**Reader count trap:** `0xC62E6` has **3** accesses on stock/V282/V279 but **5** on V292 — the cave
replicates two `ld.hu` at `0xC4C28`/`0xC4C2C` and orphans `0x28F96`/`0x28F9C`. A build script asserting
"exactly three readers" fails on a V292 base.

## 2. It has already been built, and never flown

`docs/BUILD-LINEAGE.md` §V279 — *"PURE FEEDFORWARD: the rate PID opened into a linear torque map
(2026-09-02, NOT FLOWN — THE FLIGHT CANDIDATE)"*. Read from **its own image**
(`_v279_V279-V268BASE-PURE.FEEDFORWARD.FB0.KD0.LINEAR.TORQUE.TAP_plain_image.bin`):

| cell | V279 | V282 / V292 |
|---|---|---|
| `0xC62E6` fb clamp | **0** | 46080 |
| Kd bank `0xCB7D4` → `0xE511C` | **[0,0,0,0]** | [128,128,128,128] |
| assist map `0xE502C` Y | `[0,24,40,48,64,128,192,256,320,480]` — **Y = 2X** | `[0,52,…,1032]` — **Y/X = 4.30, ×6 stock** |
| Kp `0xE5378` Y | 256 flat | 248 flat |
| `0xC61B4` / `0xC6CD0` | 3072 / 5346 | 3072 / 5346 |

710/710 assertions, independent rebuild reproduced, adversarial pass returned **no do-not-flash**.
Image and `.rwd` are on disk and are **not** marked DO-NOT-FLASH. **No flown build has ever zeroed the
LKAS rate feedback** — the flown `0xC62E6` ladder is 7680 → 15360 (V278) → 46080 (V276, V280…V292).

## 3. What it does and does not change

🛑 **It does NOT change the steady-state delivered surface.** With the wheel still, `fb = 0` already, so
`T(idx)` is byte-for-byte what V282/V292 deliver today: 19 / 64 / 213 / 427 / 1237 / 2051 counts at
idx 1 / 3 / 10 / 20 / 58 / 96, railing at **2462** from idx ≈ 115 where the **P clamp `0xC61BC` = 15360**
binds. Peak authority is untouched.

🛑 **What changes is the response to wheel MOTION, and it is an INCREASE.** Today the loop settles where
`wheel rate = 0.1294·sp deg/s` and the torque backs off; with `fb ≡ 0` the error never shrinks, so the
lane holds full commanded torque no matter how fast the wheel is already moving. **The lane becomes a
torque source with no rate limit of its own.** That is the risk line for any drive.

**Killing D as well:** `0xC61B6 := 0` (the D clamp) is exactly equivalent to zeroing the Kd bank, costs
1 halfword instead of 8 bytes across 28 records, and stays inside the **same `0xC6FFC` CRC page** as
`0xC62E6` (the Kd bank would add the `0xE5000` page). Measured on the exact integer mirror: with the
command slewing at the 123-count cap, **D already rails at ±10240 on 0.7 % of ticks today** from the
100 Hz command staircase alone — the mute does not create that, it only removes D's ring-derivative
part (280 of 353 mean|D| at a 16-count ring).

**Free liveness control on a V292 base:** the mute sits *downstream* of the filter state, so
`gp-0x3d30` keeps running and the `0x14A` **bit-3** rung (`sign(s)`, repointed at `0xC4BAA`) keeps
publishing. Bit 3 stays alive while the lane stops responding to wheel motion — a zero-cost proof the
edit is the edit.

**The open interlock question:** torque mode does not raise peak torque but it raises **dwell at peak**.
`FUN_0004595a` is an instantaneous comparator (`|gp-0x6b94|` vs `|gp-0x6ace|`), not an integrator, so it
does not see it — but that is one monitor, not a census. Census `gp-0x6b94`/`gp-0x6ace`/`gp-0x6acc`
readers for an integrate-and-trip structure before flying this.

See [[accord-lkas-pid-pid-register-map-and-taper]] and
[[accord-0x2a0c6-is-a-damper-mode-and-data-boot-values]].
