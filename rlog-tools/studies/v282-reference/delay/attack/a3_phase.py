"""ADVERSARY a3: do the IMPLICATIONS follow from the delay?

Uses MY measured chain, not the adjudication's parametric one:
  D_loop(f) = D_ctl(11.0, measured a1) + pd_B(f) (measured a2 FIR, sendcan -> 427 tap arrival)
              + 2.65 ms (0x14A batch stamp -> carState publish, measured a1) + X
  actuation magnitude roll-off |H_B(f)|/DC also taken from the measured FIR (not from an assumed 5 Hz pole).
Delivered damping fraction of AccordRateLoopGain:
  m(f) = |H_B(f)| * |F_rc(f)| * cos( 2*pi*f*D_loop(f) + atan(2*pi*f*RC) )
Then: the damping/pumping boundary, the rate loop's -180 deg crossing and |L| there (the fork comment's
claim), at the fork's own identified plant.
"""
import json
from pathlib import Path
import numpy as np

HERE = Path(__file__).resolve().parent
FS = np.array([1.0, 1.8, 2.5, 3.5, 5.0, 6.0])
RC = 0.01
J = 8e-5
HOLD_V_BP = [2.0, 4.0, 6.0, 8.0, 10.0, 12.5, 15.0, 17.5, 20.0, 23.0, 28.0]
HOLD_K_V = [0.0021, 0.0028, 0.0044, 0.0052, 0.0074, 0.0092, 0.0095, 0.0103, 0.0116, 0.0133, 0.0160]
D_CTL = 10.90
BATCH2CS = 2.65
TORQUE = ["0000006c", "0000006d", "0000006e", "00000076", "00000075"]


def measured():
    R = json.load(open(HERE / "out" / "a2_all.json"))
    rows = [r for r in R if r["tag"].split()[0] in TORQUE and r["r2"] > 0.5]  # r2 filter drops the V282 route (same 8-char prefix)
    out = {}
    for lam in sorted({r["lam_over_s"] for r in rows}):
        sel = [r for r in rows if r["lam_over_s"] == lam]
        pd = np.array([[r[f"pd_{f}"] for f in FS] for r in sel])
        mg = np.array([[r[f"mag_{f}"] for f in FS] for r in sel])
        out[lam] = (np.median(pd, 0), np.median(mg, 0), pd, mg, [r["tag"][:8] for r in sel])
    return out


def m_of(pdB, magB, X, f=FS, rc=RC):
    Dl = (D_CTL + pdB + BATCH2CS + X) * 1e-3
    phi = 2 * np.pi * f * Dl + np.arctan(2 * np.pi * f * rc)
    Frc = 1 / np.sqrt(1 + (2 * np.pi * f * rc) ** 2)
    return Dl * 1e3, np.degrees(phi), magB * Frc * np.cos(phi)


def boundary(pdB_f, magB_f, X, rc=RC):
    """frequency where the delivered damping changes sign (phase = 90 deg), pdB interpolated in f"""
    fg = np.linspace(1.0, 10.0, 2000)
    pd = np.interp(fg, FS, pdB_f)
    Dl = (D_CTL + pd + BATCH2CS + X) * 1e-3
    phi = 2 * np.pi * fg * Dl + np.arctan(2 * np.pi * fg * rc)
    i = np.argmax(phi > np.pi / 2)
    return fg[i]


def rate_loop_margin(v, gain, pdB_f, magB_f, X, rc=RC):
    """open-loop |L| of the rate loop alone, and the -180 deg crossing, on the fork's identified plant"""
    k = np.interp(v, HOLD_V_BP, HOLD_K_V)
    b = 6e-4
    fg = np.linspace(1.0, 12.0, 4000)
    w = 2 * np.pi * fg
    pd = np.interp(fg, FS, pdB_f); mg = np.interp(fg, FS, magB_f)
    Dl = (D_CTL + pd + BATCH2CS + X) * 1e-3
    Prate = (1j * w) / (J * (1j * w) ** 2 + b * (1j * w) + k)          # deg/s per torque
    Frc = 1 / (1 + 1j * w * rc)
    L = gain * mg * np.exp(-1j * w * Dl) * Frc * Prate
    ph = np.unwrap(np.angle(L))
    i = np.argmax(ph < -np.pi)
    return fg[i], abs(L[i]), 1.0 / max(abs(L[i]), 1e-9)


def main():
    M = measured()
    for lam, (pdm, mgm, pd, mg, tags) in M.items():
        print(f"\n### measured B link, lam/scale {lam:.0e}, {len(tags)} torque routes {tags}")
        print("    f Hz                  " + "".join(f"{f:8.1f}" for f in FS))
        print("    pd_B median ms        " + "".join(f"{x:8.2f}" for x in pdm)
              + f"   (per-route spread at 2.5 Hz: {pd[:,2].min():.2f}-{pd[:,2].max():.2f})")
        print("    |H_B|/DC median       " + "".join(f"{x:8.3f}" for x in mgm))
        for X in (0.0, 12.0, 18.0):
            Dl, phi, m = m_of(pdm, mgm, X)
            print(f"    X={X:4.0f} ms  D_loop ms " + "".join(f"{x:8.1f}" for x in Dl))
            print(f"              phi deg   " + "".join(f"{x:8.1f}" for x in phi))
            print(f"              m         " + "".join(f"{x:+8.3f}" for x in m)
                  + f"   damps below {boundary(pdm, mgm, X):.2f} Hz")
    pdm, mgm = M[max(M)][0], M[max(M)][1]
    print("\n### the orchestrator's premise for comparison: a PURE 30 ms D_loop, no actuation roll-off")
    Dl, phi, m = m_of(np.full(len(FS), 30.0 - D_CTL - BATCH2CS), np.ones(len(FS)), 0.0)
    print("              m         " + "".join(f"{x:+8.3f}" for x in m)
          + f"   damps below {boundary(np.full(len(FS),30.0-D_CTL-BATCH2CS), np.ones(len(FS)), 0.0):.2f} Hz")

    print("\n### rate loop alone: -180 deg crossing and |L| there (fork comment: '3.5-4 Hz; at 0.0006 it is 0.5, at 0.0012 it would cross')")
    for X in (0.0, 18.0):
        for g in (0.0006, 0.0012):
            row = []
            for v in (3.0, 6.0, 8.0, 12.0):
                f180, L180, gm = rate_loop_margin(v, g, pdm, mgm, X)
                row.append(f"v{v:4.0f}: {f180:4.2f} Hz |L| {L180:5.3f} GM {gm:5.2f}")
            print(f"  X={X:4.0f} gain {g:.4f}  " + " | ".join(row))
    print("\n### RC sensitivity of the delivered damping at 2.5 Hz (X=0 / X=18)")
    for rc in (0.0, 0.005, 0.01, 0.02, 0.03):
        r = []
        for X in (0.0, 18.0):
            _, _, m = m_of(pdm, mgm, X, rc=rc)
            r.append(f"m(2.5)={m[2]:+.3f} m(3.5)={m[3]:+.3f} m(5)={m[4]:+.3f}")
        print(f"  RC={rc:.3f}: " + "  ||  ".join(r))


if __name__ == "__main__":
    main()
