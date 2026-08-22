#!/usr/bin/env python3
r"""THE PASSIVE COLUMN IDENTIFICATION -- J_w, b_w, and a UNIT-FREE prediction of the wheel mode.

--------------------------------------------------------------------------------------------------
THE PHYSICS, STATED BEFORE THE CODE (so the fit can fail against it)

Upper column: steering-wheel + shaft inertia `J_w`, viscous `b_w`, torsion bar `k` to the pinion
`theta_p`.  Motor assists on a SECOND pinion at the rack (`reference-accord-dualpinion-arch-one-
torsion-sensor`), so the motor is NOT inside this equation.

    HANDS OFF, driver torque = 0:      J_w s^2 theta_w + b_w s theta_w + T_bar = 0
    torsion bar constitutive:          T_bar = k (theta_w - theta_p)

  =>  (A)  T_bar / theta_w  =  -(J_w s^2 + b_w s)          <-- NO RESONANCE.  A pure polynomial.
      (B)  theta_w/theta_p  =  k / (J_w s^2 + b_w s + k)    <-- the 2-pole, at w_n = sqrt(k/J_w)

🛑 THE POINT.  (A) holds at EVERY frequency hands-off, because it is Newton's law on the upper
column, not a loop relation -- the control law changes what `theta_w` and `T_bar` ARE, but cannot
change their RATIO.  So (A) is a LOOP-INDEPENDENT identification, and it is exactly the
over-determination `memory/accord-the-8hz-mode-is-the-loop-not-the-plant.md` asks for in its
"largest remaining weakness".  What limits it is NOT the crossover; it is
  * unmodelled column COULOMB friction (an extra torque on the upper column), and
  * SNR, because |J_w s^2 + b_w s| -> 0 as w -> 0.
Both bite at LOW frequency.  The valid band is MEASURED here, not assumed.

⭐ AND THE PAYOFF IS UNIT-FREE.  `T_bar` is in counts and `theta_w` in degrees, so (A) gives
`J_w` in **counts.s^2/deg**.  The kit already has `k` in the SAME units -- the identified passive
plant of `accord-the-8hz-mode-is-the-loop-not-the-plant` is a near-lossless spring of
**~2296 counts/deg**.  Therefore

        f_n = (1/2pi) sqrt(k / J_w)          with BOTH sides in counts and degrees

needs NO counts->N.m scale, NO steering ratio and NO inertia handbook value.  If it lands on
8.16 Hz the wheel-on-torsion-bar mode IS the kit's measured line.  If it lands elsewhere, the
8.16 Hz peak is the LOOP and the premise "H(s)'s dominant factor is a ~8 Hz wheel resonance" fails.

--------------------------------------------------------------------------------------------------
ESTIMATOR AND ITS CONTROLS
  * H1 = S_{theta,T}/S_{theta,theta} is biased LOW by noise on `theta` (errors-in-variables);
    H2 = S_{T,T}/S_{T,theta} is biased HIGH.  |H1| <= |H| <= |H2| and H2/H1 = 1/coh^2.
    BOTH are reported.  `plant_recon.py` measured the angle channel's in-band SNR at 2.2-4.8
    (amplitude) -- at SNR 3 the H1 bias is ~10 % -- so the bracket is not decoration.
  * |H| is DELAY-IMMUNE.  `0x18F` is one frame stale and `plant_recon.py` Q2 measured 20-38 ms of
    apparent engaged lag (itself confounded by real loop phase).  J_w is therefore taken from
    MAGNITUDE only.  The phase is reported separately, as a diagnostic, never as the fit.
  * CONTROL 1  the same fit on MANUAL (LKAS off) windows -- the fully passive car.  J_w must agree.
  * CONTROL 2  a SHAPE test: log|H| vs log f must have slope +2 (inertia).  A slope of +1 means the
    damper dominates; a slope that swings means the model is wrong.  Reported per band.
  * CONTROL 3  EPISODE bootstrap (`feedback-episodes-not-windows`), never a window bootstrap.
  * CONTROL 4  HANDS-ON windows carried alongside.  (A) is FALSE hands-on -- the driver adds a
    torque -- so hands-on must give a DIFFERENT answer.  If it does not, the fit is measuring
    something common to both and is not the column.
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
HOLD_OFF = 300.0        # p90|tq| below this = hands off
HOLD_ON = 1200.0        # p50|tq| above this = holding
K_BAR = 2296.0          # counts/deg -- the identified passive spring, accord-the-8hz-mode-is-the-loop
NBOOT = 2000
ROUTE_LABEL = {"97": "V9b STOCK", "9e": "V103", "96": "V102", "85": "V100 4x", "95": "V101 8x",
               "73": "V88"}


def reg(rt):
    if rt not in L.ROUTES:
        L.ROUTES[rt] = L._mk(rt, ROUTE_LABEL.get(rt, rt), gain=0, clamp=0, leverB=False,
                             idcode=0, bits="")
    return bool(L.ROUTES[rt]["segs"])


def hdr(s):
    print("\n" + "=" * 106)
    print(s)
    print("=" * 106, flush=True)


# ------------------------------------------------------------------------------------------------
# WINDOWING
# ------------------------------------------------------------------------------------------------

def episodes(route):
    """Contiguous runs of constant latActive, each split into NFFT/2-hopped windows.

    An EPISODE is the bootstrap unit.  A window is never the unit -- `feedback-episodes-not-windows`.
    """
    eps = []
    for blk in L.all_blocks(route):
        lat = np.asarray(blk["cc_lat"], float) > 0.5
        a = np.asarray(blk["ang"], float)
        tq = np.asarray(blk["tq"], float)
        v = np.asarray(blk.get("v_rear", blk["cs_v"]), float)
        d = np.diff(lat.astype(int))
        cuts = [0] + list(np.flatnonzero(d) + 1) + [len(lat)]
        for s, e in zip(cuts[:-1], cuts[1:]):
            if e - s < NFFT:
                continue
            eps.append(dict(lat=bool(lat[s]), ang=a[s:e], tq=tq[s:e], v=v[s:e],
                            seg=blk["_seg"], t0=float(blk["t"][s])))
    return eps


def spectra(ep, arm_hold):
    """Return per-window (Sxx, Sxy, Syy) for windows in this episode matching the hold class."""
    a, tq, v = ep["ang"], ep["tq"], ep["v"]
    w = np.hanning(NFFT)
    out = []
    for i in range(0, len(a) - NFFT, NFFT // 2):
        aa, tt, vv = a[i:i + NFFT], tq[i:i + NFFT], v[i:i + NFFT]
        p90, p50 = np.percentile(np.abs(tt), 90), np.percentile(np.abs(tt), 50)
        if arm_hold == "off" and not (p90 < HOLD_OFF):
            continue
        if arm_hold == "on" and not (p50 >= HOLD_ON):
            continue
        A = np.fft.rfft((aa - aa.mean()) * w)
        T = np.fft.rfft((tt - tt.mean()) * w)
        out.append((np.abs(A) ** 2, np.conj(A) * T, np.abs(T) ** 2, float(np.median(np.abs(vv)))))
    return out


def pool(wins):
    Sxx = np.sum([w[0] for w in wins], axis=0)
    Sxy = np.sum([w[1] for w in wins], axis=0)
    Syy = np.sum([w[2] for w in wins], axis=0)
    return Sxx, Sxy, Syy


def transfer(Sxx, Sxy, Syy):
    H1 = Sxy / np.maximum(Sxx, 1e-30)                       # biased LOW by noise on theta
    H2 = Syy / np.maximum(np.conj(Sxy), 1e-30)              # biased HIGH
    coh = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)
    return H1, H2, coh


F = np.fft.rfftfreq(NFFT, 1 / FS)


# ------------------------------------------------------------------------------------------------
# THE FIT
# ------------------------------------------------------------------------------------------------

def fit_Jb(f, magH, wts):
    r"""LS fit of |H(w)| = w * sqrt(J^2 w^2 + b^2) to a magnitude curve.

    Solved in the SQUARED domain, which is linear in (J^2, b^2):
        (|H|/w)^2 = J^2 w^2 + b^2      ->  ordinary weighted least squares, no iteration.
    Returns (J, b) in counts.s^2/deg and counts.s/deg.
    """
    w = 2 * np.pi * f
    y = (magH / np.maximum(w, 1e-9)) ** 2
    X = np.column_stack([w ** 2, np.ones_like(w)])
    W = np.diag(wts)
    try:
        beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ y)
    except np.linalg.LinAlgError:
        return np.nan, np.nan
    J = np.sqrt(beta[0]) if beta[0] > 0 else np.nan
    b = np.sqrt(beta[1]) if beta[1] > 0 else np.nan
    return float(J), float(b)


def fn_from(J, k=K_BAR):
    return np.sqrt(k / J) / (2 * np.pi) if (np.isfinite(J) and J > 0) else np.nan


def run_arm(route, lat, hold, f_lo, f_hi, coh_min=0.15, label=""):
    eps = [e for e in episodes(route) if e["lat"] == lat]
    per_ep = []
    for e in eps:
        wns = spectra(e, hold)
        if len(wns) >= 2:
            per_ep.append(wns)
    if len(per_ep) < 2:
        return None
    allw = [w for ep in per_ep for w in ep]
    Sxx, Sxy, Syy = pool(allw)
    H1, H2, coh = transfer(Sxx, Sxy, Syy)
    m = (F >= f_lo) & (F <= f_hi) & (coh >= coh_min)
    if m.sum() < 5:
        return dict(n_ep=len(per_ep), n_win=len(allw), nbins=int(m.sum()), fail="too few bins")
    wts = coh[m]
    J1, b1 = fit_Jb(F[m], np.abs(H1[m]), wts)
    J2, b2 = fit_Jb(F[m], np.abs(H2[m]), wts)
    # episode bootstrap
    Jb1, Jb2 = [], []
    rng = np.random.default_rng(4242)
    for _ in range(NBOOT):
        pick = rng.integers(0, len(per_ep), len(per_ep))
        ws = [w for i in pick for w in per_ep[i]]
        sx, sy, sz = pool(ws)
        h1, h2, ch = transfer(sx, sy, sz)
        mm = (F >= f_lo) & (F <= f_hi) & (ch >= coh_min)
        if mm.sum() < 5:
            continue
        a1, _ = fit_Jb(F[mm], np.abs(h1[mm]), ch[mm])
        a2, _ = fit_Jb(F[mm], np.abs(h2[mm]), ch[mm])
        if np.isfinite(a1):
            Jb1.append(a1)
        if np.isfinite(a2):
            Jb2.append(a2)
    ci = lambda v: (float(np.percentile(v, 2.5)), float(np.percentile(v, 97.5))) if len(v) > 50 \
        else (np.nan, np.nan)
    # shape control: log-log slope of |H| over the fit band
    sl1 = np.polyfit(np.log(F[m]), np.log(np.abs(H1[m])), 1, w=wts)[0]
    return dict(route=route, label=label, n_ep=len(per_ep), n_win=len(allw), nbins=int(m.sum()),
                coh_med=float(np.median(coh[m])),
                J1=J1, b1=b1, J2=J2, b2=b2,
                J1_ci=ci(Jb1), J2_ci=ci(Jb2),
                fn1=fn_from(J1), fn2=fn_from(J2),
                fn1_ci=tuple(fn_from(x) for x in ci(Jb1)[::-1]),
                fn2_ci=tuple(fn_from(x) for x in ci(Jb2)[::-1]),
                loglog_slope=float(sl1),
                H1=H1, H2=H2, coh=coh, mask=m)


def main():
    routes = [r for r in ("97", "9e", "96", "73", "85", "95") if reg(r)]
    OUT = {}

    hdr("1.  |H| = |T_bar/theta_w| -- SHAPE.  A pure inertia gives log-log slope +2 at every band.")
    print("    Route 0x97 = STOCK.  Values are the H1 estimator (lower bracket), coherence-weighted.")
    print("\n    %-14s %-9s %-6s %6s %6s %s" % ("route", "arm", "hold", "n_ep", "n_win",
          "".join("%17s" % ("%g-%g Hz" % b) for b in ((3, 6), (6, 9), (9, 14), (14, 20), (20, 24)))))
    for rt in routes:
        for lat, latl in ((True, "engaged"), (False, "manual")):
            for hold in ("off", "on"):
                eps = [e for e in episodes(rt) if e["lat"] == lat]
                per_ep = [w for w in (spectra(e, hold) for e in eps) if len(w) >= 2]
                if len(per_ep) < 2:
                    continue
                allw = [w for ep in per_ep for w in ep]
                H1, H2, coh = transfer(*pool(allw))
                cells = []
                for lo, hi in ((3, 6), (6, 9), (9, 14), (14, 20), (20, 24)):
                    m = (F >= lo) & (F <= hi)
                    if coh[m].max() < 0.10:
                        cells.append("%17s" % "coh<0.1")
                        continue
                    sl = np.polyfit(np.log(F[m]), np.log(np.abs(H1[m])), 1, w=coh[m])[0]
                    cells.append("%17s" % ("sl%+.2f coh%.2f" % (sl, np.median(coh[m]))))
                print("    %-14s %-9s %-6s %6d %6d %s"
                      % (ROUTE_LABEL.get(rt, rt), latl, hold, len(per_ep), len(allw),
                         "".join(cells)))

    hdr("2.  THE FIT.  J_w and b_w from |H| (DELAY-IMMUNE), then the UNIT-FREE f_n = sqrt(k/J)/2pi")
    print("    k = %.0f counts/deg (the identified passive spring, `accord-the-8hz-mode-is-the-loop`)"
          % K_BAR)
    print("    H1 = lower bracket (noise on theta biases it LOW -> J low -> f_n HIGH)")
    print("    H2 = upper bracket.  The truth is between them.  Episode bootstrap, %d resamples."
          % NBOOT)
    print("\n    %-14s %-9s %-5s %5s %6s %11s %11s %14s %14s" %
          ("route", "arm", "hold", "n_ep", "coh", "J (H1)", "J (H2)", "f_n H1 [CI]", "f_n H2 [CI]"))
    for rt in routes:
        for lat, latl in ((True, "engaged"), (False, "manual")):
            for hold in ("off", "on"):
                r = run_arm(rt, lat, hold, 9.0, 22.0, label="%s/%s/%s" % (rt, latl, hold))
                if not r or r.get("fail"):
                    continue
                OUT["%s|%s|%s" % (rt, latl, hold)] = {
                    k: v for k, v in r.items() if k not in ("H1", "H2", "coh", "mask")}
                print("    %-14s %-9s %-5s %5d %6.2f %11.4g %11.4g %14s %14s"
                      % (ROUTE_LABEL.get(rt, rt), latl, hold, r["n_ep"], r["coh_med"],
                         r["J1"], r["J2"],
                         "%.2f[%.2f,%.2f]" % (r["fn1"], *r["fn1_ci"]) if np.isfinite(r["fn1"]) else "--",
                         "%.2f[%.2f,%.2f]" % (r["fn2"], *r["fn2_ci"]) if np.isfinite(r["fn2"]) else "--"))

    hdr("3.  BAND SENSITIVITY -- does the answer depend on the band I chose?  (it must not)")
    print("    Route 0x97 STOCK, engaged, hands-off.  J in counts.s^2/deg, f_n in Hz (H1 bracket).")
    print("    %-14s %12s %12s %12s" % ("fit band", "J (H1)", "f_n (H1)", "loglog slope"))
    for lo, hi in ((6, 12), (9, 16), (9, 22), (12, 22), (14, 24), (16, 24)):
        r = run_arm("97", True, "off", lo, hi)
        if not r or r.get("fail"):
            print("    %-14s %12s" % ("%g-%g Hz" % (lo, hi), "--")); continue
        print("    %-14s %12.4g %12.2f %12.2f"
              % ("%g-%g Hz" % (lo, hi), r["J1"], r["fn1"], r["loglog_slope"]))

    p = HERE / "_plant_hs.json"
    p.write_text(json.dumps(OUT, indent=1, default=lambda o: float(o) if np.isscalar(o) else None))
    print("\nwrote %s" % p)


if __name__ == "__main__":
    main()
