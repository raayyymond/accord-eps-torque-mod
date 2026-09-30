# -*- coding: utf-8 -*-
"""page_data.py -- every number the V295 close-out page shows, READ FROM THE BUILT IMAGES and marched
through the golden model (analysis-2020accord/model/eps_lkas_chain_model.py). Nothing here is copied
from a build script's constants.

    python page_data.py            -> out/page_data.json (+ a printed summary)

What it produces
  cells      : a / b / C / out-lag / clamps / Kp+Kd records / map, per image (stock, V282, V293, V294, V295)
  surface    : delivered torque T(idx) at fb = 0 for V282 and V293/V294/V295 (golden lkas_rate_pid_surface)
  trim_frf   : the trim's torque per deg/s of wheel rate, gain + phase, 0.2..30 Hz, V294 vs V295, by a
               sinusoid march of the byte-exact lane (lkas_fb_lag + lkas_rate_pid_tick at sp = 0)
  trim_time  : the trim torque during a 0.3 s half-sine wheel-rate pulse (a hard-turn snap), V294 vs V295
  restart    : the restart pulse after a filter bail at 10/30/100/300 deg/s, V294 vs V295
  closed_lin : linear closed-loop |alpha/cmd| and |L| on the identified nominal plant per speed band,
               with the trim's exact FRF folded in, V293 (trim off) / V294 / V295
"""
import glob
import hashlib
import json
import math
import os
import sys
from pathlib import Path

_d = Path(__file__).resolve()
while not (_d / ".pkgroot").exists() and _d != _d.parent:
    _d = _d.parent
for _p in [_d] + [p for p in _d.iterdir() if p.is_dir()]:
    if str(_p) not in sys.path:
        sys.path.insert(0, str(_p))

import numpy as np                                                          # noqa: E402
from dataclasses import replace                                             # noqa: E402
import eps_lkas_chain_model as M                                            # noqa: E402

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

FW = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
IMG_DIR = os.path.join(FW, "analysis-2020accord")
OUT = Path(__file__).resolve().parent / "out"
OUT.mkdir(exist_ok=True)
TP = 0xBF000
X_PER_DEGS = 8.0          # counts per deg/s of the 0x18F rate (0x55B48 writes (-x)>>3; DBC -1)


def find_img(tag):
    hits = sorted(glob.glob(os.path.join(IMG_DIR, f"_{tag}_*_plain_image.bin")))
    assert len(hits) == 1, (tag, hits)
    return hits[0]


def rd(img, off, n, signed=False):
    v = int.from_bytes(img[off:off + n], "little", signed=signed)
    return v


def cells_of(img):
    rec_kp = rd(img, 0xCB994 + 4 * 7, 4)            # record pointer, live selector 7
    rec_kd = rd(img, 0xCB7D4 + 4 * 7, 4)
    kp_x = [rd(img, rec_kp + 2 + 2 * i, 2) for i in range(5)]
    kp_y = [rd(img, rec_kp + 0xC + 2 * i, 2) for i in range(5)]
    kd_n = rd(img, rec_kd, 2)
    kd_x = [rd(img, rec_kd + 2 + 2 * i, 2) for i in range(4)]
    kd_y = [rd(img, rec_kd + 2 + 2 * 4 + 2 * i, 2) for i in range(4)]
    return dict(
        fb_lag_a=rd(img, 0xC63E8, 2, True), fb_lag_b=rd(img, 0xC63EA, 2), fb_clamp=rd(img, 0xC62E6, 2),
        out_lag_a=rd(img, 0xC63EC, 2, True), out_lag_b=rd(img, 0xC63EE, 2),
        p_clamp=rd(img, 0xC61BC, 2), d_clamp=rd(img, 0xC61B6, 2), sum_clamp=rd(img, 0xC61BE, 2),
        lane_clamp=rd(img, 0xC61B2, 2), i_clamp=rd(img, 0xC61BA, 2), deadband=rd(img, 0xC62E4, 2),
        kp_rec=hex(rec_kp), kp_x=kp_x, kp_y=kp_y, kd_rec=hex(rec_kd), kd_n=kd_n, kd_x=kd_x, kd_y=kd_y,
        op_28FA4=img[0x28FA4:0x28FA6].hex(), shl_29D76=img[0x29D76:0x29D78].hex(),
        r24_engaged=rd(img, 0xC6446, 2), r24_diseng=rd(img, 0xC6440, 2),
    )


def cal_from(img, c):
    """Golden-model Calibration for an image: the defaults are V282; override what the image says."""
    op = "diff" if c["op_28FA4"] == "89d1" else "sum"
    shl = {"c582": 5, "c282": 2, "c182": 1, "c082": 0}.get(c["shl_29D76"])
    assert shl is not None, c["shl_29D76"]
    return replace(M.Calibration(), fb_lag_a=c["fb_lag_a"], fb_lag_b=c["fb_lag_b"], fb_clamp=c["fb_clamp"],
                   kp_y=tuple(c["kp_y"]), kp_x=tuple(c["kp_x"]), kd_y=tuple(c["kd_y"]),
                   pid_d_clamp=c["d_clamp"], fb_op=op, e_shift=shl,
                   out_lag_a=c["out_lag_a"], out_lag_b=c["out_lag_b"])


def march_trim(cal, x_seq, sp=0, idx=0):
    st = M.EpsState()
    st.pid_ramp = 0x8000
    out = []
    for x in x_seq:
        fb = M.lkas_fb_lag(int(x), st, cal)
        out.append(M.lkas_rate_pid_tick(sp, fb, idx, st, cal)["T"])
    return np.array(out, dtype=float)


def trim_frf(cal, freqs, amp_dps=20.0, n_settle=3000, n_fit=6000):
    rows = []
    for f in freqs:
        n = n_settle + n_fit
        t = np.arange(n) * 1e-3
        x = np.round(amp_dps * X_PER_DEGS * np.sin(2 * math.pi * f * t)).astype(int)
        T = march_trim(cal, x)
        tt, yy = t[n_settle:], T[n_settle:]
        A = np.column_stack([np.sin(2 * math.pi * f * tt), np.cos(2 * math.pi * f * tt), np.ones_like(tt)])
        c, *_ = np.linalg.lstsq(A, yy, rcond=None)
        g = math.hypot(c[0], c[1]) / amp_dps                 # T counts per deg/s of wheel rate
        ph = math.degrees(math.atan2(c[1], c[0]))            # phase of T relative to the rate
        # the trim OPPOSES motion: T = -g*e^{j ph} * rate. damping part = component along -rate.
        damp = -g * math.cos(math.radians(ph))
        inert = -g * math.sin(math.radians(ph)) / (2 * math.pi * f)   # T per deg/s^2 (along -alpha)
        rows.append(dict(f=f, gain=g, phase=ph, damping=damp, inertia=inert))
    return rows


def trim_pulse(cal, peak_dps=50.0, width_s=0.3, n=1200):
    t = np.arange(n) * 1e-3
    x = np.zeros(n)
    m = (t >= 0.1) & (t <= 0.1 + width_s)
    x[m] = peak_dps * X_PER_DEGS * np.sin(math.pi * (t[m] - 0.1) / width_s)
    T = march_trim(cal, np.round(x).astype(int))
    return t, x / X_PER_DEGS, T


def restart_pulse(cal, rates=(10, 30, 100, 300), idx=0):
    """State forced to 0 (a bail) while the wheel turns at a constant rate: the trim after the re-open."""
    res = {}
    for r in rates:
        st = M.EpsState()
        st.pid_ramp = 0x8000
        x = int(round(r * X_PER_DEGS))
        # settle first so the lag's state is the steady one, then force it to zero (the bail) and re-open
        for _ in range(3000):
            fb = M.lkas_fb_lag(x, st, cal)
            M.lkas_rate_pid_tick(0, fb, idx, st, cal)
        st.fb_lag_s = 0
        T = []
        for _ in range(800):
            fb = M.lkas_fb_lag(x, st, cal)
            T.append(M.lkas_rate_pid_tick(0, fb, idx, st, cal)["T"])
        T = np.array(T)
        res[r] = dict(peak=int(np.max(np.abs(T))), ms_over_50=int(np.sum(np.abs(T) > 50)))
    return res


# identified nominal plant (studies/v295/plant/V294-PLANT-IDENT-r71b.md), T counts / deg units, per band
PLANT = {"0-5": dict(J=0.2, b=4.9, k=6.5), "5-10": dict(J=0.2, b=5.2, k=20.2), "10-15": dict(J=0.2, b=9.8, k=24.3),
         "15-22": dict(J=0.2, b=20.7, k=79.7), "22+": dict(J=0.2, b=26.4, k=55.8)}
LIGHT_B = {"5-10": dict(J=0.2, b=0.0006 * 2605, k=20.2), "15-22": dict(J=0.2, b=0.0006 * 2605, k=79.7)}


def closed_linear(frf_rows, plant, ff_gain=1.0):
    """Linear: (J s^2 + b s + k) theta = FF(s)*u - G(s)*s*theta, G from the marched FRF (complex, per deg/s).
    Output lag on FF modelled as 5.05 Hz one-pole with DC 0.99. Returns |alpha/u| (deg/s^2 per T of FF) and |L|."""
    rows = []
    for r in frf_rows:
        f = r["f"]
        w = 2 * math.pi * f
        s = 1j * w
        G = r["gain"] * np.exp(1j * math.radians(r["phase"]))       # T per deg/s, sign: T = -G*rate ... see below
        # in march_trim, T = g e^{j ph} rate with the sign already in ph (T opposes: ph ~ 180 deg at low f)
        Gc = -G                                                     # so that (b + Gc) s adds damping when Re Gc > 0
        out = 0.99 / (1 + s / (2 * math.pi * 5.05))
        den = plant["J"] * s ** 2 + plant["b"] * s + plant["k"] + Gc * s
        alpha_u = (s ** 2) * out * ff_gain / den
        L = Gc * s / (plant["J"] * s ** 2 + plant["b"] * s + plant["k"])
        rows.append(dict(f=f, alpha_u=abs(alpha_u), alpha_ph=math.degrees(np.angle(alpha_u)), L=abs(L)))
    return rows


def main():
    tags = {"stock": None, "V282": "v282", "V293": "v293", "V294": "v294", "V295": "v295"}
    imgs, cells, sha = {}, {}, {}
    for name, tag in tags.items():
        if tag is None:
            p = os.path.join(FW, "analysis-2020accord", "stock_fw_dump", "code.bin")
            if not os.path.exists(p):
                cand = glob.glob(os.path.join(FW, "analysis-2020accord", "**", "code.bin"), recursive=True)
                p = cand[0] if cand else None
            if p is None:
                continue
        else:
            p = find_img(tag)
        img = open(p, "rb").read()
        imgs[name] = img
        sha[name] = hashlib.sha256(img).hexdigest()
        cells[name] = cells_of(img)
        cells[name]["path"] = os.path.basename(p)
        cells[name]["sha256"] = sha[name]
    # V295 vs V294 diff
    diff = [i for i in range(0x13000, 0x100000) if imgs["V295"][i] != imgs["V294"][i]]
    cals = {k: cal_from(imgs[k], cells[k]) for k in ("V282", "V293", "V294", "V295")}
    # surfaces
    surface = {}
    for k in ("V282", "V293", "V294", "V295"):
        surface[k] = [M.lkas_rate_pid_surface(i, cals[k])["T"] for i in range(0, 241)]
    assert surface["V293"] == surface["V294"] == surface["V295"], "FF surface must be byte-identical"
    # trim FRF
    freqs = sorted(set([0.2, 0.3, 0.5, 0.7, 1.0, 1.4, 2.0, 2.5, 3.0, 4.0, 5.0, 7.0, 10.0, 13.0, 16.0, 20.0, 25.0, 30.0]))
    frf = {k: trim_frf(cals[k], freqs) for k in ("V294", "V295")}
    # pulse
    t, rate, T4 = trim_pulse(cals["V294"])
    _, _, T5 = trim_pulse(cals["V295"])
    pulse = dict(t=t[::5].tolist(), rate=rate[::5].tolist(), T_V294=T4[::5].tolist(), T_V295=T5[::5].tolist())
    # restart
    restart = {k: restart_pulse(cals[k]) for k in ("V294", "V295")}
    # closed-loop linear
    closed = {}
    for band, pl in PLANT.items():
        closed[band] = {"V293": closed_linear([dict(f=r["f"], gain=0.0, phase=0.0) for r in frf["V294"]], pl),
                        "V294": closed_linear(frf["V294"], pl), "V295": closed_linear(frf["V295"], pl)}
    closed_lb = {}
    for band, pl in LIGHT_B.items():
        closed_lb[band] = {"V293": closed_linear([dict(f=r["f"], gain=0.0, phase=0.0) for r in frf["V294"]], pl),
                           "V294": closed_linear(frf["V294"], pl), "V295": closed_linear(frf["V295"], pl)}
    # K_alpha and 20 Hz numbers
    def k_alpha(cal):
        return (cal.fb_lag_b / (1024 - cal.fb_lag_a)) * X_PER_DEGS * 1e-3
    summary = {}
    for k in ("V294", "V295"):
        c = cals[k]
        ka_r26 = k_alpha(c)                                  # r26 counts per deg/s^2 (below the pole)
        # r26 -> T: P = (r26*Kp)>>8 -> *254/256 -> out lag DC 0.99 -> *5346/32768
        r26_to_T = (c.kp_y[0] / 256) * (254 / 256) * 0.990234375 * (5346 / 32768)
        summary[k] = dict(pole_hz=-1000 * math.log(c.fb_lag_a / 1024) / (2 * math.pi), b=c.fb_lag_b, a=c.fb_lag_a,
                          K_alpha_T_per_dps2=ka_r26 * r26_to_T, r26_per_dps2=ka_r26, r26_to_T=r26_to_T,
                          b_max=int(2 ** 31 * (1024 - c.fb_lag_a) / (12000 * c.fb_lag_a)),
                          int32_margin=(2 ** 31 * (1024 - c.fb_lag_a) / (12000 * c.fb_lag_a)) / c.fb_lag_b,
                          trim_cap_T=abs(M.lkas_rate_pid_surface(120, c, fb=-c.fb_clamp)["T"] - M.lkas_rate_pid_surface(120, c)["T"]),
                          P_per_x_20Hz=None)
    # |P/x| at 20 Hz: P-domain amplitude per x count (pre-taper); from the FRF: T = gain(20Hz) per deg/s ...
    for k in ("V294", "V295"):
        g20 = [r for r in frf[k] if r["f"] == 20.0][0]["gain"]          # T per deg/s
        # back out to P per x: T/P = (254/256)*|outlag(20Hz)|*(5346/32768); x per deg/s = 8
        a_o, b_o = 992, 507
        z = np.exp(1j * 2 * math.pi * 20.0 * 1e-3)
        H_out = abs((b_o / 1024) * (1 + 1 / z) / (1 - (a_o / 1024) / z) / 32)
        summary[k]["P_per_x_20Hz"] = g20 / ((254 / 256) * H_out * (5346 / 32768)) / X_PER_DEGS
    data = dict(sha256=sha, cells=cells, diff_offsets=[hex(i) for i in diff], surface=surface, freqs=freqs,
                trim_frf=frf, pulse=pulse, restart=restart, closed=closed, closed_light_b=closed_lb,
                summary=summary, plant=PLANT)
    (OUT / "page_data.json").write_text(json.dumps(data, indent=1))
    print("sha256:", json.dumps(sha, indent=1))
    print("V295-V294 diff offsets:", [hex(i) for i in diff])
    for k in ("V294", "V295"):
        print(k, json.dumps(summary[k], indent=1))
        print(k, "FRF:", [(r["f"], round(r["gain"], 3), round(r["phase"], 1), round(r["damping"], 3)) for r in frf[k]])
        print(k, "restart:", restart[k])
    print("rail:", surface["V295"][240], "idx58:", surface["V295"][58], "V282 idx58:", surface["V282"][58])


if __name__ == "__main__":
    main()
