# -*- coding: utf-8 -*-
"""v293_s5_ringdown.py -- the MATCHED free ring-down, done correctly for an OPEN loop.

Agent `tmdesign`, 2026-09-13.  ANALYSIS ONLY.

🛑 A METRIC OF MINE THAT FAILED, AND WHY -- recorded rather than quietly swapped.
`v292_replay_lib.kick_response` injects the kick into the residual disturbance `d`, which the replay
adds to the wire AFTER the plant.  In a CLOSED loop that is fine: the kick reaches the electronics
through the feedback, comes back as torque, and rings the plant.  In torque mode the LKAS feedback is
identically zero, so the kick NEVER reaches the torque at all and the incremental wire response is
literally the impulse itself -- no ring, no decay, r2 = 0.02, and a fitted "half-life" that is just
the fitting window's ceiling (205 ms on every fit).  The v293_s2_replay TASK 2B table is therefore
VOID and is superseded by this file.

THE CORRECTED MEASUREMENT.  Inject the kick at the PLANT INPUT (`extra_T`), where a real road or
driver impulse acts on the wheel, and take the difference of two closed byte-exact runs sharing d, the
command, the plant and the operating point.  That excites the plant's own mode in BOTH arms and is the
matched comparison the V292 replay intended.

CONTROL: the V282 arm must still reproduce its published number (free t1/2 108-197 ms, ratio work in
V292-REPLAY-PREDICTION section 4.1).  If the corrected injection changes V282's own ring-down beyond
that range the method is wrong, not the result.

Run:  python v293_s5_ringdown.py
"""
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
SCR = os.path.join(HERE, "_scratch")
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import burst_echo_sizing as ES                      # noqa: E402
import design290b_candidates as D                   # noqa: E402
import adv_v290_physics as A                        # noqa: E402
import v292_replay_lib as R                         # noqa: E402
import v292_replay_s2 as S2                         # noqa: E402
import v293_lib as L                                # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
OUT = []
NAMED = [225, 215, 38, 117]


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def kick_at_plant(c, W, pl, d, k0, amp, kd, fb, ef=False):
    """difference of two closed runs whose plant input differs by one impulse at k0."""
    ex0 = np.zeros(W["n"])
    ex1 = np.zeros(W["n"])
    ex1[k0] = amp
    base = R.closed_run(R.Elec(c, fb=fb, ef=ef, two_floor=True, kd=kd), R.PlantIIR(pl), W, d, extra_T=ex0)
    pert = R.closed_run(R.Elec(c, fb=fb, ef=ef, two_floor=True, kd=kd), R.PlantIIR(pl), W, d, extra_T=ex1)
    return pert["wire"] - base["wire"], pert["T"] - base["T"]


def main():
    fam, stable, sample = S2.load_family()
    byid = {f["id"]: f for f in fam}
    named = [byid[i] for i in NAMED]
    c282 = L.read_cells(L.IMG282)
    c292 = L.read_cells(L.IMG292)
    c293 = L.torque_mode(c282, kp=119)

    pr("=" * 122)
    pr("THE MATCHED FREE RING-DOWN, KICK AT THE PLANT INPUT     tmdesign 2026-09-13   ANALYSIS ONLY")
    pr("=" * 122)
    pr("Supersedes v293_s2_replay TASK 2B, whose kick was injected into the wire disturbance and")
    pr("therefore could not reach an OPEN lane's torque at all (r2 0.02, ratio pinned at the window).")
    pr("")

    g = S2.route("r39", (18.0, 22.0))
    wins = ES.loud_windows(g)
    pr("r39, the 10 loudest engaged windows.  Kick amplitude 512 torque counts at the plant input.")
    pr("")
    pr("  %-8s | %-24s | %-36s" % ("fit", "LINEAR closed-loop pole", "MATCHED free ring-down on the WHEEL"))
    pr("  %-8s | %11s %11s | %9s %9s %9s %7s %6s" %
       ("", "V282 f/z", "V293 f/z", "V282", "V292", "V293", "93/82", "r2 93"))
    rows = {}
    for f in named:
        pl = D.mkplant(f)
        e2 = A.Blocks(dict(c282, fb_a=R.V282_FB[0], fb_b=R.V282_FB[1]), False, 0.0)
        e9 = L.BlocksTM(c293, notch=False, g=0.0, kp=119, kd=0.0, fb_zero=True)
        f2, z2 = A.mode_pole(e2, pl, 10, 32)
        f9, z9 = A.mode_pole(e9, pl, 10, 32)
        if not np.isfinite(f9):
            w = np.roots(pl.den[::-1]); w = w[np.abs(w) > 1e-12]
            s = np.log(1.0 / w) * A.FS
            ff = np.abs(s.imag) / (2 * np.pi); zz = -s.real / np.abs(s)
            m = (ff >= 10) & (ff <= 32)
            if m.any():
                k = int(np.argmin(zz[m])); f9, z9 = float(ff[m][k]), float(zz[m][k])
        acc = []
        for (a0, b0, p0) in wins[:6]:
            W2 = R.prep_window(g, a0, b0, c282)
            W9 = R.prep_window(g, a0, b0, c293)
            d, _ = R.invert_d(R.Elec(c282, fb=R.V282_FB, ef=False, two_floor=True), R.PlantIIR(pl), W2, W2["wire1k"])
            k0 = (p0 - (a0 - 50)) * 10
            dw2, _ = kick_at_plant(c282, W2, pl, d, k0, 512.0, 128.0, R.V282_FB)
            dw92, _ = kick_at_plant(c292, W2, pl, d, k0, 512.0, 128.0, R.V292_FB, ef=True)
            dw9, _ = kick_at_plant(c293, W9, pl, d, k0, 512.0, 0.0, R.V282_FB)
            h2 = R.decay_halflife(dw2, k0)
            hm = R.decay_halflife(dw92, k0)
            h9 = R.decay_halflife(dw9, k0)
            acc.append((h2[0], hm[0], h9[0], h9[0] / h2[0] if h2[0] > 0 else np.nan, h2[2], h9[2]))
        a = np.array(acc, float)
        rows[f["id"]] = a
        pr("  %-8s | %5.2f/%.4f %5.2f/%.4f | %7.0f m %7.0f m %7.0f m %7.3f %6.2f" %
           (f["id"], f2, z2, f9, z9, np.nanmedian(a[:, 0]), np.nanmedian(a[:, 1]),
            np.nanmedian(a[:, 2]), np.nanmedian(a[:, 3]), np.nanmedian(a[:, 5])))
    pr("")
    pr("  CONTROL: V282's own free ring-down must land in the published 108-197 ms band")
    v282h = np.concatenate([rows[i][:, 0] for i in NAMED])
    v292h = np.concatenate([rows[i][:, 1] for i in NAMED])
    pr("    V282 pooled median %.0f ms (p10 %.0f, p90 %.0f)  -- published 108-197 ms across the same fits"
       % (np.nanmedian(v282h), np.nanpercentile(v282h, 10), np.nanpercentile(v282h, 90)))
    pr("    V292 pooled median %.0f ms -- published 39-71 ms" % np.nanmedian(v292h))
    v293h = np.concatenate([rows[i][:, 2] for i in NAMED])
    pr("    V293 pooled median %.0f ms   ratio to V282 x%.3f" % (np.nanmedian(v293h), np.nanmedian(v293h) / np.nanmedian(v282h)))
    pr("")
    pr("  r2 is the log-envelope fit quality; a low r2 means there is no exponential ring to fit, which")
    pr("  for an OPEN lane is itself the finding rather than a failure of the fit.")

    open(os.path.join(SCR, "v293_s5_ringdown.txt"), "w", encoding="utf-8").write("\n".join(OUT) + "\n")
    pr("")
    pr("wrote _scratch/v293_s5_ringdown.txt")


if __name__ == "__main__":
    os.makedirs(SCR, exist_ok=True)
    main()
