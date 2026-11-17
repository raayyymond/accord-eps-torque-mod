# -*- coding: utf-8 -*-
"""g2_cache.py -- one flat 100 Hz cache per route set for the GATE 2 A340 study (reads the analyst's per-segment npz).
Fields (0x14A timebase): seg, t, ang (deg, +LEFT? = -0.1*s16), rate (deg/s), tq (0x18F units), v, pressed, req,
sp_e4 (= -cmd/10 deg, NaN if no 0xE4), cmd (raw 0xE4 s16), sp_cc (carControl.actuators.steeringAngleDeg), bz.
ANALYSIS ONLY.  Runs in seconds; skips sets already cached."""
import glob
import os
import sys
import numpy as np

KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "rlog-tools", "_scratch"))
import a340_buzz_lib as BL  # noqa: E402

CACHE = os.path.join(KIT, "rlog-tools", "_scratch", "cache")
OUT = os.path.join(KIT, "analysis-2020accord", "_scratch", "out", "a340_buzz")
SETS = {
    "a340_mod": ["a340_user55"],
    "a340_stock": ["a340_user5d"],
    "a160_v300": ["a160_v300_000000ad--5909e7772a", "a160_v300_000000ae--74557c6b94", "a160_v300_000000af--a4e305dfc5",
                  "a160_v300_000000b0--26515d54d1", "a160_v300_000000b1--9038570540", "a160_v300_000000b2--b41c6320f8",
                  "a160_v300_000000b3--7449208c37", "a160_v300_000000b4--008b967c94", "a160_b8_all", "a160_b9_all"],
}


def build(name, dirs):
    fn = os.path.join(OUT, "g2_cache_%s.npz" % name)
    if os.path.exists(fn):
        return fn
    cols = {k: [] for k in ("seg", "t", "ang", "rate", "tq", "v", "pressed", "req", "sp_e4", "cmd", "sp_cc", "bz", "route")}
    for ri, d in enumerate(dirs):
        for seg, p in BL.segs(os.path.join(CACHE, d)):
            try:
                A = BL.load(p)
            except Exception as ex:  # noqa: BLE001
                print("skip", p, ex)
                continue
            z = np.load(p)
            t0 = float(z["t0"])
            cc = z["cc"]
            n = len(A["t"])
            sp_cc = np.interp(A["t"], cc[:, 0] - t0, cc[:, 3]) if len(cc) else np.full(n, np.nan)
            cols["seg"].append(np.full(n, seg)); cols["route"].append(np.full(n, ri))
            cols["t"].append(A["t"] + 1000.0 * seg + 1e6 * ri)
            for k in ("ang", "rate", "tq", "v", "pressed", "req", "cmd", "bz"):
                cols[k].append(np.asarray(A[k], float))
            cols["sp_e4"].append(-np.asarray(A["cmd"], float) / 10.0)
            cols["sp_cc"].append(sp_cc)
    np.savez(fn, **{k: np.concatenate(v) for k, v in cols.items()})
    return fn


if __name__ == "__main__":
    for name, dirs in SETS.items():
        fn = build(name, dirs)
        z = np.load(fn)
        eng = z["req"] > 0.5
        print(name, "n %.0f s, engaged %.0f s, moving>2 %.0f s" % (len(z["t"]) / 100, eng.sum() / 100, (z["v"] > 2).sum() / 100))
        m = eng & np.isfinite(z["sp_e4"])
        if m.sum() > 1000:
            print("   engaged: corr(sp_e4, ang) %.4f slope %.3f | corr(sp_cc, ang) %.4f | corr(sp_cc, sp_e4) %.4f, rms(sp_cc-sp_e4) %.2f deg" % (
                np.corrcoef(z["sp_e4"][m], z["ang"][m])[0, 1], np.polyfit(z["ang"][m], z["sp_e4"][m], 1)[0],
                np.corrcoef(z["sp_cc"][m], z["ang"][m])[0, 1], np.corrcoef(z["sp_cc"][m], z["sp_e4"][m])[0, 1],
                np.sqrt(np.mean((z["sp_cc"][m] - z["sp_e4"][m]) ** 2))))
        elif eng.sum() > 1000:
            print("   engaged: corr(sp_cc, ang) %.4f slope %.3f" % (np.corrcoef(z["sp_cc"][eng], z["ang"][eng])[0, 1],
                                                                 np.polyfit(z["ang"][eng], z["sp_cc"][eng], 1)[0]))
