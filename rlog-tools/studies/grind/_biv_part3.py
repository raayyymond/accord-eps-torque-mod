# -*- coding: utf-8 -*-
"""Part 3 of b_iv_kappa: why 10-14 Hz is not identified (window length, pool size, where the command
has power), and the incremental arithmetic of the V291 cut with the deadband in place."""
import numpy as np
from scipy import signal as sg

from b_iv_kappa import FS, COH_MIN, WinPool, ang, pr, J
import b_iv_kappa as M
import bof_v282 as BF
import creep20_loop_id as C20
from _biv_part2 import SK, SN, MAIN2, lane_d1k, lane_out

BAND = [7.3, 9.94, 10.0, 11.0, 12.0, 12.85, 13.0, 13.7, 14.0, 16.0, 20.3]


# ---------------------------------------------------------------------- window-length / pool-size scan
def pooled(gs, tags, key, nps, nfft, keys=("bar", "wire", "cmd", "T100")):
    """cross-spectra at one (nperseg, nfft), pooled over runs -- scipy.csd, bof's own Pool."""
    P, secs = BF.pool_stratum(gs, tags, SK[key], keys, nps, nfft)
    return P, secs


def coh_scan(G):
    pr("\n" + "=" * 150)
    pr("4. WHY 10-14 Hz IS NOT IDENTIFIED -- window length, pool size, and where the command has power")
    pr("=" * 150)
    pr("  4.1  DOES A LONGER WINDOW OR A BIGGER POOL LIFT THE COHERENCE?  If the 10-14 Hz hole were")
    pr("       frequency-resolution leakage across a sharp mode, nperseg 256/512 would close it.")
    pr("       coh(rate,bar) = the DIRECT estimate's identification; coh(cmd,rate) = the INSTRUMENT's relevance.")
    pr("  %-17s %-9s %7s %6s | %s" % ("stratum", "nperseg", "secs", "nwin", "coh(rate,bar) / coh(cmd,rate) at f ="))
    pr("  %-17s %-9s %7s %6s | %s" % ("", "", "", "", "  ".join("%10.1f" % f for f in [7.3, 10, 12, 13, 14, 16, 20.3])))
    pr("  " + "-" * 146)
    S = {}
    for key in ("creep_1_3med", "creep_1_6med", "loaded_idx68med", "loaded_any", "all_eng"):
        for nps, nfft in ((128, 512), (256, 1024), (512, 2048)):
            P, secs = pooled(G, BF.V282_ROUTES, key, nps, nfft)
            if P.n < 6:
                continue
            cells = []
            for f0 in [7.3, 10.0, 12.0, 13.0, 14.0, 16.0, 20.3]:
                _, crb, _ = P.bavg("wire", "bar", f0)
                _, ccr, _ = P.bavg("cmd", "wire", f0)
                cells.append("%4.2f/%4.2f" % (crb, ccr))
                S["%s|%d|%g" % (key, nps, f0)] = dict(coh_rb=float(crb), coh_cr=float(ccr),
                                                      nwin=int(P.n), secs=float(secs))
            pr("  %-17s %-9s %7.1f %6d | %s" % (key, "%d/%d" % (nps, nfft), secs, P.n,
                                                "  ".join("%10s" % c for c in cells)))
        pr("  " + "-" * 146)
    J["coh_scan"] = S

    pr("")
    pr("  4.2  WHERE THE 0xE4 COMMAND HAS POWER.  Normalised PSD (each signal's own 3-30 Hz power = 1),")
    pr("       so the shapes are comparable.  An instrument with no power at f cannot identify f.")
    pr("  %-17s %6s | %8s %8s %8s %8s | %s" % ("stratum", "f", "cmd", "bar", "rate", "T427", "cmd share vs its 18-22 Hz peak"))
    pr("  " + "-" * 116)
    PS = {}
    for key in MAIN2:
        P, secs = pooled(G, BF.V282_ROUTES, key, 128, 512)
        f = P.f
        sel = (f >= 3.0) & (f <= 30.0)
        pw = {}
        for nm in ("cmd", "bar", "wire", "T100"):
            p = np.real(P.s(nm, nm))
            pw[nm] = p / p[sel].sum()
        cpk = max(pw["cmd"][(f >= 18) & (f <= 22)])
        for f0 in [3.9, 5.0, 7.3, 10.0, 12.0, 13.0, 14.0, 16.0, 18.0, 20.3, 25.0]:
            i = int(np.argmin(np.abs(f - f0)))
            pr("  %-17s %6.1f | %8.4f %8.4f %8.4f %8.4f | x%.3f"
               % (key, f0, pw["cmd"][i], pw["bar"][i], pw["wire"][i], pw["T100"][i], pw["cmd"][i] / cpk))
            PS["%s|%g" % (key, f0)] = dict(cmd=float(pw["cmd"][i]), bar=float(pw["bar"][i]),
                                           rate=float(pw["wire"][i]), T=float(pw["T100"][i]),
                                           cmd_vs_peak=float(pw["cmd"][i] / cpk))
        pr("  " + "-" * 116)
    J["psd"] = PS


# ---------------------------------------------------------------------- the V291 cut, byte-exactly
def v291_increment(G):
    pr("\n" + "=" * 150)
    pr("5. Q2 -- THE INCREMENTAL ARITHMETIC OF THE V291 CUT, WITH THE DEADBAND IN PLACE")
    pr("=" * 150)
    pr("  5.1  THE DEADBAND's INCREMENTAL GAIN.  For a small perturbation riding on a large broadband")
    pr("       signal, a symmetric deadband's incremental (dual-input describing-function) gain is")
    pr("       simply P(|s| > db) -- it passes the perturbation on every tick it is out of the dead zone.")
    pr("       Measured at the FLOWN arm on the 1 kHz lane state, not on the 100 Hz decimation.")
    pr("  %-6s %-17s | %9s %9s | %9s %9s | %9s"
       % ("route", "stratum", "P(|s|>3)", "@4725", "N_df A=ring", "A=p50|s|", "d ln gain / d ln arm"))
    pr("  " + "-" * 106)
    DB = {}
    for t in BF.V282_ROUTES:
        g = G[t]
        d1k = lane_d1k(g["bar"])
        # 1 kHz mask: repeat the 100 Hz stratum mask 10x (the mask is a slow regime flag)
        for key in ("creep_1_3med", "loaded_idx68med", "highway", "all_eng"):
            m = SK[key](g)
            if m.sum() < 200:
                continue
            m1k = np.repeat(m, 10)[:len(d1k)]
            s5 = np.trunc(d1k[m1k] * 5244.0 / 1024.0)
            s4 = np.trunc(d1k[m1k] * 4725.0 / 1024.0)
            p5, p4 = float(np.mean(np.abs(s5) > 3)), float(np.mean(np.abs(s4) > 3))
            A = float(np.median(np.abs(s5[np.abs(s5) > 0]))) if (np.abs(s5) > 0).any() else 0.0

            def ndf(a, db=3.0):
                if a <= db:
                    return 0.0
                r = db / a
                return float(1 - (2 / np.pi) * (np.arcsin(r) + r * np.sqrt(1 - r * r)))
            # sinusoidal describing function at the 18-22 Hz ring amplitude of s.  Band-pass the WHOLE
            # series first, then select -- filtering a masked (discontinuous) array manufactures edges.
            sfull = lane_out(d1k, len(g["bar"]), 5244.0, db=0.0)
            bp = C20.bandpass(sfull, 18.0, 22.0, FS)
            ring = float(np.sqrt(2.0) * bp[m].std())
            # local slope of the delivered incremental gain wrt the arm
            eps = 0.02
            gp_ = np.mean(np.abs(np.trunc(d1k[m1k] * 5244.0 * (1 + eps) / 1024.0)) > 3)
            gm_ = np.mean(np.abs(np.trunc(d1k[m1k] * 5244.0 * (1 - eps) / 1024.0)) > 3)
            slope = 1.0 + (np.log(gp_) - np.log(gm_)) / (2 * eps)
            pr("  %-6s %-17s | %9.4f %9.4f | %9.4f %9.4f | %9.4f"
               % (t, key, p5, p4, ndf(ring), ndf(A), slope))
            DB["%s|%s" % (t, key)] = dict(p_out5244=p5, p_out4725=p4, ndf_ring=ndf(ring), ndf_p50=ndf(A),
                                          ring_amp=ring, p50_abs_s=A, dlng_dlnarm=float(slope))
    J["Q2_incremental"] = DB

    pr("")
    pr("  5.2  THE EFFECTIVE CUT.  k_nominal = 4725/5244 = %.6f.  With the deadband, the delivered" % (4725 / 5244))
    pr("       incremental gain scales by k_eff = k * P(|s4725|>3)/P(|s5244|>3).")
    ks = [DB[q]["p_out4725"] / DB[q]["p_out5244"] for q in DB]
    pr("       P ratio over the 8 cells: %.4f .. %.4f (median %.4f)  ->  k_eff %.4f .. %.4f (median %.4f)"
       % (min(ks), max(ks), float(np.median(ks)),
          (4725 / 5244) * min(ks), (4725 / 5244) * max(ks), (4725 / 5244) * float(np.median(ks))))
    J["Q2_keff"] = dict(k_nom=4725 / 5244, pratio_min=float(min(ks)), pratio_max=float(max(ks)),
                        pratio_med=float(np.median(ks)),
                        keff_min=(4725 / 5244) * float(min(ks)), keff_max=(4725 / 5244) * float(max(ks)),
                        keff_med=(4725 / 5244) * float(np.median(ks)))


# ---------------------------------------------------------------------- the arm-selector check
def arm_selector(G):
    import struct
    pr("\n" + "=" * 150)
    pr("6. Q2 -- A HYPOTHESIS I RAISED AND THEN FALSIFIED MYSELF: IS THE 5244 RUNG EVEN SELECTED?")
    pr("=" * 150)
    pr("  The implied arm 2268-2747 lands inside the lane's OWN alternative rungs -- Honda's fixed 2048")
    pr("  (0xC6440) and the mode-10 LERP surface (BUILD-LINEAGE-PART1: 'the LERP at grind #1's point' =")
    pr("  2622, and 5244 = 2.00 x 2622).  If the 5244 rung were NOT selected, V291's cut would be INERT,")
    pr("  not merely small.  The selector is gated by byte 0x3AA96.")
    img = open(BF.V282_IMG, "rb").read()
    gate = img[0x3AA96]
    pr("  READ FROM THE V282 IMAGE: 0x3AA96 = 0x%02X   (0xFB = repointed to STEER_CONTROL_ACTIVE since" % gate)
    pr("  V104 -> the 5244 rung IS taken while laterally engaged;  0xC5 = Honda gateless -> gp-0x683c has")
    pr("  ZERO writers image-wide and the 5244 load NEVER EXECUTES -- BUILD-LINEAGE-PART1, the 0xC6444 cell.)")
    for nm, a in (("0xC6440 Honda fixed", 0xC6440), ("0xC6442 latch arm", 0xC6442),
                  ("0xC6446 ENGAGED arm", 0xC6446), ("0xC61F6 deadband", 0xC61F6)):
        pr("      %-22s = %d" % (nm, struct.unpack_from("<H", img, a)[0]))
    pr("  => the strata here are ALL `eng` (0x18F SCA & 0xE4 STEER_REQUEST), so the arm IS 5244.")
    pr("  *** MY HYPOTHESIS IS FALSIFIED. Reported because a reader deserves the failed branch too. ***")
    J["Q2_gate"] = dict(gate_byte=int(gate), arm_live=bool(gate == 0xFB),
                        cells={nm: int(struct.unpack_from("<H", img, a)[0])
                               for nm, a in (("C6440", 0xC6440), ("C6442", 0xC6442),
                                             ("C6446", 0xC6446), ("C61F6", 0xC61F6))})
