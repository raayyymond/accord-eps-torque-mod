---
name: accord-v278r3-torque-tap-reads-310-and-damping-is-sign-t-ne-sign-rate
description: The delivered-torque tap on CAN 427 (V278 rev 3 / V279 rev 2, wire = sign(T)<<9 | |T|>>3, T = gp-0x6b38) can NEVER read 313 -- the output lag's readout (s_old+s_new)>>5 has DC 2*507/32/32 = 0.990, so a railed sum (15360) delivers 15210*5346>>15 = 2481, reading 310. Saturation := |field| >= 309. DAMPING = P(sign(T) != sign(0x18F rate)) -- NOT "==", which reads pumping; sign chain from the bytes (T = -lane; lane has E's sign, all Kp/Kd knots > 0; fb has gp-0x6a56's sign; wire = -gp-0x6a56). The tap's damping read is LOWER than the E-comparator's because T lags E ~38 deg at 3.9 Hz: predicted 0.68 osc / 0.60 normal at K=2 vs 0.37 / 0.40 at K=6 (V276). Score the drive against THOSE numbers, not 0.86 / 0.57.
metadata:
  type: reference
---

# The torque tap reads 310 at the rail, and damping is `sign(T) != sign(rate)` -- 2026-09-02 [EVIDENCE]

**Readout arithmetic** (cells 0xC63EC = 992, 0xC63EE = 507, 0xC61BE = 15360, 0xC6CD0 = 5346, confirmed on the rev 3 image
and asserted by `build_v278r3_tva.py` [8b]): state DC gain 507/(1024-992) = 15.84; readout `(s_old+s_new)>>5` = 0.990;
railed sum 15360 -> 15210 -> x5346>>15 = **2481** -> `>>3` = **310**. The "2505 reads 313" line in V279's docstring and
page, and in the V278 lineage entry, was the sum-clamp ceiling without the readout. **A reading of 313 would refute the
arithmetic** (pre-registered). Saturation duty := P(|field| >= 309), one LSB under the rail.

**Damping sign chain** (`adv278r3b` from the bytes, positivity closed by the orchestrator):
1. `T = -lane`: `ld.b -0x6752,r13` (= -1) x `ld.h tp+0x7cd0` (5346 > 0) at 0x2A1EE-0x2A1F6; no other sign flip 0x2A1FC..0x2A23C
   (the `subr r0` there build the -3072 clamp bound).  2. lane has the sign of E: every Kp knot 205..717 and Kd knot 64..128
   is positive on all 28 records; both lag filters have positive coefficients.  3. fb = the two-sample sum, DC +30.89 on
   gp-0x6a56.  4. the 0x18F wire = -gp-0x6a56.
   => damping (sign(E) != sign(fb)) <=> **sign(T) != sign(wire rate)**. The first rev-3 docstring draft had `==`.

**Phase caveat:** the output lag (5.05 Hz) puts T ~38 deg behind E at 3.9 Hz -- no sign flip, but the instantaneous
sign-agreement statistic is diluted. Simulated on the V276 log through the exact chain (`prereg_v278r3_saturation.py`):

| K | damp_E (rev-2 comparator) | **damp_T (what the tap reads) osc / normal** | sat |T|>=2472 osc / normal |
|---|---|---|---|
| 1 | 0.937 | 0.758 / 0.682 | 0.000 / 0.002 |
| 2 (rev 3) | 0.863 | **0.678 / 0.600** | 0.000 / 0.004 |
| 6 (V276) | 0.576 | **0.368 / 0.401** | 0.000 / 0.012 |

**FLOWN 2026-09-02 — corrections from the wire:** (1) the 10-bit field is `((b0&3)<<8)|b1` (kit convention; the DBC window
`(b0&0x7F)<<3|b1>>5` maxes at 21 and never sets the sign — b0 is only 0x80/0x82); (2) damping compares T to the RAW 0x18F rate
(the decoder had negated it once more); (3) **sign(T) = +sign(cmd)** on the wire (v = −4·cmd, then T = −lane) — V279's docstring
has it backwards; (4) the damping scalar read **0.40** on rev 3's normal frames and the chain sim on the same frames gives 0.399:
tap and model agree, the prereg's 0.60 was V276's log. It is REGIME-DEPENDENT (0.33 near centre hands-off, 0.83 above 50 deg/s,
0.68 hands-on) — the lane moving the wheel reads as "pumping" — so it does not discriminate a healthy loop from a ringing one on
its own. (5) A P-only rail delivers 2461 and reads **307**; 2481/310 is the sum-clamp rail (needs D). Decision rule and
thresholds: `rlog-tools/studies/osc-2to4/PREREG-V278R3-CLAMP-READ.md`. Decoder:
`rlog-tools/probe/decode_v278r3_torque_tap.py` (prints both duties; meaningless on any route before rev 3 / V279 rev 2,
which carry V112's gp-0x6abc tap). Related: [[accord-gp6b38-is-the-delivered-lane-torque-and-forwards-to-gp6b3c]],
[[accord-the-rate-loop-is-a-bang-bang-servo-p-rails-at-e-440]] (retracted), [[accord-v276-mechanism-is-a-matter-of-degree]].
