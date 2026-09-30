"""b4_marches.py -- ADV-B step 4: byte-exact 1 kHz marches of the V294 and V295 lanes (my advb_lane, cells from the
IMAGES) on r71b's OWN recorded inputs, built from the raw CAN cache (not from plib / the build script).

Inputs on the 1 kHz grid t_k = t0 + k ms (t0 = first 0x18F frame, absolute logMonoTime):
  wire  = ZOH of the 0xE4 STEER_TORQUE (bus 129 TX echo) at e4_t
  req   = ZOH of 0xE4 STEER_TORQUE_REQUEST
  x     = -0x18F raw rate (the bytes: 0x18F carries -x; FUN_00040a50 / 0x55C62), linearly interpolated at t18 - delta
          ("lin") or zero-order held ("zoh"); rounded to int, clipped +-12000 (no clip occurs on this route)
  bar   = 0x18F torque raw x 1.024 (the kit's inherited firmware bar scale), interpolated like x
delta = the common ECU-frame latency (0x18F / 0x1AB content time = batch time - delta), scanned.
Marches: N4 (V294, r26 forced 0 = FF only), L4 (V294 live), L5 (V295 live), I5 (V295 operand inverted), I4 (V294 inv).
Output: _scratch/marches_d<delta>_<xmode>.npz with int16 T per tick for each march, and the tap-tick index.
Run: python b4_marches.py   (about 10 s per march)
"""
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/lib")
import r71b_cache as R  # noqa: E402
from advb_lane import Lane, cells_from_image  # noqa: E402

OUT = os.path.join(HERE, "_scratch")
os.makedirs(OUT, exist_ok=True)


def inputs(delta_ms=0.0, xmode="lin"):
    D = R.load()
    t18 = D["s18_t"]
    t0 = float(t18[0])
    tend = float(t18[-1])
    n = int((tend - t0) * 1000) + 1
    tk = t0 + np.arange(n) * 1e-3
    j = np.clip(np.searchsorted(D["e4_t"], tk, side="right") - 1, 0, len(D["e4_t"]) - 1)
    pre = np.searchsorted(D["e4_t"], tk, side="right") == 0
    wire = D["e4_cmd"][j].astype(np.int64); wire[pre] = 0
    req = D["e4_req"][j].astype(np.int64); req[pre] = 0
    xs = D["x_fw"].astype(float)
    bs = D["s18_tq_raw"].astype(float) * 1.024
    ts = t18 - delta_ms * 1e-3
    if xmode == "lin":
        x = np.interp(tk, ts, xs)
        bar = np.interp(tk, ts, bs)
    else:
        jj = np.clip(np.searchsorted(ts, tk, side="right") - 1, 0, len(ts) - 1)
        x = xs[jj]; bar = bs[jj]
    x = np.clip(np.round(x), -12000, 12000).astype(np.int64)
    bar = np.clip(np.round(bar), -25600, 25600).astype(np.int64)
    tap_tick = np.round((D["tap_t"] - delta_ms * 1e-3 - t0) * 1000).astype(np.int64)
    return dict(t0=t0, n=n, wire=wire, req=req, x=x, bar=bar, tap_tick=tap_tick, tap_T=D["tap_T"], tap_t=D["tap_t"])


def march(c, I, **kw):
    L = Lane(c, pol=-1, **kw)
    w = I["wire"].tolist(); x = I["x"].tolist(); b = I["bar"].tolist(); r = I["req"].tolist()
    out = np.zeros(I["n"], dtype=np.int16)
    tick = L.tick
    for k in range(I["n"]):
        out[k] = tick(w[k], x[k], b[k], r[k])
    return out


if __name__ == "__main__":
    c4 = cells_from_image("V294")
    c5 = cells_from_image("V295")
    jobs = [(0.0, "lin"), (4.0, "lin"), (-4.0, "lin"), (8.0, "lin"), (0.0, "zoh")]
    if len(sys.argv) > 1:
        jobs = [(float(a.split(":")[0]), a.split(":")[1]) for a in sys.argv[1:]]
    for dms, xm in jobs:
        t_ = time.time()
        I = inputs(dms, xm)
        res = dict(tap_tick=I["tap_tick"], tap_T=I["tap_T"], tap_t=I["tap_t"], t0=I["t0"], req=I["req"].astype(np.int8),
                   x=I["x"].astype(np.int16), wire=I["wire"].astype(np.int16), bar=I["bar"].astype(np.int16))
        res["N4"] = march(c4, I, trim=False)
        res["L4"] = march(c4, I)
        res["L5"] = march(c5, I)
        res["I5"] = march(c5, I, inv=True)
        res["I4"] = march(c4, I, inv=True)
        # null identity: the V295 FF-only march must equal V294's (b is not read when r26 = 0)
        N5 = march(c5, I, trim=False)
        res["N5_equals_N4"] = np.array(bool(np.array_equal(N5, res["N4"])))
        fn = os.path.join(OUT, "marches_d%+d_%s.npz" % (int(dms), xm))
        np.savez_compressed(fn, **res)
        print("delta %+.0f ms x=%s: n %d ticks, %.0f s ; N5==N4 %s ; max|L5| %d max|L4| %d -> %s" % (
            dms, xm, I["n"], time.time() - t_, bool(res["N5_equals_N4"]), np.abs(res["L5"]).max(), np.abs(res["L4"]).max(), fn))
