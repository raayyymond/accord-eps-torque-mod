# H1 figure data — what is in `h1_figdata_2026-09-09.json`, in what units, and how it was measured

Subagent `h1fig2`, 2026-09-09. **Analysis only: nothing built, nothing flashed, nothing sent.**

- **Data file:** `analysis-2020accord/_scratch/out/h1_figdata_2026-09-09.json` (0.36 MB)
- **Producer:** `rlog-tools/studies/grind/h1_figdata.py` (`python h1_figdata.py all`; the wire stage is ~3.5 min per
  route the first time, then the episode mask is cached in `rlog-tools/studies/grind/_scratch/h1_figdata_hot_<tag>.npz`)
- **Companion:** `docs/review/H1-TORQUE-TABLE-RESOLUTION-2026-09-09.md` (subagent `hyptable`) — that report **tested**
  H1; this file gives a page the numbers to **plot**.

Every number in `map_curves`, `step_per_lsb`, `wire_dcmd` and `amplitude_budget` is **EVIDENCE**, re-derived here from
the built images and the wire caches by the script above. Nothing is copied out of the report text. `record_table`
rows are **EVIDENCE for the quotation** and each row names the file it came from.

**Images read** (`ACCORD_FIRMWARE_ROOT=C:/Users/dudei/Desktop/Projects/accord-firmwares`, `/analysis-2020accord/`):

| build | file | sha256 (12) |
|---|---|---|
| stock | `stock_fw_dump/code.bin` — **the true stock dump**, present, so `_v83a` was not needed | `3f1d55a98aac` |
| V112 | `_v112_…RELAY.KNEE1800…` (stock map, for the "stock-map era" rows) | `f032878c4e0b` |
| V282 | `_v282_…MAP.LINEAR.TO6X…` | `0ea98d06b292` |
| V289 | `_v289_…SUMNOTCH.20.05HZ.Q3-FBPOLE.25HZ…` | `f0c10c29752d` |

`_v83a`'s map bytes were checked and are identical to `code.bin`'s at `0xE502C`, so either would serve; the true dump
is what the figures use. **V289's map is byte-identical to V282's** — the two curves coincide exactly, so plot one
line labelled "V282 / V289".

**Wire caches:** `r39` (V282, 880 s engaged, 79 episodes) and `r5e_v288` (V288 rev 2, 642 s, 46 episodes), from
`analysis-2020accord/_scratch/cache/v280/`. V288's assist map and rate loop are byte-identical to V282's, so both
routes answer for V289's map as well.

---

## Series 1 — `map_curves`: setpoint vs command, staircase and continuous

The x axis is the **raw 0xE4 steer command, 0…4096 counts**. The y axis is the **rate setpoint**, given three ways:
`stair_sp` (sp counts), `stair_sp_degs` (deg/s), `stair_sp_out` (output torque counts after P).

- `builds.<name>.stair_idx` / `stair_cmd_lo` / `stair_cmd_hi` / `stair_sp*` — **241 points, one per index value**.
  Draw as a step plot: index *i* holds from command `stair_cmd_lo[i]` to `stair_cmd_hi[i]`. This is the staircase.
- `builds.<name>.cont_cmd` / `cont_sp` / `cont_sp_degs` — 1025 points, the same LERP with both floors removed. Overlay
  it on the staircase to show how little the quantiser costs.
- `builds.<name>.knot_cmd` / `knot_sp` — the 10 LERP knots, in the same command units. **The X knots are identical on
  all four images**; only Y is scaled. A knot is a *slope change*, never a jump.
- `idx_quantiser` — index vs command directly (every 4th command value), plus each bin's first and last command.

Key constants in this block, all re-derived:

| quantity | value | how |
|---|---|---|
| 1 index LSB | **16.126 raw 0xE4 counts** (0.394 % of full scale) | `2^22 / (255·255·4)`, confirmed by enumerating 0…4096 |
| measured bin widths | 16 or 17 counts | enumeration |
| index 240 first reached | command 3855 | enumeration |
| index 1 first reached | command **+1** going one way, **−17** going the other | enumeration — see the sign asymmetry below |
| 1 setpoint count | **0.1295 deg/s** | `32 / (fb_DC · 8)`, fb_DC `= 2·1560/(1024−923) = 30.89` from the image |
| 1 setpoint count through P | **5.06 output counts** | `32 · 248/256 · 5346/32768` |
| integer-LERP truncation | −0.97 … 0 sp counts on **both** maps | staircase minus continuous over index 0…240 |

⚠ **The quantiser is sign-asymmetric near centre, and this is new.** Both shifts are V850 `sar`, i.e. arithmetic shift, i.e. **floor** — so for one command sign it floors *away* from zero and for the other *toward* it. Index 1 is reached at command **+1** but not until command **−17**. That is a fixed one-index offset between the two steering directions near centre (`idx_quantiser.sign_asymmetry_note`). It is a standing offset, not a dither, it does not scale with the map, and it is far too small and too static to make a 20 Hz tone — but it is worth drawing on the quantiser box, and `hyptable`'s report did not surface it.

**The quantiser is map-independent.** It sits *before* the map and no build has ever changed it (`0xC64F0` = 240 on
all four images). Scaling the map does not change how finely the command is resolved; it changes how much setpoint
each index step is worth.

⚠ **Note for the "output counts" axis.** `stair_sp_out` is the **unclamped** steady P response, computed for **both**
maps through **one reference loop** (Kp 248 flat, gain 5346>>15 — the V282/V289 loop), so the curves isolate the
*map*. Each image's own cells are in the `images` block: stock's real gain is 891 (read at `0xC646C` through the
`0x2A1EE` displacement, not a hard-coded address) and its real output clamp is 512, against V282's 5346 and 3072. The
±3072 output clamp binds above about index 141 on the V282 map, so the top of the V282 "output counts" curve is
above what the ECU can deliver — mark the clamp on the plot rather than drawing the curve as delivered torque.

## Series 2 — `step_per_lsb`: what one index LSB is worth

- `idx` (1…240) and `cmd` (the command at that index) are the x axes.
- `builds.<name>.dsp_counts` / `dsp_degs` / `dT_out_counts` — the setpoint step per index LSB.
- `builds.<name>.step_multiset` — how many index steps take each integer size. **stock: {0: 104, 1: 102, 2: 32, 3: 2};
  V282/V289: {4: 168, 5: 72}.** The stock map is the one with a genuine staircase (104 index steps move the setpoint
  by *nothing at all*); the 6× map alternates between slopes 4 and 5 and never stalls.
- `per_interval` — the same thing per knot interval, the report's A3 table recomputed.
- `relative_step` — step ÷ value at a few indices. **Essentially identical on both maps** (0.17 vs 0.19 at index 6,
  0.006 vs 0.006 at index 200): the *relative* resolution does not degrade with scale, by construction.

Ranges: V282/V289 0.518–0.647 deg/s per LSB (20.2–25.3 output counts); stock 0.000–0.389 deg/s (0.0–15.2 counts).

## Series 3 — `wire_dcmd`: does 0xE4 dwell on two values?

Per 2 s census window (0.5 s step) on the dejittered 100 Hz 0xE4 clock. **Grinding** = window inside a detected
episode (`grind1_census_v282.py`'s recipe: 15–26 Hz prominence ≥ 8 **and** 18–22 Hz bar ≥ 40 raw). **Quiet** =
engaged, not in an episode, v < 12 m/s, |bar| < 400 raw — the matched baseline.

- `hist` — the **pooled** |Δcmd| distribution over frames: **201 bins, one per integer 0…199 plus a final bin
  for ≥ 200** (`hist_edges` gives the 202 edges; the last is a sentinel). Mark **122.88** on the axis: that is openpilot's `rate_limit(±0.03/frame) × 4096` slew cap.
- `hist_pooled_groups` — the same distribution collapsed to the report's groups, for a table.
- `alt_frac`, `two_c`, `two_i`, `one_i`, `chg_frac`, `cap_frac`, `idx_rate`, `v`, `bar` — each is a dict of
  p10/p50/p90/mean over windows.

| statistic (p50 over windows unless noted) | r39 grind | r39 quiet | r5e grind | r5e quiet |
|---|---|---|---|---|
| command changes on this fraction of frames | 0.990 | 0.954 | 0.995 | 0.975 |
| ±1 alternation fraction | **0.000** | 0.005 | **0.000** | 0.005 |
| 100 ms windows on exactly two command values | **0.000** | 0.000 | **0.000** | 0.000 |
| 100 ms windows on exactly two index values | **0.000** | 0.053 | **0.000** | 0.000 |
| slew-capped frames (pooled, ≥ 122) | 0.131 | 0.016 | 0.210 | 0.087 |
| index bin-crossing rate p10/p50/p90 (/s) | 65/80/92 | 40/53/71 | 71/89/97 | 37/67/88 |

**Nothing dwells.** These reproduce the report exactly.

## Series 4 — `amplitude_budget`: the decisive plot

Pooled spectra, one 2 s Hann segment per census window.

- `f100` (0…50 Hz, 0.5 Hz bins) is the axis for `spec` / `spec_median`; `f50` (0…25 Hz) is the axis for
  `specT` / `specT_median`.
- Series in `spec`: `q6` = the V282/V289 map's **quantisation residual** (staircase minus continuous, pushed through
  P and the gain, in **output counts**); `qs` = the same residual with the **stock map** on the same command;
  `q6_hyp` = the residual computed with `hyptable`'s exact recipe (see deviations below); `cmd` = the raw command;
  `bar` = the 0x18F driver-torque bar; `rate` = the 0x18F wheel rate. `specT` is the **427 torque tap**.
- Units of every spectrum: **peak amplitude per 0.5 Hz bin**, normalised so that a pure sinusoid of amplitude *A*
  reads *A* over its mainlobe, and so that summing bin² over a band recovers the kit's `GI.band` convention
  (`√2 × σ_band`). Validated on synthetic sine and noise: a 30-count sine reads 30.0 at both sample rates.
- **Use `spec_median` / `specT_median` for the drawn curve** (per-bin median across windows). `spec` is the mean-power
  pool; grinding windows are heavy-tailed, so the mean sits well above the typical window.

🛑 **The 427 tap streams at 50 Hz** (measured: median Δt = 0.020000 s), so its spectrum is only defined to 25 Hz.
**Do not draw the tap above 25 Hz.** The residual, command, bar and rate are 100 Hz and are honest to 50 Hz.

What the plot shows, r39 (median spectra, output counts per 0.5 Hz bin):

| f (Hz) | residual, grinding | residual, quiet | tap, grinding | tap, quiet |
|---|---|---|---|---|
| 5 | 0.72 | 0.82 | 9.1 | 5.3 |
| 12 | 0.76 | 0.77 | 5.3 | 2.9 |
| 18 | 0.71 | 0.79 | 5.5 | 3.4 |
| **20** | **0.77** | **0.76** | **24.5** | **5.8** |
| 22 | 0.68 | 0.74 | 7.2 | 3.4 |
| 40 | 0.75 | 0.70 | — | — |

The residual is **flat at ~0.7–0.9 counts per bin from 3 to 50 Hz and identical in grinding and quiet windows**. The
tap has a **4.2× peak at 20 Hz that appears only when the car is grinding**. At the 20 Hz bin the tap is **32×** the
residual. Band-integrated over 18–22 Hz, on r39: residual 2.15 (grinding) vs 2.25 (quiet); tap **41.1** vs 13.2.
r5e_v288 is the same picture (residual 2.29 vs 2.25; tap 46.2 vs 14.9). A second, smaller tap feature sits near 8 Hz
in grinding windows (21.0 vs 5.5 counts/bin) — that is the known 7 Hz ring, not part of H1.

Band numbers are given three ways so a reader can check them against each other:
`bands.*` (per-window `GI.band`, p10/p50/p90/mean), `band_from_spec_median` (integral of the median spectrum) and
`band_from_spec` (integral of the mean spectrum). The first two agree to ~6 %.

## Series 5 — `record_table`: the "coarser map was MORE present" point

`rows` carries build, map scale, Kp, f0 with its [p10–p90] spread, n, and presence, each with `source` and the exact
`raw` line it was parsed from — all of it from
`rlog-tools/studies/grind/_scratch/loopshape20_mode_nature.txt` (2026-09-08, 9 routes, 5 builds):

| build | map | Kp | f0 (Hz) | n | presence |
|---|---|---|---|---|---|
| V278r3 | ×2 concave | LERP 248→696 | 20.08 | 434 | **37.7 %** |
| V280r2 | ×6 linear | LERP 248→696 | 20.08 | 1026 | 24.3 % |
| V281r3 | ×6 linear | flat 248 | 20.06 | 293 | 16.2 % |
| V282 | ×6 linear | flat 248 | 20.03 | 586 | 15.2 % |
| V288 | ×6 linear + setpoint pre-filter (steps ~11× finer) | flat 248 | 20.06 | 198 | 15.6 % |

⚠ **Kp is confounded with map scale across these rows** — the two ×2/×6 rows with the highest presence also carry the
Kp LERP. The direction is still wrong for H1, and `kp_bins` / `idx_or_bar_bins` carry the within-corpus breakdowns
that separate them (f0 20.01 → 20.57 Hz as Kp goes 240–300 → 600–700). Say the confound on the page.

`stock_map_era` and `v288_null` are quoted claims with their sources named
(`docs/research/GRINDING-ROOT-CAUSE-LEDGER-2026-09-03.md`, `docs/review/GRIND1-CENSUS-V288-R5E-2026-09-08.md`);
they were **not** re-derived here — mark them as quotations on the page.

## Series 6 — `signal_path`: the diagram

`signal_path.mermaid` is a ready-to-render `flowchart LR` with the quantiser node highlighted and the LSB written on
it. `signal_path.nodes` / `edges` carry the same graph structurally, with each node's instruction address and cal
cell, if you would rather draw it as SVG. The chain is:

0xE4 command → `S = −4·cmd`, clamp ±16384 → `× (taper·speedF) & 0xFFFF` → **QUANTISER `>>16 >>6`, `|·|`, clamp 240**
→ assist-map LERP (10 knots, `divq` floors) → setpoint `sp` → `E = 32·sp − fb` → P and D → sum + post-PID fades,
clamp ±15360 → *(V289 only: 20.04 Hz Q3 notch cave)* → 5.05 Hz output lag → `× gain >>15` → clamp ±3072 → EME →
FOC/PWM → motor; the 0x18F wheel rate closes back onto `E`.

---

## Deviations from `hyptable`'s report — read before quoting a number

Both are recorded in the JSON under `deviations_from_hyptable`. Neither changes any conclusion.

1. **Index LSB: 16.126 counts here, 16.19 in the report.** The report used the taper value 254 from
   `v280_map_profiles.TAPER_Y`, which is the **superseded cliff arm**. The **live** arm read from the image
   (`0xCB924` slot 7 same-sign, `0xCB8B4` opposite-sign) is **255** for |bar| below 2591 raw — the whole regime the
   census windows sit in. A 0.4 % difference; it shifts the knot command positions by 0.4 % and nothing else.

2. **The quantisation residual.** The report's residual took the *staircase* index through the live taper but its
   *continuous* reference through the 254 cliff arm, injecting a 0.39 %-of-setpoint scale bias — a low-frequency term
   proportional to the command, not quantisation noise. Here both use the live taper, so the residual is purely the
   two floors and the integer LERP. The corrected residual is **smaller** (18–22 Hz: 2.27 vs 2.34 on r39 grinding),
   which strengthens the conclusion. **Both are in the file** (`q6` corrected, `q6_hyp` the report's recipe), and
   `q6_hyp` reproduces the report's 2.34 / 2.38 / 2.54 / 2.39 exactly.

3. **Tap band amplitude.** The report's 29.0 / 9.6 counts come from `GI.band` on the tap **interpolated to 100 Hz**,
   which loses gain near 20 Hz because 20 Hz is 0.8 of the 50 Hz stream's Nyquist. The same windows measured on the
   tap's **native 50 Hz clock** read **41.2 / 16.0** (`bands.T_band_native`, and the median-spectrum integral agrees
   at 41.1 / 13.2). Both are in the file. **The native number is the right one for a figure**, and it makes the
   tap-to-residual ratio larger, not smaller — the report's 12× is conservative. On the corrected residual and the
   native tap the 18–22 Hz ratio is **18.1×** on r39 and **20.1×** on r5e_v288, and **32×** at the 20 Hz bin
   itself. Even crediting the whole Ms = 3.8 closed-loop resonance peak to the residual, the gap is still
   **4.8–5.3×**. The quantiser cannot pay for the line under any accounting.

Everything else reproduced the report exactly, window counts included: 311/771 grinding/quiet windows on r39
(the report says 310/771) and 171/245 on r5e_v288.
