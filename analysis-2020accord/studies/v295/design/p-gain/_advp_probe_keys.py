import contextlib, io, os, sys
import numpy as np
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
for p in (os.path.join(KIT, "analysis-2020accord", "studies", "v295", "lib"), os.path.join(KIT, "rlog-tools", "studies", "grind"),
          os.path.join(KIT, "analysis-2020accord", "model"), os.path.join(KIT, "analysis-2020accord", "studies", "v295", "plant")):
    sys.path.insert(0, p)
with contextlib.redirect_stdout(io.StringIO()):
    import v293_flight_read as FR
for tag in ("r70_v293", "r71b_v294"):
    with contextlib.redirect_stdout(io.StringIO()):
        r = FR.load_route(tag, "V293")
    g = r.g
    print(tag, sorted(g.keys()))
    print("  n", len(g["t"]), "dur s", g["t"][-1] - g["t"][0], "taps", len(g["T_t"]), "eng s", g["eng"].sum() / 100)
    print("  c keys", sorted(r.c.keys()) if hasattr(r.c, "keys") else type(r.c))
import plib as P
d = P.load()
print("plib keys", sorted(d.keys()))
print("dms", d["dms"], "sg", d["sg"], "n frames", len(d["t"]), "taps", len(d["T_tap"]), "ho s", d["ho"].sum() / 100)
