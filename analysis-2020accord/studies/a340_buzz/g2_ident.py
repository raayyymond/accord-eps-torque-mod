# -*- coding: utf-8 -*-
"""g2_ident.py -- closed-loop tracking transfer theta/theta_sp (engaged, not pressed) on the A340 modded route and, as the
POSITIVE CONTROL, on the A160 V300 routes (same controller to 0.5 %, same x3 DampAxis lane engaged), then the plant the
angle loop sees:  1/P = C_ref/T - C_fb  (controller from the A160 V299/V300 image cells via the release script).
Rigid fit per speed band: Re(1/P) = k - J w^2 ; Im(1/P) = b w.   Bootstrap over 10.24 s chunks.
ANALYSIS ONLY.  Seconds."""
import json
import os
import sys
import time
import numpy as np

t00 = time.time()
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
OUT = os.path.join(KIT, "analysis-2020accord", "_scratch", "out", "a340_buzz")
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "release"))
import gate2_rescore_stock_terms as G   # noqa: E402  (module import only; main() not run)
HF = G.HF

N = 1024
HOP = 512
FS = 100.0
FREQ = np.fft.rfftfreq(N, 1 / FS)
WIN = np.hanning(N)
BANDS = [(2, 6), (6, 10), (10, 16), (16, 23), (23, 32)]
FB = np.array([0.15, 0.25, 0.35, 0.5, 0.7, 1.0, 1.4, 2.0, 2.8, 4.0, 5.6, 8.0])      # log bins, Hz
FC = np.sqrt(FB[:-1] * FB[1:])


def chunks(z, sp_key, tq_lim, bz_max=None):
    ok = (z["req"] > 0.5) & (z["pressed"] < 0.5) & (z["v"] > 2) & np.isfinite(z[sp_key])
    out = []
    n = len(ok)
    cs = np.concatenate([[0], np.cumsum(ok)])
    brk = np.concatenate([[0], np.cumsum(np.abs(np.diff(z["t"])) > 0.05)])        # time discontinuities (segment joins)
    for i in range(0, n - N, HOP):
        if cs[i + N] - cs[i] != N or brk[i + N - 1] != brk[i]:
            continue
        tq = z["tq"][i:i + N]
        if np.mean(np.abs(tq)) > tq_lim:
            continue
        if bz_max is not None and np.median(z["bz"][i:i + N]) > bz_max:
            continue
        x = z[sp_key][i:i + N]; y = z["ang"][i:i + N]
        t = np.arange(N)
        x = x - np.polyval(np.polyfit(t, x, 1), t); y = y - np.polyval(np.polyfit(t, y, 1), t)
        X = np.fft.rfft(x * WIN); Y = np.fft.rfft(y * WIN)
        out.append(dict(v=float(np.mean(z["v"][i:i + N])), Pxx=np.abs(X) ** 2, Pyy=np.abs(Y) ** 2, Pxy=np.conj(X) * Y,
                        sp_rms=float(np.std(x)), ang_abs=float(np.mean(np.abs(z["ang"][i:i + N]))),
                        bz=float(np.median(z["bz"][i:i + N])), tq=float(np.mean(np.abs(tq)))))
    return out


def binned(ch):
    """H1 = Pxy/Pxx and coherence per log bin, pooled over chunks and the raw bins inside each log bin."""
    Pxx = sum(c["Pxx"] for c in ch); Pyy = sum(c["Pyy"] for c in ch); Pxy = sum(c["Pxy"] for c in ch)
    H = np.full(len(FC), np.nan, complex); coh = np.full(len(FC), np.nan); nd = np.zeros(len(FC))
    for j in range(len(FC)):
        m = (FREQ >= FB[j]) & (FREQ < FB[j + 1])
        if not m.any():
            continue
        # per-raw-bin H weighted by Pxx (keeps the phase slope inside a bin from cancelling: bins are narrow in log f)
        H[j] = Pxy[m].sum() / Pxx[m].sum()
        coh[j] = np.abs(Pxy[m].sum()) ** 2 / (Pxx[m].sum() * Pyy[m].sum())
        nd[j] = len(ch) * m.sum() / 2.0
    return H, coh, nd


def ctl_resp(v, f):
    c = G.ctl_v299(v)
    Cf = G.C_fb_v299(f, c)
    Cr = HF.FADE * HF.H_out(f, c.oa, c.ob) * HF.FWD * G.zi(f) ** c.d * HF.PI_(f, c) * 160.0
    return Cf, Cr


def fit_rigid(f, y, w):
    om = 2 * np.pi * f
    A = np.c_[np.ones_like(om), -om ** 2]
    W = np.sqrt(w)
    (k, J), *_ = np.linalg.lstsq(A * W[:, None], y.real * W, rcond=None)
    b = float(np.sum(w * om * y.imag) / np.sum(w * om ** 2))
    return float(k), float(J), b


def analyse(name, z, sp_key, tq_lim, bz_max=None, nboot=200, seed=1):
    ch = chunks(z, sp_key, tq_lim, bz_max)
    rng = np.random.default_rng(seed)
    res = []
    for lo, hi in BANDS:
        cb = [c for c in ch if lo <= c["v"] < hi]
        if len(cb) < 6:
            res.append(dict(band=(lo, hi), n=len(cb)))
            continue
        vm = float(np.mean([c["v"] for c in cb]))
        H, coh, nd = binned(cb)
        Cf, Cr = ctl_resp(vm, FC)
        sel = (coh > 0.5) & (FC <= 4.0)
        y = Cr / H - Cf
        w = np.where(sel, nd * coh / np.maximum(1 - coh, 1e-3) / np.abs(y) ** 2, 0.0)      # ~ 1/var of the relative error
        fit = fit_rigid(FC[sel], y[sel], w[sel]) if sel.sum() >= 3 else (np.nan,) * 3
        boots = []
        for _ in range(nboot):
            cbb = [cb[i] for i in rng.integers(0, len(cb), len(cb))]
            Hb, cohb, ndb = binned(cbb)
            sb = (cohb > 0.5) & (FC <= 4.0)
            if sb.sum() < 3:
                continue
            yb = Cr / Hb - Cf
            wb = np.where(sb, ndb * cohb / np.maximum(1 - cohb, 1e-3) / np.abs(yb) ** 2, 0.0)
            boots.append(fit_rigid(FC[sb], yb[sb], wb[sb]))
        boots = np.array(boots) if boots else np.full((1, 3), np.nan)
        ci = np.nanpercentile(boots, [5, 95], axis=0)
        # family comparison: model T for each member at vm, distance over the coherent bins
        dist = {}
        for mname in ("nominal", "J_lo", "J_hi", "J_hi2", "b_lo", "b_hi", "ms_free"):
            P = HF.plant_at(mname, vm).frf(FC)
            dG = G.r24_gain_stock(vm) - 2.0                     # V300 flew r24 at stock: the 'only_r24' plant of the release doc
            P = P / (1 - P * G.F_r24(FC, vm, dG, -1.0, G.htb_model(FC, HTB)))
            Tm = Cr * P / (1 + Cf * P)
            dist[mname] = float(np.sqrt(np.sum(np.where(sel, coh, 0) * np.abs(np.log(H / Tm)) ** 2) / max(np.sum(np.where(sel, coh, 0)), 1e-9)))
        pn = HF.plant_at("nominal", vm)
        res.append(dict(band=(lo, hi), n=len(cb), sec=len(cb) * HOP / FS, v=vm, f=FC.tolist(), Tmag=np.abs(H).tolist(),
                        Tph=np.degrees(np.angle(H)).tolist(), coh=coh.tolist(), k=fit[0], J=fit[1], b=fit[2],
                        k_ci=ci[:, 0].tolist(), J_ci=ci[:, 1].tolist(), b_ci=ci[:, 2].tolist(), dist=dist,
                        fam_nom=dict(J=pn.J, b=pn.b, k=pn.k), invP_re=y.real.tolist(), invP_im=y.imag.tolist(),
                        sp_rms=float(np.median([c["sp_rms"] for c in cb])), bz=float(np.median([c["bz"] for c in cb])),
                        tq=float(np.median([c["tq"] for c in cb])), ang_abs=float(np.median([c["ang_abs"] for c in cb]))))
    return res


def show(name, res):
    print("\n=== %s" % name)
    for r in res:
        if "v" not in r:
            print("  band %s: n %d chunks (too few)" % (r["band"], r["n"])); continue
        print("  band %2d-%2d m/s  v %.1f  n %d chunks (%.0f s)  sp rms %.2f deg  |ang| %.1f  BZ p50 %.1f  |tq| %.0f" % (
            r["band"][0], r["band"][1], r["v"], r["n"], r["sec"], r["sp_rms"], r["ang_abs"], r["bz"], r["tq"]))
        print("     f     : " + " ".join("%6.2f" % x for x in r["f"]))
        print("     |T|   : " + " ".join("%6.2f" % x for x in r["Tmag"]))
        print("     ph deg: " + " ".join("%6.0f" % x for x in r["Tph"]))
        print("     coh   : " + " ".join("%6.2f" % x for x in r["coh"]))
        print("     Re 1/P: " + " ".join("%6.0f" % x for x in r["invP_re"]))
        print("     Im 1/P: " + " ".join("%6.0f" % x for x in r["invP_im"]))
        print("     rigid fit: k %.1f [%.1f, %.1f]  J %.3f [%.3f, %.3f]  b %.2f [%.2f, %.2f]   | family nominal k %.1f J %.2f b %.2f" % (
            r["k"], *r["k_ci"], r["J"], *r["J_ci"], r["b"], *r["b_ci"], r["fam_nom"]["k"], r["fam_nom"]["J"], r["fam_nom"]["b"]))
        print("     log-distance of T to each family member (x3 lane, stock r24): " + ", ".join("%s %.3f" % kv for kv in sorted(r["dist"].items(), key=lambda kv: kv[1])))


if __name__ == "__main__":
    fm, Hm, cohm, _, _ = G.measure_htb()
    HTB = G.fit_two_mass(fm, Hm, cohm)
    out = {}
    zA = dict(np.load(os.path.join(OUT, "g2_cache_a340_mod.npz")))
    zB = dict(np.load(os.path.join(OUT, "g2_cache_a160_v300.npz")))
    # tq units: 0x18F s16; light hands = mean |tq| < 400 (the analyst's 'firm' boundary is 800)
    out["a340_mod_all"] = analyse("a340", zA, "sp_e4", 400)
    out["a340_mod_quiet"] = analyse("a340q", zA, "sp_e4", 400, bz_max=4.0)
    out["a340_mod_cc"] = analyse("a340cc", zA, "sp_cc", 400)
    out["a160_v300"] = analyse("a160", zB, "sp_cc", 400)
    for k, v in out.items():
        show(k, v)
    json.dump(out, open(os.path.join(OUT, "g2_ident.json"), "w"), indent=1, default=float)
    print("\nwall %.1f s" % (time.time() - t00))
