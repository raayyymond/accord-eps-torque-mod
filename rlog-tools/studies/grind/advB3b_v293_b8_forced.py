# -*- coding: utf-8 -*-
"""advB3b_v293_b8_forced.py -- ADVERSARY B, criterion B8: the FORCED 18-22 Hz response.

agent `advB3b`, 2026-09-13.  ANALYSIS ONLY.

B8 (reported, not gated): "the forced 18-22 Hz response to the command's own 20 Hz content (the
camera comb at lock 0.50) -- with the loop open this is the residual the operator may still feel;
size it against V282's ring so the null sentence can be written."

SECOND METHOD, independent of the replay.  With the LKAS loop open the delivered torque is a
memoryless function of the command alone:  T = clamp(-( clamp(fade*(clamp(32*sp*Kp>>8)) >>8) * gain
)>>15).  Below the P rail that chain is LINEAR in the demand index with a slope this file reads
from the BUILT IMAGE by finite difference.  So the delivered 18-22 Hz ring under V293 is just

    A_T(18-22)  =  slope[counts per idx]  x  A_idx(18-22)

with A_idx measured directly off the wire.  No plant, no inversion, no marched simulation.  It is
then compared with the design's marched replay (s2 TASK 2C: 3.49 counts) as a cross-check, and with
V282's own measured delivered ring.

Run: python advB3b_v293_b8_forced.py
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUTDIR = r"C:\Users\dudei\Desktop\Projects\accord-eps-torque-mod\_scratch\advB3b"
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import creep20_loop_id as C20                       # noqa: E402
import grind_incident_r35 as GI                     # noqa: E402
import v293_lib as L                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS, CPD = 100.0, 8.0
OUT = []


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def band_amp(x, lo, hi, fs=FS):
    from scipy.signal import butter, filtfilt
    x = np.asarray(x, float)
    if len(x) < 40:
        return np.nan
    b, a = butter(3, [lo / (fs / 2), hi / (fs / 2)], btype="band")
    y = filtfilt(b, a, x - x.mean())
    return float(np.sqrt(np.mean(y ** 2)) * np.sqrt(2.0))


def main():
    c282 = L.read_cells(L.IMG282)
    cTM = L.torque_mode(c282, kp=120)
    pr("=" * 122)
    pr("ADVERSARY B -- B8: the FORCED 18-22 Hz response with the loop OPEN.  agent advB3b, 2026-09-13")
    pr("=" * 122)

    # ---- the delivered surface and its LOCAL slope, read from the BUILT cells -------------------
    idx = np.arange(0, 241, 1.0)
    T293 = np.abs(L.surface(cTM, idx, fb=0.0, kd=0, fade=254)["T"])
    T282 = np.abs(L.surface(c282, idx, fb=0.0, kd=128, fade=254)["T"])

    def local_slope(T, i0, h=6.0):
        a = max(0.0, i0 - h)
        b = min(240.0, i0 + h)
        return float((np.interp(b, idx, T) - np.interp(a, idx, T)) / (b - a))

    # ---- the OUTPUT LAG, read from the cells: s[n] = (a*s[n-1] + b*S[n])/1024, y = (s+s')>>5 ----
    a_lag, b_lag = float(c282["lag_a"]), float(c282["lag_b"])
    pr("  output lag from the image: lag_a %.0f lag_b %.0f  (byte-identical V282/V293)" % (a_lag, b_lag))

    def lag_rel(f, fs=1000.0):
        """|H(f)| / |H(0)| of the one-pole output lag; the (s+s')>>5 sum is frequency-flat here."""
        al = a_lag / 1024.0
        z = np.exp(-2j * np.pi * f / fs)
        return float(abs((1.0 - al) / (1.0 - al * z)))

    pr("  its 20 Hz attenuation relative to DC: x%.3f  (this is why the DC slope alone over-reads)"
       % lag_rel(20.0))
    pr("  NOTE: V282's P clamp first binds at idx 116, so a chord slope over 0..200 is NOT its")
    pr("  sub-rail slope.  The slope below is taken LOCALLY at each window's own median index.")
    pr()
    pr("  %-5s %7s %11s %9s %9s %9s %9s" %
       ("route", "idx p50", "A_idx 18-22", "sl_293", "sl_282", "A_T 293", "A_T 282cmd"))

    res = {}
    for tag in ("r39", "r6c", "r35"):
        try:
            g = C20.load(tag)
        except Exception as e:                                    # noqa: BLE001
            pr("  !! %s unavailable: %s" % (tag, e))
            continue
        c = GI.read_cells(L.IMG282)
        idx_live, sgn = GI.demand_live(np.round(g["cmd"]), g["bar"], c)
        eng = np.asarray(g["eng"], bool)
        wire = np.asarray(g["wire"], float)
        # the 10 loudest 3 s engaged ring windows, ranked by the wire's own 18-22 Hz amplitude
        half = 150
        cand = []
        for p0 in range(half + 20, len(wire) - half - 20, 50):
            if not eng[p0 - half:p0 + half].all():
                continue
            cand.append((band_amp(wire[p0 - half:p0 + half], 18.0, 22.0), p0))
        cand.sort(reverse=True)
        used, wins = [], []
        for amp, p0 in cand:
            if any(abs(p0 - q) < 2 * half for q in used):
                continue
            used.append(p0)
            wins.append((p0, amp))
            if len(wins) >= 10:
                break
        sgn_cmd = np.asarray(sgn, float) * np.asarray(idx_live, float)   # the SIGNED demand index
        ai = float(np.median([band_amp(sgn_cmd[p - half:p + half], 18.0, 22.0) for p, _ in wins]))
        i50 = float(np.median([np.median(np.abs(idx_live[p - half:p + half])) for p, _ in wins]))
        aw = float(np.median([a for _, a in wins]))
        k20 = lag_rel(20.0)
        s93 = local_slope(T293, i50)
        s82 = local_slope(T282, i50)
        at293 = ai * s93 * k20
        at282 = ai * s82 * k20
        res[tag] = dict(A_idx=ai, idx_p50=i50, A_wire=aw, A_T293=at293, A_T282cmd=at282,
                        slope293=s93, slope282=s82, lag20=k20)
        pr("  %-5s %7.1f %11.3f %9.3f %9.3f %9.2f %9.2f"
           % (tag, i50, ai, s93, s82, at293, at282))
    pr()
    pr("  CROSS-CHECK against the design's marched replay (v293_s2 TASK 2C, r39):")
    pr("    s2:  V282 total delivered 18-22 Hz 63.27 counts ; V282 CMD leg alone 10.99 ;")
    pr("         V293 delivered 18-22 Hz 3.49 counts = x0.055 of V282's total.")
    if "r39" in res:
        pr("    this file, r39: V293 %.2f counts, V282's COMMAND leg %.2f counts."
           % (res["r39"]["A_T293"], res["r39"]["A_T282cmd"]))
        pr("    POSITIVE CONTROL -- the V282 command leg is the one number both methods compute the")
        pr("    same way, and s2 reads it at 10.99.  This file reads %.2f  (x%.2f)."
           % (res["r39"]["A_T282cmd"], res["r39"]["A_T282cmd"] / 10.99))
        pr("    V293's command leg as a fraction of V282's TOTAL delivered ring (63.27): x%.3f"
           % (res["r39"]["A_T293"] / 63.27))
    pr()
    pr("  THE NULL SENTENCE THIS LICENSES, sized:")
    pr("    With the loop open the delivered 18-22 Hz torque is the COMMAND's own content times a")
    pr("    fixed slope.  It cannot grow with wheel motion, cannot ring, and has no pole.  If the")
    pr("    wheel's 18-22 Hz ring is UNCHANGED on the car while the within-frame identity")
    pr("    T = f(cmd)*taper holds on every engaged frame, the 20 Hz object is not the LKAS loop's.")
    json.dump(res, open(os.path.join(OUTDIR, "b8_forced.json"), "w"), indent=1)
    os.makedirs(OUTDIR, exist_ok=True)
    open(os.path.join(OUTDIR, "b8_forced.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")


if __name__ == "__main__":
    main()
