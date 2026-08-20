#!/usr/bin/env python3
r"""ADJUDICATING THE TENSION: is the ~23 Hz line UPSTREAM or DOWNSTREAM of the aggregator?

🛑 A CORRECTION TO MY OWN EARLIER PASS.  I tested `x6b94` at 17-20 Hz on the belief that 0x1AB
samples gp-0x6b94 at 41.7 Hz, so a 23 Hz component would FOLD to 18.7 Hz.  It does not.  Measured
from the caches: r85 **49.794 Hz**, r95 **49.784 Hz** => NYQUIST 24.9 Hz.  **23 Hz is BELOW Nyquist
and is directly observable in `x6b94`.**  The right band is 21-24 Hz, and that is what is tested
here.  ZOH costs |sinc(23/49.79)| = 0.684 of amplitude, but it is a COMMON factor on both routes so
the RATIO is unaffected.

A  x6b94 at 21-24 Hz, matched (speed x wheel-rate) cells -- is the line in the firmware's OWN demand?
B  Sign-bit toggle rates, using ONLY the bits that mean the same thing on both builds.
   🛑 V100 b5 = |gp-0x6ad6| >= 8192 (a THRESHOLD); V101 b5 = gp-0x6b4c < 0 (a SIGN).  NOT COMPARABLE.
      The comparable pair is b7 (gp-0x6b94 < 0) and b4 (gp-0x6ad6 < 0), identical on both.
C  The quantisation-artefact test.  b7 and mag427 are the SIGN and the MAGNITUDE OF THE SAME CELL,
   so P(toggle | |x|) is directly measurable -- and V101's toggle rate can be RE-WEIGHTED onto
   V100's magnitude distribution.  If the excess dies under re-weighting it is a near-zero artefact.
"""
import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import v102_xb_lib as L  # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

NFFT, HOP = 256, 128
VB = [(5, 20), (20, 35), (35, 50), (50, 65)]
RB = [(1, 8), (8, 20), (20, 45), (45, 120)]
win = np.hanning(NFFT)


def hdr(s):
    print("\n" + "=" * 104)
    print(s)
    print("=" * 104)


W = {r: L.sel(L.windows(r, NFFT, HOP, engaged=True, keep_raw=True), vlo=5, vhi=65)
     for r in ("85", "95")}
XB = {"18-21": (18.0, 21.0), "21-24": (21.0, 24.0), "15-18": (15.0, 18.0),
      "10-15": (10.0, 15.0), "3-5": (3.0, 5.0)}
for r in ("85", "95"):
    for x in W[r]:
        b, s = x["_blk"], x["_sl"]
        for nm, (lo, hi) in XB.items():
            x["xb|" + nm] = L.bandrms(b["x6b94"][s], L.FS, lo, hi, win)
        for nm in XB:
            if x["xb|15-18"] > 0:
                x["xbs|" + nm] = x["xb|" + nm] / x["xb|15-18"]
CELLS = []
for vlo, vhi in VB:
    for rlo, rhi in RB:
        a = L.sel(W["85"], vlo=vlo, vhi=vhi, rlo=rlo, rhi=rhi)
        b = L.sel(W["95"], vlo=vlo, vhi=vhi, rlo=rlo, rhi=rhi)
        if len(a) >= 5 and len(b) >= 5:
            CELLS.append((a, b))
print("matched cells: %d  (V100 win=%d, V101 win=%d)"
      % (len(CELLS), sum(len(a) for a, _ in CELLS), sum(len(b) for _, b in CELLS)))


def ratio(key, nboot=3000, seed=11):
    rng = np.random.default_rng(seed)
    P = []
    for a, b in CELLS:
        ga, gb = {}, {}
        for r in a:
            v = r.get(key, np.nan)
            if np.isfinite(v) and v > 0:
                ga.setdefault((r["seg"], int(r["t0"] // 15.0)), []).append(v)
        for r in b:
            v = r.get(key, np.nan)
            if np.isfinite(v) and v > 0:
                gb.setdefault((r["seg"], int(r["t0"] // 15.0)), []).append(v)
        if len(ga) >= 2 and len(gb) >= 2:
            P.append(([np.array(v) for v in ga.values()], [np.array(v) for v in gb.values()]))
    if not P:
        return None

    def stat(Q):
        num = den = 0.0
        for A, B in Q:
            va, vb = np.concatenate(A), np.concatenate(B)
            w = min(len(va), len(vb))
            num += w * np.log(np.median(vb) / np.median(va))
            den += w
        return float(np.exp(num / den)) if den else np.nan
    pt = stat(P)
    out = [stat([([A[j] for j in rng.integers(0, len(A), len(A))],
                  [B[j] for j in rng.integers(0, len(B), len(B))]) for A, B in P])
           for _ in range(nboot)]
    out = np.array([o for o in out if np.isfinite(o)])
    lo, hi = np.percentile(out, [2.5, 97.5])
    return dict(r=pt, lo=float(lo), hi=float(hi))


hdr("A -- IS THE LINE IN gp-0x6b94, THE FIRMWARE'S OWN AGGREGATOR OUTPUT?  (Nyquist 24.9 Hz)")
print("   %-10s %24s %24s" % ("band", "V101/V100 band RMS", "SHAPE (band / 15-18 Hz)"))
for nm in ("3-5", "10-15", "15-18", "18-21", "21-24"):
    a = ratio("xb|" + nm)
    b = ratio("xbs|" + nm, seed=13)
    star = "  <== the line's band" if nm == "21-24" else ("  (shape denominator)" if nm == "15-18" else "")
    print("   %-10s %10.2f x [%4.2f, %5.2f] %12.2f x [%4.2f, %5.2f]%s"
          % (nm, a["r"], a["lo"], a["hi"], b["r"], b["lo"], b["hi"], star))
print("""
   For reference, the SAME estimator on the BUS channels put 22-26 Hz at 7.1x with a shape ratio of
   3.0x, against a broadband dose of ~2.2x.""")

hdr("B -- SIGN-BIT TOGGLE RATES, using only the bits that mean the same thing on both builds")
print("""   🛑 V100 byte4 map: b7 = gp-0x6b94<0 · b6 = |gp-0x4f60-gp-0x6ad6|>=10240 · b5 = |gp-0x6ad6|>=8192
      V101 byte4 map: b7 = gp-0x6b94<0 · b6 = |gp-0x6b4c|>=4096      · b5 = gp-0x6b4c<0
   ⇒ b5 is a THRESHOLD on V100 and a SIGN on V101.  A b5-to-b5 toggle-rate comparison across these
     two routes compares two different quantities and means nothing.  Only b7 and b4 are shared.""")
RAW = {}
for route in ("85", "95"):
    acc = {}
    bits = L.ROUTES[route]["bits"]
    for s in L.ROUTES[route]["segs"]:
        d = L.load_seg(route, s)
        n = len(d["t"])
        for k in ("t", "cc_lat", "v_rear", "rate_c", "cs_tq", "e4tq",
                  bits + "_b7", bits + "_b4", "mag427", "x6b94"):
            acc.setdefault(k.replace(bits, "b"), []).append(d[k])
        acc.setdefault("seg", []).append(np.full(n, s, float))
    d = {k: np.concatenate(v) for k, v in acc.items()}
    d["eng"] = d["cc_lat"] > 0.5
    d["v"] = d["v_rear"] * 3.6
    RAW[route] = d


def toggles(d, m):
    """Transitions per second inside the mask, never across a mask break or a segment seam."""
    out = {}
    for bit in ("b_b7", "b_b4"):
        x = (d[bit] > 0.5).astype(int)
        ok = m[1:] & m[:-1] & (np.diff(d["seg"]) == 0)
        out[bit] = float((np.diff(x)[ok] != 0).sum()) / (ok.sum() / L.FS)
    return out


print("\n   %-12s %-22s %14s %14s" % ("speed", "route", "b7 sign toggles/s", "b4 sign toggles/s"))
for vlo, vhi in ((5, 20), (20, 35), (35, 65), (5, 65)):
    for route in ("85", "95"):
        d = RAW[route]
        m = d["eng"] & (d["v"] >= vlo) & (d["v"] < vhi)
        if m.sum() < 200:
            continue
        t = toggles(d, m)
        print("   %-12s r%s %-19s %14.2f %14.2f"
              % ("%d-%d km/h" % (vlo, vhi), route, L.ROUTES[route]["build"] + " (%.0f s)" % (m.sum() / L.FS),
                 t["b_b7"], t["b_b4"]))

hdr("C -- THE QUANTISATION-ARTEFACT TEST.  P(toggle | |gp-0x6b94|), same cell, sign AND magnitude")
print("   A sign bit on a near-zero signal toggles on noise.  b7 and mag427 are the SIGN and the")
print("   MAGNITUDE OF THE SAME CELL, so the dependence is directly measurable.")
BINS = [0, 1, 2, 4, 8, 16, 32, 64, 128, 10000]
prof = {}
for route in ("85", "95"):
    d = RAW[route]
    m = d["eng"] & (d["v"] >= 5) & (d["v"] < 65)
    x = (d["b_b7"] > 0.5).astype(int)
    tog = np.zeros(len(x), bool)
    tog[1:] = np.diff(x) != 0
    ok = m.copy()
    ok[1:] &= m[:-1] & (np.diff(d["seg"]) == 0)
    mag = d["mag427"]
    row, wts = [], []
    for lo, hi in zip(BINS[:-1], BINS[1:]):
        sel = ok & (mag >= lo) & (mag < hi)
        row.append(float(tog[sel].mean()) * L.FS if sel.sum() > 30 else np.nan)
        wts.append(float(sel.sum()))
    prof[route] = (np.array(row), np.array(wts) / max(np.sum(wts), 1))
    print("   r%s %-5s  P(toggle)/s by |wire code|: %s"
          % (route, L.ROUTES[route]["build"],
             "  ".join("%d-%d:%s" % (lo, hi if hi < 10000 else 999,
                                     "%.1f" % v if np.isfinite(v) else "  -")
                       for (lo, hi), v in zip(zip(BINS[:-1], BINS[1:]), row))))
    print("        magnitude mix:                %s"
          % "  ".join("%d-%d:%.3f" % (lo, hi if hi < 10000 else 999, w)
                      for (lo, hi), w in zip(zip(BINS[:-1], BINS[1:]), prof[route][1])))
ra, wa = prof["85"]
rb, wb = prof["95"]
ok = np.isfinite(ra) & np.isfinite(rb)
raw85 = float(np.nansum(ra[ok] * wa[ok]) / wa[ok].sum())
raw95 = float(np.nansum(rb[ok] * wb[ok]) / wb[ok].sum())
adj95 = float(np.nansum(rb[ok] * wa[ok]) / wa[ok].sum())     # V101 rates on V100's magnitude mix
print("""
   V100 observed  %.2f toggles/s
   V101 observed  %.2f toggles/s          -> raw excess %.2f x
   V101 RE-WEIGHTED onto V100's magnitude distribution: %.2f toggles/s -> excess %.2f x
   If the re-weighted excess collapses toward 1.0, the extra toggling is the near-zero artefact.
   If it survives, the sign really is reversing more often at the same signal size."""
      % (raw85, raw95, raw95 / raw85, adj95, adj95 / raw85))

print("\n[done]")
