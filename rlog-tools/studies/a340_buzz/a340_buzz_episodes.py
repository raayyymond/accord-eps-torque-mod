"""List buzz episodes (BZ > 4 deg/s for >= 0.3 s, merged across gaps < 0.2 s). usage: <cache dir> [manual-only=0]"""
import sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from a340_buzz_lib import load, segs

C = sys.argv[1]
MAN = len(sys.argv) > 2 and sys.argv[2] == "1"
TH = 4.0
tot = {}
print("seg   t0     dur   eng  lat  v     ang0  ang1   rlp   |tq|lp  press  cmd   BZp50  pk-pk rate  as-sampled-period")
for seg, p in segs(C):
    d = load(p)
    agree = (d["req"] == d["lat"]).mean()
    on = d["bz"] > TH
    # merge gaps < 20 samples
    idx = np.flatnonzero(np.diff(np.r_[0, on.astype(int), 0]))
    st, en = idx[0::2], idx[1::2]
    M = []
    for s, e in zip(st, en):
        if M and s - M[-1][1] < 20:
            M[-1][1] = e
        else:
            M.append([s, e])
    for s, e in M:
        if e - s < 30:
            continue
        sl = slice(s, e)
        eng = d["req"][sl].mean()
        if MAN and eng > 0.1:
            continue
        hr = d["hr"][sl]
        # dominant period from zero-crossings of hr
        zc = np.flatnonzero(np.diff(np.sign(hr)) != 0)
        per = 2 * np.median(np.diff(zc)) if len(zc) > 3 else np.nan
        key = "eng" if eng > 0.5 else "man"
        tot[key] = tot.get(key, 0) + (e - s) / 100
        print("%3d %6.1f %5.1f  %4.2f %4.2f %5.1f %6.1f %6.1f %6.1f %6.0f  %4.2f %6.0f  %5.1f  %5.1f  %4.1f" % (
            seg, d["t"][s], (e - s) / 100, eng, d["lat"][sl].mean(), d["v"][sl].mean(), d["ang"][s], d["ang"][e - 1],
            d["rlp"][sl].mean(), np.abs(d["tlp"][sl]).mean(), d["pressed"][sl].mean(),
            np.nanmean(np.abs(d["cmd"][sl])) if d["has_e4"] else np.nan, np.median(d["bz"][sl]),
            np.percentile(d["rate"][sl], 95) - np.percentile(d["rate"][sl], 5), per))
    print("   -- seg %d req/latActive agreement %.3f" % (seg, agree))
print("total episode seconds", tot)
