# -*- coding: utf-8 -*-
"""V292 FLIGHT READ -- deliverable 1: BUILD ATTRIBUTION FROM THE 0x14A BYTE-4 TAP, every segment of the
three routes flown 2026-09-13, against the V282 reference route r6c.

*** ATTRIBUTE THE BUILD FROM THE TAP, NOT FROM THE LABEL *** (memory feedback-attribute-the-build-from-
the-tap-not-from-the-label).

V292's signature, from docs/review/ADVERSARIAL-V292-PREREG-2026-09-13.md "The read, as amended by A2":
  b3 = sign(fb state gp-0x3d30)  -> DUTY 0.47-0.50 engaged, conditioned on |rate| >= 2 counts and
       mean rate <= ~1.5 deg/s;  **0.000 at rest with the wheel still** (the cave-live control).
  V282's b3 is an aliased bit that reads ~0.43-0.47 in BOTH states (r6c measured 0.468 engaged /
  0.429 SCA=0) -- so the DISCRIMINATOR IS THE IDLE READING, not the engaged one.
  b5 / b6 = the r24 comparators (V282 engaged ~0.13-0.23); V292's r24 arm cut 5244->4725 predicts ~-10 %.
  b7 = V282's three-sign rung (engaged ~0.56; 0.000 on SCA=0 more than 3 s after SCA fell).
  b0-2 = stock Honda, 1.000 on every build.

"Engaged" = LATERAL engaged = 0x18F b4.3 STEER_CONTROL_ACTIVE AND 0xE4 b2.7 STEER_REQUEST
(memory feedback-engaged-means-lateral-engaged-and-v276-is-not-a-reference).

Caches: analysis-2020accord/_scratch/cache/v280/{r6d_v292,r6e_v292,r6f_v292,r6c}.npz + _b4.npz, built by
rlog-tools/studies/grind/extract_v292_routes.py (r6c by the record's own extractor).
🛑 The dongle route counter RESET: the AUGUST r6d/r6e/r6f caches are DIFFERENT ROUTES. These tags carry
the _v292 suffix for exactly that reason.

ANALYSIS ONLY.  Run: python rlog-tools/studies/grind/v292_flight_attrib.py
"""
import io
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
CACHE = os.path.join(KIT, "analysis-2020accord", "_scratch", "cache", "v280")
SCR = os.path.join(HERE, "_scratch")
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

CPD = 8.0          # raw 0x18F rate counts per deg/s
ROUTES = [("r6d_v292", "75604b0a432fdc89_0000006d--5e7b4d2ceb", 18),
          ("r6e_v292", "75604b0a432fdc89_0000006e--64b4a5fef4", 23),
          ("r6f_v292", "75604b0a432fdc89_0000006f--d876c761bc", 13),
          ("r6c", "75604b0a432fdc89_0000006c--2bc842dbac", 62)]
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def load(tag):
    D = dict(np.load(os.path.join(CACHE, tag + ".npz")))
    B = dict(np.load(os.path.join(CACHE, tag + "_b4.npz")))
    M = json.load(open(os.path.join(CACHE, tag + "_marks.json")))
    return D, B, M


def seg_of(t, M):
    """map an absolute mono time onto its segment number using the marks file's per-segment spans.

    Two marks schemas exist.  The current extractor writes `lo_can_route` (the segment's first REAL CAN
    arrival) -- use it as the LEFT edge.  The older r39/r6c-era extractor wrote only `lo_route`, which is
    initData's process-start stamp and is IDENTICAL on every segment (a known defect, flagged in
    extract_r62_r63_v280cache.py's `lo_route_note`) -- for those, fall back to `hi_route`, which IS
    per-segment and monotonic, and treat it as the RIGHT edge.
    """
    t0 = M["t0_mono"]
    items = sorted(((int(k), v) for k, v in M["segs"].items()), key=lambda z: z[0])
    nums = np.asarray([k for k, _ in items])
    if "lo_can_route" in items[0][1]:
        edges = np.asarray([v["lo_can_route"] for _, v in items])
        idx = np.searchsorted(edges, t - t0, side="right") - 1
    else:
        edges = np.asarray([v["hi_route"] for _, v in items])
        idx = np.searchsorted(edges, t - t0, side="left")
    return nums[np.clip(idx, 0, len(nums) - 1)]


def analyse(tag, prefix, nseg_nominal):
    D, B, M = load(tag)
    t18, sca, rate = D["t18"], D["sca"].astype(float), D["rate"].astype(float)
    te4, req = D["te4"], D["req"].astype(float)
    t14b, b4 = B["t14b"], B["b4"].astype(int)

    # engaged-lateral on the 0x14A axis
    sca14 = np.interp(t14b, t18, sca) > 0.5
    req14 = np.interp(t14b, te4, req) > 0.5
    eng14 = sca14 & req14
    rate14 = np.interp(t14b, t18, rate)              # raw counts
    BIT = {n: (b4 >> n) & 1 for n in range(8)}
    seg14 = seg_of(t14b, M)

    # the record's conditioning for the b3 read: |rate| >= 2 counts, and a LOW-mean-rate context
    # (mean |rate| over a +-0.5 s window <= 1.5 deg/s = 12 counts)  [prereg "The read, as amended by A2"]
    k = 50
    absr = np.abs(rate14)
    ker = np.ones(2 * k + 1) / (2 * k + 1)
    mean_absr = np.convolve(absr, ker, mode="same")
    creepish = mean_absr <= 1.5 * CPD
    moving = absr >= 2.0

    # "at rest with the wheel still" -- the CAVE-LIVE CONTROL.  Vehicle stationary AND the wheel still.
    vego14 = np.interp(t14b, D["tcs"], D["vego"].astype(float))
    still = (mean_absr < 1.0) & (absr < 1.0) & (vego14 < 0.3)

    present = M.get("present_segments") or sorted(int(k) for k in M["segs"])
    res = dict(tag=tag, route=prefix, nseg_on_disk=len(present),
               nseg_nominal=nseg_nominal,
               missing=M.get("missing_segments", [i for i in range(nseg_nominal) if i not in present]),
               route_len_s=float(t18[-1] - t18[0]))

    dt = np.clip(np.diff(t18, prepend=t18[0]), 0, 0.05)
    eng18 = (sca > 0.5) & (np.interp(t18, te4, req) > 0.5)
    res["engaged_s"] = float(dt[eng18].sum())

    def duty(mask, n):
        m = mask
        return (float(BIT[n][m].mean()) if m.sum() else float("nan"), int(m.sum()))

    res["pooled"] = {}
    for label, mask in (("engaged", eng14),
                        ("engaged & |rate|>=2 & creep", eng14 & moving & creepish),
                        ("SCA=0", ~sca14),
                        ("IDLE: v<0.3 m/s & wheel still", still)):
        res["pooled"][label] = {("b%d" % n): duty(mask, n) for n in range(8)}

    # per-segment
    res["per_seg"] = {}
    for s in sorted(set(seg14.tolist())):
        m = seg14 == s
        e = m & eng14
        ec = m & eng14 & moving & creepish
        i = m & still
        res["per_seg"][int(s)] = dict(
            n_eng=int(e.sum()), n_engcreep=int(ec.sum()), n_idle=int(i.sum()),
            eng={("b%d" % n): (float(BIT[n][e].mean()) if e.sum() else float("nan")) for n in range(8)},
            engcreep={("b%d" % n): (float(BIT[n][ec].mean()) if ec.sum() else float("nan")) for n in range(8)},
            idle={("b%d" % n): (float(BIT[n][i].mean()) if i.sum() else float("nan")) for n in range(8)})

    # b7 by time since SCA fell (the V282 signature: -> 0.000 beyond 3 s)
    d = np.diff(np.r_[0, sca14.astype(int)])
    falls = np.flatnonzero(d == -1)
    since = np.full(len(t14b), np.inf)
    if falls.size:
        j = np.searchsorted(falls, np.arange(len(t14b)), side="right") - 1
        ok = j >= 0
        since[ok] = t14b[ok] - t14b[falls[j[ok]]]
    res["b7_since_fall"] = {}
    for a, b in ((0, 0.2), (0.2, 1.0), (1.0, 3.0), (3.0, 1e9)):
        m = (~sca14) & (since >= a) & (since < b)
        res["b7_since_fall"]["%g-%g" % (a, b)] = (float(BIT[7][m].mean()) if m.sum() else float("nan"), int(m.sum()))

    # b3 duty vs |rate| amplitude bucket (the A2 read: V292 0.47-0.50 at EVERY amplitude;
    #  V291 pinned 1.000 below A=3; V282-pole 0.54-0.70)
    res["b3_by_amp"] = {}
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 5), (5, 8), (8, 16), (16, 32), (32, 1e9)):
        m = eng14 & (absr >= lo) & (absr < hi)
        res["b3_by_amp"]["%g-%g" % (lo, hi)] = (float(BIT[3][m].mean()) if m.sum() > 20 else float("nan"), int(m.sum()))
    res["b3_by_amp_idlectx"] = {}
    for lo, hi in ((0, 1), (1, 2), (2, 3), (3, 5), (5, 8), (8, 16), (16, 1e9)):
        m = (~sca14) & (absr >= lo) & (absr < hi) & (vego14 < 0.3)
        res["b3_by_amp_idlectx"]["%g-%g" % (lo, hi)] = (float(BIT[3][m].mean()) if m.sum() > 20 else float("nan"), int(m.sum()))

    # b3 toggle rate: a live sign bit on a filter state toggles fast; an aliased bit does not
    res["b3_toggle_hz"] = {}
    for label, mask in (("engaged", eng14), ("IDLE still", still)):
        if mask.sum() > 50:
            bb = BIT[3][mask]
            res["b3_toggle_hz"][label] = float(np.mean(np.diff(bb) != 0) * 100.0)
        else:
            res["b3_toggle_hz"][label] = float("nan")
    return res


def main():
    pr("V292 FLIGHT READ -- DELIVERABLE 1: BUILD ATTRIBUTION FROM THE 0x14A BYTE-4 TAP")
    pr("=" * 118)
    pr("Rule: attribute the build FROM THE TAP, not from the label.  Engaged = LATERAL engaged")
    pr("      (0x18F STEER_CONTROL_ACTIVE AND 0xE4 STEER_REQUEST).")
    pr("V292 signature (prereg, as amended by adversary A2): b3 = sign(fb state) -> DUTY 0.47-0.50 at")
    pr("      EVERY amplitude, and 0.000 at rest with the wheel still.  V282's b3 is an aliased bit:")
    pr("      ~0.43-0.47 in BOTH states.  b5/b6 = r24 comparators; V292's r24 cut predicts ~-10 %.")
    pr("      b7 = V282's three-sign rung (engaged ~0.56, -> 0.000 beyond 3 s after SCA falls).")
    pr("")
    allr = {}
    for tag, prefix, nseg in ROUTES:
        r = analyse(tag, prefix, nseg)
        allr[tag] = r
        pr("=" * 118)
        pr("%-10s  %s   %d/%d segments   %.0f s route   %.0f s engaged-lateral" %
           (tag, prefix, r["nseg_on_disk"], r["nseg_nominal"], r["route_len_s"], r["engaged_s"]))
        if r["missing"]:
            pr("   *** MISSING SEGMENTS: %s ***" % r["missing"])
        pr("")
        pr("  POOLED DUTY")
        pr("  %-34s %s      n" % ("stratum", "  ".join("b%d   " % n for n in range(7, -1, -1))))
        for label, dd in r["pooled"].items():
            vals = "  ".join("%.3f" % dd["b%d" % n][0] for n in range(7, -1, -1))
            pr("  %-34s %s   %7d" % (label, vals, dd["b7"][1]))
        pr("")
        pr("  b7 by time since SCA fell : " + " | ".join(
            "%s s %.3f (n=%d)" % (k, v[0], v[1]) for k, v in r["b7_since_fall"].items()))
        pr("  b3 by |rate| bucket (counts), ENGAGED : " + " | ".join(
            "%s:%.3f(n=%d)" % (k, v[0], v[1]) for k, v in r["b3_by_amp"].items()))
        pr("  b3 by |rate| bucket, STATIONARY (v<0.3) : " + " | ".join(
            "%s:%.3f(n=%d)" % (k, v[0], v[1]) for k, v in r["b3_by_amp_idlectx"].items()))
        pr("  b3 toggle rate : " + " | ".join("%s %.1f/s" % (k, v) for k, v in r["b3_toggle_hz"].items()))
        pr("")
        pr("  PER SEGMENT (engaged duty; then the conditioned b3; then the idle b3)")
        pr("  %-5s %7s  %s | %-9s | %-9s" % ("seg", "n_eng", "  ".join("b%d  " % n for n in range(7, -1, -1)),
                                             "b3 cond", "b3 idle"))
        for s in sorted(r["per_seg"]):
            v = r["per_seg"][s]
            if v["n_eng"] < 50:
                pr("  %-5d %7d  (under 50 engaged 0x14A frames -- not scored)" % (s, v["n_eng"]))
                continue
            pr("  %-5d %7d  %s | %.3f n%-5d | %s n%-5d" % (
                s, v["n_eng"], "  ".join("%.3f" % v["eng"]["b%d" % n] for n in range(7, -1, -1)),
                v["engcreep"]["b3"], v["n_engcreep"],
                ("%.3f" % v["idle"]["b3"]) if v["n_idle"] >= 20 else " n/a ", v["n_idle"]))
    # ---- verdict table ----
    pr("")
    pr("=" * 118)
    pr("VERDICT TABLE -- the three new routes against the r6c V282 reference (same decode, same masks)")
    pr("=" * 118)
    pr("%-12s %-9s %-9s %-9s %-9s %-9s %-9s" % ("route", "b3 eng", "b3 cond", "b3 IDLE", "b5 eng", "b6 eng", "b7 eng"))
    for tag, _, _ in ROUTES:
        r = allr[tag]
        P = r["pooled"]
        pr("%-12s %-9.3f %-9.3f %-9s %-9.3f %-9.3f %-9.3f" % (
            tag, P["engaged"]["b3"][0], P["engaged & |rate|>=2 & creep"]["b3"][0],
            ("%.3f" % P["IDLE: v<0.3 m/s & wheel still"]["b3"][0]) if P["IDLE: v<0.3 m/s & wheel still"]["b3"][1] >= 20 else "n/a",
            P["engaged"]["b5"][0], P["engaged"]["b6"][0], P["engaged"]["b7"][0]))
    with open(os.path.join(SCR, "v292_flight_attrib.json"), "w") as fh:
        json.dump(allr, fh, indent=1, default=float)
    io.open(os.path.join(SCR, "v292_flight_attrib.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("\nwrote v292_flight_attrib.{txt,json}")


if __name__ == "__main__":
    main()
