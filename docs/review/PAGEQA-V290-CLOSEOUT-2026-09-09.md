# Adversarial QA of the V290 close-out page vs its sources — 2026-09-09

Agent `pageqa2` (predecessor `pageqa` was killed by the machine restart, wrote nothing). Target:
`analysis-2020accord/_scratch/out/artifact_v290_closeout_2026-09-09.html` (331 KB), generator
`analysis-2020accord/studies/closeout/gen_v290_closeout_page.py`. Section 5 (placeholder) excluded per brief.
**Fixes nothing — findings only.**

## Method

1. Extracted the HTML's h2-delimited sections with a small script (`extract_page_numbers.py`, scratchpad),
   stripped tags, and read the generator source in full to classify every number as either (a) computed at
   render time from a named JSON (`v290_closeout_delta.json`, `h1_figdata_2026-09-09.json`,
   `ledger_v38_to_v289.json`, `v290_closeout_marks.json`, `v289_page_data.json`, `v290page_psd.json`) — low
   transcription risk, verified by re-deriving the JSON's own numbers and diffing against the rendered text —
   or (b) hand-typed prose quoting a study report/txt file — verified by grep/read against the named source.
2. Independently re-read the three images (stock, V282, V289) byte-for-byte in a fresh ~30-line
   little-endian Python script (no build-script constants), for the cells and byte-diff count the brief named.
3. Attempted the Chrome layout pass; the `mcp__claude-in-chrome__*` tools are not present in this session
   (two `ToolSearch` queries returned no match) — **skipped per instruction, not retried further.**

## 1. Numbers audit — mismatches

| # | Page claim (location) | Page value | Source value | Source | Severity |
|---|---|---|---|---|---|
| 1 | §1 three-count box #1: "V288 and V282 marks read 19.7–20.4 Hz" | range 19.7–20.4 Hz | V288 **mark 3** reads **18.85 Hz** (table, §2) — outside the stated range. (V288 m1 19.73, m2 20.04, **m3 18.85**; r39 m1 20.09, m2 20.08) | `rlog-tools/studies/grind/V289-MARKS-R62-R63-2026-09-09.md` §2 | **WRONG** |
| 2 | §1 mark_block caption, r62 (V289) bookmark 917.8 s: "the 7.6 Hz ring (violet) peaks at **1322 raw** 2.6 s before the press" | 1322 | The JSON that actually draws this exact figure gives `b5_12_pk` = **1277.1** (`@ -2.6 s`) — the chart's own auto-generated label will print "1277 @ -2.6 s", contradicting the caption 4 lines above it. 1322 is instead `marks62`'s manually-read figure from a different script/window. | `analysis-2020accord/_scratch/out/v290_closeout_marks.json` (`r62_v289.marks[0].b5_12_pk`); generator `mark_panel()` draws directly from this file | **WRONG** |
| 3 | §1 mark_block caption, r63 (V289) bookmark 684.3 s: "the 7.5 Hz ring peaks at **1432 raw** 2.4 s before the press" | 1432 | Same file, `r63_v289.marks[0].b5_12_pk` = **1411.7** — chart label will print "1412 @ -2.4 s" | `analysis-2020accord/_scratch/out/v290_closeout_marks.json` | **WRONG** |
| 4 | §1 three-count box #3: "V288's loudest 640 and every V282 bookmark (**≤ 402**)" | 402 labelled a "bookmark" bound | 402 is the **route-wide census max** for r39 (§5 table: env pk p50/p90/max 114/243/**402**), not a bookmark value — the actual r39 *bookmark* envelopes were 360 and 263. The bound is numerically true (402 ≥ 360) but "bookmark" mislabels the quantity. | `V289-MARKS-R62-R63-2026-09-09.md` §2 (bookmarks: 360, 263) vs §5 (route max: 402) | STYLE |
| 5 | §3 "for the colleague" synthesis: "a quantisation residual **18–32×** smaller than the torque line" | 18–32× | Correctly sourced from `H1-FIGURES-README-2026-09-09.md` (18.1× r39, 20.1× r5e, 32× at the 20 Hz bin), which uses the *native-tap / GI.band* residual (`q6_hyp`-adjacent method). The **h1_budget figure captions two paragraphs above**, generated from the same JSON's `spec_median`/`band_from_spec_median` fields, imply a **different** ratio for the same comparison (41.1/2.15 ≈ **19.1×** grind, 13.2/2.25 ≈ **5.9×** quiet on r39). Both numbers are independently traceable to real files, but the page silently switches between two slightly different residual-measurement instruments for what reads as one continuous argument. | `docs/review/H1-FIGURES-README-2026-09-09.md` vs `h1_figdata_2026-09-09.json.amplitude_budget` | STYLE (flag for disambiguation, not a fabrication) |
| 6 | §6 note: "the first move of the fb pole in **285 images**" | 285 | `accord-firmwares/analysis-2020accord/` currently holds **292** `*_plain_image.bin` files. "285" may deliberately exclude non-flight-line/test images, but that wasn't stated or verified against a defined denominator. | directory listing, `../accord-firmwares/analysis-2020accord/*_plain_image.bin` | ROUNDING / unverified (low confidence this is actually wrong — flag for the author to state the denominator) |

**Everything else checked was correct**, including several claims worth recording as *passing* because they are exactly the ones the brief called out as highest-risk:

- H1 index LSB: 16.13 (all three citations) reproduces `h1_figdata_2026-09-09.json.step_per_lsb.cmd[0]` = 16.1257 exactly.
- H1 dither/quantiser fractions (±1 alternation, two-value dwell, frames-changed, capped-frame share) in the §3(d) histograms: exact against `h1_figdata_2026-09-09.json.wire_dcmd`.
- H1 band ratios in the amplitude-budget captions (2.15/2.25/41.1/13.2 for r39; 2.29/2.25/46.2/14.9 for r5e): exact against `amplitude_budget.*.band_from_spec_median`.
- H1 record table (§3f): every field (`f0`, `f0_lo/hi`, `n`, `presence_pct`) is a byte-exact quotation of `rlog-tools/studies/grind/_scratch/loopshape20_mode_nature.txt` lines 23–27.
- The 427 tap spectrum is genuinely drawn only to 25 Hz — `amplitude_budget.*.f50` tops out at exactly 25.0 Hz in the source data (not just an axis label), so the tap polyline cannot visually extend past it.
- The median series (`spec_median`, `specT_median`) is what's plotted and quoted — confirmed by reading the generator code (`h1_budget()`), not just the output text; no `_mean` field is touched anywhere in §3.
- §1 episode table (all four routes' present %, episode/h, f0, env pk) and the "12–18 Hz re-census" / "agnostic 12–25 Hz" columns: exact against `grind1_census_v289_r62_r63.txt` and `grind1_census_v289_agnostic.txt` (spot-checked every cell, including the `<8 m/s` stratum values 16.28→"16.3 Hz" and 16.43→"16.4 Hz").
- §1 build-identity table (b5/b7 duties, "in grinding episodes" 0.30/0.24/0.41/0.49): exact against `V289-QLIVE-R62-R63-2026-09-09.md` lines 19–27.
- §4 delta table, sha256 chips, byte/run counts (1984/311, 185/6, 2159/314), and the Kp/Kd/map bank first-and-last-Y values: all independently re-derived from the raw images byte-for-byte (own script, see §2 below) and matched exactly, including the 6-vs-7-run subtlety in the V282→V289 diff (the run-merge rule counts *unchanged bytes between* runs, not raw address delta — my first pass miscounted 7 before correcting to match the page's 6).
- §6 "26 images": exact (`ledger_v38_to_v289.json.order` has 26 entries including STOCK).
- §2 notch magnitude/phase hardcoded in the loop diagram (|N|=0.76/−2.4 dB/−40° at 16.5 Hz; +86° at 20.3 Hz) and the −3 dB band (16.98–23.64 Hz → "17.0–23.6 Hz"): reproduced independently from the decoded coefficients.

## 2. Independent image byte cross-check (own ~30-line script, little-endian, no build-script constants)

Read `stock_fw_dump/code.bin`, the V282 and V289 plain images directly:

| cell | stock | V282 | V289 | matches page/JSON |
|---|---|---|---|---|
| 0xC63E8 (fb pole a) | 923 | 923 | 875 | yes |
| 0xC63EA (fb pole b) | 1560 | 1560 | 2301 | yes |
| 0xC61B4 (out clamp) | 512 | 3072 | 3072 | yes |
| 0xC61B6 (D clamp) | 10240 | 10240 | 10240 | yes |
| 0xC61BC (P clamp) | 15360 | 15360 | 15360 | yes |
| 0xC61BE (sum clamp) | 15360 | 15360 | 15360 | yes |
| 0xC64F0 (idx clamp) | 240 (as **u8**, not u16 — see note) | 240 | 240 | yes |
| Kp bank (0xE5378) first/last Y | 248 / 696 | 248 / 248 | 248 / 248 | yes |
| V282→V289 diff, [0x13000,0x100000) | — | — | **185 bytes, 6 runs** | yes |
| sha256 (12-char) | 3f1d55a98aac… | 0ea98d06b292… | f0c10c29752d… | yes |

Note for whoever re-derives 0xC64F0 next: it is a **single byte** (0xF0 = 240), not a `u16` — a naive `u16` read at that address returns 0xF0F0 = −3856/61680 and looks like a live cell change when it is not. The Kp bank record at 0xE5378 also isn't a bare Y-array: it's `[n(u16), X[0..n)(u16), Y[0..n)(u16)]`, so a direct offset guess without the header will misread it (I did, on the first pass, and got n=5 where I expected Y[0]=248). Both traps cost me a re-derivation; noting them for `firmware-decompile`-adjacent memory if not already there.

**No mismatch found** in this independent pass — every image-read cell and byte-diff count on the page reproduces exactly.

## 3. Layout (Chrome)

**Skipped.** `mcp__claude-in-chrome__*` tools are not present in this session — two `ToolSearch` queries
(`select:...` and a keyword query) both returned no matching deferred tool. Per the brief, not retried further.
No layout defects were checked; this is an explicit gap, not a clean pass.

## Summary for close-out

3 WRONG-severity numeric mismatches (all in section 1, all involving hand-typed prose numbers that
drifted from either a different source script's reading or the JSON that actually drives the figure next to
them), 2 STYLE-severity looseness issues, layout unchecked (tooling unavailable). Sections 3, 4 and 6 —
everything that is JSON-driven at render time — were exhaustively spot-checked and found correct, including
every H1 item the brief called out by name. The independent byte re-derivation found nothing wrong on the
image side.
