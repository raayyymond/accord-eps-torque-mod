"""analyze_c5000_block.py — infer + plot the 0xC5000..0xC6000 calibration block.

This is the 4 kB block DELIBERATELY excluded from the V4 .rwd (build_stock_tva_v4.py).
It sits between the two flashed calibration blocks (0xC4000, 0xC6000) in the
2020 Accord 39990-TVA-A160 firmware (V850, little-endian).

Structure inferred from byte inspection (all offsets relative to BASE=0xC5000):
  0x000-0x040  header words: float32 + a couple packed words + repeated key
  0x040-0x090  float32 calibration constants (gains/scales), with a few
               non-float packed words interleaved
  0x090-0x1E4  packed scalar parameter struct — mixed u8/u16 fields, no clean
               table structure. LOW confidence on meaning -> plotted RAW.
  0x1E4-0x574  the bulk: a dense run of count-prefixed int16 lookup curves
               (1D breakpoint tables). Format per curve:
                   u16 N | N*u16 X-breakpoints | N*s16 Y-values | u16 0x0000
               X strictly increasing. HIGH confidence on structure.
  0x574-0x788  float32 calibration constants (limits/thresholds), with two
               int16 curves embedded near 0x728/0x740.
  0x788-0xFF0  erased (0xFF) gap.
  0xFF0-0x1000 16-byte tail (mostly FF + a trailing float marker).

We are confident about the ENCODING (float32 vs count-prefixed int16 LUT).
We are NOT confident about the physical MEANING of each axis (likely EPS
speed/current/torque axes vs assist/gain/limit outputs). Plots are therefore
labelled by offset + index, with only cautious hypotheses in the report.

Run: python analysis-2020accord/analyze_c5000_block.py
Outputs: plots_c5000/*.png + a printed report.
"""
import os, sys, struct
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import STOCK_FW_DUMP

HERE = os.path.dirname(os.path.abspath(__file__))
CODE_BIN = STOCK_FW_DUMP / "code.bin"
OUTDIR   = os.path.join(HERE, "plots_c5000")
BASE     = 0xC5000
SIZE     = 0x1000

code = open(CODE_BIN, "rb").read()
blk  = code[BASE:BASE + SIZE]

def u16(o): return struct.unpack_from("<H", blk, o)[0]
def s16(o): return struct.unpack_from("<h", blk, o)[0]
def f32(o): return struct.unpack_from("<f", blk, o)[0]

# ---------------- curve parser (count-prefixed int16 LUTs) ----------------

def curve_at(o):
    """Return (N, xs, ys, end_after_term) if a valid LUT starts at o, else None."""
    if o + 2 > SIZE:
        return None
    n = u16(o)
    if not (2 <= n <= 10):
        return None
    end = o + 2 + 4 * n
    if end + 2 > SIZE:
        return None
    xs = [u16(o + 2 + 2 * i) for i in range(n)]
    if not all(xs[i] < xs[i + 1] for i in range(n - 1)):
        return None
    if xs[-1] >= 60000:
        return None
    term = u16(end)
    # accept if the curve is 0x0000-terminated OR immediately followed by another curve
    nxt_ok = False
    if term != 0:
        save = u16(end)  # noqa
        nxt_ok = _looks_like_curve_start(end)
        if not nxt_ok:
            return None
    ys = [s16(o + 2 + 2 * n + 2 * i) for i in range(n)]
    return (n, xs, ys, end + (2 if term == 0 else 0))

def _looks_like_curve_start(o):
    if o + 2 > SIZE:
        return False
    n = u16(o)
    if not (2 <= n <= 10):
        return False
    end = o + 2 + 4 * n
    if end + 2 > SIZE:
        return False
    xs = [u16(o + 2 + 2 * i) for i in range(n)]
    return all(xs[i] < xs[i + 1] for i in range(n - 1)) and xs[-1] < 60000

def find_curves():
    curves = []
    o = 0
    while o < SIZE - 4:
        r = curve_at(o)
        if r:
            n, xs, ys, nxt = r
            curves.append({"off": o, "n": n, "xs": xs, "ys": ys})
            o = nxt
        else:
            o += 2
    return curves

# ---------------- float region decode ----------------

def decode_floats(lo, hi):
    out = []
    for o in range(lo, hi, 4):
        v = f32(o)
        av = abs(v)
        # "plausible calibration float": zero, or within a sane magnitude band
        plausible = (v == 0.0) or (1e-3 <= av <= 1e6)
        out.append({"off": o, "val": v, "plausible": plausible})
    return out

# ---------------- plotting ----------------

def plot_overview(curves):
    fig, ax = plt.subplots(2, 1, figsize=(14, 6), height_ratios=[3, 1])
    arr = np.frombuffer(blk, dtype=np.uint8).astype(float)
    ax[0].plot(np.arange(SIZE), arr, lw=0.4, color="#264653")
    ax[0].set_title(f"0xC5000 block — raw byte values (full {SIZE} bytes)")
    ax[0].set_xlabel("offset from 0xC5000"); ax[0].set_ylabel("byte value")
    ax[0].set_xlim(0, SIZE)
    # shade regions
    regions = [
        (0x000, 0x040, "#e9c46a", "header"),
        (0x040, 0x090, "#2a9d8f", "float consts"),
        (0x090, 0x1E4, "#e76f51", "packed struct (raw)"),
        (0x1E4, 0x574, "#457b9d", "int16 LUT curves"),
        (0x574, 0x788, "#2a9d8f", "float consts"),
        (0x788, 0xFF0, "#cccccc", "erased 0xFF"),
    ]
    for lo, hi, col, lab in regions:
        ax[0].axvspan(lo, hi, color=col, alpha=0.18)
        ax[0].text((lo + hi) / 2, 250, lab, ha="center", va="top",
                   fontsize=7, rotation=90, color="#333")
    # curve start markers
    for cv in curves:
        ax[0].axvline(cv["off"], color="#1d3557", lw=0.3, alpha=0.4)
    # entropy-ish: count of nonzero/non-FF per 64-byte window
    win = 64
    dens = [sum(1 for b in blk[i:i+win] if b not in (0x00, 0xFF)) / win
            for i in range(0, SIZE, win)]
    ax[1].bar(np.arange(len(dens)) * win, dens, width=win, align="edge",
              color="#457b9d")
    ax[1].set_title("data density (fraction non-00/non-FF per 64B)")
    ax[1].set_xlim(0, SIZE); ax[1].set_xlabel("offset")
    fig.tight_layout()
    fig.savefig(os.path.join(OUTDIR, "00_overview.png"), dpi=110)
    plt.close(fig)

def plot_curves(curves):
    n = len(curves)
    per_fig = 24
    figi = 0
    for start in range(0, n, per_fig):
        chunk = curves[start:start + per_fig]
        cols = 4
        rows = (len(chunk) + cols - 1) // cols
        fig, axes = plt.subplots(rows, cols, figsize=(16, 3 * rows))
        axes = np.atleast_1d(axes).ravel()
        for i, cv in enumerate(chunk):
            ax = axes[i]
            ax.plot(cv["xs"], cv["ys"], "o-", ms=3, lw=1.2, color="#e76f51")
            ax.set_title(f"@0x{BASE+cv['off']:05X}  N={cv['n']}", fontsize=8)
            ax.tick_params(labelsize=6)
            ax.grid(alpha=0.25)
        for j in range(len(chunk), len(axes)):
            axes[j].axis("off")
        fig.suptitle(f"int16 lookup curves (X breakpoints vs Y values) "
                     f"[{start+1}-{start+len(chunk)} of {n}]", fontsize=11)
        fig.tight_layout(rect=[0, 0, 1, 0.98])
        fig.savefig(os.path.join(OUTDIR, f"01_curves_{figi:02d}.png"), dpi=110)
        plt.close(fig)
        figi += 1

def plot_floats(floats, lo, hi, name, title):
    fig, ax = plt.subplots(figsize=(14, 4))
    offs = [f["off"] for f in floats]
    vals = [f["val"] for f in floats]
    cols = ["#2a9d8f" if f["plausible"] else "#bbbbbb" for f in floats]
    x = np.arange(len(floats))
    ax.stem(x, vals, basefmt=" ")
    for xi, f, c in zip(x, floats, cols):
        ax.plot(xi, f["val"], "o", color=c, ms=5)
        if f["plausible"]:
            ax.annotate(f"{f['val']:g}", (xi, f["val"]), fontsize=6,
                        ha="center", va="bottom", rotation=45)
    ax.set_title(f"{title}  (0x{BASE+lo:05X}-0x{BASE+hi:05X})  "
                 f"green=plausible float, grey=likely packed non-float")
    ax.set_xlabel("float32 index"); ax.set_ylabel("value")
    ax.set_xticks(x[::2])
    ax.set_xticklabels([f"0x{BASE+o:05X}" for o in offs[::2]], rotation=90, fontsize=5)
    ax.grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTDIR, name), dpi=110)
    plt.close(fig)

def plot_raw_packed(lo, hi):
    fig, ax = plt.subplots(2, 1, figsize=(14, 6))
    seg = blk[lo:hi]
    ax[0].plot(np.arange(lo, hi), np.frombuffer(seg, np.uint8), ".-",
               ms=2, lw=0.5, color="#e76f51")
    ax[0].set_title(f"packed scalar struct RAW bytes  0x{BASE+lo:05X}-0x{BASE+hi:05X}")
    ax[0].set_ylabel("byte"); ax[0].grid(alpha=0.25)
    # u16 LE interpretation
    n16 = (hi - lo) // 2
    u = [u16(lo + 2 * i) for i in range(n16)]
    s = [s16(lo + 2 * i) for i in range(n16)]
    ax[1].plot(np.arange(lo, lo + 2 * n16, 2), u, ".-", ms=2, lw=0.5,
               color="#2a9d8f", label="u16 LE")
    ax[1].plot(np.arange(lo, lo + 2 * n16, 2), s, ".-", ms=2, lw=0.5,
               color="#457b9d", label="s16 LE", alpha=0.6)
    ax[1].set_title("same region interpreted as u16 / s16 LE (no confident structure)")
    ax[1].set_xlabel("offset"); ax[1].legend(fontsize=7); ax[1].grid(alpha=0.25)
    fig.tight_layout()
    fig.savefig(os.path.join(OUTDIR, "03_packed_struct_raw.png"), dpi=110)
    plt.close(fig)

# ---------------- report ----------------

def main():
    os.makedirs(OUTDIR, exist_ok=True)
    curves = find_curves()
    fl_top = decode_floats(0x40, 0x90)
    fl_bot = decode_floats(0x574, 0x788)

    print("=" * 72)
    print(f"0xC5000 calibration block analysis  ({SIZE} bytes)")
    print("=" * 72)
    print(f"\nint16 lookup curves found: {len(curves)}")
    for cv in curves:
        print(f"  @0x{BASE+cv['off']:05X}  N={cv['n']:2d}  "
              f"X={cv['xs']}  Y={cv['ys']}")
    print(f"\nfloat consts (0x40-0x90): "
          f"{sum(1 for f in fl_top if f['plausible'])}/{len(fl_top)} plausible")
    for f in fl_top:
        tag = "" if f["plausible"] else "  <-- non-float (packed word)"
        print(f"  0x{BASE+f['off']:05X}  {f['val']:.6g}{tag}")
    print(f"\nfloat consts (0x574-0x788): "
          f"{sum(1 for f in fl_bot if f['plausible'])}/{len(fl_bot)} plausible")
    for f in fl_bot:
        tag = "" if f["plausible"] else "  <-- non-float"
        print(f"  0x{BASE+f['off']:05X}  {f['val']:.6g}{tag}")

    plot_overview(curves)
    plot_curves(curves)
    plot_floats(fl_top, 0x40, 0x90, "02_floats_top.png",
                "float32 calibration constants (top region)")
    plot_floats(fl_bot, 0x574, 0x788, "04_floats_bottom.png",
                "float32 calibration constants (bottom region)")
    plot_raw_packed(0x90, 0x1E4)

    print(f"\nWROTE plots to {OUTDIR}")
    print("  00_overview.png, 01_curves_*.png, 02_floats_top.png,")
    print("  03_packed_struct_raw.png, 04_floats_bottom.png")

if __name__ == "__main__":
    main()
