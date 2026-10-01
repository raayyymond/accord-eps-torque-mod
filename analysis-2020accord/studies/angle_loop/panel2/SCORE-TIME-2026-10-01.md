# SCORE-TIME 2026-10-01 — the panel-2 common time-domain scorer (30 columns, one pipeline)

**Status: ANALYSIS ONLY.** Nothing was built, flashed or sent; no image, `.rwd`, fork file or design file was written;
nothing was committed. GhidraMCP was not needed: every cave in scope was checked by EXECUTING its bytes (the refuter's
independent V850E2 interpreter, extended), and every lane line is the refuter's instruction-by-instruction lane, already
controlled against the disassembly (`REFUTE-C2-r2-nonlinear` §1 C2). **This scorer picks no winner.**

**Author:** the common time-domain scorer, a subagent of the orchestrator `main`.
**Script:** `analysis-2020accord/studies/angle_loop/panel2/score_time.py` (one file; `h1`, `validate`, `run`, `report`).
**Outputs:** `panel2/score_time_out/` — `score_time_tables.md` (every table, both frames), `score_time_summary.json`,
`validate_out.txt`, `h1_out.txt`, `h1_negative_controls.txt`. Raw grid caches: `_scratch/angle_loop/panel2-score-time/`
(gitignored, regenerable).

Every decision-bearing claim is **EVIDENCE** (method named) or **BELIEF**. "Simulation" means this pipeline: EVIDENCE
about the model, BELIEF about the car until a drive measures it.

---

## 0. The answer on one page

**Every one of the 30 columns ran through the identical pipeline**: the same lane arithmetic (one class, the candidate's
cave as a per-column switch), the same plant members, sensors, fork, scenarios and metric code, in one batch per
(scenario, member, column chunk), so every column saw bit-identical inputs. 94 speeds (3.0, 3.1, 5.0 and 8.00–30.00
every 0.25 m/s, plus the knots 11.9 / 26.9), members nominal / bc / F_hi / b_lo×J_hi, 22 scenarios, two frame models.

1. **Only the E2 angle-referenced-bound family — E2-A2, E2-A3, E2-A3-12k, E2-A2-X — passes every decidable time
   criterion of the goal in every band ≥ 8 m/s, on all four members, in both frames**, including the goal's tracking metric
   with route r71b's OWN torque word replayed and the light- and firm-hand release lurch bars. EVIDENCE (simulation;
   §5.1/§5.2). Worst cells: tracking 0.985 / 0.991 / 1.005 (8–15 / 15–22 / >22 m/s, replayed word); turn-hold ≥ 0.98
   (a_lat ≤ 2.5); light lurch 5.8° and firm 4.7° (b_lo×J_hi, 1 s hold).
2. **F1 (the integrator clamp) is fixed by every candidate that raises ICL to ≥ 7500 and does not drain the I on the
   torque word**: E1-cal, E1-reset, E1-freeze, E2-R1, E2-S and the A family read 0.986 / 0.993 / 1.006 on r71b's paths
   (P2: 0.892 / 0.856 / 1.002 — the refuter's F1 reproduced). EVIDENCE.
3. **Every policy that drains the I on the hand word below ~1000 fails the goal's tracking metric once r71b's own torque
   word is replayed**: E1-bleed 0.752 / 0.739 / 0.829, E2-L 0.938 (8–15), **H-A 0.925 / 0.947 and H-B 0.933 / 0.952 —
   undeclared by H** (8–15 / 15–22 m/s, vgr; unity: H-A 0.930 / 0.954, H-B 0.932 / 0.952 — the 8–15 m/s fail holds in
   both frames). The replayed word exceeds 512 on 0.8–1.2 % of frames and peaks at 1.0–1.2 k (EVIDENCE: the word
   series itself); H's bleed (`I8 −= I8 >> 7` above |tq| 512) drains the hold during normal driving. EVIDENCE.
4. **The light-hand release lurch separates the F1-fixing candidates.** With no bound on the I (E1-cal, E1-reset,
   E2-R1, E2-L) it is **24.3°** on b_lo×J_hi at 10.25 m/s with the I at its clamp (23.2° unity, 26.2° with a 3 s hold);
   H-A / H-B 22.2° / 20.8° (their bleed threshold 512 cannot see a hand reading ≤ 511). E1-freeze 11.8° and E2-S 11.1°
   (only at 8–10 m/s; ≤ 4.5° above 10 m/s). The A family 5.8°. E1-bleed 3.8° but it fails item 3. EVIDENCE.
5. **G (the D axis) keeps ICL 4096, so F1 stands on every G column** (tracking 0.814–0.903, turn-hold 0.66–0.78); G's
   re-sized D lowers the firm-hand lurch (b_lo×J_hi 7.9° → 6.0–6.9°) and the hard-turn 1.6–3 Hz ratio, and costs
   small-signal in-phase gain (±1° at 0.2 Hz, worst ≥ 8 m/s: 0.86 → 0.46–0.70; G-P48L 0.11). EVIDENCE. As G declared.
6. **Small-correction stick-slip at 8–15 m/s is the same on every integral policy** (same P, same friction): ±0.3° at
   0.2 / 0.5 Hz sticks 70–100 % of the time with in-phase gain down to −0.36…−0.46 at 10–12.5 m/s; ±1° corrections
   dwell-then-jump 221–234 times over the ≥ 8 m/s grid on the round-1, E1, E2, G-P48d and G-P48k40 columns (almost all
   at 0.5 Hz, 8–15 m/s; 245–317 on the other G tables and H-A; E1-splitP's Kp 200 cuts it to 107 but fails turn-hold). No candidate removes it; H-A (its P in the motor
   frame) and the G tables make the dip slightly worse. **Not decidable against V282** (not simulable). EVIDENCE (sim).
7. **Fail-safe paths behave on every column**: request drop → |T| = 0 by 150 ms; 0xE4 sentinel → |T| ≤ 78 counts from
   50 ms and decaying (peak ≤ 430); the 510 ms timeout moves the wheel 2.1–2.6° if it lands mid-motion at 8–12.5 m/s
   (≤ 5.6° below 8 m/s) and ≤ 0.55° in a held turn; 0 int32 wraps anywhere. EVIDENCE. The relay-close camera case and
   pol ≠ −1 (F5) are not simulable here.
8. **E2-K0, E1-sched and E1-splitP fail the goal as their designers said** (K0 0.915 at 15–22 m/s and real-curve hold
   0.652; sched 0.886; splitP turn-hold 0.755). EVIDENCE.

**Main table (vgr frame) -- worst over the four members; '>=8' = worst over every speed 8-30 m/s**

| cand | cave B | trk r71b 8-15 / 15-22 / >22 | trk replay 8-15 / 15-22 / >22 | real-curve hold min | turn-hold a<=2.0 min >=8 | a 2.5 min >=8 | in-phase gain +-1 deg 0.2 Hz min >=8 | dwell-jump +-1 deg >=8 (max snap) | dwell-jump +-0.3 deg >=8 (max snap) | light lurch max >=8 (b_lo*J_hi) | firm lurch max >=8 (b_lo*J_hi) | engage droop max >=8 | co-steer droop max >=8 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P2 | 156 | 0.892 / 0.856 / 1.002 | 0.892 / 0.855 / 1.001 | 0.76 | 0.73 | 0.69 | 0.86 | 228 (1.74) | 1038 (0.62) | 10.9 (10.9) | 7.9 (7.9) | 6.3 | 2.4 |
| F2 | 138 | 0.897 / 0.851 / 1.001 | 0.896 / 0.850 / 1.001 | 0.75 | 0.72 | 0.68 | 0.84 | 226 (1.65) | 1067 (0.61) | 10.9 (10.9) | 7.6 (7.6) | 6.4 | 2.5 |
| D2a | 162 | 0.892 / 0.857 / 1.002 | 0.892 / 0.856 / 1.001 | 0.76 | 0.73 | 0.69 | 0.85 | 232 (1.75) | 1032 (0.61) | 10.9 (10.9) | 7.9 (7.9) | 6.3 | 2.4 |
| B0r | 144 | 0.897 / 0.852 / 1.002 | 0.896 / 0.852 / 1.001 | 0.75 | 0.72 | 0.68 | 0.84 | 234 (1.66) | 1061 (0.60) | 10.9 (10.9) | 7.6 (7.6) | 6.4 | 2.5 |
| E1-reset | 168 | 0.986 / 0.993 / 1.006 | 0.985 / 0.991 / 1.005 | 0.98 | 0.98 | 0.98 | 0.86 | 224 (1.74) | 1031 (0.62) | 24.3 (24.3) | 4.2 (4.2) | 6.3 | 2.4 |
| E1-cal | 156 | 0.986 / 0.993 / 1.006 | 0.985 / 0.991 / 1.005 | 0.98 | 0.98 | 0.98 | 0.86 | 223 (1.74) | 1020 (0.61) | 24.3 (24.3) | 8.4 (8.4) | 6.3 | 2.4 |
| E1-bleed | 190 | 0.986 / 0.993 / 1.006 | 0.752 / 0.739 / 0.829 | 0.98 | 0.98 | 0.98 | 0.86 | 226 (1.75) | 1027 (0.62) | 3.8 (3.8) | 4.1 (4.1) | 6.3 | 3.6 |
| E1-freeze | 168 | 0.986 / 0.993 / 1.006 | 0.982 / 0.984 / 0.997 | 0.98 | 0.98 | 0.98 | 0.86 | 226 (1.74) | 1031 (0.61) | 11.8 (11.8) | 4.1 (4.1) | 6.3 | 1.3 |
| E1-sched | ~200 | 0.886 / 0.928 / 0.941 | 0.885 / 0.927 / 0.941 | 0.87 | 0.89 | 0.83 | 0.85 | 226 (1.75) | 1026 (0.62) | 11.1 (11.1) | 4.2 (4.2) | 6.3 | 2.4 |
| E1-splitP | 168 | 0.898 / 0.856 / 0.962 | 0.897 / 0.856 / 0.961 | 0.79 | 0.75 | 0.74 | 0.81 | 107 (1.17) | 627 (0.49) | 9.9 (9.9) | 6.4 (6.4) | 4.9 | 1.9 |
| E2-R1 | 156 | 0.986 / 0.993 / 1.006 | 0.985 / 0.991 / 1.005 | 0.98 | 0.98 | 0.98 | 0.85 | 222 (1.74) | 1035 (0.62) | 24.3 (24.3) | 8.4 (8.4) | 6.3 | 2.4 |
| E2-S | 172 | 0.986 / 0.993 / 1.006 | 0.980 / 0.984 / 0.996 | 0.98 | 0.98 | 0.98 | 0.86 | 225 (1.74) | 1035 (0.61) | 11.1 (11.1) | 8.2 (8.2) | 6.3 | 1.3 |
| E2-A2 | 204 | 0.986 / 0.993 / 1.006 | 0.985 / 0.991 / 1.005 | 0.98 | 0.98 | 0.98 | 0.86 | 226 (1.75) | 1029 (0.61) | 5.8 (5.8) | 4.7 (4.7) | 6.3 | 2.4 |
| E2-A3 | 222 | 0.986 / 0.993 / 1.006 | 0.985 / 0.991 / 1.005 | 0.98 | 0.98 | 0.98 | 0.86 | 229 (1.74) | 1034 (0.62) | 5.8 (5.8) | 4.7 (4.7) | 6.3 | 2.4 |
| E2-A3-12k | 222 | 0.997 / 0.995 / 1.006 | 0.995 / 0.991 / 1.005 | 0.98 | 0.98 | 0.98 | 0.86 | 227 (1.74) | 1032 (0.61) | 5.8 (5.8) | 4.7 (4.7) | 6.3 | 2.4 |
| E2-A2-X | 204 | 0.986 / 0.993 / 1.006 | 0.986 / 0.991 / 1.005 | 0.98 | 0.98 | 0.98 | 0.85 | 221 (1.75) | 1032 (0.61) | 5.8 (5.8) | 4.7 (4.7) | 4.3 | 2.4 |
| E2-L | 168 | 0.986 / 0.993 / 1.006 | 0.938 / 0.958 / 0.990 | 0.98 | 0.98 | 0.98 | 0.85 | 221 (1.61) | 1038 (0.61) | 24.3 (24.3) | 4.2 (4.2) | 6.3 | 2.4 |
| E2-K0 | 132 | 0.965 / 0.915 / 0.966 | 0.965 / 0.915 / 0.966 | 0.65 | 0.98 | 0.98 | -0.07 | 263 (0.77) | 31 (0.32) | 20.0 (20.0) | 5.1 (5.1) | 6.3 | 2.2 |
| G-P48d | 156 | 0.892 / 0.860 / 1.002 | 0.891 / 0.859 / 1.001 | 0.76 | 0.74 | 0.70 | 0.70 | 224 (1.61) | 969 (0.63) | 10.0 (10.0) | 6.2 (6.2) | 6.0 | 2.3 |
| G-P44d | 156 | 0.885 / 0.856 / 1.002 | 0.884 / 0.855 / 1.001 | 0.76 | 0.73 | 0.69 | 0.64 | 247 (1.69) | 960 (0.62) | 10.6 (10.6) | 6.5 (6.5) | 6.2 | 2.3 |
| G-P48 | 156 | 0.892 / 0.835 / 1.002 | 0.891 / 0.834 / 1.001 | 0.72 | 0.69 | 0.64 | 0.69 | 273 (1.60) | 1013 (0.63) | 10.1 (10.1) | 6.2 (6.2) | 6.0 | 2.3 |
| G-P44 | 156 | 0.885 / 0.831 / 1.002 | 0.884 / 0.830 / 1.001 | 0.72 | 0.68 | 0.63 | 0.66 | 306 (1.68) | 1021 (0.62) | 10.5 (10.5) | 6.5 (6.5) | 6.2 | 2.3 |
| G-F24 | 138 | 0.882 / 0.821 / 1.002 | 0.882 / 0.820 / 1.001 | 0.70 | 0.67 | 0.61 | 0.56 | 312 (1.72) | 1019 (0.59) | 10.9 (10.9) | 6.4 (6.4) | 6.5 | 2.5 |
| G-F24d | 138 | 0.883 / 0.847 / 1.002 | 0.882 / 0.846 / 1.001 | 0.74 | 0.72 | 0.67 | 0.56 | 245 (1.73) | 968 (0.60) | 11.0 (11.0) | 6.4 (6.4) | 6.6 | 2.5 |
| G-A22 | 210 | 0.877 / 0.814 / 1.002 | 0.877 / 0.814 / 1.001 | 0.69 | 0.66 | 0.60 | 0.47 | 317 (1.74) | 1012 (0.60) | 11.8 (11.8) | 6.9 (6.9) | 6.9 | 2.7 |
| G-A22d | 210 | 0.878 / 0.841 / 1.002 | 0.877 / 0.840 / 1.001 | 0.73 | 0.71 | 0.66 | 0.46 | 258 (1.65) | 1029 (0.60) | 11.9 (11.9) | 6.9 (6.9) | 6.9 | 2.7 |
| G-P48L | 156 | 0.871 / 0.834 / 1.002 | 0.870 / 0.834 / 1.001 | 0.72 | 0.69 | 0.64 | 0.11 | 248 (1.63) | 918 (0.63) | 10.9 (10.9) | 6.3 (6.3) | 5.9 | 2.3 |
| G-P48k40 | 156 | 0.903 / 0.838 / 0.998 | 0.903 / 0.837 / 0.997 | 0.74 | 0.70 | 0.65 | 0.56 | 222 (1.30) | 714 (0.52) | 9.6 (9.6) | 6.0 (6.0) | 5.8 | 2.2 |
| H-A | ~190 | 0.975 / 0.987 / 1.005 | 0.925 / 0.947 / 0.985 | 0.97 | 0.98 | 0.92 | 0.75 | 287 (1.72) | 987 (0.61) | 22.2 (22.2) | 2.8 (2.8) | 6.5 | 2.5 |
| H-B | ~164 | 0.977 / 0.988 / 1.006 | 0.933 / 0.952 / 0.988 | 0.98 | 0.97 | 0.93 | 0.84 | 233 (1.76) | 1058 (0.61) | 20.8 (20.8) | 3.3 (3.3) | 6.3 | 2.4 |

**Goal-criteria fails per band (the goal's decidable time criteria; '<8' is outside the goal's bands)**
TRK/TRKq = tracking outside 0.95-1.05 (clean / r71b's own torque word replayed; data band 8-15 serves 8-10, 10-12.5 and 12.5-15); HOLD = synthetic turn-hold < 0.90 at a_lat <= 2.0; RHOLD = a real r71b curve held < 0.90; HUNT = a limit cycle (>= 2 reversals and >= 0.2 deg p2p in the last 20 s of a 30 s constant setpoint); TEX = T 5-30 Hz > 2.0 counts in that hold; LURCH = a light or firm release lurch > 8 deg (rev2-B's pre-registered bar; a time gate of the brief, not one of the goal's own criteria).  Dwell-then-jump is NOT in this table: the goal's criterion is relative to V282 (not simulable); its counts are in their own tables.

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | n/a | TRK 0.892; TRKq 0.892; LURCH 9.8 | TRK 0.892; TRKq 0.892; LURCH 10.9 | TRK 0.892; TRKq 0.892; HOLD 0.778; LURCH 8.1 | TRK 0.856; TRKq 0.855; HOLD 0.732; RHOLD 0.756 | pass |
| F2 | n/a | TRK 0.897; TRKq 0.896; HOLD 0.896; LURCH 9.6 | TRK 0.897; TRKq 0.896; LURCH 10.9 | TRK 0.897; TRKq 0.896; HOLD 0.770; LURCH 8.1 | TRK 0.851; TRKq 0.850; HOLD 0.722; RHOLD 0.748 | pass |
| D2a | n/a | TRK 0.892; TRKq 0.892; LURCH 9.8 | TRK 0.892; TRKq 0.892; LURCH 10.9 | TRK 0.892; TRKq 0.892; HOLD 0.778; LURCH 8.1 | TRK 0.857; TRKq 0.856; HOLD 0.733; RHOLD 0.757 | pass |
| B0r | n/a | TRK 0.897; TRKq 0.896; HOLD 0.896; LURCH 9.6 | TRK 0.897; TRKq 0.896; LURCH 10.9 | TRK 0.897; TRKq 0.896; HOLD 0.770; LURCH 8.1 | TRK 0.852; TRKq 0.852; HOLD 0.725; RHOLD 0.750 | pass |
| E1-reset | n/a | LURCH 24.0 | LURCH 24.3 | LURCH 13.3 | LURCH 8.3 | pass |
| E1-cal | n/a | LURCH 24.0 | LURCH 24.3 | LURCH 13.3 | LURCH 8.3 | pass |
| E1-bleed | n/a | TRKq 0.752 | TRKq 0.752 | TRKq 0.752 | TRKq 0.739 | TRKq 0.829 |
| E1-freeze | n/a | LURCH 11.8 | pass | pass | pass | pass |
| E1-sched | n/a | TRK 0.886; TRKq 0.885; HOLD 0.887; LURCH 11.1 | TRK 0.886; TRKq 0.885; HOLD 0.897; LURCH 9.5 | TRK 0.886; TRKq 0.885; LURCH 8.5 | TRK 0.928; TRKq 0.927; HOLD 0.895; RHOLD 0.867 | TRK 0.941; TRKq 0.941 |
| E1-splitP | n/a | TRK 0.898; TRKq 0.897; HOLD 0.896; LURCH 9.9 | TRK 0.898; TRKq 0.897; HOLD 0.878 | TRK 0.898; TRKq 0.897; HOLD 0.787 | TRK 0.856; TRKq 0.856; HOLD 0.755; RHOLD 0.788 | pass |
| E2-R1 | n/a | LURCH 24.0 | LURCH 24.3 | LURCH 13.3 | LURCH 8.3 | pass |
| E2-S | n/a | LURCH 11.1 | pass | pass | pass | pass |
| E2-A2 | n/a | pass | pass | pass | pass | pass |
| E2-A3 | n/a | pass | pass | pass | pass | pass |
| E2-A3-12k | n/a | pass | pass | pass | pass | pass |
| E2-A2-X | n/a | pass | pass | pass | pass | pass |
| E2-L | n/a | TRKq 0.938; LURCH 24.0 | TRKq 0.938; LURCH 24.3 | TRKq 0.938; LURCH 13.3 | LURCH 8.3 | pass |
| E2-K0 | n/a | RHOLD 0.652; LURCH 20.0 | RHOLD 0.652 | RHOLD 0.652 | TRK 0.915; TRKq 0.915; RHOLD 0.729 | pass |
| G-P48d | n/a | TRK 0.892; TRKq 0.891; LURCH 8.2 | TRK 0.892; TRKq 0.891; LURCH 10.0 | TRK 0.892; TRKq 0.891; HOLD 0.779 | TRK 0.860; TRKq 0.859; HOLD 0.738; RHOLD 0.763 | pass |
| G-P44d | n/a | TRK 0.885; TRKq 0.884; HOLD 0.895; LURCH 8.7 | TRK 0.885; TRKq 0.884; LURCH 10.6 | TRK 0.885; TRKq 0.884; HOLD 0.774 | TRK 0.856; TRKq 0.855; HOLD 0.732; RHOLD 0.756 | pass |
| G-P48 | n/a | TRK 0.892; TRKq 0.891; LURCH 8.2 | TRK 0.892; TRKq 0.891; LURCH 10.1 | TRK 0.892; TRKq 0.891; HOLD 0.744 | TRK 0.835; TRKq 0.834; HOLD 0.690; RHOLD 0.723 | pass |
| G-P44 | n/a | TRK 0.885; TRKq 0.884; HOLD 0.895; LURCH 8.7 | TRK 0.885; TRKq 0.884; LURCH 10.5 | TRK 0.885; TRKq 0.884; HOLD 0.733 | TRK 0.831; TRKq 0.830; HOLD 0.684; RHOLD 0.718 | pass |
| G-F24 | n/a | TRK 0.882; TRKq 0.882; HOLD 0.885; LURCH 9.0 | TRK 0.882; TRKq 0.882; LURCH 10.9 | TRK 0.882; TRKq 0.882; HOLD 0.726; LURCH 8.2 | TRK 0.821; TRKq 0.820; HOLD 0.670; RHOLD 0.702 | pass |
| G-F24d | n/a | TRK 0.883; TRKq 0.882; HOLD 0.885; LURCH 9.0 | TRK 0.883; TRKq 0.882; LURCH 11.0 | TRK 0.883; TRKq 0.882; HOLD 0.761 | TRK 0.847; TRKq 0.846; HOLD 0.716; RHOLD 0.742 | pass |
| G-A22 | n/a | TRK 0.877; TRKq 0.877; HOLD 0.877; LURCH 9.8 | TRK 0.877; TRKq 0.877; LURCH 11.8 | TRK 0.877; TRKq 0.877; HOLD 0.714; LURCH 8.7 | TRK 0.814; TRKq 0.814; HOLD 0.660; RHOLD 0.693 | pass |
| G-A22d | n/a | TRK 0.878; TRKq 0.877; HOLD 0.876; LURCH 9.8 | TRK 0.878; TRKq 0.877; LURCH 11.9 | TRK 0.878; TRKq 0.877; HOLD 0.752; LURCH 8.5 | TRK 0.841; TRKq 0.840; HOLD 0.708; RHOLD 0.733 | pass |
| G-P48L | n/a | TRK 0.871; TRKq 0.870; HOLD 0.886; LURCH 8.7 | TRK 0.871; TRKq 0.870; LURCH 10.9 | TRK 0.871; TRKq 0.870; HOLD 0.733; LURCH 8.1 | TRK 0.834; TRKq 0.834; HOLD 0.688; RHOLD 0.723 | pass |
| G-P48k40 | n/a | TRK 0.903; TRKq 0.903; LURCH 8.1 | TRK 0.903; TRKq 0.903; LURCH 9.6 | TRK 0.903; TRKq 0.903; HOLD 0.760 | TRK 0.838; TRKq 0.837; HOLD 0.702; RHOLD 0.736 | pass |
| H-A | n/a | TRKq 0.925; LURCH 22.0 | TRKq 0.925; LURCH 22.2 | TRKq 0.925; LURCH 11.7 | TRKq 0.947 | pass |
| H-B | n/a | TRKq 0.933; LURCH 19.8 | TRKq 0.933; LURCH 20.8 | TRKq 0.933; LURCH 12.6 | pass | pass |

---

## 1. The pipeline, and how far it can be trusted (controls, all re-runnable)

| # | control | method | result |
|---|---|---|---|
| V1 | the refuter's own engine control, re-run unchanged after E2's additive edit to rev2-A's `score_time.py` | `refute_c2r2_nonlinear/ctl_vs_designers.py` (nl_sim vs `c2/rev2A/score_time.run`, sensor noise 0) | **EVIDENCE:** bit-exact on rh 11.9 / s02 17 / tmo 26.9; 0.015° and 3–4 counts on ov_light400 10 m/s bc (the hand-model difference the refuter recorded). Identical to the refuter's published result. |
| V2 | THIS scorer's lane + runner (frame `unity`) vs `nl_sim.run` | 7 lens scenarios (rh, ov_lt511, ov_firm, eng, tmos, mic05, sen; one member each, all four members used) × P2 / F2 / D2a / B0r × 5 speeds, sensor noise ON, same seed | **EVIDENCE: max\|Δθ\| 0, max\|ΔT\| 0** in every case. With the frame switch at `unity` this pipeline IS the refuter's engine. |
| V3a | E1's own lane (`e1_lane.E1Lane`, an nl_sim.Lane subclass) through nl_sim.run | rh / ov_lt400 / ov_firm / eng × 4 speeds × E1-reset, cal, freeze, sched, splitP, bleed | **EVIDENCE: 0 / 0** for every E1 column **except E1-bleed: 0.045° / 4–5 counts on the two override scenarios** — E1's mirror bleeds `I −= I >> 3` after the clamp; the LISTED bytes (`ld.w; mov; sar 3; sub; st.w -0x6dd0`) bleed I8 before Honda's read. This scorer implements the listing. |
| V3b | E2's own lane (`e2_lane.E2Lane`, a DSLane subclass) through rev2-A's engine | a signed torque program walking every threshold (−700 / −2000 / −400 / +400 / −280 words, the wheel held back by an external torque so the bound binds), s02, tmo × 8 / 11.75 / 17 / 26.9 m/s × R1, S, A2, A3, L, A2-X | **EVIDENCE: 0 / 0** everywhere except **E2-A2-X in tmo (0.002–0.05°, 2–6 counts)**: this scorer gives the 6803 == 2 column its own ramp-out (0xC63FA, 66 / tick); rev2-A's runner uses one scenario-level ramp-out (16) for every column. Modelled difference, not a lane difference. |
| V3c | G's own lane (`g_lane.GLane`) through rev2-A's engine | the same three scenarios × G-P48, P44d, F24, A22, A22d, P48k40 | **EVIDENCE: 0 / 0** everywhere (fresh, held, box10, Ki 40). |
| V4 | headline numbers re-derived on this pipeline (`unity` frame) | the refuter's and the designers' own scenarios | **EVIDENCE:** P2 turn-hold at 17 m/s, 2.0 m/s² = **0.734** (refuter 0.73–0.74); P2 r71b nominal 0.900 / 0.856 (refuter 0.900 / 0.856); 3 s-hold light lurch b_lo×J_hi P2 **10.4°** (refuter 10.40), E2-R1 **25.1°** (E2 25.15), E2-A2 **5.2°** (E2 5.18), nominal P2 7.1° (E2 7.17); E2-L replay 0.938 (E2 0.938); E2-K0 nominal 0.968 / 0.919 (E2 0.969 / 0.920); A2-X engage droop 4.3° (E2 4.2°). |
| H1 | every hex-backed candidate's cave BYTES executed vs this scorer's own cave stage (the function the grid runs) | `nl_cave.Cpu` (the refuter's independent interpreter) + `Cpu2` (xor, subr, add/cmp imm5, ld.w, st.h/st.w, written here from the ISA formats); 3 000 cases each: random + every threshold ±1, signed hand words, validity edges ±13000/13001 and 0x7FFF, ramp 0 / partial / 0x8000 / 0xFFFF, table knots ±1, the 1382 / 2880 speed knees, Honda's first-tick sentinel, box10 RAM states; checks r16 = E′, the exit (0x29D7A / 0x29D7E), r6 at the 0x29D7E exit, r26 out, gp-0x6dd0 / -0x6c44 / -0x6c40 after, every other RAM cell and every non-scratch register unchanged | **EVIDENCE: 0 mismatches on all 26 hex-backed columns** (P2, F2, D2a, B0r; E1-reset / freeze / splitP on the listed 12-byte block assembled here into P2's FRZ path with every displacement re-linked; E1-cal; E2 R1, S300, A2, A3, A3-12k, A2-X, L13, K0; all ten G, G-P48L and G-P48k40 as G-P48's code with their own table rows). **Negative controls all fail as they must** (wrong policy on the right bytes, wrong table, leak 14 vs 13, held vs fresh, freeze 320 vs 512): 125–1 500 mismatches of 1 500. |
| — | no listing | E1-bleed, E1-sched (no hex: implemented from the listed instructions / the designer's own ICL walk), H-A and H-B (H gives the structure, not a listing: "D2a + ~24 B bleed", "B0r + ~24 B bleed") | **BELIEF** that the mirror equals the bytes they would build. |

**Engine** (EVIDENCE, by V1/V2): the refuter's independent Karnopp plant on the r71b family (10 kHz sub-steps, 2 ms
transport), gp-0x6a00 = floor(10θ + 0.5) held at slot 4 after the lane, gp-0x6abe = the 1 kHz integer EMA (α 37/128) of
gp-0x4f50 = s16(round(−4.712 · motor-frame deg/s + N(0, 2.8))), gp-0x6a56 = the slot-4 hold of
clamp(−((abe·48·1159) >> 15), ±12000), 0xE4 on tick % 10 == 0 with raw = −round(10 θ_sp) and gp-0x69ae = clamp(−4 raw,
±16384). The 2.8-count sensor noise and the EMA form are the D designer's decode (BELIEF), reused as a model.

**One label fixed in the reused metric code** (EVIDENCE: arithmetic): `nl_lens.metrics('eng')` names `(θ − sp)·sgn` the
"droop" and `(sp − θ)·sgn` the "ovs" — the reverse of its own comment. The refuter's *reported* number (6.3°) is the
physical droop, so its report is unaffected; this scorer labels them correctly (droop = the wheel falling behind the held
command toward centre).

## 2. The frame (new in this scorer)

gp-0x6a00 = gp-0x69ca + C(gp-0x69ca): Honda's correction LERP (cal `0xC6892` X knots, `0xC68A2` Y knots, read by
`angle_signal_mirror.Cal('v295')`) makes the corrected angle **1.155×** the motor-linear angle below 27.7°, 1.120 / 1.083 /
1.032 / 0.993 / 0.963 / 0.962 outward (EVIDENCE: the bytes and the mirror). The plant is identified on carState's angle
(= gp-0x6a00), so this scorer's PRIMARY frame **`vgr`** maps every MOTOR-frame quantity: the rate the EMA sees is
ω / κ(θ), and gp-0x69ca = floor(10 C⁻¹(θ) + 0.5). This is G's "FA" reading (BELIEF that FA rather than FB is the right one;
FB — J and b per degree of the motor frame — was not run). **`unity`** (κ ≡ 1) is every previous scorer's convention and was
run on 16 of the 22 scenarios for the attribution table (§5.6). H-A's fork SR fold is modelled as PERFECT: the fork sends
C⁻¹(θ_plan) in the 69ca frame (BELIEF; any fold error is a steady angle-gain error this scorer does not see).

What the frame moves (EVIDENCE, §5.6): every lurch +0.5–0.7° (the near-centre D is ×0.866 weaker); H-A's small-signal gain
(±1° at 0.2 Hz, worst ≥ 8 m/s) 0.85 → 0.75 (its P and I are in the motor frame, ×0.866 near centre); nothing else ≥ 0.01.
G-A22 (angle-own D) is frame-exact (identical in both).

## 3. The columns as implemented

All on rev2-A P2's in-place set (E1 0x28F4C, E2 0x28FA4, B2 0x29A50, A2 0x29A56, E4 0x29D6A, hook 0x29D76) unless named;
cals a 0 / b 8192 / C 65535, DB 0, DCL 10240, Kp 112 flat, Ki 56, freeze |tq| > 512 or ramp not full, unless named.

| column | what differs (source) | cave / check |
|---|---|---|
| P2 / F2 / D2a / B0r | round-1 references: fresh D Kd 34 / held D Kd 20 / fresh Kd 34 / held Kd 20, their own 6- or 7-knot tables, ICL 4096 | 156 / 138 / 162 / 144 B, H1 0 |
| E1-reset | ICL 8192; FRZ path + `movea 1536; cmp r13,r8; bnh; st.w r0,-0x6dd0[gp]` | 168 B (assembled here), H1 0 |
| E1-cal | ICL 8192 only | P2's bytes, H1 0 |
| E1-bleed | E1-reset + non-freeze path: \|tq\| > 256 → I8 −= I8 >> 3 (the LISTED bytes) | no hex; mirror of the listing |
| E1-freeze | E1-reset with the freeze immediate 512 → 320 | 168 B, H1 0 |
| E1-sched | reset + ICL(v) from E1's own walk over `e1_policies.ICL_SCHED` | no hex; designer's walk (BELIEF on rounding) |
| E1-splitP | reset + Kp 200 + ICL 3072 | 168 B, H1 0 |
| E2-R1 / S / A2 / A3 / A3-12k / L | ICL 8192 (A3-12k 12288) + E2Lane's ordered decision: hard test → opposing hand (S: \|word\| > 300, sign(gp-0x4f60) ≠ sign(E′)) → angle-referenced bound (A2: `sgn(E′)(I8>>10) ≥ (\|gp-0x6a00\| << (4 if v ≤ 2880 else 6)) + 1250`; A3: bound ≤ 4096 S below 1382 counts) → ramp; L: \|tq\| > 512 → r6 = −(I8 >> 13) | their hex, H1 0 |
| E2-A2-X | A2 + the fork sends gp-0x6803 == 2: fade arm 0xCBAE4 / 0xCBB54, ramp-in 328 / tick (0.10 s), ramp-out 66 / tick | A2's hex, H1 0 |
| E2-K0 | Ki 0 (I identically 0), no freeze block; FORK angle integral: θ_sp = θ_plan + acc, acc += (θ_plan − θ_wire[−60 ms])·0.01/1.0 s per frame, frozen while \|word\|·125/128 > 1200 (E2's ForkInt, but on the 0x14A wire angle rather than the continuous one) | K0 hex, H1 0 |
| G-* | fresh (Kd 48 / 44), held (Kd 24) or box10 (Kd 22) D, Ki 56 (P48k40: 40), their own tables, ICL 4096 | their hex (P48L / P48k40: P48's code + their rows), H1 0 |
| H-A | feedback gp-0x69ca (fresh 1 kHz, motor-linear), fork SR fold, fresh guarded D Kd 34, D2a's table, ICL 7500, \|tq\| > 512 → freeze AND I8 −= I8 >> 7 | no listing (BELIEF) |
| H-B | feedback gp-0x6a00, held D Kd 23 (E5 form), B0r's table, ICL 7500, the same freeze + bleed | no listing (BELIEF) |

## 4. Scenarios and metrics (exact; `scenario()` / `metrics()` in the script)

Amplitudes: the refuter's A_TURN (90 / 50 / 30 / 12 / 5 / 3 / 2.5° at 3 / 5 / 8 / 12.5 / 19 / 26 / 30 m/s, log-interpolated);
Ah = 0.5 A. Hand words are SIGNED in the direction the hand pushes (E2 §2.1's sign evidence), so an opposing light hand
reads −sign(Ah)·w. Every metric is taken per column, then the WORST over the band's speeds and the four members.

| scenario | definition | metrics |
|---|---|---|
| r71b paths `rr` | route r71b's engaged, steeringPressed-false steering-angle runs ≥ 15 s (6 runs 8–15 m/s, 6 runs 15–22, 2 runs > 22; the refuter's `nl_realref` selection), each simulated at its median speed from θ0 = the path's start | **tracking** = the goal's metric: OLS slope with intercept of the 0.5 Hz zero-phase-LPF wheel angle on the LPF PLANNED path, runs concatenated per band, from 4 s; **real-curve turn-hold** = mean θ / mean plan over every window with \|plan\| ≥ 3° and \|d plan/dt\| ≤ max(1, 0.05\|plan\|) °/s for ≥ 1.5 s (14 windows); dwell-then-jump per 100 s |
| `rrq` | the same with r71b's OWN torque word replayed time-aligned (carState torque × 128/125 = gp-0x4f60) into the lane (freeze, bleed, leak, reset, the fade); no torque on the plant | tracking, real-curve hold |
| `th` | synthetic turn-hold: θ_sp = a_lat·2.83·16/v² (rad→deg), ramp 0.5–2.0 s, hold to 11 s, a_lat 1.0 / 1.5 / 2.0 / 2.5 m/s² (2.5 = r71b's sustained maximum at ≤ 18 m/s, E2 §2.4); A_TURN below 8 m/s | hold = mean θ over 9–11 s / target |
| `s03_02` `s03_05` `s10_02` `s10_05` | ±0.3° and ±1° sinusoids at 0.2 and 0.5 Hz, 4 cycles, scored from cycle 2 | in-phase gain (OLS of the 0x14A angle on the plan), fit gain, phase, dwell-then-jump events and largest snap (the refuter's record-style detector on 100 Hz frames), stuck % (ω = 0 while the plan moves), T 5–30 Hz |
| `st` | step to Ah at 0.5 s, hold to 7 s | overshoot %, settle to 5 % / 0.2°, hold ratio, slips, hunt |
| `c30` | ramp to Ah, 30 s constant setpoint | hunt (≥ 2 ω reversals at \|ω\| > 0.2 and ≥ 0.2° p2p in the last 20 s), mean error, slips, T 5–30 Hz |
| `rn30` | as c30 + **road noise: 15 T counts rms, band-limited 0.5–30 Hz (2nd-order Butterworth), applied as wheel torque** — the brief does not define "road noise 15 counts"; this definition is this scorer's (BELIEF on what was meant) | texture = T 5–30 Hz rms, wheel rate 5–30 Hz rms, error rms |
| `ov_lt400` / `lt511` / `lt1000` / `ov_fm2400` | the brief's override: hold Ah, a stiff hand (2000 T/deg, 30 T/(deg/s)) takes the wheel to 0 over 0.3 s from 2.5 s, **holds 1 s**, releases; word ramps with the grab, held, to 0 in 30 ms. `ov3_*` (bridge, §5.7): the same with the refuter's / E2's 3 s hold | **lurch** = max overshoot past the setpoint after release; droop 1 s after; I at release |
| `eng` | engage under load (the refuter's form): the hand holds the wheel at Ah, engage at 2.0 s with the measured angle sent, then held; hand released over 0.2 s from 2.3 s; ramp-in per column (33 / tick = 0.99 s; E2-A2-X 328 = 0.10 s) | droop (wheel behind the held command) |
| `cs` | co-steer (rev2-A's form): in a held curve a pure torque 0.5× the spring load IN the turn direction for 2 s, word +400, then released | droop after release |
| `tmo` / `tmos` | the fork stops; gp-0x69ae holds the last setpoint 510 ms, then the 0x7FFF sentinel with request 0xFF; tmo in a held turn, tmos mid-sinusoid (0.3 A at 0.2 Hz, stopped at the zero crossing = maximum rate) | excursion during the 510 ms, peak \|T\| after the sentinel, \|T\| from +0.25 s |
| `sen` / `dis` | 0xE4 fault sentinel / request drop in a held turn | \|T\| from +50 ms / +150 ms, excursion |
| `db` | dead band: setpoint creeps 0 → 2° at 0.2°/s | lag, slips, stuck % |
| `hard` | 0 → A in 0.3 s, hold 2 s, back in 0.3 s | 1.6–3 Hz wheel-rate rms / the command's own |

**Goal criteria this scorer can decide** (§0 fails table): tracking 0.95–1.05 (clean and replayed word), turn-hold ≥ 0.90
(synthetic a_lat ≤ 2.0 and real curves), no hunt / no 5–30 Hz texture above the harness's 2.0-count line, plus the brief's
release-lurch gate (8°, rev2-B's pre-registered bar). **Not decidable here:** dwell-then-jump ≤ V282 and hard-turn energy ≤
V282's (V282 is not simulable — counts and ratios are reported), ring ≤ 0.5 %, F7 = 0 and 20 Hz gain ≤ V295's (frequency
domain / on-car; the members carry no 20 Hz mode).

## 5. Results

### 5.1 Tracking on r71b's real paths, per member (vgr)

**clean**

| cand | 8-15 nom | 8-15 bc | 8-15 F_hi | 8-15 blJ | 15-22 nom | 15-22 bc | 15-22 F_hi | 15-22 blJ | >22 nom | >22 bc | >22 F_hi | >22 blJ | real-curve hold min (n) | dj events per 100 s (max snap) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P2 | 0.900 | 0.910 | 0.900 | 0.892 | 0.856 | 0.858 | 0.856 | 0.864 | 1.002 | 1.001 | 1.001 | 1.000 | 0.756 (14) | 7.91 (1.69) |
| F2 | 0.904 | 0.914 | 0.903 | 0.897 | 0.851 | 0.853 | 0.851 | 0.859 | 1.001 | 1.001 | 1.001 | 1.000 | 0.748 (14) | 7.58 (11.03) |
| D2a | 0.900 | 0.910 | 0.900 | 0.892 | 0.857 | 0.858 | 0.857 | 0.865 | 1.002 | 1.002 | 1.001 | 1.000 | 0.757 (14) | 7.91 (1.69) |
| B0r | 0.904 | 0.913 | 0.903 | 0.897 | 0.852 | 0.854 | 0.852 | 0.861 | 1.002 | 1.001 | 1.001 | 1.000 | 0.750 (14) | 7.58 (11.05) |
| E1-reset | 0.988 | 0.993 | 0.988 | 0.986 | 0.993 | 0.994 | 0.994 | 0.994 | 1.006 | 1.002 | 1.006 | 1.001 | 0.980 (14) | 8.40 (8.31) |
| E1-cal | 0.988 | 0.993 | 0.988 | 0.986 | 0.993 | 0.994 | 0.994 | 0.994 | 1.006 | 1.002 | 1.006 | 1.001 | 0.979 (14) | 8.24 (8.31) |
| E1-bleed | 0.988 | 0.993 | 0.988 | 0.986 | 0.993 | 0.994 | 0.994 | 0.994 | 1.006 | 1.002 | 1.006 | 1.001 | 0.980 (14) | 8.24 (8.31) |
| E1-freeze | 0.988 | 0.993 | 0.988 | 0.986 | 0.993 | 0.993 | 0.994 | 0.994 | 1.006 | 1.002 | 1.006 | 1.001 | 0.980 (14) | 8.24 (8.31) |
| E1-sched | 0.893 | 0.903 | 0.893 | 0.886 | 0.928 | 0.929 | 0.928 | 0.935 | 0.948 | 0.951 | 0.948 | 0.941 | 0.867 (14) | 7.25 (12.77) |
| E1-splitP | 0.902 | 0.909 | 0.902 | 0.898 | 0.856 | 0.858 | 0.857 | 0.865 | 0.967 | 0.968 | 0.967 | 0.962 | 0.788 (14) | 6.59 (14.65) |
| E2-R1 | 0.988 | 0.993 | 0.988 | 0.986 | 0.993 | 0.994 | 0.994 | 0.994 | 1.006 | 1.002 | 1.006 | 1.001 | 0.980 (14) | 7.82 (8.31) |
| E2-S | 0.988 | 0.993 | 0.988 | 0.986 | 0.993 | 0.994 | 0.994 | 0.994 | 1.006 | 1.001 | 1.006 | 1.001 | 0.979 (14) | 8.07 (8.31) |
| E2-A2 | 0.988 | 0.993 | 0.988 | 0.986 | 0.993 | 0.994 | 0.994 | 0.994 | 1.006 | 1.001 | 1.006 | 1.001 | 0.980 (14) | 8.57 (8.31) |
| E2-A3 | 0.988 | 0.993 | 0.988 | 0.986 | 0.993 | 0.994 | 0.994 | 0.994 | 1.006 | 1.001 | 1.006 | 1.001 | 0.980 (14) | 7.91 (8.31) |
| E2-A3-12k | 0.998 | 0.997 | 0.998 | 0.998 | 0.998 | 0.995 | 0.999 | 0.995 | 1.006 | 1.002 | 1.006 | 1.001 | 0.980 (14) | 8.07 (8.86) |
| E2-A2-X | 0.988 | 0.993 | 0.988 | 0.986 | 0.993 | 0.994 | 0.994 | 0.994 | 1.006 | 1.001 | 1.006 | 1.001 | 0.980 (14) | 8.24 (8.31) |
| E2-L | 0.988 | 0.993 | 0.988 | 0.986 | 0.993 | 0.994 | 0.994 | 0.994 | 1.006 | 1.001 | 1.006 | 1.001 | 0.979 (14) | 7.99 (8.31) |
| E2-K0 | 0.968 | 0.965 | 0.968 | 0.966 | 0.919 | 0.915 | 0.921 | 0.918 | 0.970 | 0.968 | 0.971 | 0.966 | 0.652 (14) | 2.64 (0.77) |
| G-P48d | 0.898 | 0.907 | 0.897 | 0.892 | 0.860 | 0.862 | 0.860 | 0.868 | 1.002 | 1.002 | 1.001 | 1.000 | 0.763 (14) | 7.82 (12.16) |
| G-P44d | 0.891 | 0.902 | 0.891 | 0.885 | 0.856 | 0.858 | 0.856 | 0.865 | 1.001 | 1.002 | 1.001 | 1.000 | 0.756 (14) | 7.17 (1.49) |
| G-P48 | 0.897 | 0.907 | 0.897 | 0.892 | 0.835 | 0.837 | 0.835 | 0.845 | 1.002 | 1.002 | 1.001 | 1.000 | 0.723 (14) | 7.25 (12.25) |
| G-P44 | 0.891 | 0.902 | 0.891 | 0.885 | 0.831 | 0.833 | 0.831 | 0.841 | 1.001 | 1.002 | 1.001 | 1.000 | 0.718 (14) | 6.92 (1.49) |
| G-F24 | 0.889 | 0.900 | 0.889 | 0.882 | 0.821 | 0.823 | 0.821 | 0.831 | 1.002 | 1.002 | 1.001 | 1.000 | 0.702 (14) | 5.77 (1.71) |
| G-F24d | 0.890 | 0.900 | 0.889 | 0.883 | 0.847 | 0.849 | 0.847 | 0.856 | 1.002 | 1.002 | 1.001 | 1.000 | 0.742 (14) | 5.52 (1.71) |
| G-A22 | 0.885 | 0.896 | 0.885 | 0.877 | 0.814 | 0.817 | 0.814 | 0.825 | 1.002 | 1.001 | 1.001 | 1.000 | 0.693 (14) | 6.67 (1.68) |
| G-A22d | 0.886 | 0.897 | 0.885 | 0.878 | 0.841 | 0.843 | 0.841 | 0.850 | 1.002 | 1.001 | 1.001 | 1.000 | 0.733 (14) | 6.42 (1.68) |
| G-P48L | 0.878 | 0.889 | 0.877 | 0.871 | 0.834 | 0.837 | 0.834 | 0.844 | 1.002 | 1.002 | 1.001 | 1.000 | 0.723 (14) | 5.60 (1.44) |
| G-P48k40 | 0.909 | 0.917 | 0.909 | 0.903 | 0.838 | 0.840 | 0.838 | 0.847 | 1.000 | 0.998 | 1.000 | 0.998 | 0.736 (14) | 4.94 (1.67) |
| H-A | 0.979 | 0.986 | 0.979 | 0.975 | 0.987 | 0.988 | 0.987 | 0.989 | 1.005 | 1.000 | 1.005 | 1.000 | 0.974 (14) | 7.66 (6.51) |
| H-B | 0.979 | 0.986 | 0.978 | 0.977 | 0.988 | 0.989 | 0.989 | 0.990 | 1.006 | 1.001 | 1.006 | 1.001 | 0.980 (14) | 7.82 (6.94) |

**r71b torque word replayed**

| cand | 8-15 nom | 8-15 bc | 8-15 F_hi | 8-15 blJ | 15-22 nom | 15-22 bc | 15-22 F_hi | 15-22 blJ | >22 nom | >22 bc | >22 F_hi | >22 blJ | real-curve hold min (n) | dj events per 100 s (max snap) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| P2 | 0.900 | 0.909 | 0.899 | 0.892 | 0.855 | 0.857 | 0.855 | 0.864 | 1.001 | 1.001 | 1.001 | 1.000 | 0.756 (14) | 8.15 (12.83) |
| F2 | 0.903 | 0.913 | 0.903 | 0.896 | 0.850 | 0.852 | 0.850 | 0.859 | 1.001 | 1.001 | 1.001 | 1.000 | 0.748 (14) | 7.66 (13.77) |
| D2a | 0.899 | 0.909 | 0.899 | 0.892 | 0.856 | 0.858 | 0.856 | 0.865 | 1.001 | 1.001 | 1.001 | 1.000 | 0.757 (14) | 8.15 (12.83) |
| B0r | 0.903 | 0.913 | 0.903 | 0.896 | 0.852 | 0.853 | 0.852 | 0.860 | 1.001 | 1.001 | 1.001 | 1.000 | 0.750 (14) | 7.99 (13.77) |
| E1-reset | 0.986 | 0.991 | 0.986 | 0.985 | 0.992 | 0.991 | 0.992 | 0.991 | 1.005 | 1.001 | 1.005 | 1.000 | 0.980 (14) | 8.57 (6.09) |
| E1-cal | 0.986 | 0.991 | 0.986 | 0.985 | 0.992 | 0.991 | 0.992 | 0.991 | 1.005 | 1.001 | 1.005 | 1.001 | 0.979 (14) | 8.40 (6.10) |
| E1-bleed | 0.758 | 0.762 | 0.757 | 0.752 | 0.741 | 0.739 | 0.741 | 0.744 | 0.835 | 0.833 | 0.836 | 0.829 | 0.711 (14) | 10.13 (6.07) |
| E1-freeze | 0.982 | 0.990 | 0.982 | 0.984 | 0.985 | 0.984 | 0.986 | 0.984 | 1.001 | 0.997 | 1.001 | 0.997 | 0.979 (14) | 8.32 (1.56) |
| E1-sched | 0.893 | 0.903 | 0.892 | 0.885 | 0.927 | 0.929 | 0.928 | 0.935 | 0.948 | 0.951 | 0.948 | 0.941 | 0.867 (14) | 7.25 (12.53) |
| E1-splitP | 0.902 | 0.909 | 0.901 | 0.897 | 0.856 | 0.857 | 0.856 | 0.865 | 0.967 | 0.968 | 0.967 | 0.961 | 0.788 (14) | 6.51 (14.38) |
| E2-R1 | 0.986 | 0.991 | 0.986 | 0.985 | 0.992 | 0.991 | 0.992 | 0.991 | 1.005 | 1.001 | 1.005 | 1.000 | 0.980 (14) | 8.32 (6.10) |
| E2-S | 0.980 | 0.986 | 0.980 | 0.980 | 0.986 | 0.984 | 0.986 | 0.984 | 0.999 | 0.996 | 0.999 | 0.996 | 0.979 (14) | 8.07 (5.72) |
| E2-A2 | 0.986 | 0.991 | 0.986 | 0.985 | 0.992 | 0.991 | 0.992 | 0.991 | 1.005 | 1.001 | 1.005 | 1.000 | 0.980 (14) | 8.73 (6.09) |
| E2-A3 | 0.986 | 0.991 | 0.986 | 0.985 | 0.992 | 0.991 | 0.992 | 0.991 | 1.005 | 1.001 | 1.005 | 1.000 | 0.979 (14) | 8.40 (6.10) |
| E2-A3-12k | 0.995 | 0.995 | 0.995 | 0.996 | 0.993 | 0.991 | 0.994 | 0.991 | 1.005 | 1.001 | 1.005 | 1.000 | 0.980 (14) | 8.40 (6.16) |
| E2-A2-X | 0.986 | 0.991 | 0.986 | 0.986 | 0.992 | 0.991 | 0.992 | 0.991 | 1.005 | 1.001 | 1.005 | 1.000 | 0.980 (14) | 8.48 (6.16) |
| E2-L | 0.941 | 0.945 | 0.941 | 0.938 | 0.959 | 0.958 | 0.959 | 0.958 | 0.994 | 0.990 | 0.994 | 0.990 | 0.977 (14) | 7.99 (1.69) |
| E2-K0 | 0.967 | 0.965 | 0.968 | 0.966 | 0.919 | 0.915 | 0.920 | 0.918 | 0.970 | 0.968 | 0.971 | 0.966 | 0.652 (14) | 2.64 (0.77) |
| G-P48d | 0.897 | 0.907 | 0.897 | 0.891 | 0.859 | 0.861 | 0.859 | 0.868 | 1.001 | 1.001 | 1.001 | 1.000 | 0.763 (14) | 7.58 (13.02) |
| G-P44d | 0.891 | 0.901 | 0.890 | 0.884 | 0.856 | 0.857 | 0.855 | 0.864 | 1.001 | 1.001 | 1.001 | 1.000 | 0.756 (14) | 7.08 (1.50) |
| G-P48 | 0.897 | 0.906 | 0.896 | 0.891 | 0.834 | 0.836 | 0.834 | 0.844 | 1.001 | 1.001 | 1.001 | 1.000 | 0.723 (14) | 7.25 (13.11) |
| G-P44 | 0.891 | 0.901 | 0.891 | 0.884 | 0.830 | 0.832 | 0.830 | 0.840 | 1.001 | 1.001 | 1.001 | 1.000 | 0.718 (14) | 6.84 (1.50) |
| G-F24 | 0.889 | 0.899 | 0.888 | 0.882 | 0.820 | 0.822 | 0.820 | 0.830 | 1.001 | 1.001 | 1.001 | 1.000 | 0.702 (14) | 5.77 (1.69) |
| G-F24d | 0.889 | 0.900 | 0.889 | 0.882 | 0.846 | 0.848 | 0.846 | 0.855 | 1.001 | 1.001 | 1.001 | 1.000 | 0.742 (14) | 5.44 (1.69) |
| G-A22 | 0.885 | 0.896 | 0.884 | 0.877 | 0.814 | 0.816 | 0.814 | 0.824 | 1.001 | 1.001 | 1.001 | 1.000 | 0.693 (14) | 6.67 (12.15) |
| G-A22d | 0.885 | 0.896 | 0.885 | 0.877 | 0.840 | 0.842 | 0.841 | 0.850 | 1.001 | 1.001 | 1.001 | 1.000 | 0.733 (14) | 6.34 (12.26) |
| G-P48L | 0.877 | 0.888 | 0.877 | 0.870 | 0.834 | 0.836 | 0.834 | 0.844 | 1.001 | 1.001 | 1.001 | 1.000 | 0.723 (14) | 5.35 (1.43) |
| G-P48k40 | 0.908 | 0.917 | 0.908 | 0.903 | 0.837 | 0.839 | 0.837 | 0.847 | 1.000 | 0.998 | 1.000 | 0.997 | 0.736 (14) | 5.11 (13.48) |
| H-A | 0.929 | 0.933 | 0.929 | 0.925 | 0.947 | 0.947 | 0.947 | 0.948 | 0.989 | 0.986 | 0.990 | 0.985 | 0.970 (14) | 7.58 (1.89) |
| H-B | 0.935 | 0.940 | 0.935 | 0.933 | 0.952 | 0.952 | 0.953 | 0.953 | 0.992 | 0.989 | 0.992 | 0.988 | 0.973 (14) | 7.99 (1.79) |

**Reading (EVIDENCE: simulation).** The ICL-raising columns that keep the hard freeze at 512 lose ≤ 0.007 to the replayed
word (E2-S's opposing-hand freeze at 300: −0.006…−0.009, as E2 measured). Every column that DRAINS the I on the word —
E1-bleed (256–512 band), E2-L (leak above 512), H-A / H-B (bleed above 512) — loses 0.04–0.25: the resting hand reads
> 512 on ~1 % of frames, so a drain keyed to the word empties the very hold the raised ICL added.

### 5.2 Per-band detail (vgr; worst over the four members and the band's speeds)

**Synthetic turn-hold, a_lat <= 2.0 m/s^2 (min hold ratio; < 8 m/s: the A_TURN hold)**

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | 0.988 | 0.901 | 0.925 | 0.778 | 0.732 | 0.975 |
| F2 | 0.987 | 0.896 | 0.932 | 0.770 | 0.722 | 0.974 |
| D2a | 0.988 | 0.901 | 0.925 | 0.778 | 0.733 | 0.977 |
| B0r | 0.987 | 0.896 | 0.932 | 0.770 | 0.725 | 0.975 |
| E1-reset | 0.998 | 0.993 | 0.992 | 0.993 | 0.985 | 0.978 |
| E1-cal | 0.998 | 0.993 | 0.992 | 0.993 | 0.986 | 0.976 |
| E1-bleed | 0.998 | 0.993 | 0.993 | 0.993 | 0.986 | 0.976 |
| E1-freeze | 0.998 | 0.996 | 0.992 | 0.993 | 0.986 | 0.976 |
| E1-sched | 0.998 | 0.887 | 0.897 | 0.919 | 0.895 | 0.978 |
| E1-splitP | 0.968 | 0.896 | 0.878 | 0.787 | 0.755 | 0.921 |
| E2-R1 | 0.998 | 0.996 | 0.992 | 0.993 | 0.986 | 0.976 |
| E2-S | 0.998 | 0.996 | 0.993 | 0.993 | 0.985 | 0.980 |
| E2-A2 | 0.998 | 0.996 | 0.992 | 0.993 | 0.986 | 0.976 |
| E2-A3 | 0.988 | 0.993 | 0.992 | 0.993 | 0.985 | 0.975 |
| E2-A3-12k | 0.988 | 0.996 | 0.993 | 0.993 | 0.985 | 0.976 |
| E2-A2-X | 0.998 | 0.996 | 0.993 | 0.993 | 0.986 | 0.979 |
| E2-L | 0.998 | 0.996 | 0.992 | 0.993 | 0.986 | 0.976 |
| E2-K0 | 0.999 | 0.998 | 0.996 | 0.993 | 0.989 | 0.984 |
| G-P48d | 0.979 | 0.900 | 0.925 | 0.779 | 0.738 | 0.973 |
| G-P44d | 0.978 | 0.895 | 0.916 | 0.774 | 0.732 | 0.975 |
| G-P48 | 0.979 | 0.900 | 0.923 | 0.744 | 0.690 | 0.975 |
| G-P44 | 0.978 | 0.895 | 0.917 | 0.733 | 0.684 | 0.974 |
| G-F24 | 0.975 | 0.885 | 0.916 | 0.726 | 0.670 | 0.981 |
| G-F24d | 0.975 | 0.885 | 0.916 | 0.761 | 0.716 | 0.981 |
| G-A22 | 0.977 | 0.877 | 0.911 | 0.714 | 0.660 | 0.981 |
| G-A22d | 0.977 | 0.876 | 0.912 | 0.752 | 0.708 | 0.980 |
| G-P48L | 0.979 | 0.886 | 0.902 | 0.733 | 0.688 | 0.976 |
| G-P48k40 | 0.988 | 0.909 | 0.932 | 0.760 | 0.702 | 0.976 |
| H-A | 0.999 | 0.991 | 0.993 | 0.993 | 0.981 | 0.977 |
| H-B | 0.998 | 0.994 | 0.991 | 0.993 | 0.986 | 0.972 |

**Synthetic turn-hold at a_lat 2.5 m/s^2 (r71b's sustained maximum at <= 18 m/s)**

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | - | 0.893 | 0.898 | 0.741 | 0.689 | 0.924 |
| F2 | - | 0.896 | 0.897 | 0.734 | 0.680 | 0.920 |
| D2a | - | 0.893 | 0.898 | 0.741 | 0.690 | 0.924 |
| B0r | - | 0.896 | 0.896 | 0.734 | 0.681 | 0.921 |
| E1-reset | - | 0.993 | 0.992 | 0.993 | 0.983 | 0.978 |
| E1-cal | - | 0.993 | 0.992 | 0.993 | 0.983 | 0.976 |
| E1-bleed | - | 0.993 | 0.993 | 0.993 | 0.983 | 0.976 |
| E1-freeze | - | 0.996 | 0.992 | 0.993 | 0.983 | 0.976 |
| E1-sched | - | 0.874 | 0.880 | 0.874 | 0.831 | 0.973 |
| E1-splitP | - | 0.896 | 0.869 | 0.775 | 0.736 | 0.882 |
| E2-R1 | - | 0.996 | 0.992 | 0.993 | 0.983 | 0.976 |
| E2-S | - | 0.996 | 0.993 | 0.993 | 0.983 | 0.980 |
| E2-A2 | - | 0.996 | 0.992 | 0.993 | 0.983 | 0.976 |
| E2-A3 | - | 0.993 | 0.992 | 0.993 | 0.983 | 0.975 |
| E2-A3-12k | - | 0.996 | 0.993 | 0.993 | 0.985 | 0.976 |
| E2-A2-X | - | 0.996 | 0.993 | 0.993 | 0.983 | 0.979 |
| E2-L | - | 0.996 | 0.992 | 0.993 | 0.983 | 0.976 |
| E2-K0 | - | 0.998 | 0.996 | 0.993 | 0.989 | 0.984 |
| G-P48d | - | 0.898 | 0.891 | 0.744 | 0.698 | 0.927 |
| G-P44d | - | 0.885 | 0.885 | 0.736 | 0.689 | 0.922 |
| G-P48 | - | 0.898 | 0.881 | 0.699 | 0.640 | 0.920 |
| G-P44 | - | 0.884 | 0.878 | 0.685 | 0.632 | 0.919 |
| G-F24 | - | 0.883 | 0.871 | 0.675 | 0.615 | 0.913 |
| G-F24d | - | 0.884 | 0.878 | 0.720 | 0.671 | 0.920 |
| G-A22 | - | 0.876 | 0.861 | 0.664 | 0.604 | 0.912 |
| G-A22d | - | 0.876 | 0.871 | 0.706 | 0.662 | 0.919 |
| G-P48L | - | 0.864 | 0.857 | 0.685 | 0.638 | 0.920 |
| G-P48k40 | - | 0.909 | 0.900 | 0.718 | 0.653 | 0.922 |
| H-A | - | 0.985 | 0.993 | 0.993 | 0.924 | 0.977 |
| H-B | - | 0.984 | 0.991 | 0.993 | 0.929 | 0.972 |

**In-phase wire gain, +-1 deg at 0.2 Hz (min)**

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | 0.88 | 1.00 | 0.88 | 0.86 | 0.86 | 0.96 |
| F2 | 0.89 | 1.02 | 0.88 | 0.84 | 0.84 | 0.96 |
| D2a | 0.88 | 1.00 | 0.87 | 0.85 | 0.86 | 0.97 |
| B0r | 0.86 | 1.02 | 0.88 | 0.84 | 0.84 | 0.96 |
| E1-reset | 0.88 | 1.00 | 0.88 | 0.86 | 0.86 | 0.96 |
| E1-cal | 0.88 | 1.00 | 0.87 | 0.86 | 0.86 | 0.96 |
| E1-bleed | 0.88 | 1.00 | 0.87 | 0.86 | 0.86 | 0.96 |
| E1-freeze | 0.88 | 1.00 | 0.87 | 0.86 | 0.86 | 0.96 |
| E1-sched | 0.88 | 1.00 | 0.87 | 0.85 | 0.86 | 0.96 |
| E1-splitP | 0.62 | 0.91 | 0.81 | 0.83 | 0.84 | 0.92 |
| E2-R1 | 0.88 | 1.00 | 0.90 | 0.85 | 0.86 | 0.96 |
| E2-S | 0.88 | 1.00 | 0.89 | 0.87 | 0.86 | 0.96 |
| E2-A2 | 0.88 | 1.00 | 0.87 | 0.86 | 0.86 | 0.96 |
| E2-A3 | 0.88 | 1.00 | 0.88 | 0.86 | 0.86 | 0.96 |
| E2-A3-12k | 0.88 | 1.00 | 0.88 | 0.87 | 0.86 | 0.96 |
| E2-A2-X | 0.88 | 1.00 | 0.88 | 0.85 | 0.86 | 0.96 |
| E2-L | 0.88 | 1.00 | 0.88 | 0.85 | 0.86 | 0.96 |
| E2-K0 | -0.07 | -0.05 | -0.07 | -0.01 | 0.28 | 0.58 |
| G-P48d | 1.00 | 1.05 | 0.70 | 0.83 | 0.89 | 0.97 |
| G-P44d | 0.91 | 1.01 | 0.64 | 0.80 | 0.85 | 0.96 |
| G-P48 | 1.00 | 1.03 | 0.69 | 0.75 | 0.73 | 0.96 |
| G-P44 | 0.91 | 1.01 | 0.66 | 0.68 | 0.70 | 0.96 |
| G-F24 | 0.86 | 1.00 | 0.58 | 0.56 | 0.64 | 0.94 |
| G-F24d | 0.86 | 1.01 | 0.56 | 0.75 | 0.82 | 0.96 |
| G-A22 | 0.80 | 0.99 | 0.51 | 0.47 | 0.60 | 0.93 |
| G-A22d | 0.80 | 0.99 | 0.46 | 0.73 | 0.80 | 0.96 |
| G-P48L | 0.99 | 0.81 | 0.11 | 0.49 | 0.72 | 0.96 |
| G-P48k40 | 0.56 | 0.94 | 0.56 | 0.57 | 0.59 | 0.89 |
| H-A | 0.84 | 0.95 | 0.75 | 0.79 | 0.81 | 0.95 |
| H-B | 0.93 | 1.02 | 0.88 | 0.84 | 0.84 | 0.96 |

**Release lurch, light hand (max over words 400 / 511 / 1000, deg)**

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | 11.9 | 9.8 | 10.9 | 8.1 | 4.3 | 3.6 |
| F2 | 11.7 | 9.6 | 10.9 | 8.1 | 4.3 | 3.6 |
| D2a | 11.9 | 9.8 | 10.9 | 8.1 | 4.3 | 3.6 |
| B0r | 11.7 | 9.6 | 10.9 | 8.1 | 4.3 | 3.6 |
| E1-reset | 23.1 | 24.0 | 24.3 | 13.3 | 8.3 | 4.2 |
| E1-cal | 23.1 | 24.0 | 24.3 | 13.3 | 8.3 | 4.2 |
| E1-bleed | 17.2 | 3.8 | 0.6 | 0.2 | 0.1 | 0.1 |
| E1-freeze | 23.1 | 11.8 | 4.5 | 2.3 | 1.2 | 0.6 |
| E1-sched | 14.8 | 11.1 | 9.5 | 8.5 | 7.4 | 4.1 |
| E1-splitP | 15.0 | 9.9 | 6.9 | 5.2 | 2.8 | 2.3 |
| E2-R1 | 23.1 | 24.0 | 24.3 | 13.3 | 8.3 | 4.2 |
| E2-S | 23.1 | 11.1 | 4.3 | 2.1 | 1.2 | 0.6 |
| E2-A2 | 15.5 | 5.8 | 2.6 | 2.3 | 1.1 | 1.0 |
| E2-A3 | 12.0 | 5.8 | 2.6 | 2.3 | 1.1 | 1.0 |
| E2-A3-12k | 12.0 | 5.8 | 2.6 | 2.3 | 1.1 | 1.0 |
| E2-A2-X | 15.5 | 5.8 | 2.6 | 2.3 | 1.1 | 1.0 |
| E2-L | 23.1 | 24.0 | 24.3 | 13.3 | 8.3 | 4.1 |
| E2-K0 | 51.7 | 20.0 | 5.9 | 2.7 | 1.5 | 0.9 |
| G-P48d | 7.7 | 8.2 | 10.0 | 7.3 | 3.9 | 3.4 |
| G-P44d | 8.1 | 8.7 | 10.6 | 7.6 | 4.0 | 3.5 |
| G-P48 | 7.7 | 8.2 | 10.1 | 7.6 | 4.1 | 3.5 |
| G-P44 | 8.1 | 8.7 | 10.5 | 7.9 | 4.3 | 3.6 |
| G-F24 | 8.1 | 9.0 | 10.9 | 8.2 | 4.4 | 3.5 |
| G-F24d | 8.1 | 9.0 | 11.0 | 7.9 | 4.2 | 3.6 |
| G-A22 | 8.9 | 9.8 | 11.8 | 8.7 | 4.6 | 3.5 |
| G-A22d | 8.9 | 9.8 | 11.9 | 8.5 | 4.4 | 3.7 |
| G-P48L | 7.7 | 8.7 | 10.9 | 8.1 | 4.2 | 3.5 |
| G-P48k40 | 9.9 | 8.1 | 9.6 | 7.3 | 4.1 | 2.9 |
| H-A | 19.5 | 22.0 | 22.2 | 11.7 | 7.4 | 3.7 |
| H-B | 19.3 | 19.8 | 20.8 | 12.6 | 7.7 | 4.0 |

**Release lurch, firm hand 2400 (deg)**

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | 11.5 | 7.9 | 3.4 | 1.7 | 0.9 | 0.4 |
| F2 | 11.4 | 7.6 | 3.6 | 1.6 | 0.8 | 0.4 |
| D2a | 11.5 | 7.9 | 3.4 | 1.7 | 0.9 | 0.4 |
| B0r | 11.4 | 7.6 | 3.6 | 1.6 | 0.8 | 0.4 |
| E1-reset | 18.7 | 4.2 | 0.7 | 0.2 | 0.1 | 0.2 |
| E1-cal | 22.2 | 8.4 | 3.4 | 1.7 | 0.9 | 0.4 |
| E1-bleed | 18.6 | 4.1 | 0.7 | 0.2 | 0.1 | 0.2 |
| E1-freeze | 18.4 | 4.1 | 0.7 | 0.2 | 0.1 | 0.2 |
| E1-sched | 13.9 | 4.2 | 0.7 | 0.2 | 0.1 | 0.2 |
| E1-splitP | 14.6 | 6.4 | 0.0 | -0.0 | 0.0 | 0.0 |
| E2-R1 | 22.2 | 8.4 | 3.4 | 1.7 | 0.9 | 0.4 |
| E2-S | 22.0 | 8.2 | 3.3 | 1.6 | 0.8 | 0.4 |
| E2-A2 | 14.1 | 4.7 | 2.3 | 1.7 | 0.6 | 0.4 |
| E2-A3 | 10.9 | 4.7 | 2.3 | 1.7 | 0.6 | 0.4 |
| E2-A3-12k | 10.9 | 4.7 | 2.3 | 1.7 | 0.6 | 0.4 |
| E2-A2-X | 14.1 | 4.7 | 2.3 | 1.5 | 0.6 | 0.4 |
| E2-L | 18.7 | 4.2 | 0.7 | 0.2 | 0.1 | 0.2 |
| E2-K0 | 13.9 | 5.1 | 0.3 | -0.0 | 0.0 | 0.1 |
| G-P48d | 7.4 | 6.2 | 2.9 | 1.4 | 0.7 | 0.4 |
| G-P44d | 7.7 | 6.5 | 2.9 | 1.4 | 0.7 | 0.4 |
| G-P48 | 7.4 | 6.2 | 2.9 | 1.4 | 0.7 | 0.4 |
| G-P44 | 7.7 | 6.5 | 2.8 | 1.4 | 0.7 | 0.4 |
| G-F24 | 7.7 | 6.4 | 2.9 | 1.3 | 0.6 | 0.4 |
| G-F24d | 7.7 | 6.4 | 2.9 | 1.3 | 0.7 | 0.4 |
| G-A22 | 8.5 | 6.9 | 3.1 | 1.3 | 0.6 | 0.4 |
| G-A22d | 8.5 | 6.9 | 3.1 | 1.3 | 0.7 | 0.4 |
| G-P48L | 7.4 | 6.3 | 2.5 | 1.3 | 0.7 | 0.4 |
| G-P48k40 | 9.6 | 6.0 | 2.4 | 1.1 | 0.4 | 0.3 |
| H-A | 15.4 | 2.8 | 0.6 | 0.2 | 0.1 | 0.2 |
| H-B | 16.8 | 3.3 | 0.8 | 0.3 | 0.1 | 0.2 |

**Engage under load with the measured angle sent: droop (max deg)**

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | 8.06 | 6.26 | 5.29 | 3.34 | 2.60 | 1.00 |
| F2 | 8.06 | 6.41 | 5.12 | 3.35 | 2.62 | 1.02 |
| D2a | 8.06 | 6.26 | 5.29 | 3.34 | 2.60 | 1.00 |
| B0r | 8.06 | 6.41 | 5.12 | 3.35 | 2.63 | 1.02 |
| E1-reset | 8.06 | 6.26 | 5.28 | 3.34 | 2.60 | 1.00 |
| E1-cal | 8.06 | 6.26 | 5.29 | 3.34 | 2.60 | 1.00 |
| E1-bleed | 8.06 | 6.26 | 5.29 | 3.34 | 2.60 | 1.00 |
| E1-freeze | 8.06 | 6.27 | 5.29 | 3.34 | 2.60 | 1.00 |
| E1-sched | 8.06 | 6.27 | 5.29 | 3.34 | 2.60 | 1.01 |
| E1-splitP | 6.08 | 4.91 | 4.41 | 2.84 | 2.24 | 0.83 |
| E2-R1 | 8.06 | 6.26 | 5.29 | 3.34 | 2.60 | 1.00 |
| E2-S | 8.06 | 6.27 | 5.29 | 3.34 | 2.60 | 1.01 |
| E2-A2 | 8.06 | 6.26 | 5.29 | 3.34 | 2.60 | 1.00 |
| E2-A3 | 8.06 | 6.26 | 5.29 | 3.33 | 2.60 | 1.01 |
| E2-A3-12k | 8.06 | 6.26 | 5.29 | 3.34 | 2.60 | 1.01 |
| E2-A2-X | 5.30 | 4.32 | 3.95 | 2.57 | 2.06 | 0.77 |
| E2-L | 8.06 | 6.26 | 5.29 | 3.34 | 2.60 | 1.00 |
| E2-K0 | 8.06 | 6.26 | 5.29 | 3.34 | 2.60 | 1.01 |
| G-P48d | 7.62 | 6.03 | 4.90 | 3.23 | 2.51 | 0.97 |
| G-P44d | 8.03 | 6.17 | 5.18 | 3.33 | 2.56 | 0.99 |
| G-P48 | 7.62 | 6.04 | 4.89 | 3.34 | 2.67 | 1.01 |
| G-P44 | 8.02 | 6.17 | 5.17 | 3.43 | 2.73 | 1.03 |
| G-F24 | 8.42 | 6.55 | 5.23 | 3.51 | 2.78 | 1.06 |
| G-F24d | 8.42 | 6.55 | 5.23 | 3.42 | 2.63 | 1.02 |
| G-A22 | 9.17 | 6.89 | 5.48 | 3.63 | 2.85 | 1.08 |
| G-A22d | 9.17 | 6.89 | 5.47 | 3.55 | 2.70 | 1.05 |
| G-P48L | 7.62 | 5.93 | 5.38 | 3.52 | 2.71 | 1.01 |
| G-P48k40 | 6.88 | 5.79 | 4.66 | 3.19 | 2.60 | 0.99 |
| H-A | 8.39 | 6.51 | 5.48 | 3.45 | 2.65 | 1.06 |
| H-B | 7.89 | 6.29 | 5.01 | 3.29 | 2.60 | 1.01 |

**Co-steer release droop (max deg)**

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | 2.71 | 2.40 | 2.21 | 1.47 | 1.18 | 0.43 |
| F2 | 2.77 | 2.47 | 2.12 | 1.49 | 1.20 | 0.44 |
| D2a | 2.71 | 2.40 | 2.21 | 1.47 | 1.18 | 0.43 |
| B0r | 2.77 | 2.46 | 2.12 | 1.48 | 1.20 | 0.44 |
| E1-reset | 2.72 | 2.40 | 2.21 | 1.47 | 1.18 | 0.43 |
| E1-cal | 2.71 | 2.40 | 2.21 | 1.47 | 1.18 | 0.43 |
| E1-bleed | 4.21 | 3.60 | 3.44 | 2.32 | 1.95 | 0.75 |
| E1-freeze | 1.09 | 1.29 | 0.48 | 0.25 | 0.20 | 0.11 |
| E1-sched | 2.71 | 2.40 | 2.21 | 1.47 | 1.18 | 0.43 |
| E1-splitP | 2.50 | 1.91 | 1.81 | 1.22 | 0.99 | 0.34 |
| E2-R1 | 2.71 | 2.40 | 2.21 | 1.47 | 1.18 | 0.43 |
| E2-S | 1.10 | 1.30 | 0.47 | 0.25 | 0.20 | 0.11 |
| E2-A2 | 2.70 | 2.41 | 2.21 | 1.47 | 1.18 | 0.43 |
| E2-A3 | 2.71 | 2.40 | 2.21 | 1.47 | 1.18 | 0.43 |
| E2-A3-12k | 2.71 | 2.40 | 2.21 | 1.47 | 1.19 | 0.43 |
| E2-A2-X | 2.71 | 2.39 | 2.20 | 1.47 | 1.18 | 0.43 |
| E2-L | 2.70 | 2.41 | 2.21 | 1.47 | 1.18 | 0.43 |
| E2-K0 | 2.77 | 2.20 | 1.74 | 1.07 | 0.92 | 0.33 |
| G-P48d | 2.76 | 2.26 | 1.99 | 1.40 | 1.12 | 0.42 |
| G-P44d | 2.80 | 2.33 | 2.14 | 1.46 | 1.15 | 0.43 |
| G-P48 | 2.75 | 2.25 | 1.99 | 1.47 | 1.20 | 0.44 |
| G-P44 | 2.80 | 2.34 | 2.15 | 1.52 | 1.24 | 0.45 |
| G-F24 | 3.13 | 2.51 | 2.18 | 1.56 | 1.28 | 0.45 |
| G-F24d | 3.14 | 2.51 | 2.17 | 1.53 | 1.18 | 0.44 |
| G-A22 | 3.21 | 2.69 | 2.32 | 1.63 | 1.32 | 0.47 |
| G-A22d | 3.21 | 2.69 | 2.31 | 1.60 | 1.23 | 0.45 |
| G-P48L | 2.76 | 2.31 | 2.25 | 1.57 | 1.23 | 0.44 |
| G-P48k40 | 2.77 | 2.18 | 1.89 | 1.37 | 1.13 | 0.42 |
| H-A | 2.92 | 2.47 | 2.32 | 1.54 | 1.14 | 0.45 |
| H-B | 2.71 | 2.40 | 2.04 | 1.45 | 1.18 | 0.43 |

### 5.3 Small corrections and stick-slip (vgr)

**Dwell-then-jump events, +-1 deg at 0.2 + 0.5 Hz, sum over members and speeds**

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | 112 | 31 | 129 | 68 | 0 | 0 |
| F2 | 115 | 23 | 129 | 74 | 0 | 0 |
| D2a | 113 | 30 | 134 | 68 | 0 | 0 |
| B0r | 116 | 23 | 135 | 76 | 0 | 0 |
| E1-reset | 118 | 30 | 126 | 68 | 0 | 0 |
| E1-cal | 113 | 31 | 124 | 68 | 0 | 0 |
| E1-bleed | 115 | 30 | 128 | 68 | 0 | 0 |
| E1-freeze | 117 | 30 | 129 | 67 | 0 | 0 |
| E1-sched | 116 | 30 | 128 | 68 | 0 | 0 |
| E1-splitP | 77 | 3 | 104 | 0 | 0 | 0 |
| E2-R1 | 115 | 30 | 123 | 69 | 0 | 0 |
| E2-S | 115 | 30 | 128 | 67 | 0 | 0 |
| E2-A2 | 117 | 30 | 130 | 66 | 0 | 0 |
| E2-A3 | 119 | 30 | 130 | 69 | 0 | 0 |
| E2-A3-12k | 113 | 31 | 127 | 69 | 0 | 0 |
| E2-A2-X | 115 | 30 | 123 | 68 | 0 | 0 |
| E2-L | 114 | 29 | 125 | 67 | 0 | 0 |
| E2-K0 | 46 | 45 | 169 | 49 | 0 | 0 |
| G-P48d | 113 | 28 | 129 | 67 | 0 | 0 |
| G-P44d | 119 | 35 | 131 | 81 | 0 | 0 |
| G-P48 | 113 | 26 | 131 | 100 | 16 | 0 |
| G-P44 | 119 | 34 | 134 | 110 | 28 | 0 |
| G-F24 | 102 | 45 | 118 | 106 | 43 | 0 |
| G-F24d | 108 | 45 | 118 | 82 | 0 | 0 |
| G-A22 | 101 | 47 | 113 | 101 | 56 | 0 |
| G-A22d | 101 | 46 | 113 | 97 | 2 | 0 |
| G-P48L | 110 | 41 | 72 | 105 | 30 | 0 |
| G-P48k40 | 106 | 27 | 118 | 72 | 5 | 0 |
| H-A | 120 | 41 | 140 | 104 | 2 | 0 |
| H-B | 114 | 25 | 133 | 75 | 0 | 0 |

**Largest dwell-then-jump snap, +-1 deg sinusoids (deg)**

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | 2.80 | 1.74 | 1.53 | 1.10 | 0.00 | 0.00 |
| F2 | 2.75 | 1.65 | 1.48 | 1.08 | 0.00 | 0.00 |
| D2a | 2.80 | 1.75 | 1.49 | 1.10 | 0.00 | 0.00 |
| B0r | 2.74 | 1.66 | 1.58 | 1.07 | 0.00 | 0.00 |
| E1-reset | 2.80 | 1.74 | 1.48 | 1.11 | 0.00 | 0.00 |
| E1-cal | 2.80 | 1.74 | 1.48 | 1.11 | 0.00 | 0.00 |
| E1-bleed | 2.79 | 1.75 | 1.49 | 1.11 | 0.00 | 0.00 |
| E1-freeze | 2.80 | 1.74 | 1.49 | 1.11 | 0.00 | 0.00 |
| E1-sched | 2.80 | 1.75 | 1.49 | 1.10 | 0.00 | 0.00 |
| E1-splitP | 1.76 | 1.17 | 1.12 | 0.00 | 0.00 | 0.00 |
| E2-R1 | 2.80 | 1.74 | 1.49 | 1.10 | 0.00 | 0.00 |
| E2-S | 2.79 | 1.74 | 1.48 | 1.11 | 0.00 | 0.00 |
| E2-A2 | 2.79 | 1.75 | 1.48 | 1.11 | 0.00 | 0.00 |
| E2-A3 | 2.80 | 1.74 | 1.49 | 1.11 | 0.00 | 0.00 |
| E2-A3-12k | 2.80 | 1.74 | 1.48 | 1.11 | 0.00 | 0.00 |
| E2-A2-X | 2.80 | 1.75 | 1.49 | 1.11 | 0.00 | 0.00 |
| E2-L | 2.81 | 1.61 | 1.49 | 1.10 | 0.00 | 0.00 |
| E2-K0 | 0.94 | 0.77 | 0.58 | 0.54 | 0.00 | 0.00 |
| G-P48d | 2.70 | 1.61 | 1.39 | 1.07 | 0.00 | 0.00 |
| G-P44d | 2.75 | 1.69 | 1.35 | 1.19 | 0.00 | 0.00 |
| G-P48 | 2.68 | 1.60 | 1.44 | 1.10 | 0.85 | 0.00 |
| G-P44 | 2.75 | 1.68 | 1.39 | 1.05 | 0.82 | 0.00 |
| G-F24 | 2.71 | 1.72 | 1.37 | 0.99 | 0.75 | 0.00 |
| G-F24d | 2.72 | 1.73 | 1.37 | 1.12 | 0.00 | 0.00 |
| G-A22 | 2.69 | 1.74 | 1.40 | 0.92 | 0.72 | 0.00 |
| G-A22d | 2.69 | 1.65 | 1.39 | 1.08 | 0.83 | 0.00 |
| G-P48L | 2.71 | 1.63 | 1.11 | 0.92 | 0.82 | 0.00 |
| G-P48k40 | 2.06 | 1.30 | 1.24 | 0.97 | 0.64 | 0.00 |
| H-A | 2.79 | 1.72 | 1.39 | 1.19 | 0.88 | 0.00 |
| H-B | 2.74 | 1.76 | 1.52 | 1.07 | 0.00 | 0.00 |

**In-phase wire gain, +-0.3 deg at 0.2 Hz (min)**

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | 0.00 | 0.31 | -0.36 | 0.12 | 0.78 | 1.01 |
| F2 | 0.00 | 0.54 | -0.35 | -0.05 | 0.78 | 1.01 |
| D2a | 0.00 | 0.30 | -0.36 | 0.12 | 0.78 | 1.01 |
| B0r | 0.00 | 0.49 | -0.35 | -0.05 | 0.78 | 1.01 |
| E1-reset | 0.00 | 0.31 | -0.36 | 0.12 | 0.78 | 1.01 |
| E1-cal | 0.00 | 0.30 | -0.36 | 0.12 | 0.78 | 1.01 |
| E1-bleed | 0.00 | 0.31 | -0.35 | 0.12 | 0.78 | 1.01 |
| E1-freeze | 0.00 | 0.31 | -0.35 | 0.12 | 0.78 | 1.01 |
| E1-sched | 0.00 | 0.30 | -0.36 | 0.12 | 0.78 | 1.01 |
| E1-splitP | -0.18 | 0.16 | -0.25 | 0.24 | 0.83 | 0.97 |
| E2-R1 | 0.00 | 0.31 | -0.36 | 0.12 | 0.78 | 1.01 |
| E2-S | 0.00 | 0.31 | -0.36 | 0.12 | 0.78 | 1.01 |
| E2-A2 | 0.00 | 0.31 | -0.36 | 0.12 | 0.78 | 1.01 |
| E2-A3 | 0.00 | 0.31 | -0.36 | 0.12 | 0.78 | 1.01 |
| E2-A3-12k | 0.00 | 0.31 | -0.35 | 0.12 | 0.78 | 1.01 |
| E2-A2-X | 0.00 | 0.30 | -0.36 | 0.12 | 0.78 | 1.01 |
| E2-L | 0.00 | 0.30 | -0.36 | 0.12 | 0.78 | 1.01 |
| E2-K0 | 0.00 | -0.13 | 0.00 | -0.00 | -0.01 | 0.43 |
| G-P48d | 0.00 | 0.50 | -0.40 | -0.09 | 0.78 | 1.01 |
| G-P44d | 0.00 | -0.00 | -0.36 | -0.23 | 0.77 | 1.01 |
| G-P48 | 0.00 | 0.50 | -0.38 | -0.29 | 0.31 | 1.01 |
| G-P44 | 0.00 | -0.13 | -0.37 | -0.30 | 0.31 | 1.01 |
| G-F24 | 0.00 | -0.22 | -0.20 | -0.28 | 0.18 | 0.95 |
| G-F24d | 0.00 | -0.21 | -0.33 | -0.28 | 0.51 | 1.01 |
| G-A22 | 0.00 | 0.11 | -0.17 | -0.21 | 0.12 | 0.95 |
| G-A22d | 0.00 | 0.11 | -0.36 | -0.28 | 0.48 | 1.01 |
| G-P48L | 0.00 | -0.25 | -0.39 | -0.28 | 0.31 | 1.01 |
| G-P48k40 | 0.00 | -0.15 | -0.31 | -0.23 | 0.09 | 0.90 |
| H-A | 0.00 | -0.40 | -0.46 | -0.32 | 0.61 | 0.94 |
| H-B | 0.00 | 0.48 | -0.37 | -0.06 | 0.78 | 1.01 |

**Reading (EVIDENCE: simulation + the friction-free control the refuter ran).** The stick-slip is genuine Karnopp
sticking (one trace: P2, nominal, 11.75 m/s, ±0.3° at 0.5 Hz — the wheel is stuck 84 % of the run, the longest stick
2.6 s, θ p2p 0.13° of the 0.6° commanded) and it is a property of P (Kp_eff at the 10–12.5 m/s dip) against the members'
friction: every integral policy reads the same counts to ±3 %. Lane-keeping-sized ±1° corrections at 0.2 Hz are clean
≥ 8 m/s on every I-policy column; at 0.5 Hz they dwell-then-jump at 8–15 m/s on every column. **On the real paths the
dwell-then-jump rate is 7.7–8.6 events per 100 s on every ICL-raising column (P2 7.9),** with two isolated large events
(an 8.3° snap on E1-reset/bc and an 11.0° snap on F2/F_hi): each is the wheel stuck 100–130 ms at the onset of a fast
real swing (r71b runs 7 and 1), then catching up at 39–59°/s and overshooting the plan by up to 4.6°. EVIDENCE (trace
inspection, `score_time.py` metrics on the cached runs).

### 5.4 Texture, hunt, fail-safe, hard turn (vgr)

**Texture: T 5-30 Hz rms under road noise 15 T counts (max counts)**

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | 0.36 | 0.63 | 0.36 | 0.36 | 0.43 | 0.63 |
| F2 | 0.34 | 0.61 | 0.39 | 0.38 | 0.46 | 0.72 |
| D2a | 0.29 | 0.53 | 0.35 | 0.35 | 0.43 | 0.71 |
| B0r | 0.33 | 0.58 | 0.41 | 0.41 | 0.45 | 0.65 |
| E1-reset | 0.29 | 0.60 | 0.38 | 0.39 | 0.52 | 0.68 |
| E1-cal | 0.30 | 0.56 | 0.35 | 0.36 | 0.44 | 0.72 |
| E1-bleed | 0.34 | 0.57 | 0.37 | 0.36 | 0.40 | 0.62 |
| E1-freeze | 0.30 | 0.56 | 0.37 | 0.36 | 0.45 | 0.68 |
| E1-sched | 0.31 | 0.55 | 0.37 | 0.37 | 0.44 | 0.63 |
| E1-splitP | 0.36 | 0.70 | 0.43 | 0.38 | 0.61 | 0.97 |
| E2-R1 | 0.32 | 0.59 | 0.36 | 0.37 | 0.45 | 0.63 |
| E2-S | 0.31 | 0.57 | 0.37 | 0.36 | 0.43 | 0.64 |
| E2-A2 | 0.30 | 0.57 | 0.38 | 0.36 | 0.46 | 0.71 |
| E2-A3 | 0.30 | 0.52 | 0.36 | 0.37 | 0.43 | 0.64 |
| E2-A3-12k | 0.33 | 0.58 | 0.36 | 0.37 | 0.48 | 0.70 |
| E2-A2-X | 0.31 | 0.61 | 0.37 | 0.36 | 0.42 | 0.66 |
| E2-L | 0.30 | 0.54 | 0.36 | 0.34 | 0.40 | 0.63 |
| E2-K0 | 0.38 | 0.73 | 0.38 | 0.51 | 0.95 | 1.20 |
| G-P48d | 0.37 | 0.63 | 0.44 | 0.42 | 0.54 | 0.80 |
| G-P44d | 0.35 | 0.59 | 0.42 | 0.41 | 0.52 | 0.73 |
| G-P48 | 0.35 | 0.59 | 0.43 | 0.44 | 0.53 | 0.76 |
| G-P44 | 0.34 | 0.67 | 0.41 | 0.40 | 0.50 | 0.73 |
| G-F24 | 0.38 | 0.68 | 0.48 | 0.45 | 0.49 | 0.64 |
| G-F24d | 0.36 | 0.68 | 0.44 | 0.43 | 0.51 | 0.67 |
| G-A22 | 0.40 | 1.29 | 1.44 | 1.21 | 0.75 | 1.17 |
| G-A22d | 0.36 | 1.15 | 1.45 | 0.78 | 0.63 | 1.22 |
| G-P48L | 0.36 | 0.72 | 0.47 | 0.44 | 0.52 | 0.75 |
| G-P48k40 | 0.35 | 0.82 | 0.46 | 0.44 | 0.51 | 0.70 |
| H-A | 0.32 | 0.56 | 0.36 | 0.34 | 0.41 | 0.57 |
| H-B | 0.36 | 0.65 | 0.44 | 0.42 | 0.54 | 0.76 |

**510 ms timeout mid-motion: wheel excursion during the hold (max deg)**

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | 4.95 | 2.27 | 2.27 | 1.66 | 0.98 | 0.42 |
| F2 | 4.96 | 1.99 | 2.16 | 1.68 | 1.00 | 0.43 |
| D2a | 4.98 | 2.26 | 2.27 | 1.66 | 0.98 | 0.42 |
| B0r | 4.96 | 1.99 | 2.16 | 1.68 | 1.01 | 0.43 |
| E1-reset | 4.97 | 2.27 | 2.27 | 1.66 | 0.98 | 0.41 |
| E1-cal | 4.96 | 2.26 | 2.27 | 1.66 | 0.98 | 0.41 |
| E1-bleed | 5.00 | 2.26 | 2.28 | 1.66 | 0.98 | 0.41 |
| E1-freeze | 4.98 | 2.26 | 2.27 | 1.66 | 0.98 | 0.42 |
| E1-sched | 4.96 | 2.26 | 2.27 | 1.66 | 0.98 | 0.42 |
| E1-splitP | 3.64 | 1.52 | 1.51 | 1.15 | 0.68 | 0.30 |
| E2-R1 | 4.99 | 2.26 | 2.27 | 1.66 | 0.98 | 0.41 |
| E2-S | 4.96 | 2.26 | 2.27 | 1.66 | 0.98 | 0.42 |
| E2-A2 | 4.95 | 2.27 | 2.27 | 1.66 | 0.98 | 0.42 |
| E2-A3 | 4.94 | 2.27 | 2.27 | 1.66 | 0.99 | 0.42 |
| E2-A3-12k | 4.95 | 2.27 | 2.28 | 1.66 | 0.98 | 0.41 |
| E2-A2-X | 4.95 | 2.26 | 2.27 | 1.66 | 0.98 | 0.42 |
| E2-L | 4.96 | 2.27 | 2.27 | 1.66 | 0.98 | 0.42 |
| E2-K0 | 4.92 | 1.15 | 0.98 | 0.51 | 0.29 | 0.21 |
| G-P48d | 5.08 | 2.26 | 2.40 | 1.78 | 0.98 | 0.42 |
| G-P44d | 5.26 | 2.52 | 2.53 | 1.79 | 1.00 | 0.43 |
| G-P48 | 5.09 | 2.24 | 2.42 | 1.82 | 1.06 | 0.46 |
| G-P44 | 5.26 | 2.54 | 2.52 | 1.82 | 1.07 | 0.47 |
| G-F24 | 5.37 | 2.49 | 2.54 | 1.81 | 1.03 | 0.48 |
| G-F24d | 5.39 | 2.47 | 2.54 | 1.80 | 1.03 | 0.45 |
| G-A22 | 5.61 | 2.55 | 2.57 | 1.76 | 1.01 | 0.50 |
| G-A22d | 5.61 | 2.53 | 2.58 | 1.81 | 1.03 | 0.46 |
| G-P48L | 5.08 | 2.91 | 2.87 | 1.75 | 1.07 | 0.46 |
| G-P48k40 | 4.65 | 2.15 | 2.17 | 1.58 | 0.90 | 0.42 |
| H-A | 5.27 | 2.56 | 2.52 | 1.75 | 1.01 | 0.46 |
| H-B | 4.95 | 2.06 | 2.21 | 1.70 | 1.02 | 0.42 |

**0xE4 sentinel: |T| from 50 ms after (max counts)**

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | 75 | 68 | 46 | 52 | 54 | 28 |
| F2 | 73 | 68 | 46 | 53 | 54 | 28 |
| D2a | 74 | 68 | 46 | 52 | 54 | 28 |
| B0r | 73 | 68 | 46 | 53 | 54 | 28 |
| E1-reset | 78 | 68 | 46 | 52 | 54 | 28 |
| E1-cal | 78 | 68 | 46 | 52 | 54 | 28 |
| E1-bleed | 78 | 68 | 46 | 52 | 54 | 28 |
| E1-freeze | 78 | 68 | 46 | 52 | 54 | 28 |
| E1-sched | 78 | 68 | 46 | 52 | 54 | 28 |
| E1-splitP | 63 | 72 | 47 | 53 | 54 | 27 |
| E2-R1 | 78 | 68 | 46 | 52 | 54 | 28 |
| E2-S | 75 | 68 | 46 | 52 | 54 | 28 |
| E2-A2 | 78 | 68 | 46 | 52 | 54 | 28 |
| E2-A3 | 75 | 68 | 46 | 52 | 54 | 28 |
| E2-A3-12k | 75 | 68 | 46 | 52 | 54 | 28 |
| E2-A2-X | 72 | 63 | 42 | 48 | 50 | 26 |
| E2-L | 78 | 68 | 46 | 52 | 54 | 28 |
| E2-K0 | 78 | 71 | 43 | 44 | 44 | 26 |
| G-P48d | 70 | 68 | 44 | 52 | 55 | 28 |
| G-P44d | 72 | 68 | 47 | 53 | 55 | 28 |
| G-P48 | 70 | 68 | 44 | 53 | 54 | 28 |
| G-P44 | 72 | 68 | 45 | 53 | 54 | 28 |
| G-F24 | 70 | 68 | 47 | 53 | 54 | 28 |
| G-F24d | 70 | 67 | 47 | 53 | 55 | 28 |
| G-A22 | 72 | 67 | 47 | 53 | 54 | 28 |
| G-A22d | 72 | 68 | 47 | 53 | 54 | 28 |
| G-P48L | 70 | 67 | 47 | 53 | 54 | 28 |
| G-P48k40 | 63 | 68 | 46 | 52 | 53 | 29 |
| H-A | 72 | 68 | 47 | 53 | 54 | 27 |
| H-B | 72 | 67 | 45 | 53 | 54 | 28 |

**Hard turn: 1.6-3 Hz wheel-rate rms / the command's own (max)**

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | 1.24 | 1.53 | 0.47 | 0.50 | 0.54 | 0.58 |
| F2 | 1.20 | 1.41 | 0.56 | 0.47 | 0.51 | 0.56 |
| D2a | 1.24 | 1.53 | 0.47 | 0.49 | 0.54 | 0.58 |
| B0r | 1.20 | 1.41 | 0.56 | 0.47 | 0.52 | 0.56 |
| E1-reset | 1.27 | 1.50 | 0.47 | 0.49 | 0.54 | 0.58 |
| E1-cal | 1.27 | 1.50 | 0.47 | 0.49 | 0.54 | 0.58 |
| E1-bleed | 1.27 | 1.50 | 0.47 | 0.49 | 0.54 | 0.58 |
| E1-freeze | 1.27 | 1.50 | 0.47 | 0.49 | 0.54 | 0.58 |
| E1-sched | 1.25 | 1.53 | 0.47 | 0.49 | 0.54 | 0.58 |
| E1-splitP | 2.15 | 2.36 | 0.87 | 0.78 | 0.83 | 0.91 |
| E2-R1 | 1.27 | 1.50 | 0.47 | 0.49 | 0.54 | 0.58 |
| E2-S | 1.27 | 1.50 | 0.47 | 0.49 | 0.54 | 0.58 |
| E2-A2 | 1.18 | 1.43 | 0.47 | 0.49 | 0.54 | 0.58 |
| E2-A3 | 1.22 | 1.43 | 0.47 | 0.49 | 0.54 | 0.58 |
| E2-A3-12k | 1.22 | 1.43 | 0.47 | 0.49 | 0.54 | 0.58 |
| E2-A2-X | 1.18 | 1.43 | 0.47 | 0.49 | 0.54 | 0.58 |
| E2-L | 1.27 | 1.50 | 0.47 | 0.49 | 0.54 | 0.57 |
| E2-K0 | 0.93 | 1.07 | 0.39 | 0.41 | 0.46 | 0.50 |
| G-P48d | 1.01 | 1.17 | 0.42 | 0.45 | 0.52 | 0.55 |
| G-P44d | 0.99 | 1.19 | 0.36 | 0.43 | 0.50 | 0.54 |
| G-P48 | 1.01 | 1.16 | 0.42 | 0.33 | 0.44 | 0.55 |
| G-P44 | 0.99 | 1.19 | 0.36 | 0.31 | 0.44 | 0.54 |
| G-F24 | 0.91 | 1.07 | 0.38 | 0.30 | 0.41 | 0.49 |
| G-F24d | 0.91 | 1.07 | 0.38 | 0.40 | 0.47 | 0.50 |
| G-A22 | 0.90 | 1.06 | 0.38 | 0.30 | 0.39 | 0.50 |
| G-A22d | 0.90 | 1.05 | 0.38 | 0.40 | 0.46 | 0.49 |
| G-P48L | 1.04 | 1.23 | 0.27 | 0.30 | 0.44 | 0.55 |
| G-P48k40 | 1.13 | 1.18 | 0.49 | 0.37 | 0.46 | 0.55 |
| H-A | 1.02 | 1.13 | 0.37 | 0.41 | 0.45 | 0.48 |
| H-B | 1.16 | 1.26 | 0.53 | 0.45 | 0.50 | 0.54 |

Hunt (≥ 8 m/s): **0 on every column**; below 8 m/s 0–11 hunting columns per candidate (the low-speed friction).
Request drop: \|T\| = 0 by +150 ms on every column at every speed. Wraps: 0. Full tables (dead zone, settle, overshoot,
hold error, ±0.3 / ±1° at 0.5 Hz, stuck %, timeout in a held turn, sentinel peak) are in `score_time_out/score_time_tables.md`.

### 5.5 The unity frame (every earlier scorer's convention)

**Goal-criteria fails per band (the goal's decidable time criteria; '<8' is outside the goal's bands)**
TRK/TRKq = tracking outside 0.95-1.05 (clean / r71b's own torque word replayed; data band 8-15 serves 8-10, 10-12.5 and 12.5-15); HOLD = synthetic turn-hold < 0.90 at a_lat <= 2.0; RHOLD = a real r71b curve held < 0.90; HUNT = a limit cycle (>= 2 reversals and >= 0.2 deg p2p in the last 20 s of a 30 s constant setpoint); TEX = T 5-30 Hz > 2.0 counts in that hold; LURCH = a light or firm release lurch > 8 deg (rev2-B's pre-registered bar; a time gate of the brief, not one of the goal's own criteria).  Dwell-then-jump is NOT in this table: the goal's criterion is relative to V282 (not simulable); its counts are in their own tables.

| cand | <8 | 8-10 | 10-12.5 | 12.5-15 | 15-22 | >22 |
|---|---|---|---|---|---|---|
| P2 | n/a | TRK 0.892; TRKq 0.891; LURCH 9.2 | TRK 0.892; TRKq 0.891; LURCH 10.4 | TRK 0.892; TRKq 0.891; HOLD 0.778 | TRK 0.856; TRKq 0.855; HOLD 0.732; RHOLD 0.756 | pass |
| F2 | n/a | TRK 0.896; TRKq 0.896; HOLD 0.896; LURCH 9.0 | TRK 0.896; TRKq 0.896; LURCH 10.3 | TRK 0.896; TRKq 0.896; HOLD 0.771 | TRK 0.851; TRKq 0.850; HOLD 0.722; RHOLD 0.748 | pass |
| D2a | n/a | TRK 0.892; TRKq 0.891; LURCH 9.2 | TRK 0.892; TRKq 0.891; LURCH 10.4 | TRK 0.892; TRKq 0.891; HOLD 0.778 | TRK 0.857; TRKq 0.856; HOLD 0.733; RHOLD 0.757 | pass |
| B0r | n/a | TRK 0.896; TRKq 0.896; HOLD 0.896; LURCH 9.0 | TRK 0.896; TRKq 0.896; LURCH 10.3 | TRK 0.896; TRKq 0.896; HOLD 0.770 | TRK 0.852; TRKq 0.851; HOLD 0.725; RHOLD 0.750 | pass |
| E1-reset | n/a | LURCH 22.9 | LURCH 23.2 | LURCH 12.8 | LURCH 8.0 | pass |
| E1-cal | n/a | LURCH 22.9 | LURCH 23.2 | LURCH 12.8 | LURCH 8.0 | pass |
| E1-bleed | n/a | TRKq 0.752 | TRKq 0.752 | TRKq 0.752 | TRKq 0.739 | TRKq 0.829 |
| E1-freeze | n/a | LURCH 11.0 | pass | pass | pass | pass |
| E1-sched | n/a | TRK 0.885; TRKq 0.884; HOLD 0.885; LURCH 10.4 | TRK 0.885; TRKq 0.884; HOLD 0.895; LURCH 9.0 | TRK 0.885; TRKq 0.884; LURCH 8.2 | TRK 0.928; TRKq 0.927; HOLD 0.895; RHOLD 0.867 | TRK 0.941; TRKq 0.941 |
| E1-splitP | n/a | TRK 0.897; TRKq 0.897; HOLD 0.897; LURCH 9.3 | TRK 0.897; TRKq 0.897; HOLD 0.878 | TRK 0.897; TRKq 0.897; HOLD 0.787 | TRK 0.856; TRKq 0.856; HOLD 0.755; RHOLD 0.788 | pass |
| E2-R1 | n/a | LURCH 22.9 | LURCH 23.2 | LURCH 12.8 | LURCH 8.0 | pass |
| E2-S | n/a | LURCH 10.4 | pass | pass | pass | pass |
| E2-A2 | n/a | pass | pass | pass | pass | pass |
| E2-A3 | n/a | pass | pass | pass | pass | pass |
| E2-A3-12k | n/a | pass | pass | pass | pass | pass |
| E2-A2-X | n/a | pass | pass | pass | pass | pass |
| E2-L | n/a | TRKq 0.938; LURCH 22.9 | TRKq 0.938; LURCH 23.2 | TRKq 0.938; LURCH 12.8 | LURCH 8.0 | pass |
| E2-K0 | n/a | RHOLD 0.656; LURCH 19.0 | RHOLD 0.656 | RHOLD 0.656 | TRK 0.916; TRKq 0.916; RHOLD 0.730 | pass |
| G-P48d | n/a | TRK 0.891; TRKq 0.890 | TRK 0.891; TRKq 0.890; LURCH 9.5 | TRK 0.891; TRKq 0.890; HOLD 0.779 | TRK 0.860; TRKq 0.859; HOLD 0.738; RHOLD 0.763 | pass |
| G-P44d | n/a | TRK 0.884; TRKq 0.883; HOLD 0.894; LURCH 8.1 | TRK 0.884; TRKq 0.883; LURCH 10.0 | TRK 0.884; TRKq 0.883; HOLD 0.774 | TRK 0.856; TRKq 0.855; HOLD 0.732; RHOLD 0.756 | pass |
| G-P48 | n/a | TRK 0.891; TRKq 0.890 | TRK 0.891; TRKq 0.890; LURCH 9.6 | TRK 0.891; TRKq 0.890; HOLD 0.744 | TRK 0.835; TRKq 0.834; HOLD 0.690; RHOLD 0.723 | pass |
| G-P44 | n/a | TRK 0.883; TRKq 0.883; HOLD 0.894; LURCH 8.1 | TRK 0.883; TRKq 0.883; LURCH 10.0 | TRK 0.883; TRKq 0.883; HOLD 0.733 | TRK 0.831; TRKq 0.830; HOLD 0.684; RHOLD 0.718 | pass |
| G-F24 | n/a | TRK 0.881; TRKq 0.881; HOLD 0.885; LURCH 8.3 | TRK 0.881; TRKq 0.881; LURCH 10.4 | TRK 0.881; TRKq 0.881; HOLD 0.726 | TRK 0.821; TRKq 0.820; HOLD 0.670; RHOLD 0.702 | pass |
| G-F24d | n/a | TRK 0.882; TRKq 0.881; HOLD 0.885; LURCH 8.3 | TRK 0.882; TRKq 0.881; LURCH 10.5 | TRK 0.882; TRKq 0.881; HOLD 0.761 | TRK 0.846; TRKq 0.846; HOLD 0.716; RHOLD 0.742 | pass |
| G-A22 | n/a | TRK 0.877; TRKq 0.877; HOLD 0.877; LURCH 9.8 | TRK 0.877; TRKq 0.877; LURCH 11.8 | TRK 0.877; TRKq 0.877; HOLD 0.714; LURCH 8.7 | TRK 0.814; TRKq 0.814; HOLD 0.660; RHOLD 0.693 | pass |
| G-A22d | n/a | TRK 0.878; TRKq 0.877; HOLD 0.876; LURCH 9.8 | TRK 0.878; TRKq 0.877; LURCH 11.9 | TRK 0.878; TRKq 0.877; HOLD 0.752; LURCH 8.5 | TRK 0.841; TRKq 0.840; HOLD 0.708; RHOLD 0.733 | pass |
| G-P48L | n/a | TRK 0.869; TRKq 0.868; HOLD 0.886; LURCH 8.2 | TRK 0.869; TRKq 0.868; LURCH 10.4 | TRK 0.869; TRKq 0.868; HOLD 0.733 | TRK 0.834; TRKq 0.834; HOLD 0.688; RHOLD 0.723 | pass |
| G-P48k40 | n/a | TRK 0.903; TRKq 0.902 | TRK 0.903; TRKq 0.902; LURCH 9.1 | TRK 0.903; TRKq 0.902; HOLD 0.760 | TRK 0.838; TRKq 0.837; HOLD 0.702; RHOLD 0.735 | pass |
| H-A | n/a | TRKq 0.930; LURCH 20.1 | TRKq 0.930; LURCH 20.6 | TRKq 0.930; LURCH 12.5 | pass | pass |
| H-B | n/a | TRKq 0.932; LURCH 18.7 | TRKq 0.932; LURCH 19.7 | TRKq 0.932; LURCH 12.0 | pass | pass |

(Scenarios not run in the unity frame — c30, rn30, db, tmo, sen, dis — leave HUNT/TEX blank here.)

### 5.6 Frame attribution

**Frame attribution: 'vgr' (the measured gp-0x6a00 = C(gp-0x69ca) map) minus 'unity' (every previous scorer's kappa = 1), >= 8 m/s worst cells**

| cand | trk 15-22 vgr / unity | turn-hold a<=2 vgr / unity | gain +-1 0.2 Hz vgr / unity | dj events vgr / unity | light lurch vgr / unity | firm lurch vgr / unity |
|---|---|---|---|---|---|---|
| P2 | 0.856 / 0.856 | 0.73 / 0.73 | 0.86 / 0.86 | 1266 / 1261 | 10.9 / 10.4 | 7.9 / 7.2 |
| F2 | 0.851 / 0.851 | 0.72 / 0.72 | 0.84 / 0.84 | 1293 / 1297 | 10.9 / 10.3 | 7.6 / 7.0 |
| D2a | 0.857 / 0.857 | 0.73 / 0.73 | 0.85 / 0.87 | 1264 / 1261 | 10.9 / 10.4 | 7.9 / 7.2 |
| B0r | 0.852 / 0.852 | 0.72 / 0.72 | 0.84 / 0.84 | 1295 / 1296 | 10.9 / 10.3 | 7.6 / 7.0 |
| E1-reset | 0.993 / 0.993 | 0.98 / 0.97 | 0.86 / 0.86 | 1255 / 1258 | 24.3 / 23.2 | 4.2 / 3.7 |
| E1-cal | 0.993 / 0.993 | 0.98 / 0.97 | 0.86 / 0.86 | 1243 / 1253 | 24.3 / 23.2 | 8.4 / 7.8 |
| E1-bleed | 0.993 / 0.993 | 0.98 / 0.98 | 0.86 / 0.86 | 1253 / 1253 | 3.8 / 3.4 | 4.1 / 3.7 |
| E1-freeze | 0.993 / 0.993 | 0.98 / 0.98 | 0.86 / 0.86 | 1257 / 1262 | 11.8 / 11.0 | 4.1 / 3.6 |
| E1-sched | 0.928 / 0.928 | 0.89 / 0.89 | 0.85 / 0.86 | 1252 / 1262 | 11.1 / 10.4 | 4.2 / 3.7 |
| E1-splitP | 0.856 / 0.856 | 0.75 / 0.75 | 0.81 / 0.81 | 734 / 719 | 9.9 / 9.3 | 6.4 / 5.9 |
| E2-R1 | 0.993 / 0.993 | 0.98 / 0.98 | 0.85 / 0.86 | 1257 / 1263 | 24.3 / 23.2 | 8.4 / 7.8 |
| E2-S | 0.993 / 0.993 | 0.98 / 0.98 | 0.86 / 0.86 | 1260 / 1263 | 11.1 / 10.4 | 8.2 / 7.6 |
| E2-A2 | 0.993 / 0.993 | 0.98 / 0.98 | 0.86 / 0.86 | 1255 / 1260 | 5.8 / 5.2 | 4.7 / 4.2 |
| E2-A3 | 0.993 / 0.993 | 0.98 / 0.98 | 0.86 / 0.86 | 1263 / 1264 | 5.8 / 5.2 | 4.7 / 4.2 |
| E2-A3-12k | 0.995 / 0.995 | 0.98 / 0.98 | 0.86 / 0.86 | 1259 / 1255 | 5.8 / 5.2 | 4.7 / 4.2 |
| E2-A2-X | 0.993 / 0.993 | 0.98 / 0.98 | 0.85 / 0.86 | 1253 / 1264 | 5.8 / 5.2 | 4.7 / 4.2 |
| E2-L | 0.993 / 0.993 | 0.98 / 0.98 | 0.85 / 0.86 | 1259 / 1263 | 24.3 / 23.2 | 4.2 / 3.7 |
| E2-K0 | 0.915 / 0.916 | 0.98 / 0.98 | -0.07 / -0.07 | 294 / 279 | 20.0 / 19.0 | 5.1 / 4.6 |
| G-P48d | 0.860 / 0.860 | 0.74 / 0.74 | 0.70 / 0.72 | 1193 / 1178 | 10.0 / 9.5 | 6.2 / 5.5 |
| G-P44d | 0.856 / 0.856 | 0.73 / 0.73 | 0.64 / 0.64 | 1207 / 1198 | 10.6 / 10.0 | 6.5 / 5.8 |
| G-P48 | 0.835 / 0.835 | 0.69 / 0.69 | 0.69 / 0.68 | 1286 / 1284 | 10.1 / 9.6 | 6.2 / 5.4 |
| G-P44 | 0.831 / 0.831 | 0.68 / 0.68 | 0.66 / 0.67 | 1327 / 1333 | 10.5 / 10.0 | 6.5 / 5.8 |
| G-F24 | 0.821 / 0.821 | 0.67 / 0.67 | 0.56 / 0.56 | 1331 / 1312 | 10.9 / 10.4 | 6.4 / 5.8 |
| G-F24d | 0.847 / 0.846 | 0.72 / 0.72 | 0.56 / 0.54 | 1213 / 1197 | 11.0 / 10.5 | 6.4 / 5.7 |
| G-A22 | 0.814 / 0.814 | 0.66 / 0.66 | 0.47 / 0.47 | 1329 / 1329 | 11.8 / 11.8 | 6.9 / 6.9 |
| G-A22d | 0.841 / 0.841 | 0.71 / 0.71 | 0.46 / 0.46 | 1287 / 1287 | 11.9 / 11.9 | 6.9 / 6.9 |
| G-P48L | 0.834 / 0.834 | 0.69 / 0.69 | 0.11 / 0.08 | 1166 / 1157 | 10.9 / 10.4 | 6.3 / 5.6 |
| G-P48k40 | 0.838 / 0.838 | 0.70 / 0.70 | 0.56 / 0.55 | 936 / 929 | 9.6 / 9.1 | 6.0 / 5.3 |
| H-A | 0.987 / 0.989 | 0.98 / 0.98 | 0.75 / 0.85 | 1274 / 1250 | 22.2 / 20.6 | 2.8 / 3.2 |
| H-B | 0.988 / 0.988 | 0.97 / 0.97 | 0.84 / 0.84 | 1291 / 1296 | 20.8 / 19.7 | 3.3 / 2.8 |

### 5.7 Bridge to the designers' 3 s-hold lurch numbers

**Bridge: release lurch with the refuter's / E2's 3 s hold (ov3_*), max over 8-30 m/s, per member**

| cand | frame | word 400: nom / bc / F_hi / b_lo*J_hi | word 511: nom / bc / F_hi / b_lo*J_hi | firm 2400: nom / bc / F_hi / b_lo*J_hi |
|---|---|---|---|---|
| P2 | vgr | 7.2 / 7.9 / 7.0 / 10.9 | 7.2 / 7.9 / 7.0 / 10.9 | 3.6 / 4.7 / 3.4 / 7.9 |
| F2 | vgr | 7.2 / 7.8 / 6.9 / 10.9 | 7.2 / 7.8 / 6.9 / 10.9 | 3.3 / 4.3 / 3.1 / 7.6 |
| D2a | vgr | 7.2 / 7.9 / 7.0 / 10.9 | 7.2 / 7.9 / 7.0 / 10.9 | 3.6 / 4.7 / 3.4 / 7.9 |
| B0r | vgr | 7.2 / 7.8 / 6.9 / 10.9 | 7.2 / 7.8 / 6.9 / 10.9 | 3.3 / 4.3 / 3.1 / 7.6 |
| E1-reset | vgr | 17.8 / 20.1 / 17.5 / 26.2 | 17.8 / 20.1 / 17.5 / 26.2 | 0.9 / 1.4 / 0.8 / 4.2 |
| E1-cal | vgr | 17.8 / 20.1 / 17.5 / 26.2 | 17.8 / 20.1 / 17.5 / 26.2 | 3.6 / 4.7 / 3.4 / 8.4 |
| E1-bleed | vgr | 0.7 / 1.3 / 0.6 / 3.8 | 0.6 / 1.1 / 0.6 / 3.6 | 0.9 / 1.4 / 0.8 / 4.2 |
| E1-freeze | vgr | 6.3 / 8.5 / 6.0 / 11.7 | 4.7 / 6.6 / 4.4 / 9.9 | 0.8 / 1.3 / 0.7 / 4.1 |
| E1-sched | vgr | 7.1 / 9.9 / 7.0 / 11.1 | 7.1 / 9.9 / 7.0 / 11.1 | 0.9 / 1.4 / 0.8 / 4.2 |
| E1-splitP | vgr | 6.5 / 9.7 / 6.4 / 9.9 | 6.5 / 9.7 / 6.4 / 9.9 | 2.4 / 4.3 / 2.3 / 6.4 |
| E2-R1 | vgr | 17.8 / 20.1 / 17.5 / 26.2 | 17.8 / 20.1 / 17.5 / 26.2 | 3.6 / 4.7 / 3.4 / 8.4 |
| E2-S | vgr | 5.8 / 7.9 / 5.5 / 11.1 | 4.4 / 6.2 / 4.1 / 9.5 | 3.4 / 4.5 / 3.2 / 8.2 |
| E2-A2 | vgr | 2.4 / 4.4 / 2.2 / 5.8 | 2.4 / 4.4 / 2.2 / 5.8 | 1.8 / 2.8 / 1.7 / 4.7 |
| E2-A3 | vgr | 2.4 / 4.4 / 2.2 / 5.8 | 2.4 / 4.4 / 2.2 / 5.8 | 1.8 / 2.8 / 1.7 / 4.7 |
| E2-A3-12k | vgr | 2.4 / 4.4 / 2.2 / 5.8 | 2.4 / 4.4 / 2.2 / 5.8 | 1.8 / 2.8 / 1.7 / 4.7 |
| E2-A2-X | vgr | 2.4 / 4.4 / 2.2 / 5.8 | 2.4 / 4.4 / 2.2 / 5.8 | 1.8 / 2.9 / 1.7 / 4.7 |
| E2-L | vgr | 17.8 / 20.1 / 17.5 / 26.2 | 17.8 / 20.1 / 17.5 / 26.2 | 0.9 / 1.4 / 0.8 / 4.2 |
| E2-K0 | vgr | 35.5 / 38.6 / 35.4 / 42.5 | 35.5 / 38.6 / 35.4 / 42.5 | 1.6 / 2.8 / 1.6 / 5.1 |
| G-P48d | vgr | 7.4 / 7.9 / 7.1 / 10.0 | 7.4 / 7.9 / 7.1 / 10.0 | 3.0 / 3.1 / 2.8 / 6.2 |
| G-P44d | vgr | 7.7 / 8.3 / 7.5 / 10.6 | 7.7 / 8.3 / 7.5 / 10.6 | 3.1 / 3.4 / 2.9 / 6.5 |
| G-P48 | vgr | 7.5 / 8.0 / 7.2 / 10.1 | 7.5 / 8.0 / 7.2 / 10.1 | 3.0 / 3.1 / 2.8 / 6.2 |
| G-P44 | vgr | 7.6 / 8.2 / 7.4 / 10.5 | 7.6 / 8.2 / 7.4 / 10.5 | 3.1 / 3.4 / 2.9 / 6.5 |
| G-F24 | vgr | 7.9 / 8.5 / 7.7 / 10.9 | 7.9 / 8.5 / 7.7 / 10.9 | 2.9 / 3.0 / 2.7 / 6.4 |
| G-F24d | vgr | 8.0 / 8.6 / 7.7 / 11.0 | 8.0 / 8.6 / 7.7 / 11.0 | 2.9 / 3.0 / 2.8 / 6.4 |
| G-A22 | vgr | 8.3 / 9.0 / 8.0 / 11.8 | 8.3 / 9.0 / 8.0 / 11.8 | 3.0 / 3.3 / 2.8 / 6.9 |
| G-A22d | vgr | 8.4 / 9.1 / 8.1 / 11.8 | 8.4 / 9.1 / 8.1 / 11.8 | 3.0 / 3.3 / 2.8 / 6.9 |
| G-P48L | vgr | 8.8 / 9.3 / 8.5 / 11.3 | 8.8 / 9.3 / 8.5 / 11.3 | 3.0 / 3.3 / 2.8 / 6.3 |
| G-P48k40 | vgr | 7.0 / 7.4 / 6.8 / 9.6 | 7.0 / 7.4 / 6.8 / 9.6 | 2.2 / 2.8 / 2.2 / 6.0 |
| H-A | vgr | 17.0 / 19.0 / 16.7 / 24.3 | 17.0 / 19.0 / 16.7 / 24.3 | 0.7 / 0.2 / 0.7 / 2.8 |
| H-B | vgr | 15.6 / 17.4 / 15.4 / 22.4 | 15.6 / 17.4 / 15.4 / 22.4 | 0.9 / 0.4 / 0.8 / 3.3 |
| P2 | unity | 7.1 / 7.7 / 6.9 / 10.4 | 7.1 / 7.7 / 6.9 / 10.4 | 3.3 / 4.1 / 3.1 / 7.2 |
| F2 | unity | 7.1 / 7.6 / 6.8 / 10.3 | 7.1 / 7.6 / 6.8 / 10.3 | 3.0 / 3.7 / 2.8 / 7.0 |
| D2a | unity | 7.1 / 7.7 / 6.9 / 10.4 | 7.1 / 7.7 / 6.9 / 10.4 | 3.3 / 4.1 / 3.1 / 7.3 |
| B0r | unity | 7.1 / 7.6 / 6.8 / 10.3 | 7.1 / 7.6 / 6.8 / 10.3 | 3.0 / 3.7 / 2.8 / 7.0 |
| E1-reset | unity | 17.6 / 19.6 / 17.3 / 25.1 | 17.6 / 19.6 / 17.3 / 25.1 | 0.9 / 0.9 / 0.8 / 3.7 |
| E1-cal | unity | 17.6 / 19.6 / 17.3 / 25.1 | 17.6 / 19.6 / 17.3 / 25.1 | 3.3 / 4.1 / 3.1 / 7.8 |
| E1-bleed | unity | 0.7 / 0.8 / 0.7 / 3.4 | 0.7 / 0.6 / 0.7 / 3.2 | 0.9 / 0.9 / 0.8 / 3.7 |
| E1-freeze | unity | 5.8 / 7.6 / 5.5 / 11.0 | 4.2 / 5.8 / 4.0 / 9.2 | 0.9 / 0.9 / 0.8 / 3.6 |
| E1-sched | unity | 6.5 / 8.9 / 6.3 / 10.4 | 6.5 / 8.9 / 6.3 / 10.4 | 0.9 / 0.9 / 0.8 / 3.7 |
| E1-splitP | unity | 5.9 / 8.8 / 5.8 / 9.3 | 5.9 / 8.8 / 5.8 / 9.3 | 1.9 / 3.6 / 1.8 / 5.9 |
| E2-R1 | unity | 17.6 / 19.6 / 17.3 / 25.1 | 17.6 / 19.6 / 17.3 / 25.1 | 3.3 / 4.1 / 3.1 / 7.8 |
| E2-S | unity | 5.3 / 7.0 / 5.0 / 10.4 | 4.0 / 5.4 / 3.7 / 8.8 | 3.1 / 3.9 / 2.9 / 7.6 |
| E2-A2 | unity | 1.9 / 3.7 / 1.8 / 5.2 | 1.9 / 3.7 / 1.8 / 5.2 | 1.8 / 2.2 / 1.7 / 4.2 |
| E2-A3 | unity | 1.9 / 3.6 / 1.8 / 5.2 | 1.9 / 3.6 / 1.8 / 5.2 | 1.8 / 2.2 / 1.7 / 4.2 |
| E2-A3-12k | unity | 1.9 / 3.6 / 1.8 / 5.2 | 1.9 / 3.6 / 1.8 / 5.2 | 1.8 / 2.2 / 1.7 / 4.2 |
| E2-A2-X | unity | 1.9 / 3.6 / 1.8 / 5.2 | 1.9 / 3.6 / 1.8 / 5.2 | 1.8 / 2.3 / 1.7 / 4.2 |
| E2-L | unity | 17.6 / 19.6 / 17.3 / 25.1 | 17.6 / 19.6 / 17.3 / 25.1 | 0.9 / 1.0 / 0.8 / 3.7 |
| E2-K0 | unity | 34.8 / 37.3 / 34.8 / 41.2 | 34.8 / 37.3 / 34.8 / 41.2 | 1.3 / 2.2 / 1.3 / 4.6 |
| G-P48d | unity | 7.3 / 7.7 / 7.0 / 9.5 | 7.3 / 7.7 / 7.0 / 9.5 | 2.9 / 2.7 / 2.7 / 5.5 |
| G-P44d | unity | 7.6 / 8.1 / 7.4 / 10.1 | 7.6 / 8.1 / 7.4 / 10.1 | 3.0 / 2.8 / 2.8 / 5.8 |
| G-P48 | unity | 7.4 / 7.8 / 7.1 / 9.6 | 7.4 / 7.8 / 7.1 / 9.6 | 2.9 / 2.6 / 2.7 / 5.4 |
| G-P44 | unity | 7.5 / 8.0 / 7.2 / 10.0 | 7.5 / 8.0 / 7.2 / 10.0 | 3.0 / 2.8 / 2.8 / 5.8 |
| G-F24 | unity | 7.8 / 8.3 / 7.6 / 10.4 | 7.8 / 8.3 / 7.6 / 10.4 | 2.9 / 2.6 / 2.7 / 5.8 |
| G-F24d | unity | 7.9 / 8.4 / 7.6 / 10.5 | 7.9 / 8.4 / 7.6 / 10.5 | 2.9 / 2.5 / 2.7 / 5.7 |
| G-A22 | unity | 8.3 / 9.0 / 8.0 / 11.8 | 8.3 / 9.0 / 8.0 / 11.8 | 3.0 / 3.3 / 2.8 / 6.9 |
| G-A22d | unity | 8.4 / 9.1 / 8.1 / 11.8 | 8.4 / 9.1 / 8.1 / 11.8 | 3.0 / 3.3 / 2.8 / 6.9 |
| G-P48L | unity | 8.7 / 9.1 / 8.4 / 10.9 | 8.7 / 9.1 / 8.4 / 10.9 | 2.9 / 2.7 / 2.7 / 5.6 |
| G-P48k40 | unity | 6.9 / 7.3 / 6.7 / 9.1 | 6.9 / 7.3 / 6.7 / 9.1 | 2.2 / 2.3 / 2.2 / 5.3 |
| H-A | unity | 15.6 / 17.3 / 15.3 / 22.1 | 15.6 / 17.3 / 15.3 / 22.1 | 0.8 / 0.4 / 0.8 / 3.2 |
| H-B | unity | 15.4 / 16.9 / 15.1 / 21.4 | 15.4 / 16.9 / 15.1 / 21.4 | 0.9 / 0.3 / 0.9 / 2.8 |

---

## 6. Disagreements with the designers' claims, and their causes

| # | claim (designer) | this scorer | cause |
|---|---|---|---|
| 1 | **H**: the coupled ICL ≥ 7500 + torque bleed "makes a raised ICL safe" (F1↔F4 resolved); G2 lurch "< 4°", "word-2048 ≈ word-400" | **Light-hand lurch 22.2° (H-A) / 20.8° (H-B)** on b_lo×J_hi at 10.25 m/s (1 s hold), 24.3° / 22.4° with a 3 s hold; firm 2.8° / 3.3° | H measured G2 at ICL 4096 only and withheld the 7500 rows. A bleed keyed to \|tq\| > 512 never acts on a light hand reading ≤ 511, so the I winds to the raised clamp. EVIDENCE. |
| 2 | **H**: no tracking claim with the real torque word; THR "likely → 256" | **Replayed-word tracking FAILS: H-A 0.925 / 0.947, H-B 0.933 / 0.952 (8–15 / 15–22, vgr; unity 0.930 / 0.954 and 0.932 / 0.952)**; clean 0.975–0.989 | The bleed drains the hold whenever the resting hand reads > 512 (~1 % of frames, up to 1.2 k on r71b). Lowering THR to 256 would drain on ~5 % (the word exceeds 300 on 4.4–5.2 % of frames) — worse, as E1-bleed (0.74–0.83) shows. EVIDENCE. |
| 3 | **H**: H-B's time gates are "identical to H-A's" (P and I byte-identical) | Identical only at κ = 1. In the measured frame H-A's small-signal gain is lower (±1° 0.2 Hz worst 0.75 vs 0.84; ±0.3° at 8–10 m/s −0.40 vs +0.48) | H-A closes P and I on gp-0x69ca, whose loop gain per plant degree is ×0.866 near centre. EVIDENCE (vgr vs unity). |
| 4 | **E1**: M6-E1 light-hand lurch "up to ~17°" (16.8° b_lo×J_hi at 10 m/s) | **24.3°** at 10.25 m/s (vgr, 1 s), 23.2° unity, 26.2° at 3 s | E1's lurch grid (8 / 10 / 12.5 / 15 / 17 m/s) skips 10.25–12.25 m/s, where the lurch peaks (the I at 8079 of 8192 at release); different curve sizing (a_lat 1.5 vs Ah = 0.5 A_TURN). The declared miss is under-quantified by ~7°. EVIDENCE. |
| 5 | **E1**: E1-bleed is the listed `ld.w; mov; sar 3; sub; st.w -0x6dd0` block | E1's own mirror bleeds `I −= I >> 3` AFTER the clamp | Implementation mismatch inside E1's files (V3a: 0.045°, 4–5 counts). Negligible; E1-bleed is rejected on tracking either way (0.739–0.829 replayed vs E1's 0.787 under the a6 telegraph). |
| 6 | **G**: "every implementation passes every pre-registered bar" of rev2-A's scorer | True of rev2-A's bars; **against the goal every G column fails tracking (0.814–0.903) and turn-hold (0.66–0.78) at 12.5–22 m/s, and the 8° lurch bar at 8–12.5 m/s** | rev2-A's bars never sized the curve by the spring load (the refuter's F1) and carry no lurch bar. G declared F1 as "the integral designers' axis"; it is a statement about the bar set, not a defect in G's D. |
| 7 | **G**: P2 firm lurch b_lo×J_hi 10.21° → G-P48d 5.92° | ≥ 8 m/s: 7.9° → 6.2°; below 8 m/s 11.5° → 7.4° | G's "worst over speeds" includes 3.1 / 5 m/s (E2's T3 places P2's 10.2° below 8 m/s). Direction agrees. |
| 8 | **G**: G-P48d is "+0.004 at 15–22 m/s, −0.003 at 8–15" on the real paths; G-P48 −0.021 | 0.860 vs 0.856; 0.892 vs 0.892 (worst member); G-P48 0.835 | Agreement (EVIDENCE). |
| 9 | **G**: dwell-then-jump at 8–12.5 m/s: P2 2 / 0, G-P48d 4 / 4 (bc / F_hi) | ±1° sinusoids, the full 0.25 m/s grid: P2 160, G-P48d 157 at 8–12.5 m/s; ±0.3°: 548 vs 506 | Denser grid and smaller amplitudes; the counts are the friction's and move ≤ 10 % with the D. G's in-phase finding reproduces (±1° 0.2 Hz, worst at 10–12.5 m/s: G-P48d 0.70 vs 0.87–0.90 on the P2-table columns). |
| 10 | **G**: F_hi timeout-hold deviation G-P48d 2.16° vs P2 1.01° | Held turn 0.55° vs 0.46°; mid-motion 2.40° vs 2.27° | rev2-A's `tmo` holds a turn at Ah but its hold window differs; direction agrees, magnitude does not. |
| 11 | **E2**: E2-S "fixes F1; F4 only for hands > 300 words" | Light lurch 11.1° at 8–10 m/s (≤ 4.3° above 10 m/s) with an opposing signed word ≥ 400 | Agreement in class: at 8 m/s the lurch is M-b (post-release windup on the return error), which no hand test touches (E2 §3.1). |
| 12 | **E2**: A2's worst lurch over every hand model ≥ 8 m/s 3.0 / 3.6 / 5.2° (nominal / bc / b_lo×J_hi) | 3 s hold (unity): 1.9 / 3.7 / 5.2°; the brief's 1 s hold (vgr): ≤ 5.8° | Agreement; the vgr frame adds ~0.6°. |
| 13 | **E2**: every scored column passes every pre-registered bar of rev2-A's scorer | E2-R1, E2-L fail the goal's LURCH gate (24.3°); E2-L fails the replayed-word tracking (0.938, as E2 itself rejected) | Bar-set difference (no lurch bar in rev2-A's suite). E2's own page already reports R1's lurch as "breaks F4". |
| 14 | **rev2-A / rev2-B** (round 1) | P2 / F2 / D2a / B0r fail tracking (0.851–0.897) and turn-hold (0.72–0.78) at 12.5–22 m/s and the lurch gate at 8–15 m/s, in both frames | The round-2 refuter's F1 / F3, reproduced on this pipeline (V4). |
| 15 | **refuter (nl_lens)**: `eng` metric labels | droop and overshoot swapped in the code | Label only; the refuter's reported 6.3° is the physical droop (reproduced: 6.26–6.3°). |

## 7. What this scorer does not decide, and what was not run

- **V282 is not simulable**: "dwell-then-jump ≤ V282" and "hard-turn 1.6–3 Hz energy ≤ V282's" are reported as counts and
  ratios, not passed or failed. "Low-speed stick-slip gone": every column sticks below 8 m/s (±1° sinusoids: 46–120
  dwell-then-jump events over the 3.0 / 3.1 / 5.0 m/s columns; hunt in 0–11 columns) — no candidate removes it (EVIDENCE:
  simulation); whether that is worse than V282 is the car's to say.
- **Frequency-domain criteria** (ring ≤ 0.5 %, F7 = 0, no new 5–30 Hz line, 20 Hz gain ≤ V295's, GATE 2) belong to the
  frequency scorer; the time members carry no 20 Hz plant mode. The 5–30 Hz texture here is a time-domain proxy only.
- **Not run:** the aged hold (+h10, hold ages 11–20) — not in this brief's member list (the refuter ran it for the round-1
  four); FB plant-frame reading and the κ 0.83 extreme (only the table map `vgr` and κ = 1 `unity`); ms_free / b_q /
  J≈1.0 members; a_lat 3.5; E2's consistent-sensor (κ-word) and torque-source hand families; E1's a6 telegraph (replaced
  by r71b's own replayed word, which is the measured route); the relay-close stock-camera 0xE4 and pol ≠ −1 (F5 —
  procedure / image-identity questions, not simulable here); a 0x7FFF fresh-rate fault (no scenario injects it; H1 covers
  the guard's arithmetic).
- **BELIEF items carried:** the plant family's large-angle shape (tanh saturation), SR 16 / no understeer in the a_lat
  conversion, the 2.8-count rate noise and EMA form, the hand models (stiff hand with a constant signed word is the
  κ → ∞ limit, E2 §3.1; the engage hand reads word 0 while it holds the wheel, the refuter's convention), the
  road-noise definition, H's mirror (no listing), H-A's perfect SR fold, K0's fork model.

## 8. Files and reproduction (all `python`, the bin_decompile env; fixed seeds)

| command | what | output |
|---|---|---|
| `python score_time.py h1` | every hex-backed cave executed vs the grid's cave stage | `score_time_out/h1_out.txt` (+ `h1_negative_controls.txt`) |
| `python score_time.py validate` | V1–V3 | `score_time_out/validate_out.txt` |
| `python score_time.py run 8 vgr` | the primary grid: 520 jobs, ~28 min on 8 processes | `_scratch/angle_loop/panel2-score-time/grid_vgr*.json` |
| `python score_time.py run 3 unity rr,rrq,th,s03_02,s03_05,s10_02,s10_05,ov_lt400,ov_lt511,ov_lt1000,ov_fm2400,eng,cs,tmos,hard,st` | the attribution grid | `grid_unity*.json` |
| `python score_time.py run 4 vgr ov3_lt400,ov3_lt511,ov3_fm2400 vgr_ov3` (and `unity … unity_ov3`) | the 3 s-hold bridge | `grid_*_ov3.json` |
| `python score_time.py report` | every table | `score_time_out/score_time_tables.md`, `score_time_summary.json` |

Known artefact, disclosed: the first `rrq` grid padded each shorter run's torque word with its LAST value (the pressed
word that ended the run) for the rest of the batch. Every reported `rrq` metric is scored inside the run's own length and
is causal, so it is unaffected; the freeze-duty statistic was inflated by the padded tail and is not reported (the pad is
now zeros). The word statistics quoted in §0 come from the word series itself.
