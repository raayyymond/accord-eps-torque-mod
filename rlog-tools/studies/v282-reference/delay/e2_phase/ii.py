"""Friction-bias correction by indirect inference, and the blind positive control that validates it.

The linear H(jw) fit is exact for F = 0 (control: +0.5 +/- 1 ms) but Coulomb friction adds describing-function phase
lag the linear model books as delay (+5..+9 ms at >= 8 m/s). Correction, applied IDENTICALLY to synthetic and real data:
  1. linear fit on the data -> D0, J0, b0 (rate fit, band 1.5-8 Hz, coherence > 0.5)
  2. simulate the nonlinear plant (J0, b0, k(v), F) driven by the SAME logged command at D = D0, run the same fit -> D1
  3. D_corr = D0 - (D1 - D0)          (one fixed-point step; bias is ~independent of D, see control)
F is not identified by this fit: F = 0.02 (brief) with sensitivity rows at F = 0.01 and 0.03.

usage: python ii.py control <route>      -- blind recovery of true D 30 / 60 ms (the mandatory control)
       python ii.py real <route> [...]   -- apply to real data (uses out/spectra_<route>.npz fits recomputed here)
"""
import sys, json
from pathlib import Path
import numpy as np
import common as C, estimate as E, synth as Y

OUT = Path(__file__).resolve().parent / "out"; OUT.mkdir(exist_ok=True)
BINS = [(0.0, 8.0), (8.0, 15.0), (15.0, 99.0), (8.0, 99.0), (0.0, 99.0)]


def lin_fit(S, mask, zkey, est, lo, hi):
    f, rows = E.chunk_stack(S, mask, zkey=zkey)
    rr = [r for r in rows if lo <= r["v"] < hi]
    x = E.fit_bin(f, rr, est=est, out="rate", nboot=0)
    return (x["fit"] if x and x.get("fit") else None), len(rr)


def corrected(R, mask, S_obs, zkey, est, lo, hi, F, bin_mask=None):
    ft, n = lin_fit(S_obs, mask, zkey, est, lo, hi)
    if ft is None:
        return dict(n=n, fit=None)
    Ssim = Y.simulate(R, mask, max(ft["D"], 0.0), J=ft["J"], b=ft["b"], F=F)
    f1, _ = lin_fit(Ssim, mask, "zexo", "direct", lo, hi)
    del Ssim
    if f1 is None:
        return dict(n=n, D0=ft["D"], J0=ft["J"], b0=ft["b"], D1=None, Dcorr=None)
    return dict(n=n, D0=ft["D"], J0=ft["J"], b0=ft["b"], k0=ft["k"], D1=f1["D"], bias=f1["D"] - max(ft["D"], 0.0),
                Dcorr=ft["D"] - (f1["D"] - max(ft["D"], 0.0)))


if __name__ == "__main__":
    mode, routes = sys.argv[1], sys.argv[2:]
    res = {}
    for route in routes:
        R = C.load_route(route); mask = C.handsoff_mask(R)
        if mode == "control":
            for pname, kw in [("J8e-5_b.003_F.02", dict(J=8e-5, b=0.003, F=0.02)),
                              ("J8e-5_b.005_F.02", dict(J=8e-5, b=0.005, F=0.02)),
                              ("J1.5e-4_b.003_F.02", dict(J=1.5e-4, b=0.003, F=0.02))]:
                for Dt in (0.03, 0.06):
                    S = Y.simulate(R, mask, Dt, **kw)
                    for lo, hi in BINS:
                        c = corrected(R, mask, S, "zexo", "direct", lo, hi, F=kw["F"])
                        key = f"{route}|{pname}|D{int(Dt*1e3)}|v{lo:.0f}-{hi:.0f}"
                        res[key] = c
                        print(key, "n", c["n"], "D0", None if c.get("D0") is None else round(c["D0"] * 1e3, 1),
                              "Dcorr", None if c.get("Dcorr") is None else round(c["Dcorr"] * 1e3, 1),
                              "err", None if c.get("Dcorr") is None else round((c["Dcorr"] - Dt) * 1e3, 1), flush=True)
                    del S
        else:
            for est in ("direct", "iv"):
                for lo, hi in BINS:
                    for F in (0.01, 0.02, 0.03):
                        c = corrected(R, mask, R, "sp", est, lo, hi, F=F)
                        key = f"{route}|{est}|v{lo:.0f}-{hi:.0f}|F{F}"
                        res[key] = c
                        print(key, {k: (round(v * 1e3, 1) if isinstance(v, float) and k[0] in "Db" and k != "b0" else v) for k, v in c.items()}, flush=True)
        del R
        (OUT / f"ii_{mode}_{route}.json").write_text(json.dumps(res, indent=1, default=float))
