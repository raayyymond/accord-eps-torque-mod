# HANDOFF 2026-08-29 — the saturation census closed, the notch re-centred twice, and eight retractions

**Nothing was flashed and no CAN or UDS message was sent.** Everything below is analysis, unflashed
`.rwd` artifacts, and tooling. The car is unchanged.

---

## 1. WHAT TO DO NEXT — the shelf, in one screen

| build | image | what it is |
|---|---|---|
| **V209** | `984dfe5590bb8bfe…` | ⭐ **FLY THIS.** V208 + the `gp-0x6b4e` probe. 40/40, preflight 8/8 |
| **V208** | `e27b4fcc2dafd872…` | the fix without the instrument. 31/31 |
| **V210** | `ab49ca762b7017de…` | the ratchet lever (`0xC63AE` 1024→512), priced. 34/34 |
| **V199** | `c86646ab48c4a625…` | low-phase fallback (−2.95° instead of −7.98°) |

All four reproduce **bit-for-bit** from their builders (`verify/rebuild_shelf_bitexact.py`), each has
exactly one flashable `.rwd`, and all share the same 20.50 Hz notch.

**After the drive, one command:** `python rlog-tools/score/score_drive.py <route-tag>`

---

## 2. THE HEADLINE — what changed about the fix

The notch was re-centred **twice**, both times on measurement rather than argument:

```
   V196 and earlier   19.40–19.75 Hz, poles AT the zeros   max|H| 1.35–1.72  ** FAILED the gate **
   V199               19.75 Hz, poles BELOW at 17.45       max|H| 1.000000
   V202               19.75 Hz, poles 15.25 (wider skirt)  median 5.7× at the measured peaks
   V208               20.50 Hz, poles 15.50                median 9.5×, ** 14.9× band ENERGY **
```

**The first move fixed a gate violation.** `BUILD-LINEAGE.md` names "poles at the notch angle" as a
trap; every notch build from V188 on had walked into it, adding **35–72 % loop gain** above 30 Hz. It
shipped because V195's own GATE 2 assertion was written `mx <= 2.0` when the bar is stock's `1.0000`.
**The gate existed and the number in it was wrong.**

**The second move fixed a mis-tuning.** Surveying the corpus **per engaged episode** (20 routes, 125
episodes) put the grind peak at median 20.70 Hz against a notch at 19.75.

**V208 is now within 1.19× of the energy-optimal placement**, so it stands.

---

## 3. THE SATURATION CENSUS IS CLOSED — the largest negative result

The record's model of the ratchet is a *command-gated saturation*, with the instruction *"find what
clips."* Every clamp and gate between the LKAS command and the motor is now accounted for:

| element | verdict |
|---|---|
| 14 of 18 clamps | **cannot clip** — ceiling ≥ producer, or already measured inert |
| `gp-0x6ad6` | measured **0.000000** (V100 `b5`, CI [0, 0.0186], `b4`=0.6057 same cell) |
| `gp-0x6b94` vs the governor | measured **0.000000** over 49,021 engaged frames (V105 `b6`, route `a5`) |
| `gp-0x6b70` | measured **1 frame in 72,916** — duty 0.000014, six routes V96–V99 |
| all six aggregator zero-reject gates | **cannot fire** — every producer bounded at or below its window |
| the delivery-chain zero-reject on `gp-0x6acc` | **cannot fire** — bounded 870 counts under it |

⇒ **No clamp saturates and no gate fires anywhere in the firmware command path.** If a command-gated
saturation exists, it is in the FOC inner loop or mechanical — not in the code this kit edits.

⭐ **The gates are FAULT GUARDS, not shaping nonlinearities.** Every window is sized at or above its
own producer, so they exist to drop a *corrupted* lane. Reading them as shaping elements — which
"find what clips" invites — is a category error.

---

## 4. FINDINGS

- **`gp-0x6b70 = sgn(resid) × ASSIST_CURVE(|resid|)`** — the observer re-uses the power-assist curve,
  computable from `assist_map_mirror.py`. Not a hard relay but a **soft** one: gain 2.67–3.77× near
  zero vs 0.26–0.52× mid-range, a 6.7–10.7× compression ratio.
- **`0xC63AE` is that stage's private gain cal** — 1024, **one site image-wide** (`0x38242`), zero
  writers, virgin. Scales this stage only; the assist map is untouched. **V210 halves it.**
- **The inertia lever reaches the car, with the right sign.** V105→V106 is a single-cell pair
  (inertia ×2.000): `b5` moved **−0.0891 [−0.1328, −0.0200]**, both sign rungs null controls.
- **The cave is byte-identical v105 → v210**, so `b5` and `b6` report **free on every shelf build**.
- **GATE 2 for a scaled nonlinearity needs a describing function**, not a gain. `N_g(A) = k·N_f(k·A)`.
  V210's true reduction is **1.4–2.1×**, not the flat 2× a linear reading gives.
- **`0xC6CD0` is the only firmware authority lever** — the enumeration is closed, not open.
- **The friction lane is at 0.200× Honda**, not "reverted": `0xC40D2` holds Honda's K1 but the ramp
  knee `0xC40BC` was never reverted (600→3000) and multiplies the whole expression.
- **The compensation `gp-0x6ad0` is a motor-rate deadband scheduled on steering angle** — never named
  before. Arms more easily as angle rises (LERP1 5000→1000), permits more (LERP2 512→2560).

---

## 5. RETRACTIONS — eight of my own claims, each caught in-session

1. **"The pedestal passes 64.6 %"** — that was the clamp *ceiling* `K=204`; the table is **flat at
   K=20**, so it is **7.9 %**. I quoted a ceiling without reading the table.
2. **"`gp-0x6b86` is the LKAS command"** — it is the **base power-assist** output. With it went the
   claim that the notch gives back phase in peak-command-oscillation's currency.
3. **"The notch reshapes with steering angle"** — **angle-invariant**; one curve across 8 angles at
   every speed. It is **speed**-dependent.
4. **"V206 raises a ceiling"** — the ceiling is reached **1 frame in 72,916**. That was the argument I
   had said *survives* the speed-invariance objection; only the weaker gain argument survives.
5. **A limit-cycle amplitude prediction** — speed-indexed, against a symptom the record calls
   speed-invariant. Weakened, not sustained.
6. **A command↔peak correlation** (ρ = −0.351, p < 0.0001) — **pseudo-replication**; at route level
   (n=20) p = 0.14. Within-route/total variance is 0.24, so episodes inside a route are not
   independent.
7. **The unweighted peak histogram** — gives an episode with 1 % of the grind the same vote as one
   with 20 %. Power-weighted the median is **21.48**, not 20.70.
8. **A rail-mass statistic on `probe`** — that column is a packed **boolean rung byte** (4–6 distinct
   values, spaced 64 and 16), not a magnitude. The numbers carried no information.

🛑 **On #8: the control did not catch it.** `cs_tq` behaved perfectly, because the statistic was fine
and the *channel* was wrong — which no control on a different channel can detect. **Looking at the
data caught it.**

---

## 6. OPEN ITEMS — each with what would close it

| open | what closes it |
|---|---|
| Does `gp-0x6b4e` reach its ±10240 writer saturation? | **Fly V209.** Its producer is an uncapped 10-slot accumulator, so unlike V207's this bound is **not provable** — it must be measured |
| Is the halved inertia reaching the car? | **Free on any shelf drive**: `b5` should read 0.31–0.49; **≤0.28 retires the lever** |
| Is `0xC63AE` worth its assist cost? | Fly V210 after V208 confirms. The sign is known (predominantly *less* assist, since `gp-0x6b70` is negative 67.19 % of engaged time) |
| `gp-0x6b84` (resid mirror, ±0x3000) | Unmeasured; worth a rung if a future cave has a spare |
| Four mixer accumulators (`gp-0x3d74/88/70/98`) | Written in the same pass as `gp-0x3d8c`; **never named in this kit** |
| `r1e`'s genuine 15–17 Hz line | One route, real, and V208 gives only ~2.1× there. Not a cluster — not tuned toward |
| The ramp knee `0xC40BC` = 3000 | Reverting raises friction 5× against a standing instruction. **Recorded, deliberately not built** |
| Route registry stops at `r77` | All 13 routes `r77`–`ra6` are unlabelled. Needs the rlog *tails*, which are not in `_scratch/cache` |

---

## 7. TOOLS ADDED

`score_drive.py` (one-command post-drive scoring, power-weighted) · `rebuild_shelf_bitexact.py` ·
`saturation_census.py` · `reject_gates_can_never_fire.py` · `gate2_v206_describing_function.py` ·
`c63aa_dilution.py` · `notch_*.py` (phase cost, design sweep, minimax) · `unread_rung_sweep.py` ·
`grind_peak_covariates.py` · `inertia_dose_response_v105_v106.py` · `decode_6b70_from_v96_v99.py`

The close-out check grew from 24 to **114** assertions, and now sweeps every python file for parse
errors, every flashable image against GATE 2, the latent injector's amplitude, and the friction
lane's true multiplier.

---

## 8. PROCESS LESSONS WORTH KEEPING

- **Before designing a probe, check whether a flown build already carried the rung.** V105's `b6` was
  cut for exactly the question I was about to build a probe for and had sat unread.
- **A degenerate rung (duty 0.000000 or 1.000000) is UNINTERPRETABLE, not a null.** 43 of 115 cached
  rung readings are degenerate.
- **"Episodes not windows" has a twin one level up: routes not episodes.** The record named the first;
  the second cost me a false p < 0.0001.
- **Never hand-roll a gp displacement scan.** `ld.hu` encodes `hw2 = disp|1`; a raw even-parity search
  reported "0 hits" for cells the disassembly reads four times. `scan_gp_relative_no_whitelist.py`
  handles it.
- **Derive an exact byte-count expectation, never assume it.** `1024 → 512` moves one byte, not two.
- **Decompile first.** I read assembly upward for two ticks chasing a bound that one decompile of
  `FUN_000456a4` gave whole — and that decompile retired a build before it flew.
