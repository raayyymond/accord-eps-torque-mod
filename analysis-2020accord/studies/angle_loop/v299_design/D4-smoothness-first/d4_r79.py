# -*- coding: utf-8 -*-
r"""d4_r79.py -- DESIGNER D4 (smoothness-first): ROUTE-79 COUNTERFACTUALS for the V299 candidate edits.

ANALYSIS ONLY.  Reads the route-79 caches (v280/r79_a1f5d2_al.npz, r79_fork.npz) and the V298 image cells through the
M3 lane replay (v298_flight/m3_lane.py: integer-exact memoryless stages + event-driven integer I recursion, validated
0/65,969 words against the instrument's cached replay; R2 0.928 vs the 0x1AB tap with the dir-2 ramp and the +10-tick
torque-word timing).  Writes only _scratch/v299_D4/.  Sends nothing, flashes nothing.

SECTIONS
  A. the integrator HAND-FREEZE rule, counterfactual grid on the recorded inputs (hard threshold x opposing threshold x
     the MOTION GATE "skip the opposing freeze while the wheel already moves toward the setpoint"): freeze duty,
     toggles per minute, the share of commanded integration kept (|inc|-weighted, A3 included, exact I recursion on the
     key rows), on hands-off frames and on steeringPressed frames, by speed band.
  B. the fork's O1 override counterfactual (ON/OFF thresholds, debounce): episodes, seconds, pressed episodes caught.
  C. the setpoint-rate FRICTION FEEDFORWARD counterfactual: the cave's dirty-derivative state y32 run on the recorded
     0xE4 stream (float lfilter of the integer recursion; |err| < 1 count of d32 >> K), its value inside the measured
     stick dwells vs inside quasi-static holds (the setpoint-jitter hazard), sign agreement with the error.
Usage: python d4_r79.py            (wall time printed; target < 30 s)
"""
from __future__ import annotations

import contextlib
import io
import json
import sys
import time
from pathlib import Path

import numpy as np
from scipy import signal

T0 = time.time()
HERE = Path(__file__).resolve().parent
AL = HERE.parents[1]
KIT = AL.parents[2]
sys.path.insert(0, str(AL / "v298_flight"))
with contextlib.redirect_stdout(io.StringIO()):
    import m3_lane as M  # noqa: E402

OUT = KIT / "_scratch" / "v299_D4"
OUT.mkdir(parents=True, exist_ok=True)
LOG = []


def pr(s=""):
    print(s)
    LOG.append(s)


def runs(mask, minlen=1):
    m = np.r_[False, np.asarray(mask, bool), False]
    d = np.flatnonzero(np.diff(m.astype(int)))
    return [(a, b) for a, b in zip(d[::2], d[1::2]) if b - a >= minlen]


# =====================================================================================================================
# LOAD (exactly M3's primary replay: dir-2 ramp, torque word leads 0x18F by +10 ticks)
# =====================================================================================================================
C = M.image_cells()
GL = M.glut(C["rows"])
W = M.load_wire()
th, cmd, tq, x, abe, vws = M.wire_inputs(W)
n = len(th)
eng = W["eng"]
settled = eng & (W["tse"] >= 1.2)
pressed = W["pressed"]
v = np.nan_to_num(W["vego"])
r0, R = M.ramp_ticks(eng, C["ramp_in2"], C["ramp_out2"])
QS = 10
L = M.lane_terms(C, th, cmd, tq, x, abe, vws, eng, R, r0, GL, q_shift=QS)
F, m = L["F"], L["m"]
# per-tick abe (lane_terms' own construction, not returned by it)
kn = np.minimum(F + 1, n - 1)
ab = np.empty((m, 10), np.int64)
ab[:, :9] = abe[F][:, None]
ab[:, 9] = abe[kn]
ab = M.FL.s16(ab.ravel())
# per-tick masks mapped from per-frame masks
fr_of_tick = np.repeat(F, 10)
HO = settled[fr_of_tick] & ~pressed[fr_of_tick] & L["run"]
PR = settled[fr_of_tick] & pressed[fr_of_tick] & L["run"]
vt = v[fr_of_tick]
BANDS = (("<5", 0, 5), ("5-8", 5, 8), ("8-12.5", 8, 12.5), (">12.5", 12.5, 99))
atq, hs, Ep, run = L["atq"], L["hs"], L["Ep"], L["run"]
inc = np.abs(L["inc"]).astype(float)
pr("D4 route-79 counterfactuals | V298 image %s | engaged %.1f s, settled hands-off %.1f s, settled pressed %.1f s"
   % (C["version"], eng.sum() / 100, (settled & ~pressed).sum() / 100, (settled & pressed).sum() / 100))
pr("load + lane terms: %.1f s" % (time.time() - T0))


# =====================================================================================================================
# A. the hand-freeze rule grid
# =====================================================================================================================
def hand_rule(H, T, mg=None, mg_hard=False):
    """freeze mask (per tick) of the hand rules.  H: hard threshold on gp-0x4f68 (unsigned >), T: opposing threshold,
    mg: motion gate threshold on |gp-0x6abe| (None = off): the opposing (and, if mg_hard, the hard) freeze is skipped
    while (abe ^ E') < 0 and |abe| > mg, i.e. while the wheel already moves TOWARD the setpoint (abe = -4.712 w_motor)."""
    toward = np.zeros_like(run) if mg is None else (((ab ^ Ep) < 0) & (np.abs(ab) > mg))
    c1 = atq > H
    if mg_hard:
        c1 = c1 & ~toward
    c2 = (atq > T) & ((hs ^ Ep) < 0) & ~(atq > H) & ~toward
    return c1 | c2


def toggles_per_min(mask, base):
    """rising+falling edges of mask inside base (per tick), per minute of base time."""
    mm = mask & base
    e = np.count_nonzero(mm[1:] != mm[:-1]) - np.count_nonzero((base[1:] != base[:-1]) & (mm[1:] | mm[:-1]))
    return max(e, 0) / (base.sum() / 1000.0 / 60.0)


GRID = []
for H in (512, 768, 1024, 1229):
    for T in (300, 450, 614, 1 << 20):
        for mg in (None, 10, 20):
            GRID.append((H, T, mg))
rowsA = []
for H, T, mg in GRID:
    fz = hand_rule(H, T, mg)
    row = dict(H=H, T=T if T < (1 << 20) else None, mg=mg)
    for nm, lo, hi in BANDS:
        b = HO & (vt >= lo) & (vt < hi)
        row["duty_" + nm] = float(fz[b].mean())
        row["kept_noA3_" + nm] = float(inc[b & ~fz].sum() / max(inc[b].sum(), 1e-9))
    row["duty_ho"] = float(fz[HO].mean())
    row["tog_ho"] = toggles_per_min(fz, HO)
    row["duty_pressed"] = float(fz[PR].mean())
    row["kept_noA3_ho"] = float(inc[HO & ~fz].sum() / max(inc[HO].sum(), 1e-9))
    rowsA.append(row)
pr("\nA. HAND-FREEZE RULE GRID (hands-off = settled & not steeringPressed; per-tick; A3 + ramp excluded here)")
pr("   H     T    mg | duty_ho  tog/min | duty <5 / 5-8 / 8-12.5 / >12.5     | kept(no A3) ho  <5    5-8  | duty pressed")
for r in rowsA:
    pr("  %4d %5s %4s | %6.3f  %7.1f | %.3f / %.3f / %.3f / %.3f | %.3f        %.3f %.3f | %.3f"
       % (r["H"], r["T"], r["mg"], r["duty_ho"], r["tog_ho"], r["duty_<5"], r["duty_5-8"], r["duty_8-12.5"],
          r["duty_>12.5"], r["kept_noA3_ho"], r["kept_noA3_<5"], r["kept_noA3_5-8"], r["duty_pressed"]))

# exact I recursion on the key rows (A3 bound + ramp + ICL included) -> kept fraction and the replayed-tap change
KEY = [("V298 (512/300)", 512, 300, None), ("a: H1229 T300", 1229, 300, None), ("a: H1229 T450", 1229, 450, None),
       ("a: H1229 T614", 1229, 614, None), ("b: H1229 T300 mg10", 1229, 300, 10),
       ("b: H1229 T300 mg20", 1229, 300, 20), ("no hand freeze", 1 << 20, 1 << 20, None)]
rowsK = []
Tbase = None
for nm, H, T, mg in KEY:
    fz = hand_rule(H, T, mg) | L["c4"]
    Ia, a3s, clp, nev = M.i_recursion(L, fz, a3=True, icl_s=C["icl"])
    stopped = fz | a3s
    Tn = M.output_T(C, L, Ia, n)
    if Tbase is None:
        Tbase = Tn
    r = dict(name=nm, kept_ho=float(inc[HO & ~stopped].sum() / max(inc[HO].sum(), 1e-9)))
    for bn, lo, hi in BANDS:
        b = HO & (vt >= lo) & (vt < hi)
        r["kept_" + bn] = float(inc[b & ~stopped].sum() / max(inc[b].sum(), 1e-9))
    hf = settled & ~pressed
    d = (Tn - Tbase)[hf] / 8.0
    r["dtap_p99"] = float(np.percentile(np.abs(d), 99))
    r["dtap_max"] = float(np.abs(d).max())
    r["tap_p99_ho"] = float(np.percentile(np.abs(Tn[hf]) / 8.0, 99))
    r["a3_ho"] = float(a3s[HO].mean())
    rowsK.append(r)
pr("\nA2. EXACT I RECURSION on the key rules (A3 bound, ramp, ICL included). kept = |inc|-weighted share of the")
pr("    commanded integration actually integrated (hands-off); x 2.79 /s = the effective c_I/c_P.  dtap = replayed tap")
pr("    change vs V298 (LSB, hands-off settled frames), tap p99 = the replayed |tap| p99 (LSB)")
pr("    rule                  | kept ho | <5    5-8   8-12.5 >12.5 | eff Ki <8 (/s) | A3 stop | dtap p99 / max | tap p99")
for r in rowsK:
    eki = 2.79 * 0.5 * (r["kept_<5"] + r["kept_5-8"])
    pr("    %-21s | %.3f   | %.3f %.3f %.3f  %.3f | %.2f           | %.3f   | %5.1f / %5.1f  | %5.1f"
       % (r["name"], r["kept_ho"], r["kept_<5"], r["kept_5-8"], r["kept_8-12.5"], r["kept_>12.5"], eki, r["a3_ho"],
          r["dtap_p99"], r["dtap_max"], r["tap_p99_ho"]))


def hand_rule_mc(T, c, H=None):
    """THE IN-PLACE (a) RULE: the 24-byte hand block 0xC4C62..0xC4C79 rewritten as
         |tq| > T  and  sign(gp-0x4f60 - c * gp-0x6abe) != sign(E')   -> freeze      [+ optional hard |tq| > H]
    gp-0x6abe = -4.712 w_motor, so subtracting c * abe removes the share of the word that the wheel's own motion
    TOWARD the setpoint explains (the hands-off reaction opposes the motion; M3's fit), and ADDS to it when the wheel is
    dragged AWAY from the setpoint (an opposing hand that moves the wheel keeps freezing).  Static hold: abe ~ 0 ->
    V298's test exactly."""
    hm = M.FL.s32(hs - c * ab)
    c2 = (atq > T) & ((hm ^ Ep) < 0)
    if H is not None:
        c2 = c2 | (atq > H)
    return c2


rowsMC = []
pr("\nA3. THE IN-PLACE MOTION-CORRECTED OPPOSING TEST (a): freeze iff |tq| > T and sign(hs - c abe) != sign(E')")
pr("    rule              | duty_ho tog/min | duty <5 / 5-8 / 8-12.5 / >12.5 | kept ho  <5    5-8   8-12.5 >12.5 | eff Ki <8 | A3 | pressed duty")
for nm, T, c, H in (("V298 512/300", None, None, None), ("mc c1 T300", 300, 1, None), ("mc c2 T300", 300, 2, None),
                    ("mc c4 T300", 300, 4, None), ("mc c8 T300", 300, 8, None), ("mc c4 T300 H1229", 300, 4, 1229),
                    ("mc c2 T300 H1229", 300, 2, 1229)):
    fz = hand_rule(512, 300) if T is None else hand_rule_mc(T, c, H)
    Ia, a3s, clp, nev = M.i_recursion(L, fz | L["c4"], a3=True, icl_s=C["icl"])
    stopped = fz | L["c4"] | a3s
    r = dict(name=nm, duty_ho=float(fz[HO].mean()), tog=toggles_per_min(fz, HO), pressed=float(fz[PR].mean()),
             kept_ho=float(inc[HO & ~stopped].sum() / max(inc[HO].sum(), 1e-9)), a3=float(a3s[HO].mean()))
    for bn, lo, hi in BANDS:
        b = HO & (vt >= lo) & (vt < hi)
        r["duty_" + bn] = float(fz[b].mean())
        r["kept_" + bn] = float(inc[b & ~stopped].sum() / max(inc[b].sum(), 1e-9))
    Tn = M.output_T(C, L, Ia, n)
    hf = settled & ~pressed
    r["dtap_p99"] = float(np.percentile(np.abs((Tn - Tbase)[hf]) / 8.0, 99))
    r["tap_p99"] = float(np.percentile(np.abs(Tn[hf]) / 8.0, 99))
    rowsMC.append(r)
    pr("    %-17s | %.3f  %6.1f | %.3f / %.3f / %.3f / %.3f | %.3f   %.3f %.3f %.3f  %.3f | %.2f      | %.3f | %.3f"
       % (nm, r["duty_ho"], r["tog"], r["duty_<5"], r["duty_5-8"], r["duty_8-12.5"], r["duty_>12.5"], r["kept_ho"],
          r["kept_<5"], r["kept_5-8"], r["kept_8-12.5"], r["kept_>12.5"],
          2.79 * 0.5 * (r["kept_<5"] + r["kept_5-8"]), r["a3"], r["pressed"]))
    if nm == "mc c4 T300":
        np.save(OUT / "freeze_mc4.npy", np.packbits(fz))
    if nm == "V298 512/300":
        np.save(OUT / "freeze_v298.npy", np.packbits(fz))
# ---- A4. (b): the motion gate + a LOW-PASSED signed hand word (ONE state word h: h += (hs - h) >> n, per run tick,
#      init 0 on the first tick of every run block = the sentinel path) + optional hysteresis (on T, off T_off)
blk_start = L["rs"] | ~np.r_[False, run[:-1]]
hs_lp = {}
for nlp in (4, 5, 6):
    al_ = 2.0 ** -nlp
    y = np.zeros(len(hs), float)
    st_ = np.flatnonzero(blk_start & run)
    en_ = np.r_[st_[1:], len(hs)]
    for a, b in zip(st_, en_):                               # loop over run BLOCKS (dozens), lfilter inside
        y[a:b] = signal.lfilter([al_], [1.0, -(1 - al_)], hs[a:b].astype(float))
    hs_lp[nlp] = np.trunc(y)


def hand_rule_lp(nlp, T, mg, H, T_off=None):
    h = hs_lp[nlp]
    ah = np.abs(h)
    toward = ((ab ^ Ep) < 0) & (np.abs(ab) > mg)
    opp = (np.sign(h) * np.sign(Ep) < 0)
    on = (ah > T) & opp & ~toward
    if T_off is not None:                                    # hysteresis: stay frozen while |h| > T_off and opposing
        keep = (ah > T_off) & opp & ~toward
        # latched = on, extended through keep (segment forward fill over keep runs)
        lat_ = on.copy()
        for a, b in runs(keep):
            s = np.flatnonzero(on[a:b])
            if len(s):
                lat_[a + s[0]:b] = True
        on = lat_
    return on | (np.abs(h) > H)


pr("\nA4. (b) MOTION GATE + LOW-PASSED HAND WORD (one state word; float lfilter of the integer IIR)")
pr("    rule                         | duty_ho tog/min | kept ho  <5    5-8   8-12.5 >12.5 | eff Ki <8 | A3 | pressed duty")
rowsLP = []
for nm, nlp, T, mg, H, Toff in (("b0: mg10 H1229 T300 (no LP)", None, 300, 10, 1229, None),
                                ("b1: LP16 mg10 H1229 T300", 4, 300, 10, 1229, None),
                                ("b2: LP32 mg10 H1229 T300", 5, 300, 10, 1229, None),
                                ("b3: LP64 mg10 H1229 T300", 6, 300, 10, 1229, None),
                                ("b4: LP32 mg10 H1229 T300/200", 5, 300, 10, 1229, 200),
                                ("b5: LP32 mg10 H1229 T300/150", 5, 300, 10, 1229, 150),
                                ("b6: mg10 H512 T300 (no LP)", None, 300, 10, 512, None),
                                ("b7: LP16 mg10 H512 T300", 4, 300, 10, 512, None),
                                ("b8: LP32 mg10 H512 T300", 5, 300, 10, 512, None),
                                ("b9: LP32 mg10 H768 T300", 5, 300, 10, 768, None)):
    fz = hand_rule(H, 300, 10) if nlp is None else hand_rule_lp(nlp, T, mg, H, Toff)
    Ia, a3s, clp, nev = M.i_recursion(L, fz | L["c4"], a3=True, icl_s=C["icl"])
    stopped = fz | L["c4"] | a3s
    r = dict(name=nm, duty_ho=float(fz[HO].mean()), tog=toggles_per_min(fz, HO), pressed=float(fz[PR].mean()),
             kept_ho=float(inc[HO & ~stopped].sum() / max(inc[HO].sum(), 1e-9)), a3=float(a3s[HO].mean()))
    for bn, lo, hi in BANDS:
        b = HO & (vt >= lo) & (vt < hi)
        r["kept_" + bn] = float(inc[b & ~stopped].sum() / max(inc[b].sum(), 1e-9))
    Tn = M.output_T(C, L, Ia, n)
    hf = settled & ~pressed
    r["dtap_p99"] = float(np.percentile(np.abs((Tn - Tbase)[hf]) / 8.0, 99))
    r["tap_p99"] = float(np.percentile(np.abs(Tn[hf]) / 8.0, 99))
    r["tap_max"] = float(np.abs(Tn[hf]).max() / 8.0)
    rowsLP.append(r)
    pr("    %-28s | %.3f  %6.1f | %.3f   %.3f %.3f %.3f  %.3f | %.2f      | %.3f | %.3f | dtap p99 %.1f tap p99/max %.1f/%.1f"
       % (nm, r["duty_ho"], r["tog"], r["kept_ho"], r["kept_<5"], r["kept_5-8"], r["kept_8-12.5"], r["kept_>12.5"],
          2.79 * 0.5 * (r["kept_<5"] + r["kept_5-8"]), r["a3"], r["pressed"], r["dtap_p99"], r["tap_p99"], r["tap_max"]))
    if nm.startswith("b4"):
        np.save(OUT / "freeze_b4.npy", np.packbits(fz))
# where the remaining toggles of the chosen rule sit: |alpha| of the frame (manoeuvre vs quiet)
b8, a8 = signal.butter(2, 8.0 / 50.0)
alpha = np.gradient(signal.filtfilt(b8, a8, np.nan_to_num(W["w18"]))) * 100.0
al_t = np.abs(alpha[fr_of_tick])
for nm, fz in (("V298", hand_rule(512, 300)), ("mc c4 T300", hand_rule_mc(300, 4)),
               ("b8 LP32 mg10", hand_rule_lp(5, 300, 10, 512)), ("b7 LP16 mg10", hand_rule_lp(4, 300, 10, 512))):
    s_ = []
    for lo, hi in ((0, 25), (25, 100), (100, 400), (400, 1e9)):
        b = HO & (al_t >= lo) & (al_t < hi)
        s_.append("%.3f" % fz[b].mean())
    pr("    hand-frozen share by |alpha| bin 0-25 / 25-100 / 100-400 / >400 deg/s^2, %-10s: %s" % (nm, " / ".join(s_)))
pr("A done: %.1f s" % (time.time() - T0))

# =====================================================================================================================
# B. the fork's O1 override (carcontroller._update_angle: on > ON, off <= OFF, raw |steeringTorque|, latActive)
# =====================================================================================================================
FK = np.load(M.CACHE / "r79_fork.npz")
tq_raw = np.abs(FK["cs_tq"]).astype(float)
t_cs = FK["t_cs"]
j = np.clip(np.searchsorted(FK["t_cc"], t_cs) - 1, 0, len(FK["t_cc"]) - 1)
lat = FK["cc_latActive"][j] > 0
prs = FK["cs_press"] > 0
vv = FK["cs_vego"]


def o1(on, off, deb=1):
    """hysteresis relay with an ON debounce of `deb` consecutive frames above `on` (vectorised: the debounced onset
    mask, then a forward fill of the latched state through frames above `off`)."""
    above = (tq_raw > on) & lat
    if deb > 1:
        c = np.convolve(above.astype(int), np.ones(deb, int), "full")[:len(above)]
        start = c >= deb
    else:
        start = above
    keep = (tq_raw > off) & lat
    # latched = start, or (previous latched and keep): segment-wise forward fill
    st = np.zeros(len(start), bool)
    seg = runs(keep)
    for a, b in seg:
        s = np.flatnonzero(start[a:b])
        if len(s):
            st[a + s[0]:b] = True
    return st


rowsB = []
for nm, on, off, deb in (("V298 600/500", 600, 500, 1), ("600/500 deb 3", 600, 500, 3), ("600/500 deb 5", 600, 500, 5),
                         ("900/700", 900, 700, 1), ("1200/1000 (=pressed)", 1200, 1000, 1),
                         ("1200/1000 deb 3", 1200, 1000, 3)):
    s = o1(on, off, deb)
    ep = runs(s)
    pe = [(a, b) for a, b in ep if prs[a:b].any()]
    np_ = len(ep) - len(pe)
    # pressed episodes (steeringPressed runs while latActive) caught by this O1, and the onset latency
    pr_ep = runs(prs & lat, 5)
    caught = [(a, b) for a, b in pr_ep if s[a:b].any()]
    lag = [int(np.argmax(s[a:b])) for a, b in caught]
    rowsB.append(dict(name=nm, n=len(ep), sec=float(s.sum() / 100.0), n_notpressed=np_,
                      sec_notpressed=float(sum(b - a for a, b in ep if not prs[a:b].any()) / 100.0),
                      lt8_share=float(s[lat & (vv < 8)].mean()), press_eps=len(pr_ep), caught=len(caught),
                      lag_p50_ms=float(np.median(lag) * 10) if lag else float("nan")))
pr("\nB. FORK O1 counterfactual (latActive frames; raw |steeringTorque|; 100 Hz)")
pr("   rule                  | episodes | s     | never-pressed eps / s | O1 share <8 m/s | pressed eps caught | lag p50 ms")
for r in rowsB:
    pr("   %-21s | %5d    | %5.1f | %4d / %5.1f          | %.3f           | %3d / %3d          | %5.0f"
       % (r["name"], r["n"], r["sec"], r["n_notpressed"], r["sec_notpressed"], r["lt8_share"], r["caught"],
          r["press_eps"], r["lag_p50_ms"]))
pr("B done: %.1f s" % (time.time() - T0))

# =====================================================================================================================
# C. the setpoint-rate friction feedforward (the cave's state y32, run on the recorded 0xE4 stream)
# =====================================================================================================================
sp_t = np.repeat(M.FL.s16(cmd), 10).astype(float)            # gp-0x69ae held at 1 kHz (frame k -> ticks 10k..10k+9)
eng_t = np.repeat(eng, 10)
# engage init: y32 := sp << 12 on the first tick of every engaged run (the sentinel path); float IIR inside each run
d32 = np.zeros_like(sp_t)
for a, b in runs(eng_t):                                     # loop over engaged RUNS (8), not samples
    x_ = sp_t[a:b] * 4096.0
    for N in (7,):
        al = 2.0 ** -N
        zi = signal.lfilter_zi([al], [1.0, -(1 - al)]) * x_[0]
        y_, _ = signal.lfilter([al], [1.0, -(1 - al)], x_, zi=zi)
        y_prev = np.r_[x_[0], y_[:-1]]                       # d32 uses y BEFORE this tick's update
        d32[a:b] = x_ - y_prev
th_sp = -np.round(np.nan_to_num(W["raw"])) / 10.0
ang = np.nan_to_num(W["ang"])
err = th_sp - ang
w18 = np.nan_to_num(W["w18"])
wl = np.convolve(w18, np.ones(10) / 10.0, "same")
spl = signal.filtfilt(*signal.butter(2, 0.5 / 50.0), th_sp)
sp_rate = np.gradient(spl) * 100.0
base = settled & ~pressed
# stuck dwells under a moving setpoint (M4's (b) symptom detector at 0.25 deg/s + the setpoint-moving split)
dw = []
for a, b in runs(base & (np.abs(wl) < 0.25), 20):
    if abs(th_sp[b - 1] - th_sp[a]) >= 0.1:
        dw.append((a, b))
holds = base & (np.abs(sp_rate) < 0.3) & (np.abs(wl) < 1.0)
pr("\nC. SETPOINT-RATE FRICTION FF on the recorded 0xE4 stream (tau 2^7 = 128 ms; d32 = (sp<<12) - y32)")
pr("   stuck dwells under a moving setpoint (settled, hands-off): n %d, %.1f s ; quasi-static holds %.1f s"
   % (len(dw), sum(b - a for a, b in dw) / 100.0, holds.sum() / 100.0))
# raw-setpoint jitter census in holds: one-quantum reversals (+1 then -1 within 0.3 s) per minute
dr = np.diff(np.round(np.nan_to_num(W["raw"])))
rev = 0
nz = np.flatnonzero((dr != 0) & holds[1:])
for i0, i1 in zip(nz[:-1], nz[1:]):
    if i1 - i0 <= 30 and abs(dr[i0]) == 1 and dr[i1] == -dr[i0]:
        rev += 1
pr("   raw-setpoint one-quantum reversals in holds: %d (%.1f /min of hold)" % (rev, rev / (holds.sum() / 6000.0)))
rowsC = []
for K, DZ, FC in ((8, 0, 60), (8, 16384, 60), (9, 16384, 60), (8, 32768, 60), (7, 32768, 60)):
    q = d32 - np.sign(d32) * np.minimum(np.abs(d32), DZ)
    ff_t = np.clip(np.floor(q / 2.0 ** K), -FC, FC)
    ff = np.zeros(n)
    ff[:] = ff_t.reshape(n, 10)[:, 4]                         # slot 4 of each frame
    in_dw = np.zeros(n, bool)
    for a, b in dw:
        in_dw[a:b] = True
    # during the dwell: share of dwell frames where |ff| >= FC/2 and sign(ff) == sign(err) (pushing the right way)
    rightway = np.sign(ff) == np.sign(err)
    dwm = in_dw
    # time from dwell start to |ff| >= FC/2
    t_half = []
    for a, b in dw:
        h = np.flatnonzero(np.abs(ff[a:b]) >= FC / 2)
        t_half.append(h[0] * 10.0 if len(h) else np.nan)
    rowsC.append(dict(K=K, DZ=DZ, FC=FC,
                      dwell_half=float((np.abs(ff[dwm]) >= FC / 2).mean()),
                      dwell_right=float(rightway[dwm & (ff != 0)].mean()) if (dwm & (ff != 0)).any() else float("nan"),
                      t_half_p50=float(np.nanmedian(t_half)), never=float(np.mean(np.isnan(t_half))),
                      hold_half=float((np.abs(ff[holds]) >= FC / 2).mean()),
                      hold_any=float((ff[holds] != 0).mean()),
                      hold_flips=float(np.count_nonzero(np.diff(np.sign(ff[holds])) != 0) / (holds.sum() / 6000.0))))
pr("   K  DZ(d32)  FC | dwell frames |ff|>=FC/2 | right sign | t to FC/2 p50 (ms) / never | HOLD frames |ff|>=FC/2 / ff!=0 | hold sign flips /min")
for r in rowsC:
    pr("   %d  %6d  %3d | %.3f                  | %.3f      | %5.0f / %.2f              | %.3f / %.3f              | %.1f"
       % (r["K"], r["DZ"], r["FC"], r["dwell_half"], r["dwell_right"], r["t_half_p50"], r["never"], r["hold_half"],
          r["hold_any"], r["hold_flips"]))
# the error and the P the loop delivered at dwell end (the breakaway), for the FF's sizing
brk = np.array([abs(err[b - 1]) for a, b in dw])
pr("   dwell-end |err| p50 / p90: %.2f / %.2f deg (M4: median 0.8, max 2.9)" % (np.median(brk), np.percentile(brk, 90)))
pr("C done: %.1f s" % (time.time() - T0))

# =====================================================================================================================
# D. the GB-S13 stiffness table on the recorded inputs (open loop: the recorded errors fed through the new gains)
# =====================================================================================================================
GB_S13 = [(714, 1178, 1041), (1843, 1465, -4238), (2304, 988, -2643), (2707, 728, 2040), (4032, 1388, 1513),
          (6198, 2188, 0), (65535, 2188, 0)]
GL13 = M.glut(GB_S13)
L13 = M.lane_terms(C, th, cmd, tq, x, abe, vws, eng, R, r0, GL13, q_shift=QS)
rowsD = []
pr("\nD. GB-S13 TABLE on route 79's recorded errors (OPEN LOOP: closed loop the error would shrink; BELIEF beyond that)")
for nm, LL, fzf in (("V298", L, lambda Q: Q["c1"] | Q["c2"] | Q["c4"]), ("GB-S13 (V298 hand rules)", L13,
                                                                         lambda Q: Q["c1"] | Q["c2"] | Q["c4"])):
    Ia, a3s, clp, nev = M.i_recursion(LL, fzf(LL), a3=True, icl_s=C["icl"])
    Tn = M.output_T(C, LL, Ia, n)
    out = dict(name=nm)
    for bn, lo, hi in (("10-20", 10, 20), ("<10", 0, 10), (">20", 20, 99)):
        b = settled & ~pressed & (v >= lo) & (v < hi)
        out["tap_p99_" + bn] = float(np.percentile(np.abs(Tn[b]) / 8.0, 99))
        out["tap_med_" + bn] = float(np.median(np.abs(Tn[b]) / 8.0))
        # small-correction slope: |err| < 1 deg frames, tap per deg of error (median of |tap|/|err| where |err|>0.2)
        mm = b & (np.abs(err) > 0.2) & (np.abs(err) < 1.0)
        out["tap_per_deg_small_" + bn] = float(np.median(np.abs(Tn[mm]) / 8.0 / np.abs(err[mm])))
    rowsD.append(out)
    pr("   %-26s | tap p99 <10 / 10-20 / >20: %5.1f %5.1f %5.1f LSB | median %4.1f %4.1f %4.1f | small-error tap/deg %4.1f %4.1f %4.1f"
       % (nm, out["tap_p99_<10"], out["tap_p99_10-20"], out["tap_p99_>20"], out["tap_med_<10"], out["tap_med_10-20"],
          out["tap_med_>20"], out["tap_per_deg_small_<10"], out["tap_per_deg_small_10-20"], out["tap_per_deg_small_>20"]))
pr("D done: %.1f s" % (time.time() - T0))

json.dump(dict(D=rowsD, A=rowsA, A2=rowsK, A3=rowsMC, A4=rowsLP, B=rowsB, C=rowsC, wall_s=time.time() - T0), open(OUT / "d4_r79.json", "w"), indent=1)
(OUT / "d4_r79.txt").write_text("\n".join(LOG) + "\n", encoding="utf-8")
pr("\nWALL TIME %.1f s -> %s" % (time.time() - T0, OUT / "d4_r79.txt"))
