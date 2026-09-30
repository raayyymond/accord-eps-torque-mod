"""ADV-D 2b: the same positive-controlled raw decoder as d2_census.py (imported from its source), on the interlock /
downstream cells.  Reproduces d2b_more_out.txt (detector, damper-mode flag, soft-EME), d2c_more_out.txt (aggregator
neighbourhood) and d2d_lockstep_out.txt (aggregator shadow) in one run."""
src = open("d2_census.py").read().split("# ---------------------------------------------------------------------------------------------------- targets")[0]
ns = {}
exec(src, ns)
decode, ea, GP = ns["decode"], ns["ea"], ns["GP"]
SETS = [
    ("d2b", [("gp-0x6c2c detector operand", -0x6C2C, 2), ("gp-0x680a damper-mode flag", -0x680A, 1),
             ("gp-0x3570 soft-EME I", -0x3570, 4), ("gp-0x6b08 post-gov total", -0x6B08, 2), ("gp-0x6994 derate", -0x6994, 2)]),
    ("d2c", [("gp-0x6b98", -0x6B98, 2), ("gp-0x6b94 aggregator", -0x6B94, 2), ("gp-0x6b4c lkas at agg", -0x6B4C, 2),
             ("gp-0x6ace", -0x6ACE, 2)]),
    ("d2d", [("gp-0x4ce0 agg shadow", -0x4CE0, 2), ("gp-0x6b4c lkas at agg", -0x6B4C, 2), ("gp-0x6b3a", -0x6B3A, 2)]),
]
for tag, T in SETS:
    print("== %s ==" % tag)
    for n, o, w in T:
        t = (GP + o) & 0xFFFFFFFF
        H = []
        for i in range(0x13000, 0x100000 - 6, 2):
            for kind, base, disp, ww, rw, ln in decode(i):
                a = ea(base, disp)
                if a is not None and a < t + w and t < a + ww:
                    H.append("0x%X %s %s" % (i, kind, rw))
        print("%-30s %d: %s" % (n, len(H), ", ".join(H)))
