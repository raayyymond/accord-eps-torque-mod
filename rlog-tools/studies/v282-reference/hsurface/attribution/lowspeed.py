"""The 0-8 m/s cell at 0.10-0.50 Hz -- mechanism (c)'s own regime, which no per-route pass can reach
(the 20.48 s instrument yields 0-4 blocks per torque route below 8 m/s; pooled it is 10 blocks = 205 s).
Pooling across routes is the ONLY way to measure it at all, so the block bootstrap here is over ROUTES
first and blocks second, and the per-route |H| values are printed next to the pooled one so a pooled
number carried by one route is visible as such.

Same three cuts as decomp.py: model -> setpoint (fork), setpoint -> achieved (EPS+plant), model -> achieved.
MEASUREMENT.
"""
import sys, json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parents[1])); sys.path.insert(0, str(HERE))
import v282cmp as V
from surf import _spec, OUT

rng = np.random.default_rng(23)
GRP = {"V282": ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"],
       "TON": ["0000006c--68c6e94b17", "0000006d--05e83bb04f", "0000006e--6ca3e014fd", "00000076--d0b7ea7e4d"],
       "TOFF": ["00000075--6c8687d5bd"],
       "V282old": ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4"]}
CUTS = [("model", "setpoint", "H_fork"), ("setpoint", "la_pose", "H_dwn"), ("model", "la_pose", "H_tot")]


def blocks(rk, n, vlo, vhi):
    S = V.load(rk)
    u = V.usable(S, vlo, vhi)
    got = {c[2]: [] for c in CUTS}
    cov = []
    for a, b in V.runs(u, S["t"], min_s=n / V.FS):
        for k in range(a, b - n + 1, n):
            for xk, yk, nm in CUTS:
                f, pxx, pyy, pxy = _spec(np.nan_to_num(S[xk])[k:k + n], np.nan_to_num(S[yk])[k:k + n], n)
                got[nm].append((f, pxx, pyy, pxy))
            cov.append((float(np.median(np.abs(S["sa"][k:k + n]))),
                        float(np.median(np.abs(np.nan_to_num(S["out"][k:k + n])))),
                        float(np.median(np.abs(np.nan_to_num(S["i"][k:k + n])))),
                        float(np.median(np.abs(np.nan_to_num(S["f"][k:k + n]))))))
    del S
    return got, cov


def band(P, f1, f2):
    if not P:
        return None
    f = P[0][0]; s = (f >= f1) & (f < f2)
    Pxx = np.sum([p[1][s] for p in P], axis=0)
    Pyy = np.sum([p[2][s] for p in P], axis=0)
    Pxy = np.sum([p[3][s] for p in P], axis=0)
    H = float(np.average(np.abs(Pxy) / np.maximum(Pxx, 1e-30), weights=Pxx))
    coh = float(np.average(np.abs(Pxy) ** 2 / np.maximum(Pxx * Pyy, 1e-30), weights=Pxx))
    lag = float(np.average(-np.degrees(np.angle(Pxy)) / (360.0 * f[s]), weights=Pxx))
    return H, coh, lag


def main():
    n = 2048
    print("=" * 140)
    print("LOW SPEED 0-8 m/s, the 20.48 s instrument.  Mechanism (c)'s own regime.")
    print("  H_fork = model->setpoint   H_dwn = setpoint->achieved   H_tot = model->achieved  (lag in s)")
    print("=" * 140)
    store = {}
    for g, rks in GRP.items():
        for rk in rks:
            got, cov = blocks(rk, n, 0.0, 8.0)
            store[(g, rk)] = (got, cov)
            nb = len(got["H_tot"])
            if nb:
                print(f"  {g:8s} {rk:24s} {nb:3d} blocks = {nb*n/V.FS:5.0f} s   "
                      f"med |ang| {np.median([c[0] for c in cov]):6.1f} deg  med |cmd| {np.median([c[1] for c in cov]):.4f}"
                      f"  med |i|/LAF {np.median([c[2] for c in cov]):.4f}  med |f|/LAF {np.median([c[3] for c in cov]):.4f}")
            else:
                print(f"  {g:8s} {rk:24s}   0 blocks")
    for f1, f2 in [(0.10, 0.25), (0.25, 0.50)]:
        print(f"\n--- band {f1:.2f}-{f2:.2f} Hz, 0-8 m/s ---")
        print(f"{'group':9s} {'routes':6s} {'blk':>4s} {'sec':>5s} | " +
              " | ".join(f"{nm:>22s}" for _, _, nm in CUTS) + " | pooled check")
        for g, rks in GRP.items():
            allb = {nm: [] for _, _, nm in CUTS}
            used = []
            for rk in rks:
                got, cov = store[(g, rk)]
                if not got["H_tot"]:
                    continue
                used.append(rk)
                for nm in allb:
                    allb[nm] += got[nm]
            if not used:
                continue
            res = {nm: band(allb[nm], f1, f2) for nm in allb}
            if any(v is None for v in res.values()):
                continue
            # route-cluster bootstrap on H_tot
            bt = []
            for _ in range(400):
                sel = []
                for rk in rng.choice(used, len(used), replace=True):
                    got, _ = store[(g, rk)]
                    L = got["H_tot"]
                    sel += [L[i] for i in rng.integers(0, len(L), len(L))]
                r = band(sel, f1, f2)
                if r:
                    bt.append(r[0])
            lo, hi = (np.percentile(bt, [2.5, 97.5]) if len(bt) > 50 else (np.nan, np.nan))
            nb = len(allb["H_tot"])
            s = f"{g:9s} {len(used):6d} {nb:4d} {nb*n/V.FS:5.0f} | "
            s += " | ".join(f"H {res[nm][0]:5.2f} coh {res[nm][1]:.2f} lag{res[nm][2]:+.2f}" for _, _, nm in CUTS)
            s += f" | Hf*Hd {res['H_fork'][0]*res['H_dwn'][0]:5.2f}  CI(H_tot)[{lo:.2f},{hi:.2f}]"
            print(s)
            per = []
            for rk in used:
                got, _ = store[(g, rk)]
                r = band(got["H_tot"], f1, f2)
                if r:
                    per.append(f"{rk[:8]}:{r[0]:.2f}(n{len(got['H_tot'])})")
            print(f"{'':9s} per-route H_tot: " + "  ".join(per))


if __name__ == "__main__":
    main()
