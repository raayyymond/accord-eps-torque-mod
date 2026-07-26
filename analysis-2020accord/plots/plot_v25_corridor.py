"""plot_v25_corridor.py — before/after of the V25 direction-corridor 2x edit.

Reads the configured STOCK image and the configured built V25 image,
decodes the two direction-corridor LERP tables, and
plots how the edit changes the firmware's soft-EME wind-up behavior.

Firmware context (so the axes mean something):
  * The soft-EME command integrator gp-0x3570 winds up per 1 kHz tick by
        delta = (command - dir_boundary) << 13
    accumulating ONLY when the LKAS command exits the corridor [dir2, dir1].
    When the integrator saturates it arms SM2/SM3, which cut steering authority
    (V18's wonky-for-~10s, self-recovering EME; no DTC, no dash light).
  * dir1 (UPPER) = LERP(tp+0x7748) and dir2 (LOWER) = LERP(tp+0x7754), both
    indexed by column angular velocity gp-0x4f60 (Q10, 1024 = 1.0 rad/s).
  * Command + corridor share raw command-domain counts; full-scale = +-8192
    (= +-0x2000, the shaper-input clamp). So 1024 counts = 12.5% of full scale.
  * The V18 GAIN doubles the LKAS command, so a 1x-sized corridor (+-1024) is
    exceeded by the 2x command -> wind-up -> soft EME. V25 scales the corridor
    Y-values x2 (-> +-2048) so the 2x command fits inside the deadband again.
"""
import os, struct, sys
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import STOCK_FW_DUMP, plain_image_path

HERE = os.path.dirname(os.path.abspath(__file__))
A2020 = os.path.dirname(HERE)
STOCK = STOCK_FW_DUMP / "code.bin"
V25   = plain_image_path("_v25_plain_image.bin")
OUT   = os.path.join(HERE, "v25_corridor_before_after.png")

FULL_SCALE = 8192.0   # command-domain full scale (= 0x2000)
Q10        = 1024.0    # velocity Q10 (counts per rad/s) and command unit


def decode_corridor(buf):
    """Return (dir1_upper, dir2_lower) flat corridor bounds (counts).
    Table fmt: [N][X0..X_{N-1}][Y0..Y_{N-1}] s16; both tables are flat (Y0==Y1)."""
    def s16(off):
        return struct.unpack_from("<h", buf, off)[0]
    # TABLE1 @0xC6748: N, X[2], Y[2]  -> dir1 = Y[0] (flat)
    n1 = s16(0xC6748); x1 = (s16(0xC674A), s16(0xC674C)); y1 = (s16(0xC674E), s16(0xC6750))
    # TABLE2 @0xC6754: N, X[2], Y[2]  -> dir2 = Y[0] (flat)
    n2 = s16(0xC6754); x2 = (s16(0xC6756), s16(0xC6758)); y2 = (s16(0xC675A), s16(0xC675C))
    return dict(n1=n1, x1=x1, y1=y1, n2=n2, x2=x2, y2=y2,
                dir1=y1[0], dir2=y2[0])


def main():
    stock = open(STOCK, "rb").read()
    v25   = open(V25, "rb").read()
    s = decode_corridor(stock)
    v = decode_corridor(v25)
    print("STOCK corridor:", s)
    print("V25   corridor:", v)

    # representative sustained 2x LKAS command magnitude (illustrative): the V18
    # gain (x~1.74 effective) lifts a moderate ~1x hold of ~860 counts to ~1500.
    cmd_2x = 1500

    fig, (axA, axB) = plt.subplots(1, 2, figsize=(14, 6))

    # ---- Panel A: corridor vs column velocity --------------------------------
    vel = np.linspace(-25, 25, 400)            # rad/s (clamp is +-25.0)
    axA.axhspan(s["dir2"], s["dir1"], color="tab:blue",   alpha=0.12, label="_stock band")
    axA.axhspan(v["dir2"], v["dir1"], color="tab:orange", alpha=0.10, label="_v25 band")
    axA.plot(vel, np.full_like(vel, s["dir1"]), color="tab:blue",   lw=2, label=f"STOCK dir1 (+{s['dir1']})")
    axA.plot(vel, np.full_like(vel, s["dir2"]), color="tab:blue",   lw=2, ls="--", label=f"STOCK dir2 ({s['dir2']})")
    axA.plot(vel, np.full_like(vel, v["dir1"]), color="tab:orange", lw=2, label=f"V25 dir1 (+{v['dir1']})")
    axA.plot(vel, np.full_like(vel, v["dir2"]), color="tab:orange", lw=2, ls="--", label=f"V25 dir2 ({v['dir2']})")
    axA.axhline( cmd_2x, color="tab:red", lw=1.6, ls=":", label=f"~2x LKAS cmd (±{cmd_2x})")
    axA.axhline(-cmd_2x, color="tab:red", lw=1.6, ls=":")
    # show where the X (velocity) breakpoints sit
    for bx in set(s["x1"] + s["x2"]):
        axA.axvline(bx / Q10, color="gray", lw=0.7, ls=":", alpha=0.6)
    axA.set_title("A. Direction corridor [dir2, dir1] vs column velocity\n"
                  "(command must stay INSIDE the band to avoid integrator wind-up)")
    axA.set_xlabel("column angular velocity  (rad/s)   [gp-0x4f60, Q10]")
    axA.set_ylabel("corridor bound  (command counts;  full-scale ±8192 = ±0x2000)")
    axA.set_xlim(-25, 25); axA.set_ylim(-3000, 3000)
    axA.grid(True, alpha=0.3); axA.legend(loc="upper right", fontsize=8)
    axA.annotate("stock corridor is FLAT (velocity-independent):\nY[0]=Y[1] in both tables",
                 xy=(0, s["dir1"]), xytext=(-23, 1300), fontsize=8,
                 arrowprops=dict(arrowstyle="->", color="tab:blue"))

    # ---- Panel B: per-tick wind-up vs command magnitude ----------------------
    cmd = np.linspace(0, FULL_SCALE, 400)
    excess_stock = np.clip(cmd - s["dir1"], 0, None)   # |cmd|-corridor when outside
    excess_v25   = np.clip(cmd - v["dir1"], 0, None)
    axB.plot(cmd, excess_stock, color="tab:blue",   lw=2, label=f"STOCK (corridor +{s['dir1']})")
    axB.plot(cmd, excess_v25,   color="tab:orange", lw=2, label=f"V25 (corridor +{v['dir1']})")
    axB.axvspan(0, s["dir1"], color="tab:blue",   alpha=0.10)
    axB.axvspan(s["dir1"], v["dir1"], color="tab:green", alpha=0.16,
                label=f"NEW dead-band gained: {s['dir1']}–{v['dir1']} counts")
    axB.axvline(cmd_2x, color="tab:red", lw=1.6, ls=":", label=f"~2x LKAS cmd ({cmd_2x})")
    axB.set_title("B. Integrator wind-up vs |LKAS command|\n"
                  "(excess beyond corridor → Δgp-0x3570 per tick → SM2/SM3 → soft EME)")
    axB.set_xlabel("|LKAS command|  (command counts;  ±8192 = full scale)")
    axB.set_ylabel("excess beyond corridor  (counts;  drives wind-up rate)")
    axB.set_xlim(0, FULL_SCALE); axB.set_ylim(-200, 6500)
    axB.grid(True, alpha=0.3); axB.legend(loc="upper left", fontsize=8)
    axB.annotate("a ~2x command that WOUND UP under stock\n(it sits past +1024) now sits INSIDE the\nV25 corridor (< +2048) → no wind-up → no soft EME",
                 xy=(cmd_2x, 0), xytext=(2600, 3500), fontsize=8,
                 arrowprops=dict(arrowstyle="->", color="tab:red"))

    fig.suptitle("V25 — Direction-corridor ×2  (39990-TVA-A160)   "
                 "stock ±1024  →  V25 ±2048   [tp+0x774e/0x7750/0x775a/0x775c]",
                 fontsize=12, fontweight="bold")
    fig.tight_layout(rect=[0, 0, 1, 0.96])
    fig.savefig(OUT, dpi=130)
    print("WROTE", os.path.relpath(OUT, A2020))


if __name__ == "__main__":
    main()
