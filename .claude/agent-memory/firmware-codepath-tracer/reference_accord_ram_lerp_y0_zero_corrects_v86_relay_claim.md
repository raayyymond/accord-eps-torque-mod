---
name: reference_accord_ram_lerp_y0_zero_corrects_v86_relay_claim
description: FUN_000389ec's RAM LERP Y[0]=0 definitively resolved (address-cited) — corrects build_v86_tva.py's "0xC63AE->0 = pure relay at full authority" claim; also closes 0xC6200's 15-reader census and prices 0xC646E/0xC613A/0xC6468's blast radius
metadata:
  type: reference
---

**Y[0] of the RAM LERP that `FUN_00038148` reads (X: gp-0x64b8..gp-0x64aa, Y: gp-0x641c..gp-0x640a) is DEFINITIVELY 0**, not a large constant. [EVIDENCE — full address chain]

Populator `FUN_000389ec`:
- `0x38D1C: st.h r0,-0x373c,gp` and `0x38D22: st.h r0,-0x3714,gp` — unconditional, every call, BEFORE the per-index loop (which starts at `mov 0x1,r12`, index 1, never revisits index 0). r0 is V850's hard-zero register.
- Commit (every 10th call, the `r14==9` branch): `0x39508 movea -0x3714,gp,ep` / `0x3950C sld.hu 0x0[ep],r11` (reads working Y[0]=0) → `0x39522 st.h r11,-0x641c,gp` (writes the LIVE cell). Same pattern for X[0]: `0x39548 st.h r9,-0x64b8,gp`.

Writer-exclusivity confirmed both ways: `search_instructions operand_pattern=641c` returns 15 hits, but 11 are `gp+0x641c` (POSITIVE — an unrelated cell in FUN_0003f884/FUN_0003fc16/FUN_0003fd8e/FUN_000558a6, a substring collision, discarded). The 4 real `gp-0x641c` hits are exactly: read @0x38266 (FUN_00038148) + the 3 FUN_000389ec sites above. Zero other writers image-wide. Same check on `64b8` confirms X[0].

**Consequence**: `build_v86_tva.py`'s FROZEN_CELLS text for `0xC63AE` ("lowering toward 0 drives the LERP index to 0 ⇒ output becomes constant ±Y[0] ⇒ A PURE RELAY AT FULL AUTHORITY") has the mechanism right and the magnitude wrong. Y[0]=0 ⇒ lowering 0xC63AE toward 0 SILENCES `gp-0x6b70` (Path-2's residual correction term goes to exactly 0), it does not slam to full authority. The paired `0xC6200` claim ("if it drops below Y[0], same relay failure") is moot for the same reason — 0xC6200 remains a legitimate independent output-authority clamp on gp-0x6b70, just not via a "Y[0] relay" mechanism. The FREEZE decisions on both cells are still reasonable, but for a different (smaller) reason: silent deletion of a lane, not runaway authority. Reported to team-lead 2026-08-08/09 (fw-lever-census task); comment text in build_v86_tva.py was NOT edited (report-only per standing instruction).

**0xC6200's "15 readers, 3 unidentified" census — now closed at function level**: FUN_000352b4 (6 hits, peak-hold per [[reference_accord_fun352b4_peakhold_correction_and_fun3a382_stageA_pole]]), FUN_00038148 (4, gp-0x6b70 clamp), FUN_0003a382 (3, PID feedback clamp `±tp+0x7200`), FUN_000389ec (1, a ceiling clamp inside the table-builder loop), **FUN_00039702 (1, NEW, not decompiled this session)**.

**FUN_0003b8f6's other cals priced/blast-radius'd** (full decompile 2026-08-09, tp=0xBF000):
- `0xC646E` (tp+0x746e) = **1428** (0x0594 LE). INERTIA gain, applied post-2-pole-EMA (alpha 0xC40D6=246/4096, both stages) as `*1428*2^-24` before the ±10 clamp → gp-0x6ae0. **1 reader, 1 function (FUN_0003b8f6 @0x3BB92), 0 writers ever** — the cleanest/most isolated candidate in the whole estimator; matches 0xC40D0/D2/D6/D8/0xC4080's single-function profile.
- `0xC613A` (tp+0x713a) = 1159 (Q15 scale on the sensor branch, feeds the dead/identity 3-tap FIR). **18 sites / 16 DISTINCT FUNCTIONS**, NOT isolated: FUN_000389ec, FUN_00039702, FUN_0003b66a, FUN_0003b8f6, FUN_0003bd40, FUN_0003bd7c(×2, =gp-0x6bf0's writer), FUN_0003c7ce, FUN_0003c7fc(×2), FUN_0003d274, FUN_0003d4a2, FUN_0003e00e(×2), FUN_0003e6d8, FUN_0003f776(=gp-0x6a56's writer), FUN_0003fd9c, FUN_00040a50. Widest blast radius found in this census — moving it touches the whole plant-model/residual/mixer source-file cluster, not just the estimator.
- `0xC6468` (tp+0x7468) = 2639. Confirmed 3rd/4th consumer beyond the known FUN_00038148(Q10)/FUN_0003b8f6(raw float) pair: FUN_000389ec (×2, one computes `0x1000000/cal`, a reciprocal) and FUN_00039702 (new).
- `0xC4080` (tp+0x5080) = 0, confirmed sole reader FUN_0003b8f6 @0x3BAF6 (a raw scan for "5080" surfaces false positives at gp-0x5080, a wholly different RAM cell — discard).
- None of 0xC40D0/D2/D6/D8/0xC613A/0xC6468/0xC646E/0xC4080 have EVER been written by any build script (grep-confirmed against all `build_v*_tva.py`); V85/V86 mention several in inventory/assertion prints only, not edits. 0xC40BC(600→6000) was V85's actual edit; 0xC40D4(573→286) is V86's.

Related: [[reference_accord_v86_prep_plantmodel_c64c8_boost_lerp2_closed]], [[reference_accord_fun3b8f6_fir_not_biquad_inertia_friction_and_free_taps]].
