import math, numpy as np
import rp5_outer_loop as O
HOLD_V_BP, HOLD_K_V, G_BP, G_V = O.HOLD_V_BP, O.HOLD_K_V, O.G_BP, O.G_V
print("outer-loop PM (first crossover), V293 -> trim with pole a (K/J 1), nominal tau 25 ms, fric on")
for a in (1011, 1018, 1020):
    O.WP = -math.log(a / 1024) / 1e-3
    for world in ("light", "ident"):
        row = []
        for v in (3, 5, 8, 12.5, 19, 26):
            k = float(np.interp(v, HOLD_V_BP, HOLD_K_V)); b = 6e-4 if world == "light" else 1 / float(np.interp(v, G_BP, G_V))
            p3, c3, _, _ = O.margins(v, False, b, k); p4, c4, _, _ = O.margins(v, True, b, k)
            row.append(f"{v}:{p3[0][1]:+.0f}->{p4[0][1]:+.0f}")
        print(f"  a {a} ({-math.log(a/1024)/(2*math.pi*1e-3):.2f} Hz) {world:5s}: " + "  ".join(row))
