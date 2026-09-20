"""chain.py picks the producing message by MINIMUM rms of the value match. On the V282 route that selection is an
artefact: carControl.actuators.torque does not match the sent 0xE4 at ANY offset (rms 310-371 counts, 0 % within
1 LSB), and the rms falls monotonically with k, so k=3 "wins" and the reported D_ctl of 41 ms is meaningless.

This script re-derives D_ctl with an EXPLICIT acceptance test -- a candidate is accepted only if >= 90 % of frames
match within 1 LSB -- and reports, for every candidate stream and offset, whether it passes. If nothing passes,
D_ctl is reported as NOT ESTABLISHED for that route rather than as a number.

usage: python chain2.py <counter--hash> [seg]
"""
import sys, json
from pathlib import Path
import numpy as np
import chain as CH

OUT = Path(__file__).resolve().parent / "out"


def analyse2(D):
    out = {}
    sc_t, sc = D["sc_t"], D["sc_e4"]
    cand = {}
    for name in ("carControl", "carOutput"):
        tt = D["cc_t"] if name == "carControl" else D["co_t"]
        val = D["cc_tq"] if name == "carControl" else D["co_tq"]
        if len(tt) == 0:
            continue
        idx = np.searchsorted(tt, sc_t) - 1
        for k in range(4):
            j = idx - k
            ok = (j >= 0) & (np.abs(sc) > 50) & np.isfinite(val[np.clip(j, 0, len(val) - 1)])
            if ok.sum() < 100:
                continue
            x = val[j[ok]]; y = sc[ok]
            g = float(np.dot(x, y) / np.dot(x, x))
            frac = float(np.mean(np.abs(y - np.round(g * x)) <= 1))
            cand[f"{name}_k{k}"] = dict(scale=g, rms=float(np.sqrt(np.mean((y - g * x) ** 2))),
                                        frac_within_1lsb=frac, accept=bool(frac >= 0.90))
    out["candidates"] = cand
    acc = [k for k, v in cand.items() if v["accept"]]
    out["accepted"] = acc
    if not acc:
        out["D_ctl_ms"] = None
        out["verdict"] = "NOT ESTABLISHED - no stream/offset matches the sent 0xE4 within 1 LSB on 90 % of frames"
        return out
    pick = sorted(acc, key=lambda s: (int(s[-1]), s.startswith("carOutput")))[0]
    name, k = pick.rsplit("_k", 1); k = int(k)
    tt = D["cc_t"] if name == "carControl" else D["co_t"]
    idx = np.searchsorted(tt, sc_t) - 1 - k
    jcst0 = np.searchsorted(D["cst_t"], tt) - 1
    offs = {}
    for m in range(3):
        jj = jcst0 - m
        g = jj >= 0
        a = np.diff(D["cst_sa"][jj[g]])
        c = np.diff(D["cc_curvnow"][g]) if name == "carControl" else None
        if c is None or len(a) != len(c) or np.std(a) == 0 or np.std(c) == 0:
            offs[m] = float("nan")
        else:
            offs[m] = float(np.corrcoef(a, c)[0, 1])
    mbest = max(offs, key=lambda q: abs(offs[q]) if np.isfinite(offs[q]) else -1)
    ok = idx >= 0
    jcst = jcst0[idx[ok]] - mbest
    g = jcst >= 0
    d = (sc_t[ok][g] - D["cst_t"][jcst[g]]) * 1e3
    out.update(picked=pick, carState_offset_corr=offs, carState_best_offset=mbest,
               D_ctl_ms=[float(np.percentile(d, p)) for p in (5, 25, 50, 75, 95)], D_ctl_mean_ms=float(np.mean(d)),
               verdict="established")
    return out


if __name__ == "__main__":
    route = sys.argv[1]; seg = sys.argv[2] if len(sys.argv) > 2 else "4"
    D = CH.grab(route, seg)
    r = analyse2(D)
    print(route, seg, json.dumps(r, indent=1))
    (OUT / f"chain2_{route}.json").write_text(json.dumps({seg: r}, indent=1))
