# -*- coding: utf-8 -*-
"""d0_setup -- ADV-dynamics: environment, toggles, real-controller timing, and the V295 cells (adversary, read-only)."""
import os, sys, time, json
import numpy as np
HARN = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/studies/v295/design/harness"
sys.path.insert(0, HARN)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import v295_harness as H
import fork_real as FK

d = H.route()
tg = d["toggles"]
keys = sorted(k for k in tg if any(s in k.lower() for s in ("accord", "steer", "lat", "fric", "ki", "kp", "delay", "custom")))
for k in keys:
    print("%-40s %r" % (k, tg[k]))

# V295 cells from the image, second reader: raw bytes at 0xC63EA
V295_IMG = ("C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR."
            "SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin")
import hashlib
b = open(V295_IMG, "rb").read()
print("V295 sha", hashlib.sha256(b).hexdigest())
b4 = open(H.IMG["V294"][0], "rb").read()
print("V294 sha", hashlib.sha256(b4).hexdigest())
for a in (0xC63E8, 0xC63EA, 0xC62E6):
    print(hex(a), "V294", int.from_bytes(b4[a:a + 2], "little"), "V295", int.from_bytes(b[a:a + 2], "little"))
diff = [i for i in range(min(len(b), len(b4))) if b[i] != b4[i]]
print("n differing bytes V294 vs V295:", len(diff), [hex(x) for x in diff[:10]])
c5 = H.Cells.from_image(V295_IMG, "V295")
c4 = H.Cells.v294()
print("cells diff:", c5.diff(c4))
print("map_x", list(c4.map_x)[:20], "map_y", list(c4.map_y)[:20], "idx_clamp", c4.idx_clamp)

# timing of the REAL controller
rc = FK.RealController(dict(tg, accord_torque_ki_high=0.8))
t = time.time()
for n in range(2000):
    rc.step(True, 20.0, 1.0 + 0.1 * np.sin(n * 0.05), 0.0, False, 0.0, 0.0, 0.0005, 0.426, -0.149, False)
print("real controller: %.1f us/step" % ((time.time() - t) / 2000 * 1e6), "ki now", rc.LaC.pid._k_i)
