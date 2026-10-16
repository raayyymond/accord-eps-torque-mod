# -*- coding: utf-8 -*-
"""Figures for docs/FIRMWARE-CODEPATH.md. Every number is read from the images (stock code.bin, V300 release).
Runs in ~3 s:  python analysis-2020accord/figures/codepath/make_codepath_figures.py"""
import os, glob, struct, time
import numpy as np
import matplotlib; matplotlib.use("Agg")
import matplotlib.pyplot as plt
t0 = time.time()
ROOT = os.environ.get("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares") + "/analysis-2020accord/"
OUT = os.path.dirname(os.path.abspath(__file__))
st = open(ROOT + "stock_fw_dump/code.bin", "rb").read()
import hashlib
v = open([p for p in glob.glob(ROOT + "_v300_*plain_image.bin") if "REV2" in p][0], "rb").read()
assert hashlib.sha256(v).hexdigest() == "7d58c823544e9e6ec369e7cc0fc0d7aa42fc8b075ad9b0005f58973d400f384e", "not the V300 rev-2 image"
u16 = lambda b, a: struct.unpack("<H", b[a:a+2])[0]


def rec(b, a):                      # n, X[n], Y[n]  (layout from 0x29DDE sld.hu 0x2 / 0x29DE2 add 0xc)
    n = u16(b, a); X = [u16(b, a+2+2*i) for i in range(n)]; Y = [u16(b, a+2+2*n+2*i) for i in range(n)]
    return X, Y


def lerp(x, X, Y):
    if x <= X[0]:
        return Y[0]
    if x >= X[-1]:
        return Y[-1]
    for i in range(len(X)-1):
        if x <= X[i+1]:
            return Y[i] + (Y[i+1]-Y[i])*(x-X[i])//(X[i+1]-X[i])


C = dict(stock="#6b7280", mod="#c2410c", mod2="#1d4ed8", aux="#059669")
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": .3, "figure.dpi": 130})

# 1. G(v) -----------------------------------------------------------------------------------------
rows = [struct.unpack("<HHh", v[0xC4CDA+6*k:0xC4CDA+6*k+6]) for k in range(7)]


def G(vv):
    if vv <= rows[0][0]:
        return rows[0][1]
    k = 0
    while vv > rows[k+1][0]:
        k += 1
    x, y, s = rows[k]
    return (((vv-x)*s) >> 12) + y


vw = np.arange(0, 7200); g = np.array([G(int(x)) for x in vw]); ms = vw/230.4
fig, ax = plt.subplots(figsize=(7, 3.4))
ax.plot(ms, g, color=C["mod"], lw=2, label="G(v) = table walk @0xC4CDA (V300 = V299 cave)")
ax.plot(ms, g*112/256*16/256*10, color=C["mod2"], lw=1.2, ls="--",
        label="P per degree of error = 10*16*G*112/2^16  (lane S counts/deg)")
for xv, lab in [(1382, "1382 (6.0 m/s): cap 4096 -> 6144"), (2880, "2880 (12.5 m/s): cap off, bound x64")]:
    ax.axvline(xv/230.4, color=C["aux"], lw=1, ls=":"); ax.text(xv/230.4+.15, 2050, lab, fontsize=7, color=C["aux"])
ax.scatter([r[0]/230.4 for r in rows[:6]], [r[1] for r in rows[:6]], color=C["mod"], s=14, zorder=3)
ax.set_xlabel("vehicle speed  (gp-0x6a5e / 230.4  m/s)"); ax.set_ylabel("G  (Q8: 256 = x1)"); ax.set_xlim(0, 31); ax.set_ylim(0, 2400)
ax.set_title("Cave speed gain G(v): E' = (E*G)>>8.  1178 below 3.1 m/s, min 559 at 11.75, 2188 above 26.9", fontsize=9)
ax.legend(fontsize=7, loc="upper right")
fig.tight_layout(); fig.savefig(OUT + "/fig1_gv.png"); plt.close(fig)

# 2. Kp / Kd schedules (slot 7 records) ----------------------------------------------------------------
KpX, KpYs = rec(st, 0xE5378); _, KpYv = rec(v, 0xE5378); KdX, KdYs = rec(st, 0xE511C); _, KdYv = rec(v, 0xE511C)
idx = np.arange(0, 241)
fig, axs = plt.subplots(1, 2, figsize=(8, 3.2))
axs[0].plot(idx, [lerp(i, KpX, KpYs) for i in idx], color=C["stock"], lw=2, label="stock Kp: %s" % KpYs)
axs[0].plot(idx, [lerp(i, KpX, KpYv) for i in idx], color=C["mod"], lw=2, label="V300 Kp: 112 flat (all 28 records)")
axs[0].set_title("Kp record 0xE5378 (bank 0xCB994, slot 7) vs demand index"); axs[0].set_xlabel("idx = |cmd|/16.1 (0..240), an inert key once flat"); axs[0].legend(fontsize=7)
axs[1].plot(np.arange(0, 40), [lerp(i, KdX, KdYs) for i in range(40)], color=C["stock"], lw=2, label="stock Kd: 128 flat")
axs[1].plot(np.arange(0, 40), [lerp(i, KdX, KdYv) for i in range(40)], color=C["mod"], lw=2, label="V300 Kd: 48 flat (all 28 records)")
axs[1].set_title("Kd record 0xE511C (bank 0xCB7D4, slot 7)"); axs[1].set_xlabel("idx (X knots 0,11,22,32)"); axs[1].legend(fontsize=7); axs[1].set_ylim(0, 150)
fig.tight_layout(); fig.savefig(OUT + "/fig2_kp_kd.png"); plt.close(fig)

# 3. A3 bound and the two-level cap ------------------------------------------------------------------------
th = np.arange(0, 601)   # 0.1 deg counts (0..60 deg)


def bound(theta, vv, outward=True):
    r9 = theta if outward else 0
    if vv > 2880:
        return (r9 << 6) + 1250
    b = (r9 << 4) + 1250; cap = 4096 if vv <= 1382 else 6144
    return min(b, cap)


fig, ax = plt.subplots(figsize=(7, 3.4))
for vv, lab, col in [(1000, "v <= 6.0 m/s: 16|th|+1250, cap 4096", C["mod"]), (2000, "6.0 < v <= 12.5 m/s: 16|th|+1250, cap 6144", C["mod2"]),
                     (4000, "v > 12.5 m/s: 64|th|+1250, no cap", C["aux"])]:
    ax.plot(th/10, [bound(int(t), vv) for t in th], color=col, lw=2, label=lab)
ax.axhline(1250, color=C["stock"], lw=1.5, ls="--", label="error toward centre (sign th != sign E'): 1250 at every v")
ax.axhline(8192, color="k", lw=.8, ls=":"); ax.text(1, 8300, "Honda ICL 0xC61BA = 8192 (I>>7 ceiling)", fontsize=7)
ax2 = ax.twinx(); ax2.set_ylim(0, 16000*0.1602); ax2.set_ylabel("lane torque T at full ramp, hands off  (S x 0.1602)")
ax.set_xlabel("|steering angle th|  (deg, gp-0x6a00/10)"); ax.set_ylabel("integral bound on I>>7  (S counts)"); ax.set_ylim(0, 16000); ax.set_xlim(0, 60)
ax.set_title("A3 integral bound (cave 0xC4C6A-0xC4CAB), in the direction of E'", fontsize=9); ax.legend(fontsize=7, loc="upper left")
fig.tight_layout(); fig.savefig(OUT + "/fig3_bound.png"); plt.close(fig)

# 4. Driver-torque fade (post-PID) ---------------------------------------------------------------------
fBX, fBY = rec(st, 0xE564C); fB2Xs, fB2Ys = rec(st, 0xE54FC); fB2Xv, fB2Yv = rec(v, 0xE54FC)
key = np.arange(0, 160)   # gp-0x682f = |tq|>>5
fig, ax = plt.subplots(figsize=(7, 3.4))
ax.plot(key*32, [lerp(k, fBX, fBY)/255 for k in key], color=C["stock"], lw=2, label="fadeB 0xE564C (arm 0, stock camera and every build before V298)")
ax.plot(key*32, [lerp(k, fB2Xs, fB2Ys)/255 for k in key], color=C["stock"], lw=1.2, ls="--", label="fadeB2 0xE54FC STOCK values (arm 2): what gp-0x6803 == 2 would have selected")
ax.plot(key*32, [lerp(k, fB2Xv, fB2Yv)/255 for k in key], color=C["mod"], lw=2.5, alpha=.7, label="fadeB2 0xE54FC in V300 := fadeB's X/Y (the live fade under the angle loop)")
ax.axvline(1229, color=C["mod2"], lw=1.2, ls=":"); ax.text(1250, .55, "cave hard freeze:\n|gp-0x4f68| > 1229\n(= Honda hands-on 1200 on the wire)", fontsize=7, color=C["mod2"])
ax.set_xlabel("|driver torque|  (raw torque-sensor counts gp-0x4f68; key = counts >> 5)"); ax.set_ylabel("fade f/255 on (I>>7)+P+D"); ax.set_xlim(0, 5000); ax.set_ylim(0, 1.05)
ax.set_title("Hand-torque fade on (I>>7)+P+D at 0x2A0B4-0x2A0C2: floor 0.30 above 2048 counts", fontsize=9); ax.legend(fontsize=6.5, loc="lower left")
fig.tight_layout(); fig.savefig(OUT + "/fig4_fade.png"); plt.close(fig)

# 5. The demand->setpoint map and LIM: STOCK in the release (bypassed by E4) ----------------------------
mX, mYs = rec(st, 0xE502C); _, mYv = rec(v, 0xE502C); lX, lYs = rec(st, 0xE51A8); _, lYv = rec(v, 0xE51A8)
assert mYs == mYv and lYs == lYv, "release must carry the stock map and LIM"
fig, axs = plt.subplots(1, 2, figsize=(8, 3.2))
axs[0].plot(mX, mYs, "o-", color=C["stock"], lw=2, ms=3, label="Honda map Y (max 172 = a RATE setpoint); V300 == stock")
axs[0].set_title("Demand map 0xE502C (bank 0xC9A88): BYPASSED by E4 in angle mode"); axs[0].set_xlabel("idx (0..240)"); axs[0].legend(fontsize=7)
axs[1].plot(np.array(lX)/230.4, lYs, "o-", color=C["stock"], lw=2, ms=3, label="Honda LIM Y 15360; V300 == stock")
axs[1].set_title("Command clamp LIM 0xE51A8 vs speed: feeds only idx now"); axs[1].set_xlabel("speed m/s"); axs[1].set_ylim(0, 18000); axs[1].legend(fontsize=7)
fig.tight_layout(); fig.savefig(OUT + "/fig5_map_lim.png"); plt.close(fig)

# 6. Delivered lane torque vs angle error (P only), both G extremes, with the clamps ------------------------
e_deg = np.linspace(0, 60, 601)


def T_of(e, Gv, Kp=112):
    E = 160*e; Ep = (E*Gv)/256; P = np.clip(Ep*Kp/256, -15360, 15360)
    return P*0.990*(254/256)*5346/32768


fig, ax = plt.subplots(figsize=(7, 3.4))
ax.plot(e_deg, T_of(e_deg, 1178), color=C["mod"], lw=2, label="V300 P only, v <= 3.1 m/s (G 1178): 51.6 T/deg, rail at 47.7 deg")
ax.plot(e_deg, T_of(e_deg, 559), color=C["mod2"], lw=2, label="V300 P only, 11.75 m/s (G 559): 24.5 T/deg")
ax.plot(e_deg, T_of(e_deg, 2188), color=C["aux"], lw=2, label="V300 P only, >= 26.9 m/s (G 2188): 95.8 T/deg, rail at 25.7 deg")
ax.axhline(2461, color="k", lw=.8, ls=":"); ax.text(1, 2500, "lane rail 2461 T (S 15360 x lag 0.990 x fade 254/256 x 5346/32768); the stock chain tops at 410 T", fontsize=7)
ax.set_xlabel("angle error |th_sp - th|  (deg)"); ax.set_ylabel("lane torque gp-0x6b38  (T counts)"); ax.set_ylim(0, 2800)
ax.set_title("P authority read from the image (I and D add; fade x0.30 under a hard hand)", fontsize=9); ax.legend(fontsize=7, loc="lower right")
fig.tight_layout(); fig.savefig(OUT + "/fig6_authority.png"); plt.close(fig)

# 8. DampAxis lane Y(v) record 0xD7A54 (and twin 0xD7A64): stock vs kept -------------------------------------------
def srec(b, a):
    n = u16(b, a); X = [u16(b, a+2+2*i) for i in range(n)]; Y = [struct.unpack("<h", b[a+2+2*n+2*i:a+4+2*n+2*i])[0] for i in range(n)]; return X, Y
dX, dYs = srec(st, 0xD7A54); _, dYv = srec(v, 0xD7A54); assert srec(v, 0xD7A64) == (dX, dYv)
fig, ax = plt.subplots(figsize=(7, 3.2))
ax.plot(np.array(dX)/230.4, dYs, "o-", color=C["stock"], lw=2, ms=4, label="stock Y %s" % dYs)
ax.plot(np.array(dX)/230.4, dYv, "o-", color=C["mod"], lw=2, ms=4, label="V300 rev 2 keeps V299's Y %s" % dYv)
ax.set_xlabel("speed (X / 230.4 m/s; X = 0, 1280, 5760)"); ax.set_ylabel("Y (lane gain, negative = inertia sign)")
ax.set_title("DampAxis lane gp-0x6b26, record 0xD7A54: Y(v) stock vs kept (reverting fails GATE 2 at 3 m/s)", fontsize=9); ax.legend(fontsize=7)
fig.tight_layout(); fig.savefig(OUT + "/fig8_dampaxis.png"); plt.close(fig)

# 7. Timing: 1 kHz lane vs 100 Hz holds ------------------------------------------------------------------------
fig, ax = plt.subplots(figsize=(7.5, 2.6))
t = np.arange(0, 41)
ax.eventplot([t], lineoffsets=3, linelengths=.6, colors=C["mod"]); ax.text(41.5, 3, "slot 0, 1 ms: FUN_00028ea6 lane + cave (reads th, v, op, hand)", fontsize=7, va="center")
ax.eventplot([t[t % 10 == 4]], lineoffsets=2, linelengths=.6, colors=C["stock"]); ax.text(41.5, 2, "slot 4, every 10th tick (c%10==4): writes gp-0x6a00 th, gp-0x6a56 rate -> the lane sees them 1-10 ms old", fontsize=7, va="center")
ax.eventplot([t[t % 5 == 2]], lineoffsets=1, linelengths=.6, colors=C["mod2"]); ax.text(41.5, 1, "slot 3, every 5th tick: 0xE4 RX poll -> gp-0x69ae setpoint (openpilot sends 0xE4 at 100 Hz)", fontsize=7, va="center")
ax.eventplot([t], lineoffsets=0, linelengths=.6, colors=C["aux"]); ax.text(41.5, 0, "slot 0, 1 ms, before the lane: FUN_00041464 fresh motor-frame rate gp-0x6abe (the D operand)", fontsize=7, va="center")
ax.set_yticks([]); ax.set_xlabel("ms"); ax.set_xlim(0, 40); ax.set_title("Who runs when (TCB table 0xBB920; dispatcher FUN_00014be4)"); ax.grid(False)
fig.tight_layout(); fig.savefig(OUT + "/fig7_timing.png", bbox_inches="tight"); plt.close(fig)
print("done in %.1f s" % (time.time()-t0), sorted(os.listdir(OUT)))
