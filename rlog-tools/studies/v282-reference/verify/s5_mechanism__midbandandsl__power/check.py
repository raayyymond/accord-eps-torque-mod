import json
d = json.load(open("../../s5_mechanism/s5_05_closedloop_validate.json"))
T64_KEYS = ["0000006c--68c6e94b17","0000006d--05e83bb04f"]
T64B_KEY = "0000006e--6ca3e014fd"
T5_KEY = "00000076--d0b7ea7e4d"
T4_KEY = "00000075--6c8687d5bd"

print(f"{'variant':10s} {'6c_b030':>8s} {'6d_b030':>8s} {'T64mean':>8s} {'T64B':>8s} {'B>mean':>7s} {'B>6d(low)':>10s} {'T5':>7s} {'T4':>7s}")
n_mean_below=0; n_vs_low=0
margins=[]
for vn, g in d.items():
    c = g[T64_KEYS[0]]['b030']['sim']
    dd = g[T64_KEYS[1]]['b030']['sim']
    mean64 = (c+dd)/2
    b = g[T64B_KEY]['b030']['sim']
    t5 = g[T5_KEY]['b030']['sim']
    t4 = g[T4_KEY]['b030']['sim']
    below_mean = b < mean64
    below_low = b < min(c,dd)
    if below_mean: n_mean_below+=1
    if below_low: n_vs_low+=1
    margins.append(mean64-b)
    print(f"{vn:10s} {c:8.3f} {dd:8.3f} {mean64:8.3f} {b:8.3f} {'Y' if below_mean else 'N':>7s} {'Y' if below_low else 'N':>10s} {t5:7.3f} {t4:7.3f}")

print()
print("ranking T64B < mean(T64):", n_mean_below, "/13")
print("ranking T64B < min(T64 routes) [i.e. below BOTH]:", n_vs_low, "/13")
print("margins mean64-B (sorted):", sorted(round(m,3) for m in margins))
print("intra-T64 spread (|6c-6d|) per variant:")
for vn,g in d.items():
    c=g[T64_KEYS[0]]['b030']['sim']; dd=g[T64_KEYS[1]]['b030']['sim']
    print(f"  {vn:10s} spread={abs(c-dd):.3f}")

print()
print("T4 b030 sim max across variants:", max(g[T4_KEY]['b030']['sim'] for g in d.values()), "vs threshold 1.5")
print("T4 measured:", d['nominal'][T4_KEY]['b030']['meas'])
