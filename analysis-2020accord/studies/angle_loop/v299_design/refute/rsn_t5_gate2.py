# -*- coding: utf-8 -*-
"""rsn_t5_gate2.py -- GATE 2, my own derivation: a FLOAT (untruncated) mirror of the V298/V299 lane's linear
structure (two-sample fb sum of the 100 Hz-held angle at age 0 / 10 ms, E' = E G/256, P Kp/256, I e5 Ki/8 per tick
(PID) or frozen (PD), D Kd abe/8 on the 37/128 EMA of the motor-frame rate, fade 254/256, output lag OB/OA, fwd 5346,
2 ms transport), closed around a LINEARISED plant (J, b, k sech^2(th/sat); friction off) at the operating angle, and
measured by SINUSOIDAL INJECTION at the plant input (L = T_applied / u, fundamental projection): PM / GM / fc per
point.  Then the fork O1 loop as L_O1 = L_in (1 - (1 + j w lead) e^{-j w Trt}) (sp = the wheel Trt ago + lead rate).
Points: members nominal, b_lo, J_hi, ms_free, b_lo*J_hi, b_lo*ms_free; speeds 3.1-26.9; op straight + curve-hold
2.5 m/s^2; hold age 0 / 10 ms; D x1 / x0.55 (route 79's measured D fraction) with P x0.93.  ANALYSIS ONLY."""
import json
import sys
import time
from multiprocessing import Pool
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import rsn_engine as E  # noqa: E402

FREQS = np.geomspace(0.35, 40.0, 26)
SPEEDS = (3.1, 5.0, 8.0, 10.0, 11.0, 11.75, 13.0, 15.0, 17.5, 20.0, 26.9)
MEMBERS = ("nominal", "b_lo", "J_hi", "ms_free", "b_lo*J_hi", "b_lo*ms_free")


def mparams(m, v):
    def at(nm):
        return {k: float(np.asarray(q).ravel()[0]) for k, q in E._FAM[nm].arrays_at(np.array([float(v)])).items()}
    if m == "b_lo*J_hi":
        a = at("J_hi")
        a["b"] *= (1 / 1.8 if v >= 10.0 else 0.7)
        return a
    if m == "b_lo*ms_free":
        a = at("ms_free")
        a["b"] *= at("b_lo")["b"] / at("nominal")["b"]
        return a
    return at(m)


def job(v):
    cols = []
    for m in MEMBERS:
        p = mparams(m, v)
        for op in ("str", "a2.5"):
            th = 0.0 if op == "str" else min(float(E.steer_from_curv(2.5 / v ** 2, v)), 400.0)
            keff = p["k"] / np.cosh(th / p["sat"]) ** 2
            kap = float(E.FRAME.kappa(th))
            for age in (0, 10):
                for dsc in (1.0, 0.55):
                    for mode in ("PID", "PD"):
                        for f in FREQS:
                            cols.append(dict(m=m, op=op, th=th, J=p["J"], b=p["b"], k=keff, kap=kap, age=age,
                                             dsc=dsc, mode=mode, f=f))
    B = len(cols)
    g = lambda q: np.array([c[q] for c in cols], float)  # noqa: E731
    J, b, k, kap, f, dsc = g("J"), g("b"), g("k"), g("kap"), g("f"), g("dsc")
    psc = np.where(dsc < 1, 0.93, 1.0)
    pid = np.array([c["mode"] == "PID" for c in cols])
    age = np.array([c["age"] for c in cols])
    G = float(E.G_walk(round(v * 230.4)))
    dt = 1e-3
    nsub = 10
    h = dt / nsub
    ncyc = np.maximum(np.floor(4.0 * f), 1.0)
    dur = np.maximum(6.0, (ncyc + 4.0) / f)
    nT = int(dur.max() * 1000)
    t_start = dur - ncyc / f
    th_ = np.zeros(B); om = np.zeros(B); held = np.zeros(B); held_prev = np.zeros(B); hist = np.zeros((11, B))
    I = np.zeros(B); st = np.zeros(B); olag = np.zeros(B); buf = np.zeros((3, B))
    w = 2 * np.pi * f
    accT = np.zeros(B, complex)
    accU = np.zeros(B, complex)
    fwd, ob, oa = E.CAL["FWD"], E.CAL["OB"], E.CAL["OA"]
    for n in range(nT):
        t = n * dt
        q = 10.0 * th_
        hist[n % 11] = q
        if n % 10 == 4:
            held = np.where(age == 10, hist[(n + 1) % 11], q)      # the sample 10 ticks older
        r26 = 8.0 * held + 8.0 * held_prev
        held_prev = held
        Ep = (-r26) * G / 256.0
        I = np.where(pid, I + (Ep / 32.0) * 40.0 / 8.0, I)
        P = psc * Ep * 112.0 / 256.0
        gm = E.ABE_PER * om / kap
        st = st + (gm * 1024.0 - st) * 37.0 / 128.0
        D = dsc * 48.0 * (st / 1024.0) / 8.0
        S = (I / 128.0 + P + D) * 254.0 / 256.0
        o_new = S * ob / 1024.0 + oa * olag / 1024.0
        y = (olag + o_new) / 32.0
        olag = o_new
        T = y * (-fwd) / 32768.0
        buf[n % 3] = T
        Td = buf[(n + 1) % 3]                                   # 2 ms transport
        u = 20.0 * np.sin(w * t) - Td
        for _ in range(nsub):
            om = om + (u - k * th_ - b * om) / J * h
            th_ = th_ + om * h
        if n >= int(t_start.min() * 1000):
            on = t >= t_start
            ph = np.exp(-1j * w * t)
            accT += np.where(on, Td * ph, 0)
            accU += np.where(on, u * ph, 0)
    L = accT / accU
    out = []
    keys = sorted(set((c["m"], c["op"], c["age"], c["dsc"], c["mode"]) for c in cols))
    for key in keys:
        idx = [i for i, c in enumerate(cols) if (c["m"], c["op"], c["age"], c["dsc"], c["mode"]) == key]
        out.append(dict(v=v, m=key[0], op=key[1], age=key[2], dsc=key[3], mode=key[4], f=f[idx].tolist(),
                        Lr=L[idx].real.tolist(), Li=L[idx].imag.tolist(), th=cols[idx[0]]["th"]))
    return out


def margins(f, L):
    mag = np.abs(L)
    ph = np.degrees(np.unwrap(np.angle(L)))
    pm = gm = fc = np.nan
    pms = []
    for i in np.flatnonzero((mag[:-1] >= 1) & (mag[1:] < 1)):
        a = np.log(mag[i]) / (np.log(mag[i]) - np.log(mag[i + 1]))
        p = ph[i] + a * (ph[i + 1] - ph[i])
        pms.append(((p + 360.0) % 360.0 - 180.0 + 180.0 if False else (p % 360.0) - 180.0,
                    float(np.exp(np.log(f[i]) + a * (np.log(f[i + 1]) - np.log(f[i]))))))
    if pms:
        pm, fc = min(pms)
    pp = ph % 360.0 - 180.0                                      # distance from -180 deg (0 = on it)
    gms = []
    for i in np.flatnonzero(np.diff(np.sign(pp)) != 0):
        if abs(pp[i]) < 60 and abs(pp[i + 1]) < 60:
            a = pp[i] / (pp[i] - pp[i + 1])
            gms.append(-20 * np.log10(np.exp(np.log(mag[i]) + a * (np.log(mag[i + 1]) - np.log(mag[i])))))
    gms = [x for x in gms if x > -1e9]
    if gms:
        gm = min(gms)
    return pm, gm, fc, float(mag.max())


def report(rows):
    def sel(**kw):
        return [r for r in rows if all((r[k] in v) if isinstance(v, tuple) else (r[k] == v) for k, v in kw.items())]
    print("worst inner PM per (mode, D scale) over the grid:")
    for mode in ("PID", "PD"):
        for dsc in (1.0, 0.55):
            d = sel(mode=mode, dsc=dsc)
            w = min(d, key=lambda r: r["pm"])
            print(f"  {mode} D x{dsc}: min PM {w['pm']:.1f} at {w['m']} v {w['v']} {w['op']} age {w['age']} fc "
                  f"{w['fc']:.2f}; min GM {np.nanmin([r['gm'] for r in d]):.1f} dB; n PM<30 "
                  f"{sum(r['pm'] < 30 for r in d)}/{len(d)}; max|S| {max(r['Smax'] for r in d):.2f}")
    for dsc in (1.0, 0.55):
        d = sel(mode="PID", dsc=dsc)
        bys = {}
        for r in d:
            bys[r["v"]] = min(bys.get(r["v"], 999), r["pm"])
        print(f"PID D x{dsc} worst PM by speed:", {k: round(v, 1) for k, v in sorted(bys.items())})
        ms = [r["pm"] for r in d if "ms_free" in r["m"]]
        ot = [r["pm"] for r in d if "ms_free" not in r["m"]]
        print(f"   ms_free family worst {min(ms):.1f}; others worst {min(ot):.1f}; sub-30 points: "
              f"{[(r['v'], r['m'], r['op'], r['age'], round(r['pm'], 1)) for r in d if r['pm'] < 30]}")
    for trt in (30, 60, 90):
        for lead in (0.0, 0.06):
            k = f"o1_{trt}_{lead}"
            pmv = np.array([r[k][0] for r in rows], float)
            gmv = np.array([r[k][1] for r in rows], float)
            smx = np.array([r[k][2] for r in rows], float)
            print(f"  O1 loop Trt {trt} ms lead {lead}: min PM {np.nanmin(pmv):.1f}  min GM {np.nanmin(gmv):.1f} dB "
                  f" max|S| {smx.max():.2f} (n PM<30 {(pmv < 30).sum()}, n GM<6 {(gmv < 6).sum()} of {len(rows)})")
    nom = sorted(sel(m="nominal", op="str", age=0, dsc=1.0, mode="PID"), key=lambda r: r["v"])
    print("nominal straight PID age0 (v, PM, GM, fc):", [(r["v"], round(r["pm"], 1), round(r["gm"], 1),
                                                           round(r["fc"], 2)) for r in nom])


if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "report":
    report(json.loads((E.OUT / "t5_gate2.json").read_text(encoding="utf-8")))


if __name__ == "__main__" and len(sys.argv) == 1:
    T0 = time.perf_counter()
    with Pool(len(SPEEDS)) as p:
        res = sum(p.map(job, SPEEDS), [])
    rows = []
    for r in res:
        f = np.array(r["f"])
        L = np.array(r["Lr"]) + 1j * np.array(r["Li"])
        pm, gm, fc, mx = margins(f, L)
        row = dict({k: r[k] for k in ("v", "m", "op", "age", "dsc", "mode")}, pm=pm, gm=gm, fc=fc,
                   Smax=float((1 / np.abs(1 + L)).max()))
        for trt in (0.03, 0.06, 0.09):
            for lead in (0.0, 0.06):
                Lo = L * (1 - (1 + 1j * 2 * np.pi * f * lead) * np.exp(-1j * 2 * np.pi * f * trt))
                pmo, gmo, _, _ = margins(f, Lo)
                row[f"o1_{int(round(trt * 1000))}_{lead}"] = [pmo, gmo, float((1 / np.abs(1 + Lo)).max())]
        rows.append(row)
    (E.OUT / "t5_gate2.json").write_text(json.dumps(rows, default=float), encoding="utf-8")
    report(rows)
    print(f"wall {time.perf_counter() - T0:.1f} s")
