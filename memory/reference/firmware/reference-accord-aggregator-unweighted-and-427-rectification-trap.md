---
name: reference-accord-aggregator-unweighted-and-427-rectification-trap
description: FUN_0003aa2c's aggregator is an unweighted 11-term sum (10 add + 1 jarl-add, ZERO multiplies) so phi = Path2/total needs no model; CAN 427 carrying |gp-0x6b70| RECTIFIED instead of signed understates 6-9Hz RMS by ~4.9x, a live regression introduced at V98 and inherited by V99 in two scoring scripts; and the free anchor RMS_6-9(gp-0x6b70)/RMS_6-9(column torque) is 1.13+/-0.09 (CORRECTED — first reported as 1.18/"1.0% apart" on the rectified channel, ~8x too tight).
metadata:
  type: reference
---

Promoted from `tracer-c63ae`'s private agent-memory 2026-08-13 (later still), record-repair pass —
these three facts had no home in the shared record. Full trace: `docs/traces/TRACE-2026-08-13-c63ae-lever.md`
Part 2. Task origin: making **φ** (Path-2's share of the delivered command at 6–9 Hz) measurable,
replacing V97's modelled `[0.085, 0.556]`.

## 1. ⭐ THE AGGREGATOR IS AN UNWEIGHTED 11-TERM SUM [EVIDENCE — decompile + opcode census]
`FUN_0003aa2c` @`0x3aa2c`, with `gp-0x67ac ≡ 0`:
```
gp-0x6b94 = clamp( gp-0x6ade + gp-0x6b4c + gp-0x6ad4 + gp-0x6b62 + gp-0x6b26 + gp-0x6bbe
                 + gp-0x6bd0 + gp-0x6b86 + r24_lane + r26_lane + FUN_00036682(), ±0x2800=10240 )
                                ^^^^^^^^^ PATH 2 (the PID output), coefficient +1
```
Per-term `[|·| ≤ W]` factors are **zero-reject booleans (0/1), NOT gains**. Assembly
`0x3acc8`–`0x3ace6`: `mov` + TEN `add` + `jarl`(→`FUN_00036682`) + `add`. 16-bit opcode census
**`{add:10, mov:2}` — ZERO multiplies.**

⇒ **φ is not a share of a weighted mix — it is `Path2/total` at ONE summing junction, all coefficients
+1.** Two numbers at the same node in the same units; no modelling needed to compute it.
⊕ Confirms `builds/v80_v107/build_v97_tva.py`'s "Path 1 is unweighted" claim.
⊕ `gp-0x374c` (the Stage-1 accumulator `0xC63AC` acts on) **never leaves `FUN_00038148`** — 2 hits
total, both inside that function — so `0xC63AC` cannot reach any of the other ten summands.

## 2. 🛑🛑 THE 4.9× RECTIFICATION TRAP — a LIVE, REGRESSED DEFECT
CAN 427 carries `|gp-0x6b70|` (`clamp(|X|*5>>6, 0, 0x3FF)`); the SIGN is a separate cave bit (V98's
`b7`). The sign toggles **5.06×/s** over a whole drive (11.68–13.09×/s engaged) — far too fast for
`|x| ≈ ±x`.

| reconstruction | 6–9 Hz RMS engaged | eng/manual |
|---|---|---|
| **SIGNED (sign bit applied)** | **548.28** — matches the record's 548.3 | 18.51 |
| RECTIFIED (magnitude only) | 112.73 | 3.93 |

**Omitting the sign costs 4.9× on the 6–9 Hz RMS.** This is the design law's "sign bit paired with a
magnitude channel" principle, MEASURED on a real lane — quote it whenever a rectified-magnitude
channel is proposed for a future cave.

🛑 **This is a REGRESSION at V98, not a class the kit always got wrong.** Full sweep of every script
that touches this 427 lane and does spectral work:

| script | 427 → spectrum | verdict |
|---|---|---|
| `probe/v87_probe_6b98.py` | made rectification a MEASUREMENT — screens each window, reports screened AND unscreened | ✅ |
| `probe/decode_v90_probe.py`, `studies/v91-v94-dose/v92_boost_lane_and_rez.py`, `studies/v95-override/v95_lane_decomposition.py`, `probe/v96_probe_vs_ratchet.py`, `studies/v97-r80/v97_r80_vs_v96.py` | all use the SIGNED lane for spectra | ✅ |
| **`score/v98_r81_score.py:541`** | feeds the RECTIFIED lane into D4b | ❌ |
| **`score/v99_r82_score.py:672,718`** | feeds the RECTIFIED lane into AUDIBLE + CROSSBUILD | ❌ |

Both defective scripts already compute `sign_6b70` and use it correctly elsewhere — this is a
one-line omission on one output row, not a missing capability. **Measured impact**: the 427-derived
6–9 Hz engaged/manual ratio reads **0.865 rectified (a false 13.5% "improvement") vs 0.976 signed (the
correct NULL)**. Reported, not silently fixed — check before trusting any `mt427`-row band claim from
`score/v98_r81_score.py` or `score/v99_r82_score.py`.

## 3. ⭐ THE FREE φ ANCHOR — CORRECTED 2026-08-13 (later still), was computed on the RECTIFIED channel
`RMS₆₋₉(gp-0x6b70) / RMS₆₋₉(column torque, 0x18F)`.
🛑 **First reported as `1.190 (route 81) / 1.178 (route 82)`, "stable to 1.0%" — WRONG.** That was
computed on the rectified 427 lane, the same defect §2 corrects. **Recomputed signed: r82 `1.1725
[1.0709, 1.2709]` rel s.e. 4.37% · r81 `1.0825 [0.9089, 1.2106]` rel s.e. 7.73%** — **1.173 vs 1.083
is 8% apart, not 1%.** Rectification inflated the anchor's apparent stability ~8×. **Use `1.13 ± 0.09`
and treat it as a LOOSE cross-check, not a tight one.** This makes the cross-route numerator in
`φ = 140.6/R` roughly predictable from a free `0x18F` channel on any future drive, but do not quote a
tighter figure than the corrected one above.

## Related
[[accord-c6200-clamps-the-pid-reference]] (the clamp φ's denominator sits behind) ·
[[accord-friction-polarity-more-friction-is-more-assist]] · [[accord-ratchet-is-a-linear-loop-oscillation]]
