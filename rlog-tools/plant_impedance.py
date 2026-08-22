#!/usr/bin/env python3
r"""PASSIVE COLUMN IDENTIFICATION, IMPEDANCE FORM -- supersedes `plant_hs.py`'s angle-denominator fit.

WHY THE ANGLE DENOMINATOR FAILED, stated so this file can be audited against it
  `plant_recon.py` Q1 measured the 6-9 Hz band-RMS of `ang` at **0.0155-0.032 deg against a
  0.0071 deg quantiser floor** -- SNR 2.2-4.8, i.e. the angle channel's in-band content is BELOW
  one 0.1 deg LSB.  `plant_hs.py` §1 then showed the consequence directly: the log-log slope of
  |T/theta| is a healthy +1.5..+2.7 over 3-14 Hz and then collapses to **-2..-8 above 14 Hz**,
  which is impossible for a passive column and is the signature of the denominator becoming pure
  quantisation noise.  Every fit above 12 Hz returned a negative J^2 (nan).

THE FIX -- use the FINE COLUMN RATE, and fit the IMPEDANCE
  `rate_f` is the fine column angular rate in deg/s, packed into **0x18F bytes 2:3 -- the SAME
  FRAME as `tq`**.  Two consequences, both decisive:
    1. far better in-band SNR than the 0.1 deg angle channel;
    2. **no relative stale-frame skew**, because both signals ride the same message.  `plant_recon`
       Q2 could not cleanly measure the tq/ang delay (20-38 ms, confounded by real loop phase);
       with `rate_f` the question does not arise.

  Hands off, the upper-column equation  J_w s^2 th + b_w s th + T_bar = 0  divided by s.th gives

        Z(jw)  ==  T_bar / Omega_w  =  -(J_w s + b_w)        =>   |Z|^2 = J_w^2 w^2 + b_w^2

  A straight line in w^2, with slope J_w^2 and intercept b_w^2.  🛑 **THAT LINEARITY IS THE TEST.**
  A passive column CANNOT put a peak in |Z|.  If |Z| peaks at ~8 Hz the wheel-on-torsion-bar mode
  is there and the orchestrator's premise holds; if |Z|^2 is straight through 8 Hz, the 8.16 Hz
  line in `T_s` is NOT a passive wheel resonance.

⭐ THE UNIT-FREE PAYOFF (unchanged from `plant_hs.py`)
  `T_bar` in counts, rate in deg/s => J_w in counts.s^2/deg, in the SAME units as the kit's
  identified spring k ~ 2296 counts/deg.  So  f_n = sqrt(k/J_w)/2pi  needs no N.m scale at all.

CONTROLS RUN BEFORE ANY NUMBER IS QUOTED
  C0  `rate_f` really is d(ang)/dt          -- correlation and gain against a differentiated `ang`.
  C1  three independent denominators        -- `rate_f` (0x18F), `rate_c` (0x14A), d(`ang`)/dt.
                                               They carry DIFFERENT noise; J must agree.
  C2  MANUAL (LKAS off) vs ENGAGED          -- the passive column cannot know about the loop.
  C3  HANDS-ON                              -- the identity is FALSE hands-on, so it must differ.
  C4  EPISODE bootstrap                     -- `feedback-episodes-not-windows`.
  C5  LINEARITY RESIDUAL of |Z|^2 vs w^2    -- reported, not assumed.
  C6  a SYNTHETIC positive control          -- a known (J,b) column driven through the same
                                               pipeline, to prove the pipeline recovers it.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(ROOT / "analysis-2020accord"))

import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = L.FS
NFFT = 512
F = np.fft.rfftfreq(NFFT, 1 / FS)
HOLD_OFF = 300.0
HOLD_ON = 1200.0
K_BAR = 2296.0
NBOOT = 1500
ROUTE_LABEL = {"97": "V9b STOCK", "9e": "V103", "96": "V102", "85": "V100 4x", "95": "V101 8x",
               "73": "V88"}
DENOMS = ("rate_f", "rate_c", "dang")


def reg(rt):
    if rt not in L.ROUTES:
        L.ROUTES[rt] = L._mk(rt, ROUTE_LABEL.get(rt, rt), gain=0, clamp=0, leverB=False,
                             idcode=0, bits="")
    return bool(L.ROUTES[rt]["segs"])


def hdr(s):
    print("\n" + "=" * 108)
    print(s)
    print("=" * 108, flush=True)


def episodes(route):
    eps = []
    for blk in L.all_blocks(route):
        lat = np.asarray(blk["cc_lat"], float) > 0.5
        d = dict(tq=np.asarray(blk["tq"], float),
                 rate_f=np.asarray(blk["rate_f"], float),
                 rate_c=np.asarray(blk["rate_c"], float),
                 ang=np.asarray(blk["ang"], float),
                 v=np.asarray(blk.get("v_rear", blk["cs_v"]), float))
        # central difference of the angle, deg/s, on the uniform FS grid
        d["dang"] = np.gradient(d["ang"]) * FS
        cuts = [0] + list(np.flatnonzero(np.diff(lat.astype(int))) + 1) + [len(lat)]
        for s, e in zip(cuts[:-1], cuts[1:]):
            if e - s < NFFT:
                continue
            eps.append(dict(lat=bool(lat[s]), seg=blk["_seg"],
                            **{k: v[s:e] for k, v in d.items()}))
    return eps


def ep_spectra(ep, denom, hold):
    w = np.hanning(NFFT)
    x, y = ep[denom], ep["tq"]
    out = []
    for i in range(0, len(y) - NFFT, NFFT // 2):
        yy = y[i:i + NFFT]
        p90, p50 = np.percentile(np.abs(yy), 90), np.percentile(np.abs(yy), 50)
        if hold == "off" and not (p90 < HOLD_OFF):
            continue
        if hold == "on" and not (p50 >= HOLD_ON):
            continue
        xx = x[i:i + NFFT]
        X = np.fft.rfft((xx - xx.mean()) * w)
        Y = np.fft.rfft((yy - yy.mean()) * w)
        out.append((np.abs(X) ** 2, np.conj(X) * Y, np.abs(Y) ** 2))
    return out


def pool(ws):
    return (np.sum([w[0] for w in ws], axis=0), np.sum([w[1] for w in ws], axis=0),
            np.sum([w[2] for w in ws], axis=0))


def zmag(Sxx, Sxy, Syy, which="H2"):
    r"""|Z| estimators.  H1 is biased LOW by noise on the RATE, H2 by noise on the TORQUE.

    The torque channel is the cleaner of the two (`plant_recon` Q1: |tq|(6-9) = 20-83 counts
    against a 1-count LSB), so **H2 is the less-biased estimator here** and H1 is the lower
    bracket.  Both are carried.
    """
    if which == "H1":
        return np.abs(Sxy) / np.maximum(Sxx, 1e-30)
    return Syy / np.maximum(np.abs(Sxy), 1e-30)


def coh2(Sxx, Sxy, Syy):
    return np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)


def fit_line(f, z2, wts):
    """|Z|^2 = J^2 w^2 + b^2.  Weighted LS in (w^2, 1).  Returns J, b, R2."""
    w2 = (2 * np.pi * f) ** 2
    X = np.column_stack([w2, np.ones_like(w2)])
    W = np.diag(wts)
    try:
        beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ z2)
    except np.linalg.LinAlgError:
        return np.nan, np.nan, np.nan
    pred = X @ beta
    ss = 1 - np.sum(wts * (z2 - pred) ** 2) / max(np.sum(wts * (z2 - np.average(z2, weights=wts)) ** 2), 1e-30)
    J = np.sqrt(beta[0]) if beta[0] > 0 else np.nan
    b = np.sqrt(beta[1]) if beta[1] > 0 else np.nan
    return float(J), float(b), float(ss)


def fn_of(J, k=K_BAR):
    return float(np.sqrt(k / J) / (2 * np.pi)) if (np.isfinite(J) and J > 0) else np.nan


# ------------------------------------------------------------------------------------------------


def c0_rate_identity(routes):
    hdr("C0  IS `rate_f` REALLY d(ang)/dt?  (if not, the whole identification is of the wrong body)")
    print("    %-12s %10s %12s %12s %10s" % ("route", "corr", "gain f/dang", "corr rate_c", "n"))
    for rt in routes:
        rf, dg, rc = [], [], []
        for blk in L.all_blocks(rt):
            a = np.asarray(blk["ang"], float)
            rf.append(np.asarray(blk["rate_f"], float))
            rc.append(np.asarray(blk["rate_c"], float))
            dg.append(np.gradient(a) * FS)
        rf, dg, rc = np.concatenate(rf), np.concatenate(dg), np.concatenate(rc)
        m = np.abs(dg) > 1.0
        if m.sum() < 500:
            continue
        g = float(np.polyfit(dg[m], rf[m], 1)[0])
        print("    %-12s %10.4f %12.4f %12.4f %10d"
              % (ROUTE_LABEL.get(rt, rt), np.corrcoef(rf[m], dg[m])[0, 1], g,
                 np.corrcoef(rc[m], dg[m])[0, 1], int(m.sum())))


def c6_synthetic():
    hdr("C6  POSITIVE CONTROL -- push a KNOWN column through the identical pipeline")
    from scipy.signal import lfilter
    print("    Synthetic: theta_p (pinion) = filtered noise drives  theta_w/theta_p = k/(Js^2+bs+k),")
    print("    then T = k(theta_w - theta_p).  Quantise ang to 0.1 deg and tq to 1 count, exactly")
    print("    like the bus.  Recover J from |T/Omega| and compare with truth.")
    print("\n    %10s %10s %12s %12s %12s %12s %10s"
          % ("J true", "b true", "f_n true", "J rec(H2)", "f_n rec", "J rec(H1)", "R2"))
    rows = {}
    for Jt, bt in ((0.6, 6.0), (0.9, 9.0), (1.5, 12.0)):
        rng = np.random.default_rng(11)
        n = int(400 * FS)
        drive = lfilter(*__import__("scipy.signal", fromlist=["butter"]).butter(
            2, 12.0, fs=FS), rng.normal(0, 1, n)) * 3.0
        # discretise k/(J s^2 + b s + k) by bilinear
        from scipy.signal import cont2discrete
        num, den = [K_BAR], [Jt, bt, K_BAR]
        (bd, ad, _) = cont2discrete((num, den), 1 / FS, method="bilinear")
        th_w = lfilter(bd.ravel(), ad.ravel(), drive)
        T = K_BAR * (th_w - drive)
        th_q = np.round(th_w / 0.1) * 0.1
        T_q = np.round(T)
        om = np.gradient(th_q) * FS
        ws = []
        w = np.hanning(NFFT)
        for i in range(0, n - NFFT, NFFT // 2):
            X = np.fft.rfft((om[i:i + NFFT] - om[i:i + NFFT].mean()) * w)
            Y = np.fft.rfft((T_q[i:i + NFFT] - T_q[i:i + NFFT].mean()) * w)
            ws.append((np.abs(X) ** 2, np.conj(X) * Y, np.abs(Y) ** 2))
        Sxx, Sxy, Syy = pool(ws)
        ch = coh2(Sxx, Sxy, Syy)
        m = (F >= 4) & (F <= 20) & (ch > 0.2)
        J2, b2, r2 = fit_line(F[m], zmag(Sxx, Sxy, Syy, "H2")[m] ** 2, ch[m])
        J1, b1, _ = fit_line(F[m], zmag(Sxx, Sxy, Syy, "H1")[m] ** 2, ch[m])
        print("    %10.3f %10.2f %12.2f %12.3f %12.2f %12.3f %10.3f"
              % (Jt, bt, fn_of(Jt), J2, fn_of(J2), J1, r2))
        rows["%.1f" % Jt] = dict(J_true=Jt, J_h2=J2, J_h1=J1, fn_true=fn_of(Jt), fn_h2=fn_of(J2))
    print("\n    ⇒ read the bias off this table before believing any J below.")
    return rows


def shape_table(routes):
    hdr("1.  |Z| SHAPE -- a passive column gives |Z|^2 STRICTLY LINEAR in w^2 (slope J^2, "
        "intercept b^2)")
    print("    Reported: the log-log slope of |Z| per band (H2 estimator).  A pure inertia -> +1,")
    print("    a pure damper -> 0.  🛑 A PEAK (slope going strongly positive then negative) would")
    print("    be a passive resonance -- that is the orchestrator's premise, and this is its test.")
    print("\n    %-12s %-8s %-5s %5s %5s %s" % ("route", "arm", "hold", "nep", "nwin",
          "".join("%16s" % ("%g-%g" % b) for b in ((3, 6), (6, 9), (9, 12), (12, 16), (16, 22)))))
    for rt in routes:
        for lat, latl in ((True, "eng"), (False, "man")):
            for hold in ("off", "on"):
                eps = [e for e in episodes(rt) if e["lat"] == lat]
                per = [w for w in (ep_spectra(e, "rate_f", hold) for e in eps) if len(w) >= 2]
                if len(per) < 2:
                    continue
                allw = [w for p in per for w in p]
                Sxx, Sxy, Syy = pool(allw)
                ch, Z = coh2(Sxx, Sxy, Syy), zmag(Sxx, Sxy, Syy, "H2")
                cells = []
                for lo, hi in ((3, 6), (6, 9), (9, 12), (12, 16), (16, 22)):
                    m = (F >= lo) & (F <= hi)
                    if np.median(ch[m]) < 0.05:
                        cells.append("%16s" % "coh<.05"); continue
                    sl = np.polyfit(np.log(F[m]), np.log(Z[m]), 1, w=ch[m])[0]
                    cells.append("%16s" % ("%+.2f c%.2f" % (sl, np.median(ch[m]))))
                print("    %-12s %-8s %-5s %5d %5d %s"
                      % (ROUTE_LABEL.get(rt, rt), latl, hold, len(per), len(allw), "".join(cells)))


def fit_table(routes, f_lo=4.0, f_hi=20.0, coh_min=0.10):
    hdr("2.  THE FIT.  |Z|^2 = J^2 w^2 + b^2 over %.0f-%.0f Hz, coherence-weighted, "
        "episode bootstrap n=%d" % (f_lo, f_hi, NBOOT))
    print("    J in counts.s^2/deg · b in counts.s/deg · f_n = sqrt(%.0f/J)/2pi Hz (UNIT-FREE)"
          % K_BAR)
    print("\n    %-12s %-8s %-5s %-7s %4s %5s %7s %8s %8s %18s %6s"
          % ("route", "arm", "hold", "denom", "nep", "coh", "J", "b", "R2", "f_n [95% CI]", "n_bin"))
    OUT = {}
    for rt in routes:
        for lat, latl in ((True, "eng"), (False, "man")):
            for hold in ("off", "on"):
                for den in DENOMS:
                    eps = [e for e in episodes(rt) if e["lat"] == lat]
                    per = [w for w in (ep_spectra(e, den, hold) for e in eps) if len(w) >= 2]
                    if len(per) < 3:
                        continue
                    allw = [w for p in per for w in p]
                    Sxx, Sxy, Syy = pool(allw)
                    ch = coh2(Sxx, Sxy, Syy)
                    m = (F >= f_lo) & (F <= f_hi) & (ch >= coh_min)
                    if m.sum() < 8:
                        continue
                    J, b, r2 = fit_line(F[m], zmag(Sxx, Sxy, Syy, "H2")[m] ** 2, ch[m])
                    boot = []
                    rng = np.random.default_rng(7)
                    for _ in range(NBOOT):
                        pk = rng.integers(0, len(per), len(per))
                        sx, sy, sz = pool([w for i in pk for w in per[i]])
                        c2 = coh2(sx, sy, sz)
                        mm = (F >= f_lo) & (F <= f_hi) & (c2 >= coh_min)
                        if mm.sum() < 8:
                            continue
                        jj, _, _ = fit_line(F[mm], zmag(sx, sy, sz, "H2")[mm] ** 2, c2[mm])
                        if np.isfinite(jj):
                            boot.append(fn_of(jj))
                    ci = ("[%.2f,%.2f]" % (np.percentile(boot, 2.5), np.percentile(boot, 97.5))
                          if len(boot) > 100 else "[--]")
                    print("    %-12s %-8s %-5s %-7s %4d %5.2f %7.3f %8.1f %8.3f %8.2f %-9s %6d"
                          % (ROUTE_LABEL.get(rt, rt), latl, hold, den, len(per),
                             float(np.median(ch[m])), J, b, r2, fn_of(J), ci, int(m.sum())))
                    OUT["%s|%s|%s|%s" % (rt, latl, hold, den)] = dict(
                        J=J, b=b, r2=r2, fn=fn_of(J), ci=ci, nep=len(per),
                        coh=float(np.median(ch[m])), nbin=int(m.sum()))
    return OUT


def main():
    routes = [r for r in ("97", "9e", "96", "73", "85", "95") if reg(r)]
    print("routes: " + ", ".join("0x%s=%s" % (r, ROUTE_LABEL.get(r, r)) for r in routes))
    c0_rate_identity(routes)
    syn = c6_synthetic()
    shape_table(routes)
    o = fit_table(routes)
    (HERE / "_plant_impedance.json").write_text(
        json.dumps(dict(synthetic=syn, fits=o), indent=1, default=float))
    print("\nwrote %s" % (HERE / "_plant_impedance.json"))


if __name__ == "__main__":
    main()
