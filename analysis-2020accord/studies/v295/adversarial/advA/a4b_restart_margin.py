# -*- coding: utf-8 -*-
"""ADV-A a4b: (1) the b-DEPENDENT part of the restart: max |T_V295 - T_V294| on the same lane, same state, bail
lengths 1/2/5; (2) the largest b whose 1-tick and 2-tick pulse at 100 deg/s stays <= 288 over the envelope, both
fixed-point ends; (3) the exact 288 lane re-run through the SCALAR mirror as a second implementation."""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import advA_lane as A  # noqa: E402
import a4_restart as R  # noqa: E402  (re-runs its validation + table on import; harmless)

J = R.J


def traces(c, rate, end, bl):
    r = R.run(c, rate, end, bail_len=bl, want_trace=True)
    return r["trace"], r["T_pre"]


for bl in (1, 2, 5):
    for end in ("lo", "hi"):
        t4, p4 = traces(J["v294"], 100.0, end, bl)
        t5, p5 = traces(J["v295"], 100.0, end, bl)
        d = np.abs(t5 - t4).max(axis=0)
        j = int(np.argmax(d))
        print("bail %d end %s: max |T295 - T294| over the restart = %d T (idx %d ds %+d rs %+d); T_pre equal on all lanes: %s"
              % (bl, end, d[j], R.lanes[j][0], R.lanes[j][1], R.lanes[j][2], bool(np.array_equal(p4, p5))))


def worst(b, bl):
    c = dict(J["v295"]); c["fb_b"] = b
    return max(int(R.run(c, 100.0, e, bail_len=bl)["pk_all"].max()) for e in ("lo", "hi", "boot"))


for bl in (1, 2):
    lo, hi = 567, 1060
    while hi - lo > 1:
        mid = (lo + hi) // 2
        if worst(mid, bl) <= 288:
            lo = mid
        else:
            hi = mid
    print("bail %d: largest b with worst pulse <= 288 at 100 deg/s over the envelope (both ends + boot): %d (%d T); b %d -> %d T"
          % (bl, lo, worst(lo, bl), lo + 1, worst(lo + 1, bl)))

# (3) scalar second implementation of the 288 lane: idx 238, demand -, rate -, output lag at its LOW (most negative) end
c5 = J["v295"]
L = A.Lane(c5)
x = -800; sp = L.sp_of(238, -1)
for _ in range(3000):
    L.tick(x, sp, 238)
S = L.last["S"]; q = (S * L.lb) >> 10
fx = [o for o in range(L.o - 200, L.o + 200) if o == ((L.la * o) >> 10) + q]
print("scalar: settled S %d, o %d, fixed-point interval [%d .. %d] (%d points)" % (S, L.o, fx[0], fx[-1], len(fx)))
for end, o0 in (("lo", fx[0]), ("hi", fx[-1])):
    L2 = A.Lane(c5)
    for _ in range(3000):
        L2.tick(x, sp, 238)
    L2.o = o0
    for _ in range(300):
        Tp = L2.tick(x, sp, 238)
    tr = [L2.tick(x, sp, 238, valid=(k >= 1)) for k in range(1501)]
    dev = [t - Tp for t in tr]
    k = int(np.argmax(np.abs(dev)))
    print("  end %s: T_pre %d, pulse max |T-T_pre| = %d at tick %d after the bail (T %d); first 6 T after the bail %s"
          % (end, Tp, abs(dev[k]), k, tr[k], tr[:6]))
# is the LOW end reachable?  approach from a LARGER |demand| (idx 240 -> 238): where does o land?
L3 = A.Lane(c5)
for _ in range(3000):
    L3.tick(x, L3.sp_of(240, -1), 240)
for _ in range(3000):
    L3.tick(x, sp, 238)
print("reachability: after idx 240 -> 238 (demand magnitude falling), o settles at %d (interval [%d..%d]) -> %s end"
      % (L3.o, fx[0], fx[-1], "LOW(most negative)" if L3.o == fx[0] else ("HIGH" if L3.o == fx[-1] else "interior")))
