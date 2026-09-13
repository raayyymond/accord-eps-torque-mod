# -*- coding: utf-8 -*-
"""V292 FLIGHT READ -- the DECISIVE attribution test.

The prereg's b3 DUTY read (0.47-0.50) turns out NOT to discriminate on this corpus: r6c/V282 measures
0.467 engaged and the three new routes 0.418-0.453, overlapping ranges.  So test the bit's MEANING
instead of its duty.

V292's b3 is `sign(fb state gp-0x3d30)`.  The fb state is the LKAS rate-PID feedback lag's accumulator,
driven by x = -wire (the negated 0x18F STEER_ANGLE_RATE) through a one-pole lag.  So if the rung is live:
  (1) b3 must be a near-DETERMINISTIC function of sign(-rate), lagged by the filter's group delay;
  (2) it must toggle at the rate of a filtered kinematic sign, not at the frame rate.
V282's b3 is an aliased bit with neither property.

Tests, all on the 0x14A native frames:
  A  P(b3=1 | rate<0) vs P(b3=1 | rate>0), engaged and disengaged.
  B  the lag profile: max over lag L of |corr(b3, sign(rate[n-L]))|, L = -10..+30 frames.
  C  the ZERO-CROSSING match: does b3 change state within +-3 frames of a sign(rate) zero crossing?
  D  toggle rate (Hz) of b3 vs the toggle rate of sign(rate) itself, same frames.
  E  the same four for b5/b6/b7 as controls (they are NOT sign(fb state) on any build).

ANALYSIS ONLY.  Run: python rlog-tools/studies/grind/v292_flight_b3sign.py
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
SCR = os.path.join(HERE, "_scratch")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TAGS = ["r6d_v292", "r6e_v292", "r6f_v292", "r6c", "r39", "r5e_v288", "r62_v289"]
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def prep(tag):
    D = dict(np.load(os.path.join(CACHE, tag + ".npz")))
    B = dict(np.load(os.path.join(CACHE, tag + "_b4.npz")))
    t18, sca, rate = D["t18"], D["sca"].astype(float), D["rate"].astype(float)
    te4, req = D["te4"], D["req"].astype(float)
    t14b, b4 = B["t14b"], B["b4"].astype(int)
    eng = (np.interp(t14b, t18, sca) > 0.5) & (np.interp(t14b, te4, req) > 0.5)
    r14 = np.interp(t14b, t18, rate)
    # only frames on a contiguous 0x14A cadence (no segment joins inside a lag window)
    dt = np.diff(t14b, prepend=t14b[0])
    good = (dt > 0.003) & (dt < 0.03)
    return dict(tag=tag, t=t14b, b4=b4, eng=eng, rate=r14, good=good,
                bits={n: ((b4 >> n) & 1).astype(float) for n in range(8)})


def lagprofile(bit, s, mask, lags):
    """corr(bit[n], s[n-L]) over L; s is sign(rate) in {-1,0,+1}."""
    out = {}
    n = len(bit)
    for L in lags:
        if L >= 0:
            a, b = bit[L:], s[:n - L] if L else s
            m = mask[L:]
        else:
            a, b = bit[:n + L], s[-L:]
            m = mask[:n + L]
        m = m & (b != 0)
        if m.sum() < 500:
            out[L] = np.nan
            continue
        x, y = a[m], b[m]
        out[L] = float(np.corrcoef(x, y)[0, 1])
    return out


def main():
    pr("V292 FLIGHT READ -- DECISIVE ATTRIBUTION: IS 0x14A b3 = sign(fb state)?")
    pr("=" * 120)
    pr("The prereg's b3 DUTY read does not discriminate on this corpus (r6c/V282 0.467 engaged vs the")
    pr("new routes 0.418-0.453).  Test the bit's MEANING instead: a live sign(fb state) rung must be a")
    pr("near-deterministic, LAGGED function of sign(-rate) and must toggle like a filtered kinematic")
    pr("sign, not like an aliased bit.")
    pr("")
    res = {}
    lags = list(range(-6, 26))
    for tag in TAGS:
        try:
            G = prep(tag)
        except FileNotFoundError:
            pr("  %-10s : cache absent, skipped" % tag)
            continue
        r = {}
        for name, mask in (("engaged", G["eng"] & G["good"]),
                           ("disengaged", (~G["eng"]) & G["good"])):
            s = np.sign(G["rate"])
            sub = {}
            for n in (3, 5, 6, 7):
                bit = G["bits"][n]
                # A: conditional duties
                mneg = mask & (G["rate"] < -2)
                mpos = mask & (G["rate"] > 2)
                dneg = float(bit[mneg].mean()) if mneg.sum() > 100 else np.nan
                dpos = float(bit[mpos].mean()) if mpos.sum() > 100 else np.nan
                # B: lag profile
                lp = lagprofile(bit, s, mask, lags)
                fin = {k: v for k, v in lp.items() if np.isfinite(v)}
                bestL = max(fin, key=lambda k: abs(fin[k])) if fin else np.nan
                bestC = fin.get(bestL, np.nan)
                # D: toggle rate (per second, on the ~100 Hz 0x14A frame axis)
                mm = mask.copy()
                tog = float(np.mean(np.diff(bit[mm]) != 0) * 100.0) if mm.sum() > 500 else np.nan
                sub["b%d" % n] = dict(duty_rate_neg=dneg, duty_rate_pos=dpos,
                                      split=(abs(dneg - dpos) if np.isfinite(dneg) and np.isfinite(dpos) else np.nan),
                                      best_lag=bestL, best_corr=bestC, toggle_hz=tog,
                                      lag_profile={str(k): v for k, v in lp.items()})
            # the sign channel's own toggle rate, for scale
            sub["sign(rate) toggle_hz"] = float(np.mean(np.diff(s[mask]) != 0) * 100.0) if mask.sum() > 500 else np.nan
            sub["n"] = int(mask.sum())
            r[name] = sub
        res[tag] = r

    for name in ("engaged", "disengaged"):
        pr("")
        pr("=" * 120)
        pr("%s FRAMES" % name.upper())
        pr("=" * 120)
        pr("%-10s %8s | %-34s | %-34s" % ("route", "n", "b3  (V292: = sign(fb state))", "b7 (control: V282 three-sign rung)"))
        pr("%-10s %8s | %6s %6s %6s %5s %6s | %6s %6s %6s %5s %6s | %6s" %
           ("", "", "P|r<0", "P|r>0", "split", "lag", "corr", "P|r<0", "P|r>0", "split", "lag", "corr", "tog b3"))
        for tag in TAGS:
            if tag not in res or name not in res[tag]:
                continue
            a = res[tag][name]["b3"]; b = res[tag][name]["b7"]
            pr("%-10s %8d | %6.3f %6.3f %6.3f %5s %6.3f | %6.3f %6.3f %6.3f %5s %6.3f | %5.1f/s (sign(rate) %.1f/s)" % (
                tag, res[tag][name]["n"], a["duty_rate_neg"], a["duty_rate_pos"], a["split"],
                a["best_lag"], a["best_corr"],
                b["duty_rate_neg"], b["duty_rate_pos"], b["split"], b["best_lag"], b["best_corr"],
                a["toggle_hz"], res[tag][name]["sign(rate) toggle_hz"]))

    pr("")
    pr("=" * 120)
    pr("b3 LAG PROFILE, ENGAGED -- corr(b3[n], sign(rate[n-L])).  A live sign(fb state) rung peaks at a")
    pr("SMALL POSITIVE lag with a LARGE |corr|; an aliased bit has no peak.")
    pr("=" * 120)
    show = [-4, -2, 0, 1, 2, 3, 4, 5, 6, 8, 10, 14, 20]
    pr("%-10s %s" % ("route", " ".join("L%+d " % L for L in show)))
    for tag in TAGS:
        if tag not in res:
            continue
        lp = res[tag]["engaged"]["b3"]["lag_profile"]
        pr("%-10s %s" % (tag, " ".join("%+.2f" % lp[str(L)] if np.isfinite(lp[str(L)]) else "  nan" for L in show)))

    with open(os.path.join(SCR, "v292_flight_b3sign.json"), "w") as fh:
        json.dump(res, fh, indent=1, default=float)
    io.open(os.path.join(SCR, "v292_flight_b3sign.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("\nwrote v292_flight_b3sign.{txt,json}")


if __name__ == "__main__":
    main()
