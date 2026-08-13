---
name: reference_accord_aggregator_is_unweighted_and_427_rectification_costs_4.9x
description: FUN_0003aa2c's summing junction is 10 add + 1 jarl-add with ZERO multiplies -- an unweighted 11-term sum in which Path 2 (gp-0x6ad4) is exactly one term with coefficient +1, so phi is literally Path2/total at one node; gp-0x374c never leaves FUN_00038148 so 0xC63AC cannot touch any other summand (build_v97's "unweighted and unaffected by A" SURVIVES); and using CAN 427 RECTIFIED instead of sign-reconstructed understates the 6-9 Hz RMS by 4.86x because the sign toggles 5.06 times per second -- a defect live in rlog-tools/v98_r81_score.py:541 D4b.
metadata:
  type: reference
---

# The aggregator junction, and the 4.9× rectification trap — 2026-08-13, `tracer-c63ae`

Full trace: `docs/TRACE-2026-08-13-c63ae-lever.md` Part 2. Task: make **φ** (Path-2's share of the
delivered command at 6–9 Hz) measurable, replacing V97's modelled `[0.085, 0.556]`.

## ⭐ THE AGGREGATOR IS AN UNWEIGHTED 11-TERM SUM [EVIDENCE — decompile + opcode census]
`FUN_0003aa2c` @`0x3aa2c`, with `gp-0x67ac ≡ 0`:
```
gp-0x6b94 = clamp( gp-0x6ade + gp-0x6b4c + gp-0x6ad4 + gp-0x6b62 + gp-0x6b26 + gp-0x6bbe
                 + gp-0x6bd0 + gp-0x6b86 + r24_lane + r26_lane + FUN_00036682(), ±0x2800=10240 )
                                ^^^^^^^^^ PATH 2, coefficient +1
```
Per-term `[|·| ≤ W]` factors are **zero-reject booleans (0/1), NOT gains.**
**Assembly `0x3acc8`–`0x3ace6`: `mov` + TEN `add` + `jarl`(→`FUN_00036682`) + `add`. 16-bit opcode
census `{add:10, mov:2}` — ZERO multiplies.**

⇒ **φ is not a share of a weighted mix — it is `Path2/total` at ONE junction, all coefficients +1.**
Two numbers at the same node in the same units; no modelling.
⇒ `build_v97_tva.py:65-67`'s **"Path 1 is unweighted" — CONFIRMED.**

## `gp-0x374c` NEVER LEAVES `FUN_00038148` ⇒ "unaffected by A" CONFIRMED [EVIDENCE, 2 methods]
Ghidra `search_instructions "-0x374c"` → **2 hits, both in `FUN_00038148`** (`ld.w` @`0x381fe`,
`st.w` @`0x38230`); raw both-parity Python → the same 2; absolute literal `0xFEDFC8B4` → **0**.
⇒ `0xC63AC` cannot reach any of the other ten summands.
⊕ `gp-0x6ad4` = **1 writer** (`0x3a8a0`) / **1 reader** (`0x3aca8`). Python's extra hit @`0x767b2` is
**adjudicated OUT** — `op6=0x23`, not `ld`(0x39)/`st`(0x3b); neighbour `0x767a8` carries the identical
pattern. **A dense 16-bit stream manufactures gp-relative-looking coincidences — always check op6.**

## 🛑🛑 THE 4.9× RECTIFICATION TRAP — a live defect, and a measured case for the design law
CAN 427 carries `|gp-0x6b70|` (`clamp(|X|*5>>6, 0, 0x3FF)`); the SIGN is a separate cave bit (V98 b7).

| reconstruction | **6–9 Hz RMS engaged** | eng/manual |
|---|---|---|
| **SIGNED (b7 applied)** | **548.28** ✅ matches the record's 548.3 | 18.51 |
| RECTIFIED (magnitude only) | 112.73 | 3.93 |

**The sign toggles 5.06 ×/s (918 transitions in 181.5 s) ⇒ `|x| ≉ ±x`.**
🛑 **`rlog-tools/v98_r81_score.py:541` feeds D4b the RECTIFIED lane** (`d["mt_row"]*(64.0/5.0)`) ⇒ its
`mt427_gp6b70` band claims understate 6–9 Hz by **~4.9×**. **Reported, not fixed.**
✅ `TRACE-2026-08-13-path2-authority`'s **140.6 ct is CORRECT** (0.2565 × 548.28 = 140.63).

⭐ **This is the design law's "sign bit paired with a magnitude channel" MEASURED on a real lane:
omitting the sign costs 4.9×.** Quote it whenever a rectified magnitude channel is proposed.

### 🛑 BLAST RADIUS — a **REGRESSION at V98**, NOT a replicating class [EVIDENCE, full sweep]
Every script that touches `ab_mt` **and** does spectral work was checked:

| script | 427 → spectrum | verdict |
|---|---|---|
| `v87_probe_6b98.py` (r71) | ⭐ made rectification a MEASUREMENT — Stage 2 *"RECTIFICATION TRANSPARENCY"*, screens each window for a zero approach, reports screened AND unscreened | ✅ |
| `decode_v90_probe.py` (r77) | `_bandpow(S["signed"])` | ✅ |
| `v92_boost_lane_and_rez.py` (r77/78/79) | "band content of the SIGNED lane" | ✅ |
| `v95_lane_decomposition.py` | `S["signed"]` for spectra; `mag` only for levels | ✅ |
| `v96_probe_vs_ratchet.py` (r7e/7f) | `signed_lane()` → `welch` | ✅ |
| `v97_r80_vs_v96.py` (r80) | `ab_signed` → `csd`/`welch` | ✅ |
| **`v98_r81_score.py:541`** | `mt427_gp6b70` RECTIFIED into D4b | ❌ |
| **`v99_r82_score.py:672,718`** | `mt427` RECTIFIED into AUDIBLE + CROSSBUILD | ❌ |

Both defective scripts **do** compute `sign_6b70` (`v98:87`, `v99:118`) and apply it elsewhere — a
one-line omission on one row. **Unlike the raw14 off-by-one, this has a clean before/after.**

**Measured verdict impact** — r82/r81 ENGAGED 6–9 Hz on the `mt427` row: **0.865 rectified
(reads as a 13.5 % improvement) vs 0.976 signed (a NULL)**. Within-route ENG/MAN: 3.933 vs 18.509
(r81), 3.361 vs 19.431 (r82). ⊕ Engaged sign-flip rate is **11.68/s (r81) / 13.09/s (r82)** — the
"5.06/s" figure is whole-drive.
✅ **`Re(Z) < 0` is NOT exposed**: `Z = S_Tw/S_ww` from `tq` + `rate_f`, **both `0x18F` fields**
(`v92_boost_lane_and_rez.py:103-110`); 427 is not involved.
✅ HANDOFF §1's *"427 broadband-elevated 4.14×"* was **already retracted** as a ZOH image — the
rectification is a second, independent reason; its replacement (2.30×) used the signed lane and is safe.

### ⭐ THE FREE φ ANCHOR — `RMS₆₋₉(gp-0x6b70) / RMS₆₋₉(column torque 0x18F)` = **1.190 (r81) / 1.178 (r82)**
Stable to **1.0 % across two routes and two builds** ⇒ the cross-route numerator in `φ = 140.6/R` is
predictable from a **free `0x18F` channel** on any future drive. **Within-drive comparator anchors are
not needed for φ; use 1.18.**

## THE φ INSTRUMENT — 427 repoint, ~2 bytes, NO cave growth [spec, not built]
`clamp(|gp-0x6b94|*5>>6,0,0x3FF)` → **max code 800 of 1023 ⇒ SATURATION STRUCTURALLY IMPOSSIBLE**,
LSB 12.8 ct. Edit = hw2 at `0x55DF2` only; packer and `0x55E10 sar 0x6` unchanged.
**GATE 1 store set unchanged `{gp-0x1514, gp-0x1511}`.** GATE 3 satisfied — ±10240 is the lane's OWN
output clamp (`0x3acec`), not a downstream gate.
Bits: **b7 = `gp-0x6b94 < 0` MANDATORY**; b6/b5/b4 = `2ᵏ|gp-0x6ad4| ≥ |gp-0x6b94|` (broadband ratio
CDF, **not** the band ratio — say so); b3 = `|gp-0x6b70| ≥ 1024`, **pre-measured duty 0.4559 engaged /
0.5913 manual**.

**🛑 NO NULL IS POSSIBLE:** `φ = 140.6/R` with R a signed unsaturated known-LSB RMS.
**CROSSOVER `R ≈ 387 ct`** — below it a lane ratio of 1.242 clears V85's not-felt 1.088; above it, it
does not. 15 s engaged ⇒ RMS rel. s.e. 7.5 %.

## Related
[[reference_accord_c63ae_dose_is_a_level_not_an_ac_change]] — φ is the soft link in that NO-GO.
[[reference_accord_path2_bracket_criterion_closes_openloop_not_closedloop]] · [[reference_accord_c63ac_is_the_pure_lead_pole_lever]]
