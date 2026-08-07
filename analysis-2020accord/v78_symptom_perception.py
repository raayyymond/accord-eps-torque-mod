#!/usr/bin/env python3
"""DELIVERABLE 2 (second half) -- how much FURTHER attenuation the micro ratchet needs, and the
honest bounds on that number.

🛑 THE PERCEPTUAL THRESHOLD IS NOT CALIBRATED. Nothing in this kit has ever measured what level of
band energy the operator can and cannot feel. What the record DOES contain is four verbal reports
mapped onto four measured builds, and that gives a BRACKET, not a threshold. This script builds the
bracket explicitly and then states what it can and cannot support.

THE MAPPING (operator quotes, verbatim from the handoffs):
  V72/r59  k=0.0000  "grind #1 and micro ratcheting both still present"
  V73/r5a  k=0.0000  "...they feel like the same vibration frequency; grind #1 is audible, the micro
                      ratcheting is not." grind #1 at 5 mph wheel-near-zero; ratchet at any speed
  V74/r5d  k=0.5799  "V74 attenuated grinding and micro-ratcheting"
  V75/r5e  k=1.5798  "grinding to an imperceptible level, and micro-ratcheting was barely still
                      existing"

THE ONE ASSUMPTION, and it is load-bearing [BELIEF]: that the numerical level at which a band
becomes imperceptible is the SAME for the 7.8 Hz ratchet as for the 21 Hz grind. It is almost
certainly not exactly true -- the operator's own words say grind #1 is AUDIBLE and the ratchet is
not, i.e. they reach him through different senses. The direction of the error is unknown. Every
number below inherits it.

The estimator for the headline is the PAIRED ratio-of-ratios: both bands read on the SAME windows,
each against the same 24-28 Hz control, one shared episode-bootstrap draw. It is the only form in
which "how far is the ratchet from where grind #1 ended up" is free of route, exposure and driver.

Usage:  python v78_symptom_perception.py   ->  writes _v78_perception.json
"""
import json
import pickle
import sys
from pathlib import Path

import numpy as np

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE))
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

import _grind2_lib as G  # noqa: E402
import _nearcentre_lib as N  # noqa: E402
import v78_symptom_lib as V  # noqa: E402

RNG = np.random.default_rng(78222)
OUT = {}
PARK = {"V74/r5d": [2, 3, 9], "V75/r5e": [0]}
V.install_fs()
R = V.records()
LAD = [("V72/r59", 0.0), ("V73/r5a", 0.0), ("V74/r5d", 0.5799), ("V75/r5e", 1.5798)]


def sub(b, eng=1, vhi=12.5, vlo=0.5):
    return [r for r in R[b] if r["seg"] not in PARK.get(b, []) and r["eng"] == eng
            and vlo <= r["v"] < vhi]


def paired_R(rs, nb=4000):
    """median(6-9 / ctl) / median(18-22 / ctl) over the SAME windows, episode-resampled."""
    ep = {}
    for r in rs:
        if r.get("e_24-28", 0) > 0 and np.isfinite(r["e_6-9"]) and np.isfinite(r["e_18-22"]):
            ep.setdefault(r["ep"], []).append((r["e_6-9"] / r["e_24-28"],
                                               r["e_18-22"] / r["e_24-28"]))
    ks = list(ep)
    if len(ks) < 3:
        return (np.nan,) * 4
    allv = np.concatenate([ep[k] for k in ks])
    obs = float(np.median(allv[:, 0]) / np.median(allv[:, 1]))
    d = np.full(nb, np.nan)
    for i in range(nb):
        z = np.concatenate([ep[ks[j]] for j in RNG.integers(0, len(ks), len(ks))])
        d[i] = np.median(z[:, 0]) / np.median(z[:, 1])
    return obs, float(np.nanpercentile(d, 2.5)), float(np.nanpercentile(d, 97.5)), len(ks)


# duty axis
G.EPKEY = "blk"
SP = [(0.0, 2.0), (2.0, 8.0), (8.0, 25.0), (25.0, 75.0), (75.0, 200.0), (200.0, 1e9)]
with open(ROOT / "_cache_r5d_nearcentre.pkl", "rb") as fh:
    store = pickle.load(fh)
with open(ROOT / "_cache_r5e_sym_nearcentre.pkl", "rb") as fh:
    store.update(pickle.load(fh))
for b in store:
    for r in store[b]:
        r["span"] = r["a_max"] - r["a_min"]
        r["sb"] = G.binof(r["span"], SP)
ACT = {b: [r for r in N.eng_creep(store[b]) if r["sb"] in (2, 3, 4)] for b in store}


def duty(b, key, T=600.0, nb=3000):
    ep = {}
    for r in ACT.get(b, []):
        ep.setdefault(r[G.EPKEY], []).append(r)
    per = [G.col(v, key) for v in ep.values()]
    per = [p[np.isfinite(p)] for p in per]
    per = [p for p in per if len(p)]
    if len(per) < 2:
        return (np.nan,) * 3
    allv = np.concatenate(per)
    d = np.array([float(np.mean(np.concatenate([per[j] for j in
                                                RNG.integers(0, len(per), len(per))]) >= T))
                  for _ in range(nb)])
    return float(np.mean(allv >= T)), float(np.percentile(d, 2.5)), float(np.percentile(d, 97.5))


# ================================================== 1. THE MAPPING ================================
V.hdr("1. THE VERBAL RECORD MAPPED ONTO THE MEASUREMENTS")
print(f"  {'build':<10} {'k':>7} {'18-22 rel':>10} {'6-9 rel':>9} {'18-22 duty':>11} "
      f"{'6-9 duty':>9}   operator")
rows = {}
for b, k in LAD:
    rs = sub(b)
    rel = {}
    for key in ("e_6-9", "e_18-22"):
        v = np.array([r[key] / r["e_24-28"] for r in rs
                      if r.get("e_24-28", 0) > 0 and np.isfinite(r[key])], float)
        rel[key] = float(np.median(v)) if len(v) > 8 else np.nan
    du = {key: duty(b, key)[0] for key in ("e_6-9", "e_18-22")}
    rows[b] = dict(k=k, rel=rel, duty=du, verbal=V.VERBAL.get(b, ""))
    print(f"  {b:<10} {k:>7.4f} {rel['e_18-22']:>10.2f} {rel['e_6-9']:>9.2f} "
          f"{du['e_18-22']:>11.3f} {du['e_6-9']:>9.3f}   {V.VERBAL.get(b, '')}")
OUT["mapping"] = rows

V.hdr("2. THE BRACKET THE RECORD SUPPORTS -- a range, because there is no intermediate build")
g_pres = rows["V74/r5d"]["rel"]["e_18-22"]
g_gone = rows["V75/r5e"]["rel"]["e_18-22"]
gd_pres = rows["V74/r5d"]["duty"]["e_18-22"]
gd_gone = rows["V75/r5e"]["duty"]["e_18-22"]
print(f"  GRIND #1, the only band with a 'perceptible -> imperceptible' transition in the record:")
print(f"     still perceptible at   relative excess {g_pres:.2f}   /   creep duty {gd_pres:.3f}   "
      f"(V74)")
print(f"     imperceptible at       relative excess {g_gone:.2f}   /   creep duty {gd_gone:.3f}   "
      f"(V75)")
print(f"  ⇒ the threshold lies SOMEWHERE inside a {g_pres / g_gone:.2f}x window on the amplitude "
      f"axis and a {gd_pres / max(gd_gone, 1e-9):.0f}x window on the duty axis.")
print(f"     🛑 That is the whole resolution the record has. No build sits between them.")
print(f"\n  MICRO RATCHET: no build has ever been reported GONE, so its threshold is bounded from")
print(f"  ABOVE only -- it is below V75's {rows['V75/r5e']['rel']['e_6-9']:.2f} relative / "
      f"{rows['V75/r5e']['duty']['e_6-9']:.3f} duty ('barely still existing') and nothing more can")
print(f"  be said from the record alone.")
OUT["bracket"] = dict(grind_perceptible_rel=g_pres, grind_gone_rel=g_gone,
                      grind_perceptible_duty=gd_pres, grind_gone_duty=gd_gone,
                      ratchet_now_rel=rows["V75/r5e"]["rel"]["e_6-9"],
                      ratchet_now_duty=rows["V75/r5e"]["duty"]["e_6-9"])

# ================================================== 3. THE HEADLINE ==============================
V.hdr("3. ★★ HOW MUCH FURTHER -- the paired, route-cancelling estimate")
print("  R = median(6-9/ctl) / median(18-22/ctl) on V75's OWN windows. Under the stated assumption")
print("  (same numerical threshold at both frequencies) R IS the required further attenuation.\n")
hd = {}
for lab, kw in (("engaged, 0.5-12.5 m/s", dict()), ("engaged CREEP 0.5-4", dict(vhi=4.0)),
                ("engaged 9.4-12.5 clean", dict(vlo=9.4, vhi=12.5))):
    o, lo, hi, ne = paired_R(sub("V75/r5e", **kw))
    db = 20 * np.log10(o) if np.isfinite(o) else np.nan
    dlo, dhi = 20 * np.log10(lo), 20 * np.log10(hi)
    hd[lab] = dict(R=o, lo=lo, hi=hi, dB=db, dB_lo=dlo, dB_hi=dhi, ep=ne)
    print(f"  {lab:<24} R = {o:5.2f} [{lo:5.2f}, {hi:5.2f}]  ⇒ "
          f"{db:5.2f} dB [{dlo:5.2f}, {dhi:5.2f}]   {ne} episodes")
print("\n  the same statistic on the previous builds, for scale (this is a WITHIN-build number, so")
print("  it is comparable across routes without any matching):")
for b, k in LAD[:-1]:
    o, lo, hi, ne = paired_R(sub(b))
    print(f"  {b:<24} R = {o:5.2f} [{lo:5.2f}, {hi:5.2f}]  ⇒ "
          f"{20 * np.log10(o):5.2f} dB   {ne} episodes")
OUT["headline"] = hd

print("\n  DUTY-AXIS version of the same question (engaged creep, grind-active regime):")
dr = duty("V75/r5e", "e_6-9")
dg = duty("V75/r5e", "e_18-22")
print(f"     ratchet duty {dr[0]:.3f} [{dr[1]:.3f}, {dr[2]:.3f}]   target (V75's own grind #1) "
      f"{dg[0]:.3f} [{dg[1]:.3f}, {dg[2]:.3f}]")
if dg[0] > 0:
    print(f"     ⇒ required further reduction in duty {dr[0] / dg[0]:.1f}x = "
          f"{20 * np.log10(dr[0] / dg[0]):.1f} dB-equivalent")
    print(f"     🛑 duty is a FRACTION and its CI reaches 0 on both bands at this exposure "
          f"(6 blocks), so this figure is INDICATIVE ONLY.")
OUT["duty_axis"] = dict(ratchet=list(dr), target=list(dg))

V.hdr("4. WHAT THIS CANNOT SUPPORT -- read this before using any number above")
for line in [
    "· n = 1 route for V75, 6 engagement episodes, 182.3 s engaged, TRUNCATED at the fault.",
    "· The perceptual threshold is NOT measured. It is bracketed by two builds and the bracket is",
    "  2.0x wide on the amplitude axis and ~15x wide on the duty axis.",
    "· Equating the threshold at 7.8 Hz with the threshold at 21 Hz is an ASSUMPTION. The operator's",
    "  own words distinguish them (one audible, one not), so it is probably wrong in some direction.",
    "· The dB figure is a RATIO OF BAND ENVELOPES on the torsion bar, not a sound-pressure or",
    "  acceleration level. It is not a psychoacoustic quantity and must not be read as one.",
    "· `duty` bottoms out: V75's grind-#1 duty is 1 window in 29, so its CI includes 0 and every",
    "  ratio taken against it is unstable.",
]:
    print("  " + line)

with open(ROOT / "_v78_perception.json", "w", encoding="utf-8") as fh:
    json.dump(OUT, fh, indent=1, default=float)
print("\nwrote _v78_perception.json")
