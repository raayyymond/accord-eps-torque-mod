# LENS C (dynamics / unit chain / lineage) on V300-A340 REV 4 -- verdict PASS_WITH_DEFECTS
E = evidence (method), B = belief. Scripts in this folder: c_manual.py c_readout.py c_lane.py c_amp.py c_pert.py (84 s, over the seconds budget) c_strict.py c_jlo.py.
FAIL defined beforehand: (i) a data-consistent, positive-inertia plant with GM < 3 dB or closed-loop peak > +6 dB; (ii) manual buzz shown to be the angle loop; (iii) a stock-lane angle loop already flown and failed.

## 1. Lineage
- No A160 build has flown the angle loop with the lane at stock. V298/V299/V300 carry the x3 rows; the A160 re-score kept them because reverting failed GATE 2 (PART6 l.27-29, lever index l.35). V298's rows not checked directly (B).
- Why x3 was added (E, lineage text): on the x6 RATE loop, V106 (x3) extinguished the 21-27 Hz low-speed grinding (a6/V105 = 0.347; stock control a6/STOCK = 5.7). V94 cut the lane to a quarter and the operator said the car vibrated entirely and was unsafe: the lane is a real 6-9 Hz damper on A160. So the stock lane was not enough damping for a boosted rate loop on A160.
- Why REV 4 may still differ (B): the angle loop has its own Kd 48 and a fresh motor-rate D, so the rate-loop precedent is not like-for-like. A340 stock was quiet at 4-48 Hz engaged, but only 135 s at >= 10 m/s; no stock-lane evidence on A340 below 10 m/s.

## 2. The lane's own loop
- Local loop (E, own derivation, ZOH inertia, L = g*LP1(37/128)*LP2(a2/64)*z^-d): a2 14 d2: g_crit 7.03 at 116 Hz (alias 16.0); a2 14 d3: 4.03, 81 Hz (19.0); a2 22 d2: 5.37, 130 Hz (30); a2 22 d3: 3.19, 91 Hz (9.3). Agrees with tracer/GATE 2. 16 Hz alias matches measured 16.3 Hz median (12.7-22.1). a2 22->14 raises g_crit 2.0-2.3 dB. REV 3 gain steps x3 / x4.5 / x8.1 = 9.5 / 13 / 18.2 dB. Clamp DF: amplitude above the clamp for g/g_crit > 1; hard excitation needs friction holding it quiet until a kick.
- Stock margin (B, from measured duty): between 0 and ~7.4 dB at <= 20 km/h. REV 4 keeps stock's margin, which is thin.
- Manual buzz is not the angle loop (E; 137,675 samples, 23 segments): all 10,205 manual buzz samples have cmd = 0 and request = 0; 26 manual buzz runs >= 1 s (80.6 s) start >= 5 s after the last engagement, 7 of them before the route's first engagement (t = 17-135 s); manual duty near centre is flat 36-40 % for 0 to 60 s since engagement, so not a leftover. Tracer's request-off audit gates the loop at request 0 (E, disassembly).
- Speed profile (E): engaged duty 50-60 % at 2-8 m/s, 87-100 % at 10-20, 78-83 % at 26-34; manual 10-15 % at 2-6, 63 % at 10-12, 0 % at 0-2. Rises with lane gain; consistent with the lane explanation, does not discriminate against the angle loop. In-buzz amplitude engaged 8.7-9.8 vs manual 7.6-8.1 deg/s: amplitude nearly engagement-independent; engagement mostly doubles duty.
- Open (B): why engagement doubles duty is unexplained (hands-off, loop kicks, or angle-to-lane coupling); a null on engaged duty could land here.
- Confound (B): the lane hypothesis needs the chassis key to be TWAA0/1 (tracer's open fact). If the key is different the rows are inert and REV 4 reverts only a2, which lowers g_crit and would not cure a buzz from another source.
- Other manual-live edits survive REV 4 (B): EME ladder and boost floor (limits only raised, tracer BELIEF), A340 base-assist bank (7,487 B different, untraced). A160 flew the ladder quietly.

## 3. GATE 2 attack
a) J_lo corner (c_jlo.py, E): needs negative mechanical inertia only at lane scale >= 0.77. At scale 0.5 the point is admissible and GM is 13.8 dB (T -3.3); at 0.25 GM 21.7. In the doc formulation no admissible point fails.
b) Explicit plant perturbed (c_pert.py, c_strict.py; central b x1.6, k x1.3, J_m 0.035): central at 3-8 m/s GM 31-33 dB, T -8 dB. k x0.7-2 and J_m 0.012-0.15 move GM <= 3 dB. Lane delay to 5 ms, lane scale 0.5-2, two-mass 10-20 Hz with b x0.5: all pass (T <= +0.2). Extra angle-path delay 10/20 ms costs 12-15 / 20 dB GM, still passes at central. Only b matters: at 3-8 m/s b x0.5 T -0.6..-0.8; x0.3 +2.3..+2.8; x0.2 +4.3..+5.4 (GM 23-26); x0.1 +7.0..+9.4 (GM 9-13); x0 +11..+17 (GM 5.5-9.7), peak at 7-8 Hz. Combined: b x0.5 + 20 ms extra delay + lane scale <= 1 gives GM 2.4-2.8, T +10..+12.
c) Unit chain: own derivation agrees (1.155*4.7121 is B). Lane scale x0.5 / x2 never creates a failure at central; local-loop dB margins are scale-independent. Scale only decides whether J_lo is admissible.
d) 2.0T mass and base-assist bank not modelled: plant = A160 family scaled by A340 low-frequency ratios; no A340 data below 6 m/s. A340 b ratio 6-10 m/s 0.62 [-0.16, 1.31]; 10-16 m/s 0.17 [-0.05, 0.83]; both from <= 1.5 Hz data. 5-11 Hz damping unidentified.

## 4. Exposure and readout
- Exposure (B): engaged, creep to ~18 km/h, 7-8 Hz ring; firm grip suppresses (pressed duty 6.7 %; |tq| >= 800 duty 13 %). Numeric amplitude not computable without the lane scale (B); the loop's own bound is the 3072-count output clamp.
- Readout (E; 8-20 Hz rms over 1 s, request set, not pressed): A340 REV 3 1-8 m/s (73 s) p50 5.83 / p90 8.61; REV 3 10-20 m/s p50 9.24 / p90 10.17; A160 V300 1-8 m/s (818 s) 0.61 / 1.54; A160 V300 10-20 m/s 0.56 / 1.50; A340 stock 10-20 m/s (135 s) 1.20 / 2.33. Separates buzzing from quiet by ~6x. Defect: "clean" (p50 <= 1.0, p90 <= 2.0) is tighter than A340 stock itself. No A340 stock reference at 1-8 m/s.

## 5. What a null licenses
- Manual buzz unchanged on a confirmed REV 4 flash: falsifies "rows and a2 are the cause" on this car; not the angle loop (gated off in manual); leaves the chassis key, EME ladder and base-assist bank.
- Gone in manual, present engaged: lane explains manual only; residual is angle-loop or engagement coupling.
- Quiet everywhere: licenses only "x3 rows / a2 14 were sufficient"; says nothing about creep without >= 20 s engaged at 1-8 m/s hands light.
- Confounds the route cannot settle: fork version, user's grip, chassis key, speed mix.

## 2a. Literal trigger
Met on the letter at b ~0.1x the A160 nominal viscous, 3-8 m/s (peak +7.0..+9.4 dB at 7-8 Hz, GM 9-13). Not declared DO_NOT_FLASH: that corner is unidentified rather than evidenced, it is a linear-model ring that Coulomb friction would damp, and A340 stock was quiet at >= 10 m/s. Judgement is the orchestrator's (B).

## Defects
D1 no precedent for angle loop on stock lane (high); D2 creep 5-11 Hz damping unmeasured (high); D3 "clean" threshold miscalibrated vs A340 stock (medium); D4 chassis key unconfirmed (high); D5 engaged-duty doubling unexplained (medium); D6 2.0T plant and base-assist bank unmodelled (medium); D7 c_pert.py runs 84 s (low).
