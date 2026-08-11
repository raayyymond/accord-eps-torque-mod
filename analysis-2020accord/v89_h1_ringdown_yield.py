#!/usr/bin/env python3
"""v89_h1_ringdown_yield.py -- how many usable ring-down edges exist in the WHOLE corpus?

YIELD FIRST, FIT LATER.  The M2 test (zeta falling with pre-ring command magnitude) needs enough
edges to support at least two command bins.  Recorded power: sd(log zeta) ~ 0.64 (400 ct creep) /
0.78 (250 ct) / 1.08 (90 ct highway) => +-50% needs 10 / 15 / 28 edges.  Route 73 alone gave
1 usable edge from 5.  This enumerates every cache before anything is fitted.

CRITERIA -- taken verbatim from `_cache_r73/v88_d7_ringdown_speed.py`, with the orchestrator's
tightened hold times:
  * latActive falling edge, >= 5.0 s engaged before, >= 5.0 s manual after   (d7 used 3.0/4.0)
  * not within the pre/post window of a segment boundary
  * pre-edge 6-9 Hz envelope > 1.2x the post-edge floor (i.e. the ratchet WAS running)
  * `ringdown_zeta` returns finite and > 0 (a growing envelope means re-excitation)
  * DISENGAGE CAUSE: not by grabbing the wheel (`cs_press`) and not by braking (`cs_brake`)
  * DAMPER SCREEN: FactorC m26 Y[0] != 0 marks the engaged-only creep damper, which is OURS and
    was armed V74..V86B.  Those routes are EXCLUDED -- they do not pool with stock-damper builds.
    Read from each build's own image, not from a table.
  * WHEEL-ORDER-CLEAN speed bands for 6-9 Hz: 1.8-3.6, 33.8-44.6, 67.7+ km/h.  Reported but NOT
    applied as a hard screen, so the cost of applying it is visible.
"""
from __future__ import annotations
import json
import struct
import sys
from pathlib import Path

import numpy as np
from scipy.signal import butter, filtfilt, hilbert

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ROOT = Path(__file__).resolve().parent.parent
FWD = Path(r"C:/Users/dudei/Desktop/Projects/accord-firmwares/analysis-2020accord")
OUT = ROOT / "_cache_r73" / "v89_h1_yield.json"

EDGE_PRE, EDGE_POST = 5.0, 5.0
FACTOR_C_PTRS = 0xC9E9C
ORDER_CLEAN_KPH = [(1.8, 3.6), (33.8, 44.6), (67.7, 999.0)]

ROUTE_BUILD = {
    "r28": "v57", "r29": "v57", "r2b": "v58", "r2c": "v59", "r31": "v59", "r35": "v64",
    "r37": "v62", "r3a": "v65", "r3b": "v65", "r47": "v67", "4c": "v68", "4e": "v68",
    "r4f": "v69", "r50": "v70", "r58": "v71c", "r59": "v72", "r5a": "v73", "r5d": "v74",
    "r5e": "v75", "r61": "v74", "r65": "v76", "r66": "v80", "r67": "v81", "r68": "v83a",
    "r6d": "v84", "r6e": "v85", "r6f": "v86", "r70": "v86b", "r71": "v87", "r73": "v88",
    "r75": "v89", "r76": "v89",
}


def damper_armed(tag):
    h = sorted(FWD.glob("_{}_plain_image.bin".format(tag))) or \
        sorted(FWD.glob("_{}_*_plain_image.bin".format(tag)))
    if not h:
        return None
    b = h[0].read_bytes()
    rec = struct.unpack_from("<I", b, FACTOR_C_PTRS + 26 * 4)[0]
    n = struct.unpack_from("<H", b, rec)[0]
    y0 = struct.unpack_from("<{}h".format(n), b, rec + 2 + 2 * n)[0]
    return bool(y0 != 0)


def ringdown_zeta(env, fs, f0, i0, fit_s=2.0, floor_from=2.5):
    """`v88_d6_dose_and_protocol.ringdown_zeta`, verbatim -- the only estimator in this kit's
    record that has passed its own control."""
    post = env[i0:]
    if len(post) < int((floor_from + 0.5) * fs):
        return np.nan
    floor = float(np.percentile(post[int(floor_from * fs):], 25))
    tt = np.arange(len(post)) / fs
    m = tt <= fit_s
    y = np.sqrt(np.clip(post[m] ** 2 - floor ** 2, 1e-9, None))
    if np.count_nonzero(y > 1e-4) < 20:
        return np.nan
    return -float(np.polyfit(tt[m], np.log(y), 1)[0]) / (2 * np.pi * f0)


def line_centre(x, fs):
    w = np.hanning(len(x))
    P = np.abs(np.fft.rfft((x - x.mean()) * w)) ** 2
    f = np.fft.rfftfreq(len(x), 1.0 / fs)
    m = (f >= 6.0) & (f < 9.0)
    return float(f[m][np.argmax(P[m])]) if m.any() else 7.79


def order_clean(kph):
    return any(a <= kph < b for a, b in ORDER_CLEAN_KPH)


def scan_route(rt, path, armed):
    z = np.load(path, allow_pickle=True)
    need = {"t", "tq", "cs_v", "cc_lat"}
    if not need <= set(z.files):
        return [], "missing columns"
    t = np.asarray(z["t"], float)
    n = len(t)
    seg = np.asarray(z["seg"], int) if "seg" in z.files else np.zeros(n, int)
    # per-segment fs; the whole-route figure is contaminated by dropouts
    fs = 100.0
    x = np.asarray(z["tq"], float)
    v = np.abs(np.asarray(z["cs_v"], float))
    lat = np.asarray(z["cc_lat"], float) > 0.5
    has_press = "cs_press" in z.files
    has_brake = "cs_brake" in z.files
    has_cmd = "sc_tq" in z.files
    pr = np.asarray(z["cs_press"], float) if has_press else np.zeros(n)
    br = np.asarray(z["cs_brake"], float) if has_brake else np.zeros(n)
    cmd = np.asarray(z["sc_tq"], float) if has_cmd else np.full(n, np.nan)
    npre, npost = int(EDGE_PRE * fs), int(EDGE_POST * fs)
    fe = np.flatnonzero(lat[:-1] & ~lat[1:])
    rows = []
    for i in fe:
        r = {"route": rt, "build": ROUTE_BUILD.get(rt, "?"), "t": float(t[i]),
             "v_kph": float(v[i] * 3.6), "armed": armed}
        why = []
        if i - npre < 0 or i + npost >= n:
            why.append("at route end")
        if not why and (seg[i - npre] != seg[i] or seg[min(i + npost, n - 1)] != seg[i]):
            why.append("crosses a segment boundary")
        j = i
        while j > 0 and lat[j]:
            j -= 1
        eb = (i - j) / fs
        k = i + 1
        while k < n - 1 and not lat[k]:
            k += 1
        ma = (k - i - 1) / fs
        r["eng_before"], r["man_after"] = float(eb), float(ma)
        if eb < EDGE_PRE:
            why.append("only {:.1f}s engaged before".format(eb))
        if ma < EDGE_POST:
            why.append("only {:.1f}s manual after".format(ma))
        if not why:
            sl = slice(i - npre, i + npost)
            if not np.isfinite(x[sl]).all():
                why.append("non-finite torque")
        if not why:
            pmean = float(np.mean(pr[i - int(0.5 * fs):i + int(1.0 * fs)]))
            bmean = float(np.mean(br[i - int(0.5 * fs):i + int(1.0 * fs)]))
            r["press"], r["brake"] = pmean, bmean
            if pmean > 0.05:
                why.append("disengaged by GRABBING the wheel (press {:.2f})".format(pmean))
            if has_brake and bmean > 0.05:
                why.append("disengaged by BRAKING (brake {:.2f})".format(bmean))
            if not has_brake:
                why.append("NO cs_brake channel -- disengage cause unverifiable")
            if not has_cmd:
                why.append("NO sc_tq channel -- the command magnitude CANNOT be binned")
        if not why:
            pre = x[i - npre:i]
            f0 = line_centre(pre, fs)
            bp = butter(2, [max(f0 - 1.5, 0.5), f0 + 1.5], btype="band", fs=fs)
            env = np.abs(hilbert(filtfilt(*bp, x[i - npre:i + npost])))
            pe = float(np.percentile(env[:npre], 75))
            post = env[npre:]
            fl = float(np.percentile(post[int(2.5 * fs):], 25))
            ratio = pe / max(fl, 1e-9)
            r.update({"f0": f0, "pre_env": pe, "floor": fl, "ratio": ratio})
            if ratio <= 1.2:
                why.append("pre-env only {:.2f}x floor -- the ratchet was NOT running".format(ratio))
            else:
                zz = ringdown_zeta(env, fs, f0, npre)
                r["zeta"] = float(zz) if np.isfinite(zz) else None
                if not (np.isfinite(zz) and zz > 0):
                    why.append("envelope GREW after the edge -- re-excited")
        if not why:
            c = cmd[i - npre:i]
            r["cmd_rms"] = float(np.sqrt(np.nanmean(c ** 2))) if np.isfinite(c).any() else None
            r["order_clean"] = order_clean(r["v_kph"])
        r["verdict"] = "USABLE" if not why else " ; ".join(why)
        rows.append(r)
    return rows, None


def main():
    # whole-route npz where it exists, otherwise the per-segment set -- the same rule as
    # v89_c1.collect(). Scanning only `_cache_<rt>/<rt>.npz` missed 18 of 30 routes on the
    # first run of this script.
    import re
    caches = {}
    for d in sorted(ROOT.glob("_cache_*")):
        if not d.is_dir():
            continue
        for f in sorted(d.glob("*.npz")):
            m = re.match(r"^(r?[0-9a-f]{2}[a-z]?)(?:s(\d+))?$", f.stem)
            if not m or m.group(1) not in ROUTE_BUILD:
                continue
            rk = m.group(1)
            caches.setdefault(rk, {"whole": [], "segs": []})
            (caches[rk]["whole"] if m.group(2) is None else caches[rk]["segs"]).append(f)
    caches = {k: (v["whole"][:1] if v["whole"] else v["segs"]) for k, v in caches.items()}
    armedmap = {}
    for rt in caches:
        b = ROUTE_BUILD[rt]
        if b not in armedmap:
            armedmap[b] = damper_armed(b)

    print("=" * 108)
    print("DAMPER SCREEN -- FactorC m26 Y[0] read from each build's own image")
    print("=" * 108)
    for b in sorted(armedmap):
        a = armedmap[b]
        print("  {:6s} {}".format(b, "ARMED -> EXCLUDE" if a else
                                  ("stock -> pool" if a is False else "NO IMAGE -> exclude")))

    print("\n" + "=" * 108)
    print("EDGE ENUMERATION -- every latActive falling edge in every cache")
    print("=" * 108)
    allrows, excluded = [], []
    for rt in sorted(caches):
        a = armedmap[ROUTE_BUILD[rt]]
        rows, err = [], None
        for f in caches[rt]:
            rr, e2 = scan_route(rt, f, a)
            rows.extend(rr)
            err = err or e2
        if err and not rows:
            print("  {:5s} {}".format(rt, err))
            continue
        us = [r for r in rows if r["verdict"] == "USABLE"]
        tag = "" if a is False else ("   [DAMPER ARMED -- excluded]" if a else "   [no image]")
        print("  {:5s} {:6s} {:2d} file(s) {:3d} edges -> {:2d} usable{}".format(
            rt, ROUTE_BUILD[rt], len(caches[rt]), len(rows), len(us), tag))
        (allrows if a is False else excluded).extend(rows)

    us = [r for r in allrows if r["verdict"] == "USABLE"]
    print("\n" + "=" * 108)
    print("YIELD")
    print("=" * 108)
    print("  poolable (stock damper) routes: {} edges -> {} USABLE".format(len(allrows), len(us)))
    print("  excluded (damper armed V74-V86B): {} edges -> {} would-be usable".format(
        len(excluded), len([r for r in excluded if r["verdict"] == "USABLE"])))
    if us:
        print("\n  the usable ones:")
        print("   {:6s} {:6s} {:>8s} {:>8s} {:>7s} {:>8s} {:>9s} {:>7s} {:>6s}".format(
            "route", "build", "t s", "v kph", "f0 Hz", "pre ct", "cmd rms", "zeta", "ordclean"))
        for r in us:
            print("   {:6s} {:6s} {:8.1f} {:8.1f} {:7.2f} {:8.0f} {:9.0f} {:7.4f} {:>6}".format(
                r["route"], r["build"], r["t"], r["v_kph"], r.get("f0", np.nan),
                r.get("pre_env", np.nan), r.get("cmd_rms") or np.nan, r.get("zeta") or np.nan,
                r.get("order_clean")))
        oc = [r for r in us if r.get("order_clean")]
        print("\n  after the wheel-order-clean speed screen (1.8-3.6 / 33.8-44.6 / 67.7+ km/h): "
              "{} of {}".format(len(oc), len(us)))
    print("\n  WHY THE REST FAILED (poolable routes only):")
    from collections import Counter
    c = Counter()
    for r in allrows:
        if r["verdict"] == "USABLE":
            continue
        for part in r["verdict"].split(" ; "):
            c[part.split("(")[0].split("--")[0].strip().rstrip("0123456789.s ")] += 1
    for k, n in c.most_common():
        print("    {:4d}  {}".format(n, k))

    OUT.write_text(json.dumps({"usable": us, "all": allrows, "excluded_n": len(excluded)},
                              indent=1, default=float))
    print("\nwrote {}".format(OUT))


if __name__ == "__main__":
    main()
