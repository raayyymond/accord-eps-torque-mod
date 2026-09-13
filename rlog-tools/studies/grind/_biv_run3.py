import json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
os.environ.setdefault("ACCORD_FIRMWARE_ROOT", "C:/Users/dudei/Desktop/Projects/accord-firmwares")
import b_iv_kappa as M, _biv_part4 as P4, bof_v282 as BF
from v282_r24_tap_read import read_cells
cells = read_cells(BF.V282_IMG)
G = {}
for t in BF.V282_ROUTES:
    print("loading %s ..." % t, flush=True); G[t] = BF.load(t, cells)
P4.longwin(G)
with open(os.path.join(HERE, "_scratch", "b_iv_kappa_p4.txt"), "w", encoding="utf-8") as fh:
    fh.write("\n".join(M.OUT) + "\n")
with open(os.path.join(HERE, "_scratch", "b_iv_kappa_p4.json"), "w", encoding="utf-8") as fh:
    json.dump(M.J, fh, indent=1, default=float)
print("wrote p4")
