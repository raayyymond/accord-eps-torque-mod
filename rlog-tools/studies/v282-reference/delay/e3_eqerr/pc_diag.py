"""Where does the positive control's +8..+12 ms bias come from?  Peel it off one cause at a time.

Causes tested, in order:
  ZOH      the CAN command is a zero-order hold; the estimator resamples it by LINEAR interpolation.
           ZOH(s) = linear(s - T/2) exactly in phase (sinc vs sinc^2 differ in magnitude only), so this
           must contribute exactly +T/2 = +4.955 ms with the measured 9.91 ms send interval.
  FRICTION Coulomb friction + stick: the model term F*sign(rate) is wrong during a dwell.
  QUANT    angle 0.1 deg / rate 1 deg/s rounding (errors-in-variables on acc).
  DWELL    the |rate| >= dwell row mask.
Each row prints the recovered D for true D = 30 and 60 ms.
"""
import sys, json
from pathlib import Path
import numpy as np
sys.path.insert(0, str(Path(__file__).resolve().parent))
import eqerr as E

RK = "00000075--6c8687d5bd"
T0 = E.engaged_start(RK)
rows = []


def run(nm, *, J=8e-5, b=6e-4, F=0.020, kl=3.0, stick=True, quant=True, dwell=2.0,
        zoh=False, band=(0.3, 8.0), dt=0.001):
    E.BAND = band
    sos = E.make_L(band)
    o = [nm]
    for Dt in (30, 60):
        sa, sr, ts, info = E.simulate(RK, Dt, J, b, F, klevel=kl, t_from=T0, stick=stick, dt=dt, quant=quant)
        bl = E.route_blocks(RK, sos, synth=(sa, sr, ts), dwell=dwell, band=band, interp_cmd=not zoh)
        r = E.fit_report(bl, nboot=120)
        o.append((r["D"] - Dt, r["D"], r["R2"], r["beta"], info["stick_frac"], r["n_blocks"]))
        del bl
    rows.append(o)
    a, c = o[1], o[2]
    print(f"  {nm:34s} err {a[0]:+6.2f} / {c[0]:+6.2f} ms   D {a[1]:6.2f}/{c[1]:6.2f}  R2 {a[2]:.3f}  "
          f"J {a[3][0]:.2e} b {a[3][1]:+.2e} gk {a[3][2]:+.2f} F {a[3][3]:+.4f}  stick {a[4]*100:.0f}%  blk {a[5]}",
          flush=True)


# a plant with NO friction and NO quantisation -- only the ZOH/interp mismatch can bias this
run("linear plant, no quant, interp", F=0.0, stick=False, quant=False, dwell=0.0)
run("linear plant, no quant, ZOH", F=0.0, stick=False, quant=False, dwell=0.0, zoh=True)
run("linear plant, QUANT, ZOH", F=0.0, stick=False, quant=True, dwell=0.0, zoh=True)
run("+friction no stick, QUANT, ZOH", F=0.020, stick=False, quant=True, dwell=2.0, zoh=True)
run("+stick, QUANT, ZOH, dwell2", F=0.020, stick=True, quant=True, dwell=2.0, zoh=True)
run("+stick, QUANT, ZOH, dwell0", F=0.020, stick=True, quant=True, dwell=0.0, zoh=True)
run("+stick, QUANT, ZOH, dwell4", F=0.020, stick=True, quant=True, dwell=4.0, zoh=True)
run("full, interp (as shipped)", F=0.020, stick=True, quant=True, dwell=2.0, zoh=False)
Path(Path(__file__).resolve().parent / "pc_diag.json").write_text(
    json.dumps([[r[0], r[1][:3], r[2][:3]] for r in rows], indent=1, default=float))
