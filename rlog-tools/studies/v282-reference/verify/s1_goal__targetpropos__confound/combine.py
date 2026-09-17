import json
from pathlib import Path

R = Path(__file__).resolve().parent / "results"
V282_ROUTES = ["00000064--ce6b0b0ebb", "00000065--b9f78988bd", "0000006c--2bc842dbac"]

data = {r: json.loads((R / f"{r}.json").read_text()) for r in V282_ROUTES if (R / f"{r}.json").exists()}


def show(routes, label):
    print(f"\n=== {label} ===")
    for sp in [">22", "15-22", "8-15"]:
        for band in ["0.15-0.3", "0.3-0.6", "0.6-1.2"]:
            for ach in ["la_act", "la_pose"]:
                gains, secs = [], []
                for r in routes:
                    d = data.get(r)
                    if not d:
                        continue
                    sb = d["speed_bins"].get(sp, {})
                    if "bands" not in sb or band not in sb["bands"]:
                        continue
                    h = sb["bands"][band][ach]["H"]
                    if h is None:
                        continue
                    gains.append(h["H"])
                    secs.append(h["sec"])
                if gains:
                    wavg = sum(g * s for g, s in zip(gains, secs)) / sum(secs)
                    print(f"  sp={sp:6s} band={band:9s} ach={ach:6s} per-route H={['%.3f'%g for g in gains]}"
                          f"  secs={['%.0f'%s for s in secs]}  weighted={wavg:.3f}")


show(V282_ROUTES, "ALL V282 (64+65+6c)")
show(["00000064--ce6b0b0ebb", "00000065--b9f78988bd"], "LEAVE-OUT 6c (64+65 only)")
show(["0000006c--2bc842dbac"], "6c ONLY")

print("\n\n=== TERCILE relative error, ALL V282 pooled per-route (not merged) ===")
for sp in [">22", "15-22", "8-15"]:
    for band in ["0.15-0.3", "0.3-0.6", "0.6-1.2"]:
        for ach in ["la_act", "la_pose"]:
            for r in V282_ROUTES:
                d = data.get(r)
                if not d:
                    continue
                sb = d["speed_bins"].get(sp, {})
                if "bands" not in sb or band not in sb["bands"]:
                    continue
                t = sb["bands"][band][ach]["tercile"]
                if not t:
                    continue
                print(f"  {r:24s} sp={sp:6s} band={band:9s} ach={ach:6s} "
                      f"low={t['low']['relerr']:.3f}(n{t['low']['n_chunks']}) "
                      f"mid={t['mid']['relerr']:.3f}(n{t['mid']['n_chunks']}) "
                      f"high={t['high']['relerr']:.3f}(n{t['high']['n_chunks']})")

print("\n\n=== LAG (median s), per route ===")
for sp in [">22", "15-22", "8-15"]:
    for ach in ["la_act", "la_pose"]:
        for r in V282_ROUTES:
            d = data.get(r)
            if not d:
                continue
            sb = d["speed_bins"].get(sp, {})
            lg = sb.get("lag", {}).get(ach)
            if not lg:
                continue
            print(f"  {r:24s} sp={sp:6s} ach={ach:6s} median={lg['median']:.3f} "
                  f"[{lg['p25']:.3f},{lg['p75']:.3f}] n={lg['n']}")
