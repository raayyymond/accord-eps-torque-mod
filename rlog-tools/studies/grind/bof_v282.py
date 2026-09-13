# -*- coding: utf-8 -*-
"""studies/grind/bof_v282.py -- IDENTIFY B(f), the torsion-bar torque per unit of wheel rate, 3-30 Hz,
on the two V282 routes (r39, r6c), so the r24 base-assist rate lane's transfer

    R_r24(f) = -(0xC6446/1024) * D4(f) * B(f),   D4(f) = 0.5*(1 - exp(-j*2*pi*f*0.004))

can be evaluated at any frequency.  B(f) is the only piece of that product that is not exact integer
arithmetic already known from the bytes.

Subagent `bof`, 2026-09-13.  ANALYSIS ONLY: builds nothing, flashes nothing, sends nothing on any bus.

SIGN CONVENTION -- stated once, used everywhere, positively controlled in section 0.
  bar  = 0x18F bytes 0-1 as decoded by cache/v280, x 1.024 (raw counts)
  rate = 0x18F bytes 2-3 as decoded by cache/v280, raw counts (8 per deg/s)
  Both internal cells (gp-0x4f60 = -bar, gp-0x6a56 = -rate) are negated by the SAME frame builder, so
        B := bar/rate   is IDENTICAL in wire and internal sign -- the ratio is convention-free.
  That is the number the record quotes as "+114 deg, coherence 0.94 at 20 Hz creep"
  (docs/research/GRINDING-DEEP-ANALYSIS-2026-09-03.md headline 3); section 0 reproduces it.
  With that B, ang(R_r24) = 180 + ang(D4) + ang(B) is the phase of the CELL gp-0x6ada referred to
  x = -rate (the internal rate) -- verified against the cave's bit 4 in section 3b.

  *** THE 180 TRAP, RE-CONFIRMED HERE ***  cache/v280 decodes 0x18F's torque and rate with the OPPOSITE
  sign to _scratch/r24sign_*.npz (recorded in V282-R24-TAP-READ-r36-r38-2026-09-03.md sec 0.5).  So
  r24_series(g["bar"], gain) applied to THIS cache returns the cell NEGATED.  B is immune (both flip);
  the closed-form SIGN is not.  s4cf below therefore carries the explicit extra negation, and the
  timing control ang(tf(s4cf -> s4)) then reads ~0, not ~180.

Inputs: analysis-2020accord/_scratch/cache/v280/{r31,r32,r33,r34,r39,r6c}.npz and {r39,r6c}_b4.npz.
  r6c.npz / r6c_b4.npz were built this session by _scratch/extract_r6c_v280cache.py (a verbatim copy of
  extract_r39_v280cache.py with the prefix changed); everything else pre-existed.
Run: python bof_v282.py       (writes _scratch/bof_v282.txt and _scratch/bof_v282.json)
"""
import json
import os
import sys

import numpy as np
from scipy import optimize, signal

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                              # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG                # noqa: E402
from v282_r24_tap_read import read_cells, demand_live, r24_series   # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS = 100.0
CACHE = C20.CACHE
V282_IMG = (LG.FW + "_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-"
                    "MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
V280R2_IMG = LG.FW + LG.IMAGES["V280r2"]
CTRL_ROUTES = ("r31", "r32", "r33", "r34")
V282_ROUTES = ("r39", "r6c")
FREQS = [3.0, 3.9, 5.0, 6.0, 7.3, 8.0, 10.0, 12.0, 14.0, 16.0, 18.0, 20.3, 22.0, 25.0, 30.0]
COH_MIN = 0.40
HALF = 0.40                                   # band-average half width, Hz
NPS, NFFT = 128, 512                          # PRIMARY: 1.28 s windows, spectra interpolated to 0.195 Hz
NPS2, NFFT2 = 256, 1024                       # CROSS-CHECK: 2.56 s windows
GAIN_LADDER = [256.0, 512.0, 768.0, 1024.0, 1536.0, 2048.0, 2560.0, 3072.0, 4096.0, 5244.0, 6144.0, 8192.0]
OUT = []
J = {}


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def runmed(x, n):
    """centred running median, odd window n samples (used only for the selection-bias control strata)."""
    n = int(n) | 1
    pad = n // 2
    xp = np.r_[np.full(pad, x[0]), x, np.full(pad, x[-1])]
    return np.median(np.lib.stride_tricks.sliding_window_view(xp, n), axis=-1)


# ====================================================================================================== strata
STRATA = [
    ("creep_1_3",    "creep engaged hands-off  v 1-3, |bar|<400",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)),
    ("creep_1_6",    "creep engaged hands-off  v 1-6, |bar|<400",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 6.0) & (np.abs(g["bar"]) < 400)),
    ("creep_1_3med", "CONTROL creep hands-off v 1-3, 1 s MEDIAN |bar|<400 (no instantaneous gate)",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (g["barmed"] < 400)),
    ("creep_1_6med", "CONTROL creep hands-off v 1-6, 1 s MEDIAN |bar|<400",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 6.0) & (g["barmed"] < 400)),
    ("loaded_idx68", "loaded high-angle engaged  v 2-9, |ang|>30, idx>=68",
     lambda g: g["eng"] & (g["vego"] >= 2.0) & (g["vego"] < 9.0) & (np.abs(g["ang"]) > 30) & (g["idx"] >= 68)),
    ("loaded_idx68med", "CONTROL loaded v 2-9, |ang|>30, 1 s MEDIAN idx>=68",
     lambda g: g["eng"] & (g["vego"] >= 2.0) & (g["vego"] < 9.0) & (np.abs(g["ang"]) > 30) & (g["idxmed"] >= 68)),
    ("loaded_any",   "loaded high-angle engaged  v 2-9, |ang|>30 (any idx)",
     lambda g: g["eng"] & (g["vego"] >= 2.0) & (g["vego"] < 9.0) & (np.abs(g["ang"]) > 30)),
    ("highway",      "highway engaged  v > 15",
     lambda g: g["eng"] & (g["vego"] > 15.0)),
    ("all_eng",      "all engaged lateral",
     lambda g: g["eng"]),
]
MAIN = ("creep_1_3", "creep_1_6", "loaded_idx68", "loaded_any")


# ====================================================================================================== pooled spectra
class Pool:
    def __init__(self, fs, nps, nfft=None):
        self.fs, self.nps, self.nfft, self.f, self.S, self.n = fs, nps, nfft or nps, None, {}, 0

    def add(self, sigs):
        n = len(next(iter(sigs.values())))
        if n < self.nps:
            return 0
        nw = max(1, (n - self.nps // 2) // (self.nps // 2))
        keys = list(sigs)
        for i, a in enumerate(keys):
            for b in keys[i:]:
                f, P = signal.csd(sigs[a], sigs[b], fs=self.fs, nperseg=self.nps, nfft=self.nfft,
                                  detrend="constant")
                self.f = f
                self.S[(a, b)] = self.S.get((a, b), 0) + nw * P
        self.n += nw
        return nw

    def s(self, a, b):
        return self.S[(a, b)] / self.n if (a, b) in self.S else np.conj(self.S[(b, a)]) / self.n

    def coh(self, a, b):
        return np.abs(self.s(a, b)) ** 2 / (np.real(self.s(a, a)) * np.real(self.s(b, b)))

    def tf(self, u, y):
        return self.s(u, y) / np.real(self.s(u, u))

    def bavg(self, u, y, f0, half=HALF):
        """Band-averaged H1, coherence, bin count at f0 +- half.  Averaging SPECTRA (not ratios) is the
        unbiased estimator and keeps the coherence meaningful."""
        sel = np.abs(self.f - f0) <= half + 1e-9
        if sel.sum() == 0:
            sel = np.zeros(len(self.f), bool); sel[int(np.argmin(np.abs(self.f - f0)))] = True
        sxy, sxx, syy = self.s(u, y)[sel].sum(), np.real(self.s(u, u))[sel].sum(), np.real(self.s(y, y))[sel].sum()
        return sxy / sxx, float(np.abs(sxy) ** 2 / (sxx * syy)), int(np.sum(sel))

    def grid(self, u, y, flo=3.0, fhi=30.0):
        """H1, coherence on the native (interpolated) bin grid inside [flo,fhi]."""
        sel = (self.f >= flo) & (self.f <= fhi)
        return self.f[sel], self.tf(u, y)[sel], self.coh(u, y)[sel]


def pool_stratum(gs, tags, fn, keys, nps, nfft=None):
    P = Pool(FS, nps, nfft)
    secs = 0.0
    for t in tags:
        g = gs[t]
        m = fn(g)
        for a, b in C20.runs(m, nps):
            if P.add({k: g[k][a:b] for k in keys}):
                secs += (b - a) / FS
    return P, secs


# ====================================================================================================== the lane
def D4(f, N=4, fs1k=1000.0):
    return 0.5 * (1.0 - np.exp(-2j * np.pi * np.asarray(f, float) * N / fs1k))


def R_r24(Bv, f, gain=5244.0):
    """the CELL gp-0x6ada per unit of x = -rate (the internal rate)."""
    return -(gain / 1024.0) * D4(f) * Bv


# ====================================================================================================== load
def load(tag, cells):
    g = C20.load(tag)
    g["tr"] = g["t"] - g["t"][0]
    g["idx"], g["sgn"] = demand_live(np.round(g["cmd"]), g["bar"], cells)
    g["barmed"] = runmed(np.abs(g["bar"]), 101)
    g["idxmed"] = runmed(g["idx"], 101)
    p = os.path.join(CACHE, tag + "_b4.npz")
    if os.path.exists(p):
        B = np.load(p)
        k14, P14, tn14, res14 = C20.dejitter(B["t14b"], 0.01, 100)
        b4 = B["b4"].astype(int)
        g["b4_n"] = len(b4)
        g["b4_res"] = (float(np.percentile(res14, 50)), float(np.percentile(res14, 90)))
        for bit in (3, 4, 5, 6, 7):
            g["bit%d" % bit] = np.round(np.interp(g["t"], tn14, ((b4 >> bit) & 1).astype(float)))
            g["s%d" % bit] = 1.0 - 2.0 * g["bit%d" % bit]
    return g


# ====================================================================================================== parametric fit
# B(f) = A * exp(j phi0) * NUM(f) / DEN(f) * exp(-j 2 pi f tau),  f in Hz
#   families differ only in NUM and the extra factors; phi0 absorbs the overall sign.
def model(p, f, kind):
    f = np.asarray(f, float)
    if kind == "Z1":      # zero at the origin + one 2nd-order pole (+ delay)
        A, ph, fn, z, tau = p
        H = (1j * f) / (1 - (f / fn) ** 2 + 2j * z * (f / fn))
    elif kind == "Z1P":   # + one extra real pole
        A, ph, fn, z, fp, tau = p
        H = (1j * f) / ((1 - (f / fn) ** 2 + 2j * z * (f / fn)) * (1 + 1j * f / fp))
    elif kind == "Z1PZ":  # + one extra real pole and one extra real zero
        A, ph, fn, z, fp, fz, tau = p
        H = (1j * f) * (1 + 1j * f / fz) / ((1 - (f / fn) ** 2 + 2j * z * (f / fn)) * (1 + 1j * f / fp))
    elif kind == "Z1PP":  # + a SECOND 2nd-order pole pair
        A, ph, fn, z, f2, z2, tau = p
        H = (1j * f) / ((1 - (f / fn) ** 2 + 2j * z * (f / fn)) * (1 - (f / f2) ** 2 + 2j * z2 * (f / f2)))
    elif kind == "INT":   # the classical "spring" form: integrator * 2nd-order pole
        A, ph, fn, z, tau = p
        H = 1.0 / ((1j * f) * (1 - (f / fn) ** 2 + 2j * z * (f / fn)))
    else:
        raise ValueError(kind)
    return A * np.exp(1j * ph) * H * np.exp(-2j * np.pi * f * tau)


SPEC = {
    "Z1":    (("A", "phi0", "fn", "zeta", "tau"),
              [1.0, 0.0, 8.0, 0.25, 0.0], [1e-6, -np.pi, 4.0, 0.02, -0.005], [1e6, np.pi, 30.0, 3.0, 0.06]),
    "Z1P":   (("A", "phi0", "fn", "zeta", "fp", "tau"),
              [1.0, 0.0, 8.0, 0.25, 25.0, 0.0], [1e-6, -np.pi, 4.0, 0.02, 5.0, -0.005], [1e6, np.pi, 30.0, 3.0, 500.0, 0.06]),
    "Z1PZ":  (("A", "phi0", "fn", "zeta", "fp", "fz", "tau"),
              [1.0, 0.0, 8.0, 0.25, 25.0, 60.0, 0.0], [1e-6, -np.pi, 4.0, 0.02, 5.0, 5.0, -0.005],
              [1e6, np.pi, 30.0, 3.0, 500.0, 2000.0, 0.06]),
    "Z1PP":  (("A", "phi0", "fn", "zeta", "f2", "zeta2", "tau"),
              [1.0, 0.0, 8.0, 0.25, 20.0, 0.5, 0.0], [1e-6, -np.pi, 4.0, 0.02, 9.0, 0.02, -0.005],
              [1e6, np.pi, 30.0, 3.0, 120.0, 5.0, 0.06]),
    "INT":   (("A", "phi0", "fn", "zeta", "tau"),
              [1.0, 0.0, 8.0, 0.25, 0.0], [1e-6, -np.pi, 4.0, 0.02, -0.005], [1e6, np.pi, 30.0, 3.0, 0.06]),
}


def fit(f, Bm, w, kind):
    names, p0d, lo, hi = SPEC[kind]

    def res(p):
        Bp = model(p, f, kind)
        return np.concatenate([w * (np.log(np.abs(Bm)) - np.log(np.abs(Bp))),
                               w * np.angle(Bm * np.conj(Bp))])
    best, bestc = None, np.inf
    for fn0 in (6.0, 7.5, 8.5, 10.0, 12.0):
        for z0 in (0.08, 0.2, 0.4, 0.8):
            for ph0 in (0.0, np.pi * 0.99, -np.pi * 0.99):
                p0 = list(p0d); p0[2] = fn0; p0[3] = z0; p0[1] = ph0
                # scale A so the model starts on the data
                try:
                    p0[0] = float(np.abs(Bm[len(Bm) // 2]) / max(1e-12, np.abs(model(p0, f[len(f) // 2:len(f) // 2 + 1], kind))[0]) * p0[0])
                    r = optimize.least_squares(res, p0, bounds=(lo, hi), max_nfev=6000)
                except Exception:
                    continue
                if r.cost < bestc:
                    best, bestc = r, r.cost
    return best, names


def fit_report(f, Bm, coh, nw, flo=3.0, fhi=30.0, kinds=("INT", "Z1", "Z1P", "Z1PZ", "Z1PP")):
    sel = (f >= flo) & (f <= fhi) & (coh >= COH_MIN) & np.isfinite(np.abs(Bm)) & (np.abs(Bm) > 0)
    if sel.sum() < 10:
        pr("      only %d usable bins in %.0f-%.0f Hz (coh >= %.2f) -- NOT FITTED" % (sel.sum(), flo, fhi, COH_MIN))
        return None
    fv, cv = f[sel], np.clip(coh[sel], 0.02, 0.995)
    Bv = Bm[sel] / np.sqrt(cv)           # Hv: the geometric mean of H1 and H2 (H1 is biased LOW)
    w = np.minimum(np.sqrt(2.0 * nw * cv / (1.0 - cv)), 40.0)
    out = {}
    for kind in kinds:
        r, names = fit(fv, Bv, w, kind)
        if r is None:
            continue
        Bp = model(r.x, fv, kind)
        rm = float(np.sqrt(np.mean((np.log(np.abs(Bv)) - np.log(np.abs(Bp))) ** 2)))
        rp = float(np.degrees(np.sqrt(np.mean(np.angle(Bv * np.conj(Bp)) ** 2))))
        out[kind] = dict(p={k: float(v) for k, v in zip(names, r.x)}, rms_ln_mag=rm, rms_phase_deg=rp,
                         n_bins=int(sel.sum()), flo=flo, fhi=fhi)
        pr("      %-5s %-62s  rms ln|B| %.3f (%+.0f%%)  rms ph %5.1f deg  n=%d"
           % (kind, "  ".join("%s=%.4g" % (k, v) for k, v in zip(names, r.x)), rm, 100 * (np.exp(rm) - 1), rp, sel.sum()))
    return out


# ====================================================================================================== main
def main():
    cells = read_cells(V282_IMG)
    cells280 = read_cells(V280R2_IMG)
    pr("=" * 154)
    pr("B(f) -- THE TORSION-BAR TORQUE PER UNIT WHEEL RATE, 3-30 Hz, ON V282 (routes r39 and r6c)")
    pr("  B := bar/rate, both raw off the SAME 0x18F frame, NO negation applied to either -> convention-free.")
    pr("  R_r24(f) = -(5244/1024) * D4(f) * B(f) is then the CELL gp-0x6ada per unit of x = -rate.")
    pr("=" * 154)

    # ---------------------------------------------------------------- 0. POSITIVE CONTROL
    pr("\n" + "=" * 154)
    pr("0. POSITIVE CONTROL -- reproduce the record's +114 deg / coh 0.94 at 20 Hz, creep 1-3, on ITS OWN pool")
    pr("   (r31..r34; GRINDING-DEEP-ANALYSIS-2026-09-03 headline 3 and sec 1; nperseg 128, nearest bin)")
    pr("=" * 154)
    gs = {}
    for t in CTRL_ROUTES:
        print("loading %s ..." % t, flush=True)
        gs[t] = load(t, cells280)
    P, secs = pool_stratum(gs, CTRL_ROUTES, STRATA[0][2], ("bar", "wire"), 128)
    f = P.f
    Bc, Cc = P.tf("wire", "bar"), P.coh("wire", "bar")
    i20, i7 = int(np.argmin(np.abs(f - 20.0))), int(np.argmin(np.abs(f - 7.0)))
    pr("  pool: %.1f s, %d Welch windows        (record: 28.0 s, 25 windows)" % (secs, P.n))
    pr("  @%.2f Hz : |B| %.2f  ang %+.0f deg  coh %.2f   (record +114 deg, coh 0.94, |B| 2.81)"
       % (f[i20], abs(Bc[i20]), np.degrees(np.angle(Bc[i20])), Cc[i20]))
    pr("  @%.2f Hz : |B| %.2f  ang %+.0f deg  coh %.2f   (record -139 deg, coh 0.73)"
       % (f[i7], abs(Bc[i7]), np.degrees(np.angle(Bc[i7])), Cc[i7]))
    ok = abs(((np.degrees(np.angle(Bc[i20])) - 114 + 180) % 360) - 180) <= 8
    pr("  CONTROL %s" % ("PASS (within 8 deg of the record)" if ok else "*** FAIL ***"))
    for nm, fn, rec in (("loaded_any", STRATA[6][2], "-96/+116"), ("highway", STRATA[7][2], "-121/+114")):
        P2, s2 = pool_stratum(gs, CTRL_ROUTES, fn, ("bar", "wire"), 128)
        if P2.n:
            B2, C2 = P2.tf("wire", "bar"), P2.coh("wire", "bar")
            pr("  %-11s %6.1f s : @7 Hz %+.0f (coh %.2f)  @20 Hz %+.0f (coh %.2f)   (record %s)"
               % (nm, s2, np.degrees(np.angle(B2[i7])), C2[i7], np.degrees(np.angle(B2[i20])), C2[i20], rec))
    pr("  closed form ang(R_r24) per unit of x=-rate: @%.2f Hz %+.0f deg  (record closed form +10; wire bit4 +10 on r39)"
       % (f[i20], np.degrees(np.angle(R_r24(Bc[i20], f[i20])))))
    J["control"] = dict(secs=secs, nwin=P.n, f20=float(f[i20]), absB20=float(abs(Bc[i20])),
                        phB20=float(np.degrees(np.angle(Bc[i20]))), coh20=float(Cc[i20]),
                        f7=float(f[i7]), absB7=float(abs(Bc[i7])), phB7=float(np.degrees(np.angle(Bc[i7]))),
                        coh7=float(Cc[i7]), passed=bool(ok))
    del gs

    # ---------------------------------------------------------------- load V282 routes
    G = {}
    for t in V282_ROUTES:
        print("loading %s ..." % t, flush=True)
        G[t] = load(t, cells)
    pr("\n" + "-" * 154)
    pr("V282 ROUTES")
    for t in V282_ROUTES:
        g = G[t]
        pr("  %-5s len %7.1f s  engaged-lateral %7.1f s  0x14A b4 frames %7d  0x18F dejitter resid p50/p90 %.1f/%.1f ms"
           % (t, g["tr"][-1], g["eng"].sum() / FS, g.get("b4_n", 0), 1e3 * g["b4_res"][0], 1e3 * g["b4_res"][1]))
        pr("        strata seconds: " + "  ".join("%s %.0f" % (k, fn(g).sum() / FS) for k, _, fn in STRATA))
        J.setdefault("routes", {})[t] = dict(length_s=float(g["tr"][-1]), eng_s=float(g["eng"].sum() / FS),
                                             strata_s={k: float(fn(g).sum() / FS) for k, _, fn in STRATA})

    # ---------------------------------------------------------------- 1. B(f)
    pr("\n" + "=" * 154)
    pr("1. B(f).  |B| in bar counts per raw rate count (the 0x18F rate is 8 raw counts per deg/s).")
    pr("   Estimator: pooled Welch nperseg %d, spectra interpolated to %.3f Hz (nfft %d), band-averaged over"
       % (NPS, FS / NFFT, NFFT))
    pr("   f0 +- %.2f Hz, so every row is evaluated AT the requested frequency.  Cross-check: nperseg %d." % (HALF, NPS2))
    pr("   |B|H1 = Sxy/Sxx is biased LOW by input noise; |B|H2 = Syy/Syx is biased HIGH; the truth lies")
    pr("   between.  |B|Hv = |B|H1/sqrt(coh) is their geometric mean and is the recommended central value.")
    pr("   coh < %.2f => UNUSABLE: no phase is reported for that point." % COH_MIN)
    pr("=" * 154)
    TAB = {}
    for key, name, fn in STRATA:
        for grp, tags in (("r39", ("r39",)), ("r6c", ("r6c",)), ("V282pool", V282_ROUTES)):
            Pa, sa = pool_stratum(G, tags, fn, ("bar", "wire"), NPS, NFFT)
            Pb, sb = pool_stratum(G, tags, fn, ("bar", "wire"), NPS2, NFFT2)
            if Pa.n == 0:
                continue
            pr("\n  %-62s %-9s  nps%d: %7.1f s / %4d win    nps%d: %7.1f s / %4d win"
               % (name, grp, NPS, sa, Pa.n, NPS2, sb, Pb.n))
            pr("    %-6s %8s %8s %8s %8s %6s %5s | %8s %8s %6s" %
               ("f Hz", "|B|H1", "|B|Hv", "|B|H2", "ang B", "coh", "bins", "|B|Hv", "ang B", "coh"))
            rows = []
            for f0 in FREQS:
                b, c, nb = Pa.bavg("wire", "bar", f0)
                hv = abs(b) / np.sqrt(max(c, 1e-6)); h2 = abs(b) / max(c, 1e-6)
                r = dict(f=f0, H1=float(abs(b)), Hv=float(hv), H2=float(h2),
                         ph=float(np.degrees(np.angle(b))), coh=float(c), nbins=nb, usable=bool(c >= COH_MIN))
                if Pb.n:
                    b2, c2, _ = Pb.bavg("wire", "bar", f0)
                    r.update(Hv2=float(abs(b2) / np.sqrt(max(c2, 1e-6))), ph2=float(np.degrees(np.angle(b2))), coh2=float(c2))
                rows.append(r)
                pr("    %-6.1f %8.2f %8.2f %8.2f %8s %6.2f %5d | %8.2f %8s %6.2f" %
                   (f0, r["H1"], r["Hv"], r["H2"], ("%+8.0f" % r["ph"]) if r["usable"] else "  UNUSBL", r["coh"], nb,
                    r.get("Hv2", np.nan), ("%+8.0f" % r["ph2"]) if r.get("coh2", 0) >= COH_MIN else "  UNUSBL",
                    r.get("coh2", np.nan)))
            fg, Bg, Cg = Pa.grid("wire", "bar")
            sl = Cg >= COH_MIN
            entry = dict(rows=rows, secs=sa, nwin=Pa.n, secs2=sb, nwin2=Pb.n)
            if sl.sum() > 6:
                phu = np.degrees(np.unwrap(np.angle(Bg[sl])))
                phu = phu - phu[0] + np.degrees(np.angle(Bg[sl][0]))
                pr("    |B| peak at %.2f Hz (usable bins) ; UNWRAPPED phase %.1f Hz %+.0f deg -> %.1f Hz %+.0f deg  (NET %+.0f deg)"
                   % (fg[sl][int(np.argmax(np.abs(Bg[sl])))], fg[sl][0], phu[0], fg[sl][-1], phu[-1], phu[-1] - phu[0]))
                entry["unwrap"] = dict(f=[float(x) for x in fg[sl]], ph=[float(x) for x in phu])
            TAB["%s|%s" % (key, grp)] = entry
    J["tables"] = TAB

    # ---------------------------------------------------------------- 2. FIT
    pr("\n" + "=" * 154)
    pr("2. PARAMETRIC FIT.  B(f) = A e^{j phi0} * H(f) * e^{-j 2 pi f tau},  f in Hz, fitted to Hv on")
    pr("   coherence-usable bins, weights sqrt(2 nw coh/(1-coh)) capped at 40.  phi0 absorbs the overall sign.")
    pr("     INT   H = 1/((j f) (1-(f/fn)^2+2j z f/fn))                     integrator * 2nd-order pole")
    pr("     Z1    H = (j f)/(1-(f/fn)^2+2j z f/fn)                         zero at the origin * 2nd-order pole")
    pr("     Z1P   H = Z1 / (1+j f/fp)                                      + one real pole")
    pr("     Z1PZ  H = Z1 (1+j f/fz)/(1+j f/fp)                             + a real pole and a real zero")
    pr("     Z1PP  H = (j f)/(two 2nd-order pole pairs)")
    pr("=" * 154)
    FITS = {}
    for key, name, fn in STRATA:
        for grp, tags in (("r39", ("r39",)), ("r6c", ("r6c",)), ("V282pool", V282_ROUTES)):
            Pa, sa = pool_stratum(G, tags, fn, ("bar", "wire"), NPS, NFFT)
            if Pa.n < 8:
                continue
            fg, Bg, Cg = Pa.grid("wire", "bar")
            for flo, fhi in ((3.0, 30.0), (6.0, 25.0)):
                pr("\n  %-62s %-9s %.1f s / %d win   band %.0f-%.0f Hz" % (name, grp, sa, Pa.n, flo, fhi))
                r = fit_report(fg, Bg, Cg, Pa.n, flo, fhi)
                if r:
                    FITS["%s|%s|%g-%g" % (key, grp, flo, fhi)] = r
    J["fits"] = FITS

    # ---------------------------------------------------------------- 3a. bit-6 duty
    pr("\n" + "=" * 154)
    pr("3a. BIT-6 DUTY  ( bit6 = |gp-0x6ada| >= |gp-0x6b38| = |r24| >= |T| ).")
    pr("    PREREG-V282-READ rule: >= 0.22 => r24 dominant (5244 arm live) ; <= 0.10 => the gp-0x671d/1024 arm is live.")
    pr("    CI: moving-block bootstrap, 1.0 s blocks, 2000 resamples, percentile 2.5/97.5.")
    pr("=" * 154)
    rng = np.random.default_rng(20260913)

    def block_ci(x, blk=100, nboot=2000):
        x = np.asarray(x, float); n = len(x)
        if n < 2 * blk:
            blk = max(1, n // 4)
        nb = max(1, n // blk); starts = np.arange(0, n - blk + 1)
        if len(starts) == 0:
            return float(x.mean()), float("nan"), float("nan")
        idx = rng.integers(0, len(starts), size=(nboot, nb))
        base = starts[idx][:, :, None] + np.arange(blk)[None, None, :]
        bs = x[base.reshape(nboot, -1)].mean(axis=1)
        return float(x.mean()), float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))

    DUTY = {}
    pr("  %-5s %-62s %8s %8s %8s %20s %8s %12s" %
       ("route", "stratum", "frames", "seconds", "bit6", "95% CI", "bit5", "prereg verdict"))
    for t in list(V282_ROUTES) + ["POOL"]:
        for key, name, fn in STRATA:
            if t == "POOL":
                xs = [G[u]["bit6"][fn(G[u])] for u in V282_ROUTES if fn(G[u]).sum() >= 200]
                ys = [G[u]["bit5"][fn(G[u])] for u in V282_ROUTES if fn(G[u]).sum() >= 200]
                if len(xs) < 2:
                    continue
                x, y = np.concatenate(xs), np.concatenate(ys)
            else:
                m = fn(G[t])
                if m.sum() < 200:
                    continue
                x, y = G[t]["bit6"][m], G[t]["bit5"][m]
            d, lo, hi = block_ci(x)
            v = "r24 DOMINANT" if lo >= 0.22 else ("1024 ARM" if hi <= 0.10 else "between")
            pr("  %-5s %-62s %8d %8.1f %8.4f  [%.4f, %.4f] %8.4f %12s"
               % (t, name, len(x), len(x) / FS, d, lo, hi, y.mean(), v))
            DUTY["%s|%s" % (t, key)] = dict(n=int(len(x)), secs=float(len(x) / FS), bit6=d, lo=lo, hi=hi,
                                            bit5=float(y.mean()), verdict=v)
    J["duty"] = DUTY

    pr("\n  CLOSED-FORM LADDER on each route's OWN torsion-bar data (r24_series verbatim from v282_r24_tap_read.py).")
    pr("  The measured duty is inverted onto the ladder to give the IMPLIED 0xC6446 arm.")
    R24 = {t: {gn: r24_series(G[t]["bar"], gn) for gn in GAIN_LADDER} for t in V282_ROUTES}
    LAD = {}
    for key, name, fn in STRATA:
        pr("\n    %s" % name)
        pr("      %-6s %s%12s%12s" % ("route", "".join("%8.0f" % gn for gn in GAIN_LADDER), "MEASURED", "implied arm"))
        for t in V282_ROUTES:
            g = G[t]; m = fn(g)
            if m.sum() < 200:
                continue
            Tm = np.abs(g["T100"])
            pred = np.array([np.mean((np.abs(R24[t][gn]) >= Tm)[m]) for gn in GAIN_LADDER])
            meas = g["bit6"][m].mean(); gl = np.array(GAIN_LADDER)
            imp = float(np.exp(np.interp(meas, pred, np.log(gl)))) if (pred[0] <= meas <= pred[-1]) else float("nan")
            pr("      %-6s %s%12.4f%12.0f" % (t, "".join("%8.4f" % p for p in pred), meas, imp))
            LAD["%s|%s" % (t, key)] = dict(gains=GAIN_LADDER, pred=[float(p) for p in pred], meas=float(meas), implied=imp)
    J["ladder"] = LAD

    # ---------------------------------------------------------------- 3b. bit-4 phase
    pr("\n" + "=" * 154)
    pr("3b. BIT-4 PHASE.  bit4 = sign(gp-0x6ada); the bit is SET when the cell is NEGATIVE, so")
    pr("    s4 = 1-2*bit4 = +1 when the cell >= 0.  Reported as ang(tf(x -> s4)) with x = -rate (INTERNAL rate),")
    pr("    which is the SAME reference as the model ang(-(5244/1024) D4 B).  The wire-rate-referenced number")
    pr("    is this MINUS 180 -- printed too, so no 180 is absorbed anywhere.")
    pr("    TIMING CONTROL  ang(tf(s4cf -> s4)) must be ~0.  s4cf = -sign(r24_series(bar)) -- the explicit extra")
    pr("    negation is the cache-sign trap documented in the module docstring, NOT a free parameter.")
    pr("=" * 154)
    for t in V282_ROUTES:
        G[t]["xrate"] = -G[t]["wire"]
        s = -np.sign(R24[t][5244.0]); s[s == 0] = 1.0
        G[t]["s4cf"] = s
    PH = {}
    for key, name, fn in STRATA:
        for grp, tags in (("r39", ("r39",)), ("r6c", ("r6c",)), ("V282pool", V282_ROUTES)):
            Pa, sa = pool_stratum(G, tags, fn, ("bar", "wire", "xrate", "s4", "s4cf"), NPS, NFFT)
            if Pa.n < 6:
                continue
            pr("\n  %-62s %-9s %7.1f s / %d win" % (name, grp, sa, Pa.n))
            pr("    %-6s %10s %6s | %10s %6s | %9s | %10s %6s | %8s" %
               ("f Hz", "ang s4|x", "coh", "MODEL", "cohB", "ang s4|wire", "ctrl s4cf", "coh", "meas-model"))
            row = {}
            for f0 in (7.3, 20.3):
                h4, c4, _ = Pa.bavg("xrate", "s4", f0)
                hB, cB, _ = Pa.bavg("wire", "bar", f0)
                hc, cc, _ = Pa.bavg("s4cf", "s4", f0)
                mod = R_r24(hB, f0)
                p4 = np.degrees(np.angle(h4)); pm = np.degrees(np.angle(mod))
                d = ((p4 - pm + 180) % 360) - 180
                pr("    %-6.1f %10s %6.2f | %10s %6.2f | %9s | %10s %6.2f | %+8.0f" %
                   (f0, ("%+10.0f" % p4) if c4 >= COH_MIN else "  UNUSABLE", c4,
                    ("%+10.0f" % pm) if cB >= COH_MIN else "  UNUSABLE", cB,
                    ("%+9.0f" % (((p4 - 180 + 180) % 360) - 180)) if c4 >= COH_MIN else " UNUSABLE",
                    ("%+10.0f" % np.degrees(np.angle(hc))) if cc >= COH_MIN else "  UNUSABLE", cc, d))
                row["%.1f" % f0] = dict(ph_s4_internal=float(p4), coh_s4=float(c4), ph_model=float(pm),
                                        coh_B=float(cB), ph_ctrl=float(np.degrees(np.angle(hc))),
                                        coh_ctrl=float(cc), meas_minus_model=float(d))
            PH["%s|%s" % (key, grp)] = row
    J["bit4"] = PH

    # ---------------------------------------------------------------- 4. LATCH SCAN
    pr("\n" + "=" * 154)
    pr("4. gp-0x671d FIRST-STRIKE LATCH SCAN.  A latch collapsing r24 to ~x0.195 would show as a MONOTONE")
    pr("   STEP-DOWN in bit-6 duty that never recovers.  duty is regime-dependent, so the primary statistic is")
    pr("   ratio = duty_measured / duty_predicted_at_5244 on the SAME frames.  Windows: 30 s of engaged-lateral")
    pr("   time each, 15 s step, in route order.")
    pr("=" * 154)
    LATCH = {}
    for t in V282_ROUTES:
        g = G[t]
        e = np.flatnonzero(g["eng"]); W, S = 3000, 1500
        Tm = np.abs(g["T100"])
        p5244 = (np.abs(R24[t][5244.0]) >= Tm).astype(float)
        p1024 = (np.abs(R24[t][1024.0]) >= Tm).astype(float)
        rows = []
        for a in range(0, max(0, len(e) - W + 1), S):
            ii = e[a:a + W]
            pp = p5244[ii].mean()
            rows.append(dict(t0=float(g["tr"][ii[0]]), t1=float(g["tr"][ii[-1]]), duty=float(g["bit6"][ii].mean()),
                             p5244=float(pp), p1024=float(p1024[ii].mean()),
                             ratio=float(g["bit6"][ii].mean() / pp) if pp > 1e-6 else float("nan")))
        if len(rows) < 8:
            continue
        ra = np.array([r["ratio"] for r in rows]); dm = np.array([r["duty"] for r in rows])
        tt = np.array([r["t0"] for r in rows])

        def maxz(v, sign=+1):
            b, bk = -np.inf, None
            for k in range(3, len(v) - 3):
                a1, a2 = v[:k], v[k:]
                sd = np.sqrt(a1.var(ddof=1) / len(a1) + a2.var(ddof=1) / len(a2))
                if sd > 0:
                    z = sign * (a1.mean() - a2.mean()) / sd
                    if z > b:
                        b, bk = z, k
            return b, bk
        zd, kd = maxz(ra, +1)
        zu, ku = maxz(ra, -1)
        null = np.array([maxz(rng.permutation(ra), +1)[0] for _ in range(1000)])
        pv = float(np.mean(null >= zd))
        sdw = float(np.nanstd(ra, ddof=1))
        half = 3 * sdw * np.sqrt(4.0 / len(rows))       # a z=3 step located mid-route
        med = float(np.nanmedian(ra))
        pr("\n  %-5s  %d windows of 30 s engaged (%.0f s engaged total)" % (t, len(rows), g["eng"].sum() / FS))
        pr("    duty  p10/p50/p90 = %.4f / %.4f / %.4f ;  ratio(meas/pred@5244) p10/p50/p90 = %.3f / %.3f / %.3f"
           % (np.percentile(dm, 10), np.median(dm), np.percentile(dm, 90),
              np.nanpercentile(ra, 10), med, np.nanpercentile(ra, 90)))
        pr("    predicted duty medians: 5244 arm %.4f, 1024 arm %.4f -> a latch would multiply the ratio by %.2f"
           % (np.median([r["p5244"] for r in rows]), np.median([r["p1024"] for r in rows]),
              np.median([r["p1024"] for r in rows]) / max(1e-9, np.median([r["p5244"] for r in rows]))))
        pr("    best DOWNWARD step: z %+.2f at t %.0f s, permutation p %.3f  -> %s"
           % (zd, tt[kd] if kd else -1, pv, "NO persistent step-down" if pv > 0.05 else "*** CANDIDATE -- inspect ***"))
        pr("    best UPWARD   step: z %+.2f at t %.0f s   (reported for symmetry; a latch cannot go up)"
           % (zu, tt[ku] if ku else -1))
        pr("    window sd of ratio %.3f ; smallest mid-route step detectable at z=3 is %.3f in ratio"
           % (sdw, half))
        pr("    = a collapse of r24 to x%.2f or worse would have been seen.  The hypothesised latch is x0.195." % (1 - half / med))
        pr("    first 5 window ratios: %s ;  last 5: %s"
           % (" ".join("%.3f" % v for v in ra[:5]), " ".join("%.3f" % v for v in ra[-5:])))
        LATCH[t] = dict(n_windows=len(rows), z_down=float(zd), t_down=float(tt[kd]) if kd else None, p=pv,
                        z_up=float(zu), sd_ratio=sdw, median_ratio=med, min_detectable_factor=float(1 - half / med),
                        rows=rows)
        x = signal.resample_poly(g["bar"] - g["bar"][0], 10, 1) + g["bar"][0]
        dd = np.zeros_like(x); dd[4:] = 0.5 * (x[4:] - x[:-4])
        pre = np.abs(np.trunc(np.clip(dd, -5120, 5120) * 5244.0 / 1024.0))
        raw = np.abs(np.trunc(dd * 5244.0 / 1024.0))
        pr("    LATCH-INPUT BOUND -- does ANY quantity in the lane ever reach the SET threshold 5530?")
        pr("      |bar|        max %7.0f   frames >=5530: %d" % (np.abs(g["bar"]).max(), int((np.abs(g["bar"]) >= 5530).sum())))
        pr("      |d| (1 kHz)  max %7.0f   frames >=5530: %d   (the +-5120 clip is never reached either: max |d| %.0f)"
           % (np.abs(dd).max(), int((np.abs(dd) >= 5530).sum()), np.abs(dd).max()))
        pr("      |r24| pre-db max %7.0f   frames >=5530: %d   (post-clip d * 5244/1024)" % (pre.max(), int((pre >= 5530).sum())))
        pr("      |d*5244/1024| PRE-clip max %7.0f  frames >=5530: %d" % (raw.max(), int((raw >= 5530).sum())))
        LATCH[t]["input_bound"] = dict(bar_max=float(np.abs(g["bar"]).max()), d_max=float(np.abs(dd).max()),
                                       r24_max=float(pre.max()), raw_max=float(raw.max()),
                                       n_ge_5530=int((raw >= 5530).sum()))
    J["latch"] = LATCH

    with open(os.path.join(SCR, "bof_v282.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    with open(os.path.join(SCR, "bof_v282.json"), "w") as fh:
        json.dump(J, fh, indent=1, default=float)
    print("\nwrote", os.path.join(SCR, "bof_v282.txt"))


if __name__ == "__main__":
    main()
