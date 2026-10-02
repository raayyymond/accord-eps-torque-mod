"""ADV-ARITHMETIC V298 step 1: full byte diff V298 vs V295 over [0x13000, 0x100000), grouped into runs.
Independent of the build script: reads only the two images."""
import hashlib, sys
FW = "C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord/"
V298 = FW + "_v298_V298-ANGLELOOP.C3REV2P.CAM-KI40.GBP.A3.OPH300.OPSKIP.KP112.KD48-FB.SUM.SP69AE.A16A_plain_image.bin"
V295 = FW + "_v295_V295-V294BASE-ACCELTRIM.B1050-SUBR.SHL2-FB.DIFF.C1024-POLE.2.0HZ.1011.1050-KP.FLAT.960.ALL-KD0-R24.2048-MAP.LINEAR.TO6X.TORQUE.TAP_plain_image.bin"
a = open(V295, "rb").read(); b = open(V298, "rb").read()
print("V295", hashlib.sha256(a).hexdigest()[:12], len(a)); print("V298", hashlib.sha256(b).hexdigest()[:12], len(b))
lo, hi = 0x13000, 0x100000
runs = []; cur = None
for i in range(lo, hi):
    if a[i] != b[i]:
        if cur and i - cur[1] <= 1: cur[1] = i + 1
        else:
            cur = [i, i + 1]; runs.append(cur)
tot = sum(r[1] - r[0] for r in runs)
nd = sum(1 for i in range(lo, hi) if a[i] != b[i])
print("runs", len(runs), "span bytes", tot, "differing bytes", nd)
for s, e in runs:
    print(f"{s:#08x}..{e:#08x} ({e-s:3d})  old {a[s:e].hex()[:80]}  new {b[s:e].hex()[:80]}")
