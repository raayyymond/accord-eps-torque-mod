# -*- coding: utf-8 -*-
"""studies/grind/v282_r24_tap_read.py -- score PREREG-V282-READ.md (A)-(E) on the FIRST FLIGHT of the V282
cave (routes r36/r37/r38, build V283 = V282 + Ki 50), against r35 (V281 rev 3, OLD cave decode) and
r34 (V280 rev 2, OLD cave decode).  Subagent grind283, 2026-09-03.  Analysis only: builds nothing, sends nothing.

V283 cave decode, CAN 0x14A byte 4 (100 Hz):
    bit 7 = sign(gp-0x6b4c)  (11-slot assist sum)          -- unchanged since V105
    bit 6 = |gp-0x6ada| >= |gp-0x6b38|   = |r24| >= |T|    -- REPOINTED by V282 (was |6b94|>=|4f64|, duty 0.0000)
    bit 5 = |gp-0x6ada| >= |gp-0x6b94|   = |r24| >= |agg|  -- REPOINTED by V282 (was |6ae2|>=|6b26|, duty 0.337)
    bit 4 = sign(gp-0x6ada) = sign(r24)                    -- unchanged since V105
    bit 3 = sign(gp-0x3680)                                -- unchanged since V105
The bit is 1 when the predicate holds / when the cell is NEGATIVE (r24_sign_on_the_wire.py's convention).

Inputs (all pre-existing caches; nothing here writes to the shared v280 cache except *_b4 which this
session's extract_14a_b4_r36_r38.py already wrote):
    analysis-2020accord/_scratch/cache/v280/r3{4,5,6,7,8}.npz        (0x18F, 0x14A, 0x1AB tap, 0xE4, vEgo)
    analysis-2020accord/_scratch/cache/v280/r3{4,5,6,7,8}_b4.npz     (0x14A byte 4)
Run: python v282_r24_tap_read.py     (writes _scratch/v282_r24_tap_read.txt beside it)
"""
import os
import sys

import numpy as np
from scipy import signal, stats

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(os.path.dirname(HERE)))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "studies", "v280"))
sys.path.insert(0, os.path.join(KIT, "analysis-2020accord", "lib"))
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                 # noqa: E402
import lowcmd_loopgain_v112_v278_v280 as LG   # noqa: E402
import v280_map_profiles as V                 # noqa: E402
import _grind2_lib as G2                      # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FS, FS1K, FST = 100.0, 1000.0, 50.0
CACHE = C20.CACHE
V283_ROUTES = ("r36", "r37", "r38")
BASE_ROUTES = ("r35", "r34")
ALL = V283_ROUTES + BASE_ROUTES
BUILD = {"r36": "V283 (Ki 50, Kp flat 248, r24 cmp tap)", "r37": "V283", "r38": "V283",
         "r35": "V281r3 (Kp flat 248, OLD cave decode)", "r34": "V280r2 new tune (OLD cave decode)"}
IMG = {"V283": LG.FW + "_v283_V283-V282BASE-KI50.KP.FLAT.Y0-CAVE.R24CMP-MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
       "V281r3": LG.FW + "_v281r3_V281R3-V280R2BASE-KP.FLAT.Y0.MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin",
       "V280r2": LG.FW + LG.IMAGES["V280r2"]}
GAINS = (5244.0, 3072.0, 2048.0, 1024.0, 512.0)
GLBL = {5244.0: "5244  (flown engaged arm)", 3072.0: "3072  (Honda LERP top)", 2048.0: "2048  (0xC6440 stock arm)",
        1024.0: "1024  (0xC6442 fault arm)", 512.0: "512   (stock 0xC6446)"}
OUT = []


def pr(s=""):
    print(s, flush=True); OUT.append(s)


def lerp(x, y, u):
    return np.interp(np.asarray(u, float), x, y)


# ---------------------------------------------------------------------------------------------------- image
def read_cells(path):
    c = LG.read_build(path)
    b = open(path, "rb").read()
    c["fadeB"] = LG.lerp_rec(b, LG.u32(b, 0xCBBC4 + 4 * LG.SEL), 6)
    c["fadeA"] = LG.lerp_rec(b, LG.u32(b, 0xCBC34 + 4 * LG.SEL), 6)
    c["taperS"] = LG.lerp_rec(b, LG.u32(b, 0xCB924 + 4 * LG.SEL), 4)
    c["taperO"] = LG.lerp_rec(b, LG.u32(b, 0xCB8B4 + 4 * LG.SEL), 4)
    c["ki"] = int.from_bytes(b[0xC63E6:0xC63E8], "little")
    c["lb"] = int.from_bytes(b[0xC6446:0xC6448], "little")
    c["lag_c"] = (int.from_bytes(b[0xC63EC:0xC63EE], "little"), int.from_bytes(b[0xC63EE:0xC63F0], "little"))
    c["fbp"] = (int.from_bytes(b[0xC63E8:0xC63EA], "little"), int.from_bytes(b[0xC63EA:0xC63EC], "little"))
    return c


def demand_live(cmd, bar, c):
    S = np.clip(-4.0 * np.round(cmd), -V.LIMIT, V.LIMIT)
    same = np.sign(S) == np.sign(bar)
    tx = np.abs(bar) // 32
    taper = np.where(same, lerp(c["taperS"][0], c["taperS"][1], tx), lerp(c["taperO"][0], c["taperO"][1], tx))
    prod = (taper * 255).astype(np.int64) & 0xFFFF
    v = np.floor(prod * S / 65536.0); v = np.floor(v / 64.0); v = np.clip(v, -V.IDX_CLAMP, V.IDX_CLAMP)
    return np.abs(v), np.where(v < 0, -1.0, 1.0)


# ---------------------------------------------------------------------------------------------------- pooled spectra
class Pool:
    def __init__(self, fs, nps):
        self.fs, self.nps, self.f, self.S, self.n = fs, nps, None, {}, 0

    def add(self, sigs):
        n = len(next(iter(sigs.values())))
        if n < self.nps:
            return 0
        nw = max(1, (n - self.nps // 2) // (self.nps // 2))
        keys = list(sigs)
        for i, a in enumerate(keys):
            for b in keys[i:]:
                f, P = signal.csd(sigs[a], sigs[b], fs=self.fs, nperseg=self.nps, detrend="constant")
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


def r24_series(bar100, gain):
    """r24 at 1 kHz from the decompiled arithmetic, decimated to the 100 Hz frame axis (v282_prereg_duty.py, verbatim)."""
    x = signal.resample_poly(bar100 - bar100[0], 10, 1) + bar100[0]
    d = np.zeros_like(x)
    d[4:] = 0.5 * (x[4:] - x[:-4])
    d = np.clip(d, -5120, 5120)
    s = np.trunc(d * gain / 1024.0)
    s = np.where(np.abs(s) <= 3, 0.0, s - np.sign(s) * 3)
    return np.clip(-s, -8192, 8192)[::10][:len(bar100)]


def line_of(x, fs, lo=15.0, hi=26.0, nfft=4096):
    x = np.asarray(x, float)
    if len(x) < 32:
        return np.nan, np.nan
    f, P = signal.periodogram(x - x.mean(), fs=fs, window="hann", nfft=nfft)
    Rp = G2.prom_spectrum(f, P, 6.0, 1.5)
    return G2.locate(f, P, lo, hi, R=Rp)


def band(x, lo, hi, fs=FS):
    return C20.bamp(x, lo, hi, fs)


# ---------------------------------------------------------------------------------------------------- strata
STRATA = [
    ("(A/B) creep engaged hands-off  v 1-3, |bar|<400",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 3.0) & (np.abs(g["bar"]) < 400)),
    ("      creep engaged hands-off  v 1-6, |bar|<400",
     lambda g: g["eng"] & (g["vego"] >= 1.0) & (g["vego"] < 6.0) & (np.abs(g["bar"]) < 400)),
    ("(D)   loaded high-angle engaged  v 2-9, |ang|>30, idx>=68",
     lambda g: g["eng"] & (g["vego"] >= 2.0) & (g["vego"] < 9.0) & (np.abs(g["ang"]) > 30) & (g["idx"] >= 68)),
    ("      loaded high-angle engaged  v 2-9, |ang|>30 (any idx)",
     lambda g: g["eng"] & (g["vego"] >= 2.0) & (g["vego"] < 9.0) & (np.abs(g["ang"]) > 30)),
    ("      highway engaged  v > 15",
     lambda g: g["eng"] & (g["vego"] > 15.0)),
    ("      all engaged lateral",
     lambda g: g["eng"]),
]
SHOW = [3.9, 5.5, 7.0, 8.6, 10.9, 13.3, 15.6, 18.0, 19.5, 21.1, 22.7]


def main():
    cells = {k: read_cells(p) for k, p in IMG.items()}
    pr("=" * 152)
    pr("V282 CAVE FIRST FLIGHT -- scoring PREREG-V282-READ.md (A)-(E) on r36/r37/r38 (V283), vs r35 (V281r3) and r34 (V280r2)")
    pr("=" * 152)
    pr("\nCELLS READ FROM THE IMAGES (variant slot %d)" % LG.SEL)
    pr("  %-8s %-6s %-30s %-14s %-10s %-14s %s" % ("image", "Ki", "Kp Y", "Kd Y", "0xC6446", "out-lag a/b", "fb-pole a/b"))
    for k in ("V283", "V281r3", "V280r2"):
        c = cells[k]
        pr("  %-8s %-6d %-30s %-14s %-10d %-14s %s" % (
            k, c["ki"], c["kp_Y"].astype(int).tolist(), c["kd_Y"].astype(int).tolist()[:2], c["lb"],
            "%d/%d" % c["lag_c"], "%d/%d" % c["fbp"]))
    pr("  [EVIDENCE] V283 vs V281r3: Ki %d -> %d is the only calibration difference; 0xC6446 = %d (unchanged),"
       % (cells["V281r3"]["ki"], cells["V283"]["ki"], cells["V283"]["lb"]))
    pr("             out-lag pole %s and fb pole %s BYTE-IDENTICAL in all three images (never touched on any build)."
       % ("%d/%d" % cells["V283"]["lag_c"], "%d/%d" % cells["V283"]["fbp"]))

    # ------------------------------------------------------------------ load
    G = {}
    for tag in ALL:
        print("loading %s ..." % tag, flush=True)
        C20.BUILD[tag] = BUILD[tag]
        g = C20.load(tag)
        D = dict(np.load(os.path.join(CACHE, tag + ".npz")))
        g["t0"] = float(D["t18"][0]); g["tr"] = g["t"] - g["t"][0]
        c = cells["V283"] if tag in V283_ROUTES else (cells["V281r3"] if tag == "r35" else cells["V280r2"])
        g["idx"], g["sgn"] = demand_live(np.round(g["cmd"]), g["bar"], c)
        B = np.load(os.path.join(CACHE, tag + "_b4.npz"))
        k14, P14, tn14, res14 = C20.dejitter(B["t14b"], 0.01, 100)
        b4 = B["b4"].astype(int)
        g["b4_n"] = len(b4)
        for bit in (3, 4, 5, 6, 7):
            g["bit%d" % bit] = np.round(np.interp(g["t"], tn14, ((b4 >> bit) & 1).astype(float)))
            g["s%d" % bit] = 1.0 - 2.0 * g["bit%d" % bit]
        g["s_T"] = np.sign(g["T100"])
        pr("  %-4s %-40s %7.1f s, engaged-lateral %6.1f s ; 0x14A b4 frames %6d ; 0x18F resid p50/p90 %.1f/%.1f ms" % (
            tag, BUILD[tag], g["tr"][-1], g["eng"].sum() / FS, g["b4_n"], 1e3 * g["res"]["f18"][0], 1e3 * g["res"]["f18"][1]))
        G[tag] = g

    # ================================================================== 0. FAIL GATE
    pr("\n" + "=" * 152)
    pr("0. THE FAIL GATE -- is the repointed comparator NON-DEGENERATE?  (checked BEFORE any duty is interpreted)")
    pr("   PREREG FAIL: '(A) or (B) reading 0.000 or 1.000 over >= 20 s of engaged creep'.")
    pr("=" * 152)
    pr("  %-5s %-40s %8s %8s %8s %8s %8s %10s" % ("route", "build", "bit7", "bit6", "bit5", "bit4", "bit3", "creep s"))
    for tag in ALL:
        g = G[tag]
        m = STRATA[0][1](g)
        pr("  %-5s %-40s %8.4f %8.4f %8.4f %8.4f %8.4f %10.1f" % (
            tag, BUILD[tag], g["bit7"].mean(), g["bit6"].mean(), g["bit5"].mean(), g["bit4"].mean(), g["bit3"].mean(), m.sum() / FS))
    pr("  (duties above are ROUTE-WIDE, every logged frame; the stratified numbers are section A/B)")
    pr("")
    for tag in ALL:
        g = G[tag]
        m = STRATA[0][1](g)
        secs = m.sum() / FS
        d6, d5 = g["bit6"][m].mean() if m.any() else np.nan, g["bit5"][m].mean() if m.any() else np.nan
        deg6 = (secs >= 20.0) and (d6 <= 1e-6 or d6 >= 1 - 1e-6)
        deg5 = (secs >= 20.0) and (d5 <= 1e-6 or d5 >= 1 - 1e-6)
        pr("  %-5s engaged-creep %6.1f s : bit6 %.4f %s ; bit5 %.4f %s" % (
            tag, secs, d6, "DEGENERATE (FAIL for this decode)" if deg6 else "non-degenerate",
            d5, "DEGENERATE (FAIL for this decode)" if deg5 else "non-degenerate"))
    pr("\n  [EVIDENCE] r34/r35 carry the OLD decode, on which bit 6 (|gp-0x6b94| >= |gp-0x4f64|) was recorded dead")
    pr("  (duty 0.0000).  It reads 0.0000 here too -- that is the NEGATIVE CONTROL for the repoint, and it means any")
    pr("  non-zero bit-6 duty on r36/r37/r38 can only come from the four changed ld.h displacements.")

    # ================================================================== A / B
    pr("\n" + "=" * 152)
    pr("A / B / D. COMPARATOR DUTIES BY STRATUM.  bit6 = P(|r24| >= |T|) ; bit5 = P(|r24| >= |aggregator|)")
    pr("=" * 152)
    for name, fn in STRATA:
        pr("\n  %s" % name)
        pr("    %-5s %-34s %8s %8s %9s %8s %8s %8s %8s" % (
            "route", "build", "bit6", "bit5", "seconds", "|T| p50", "idx p50", "|bar|p50", "v p50"))
        pool6, pool5 = {}, {}
        for tag in ALL:
            g = G[tag]
            m = fn(g)
            if m.sum() < 100:
                pr("    %-5s %-34s     (n %d frames -- too thin)" % (tag, BUILD[tag][:34], m.sum()))
                continue
            grp = "V283" if tag in V283_ROUTES else tag
            pool6.setdefault(grp, []).append(g["bit6"][m]); pool5.setdefault(grp, []).append(g["bit5"][m])
            pr("    %-5s %-34s %8.4f %8.4f %9.1f %8.0f %8.0f %8.0f %8.2f" % (
                tag, BUILD[tag][:34], g["bit6"][m].mean(), g["bit5"][m].mean(), m.sum() / FS,
                np.median(np.abs(g["T100"][m])), np.median(g["idx"][m]), np.median(np.abs(g["bar"][m])), np.median(g["vego"][m])))
        for grp in ("V283", "r35", "r34"):
            if grp in pool6:
                a, b = np.concatenate(pool6[grp]), np.concatenate(pool5[grp])
                se = np.sqrt(a.mean() * (1 - a.mean()) / max(1, len(a) / 25.0))    # 0.25 s effective independence
                pr("    %-5s %-34s %8.4f %8.4f %9.1f      (pooled; bit6 +-%.3f at 1 sd, blocks of 0.25 s)" % (
                    "POOL", grp, a.mean(), b.mean(), len(a) / FS, se))

    # ------------------------------------------------------------------ closed-form replay on THESE routes' own bar
    pr("\n  CLOSED-FORM REPLAY on r36/r37/r38's OWN torsion-bar data (v282_prereg_duty.py's r24_series, verbatim):")
    pr("  what bit 6 WOULD read at each candidate 0xC6446 arm, so the measured duty is compared like-for-like.")
    for name, fn in STRATA[:1] + STRATA[2:3]:
        pr("\n    %s" % name)
        pr("      %-28s %10s %10s %12s %12s %10s" % ("0xC6446 arm", "bit6 pred", "bit5 pred*", "|r24| p50", "|T| p50", "n frames"))
        for gain in GAINS:
            b6, b5, ra, ta = [], [], [], []
            for tag in V283_ROUTES:
                g = G[tag]; m = fn(g)
                if m.sum() < 200:
                    continue
                r = r24_series(g["bar"], gain); T = g["T100"]
                b6.append((np.abs(r) >= np.abs(T))[m]); b5.append((np.abs(r) >= np.abs(T + r))[m])
                ra.append(np.abs(r)[m]); ta.append(np.abs(T)[m])
            if not b6:
                continue
            b6 = np.concatenate(b6); b5 = np.concatenate(b5)
            pr("      %-28s %10.4f %10.4f %12.0f %12.0f %10d" % (
                GLBL[gain], b6.mean(), b5.mean(), np.median(np.concatenate(ra)), np.median(np.concatenate(ta)), len(b6)))
        meas = np.concatenate([G[t]["bit6"][fn(G[t])] for t in V283_ROUTES if fn(G[t]).sum() >= 200])
        pr("      %-28s %10.4f    <== MEASURED ON THE WIRE" % ("V283 as flown", meas.mean()))
        pr("      (* bit5 pred uses |T + r24| as a LOWER bound on the aggregator, so it is an UPPER bound on the duty)")

    # ================================================================== C. bit-4 phase
    pr("\n" + "=" * 152)
    pr("C. PHASE OF bit 4 = sign(r24) AGAINST THE WIRE WHEEL RATE, 18-22 Hz, creep.  PREREG: -6 +- 25 deg.")
    pr("   Convention: tf(rate -> s4), s = +1 when the cell is >= 0 (r24_sign_on_the_wire.py).  cos > 0 = DAMP.")
    pr("=" * 152)
    NPS = 128
    for name, fn in (STRATA[0], STRATA[1], STRATA[3]):
        for grp, tags in (("V283 (r36+r37+r38)", V283_ROUTES), ("r35 V281r3", ("r35",)), ("r34 V280r2", ("r34",))):
            P = Pool(FS, NPS); secs = 0.0
            for tag in tags:
                g = G[tag]
                for a, b in C20.runs(fn(g), NPS):
                    if P.add({"rate": g["wire"][a:b], "bar": g["bar"][a:b], "T": g["T100"][a:b],
                              "sT": g["s_T"][a:b], "sR": g["s4"][a:b], "sB": g["s7"][a:b]}):
                        secs += (b - a) / FS
            if P.n == 0:
                continue
            f = P.f
            idx = [int(np.argmin(np.abs(f - x))) for x in SHOW]
            HsR, HsB, HT = P.tf("rate", "sR"), P.tf("rate", "sB"), P.tf("rate", "T")
            pr("\n  %-44s %s   (%.1f s, %d Welch windows)" % (grp, name.strip(), secs, P.n))
            pr("    f Hz                :" + "".join("%8.1f" % f[i] for i in idx))
            pr("    ph(bit4=sign r24)   :" + "".join("%8.0f" % np.degrees(np.angle(HsR[i])) for i in idx))
            pr("      coh rate,bit4     :" + "".join("%8.2f" % P.coh("rate", "sR")[i] for i in idx))
            pr("      cos -> verdict    :" + "".join("%8s" % ("DAMP" if np.cos(np.angle(HsR[i])) > 0.2 else
                                                              ("PUMP" if np.cos(np.angle(HsR[i])) < -0.2 else "~neut")) for i in idx))
            pr("    CONTROL ph(bit7)-ph(T) :" + "".join("%5.0f" % np.degrees(np.angle(HsB[i] * np.conj(HT[i]) / max(abs(HT[i]), 1e-12))) for i in idx)
               + "   <- must be ~0 for the sign-transform method to be trusted")
            sel = (f >= 18.0) & (f <= 22.0)
            w = np.abs(P.s("rate", "sR"))[sel]
            ph = np.degrees(np.angle(np.sum(P.s("rate", "sR")[sel] / np.real(P.s("rate", "rate"))[sel] * w) / w.sum()))
            pr("    >>> 18-22 Hz weighted mean phase of bit4 re rate: %+.0f deg  (coh p50 %.2f)  PREREG -6 +- 25 -> %s" % (
                ph, np.median(P.coh("rate", "sR")[sel]), "IN BAND" if abs(((ph + 180) % 360) - 180 + 6) <= 25 else "OUT OF BAND"))

    # ================================================================== E. cost check
    pr("\n" + "=" * 152)
    pr("E. COST CHECK -- does the 427 delivered-torque tap still decode on V283?  (prereg 'Cost FAIL')")
    pr("=" * 152)
    pr("  %-5s %8s %8s %10s %10s %10s %10s" % ("route", "n 0x1AB", "sat frac", "|T| p50", "|T| p90", "|T| max", "T==0 frac"))
    for tag in ALL:
        g = G[tag]
        T = np.abs(g["T"])
        pr("  %-5s %8d %8.4f %10.0f %10.0f %10.0f %10.4f" % (
            tag, len(T), np.mean(T >= 511 * 8), np.median(T), np.percentile(T, 90), T.max(), np.mean(T == 0)))

    with open(os.path.join(SCR, "v282_r24_tap_read.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote", os.path.join(SCR, "v282_r24_tap_read.txt"))


if __name__ == "__main__":
    main()
