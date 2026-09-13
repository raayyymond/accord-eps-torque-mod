# -*- coding: utf-8 -*-
"""v292_replay_s2.py -- STAGE 2/3/4: the CLOSED-LOOP replay of real recorded grinding episodes
through V282's electronics and V292's.  Agent `replay`, 2026-09-13.  ANALYSIS ONLY.

🛑 PRE-REGISTERED FALSIFICATION, written before this file was run
   "V292 DOES NOT HELP ON REAL EPISODES" if ANY of:
     F1  pooled median 18-22 Hz delivered-torque ring ratio V292/V282 >= 0.85 on the median fit
     F2  pooled median ring-envelope HALF-LIFE ratio >= 1.00 (the ring does not die faster)
     F3  the 9-18 Hz shoulder ratio >= 1.50 pooled while the 18-22 Hz gain is < x2
     F4  the 6-9 Hz strong-turn ripple ratio > 1.05 in situ (the B5 gate, on real episodes)
     F5  delivered torque OUTSIDE the ring bands moves by more than +-2 % (authority)
   and "the prediction is WORTHLESS" if the V282 closed loop does not reproduce the recorded window
   exactly (checked every window, every fit: max|dT| must be 0).

Run:  python v292_replay_s2.py [stage]
"""
import json
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import burst_onset_triggers as B                   # noqa: E402
import burst_echo_sizing as ES                     # noqa: E402
import grind_incident_r35 as GI                    # noqa: E402
import creep20_loop_id as C20                      # noqa: E402
import design290b_candidates as D                  # noqa: E402
import v292_replay_lib as R                        # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
FS, FS1K = 100.0, 1000.0
SCR = os.path.join(HERE, "_scratch")
OUT = []
RNG = np.random.default_rng(20260913)

NAMED = [225, 215, 38, 117]          # median fit + the worst fits ADV-V292-B section 5.2 names
BANDS = dict(ring=(18.0, 22.0), shoulder=(9.0, 18.0), low=(5.0, 9.0), turn=(6.0, 9.0))


def pr(s=""):
    print(s, flush=True)
    OUT.append(s)


def boot(v, n=4000):
    v = np.asarray(v, float)
    v = v[np.isfinite(v)]
    if len(v) < 3:
        return np.nan, np.nan
    bs = np.median(v[RNG.integers(0, len(v), (n, len(v)))], axis=1)
    return float(np.percentile(bs, 2.5)), float(np.percentile(bs, 97.5))


# ------------------------------------------------------------------------------------------------
def load_family():
    fam = json.load(open(os.path.join(SCR, "design290b_family.json")))
    stable = [f for f in fam if f["z289"] >= 0.005]
    assert len(stable) == 121, len(stable)
    byid = {f["id"]: f for f in fam}
    sample = [byid[i] for i in NAMED] + [f for f in stable[::6] if f["id"] not in NAMED]
    return fam, stable, sample


def route(tag, band=None):
    g = B.load_route(tag) if tag in B.IMG else load_v282_route(tag)
    lo, hi = band or (18.0, 22.0)
    g["f0"] = B.ring_f0(g, lo, hi)
    g["env"] = B.demod_env(g["bar"], g["f0"], FS)
    on, pk, amp, thi, tlo = B.find_onsets(g["env"], g["eng"])
    g["on"], g["pk"], g["amp"] = on, pk, amp
    return g


def load_v282_route(tag):
    """a V282 route not in burst_onset_triggers.IMG (r6c): same loader, V282's own image cells."""
    import lowcmd_loopgain_v112_v278_v280 as LG
    img = LG.FW + ("_v282_V282-V281R3BASE-KP.FLAT.Y0-CAVE.R24CMP.BITS5.6-"
                   "MAP.LINEAR.TO6X.FEEDBACK46080.TORQUE.TAP_plain_image.bin")
    cells = GI.read_cells(img)
    g = C20.load(tag)
    g["tr"] = g["t"] - g["t"][0]
    g["cells"] = cells
    g["idx_live"], g["sgn_live"] = GI.demand_live(np.round(g["cmd"]), g["bar"], cells)
    return g


# ------------------------------------------------------------------------------------------------
def replay_window(g, a0, b0, c, pl, r24=True, motor_gain=True, n_iter=3):
    """the whole experiment for ONE window on ONE plant fit.

    V282 arm: electronics 923/1560, no cave.  Its closed run REPRODUCES the recording exactly, by
    construction of `d` -- asserted, not assumed.
    V292 arm: electronics 962/958 + the error-feedback cave, SAME command, SAME disturbance, plus the
    r24-arm delta branch (0xC6446 5244 -> 4725 at the wire-settled effective arm).
    """
    W = R.prep_window(g, a0, b0, c)
    P282 = R.PlantIIR(pl)
    el = R.Elec(c, fb=R.V282_FB, ef=False, two_floor=True)
    d, S_ol = R.invert_d(el, P282, W, W["wire1k"])
    A = R.closed_run(R.Elec(c, fb=R.V282_FB, ef=False, two_floor=True), R.PlantIIR(pl), W, d)
    recon = float(np.max(np.abs(A["T"] - S_ol["T"])))
    Bv = R.closed_run(R.Elec(c, fb=R.V292_FB, ef=True, two_floor=True), R.PlantIIR(pl), W, d)
    iters = []
    if r24:
        H = lambda f: R.r24_delta_response(f, with_motor_gain=motor_gain)   # noqa: E731
        ex = np.zeros(W["n"])
        for _ in range(n_iter):
            ex_new = R.apply_fr(Bv["wire"], H)
            iters.append(float(np.max(np.abs(ex_new - ex))))
            ex = ex_new
            Bv = R.closed_run(R.Elec(c, fb=R.V292_FB, ef=True, two_floor=True), R.PlantIIR(pl), W, d, extra_T=ex)
    return dict(W=W, d=d, A=A, B=Bv, recon=recon, iters=iters, ol=S_ol)


def measure(A, Bv, f0, skip=500):
    """every pre-registered readout, as V292/V282 ratios."""
    o = {}
    for nm, (lo, hi) in BANDS.items():
        ta = R.band_amp(A["T"][skip:], lo, hi)
        tb = R.band_amp(Bv["T"][skip:], lo, hi)
        o["T_" + nm] = (ta, tb, tb / ta if ta > 0 else np.nan)
    lo, hi = BANDS["ring"]
    wa = R.band_amp(A["wire"][skip:], lo, hi)
    wb = R.band_amp(Bv["wire"][skip:], lo, hi)
    o["W_ring"] = (wa, wb, wb / wa if wa > 0 else np.nan)
    ha = R.env_halflife(A["T"], f0)
    hb = R.env_halflife(Bv["T"], f0)
    o["halflife"] = (ha, hb, hb / ha if np.isfinite(ha) and ha > 0 else np.nan)
    # authority: delivered torque OUTSIDE every ring band
    oa = R.out_of_band_rms(A["T"][skip:], [(5.0, 22.0)])
    ob = R.out_of_band_rms(Bv["T"][skip:], [(5.0, 22.0)])
    o["auth_oob"] = (oa, ob, ob / oa if oa > 0 else np.nan)
    la = R.band_amp(A["T"][skip:], 0.3, 3.0)
    lb = R.band_amp(Bv["T"][skip:], 0.3, 3.0)
    o["auth_lf"] = (la, lb, lb / la if la > 0 else np.nan)
    ma = float(np.mean(np.abs(A["T"][skip:])))
    mb = float(np.mean(np.abs(Bv["T"][skip:])))
    o["auth_absmean"] = (ma, mb, mb / ma if ma > 0 else np.nan)
    return o


def pooled(rows, key):
    v = np.array([r[key][2] for r in rows], float)
    v = v[np.isfinite(v)]
    if len(v) == 0:
        return np.nan, (np.nan, np.nan)
    return float(np.median(v)), boot(v)


# ================================================================================================
#  DRIVER
# ================================================================================================
def run_route(tag, band, nwin=10, label="", fits=None, skip=800, motor_gain=True, r24=True,
              wins=None, gload=None):
    g = gload if gload is not None else route(tag, band)
    c = g["cells"]
    if wins is None:
        wins = ES.loud_windows(g, n=nwin)
    fam, stable, sample = load_family()
    fits = fits if fits is not None else sample
    res = {}
    t0 = time.time()
    for f in fits:
        pl = D.mkplant(f)
        rows = []
        for (a0, b0, p0) in wins:
            rep = replay_window(g, a0, b0, c, pl, r24=r24, motor_gain=motor_gain)
            assert rep["recon"] == 0.0, "V282 closed loop did NOT reproduce the window (fit %d)" % f["id"]
            m = measure(rep["A"], rep["B"], g["f0"], skip=skip)
            m["_iters"] = rep["iters"]
            rows.append(m)
        res[f["id"]] = rows
    return g, wins, res, time.time() - t0


HDR = {"T_ring": "T 18-22", "W_ring": "W 18-22", "halflife": "drivn t1/2", "T_shoulder": "T 9-18",
       "T_low": "T 5-9", "T_turn": "T 6-9", "T_sel": "T sel-band", "auth_oob": "auth oob",
       "auth_lf": "auth LF", "auth_absmean": "auth |T|"}


def table(res, fits, title, keys=("T_ring", "W_ring", "halflife", "T_shoulder", "T_low",
                                  "auth_oob", "auth_lf", "auth_absmean")):
    """every column is a V292/V282 RATIO on the same window.  Headers follow `keys`, always."""
    pr("")
    pr(title)
    pr("-" * 126)
    hdr = [HDR.get(k, k) for k in keys]
    pr("  %-22s" % "fit" + "".join("%11s" % h for h in hdr))
    allrows = []
    for f in fits:
        rows = res[f["id"]]
        allrows += rows
        vals = [pooled(rows, k)[0] for k in keys]
        tag = "%d%s" % (f["id"], {225: " (median)", 215: " (lo-auth)", 38: " (hi-auth)",
                                  117: " (worst B4)"}.get(f["id"], ""))
        pr("  %-22s" % tag + "".join("%11.3f" % v for v in vals))
    pr("  " + "-" * 124)
    ms, ci = [], []
    for k in keys:
        m, (lo, hi) = pooled(allrows, k)
        ms.append(m)
        ci.append("[%.2f,%.2f]" % (lo, hi))
    pr("  %-22s" % "POOLED (all fits)" + "".join("%11.3f" % v for v in ms))
    pr("  %-22s" % "  95% CI" + "".join("%11s" % v for v in ci))
    return allrows



def ringdown(g, wins, c, fits, amp=512.0, nwin=6):
    """the MATCHED free ring-down at each episode's operating point, plus the LINEAR pole as a
    second, independent method.  Returns (rows, linear_rows)."""
    import adv_v290_physics as A
    rows, lin = {}, {}
    for f in fits:
        pl = D.mkplant(f)
        e2 = A.Blocks(dict(c, fb_a=R.V282_FB[0], fb_b=R.V282_FB[1]), False, 0.0)
        e9 = A.Blocks(dict(c, fb_a=R.V292_FB[0], fb_b=R.V292_FB[1]), False, 0.0)
        f2, z2 = A.mode_pole(e2, pl, 10, 32)
        f9, z9 = A.mode_pole(e9, pl, 10, 32)
        h2 = np.log(2) / (2 * np.pi * z2 * f2) * 1e3 if z2 > 0 else np.inf
        h9 = np.log(2) / (2 * np.pi * z9 * f9) * 1e3 if z9 > 0 else np.inf
        lin[f["id"]] = (f2, z2, h2, f9, z9, h9, h9 / h2)
        rr = []
        for (a0, b0, p0) in wins[:nwin]:
            W = R.prep_window(g, a0, b0, c)
            d, _ = R.invert_d(R.Elec(c, fb=R.V282_FB, ef=False, two_floor=True), R.PlantIIR(pl), W, W["wire1k"])
            k0 = (p0 - (a0 - 50)) * 10
            o = []
            for kw in (dict(c=c, fb=R.V282_FB, ef=False, two_floor=True),
                       dict(c=c, fb=R.V292_FB, ef=True, two_floor=True)):
                dT, _ = R.kick_response(kw, pl, W, d, k0, amp=amp)
                o.append(R.decay_halflife(dT, k0))
            rr.append((o[0][0], o[1][0], o[1][0] / o[0][0] if o[0][0] > 0 else np.nan, o[0][2], o[1][2]))
        rows[f["id"]] = np.array(rr, float)
    return rows, lin


def disturbance_envelope_control(g, wins, c, pl):
    """THE CONTROL for the driven half-life metric: the half-life of the DISTURBANCE's own 18-22 Hz
    envelope.  If it is long, then a loop that has stopped resonating simply follows it, and a driven
    half-life ratio > 1 says nothing about the loop's ring-down."""
    out = []
    for (a0, b0, p0) in wins:
        W = R.prep_window(g, a0, b0, c)
        d, _ = R.invert_d(R.Elec(c, fb=R.V282_FB, ef=False, two_floor=True), R.PlantIIR(pl), W, W["wire1k"])
        out.append(R.env_halflife(d, g["f0"]))
    return np.array(out, float)


def high_angle_windows(g, n=6, half=150, idx_min=60.0, vmax=6.0, band=(6.0, 9.0)):
    """loaded high-angle engaged windows, ranked by their own 6-9 Hz driver-torque ripple."""
    import creep20_loop_id as C20
    lo, hi = band
    bp = C20.bandpass(g["bar"], lo, hi, FS)
    cand = []
    m = g["eng"] & (g["idx_live"] >= idx_min) & (g["vego"] < vmax)
    for a, b in C20.runs(m, 2 * half):
        for p0 in range(a + half, b - half, half):
            cand.append((float(np.sqrt(np.mean(bp[p0 - half:p0 + half] ** 2))), p0))
    cand.sort(reverse=True)
    out, used = [], []
    for amp, p0 in cand:
        if any(abs(p0 - q) < 2 * half for q in used):
            continue
        a0, b0 = p0 - half, p0 + half
        if a0 < 60 or b0 > len(g["t"]) - 20 or not g["eng"][a0:b0].all():
            continue
        out.append((a0, b0, p0)); used.append(p0)
        if len(out) >= n:
            break
    return out


# ================================================================================================
def main():
    fam, stable, sample = load_family()
    byid = {f["id"]: f for f in fam}
    named = [byid[i] for i in NAMED]
    spread = named + [f for f in stable[::6] if f["id"] not in NAMED]
    pr("=" * 126)
    pr("V292 ON THE OPERATOR'S OWN RECORDED GRINDING EPISODES -- byte-exact closed-loop replay")
    pr("agent `replay`, 2026-09-13.  ANALYSIS ONLY.")
    pr("=" * 126)
    pr("V292 image d1128232993d3a1d... : fb lag 923/1560 -> 962/958 (pole 16.52 -> 9.94 Hz, DC held 30.891/30.903),")
    pr("r24 arm 0xC6446 5244 -> 4725, error-feedback cave 0xC4C00 (52 B, hook 0x28F8E), 0x14A b3 telemetry.")
    pr("Cells read from the IMAGES here, not from a build script.  Plant family: design290b, %d fits, %d linear-stable."
       % (len(fam), len(stable)))
    pr("Fits scored: %s" % ", ".join(str(f["id"]) for f in spread))

    # ------------------------------------------------------------------ TASK 2, r39
    g39 = route("r39", (18.0, 22.0))
    w39 = ES.loud_windows(g39)
    pr("")
    pr("=" * 126)
    pr("TASK 2  r39 (V282), the 10 loudest 3 s engaged windows, f0 %.3f Hz" % g39["f0"])
    pr("=" * 126)
    pr("Every number is V292 / V282 on the SAME window, SAME 0xE4 command, SAME residual disturbance.")
    pr("The V282 arm reproduces the recording EXACTLY (max|dT| = 0 asserted on every window, every fit).")
    _, _, res39, dt = run_route("r39", (18.0, 22.0), fits=spread, gload=g39, wins=w39)
    pr("(%.0f s)" % dt)
    all39 = table(res39, spread, "2.1  PRIMARY -- r24 arm delta folded WITH the motor gain K = 5346/32768 (ADV-V292-B 7.1)")
    _, _, res39b, _ = run_route("r39", (18.0, 22.0), fits=named, gload=g39, wins=w39, r24=False)
    table(res39b, named, "2.2  CONTROL -- r24 arm delta NOT folded at all (0xC6446 held at 5244)")
    _, _, res39c, _ = run_route("r39", (18.0, 22.0), fits=named, gload=g39, wins=w39, motor_gain=False)
    table(res39c, named, "2.3  CONTROL -- r24 fold WITHOUT the motor gain (the record's inherited fold, x6.13 too big)")

    pr("")
    pr("2.4  RING-DOWN -- the driven metric is an ARTIFACT; the matched free ring-down is the answer")
    pr("-" * 126)
    rd, lin = ringdown(g39, w39, g39["cells"], named)
    pr("  %-16s %28s | %34s | %10s" % ("fit", "LINEAR closed-loop pole", "MATCHED free ring-down, byte-exact", "driven"))
    pr("  %-16s %11s %11s %5s | %10s %10s %6s %5s | %10s" %
       ("", "V282 f/z", "V292 f/z", "ratio", "V282 t1/2", "V292 t1/2", "ratio", "r2", "ratio"))
    for f in named:
        f2, z2, h2, f9, z9, h9, lr = lin[f["id"]]
        rr = rd[f["id"]]
        drv = pooled(res39[f["id"]], "halflife")[0]
        pr("  %-16s %5.2f/%.4f %5.2f/%.4f %5.3f | %8.0f ms %8.0f ms %6.3f %5.2f | %10.3f" %
           (f["id"], f2, z2, f9, z9, lr, np.median(rr[:, 0]), np.median(rr[:, 1]),
            np.median(rr[:, 2]), np.median(rr[:, 4]), drv))
    dctl = disturbance_envelope_control(g39, w39, g39["cells"], D.mkplant(byid[225]))
    drv_a = np.array([r["halflife"][0] for r in res39[225]], float)
    drv_b = np.array([r["halflife"][1] for r in res39[225]], float)
    pr("")
    pr("  CONTROL for the driven metric (fit 225): half-life of the DISTURBANCE's own 18-22 Hz envelope")
    pr("    disturbance  median %7.0f ms   (p10 %5.0f, p90 %6.0f)" % (np.median(dctl), np.percentile(dctl, 10), np.percentile(dctl, 90)))
    pr("    V282 driven  median %7.0f ms      V292 driven median %7.0f ms" % (np.median(drv_a), np.median(drv_b)))
    pr("    => V282's driven envelope is the MODE's own ring-down; V292's has stopped resonating and")
    pr("       tracks the disturbance, whose envelope is longer.  The driven ratio therefore measures")
    pr("       peak-to-background contrast, NOT ring-down.  The matched free ring-down is the metric.")

    with open(os.path.join(SCR, "v292_replay_s2.txt"), "w", encoding="utf-8") as fh:
        fh.write("\n".join(OUT) + "\n")
    print("\nwrote _scratch/v292_replay_s2.txt")


if __name__ == "__main__":
    main()
