"""ADV-D 9: can a filter BAIL (the only path to the b-scaled restart pulse) happen in driving?  Bail conditions from the
V294/V295 decompile of FUN_00028ea6 (identical code bytes): |gp-0x4f60| > 25600 (torsion bar, raw; wire = raw x 1.024),
gp-0x6752 not in {-1, +1}, |x = gp-0x6a56| > 12000 (0x18F raw rate, 8 counts per deg/s).  Max |0x18F rate| and |bar|
over every cached route in the kit's v280 cache (raw npz, all frames engaged or not)."""
import glob, os
import numpy as np
C = r"C:/Users/dudei/Desktop/Projects/accord-eps-torque-mod/analysis-2020accord/_scratch/cache/v280"
tot_s = 0.0; mr = 0; mb = 0; rows = []
for f in sorted(glob.glob(os.path.join(C, "r*.npz"))):
    if "_b4" in f:
        continue
    try:
        D = np.load(f)
        if "rate" not in D or "tq" not in D:
            continue
        r = np.abs(D["rate"].astype(float)); b = np.abs(D["tq"].astype(float)) * 1.024
        s = len(r) / 100.0
        tot_s += s; mr = max(mr, r.max()); mb = max(mb, b.max())
        rows.append((os.path.basename(f), s, r.max(), b.max()))
    except Exception as e:
        rows.append((os.path.basename(f), 0, -1, -1))
for nm, s, r, b in rows:
    print("  %-22s %6.0f s  max|rate| %6.0f counts (%4.0f deg/s)  max|bar| %6.0f wire" % (nm, s, r, r / 8, b))
print("ALL %d routes, %.0f s: max |0x18F rate| %.0f counts = %.0f deg/s (bail 12000 = 1500 deg/s, %.0f %% of it); max |bar| %.0f wire (bail %.0f wire, %.0f %%)" % (
    len(rows), tot_s, mr, mr / 8, 100 * mr / 12000, mb, 25600 * 1.024, 100 * mb / (25600 * 1.024)))
