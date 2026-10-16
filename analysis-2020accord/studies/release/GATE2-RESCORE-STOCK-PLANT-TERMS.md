# GATE 2 re-score — the V299 angle loop on STOCK plant-side firmware terms (release census D3 / D5 / D8)

Study artifact, 2026-10-15, fork `gate2-rescore` for orchestrator `main`. Nothing built, flashed or sent.
Script `analysis-2020accord/studies/release/gate2_rescore_stock_terms.py` (4.8 s wall; writes
`_scratch/out/release/gate2_rescore.{md,json}` and `figures/release/*.png`). **E** = EVIDENCE (method given), **B** = BELIEF.

## 0. Verdict

| release revert (census row) | what changes in the loop | PM bars (45° A / 30° B) | GM ≥ 6 dB | closed-loop peak 5–30 Hz ≤ +3 dB | L20 ≤ V295's | **verdict** |
|---|---|---|---|---|---|---|
| **D3** r24 gate `0x3AA96` + arm `0xC6446` → stock (engaged r24 gain flat 2.00 → Honda's 3.00/2.50/2.25/2.10 at 0/10/50/100 km/h) | a driver-torque-derivative lane on the hands-off twist: pumps at 7 Hz (−0.64 T per deg/s per unit G), damps at 20 Hz (+5.7) | pass, ΔPM −0.7…+0.1° | pass (≥ 20 dB) | pass (max −4.0 dB) | pass (≤ 1.01×) | **REVERT — clean** |
| **D8′ + 0xC40DC** DampAxis lane `gp-0x6b26`: Y `0xD7A5C`/`0xD7A6C` (−29490,−17202,−16000) → stock (−9830,−5734,−1966) and α2 `0xC40DC` 14 → 22 | a lagged **positive-inertia** term on the motor rate: +0.13 T/(deg/s²) at V299, +0.043 stock (3 m/s); damping at 24 Hz 11.9 → 3.6 T per deg/s | pass (PM RISES +0.1…+14°) | **FAIL**: J_lo 3 m/s 20.0 → 5.2 dB (combined) | **FAIL**: J_lo 3 m/s −4.2 → +5.4 dB combined, +3.0 dB DampAxis alone; Ms 1.26 → 2.68 | **FAIL**: nominal 1.18–1.29× V295 at every speed; L13–17 ×1.3–2.2 | **KEEP at V299 values — 13 bytes** (`0xD7A5C` 6 B, `0xD7A6C` 6 B, `0xC40DC` 1 B) |
| **D5** `0xC40BC` relay / `0xC40D2` K1 → stock | inside `FUN_0003b8f6`, the plant-model OBSERVER → `gp-0x6bfc` → plausibility latch `FUN_0003bc20`; writes no motor command (E: TRACE-2026-08-10-lkas-command-visibility §3/§5) | not in the linear loop | — | — | — | **REVERT — not a loop term**; the interlock lens owns the latch threshold with the ×6 lane (stock K1 102 ran under the ×6 lane V38→V88 without a trip, E: record) |
| **D8** r24 rate-axis flatten (Y2/Y3 → plateau), damper/boost families → stock | zero below ~85 deg/s in BOTH images (plateau Y0 = Y1; the stock damper dead zone) | no small-signal term | — | — | — | **REVERT**; large-signal note §4 |

**Bottom line:** the full plant-side revert **does not pass GATE 2 as the design defined it** — the DampAxis lane is part of
the plant C3-rev2-P was scored on, and taking it back to Honda's values raises the 13–20 Hz loop gain 1.2–2.2× and puts a
+3…+5 dB closed-loop peak at 13–17 Hz on the light-inertia corner at creep. Keeping its 13 bytes at V299 values, and
reverting everything else in D3/D5/D8, passes every gate with margin to spare (the "only r24" columns). The minimal fix is
those 13 bytes; no tuning change is needed.

## 1. How the three terms enter the loop (E unless marked)

Decompiles read this session on the open stock program (`FUN_0003aa2c` r24/r26 + sum; the record's fresh decompiles of
`FUN_00041464` → `FUN_00036c12` and `FUN_0003b8f6` re-read from the traces); every cal byte re-read LE from both images.

| lane | formula (integer, addresses in the traces) | stock | V299 | linear model used |
|---|---|---|---|---|
| r24 (`st.h r24,-0x6ada[gp]` @0x3AD5A) | `pol · deadband(G · gp-0x4f62, 3)`, `gp-0x4f62 = 0.5·(T_raw[n] − T_raw[n−4])` (N = `0xC6C42` = 4), G = 4-way mux → mode-26 speed LERP (plateau Y0, flat to 85 deg/s) | G(v) = 3.00/2.50/2.25/2.10 (0/10/50/100 km/h, `0xC6010` axis) | G = 2048/1024 = 2.00 flat while `gp-0x6806` ≠ 0 (gate repoint `0x3AA96` C5→FB, arm `0xC6446` 512→2048) | `ΔF = σ_r·ΔG·0.5·(1 − z⁻⁴)·H_tb(f)`, deadband off |
| DampAxis `gp-0x6b26` | `x = gp-0x4f50` (motor rate) → `y0 += ((1024x − y0)·37)>>7` → `d = Δy0` → `d32 = 32d` → `yA += ((d32 − yA)·K2)>>6` → `g = yA>>9` (`FUN_00041464`); `lane = clamp(((g·Y(v))>>6)·0x111>>18, ±511)` (`FUN_00036c12`); summed into `gp-0x6b94` without pol | Y(v) = −9830/−5734/−1966 at 0/20/90 km/h (`0xD7A54` record, X = 0,1280,5760), K2 = 22 | Y = −29490/−17202/−16000, K2 = 14 | exact z-domain chain (checked against the record's time-domain gains 3.08× @7.8 Hz, 7.54× @21 Hz: mine 2.98 / 7.2), clamp off, `x = 1.155·4.7121·θ̇` (B: motor-frame counts per deg/s of `gp-0x6a00`) |
| Coulomb relay / K1 | `friction = EMA(|model|·clamp(r/0xC40BC, ±1)·K1/1024)`, `gp_0x6bfc = K·(model − friction − inertia)` in `FUN_0003b8f6` | 600 / 102 | 1800 / 612 | **excluded** — observer output, no command written (E, trace §3/§5) |

**The identified plant already contains the V299-level lanes.** `v294_plant.family()` is an output-error fit on route
r71b (V294 image, which carries the gate repoint, r24 2048, the V105/V106 DampAxis Y and `0xC40DC` 14 — census "introduced"
column, E). So the release plant is `P′ = P/(1 − P·ΔF)` with `ΔF = F_stock − F_V299` per lane.

**Sign anchors (B, anchored to on-car EVIDENCE in the record).** The decompile fixes each lane's arithmetic but not the
sign convention of the summed torque against the loop's `u`, so each lane's overall sign is set to reproduce a measured
fact: r24 **pumps at 7 Hz** (the V281-era cave sign bit); the DampAxis ×3 of V106 **extinguished the 21–27 Hz mode**
(route a6, 18–30 Hz band power 0.347×). Cross-check that both anchors are consistent with the model and with each other:
with σ_r fixed at 7 Hz, the same model gives r24 **damping at 20 Hz** (+5.7 T per deg/s per unit G) — the record's second
observation, reproduced without being fitted (E for the phase flip, from the measured H_tb). With σ_d fixed at 24 Hz the
lane reads as a positive inertia (+0.043 stock / +0.129 V299 T per deg/s² at 3 m/s) whose two EMA lags supply the HF
damping — a lagged +J term is damping, self-consistent. The three other sign combinations are tabled in §3 so the verdict's
dependence on the anchors is visible.

**H_tb(f) = hands-off torsion-bar twist per degree of wheel angle (E, measured).** Route 79 (V298 flight), 100 Hz wire
(0x18F torque sensor ÷ 1.024 → raw counts, 0x14 angle), 22 engaged hands-off windows ≥ 6 s (251 s), Welch CSD. Two-mass
fit for extrapolation: rim inertia 0.144 raw counts per deg/s², torsion mode **f2 = 16.5 Hz**, ζ 0.2 (B above the coherent
band). Figure `htb_r79.png`. (f2 ≈ 16.5 Hz is the 15–17 Hz pole the V289 flight exposed — B that it is the same object.)

## 2. GATE 2 at θ = 0, the design's box (E for the arithmetic; the plant family is the record's)

Controller = the V299 image's cells (Kp 112, Ki 40, Kd 48 fresh motor-frame D, a 0 / b 8192 sum, GB-P table read from
the cave at `0xC4CDA`: G = 1178/1465/760/560/1068/2188 at 714…6198 speed counts), hold ages 1–10, output lag 992/507,
FWD 5346/32768, fade 254/256. Members: nominal, J_lo 0.1, J_hi 0.5, J_hi2 0.8, b_lo, b_hi, tau0, tau6, ms_free; speeds
3/5/8/12.5/19/26/30 m/s. `V299plant` = the identified plant as is; `stock terms` = D3 + DampAxis reverted; `only r24` /
`only DampAxis` isolate each. Full table in `_scratch/out/release/gate2_rescore.md`; the worst rows:

| v | member | PM V299 → stock terms | PM only r24 / only DampAxis | GM↑ dB V299 → stock | L20 V299 → stock | L13–17 | T5–30 dB V299 → stock | Ms |
|---|---|---|---|---|---|---|---|---|
| 3 | nominal | 88.0 → 96.6 | 87.8 / 97.1 | 22.1 → 14.3 | 0.045 → 0.054 | 0.105 → 0.142 | −5.1 → −3.1 | 1.26 → 1.43 |
| 3 | **J_lo** | 99.2 → 113.0 | 98.9 / 113.7 | **20.0 → 5.2** | 0.087 → 0.132 | 0.190 → 0.408 | **−4.2 → +5.4** | **1.26 → 2.68** |
| 3 | b_lo | 70.8 → 67.4 | 70.1 / 69.5 | 20.4 → 11.8 | 0.046 → 0.054 | 0.107 → 0.141 | −3.2 → −0.1 | 1.36 → 1.66 |
| 5 | J_lo | 99.7 → 110.7 | 99.3 / 111.3 | 20.0 → 9.0 | 0.086 → 0.118 | 0.189 → 0.340 | −4.2 → −0.1 | 1.26 → 1.82 |
| 8 | J_lo | 100.5 → 112.0 | 100.1 / 112.3 | 20.3 → 9.8 | 0.086 → 0.120 | 0.189 → 0.343 | −4.2 → −1.2 | 1.26 → 1.71 |
| 12.5 | J_lo | 91.1 → 91.2 | — | 27.7 → 22.6 | 0.067 → 0.096 | 0.122 → 0.182 | −11.9 → −11.7 | 1.08 → 1.12 |
| 26 | b_lo | 99.8 → 100.9 | — | 28.5 → 24.5 | 0.040 → 0.053 | 0.083 → 0.114 | −11.6 → −11.3 | 1.09 → 1.11 |

Tier summaries (stock terms): A min PM 69.5 → 69.8°, 0 of 42 below 45°; B 64.8 → 67.4°, 0 of 14 below 30°; ms_free
74.9 → 78.6°. **GM < 6 dB: 0 → 1 point (J_lo, 3 m/s). Closed-loop peak 5–30 Hz > +3 dB: 0 → 1 point (J_lo 3 m/s, +5.4 dB
at 13–17 Hz; DampAxis alone +3.0 dB). L20/V295 (nominal) 1.18–1.29× at every speed (gate ≤ 1.00).** With only r24
reverted every gate passes at every point (max T −4.0 dB, L20 ratio ≤ 1.01, PM within 0.7°).

Extra boxes (`extra` in the json): hold ages 11–20, curve operating points k·sech²(θ_op/sat) at 2.5 m/s², ms_free × b_lo —
same picture: PM unchanged or up; the J_lo 3 m/s corner carries the HF peak (+3.3 dB aged, +5.0 dB curve); ms_free rows
stay ≤ −1.7 dB.

**Why PM goes UP while the HF gates FAIL (E, from the model):** the V299 DampAxis lane is +0.13 T/(deg/s²) of effective
inertia with HF damping; reverting it to +0.043 lightens the plant (crossover moves out, more phase) but removes
8.3 T per deg/s of damping at 24 Hz and ~5 at 15 Hz, exactly where the identified two-mass/hold phase stack lives. On the
J_lo corner the lightened plant (0.1 − 0.087 ≈ 0.013 effective) is nearly massless at 13–17 Hz. (B: J_lo = 0.1 is then
hard to reconcile with a +0.13 lane inertia — mechanical J would be negative — so that corner may be unphysical under
this reading; the nominal member alone passes GM 14.3 dB / T −3.1 dB / but still L20 1.24× V295. The gate as written
includes J_lo, and L20 ≤ V295 fails on nominal too, so the verdict stands.)

## 3. Sensitivity to the sign anchors (E for the arithmetic, the anchors are B)

4 members (nominal, J_lo, b_lo, ms_free) × 7 speeds, both terms reverted:

| σ_r | σ_d | anchored | min ΔPM | min PM | max L20 stock/V299 | max T5–30 dB | encirclement | at max T |
|---|---|---|---|---|---|---|---|---|
| −1 | +1 | **yes** | −3.4° | 67.4° | 1.53 | **+5.4** | no | 3 m/s J_lo |
| +1 | +1 | no | −0.1° | 70.6° | 2.02 | +6.9 | **yes** (12.5 m/s b_lo) | 3 m/s J_lo |
| +1 | −1 | no | −9.9° | 65.8° | 0.99 | −5.0 | no | 8 m/s b_lo |
| −1 | −1 | no | −10.3° | 65.0° | 0.98 | −4.7 | no | 8 m/s J_lo |

Under either DampAxis sign the full revert costs something (an HF peak, or −10° of PM at creep); under the anchored sign
(the one consistent with V106's on-car result) it fails the HF gates. **Keeping the DampAxis cells makes the verdict
independent of σ_d** — only σ_r remains, and r24's revert passes under both signs.

## 4. Predicted direction of the stutter readouts and large-signal notes (B)

- r24 → stock: at creep the lane's 7 Hz anti-damping grows by 0.64 T per deg/s (ΔG +1.0), falling to +0.1 at 100 km/h;
  the plant's own b at 3 m/s is an order of magnitude larger (family), and the angle loop's |L| at 7 Hz is ≤ 0.1, so no
  7 Hz cycle is predicted; the stutter readouts (stall-surges, ratchet trains, dwells) are friction/stiction-driven and
  the Coulomb level is untouched by D3 — predicted **unchanged**. F7 (7 Hz) is the readout to watch on the first release drive.
- Dead zone Fc/Kp: Fc is the identified 73–156 T (unchanged by any of these reverts: D5 is observer-side, the DampAxis lane
  is linear in rate, the boost/damper families are dead below 85 deg/s) → **unchanged**.
- Large signal (> 85 deg/s wheel rate, i.e. the fork's 120 deg/s slews): D8's revert restores Honda's r24 roll-off (3.0 →
  1.5 at 637 deg/s) and the stock damper families above their dead zone — both reduce authority against fast motion
  only; the DampAxis clamp ±511 binds at ~190 deg/s (stock Y) vs ~63 deg/s (V299 Y) at 7.8 Hz, so keeping the V299 Y
  keeps the lane saturating earlier on hard slews (as it did on every flight since V106).

## 5. Caveats

1. The plant was identified (r71b, output-error fit) with ALL these lanes active; the "stock plant" here is inferred by
   subtracting mirrored lane transfers, not re-identified. J is identified only at 0–5 m/s (0.1–0.3); the inferred
   mechanical J ≈ 0.07 at that speed (0.2 − 0.13) is B and sits at the edge of the family — a first release drive with the
   DampAxis lane kept changes nothing there; with it reverted, the J corner is the risk.
2. `x = 1.155·4.7121·θ̇` (motor-rate counts per deg/s of `gp-0x6a00`) is the record's scale (E for 4.7121 on `gp-0x6ac0`,
   B for the ×1.155 frame and for `gp-0x4f50` sharing it). The DampAxis magnitude scales linearly with it.
3. Small-signal reading: the DampAxis clamp (±511) and the r24 deadband (3 counts) are off; both make the real lanes
   WEAKER than modelled at large amplitude, so the linear gate is the conservative one for the revert's HF cost.
4. The common panel-2 scorer (frame box κ ∈ {0.83, 1, 1.155}, aged singles, k·sech² op-points on the refuter model) was not
   re-run; this harness reproduces its structure (hold, lag, fade, FWD, fresh D) but its absolute PMs are higher than the
   design's quoted tier minima (69.5° vs 58.8° tier A), so read the **deltas and the HF gates**, not the absolute PM.
5. H_tb above 30 Hz is the two-mass fit (B); the r24 term's 20 Hz damping rests on the measured band (E).

## 6. Pre-registered items for the adversarial lenses

- Confirm the DampAxis sum sign from bytes (the `add` into `gp-0x6b94` and `gp-0x4f50`'s sign vs the resolver) — would
  convert σ_d from B to E and close §3.
- Interlock lens: the observer latch (`FUN_0003bc20`, |gp-0x6bfc| ≤ 20000) with stock K1 102 / relay 600 under the ×6 lane.
- If the operator insists on a full stock plant: re-score with the DampAxis at an intermediate Y (e.g. stock ×2) — not done.
