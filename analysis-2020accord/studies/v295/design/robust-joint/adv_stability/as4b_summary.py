import json, numpy as np
res = json.load(open("as4_outer.json"))
st = [r for r in res if r["V"]["GM"] > 1.0]
un = [r for r in res if r["V"]["GM"] <= 1.0]
print("outer cases %d: V294 linearly stable %d, unstable %d" % (len(res), len(st), len(un)))
print("V294 stable -> A unstable: %d" % sum(1 for r in st if r["A"]["GM"] <= 1.0))
print("V294 unstable -> A stable: %d of %d" % (sum(1 for r in un if r["A"]["GM"] > 1.0), len(un)))
print("min A_GM/V294_GM over ALL cases: %.3f" % min(r["A"]["GM"] / r["V"]["GM"] for r in res))
w = max(st, key=lambda r: r["A"]["Ms"] / r["V"]["Ms"])
print("V294-stable cases: max Ms ratio A/V294 %.3f (%s v%.1f relay %.0f pipe %.0f srg %.1f: %.3f -> %.3f)" % (w["A"]["Ms"] / w["V"]["Ms"], w["case"], w["v"], w["relay"], w["pipe"], w["srg"], w["V"]["Ms"], w["A"]["Ms"]))
w = min(st, key=lambda r: r["A"]["PM"] - r["V"]["PM"] if np.isfinite(r["A"]["PM"]) and np.isfinite(r["V"]["PM"]) else 0)
print("V294-stable cases: largest PM loss %.1f deg (%s v%.1f relay %.0f pipe %.0f srg %.1f: %.1f -> %.1f)" % (w["A"]["PM"] - w["V"]["PM"], w["case"], w["v"], w["relay"], w["pipe"], w["srg"], w["V"]["PM"], w["A"]["PM"]))
sm = [r for r in st if r["A"]["Ms"] > max(1.1 * r["V"]["Ms"], 1.5)]
print("F-OUT-1 Ms clause on V294-STABLE cases: %d" % len(sm))
for r in sm[:10]:
    print("   ", r["case"], r["v"], r["relay"], r["pipe"], r["srg"], r["V"], r["A"])
# identified family only (not light_b), all cases
idf = [r for r in res if not r["case"].startswith("light_b")]
print("identified family (excl light_b): min GM V294 %.2f A %.2f ; max Ms V294 %.3f A %.3f" % (min(r["V"]["GM"] for r in idf), min(r["A"]["GM"] for r in idf), max(r["V"]["Ms"] for r in idf), max(r["A"]["Ms"] for r in idf)))
lb = [r for r in res if r["case"] == "light_b Jx1.0 bx1.00"]
print("light_b proper: min GM V294 %.2f A %.2f ; worst case %s" % (min(r["V"]["GM"] for r in lb), min(r["A"]["GM"] for r in lb), min(lb, key=lambda r: r["A"]["GM"])))
