# -*- coding: utf-8 -*-
"""SECTION N -- independent verification of the amplitude stream's decision-bearing numbers.

N1  SECOND INSTRUMENT: repeat the headline cells with the controller's own achieved lateral accel
    (controlsState.lateralControlState.actualLateralAccel) instead of livePose yaw x v.  These are
    different measurement paths; a conclusion that flips between them is not a conclusion.
N2  SECOND ESTIMATOR, purely TIME DOMAIN: band-pass both signals, then
      NE_td  = RMS(y - x) / RMS(x)  over the cell's windows
      lag_td = the lag that maximises the cross-correlation of the band-passed pair
    No Welch, no cross spectrum.  Must reproduce the spectral NE and the spectral lag.
N3  AMPLITUDE METRIC ROBUSTNESS: redo the trend with p95 of |band-passed demand| instead of its RMS.
N4  STABILITY AT 2-8 m/s: the same low-speed cell under three different binnings, to show how far the
    torque estimate moves when n is 8-26 windows.

ANALYSIS ONLY.  Run: python verify.py
"""
import os, sys
import numpy as np
from scipy import signal

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import dflib as D            # noqa: E402
import fastH as FH           # noqa: E402
import v282cmp as C          # noqa: E402

GROUPS = {"V282": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
          "V282old": ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4"],
          "TQall": ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd",
                    "00000076--d0b7ea7e4d", "00000075--6c8687d5bd"]}
MIN_WIN = 8
LOG = []


def pr(s=""):
    print(s, flush=True)
    LOG.append(s)


RUNS = {}
for rk in C.ROUTES:
    RUNS[rk], _ = D.route_runs(rk)


def build(ykey, hop_div=2, amp_metric="rms"):
    S = {}
    for f1, f2, W in D.BANDS:
        WS = {}
        for rk in C.ROUTES:
            ws = D.windows(RUNS[rk], W, hop=W // hop_div, ykey=ykey)
            for w in ws:
                xb = signal.sosfiltfilt(D.sos(f1, f2), w["x"].astype(float))
                yb = signal.sosfiltfilt(D.sos(f1, f2), w["y"].astype(float))
                w["A"] = float(np.sqrt(np.mean(xb ** 2))) if amp_metric == "rms" \
                    else float(np.percentile(np.abs(xb), 95))
                w["xb"], w["yb"] = xb, yb
                w["spec"] = FH.win_spec(w, f1, f2, W)
            WS[rk] = ws
        S[(f1, f2, W)] = WS
    return S


def gather(WS, rks, slo, shi, lo=0.0, hi=1e9):
    out = []
    for ri, rk in enumerate(rks):
        for w in WS[rk]:
            if slo <= w["v"] < shi and lo <= w["A"] < hi:
                w2 = dict(w); w2["cid"] = (ri, w["rid"]); out.append(w2)
    return out


def td_metrics(ws, maxlag=80):
    """time-domain NE and lag on the band-passed pair -- no spectra anywhere"""
    num = den = 0.0
    for w in ws:
        num += float(np.sum((w["yb"] - w["xb"]) ** 2)); den += float(np.sum(w["xb"] ** 2))
    ne = float(np.sqrt(num / max(den, 1e-30)))
    cc = np.zeros(2 * maxlag + 1)
    for w in ws:
        x, y = w["xb"], w["yb"]
        for i, L in enumerate(range(-maxlag, maxlag + 1)):
            xa, ya = (x[:len(x) - L], y[L:]) if L >= 0 else (x[-L:], y[:len(y) + L])
            cc[i] += float(np.dot(xa, ya))
    lag = (int(np.argmax(cc)) - maxlag) / D.FS
    return ne, lag


def bins(WS, slo, shi):
    pooled = [w["A"] for g in ("V282", "V282old") for rk in GROUPS[g] for w in WS[rk]
              if slo <= w["v"] < shi]
    pooled += [w["A"] for rk in GROUPS["TQall"][:2] for w in WS[rk] if slo <= w["v"] < shi]
    if len(pooled) < 5 * MIN_WIN:
        return None
    ed = [float(q) for q in np.percentile(pooled, [0, 25, 50, 75, 90, 100])]
    ed[0], ed[-1] = 0.0, 1e9
    return ed


HEAD = [((0.08, 0.25, 2048), (15, 22)), ((0.15, 0.30, 1024), (8, 15)),
        ((0.15, 0.30, 1024), (15, 22)), ((0.15, 0.30, 1024), (22, 40)),
        ((0.30, 0.60, 1024), (8, 15)), ((0.30, 0.60, 1024), (15, 22))]

# ================================================================================= N1 + N2
for ykey, nm in (("y", "livePose yaw x v  (primary)"), ("ya", "controlsState actualLateralAccel (2nd)")):
    SURF = build(ykey)
    pr("=" * 140)
    pr(f"N1/N2   ACHIEVED SIGNAL = {nm}")
    pr("=" * 140)
    pr(f"{'band':>11s} {'v':>7s} {'Q':>2s} {'medA':>7s} | {'V282 H':>7s}{'NE':>6s}{'NEtd':>6s}"
       f"{'lag':>6s}{'lagtd':>7s}{'n':>5s} | {'TQ H':>6s}{'NE':>6s}{'NEtd':>6s}{'lag':>6s}{'lagtd':>7s}"
       f"{'n':>5s} | {'NE x':>6s} {'NEtd x':>7s} {'dlag':>6s} {'dlagtd':>7s}")
    for (f1, f2, W), (slo, shi) in HEAD:
        WS = SURF[(f1, f2, W)]
        ed = bins(WS, slo, shi)
        if ed is None:
            continue
        for q in range(5):
            wv = gather(WS, GROUPS["V282"], slo, shi, ed[q], ed[q + 1])
            wt = gather(WS, GROUPS["TQall"], slo, shi, ed[q], ed[q + 1])
            if len(wv) < MIN_WIN or len(wt) < MIN_WIN:
                continue
            v, t = FH.pool([w["spec"] for w in wv]), FH.pool([w["spec"] for w in wt])
            if min(v["coh"], t["coh"]) < D.COH_MIN:
                continue
            nv, lv = td_metrics(wv); nt, lt = td_metrics(wt)
            pr(f"{f'{f1:.2f}-{f2:.2f}':>11s} {f'{slo}-{shi}':>7s} {q+1:2d} "
               f"{float(np.median([w['A'] for w in wv])):7.4f} | "
               f"{v['H']:7.2f}{v['NE']:6.2f}{nv:6.2f}{1000*v['lag']:+6.0f}{1000*lv:+7.0f}{len(wv):5d} | "
               f"{t['H']:6.2f}{t['NE']:6.2f}{nt:6.2f}{1000*t['lag']:+6.0f}{1000*lt:+7.0f}{len(wt):5d} | "
               f"{t['NE']/max(v['NE'],1e-9):6.2f} {nt/max(nv,1e-9):7.2f} "
               f"{1000*(t['lag']-v['lag']):+6.0f} {1000*(lt-lv):+7.0f}")
    pr("")
    del SURF

# ================================================================================= N3
pr("=" * 140)
pr("N3   AMPLITUDE METRIC ROBUSTNESS -- bins built on p95 of |band-passed demand| instead of its RMS")
pr("=" * 140)
SURF = build("y", 2, amp_metric="p95")
pr(f"{'band':>11s} {'v':>7s} {'Q':>2s} {'p95A':>7s} | {'V282 H':>7s}{'NE':>6s}{'lag':>6s} | "
   f"{'TQ H':>6s}{'NE':>6s}{'lag':>6s} | {'NE x':>6s} {'dlag':>6s}")
for (f1, f2, W), (slo, shi) in HEAD:
    WS = SURF[(f1, f2, W)]
    ed = bins(WS, slo, shi)
    if ed is None:
        continue
    for q in range(5):
        wv = gather(WS, GROUPS["V282"], slo, shi, ed[q], ed[q + 1])
        wt = gather(WS, GROUPS["TQall"], slo, shi, ed[q], ed[q + 1])
        if len(wv) < MIN_WIN or len(wt) < MIN_WIN:
            continue
        v, t = FH.pool([w["spec"] for w in wv]), FH.pool([w["spec"] for w in wt])
        if min(v["coh"], t["coh"]) < D.COH_MIN:
            continue
        pr(f"{f'{f1:.2f}-{f2:.2f}':>11s} {f'{slo}-{shi}':>7s} {q+1:2d} "
           f"{float(np.median([w['A'] for w in wv])):7.4f} | {v['H']:7.2f}{v['NE']:6.2f}"
           f"{1000*v['lag']:+6.0f} | {t['H']:6.2f}{t['NE']:6.2f}{1000*t['lag']:+6.0f} | "
           f"{t['NE']/max(v['NE'],1e-9):6.2f} {1000*(t['lag']-v['lag']):+6.0f}")
pr("")
del SURF

# ================================================================================= N4
pr("=" * 140)
pr("N4   STABILITY AT 2-8 m/s -- the same question under three binnings (this is where n is too thin)")
pr("=" * 140)
for hop_div, tag in ((2, "50% overlap"), (4, "75% overlap")):
    SURF = build("y", hop_div)
    for f1, f2, W in D.BANDS[1:4]:
        WS = SURF[(f1, f2, W)]
        pooled = [w["A"] for g in ("V282", "V282old") for rk in GROUPS[g] for w in WS[rk] if 2 <= w["v"] < 8]
        if len(pooled) < 20:
            continue
        for scheme, qs in (("median split", [0, 50, 100]), ("terciles", [0, 33, 67, 100]),
                           ("quartiles", [0, 25, 50, 75, 100])):
            ed = [float(q) for q in np.percentile(pooled, qs)]
            ed[0], ed[-1] = 0.0, 1e9
            outs = []
            for q in range(len(ed) - 1):
                wv = gather(WS, GROUPS["V282"], 2, 8, ed[q], ed[q + 1])
                wt = gather(WS, GROUPS["TQall"], 2, 8, ed[q], ed[q + 1])
                if len(wv) < MIN_WIN or len(wt) < MIN_WIN:
                    outs.append("     --      ")
                    continue
                v, t = FH.pool([w["spec"] for w in wv]), FH.pool([w["spec"] for w in wt])
                outs.append(f"H{v['H']:4.2f}/{t['H']:4.2f} dlag{1000*(t['lag']-v['lag']):+5.0f}"
                            f" n{len(wt):3d}")
            pr(f"  {f1:.2f}-{f2:.2f} Hz {tag:11s} {scheme:12s} | " + " | ".join(outs))
    del SURF
pr("")

with open(os.path.join(HERE, "VERIFY-OUT.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(LOG) + "\n")
