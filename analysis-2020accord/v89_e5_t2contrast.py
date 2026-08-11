#!/usr/bin/env python3
r"""V89 flight -- the TWO follow-ups `v89_e4` left open, both of them controls.

C1  THE T2 COEFFICIENTS AS A BAND CONTRAST.  `v89_e4`'s T2 found log e_6-9 loading on
    |d2 cmd/dt2| at +1.403 -- but the 32-38 Hz NEGATIVE CONTROL loads at +0.899, so most of that is
    the kit's already-recorded common cause (STATE.md sec.10: the negative control responds at
    elasticity 0.664).  The only readable quantity is the DIFFERENCE, and it must be bootstrapped on
    the SAME resampled blocks for both responses or its CI is meaningless.

C2  T1 RESTRICTED TO HANDS-OFF.  The in-phase command<->column relation `v89_e4` measured could be
    the DRIVER co-steering rather than anything the column is doing on its own.  `cs_press`
    (openpilot's `steeringPressed`, |steeringTorque| > 1200 ct) splits it.  Hands-off is where the
    inertial reaction is the ONLY thing the bar can be carrying, so it is the decisive arm.
"""
import json
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / "rlog-tools"))

import _r31_common as C31        # noqa: E402
import _grind2_lib as G          # noqa: E402
import _r4f_lib as R4F           # noqa: E402
from v89_e4_inertia import ARMS, NFFT, HOP, fs_of, bp, t2_windows, ols, boot_med  # noqa: E402

R4F.install_fs()
RNG = np.random.default_rng(89_5555)
OUTJ = ROOT / "_cache_r75" / "v89_e5_t2contrast.json"
OUT = {}
BANDS = [(0.2, 3.0), (3.0, 6.0), (6.0, 9.0), (9.0, 12.0)]


def hdr(s):
    print("\n" + "=" * 116 + f"\n{s}\n" + "=" * 116, flush=True)


def sub(s):
    print(f"\n--- {s}", flush=True)


# =================================================================================================
def c1():
    hdr("C1  T2's COEFFICIENTS AS A BAND CONTRAST -- ratchet MINUS the 32-38 Hz negative control,\n"
        "    both fitted on the SAME bootstrap resample so the difference's CI is honest.")
    W = []
    for name in ARMS:
        W += t2_windows(name)
    W = [r for r in W if all(np.isfinite(r[k]) and r[k] > 0
                             for k in ("e69", "e3238", "x_mag", "x_d1", "x_d2", "v", "rate"))]
    print(f"    {len(W)} engaged windows")
    lm, l1, l2 = (np.log([r[k] for r in W]) for k in ("x_mag", "x_d1", "x_d2"))
    dum = [np.array([1.0 if r["build"] == n else 0.0 for r in W]) for n in ARMS]
    lv = np.log([max(r["v"], 0.05) for r in W])
    lr = np.log([max(r["rate"], 0.05) for r in W])
    X = np.column_stack(dum + [lv, lr, lm, l1, l2])
    k0 = len(dum) + 2
    y69 = np.log([r["e69"] for r in W])
    yc = np.log([r["e3238"] for r in W])
    blks = np.array([str(r["blk"]) for r in W])
    ub = np.unique(blks)
    idxof = {b: np.where(blks == b)[0] for b in ub}

    b69, bc = ols(y69, X)[k0:], ols(yc, X)[k0:]
    nboot = 3000
    D = np.empty((nboot, 3, 2))
    for i in range(nboot):
        pick = np.concatenate([idxof[ub[j]] for j in RNG.integers(0, len(ub), len(ub))])
        Xp = X[pick]
        D[i, :, 0] = ols(y69[pick], Xp)[k0:]
        D[i, :, 1] = ols(yc[pick], Xp)[k0:]
    names = ["log|cmd|", "log|dcmd/dt|", "log|d2cmd/dt2|"]
    print(f"\n    {'regressor':18s} {'6-9 Hz':>22s} {'32-38 Hz control':>22s} "
          f"{'DIFFERENCE [CI]':>26s}  excludes 0?")
    for j, nm in enumerate(names):
        d = D[:, j, 0] - D[:, j, 1]
        lo, hi = np.percentile(d, [2.5, 97.5])
        p = b69[j] - bc[j]
        la, ha = np.percentile(D[:, j, 0], [2.5, 97.5])
        lb, hb = np.percentile(D[:, j, 1], [2.5, 97.5])
        print(f"    {nm:18s} {b69[j]:+7.3f} [{la:+6.3f},{ha:+6.3f}] "
              f"{bc[j]:+7.3f} [{lb:+6.3f},{hb:+6.3f}] "
              f"{p:+9.3f} [{lo:+6.3f},{hi:+6.3f}]  {'YES' if lo > 0 or hi < 0 else 'no'}")
        OUT[f"c1/{nm}"] = dict(b69=float(b69[j]), b69_ci=[float(la), float(ha)],
                               bctl=float(bc[j]), bctl_ci=[float(lb), float(hb)],
                               diff=float(p), diff_ci=[float(lo), float(hi)])
    print("\n    ⊕ INTERPRETATION KEY.  An INERTIAL reaction is |d2cmd/dt2|-proportional; a")
    print("      load/friction/stick-slip mechanism is |cmd|-proportional.  Only a coefficient")
    print("      whose DIFFERENCE from the control excludes 0 says anything about the RATCHET as")
    print("      opposed to about the whole column spectrum.")


# =================================================================================================
def c2():
    hdr("C2  T1 SPLIT BY HANDS-ON / HANDS-OFF.  Hands-off is where the bar can ONLY be carrying the\n"
        "    upper column's own inertia and friction, so it is the decisive arm for the operator's\n"
        "    hypothesis; hands-on is contaminated by the driver co-steering.")
    OUT["c2"] = {}
    for name in ARMS:
        cache, pfx, segs = ARMS[name]
        rows = []
        for s in segs:
            if not (cache / f"{pfx}{s}.npz").exists():
                continue
            d = C31.load(s, cache, pfx)
            fs = fs_of(d)
            lat = np.asarray(d["cc_lat"], float) > 0.5
            cmd = np.asarray(d["e4tq"], float)
            tq = np.asarray(d["tq"], float)
            pr = np.asarray(d.get("cs_press", np.zeros_like(tq)), float)
            for a, b in C31.runs_of(lat, d["t"], NFFT):
                filt = {(lo, hi): (bp(cmd[a:b], fs, lo, hi), bp(tq[a:b], fs, lo, hi))
                        for lo, hi in BANDS}
                nwin = 0
                for i in range(0, (b - a) - NFFT + 1, HOP):
                    sl = slice(i, i + NFFT)
                    r = dict(blk=(name, s, a, nwin // 8),
                             press=float(np.mean(pr[a + i:a + i + NFFT] > 0.5)))
                    for (lo, hi), (cf, yf) in filt.items():
                        x, z = cf[sl], yf[sl]
                        sx, sz = np.std(x), np.std(z)
                        r[f"r_{lo}-{hi}"] = (float(np.mean((x - x.mean()) * (z - z.mean()))
                                                   / (sx * sz)) if sx > 0 and sz > 0 else np.nan)
                    nwin += 1
                    rows.append(r)
        OFF = [r for r in rows if r["press"] <= 0.02]
        ON = [r for r in rows if r["press"] >= 0.5]
        print(f"\n    {name}:  hands-OFF {len(OFF)} windows   hands-ON {len(ON)}   "
              f"mixed {len(rows) - len(OFF) - len(ON)}")
        print(f"    {'band':>10s} | {'r HANDS-OFF [CI]':>26s} {'r HANDS-ON [CI]':>26s}")
        for lo, hi in BANDS:
            k = f"r_{lo}-{hi}"
            a1 = boot_med(OFF, k)
            a2 = boot_med(ON, k)
            print(f"    {lo}-{hi:>6} | {a1[0]:7.3f} [{a1[1]:6.3f},{a1[2]:6.3f}] "
                  f"{a2[0]:7.3f} [{a2[1]:6.3f},{a2[2]:6.3f}]")
            OUT["c2"][f"{name}/{lo}-{hi}"] = dict(off=list(a1[:3]), on=list(a2[:3]))


if __name__ == "__main__":
    which = sys.argv[1:] or ["c1", "c2"]
    if "c1" in which:
        c1()
    if "c2" in which:
        c2()
    json.dump(OUT, open(OUTJ, "w"), indent=1, default=float)
    print(f"\n  wrote {OUTJ}")
