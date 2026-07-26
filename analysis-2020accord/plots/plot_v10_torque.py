"""plot_v10_torque.py — visualize the V10 torque Y-axis table edits.

Two candidate torque Y-axis lists (TORQUE_PATH_AND_TABLE.md §3c), 12 x int16, in the
0xC4000 calibration page. Shows stock vs the V10 transform: linearize start->end, then
x2 (V10a) and x3 (V10b)."""
import os, struct, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ANALYSIS_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ANALYSIS_DIR not in sys.path:
    sys.path.insert(0, ANALYSIS_DIR)
from firmware_paths import STOCK_FW_DUMP

HERE = os.path.dirname(os.path.abspath(__file__))
code = open(STOCK_FW_DUMP / "code.bin", "rb").read()


def rd(off, n=12):
    return [struct.unpack_from("<h", code, off + 2 * i)[0] for i in range(n)]


def linearize(v):
    n, s, e = len(v), v[0], v[-1]
    return [round(s + (e - s) * i / (n - 1)) for i in range(n)]


LISTS = {"0xC4A42": rd(0xC4A42), "0xC4A6E": rd(0xC4A6E)}
x = list(range(12))

fig, axes = plt.subplots(1, 2, figsize=(15, 6.2), sharex=True)
fig.suptitle("2020 Accord TVA EPS — V10 torque Y-axis table candidates\n"
             "stock  →  linearized (start→end)  →  ×2 (V10a)  ×3 (V10b)",
             fontsize=13, fontweight="bold")

styles = dict(stock=dict(color="#888", marker="o", ls="--", lw=1.6),
              lin=dict(color="#1f77b4", marker="s", lw=2.0),
              x2=dict(color="#2ca02c", marker="^", lw=2.0),
              x3=dict(color="#d62728", marker="D", lw=2.0))

for ax, (name, stock) in zip(axes, LISTS.items()):
    base = linearize(stock)
    v2 = [v * 2 for v in base]
    v3 = [v * 3 for v in base]
    ax.plot(x, stock, label=f"stock {stock[0]}…{stock[-1]}", **styles["stock"])
    ax.plot(x, base, label="linearized", **styles["lin"])
    ax.plot(x, v2, label="V10a  ×2", **styles["x2"])
    ax.plot(x, v3, label="V10b  ×3", **styles["x3"])
    ax.set_title(f"torque list @ {name}  (12 × int16)", fontsize=11)
    ax.set_xlabel("breakpoint index")
    ax.set_ylabel("table value (counts)")
    ax.set_xticks(x)
    ax.grid(True, alpha=0.3)
    ax.legend(loc="upper left", framealpha=0.95)
    ax.axhline(0, color="k", lw=0.6)

fig.tight_layout(rect=[0, 0, 1, 0.93])
out = os.path.join(HERE, "v10_torque_tables.png")
fig.savefig(out, dpi=130)
print("wrote", out)
