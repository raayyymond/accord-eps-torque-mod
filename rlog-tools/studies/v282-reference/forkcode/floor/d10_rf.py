# -*- coding: utf-8 -*-
"""d10 -- the EXACT AccordRefFilter transfer priced on the metric, and the model's own falsification test.

AccordRefFilter is TWO cascaded first-order filters of RC seconds on the setpoint (latcontrol_torque.py
:320-329), so its exact transfer is 1/(1 + j w RC)^2 and its DC group delay is exactly 2*RC.
T64 flew RC = 0.06 (params_all.json, both routes) -> 119 ms of pure lag at unity DC magnitude.
The V282 reference routes flew it ABSENT.

W_undo = (1 + j w 0.06)^2 removes it EXACTLY.  It is a TOGGLE (AccordRefFilter 0.0), not fork code.

FALSIFICATION TEST the model has to survive: run the SAME model BACKWARDS on the V282 routes --
insert the filter the torque build carries -- and see whether it moves V282's J by an amount
consistent with the difference the model claims.  If adding 119 ms of lag to V282 barely moves its J,
then removing it from T64 cannot be worth 46 % of the gap and the model is wrong.
"""
import json
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
OUT = HERE / "out"
sys.path.insert(0, str(HERE))
from d8_refladder import Ref, T64, V282R, JREF, JFLOWN  # noqa: E402

RC = 0.06


def rf(f, rc=RC):
    return 1.0 / (1.0 + 2j * np.pi * f * rc) ** 2


if __name__ == "__main__":
    o = {}
    print("=" * 104)
    print("A. THE EXACT AccordRefFilter INVERSE on the torque build (toggle AccordRefFilter 0.06 -> 0.0)")
    for corrected in (False, True):
        R = Ref(T64, corrected)
        W = 1.0 / rf(R.f)
        J, sh = R.apply(W)
        gd = 2 * RC * 1000
        s = (R.f >= 0.15) & (R.f <= 0.6)
        print(f"   {'corrected' if corrected else 'raw      '}  J {R.J0:.4f} -> {J:.4f}   "
              f"closure {(JFLOWN-J)/(JFLOWN-JREF)*100:5.1f}%   cmd shake x{sh:.3f}   "
              f"|W| in band {float(np.mean(np.abs(W[s]))):.3f}, at 2.5 Hz {abs(W[np.argmin(abs(R.f-2.5))]):.2f}")
        o[f"undo_{'corr' if corrected else 'raw'}"] = dict(J0=R.J0, J=J, shake=sh)
        del R
    print(f"   NOTE |W| rises as f^2 -- at 2.5 Hz the exact inverse is a large boost.  The TOGGLE does")
    print(f"   not apply an inverse, it REMOVES the filter, which is the same thing only if the rest of")
    print(f"   the chain is unchanged.  It is: the filter sits alone on the setpoint.")

    print("\n" + "=" * 104)
    print("B. FALSIFICATION TEST -- run the model BACKWARDS on the V282 routes")
    R = Ref(V282R, corrected=False)
    for rc in (0.06, 0.12):
        J, sh = R.apply(rf(R.f, rc))
        print(f"   V282 + AccordRefFilter {rc:.2f} inserted:  J {R.J0:.4f} -> {J:.4f}  "
              f"({(J-R.J0)/R.J0*100:+.0f} %)   cmd shake x{sh:.3f}")
    o["v282_insert"] = True
    print("   The model says the torque build's own filter costs it that much.  The flown contrast")
    print("   (r70/r71 carry no filter) read ~null, but at kp/LAF 0.050-0.061 on different roads.")

    print("\n" + "=" * 104)
    print("C. WHERE THE 400 ms GOES (this stream's numbers beside the withdrawn ARM-RF stream's)")
    print(f"   {'leg':34s} {'this stream':>13s} {'ARM-RF stream':>15s}")
    print(f"   {'AccordRefFilter (2 x RC, toggle)':34s} {'119 ms':>13s} {'124.7 ms':>15s}")
    print(f"   {'the loop, setpoint -> wheel angle':34s} {'~197 ms':>13s} {'197.2 ms':>15s}")
    print(f"   {'livePose publish latency':34s} {'102 ms':>13s} {'not split out':>15s}")
    print(f"   {'delay canceller + jerk filter':34s} {'in the 132':>13s} {'-2.2 ms':>15s}")
    print(f"   {'vehicle (wheel -> yaw)':34s} {'~0':>13s} {'-6.3 ms':>15s}")
    print(f"   {'MEASURED X -> Y total':34s} {'400 ms':>13s} {'307 + 102':>15s}")
    json.dump(o, open(OUT / "d10.json", "w"), indent=1, default=float)
    print("\nwrote out/d10.json")
