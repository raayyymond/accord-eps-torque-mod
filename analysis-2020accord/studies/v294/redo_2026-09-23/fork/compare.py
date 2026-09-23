import numpy as np
cols = ["t","v","out","p","i","f","error","desLA","desJerk","output","jerk_alpha","ki"]
def load(n): return np.load(n)["arr"]
pairs = [("o_head_r1.npz","o_head_r1_generic.npz","HEAD r1 Accord path vs HEAD generic torque path (same car)"),
         ("o_head_r1.npz","o_base_r1.npz","HEAD r1 vs PRE-V293 base a357cd2b5 with the same toggles"),
         ("o_head_r1.npz","o_head_fallbacks.npz","HEAD r1 vs HEAD with EMPTY toggles (getattr fallbacks)"),
         ("o_head_rv.npz","o_parent_af.npz","HEAD + REVERT config vs rev 6.4 code 84766cdc5 + as-flown config"),
         ("o_head_af_nojerk.npz","o_parent_af.npz","HEAD + as-flown WITHOUT AccordJerkLpHz vs rev 6.4 code"),
         ("o_head_r1.npz","o_parent_af.npz","HEAD r1 vs rev 6.4 as flown (how much the revert changes the command)")]
for a, b, label in pairs:
    A, B = load(a), load(b)
    d = np.abs(A[:, 2:10] - B[:, 2:10])
    exact = np.array_equal(A[:, 2:10], B[:, 2:10])
    worst = {cols[2+j]: float(d[:, j].max()) for j in range(8)}
    print(f"{label}\n   bit-identical: {exact}   max|diff| out={worst['out']:.3g} p={worst['p']:.3g} i={worst['i']:.3g} f={worst['f']:.3g} desLA={worst['desLA']:.3g}")
    if not exact:
        for v in (4.5, 12.0, 20.0, 27.0):
            m = A[:, 1] == v
            print(f"      v={v:5.1f}: max|d out| {np.abs(A[m,2]-B[m,2]).max():.4f}  rms {np.sqrt(np.mean((A[m,2]-B[m,2])**2)):.4f}  |out| max A {np.abs(A[m,2]).max():.3f} B {np.abs(B[m,2]).max():.3f}")
