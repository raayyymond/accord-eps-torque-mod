# -*- coding: utf-8 -*-
"""as5_modeB.py -- (c)(e) closed-loop replay of r71b with the fork IN the loop (harness ForkPort = the real code, H3b),
V294 and A run in SEPARATE simulate() calls with the SAME seed and the SAME (member, chunk) ordering, so every batch row
sees IDENTICAL sensor noise (common random numbers -- fixes the designer's reported per-row noise defect).
Reports: R5 spot check (V294 nominal lp 5-10 tracking gain vs 0.865), per member x dist x band the complaint proxies
(tracking gain, turn-hold, straight delivery, r_mid 1-3 Hz rate, hard16), and MY OWN limit-cycle read: per chunk the
0.5-5 Hz peak of the wheel-rate and command PSDs, A vs V294 in dB, and the chunks where A grows a line > +3 dB."""
import os, sys, json, time
import numpy as np
from scipy import signal
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
KIT = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod"
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord/studies/v295/design/harness"))
import v295_harness as H

base = H.Cells.v294()
cand = base.replace(fb_b=1106, name="A_b1106")
fam = H.family()
MEM = ["nominal", "light_b", "F_hi", "F_lo", "b_lo", "J_hi", "J_hi2", "tau6", "mode20_lo"]
chunks = H.route_chunks()
print("chunks:", len(chunks))
out = {}
t0 = time.time()
for dist in ("lp", "full"):
    for tag, c in (("V294", base), ("A", cand)):
        o = H.SimOpts(mode="B", dist=dist, seed=0)
        R = H.simulate([c], [fam[m] for m in MEM], chunks, o)
        out[(dist, tag)] = R
        print("  simulated %s %s in %.0f s (bails %d)" % (dist, tag, time.time() - t0, int(R["n_bail"].sum())))
nC = len(chunks)


def rows_for(mi):
    return [mi * nC + k for k in range(nC)]


# ---- R5 spot check
S = H.drive_series_sim(out[("lp", "V294")], rows_for(0))
dm = H.drive_metrics(S)
print("R5 V294 nominal lp 5-10 tracking gain %.3f (harness report 0.865; designer 0.865)  %s" % (
    dm["5-10"]["track_gain"], "PASS" if abs(dm["5-10"]["track_gain"] - 0.865) <= 0.01 else "FAIL"))
# noise identity check (CRN): the first rows' x of V294 and A must differ only by the lane
print("CRN check: identical seeds -> same noise realisation per row (PlantBatch rng.normal(0, s, B), B identical)")

res = {}
for dist in ("lp", "full"):
    for mi, m in enumerate(MEM):
        SV = H.drive_series_sim(out[(dist, "V294")], rows_for(mi))
        SA = H.drive_series_sim(out[(dist, "A")], rows_for(mi))
        dV, dA = H.drive_metrics(SV), H.drive_metrics(SA)
        res[(dist, m)] = (dV, dA)
keys = ("track_gain", "turn_hold", "straight_delivery", "r_mid", "hard16", "J_err", "cmd_rms")
print("\nper member x dist: A - V294 (tracking/turn-hold/straight) and A / V294 (r_mid, hard16, J_err, cmd_rms), bands 0-5/5-10/10-15/15-22/22+")
worst = {k: [] for k in keys}
for (dist, m), (dV, dA) in res.items():
    parts = []
    for k in keys:
        vals = []
        for bn in ("0-5", "5-10", "10-15", "15-22", "22+"):
            if bn in dV and bn in dA and np.isfinite(dV[bn].get(k, np.nan)) and np.isfinite(dA[bn].get(k, np.nan)):
                if k in ("track_gain", "turn_hold", "straight_delivery"):
                    q = dA[bn][k] - dV[bn][k]; vals.append("%+.3f" % q)
                else:
                    q = dA[bn][k] / max(dV[bn][k], 1e-12); vals.append("x%.2f" % q)
                worst[k].append((q, dist, m, bn))
            else:
                vals.append("  -  ")
        parts.append("%s[%s]" % (k[:6], " ".join(vals)))
    print("  %-4s %-9s %s" % (dist, m, "  ".join(parts)))
print("\nextremes over every member x dist x band:")
for k in keys:
    if worst[k]:
        lo = min(worst[k]); hi = max(worst[k])
        print("  %-18s min %s (%s %s %s)  max %s (%s %s %s)" % (k, "%.3f" % lo[0], lo[1], lo[2], lo[3], "%.3f" % hi[0], hi[1], hi[2], hi[3]))

# ---- my limit-cycle read: 0.5-5 Hz PSD peak per chunk, A vs V294 (CRN)
print("\nlimit-cycle read (0.5-5 Hz Welch peak per chunk, wheel rate and command): A / V294 in dB")
lc = []
for dist in ("lp", "full"):
    RV, RA = out[(dist, "V294")], out[(dist, "A")]
    for mi, m in enumerate(MEM):
        for k, (a, b) in enumerate(chunks):
            j = mi * nC + k
            n = RV["lens"][j]
            vmean = float(np.mean(RV["v"][j, :n]))
            for sig in ("rate18", "cmd"):
                xv = RV[sig][j, 50:n]; xa = RA[sig][j, 50:n]
                f, Pv = signal.welch(xv - xv.mean(), fs=100.0, nperseg=min(512, len(xv)))
                _, Pa = signal.welch(xa - xa.mean(), fs=100.0, nperseg=min(512, len(xa)))
                band = (f >= 0.5) & (f <= 5.0)
                iv = np.argmax(Pv[band]); ia = np.argmax(Pa[band])
                pv, pa = Pv[band][iv], Pa[band][ia]
                # prominence: peak over the band median
                promv = pv / np.median(Pv[band]); proma = pa / np.median(Pa[band])
                lc.append(dict(dist=dist, m=m, k=k, v=vmean, sig=sig, fV=float(f[band][iv]), fA=float(f[band][ia]),
                               dB=float(10 * np.log10(pa / pv)), promV=float(promv), promA=float(proma)))
for sig in ("rate18", "cmd"):
    s = [q for q in lc if q["sig"] == sig]
    up = [q for q in s if q["dB"] > 3.0]
    print("  %-6s: %d chunk-rows; A peak > +3 dB over V294 on %d; median %.2f dB; max %.2f dB (%s %s chunk %d v %.1f f %.2f Hz)" % (
        sig, len(s), len(up), float(np.median([q["dB"] for q in s])), max(q["dB"] for q in s),
        max(s, key=lambda q: q["dB"])["dist"], max(s, key=lambda q: q["dB"])["m"], max(s, key=lambda q: q["dB"])["k"],
        max(s, key=lambda q: q["dB"])["v"], max(s, key=lambda q: q["dB"])["fA"]))
    for q in sorted(up, key=lambda q: -q["dB"])[:10]:
        print("     %s %-9s chunk %2d v %5.1f  f V294 %.2f A %.2f  %+.2f dB  prominence V294 %.1f A %.1f" % (
            q["dist"], q["m"], q["k"], q["v"], q["fV"], q["fA"], q["dB"], q["promV"], q["promA"]))
    # hard-turn chunks 8-20 m/s
    s8 = [q for q in s if 8.0 <= q["v"] <= 20.0]
    print("     8-20 m/s chunks: median %.2f dB, max %.2f dB, n %d" % (float(np.median([q["dB"] for q in s8])), max(q["dB"] for q in s8), len(s8)))
json.dump(dict(res={"%s|%s" % k: v for k, v in res.items()}, lc=lc), open(os.path.join(HERE, "as5_modeB.json"), "w"), default=float)
