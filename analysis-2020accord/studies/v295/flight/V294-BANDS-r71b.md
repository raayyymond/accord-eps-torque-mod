# V294 bands read: route `75604b0a432fdc89_00000071--a7b8ba5d9d` (kit tag `r71b_v294`)

Subagent "bands", 2026-09-30. Analysis only.
- Nothing was sent, flashed, committed or pushed.
- The fork, the firmware artifacts, the kit's scorers, STATE, memory and the lineage were not modified.

**Bands, not symptoms.**
- Every number here is an instrument reading. Nothing below licenses the words "fixed" or "present" about anything
  the operator feels.
- Every claim is marked EVIDENCE (with the method) or BELIEF.
- The pre-registered FAIL/surprise criteria were written **before** any band was computed:
  `flight/bands/CRITERIA-BANDS-r71b.md`, written at 06:58 PDT. At that time only the cache extractions were running.
- All scripts, logs and outputs are under `analysis-2020accord/studies/v295/flight/bands/`.

> ⚠ **The operator's words.** The brief says he has not described this drive. However,
> `analysis-2020accord/studies/v295/OPERATOR-REPORT-r71b.md` exists and quotes him as saying:
> - *"No grinding or stuttering!"*
> - *"Jerky on hard turns at medium speed"*
> - *"Loose on straights and turns at low speed."*
> - *"Loose/understeer at highway turns."*
>
> I did not verify those quotes. I use them only to decide which bands to put next to which words. The questions in
> §6 are the ones the bands raise either way.

---

## 0. Bottom line (bands only)

1. **P1: the pre-registered outcome ("1.6–3 Hz wheel-rate energy in hard turns vs r75/r76, predicted DOWN") went
   DOWN.** It did not fire. EVIDENCE, by two independent methods on two different caches:
   - At **matched speed × planner demand in hard turns**, V294's 1.6–3 Hz wheel-rate rms is **×0.56–0.91 of r75 /
     r76** in every cell where both routes have ≥ 8 s.
   - It is below the whole V293-family range in every populated cell.
   - Hands-off by speed band it is lower than r75 and r76 at every speed ≥ 5 m/s. At 0–5 m/s the result is mixed
     (1.25 vs 1.49 / 1.22 deg/s).
   - The rev-5 O4 hard-turn statistic reads **6 %** (r75 19 %, r76 18 %).
   - It is still **2–3 × V282's** level at 1.6–3 Hz.
2. **P2 ("any NEW line in 5–30 Hz = the revert signature") FIRED as written, on one line.**
   - The line is **15.6 Hz on the 427 tap (+6.1 dB)** in the *engaged 0–5 m/s* stratum. No V293 reference has a
     line within 1 Hz and 3 dB of it.
   - EVIDENCE, localisation: 88 % of its energy sits in **one ~5 s hands-on manoeuvre at 0–1.8 m/s** near full lock
     (route 41–47 s, ≈ 20:10:48 PDT, BELIEF on the clock).
   - In that manoeuvre the driver-torque bar and the wheel rate carry the same 15.6 Hz line. Coherence with the tap is
     0.91 (bar) and 0.95 (rate). The 0xE4 command does **not** carry it (coherence 0.15).
   - It is absent hands-off.
   - It belongs to the same family as the hands-on low-speed lines on the V293 routes (r72 19.5 Hz, r73 22.3 Hz, r75
     20.7 Hz), at a different frequency.
   - No other ≥ 3 dB line is new. The 13.3 Hz line at highway speed tracks wheel rotation (v / 2.06 m) on V294, r75
     and r6c alike.
3. **The 2.34 Hz limit cycle** (route 71-old's signature, the expected symptom if the trim were not live) **did not
   fire**. EVIDENCE (the record's own S7 instrument):
   - At ≥ 19 m/s the rate peak is at 1.76 Hz, +1.8 dB. Route 71-old read +22.5 dB at 2.34 Hz, and the same line was
     in all four channels.
   - Near-miss, stated in full: on hard curves at v > 15 m/s (29 s) the **wheel rate alone** peaks at **1.95 Hz,
     +10.3 dB**. The command, error and angle peak at 0.39 Hz. The rule needs the rate peak in 2.0–2.7 Hz, so it does
     not fire, by 0.05 Hz.
4. **The high-frequency bands are the quietest of any V293-class flight** (EVIDENCE, the scorer).
   - F7: 0.00 per 100 s.
   - Tap rip/L: 0.004.
   - Absolute 6–8.5 Hz tap ripple: 2.9 counts, ×0.04 of V282.
   - 13–17 Hz on hands-off 8–15 m/s: ×0.88 of r6c. r76 read ×2.12 and fired REVERT.
   - 18–22 Hz engaged ÷ disengaged: 1.23 (V282: 3.4–3.9).
   - Ring presence: 0.5 %, in 8 windows.
   - 5–9 Hz on hands-off 8–15 m/s: the lowest of the V293 family.
5. **Outer loop: V294 + the r1 fork config UNDER-DELIVERS at low frequency, but on time.** EVIDENCE, three
   estimators agree:
   - Planner tracking gain is **0.80–0.83 at 8–22 m/s** and **0.93 above 22 m/s** (r75 0.97–0.99, r76 0.96–1.04,
     r6c 0.97–1.00).
   - Turn-hold act/plan at |D| 0.8–1.5 is **0.67–0.69 at 8–22 m/s** (r75 1.00–1.01).
   - Straight-line delivery is **58 %**, the lowest in the corpus.
   - Lag is **0.00–0.36 s** (r75 0.09–0.47, r76 0.32–0.57).
   - The integrator carries **0.25–0.41** of the torque.
   - BELIEF: this is the band behind "loose" and "understeer".
6. **J** (the goal metric, 0.15–2.4 Hz, ≥ 15 m/s): **0.417, 95 % block CI [0.314, 0.758]**, from 18 windows (115 s).
   - The CI is disjoint from rev 4 (1.015 [0.878, 1.312]) and rev 5 (1.178 [1.008, 1.476]).
   - It is indistinguishable from V282 (r64 0.465 [0.308, 0.878]; brief's reference 0.442).
   - EVIDENCE:
     - The record's own f1/f2 code reproduces the record to 1e-3 on three routes.
     - An independent implementation on the raw gyro reads the same ordering and the same ratio to rev 4 (0.40–0.42).
   - The low J comes from **timing**: at 0.15–0.3 Hz the transfer is |H| 0.78 at −16°, against rev 4/5's ~1.0 at
     −48/−57°. It does **not** come from gain.
7. **Two REVERT triggers fired as the scorer writes them.** Both have fired on **every** V293-class flight, so they do
   not discriminate this build:
   - **Outer loop** (1–4 Hz angle amplitude at 5–10 m/s is > 1.5 × V282).
   - **Ratchet** (dwells/min above r70's in 4 bands).
   - The **pre-registered prominence clause (< 3 dB) PASSES in all four bands** (2.22 / 1.04 / 2.87 / −1.40 dB). This
     is the first V293-class flight to pass it in every band.
8. **The 0x14A b4 negative control (sign r24) is unchanged.** EVIDENCE, two methods agree:
   - It reads 0.347 (V293 family 0.351–0.399).
   - Bits 0–2 read 1.000 (stock Honda).

---

## 1. Instruments and provenance (what ran, on what)

| instrument | code | caches | result file |
|---|---|---|---|
| The V293 flight read, sections 0–7, verdict block | `rlog-tools/studies/grind/v293_flight_read.py`, **unchanged**; run through `bands/run_flight_read.py` (see the defect note) with `--build V293 --config toggle-config_V294_accel-trim_r1.decoded.json` | v280 `r71b_v294`, cs `cs_r71b_v294` (the extract agent's) | `bands/v293_flight_read_r71b_v294.{txt,json}` |
| The same scorer on **r76** (rev 5) as a new reference | same, `--config …_r5.decoded.json`, tag `r76_v293r5` (v280 cache extracted by the scorer) | new `r76_v293r5` v280 + cs caches | `bands/v293_flight_read_r76_v293r5.{txt,json}` |
| Rev-4/5 outer-loop and hard-turn readers | `v293r5_read` n0/n1/n2/n3/n6, `v293r5_observer_read.read` O1–O4, `v293r3_read.analyse` + `compare` S2–S9. All called as library functions so nothing is written into grind/ | ident caches `r71b_v294_ident`, `r76_v293r5_ident` (new, `v293r2_extract.py`), `r75_v293r4_ident` | `bands/outer_loop_reads_out.txt` |
| 2.34 Hz limit cycle | `v293r2_read` S7, copied verbatim, plus the same computation at v ≥ 19 | ident | same file, section D |
| J | `v282-reference/shapedgain/frontier/f1_extract.do_route` + the f2 metric, unchanged (monkeypatched group map and output dir) | new `v282ref/00000071--a7b8ba5d9d.npz` (`build_cache.py`) | `bands/j_metric_r71b_out.txt`, `bands/j_metric_ci_out.txt` |
| Spectra by speed band, line list, P2 | `bands/spectra_by_band.py`, using `creep20_loop_id.load`, `seg_psds` and `excess_db` (the scorer's estimators) | v280 ×12 routes | `bands/spectra_by_band_out.{txt,json}` |
| Matched hard-turn cells | `bands/hardturn_matched.py` (record masks, ident lib band-passes) | ident ×7 routes | `bands/hardturn_matched_out.txt` |
| Command 1–4 Hz prominence | `bands/prom14_cmd.py`: the scorer's own `prominence_1_4` with the command in the angle slot | v280 + cs | `bands/prom14_cmd_out.txt` |
| Second methods | `bands/second_methods.py` (raw-rlog spot check, cave duties, J via gyro) | rlog seg 5, extract loader, ident | `bands/second_methods_out.txt` |

**Attribution precondition.**
- The scorer's own identity reads R² 0.9868, resid 22.4 counts, V293/bar at −30 ms. Its positive control is R² 0.9745.
  V282 cells give −1.02. EVIDENCE.
- The resid is larger than r75's (13.4) and r76's (11.6). That is the expected signature of the live trim: the
  extract agent measured 5.8 counts on low-acceleration frames.
- The fork config matched on all 26 keys. Kp 0.9000 and LAF 14.0000 at 100 Hz. EVIDENCE.
- The scorer has no `--build V294`. V293's cells are the correct surface because V294's feedforward is byte-identical
  (241/241 indices, extract agent).

**Loader spot check against the raw rlog** (the brief asked for one). EVIDENCE, M1:
- Segment 5 was decoded straight from `.rlog.zst` with the kit's stock cereal.
- The 0x14A byte 4 sequence is identical to the extract loader over 6000 / 6000 frames. The 0x18F rate is identical
  over 6000 / 6000 frames.
- A first version of this check read 0.981, because 2.4–2.6 % of CAN events carry two frames of one address at one
  timestamp and the timestamp lookup mis-paired them. That was an artefact of the check. It is fixed in the script.

---

## 2. Section (1): the V294 pre-registered outcome

### 2.1 P1 — 1.6–3 Hz wheel-rate energy and hard turns vs r75 / r76 (predicted DOWN) → **did not fire**

**(a) Hands-off, all demand, by speed band.** EVIDENCE: `spectra_by_band`, 0x18F rate, Welch 2.56 s, amplitude in
deg/s, exposure in s.

| band m/s | V294 | r75 (rev 4) | r76 (rev 5) | V293 family | V282 (r6c / r39 / r35) |
|---|---|---|---|---|---|
| 0–5 | **1.25** (81) | 1.49 (84) | 1.22 (38) | 0.91–2.07 | 0.79 / 0.55 / 0.74 |
| 5–10 | **1.68** (191) | 2.14 (256) | 3.19 (67) | 1.82–3.19 | 0.48 / 0.55 / 0.51 |
| 10–15 | **0.72** (208) | 1.59 (193) | 1.70 (58) | 0.83–1.70 | 0.35 / 0.40 / 0.30 |
| 15–22 | **0.83** (157) | 1.59 (130) | 1.37 (137) | 0.60–1.59 | 0.28 / 0.36 / 0.28 |
| 22+ | **0.95** (72) | 1.00 (85) | 0.98 (143) | 0.44–1.00 | 0.27 / 0.38 / 0.28 |

**(b) Matched speed × planner demand, HARD turns.** EVIDENCE: `hardturn_matched`, ident cache, ≥ 2 s stretches,
cell ≥ 8 s.
- `r16` = 1.6–3 Hz wheel-rate rms in deg/s. `shr` = its share of the 0.3–8 Hz energy.
- `coh` = command → rate coherence at 1.6–3 Hz. `c16` / `tap16` = command / tap 1.6–3 Hz rms in counts.

| cell | V294 r16 [shr] coh | r75 | r76 | V294 ÷ r75 / r76 | V293 family r16 |
|---|---|---|---|---|---|
| hands-off 5–10, \|D\| ≥ 1.5 | 11.8 [7 %] 0.62 (11 s) | 21.2 [20 %] 0.77 | – (7 s) | ×0.56 / – | 13.0–34.9 |
| hands-off 15–22, \|D\| ≥ 1.5 | 7.47 [39 %] 0.58 (14 s) | 10.8 [21 %] 0.76 | – | ×0.69 / – | 10.8 |
| hands-off v < 10, \|ang\| > 60 | 13.0 [6 %] 0.54 (23 s) | 18.4 [15 %] 0.65 | 16.1 [14 %] 0.80 | ×0.71 / ×0.81 | 15.2–31.6 |
| engaged 5–10, \|D\| ≥ 1.5 | 10.9 [7 %] 0.50 (14 s) | 19.4 [15 %] 0.67 | 16.3 [16 %] 0.84 | ×0.56 / ×0.67 | 15.0–32.2 |
| engaged 15–22, \|D\| ≥ 1.5 | 7.47 [39 %] 0.58 (14 s) | 12.3 [27 %] 0.90 | – | ×0.61 / – | 9.6–48.5 |
| engaged v < 10, \|ang\| > 60 | 14.6 [5 %] 0.25 (56 s) | 18.8 [9 %] 0.38 | 16.0 [14 %] 0.44 | ×0.77 / ×0.91 | 16.0–56.7 |

- At 15–22 m/s in hard turns the 1.6–3 Hz energy is lower in absolute terms, but it is a **larger share (39 %) of a
  smaller total**.
- The command carries less of it than on r75 (coherence 0.58 vs 0.76–0.90).

**(c) The record's own hard-turn readers.** EVIDENCE:
- **O4** (v293r5_observer_read, hard turns v < 10), 1.6–3 Hz share of 0.3–8 Hz wheel-rate energy:
  - **V294 6 %**, against r75 19 %, r76 18 %, r70 26 %, r71-old 17 %, r72 9 %.
  - Rate sign reversals: 63.3 /min, against r75 77 and r76 88.
  - Rev 5's own O4 clause ("not above r75's 19 % by more than 10 points; reversals ≤ 1.5 × 77") passes.
- **S4** (v293r3_read hard-turn jerkiness):

  | band | metric | V294 | r75 | r76 |
  |---|---|---|---|---|
  | v < 10 | \|rate\| > 80 bursts /min | 60.9 | 77.8 | 57.6 |
  | v < 10 | 0.5–5 Hz rate rms, deg/s | 48.3 | 43.6 | 37.3 |
  | v < 10 | reversals /min | 2.3 | 6.9 | 7.5 |
  | 10–20 | bursts /min | 37.6 | 60.4 | – |
  | 10–20 | 0.5–5 Hz rate rms, deg/s | 20.0 | 20.5 | – |
  | > 20 | bursts /min | 0.0 | 21.3 | – |
  | > 20 | 0.5–5 Hz rate rms, deg/s | 3.1 | 9.4 | – |
  | v < 10 | stall → ramp → snap | 1 event in 63 s (1.0 /min) | 0.0 | 0.0 |

  The v < 10 0.5–5 Hz rms is **higher** (+11 % / +29 %). That band contains the deliberate low-speed wheel motion;
  the mode band (O4, 1.6–3 Hz share) is the one that isolates the wheel mode, and it fell.
- **N2** (v293r5_read, hard turns by \|planner\| > 1.5 or \|angle\| > 60):

  | band | metric | V294 | r75 |
  |---|---|---|---|
  | v < 10 | rate rms, deg/s | 52.1 | 55.2 |
  | v < 10 | bursts /min | 107 | 135 |
  | 10–20 | rate rms, deg/s | 23.1 | 23.6 |
  | 10–20 | bursts /min | 97 | 154 |

**P1 verdict: the pre-registered prediction held.**
- 1.6–3 Hz wheel-rate energy went down vs r75 / r76 in every matched cell with exposure, and in every hands-off speed
  band ≥ 5 m/s.
- Two methods and two caches agree.
- The only exception is 0–5 m/s hands-off vs r76 (1.25 vs 1.22, r76 38 s).
- The redo audit's corrected physics predicted ζ× 0.89 at 5 m/s. A flat or slightly-up 0–5 m/s band is therefore not
  a surprise against the corrected design.
- It remains **2–3 × V282** in every band. BELIEF: the V282 rate servo damped the wheel far more strongly than this
  trim does, which is consistent with the design's "a damper comparable to the wheel's own".

**The medium-speed hard turns, event by event** (for the operator's "jerky on hard turns at medium speed"). EVIDENCE,
`hardturn_events.py`: v 8–22, \|D\| ≥ 1.0 for ≥ 1 s. PDT is BELIEF from the extract agent's GPS anchor, ±1 s.

| PDT | route s | v m/s | \|D\|pk | \|ang\|pk | hold act/des | 1.6–3 Hz rate rms | \|dr/dt\| p95 | i-share | tap 1.6–3 Hz |
|---|---|---|---|---|---|---|---|---|---|
| 20:11:21.6 | 75.6 | 9.2 | 1.38 | 45 | 0.72 | 6.3 | 456 | 0.40 | 5.8 |
| 20:11:28.5 | 82.5 | 10.0 | 1.82 | 46 | 0.71 | 10.4 | 669 | 0.09 | 11.3 |
| 20:12:20.1 | 134.1 | 9.5 | 3.02 | 97 | 0.89 | 11.5 | 669 | 0.26 | 12.4 |
| 20:12:30.1 | 144.2 | 9.9 | 2.53 | 79 | 0.96 | 13.0 | 700 | 0.38 | 11.7 |
| 20:13:25.5 | 199.6 | 10.8 | 3.79 | 96 | 0.84 | 9.3 | 778 | 0.24 | 8.8 |
| 20:13:34.0 | 208.0 | 12.6 | 1.13 | 10 | 0.42 | 2.1 | 256 | 0.15 | 7.9 |
| **20:16:52.8** | 406.8 | 10.5 | 2.71 | 100 | 0.72 | **16.2** | **914** | 0.21 | 15.7 |
| 20:18:59.1 | 533.1 | 17.8 | 2.63 | 25 | 0.90 | 3.4 | 374 | 0.21 | 5.6 |
| **20:19:11.1** | 545.1 | 19.2 | 2.73 | 27 | 0.77 | **10.0** | 588 | 0.14 | 10.6 |
| 20:21:26.7 | 680.7 | 8.7 | 1.75 | 71 | 1.00 | 5.5 | 443 | 0.54 | 5.6 |
| 20:21:43.2 | 697.2 | 16.7 | 1.38 | 13 | 0.56 | 2.8 | 212 | 0.14 | 3.8 |
| 20:24:15.2 | 849.2 | 15.4 | 1.20 | 10 | 0.60 | 2.5 | 329 | 0.09 | 3.1 |
| 20:25:52.5 | 946.5 | 15.6 | 1.24 | 18 | 0.71 | 4.8 | 442 | 0.20 | 15.7 |

Comparison with r75 (12 events): hold ratio 0.90–1.11 (median ≈ 0.97); 1.6–3 Hz rate rms 1.4–13.9; tap 1.6–3 Hz
2–24 counts.

- V294's medium-speed hard turns do **not** have more 2 Hz energy than rev 4.
- What distinguishes them is **under-delivery**: the hold ratio is 0.42–1.00 (median 0.72).
- BELIEF, not measured: under-delivery followed by the integrator's catch-up could read as "jerky". §6 asks him.

### 2.2 P2 — a NEW line in 5–30 Hz (the revert signature) → **FIRED on one line; localised**

The test is `spectra_by_band`: every ≥ 3 dB excess line in 5–30 Hz (tap 5–24 Hz), in hands-off and all-engaged strata
× 5 speed bands. A line is "new" if no V293 reference (r70, r71-old, r72, r73, r75, r76) has excess ≥ (V294 − 3 dB)
within ±1 Hz.

| stratum | band | channel | line | best V293 ref within 1 Hz | best V282 ref | verdict |
|---|---|---|---|---|---|---|
| engaged | 0–5 | **tap** | **15.6 Hz +6.1 dB** | +2.0 | +0.5 | **NEW** |
| engaged | 0–5 | rate | 15.6 Hz +4.7 dB | +1.8 | +3.0 | present (by 0.1 dB) |
| hands-off | 0–5 | tap | 19.9 Hz +3.7 | +2.9 | +5.3 | present |
| hands-off | 22+ | rate | 26.6 Hz +4.2 | +1.6 | +3.3 | present |
| hands-off | 22+ | tap | 5.1 Hz +4.6 | +2.1 | +0.6 | present |
| engaged | 22+ | rate | 13.3 Hz +4.6 | +3.0 | +3.6 | present |

**Where the 15.6 Hz line lives.** EVIDENCE: `line156_localise.py`, `line156_bar_tap.py`.
- It is **absent hands-off**: 0–5 m/s hands-off tap +1.1 dB, rate +0.0 dB.
- It is absent for \|cmd\| < 2000: +1.3 dB.
- In sliding 2.56 s windows, **88 % of the 14.5–16.8 Hz tap energy is in the top 5 windows**, all at route
  **41–47 s**.

The episode at route 41–47 s:
- v 0.0–1.8 m/s, \|bar\| p50 2394 (hands on, hard), \|cmd\| up to 4096, wheel 0 → 374°, \|rate\| p90 ≈ 250 deg/s.
- Line amplitudes in 14.5–16.8 Hz:

  | channel | amplitude | peak frequency |
  |---|---|---|
  | driver-torque bar | 108 counts | 15.62 Hz |
  | wheel rate | 3.7 deg/s | 15.62 Hz |
  | 427 tap | 23.6 counts | 15.62 Hz |
  | 0xE4 command | 2.7 counts | 13.28 Hz |

- Coherence with the tap at 14–17 Hz: **bar 0.91, rate 0.95, command 0.15**.
- EVIDENCE: the object is **mechanical** (hand + column + motor) and the delivered lane torque moves with it. The
  command does not drive it.
- BELIEF, sizing the V294 trim's share from the design gain: K_α ≈ 0.21 T-counts per deg/s² below the pole, ×
  |H| (2.03 Hz lag × 5.05 Hz output lag) ≈ 0.040 at 15.6 Hz, × α ≈ 2π·15.6·3.7 ≈ 360 deg/s². That gives ≈ **3 counts
  of the 24**. The remainder is consistent with the override fade (0xCBBC4, indexed by \|bar\|) modulating a large
  surface torque. **Driving versus following is not separable from this route.**
- Context:
  - The V293 routes each carry a hands-on low-speed line in the same stratum: r72 19.5 Hz, r73 22.3 Hz (hands-on),
    r75 20.7 Hz.
  - This is one more member of that family, at a new frequency.
  - The pre-registered rule does not distinguish hands-on episodes, so **it fired**, and I report it as fired.

**13.3 Hz at highway speed is the wheel-rotation order, not the loop.** EVIDENCE: the 9–18 Hz peak tracks
v / 2.06 m.

| route | speed m/s (median) | peak Hz | v / 2.06 Hz |
|---|---|---|---|
| V294 | 19.6 | 9.38 | 9.50 |
| V294 | 29.1 | 13.67 | 14.10 |
| r75 | 19.1 | 10.16 | 9.29 |
| r75 | 26.6 | 12.70 | 12.89 |
| r6c | 20.7 | 9.96 | 10.04 |
| r6c | 23.8 | 11.33 | 11.56 |
| r6c | 26.8 | 12.70 | 13.02 |
| r6c | 30.2 | 14.65 | 14.64 |

The 2.06 m tyre circumference is BELIEF. At 22+ m/s, 13–17 Hz wheel-rate amplitude is 0.75 deg/s: V293 family
0.40–0.74, V282 0.66–0.95.

**Full spectra by speed band** (hands-off and engaged; wheel rate 1.6–45 Hz, tap 1.6–25 Hz; nine sub-bands, and every
≥ 3 dB line for V294 and all 11 references) are in `bands/spectra_by_band_out.txt`. The excess-dB curves are in
`bands/_scratch/spectra_curves.npz`.

### 2.3 The 18–22 Hz ring — drive-controlled measure and presence (P3) → **no surprise**

EVIDENCE: the scorer, section 2.

| | V294 | V293 family (r70 / r71o / r72 / r73 / r75 / r76) | V282 (r6c / r39 / r35) |
|---|---|---|---|
| 18–22 Hz engaged ÷ disengaged | **1.226** (×0.36 of r6c) | 1.88 / 1.00 / 3.23 / 1.45 / 0.81 / 1.90 | 3.40 / 3.92 / 3.62 |
| presence, % of 2 s windows | **0.5 %** (8 of 1580) | 1.1 / 0.1 / 0.65 / 3.1 / 0.44 / 0.96 | 9.8 / 20.9 / 16.2 |
| present-window amplitude p50 | 1.08 deg/s = ×0.41 of r6c | 0.85–7.44 | 2.63–3.49 |
| f0 of present windows | 16.8 Hz | 17.9–24.9 | 20.0–20.1 |

- The ×0.41 is **not decisive**: 8 windows, and the scorer says so.
- The scorer prints the V293 "terminal null sentence" mechanically, because the identity holds and the ring amplitude
  did not reach ≤ 0.40 ×. That sentence belongs to the V293 record and is not new here.

### 2.4 13–17 Hz

EVIDENCE, the scorer section 5, hands-off 8–15 m/s:
- **0.383 deg/s = ×0.88 of r6c**. PASS against the ×1.5 gate.
- It is the lowest of the V293 family (0.388–0.925). r76 read ×2.12 and fired REVERT.
- Engaged ÷ disengaged at 13–17 Hz is 1.88 (V293 family 1.12–3.28).

### 2.5 F7 and the tap ripple at |angle| ≥ 30 (P7) → **PASS**

EVIDENCE: the scorer, section 3, 84 s at high angle.

| | V294 | V293 family | V282 / V281r3 |
|---|---|---|---|
| F7 per 100 s | **0.00** | 0.00 on all six | r39 1.03 (record), r6c 1.03 (scorer), r35 0.00 |
| rip/L p50 | **0.004** | 0.004–0.017 | 0.104–0.166 |
| absolute 6–8.5 Hz tap ripple | **2.9 counts** | 3.6–17.7 | 73–119 |
| 5–9 Hz rate at \|ang\| ≥ 30, hands-off | 1.59 deg/s | r70 1.42, r71o 2.31, r75 1.44 | r6c 1.02, r39 1.00 |

### 2.6 P4 — the 2.34 Hz limit cycle on sustained curves ≥ 19 m/s → **did not fire**

EVIDENCE: v293r2_read S7, copied verbatim. Hard curves have \|Ddes\| > 1.0 and runs ≥ 5 s.

| route | stratum | runs, s | rate peak | cmd peak | err peak | angle peak | rate rms 0.5–3 Hz |
|---|---|---|---|---|---|---|---|
| **V294** | v > 15 | 3, 29 | **1.95 Hz +10.3 dB** | 0.39 Hz +3.4 | 0.39 +3.5 | 0.39 +4.0 | 7.6 deg/s |
| **V294** | **v ≥ 19** | 1, 14 | 1.76 Hz +1.8 | 0.39 +2.5 | 0.39 +1.8 | 0.39 −3.4 | 2.7 |
| r75 | v > 15 | 2, 18 | 1.37 +16.2 | 0.39 +3.1 | … | … | 14.5 |
| r71-old | v > 15 / ≥ 19 | 2, 21 | **2.34 +22.5** | **2.34 +18.1** | **2.34 +23.0** | **2.34 +20.5** | 27.0 |
| r76 | – | no runs | NOT TESTABLE | | | | |

- Near-miss: the v > 15 rate peak (1.95 Hz, +10.3 dB) sits 0.05 Hz below the rule's 2.0–2.7 Hz window.
- It is **rate-only**. The command, error and angle do not share it, and in the matched 15–22 m/s hard-turn cell
  command → rate coherence is 0.58.
- Route 71-old's cycle was in all four channels at +18–23 dB with 3.6 × the rate rms.
- BELIEF: this is the lightly damped wheel mode ringing in hard curves, not an outer-loop limit cycle.
- Exposure is 29 s at > 15 m/s and **14 s at ≥ 19 m/s**. This is thin.

### 2.7 1–4 Hz prominence in command AND angle (P5, the V276 signature)

EVIDENCE: the scorer's shoulder-fitted `prominence_1_4`. The angle row is the scorer's own; the command row is the
same function with the command passed in.

| route | 0–5: angle / cmd | 5–10: angle / cmd | 10–20: angle / cmd | > 20: angle / cmd |
|---|---|---|---|---|
| **V294** | **+2.22** / −4.82 | **+1.04** / +0.04 | **+2.87** / **+3.03** @ 1.37 Hz | **−1.40** / −1.98 |
| r70 | +6.51 / +5.71 | +11.78 / +8.11 | +7.65 / +6.42 | +3.08 / −0.40 |
| r71-old | +3.87 / +1.67 | +1.71 / +4.96 | +9.61 / +5.84 | +22.24 / +15.05 |
| r73 | +6.20 / +13.66 | +19.38 / +17.48 | +22.83 / +16.59 | +5.60 / +2.53 |
| r75 | +5.08 / −0.91 | +7.52 / +7.80 | +3.85 / −1.71 | +0.26 / −0.71 |
| r76 | +3.18 / +2.23 | +2.41 / +0.36 | −0.79 / −2.00 | +0.55 / +0.26 |
| r6c / r39 / r35 | +2.19 / +1.08 / +1.91 (cmd up to +3.53) | ≤ +0.61 | ≤ +1.69 | ≤ +2.21 |

- **The pre-registered clause (angle < 3 dB in every band) PASSES.** It is the first V293-class flight to pass it in
  all four bands.
- The command reads +3.03 dB at 10–20 m/s, 0.03 dB over the threshold, where the angle is 2.87. The V276 signature
  needs both, so it is **not present**. If "either" were the rule, the command would fire marginally. That clause is
  uncalibrated: r39's command reaches +3.53.
- **The scorer's section-4 outer-loop REVERT fired anyway.** It uses the 1–4 Hz angle **amplitude** against V282,
  where the pre-registered clause is prominence:
  - V294 at 5–10 m/s: 0.912 deg vs r6c 0.230. The trigger is > 1.5 × every V282 reference.
  - It has fired on every V293-class flight: r70 at 0–5 m/s 3.55 deg; r71-old 0.78; r72 1.34; r73 6.09; r75 0.56;
    r76 1.77.
  - It does not discriminate this build from its V293 references.
  - 1–4 Hz rate content: 16.9 / 9.7 / 4.9 / 1.6 deg/s by band. That is the lowest or second-lowest of the V293 family
    in every band, and still 2–4 × r6c. It is a target-only clause.

### 2.8 Dwell-then-jump ratchet statistics (P6) vs route 70 and V282

EVIDENCE: the scorer section 7.1. Its positive control reproduces r70 on all 11 instruments.

| | 0–5 | 5–10 | 10–20 | > 20 m/s |
|---|---|---|---|---|
| dwells/min, th 0.25, **V294** | **18.60** | **7.96** | **8.30** | **5.66** |
| r70 (rev 1) | 15.23 | 7.66 | 4.56 | 1.24 |
| r71-old / r73 / r75 / r76 | 10.5 / 0.0 / 13.0 / 21.0 | 5.8 / 1.9 / 10.6 / 2.8 | 9.1 / 5.8 / 8.5 / 4.9 | 4.3 / 2.4 / 3.8 / 4.7 |
| r6c / r39 / r35 (V282) | 0.39 / 0.38 / 0.51 | 0.64 / 0.00 / 0.00 | 0.44 / 0.84 / 0.88 | 0.20 / 0.00 / 0.51 |
| dwell p90, s (th 0.5): V294 / r70 / r6c | 1.15 / 0.92 / 0.38 | 1.06 / 1.09 / 0.51 | 1.14 / 0.91 / 0.63 | 0.80 / 0.78 / 0.61 |
| snap p90, deg: V294 / r70 / r6c | 2.95 / 7.00 / 5.04 | 6.80 / 1.70 / 2.20 | 3.70 / 5.84 / 2.78 | 1.60 / 4.00 / 1.40 |
| rate concentration q75–90 (gate ≤ 0.40) | V294 **0.482**; V293 0.438–0.562; V282 0.325–0.351 | | | |

- **FAIL** on "≤ 3 × r6c" in all 4 bands, as on every V293 flight.
- **The ratchet REVERT (above r70 in ≥ 2 bands) fired, in 4 bands.** It also fired on r71-old, r72, r73, r75 and r76.
  r70 is the lowest V293 flight, so the trigger does not discriminate V294 from the V293 family.
- The \> 20 m/s band (5.66) is above every V293 flight (max 4.70).
- The snaps that follow the dwells are small: 1.6–6.8 deg p90.
- N2 stiction/breakaway (v293r5_read): 0.2 events/min at 8–15 m/s. r75 and r76 read 0.

### 2.9 What the fork side contributes

The fork is generic, with the friction relay live. EVIDENCE, from the scorer's own branch rows:
- The else-arm f identity does not close exactly: slope 1.057, R² 0.978, against r70's 1.000 / 0.99998. The extract
  agent measured the SteerFriction relay live in `f` (0.011 × LAF 14 = 0.154 m/s², 45 CAN counts), which is
  consistent.
- The effective latAccelOffset is −0.157 m/s² (KeepLearnedLatAccelOffset = 1).
- Roll is +1.77°, and the roll term subtracts a median 0.30 m/s² from the feedforward.

---

## 3. Section (2): the outer loop

Hands-off throughout. N6 and S2 are the record's rev-4/5 readers; O2 and O3 are the rev-5 observer read. EVIDENCE for
every row.

| band (m/s) | tracking gain act/plan (S2 · N6 · scorer 7.3) | \|H\|(0.2 Hz) (N6) | lag des→act, s (N6) | planner-error energy share < 0.3 / 0.3–1 / 1–3 Hz (S2) |
|---|---|---|---|---|
| < 8 | 0.836 · 0.63 (13 s) · 0.817 | 0.66 | 0.07 | 85 / 9 / 2 % |
| 8–15 | **0.800 · 0.79 · 0.804** | 0.83 | 0.00 | 79 / 14 / 4 % |
| 15–22 | **0.831 · 0.81 · 0.825** | 0.79 | 0.36 | 86 / 7 / 4 % |
| > 22 | 0.934 · 0.85 · 0.925 | 0.81 | 0.00 | 79 / 11 / 5 % |
| r75, same order (gain column = S2; scorer 7.3 reads 0.90 / 0.97 / 0.99 / 0.98) | 0.98 / 0.97 / 0.98 / 0.97 | 0.75 / 0.88 / 0.93 / 0.96 | 0.47 / 0.29 / 0.09 / 0.45 | 49/34/4 · 66/23/3 · 62/18/9 · 69/17/2 |
| r76 (gain = S2; scorer 7.3 reads 0.98 / 1.03 / 1.04 / 0.96) | 0.97 / 0.93 / 0.90 / 0.81 | – / 1.08 / 1.28 / 1.04 | – / 0.32 / 0.57 / 0.50 | 88/8/1 · 91/5/2 · 71/17/3 · 63/18/2 |
| r6c (V282), scorer 7.3 | 0.966 / 0.968 / 0.996 / 0.989 | – | – | – |

**Planner-error rms by band** (O2, m/s², 0.05–0.3 / 0.3–1 / 1–3 Hz):

| band m/s | V294 | r75 | r76 |
|---|---|---|---|
| 8–15 | **0.163** / 0.051 / 0.034 | 0.048 / 0.040 / 0.019 | 0.075 / 0.030 / 0.022 |
| 15–22 | **0.134** / 0.037 / 0.036 | 0.064 / 0.056 / 0.062 | 0.084 / 0.037 / 0.020 |
| 22–31 | **0.094** / 0.033 / 0.025 | 0.067 / 0.030 / 0.023 | 0.088 / 0.046 / 0.031 |

V294's < 0.3 Hz planner error is ×1.4–3.4 of r75's. That is the under-delivery. Above 0.3 Hz it is equal or lower.

**Turn hold** (S2, act/plan at \|plan\| 0.8–1.5 / > 1.5):

| band m/s | V294 | r75 |
|---|---|---|
| 1–8 | 0.81 / 0.86 | 1.06 / 0.94 |
| 8–15 | **0.69** / 0.84 | 1.01 / 0.93 |
| 15–22 | **0.67** / 0.88 | 1.00 / 0.97 |
| > 22 | 0.94 / 0.96 | 0.99 / – |

The scorer's 7.3 turn-hold at 10–20 m/s reads 0.754 (r70 0.937, r75 0.984, r6c 1.004).

**Delivery by regime** (scorer 7.5, mean\|act\| / mean\|des\|):

| regime | V294 | V293 family | r6c |
|---|---|---|---|
| straight | **57.6 %** | 69.5–102.6 % | 86 % |
| entry | 73.4 % | | |
| hold | 82.5 % | | |
| exit | 92.3 % | | |
| low-speed manoeuvre | 85.5 % | | |

**Straights** (v293r3 S8, hands-off, \|planner\| < 0.4):

| band m/s | V294 wander | r75 wander | r76 wander | V294 loop stiffness | r75 loop stiffness |
|---|---|---|---|---|---|
| 8–15 | **1.25** | 2.45 | – | 0.0093 | 0.0183 |
| 15–22 | **0.44** | 1.30 | 1.50 | 0.0226 | 0.0185 |
| > 22 | **0.45** | 0.97 | 0.96 | 0.0337 | 0.0049 |

- Angle wander is 0.05–0.5 Hz rms in deg; loop stiffness is in torque per deg.
- The wheel wanders **less** on straights. The **delivered lateral accel is lower**.
- The scorer's 7.2 low-speed stiffness at 0–5 m/s is 0.0040 (r75 0.014, r76 0.012).
- BELIEF: "loose on straights" is under-delivery, not wander. The same reading the kit made on r70.

**Integrator share of \|f\|+\|p\|+\|i\|**:

| source | band grid | V294 | r75 | r76 | r6c |
|---|---|---|---|---|---|
| scorer 7.5 | < 8 / 8–15 / 15–22 / > 22 | 0.389 / 0.348 / 0.413 / 0.253 | 0.338 / 0.289 / 0.290 / 0.335 | 0.167 / 0.113 / 0.076 / 0.082 | 0.30–0.40 |
| S5 | 1–8 / 8–15 / 15–22 / > 22 | 0.353 / 0.343 / 0.411 / 0.251 | | | |

Target < 0.20; no route passes.

**Saturation share** (engaged + torqueState.active):
- torqueState.saturated: 0.00 % in every band (0.01 % at 10–15).
- \|cmd\| ≥ 4096 on 1.66 % of 0–5 m/s frames. Every one is driver-pressed (extract agent). r75 reads 1.90 %.
- \|op torque\| ≥ 0.95 on 0.00 % above 5 m/s.

**des → act |H| at 2 Hz** (coherence in brackets):

| estimator | band | V294 | r75 | r76 |
|---|---|---|---|---|
| S2 | 1–8 | 0.41 (0.61) | 1.53 (0.75) | 1.12 (0.92) |
| S2 | 8–15 | 0.91 (0.64) | 1.07 (0.86) | 0.75 (0.14) |
| S2 | 15–22 | 1.41 (0.42) | 1.50 (0.30) | 0.94 (0.41) |
| S2 | > 22 | 0.64 (0.80) | 0.71 (0.42) | 1.07 (0.51) |
| O3 | 8–15 | 0.95 (0.84) | | |
| O3 | 15–22 | 2.10 (0.32) | | |
| O3 | 22–31 | 0.58 (0.32) | | |
| N1, IV closed loop, 15–30 m/s | | 1.20 | 1.06 | 0.98 |

- Coherence is low at 15–22 m/s, so those rows are weak.
- The rev-4 handoff's "2.28 at 2 Hz, coherence 0.99 at 10–20 m/s" came from a design-stream estimator I did not
  locate. It is not comparable to these rows.

**J, the goal metric** (0.15–2.4 Hz, one denominator, ≥ 15 m/s, lateral-engaged hands-off runs ≥ 30 s,
unsaturated). **The exposure QUALIFIES**: 18 windows, 115 s, 3 runs ≥ 30 s. My pre-written gate was ≥ 5 windows; the
record's smallest route had 17.

| route | J | 95 % block CI (blocks of 3 windows) | sub-bands 0.15–0.3 / 0.3–0.6 / 0.6–1.2 / 1.2–2.4 | \|H\| at 0.15–0.3 Hz |
|---|---|---|---|---|
| **V294** | **0.417** | **[0.314, 0.758]** | 0.170 / 0.058 / 0.075 / 0.115 | **0.778 @ −16°** |
| r75 (rev 4) | 1.015 | [0.878, 1.312] | 0.731 / 0.152 / 0.038 / 0.094 | 0.995 @ −48° |
| r76 (rev 5) | 1.178 | [1.008, 1.476] | 0.980 / 0.104 / 0.036 / 0.058 | 1.033 @ −57° |
| r64 (V282) | 0.465 | [0.308, 0.878] | 0.119 / 0.069 / 0.123 / 0.154 | 0.892 @ −18° |
| rev 6.4 as flown (record) | 1.351 | – | – | – |
| V282 (brief / pooled record) | 0.442 / 0.471 | – | – | – |

- EVIDENCE, method 1: the record's f1/f2 code reproduces f2_metric.json to 1e-3 on r64, r75 and r76 (positive
  control PASS).
- EVIDENCE, method 2: an independent implementation, with the raw gyro × v as the achieved accel, reads V294 0.350 /
  r75 0.874 / r76 1.044. My own livePose version reads 0.450 / 1.068 / 1.273. The **ratio to rev 4 is 0.40–0.42 in
  all three**.
- The worst single window carries 18 % of V294's error; leave-one-block-out spans [0.371, 0.489].
- **What it says:**
  - The low-frequency error is small because the achieved accel arrives **on time**: −16° at 0.15–0.3 Hz against
    −48 / −57° on rev 4/5.
  - Under-delivery (|H| 0.78) is the dominant residual at 0.15–0.3 Hz. The record's 09-20 finding was "the gap is
    timing, not gain"; on V294 the remaining gap is gain.
- **What it does not say:** J is ≥ 15 m/s only. It cannot see the low-speed complaints, and it does not attribute the
  change to firmware vs fork. Both the firmware (V294) and the fork (generic torque path, r1 config) changed at once.

---

## 4. Section (3): the 0x14A byte-4 cave duties (the r24 control)

EVIDENCE. Method 1 is the scorer section 6 (kit v280 cache). Method 2 is the extract loader (0xE4 req on bus 129 and
SCA, ZOH onto the 0x14A clock). They are identical to 3 decimals.

| engaged duty | b7 | b6 | b5 | **b4 (neg. control)** | b3 | b2–b0 |
|---|---|---|---|---|---|---|
| **V294** (80,071 frames) | 0.481 | 0.043 | 0.037 | **0.347** | 0.461 | 1.000 |
| V293 family (r70 … r76) | 0.428–0.579 | 0.035–0.075 | 0.035–0.076 | **0.351–0.399** | 0.460–0.468 | 1.000 |
| V282 / V292 (r6c, r39, r35, r6d–f) | 0.49–0.59 | 0.00–0.22 | 0.13–0.25 | 0.389–0.441 | 0.42–0.48 | 1.000 |

- **P8 does not fire.** b4 = sign(r24) sits 0.004 below the V293 minimum; my surprise threshold was 0.05. The r24 arm
  (2048) is unchanged V293 → V294, and the control behaves.
- b5 and b6 are unchanged from V293. They are not pre-registered.
- b7 (the sign of the LKAS summand, which now includes the trim) is inside the V293 range.
- SCA = 0: b4 0.151 (V293 0.124–0.363).

---

## 5. Section (4): one-table summary

| metric | V294 r71b | V293 refs | V282 refs | pre-registered expectation | pass / fired |
|---|---|---|---|---|---|
| FF identity, tap vs V293 surface | R² 0.987, resid 22.4 | 0.94–1.00, resid 11.6–65 (best lag) | V282 cells on V294 −1.02 | R² ≥ 0.50, resid ≤ 2.5 × PC | **PASS** (attribution) |
| trim live (extract agent, E3) | +0.197 (6/6 > 0.10) | null +0.000 / +0.003 | – | β > +0.10 = LIVE | **LIVE** |
| **P1** 1.6–3 Hz wheel rate, hands-off, 0–5 / 5–10 / 10–15 / 15–22 / 22+ (deg/s) | 1.25 / 1.68 / 0.72 / 0.83 / 0.95 | r75 1.49 / 2.14 / 1.59 / 1.59 / 1.00; r76 1.22 / 3.19 / 1.70 / 1.37 / 0.98 | r6c 0.79 / 0.48 / 0.35 / 0.28 / 0.27 | DOWN vs r75 / r76 | **held** at ≥ 5 m/s; 0–5 mixed |
| **P1** matched hard-turn cells | ×0.56–0.91 of r75 / r76 | family 9.6–56.7 deg/s | – | DOWN | **held** (every cell) |
| **P1** O4 hard turns v < 10, 1.6–3 Hz share | 6 %, 63 reversals /min | r75 19 % / 77; r76 18 % / 88; r70 26 %; r71o 17 %; r72 9 % | – | ≤ r75 + 10 pts | **held** |
| **P2** new line 5–30 Hz | **15.6 Hz tap +6.1 dB**, engaged 0–5 m/s, one hands-on episode at 41–47 s; command not coherent | hands-on low-speed lines 19.5 / 22.3 / 20.7 Hz | – | none | **FIRED** (localised, §2.2) |
| highway 13.3 Hz line | wheel-rotation order | same on r75 | same on r6c | – | REPORT (not the loop) |
| **P3** 18–22 Hz engaged ÷ disengaged | 1.226 | 0.81–3.23 | 3.40–3.92 | V293-like | no surprise |
| ring presence / amplitude | 0.5 % / ×0.41 r6c (8 windows) | 0.1–3.1 % | 9.8–20.9 % | ≤ 0.40 × V282 amplitude | not decisive (8 windows) |
| 13–17 Hz, hands-off 8–15 | 0.383 deg/s = ×0.88 r6c | 0.388–0.925 (r76 ×2.12 REVERT) | 0.437–0.532 | < 1.5 × V282 | **PASS** |
| **P7** F7 per 100 s | 0.00 | 0.00 | 0–1.03 | < 2 | **PASS** |
| rip/L p50 / absolute ripple | 0.004 / 2.9 counts | 0.004–0.017 / 3.6–17.7 | 0.10–0.17 / 73–119 | < 0.25 / < 1.5 × r6c | **PASS** |
| **P4** 2.34 Hz limit cycle ≥ 19 m/s | 1.76 Hz +1.8 dB (14 s); at > 15, rate-only 1.95 Hz +10.3 dB | r71-old 2.34 Hz +22.5 dB in all four channels | – | absent if the trim is live | **not fired** (rate-only near-miss) |
| **P5** 1–4 Hz prominence, angle | 2.22 / 1.04 / 2.87 / −1.40 dB | r75 5.1 / 7.5 / 3.9 / 0.3; r76 3.2 / 2.4 / −0.8 / 0.6 | −2.3 … +2.2 | < 3 dB everywhere | **PASS** (first V293-class) |
| 1–4 Hz prominence, command (same estimator) | −4.8 / +0.0 / **+3.03** / −2.0 | up to +17.5 | up to +3.53 | (not pre-registered) | marginal at 10–20; uncalibrated |
| scorer outer-loop row (1–4 Hz angle amplitude) | 0.91 deg at 5–10 | fired on all 6 | 0.23–0.30 | < 1.5 × V282 | **REVERT fired**, as on every V293 flight |
| **P6** dwells /min th 0.25 | 18.6 / 8.0 / 8.3 / 5.7 | r70 15.2 / 7.7 / 4.6 / 1.2; r75 13.0 / 10.6 / 8.5 / 3.8; r76 21.0 / 2.8 / 4.9 / 4.7 | 0.0–0.9 | ≤ 3 × r6c; REVERT if > r70 in ≥ 2 bands | **FAIL; ratchet REVERT fired** (as on r71o, r72, r73, r75, r76) |
| dwell p90 / snap p90 | 0.8–1.15 s / 1.6–6.8° | r70 0.78–1.09 s / 1.7–7.0° | 0.38–0.63 s / 1.4–5.0° | – | REPORT |
| rate concentration q75–90 | 0.482 | 0.438–0.562 | 0.325–0.351 | ≤ 0.40 | FAIL (as V293) |
| tracking gain < 8 / 8–15 / 15–22 / > 22 | 0.82 / **0.80 / 0.83** / 0.93 | r75 0.90 / 0.97 / 0.99 / 0.98; r76 0.98 / 1.03 / 1.04 / 0.96 | r6c 0.97 / 0.97 / 1.00 / 0.99 | 0.95–1.05 | **FAIL** (under-delivery) |
| \|H\|(0.2 Hz) | 0.66 / 0.83 / 0.79 / 0.81 | r75 0.75 / 0.88 / 0.93 / 0.96 | – | ≥ 0.9 (rev-4 sentence) | FAIL |
| lag des → act | 0.07 / 0.00 / 0.36 / 0.00 s | r75 0.09–0.47; r76 0.32–0.57 | – | ≤ 0.3 s (rev-4) | within, except 15–22 (0.36) |
| turn-hold act/plan (\|D\| 0.8–1.5) | 0.81 / **0.69 / 0.67** / 0.94 | r75 1.06 / 1.01 / 1.00 / 0.99 | r6c ≈ 1.00 | (> 20 m/s ≤ 1.04) | under-delivery |
| planner-error rms 0.05–0.3 Hz, 8–15 / 15–22 / 22+ | 0.163 / 0.134 / 0.094 | r75 0.048 / 0.064 / 0.067 | – | – | REPORT (×1.4–3.4 of r75) |
| integrator share | 0.39 / 0.35 / 0.41 / 0.25 | r75 0.29–0.34; r76 0.08–0.17 | 0.30–0.40 | < 0.20 (target) | FAIL (target-only) |
| saturation share | 0.00 % (\|cmd\| ≥ 4096 1.66 % at 0–5, all driver-pressed) | r75 1.90 % at 0–5 | – | – | REPORT |
| straight delivery | 57.6 % | 69.5–102.6 % | 86 % | 90–110 % (target) | FAIL (lowest in corpus) |
| **J** (≥ 15 m/s) | **0.417 [0.314, 0.758]** | r75 1.015; r76 1.178; rev 6.4 1.351 | 0.442 / 0.465 / 0.471 | none pre-registered | REPORT: below rev 4/5 (CIs disjoint), ≈ V282 |
| des → act \|H\| at 2 Hz (S2) | 0.41 / 0.91 / 1.41 / 0.64 | r75 1.53 / 1.07 / 1.50 / 0.71 | – | – | REPORT (coherence 0.4–0.8) |
| **P8** cave b4 (neg. control) | 0.347 (two methods) | 0.351–0.399 | 0.389–0.441 | unchanged | **PASS** |
| faults (extract agent) | none | – | – | none | PASS |

---

## 6. Questions for the operator

These are the questions the bands raise. His recorded words are in OPERATOR-REPORT-r71b.md; I have not verified them.

1. **The one new line (P2).** About 40 s into the drive (≈ 20:10:48–20:10:53 PDT, clock BELIEF ±1 s), you were
   crawling (0–2 m/s) with the wheel near full lock (up to ~370°) and your hands on it hard. The wheel, the torque
   sensor and the EPS torque all carried a 15.6 Hz vibration. Did you feel a buzz or a grind in the rim then? You
   said "no grinding" overall; was that moment different?
2. **"Jerky on hard turns at medium speed."** What speed do you mean? Which of these was it:
   - **20:16:52.8** — ~23 mph, 100° of wheel. The largest 2 Hz wheel motion of the drive.
   - **20:19:11** — ~43 mph, a hard curve. The car held only 77 % of the planner's lateral accel.
   - **20:12:20 / 20:13:25** — ~21–24 mph, ~97°.

   Was it one jolt at turn-in, a catch-up partway through the turn, or a shake of about 2 per second?
3. **"Loose" at low speed and in highway turns.** Did the car not turn enough (understeer), or did the wheel feel free
   and wandering? On the wire:
   - At 8–22 m/s the car delivered **67–83 %** of the planner's lateral accel in turns.
   - On straights it delivered 58 %.
   - Straight-line wander was **lower** than on rev 4/5.
4. **Better or worse than V293 rev 4 / rev 5** on the specific hard-turn jerk? The pre-registered band, 2 Hz wheel
   energy in hard turns, moved down ×0.56–0.91.
5. **Ratchet / sit-still-then-jump** (his word from route 70). Did you feel it on this drive? Above 45 mph the dwell
   count is the highest of any V293-class drive (5.7 /min), but the snaps are small (≤ 2° p90 above 20 m/s).
6. **Engage moments.** Did you feel a brief brake or tug on the wheel right as lateral control engaged? The design
   predicts an 80–400 ms braking pulse at each filter restart. It was not measured here.
7. Was the drive mostly hands-off, as the wire says (steeringPressed 6.6 % of engaged time)?

---

## 7. Surprises, defects, and what was not done

- **DEFECT in the kit scorer (reported, NOT fixed).** `v293_flight_read.print_scorecard` reads an undefined name `g`
  in the rev-5 observer block (lines ~1876–1884, added in commit 2ef033a on 2026-09-15).
  - Every run since that commit dies with `NameError` after all scoring and before anything is printed or saved. Both
    r71b and r76 crashed.
  - I worked around it in `bands/run_flight_read.py` by defining the module global `g = {}`. That skips only the
    observer print line; no verdict depends on it.
  - The `r75_v293r4` scorecard on disk predates the edit.
- **The scorer's two REVERT triggers do not discriminate this build.** "Outer loop" (1–4 Hz angle amplitude > 1.5 ×
  V282) has fired on all six V293-class flights. "Ratchet" (> r70 in ≥ 2 bands) has fired on every flight after r70.
  - Both are calibrated against the lowest reference.
  - This is not a verdict on V294. It says those two gates are aspirational on the torque-map class, and the
    orchestrator should not relay them as "revert V294" without that context.
- **P2's rule has no hands-on exclusion.** It fired on a parking-speed hands-on episode that the V293 routes also show
  in their own frequencies.
- **The V294 tap carries more 1.6–3 Hz torque at 22+ m/s hands-off** (4.45 counts vs r75 2.63, r76 2.34), while the
  wheel carries less. BELIEF: this is the trim working, opposing wheel acceleration. It is consistent with the extract
  agent's live-trim reading.
- **The rate-only 1.95 Hz, +10.3 dB line on hard curves at > 15 m/s**, 0.05 Hz outside P4's window. BELIEF: the
  wheel mode, not the outer loop. It is thin (29 s).
- **Exposure is thin where the complaints live.**
  - 14 s of hands-off hard turns at 15–22 m/s.
  - 3–5 s at 10–15 m/s with \|D\| ≥ 1.5.
  - 14 s of hard curves at ≥ 19 m/s.
  - r76 has almost no hard-turn exposure: 1 medium-speed event.
- **Not done:**
  - A V282 row for the ident-cache readers (S2/N6/O-reads). No V282 ident caches exist; V282 is covered by the
    scorer's own references.
  - Locating the estimator behind the rev-4 handoff's "|H| 2.28 at 2 Hz".
  - Attributing the outer-loop under-delivery to firmware vs fork. Both changed at once. The FF identity says the
    firmware surface is V293's exactly, so the under-delivery is the r1 fork law on this surface: BELIEF, pending a
    replay.
- **Caches created** (gitignored, regenerable):
  - `analysis-2020accord/_scratch/cache/tau/{r71b_v294,r76_v293r5}_ident{.npz,_meta.json}`
  - `analysis-2020accord/_scratch/cache/v280/r76_v293r5*`
  - `analysis-2020accord/_scratch/cache/v282ref/00000071--a7b8ba5d9d.npz`
  - `rlog-tools/studies/grind/_scratch/cs_r76_v293r5.npz`
  - `rlog-tools/studies/grind/_scratch/v293_flight_read_{r71b_v294,r76_v293r5}.{txt,json}`
  - `rlog-tools/_scratch/cache/75604b0a432fdc89_00000076--d0b7ea7e4d/CACHE-POINTER.json`
  - `analysis-2020accord/studies/v295/flight/bands/_scratch/`
