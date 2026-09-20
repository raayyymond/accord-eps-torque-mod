# -*- coding: utf-8 -*-
"""TEST 2 -- the wheel mode: where is it, how damped, and has it moved?

The only excitation available above ~1 Hz is the road, so this is OPERATIONAL modal analysis: the
part of the wheel motion that the reference does NOT explain, fitted with

    PSD_incoherent(f) = A * f^alpha * |1 / (1 - (f/fn)^2 + 2 j zeta f/fn)|^2

i.e. a smooth broadband drive through one second-order mode.  The power law absorbs the unknown
road spectrum and everything else that is smooth in the band.

WHAT THIS CAN AND CANNOT SAY.  It measures the CLOSED-LOOP wheel response as flown; it cannot
separate "the plant's mode" from "the loop's contribution to it", because there is no loop-open
control (u0_census: ZERO seconds of longitudinal-only engaged driving at 8-22 m/s in the whole
corpus, and hands-on runs are all shorter than 6 s).  That limit is binding and is stated, not
worked around.

POSITIVE CONTROL: the same fit is run on synthetic noise through a KNOWN second-order mode and must
recover fn and zeta before any real number is printed.

out: U4-<TAG>-OUT.txt, u4_<tag>.json
"""
import json
import sys
import numpy as np
from scipy import optimize, signal
import ulib as U

TAG = sys.argv[1] if len(sys.argv) > 1 else "hi1k"
FITBAND = (0.8, 6.0)


def model(f, A, alpha, fn, z):
    x = f / fn
    return A * f ** alpha / ((1 - x ** 2) ** 2 + (2 * z * x) ** 2)


def fit_mode(f, psd, f1=FITBAND[0], f2=FITBAND[1], p0=(1e-3, -2.0, 2.4, 0.2)):
    s = (f >= f1) & (f < f2) & np.isfinite(psd) & (psd > 0)
    ff, pp = f[s], psd[s]
    lw = np.log(pp)

    def resid(p):
        A, alpha, fn, z = p
        if not (0.8 < fn < 6.0 and 0.01 < z < 2.0 and A > 0):
            return np.full(len(ff), 1e3)
        return np.log(model(ff, A, alpha, fn, z)) - lw
    best = None
    for fn0 in (1.2, 1.8, 2.4, 3.0, 3.6, 4.5):
        for z0 in (0.05, 0.15, 0.3, 0.6):
            try:
                r = optimize.least_squares(resid, (p0[0], p0[1], fn0, z0), method="lm", max_nfev=4000)
            except Exception:
                continue
            if best is None or r.cost < best.cost:
                best = r
    if best is None:
        return dict(fn=np.nan, zeta=np.nan, alpha=np.nan, rms=np.nan, Q=np.nan)
    A, alpha, fn, z = best.x
    return dict(fn=float(fn), zeta=float(abs(z)), alpha=float(alpha),
                rms=float(np.sqrt(np.mean(resid(best.x) ** 2))), Q=float(1 / (2 * abs(z))))


def _self_test():
    rng = np.random.default_rng(1)
    n = 400000
    fs = 100.0
    out = []
    for fn, z in ((2.4, 0.10), (2.0, 0.25), (3.2, 0.06)):
        wn = 2 * np.pi * fn
        b, a = signal.bilinear([wn ** 2], [1, 2 * z * wn, wn ** 2], fs)
        drive = signal.sosfiltfilt(signal.butter(1, 8.0, "low", fs=fs, output="sos"), rng.standard_normal(n))
        y = signal.lfilter(b, a, drive)
        f, p = signal.welch(y, fs, nperseg=1024)
        r = fit_mode(f, p)
        out.append((fn, z, r["fn"], r["zeta"]))
        assert abs(r["fn"] - fn) < 0.12 * fn, f"fn {r['fn']:.2f} vs {fn}"
        assert abs(r["zeta"] - z) < max(0.35 * z, 0.02), f"zeta {r['zeta']:.3f} vs {z}"
    return "fit self-test OK: " + "; ".join(f"fn {a:.1f}->{c:.2f}, z {b:.2f}->{d:.3f}" for a, b, c, d in out)


ST = _self_test()
D = np.load(f"spec_{TAG}.npz", allow_pickle=True)
f = D["f"]
fam, route, sec, vv = D["fam"], D["route"], D["sec"], D["v"]
MEM = {k[2:]: np.asarray(D[k]) for k in D.files if k.startswith("S_")}


def pooled(idx):
    w = sec[idx]
    return {k: np.tensordot(w, v[idx], axes=(0, 0)) / w.sum() for k, v in MEM.items()}


def parts(idx):
    S = pooled(idx)
    gp = lambda a, b: (S[f"{a}_{b}"] if f"{a}_{b}" in S else np.conj(S[f"{b}_{a}"]))
    Pss = np.real(gp("sa", "sa"))
    Prr = np.maximum(np.real(gp("r", "r")), 1e-30)
    coh = np.abs(gp("r", "sa")) ** 2 / np.maximum(Prr * Pss, 1e-30)
    Psr = np.real(gp("sr", "sr"))
    cohr = np.abs(gp("r", "sr")) ** 2 / np.maximum(Prr * Psr, 1e-30)
    return dict(inc_sa=Pss * (1 - coh), coh_sa=Pss * coh, inc_sr=Psr * (1 - cohr), sr=Psr, sa=Pss)


rows = {}
for rt in sorted(set(route)):
    idx = np.where(route == rt)[0]
    p = parts(idx)
    r = fit_mode(f, p["inc_sa"])
    r2 = fit_mode(f, p["inc_sr"])
    rows[rt] = dict(fam=U.FAMILY[rt], sec=float(sec[idx].sum()), v=float(np.median(vv[idx])),
                    fn=r["fn"], zeta=r["zeta"], alpha=r["alpha"], rms=r["rms"],
                    fn_sr=r2["fn"], zeta_sr=r2["zeta"], rms_sr=r2["rms"])

FAMS = ("V282", "V282old", "TORQ")
famfit = {}
for FM in FAMS:
    idx = np.where(fam == FM)[0]
    p = parts(idx)
    famfit[FM] = dict(sa=fit_mode(f, p["inc_sa"]), sr=fit_mode(f, p["inc_sr"]), P=p)

L = [f"TEST 2 -- THE WHEEL MODE (operational modal analysis on the reference-INCOHERENT wheel motion)",
     f"tag {TAG}, engaged hands-off, >=15 m/s.   {ST}", ""]
L.append("FAMILY FITS over 0.8-6.0 Hz:")
L.append(f"{'family':<10}{'fn Hz':>8}{'zeta':>8}{'Q':>7}{'alpha':>8}{'logrms':>8}   |   "
         f"{'fn(rate)':>9}{'zeta':>8}{'logrms':>8}")
for FM in FAMS:
    a, b = famfit[FM]["sa"], famfit[FM]["sr"]
    L.append(f"{FM:<10}{a['fn']:>8.2f}{a['zeta']:>8.3f}{a['Q']:>7.1f}{a['alpha']:>8.2f}{a['rms']:>8.3f}   |   "
             f"{b['fn']:>9.2f}{b['zeta']:>8.3f}{b['rms']:>8.3f}")
L.append("")
L.append("PER ROUTE:")
L.append(f"{'route':<9}{'fam':<8}{'s':>5}{'v':>5}{'fn Hz':>8}{'zeta':>8}{'Q':>7}{'logrms':>8}"
         f"{'fn(rate)':>10}{'zeta':>8}")
for rt, d in rows.items():
    L.append(f"{U.SHORT[rt]:<9}{d['fam']:<8}{d['sec']:>5.0f}{d['v']:>5.1f}{d['fn']:>8.2f}{d['zeta']:>8.3f}"
             f"{0.5/max(d['zeta'],1e-6):>7.1f}{d['rms']:>8.3f}{d['fn_sr']:>10.2f}{d['zeta_sr']:>8.3f}")
L.append("")
L.append("SPECTRUM OF THE REFERENCE-INCOHERENT WHEEL ANGLE, 1/6-octave RMS (deg), and the COHERENT")
L.append("part beside it.  If the 0.6-1.2 Hz excess were the skirt of a single mode, the excess ratio")
L.append("would peak AT the mode and fall away from it.")
edges = 2.0 ** (np.arange(np.log2(0.35), np.log2(10.0) + 1e-9, 1 / 6.0))
hdr = f"{'band Hz':<14}" + "".join(f"{FM[:7]:>10}" for FM in FAMS) + f"{'T/V ratio':>11}{'cohV':>9}{'cohT':>9}"
L.append(hdr)
df = f[1] - f[0]
spec_rows = []
for a, b in zip(edges[:-1], edges[1:]):
    s = (f >= a) & (f < b)
    if s.sum() < 1:
        continue
    vals = {FM: float(np.sqrt(np.sum(famfit[FM]["P"]["inc_sa"][s]) * df)) for FM in FAMS}
    cv = float(np.sqrt(np.sum(famfit["V282"]["P"]["coh_sa"][s]) * df))
    ct = float(np.sqrt(np.sum(famfit["TORQ"]["P"]["coh_sa"][s]) * df))
    ratio = vals["TORQ"] / max(vals["V282"], 1e-12)
    spec_rows.append(dict(f1=a, f2=b, **vals, ratio=ratio, cohV=cv, cohT=ct))
    L.append(f"{a:5.2f}-{b:5.2f}   " + "".join(f"{vals[FM]:>10.4f}" for FM in FAMS) +
             f"{ratio:>11.2f}{cv:>9.4f}{ct:>9.4f}")
json.dump(dict(selftest=ST, rows=rows,
               fam={FM: {k: famfit[FM][k] for k in ("sa", "sr")} for FM in FAMS},
               spectrum=spec_rows), open(f"u4_{TAG}.json", "w"), indent=1, default=float)
txt = "\n".join(L)
open(f"U4-{TAG.upper()}-OUT.txt", "w").write(txt)
print(txt)
