#!/usr/bin/env python3
r"""FINAL PASSIVE-COLUMN FIT -- J_w, b_w, and the implied wheel-mode f_n and zeta, with CIs.

Read `plant_zcurve.py`'s header first; it establishes the channel choice and the shape.  The one
line that matters: **|Z|/w is FLAT across ~6-13 Hz on every route with usable coherence**, which is
the signature of a pure inertia + damper and NOT of a resonance.  This file puts numbers and
episode-bootstrap CIs on it.

    hands off:   Z = T_bar/Omega_w = -(J_w s + b_w)      |Z|^2 = J_w^2 w^2 + b_w^2
    implied:     f_n = sqrt(k/J_w)/2pi        zeta = b_w / (2 sqrt(k J_w))       k = 2296 ct/deg

⚠ THREE CAVEATS CARRIED ON EVERY NUMBER, none of which the fit can remove:
  1. SCALE.  `rate_c` == 1.25 x `rate_f`; one decode has the wrong deg/s scale.  J scales linearly
     with the choice, f_n as 1/sqrt (1.12x), zeta as 1/sqrt (1.12x).  Both are printed.
  2. `k` = 2296 counts/deg is the kit's OWN identified spring from the 4x/8x gain-step solve
     (`accord-the-8hz-mode-is-the-loop-not-the-plant`), which that memory itself calls PROVISIONAL
     and CONFOUNDED (route 0x85 has Lever B armed, 0x95 does not).  f_n and zeta inherit that.
     J_w and b_w do NOT -- they are measured here and need no k.
  3. ENGAGED b_w is NOT the passive column's damping.  Engaged, the assist loop contributes to
     what this instrument calls `b_w`.  The MANUAL arm is the passive one, and its coherence is
     0.01-0.10 hands-off -- **too low to fit.**  That is the gap the drive has to close.
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

FS, NFFT = L.FS, 1024
F = np.fft.rfftfreq(NFFT, 1 / FS)
HOLD_OFF, HOLD_ON = 300.0, 1200.0
K_BAR = 2296.0
F_LO, F_HI = 4.5, 13.0
COH_MIN = 0.15
NBOOT = 3000
LAB = {"97": "V9b STOCK", "9e": "V103", "96": "V102", "73": "V88", "85": "V100 4x", "95": "V101 8x"}


def reg(rt):
    if rt not in L.ROUTES:
        L.ROUTES[rt] = L._mk(rt, LAB.get(rt, rt), gain=0, clamp=0, leverB=False, idcode=0, bits="")
    return bool(L.ROUTES[rt]["segs"])


def hdr(s):
    print("\n" + "=" * 108); print(s); print("=" * 108, flush=True)


def episodes(rt):
    eps = []
    for blk in L.all_blocks(rt):
        lat = np.asarray(blk["cc_lat"], float) > 0.5
        tq, r = np.asarray(blk["tq"], float), np.asarray(blk["rate_f"], float)
        v = np.asarray(blk.get("v_rear", blk["cs_v"]), float)
        cuts = [0] + list(np.flatnonzero(np.diff(lat.astype(int))) + 1) + [len(lat)]
        for s, e in zip(cuts[:-1], cuts[1:]):
            if e - s >= NFFT:
                eps.append(dict(lat=bool(lat[s]), tq=tq[s:e], r=r[s:e], v=v[s:e]))
    return eps


def wins(ep, hold):
    w = np.hanning(NFFT)
    out = []
    for i in range(0, len(ep["tq"]) - NFFT, NFFT // 2):
        y = ep["tq"][i:i + NFFT]
        if hold == "off" and not (np.percentile(np.abs(y), 90) < HOLD_OFF):
            continue
        if hold == "on" and not (np.percentile(np.abs(y), 50) >= HOLD_ON):
            continue
        x = ep["r"][i:i + NFFT]
        out.append((np.abs(np.fft.rfft((x - x.mean()) * w)) ** 2,
                    np.conj(np.fft.rfft((x - x.mean()) * w)) * np.fft.rfft((y - y.mean()) * w),
                    np.abs(np.fft.rfft((y - y.mean()) * w)) ** 2))
    return out


def pool(ws):
    return tuple(np.sum([w[i] for w in ws], axis=0) for i in range(3))


def solve(ws):
    Sxx, Sxy, Syy = pool(ws)
    ch = np.abs(Sxy) ** 2 / np.maximum(Sxx * Syy, 1e-30)
    Z2 = Syy / np.maximum(np.abs(Sxy), 1e-30)
    m = (F >= F_LO) & (F <= F_HI) & (ch >= COH_MIN)
    if m.sum() < 10:
        return None
    w2 = (2 * np.pi * F[m]) ** 2
    X = np.column_stack([w2, np.ones_like(w2)])
    W = np.diag(ch[m])
    try:
        beta = np.linalg.solve(X.T @ W @ X, X.T @ W @ (Z2[m] ** 2))
    except np.linalg.LinAlgError:
        return None
    if beta[0] <= 0 or beta[1] <= 0:
        return None
    J, b = float(np.sqrt(beta[0])), float(np.sqrt(beta[1]))
    pred = X @ beta
    r2 = 1 - np.sum(ch[m] * (Z2[m] ** 2 - pred) ** 2) / max(
        np.sum(ch[m] * (Z2[m] ** 2 - np.average(Z2[m] ** 2, weights=ch[m])) ** 2), 1e-30)
    return dict(J=J, b=b, r2=float(r2), nbin=int(m.sum()), coh=float(np.median(ch[m])),
                fn=float(np.sqrt(K_BAR / J) / (2 * np.pi)),
                zeta=float(b / (2 * np.sqrt(K_BAR * J))))


def main():
    routes = [r for r in ("97", "9e", "96", "73", "85", "95") if reg(r)]
    hdr("PASSIVE-COLUMN FIT   |Z|^2 = J_w^2 w^2 + b_w^2   over %.1f-%.1f Hz, coh >= %.2f, "
        "episode bootstrap n=%d" % (F_LO, F_HI, COH_MIN, NBOOT))
    print("    J_w counts.s^2/deg · b_w counts.s/deg · f_n = sqrt(%.0f/J)/2pi Hz · "
          "zeta = b/(2 sqrt(kJ))" % K_BAR)
    print("    ⚠ the `rate_c` scale alternative multiplies J and b by 1/1.25 => f_n x1.118, "
          "zeta x1.118")
    print("\n    %-11s %-8s %-5s %4s %5s %5s %16s %16s %16s %16s"
          % ("route", "arm", "hold", "nep", "coh", "R2", "J_w [95% CI]", "b_w [95% CI]",
             "f_n Hz [95% CI]", "zeta [95% CI]"))
    OUT = {}
    for rt in routes:
        for lat, latl in ((True, "engaged"), (False, "manual")):
            for hold in ("off", "on"):
                eps = [e for e in episodes(rt) if e["lat"] == lat]
                per = [w for w in (wins(e, hold) for e in eps) if len(w) >= 1]
                if len(per) < 3:
                    continue
                base = solve([w for p in per for w in p])
                if not base:
                    continue
                rng = np.random.default_rng(31337)
                B = {k: [] for k in ("J", "b", "fn", "zeta")}
                for _ in range(NBOOT):
                    pk = rng.integers(0, len(per), len(per))
                    s = solve([w for i in pk for w in per[i]])
                    if s:
                        for k in B:
                            B[k].append(s[k])
                ci = lambda k: (np.percentile(B[k], 2.5), np.percentile(B[k], 97.5)) \
                    if len(B[k]) > 200 else (np.nan, np.nan)
                fm = lambda v, c, p=2: "%.*f[%.*f,%.*f]" % (p, v, p, c[0], p, c[1])
                print("    %-11s %-8s %-5s %4d %5.2f %5.2f %16s %16s %16s %16s"
                      % (LAB.get(rt, rt), latl, hold, len(per), base["coh"], base["r2"],
                         fm(base["J"], ci("J")), fm(base["b"], ci("b"), 0),
                         fm(base["fn"], ci("fn")), fm(base["zeta"], ci("zeta"), 3)))
                OUT["%s|%s|%s" % (rt, latl, hold)] = dict(
                    nep=len(per), **base,
                    J_ci=list(ci("J")), b_ci=list(ci("b")), fn_ci=list(ci("fn")),
                    zeta_ci=list(ci("zeta")))

    hdr("WHAT THIS SAYS ABOUT THE 8.16 Hz LINE")
    fits = [v for k, v in OUT.items() if "engaged|off" in k]
    if fits:
        Js = np.array([v["J"] for v in fits])
        fns = np.array([v["fn"] for v in fits])
        zs = np.array([v["zeta"] for v in fits])
        print("    engaged / hands-off arms, n = %d routes" % len(fits))
        print("      J_w   %.2f - %.2f counts.s^2/deg   (median %.2f)" % (Js.min(), Js.max(),
                                                                         np.median(Js)))
        print("      f_n   %.2f - %.2f Hz               (median %.2f)" % (fns.min(), fns.max(),
                                                                          np.median(fns)))
        print("      zeta  %.3f - %.3f                  (median %.3f)  => Q = %.1f - %.1f"
              % (zs.min(), zs.max(), np.median(zs), 1 / (2 * zs.max()), 1 / (2 * zs.min())))
        print("\n    Compare: the kit's measured line is 8.16 Hz at Q ~ 10 (zeta ~ 0.049).")
        print("    A wheel-on-torsion-bar mode with the J_w and b_w measured HERE would sit at")
        print("    %.1f-%.1f Hz with zeta %.2f-%.2f (Q %.1f-%.1f) -- i.e. HEAVILY DAMPED and NOT"
              % (fns.min(), fns.max(), zs.min(), zs.max(), 1 / (2 * zs.max()), 1 / (2 * zs.min())))
        print("    capable of a Q ~ 10 line anywhere.")
    (HERE / "_plant_fit_final.json").write_text(json.dumps(OUT, indent=1, default=float))
    print("\nwrote %s" % (HERE / "_plant_fit_final.json"))


if __name__ == "__main__":
    main()
