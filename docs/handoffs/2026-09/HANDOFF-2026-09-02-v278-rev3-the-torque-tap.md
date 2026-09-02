# HANDOFF 2026-09-02 — V278 rev 3: the torque tap, and two corrections of record

**Status: V278 rev 3 BUILT (`aadeced6…3765e6` / rwd `7effd74c…0de37`), written to `../accord-firmwares`, NOT flashed.
The operator's flight candidate by his own choice ("maybe I will try V278 actually"). Rev 2 renamed SUPERSEDED-DO-NOT-FLASH.
V279 rev 2 stays built as the alternative. Chain: ← `HANDOFF-2026-09-02-v279-pure-feedforward.md`.**

## What was asked

The operator, leaning to V278 (K=2, no StarPilot change), asked: *"Regarding the narrow linear region, how will I know if the
clamps should be widened, will the live telemetry and a drive on V278 be sufficient?"* Answer given: rev 2's comparator tap
reads damping only; the delivered torque reads damping AND saturation. He said: **"Build V278 rev 3."**

## What rev 3 is

V278 rev 2's two cal edits (28 map records Y×2, `0xC62E6` 7680→15360), with the 34-byte CAN-427 packer window replaced by
**V279 rev 2's delivered-torque tap, byte-identical**: `wire = (sign(T)<<9) | (|T|>>3)`, T = `gp-0x6b38`. The build script
(`build_v278r3_tva.py`, 598/598) asserts the window against V279 rev 2's IMAGE and the cal region against rev 2's IMAGE, and
re-reads the end state from the final image and the decoded .rwd. Everything else byte-identical to V268.

## Adversarial pass (three agents, disjoint surfaces)

| agent | surface | result |
|---|---|---|
| `adv278r3a` | build script | rebuild reproduces the hash; 438 bytes vs V268 all attributed (378 map, 2 FB, 31 window, 28 trailer); own CRC walker 50/50 + 49/49; rwd decodes to the image; census 540 → 17 substantive; **25/25 mutations caught**. FLASH-CLEAN. |
| `adv278r3b` | sign chain, from the bytes | **The docstring's damping formula was BACKWARDS** (`sign(T) == sign(rate)` reads pumping). Chain: T = −lane (gp-0x6752 = −1, gain 5346, no other negation 0x2A1FC..0x2A23C); fb has gp-0x6a56's sign (DC +30.89); wire = −gp-0x6a56. One gap (lane keeps E's sign) closed by the orchestrator: every Kp knot 205..717, every Kd knot 64..128 positive on all 28 records. Output lag 5.05 Hz → T lags E 37.7° at 3.9 Hz. Wrote `rlog-tools/probe/decode_v278r3_torque_tap.py`. Image clean. |
| `adv278r3c` | pre-registration | Three premise contradictions (below); `PREREG-V278R3-CLAMP-READ.md` + `prereg_v278r3_saturation.py`. |

Orchestrator verification of the crux: decompile of `FUN_00028ea6` (code.bin) lines 975 / 1034 / 1036 — `iVar31 = iVar31 * 0x20 - uVar35`,
`iVar26 = iVar31 * Kp`, `uVar33 = iVar26 >> 8`; `sar 0x8` at `0x2A0C2`. And 0xC63EC/EE = 992/507 → readout 0.990 → 2481 → reads 310.

## 🛑 Corrections of record

1. **"P rails at |E| = 440 (±1.8 deg/s); bang-bang servo; stock delivers 417 at cmd 113" — RETRACTED.** The chain has ONE ×32,
   inside E. P rails at |E| = 15360·256/Kp = 15855 (64 deg/s) at Kp 248, 5650 (22.9 deg/s) at Kp 696. Stock's wheel-still
   surface peaks at P = 14964 < 15360. The linear band covers 92–97 % of ticks on the V276 log at K=2. Memory stamped
   RETRACTED; STATE.md's V279 "WHY" paragraph corrected; V278 page §04 carries it. **What survives:** LKAS commands a RATE; the
   damping-fraction analysis (a sign statistic).
2. **"2505 reads 313" → a railed sum delivers 2481 and reads 310.** The output lag's readout `(s_old+s_new)>>5` is 0.990.
   Corrected in V279's docstring and page, the lineage, STATE, and rev 3's docstring. A reading of 313 refutes the arithmetic.
3. **Damping on the torque tap is `sign(T) != sign(0x18F rate)`**, and it reads LOWER than the E-comparator because of the
   38° lag: predicted **0.68 osc / 0.60 normal at K=2**, **0.37 / 0.40 at K=6**. Score the drive against these, not 0.86 / 0.57.

## The pre-registered read (before the drive)

Saturation = P(|field| ≥ 309): predicted **0.000 osc / 0.004 normal** at K=2 — **the clamp question's pre-registered answer is
"do not widen."** Four-way rule with thresholds (damping high ≥ 0.60 osc / 0.55 normal, low ≤ 0.50; saturation high ≥ 0.05,
low < 0.02) in `PREREG-V278R3-CLAMP-READ.md`, with the widening table (W=20480 needs `0xC6CD0`→4008 to hold 2505; `0xC61BE`,
`0xC61B4`, `0xC6CD0` all have `ld.h` reads — keep < 32768).

## Open items (not requested)

- The golden model: check whether `eps_chain_control.py` carries the P-term arithmetic at all, and that it has the single ×32.
- `dose_e_sign_by_k.py` still hard-codes LIMIT 15360 (slot 7: 16384; no frame on the V276 log is affected).
- Next hops from `gp-0x6b3c` toward the motor.
- `adv278r3b`'s rough T-proxy (no ramp, no table cascade) gave 0.55 vs `adv278r3c`'s full-chain 0.68 for the same statistic —
  the full-chain number is the pre-registered one; the discrepancy is the proxy's omissions, not a disagreement about the sign.

## Files

`analysis-2020accord/builds/v108_plus/build_v278r3_tva.py` · `rlog-tools/probe/decode_v278r3_torque_tap.py` ·
`rlog-tools/studies/osc-2to4/PREREG-V278R3-CLAMP-READ.md` · `rlog-tools/studies/osc-2to4/prereg_v278r3_saturation.py` ·
memories `accord-v278r3-torque-tap-reads-310-and-damping-is-sign-t-ne-sign-rate` (new), `accord-the-rate-loop-is-a-bang-bang-servo-p-rails-at-e-440` (retracted) ·
page https://claude.ai/code/artifact/b2a2995e-e219-4e18-a2c3-e99a979d0575 (updated to rev 3).
