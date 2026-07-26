---
name: reference-accord-lkas-delivery-and-governor
description: "Accord delivery splits after the aggregator: gp-0x6acc drives the Q15 shaper integrator, while gp-0x6afe+r20 drives final gp-0x6b98. Governor is MIN(4762, A160 motor-rate table, optional budget); table=4607 at z=1318, while conservative gp-0x6acc envelope is 7322."
metadata:
  node_type: memory
  type: reference
---

The 2020 Accord (`39990-TVA-A160`, V850, code.bin) LKAS-torque delivery topology, established by a 3-tracer firmware-codepath-tracer swarm + operator-directed self-verification on 2026-05-26 (late). Every link below is xref- or disasm-verified in the open Ghidra instance. Builds on / corrects [[reference-accord-demand-aggregator-pipeline]], [[reference-accord-arbitration-limit-family]], [[reference-accord-lkas-window-ceiling]], [[project-accord-torque-mod-v0]]. Bases: gp=0xFEDF8000, tp=0xBF000 (see [[reference-accord-databin-tp-base]]).

> **2026-07-18 V39 UPDATE:** `FUN_0007b022` is now traced numerically. `0xC6202=4762` is verified; states 0/2 use `MIN(nominal, adaptive)` rather than a flat 4762; other states also take the unresolved budget minimum. A160's adaptive table is X `[1050,1700,2500,3700,4100]`, Y `[5325,3584,2406,1587,512]`, slopes `[-21940,-12059,-5593,-22021] >> 13`. Exact result is 4607 at z=1318, 4342 at z=1417, and 1586 at z=3700. The upstream multiplicand is a Q15 limiter-bank output, NOT `gp-0x6a64`. See `eps_lkas_chain_model.py` and the V39 handoff.
>
> **CORRECTION:** the old linear shorthand `gp-0x6acc -> shaper -> gp-0x6b98` conflated two inputs. `gp-0x6acc` is sanitized at +/-8192 and drives the signed-Q15 `gp-0x3570` integrator. Final output is `range_gate(gp-0x6afe,+/-10240) + r20`, then the second governor and +/-8192 clamp. Since assist joins before the first governor, conservative `abs(gp-0x6acc) <= 4762 + 2560 = 7322`; 4608/4342 are not whole-aggregate maxima.

## The arb output is NOT a monitor dead-end (corrects an intra-session wrong turn)

An earlier turn this session concluded the arbitration output `gp-0x6b3c` only fed a redundancy monitor and that V14 was "very likely a no-op." **That was WRONG** — the decompiler rendered the `distribute_clamp` argument struct as constants, hiding the torque. The assembly is unambiguous: `m_steer_torque_limit_and_pack` (FUN_0x2b422) packs the clamped arb torque into the distribute struct and calls the distributor.

**Verified full delivery chain (LKAS arbitrated torque → motor):**
```
arb FUN_00028ea6: out = (demand × polarity[gp-0x6752] × GAIN[tp+0x746c=0xC646C=891]) >>15,
                  clamp ±[tp+0x71b4=0xC61B4=512]              → gp-0x6b3c (0xFEDF14C4)
 → limit_and_pack FUN_0x2b422: clamp ±[tp+0x71b2=0xC61B2=512];
       0x2b522 mov 0x1,r10 / 0x2b526 sst.b r10,0x0[ep]        struct[0]=1  (SOURCE INDEX 1 = LKAS)
       0x2b52c sst.h r12,0x4[ep]                              struct[+4]=clamped arb torque
       0x2b53e jarl 0x25c32                                   → distribute_clamp(&struct)
       (it ALSO does 0x2b45c st.h r12,-0x6b3a → channel_router FUN_0x2b57a → FUN_00027802 = a
        redundancy MONITOR; that is a SECOND consumer / genuine dead-end, not the only one)
 → distribute_clamp FUN_00025c32 (idx=struct[0]=1): writes gp-0x62f8[1] = clamp(arb,±0x2800)  [inert vs 512]
 → mixer FUN_00026c80, channel 1, mode tp+0x5124[1]=0 (default case 0x270b8):
       0x270d6 st.h r0,0[r28]  → gp-0x62c8[1]=0   (does NOT enter the gp-0x3d8c gate lane)
       0x270d2 st.h r10,0[r24] → gp-0x62b0[1]=gp-0x62f8[1]   (enters the gp-0x3d88 lane)
 → gp-0x3d88 (st.w r1,-0x3d88 @0x2730c)
 → gp-0x6b4c (st.h @0x276f0; clamp ±0x2800)                   (0xFEDF14B4)
 → FUN_0003aa2c (ld.h -0x6b4c @0x3aa3e) → gp-0x6b94 (st.h @0x3acfa; aggregator, clamp ±0x2800)
 → FUN_0004503c (ld.h -0x6b94 @0x453e0; GOVERNOR clamp ±(gp-0x4f64×Q15 limiter-bank output)>>15 + slew) → gp-0x6ace (@0x454d2)
 → FUN_000456a4 (ld.h -0x6ace @0x458bc) → gp-0x6acc (st.h @0x45932)
 → shaper FUN_00042af8 (ld.h -0x6acc @0x431c4; governor ±gp-0x4f64 again + static ±0x2000) → gp-0x6b98 (0xFEDF1468)
 → FOC: FUN_000370b6 / FUN_0003b8f6 / FUN_00056420 / FUN_0007c4f2 + CAN packer FUN_00059912  (gp-0x6b98 has 45 readers)
```

**Two mixer lanes RECONVERGE at the shaper.** The shaper FUN_00042af8 reads BOTH `gp-0x6acc` (the mode-0 / LKAS path, `0x431c4`) AND `gp-0x6afe` (the mode-5 path via gate FUN_00042ac6, `0x43ae0`). So the "separate lanes" and "series chain" framings are both right — the lanes merge at gp-0x6b98. This also resolves [[reference-accord-demand-aggregator-pipeline]] GAP 2 in the affirmative: gp-0x6b98 (the shaper output) IS read by the on-chip FOC functions.

## distribute_clamp source map (10 callers; source idx = struct[0]) → mixer lane

`distribute_clamp` (FUN_00025c32) is a shared hub; each caller tags its torque with a source index. Per-channel mode array `tp+0x5124` (`0xC4124`) = `[0,0,5,0,5,5,0,0,0,5,0]` decides each index's lane.

| idx | caller | mode tp+0x5124[idx] | lane |
|---|---|---|---|
| 0 | FUN_0002e52e | 0 | gp-0x62b0→gp-0x3d88→gp-0x6b4c |
| **1** | **m_steer_torque_limit_and_pack (LKAS)** | **0** | **gp-0x62b0→gp-0x3d88→gp-0x6b4c** |
| 2 | FUN_0003405a | 5 | gp-0x62c8→gp-0x3d8c→gate→gp-0x6afe |
| 3 | FUN_0002c246 | 0 | gp-0x6b4c |
| 4 | FUN_00023ad2 | 5 | gp-0x6afe |
| 5 | FUN_00023fe2 | 5 | gp-0x6afe |
| 6 | FUN_0003aff4 | 0 | gp-0x6b4c (torque slot 0; payload in struct[+8]→gp-0x633c) |
| 7 | FUN_0003a8a8 | 0 | (null — all torque fields 0) |
| 8 | FUN_0002caa2 | 0 | gp-0x6b4c |
| 9 | FUN_000339cc | 5 | gp-0x6afe |

Both lanes reconverge at the shaper, so all non-null sources reach gp-0x6b98. **Caveat:** the semantic labels for sources 0,2–9 (RTC, column torque, integrator, etc.) are tracer inference; only source 1 = LKAS and the index→lane routing are independently verified.

## The high-end binder: runtime governor gp-0x4f64 = cal const 0xC6202 = 4762

`gp-0x4f64` (`0xFEDF309C`) clamps the COMBINED command in FUN_0004503c (gp-0x6b94→gp-0x6ace) and again in the shaper FUN_00042af8 (before gp-0x6b98). It is written ONLY by `FUN_0007b022` (stores @0x7c2e2/0x7c3b4/0x7c47c), in lockstep with shadow `gp-0x448a` (mismatch → FUN_0006b9ee fault). 3 branches selected by `uVar26 = *(byte)gp-0x4e5a` (0xFEDF31A6, written by motor state machine FUN_00071272):
- **uVar26==0 and ==2:** governor = `MIN(4762, adaptive motor-rate cap)` through `gp+0x184`; these branches are not flat 4762.
- **Other states (including inferred operative state 1):** governor = `MIN(4762, adaptive motor-rate cap, budget B)`. The adaptive axis is normalized motor resolver electrical-angle rate, not road speed. The exact A160 table is recorded in the update above. `B` is a motor-feasibility calculation; calling it specifically I2t/thermal remains inference.

**So the governor ≈ 4762 is the dominant binder, NOT the ±0x2000=8192 static** (4762 < 8192, governor fires first). This corrects the long-standing "delivered ~8192" / "±0x2000 is the wall" framing — the operative cap is the governor.

**Do not treat `0xC6202` as the hard-turn lever.** Raising it alone does not lift the descending adaptive table or budget minimum, and broadens diagnostic/limp and motor-protection behavior. Strong driver torque can move the wheel quickly without the V38 ratchet or vibration, contradicting an intrinsic moving-motor torque limit. V39 deliberately leaves the complete governor byte-identical while testing the direct `r24` torque-rate lane.

> **⚠ CORRECTION 2026-07-17/18:** the taper axis is motor resolver electrical-angle RATE, not vehicle speed. The shaper applies the governor again before a separate ±0x2000 clamp; the upstream `FUN_0004503c` uses a Q15 limiter-bank result, not `gp-0x6a64`. A diagnostic path can also write `gp-0x6b98 = gov×1` directly. See [[reference-accord-gp4f64-three-consumers]].

## Variant mode gp-0x674e — what it is, and what it does NOT do

`gp-0x674e` is set once at init: `FUN_00057f8e` matches a 5-byte ECU hardware ID at `gp+0x6408..0x640C` against a **16-entry table at `0xCD000`** (36 bytes/entry) → index 0-15; `FUN_00042692` latches `gp-0x674e` = entry[+0x1a]. Decoded table: keys `TVAA0/1/2/4/6/7`, `TVAC1/4`, `TVCA0/3/4/6`, `TWAA0/1/2`; mode values {0,1,3,4,6,7,8,9}. **39990-TVA-A160 → key `TVAA1` → entry 2 → mode 1** (inference from part-number→key encoding; confirm via runtime gp+0x6408 bytes).

The variant mode (×4) indexes the LERP curve-pointer arrays used by the **arbitration** (FUN_00028ea6, monitor path) and **driver-assist** (FUN_0002a93a). It does **NOT** directly set the delivered LKAS gain — that lives in the mixer source routing (governed by the *separate* per-channel array `tp+0x5124`, not gp-0x674e). Don't conflate the two "mode" systems.

## ✅ RESOLVED 2026-05-26 — V14 FLASHED + ROAD-TESTED: IT WORKS (the magnitude question is closed)

Operator confirmed V14 (gain `tp+0x746c` 891→1782 + clamps `tp+0x71b2`/`tp+0x71b4` 512→1024) delivers the intended ~2× LKAS torque at the wheel. This **empirically closes the open MAGNITUDE question below in the affirmative (Case A):**
- The LKAS path is **REQUEST-LIMITED** by the arb output gain + ±512 clamps, **well below the 4762 governor** — the governor does NOT bind during op-engaged hands-off driving (the non-LKAS addends into gp-0x6b94 are small there, so the sum never approaches 4762). Doubling the LKAS source therefore reaches the motor uncut.
- Quantified: stock arb output ≈ 15360×891≫15 ≈ **418** (gain-limited, below the ±512 clamp); V14 ≈ 15360×1782≫15 ≈ **835** — the clamp×2 is necessary so 835 isn't re-cut to 512. 835 ≪ 4762 governor ≪ 8192 shaper, so nothing downstream re-cuts it. Matches the independent "REQUEST-LIMITED" finding in [[reference-accord-mixer-lkas-source-chain]].
- **V15 / governor `0xC6202` edit is NOT needed for 2×.** The governor only becomes the binder above ~4762 (a >~9× push); held as a contingency only.
- Disasm re-verified this session in the open Ghidra project: arb gain/clamp/store at FUN_00028ea6 @0x2a1ee–0x2a2ea; limit_and_pack source-idx-1 + struct[+4] + jarl 0x25c32 @0x2b522–0x2b53e; governor s_clamp(gp-0x6b94, ±(gp-0x4f64×speed≫15)) in FUN_0004503c.

## Consequences for the torque mod (supersedes the V14 "no-op" worry) — NOW CONFIRMED BY ROAD TEST

- **V14 edits are on a live path.** `tp+0x746c` (gain 891→1782) and `tp+0x71b2`/`tp+0x71b4` (clamps 512→1024) scale the LKAS source's contribution, which DOES reach the motor via the chain above. Not inert. ✅ confirmed working.
- **LKAS is one summed source into gp-0x6b94**, capped by the governor (~4762) — but during op-engaged driving the LKAS term is small/request-limited and the sum stays far below 4762, so V14's doubling is delivered (Case A, confirmed). The earlier "the open MAGNITUDE question" is now CLOSED.
- **Two distinct levers:** (a) V14's arb-source scaling (LKAS share) — sufficient for 2×, proven; (b) the governor `0xC6202` (combined ceiling) — only needed above ~9×, lockstep-shadowed.
- **Why V11/V12/V13 saw no high-end change:** they edited the mode-5/gate/shaper clamps and the setpoint shl3 — NEITHER the arb-source lever NOR the governor. V14 was the first build to touch a live lever, and it delivered.

Method per [[feedback-rigorous-validation]] (verified vs inferred kept distinct; agent claims independently re-verified in Ghidra before recording).
