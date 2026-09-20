"""ADVERSARY 1 -- the confound census and the +0.808 re-examination. Pure bookkeeping on already-measured
artifacts (params_all.json = each route's own initData; ROUTE-OUT.txt = per-route legs). No new signal math."""
import json, re, itertools
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
STUDY = HERE.parents[1]
P = json.load(open(STUDY / "hsurface" / "surface" / "params_all.json"))

EPS = {  # which EPS firmware each route flew (v282cmp.ROUTES + r70..r74 = V293 per BUILD-LINEAGE)
  "00000039": "V282", "0000003a": "V282", "0000003c": "V282",
  "00000064": "V282", "00000065": "V282", "0000006c--2bc842dbac": "V282",
}
def eps_of(rk):
    return EPS.get(rk, EPS.get(rk.split("--")[0], "V293"))

def fnum(x):
    try: return float(x)
    except Exception: return None

rows = []
for rk, pr in sorted(P.items()):
    kp, laf = fnum(pr.get("SteerKP")), fnum(pr.get("SteerLatAccel"))
    rows.append(dict(rk=rk, short="r" + rk.split("--")[0][-2:] + ("'" if rk == "0000006c--68c6e94b17" else ""),
                     eps=eps_of(rk), kp=kp, laf=laf, kpl=(kp / laf if kp and laf else None),
                     commit=pr.get("GitCommit", "?")[:8], **{k: pr.get(k, "ABSENT") for k in
                     ["AccordDobHz", "AccordTorqueKi", "AccordTorqueKiHigh", "AccordRateLoopGain",
                      "AccordRefFilter", "AccordFrictionHyst", "AccordFrictionHystBand", "AccordHoldLevel",
                      "AccordRatePlantFF", "SteerFriction", "SteerRatio", "AccordHoldMap"]}))

print("=" * 128)
print("1. THE NINE TORQUE ROUTES THE DOSE-RESPONSE WOULD BE READ FROM  (kp/LAF in 0.0607-0.0714)")
print("=" * 128)
T9 = [r for r in rows if r["eps"] == "V293" and r["kpl"] and 0.060 <= r["kpl"] <= 0.072]
hdr = ["short", "kp", "laf", "kpl", "commit", "AccordDobHz", "AccordTorqueKi", "AccordTorqueKiHigh",
       "AccordRateLoopGain", "AccordRefFilter", "AccordFrictionHyst", "SteerFriction", "AccordHoldLevel"]
print(" ".join(f"{h[:12]:>12s}" for h in hdr))
for r in sorted(T9, key=lambda r: (-r["kpl"], r["short"])):
    print(" ".join(f"{str(r[h])[:12]:>12s}" for h in hdr))

print("\n-- ALIASING WITH SteerKP over those nine routes (Cramer's V / exact alias) --")
kpv = np.array([r["kp"] for r in T9])
for k in ["AccordDobHz", "AccordTorqueKi", "AccordTorqueKiHigh", "AccordRateLoopGain", "AccordRefFilter",
          "AccordFrictionHystBand", "AccordHoldLevel", "SteerFriction", "commit", "AccordFrictionHyst"]:
    vals = [str(r[k]) for r in T9]
    lv = sorted(set(vals))
    # is it a deterministic function of SteerKP, and vice versa?
    byk = {}
    for kp, v in zip(kpv, vals):
        byk.setdefault(kp, set()).add(v)
    det = all(len(s) == 1 for s in byk.values())
    byv = {}
    for kp, v in zip(kpv, vals):
        byv.setdefault(v, set()).add(kp)
    inv = all(len(s) == 1 for s in byv.values())
    tag = "PERFECT ALIAS (both ways)" if (det and inv) else ("determined BY SteerKP" if det else
          ("determines SteerKP" if inv else "crossed"))
    print(f"  {k:24s} levels={len(lv):2d} {str(lv)[:56]:56s} -> {tag}")

print("\n" + "=" * 128)
print("2. THE +0.808 WITHIN-V282 CORRELATION -- what it is actually a contrast between")
print("=" * 128)
# per-route L34 lag, from the already-published route-level budget
TXT = (STUDY / "stagebudget" / "stagebudget" / "out" / "ROUTE-OUT.txt").read_text()
def parse(band, speed):
    """Walk the file line by line; a 'BAND x' line opens a band, a '-- speed y --' line opens a speed block."""
    out, curb, curs = {}, None, None
    for ln in TXT.splitlines():
        if ln.startswith("BAND "):
            curb = ln.split()[1]; curs = None; continue
        if ln.strip().startswith("-- speed"):
            curs = ln.strip().split()[2]; continue
        if curb != band or curs != speed:
            continue
        f = ln.split("|")
        if len(f) < 4 or "route" in ln:
            continue
        left = f[0].split(); name = left[0]
        try:                                   # f[1] = L1lag L2lag L34g L34lag L5g L5lag ; f[2] = TOTg TOTlag
            legs = f[1].split(); tot = f[2].split()
            out[name] = dict(n=int(left[-3]), L1lag=float(legs[0]), L2lag=float(legs[1]),
                             L34g=float(legs[2]), L34lag=float(legs[3]), L5g=float(legs[4]), L5lag=float(legs[5]),
                             TOTg=float(tot[0]), TOTlag=float(tot[1]), weak="WEAK" in ln)
        except Exception:
            pass
    return out

NAME2RK = {"r64": "00000064--ce6b0b0ebb", "r65": "00000065--b9f78988bd", "r6c": "0000006c--2bc842dbac",
           "r39": "00000039--f56039af87", "r3a": "0000003a--283a39a1d6", "r3c": "0000003c--927965c2b4"}
def pearson(x, y):
    x, y = np.asarray(x, float), np.asarray(y, float)
    return float(np.corrcoef(x, y)[0, 1])

for band in ["0.15-0.30", "0.30-0.60"]:
    for speed in ["8-15", "15-22", "22+"]:
        d = parse(band, speed)
        xs, ys, nm = [], [], []
        for n, rk in NAME2RK.items():
            if n in d:
                pr = P[rk]
                xs.append(float(pr["SteerKP"]) / float(pr["SteerLatAccel"])); ys.append(d[n]["L34lag"]); nm.append(n)
        if len(xs) >= 5:
            r = pearson(xs, ys)
            # cluster structure: new fork (r64/r65/r6c, Kp 0.9 LAF 6.0) vs old fork (r39/r3a/r3c, Kp 0.8)
            newg = [y for n, y in zip(nm, ys) if n in ("r64", "r65", "r6c")]
            oldg = [y for n, y in zip(nm, ys) if n in ("r39", "r3a", "r3c")]
            # correlation with the cluster label alone (a 2-level dummy)
            dum = [0 if n in ("r64", "r65", "r6c") else 1 for n in nm]
            rd = pearson(dum, ys)
            # within-cluster correlation of kp/LAF vs lag (old cluster is the only one with spread)
            xo = [x for n, x in zip(nm, xs) if n in ("r39", "r3a", "r3c")]
            rw = pearson(xo, oldg) if len(set(xo)) > 1 else float("nan")
            print(f"  band {band} speed {speed:5s} n={len(xs)}  corr(kp/LAF, L34lag)={r:+.3f} | "
                  f"corr(CLUSTER dummy, lag)={rd:+.3f} | within-old-cluster corr={rw:+.3f} | "
                  f"new {np.mean(newg):.0f} ms vs old {np.mean(oldg):.0f} ms")

print("\n-- THE WHOLE FAMILY the '+0.808' is one draw from: every (band, speed, metric) cell with all 6 routes --")
fam = []
for band in ["0.15-0.30", "0.30-0.60"]:
    for speed in ["0-8", "8-15", "15-22", "22+"]:
        d = parse(band, speed)
        if not all(n in d for n in NAME2RK):
            continue
        for metric in ["L34lag", "TOTlag", "L5lag"]:
            xs = [float(P[rk]["SteerKP"]) / float(P[rk]["SteerLatAccel"]) for rk in NAME2RK.values()]
            ys = [d[n][metric] for n in NAME2RK]
            fam.append((band, speed, metric, pearson(xs, ys)))
            print(f"    {band} {speed:5s} {metric:8s} corr = {fam[-1][3]:+.3f}")
rs = np.array([f[3] for f in fam])
print(f"    => {len(rs)} cells: median {np.median(rs):+.3f}, range [{rs.min():+.3f}, {rs.max():+.3f}], "
      f"{int((rs > 0).sum())}/{len(rs)} positive.  A single cell reaching +0.8 is unremarkable in this family.")
# route-mean form: average each route's lag over the speed bins it clears, then correlate
for band in ["0.15-0.30", "0.30-0.60"]:
    acc = {n: [] for n in NAME2RK}
    for speed in ["0-8", "8-15", "15-22", "22+"]:
        d = parse(band, speed)
        for n in NAME2RK:
            if n in d:
                acc[n].append(d[n]["L34lag"])
    xs = [float(P[rk]["SteerKP"]) / float(P[rk]["SteerLatAccel"]) for rk in NAME2RK.values()]
    ys = [float(np.mean(acc[n])) for n in NAME2RK]
    print(f"    ROUTE-MEAN L34 lag, band {band}: corr = {pearson(xs, ys):+.3f}   lags={['%.0f' % y for y in ys]}")

print("\n-- what separates the two V282 clusters (every field that differs) --")
newc, oldc = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"], \
             ["00000039--f56039af87", "0000003a--283a39a1d6", "0000003c--927965c2b4"]
keys = sorted(set().union(*[set(P[r]) for r in newc + oldc]))
ndiff = 0
for k in keys:
    a = sorted({P[r].get(k, "ABSENT") for r in newc}); b = sorted({P[r].get(k, "ABSENT") for r in oldc})
    if a != b:
        ndiff += 1
        print(f"  {k:26s} new={str(a)[:44]:44s} old={str(b)[:44]}")
print(f"  => {ndiff} fields differ between the two clusters of 3. SteerKP is ONE of them, and it moves "
      f"0.8 -> 0.9 in the LOW-lag direction.")

print("\n" + "=" * 128)
print("3. WHAT THE 'DOSE' RANGE ACTUALLY IS")
print("=" * 128)
kpls = sorted({round(r["kpl"], 4) for r in T9})
print(f"  torque family kp/LAF levels: {kpls}  (ratio max/min = {max(kpls)/min(kpls):.3f})")
print(f"  SteerKP levels: {sorted({r['kp'] for r in T9})}   LAF levels: {sorted({r['laf'] for r in T9})}")
print(f"  V282 reference kp/LAF: {sorted({round(float(P[r]['SteerKP'])/float(P[r]['SteerLatAccel']),4) for r in newc})}")
print(f"  V282old kp/LAF:        {sorted({round(float(P[r]['SteerKP'])/float(P[r]['SteerLatAccel']),4) for r in oldc})}")
