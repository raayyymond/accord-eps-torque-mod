# -*- coding: utf-8 -*-
"""studies/osc-highangle/stutter_v283.py -- the 7 Hz strong-turn / stall-stutter READ on V283 (r36/r37/r38),
scored with the SAME code paths and thresholds as r35 (strongturn_r35.py / strongturn_r32_r33.py /
highangle_stutter.py / r24_deembed.py).  V283 = V281 rev 3 (Kp flat 248) + V282's inert r24 comparator tap
(0x14A byte 4 bits 6/5/4) + 0xC63E6 Ki 0 -> 50, on the V280 rev 2 base.

Baselines: r35 = V281 rev 3 (Ki 0, same StarPilot tune) -- the clean Ki 0->50 contrast; r34 = V280 rev 2.

Sections
  A   build attribution from the 427 tap (Kp = stock LERP / flat 248 / 341 / 512) AND the Ki FIT: the
      integrator of FUN_00028ea6 (0x29d7c..0x29dc2 accumulate, 0x29f18 sar 7, 0x29f1e/0x29f24 add) run in the
      chain at Ki in {0,5,20,50,100,200} -- which Ki reproduces the tap best, per route?  [prereg (g)]
  B   F7 census: FIXED threshold 103 wire (r32/r33/r34/r35 census) + own-threshold + thresholds 80/60/40
      [prereg (e) part 1]
  C   discriminators on every hands-light strong-turn window (f0, |bar|/|rate| at f0, L_servo / L_r24,
      0x14A b4.4 sign(r24) phase) + PREREG-V282-READ.md statistic (D): bit-6 duty in the 7 Hz strong-turn
      frames (|angle| >= 30, idx >= 68); comparator non-degeneracy census first  [prereg (e) part 2, (D)]
  D   the STALL / DESATURATION census: (a) stalled runs >= 1 s, (b) idx 40-80 wheel rate vs reference,
      (c) prereg (k) dead fraction speed-matched, (d) stall-release overshoot, the 0.2-1 Hz integrator hunt
      on straights AND in turns, and the 8.5-10 Hz / spectra columns
  E   authority: hands-light full demand, hands-on hold at idx 40-84 (h), saturation (viii)

Run: python stutter_v283.py    (needs analysis-2020accord/_scratch/cache/v280/r3{5,6,7,8}.npz,
     r35_b4.npz and r3{6,7,8}_b4st.npz -- the latter from extract_14a_b4_v283.py)
Subagent stutter283, 2026-09-03.
"""
import os
import sys

import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import strongturn_r32_r33 as ST  # noqa: E402
import strongturn_r35 as S35  # noqa: E402
import r24_deembed as RD  # noqa: E402

V, S = ST.V, ST.S
FS, FS1K = ST.FS, ST.FS1K
CPD = V.CPD

NEW = {"r36": "75604b0a432fdc89_00000036--f4be1a18e9",
       "r37": "75604b0a432fdc89_00000037--4a79da5d18",
       "r38": "75604b0a432fdc89_00000038--f77bddf4bd"}
for _t, _p in NEW.items():
    V.ROUTE_PREFIX[_t] = _p
    V.ROUTE_BUILD[_t] = "V283 Kp flat 248 + Ki 50"
    V.ROUTE_K[_t] = 6.0
ST.TAP_TAGS.update(set(NEW))
ST.TAP_TAGS.update({"r34", "r35"})

V280R2 = ST.V280R2
KP_FLAT = S35.KP_FLAT
ROUTES = ("r35", "r36", "r37", "r38")
KP_ONCAR = {t: "flat 248" for t in ROUTES}
KI_ONCAR = {"r35": 0, "r36": 50, "r37": 50, "r38": 50}

# own-threshold episode lists at |angle| >= 30 from HIGHANGLE-r3x.txt (SAME detector, --build v278r3)
EPIS = {"r35": S35.EPIS["r35"],
        "r36": [(705.9, 1.1, 2.61)],
        "r37": [],                       # its only episode is at |angle| 26.4 -- below the 30 deg gate
        "r38": []}
HIGH_ANG_S = {"r35": 79.8, "r36": 48.0, "r37": 35.0, "r38": 43.4}

DEADBAND_CAL = 4          # 0xC62E4
I_CLAMP_CAL = 10240       # 0xC61BA


# ----------------------------------------------------------------------------------------------------
# the chain WITH the integrator -- mirrors FUN_00028ea6 exactly (V850 is LE; sar = arithmetic = floor div)
# ----------------------------------------------------------------------------------------------------
def integrate(E, eng1k, ki, deadband=DEADBAND_CAL, iclamp=I_CLAMP_CAL):
    """acc = clamp(acc + ((excess*Ki) >> 3), +-iclamp<<7); I_term = acc >> 7.
       0x29d7c  sar 0x5,r6        -> e5 = E >> 5
       0x29d7e..0x29d9a           -> excess = e5 - db if e5 > db ; e5 + db if e5 < -db ; else 0
       0x29da8  mul r6,r9         -> excess * Ki
       0x29db2  sar 0x3,r9        -> (excess*Ki) >> 3
       0x29db4  add r9,r10        -> acc + that            (r10 = gp-0x6dd0 >> 3, 0x29db0)
       0x29db6..0x29dc2           -> clamp to +-(0xC61BA << 10 >> 3) = +-iclamp*128
       0x29f18  sar 0x7,r2        -> I_term = acc >> 7,  |I_term| <= iclamp
       reset: only the not-engaged / not-valid arm (0x2A164 mov 0x0,r24) -- no override reset."""
    if ki == 0:
        return np.zeros_like(E)
    e5 = np.right_shift(np.floor(E).astype(np.int64), 5)
    exc = np.where(e5 > deadband, e5 - deadband, np.where(e5 < -deadband, e5 + deadband, 0))
    inc = np.right_shift(exc * np.int64(ki), 3)
    lim = np.int64(iclamp) * 128
    acc = np.zeros(len(E), np.int64)
    d = np.diff(np.r_[0, eng1k.astype(int), 0])
    for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)):
        c = np.cumsum(inc[a:b])
        if c.size and np.abs(c).max() <= lim:
            acc[a:b] = c                                     # clamp never bites -> cumsum is exact
        else:
            s = np.int64(0)
            seg = inc[a:b]
            out = np.empty(b - a, np.int64)
            for i in range(b - a):
                s = min(max(s + seg[i], -lim), lim)
                out[i] = s
            acc[a:b] = out
    return np.right_shift(acc, 7).astype(float)


def sim_ki(r, mapY, clamp, kpY, ki, kd=V.KD):
    """V.Route.simulate with I_term added at the P/D summing node (0x29f1e add r9,r2 ; 0x29f24 add r8,r2)."""
    y = V.lerp(V.MAP_X, mapY, r.idx1k)
    kp = V.lerp(V.KP_X, kpY, r.idx1k)
    sp = r.sgn1k * y
    fb = np.clip(r.fb_un, -clamp, clamp)
    E = 32 * sp - fb
    P_raw = np.floor(E * kp / 256)
    P = np.clip(P_raw, -V.P_CLAMP, V.P_CLAMP)
    dE = np.r_[0.0, np.diff(E)]
    onset = r.eng1k & ~np.r_[False, r.eng1k[:-1]]
    dE[onset] = 0.0
    D_raw = np.floor(dE * kd / 8)
    Dt = np.clip(D_raw, -V.D_CLAMP, V.D_CLAMP)
    I = integrate(E, r.eng1k, ki)
    S_raw = np.floor(V.SUM_MULT * (P + Dt + I) / 256)
    Sc = np.clip(S_raw, -V.SUM_CLAMP, V.SUM_CLAMP)
    Sc[~r.eng1k] = 0.0
    lag = V.output_lag(Sc)
    T = np.clip(np.floor(-lag * V.GAIN / 32768), -V.OUT_CAP, V.OUT_CAP)
    R = dict(E=E, P_raw=P_raw, D_raw=D_raw, S_raw=S_raw, T=T, fb=fb, sp=sp, I=I)
    R["clamped"] = np.abs(r.fb_un) >= clamp
    R["ref_deg"] = 32 * np.abs(sp) / V.FB_DC / CPD
    return R


def load_b4(tag, r):
    for suf in ("_b4st.npz", "_b4.npz"):
        f = os.path.join(V.CACHE, tag + suf)
        if os.path.exists(f):
            D = dict(np.load(os.path.join(V.CACHE, tag + ".npz")))
            t0 = D["t18"][0]
            B = dict(np.load(f))
            tb = B["t14b"] - t0
            j = np.clip(np.searchsorted(tb, r.tg), 0, len(tb) - 1)
            return B["b4"][j]
    return None


def band_amp_psd(f, P, lo, hi):
    m = (f >= lo) & (f < hi)
    return float(np.sqrt(2 * np.trapezoid(P[m], f[m]))) if m.sum() > 1 else np.nan


def runs_of(mask, n):
    d = np.diff(np.r_[0, mask.astype(int), 0])
    return [(a, b) for a, b in zip(np.flatnonzero(d == 1), np.flatnonzero(d == -1)) if b - a >= n]


def main():
    L = []

    def pr(s=""):
        print(s, flush=True)
        L.append(s)

    routes, gs, b4s, SIM = {}, {}, {}, {}
    for tag in ROUTES:
        print("loading %s ..." % tag, flush=True)
        routes[tag] = V.Route(tag)
        gs[tag] = RD.load(tag)
        b4s[tag] = load_b4(tag, routes[tag])
    KIS = (0, 5, 20, 50, 100, 200)
    for tag in ROUTES:
        SIM[tag] = {ki: sim_ki(routes[tag], *V280R2, kpY=KP_FLAT["flat 248"], ki=ki) for ki in KIS}
        print("  simulated %s" % tag, flush=True)

    pr("=" * 175)
    pr("V283 (Kp flat 248 + Ki 50 on the V280 rev 2 base) -- STUTTER / 7 Hz READ on r36/r37/r38, scored as r35 was.  Subagent stutter283, 2026-09-03")
    pr("  r35 = V281 rev 3 (Kp flat 248, Ki 0) -- the like-for-like Ki 0 baseline (same StarPilot tune).  r34/r33/r32 = V280 rev 2, quoted from V281R3-READ-r35-2026-09-03.md.")
    pr("=" * 175)
    pr("route  engaged s   high-angle(|ang|>=30) s   own-threshold episodes >=30 deg")
    for tag in ROUTES:
        r = routes[tag]
        pr("  %-4s %8.1f      %6.1f                  %s" % (tag, r.eng.sum() / FS, float(np.sum(r.eng & (np.abs(r.ang) >= 30)) / FS),
           ", ".join("t0 %.1f dur %.1f fdom %.2f" % e for e in EPIS[tag]) or "none"))

    # ------------------------------------------------------------------------------------------- A
    pr("\n" + "=" * 175)
    pr("SECTION A -- BUILD ATTRIBUTION and the Ki FIT [prereg (g)].  Chain = V280 rev 2 line x6 / fb clamp 46080 / gain 5346 / cap 3072, open loop on the measured rate.")
    pr("  A1 Kp: corr/slope of T_sim vs the CAN-427 tap at Ki = 0.  A2 Ki: the SAME chain at Kp flat 248 with the FUN_00028ea6 integrator at each Ki -- rms residual vs the tap.")
    pr("=" * 175)
    for tag in ROUTES:
        r = routes[tag]
        e = r.eng & (r.idx > 0)
        hi = e & (np.abs(r.ang) >= 30)
        strong = hi & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.wire) / CPD > 5)
        Tm = r.T_meas
        for k, y in KP_FLAT.items():
            R = sim_ki(r, *V280R2, kpY=y, ki=0)
            Ts = R["T"][r.i100]
            c_all = np.corrcoef(Ts[e], Tm[e])[0, 1]
            s_all = np.sum(Ts[e] * Tm[e]) / np.sum(Ts[e] ** 2)
            c_st = np.corrcoef(Ts[strong], Tm[strong])[0, 1] if strong.sum() > 100 else np.nan
            s_st = np.sum(Ts[strong] * Tm[strong]) / np.sum(Ts[strong] ** 2) if strong.sum() > 100 else np.nan
            pr("  A1 %s Kp %-10s Ki 0 | all eng (n %6d): corr %.3f slope %.3f | strong (n %5d): corr %.3f slope %.3f%s"
               % (tag, k, e.sum(), c_all, s_all, strong.sum(), c_st, s_st, "   <-- Kp ON CAR" if KP_ONCAR[tag] == k else ""))
        pr("")
    pr("  A2 -- the Ki ladder at Kp flat 248.  'resid' = rms(T_sim - T_meas); 'slope' = <T_sim,T_meas>/<T_sim,T_sim> (1.00 = the chain reproduces the tap).")
    pr("       I-AUTHORITY frames = engaged, idx 20-120, |angle| > 10 (where |I| grows against a held error).  BEST = lowest resid.")
    for tag in ROUTES:
        r = routes[tag]
        Tm = r.T_meas
        e = r.eng & (r.idx > 0)
        mI = r.eng & (r.idx >= 20) & (r.idx <= 120) & (np.abs(r.ang) > 10)
        cells, cellsI = [], []
        for ki in KIS:
            Ts = SIM[tag][ki]["T"][r.i100]
            cells.append((ki, float(np.sqrt(np.mean((Ts[e] - Tm[e]) ** 2))), float(np.sum(Ts[e] * Tm[e]) / np.sum(Ts[e] ** 2)),
                          float(np.corrcoef(Ts[e], Tm[e])[0, 1])))
            cellsI.append((ki, float(np.sqrt(np.mean((Ts[mI] - Tm[mI]) ** 2))), float(np.sum(Ts[mI] * Tm[mI]) / np.sum(Ts[mI] ** 2)),
                           float(np.corrcoef(Ts[mI], Tm[mI])[0, 1])))
        b1 = min(cells, key=lambda c: c[1])[0]
        b2 = min(cellsI, key=lambda c: c[1])[0]
        pr("  %s ALL ENGAGED  n %6d: %s  => BEST Ki %3d   (flown: %d)" % (tag, e.sum(), "  ".join("Ki%3d resid %5.0f slope %.3f corr %.3f" % c for c in cells), b1, KI_ONCAR[tag]))
        pr("  %s I-AUTHORITY  n %6d: %s  => BEST Ki %3d" % (tag, mI.sum(), "  ".join("Ki%3d resid %5.0f slope %.3f corr %.3f" % c for c in cellsI), b2))
        I = SIM[tag][50]["I"][r.i100]
        Pp = np.median(np.abs(SIM[tag][50]["P_raw"][r.i100][mI]))
        pr("       modelled |I_term| at Ki 50 on those frames: p50 %5.0f p90 %5.0f max %5.0f (clamp 10240); |P| p50 %5.0f => I/P p50 %.2f; 1 kHz frames at the I clamp %.4f"
           % (np.median(np.abs(I[mI])), np.percentile(np.abs(I[mI]), 90), np.abs(I[mI]).max(), Pp, np.median(np.abs(I[mI])) / max(Pp, 1),
              float(np.mean(np.abs(SIM[tag][50]["I"][r.eng1k]) >= 10239))))

    # ------------------------------------------------------------------------------------------- B
    pr("\n" + "=" * 175)
    pr("SECTION B -- F7 CENSUS [prereg (e) part 1].  FIXED threshold 103 wire (the r32/r33/r34/r35 census, strongturn_r32_r33.fixed_thr_episodes); then 80/60/40.")
    pr("  prereg (e): F7 episodes per 100 s of high-angle time predicted UNCHANGED, <= 2.  r35 = 0.0, r34 = 6.8, r33 = 4.3, r32 = 8.1.")
    pr("=" * 175)
    for tag in ROUTES:
        r = routes[tag]
        eps = ST.fixed_thr_episodes(r)
        hi = [e for e in eps if e["ang"] >= 30]
        f7 = [e for e in hi if e["fdom"] >= 6]
        hs = float(np.sum(r.eng & (np.abs(r.ang) >= 30)) / FS)
        pr("%s: engaged %.0f s, high-angle %.1f s | FIXED-103: %d episodes (%.1f s); >=30 deg %d (%.1f s); F7 %d (%.1f s) = %.2f per 100 s high-angle | fdom(>=30): %s"
           % (tag, r.eng.sum() / FS, hs, len(eps), sum(e["dur"] for e in eps), len(hi), sum(e["dur"] for e in hi), len(f7), sum(e["dur"] for e in f7),
              100 * len(f7) / hs, " ".join("%.1f" % e["fdom"] for e in hi) or "-"))
        for e in hi:
            pr("     fixed-103 t0 %6.1f dur %3.1f fdom %.2f ang %4.0f v %3.1f rate amp %4.0f wire  %s" % (e["t0"], e["dur"], e["fdom"], e["ang"], e["v"], e["ramp"], "F7" if e["fdom"] >= 6 else "F2"))
        own = EPIS[tag]
        f7o = [x for x in own if x[2] >= 6]
        pr("     own-threshold: %d at >=30 deg, F7 %d (%.1f s) = %.2f per 100 s" % (len(own), len(f7o), sum(x[1] for x in f7o), 100 * len(f7o) / HIGH_ANG_S[tag]))
        for thr in (80, 60, 40):
            e2 = ST.fixed_thr_episodes(r, thr=thr)
            h2 = [e for e in e2 if e["ang"] >= 30]
            f2 = [e for e in h2 if e["fdom"] >= 6]
            pr("     threshold %3d wire: >=30 deg %2d episodes, F7 %2d (%.1f s) = %.2f per 100 s; F7 fdom %s"
               % (thr, len(h2), len(f2), sum(e["dur"] for e in f2), 100 * len(f2) / hs, " ".join("%.1f" % e["fdom"] for e in f2) or "-"))
        for lo, hi_ in ((0, 3), (3, 6), (6, 10), (10, 99)):
            mm = r.eng & (np.abs(r.ang) >= 30) & (r.vego >= lo) & (r.vego < hi_)
            pr("       high-angle time at v %2d-%2d m/s: %5.1f s  (idx>=40 & hands-light <1216: %5.1f s)" % (lo, hi_, mm.sum() / FS, (mm & (r.idx >= 40) & (np.abs(r.tq_raw) < 1216)).sum() / FS))

    # ------------------------------------------------------------------------------------------- C
    pr("\n" + "=" * 175)
    pr("SECTION C -- the discriminators on every hands-light strong-turn window (engaged, |angle|>=30, v<=10, |tq|<2240, idx>=40, 1 s / 0.5 s step) -- IDENTICAL to r35's method.")
    pr("  prereg (e) part 2: tap 6-8.5 Hz ripple/level in idx >= 68 runs, predicted <= 0.25 (r35 0.18, r34 0.37, r33 0.62, r32 0.36).")
    pr("=" * 175)
    pr("  C0 -- 0x14A byte 4 COMPARATOR NON-DEGENERACY (checked BEFORE any bit is interpreted).  bit6 = |r24|>=|T|, bit5 = |r24|>=|aggregator|, bit4 = sign(r24).")
    for tag in ROUTES:
        r = routes[tag]
        b4 = b4s[tag]
        if b4 is None:
            pr("  %s: NO byte-4 cache" % tag)
            continue
        e = r.eng
        d6, d5, d4 = [float(np.mean((b4[e] >> k) & 1)) for k in (6, 5, 4)]

        def fl(k, e=e, b4=b4):
            return float(np.mean(np.diff(((b4[e] >> k) & 1).astype(int)) != 0) * FS)

        pr("  %s engaged n %6d: bit6 duty %.3f (%.1f flips/s) | bit5 duty %.3f (%.1f/s) | bit4 duty %.3f (%.1f/s)"
           % (tag, e.sum(), d6, fl(6), d5, fl(5), d4, fl(4)))
        pr("       NON-DEGENERATE? bit6 %s | bit5 %s | bit4 %s" % tuple("YES" if 0.001 < x < 0.999 else "*** DEGENERATE ***" for x in (d6, d5, d4)))

    disc = {}
    for tag in ROUTES:
        r = routes[tag]
        g = gs[tag]
        b4 = b4s[tag]
        RD.KP_Y = KP_FLAT["flat 248"]
        wins = S35.strong_windows(r, tq_max=2240)
        rows = []
        for t0, dur in wins:
            x = S35.disc_row(g, t0, dur, b4, r)
            s, e_ = int(round(t0 * FS)), int(round((t0 + dur) * FS))
            if b4 is not None:
                x["b6duty"] = float(np.mean((b4[s:e_] >> 6) & 1))
                x["b5duty"] = float(np.mean((b4[s:e_] >> 5) & 1))
            else:
                x["b6duty"] = x["b5duty"] = np.nan
            x["idx68"] = bool(np.median(r.idx[s:e_]) >= 68)
            rows.append(x)
        disc[tag] = rows
        if not rows:
            pr("  %s: no hands-light strong-turn windows" % tag)
            continue

        def med(k, sub):
            return float(np.median([x[k] for x in sub]))

        for lab, sub in (("ALL <2240", rows), ("hands-light <1216", [x for x in rows if x["tq_p50"] < 1216]),
                         ("idx>=68 [prereg e]", [x for x in rows if x["idx68"]]),
                         ("idx>=68 & <1216", [x for x in rows if x["idx68"] and x["tq_p50"] < 1216])):
            if not sub:
                pr("  %s %-20s: no windows" % (tag, lab))
                continue
            pr("  %s %-20s n %3d: f0 %.2f (p10-p90 %.2f-%.2f) | rate@f0 %.1f (6-8.5 band %.1f) | bar %.0f T %.0f |T| %.0f | rip/L %.3f (p90 %.2f) | |bar|/|rate| %.1f | |L_servo| %.2f@%+.0f |L_r24| %.2f@%+.0f (>1 on %d) | bit4 ph %+.0f R %.2f | b6 %.3f b5 %.3f | F7-class %d"
               % (tag, lab, len(sub), med("f0", sub), np.percentile([x["f0"] for x in sub], 10), np.percentile([x["f0"] for x in sub], 90),
                  med("Arate", sub), med("rate7", sub), med("Abar", sub), med("AT", sub), med("Tlev", sub),
                  med("rl", sub), np.percentile([x["rl"] for x in sub], 90), med("bar_over_rate", sub),
                  np.median([abs(x["Ls"]) for x in sub]), np.median([np.degrees(np.angle(x["Ls"])) for x in sub]),
                  np.median([abs(x["Lr"]) for x in sub]), np.median([np.degrees(np.angle(x["Lr"])) for x in sub]), sum(abs(x["Lr"]) > 1 for x in sub),
                  np.degrees(np.angle(np.nanmean(np.exp(1j * np.radians([x["ph_bit"] for x in sub]))))),
                  abs(np.nanmean(np.exp(1j * np.radians([x["ph_bit"] for x in sub])))),
                  float(np.nanmedian([x["b6duty"] for x in sub])), float(np.nanmedian([x["b5duty"] for x in sub])),
                  sum(1 for x in sub if x["Arate"] >= 15 and x["rl"] >= 0.4)))

    pr("\n  C2 -- PREREG-V282-READ.md statistic (D): bit-6 duty P(|r24| >= |T|) in the 7 Hz STRONG-TURN frames (|angle| >= 30, idx >= 68).  Predicted >= 0.5 if r24 is the pump, < 0.2 if the servo is.")
    pr("       Two framings, both reported: (D-frame) every engaged frame meeting the mask; (D-win) the 1 s windows above with rip/L >= 0.25 (the residual-ring windows).")
    for tag in ROUTES:
        r = routes[tag]
        b4 = b4s[tag]
        if b4 is None:
            continue
        m = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 68)
        mL = m & (np.abs(r.tq_raw) < 1216)
        sub = [x for x in disc[tag] if x["idx68"] and x["rl"] >= 0.25]
        pr("  %s (D-frame) n %5d (%.1f s): bit6 duty %.3f | hands-light n %5d: %.3f | (D-win) %d ring windows: bit6 duty %.3f | ALL engaged bit6 %.3f"
           % (tag, m.sum(), m.sum() / FS, float(np.mean((b4[m] >> 6) & 1)) if m.sum() else np.nan,
              mL.sum(), float(np.mean((b4[mL] >> 6) & 1)) if mL.sum() else np.nan,
              len(sub), float(np.nanmedian([x["b6duty"] for x in sub])) if sub else np.nan,
              float(np.mean((b4[r.eng] >> 6) & 1))))

    # ------------------------------------------------------------------------------------------- D
    pr("\n" + "=" * 175)
    pr("SECTION D -- THE STALL / DESATURATION CENSUS and the integrator's signatures.")
    pr("=" * 175)
    pr("  D1 [prereg (a)] STALLED-WHEEL runs: engaged, |angle|>=30, idx 40-200, hands-light (|tq|<1216), rate/ref < 0.5, through the ON-CAR chain (Kp 248, Ki as flown).")
    pr("     r35 (Ki 0) = 7 runs / 14.8 s at idx 54-79.  V283 predicted <= 2 runs, none > 1.5 s.")
    for tag in ROUTES:
        r = routes[tag]
        R = SIM[tag][KI_ONCAR[tag]]
        ref = R["ref_deg"][r.i100]
        w = np.abs(r.wire) / CPD
        elig = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.tq_raw) < 1216)
        st = elig & (ref > 5) & (w < 0.5 * ref)
        for nm, nmin in (("runs >= 1.0 s [prereg]", 100), ("runs >= 0.5 s [r35 table]", 50)):
            rr = runs_of(st, nmin)
            pr("  %s %-26s: %d runs (%.1f s); longest %.1f s; eligible %.1f s; stalled frames %.1f s (%.3f of eligible)"
               % (tag, nm, len(rr), sum(b - a for a, b in rr) / FS, max([(b - a) / FS for a, b in rr] or [0]), elig.sum() / FS, st.sum() / FS, st.sum() / max(elig.sum(), 1)))
        for a, b in runs_of(st, 100)[:14]:
            i = r.i100[a:b]
            pr("       t0 %6.1f dur %3.1f ang %4.0f v %4.1f idx %3.0f | rate %4.1f ref %5.1f (r/ref %.2f) | |T| %4.0f | |I| %5.0f |P| %5.0f | tq %4.0f | 6-8.5 Hz rate %.1f deg/s"
               % (a / FS, (b - a) / FS, np.median(np.abs(r.ang[a:b])), r.vego[a:b].mean(), np.median(r.idx[a:b]), np.median(w[a:b]), np.median(ref[a:b]),
                  np.median(w[a:b]) / max(np.median(ref[a:b]), 1e-9), np.median(np.abs(r.T_meas[a:b])), np.median(np.abs(R["I"][i])), np.median(np.abs(R["P_raw"][i])),
                  np.median(np.abs(r.tq_raw[a:b])), ST.band_amp(r.wire[a:b]) / CPD if b - a >= 40 else np.nan))

    pr("\n  D2 [prereg (b)] idx 40-80 WHEEL RATE vs the map REFERENCE, hands-light strong turns (|angle|>=30, |tq|<1216).  r35 13.6 vs 30 deg/s (45 %).  V283 predicted >= 22 deg/s (>= 70 %).")
    for tag in ROUTES:
        r = routes[tag]
        R = SIM[tag][KI_ONCAR[tag]]
        ref = R["ref_deg"][r.i100]
        w = np.abs(r.wire) / CPD
        cells = []
        for lo, hi_ in ((20, 40), (40, 80), (80, 120), (120, 200), (200, 241)):
            m = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= lo) & (r.idx < hi_) & (np.abs(r.tq_raw) < 1216)
            if m.sum() < 30:
                cells.append("idx %3d-%3d: n %4d --" % (lo, hi_, m.sum()))
                continue
            cells.append("idx %3d-%3d: n %5d rate %5.1f / ref %5.1f = %.2f | |T| %4.0f" % (lo, hi_, m.sum(), np.median(w[m]), np.median(ref[m]),
                         np.median(w[m]) / max(np.median(ref[m]), 1e-9), np.median(np.abs(r.T_meas[m]))))
        pr("  %s  %s" % (tag, "  ||  ".join(cells)))

    pr("\n  D3 [prereg (c) / (k)] the DEADBAND: engaged, idx 20-40, |rate| < 1 deg/s, |angle| > 10 -- fraction of the idx cell.  r35 0.114 all / 0.336 speed-matched 8-12 m/s; r34 0.041.")
    for tag in ROUTES:
        r = routes[tag]
        w = np.abs(r.wire) / CPD
        out = []
        for lo, hi_ in ((20, 40), (40, 80), (80, 120)):
            base = r.eng & (r.idx >= lo) & (r.idx < hi_) & (np.abs(r.ang) > 10)
            k = base & (w < 1.0)
            out.append("idx %3d-%3d: %.3f (%.1f s of %.1f s)" % (lo, hi_, k.sum() / max(base.sum(), 1), k.sum() / FS, base.sum() / FS))
        pr("  %s ALL SPEEDS   %s" % (tag, "  |  ".join(out)))
        for vlo, vhi in ((3, 8), (8, 12)):
            out = []
            for lo, hi_ in ((20, 40), (40, 80)):
                base = r.eng & (r.idx >= lo) & (r.idx < hi_) & (np.abs(r.ang) > 10) & (r.vego >= vlo) & (r.vego < vhi) & (np.abs(r.tq_raw) < 1216)
                k = base & (w < 1.0)
                out.append("idx %3d-%3d: %.3f (%.1f s of %.1f s)" % (lo, hi_, k.sum() / max(base.sum(), 1), k.sum() / FS, base.sum() / FS))
            pr("  %s v %2d-%2d m/s  %s" % (tag, vlo, vhi, "  |  ".join(out)))

    pr("\n  D4 [prereg (d)] STALL-RELEASE OVERSHOOT: for every stall run >= 0.5 s, the peak wheel rate in the 2.5 s AFTER it ends, minus the reference then.")
    pr("     Cost FAIL if > +20 deg/s or lasting > 3 s.  Predicted <= +12 deg/s for <= 2 s (BELIEF, clamp-set).")
    for tag in ROUTES:
        r = routes[tag]
        R = SIM[tag][KI_ONCAR[tag]]
        ref = R["ref_deg"][r.i100]
        w = np.abs(r.wire) / CPD
        st = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.tq_raw) < 1216) & (ref > 5) & (w < 0.5 * ref)
        rows = []
        for a, b in runs_of(st, 50):
            e2 = min(b + 250, len(w))
            if e2 - b < 50 or not r.eng[b:e2].all():
                continue
            over = w[b:e2] - ref[b:e2]
            rows.append((a / FS, (b - a) / FS, float(over.max()), float(np.sum(over > 0) / FS)))
        if rows:
            pr("  %s: %d releases | peak over-reference p50 %+.1f p90 %+.1f max %+.1f deg/s | time above reference p50 %.2f p90 %.2f s | worst: %s"
               % (tag, len(rows), np.median([x[2] for x in rows]), np.percentile([x[2] for x in rows], 90), max(x[2] for x in rows),
                  np.median([x[3] for x in rows]), np.percentile([x[3] for x in rows], 90),
                  "  ".join("t0 %.1f +%.1f for %.2f s" % (x[0], x[2], x[3]) for x in sorted(rows, key=lambda z: -z[2])[:4])))
        else:
            pr("  %s: no stall releases with 2.5 s of engaged follow-through" % tag)

    pr("\n  D5 THE 0.2-1 Hz INTEGRATOR HUNT (the pre-registered integrator signature).  Rate band amplitude, deg/s, over >= 5 s engaged runs; 1-2 Hz is the neighbour control.")
    for tag in ROUTES:
        r = routes[tag]
        for lab, m in (("STRAIGHT v>=8, |ang|<5", r.eng & (np.abs(r.ang) < 5) & (r.vego >= 8)),
                       ("STRAIGHT v>=15, |ang|<5", r.eng & (np.abs(r.ang) < 5) & (r.vego >= 15)),
                       ("TURN |ang|>=30, v<=10", r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10)),
                       ("CURVE |ang| 10-30", r.eng & (np.abs(r.ang) >= 10) & (np.abs(r.ang) < 30))):
            runs = V.runs(m, 500)
            if runs.sum() < 1024:
                pr("  %s %-24s: %.1f s -- too short" % (tag, lab, runs.sum() / FS))
                continue
            f, P = signal.welch(r.wire[runs] - r.wire[runs].mean(), fs=FS, nperseg=1024)
            _, Pc = signal.welch(r.cmd[runs] - r.cmd[runs].mean(), fs=FS, nperseg=1024)
            _, Pt = signal.welch(r.T_meas[runs] - r.T_meas[runs].mean(), fs=FS, nperseg=1024)
            pr("  %s %-24s %6.1f s | RATE deg/s 0.2-0.5 %.3f  0.5-1 %.3f  1-2 %.3f  2-4 %.3f | CMD 0.2-1 %5.0f 1-2 %5.0f | TAP 0.2-1 %5.0f 1-2 %5.0f"
               % (tag, lab, runs.sum() / FS, band_amp_psd(f, P, 0.2, 0.5) / CPD, band_amp_psd(f, P, 0.5, 1.0) / CPD, band_amp_psd(f, P, 1, 2) / CPD,
                  band_amp_psd(f, P, 2, 4) / CPD, band_amp_psd(f, Pc, 0.2, 1), band_amp_psd(f, Pc, 1, 2), band_amp_psd(f, Pt, 0.2, 1), band_amp_psd(f, Pt, 1, 2)))

    pr("\n  D6 SPECTRA in strong turns (engaged, |angle|>=30, v<=10, >=1 s runs; Welch 256) -- rate deg/s and tap counts by band; and 8.5-10 Hz on straights [prereg (f)].")
    bands = ((1, 2), (2, 4), (4, 6), (6, 8.5), (8.5, 10), (10, 12), (12, 15), (15, 22))
    for tag in ROUTES:
        r = routes[tag]
        for lab, m in (("ALL strong", r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10)),
                       ("hands-light idx>=40", r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10) & (np.abs(r.tq_raw) < 1216) & (r.idx >= 40)),
                       ("hands-on >=1216", r.eng & (np.abs(r.ang) >= 30) & (r.vego <= 10) & (np.abs(r.tq_raw) >= 1216))):
            runs = V.runs(m, 100)
            if runs.sum() < 300:
                pr("  %s %-20s: %.1f s -- too short" % (tag, lab, runs.sum() / FS))
                continue
            f, Pr = signal.welch(r.wire[runs] - r.wire[runs].mean(), fs=FS, nperseg=256)
            _, Pt = signal.welch(r.T_meas[runs] - r.T_meas[runs].mean(), fs=FS, nperseg=256)
            _, Pq = signal.welch(r.tq_raw[runs] - r.tq_raw[runs].mean(), fs=FS, nperseg=256)
            mm = (f >= 3) & (f <= 15)
            pr("  %s %-20s %6.1f s | RATE deg/s: %s | peak 3-15 Hz %.1f | TAP: %s | BAR 4-8.5/8.5-12: %.0f/%.0f"
               % (tag, lab, runs.sum() / FS, " ".join("%g-%g %.2f" % (lo, hi_, band_amp_psd(f, Pr, lo, hi_) / CPD) for lo, hi_ in bands),
                  f[mm][np.argmax(Pr[mm])], " ".join("%g-%g %.0f" % (lo, hi_, band_amp_psd(f, Pt, lo, hi_)) for lo, hi_ in bands),
                  band_amp_psd(f, Pq, 4, 8.5), band_amp_psd(f, Pq, 8.5, 12)))
        st = r.eng & (np.abs(r.ang) < 5) & (r.vego >= 8)
        runs = V.runs(st, 512)
        if runs.sum() > 512:
            f, Pr = signal.welch(r.wire[runs] - r.wire[runs].mean(), fs=FS, nperseg=512)
            pr("  %s STRAIGHT >=8 m/s %6.1f s: rate 2-4 %.2f  3.5-4.3 %.2f  6-8.5 %.2f  8.5-10 %.3f  10-12 %.3f deg/s [prereg (f): r35 0.496, r34 0.688]"
               % (tag, st.sum() / FS, band_amp_psd(f, Pr, 2, 4) / CPD, band_amp_psd(f, Pr, 3.5, 4.3) / CPD, band_amp_psd(f, Pr, 6, 8.5) / CPD,
                  band_amp_psd(f, Pr, 8.5, 10) / CPD, band_amp_psd(f, Pr, 10, 12) / CPD))

    pr("\n  D7 P-DESATURATION: the r35 mechanism was P pulling back on a stalled wheel.  P-rail duty and |P|/clamp in strong turns; and the P/I/D split there.")
    for tag in ROUTES:
        r = routes[tag]
        R = SIM[tag][KI_ONCAR[tag]]
        m = r.eng & (np.abs(r.ang) >= 30) & (r.idx >= 40) & (r.idx <= 200) & (np.abs(r.tq_raw) < 1216)
        if m.sum() < 100:
            continue
        i = r.i100[m]
        pr("  %s strong hands-light n %5d: P-rail duty %.3f | |P| p50 %5.0f (%.2f of clamp) | |I| p50 %5.0f p90 %5.0f | |D| p50 %5.0f | sum-clamp duty %.3f | |T_meas| p50 %4.0f"
           % (tag, m.sum(), float(np.mean(np.abs(R["P_raw"][i]) >= V.P_CLAMP)), np.median(np.abs(R["P_raw"][i])), np.median(np.abs(R["P_raw"][i])) / V.P_CLAMP,
              np.median(np.abs(R["I"][i])), np.percentile(np.abs(R["I"][i]), 90), np.median(np.abs(R["D_raw"][i])),
              float(np.mean(np.abs(R["S_raw"][i]) >= V.SUM_CLAMP)), np.median(np.abs(r.T_meas[m]))))

    # ------------------------------------------------------------------------------------------- E
    pr("\n" + "=" * 175)
    pr("SECTION E -- AUTHORITY and the hands-on case [prereg (h)].")
    pr("=" * 175)
    for tag in ROUTES:
        r = routes[tag]
        o = ST.stat_iv(r)
        pr("%s (iv) full-demand hands-light rate p50/p90: " % tag + " | ".join("<%4d: n=%4d %5.1f/%5.1f" % (t, *o[t]) for t in (2240, 1000, 400, 200))
           + " | (v) tap |T| p50/p90 %.0f/%.0f" % (o["tap"][0], o["tap"][1]))
        for lo, hi_ in ((40, 84), (84, 140)):
            m = r.eng & (r.idx >= lo) & (r.idx < hi_) & (np.abs(r.tq_raw) >= 2240)
            if m.sum() < 30:
                pr("      (h) idx %3d-%3d hands-ON (|tq|>=2240): n %4d -- too few" % (lo, hi_, m.sum()))
                continue
            pr("      (h) idx %3d-%3d hands-ON (|tq|>=2240): n %5d (%.1f s) | tap |T| p50 %4.0f p90 %4.0f max %4.0f  [r35 <= 1281 at Ki 0; V283 predicted rising toward the 2462 cap]"
               % (lo, hi_, m.sum(), m.sum() / FS, np.median(np.abs(r.T_meas[m])), np.percentile(np.abs(r.T_meas[m]), 90), np.abs(r.T_meas[m]).max()))
        D = dict(np.load(os.path.join(V.CACHE, tag + ".npz")))
        t0 = D["t18"][0]
        e1 = np.interp(D["t1ab"] - t0, r.tg, r.eng.astype(float)) > 0.5
        m = r.eng & (np.abs(r.cmd) < 1300) & (r.T_meas != 0) & (r.wire != 0)
        pr("      (vi) low-command damping fraction %.3f (n=%d) | (viii) P(|field|>=309) %.4f, max |field| %d, field==313 anywhere: %d"
           % (float(np.mean(np.sign(r.T_meas[m]) != np.sign(r.wire[m]))), m.sum(), float(np.mean((r.fld[e1] & 511) >= 309)), int((r.fld[e1] & 511).max()), int(np.sum(r.fld == 313))))

    out = os.path.join(HERE, "_scratch", "stutter_v283.txt")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "w", encoding="utf-8") as fh:
        fh.write("\n".join(L) + "\n")
    print("wrote", out)


if __name__ == "__main__":
    main()
