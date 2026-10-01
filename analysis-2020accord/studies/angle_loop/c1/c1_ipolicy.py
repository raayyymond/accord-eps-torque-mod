# -*- coding: utf-8 -*-
"""c1_ipolicy.py -- choose the I policy with BYTES in mind: the friction refuter's three driver-torque / engage
scenarios (expC light-hand override, expD engage under load, expF co-steer release -- their logic, re-implemented here
per column so several policies run in ONE batch on identical inputs), plus a fourth the refuters did not run:
E4 LONG OVERRIDE WITH FORK O1 (the driver takes the wheel out of a held curve for 3 s, the fork's theta_sp follows
the 60 ms-old measured angle, then he lets go and the fork holds theta_sp where he left it) -- the stale-I case that a
FREEZE (unlike a bleed) leaves in place.

Policies (each a column; every one runs the C1 gains):
  C1         freeze I when |gp-0x4f68| > 512 or ramp < 0x8000                         (cave +14 B over the bare return)
  C1-noramp  freeze I when |gp-0x4f68| > 512 only                                       (-6 B)
  C1-1024    freeze when |tq| > 1024, + ramp
  C1+reset   C1 + st.w r0,-0x6dd0[gp] when |tq| > 2048 (the fade floor)                (+10 B, a RAM write)
  C0-bleed   8I -= 8I >> 6 when |tq| > 1024 (C0's policy, the listing's arithmetic)
  none       no I handling (control)
Plant / sensors / fork frame: refute_friction/fric_lib.run (the harness's PlantVec Karnopp model, 100 Hz hold,
60 ms-old fork angle).  ANALYSIS ONLY.  usage: python c1_ipolicy.py [E1|E2|E3|E4|all]"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import c1_lib as C  # noqa: E402

F = C.install_fric(tbl=C.c1_table(), thr=C.FRZ_THR, rampfrz=True, pol="freeze")
POL = {
    "C1": dict(pol="freeze", thr=512, rampfrz=True),
    "C1-noramp": dict(pol="freeze", thr=512, rampfrz=False),
    "C1-1024": dict(pol="freeze", thr=1024, rampfrz=True),
    "C1+reset": dict(pol="freeze", thr=512, rampfrz=True, reset_thr=2048),
    "C0-bleed": dict(pol="bleed", bleed_thr=1024, bleed_sh=6, rampfrz=False, thr=0),
    "none": dict(pol="none", rampfrz=False, thr=0),
}
_COLS = []


class _Lane(C.LaneC1F):
    def __init__(self, B, **kw):
        cols = [dict(tbl=C.c1_table(), **POL[c["pol"]]) for c in _COLS] if len(_COLS) == B else None
        super().__init__(B, cols=cols, **kw)


F.LaneC0 = _Lane
OUTP = []


def P(s=""):
    OUTP.append(s)
    print(s, flush=True)


def run(cols, dur, **kw):
    _COLS[:] = cols
    return F.run(cols, dur, **kw)


# ---------------------------------------------------------------------------------------------------- E1 light hand
def E1(pols=("C1", "C1-1024", "C0-bleed", "none")):
    SPEEDS = (5.0, 8.0, 12.5, 19.0, 26.0)
    TQS = (0, 300, 500, 700, 1000, 1100, 2400)
    H, TG, TRAMP = 3.0, 1.0, 0.3
    TREL = TG + TRAMP + H
    DUR = TREL + 4.0

    def hand(delta):
        def h(t):
            if TG <= t < TREL:
                return (2000.0, 30.0, -min(1.0, (t - TG) / TRAMP) * delta)
            return None
        return h

    def tqf(a):
        return lambda t: (a * min(1.0, (t - TG) / TRAMP) if TG <= t < TREL else
                          (a * (1 - (t - TREL) / 0.03) if TREL <= t < TREL + 0.03 else 0.0))
    cols = [dict(member="nominal", v=v, delta=dl, tqa=a, pol=p, ref=lambda t: 0.0, hand=hand(dl), tq=tqf(a))
            for v in SPEEDS for dl in (0.5, 1.0, 2.0) for a in TQS for p in pols]
    rec = run(cols, DUR, rec_I=True)
    tt = np.arange(rec["th"].shape[0]) * 1e-3
    i_end = int(TREL * 1000) - 5
    w = tt >= TREL
    P("E1 LIGHT-HAND OVERRIDE (expC's logic; theta_sp = 0, the hand holds delta for 3 s, then releases in 30 ms): "
      "release overshoot deg [T fought / I share T]")
    res = []
    for j, c in enumerate(cols):
        T = rec["T"][:, j].astype(float); th = rec["th"][:, j].astype(float)
        I = rec["I"][:, j].astype(float); f = rec["f"][:, j]
        Ish = I[i_end] * f[i_end] / 256.0 * 5346 / 32768.0
        res.append(dict(v=c["v"], delta=c["delta"], tq=c["tqa"], pol=c["pol"], ov=float(th[w].max()),
                        Tf=float(T[i_end]), Ish=float(Ish)))
    for v in SPEEDS:
        for dl in (0.5, 1.0, 2.0):
            cells = []
            for a in TQS:
                cc = [r for r in res if r["v"] == v and r["delta"] == dl and r["tq"] == a]
                cells.append(f"|tq| {a:4d}: " + " ".join(f"{r['pol']}={r['ov']:.2f}[{r['Tf']:.0f}/{r['Ish']:.0f}]" for r in cc))
            P(f"  v {v:4.1f} delta {dl:3.1f}: " + "  ".join(cells))
    return res


# ---------------------------------------------------------------------------------------------------- E2 engage
def E2(pols=("C1", "C1-noramp", "C0-bleed")):
    CASES = {3.0: 45.0, 5.0: 25.0, 8.0: 15.0, 12.5: 6.0, 19.0: 2.5, 26.0: 1.5}
    LAGS = (0.0, 0.3, 1.0)
    TE = 2.0
    DUR = TE + 6.0

    def hand(th0, lag):
        def h(t):
            if t < TE + lag:
                return (2000.0, 30.0, th0)
            frac = min(1.0, (t - TE - lag) / 0.2)
            if frac >= 1.0:
                return None
            return (2000.0 * (1 - frac), 30.0 * (1 - frac), th0)
        return h
    cols = [dict(member="nominal", v=v, th0=th0, lag=lag, pol=p, ref=lambda t: 0.0, hand=hand(th0, lag),
                 mode=lambda t: "off" if t < TE else "engage_ramp",
                 sp_src=lambda t: "meas" if t < TE + 0.011 else "hold")
            for v, th0 in CASES.items() for lag in LAGS for p in pols]
    rec = run(cols, DUR, rec_I=True)
    tt = np.arange(rec["th"].shape[0]) * 1e-3
    w = tt >= TE
    P("\nE2 ENGAGE UNDER LOAD (expD's logic): droop deg / overshoot deg / slips / peak T, per policy")
    res = []
    for j, c in enumerate(cols):
        th = rec["th"][:, j].astype(float); sp = rec["sp"][:, j].astype(float); T = rec["T"][:, j].astype(float)
        e = (sp - th)[w] * np.sign(c["th0"])
        sl = F.slips(rec, TE, DUR)[j]
        res.append(dict(v=c["v"], th0=c["th0"], lag=c["lag"], pol=c["pol"], droop=float(e.max()), ovs=float((-e).max()),
                        slips=int(sl), peakT=float(np.abs(T[w]).max()), e_end=float(abs(e[-1]))))
    for v, th0 in CASES.items():
        for lag in LAGS:
            cc = [r for r in res if r["v"] == v and r["lag"] == lag]
            P(f"  v {v:4.1f} curve {th0:4.1f} deg, release {lag:3.1f} s after engage: " + " | ".join(
                f"{r['pol']}: {r['droop']:.2f} / {r['ovs']:.2f} / {r['slips']} / {r['peakT']:.0f}" for r in cc))
    return res


# ---------------------------------------------------------------------------------------------------- E3 co-steer
def E3(pols=("C1", "C1-1024", "C0-bleed", "none")):
    fam = F.VP.family()
    CASES = {5.0: 25.0, 8.0: 15.0, 12.5: 6.0, 19.0: 2.5, 26.0: 1.5}
    TH, T1, T2 = 3.0, 5.0, 7.0
    DUR = 11.0
    cols = []
    for v, A in CASES.items():
        p = fam["nominal"].at(v)
        load = p.k * p.sat * np.tanh(A / p.sat)
        for share in (0.5, 1.0):
            for tqa in (700, 1500):
                for pol in pols:
                    dval = share * load
                    cols.append(dict(member="nominal", v=v, A=A, share=share, tqa=tqa, pol=pol,
                                     ref=lambda t, A=A: float(np.interp(t, [0, 0.5, TH, 100], [0, 0, A, A])),
                                     d=lambda t, dv=dval: dv * float(np.clip((t - T1) / 0.2, 0, 1)) if t < T2 else
                                     dv * float(np.clip(1 - (t - T2) / 0.05, 0, 1)),
                                     tq=lambda t, a=tqa: a if T1 <= t < T2 else 0))
    rec = run(cols, DUR, rec_I=True)
    tt = np.arange(rec["th"].shape[0]) * 1e-3
    P("\nE3 CO-STEER RELEASE (expF's logic; a helping hand for 2 s, then release): droop after release deg [I at "
      "release T]")
    res = []
    for j, c in enumerate(cols):
        th = rec["th"][:, j].astype(float); sp = rec["sp"][:, j].astype(float); I = rec["I"][:, j].astype(float)
        e = (sp - th)[tt >= T2]
        Ir = I[int(T2 * 1000) - 2] * 5346 / 32768.0
        res.append(dict(v=c["v"], share=c["share"], tq=c["tqa"], pol=c["pol"], droop=float(e.max()), I_T=float(Ir)))
    for v, A in CASES.items():
        for share in (0.5, 1.0):
            for tqa in (700, 1500):
                cc = [r for r in res if r["v"] == v and r["share"] == share and r["tq"] == tqa]
                P(f"  v {v:4.1f} curve {A:4.1f} share {share:3.1f} |tq| {tqa:4d}: " + " | ".join(
                    f"{r['pol']}: {r['droop']:.2f} [{r['I_T']:.0f}]" for r in cc))
    return res


# ---------------------------------------------------------------------------------------------------- E4 long override
def E4(pols=("C1", "C1+reset", "C0-bleed", "none")):
    CASES = {5.0: 25.0, 8.0: 15.0, 12.5: 6.0, 19.0: 2.5, 26.0: 1.5}
    TG, TRAMP, H = 4.0, 0.3, 3.0
    TREL = TG + TRAMP + H
    DUR = TREL + 4.0
    cols = []
    for v, A in CASES.items():
        for tgt_frac, lab in ((0.0, "straighten"), (1.5, "tighten x1.5")):
            for tqa in (1500, 2400):
                for pol in pols:
                    def hand(t, A=A, fr=tgt_frac):
                        if TG <= t < TREL:
                            k = min(1.0, (t - TG) / TRAMP)
                            return (2000.0, 30.0, A + k * (fr * A - A))
                        return None
                    cols.append(dict(member="nominal", v=v, A=A, lab=lab, tqa=tqa, pol=pol,
                                     ref=lambda t, A=A: float(np.interp(t, [0, 0.5, 2.0, 100], [0, 0, A, A])),
                                     hand=hand,
                                     tq=lambda t, a=tqa: (a * min(1.0, (t - TG) / TRAMP) if TG <= t < TREL else
                                                          (a * (1 - (t - TREL) / 0.03) if TREL <= t < TREL + 0.03 else 0.0)),
                                     sp_src=lambda t: "ref" if t < TG else ("meas" if t < TREL else "hold")))
    rec = run(cols, DUR, rec_I=True)
    tt = np.arange(rec["th"].shape[0]) * 1e-3
    w = (tt >= TREL) & (tt < TREL + 3.0)
    P("\nE4 LONG OVERRIDE WITH FORK O1 (held curve A; the driver moves the wheel to frac*A for 3 s, theta_sp follows the "
      "60 ms-old wire angle; release; theta_sp held where he left it): lurch = max |theta - theta_release| in 3 s "
      "[I at release, T]")
    res = []
    for j, c in enumerate(cols):
        th = rec["th"][:, j].astype(float); I = rec["I"][:, j].astype(float); T = rec["T"][:, j].astype(float)
        th_rel = th[int(TREL * 1000) - 1]
        lurch = float(np.abs(th[w] - th_rel).max())
        Ir = I[int(TREL * 1000) - 2] * 5346 / 32768.0
        res.append(dict(v=c["v"], A=c["A"], lab=c["lab"], tq=c["tqa"], pol=c["pol"], lurch=lurch, I_T=float(Ir),
                        peakT=float(np.abs(T[w]).max())))
    for v, A in CASES.items():
        for lab in ("straighten", "tighten x1.5"):
            for tqa in (1500, 2400):
                cc = [r for r in res if r["v"] == v and r["lab"] == lab and r["tq"] == tqa]
                P(f"  v {v:4.1f} curve {A:4.1f} {lab:12s} |tq| {tqa}: " + " | ".join(
                    f"{r['pol']}: {r['lurch']:.2f} [{r['I_T']:.0f}]" for r in cc))
    return res


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else "all"
    res = {}
    for k, fn in (("E1", E1), ("E2", E2), ("E3", E3), ("E4", E4)):
        if which in (k, "all"):
            res[k] = fn()
    (C.OUT / f"ipolicy_{which}.json").write_text(json.dumps(res))
    (HERE / f"ipolicy_{which}.txt").write_text("\n".join(OUTP), encoding="utf-8")
